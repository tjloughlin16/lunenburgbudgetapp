#!/usr/bin/env python3
"""The town's own wage list: every name it prints and what it paid them.

    python3 scripts/extract_gross_wages.py [--check]     # build from sources/data/wage-pages/
    python3 scripts/extract_gross_wages.py --dump        # re-dump the pages first (needs build/)

Writes `sources/data/gross-wages.csv` -- fy, name, amount, and the department where the
town prints one.

TJ, 22 September 2026, on seeing the Council on Aging at eleven people: *"because when i
saw council on aging numbers, i was very surprised. but if some are part time, that number
is misleading."*

HE IS RIGHT AND THIS IS THE CORRECTIVE. The Council on Aging's eleven are real people and
nothing like eleven jobs: its MART van drivers were paid $1,539.37, $13,701.97 and
$24,119.96 in 2025, and its meal-site assistants $3,035.52 and $7,399.64. A headcount
counts the driver who works Tuesdays the same as the Director. The wage list is the only
thing the town publishes that can tell them apart.

WHAT IT IS AND IS NOT. It is GROSS WAGES paid in the year -- so it includes overtime,
police details, stipends and anyone who worked a single shift, and it is not salary, not
FTE and not a rate of pay. A low figure means a small amount of money was paid to that
person in that year; it does not say whether that is a part-time post, a mid-year start or
a retirement in September. Rule 11's warning runs the other way here too: this is what the
town PAID, which is not what a post COSTS once benefits are counted.

THE DEPARTMENT IS PRINTED UNTIL FY2017 AND NOT AFTER. FY2011-FY2017 print one beside each
name -- before the amount in some years, after it in others -- and FY2018 onward print a
name and an amount and nothing else. So a town-wide total is available for every year, and
a per-department total only where the town printed the department, or where a name can be
matched to a roster we hold.

HOW EACH PAGE IS READ is the section headed ONE INSTRUMENT PER KIND OF PAGE below: the text
layer where the PDF is digital, Textract where the page is a scan, every page graded on
whether each money figure it prints was captured.
"""
import argparse
import collections
import csv
import glob
import json
import os
import re
import statistics
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'gross-wages.csv')
FIELDS = ['fy', 'page', 'name', 'amount', 'department', 'as_printed', 'status',
          'reconciliation']
# THE DOLLAR SIGN IS NOT ALWAYS THERE. FY2025 prints `$64,696.14` and FY2018 prints
# `13,757.44` bare, so a pattern anchored on `$` read FY2018's wage page as empty. The
# page is found from the contents rather than from the money, so dropping the anchor is
# safe here in a way it would not be if this were hunting for the page.
MONEY = re.compile(r'\$?\s?([\d,]+\.\d\d)')
NOISE = re.compile(r'^(?:TOTAL|GRAND|PAGE|\d+)$', re.I)
def _wagey(lines):
    """Is this page a list of PEOPLE and pay, rather than a table of appropriations?

    Wages are small and there are hundreds of them. A budget page carries a few dozen
    figures and many of them are six and seven digits. Both are dense in money; only one
    is dense in money UNDER $250,000.
    """
    amts = [float(m.replace(',', '')) for t in lines for m in MONEY.findall(t)]
    if len(amts) < 25:
        return False
    small = sum(1 for a in amts if a < 250000)
    return small / len(amts) > 0.95
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT_REFUSED = os.path.join(ROOT, 'sources', 'data', 'gross-wages-refused.csv')
REFUSED_FIELDS = ['report_fy', 'document', 'page', 'subject', 'reason', 'evidence']
def ocr_boxes(doc, page):
    """One page of Vision boxes. Split on tabs -- csv may not be used on these files."""
    path = os.path.join(OCR, doc[:-4] + '.tsv')
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', errors='replace') as fh:
        for i, line in enumerate(fh):
            f = line.rstrip('\n').split('\t')
            if i == 0 or len(f) < 7:
                continue
            try:
                p, x, y = int(f[0]), float(f[1]), float(f[2])
            except ValueError:
                continue
            if p == page:
                # `w` is carried because measured_skew() needs the box's RIGHT edge to
                # find its neighbour; read_ocr_page() ignores it.
                out.append({'x': x, 'y': y, 'w': float(f[3] or 0),
                            't': '\t'.join(f[6:]).strip()})
    return out
MIN_PAIRS = 8             # below this a measurement is REFUSED, never defaulted to zero
def measured_skew(boxes):
    """(slope, n_pairs) -- rule 13b #1, with the pair count returned deliberately.

    A scan is slightly turned, so a printed row's boxes do not share a `y`. The rotation is
    recoverable from the page itself: take each box's nearest neighbour to its right, take
    the MEDIAN slope between them.

    IT RETURNS THE PAIR COUNT BECAUSE A MEASURED ZERO AND AN UNMEASURABLE PAGE MUST NOT
    LOOK ALIKE. FY2013 p83 was recorded as rotated on the strength of a skew function that
    returned `0.00000` for `fewer than 8 usable pairs` -- a failure signalled with a value
    the successful measurement can legitimately produce. Three of these seven pages really
    are square, measured from 237 pairs each, and that is a different statement from
    silence wearing the same number.
    """
    slopes = []
    for b in boxes:
        right = [c for c in boxes
                 if c['x'] > b['x'] + b['w'] * 0.5 and abs(c['y'] - b['y']) < 0.012]
        if not right:
            continue
        n = min(right, key=lambda c: c['x'])
        dx = n['x'] - b['x']
        if dx > 0.01:
            slopes.append((n['y'] - b['y']) / dx)
    if len(slopes) < MIN_PAIRS:
        return None, len(slopes)
    return statistics.median(slopes), len(slopes)
def grade(rows):
    """What a WAGE LIST can be checked against, which is not a total.

    TJ: *"yes there is no total, but that's fine. this table doesnt intend to do that and
    print totals. that shouldnt be a blocker."* Right -- demanding a footing was the wrong
    test for the wrong kind of table.

    THE CHECK THAT DOES FIT IS COVERAGE: every money figure PRINTED on the page is in the
    data, paired with a name on its own printed row. That has real power to fail -- before
    the text layer was used, FY2025 pages 180-182 covered 87 of 104, 54 of 104 and 89 of
    102, and this would have failed all three.

    An earlier version of this graded whether SURNAMES ASCEND down the page. That test is
    wrong here and the first run showed it: these pages print TWO records per line, so
    reading order alternates between the columns and the sequence is not monotonic even
    when every row is right. It marked 3,388 correct rows as failures. The ordering only
    means something WITHIN a column, which needs the x position -- and coverage is the
    better check anyway, because it catches a row that was never read at all.
    """
    by = collections.defaultdict(list)
    for r in rows:
        by[(r['fy'], int(r['page']))].append(r)
    for (fy, page), page_rows in by.items():
        printed = max((r.pop('_printed_money', 0) or 0) for r in page_rows)
        got = len(page_rows)
        if not printed:
            verdict = 'no check'
            why = ('%d row(s); the count of money figures printed on the page is not '
                   'established, so coverage cannot be asserted' % got)
        elif got >= printed:
            verdict = 'checked'
            why = ('%d of %d money figures printed on the page are captured, each paired '
                   'with a name on its own printed row. A wage list prints no total, so '
                   'this proves COVERAGE and the pairing, not the digits' % (got, printed))
        else:
            verdict = 'check failed'
            why = ('%d of %d money figures printed on the page are captured; %d are not '
                   'accounted for' % (got, printed, printed - got))
        for r in page_rows:
            r['status'], r['reconciliation'] = verdict, why


# ======================================================================================
# ONE INSTRUMENT PER KIND OF PAGE -- 4 November 2026
# ======================================================================================
#
# Until today this file had four readers -- a line cache, Vision boxes in two layouts, and
# the text layer for FY2025 alone -- chosen per year by whichever had been made to work.
# The result was a dataset nobody could compare across years: FY2025 612 names, `checked`;
# FY2012 and FY2013 none at all; FY2023 one name; FY2022 and FY2024 thirty-nine each. And
# FY2019 fell from 516 to 461 the day its Vision OCR was redone, because the new reading
# dropped the given-name column off the lower half of two pages.
#
# TJ, the same day: *"whatever is most accurate do that, but make sure you use aws
# textract.... we might need to reprocess the newer reports so they are consistent?"*
#
# So every year is now read the same way, by the instrument that fits the PAGE:
#
#   text layer   the PDF is digital: exact words, exact positions, nothing to misread
#   textract     the page is a scan and Textract has read it (Vision 87.5% against
#                Textract 99.7% on the FY2011 pilot pages, 27 October 2026)
#   vision       a scan Textract has not read -- the fallback, and named as one
#
# Every page's words are DUMPED into `sources/data/wage-pages/FY<year>-p<NNN>.tsv` with the
# instrument that read them (`--dump`, which needs `build/textract/cache`). The build reads
# only those files, so `--check` reproduces on a clone that holds no Textract cache.
#
# THE PAGES ARE WRITTEN DOWN, and the edges are checked. The contents page names the list
# `Payroll Report` in FY2011-FY2013 and something else after, and in FY2011 the entry is
# misread (`Payroll Report 97-99 10 PM Personnel Committee`, pdf 26-27). So the pages are
# recorded here per year, as found by measuring every page near the index entry, and
# `--dump` refuses if the page before the first or after the last is itself a wage page:
# that would mean the list runs on and this table is wrong.
LIST_PAGES = {
    '2011': ('4117-fy-2011-annual-town-report.pdf', range(98, 102)),
    '2012': ('4118-fy-2012-annual-town-report.pdf', range(112, 116)),
    '2013': ('4119-fy-2013-annual-town-report.pdf', range(93, 98)),
    '2014': ('4120-fy-2014-annual-town-report.pdf', range(168, 175)),
    '2015': ('4121-fy-2015-annual-town-report.pdf', range(206, 212)),
    '2016': ('4123-fy-2016-annual-town-report.pdf', range(198, 203)),
    '2017': ('4124-fy-2017-annual-town-report.pdf', range(192, 199)),
    '2018': ('4125-fy-2018-annual-town-report.pdf', range(248, 255)),
    '2019': ('4126-fy-2019-annual-town-report.pdf', range(197, 204)),
    '2020': ('4127-fy-2020-annual-town-report.pdf', range(208, 215)),
    '2021': ('4128-fy-2021-annual-town-report.pdf', range(162, 169)),
    '2022': ('4129-fy-2022-annual-town-report.pdf', range(186, 193)),
    '2023': ('4131-fy-2023-annual-town-report.pdf', range(190, 198)),
    '2024': ('4132-fy-2024-annual-town-report.pdf', range(186, 194)),
    '2025': ('4130-fy-2025-annual-town-report.pdf', range(177, 183)),
}
WAGE_PAGES = os.path.join(ROOT, 'sources', 'data', 'wage-pages')
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
TEXTRACT_CACHE = os.path.join(ROOT, 'build', 'textract', 'cache')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
WORD_FIELDS = ['x', 'y', 'w', 'confidence', 'text']
LIST_MONEY = re.compile(r'^\$?([\d,]{1,9}\.\d\d)$')
NAME_WORD = re.compile(r"^[A-Za-z][A-Za-z'\-\.]*,?$")
MIN_LIST_MONEY = 15        # a page holding fewer money figures than this is not a wage page


def _sha_of(doc):
    for r in csv.DictReader(open(MANIFEST, encoding='utf-8')):
        if r['key'].endswith('/' + doc) and 'searchable' not in r['key']:
            return r['sha256']
    return None


def _text_layer_words(pdf, n):
    """Words off a digital page, normalised to the page: x from the left, y UP from the
    bottom (the Vision convention the banding functions were written for)."""
    if n < 1 or n > len(pdf.pages):
        return None
    pg = pdf.pages[n - 1]
    ws = pg.extract_words()
    if len(ws) < 40 or not any(LIST_MONEY.match(w['text']) for w in ws):
        return None
    W, H = float(pg.width), float(pg.height)
    return [dict(x=w['x0'] / W, y=1 - (w['top'] + w['bottom']) / 2 / H,
                 w=(w['x1'] - w['x0']) / W, confidence=100.0, text=w['text']) for w in ws]


def _textract_words(sha, n):
    if not sha:
        return None
    hits = sorted(glob.glob(os.path.join(TEXTRACT_CACHE, sha, 'p%03d-*.json' % n)))
    # `tables` carries the words too and is the richer read; prefer it, then `text`.
    hits.sort(key=lambda p: (not p.endswith('-tables.json'), p))
    for h in hits:
        if h.endswith('-reread.json'):
            continue
        out = []
        for b in json.load(open(h, encoding='utf-8'))['Blocks']:
            if b['BlockType'] != 'WORD':
                continue
            g = b['Geometry']['BoundingBox']
            out.append(dict(x=g['Left'], y=1 - (g['Top'] + g['Height'] / 2),
                            w=g['Width'], confidence=round(b['Confidence'], 1),
                            text=b['Text']))
        return out
    return None


def _vision_words(doc, n):
    out = [dict(x=b['x'], y=b['y'], w=b['w'], confidence='', text=t)
           for b in ocr_boxes(doc, n) for t in [b['t']]]
    return out or None


def _money_count(words):
    return sum(1 for w in words if LIST_MONEY.match(w['text']))


def dump():
    """Write every wage page's words, from the best instrument that has read it."""
    import pdfplumber
    os.makedirs(WAGE_PAGES, exist_ok=True)
    index = []
    for fy, (doc, rng) in sorted(LIST_PAGES.items()):
        sha = _sha_of(doc)
        with pdfplumber.open(os.path.join(DOCS, doc)) as pdf:
            def best(n):
                for how, get in (('text layer', lambda: _text_layer_words(pdf, n)),
                                 ('textract', lambda: _textract_words(sha, n)),
                                 ('vision', lambda: _vision_words(doc, n))):
                    ws = get()
                    if ws:
                        return how, ws
                return None, None
            # THE EDGES: the list must not run past the pages written down.
            for edge in (rng.start - 1, rng.stop):
                how, ws = best(edge)
                if ws and _money_count(ws) >= MIN_LIST_MONEY and _wagey(
                        [w['text'] for w in ws]):
                    raise SystemExit('FY%s p%d holds %d wage-like figures (%s): the list '
                                     'runs past LIST_PAGES. Look at the page and fix the '
                                     'range.' % (fy, edge, _money_count(ws), how))
            for n in rng:
                how, ws = best(n)
                if not ws:
                    raise SystemExit('FY%s p%d: no instrument has read this page' % (fy, n))
                name = 'FY%s-p%03d.tsv' % (fy, n)
                with open(os.path.join(WAGE_PAGES, name), 'w', encoding='utf-8',
                          newline='') as fh:
                    w = csv.writer(fh, delimiter='\t', lineterminator='\n')
                    w.writerow(WORD_FIELDS)
                    for b in sorted(ws, key=lambda b: (-round(b['y'], 4), b['x'])):
                        w.writerow(['%.4f' % b['x'], '%.4f' % b['y'], '%.4f' % b['w'],
                                    b['confidence'], b['text'].replace('\t', ' ')])
                index.append(dict(fy=fy, page=n, document=doc, instrument=how,
                                  words=len(ws), money=_money_count(ws)))
    with open(os.path.join(WAGE_PAGES, 'PAGES.csv'), 'w', encoding='utf-8',
              newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'page', 'document', 'instrument',
                                           'words', 'money'])
        w.writeheader()
        w.writerows(index)
    print('%d wage pages dumped: %s' % (len(index), dict(collections.Counter(
        r['instrument'] for r in index))))


def _load_page(fy, n):
    path = os.path.join(WAGE_PAGES, 'FY%s-p%03d.tsv' % (fy, n))
    out = []
    with open(path, encoding='utf-8') as fh:
        for i, line in enumerate(fh):
            f = line.rstrip('\n').split('\t')
            if i == 0 or len(f) < 5:
                continue
            out.append({'x': float(f[0]), 'y': float(f[1]), 'w': float(f[2]),
                        't': '\t'.join(f[4:]).strip()})
    return out


def _money_columns(boxes):
    """Right edges of the page's money columns, MEASURED: amounts are right-aligned, so
    their right edges cluster, one cluster per printed column. Two columns on most pages,
    three on FY2016's, one on the last page of a list that ran short."""
    edges = sorted(b['x'] + b['w'] for b in boxes if LIST_MONEY.match(b['t']))
    cols, cur = [], []
    for e in edges:
        if cur and e - cur[-1] > 0.08:
            cols.append(max(cur))
            cur = []
        cur.append(e)
    if cur:
        cols.append(max(cur))
    return cols


# THE DEPARTMENT IS A COLUMN, AND IT IS FOUND BY MEASURING, NOT BY VOCABULARY. FY2014 prints
# `CARDONE JOSEPH 4,206.26 FIRE`, FY2015 `CARRIER JANICE CONSERVATION 42,494.54`, FY2019 on
# no department at all. A list of department words missed CONSERVATION, TREASURER and `BD`
# on the first run. What does separate the column is that its values REPEAT -- SCHOOL,
# SCHOOL, FIRE, SCHOOL -- where surnames and given names are mostly distinct. So each
# sub-column (a cluster of word left edges) is classed by how many distinct values it holds.
SUBCOL_GAP = 0.025
DEPT_DISTINCT = 0.35       # a column with fewer distinct values than this share is a department
DEPT_MIN = 6               # ...and only if it has at least this many entries to judge by


def _layout(boxes, cols):
    """[[left, kind, owner, words]] for the page's word sub-columns. `owner` is the money
    column (record) a sub-column belongs to."""
    words = sorted((b for b in boxes if not LIST_MONEY.match(b['t'])), key=lambda b: b['x'])
    if not words:
        return None
    clusters, cur = [], [words[0]]
    for b in words[1:]:
        if b['x'] - cur[-1]['x'] > SUBCOL_GAP:
            clusters.append(cur)
            cur = []
        cur.append(b)
    clusters.append(cur)
    money_left = []
    for right in cols:
        xs = [b['x'] for b in boxes if LIST_MONEY.match(b['t'])
              and abs(b['x'] + b['w'] - right) < 0.08]
        money_left.append(min(xs))
    out = []
    for c in clusters:
        left = statistics.median(b['x'] for b in c)
        vals = [b['t'].upper() for b in c]
        alpha = sum(1 for v in vals if re.match(r'^[A-Z&/\.]+$', v))
        dept = len(vals) >= DEPT_MIN and len(set(vals)) / len(vals) < DEPT_DISTINCT \
            and alpha >= 0.8 * len(vals)
        out.append([left, 'dept' if dept else 'name', None, len(c)])
    # A TWO-WORD DEPARTMENT. FY2014's `ANIMAL CTRL` puts `CTRL` in a sparse cluster of its
    # own just right of the department column, which read as a name of the NEXT record. A
    # sparse cluster that close to a department column's right is that department's.
    big = max((o[3] for o in out), default=0)
    for i in range(1, len(out)):
        if out[i][1] == 'name' and out[i - 1][1] == 'dept' and out[i][3] < big / 3.0 \
                and out[i][0] - out[i - 1][0] < 0.08:
            out[i][1] = 'dept'
    # A sub-column belongs to the first money column to its right -- unless it is a
    # department printed AFTER an amount (FY2014: `CARDONE JOSEPH 4,206.26 FIRE`). The test
    # is what sits IMMEDIATELY to its left: an amount, with no name sub-column between, means
    # it closes that amount's record. Testing what lies to its RIGHT instead handed FY2011's
    # right-hand department to the left-hand record, because a stray name cluster sat
    # between it and the next amount.
    for sc in out:
        right_money = [k for k, ml in enumerate(money_left) if ml > sc[0]]
        nxt = right_money[0] if right_money else None
        if sc[1] == 'dept':
            left_money = [k for k, r in enumerate(cols) if r <= sc[0] + 0.01]
            if left_money:
                k = left_money[-1]
                if not any(o[1] == 'name' and cols[k] < o[0] < sc[0] for o in out):
                    sc[2] = k
                    continue
        sc[2] = nxt
    return out


def _place(b, layout, cols):
    """(kind, owner) for one word: money goes to its column, a word to its sub-column."""
    if LIST_MONEY.match(b['t']):
        e = b['x'] + b['w']
        k = min(range(len(cols)), key=lambda k: abs(cols[k] - e))
        return ('money', k, False) if abs(cols[k] - e) < 0.08 else ('money', None, False)
    sc = min(layout, key=lambda sc: abs(sc[0] - b['x']))
    return sc[1], sc[2], sc is _surname_col(layout, sc[2], cols)


def _surname_col(layout, k, cols):
    """The record's SURNAME sub-column: its leftmost name sub-column that is POPULATED.
    Not merely its leftmost -- FY2019 p197's right half has a stray cluster at 0.444, where
    the left-hand amounts sit, and taking that refused every right-hand record."""
    if k is None:
        return None
    cand = [o for o in layout if o[1] == 'name' and o[2] == k]
    big = max((o[3] for o in cand), default=0)
    cand = [o for o in cand if o[3] >= max(3, big / 3.0)]
    return min(cand, key=lambda o: o[0]) if cand else None



def money_pitch(boxes, slope, cols):
    """The page's row pitch, measured on its MONEY columns -- rule 13b #2.

    A wage list prints exactly one amount per record per row, so the gaps between amounts
    in one column ARE the pitch. `row_pitch` measures the leftmost column instead, which on
    a short last page is the running head: FY2018 p254 has 22 records and its leftmost box
    is `Town`, so it found fewer than eight gaps and refused the page.
    """
    for b in boxes:
        b['Y'] = b['y'] - slope * b['x']
    gaps = []
    for right in cols:
        ys = sorted((b['Y'] for b in boxes if LIST_MONEY.match(b['t'])
                     and abs(b['x'] + b['w'] - right) < 0.08), reverse=True)
        gaps += [a - b for a, b in zip(ys, ys[1:]) if 0.004 < a - b < 0.06]
    if len(gaps) < MIN_PAIRS:
        return None
    return statistics.median(gaps)


def read_list_page(fy, doc, page, instrument, refused):
    """Rows off one page of words, whatever read them.

    Measure the rotation and the row pitch (rule 13b), band, give every word to the money
    column it sits left of, and pair. A record is ONE amount and at least one name word in
    one printed row of one column; anything else holding money is refused and counted.
    """
    def bail(reason, evidence):
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll', 'reason': reason,
                        'evidence': evidence + ' (read by %s)' % instrument})
        return []

    boxes = [b for b in _load_page(fy, page) if b['t'] != '$']
    cols = _money_columns(boxes)
    printed = sum(1 for b in boxes if LIST_MONEY.match(b['t']))
    if not cols:
        return bail('no money figure on the page', '%d word(s)' % len(boxes))
    slope, pairs = measured_skew(boxes)
    if slope is None:
        return bail('the page rotation could not be measured, so its rows cannot be banded',
                    '%d word(s); only %d usable neighbour pair(s), %d needed'
                    % (len(boxes), pairs, MIN_PAIRS))
    pitch = money_pitch(boxes, slope, cols)
    if pitch is None:
        return bail('the page row pitch could not be measured, so its rows cannot be banded',
                    '%d word(s); fewer than %d gaps in any money column'
                    % (len(boxes), MIN_PAIRS))
    bands = []
    for b in sorted(boxes, key=lambda b: (-b['Y'], b['x'])):
        if bands and abs(b['Y'] - bands[-1][0]['Y']) < pitch / 2.0:
            bands[-1].append(b)
        else:
            bands.append([b])

    layout = _layout(boxes, cols)
    if layout is None:
        return bail('the page sub-columns could not be measured',
                    '%d word(s), %d money column(s)' % (len(boxes), len(cols)))

    rows, unpaired, order = [], 0, collections.defaultdict(list)
    for band in bands:
        rec = collections.defaultdict(lambda: {'name': [], 'dept': [], 'money': []})
        for b in sorted(band, key=lambda b: b['x']):
            kind, owner, first = _place(b, layout, cols)
            if owner is None:
                continue
            rec[owner][kind].append(b)
            rec[owner]['surname'] = rec[owner].get('surname') or first
        for k, cell in sorted(rec.items()):
            if not cell['money']:
                continue                 # a heading, a column label, a wrapped word
            words = [t.rstrip(',') for b in cell['name'] for t in b['t'].split()]
            # A department misread as digits (FY2011 p99 `161` for SCHOOL) is not guessed.
            dept = ' '.join(b['t'] for b in cell['dept']
                            if re.match(r'^[A-Za-z&/\.]+$', b['t'])).title()
            shown_ = sorted(cell['name'] + cell['dept'] + cell['money'], key=lambda b: b['x'])
            # A GIVEN NAME ALONE IS NOT A NAME. Where Textract missed the surname (FY2017
            # p197: `JOHN  DPW  59,017.55`) the record would be published as `JOHN`. The
            # record must hold a word in its SURNAME sub-column; a surname alone is still a
            # payment, as it always was here.
            if len(cell['money']) != 1 or not words or not cell.get('surname') \
                    or not all(NAME_WORD.match(w) for w in words) or NOISE.match(words[0]):
                unpaired += 1
                continue
            rows.append(dict(fy=fy, page=page, name=' '.join(words),
                             amount='%.2f' % float(LIST_MONEY.match(
                                 cell['money'][0]['t']).group(1).replace(',', '')),
                             department=dept,
                             as_printed=' '.join(b['t'] for b in shown_)[:160],
                             _printed_money=printed, _instrument=instrument, _col=k))
            order[k].append(re.sub(r'[^A-Z]', '', words[0].upper()))
    # THE ALPHABET, PER COLUMN, graded as before: a few inversions are a misread surname
    # and those rows are dropped; many mean the banding is wrong and the page is refused.
    for k, names in order.items():
        bad = [(a, b) for a, b in zip(names, names[1:]) if a > b]
        if not bad:
            continue
        if len(bad) > max(2, len(names) // 20):
            return bail('the surnames read off this column are not in the order the list '
                        'prints them, so rows have been misassigned',
                        '%d inversion(s) in %d name(s) in column %d, first at %s -> %s'
                        % (len(bad), len(names), k + 1, bad[0][0], bad[0][1]))
        drop = {b for _, b in bad}
        rows = [r for r in rows if not (r['_col'] == k and r['name'].split()[0].upper()
                                        in drop)]
        refused.append({'report_fy': fy, 'document': doc, 'page': page, 'subject': 'payroll',
                        'reason': 'a surname was read out of the order the list prints '
                                  'it, so that row was dropped rather than published under '
                                  'a name we may have misread',
                        'evidence': '%d inversion(s) in %d name(s) in column %d: %s (read '
                                    'by %s)' % (len(bad), len(names), k + 1, ', '.join(
                                        '%s -> %s' % p for p in bad), instrument)})
    if unpaired:
        refused.append({'report_fy': fy, 'document': doc, 'page': page, 'subject': 'payroll',
                        'reason': 'a printed row held an amount without a name, or more '
                                  'than one amount, and was not guessed at',
                        'evidence': '%d row(s) paired, %d refused; %d money figure(s) on '
                                    'the page in %d column(s) (read by %s)'
                                    % (len(rows), unpaired, printed, len(cols), instrument)})
    for r in rows:
        r.pop('_col', None)
    return rows


# THE CHECK WITH POWER TO FAIL. Seven years of these lists were also read BY EYE, row by row,
# into `pages-read.csv` (column `gross_wages`; surname in `fund_number`, given name in
# `fund_name`). That reading is independent of every instrument here, so the amounts this
# file captures are compared with it, year by year, and nothing is written if any year
# agrees on fewer than AGREE_MIN of them. On 4 November 2026: 4,240 of 4,246.
PAGES_READ = os.path.join(ROOT, 'sources', 'data', 'pages-read.csv')
AGREE_MIN = 0.99


def against_page_reads(rows):
    hand = collections.defaultdict(collections.Counter)
    for r in csv.DictReader(open(PAGES_READ, encoding='utf-8')):
        if r['column'] == 'gross_wages':
            hand[r['fy']]['%.2f' % float(r['value'])] += 1
    out = {}
    for fy, want in hand.items():
        got = collections.Counter(r['amount'] for r in rows if r['fy'] == fy)
        agree = sum((want & got).values())
        out[fy] = (sum(want.values()), agree)
        if agree < AGREE_MIN * sum(want.values()):
            raise SystemExit('FY%s: %d of %d amounts agree with the by-eye read in '
                             'pages-read.csv, under %.0f%%. Nothing written.'
                             % (fy, agree, sum(want.values()), AGREE_MIN * 100))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dump', action='store_true',
                    help='re-dump every wage page from the instruments (needs the '
                         'Textract cache in build/), then build')
    a = ap.parse_args()
    if a.dump:
        dump()
    rows, refused = [], []
    for p in csv.DictReader(open(os.path.join(WAGE_PAGES, 'PAGES.csv'), encoding='utf-8')):
        rows += read_list_page(p['fy'], p['document'], int(p['page']), p['instrument'],
                               refused)
    grade(rows)
    for r in rows:
        r['reconciliation'] += '. Read by %s' % r.pop('_instrument')
    # THE TOWN PRINTS SOME RECORDS TWICE, and a total would pay those people twice. FY2016
    # p202 reprints 32 of p201's names; FY2023 p197 reprints the right-hand column of p196;
    # FY2017 p197 is two photographed sheets that overlap, so its right-hand column runs
    # SMITH to SULLIVAN and starts again at SMITH. The same name with the same amount to
    # the cent, in one year's list, is one record printed again. It counted above, because
    # it WAS read off the page; it is dropped here, and registered with where it repeats.
    seen, kept, repeats = {}, [], collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: (r['fy'], int(r['page']))):
        k = (r['fy'], r['name'], r['amount'])
        if k in seen:
            repeats[(r['fy'], int(r['page']), seen[k])].append(r['name'])
            continue
        seen[k] = int(r['page'])
        kept.append(r)
    rows = kept
    for (fy, page, first), names in sorted(repeats.items()):
        refused.append({'report_fy': fy, 'document': LIST_PAGES[fy][0], 'page': page,
                        'subject': 'payroll',
                        'reason': 'the page prints a record already printed earlier in the '
                                  'list, with the same amount; kept once',
                        'evidence': '%d record(s) repeat page %d, first %s'
                                    % (len(names), first, ', '.join(sorted(names)[:3]))})
    agreement = against_page_reads(rows)
    rows.sort(key=lambda r: (r['fy'], int(r['page']), r['name']))
    refused.sort(key=lambda r: (r['report_fy'], int(r['page']), r['reason']))
    if a.check:
        rc = 0
        old = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        if len(old) != len(rows) or any(
                any(str(r[k]) != o[k] for k in FIELDS) for r, o in zip(rows, old)):
            print('STALE %s' % OUT)
            rc = 1
        oldr = (list(csv.DictReader(open(OUT_REFUSED, encoding='utf-8')))
                if os.path.exists(OUT_REFUSED) else [])
        if len(oldr) != len(refused) or any(
                any(str(r[k]) != o[k] for k in REFUSED_FIELDS)
                for r, o in zip(refused, oldr)):
            print('STALE %s' % OUT_REFUSED)
            rc = 1
        return rc
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(OUT_REFUSED, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=REFUSED_FIELDS)
        w.writeheader()
        w.writerows(refused)
    for fy, (hand, agree) in sorted(agreement.items()):
        print('  FY%s against the by-eye read: %d of %d amounts agree' % (fy, agree, hand))
    for r in refused:
        print('  REFUSED FY%s page %s: %s -- %s'
              % (r['report_fy'], r['page'], r['reason'], r['evidence']))
    per = collections.Counter(r['fy'] for r in rows)
    tot = collections.defaultdict(float)
    for r in rows:
        tot[r['fy']] += float(r['amount'])
    print('%d wage rows across %d years' % (len(rows), len(per)))
    for fy in sorted(per):
        dep = len({r['department'] for r in rows
                   if r['fy'] == fy and r['department']})
        print('  FY%s  %4d names  $%12s  %s'
              % (fy, per[fy], format(int(tot[fy]), ','),
                 '%d departments tagged' % dep if dep else 'no department printed'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
