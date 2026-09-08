#!/usr/bin/env python3
"""How much of the meeting archive can actually be SEARCHED, per board, per year.

    python3 scripts/build_minutes_searchable.py           # write the dataset
    python3 scripts/build_minutes_searchable.py --check   # fail if it has gone stale
    python3 scripts/build_minutes_searchable.py --report  # print the summary, write nothing

WHY THIS EXISTS

`build_minutes_coverage.py` answers *did the town post minutes for this meeting*.
This answers the question one layer further in: **of the documents the town DID post
and we DID fetch and DID extract, how many contain any words a grep could match.**

Those are not the same number, and for a long time nothing distinguished them.
`search_minutes.py` counted a document as searched when a `.txt` file existed beside it.
A `.txt` file exists for every PDF the extractor opened, including the ones whose every
page is a photograph of a page. The extractor writes `===PAGE 1===` and nothing else, the
grep matches nothing, and the coverage line reports the document as searched.

That defeats the one thing the coverage line is for. Rule 15a tells everyone working here
to search the meeting archive before concluding a thing was never discussed; a silent grep
over an image scan reads exactly like *nobody said it*.

THE THRESHOLD, AND WHY IT IS ZERO

The obvious way to write this is a character threshold -- "under 40 characters is not a
document" -- and a threshold picked by eye is a number typed into prose wearing a
constant's clothing. So it was calibrated against a signal that does not depend on the
extractor at all: **whether the PDF carries a `/Font` resource**, which is the mechanical
question of whether the file has a text layer, and whether it carries a raster image.

Measured across the whole archive, the two agree at zero and nowhere else. Do not take
that on this docstring's word -- `--calibrate` recomputes it and prints the cross-tabulation
that justifies the cut, band by band, so the threshold can be rechecked rather than
inherited:

    python3 scripts/build_minutes_searchable.py --calibrate

What it shows: every document whose extracted body is empty has, almost without exception,
no `/Font` anywhere in its page tree -- there is no text in the file to find -- and every
band above zero is essentially all fonts. There is no second break to justify a higher cut.
Documents in the 1-40 character band are NOT scans: they are one-line AgendaCenter stubs
that DO carry a text layer (`Planning Board Meeting1.`), where the substance is in an
attachment the town posted separately. That is a different gap with a different remedy, and
folding it into this one would misattribute several hundred documents to OCR.

So: **a document is searchable if its extracted text holds one non-whitespace character
after the `===PAGE n===` markers are stripped.** Not a judgement, and it is checkable.

WHY EACH UNSEARCHABLE DOCUMENT IS DIAGNOSED

"Cannot be searched" is a measurement. "It is a scan" is an explanation, and rule 7 says
those are different kinds of claim. So each one is classified from the file's own
structure rather than assumed:

  ``image scan``       a raster image in the page resources and no text layer -- OCR recovers it
  ``vector outlines``  no font and no image; the page draws the text as filled paths.
                       Unsearchable in the same way and NOT fixed by the same tool: it has
                       to be rasterised before any OCR can see it.
  ``blank``            the page draws nothing. There is no text to recover, here or ever.
  ``extract failed``   the file HAS a text layer and our extractor got nothing out of it.
                       Ours to fix, not the town's.
  ``unreadable``       the PDF will not parse at all.
  ``not fetched``      the town lists the document; we hold no file for it.

Only the first two are OCR's to fix, which is the distinction the OCR item in
notes/QUEUE.md needs and could not previously make.
"""
import argparse
import collections
import csv
import logging
import os
import re
import sys
import warnings

# pypdf narrates every malformed cross-reference table it repairs. This archive is full
# of them and none of it is a finding; the diagnoses below are the finding.
warnings.filterwarnings('ignore')
logging.getLogger('pypdf').setLevel(logging.CRITICAL)
logging.getLogger('pypdf._reader').setLevel(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, 'sources', 'meetings')
TEXT = os.path.join(MIN, 'text')
INDEX = os.path.join(MIN, 'index.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'minutes-searchable.csv')

PAGE_MARKER = re.compile(r'^===PAGE \d+===$', re.M)

FIELDS = ['board', 'board_slug', 'year', 'listed', 'held', 'with_text_file',
          'searchable', 'unsearchable', 'image_scan', 'vector_outlines', 'blank',
          'extract_failed', 'unreadable', 'not_fetched']

# The diagnosis categories, in the order they are tried. Order matters: a file that has a
# text layer AND an image is our extractor's failure, not a scan.
DIAGNOSES = ['extract_failed', 'image_scan', 'vector_outlines', 'blank', 'unreadable']


def searchable_text(path):
    """The body a grep can match: the extract, with our own page markers removed.

    The markers are ours. Counting them as text is the whole defect this file exists for.
    """
    body = open(path, encoding='utf-8', errors='replace').read()
    return PAGE_MARKER.sub('', body).strip()


def _walk_resources(res, seen, acc, depth=0):
    """Does this resource tree reach a font, or a raster image?

    Form XObjects nest, and the archive contains files whose only image sits two levels
    down inside one. A non-recursive check reported those as neither text nor picture,
    which is a category that would have needed explaining and does not exist.
    """
    if depth > 6 or res is None:
        return
    try:
        res = res.get_object()
    except Exception:
        return
    if not hasattr(res, 'get'):
        return
    if res.get('/Font'):
        acc['font'] = True
    xobjects = res.get('/XObject')
    if not xobjects:
        return
    try:
        xobjects = xobjects.get_object()
    except Exception:
        return
    for key in list(xobjects.keys()):
        try:
            obj = xobjects[key].get_object()
        except Exception:
            continue
        subtype = obj.get('/Subtype')
        if subtype == '/Image':
            acc['image'] = True
        elif subtype == '/Form':
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            _walk_resources(obj.get('/Resources'), seen, acc, depth + 1)


def diagnose(src):
    """Why does this file yield no text? Read off its structure, never assumed."""
    from pypdf import PdfReader
    if not src.lower().endswith('.pdf'):
        # A Word or Excel file that extracted to nothing extracted to nothing. There is no
        # text layer to interrogate and no scan to OCR.
        return 'extract_failed'
    try:
        reader = PdfReader(src)
        pages = list(reader.pages)
    except Exception:
        return 'unreadable'

    acc = {'font': False, 'image': False}
    for page in pages:
        try:
            _walk_resources(page.get_inherited('/Resources'), set(), acc)
        except Exception:
            pass
    if acc['font']:
        return 'extract_failed'
    if acc['image']:
        return 'image_scan'

    # No text and no picture. Either the page draws the words as vector paths -- text
    # converted to outlines, which extraction cannot see and OCR cannot see either until
    # somebody rasterises it -- or it draws nothing at all.
    drawn = 0
    for page in pages:
        try:
            contents = page.get_contents()
            data = contents.get_data() if contents is not None else b''
        except Exception:
            data = b''
        drawn += len(re.findall(rb'(?<![A-Za-z])[ml](?![A-Za-z])', data))
    return 'vector_outlines' if drawn else 'blank'


def measure(diagnose_unsearchable=True):
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8', errors='replace')))
    if not rows:
        raise SystemExit('sources/meetings/index.csv parsed to zero rows. Refusing to '
                         'write: an archive with no meetings in it is a read failure, '
                         'not a town that holds none.')

    slug_of = {}
    per = collections.defaultdict(lambda: collections.Counter())
    joined = 0

    for r in rows:
        path = (r.get('path') or '').strip()
        stem = os.path.splitext(path)[0] if path else ''
        slug = stem.split('/')[0] if stem else ''
        if slug:
            slug_of.setdefault(r['board'], slug)
        year = (r.get('date') or '')[:4]
        if not year.isdigit():
            continue
        key = (r['board'], int(year))
        cell = per[key]
        cell['listed'] += 1

        src = os.path.join(MIN, path) if path else ''
        if not src or not os.path.exists(src):
            cell['not_fetched'] += 1
            continue
        cell['held'] += 1

        txt = os.path.join(TEXT, stem + '.txt')
        if not os.path.exists(txt):
            # Held, but the extractor never produced a file. Diagnose it the same way.
            cell['unsearchable'] += 1
            cell[diagnose(src) if diagnose_unsearchable else 'image_scan'] += 1
            continue

        joined += 1
        cell['with_text_file'] += 1
        if searchable_text(txt):
            cell['searchable'] += 1
        else:
            cell['unsearchable'] += 1
            cell[diagnose(src) if diagnose_unsearchable else 'image_scan'] += 1

    if not joined:
        raise SystemExit('not one indexed document joined to an extracted text file. '
                         'That is a broken join, and a broken join looks exactly like an '
                         'archive nobody has extracted -- refusing to write.')

    out = []
    for (board, year), cell in sorted(per.items()):
        row = dict(board=board, board_slug=slug_of.get(board, ''), year=year)
        for f in FIELDS[3:]:
            row[f] = cell[f]
        out.append(row)

    # Fail closed on the identities this dataset states about itself. A count that does
    # not foot is a count nobody should quote.
    tot = {f: sum(r[f] for r in out) for f in FIELDS[3:]}
    if tot['listed'] != tot['held'] + tot['not_fetched']:
        raise SystemExit('listed != held + not_fetched; refusing to write.')
    if tot['held'] != tot['searchable'] + tot['unsearchable']:
        raise SystemExit('held != searchable + unsearchable; refusing to write.')
    if diagnose_unsearchable and tot['unsearchable'] != sum(tot[d] for d in DIAGNOSES):
        raise SystemExit('the unsearchable documents do not sum to their diagnoses; '
                         'refusing to write.')
    if not tot['searchable']:
        raise SystemExit('zero searchable documents. Refusing to write: that is an '
                         'extraction failure, not an unreadable town.')
    return out, tot


def write(rows):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def summarise(rows, tot):
    pct = lambda n, d: (100.0 * n / d) if d else 0.0
    print('%d board-years, %d boards' % (len(rows), len({r['board'] for r in rows})))
    print('  listed by the town      %6d' % tot['listed'])
    print('  held on disk            %6d  (%d never fetched)'
          % (tot['held'], tot['not_fetched']))
    print('  with a text file        %6d' % tot['with_text_file'])
    print('  SEARCHABLE              %6d  (%.1f%% of held)'
          % (tot['searchable'], pct(tot['searchable'], tot['held'])))
    print('  unsearchable            %6d  (%.1f%% of held)'
          % (tot['unsearchable'], pct(tot['unsearchable'], tot['held'])))
    for d in DIAGNOSES:
        print('      %-18s %6d' % (d.replace('_', ' '), tot[d]))
    worst = sorted(rows, key=lambda r: -r['unsearchable'])
    by_board = collections.Counter()
    held = collections.Counter()
    for r in rows:
        by_board[r['board_slug'] or r['board']] += r['unsearchable']
        held[r['board_slug'] or r['board']] += r['held']
    print('\n  worst affected boards (unsearchable / held):')
    for slug, n in by_board.most_common(8):
        print('      %-42s %5d / %5d  (%.0f%%)' % (slug, n, held[slug], pct(n, held[slug])))
    del worst


def calibrate():
    """Recompute the evidence for putting the threshold at zero. Writes nothing.

    For each band of extracted characters-per-page, how many of those documents carry a
    `/Font` resource. If the split is real, the zero band is almost all fontless and every
    band above it is almost all fonted -- and if it ever stops being real, this says so
    instead of the threshold quietly becoming a number somebody once chose.
    """
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8', errors='replace')))
    bands = [(0, 0), (1, 20), (21, 40), (41, 100), (101, 200), (201, 500),
             (501, 10 ** 9)]
    # documents, PDFs among them, with /Font, with a raster image. PDFs are counted
    # separately because a .docx has no /Font to lack, and lumping the 93 Word and Excel
    # files in with the scans would put 93 documents in a column that means "no text
    # layer" about files that have no page tree at all.
    tally = {b: [0, 0, 0, 0] for b in bands}
    for r in rows:
        path = (r.get('path') or '').strip()
        stem = os.path.splitext(path)[0] if path else ''
        src = os.path.join(MIN, path) if path else ''
        txt = os.path.join(TEXT, stem + '.txt') if stem else ''
        if not (txt and os.path.exists(txt) and os.path.exists(src)):
            continue
        raw = open(txt, encoding='utf-8', errors='replace').read()
        pages = len(PAGE_MARKER.findall(raw)) or 1
        chars = len(re.sub(r'\s+', '', PAGE_MARKER.sub('', raw)))
        per = chars / pages
        band = next(b for b in bands if b[0] <= per <= b[1])
        tally[band][0] += 1
        if not src.lower().endswith('.pdf'):
            continue
        try:
            from pypdf import PdfReader
            acc = {'font': False, 'image': False}
            for page in PdfReader(src).pages:
                _walk_resources(page.get_inherited('/Resources'), set(), acc)
        except Exception:
            continue
        tally[band][1] += 1
        tally[band][2] += acc['font']
        tally[band][3] += acc['image']

    print('extracted characters per page, against what the PDF itself contains\n')
    print('%18s %8s %8s %8s %8s %8s'
          % ('band', 'docs', 'PDFs', '/Font', 'no /Font', 'image'))
    for b in bands:
        n, pdfs, font, image = tally[b]
        hi = b[1] if b[1] < 10 ** 8 else None
        label = '%d' % b[0] if b[0] == b[1] else ('%d-%s' % (b[0], hi if hi else '...'))
        print('%18s %8d %8d %8d %8d %8d' % (label, n, pdfs, font, pdfs - font, image))
    zero = tally[(0, 0)]
    above = [sum(tally[b][i] for b in bands if b != (0, 0)) for i in range(4)]
    print('\nThe threshold sits where the two signals agree, counting PDFs only.')
    print('  empty extract, no text layer either: %d of %d (%.2f%%)'
          % (zero[1] - zero[2], zero[1], 100.0 * (zero[1] - zero[2]) / (zero[1] or 1)))
    print('  non-empty extract, HAS a text layer: %d of %d (%.2f%%)'
          % (above[2], above[1], 100.0 * above[2] / (above[1] or 1)))
    print('\nIf those two percentages ever stop being near 100, the cut is no longer')
    print('supported by anything but habit, and this script should be re-argued.')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--report', action='store_true', help='print, write nothing')
    ap.add_argument('--calibrate', action='store_true',
                    help='recompute the evidence for the zero threshold; write nothing')
    a = ap.parse_args()

    if a.calibrate:
        return calibrate()

    rows, tot = measure()

    if a.check:
        if not os.path.exists(OUT):
            print('STALE — %s has never been written' % os.path.relpath(OUT, ROOT))
            return 1
        have = list(csv.DictReader(open(OUT, encoding='utf-8')))
        made = [{k: str(v) for k, v in r.items()} for r in rows]
        if have != made:
            print('STALE — sources/data/minutes-searchable.csv no longer reproduces from '
                  'sources/meetings/. Run scripts/build_minutes_searchable.py')
            return 1
        print('ok — %d board-years reproduce; %d of %d held documents are searchable'
              % (len(have), tot['searchable'], tot['held']))
        return 0

    if a.report:
        summarise(rows, tot)
        return 0

    write(rows)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    summarise(rows, tot)
    return 0


if __name__ == '__main__':
    sys.exit(main())
