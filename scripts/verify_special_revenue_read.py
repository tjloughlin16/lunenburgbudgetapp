#!/usr/bin/env python3
"""Check the special revenue schedule we READ against the totals the report PRINTS.

    python3 scripts/verify_special_revenue_read.py

WHY THERE IS A SECOND DATASET FOR THE SAME TABLE

`special-revenue-funds.csv` is produced by `extract_special_revenue.py` from OCR geometry.
It is the reproducible one — a script makes it, `--check` proves it still does — and **not
one of its sixteen years reconciles to its own printed grand total.**

The reason is not the extractor, which was proved to capture every amount the OCR produced
(FY2022: 483 amounts, identical totals). The reason is that macOS Vision drops a handful of
cells per page and occasionally misreads a digit. On FY2022 page 33 it dropped exactly one
value out of about seventy — `Adult Education` receipts, $3,330.00 — and on page 34 it read
`Insurance Recoveries - Police` disbursements as $19,726.17 where the page says
$19,725.17. A 99% instrument still cannot tie to a printed total.

**And it misread the target as well as the data.** The printed GRAND TOTAL for receipts is
$9,235,154.01; the OCR recorded $9,236,164.01, so the reconciliation was being measured
against a number that was itself wrong by $1,010.

So this dataset is the pages READ DIRECTLY — rendered at 2x and transcribed. That is a
different instrument, not a better version of the same one, which is why it is a separate
file rather than a correction applied to the first.

WHAT MAKES IT TRUSTWORTHY, WHICH IS NOT THAT A MODEL READ IT

A figure read off an image is a READING. It has exactly the same status as the OCR's — an
instrument's output, not a published number — and rule 13 applies to it in full. It becomes
trustworthy only because two independent things check it, and both are in this script:

  1. **The report's own printed GRAND TOTAL.** Four columns, and all four must tie. This is
     independent of the transcription: it was printed by the town, not derived by us.
  2. **The identity the table itself states.** forward + receipts − disbursements =
     carried forward, on every row. A transcription error in any one cell breaks it.

Passing one of those could be luck. Passing both, on 167 rows and four column totals, is
not — a wrong digit that survives the row identity has to be compensated by another wrong
digit in the same row, and then still has to leave the column total unchanged.

**A year that does not tie is not written down as data.** It stays out until it does.
"""

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ = os.path.join(ROOT, 'sources', 'data', 'special-revenue-read.csv')
TOTALS = os.path.join(ROOT, 'sources', 'data', 'special-revenue-printed-totals.csv')
COLS = ('forward', 'receipts', 'disbursements', 'carried')

# CHAIN BREAKS WE HAVE EXAMINED, with the amount and what explains it.
#
# The year chain assumes a fund's closing balance is next year's opening balance. Usually
# it is. When it is not, that is a fact about the TOWN'S BOOKS rather than an error in
# this dataset — but it must never be assumed to be, so an exception is recorded only with
# the amount pinned and a decomposition that accounts for all of it.
#
# The amount is matched EXACTLY. If the break changes by a penny the check fails again,
# because a new discrepancy hiding inside an old allowance is exactly what an exception
# list is for preventing.
CHAIN_EXCEPTIONS = {
    ('FY2022', 'FY2023'): (
        17861.24,
        'The town re-cut its grant funds BY YEAR between these reports — `Title I #305` '
        'becomes `Title I #305 - FY22`, `- FY21`, `- FY20`, and the same for PL 94-142, '
        'Title IV, Teacher Quality and others. BOTH YEARS TIE TO THEIR OWN PRINTED GRAND '
        'TOTAL, so neither reading is in doubt: the two reports disagree with each other. '
        'Nothing here establishes WHY the town restated, and this dataset does not '
        'speculate.'),
}


def decompose(rows, a, b):
    """Account for a chain break, per fund, COMPUTED — never typed.

    The first version of this note carried the per-fund figures in its prose and one of
    them was wrong: it said $14,859.26 against the Firefighter Safety Equipment Grant
    where the answer is $14,869.10. The cause is worth more than the correction. The
    diagnostic built `{fund: amount}` as a dict comprehension, and FY2023 prints TWO rows
    named `Firefighter Safety Equipment Grant` — $9.84 and $14,869.10 — so the second
    silently replaced the first. A duplicate key in a source nobody promised was unique.

    Then the wrong figure was typed into a docstring, where nothing could ever check it.
    Rule 2 exists for exactly this, and an agent reading the same data found it.
    """
    def bag(fy, col):
        out = {}
        for r in rows:
            if r['fy'] == str(fy):
                # `+=`, not assignment: fund names are NOT unique within a year.
                out[r['fund']] = out.get(r['fund'], 0.0) + num(r[col])
        return out
    was, now = bag(a, 'carried'), bag(b, 'forward')
    added = sum(v for k, v in now.items() if k not in was)
    dropped = sum(v for k, v in was.items() if k not in now)
    restated = sum(now[k] - was[k] for k in set(was) & set(now))
    biggest = max(((now[k] - was[k], k) for k in set(was) & set(now)),
                  key=lambda t: abs(t[0]), default=(0.0, ''))
    return added, dropped, restated, biggest
TOL = 0.02


def num(v):
    return float(v) if (v or '').strip() else 0.0


def main():
    for p in (READ, TOTALS):
        if not os.path.exists(p):
            sys.exit(f'{os.path.relpath(p, ROOT)} is missing')
    rows = list(csv.DictReader(open(READ, newline='', encoding='utf-8')))
    printed = {r['edition']: r for r in
               csv.DictReader(open(TOTALS, newline='', encoding='utf-8'))}

    editions = sorted({r['edition'] for r in rows})
    fails = 0
    for ed in editions:
        mine = [r for r in rows if r['edition'] == ed]
        print(f'\n{ed} — {len(mine)} funds, pages '
              f'{"-".join(sorted({r["page"] for r in mine}, key=int)[::len(set(r["page"] for r in mine))-1 or 1])}')

        # 1. every row satisfies the identity the table states
        bad = [r for r in mine
               if abs(num(r['forward']) + num(r['receipts'])
                      - num(r['disbursements']) - num(r['carried'])) > 0.005]
        if bad:
            fails += 1
            print(f'  FAIL  {len(bad)} row(s) do not balance:')
            for r in bad[:8]:
                d = (num(r['forward']) + num(r['receipts'])
                     - num(r['disbursements']) - num(r['carried']))
                print(f'          {r["fund"][:46]:48} {d:+,.2f}')
        else:
            print(f'  ok    all {len(mine)} rows: forward + receipts '
                  f'- disbursements = carried')

        # 2. every column ties to the total the REPORT prints
        p = printed.get(ed)
        if not p:
            fails += 1
            print(f'  FAIL  no printed GRAND TOTAL recorded for {ed}')
            continue
        for c in COLS:
            got = sum(num(r[c]) for r in mine)
            want = num(p[c])
            d = got - want
            ok = abs(d) <= TOL
            fails += 0 if ok else 1
            print(f'  {"ok  " if ok else "FAIL"}  {c:14} {got:>15,.2f}  '
                  f'printed {want:>15,.2f}  {d:+,.2f}')

    # 3. THE YEAR CHAIN. Free, and independent of both checks above: what a year carries
    # forward must be what the next year brings forward. It catches a whole page missed at
    # the end of a year, which the other two checks cannot -- a missing page would make the
    # column totals disagree with the printed grand total, yes, but only if the grand total
    # were on a page we still read. This is checked between CONSECUTIVE years only; a gap
    # in coverage is reported rather than chained across.
    print('\nThe year chain — one year\'s carried forward against the next year\'s brought forward')
    by_fy = {}
    for r in rows:
        by_fy.setdefault(int(r['fy']), []).append(r)
    years = sorted(by_fy)
    linked = 0
    for a, b in zip(years, years[1:]):
        if b != a + 1:
            print(f'  --    FY{a} to FY{b}: not consecutive, nothing to chain')
            continue
        carried = sum(num(r['carried']) for r in by_fy[a])
        forward = sum(num(r['forward']) for r in by_fy[b])
        d = carried - forward
        ok = abs(d) <= TOL
        # An examined break, matched on the exact amount.
        known = CHAIN_EXCEPTIONS.get((f'FY{a}', f'FY{b}'))
        if not ok and known and abs(d + known[0]) <= TOL:
            print(f'  note  FY{a} carried {carried:>15,.2f} -> FY{b} forward '
                  f'{forward:>15,.2f}  {d:+,.2f}')
            print(f'        EXAMINED — {known[1]}')
            added, dropped, restated, (big, bigname) = decompose(rows, a, b)
            print(f'        computed: +{added:,.2f} in funds FY{b} opens and FY{a} did '
                  f'not carry, -{dropped:,.2f} in funds FY{a} carried and FY{b} does '
                  f'not open,')
            print(f'                  {restated:+,.2f} restated across funds in both '
                  f'(largest: {bigname}, {big:+,.2f}).')
            print(f'                  residual {added - dropped + restated - known[0]:+,.2f}')
            linked += 1
            continue
        fails_here = 0 if ok else 1
        globals()['_chain_fails'] = globals().get('_chain_fails', 0) + fails_here
        linked += 1
        print(f'  {"ok  " if ok else "FAIL"}  FY{a} carried {carried:>15,.2f} '
              f'-> FY{b} forward {forward:>15,.2f}  {d:+,.2f}')
    if not linked:
        print('  --    only one year so far; the chain needs two consecutive ones')
    fails += globals().get('_chain_fails', 0)

    print(f'\n{len(editions)} edition(s) checked, {fails} failure(s)')
    if fails:
        sys.exit(1)
    n_ex = sum(1 for k in CHAIN_EXCEPTIONS)
    print('Every column ties to the total the report itself prints and every row satisfies')
    print('the identity the table states. Consecutive years chain, with %d examined'
          % n_ex if n_ex else 'the identity the table states, and consecutive years chain.')
    if n_ex:
        print('exception%s above — a break the town made, pinned to the penny, not one we'
              % ('' if n_ex == 1 else 's'))
        print('are ignoring.')


if __name__ == '__main__':
    main()
