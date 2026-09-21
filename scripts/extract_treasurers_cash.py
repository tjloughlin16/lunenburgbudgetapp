"""Treasurer's Cash: what the town held, by bank and by fund, every year.

    python3 scripts/extract_treasurers_cash.py
    python3 scripts/extract_treasurers_cash.py --check

Writes `sources/data/treasurers-cash.csv`.

THE PAGE THAT WAS IN EVERY REPORT ALL ALONG.

The stabilization work went at the hardest table in the annual report -- `TRUST AND
STABILIZATION FUNDS HELD BY OTHER BANKS`, wide, skewed, multi-column, proved against its
own arithmetic -- and got fifteen rows out of fifteen reports. Meanwhile every single
report prints `Treasurer's Cash as of 6/30/<year>`: a two-column list of what the town
holds, by where it is held, with the funds named.

`Bartholomew Stabilization Fund` is on it. That is the GENERAL Stabilization Fund, the one
everybody at Town Meeting means, and the one the other-banks table does not carry at all --
which is the real reason a chart of it stopped four years before the figure printed above
it on the same page.

TWO YEARS PER PAGE. The table sets this year beside last year, so each report yields the
fiscal year it covers AND the one before it. Fifteen reports therefore reach back sixteen
years, and every interior year is read twice, from two different documents, which is a
free check nobody had to build.

WHAT PROVES IT. The page foots itself: `Total Cash per Treasurer` closes both columns, and
this refuses to write a year whose rows do not sum to it. That is rule 13's "when an
extract has a total the source itself prints, reconcile to it" -- and it is what separates
this from reading numbers off a picture and hoping.

WHAT IT IS NOT. Cash held, by custodian. It is not a fund balance: the Opioid Settlement
fund shows $233,317.54 of cash at Bartholomew where the ledger puts the FUND at
$241,421.18, because a fund's balance and the cash sitting in one bank for it are
different quantities. Where this file and `trust-agency-balances.csv` disagree, the ledger
is the fund and this is the cash. The stabilization funds happen to agree for most years
because they are held whole in one place, and that is a fact about them rather than a rule.
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
OUT = os.path.join(ROOT, 'sources', 'data', 'treasurers-cash.csv')

HEADING = re.compile(r"treasurer.{0,3}s\s+cash\s+as\s+of", re.I)
# The town writes this line at least three ways across the run -- `Total Cash per
# Treasurer 6/30/14`, `Total Treasurer Cash as of 06/30/2020` -- so the test is the two
# words in either order rather than one phrasing, which matched two reports out of fifteen.
TOTAL = re.compile(r"total.{0,20}treasurer|treasurer.{0,20}total", re.I)
MONEY = re.compile(r'^\$?\s*-?\(?[\d,]{1,15}\.\d{2}\)?$')
# The heading carries the date the column is measured to.
ASOF = re.compile(r'(\d{1,2})/(\d{1,2})/(\d{2,4})')

FIELDS = ['fy', 'held_as', 'amount', 'column', 'page', 'document']
TOL = 1.0


def money(t):
    t = t.replace('$', '').replace(',', '').strip()
    neg = t.startswith('(') and t.endswith(')')
    t = t.strip('()')
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def read_boxes(path):
    """Pages of boxes, via the SHARED reader.

    NOT `csv.DictReader`. These TSVs are unquoted and OCR text routinely contains a double
    quote, which the csv module treats as opening a quoted field -- it then swallows every
    following line until it finds a closing one, and raises `field larger than field
    limit` when it does not. `pdf_tables.read_boxes` splits on tabs, line by line, and is
    the reason nothing downstream of it ever lost a row.

    This function used the csv module until it met an OCR run containing a stray quote,
    which is the same mistake that made a measurement script report 5,215 rows missing
    from files that were complete.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pdf_tables as T
    by_page = collections.defaultdict(list)
    for b in T.read_boxes(path):
        by_page[b['page']].append(dict(x=b['x'], y=b['y'], w=b['w'], text=b['text']))
    return by_page


def columns(boxes):
    """The x-range of each amount column, left to right.

    Amounts are right-aligned, so their right edges cluster. The page sets this year and
    last year side by side; a year that prints only one column is handled by taking
    however many clusters there are rather than assuming two.
    """
    rights = sorted(b['x'] + b['w'] for b in boxes if MONEY.match(b['text'].strip()))
    if not rights:
        return []
    groups, cur = [], [rights[0]]
    for lo, hi in zip(rights, rights[1:]):
        if hi - lo > 0.04:
            groups.append(cur); cur = [hi]
        else:
            cur.append(hi)
    groups.append(cur)
    return [(min(g) - 0.03, max(g) + 0.03) for g in groups if len(g) >= 4]


def read_page(fy, page, boxes, doc):
    cols = columns(boxes)
    if not cols:
        return [], []
    labels = [b for b in boxes
              if not MONEY.match(b['text'].strip())
              and len(b['text'].strip()) > 5
              and b['x'] < min(c[0] for c in cols)]
    rows, totals = [], [None] * len(cols)
    for lab in labels:
        name = ' '.join(lab['text'].split())
        near = [b for b in boxes if abs(b['y'] - lab['y']) < 0.006
                and MONEY.match(b['text'].strip())]
        vals = []
        for lo, hi in cols:
            hit = [b for b in near if lo <= b['x'] + b['w'] <= hi]
            vals.append(money(hit[0]['text'].strip()) if hit else None)
        if TOTAL.search(name):
            # THE TOTAL ROW IS NOT SET IN THE COLUMNS. It is bolder and wider and sits
            # left of them -- FY2020's $19,768,992.71 lands at x=0.60 where the column it
            # closes runs 0.70 to 0.76 -- so matching it by position finds nothing and
            # every page reports "the page says nothing" while printing its total in
            # plain sight. Its values are taken in order instead: the order of a row is
            # not in doubt even when its alignment is.
            got = sorted([b for b in near], key=lambda b: b['x'])
            vals = [money(b['text'].strip()) for b in got]
            totals = [v if v is not None else t
                      for v, t in zip(vals + [None] * len(totals), totals)]
            continue
        if all(v is None for v in vals):
            continue
        rows.append((name, vals))
    return rows, totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    body, report = [], []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv')), reverse=True):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        fy = int(m.group(1))
        doc = os.path.relpath(f, ROOT)
        for page, boxes in sorted(read_boxes(f).items()):
            if not any(HEADING.search(b['text']) for b in boxes):
                continue
            rows, totals = read_page(fy, page, boxes, doc)
            if not rows:
                continue
            # RECONCILE EACH COLUMN TO THE TOTAL THE PAGE PRINTS, or take nothing from it.
            kept = []
            for i, total in enumerate(totals):
                got = sum(v[i] for _, v in rows if v[i] is not None)
                if total is None or abs(got - total) > TOL:
                    report.append('FY%d p%d col%d: rows sum to %.2f, page says %s'
                                  % (fy, page, i, got,
                                     '%.2f' % total if total is not None else 'nothing'))
                    continue
                # Column 0 is the year the page is headed with; each column right of it is
                # one year older.
                kept.append((i, fy - i))
            for i, year in kept:
                for name, vals in rows:
                    if vals[i] is None:
                        continue
                    body.append(dict(fy=year, held_as=name, amount=round(vals[i], 2),
                                     column='as printed' if i == 0 else 'prior year',
                                     page=page, document=doc))
    if not body:
        print('no Treasurer\'s Cash page reconciled', file=sys.stderr)
        for r in report:
            print('  ' + r, file=sys.stderr)
        return 1

    body.sort(key=lambda r: (-r['fy'], r['held_as']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(body)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/extract_treasurers_cash.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d rows across %d years, every column footed to its own total'
              % (len(body), len({r['fy'] for r in body})))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    years = sorted({r['fy'] for r in body})
    print('wrote %s -- %d rows, FY%d to FY%d'
          % (os.path.relpath(OUT, ROOT), len(body), years[0], years[-1]))
    stab = [r for r in body if re.search(r'stabiliz', r['held_as'], re.I)]
    print('  %d of them name a stabilization fund' % len(stab))
    # A REFUSAL IS A FINDING AND IT HAS TO OUTLIVE THE RUN. These lines were printed to
    # stdout and nothing kept them, so five years were being read and dropped on every
    # run, invisibly -- and when asked which years we had, the honest answer "read but
    # not proven" was not available anywhere. Now it is written down beside the data, and
    # build_pipeline_state.py reads it into the `blocked` column.
    #
    # The distinction it preserves is the one that decides the work: a year nobody has
    # written an extractor for needs an extractor, and a year whose column missed its own
    # printed total by a stated amount needs that amount chased. They look identical in
    # any count of rows.
    blockers = os.path.join(ROOT, 'sources', 'data', 'extraction-blocked.csv')
    keep = [r for r in _blockers(blockers) if r['extractor'] != 'treasurers-cash']
    for r in report:
        m = re.match(r'FY(\d{4}) p(\d+) (\S+): rows sum to ([\d.]+), page says (.+)', r)
        if not m:
            continue
        fy, page, col, ours, theirs = m.groups()
        try:
            diff = '%.2f' % (float(ours) - float(theirs))
        except ValueError:
            diff = ''
        keep.append(dict(
            extractor='treasurers-cash', fy=fy, page=page, what=col,
            reason='column does not foot to the page\u2019s own printed total',
            ours=ours, theirs=theirs, difference=diff))
    _write_blockers(blockers, keep)
    if report:
        print('  columns that did NOT foot, and were dropped '
              '(recorded in sources/data/extraction-blocked.csv):')
        for r in report:
            print('    ' + r)
    return 0


BLOCK_FIELDS = ['extractor', 'fy', 'page', 'what', 'reason', 'ours', 'theirs',
                'difference']


def _blockers(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path, encoding='utf-8')))


def _write_blockers(path, rows):
    rows.sort(key=lambda r: (r['extractor'], str(r['fy']), str(r['page']), r['what']))
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=BLOCK_FIELDS, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in BLOCK_FIELDS})


if __name__ == '__main__':
    sys.exit(main())
