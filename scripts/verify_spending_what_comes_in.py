#!/usr/bin/env python3
"""Every figure in /analysis/spending-what-comes-in, recomputed by a SECOND ROUTE.

    python3 scripts/verify_spending_what_comes_in.py

The generator reads `munis-school-ytd.csv` in floats and imports its fund grouping from
build_sitting_on_money.py. This script does neither:

  * it reads the eight period-13 WORKBOOKS the Town delivered (openpyxl), not the extracted
    CSV, takes the fund from the ACCOUNT STRING rather than the fund column, and adds in
    Decimal;
  * it writes the fourteen funds out again rather than importing them, so a change to the
    shared table is something this script disagrees with rather than inherits;
  * it takes the 30 June 2026 balance from the annual report's 30 June 2023 figure forward,
    not from 30 June 2022, and the 30 June 2022 figure from the FY2022 report directly;
  * it checks the published payload, every registered conclusion figure, the stat row, the
    reconciliation against sitting-on-money's PUBLISHED balances, and the figures typed into
    this report's money-gaps.csv row against the payload (a gap row is prose that ships).
"""
import csv
import json
import os
import sys
from decimal import Decimal as D

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conclusions import check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'spending-what-comes-in.json')
SOM = os.path.join(ROOT, 'fy28', 'public', 'data', 'sitting-on-money.json')
BOOK = os.path.join(ROOT, 'sources', 'town-ledgers', 'expenses', 'glytdbud-expense-fy%d-p13-%s.xlsx')
YEARS = (2023, 2024, 2025, 2026)

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


def dm(v):
    if v is None:
        return D(0)
    s = str(v).strip()
    return D(s) if s not in ('', '-') else D(0)


def same(name, got, want, tol=D('0.5')):
    if abs(D(str(got)) - D(str(want))) > tol:
        bad.append('%s: payload %s, recomputed %s' % (name, got, want))


def fig(conc, cid, key, want, tol=D('0.5')):
    CHECKED.add((cid, key))
    same('%s/%s' % (cid, key), conc[cid]['figures'][key]['value'], want, tol)


def book(y, which):
    """(fund, function, type, description) -> Decimal YTD actual, from the workbook itself."""
    wb = openpyxl.load_workbook(BOOK % (y, which), read_only=True, data_only=True)
    out = {}
    head = None
    for row in wb.worksheets[0].iter_rows(values_only=True):
        if head is None:
            if row and any(isinstance(c, str) and c.strip() == 'ACCOUNT' for c in row):
                head = [str(c or '').strip() for c in row]
            continue
        rec = dict(zip(head, row))
        acct, typ = str(rec.get('ACCOUNT') or '').strip(), str(rec.get('TYPE') or '').strip()
        if not acct or typ not in ('R', 'E'):
            continue
        seg = acct.split('-')
        k = (seg[0], seg[3], typ, str(rec.get('ACCOUNT DESCRIPTION') or '').strip())
        # The special-funds workbook heads the column `YTD ACTUAL`, the general fund one
        # `YTD EXPENDED`; exactly one of the two must be present.
        cols = [c for c in ('YTD ACTUAL', 'YTD EXPENDED') if c in rec]
        if len(cols) != 1:
            bad.append('%s: no single YTD column in %s' % (BOOK % (y, which), head))
            return out
        out[k] = out.get(k, D(0)) + dm(rec.get(cols[0]))
    if not out:
        bad.append('nothing read from %s' % (BOOK % (y, which)))
    return out


def main():
    pay = json.load(open(PAYLOAD, encoding='utf-8'))
    conc = {c['id']: c for c in pay['conclusions']}
    bad.extend(check('spending-what-comes-in',
                     [dict(c, _allow=c.get('literals') or []) for c in pay['conclusions']]))

    sp = {y: book(y, 'special-school') for y in YEARS}
    gf = {y: book(y, 'gf-school') for y in YEARS}
    rin, rout = {}, {}
    for y in YEARS:
        for (f, _fn, t, _d), v in sp[y].items():
            if t == 'R':
                rin[(f, y)] = rin.get((f, y), D(0)) - v
            else:
                rout[(f, y)] = rout.get((f, y), D(0)) + v

    # ---- every fund, every year, against the payload -------------------------------
    pf = {r['fund']: r for r in pay['funds']}
    for f in sorted({f for f, _y in list(rin) + list(rout)}):
        if f not in pf:
            if any(rin.get((f, y), 0) or rout.get((f, y), 0) for y in YEARS):
                bad.append('fund %s moved money and is not in the payload' % f)
            continue
        for i, y in enumerate(YEARS):
            same('%s FY%d in' % (f, y), pf[f]['years'][i]['in'], rin.get((f, y), D(0)), D('0.01'))
            same('%s FY%d out' % (f, y), pf[f]['years'][i]['out'], rout.get((f, y), D(0)), D('0.01'))

    def net(f, ys=YEARS):
        return sum((rin.get((f, y), D(0)) - rout.get((f, y), D(0)) for y in ys), D(0))

    # ---- kinds ---------------------------------------------------------------------
    for k in pay['kinds']:
        fs = [f for f in pf if (FUNDS[f][0] if f in FUNDS else 'grants') == k['key']]
        same('kind %s net' % k['key'], k['net'], sum((net(f) for f in fs), D(0)), D('0.01'))

    # ---- balances, from the annual reports by a different starting point -----------
    ar = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'special-revenue-read.csv'), encoding='utf-8')):
        if r['group'] == 'SCHOOL DEPARTMENT' and r['fy'] in ('2022', '2023'):
            ar.setdefault(int(r['fy']), []).append(r)
    carried = {y: {r['fund']: dm(r['carried']) for r in ar[y]} for y in ar}
    bal22 = sum((carried[2022][n] for _c, n in FUNDS.values()), D(0))
    bal26 = sum((carried[2023][n] + net(f, (2024, 2025, 2026)) for f, (_c, n) in FUNDS.items()), D(0))
    som = json.load(open(SOM, encoding='utf-8'))
    sb = {r['fund']: r['balances'] for r in som['school_funds']}
    for f in FUNDS:
        for y in (2024, 2025, 2026):
            same('sitting-on-money %s FY%d change' % (f, y),
                 D(str(sb[f][str(y)])) - D(str(sb[f][str(y - 1)])), net(f, (y,)), D('0.01'))

    # ---- the conclusions -----------------------------------------------------------
    c = 'the-school-funds-drew-down'
    n14 = sum((net(f) for f in FUNDS), D(0))
    fig(conc, c, 'net', -n14)
    fig(conc, c, 'in', sum((rin.get((f, y), D(0)) for f in FUNDS for y in YEARS), D(0)))
    fig(conc, c, 'out', sum((rout.get((f, y), D(0)) for f in FUNDS for y in YEARS), D(0)))
    fig(conc, c, 'bal22', bal22)
    fig(conc, c, 'bal26', bal26)
    fig(conc, c, 'gifts', sum((net(f) for f, (k, _n) in FUNDS.items() if k == 'gifts'), D(0)))

    persist = [f for f in FUNDS if sum(1 for y in YEARS if net(f, (y,)) < 0) >= 3]
    fig(conc, 'three-funds-every-year', 'n', len(persist))

    c = 'extended-day-not-covering'
    fig(conc, c, 'short', -net('1312', (2024, 2025, 2026)))
    fig(conc, c, 'bal', carried[2023]['Extended Day Revolving Fund'] + net('1312', (2024, 2025, 2026)))

    c = 'athletics-fees-pay-a-share'
    g = {y: sum((v for (f, fn, t, _d), v in gf[y].items() if fn == '3510' and t == 'E'), D(0)) for y in YEARS}
    fund_out = sum((rout.get(('1301', y), D(0)) for y in YEARS), D(0))
    fees = sum((rin.get(('1301', y), D(0)) for y in YEARS), D(0))
    fig(conc, c, 'gf', sum(g.values(), D(0)))
    fig(conc, c, 'fund', fund_out)
    fig(conc, c, 'f25', rout[('1301', 2025)])
    fig(conc, c, 'g25', g[2025])
    fig(conc, c, 'share', D(100) * fees / (fund_out + sum(g.values(), D(0))), D('0.05'))

    c = 'lunch-is-federal-money'
    src = {}
    for y in YEARS:
        for (f, _fn, t, d), v in sp[y].items():
            if f == '2200' and t == 'R':
                src[d] = src.get(d, D(0)) - v
    tot = sum(src.values(), D(0))
    fig(conc, c, 'fed', D(100) * src['FEDERAL REVENUE THROUGH STATE'] / tot, D('0.05'))
    fig(conc, c, 'fee', D(100) * src['USER CHARGES'] / tot, D('0.05'))
    fig(conc, c, 'n26', -net('2200', (2026,)))
    fig(conc, c, 'b26', carried[2023]['School Lunch'] + net('2200', (2024, 2025, 2026)))

    for cc in pay['conclusions']:
        for k in cc['figures']:
            if (cc['id'], k) not in CHECKED:
                bad.append('%s/%s was never recomputed' % (cc['id'], k))

    # ---- the stat row --------------------------------------------------------------
    st = [s['value'] for s in pay['stats']]
    if st[0] != '$' + format(int(round(-n14)), ',d'):
        bad.append('stat 1 reads %s' % st[0])
    if st[1] != '%d of %d' % (len(persist), len(FUNDS)):
        bad.append('stat 2 reads %s' % st[1])
    if st[2] != conc['athletics-fees-pay-a-share']['figures']['share']['text']:
        bad.append('stat 3 disagrees with the athletics card')

    # ---- the figures typed into this report's gap row -------------------------------
    ar_in = sum((dm(r['receipts']) for r in ar[2023]), D(0))
    ar_out = sum((dm(r['disbursements']) for r in ar[2023]), D(0))
    led_in = sum((v for (k, v) in rin.items() if k[1] == 2023), D(0))
    led_out = sum((v for (k, v) in rout.items() if k[1] == 2023), D(0))
    gr26_in = sum((rin.get((f, 2026), D(0)) for f in pf if f not in FUNDS), D(0))
    gr26_out = sum((rout.get((f, 2026), D(0)) for f in pf if f not in FUNDS), D(0))
    row = next((r for r in csv.DictReader(open(os.path.join(DATA, 'money-gaps.csv'), encoding='utf-8'))
                if r['what'] == 'Which school special revenue funds the period-13 special funds report leaves out'),
               None)
    if row is None:
        bad.append('the gap row is gone from money-gaps.csv')
    else:
        for v in (ar_in, ar_out, led_in, led_out, gr26_in, gr26_out):
            txt = '$' + format(int(round(v)), ',d')
            if txt not in row['why']:
                bad.append('the gap row does not state %s, which the data now gives' % txt)

    if bad:
        print('FAILED, %d:' % len(bad))
        for x in bad:
            print('  ' + x)
        return 1
    n = sum(len(c['figures']) for c in pay['conclusions'])
    print('spending-what-comes-in: all %d conclusion figures across %d conclusions recomputed from '
          'the eight workbooks; every fund-year in the payload matches; sitting-on-money balances tie '
          'FY2024-FY2026; the gap row states the current figures' % (n, len(pay['conclusions'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
