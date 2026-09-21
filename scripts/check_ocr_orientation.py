#!/usr/bin/env python3
"""Is an OCR run actually upright, page by page — checked before anything is built on it.

Run this on each document as it finishes, not on all sixteen at the end. The reason is
specific rather than general: the previous OCR run completed cleanly across 2,751 pages and
about 700 of them were read sideways, which nothing in the output revealed. The text was
present and correctly spelled; only the geometry was wrong, so every downstream table
collapsed into one line of labels followed by one line of values. A batch that finishes is
not a batch that worked.

The test is the same one the recogniser is calibrated on, applied afterwards as an
independent check: **horizontal text produces boxes wider than they are tall.** A page where
most boxes are taller than wide was read at ninety degrees.

    python3 scripts/check_ocr_orientation.py <dir> [<dir to compare against>]

Exits non-zero if any document has sideways pages, so it can gate a pipeline.
"""

import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sideways(path, min_boxes=5, tall_share=0.5):
    """Pages where most recognised boxes are taller than wide, and the page totals."""
    boxes = T.read_boxes(path)
    per = collections.Counter(b['page'] for b in boxes)
    tall = collections.Counter()
    for b in boxes:
        if b['h'] > b['w']:
            tall[b['page']] += 1
    bad = [p for p in per
           if per[p] >= min_boxes and tall[p] > per[p] * tall_share]
    return sorted(bad), len(per), len(boxes)


# ---- 180 degrees, which the box-shape test cannot see ------------------------------
#
# THE SAME FAILURE ONE ROTATION FURTHER. This file was written because ~700 pages were read
# at 90 degrees and nothing in the output revealed it. A page fed in UPSIDE DOWN passes
# that test completely: its boxes are still wider than they are tall, because the line is
# still a line. What changes is the ORDER of the glyphs, so `$0.00` is recognised, with
# confidence, as `00'0$`.
#
# It is not rare and it is not confined to the bad years: 27 pages across all fifteen
# annual reports, and they are disproportionately the dense financial tables -- the trust
# fund pages, the debt schedules. TJ found one of them by hand, page 51 of the FY2023
# report, and asked why the extractor had not: it never could have. No pattern matches
# `00'0$`, so the page reads as containing no money at all.
#
# THE TEST. Reverse each token and apply the glyph swaps a mirrored read produces -- S for
# $, E for 3, Z for 2, B for 8, an apostrophe for a comma. If far more tokens look like
# money BACKWARDS than forwards, the page went in upside down.
MONEY = re.compile(r'^\(?-?[$S]?-?[\d,]{1,15}[.,]\d{2}\)?$')


def _unreversed(t):
    r = t[::-1]
    for a, b in (('S', '$'), ('E', '3'), ('Z', '2'), ('B', '8'), ("'", ',')):
        r = r.replace(a, b)
    return r


def upside_down(path, min_hits=8):
    """Pages whose text reads as money only when reversed."""
    boxes = T.read_boxes(path)
    fwd = collections.Counter()
    rev = collections.Counter()
    for b in boxes:
        t = (b.get('text') or '').strip()
        if not t:
            continue
        if MONEY.match(t):
            fwd[b['page']] += 1
        elif MONEY.match(_unreversed(t)):
            rev[b['page']] += 1
    return sorted(p for p in rev if rev[p] >= min_hits and rev[p] > fwd[p])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    new_dir = sys.argv[1]
    old_dir = sys.argv[2] if len(sys.argv) > 2 else None

    files = sorted(glob.glob(os.path.join(new_dir, '*.tsv')))
    if not files:
        print(f'no TSVs in {new_dir}')
        return 2

    print(f'{"document":<46}{"pages":>6}{"lines":>8}{"sideways":>10}'
          f'{"  was":>7}  verdict')
    failed, upended = [], []
    for f in files:
        bad, pages, lines = sideways(f)
        flipped = upside_down(f)
        was = ''
        if old_dir:
            old = os.path.join(old_dir, os.path.basename(f))
            if os.path.exists(old):
                oldbad, _, _ = sideways(old)
                was = str(len(oldbad))
        verdict = ('OK' if not bad and not flipped
                   else ' '.join(filter(None, [
                       f'FAIL — {len(bad)} sideways' if bad else '',
                       f'FAIL — {len(flipped)} upside down' if flipped else ''])))
        if flipped:
            upended.append((os.path.basename(f), flipped))
        if bad:
            failed.append((os.path.basename(f), bad))
        print(f'{os.path.basename(f)[:44]:<46}{pages:>6}{lines:>8}'
              f'{len(bad):>10}{was:>7}  {verdict}')

    if upended:
        n = sum(len(p) for _, p in upended)
        print(f'\n{n} page(s) across {len(upended)} document(s) were read UPSIDE DOWN. '
              f'Their text is reversed, so every figure on them is invisible to every '
              f'extractor here — re-OCR these pages rotated 180°:')
        for name, pages in upended:
            print(f'  {name}: {" ".join(str(p) for p in pages)}')

    if failed:
        print(f'\n{len(failed)} document(s) still have sideways pages — do NOT build on '
              f'them:')
        for name, bad in failed:
            shown = ' '.join(str(p) for p in bad[:24])
            more = f' … and {len(bad) - 24} more' if len(bad) > 24 else ''
            print(f'  {name}: {shown}{more}')
        return 1
    if upended:
        return 1
    print(f'\nall {len(files)} document(s) upright')
    return 0


if __name__ == '__main__':
    sys.exit(main())
