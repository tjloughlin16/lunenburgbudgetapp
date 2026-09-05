#!/usr/bin/env python3
"""Write every page of every annual town report to text, for reading end to end.

This exists because of what `notes/findings/TOWN-ARCHIVE.md` calls the rule the rest of
that file kept discovering the hard way: **each report is its own document, and no pattern
carries across years.** Fifteen reports, fifteen years, different town managers,
superintendents and principals, and nobody maintaining a format.

Every extractor written so far started by assuming what it would find -- a heading, a
column order, a label spelling -- and each one silently succeeded for the years that
happened to match. So the order is inverted here: read the documents first, write down what
is actually in them, and only then extract, in whatever format each year presents.

One file per report, pages marked `===PAGE n===`, each non-blank line numbered within its
page so anything found can be cited back to a coordinate. The instrument is chosen per page
and named in the page header, because that is part of the finding too.

    python3 scripts/dump_report_pages.py --boxes <dir> --out <dir>
"""

import argparse
import glob
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import pypdf
import pdf_tables as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The sixteen annual town reports moved out of town-budget/ on 5 September 2026.
# Every script here globs '*annual-town-report*.pdf' under this path, and a glob
# that matches nothing raises nothing -- so pointing at the folder they left made
# each of these a silent no-op rather than an error.
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boxes', default=os.path.join(ROOT, 'sources', 'town-budget', 'ocr'))
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    for path in sorted(glob.glob(os.path.join(DOCS, '*annual-town-report*.pdf'))):
        doc = os.path.basename(path)
        fy = re.search(r'fy-?(\d{4})', doc)
        fy = fy.group(1) if fy else '????'

        reader = pypdf.PdfReader(path)
        pages, need_ocr = {}, []
        for i, pg in enumerate(reader.pages):
            try:
                mode, _ = T.instrument(pg)
            except Exception:
                mode = None
            if mode:
                pages[i + 1] = (mode, T.page_lines(pg, mode))
            else:
                need_ocr.append(i + 1)

        if args.boxes and need_ocr:
            tsv = os.path.join(args.boxes, doc.replace('.pdf', '.tsv'))
            if os.path.exists(tsv):
                by = {}
                for b in T.read_boxes(tsv):
                    by.setdefault(b['page'], []).append(b)
                for p in need_ocr:
                    if p in by:
                        pages[p] = ('ocr', T.layout_from_boxes(by[p]))

        out = os.path.join(args.out, f'FY{fy}.txt')
        unread = [p for p in range(1, len(reader.pages) + 1) if p not in pages]
        with open(out, 'w') as fh:
            fh.write(f'# {doc}\n# FY{fy}, {len(reader.pages)} pages, '
                     f'{len(pages)} readable, {len(unread)} unreadable\n')
            if unread:
                fh.write(f'# unreadable pages (no text layer, no OCR): '
                         f'{" ".join(str(u) for u in unread)}\n')
            fh.write('\n')
            for p in sorted(pages):
                mode, lines = pages[p]
                keep = [l.rstrip() for l in lines if l.strip()]
                fh.write(f'===PAGE {p}=== ({mode}, {len(keep)} lines)\n')
                for i, l in enumerate(keep, 1):
                    fh.write(f'{i:4d}| {l}\n')
                fh.write('\n')
        print(f'FY{fy}  {len(reader.pages):>4} pages  {len(pages):>4} readable  '
              f'{os.path.getsize(out) // 1024:>5} KB  -> {os.path.basename(out)}')


if __name__ == '__main__':
    main()
