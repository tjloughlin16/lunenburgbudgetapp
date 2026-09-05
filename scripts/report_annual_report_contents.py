#!/usr/bin/env python3
"""What data is in each annual town report, year by year, and what could be made of it.

Fifteen years of annual town reports are 2,751 pages, and the useful question is not
"what is in them" but **"which tables exist in which years, are they checkable, and what
would each one become as a table in the database."** That is what this answers.

It reads `sources/data/annual-report-survey.csv` -- the per-page pass -- and groups
consecutive pages carrying the same section into one table instance. For each it reports
the pages, how many rows carry figures, how many columns the rows agree on, and **whether
the report prints a total the table can be reconciled against**, which is the difference
between a table that can be published and one that can only be transcribed.

Two outputs:

  sources/data/annual-report-contents.csv        one row per table instance
  notes/generated/ANNUAL-REPORT-CONTENTS.md      the same thing, readable, by year

Nothing here extracts a figure. It says what is there and what it would take.

    python3 scripts/report_annual_report_contents.py
"""

import collections
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURVEY = os.path.join(ROOT, 'sources', 'data', 'annual-report-survey.csv')
OUT_CSV = os.path.join(ROOT, 'sources', 'data', 'annual-report-contents.csv')
OUT_MD = os.path.join(ROOT, 'notes', 'generated', 'ANNUAL-REPORT-CONTENTS.md')

# What each table would become. The grain is the thing to get right before any of it is
# written: it is what a row in the database means, and it is not always obvious from the
# page -- a receipts page is one row per revenue source, a staff roster is one row per
# position and school and emphatically not one row per person.
SHAPE = {
    'receipts':        ('fy, source, amount',
                        'one row per revenue source per year'),
    'appropriations':  ('fy, department, appropriated, expended, balance',
                        'one row per department per year'),
    'special_revenue': ('fy, fund_number, fund_name, balance, receipts, deficit',
                        'one row per fund per year -- turns fund_activity from a '
                        'snapshot into a history'),
    'capital_project': ('fy, project_number, project_name, balance',
                        'one row per capital project per year'),
    'trust_funds':     ('fy, fund_number, fund_name, balance, income',
                        'one row per trust fund per year'),
    'enterprise':      ('fy, fund, line, amount',
                        'one row per enterprise fund line per year'),
    'balance_sheet':   ('fy, fund_type, line, amount',
                        'one row per balance sheet line per fund type'),
    'debt':            ('fy, issue, principal, interest, maturity',
                        'one row per debt issue per year'),
    'payroll':         ('fy, department, position_count, gross',
                        'AGGREGATE ONLY -- never one row per named person'),
    'staff_roster':    ('fy, school, position, count',
                        'COUNTS, never names. The names stay in the archived PDF'),
    'valuation':       ('fy, class, valuation',
                        'one row per property class per year'),
    'tax_rate':        ('fy, class, rate',
                        'one row per class per year'),
    'town_meeting':    ('(not tabular)', 'votes and articles -- prose, not a table'),
    'school_report':   ('(not tabular)', 'narrative'),
}


def group_runs(pages):
    """Consecutive page numbers, as (first, last) runs."""
    runs, start, prev = [], None, None
    for p in sorted(pages):
        if start is None:
            start = prev = p
        elif p == prev + 1:
            prev = p
        else:
            runs.append((start, prev))
            start = prev = p
    if start is not None:
        runs.append((start, prev))
    return runs


def main():
    rows = list(csv.DictReader(open(SURVEY)))
    by_year_section = collections.defaultdict(list)
    for r in rows:
        for sec in (r['sections'] or '').split('|'):
            if sec:
                by_year_section[(r['fy'], sec)].append(r)

    out = []
    for (fy, sec), pages in sorted(by_year_section.items(),
                                   key=lambda kv: (int(kv[0][0] or 0), kv[0][1])):
        nums = [int(p['page']) for p in pages]
        figure_pages = [p for p in pages if int(p['money'] or 0) > 0]
        totals = [t for p in pages for t in (p['totals'] or '').split(' ; ') if t]
        grand = [t for t in totals if t.upper().startswith('GRAND TOTAL')]
        cols = [int(p['gutters'] or 0) + 1 for p in figure_pages]
        modes = sorted({p['mode'] for p in pages if p['mode']})
        fields, grain = SHAPE.get(sec, ('', ''))
        out.append({
            'fy': fy,
            'table': sec,
            'pages': ','.join(f'{a}-{b}' if a != b else str(a)
                              for a, b in group_runs(nums)),
            'page_count': len(nums),
            'pages_with_figures': len(figure_pages),
            'figure_rows': sum(int(p['rows'] or 0) for p in figure_pages),
            'figures': sum(int(p['money'] or 0) for p in pages),
            'columns': max(cols) if cols else 0,
            'read_by': '+'.join(modes),
            'printed_total': (grand or totals or [''])[0],
            'checkable': 'yes' if (grand or totals) else 'no',
            'csv_fields': fields,
            'grain': grain,
        })

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    write_markdown(out, rows)
    print(f'wrote {os.path.relpath(OUT_CSV, ROOT)}')
    print(f'wrote {os.path.relpath(OUT_MD, ROOT)}')


def write_markdown(out, survey_rows):
    years = sorted({r['fy'] for r in out if r['fy']}, key=int)
    tables = [t for t in SHAPE if any(r['table'] == t for r in out)]
    have = {(r['fy'], r['table']): r for r in out}

    L = ['# What is in the annual town reports, year by year', '',
         '**Generated by `scripts/report_annual_report_contents.py`. Do not edit.**',
         'Derived from `sources/data/annual-report-survey.csv`, which is a per-page pass',
         'over all sixteen reports.', '',
         'Nothing here is an extracted figure. This says which tables exist in which',
         'years, whether the report prints a total they can be checked against, and what',
         'each would become as a table in the database.', '',
         '## The matrix', '',
         'A cell shows the pages carrying figures for that table. **Bold** means the',
         'report prints a total the table can be reconciled against; plain means it does',
         'not, and such a table can be transcribed but never checked.', '']

    L.append('| table | ' + ' | '.join('FY' + y[2:] for y in years) + ' |')
    L.append('|---|' + '---|' * len(years))
    for t in tables:
        cells = []
        for y in years:
            r = have.get((y, t))
            if not r or not r['pages_with_figures']:
                cells.append('·')
            elif r['checkable'] == 'yes':
                cells.append(f"**{r['pages_with_figures']}p**")
            else:
                cells.append(f"{r['pages_with_figures']}p")
        L.append(f'| `{t}` | ' + ' | '.join(cells) + ' |')
    L.append('')
    L.append('`·` means not found. For a year whose pages are scans, that may mean the')
    L.append('table is there and has not been OCR\'d -- the survey records which.')
    L.append('')

    L.append('## What each table would become')
    L.append('')
    L.append('| table | CSV fields | what one row means |')
    L.append('|---|---|---|')
    for t in tables:
        f, g = SHAPE[t]
        L.append(f'| `{t}` | `{f}` | {g} |')
    L.append('')
    L.append('Two of these carry a rule rather than a shape. **`staff_roster` is counts by')
    L.append('position and school, never names** -- the analysis needs "nine paras at')
    L.append('Primary" and has no use for who they are, and storing names creates an')
    L.append('obligation this project does not want. **`payroll` is aggregate only**, for')
    L.append('the same reason. The names stay in the archived PDF where the town put them.')
    L.append('')

    L.append('## By year')
    L.append('')
    for y in years:
        mine = [r for r in out if r['fy'] == y and r['pages_with_figures']]
        pages = [r for r in survey_rows if r['fy'] == y]
        readable = sum(1 for r in pages if r['mode'])
        scans = sum(1 for r in pages if not r['mode'])
        L.append(f'### FY{y}')
        L.append('')
        L.append(f'{len(pages)} pages — {readable} readable, {scans} with no text layer '
                 f'and no OCR.')
        L.append('')
        if not mine:
            L.append('No tables found. If the page count above shows scans, that is why.')
            L.append('')
            continue
        L.append('| table | pages | rows | figures | cols | checkable against |')
        L.append('|---|---|---:|---:|---:|---|')
        for r in sorted(mine, key=lambda r: -r['figures']):
            anchor = r['printed_total'] or '— nothing printed —'
            L.append(f"| `{r['table']}` | {r['pages']} | {r['figure_rows']} | "
                     f"{r['figures']} | {r['columns']} | {anchor} |")
        L.append('')

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, 'w') as fh:
        fh.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
