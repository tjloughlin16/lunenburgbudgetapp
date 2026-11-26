#!/usr/bin/env python3
"""Recompute the circuit breaker facts on FY2026 school surplus by a second route, and fail if a figure differs.

    python3 scripts/verify_circuit_breaker_surplus.py

The page is built by build_fy2026_school_surplus.py (24 November 2026; it absorbed Circuit
breaker and surplus) from `build_circuit_breaker_surplus.data()`, which reads the journal through `journal.py` and the general fund
lines through `fy_breakdown.model` (verified on its own by verify_fy_breakdown.py). This reads
the journal CSV with csv and Decimal and the budget book's text directly, shares nothing with
the generator, and asserts every figure on the page's facts reproduces, to the dollar:

  - the book's FY2026 circuit breaker offset, and that gross less it is the vote;
  - the 29 June 2026 charge, and that it is the only entry moving collaborative tuition onto
    fund 2640 that year;
  - what fund 2640 drew July to May in FY2026, and the least it drew in FY2023-FY2025;
  - FY2026's left.
"""
import csv
import json
import os
import re
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', 'fy2026-surplus-by-category.json')
BOOK = os.path.join(ROOT, 'sources', 'district-budget', 'text', '3-12-25-town-manager-39-s-budget.txt')
COLLAB = '0100-3-300-9400-51-1-06-2-535023'
SPENT = {'API', 'APM', 'PRJ', 'PRH', 'GEN', 'GRV', 'CRP', 'POE', 'POL', 'POM', 'SOY', 'GEL'}
ACTUAL = {'API', 'APM', 'PRJ', 'PRH', 'GEN', 'GRV'}
bad = []


def check(ok, msg):
    if not ok:
        bad.append(msg)


def usd(v):
    v = round(v)
    return ('-$%s' if v < 0 else '$%s') % format(abs(v), ',d')


def main():
    p = json.load(open(PAYLOAD, encoding='utf-8'))
    facts = {f['id']: f['value']['text'] for f in p['facts'] if f.get('value')}
    rows = []
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')):
        r['y'], r['v'] = int(r['fiscal_year']), Decimal(r['amount'])
        rows.append(r)
    text = ' '.join(open(BOOK, encoding='utf-8').read().split())
    g = re.search(r'Collaborative Tuitions [\d,]+ ([\d,]+) ', text)
    o = re.search(r'\(75% = [\d,]+\)-[\d,]+ -([\d,]+) ', text)
    gross, plan = Decimal(g.group(1).replace(',', '')), Decimal(o.group(1).replace(',', ''))
    voted = sum((r['v'] for r in rows if r['y'] == 2026 and r['account'] == COLLAB
                 and r['source'] == 'BUC'), Decimal(0))
    check(abs(gross - plan - voted) < 1, 'book gross %s less %s is not the vote %s' % (gross, plan, voted))
    check(facts['plan'] == usd(plan), 'plan: page %s, book %s' % (facts['plan'], plan))
    onto = [r for r in rows if r['y'] == 2026 and r['fund'] == '2640' and r['source'] == 'GEN'
            and r['v'] > 0]
    check(len(onto) == 1 and onto[0]['effective_date'] == '2026-06-29',
          'the charge onto fund 2640 is not one 29 June 2026 entry')
    charged = onto[0]['v']
    check(facts['charged'] == usd(charged), 'charged: page %s, journal %s' % (facts['charged'], charged))
    early = lambda y: sum((r['v'] for r in rows if r['y'] == y and r['fund'] == '2640'
                           and r['source'] in ACTUAL   # payments and re-charges; open orders and receipts out
                           and r['effective_date'][5:7] != '06'), Decimal(0))
    check(facts['may26'] == usd(early(2026)), 'may26: page %s, journal %s' % (facts['may26'], early(2026)))
    # the third conclusion: FY2023-FY2025 drew at least this much by May
    prior = min(early(y) for y in (2023, 2024, 2025))
    claims = ' '.join(c['text']['text'] if isinstance(c.get('text'), dict) else str(c.get('text'))
                      for c in p['conclusions'])
    check(usd(prior) in claims, 'least drawn by May, FY2023-FY2025: journal %s, not in the '
                                'conclusions' % usd(prior))
    # FY2026 left: every surplus-scope line, budget + transfers less spent, orders owed counted
    # (the period-13 report's own footing in the open year, so no close to add back)
    sc = [r for r in rows if r['y'] == 2026 and r['account'].startswith('0100-3-300-')
          and r['account'].split('-')[-1].startswith('5')]
    bud = sum((r['v'] for r in sc if r['source'] in ('BUC', 'BUA')), Decimal(0))
    spent = sum((r['v'] for r in sc if r['source'] in SPENT), Decimal(0))
    left = bud - spent
    check(facts['left'] == usd(left), 'left: page %s, journal %s' % (facts['left'], left))
    if bad:
        print('verify_circuit_breaker_surplus: %d FAILED' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    print('verify_circuit_breaker_surplus: %d facts recomputed from the journal and the budget book'
          % 5)
    return 0


if __name__ == '__main__':
    sys.exit(main())
