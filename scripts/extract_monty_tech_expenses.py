"""Monty Tech's district expenses by category, off the chart in the annual town report.

    python3 scripts/extract_monty_tech_expenses.py
    python3 scripts/extract_monty_tech_expenses.py --check

Writes `sources/data/monty-tech-expenses.csv`.

WHY THIS ONE IS READ FROM OCR, WHEN THE PAGE IS BORN-DIGITAL

The gate in `notes/process/READING-A-DIGITAL-PAGE.md` says a text layer outranks OCR and
the OCR reading is discarded. This page is the exception the gate allows for, and it has to
be checked rather than assumed: FY2025 page 115 carries its own text, and the table is NOT
in it. The page embeds a single IMAGE from x 25 to 597 and y 194 to 530 -- a chart, with the
figures drawn into it -- so `extract_words()` returns the surrounding prose and a hole where
the numbers are. Recognition is the only reader for that rectangle, and reporting the hole
as `the town does not publish this` would be rule 13c exactly.

The test is the one the gate names, applied to the REGION rather than the page: ask the
text layer for the words inside the table's bounds. None means an image.

WHAT THE CHART IS

A 100% stacked bar, one bar per fiscal year, with every segment's dollar value drawn on it:
eight spending categories and a `District Expenses` total, across three years. It is the
only published breakdown of the OTHER district Lunenburg pays into.

ORDER IS THE RULE HERE, AND POSITION IS NOT -- WHICH IS BACKWARDS FROM A TABLE

Rule 13b says place a figure by the column it sits nearest and never by the order it
appears. That rule is about a TABLE, where x means a column. On a bar chart x means a
VALUE: a label sits at the end of its segment, so `Fixed Assets` FY23 is drawn at x=0.23
and `Grants` FY25 at x=0.76, and clustering them into columns would file the small years
together and the large years together. Within a row the three segments are always drawn in
year order, so the order IS the column here. A row that does not carry exactly one figure
per year is refused rather than guessed at.

WHAT PROVES IT

The chart states an identity about itself: `District Expenses` is the sum of the eight
categories, in every year. Nothing is written unless all three close to the dollar. That is
what makes reading digits off a picture safe -- a misread digit cannot survive it.

AND IT CORROBORATES THE PROSE ON THE SAME PAGE. The seven categories excluding `Grants`
sum to $33,334,173 for FY25, and the paragraph above the chart calls the FY2024-2025
Educational Plan $33,334,174. The two differ by a dollar of rounding, and together they say
what the Educational Plan is: district expenses less grant-funded spending. That is recorded
as an observation; the page does not state the relationship, and this does not test it.

THIS IS NOT LUNENBURG'S MONEY (rule 11). It is the Montachusett Regional Vocational
Technical School District's own spending, across eighteen member towns. Lunenburg's budget
carries a single assessment line. These figures must never be summed with the Lunenburg
district's, and the `district` column says so on every row.
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
OUT = os.path.join(ROOT, 'sources', 'data', 'monty-tech-expenses.csv')

MONEY = re.compile(r'^\$[\d,]+$')
TOTAL = 'District Expenses'
LEGEND = re.compile(r'FY\s?(\d\d)')
FIELDS = ['report_fy', 'district', 'category', 'fy', 'amount', 'kind', 'proof',
          'page', 'document']
# CLUSTER ON THE GAP, DO NOT ROUND TO A GRID. Rounding y to a fixed band split four of the
# nine rows in half -- `Fixed Assets` has its figures at 0.427 and 0.430, which round to
# different bands at any divisor near the row pitch, while two ADJACENT rows can round
# together. The gap within a row here is at most 0.004 and the gap between rows is 0.035, so
# the two are not close and a threshold between them cannot be wrong. Rule 13b's own point:
# measure the page's pitch, never guess a tolerance.
GAP = 0.012


def num(t):
    return int(t.replace('$', '').replace(',', ''))


def rows_on(boxes):
    """One row per category: the label, and its figures in the order they are drawn.

    THE TOTAL'S LABEL IS DRAWN BELOW ITS FIGURES, and every other label beside them. The
    bar's own total sits at the end of the bar while `District Expenses` is the axis caption
    under it -- 0.04 down the page, a whole row away. So a band of figures with no label
    takes the label from the next band that has a label and no figures. Without that the
    total row is dropped and the identity has nothing to close against.
    """
    ys = sorted(boxes, key=lambda b: b['y'])
    bands = [[ys[0]]]
    for a, b in zip(ys, ys[1:]):
        if b['y'] - a['y'] > GAP:
            bands.append([])
        bands[-1].append(b)

    parsed = []
    for bs in bands:
        bs = sorted(bs, key=lambda b: b['x'])
        figs = [num(b['text'].strip()) for b in bs if MONEY.match((b['text'] or '').strip())]
        label = ' '.join((b['text'] or '').strip() for b in bs
                         if not MONEY.match((b['text'] or '').strip())).strip()
        parsed.append((label, figs))

    out = []
    for i, (label, figs) in enumerate(parsed):
        if figs and not label:
            nxt = next((l for l, f in parsed[i + 1:i + 2] if l and not f), None)
            label = nxt or ''
        if figs and label:
            out.append((label, figs))
    return out


def read_page(path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pdf_tables as T
    by = collections.defaultdict(list)
    for b in T.read_boxes(path):
        by[str(b['page'])].append(b)
    for page, boxes in sorted(by.items(), key=lambda kv: int(kv[0])):
        rows = rows_on(boxes)
        if not any(r[0].startswith(TOTAL) for r in rows):
            continue
        legend = next((b['text'] for b in boxes
                       if len(LEGEND.findall(b['text'] or '')) >= 3), None)
        if not legend:
            continue
        return int(page), rows, ['20' + y for y in LEGEND.findall(legend)]
    return None, [], []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    body = []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        report_fy = int(m.group(1))
        page, rows, years = read_page(f)
        if not page:
            continue

        # EXACTLY ONE FIGURE PER YEAR, OR THE ROW IS REFUSED. A segment too narrow to carry
        # its label, or two labels recognised as one box, both show up here -- and either
        # would shift every later year on that row by one.
        keep = [(lbl, v) for lbl, v in rows if len(v) == len(years)]
        short = [lbl for lbl, v in rows if len(v) != len(years)]
        total = next((v for lbl, v in keep if lbl.startswith(TOTAL)), None)
        cats = [(lbl, v) for lbl, v in keep if not lbl.startswith(TOTAL)]
        if total is None or len(cats) < 4:
            print('FY%d p%s: no usable chart (%d categories, total=%s)'
                  % (report_fy, page, len(cats), total), file=sys.stderr)
            continue

        # THE IDENTITY THE CHART STATES ABOUT ITSELF, in every year. Nothing is written
        # unless all of them close.
        bad = []
        for i, fy in enumerate(years):
            got = sum(v[i] for _, v in cats)
            if got != total[i]:
                bad.append('%s: the %d categories sum to %d against a drawn %d (%+d)'
                           % (fy, len(cats), got, total[i], got - total[i]))
        if bad:
            print('FY%d p%s does not close, nothing written:\n  %s'
                  % (report_fy, page, '\n  '.join(bad)), file=sys.stderr)
            return 1
        if short:
            print('FY%d p%s: %d rows refused for carrying the wrong number of figures: %s'
                  % (report_fy, page, len(short), '; '.join(short)), file=sys.stderr)

        proof = ('District Expenses is the sum of the %d categories in every year drawn'
                 % len(cats))
        for lbl, v in [(TOTAL, total)] + cats:
            for i, fy in enumerate(years):
                body.append(dict(
                    report_fy=report_fy, district='Montachusett Regional Vocational '
                    'Technical (Monty Tech) -- NOT the Lunenburg district',
                    category=' '.join(lbl.split()), fy=fy, amount=v[i],
                    kind='total' if lbl == TOTAL else 'category', proof=proof,
                    page=page, document=os.path.relpath(f, ROOT)))

    if not body:
        print('no annual report carries the Monty Tech expense chart', file=sys.stderr)
        return 1

    body.sort(key=lambda r: (r['report_fy'], r['fy'], r['kind'] != 'total', r['category']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(body)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/extract_monty_tech_expenses.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d figures, the total closes in every year' % len(body))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote %s -- %d figures' % (os.path.relpath(OUT, ROOT), len(body)))
    for fy in sorted({r['report_fy'] for r in body}):
        rs = [r for r in body if r['report_fy'] == fy]
        print('  FY%d  p%s  %d categories x %d years'
              % (fy, rs[0]['page'], len({r['category'] for r in rs}) - 1,
                 len({r['fy'] for r in rs})))
    return 0


if __name__ == '__main__':
    sys.exit(main())
