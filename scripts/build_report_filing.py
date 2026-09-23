#!/usr/bin/env python3
"""DOES THIS BODY FILE AN ANNUAL REPORT? Per body, per year, from the town's own contents.

    python3 scripts/build_report_filing.py [--check]

Writes `sources/data/report-filing.csv` and `fy28/public/data/report-filing.json`.

TJ, 22 September 2026: *"on each board/commission/department page, lets have a label if
they file an Annual Report."*

THE TOWN ALREADY ANSWERS THIS AND IT IS THE ONLY PLACE IT DOES. The contents page of each
annual report lists every body and, beside the ones that sent nothing, prints `No Report
Submitted` in the town's own words. 612 filings and 40 of those refusals across fourteen
books.

THREE STATES, AND THE DIFFERENCE BETWEEN THEM IS THE POINT:

  filed        the contents page gives it a page range
  said none    the contents page prints `No Report Submitted` beside its name. The body
               was asked, and the town recorded that it did not answer
  not listed   the body is not on the contents page at all that year

`not listed` is NOT a quieter version of `said none`. A body the town did not ask has not
refused anything, and four departments -- Accounting, Human Resources, Land Use,
Facilities -- are never on a contents page in any year while plainly existing, with their
own phone numbers on the town's staff directory. Reading their silence as a refusal would
be a statement about them rather than about the document.

AND FILING IS NOT PERFORMANCE. A board that meets four times a year and files nothing is
not failing at anything a statute names; the annual report is a convention, not a duty
this project can point at a law for. What the label says is what the town printed.
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
INDEX = os.path.join(DATA, 'report-index.csv')
ORG = os.path.join(DATA, 'org-chart.csv')
OUT = os.path.join(DATA, 'report-filing.csv')
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'report-filing.json')
FIELDS = ['body', 'slug', 'years_filed', 'years_said_none', 'first_filed', 'last_filed',
          'filed', 'said_none', 'of_years', 'org_chart_unit']

# A contents entry that is a TABLE rather than a body -- the same list the coverage work
# uses, because the contents page prints the balance sheet beside the Cemetery Commission.
NOT_A_BODY = re.compile(r'balance|receipt|indebted|collection of taxes|revenue fund|'
                        r'capital project|debt|wages|officials|profile|summary|hours|'
                        r'classification|vital|meeting|election|omnibus|memoriam|'
                        r'compensation|roll-forward|detail|excerpt|contents|^page', re.I)


def slugify(name):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', name.lower())).strip('-')


def key(name):
    """A body's name reduced to what does not vary between the two lists."""
    n = re.sub(r'\s*\((staff|board|schools|appointed post)\)$', '', name, flags=re.I)
    return re.sub(r'[^a-z]', '',
                  re.sub(r'\b(the|of|and|lunenburg|department|town|report)\b', '',
                         n.lower()))


def build():
    idx = [r for r in csv.DictReader(open(INDEX, encoding='utf-8'))
           if len(r['department'].strip()) > 3 and not NOT_A_BODY.search(r['department'])]
    years = sorted({r['fy'] for r in idx})

    # THE BODY'S NAME AS THE ORG CHART KNOWS IT, so a page can join on one thing. The
    # contents page and the officials listing spell the same body differently, and the
    # org chart has already reconciled them -- reconciling them a second time here would
    # be two answers to one question, which is how this project gets its defects.
    org = {}
    if os.path.exists(ORG):
        for r in csv.DictReader(open(ORG, encoding='utf-8')):
            org.setdefault(key(r['unit']), r['unit'])

    filed, none = collections.defaultdict(set), collections.defaultdict(set)
    printed = {}
    for r in idx:
        k = key(r['department'])
        printed.setdefault(k, r['department'].strip())
        (none if r['state'] == 'no report submitted' else filed)[k].add(r['fy'])

    out = []
    for k in sorted(set(filed) | set(none)):
        f, n = sorted(filed[k]), sorted(none[k])
        name = org.get(k) or printed[k]
        out.append(dict(body=name, slug=slugify(name),
                        years_filed=';'.join(f), years_said_none=';'.join(n),
                        first_filed=f[0] if f else '', last_filed=f[-1] if f else '',
                        filed=len(f), said_none=len(n), of_years=len(years),
                        org_chart_unit=org.get(k, '')))
    out.sort(key=lambda r: (-r['filed'], r['body'].lower()))
    return out, years


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, years = build()
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
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(dict(generated_by='scripts/build_report_filing.py', years=years,
                   bodies=rows),
              open(OUT_JSON, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    joined = sum(1 for r in rows if r['org_chart_unit'])
    every = sum(1 for r in rows if r['filed'] == len(years))
    print('%d bodies across %d years; %d join to a unit in the org chart'
          % (len(rows), len(years), joined))
    print('  %d filed in every year the town published' % every)
    print('  %d said `No Report Submitted` at least once'
          % sum(1 for r in rows if r['said_none']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
