#!/usr/bin/env python3
"""Every figure on /lunenburg-by-the-numbers, recomputed from the CSVs by a second route.

    python3 scripts/verify_lunenburg_by_the_numbers.py

THE SECOND ROUTE IS THE WHOLE POINT. `build_lunenburg_by_the_numbers.py` reads the
database; this reads `sources/data/census-acs.csv`, `dese-function-statewide.csv` and
`dese-enrollment.csv` directly, with its own arithmetic, and asserts the VALUES in the
published payload. A verifier that called the generator's own functions would check that
the code agrees with itself.

IT ASSERTS NUMBERS, NEVER PROSE. `verify_athletics.py` once passed because a sentence
existed while the sentence was wrong, so nothing here looks for a phrase. The one
structural assertion is the opposite shape and is the most important check in the file:
NO CENSUS SENTINEL MAY BE RENDERED AS A FIGURE ANYWHERE IN THE PAYLOAD. -666666666 is not
an income and -555555555 is not a margin of zero, and the way that error would ship is a
figure quietly reading one of them as a number.

It also re-runs the aggregation rules the Census publishes, because those are where a
plausible-looking wrong answer comes from:

  * the margin of a SUM is the root of the sum of the squares, not the sum;
  * the margin of a SHARE has its own formula, with a second branch where the radicand
    goes negative;
  * two estimates differ only if the difference exceeds the root of the sum of their
    squared margins.
"""
import csv
import io
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'lunenburg-by-the-numbers.json')

LUN = 'Lunenburg town, Worcester County, Massachusetts'
SENTINELS = ('-666666666', '-555555555', '-333333333', '-222222222', '-999999999')
NEW, OLD = 2023, 2018

FAILURES = []


def check(what, got, want, tol=0.0):
    ok = (abs(float(got) - float(want)) <= tol) if isinstance(want, (int, float)) \
        else got == want
    if not ok:
        FAILURES.append('%s: payload says %r, recomputed %r' % (what, got, want))
    return ok


def rows(name):
    with io.open(os.path.join(DATA, name + '.csv'), encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def value(raw):
    v = (raw or '').strip()
    if v == '' or v in SENTINELS:
        return None
    return float(v)


def town_cells():
    out = {}
    for r in rows('census-acs'):
        if r['table'] == 'B19013':
            continue
        if r['geography'] != LUN:
            FAILURES.append('census-acs.csv: a Lunenburg-only table carries %r'
                            % r['geography'])
            continue
        e, m = value(r['estimate']), value(r['moe'])
        if e is None or m is None:
            continue
        out[(int(r['vintage']), r['variable'])] = (e, m)
    return out


def total(parts):
    return (sum(p[0] for p in parts), math.sqrt(sum(p[1] ** 2 for p in parts)))


def share(sub, tot):
    p = sub[0] / tot[0]
    rad = sub[1] ** 2 - (p ** 2) * (tot[1] ** 2)
    m = math.sqrt(rad) if rad > 0 else math.sqrt(sub[1] ** 2 + (p ** 2) * (tot[1] ** 2))
    return p * 100.0, m / tot[0] * 100.0


def band_vars(lo, hi):
    """The B01001 variables in an age group, derived here rather than imported.

    The band boundaries are written out again on purpose: if the generator's table and
    this one ever disagree, the group totals stop matching and that is the finding.
    """
    edges = [5, 10, 15, 18, 20, 21, 22, 25, 30, 35, 40, 45, 50, 55, 60, 62, 65,
             67, 70, 75, 80, 85, 999]
    out, prev = [], 0
    for i, upper in enumerate(edges):
        male = 3 + i
        if prev >= lo and upper <= hi:
            out += ['B01001_%03dE' % male, 'B01001_%03dE' % (male + 24)]
        prev = upper
    return out


GROUPS = [('children', 0, 18), ('young', 18, 25), ('early', 25, 45),
          ('middle', 45, 65), ('senior', 65, 999)]


def verify_ages(p, cs, vintage, ages):
    pop = cs[(vintage, 'B01001_001E')]
    check('population (%d)' % vintage, ages['population']['estimate'], pop[0])
    check('population margin (%d)' % vintage, ages['population']['moe'], pop[1])
    by = {g['key']: g for g in ages['groups']}
    summed = 0.0
    for key, lo, hi in GROUPS:
        vs = band_vars(lo, hi)
        got = total([cs[(vintage, v)] for v in vs])
        check('age group %s (%d)' % (key, vintage), by[key]['estimate'], got[0])
        check('age group %s margin (%d)' % (key, vintage), by[key]['moe'], got[1], 1e-6)
        s = share(got, pop)
        check('age group %s share (%d)' % (key, vintage), by[key]['share'], s[0], 1e-9)
        check('age group %s share margin (%d)' % (key, vintage),
              by[key]['share_moe'], s[1], 1e-9)
        summed += got[0]
    check('the age groups sum to the published total (%d)' % vintage, summed, pop[0])


def verify_households(p, cs, vintage, hh):
    tot = cs[(vintage, 'B11005_001E')]
    kid = cs[(vintage, 'B11005_002E')]
    check('households (%d)' % vintage, hh['households']['estimate'], tot[0])
    check('households margin (%d)' % vintage, hh['households']['moe'], tot[1])
    check('households with a child (%d)' % vintage, hh['with_child']['estimate'], kid[0])
    check('households with a child margin (%d)' % vintage, hh['with_child']['moe'], kid[1])
    s = share(kid, tot)
    check('share with a child (%d)' % vintage, hh['share'], s[0], 1e-9)
    check('share with a child margin (%d)' % vintage, hh['share_moe'], s[1], 1e-9)


def verify_tenure(p, cs, vintage, ten):
    occ, own, rent = (cs[(vintage, 'B25003_%03dE' % i)] for i in (1, 2, 3))
    check('occupied homes (%d)' % vintage, ten['occupied']['estimate'], occ[0])
    check('owner-occupied (%d)' % vintage, ten['owner']['estimate'], own[0])
    check('owner-occupied margin (%d)' % vintage, ten['owner']['moe'], own[1])
    check('renter-occupied (%d)' % vintage, ten['renter']['estimate'], rent[0])
    check('owners plus renters equal the occupied total (%d)' % vintage,
          own[0] + rent[0], occ[0])
    s = share(own, occ)
    check('owner share (%d)' % vintage, ten['owner_share'], s[0], 1e-9)
    check('owner share margin (%d)' % vintage, ten['owner_share_moe'], s[1], 1e-9)


INCOME_VARS = {'Under 25': 'B19049_002E', '25 to 44': 'B19049_003E',
               '45 to 64': 'B19049_004E', '65 and over': 'B19049_005E'}


def verify_income(p, cs, vintage, inc):
    allhh = cs[(vintage, 'B19049_001E')]
    check('median household income (%d)' % vintage,
          inc['all_households']['estimate'], allhh[0])
    check('median household income margin (%d)' % vintage,
          inc['all_households']['moe'], allhh[1])
    published = {r['label']: r for r in inc['bands']}
    for label, var in INCOME_VARS.items():
        cell = cs.get((vintage, var))
        if cell is None:
            if label in published:
                FAILURES.append('income band %r (%d) is a sentinel in the CSV and a '
                                'figure in the payload' % (label, vintage))
            continue
        if label not in published:
            FAILURES.append('income band %r (%d) is published by the Census and missing '
                            'from the payload' % (label, vintage))
            continue
        check('income %s (%d)' % (label, vintage), published[label]['estimate'], cell[0])
        check('income %s margin (%d)' % (label, vintage), published[label]['moe'], cell[1])


def verify_rank(p, rk):
    muni = [r for r in rows('census-acs')
            if r['table'] == 'B19013' and int(r['vintage']) == NEW]
    check('municipalities ranked', rk['municipalities'], len(muni))
    me = [r for r in muni if r['geography'] == LUN]
    if len(me) != 1:
        FAILURES.append('%d Lunenburg rows in the statewide income table' % len(me))
        return
    e, m = float(me[0]['estimate']), value(me[0]['moe'])
    check('Lunenburg median household income', rk['estimate'], e)
    check('its margin', rk['moe'], m)

    ordered = sorted(muni, key=lambda r: -float(r['estimate']))
    place = [i for i, r in enumerate(ordered, 1) if r['geography'] == LUN][0]
    check('the rank', rk['rank'], place)
    check('the rank, as rendered', rk['rank_text'], '%d of %d' % (place, len(muni)))

    usable = [(r['geography'], float(r['estimate']), value(r['moe']))
              for r in muni if value(r['moe']) is not None]
    check('municipalities with no computable margin',
          rk['no_margin'], len(muni) - len(usable))
    lo, hi = e - m, e + m
    overlap = [g for g in usable if g[1] + g[2] >= lo and g[1] - g[2] <= hi]
    check('municipalities whose interval overlaps Lunenburg’s', rk['overlap'],
          len(overlap))
    indis = [g for g in usable
             if abs(g[1] - e) <= math.sqrt(g[2] ** 2 + m ** 2)]
    check('municipalities the significance test cannot separate',
          rk['indistinguishable'], len(indis))
    check('the histogram keeps every municipality',
          sum(b['count'] for b in rk['distribution']), len(muni))
    marked = [b for b in rk['distribution'] if b['is_lunenburg']]
    check('exactly one histogram bin is marked as ours', len(marked), 1)
    if marked:
        b = marked[0]
        if not (b['low'] <= e < b['high']):
            FAILURES.append('the marked histogram bin does not contain Lunenburg')


def verify_change(p, cs, chg):
    """Every comparison, recomputed, including the ones the page says did not survive."""
    survived = 0
    for t in chg['tests']:
        a, b = (t['old'], t['old_moe']), (t['new'], t['new_moe'])
        m = math.sqrt(a[1] ** 2 + b[1] ** 2)
        d = b[0] - a[0]
        check('%s: the difference' % t['label'], t['difference'], d, 1e-9)
        check('%s: the combined margin' % t['label'], t['combined_moe'], m, 1e-9)
        check('%s: does it clear the margin' % t['label'],
              t['distinguishable'], abs(d) > m)
        survived += 1 if abs(d) > m else 0
    check('comparisons that clear their margins', chg['survived'], survived)
    check('comparisons that do not', chg['inside_the_margin'],
          len(chg['tests']) - survived)
    check('the comparison count', chg['compared'], len(chg['tests']))


def verify_per_pupil(p, pp):
    series = [r for r in rows('dese-function-statewide')
              if r['level'] == 'total' and r['func_cat_code'] == 'TTPP']
    check('per-pupil years', pp['years'], len(series))
    by = {int(r['fy']): r for r in series}
    last = by[max(by)]
    check('the latest per-pupil year', pp['last']['fy'], max(by))
    check('the latest per-pupil rank', pp['last']['rank_text'],
          last['lunenburg_rank_of_districts'])
    bottom = 0
    for r in series:
        place, of = (int(x) for x in r['lunenburg_rank_of_districts'].split(' of '))
        if 100.0 * (of - place + 1) / of <= 25.0:
            bottom += 1
    check('years in the bottom quarter of districts', pp['bottom_quarter_years'], bottom)
    below = sum(1 for r in series
                if float(r['lunenburg_per_pupil']) < float(r['per_pupil_median']))
    check('years below the statewide median', pp['below_median_years'], below)


def verify_children(p, ch):
    district = [r for r in rows('dese-enrollment') if r['org_level'] == 'district'
                and r['lea'] == '01620000']
    latest = max(district, key=lambda r: int(r['fy']))
    check('the enrolment year', ch['fy'], int(latest['fy']))
    check('children enrolled', ch['students'], float(latest['total_cnt']))


def verify_no_sentinel_printed(p):
    """A sentinel may appear as a raw string; it may never be a number.

    The two are told apart by field: `estimate_raw`, `moe_raw` and the sentinel glossary
    carry the codes verbatim, and every other field in the payload is checked for one.
    """
    raw_fields = {'estimate_raw', 'moe_raw', 'code'}
    bad = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in raw_fields:
                    continue
                walk(v, '%s.%s' % (path, k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, '%s[%d]' % (path, i))
        else:
            s = str(node)
            for code in SENTINELS:
                if code in s or code.lstrip('-') in s.replace(',', ''):
                    bad.append('%s = %r' % (path, node))
    walk(p, '')
    for b in bad:
        FAILURES.append('a Census sentinel is published as a value: %s' % b)


def verify_conclusion_figures(p, cs, rk, pp, ch):
    """Every figure a conclusion states, against the value it should have been computed
    from. The rule-2 scan -- that no unregistered digit is in the prose -- is run
    separately by verify_conclusions.py against the published payload."""
    by = {c['id']: c for c in p['conclusions']}
    senior = [g for g in p['ages']['groups'] if g['key'] == 'senior'][0]
    want = {
        ('a-sixth-of-the-town-is-65-or-over', 'senior'): senior['estimate'],
        ('a-sixth-of-the-town-is-65-or-over', 'students'): ch['students'],
        ('a-third-of-homes-have-a-child-under-18', 'withchild'):
            p['households']['with_child']['estimate'],
        ('a-third-of-homes-have-a-child-under-18', 'households'):
            p['households']['households']['estimate'],
        ('a-senior-household-earns-about-half', 'senior'):
            p['senior_gap']['senior']['estimate'],
        ('a-senior-household-earns-about-half', 'middle'):
            p['senior_gap']['middle']['estimate'],
        ('four-in-five-homes-are-owner-occupied', 'owner'):
            p['tenure']['owner']['estimate'],
        ('ordinary-on-income-near-the-bottom-on-spending', 'overlap'): rk['overlap'],
        ('ordinary-on-income-near-the-bottom-on-spending', 'rank'): rk['rank'],
        ('ordinary-on-income-near-the-bottom-on-spending', 'pprank'): pp['last']['rank'],
        ('most-of-what-changed-is-inside-the-margin', 'survived'): p['change']['survived'],
    }
    for (cid, name), v in sorted(want.items()):
        c = by.get(cid)
        if not c:
            FAILURES.append('the conclusion %r is no longer published' % cid)
            continue
        f = c['figures'].get(name)
        if not f:
            FAILURES.append('%s: the figure %r is no longer registered' % (cid, name))
            continue
        check('%s/%s' % (cid, name), f['value'], v, 1e-9)
        if f['text'] not in ' '.join((c['claim'], c['so_what'], c['detail'])):
            FAILURES.append('%s: the figure %r renders as %r and appears in none of its '
                            'prose' % (cid, name, f['text']))


def main():
    if not os.path.exists(PAYLOAD):
        print('MISSING %s — run scripts/build_lunenburg_by_the_numbers.py'
              % os.path.relpath(PAYLOAD, ROOT))
        return 1
    with io.open(PAYLOAD, encoding='utf-8') as fh:
        p = json.load(fh)

    cs = town_cells()
    verify_ages(p, cs, NEW, p['ages'])
    verify_ages(p, cs, OLD, p['previous']['ages'])
    verify_households(p, cs, NEW, p['households'])
    verify_households(p, cs, OLD, p['previous']['households'])
    verify_tenure(p, cs, NEW, p['tenure'])
    verify_tenure(p, cs, OLD, p['previous']['tenure'])
    verify_income(p, cs, NEW, p['income'])
    verify_income(p, cs, OLD, p['previous']['income'])

    gap = p['senior_gap']
    check('the senior share of a 45-to-64 median',
          gap['share'], 100.0 * gap['senior']['estimate'] / gap['middle']['estimate'],
          1e-9)

    verify_rank(p, p['rank'])
    verify_change(p, cs, p['change'])
    verify_per_pupil(p, p['per_pupil'])
    verify_children(p, p['children'])
    verify_no_sentinel_printed(p)
    verify_conclusion_figures(p, cs, p['rank'], p['per_pupil'], p['children'])

    # AND EVERY PUBLISHED ESTIMATE CARRIES A MARGIN. The page's whole discipline is that
    # an ACS figure never travels without one, so the shape is asserted rather than
    # trusted: anything with an `estimate` has a `moe` beside it.
    missing = []

    def walk(node, path):
        if isinstance(node, dict):
            if 'estimate' in node and 'moe' not in node and 'estimate_raw' not in node:
                missing.append(path)
            for k, v in node.items():
                walk(v, '%s.%s' % (path, k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, '%s[%d]' % (path, i))
    walk(p, '')
    for m in missing:
        FAILURES.append('an estimate is published with no margin beside it: %s' % m)

    if FAILURES:
        print('%d figure(s) on /lunenburg-by-the-numbers do not reproduce:\n' % len(FAILURES))
        for f in FAILURES:
            print('  ' + f)
        return 1
    senior = [g for g in p['ages']['groups'] if g['key'] == 'senior'][0]
    print('ok — every figure on /lunenburg-by-the-numbers recomputes from the CSVs')
    print('  %s residents, %s of them 65 or over; %s households, %s with a child under 18'
          % (p['ages']['population']['text'], senior['text'],
             p['households']['households']['text'], p['households']['with_child']['text']))
    print('  income %s: rank %s, overlapping %d of %d municipalities (%d by the '
          'significance test)'
          % (p['rank']['text'], p['rank']['rank_text'], p['rank']['overlap'],
             p['rank']['municipalities'], p['rank']['indistinguishable']))
    print('  %s comparisons between the two releases clear their margins'
          % p['change']['survived_text'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
