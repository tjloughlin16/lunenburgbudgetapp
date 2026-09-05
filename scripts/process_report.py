#!/usr/bin/env python3
"""Process ONE annual town report end to end, and say what changed.

Run per document, as soon as its OCR lands -- not once over all sixteen at the end.

The reason is a specific failure rather than a general preference. The previous OCR run
completed cleanly across 2,751 pages and roughly 700 of them had been read sideways; the
text was present and correctly spelled, only the geometry was wrong, and nothing in the
output revealed it. Hours of extraction were built on that before it surfaced. A batch that
finishes is not a batch that worked.

So this reports, for one document:

  * whether its OCR is upright, page by page
  * how many pages carry figures, and how many are readable at all
  * which roster pages the catalogue points at, and how many render usefully
  * whether its receipts table is found and whether it reconciles
  * **the delta against the previous run**, so an improvement is shown rather than assumed

Exits non-zero when the document is not fit to build on.

    python3 scripts/process_report.py FY2019 [--against <old ocr dir>]
"""

import argparse
import collections
import csv
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
DOCS = os.path.join(ROOT, 'sources', 'town-budget', 'docs')
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
CATALOGUE = os.path.join(ROOT, 'sources', 'data', 'annual-report-catalogue.csv')


def pdf_for(fy):
    pat = 'addendum' if fy.endswith('-addendum') else None
    year = re.search(r'(\d{4})', fy).group(1)
    for p in sorted(glob.glob(os.path.join(DOCS, f'*fy-{year}-annual-town-report*.pdf'))):
        if pat and 'addendum' in p:
            return p
        if not pat and 'addendum' not in p:
            return p
    return None


def orientation_report(tsv):
    if not os.path.exists(tsv):
        return None
    boxes = T.read_boxes(tsv)
    per = collections.Counter(b['page'] for b in boxes)
    tall = collections.Counter()
    for b in boxes:
        if b['h'] > b['w']:
            tall[b['page']] += 1
    bad = sorted(p for p in per if per[p] >= 5 and tall[p] > per[p] * 0.5)
    return {'pages': len(per), 'lines': len(boxes), 'sideways': bad}


def read_pages(pdf, tsv):
    """Every page, text layer where there is one and OCR where there is not."""
    reader = pypdf.PdfReader(pdf)
    out, need = {}, []
    for i, pg in enumerate(reader.pages):
        try:
            mode, _ = T.instrument(pg)
        except Exception:
            mode = None
        if mode:
            out[i + 1] = T.page_lines(pg, mode)
        else:
            need.append(i + 1)
    if os.path.exists(tsv) and need:
        by = {}
        for b in T.read_boxes(tsv):
            by.setdefault(b['page'], []).append(b)
        for p in need:
            if p in by:
                out[p] = T.layout_from_boxes(by[p])
    return out, len(reader.pages)


def catalogue_pages(fy, matcher):
    """Pages for one report, from the catalogue.

    The matcher is handed the row, not a blob, because **an exclusion has to apply to what
    a table IS and not to prose describing it.** Matching exclusions against the
    description reported FY2018 as publishing no receipts table: its entry reads "Every
    general-fund revenue account and its FY2018 receipts, grouped under TAXES & EXCISES,
    ... assessments ...", and the word `assessment` in that sentence disqualified the page.

    Identity lives in `name` and `printed_heading`. `what_it_is` is a description and will
    mention half the book.
    """
    pages = set()
    for r in csv.DictReader(open(CATALOGUE)):
        if str(r['edition']) != fy:
            continue
        if not matcher(r):
            continue
        for a, b in re.findall(r'(\d+)\s*[-–]\s*(\d+)', r['pages'] or ''):
            if int(b) >= int(a) and int(b) - int(a) < 30:
                pages.update(range(int(a), int(b) + 1))
        for n in re.findall(r'(?<![\d-])(\d{1,3})(?![\d-])', r['pages'] or ''):
            pages.add(int(n))
    return sorted(pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fy')
    ap.add_argument('--ocr', default=OCR)
    ap.add_argument('--against', help='an earlier OCR directory, to show the delta')
    args = ap.parse_args()

    fy = args.fy if args.fy.startswith('FY') else 'FY' + args.fy
    pdf = pdf_for(fy)
    if not pdf:
        print(f'{fy}: no PDF found')
        return 2
    tsv = os.path.join(args.ocr, os.path.basename(pdf).replace('.pdf', '.tsv'))

    print(f'== {fy}  {os.path.basename(pdf)}')
    problems = []

    now = orientation_report(tsv)
    if now is None:
        print('   OCR: MISSING')
        problems.append('no OCR')
    else:
        was = orientation_report(
            os.path.join(args.against, os.path.basename(tsv))) if args.against else None
        delta = f'  (was {len(was["sideways"])})' if was else ''
        verdict = 'OK' if not now['sideways'] else f'FAIL {len(now["sideways"])} sideways'
        print(f'   OCR: {now["pages"]} pages, {now["lines"]} lines, '
              f'{len(now["sideways"])} sideways{delta}  {verdict}')
        if now['sideways']:
            problems.append(f'{len(now["sideways"])} sideways pages')

    pages, total = read_pages(pdf, tsv)
    figs = sum(1 for p in pages.values() if T.money_tokens(p))
    print(f'   readable: {len(pages)}/{total} pages, {figs} carry figures')
    if len(pages) < total * 0.9:
        problems.append(f'{total - len(pages)} unreadable pages')

    def is_school_roster(r):
        ident = f"{r['name']} {r['printed_heading']}"
        blob = f"{ident} {r['what_it_is']}"
        return (re.search(r'roster|faculty|staff', blob, re.I)
                and re.search(r'school|primary|turkey|middle|high|thes|passios',
                              blob, re.I)
                and not re.search(r'\b(fire|police|dpw)\b', ident, re.I))

    roster = catalogue_pages(fy, is_school_roster)
    # A thin page has two quite different causes and only one is a fault.
    #
    # A page read sideways collapses into a handful of run-together lines and is broken. A
    # page that is genuinely short -- two names spilling over from the roster on the page
    # before, plus a folio -- is the document, not the reader. FY2013 p43 is exactly that:
    # three items, all horizontal, continuing p42. Flagging both the same way makes the
    # gate cry wolf, and a gate that cries wolf gets ignored.
    #
    # They are told apart by orientation and by the neighbour: a broken page is sideways;
    # a spillover is upright and sits next to a dense page.
    sideways_pages = set(now['sideways']) if now else set()
    thin, spill = [], []
    for p in roster:
        if len(pages.get(p, [])) >= 8:
            continue
        neighbour_dense = any(len(pages.get(p + d, [])) >= 20 for d in (-1, 1))
        (spill if (p not in sideways_pages and neighbour_dense) else thin).append(p)
    ok = len(roster) - len(thin) - len(spill)
    print(f'   school rosters: {len(roster)} pages from the catalogue, '
          f'{ok} render usefully'
          + (f', {len(spill)} short continuations {spill}' if spill else '')
          + (f', {len(thin)} BROKEN {thin}' if thin else ''))
    if thin:
        problems.append(f'{len(thin)} unreadable roster pages')

    # Located from the catalogue, and matched loosely against the page.
    #
    # This check previously searched for the exact string `SUMMARY OF RECEIPTS` and
    # reported FY2018 as having no receipts page, minutes after the extractor had
    # reconciled that very page to its printed $40,193,021.76. The page renders the words
    # as `SUMMARY OF RECEIPT S`.
    #
    # A checker that carries the same defect as the thing it checks is not a check. This
    # is the same fix already made in `extract_annual_receipts.py` and
    # `extract_placement_counts.py` -- the third place it was needed, and the second time
    # it was written rather than reused.
    def is_receipts(r):
        ident = f"{r['name']} {r['printed_heading']}"
        return (re.search(r'RECEIPTS', ident, re.I)
                and not re.search(r'SPECIAL REVENUE|GENERAL FUND REVENUES|New Growth|'
                                  r'Assessment|TRUST|CAPITAL|ENTERPRISE|BALANCE SHEET',
                                  ident, re.I))

    listed = catalogue_pages(fy, is_receipts)
    loose_summary = re.compile(
        r'[-\s]*'.join(re.escape(c) for c in 'SUMMARYOFRECEIPTS'), re.I)
    found = [p for p in listed if p in pages]
    checkable = [p for p in found if loose_summary.search('\n'.join(pages[p]))]
    if not listed:
        print('   receipts page: none in the catalogue — this year publishes no '
              'general fund receipts table')
    else:
        print(f'   receipts page: {found or "listed but not readable: " + str(listed)}'
              + (f', summary panel on {checkable}' if checkable
                 else ' — no SUMMARY OF RECEIPTS panel, so it cannot be reconciled'))
        if not found:
            problems.append('receipts page listed but unreadable')

    if problems:
        print(f'   >> NOT fit to build on: {"; ".join(problems)}')
        return 1
    print('   >> ready')
    return 0


if __name__ == '__main__':
    sys.exit(main())
