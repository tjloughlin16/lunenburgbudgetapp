"""Draw the three charts that head the FY26 closeout analyses.

    python3 scripts/build_closeout_charts.py            # both sides
    python3 scripts/build_closeout_charts.py --side town

Writes `sources/analyses/charts/fy26-<side>-<name>.svg`, which the Markdown embeds and
`build_analysis_pdf.py` renders into the PDF.

WHY THESE THREE FORMS, AND WHY NOT PIE CHARTS

A pie shows parts of a meaningful whole. Two of the three questions here are about
VARIANCE -- a signed quantity where direction is the whole point -- and a pie has no way
to show a negative. The third is a composition of more than seven categories, where a pie
becomes a colour-matching exercise. So:

  1. What happened to the budget   ONE stacked bar: spent / encumbered / unspent.
                                   Part-to-whole, three ordered parts, direct-labelled.

  2. Over and under               DIVERGING bar, zero in the middle, over to the right
                                   and under to the left. This is the chart that carries
                                   the actual finding: the net is small and the pieces
                                   are large and cancel. One picture answers "biggest
                                   overspend" and "biggest underspend" together, which
                                   two separate pies could not.

  3. Where the money goes         Horizontal bars, largest first, one hue. Magnitude
                                   compared across categories.

COLOUR, VALIDATED RATHER THAN CHOSEN

  diverging   #2a78d6 blue (under) <-> #e34948 red (over), gray zero line.
              all-pairs CVD dE 21.6, normal-vision 32.3, both >= 3:1 on the surface.
  ordinal     #184f95 / #3987e5 / #86b6ef, a single blue hue, light-end 2.06:1.

Both were run through the palette validator; the first ramp tried used step 200
(`#9ec5f4`), which failed the lightness band and the chroma floor and was re-stepped to
250. Colour is computable, so it was computed.

THESE RENDER TO PRINT, so there is no hover layer and every bar is directly labelled.
The analysis text underneath each chart is the table view.
"""
import argparse
import csv
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'charts')

# Validated. See the module docstring; do not substitute by eye.
UNDER = '#2a78d6'
OVER = '#e34948'
SEQ = ['#184f95', '#3987e5', '#86b6ef']
INK = '#0b0b0b'
SECOND = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
AXIS = '#c3c2b7'
SURFACE = '#fcfcfb'
FONT = ('system-ui, -apple-system, "Segoe UI", sans-serif')

# Readable titles for the ledger's ten-character codes.
#
# **These expansions are OURS.** Nothing published maps `SCHRETHLTH` to "school retiree
# health insurance"; the ledger prints the abbreviation and stops. So each one is recorded
# in sources/data/account-names.csv with the basis it rests on -- a district budget line
# that prints the full name, the department's own name, the object code's meaning, or a
# plain reading of the abbreviation -- and anything without a defensible basis keeps the
# code and gets no title at all.
#
# Keyed on DEPARTMENT, because the same code means different things in different places:
# `REG TRANS` is school busing in department 300 and a regional transit assessment in
# department 825. A lookup on the code alone would have silently mislabelled one of them.
NAMES_CSV = os.path.join(ROOT, 'sources', 'data', 'account-names.csv')


def load_names():
    by_org, by_obj = {}, {}
    if not os.path.exists(NAMES_CSV):
        return by_org, by_obj
    with open(NAMES_CSV, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['org']:
                # Keyed on the CODE as well as the org. Org S2066651 carries BOTH
                # HS GUIDANC and SOCWORKSAL, so a lookup on (dept, org) alone returned
                # the guidance title for the social worker line and printed it under the
                # wrong bar. Caught by rendering the chart and reading it.
                by_org[(r['dept'], r['org'], r['code'])] = r['readable']
            else:
                by_obj[(r['dept'], r['object'], r['code'])] = r['readable']
    return by_org, by_obj


BY_ORG, BY_OBJ = load_names()


def readable(dept, org, obj, code):
    """The title, or None. An unexpanded code shows as itself rather than as a guess."""
    return BY_ORG.get((dept, org, code)) or BY_OBJ.get((dept, obj, code))


def label(b, x, y, dept, org, obj, code, anchor='end'):
    """Two lines: our title above, the ledger's own code beneath it in muted ink.

    Both, always. The title is what a reader can follow; the code is what they would type
    into a records request, and it is the thing the town would recognise.
    """
    r = readable(dept, org, obj, code)
    if r:
        b.append(f'<text x="{x}" y="{y - 3}" font-size="9.5" text-anchor="{anchor}" '
                 f'fill="{SECOND}">{esc(r)}</text>')
        b.append(f'<text x="{x}" y="{y + 7}" font-size="7.5" text-anchor="{anchor}" '
                 f'fill="{MUTED}" font-family="Menlo, monospace">{esc(code)}</text>')
    else:
        b.append(f'<text x="{x}" y="{y + 2}" font-size="9.5" text-anchor="{anchor}" '
                 f'fill="{SECOND}" font-family="Menlo, monospace">{esc(code)}</text>')


SIDES = {
    'school': dict(where="a.dept = '300'", label='School department'),
    'town': dict(where="a.fund = '0100' AND a.dept NOT IN ('300','301')",
                 label='The town, 67 other departments'),
}


def usd(v, dp=0):
    return ('-$' if v < 0 else '$') + f'{abs(v):,.{dp}f}'


def usdk(v):
    a = abs(v)
    s = '-' if v < 0 else ''
    if a >= 1e6:
        return f'{s}${a / 1e6:.2f}M'
    return f'{s}${a / 1000:,.0f}k'


def esc(t):
    return (str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def svg(w, h, body, title, subtitle):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}"
 height="{h}" role="img" aria-label="{esc(title)}. {esc(subtitle)}"
 font-family='{FONT}'>
<rect width="{w}" height="{h}" fill="{SURFACE}"/>
<text x="0" y="15" font-size="13" font-weight="700" fill="{INK}">{esc(title)}</text>
<text x="0" y="31" font-size="10.5" fill="{SECOND}">{esc(subtitle)}</text>
{body}
</svg>
'''


def chart_budget(db, side, meta):
    """One stacked bar: how the revised budget was consumed."""
    r = db.execute(f"""SELECT SUM(revised) rv, SUM(expended) e, SUM(encumbered) en,
                              SUM(available) av
                       FROM ledger_snapshot l JOIN account a USING (account_id)
                       WHERE l.fy=2026 AND l.period=12 AND {meta['where']}""").fetchone()
    rv, parts = float(r[0]), [
        ('Spent', float(r[1]), SEQ[0]),
        ('Encumbered', float(r[2]), SEQ[1]),
        ('Unspent', float(r[3]), SEQ[2]),
    ]
    W, H, X, BW, Y, BH = 640, 158, 0, 640, 52, 30
    b, x = [], X
    for i, (lbl, v, col) in enumerate(parts):
        w = max(v / rv * BW, 1.2)
        # 2px surface gap between segments, per the mark spec.
        gap = 2 if i < len(parts) - 1 else 0
        b.append(f'<rect x="{x:.1f}" y="{Y}" width="{max(w - gap, 1):.1f}" height="{BH}" '
                 f'fill="{col}" rx="2"/>')
        x += w
    # Labels go in an evenly spaced row beneath, NOT centred under their own segment.
    # Encumbered is 0.9% of the bar and unspent 1.8%: a label centred on a six-pixel
    # segment lands on top of its neighbour, which is what the first render did. Each
    # label carries its own swatch instead, so identity survives the disconnection.
    lab = []
    slot = BW / len(parts)
    for i, (lbl, v, col) in enumerate(parts):
        x0 = X + i * slot
        lab.append(
            f'<rect x="{x0:.1f}" y="{Y + BH + 10}" width="9" height="9" fill="{col}" '
            f'rx="2"/>'
            f'<text x="{x0 + 14:.1f}" y="{Y + BH + 18}" font-size="10.5" '
            f'fill="{SECOND}">{esc(lbl)}</text>'
            f'<text x="{x0:.1f}" y="{Y + BH + 36}" font-size="13" font-weight="700" '
            f'fill="{INK}">{usdk(v)}</text>'
            f'<text x="{x0:.1f}" y="{Y + BH + 50}" font-size="9.5" fill="{MUTED}">'
            f'{v / rv * 100:.1f}% of the revised budget</text>')
    body = ''.join(b) + ''.join(lab) + (
        f'<text x="0" y="{Y - 8}" font-size="10" fill="{MUTED}">'
        f'Revised budget {usd(rv)}</text>')
    return svg(W, H, body,
               f'{meta["label"]}: what happened to the budget',
               'FY2026 at period 12 — the books are not closed, so nothing here is a '
               'surplus')


def chart_variance(db, side, meta, n=7):
    """Diverging bars: the largest overspends and underspends, on one zero line."""
    # Two queries, one per direction. Taking the top 2n by MAGNITUDE and splitting
    # them gives however many of each happen to land in that pool -- on the town side
    # only four overspends made the top fourteen, so the chart drew four red bars under
    # a subtitle promising seven. Ask for n of each, and then say how many there are.
    def top(sign, limit):
        cmp = '<' if sign < 0 else '>'
        order = 'ASC' if sign < 0 else 'DESC'
        return [dict(zip(('name', 'org', 'obj', 'dept', 'v'), r)) for r in db.execute(
            f"""SELECT a.name, a.org, a.object, a.dept, l.available
                FROM ledger_snapshot l JOIN account a USING (account_id)
                WHERE l.fy=2026 AND l.period=12 AND {meta['where']}
                  AND l.available {cmp} 0.5
                ORDER BY l.available {order} LIMIT ?""", (limit,))]

    under, over = top(1, n), top(-1, n)
    items = under + over[::-1]
    if not items:
        return None
    span = max(abs(r['v']) for r in items)

    # Geometry, laid out explicitly rather than by subtracting margins.
    #
    # The first render let the longest bar reach the category column, so COLL TUITI's
    # name and its own $434k value were printed on top of each other. Each arm now has a
    # dedicated label gutter that no bar may enter, so the value always has somewhere to
    # go however long the bar is.
    W = 640
    NAME_W, GUT, LABEL_W = 196, 8, 58
    HALF = (W - NAME_W - GUT - 2 * LABEL_W) / 2
    MID = NAME_W + GUT + LABEL_W + HALF
    ROW, TOP = 23, 58
    H = TOP + ROW * len(items) + 42
    b = [f'<line x1="{MID}" y1="{TOP - 8}" x2="{MID}" y2="{TOP + ROW * len(items)}" '
         f'stroke="{AXIS}" stroke-width="1"/>']
    for i, r in enumerate(items):
        y = TOP + i * ROW
        w = abs(r['v']) / span * HALF
        pos = r['v'] > 0
        x = MID + 1 if pos else MID - w - 1
        b.append(f'<rect x="{x:.1f}" y="{y + 3}" width="{max(w, 1.5):.1f}" height="11" '
                 f'fill="{UNDER if pos else OVER}" rx="2"/>')
        label(b, NAME_W, y + 11, r['dept'], r['org'], r['obj'], r['name'])
        lx = x + w + 6 if pos else x - 6
        b.append(f'<text x="{lx:.1f}" y="{y + 12}" font-size="10" font-weight="700" '
                 f'text-anchor="{"start" if pos else "end"}" fill="{INK}">'
                 f'{usdk(abs(r["v"]))}</text>')
    # Legend: identity is never colour alone, so each swatch carries its word.
    ly = TOP + ROW * len(items) + 22
    b.append(f'<rect x="{NAME_W}" y="{ly - 8}" width="9" height="9" fill="{OVER}" rx="2"/>'
             f'<text x="{NAME_W + 14}" y="{ly}" font-size="10" fill="{SECOND}">'
             f'Spent past the budget</text>'
             f'<rect x="{MID + 20}" y="{ly - 8}" width="9" height="9" fill="{UNDER}" rx="2"/>'
             f'<text x="{MID + 34}" y="{ly}" font-size="10" fill="{SECOND}">'
             f'Left unspent</text>')
    tot_u = db.execute(f"""SELECT SUM(available) FROM ledger_snapshot l
                           JOIN account a USING (account_id)
                           WHERE l.fy=2026 AND l.period=12 AND {meta['where']}
                             AND available > 0.5""").fetchone()[0]
    tot_o = db.execute(f"""SELECT SUM(-available) FROM ledger_snapshot l
                           JOIN account a USING (account_id)
                           WHERE l.fy=2026 AND l.period=12 AND {meta['where']}
                             AND available < -0.5""").fetchone()[0]
    n_u = db.execute(f"""SELECT COUNT(*) FROM ledger_snapshot l
                         JOIN account a USING (account_id)
                         WHERE l.fy=2026 AND l.period=12 AND {meta['where']}
                           AND available > 0.5""").fetchone()[0]
    n_o = db.execute(f"""SELECT COUNT(*) FROM ledger_snapshot l
                         JOIN account a USING (account_id)
                         WHERE l.fy=2026 AND l.period=12 AND {meta['where']}
                           AND available < -0.5""").fetchone()[0]
    return svg(W, H, ''.join(b),
               f'{meta["label"]}: the biggest misses, both directions',
               f'{usd(float(tot_u))} left across {n_u} accounts, {usd(float(tot_o))} '
               f'overspent across {n_o} — the {len(under)} and {len(over)} largest')


def chart_spend(db, side, meta, n=10):
    """Horizontal bars: where the money actually went."""
    rows = [dict(zip(('name', 'dept', 'org', 'obj', 'v'), r)) for r in db.execute(
        f"""SELECT a.name, MIN(a.dept), MIN(a.org), MIN(a.object), SUM(l.expended) e
            FROM ledger_snapshot l JOIN account a USING (account_id)
            WHERE l.fy=2026 AND l.period=12 AND {meta['where']} AND l.expended > 0
            GROUP BY a.name ORDER BY e DESC LIMIT ?""", (n,))]
    total = float(db.execute(
        f"""SELECT SUM(expended) FROM ledger_snapshot l JOIN account a USING (account_id)
            WHERE l.fy=2026 AND l.period=12 AND {meta['where']}""").fetchone()[0])
    shown = sum(r['v'] for r in rows)
    rows.append(dict(name='everything else', dept='', org='', obj='',
                     v=total - shown, rest=True))

    W, NAME_W, RIGHT = 640, 248, 92
    LEFT = NAME_W + 10
    ROW, TOP = 23, 56
    H = TOP + ROW * len(rows) + 20
    span = max(r['v'] for r in rows)
    b = []
    for i, r in enumerate(rows):
        y = TOP + i * ROW
        w = r['v'] / span * (W - LEFT - RIGHT)
        # Emphasis: the named accounts in the accent, the remainder recessive.
        col = SEQ[2] if r.get('rest') else SEQ[1]
        b.append(f'<rect x="{LEFT}" y="{y + 3}" width="{max(w, 1.5):.1f}" height="11" '
                 f'fill="{col}" rx="2"/>')
        if r.get('rest'):
            b.append(f'<text x="{NAME_W}" y="{y + 13}" font-size="9.5" text-anchor="end" '
                     f'fill="{SECOND}">everything else</text>')
        else:
            label(b, NAME_W, y + 11, r['dept'], r['org'], r['obj'], r['name'])
        b.append(f'<text x="{LEFT + w + 6:.1f}" y="{y + 12}" font-size="10" '
                 f'font-weight="700" fill="{INK}">{usdk(r["v"])}</text>')
    return svg(W, H, ''.join(b),
               f'{meta["label"]}: where the money went',
               f'The {n} largest accounts by spending, of {usd(total)} in total')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--side', choices=list(SIDES) + ['both'], default='both')
    a = ap.parse_args()
    db = sqlite3.connect(DB)
    os.makedirs(OUT, exist_ok=True)
    sides = list(SIDES) if a.side == 'both' else [a.side]
    for side in sides:
        meta = SIDES[side]
        for name, fn in (('budget', chart_budget), ('variance', chart_variance),
                         ('spend', chart_spend)):
            s = fn(db, side, meta)
            if s is None:
                continue
            path = os.path.join(OUT, f'fy26-{side}-{name}.svg')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(s)
            print('wrote %s' % os.path.relpath(path, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
