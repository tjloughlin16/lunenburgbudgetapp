"""Why did this page refuse? Run every cheap check before concluding anything.

    python3 scripts/diagnose_table.py --fy 2021 --page 39
    python3 scripts/diagnose_table.py --blocked          # every refusal on record

WHY THIS EXISTS. Reading one table family took a full day, and the time did not go on
hard problems -- it went on improvising the same four diagnostics over and over, and on
stopping to report a residual instead of chasing it. TJ: *"you seem to try something and
then stop until i push. that's not going to lead to data the fastest possible way."*

So the ladder from notes/process/INGESTING-A-TABLE-FAMILY.md is a command. It runs the
checks in cost order and prints what each one found, so the next step is read off the
output rather than invented.

WHAT IT DELIBERATELY DOES NOT DO. It does not decide anything and it does not edit. Every
check here answers "what does the page say", and what to do about that is a judgement --
often about whether two names are one fund, or whether a figure may be published on a
page that cannot foot. Those belong to a person.
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import pdf_tables as T  # noqa: E402

OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
BLOCKED = os.path.join(ROOT, 'sources', 'data', 'extraction-blocked.csv')
MONEY = re.compile(r'^\$?\s*-?\(?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\)?$|^\$?\s*-?\(?\d+[.,]\d{2}\)?$')


def ocr_file(fy):
    hits = glob.glob(os.path.join(OCR, '*fy-%d-*annual-town-report.tsv' % fy))
    return hits[0] if hits else None


def money(t):
    t = t.replace('$', '').strip()
    cut = max(t.rfind('.'), t.rfind(','))
    if cut > 0:
        t = t[:cut].replace('.', '').replace(',', '') + '.' + t[cut + 1:]
    try:
        return float(t.strip('()').replace(',', ''))
    except ValueError:
        return None


def pdf_for(fy):
    hits = glob.glob(os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs',
                                  '*fy-%d-*annual-town-report.pdf' % fy))
    return hits[0] if hits else None


def diagnose(fy, page, residual=None):
    f = ocr_file(fy)
    if not f:
        print('  no OCR for FY%d' % fy)
        return
    boxes = [b for b in T.read_boxes(f) if b['page'] == page]
    if not boxes:
        print('  FY%d has no page %d' % (fy, page))
        return
    amts = [b for b in boxes if MONEY.match((b['text'] or '').strip())]
    labs = [b for b in boxes if not MONEY.match((b['text'] or '').strip())
            and len((b['text'] or '').strip()) >= 3
            and re.search(r'[A-Za-z]{3,}', b['text'] or '')]
    print('  boxes %d   amounts %d   labels %d' % (len(boxes), len(amts), len(labs)))

    # 2. does the residual equal exactly one row?
    if residual:
        hit = [b for b in amts
               if money(b['text'].strip()) is not None
               and abs(abs(money(b['text'].strip())) - abs(residual)) < 0.02]
        print('  [2] residual %s -> %s' % (
            format(residual, ',.2f'),
            ('ONE row matches it: %r at x=%.3f' % (hit[0]['text'].strip(), hit[0]['x']))
            if len(hit) == 1 else '%d rows match' % len(hit)))

    # 3. pairing: labels with no amount, amounts with no label
    ys = sorted({round(b['y'], 4) for b in amts})
    gaps = [b - a for a, b in zip(ys, ys[1:]) if b - a > 0.002]
    band = (sorted(gaps)[len(gaps) // 2] / 2) if len(gaps) >= 3 else 0.006
    lonely_lab = [b for b in labs if not any(abs(a['y'] - b['y']) < band for a in amts)]
    lonely_amt = [b for b in amts if not any(abs(l['y'] - b['y']) < band for l in labs)]
    print('  [3] row band measured at %.4f; labels with no amount %d, amounts with no '
          'label %d' % (band, len(lonely_lab), len(lonely_amt)))
    for b in lonely_lab[:4]:
        print('        no amount: %r' % (b['text'] or '').strip()[:52])
    for b in lonely_amt[:4]:
        print('        no label : %r' % (b['text'] or '').strip()[:52])

    # 3b. wrapped labels
    wrapped = [b for b in labs if (b['text'] or '').strip().endswith('-')]
    if wrapped:
        print('  [3b] %d label(s) end in a hyphen and wrap to the next line: %s'
              % (len(wrapped), ', '.join((b['text'] or '').strip()[:28] for b in wrapped[:3])))

    # 5. landscape?
    pdf = pdf_for(fy)
    if pdf:
        print('  [5] render it and LOOK -- this is the decisive one:')
        print('        swift scripts/render_pdf_page.swift %s %d /tmp/p.png'
              % (os.path.relpath(pdf, ROOT), page))

    # 6. homoglyphs
    odd = [b for b in boxes if any(ord(c) > 127 for c in (b['text'] or ''))]
    if odd:
        print('  [6] %d box(es) contain non-ASCII characters -- check for Cyrillic '
              'lookalikes:' % len(odd))
        for b in odd[:3]:
            t = (b['text'] or '').strip()
            print('        %r  %s' % (t[:40], [hex(ord(c)) for c in t if ord(c) > 127][:5]))


def neighbours(fy, dataset='treasurers-cash.csv', field='held_as'):
    """[1] which rows the nearest published years have that this one does not."""
    p = os.path.join(ROOT, 'sources', 'data', dataset)
    if not os.path.exists(p):
        return
    by = collections.defaultdict(set)
    for r in csv.DictReader(open(p, encoding='utf-8')):
        try:
            by[int(r['fy'])].add(r[field])
        except (KeyError, TypeError, ValueError):
            continue
    mine = by.get(fy, set())
    for other in sorted(by, key=lambda y: (abs(y - fy), -y))[:2]:
        if other == fy:
            continue
        missing = sorted(t for t in by[other]
                         if not any(t.lower()[:18] in m.lower() for m in mine))
        if missing:
            print('  [1] vs FY%d, this year is missing %d row(s): %s'
                  % (other, len(missing), ', '.join(m[:26] for m in missing[:6])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fy', type=int)
    ap.add_argument('--page', type=int)
    ap.add_argument('--residual', type=float)
    ap.add_argument('--blocked', action='store_true')
    a = ap.parse_args()

    if a.blocked:
        if not os.path.exists(BLOCKED):
            print('nothing blocked')
            return 0
        for r in csv.DictReader(open(BLOCKED, encoding='utf-8')):
            print('\n=== FY%s p%s %s -- %s' % (r['fy'], r['page'], r['what'], r['reason']))
            try:
                fy, pg = int(r['fy']), int(r['page'])
            except (TypeError, ValueError):
                continue
            neighbours(fy)
            diagnose(fy, pg, float(r['difference']) if r.get('difference') else None)
        return 0

    if not (a.fy and a.page):
        ap.error('--fy and --page, or --blocked')
    print('=== FY%d page %d' % (a.fy, a.page))
    neighbours(a.fy)
    diagnose(a.fy, a.page, a.residual)
    return 0


if __name__ == '__main__':
    sys.exit(main())
