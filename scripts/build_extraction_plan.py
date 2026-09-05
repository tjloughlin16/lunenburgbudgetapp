#!/usr/bin/env python3
"""Which tables to extract, in what order, derived from the catalogue.

The catalogue (`sources/data/annual-report-catalogue.csv`, 848 blocks found by reading all
sixteen reports end to end) says what exists. This says what to do about it, and the
ordering is not a matter of taste:

**A table with a printed total can be checked against itself. One without can be
transcribed and never verified.** That is the difference between a figure this project may
publish and one it may only record, so it is the first sort key. Years covered is the
second, because a series is worth more than a snapshot.

Nothing here decides that a table is worth having -- the reading already did that. This
turns 848 rows into a queue.

    python3 scripts/build_extraction_plan.py
"""

import collections
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGUE = os.path.join(ROOT, 'sources', 'data', 'annual-report-catalogue.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'extraction-plan.csv')
MD = os.path.join(ROOT, 'notes', 'generated', 'EXTRACTION-PLAN.md')

# The datasets, and what identifies each one. Matched against the reader's plain-English
# name and the printed heading together, because a year that prints no heading is still
# described.
#
# `exclude` matters as much as `match`: the special revenue schedules carry a Receipts
# COLUMN and were pulled into the receipts extractor twice before being excluded by name.
DATASETS = [
    ('receipts',         r'receipts', r'special revenue|general fund revenues|new growth|'
                                      r'assessment|trust|capital|enterprise|balance sheet'),
    ('appropriations',   r'appropriation|classification of accounts|omnibus|'
                         r'expenditure ledger|general fund expenditure', r'chart|percentage'),
    ('special_revenue',  r'special revenue', r''),
    ('trust_funds',      r'trust fund', r'commission'),
    ('debt',             r'debt|bonded indebtedness|bond anticipation', r'chart'),
    ('capital_projects', r'capital project', r''),
    ('gross_wages',      r'gross wage|wages paid|employee compensation|payroll report|'
                         r'employee earnings|salaries paid',
                         r'schedule|grade|step|plan|appropriation|classification|'
                         r'town meeting|article'),
    ('elections',        r'election|ballot|precinct|vote tally',
                         r'wage|salar|appropriation|classification'),
    ('officials',        r'official|committee|board member|roster', r'school|primary|'
                                                                    r'turkey|middle|high|thes'),
    ('school_rosters',   r'roster|faculty', r'fire|police|dpw|official|committee'),
    ('valuation',        r'valuation|assessor|abstract of assessment|new growth|tax rate',
                         r'receipts|revenue|appropriation|special revenue|trust|'
                         r'balance sheet|capital'),
    ('vital_records',    r'vital|birth|death|marriage', r''),
    ('dept_activity',    r'permit|inspection|call|incident|circulation|arrest|burial|'
                         r'interment', r''),
    ('enrollment_mcas',  r'mcas|enrollment|student', r''),
    ('monty_tech',       r'monty tech|montachusett', r''),
]


def main():
    rows = list(csv.DictReader(open(CATALOGUE)))
    plan, seen = [], set()

    for name, match, exclude in DATASETS:
        for r in rows:
            # Match on IDENTITY only -- what the table is called and what its heading
            # says. Never on `what_it_is`, which is a sentence describing the table and
            # will mention half the book.
            #
            # Matching the description assigned 193 of the 382 `valuation` rows to
            # RECEIPTS pages, because the sentence describing a receipts table mentions
            # assessments. The extractor then forced the valuation shape onto a receipts
            # page and produced rows that carry real figures paired with the wrong labels.
            # That is worse than a missing row: a missing row shifts nothing, while a
            # scrambled row asserts something false.
            ident = f"{r['name']} {r['printed_heading']}"
            if not re.search(match, ident, re.I):
                continue
            if exclude and re.search(exclude, ident, re.I):
                continue
            key = (r['edition'], r['pages'], r['name'])
            if key in seen:
                continue
            seen.add(key)
            plan.append({
                'dataset': name, 'fy': r['fy'], 'edition': r['edition'],
                'pages': r['pages'], 'printed_heading': r['printed_heading'],
                'table': r['name'], 'grain': r['grain'],
                'printed_total': r['printed_total'],
                'checkable': 'yes' if r['printed_total'] else 'no',
                'extractable': r['extractable'], 'rows': r['approx_rows'],
                'notes': r['notes'][:300],
            })

    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(plan[0].keys()))
        w.writeheader()
        w.writerows(plan)

    agg = collections.defaultdict(lambda: {'years': set(), 'anchored': set(),
                                           'rows': 0, 'clean': 0, 'n': 0})
    for p in plan:
        a = agg[p['dataset']]
        a['years'].add(str(p['fy']))
        a['n'] += 1
        if p['checkable'] == 'yes':
            a['anchored'].add(str(p['fy']))
        try:
            a['rows'] += int(p['rows'] or 0)
        except ValueError:
            pass
        if (p['extractable'] or '').startswith('clean'):
            a['clean'] += 1

    order = sorted(agg.items(),
                   key=lambda kv: (-len(kv[1]['anchored']), -len(kv[1]['years'])))
    print(f'{"dataset":<20}{"years":>6}{"checkable":>11}{"tables":>8}{"rows~":>8}'
          f'{"clean":>7}')
    for name, a in order:
        print(f'{name:<20}{len(a["years"]):>6}{len(a["anchored"]):>11}{a["n"]:>8}'
              f'{a["rows"]:>8}{a["clean"]:>7}')

    L = ['# What to extract, and in what order', '',
         '**Generated by `scripts/build_extraction_plan.py`. Do not edit.**', '',
         'Derived from `sources/data/annual-report-catalogue.csv` — 848 blocks of',
         'structured data found by reading all sixteen annual town reports end to end.', '',
         '## The ordering is not a preference', '',
         '**A table with a printed total can be checked against itself. One without can be',
         'transcribed and never verified.** That decides whether a figure may be published',
         'or only recorded, so `checkable` sorts first and years covered second.', '',
         'The receipts extraction shows why it matters: FY2018 came out at $119,723,580.93',
         'and looked entirely plausible for a town with a $46M budget. It was wrong by a',
         'factor of three, and the only thing that said so was the $40,193,021.76 the',
         'report prints on the same page.', '',
         '| dataset | years | of which checkable | tables | approx rows |',
         '|---|---:|---:|---:|---:|']
    for name, a in order:
        L.append(f'| `{name}` | {len(a["years"])} | {len(a["anchored"])} | {a["n"]} '
                 f'| {a["rows"]} |')
    L += ['', '## Per table', '',
          'Full detail is in `sources/data/extraction-plan.csv`: every page range, the',
          'heading as printed that year, what one row means, and the total to reconcile',
          'against where one exists.', '']
    os.makedirs(os.path.dirname(MD), exist_ok=True)
    with open(MD, 'w') as fh:
        fh.write('\n'.join(L) + '\n')
    print(f'\n{len(plan)} table instances queued')
    print(f'wrote {os.path.relpath(OUT, ROOT)}')
    print(f'wrote {os.path.relpath(MD, ROOT)}')


if __name__ == '__main__':
    main()
