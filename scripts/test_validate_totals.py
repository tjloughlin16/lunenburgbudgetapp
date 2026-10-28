#!/usr/bin/env python3
"""VALIDATE and TRIAGE against the pages a person checked by hand, and against proven pages.

The answer key (PLAN-ANNUAL-REPORT-PIPELINE.md section 7), all of it measured, none of it
typed from memory:

  2000 report, PDF 67    the balance sheet: every printed total and both sides of the
                         balance close
  2000 report, PDF 86-88 the Colonial dividends print $12,276.93 over cells summing to
                         $12,274.58 -- the town's own arithmetic, off $2.35; the `TOTAL:` block
                         closes once the unlabeled subtotal above it is seen as one; the
                         Century block continues across two page breaks; one cell holds two
                         rows' figures
  FY2020, PDF 41         `($21,00)`: a comma scanned for a decimal point
  FY2011, 29 pages       PROVEN pages: every open total on them is a false alarm, counted

Needs the Textract output in build/textract/out (gitignored); without it the test fails rather
than passing on nothing.

    python3 scripts/test_validate_totals.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import report_review as R  # noqa: E402
import triage_totals as T  # noqa: E402
import validate_totals as V  # noqa: E402

Y2000 = '2000 Annual Town Report'
FY2011 = '4117-fy-2011-annual-town-report'
FY2020 = '4127-fy-2020-annual-town-report'
fails = []


def expect(ok, what):
    print(('  ok    ' if ok else '  FAIL  ') + what)
    if not ok:
        fails.append(what)


def one(found, ref, column):
    hit = [(c, t) for c, t in found if c.ref == ref and c.column.startswith(column)]
    return hit[0] if len(hit) == 1 else (None, None)


def main():
    for stem in (Y2000, FY2011, FY2020):
        if not (V.OUT / f'{stem}.cells.tsv').exists():
            sys.exit(f'FAIL: no Textract cells for {stem}; nothing was tested')

    print('2000 report, the balance sheet (PDF 67)')
    checks, _ = V.validate(Y2000, {67})
    totals = [c for c in checks if c.grouping != 'balance']
    balance = [c for c in checks if c.grouping == 'balance']
    expect(len(totals) == 19 and all(c.status == 'closed' for c in totals),
           f'19 printed totals, all closed (got {len(totals)}, '
           f'{sum(c.status == "closed" for c in totals)} closed)')
    expect(len(balance) == 5 and all(c.status == 'closed' for c in balance),
           f'assets = liabilities + fund equity in all 5 columns (got {len(balance)})')
    expect(any(c.label.startswith('TOTAL LIABILITIES/FUND') and c.grouping == 'of_totals' for c in totals),
           'the last total closes on the two totals above it, not on rows')

    print('2000 report, the trust funds (PDF 86-88)')
    found, checks = T.run(Y2000, {86, 87, 88})
    c, t = one(found, 'p86r15', 'DIVIDENDS')
    expect(c is not None and c.difference == '2.35' and c.printed == '12,276.93' and c.computed == '12,274.58',
           'Colonial dividends: printed 12,276.93 over cells summing to 12,274.58, off 2.35')
    expect(t is not None and t.triage == 'printed_error' and not t.settled,
           'triaged a printed-error SUSPECT, not settled (a second reader must agree)')
    c, t = one(found, 'p88r17', 'BOOK')
    expect(t is not None and t.triage == 'misread' and t.settled and 'two figures' in t.how,
           'Century book balance: two figures in one cell, settled as a misread')
    expect(len(found) == 2, f'nothing else on these pages is open (got {len(found)})')
    sub = [c for c in checks if c.ref == 'p86r28']
    expect(sub and all(c.status == 'closed' for c in sub), 'the unlabeled row 28 is read as a subtotal')
    tot = [c for c in checks if c.ref == 'p86r42']
    expect(tot and all(c.status == 'closed' for c in tot), 'so `TOTAL:` closes on the block below it')
    century = [c for c in checks if c.ref == 'p88r17' and c.status == 'closed']
    expect(any(i.startswith('p87') for c in century for i in c.items),
           'the Century block is summed across the page break from PDF 87')
    pbhg = [c.column for c in checks if c.ref == 'p86r45']
    expect(len(pbhg) == 2, f'a `$ -` under a column with no rows in the block is not a check: {pbhg}')
    grand = [c for c in checks if c.label.startswith('GRAND TOTAL TRUST')]
    expect(len(grand) == 2 and all(c.status == 'closed' for c in grand),
           'both grand totals of trust funds close (the block totals, and the summary list)')

    print('2000 report, the debt schedule (PDF 89)')
    checks, _ = V.validate(Y2000, {89})
    debt = [c for c in checks if c.ref == 'p89r23' and c.column == '2006']
    expect(debt and debt[0].grouping == 'of_totals' and debt[0].difference == '100.00',
           'TOTAL DEBT is measured on the two grand totals the other columns close on: off 100.00 for 2006')

    print('FY2020, PDF 41')
    found, _ = T.run(FY2020, {41})
    expect(len(found) == 1 and found[0][1].settled and 'comma' in found[0][1].how,
           '`($21,00)` re-read as -21.00, and the one open total closes')

    print('FY2011, 29 proven pages: open totals are false alarms')
    found, checks = T.run(FY2011)
    unsettled = [(c, t) for c, t in found if not t.settled]
    elsewhere = [c.ref for c, t in unsettled if c.page not in (76, 77)]
    print(f'        {len(checks)} totals, {len(found)} open, {len(unsettled)} unsettled '
          f'(on the two debt schedules, PDF 76-77, where Textract misplaces cells)')
    expect(not elsewhere, f'no unsettled false alarm outside the debt schedules: {elsewhere}')
    expect(not [c for c, t in found if t.triage == 'printed_error' and c.page not in (76, 77)],
           'no proven page outside them is called a printed error')
    expect(not [c for c, t in found if c.ref == 'p65r7'],
           '`Total Insurance` prints a balance only on the total: its rows have none to sum, so no check')

    print('the register keeps a person\'s verdict')
    rows, _ = R.review(FY2020)
    old = [dict(rows[0], verdict='misread', decided_by='TJ', note='checked on the scan')]
    merged = R.merge(old, rows, {rows[0]['sha256']})
    expect(merged[0]['verdict'] == 'misread' and merged[0]['decided_by'] == 'TJ',
           'verdict and decided_by survive a rerun')
    gone = R.merge(old, [], {rows[0]['sha256']})
    expect(len(gone) == 1, 'a decided row stays even when its check stops firing')
    expect(not R.merge([dict(rows[0])], [], {rows[0]['sha256']}), 'an undecided row that stopped firing goes')

    print('every case holds' if not fails else f'{len(fails)} FAILED')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
