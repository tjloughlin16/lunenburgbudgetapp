#!/usr/bin/env python3
"""Two charts for board composition: where the seats are, and how they move.

    python3 scripts/build_board_composition_charts.py
    python3 scripts/build_board_composition_charts.py --check

Writes `sources/analyses/charts/board-composition-*.svg`.

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

PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'board-composition.json')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'charts')

ELECTED = '#184f95'
APPOINTED = '#e08214'
OFFICER = '#2a8c6a'
SLICES = ['#12325f', '#184f95', '#3f78bd', '#7ea6d8', '#8a5210', '#b86d15',
          '#e08214', '#eeb069', '#17563f', '#22795a', '#9aa4ad']


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


def chart_where(d):
    """A pie of the town's seats by body, with the long tail grouped."""
    rows = sorted(d['sizes'], key=lambda r: -r['people'])
    top = rows[:10]
    tail = rows[10:]
    parts = [(r['post'], r['people']) for r in top]
    if tail:
        parts.append(('%d smaller bodies and single-holder posts' % len(tail),
                      sum(r['people'] for r in tail)))
    total = sum(n for _p, n in parts)
    W, H = 720, 400
    cx, cy, R = 210.0, 236.0, 140.0
    b, ang = [], -90.0
    for i, (_name, n) in enumerate(parts):
        frac = n / total
        sweep = frac * 360.0
        a0, a1 = math.radians(ang), math.radians(ang + sweep)
        x0, y0 = cx + R * math.cos(a0), cy + R * math.sin(a0)
        x1, y1 = cx + R * math.cos(a1), cy + R * math.sin(a1)
        big = 1 if sweep > 180 else 0
        b.append(f'<path d="M{cx:.1f},{cy:.1f} L{x0:.1f},{y0:.1f} '
                 f'A{R},{R} 0 {big},1 {x1:.1f},{y1:.1f} Z" fill="{SLICES[i % 11]}" '
                 f'stroke="{SURFACE}" stroke-width="2"/>')
        if frac >= 0.05:
            am = math.radians(ang + sweep / 2)
            lx, ly = cx + R * 0.64 * math.cos(am), cy + R * 0.64 * math.sin(am)
            b.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" font-size="11" '
                     f'font-weight="700" text-anchor="middle" fill="#ffffff">{n}</text>')
        ang += sweep
    lx = 400
    for i, (name, n) in enumerate(parts):
        ly = 70 + i * 26.0
        b.append(f'<rect x="{lx}" y="{ly - 9:.1f}" width="11" height="11" rx="2" '
                 f'fill="{SLICES[i % 11]}"/>')
        b.append(f'<text x="{lx + 18}" y="{ly:.1f}" font-size="10.5" fill="{INK}">'
                 f'{esc(name[:38])}</text>')
        b.append(f'<text x="{W}" y="{ly:.1f}" font-size="10.5" text-anchor="end" '
                 f'fill="{SECOND}">{n}</text>')
    return svg(W, H, ''.join(b),
               'Where the town’s seats are, FY%s' % d['last'],
               'Every filled post in the listing, by body. The ten largest are named; the '
               'rest are grouped, and the table beneath ranks all of them.')


def _lines(b, series, xs, Y, cx, colours, labels):
    for key, colour in zip(series, colours):
        pts = ' '.join('%.1f,%.1f' % (cx(i), Y(v)) for i, v in enumerate(series[key]))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                 f'stroke-width="2" stroke-linejoin="round"/>')
        for i, v in enumerate(series[key]):
            b.append(f'<circle cx="{cx(i):.1f}" cy="{Y(v):.1f}" r="3.2" fill="{colour}"/>')
        b.append(f'<text x="{cx(len(xs) - 1) + 8:.1f}" y="{Y(series[key][-1]) + 4:.1f}" '
                 f'font-size="10.5" fill="{colour}">{esc(labels[key])}</text>')


def chart_fill(d):
    """Names printed against the seats the charters create.

    NOT a chart of seat COUNTS. TJ: *"The boards have a charter that says how many seats
    are in them. why would that chagne?!"* -- exactly, and the first version of this panel
    drew those counts over ten years and called their flatness a finding. A charter fixes
    the number; a line that moves is measuring our reading of the listing, not the town.

    What the town can change, and has, is whether those seats have anybody in them. Above
    100% is not an overfull board: it is a mid-year replacement printed beside the person
    replaced, so the figure is drawn as it falls rather than capped, with the line marked.
    """
    fill = d['fill']
    W, H = 720, 300
    top, left, bottom, right = 58, 52, 42, 92
    plot_h, plot_w = H - top - bottom, W - left - right
    hi = max(max(f['pct'] for f in fill) * 1.12, 110)

    def cx(i):
        return left + (plot_w * i / max(len(fill) - 1, 1))

    def Y(v):
        return top + plot_h - (v / hi) * plot_h

    b = []
    for v in (0, 25, 50, 75, 100):
        y = Y(v)
        b.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="{left - 6}" y="{y + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="end" fill="{MUTED}">{v}%</text>')
    b.append(f'<line x1="{left}" y1="{Y(100):.1f}" x2="{left + plot_w}" y2="{Y(100):.1f}" '
             f'stroke="{AXIS}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    b.append(f'<text x="{left + plot_w + 6}" y="{Y(100) + 3.5:.1f}" font-size="9.5" '
             f'fill="{SECOND}">every seat</text>')
    pts = ' '.join('%.1f,%.1f' % (cx(i), Y(f['pct'])) for i, f in enumerate(fill))
    b.append(f'<polyline points="{pts}" fill="none" stroke="{ELECTED}" stroke-width="2.5"/>')
    for i, f in enumerate(fill):
        colour = ELECTED if f['pct'] >= 100 else APPOINTED
        b.append(f'<circle cx="{cx(i):.1f}" cy="{Y(f["pct"]):.1f}" r="3.6" fill="{colour}"/>')
        b.append(f'<text x="{cx(i):.1f}" y="{top + plot_h + 15:.1f}" font-size="9" '
                 f'text-anchor="middle" fill="{MUTED}">{f["fy"][2:]}</text>')
    last = fill[-1]
    b.append(f'<text x="{cx(len(fill) - 1):.1f}" y="{Y(last["pct"]) - 9:.1f}" '
             f'font-size="10.5" font-weight="700" text-anchor="middle" '
             f'fill="{APPOINTED}">{last["pct"]:.0f}%</text>')
    return svg(W, H, ''.join(b),
               'Are the chartered seats filled?',
               'Names printed against the seats the charters create, over the %d bodies '
               'that state a plain size. Above 100%% is a mid-year replacement printed '
               'beside the person replaced.' % last['bodies'])


CHARTS = [('board-composition-where.svg', chart_where),
          ('board-composition-fill.svg', chart_fill)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(PAYLOAD):
        print('missing %s -- run scripts/build_board_composition.py first'
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
