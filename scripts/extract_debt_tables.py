#!/usr/bin/env python3
"""What the town OWES, off the annual reports' two debt tables -- and only where it foots.

    python3 scripts/extract_debt_tables.py
    python3 scripts/extract_debt_tables.py --check

Writes `sources/data/outstanding-debt.csv` and `sources/data/debt-repayment.csv`.

--------------------------------------------------------------------------------------
THESE ARE TWO TABLES, NOT ONE
--------------------------------------------------------------------------------------

`annual-report-pages.csv` files both under the subject `debt`. They share a subject and
nothing else -- different grain, different columns, different proof:

  FIVE YEARS OUTSTANDING DEBT -- principal outstanding on 30 June, by PURPOSE (sewers,
  schools, water, roads...), split inside and outside the Chapter 44 debt limit, for the
  report's year and the four before it. One report, five as-of years, ~15 purposes.
  Grain: report x as-of fiscal year x purpose.  ->  outstanding-debt.csv

  DEBT REPAYMENT SCHEDULE -- what falls due in each FUTURE fiscal year, per bond issue,
  split principal / interest / MWPAT admin fee, running out to FY2047. Sixteen to
  twenty-five year columns, printed across two to four pages.
  Grain: report x due fiscal year x measure.  ->  debt-repayment.csv

Flattening them would put an amount OUTSTANDING and an amount DUE in one column, which is
the same class of error as rule 1's budget-against-actual: two stages of one quantity,
differenced as though they were comparable.

--------------------------------------------------------------------------------------
WHAT IS PUBLISHED AND WHAT IS REFUSED
--------------------------------------------------------------------------------------

**A row is written only where the document's own arithmetic closes on it.** Not a
tolerance on a reading -- the identity the table states about itself.

FIVE YEARS OUTSTANDING DEBT states up to five identities in every one of its five year
columns, and a column is published only if every one it prints holds to the dollar:

    sum(purposes inside the limit)   = Total Within the General Debt Limit
    sum(purposes outside the limit)  = Total Outside the General Debt Limit
    within + outside                 = Total Long-Term Indebtedness
    sum(note types)                  = Total Short-Term Indebtedness
    long-term + short-term           = Total Outstanding Indebtedness

And then a check almost nothing else in this archive gets: each fiscal year is printed in
up to FIVE different books, four years apart, off the same ledger. `--check` reports where
two reports disagree about one year.

DEBT REPAYMENT SCHEDULE publishes its GRAND TOTAL block and NOT its issue-level detail.
That is a statement about the scans, not about the town. The grand-total block is set in a
handful of wide rows and reads cleanly; the issue detail is twenty-odd narrow columns of
small type, and Vision returns it as `52782335 52547440 52531098` -- the FY2024 page is in
the cache in that state. There is no threshold that rescues it, and an issue-level row
that cannot foot to the printed grand total is not evidence of anything. So the per-issue
schedule is UNREAD, deliberately, and said so here rather than published unproven.

The grand-total block states two identities per year column, both checked:

    GRAND TOTAL PRINCIPAL + GRAND TOTAL INTEREST = GRAND TOTAL PRINCIPAL & INTEREST
    principal & interest + GRAND TOTAL MWPAT ADMIN FEES = TOTAL DEBT

--------------------------------------------------------------------------------------
READING THE PAGES: four things, three of them from `scripts/read_trust_table.py`
--------------------------------------------------------------------------------------

1. **The OCR origin is at the BOTTOM LEFT.** `sources/town-budget/ocr/README.md` says so
   and it is easy to miss: sorted by the `y` column, a page comes out upside down. That is
   why `scripts/extract_debt_outstanding.py` -- the earlier attempt at the first of these
   two tables -- finds the right page in ten reports and reads nothing from any of them.
   It looks for the year header in the first eight lines of the page, and in a
   bottom-origin rendering the header is in the last eight. `sources/data/debt-outstanding.csv`
   is one line long for that reason, not because the table is absent.

2. **A page may also be turned 180 degrees on top of that**, and several are: FY2022's
   FIVE YEARS page and FY2024's whole repayment schedule come off the scanner inverted.
   The test is the one `read_trust_table.upright()` uses -- where the labels sit relative
   to the figures -- because it needs no keyword and nothing typed in.

3. **The rotation is measured, never guessed.** FY2011 page 75 is turned enough that one
   row's five figures occupy three different `y` values while adjacent rows overlap. The
   median slope between a figure and its nearest neighbour to the right recovers it.

4. **Figures are placed by COLUMN POSITION and named from a header that was read.** A
   purpose with nothing outstanding in 2016 prints nothing in that column, so taking the
   figures in order puts every later one under the wrong year. Right edges are clustered
   -- accounting figures are right-aligned and the `$` on some rows and not others makes
   the left edge and the centre both move -- and the clusters are NAMED from the printed
   year header. Where the header is unreadable (FY2019 prints `40021012 10020 20011224`)
   the years are taken from the table's own `As of June 30, YYYY` and the report's
   descending five-year layout, `as_of_basis` records that it was derived rather than
   read, and the cross-report check is what tests it.

`csv.DictReader` may not be used on these TSVs. OCR text contains bare `"`, and the csv
module then swallows the following lines into one field: it returns 8,059 rows for a
10,027-line FY2011 file, and page 75 disappears entirely. Split on tabs.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT_OUTSTANDING = os.path.join(ROOT, 'sources', 'data', 'outstanding-debt.csv')
OUT_REPAYMENT = os.path.join(ROOT, 'sources', 'data', 'debt-repayment.csv')
OUT_NOTE = os.path.join(ROOT, 'sources', 'data', 'PROVENANCE-debt-tables.md')

OUTSTANDING_FIELDS = ['report_fy', 'document', 'page', 'as_of_fy', 'as_of_basis', 'section',
                      'category', 'amount', 'identities_closed']
REPAYMENT_FIELDS = ['report_fy', 'document', 'page', 'as_of', 'due_fy', 'principal',
                    'interest', 'principal_and_interest', 'mwpat_admin_fee', 'total_debt']

# A figure on these pages is WHOLE DOLLARS. `read_trust_table.money()` may not be reused:
# it takes the last two digits as cents, which turns `9,058,250` into $90,582.50. The
# group separator may be a comma or a full stop -- a scanner cannot tell them apart, and
# `25.928,189` and `305.771` are both in the cache -- so both are accepted as separators
# and the group lengths are what says whether a reading is a number at all.
MONEY = re.compile(r'^[\s_.\-–—•]*\(?\s*[-–—]?\s*[$S]?\s*'
                   r'(\d{1,3}(?:[.,]\d{3})*)\s*\)?[\s_.\-$S]*$')
MONEY_TOKEN = re.compile(r'[$S]?\s?\d{1,3}(?:[.,]\d{3})+|[$S]\s?\d{1,3}\b')
YEAR = re.compile(r'^\W*(19\d\d|20[0-5]\d)\W*$')
LETTERS = re.compile(r'[A-Za-z]{3}')


def money(text):
    """The figure a box holds, or None. Whole dollars; both separators; ( ) is negative."""
    m = MONEY.match(text.strip())
    if not m:
        return None
    v = float(re.sub(r'[.,]', '', m.group(1)))
    t = text.strip()
    if t.startswith('(') or t.rstrip('_ .-').endswith(')') or re.match(r'^[\s_]*[-–—]\s*[$S]?\s*\d', t):
        v = -v
    return v


def load(path):
    """Boxes per page, y flipped to a TOP-LEFT origin. Tab split, never csv.DictReader."""
    pages = collections.defaultdict(list)
    with open(path, encoding='utf-8', errors='replace') as fh:
        for i, line in enumerate(fh):
            f = line.rstrip('\n').split('\t')
            if i == 0 or len(f) < 7:
                continue
            try:
                page, x, y, w, h = int(f[0]), float(f[1]), float(f[2]), float(f[3]), float(f[4])
            except ValueError:
                continue
            pages[page].append({'x': x, 'y': 1.0 - y - h, 'w': w, 'h': h,
                                'text': '\t'.join(f[6:]).strip()})
    return pages


def upright(boxes):
    """Turn the page over if the scanner fed it in backwards. See `read_trust_table`."""
    labels = [b for b in boxes if money(b['text']) is None and len(b['text']) > 10]
    figs = [b for b in boxes if money(b['text']) is not None]
    if len(labels) < 5 or len(figs) < 5:
        return boxes
    lx = sum(b['x'] for b in labels) / len(labels)
    fx = sum(b['x'] for b in figs) / len(figs)
    if lx <= fx:
        return boxes
    return [dict(b, x=1.0 - b['x'] - b['w'], y=1.0 - b['y'] - b['h']) for b in boxes]


def skew(boxes):
    """The page's own rotation, from the median slope to each figure's right neighbour."""
    vals = [b for b in boxes if money(b['text']) is not None]
    slopes = []
    for v in vals:
        right = [w for w in vals if 0.02 < w['x'] - v['x'] < 0.18]
        if not right:
            continue
        w = min(right, key=lambda w: abs(w['y'] - v['y']))
        if abs(w['y'] - v['y']) < 0.02:
            slopes.append((w['y'] - v['y']) / (w['x'] - v['x']))
    return statistics.median(slopes) if len(slopes) >= 8 else 0.0


def deskew(boxes):
    s = skew(boxes)
    return [dict(b, Y=b['y'] - s * b['x']) for b in boxes]


def split_merged(boxes):
    """One observation holding several cells, split by character position.

    Vision returns `$4,689,187 $4,516,558 $4,456,114 ...` -- sixteen year columns in one
    box -- on every grand-total row it reads well. Anchored money matching sees no figure
    there at all, so the whole row goes missing while being perfectly legible. The split
    is by the token's share of the string, which is an ESTIMATE; only the right edge is
    used to place it, and the row's arithmetic still has to close, so a token that lands
    in the wrong column cannot manufacture agreement.
    """
    out = []
    for b in boxes:
        t = b['text']
        parts = list(MONEY_TOKEN.finditer(t))
        # A LABEL AND ITS FIRST FIGURE IN ONE OBSERVATION. FY2014 returns `Total Within
        # the General Debt Limit $ 17,859,121` as a single box, so the row's own year --
        # the report's headline column -- had no total and the whole column was refused.
        # Only tokens that start after the last letter are taken, so `As of June 30, 2014`
        # and `FIVE YEARS OUTSTANDING DEBT (1)` are left alone.
        letters = [m.end() for m in re.finditer(r'[A-Za-z]{3,}', t)]
        if letters and parts:
            parts = [m for m in parts if m.start() >= letters[-1]]
            if parts:
                n = float(len(t))
                cut = parts[0].start()
                out.append(dict(b, text=t[:cut].rstrip(), w=b['w'] * (cut / n)))
                for m in parts:
                    out.append(dict(b, text=m.group(0),
                                    x=b['x'] + b['w'] * (m.start() / n),
                                    w=b['w'] * ((m.end() - m.start()) / n),
                                    split_from=t))
                continue
        if len(parts) < 2:
            out.append(b)
            continue
        n = float(len(t))
        for m in parts:
            out.append(dict(b, text=m.group(0),
                            x=b['x'] + b['w'] * (m.start() / n),
                            w=b['w'] * ((m.end() - m.start()) / n),
                            split_from=t))
    return out


def clusters(values, gap):
    """1-D grouping: a new group wherever consecutive values are more than `gap` apart."""
    out = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= gap:
            out[-1].append(v)
        else:
            out.append([v])
    return out


def rows_by_nearest_label(figs, labels, pitch):
    """Each FIGURE to its nearest label. NOT each label to the figures near it.

    The loose direction is what broke the first reading of FY2024 page 36: a band wide
    enough to hold `Other Building`'s own row also reached `Schools` above it, so Schools'
    five figures were counted twice and the section over-footed by $2,396,142. A figure
    belongs to exactly one row, so the assignment has to be exclusive.
    """
    out = collections.defaultdict(list)
    for f in figs:
        cand = [l for l in labels if l['x'] + l['w'] < f['x'] + 0.01]
        if not cand:
            continue
        lab = min(cand, key=lambda l: abs(l['Y'] - f['Y']))
        if abs(lab['Y'] - f['Y']) > pitch * 0.8:
            continue
        out[id(lab)].append(f)
    return out


def place(figs, centres):
    """Each figure to the column whose right edge it is nearest. Position, never order."""
    cols = collections.defaultdict(list)
    for f in figs:
        r = f['x'] + f['w']
        i = min(range(len(centres)), key=lambda j: abs(centres[j] - r))
        cols[i].append(f)
    return cols


# ------------------------------------------------------------------ FIVE YEARS OUTSTANDING

FIVE_MARK = re.compile(r'Outside the General Debt Limit', re.I)
FIVE_HEAD = re.compile(r'FIVE\s+YEARS?\s+OUTSTANDING\s+DE[BR]T|E[IVL]+E\s+YEARS?\s+OUTSTANDING', re.I)
AS_OF = re.compile(r'As of June 30,?\s*(\d{4})', re.I)
STOP = re.compile(r'^\(1\)|Authorized Unissued', re.I)
SECTIONS = [
    (re.compile(r'^(within|inside) the general debt limit', re.I), 'inside the debt limit'),
    (re.compile(r'^outside the general debt limit', re.I), 'outside the debt limit'),
    (re.compile(r'^short[- ]?term indebtedness', re.I), 'short-term'),
]
TOTALS = [
    (re.compile(r'^total (within|inside) the general debt limit', re.I), 'within'),
    (re.compile(r'^total outside the general debt limit', re.I), 'outside'),
    (re.compile(r'^total long[- ]?term indebtedness', re.I), 'long'),
    (re.compile(r'^total short[- ]?term indebtedness', re.I), 'short'),
    (re.compile(r'^total outstanding indebtedness', re.I), 'outstanding'),
]


def find_pages(pages, pattern, need=1):
    hits = []
    for pg, boxes in sorted(pages.items()):
        n = sum(1 for b in boxes if pattern.search(b['text']))
        if n >= need:
            hits.append(pg)
    return hits


def read_five_years(fy, doc, pages, problems):
    pgs = find_pages(pages, FIVE_MARK)
    if not pgs:
        problems.append('FY%s: no FIVE YEARS OUTSTANDING DEBT page' % fy)
        return []
    page = pgs[0]
    boxes = upright(pages[page])

    # TRIM TO THE HEADING. FY2025 prints the trust funds above this table on one page.
    head = [b for b in boxes if FIVE_HEAD.search(b['text'])]
    if head:
        top = max(b['y'] for b in head)
        boxes = [b for b in boxes if b['y'] >= top - 0.002]
    stop = [b for b in boxes if STOP.search(b['text'])]
    if stop:
        boxes = [b for b in boxes if b['y'] < min(b2['y'] for b2 in stop)]

    boxes = deskew(split_merged(boxes))
    figs = [b for b in boxes if money(b['text']) is not None]
    labels = [b for b in boxes if money(b['text']) is None and LETTERS.search(b['text'])]
    if len(figs) < 20:
        problems.append('FY%s page %d: only %d figures read' % (fy, page, len(figs)))
        return []

    # THE COLUMNS, from the figures' own right edges. Five are expected: the table is
    # called FIVE YEARS. A page that does not cluster into five is refused, not coerced.
    groups = [g for g in clusters([f['x'] + f['w'] for f in figs], 0.025) if len(g) >= 4]
    if len(groups) != 5:
        problems.append('FY%s page %d: figure right edges cluster into %d columns, not 5'
                        % (fy, page, len(groups)))
        return []
    centres = [statistics.median(g) for g in groups]

    # NAMING THEM. The printed year header first; the table's own `As of June 30, YYYY`
    # and the descending layout where the header did not survive the scan.
    printed = []
    for b in boxes:
        m = YEAR.match(b['text'])
        if m and money(b['text']) is None:
            printed.append((b['x'] + b['w'], int(m.group(1))))
    as_of = None
    for b in boxes:
        m = AS_OF.search(b['text'])
        if m:
            as_of = int(m.group(1))
    if as_of is None:
        as_of = int(fy)
    derived = [as_of - i for i in range(5)]
    basis = 'derived from the As-of line and the descending five-year layout'
    if len(printed) == 5:
        read_years = [y for _, y in sorted(printed)]
        wrong = sum(1 for a, b in zip(read_years, derived) if a != b)
        if not wrong:
            basis = 'printed year header, which matches the descending five-year layout'
        elif wrong == 1:
            # ONE misread DIGIT is not a different layout. FY2011 prints 2009 and Vision
            # returns `2002`; the other four columns are exact and the As-of line says
            # 2011. The cross-report check is what tests this, not the scan.
            basis = ('the As-of line and the layout; the header read %s, one column misread'
                     % read_years)
        else:
            problems.append('FY%s page %d: header reads %s, the layout says %s -- REFUSED'
                            % (fy, page, read_years, derived))
            return []

    ys = sorted({round(l['Y'], 4) for l in labels})
    pitch = statistics.median([b - a for a, b in zip(ys, ys[1:])] or [0.02])
    owned = rows_by_nearest_label(figs, labels, pitch)

    rows, section, printed_tot = [], '', collections.defaultdict(dict)
    for lab in sorted(labels, key=lambda b: b['Y']):
        text = re.sub(r'\s+', ' ', lab['text']).strip(' .$_')
        sec = next((s for pat, s in SECTIONS if pat.match(text)), None)
        tot = next((k for pat, k in TOTALS if pat.match(text)), None)
        if sec and not tot:
            section = sec
            continue
        # A TOTAL IS READ WITHOUT ITS SECTION HEADING. FY2019's page begins below
        # `Inside the General Debt Limit`, so requiring a section first threw away every
        # printed total on a page where all five columns of them tie.
        if not section and not tot:
            continue
        mine = owned.get(id(lab), [])
        if not mine:
            continue
        cols = place(mine, centres)
        for i, group in cols.items():
            if len(group) != 1:
                continue
            v = money(group[0]['text'])
            if tot:
                printed_tot[i][tot] = v
            else:
                rows.append({'report_fy': fy, 'document': doc, 'page': page, 'as_of_fy': derived[i],
                             'as_of_basis': basis, 'section': section,
                             'category': text, 'amount': '%.0f' % v,
                             'identities_closed': ''})

    # THE PROOF, PER COLUMN -- AND PER SECTION INSIDE IT.
    #
    # A column is published only if the totals the table prints add up to each other. A
    # PURPOSE row inside it is published only if its own section also sums to the section
    # total printed beneath it. The two are separate because the scans separate them:
    # FY2019's page begins part-way down the table, so `Sewers & Drains`, `Land
    # Acquisition` and `Schools` are off the top of the image while every printed total is
    # on it and ties. Refusing the whole column there would throw away five years of the
    # headline figure to protect three purposes that were never scanned.
    #
    # TOLERANCE IS ONE DOLLAR, and it is the DOCUMENT's rounding rather than ours. The
    # FY2020 column's inside purposes sum to $11,256,660 against a printed $11,256,659 --
    # in FY2021, FY2022 and FY2023, three books, the same pair. Three independent scans do
    # not misread the same digit the same way; the town's own table is off by a dollar.
    TOL = 1.0
    out = []
    for i in range(5):
        comp = collections.defaultdict(float)
        for r in rows:
            if r['as_of_fy'] == derived[i]:
                comp[r['section']] += float(r['amount'])
        t = printed_tot.get(i, {})

        closed = []
        if not {'within', 'outside', 'long'} <= set(t):
            problems.append('FY%s %d: REFUSED -- the printed totals are not all readable'
                            % (fy, derived[i]))
            continue
        if abs(t['within'] + t['outside'] - t['long']) > TOL:
            problems.append('FY%s %d: REFUSED -- within + outside = %s, printed long-term %s'
                            % (fy, derived[i], f"{t['within'] + t['outside']:,.0f}",
                               f"{t['long']:,.0f}"))
            continue
        closed.append('within+outside=long')
        # A BLANK IS NOT A MISSING READING. Several columns print no short-term line at
        # all -- FY2025's own year has no note outstanding -- and the table says so by
        # printing the same figure for long-term and outstanding. So `short` absent is
        # taken as zero and the identity still has to close; it is the identity, not the
        # assumption, that decides.
        unverified_short = False
        if 'outstanding' in t:
            short = t.get('short', 0.0)
            if abs(t['long'] + short - t['outstanding']) > TOL:
                problems.append('FY%s %d: REFUSED -- long + short = %s, printed outstanding %s'
                                % (fy, derived[i], f"{t['long'] + short:,.0f}",
                                   f"{t['outstanding']:,.0f}"))
                continue
            closed.append('long+short=outstanding')
        elif 'short' in t:
            # The short-term total is printed and the row that would check it is not.
            unverified_short = True
            problems.append('FY%s %d: a short-term total is printed but Total Outstanding '
                            'did not read, so the short-term rows are not published'
                            % (fy, derived[i]))

        good = set()
        for sec, key in (('inside the debt limit', 'within'),
                         ('outside the debt limit', 'outside'),
                         ('short-term', 'short')):
            if sec not in comp or (sec == 'short-term' and unverified_short):
                continue
            if key in t and abs(comp[sec] - t[key]) <= TOL:
                good.add(sec)
                closed.append('sum(%s)=%s' % (sec, key))
            else:
                problems.append('FY%s %d: the %s purposes sum to %s, printed total %s -- '
                                'those rows are not published'
                                % (fy, derived[i], sec, f'{comp[sec]:,.0f}',
                                   f"{t[key]:,.0f}" if key in t else 'unreadable'))
        mark = '|'.join(closed)
        for r in rows:
            if r['as_of_fy'] == derived[i] and r['section'] in good:
                out.append(dict(r, identities_closed=mark))
        for key, label in (('within', 'Total Within the General Debt Limit'),
                           ('outside', 'Total Outside the General Debt Limit'),
                           ('long', 'Total Long-Term Indebtedness'),
                           ('short', 'Total Short-Term Indebtedness'),
                           ('outstanding', 'Total Outstanding Indebtedness')):
            if key in t and not (unverified_short and key in ('short', 'outstanding')):
                out.append({'report_fy': fy, 'document': doc, 'page': page,
                            'as_of_fy': derived[i],
                            'as_of_basis': basis, 'section': 'printed total',
                            'category': label, 'amount': '%.0f' % t[key],
                            'identities_closed': mark})
    return out


# ------------------------------------------------------------------ REPAYMENT SCHEDULE

REPAY_HEAD = re.compile(r'DEBT REPAYMENT SCHE[DC]ULE', re.I)
GRAND = [
    (re.compile(r'GRAND\W*T[OU]T[AU]L\W*PRINCIPAL\W*(&|AND)\W*INTEREST', re.I), 'pi'),
    (re.compile(r'GRAND\W*T[OU]T[AU]L\W*PRINCIPAL', re.I), 'principal'),
    (re.compile(r'GRAND\W*T[OU]T[AU]L\W*INTEREST', re.I), 'interest'),
    (re.compile(r'GRAND\W*T[OU]T[AU]L\W*M\w*PAT\W*ADMIN', re.I), 'admin'),
    (re.compile(r'^T[OU]T[AU]L\W*DE[BES][TFI]\b', re.I), 'total'),
]


ONLY_YEARS = re.compile(r'^[\s\W]*(?:(?:19|20)\d\d[\s\W]*)+$')
YEAR_TOKEN = re.compile(r'(?:19|20)\d\d')


def year_boxes(boxes):
    """Year headings, one per year, splitting a box that swallowed several.

    Vision returns `2026 2027 2028` and `2035 2036|` as single observations on these
    header rows. Left whole they are three columns reported as none, and the run stops
    being consecutive -- which is how FY2013 and FY2022 came back as `the FISCAL YEAR
    header did not read`.
    """
    out = []
    for b in boxes:
        t = b['text']
        if not ONLY_YEARS.match(t):
            continue
        n = float(len(t))
        for m in YEAR_TOKEN.finditer(t):
            out.append((b['x'] + b['w'] * (m.end() / n), int(m.group(0)), b['y']))
    return out


def year_grid(raw, problems, where):
    """The column grid, MEASURED from the header's own spacing rather than assumed.

    A repayment schedule's columns are CONSECUTIVE fiscal years at a fixed pitch, so the
    pitch and the first year can be fitted from the readings and every reading then votes
    on the fit. That is what makes a misread survivable without guessing: FY2017 prints
    2029 and Vision returns `2022`, FY2021 prints `2022.` twice. It also recovers a column
    whose heading did not read at all, because the grid is continuous where the readings
    are not -- but ONLY between the leftmost and rightmost year actually read, never
    extrapolated past them, or the schedule's `TOTAL` column would be handed a year.

    Returns (right edges, years) or (None, None) if two thirds of the readings do not
    agree with the fit.
    """
    if len(raw) < 5:
        problems.append('%s: the FISCAL YEAR header did not read (%d years)' % (where, len(raw)))
        return None, None
    hy = statistics.median([y for _, _, y in raw])
    pts = sorted((x, v) for x, v, y in raw if abs(y - hy) < 0.02)
    gaps = [(xb - xa) / (vb - va) for (xa, va) in pts for (xb, vb) in pts
            if 0 < vb - va <= 8 and 0.015 < (xb - xa) / (vb - va) < 0.09]
    if len(gaps) < 4:
        problems.append('%s: the year header has no measurable column pitch' % where)
        return None, None
    gap = statistics.median(gaps)
    x0 = pts[0][0]
    bases = collections.Counter(v - round((x - x0) / gap) for x, v in pts)
    base, agree = bases.most_common(1)[0]
    if agree < 0.67 * len(pts):
        problems.append('%s: the year header is not a consecutive run (%d of %d columns '
                        'agree with a %.3f pitch) -- REFUSED' % (where, agree, len(pts), gap))
        return None, None
    kmax = round((pts[-1][0] - x0) / gap)
    if not 0 < kmax < 40:
        problems.append('%s: the year header spans %d columns -- REFUSED' % (where, kmax + 1))
        return None, None
    if agree < len(pts):
        problems.append('%s: %d of %d header years misread or unread; the grid is fitted at '
                        'a %.3f pitch, %d-%d' % (where, len(pts) - agree, len(pts), gap,
                                                 base, base + kmax))
    return [x0 + k * gap for k in range(kmax + 1)], [base + k for k in range(kmax + 1)]


def read_repayment(fy, doc, pages, problems):
    out = []
    for page in find_pages(pages, REPAY_HEAD):
        boxes = deskew(split_merged(upright(pages[page])))
        hits = {}
        for b in boxes:
            t = re.sub(r'\s+', ' ', b['text']).strip(' .,')
            for pat, key in GRAND:
                if pat.search(t) and key not in hits:
                    hits[key] = b
                    break
        # THE BLOCK HAS TWO SHAPES, AND ASSUMING ONE LOSES SEVEN REPORTS. FY2011 to
        # FY2017 print three rows -- GRAND TOTAL PRINCIPAL, GRAND TOTAL INTEREST, TOTAL
        # DEBT -- and from FY2019 the town adds GRAND TOTAL PRINCIPAL & INTEREST and GRAND
        # TOTAL MWPAT ADMIN FEES between them. So the identity is read off the rows the
        # page actually prints rather than off one remembered layout.
        if 'total' not in hits or 'principal' not in hits or 'interest' not in hits:
            continue

        # THE YEAR HEADER NAMES THE COLUMNS, fitted against itself. See `year_grid`.
        centres, names = year_grid(year_boxes(boxes), problems, 'FY%s page %d' % (fy, page))
        if centres is None:
            continue

        figs = [b for b in boxes if money(b['text']) is not None]
        labels = list(hits.values())
        ys = sorted({round(l['Y'], 4) for l in labels})
        pitch = statistics.median([b - a for a, b in zip(ys, ys[1:])] or [0.012])
        owned = rows_by_nearest_label(figs, labels, pitch)
        got = {}
        for key, lab in hits.items():
            cols = place([f for f in owned.get(id(lab), []) if f['x'] > lab['x'] + lab['w'] - 0.01],
                         centres)
            got[key] = {i: money(g[0]['text']) for i, g in cols.items() if len(g) == 1}

        # A GUARD AGAINST A COMPENSATING OCR ERROR, and it is a guard rather than a proof.
        #
        # `principal + interest = TOTAL DEBT` has no power to fail when the SAME character
        # is misread in an addend and in the sum. FY2017 page 42 is the worked example:
        # the currency sign is read as a `3` in two eight-digit figures on one column, so
        # `$1,399,353` becomes `31,399,353` and `$2,050,366` becomes `32,050,366`, both
        # gain exactly $30,000,000, and the column foots perfectly at twenty times the
        # size of every other year on the page. Published, it would say the town owed
        # $32m of debt service in a single year.
        #
        # So a figure more than eight times the median of its own row is refused. Only
        # LARGE outliers: the tail years of a schedule are legitimately a hundredth of the
        # first, and the admin fee runs from $3,396 to $109 by design.
        scale = {}
        for key, cols in got.items():
            vals = [abs(v) for v in cols.values() if v]
            if len(vals) >= 5:
                scale[key] = statistics.median(vals) * 8

        kept = 0
        for i, due in enumerate(names):
            v = {k: got.get(k, {}).get(i) for k in ('principal', 'interest', 'pi', 'admin', 'total')}
            if None in (v['total'], v['principal'], v['interest']):
                continue
            big = [k for k, x in v.items()
                   if x is not None and k in scale and abs(x) > scale[k]]
            if big:
                problems.append('FY%s due %d: %s is %s, more than eight times the median of '
                                'its row -- a currency sign read as a digit; REFUSED'
                                % (fy, due, big[0], f'{v[big[0]]:,.0f}'))
                continue
            pi = v['principal'] + v['interest']
            if v['pi'] is not None and abs(pi - v['pi']) > 1.0:
                problems.append('FY%s due %d: principal + interest = %s, printed %s'
                                % (fy, due, f'{pi:,.0f}', f"{v['pi']:,.0f}"))
                continue
            admin = v['admin'] if v['admin'] is not None else 0.0
            if abs(pi + admin - v['total']) > 1.0:
                problems.append('FY%s due %d: principal + interest + admin fee = %s, printed '
                                'TOTAL DEBT %s' % (fy, due, f'{pi + admin:,.0f}',
                                                   f"{v['total']:,.0f}"))
                continue
            out.append({'report_fy': fy, 'document': doc, 'page': page,
                        'as_of': 'June 30, %s' % fy,
                        'due_fy': due, 'principal': '%.0f' % v['principal'],
                        'interest': '%.0f' % v['interest'],
                        'principal_and_interest': '%.0f' % (v['pi'] if v['pi'] is not None else pi),
                        'mwpat_admin_fee': '' if v['admin'] is None else '%.0f' % v['admin'],
                        'total_debt': '%.0f' % v['total']})
            kept += 1
        if not kept:
            problems.append('FY%s page %d: no year column in the grand-total block foots'
                            % (fy, page))
    return out


def write(path, fields, rows, check):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    if check:
        cur = open(path, encoding='utf-8', newline='').read() if os.path.exists(path) else ''
        if cur != buf.getvalue():
            print('  STALE: %s -- run python3 scripts/extract_debt_tables.py'
                  % os.path.relpath(path, ROOT))
            return 1
        print('  %s is current' % os.path.relpath(path, ROOT))
        return 0
    open(path, 'w', encoding='utf-8', newline='').write(buf.getvalue())
    print('wrote %s (%d rows)' % (os.path.relpath(path, ROOT), len(rows)))
    return 0


def provenance(five, repay, detail, refused, problems):
    """The note beside the data, with every count DERIVED. Rule 2 covers this file too."""
    L = []
    A = L.append
    A('# The two debt tables in the annual town reports — what was read, and what was refused')
    A('')
    A('**Generated by `scripts/extract_debt_tables.py`. Do not edit.**')
    A('')
    A('Two printed tables share the subject `debt` in `annual-report-pages.csv` and are')
    A('nothing alike. They are read into two datasets, and neither is published where the')
    A("document's own arithmetic does not close on it. The script's docstring carries the")
    A('method; this note carries the result.')
    A('')
    A('## FIVE YEARS OUTSTANDING DEBT')
    A('')
    A('`sources/data/outstanding-debt.csv`. Principal outstanding on 30 June, by purpose,')
    A('inside and outside the Chapter 44 debt limit.')
    A('')
    A('**Two files here have almost the same name and one of them is dead.**')
    A('`sources/data/debt-outstanding.csv` is the earlier attempt at this same table; it is')
    A('one line long — a header and no rows — and `scripts/extract_debt_outstanding.py`')
    A('still produces nothing, because it looks for the year header in the first eight')
    A('lines of a page rendering whose origin is at the BOTTOM left, where the header is in')
    A('the last eight. That is a fact about the renderer, not about the reports. Retiring')
    A('one of the two names is a decision for a person, not for this script, which is why')
    A('both are still on disk.')
    A('')
    reports = sorted({r['report_fy'] for r in five})
    years = sorted({int(r['as_of_fy']) for r in five})
    A('- **%d rows**, from **%d** annual reports, covering **FY%d to FY%d**.'
      % (len(five), len(reports), years[0], years[-1]))
    kinds = collections.Counter(r['section'] for r in five)
    A('- By section: ' + ', '.join('%s %d' % (k, v) for k, v in sorted(kinds.items())) + '.')
    A('')
    A('### The headline series, and how many books agree on each year')
    A('')
    A('Each fiscal year is printed by up to five different reports, four years apart, off')
    A('the same ledger. This is the check almost nothing else in the archive gets.')
    A('')
    A('| as of 30 June | total long-term indebtedness | reports printing it | agree |')
    A('|---|---:|---:|---|')
    by_year = collections.defaultdict(dict)
    for r in five:
        if r['category'] == 'Total Long-Term Indebtedness':
            by_year[int(r['as_of_fy'])][r['report_fy']] = int(r['amount'])  # one page per report
    for yr in sorted(by_year):
        vals = sorted(set(by_year[yr].values()))
        A('| FY%d | %s | %d | %s |'
          % (yr, ' / '.join(f'{v:,}' for v in vals), len(by_year[yr]),
             'yes' if len(vals) == 1 else 'NO — see below'))
    A('')
    dis = {y: v for y, v in by_year.items() if len({*v.values()}) > 1}
    for yr, v in sorted(dis.items()):
        A('**FY%d does not agree.** %s. One dollar, and this file does not say which book is'
          % (yr, '; '.join('FY%s prints %s' % (k, f'{x:,}') for k, x in sorted(v.items()))))
        A('right: the difference is below what either scan can settle, and nothing here tests it.')
        A('')
    A('## DEBT REPAYMENT SCHEDULE — the grand totals only')
    A('')
    A('`sources/data/debt-repayment.csv`. What falls due in each FUTURE fiscal year.')
    A('')
    rrep = sorted({r['report_fy'] for r in repay})
    A('- **%d rows**, from **%d** reports, for **%d** distinct due years.'
      % (len(repay), len(rrep), len({r['due_fy'] for r in repay})))
    A('- Reports represented: %s.' % ', '.join('FY' + r for r in rrep))
    A('')
    A('## DEBT REPAYMENT SCHEDULE — the per-issue detail')
    A('')
    A('`sources/data/debt-repayment-detail.csv`, and what would not read in')
    A('`sources/data/debt-repayment-detail-refused.csv`.')
    A('')
    A('**On a scan this table cannot be read, and that was taken for a fact about the')
    A('archive.** It is twenty to twenty-five narrow columns of small type, and Apple')
    A('Vision returns it as runs like `52782335 52547440 52531098`. What was never checked')
    A('is whether every report IS a scan. Five are not: their PDFs carry a real text layer')
    A('and the schedule reads exact to the dollar out of it, with no OCR anywhere.')
    A('')
    dpages = sorted({(r['report_fy'], int(r['page'])) for r in detail})
    drep = sorted({r['report_fy'] for r in detail})
    A('- **%d rows** off **%d pages** in **%d** reports: %s.'
      % (len(detail), len(dpages), len(drep), ', '.join('FY' + r for r in drep)))
    A('- **%d issues** and **%d due years**, plus the TOTAL column each schedule prints.'
      % (len({(r['report_fy'], r['issue_seq']) for r in detail}),
         len({r['due_fy'] for r in detail if r['due_fy'] != 'TOTAL'})))
    A('- Every row closes the identity its own table states: **principal + interest')
    A('  (+ MWPAT admin fee where one is printed) = the issue total**, to the dollar. '
      '%d of them also sit in a year column whose issues sum to the page\'s own printed '
      'GRAND TOTAL.' % sum(1 for r in detail if r['column_foots'] == 'yes'))
    A('- **%d pages are refused**, listed in the refusal file with what is actually on'
      % len(refused))
    A('  them. %d of them are scans with no text layer at all.'
      % sum(1 for r in refused if 'scanned image' in r['reason']))
    A('')
    A('**Where a column does not foot, the shortfall is printed rather than hidden behind')
    A('a no.** Two kinds turn up and they are not alike. FY2014, FY2016 and FY2025 are out')
    A('by one dollar in some columns — the town rounding its own total. FY2015 is out by')
    A('exactly the two MS-HS CONSTRUCTION bonds: $625,000 in 2016, $640,000 in 2017,')
    A('$665,000 in 2018, and so on down the row. Those bonds are printed in the table and')
    A('left out of the line that totals it. Nothing here tests why.')
    A('')
    A('**A due year is not cross-checkable between reports.** A year of OUTSTANDING debt is')
    A('history and two books must agree; a year of future debt SERVICE moves every time the')
    A('town issues a bond. Both readings are right.')
    A('')
    A('## Everything refused, and why')
    A('')
    A('%d refusals and warnings. This list is the dataset as much as the rows are.' % len(problems))
    A('')
    for line in problems:
        A('- %s' % line)
    A('')
    return '\n'.join(L)



# ======================================================================================
# THE PER-ISSUE DETAIL, OFF THE PDF'S OWN TEXT LAYER
# ======================================================================================
#
# The docstring above says the issue-level schedule is unread because twenty-odd narrow
# columns of small type come back from Vision as `52782335 52547440 52531098`. That was a
# statement about the SCANS, and rule 13c says a matcher that finds nothing is a statement
# about our instrument. It is: five of the sixteen reports did not arrive as scans at all.
#
#     python3 -c "import pdfplumber; ..." on FY2016 page 44 returns 4,531 characters and
#     628 words. `A row of it: PRINCIPAL $10,651` -- exact, to the dollar, no OCR anywhere.
#
# So the schedule is read TWICE by this script, from two different instruments:
#
#   * the GRAND-TOTAL block, from the Vision boxes, for every report -- `read_repayment`.
#   * the PER-ISSUE detail, from the PDF text layer, for the reports that HAVE one --
#     this section. Where a report is image-only the detail stays unread and the page is
#     written to `debt-repayment-detail-refused.csv` with what is actually on it.
#
# Three things about the text layer that are not obvious.
#
# 1. **Most of these pages are landscape content on a portrait page, drawn ROTATED, and
#    the page's own `/Rotate` is 0.** The characters carry the rotation in their text
#    matrix instead: `(0.0, 0.418, -0.335, 0.0, ...)` on FY2014 page 40. Read without
#    normalising that, a row comes out as a vertical column of single letters and
#    `extract_text()` returns `RAEY LACSIF` -- FISCAL YEAR, backwards. Nothing about this
#    is a tolerance to tune: the matrix says which way the glyph faces, so the transform
#    is exact. Rule 13b's "measure the rotation, do not fight it" has an easy form here --
#    the document states it.
#
# 2. **A label and the figure beside it can be drawn with no gap at all.** FY2018 page 49
#    holds `OBLIGATIO$N82,060` -- the `$` of $82,060 is positioned between the O and the N
#    of OBLIGATION. Grouping characters into words by spacing therefore cannot be trusted
#    to separate the two. Figures are matched on the LINE, by `\$[\d,]+`, and placed by
#    the right edge of the last character of the match, which that overlap does not move.
#
# 3. **A page may print the same year column twice.** FY2016 page 46 is headed
#    `FISC AL YEAR 2030 2031 2032 2040 ... 2047 TOTAL`, and its first three columns repeat
#    what page 45 already printed for 2030-2032 -- MUNICIPAL PURPOSE SEWER principal reads
#    $43,109 / $44,995 / $46,963 in both places. They are not a misread header: they agree
#    to the dollar with the other page. They are published from both pages, and the
#    agreement is reported, because two printings agreeing is a check and not a problem.
#
# WHAT PROVES A ROW. The table states an identity about every cell it prints:
#
#     PRINCIPAL + INTEREST = TOTAL <issue>,  in each year column, for each issue
#
# and a row is written only where that closes TO THE DOLLAR. No tolerance. Where a column
# prints two of the three the third is taken as zero and `cells_printed` says so, because
# an issue that has retired its interest prints nothing rather than `$0` on some rows and
# `$0` on others -- MASS WATER POOL 13 prints twelve zeros against thirteen principals.
#
# And then the page's own foot, which is the guard against a compensating error: the issue
# principals in a column must sum to GRAND TOTAL PRINCIPAL, and the interests to GRAND
# TOTAL INTEREST. A figure placed in the wrong column breaks its own row identity AND that
# sum, in two places at once, which is why placing by right edge is safe to do at all.
# `column_foots` records the result per cell. A continuation page whose earlier issues are
# on an image-only page -- FY2018 page 49 is exactly that -- cannot foot, and says so
# rather than being dropped: its own row identities still hold.

DETAIL_FIELDS = ['report_fy', 'document', 'page', 'as_of', 'issue_seq', 'issue', 'due_fy',
                 'principal', 'interest', 'admin_fee', 'total', 'cells_printed',
                 'rows_offset', 'column_foots']
REFUSED_FIELDS = ['report_fy', 'document', 'page', 'subject', 'reason', 'evidence']

OUT_DETAIL = os.path.join(ROOT, 'sources', 'data', 'debt-repayment-detail.csv')
OUT_DETAIL_REFUSED = os.path.join(ROOT, 'sources', 'data', 'debt-repayment-detail-refused.csv')

DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')

# A FIGURE ON THESE PAGES IS `$n,nnn` AND NEVER CARRIES CENTS, and the trailing guard is
# load-bearing: `MS-HS CONSTRUCTION $9,000,000.00` prints the bond's FACE amount beside
# the issue's name, and a looser pattern reads `$9` out of it. That is not a harmless
# stray -- a label line that appears to hold a figure is not treated as the start of a new
# issue, so the two school bonds folded into the block above them and every year column on
# the page stopped footing to its own printed grand total. The foot is what caught it.
FIGURE = re.compile(r'\$\d{1,3}(?:,\d{3})*(?![\d,.])')
ROW_KINDS = ('PRINCIPAL', 'INTEREST', 'TOTAL', 'GRAND')


def _orientation(chars):
    """Which way the glyphs face, from the text matrix -- 0, 90, 180 or 270."""
    c = collections.Counter()
    for ch in chars:
        if not ch['text'].strip():
            continue
        m = ch.get('matrix')
        if not m:
            continue
        a, b = m[0], m[1]
        if abs(a) >= abs(b):
            c['0' if a > 0 else '180'] += 1
        else:
            c['90' if b > 0 else '270'] += 1
    return c.most_common(1)[0][0] if c else '0'


def _char_orientation(ch):
    m = ch.get('matrix')
    if not m:
        return '0'
    a, b = m[0], m[1]
    if abs(a) >= abs(b):
        return '0' if a > 0 else '180'
    return '90' if b > 0 else '270'


def _upright_chars(page):
    """Every character on the page in reading coordinates: x rightward, y downward.

    ONLY the characters that face the way the TABLE does. FY2025 page 39 prints its
    running head, `DEBT REPAYMENT SCHEDULE`, upright on a page whose schedule is turned
    270 degrees. Rotate the page to read the table and those 27 characters scatter through
    it, one per row, which is why that page reads `EPRINCIPAL`, `STOTAL SCH GENERAL
    OBLIGATION` and `NINTEREST`. A glyph's own matrix says which way it faces, so the ones
    that do not belong to the table can be dropped exactly rather than by a size threshold.
    """
    chars = page.dedupe_chars(tolerance=0.5).chars
    o = _orientation(chars)
    chars = [c for c in chars if not c['text'].strip() or _char_orientation(c) == o]
    out = []
    for ch in chars:
        x0, x1, y0, y1 = ch['x0'], ch['x1'], ch['y0'], ch['y1']
        if o == '0':
            nx0, nx1, nt, nb = x0, x1, -y1, -y0
        elif o == '180':
            nx0, nx1, nt, nb = -x1, -x0, y0, y1
        elif o == '90':
            nx0, nx1, nt, nb = y0, y1, x0, x1
        else:
            nx0, nx1, nt, nb = -y1, -y0, -x1, -x0
        out.append({'t': ch['text'], 'x0': nx0, 'x1': nx1, 'top': nt, 'bot': nb})
    out.sort(key=lambda c: (round(c['top'], 1), c['x0']))
    return out, o


def _lines(chars):
    """Characters banded into printed lines, each carrying its string and its char boxes.

    The band is the page's own median line pitch, halved -- rule 13b. It is not a constant:
    FY2014 sets the schedule at 4.1pt and FY2022's warrant at 11pt, and a guessed band that
    holds one together splits the other.
    """
    if not chars:
        return []
    tops = sorted({round(c['top'], 1) for c in chars})
    gaps = [b - a for a, b in zip(tops, tops[1:]) if 0.5 < b - a < 40]
    band = (statistics.median(gaps) / 2.0) if gaps else 2.0
    rows = []
    for c in chars:
        if rows and abs(c['top'] - rows[-1][0]['top']) < band:
            rows[-1].append(c)
        else:
            rows.append([c])
    out = []
    for r in rows:
        r.sort(key=lambda c: c['x0'])
        s, boxes = [], []
        prev = None
        for c in r:
            if prev is not None and c['x0'] - prev > 1.2:
                s.append(' ')
                boxes.append(None)
            s.append(c['t'])
            boxes.append(c)
            prev = c['x1']
        out.append({'text': ''.join(s), 'boxes': boxes, 'top': r[0]['top']})
    return out


def _figures(line):
    """Every `$n,nnn` on a line, with the right edge of its last character."""
    figs = []
    for m in FIGURE.finditer(line['text']):
        boxes = [b for b in line['boxes'][m.start():m.end()] if b]
        if not boxes:
            continue
        figs.append({'v': float(m.group(0)[1:].replace(',', '')),
                     'x1': max(b['x1'] for b in boxes),
                     'start': m.start()})
    return figs


def _header_years(lines):
    """The year columns, NAMED off the printed header. Never inferred from order.

    Rule 13c, in its smallest form: the header is not printed the same way twice.
    FY2016 page 46 breaks the word itself -- `FISC AL YEAR` -- and FY2014 page 42, the
    last sheet of that year's schedule, prints no FISCAL YEAR at all: its two remaining
    year headings sit on the same line as the first issue's name,
    `MASS WATER POOL 3* 2046 2047   TOTAL`. So the header is whichever line first carries
    two or more four-digit years, and whatever is printed to the LEFT of the first of them
    is handed back as a label, because on that page it is one.
    """
    for i, ln in enumerate(lines):
        cols = []
        for m in re.finditer(r'\b(20[0-9]{2})\b|\bTOTAL\b', ln['text']):
            boxes = [b for b in ln['boxes'][m.start():m.end()] if b]
            if boxes:
                cols.append({'name': m.group(0), 'start': m.start(),
                             'c': (min(b['x0'] for b in boxes) + max(b['x1'] for b in boxes)) / 2})
        # THE TITLE LINE ALSO HOLDS YEARS. FY2014 page 40 prints its title twice --
        # `...AS OF JUNE 30, 2014 TOWN OF LUNENBURG ... JUNE 30 2014` -- so a rule of
        # "two four-digit years makes a header" picks the title and reads no column at
        # all. A column header's years are DISTINCT and ascend; a date repeated does
        # neither.
        years = [c for c in cols if c['name'] != 'TOTAL']
        years.sort(key=lambda c: c['c'])
        vals = [int(c['name']) for c in years]
        if len(vals) < 2 or len(set(vals)) != len(vals) or vals != sorted(vals):
            continue
        cols.sort(key=lambda c: c['c'])
        head = re.sub(r'\s+', ' ', ln['text'][:min(c['start'] for c in cols)]).strip()
        if head.upper().startswith('FISC'):
            head = ''
        return cols, i, head
    return None, None, None


def _place(figs, cols, pitch):
    """A figure belongs to the column its RIGHT EDGE is nearest, or to none at all.

    Accounting figures are right-aligned and a `$` widens some of them, so the left edge
    and the centre both move with the digit count and the right edge does not. A figure
    further than half the column pitch from every heading is refused rather than pushed
    into the closest one -- placing by order is what puts every later figure in a row with
    a gap under the wrong year.
    """
    out = {}
    for f in figs:
        best = min(cols, key=lambda c: abs(c['c'] - f['x1']))
        if abs(best['c'] - f['x1']) > pitch * 0.75:
            continue
        out.setdefault(best['name'], []).append(f['v'])
    return {k: v[0] for k, v in out.items() if len(v) == 1}


def read_repayment_detail(fy, doc, pdf_path, catalogue_pages, ocr, problems, refused):
    """The issue-level schedule off the text layer, where the report has one."""
    rows = []
    try:
        import pdfplumber
    except ImportError:
        problems.append('pdfplumber is not installed; the per-issue detail cannot be read')
        return rows
    want = set()
    for p in catalogue_pages:
        want.update((p - 1, p, p + 1))
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for page_no in sorted(p for p in want if 1 <= p <= n):
            page = pdf.pages[page_no - 1]
            # RULE 13c: SAY WHAT IS ACTUALLY ON THE PAGE, not that a matcher found nothing.
            # A page the catalogue files under `debt` with no text layer is a scan, and
            # the refusal carries the evidence -- how many characters the PDF holds and
            # how many images are drawn on it -- so nobody has to take it on trust.
            # Which page IS a repayment schedule is decided from the Vision reading of
            # it, not from the catalogue's heading: five of these headings are the first
            # line the scanner happened to recognise (`FISCAL YEAR`, `40021012`, blank).
            # A FIVE YEARS OUTSTANDING page is read by `read_five_years` and is not
            # refused here -- a refusal has to mean something.
            seen = ' '.join(b['text'] for b in ocr.get(page_no, [])).upper()
            is_schedule = page_no in catalogue_pages and (
                'REPAYMENT' in seen or 'GRAND TOTAL' in seen or 'TOTAL DEBT' in seen)
            if len(page.chars) < 30:
                if is_schedule:
                    refused.append({
                        'report_fy': fy, 'document': doc, 'page': page_no,
                        'subject': 'debt',
                        'reason': 'the page is a scanned image; there is no text layer to '
                                  'read, and the issue columns are too narrow for Vision',
                        'evidence': '%d characters and %d image(s) in the PDF; Vision reads '
                                    '%d boxes, e.g. %r'
                                    % (len(page.chars), len(page.images),
                                       len(ocr.get(page_no, [])),
                                       next((b['text'] for b in ocr.get(page_no, [])
                                             if money(b['text']) is not None), ''))})
                continue
            chars, orient = _upright_chars(page)
            lines = _lines(chars)
            flat = ' '.join(ln['text'] for ln in lines).upper().replace(' ', '')
            if 'GRANDTOTALPRINCIPAL' not in flat:
                if is_schedule:
                    refused.append({
                        'report_fy': fy, 'document': doc, 'page': page_no,
                        'subject': 'debt',
                        'reason': 'the page carries a text layer but no repayment '
                                  'schedule in it; the table is a scanned image on top',
                        'evidence': 'the whole text layer reads %r'
                                    % ' '.join(l['text'] for l in lines)[:90]})
                continue
            cols, hidx, hlabel = _header_years(lines)
            if not cols:
                refused.append({'report_fy': fy, 'document': doc, 'page': page_no,
                                'subject': 'debt',
                                'reason': 'the year header could not be read off the page',
                                'evidence': 'first line: %r' % lines[0]['text'][:80]})
                continue
            centres = [c['c'] for c in cols]
            pitch = statistics.median([b - a for a, b in zip(centres, centres[1:])]) \
                if len(centres) > 1 else 40.0
            names = [c['name'] for c in cols]
            as_of = ''
            m = re.search(r'JUNE\s*30,?\s*(\d{4})',
                          (' '.join(l['text'] for l in lines) + ' '
                           + (page.extract_text() or '')).upper())
            if m:
                as_of = 'June 30, %s' % m.group(1)

            # A PAGE MAY PRINT ITS FIGURES ONE ROW BELOW THEIR LABELS, and FY2014 page 42
            # does: `PRINCIPAL` is bare, `INTEREST $31,011` carries MASS WATER POOL 3's
            # TOTAL PRINCIPAL, and the last figure line has no label at all. Read straight
            # off the line, nothing on that page closes. Read one row up, everything does:
            # $22,140,229 + $6,338,637 = $28,478,866, the grand total the page prints for
            # itself. So both readings are built and the DOCUMENT chooses between them --
            # a wrong alignment cannot make an identity close 57 times and foot as well,
            # which is the whole reason this is safe to attempt rather than a tuned guess.
            best = None
            for shift in (0, 1):
                got = _walk(lines, hidx, hlabel, cols, pitch, names, shift)
                if best is None or got['closed'] > best['closed']:
                    best = got
            if best['shift'] and not best['grand_closes']:
                refused.append({'report_fy': fy, 'document': doc, 'page': page_no,
                                'subject': 'debt',
                                'reason': 'the figures are printed out of line with their '
                                          'labels and the shifted reading does not foot',
                                'evidence': '%d of %d cells close at the printed alignment'
                                            % (best['closed'], best['closed'] + best['open'])})
                continue
            if not best['cells']:
                refused.append({'report_fy': fy, 'document': doc, 'page': page_no,
                                'subject': 'debt',
                                'reason': 'no issue block on the page held a readable row',
                                'evidence': 'header columns: %s' % ' '.join(names)})
                continue
            for c in best['cells']:
                c.update({'report_fy': fy, 'document': doc, 'page': page_no, 'as_of': as_of})
                rows.append(c)
            if best['open']:
                problems.append('FY%s page %d: %d of %d issue cells do not close '
                                'principal + interest (+ admin fee) = total'
                                % (fy, page_no, best['open'], best['open'] + best['closed']))
    return rows


def _walk(lines, hidx, hlabel, cols, pitch, names, shift):
    """One reading of a schedule page: issue blocks, their cells, and what closes.

    `shift` is how many printed lines separate a label from the figures that belong to
    it -- 0 everywhere but the pages where the figure column was pasted a row low.
    """
    issue, seq = '', 0
    if hlabel:
        seq, issue = 1, hlabel.upper()
    blocks = collections.OrderedDict()
    grand = {}
    for i in range(hidx + 1, len(lines)):
        own = _figures(lines[i])
        src = lines[i + shift] if i + shift < len(lines) else None
        figs = _figures(src) if src is not None else []
        head = lines[i]['text'][:own[0]['start']].strip() if own else lines[i]['text'].strip()
        head = re.sub(r'\s+', ' ', head).upper().strip(' $')
        if not head:
            continue
        if head.startswith('GRAND TOTAL') or head.startswith('TOTAL DEBT'):
            grand[head] = _place(figs, cols, pitch)
            continue
        for word, kind in (('PRINCIPAL', 'PRINCIPAL'), ('INTEREST', 'INTEREST'),
                           ('ADMIN FEE', 'ADMIN'), ('MWPAT ADMIN', 'ADMIN')):
            if head.startswith(word):
                blocks.setdefault((seq, issue), {}).setdefault(kind, {}).update(
                    _place(figs, cols, pitch))
                break
        else:
            if head.startswith('TOTAL'):
                blocks.setdefault((seq, issue), {}).setdefault('TOTAL', {}).update(
                    _place(figs, cols, pitch))
            # A NEW ISSUE STARTS AT A LABEL THAT CARRIES NO FIGURE OF ITS OWN -- except
            # on a shifted page, where every label line carries the PREVIOUS row's
            # figure and that test would find no issues at all after the first.
            elif len(head) > 3 and not head.startswith('*') and (shift or not own):
                seq += 1
                issue = re.sub(r'\s*\$[\d,.]+$', '', head).strip()

    # The page's own foot, per column: the issues must sum to the grand total.
    # THE FOOT SAYS BY HOW MUCH, not merely yes or no, because the differences here are
    # the finding. FY2016 page 44 is out by exactly $1 in two of its twelve columns --
    # the town's own rounding. FY2015 page 42 is out by exactly $625,000 in 2016,
    # $640,000 in 2017, $665,000 in 2018: in every column the shortfall is precisely the
    # two MS-HS CONSTRUCTION bonds' principal for that year, which are printed in the
    # table and left out of the row that totals it. An `out by` that is a round number
    # equal to a block on the same page is a different animal from one that is a dollar,
    # and collapsing both to `no` would hide it.
    foots = {}
    for name in names:
        parts, missing = [], False
        for letter, kind, key in (('principal', 'PRINCIPAL', 'GRAND TOTAL PRINCIPAL'),
                                  ('interest', 'INTEREST', 'GRAND TOTAL INTEREST')):
            tot = grand.get(key, {}).get(name)
            if tot is None:
                missing = True
                continue
            got = sum(b.get(kind, {}).get(name, 0.0) for b in blocks.values())
            if abs(got - tot) >= 0.5:
                parts.append('%s out by %s' % (letter, format(got - tot, '+,.0f')))
        foots[name] = ('; '.join(parts) if parts
                       else 'no grand total printed' if missing else 'yes')

    # GRAND TOTAL PRINCIPAL + GRAND TOTAL INTEREST = TOTAL DEBT, the identity the block
    # states about itself. It is what decides between two readings of the same page.
    gp, gi = grand.get('GRAND TOTAL PRINCIPAL', {}), grand.get('GRAND TOTAL INTEREST', {})
    gd = grand.get('TOTAL DEBT', {})
    ga = grand.get('GRAND TOTAL MWPAT ADMIN FEES', {})
    checked = [abs(gp[k] + gi[k] + ga.get(k, 0.0) - gd[k]) < 0.5
               for k in gd if k in gp and k in gi]
    grand_closes = bool(checked) and all(checked)

    cells, closed, still_open = [], 0, 0
    for (sq, name), kinds in blocks.items():
        for col in names:
            pr = kinds.get('PRINCIPAL', {}).get(col)
            it = kinds.get('INTEREST', {}).get(col)
            ad = kinds.get('ADMIN', {}).get(col)
            tt = kinds.get('TOTAL', {}).get(col)
            printed = ''.join(k for k, v in (('P', pr), ('I', it), ('A', ad), ('T', tt))
                              if v is not None)
            if len(printed) < 2 or 'T' not in printed:
                if printed:
                    still_open += 1
                continue
            if abs((pr or 0.0) + (it or 0.0) + (ad or 0.0) - tt) >= 0.5:
                still_open += 1
                continue
            closed += 1
            cells.append({'issue_seq': sq, 'issue': name, 'due_fy': col,
                          'principal': '%.0f' % (pr or 0.0),
                          'interest': '%.0f' % (it or 0.0),
                          'admin_fee': '%.0f' % (ad or 0.0) if ad is not None else '',
                          'total': '%.0f' % tt,
                          'cells_printed': printed,
                          'rows_offset': shift,
                          'column_foots': foots.get(col, '')})
    return {'cells': cells, 'closed': closed, 'open': still_open, 'shift': shift,
            'grand_closes': grand_closes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()

    five, repay, detail, problems, refused = [], [], [], [], []
    # WHERE THE ISSUE-LEVEL SCHEDULE IS PRINTED. The catalogue is the index into the
    # reports and is consulted rather than a page number being typed in -- its `debt`
    # pages, widened by one either side, because a schedule that runs onto a fourth page
    # has been filed under a heading the cataloguer read as something else (FY2014 page
    # 41 is a repayment page that the catalogue does not list as one).
    debt_pages = collections.defaultdict(set)
    cat = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')
    with open(cat, encoding='utf-8') as fh:
        head = fh.readline().rstrip('\n').split(',')
        fh.seek(0)
        rdr = csv.DictReader(fh)
        for r in rdr:
            if r.get('subject') == 'debt':
                debt_pages[r['fy']].add(int(r['page']))
    # THE ADDENDUM IS A REPORT. FY2016 was published in two volumes and the second holds
    # a debt repayment schedule of its own -- twelve proven year columns that a glob
    # ending `annual-town-report.tsv` walks straight past.
    for path in sorted(glob.glob(os.path.join(OCR, '*annual-town-report*.tsv'))):
        fy = re.search(r'fy-(\d{4})', path).group(1)
        doc = os.path.basename(path)[:-4] + '.pdf'
        pages = load(path)
        five += read_five_years(fy, doc, pages, problems)
        repay += read_repayment(fy, doc, pages, problems)
        pdf_path = os.path.join(DOCS, doc)
        if debt_pages.get(fy) and os.path.exists(pdf_path):
            detail += read_repayment_detail(fy, doc, pdf_path, sorted(debt_pages[fy]),
                                            pages, problems, refused)
    five.sort(key=lambda r: (r['report_fy'], r['document'], -int(r['as_of_fy']),
                             r['section'], r['category']))
    repay.sort(key=lambda r: (r['report_fy'], r['document'], r['due_fy']))
    detail.sort(key=lambda r: (r['report_fy'], int(r['page']), int(r['issue_seq']),
                               r['due_fy']))
    refused.sort(key=lambda r: (r['report_fy'], int(r['page'])))

    # THE CROSS-REPORT CHECK: one fiscal year, printed in up to five different books.
    seen = collections.defaultdict(dict)
    for r in five:
        if r['category'] == 'Total Long-Term Indebtedness':
            seen[r['as_of_fy']][r['document']] = float(r['amount'])
    agree = disagree = 0
    for yr, by_report in sorted(seen.items()):
        if len(by_report) < 2:
            continue
        if len({round(v) for v in by_report.values()}) == 1:
            agree += 1
        else:
            disagree += 1
            problems.append('FY%s total long-term indebtedness is printed %s by %s'
                            % (yr, ' and '.join(f'{v:,.0f}' for v in sorted(set(by_report.values()))),
                               ' and '.join('FY' + k for k in sorted(by_report))))

    print('FIVE YEARS OUTSTANDING DEBT: %d rows, %d reports, %d as-of years that foot'
          % (len(five), len({r['report_fy'] for r in five}), len({r['as_of_fy'] for r in five})))
    print('  cross-report: %d fiscal years agree across reports, %d do not' % (agree, disagree))
    # THE SCHEDULE IS NOT CROSS-CHECKABLE THE WAY THE OUTSTANDING TABLE IS, and saying so
    # is the point of this block. A year of OUTSTANDING debt is history: FY2019 and FY2023
    # must print the same figure for FY2019 or one of them is wrong. A year of FUTURE debt
    # SERVICE is not: the FY2011 book shows $155,945 falling due in FY2032 because that is
    # what the town owed on the debt it had THEN, and the FY2021 book shows $2,303,500
    # because two school bonds were issued in between. Both are right. So the overlap is
    # reported as movement, never as a disagreement to be resolved.
    due = collections.defaultdict(dict)
    for r in repay:
        due[r['due_fy']][r['document']] = float(r['total_debt'])
    ragree = rdis = 0
    for yr, by_report in sorted(due.items()):
        if len(by_report) < 2:
            continue
        if len({round(v) for v in by_report.values()}) == 1:
            ragree += 1
        else:
            rdis += 1
    print('DEBT REPAYMENT SCHEDULE (grand totals): %d rows, %d reports, %d due years that foot'
          % (len(repay), len({r['report_fy'] for r in repay}), len({r['due_fy'] for r in repay})))
    print('  %d due years are printed by more than one report: %d unchanged, %d moved as '
          'new debt was issued (both are correct -- see the note in read_repayment)'
          % (ragree + rdis, ragree, rdis))
    shown = problems if a.verbose else problems[:14]
    for p in shown:
        print('  %s' % p)
    if len(problems) > len(shown):
        print('  ...and %d more (--verbose)' % (len(problems) - len(shown)))

    print('DEBT REPAYMENT SCHEDULE (issue detail): %d rows, %d reports, %d pages; '
          '%d rows sit in a column that foots to the page\'s own grand total'
          % (len(detail), len({r['report_fy'] for r in detail}),
             len({(r['report_fy'], r['page']) for r in detail}),
             sum(1 for r in detail if r['column_foots'] == 'yes')))
    print('  %d pages refused, in %d reports'
          % (len(refused), len({r['report_fy'] for r in refused})))

    rc = write(OUT_OUTSTANDING, OUTSTANDING_FIELDS, five, a.check)
    rc |= write(OUT_DETAIL, DETAIL_FIELDS, detail, a.check)
    rc |= write(OUT_DETAIL_REFUSED, REFUSED_FIELDS, refused, a.check)
    rc |= write(OUT_REPAYMENT, REPAYMENT_FIELDS, repay, a.check)
    note = provenance(five, repay, detail, refused, problems)
    if a.check:
        cur = open(OUT_NOTE, encoding='utf-8').read() if os.path.exists(OUT_NOTE) else ''
        if cur != note:
            print('  STALE: %s' % os.path.relpath(OUT_NOTE, ROOT))
            rc |= 1
        else:
            print('  %s is current' % os.path.relpath(OUT_NOTE, ROOT))
    else:
        open(OUT_NOTE, 'w', encoding='utf-8').write(note)
        print('wrote %s' % os.path.relpath(OUT_NOTE, ROOT))
    return rc


if __name__ == '__main__':
    sys.exit(main())
