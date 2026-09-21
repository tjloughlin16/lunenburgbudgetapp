"""Draw the stabilization funds: what each holds, and what each has done.

    python3 scripts/build_stabilization_charts.py
    python3 scripts/build_stabilization_charts.py --check

Writes `sources/analyses/charts/stabilization-*.svg`, which the Markdown embeds and
`build_analysis_pdf.py` renders into the PDF.

WHAT THE DATA IS, AND WHAT IT IS NOT

Every point is a row from `sources/data/stabilization-balances.csv` -- a balance read off
a photograph of the town's own trust-fund table and then PROVEN against an identity the
table states about itself. Nothing is plotted that did not close.

Three consequences shape all three charts, and none of them is cosmetic:

**The years are irregular, because proof is irregular.** Zoning Incentive has FY2014,
2015, 2016, 2018, 2020, 2022, 2025. The missing years are not zero and they are not
missing data in the ordinary sense -- the town published them and our reading of those
pages has not yet closed. So a solid line between FY2022 and FY2025 would be drawing three
years nobody has read. **Consecutive years join with a solid segment; a jump joins with a
dashed one**, and the caption says why.

**Three funds, not nine.** The town has at least nine stabilization funds -- the general
one plus Reserve Capacity, Inflow/Infiltration, Health Insurance, Opioid Settlement, Town
Building, Vehicle/Equipment and Zoning Incentive. Three have a series long enough to plot.
A chart headed "the stabilization funds" would be claiming a completeness this archive
does not have, so every title says which three.

**ENDING CASH, not market value, on every chart.** It is the column the cash identity
proves, it exists on every proven row, and FY2019's table prints no market value at all.
Mixing the two would put a different quantity at different points of the same line.

WHY THESE THREE FORMS

  1. All three funds, one axis    The magnitude question: what does the town hold, and
                                  how do the funds compare in size. A single linear axis,
                                  because two y-scales on one chart is the one chart
                                  mistake that is never worth it.

  2. Each fund, its own scale     The shape question. Chart 1 cannot answer it: against a
                                  $2.6M axis the Zoning fund is a flat line, and that
                                  flatness is a real finding that deserves its own panel
                                  rather than being squashed into the floor of somebody
                                  else's. Small multiples on a SHARED time axis, so the
                                  eye can still line the years up.

  3. How fast each one moved      The comparison TJ asked for, made on one scale.
                                  Percent per year between the first and last proven
                                  year, with that span printed on every bar, because
                                  0.8%/yr over eleven years and 40.8%/yr over seven are
                                  not the same kind of statement.

WHAT CHART 3 DOES NOT SAY. A rate of change in a balance is not a rate of RETURN. These
funds grow by Town Meeting voting money into them and by interest, and this data cannot
separate the two -- rule 7. The town-meeting articles in the analysis show transfers voted
in during these years, which establishes that deposits happened; it does not establish
what share of any rise they are. The chart is labelled as the balance's movement and the
caption says what it cannot distinguish.

COLOUR, VALIDATED RATHER THAN CHOSEN

  #184f95 blue / #e08214 amber / #2a8c6a green, on the #fcfcfb surface.
  Lightness band PASS, chroma floor PASS, worst adjacent CVD dE 9.9 (protan) against a
  target of 8, worst adjacent normal-vision dE 24.0. The amber sits at 2.77:1 against the
  surface, which is a WARN and not dismissable: it obligates visible labels, so every
  series is directly labelled on every chart and the analysis prints the full table
  underneath. Run through the validator; not picked by eye.

THESE RENDER TO PRINT, so there is no hover layer and every series is directly labelled.
"""
import argparse
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN = os.path.join(ROOT, 'sources', 'data', 'stabilization-balances.csv')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'charts')

# Validated. See the module docstring; do not substitute by eye.
SERIES_COLOUR = {
    'Stabilization': '#184f95',
    'Vehicle/Equipment Stabilization': '#e08214',
    'Zoning Incentive Stabilization': '#2a8c6a',
}
# THE LABEL ON THE CHART, NOT THE NAME IN THE DOCUMENT. Every one of these is a
# stabilization fund and the chart title says so, so repeating the word three times down
# the right-hand edge spends the width that made the labels overflow in the first place.
# The name the town actually prints -- `ZONING INCENTIVE STABILIZATION (TD BANKNORTH)` --
# is in the table under the chart, where a reader who wants to look it up needs it.
SHORT = {
    'Stabilization': 'Stabilization (general)',
    'Vehicle/Equipment Stabilization': 'Vehicle/Equipment',
    'Zoning Incentive Stabilization': 'Zoning Incentive',
}

INK = '#0b0b0b'
SECOND = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
AXIS = '#c3c2b7'
SURFACE = '#fcfcfb'
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

# A series needs at least this many proven years before it is worth a line. Two points
# are a pair of readings, not a shape, and drawing a trend through them invites exactly
# the reading the gaps are meant to prevent.
MIN_POINTS = 3


def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def usdk(v):
    a = abs(v)
    s = '-' if v < 0 else ''
    if a >= 1e6:
        return f'{s}${a / 1e6:.2f}M'
    return f'{s}${a / 1000:,.0f}k'


def usd(v):
    return ('-$' if v < 0 else '$') + f'{abs(v):,.2f}'


def fund_key(name):
    """The fund, without the bank that happens to hold it.

    8129 is printed `(TD BANKNORTH)` in most years, `(TD BI` where the scan clipped it and
    `(TL 8129` where the account number ran into it. The bank is not part of the fund's
    identity and it moves; cutting at the bracket gives the thing a series is OF.
    """
    n = ' '.join(name.split()).split('(')[0]
    return ' '.join(w for w in n.split() if not w.isdigit()).strip().title()


# THE LEDGER'S OPENING BALANCE IS THE PREVIOUS YEAR'S CLOSING BALANCE, and that is a
# reading of these funds we already hold. Account 8124's photograph-read series stops at
# FY2021 -- no later page has yielded a general-fund row whose arithmetic closes -- while
# the page's own headline says $3,147,179 is held, from the general ledger. A chart whose
# line stops four years before the figure printed above it is the page contradicting
# itself, and TJ read it straight off the picture: "we dont have data for the
# stabilization fund beyond FY21?"
#
# We do. MUNIS's beginning balance at 2025-07-01 IS the FY2025 year-end balance, printed
# by the accounting system and tied to its own subtotal -- better evidence than the
# photographs, not worse. So it joins the series as the most recent point.
#
# KEYED ON THE ACCOUNT NUMBER, NEVER THE NAME. The ledger calls 8129 `playground fund`
# and the annual report calls it `ZONING INCENTIVE STABILIZATION (TD BANKNORTH)`; the
# account number is the only thing both documents agree on. Only funds that already have
# a series get a point, so this adds evidence to existing lines and never invents one.
LEDGER_CSV = os.path.join(ROOT, 'sources', 'data', 'trust-agency-balances.csv')
# The annual report's own per-account listing -- the table this reader spent weeks not
# noticing. It carries a balance for EVERY fund in the years that print it, so it fills
# years the other-banks tables never reached.
LISTING_CSV = os.path.join(ROOT, 'sources', 'data', 'trust-fund-balances.csv')
# The Treasurer's Cash page, which every annual report prints and which carries the
# general Stabilization Fund. A DIFFERENT GRAIN from the other three -- cash held by a
# custodian rather than a fund balance -- so it is used only where nothing else covers the
# fund-year, and the chart says so.
CASH_CSV = os.path.join(ROOT, 'sources', 'data', 'treasurers-cash.csv')
FLOWS_CSV = os.path.join(ROOT, 'sources', 'data', 'stabilization-flows.csv')

# A DIVERGING PAIR, for a signed quantity where the direction is the whole point. Money in
# above the line, money out below. Validated: adjacent CVD dE 21.6 protan, normal-vision
# 32.3, both above 3:1 on the surface.
IN_COLOUR, OUT_COLOUR = '#2a78d6', '#e34948'
CASH_FOR = (
    (re.compile(r'bartholomew\s+stabilization\s+fund', re.I), 'Stabilization'),
    (re.compile(r'vehicle/equipment\s+stabilization', re.I),
     'Vehicle/Equipment Stabilization'),
    (re.compile(r'zoning\s+(incentive\s+)?stabilization', re.I),
     'Zoning Incentive Stabilization'),
)
LEDGER_FOR = {
    '8124': 'Stabilization',
    '8136': 'Vehicle/Equipment Stabilization',
    '8129': 'Zoning Incentive Stabilization',
}


def creation_years():
    """{fund: fiscal year} for every fund whose CREATING VOTE this archive holds.

    TJ: "can you put a different symbol if we KNOW (can confirm) the creation of the
    funds? ... on teh FY that happened."

    It marks WHEN, never HOW MUCH. The creating article prints an amount, and that amount
    is money voted IN -- not the fund's opening balance, which is only the same number if
    nothing else touched it that year. Rule 7: plotting a deposit as a balance would be
    using a proxy as the thing. So the mark sits on the time axis at the fiscal year of
    the vote, and the value axis is left alone.

    Classification is imported rather than copied, because the fund-word list is the same
    judgement this page makes everywhere else and two copies of it would drift.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from build_stabilization import FUND_WORDS, creations
    except Exception:
        return {}
    out = {}
    for c in creations():
        label = next((lbl for word, lbl in FUND_WORDS
                      if word in (c.get('subject') or '').lower()), None)
        if label:
            out[label] = int(c['fy'])
    return out


def ledger_points():
    """{fund: (fy, ending_cash)} from the general ledger's opening balances."""
    out = {}
    if not os.path.exists(LEDGER_CSV):
        return out
    for r in csv.DictReader(open(LEDGER_CSV, encoding='utf-8')):
        label = LEDGER_FOR.get(r['account'])
        if not label or not r.get('held'):
            continue
        # `fy` on the row is the ledger's own fiscal year; its OPENING balance belongs to
        # the year before.
        out[label] = (int(r['fy']) - 1, float(r['held']))
    return out


def listing_points():
    """{fund: [(fy, balance), ...]} from the annual report's per-account listing."""
    out = {}
    if not os.path.exists(LISTING_CSV):
        return out
    for r in csv.DictReader(open(LISTING_CSV, encoding='utf-8')):
        label = LEDGER_FOR.get(r['account'])
        if not label or not r.get('balance'):
            continue
        out.setdefault(label, []).append((int(r['fy']), float(r['balance'])))
    return out


def cash_points():
    """{fund: [(fy, cash)]} from the Treasurer's Cash page."""
    out = {}
    if not os.path.exists(CASH_CSV):
        return out
    for r in csv.DictReader(open(CASH_CSV, encoding='utf-8')):
        for pat, label in CASH_FOR:
            if pat.search(r['held_as'] or ''):
                out.setdefault(label, []).append((int(r['fy']), float(r['amount'])))
                break
    return out


def series():
    """{fund: [(fy, ending_cash), ...]}, read from the payload the page is rendered from.

    ONE SOURCE, BECAUSE THIS FILE WAS THE THIRD COPY OF THE SAME JOIN. It re-implemented
    what build_stabilization.py's render() and payload() each did separately -- the
    proven rows, then the annual report's listing, then the ledger, then the Treasurer's
    Cash page -- and the three drifted, which is the only thing three copies of a join
    ever do. The chart carried the general fund to FY2025 while the payload stopped at
    FY2021; then the payload was fixed and the CHART was the stale one, still dashing
    across FY2021 after the gap had been closed.

    So the payload is the source and this draws it. A caption computed from a different
    set of points than the picture above it is the page arguing with itself, and a chart
    drawn from a different set again is that argument with a third voice in it.

    It means build_stabilization.py must run first. That is the right dependency: the
    model decides what is established, and the drawing follows.
    """
    import json
    p = os.path.join(ROOT, 'fy28', 'public', 'data', 'stabilization-funds.json')
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding='utf-8'))
    out = {}
    for s in d.get('series', []):
        pts = sorted({(int(x['fy']), float(x['ending_cash'])) for x in s['points']})
        if len(pts) >= MIN_POINTS:
            out[s['fund']] = pts
    return out


def fylabel(fy):
    """`FY14`, not `14`.

    TJ: "make sure the xaxis has FY in the years (i assume they ARE years)." They are
    fiscal years, and that he had to ask is the whole argument -- a bare `14` beside
    dollar figures could be a count, an age or a page number, and this project's own rule
    is that a unitless number in a chart is the one most likely to be quoted wrongly.
    """
    return 'FY%s' % str(fy)[2:]


def colour(fund):
    return SERIES_COLOUR.get(fund, SECOND)


def short(fund):
    return SHORT.get(fund, fund)


# BREATHING ROOM ON ALL FOUR SIDES. Every coordinate in this file is measured from 0,
# which put the title hard against the left edge of the image and ran the right-hand
# series labels into the other one -- TJ: "Titles go to the edges."
#
# Adding it to each geometry would mean touching every x in three charts and getting one
# of them wrong. Instead the whole drawing is translated inside a viewBox grown by twice
# the pad, so the internal coordinates are untouched and the padding cannot drift between
# charts: there is one number and all three read it.
PAD = 18


def svg(w, h, body, title, subtitle):
    W, H = w + PAD * 2, h + PAD * 2
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}"
 height="{H}" role="img" aria-label="{esc(title)}. {esc(subtitle)}"
 font-family='{FONT}'>
<rect width="{W}" height="{H}" fill="{SURFACE}"/>
<g transform="translate({PAD},{PAD})">
<text x="0" y="15" font-size="13" font-weight="700" fill="{INK}">{esc(title)}</text>
<text x="0" y="31" font-size="10.5" fill="{SECOND}">{esc(subtitle)}</text>
{body}
</g>
</svg>
'''


def path_segments(pts, X, Y):
    """Solid where the years are consecutive, dashed where the run skips one.

    THE WHOLE POINT OF THIS FUNCTION. A line drawn straight from FY2022 to FY2025 asserts
    a path through three years nobody has read. The dash is the only thing on the chart
    that says the difference between a year we proved and a year we did not, and without
    it the chart would be making a claim the data does not support.
    """
    out = []
    for (y0, v0), (y1, v1) in zip(pts, pts[1:]):
        dash = '' if y1 - y0 == 1 else ' stroke-dasharray="3 3"'
        out.append(f'<line x1="{X(y0):.1f}" y1="{Y(v0):.1f}" x2="{X(y1):.1f}" '
                   f'y2="{Y(v1):.1f}" stroke-width="2" stroke-linecap="round"'
                   f'{dash} stroke="%s"/>')
    return out


def nice_top(v):
    """A round number at or above the largest value, for an axis a reader can read."""
    for step in (50_000, 100_000, 250_000, 500_000, 1_000_000):
        if v <= step * 6:
            import math
            return math.ceil(v / step) * step
    import math
    return math.ceil(v / 1_000_000) * 1_000_000


# ------------------------------------------------------------ 1. all three, one axis

def chart_all(data):
    # PADDING, MEASURED RATHER THAN EYEBALLED. The first version ended 3px below the
    # last caption on this chart and 23px below it on the next one, which is what reads
    # as "the padding is off" even when no single number looks wrong. T and BOT are now
    # the same on all three: 22px of air under the subtitle, 16px under the last text.
    W, H = 640, 316
    L, R, T, B = 56, 152, 56, 46
    years = sorted({y for v in data.values() for y, _ in v})
    y0, y1 = years[0], years[-1]
    top = nice_top(max(v for s in data.values() for _, v in s))

    def X(fy):
        return L + (fy - y0) / max(y1 - y0, 1) * (W - L - R)

    def Y(v):
        return H - B - v / top * (H - T - B)

    b = []
    # Grid and the money axis. Recessive: the data is the thing.
    for i in range(5):
        v = top * i / 4
        b.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W - R}" y2="{Y(v):.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="{L - 6}" y="{Y(v) + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="end" fill="{MUTED}">{usdk(v)}</text>')
    # The year axis, labelled only where a reading exists, so the ticks are the evidence.
    b.append(f'<line x1="{L}" y1="{H - B}" x2="{W - R}" y2="{H - B}" '
             f'stroke="{AXIS}" stroke-width="1"/>')
    for fy in years:
        b.append(f'<text x="{X(fy):.1f}" y="{H - B + 14}" font-size="9" '
                 f'text-anchor="middle" fill="{MUTED}">{fylabel(fy)}</text>')
    b.append(f'<text x="{L}" y="{H - B + 27}" font-size="9" fill="{MUTED}">'
             f'fiscal year — a tick is a year that PROVED, not every year</text>')

    # Largest last, so the biggest fund draws over the grid rather than under a neighbour.
    for fund, pts in sorted(data.items(), key=lambda kv: kv[1][-1][1]):
        c = colour(fund)
        for seg in path_segments(pts, X, Y):
            b.append(seg % c)
        for fy, v in pts:
            # A 2px surface ring, so a marker crossing another series stays legible.
            b.append(f'<circle cx="{X(fy):.1f}" cy="{Y(v):.1f}" r="4" fill="{c}" '
                     f'stroke="{SURFACE}" stroke-width="2"/>')
        fy, v = pts[-1]
        b.append(f'<text x="{X(fy) + 10:.1f}" y="{Y(v) - 1:.1f}" font-size="10.5" '
                 f'font-weight="600" fill="{c}">{esc(short(fund))}</text>')
        b.append(f'<text x="{X(fy) + 10:.1f}" y="{Y(v) + 11:.1f}" font-size="9.5" '
                 f'fill="{MUTED}">FY{pts[-1][0]} {usdk(v)}</text>')
    return svg(W, H, ''.join(b),
               'Three stabilization funds, on one scale',
               'Ending cash: each annual report reading that proved itself, plus the '
               'general ledger at FY2025. Dashes span years not yet read')


# ------------------------------------------------- 2. each fund on its own scale

def chart_each(data):
    ROWH, GAP = 96, 22
    W = 640
    L, R, T = 56, 152, 56
    # 16px under the final row's year ticks, the same as every other chart here.
    H = T + len(data) * (ROWH + GAP) - GAP + 16
    years = sorted({y for v in data.values() for y, _ in v})
    y0, y1 = years[0], years[-1]

    def X(fy):
        return L + (fy - y0) / max(y1 - y0, 1) * (W - L - R)

    b = []
    # Biggest first: the reader meets the fund they have heard of before the two they
    # have not.
    order = sorted(data.items(), key=lambda kv: -kv[1][-1][1])
    for i, (fund, pts) in enumerate(order):
        top = T + i * (ROWH + GAP)
        base, head = top + ROWH - 22, top + 16
        lo = min(v for _, v in pts)
        hi = max(v for _, v in pts)
        # EACH PANEL ZEROED ON ITS OWN FLOOR, NOT ON ZERO -- and that is a real trade.
        # Zeroing every panel would flatten the Zoning fund back into the line chart
        # above and lose the shape this chart exists to show. Zeroing on the floor
        # exaggerates small movement, so the panel prints its own range in the corner and
        # the first and last figures sit on the line: a reader is told the scale rather
        # than left to assume it starts at nothing.
        span = max(hi - lo, 1.0)

        def Y(v, base=base, head=head, lo=lo, span=span):
            return base - (v - lo) / span * (base - head)

        c = colour(fund)
        b.append(f'<line x1="{L}" y1="{base + 6}" x2="{W - R}" y2="{base + 6}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="0" y="{top + 10}" font-size="11" font-weight="600" '
                 f'fill="{c}">{esc(short(fund))}</text>')
        for seg in path_segments(pts, X, Y):
            b.append(seg % c)
        for fy, v in pts:
            b.append(f'<circle cx="{X(fy):.1f}" cy="{Y(v):.1f}" r="3.5" fill="{c}" '
                     f'stroke="{SURFACE}" stroke-width="2"/>')
        # The two ends carry their figure; the middle points do not, because a number on
        # every point is noise rather than information.
        f0, v0 = pts[0]
        f1, v1 = pts[-1]
        # ABOVE THE POINT WHEN THE POINT IS ON THE FLOOR. Each panel is zeroed on its
        # own minimum, so the opening reading is usually the lowest one and sits on the
        # baseline -- where a label placed beneath it lands on top of the year ticks.
        # It did, on all three panels.
        above = v0 <= lo + span * 0.15
        dy = -8 if above else 16
        b.append(f'<text x="{X(f0):.1f}" y="{Y(v0) + dy:.1f}" font-size="9.5" '
                 f'text-anchor="middle" fill="{SECOND}">{usdk(v0)}</text>')
        b.append(f'<text x="{X(f1) + 10:.1f}" y="{Y(v1) + 3.5:.1f}" font-size="10.5" '
                 f'font-weight="600" fill="{INK}">{usdk(v1)}</text>')
        b.append(f'<text x="{W - R + 10}" y="{top + 10}" font-size="9" fill="{MUTED}">'
                 f'FY{f0}–FY{f1}</text>')
        b.append(f'<text x="{W - R + 10}" y="{base + 9}" font-size="9" fill="{MUTED}">'
                 f'panel spans {usdk(lo)}–{usdk(hi)}</text>')
        for fy in years:
            b.append(f'<text x="{X(fy):.1f}" y="{base + 19}" font-size="8.5" '
                     f'text-anchor="middle" fill="{MUTED}">{fylabel(fy)}</text>')
    return svg(W, H, ''.join(b),
               'The same three funds, each on its own scale',
               'Each panel stretched to its OWN range, so the shapes are comparable and '
               'the heights are not. Dashes span years not yet read')


# ------------------------------------------------------------ 3. how fast each moved

def growth(pts):
    """Per cent a year between the first and last PROVEN year. Both ends are real."""
    (f0, v0), (f1, v1) = pts[0], pts[-1]
    n = f1 - f0
    if n <= 0 or v0 <= 0:
        return None
    return ((v1 / v0) ** (1.0 / n) - 1) * 100


def chart_growth(data):
    rows = []
    for fund, pts in data.items():
        g = growth(pts)
        if g is not None:
            rows.append((fund, pts, g))
    rows.sort(key=lambda r: -r[2])
    W = 640
    L, R, T, ROWH = 0, 130, 56, 52  # T matches the other two: 22px under the subtitle
    # 56, not 34: the footnote is two lines, and the second needs a descender's worth of
    # room under its baseline or the viewBox clips the tails off 'g' and 'p'.
    H = T + len(rows) * ROWH + 56
    BARL = 200
    top = max(r[2] for r in rows)
    b = []
    for i, (fund, pts, g) in enumerate(rows):
        y = T + i * ROWH
        c = colour(fund)
        w = max(g / top * (W - BARL - R), 2)
        b.append(f'<text x="0" y="{y + 10}" font-size="11" font-weight="600" '
                 f'fill="{c}">{esc(short(fund))}</text>')
        b.append(f'<text x="0" y="{y + 24}" font-size="9" fill="{MUTED}">'
                 f'FY{pts[0][0]}–FY{pts[-1][0]}, {pts[-1][0] - pts[0][0]} years, '
                 f'{len(pts)} proven readings</text>')
        b.append(f'<rect x="{BARL}" y="{y}" width="{w:.1f}" height="20" fill="{c}" '
                 f'rx="2"/>')
        b.append(f'<text x="{BARL + w + 8:.1f}" y="{y + 14.5}" font-size="12" '
                 f'font-weight="700" fill="{INK}">{g:.1f}% a year</text>')
        b.append(f'<text x="{BARL}" y="{y + 34}" font-size="9.5" fill="{SECOND}">'
                 f'{usdk(pts[0][1])} → {usdk(pts[-1][1])}</text>')
    b.append(f'<text x="0" y="{H - 22}" font-size="9.5" fill="{MUTED}">'
             f'The balance’s movement, not a rate of return: these funds rise when '
             f'Town Meeting votes money in AND when they earn interest,</text>')
    b.append(f'<text x="0" y="{H - 10}" font-size="9.5" fill="{MUTED}">'
             f'and nothing in this data separates the two.</text>')
    return svg(W, H, ''.join(b),
               'How fast each fund moved, per year',
               'Between each fund’s first and last reading — the span differs per '
               'fund and is printed on each')



def chart_flows(_data):
    """Deposits above the line, withdrawals below, by year.

    TJ: "is there a chart type that can show both the increase and draw on the funds? ...
    i want to see how often they are drawn from and how much at a time."

    A DIVERGING BAR is the form for that: one axis, zero in the middle, and the thing a
    reader is actually asking -- how often, and how big -- is the shape of the bars below
    the line rather than any number in a table.

    WHAT IS DELIBERATELY NOT ON IT: the BALANCE. It is the same unit and about thirty
    times the size, so putting it here needs a second y-scale, and a dual axis is the one
    chart mistake that is never worth making. Levels are the other chart; this is flows.
    """
    import build_stabilization as B
    fl = B.flows()
    ins = collections.defaultdict(float)
    for d in fl['deposits']:
        ins[d['fy']] += d['amount']
    outs = collections.defaultdict(float)
    nout = collections.Counter()
    if os.path.exists(FLOWS_CSV):
        for r in csv.DictReader(open(FLOWS_CSV, encoding='utf-8')):
            if r['confidence'] != 'clear':
                continue
            outs[int(r['fy'])] += float(r['amount'])
            nout[int(r['fy'])] += 1
    years = sorted(set(ins) | set(outs))
    if not years:
        return None
    W, H = 640, 300
    L, R, T, B_ = 62, 18, 58, 46
    # ONE SCALE FOR BOTH HALVES, and it is tight to the data rather than rounded up to a
    # comfortable number. Scaling the halves independently would make a $106k withdrawal
    # look like a $770k deposit, which is the opposite of what this chart is for: that
    # the withdrawals are RARE and SMALL against the deposits is the finding, not an
    # inconvenience of the drawing.
    import math
    raw = max(max(ins.values(), default=0), max(outs.values(), default=0))
    step = 10 ** max(0, len(str(int(raw))) - 2)
    top = math.ceil(raw / step) * step
    mid = T + (H - T - B_) * (top / (top * 2))

    def X(fy):
        return L + (fy - years[0]) / max(years[-1] - years[0], 1) * (W - L - R)

    def Y(v):
        return mid - (v / top) * (H - T - B_) / 2

    b = []
    for i in range(-2, 3):
        v = top * i / 2
        b.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W - R}" y2="{Y(v):.1f}" '
                 f'stroke="{GRID if i else AXIS}" stroke-width="1"/>')
        b.append(f'<text x="{L - 6}" y="{Y(v) + 3.5:.1f}" font-size="9" text-anchor="end" '
                 f'fill="{MUTED}">{usdk(abs(v)) if i else "0"}</text>')
    bw = max(6, (W - L - R) / (len(years) * 1.7))
    for fy in years:
        x = X(fy) - bw / 2
        if ins.get(fy):
            h = abs(Y(ins[fy]) - mid)
            b.append(f'<rect x="{x:.1f}" y="{Y(ins[fy]):.1f}" width="{bw:.1f}" '
                     f'height="{h:.1f}" fill="{IN_COLOUR}" rx="2"/>')
        if outs.get(fy):
            h = abs(Y(-outs[fy]) - mid)
            b.append(f'<rect x="{x:.1f}" y="{mid:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                     f'fill="{OUT_COLOUR}" rx="2"/>')
            # DIRECT-LABELLED, because the withdrawals are the rare event and the reason
            # for the chart; a reader should not have to measure one against an axis.
            b.append(f'<text x="{X(fy):.1f}" y="{Y(-outs[fy]) + 11:.1f}" font-size="8.5" '
                     f'text-anchor="middle" fill="{OUT_COLOUR}">{usdk(outs[fy])}</text>')
        b.append(f'<text x="{X(fy):.1f}" y="{H - B_ + 22}" font-size="8.5" '
                 f'text-anchor="middle" fill="{MUTED}">{fylabel(fy)}</text>')
    b.append(f'<text x="{L}" y="{T - 8}" font-size="10" font-weight="600" '
             f'fill="{IN_COLOUR}">voted IN</text>')
    b.append(f'<text x="{L}" y="{H - B_ + 38}" font-size="10" font-weight="600" '
             f'fill="{OUT_COLOUR}">taken OUT</text>')
    drawn = sum(nout.values())
    b.append(f'<text x="{W - R}" y="{H - B_ + 38}" font-size="9" text-anchor="end" '
             f'fill="{MUTED}">{drawn} withdrawals in {len(years)} years</text>')
    return svg(W, H, ''.join(b), 'Money in and money out, by year',
               'Deposits above the line, withdrawals below. Balances are the other chart: '
               'they are thirty times the size and would need a second axis')


CHARTS = [
    ('stabilization-all.svg', chart_all),
    ('stabilization-each.svg', chart_each),
    ('stabilization-growth.svg', chart_growth),
    ('stabilization-flows.svg', chart_flows),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = series()
    if not data:
        print('no fund has %d proven years yet — nothing to draw' % MIN_POINTS)
        return 0
    os.makedirs(OUT, exist_ok=True)
    stale = []
    for name, fn in CHARTS:
        got = fn(data)
        if got is None:
            continue
        p = os.path.join(OUT, name)
        if a.check:
            old = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if old != got:
                stale.append(name)
            continue
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(got)
        print('wrote %s' % os.path.relpath(p, ROOT))
    if a.check:
        if stale:
            print('STALE %s — run: python3 scripts/build_stabilization_charts.py'
                  % ', '.join(stale))
            return 1
        print('ok — %d charts reproduce from %d funds'
              % (len(CHARTS), len(data)))
    else:
        for fund, pts in sorted(data.items()):
            print('  %-34s %d readings, FY%d–FY%d'
                  % (fund, len(pts), pts[0][0], pts[-1][0]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
