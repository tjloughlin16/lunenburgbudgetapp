#!/usr/bin/env python3
"""Is the first glyph of a money figure a DOLLAR SIGN or a DIGIT? Read off the page's pixels.

    python3 scripts/witness_dollar_glyphs.py 2009            # write report-tables/2009/glyph-witness.csv
    python3 scripts/witness_dollar_glyphs.py 2009 --check    # fail if it does not reproduce

WHY THIS EXISTS. The 2009 annual report's payroll (pp84-89) is set in a bitmap face whose `$`
looks like an `8`. Textract read 90 of its 574 wage cells with no `$` and a leading `8` or `3`
(`87,342.00` for `$7,342.00`, `8100.00` for `$100.00`). The coverage check graded every one of
them `checked`, because its witness -- the page's LINE output -- is the same engine reading the
same pixels, and it shares the misreading. A check with no power to fail is not a check
(CLAUDE.md rule 13). Vision OCR is no better on this face: the same cell came back
`$7,342.00`, `87,818.00` and `87,319.00` at three renderings.

SO THE WITNESS IS THE GLYPH ITSELF, compared with the page's own glyphs. On these pages the
same face prints hundreds of `$` signs Textract DID read, and hundreds of real `8`s and `3`s.
Each suspect cell's first glyph is cut out at the face's own advance width and correlated with:

  - the first glyph of every line Textract read beginning `$`      (what a `$` looks like here)
  - the second glyph of every `$8...` / `$3...` / `$5...` line     (what that digit looks like here)

and called `$` or `digit` only when it matches one by a clear margin; otherwise `undecided`,
which the reader keeps OUT of `checked`. The same comparison is run on the KNOWN digits as a
negative control, and the run fails if any real digit is called a `$` -- so this witness has
the power to fail, which the line output never had.

WHICH CELLS. On a WAGE page (a map row of family `gross-wages`), a whole-line money figure with
no `$` whose first character is a glyph Textract confuses with `$` (CONFUSABLE), where most of
the page's money lines DO print `$`. A page that prints no `$` at all (2005 p100, half of
2008's payroll) is not suspect: there the digit is simply the first digit. Wage pages only,
because a wage list prints NO TOTAL: every other money table here states a total its rows
must foot to, and an inflated leading digit breaks that total, so those tables already have a
check with the power to fail. A wage list had none.

AND THE WIDTH MUST AGREE. A `$` glyph at the front of the cell can be a misread FIRST
CHARACTER (`87,342.00` is really `$7,342.00`) or a `$` Textract DROPPED (`3,100.53` is really
`$3,100.53`). The two differ by one glyph's advance, so the cell's measured width is compared
with both; a reading is taken only when the width agrees with it, and only when it is a
well-formed money figure.

Reads the PDF with pypdfium2, locally. No network, no Textract.
"""
from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = os.path.join(ROOT, 'sources', 'data', 'report-tables')
LINES = os.path.join(ROOT, 'build', 'textract', 'out', '{stem}.lines.tsv')
MONEY = re.compile(r'^\S?\d[\d,]*\.\d\d$')
CONFUSABLE = '835'
SCALE = 8                 # render scale: the face's stroke is ~2 px at 4, ~4 at 8
MIN_SCORE = 0.6           # a match below this is not a match to anything
MARGIN = 0.25             # ...and must beat the other reading by this much
FIELDS = ['page', 'text', 'reading', 'decision', 'score_dollar', 'score_digit', 'templates']


WELLFORMED = re.compile(r'^\$(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2}$')
MIN_TEMPLATES = 5         # a digit compared with fewer of its own kind decides nothing


def suspects(lines, wage_pages):
    """{page: [line dicts]} -- the cells this witness must decide, by the rule above."""
    by = collections.defaultdict(list)
    for r in lines:
        if int(r['page']) in wage_pages:
            by[int(r['page'])].append(r)
    out = {}
    for p, ls in by.items():
        money = [l for l in ls if MONEY.match(l['text'].replace(' ', ''))]
        dollar = [l for l in money if l['text'].replace(' ', '').startswith('$')]
        sus = [l for l in money if not l['text'].replace(' ', '').startswith('$')
               and l['text'].replace(' ', '')[0] in CONFUSABLE]
        if sus and len(dollar) * 2 >= len(money):
            out[p] = ls
    return out


def crop(img, r):
    H, W = img.shape
    l, t, w, h = (float(r[k]) for k in ('left', 'top', 'width', 'height'))
    a = img[max(0, int((t - .006) * H)):int((t + h + .006) * H), max(0, int((l - .006) * W)):int((l + w + .006) * W)]
    ys, xs = np.where(a.any(1))[0], np.where(a.any(0))[0]
    return a[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1] if len(xs) else None


def patch(a, i, adv):
    from PIL import Image
    x = int(round(i * adv))
    q = a[:, x:x + int(adv)]
    v = np.array(Image.fromarray((q * 255).astype('uint8')).resize((16, 24)), dtype=float)
    v -= v.mean()
    n = np.linalg.norm(v)
    return v / n if n else v


def score(v, templates):
    """The mean of the five best correlations: one near-duplicate cannot carry a decision."""
    s = sorted(float((v * u).sum()) for u in templates)
    return float(np.mean(s[-5:])) if s else 0.0


def decide(sd, sx):
    if sd >= MIN_SCORE and sd - sx >= MARGIN:
        return '$'
    if sx >= MIN_SCORE and sx - sd >= MARGIN:
        return 'digit'
    return 'undecided'


def build(edition):
    import pypdfium2
    d = os.path.join(FOLDERS, edition)
    ed = json.load(open(os.path.join(d, 'edition.json'), encoding='utf-8'))
    with open(LINES.format(stem=ed['stem']), newline='') as fh:
        lines = list(csv.DictReader(fh, delimiter='\t'))
    with open(os.path.join(d, 'map.csv'), newline='', encoding='utf-8') as fh:
        wage_pages = {int(m['page']) for m in csv.DictReader(fh) if m['family'] == 'gross-wages'}
    pages = suspects(lines, wage_pages)
    if not pages:
        return [], 'no wage page has a suspect cell'
    pdf = pypdfium2.PdfDocument(os.path.join(ROOT, ed['pdf']))
    items = []                                     # (page, text, glyph array)
    for p in sorted(pages):
        img = np.array(pdf[p - 1].render(scale=SCALE).to_pil().convert('L')) < 128
        for r in pages[p]:
            t = r['text'].replace(' ', '')
            if MONEY.match(t):
                a = crop(img, r)
                if a is not None and a.shape[1] > 4:
                    items.append((p, t, a))
    # THE FACE'S ADVANCE WIDTH, fitted on the lines Textract read with a `$`:
    # width = advance x (digits + the `$`) + a narrower width x (commas and points)
    X = [[sum(c.isdigit() for c in t) + 1, sum(c in ',.' for c in t)] for _, t, _ in items if t[0] == '$']
    Y = [a.shape[1] for _, t, a in items if t[0] == '$']
    adv, pw = (float(x) for x in np.linalg.lstsq(np.array(X, float), np.array(Y, float), rcond=None)[0])

    def width(t):
        return adv * sum(c.isdigit() or c == '$' for c in t) + pw * sum(c in ',.' for c in t)
    T_dollar = [patch(a, 0, adv) for _, t, a in items if t[0] == '$']
    T_digit = {c: [patch(a, 1, adv) for _, t, a in items if t.startswith('$' + c)] for c in CONFUSABLE}
    # THE NEGATIVE CONTROL: every known digit, against the $ templates and its own (less itself)
    control = collections.Counter()
    for c in CONFUSABLE:
        for j, v in enumerate(T_digit[c]):
            own = T_digit[c][:j] + T_digit[c][j + 1:]
            control[decide(score(v, T_dollar), score(v, own))] += 1
    if control['$']:
        raise SystemExit('NEGATIVE CONTROL FAILED: %d known digit(s) read as a dollar sign -- '
                         'this witness cannot be trusted on this edition' % control['$'])
    out = []
    for p, t, a in items:
        if t[0] == '$' or t[0] not in CONFUSABLE:
            continue
        v = patch(a, 0, adv)
        sd, sx = score(v, T_dollar), score(v, T_digit[t[0]])
        dec = decide(sd, sx) if len(T_digit[t[0]]) >= MIN_TEMPLATES else 'undecided'
        # which reading the measured width agrees with: the first character IS the `$`, or a
        # `$` stands in front of everything Textract read
        replaced, prefixed = width('$' + t[1:]), width('$' + t)
        w = a.shape[1]
        if dec == '$':
            if abs(w - replaced) < abs(w - prefixed) and WELLFORMED.match('$' + t[1:]):
                reading = '$' + t[1:]
            elif abs(w - prefixed) < abs(w - replaced):
                reading = '$' + t
            else:
                dec, reading = 'undecided', ''
        else:
            reading = t if dec == 'digit' else ''
        out.append({'page': p, 'text': t, 'reading': reading,
                    'decision': dec, 'score_dollar': '%.3f' % sd, 'score_digit': '%.3f' % sx,
                    'templates': '%d $, %d %s' % (len(T_dollar), len(T_digit[t[0]]), t[0])})
    note = ('pages %s; advance %.1f px at scale %d; negative control: %d known digits, %d read as digit, '
            '%d undecided, 0 as $' % (','.join(map(str, sorted(pages))), adv, SCALE,
                                      sum(control.values()), control['digit'], control['undecided']))
    return out, note


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('edition')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    rows, note = build(a.edition)
    path = os.path.join(FOLDERS, a.edition, 'glyph-witness.csv')
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    text = buf.getvalue() if rows else ''
    cur = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
    if a.check:
        if cur != text:
            print('STALE: %s' % os.path.relpath(path, ROOT), file=sys.stderr)
            return 1
        print('ok -- %s reproduces (%s)' % (os.path.relpath(path, ROOT), note))
        return 0
    if text != cur:
        if text:
            with open(path + '.tmp', 'w', encoding='utf-8', newline='') as fh:
                fh.write(text)
            os.replace(path + '.tmp', path)
        elif os.path.exists(path):
            os.remove(path)
    print('%s: %s' % (a.edition, note))
    print('  decisions: %s' % dict(collections.Counter(r['decision'] for r in rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
