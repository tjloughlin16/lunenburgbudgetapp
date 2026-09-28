"""Read a TABLE off a page of an annual report: band, place, name, check.

    import page_table as PT

    import page_table as PT

    ws    = PT.words(pdf, page)              # born-digital page: its own text
    ws    = PT.boxes(tsv, page)              # a photograph: recognition
    cols  = PT.declare(ws, BAND, LAYOUT)     # the heading you READ, checked against the page
    for r in PT.rows(ws, within=BODY):       # banded on the page's MEASURED gap
        cell = PT.place(r, cols)             # each figure under the column it is printed in
    PT.check('FY2025 Option 1', ('the projects against the printed Total', run, total))

THE WORKED EXAMPLE, measured. FY2025's two capital plans, pages 138 and 139:

    LAYOUT = {'project_cost': (395, 470, 'Project Cost'),
              'cumulative':   (470, 540, 'Cumulative Cost')}

    p138  20 projects  1,225,000  breaks 0  -- CLOSES
    p139  16 projects  1,225,000  breaks 0  -- CLOSES

Twenty-five lines, and the same figures the hand-written extractor produces.

WHY THIS EXISTS

TJ, 28 September 2026: *"i think we may need an updated extractor format. you fail very
often on the extractor and spin a lot."* and *"we need a repeatable fast process to do the
next batch."*

One afternoon, one archive, one reader, four extractors. Three were written directly on word
boxes -- the trust matrix (462 figures), Monty Tech's chart, the two capital plans -- and
each took about twenty minutes and closed on the page's own arithmetic first or second try.
The fourth extended an extractor built on the page FLATTENED TO TEXT LINES and ate the rest
of the day without closing.

The tables were not the difficulty. The trust matrix prints its fund names SIDEWAYS, one per
column, and closed first time; the special revenue schedule is a plain grid and did not
close at all. What differs is whether the coordinates survive to the point of use.

And the three that worked each hand-rolled the SAME forty lines. This is those forty lines,
once, so the next extractor is thirty and not four hundred. See
`notes/process/AN-EXTRACTOR.md`.

THE FOUR RULES, AND EACH WAS PAID FOR

1. BAND ON THE MEASURED GAP, NEVER ROUND TO A GRID. Rounding y split four of nine rows on
   the Monty Tech chart: 0.427 and 0.430 round apart at any divisor near the row pitch,
   while two ADJACENT rows can round together. The within-row spread and the between-row
   pitch are both measurable -- 0.004 and 0.035 there -- and a threshold between two
   measured numbers cannot be wrong. `rows()` measures both and says so.

2. PLACE BY THE NEAREST MEASURED COLUMN, NEVER BY ORDER. A fund with nothing in a column
   prints nothing; take the figures in order and every one lands under the wrong heading
   from the first gap onward. `place()` puts each figure under the column whose centre it is
   nearest and leaves an absent column absent.

3. NAME FROM A HEADING YOU READ. A POSITION IS NOT A NAME. This is the one the old path
   cannot do at all: it renders the page back to text lines, so a column is a run of spaces
   most rows agree on -- a column no row fills does not exist, and a CENTRED heading never
   shares a character position with a RIGHT-ALIGNED figure. `Fund Balance` cut at a ruler
   measured from the figures came out `F` and `und Balance`. In the boxes that heading sits
   at x=0.554 on all four pages of the schedule, to three decimals.

4. REFUSE RATHER THAN PUBLISH. Every extractor that worked writes nothing at all unless the
   page's own arithmetic closes, so a row's existence is the verdict. `check()` is the
   scaffolding for that and it RAISES; it does not return a warning nobody reads.

WHAT THIS IS NOT FOR

Prose, and the three-column newspaper layouts whose columns are kerned rather than
positioned. Those have no measurable gutter and `report_pages` renders them correctly; that
path stays.

AND x DOES NOT ALWAYS MEAN A COLUMN. On a TABLE it does. On a BAR CHART x is the VALUE --
a label sits at the end of its segment, so Monty Tech's `Fixed Assets` FY23 is drawn at
x=0.23 and `Grants` FY25 at x=0.76 -- and there the ORDER is the column. Know which kind of
page you are on; `place()` is for tables and `series()` is for charts.
"""
import collections
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `$ 1,234.56`, `(1,234.56)`, `1,234.56-`, `$1,234`. The space after the dollar sign is not
# decoration: `$ 4,963,068.15` is how the FY2024 total is recognised, and a pattern without
# it silently drops the one figure the whole section is checked against.
# A THOUSANDS GROUP IS THREE DIGITS. `[\d,]+` accepts `3,` and `2,025`, so `May 3, 2025`
# in the prose under a table yields two figures and joins the sums -- which is how a
# running total that closed on one page came out $2 over on the next.
MONEY = re.compile(r'^\$?\s*\(?\s*\$?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d\d)?\s*\)?-?$')


def amount(text):
    """The number a cell holds, or None. Parentheses and a trailing dash are negatives.

    A BARE INTEGER IS NOT MONEY. `1`, `2`, `13` are the CPC rankings printed down the left of
    the capital table, the line numbers on a warrant article, a page number at the foot --
    and read as figures they land in whatever column they are nearest and quietly join the
    sums. The first run of this over the capital plan came out $50,000 high on one page and
    $2 high on the other, and the $2 was `Option 2` in the heading.

    So a figure must LOOK like money: a currency sign, a thousands separator, or cents. The
    town prints `$72,058` without cents and `1,500.00` without a sign, and both pass; `2`
    does not.
    """
    t = (text or '').strip()
    if not MONEY.match(t):
        return None
    if '$' not in t and ',' not in t and not re.search(r'\.\d\d', t):
        return None
    neg = (t.startswith('(') and t.endswith(')')) or t.endswith('-')
    t = t.strip('()-').replace('$', '').replace(',', '').replace(' ', '')
    if not t or not re.match(r'^\d+(\.\d\d)?$', t):
        return None
    return -float(t) if neg else float(t)


def words(pdf, page):
    """A born-digital page, as its own text: `{text, x, y, w}` per word, y down the page."""
    import pdfplumber
    with pdfplumber.open(pdf) as doc:
        return [dict(text=w['text'], x=w['x0'], y=w['top'], w=w['x1'] - w['x0'])
                for w in doc.pages[page - 1].extract_words()]


def boxes(tsv, page):
    """A photographed page, as recognition read it. Same shape as `words`.

    NOT `csv.DictReader`. These TSVs are unquoted and recognition routinely returns a double
    quote, which the csv module treats as opening a quoted field: it swallows every
    following line looking for a close and then raises `field larger than field limit`.
    """
    out = []
    for i, line in enumerate(open(tsv, encoding='utf-8')):
        if i == 0:
            continue
        f = line.rstrip('\n').split('\t')
        if len(f) >= 7 and f[0] == str(page):
            out.append(dict(text=f[6], x=float(f[1]), y=float(f[2]), w=float(f[3]),
                            conf=float(f[5])))
    return out


def has_text_layer(pdf, page, region=None, minimum=40):
    """Does this PAGE carry its own text -- and does the REGION the figures are in?

    THE GATE, in one call. A text layer supersedes recognition and the recognition of that
    page is discarded, not reconciled. But the screen is not a proof: a page can pass and
    still hold its TABLE as an image, which is what FY2025 page 115 does, so pass `region`
    as `(x0, top, x1, bottom)` when the figures live in one part of the page.
    """
    ws = words(pdf, page)
    if region:
        x0, t0, x1, t1 = region
        ws = [w for w in ws if x0 <= w['x'] <= x1 and t0 <= w['y'] <= t1]
    return len(ws) > minimum


def rows(ws, gap=None, within=None):
    """Printed rows, banded on the page's own measured gap.

    Returns `[[word, ...], ...]`, each sorted left to right, top of the page first.

    The threshold is measured, not chosen: take the gaps between consecutive y values, and
    cut where a gap exceeds the MEDIAN gap between rows. Pass `gap` only to override a page
    whose pitch genuinely cannot be measured, and say in the caller why.
    """
    if within is not None:
        # BOUND THE TABLE. A page is not a table: the prose under FY2025's capital plan
        # carries `$1,225,000` and `May 3, 2025`, and both walked into the sums.
        ws = [w for w in ws if within[0] <= w['y'] <= within[1]]
    if not ws:
        return []
    ys = sorted(ws, key=lambda w: w['y'])
    if gap is None:
        steps = sorted(b['y'] - a['y'] for a, b in zip(ys, ys[1:]) if b['y'] - a['y'] > 0)
        if not steps:
            gap = 1.0
        else:
            # TWO POPULATIONS, AND THE PAGE SEPARATES THEM ITSELF. The gaps between
            # consecutive y values are of two kinds: the jitter WITHIN a printed row, where
            # a tall glyph or a right-aligned figure sits a fraction higher than its
            # neighbour, and the PITCH between rows. On FY2025's capital table those are
            # about 1pt and 15pt; on the Monty Tech chart, normalised, 0.004 and 0.035.
            #
            # So the threshold is not a multiple of anything -- it is the midpoint of the
            # biggest RATIO jump in the sorted steps, which is where one population ends and
            # the other begins. A multiple of the median fails because the median sits in
            # whichever population has more members, and that is the jitter on a wide page
            # and the pitch on a narrow one. Multiplying it by three banded a 20-row table
            # into ONE row.
            best, gap = 0.0, steps[-1]
            for a, b in zip(steps, steps[1:]):
                if a > 0 and b / a > best:
                    best, gap = b / a, (a + b) / 2
    out = [[ys[0]]]
    for a, b in zip(ys, ys[1:]):
        if b['y'] - a['y'] > gap:
            out.append([])
        out[-1].append(b)
    return [sorted(r, key=lambda w: w['x']) for r in out]


def heading_words(ws, band):
    """The words in a heading `band` -- `(y from, y to)` in the page's own units.

    A BAND, not "everything above the first figure". FY2025 page 138 carries TWO tables --
    the tail of a transfer article at the top and the capital plan below it -- so the first
    figure on the page is not the first figure of the table you are reading.
    """
    return [w for w in ws if band[0] <= w['y'] <= band[1]]


def declare(ws, band, layout):
    """Check a layout you READ OFF THE PAGE, and return it. Refuses if the page disagrees.

    `layout` is `{name: (x from, x to, expected heading text)}`, written down by a person who
    looked at the page.

    DO NOT INFER THE COLUMNS. This is rule 13b's fourth rule -- *name columns from a header
    you read and wrote down, never inferred* -- and every extractor that worked in this
    archive obeys it while every attempt to automate it has produced confident nonsense:
    three columns of the trust matrix all claiming to be `begin_principal`, a proportional
    word-split turning one observation into `TRANSFERS PRINCIPAL / OF EARNINGS / TRANSFERS
    VALUE`, and -- on the capital table this function was first tried on -- `Project Cost`
    at x=404 and `Cumulative Cost` at x=480 collapsing into one column, because the gap
    between `Cost` and `Cumulative` is smaller than the gap between `Project` and `Cost`.
    No clustering rule separates those. A person reading the page separates them instantly.

    So the layout is DATA in the extractor, and this is the check on it: the words actually
    printed in each declared x range must contain the text declared for it. A year whose
    page disagrees is REFUSED rather than aligned, which is what makes a hand-written layout
    safe to reuse across editions -- FY2014's nine columns were proposed for four other
    years, two accepted them and two refused, and the two that refused were right to.

    Returns `{name: x centre}` for `place`.
    """
    hs = heading_words(ws, band)
    cols, bad = {}, []
    for name, (lo, hi, want) in layout.items():
        got = ' '.join(w['text'] for w in sorted(hs, key=lambda w: (w['y'], w['x']))
                       if lo <= w['x'] + w['w'] / 2 <= hi)
        got = ' '.join(got.split()).lower()
        if ' '.join(want.split()).lower() not in got:
            bad.append('  %s: the page prints %r in x %s-%s, not %r'
                       % (name, got, lo, hi, want))
        cols[name] = (lo + hi) / 2
    if bad:
        raise SystemExit('the declared layout does not match this page:\n%s\n'
                         'Read the page and write the layout down again; do not widen the '
                         'ranges until it passes.' % '\n'.join(bad))
    return cols


def place(row, cols, tolerance=0.06):
    """`{column: value}` for one row: each figure under the column it is printed in.

    A figure further than `tolerance` from every column centre is NOT placed and is returned
    under `None`, so a caller can refuse the row rather than file it under its nearest
    neighbour. Silence there is how a deficits column ends up added into fund balances.
    """
    out, stray = {}, []
    for w in row:
        v = amount(w['text'])
        if v is None:
            continue
        mid = w['x'] + w['w'] / 2
        near = min(cols, key=lambda k: abs(cols[k] - mid)) if cols else None
        if near is not None and abs(cols[near] - mid) <= tolerance:
            out[near] = v
        else:
            stray.append((round(mid, 4), w['text']))
    if stray:
        out[None] = stray
    return out


def series(row, n):
    """For a CHART, not a table: the row's figures in the ORDER they are drawn.

    On a bar chart x is the VALUE, not the column -- a label sits at the end of its segment
    -- so clustering by x files the small years together and the large years together.
    Within a row the segments are drawn in series order. A row that does not carry exactly
    `n` figures returns None rather than a guess.
    """
    vs = [amount(w['text']) for w in row]
    vs = [v for v in vs if v is not None]
    return vs if len(vs) == n else None


def label(row, before):
    """The row's text to the left of `before` (an x), joined -- its label."""
    return ' '.join((w['text'] or '').strip() for w in row
                    if w['x'] < before and amount(w['text']) is None).strip()


def check(name, *claims):
    """Every claim, or write nothing. RAISES; it does not return a warning nobody reads.

    Each claim is `(description, got, want)` compared to the cent. The message names every
    failure rather than the first, because one broken row and a broken COLUMN look the same
    from a single line and are not the same defect.
    """
    bad = ['  %s: %s against a printed %s (%+,.2f)'
           % (d, format(round(g, 2), ','), format(round(w, 2), ','), g - w)
           for d, g, w in claims if abs(g - w) > 0.02]
    if bad:
        raise SystemExit('%s does not close, nothing written:\n%s' % (name, '\n'.join(bad)))
    return True


def coverage(ws, cols, row_marker):
    """How many rows the page PRINTS against how many carry a figure.

    A gap is not proof of a defect -- 15 of FY2024 page 25's rows print a DASH, and a closed
    grant is a real row with no figure. But a gap is the ALARM, and the alarm is what was
    missing: that page prints 60 fund rows, recognition held figures for 14, and nothing
    compared the two numbers. Publish this beside any extract read off a photograph, the way
    `search_minutes.py` prints its denominator on every run and for the same reason: a
    reader who is told nothing assumes nothing was lost.

    `row_marker` is a pattern for the thing the page has exactly one of per row and which
    recognition reads reliably -- a fund number, an account code, a line number.
    """
    rs = rows(ws)
    printed = sum(1 for r in rs if any(re.match(row_marker, (w['text'] or '').strip())
                                       for w in r))
    got = sum(1 for r in rs
              if any(re.match(row_marker, (w['text'] or '').strip()) for w in r)
              and any(k is not None for k in place(r, cols)))
    return printed, got
