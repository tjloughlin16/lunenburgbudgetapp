"""Draw what the stabilization funds could do about the gap, and for how long.

    python3 scripts/build_stabilization_option_charts.py
    python3 scripts/build_stabilization_option_charts.py --check

Writes `sources/analyses/charts/stabilization-option-*.svg`, which
`sources/analyses/stabilization-option.md` embeds and `build_analysis_pdf.py` renders
into the PDF.

TJ: *"can you add a graph or two? I think a burndown of the funds related to the deficit
... something that shows redirecting funds away (no more growth into these funds, then
the burndown) ... then burning them down and how it changes the deficits."*

TWO CHARTS, BECAUSE THEY ANSWER TWO QUESTIONS AND ONE CHART WOULD ANSWER NEITHER.

  1. THE BURNDOWN.      How long does the money last? A balance falling to zero, drawn
                        beside the yearly draw that empties it. The shape is the finding:
                        it does not taper, it stops.
  2. THE GAP, SPLIT.    What does any of it cover? One stacked bar per year, the whole
                        bar being that year's level-service gap, split into the part the
                        redirected deposits cover, the part the reserve covers, and the
                        part still short. The third segment is the answer to "then what".

EVERYTHING IS READ OUT OF THE PAYLOAD `build_stabilization_option.py` writes. Not
recomputed here and not typed: a chart that derives its own figures is a second model,
and the first thing two models do is disagree. The generator runs first; this refuses to
draw if its output is missing.

ONE AXIS, DOLLARS, ON BOTH. The balance and the gap are both money, so they CAN share an
axis -- and they are deliberately not put on one, because a falling balance and a rising
gap on one pair of axes is the dual-axis mistake wearing a disguise: the crossing point
would look like a finding and would be an artefact of two scales. They are two charts
on two panels, each with its own title saying what it measures.

COLOUR, VALIDATED RATHER THAN CHOSEN. The same three steps as the stabilization charts --
#184f95 blue, #e08214 amber, #2a8c6a green on the #fcfcfb surface -- so two reports about
one subject do not look like two projects. Worst adjacent CVD dE 9.9 (protan) against a
target of 8. The amber's 2.77:1 against the surface is a WARN that obligates visible
labels, so every segment worth reading is directly labelled and the analysis prints the
table underneath.

THESE RENDER TO PRINT, so there is no hover layer and every series is directly labelled.
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

PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'stabilization-option.json')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'charts')

REDIRECT = '#2a8c6a'   # money that arrives every year
RESERVE = '#184f95'    # money the town has once
SHORT = '#e08214'      # what neither covers


def svg(w, h, body, title, subtitle):
    """The shell. Same geometry as the stabilization charts, so the two sets line up."""
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


def fy(n):
    return 'FY%d' % n


# ------------------------------------------------------------------ 1. the burndown

def chart_burndown(d):
    """The balance falling to zero, one column a year, the draw that did it underneath.

    ONE ENCODING, NOT TWO. The first version drew the yearly draw as bars and the
    remaining balance as a line over them. Both are dollars of one fund so they may share
    an axis -- but the line's markers landed on the bars' value labels, and the year the
    fund empties got its annotation written across the bar beside it. Collisions are a
    symptom: two encodings were competing for the same 640px because the chart was
    answering two questions.

    So the bar IS the balance, and the draw is printed under the year as the step that
    got it there. A reader follows one falling shape and reads what each fall cost.

    AND IT OPENS AT THE FULL BALANCE. The first column is what the fund holds BEFORE any
    of this happens, labelled `now` rather than with a fiscal year, because it is a
    reading off the general ledger rather than a projected one. Without it the chart
    opened at the balance after the first year's draw and silently understated the fund
    by that draw.
    """
    rows = d['both']
    opening = rows[0]['left'] + rows[0]['drawn']
    cols = [dict(label='now', left=opening, drawn=0.0)] + [
        dict(label=fy(r['fy']), left=r['left'], drawn=r['drawn']) for r in rows]

    W, H = 640, 300
    L, R, T, B = 58, 24, 56, 56
    top = nice_top(opening)
    n = len(cols)
    step = (W - L - R) / n
    bw = min(38.0, step * 0.58)

    def cx(i):
        return L + step * (i + 0.5)

    def Y(v):
        return H - B - v / top * (H - T - B)

    b = []
    for i in range(5):
        v = top * i / 4
        b.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W - R}" y2="{Y(v):.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="{L - 6}" y="{Y(v) + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="end" fill="{MUTED}">{usdk(v)}</text>')
    b.append(f'<line x1="{L}" y1="{H - B}" x2="{W - R}" y2="{H - B}" '
             f'stroke="{AXIS}" stroke-width="1"/>')

    for i, c in enumerate(cols):
        x = cx(i) - bw / 2
        if c['left'] > 0:
            y = Y(c['left'])
            # The opening column is the reading; every later one is projected, so it is
            # drawn back to let the ledger figure lead.
            fade = '' if i == 0 else ' opacity="0.55"'
            b.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                     f'height="{H - B - y:.1f}" rx="4" fill="{RESERVE}"{fade}/>')
            b.append(f'<text x="{cx(i):.1f}" y="{y - 6:.1f}" font-size="9" '
                     f'text-anchor="middle" fill="{SECOND}">{usdk(c["left"])}</text>')
        else:
            # A zero balance draws nothing, so it needs a word or the column reads as
            # missing data rather than as an empty fund.
            b.append(f'<text x="{cx(i):.1f}" y="{H - B - 7:.1f}" font-size="9.5" '
                     f'font-weight="600" text-anchor="middle" fill="{INK}">empty</text>')
        b.append(f'<text x="{cx(i):.1f}" y="{H - B + 14}" font-size="9" '
                 f'text-anchor="middle" fill="{MUTED}">{esc(c["label"])}</text>')
        if c['drawn'] > 0:
            b.append(f'<text x="{cx(i):.1f}" y="{H - B + 26}" font-size="9" '
                     f'text-anchor="middle" fill="{RESERVE}">'
                     f'\u2212{usdk(c["drawn"])}</text>')

    b.append(f'<text x="{L}" y="{H - B + 42}" font-size="9" fill="{MUTED}">'
             f'bar: what is left in the fund \u2014 under each year: what was drawn out '
             f'of it that year</text>')
    return svg(W, H, ''.join(b),
               'The reserve, drawn down against the gap',
               'The general Stabilization Fund spent on the school gap, after the '
               'redirected deposits have covered what they can')


# ------------------------------------------------------- 2. the gap, split three ways

def chart_split(d):
    """One bar per year, the whole bar the gap, split by what covers it.

    A STACKED BAR RATHER THAN THREE LINES, because the parts sum to a whole a reader
    already knows -- that year's gap -- and the question is the SHARE each covers. Three
    lines would make the reader add them up in their head to get back to the thing the
    page is about.
    """
    rows = d['both']
    W, H = 640, 330
    L, R, T, B = 58, 24, 56, 58
    top = nice_top(max(r['gap'] for r in rows))
    n = len(rows)
    step = (W - L - R) / n
    bw = min(40.0, step * 0.56)

    def cx(i):
        return L + step * (i + 0.5)

    def Y(v):
        return H - B - v / top * (H - T - B)

    b = []
    for i in range(5):
        v = top * i / 4
        b.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W - R}" y2="{Y(v):.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        b.append(f'<text x="{L - 6}" y="{Y(v) + 3.5:.1f}" font-size="9.5" '
                 f'text-anchor="end" fill="{MUTED}">{usdk(v)}</text>')
    b.append(f'<line x1="{L}" y1="{H - B}" x2="{W - R}" y2="{H - B}" '
             f'stroke="{AXIS}" stroke-width="1"/>')

    for i, r in enumerate(rows):
        x = cx(i) - bw / 2
        base = H - B
        # Bottom up: the recurring money, then the one-off, then what neither covers.
        # A 2px surface gap between segments, so two fills never touch.
        for value, colour in ((r['redirected'], REDIRECT), (r['drawn'], RESERVE),
                              (r['shortfall'], SHORT)):
            if value <= 0:
                continue
            h = (H - T - B) * value / top
            y = base - h
            b.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                     f'height="{max(h - 2, 1):.1f}" rx="2" fill="{colour}"/>')
            base = y
        b.append(f'<text x="{cx(i):.1f}" y="{Y(r["gap"]) - 6:.1f}" font-size="9" '
                 f'text-anchor="middle" fill="{SECOND}">{usdk(r["gap"])}</text>')
        b.append(f'<text x="{cx(i):.1f}" y="{H - B + 14}" font-size="9" '
                 f'text-anchor="middle" fill="{MUTED}">{fy(r["fy"])}</text>')

    # The key, under the chart and after it -- rule 7a: a legend is read once the reader
    # has seen the thing it is a legend to.
    key = [(REDIRECT, 'deposits redirected — every year'),
           (RESERVE, 'drawn from the reserve — once'),
           (SHORT, 'still short')]
    kx = L
    for colour, label in key:
        b.append(f'<rect x="{kx}" y="{H - B + 26}" width="9" height="9" rx="2" '
                 f'fill="{colour}"/>')
        b.append(f'<text x="{kx + 13}" y="{H - B + 34.5}" font-size="9.5" '
                 f'fill="{SECOND}">{esc(label)}</text>')
        kx += 15 + len(label) * 5.3
    return svg(W, H, ''.join(b),
               'The gap each year, and what each option covers of it',
               'Each bar is that year’s level-service shortfall. The redirected '
               'deposit arrives every year; the reserve is spent once')


CHARTS = [('stabilization-option-burndown.svg', chart_burndown),
          ('stabilization-option-split.svg', chart_split)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    if not os.path.exists(PAYLOAD):
        print('missing %s -- run scripts/build_stabilization_option.py first'
              % os.path.relpath(PAYLOAD, ROOT), file=sys.stderr)
        return 1
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    if not d.get('both'):
        print('the payload carries no `both` scenario; nothing to draw', file=sys.stderr)
        return 1

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
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(path, ROOT))

    if a.check:
        if stale:
            print('STALE %s -- run: python3 scripts/build_stabilization_option_charts.py'
                  % ', '.join(stale), file=sys.stderr)
            return 1
        print('ok -- %d charts current' % len(CHARTS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
