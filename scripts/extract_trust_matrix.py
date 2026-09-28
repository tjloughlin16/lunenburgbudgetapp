"""The annual report's TRUST FUNDS matrix: every fund, every measure, one page.

    python3 scripts/extract_trust_matrix.py
    python3 scripts/extract_trust_matrix.py --check

Writes `sources/data/trust-fund-matrix.csv`.

WHAT THIS TABLE IS, AND WHY IT WAS NOT READ

FY2025 page 36 prints the whole trust fund accounting as a matrix: 29 funds and 4 group
subtotals and a grand total across the page, 14 measures down it -- beginning principal,
beginning earnings, net income, realized gain, transfers, ending cash, unrealized gain,
ending market. 462 figures on one page.

It went unread because the fund names are printed SIDEWAYS, one per column, and every
reader here looks for a label at the left of a row. There is no label at the left of a
row. The names are a header, turned ninety degrees.

They come out of the text layer perfectly -- `DORA HAVEN COWDRY SCHOLARSHIP`, `I. KIMBALL
CONSERVATION` -- because the publisher embedded them as text and only the RENDERING is
rotated. Recognising a picture of this page instead is what made it look hard.

WHAT PROVES IT

The page states five identities about itself, and all five close to the cent on all 33
columns before anything is written:

    each group SUBTOTAL          = the sum of the funds printed under it
    GRAND TOTALS                 = the sum of the four group subtotals
    net earnings                 = net income + realized gain/loss
    ending principal             = beginning principal + transfers of principal
    ending cash value            = ending principal + ending earnings
    ending market value          = ending cash value + unrealized gain/loss

That is 14 measures x 5 groups of column arithmetic plus 4 identities x 33 columns. A
column read off the wrong x, a row banded onto its neighbour or a misread digit cannot
survive it, which is why this extract writes nothing at all unless every one holds.

AND IT IS A SECOND PRINTING OF THE FUND LIST. `ending cash value` here equals the balance
`trust-fund-balances.csv` reads off the listing on pages 30-31, fund by fund -- two
different tables in one document, read by two different routes, agreeing. That check runs
here too.

THE LAYOUT IS WRITTEN DOWN, NOT INFERRED (rule 13b). The measure names arrive scrambled,
because rotated text stacks in reading order rather than in the order a person sees --
`MARKET BEGINNING FY 2025 VALUE` is how `BEGINNING MARKET VALUE FY 2025` comes out. Two
attempts to unscramble them automatically produced confident nonsense, so the fourteen
names are declared below against the token set each one must match, and a year whose page
does not match them is REFUSED rather than aligned.
"""
import argparse
import collections
import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'trust-fund-matrix.csv')
LISTING = os.path.join(ROOT, 'sources', 'data', 'trust-fund-balances.csv')

MONEY = re.compile(r'^\(?\$?-?[\d,]+\.\d\d\)?$')
FIELDS = ['fy', 'column', 'kind', 'group', 'measure', 'amount', 'proof', 'page', 'document']

# One edition, one page. The matrix arrives with the FY2024 change in how the Treasurer's
# section is laid out; earlier years print the `HELD BY OTHER BANKS` table instead, which
# `read_trust_table.py` handles and which is a different table with different columns.
EDITIONS = {
    2025: ('sources/town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf', 36),
}

# THE MEASURES, READ OFF THE PAGE AND WRITTEN DOWN. The key is the sorted set of words the
# rotated header yields for that row; the value is the name a person reads. Refusing on an
# unknown token set is the point -- a year that prints a fifteenth measure, or renames one,
# stops here instead of publishing a figure under somebody else's heading.
MEASURES = {
    frozenset('MARKET BEGINNING FY 2025 VALUE'.split()): 'beginning market value',
    frozenset('(Non-Expend) PRINCIPAL BEGINNING FY 2025'.split()): 'beginning principal (non-expendable)',
    frozenset('(Expendable) BEGINNING EARNINGS FY 2025'.split()): 'beginning earnings (expendable)',
    frozenset('NET FY INCOME 2025'.split()): 'net income',
    frozenset('GAIN/LOSS REALIZED FY 2025'.split()): 'realized gain/loss',
    frozenset('NET FY EARNINGS 2025'.split()): 'net earnings',
    frozenset('TRANSFERS (Non-Expend) PRINCIPAL FY 2025 OF'.split()): 'transfers of principal (non-expendable)',
    frozenset('TRANSFERS (Expendable) EARNINGS FY 2025 OF'.split()): 'transfers of earnings (expendable)',
    frozenset('(Non-Expend) PRINCIPAL FY ENDING 2025'.split()): 'ending principal (non-expendable)',
    frozenset('(Expendable) EARNINGS FY ENDING 2025'.split()): 'ending earnings (expendable)',
    frozenset('ENDING FY VALUE 2025 CASH'.split()): 'ending cash value',
    frozenset('UNREALIZED GAIN/LOSS CHANGE FY 2025 IN'.split()): 'change in unrealized gain/loss',
    frozenset('UNREALIZED GAIN/LOSS FY 2025'.split()): 'unrealized gain/loss',
    frozenset('ENDING FY VALUE 2025 MARKET'.split()): 'ending market value',
}

# The four groups, in the order they are printed. The page puts each group's NAME in its own
# narrow column to the RIGHT of its member funds and labels the totalling column `SUBTOTALS`,
# so the name cannot be read off the subtotal column itself.
GROUPS = ['miscellaneous funds', 'scholarship funds', 'conservation funds', 'cemetery funds']

# The identities the page states about itself. Each is (result, [parts]).
IDENTITIES = [
    ('net earnings', ['net income', 'realized gain/loss']),
    ('ending principal (non-expendable)',
     ['beginning principal (non-expendable)', 'transfers of principal (non-expendable)']),
    ('ending cash value',
     ['ending principal (non-expendable)', 'ending earnings (expendable)']),
    ('ending market value', ['ending cash value', 'unrealized gain/loss']),
]
TOL = 0.02


def num(t):
    t = t.replace('$', '').replace(',', '').strip()
    return -float(t[1:-1]) if t.startswith('(') else float(t)


def blocks_of(words):
    """The page's printed BLOCKS, banded on a vertical gap.

    A measure occupies several printed lines, because a long figure and a short one sit at
    different heights in a rotated layout, and the gap WITHIN a block (at most 7pt here) is
    comfortably smaller than the gap BETWEEN two (at least 18pt). Measured, not guessed.
    """
    ys = sorted(words, key=lambda w: w['top'])
    out = [[ys[0]]]
    for a, b in zip(ys, ys[1:]):
        if b['top'] - a['top'] > 12:
            out.append([])
        out[-1].append(b)
    return out


def read_matrix(pdf, page):
    import pdfplumber
    with pdfplumber.open(pdf) as doc:
        words = [w for w in doc.pages[page - 1].extract_words()
                 if 110 <= w['x0'] < 505]
    blocks = blocks_of(words)

    # THE HEADER IS THE BLOCK THAT CARRIES `SUBTOTALS`, not the first block on the page --
    # the first block is the page's title, and taking it as the header matched every figure
    # to the word `TRUST` and footed nothing.
    hi = next((i for i, b in enumerate(blocks)
               if any(w['text'] == 'SUBTOTALS' for w in b)), None)
    if hi is None:
        raise SystemExit('%s p%d: no SUBTOTALS row -- this is not the matrix'
                         % (os.path.basename(pdf), page))
    head = collections.defaultdict(list)
    for w in blocks[hi]:
        head[round(w['x0'])].append(w)
    names = {k: ' '.join(t['text'] for t in sorted(v, key=lambda t: t['top']))
             for k, v in head.items()}

    rows = []
    for bl in blocks[hi + 1:]:
        # PLACE EACH FIGURE IN THE NEAREST COLUMN, never in reading order (rule 13b). A
        # fund with nothing in a measure prints nothing, and taking the figures in order
        # puts every later one under the wrong fund from the first gap onward.
        cells = {}
        for w in bl:
            if MONEY.match(w['text']):
                cells[min(names, key=lambda k: abs(k - w['x0']))] = num(w['text'])
        if not cells:
            continue
        tokens = frozenset(t['text'] for t in bl if t['x0'] >= 470)
        if tokens not in MEASURES:
            raise SystemExit('%s p%d: unknown measure %s -- read the header and declare it'
                             % (os.path.basename(pdf), page, sorted(tokens)))
        rows.append((MEASURES[tokens], cells))
    return names, rows


def structure(names, rows):
    """The grand total column, and each group's subtotal column with its member funds."""
    xs = sorted({x for _, c in rows for x in c})
    subs = [x for x in xs if names[x] == 'SUBTOTALS']
    if len(subs) != len(GROUPS):
        raise SystemExit('%d subtotal columns, %d groups declared' % (len(subs), len(GROUPS)))
    groups = []
    for i, s in enumerate(subs):
        nxt = subs[i + 1] if i + 1 < len(subs) else 10 ** 9
        groups.append((GROUPS[i], s, [x for x in xs if s < x < nxt]))
    return xs[0], groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    body, notes = [], []
    for fy, (rel, page) in sorted(EDITIONS.items()):
        pdf = os.path.join(ROOT, rel)
        names, rows = read_matrix(pdf, page)
        if len(rows) != len(MEASURES):
            raise SystemExit('FY%d p%d: %d measures, %d declared'
                             % (fy, page, len(rows), len(MEASURES)))
        grand, groups = structure(names, rows)
        by = {m: c for m, c in rows}

        # NOTHING IS WRITTEN UNLESS THE PAGE'S OWN ARITHMETIC CLOSES.
        bad = []
        for m, cells in rows:
            for g, s, mem in groups:
                got = sum(cells.get(x, 0.0) for x in mem)
                if abs(got - cells.get(s, 0.0)) > TOL:
                    bad.append('%s: %s subtotal %.2f, its funds sum to %.2f'
                               % (m, g, cells.get(s, 0.0), got))
            got = sum(cells.get(s, 0.0) for _, s, _ in groups)
            if abs(got - cells.get(grand, 0.0)) > TOL:
                bad.append('%s: grand total %.2f, its subtotals sum to %.2f'
                           % (m, cells.get(grand, 0.0), got))
        for res, parts in IDENTITIES:
            for x in sorted({x for _, c in rows for x in c}):
                got = sum(by[p].get(x, 0.0) for p in parts)
                if abs(got - by[res].get(x, 0.0)) > TOL:
                    bad.append('%s: %s is %.2f, %s sum to %.2f'
                               % (names[x], res, by[res].get(x, 0.0), ' + '.join(parts), got))
        if bad:
            print('FY%d p%d does not close, nothing written:\n  %s'
                  % (fy, page, '\n  '.join(bad[:12])), file=sys.stderr)
            return 1

        members = {x for _, _, mem in groups for x in mem}
        for m, cells in rows:
            for x in sorted(cells):
                kind = ('grand total' if x == grand else
                        'group subtotal' if names[x] == 'SUBTOTALS' else 'fund')
                g = next((gn for gn, s, mem in groups if x == s or x in mem), '')
                body.append(dict(
                    fy=fy, column=names[x], kind=kind, group=g, measure=m,
                    amount=round(cells[x], 2),
                    proof='every identity the page states about itself closes',
                    page=page, document=os.path.relpath(pdf, ROOT)))

        # THE SECOND PRINTING: `ending cash value` here against the pages 30-31 listing.
        if os.path.exists(LISTING):
            seen = {}
            for r in csv.DictReader(open(LISTING, encoding='utf-8')):
                if int(r['fy']) == fy:
                    seen[round(float(r['balance']), 2)] = r['name']
            ends = by['ending cash value']
            hit = sum(1 for x in members if round(ends.get(x, 0.0), 2) in seen)
            notes.append('  FY%d  %d of %d funds also appear in the pages 30-31 listing '
                         'at the same ending cash value' % (fy, hit, len(members)))

    body.sort(key=lambda r: (r['fy'], r['measure'], r['column']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(body)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/extract_trust_matrix.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d figures, every identity closes' % len(body))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote %s -- %d figures' % (os.path.relpath(OUT, ROOT), len(body)))
    print('\n'.join(notes))
    return 0


if __name__ == '__main__':
    sys.exit(main())
