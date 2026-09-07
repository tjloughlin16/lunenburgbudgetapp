#!/usr/bin/env python3
"""Check the enterprise-funds combining balance sheet we READ against what it PRINTS.

    python3 scripts/verify_enterprise_balance_sheet.py

WHAT THIS TABLE IS -- AND WHAT IT IS NOT

The COMBINING BALANCE SHEET -- ENTERPRISE FUNDS is what the town's four enterprise funds
HOLD at 30 June: Sewer, Water, Solid Waste and PEG Access, side by side, with a
memorandum-only total column. FY2024 and FY2025 print this sheet and print NO town-wide
combined balance sheet at all, which is why it needed a dataset of its own.

RULE 11 APPLIES WITH FORCE. An enterprise fund is RATEPAYER money -- sewer and water user
charges, betterments, trash fees, cable franchise money. Nothing in this table is available
to the town's general operations, and none of these balances is a tax dollar. The town-wide
balance sheet in `balance-sheet.csv` carries an `enterprise` COLUMN for FY2011-FY2023; this
is a different table with a different population (four named funds, not one fund type) and
the two must never be appended to one another.

THIS IS NOT THE SAME DATASET AS balance-sheet.csv. Different columns, different meanings.

A figure read off a rendered page is a READING -- an instrument's product, not a published
number -- and rule 13 applies to it in full. So nothing is written down that these checks
do not confirm.

THE FIVE CHECKS

  1. COLUMN FOOTING. Each fund column's detail rows must sum to the total the sheet prints
     for that column, in each of the three sections. Independent of us: the town printed
     the total.

  2. THE IDENTITY THE SHEET STATES. Total Liabilities + Total Fund Equity = Total Assets,
     per column -- and the sheet reprints Total Assets at its foot as
     `Total Liabilities and Fund Equity`, so the town's own two rows must agree too.

  3. THE PRINTED PROOF ROW. The sheet carries its own self-check row at the foot, printed
     as zero in every column. Rule 13: reconcile to a total the source itself prints. The
     Proof is read as (Total Assets - Total Liabilities and Fund Equity) and must equal the
     zero the town printed.

  4. THE MEMORANDUM CROSS-FOOT. The Totals (Memorandum Only) column must equal the four
     fund columns added across -- checked on every total row AND on every detail line.
     This is what catches FY2024's printed defect below.

  5. FY2024 PRINTS THE SAME SHEET TWICE, on printed pages 21 and 28. Both printings were
     transcribed independently and every figure in them must agree. That is a free
     cross-check the town gave us and it is used as one.

A YEAR THAT DOES NOT TIE IS NOT WRITTEN DOWN HERE.
`append_enterprise_balance_sheet_year.py` refuses it.

WHAT IS RECORDED RATHER THAN ADJUSTED

Every cell here is checked to the CENT. There is no rounding allowance, because unlike the
town-wide sheet's long-term debt column nothing on this page is printed to the dollar.
"""

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ = os.path.join(ROOT, 'sources', 'data', 'enterprise-balance-sheet.csv')
TOTALS = os.path.join(ROOT, 'sources', 'data',
                      'enterprise-balance-sheet-printed-totals.csv')

FUNDS = ('sewer', 'water', 'solid_waste', 'peg_access')
MEMO = 'total_memorandum'
ALL_COLS = FUNDS + (MEMO,)
SECTION_TOTAL = {
    'assets': 'TOTAL ASSETS',
    'liabilities': 'TOTAL LIABILITIES',
    'fund_equity': 'TOTAL FUND EQUITY',
}
CENT = 0.005

# PRINTED SHEETS THAT DO NOT CROSS-FOOT.
#
# Where the page itself is internally inconsistent that is a fact about the TOWN'S PRINTED
# REPORT, not an error in this reading, and it is recorded with the amount pinned EXACTLY.
# If the discrepancy changes by a penny the check fails again, because a new error hiding
# inside an old allowance is exactly what an exception list exists to prevent. Nothing here
# is adjusted to make it tie.
#
# Keyed (edition, check, line).
PRINTED_DEFECTS = {
    ('FY2024', 'memo_cross_foot', 'Reserved for expenditures'): (
        102000.00,
        'The Totals (Memorandum Only) column prints 502,000.00 on the '
        '`Reserved for expenditures` line while the only fund column carrying a figure on '
        'that line is Sewer at 400,000.00 -- the memorandum column is 102,000.00 higher '
        'than the funds add to. It is offset EXACTLY on the line below: '
        '`Unreserved retained earnings` prints 2,973,842.15 in the memorandum column while '
        'the four fund columns add to 3,075,842.15, which is 102,000.00 LOWER. The two '
        'errors cancel, which is why Total Fund Equity (3,483,633.65), Total Assets, the '
        'identity and the printed PROOF row all still tie in every column. Both printings '
        '(pages 21 and 28) carry it identically, so it is not a page-specific misprint. '
        'WHAT IS NOT ESTABLISHED: which of the two presentations is right, or what the '
        '102,000.00 is. A reservation of 102,000.00 sitting in a fund column that prints '
        'blank, a memorandum column keyed to a different worksheet row, and a '
        'reclassification made only in the total column all fit this signature equally '
        'well, and nothing on the page distinguishes them. The document that would settle '
        'it is the Town Accountant\'s FY2024 trial balance for the enterprise funds, which '
        'the annual report does not contain.'),
    ('FY2024', 'memo_cross_foot', 'Unreserved retained earnings'): (
        102000.00,
        'The offsetting half of the Reserved for expenditures defect above; see that '
        'entry. The memorandum column prints 2,973,842.15 where the four fund columns add '
        'to 3,075,842.15.'),
}


def num(v):
    v = (v or '').strip()
    return float(v) if v else 0.0


def load():
    for p in (READ, TOTALS):
        if not os.path.exists(p):
            sys.exit(f'{os.path.relpath(p, ROOT)} is missing')
    rows = list(csv.DictReader(open(READ, newline='', encoding='utf-8')))
    printed = list(csv.DictReader(open(TOTALS, newline='', encoding='utf-8')))
    return rows, printed


def defect(ed, check, line, delta):
    """Return the recorded defect if `delta` matches it exactly, else None."""
    known = PRINTED_DEFECTS.get((ed, check, line))
    if known and abs(abs(delta) - known[0]) <= CENT:
        return known
    return None


def check_printing(ed, printing, mine, tot, out):
    """Checks 1-4 for ONE printing of the sheet. Returns the failure count."""
    fails = 0
    for section, label in SECTION_TOTAL.items():
        for fund in ALL_COLS:
            p = tot.get((label, fund))
            got = sum(num(r['amount']) for r in mine
                      if r['section'] == section and r['fund'] == fund)
            if p is None:
                fails += 1
                out(f'  FAIL  {label:29} {fund:17} the sheet prints no total in this '
                    f'column and {got:,.2f} was read into it')
                continue
            want = num(p['amount'])
            d = got - want
            ok = abs(d) <= CENT
            fails += 0 if ok else 1
            out(f'  {"ok  " if ok else "FAIL"}  {label:29} {fund:17} '
                f'{got:>16,.2f}  printed {want:>16,.2f}  {d:+,.2f}')

    out('  --    the identity: Total Liabilities + Total Fund Equity = Total Assets')
    for fund in ALL_COLS:
        a = tot.get(('TOTAL ASSETS', fund))
        if a is None:
            continue
        assets = num(a['amount'])
        liab = num((tot.get(('TOTAL LIABILITIES', fund)) or {}).get('amount'))
        eq = num((tot.get(('TOTAL FUND EQUITY', fund)) or {}).get('amount'))
        d = liab + eq - assets
        ok = abs(d) <= CENT
        fails += 0 if ok else 1
        out(f'  {"ok  " if ok else "FAIL"}  {fund:17} {liab + eq:>16,.2f}  '
            f'assets {assets:>16,.2f}  {d:+,.2f}')
        rep = tot.get(('TOTAL LIABILITIES AND FUND EQUITY', fund))
        if rep is not None:
            d2 = num(rep['amount']) - (liab + eq)
            if abs(d2) > CENT:
                fails += 1
                out(f'  FAIL  {fund:17} the printed Total Liabilities and Fund Equity row '
                    f'is {num(rep["amount"]):,.2f}, not {liab + eq:,.2f}')

    out('  --    the PROOF row the sheet prints about itself')
    for fund in ALL_COLS:
        p = tot.get(('PROOF', fund))
        a = tot.get(('TOTAL ASSETS', fund))
        r = tot.get(('TOTAL LIABILITIES AND FUND EQUITY', fund))
        if p is None or a is None or r is None:
            fails += 1
            out(f'  FAIL  PROOF {fund:17} the sheet prints no Proof for this column')
            continue
        proof = num(a['amount']) - num(r['amount'])
        d = proof - num(p['amount'])
        ok = abs(d) <= CENT
        fails += 0 if ok else 1
        out(f'  {"ok  " if ok else "FAIL"}  PROOF {fund:17} recomputed {proof:>10,.2f}  '
            f'printed {num(p["amount"]):>10,.2f}  {d:+,.2f}')

    out('  --    the memorandum column against the four fund columns, added across')
    for label in ('TOTAL ASSETS', 'TOTAL LIABILITIES', 'TOTAL FUND EQUITY',
                  'TOTAL LIABILITIES AND FUND EQUITY'):
        memo = tot.get((label, MEMO))
        if memo is None:
            continue
        across = sum(num((tot.get((label, f)) or {}).get('amount')) for f in FUNDS)
        d = across - num(memo['amount'])
        ok = abs(d) <= CENT
        fails += 0 if ok else 1
        out(f'  {"ok  " if ok else "FAIL"}  {label:33} across {across:>16,.2f}  '
            f'memorandum {num(memo["amount"]):>16,.2f}  {d:+,.2f}')

    seen = []
    for r in mine:
        key = (r['section'], r['line'])
        if key not in seen:
            seen.append(key)
    for section, line in seen:
        cells = {r['fund']: num(r['amount']) for r in mine
                 if r['section'] == section and r['line'] == line}
        if MEMO not in cells:
            continue
        across = sum(cells.get(f, 0.0) for f in FUNDS)
        d = across - cells[MEMO]
        if abs(d) <= CENT:
            continue
        known = defect(ed, 'memo_cross_foot', line, d)
        if known:
            out(f'  note  {section}/{line}: across {across:,.2f}, memorandum '
                f'{cells[MEMO]:,.2f}, {d:+,.2f}')
            out(f'        EXAMINED — {known[1]}')
            continue
        fails += 1
        out(f'  FAIL  {section}/{line}: the four fund columns add to {across:,.2f} but '
            f'the memorandum column prints {cells[MEMO]:,.2f}  ({d:+,.2f})')
    return fails


def check_edition(ed, rows, printed):
    fails = 0
    mine = [r for r in rows if r['edition'] == ed]
    prints = sorted({int(r['printing']) for r in mine})
    pages = ', '.join(sorted({f"{r['page_printed']} (pdf {r['page_pdf']})" for r in mine},
                             key=lambda s: int(s.split()[0])))
    print(f'\n{ed} — {len(mine)} figures, '
          f'{len(prints)} printing{"s" if len(prints) > 1 else ""} on printed page{"s" if len(prints) > 1 else ""} {pages}')

    for pr in prints:
        sub = [r for r in mine if int(r['printing']) == pr]
        tot = {(p['total_row'], p['fund']): p for p in printed
               if p['edition'] == ed and int(p['printing']) == pr}
        if not tot:
            print(f'  FAIL  printing {pr}: no printed totals recorded')
            fails += 1
            continue
        if len(prints) > 1:
            pg = sub[0]['page_printed']
            print(f'  ..    printing {pr}, printed page {pg}')
        fails += check_printing(ed, pr, sub, tot, print)

    # 5. THE TWO PRINTINGS MUST AGREE, figure for figure.
    if len(prints) > 1:
        base = prints[0]
        bmap = {(r['section'], r['line'], r['fund']): r['amount']
                for r in mine if int(r['printing']) == base}
        for pr in prints[1:]:
            omap = {(r['section'], r['line'], r['fund']): r['amount']
                    for r in mine if int(r['printing']) == pr}
            diffs = [k for k in set(bmap) | set(omap)
                     if abs(num(bmap.get(k)) - num(omap.get(k))) > CENT
                     or (k in bmap) != (k in omap)]
            tb = {(p['total_row'], p['fund']): p['amount'] for p in printed
                  if p['edition'] == ed and int(p['printing']) == base}
            to = {(p['total_row'], p['fund']): p['amount'] for p in printed
                  if p['edition'] == ed and int(p['printing']) == pr}
            tdiffs = [k for k in set(tb) | set(to)
                      if abs(num(tb.get(k)) - num(to.get(k))) > CENT
                      or (k in tb) != (k in to)]
            ok = not diffs and not tdiffs
            fails += 0 if ok else (len(diffs) + len(tdiffs))
            print(f'  {"ok  " if ok else "FAIL"}  printings {base} and {pr} agree: '
                  f'{len(bmap)} figures and {len(tb)} printed totals compared')
            for k in sorted(diffs):
                print(f'  FAIL  printing {base} has {bmap.get(k, "(absent)")} and '
                      f'printing {pr} has {omap.get(k, "(absent)")} for {k}')
            for k in sorted(tdiffs):
                print(f'  FAIL  printed total {k}: {tb.get(k, "(absent)")} vs '
                      f'{to.get(k, "(absent)")}')
    return fails


def main():
    rows, printed = load()
    editions = sorted({r['edition'] for r in rows})
    if not editions:
        sys.exit('enterprise-balance-sheet.csv holds no rows')
    fails = sum(check_edition(ed, rows, printed) for ed in editions)
    print(f'\n{len(editions)} edition(s) checked, {fails} failure(s)')
    if fails:
        sys.exit(1)
    n = sum(1 for k in PRINTED_DEFECTS if k[0] in editions)
    print('Every column foots to the total the sheet itself prints, the identity the sheet')
    print('states holds, the sheet\'s own printed Proof row reconciles, and FY2024\'s two')
    print('printings agree figure for figure.')
    if n:
        print(f'{n} printed defect{"" if n == 1 else "s"} noted above: the town\'s page '
              f'disagreeing with itself, pinned to')
        print('the penny and not adjusted away.')
    print('These are RATEPAYER funds. Nothing here is available to the general fund.')


if __name__ == '__main__':
    main()
