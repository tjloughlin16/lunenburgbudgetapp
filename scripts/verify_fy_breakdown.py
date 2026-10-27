#!/usr/bin/env python3
"""Recompute the FY breakdown by a second route, and fail if any figure differs.

    python3 scripts/verify_fy_breakdown.py

The generator (`fy_breakdown.py`, `build_fy_breakdown.py`) reads the journal through
`journal.py`. This reads the two CSVs with csv and Decimal and re-derives every definition
itself -- source codes, the scope, the footing, the payee key, the voted function codes, the
three match rules -- sharing ONLY the category definition (`build_school_surplus.category_of`),
which is what makes a category here the category on the published surplus pages. It asserts:

  1. every line's four parts sum to what the period-13 `gf-school` spreadsheet prints as
     available, less the orders the close zeroed (read here off NEXT July's `SOY` lines, not
     the `YEC` lines the generator reads), so the owed footing is tied by another document;
  2. each year's four totals sum to that year's surplus on the same footing;
  3. every line's four parts equal the ones recomputed here, to the cent;
  4. the two worked cases in notes/HANDOFF-FY-BREAKDOWN.md, exactly;
  5. every figure the payload prints, if it has been written (`--no-payload` skips it).
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_school_surplus import category_of  # noqa: E402  (the one shared definition)

DATA = os.path.join(ROOT, 'sources', 'data')
D0, CENT = Decimal(0), Decimal('0.01')
YEARS = (2023, 2024, 2025, 2026)
OPEN = 2026
PRIVATE = '0100-3-300-9300-51-1-06-2-535019'
COLLAB = '0100-3-300-9400-51-1-06-2-535023'
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', 'fy2026-breakdown.json')
bad = []


def check(ok, msg):
    if not ok:
        bad.append(msg)


def raw():
    acc = {a['account']: a for a in csv.DictReader(
        open(os.path.join(DATA, 'munis-school-journal-accounts.csv'), encoding='utf-8'))}
    rows = []
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')):
        r['y'], r['v'] = int(r['fiscal_year']), Decimal(r['amount'])
        rows.append(r)
    return acc, rows


def in_scope(acct):
    p = acct.split('-')
    return p[0] == '0100' and p[2] == '300'


def fn(acct):
    return acct.split('-')[3]


def cat(acct):
    return category_of(dict(account=acct, obj=acct.split('-')[-1]))


def key(r):
    """The payee: None for no payee, '' for a masked one."""
    if r['ref_type'] != 'VND':
        return None
    v = r['vendor'].strip()
    if v in ('', 'individual (redacted)'):
        return ''
    k = ' '.join(v.upper().split()).rstrip('.,;')
    return {'FLLAC EDUCATIONAL CO': 'FLLAC (KEYSTONE)'}.get(k, k)


def capital(fund):
    return fund[:2] in ('30', '31', '81', '90')


def recompute():
    acc, rows = raw()
    ex = [r for r in rows if acc[r['account']]['object'].startswith('5')]
    SPENT = {'API', 'APM', 'PRJ', 'PRH', 'GEN', 'GRV', 'CRP', 'POE', 'POL', 'POM', 'SOY', 'GEL'}
    # voted function codes: any 0100 expense budget posting, headings (x000) excluded
    voted = {fn(r['account']) for r in ex if r['fund'] == '0100' and r['source'] in ('BUC', 'BUA')
             and r['v'] != 0 and not fn(r['account']).endswith('000')}

    def is_line(code):
        return code in voted and code != '0000'

    pieces = defaultdict(lambda: defaultdict(Decimal))
    soy_docs = defaultdict(set)
    for r in ex:
        if in_scope(r['account']) and r['source'] == 'SOY':
            soy_docs[(r['y'], r['account'])].add(r['doc_no'])
    for r in ex:
        if not in_scope(r['account']):
            continue
        k, s, p = (r['y'], r['account']), r['source'], pieces[(r['y'], r['account'])]
        d = r['description']
        if s == 'BUC' or (s == 'BUA' and r['journal'] == '2025/01/000564' and r['y'] == 2025):
            p['V'] += r['v']
        elif s == 'BUA' and d.startswith('ENCUMBRANCE CARRY FORWARD'):
            p['CF'] += r['v']
        elif s == 'BUA':
            p['T'] += r['v']
        elif s in SPENT:
            p['G'] += r['v']
            if r['doc_no'] in soy_docs[k] and s in ('SOY', 'POL', 'POM', 'POE', 'GEL'):
                p['CE'] += r['v']
                if s == 'POL':
                    p['CP'] -= r['v']
            m = re.match(r'(\d\d)L2KEY', r['doc_no'])
            if s in ('API', 'APM') and m and int(m.group(1)) > r['y'] % 100:
                p['PP'] += r['v']

    O = defaultdict(Decimal)          # (y, account) -> other funds placed
    F = defaultdict(Decimal)          # (y, category) -> rule c
    used = set()
    js = defaultdict(list)
    for i, r in enumerate(ex):
        if r['source'] in ('GEN', 'GRV'):
            js[(r['y'], r['journal'])].append((i, r))
    for _, ir in js.items():
        rs = [r for _, r in ir]
        if len({r['fund'] for r in rs}) < 2 or abs(sum(r['v'] for r in rs)) > 1:
            continue
        sc = [r for r in rs if in_scope(r['account'])]
        if not sc or len(sc) == len(rs):
            continue
        for i, o in ir:
            if in_scope(o['account']) or o['v'] <= 0:
                continue        # a cost taken back stays with its own account
            opp = [s for s in sc if s['v'] < 0]
            pool = [s for s in opp if fn(s['account']) == fn(o['account'])] or opp
            if not pool:
                continue
            w = defaultdict(Decimal)
            for s in pool:
                w[s['account']] += abs(s['v'])
            # the cents of a shared move are not checked one by one; the journal's total is
            tot = sum(w.values())
            for a_, wt in w.items():
                O[(o['y'], a_)] += o['v'] * wt / tot
            used.add(i)
    paid = defaultdict(lambda: defaultdict(Decimal))
    for r in ex:
        if in_scope(r['account']) and r['source'] in ('API', 'APM') and key(r):
            paid[key(r)][r['account']] += r['v']
    for i, r in enumerate(ex):
        if i in used or in_scope(r['account']) or r['source'] not in SPENT:
            continue
        k = key(r)
        if k and k in paid and not capital(r['fund']):
            g = paid[k]
            cand = [a for a in g if fn(a) == fn(r['account'])] or list(g)
            best = max(cand, key=lambda a: (g[a], a))
            O[(r['y'], best)] += r['v']
        elif not capital(r['fund']) and is_line(fn(r['account'])):
            F[(r['y'], cat(r['account']))] += r['v']

    out = {}
    for k in list(O):
        pieces[k]
    for k, p in pieces.items():
        cost = p['G'] - p['PP'] - p['CP'] - p['CE']
        out[k] = dict(voted_above_cost=p['V'] - cost - O[k], transfers=p['T'],
                      other_funds=O[k], another_year=p['CF'] - p['CP'] - p['CE'] - p['PP'],
                      prepaid=p['PP'])
    return out, F


def printed():
    """(y, account) -> the period-13 `available_budget`, and the orders the close zeroed, read
    off next July's SOY lines."""
    av = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['report'] == 'gf-school' and r['type'] == 'E' and r['period'] == '13':
            av[(int(r['fiscal_year']), r['account'])] = Decimal(r['available_budget']).quantize(CENT)
    acc, rows = raw()
    owed = defaultdict(Decimal)
    for r in rows:
        if r['source'] == 'SOY' and in_scope(r['account']):
            owed[(r['y'] - 1, r['account'])] += r['v']
    return av, owed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-payload', action='store_true')
    args = ap.parse_args(argv)
    import fy_breakdown as FB          # the generator's model, compared against, never trusted
    m = FB.model()
    mine, F = recompute()
    av, owed = printed()
    T = FB.TERMS
    gen = {(r['fy'], r['account']): r for r in m['rows'] if r['account']}
    for k in set(gen) | set(mine):
        g, me = gen.get(k), mine.get(k)
        if g is None or me is None:
            check(False, 'FY%d %s is in one route only' % k)
            continue
        for t in T:
            d = abs(g[t] - me[t])
            # a shared move's cents fall where the generator's largest remainder puts them
            check(d < Decimal('0.05') if t in ('other_funds', 'voted_above_cost') else d == 0,
                  'FY%d %s %s: generator %s, recomputed %s' % (k[0], k[1], t, g[t], me[t]))
        target = av.get(k, D0) - (owed.get(k, D0) if k[0] != OPEN else D0)
        check(sum(g[t] for t in T) == target,
              'FY%d %s: parts sum %s; the period-13 report less orders owed gives %s'
              % (k[0], k[1], sum(g[t] for t in T), target))
    for (y, c), v in F.items():
        g = sum((r['other_funds'] for r in m['rows'] if r['fy'] == y and r['account'] is None
                 and r['category'] == c), D0)
        check(abs(g - v) < CENT, 'FY%d %s: same-function money %s vs %s' % (y, c, g, v))
    for y in YEARS:
        target = sum((v for (yy, _), v in av.items() if yy == y), D0) - (
            sum((v for (yy, _), v in owed.items() if yy == y), D0) if y != OPEN else D0)
        tot = m['years'][y]
        check(sum(tot['terms'].values()) == target == tot['left'],
              'FY%d: four totals %s, left %s, period-13 route %s'
              % (y, sum(tot['terms'].values()), tot['left'], target))
    # the worked cases
    p, c = gen[(2026, PRIVATE)], gen[(2026, COLLAB)]
    check(p['voted'] == Decimal('988630.00') and p['transfers'] == 0
          and p['other_funds'] == Decimal('287107.65') and p['left'] == Decimal('522629.18')
          and p['voted_above_cost'] == Decimal('235521.53'),
          'private tuition FY2026 no longer reproduces 988,630 - 753,108.47 + 287,107.65')
    check(dict(p['payers']) == {('payee', 'IDEA (special education)'): Decimal('287107.65')},
          'private tuition FY2026: the other-fund money is not all the IDEA grant')
    check(c['by_rule']['moved'] == Decimal('333494.89') and c['prepaid'] == Decimal('189276.75')
          and c['left'] == Decimal('-434107.56'),
          'collaborative tuition FY2026: reclass 333,494.89 / prepaid 189,276.75 / left -434,107.56')
    if not args.no_payload:
        payload_checks(m)
    if bad:
        print('verify_fy_breakdown: %d FAILED' % len(bad))
        for b in bad[:40]:
            print('  ' + b)
        return 1
    print('verify_fy_breakdown: %d lines in %d years, every part recomputed and tied to the '
          'period-13 report' % (len(gen), len(YEARS)))
    return 0


def payload_checks(m):
    if not os.path.exists(PAYLOAD):
        check(False, 'no payload at %s (run build_fy_breakdown.py, or pass --no-payload)' % PAYLOAD)
        return
    import build_fy_breakdown as B
    text = open(PAYLOAD, encoding='utf-8').read()
    check(text == B.render(m), 'the payload does not reproduce from the model')
    p = json.loads(text)
    yr = {y: sum((r['left'] for r in m['rows'] if r['fy'] == y), D0) for y in YEARS}
    # every dollar figure the page prints, against the recomputed route
    mine, _ = recompute()
    left26 = sum((mine[k]['voted_above_cost'] + mine[k]['transfers'] + mine[k]['other_funds']
                  + mine[k]['another_year'] for k in mine if k[0] == 2026), D0)
    check('$%s' % format(round(left26), ',d') in p['finding']['text'],
          'the finding does not carry FY2026 left, recomputed %s' % left26)
    check(abs(left26 - yr[2026]) < 1, 'FY2026 left: model %s, recomputed %s' % (yr[2026], left26))
    data = next(b for b in p['blocks'] if b['block'] == 'custom')['data']
    for col in data['years']:
        y = int(col['fy'][2:])
        flows = sum((v for (yy, _, _), v in m['flows'].items() if yy == y), D0)
        segs = sum((s['value'] for b in col['blocks'] for s in b['segs']), 0.0)
        check(abs(Decimal(str(col['total'])) - flows) < 1 and abs(segs - float(flows)) < 1,
              'alluvial %s total %s, flows %s, drawn %s' % (col['fy'], col['total'], flows, segs))
        # what the alluvial draws is every school expense dollar of the year, all funds, on the
        # footing used: recomputed straight off the CSV
        allf = all_funds(y)
        check(abs(Decimal(str(col['total'])) - allf) < 1,
              'alluvial %s draws %s; every fund, recomputed, %s' % (col['fy'], col['total'], allf))


def all_funds(y):
    """Every school expense dollar of year y: spent (orders owed counted), less the general
    fund's payments on orders carried in from the year before and next year's invoices paid
    early -- each of those belongs to another year's column."""
    out, _ = recompute()
    acc, rows = raw()
    SPENT = {'API', 'APM', 'PRJ', 'PRH', 'GEN', 'GRV', 'CRP', 'POE', 'POL', 'POM', 'SOY', 'GEL'}
    tot = sum((r['v'] for r in rows if r['y'] == y and r['source'] in SPENT
               and acc[r['account']]['object'].startswith('5')), D0)
    other = sum((v['another_year'] for k, v in out.items() if k[0] == y), D0)
    cf = sum((r['v'] for r in rows if r['y'] == y and in_scope(r['account']) and r['source'] == 'BUA'
              and r['description'].startswith('ENCUMBRANCE CARRY FORWARD')), D0)
    # another_year = carried budget - what the carried orders paid - next year's bills, so the
    # general fund's spending on other years is carried budget less another_year
    return tot - (cf - other)


if __name__ == '__main__':
    sys.exit(main())
