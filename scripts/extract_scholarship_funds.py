#!/usr/bin/env python3
"""School scholarship and prize funds, every year, read off the annual reports' trust fund
summaries and proved row by row.

    python3 scripts/extract_scholarship_funds.py           # write sources/data/scholarship-funds.csv
    python3 scripts/extract_scholarship_funds.py --check
    python3 scripts/extract_scholarship_funds.py --fy 2018 --verbose

WHY THIS EXISTS. TJ, 4 November 2026: *"im looking to see how much is given out each year by
each scholarship."* The scholarship funds print on the same trust fund summary pages as the
stabilization funds, so the same reader reads them: `read_trust_table.rows()` returns EVERY row
on a page, and this keeps the ones that are a fund on `build_school_scholarships.FUNDS`.

NOTHING IS TRUSTED. A row is written only when the table's own identity closes on it
(`R.verify`), or when last year's PROVEN ending cash plus this year's activity closes it
(`R.verify_from_prior`). The basis column says which. FY2025 is taken from
`trust-fund-matrix.csv`, which is the same page read and proven by another pipeline.

WHAT `paid_out` IS, AND WHAT IT IS NOT. The layouts differ year to year: FY2018 prints
`DISBURSE FROM PRINCIPAL` and `TRANSFERS OF EARNINGS`; FY2025 prints `TRANSFERS OF PRINCIPAL`
and `TRANSFERS OF EARNINGS`. `net_transfers` is the sum of whichever of those the year
prints, as printed; `paid_out` is its negative where that sum is negative, else 0. The
sum, not each column: FY2018's Mabel Allen and Harwood prizes each print +72.50 of earnings
transferred IN, and a positive disbursement is money in too (Pete Lincoln FY2018, +15,000.00,
the fund's start). Rule 7: the table says money left the fund. That it was an award to a
student is OUR reading -- the round totals ($500, $1,000, $2,000) are why it is a good one,
and nothing on the page states it.

COVERAGE IS PARTIAL AND SAYS SO. A fund missing from a year here is missing because no row
for it proved -- a statement about our reading, not about the town (rule 13c). `--check`
fails if the file drifts; it does not claim the series is complete.
"""
import argparse
import csv
import glob
import io
import json
import os
import re
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T                    # noqa: E402
import read_trust_table as R              # noqa: E402
import extract_stabilization as S         # noqa: E402
import build_school_scholarships as B     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'scholarship-funds.csv')
MATRIX = os.path.join(ROOT, 'sources', 'data', 'trust-fund-matrix.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
TEXTRACT_CACHE = os.path.join(ROOT, 'build', 'textract', 'cache')

# The printed columns carried into the CSV, in the reader's names. Absent where the year's
# layout does not print the column -- never 0, because "not printed" and "printed as zero"
# are different facts.
COLS = ['begin_principal', 'begin_earnings', 'contrib_principal', 'net_earnings',
        'disburse_principal', 'transfers_principal', 'transfers_earnings',
        'ending_cash', 'ending_market']
OUTFLOW = ('disburse_principal', 'transfers_principal', 'transfers_earnings')

FIELDS = ['fy', 'fund', 'account', 'printed_name'] + COLS + [
    'net_transfers', 'reclassified', 'paid_out', 'page', 'basis', 'document']

# trust-fund-matrix.csv measure -> reader column. Only what COLS carries.
MATRIX_COLS = {
    'beginning principal (non-expendable)': 'begin_principal',
    'beginning earnings (expendable)': 'begin_earnings',
    'net earnings': 'net_earnings',
    'transfers of principal (non-expendable)': 'transfers_principal',
    'transfers of earnings (expendable)': 'transfers_earnings',
    'ending cash value': 'ending_cash',
    'ending market value': 'ending_market',
}


def fund_of(text):
    """The FUNDS display name a printed row belongs to, or None. Surname match, because
    one fund prints as COWDRY and COWDREY."""
    t = ' '.join((text or '').split())
    hits = [disp for disp, pat, _, _ in B.FUNDS if re.search(pat, t, re.I)]
    # A ROW NAMING TWO FUNDS IS NOT A FUND'S ROW. Textract sometimes returns a page's whole
    # name column as one LINE (FY2019 p46 and others), and the reader then anchors one "row"
    # on eleven fund names. Refused -- never assigned to whichever matched first.
    return hits[0] if len(hits) == 1 else None


def account_of(text):
    """`stock` for a share holding printed as its own row, else `fund`.

    The Mabel Allen and Joseph Harwood prizes each print a SECOND row most years --
    `MABEL ALLEN UNITIL STOCK #20376`, `JOSEPH HARWOOD UNITIL STOCK` -- a holding of shares
    carried at a fixed book value, in the "held by other banks" table. Keyed on the fund
    alone, the stock row competed with the prize row for one slot and sometimes won. They are
    two accounts and are written as two."""
    return 'stock' if re.search(r'\bSTOCK\b', (text or '').upper()) else 'fund'


def candidate(text):
    """A row that LOOKS like a school award but is on no list -- printed, never written."""
    return bool(re.search(r'SCHOLAR|PRIZE|AWARD', (text or '').upper()))


def pdf_of(fy):
    """(archive-relative PDF path, sha256) of the year's annual report, from the manifest."""
    for r in csv.DictReader(open(MANIFEST, encoding='utf-8')):
        k = r['key']
        if (k.startswith('town-annual-reports/docs/')
                and re.search(r'fy-%d-annual-town-report\.pdf$' % fy, k)):
            return os.path.join('sources', k), r['sha256']
    return None, None


def textract_boxes(sha, page):
    """Textract's LINE blocks for one page, shaped like the Vision TSV's boxes: x = left edge,
    y = bottom edge with the origin at the bottom-left (ocr_pdf.swift emits Vision's
    `minX, minY` unchanged), so `R.rows` reads them without knowing which instrument it is.

    A SECOND INSTRUMENT, NOT A CORRECTION OF THE FIRST. Vision lost figures on the short years
    (FY2012, FY2017, FY2021, FY2023); Textract's cached read of the same page is tried through
    the same reader and must prove a row by the same identities. Nothing here is re-read: these
    are the cache files `annual_report_textract` already paid for."""
    if not sha:
        return []
    hits = sorted(glob.glob(os.path.join(TEXTRACT_CACHE, sha, 'p%03d-*.json' % page)))
    hits = [h for h in hits if not h.endswith('-reread.json')]
    hits.sort(key=lambda h: (not h.endswith('-tables.json'), h))
    for h in hits:
        lines = [b for b in json.load(open(h, encoding='utf-8'))['Blocks']
                 if b['BlockType'] == 'LINE']
        # A PAGE SET SIDEWAYS. Several trust summaries are printed landscape and scanned
        # portrait, and Textract reports geometry in the IMAGE frame, so the reader sees each
        # fund as a column. The text direction is in each line's polygon (its first edge runs
        # along the text) -- extract_gross_wages.py met the same thing on FY2016's wage list.
        # The page is turned back so text runs left to right, in the bottom-left frame.
        def run(b):
            q = b['Geometry']['Polygon']
            return q[1]['X'] - q[0]['X'], q[1]['Y'] - q[0]['Y']
        down = sum(1 for b in lines if abs(run(b)[1]) > abs(run(b)[0]) and run(b)[1] > 0)
        up = sum(1 for b in lines if abs(run(b)[1]) > abs(run(b)[0]) and run(b)[1] < 0)
        out = []
        for b in lines:
            g = b['Geometry']['BoundingBox']
            if down > len(lines) / 2:        # reads top to bottom: turned a quarter clockwise
                x, y, w, hh = g['Top'], g['Left'], g['Height'], g['Width']
            elif up > len(lines) / 2:        # reads bottom to top: a quarter anticlockwise
                x, y = 1 - (g['Top'] + g['Height']), 1 - (g['Left'] + g['Width'])
                w, hh = g['Height'], g['Width']
            else:
                x, y, w, hh = g['Left'], 1 - (g['Top'] + g['Height']), g['Width'], g['Height']
            out.append(dict(page=page, x=x, y=y, w=w, h=hh, conf=b['Confidence'] / 100,
                            text=b['Text']))
        if out:
            return out
    return []


def from_ocr(fy, path, prior, verbose=False):
    boxes = T.read_boxes(path)
    pats = [pat for _, pat, _, _ in B.FUNDS]
    pages = sorted({b['page'] for b in boxes
                    if any(re.search(p, b['text'] or '', re.I) for p in pats)})
    pdf, sha = pdf_of(fy)
    reads = []
    for p in pages:
        reads.append((p, 'vision', [b for b in boxes if b['page'] == p],
                      os.path.relpath(path, ROOT)))
        tb = textract_boxes(sha, p)
        if tb:
            reads.append((p, 'textract', tb, pdf))
    found, strays = {}, set()
    for p, instrument, pb, doc in reads:
        rows, cols = R.rows(pb, fy, geom={})
        rows = name_positional(cols, rows, fy)
        if len(cols) < 3:
            continue
        for r in rows:
            label = (r['code'] + ' ' + r['name']).strip()
            fund = fund_of(label)
            if not fund:
                if candidate(label):
                    strays.add(' '.join(label.split())[:50])
                continue
            ok, why = R.verify(r['cells'])
            if not ok:
                ok, why = R.verify_from_prior(r['cells'], prior.get((fund, account_of(label))))
            if not ok or 'ending_cash' not in r['cells']:
                if verbose:
                    print('   page %d: %s REFUSED (%s)' % (p, fund, why))
                continue
            key = (fund, account_of(label))
            # Vision first on a tie: it is the instrument every other trust extract reads,
            # so a fund both prove keeps the citation the rest of the archive uses.
            strength = (why == 'both identities hold', len(r['cells']), instrument == 'vision')
            if key not in found or strength > found[key][0]:
                found[key] = (strength, p, r, why + ' (%s)' % instrument, doc)
    out = []
    for (fund, _), (_, p, r, why, doc) in found.items():
        out.append(row(fy, fund, ' '.join(r['name'].split()), r['cells'], p, why, doc))
    return out, strays


def from_matrix(fy):
    """FY2025 (and any year the matrix holds): already proven by build_trust_fund_matrix."""
    by = {}
    for m in csv.DictReader(open(MATRIX, encoding='utf-8')):
        if int(m['fy']) != fy or m['kind'] != 'fund':
            continue
        fund = fund_of(m['column'])
        col = MATRIX_COLS.get(m['measure'])
        if fund and col:
            d = by.setdefault(fund, dict(name=m['column'], page=m['page'],
                                         proof=m['proof'], doc=m['document'], cells={}))
            d['cells'][col] = float(m['amount'] or 0)
    return [row(fy, f, d['name'], d['cells'], d['page'],
                d['proof'] + ' (trust-fund-matrix.csv)', d['doc'])
            for f, d in by.items()]


def row(fy, fund, name, cells, page, basis, doc):
    present = [c for c in OUTFLOW if c in cells]
    flows = {c: cells[c] for c in present}
    # AN EARNINGS-TO-PRINCIPAL MOVE IS NOT A PAYOUT. FY2017's Cowdry row prints CONTRIBUTE TO
    # PRINCIPAL +12,528.46 and TRANSFERS OF EARNINGS -12,528.46: the same money, one column to
    # another, and principal rises by exactly that the next year (359,426.21 -> 371,954.67).
    # Counted as an outflow it is a $12,528 award that never left the fund. Only an EXACT
    # offset on one row is taken as this -- a gift and an award in the same year are real and
    # common (Nelson FY2012: +2,411.92 in, $500 out), and netting the contribution in general
    # would hide the award inside the gift.
    contrib = cells.get('contrib_principal') or 0
    reclass = ''
    if contrib:
        for c in present:
            if abs(flows[c] + contrib) < 0.005:
                reclass = round(contrib, 2)
                del flows[c]
                break
    net = round(sum(flows.values()), 2) if present else ''
    out = dict(fy=fy, fund=fund, account=account_of(name), printed_name=name, page=page,
               basis=basis, document=doc, net_transfers=net, reclassified=reclass,
               paid_out=(round(-net, 2) if net != '' and net < 0 else (0 if net != '' else '')))
    for c in COLS:
        out[c] = round(cells[c], 2) if c in cells else ''
    return out


def name_positional(cols, rows, fy):
    """Name a page's POSITIONAL columns from the year's written-down layout -- only when it
    fits exactly.

    FY2017 p38 prints the NINE header (read off the page, 4 Nov 2026: BEGINNING PRINCIPAL |
    BEGINNING EARNINGS | CONTRIBUTE TO PRINCIPAL | NET EARNINGS | DISBURSE FROM PRINCIPAL |
    TRANSFERS OF EARNINGS | ENDING CASH VALUE | UNREALIZED GAIN/LOSS | ENDING MARKET VALUE),
    and `R.LAYOUTS` already says 2017 is NINE -- but the reader returned nine positional
    columns (`activity_0..5`, `ending_cash`, `unreal_0..1`) and named none of them. Those rows
    PROVE, because a sum closes in any column order, and so cannot say which figure is the
    payout. The names are applied here only where the count matches the layout AND
    `ending_cash` sits at the layout's own index; anything else stays positional and its
    `paid_out` stays empty. Rule 13b, rule 4: a position is not a name unless a header says so.
    """
    names = [c['name'] for c in cols]
    layout = R.LAYOUTS.get(fy)
    if (not layout or len(names) != len(layout) or 'ending_cash' not in names
            or names.index('ending_cash') != layout.index('ending_cash')
            or not any(re.match(r'(activity|unreal)_\d', n or '') for n in names)):
        return rows
    m = dict(zip(names, layout))
    for r in rows:
        r['cells'] = {m.get(k, k): v for k, v in r['cells'].items()}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fy', type=int)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()

    matrix_years = {int(m['fy']) for m in csv.DictReader(open(MATRIX, encoding='utf-8'))}
    # A PARTIAL TREE MAY NOT PUBLISH A COUNT. Textract proves 83 of these rows from a
    # gitignored cache; without it this would write a SHORTER file that reads exactly like a
    # complete one. Refuse instead, and say what restores it.
    gone = [fy for fy, _ in S.year_files() if fy not in matrix_years
            and pdf_of(fy)[1] and not os.path.isdir(os.path.join(TEXTRACT_CACHE, pdf_of(fy)[1]))]
    if gone:
        raise SystemExit('extract_scholarship_funds: no Textract cache for FY%s under %s -- '
                         'restore build/textract/cache before running; refusing to write a '
                         'short file.' % (', FY'.join(map(str, gone)),
                                          os.path.relpath(TEXTRACT_CACHE, ROOT)))
    rows, prior, strays = [], {}, {}
    # OLDEST FIRST: verify_from_prior leans on last year's proven ending cash.
    for fy, path in sorted(S.year_files()):
        if a.fy and fy not in (a.fy, a.fy - 1):
            continue
        if fy in matrix_years:
            got = from_matrix(fy)
        else:
            got, st = from_ocr(fy, path, prior, a.verbose and fy == (a.fy or fy))
            if st:
                strays[fy] = st
        if not a.fy or fy == a.fy:
            print('FY%d  %2d of %d funds proven' % (fy, len({r['fund'] for r in got if r['account'] == 'fund'}), len(B.FUNDS)))
            if a.verbose:
                for r in sorted(got, key=lambda r: r['fund']):
                    print('   p%s %-38s paid out %10s  end %12s  %s'
                          % (r['page'], r['fund'], r['paid_out'], r['ending_cash'],
                             r['basis'][:40]))
            rows += got
        for r in got:
            prior[(r['fund'], r['account'])] = float(r['ending_cash'])

    if strays:
        print('\nnamed like an award, on no fund list (not written):')
        for fy in sorted(strays):
            for s in sorted(strays[fy]):
                print('  FY%d  %s' % (fy, s))

    rows.sort(key=lambda r: (r['fy'], r['fund'], r['account']))
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    out = s.getvalue()
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if out != cur:
            print('scholarship-funds.csv is stale', file=sys.stderr)
            return 1
        print('current: %d proven rows' % len(rows))
        return 0
    if not a.fy:
        open(OUT, 'w', encoding='utf-8', newline='').write(out)
        print('\nwrote %s -- %d proven rows across %d years'
              % (os.path.relpath(OUT, ROOT), len(rows), len({r['fy'] for r in rows})))
    return 0


if __name__ == '__main__':
    sys.exit(main())
