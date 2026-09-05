#!/usr/bin/env python3
"""Read tables out of the town's annual reports, and say which instrument read them.

The annual reports are not one kind of document. Sixteen of them span fifteen years and
split three ways, and a parser that assumes any one shape gets the other two silently
wrong:

  * Six are page scans with no font resources at all -- FY2011, FY2012, FY2013, the FY2016
    addendum, FY2019 and FY2021. pypdf returns nothing from them, correctly. Their text
    comes from OCR (`ocr_pdf.swift`), and OCR digits are a reading, not a figure.
  * Ten carry a real text layer, and even those disagree with themselves page to page.

And the extraction mode is part of the finding. On FY2025 page 26 (the special revenue
fund detail) `extraction_mode='layout'` is the only one that gets the columns right:

    1303  SUMMER SCH   $   340.00                        $   -
                       ^ Fund Balance      ^ BLANK        ^ Deficits

Plain mode renders that row as `$ 340.00 $ -` -- two values where the table has three
columns -- so a parser assigns 340 to Fund Balance and `-` to Receipts, shifting every
figure one column left. The blank cell is only visible as a *position*.

Two pages earlier, on the combining balance sheet, layout mode is the one that is wrong:
it recovers **zero** money tokens off a page that holds 61, spreading the row over 3,469
characters. Plain mode reads it correctly.

So there is no right mode, only a right mode *for this page*, and the only honest way to
pick one is to measure all of them and write down which won. That is what `instrument()`
does, and every table this module returns carries the instrument that produced it.

Nothing here decides what a table means. It finds rows and columns and refuses to guess
when the evidence is thin; deciding which pages hold which table is a survey step, and
checking a table against a total the report itself prints is `reconcile()`.
"""

import collections
import re
import statistics

MONEY = re.compile(r'\(?-?\$?\s?-?[\d,]+\.\d\d\)?|\(?-?\$?\s?[\d,]{4,}\)?')
MONEY_TOKEN = re.compile(r'[\d,]+\.\d\d')
NUMERIC = re.compile(r'^\(?-?\$?\s*[\d,]*\.?\d*\)?-?$')

MODES = ('layout', 'plain')


def page_lines(page, mode):
    """The page as lines, under one extraction mode. Never raises: a mode that fails is a
    mode that scored zero, which is a result and not an error."""
    try:
        if mode == 'plain':
            text = page.extract_text() or ''
        else:
            text = page.extract_text(extraction_mode=mode) or ''
    except Exception:
        return []
    return text.split('\n')


def money_tokens(lines):
    return sum(len(MONEY_TOKEN.findall(l)) for l in lines)


def instrument(page, min_chars=40):
    """Which extraction mode reads this page, and the evidence for saying so.

    Returns (mode, scores). The winner is the mode that recovers the most money tokens; a
    tie goes to layout, because when both modes see the same figures layout is the only one
    that also sees the blank cells.

    **A page with no figures is not a page with no text.** An earlier version returned None
    whenever both modes scored zero money, and a survey built on it reported 2,311 of 2,751
    pages as having no text layer. Many of those pages read perfectly well -- FY2025's
    school staff rosters, for one, which are lists of names and carry no dollar amounts at
    all. Counting figures and calling the absence of figures an absence of text is the same
    mistake as a grep that finds nothing being read as nobody having said it.

    So the fall-back is character count, and None is returned only when neither mode
    produces meaningful text. That is the one case where the caller wants OCR.
    """
    scores = {}
    for mode in MODES:
        lines = page_lines(page, mode)
        scores[mode] = {
            'money': money_tokens(lines),
            'chars': sum(len(l.strip()) for l in lines),
            'lines': sum(1 for l in lines if l.strip()),
            'widest': max((len(l) for l in lines), default=0),
        }
    if any(s['money'] for s in scores.values()):
        best = max(MODES, key=lambda m: (scores[m]['money'], m == 'layout'))
        return best, scores
    best = max(MODES, key=lambda m: (scores[m]['chars'], m == 'plain'))
    if scores[best]['chars'] < min_chars:
        return None, scores
    return best, scores


COUNT_TOKEN = re.compile(r'(?<![\d.,])\d{1,7}(?![\d.,])')


def figure_rows(lines, counts=False):
    """The lines that carry figures. These, and only these, get to vote on where the
    columns are.

    `counts=True` treats bare integers as figures. Not every table in these reports is
    money: election tallies print `58 27 34 62 181`, enrolment prints headcounts, vital
    records prints births and deaths. Keyed on currency alone those pages yield ZERO figure
    rows, so no ruler forms and the whole table is silently skipped — which is exactly what
    happened to the elections, enrolment and vital-records datasets.

    A page is not only its table. Centred titles, a `TOWN OF LUNENBURG` heading and a
    date span the full width and cross every gutter, so a ruler measured over all lines
    finds boundaries in the title's own word gaps and none of the table's. Measured over
    the rows that hold money, the FY2025 special revenue detail resolves to the seven
    gutters its 36 fund rows agree on.
    """
    pat = COUNT_TOKEN if counts else MONEY_TOKEN
    return [l for l in lines if pat.search(l)]


def column_ruler(lines, min_gutter=2, blank_frac=0.92):
    """Character positions where a column ends, taken from the whitespace between them.

    A gutter is a run of positions blank in nearly every row. Not *every* row: one long
    label crossing into the next column would otherwise erase a boundary that thirty other
    rows agree on, and losing a boundary shifts every figure after it.

    Returns a list of (start, end) cut ranges. Empty means the rows do not agree on any
    boundary, which is the honest answer for prose and for a table whose spacing is
    kerning rather than position -- the caller must not fall back to splitting on runs of
    spaces, because that is precisely the shift this function exists to prevent.
    """
    rows = [l for l in lines if l.strip()]
    if len(rows) < 3:
        return []
    width = max(len(r) for r in rows)
    rows = [r.ljust(width) for r in rows]
    need = len(rows) * blank_frac
    blank = [sum(1 for r in rows if r[i] == ' ') >= need for i in range(width)]

    gutters, start = [], None
    for i, b in enumerate(blank + [False]):
        if b and start is None:
            start = i
        elif not b and start is not None:
            if i - start >= min_gutter:
                gutters.append((start, i))
            start = None
    return gutters


def cells(line, ruler):
    """Split one row at the ruler. A cell with nothing in it comes back as '' rather than
    being dropped, which is the whole point -- see the 1303 SUMMER SCH row above.

    The cut is *snapped* to a blank position inside the gutter rather than taken at the
    gutter's edge. A ruler is what most rows agree on, so a minority row can carry a
    character where the majority has space, and cutting there slices a value in half. It
    did: `1308 SCH CHOICE` lost the last digit of `45.00` to a gutter, and `(62.84)` lost
    its closing bracket -- which is worse than truncation, because a negative that loses
    its bracket reads as a positive.

    A row with nothing blank anywhere in a gutter genuinely spans that boundary. It is
    returned with a `!` marker in place of the cut so the caller can drop the row rather
    than parse a value that was never separated.
    """
    out, prev, spanned = [], 0, False
    for start, end in ruler:
        seg = line[start:end]
        cut = start + (seg.index(' ') if ' ' in seg else 0)
        if ' ' not in seg and start < len(line):
            spanned = True
        out.append(line[prev:cut].strip())
        prev = cut
    out.append(line[prev:].strip())
    return (out + ['!']) if spanned else out


def count(text):
    """A whole number, for tables that tally rather than cost. Blank stays blank."""
    t = (text or '').strip().replace(',', '')
    if re.fullmatch(r'-?\d{1,7}', t):
        return int(t)
    return None


def amount(text):
    """A figure, or None if the cell does not hold one.

    Handles what the town's ledgers actually print: a leading dollar sign, a parenthesised
    negative, a trailing minus, and `-` on its own for a line with nothing on it. `-` is
    returned as 0.0 rather than None, because a printed dash is the report saying zero,
    and a total that skips it will not tie.
    """
    t = (text or '').strip()
    if not t:
        return None
    # `S` and `s` for `$`. OCR confuses them constantly -- `S283,149.23`, `SO.00`,
    # `S1.848.802.86` -- and each one silently dropped a cell.
    t = re.sub(r'^[Ss](?=[\d.,O])', '$', t)
    t = t.replace('SO.00', '$0.00').replace('$O', '$0')
    if t in ('-', '$-', '$ -', '--', '$'):
        return 0.0
    neg = t.startswith('(') or t.endswith(')') or t.endswith('-')
    t = t.strip('()').lstrip('$').strip().rstrip('-').replace('$', '').strip()

    # Separators, whichever glyph OCR produced for them.
    #
    # A figure printed `$2,306,293.24` can come back as `2.306,293.24` -- one comma read as
    # a point -- and `$29,075.55` as `29.075.55`. Both were unparseable and both silently
    # dropped the cell, which shifts nothing and so cannot be caught downstream.
    #
    # The rule that covers all of them: **the LAST separator followed by exactly two digits
    # is the decimal point; every other separator is a thousands mark.** That is unambiguous
    # for money and is applied only where the shape fits, so a bare `1.234` is still read as
    # one point two three four.
    m = re.fullmatch(r'(-?[\d.,]*[\d])([.,])(\d\d)', t)
    if m and re.search(r'[.,]', m.group(1)):
        t = re.sub(r'[.,]', '', m.group(1)) + '.' + m.group(3)
    else:
        t = t.replace(',', '')
    if not t or not re.fullmatch(r'-?\d*\.?\d*', t) or t in ('.', '-'):
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return -abs(v) if neg else v


def was_repaired(text):
    """True when `amount()` had to repair this cell to read it.

    Currently one case: a thousands separator OCR'd as a decimal point. Callers record it
    so a repaired figure can be told from one that parsed cleanly -- rule 7, an inference
    is never quietly promoted to an observation.
    """
    t = (text or '').strip().strip('()').lstrip('$').strip().rstrip('-')
    t = t.replace(',', '').replace('$', '').strip()
    return bool(re.fullmatch(r'-?\d{1,3}(?:\.\d{3})+\.\d\d', t))


def looks_like_money(text):
    """A cell that is plainly meant to be a figure, whether or not it parses.

    Used to catch the cells `amount()` returns None for. A dropped cell is invisible in the
    output and shifts nothing, so nothing downstream can notice it -- which is how
    `$29.075.55` went missing from a row whose other three columns were right.
    """
    t = (text or '').strip()
    return bool(t) and bool(re.search(r'\d', t)) and bool(re.search(r'[\d.,$()]', t)) \
        and not re.search(r'[A-Za-z]{3}', t)


def reconcile(values, printed_total, tolerance=0.02):
    """Does what we extracted add up to what the report prints?

    Rule 13: when an extract has a total the source itself prints, reconcile to it.
    `extract_munis_report.py` refuses to write when it does not tie, because sixteen
    departments went missing for weeks with nothing comparing the two. Returns
    (ok, extracted_total, difference) so a caller can print the gap rather than a boolean.
    """
    got = round(sum(v for v in values if v is not None), 2)
    if printed_total is None:
        return False, got, None
    diff = round(got - printed_total, 2)
    return abs(diff) <= tolerance, got, diff


def table(page, min_cols=2):
    """Rows and columns off one page, with the instrument that produced them.

    Returns a dict carrying `mode`, `ruler`, `rows` and `scores`. `rows` is every line cut
    at the ruler; nothing is filtered out here, because deciding which rows are data is a
    question about the table and this function only knows about the page.
    """
    mode, scores = instrument(page)
    if mode is None:
        return {'mode': None, 'ruler': [], 'rows': [], 'scores': scores,
                'why': 'no text layer -- this page is a scan, OCR it'}
    lines = page_lines(page, mode)
    ruler = column_ruler(figure_rows(lines))
    if len(ruler) + 1 < min_cols:
        return {'mode': mode, 'ruler': ruler, 'rows': [], 'scores': scores,
                'why': f'rows do not agree on {min_cols} columns; '
                       f'{len(ruler)} gutter(s) found'}
    rows = [cells(l, ruler) for l in lines if l.strip()]
    return {'mode': mode, 'ruler': ruler, 'rows': rows, 'scores': scores, 'why': ''}


# ---------------------------------------------------------------------------
# The scanned reports
#
# Six of the sixteen annual town reports have no text layer at all. Their text comes from
# Vision OCR, and `ocr_pdf.swift --boxes` writes each recognised line with its position.
# Rebuilding a fixed-width page from those positions means the ruler above works on a scan
# exactly as it does on a digital page -- the alternative, splitting OCR reading-order text
# on runs of spaces, is the column shift this module exists to prevent.
# ---------------------------------------------------------------------------

def read_boxes(path):
    """The TSV `ocr_pdf.swift --boxes` writes, as a list of dicts, one per recognised line."""
    rows = []
    with open(path, encoding='utf-8') as fh:
        header = fh.readline()
        if not header.startswith('page\t'):
            raise ValueError(f'{path} is not a --boxes TSV')
        for line in fh:
            f = line.rstrip('\n').split('\t', 6)
            if len(f) < 7:
                continue
            rows.append({'page': int(f[0]), 'x': float(f[1]), 'y': float(f[2]),
                         'w': float(f[3]), 'h': float(f[4]), 'conf': float(f[5]),
                         'text': f[6]})
    return rows


def looks_flipped(boxes, min_rows=4):
    """Is this page's OCR a half-turn out?

    A 180-degree error is invisible to every test that asks how the text LOOKS: the lines
    are still horizontal, the words still read correctly, and Vision still reports
    confidence 1.000. What it changes is where things sit -- rows arrive bottom-to-top and
    columns right-to-left -- so the output is orderly and mirrored, which is worse than
    obviously broken.

    The tell is structural and holds across every table in this archive: **a label sits to
    the LEFT of its figures.** Flip the page and it sits to the right. That is checked per
    row and put to a vote, so one odd row cannot decide it.
    """
    rows, votes = collections.defaultdict(list), []
    if not boxes:
        return False
    tol = statistics.median([b['h'] for b in boxes]) * 0.6 or 0.004
    for b in sorted(boxes, key=lambda b: -b['y']):
        for y in rows:
            if abs(y - b['y']) <= tol:
                rows[y].append(b)
                break
        else:
            rows[b['y']].append(b)
    for items in rows.values():
        text = [b['x'] for b in items
                if amount(b['text']) is None and re.search(r'[A-Za-z]{3}', b['text'])]
        money = [b['x'] for b in items if amount(b['text']) is not None]
        if text and money:
            votes.append(statistics.mean(text) > statistics.mean(money))
    if len(votes) < min_rows:
        return False
    return sum(votes) > len(votes) * 0.6


def unflip(boxes):
    """Mirror a page that was read a half-turn out. Exactly reversible, so exactly fixable."""
    return [dict(b, x=1.0 - b['x'] - b['w'], y=1.0 - b['y'] - b['h']) for b in boxes]


def layout_from_boxes(boxes, width=None, min_width=190, max_width=400):
    """Fixed-width lines rebuilt from OCR geometry, in the shape `page_lines` returns.

    Rows come from clustering on y rather than from Vision's reading order, because a
    table row is a horizontal band and Vision emits it as several separate observations.
    The band tolerance is derived from the observations' own median height, so a page set
    in a larger face does not need a different constant.

    Columns are the observation's own x, scaled to character positions. Where two
    observations would collide the later one is pushed right by a single space -- it moves
    the text, never drops it, and the ruler is measured over many rows so one nudged cell
    does not move a boundary.

    **The character grid is sized to the content, not fixed.** It was fixed at 190 columns,
    and any table wider than that lost its right-hand edge -- silently, because the labels
    all survive and only the last column of figures goes. On the widest schedules that took
    the third amount column, the `SUMMARY OF RECEIPTS` grand total, the trust funds' ENDING
    VALUE and the receivables ADJUSTMENTS column. A missing right edge is the shape of error
    rule 13 warns about: what is left still reads as a complete table.

    The width now comes from the longest text the page actually holds at its rightmost
    position, so a wide table gets a wide grid and a narrow one is not padded out.
    """
    if not boxes:
        return []
    # Correct a half-turn before anything else reads the geometry. Rotation survived the
    # recogniser's own calibration on about 22 pages of this archive, and every downstream
    # reader inherits it silently.
    if looks_flipped(boxes):
        boxes = unflip(boxes)
    if width is None:
        # The grid must be wide enough that every box, placed at its own x, still fits.
        # A box starting at fraction x needs W such that x*W + len(text) <= W, so
        # W >= len(text) / (1 - x). Taking the max over all boxes is the smallest grid on
        # which nothing is clipped.
        #
        # Guessing at this does not work: a first attempt used a fixed 190 columns and lost
        # the right-hand column of every wide schedule -- the SUMMARY OF RECEIPTS grand
        # total, the trust funds' ENDING VALUE, the receivables ADJUSTMENTS. A second used
        # a fudged multiple and still clipped `GRAND T` off the end of the FY2019 receipts
        # page. The requirement is arithmetic, so it is computed rather than estimated.
        need = min_width
        for b in boxes:
            if b['x'] < 0.999 and b['text']:
                need = max(need, len(b['text']) / (1.0 - b['x']))
        width = int(min(max_width, need + 2))
    tol = statistics.median([b['h'] for b in boxes]) * 0.6 or 0.004

    bands = []
    for b in sorted(boxes, key=lambda b: -b['y']):
        for band in bands:
            if abs(band['y'] - b['y']) <= tol:
                band['items'].append(b)
                break
        else:
            bands.append({'y': b['y'], 'items': [b]})

    lines = []
    for band in bands:
        row = ''
        for b in sorted(band['items'], key=lambda b: b['x']):
            col = int(round(b['x'] * width))
            # At least one space between runs, always. Two runs whose scaled columns land
            # exactly adjacent were being concatenated with no separator -- FY2011 page 70
            # came out as `GRAND TOTALCitizens Relief Fund`, which is one token to every
            # regex that reads it and two things on the page.
            if row and col <= len(row):
                col = len(row) + 1
            row = row.ljust(col) + b['text']
        lines.append(row)
    return lines


def low_confidence(boxes, threshold=0.5):
    """Recognised lines the OCR was not sure of, and which carry a figure.

    An OCR digit is a reading, not a figure. A table that ties to its printed total has
    checked itself; one that does not, and that is full of low-confidence rows, has an
    explanation for why -- and one that ties *despite* them has not been let off, because
    two misreadings can cancel.
    """
    return [b for b in boxes if b['conf'] < threshold and MONEY_TOKEN.search(b['text'])]


def orphans(rows, pairs):
    """Figures with no label beside them, given which columns pair up.

    `pairs` is a list of (label_col, value_col). It has to be supplied rather than guessed
    because the town's receipts page is a three-up newspaper layout -- three separate
    label/amount pairs across one physical row -- and "the label column" is not a thing
    that page has. Which columns pair with which is a fact about the table, established by
    the survey, and guessing it produces either fifty false positives or none at all.

    Returns a list of (row_index, label_col, value_col, value).

    This is the check reconciliation cannot do, and the reason it exists is worth keeping:
    on page 1 of the FY2016 addendum, Vision read `$22,399,495.70` and did not read
    `REAL ESTATE TAXES` beside it -- the largest revenue line in the town, extracted as a
    number with no name. The figures still summed to the report's printed GRAND TOTAL,
    because a missing *label* does not change a total. A table can tie perfectly and still
    have lost what half its rows are about.
    """
    out = []
    for i, row in enumerate(rows):
        if '!' in row:
            continue
        for lab, val in pairs:
            if val >= len(row) or lab >= len(row):
                continue
            v = amount(row[val])
            if v is not None and not re.search(r'[A-Za-z]', row[lab] or ''):
                out.append((i, lab, val, v))
    return out


def differential(passes):
    """Compare two OCR passes of the same page and report where they disagree.

    Raster scale is a *correctness* parameter for Vision, not a performance one, and it
    fails silently. At scale 3.0 and 4.0 the FY2016 addendum loses `REAL ESTATE TAXES` and
    `TAX LIENS REDEEMED` entirely; at 6.0 both come back. Every one of those readings --
    the ones it got and the ones it truncated -- is reported at confidence 1.000, so
    confidence cannot be used to find them. Only a second pass can.

    Going further up does not converge either. Between 6.0 and 8.0 no rows are gained or
    lost, but `PERSONAL PROPERTY TAXES` degrades to `PERSONAL PROPERTY TAXE` and `TEREST`
    becomes `ITEREST`. So structure settles and characters do not, and the two have to be
    reported separately: a row seen by both passes is a row that exists, and text the two
    passes spell differently is text that has not been read.

    `passes` is a list of line-lists. Returns (agreed, only_in_one, spelled_differently).
    """
    sets = [set(l.strip() for l in p if l.strip()) for p in passes]
    agreed = set.intersection(*sets) if sets else set()
    only = set.union(*sets) - agreed if sets else set()

    def shape(s):
        return re.sub(r'[A-Za-z]+', 'W', re.sub(r'[\d,]+\.?\d*', 'N', s))

    by_shape = {}
    for s in only:
        by_shape.setdefault(shape(s), []).append(s)
    differing = [sorted(v) for v in by_shape.values() if len(v) > 1]
    return sorted(agreed), sorted(only), differing


def repair_label(text, vocabulary, min_ratio=0.82):
    """Match a damaged OCR label against labels the digital reports print exactly.

    The scanned years are FY2011-FY2013, the FY2016 addendum, FY2019 and FY2021. The other
    ten reports have a real text layer, and the town reuses its own line names year after
    year -- so `TEREST REAL ESTAT` has a correct spelling sitting in FY2020's receipts
    table, and the archive can repair itself from the half of it that was typed rather
    than scanned.

    A repair is a derived thing. It comes back as (label, matched, ratio) and never
    replaces the reading in place, because rule 7 applies to a corrected label exactly as
    it applies to anything else: what was observed is `TEREST REAL ESTAT`, and
    `INTEREST REAL ESTATE` is an inference, however good. Callers write both.
    """
    import difflib
    t = (text or '').strip().upper()
    if not t:
        return text, None, 0.0
    best, ratio = None, 0.0
    for cand in vocabulary:
        r = difflib.SequenceMatcher(None, t, cand.upper()).ratio()
        if r > ratio:
            best, ratio = cand, r
    if ratio < min_ratio:
        return text, None, ratio
    return text, best, round(ratio, 3)
