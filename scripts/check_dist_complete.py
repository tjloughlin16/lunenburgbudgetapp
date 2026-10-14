#!/usr/bin/env python3
"""IS fy28/dist A WHOLE BUILD? Every page the sitemap names must have its prerendered file.

check_prerender.py asks whether the pages PRESENT are rendered, and a build caught halfway
passes it -- 128 of ~1,900 pages, "every page carries rendered HTML" (14 October 2026),
because `vite build` empties dist/ and the prerender refills it page by page. This asks the
other question: is every page that should be there, there. deploy_site.sh runs both.

Two kinds of sitemap entry are not prerendered pages, and both are read from
build_sitemap.py, the file that put them in the sitemap -- never listed here:
  ENTRY         the agent doors (/mcp, /api/index ...), served by Functions, not pages.
  feed_pages()  the budget feed's season pages (/budget-feed/fy27 ...). The prerender does
                not render them; they are drawn in the browser. A KNOWN GAP, printed every
                run so it is not mistaken for coverage -- not a reason to refuse a deploy,
                because it is the same in every build.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sitemap as S  # noqa: E402

DIST = S.DIST
sm = open(os.path.join(DIST, 'sitemap.xml'), encoding='utf-8').read()
pages = [re.sub(r'^https?://[^/]+', '', u) for u in re.findall(r'<loc>([^<]+)</loc>', sm)]
pages = [p for p in pages if not re.search(r'\.[a-z0-9]+$', p) and p not in S.ENTRY]
browser_only = set(S.feed_pages()) - {'/budget-feed'}


def held(p):
    p = p.strip('/')
    return (os.path.exists(os.path.join(DIST, (p or 'index') + '.html'))
            or os.path.exists(os.path.join(DIST, p, 'index.html')))


missing = [p for p in pages if not held(p)]
gap = [p for p in missing if p in browser_only]
missing = [p for p in missing if p not in browser_only]
print('%d of %d sitemap pages are prerendered in fy28/dist' % (len(pages) - len(missing) - len(gap), len(pages)))
if gap:
    print('known gap, drawn in the browser only: %s' % ', '.join(sorted(gap)))
if missing:
    print('MISSING, e.g.: ' + ', '.join(missing[:5]))
    sys.exit(1)
