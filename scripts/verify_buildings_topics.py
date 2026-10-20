#!/usr/bin/env python3
"""Recompute every figure on the Buildings and grounds hub and its two topic pages by a
DIFFERENT ROUTE.

    python3 scripts/verify_buildings_topics.py

The generator reads the journal through scripts/journal.py. This reads:

  * the PUBLISHED period-13 spreadsheets (`munis-school-ytd.csv`, report gf-school), which the
    generator never reads, for every account's original budget, spending, open orders and what
    was left, each year -- the journal must reproduce them;
  * the journal CSV raw, with csv and Decimal, for the payees, the type of work (joined to
    `building-payee-trades.csv` here, by its own reading of the file) and the capital funds;
  * the budget book's TEXT, split line by line rather than by the generator's pattern.

Shared on purpose, as definitions: build_school_surplus.category_of (the line IS the surplus
pages' category) and journal.payee (the one payee rule, which the redaction uses too).
"""
import csv
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_school_surplus import category_of  # noqa: E402  (the definition)
import journal as J  # noqa: E402  (journal.payee only)

DATA = os.path.join(ROOT, 'sources', 'data')
TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
YEARS = (2023, 2024, 2025, 2026)
ACTUAL = ('API', 'APM', 'PRJ', 'PRH', 'GEN', 'GRV', 'CRP')
bad = []


def money(v):
    return '$' + format(abs(round(float(v))), ',')


def main():
    # ---- route 1: the period-13 spreadsheets
    col = defaultdict(D)
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['period'] != '13' or r['report'] != 'gf-school' or r['type'] != 'E':
            continue
        if category_of(r) != 'buildings':
            continue
        y = int(r['fiscal_year'])
        for c in ('original_approp', 'transfers_adjustments', 'ytd_expended', 'encumbrances',
                  'available_budget'):
            v = D(r[c]).quantize(D('0.01'))
            col[(y, c)] += v
            col[(y, r['account'], c)] += v
    # ---- route 2: the journal raw
    trade = {r['payee']: r['trade'] for r in
             csv.DictReader(open(os.path.join(DATA, 'building-payee-trades.csv'), encoding='utf-8'))}
    spent, pay, cap = defaultdict(D), defaultdict(D), defaultdict(D)
    payees = set()
    rows = list(csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')))
    for r in rows:
        if r['fund'] == '0100' and r['account'].split('-')[2] == '300' and r['source'] in ACTUAL \
                and category_of(dict(account=r['account'], obj=r['object'])) == 'buildings':
            y, a = int(r['fiscal_year']), D(r['amount'])
            spent[y] += a
            p = J.payee(r) if r['ref_type'] == 'VND' else None
            if p is not None:
                payees.add(p)
            pay[(p, y)] += a
    for r in rows:
        if r['fund'].startswith('3') and r['source'] in ACTUAL and r['ref_type'] == 'VND' \
                and J.payee(r) in payees:
            cap[int(r['fiscal_year'])] += D(r['amount'])
    for y in YEARS:
        if spent[y] != col[(y, 'ytd_expended')]:
            bad.append('FY%d: the journal’s spending does not tie to the spreadsheet' % y)
    yp = {p: sum(1 for y in YEARS if pay[(p, y)] > 0) for p in payees}
    rec = {y: sum(pay[(p, y)] for p in payees if yp[p] >= 3) for y in YEARS}
    one = {y: sum(pay[(p, y)] for p in payees if yp[p] <= 2) for y in YEARS}
    tr = defaultdict(D)
    for (p, y), v in pay.items():
        tr[(trade.get(p, 'Other repairs and supplies'), y)] += v
    # ---- route 3: the book, line by line
    book = {}
    for line in open(os.path.join(ROOT, 'sources', 'district-budget', 'text',
                                  '3-12-25-town-manager-39-s-budget.txt'), encoding='utf-8'):
        parts = line.split()
        if len(parts) > 6 and parts[-1].endswith('%'):
            try:
                book[' '.join(parts[:-6])] = (D(parts[-6].replace(',', '')),
                                              D(parts[-2].replace(',', '')))
            except Exception:       # a line whose last six words are not figures
                continue

    left = {y: col[(y, 'available_budget')] for y in YEARS}
    want = {
        'upkeep-budget-vs-spending': dict(
            o0=col[(2023, 'original_approp')], o1=col[(2026, 'original_approp')],
            s0=col[(2023, 'ytd_expended')], s1=col[(2026, 'ytd_expended')],
            db=col[(2026, 'original_approp')] - col[(2025, 'original_approp')],
            ds=col[(2025, 'ytd_expended')] - col[(2026, 'ytd_expended')],
            left=left[2026], enc=col[(2026, 'encumbrances')], c0=cap[2025], c1=cap[2026]),
        'upkeep-spending': dict(rlo=min(rec.values()), rhi=max(rec.values()), one0=one[2025],
                                one23=one[2023]),
    }
    for tid, fig in want.items():
        p = json.load(open(os.path.join(TOPICS, '%s.json' % tid), encoding='utf-8'))
        facts = {x['id']: x for x in p['facts']}
        for k, v in fig.items():
            got = facts[k]['value']['value']
            if abs(float(got) - float(v)) > 0.006:
                bad.append('%s %s: page %r, recomputed %r' % (tid, k, got, float(v)))
        if tid == 'upkeep-budget-vs-spending':
            for r in p['table']['views'][0]['rows']:
                b = book.get(r['label'])
                if b is None:
                    bad.append('book line %r not found by a line split' % r['label'])
                elif r['cells'][:2] != [money(b[0]), money(b[1])]:
                    bad.append('book line %r reads %s, the book %s' % (r['label'], r['cells'][:2], b))
            ch = p['chart']['series']
            for y, s, o in zip(YEARS, ch[0]['values'], ch[1]['values']):
                if abs(s - float(col[(y, 'ytd_expended')])) > 0.006 or \
                        abs(o - float(col[(y, 'original_approp')])) > 0.006:
                    bad.append('chart FY%d does not match the spreadsheet' % y)
        else:
            for t in p['chart']['series']:
                for y, v in zip(YEARS, t['values']):
                    if abs(v - float(tr[(t['name'], y)])) > 0.006:
                        bad.append('%s %s %d: %r, recomputed %r' % (tid, t['name'], y, v, float(tr[(t['name'], y)])))
    # ---- contracted building services, one account
    a = '0100-3-300-4220-01-1-74-2-535006'
    rf = sum(D(r['amount']) for r in rows if r['account'] == a and r['source'] == 'BUA'
             and r['description'] == 'RSF TRANSFER APPROVED 2/13/25')
    ap = defaultdict(D)
    for r in rows:
        if r['account'] == a and r['source'] in ACTUAL and r['ref_type'] == 'VND':
            ap[(J.payee(r), int(r['fiscal_year']))] += D(r['amount'])
    ps = {p for (p, _) in ap}
    yp = {p: sum(1 for y in YEARS if ap[(p, y)] > 0) for p in ps}
    arec = {y: sum(ap[(p, y)] for p in ps if yp[p] >= 3) for y in YEARS}
    g = lambda y, c: col[(y, a, c)]
    cw = dict(o24=g(2024, 'original_approp'), s24=g(2024, 'ytd_expended'),
              o25=g(2025, 'original_approp'), s25=g(2025, 'ytd_expended'), rf=rf,
              o26=g(2026, 'original_approp'),
              s26=g(2026, 'ytd_expended'), left=g(2026, 'available_budget'), r25=arec[2025],
              r26=arec[2026])
    p = json.load(open(os.path.join(TOPICS, 'contracted-building-services.json'), encoding='utf-8'))
    facts = {x['id']: x for x in p['facts']}
    for k, v in cw.items():
        if abs(float(facts[k]['value']['value']) - float(v)) > 0.006:
            bad.append('contracted-building-services %s: page %r, recomputed %r'
                       % (k, facts[k]['value']['value'], float(v)))
    # ---- every dollar, FY2026: each account row against the spreadsheet, the payees footed
    p = json.load(open(os.path.join(TOPICS, 'upkeep-surplus-every-dollar.json'), encoding='utf-8'))
    views = {v['key']: v for v in p['table']['views']}
    budget = lambda y, a=None: (col[(y, 'original_approp')] + col[(y, 'transfers_adjustments')]) \
        if a is None else (col[(y, a, 'original_approp')] + col[(y, a, 'transfers_adjustments')])
    for r in views['accounts']['rows']:
        a = None if r['label'] == 'Every account' else r['label'].rsplit('(', 1)[1].rstrip(')')
        g = (lambda y, c: col[(y, c)]) if a is None else (lambda y, c: col[(y, a, c)])
        want_row = [budget(2025, a), budget(2026, a), g(2025, 'ytd_expended'), g(2026, 'ytd_expended'),
                    g(2026, 'encumbrances'), g(2026, 'available_budget')]
        for cell, w in zip(r['cells'], want_row):
            if cell != ('-' if w < 0 else '') + money(w):
                bad.append('every-dollar %r: %s, the spreadsheet %s' % (r['label'][:40], cell, w))
    paid = sum(D(r['cells'][2].replace('$', '').replace(',', '').replace('-', '')) *
               (-1 if r['cells'][2].startswith('-') else 1)
               for k, v in views.items() if k.startswith('payees') for r in v['rows'])
    n_cells = sum(len(v['rows']) for k, v in views.items() if k.startswith('payees'))
    if abs(paid - col[(2026, 'ytd_expended')]) > D('0.5') * n_cells:   # each cell is whole dollars
        bad.append('every-dollar: the payee views foot to %s, the spreadsheet %s'
                   % (paid, col[(2026, 'ytd_expended')]))
    ch = p['chart']
    if abs(sum(x['value'] for x in ch['parts']) - float(col[(2026, 'available_budget')])) > 0.01:
        bad.append('every-dollar: the slices do not add up to what was left')
    cbs = '0100-3-300-4220-01-1-74-2-535006'
    if abs(ch['parts'][0]['value'] - float(col[(2026, cbs, 'available_budget')])) > 0.006:
        bad.append('every-dollar: the first slice is not contracted building services')
    br = p['also'][0]
    if abs(br['start']['value'] - float(col[(2025, 'available_budget')])) > 0.006 or \
            abs(br['end']['value'] - float(col[(2026, 'available_budget')])) > 0.006:
        bad.append('every-dollar: the bridge does not run from FY2025’s leftover to FY2026’s')
    # ---- usual purchases skipped: each row's four years, from the raw journal
    p = json.load(open(os.path.join(TOPICS, 'upkeep-skipped.json'), encoding='utf-8'))
    byname = defaultdict(D)
    for (py, y), v in pay.items():
        if py is not None:
            byname[(py.title(), y)] += v
    for r in p['table']['views'][0]['rows']:
        got = r['cells'][2:6]
        want_row = [money(byname[(r['label'], y)]) for y in YEARS]
        usual = sum(byname[(r['label'], y)] for y in YEARS[:-1]) / 3
        if got != want_row or r['cells'][6] != money(usual):
            bad.append('skipped %s: %s, recomputed %s and %s' % (r['label'], got, want_row, money(usual)))
        if not all(byname[(r['label'], y)] > 0 for y in YEARS[:-1]) or \
                byname[(r['label'], 2026)] >= usual / 2:
            bad.append('skipped %s is not paid every year and under half in FY2026' % r['label'])
    # ---- orders released unpaid, contracted building services, FY2026
    p = json.load(open(os.path.join(TOPICS, 'contracted-building-services.json'), encoding='utf-8'))
    pom = defaultdict(D)
    for r in rows:
        if r['account'] == '0100-3-300-4220-01-1-74-2-535006' and r['fiscal_year'] == '2026' \
                and r['source'] == 'POM':
            pom[r['doc_no']] += D(r['amount'])
    rel = {k: -v for k, v in pom.items() if v < 0}
    view = next(v for v in p['table']['views'] if v['key'] == 'released')
    if sorted(r['label'] for r in view['rows']) != sorted(rel):
        bad.append('released orders: the table does not list exactly the released orders')
    for r in view['rows']:
        if r['cells'][4] != money(rel.get(r['label'], 0)):
            bad.append('released order %s: %s, recomputed %s' % (r['label'], r['cells'][4], rel.get(r['label'])))
    if bad:
        print('verify_buildings_topics: %d problem(s)' % len(bad))
        print('\n'.join('  ' + b for b in bad))
        return 1
    print('verify_buildings_topics: %d facts, the budget book lines and every chart value '
          'recomputed from the period-13 spreadsheets, the raw journal and the book’s text'
          % (sum(len(v) for v in want.values()) + len(cw)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
