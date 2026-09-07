#!/usr/bin/env python3
"""Check the combined balance sheet we READ against the totals the report PRINTS.

    python3 scripts/verify_balance_sheet.py

WHAT THIS TABLE IS, AND WHY IT IS WORTH READING BY HAND

Everything else in this archive measures money MOVING -- appropriated, received, disbursed.
The COMBINED BALANCE SHEET is the only table in the annual reports that measures what the
town HOLDS: cash, receivables, warrants payable, reserves and undesignated fund balance, by
fund type, at 30 June. `notes/reference/EXTRACTION-GAPS.md` counted 488 figure rows across
fourteen editions and no dataset held any of them.

`pdf_tables.py` names this page as one where layout extraction recovers ZERO of its 61
money tokens, and the OCR of the older editions is worse than that -- FY2023's page reads
`TOTAL LIABILITIES/FLIND EQUITY` with `$` rendered as `5` throughout. So this is the same
method as `verify_special_revenue_read.py`: the page is RENDERED and READ, and the reading
is only written down if independent checks agree with it.

A figure read off an image is a READING. It has exactly the same status as OCR's output --
an instrument's product, not a published number -- and rule 13 applies to it in full.

THE FOUR CHECKS, AND WHY THEY ARE INDEPENDENT

  1. COLUMN FOOTING. Each fund column's detail rows must sum to the total the report
     prints for that column, in each of the three sections. Independent of us: the town
     printed the total.

  2. THE IDENTITY THE TABLE STATES. TOTAL LIABILITIES + TOTAL FUND EQUITY = TOTAL ASSETS,
     per column. The sheet also reprints TOTAL ASSETS as a TOTAL LIABILITIES/FUND EQUITY
     row, so the two printed rows must agree as well.

  3. THE CROSS-DOCUMENT CHECK, which is the strongest thing available here. The Special
     Revenue Funds schedule elsewhere in the SAME report prints a GRAND TOTAL balance
     carried forward, and that schedule carries the enterprise funds inside it. So

         SPECIAL REVENUE fund equity + ENTERPRISE fund equity == special revenue carried

     ties this page to a dataset already verified to the penny for thirteen years by a
     different instrument on different pages. It was confirmed to the cent on FY2011,
     FY2013, FY2019 and FY2022 before a single row was written down.

  4. THE LONG-TERM DEBT MIRROR. The account group prints the same figure as an asset
     (AMOUNT TO BE PROVIDED FOR RETIREMENT...) and as a liability (GENERAL OBLIGATION
     LONG TERM DEBT). They must match.

A YEAR THAT DOES NOT RECONCILE IS NOT WRITTEN DOWN HERE. `append_balance_sheet_year.py`
refuses it.

ROUNDING IS A PROPERTY OF THE PAGE, NOT A TOLERANCE WE GRANT

The GENERAL LONG-TERM DEBT column is printed to the DOLLAR in its total rows while its
detail rows sometimes carry cents (FY2022: detail $38,749,084.72, total $38,749,085). That
is the town's rounding, so that column alone is checked to within $1. Every other column is
checked to the cent. The allowance is named and confined rather than applied everywhere.
"""

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ = os.path.join(ROOT, 'sources', 'data', 'balance-sheet.csv')
TOTALS = os.path.join(ROOT, 'sources', 'data', 'balance-sheet-printed-totals.csv')
SPECIAL = os.path.join(ROOT, 'sources', 'data', 'special-revenue-printed-totals.csv')

FUNDS = ('general', 'special_revenue', 'enterprise', 'capital_project',
         'trust_agency', 'long_term_debt')
SECTION_TOTAL = {
    'assets': 'TOTAL ASSETS',
    'liabilities': 'TOTAL LIABILITIES',
    'fund_balances': 'TOTAL FUND EQUITY',
}
CENT = 0.005
DOLLAR = 1.0            # GENERAL LONG-TERM DEBT only; see the docstring.

# PRINTED SHEETS THAT DO NOT BALANCE THEMSELVES.
#
# Not every edition ties. Where the page itself is internally inconsistent that is a fact
# about the TOWN'S PRINTED REPORT, not an error in this reading, and it is recorded with
# the amount pinned EXACTLY -- if the discrepancy changes by a penny the check fails again,
# because a new error hiding inside an old allowance is what an exception list exists to
# prevent. Nothing here is adjusted to make it tie.
PRINTED_DEFECTS = {
    ('FY2019', 'trust_agency', 'identity'): (
        657297.35,
        'The FIDUCIARY TRUST and AGENCY column prints TOTAL ASSETS $3,841,163.85 and '
        'TOTAL LIABILITIES/FUND EQUITY $3,183,866.50 -- the page disagrees with itself by '
        'this amount. Both sides foot to their own printed totals: assets are '
        '$3,845,771.57 cash less $4,607.72 DUE FROM/TO GENERAL FUND, and equity is the '
        'single UNDESIGNATED figure $3,183,866.50 with TOTAL LIABILITIES $0.00. WHAT IS '
        'NOT ESTABLISHED: why. FY2020 and FY2021 both carry a RESERVED FOR ENDOWMENTS '
        'line in this column ($661,563.75 and $668,915.17) that FY2019 does not print, '
        'which is close to the gap and is a HYPOTHESIS, not a finding -- nothing here '
        'tests it. The document that would settle it is the audited financial statements '
        'for FY2019, which the annual report does not contain.'),
}


def num(v):
    v = (v or '').strip()
    return float(v) if v else 0.0


def blank(v):
    return not (v or '').strip()


def tol(fund):
    return DOLLAR if fund == 'long_term_debt' else CENT


def load():
    if not os.path.exists(READ):
        sys.exit(f'{os.path.relpath(READ, ROOT)} is missing')
    if not os.path.exists(TOTALS):
        sys.exit(f'{os.path.relpath(TOTALS, ROOT)} is missing')
    rows = list(csv.DictReader(open(READ, newline='', encoding='utf-8')))
    printed = list(csv.DictReader(open(TOTALS, newline='', encoding='utf-8')))
    return rows, printed


def check_edition(ed, rows, printed, special):
    """Return the number of failures for one edition, printing as it goes."""
    fails = 0
    mine = [r for r in rows if r['edition'] == ed]
    tot = {(p['total_row'], p['fund']): p for p in printed if p['edition'] == ed}
    pages = sorted({r['page_printed'] for r in mine}, key=int)
    print(f'\n{ed} — {len(mine)} figures, printed page{"s" if len(pages) > 1 else ""} '
          f'{", ".join(pages)}')

    if not tot:
        print(f'  FAIL  no printed totals recorded for {ed}')
        return 1

    # 1. COLUMN FOOTING, per section per fund.
    for section, label in SECTION_TOTAL.items():
        for fund in FUNDS:
            p = tot.get((label, fund))
            got = sum(num(r['amount']) for r in mine
                      if r['section'] == section and r['fund'] == fund)
            if p is None or blank(p['amount']):
                # A blank printed cell must mean nothing was read into it either.
                if abs(got) > CENT:
                    fails += 1
                    print(f'  FAIL  {label:29} {fund:16} read {got:>16,.2f} but the '
                          f'report prints no total in this column')
                continue
            want = num(p['amount'])
            d = got - want
            ok = abs(d) <= tol(fund)
            fails += 0 if ok else 1
            print(f'  {"ok  " if ok else "FAIL"}  {label:29} {fund:16} '
                  f'{got:>16,.2f}  printed {want:>16,.2f}  {d:+,.2f}')

    # 2. THE IDENTITY THE TABLE STATES, per fund.
    print('  --    the identity: TOTAL LIABILITIES + TOTAL FUND EQUITY = TOTAL ASSETS')
    for fund in FUNDS:
        a = tot.get(('TOTAL ASSETS', fund))
        if a is None or blank(a['amount']):
            continue
        assets = num(a['amount'])
        liab = num((tot.get(('TOTAL LIABILITIES', fund)) or {}).get('amount'))
        eq = num((tot.get(('TOTAL FUND EQUITY', fund)) or {}).get('amount'))
        d = liab + eq - assets
        known = PRINTED_DEFECTS.get((ed, fund, 'identity'))
        if abs(d) > tol(fund) and known and abs(abs(d) - known[0]) <= CENT:
            print(f'  note  {fund:16} {liab + eq:>16,.2f}  assets {assets:>16,.2f}  '
                  f'{d:+,.2f}')
            print(f'        EXAMINED — {known[1]}')
            continue
        ok = abs(d) <= tol(fund)
        fails += 0 if ok else 1
        print(f'  {"ok  " if ok else "FAIL"}  {fund:16} {liab + eq:>16,.2f}  '
              f'assets {assets:>16,.2f}  {d:+,.2f}')

        # ...and the sheet reprints TOTAL ASSETS at the foot. The two printed rows must
        # agree with each other, which is the town's own restatement of the same identity.
        rep = tot.get(('TOTAL LIABILITIES/FUND EQUITY', fund))
        if rep is not None and not blank(rep['amount']):
            d2 = num(rep['amount']) - (liab + eq)
            if abs(d2) > tol(fund):
                if known and abs(abs(num(rep['amount']) - assets) - known[0]) <= CENT:
                    pass  # the same examined defect, already reported above
                else:
                    fails += 1
                    print(f'  FAIL  {fund:16} the printed TOTAL LIABILITIES/FUND EQUITY '
                          f'row is {num(rep["amount"]):,.2f}, not {liab + eq:,.2f}')

    # 3. THE CROSS-DOCUMENT CHECK against the special revenue schedule.
    sr = special.get(ed)
    srf = num((tot.get(('TOTAL FUND EQUITY', 'special_revenue')) or {}).get('amount'))
    ent = num((tot.get(('TOTAL FUND EQUITY', 'enterprise')) or {}).get('amount'))
    if sr is None:
        print('  --    no special revenue GRAND TOTAL for this edition; cross-check '
              'not available')
    else:
        want = num(sr['carried'])
        d = srf + ent - want
        ok = abs(d) <= CENT
        fails += 0 if ok else 1
        print(f'  {"ok  " if ok else "FAIL"}  cross-check: special revenue + enterprise '
              f'fund equity {srf + ent:>16,.2f}')
        print(f'        vs the special revenue schedule\'s printed carried forward '
              f'{want:>16,.2f}  {d:+,.2f}')

    # 4. THE LONG-TERM DEBT MIRROR.
    asset = [r for r in mine if r['fund'] == 'long_term_debt' and r['section'] == 'assets']
    liab = [r for r in mine if r['fund'] == 'long_term_debt'
            and r['section'] == 'liabilities']
    if asset and liab:
        d = sum(num(r['amount']) for r in asset) - sum(num(r['amount']) for r in liab)
        ok = abs(d) <= DOLLAR
        fails += 0 if ok else 1
        print(f'  {"ok  " if ok else "FAIL"}  long-term debt appears as both an asset and '
              f'a liability; they differ by {d:+,.2f}')
    return fails


def main():
    rows, printed = load()
    special = {}
    if os.path.exists(SPECIAL):
        special = {r['edition']: r for r in
                   csv.DictReader(open(SPECIAL, newline='', encoding='utf-8'))}

    editions = sorted({r['edition'] for r in rows})
    if not editions:
        sys.exit('balance-sheet.csv holds no rows')

    fails = sum(check_edition(ed, rows, printed, special) for ed in editions)

    print(f'\n{len(editions)} edition(s) checked, {fails} failure(s)')
    if fails:
        sys.exit(1)
    n = sum(1 for k in PRINTED_DEFECTS if k[0] in editions)
    print('Every column foots to the total the report itself prints, the identity the')
    print('table states holds, and the special revenue and enterprise fund equity ties to')
    print('a schedule read from different pages by a different instrument.')
    if n:
        print(f'{n} printed defect{"" if n == 1 else "s"} above: the town\'s page '
              f'disagreeing with itself, pinned to')
        print('the penny and not adjusted away.')


if __name__ == '__main__':
    main()
