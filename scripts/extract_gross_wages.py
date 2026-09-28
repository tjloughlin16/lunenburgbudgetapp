#!/usr/bin/env python3
"""The town's own wage list: every name it prints and what it paid them.

    python3 scripts/extract_gross_wages.py [--check]

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

THE DEPARTMENT IS THE PROBLEM. The early lists tag each name with one -- `HOWARD, ERIN
FIRE` in FY2011, a `SCHOOL` heading in FY2016 -- and the later ones do not: FY2018 onward
print a name and an amount and nothing else. So a town-wide total is available for every
year the list reads, and a per-department total is only available where the town printed
the department, or where a name can be matched to a roster we hold.
"""
import argparse
import collections
import csv
import glob
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
OUT = os.path.join(ROOT, 'sources', 'data', 'gross-wages.csv')
FIELDS = ['fy', 'page', 'name', 'amount', 'department', 'as_printed', 'status',
          'reconciliation']

# THE DOLLAR SIGN IS NOT ALWAYS THERE. FY2025 prints `$64,696.14` and FY2018 prints
# `13,757.44` bare, so a pattern anchored on `$` read FY2018's wage page as empty. The
# page is found from the contents rather than from the money, so dropping the anchor is
# safe here in a way it would not be if this were hunting for the page.
MONEY = re.compile(r'\$?\s?([\d,]+\.\d\d)')
HEAD = re.compile(r'gross wages|employee compensation|employee gross', re.I)
# The department, where the town tags it: appended to the name in the early lists.
DEPT_TAG = re.compile(r'\b(FIRE|POLICE|SCHOOL|DPW|LIBRARY|HIGHWAY|CEMETERY|WATER|SEWER'
                      r'|TOWN HALL|COA|SENIOR|BUILDING|PARK|RECREATION)\b$')
NOISE = re.compile(r'^(?:TOTAL|GRAND|PAGE|\d+)$', re.I)


def pages(fy):
    by, page = collections.defaultdict(list), None
    path = os.path.join(PAGES, 'FY%s.ocr.txt' % fy)
    if not os.path.exists(path):
        return {}
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        if page:
            by[page].append(re.sub(r'\s+', ' ', re.sub(r'^\s*\d+\|', '', line)).strip())
    return by


INDEX = os.path.join(ROOT, 'sources', 'data', 'report-index.csv')


def _index_pages(fy):
    """Where the town's contents page says the wage list is."""
    if not os.path.exists(INDEX):
        return []
    out = []
    for r in csv.DictReader(open(INDEX, encoding='utf-8')):
        if r['fy'] == fy and r['state'] == 'report' and HEAD.search(r['department']) \
                and r['pdf_from']:
            out += list(range(int(r['pdf_from']), int(r['pdf_to']) + 1))
    return sorted(set(out))


def wage_pages(by, fy):
    """Pages of the wage list, from the town's own contents page, then run on.

    THE FIRST VERSION GUESSED AND WAS COMPREHENSIVELY WRONG. It looked for pages dense in
    money, which is a description of every budget table in the book: FY2011 came back with
    39 `names` totalling $25.7 MILLION, because it was reading the appropriations summary.
    A wage figure is a person's pay and a budget figure is a department's, and nothing in
    the shape of the page tells them apart.

    The contents page says where the list is, and `extract_report_index.py` already reads
    it. The range it gives is often one page when the list runs six, so it is extended
    while the pages stay dense in SMALL money -- the test that does separate the two.
    """
    seed = _index_pages(fy)
    if not seed:
        seed = [p for p in sorted(by)
                if any(HEAD.search(t) for t in by[p][:8]) and _wagey(by[p])]
    if not seed:
        return []
    out, p = sorted(seed), max(seed) + 1
    while p in by and _wagey(by[p]):
        out.append(p)
        p += 1
    p = min(seed) - 1
    while p in by and _wagey(by[p]):
        out.insert(0, p)
        p -= 1
    return sorted(set(out))


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


def parse_line(t):
    """(name, amount) pairs on one printed line, which carries TWO columns.

    SPLIT ON THE MONEY, NOT ON THE NAME. The list prints `ABRAHAM DAVID $64,696.14 LEGER
    VICTORIA $2,056.23` -- two people on one line -- and a pattern that tries to describe
    what a NAME looks like loses every compound surname on the page. The amounts are
    unambiguous, so each name is simply whatever text sits between the previous amount and
    the next one.
    """
    out, last = [], 0
    for m in MONEY.finditer(t):
        name = t[last:m.start()].strip(' .,-')
        last = m.end()
        name = re.sub(r'\s+', ' ', name).strip()
        if not name or NOISE.match(name) or len(name) < 4:
            continue
        dept = ''
        d = DEPT_TAG.search(name)
        if d:
            dept = d.group(1).title()
            name = name[:d.start()].strip(' ,')
        # A SURNAME ON ITS OWN IS STILL A PAYMENT. The list is set in two columns and the
        # right-hand column loses its given names in the line-level OCR -- `CAVACO QUINN
        # $68,275.47 NORMANDIN $58,020.26` -- so requiring two words threw away 47 lines
        # of one FY2025 page and about $5M of the town's payroll. The money is certain
        # even where the name is half read, and a town TOTAL needs only the money. A
        # partial name simply will not match a roster, which is the honest outcome.
        out.append((name, float(m.group(1).replace(',', '')), dept))
    return out


def read_year(fy, refused=None, doc=''):
    """Rows of the wage list for one year, and a REFUSAL for every page that yielded none.

    A PAGE THAT YIELDS NOTHING USED TO YIELD SILENCE. `wage_pages()` correctly returns all
    seven of FY2019's payroll pages, 197 to 203. Four of them -- 198, 201, 202, 203 --
    produce no rows and produced no record of it either, so the archive held pages 197, 199
    and 200 of a seven-page list and nothing anywhere said the other four had been looked at.
    They were indistinguishable from pages nobody had opened, and two of them were reported
    to TJ as pages the town does not print a header on.

    The same defect as the receivables refusals, one step worse: those at least printed a
    line to a terminal. A page the extractor reached and could not read is a finding about
    OUR reader, and rule 13c says exactly that -- a pattern that does not match is not an
    absence.
    """
    by = pages(fy)
    rows = []
    owned = set(SPLIT_NAME.get(fy, ('', []))[1])
    for p in wage_pages(by, fy):
        if p in owned:
            # Read from the Vision boxes instead -- the line cache merges this page's two
            # columns into one box and loses the right-hand person on every row.
            continue
        before = len(rows)
        for t in by[p]:
            for name, amt, dept in parse_line(t):
                rows.append(dict(fy=fy, page=p, name=name, amount='%.2f' % amt,
                                 department=dept, as_printed=t[:160]))
        if refused is not None and len(rows) == before:
            refused.append({'report_fy': fy, 'document': doc, 'page': p,
                            'subject': 'payroll',
                            'reason': 'the page is in the wage list and no line on it '
                                      'paired a name with an amount',
                            'evidence': '%d cached line(s) on the page; parse_line() '
                                        'returned nothing for any of them' % len(by[p])})
    return rows


# ======================================================================================
# THE PAGES THE PAGE CACHE LOSES -- read from the Vision boxes instead
# ======================================================================================
#
# `sources/town-budget/pages/FY<year>.ocr.txt` is a fixed-width rendering of the Vision
# boxes, and everything above reads it. On two wage pages that rendering is empty of
# money where the boxes are full of it:
#
#     FY2011 page  98 -- 138 money boxes in the OCR, 0 in the page cache
#     FY2012 page 114 -- 133 money boxes in the OCR, 0 in the page cache
#
# The cache's FY2011 page 98 is not blank, which is worse than blank: it is that page
# rendered UPSIDE DOWN, so line 1 reads `L9'SLÉE$` and `T00 HOS`, which is `$338.27` and
# `SCHOOL` turned over. Nothing downstream could tell that from a page of bad OCR.
#
# RULE 13c: A MATCHER THAT FINDS NOTHING IS A STATEMENT ABOUT OUR INSTRUMENT. Two of
# them here -- the cache for both pages, and Vision itself for half of one -- and neither
# is a statement about the town, which printed both pages in full.
#
# What the boxes actually hold, which is the reason only one of the two pages publishes:
#
#   FY2011 page 98 is set in FOUR columns -- name, department, amount, then the same
#   again. Vision reads the RIGHT half completely (74 names against 75 amounts) and gives
#   up on the LEFT name column two thirds of the way down the page: 19 names against 63
#   amounts. So the right half pairs and most of the left half is amounts with nobody to
#   attach them to.
#
#   FY2012 page 114 has no names on it AT ALL. 338 boxes, of which 133 are money and the
#   rest are department words -- `SCHOOL`, `FIRE`, `SEWER`, `POLICE`. Both name columns
#   are unread. A department and an amount is not a wage row: it cannot be attributed to
#   anybody, it cannot be matched to a roster, and summing it would double-count against
#   the pages either side. That page is REFUSED.
#
# A WAGE PAGE PRINTS NO TOTAL -- not on any of the eight pages of the two lists, checked
# box by box -- so there is no identity to foot a row against, which is why every row in
# `report-gross-wages.csv` already carries `no check`. What stands in for it here is the
# PAIRING: a row is written only where one name and one amount sit in the same printed
# row on the same side of the page. An amount with two candidate names, or none, is
# counted and refused rather than attached to the nearest one.

OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT_REFUSED = os.path.join(ROOT, 'sources', 'data', 'gross-wages-refused.csv')
REFUSED_FIELDS = ['report_fy', 'document', 'page', 'subject', 'reason', 'evidence']

# fy -> document, pages. Kept explicit, and checked at run time against the cache: if a
# page here ever starts rendering, the script says so rather than reading it twice.
OCR_ONLY = {
    '2011': ('4117-fy-2011-annual-town-report.pdf', [98]),
    '2012': ('4118-fy-2012-annual-town-report.pdf', [114]),
}

OCR_MONEY = re.compile(r'^\$?\s?([\d,]+\.\d\d)$')
OCR_NAME = re.compile(r"^[A-Z][A-Za-z'\- ]{1,30},\s*[A-Z][A-Za-z'\- ]{1,30}$")
OCR_DEPT = re.compile(r'^(FIRE|POLICE|SCHOOL|DPW|LIBRARY|HIGHWAY|CEMETERY|WATER|SEWER'
                      r'|COA|SENIOR|BUILDING|PARK|RECREATION|TOWN HALL)$', re.I)


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


def _bands(boxes):
    """Printed rows, banded at HALF the page's own median row pitch -- rule 13b."""
    ys = sorted({round(b['y'], 4) for b in boxes}, reverse=True)
    gaps = sorted(a - b for a, b in zip(ys, ys[1:]) if 0.002 < a - b < 0.05)
    band = (gaps[len(gaps) // 2] / 2.0) if gaps else 0.005
    rows = []
    for b in sorted(boxes, key=lambda b: (-b['y'], b['x'])):
        if rows and abs(b['y'] - rows[-1][0]['y']) < band:
            rows[-1].append(b)
        else:
            rows.append([b])
    for r in rows:
        r.sort(key=lambda b: b['x'])
    return rows


def read_ocr_page(fy, doc, page, cache, refused):
    """Name-and-amount pairs off the boxes, and a refusal for everything that will not
    pair. The page is split at the middle because it is printed in two halves; a name in
    one half is never attached to an amount in the other.
    """
    boxes = ocr_boxes(doc, page)
    if not boxes:
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'the page has no Vision reading in the archive',
                        'evidence': '0 boxes'})
        return []
    cached_money = sum(len(MONEY.findall(t)) for t in cache.get(page, []))
    money = [b for b in boxes if OCR_MONEY.match(b['t'])]
    # THE PAGE RENDERING IS NOT THE SAME FACT AS THE PAGE BEING READ, and conflating them
    # cost FY2011 all 80 of its wage rows on 28 September 2026. The page cache was rebuilt
    # that day against OCR four weeks newer, so p98 started rendering -- 138 money figures
    # -- and this guard refused it for "being read twice". It was not: `wage_pages()` never
    # finds that page, because its heading OCRs as `N H H WAGES` and the pattern wants
    # `gross wages`. So the line path reads nothing there and this was the only reader.
    #
    # Ask the question that matters instead: does the LINE PATH actually claim this page?
    if cached_money > 5 and page in wage_pages(cache, fy):
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'this page now renders in the page cache and is being '
                                  'read twice; take it out of OCR_ONLY',
                        'evidence': '%d money figures in the cache, %d in the boxes'
                                    % (cached_money, len(money))})
        return []
    rows, unpaired = [], 0
    for band in _bands(boxes):
        for lo, hi in ((0.0, 0.5), (0.5, 1.0)):
            half = [b for b in band if lo <= b['x'] < hi]
            names = [b for b in half if OCR_NAME.match(b['t'])]
            amts = [b for b in half if OCR_MONEY.match(b['t'])]
            depts = [b for b in half if OCR_DEPT.match(b['t'])]
            if len(names) == 1 and len(amts) == 1:
                rows.append(dict(fy=fy, page=page, name=names[0]['t'].strip(),
                                 amount='%.2f' % float(
                                     OCR_MONEY.match(amts[0]['t']).group(1).replace(',', '')),
                                 department=depts[0]['t'].title() if len(depts) == 1 else '',
                                 as_printed=' '.join(b['t'] for b in half)[:160]))
            elif names or amts:
                unpaired += 1
    if not rows:
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'no name on the page could be paired with an amount',
                        'evidence': '%d boxes, %d of them money, %d of them a personal '
                                    'name; the department words that remain (%s) cannot '
                                    'be attributed to anybody'
                                    % (len(boxes), len(money),
                                       sum(1 for b in boxes if OCR_NAME.match(b['t'])),
                                       ', '.join(sorted({b['t'].upper() for b in boxes
                                                         if OCR_DEPT.match(b['t'])})[:6]))})
    elif unpaired:
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'a half-row held a name without an amount, or an amount '
                                  'without a name, and was not guessed at',
                        'evidence': '%d half-rows paired, %d refused; Vision reads %d '
                                    'names against %d money figures on the page'
                                    % (len(rows), unpaired,
                                       sum(1 for b in boxes if OCR_NAME.match(b['t'])),
                                       len(money))})
    return rows


# ======================================================================================
# THE PAGES WHOSE NAMES ARE PRINTED AS TWO WORDS -- read by measured geometry
# ======================================================================================
#
# `read_ocr_page` above pairs a name with an amount and expects the name in ONE box:
# `OCR_NAME` wants `SURNAME, GIVEN` with the comma printed. FY2019 does not print the
# comma. Its list sets six columns -- surname, given name, amount, and the same again --
# so Vision returns `RHODES` `GARRY` `12,661.62` as three boxes, and no pattern over a
# single box can see a person in that.
#
# TJ, 28 September 2026, reading the document himself: *"i see the gross wage table
# starting on pdf page 197 and ending on page 203, and i dont see any loss of info."*
#
# HE WAS RIGHT AND FOUR RECORDED REASONS WERE WRONG. What the archive said about these
# pages, against what the pages hold:
#
#   "mid-table continuation, no header printed"   every one of the seven prints
#                                                 `CALENDAR YEAR 2019 WAGES`
#   "the two-column layout loses a third to a     both columns carry them; the boxes were
#    half of the given names"                     missing from OUR CACHE, not the page
#   "a stray ZRATE in the surname x-position"     ZRATE is the last surname in the list
#   p203 defective                                the list runs out of names, so the
#                                                 right-hand column is empty. Correct
#
# The cache was the whole of it. It held 871 boxes for the seven pages where a re-read
# gives 1,753, and on pages 201 and 202 it held the surname column and NOTHING ELSE --
# zero money boxes against 94 printed. Somebody measured that and wrote it down as a fact
# about how the town sets the page. Rule 13c: a matcher that finds nothing is a statement
# about our instrument, and this one had been restated twice in `money-gaps.csv`.
#
# It is not a resolution problem. Page 202 re-read at scale 2.0, 3.0 and 4.0 gives 94
# money boxes every time, against 0 cached.
#
# WHAT PROVES A ROW HERE. A wage page prints no total -- checked box by box on all seven;
# the list ends `ZRATE SEAN 142,893.22` and then the page number -- so there is no
# arithmetic to foot against and every row stays `no check`. Two things stand in for it,
# and neither is a reconciliation:
#
#   THE PAIRING. A row is written only where one amount and at least two name words sit in
#   one printed row on one side of the page. Anything else is refused and counted.
#
#   THE ALPHABET. The list is ordered, and that is an identity the table states about
#   itself -- ABARE on 197 through ZRATE on 203. A row banded onto its neighbour, or a
#   figure taken from the wrong half of the page, breaks the order. So the order is
#   asserted per column and a page that breaks it is refused rather than published. It
#   proves the ASSIGNMENT. It says nothing about whether a digit was read correctly.

# The reports that are BORN DIGITAL, with the pages their wage list is printed on. A
# year listed here is read from the text layer and never recognised.
TEXT_LAYER = {
    '2025': ('4130-fy-2025-annual-town-report.pdf', list(range(177, 183))),
}

SPLIT_NAME = {
    '2019': ('4126-fy-2019-annual-town-report.pdf', list(range(197, 204))),
}
HEADER_BAND = 0.86        # the running head sits above this; the list is below it
MIN_PAIRS = 8             # below this a measurement is REFUSED, never defaulted to zero
WORD = re.compile(r"^[A-Z][A-Za-z'\-\.]*$")


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


def row_pitch(boxes, slope):
    """The page's own row pitch, measured on the LEFTMOST column -- rule 13b #2.

    Not a constant, and not measured over every box on the page: the surname column prints
    exactly one box per row, so its gaps ARE the pitch. Measured over all boxes it
    collapses, because two boxes of one printed row differ by a fraction of a line and drag
    the median under a real gap -- which banded FY2019 p199 into 70 rows for 47 printed.
    """
    for b in boxes:
        b['Y'] = b['y'] - slope * b['x']
    x0 = min(b['x'] for b in boxes)
    col = sorted((b['Y'] for b in boxes if b['x'] < x0 + 0.04), reverse=True)
    gaps = sorted(a - b for a, b in zip(col, col[1:]) if 0.004 < a - b < 0.06)
    if len(gaps) < MIN_PAIRS:
        return None
    return statistics.median(gaps)


def unread_block(boxes, pitch):
    """A run of printed rows Vision did not read AT ALL, measured rather than inferred.

    FY2019 p200 reads 25 surnames where its neighbours read 47, and the missing ones are
    not scattered: a single gap of 0.353 sits between `LANDI` and `LEVASSEUR`, about 22
    rows of one column that produced no box of any kind. A page short because the list
    ended and a page short because the scan lost a band are different facts about the
    archive, and only the gap tells them apart. Returned as evidence, never repaired.
    """
    x0 = min(b['x'] for b in boxes)
    col = sorted(((b['Y'], b['t']) for b in boxes if b['x'] < x0 + 0.04), reverse=True)
    worst = None
    for (ya, ta), (yb, tb) in zip(col, col[1:]):
        if ya - yb > pitch * 3 and (worst is None or ya - yb > worst[0]):
            worst = (ya - yb, ta, tb)
    if not worst:
        return ''
    return '; %d printed row(s) between %s and %s produced no box at all (a gap of %.4f ' \
           'against a measured pitch of %.5f)' % (
               round(worst[0] / pitch) - 1, worst[1], worst[2], worst[0], pitch)


def _side_of(row, side):
    return row.get('_side') == side


def read_words_page(fy, doc, page, refused):
    """Rows off the word boxes, for a list that prints the name as two words.

    Measure the rotation, band at half the page's own pitch, split at the gutter, pair --
    and refuse, with a count, everything that will not pair.
    """
    def bail(reason, evidence):
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll', 'reason': reason, 'evidence': evidence})
        return []

    boxes = [b for b in ocr_boxes(doc, page) if b['y'] < HEADER_BAND]
    if not boxes:
        return bail('the page has no Vision reading in the archive', '0 boxes')
    slope, pairs = measured_skew(boxes)
    if slope is None:
        return bail('the page rotation could not be measured, so its rows cannot be banded',
                    '%d box(es); only %d usable neighbour pair(s), %d needed'
                    % (len(boxes), pairs, MIN_PAIRS))
    pitch = row_pitch(boxes, slope)
    if pitch is None:
        return bail('the page row pitch could not be measured, so its rows cannot be banded',
                    '%d box(es); fewer than %d gaps in the label column'
                    % (len(boxes), MIN_PAIRS))
    printed = []
    for b in sorted(boxes, key=lambda b: (-b['Y'], b['x'])):
        if printed and abs(b['Y'] - printed[-1][0]['Y']) < pitch / 2.0:
            printed[-1].append(b)
        else:
            printed.append([b])
    rows, unpaired, sides = [], 0, {0: [], 1: []}
    for r in printed:
        for side, (lo, hi) in enumerate(((0.0, 0.5), (0.5, 1.0))):
            half = sorted([b for b in r if lo <= b['x'] < hi], key=lambda b: b['x'])
            if not half:
                continue
            words = [b for b in half if not OCR_MONEY.match(b['t'])]
            amts = [b for b in half if OCR_MONEY.match(b['t'])]
            if len(words) >= 2 and len(amts) == 1 and all(WORD.match(w['t']) for w in words):
                row = dict(fy=fy, page=page,
                           name=' '.join(w['t'] for w in words),
                           amount='%.2f' % float(
                               OCR_MONEY.match(amts[0]['t']).group(1).replace(',', '')),
                           department='',
                           as_printed=' '.join(b['t'] for b in half)[:160])
                row['_side'] = side
                rows.append(row)
                sides[side].append(words[0]['t'])
            else:
                unpaired += 1
    money = sum(1 for b in boxes if OCR_MONEY.match(b['t']))
    if not rows:
        return bail('no name on the page could be paired with an amount',
                    '%d box(es) in %d printed row(s), %d of them money'
                    % (len(boxes), len(printed), money))
    # THE ALPHABET, ASSERTED PER COLUMN -- and the response GRADED, because one inversion
    # and fifty are different findings.
    #
    # An out-of-order surname means the row was misassigned OR the surname was misread,
    # and the order alone cannot tell which. The COUNT can. A banding failure or a figure
    # taken from the wrong half puts a page comprehensively out of order; a scanner
    # dropping a character puts one name out of place and leaves the other thirty-three
    # exactly where the town printed them.
    #
    # The first draft of this check refused the whole page on any inversion and threw away
    # all 34 rows of FY2019 p203 for `ZAMORA -> IZIVOJINOVIC` -- which is `ZIVOJINOVIC`
    # with a leading `I` hallucinated by the scanner, on the last page of the alphabet.
    # That is the shape this project keeps having to correct: a check that cannot tell our
    # instrument from the document reported one as the other.
    #
    # So: past the threshold the PAGE is refused, because the assignment is not trustworthy.
    # Under it the offending ROWS are dropped and counted, because the page is fine and one
    # name is not.
    for side, names in sides.items():
        bad = [(a, b) for a, b in zip(names, names[1:]) if a > b]
        if not bad:
            continue
        where = 'left' if side == 0 else 'right'
        if len(bad) > max(2, len(names) // 20):
            return bail('the surnames read off this column are not in the order the list '
                        'prints them, so rows have been misassigned',
                        '%d inversion(s) in %d name(s) on the %s column, first at '
                        '%s -> %s' % (len(bad), len(names), where, bad[0][0], bad[0][1]))
        drop = {b for _, b in bad}
        rows = [r for r in rows
                if not (r['name'].split()[0] in drop and _side_of(r, side))]
        refused.append({
            'report_fy': fy, 'document': doc, 'page': page, 'subject': 'payroll',
            'reason': 'a surname was read out of the order the list prints it, so that '
                      'row was dropped rather than published under a name we may have '
                      'misread',
            'evidence': '%d inversion(s) in %d name(s) on the %s column: %s'
                        % (len(bad), len(names), where,
                           ', '.join('%s -> %s' % p for p in bad))})
    if unpaired:
        refused.append({
            'report_fy': fy, 'document': doc, 'page': page, 'subject': 'payroll',
            'reason': 'a printed row held a name without an amount, or an amount without '
                      'a name, and was not guessed at',
            'evidence': '%d row(s) paired, %d refused; Vision reads %d box(es) in %d '
                        'printed row(s), %d of them money%s'
                        % (len(rows), unpaired, len(boxes), len(printed), money,
                           unread_block(boxes, pitch))})
    for r in rows:
        r.pop('_side', None)
    return rows




# ======================================================================================
# HALF THESE REPORTS ARE NOT SCANS, AND WE WERE RECOGNISING THEM ANYWAY
# ======================================================================================
#
# TJ, 28 September 2026, on FY2025's wage pages reading 532 names where the page prints
# 612: *"i want to know how we read pages 177, 178 and 179, but didnt read 180, 181, and
# 182"* -- the six pages being identical in form.
#
# They are identical. The difference was never the pages. FY2025's report is BORN DIGITAL:
# every one of those pages carries an exact text layer, 301 to 315 words with exact
# coordinates, and we were rendering each to an image and running character recognition
# over it. Vision happened to read three of the six well and dropped most of page 181's
# right-hand NAME column -- not because the print is faint, but because recognition is a
# guess and the characters were sitting in the file all along.
#
# Eight of the sixteen annual reports are digital: FY2014, FY2015, FY2016, FY2017, FY2018,
# FY2020, FY2024, FY2025. The other eight are scans and still need Vision.
#
# The cost of not asking: 80 people and $3,728,578 missing from FY2025 alone, and days
# spent hunting figures that were never lost.
#
# So the text layer is tried FIRST and OCR is the fallback. That is not a tuning change --
# it is a different instrument, and on a digital page it is the right one: there is
# nothing to misread.


def text_layer_pages(doc, pages):
    """Wage rows straight off a digital PDF. {} when the page has no text layer."""
    try:
        import pdfplumber
    except ImportError:
        return {}
    path = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs', doc)
    if not os.path.exists(path):
        return {}
    out = {}
    with pdfplumber.open(path) as pdf:
        for n in pages:
            if n < 1 or n > len(pdf.pages):
                continue
            words = pdf.pages[n - 1].extract_words()
            if len(words) < 40:          # a scan: nothing to read here
                continue
            lines = {}
            for w in words:
                lines.setdefault(round(w['top']), []).append(w)
            rows = []
            for top in sorted(lines):
                ws = sorted(lines[top], key=lambda w: w['x0'])
                # The list prints TWO records per line, side by side. Split at the gutter
                # rather than pairing by order: a line with one record on it would
                # otherwise take the next line's figure.
                for lo, hi in ((0, 300), (300, 10000)):
                    cell = [w for w in ws if lo <= w['x0'] < hi]
                    money = [w for w in cell if w['text'].startswith('$')]
                    names = [w for w in cell if not w['text'].startswith('$')]
                    if len(money) == 1 and names:
                        rows.append({
                            'name': ' '.join(w['text'] for w in names),
                            'amount': float(money[0]['text'].replace('$', '').replace(',', '')),
                            'as_printed': ' '.join(w['text'] for w in cell)[:160],
                            'printed_money': sum(1 for w in words
                                                 if w['text'].startswith('$')),
                        })
            if rows:
                out[n] = rows
    return out


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, refused = [], []
    for f in sorted(glob.glob(os.path.join(PAGES, 'FY*.ocr.txt'))):
        m = re.search(r'FY(\d{4})\.ocr', f)
        if m:
            rows += read_year(m.group(1), refused, os.path.basename(f))
    for fy in sorted(OCR_ONLY):
        doc, want = OCR_ONLY[fy]
        cache = pages(fy)
        for page in want:
            rows += read_ocr_page(fy, doc, page, cache, refused)
    for fy in sorted(SPLIT_NAME):
        doc, want = SPLIT_NAME[fy]
        for page in want:
            rows += read_words_page(fy, doc, page, refused)
    # THE TEXT LAYER WINS WHERE THERE IS ONE, and it REPLACES whatever OCR produced for
    # that page rather than adding to it -- two readings of one page are not more data.
    for fy in sorted(TEXT_LAYER):
        doc, want = TEXT_LAYER[fy]
        got = text_layer_pages(doc, want)
        if not got:
            continue
        rows = [r for r in rows if not (r['fy'] == fy and int(r['page']) in got)]
        for page, found in sorted(got.items()):
            for r in found:
                rows.append(dict(fy=fy, page=page, name=r['name'],
                                 amount='%.2f' % r['amount'], department='',
                                 as_printed=r['as_printed'],
                                 _printed_money=r['printed_money']))
    grade(rows)
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
