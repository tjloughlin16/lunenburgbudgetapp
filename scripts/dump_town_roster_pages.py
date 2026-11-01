#!/usr/bin/env python3
"""Write every TOWN officials/staff list page to numbered text, with column positions.

The school rosters have their own dumper (`dump_roster_pages.py`). This is the town side:
the officers' directory at the front of nearly every annual report -- elected and
appointed, usually with the year a term ends -- and any department staff list registered
in `sources/data/town-rosters/PAGES.csv`.

**The pages come from PAGES.csv, which was written by looking, not by matching.** The
directory is called `TOWN GOVERNMENT` (1959), `About the Town Officials` (1965),
`Town Officials` (1970s-1990s), `2005 ELECTED OFFICIALS` / `FY'05 APPOINTMENT LIST`
(2000s) and `ELECTED OFFICIALS` / `APPOINTED OFFICIALS` (FY2014 on), and in 1995 the
elected list starts two-thirds of the way down the appointed list's second page. Each
edition's pages were found from its own text (rule 13c) and the file records them.

**Why positions.** These lists are printed in two to four columns with the headings in
one row and the names in rows beneath. A text layer that reads left to right interleaves
the columns (1965 p5 reads `Moderator / Board of Assessors / Commissioners of Trust Funds /
Planning Board / 1967 Richard Shifler / 1966 Leroy Allen ...`), and nothing in that order
says which name sits under which heading. So each printed run is written with its left
edge as a percentage of the page width (`@38`), which is what a reader needs to put a
name under the heading above it.

Sources, in order: Textract's lines for the document (all calendar editions and some FY
ones); otherwise the PDF's own words (digital FY reports); otherwise the OCR cache in
`report_pages` (scanned FY reports), whose leading spaces carry the column.

Output: `sources/data/town-rosters/<edition>-p<NNN>.txt`, every non-blank line numbered,
because line accounting is the only check a list with no printed total allows.

    python3 scripts/dump_town_roster_pages.py [--edition 1965]
"""

import argparse
import csv
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
OUT = os.path.join(ROOT, 'sources', 'data', 'town-rosters')
PAGES = os.path.join(OUT, 'PAGES.csv')
TEXTRACT_OUT = os.path.join(ROOT, 'build', 'textract', 'out')


def rows_from_runs(runs):
    """[(top, height, left, text)] -> [[(left, text), ...] per printed row], top to bottom.
    Runs whose vertical middles fall within half the page's median line height share a
    row -- the same rule `dump_roster_pages.textract_lines` uses."""
    heights = sorted(h for _, h, _, _ in runs if h > 0)
    band = (heights[len(heights) // 2] if heights else 0.01) * 0.5
    rows = []
    for top, h, left, text in sorted(runs, key=lambda t: t[0] + t[1] / 2):
        mid = top + h / 2
        if rows and abs(mid - rows[-1][0]) <= band:
            rows[-1][1].append((left, text))
        else:
            rows.append([mid, [(left, text)]])
    return [sorted(cells) for _, cells in rows]


def textract_runs(doc):
    path = os.path.join(TEXTRACT_OUT, os.path.splitext(doc)[0] + '.lines.tsv')
    if not os.path.exists(path):
        return None
    by = {}
    for r in csv.DictReader(open(path, newline='', encoding='utf-8'), delimiter='\t'):
        by.setdefault(int(r['page']), []).append(
            (float(r['top']), float(r['height']), float(r['left']), r['text']))
    return by


def pdf_runs(doc, page):
    """Words from the PDF's text layer, joined into runs where the gap is under ~1.5
    characters, as fractions of the page. None when the page has no text layer."""
    import pdfplumber
    with pdfplumber.open(os.path.join(DOCS, doc)) as pdf:
        pg = pdf.pages[page - 1]
        W, H = float(pg.width), float(pg.height)
        words = pg.extract_words(keep_blank_chars=False, use_text_flow=False)
    if not words:
        return None
    words.sort(key=lambda w: (round(w['top']), w['x0']))
    runs = []
    for w in words:
        cw = (w['x1'] - w['x0']) / max(len(w['text']), 1)
        if runs:
            t, h, x0, x1, text = runs[-1]
            if abs(w['top'] - t) < h * 0.5 and 0 <= w['x0'] - x1 < max(cw * 1.6, 4):
                runs[-1] = (t, h, x0, w['x1'], text + ' ' + w['text'])
                continue
        runs.append((w['top'], w['bottom'] - w['top'], w['x0'], w['x1'], w['text']))
    return [(t / H, h / H, x0 / W, text) for t, h, x0, _x1, text in runs]


def ocr_runs(edition, page):
    import report_pages as RP
    lines = RP.load(edition, ocr=True).get(page) or []
    width = max((len(l) for l in lines), default=1) or 1
    out = []
    for i, l in enumerate(lines):
        for m in re.finditer(r'\S+(?: \S+)*', l):
            out.append((i / max(len(lines), 1), 0.5 / max(len(lines), 1),
                        m.start() / width, m.group(0)))
    return out or None


def render(rows):
    out = []
    for cells in rows:
        txt = '   '.join('@%02d %s' % (min(int(left * 100), 99), ' '.join(t.split()))
                         for left, t in cells if t.strip())
        if txt.strip():
            out.append(txt)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edition', action='append', help='only these editions (repeatable)')
    args = ap.parse_args()
    want = set(args.edition or [])
    plan = list(csv.DictReader(open(PAGES, newline='', encoding='utf-8')))
    tx_cache = {}
    n_pages = n_lines = 0
    for r in plan:
        if want and r['edition'] not in want:
            continue
        doc, page, ed = r['document'], int(r['page']), r['edition']
        if doc not in tx_cache:
            tx_cache[doc] = textract_runs(doc)
        tx = tx_cache[doc]
        # Textract read FINANCIAL pages only for some reports, so a document can have a
        # lines file that does not cover this page.
        if tx is not None and tx.get(page):
            runs, how = tx[page], 'Textract lines'
        else:
            runs, how = pdf_runs(doc, page), 'the PDF text layer'
            # A MIXED page (rule 13d): a text layer holding only the page number over a
            # picture of the list (FY2023 p96, the police roster). Too few runs is a
            # statement about the text layer, not the page, so the OCR is consulted and the
            # fuller reading kept.
            if not runs or len(runs) < 8:
                alt = ocr_runs(ed, page)
                if alt and len(alt) > len(runs or []):
                    runs, how = alt, 'the OCR cache (report_pages)'
        lines = render(rows_from_runs(runs or []))
        name = '%s-p%03d.txt' % (ed, page)
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as fh:
            fh.write('# %s page %d -- edition %s -- %s list -- read from %s\n'
                     % (doc, page, ed, r['list'], how))
            fh.write('# %d non-blank lines. @NN = left edge of the run, %% of page width. '
                     'Every line must be accounted for.\n\n' % len(lines))
            for i, l in enumerate(lines, 1):
                fh.write('%4d| %s\n' % (i, l))
        n_pages += 1
        n_lines += len(lines)
        if len(lines) < 5:
            print('  %s: only %d lines -- look at the page before reading it as short'
                  % (name, len(lines)))
    print('%d pages, %d lines to account for -> %s' % (n_pages, n_lines,
                                                      os.path.relpath(OUT, ROOT)))


if __name__ == '__main__':
    main()
