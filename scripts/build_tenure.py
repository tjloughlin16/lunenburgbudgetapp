#!/usr/bin/env python3
"""HOW LONG PEOPLE STAY, and how many leave — by department, FY2011 to FY2025.

    python3 scripts/build_tenure.py [--check]

Writes `sources/data/tenure.csv`, `sources/data/turnover.csv` and
`fy28/public/data/tenure.json`.

TJ, 22 September 2026: *"OH shoot. TENURE. We need a tenure report on the town-personnel
page. I think we can calculate this now. Whats the statistics about tenure for each
department... This goes well with turnover rates."*

IT IS CALCULABLE NOW AND IT WAS NOT LAST WEEK. `org-chart.csv` joins a NAMED PERSON to a
department, a role and a fiscal year across fifteen annual reports, so a person's tenure
is the span of years their name appears under a body. Nothing else in this project
measures how long anybody stays.

FOUR THINGS MAKE THIS NUMBER WRONG IF THEY ARE NOT HANDLED, and each is handled here.

1. A GAP YEAR IS NOT A DEPARTURE. 27 of 86 bodies skip at least one year inside their own
   span -- the Council on Aging board is missing four, the Public Library four, the DPW
   three -- because the department did not submit a report, or its page did not read.
   Measured naively, the whole staff leaves and comes back. So every span is counted in
   the years the BODY ITSELF PUBLISHED, never in calendar years, and the skipped years
   are named in the output rather than silently spanned.

2. THE ARCHIVE HAS EDGES, AND PEOPLE AT THEM ARE CENSORED. Somebody present in a body's
   FIRST published year began before it, and somebody present in its LAST is still there
   as far as anything here can see. Their tenure is a LOWER BOUND, not a length. That is
   survival analysis in one sentence, and a median computed without it understates every
   long-serving department -- which is most of them, because the archive is fifteen years
   and half the Fire Department has been there longer. Both bounds are published; so is
   the median of the uncensored, which is the only median that means what it says.

3. A ROSTER IS A POINT IN TIME, UNDATED WITHIN ITS YEAR. So N appearances is at most N
   years of service and at least N-1. Both are given and neither is called "tenure" on
   its own.

4. ONE PERSON MUST NOT BE TWO. `Josh Tocci` and `Joshua Tocci`, `John J. Londa` and
   `John Londa`, `Steve McKenna` and `Stephen McKenna` are each one person in two
   spellings, and read as two they halve each other's tenure. Identity here is SURNAME
   PLUS FIRST INITIAL WITHIN ONE BODY, and the collisions that choice could cause are
   counted and printed, not assumed away.

AND THE EPISTEMIC LINE (rule 7). A name leaving a roster is a name leaving a roster. It
is not a resignation, a retirement, a cut post or a person -- somebody may have moved
between departments, been left off a page, or held a post the town stopped printing.
Turnover here is the rate at which NAMES STOP APPEARING, and every figure says so.
"""
import argparse
import collections
import csv
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
SRC = os.path.join(DATA, 'org-chart.csv')
OUT_TENURE = os.path.join(DATA, 'tenure.csv')
OUT_TURNOVER = os.path.join(DATA, 'turnover.csv')
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'tenure.json')

TENURE_FIELDS = ['unit', 'unit_kind', 'person', 'first_fy', 'last_fy', 'appearances',
                 'published_years_spanned', 'missing_years_inside', 'left_censored',
                 'right_censored', 'roles']
TURNOVER_FIELDS = ['unit', 'unit_kind', 'fy', 'next_published_fy', 'people',
                   'names_not_reappearing', 'rate']


def identity(name):
    """Surname and first initial. See §4 of the module docstring."""
    parts = [p for p in name.replace('—', ' ').split() if p]
    if not parts:
        return None
    return (parts[-1].lower().strip('.,'), parts[0][:1].lower())


def load():
    rows = [r for r in csv.DictReader(open(SRC, encoding='utf-8')) if r['person'].strip()]
    published = collections.defaultdict(set)
    for r in rows:
        published[r['unit']].add(int(r['fy']))
    return rows, {u: sorted(y) for u, y in published.items()}


def build():
    rows, published = load()
    seen = collections.defaultdict(lambda: {'years': set(), 'names': collections.Counter(),
                                            'roles': collections.Counter(), 'kind': ''})
    for r in rows:
        key = identity(r['person'])
        if key is None:
            continue
        s = seen[(r['unit'], key)]
        s['years'].add(int(r['fy']))
        s['names'][r['person'].strip()] += 1
        s['kind'] = s['kind'] or r['unit_kind']
        if r['role'].strip() and r['role'] not in ('board seat', 'officer'):
            s['roles'][r['role'].strip()] += 1

    tenure = []
    for (unit, _key), s in seen.items():
        years = sorted(s['years'])
        pub = published[unit]
        inside = [y for y in pub if years[0] <= y <= years[-1]]
        tenure.append(dict(
            unit=unit, unit_kind=s['kind'],
            # The spelling the reports used most often, so the table reads as printed.
            person=s['names'].most_common(1)[0][0],
            first_fy=years[0], last_fy=years[-1], appearances=len(years),
            published_years_spanned=len(inside),
            missing_years_inside=';'.join(str(y) for y in inside if y not in s['years']),
            left_censored='yes' if years[0] == pub[0] else '',
            right_censored='yes' if years[-1] == pub[-1] else '',
            roles=' / '.join(r for r, _ in s['roles'].most_common(3))))
    tenure.sort(key=lambda r: (r['unit'].lower(), -r['published_years_spanned'],
                               r['person'].lower()))

    turnover = []
    by_unit_year = collections.defaultdict(set)
    kinds = {}
    for r in rows:
        key = identity(r['person'])
        if key:
            by_unit_year[(r['unit'], int(r['fy']))].add(key)
            kinds[r['unit']] = kinds.get(r['unit']) or r['unit_kind']
    for unit, pub in published.items():
        for a, b in zip(pub, pub[1:]):
            now, nxt = by_unit_year[(unit, a)], by_unit_year[(unit, b)]
            if not now:
                continue
            gone = now - nxt
            turnover.append(dict(unit=unit, unit_kind=kinds[unit], fy=a,
                                 next_published_fy=b, people=len(now),
                                 names_not_reappearing=len(gone),
                                 rate=round(len(gone) / len(now), 4)))
    turnover.sort(key=lambda r: (r['unit'].lower(), r['fy']))
    return tenure, turnover, published


def collisions(rows):
    """How often surname-plus-initial could have merged two DIFFERENT people.

    Not a guess: it counts the cases where one identity in one body carries names whose
    FULL forms cannot be reconciled -- `Robert Smith` and `Rachel Smith` would collide
    only if they shared an initial, and then the middle names or the second forename are
    the only thing left to look at. Printed on every run so the figure is never taken on
    trust.
    """
    byid = collections.defaultdict(set)
    for r in rows:
        k = identity(r['person'])
        if k:
            byid[(r['unit'], k)].add(r['person'].strip())
    risky = []
    for (unit, _k), names in byid.items():
        if len(names) < 2:
            continue
        firsts = {n.split()[0].lower().strip('.,') for n in names if n.split()}
        long = {f for f in firsts if len(f) > 2}
        if len(long) > 1 and not any(a != b and (a.startswith(b) or b.startswith(a))
                                     for a in long for b in long):
            risky.append((unit, sorted(names)))
    return risky


def payload(tenure, turnover, published):
    units = collections.defaultdict(list)
    for t in tenure:
        units[t['unit']].append(t)
    stats = []
    for unit, people in units.items():
        spans = [p['published_years_spanned'] for p in people]
        settled = [p['published_years_spanned'] for p in people
                   if not p['left_censored'] and not p['right_censored']]
        tr = [t for t in turnover if t['unit'] == unit]
        stats.append(dict(
            unit=unit, kind=people[0]['unit_kind'], people=len(people),
            published_years=len(published[unit]),
            first_fy=min(published[unit]), last_fy=max(published[unit]),
            median_all=statistics.median(spans),
            median_settled=statistics.median(settled) if settled else None,
            settled=len(settled), longest=max(spans),
            longest_person=max(people, key=lambda p: p['published_years_spanned'])['person'],
            still_there=sum(1 for p in people if p['right_censored']),
            turnover=round(sum(t['names_not_reappearing'] for t in tr)
                           / sum(t['people'] for t in tr), 4) if tr else None))
    stats.sort(key=lambda s: (-s['people'], s['unit']))
    return dict(generated_by='scripts/build_tenure.py', units=stats,
                people=tenure, turnover=turnover)


def _write(path, fields, rows):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    tenure, turnover, published = build()
    if a.check:
        for path, fields, rows in ((OUT_TENURE, TENURE_FIELDS, tenure),
                                   (OUT_TURNOVER, TURNOVER_FIELDS, turnover)):
            old = list(csv.DictReader(open(path, encoding='utf-8'))) \
                if os.path.exists(path) else []
            if len(old) != len(rows) or any(
                    any(str(r[k]) != o[k] for k in fields) for r, o in zip(rows, old)):
                print('STALE %s' % path)
                return 1
        return 0
    _write(OUT_TENURE, TENURE_FIELDS, tenure)
    _write(OUT_TURNOVER, TURNOVER_FIELDS, turnover)
    pay = payload(tenure, turnover, published)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(pay, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, sort_keys=True)

    rows, _ = load()
    risky = collisions(rows)
    cens = sum(1 for t in tenure if t['left_censored'] or t['right_censored'])
    print('%d people across %d bodies' % (len(tenure), len(pay['units'])))
    print('  %d (%.0f%%) are CENSORED — present in their body’s first or last published '
          'year, so their tenure is a lower bound'
          % (cens, 100 * cens / len(tenure)))
    print('  %d spans cross a year the body published nothing; those years are named '
          'per person' % sum(1 for t in tenure if t['missing_years_inside']))
    print('  %d identities carry two forenames that cannot be reconciled — read them '
          'before trusting them:' % len(risky))
    for unit, names in risky[:10]:
        print('      %-34s %s' % (unit[:34], ' | '.join(names)[:60]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
