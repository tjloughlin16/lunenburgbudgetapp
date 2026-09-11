"""The Facebook group cover and the site favicon — one idea, two sizes, three options.

    python3 scripts/build_brand_assets.py

Writes into `notes/generated/brand/`:

    banner-<option>.png        1640x856, the Facebook group cover
    favicon-<option>.svg       the same idea at 32 pixels
    favicons.png               all three at 32, 16 and magnified, light and dark
    index.html                 all of it side by side, at both sizes, light and dark

Nothing here is published. This is a DRAFT for a decision; a chosen option gets moved
into `fy28/public/` deliberately, in its own commit.

WHY IT IS GENERATED FROM HTML RATHER THAN DRAWN

Same reason every other artefact here is generated: a banner drawn once in a design tool
is a file nobody can change without the tool, and it drifts from the site's tokens the
first time a colour moves. Chrome is already a dependency of this repo
(`scripts/build_analysis_pdf.py` prints the analyses with it), so the cover is HTML and a
headless screenshot, and the favicon is SVG written out by hand.

THE DIMENSIONS, AND WHERE THEY CAME FROM

1640 x 856, a 1.91:1 aspect ratio, with the content kept inside the centre 1440 x 560.
Checked on 11 September 2026 rather than remembered -- Facebook changes these -- against
snappa.com/blog/facebook-group-cover-photo-size/ and three other 2026 size guides, which
agree on 1640 x 856 for a GROUP cover. (A PAGE cover is 820 x 312 and is a different
thing; one source quotes 1640 x 922 for groups, which is the older figure.) The top and
bottom of the image are cropped on mobile and the group's name and member count are laid
over the bottom, so nothing that matters sits outside the safe area. The preview page
draws that crop over each banner in CSS rather than rendering a second PNG of it -- one
Chrome launch per banner instead of two, which matters on a loaded machine.

THE COLOUR DECISION, WHICH IS THE ONE THAT COULD GO WRONG

`--brand: #12428f` in `fy28/src/index.css` is the Blue Knights' royal -- the SCHOOL
DISTRICT'S colour. On the site it sits surrounded by pages that say who wrote them and
reads as affection for the town. Alone on a Facebook banner, seen by somebody scrolling,
a town name set in the district's own blue is indistinguishable from a communication FROM
the district, and this project's only authority is that its figures are checkable. It
must not borrow an authority it does not have.

So the decision here is deliberate and it is NOT inheritance: the brand blue appears in
exactly ONE of the three options, as the water in a landscape, at a few percent of the
area and never behind or near the wordmark. Two of the three do not use it at all. If the
chosen option is A, the blue is a lake; if it is B or C, the blue does not ship.

Nothing here carries a figure, for the reason rule 2 exists in its sharpest form: a banner
cannot be corrected, it is seen more than anything else this project publishes, and a
number on it is stale the day a generator runs. Each option says what the project IS.
"""
import argparse
import os
import subprocess
import tempfile
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'notes', 'generated', 'brand')

W, H = 1640, 856
SAFE_W, SAFE_H = 1440, 560            # the centre area that survives the mobile crop
SAFE_X, SAFE_Y = (W - SAFE_W) // 2, (H - SAFE_H) // 2

CHROME = next((p for p in (
    os.environ.get('CHROME'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
) if p and os.path.exists(p)), None)

# The wordmark and the plain description, identical across all three options so that the
# choice being made is the visual one. The description is not a disclaimer: "independent"
# and "published documents" are simply true, and a plain true sentence does the work of a
# disclaimer without the defensive tone. The same sentence already opens the site's own
# meta description.
NAME_THE = 'The'
NAME = 'Lunenburg Budget Project'
BLURB = 'An independent project reading the town and school budgets, document by document'
ADDR = 'lunenburgbudgetproject.org'

SANS = ('ui-sans-serif, system-ui, -apple-system, "Helvetica Neue", '
        '"Segoe UI", Roboto, sans-serif')
SERIF = 'Georgia, "Iowan Old Style", "Times New Roman", serif'


# ---------------------------------------------------------------- banners

def banner_a():
    """A. THE RIDGE — the town seen whole, at the end of the day.

    Two ridge lines and a strip of water under a late-afternoon sky. Says: this is a place
    somebody lives in, looked at calmly and from a distance. The ONLY option that uses the
    brand blue, and it uses it as WATER — one lake, under 2% of the area, low in the frame
    and nowhere near the wordmark. Two earlier attempts crossed the whole frame: a band and
    then a ribbon, and both read as a stripe on a flag rather than as water. A CONTAINED
    shape with the near ridge cutting across its foot is what reads as a lake.
    """
    sky_hi, sky_lo = '#f8f1e3', '#ead9bb'
    far, mid, near = '#9aa79c', '#5f7367', '#33463d'
    water, ink, soft = '#12428f', '#1b1a17', '#4a4438'
    return f"""
<style>
  body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden;
          background:linear-gradient(180deg,{sky_hi} 0%,{sky_hi} 40%,{sky_lo} 84%);
          font-family:{SANS}; position:relative; }}
  .sun {{ position:absolute; right:196px; top:132px; width:118px; height:118px;
          border-radius:50%; background:#f2dfb6; opacity:.9; }}
  svg {{ position:absolute; left:0; bottom:0; display:block; }}
  .txt {{ position:absolute; left:132px; top:186px; color:{ink}; }}
  .the {{ font-size:30px; letter-spacing:.30em; text-transform:uppercase;
          color:{soft}; margin:0 0 16px 3px; font-weight:600; }}
  h1 {{ font-size:100px; line-height:1.0; letter-spacing:-.028em; margin:0;
        font-weight:700; }}
  .blurb {{ font-size:30px; line-height:1.45; color:{soft}; margin:28px 0 0;
            max-width:820px; font-weight:400; }}
  .addr {{ font-size:26px; letter-spacing:.055em; color:{ink}; margin:24px 0 0;
           font-weight:600; }}
</style>
<div class="sun"></div>
<svg width="{W}" height="352" viewBox="0 0 1640 300" preserveAspectRatio="none">
  <path fill="{far}" d="M0 96 C 180 40, 380 52, 540 100 C 720 154, 900 46, 1100 76
                        C 1320 110, 1470 58, 1640 92 L1640 300 L0 300 Z"/>
  <path fill="{mid}" d="M0 160 C 220 112, 430 140, 640 170 C 900 208, 1120 142, 1360 158
                        C 1480 166, 1560 176, 1640 168 L1640 300 L0 300 Z"/>
  <path fill="{water}" d="M132 212 C 280 192, 520 190, 676 202 C 748 208, 792 214, 812 220
                          C 752 234, 560 242, 372 238 C 248 235, 170 226, 132 212 Z"/>
  <path fill="{near}" d="M0 236 C 300 226, 560 246, 900 238 C 1200 231, 1420 248, 1640 236
                         L1640 300 L0 300 Z"/>
</svg>
<div class="txt">
  <p class="the">{NAME_THE}</p>
  <h1>{NAME}</h1>
  <p class="blurb">{BLURB}</p>
  <p class="addr">{ADDR}</p>
</div>
"""


def banner_b():
    """B. THE ORCHARD — a neighbour's project, in harvest colours.

    An orchard row on a slope. Lunenburg is orchard country and the imagery is
    agricultural rather than civic, which is the point: nothing in a barn-red apple
    resembles a letterhead. NO BLUE AT ALL. The warmest and least institutional of the
    three, and the one most likely to be read as friendly rather than as a notice.
    """
    paper, ink, soft = '#fbf3e4', '#2a2118', '#5c4b38'
    leaf, leaf2, trunk, fruit, ground = '#4b6b3a', '#628049', '#6b4a2c', '#b5442e', '#cbb489'
    trees = []
    for i, (x, s) in enumerate([(96, .62), (330, .56), (556, .66), (790, .54),
                                (1022, .62), (1252, .58), (1486, .64), (1636, .55)]):
        c = leaf if i % 2 == 0 else leaf2
        trees.append(
            f'<g transform="translate({x},788) scale({s})">'
            f'<rect x="-11" y="-78" width="22" height="80" fill="{trunk}"/>'
            f'<circle cx="0" cy="-120" r="78" fill="{c}"/>'
            f'<circle cx="-46" cy="-86" r="44" fill="{c}"/>'
            f'<circle cx="46" cy="-86" r="44" fill="{c}"/>'
            f'<circle cx="-30" cy="-130" r="11" fill="{fruit}"/>'
            f'<circle cx="34" cy="-108" r="11" fill="{fruit}"/>'
            f'<circle cx="6" cy="-160" r="11" fill="{fruit}"/></g>')
    return f"""
<style>
  body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{paper};
          font-family:{SERIF}; position:relative; }}
  svg {{ position:absolute; left:0; top:0; }}
  .txt {{ position:absolute; left:132px; top:196px; color:{ink}; }}
  .the {{ font-family:{SANS}; font-size:29px; letter-spacing:.30em;
          text-transform:uppercase; color:{fruit}; margin:0 0 18px 4px;
          font-weight:700; }}
  h1 {{ font-size:106px; line-height:1.02; letter-spacing:-.022em; margin:0;
        font-weight:700; }}
  .blurb {{ font-family:{SANS}; font-size:30px; line-height:1.45; color:{soft};
            margin:32px 0 0; max-width:900px; }}
  .addr {{ font-family:{SANS}; font-size:27px; letter-spacing:.055em; color:{ink};
           margin:26px 0 0; font-weight:700; }}
</style>
<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <circle cx="1404" cy="166" r="96" fill="#f0dcb4"/>
  <path fill="{ground}" opacity=".5"
        d="M0 742 C 320 708, 700 732, 1040 718 C 1320 706, 1470 724, 1640 712 L1640 856 L0 856 Z"/>
  {''.join(trees)}
  <path fill="#b9a077"
        d="M0 788 C 360 766, 760 786, 1120 774 C 1380 766, 1500 780, 1640 772 L1640 856 L0 856 Z"/>
</svg>
<div class="txt">
  <p class="the">{NAME_THE}</p>
  <h1>{NAME}</h1>
  <p class="blurb">{BLURB}</p>
  <p class="addr">{ADDR}</p>
</div>
"""


def banner_c():
    """C. THE MARGIN — a page, not a poster.

    Almost entirely typographic: paper, a ruled grid, a gutter, a wordmark, one ochre
    highlighter mark, and a pine treeline along the bottom edge so there is a sense of
    place without a picture of one. Says: this is reading, done in public. It is the
    option that argues least, which is either its whole virtue or too quiet for Facebook
    — that is the judgement to make.

    NO BLUE. The accent is a highlighter ochre, which means "somebody marked this line"
    and is nobody's livery.
    """
    paper, ink, soft, mark = '#fbf8f1', '#181713', '#565044', '#c9911c'
    # The treeline is generated so it spans the full frame. Typed by hand it ran out of
    # coordinates a third of the way across and the remainder read as a saw blade. The
    # crowns then had to be widened twice: narrow triangles at this opacity read as GRASS,
    # not as a stand of pines, and the fix is width against height rather than more of
    # them.
    import random

    def row(seed, lo, hi, base, overlap):
        rnd = random.Random(seed)
        pts, x = [], -30
        while x < W + 70:
            w = rnd.randint(88, 164)
            pts.append(f'L{x + w / 2:.0f} {base - rnd.randint(lo, hi)} L{x + w:.0f} {base}')
            x += w - rnd.randint(overlap, overlap + 22)
        return 'M-30 %d ' % base + ' '.join(pts) + f' L{W + 70} {base} Z'

    back = row(3, 74, 132, 162, 34)      # farther, taller, paler
    front = row(11, 48, 100, 172, 26)
    return f"""
<style>
  body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{paper};
          font-family:{SERIF}; position:relative; color:{ink}; }}
  .rules {{ position:absolute; inset:0;
            background:repeating-linear-gradient(180deg,
              transparent 0 51px, rgba(24,23,19,.05) 51px 52px); }}
  .gutter {{ position:absolute; left:196px; top:0; bottom:0; width:2px;
             background:rgba(181,58,40,.22); }}
  .txt {{ position:absolute; left:250px; top:240px; }}
  .the {{ font-family:{SANS}; font-size:27px; letter-spacing:.32em;
          text-transform:uppercase; color:{soft}; margin:0 0 20px 3px; font-weight:600; }}
  h1 {{ font-size:108px; line-height:1.0; letter-spacing:-.026em; margin:0;
        font-weight:400; }}
  .hl {{ display:inline-block; height:19px; width:452px; background:{mark};
         opacity:.5; margin:-9px 0 0 3px; }}
  .blurb {{ font-family:{SANS}; font-size:30px; line-height:1.45; color:{soft};
            margin:32px 0 0; max-width:880px; }}
  .addr {{ font-family:{SANS}; font-size:27px; letter-spacing:.055em; margin:26px 0 0;
           font-weight:600; }}
  svg {{ position:absolute; left:0; bottom:0; }}
</style>
<div class="rules"></div>
<div class="gutter"></div>
<div class="txt">
  <p class="the">{NAME_THE}</p>
  <h1>{NAME}</h1>
  <div class="hl"></div>
  <p class="blurb">{BLURB}</p>
  <p class="addr">{ADDR}</p>
</div>
<svg width="{W}" height="172" viewBox="0 0 {W} 172">
  <path fill="{ink}" opacity=".10" d="{back}"/>
  <path fill="{ink}" opacity=".19" d="{front}"/>
</svg>
"""


# ---------------------------------------------------------------- favicons
#
# Hand-written SVG on a 32 grid, because 32 pixels is where the idea either survives or
# does not and a shrunk banner never survives it. Every one is a full-bleed rounded tile
# rather than a floating glyph: a tab strip is busy and a tile holds its edge. Deliberately
# NOT a circle with a ring -- a ring with something inside it is what a town seal looks
# like, and looking official is the one failure mode that matters here.

FAVICONS = {
    'a': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <title>The Lunenburg Budget Project</title>
  <rect width="32" height="32" rx="7" fill="#f6eeda"/>
  <circle cx="23.5" cy="9" r="4" fill="#eedcb2"/>
  <path fill="#9aa79c" d="M0 24 V19 C5 12 11 13 16 19 C20 23.5 26 15 32 18 V24 Z"/>
  <path fill="#5f7367" d="M0 25 C5 20 10 21 14 24 C18 27 24 21 32 23 V25 Z"/>
  <rect y="24.8" width="32" height="2.6" fill="#12428f"/>
  <path fill="#33463d" d="M0 27.4 H32 V32 H0 Z"/>
</svg>
""",
    'b': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <title>The Lunenburg Budget Project</title>
  <rect width="32" height="32" rx="7" fill="#fbf0dc"/>
  <path fill="#cbb489" d="M0 25 C8 23.4 14 25.4 22 24.2 C26 23.6 29 24.4 32 23.8 V32 H0 Z"/>
  <rect x="14.6" y="17" width="2.8" height="9" fill="#6b4a2c"/>
  <circle cx="16" cy="13" r="9" fill="#4b6b3a"/>
  <circle cx="9.4" cy="17.4" r="4.6" fill="#4b6b3a"/>
  <circle cx="22.6" cy="17.4" r="4.6" fill="#4b6b3a"/>
  <circle cx="12.2" cy="11.6" r="2.1" fill="#b5442e"/>
  <circle cx="20.2" cy="15.4" r="2.1" fill="#b5442e"/>
  <circle cx="18.4" cy="8.6" r="2.1" fill="#b5442e"/>
</svg>
""",
    'c': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <title>The Lunenburg Budget Project</title>
  <rect width="32" height="32" rx="7" fill="#fbf8f1"/>
  <rect x="8.5" y="5" width="4.6" height="17" fill="#181713"/>
  <rect x="8.5" y="22" width="13.5" height="4.6" fill="#181713"/>
  <rect x="15.6" y="6.6" width="9.5" height="3.4" fill="#c9911c"/>
  <rect x="15.6" y="12.4" width="7" height="3.4" fill="#181713" opacity=".22"/>
  <rect x="15.6" y="17.2" width="9.5" height="3.4" fill="#181713" opacity=".22"/>
</svg>
""",
}

BANNERS = {'a': banner_a, 'b': banner_b, 'c': banner_c}

TITLES = {
    'a': ('The Ridge', 'The town seen whole, at the end of the day. Landscape, calm, '
                       'looked at from a distance. The ONLY option that uses the brand '
                       'blue — as one small lake, low in the frame and far from the '
                       'wordmark.'),
    'b': ('The Orchard', 'A neighbour, in harvest colours. Agricultural rather than '
                         'civic: nothing in a barn-red apple resembles a letterhead. '
                         'No blue at all. The warmest and the least institutional.'),
    'c': ('The Margin', 'A page, not a poster. Paper, a wordmark, one marked line, and a '
                        'hairline treeline. Says the work is reading, done in public. '
                        'No blue; the accent is a highlighter ochre.'),
}


def shoot(html, path, w, h):
    """One headless Chrome, a fresh profile, a hard timeout.

    The timeout is not defensive padding. A run hung here for three minutes while another
    agent's Chrome held the machine, and a build that hangs forever is worse than one that
    fails: nothing downstream can tell slow from stuck.
    """
    if not CHROME:
        print('no Chrome found; skipping ' + os.path.basename(path))
        return
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, 'b.html')
        with open(src, 'w', encoding='utf-8') as fh:
            fh.write('<!doctype html><meta charset="utf-8">' + html)
        try:
            subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                            '--no-first-run', '--no-default-browser-check',
                            '--force-device-scale-factor=1',
                            '--user-data-dir=' + os.path.join(td, 'u'),
                            '--window-size=%d,%d' % (w, h),
                            '--virtual-time-budget=1500',
                            '--screenshot=' + path, 'file://' + src],
                           check=True, capture_output=True, timeout=240)
        except subprocess.TimeoutExpired:
            # Chrome often WRITES the screenshot and then fails to exit, so a timeout here
            # does not mean the file is missing. Say which it was rather than assuming.
            if os.path.exists(path):
                print('%s written, but Chrome did not exit; killed it'
                      % os.path.relpath(path, ROOT))
            else:
                print('TIMED OUT rendering %s; rerun when the machine is quieter'
                      % os.path.basename(path))
            return
    print('wrote %s  (%.0f KB)' % (os.path.relpath(path, ROOT),
                                   os.path.getsize(path) / 1024))


def favicon_sheet():
    """All three marks at the size that decides them.

    32 pixels is where a mark either survives or does not, and no amount of looking at a
    banner tells you which. The sheet also shows each one magnified 8x with the pixel grid
    OFF -- the magnification is for judging the silhouette, not the rendering.
    """
    # The SVGs are inlined as data URIs rather than referenced by filename. The sheet is
    # rendered from a temp directory, so a relative src resolves to nothing and the first
    # version of this came back as three columns of broken-image icons.
    cols = []
    for k in ('a', 'b', 'c'):
        uri = 'data:image/svg+xml,' + quote(FAVICONS[k])
        cols.append(f"""
<div class="col">
  <div class="cap">{k.upper()}</div>
  <div class="mag"><img src="{uri}" width="256" height="256"></div>
  <div class="strip light"><img src="{uri}" width="32" height="32">
    <img src="{uri}" width="16" height="16"></div>
  <div class="strip dark"><img src="{uri}" width="32" height="32">
    <img src="{uri}" width="16" height="16"></div>
</div>""")
    html = f"""<style>
  body {{ margin:0; width:900px; height:470px; background:#f4f3ef; display:flex;
          gap:26px; padding:28px; box-sizing:border-box;
          font:13px ui-sans-serif, system-ui, sans-serif; color:#4a4840; }}
  .col {{ flex:1; display:flex; flex-direction:column; gap:12px; align-items:center; }}
  .cap {{ font-weight:700; color:#14140f; }}
  .mag img {{ image-rendering:auto; border-radius:14px; }}
  .strip {{ display:flex; gap:14px; align-items:center; padding:12px 18px;
            border-radius:9px; width:100%; box-sizing:border-box;
            justify-content:center; }}
  .strip.light {{ background:#fcfcfb; border:1px solid #e0dfd7; }}
  .strip.dark {{ background:#17171a; }}
</style>{''.join(cols)}"""
    shoot(html, os.path.join(OUT, 'favicons.png'), 900, 470)


def render(key):
    shoot(BANNERS[key](), os.path.join(OUT, 'banner-%s.png' % key), W, H)


def preview():
    """One local page showing all of it. No build, no server — open the file."""
    blocks = []
    for k in ('a', 'b', 'c'):
        title, why = TITLES[k]
        blocks.append(f"""
<section>
  <h2><span class="k">{k.upper()}</span> {title}</h2>
  <p class="why">{why}</p>
  <div class="shot"><img class="banner" src="banner-{k}.png" alt=""></div>
  <div class="row">
    <div class="tiles">
      <div class="tile light">
        <img src="favicon-{k}.svg" width="32" height="32" alt="">
        <img src="favicon-{k}.svg" width="16" height="16" alt="">
        <span>32 / 16 on light</span>
      </div>
      <div class="tile dark">
        <img src="favicon-{k}.svg" width="32" height="32" alt="">
        <img src="favicon-{k}.svg" width="16" height="16" alt="">
        <span>32 / 16 on dark</span>
      </div>
      <div class="tabstrip">
        <div class="tab"><img src="favicon-{k}.svg" width="16" height="16" alt="">
          <span>The Lunenburg Budget Project</span></div>
        <div class="tab off"><img src="favicon-{k}.svg" width="16" height="16" alt="">
          <span>Lunenburg, MA</span></div>
      </div>
    </div>
    <figure class="crop">
      <div class="shot cropped"><img class="banner" src="banner-{k}.png" alt=""></div>
      <figcaption>Red is what the mobile crop and the group-name overlay can take.
        Everything that matters sits inside the dashed box.</figcaption>
    </figure>
  </div>
</section>""")
    html = f"""<!doctype html>
<meta charset="utf-8">
<title>Brand options — The Lunenburg Budget Project</title>
<style>
  body {{ margin:0; padding:40px 44px 80px; background:#f4f3ef; color:#14140f;
          font:15px/1.6 ui-sans-serif, system-ui, -apple-system, sans-serif; }}
  h1 {{ font-size:27px; margin:0 0 6px; letter-spacing:-.01em; }}
  .lede {{ color:#5b594f; margin:0 0 34px; max-width:74ch; }}
  section {{ background:#fff; border:1px solid #e0dfd7; border-radius:14px;
             padding:22px 24px 26px; margin:0 0 30px; }}
  h2 {{ font-size:21px; margin:0 0 4px; }}
  .k {{ display:inline-block; background:#14140f; color:#fff; border-radius:6px;
        padding:1px 9px; margin-right:8px; font-size:15px; vertical-align:2px; }}
  .why {{ color:#5b594f; margin:0 0 18px; max-width:88ch; }}
  .shot {{ position:relative; border-radius:8px; overflow:hidden;
           border:1px solid #e0dfd7; }}
  img.banner {{ width:100%; height:auto; display:block; }}
  /* The mobile crop, drawn over the same PNG rather than rendered as a second one.
     Percentages of {W}x{H}: the safe area is the centre {SAFE_W}x{SAFE_H}. */
  .cropped::after {{ content:""; position:absolute; inset:0; pointer-events:none;
    background:
      linear-gradient(rgba(200,20,20,.30) 0 0) 0 0 / 100% {SAFE_Y/H:.4%} no-repeat,
      linear-gradient(rgba(200,20,20,.30) 0 0) 0 100% / 100% {SAFE_Y/H:.4%} no-repeat,
      linear-gradient(rgba(200,20,20,.18) 0 0) 0 0 / {SAFE_X/W:.4%} 100% no-repeat,
      linear-gradient(rgba(200,20,20,.18) 0 0) 100% 0 / {SAFE_X/W:.4%} 100% no-repeat; }}
  .cropped::before {{ content:""; position:absolute; z-index:1; pointer-events:none;
    left:{SAFE_X/W:.4%}; top:{SAFE_Y/H:.4%}; right:{SAFE_X/W:.4%}; bottom:{SAFE_Y/H:.4%};
    outline:2px dashed rgba(200,20,20,.9); }}
  .row {{ display:flex; gap:26px; align-items:flex-start; margin-top:20px;
          flex-wrap:wrap; }}
  .tiles {{ display:flex; flex-direction:column; gap:12px; }}
  .tile {{ display:flex; align-items:center; gap:12px; padding:12px 16px;
           border-radius:9px; font-size:13px; }}
  .tile.light {{ background:#fcfcfb; border:1px solid #e0dfd7; color:#52514e; }}
  .tile.dark {{ background:#17171a; color:#a9a8a2; }}
  .tabstrip {{ background:#dedcd6; border-radius:9px; padding:7px 7px 0;
               display:flex; gap:4px; }}
  .tab {{ background:#fcfcfb; border-radius:7px 7px 0 0; padding:7px 13px;
          display:flex; align-items:center; gap:8px; font-size:12px; color:#3a3a36;
          max-width:210px; }}
  .tab.off {{ background:#cfcdc6; color:#6a6962; }}
  .tab span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  figure.crop {{ margin:0; flex:1 1 420px; min-width:340px; }}
  figcaption {{ font-size:12.5px; color:#6d6b61; margin-top:7px; }}
  img.sheet {{ width:100%; max-width:900px; height:auto; display:block; }}
  footer {{ color:#5b594f; max-width:78ch; font-size:14px; }}
  code {{ font:13px ui-monospace, Menlo, monospace; background:#eceae3;
          padding:1px 4px; border-radius:3px; }}
</style>
<h1>Three options for the group cover and the favicon</h1>
<p class="lede">One idea in two sizes, three times over. Generated by
  <code>scripts/build_brand_assets.py</code>. Nothing here is published — a chosen option
  gets moved into <code>fy28/public/</code> deliberately. The cover is
  {W}&thinsp;&times;&thinsp;{H} with everything that matters inside the centre
  {SAFE_W}&thinsp;&times;&thinsp;{SAFE_H}.</p>
{''.join(blocks)}
<section>
  <h2>All three at the size that decides them</h2>
  <p class="why">32 pixels is where a mark survives or does not. Magnified 8&times; for the
    silhouette, then actual size on light and on dark.</p>
  <img class="sheet" src="favicons.png" alt="">
</section>
<footer>
  <p><b>On the brand blue.</b> <code>--brand: #12428f</code> is the Blue Knights' royal —
  the school district's colour. On the site it reads as affection for the town; alone on
  a Facebook banner it reads as the district talking, and this project's only authority is
  that its figures are checkable. It appears in option A only, as the lake, and in neither
  of the others.</p>
  <p><b>No figure appears on any of them</b>, deliberately: a banner cannot be corrected
  and it is seen more than anything else here.</p>
  <p><b>The live favicon today is not the purple file.</b>
  <code>fy28/index.html</code> carries an inline <code>rel="icon"</code> data URI of the
  🏫 school-building emoji, so that is what every tab shows;
  <code>fy28/public/favicon.svg</code> is the purple template leftover and nothing
  references it. Replacing the mark means changing the tag as well as the file.</p>
</footer>
"""
    p = os.path.join(OUT, 'index.html')
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('wrote ' + os.path.relpath(p, ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help="a, b, c, or 'sheet' for the favicon sheet alone")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.only == 'sheet':
        favicon_sheet()
        preview()
        return 0
    keys = [a.only] if a.only else ['a', 'b', 'c']
    for k in keys:
        p = os.path.join(OUT, 'favicon-%s.svg' % k)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(FAVICONS[k])
        print('wrote ' + os.path.relpath(p, ROOT))
        render(k)
    favicon_sheet()
    preview()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
