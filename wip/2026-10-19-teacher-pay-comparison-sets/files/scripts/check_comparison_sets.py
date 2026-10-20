#!/usr/bin/env python3
"""The COMPARISON SETS: which districts somebody chose to compare Lunenburg with, and who chose.

    python3 scripts/check_comparison_sets.py           # print each set and its districts
    python3 scripts/check_comparison_sets.py --check   # ...and fail on any row that does not resolve

THE REGISTRY is sources/data/comparison-sets.csv, written by hand from the documents, one row
per (set, district, document that named it). Two sets:

  official      every district the DISTRICT ITSELF named as a comparison, in three documents:
                the Budget Task Force's nine (FY2026 Superintendent's proposed budget, p57), the
                three entered in DESE's RADAR selection cells and the three columns of a DART
                summary (both in the FY2020 proposed budget). A district named in several
                documents has a row for each, so its provenance is all of them.
  project-six   the six THIS PROJECT compares with (scripts/build_school_spending_topics.py).
                No criterion was recorded when it was chosen, and the registry says so.

Not in it: a page headed "Comparable Districts" in the 2025-2026 draft budget book (pdf page
21, an image) reproduces DESE's "FY26 Chapter 70 district summary" for 28 districts,
Lunenburg among them, and states no criterion for choosing them. It is not folded into
`official`, because nothing on it says the district chose those 28 as comparisons.

THE CHECK. Every printed name must resolve to EXACTLY ONE district in DESE's statewide table
(sources/data/dese-teacher-salaries.csv, every district DESE reports), and that district's
code must be the `dese_org_code` the row gives. A printed name resolves by equality after
case, hyphens and spacing are ignored, or through ALIAS below -- each alias a reading
somebody wrote down, because "Nashoba" also prefixes Nashoba Valley Regional Vocational
Technical and a prefix match would be a guess.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, 'sources', 'data', 'comparison-sets.csv')
DESE = os.path.join(ROOT, 'sources', 'data', 'dese-teacher-salaries.csv')
FIELDS = ['set_id', 'set_label', 'chosen_by', 'district_as_printed', 'dese_name',
          'dese_org_code', 'source_doc', 'source_page', 'source_quote', 'fy_of_list', 'criterion']
# Printed name -> DESE's name, where the two are not the same words.
ALIAS = {'ayer shirley': 'Ayer Shirley School District'}
SETS = {'official', 'project-six'}


def fail(msg):
    raise SystemExit('check_comparison_sets: ' + msg)


def norm(s):
    return re.sub(r'\s+', ' ', s.replace('-', ' ')).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    with open(REG, encoding='utf-8', newline='') as fh:
        rd = csv.DictReader(fh)
        if rd.fieldnames != FIELDS:
            fail('columns are %r' % rd.fieldnames)
        rows = list(rd)
    names = {}
    with open(DESE, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            names.setdefault(r['district'], set()).add(r['org_code'])
    by_norm = {}
    for n in names:
        by_norm.setdefault(norm(n), []).append(n)
    seen, problems = set(), []
    for i, r in enumerate(rows, 2):
        if r['set_id'] not in SETS:
            problems.append('line %d: unknown set %r' % (i, r['set_id']))
        key = (r['set_id'], r['dese_org_code'], r['source_doc'])
        if key in seen:
            problems.append('line %d: %s named twice by one document' % (i, r['district_as_printed']))
        seen.add(key)
        p = norm(r['district_as_printed'])
        target = ALIAS.get(p)
        hits = [target] if target in names else by_norm.get(p, [])
        if len(hits) != 1:
            problems.append('line %d: %r resolves to %d DESE districts %r' % (
                i, r['district_as_printed'], len(hits), hits))
            continue
        name = hits[0]
        if name != r['dese_name']:
            problems.append('line %d: %r is DESE %r, the row says %r' % (
                i, r['district_as_printed'], name, r['dese_name']))
        codes = names[name]
        if codes != {r['dese_org_code']}:
            problems.append('line %d: DESE %r carries code(s) %s, the row says %s' % (
                i, name, sorted(codes), r['dese_org_code']))
        doc = r['source_doc']
        if not os.path.exists(os.path.join(ROOT, doc)):
            problems.append('line %d: %s is not on disk' % (i, doc))
        if not r['source_quote'] or not r['chosen_by']:
            problems.append('line %d: no quote or no chooser' % i)
    if problems:
        fail('\n  ' + '\n  '.join(problems))
    for s in sorted({r['set_id'] for r in rows}):
        mine = [r for r in rows if r['set_id'] == s]
        dist = {}
        for r in mine:
            dist.setdefault(r['dese_name'], []).append(os.path.basename(r['source_doc']))
        print('%s: %d districts, %d rows' % (s, len(dist), len(mine)))
        if not a.check:
            for d, docs in sorted(dist.items()):
                print('  %-45s %s' % (d, ', '.join(docs)))
    if a.check:
        print('ok: every name resolves to exactly one DESE district and code')


if __name__ == '__main__':
    main()
