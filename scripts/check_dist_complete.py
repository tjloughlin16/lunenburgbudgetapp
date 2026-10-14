#!/usr/bin/env python3
"""IS fy28/dist A WHOLE BUILD? Every page the sitemap names must have its prerendered file.

check_prerender.py asks whether the pages PRESENT are rendered, and a build caught halfway
passes it -- 128 of ~1,900 pages, "every page carries rendered HTML" (14 October 2026),
because `vite build` empties dist/ and the prerender refills it page by page. This asks the
other question: is every page that should be there, there. deploy_site.sh runs both.
"""
import os, re, sys
DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fy28', 'dist')
sm = open(os.path.join(DIST, 'sitemap.xml'), encoding='utf-8').read()
pages = [re.sub(r'^https?://[^/]+', '', u) for u in re.findall(r'<loc>([^<]+)</loc>', sm)]
pages = [p for p in pages if not re.search(r'\.[a-z0-9]+$', p)]
def held(p):
    p = p.rstrip('/')
    return os.path.exists(os.path.join(DIST, 'index.html' if not p else p.lstrip('/') + '.html')) \
        or os.path.exists(os.path.join(DIST, p.lstrip('/'), 'index.html'))
missing = [p for p in pages if not held(p)]
print('%d of %d sitemap pages are in fy28/dist' % (len(pages) - len(missing), len(pages)))
if missing:
    print('MISSING, e.g.: ' + ', '.join(missing[:5]))
    sys.exit(1)
