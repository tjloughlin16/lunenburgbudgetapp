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
TRAILING = re.compile(r'^(.+?),\s*([A-Za-z/\s]*(?:Chief|Lieutenant|Captain|Sergeant|EMT'
                      r'|AEMT|Paramedic|Firefighter|Officer)[A-Za-z/\s]*)$', re.I)
TITLED = re.compile(r'^([A-Z][A-Za-z\-\s]{3,40}?):\s*(.+)$')   # `Public Safety Desk Clerk: Evelyn`

NAMEISH = re.compile(r'^[A-Z][A-Za-z.\'\-]+(?:\s+[A-Z][A-Za-z.\'\-]+){1,3}$')
NOISE = re.compile(r'comfort dog|accompanied by|mission statement|^values?$|^\W*$', re.I)


def pages_of(fy):
    """Word rows for the roster pages of one year, from the rosters TSV."""
    path = os.path.join(WORDS, 'fy%s.rosters.tsv' % fy)
    if not os.path.exists(path):
        return {}
    out = collections.defaultdict(list)
    with open(path, encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            x, y, w, h = float(r['x']), float(r['y']), float(r['w']), float(r['h'])
            out[int(r['page'])].append(dict(page=int(r['page']), x0=x, x1=x + w,
                                            cy=y + h / 2, text=r['text']))
    return out


def parse(line):
    """(rank, name) from a printed roster line, or None if it is not a person."""
    t = re.sub(r'\s+', ' ', line).strip().strip('*+')
    if not t or NOISE.search(t) or SECTIONS.match(t):
        return None
    m = LEADING.match(t)
    if m:
        return ((m.group(1) or '').strip() + ' ' + m.group(2)).strip(), m.group(3).strip()
    m = TITLED.match(t)
    if m and NAMEISH.match(m.group(2).strip()):
        return m.group(1).strip(), m.group(2).strip()
    m = TRAILING.match(t)
    if m and NAMEISH.match(m.group(1).strip()):
        return m.group(2).strip(), m.group(1).strip()
    if NAMEISH.match(t):
        return '', t
    return None


def read_year(fy):
    rows = []
    for page, words in sorted(pages_of(fy).items()):
        wrows = P.rows_of(words)
        entries = P.read_order(page, P.cells_of(wrows))
        dept, section = '', ''
        for _col, t in entries:
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
            if got:
                rows.append(dict(fy=fy, page=page, department=dept, section=section,
                                 rank=got[0], name=got[1], as_printed=t.strip()[:120]))
    return rows


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
    rows = []
    for f in sorted(glob.glob(os.path.join(WORDS, 'fy*.rosters.tsv'))):
        rows += read_year(re.search(r'fy(\d{4})\.rosters', f).group(1))
    # Same name twice on one page is the scanner, not two officers.
    seen, uniq = set(), []
    for r in rows:
        k = (r['fy'], r['department'], r['name'].lower())
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    rows = uniq
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
