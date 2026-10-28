#!/usr/bin/env python3
"""page_integrity.py against the 2000 report as scanned, and against copies of it doctored the
ways a paper copy goes wrong: a page lost, two pages swapped, a page copied twice.

The real report is the answer key, checked by hand on 27 October 2026: 130 of 130 numbered
pages in order at printed = PDF - 3, and printed 132 missing. Each doctored copy must be
caught by the check built for it -- a check that has never failed has not been shown to work.

Needs the Textract output of the 2000 report (build/textract/out, gitignored); without it the
test says so and fails, rather than passing on nothing.

    python3 scripts/test_page_integrity.py
"""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import page_integrity as P  # noqa: E402

SOURCE = P.OUT / '2000 Annual Town Report.lines.tsv'
SANDBOX = ROOT / 'build' / 'test-page-integrity' / str(os.getpid())
TOTAL = 134
fails = []


def expect(ok, what):
    print(('  ok    ' if ok else '  FAIL  ') + what)
    if not ok:
        fails.append(what)


def load():
    with open(SOURCE, newline='') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    pages = {}
    for r in rows:
        pages.setdefault(int(r['page']), []).append(r)
    return pages


def write(name, order, pages, strip_folios=()):
    """A doctored copy: `order` lists source PDF pages in their new order."""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    path = SANDBOX / f'{name}.lines.tsv'
    with open(path, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['page', 'line', 'confidence', 'left', 'top', 'width', 'height', 'text'])
        for new, old in enumerate(order, 1):
            for r in pages.get(old, []):
                if old in strip_folios and float(r['top']) > 1 - P.BAND and r['text'].isdigit():
                    continue
                w.writerow([new] + [r[k] for k in ('line', 'confidence', 'left', 'top', 'width',
                                                   'height', 'text')])
    return P.check(path, sent=list(range(1, len(order) + 1)), total=len(order))


def found(rep, kind, check, text=''):
    return [f for f in rep.findings if f.kind == kind and f.check == check and text in f.detail]


def issues(rep):
    return sorted(f.check for f in rep.findings if f.kind == 'issue')


def main():
    if not SOURCE.exists():
        sys.exit(f'FAIL: no Textract output for the 2000 report at {SOURCE}; nothing was tested')
    pages = load()
    every = list(range(1, TOTAL + 1))

    print('the 2000 report, as scanned')
    rep = write('real', every, pages)
    expect(rep.offset == -3, f'printed = PDF - 3 (got {rep.offset})')
    expect(len(rep.folios) == 130 and sorted(rep.folios.values()) == list(range(2, 132)),
           f'130 numbered pages, printed 2-131 (got {len(rep.folios)})')
    expect(132 not in rep.folios.values(), 'the vote count of 132 mid-page at PDF 102 and 106 is no folio')
    expect(issues(rep) == ['index_page_absent', 'pages_after_last'], f'only page 132 is an issue: {issues(rep)}')
    expect(bool(found(rep, 'issue', 'index_page_absent', 'printed 132')), 'printed 132 named as absent')
    expect(not [f for f in rep.findings if f.kind == 'check'], 'nothing to check on a scan in order')

    print('a page lost: PDF 60 (printed 57) removed')
    rep = write('lost', [p for p in every if p != 60], pages)
    expect(bool(found(rep, 'issue', 'folio_gap', 'printed 57 not in the file')), 'printed 57 reported missing')

    print('two pages swapped: PDF 50 and PDF 70')
    order = every[:]
    order[49], order[69] = 70, 50
    rep = write('swapped', order, pages)
    expect(sorted(p for f in found(rep, 'issue', 'out_of_place') for p in f.pages) == [50, 70],
           'both pages reported out of place')
    expect('folio_gap' not in issues(rep), 'a swap is not reported as a loss')

    print('a page copied twice: PDF 40 again after itself')
    rep = write('doubled', every[:40] + [40] + every[40:], pages)
    expect(bool(found(rep, 'issue', 'duplicate_folio', 'printed 37 is on PDF 40, 41')), 'printed 37 reported twice')

    print('two wages pages swapped, their page numbers unreadable: PDF 129 and PDF 132')
    order = every[:]
    order[128], order[131] = 132, 129
    rep = write('wages', order, pages, strip_folios={129, 132})
    expect(not found(rep, 'issue', 'out_of_place'), 'the folios are gone, so the folio check cannot see it')
    expect(bool(found(rep, 'check', 'run_break', 'at "Nelson"')),
           'the alphabetical list breaking at "Nelson" catches it anyway')

    print('a town meeting page lost: PDF 109 (ARTICLES 14-18) removed')
    rep = write('articles', [p for p in every if p != 109], pages)
    expect(bool(found(rep, 'check', 'article_gap', 'ARTICLES 14-18')), 'ARTICLES 14-18 reported unread')

    print('the wages run is cut short: the file stops at PDF 131')
    rep = write('short', every[:131], pages)
    expect(bool(found(rep, 'issue', 'index_page_absent', 'printed 129, 130, 131, 132')),
           'the index names the pages the file no longer has')

    print('every case holds' if not fails else f'{len(fails)} FAILED')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
