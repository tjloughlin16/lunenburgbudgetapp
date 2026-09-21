"""Which page of which annual report carries the stabilization funds — every one of them.

    python3 scripts/map_stabilization_pages.py
    python3 scripts/map_stabilization_pages.py --check

Writes `sources/data/stabilization-pages.csv`, newest report first.

WHY THIS EXISTS, IN TJ'S WORDS.

*"i dont know how to make this process systematic. I thought we already did that but i
guess not. I want to 1) Make sure we know which pages on the annual reports these stabil
funds land 2) Process the data 3) Work backwards from newest to oldest."*

He is right that it was not systematic. Pages were found one at a time, by hand, by
searching a PDF — and each time one turned up, the reader was adjusted until that page
worked. Nothing recorded WHICH pages exist, so nothing could say what had been looked at
and what had not, and the same page could be rediscovered twice a week apart.

This is step 1, on its own, as a file. It does not read a table or prove a figure: it says
where the tables ARE, what KIND each one is, and what state it is in. Step 2 reads them,
and it can only be planned once this exists.

FOUR DIFFERENT TABLES CARRY THESE FUNDS, and conflating them is how figures go wrong.

  other-banks      `TRUST AND STABILIZATION FUNDS HELD BY OTHER BANKS`. Wide, skewed,
                   beginning/activity/ending columns that foot. Holds the funds at TD
                   Banknorth, Unibank and MMDT -- and NOT the general Stabilization Fund,
                   which is why the charts stopped at FY2021 for the fund everybody means.
  book-value       The investment manager's statement (`BARTHOLOMEW`, `ACCOUNTING METHOD:
                   BOOK VALUE`). Holds the general Stabilization Fund and the OPEB trust.
  balance-listing  `Trust Fund Balance Detail`: one line per account number with its
                   balance. The COMPLETE list, and the easiest to read. FY2024 onward.
  treasurers-cash  `Treasurer's Cash as of ...`: cash by bank, naming funds but not
                   itemising them by account.

A page that merely mentions a fund in a Town Meeting article is `article`, not a table,
and is excluded from the work queue -- those are already read by the votes extractor.

THE COLUMN THAT MATTERS IS `state`.

  read             a row from this page is published in stabilization-balances.csv
  reversed         the OCR of this page is upside down; its text is mirrored and no
                   extractor can see a figure on it. Re-OCR before anything else.
  unread           a table we can see and have not yet taken figures from

`unread` is the work queue, and sorting the file newest-first is step 3.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'stabilization-pages.csv')
PROVEN = os.path.join(ROOT, 'sources', 'data', 'stabilization-balances.csv')
LISTING = os.path.join(ROOT, 'sources', 'data', 'trust-fund-balances.csv')

MONEY = re.compile(r'^\(?-?[$S]?-?[\d,]{1,15}[.,]\d{2}\)?$')
FUND = re.compile(r'stabiliz|trust fund|opeb|conservation trust|playground|perpetual care',
                  re.I)
CODE = re.compile(r'^(8[01]\d\d|9\d{3})\b')

KINDS = [
    ('balance-listing', re.compile(r'trust\s+fund\s+balance', re.I)),
    ('other-banks', re.compile(r'held\s+by\s+other\s+banks', re.I)),
    ('book-value', re.compile(r'bartholomew|accounting\s+method', re.I)),
    ('treasurers-cash', re.compile(r'treasurer.{0,3}s\s+cash', re.I)),
]

FIELDS = ['fy', 'page', 'kind', 'state', 'funds_named', 'accounts', 'figures',
          'figures_reversed', 'rows_published', 'document']


def unreversed(t):
    r = t[::-1]
    for a, b in (('S', '$'), ('E', '3'), ('Z', '2'), ('B', '8'), ("'", ',')):
        r = r.replace(a, b)
    return r


def published():
    """{(fy, page): rows} already in a published extract, from either reader."""
    out = collections.Counter()
    for path, pagekey in ((PROVEN, 'page'), (LISTING, 'page')):
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding='utf-8')):
            try:
                out[(int(r['fy']), int(r[pagekey]))] += 1
            except (TypeError, ValueError, KeyError):
                continue
    return out


def scan(path):
    """Per page: what it names, how many figures, and which way up they are."""
    pages = collections.defaultdict(lambda: dict(
        funds=0, accounts=0, figs=0, rev=0, text=[]))
    with open(path, encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            t = (r['text'] or '').strip()
            if not t:
                continue
            p = pages[int(r['page'])]
            if MONEY.match(t):
                p['figs'] += 1
            elif MONEY.match(unreversed(t)):
                p['rev'] += 1
            if FUND.search(t) or FUND.search(unreversed(t)):
                p['funds'] += 1
            if CODE.match(t):
                p['accounts'] += 1
            if len(t) > 8:
                p['text'].append(t)
    return pages


def classify(p):
    """The kind of table, from the page's own headings; None if it is not one."""
    joined = ' | '.join(p['text'][:60])
    for kind, pat in KINDS:
        if pat.search(joined) or pat.search(unreversed(joined)):
            return kind
    # A REVERSED PAGE HAS NO READABLE NAMES EITHER, which is why the first version of
    # this map showed zero of them while the orientation checker was reporting 31. On an
    # upside-down page `STABILIZATION` is as mangled as `$0.00`, so a test that needs a
    # fund name to call something a table cannot see the very pages most in need of
    # listing. A wall of backwards figures is enough on its own.
    if p['rev'] >= 8 and p['rev'] > p['figs']:
        return 'table'
    # No heading survived the scan. A page with fund names AND a wall of figures is still
    # a table -- most of the early reports land here, because their headings are the part
    # the scanner lost.
    if p['funds'] >= 3 and (p['figs'] + p['rev']) >= 15:
        return 'table'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    done = published()
    rows = []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        fy = int(m.group(1))
        doc = os.path.relpath(f, ROOT)
        for page, p in sorted(scan(f).items()):
            kind = classify(p)
            if not kind:
                continue
            # A CONTENTS LINE IS NOT A TABLE. `Trust Fund Balance ....... 27` matches the
            # heading test and carries no figures at all; listing it puts four index
            # entries at the top of a work queue sorted newest-first, which is exactly
            # where they do the most damage.
            if p['figs'] + p['rev'] < 10:
                continue
            n = done.get((fy, page), 0)
            if n:
                state = 'read'
            elif p['rev'] > p['figs']:
                state = 'reversed'
            else:
                state = 'unread'
            rows.append(dict(
                fy=fy, page=page, kind=kind, state=state, funds_named=p['funds'],
                accounts=p['accounts'], figures=p['figs'], figures_reversed=p['rev'],
                rows_published=n, document=doc))

    # NEWEST FIRST, because that is the order the work is to be done in and a file that
    # sorts the other way invites starting at the wrong end.
    rows.sort(key=lambda r: (-r['fy'], r['page']))

    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(rows)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/map_stabilization_pages.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d table pages mapped across %d reports'
              % (len(rows), len({r['fy'] for r in rows})))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote %s -- %d table pages across %d reports'
          % (os.path.relpath(OUT, ROOT), len(rows), len({r['fy'] for r in rows})))
    by_state = collections.Counter(r['state'] for r in rows)
    for s in ('read', 'unread', 'reversed'):
        print('  %-9s %3d' % (s, by_state.get(s, 0)))
    print()
    print('  the queue, newest first:')
    for r in rows:
        if r['state'] != 'read':
            print('    FY%d p%-4d %-16s %-8s %2d funds, %3d figures%s'
                  % (r['fy'], r['page'], r['kind'], r['state'], r['funds_named'],
                     r['figures'],
                     ' (%d reversed)' % r['figures_reversed'] if r['figures_reversed'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
