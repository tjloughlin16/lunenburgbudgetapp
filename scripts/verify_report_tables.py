#!/usr/bin/env python3
"""Recompute every reconciliation the annual-report extracts state about themselves.

Rule 9: every figure in a finished document gets re-checked against the data by script —
not re-read, recomputed. These CSVs carry their own verdict in two columns, `status` and
`reconciliation`, and those are prose written by the extractor at the moment it ran. They
are exactly the thing rule 2 warns about: a sentence that goes on rendering confidently
after the model beneath it has moved.

So this reads only the CSVs, recomputes what they claim, and fails when the claim and the
rows disagree. It does NOT go back to the PDF — `scripts/verify_against_page.py` does that,
one page at a time, and a person has to look.

Four things are checked.

**1. The stated reconciliation is arithmetic that holds.** Every `check failed` string names
a column, a sum and a printed total. The sum is recomputed from the rows in that run and
must match to the cent.

**2. A column is named or the string says it is not.** `v1` is an ordinal — the first column
of a page that held figures — and it is not the same printed column on two pages of the
same run. A reconciliation that quotes `v1` must carry the words saying so.

**3. No detail row exceeds its own table's printed total.** A single line cannot be larger
than the budget it sits in. FY2021's omnibus read `Reserve Fund 75000000` off a page whose
whole budget is $39.8M.

**4. `status` is one of the three words.** `checked`, `check failed`, `no check` — a table
that prints no total is not doubtful, it is unverifiable by arithmetic, and `partial` used
to say the first while meaning the second.

    python3 scripts/verify_report_tables.py [--quiet]
"""

import argparse
import collections
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')

STATUSES = {'checked', 'check failed', 'no check'}
# `name: got vs printed` or `v1: got vs printed`, the two forms the extractor writes.
CLAIM = re.compile(r'^([a-z_0-9]+): ([\d,.-]+) vs ([\d,.-]+)')


def num(s):
    try:
        return float(str(s).replace(',', ''))
    except (TypeError, ValueError):
        return None


def column_of(row, name):
    """The value of the column CALLED `name` on this row's page, or None."""
    meaning = row.get('column_meaning') or ''
    m = re.search(rf'v(\d)={re.escape(name)}\b', meaning)
    if not m:
        return None
    return num(row.get(f'v{m.group(1)}'))


def runs(rows):
    """A run is what the extractor stamped one verdict on: an edition and a reconciliation.

    The CSV does not carry a run id. It does not need one -- every row of a run carries the
    same `reconciliation` string, because that is what the string is about.
    """
    out = collections.OrderedDict()
    for r in rows:
        out.setdefault((r['edition'], r['status'], r['reconciliation']), []).append(r)
    return out


def check_file(path, problems, notes):
    name = os.path.basename(path)
    rows = list(csv.DictReader(open(path)))
    if not rows:
        problems.append(f'{name}: no rows')
        return 0
    checked = 0
    for (edition, status, recon), in_run in runs(rows).items():
        if status not in STATUSES:
            problems.append(f'{name} {edition}: status {status!r} is not one of {STATUSES}')
        detail = [r for r in in_run if r['kind'] == 'row']
        grand = next((r for r in in_run if r['kind'] == 'grand_total'), None)

        for part in recon.split(' ; '):
            m = CLAIM.match(part.strip())
            if not m:
                continue
            col, said_got, said_printed = m.group(1), num(m.group(2)), num(m.group(3))
            checked += 1

            # (2) an ordinal must say it is one
            if col.startswith('v') and col[1:].isdigit():
                if 'ORDINAL' not in part:
                    problems.append(
                        f'{name} {edition}: reconciles on {col}, which is an ordinal, '
                        f'and does not say so')
                got = round(sum(num(r.get(col)) or 0.0 for r in detail), 2)
                printed = num(grand.get(col)) if grand else None
            else:
                got = round(sum(column_of(r, col) or 0.0 for r in detail), 2)
                printed = column_of(grand, col) if grand else None

            # (1) the arithmetic the string states
            if abs(got - said_got) > 0.02:
                problems.append(
                    f'{name} {edition}: states {col} sums to {said_got:,.2f}; '
                    f'the rows sum to {got:,.2f}')
            if printed is None:
                problems.append(
                    f'{name} {edition}: states a printed total of {said_printed:,.2f} '
                    f'for {col}, and no grand total row carries that column')
            elif abs(printed - said_printed) > 0.02:
                problems.append(
                    f'{name} {edition}: states the report prints {said_printed:,.2f} '
                    f'for {col}; the grand total row holds {printed:,.2f}')

            # (3) no line larger than the table it is in -- unless the TOTAL is the
            # thing that is wrong.
            #
            # `report-trust-funds` FY2020 read its own grand total as $7.00 against detail
            # of $92,625.78, and every one of forty rows then exceeded it. Reporting forty
            # suspect rows there says the wrong thing: what is not credible is our reading
            # of the total, and the rows are the evidence for that.
            if printed and abs(got) > 100 * abs(printed):
                notes.append(
                    f'{name} {edition}: the grand total row holds {printed:,.2f} for '
                    f'{col} while the rows sum to {got:,.2f}. Our reading of the '
                    f'TOTAL is what is not credible here, not the rows.')
            elif printed:
                over = []
                for r in detail:
                    v = (num(r.get(col)) if col.startswith('v')
                         else column_of(r, col))
                    if v is not None and abs(v) > abs(printed):
                        over.append((abs(v), r, v))
                for _, r, v in sorted(over, reverse=True)[:3]:
                    notes.append(
                        f'{name} {edition} p{r["page"]}: {r["label"][:34]!r} holds '
                        f'{v:,.2f} in {col}, larger than the {printed:,.2f} the table '
                        f'prints as its own total')
                if len(over) > 3:
                    notes.append(f'{name} {edition}: and {len(over) - 3} more row(s) '
                                 f'larger than the printed {col} total')
    return checked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    problems, notes = [], []
    total = 0
    files = sorted(glob.glob(os.path.join(DATA, 'report-*.csv')))
    files = [f for f in files if 'anomalies' not in f]
    for f in files:
        total += check_file(f, problems, notes)

    if not args.quiet:
        print(f'{len(files)} datasets, {total} stated reconciliations recomputed')
        for n in notes:
            print(f'  NOTE  {n}')
    for p in problems:
        print(f'  FAIL  {p}')
    if problems:
        print(f'\n{len(problems)} stated reconciliation(s) do not match the rows.')
        sys.exit(1)
    print(f'every stated reconciliation matches the rows'
          + (f'; {len(notes)} row(s) exceed their own table total' if notes else ''))


if __name__ == '__main__':
    main()
