#!/usr/bin/env python3
"""One place that turns the sixteen annual reports into pages of text, and caches it.

Every extractor needs the same thing: each page as lines, read by whichever instrument
works on it. Each was doing that for itself -- opening all sixteen PDFs and running
`instrument()` over 2,751 pages to choose an extraction mode -- which costs minutes per
run. With four extractors and two or three iterations each to get right, that is most of
an afternoon spent re-deciding the same 2,751 questions.

So it is done once and written to `sources/town-budget/pages/FY####.txt`, and everything
reads from there. The cache records which instrument read each page, because that is part
of the finding rather than an implementation detail.

Rebuild it after any change to the OCR:

    python3 scripts/report_pages.py --rebuild
"""

import argparse
import glob
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import pdf_tables as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The sixteen annual town reports moved out of town-budget/ on 5 September 2026.
# Every script here globs '*annual-town-report*.pdf' under this path, and a glob
# that matches nothing raises nothing -- so pointing at the folder they left made
# each of these a silent no-op rather than an error.
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')

HEADER = re.compile(r'^===PAGE (\d+)=== \(([^,]+), (\d+) lines\)')


def edition_of(name):
    fy = re.search(r'fy-?(\d{4})', name).group(1)
    return f'FY{fy}' + ('-addendum' if 'addendum' in name else '')


def build(pdf, boxes_dir, out_dir):
    """Every page as lines, choosing the rendering that keeps its COLUMNS.

    `instrument()` picks whichever extraction mode recovers the most figures, which is
    right for reading a page and wrong for reading a table. FY2014 page 29 is the case that
    settled it: the text layer yields 83 money tokens and renders the row as

        Regional Assessor Fund $30,907.25 $30,907.25

    -- single spaces, column positions gone, so the ruler finds one gutter and the table
    cannot be cut. The OCR of that same page, which has a perfectly good text layer, keeps
    the columns and rules cleanly into five.

    So a page whose text layer will not rule into columns is taken from OCR instead, where
    OCR exists. A page of prose is unaffected, because prose has no columns to lose and the
    text layer is the more faithful reading of the words.
    """
    import pypdf
    doc = os.path.basename(pdf)
    reader = pypdf.PdfReader(pdf)

    ocr = {}
    tsv = os.path.join(boxes_dir, doc.replace('.pdf', '.tsv'))
    if os.path.exists(tsv):
        for b in T.read_boxes(tsv):
            ocr.setdefault(b['page'], []).append(b)

    pages = {}
    for i, pg in enumerate(reader.pages):
        page = i + 1
        try:
            mode, _ = T.instrument(pg)
        except Exception:
            mode = None
        lines = T.page_lines(pg, mode) if mode else []

        if mode:
            pages[page] = (mode, lines)
        elif page in ocr:
            pages[page] = ('ocr', T.layout_from_boxes(ocr[page]))

    # TWO renderings are written, and the caller chooses.
    #
    # An earlier version picked one per page: where the text layer would not rule into
    # columns it substituted OCR. That fixed the special revenue schedules, whose text
    # layer collapses `Regional Assessor Fund $30,907.25 $30,907.25` to single spaces --
    # and broke the receipts pages, whose three-column newspaper layout plain mode reads
    # correctly and which legitimately have no gutters, because their columns are spaced by
    # kerning rather than by position. Five reconciled years became zero.
    #
    # There is no single right rendering of a page, only a right one for the question being
    # asked of it. So both are kept: `.txt` is the text layer where there is one, and
    # `.ocr.txt` is the OCR geometry for every page that has it. A ruler-based extractor
    # reads the second; a pattern-based one reads the first.
    ocr_out = os.path.join(out_dir, edition_of(doc) + '.ocr.txt')
    with open(ocr_out, 'w') as fh:
        fh.write(f'# {doc}\n# OCR geometry, {len(ocr)} pages\n\n')
        for p in sorted(ocr):
            keep = [l.rstrip() for l in T.layout_from_boxes(ocr[p]) if l.strip()]
            fh.write(f'===PAGE {p}=== (ocr, {len(keep)} lines)\n')
            for i, l in enumerate(keep, 1):
                fh.write(f'{i:4d}| {l}\n')
            fh.write('\n')

    out = os.path.join(out_dir, edition_of(doc) + '.txt')
    with open(out, 'w') as fh:
        fh.write(f'# {doc}\n# {len(reader.pages)} pages, {len(pages)} readable\n\n')
        for p in sorted(pages):
            mode, lines = pages[p]
            keep = [l.rstrip() for l in lines if l.strip()]
            fh.write(f'===PAGE {p}=== ({mode}, {len(keep)} lines)\n')
            for i, l in enumerate(keep, 1):
                fh.write(f'{i:4d}| {l}\n')
            fh.write('\n')
    return len(reader.pages), len(pages), os.path.getsize(out)


def load(edition, ocr=False):
    """{page number: [lines]} for one report, from the cache. Cheap.

    `ocr=True` returns the OCR geometry rendering, which preserves column POSITION and is
    what a ruler-based extractor needs. The default returns the text layer, which is the
    more faithful reading of the words and what a pattern-based extractor needs.
    """
    path = os.path.join(PAGES, edition + ('.ocr.txt' if ocr else '.txt'))
    if not os.path.exists(path):
        return {}
    pages, cur, num = {}, [], None
    with open(path) as fh:
        for line in fh:
            m = HEADER.match(line)
            if m:
                if num is not None:
                    pages[num] = cur
                num, cur = int(m.group(1)), []
            elif num is not None and line.strip():
                cur.append(re.sub(r'^\s*\d+\|\s?', '', line.rstrip('\n')))
    if num is not None:
        pages[num] = cur
    return pages


def modes(edition):
    """{page number: instrument} -- which reader produced each page."""
    path = os.path.join(PAGES, edition + '.txt')
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for line in fh:
            m = HEADER.match(line)
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


def editions():
    return sorted(os.path.basename(p)[:-4]
                  for p in glob.glob(os.path.join(PAGES, '*.txt'))
                  if not p.endswith('.ocr.txt'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--boxes', default=OCR)
    ap.add_argument('--out', default=PAGES)
    args = ap.parse_args()
    if not args.rebuild:
        print(__doc__)
        return
    os.makedirs(args.out, exist_ok=True)
    pdfs = sorted(glob.glob(os.path.join(DOCS, '*annual-town-report*.pdf')))
    # A rebuild that finds no PDFs leaves the existing cache in place and says nothing,
    # so every extractor downstream keeps producing byte-identical rows off text that is
    # no longer traceable to a document. Loud is safe here; quiet is not.
    if not pdfs:
        raise SystemExit(f'No annual town reports found in {os.path.relpath(DOCS, ROOT)}. '
                         f'The page cache has NOT been rebuilt.')
    total = 0
    for pdf in pdfs:
        n, ok, size = build(pdf, args.boxes, args.out)
        total += ok
        print(f'{edition_of(os.path.basename(pdf)):<18}{n:>5} pages  {ok:>5} readable  '
              f'{size // 1024:>5} KB')
    print(f'\n{total} readable pages cached in {os.path.relpath(args.out, ROOT)}')


if __name__ == '__main__':
    main()
