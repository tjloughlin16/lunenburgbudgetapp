"""Does every stabilization fund have a balance for every year it existed?

    python3 scripts/check_stabilization_coverage.py
    python3 scripts/check_stabilization_coverage.py --check   # non-zero if any gap

TJ set the target: *"I want the line charts to have 0 dotted lines because we have all
the data. I am 100% confident we have all the data."* He was right, and getting there
took eight separate defects in how this project READ the documents rather than anything
missing from them. This is the check that says whether it is still true.

TWO THINGS IT GETS RIGHT THAT A NAIVE COUNT DOES NOT, and both were learned the hard way.

**A fund's life starts at its first BALANCE, not at its creating vote.** Money voted at a
spring Town Meeting moves in the following fiscal year. Vehicle/Equipment is the worked
example: created FY2017 by article 10 with $200,000 authorised, opening balance $0.00,
and $235,000 arriving in FY2018. Counting the creation year as a missing balance invents
a gap that is really a zero -- and it did, for four funds at once.

**And one fund is several funds unless the names are resolved first.** The town writes
`Sewer Reserve Capacity` and `Sewer Capacity Reserve` for one account, the scanner turns
`I/I` into `I/1`, and FY2023's page gives `Bartholomew - ОРЕВ` in Cyrillic characters
that render identically to OPEB. scripts/fund_names.py does that resolution; without it
this check reported gaps that were spellings.
"""
import argparse
import collections
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from fund_names import canonical  # noqa: E402

LATEST = 2025

# The first fiscal year each fund can have a BALANCE. For funds created inside the
# archive's reach this is the year after the creating vote, and that is not a guess: each
# is confirmed by the following year's table printing a beginning balance of $0.00.
FIRST_BALANCE = {
    # FY2011 IS REAL AND I SAID IT WAS NOT. The Treasurer's Cash pages for FY2011-FY2013
    # do not itemise this fund -- it sits inside `Bartholomew Trust Funds` there -- and I
    # reported the years missing on that basis. The TRUST TABLE prints all three, and had
    # done since the rotated-page fix an hour earlier; I had not re-run the reader over
    # the re-OCR'd files before answering. TJ pointed at FY2011 PDF page 74 and they were
    # on it: $1,186,776.91, both identities holding.
    #
    # Rule 13c again, and this time against my own pipeline: a dataset with no rows for a
    # year is a thing we built, not a fact about the town, and it is stale the moment its
    # input changes.
    'Stabilization (general)': 2011,
    'Zoning Incentive': 2011,       # listed as `TD BankNorth Stabilization` until FY2014
    'Sewer Reserve Capacity': 2016,      # created FY2015; FY2015 ends at $0.00
    'Sewer Inflow/Infiltration': 2017,
    'Sewer Capital Reserve': 2018,       # created FY2017; FY2017 ends at $0.00
    'OPEB': 2018,
    'Vehicle/Equipment': 2018,           # created FY2017 art 10; FY2017 ends at $0.00
    'Health Insurance': 2022,            # created FY2021
    'Opioid Settlement': 2024,           # created FY2023
}

SOURCES = [
    ('treasurers-cash.csv', 'held_as', None),
    ('stabilization-balances.csv', 'name', 'code'),
    ('trust-fund-balances.csv', 'name', 'account'),
    ('stabilization-unfooted.csv', 'fund', 'account'),
]


def coverage():
    got = collections.defaultdict(set)
    for name, field, code in SOURCES:
        p = os.path.join(ROOT, 'sources', 'data', name)
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p, encoding='utf-8')):
            k = canonical(r.get(field), r.get(code) if code else None)
            if k:
                try:
                    got[k].add(int(r['fy']))
                except (KeyError, TypeError, ValueError):
                    continue
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    got = coverage()
    gaps, done = [], 0
    print('%-28s %-16s %s' % ('fund', 'life', 'missing'))
    for fund in sorted(FIRST_BALANCE, key=lambda f: FIRST_BALANCE[f]):
        first = FIRST_BALANCE[fund]
        missing = sorted(set(range(first, LATEST + 1)) - got.get(fund, set()))
        if missing:
            gaps.append((fund, missing))
        else:
            done += 1
        print('%-28s FY%d-FY%d    %s'
              % (fund, first, LATEST,
                 ', '.join('FY%d' % y for y in missing) if missing else 'COMPLETE'))
    print()
    print('%d of %d funds have a balance for every year they existed'
          % (done, len(FIRST_BALANCE)))
    if a.check and gaps:
        print('\nGAPS REMAIN', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
