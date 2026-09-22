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

PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'town-personnel.json')

BAR = '#184f95'
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
               'Every part of the town that publishes a staff count. Four do; the other '
               'departments publish none, and their staff are in no figure here.')


CHARTS = [('town-personnel-employers.svg', chart_employers),
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
