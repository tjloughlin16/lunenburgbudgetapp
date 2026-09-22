#!/usr/bin/env python3
"""IS `dist/` WHOLLY PRERENDERED, OR WHOLLY NOT? A mixture is the dangerous state.

    python3 scripts/check_prerender.py [--dist PATH]

22 September 2026. A site build was killed four times by memory pressure part way through
prerendering 400 routes, and each time it left `dist/` with SOME routes server-rendered
and some not. Every one of those states looks like a finished build: the files are there,
the sizes are plausible, the sitemap describes them, and nothing downstream compares the
two halves. Deploying one would have published a site where an arbitrary subset of pages
had no HTML at all -- which costs exactly the readers the prerender exists for, and is
invisible to anybody browsing with JavaScript on.

The term for it is a TORN WRITE: an operation interrupted half way leaves a result that
is neither the old thing nor the new one and is usually valid-looking.

What caught it that day was `prerender.mjs` refusing to run on its own output -- a guard
against prerendering twice, which noticed the torn state for an unrelated reason and only
because another run was attempted. Nothing would have caught it on the way to a deploy.

THE CHECK IS THE MIXTURE, NOT THE COUNT. A dist with no prerendering at all is a normal
intermediate state: `npm run build` produces exactly that, and `npm run prerender` turns
it into the finished article. A dist where 112 of 400 pages carry HTML is a build that
died, and there is no legitimate way to reach it.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'fy28', 'dist')
# What Vite ships before anything renders into it. Whitespace varies by build, so the
# test is that the div is EMPTY rather than that it matches a literal string.
EMPTY_ROOT = re.compile(r'<div id="root">\s*</div>')


def classify(path):
    try:
        html = open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return 'unreadable'
    if 'id="root"' not in html:
        return 'not a page'          # _headers, an error page, a hand-written asset
    return 'shell' if EMPTY_ROOT.search(html) else 'prerendered'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dist', default=DIST)
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    if not os.path.isdir(a.dist):
        print('no build at %s — nothing to check' % a.dist)
        return 0

    pages = {}
    for dirpath, _dirs, files in os.walk(a.dist):
        for f in files:
            if f.endswith('.html'):
                p = os.path.join(dirpath, f)
                pages[os.path.relpath(p, a.dist)] = classify(p)

    done = sorted(k for k, v in pages.items() if v == 'prerendered')
    shell = sorted(k for k, v in pages.items() if v == 'shell')
    print('%d pages in %s: %d prerendered, %d empty shells'
          % (len(done) + len(shell), os.path.relpath(a.dist, ROOT), len(done), len(shell)))

    if done and shell:
        print('\nTORN: this build is neither prerendered nor not. A run was interrupted,')
        print('and deploying it publishes %d page(s) with no HTML at all.' % len(shell))
        print('Fix: npm run build && npm run prerender — both, in that order, in one go.')
        for k in shell[:20]:
            print('    empty: %s' % k)
        if len(shell) > 20:
            print('    ... and %d more' % (len(shell) - 20))
        return 1
    if shell:
        print('not prerendered — this is `npm run build` output. Run `npm run prerender`.')
        return 1
    if not done:
        print('no pages found — is this a build directory?')
        return 1
    print('every page carries rendered HTML.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
