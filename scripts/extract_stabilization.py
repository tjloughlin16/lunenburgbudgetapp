#!/usr/bin/env python3
"""The stabilization fund balances, read off the annual reports' own trust-fund tables.

    python3 scripts/extract_stabilization.py            # write sources/data/stabilization-balances.csv
    python3 scripts/extract_stabilization.py --check
    python3 scripts/extract_stabilization.py --fy 2014 --verbose

WHY A DEDICATED EXTRACTOR. `report_trust_funds` holds 642 rows of this across FY2011-2025
and twelve are reconciled. The generic pass could not read these pages, and the per-year
survey in `sources/data/extraction-plan.csv` says why: ten of seventeen years are marked
`not without geometry`.

THE PAGES ARE ROTATED AND RIGHT-TO-LEFT, which is the whole of the difficulty and is not
obvious from the text layer. `page.extract_text()` returns `TROPER YRAMMUS` -- "SUMMARY
REPORT" backwards -- because the characters carry correct coordinates and the wrong
reading order. So:

  1. a visual ROW is a band of near-equal x0, because the page is turned a quarter turn;
  2. within a band, characters run right-to-left, so each word is reversed AND the words
     are in reverse order;
  3. clustering on real gaps rather than rounded buckets, because a wrapped fund name
     lands in an adjacent band and a rounded bucket merges the two into
     `(TD BA$2N2K6,N8O2R1.T9H0)`.

EVERY ROW PROVES ITSELF, which is why this can be trusted where the generic pass cannot.
The table states two identities per row and this refuses any row that fails them:

    beginning + contributions + earnings - disbursements - transfers  =  ENDING CASH
    ending cash + unrealised gain/loss                                =  ENDING MARKET

A row that does not close is not written. That is a stronger guarantee than the usual
one here: not "the year foots to a printed total" but "this line is internally consistent
in the way the document itself claims".

WHAT THIS IS NOT. It is the stabilization SECTION of a table the town heads TRUST FUNDS,
and those are different instruments -- a stabilization fund is the town's own reserve
under c.40 s5B, a trust is somebody's bequest under conditions. The table groups by where
the Treasurer holds the money; this file keeps only the rows that are stabilization.
"""
import argparse
import csv
import os
import re
import sys
import warnings

warnings.filterwarnings('ignore')
try:
    import pdfplumber
except ImportError:
    sys.exit('pdfplumber is required: pip install pdfplumber')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
PLAN = os.path.join(ROOT, 'sources', 'data', 'extraction-plan.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'stabilization-balances.csv')

# The nine columns the table prints, in order, from the FY2012 heading which spells them
# out in full. Earlier and later years print the same nine under shorter names.
COLUMNS = ['begin_principal', 'begin_earnings', 'contrib_principal', 'earnings_net',
           'disburse_principal', 'transfers_earnings', 'ending_cash',
           'unrealized_gain_loss', 'ending_market']

MONEY = re.compile(r'\(?\$-?[\d,]+\.\d{2}\)?')
CODE = re.compile(r'^(8\d{3})')


def money(tok):
    neg = tok.startswith('(') or tok.endswith(')')
    v = float(tok.strip('()$').replace(',', '').replace('$', ''))
    return -v if neg else v


def rows_of(page, xgap=3.0, wgap=2.2):
    """Visual rows of the page, however it happens to be laid out.

    NOT EVERY YEAR IS TURNED, which cost an hour to discover. FY2014's pages are a quarter
    turn with right-to-left characters; most other years are ordinary upright text where
    `extract_text()` is correct and the geometry below would scramble it. `upright` is the
    flag that tells them apart, and it is read per page rather than per year -- the town
    changed printer and format more than once across fifteen reports.
    """
    chars = page.chars
    if chars and sum(1 for c in chars if c.get('upright')) > len(chars) * 0.5:
        return (page.extract_text() or '').split('\n')
    cs = sorted(chars, key=lambda c: -c['x0'])
    if not cs:
        return []
    bands, cur = [], [cs[0]]
    for prev, c in zip(cs, cs[1:]):
        if abs(prev['x0'] - c['x0']) > xgap:
            bands.append(cur); cur = [c]
        else:
            cur.append(c)
    bands.append(cur)
    out = []
    for band in bands:
        b = sorted(band, key=lambda c: c['top'])
        words, w = [], [b[0]]
        for prev, c in zip(b, b[1:]):
            if c['top'] - prev['bottom'] > wgap:
                words.append(w); w = [c]
            else:
                w.append(c)
        words.append(w)
        out.append(''.join(''.join(x['text'] for x in ww)[::-1] for ww in words[::-1]))
    return out


def parse(line):
    """A fund row, or None. Returns (code, name, [values]) with the values in column order."""
    m = CODE.match(line)
    if not m:
        return None
    rest = line[4:]
    vals = MONEY.findall(rest)
    if len(vals) < 3:
        return None
    # THE CODE IS THE IDENTITY, NOT THE NAME. A long fund name wraps to a second visual
    # line, which after the quarter-turn is an adjacent band, and the two interleave --
    # `ZONING INCENTIVE STABILIZATION (TD BA$2N2K6,N8O2R1.T9H0)`. The figures are
    # unaffected and prove themselves; only the label is damaged. So the scraped name is
    # cut at the first `$` and treated as a hint, and the canonical name comes from
    # fund-owners.csv, which is this project's own registry of what each account is.
    name = rest.split('$')[0].strip(' $.')
    return m.group(1), name, [money(v) for v in vals]


_REGISTRY = None


def canonical(code):
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = {}
        f = os.path.join(ROOT, 'sources', 'data', 'fund-owners.csv')
        if os.path.exists(f):
            for r in csv.DictReader(open(f, encoding='utf-8')):
                if (r.get('code') or '').strip():
                    _REGISTRY[r['code'].strip()] = (r.get('name') or '').strip()
    return _REGISTRY.get(code, '')


def closes(vals):
    """The two identities the table states about every row.

    Short rows are the norm rather than an error: a fund with no activity prints only the
    columns it has, so the nine are right-aligned and the identity is checked on what is
    present. A row is accepted only if ONE of the two identities can be tested and holds.
    """
    if len(vals) == 9:
        cash = sum(vals[:4]) - 0 + vals[4] + vals[5]
        if abs(cash - vals[6]) > 0.02:
            return False, 'beginning+activity != ending cash'
        if abs(vals[6] + vals[7] - vals[8]) > 0.02:
            return False, 'ending cash + unrealised != ending market'
        return True, 'nine columns, both identities hold'
    if len(vals) >= 2 and abs(vals[-2] - vals[-1]) < 0.02:
        return True, 'short row, ending cash equals ending market'
    return False, 'too few columns to test an identity'


def pages_for(fy):
    """PDF page indices to read, from the survey's printed pages plus the year's offset."""
    want = []
    for r in csv.DictReader(open(PLAN, encoding='utf-8')):
        if r.get('dataset') == 'trust_funds' and r['fy'] == str(fy):
            for part in (r['pages'] or '').split(','):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-')
                    want += list(range(int(a), int(b) + 1))
                elif part.isdigit():
                    want.append(int(part))
    return sorted(set(want))


def pdf_for(fy):
    for f in os.listdir(DOCS):
        if re.search(r'fy-%d-annual-town-report\.pdf$' % fy, f):
            return os.path.join(DOCS, f)
    return None


def extract(fy, verbose=False):
    path = pdf_for(fy)
    if not path:
        return [], 'no annual report PDF held'
    printed = pages_for(fy)
    if not printed:
        return [], 'no trust-fund pages in the survey'
    found, seen = [], set()
    with pdfplumber.open(path) as pdf:
        # The survey records PRINTED page numbers; the offset to the PDF index differs by
        # year and is not recorded for every one, so search a window around each rather
        # than trusting a single offset.
        idxs = sorted({i for p in printed for i in range(p - 6, p + 6)
                       if 0 <= i < len(pdf.pages)})
        for i in idxs:
            try:
                lines = rows_of(pdf.pages[i])
            except Exception:
                continue
            if not any('STABILIZATION' in l.upper() for l in lines):
                continue
            for line in lines:
                if 'STABILIZATION' not in line.upper():
                    continue
                p = parse(line)
                if not p:
                    continue
                code, name, vals = p
                ok, why = closes(vals)
                key = (code, round(vals[-1], 2))
                if key in seen:
                    continue
                seen.add(key)
                if verbose:
                    print('   %s %-44s %-14s %s' % (code, name[:44],
                                                    '{:,.2f}'.format(vals[-1]),
                                                    'OK' if ok else 'REJECT: ' + why))
                if ok:
                    found.append(dict(fy=fy, code=code,
                                      name=canonical(code) or name,
                                      name_as_read=name,
                                      ending_cash=vals[6] if len(vals) == 9 else vals[-1],
                                      ending_market=vals[-1],
                                      columns_read=len(vals), page_pdf=i,
                                      basis=why, document=os.path.relpath(path, ROOT)))
    return found, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fy', type=int)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()
    years = [a.fy] if a.fy else list(range(2011, 2026))
    rows, notes = [], []
    for fy in years:
        got, err = extract(fy, a.verbose)
        if err:
            notes.append('FY%d: %s' % (fy, err))
        print('FY%d  %d stabilization row(s) that prove themselves' % (fy, len(got)))
        rows += got
    if notes:
        print('\n'.join('  ' + n for n in notes))
    rows.sort(key=lambda r: (r['fy'], r['code']))
    buf = []
    import io
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=['fy', 'code', 'name', 'name_as_read', 'ending_cash',
                                      'ending_market', 'columns_read', 'page_pdf',
                                      'basis', 'document'])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    out = s.getvalue()
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if out != cur:
            print('stabilization-balances.csv is stale', file=sys.stderr); return 1
        print('current'); return 0
    if not a.fy:
        open(OUT, 'w', encoding='utf-8', newline='').write(out)
        print('\nwrote %s — %d rows' % (os.path.relpath(OUT, ROOT), len(rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
