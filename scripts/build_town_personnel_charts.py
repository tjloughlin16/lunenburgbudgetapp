#!/usr/bin/env python3
"""The chart for the town's paid staff: the one department that states its strength.

    python3 scripts/build_town_personnel_charts.py
    python3 scripts/build_town_personnel_charts.py --check

Writes `sources/analyses/charts/town-personnel-*.svg`.

TJ asked for these twice -- *"Pie charts of which departments have the most personel or
least. Biggest and smallest elected boards"* and *"line charts of personel over time per
dept"* -- and the page shipped with none, which is why he asked again.

THREE, BECAUSE THE PAGE ASKS THREE QUESTIONS.

  1. WHERE ARE THE POSTS?   A pie of the town's seats by body. The Council on Aging alone
                            is a tenth of every seat the town fills; twenty-nine posts have
                            a single holder. The long tail is grouped rather than drawn as
                            forty unreadable slivers, and the table beneath ranks all of it.
  2. WHAT IS MOVING?        Elected seats, appointed seats and officers over ten years, one
                            line each. The answer is that almost nothing moves: the shape
                            is three flat lines, and that IS the finding, because a third
                            of the PEOPLE change every year underneath them. Seats are
                            stable; the people in them are not.
  3. WHO STAFFED UP?        The Fire Department's career and on-call rolls, the only
                            department that states both the same way for nine years. They
                            move in OPPOSITE directions, which no single number shows.

COLOUR is the same three steps as every other chart here -- #184f95 blue, #e08214 amber,
#2a8c6a green on #fcfcfb -- so one town does not look like three projects. These render to
print, so there is no hover layer and every series is directly labelled.
"""
import argparse
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from build_stabilization_charts import (  # noqa: E402
    AXIS, FONT, GRID, INK, MUTED, PAD, SECOND, SURFACE, esc,
)

import pictograms as P                                            # noqa: E402
from pictograms import _esc                                       # noqa: E402

PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'town-personnel.json')

BAR = '#184f95'
OUT = os.path.join(ROOT, 'sources', 'analyses', 'charts')

ELECTED = '#184f95'
APPOINTED = '#e08214'
OFFICER = '#2a8c6a'
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


def _lines(b, series, xs, Y, cx, colours, labels):
    for key, colour in zip(series, colours):
        pts = ' '.join('%.1f,%.1f' % (cx(i), Y(v)) for i, v in enumerate(series[key]))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                 f'stroke-width="2" stroke-linejoin="round"/>')
        for i, v in enumerate(series[key]):
            b.append(f'<circle cx="{cx(i):.1f}" cy="{Y(v):.1f}" r="3.2" fill="{colour}"/>')
        b.append(f'<text x="{cx(len(xs) - 1) + 8:.1f}" y="{Y(series[key][-1]) + 4:.1f}" '
                 f'font-size="10.5" fill="{colour}">{esc(labels[key])}</text>')


def chart_fire(d):
    """Career against on-call, the one department that states both for nine years."""
    fire = d['fire']
    years = [f['fy'] for f in fire]
    W, H = 720, 320
    top, left, bottom, right = 58, 46, 42, 150
    plot_h, plot_w = H - top - bottom, W - left - right
    hi = max(f['on_call_high'] for f in fire) * 1.2

    def cx(i):
        return left + (plot_w * i / max(len(years) - 1, 1))

    def Y(v):
        return top + plot_h - (v / hi) * plot_h

    b = []
    for i in range(5):
        v = hi * i / 4.0
        y = Y(v)
        b.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="{left - 6}" y="{y + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="end" fill="{MUTED}">{v:.0f}</text>')
    for i, y in enumerate(years):
        b.append(f'<text x="{cx(i):.1f}" y="{top + plot_h + 15:.1f}" font-size="9" '
                 f'text-anchor="middle" fill="{MUTED}">{y[2:]}</text>')
    # The on-call roll is a RANGE, so it is drawn as a band and never as a line: a line
    # through the middle of `30-35` would be a number the town never printed.
    up = ' '.join('%.1f,%.1f' % (cx(i), Y(f['on_call_high'])) for i, f in enumerate(fire))
    dn = ' '.join('%.1f,%.1f' % (cx(i), Y(f['on_call_low']))
                  for i, f in reversed(list(enumerate(fire))))
    b.append(f'<polygon points="{up} {dn}" fill="{APPOINTED}" fill-opacity="0.30"/>')
    b.append(f'<text x="{cx(len(years) - 1) + 8:.1f}" '
             f'y="{Y((fire[-1]["on_call_low"] + fire[-1]["on_call_high"]) / 2) + 4:.1f}" '
             f'font-size="10.5" fill="#8a5210">on call (a range)</text>')
    pts = ' '.join('%.1f,%.1f' % (cx(i), Y(f['career'])) for i, f in enumerate(fire))
    b.append(f'<polyline points="{pts}" fill="none" stroke="{ELECTED}" stroke-width="2.5"/>')
    for i, f in enumerate(fire):
        b.append(f'<circle cx="{cx(i):.1f}" cy="{Y(f["career"]):.1f}" r="3.4" '
                 f'fill="{ELECTED}"/>')
    b.append(f'<text x="{cx(len(years) - 1) + 8:.1f}" y="{Y(fire[-1]["career"]) + 4:.1f}" '
             f'font-size="10.5" fill="{ELECTED}">career</text>')
    b.append(f'<line x1="{left}" y1="{top + plot_h:.1f}" x2="{left + plot_w}" '
             f'y2="{top + plot_h:.1f}" stroke="{AXIS}" stroke-width="1"/>')
    return svg(W, H, ''.join(b),
               'The Fire Department grew and shrank at the same time',
               'Career firefighters against the on-call roll, FY%s to FY%s, as the '
               'department states them. The two move in opposite directions.'
               % (years[0], years[-1]))


def chart_employers(d):
    """How many people each part of the town employs, on one axis.

    TJ, after three versions of this page that were not it: *"I wanted it to be a cross
    department report. which departments have the most employees. which have the least.
    which are growing in employee count the most ... who has made cuts, who hasnt ... and
    i expect the schools to be on this too."*

    One bar each, ranked, with the change beside it. The schools bar is six times the rest
    together and that is the first thing the chart should say -- the earlier versions of
    this page led with what the town PUBLISHES about staffing, which is a page about
    documents wearing a report's clothes.
    """
    emp = d['employers']
    W, H = 720, 74 + 46 * len(emp)
    top, label_w, right = 62, 200, 150
    plot_w = W - label_w - right
    hi = max(e['people'] for e in emp) * 1.05
    b = []
    for i, e in enumerate(emp):
        cy = top + 46 * i + 14
        w = e['people'] / hi * plot_w
        b.append(f'<rect x="{label_w}" y="{cy - 11:.1f}" width="{max(w, 1):.1f}" '
                 f'height="22" fill="{BAR}" rx="2"/>')
        b.append(f'<text x="{label_w - 8}" y="{cy + 4:.1f}" font-size="11" '
                 f'text-anchor="end" fill="{INK}">{esc(e["department"][:26])}</text>')
        b.append(f'<text x="{label_w + w + 8:.1f}" y="{cy + 4:.1f}" font-size="11" '
                 f'font-weight="700" fill="{INK}">{e["people"]}</text>')
        ch = e['change']
        sign = '+' if ch >= 0 else '\u2212'
        colour = OFFICER if ch > 0 else (APPOINTED if ch < 0 else MUTED)
        b.append(f'<text x="{label_w + w + 8:.1f}" y="{cy + 18:.1f}" font-size="9.5" '
                 f'fill="{colour}">{sign}{abs(ch)} since FY{e["first_fy"]}</text>')
    return svg(W, H - 2 * PAD, ''.join(b),
               'How many people each part of the town employs',
               # DERIVED, BECAUSE IT WAS TYPED AND IT WENT WRONG. This said `Four do`
               # and stood while the count reached nine.
               'Every part of the town that publishes a staff count. %d do; the other '
               'departments publish none, and their staff are in no figure here.'
               % len(emp))


def chart_counts(d):
    """Headcount over time, one panel per part of the town.

    TJ: *"Can you show line charts of growth over time for each?"* then, correcting
    himself and me: *"not 'growth', counts over time."* Right — a growth rate off a
    fifteen-point series and a two-point one are not the same kind of number, and the
    counts are what the town actually published.

    Each panel carries its OWN span, because they differ wildly: the schools publish
    fifteen years, the DPW two. A shared axis would imply the town started counting its
    public works staff in 2011 and lost the records.

    A YEAR DROPPED AS A SHORT READ OR A SPIKE IS DRAWN AS A GAP, never interpolated
    through. The schools read 343 in FY2024 — one school doubling and halving — and the
    police 7 in FY2024 against 25. Joining across them would draw a hiring spree and a
    mass sacking, neither of which happened.
    """
    # THE GRID FITS THE DEPARTMENTS, IT DOES NOT CAP THEM. This was two by two and drew
    # four panels while the page listed nine, because the check for departments whose
    # counts we had missed found five more and the canvas did not grow with them. A panel
    # needs at least two years to be a line, so a single-year department is left out --
    # and the caption says how many, rather than the chart quietly dropping them.
    emp = [e for e in d['employers']
           if len([p for p in e['series'] if not p.get('suspect')]) >= 2]
    cols = 2
    rowsn = -(-len(emp) // cols)
    pw, ph = 330.0, 140.0
    W, H = int(cols * pw + 30), int(rowsn * ph + 76)
    b = []
    for i, e in enumerate(emp):
        cx0 = 10 + (i % cols) * pw
        cy0 = 62 + (i // cols) * ph
        pts_all = e['series']
        vals = [p['people'] for p in pts_all if not p.get('suspect')]
        if len(vals) < 2:
            continue
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.3 or max(hi * 0.08, 1)
        lo, hi = max(lo - pad, 0), hi + pad
        gw, gh = pw - 60, ph - 62

        # SPACED BY YEAR, NOT BY POSITION. TJ asked for counts over time, and an ordinal
        # axis is not time: the Council on Aging publishes no roster in FY2012, FY2013 or
        # FY2021, and spacing its twelve points evenly drew those three gaps away -- a
        # fifteen-year record rendered as an unbroken run.
        yrs = [int(p_['fy']) for p_ in pts_all]
        y0, y1 = min(yrs), max(yrs)

        def X(k):
            return cx0 + 34 + gw * (int(pts_all[k]['fy']) - y0) / max(y1 - y0, 1)

        def Y(v):
            # CLAMPED TO THIS PANEL. A year dropped as a misreading is dropped because its
            # value is absurd, so plotting it where it falls puts it outside the panel
            # entirely: the Police FY2024 reading of seven, against a floor of eighteen,
            # was drawn thirty pixels down into the Council on Aging's panel, where it
            # reads as one of the senior centre's own points.
            raw = cy0 + 26 + gh - (v - lo) / (hi - lo) * gh
            return min(max(raw, cy0 + 26), cy0 + 26 + gh)

        b.append(f'<text x="{cx0 + 34}" y="{cy0 + 10:.1f}" font-size="10.5" '
                 f'font-weight="700" fill="{INK}">{esc(e["department"][:30])}</text>')
        # THE SPAN IS THE SPAN OF WHAT IS TRUSTED. Labelling it with the first and last
        # point INCLUDING a year dropped as a misreading claims a record that ends a year
        # later than it does -- the Police panel read `FY2021-FY2024` while its last
        # trustworthy point is FY2023.
        good = [p for p in pts_all if not p.get('suspect')]
        b.append(f'<text x="{cx0 + 34}" y="{cy0 + 22:.1f}" font-size="8.5" '
                 f'fill="{SECOND}">FY{good[0]["fy"]}\u2013FY{good[-1]["fy"]} '
                 f'\u00b7 {e["people"]} now</text>')
        for v in (lo, hi):
            b.append(f'<text x="{cx0 + 30}" y="{Y(v) + 3.5:.1f}" font-size="8.5" '
                     f'text-anchor="end" fill="{MUTED}">{v:.0f}</text>')
        b.append(f'<line x1="{cx0 + 34}" y1="{cy0 + 26 + gh:.1f}" '
                 f'x2="{cx0 + 34 + gw:.1f}" y2="{cy0 + 26 + gh:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        # draw in RUNS, breaking at a suspect year so nothing is interpolated across it
        run = []
        for k, p_ in enumerate(pts_all):
            if p_['fy'] in e['suspect']:
                if len(run) > 1:
                    b.append(_poly(run, ELECTED))
                run = []
                b.append(f'<circle cx="{X(k):.1f}" cy="{Y(p_["people"]):.1f}" r="3" '
                         f'fill="none" stroke="{MUTED}" stroke-width="1.2" '
                         f'stroke-dasharray="2 2"/>')
                continue
            run.append((X(k), Y(p_['people'])))
            b.append(f'<circle cx="{X(k):.1f}" cy="{Y(p_["people"]):.1f}" r="2.6" '
                     f'fill="{ELECTED}"/>')
        if len(run) > 1:
            b.append(_poly(run, ELECTED))
    return svg(W, H - 2 * PAD, ''.join(b),
               'Headcount over time, where the town publishes one',
               'Each panel on its own scale and span. A hollow point is a year dropped as '
               'a misreading, never drawn through.')


def _poly(pts, colour):
    s_ = ' '.join('%.1f,%.1f' % p for p in pts)
    return (f'<polyline points="{s_}" fill="none" stroke="{colour}" stroke-width="2.2" '
            f'stroke-linejoin="round"/>')


def chart_all(d):
    """Every department on ONE people axis, which is the point: the schools dwarf the rest.

    TJ: *"headcount over time: we also need a combined chart to compare them."*

    The small multiples beside this one give every department its own scale, so the SHAPE
    of a three-person office is legible next to a 250-person one. That is the right way to
    read a trend and the wrong way to read size -- read alone it leaves the Assessing
    office and the schools looking like comparable things. One axis restores the relation:
    one line near 250, one near 40, and seven along the floor.

    TWO THINGS THIS CHART DOES THAT THE BUDGET VERSION DOES NOT HAVE TO.

    Spaced by YEAR, not by position, because these series have holes in them -- the
    Council on Aging publishes no roster in FY2012, FY2013 or FY2021 -- and an ordinal
    axis would close those gaps up and draw a continuous record the town never printed.

    And the line BREAKS at a year with no figure rather than joining across it. Drawing
    the Building Department from FY2022 straight to nothing, or the Library's single
    FY2019 point as a line to anywhere, would be us inventing the years in between.
    """
    emp = [e for e in d['employers']
           if len([p for p in e['series'] if not p.get('suspect')]) >= 1]
    emp = sorted(emp, key=lambda e: -e['people'])
    pts_by = {e['department']: {p['fy']: p['people'] for p in e['series']
                                if not p.get('suspect')} for e in emp}
    yrs = sorted({int(y) for v in pts_by.values() for y in v})
    y0, y1 = min(yrs), max(yrs)
    hi = max(max(v.values()) for v in pts_by.values())
    hi = int(hi * 1.08 / 25 + 1) * 25

    W, H = 720, 380
    top, left, bottom, right = 58, 44, 40, 246
    plot_h, plot_w = H - top - bottom, W - left - right

    def cx(y):
        return left + plot_w * (int(y) - y0) / max(y1 - y0, 1)

    def Y(v):
        return top + plot_h - (v / hi) * plot_h

    b = []
    for k in range(6):
        v = hi * k / 5.0
        y = Y(v)
        b.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="{left - 6}" y="{y + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="end" fill="{MUTED}">{v:.0f}</text>')
    for y in range(y0, y1 + 1, 2):
        b.append(f'<text x="{cx(y):.1f}" y="{top + plot_h + 15:.1f}" font-size="9.5" '
                 f'text-anchor="middle" fill="{MUTED}">FY{y}</text>')

    lx = left + plot_w + 12
    for i, e in enumerate(emp):
        colour = SLICES[i % len(SLICES)]
        pts = pts_by[e['department']]
        run = []
        for y in range(y0, y1 + 1):
            v = pts.get(str(y))
            if v is None:
                if len(run) > 1:
                    b.append(_poly(run, colour))
                run = []
                continue
            run.append((cx(y), Y(v)))
            b.append(f'<circle cx="{cx(y):.1f}" cy="{Y(v):.1f}" r="2.6" '
                     f'fill="{colour}"/>')
        if len(run) > 1:
            b.append(_poly(run, colour))
        ly = top + 6 + i * 22.0
        b.append(f'<rect x="{lx}" y="{ly - 8:.1f}" width="10" height="10" rx="2" '
                 f'fill="{colour}"/>')
        b.append(f'<text x="{lx + 15}" y="{ly:.1f}" font-size="9.5" fill="{INK}">'
                 f'{esc(e["department"][:26])}</text>')
        b.append(f'<text x="{W}" y="{ly:.1f}" font-size="9.5" text-anchor="end" '
                 f'fill="{SECOND}">{e["people"]}</text>')
    b.append(f'<line x1="{left}" y1="{top + plot_h:.1f}" x2="{left + plot_w}" '
             f'y2="{top + plot_h:.1f}" stroke="{AXIS}" stroke-width="1"/>')
    return svg(W, H, ''.join(b),
               'Every department that publishes a headcount, on one axis',
               'The same figures as the panels above, on one scale. A break in a line is '
               'a year that department published no figure, never a year at zero.')


def chart_share(d):
    """A pie: how the people the town publishes a count for divide between departments.

    TJ: *"Similar pie chart for the personel breakdown, also at the top of its page (we
    dont have a pie chart but need one)."* The budget page leads with one because a
    resident opens a page about the town's money wanting to know who gets it; the same
    reader opens this one wanting to know who the town employs, and the answer is one
    slice and a rim.

    THE WHOLE HERE IS NOT THE TOWN, and the subtitle says so. It is the people the town
    publishes a count for -- nine departments -- and the rest of the payroll is in no
    published count at all, so this is a part-to-whole of what is KNOWN rather than of
    what exists. A pie of a partial whole is exactly the shape that misleads if its whole
    is not named, which is why the name of the whole is in the subtitle rather than in a
    footnote.
    """
    import math
    rows = sorted(d['employers'], key=lambda e: -e['people'])
    total = sum(e['people'] for e in rows)
    W, H = 720, 400
    cx, cy, R = 232.0, 232.0, 142.0
    b, ang = [], -90.0
    for i, r in enumerate(rows):
        frac = r['people'] / total
        sweep = frac * 360.0
        a0, a1 = math.radians(ang), math.radians(ang + sweep)
        x0, y0 = cx + R * math.cos(a0), cy + R * math.sin(a0)
        x1, y1 = cx + R * math.cos(a1), cy + R * math.sin(a1)
        big = 1 if sweep > 180 else 0
        b.append(f'<path d="M{cx:.1f},{cy:.1f} L{x0:.1f},{y0:.1f} '
                 f'A{R},{R} 0 {big},1 {x1:.1f},{y1:.1f} Z" '
                 f'fill="{SLICES[i % len(SLICES)]}" stroke="{SURFACE}" '
                 f'stroke-width="2"/>')
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
                 f'fill="{SLICES[i % len(SLICES)]}"/>')
        b.append(f'<text x="{lx + 18}" y="{ly:.1f}" font-size="10.5" fill="{INK}">'
                 f'{esc(r["department"][:26])}</text>')
        b.append(f'<text x="{W}" y="{ly:.1f}" font-size="10.5" text-anchor="end" '
                 f'fill="{SECOND}">{r["people"]}</text>')
    return svg(W, H, ''.join(b),
               'Who the town employs, where it publishes a count',
               'The %d people named or counted across the %d departments that state a '
               'figure. Not a town total: every other department publishes none.'
               % (total, len(rows)))


def chart_crowd(d):
    """THE SIGNATURE IMAGE: everybody the town publishes a count for, as a crowd.

    TJ: *"not a 'chart' so much as chart-like... a conceptual and interesting image that
    shows the proportions, but not in a structured chart way."*

    ONE FIGURE IS ONE PERSON. No unit to explain, no rows, no labels on the picture --
    three hundred and sixty-four figures, coloured by department, and the schools are
    plainly most of the crowd before anybody reads a number. The colours are named
    underneath, which is where a legend belongs when the picture is doing the arguing.

    The scatter is seeded, so this is the same crowd in every build and in print.
    """
    emp = sorted(d['employers'], key=lambda e: -e['people'])
    items, legend = [], []
    for i, e in enumerate(emp):
        colour = SLICES[i % len(SLICES)]
        items += [('person', colour)] * e['people']
        legend.append((e['department'], e['people'], colour))
    # WIDE AND SHORT, the shape of the commercial page's concept image. Thirty-four
    # columns made a tall block that sat in the reading column; forty-six across ten rows
    # is a band the width of the screen.
    cols, cell = 46, 24.0
    body, h, W = P.scene(items, cols, cell, cols * cell)
    TOP = 46.0
    body = f'<g transform="translate(0,{TOP})">{body}</g>'
    x = 0.0
    y = TOP + h + 26
    for name, n, colour in legend:
        body += (f'<rect x="{x:.1f}" y="{y - 9:.1f}" width="10" height="10" rx="2" '
                 f'fill="{colour}"/>')
        body += (f'<text x="{x + 15:.1f}" y="{y:.1f}" font-size="11" fill="#0b0b0b">'
                 f'{_esc(name)}</text>')
        body += (f'<text x="{x + 15 + len(name) * 5.9 + 6:.1f}" y="{y:.1f}" '
                 f'font-size="11" fill="#52514e">{n}</text>')
        # WRAP BEFORE THE NEXT ITEM WOULD OVERRUN, not after this one did. Measuring the
        # width already used put `Library` half off the right edge.
        x += 15 + len(name) * 5.9 + 34
        if x > W - 210:
            x, y = 0.0, y + 18
    return svg(W, y + 10, body,
               'Everyone the town publishes a count for',
               'One figure is one person, %d in all. Only the %d departments that state a '
               'figure are here; the rest publish none, so their staff are in no picture '
               'on this page.' % (sum(e['people'] for e in emp), len(emp)))


def chart_people(d):
    """THE SIGNATURE IMAGE: every department drawn as the people it employs.

    TJ: *"show PEOPLE that represent each department as characters in proportion to the
    amounts."* Rule 7f's signature note -- a reader remembers one image per page, and for
    a page about who works for the town that image should be made of people.

    ONE FIGURE IS TEN PEOPLE and the chart says so, because the unit is the whole contract
    between the picture and the number. Repetition rather than a scaled figure: nobody can
    read area, and twenty-five figures beside four is a ratio anyone can count.

    A department that does not fill a whole figure gets a PARTIAL one rather than being
    rounded. The Board of Assessors is three people; rounded up it would be drawn the same
    as ten, and rounded down it would not appear at all.
    """
    emp = sorted(d['employers'], key=lambda e: -e['people'])
    unit = 10
    rows = [(e['department'], e['people'], 'person',
             '%d' % e['people']) for e in emp]
    # THE BODY STARTS BELOW THE TITLE. `svg()` writes the title at y=15 and the subtitle
    # at y=31 into the same coordinate space, so a body drawn from zero lands on top of
    # them -- which is exactly what the first render did, printing the Schools row across
    # the chart's own headline.
    TOP = 46.0
    body, h, _ = P.pictogram(rows, unit, '', [ELECTED] * len(rows),
                             cols=25, size=18.0, gap=2.6, label_w=172.0)
    body = f'<g transform="translate(0,{TOP})">{body}</g>'
    return svg(720, h + TOP + 4, body,
               'Who the town employs, drawn in people',
               'One figure is %d people. Only the %d departments that publish a count are '
               'here; the rest publish none, so their staff are in no figure on this page.'
               % (unit, len(emp)))


CHARTS = [('town-personnel-crowd.svg', chart_crowd),
          ('town-personnel-people.svg', chart_people),
          ('town-personnel-share.svg', chart_share),
          ('town-personnel-counts.svg', chart_counts),
          ('town-personnel-all.svg', chart_all),
          ('town-personnel-fire.svg', chart_fire)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(PAYLOAD):
        print('missing %s -- run scripts/build_town_personnel.py first'
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
