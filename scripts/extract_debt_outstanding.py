#!/usr/bin/env python3
"""What the town owes, and for what — the Five Years Outstanding Debt table, every year.

    python3 scripts/extract_debt_outstanding.py
    python3 scripts/extract_debt_outstanding.py --check

Writes `sources/data/debt-outstanding.csv`.

TJ: *"well, then we need a bond report."* This is the half of it the annual reports print
plainly: not which bond finishes when, but how much the town owes and what it borrowed the
money FOR — sewers, schools, water, roads, athletic facilities, departmental equipment —
split inside and outside the general debt limit that Chapter 44 sets.

FINDING IT WAS THE WHOLE PROBLEM, and it is worth writing down because it cost this
project twelve years of data. Every annual report lists `Five Year Outstanding Debt` in its
CONTENTS, so searching for the title returns page 3 or page 4 in twelve years running and
the table itself in none of them. It is found here by rows that appear only on the table:
`Outside the General Debt Limit`, `Total Long-Term Indebtedness`. Page 75 in FY2011, page
37 in FY2025.

AND IN SEVERAL YEARS ANOTHER TABLE SHARES THE PAGE -- FY2025 prints the trust and
stabilization funds above it -- so an extractor reading top to bottom files bank names as
bonds, which is exactly what the previous debt dataset contained.

TWO IDENTITIES, AND THE SECOND IS THE UNUSUAL ONE.

  1. PER COLUMN: `Total Within` + `Total Outside` = `Total Long-Term Indebtedness`. The
     table states it in every one of its five year columns, so a column that ties is a
     column read correctly, and a column that does not says which of the three is wrong.

  2. ACROSS REPORTS: each report prints FIVE fiscal years, so any given year appears in
     five different books. FY2015's table and FY2019's table both state what was
     outstanding in FY2015, printed four years apart from the same ledger. They should
     agree to the dollar. Where they do not, one of the two readings is wrong and neither
     is published as though it were settled -- a cross-check almost nothing else in this
     archive has, because almost nothing else is printed twice.
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

import pdf_tables as T                                          # noqa: E402

PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
OUT = os.path.join(ROOT, 'sources', 'data', 'debt-outstanding.csv')
FIELDS = ['report_fy', 'page', 'as_of_fy', 'section', 'category', 'amount', 'column_check']

# Rows that appear ONLY on this table, never on a contents page.
MARKER = re.compile(r'Outside the General Debt Limit|Total Long-Term Indebtedness', re.I)
HEADING = re.compile(r'FIVE\s+YEARS?\s+OUTSTANDING\s+DEBT', re.I)
INSIDE = re.compile(r'^(within|inside) the general debt limit', re.I)
OUTSIDE = re.compile(r'^outside the general debt limit', re.I)
SHORT = re.compile(r'^short[- ]term indebtedness', re.I)
TOT_IN = re.compile(r'^total (within|inside) the general debt limit', re.I)
TOT_OUT = re.compile(r'^total outside the general debt limit', re.I)
TOT_LONG = re.compile(r'^total long[- ]term indebtedness', re.I)
YEARS = re.compile(r'\b(20\d\d)\b')


def page_lines(path):
    page = None
    for raw in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', raw)
        if m:
            page = int(m.group(1))
            continue
        yield page, re.sub(r'^\s*\d+\|', '', raw.rstrip('\n'))


def find_page(path):
    """The page the table is ON, by its own rows rather than its title."""
    hits = collections.Counter()
    for page, t in page_lines(path):
        if page and MARKER.search(t):
            hits[page] += 1
    return max(hits, key=hits.get) if hits else None


def read_year(fy, path):
    page = find_page(path)
    if not page:
        return [], ['FY%s: the table was not found' % fy]
    lines = [t for p, t in page_lines(path) if p == page]
    # TRIM TO THE HEADING, because another table may share the page above it.
    for i, t in enumerate(lines):
        if HEADING.search(t):
            lines = lines[i:]
            break

    # The year columns, left to right, off the first line that is mostly years.
    cols = []
    for t in lines[:8]:
        found = YEARS.findall(t)
        if len(found) >= 3 and 'june' not in t.lower():
            cols = found
            break
    if not cols:
        return [], ['FY%s: no year header row on page %d' % (fy, page)]

    rows, section, totals = [], '', {}
    for t in lines:
        label = re.sub(r'\s{2,}.*$', '', t).strip(' .$')
        if not label:
            continue
        if INSIDE.match(label) and not TOT_IN.match(label):
            section = 'inside the debt limit'
            continue
        if OUTSIDE.match(label) and not TOT_OUT.match(label):
            section = 'outside the debt limit'
            continue
        if SHORT.match(label):
            section = 'short-term'
            continue
        vals = [T.amount(x) for x in T.MONEY.findall(t)]
        vals = [v for v in vals if v is not None]
        if not vals or not re.search(r'[A-Za-z]{3}', label):
            continue
        for key, pat in (('within', TOT_IN), ('outside', TOT_OUT), ('long', TOT_LONG)):
            if pat.match(label):
                totals[key] = vals
        for i, v in enumerate(vals[:len(cols)]):
            rows.append(dict(report_fy=fy, page=page, as_of_fy=cols[i],
                             section=section or 'unsectioned',
                             category=re.sub(r'\s+', ' ', label), amount='%.2f' % v,
                             column_check=''))

    # THE IDENTITY, PER COLUMN.
    problems, state = [], {}
    for i, col in enumerate(cols):
        a = totals.get('within', [None] * 9)[i] if i < len(totals.get('within', [])) else None
        b = totals.get('outside', [None] * 9)[i] if i < len(totals.get('outside', [])) else None
        c = totals.get('long', [None] * 9)[i] if i < len(totals.get('long', [])) else None
        if a is None or b is None or c is None:
            state[col] = 'no check'
            continue
        if abs(a + b - c) <= 1.0:
            state[col] = 'checked'
        else:
            state[col] = 'check failed'
            problems.append('FY%s column %s: within %s + outside %s = %s, printed %s'
                            % (fy, col, f'{a:,.0f}', f'{b:,.0f}', f'{a + b:,.0f}',
                               f'{c:,.0f}'))
    for r in rows:
        r['column_check'] = state.get(r['as_of_fy'], 'no check')
    return rows, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, problems = [], []
    for f in sorted(glob.glob(os.path.join(PAGES, 'FY*.ocr.txt'))):
        fy = re.search(r'FY(\d{4})', f).group(1)
        got, probs = read_year(fy, f)
        rows += got
        problems += probs

    # THE CROSS-REPORT CHECK: one fiscal year, printed in up to five different books.
    seen = collections.defaultdict(dict)
    for r in rows:
        if TOT_LONG.match(r['category']):
            seen[r['as_of_fy']][r['report_fy']] = float(r['amount'])
    agree = disagree = 0
    for yr, by_report in sorted(seen.items()):
        vals = {round(v) for v in by_report.values()}
        if len(by_report) < 2:
            continue
        if len(vals) == 1:
            agree += 1
        else:
            disagree += 1
            problems.append('FY%s total long-term is printed %s by %s'
                            % (yr, ' and '.join(f'{v:,.0f}' for v in sorted(vals)),
                               ' and '.join('FY' + k for k in sorted(by_report))))

    by_state = collections.Counter(r['column_check'] for r in rows)
    print('%d rows from %d reports; columns %s'
          % (len(rows), len({r['report_fy'] for r in rows}), dict(by_state)))
    print('  cross-report: %d fiscal years agree across reports, %d do not'
          % (agree, disagree))
    for p in problems[:10]:
        print('  %s' % p)
    if len(problems) > 10:
        print('  ...and %d more' % (len(problems) - 10))

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
    if a.check:
        cur = open(OUT, encoding='utf-8', newline='').read() if os.path.exists(OUT) else ''
        if cur != buf.getvalue():
            print('  STALE — run: python3 scripts/extract_debt_outstanding.py')
            return 1
        print('  debt-outstanding.csv is current')
        return 0
    open(OUT, 'w', encoding='utf-8', newline='').write(buf.getvalue())
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
