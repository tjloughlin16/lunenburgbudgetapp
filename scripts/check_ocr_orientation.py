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
    failed = []
    for f in files:
        bad, pages, lines = sideways(f)
        was = ''
        if old_dir:
            old = os.path.join(old_dir, os.path.basename(f))
            if os.path.exists(old):
                oldbad, _, _ = sideways(old)
                was = str(len(oldbad))
        verdict = 'OK' if not bad else f'FAIL — {len(bad)} pages'
        if bad:
            failed.append((os.path.basename(f), bad))
        print(f'{os.path.basename(f)[:44]:<46}{pages:>6}{lines:>8}'
              f'{len(bad):>10}{was:>7}  {verdict}')

    if failed:
        print(f'\n{len(failed)} document(s) still have sideways pages — do NOT build on '
              f'them:')
        for name, bad in failed:
            shown = ' '.join(str(p) for p in bad[:24])
            more = f' … and {len(bad) - 24} more' if len(bad) > 24 else ''
            print(f'  {name}: {shown}{more}')
        return 1
    print(f'\nall {len(files)} document(s) upright')
    return 0


if __name__ == '__main__':
    sys.exit(main())
