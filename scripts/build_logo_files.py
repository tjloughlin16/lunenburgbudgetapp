#!/usr/bin/env python3
"""Build the Lunenburg Budget Project logo files: the square mark and the full lockups.

    python3 scripts/build_logo_files.py --font path/to/Inter-Bold.ttf

Writes sources/data/brand/logo/. (The Facebook cover and the favicon options are
scripts/build_brand_assets.py; this is the plain logo kit.) The mark is the one in fy28/public/favicon.svg
-- "The Margin", an L drawn as a page margin with a highlighter stroke and two ruled lines --
redrawn here from the same coordinates so the favicon and the logo files cannot drift apart
by hand-editing. The wordmark is ink, all of it, like the Facebook cover's. NOT the brand blue
the site header puts on "Lunenburg": that is the district's colour, and sources/data/brand/
README.md records why the mark never uses it -- a logo travels alone, and alone, the
district's blue on the town's name reads as the district talking.

The text is converted to OUTLINES (paths), so the SVGs need no font installed and render
identically everywhere. The face is Inter Bold (SIL Open Font Licence), chosen because the
site itself uses the system UI face, which differs per device and whose Apple and Microsoft
versions may not be embedded in a logo.

Needs: fonttools, uharfbuzz, resvg-py, pillow (not in the repo's requirements; a venv will do).
"""
import argparse
import io
from pathlib import Path

import resvg_py
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / 'sources' / 'data' / 'brand' / 'logo'

# Colours: favicon.svg. Dark is the same three inverted, the ochre lifted a step to hold
# its contrast on ink.
THEMES = {
    'light': dict(tile='#fbf8f1', ink='#181713', gold='#c9911c'),
    'dark':  dict(tile='#181713', ink='#fbf8f1', gold='#d9a43a'),
}

MARK_PNG = [16, 32, 48, 64, 128, 180, 192, 256, 512, 1024]
LOCKUP_PNG_HEIGHTS = [64, 128, 256, 512]


def mark_shapes(t, tile=True):
    """The mark on a 32x32 grid -- coordinates copied from favicon.svg."""
    s = []
    if tile:
        s.append(f'<rect width="32" height="32" rx="7" fill="{t["tile"]}"/>')
    s += [
        f'<rect x="8.5" y="5" width="4.6" height="17" fill="{t["ink"]}"/>',
        f'<rect x="8.5" y="22" width="13.5" height="4.6" fill="{t["ink"]}"/>',
        f'<rect x="15.6" y="6.6" width="9.5" height="3.4" fill="{t["gold"]}"/>',
        f'<rect x="15.6" y="12.4" width="7" height="3.4" fill="{t["ink"]}" opacity=".22"/>',
        f'<rect x="15.6" y="17.2" width="9.5" height="3.4" fill="{t["ink"]}" opacity=".22"/>',
    ]
    return '\n  '.join(s)


class Typesetter:
    def __init__(self, font_path):
        self.tt = TTFont(font_path)
        self.gs = self.tt.getGlyphSet()
        self.upem = self.tt['head'].unitsPerEm
        self.cap = self.tt['OS/2'].sCapHeight
        blob = hb.Blob.from_file_path(str(font_path))
        self.hbfont = hb.Font(hb.Face(blob))
        self.order = self.tt.getGlyphOrder()
        cmap = self.tt.getBestCmap()
        # Deepest descender in the name ("g", "j"), in font units, so a frame clears it.
        self.desc = -min(self.tt['glyf'][cmap[ord(c)]].yMin for c in 'gj')

    def path(self, text, size, x0, baseline, tracking=-0.01):
        """SVG path data for `text` at `size`, kerned by harfbuzz; returns (d, advance)."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf, {'kern': True, 'liga': True})
        k = size / self.upem
        pen = SVGPathPen(self.gs)
        x = 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            name = self.order[info.codepoint]
            tp = TransformPen(pen, (k, 0, 0, -k, x0 + (x + pos.x_offset) * k,
                                    baseline - pos.y_offset * k))
            self.gs[name].draw(tp)
            x += pos.x_advance + tracking * self.upem
        return pen.getCommands(), (x - tracking * self.upem) * k


def svg(w, h, body, title='The Lunenburg Budget Project'):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" '
            f'width="{w:g}" height="{h:g}">\n  <title>{title}</title>\n  {body}\n</svg>\n')


def r(v):
    return round(v, 2)


# The glyph's own extent on the 32-grid (favicon.svg): x 8.5-25.1, y 5-26.6. Lockups use
# the BARE glyph, not the tile -- a tile inside a lockup doubles the inset on the left and
# drops a cream square onto whatever surface the transparent version is placed on.
GX0, GX1, GY0, GY1 = 8.5, 25.1, 5.0, 26.6
GH = GY1 - GY0
GAP = 0.42 * GH            # glyph to name
PAD = 0.55 * GH            # the even inset around everything, on the -bg versions


def _lockup(t, bg, paths, text_right, bottom=GY1):
    x0, y0 = GX0, GY0
    w, h = text_right - GX0, max(GY1, bottom) - GY0
    if bg:
        x0, y0, w, h = x0 - PAD, y0 - PAD, w + 2 * PAD, h + 2 * PAD
    body = []
    if bg:
        body.append(f'<rect x="{r(x0)}" y="{r(y0)}" width="{r(w)}" height="{r(h)}" fill="{t["tile"]}"/>')
    body.append(mark_shapes(t, tile=False))
    body += [f'<path fill="{t["ink"]}" d="{d}"/>' for d in paths]
    out = svg(r(w), r(h), '\n  '.join(body))
    return out.replace('viewBox="0 0 ', f'viewBox="{r(x0)} {r(y0)} ', 1)


def lockup_horizontal(ts, t, bg):
    """The L, then 'Lunenburg Budget Project' on one line; cap height = 52% of the L."""
    size = GH * 0.52 * ts.upem / ts.cap
    x = GX1 + GAP
    base = (GY0 + GY1) / 2 + (size * ts.cap / ts.upem) / 2   # caps centred on the L
    d, w = ts.path('Lunenburg Budget Project', size, x, base)
    return _lockup(t, bg, [d], x + w, base + ts.desc * size / ts.upem)


def lockup_stacked(ts, t, bg):
    """The L, then 'Lunenburg' over 'Budget Project': first cap top on the L's top,
    second baseline on the L's foot."""
    capw = GH * 0.36
    size = capw * ts.upem / ts.cap
    x = GX1 + GAP
    d1, w1 = ts.path('Lunenburg', size, x, GY0 + capw)
    d2, w2 = ts.path('Budget Project', size, x, GY1)
    return _lockup(t, bg, [d1, d2], x + max(w1, w2), GY1 + ts.desc * size / ts.upem)


def png(svg_text, height):
    import re
    m = re.search(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"', svg_text)
    w, h = float(m.group(1)), float(m.group(2))
    width = round(w * height / h)
    data = resvg_py.svg_to_bytes(svg_string=svg_text, width=width, height=height)
    return bytes(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--font', required=True, help='Inter-Bold.ttf')
    a = ap.parse_args()
    ts = Typesetter(a.font)
    (OUT / 'png').mkdir(parents=True, exist_ok=True)
    written = []

    def put(name, text):
        (OUT / name).write_text(text)
        written.append(name)

    def put_png(name, data):
        (OUT / 'png' / name).write_bytes(data)
        written.append('png/' + name)

    for theme, t in THEMES.items():
        sfx = '' if theme == 'light' else '-dark'
        m = svg(32, 32, mark_shapes(t))
        put(f'mark{sfx}.svg', m)
        for px in MARK_PNG:
            put_png(f'mark{sfx}-{px}.png', png(m, px))
        # The glyph without its tile, for placing on a surface of your own.
        g = svg(32, 32, mark_shapes(t, tile=False))
        put(f'mark-notile{sfx}.svg', g)
        for px in (64, 256, 1024):
            put_png(f'mark-notile{sfx}-{px}.png', png(g, px))

        for kind, fn in (('horizontal', lockup_horizontal), ('stacked', lockup_stacked)):
            for bg in (False, True):
                name = f'logo-{kind}{sfx}{"-bg" if bg else ""}'
                s = fn(ts, t, bg)
                put(name + '.svg', s)
                for hpx in LOCKUP_PNG_HEIGHTS:
                    put_png(f'{name}-{hpx}h.png', png(s, hpx))

    # favicon.ico: 16/32/48 in one file, for anything that will not take an SVG.
    im = Image.open(io.BytesIO(png(svg(32, 32, mark_shapes(THEMES['light'])), 256)))
    im.save(OUT / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
    written.append('favicon.ico')
    print(f'{len(written)} files -> {OUT}')


if __name__ == '__main__':
    main()
