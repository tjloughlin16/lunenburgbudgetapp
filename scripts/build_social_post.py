#!/usr/bin/env python3
"""Build a social-media post -- the text to paste and the image to attach -- from a spec.

    python3 scripts/build_social_post.py social/posts/2026-10-05-find-your-board
    python3 scripts/build_social_post.py --all
    python3 scripts/build_social_post.py --check          # every post still reproduces
    python3 scripts/build_social_post.py --new <slug>     # start a post from the template

ONE FOLDER PER POST, AND THE FOLDER IS THE POST.

    social/posts/<date>-<slug>/
        post.json    the spec: what it says, where its figures come from, how it looks.
                     The ONLY file anybody writes by hand.
        post.txt     GENERATED. Open it, select all, paste into Facebook. Plain text:
                     Facebook does not render Markdown, so a `**bold**` arrives as
                     asterisks. Line breaks, emoji and bare URLs all survive the paste.
        image.png    GENERATED. Attach it. A post without one is refused -- the build
                     writes post.txt only after the image has rendered and been measured.
        image.html   GENERATED. What the image was rendered from, so --check can tell
                     whether it would still come out the same.

EVERY FIGURE IS INTERPOLATED (rule 2). A template says `{sb.counts.agendas|n}`, never
`701`. The spec's `data` block names where each alias comes from in the site's published
payloads, so a post quotes exactly what the site shows on the day it was built. A digit
typed into a template is REFUSED, because a number in a sentence is the one thing here
that can be silently wrong -- the exceptions are URLs and the spec's own `literal` list,
for a digit that is not a figure (a "5-minute read", a year in a board's name).

STANDARD FRAME, ITS OWN FLARE. Every image shares the frame: the kicker, the headline,
the footer with the address and the as-of date, one type family, one surface. What
changes per post is the LAYOUT (what shape the content takes) and the FLARE -- an accent
colour and a background motif. Both default to a pick seeded by the slug, so two posts
never look like copies by accident, and either can be set in the spec when it matters.

A POSTED POST IS FROZEN. Once `posted` is set in the spec, --check stops re-rendering it:
the payloads it quotes will move, and what went out on that day is what it should say.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'fy28', 'public', 'data')
POSTS = os.path.join(ROOT, 'social', 'posts')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
SITE = 'lunenburgbudgetproject.org'

SIZES = {'square': (1200, 1200), 'landscape': (1200, 630), 'portrait': (1080, 1350)}

# Accents for TEXT and marks on the light surface. Each is dark enough to carry a kicker
# or a large figure (contrast >= 4.5:1 against #fcfcfb), and they are kept apart from the
# site's --series-cost / --series-revenue, which mean cost and revenue on a chart.
ACCENTS = {
    'royal':   '#12428f',   # the site's own --brand
    'pine':    '#1d6f2e',
    'plum':    '#a3357f',
    'ember':   '#b4441c',
    'violet':  '#5b3fa3',
    'harbor':  '#0f6e75',
}
MOTIFS = ('contours', 'dots', 'arcs', 'stripes', 'blocks')


# ---- figures ---------------------------------------------------------------------

def walk(obj, path):
    """`boards[slug=select-board].counts.agendas`, `meetings[0].date`. Fails loudly: a
    path that matches nothing is not a zero (the shape every silent defect here took)."""
    for part in re.findall(r'[^.\[\]]+|\[[^\]]*\]', path):
        if part.startswith('['):
            sel = part[1:-1]
            if '=' in sel:
                k, v = sel.split('=', 1)
                hits = [x for x in obj if str(x.get(k)) == v]
                if len(hits) != 1:
                    raise SystemExit(f'REFUSING: [{sel}] matched {len(hits)} rows in {path!r}')
                obj = hits[0]
            else:
                obj = obj[int(sel)]
        else:
            if not isinstance(obj, dict) or part not in obj:
                raise SystemExit(f'REFUSING: {path!r} -- no key {part!r}')
            obj = obj[part]
    return obj


def load_data(spec):
    out, cache = {}, {}
    for alias, ref in (spec.get('data') or {}).items():
        fname, _, path = ref.partition('#')
        if fname not in cache:
            p = os.path.join(DATA, fname)
            if not os.path.exists(p):
                raise SystemExit(f'REFUSING: data file {fname} is not in fy28/public/data')
            cache[fname] = json.load(open(p, encoding='utf-8'))
        out[alias] = walk(cache[fname], path) if path else cache[fname]
    return out


def _date(v):
    return dt.date.fromisoformat(str(v)[:10])


FILTERS = {
    'n':     lambda v: f'{v:,.0f}' if isinstance(v, (int, float)) else str(v),
    'pct':   lambda v: f'{v * 100:.0f}%',
    'day':   lambda v: _date(v).strftime('%A, %B ') + str(_date(v).day),
    'short': lambda v: _date(v).strftime('%b ') + str(_date(v).day),
    'wday':  lambda v: _date(v).strftime('%a %b ') + str(_date(v).day),
    'year':  lambda v: str(v)[:4],
    'len':   lambda v: f'{len(v):,}',
    'upper': lambda v: str(v).upper(),
}
REF = re.compile(r'\{([A-Za-z_][\w.\-]*(?:\[[^\]]*\][\w.\-]*)*)(?:\|(\w+))?\}')
URL = re.compile(r'(?:https?://)?[\w.-]+\.(?:org|gov|com|net)(?:/[^\s<>"]*)?')


def render(text, data, literal=(), where='template', esc=False):
    """Fill `{alias.path|filter}`. Refuse a digit the template typed itself."""
    bare = URL.sub('', REF.sub('', text))
    for lit in literal:
        bare = bare.replace(lit, '')
    typed = re.findall(r'\d[\d,.]*', bare)
    if typed:
        raise SystemExit(f'REFUSING: {where} types the figure(s) {typed} -- interpolate them '
                         f'from `data`, or list a non-figure in `literal`.\n  {text!r}')

    def sub(m):
        expr, filt = m.group(1), m.group(2)
        alias, _, rest = expr.partition('.')
        if alias not in data:
            raise SystemExit(f'REFUSING: {where} uses {{{expr}}} but `data` has no {alias!r}')
        v = walk(data[alias], rest) if rest else data[alias]
        if filt:
            if filt not in FILTERS:
                raise SystemExit(f'REFUSING: unknown filter |{filt}')
            v = FILTERS[filt](v)
        v = str(v)
        return html.escape(v) if esc else v
    return REF.sub(sub, text)


# ---- the image -------------------------------------------------------------------

def flare_of(spec, slug):
    seed = int(hashlib.sha256(slug.encode()).hexdigest(), 16)
    f = spec.get('flare') or {}
    names = sorted(ACCENTS)
    accent = f.get('accent') or names[seed % len(names)]
    motif = f.get('motif') or MOTIFS[(seed // 7) % len(MOTIFS)]
    if accent not in ACCENTS:
        raise SystemExit(f'REFUSING: accent {accent!r}; choose from {", ".join(names)}')
    if motif not in MOTIFS:
        raise SystemExit(f'REFUSING: motif {motif!r}; choose from {", ".join(MOTIFS)}')
    return accent, ACCENTS[accent], motif, seed


def motif_svg(motif, color, w, h, seed):
    """A quiet background figure in the top-right corner -- the post's own mark. Drawn,
    deterministic from the slug, and always behind the content at low opacity."""
    cx, cy = w - 40, 40
    s = []
    if motif == 'contours':
        for i in range(9):
            r = 90 + i * 46
            wob = 10 + (seed >> i) % 18
            s.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{r + wob}" ry="{r}" fill="none" '
                     f'stroke="{color}" stroke-width="2"/>')
    elif motif == 'dots':
        for i in range(12):
            for j in range(9):
                d = ((i - 11) ** 2 + j ** 2) ** .5
                if d < 10.5:
                    s.append(f'<circle cx="{w - 30 - i * 34}" cy="{30 + j * 34}" '
                             f'r="{max(1.5, 6 - d * .45):.1f}" fill="{color}"/>')
    elif motif == 'arcs':
        for i in range(7):
            r = 120 + i * 60
            s.append(f'<circle cx="{w}" cy="0" r="{r}" fill="none" stroke="{color}" '
                     f'stroke-width="{14 - i * 1.6:.1f}"/>')
    elif motif == 'stripes':
        for i in range(14):
            x = w - 520 + i * 40
            s.append(f'<line x1="{x}" y1="0" x2="{x + 380}" y2="380" stroke="{color}" '
                     f'stroke-width="10"/>')
    elif motif == 'blocks':
        for i in range(6):
            for j in range(4):
                if (seed >> (i * 4 + j)) & 1 and i + j < 7:
                    s.append(f'<rect x="{w - 70 - i * 64}" y="{14 + j * 64}" width="52" '
                             f'height="52" rx="8" fill="{color}"/>')
    return (f'<svg class="motif" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<g opacity=".11">{"".join(s)}</g></svg>')


def layout_spotlight(img, R):
    """One capability, shown as the thing itself: a card drawn the way the page reads."""
    c = img['card']
    rows = ''.join(
        f'<div class="row"><div class="rl">{R(r["label"])}</div>'
        f'<div class="rv">{R(r["value"])}</div></div>' for r in c.get('rows', []))
    chips = ''.join(f'<span class="chip">{R(x)}</span>' for x in c.get('chips', []))
    stats = ''.join(
        f'<div class="st"><div class="sv">{R(s["value"])}</div><div class="sl">{R(s["label"])}'
        f'</div></div>' for s in c.get('stats', []))
    return f'''
<div class="card">
  <div class="ch"><div class="ce">{R(c.get("eyebrow", ""))}</div>
    <div class="ct">{R(c["title"])}</div></div>
  {rows}
  {f'<div class="chips">{chips}</div>' if chips else ''}
  {f'<div class="stats">{stats}</div>' if stats else ''}
</div>'''


def layout_tiles(img, R):
    t = ''.join(
        f'<div class="t"><div class="te">{R(x["eyebrow"])}</div><div class="tn">{R(x["value"])}</div>'
        f'<div class="tu">{R(x["label"])}</div><div class="td">{R(x.get("text", ""))}</div>'
        f'<div class="tp">{SITE}<b>{html.escape(x.get("path", ""))}</b></div></div>'
        for x in img['tiles'])
    return f'<div class="tiles">{t}</div>'


def layout_hero(img, R):
    h = img['hero']
    return (f'<div class="hero"><div class="hv">{R(h["value"])}</div>'
            f'<div class="hl">{R(h["label"])}</div><div class="ht">{R(h.get("text", ""))}</div></div>')


LAYOUTS = {'spotlight': layout_spotlight, 'tiles': layout_tiles, 'hero': layout_hero}

CSS = '''
*{box-sizing:border-box}
html,body{margin:0}
body{width:%(w)spx;height:%(h)spx;background:#fcfcfb;color:#0b0b0b;position:relative;overflow:hidden;
  font-family:-apple-system,"Helvetica Neue",Helvetica,Arial,sans-serif;padding:64px 60px 0}
.motif{position:absolute;left:0;top:0;z-index:0}
.frame{position:relative;z-index:1;height:100%%;display:flex;flex-direction:column}
.k{font-weight:700;font-size:22px;letter-spacing:.14em;color:%(a)s}
h1{margin:18px 0 0;font-weight:800;font-size:%(hs)spx;line-height:1.06;letter-spacing:-.02em;max-width:1080px;text-wrap:balance}
h1 em{font-style:normal;color:%(a)s}
.sub{font-size:28px;line-height:1.35;color:#52514e;margin:16px 0 0;max-width:980px}
.body{margin-top:40px;flex:1;display:flex;flex-direction:column;justify-content:center;padding-bottom:40px}
.foot{display:flex;justify-content:space-between;align-items:baseline;padding:22px 0 36px;
  border-top:2px solid #e4e2dc;font-size:20px;color:#898781}
.foot b{color:%(a)s;font-size:24px}
/* spotlight */
.card{background:#fff;border:2px solid #e4e2dc;border-radius:20px;overflow:hidden;
  box-shadow:0 18px 40px -24px rgba(0,0,0,.25)}
.ch{background:%(a)s;color:#fff;padding:26px 34px 24px}
.ce{font-weight:700;font-size:17px;letter-spacing:.14em;opacity:.85}
.ct{font-weight:800;font-size:44px;margin-top:4px;letter-spacing:-.01em}
.row{display:flex;gap:24px;padding:20px 34px;border-bottom:1px solid #eeece6}
.rl{flex:0 0 190px;font-weight:700;font-size:19px;letter-spacing:.06em;color:#898781;text-transform:uppercase;padding-top:5px}
.rv{font-size:27px;line-height:1.35;font-weight:500}
.chips{display:flex;gap:12px;flex-wrap:wrap;padding:20px 34px}
.chip{border:2px solid %(a)s;color:%(a)s;border-radius:999px;padding:8px 18px;font-weight:700;font-size:21px}
.stats{display:flex;background:#f6f5f1;border-top:1px solid #eeece6}
.st{flex:1;padding:20px 34px}
.sv{font-weight:800;font-size:40px;letter-spacing:-.01em}
.sl{font-size:18px;color:#52514e;margin-top:2px}
/* tiles */
.tiles{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.t{background:#fff;border:2px solid #e4e2dc;border-top:10px solid %(a)s;border-radius:16px;padding:26px 30px;min-height:330px;display:flex;flex-direction:column}
.te{font-weight:700;font-size:18px;letter-spacing:.12em;color:%(a)s}
.tn{font-weight:800;font-size:72px;line-height:1;margin-top:12px;letter-spacing:-.02em}
.tu{font-weight:700;font-size:25px;margin-top:6px}
.td{font-size:21px;line-height:1.38;color:#52514e;margin-top:10px}
.tp{margin-top:auto;font-size:18px;color:#898781}.tp b{color:%(a)s}
/* hero */
.hero{padding-top:30px}
.hv{font-weight:800;font-size:220px;line-height:.95;letter-spacing:-.04em;color:%(a)s}
.hl{font-weight:700;font-size:44px;margin-top:10px}
.ht{font-size:30px;line-height:1.4;color:#52514e;margin-top:20px;max-width:900px}
'''


def build_html(spec, slug, data):
    lit = spec.get('literal', [])
    img = spec['image']
    w, h = SIZES[img.get('size', 'square')]
    name, color, motif, seed = flare_of(spec, slug)
    R = lambda t: render(t, data, lit, where=f'{slug} image', esc=True)  # noqa: E731
    if img['layout'] not in LAYOUTS:
        raise SystemExit(f'REFUSING: layout {img["layout"]!r}; choose from {", ".join(LAYOUTS)}')
    body = LAYOUTS[img['layout']](img, R)
    head = R(img['headline'])
    if img.get('emphasis'):
        e = R(img['emphasis'])
        if e not in head:
            raise SystemExit(f'REFUSING: emphasis {e!r} is not in the headline')
        head = head.replace(e, f'<em>{e}</em>', 1)
    path = html.escape(img.get('path', ''))
    css = CSS % dict(w=w, h=h, a=color, hs=img.get('headline_size', 66))
    return f'''<!doctype html><html><head><meta charset="utf-8">
<!-- GENERATED by scripts/build_social_post.py from post.json. Flare: {name} / {motif}. -->
<style>{css}</style></head><body>
{motif_svg(motif, color, w, h, seed)}
<div class="frame">
<div class="k">LUNENBURG BUDGET PROJECT</div>
<h1>{head}</h1>
{f'<p class="sub">{R(img["sub"])}</p>' if img.get('sub') else ''}
<div class="body">{body}</div>
<div class="foot"><span>{SITE}<b>{path}</b></span><span>{R(img["as_of"]) if img.get("as_of") else ""}</span></div>
</div></body></html>
'''


def shoot(html_path, png_path, size):
    w, h = SIZES[size]
    if not os.path.exists(CHROME):
        raise SystemExit('REFUSING: Chrome not found; a post without an image is not a post')
    tmp = png_path + '.tmp.png'
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                    '--force-device-scale-factor=2', f'--window-size={w},{h}',
                    f'--screenshot={tmp}', 'file://' + html_path],
                   capture_output=True, timeout=120)
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 20_000:
        raise SystemExit(f'REFUSING: the image did not render ({tmp})')
    os.replace(tmp, png_path)


def overflow(html_path, size):
    """Does anything in the frame run past the canvas? Rendered, then measured in JS."""
    w, h = SIZES[size]
    js_html = open(html_path, encoding='utf-8').read().replace(
        '</body>', '<script>document.title=JSON.stringify({sh:document.querySelector(".frame")'
        '.scrollHeight,ch:document.querySelector(".frame").clientHeight,'
        'sw:document.body.scrollWidth});</script></body>')
    tmp = html_path + '.probe.html'
    open(tmp, 'w', encoding='utf-8').write(js_html)
    out = subprocess.run([CHROME, '--headless=new', '--disable-gpu', f'--window-size={w},{h}',
                          '--dump-dom', 'file://' + tmp], capture_output=True, text=True,
                         timeout=120).stdout
    os.remove(tmp)
    m = re.search(r'<title>(\{.*?\})</title>', out)
    if not m:
        return None
    d = json.loads(html.unescape(m.group(1)))
    return d if (d['sh'] > d['ch'] + 1 or d['sw'] > w + 1) else None


# ---- the text --------------------------------------------------------------------

def build_text(spec, slug, data):
    lines = spec['text']
    if isinstance(lines, list):
        lines = '\n'.join(lines)
    out = render(lines, data, spec.get('literal', []), where=f'{slug} text')
    # Facebook pastes this verbatim. Markdown would arrive as punctuation.
    for bad, why in (('**', 'bold'), ('__', 'bold'), ('](', 'a link'), ('\n#', 'a heading')):
        if bad in out:
            raise SystemExit(f'REFUSING: {slug} text uses Markdown {why} ({bad!r}); Facebook '
                             f'shows it literally. Use plain text, emoji and line breaks.')
    return out.rstrip('\n') + '\n'


# ---- driver ----------------------------------------------------------------------

def build(folder, check=False):
    slug = os.path.basename(folder.rstrip('/'))
    spec = json.load(open(os.path.join(folder, 'post.json'), encoding='utf-8'))
    pj = lambda n: os.path.join(folder, n)  # noqa: E731
    if spec.get('posted'):
        missing = [n for n in ('post.txt', 'image.png') if not os.path.exists(pj(n))]
        if missing:
            return f'FAIL {slug}: posted {spec["posted"]} but {", ".join(missing)} missing'
        return f'ok   {slug}: posted {spec["posted"]}, frozen'
    data = load_data(spec)
    text = build_text(spec, slug, data)
    page = build_html(spec, slug, data)
    if check:
        bad = [n for n, want in (('post.txt', text), ('image.html', page))
               if not os.path.exists(pj(n)) or open(pj(n), encoding='utf-8').read() != want]
        if not os.path.exists(pj('image.png')):
            bad.append('image.png (missing)')
        return f'FAIL {slug}: stale {", ".join(bad)}' if bad else f'ok   {slug}'
    open(pj('image.html'), 'w', encoding='utf-8').write(page)
    size = spec['image'].get('size', 'square')
    over = overflow(os.path.abspath(pj('image.html')), size)
    if over:
        raise SystemExit(f'REFUSING: {slug} image overflows its canvas {over}; cut words, '
                         f'not the frame')
    shoot(os.path.abspath(pj('image.html')), os.path.abspath(pj('image.png')), size)
    # The text is written LAST, so a post.txt on disk always has its image beside it.
    open(pj('post.txt'), 'w', encoding='utf-8').write(text)
    return f'wrote {slug}: post.txt ({len(text):,} chars), image.png'


TEMPLATE = {
    "posted": None,
    "about": "One line: the single capability this post shows, and who it is for.",
    "data": {"m": "app-metrics.json"},
    "literal": [],
    "flare": {},
    "image": {
        "layout": "hero", "size": "square",
        "headline": "Headline, one idea", "emphasis": "one idea",
        "sub": "One line under it.",
        "hero": {"value": "{m.meetings.documents|n}", "label": "agendas and minutes",
                 "text": "What a reader can do with it."},
        "path": "/", "as_of": "As of {m.as_of|short}"
    },
    "text": ["First line is the hook.", "", "Link: https://" + SITE + "/"]
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', nargs='?')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--new')
    a = ap.parse_args()
    if a.new:
        d = os.path.join(POSTS, f'{dt.date.today()}-{a.new}')
        os.makedirs(d, exist_ok=False)
        json.dump(TEMPLATE, open(os.path.join(d, 'post.json'), 'w'), indent=2)
        print(f'started {d}/post.json'); return
    folders = ([os.path.join(POSTS, n) for n in sorted(os.listdir(POSTS))
                if os.path.exists(os.path.join(POSTS, n, 'post.json'))]
               if (a.all or a.check) and not a.folder else [a.folder])
    if not folders or folders == [None]:
        ap.error('name a post folder, or --all / --check')
    res = [build(f, check=a.check) for f in folders]
    print('\n'.join(res))
    if any(r.startswith('FAIL') for r in res):
        sys.exit(1)


if __name__ == '__main__':
    main()
