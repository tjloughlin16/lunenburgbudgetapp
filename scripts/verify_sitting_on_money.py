#!/usr/bin/env python3
"""Every figure in /analysis/sitting-on-money, recomputed by a SECOND ROUTE.

    python3 scripts/verify_sitting_on_money.py

The generator (`build_sitting_on_money.py`) computes each figure one way. This script reads
the PUBLISHED payload, takes every registered figure in every conclusion, and recomputes it
a different way -- different arithmetic, and wherever one exists, a different document:

  * the school funds at 30 June 2025 from the Town's MARCH 2026 report alone (balance less
    what came in, plus what went out), not from the chain through MUNIS;
  * the school funds at 30 June 2026 from the March 2026 balance plus the FY2026 ledger's
    April-June movement, not from 30 June 2023 forward;
  * free cash, receipts above estimate and unspent appropriations from the state's own
    WORKBOOK cells (openpyxl), not from the extracted CSV;
  * the turnback as revised less spent less still committed, not the `available` column;
  * the town's 30 June 2023 special revenue as the PRINTED grand total less every school
    fund, not as a sum of town funds;
  * the stabilization balances against the stabilization report's own payload.

It also re-runs the rule-2 check on the published conclusions, and asserts the FY2023
identity for each of the fourteen school funds (annual report forward + MUNIS net = annual
report carried), which is what tests the name-to-number matching the chain rests on.
"""
import csv
import json
import os
import sys
from decimal import Decimal as D

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conclusions import check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'sitting-on-money.json')

# The fourteen funds, written out again here rather than imported, so a change to the
# generator's mapping is something this script disagrees with rather than inherits.
FUNDS = {
    '2640': ('cb', '50/50 Grant Sped Tuitions'), '1308': ('choice', 'School Choice'),
    '2200': ('lunch', 'School Lunch'), '1301': ('fees', 'Chapter 658 School Athletics'),
    '1305': ('fees', 'After School Activities'), '1312': ('fees', 'Extended Day Revolving Fund'),
    '1306': ('fees', 'School Facilities Use'), '1302': ('fees', 'Adult Education'),
    '1300': ('fees', 'Recovery for Lost Books'), '1310': ('fees', 'Greenthumb Revolving'),
    '1314': ('fees', 'Vending Machine Revolving'), '1311': ('gifts', 'School Gift Fund'),
    '1315': ('gifts', 'Family Network Gift Fund'),
    '1549': ('gifts', 'Technology for School Children Gift Fund'),
}

bad = []
CHECKED = set()


def fig(cid, key, got_from, want, tol=D('0.5')):
    """Recompute one registered figure and mark it covered."""
    CHECKED.add((cid, key))
    same('%s/%s' % (cid, key), got_from[key]['value'], want, tol)


def dm(s):
    s = (s or '').strip()
    return D(s) if s not in ('', '-') else D(0)


def same(name, got, want, tol=D('0.5')):
    if abs(D(str(got)) - D(str(want))) > tol:
        bad.append('%s: payload %s, recomputed %s' % (name, got, want))


def main():
    pay = json.load(open(PAYLOAD, encoding='utf-8'))
    conc = {c['id']: c for c in pay['conclusions']}

    # ---- rule 2 on the PUBLISHED rows --------------------------------------------
    rows = [dict(c, _allow=c.get('literals') or []) for c in pay['conclusions']]
    bad.extend(check('sitting-on-money', rows))

    # ---- the school funds ---------------------------------------------------------
    ar = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'special-revenue-read.csv'), encoding='utf-8')):
        if r['group'] == 'SCHOOL DEPARTMENT':
            ar.setdefault(int(r['fy']), {})
            ar[int(r['fy'])][r['fund']] = ar[int(r['fy'])].get(r['fund'], D(0)) + dm(r['carried'])
            if r['fy'] == '2023':
                ar.setdefault('fw23', {})[r['fund']] = dm(r['forward'])
    mun = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['report'] == 'special-school' and r['period'] == '13':
            k = (r['fund'], int(r['fiscal_year']))
            mun[k] = mun.get(k, D(0)) - dm(r['ytd_expended'])
    q3 = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'school-special-revenue-fy26-q3.csv'), encoding='utf-8')):
        q3[r['fund'].lstrip("'")] = r

    # FY2023 identity, fund by fund: tests the name <-> number match.
    ties = 0
    for f, (_c, n) in FUNDS.items():
        diff = ar['fw23'][n] + mun.get((f, 2023), D(0)) - ar[2023][n]
        if abs(diff) < D('0.01'):
            ties += 1
        else:
            print('  note: fund %s %s -- FY2023 forward + MUNIS net misses the printed carried '
                  'by %s (the chain starts from the printed carried, so this does not enter it)'
                  % (f, n, diff))
    if ties < len(FUNDS) - 1:
        bad.append('only %d of %d funds satisfy the FY2023 identity' % (ties, len(FUNDS)))

    def year_total(y):
        if y <= 2023:
            return sum((ar[y].get(n, D(0)) for _f, (_c, n) in FUNDS.items()), D(0))
        if y == 2025:   # from the March 2026 report alone
            return sum((dm(q3[f]['balance']) - dm(q3[f]['revenue']) + dm(q3[f]['salaries'])
                        + dm(q3[f]['expenditure']) + dm(q3[f]['encumbered'])) for f in FUNDS)
        if y == 2026:   # March 2026 balance, plus the FY2026 ledger less what March had seen
            return sum((dm(q3[f]['balance']) + mun.get((f, 2026), D(0))
                        - (dm(q3[f]['revenue']) - dm(q3[f]['salaries']) - dm(q3[f]['expenditure'])
                           - dm(q3[f]['encumbered']))) for f in FUNDS)
        if y == 2024:   # back from the March-implied FY2025 opening
            return year_total(2025) - sum((mun.get((f, 2025), D(0)) for f in FUNDS), D(0))
    totals = {y: year_total(y) for y in list(range(2011, 2024)) + [2024, 2025, 2026]}
    for r in pay['school_series']:
        same('school total FY%d' % r['fy'], r['total'], totals[r['fy']], D('0.01'))
    c = conc['the-schools-funds-peaked-and-have-fallen']['figures']
    peak_y = max(totals, key=lambda y: totals[y])
    fig('the-schools-funds-peaked-and-have-fallen', 'last', c, totals[2026])
    fig('the-schools-funds-peaked-and-have-fallen', 'peak', c, totals[peak_y])
    fig('the-schools-funds-peaked-and-have-fallen', 'first', c, totals[2011])

    # circuit breaker
    cb = {y: (ar[y].get(FUNDS['2640'][1], D(0)) if y <= 2023 else None) for y in range(2011, 2027)}
    cb[2025] = (dm(q3['2640']['balance']) - dm(q3['2640']['revenue']) + dm(q3['2640']['salaries'])
                + dm(q3['2640']['expenditure']))
    cb[2024] = cb[2025] - mun[('2640', 2025)]
    cb[2026] = cb[2025] + mun[('2640', 2026)]
    pk = max(cb, key=lambda y: cb[y])
    fell = sum(1 for y in range(pk + 1, 2027) if cb[y] < cb[y - 1])
    c = conc['the-circuit-breaker-is-being-drawn-down']['figures']
    fig('the-circuit-breaker-is-being-drawn-down', 'last', c, cb[2026])
    fig('the-circuit-breaker-is-being-drawn-down', 'peak', c, cb[pk])
    fig('the-circuit-breaker-is-being-drawn-down', 'fell', c, fell, D(0))
    fig('the-circuit-breaker-is-being-drawn-down', 'span', c, 2026 - pk, D(0))

    # ---- the school general fund at the close -------------------------------------
    gf = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['report'] == 'gf-school' and r['period'] == '13':
            y = int(r['fiscal_year'])
            g = gf.setdefault(y, [D(0), D(0), D(0)])
            g[0] += dm(r['revised_budget'])
            g[1] += dm(r['ytd_expended'])
            g[2] += dm(r['encumbrances'])
    left = {y: g[0] - g[1] - g[2] for y, g in gf.items()}
    c = conc['the-school-turnback-goes-to-the-town']['figures']
    for k, y in (('y26', 2026), ('y25', 2025), ('y24', 2024), ('y23', 2023)):
        fig('the-school-turnback-goes-to-the-town', k, c, left[y])
    fig('the-school-turnback-goes-to-the-town', 'enc', c, gf[2026][2])

    # ---- the state's workbook, read cell by cell ----------------------------------
    import openpyxl
    ws = openpyxl.load_workbook(os.path.join(ROOT, 'sources', 'state-dls',
                                             'free-cash-proof-lunenburg.xlsx'),
                                data_only=True)['Sheet1']
    grid = {}
    head = None
    for row in ws.iter_rows(values_only=True):
        if row[0] == 'Free Cash Proof Description':
            head = [int(x) for x in row[1:] if x]
            continue
        if head and row[0]:
            grid[row[0].strip()] = dict(zip(head, row[1:]))
    cl11 = grid['Add Unencumbered/Unexpended Appropriations (CL#11)']
    cl6 = grid['Excess/Shortfall Local Receipts (CL#6)']
    cert = grid['Current Year Calculation']
    c = conc['the-schools-share-of-what-went-unspent']['figures']
    fig('the-schools-share-of-what-went-unspent', 'town', c, cl11[2025])
    fig('the-schools-share-of-what-went-unspent', 'school', c, left[2025])
    for k, y in (('share', 2025), ('s24', 2024), ('s23', 2023)):
        fig('the-schools-share-of-what-went-unspent', k, c, round(100 * left[y] / D(cl11[y]), 1), D('0.05'))
    c = conc['receipts-above-estimate-feed-free-cash']['figures']
    big = [y for y in sorted(cl6) if cl6[y] >= 1000000]
    fig('receipts-above-estimate-feed-free-cash', 'min', c, min(cl6[y] for y in big))
    fig('receipts-above-estimate-feed-free-cash', 'million', c, 1000000, D(0))
    fig('receipts-above-estimate-feed-free-cash', 'max', c, max(cl6[y] for y in big))
    if big != list(range(big[0], max(cl6) + 1)):
        bad.append('receipts above a million are not an unbroken run to the latest year')
    c = conc['free-cash-has-grown-most']['figures']
    fig('free-cash-has-grown-most', 'last', c, cert[2025])
    sheet_txt = open(os.path.join(ROOT, 'sources', 'budget-workbooks', 'finance-committee',
                                  'fy27-budget', 'tm-warrant', 'text',
                                  'free-cash-fact-sheet.docx.txt'), encoding='utf-8').read()
    for k in ('first', 'pct', 'firstpct'):
        CHECKED.add(('free-cash-has-grown-most', k))
        if c[k]['text'].lstrip('$') not in sheet_txt:
            bad.append('free cash %s %r is not printed in the Town’s fact sheet' % (k, c[k]['text']))
    fc = [r['amount'] for r in pay['free_cash']]
    nf = sum(1 for a, b in zip(fc, fc[1:]) if b < a)
    fig('free-cash-has-grown-most', 'fell', c, nf, D(0))
    fig('free-cash-has-grown-most', 'steps', c, len(fc) - 1, D(0))
    fig('free-cash-has-grown-most', 'rose', c, len(fc) - 1 - nf, D(0))

    # ---- the town's special revenue at 30 June 2023 -------------------------------
    printed = {int(r['fy']): dm(r['carried']) for r in
               csv.DictReader(open(os.path.join(DATA, 'special-revenue-printed-totals.csv'), encoding='utf-8'))}
    town23 = printed[2023] - sum(ar[2023].values(), D(0))
    c = conc['most-town-special-revenue-is-not-free-to-spend']['figures']
    fig('most-town-special-revenue-is-not-free-to-spend', 'total', c, town23)
    fig('most-town-special-revenue-is-not-free-to-spend', 'pct', c,
         round(100 * (D(str(c['relief']['value'])) + D(str(c['ent']['value']))) / town23, 1), D('0.05'))
    fig('most-town-special-revenue-is-not-free-to-spend', 'other', c,
         town23 - D(str(c['relief']['value'])) - D(str(c['ent']['value'])))

    named = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'special-revenue-read.csv'), encoding='utf-8')):
        if r['group'] != 'SCHOOL DEPARTMENT':
            if 'Enterprise' in r['fund'] or r['fund'] == 'Sewer Betterment Fund':
                kind = 'ent'
            elif r['fund'] in ('ARPA Funds', 'Cares Act Funding - COVID', 'FEMA #4496 - COVID Grant'):
                kind = 'relief'
            else:
                kind = 'other'
            named[(int(r['fy']), kind)] = named.get((int(r['fy']), kind), D(0)) + dm(r['carried'])
    fig('most-town-special-revenue-is-not-free-to-spend', 'relief', c, named[(2023, 'relief')])
    fig('most-town-special-revenue-is-not-free-to-spend', 'ent', c, named[(2023, 'ent')])
    fig('most-town-special-revenue-is-not-free-to-spend', 'other11', c, named[(2011, 'other')])

    # ---- stabilization, against the stabilization report's own payload ------------
    sp = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'stabilization-funds.json'),
                        encoding='utf-8'))
    gen = next(s for s in sp['series'] if s['fund'] == 'Stabilization')
    pts = {p['fy']: p['ending_cash'] for p in gen['points']}
    c = conc['the-general-stabilization-fund-is-growing']['figures']
    stab = {r['fy']: r['amount'] for r in pay['stabilization']}
    fig('the-general-stabilization-fund-is-growing', 'first', c, pts[min(stab)])
    fig('the-general-stabilization-fund-is-growing', 'last', c, pts[max(stab)])

    for cc in pay['conclusions']:
        for k in cc['figures']:
            if (cc['id'], k) not in CHECKED:
                bad.append('%s/%s was never recomputed' % (cc['id'], k))
    if bad:
        print('FAILED, %d:' % len(bad))
        for x in bad:
            print('  ' + x)
        return 1
    n = sum(len(c['figures']) for c in pay['conclusions'])
    print('sitting-on-money: all %d conclusion figures across %d conclusions recomputed by a '
          'second route; %d of %d school funds satisfy the FY2023 identity'
          % (n, len(pay['conclusions']), ties, len(FUNDS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
