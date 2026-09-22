#!/usr/bin/env python3
"""Every department's staffing, read from ITS OWN PAGES, for every year it reported.

    python3 scripts/extract_staffing_by_section.py [--check]

Writes `sources/data/staffing-by-section.csv`: one row per department per year it filed a
report, with a count where the pages give one and a stated REASON where they do not.

TJ, 22 September 2026: *"i dont want to have to keep asking TBH... just capture it all.
you dont need me to push you forward."*

WHY THIS EXISTS RATHER THAN MORE TRIGGERS. The old reader scanned the whole book for
sentences matching a pattern, so a department's staffing was found only if that year's
department head happened to phrase it the way the pattern expected. Every gap then looked
the same and none of them said why. Six real shapes turned up one at a time, each after
TJ opened the book himself:

    a roster of names in one sentence          Council on Aging, twelve years
    an establishment, post by post             DPW
    the same establishment, one article each   Assessing office
    a count spelled out in words               the Library, in a clause about turnover
    a list of names under a colon              Building Department, FY2020
    the same four people as flowing prose      Building Department, FY2021 and FY2022

Reading a department's OWN pages inverts the problem. The town's contents page says where
each department's report is (`scripts/extract_report_index.py`), so every department-year
is visited whether or not its wording is one we have seen, and a year with no count comes
back with a reason rather than with silence.
"""
import argparse
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import extract_department_staffing as S                         # noqa: E402

PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
INDEX = os.path.join(ROOT, 'sources', 'data', 'report-index.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'staffing-by-section.csv')
FIELDS = ['fy', 'department', 'pages', 'people', 'form', 'reason', 'evidence']

# Pages that are a TABLE rather than a department's report -- the balance sheet, the
# fund details, the wage list. They belong to an office, they are not its staffing.
NOT_A_REPORT = re.compile(
    r'balance sheet|fund balance|revenue chart|appropriations summary|receivables'
    r'|outstanding debt|repayment schedule|gross wages|town meeting|election results'
    r'|vital|profile|in memoriam|officials|town office|trust fund|capital project'
    r'|special revenue|collection of taxes|classification of accounts'
    r'|bonded indebtedness|indebtedness|cash as of|summary$', re.I)

# A person thanked is not a person employed. These open a sentence that names people the
# department does NOT employ, and they are the main way a roster reader over-counts.
THANKS = re.compile(r'\bthank|\bgratitude|\bappreciat|\bwelcome[sd]?\b|\bcongratulat'
                    r'|\bretir|\bin memoriam|\bpassed away|\bcondolence', re.I)


def _cut_before_own(lines, name):
    """Drop everything before this department's own heading, when it appears."""
    head = re.compile(r'^%s\b' % re.escape(name[:28]), re.I)
    for i, ln in enumerate(lines):
        flat = re.sub(r'\s+', ' ', ln).strip()
        if flat and len(flat) < 60 and head.match(flat):
            return lines[i:]
    return lines


def _cut_at_next(lines, next_name):
    """Drop everything from the next department's own heading onward."""
    if not next_name:
        return lines
    head = re.compile(r'^%s\b' % re.escape(next_name[:28]), re.I)
    for i, ln in enumerate(lines):
        flat = re.sub(r'\s+', ' ', ln).strip()
        if flat and len(flat) < 60 and head.match(flat):
            return lines[:i]
    return lines


def page_text(fy):
    by, page = collections.defaultdict(list), None
    path = os.path.join(PAGES, 'FY%s.ocr.txt' % fy)
    if not os.path.exists(path):
        return {}
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        if page:
            by[page].append(re.sub(r'^\s*\d+\|', '', line).rstrip())
    return by


def sentences(lines):
    """The section's text as single-spaced lines, and as joined paragraphs."""
    flat = [re.sub(r'\s+', ' ', ln).strip() for ln in lines]
    flat = [f for f in flat if f]
    joined = []
    buf = ''
    for f in flat:
        buf = (buf + ' ' + f).strip()
        if f.endswith('.') and not S.ABBREV_END.search(f):
            joined.append(buf)
            buf = ''
    if buf:
        joined.append(buf)
    return flat, joined


def read_section(fy, dept, lines):
    """(people, form, evidence) for one department's own pages, or (None, reason, '')."""
    flat, joined = sentences(lines)

    # 1. A STATED HEADCOUNT, in words or figures -- unless it is an on-call rota.
    for s_ in joined:
        hc = S.HEADCOUNT.search(s_)
        if hc and not S.NOT_A_HEADCOUNT.search(s_):
            return (S.count(hc.group(1) or hc.group(2)),
                    'a stated headcount', s_[:200])

    # 2. FIRE'S OWN FORM: a career count beside an on-call range.
    for s_ in joined:
        f = S.FIRE.search(s_)
        if f:
            return (S.count(f.group(1)) + int(f.group(2)),
                    'career staff plus the low end of the on-call range', s_[:200])

    # 3. AN ESTABLISHMENT, POST BY POST -- numbered posts inside a list opener.
    for s_ in joined:
        if S.NAMED_LIST.search(s_) and not S.BOARDISH.search(s_):
            posts = [(S.count(a), b.strip()) for a, b in S.POST.findall(s_)]
            posts = [(n, w) for n, w in posts if n and len(w) > 3]
            if len(posts) > 1:
                return (sum(n for n, _w in posts),
                        'an establishment, post by post', s_[:200])

    # 4. A NAMED LIST, counted by name.
    for s_ in joined:
        m = S.NAMED_LIST.search(s_)
        if m and not S.BOARDISH.search(s_) and not THANKS.search(s_[:m.start() + 40]):
            people = S.named_people(s_[m.end():])
            if len(people) >= 2:
                return (len(people), 'a named staff list', s_[:200])
            posts = [w.strip() for w in S.ARTICLE_POST.findall(s_[m.end():])
                     if len(w.strip()) > 3]
            if len(posts) >= 2:
                return (len(posts), 'an establishment, one post at a time', s_[:200])

    # 5. A ROSTER LAID OUT AS BIOGRAPHIES -- `Name - Role`, then bulleted notes.
    names = []
    for i, f in enumerate(flat):
        if not S.TEAM_OPENER.search(f):
            continue
        for g in flat[i + 1:i + 1 + S.BIO_WINDOW]:
            if S.HEADING.match(g):
                break
            m = S.BIO_ENTRY.match(g)
            if m and not re.search(r'\d', m.group(2)) and m.group(1) not in names:
                names.append(m.group(1))
    if len(names) >= 2:
        return (len(names), 'a named roster, one biography per person',
                '; '.join(names)[:200])

    # NOTHING. Say which of the two kinds of nothing it is, because they are different
    # problems: a report that never mentions its staff, and one that talks about staff
    # without ever giving a number.
    talks = [f for f in flat if re.search(r'\bstaff\b|\bemploy|\bpersonnel\b', f, re.I)]
    if talks:
        return (None, 'mentions staff, states no number', talks[0][:200])
    return (None, 'no mention of staff on its own pages', '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(INDEX):
        print('run scripts/extract_report_index.py first')
        return 1
    idx = [r for r in csv.DictReader(open(INDEX, encoding='utf-8'))
           if r['state'] == 'report' and r['pdf_from']
           and not NOT_A_REPORT.search(r['department'])]
    # Each entry needs to know which report follows it in the book.
    by_year = collections.defaultdict(list)
    for r in idx:
        by_year[r['fy']].append(r)
    for fy, rs in by_year.items():
        rs.sort(key=lambda r: (int(r['pdf_from']), int(r['pdf_to'])))
        for a_, b_ in zip(rs, rs[1:]):
            a_['_next'] = b_['department']
    cache, rows = {}, []
    for r in idx:
        fy = r['fy']
        if fy not in cache:
            cache[fy] = page_text(fy)
        lo, hi = int(r['pdf_from']), int(r['pdf_to'])
        lines = []
        for p in range(lo, hi + 1):
            lines += cache[fy].get(p, [])
        # TWO DEPARTMENTS CAN SHARE A PAGE, and FY2025's contents gives Conservation
        # Commission and the Council on Aging the SAME range -- it prints `Pages 44-43`
        # for one of them, transposed, so the two overlap completely. A report ends where
        # the next one's heading begins, so the section is cut there rather than at the
        # page boundary the contents claims.
        # AND CUT THE FRONT TOO. A report starts partway down a page, so the pages its
        # range names also carry the END of the report before it: FY2022's Cemetery
        # Commission section opened with the Building Department's staff sentence and
        # published Casey Burlingame as a Cemetery employee.
        lines = _cut_before_own(lines, r['department'])
        lines = _cut_at_next(lines, r.get('_next') or '')
        if not lines:
            rows.append(dict(fy=fy, department=r['department'],
                             pages='%d-%d' % (lo, hi), people='', form='',
                             reason='pages not in our text of the book', evidence=''))
            continue
        people, form, ev = read_section(fy, r['department'], lines)
        rows.append(dict(fy=fy, department=r['department'], pages='%d-%d' % (lo, hi),
                         people='' if people is None else people,
                         form=form if people is not None else '',
                         reason='' if people is not None else form,
                         evidence=ev))
    rows.sort(key=lambda r: (r['department'], r['fy']))
    if a.check:
        old = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        if len(old) != len(rows) or any(
                any(str(r[k]) != o[k] for k in FIELDS) for r, o in zip(rows, old)):
            print('STALE %s' % OUT)
            return 1
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    got = [r for r in rows if r['people'] != '']
    print('%d department-years visited; %d gave a number' % (len(rows), len(got)))
    for reason, n in collections.Counter(
            r['reason'] for r in rows if r['reason']).most_common():
        print('  %-44s %d' % (reason, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
