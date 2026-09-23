#!/usr/bin/env python3
"""HOW MANY OF A DEPARTMENT'S PEOPLE ARE IN THE CHART, and how we know.

    python3 scripts/build_roster_completeness.py [--check]

Writes `sources/data/roster-completeness.csv` and `fy28/public/data/roster-completeness.json`.

TJ, 22 September 2026: *"we need to flag somehow that these department org charts are not
complete. is there a way to KNOW they aren't complete?"* and then: *"i think this means
our org numbers are off too."*

BOTH ARE RIGHT, AND FOR SEVERAL DEPARTMENTS IT IS KNOWABLE RATHER THAN SUSPECTED, because
the town publishes a COUNT in one place and NAMES in another and they are not the same
number. That is the whole mechanism: a shortfall is only a fact when something the town
said supplies the denominator.

THREE BASES, AND EACH IS THE TOWN'S OWN STATEMENT:

  a stated headcount     the Library, FY2019: *"we only employ ten total."* One sentence
                         of prose, and the reason we can say the Library chart names one
                         of ten rather than merely looking thin
  a stated strength      the Fire Department gives career staff plus an on-call range in
                         nearly every year. The LOW end is used, so no department is
                         flattered by its own vagueness
  an establishment       the DPW and the Assessing office publish POSTS and no names at
                         all. Named is zero by construction, and that is not a failure of
                         our reading -- it is what the document is
  the staff directory    for FY2027, the town's own list of who works there

WHAT IS NOT A BASIS. The gross-wages list would be the best denominator in the archive --
every name the town paid -- and it prints a DEPARTMENT beside the name only in FY2014 to
FY2016, and our reader gets it for 156 rows of 2,866. Compared against those, the Fire
Department shows five paid and forty-five named, which is not a finding about the town:
it is our own extraction being 11% complete on that column. It is excluded, and the
exclusion is the point -- a denominator you cannot trust makes a shortfall that is not
there.

AND A SHORTFALL IS NOT A CRITICISM. A department that publishes an establishment is
telling the truth about its posts; a library that reports a headcount and not a staff list
is doing what every library report in this archive does. The number says how much of the
picture this page can draw, and nothing about how the department is run.
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
OUT = os.path.join(DATA, 'roster-completeness.csv')
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'roster-completeness.json')
FIELDS = ['fy', 'unit', 'named', 'stated', 'basis', 'shortfall', 'as_printed']

# The staffing extract names departments its own way; the org chart has reconciled the
# spellings already, so it is the one to join on.
UNIT = {'library': 'Public Library', 'fire': 'Fire Department',
        'fire department': 'Fire Department', 'police department': 'Police Department',
        'police': 'Police Department', 'council on aging': 'Council on Aging (staff)',
        'department of public works': 'Department of Public Works',
        'board of assessors': 'Board Of Assessors (staff)',
        'building': 'Building Department',
        'information technology': 'Information Technology'}


def load(name):
    p = os.path.join(DATA, name)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def build():
    org = load('org-chart.csv')
    named = collections.Counter()
    for r in org:
        if r['person'].strip():
            named[(r['fy'], r['unit'])] += 0
    seen = collections.defaultdict(set)
    for r in org:
        if r['person'].strip():
            seen[(r['fy'], r['unit'])].add(r['person'].strip().lower())

    out = []
    for r in load('department-staffing.csv'):
        if r['parsed'] != 'yes':
            continue
        unit = UNIT.get(r['department'].strip().lower())
        if not unit:
            continue
        n = len(seen.get((r['fy'], unit), ()))
        stated, basis = None, ''
        if r['measure'] == 'a stated headcount' and r['career']:
            stated, basis = int(r['career']), 'the department states a headcount'
        elif r['career'] and r['on_call_low']:
            # THE LOW END OF A RANGE, always. A department that says `40 to 45` is given
            # 40, so none is flattered by its own vagueness.
            stated = int(r['career']) + int(r['on_call_low'])
            basis = 'the department states its career and on-call strength'
        elif 'establishment' in r['measure']:
            stated = len([x for x in r['positions'].split(';') if x.strip()])
            basis = 'the department publishes posts, not people'
        if stated is None:
            continue
        out.append(dict(fy=r['fy'], unit=unit, named=n, stated=stated, basis=basis,
                        shortfall=max(0, stated - n),
                        as_printed=re.sub(r'\s+', ' ', r['statement'])[:160]))

    # FY2027: the town's own directory is the count, and it is the count BECAUSE the
    # chart's FY2027 rows come from nowhere else -- so it says the chart is complete for
    # that year and that source, which is a weaker claim than it looks and is stated as
    # such rather than dressed up.
    seen_units = {(r['fy'], r['unit']) for r in org
                  if r['source'].startswith('town staff directory')}
    for fy, unit in sorted(seen_units):
        n = len(seen.get((fy, unit), ()))
        out.append(dict(fy=fy, unit=unit, named=n, stated=n,
                        basis='the town staff directory lists them', shortfall=0,
                        as_printed='the town’s own staff directory'))

    out.sort(key=lambda r: (r['unit'].lower(), r['fy']))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
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
    json.dump(dict(generated_by='scripts/build_roster_completeness.py', rows=rows),
              open(OUT_JSON, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    short = [r for r in rows if r['shortfall'] > 0]
    print('%d department-years have a count to check the chart against; %d fall short'
          % (len(rows), len(short)))
    for r in sorted(short, key=lambda r: -r['shortfall'])[:12]:
        print('  FY%s %-30s names %2d of %2d  — %s'
              % (r['fy'], r['unit'][:30], r['named'], r['stated'], r['basis']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
