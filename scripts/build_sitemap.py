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
import io
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public')
DIST = os.path.join(ROOT, 'fy28', 'dist')
OUT = os.path.join(PUB, 'sitemap.xml')
SITE = 'https://lunenburgbudgetproject.org'

# The doors, in the order an agent should meet them.
ENTRY = [
    '/llms.txt', '/version.json', '/mcp',
    '/api/index', '/api/schema', '/api/tables', '/api/questions', '/api/query',
    '/api/coverage', '/api/documents',
    '/minutes/INDEX.txt', '/minutes/find/README.txt',
    '/minutes/find/coverage.json', '/minutes/find/documents-index.json',
    '/data/archive-manifest.csv', '/data/minutes-index.csv',
    '/data/model/index.json', '/data/sources/index.json',
]


ROUTES_TS = os.path.join(ROOT, 'fy28', 'src', 'routes.ts')


def routed():
    """Every top-level route the app itself routes on, read from routes.ts -- the SLUG
    table minus UNLISTED -- the same way prerender.mjs reads it.

    THIS BREAKS THE LAST CYCLE. `routes()` used to read dist alone, and `prerender.mjs`
    refuses to write a route that is not in the sitemap, so a brand new top-level page
    could never enter either: the first refresh after /commercial-development was added
    (16 September 2026) built every route and then failed on exactly that check, and
    production went another day without a deploy. The route table is the thing that
    decides a page exists, so the sitemap reads it directly.
    """
    src = io.open(ROUTES_TS, encoding='utf-8').read()
    m = re.search(r'export const SLUG: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    if not m:
        raise SystemExit('routes.ts: could not find SLUG')
    slugs = {k: v for k, v in re.findall(r"^\s*([a-z]+):\s*'([^']*)'", m.group(1), re.M)}
    u = re.search(r"export const UNLISTED[^\n]*new Set<Tab>\(\[([^\]]*)\]", src)
    unlisted = set(re.findall(r"'([a-z]+)'", u.group(1))) if u else set()
    return ['/' + v for k, v in slugs.items() if v and k not in unlisted]


def routes():
    """Every top-level page, from the route table (see `routed`), alphabetical as the
    build's file listing was, so the sitemap's order does not churn. Nested routes --
    /analysis/<id>, /blog/<slug> and the rest -- are enumerated by their own sources."""
    return ['/'] + sorted(routed())


def analysis_pages():
    """The markdown analyses as PAGES, derived from the documents rather than the build.

    `routes()` finds these once they have been rendered, and cannot find them before the
    first build that renders them -- while `prerender.mjs` refuses to write a route that
    is not already in the sitemap. That is a genuine cycle, and this breaks it at the end
    the documents are on: the .md files decide which analyses exist, so the sitemap can
    know the addresses before anything has been built.
    """
    out = []
    for p in sorted(glob.glob(os.path.join(PUB, 'docs', 'analyses', '*.md'))):
        out.append('/analysis/' + os.path.basename(p)[:-3])
    return out


def blog_pages():
    """The archive, and every post that has actually been PUBLISHED.

    Two things this has to get right and neither is obvious.

    THE ARCHIVE BREAKS THE SAME CYCLE `analysis_pages` BREAKS. `routes()` finds a page only
    once it has been rendered into dist, and `prerender.mjs` refuses to render a route that
    is not already in the sitemap -- so a brand new top-level route can never enter either
    list on its own. `/blog` is emitted from the payload, which is the thing that decides
    it exists.

    AND A DRAFT IS NOT AN ADDRESS TO INDEX. A post with no publication date, or one dated
    in the future, is reachable by its link and listed nowhere: putting it in the sitemap
    would be publishing it, which is the one decision this whole pipeline leaves to a
    person. So the state is computed here, from the same field the page computes it from.
    """
    p = os.path.join(PUB, 'data', 'blog.json')
    if not os.path.exists(p):
        return []
    posts = json.load(io.open(p, encoding='utf-8')).get('posts', [])
    today = date.today().isoformat()
    live = [x['slug'] for x in posts if x.get('publish') and x['publish'] <= today]
    return ['/blog'] + ['/blog/' + s for s in sorted(live)]


def board_pages():
    """One page per board, read from the boards payload -- the same list the page renders."""
    p = os.path.join(PUB, 'data', 'boards.json')
    if not os.path.exists(p):
        return []
    boards = json.load(io.open(p, encoding='utf-8')).get('boards', [])
    return ['/boards/' + b['slug'] for b in boards]


def feed_pages():
    """The budget feed and every finished year and episode it lists, from its own payload."""
    p = os.path.join(PUB, 'data', 'budget-feed.json')
    if not os.path.exists(p):
        return []
    d = json.load(io.open(p, encoding='utf-8'))
    out = ['/budget-feed'] + [s['path'] for s in d.get('seasons', []) if s.get('path') and s['path'] != '/budget-feed']
    return sorted(set(out))


def published_data():
    """Every dataset published under /data, so each is indexable on its own."""
    out = []
    for p in sorted(glob.glob(os.path.join(PUB, 'data', '*'))):
        if os.path.isfile(p) and not p.endswith('.db'):
            out.append('/data/' + os.path.basename(p))
    return out


def feeds():
    """The Atom feeds (scripts/build_feeds.py): addresses a program subscribes to."""
    return ['/feeds/' + os.path.basename(p) for p in sorted(glob.glob(os.path.join(PUB, 'feeds', '*.xml')))]


def analyses():
    out = []
    for p in sorted(glob.glob(os.path.join(PUB, 'docs', 'analyses', '*.md'))):
        out.append('/docs/analyses/' + os.path.basename(p))
    return out


def reference():
    """Every reference page published by `build_reference_pages.py`.

    Globbed rather than listed, for the same reason `routes()` is: a page added there and
    not added here would be published, correct, and reachable by nobody -- which is the
    exact condition these pages were rescued FROM. And per this project's reachability
    note, some agent tools accept only URLs that came from a search result, so being a
    static file at a real address is not enough on its own; being INDEXED is what reaches
    them, and the sitemap is where that starts.
    """
    return ['/reference/' + os.path.basename(p)
            for p in sorted(glob.glob(os.path.join(PUB, 'reference', '*')))
            if os.path.isfile(p)]


def render():
    seen, urls = set(), []
    for u in (routes() + analysis_pages() + blog_pages() + board_pages() + feed_pages() + ENTRY + published_data()
              + reference() + analyses() + feeds()):
        if u not in seen:
            seen.add(u)
            urls.append(u)
    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        # A page a person reads is worth more to a crawler than one shard of a dataset,
        # but the endpoints must be here at all -- that is the whole point.
        pri = '1.0' if u == '/' else ('0.8' if not u.startswith(('/api/', '/data/', '/docs/', '/feeds/'))
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
    pages = sum(1 for u in urls if not u.startswith(('/api/', '/data/', '/docs/', '/feeds/')))
    print(f'wrote sitemap.xml: {len(urls)} URLs — {pages} pages a person reads, '
          f'{len(urls) - pages} addresses a program needs')
    return 0


if __name__ == '__main__':
    sys.exit(main())
