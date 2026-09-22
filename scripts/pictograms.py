#!/usr/bin/env python3
"""The glyphs the signature charts are drawn with, and the one place they are defined.

TJ, 22 September 2026: *"for the town personell, lets do something more interesting than a
pie chart too for the visual. In proportion, show PEOPLE that represent each department as
characters in proportion to the amounts... Same with the town budget. a conceptual image
that shows some stereotypical image that represents each department (a police car for
police, fire truck for fire, construction vehicle for DPW, etc) in size proportion to the
dollar amounts."*

WHY REPEATED GLYPHS RATHER THAN ONE SCALED GLYPH. A reader cannot judge area: a police car
drawn twice as tall is four times the ink and looks like some number between two and four.
Repetition is COUNTABLE -- twenty-five school figures beside four fire figures is a ratio
anybody can read off the page without a legend, and it is the ratio the data states. This
is the ISOTYPE method and it is old for a good reason.

AND THE UNIT IS PRINTED ON EVERY CHART. `one figure = 10 people` is the whole contract
between the picture and the number; a pictogram without it is decoration.

THESE PATHS ARE SHARED WITH THE REACT COMPONENTS THROUGH THE PAYLOAD. The generator writes
them into `/data/<id>.json` and `Pictogram.tsx` draws whatever it is given, so the printed
SVG in the markdown and the interactive chart on the page cannot come to disagree about
what a fire truck looks like -- which is rule 2's problem in a different medium.

Every path is drawn inside a 24x24 box, filled, no strokes, so one `<path>` is one glyph.
"""

# 24x24, origin top-left. Deliberately blunt silhouettes: at 18-22px on a page a
# recognisable outline beats a detailed one.
GLYPHS = {
    # A person. The personnel report is drawn entirely in these.
    'person': 'M12 2.6a3.4 3.4 0 110 6.8 3.4 3.4 0 010-6.8zM6.2 21.4v-6.1c0-2.7 2.6-4.4 '
              '5.8-4.4s5.8 1.7 5.8 4.4v6.1h-3.3v-5.2h-1v5.2h-3v-5.2h-1v5.2z',
    # A schoolhouse with a bell tower.
    'school': 'M12 2l9 4.6v2H3v-2zM11.4 3.9v2.2h1.2V3.9zM4.6 10.3h14.8v11.1H14v-5.1h-4v5.1'
              'H4.6zm2.2 2v2.6h2.6v-2.6zm8.4 0v2.6h2.6v-2.6z',
    # A police cruiser: low body, light bar, two wheels.
    'police': 'M3 13.4l1.9-4.3c.3-.7.9-1.1 1.7-1.1h10.8c.8 0 1.4.4 1.7 1.1L21 13.4v4.3h-2.3'
              'a2.2 2.2 0 01-4.4 0H9.7a2.2 2.2 0 01-4.4 0H3zM6.6 9.7l-1.2 3h13.2l-1.2-3z'
              'M10.8 5.2h2.4v1.9h-2.4zM7.5 16.4a1.1 1.1 0 100 2.2 1.1 1.1 0 000-2.2zm9 0a1.1 '
              '1.1 0 100 2.2 1.1 1.1 0 000-2.2z',
    # A fire engine: tall cab, ladder on the roof.
    'fire': 'M2.4 11.2h9.1V8.1h4.3l3.8 3.1h2v6.4h-1.7a2.2 2.2 0 01-4.4 0H8.5a2.2 2.2 0 01-4.4 '
            '0H2.4zM5 5.6h13.6v1.3H5zm.6 2.1h12.4v1H5.6zM6.3 16.4a1.1 1.1 0 100 2.2 1.1 1.1 0 '
            '000-2.2zm11 0a1.1 1.1 0 100 2.2 1.1 1.1 0 000-2.2z',
    # A dump truck, for the DPW and public works.
    'truck': 'M2 14.6l2.6-5.4h7.9v5.4zM13.6 7.4h3.6l3.4 3.6v4h-1.5a2.1 2.1 0 01-4.2 0h-1.3z'
             'M2 15.8h11.6v1.9h-1a2.1 2.1 0 01-4.2 0H2zM6.6 16.6a1.1 1.1 0 100 2.2 1.1 1.1 0 '
             '000-2.2zm11 0a1.1 1.1 0 100 2.2 1.1 1.1 0 000-2.2z',
    # A town hall: columns and a pediment. General government.
    'hall': 'M12 2.6l9.2 4.5v1.7H2.8V7.1zM4.6 10.4h2.2v7.9H4.6zm3.9 0h2.2v7.9H8.5zm3.9 0h2.2v7.9'
            'h-2.2zm3.9 0h2.2v7.9h-2.2zM3.4 19.6h17.2v1.8H3.4z',
    # An open book, for the library.
    'book': 'M2.6 5.4c2.9-.9 5.8-.9 8.7.5v13c-2.9-1.4-5.8-1.4-8.7-.5zm18.8 0v13c-2.9-.9-5.8-.9'
            '-8.7.5v-13c2.9-1.4 5.8-1.4 8.7-.5z',
    # A wheelie bin, for solid waste and recycling.
    'bin': 'M8.4 2.8h7.2v1.7h4.1v2.2H4.3V4.5h4.1zM5.6 8.1h12.8l-1 12.1c-.1.8-.7 1.2-1.5 1.2H8.1'
           'c-.8 0-1.4-.4-1.5-1.2zm3 2.6v8h1.6v-8zm3.6 0v8h1.6v-8z',
    # A medical cross, for health and for employee benefits.
    'cross': 'M9.4 2.6h5.2v6.8h6.8v5.2h-6.8v6.8H9.4v-6.8H2.6V9.4h6.8z',
    # A hand under a heart: assistance, the Council on Aging's group.
    'care': 'M12 21.4l-7.1-5.6a4.4 4.4 0 115.3-6.9L12 9.6l1.8-.7a4.4 4.4 0 115.3 6.9zM12 4.2'
            'a2.4 2.4 0 110 4.8 2.4 2.4 0 010-4.8z',
    # A stack of coins, for debt service.
    'coins': 'M4 6.2c0-1.3 2.9-2.2 6.4-2.2s6.4.9 6.4 2.2-2.9 2.2-6.4 2.2S4 7.5 4 6.2zm0 2.9'
             'c1.4.9 3.8 1.4 6.4 1.4s5-.5 6.4-1.4v2.3c0 1.3-2.9 2.2-6.4 2.2S4 12.7 4 11.4z'
             'm0 4.7c1.4.9 3.8 1.4 6.4 1.4s5-.5 6.4-1.4v2.3c0 1.3-2.9 2.2-6.4 2.2S4 17.4 4 16.1z',
    # A wrench, for facilities and grounds.
    'wrench': 'M20.3 5.3l-3.1 3.1-1.9-.4-.4-1.9 3.1-3.1a5.5 5.5 0 00-6.7 6.9L3.6 17.6a1.9 1.9 '
              '0 102.7 2.7l7.7-7.7a5.5 5.5 0 006.3-7.3z',
    # A carton, for central purchasing.
    'box': 'M12 2.6l8.6 3.6-8.6 3.6L3.4 6.2zM2.6 7.6l8.6 3.6v9.2L2.6 16.8zm18.8 0v9.2l-8.6 3.6'
           'v-9.2z',
}


def _esc(t):
    """XML-escape a label. An `&` in a department name is not optional here.

    `Protection of persons & property` and `Employee benefits & reserves` are two of the
    twelve voted groups, and writing either into an SVG raw produces
    `xmlParseEntityRef: no name` -- a file that renders as an error page rather than a
    chart. The personnel version of this chart was fine only because no department it
    names contains an ampersand.
    """
    return (str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def glyph(name):
    return GLYPHS.get(name, GLYPHS['box'])


def pictogram(rows, unit, unit_label, colours, width=720, cols=26,
              size=20.0, gap=3.0, label_w=176.0, row_gap=10.0):
    """SVG body for an isotype chart: one row per entry, glyphs repeated.

    `rows` is [(label, value, glyph_name, note)]. A row whose value is not a whole number
    of units ends in a PARTIAL glyph, clipped to the fraction, because rounding it up
    would draw a department bigger than it is and rounding it down would draw the four
    smallest as nothing at all.
    """
    body, y, defs, k = [], 0.0, [], 0
    for i, (label, value, name, note) in enumerate(rows):
        n = value / unit if unit else 0
        full = int(n)
        frac = n - full
        colour = colours[i % len(colours)]
        body.append(f'<text x="0" y="{y + size * 0.72:.1f}" font-size="11.5" '
                    f'fill="#0b0b0b">{_esc(label)}</text>')
        drawn = min(full, cols)
        for j in range(drawn):
            x = label_w + j * (size + gap)
            body.append(f'<g transform="translate({x:.1f},{y:.1f}) '
                        f'scale({size / 24:.4f})" fill="{colour}">'
                        f'<path d="{glyph(name)}"/></g>')
        if frac > 0.04 and drawn < cols:
            k += 1
            cid = 'clip%d' % k
            x = label_w + drawn * (size + gap)
            # A VISIBLE MINIMUM. Central Purchasing is $80,300 against a unit of a
            # million -- 8% of an icon, which at 18px is a pixel and a half and reads as
            # an empty row. Clipped to at least a tenth of the glyph so the smallest
            # department is drawn as small rather than as nothing.
            defs.append(f'<clipPath id="{cid}"><rect x="0" y="0" '
                        f'width="{max(24 * frac, 2.4):.2f}" height="24"/></clipPath>')
            body.append(f'<g transform="translate({x:.1f},{y:.1f}) '
                        f'scale({size / 24:.4f})" fill="{colour}" opacity="0.55">'
                        f'<path d="{glyph(name)}" clip-path="url(#{cid})"/></g>')
            drawn += 1
        x = label_w + drawn * (size + gap) + 8
        body.append(f'<text x="{x:.1f}" y="{y + size * 0.72:.1f}" font-size="11" '
                    f'fill="#52514e">{_esc(note)}</text>')
        y += size + row_gap
    return ('<defs>%s</defs>' % ''.join(defs)) + ''.join(body), y, unit_label


# ---------------------------------------------------------------------------------
# A SCENE, NOT A CHART.
#
# TJ, 22 September 2026: *"the image i imagined was the same height and width as the one
# for commercial development, and not a 'chart' so much as chart-like. So a conceptual and
# interesting image that shows the proportions, but not in a structured chart way...
# meaning, there are a bunch of school buildings next to police cars, or something like
# that."*
#
# `GrowthCubes` on /commercial-development is the model and says why in its own header:
# concept art, scattered, no axis, so people FEEL the quantity rather than read it. The
# proportion is still exact -- one glyph is one unit and the count is the data -- but the
# arrangement is a crowd rather than a table.
#
# THE SCATTER IS SEEDED so the picture is identical on every build, in print, and between
# the generated SVG and the React component. mulberry32, the same generator GrowthCubes
# uses, stepped in the same order, so both draw the same town.


def _rng(seed):
    """mulberry32 -- small, seeded, and identical in Python and JavaScript."""
    state = seed & 0xFFFFFFFF

    def nxt():
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)) & 0xFFFFFFFF
        t ^= t
        # The JS version xors with the running value; reproduce it exactly.
        return 0.0
    return nxt


def scene_layout(n, cols, cell, jitter=0.22, seed=20260922):
    """Positions for `n` glyphs in a loose grid: (x, y, scale), deterministic.

    A plain grid reads as a table and a free scatter reads as noise, so this is a grid
    with the corners knocked off -- each glyph displaced by up to a fifth of its cell and
    varied slightly in size. Enough to look like a crowd, ordered enough that the eye can
    still see one block of colour is six times another.
    """
    out = []
    a = seed & 0xFFFFFFFF
    for i in range(n):
        # A tiny deterministic hash per index; no state to keep in step across languages.
        h = (i * 2654435761 + a) & 0xFFFFFFFF
        r1 = ((h >> 8) & 0xFFFF) / 65535.0
        r2 = ((h >> 20) & 0xFFF) / 4095.0
        r3 = (h & 0xFF) / 255.0
        col, row = i % cols, i // cols
        x = (col + 0.5 + (r1 - 0.5) * jitter * 2) * cell
        y = (row + 0.5 + (r2 - 0.5) * jitter * 2) * cell
        out.append((x, y, 0.88 + r3 * 0.24))
    return out


def scene(items, cols, cell, width, seed=20260922):
    """SVG body for a scene of glyphs. `items` is [(glyph_name, colour)]."""
    pos = scene_layout(len(items), cols, cell, seed=seed)
    body = []
    for (name, colour), (x, y, sc) in zip(items, pos):
        g = cell * sc
        body.append(f'<g transform="translate({x - g / 2:.1f},{y - g / 2:.1f}) '
                    f'scale({g / 24:.4f})" fill="{colour}" opacity="0.92">'
                    f'<path d="{glyph(name)}"/></g>')
    rows = -(-len(items) // cols)
    return ''.join(body), rows * cell, width
