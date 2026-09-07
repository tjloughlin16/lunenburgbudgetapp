#!/usr/bin/env python3
"""Append one transcribed year to the read-from-the-page dataset, if it ties.

    python3 scripts/append_special_revenue_year.py <year-module.py>

The module defines FY, EDITION, DOC, GRAND, GRAND_PAGE and R (page, group, fund,
forward, receipts, disbursements, carried).

**It refuses to write a year that does not reconcile.** That is the whole point: the
dataset's guarantee is that everything in it ties to the total its own report prints, so a
year is either correct or absent. A year that half-works would be worse than a missing one,
because nothing downstream would know which half.
"""
import argparse
import csv
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ = os.path.join(ROOT, 'sources', 'data', 'special-revenue-read.csv')
TOTALS = os.path.join(ROOT, 'sources', 'data', 'special-revenue-printed-totals.csv')
COLS = ('forward', 'receipts', 'disbursements', 'carried')


def load(path):
    spec = importlib.util.spec_from_file_location('year', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('module')
    a = ap.parse_args()
    Y = load(a.module)

    # Both checks, before anything is written.
    bad = [r for r in Y.R
           if abs((r[3] or 0) + (r[4] or 0) - (r[5] or 0) - (r[6] or 0)) > 0.005]
    if bad:
        print(f'{len(bad)} row(s) do not balance:')
        for r in bad[:10]:
            print(f'   {r[2][:46]:48} '
                  f'{(r[3] or 0)+(r[4] or 0)-(r[5] or 0)-(r[6] or 0):+,.2f}')
        sys.exit(1)
    for i, n in enumerate(COLS):
        got = sum(r[3 + i] or 0 for r in Y.R)
        if abs(got - Y.GRAND[i]) > 0.02:
            sys.exit(f'{n}: {got:,.2f} against printed {Y.GRAND[i]:,.2f} '
                     f'({got - Y.GRAND[i]:+,.2f}) — not written.')

    existing = []
    if os.path.exists(READ):
        existing = list(csv.DictReader(open(READ, newline='', encoding='utf-8')))
    if any(r['edition'] == Y.EDITION for r in existing):
        sys.exit(f'{Y.EDITION} is already in the dataset.')

    f = lambda v: '' if v is None else f'{v:.2f}'
    fields = ['fy', 'edition', 'page', 'group', 'fund', 'forward', 'receipts',
              'disbursements', 'carried', 'row_ties', 'document', 'read_by']
    with open(READ, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in existing:
            w.writerow(r)
        for page, group, fund, b, c, d, e in Y.R:
            w.writerow(dict(fy=Y.FY, edition=Y.EDITION, page=page, group=group, fund=fund,
                            forward=f(b), receipts=f(c), disbursements=f(d), carried=f(e),
                            row_ties='yes', document=Y.DOC, read_by='vision'))

    tot = list(csv.DictReader(open(TOTALS, newline='', encoding='utf-8')))
    tot.append(dict(fy=Y.FY, edition=Y.EDITION, page=Y.GRAND_PAGE,
                    forward=f(Y.GRAND[0]), receipts=f(Y.GRAND[1]),
                    disbursements=f(Y.GRAND[2]), carried=f(Y.GRAND[3]),
                    quote=f'GRAND TOTAL row, page {Y.GRAND_PAGE}'))
    tot.sort(key=lambda r: int(r['fy']))
    with open(TOTALS, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'edition', 'page', 'forward', 'receipts',
                                           'disbursements', 'carried', 'quote'])
        w.writeheader()
        w.writerows(tot)
    print(f'{Y.EDITION}: {len(Y.R)} funds appended — all four columns tie, '
          f'all rows balance.')


if __name__ == '__main__':
    main()
