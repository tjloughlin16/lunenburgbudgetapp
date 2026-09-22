#!/usr/bin/env python3
"""Two charts for the town budget: the fifteen-year line, and who pushes it.

    python3 scripts/build_town_budgets_charts.py
    python3 scripts/build_town_budgets_charts.py --check

Writes `sources/analyses/charts/town-budgets-*.svg`.

TWO CHARTS, BECAUSE THE PAGE ANSWERS TWO QUESTIONS.

  1. THE TOTAL, FY2012 TO FY2026.  What the town votes, every year, one column each. The
                                   shape is a steady climb and then a step, and the step
                                   is the year with no department detail behind it -- so
                                   that column is drawn in the warning colour and labelled,
                                   because a reader who takes it for an ordinary year has
                                   been misled about the one year nobody can break down.
  2. PULL, BY DEPARTMENT.          Share of the budget times excess growth over the levy
                                   cap, diverging about zero. This is rule 4 drawn: it is
                                   the only chart that puts insurance and retirement above
                                   the schools, which is the finding, and a chart of SIZE
                                   would put the schools on top and say nothing.

EVERYTHING IS READ OUT OF THE PAYLOAD, never recomputed. A chart that derives its own
figures is a second model and the first thing two models do is disagree.

COLOUR IS THE SAME THREE STEPS the stabilization charts use -- #184f95 blue, #e08214
amber, #2a8c6a green on the #fcfcfb surface -- so reports about one town do not look like
reports from different projects. The amber's 2.77:1 against the surface is a contrast WARN
rather than a pass, which obligates visible labels: every bar worth reading is directly
labelled and both charts are printed above the table they summarise.

THESE RENDER TO PRINT, so there is no hover layer and nothing depends on colour alone --
the diverging chart puts its sign in the label as well as the side.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from build_stabilization_charts import (  # noqa: E402
    AXIS, FONT, GRID, INK, MUTED, PAD, SECOND, SURFACE, esc, nice_top, usdk,
)

import pictograms as P                                            # noqa: E402

PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'town-budgets.json')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'charts')

VOTED = '#184f95'      # an ordinary year, with a table behind it
NODETAIL = '#e08214'   # a year that is a total and nothing else
DOWN = '#2a8c6a'       # a department pulling the total DOWN


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


def chart_total(d):
    """One column a fiscal year, FY2012 to FY2026."""
    rows = d['totals']
    W, H = 720, 300
    top, left, bottom = 56, 52, 46
    plot_h = H - top - bottom
    hi = nice_top(max(r['voted'] for r in rows))
    step = (W - left) / len(rows)
    bw = min(34.0, step * 0.62)

    def Y(v):
        return top + plot_h - (v / hi) * plot_h

    b = []
    for i in range(5):
        v = hi * i / 4.0
        y = Y(v)
        b.append(f'<line x1="{left}" y1="{y:.1f}" x2="{W}" y2="{y:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="{left - 6}" y="{y + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="end" fill="{MUTED}">{usdk(v)}</text>')
    for i, r in enumerate(rows):
        cx = left + step * (i + 0.5)
        y = Y(r['voted'])
        fill = NODETAIL if 'prose' in (r.get('status') or '') else VOTED
        b.append(f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                 f'height="{top + plot_h - y:.1f}" fill="{fill}" rx="2"/>')
        if i == 0 or i == len(rows) - 1 or r['fy'] % 5 == 0:
            b.append(f'<text x="{cx:.1f}" y="{y - 5:.1f}" font-size="9" '
                     f'text-anchor="middle" fill="{INK}">{usdk(r["voted"])}</text>')
        if i % 2 == 0 or i == len(rows) - 1:
            b.append(f'<text x="{cx:.1f}" y="{top + plot_h + 14:.1f}" font-size="9" '
                     f'text-anchor="middle" fill="{MUTED}">{str(r["fy"])[2:]}</text>')
    last = rows[-1]
    b.append(f'<text x="{W}" y="{top + plot_h + 32:.1f}" font-size="9.5" '
             f'text-anchor="end" fill="{NODETAIL}">'
             f'FY{last["fy"]} in amber: a total with no department table printed</text>')
    b.append(f'<line x1="{left}" y1="{top + plot_h:.1f}" x2="{W}" y2="{top + plot_h:.1f}" '
             f'stroke="{AXIS}" stroke-width="1"/>')
    return svg(W, H, ''.join(b), 'What Town Meeting voted, FY%d to FY%d'
               % (rows[0]['fy'], rows[-1]['fy']),
               'The omnibus budget total, as printed in each annual report. Fiscal years '
               'on the axis.')


def chart_pull(d):
    """Diverging bars in DOLLARS A YEAR, because `+1.00` is not a unit.

    TJ: *"'which departments move the total' i dont know what units these are."* The first
    version drew `pull` -- share times excess rate -- and called it points of total growth.
    That was worse than unlabelled: the twelve pulls sum to +1.30 while the budget exceeds
    the cap by +0.41, because the weight is the end-year share and the rate is compound, so
    it never decomposed anything. An index presented as a share is rule 13 in a chart.

    What is drawn now is the department\u2019s own money times how far its growth exceeds
    the cap: dollars a year, a quantity a reader can check against the budget line beside
    it, ranking identically and summing to something real.
    """
    rows = [r for r in d['departments'] if r.get('excess') is not None]
    W, H = 720, 330
    top, label_w, bottom = 58, 168, 34
    plot_h = H - top - bottom
    span = max(abs(r['excess']) for r in rows) * 1.15 or 1.0
    zero = label_w + (W - label_w) * (span / (2 * span))
    half = (W - label_w) / 2.0
    rh = plot_h / len(rows)
    bh = min(16.0, rh * 0.68)

    b = [f'<line x1="{zero:.1f}" y1="{top - 6:.1f}" x2="{zero:.1f}" '
         f'y2="{top + plot_h:.1f}" stroke="{AXIS}" stroke-width="1"/>']
    for i, r in enumerate(rows):
        cy = top + rh * (i + 0.5)
        w = abs(r['excess']) / span * half
        up = r['excess'] >= 0
        x = zero if up else zero - w
        b.append(f'<rect x="{x:.1f}" y="{cy - bh / 2:.1f}" width="{max(w, 0.8):.1f}" '
                 f'height="{bh:.1f}" fill="{VOTED if up else DOWN}" rx="2"/>')
        b.append(f'<text x="{label_w - 8}" y="{cy + 3.5:.1f}" font-size="10" '
                 f'text-anchor="end" fill="{INK}">{esc(r["name"])}</text>')
        sign = '+' if up else '\u2212'
        tx = (x + w + 6) if up else (x - 6)
        b.append(f'<text x="{tx:.1f}" y="{cy + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="{"start" if up else "end"}" fill="{SECOND}">'
                 f'{sign}{usdk(abs(r["excess"]))}</text>')
    b.append(f'<text x="{zero + 8:.1f}" y="{top + plot_h + 20:.1f}" font-size="9.5" '
             f'fill="{MUTED}">spends more than the cap would carry</text>')
    b.append(f'<text x="{zero - 8:.1f}" y="{top + plot_h + 20:.1f}" font-size="9.5" '
             f'text-anchor="end" fill="{MUTED}">spends less</text>')
    net = sum(r['excess'] for r in rows)
    return svg(W, H, ''.join(b),
               'Which departments outgrow the levy cap, in dollars a year',
               'Each department\u2019s own money times how far its growth exceeds the '
               '%.1f%% cap, FY%d to FY%d. The twelve net to %s a year.'
               % (d['levy_cap'], d['detail_years'][0], d['detail_years'][-1], usdk(net)))


# Twelve steps, assigned in a fixed order by SIZE so the same department is the same
# colour on every redraw. Three hues, four lightnesses each -- a categorical ramp of
# twelve fully distinct hues would be unreadable at 2% of a circle, and the slices that
# small are labelled in the table rather than on the chart anyway.
# TWELVE STEPS FOR TWELVE DEPARTMENTS. There were eleven, and `SLICES[i % len(SLICES)]` gave the
# twelfth department the first one's colour -- Central Purchasing wearing the school line's
# navy in a legend ranked by size, which is the one place two identical swatches mislead.
# A CATEGORICAL PALETTE, VALIDATED RATHER THAN CHOSEN. TJ: *"the colors have to be
# distinct enough. the personel page is hard to see the differences."* The old one ran
# four BLUES in a row -- #12325f, #184f95, #3f78bd, #7ea6d8 -- so the four biggest
# departments, which are the four a reader cares most about telling apart, were four
# shades of one hue.
#
# Checked with the dataviz validator rather than by eye (`scripts/validate_palette.js`
# in the bundled skill), against this surface, in this ORDER -- the checks are on
# ADJACENT pairs and these charts are ranked by size, so adjacent means adjacent in rank:
#
#   lightness band       all 12 inside L 0.43-0.77      PASS
#   chroma floor         all 12 >= 0.1                  PASS
#   CVD separation       worst adjacent dE 8.4 protan   PASS
#   normal-vision floor  worst adjacent dE 19.6         PASS
#   contrast vs surface  three below 3:1                WARN -- see below
#
# The contrast warning is not dismissable and is not dismissed: it obliges visible labels
# or a table view, and every chart using this palette carries a legend naming each series
# with its value, plus the same figures as a table further down the page.
#
# DARK MODE IS NOT THIS PALETTE FLIPPED. Three of these fall outside the band the
# validator wants against the dark surface, and the honest fix is a second set of steps
# chosen for that surface rather than a reuse of these. These SVGs are fixed-colour files
# served to /docs and to the PDF, so they use the light set; picking the dark steps is
# open work.
SLICES = ['#2b6cb0', '#dc2626', '#ea8c00', '#2f8f4e', '#7c3aed', '#0d9488', '#92400e', '#c026d3', '#38bdf8', '#a3a324', '#e0558a', '#3b5bbf']


def chart_share(d):
    """A pie: how the voted budget divides between the twelve departments.

    TJ asked for this twice -- *"pie charts. which dept is biggest."* -- and the first
    version of the page did not have it, which was a mistake dressed up as good practice.
    The page led with PULL, which is share times excess growth, and pull is the subtle
    finding rather than the obvious question. A resident opens a page about the town budget
    wanting to know who gets the money. Answer that first; the clever ranking keeps.

    A pie is the right form here for a reason that does not always hold: this is a
    part-to-whole split of ONE quantity, the parts are mutually exclusive and exhaust the
    total, and one slice is 57% -- so the shape carries the finding before any label is
    read. What a pie is bad at is comparing the small slices to each other, and five of
    these are under 2%. So every slice is also a row in the table underneath, ranked, with
    its share printed: the chart answers "who is biggest" and the table answers "by how
    much", and neither is asked to do the other's job.
    """
    rows = sorted([r for r in d['departments'] if r.get('last')],
                  key=lambda r: -r['last'])
    total = sum(r['last'] for r in rows)
    W, H = 720, 400
    cx, cy, R = 232.0, 232.0, 142.0
    b, ang = [], -90.0
    import math
    for i, r in enumerate(rows):
        frac = r['last'] / total
        sweep = frac * 360.0
        a0, a1 = math.radians(ang), math.radians(ang + sweep)
        x0, y0 = cx + R * math.cos(a0), cy + R * math.sin(a0)
        x1, y1 = cx + R * math.cos(a1), cy + R * math.sin(a1)
        big = 1 if sweep > 180 else 0
        b.append(f'<path d="M{cx:.1f},{cy:.1f} L{x0:.1f},{y0:.1f} '
                 f'A{R},{R} 0 {big},1 {x1:.1f},{y1:.1f} Z" fill="{SLICES[i % 12]}" '
                 f'stroke="{SURFACE}" stroke-width="2"/>')
        if frac >= 0.04:
            am = math.radians(ang + sweep / 2)
            lx, ly = cx + R * 0.62 * math.cos(am), cy + R * 0.62 * math.sin(am)
            b.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" font-size="11" '
                     f'font-weight="700" text-anchor="middle" fill="#ffffff">'
                     f'{frac * 100:.0f}%</text>')
        ang += sweep
    lx = 430
    for i, r in enumerate(rows):
        ly = 74 + i * 25.0
        b.append(f'<rect x="{lx}" y="{ly - 9:.1f}" width="11" height="11" rx="2" '
                 f'fill="{SLICES[i % 12]}"/>')
        b.append(f'<text x="{lx + 18}" y="{ly:.1f}" font-size="10.5" fill="{INK}">'
                 f'{esc(r["name"])}</text>')
        b.append(f'<text x="{W}" y="{ly:.1f}" font-size="10.5" text-anchor="end" '
                 f'fill="{SECOND}">{r["last"] / total * 100:.1f}%</text>')
    return svg(W, H, ''.join(b),
               'Who gets the money: the voted budget, FY%d' % d['detail_years'][-1],
               'The twelve departments as shares of one %s budget. Slices under 4%% are '
               'labelled in the legend only.' % usdk(total))


def chart_trends(d):
    """Twelve small panels, one per department: where its money went, year by year.

    TJ: *"one major thing missing is: how are each departments budgets GROWING over time.
    I want to see that visualy."* Twelve series on one pair of axes is unreadable at any
    scale -- the school line is 57% of the budget and everything else is a flat smear
    along the bottom. Small multiples is the form for this: each department gets its own
    panel and its own vertical scale, so the SHAPE of its change is legible whatever its
    size, and the rate is printed on the panel so nobody mistakes a steep small line for a
    big movement.

    Three years is a short series, and in this town three years is also more forward
    visibility than most boards use -- so the span is stated on every panel rather than
    implied.
    """
    rows = [r for r in d['departments'] if r.get('series')]
    ys = d['detail_years']
    cols, rowsn = 4, 3
    pw, ph = 168.0, 96.0
    W = int(cols * pw + 24)
    H = int(rowsn * ph + 96)
    b = []
    for i, r in enumerate(rows[:cols * rowsn]):
        cx0 = 8 + (i % cols) * pw
        cy0 = 62 + (i // cols) * ph
        vals = [r['series'].get(str(y), r['series'].get(y)) for y in ys]
        vals = [v for v in vals if v]
        if len(vals) < 2:
            continue
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.35 or max(hi * 0.02, 1)
        lo, hi = lo - pad, hi + pad
        gw, gh = pw - 30, ph - 46

        def X(k, n=len(vals)):
            return cx0 + 6 + gw * k / max(n - 1, 1)

        def Y(v):
            return cy0 + 22 + gh - (v - lo) / (hi - lo) * gh

        # WHAT THE CAP WOULD HAVE ALLOWED, faintly, from the same starting point. TJ:
        # *"I think we need a prop 2.5% line on each chart subtle."* On a panel of DOLLARS
        # a rate has no axis of its own, so the cap is drawn as the line this department
        # would have traced had it grown at 2.5% a year from where it started. Where the
        # real line sits above it, the department outgrew the cap, and by how much is the
        # gap between them.
        cap_vals = [vals[0] * (1 + d['levy_cap'] / 100.0) ** k for k in range(len(vals))]
        cap_pts = ' '.join('%.1f,%.1f' % (X(k), Y(v)) for k, v in enumerate(cap_vals)
                           if lo <= v <= hi)
        if cap_pts.count(',') >= 2:
            # A LITTLE MORE PRESENT. TJ: *"for the prop 2.5 line, ut needs to stand out a
            # TINY bit more. its too faded as that gray."* It is a reference line, so it
            # must not compete with the department's own line -- but at 0.55 opacity in
            # axis grey it read as a printing artefact rather than a deliberate mark. The
            # secondary ink at full weight, a slightly longer dash and a hair more width
            # is visible without pulling the eye off the data.
            b.append(f'<polyline points="{cap_pts}" fill="none" stroke="{SECOND}" '
                     f'stroke-width="1.3" stroke-dasharray="4 3" opacity="0.9"/>')
        up = vals[-1] >= vals[0]
        colour = VOTED if up else DOWN
        b.append(f'<text x="{cx0 + 6}" y="{cy0 + 10:.1f}" font-size="9.5" '
                 f'font-weight="700" fill="{INK}">{esc(r["name"][:26])}</text>')
        b.append(f'<text x="{cx0 + 6}" y="{cy0 + 21:.1f}" font-size="8.5" '
                 f'fill="{SECOND}">{r["rate"]:+.1f}% a year · {usdk(vals[-1])}</text>')
        b.append(f'<line x1="{cx0 + 6}" y1="{cy0 + 22 + gh:.1f}" x2="{X(len(vals) - 1):.1f}" '
                 f'y2="{cy0 + 22 + gh:.1f}" stroke="{GRID}" stroke-width="1"/>')
        pts = ' '.join('%.1f,%.1f' % (X(k), Y(v)) for k, v in enumerate(vals))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                 f'stroke-width="2.2" stroke-linejoin="round"/>')
        for k, v in enumerate(vals):
            b.append(f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="2.8" fill="{colour}"/>')
    return svg(W, H, ''.join(b),
               'Every department, year by year',
               'FY%d to FY%d, each panel on its OWN scale. The faint dashed line is what '
               '%s%% a year \u2014 the levy cap \u2014 would have allowed.'
               % (ys[0], ys[-1], d['levy_cap']))


def chart_rates(d):
    """Each department's growth RATE against Proposition 2 1/2, on one axis.

    TJ: *"I want to see the growth RATE, esp to compare against Prop 2.5 ... its just not
    in the chart."* The small multiples print each rate as text on its panel, which is
    readable and is not comparable -- twelve numbers in twelve boxes ask the reader to do
    the sorting. One axis with the cap drawn on it does the comparison for them, and the
    only thing worth seeing is which side of that line a department falls on.

    The cap is a REFERENCE, not a limit that was breached: Proposition 2 1/2 caps the
    LEVY, and the budget is the levy plus state aid, local receipts and transfers. It is
    drawn because every board in this town already argues against it.
    """
    rows = sorted([r for r in d['departments'] if r.get('rate') is not None],
                  key=lambda r: -r['rate'])
    cap = d['levy_cap']
    W, H = 720, 360
    top, label_w, bottom = 62, 210, 40
    plot_h, plot_w = H - top - bottom, W - label_w - 40
    lo = min(min(r['rate'] for r in rows), 0) * 1.1
    hi = max(r['rate'] for r in rows) * 1.12
    rh = plot_h / len(rows)
    bh = min(16.0, rh * 0.66)

    def X(v):
        return label_w + plot_w * (v - lo) / (hi - lo)

    b = [f'<line x1="{X(0):.1f}" y1="{top - 8:.1f}" x2="{X(0):.1f}" '
         f'y2="{top + plot_h:.1f}" stroke="{AXIS}" stroke-width="1"/>']
    for i, r in enumerate(rows):
        cy = top + rh * (i + 0.5)
        x0, x1 = X(min(0, r['rate'])), X(max(0, r['rate']))
        over = r['rate'] > cap
        b.append(f'<rect x="{x0:.1f}" y="{cy - bh / 2:.1f}" width="{max(x1 - x0, 0.8):.1f}" '
                 f'height="{bh:.1f}" fill="{NODETAIL if over else DOWN}" rx="2"/>')
        b.append(f'<text x="{label_w - 8}" y="{cy + 3.5:.1f}" font-size="10" '
                 f'text-anchor="end" fill="{INK}">{esc(r["name"][:34])}</text>')
        b.append(f'<text x="{x1 + 6:.1f}" y="{cy + 3.5:.1f}" font-size="9.5" '
                 f'fill="{SECOND}">{r["rate"]:+.1f}%</text>')
    xc = X(cap)
    b.append(f'<line x1="{xc:.1f}" y1="{top - 14:.1f}" x2="{xc:.1f}" '
             f'y2="{top + plot_h + 4:.1f}" stroke="{VOTED}" stroke-width="2" '
             f'stroke-dasharray="5 3"/>')
    b.append(f'<text x="{xc + 5:.1f}" y="{top - 18:.1f}" font-size="10" '
             f'font-weight="700" fill="{VOTED}">Proposition 2\u00bd \u2014 {cap}%</text>')
    return svg(W, H, ''.join(b),
               'How fast each department grows, against the levy cap',
               'Compound annual change, FY%d to FY%d. The cap limits the LEVY, not the '
               'budget \u2014 it is drawn because every board here argues against it.'
               % (d['detail_years'][0], d['detail_years'][-1]))


def chart_all(d):
    """All twelve on ONE axis, which is the point: the schools dwarf everything.

    TJ: *"and a graph that puts them all together in one place. the schools will dwarf the
    others."* They do, and that is worth one chart. The small multiples deliberately give
    every department its own scale so the SHAPE of a $80,000 line is legible beside a $25M
    one -- which is the right way to read growth and the wrong way to read size. Put them
    on one axis and the honest relation returns: one line at $25M, one at $4.6M, and ten
    crowded along the floor.

    Both are true and neither is sufficient, so the page carries both and says which
    question each answers.
    """
    rows = sorted([r for r in d['departments'] if r.get('series')],
                  key=lambda r: -(r['last'] or 0))
    ys = d['detail_years']
    W, H = 720, 380
    top, left, bottom, right = 58, 56, 40, 238
    plot_h, plot_w = H - top - bottom, W - left - right
    hi = nice_top(max(r['last'] for r in rows))

    def cx(i):
        return left + plot_w * i / max(len(ys) - 1, 1)

    def Y(v):
        return top + plot_h - (v / hi) * plot_h

    b = []
    for k in range(6):
        v = hi * k / 5.0
        y = Y(v)
        b.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="{left - 6}" y="{y + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="end" fill="{MUTED}">{usdk(v)}</text>')
    for i, y in enumerate(ys):
        b.append(f'<text x="{cx(i):.1f}" y="{top + plot_h + 15:.1f}" font-size="9.5" '
                 f'text-anchor="middle" fill="{MUTED}">FY{y}</text>')
    # A LEGEND, NOT LINE-END LABELS. Ten of the twelve lines finish within a few pixels of
    # each other along the floor, so labelling each at its own line collided them into an
    # unreadable stack that ran off the bottom of the panel. Ranked down the side, they are
    # legible and they also say the thing the chart is for: the order of size.
    lx = left + plot_w + 12
    for i, r in enumerate(rows):
        vals = [r['series'].get(str(y), r['series'].get(y)) for y in ys]
        if not all(vals):
            continue
        colour = SLICES[i % len(SLICES)]
        pts = ' '.join('%.1f,%.1f' % (cx(k), Y(v)) for k, v in enumerate(vals))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                 f'stroke-width="2"/>')
        ly = top + 6 + i * 24.0
        b.append(f'<rect x="{lx}" y="{ly - 8:.1f}" width="10" height="10" rx="2" '
                 f'fill="{colour}"/>')
        b.append(f'<text x="{lx + 15}" y="{ly:.1f}" font-size="9.5" fill="{INK}">'
                 f'{esc(r["name"][:22])}</text>')
        b.append(f'<text x="{W}" y="{ly:.1f}" font-size="9.5" text-anchor="end" '
                 f'fill="{SECOND}">{usdk(vals[-1])}</text>')
    b.append(f'<line x1="{left}" y1="{top + plot_h:.1f}" x2="{left + plot_w}" '
             f'y2="{top + plot_h:.1f}" stroke="{AXIS}" stroke-width="1"/>')
    return svg(W, H, ''.join(b),
               'All twelve departments on one axis',
               'The same figures, on one scale. One line is most of the budget and ten '
               'share the floor.')


# WHAT EACH DEPARTMENT LOOKS LIKE. TJ: *"a conceptual image that shows some stereotypical
# image that represents each department (a police car for police, fire truck for fire,
# construction vehicle for DPW, etc) in size proportion to the dollar amounts."*
#
# One glyph per voted GROUP, not per office, because the groups are what the budget
# actually votes. `Protection of persons & property` holds the Police and the Fire
# Department together and is drawn as a police car, which is a compromise the caption
# states rather than hides.
GROUP_GLYPH = {
    'schools': 'school',
    'protection': 'police',
    'unclassified': 'cross',
    'maturing-debt': 'coins',
    'public-works': 'truck',
    'general-government': 'hall',
    'facilities-grounds': 'wrench',
    'library': 'book',
    'solid-waste': 'bin',
    'assistance': 'care',
    'health-sanitation': 'cross',
    'central-purchasing': 'box',
}


def chart_town(d):
    """THE SIGNATURE IMAGE: the voted budget as a town you can look at.

    TJ: *"there are a bunch of school buildings next to police cars, or something like
    that"* -- concept art in the manner of `GrowthCubes` on /commercial-development, not
    a chart with rows.

    ONE ICON IS $100,000, which is the unit that lets every department appear: at a
    million, four of the twelve would be drawn as nothing, and a picture that silently
    omits the smallest departments is making a claim the budget does not. Four hundred
    and forty icons, each department in its own thing and its own colour, scattered on
    one ground. The schools are a quarter of the picture before a number is read.

    Seeded, so it is the same town in every build and in print.
    """
    rows_in = sorted([r for r in d['departments'] if r.get('last')],
                     key=lambda r: -r['last'])
    unit = 100_000
    items, legend = [], []
    for i, r in enumerate(rows_in):
        colour = SLICES[i % len(SLICES)]
        n = max(1, int(round(r['last'] / unit)))
        items += [(GROUP_GLYPH.get(r['slug'], 'box'), colour)] * n
        legend.append((r['name'], usdk(r['last']), colour))
    cols, cell = 50, 26.0
    body, h, W = P.scene(items, cols, cell, cols * cell)
    TOP = 46.0
    body = f'<g transform="translate(0,{TOP})">{body}</g>'
    x, y = 0.0, TOP + h + 26
    for name, amt, colour in legend:
        body += (f'<rect x="{x:.1f}" y="{y - 9:.1f}" width="10" height="10" rx="2" '
                 f'fill="{colour}"/>')
        body += (f'<text x="{x + 15:.1f}" y="{y:.1f}" font-size="11" fill="#0b0b0b">'
                 f'{P._esc(name)}</text>')
        body += (f'<text x="{x + 15 + len(name) * 5.9 + 6:.1f}" y="{y:.1f}" '
                 f'font-size="11" fill="#52514e">{amt}</text>')
        x += 15 + len(name) * 5.9 + 52
        if x > W - 240:
            x, y = 0.0, y + 18
    return svg(W, y + 10, body,
               'What the town votes for, as a town',
               'One icon is $100,000 of the FY%d budget, %d in all, each department drawn '
               'in a thing it buys.' % (d['detail_years'][-1], len(items)))


def chart_icons(d):
    """THE SIGNATURE IMAGE: each department drawn in a thing it buys, in proportion.

    ONE ICON IS A MILLION DOLLARS, printed on the chart, because the unit is the whole
    contract between the picture and the number.

    REPEATED RATHER THAN SCALED. A fire truck drawn twice as tall is four times the ink
    and reads as some number between two and four; twenty-five school glyphs beside four
    is a ratio a reader can count. It also makes the range legible in a way no pie can:
    the largest department here is 313 times the smallest, and at this unit the smallest
    four are visibly a fraction of one icon.
    """
    rows_in = sorted([r for r in d['departments'] if r.get('last')],
                     key=lambda r: -r['last'])
    unit = 1_000_000
    rows = [(r['name'], r['last'], GROUP_GLYPH.get(r['slug'], 'box'), usdk(r['last']))
            for r in rows_in]
    TOP = 46.0
    # THE WIDEST ROW HAS TO FIT ITS OWN LABEL. Twenty-five icons plus a 196px name plus
    # `$25.13M` at the end ran off a 740px canvas and the figure was cut in half.
    body, h, _ = P.pictogram(rows, unit, '', SLICES, cols=25, size=16.0, gap=2.4,
                             label_w=190.0)
    body = f'<g transform="translate(0,{TOP})">{body}</g>'
    return svg(740, h + TOP + 4, body,
               'What the town votes for, drawn in what it buys',
               'One icon is $1 million of the FY%d voted budget. `Protection of persons & '
               'property` is the Police and the Fire Department together, drawn as one. A '
               'part-icon is a department that does not reach a million.'
               % d['detail_years'][-1])


CHARTS = [('town-budgets-town.svg', chart_town),
          ('town-budgets-share.svg', chart_share),
          ('town-budgets-all.svg', chart_all),
          ('town-budgets-rates.svg', chart_rates),
          ('town-budgets-trends.svg', chart_trends),
          ('town-budgets-total.svg', chart_total),
          ('town-budgets-pull.svg', chart_pull)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(PAYLOAD):
        print('missing %s -- run scripts/build_town_budgets.py first'
              % os.path.relpath(PAYLOAD, ROOT), file=sys.stderr)
        return 1
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    stale = []
    for name, fn in CHARTS:
        text = fn(d)
        path = os.path.join(OUT, name)
        if a.check:
            cur = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
            if cur != text:
                stale.append(name)
            continue
        open(path, 'w', encoding='utf-8').write(text)
        print('wrote %s' % os.path.relpath(path, ROOT))
    if a.check:
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('ok -- %d charts current' % len(CHARTS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
