#!/usr/bin/env python3
"""How long every page takes to read, measured from the build.

    python3 scripts/build_reading_time.py           # write notes/generated/reading-time.csv
    python3 scripts/build_reading_time.py --check   # fail if it no longer reproduces

One row per prerendered route in fy28/dist: the words a reader meets (body text, with
the header, breadcrumb, footer and scripts stripped), the minutes that is at 230 words a
minute, and the shape of the page -- how many sections, how many words before the first
one. TJ, 15 September 2026: "an expected reading time for every page and report ... I
think that will help us figure out how we need to create separate shorter pages."

WHAT THE NUMBER IS. Words in the DOM as prerendered, at every dial's default, with
`<details>` counted whether or not it is open -- so a page that hides half of itself
behind an expander is measured at its full length, which is the honest length. A route
that serves many pages (a post, a meeting, a board) is measured only at its index,
because those are the only ones in the build; the per-item pages are in the JSON
payloads and not here. The pace is a reading pace, not a skimming one: nobody reads a
45-minute page, which is the point of the table.

Sorted longest first, because the top of the list is the work.
"""
import argparse
import csv
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'fy28', 'dist')
OUT = os.path.join(ROOT, 'notes', 'generated', 'reading-time.csv')

WPM = 230
# Skipped: not pages a person reads, or not ours to measure.
SKIP_PREFIX = ('share/', 'docs/', 'data/', 'api/', 'reference/', 'minutes/', 'assets/')

TAG = re.compile(r'<[^>]+>')
COMMENT = re.compile(r'<!--.*?-->', re.S)
DROP = re.compile(r'<(script|style|noscript|svg)\b.*?</\1>', re.S | re.I)
# The furniture every page carries: the sticky header, the breadcrumb and the footer.
FURNITURE = re.compile(r'<header class="no-print[^"]*".*?</header>|<nav aria-label="Breadcrumb".*?</nav>|<footer\b.*?</footer>', re.S | re.I)
H1 = re.compile(r'<h1\b[^>]*>(.*?)</h1>', re.S | re.I)
H2 = re.compile(r'<h2\b[^>]*>(.*?)</h2>', re.S | re.I)
TITLE = re.compile(r'<title>(.*?)</title>', re.S | re.I)
CRUMB = re.compile(r'<nav aria-label="Breadcrumb".*?</nav>', re.S | re.I)
LI = re.compile(r'<li\b[^>]*>(.*?)</li>', re.S | re.I)


def text(fragment):
    return re.sub(r'\s+', ' ', html.unescape(TAG.sub(' ', fragment))).strip()


def words(fragment):
    return len(text(fragment).split())


def routes():
    out = []
    for dirpath, _, names in os.walk(DIST):
        for name in names:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            route = os.path.relpath(path, DIST)[:-len('.html')]
            if route == 'index':
                route = ''
            if route.startswith(SKIP_PREFIX) or route.startswith('__'):
                continue
            out.append((route, path))
    return out


def measure(route, path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    raw = COMMENT.sub(' ', raw)
    raw = DROP.sub(' ', raw)
    t = TITLE.search(raw)
    title = re.sub(r'\s+—\s+Lunenburg Budget Project\s*$', '', text(t.group(1))) if t else route
    crumb = CRUMB.search(raw)
    # The structural trail, as the page shows it -- PARENT in routes.ts, not the area.
    trail = ' > '.join(text(x).rstrip(' \u203a') for x in LI.findall(crumb.group(0))) if crumb else ''
    body = FURNITURE.sub(' ', raw)
    h1 = H1.search(body)
    h2s = [m.start() for m in H2.finditer(body)]
    total = words(body)
    # Words before the first section heading -- the standfirst and whatever else stands
    # in front of the thing (rule 7a's count).
    before = words(body[:h2s[0]]) if h2s else total
    return {
        'route': '/' + route,
        'title': title,
        'breadcrumb': trail,
        'h1': text(h1.group(1)) if h1 else '',
        'words': total,
        'minutes': round(total / WPM, 1),
        'sections': len(h2s),
        'words_before_first_section': before,
        # A table is read down a column, not word by word, so a page whose words are
        # mostly rows is shorter than its count says. The count is here to discount it.
        'table_rows': len(re.findall(r'<tr\b', body, re.I)),
        'details_blocks': len(re.findall(r'<details\b', body, re.I)),
    }


def render():
    if not os.path.isdir(DIST):
        raise SystemExit('no build at fy28/dist -- run npm run build:site first')
    rows = [measure(r, p) for r, p in routes()]
    rows.sort(key=lambda r: (-r['words'], r['route']))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue(), rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out, rows = render()
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != out:
            print('STALE %s -- run: python3 scripts/build_reading_time.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok: %s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(out)
    total = sum(r['words'] for r in rows)
    print('wrote %s -- %d pages, %s words, %d min at %d wpm; longest %s (%s min)'
          % (os.path.relpath(OUT, ROOT), len(rows), format(total, ','), total // WPM, WPM,
             rows[0]['route'], rows[0]['minutes']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
