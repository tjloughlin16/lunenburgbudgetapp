#!/usr/bin/env python3
"""The sitemap, generated — including the addresses an agent needs indexed.

    python3 scripts/build_sitemap.py [--check]

TWO REASONS THIS IS NO LONGER HAND-WRITTEN

**It went stale.** It was a static file, edited by hand, listing 24 URLs. Routes were added
after it and `prerender.mjs` caught those, but nothing caught the machine-readable
endpoints that were never in it at all.

**And a sitemap is how some agents learn a URL exists.** One reported that its fetch tool
accepts only URLs that came from a prior SEARCH RESULT -- not links extracted from a page
it had already fetched. It had the homepage open, with `/agents` and `/api/index` as real
anchors in it, and was still refused: *"not in any prior search or fetch result."* So every
link-shaped fix made here is beside the point for that failure mode. What reaches it is
being INDEXED, and what gets indexed starts with the sitemap.

So this lists the pages a person reads AND the endpoints a program needs: llms.txt, the API
entry points, every published dataset, every analysis, the meeting index. Not all 817 API
files -- a sitemap of shards helps nobody -- but every door into them.
"""
import argparse
import glob
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public')
DIST = os.path.join(ROOT, 'fy28', 'dist')
OUT = os.path.join(PUB, 'sitemap.xml')
SITE = 'https://lunenburgbudgetproject.org'

# The doors, in the order an agent should meet them.
ENTRY = [
    '/llms.txt', '/version.json',
    '/api/index', '/api/schema', '/api/tables', '/api/questions', '/api/query',
    '/api/coverage', '/api/documents',
    '/minutes/INDEX.txt', '/minutes/find/README.txt',
    '/minutes/find/coverage.json', '/minutes/find/documents-index.json',
    '/data/archive-manifest.csv', '/data/minutes-index.csv',
    '/data/model/index.json', '/data/sources/index.json',
]


def routes():
    """Every prerendered page, read off the build rather than listed here."""
    out = ['/']
    for p in sorted(glob.glob(os.path.join(DIST, '*.html'))):
        name = os.path.basename(p)[:-5]
        if name not in ('index', 'not-found'):
            out.append('/' + name)
    return out


def published_data():
    """Every dataset published under /data, so each is indexable on its own."""
    out = []
    for p in sorted(glob.glob(os.path.join(PUB, 'data', '*'))):
        if os.path.isfile(p) and not p.endswith('.db'):
            out.append('/data/' + os.path.basename(p))
    return out


def analyses():
    out = []
    for p in sorted(glob.glob(os.path.join(PUB, 'docs', 'analyses', '*.md'))):
        out.append('/docs/analyses/' + os.path.basename(p))
    return out


def render():
    seen, urls = set(), []
    for u in routes() + ENTRY + published_data() + analyses():
        if u not in seen:
            seen.add(u)
            urls.append(u)
    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        # A page a person reads is worth more to a crawler than one shard of a dataset,
        # but the endpoints must be here at all -- that is the whole point.
        pri = '1.0' if u == '/' else ('0.8' if not u.startswith(('/api/', '/data/', '/docs/'))
                                      else '0.5')
        lines += ['  <url>', f'    <loc>{SITE}{u}</loc>',
                  f'    <lastmod>{today}</lastmod>',
                  f'    <priority>{pri}</priority>', '  </url>']
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n', urls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    body, urls = render()
    if args.check:
        current = open(OUT).read() if os.path.exists(OUT) else ''
        # lastmod moves every day by design, so compare everything else.
        strip = lambda t: '\n'.join(l for l in t.splitlines() if 'lastmod' not in l)
        if strip(current) != strip(body):
            print('STALE  sitemap.xml — run: python3 scripts/build_sitemap.py')
            return 1
        print(f'ok: sitemap.xml lists {len(urls)} URLs')
        return 0
    open(OUT, 'w').write(body)
    pages = sum(1 for u in urls if not u.startswith(('/api/', '/data/', '/docs/')))
    print(f'wrote sitemap.xml: {len(urls)} URLs — {pages} pages a person reads, '
          f'{len(urls) - pages} addresses a program needs')
    return 0


if __name__ == '__main__':
    sys.exit(main())
