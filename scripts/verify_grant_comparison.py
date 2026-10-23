#!/usr/bin/env python3
"""Every headline figure on the two grant-comparison pages, recomputed by a different route.

    python3 scripts/verify_grant_comparison.py

The generator (build_grant_comparison_topics.py) builds the comparison sets by CALLING
build_town_comparison.cohort() and joins through its own lookups. This reads the cohorts off the
PUBLISHED towns-like-us.json payload instead (role `structural` / `behavioural`), reads the raw
CSV and the DESE profile itself with no shared helper, computes its own medians and its own
correlation, and compares each to the value the page prints. A figure that disagrees fails.
"""
import csv
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_town_comparison import NEIGHBOURS, PEERS, DISTRICT_OF  # noqa: E402  (definitions only)

TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
YEAR = 2025


def facts(tid):
    d = json.load(open(os.path.join(TOPICS, tid + '.json'), encoding='utf-8'))
    return {f['id']: f['value']['value'] for f in d['facts']}


def main():
    twins = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'towns-like-us.json'),
                           encoding='utf-8'))['twins']
    makeup = [t['district'] for t in twins if t['role'] == 'structural']
    behaviour = [t['district'] for t in twins if t['role'] == 'behavioural']
    names = set(DISTRICT_OF[t] for t in NEIGHBOURS + PEERS) | set(makeup) | set(behaviour)
    names.discard('Fitchburg')            # DESE's two `Fitchburg` codes; the page leaves it out

    prof = {}
    code = {}
    for r in json.load(open(os.path.join(ROOT, 'sources', 'state-dese', 'er3w-dyti.json'),
                            encoding='utf-8')):
        if r['sy'] != str(YEAR) or r['ind_value'] in (None, ''):
            continue
        code[r['dist_name']] = r['dist_code'][:4]
        prof.setdefault(r['dist_code'][:4], {})[r['ind_subcat']] = float(r['ind_value'])
    amt = {}
    pages = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                              'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['fy'] != str(YEAR) or not r['district_code'] or r['amount'] == '':
            continue
        amt[(r['district_code'], r['fund_code'])] = float(r['amount'])
    lun = code['Lunenburg']
    comp = sorted(code[n] for n in names)
    hc = lambda c: prof[c]['Student Headcount']
    pp = lambda c, fc: amt[(c, fc)] / hc(c)
    five = ['0305', '0140', '0309', '0240', '0262']

    got1, got2 = facts('grant-allocations-compared'), facts('grants-others-receive')
    mk = [code[n] for n in makeup]
    want1 = {
        'idea-l': round(pp(lun, '0240')),
        'idea-med': round(st.median(pp(c, '0240') for c in comp)),
        'idea-below': sum(pp(c, '0240') < pp(lun, '0240') for c in comp),
        'ti-l': round(pp(lun, '0305')),
        'ti-mk': round(st.median(pp(c, '0305') for c in mk)),
        'li-l': prof[lun]['Low-Income % Headcount'],
        'li-mk': st.median(prof[c]['Low-Income % Headcount'] for c in mk),
        'five-l': round(sum(pp(lun, fc) for fc in five)),
        'five-med': round(st.median(sum(pp(c, fc) for fc in five) for c in comp)),
    }
    xs, ys = [], []
    for c, p in prof.items():
        if (c, '0305') in amt and 'Student Headcount' in p and 'Low-Income % Headcount' in p:
            xs.append(p['Low-Income % Headcount'])
            ys.append(amt[(c, '0305')] / p['Student Headcount'])
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    r = (sum((a - mx) * (b - my) for a, b in zip(xs, ys))
         / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)))
    want1['r-ti'] = round(r, 2)
    t3 = [c for c in comp if amt.get((c, '0180'), 0) > 0]
    rates = [amt[(c, '0180')] / (p['Student Headcount'] * p['English learner % Headcount'] / 100)
             for c, p in prof.items()
             if amt.get((c, '0180')) and p.get('Student Headcount') and p.get('English learner % Headcount')]
    learners = hc(lun) * prof[lun]['English learner % Headcount'] / 100
    want2 = {'t3-now': len(t3), 'el-l': prof[lun]['English learner % Headcount'],
             'rate': round(st.median(rates)), 'est': round(learners * st.median(rates))}
    bad = []
    if len(comp) != 28:
        bad.append('expected 28 comparison districts, found %d' % len(comp))
    if any(k[0] == lun and k[1] == '0180' for k in amt):
        bad.append('Lunenburg has a Title III row')
    for got, want, tid in ((got1, want1, 'grant-allocations-compared'),
                           (got2, want2, 'grants-others-receive')):
        for k, v in want.items():
            g = got.get(k)
            if g is None or abs(float(g) - float(v)) > 1e-6:
                bad.append('%s %s: page %r, recomputed %r' % (tid, k, g, v))
    if bad:
        print('\n'.join(bad))
        return 1
    print('grant comparison: %d figures recomputed, all agree' % (len(want1) + len(want2)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
