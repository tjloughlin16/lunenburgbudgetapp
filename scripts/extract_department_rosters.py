#!/usr/bin/env python3
"""The Police and Fire rosters, by name, as the town prints them.

    python3 scripts/extract_department_rosters.py
    python3 scripts/extract_department_rosters.py --check

Writes `sources/data/department-rosters.csv`.

TJ: *"police posts its exact staff ... literally by name"*. It does, and so does the Fire
Department, in every annual report. I had said the town publishes no roster for most
departments, having searched our own extraction plan rather than the documents -- the same
mistake twice in one day, and this is the correction to it.

WHAT THEY PRINT. The Police Department heads a section `Department Personnel:` and lists
every officer by rank and assignment: Administration, then the Patrol Bureau split into Day,
Evening and Split shifts, then the Investigative Bureau and the Community Policing Bureau.
The Fire Department heads a `Roster of the Lunenburg Fire Department`, gives the Chief and
Deputy Chief, then `Career Firefighters` across A and B shifts, then `Call Firefighters`.

BOTH ARE SET IN TWO COLUMNS, which is why this needs the word geometry and not the
flattened text: `Sgt. John Morreale` on the Day Shift sits beside `Sgt. Va...` on the
Evening Shift, and read as one line they are one person with a nonsense name. The column
machinery is imported from `extract_personnel` rather than copied, because two readers of
one page layout that disagree is the defect this file exists to fix.

THE SECTION IS THE POINT, not just the count. `10 career and 30-35 on call` -- which the
Fire Department also states in prose -- says nothing about how the career staff are
deployed. The roster does: A shift against B shift, patrol against detectives, and which
assignments exist at all in a given year.
"""
import argparse
import collections
import glob
import csv
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import extract_personnel as P                                   # noqa: E402

WORDS = os.path.join(ROOT, 'sources', 'town-budget', 'ocr', 'words')
OUT = os.path.join(ROOT, 'sources', 'data', 'department-rosters.csv')
FIELDS = ['fy', 'page', 'department', 'section', 'rank', 'name', 'as_printed',
          'roster_check']
STAFFING = os.path.join(ROOT, 'sources', 'data', 'department-staffing.csv')

FIRE_START = re.compile(r'roster of the lunenburg fire', re.I)
POLICE_START = re.compile(r'department personnel\s*:?', re.I)

# The sub-headings each roster prints. A line that is one of these opens a section; it is
# never a person, however much it looks like a title.
SECTIONS = re.compile(
    r'^(administration|patrol bureau|investigative bureau|community policing bureau'
    r'|day shift|evening shift|split shift|night shift|overnight shift'
    r'|career firefighters?|call firefighters?|on[\s-]?call firefighters?'
    r'|per diem|department|auxiliary|dispatch(?:ers)?|school resource)\b', re.I)

# `Sgt.`, `Ofc.`, `Lt.`, `Det.`, `K9 Ofc.`, `Traffic Ofc.`, `SRO`, and the Fire
# department's trailing form `Scott Dillon, Lieutenant/EMT`.
LEADING = re.compile(
    r'^((?:K9|Traffic|Acting|Interim)\s+)?'
    r'(Chief|Deputy\s+Chief|Lt\.?|Lieutenant|Sgt\.?|Sergeant|Ofc\.?|Officer|Det\.?'
    r'|Detective|Capt\.?|Captain|SRO|EMT|AEMT|Paramedic|Firefighter|FF)\.?\s+(.+)$', re.I)
# THE NON-FIGHTING POSTS ARE ON THE ROSTER TOO, and the rank vocabulary had only ranks
# in it. `Karen Weller, Administrative Assistant/EMS Coordinator` and `Rev. Andrew C.
# Burr, Chaplain` are printed among the firefighters in every year and were read as
# nobody -- and in FY2022, where the page break cuts her title to `Karen Weller,
# Administrative`, she was the twelfth of twelve people on the page.
TRAILING = re.compile(r'^(.+?),\s*([A-Za-z/\s]*(?:Chief|Lieutenant|Captain|Sergeant|EMT'
                      r'|AEMT|Paramedic|Firefighter|Officer|Administrative|Admin\.?'
                      r'|Coordinator|Chaplain|Clerk|Dispatcher|Warden|Mechanic)'
                      r'[A-Za-z/\s]*)$', re.I)
TITLED = re.compile(r'^([A-Z][A-Za-z\-\s]{3,40}?):\s*(.+)$')   # `Public Safety Desk Clerk: Evelyn`

NAMEISH = re.compile(r'^[A-Z][A-Za-z.\'\-]+(?:\s+[A-Z][A-Za-z.\'\-]+){1,3}$')
# `Lunenburg Fire Department.` is three capitalised words and matched NAMEISH, so it was
# filed as a person -- and as the ONLY person on FY2011's Police roster, which then
# published a police force of one.
NOISE = re.compile(r'comfort dog|accompanied by|mission statement|^values?$|^\W*$', re.I)
# A SENTENCE ABOUT SOMEBODY IS NOT A ROSTER ENTRY. FY2012's Fire chief came out as
# `Chief | Scott Glenny retired in August`, off a paragraph two columns away from the
# roster, while the roster's own `Patrick A. Sullivan` / `Chief of Department*` sat in
# two separate cells and never joined up.
SENTENCE = re.compile(r'\b(?:retired|resigned|graduated|began|started|served|obtained|'
                      r'elevated|hired|after|during|following)\b', re.I)
# A BODY'S NAME IS NOT A PERSON'S NAME -- but it is only ever tested against the NAME,
# never against the whole line. Applied to the line it rejected
# `Patrick A. Sullivan, Chief of Department`, which is the first row of the Fire
# Department roster in every single year, so the CHIEF was missing from seven of the
# fourteen charts while his deputy stood at the top. Rule 13c: a line that fails a
# matcher is a fact about the matcher.
BODY_NAME = re.compile(r'^(?:[A-Z][A-Za-z.\'\-]+\s+){0,3}'
                       r'(?:department|town|lunenburg|commission|committee|board)\s*\.?$',
                       re.I)


def pages_of(fy):
    """Word rows for the roster pages of one year.

    EVERY word file for the year, not one. The original `fy<y>.rosters.tsv` files were cut
    to page ranges somebody typed, and `scripts/ocr_roster_pages.py` now finds the roster
    pages from the text of the book and reads whatever those ranges missed into
    `fy<y>.extraN.tsv`. Twenty-three pages had never been read at all, including every
    roster in FY2012, FY2013 and FY2025.
    """
    paths = [os.path.join(WORDS, 'fy%s.rosters.tsv' % fy)]
    paths += sorted(glob.glob(os.path.join(WORDS, 'fy%s.extra*.tsv' % fy)))
    paths = [p_ for p_ in paths if os.path.exists(p_)]
    if not paths:
        return {}
    out = collections.defaultdict(list)
    seen = set()
    for path in paths:
        with open(path, encoding='utf-8') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                key = (int(r['page']), r['x'], r['y'], r['text'])
                if key in seen:
                    continue
                seen.add(key)
                x, y = float(r['x']), float(r['y'])
                w, h = float(r['w']), float(r['h'])
                out[int(r['page'])].append(dict(page=int(r['page']), x0=x, x1=x + w,
                                                cy=y + h / 2, text=r['text']))
    return out


# WHICH DEPARTMENT A ROSTER PAGE BELONGS TO, decided by the PAGE and not by one heading.
# `POLICE_START` wanted the words `Department Personnel`, which FY2016 does not print --
# that year runs `POLICE DEPARTMENT`, then `Administrative`, `Patrol Supervisors`,
# `Detectives`. So a roster in a year that words its heading differently was read as no
# roster at all, and the report said the town published nothing.
PAGE_FIRE = re.compile(r'lunenburg fire department|roster of the lunenburg fire'
                       r'|call firefighters?|career firefighters?|fire chief', re.I)
PAGE_POLICE = re.compile(r'lunenburg police department|police department'
                         r'|department personnel|patrol (?:bureau|supervisors?|officers?)'
                         r'|reserve (?:intermittent|police) officers?|chief of police', re.I)


def department_of_page(fy, page):
    """'Fire Department' / 'Police Department' / '' from the page's own text."""
    text = _page_text(fy).get(page, '')
    fire, police = len(PAGE_FIRE.findall(text)), len(PAGE_POLICE.findall(text))
    if not fire and not police:
        return ''
    return 'Fire Department' if fire > police else 'Police Department'


_PAGE_TEXT_CACHE = {}


def _page_text(fy):
    if fy in _PAGE_TEXT_CACHE:
        return _PAGE_TEXT_CACHE[fy]
    path = os.path.join(ROOT, 'sources', 'town-budget', 'pages', 'FY%s.ocr.txt' % fy)
    by_page, page = collections.defaultdict(list), None
    if os.path.exists(path):
        for line in open(path, encoding='utf-8', errors='replace'):
            m = re.match(r'^===PAGE (\d+)===', line)
            if m:
                page = int(m.group(1))
                continue
            if page:
                by_page[page].append(re.sub(r'^\s*\d+\|', '', line).rstrip())
    _PAGE_TEXT_CACHE[fy] = {p: '\n'.join(v) for p, v in by_page.items()}
    return _PAGE_TEXT_CACHE[fy]


def parse(line):
    """(rank, name) from a printed roster line, or None if it is not a person."""
    t = re.sub(r'\s+', ' ', line).strip().strip('*+')
    if not t or NOISE.search(t) or SECTIONS.match(t):
        return None
    got = None
    m = LEADING.match(t)
    if m:
        got = (((m.group(1) or '').strip() + ' ' + m.group(2)).strip(), m.group(3).strip())
    if got is None:
        m = TITLED.match(t)
        if m and NAMEISH.match(m.group(2).strip()):
            got = (m.group(1).strip(), m.group(2).strip())
    if got is None:
        m = TRAILING.match(t)
        if m and NAMEISH.match(m.group(1).strip()):
            got = (m.group(2).strip(), m.group(1).strip())
    if got is None and NAMEISH.match(t):
        got = ('', t)
    if got is None or BODY_NAME.match(got[1]) or SENTENCE.search(got[1]):
        return None
    return got


def read_year(fy):
    # ONLY THE PAGES THE FINDER ENDORSES. The word files are appended to as pages are
    # read, and an early run of `ocr_roster_pages.py` captured the front-of-book officials
    # listing before that was excluded -- FY2014's Police roster came back as 62 people
    # and FY2023's as 53, each the department's own roster plus the listing. Filtering
    # here means a page captured in error stops counting the moment the finder stops
    # asking for it, rather than having to be deleted by hand.
    import ocr_roster_pages as F
    wanted = set(F.pages_with_rosters(fy))
    rows = []
    for page, words in sorted(pages_of(fy).items()):
        if wanted and page not in wanted:
            continue
        wrows = P.rows_of(words)
        entries = P.read_order(page, P.cells_of(wrows))
        # The page decides the department; an inline heading can still switch it, because
        # one page occasionally carries the end of one roster and the start of the next.
        dept, section = department_of_page(fy, page), ''
        # THE NAME AND THE RANK ON TWO SEPARATE LINES. FY2012 prints the chief as
        # `Patrick A. Sullivan` and `Chief of Department*` in two cells, so the name
        # arrived rankless and the year's chart had no chief at all. A bare rank
        # directly after a bare name belongs to that name.
        texts = [t for _c, t in entries]
        for i, t in enumerate(texts):
            if FIRE_START.search(t):
                dept, section = 'Fire Department', ''
                continue
            if POLICE_START.search(t):
                dept, section = 'Police Department', ''
                continue
            if not dept:
                continue
            if SECTIONS.match(t.strip()):
                section = re.sub(r'\s+', ' ', t.strip()).title()
                continue
            got = parse(t)
            if got and not got[0] and i + 1 < len(texts):
                nxt = re.sub(r'\s+', ' ', texts[i + 1]).strip().strip('*+')
                if RANK_ONLY.match(nxt):
                    got = (CHIEF_OF.sub('Chief of Department', nxt), got[1])
            if got:
                rows.append(dict(fy=fy, page=page, department=dept, section=section,
                                 rank=CHIEF_OF.sub('Chief of Department', got[0]),
                                 name=got[1], as_printed=t.strip()[:120]))
    return _prefer_ranked(rows)


# A LINE THAT IS NOTHING BUT A RANK.
RANK_ONLY = re.compile(r'^(?:Chief of(?:\s+Departmen\w*)?|Deputy Chief(?:/\w+)?|Chief|'
                       r'(?:Capt(?:ain)?|Lt\.?|Lieutenant|Sgt\.?|Sergeant|Det(?:ective)?|'
                       r'Officer|Firefighter|FF|EMT|AEMT|Paramedic)(?:[/\w. -]{0,14})?)$',
                       re.I)

# `Chief of`, `Chief of Departmentt`, `Chief of Department+*` -- one post, four scans.
CHIEF_OF = re.compile(r'^chief\s+of(?:\s+departmen\w*)?$', re.I)


def _prefer_ranked(rows):
    """One row per person per page, and the one carrying a RANK wins.

    THE LETTERHEAD IS NOT A ROSTER ENTRY. Every Fire Department page opens with the
    department's own letterhead -- `FIRE DEPARTMENT / CHIEF / Patrick A. Sullivan / 655
    Massachusetts Ave` -- and the column reader hands back `Patrick A. Sullivan` with no
    rank beside it, three cells before the roster's own `Patrick A. Sullivan, Chief of
    Department*`. Deduplicating on the name alone kept whichever came first, which is the
    letterhead, so FY2017's chart had the Deputy Chief at the top of the department.
    """
    best = {}
    for r in rows:
        k = (r['fy'], r['department'], r['page'], r['name'].lower())
        if k not in best or (not best[k]['rank'] and r['rank']):
            best[k] = r
    return [r for r in rows if best[(r['fy'], r['department'], r['page'],
                                    r['name'].lower())] is r]


def stated_fire():
    """{fy: (low, high)} — what the Fire Department SAYS its strength is, in prose.

    THE DEPARTMENT DESCRIBES ITSELF TWICE IN THE SAME BOOK, in two independent forms: a
    sentence giving career and on-call counts, and a roster giving every name. They should
    agree, and where they do the year is `checked` -- a reconciliation the document offers
    about itself, which is the only kind this project trusts.

    Where they do not, the roster is short and the year says so rather than being averaged
    in. FY2022 lists 11 names against a stated 40-45 and FY2024 lists 7 police officers
    against 25 the year before: both are pages this reader did not find, not departments
    that shrank by three quarters, and publishing them as a headcount would invent a
    collapse.
    """
    out = {}
    if not os.path.exists(STAFFING):
        return out
    for r in csv.DictReader(open(STAFFING, encoding='utf-8')):
        if r['parsed'] == 'yes' and r['measure'].startswith('career'):
            lo = int(r['career']) + int(r['on_call_low'])
            hi = int(r['career']) + int(r['on_call_high'])
            out.setdefault(r['fy'], (lo, hi))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    # EVERY YEAR THE TOWN PUBLISHED A BOOK, not every year somebody happened to make a
    # `rosters.tsv`. FY2012 and FY2013 have no such file and were therefore not in this
    # loop at all -- two years silently outside the run, which is the join-that-matches-
    # nothing failure in its purest form.
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'sources', 'town-budget', 'pages',
                                           'FY*.ocr.txt'))):
        m = re.search(r'FY(\d{4})\.ocr', f)   # FY2016-addendum.ocr.txt is not a year
        if m:
            rows += read_year(m.group(1))
    # Same name twice on one page is the scanner, not two officers.
    seen, uniq = set(), []
    for r in rows:
        k = (r['fy'], r['department'], r['name'].lower())
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    rows = uniq
    # A HANDFUL OF NAMES IS NOT A ROSTER. Either the page was misread or it was never a
    # roster; either way publishing it would say the department shrank to almost nothing.
    MIN_ROSTER = 5
    counts = collections.Counter((r['fy'], r['department']) for r in rows)
    dropped = sorted(k for k, n in counts.items() if n < MIN_ROSTER)
    rows = [r for r in rows if counts[(r['fy'], r['department'])] >= MIN_ROSTER]
    for fy, dept in dropped:
        print('  dropped FY%s %s -- only %d name(s), not a roster'
              % (fy, dept, counts[(fy, dept)]))
    # Reconcile the Fire roster against the Fire Department's own stated strength.
    stated = stated_fire()
    per_dept = collections.Counter((r['fy'], r['department']) for r in rows)
    for r in rows:
        if r['department'] != 'Fire Department' or r['fy'] not in stated:
            r['roster_check'] = 'no check'
            continue
        lo, hi = stated[r['fy']]
        n = per_dept[(r['fy'], r['department'])]
        r['roster_check'] = ('checked' if lo - 3 <= n <= hi + 3
                             else 'short of the strength the department states')
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
    per = collections.Counter((r['fy'], r['department']) for r in rows)
    print('%d named staff across %d years' % (len(rows), len({r['fy'] for r in rows})))
    st = stated_fire()
    for (fy, d), n in sorted(per.items()):
        note = ''
        if d == 'Fire Department' and fy in st:
            lo, hi = st[fy]
            note = ('  states %d-%d%s' % (lo, hi, '' if lo - 3 <= n <= hi + 3 else '  SHORT'))
        print('  FY%s %-20s %3d%s' % (fy, d, n, note))
    if a.check:
        cur = open(OUT, encoding='utf-8', newline='').read() if os.path.exists(OUT) else ''
        if cur != buf.getvalue():
            print('  STALE — run: python3 scripts/extract_department_rosters.py')
            return 1
        print('  department-rosters.csv is current')
        return 0
    open(OUT, 'w', encoding='utf-8', newline='').write(buf.getvalue())
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
