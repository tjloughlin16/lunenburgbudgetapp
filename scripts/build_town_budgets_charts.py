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
    """Diverging bars: how much of the budget's growth each department accounts for."""
    rows = [r for r in d['departments'] if r.get('pull') is not None]
    W, H = 720, 330
    top, label_w, bottom = 58, 168, 34
    plot_h = H - top - bottom
    span = max(abs(r['pull']) for r in rows) * 1.15 or 1.0
    zero = label_w + (W - label_w) * (span / (2 * span))
    half = (W - label_w) / 2.0
    rh = plot_h / len(rows)
    bh = min(16.0, rh * 0.68)

    b = [f'<line x1="{zero:.1f}" y1="{top - 6:.1f}" x2="{zero:.1f}" '
         f'y2="{top + plot_h:.1f}" stroke="{AXIS}" stroke-width="1"/>']
    for i, r in enumerate(rows):
        cy = top + rh * (i + 0.5)
        w = abs(r['pull']) / span * half
        up = r['pull'] >= 0
        x = zero if up else zero - w
        b.append(f'<rect x="{x:.1f}" y="{cy - bh / 2:.1f}" width="{max(w, 0.8):.1f}" '
                 f'height="{bh:.1f}" fill="{VOTED if up else DOWN}" rx="2"/>')
        b.append(f'<text x="{label_w - 8}" y="{cy + 3.5:.1f}" font-size="10" '
                 f'text-anchor="end" fill="{INK}">{esc(r["name"])}</text>')
        tx = (x + w + 6) if up else (x - 6)
        b.append(f'<text x="{tx:.1f}" y="{cy + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="{"start" if up else "end"}" fill="{SECOND}">'
                 f'{r["pull"]:+.2f}</text>')
    b.append(f'<text x="{zero + 8:.1f}" y="{top + plot_h + 20:.1f}" font-size="9.5" '
             f'fill="{MUTED}">pushes the total up</text>')
    b.append(f'<text x="{zero - 8:.1f}" y="{top + plot_h + 20:.1f}" font-size="9.5" '
             f'text-anchor="end" fill="{MUTED}">pulls it down</text>')
    return svg(W, H, ''.join(b), 'Which departments move the total',
               'Share of the budget times how far growth exceeds the %.1f%% levy cap, in '
               'points of total growth. FY%d to FY%d.'
               % (d['levy_cap'], d['detail_years'][0], d['detail_years'][-1]))


# Twelve steps, assigned in a fixed order by SIZE so the same department is the same
# colour on every redraw. Three hues, four lightnesses each -- a categorical ramp of
# twelve fully distinct hues would be unreadable at 2% of a circle, and the slices that
# small are labelled in the table rather than on the chart anyway.
SLICES = ['#12325f', '#184f95', '#3f78bd', '#7ea6d8',
          '#8a5210', '#b86d15', '#e08214', '#eeb069',
          '#17563f', '#22795a', '#2a8c6a', '#6fb79c']


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


CHARTS = [('town-budgets-share.svg', chart_share),
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
