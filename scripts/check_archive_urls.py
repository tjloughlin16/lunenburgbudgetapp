#!/usr/bin/env python3
"""Fetch every document at its published URL and check the bytes that come back.

    python3 scripts/check_archive_urls.py --base https://<preview>.lunenburg-fy28.pages.dev
    python3 scripts/check_archive_urls.py --base https://lunenburgbudgetproject.org --limit 40

**This is the gate.** The binaries left git and left the build on 5 September 2026, and
`/docs/<path>` is a promise: llms.txt publishes 302 of those addresses and tells agents to
cite them, and `documents.json` embeds 1,422 more. Moving where the bytes are kept is only
safe if every one of those addresses still hands back the same document, so this asks each
of them and hashes the answer.

**It hashes the body. It does not trust the status code.** A 200 that returns the app
shell is the soft 404 `_notfound.js` was written against, and a 200 that returns a
sign-in page is what a dead Google Drive link looks like. Neither is distinguishable from
success without comparing the bytes to the manifest -- rule 13, in the smallest form
there is: the status line is derived, the sha256 is observed.

**It also asks WHICH copy answered.** The same URL can be served by a build asset or by
the R2 bucket and the bytes are identical either way, so `_bucket.js` sets
`x-archive-source: r2` on everything it streams. Without that header a run of this could
pass having never touched the bucket -- exercising exactly the path that did not change.
`--expect-bucket` turns that into an assertion for every file the archive freezes.

**Aliases are checked live, not statically.** `check_moved_docs.py` proves each alias
target exists on disk; this proves the deployed site actually answers 301 and that the
address it names then serves the document. A 301 to a 404 is worse than a 404.
"""
import argparse
import concurrent.futures
import hashlib
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_storage as A  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOVED = os.path.join(ROOT, 'fy28', 'functions', 'docs', '_moved.js')

# The published URL for the meeting archive is /docs/minutes/...; the folder, and so the
# bucket key, is meetings/. The same translation `functions/docs/_bucket.js` does, in the
# opposite direction. It is here rather than imported because the JS is what ships.
URL_PREFIX = [('meetings/', 'minutes/')]


def published_url(key):
    for frm, to in URL_PREFIX:
        if key.startswith(frm):
            return '/docs/' + to + key[len(frm):]
    return '/docs/' + key


def fetch(url, timeout=300):
    """Return (status, headers, sha256, nbytes). A redirect is reported, not followed."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={'User-Agent': 'lunenburgbudgetproject.org '
                                                             'archive check'})
    try:
        res = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 307, 308):
            return e.code, e.headers, '', 0
        try:
            e.read()
        except Exception:
            pass
        return e.code, e.headers, '', 0
    sha, n = hashlib.sha256(), 0
    while True:
        chunk = res.read(1 << 20)
        if not chunk:
            break
        sha.update(chunk)
        n += len(chunk)
    return res.status, res.headers, sha.hexdigest(), n


def alias_pairs():
    src = open(MOVED, encoding='utf-8').read()
    prefix = re.findall(r'\["([^"]+)",\s*"([^"]+)"\]', src)
    exact = re.findall(r'^\s*"([^"]+)":\s*"([^"]+)",\s*$', src, re.M)
    return prefix, exact


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base', required=True, help='site root, e.g. a preview deploy URL')
    p.add_argument('--only', help='limit to keys containing this substring')
    p.add_argument('--limit', type=int)
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--expect-bucket', action='store_true',
                   help="fail unless every publisher's file was served from R2")
    p.add_argument('--skip-aliases', action='store_true')
    args = p.parse_args()
    base = args.base.rstrip('/')

    manifest = A.read_manifest()
    rows = [r for r in manifest.values() if not args.only or args.only in r['key']]
    rows.sort(key=lambda r: r['key'])
    if args.limit:
        rows = rows[:args.limit]
    print(f'{base}\n{len(rows)} documents, '
          f'{sum(int(r["bytes"]) for r in rows) / 1e9:.2f} GB\n', flush=True)

    bad, served_by = [], {'r2': 0, 'build': 0}

    def one(row):
        url = base + published_url(row['key'])
        try:
            status, headers, sha, n = fetch(url)
        except Exception as e:                                  # noqa: BLE001
            return row, f'{type(e).__name__}: {e}', None
        src = 'r2' if (headers.get('x-archive-source') == 'r2') else 'build'
        if status != 200:
            return row, f'HTTP {status}', src
        if sha != row['sha256']:
            ctype = headers.get('content-type', '?')
            return row, (f'{n:,} bytes of {ctype} hashing {sha[:16]}..., '
                         f'expected {row["sha256"][:16]}...'), src
        if args.expect_bucket and A.frozen(row['key']) and src != 'r2':
            return row, 'served from the build, not the bucket', src
        return row, None, src

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, (row, err, src) in enumerate(pool.map(one, rows), 1):
            if src:
                served_by[src] += 1
            if err:
                bad.append((row['key'], err))
                print(f'  FAIL {published_url(row["key"])}\n       {err}', flush=True)
            if i % 200 == 0:
                print(f'  {i}/{len(rows)}  ok {i - len(bad)}  failed {len(bad)}',
                      flush=True)

    print(f'\n{len(rows) - len(bad)} of {len(rows)} documents served their own sha256'
          f'  (from the bucket {served_by["r2"]}, from the build {served_by["build"]})')

    alias_bad = []
    if not args.skip_aliases:
        prefix, exact = alias_pairs()
        # One live probe per prefix rule is enough to prove the rule fires; the exact map
        # is small enough to check in full.
        probes = list(exact)
        for frm, to in prefix:
            sample = next((k for k in manifest if k.startswith(to)), None)
            if sample:
                probes.append((frm + sample[len(to):], sample))
        print(f'\n{len(probes)} old addresses, checked live')

        def probe(pair):
            old, new = pair
            status, headers, _, _ = fetch(base + '/docs/' + old)
            if status not in (301, 308):
                return old, f'answered {status}, not a redirect'
            loc = headers.get('location') or ''
            if not loc.endswith('/docs/' + new):
                return old, f'redirects to {loc}, expected /docs/{new}'
            return old, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for old, err in pool.map(probe, probes):
                if err:
                    alias_bad.append((old, err))
                    print(f'  FAIL /docs/{old}\n       {err}', flush=True)
        print(f'{len(probes) - len(alias_bad)} of {len(probes)} old addresses '
              f'still redirect to the document')

    if bad or alias_bad:
        print(f'\nFAIL: {len(bad)} documents, {len(alias_bad)} aliases')
        return 1
    print('\nOK: every published address serves the document the manifest names.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
