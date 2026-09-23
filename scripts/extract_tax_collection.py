#!/usr/bin/env python3
"""The Collector's receivables: what was committed, collected, abated and still owed.

    python3 scripts/extract_tax_collection.py
    python3 scripts/extract_tax_collection.py --check
    python3 scripts/extract_tax_collection.py --page 4130-fy-2025 41   # read one page aloud

Writes `sources/data/tax-collection.csv` and, beside it,
`sources/data/tax-collection-unreconciled.csv` -- the years this refuses to publish, with
the reason each one was refused.

--------------------------------------------------------------------------------------
WHAT THE TABLE IS
--------------------------------------------------------------------------------------

Every annual town report prints `COLLECTION OF TAXES / RECEIVABLES SUMMARY`, one line per
receivable -- real estate by levy year, personal property by levy year, motor vehicle
excise by levy year, then the betterments, the liens, the user charges -- and eight
columns across:

    FORWARD  +  COMMITTMENTS  +/- (the five movement columns)  =  BALANCES

The town spells it `COMMITTMENTS` and `APPROTIONED`; both are kept as printed wherever
this file quotes the page.

It is the one table in the book that states what is OWED rather than what was spent, and
it is a receivable, not revenue: `LEVY OF 2007` still carrying $71.57 in FY2024 is a
fifteen-year-old unpaid bill, not money collected in 2024.

--------------------------------------------------------------------------------------
WHAT PROVES A ROW, AND WHAT PROVES A YEAR
--------------------------------------------------------------------------------------

Two things, and neither is a tolerance anybody tuned.

**A ROW FOOTS ACROSS.** The seven movement columns sum to the balance the table itself
prints at the end of the row, with the credits already printed in parentheses. A misread
digit does not survive that -- which is the only reason it is safe to read a scan at all.
A row that does not close is not published.

**A YEAR FOOTS DOWN.** The last page prints `GRAND TOTAL`, and the detail rows have to
sum to it in every one of the eight columns. That is rule 13's "when an extract has a
total the source itself prints, reconcile to it", and it is a far harder test than the
row check: it fails if a single row anywhere in the table was missed, so it catches the
silent loss -- the row that was never read at all -- which no per-row identity can.

A year that does not tie is REFUSED WHOLE and written to the unreconciled register with
its per-column shortfall. Publishing the rows that happened to close out of a table that
does not add up would be publishing an unknown fraction of a receivable and calling it
the receivable.

--------------------------------------------------------------------------------------
THE THREE THINGS THAT MAKE THE PAGE HARD
--------------------------------------------------------------------------------------

**1. THE COLUMN ORDER CHANGED, and it changed silently.** FY2011 through FY2018 print

    FORWARD COMMITTMENTS ADJUSTMENTS REFUNDS PAYMENTS ABATEMENTS TRANSFER BALANCES

and FY2019 onward print

    FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS TRANSFER ADJUSTMENTS BALANCES

Both foot the same way, so an extractor that assumed one order would produce a table
that adds up perfectly and calls payments abatements. Every layout below was READ off
the report's own printed header and written down, with the header line quoted beside it,
exactly as `read_trust_table.LAYOUTS` records the trust tables -- never inferred from
position, which is what `column_meaning` exists in this archive to forbid.

**2. THE HEADER IS OFTEN ONE BOX OVER SEVERAL COLUMNS.** Vision returns FY2024's header
as `COMMITIMENTS ABATEMENTS` and `TRANSFER ADJUSTMENTS BALANCES`, and FY2015's as one
box holding seven words. So a word's position inside its box is used to place the
column -- by character offset, an estimate, and stated as one. It is used ONLY for
POSITION. The NAME comes from the written-down layout, and where a header word is missing
altogether the position is interpolated between its neighbours. Neither can invent
agreement: the row still has to foot and the year still has to tie.

**3. FINDING THE ROWS TAKES THREE MEASUREMENTS AND NO CONSTANTS.** A figure in
parentheses descends below its line and a label does not, so `(205,072.00)` sits five
thousandths below `LEVY OF 2025` on the same row -- more than half the row pitch -- which
is why a box is placed by its CENTRE and not its bottom. A scanned page is turned, and on
FY2013 page 83 the turn is a whole row's worth from the left margin to the right, which is
why the SKEW is fitted through the header, the one line on the page every word of which
can be named. And the table prints a blank line between groups, so half the gaps on the
page are two rows rather than one, which is why the PITCH is the smallest step that
recurs among the row labels rather than the median of all of them. Each of the three was
found by a year being refused for something that looked like bad arithmetic.

--------------------------------------------------------------------------------------
TWO INSTRUMENTS, AND THE PAGE DECIDES WHICH
--------------------------------------------------------------------------------------

**Four of these reports are not scans at all, and reading them as scans threw away most
of the table.** FY2014, FY2015, FY2016 and FY2025 carry a real text layer -- every figure
in the file, exact, to the cent -- and they are the three years published here plus the
one the town cropped. The OCR of FY2025 page 40 recovered ten figures off a
page that holds a hundred and ninety-four, and the year was refused for rows that "do not
foot" when the truth was that seven of their eight columns had never been read.

So each page is read with the better of two instruments, and which one it was travels
with every row in the `instrument` column -- rule 13: an instrument that reformats before
you see it is part of the finding.

    text layer   pdfplumber word boxes, exact                  FY2014-FY2016, FY2025
    ocr          Apple Vision line boxes at raster scale 6.0   the rest

Every year read off a text layer ties. No year read off OCR does, and the shortfall is
always the same shape: figures the scanner never returned at all. FY2024 page 38 prints a
BALANCE FORWARD against thirty-eight rows and Vision gives back the balance alone.

**And three of the four text-layer pages are drawn sideways.** FY2014's and FY2016's
tables are landscape content on a portrait page with no `/Rotate` to say so, so the words
come back as `GRUBNENUL` and `SEXAT` -- the right characters, upside down. The rotation is
DECIDED BY MEASUREMENT rather than read off the file, exactly as `ocr_pdf.swift` decides
it: the page is turned to each of the four quarters and the one that yields the most
words the table is known to print is the one that is used.

--------------------------------------------------------------------------------------
THE SAME TABLE IS ALSO READ BY `extract_receivables.py`, AND THIS DEFERS TO IT
--------------------------------------------------------------------------------------

Two readers of one table landed the same afternoon. `sources/data/receivables.csv`
publishes FY2017, FY2018, FY2020, FY2021, FY2022 and FY2023, each proved to the same
printed GRAND TOTAL; this file does not read those years again, and the register beside
it says so year by year. What is here is the half that reader refused: the years whose
pages carry a text layer, which is the instrument that recovers them.

Anyone merging the two should merge the READERS, not the files. The column names differ
(`balance_forward` there, `forward` here) and nothing but confusion is served by two
series of one table.

--------------------------------------------------------------------------------------
WHAT IS NOT HERE, AND WHY
--------------------------------------------------------------------------------------

**Nothing is reported missing from a count.** An earlier draft of this file said in so
many words that FY2011, FY2019 and FY2020 "have no word geometry" and named the page
ranges. They have it. Python's csv module treats an inch mark in a scanned line as an
opening quote and swallows everything up to the next one, and those three reports lost
whole spans of pages to it -- a defect in the READER, published as a fact about the town.
See `read_boxes`.

**The FY2016 addendum reprints the table at a larger scale and crops it.** Its header
ends at ABATEMENTS; TRANSFER and BALANCES are off the right edge of the page. The full
table is in the main FY2016 report and that is what is read.

**A grain warning.** The row label is the page's own, verbatim. `LEVY OF 2025` appears
under REAL ESTATE, under PERSONAL PROPERTY and under MOTOR VEHICLE EXCISE, so the
`section` column carries the nearest preceding label that is not itself a `LEVY OF` line
-- the document's own grouping, taken from its own order, not from a list of categories
somebody typed.
"""
import argparse
import collections
import csv
import glob
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read_trust_table import MONEY, money, split_merged, skew   # noqa: E402

# SOME OCR LINES ARE ENORMOUS -- a whole debt schedule returned as one observation runs
# past Python's default 131,072-character field limit, and the reader dies on a page it
# does not even want.
csv.field_size_limit(10 ** 9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
PDFS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
OUT = os.path.join(ROOT, 'sources', 'data', 'tax-collection.csv')
# THE SAME TABLE, READ BY SOMEBODY ELSE. `extract_receivables.py` landed the same
# afternoon as this and publishes the same eight columns off the same pages for the years
# it could prove. One table must not become two series, so a year that file already
# publishes -- proved to the same printed GRAND TOTAL -- is not read again here, and the
# register beside this says which file to go to for it.
SIBLING = os.path.join(ROOT, 'sources', 'data', 'receivables.csv')
OUT_BAD = os.path.join(ROOT, 'sources', 'data', 'tax-collection-unreconciled.csv')

FIELDS = ['fy', 'section', 'item', 'forward', 'committed', 'adjustments', 'refunds',
          'payments', 'abatements', 'transfer', 'balance', 'proof', 'page', 'instrument',
          'document']
BAD_FIELDS = ['fy', 'pages', 'why', 'document']

# The seven that move a receivable, and the one they land in. The credits are printed in
# parentheses on the page, so this is a sum and not an alternating sign.
MOVERS = ['forward', 'committed', 'adjustments', 'refunds', 'payments', 'abatements',
          'transfer']
BALANCE = 'balance'

# WHAT EACH YEAR'S COLUMNS ARE, READ OFF ITS OWN PRINTED HEADER AND WRITTEN DOWN.
#
# The quoted line beside each is what Vision returned for that report's header row, and
# it is the evidence for the order. Where the OCR merged words into one box the merge is
# shown as it came, because that merge is the reason the order cannot be taken from the
# number of boxes.
LAYOUT_A = ['forward', 'committed', 'adjustments', 'refunds', 'payments', 'abatements',
            'transfer', 'balance']
LAYOUT_B = ['forward', 'committed', 'abatements', 'payments', 'refunds', 'transfer',
            'adjustments', 'balance']
LAYOUTS = {
    # FY2011 p78:  COLLECTION OF TAXES FORWARD COMMITTMENTS ADJUSTMENTS REFUNDS PAYMENTS
    #              ABATEMENTS TRANSFER BALANCES
    2011: LAYOUT_A,
    # FY2012 p78:  FORWARD COMMITTMENTS [ADJUSTMENTS] REFUNDS PAYMENTS ABATEMENTS
    #              TRANSFER BALANCES   (ADJUSTMENTS dropped by OCR on p78; it is printed,
    #              and p77 carries the same header in a sliver at the foot of the sheet
    #              with ADJUSTMENTS at x=0.384 -- where interpolation puts it, 0.3845)
    2012: LAYOUT_A,
    # FY2013 p83:  FORWARD COMMITTMENTS ADJUSTMENTS REFUNDS PAYMENTS ABATEMENTS
    #              TRANSFER BALANCES
    2013: LAYOUT_A,
    # FY2014 p43:  FISCAL YEAR FORWARD COMMITIMENTS ADJUSTMENTS REFUNDS PAYMENTS
    #              ABATEMENTS TRANSFERS BALANCES
    2014: LAYOUT_A,
    # FY2015 p44:  FISCAL YEAR FORWARD | COMMITTMENTS DJUSTMENT REFUNDS PAYMENTS
    #              ABATEMENTS TRANSFER BALANCES   (one box, seven words)
    2015: LAYOUT_A,
    # FY2016 p47:  FISCAL YEAR FORWARD | COMMITTMENTS ADJUSTMENTS | REFUNDS PAYMENTS
    #              ABATEMENTS TRANSFER BALANCES
    2016: LAYOUT_A,
    # FY2017 p44:  FISCAL YEAR FORWARD | COMMITTMENTS ADJUSTMENTS | REFUNDS PAYMENTS
    #              ABATEMENTS TRANSFER BALANCES
    2017: LAYOUT_A,
    # FY2018 p52:  FISCAL YEAR FORWARD COMMITTMENTS ADJUSTMENTS REFUNDS PAYMENTS
    #              ABATEMENTS TRANSFER BALANCES                <- the last year of this order
    2018: LAYOUT_A,
    # FY2019 p54:  FISCAL YEAR FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS
    #              TRANSFER ADJUSTM[ENTS]                      <- the order changes here,
    #              and BALANCES is off the right edge of all three pages
    2019: LAYOUT_B,
    # FY2020 p47:  FISCAL YEAR FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS
    #              TRANSFER ADJUSTMENTS BALANCES
    2020: LAYOUT_B,
    # FY2021 p48:  FISCAL YEAR FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS
    #              TRANSFER ADJUSTMENTS BALANCES
    2021: LAYOUT_B,
    # FY2022 p50:  FISCAL YEAR FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS
    #              TRANSFER ADJUSTMENTS BALANCES
    2022: LAYOUT_B,
    # FY2023 p56:  FISCAL YEAR FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS
    #              TRANSFER ADJUSTMENTS BALANCES
    2023: LAYOUT_B,
    # FY2024 p39:  FISCAL YEAR FORWARD | COMMITTMENTS ABATEMENTS | PAYMENTS REFUNDS
    #              TRANSFER ADJUSTMENTS BALANCES
    2024: LAYOUT_B,
    # FY2025 p40:  FISCAL YEAR FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS
    #              TRANSFER ADJUSTMENTS BALANCES
    2025: LAYOUT_B,
}

# HOW THE HEADER WORDS COME BACK OFF A SCAN. Every spelling here was observed; none is a
# guess at what a scanner might do. `COMMITTMENTS` is the town's own spelling.
HEADER_WORD = {
    'FORWARD': 'forward',
    'COMMITTMENTS': 'committed', 'COMMITIMENTS': 'committed', 'COMMITMENTS': 'committed',
    'ADJUSTMENTS': 'adjustments', 'ADIUSTMENTS': 'adjustments',
    'DJUSTMENT': 'adjustments', 'DJUSTMENTS': 'adjustments', 'ADJUSTMENT': 'adjustments',
    'REFUNDS': 'refunds',
    'PAYMENTS': 'payments',
    'ABATEMENTS': 'abatements',
    'TRANSFER': 'transfer', 'TRANSFERS': 'transfer',
    'BALANCES': 'balance',
}
HEADER_RE = re.compile('|'.join(sorted(HEADER_WORD, key=len, reverse=True)))
LABEL_RE = re.compile(r'FISCAL\s+YEAR', re.I)
GRAND = re.compile(r'^GRAND\s*TOTALS?$', re.I)
TITLE = re.compile(r'COLLECTION OF TAXES|RECEIVABLES SUMMARY', re.I)
# A DASH IS A PRINTED ZERO. These are accounting tables and they set nothing in a cell
# that holds nothing: FY2014 prints `$ -` for the balance on four rows whose movements
# cancel, and a reader that sees no balance there cannot close the row. Four rows, and
# they were the whole of that year's refusal.
DASH = re.compile(r'^[$S]?\s*[-‐-―_]$')
LEVY = re.compile(r'^LEVY\s+OF\b', re.I)
UNNAMED = '(the page prints no name for this line)'
# A LABEL IS EVERY WORD OF IT. The `$` a column prints to the left of its figure falls
# left of the first column's own start, so it was read as part of the row's name -- and
# `GRAND TOTAL $` is not the control row. Filtering to boxes that contain a LETTER fixed
# that and broke something quieter: FY2014 names its rows `1997 MVE`, in two boxes, and
# sixty-nine rows came out called `MVE`. So what is dropped is the ornament, by name.
ORNAMENT = re.compile(r'^[$S|\s]*$')
JUNE30 = re.compile(r'JUNE\s*30,?\s*(\d{4})', re.I)

# A row's figures have to close on the balance the row itself prints. A cent of rounding
# is all the slack there is, because both sides are printed to the cent.
TOL = 0.02
# The year's own GRAND TOTAL, against the sum of every row under it. Eight columns of
# forty-odd rows each, so the slack is a few cents, not a few dollars.
TOL_YEAR = 0.05


def read_boxes(path):
    """Every recognised line in a report, by page.

    QUOTE_NONE, AND IT IS NOT A DETAIL. These TSVs hold scanned text, and scanned text
    holds inch marks: a box reading `6" PIPE` opens a quoted field to Python's csv module,
    which then swallows every following physical line until it meets the next quote. Read
    with the default dialect, FY2011 lost pages 71-82, FY2019 lost 53-59 and FY2020 lost
    45-55 -- and each of those is a table this project would have reported the town as not
    having printed. Rule 13c: a reader that finds nothing is a statement about the reader.
    The file has no quoting and no escaping; it is tabs, and it is read as tabs.
    """
    pages = collections.defaultdict(list)
    with open(path, newline='') as fh:
        rd = csv.reader(fh, delimiter='\t', quoting=csv.QUOTE_NONE)
        head = next(rd)
        for row in rd:
            if len(row) != len(head):
                continue
            b = dict(zip(head, row))
            try:
                for k in ('x', 'y', 'w', 'h', 'conf'):
                    b[k] = float(b[k])
                pg = int(b['page'])
            except ValueError:
                continue
            b['text'] = (b['text'] or '').strip()
            pages[pg].append(b)
    return pages


# WORDS THE TABLE IS KNOWN TO PRINT, used to decide which way up a page is drawn. Not a
# spelling test on the whole page -- a quarter turn either way returns the same characters
# in the same quantity, and only the reading direction tells them apart.
UPRIGHT_WORDS = ('TOWN', 'LUNENBURG', 'FISCAL', 'YEAR', 'FORWARD', 'BALANCES', 'LEVY',
                 'TAXES', 'COLLECTION', 'RECEIVABLES', 'SUMMARY', 'TRANSFER', 'GRAND')
# Two words a hair apart are one figure the extractor split: `(` and `13,292.77)`, or `4`
# and `,964.08`. In points, on a page whose columns are sixty points apart.
#
# ONLY FIGURES ARE GLUED. The first version glued anything that close and turned `FISCAL
# YEAR` into `FISCALYEAR` and `GRAND TOTAL` into `GRANDTOTAL` -- which cost the control
# row, because the thing that identifies it is its name.
GLUE_PT = 2.0
NUMERISH = re.compile(r'^[-($]?[\d,. ]*[\d)]?$')


def text_boxes(pdf_path, page):
    """Word boxes off a page's own text layer, or None if it has none.

    Returns boxes in the same shape the OCR geometry uses -- x, y, w, h as fractions of
    the page with the origin at the BOTTOM left -- so that one reader serves both.
    """
    try:
        import pdfplumber
        import pypdf
    except ImportError:
        return None
    # ALL FOUR QUARTERS, EVERY PAGE. An earlier version remembered the quarter that won
    # for a document and tried that first, and one report's pages are not all drawn the
    # same way up: FY2015's page 22 is sideways and its page 44 is not, so the table was
    # read at a quarter turn -- 153 figures, in the wrong places, no rows at all, and the
    # year reported as a page nobody could find. The cost of being sure is one second a
    # page, and only the table's own pages are ever read.
    best, best_score = None, 0
    for angle in (0, 90, 180, 270):
        try:
            if angle:
                import io
                r = pypdf.PdfReader(pdf_path)
                w = pypdf.PdfWriter()
                w.add_page(r.pages[page - 1])
                w.pages[0].rotate(angle)
                buf = io.BytesIO()
                w.write(buf)
                buf.seek(0)
                with pdfplumber.open(buf) as pdf:
                    pg = pdf.pages[0]
                    words, size = pg.extract_words(), (pg.width, pg.height)
            else:
                with pdfplumber.open(pdf_path) as pdf:
                    pg = pdf.pages[page - 1]
                    words, size = pg.extract_words(), (pg.width, pg.height)
        except Exception:
            continue
        score = sum(1 for w in words if w['text'].upper() in UPRIGHT_WORDS)
        if score > best_score:
            best, best_score = (words, size, angle), score
    if not best or best_score < 3:
        return None
    words, (pw, ph) = best[0], best[1]

    # Glue the pieces of a split figure back together, and only those: a gap of two
    # points on a page whose columns stand sixty apart cannot be a column boundary.
    words.sort(key=lambda w: (round(w['top'], 1), w['x0']))
    out = []
    for w in words:
        if out and abs(out[-1]['top'] - w['top']) < 1.0 \
                and 0 <= w['x0'] - out[-1]['x1'] < GLUE_PT \
                and NUMERISH.match(out[-1]['text']) and NUMERISH.match(w['text']):
            out[-1] = dict(out[-1], text=out[-1]['text'] + w['text'], x1=w['x1'])
            continue
        out.append(dict(w))
    return [{'text': w['text'].strip(),
             'x': w['x0'] / pw, 'w': (w['x1'] - w['x0']) / pw,
             'y': (ph - w['bottom']) / ph, 'h': (w['bottom'] - w['top']) / ph,
             'conf': 1.0} for w in out if w['text'].strip()]


def header_slope(boxes):
    """The page's tilt, fitted through the one line we can name every word of."""
    words = sorted(header_words(boxes), reverse=True)
    groups, cur = [], []
    for c in words:
        if cur and cur[0][0] - c[0] > 0.03:
            groups.append(cur)
            cur = []
        cur.append(c)
    if cur:
        groups.append(cur)
    best = max(groups, key=lambda g: len({n for _c, n, _x in g}), default=[])
    xs = [x for _c, _n, x in best]
    ys = [c for c, _n, _x in best]
    if len(best) < 5 or max(xs) - min(xs) < 0.3:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else None


def centre(b):
    """Where a box sits vertically, once the page's own turn is taken out of it.

    Two corrections, and both are measured rather than chosen. The CENTRE, not the
    bottom, because a figure in parentheses descends below its line and a label does not,
    which on FY2025 page 40 puts `(205,072.00)` five thousandths below `LEVY OF 2025` on
    the same row -- more than half the row pitch. And the SKEW, because a scan is
    slightly turned: FY2012's header drifts a whole row's worth from `COLLECTION OF
    TAXES` at the left margin to `BALANCES` at the right, so the header was read as five
    separate rows and the page was refused for printing only half its columns.
    """
    return b.get('c', b['y'] + b['h'] / 2.0)


def deskew(boxes):
    """Measure the page's rotation, and take it out.

    THE HEADER IS THE BEST RULER ON THE PAGE, and it is the only line on it that is
    KNOWN to be one line: eight named words, left to right, right across the sheet.
    `read_trust_table.skew` measures the median slope between neighbouring figures, which
    is the right tool where the figures are all a reader has -- but on FY2013 page 83 it
    recovered about half the true tilt, and half a tilt across half a page is most of a
    row. Every balance on that page attached to the row above its own, eighty-two rows
    read, eighty-two refused, and nothing about them looked like a rotation.

    So where the page prints a header this fits a line through it; where it does not, the
    figures answer, as before.
    """
    for b in boxes:
        b.pop('c', None)
    slope = header_slope(boxes)
    if slope is None:
        slope = skew(boxes)
    for b in boxes:
        b['c'] = b['y'] + b['h'] / 2.0 - slope * (b['x'] + b['w'] / 2.0)
    return boxes


def pitch_of(gaps):
    """The page's own row pitch: the LARGEST step that explains every gap as a whole
    number of rows.

    Rule 13b's second rule says to take the median gap between consecutive rows and halve
    it, and the median is wrong on exactly these pages: the table prints a blank line
    between REAL ESTATE and PERSONAL PROPERTY and between every group of betterments, so
    on FY2014 page 44 more than half the gaps are DOUBLE the row pitch and the median
    lands on 0.0408 against a true pitch of 0.0204. The band came out a whole row wide
    and `DEFERRED SWR BETT` and `DEFERRED SWR INT` were read as one row.

    A gap is one row, or two, or five, so what is wanted is the SMALLEST gap the page
    prints OFTEN -- one row -- and not the commonest gap, which on a page with many blank
    lines is two. Taking the smallest that recurs, rather than the smallest full stop, is
    what stops a single stray observation from setting the band.
    """
    if len(gaps) < 4:
        return 0.01
    need = max(3, int(0.2 * len(gaps)))
    for g in sorted(gaps):
        if sum(1 for h in gaps if 0.8 * g <= h <= 1.2 * g) >= need:
            return g
    return statistics.median(gaps)


def band_rows(boxes):
    """Group boxes into printed rows, around the row labels the page prints.

    THE BAND IS MEASURED, AND IT IS MEASURED OFF THE LABELS. Rule 13b says to take the
    page's own row pitch and halve it, and the gap between every pair of OBSERVATIONS is
    not that: a figure in parentheses sits a fraction below the label on its own row, so
    the gap list holds two populations -- fractions of a row, and whole rows -- and the
    band came out either a row wide (merging `DEFERRED SWR BETT` into `DEFERRED SWR INT`)
    or a tenth of one (tearing GRAND TOTAL from its own figures).

    Every row of this table begins with a label at the left margin, so those labels ARE
    the rows: their centres are the anchors, the pitch is the smallest step that recurs
    among them, and everything else on the page joins the anchor it is nearest. A figure
    that is nearer to nothing keeps its own row and is reported unread, which refuses a
    year rather than filing the figure under the wrong one.
    """
    if not boxes:
        return []
    anchors, band = row_anchors(boxes)
    rows = collections.defaultdict(list)
    for b in sorted(boxes, key=lambda b: -centre(b)):
        near = min(anchors, key=lambda a: abs(a - centre(b)))
        rows[near if abs(near - centre(b)) <= band else centre(b)].append(b)
    return [rows[k] for k in sorted(rows, reverse=True)]


def row_anchors(boxes):
    """The rows' own vertical positions, and how far a box may be from one."""
    left = min((b['x'] for b in boxes
                if not MONEY.match(b['text']) and len(b['text']) >= 3), default=0.0)
    anchors = sorted({round(centre(b), 5) for b in boxes
                      if b['x'] <= left + 0.03 and not MONEY.match(b['text'])},
                     reverse=True)
    if len(anchors) < 4:
        anchors = sorted({round(centre(b), 5) for b in boxes}, reverse=True)
    gaps = [a - b for a, b in zip(anchors, anchors[1:]) if a - b > 0.002]
    return anchors, pitch_of(gaps) * 0.6


def header_words(boxes):
    """Every header word on the page, with where its column starts.

    A word's own position inside its box, by character offset, because the scanner
    returns `COMMITIMENTS ABATEMENTS` and `TRANSFER ADJUSTMENTS BALANCES` as single
    observations. An ESTIMATE, and used for POSITION only -- the NAME comes from the
    layout read off the printed header and written down above.
    """
    out = []
    for b in boxes:
        t = b['text'].upper()
        if LABEL_RE.search(t):
            continue
        n = float(len(t)) or 1.0
        for m in HEADER_RE.finditer(t):
            out.append((centre(b), HEADER_WORD[m.group(0)],
                        b['x'] + b['w'] * (m.start() / n)))
    return out


def header_axes(boxes, layout, band):
    """Where each column starts, from the header this page prints.

    Returns `[(name, x)]` in printed order, `('short', [(name, x)])` where the page
    prints only some of the columns, or None where it prints no header at all.

    THE HEADER IS FOUND BY ITS OWN WORDS, not by first cutting the page into rows. The
    row bands are set by the labels at the left margin, and the header's own label is
    indented past them -- `COLLECTION OF TAXES` sits at x=0.078 on FY2012 page 78 where
    every row label sits at 0.048 -- so the header anchored nothing, every one of its
    words became a row of its own, and two years were refused for printing four columns
    out of eight. They print all eight.

    The words are matched against the layout IN ORDER; a word out of order, or one the
    layout does not contain, refuses the page rather than being shuffled into place. A
    column whose word did not survive the scan has its position interpolated between the
    neighbours that did -- these columns are near enough evenly spaced that FY2012's
    missing ADJUSTMENTS lands at 0.3845 against the 0.384 its own sheet prints an inch
    lower.
    """
    # THE HEADER IS ONE ROW AND IT IS THE MOST SLOPED ROW ON THE PAGE, because it is the
    # widest: FY2013 page 83 drops fifteen thousandths from FORWARD to BALANCES, twice the
    # row band, and split into three groups of fewer than four words each. So the band is
    # widened until the words make a header, and a band too wide cannot smuggle anything
    # in -- eight names, in the layout's order, at increasing x, is a test a mixture of
    # two rows does not pass.
    cands = sorted(header_words(boxes), reverse=True)
    groups, short = [], None
    for mult in (1.0, 2.5, 5.0):
        groups, cur = [], []
        for c in cands:
            if cur and cur[0][0] - c[0] > band * mult:
                groups.append(cur)
                cur = []
            cur.append(c)
        if cur:
            groups.append(cur)
        got = _axes_from(groups, layout)
        if isinstance(got, list):
            return got
        short = short or got
    return short


def _axes_from(groups, layout):
    short = None
    for g in groups:
        if g[0][0] < 0.30:          # a header in the bottom third of a sheet is the
            continue                # next page bleeding in, not this table's
        found = sorted(((x, name) for _c, name, x in g))
        if len(found) < 4:
            continue
        idx, at, bad = [], 0, False
        for x, name in found:
            while at < len(layout) and layout[at] != name:
                at += 1
            if at >= len(layout):
                bad = True
                break
            idx.append(at)
            at += 1
        if bad or len(set(idx)) != len(idx):
            continue
        known = dict(zip(idx, [x for x, _n in found]))
        lo, hi = min(known), max(known)
        axes, whole = [], True
        for i in range(len(layout)):
            if i in known:
                axes.append(known[i])
            elif lo < i < hi:
                a = max(k for k in known if k < i)
                b2 = min(k for k in known if k > i)
                axes.append(known[a] + (known[b2] - known[a]) * (i - a) / float(b2 - a))
            else:
                whole = False
                break
        if not whole:
            if short is None or len(known) > len(short[1]):
                short = ('short', [(layout[k], known[k]) for k in sorted(known)])
            continue
        if any(b <= a for a, b in zip(axes, axes[1:])):
            continue
        return list(zip(layout, axes))
    return short


def grand_axes(rows, layout):
    """Fall back to the control row: the eight figures the GRAND TOTAL line prints.

    Two pages in fifteen reports carry table rows and no header of their own -- FY2015
    p45 and FY2025 p41 -- and both print GRAND TOTAL. A row that carries exactly one
    figure per column, in order, IS the column ruler for that page, and it is the row
    everything on the page is checked against anyway.
    """
    for row in rows:
        # The name is the JOIN of the label boxes, never one of them: a text layer
        # returns `GRAND` and `TOTAL` as two words, and testing them one at a time found
        # the control row on the scanned pages and missed it on the exact ones.
        labels = ' '.join(b['text'] for b in sorted(row, key=lambda b: b['x'])
                          if not MONEY.match(b['text']))
        if not GRAND.match(re.sub(r'\s+', ' ', labels).strip()):
            continue
        figs = sorted([b for b in row if MONEY.match(b['text'])],
                      key=lambda b: b['x'] + b['w'])
        if len(figs) != len(layout):
            continue
        return list(zip(layout, [b['x'] for b in figs]))
    return None


def is_figure(b):
    return MONEY.match(b['text']) or DASH.match(b['text'])


def value(text):
    return 0.0 if DASH.match(text) else money(text)


def place(figs, axes):
    """Each figure under the column whose start it is nearest from the right.

    By POSITION, never by order -- rule 13b's third rule. A receivable with no activity
    prints nothing in five of the eight columns, so the figures that are present would
    shift left and every one would land under the wrong heading.

    The right edge is the axis because the columns are right-aligned: the widest figure
    in a column begins at the column's own left margin and every narrower one ends where
    it does.
    """
    out = {}
    for b in figs:
        r = b['x'] + b['w']
        hit = None
        for name, x in axes:
            if r >= x - 0.004:
                hit = name
        if hit is None:
            continue
        if hit in out:
            return None                    # two figures in one column: not a row we can read
        out[hit] = value(b['text'])
    return out


def table_pages(pages):
    """Which pages of a report carry this table.

    THE LAST PAGE OFTEN DOES NOT REPEAT THE HEADING -- FY2015 page 45 and FY2025 page 41
    open straight into `OTHER EXCISE TAXES` -- so the run is extended over any following
    page that prints a GRAND TOTAL and no heading of its own.

    And the test is on a page's own TITLE, not on the words appearing anywhere on it. A
    looser test pulled in four other tables in FY2015 that happen to print GRAND TOTAL,
    which cost nothing but time until it cost a year: see `text_boxes`.
    """
    titled = sorted(p for p, boxes in pages.items()
                    if any(TITLE.search(b['text']) for b in boxes))
    out = list(titled)
    for p in titled:
        n = p + 1
        while n in pages and n not in out \
                and any(GRAND.match(b['text']) for b in pages[n]) \
                and not any(TITLE.search(b['text']) for b in pages[n]):
            out.append(n)
            n += 1
    return sorted(out)


def read_page(fy, page, boxes, layout, doc):
    """One page of the table: its rows, its grand total, and why not if neither."""
    boxes = deskew([b for b in boxes if b['text']])
    rows = band_rows(boxes)
    axes = header_axes(boxes, layout, row_anchors(boxes)[1])
    if isinstance(axes, tuple):
        names = ', '.join(n for n, _ in axes[1])
        return [], None, ('p%d prints only %s of the %d columns -- the crop ends before '
                          'the rest' % (page, names, len(layout)))
    if axes is None:
        axes = grand_axes(rows, layout)
        if axes is None:
            return [], None, None
    x0 = axes[0][1]

    out, total, section = [], None, ''
    for row in rows:
        figs = [b for b in row if is_figure(b)]
        text = ' '.join(b['text'] for b in sorted(row, key=lambda b: b['x'])
                        if not is_figure(b) and b['x'] + b['w'] < x0
                        and not ORNAMENT.match(b['text']))
        label = re.sub(r'\s+', ' ', text).strip(' |.')
        if not figs:
            if label and not LEVY.match(label):
                section = label
            continue
        cells = place(figs, axes)
        if cells is None:
            out.append((label, section, None))
            continue
        if GRAND.match(label):
            total = cells
            continue
        # A LINE THE PAGE DID NOT NAME. FY2015 prints $92,709.54 in the PAYMENTS column
        # on a row with no name at all, under UTILITY LIENS ADDED TO TAXES -- not a
        # reading failure; the rendered page has the figure and an empty name cell. It
        # cannot foot, because there is no balance beside it, and the year's own GRAND
        # TOTAL is short by exactly that amount without it. So it is carried, and it is
        # labelled as what it is rather than being given a name that is not printed.
        out.append((label or UNNAMED, section if label and LEVY.match(label) else '',
                    cells))
    return out, total, None


def foots(cells):
    """The row's own arithmetic, as the table states it."""
    if BALANCE not in cells:
        return False
    got = sum(cells.get(k, 0.0) for k in MOVERS)
    return abs(got - cells[BALANCE]) <= TOL


def published_elsewhere():
    """The years `receivables.csv` already carries."""
    if not os.path.exists(SIBLING):
        return set()
    with open(SIBLING, newline='') as fh:
        return {int(r['fy']) for r in csv.DictReader(fh) if r.get('fy', '').isdigit()}


def collect():
    body, bad, report = [], [], []
    theirs = published_elsewhere()
    seen = set()
    for path in sorted(glob.glob(os.path.join(OCR, '*annual-town-report*.tsv'))):
        m = re.search(r'fy-(\d{4})-', os.path.basename(path))
        if not m:
            continue
        fy = int(m.group(1))
        doc = os.path.relpath(path, ROOT)
        addendum = 'addendum' in os.path.basename(path)
        seen.add(fy)
        if fy in theirs and not addendum:
            bad.append(dict(fy=fy, pages='', document=doc, why=(
                'read and published by scripts/extract_receivables.py in '
                'sources/data/receivables.csv, proved to the same printed GRAND TOTAL. '
                'One table, one series: it is not read twice')))
            continue
        layout = LAYOUTS.get(fy)
        pages = read_boxes(path)
        pdf = os.path.join(PDFS, os.path.basename(path)[:-4] + '.pdf')

        found, total, pgs, why, how = [], None, [], [], set()
        for pg in table_pages(pages):
            if layout is None:
                continue
            # THE BETTER INSTRUMENT, AND THE PAGE DECIDES. A text layer is exact; OCR is
            # a reading. Where both exist the text layer wins, and which one answered is
            # published beside the row.
            boxes = text_boxes(pdf, pg) if os.path.exists(pdf) else None
            if boxes and sum(1 for b in boxes if MONEY.match(b['text'])) >= 10:
                instrument = 'text layer'
            else:
                boxes, instrument = split_merged(pages[pg]), 'ocr'
            how.add(instrument)
            rows, tot, refused = read_page(fy, pg, boxes, layout, doc)
            if refused:
                why.append(refused)
                pgs.append(pg)
                continue
            if not rows and tot is None:
                continue
            pgs.append(pg)
            found += [(pg, instrument, r) for r in rows]
            if tot is not None:
                total = tot
        if not pgs:
            bad.append(dict(fy=fy, pages='', document=doc, why=(
                'no page of this report was recognised as the table -- neither its '
                'heading nor a GRAND TOTAL row was found. Rule 13c: go and look at the '
                'pages before saying the town did not print it')))
            continue

        unread = [(pg, lab) for pg, _i, (lab, _s, c) in found if c is None]
        rows = [(pg, i, lab, sec, c) for pg, i, (lab, sec, c) in found if c is not None]
        closed = [r for r in rows if foots(r[4]) or r[2] == UNNAMED]
        if why:
            bad.append(dict(fy=fy, pages=' '.join(str(p) for p in pgs),
                            why='; '.join(why), document=doc))
            continue
        if total is None:
            bad.append(dict(fy=fy, pages=' '.join(str(p) for p in pgs),
                            why='no GRAND TOTAL row was read, so nothing on these pages '
                                'can be reconciled to the document', document=doc))
            continue
        if len(closed) != len(rows) or unread:
            n = len(rows) - len(closed) + len(unread)
            bad.append(dict(
                fy=fy, pages=' '.join(str(p) for p in pgs),
                why='%d of %d rows do not foot across to their own printed balance'
                    % (n, len(rows) + len(unread)), document=doc))
            continue
        deltas = []
        for name in MOVERS + [BALANCE]:
            got = sum(c.get(name, 0.0) for _p, _i, _l, _s, c in rows)
            want = total.get(name)
            if want is None:
                deltas.append('%s: the GRAND TOTAL prints nothing' % name)
            elif abs(got - want) > TOL_YEAR:
                deltas.append('%s: rows sum to %.2f, GRAND TOTAL says %.2f (%+.2f)'
                              % (name, got, want, got - want))
        if deltas:
            bad.append(dict(fy=fy, pages=' '.join(str(p) for p in pgs),
                            why='does not tie to its own GRAND TOTAL -- ' +
                                '; '.join(deltas), document=doc))
            continue
        if addendum:
            bad.append(dict(fy=fy, pages=' '.join(str(p) for p in pgs),
                            why='the addendum reprints the main report\'s table; the '
                                'main report is what is published', document=doc))
            continue
        for pg, instrument, label, sec, c in rows:
            row = dict(fy=fy, section=sec, item=label, page=pg, document=doc,
                       instrument=instrument,
                       proof=('footed to its own printed balance' if foots(c)
                              else 'no name printed; carried because the year\'s own '
                                   'GRAND TOTAL is short by exactly this without it'))
            for name in MOVERS + [BALANCE]:
                row[name] = ('%.2f' % c[name]) if name in c else ''
            body.append(row)
        unnamed = sum(1 for r in rows if r[2] == UNNAMED)
        report.append('FY%d p%s (%s): %d rows%s, and the eight columns tie to the '
                      'printed GRAND TOTAL'
                      % (fy, ','.join(str(p) for p in pgs), '+'.join(sorted(how)),
                         len(rows),
                         ', every one footed' if not unnamed else
                         ', all but %d footed -- the rest carry no printed name'
                         % unnamed))

    for fy in sorted(set(LAYOUTS) - seen):
        bad.append(dict(fy=fy, pages='', document='', why=(
            'no annual report for this year is in sources/town-budget/ocr/')))
    bad.sort(key=lambda r: (r['fy'], r['document']))
    return body, bad, report


def write(path, fields, rows):
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def same(path, fields, rows):
    if not os.path.exists(path):
        return False
    with open(path, newline='') as fh:
        have = list(csv.DictReader(fh))
    want = [{k: str(r.get(k, '')) for k in fields} for r in rows]
    return have == want


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--page', nargs=2, metavar=('DOC', 'PAGE'),
                    help='read one page aloud, for looking at the thing itself')
    a = ap.parse_args()

    if a.page:
        path = glob.glob(os.path.join(OCR, '%s*.tsv' % a.page[0]))[0]
        boxes = read_boxes(path)[int(a.page[1])]
        pdf = os.path.join(PDFS, os.path.basename(path)[:-4] + '.pdf')
        text = text_boxes(pdf, int(a.page[1])) if os.path.exists(pdf) else None
        if text and sum(1 for b in text if MONEY.match(b['text'])) >= 10:
            boxes = text
        else:
            boxes = split_merged(boxes)
        for row in band_rows(deskew([b for b in boxes if b['text']])):
            print('%.4f  %s' % (centre(row[0]), '  |  '.join(
                '%s@%.3f' % (b['text'], b['x'] + b['w'])
                for b in sorted(row, key=lambda b: b['x']))))
        return 0

    body, bad, report = collect()
    if a.check:
        ok = same(OUT, FIELDS, body) and same(OUT_BAD, BAD_FIELDS, bad)
        for line in report:
            print('  ' + line)
        for r in bad:
            print('  refused FY%d: %s' % (r['fy'], r['why'][:150]))
        print(('ok -- ' if ok else 'STALE -- ') +
              '%d rows across %d years; %d years refused'
              % (len(body), len({r['fy'] for r in body}), len(bad)))
        return 0 if ok else 1

    write(OUT, FIELDS, body)
    write(OUT_BAD, BAD_FIELDS, bad)
    for line in report:
        print('  ' + line)
    for r in bad:
        print('  refused FY%d: %s' % (r['fy'], r['why'][:150]))
    print('wrote %s -- %d rows across %d years' %
          (os.path.relpath(OUT, ROOT), len(body), len({r['fy'] for r in body})))
    print('wrote %s -- %d years refused' % (os.path.relpath(OUT_BAD, ROOT), len(bad)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
