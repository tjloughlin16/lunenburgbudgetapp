"""The town's trust, agency and stabilization funds, as the accounting system prints them.

    python3 scripts/extract_trust_agency.py
    python3 scripts/extract_trust_agency.py --check

Writes `sources/data/trust-agency-balances.csv`.

WHY THIS OUTRANKS EVERYTHING ELSE WE HOLD ON THESE FUNDS.

Rule 13a: a sheet the accounting system printed is proof, a sheet somebody assembled is
not. Every other stabilization figure in this archive is read off a PHOTOGRAPH of a table
in an annual town report -- measured, de-skewed, and published only where the page's own
arithmetic closes, which is careful work and is still us reading a picture. This file is
MUNIS printing its own books: account number, fund name, beginning balance, revenue,
expenditure, remaining balance, with the system's own subtotals.

**And it agrees with the photographs to the cent.** Three funds can be compared directly
against `stabilization-balances.csv`, and all three match exactly:

    8136 vehicle equipment     $2,598,621.38
    8129 playground fund         $249,060.25
    8124 stabilization         $3,147,178.96

That is the strongest check this project has run on the table reader, and nothing was
built to make it happen -- the FY2025 annual report's closing balance is the FY2026
ledger's opening balance, read two entirely different ways.

WHAT IT SETTLES, AND WHAT IT DOES NOT.

It settles the CURRENT balances, this year's revenue and this year's spending, per fund.
It is one report at one date -- FY2026 through period 09, 31 March 2026 -- so it is not a
series and it says nothing about FY2011 to FY2024. The remedy is the same report for the
other years; it is a report MUNIS already produces.

It also settles a name this archive has carried a disagreement about for weeks. Account
8129 is `ZONING INCENTIVE STABILIZATION (TD BANKNORTH)` in the annual report and
`playground fund` in the ledger. Both are the town's own words for one account, and
`stabilization-balances.csv` has a `name_disagrees` column precisely for this. Neither is
corrected here: the document's name and the ledger's name are both recorded.

TWO THINGS TO KNOW BEFORE QUOTING A FIGURE FROM IT.

**Balances are CREDITS, so they print negative.** A fund holding $240,202.91 shows as
`-240202.91`. These are fund-balance accounts and a credit balance is money held. The CSV
stores the SIGN AS PRINTED and adds a `held` column with the sign flipped, because a
reader comparing to the annual report needs the positive number and a reader checking
against the ledger needs the printed one.

**`STABILIZATION FUNDS` is the ledger's grouping, not a legal category.** MUNIS files nine
accounts under that subtotal and two of them are not stabilization funds in the sense
anybody at Town Meeting means: `8137 opeb` is the other-post-employment-benefits trust and
`8125 conservation trust` is a conservation fund. Quoting the $9,061,421.24 subtotal as
"the stabilization funds" would be taking the system's filing decision for a statement
about what may be spent. The CSV records the group the report printed and nothing more.

THE CHECK. Both subtotals the report prints are recomputed from the rows beneath them, and
the script refuses to write if either fails to tie -- rule 13's "when an extract has a
total the source itself prints, reconcile to it".
"""
import argparse
import csv
import os
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'town-ledgers', 'fund-balances',
                   'trust-agency-fy2026-p09.xlsx')
OUT = os.path.join(ROOT, 'sources', 'data', 'trust-agency-balances.csv')
FY, PERIOD, AS_OF = 2026, 9, '2026-03-31'

# The columns the report sets, by position on Sheet2. Read once, written down here, and
# not inferred per run -- rule 13b's "name columns from a header you read and wrote down".
# Sheet2 row 5-7 prints: Beginning Balance 2025-07-01 | Revenue | Expenditure |
# Remaining Balance 2026-06-30.
COL = dict(account=0, name=1, beginning=3, revenue=5, expenditure=6, remaining=8)

FIELDS = ['account', 'name', 'group', 'held', 'beginning', 'revenue', 'expenditure',
          'remaining', 'fy', 'period', 'as_of', 'document']

TOL = 0.005


def cell(row, key):
    i = COL[key]
    return row[i] if i < len(row) else None


def num(v):
    return float(v) if isinstance(v, (int, float)) else None


def read():
    """Rows and the subtotals the report prints, in the order it prints them."""
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    try:
        rows = list(wb['Sheet2'].iter_rows(values_only=True))
    finally:
        wb.close()
    out, totals, pending = [], [], []
    for r in rows:
        a = cell(r, 'account')
        label = str(a).strip() if a is not None else ''
        name = str(cell(r, 'name') or '').strip()
        if label.isdigit():
            out.append(dict(
                account=label, name=' '.join(name.split()), group=None,
                beginning=num(cell(r, 'beginning')),
                revenue=num(cell(r, 'revenue')),
                expenditure=num(cell(r, 'expenditure')),
                remaining=num(cell(r, 'remaining'))))
            pending.append(out[-1])
            continue
        # A GROUP IS DEFINED BY ITS TRAILING SUBTOTAL, and by nothing else. There are no
        # heading rows on this report: `TRUST FUNDS` and `STABILIZATION FUNDS` appear
        # once each, in the NAME column, on a row carrying the group's figures in the
        # same columns the data rows use. So a row with no account number, a name, and a
        # beginning balance closes the group that has accumulated above it.
        if name and num(cell(r, 'beginning')) is not None and pending:
            totals.append(dict(label=name, beginning=num(cell(r, 'beginning')),
                               remaining=num(cell(r, 'remaining')), rows=pending))
            pending = []
    for t in totals:
        for r in t['rows']:
            r['group'] = t['label']
    return out, totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(SRC):
        print('missing %s' % os.path.relpath(SRC, ROOT), file=sys.stderr)
        return 1
    rows, totals = read()
    if not rows or not totals:
        print('read %d rows and %d subtotals -- the sheet is not the shape this expects'
              % (len(rows), len(totals)), file=sys.stderr)
        return 1

    # RECONCILE TO THE REPORT'S OWN SUBTOTALS, both of them, or refuse to write.
    bad = []
    for t in totals:
        for key in ('beginning', 'remaining'):
            got = sum(r[key] or 0.0 for r in t['rows'])
            if abs(got - t[key]) > TOL:
                bad.append('%s %s: rows sum to %.2f, the report prints %.2f'
                           % (t['label'], key, got, t[key]))
    if bad:
        print('DOES NOT TIE to the report\'s own totals:\n  %s' % '\n  '.join(bad),
              file=sys.stderr)
        return 1

    doc = os.path.relpath(SRC, ROOT)
    body = []
    for r in rows:
        body.append({
            'account': r['account'], 'name': r['name'], 'group': r['group'] or '',
            # The sign flipped, because a credit balance IS money held and every other
            # figure on the site is positive. Both are kept: this one to read, the
            # printed one to check.
            'held': round(-(r['beginning'] or 0.0), 2),
            'beginning': round(r['beginning'], 2) if r['beginning'] is not None else '',
            'revenue': round(r['revenue'], 2) if r['revenue'] is not None else '',
            'expenditure': round(r['expenditure'], 2) if r['expenditure'] is not None else '',
            'remaining': round(r['remaining'], 2) if r['remaining'] is not None else '',
            'fy': FY, 'period': PERIOD, 'as_of': AS_OF, 'document': doc})

    import io
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(body)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/extract_trust_agency.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d accounts, both subtotals tie to the report' % len(body))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote %s -- %d accounts' % (os.path.relpath(OUT, ROOT), len(body)))
    for t in totals:
        print('  %-22s %s accounts, %s held'
              % (t['label'], len(t['rows']), '${:,.2f}'.format(-t['beginning'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
