"""Fill the DERIVED bucket with our extracted meeting text, and stage a deploy without it.

    python3 scripts/sync_derived.py --dry-run   # what would be uploaded, changed, orphaned
    python3 scripts/sync_derived.py --push      # upload, then confirm by LISTING the bucket
    python3 scripts/sync_derived.py --check     # every file in dist matches the bucket (exit 1 if not)
    python3 scripts/sync_derived.py --stage DIR # copy fy28/dist to DIR without those files

WHY. Cloudflare Pages refuses a deployment past 20,000 files, and on 21 October 2026 the
build was 20,351 -- 12,175 of them our `.txt` reading of the town's meeting documents
(`/docs/minutes/text/`). Those are OURS, so they may change when an extractor improves, and
they go in `lunenburg-derived`, an UNLOCKED bucket, not beside the town's documents in the
locked archive (TJ, 22 October 2026). functions/docs/_bucket.js `fromDerived` serves them at
the same addresses; deploy_site.sh runs --push, --check and --stage before every deploy.

THE BUCKET IS THE TRUTH, NOT A STATE FILE. Whether an object is current is answered by
listing the bucket and comparing each object's etag -- the MD5 of a single-part upload -- to
the MD5 of the file in dist. A PUT that reported success is a claim about the PUT.

Keys are the published path under /docs/, e.g. `minutes/text/select-board/2026-10-06-minutes-8052.txt`.
An object in the bucket that dist no longer holds is reported as an orphan and left alone:
the 410 for a withdrawn document is answered before any bucket is read, so an orphan is
never served in its place, and deleting is a decision rather than a side effect of a sync.
"""
import argparse
import hashlib
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_storage as AS  # noqa: E402

DERIVED_BUCKET = 'lunenburg-derived'
ROOT = AS.ROOT
DIST = os.path.join(ROOT, 'fy28', 'dist')
PREFIX = 'minutes/text/'          # the published path under /docs/, and the key
LOCAL = os.path.join(DIST, 'docs', PREFIX)


def local_files():
    """{key: path} for every .txt the build wrote under /docs/minutes/text/."""
    out = {}
    for d, _, names in os.walk(LOCAL):
        for n in names:
            if n.endswith('.txt'):
                p = os.path.join(d, n)
                out[PREFIX + os.path.relpath(p, LOCAL).replace(os.sep, '/')] = p
    return out


def md5(path):
    with open(path, 'rb') as fh:
        return hashlib.md5(fh.read()).hexdigest()


def remote():
    """{key: etag} as the bucket itself reports it."""
    return {o['key']: (o.get('etag') or '').strip('"')
            for o in AS.list_objects(PREFIX, bucket=DERIVED_BUCKET)}


def plan():
    loc = local_files()
    if not loc:
        sys.exit('fy28/dist holds no %s files -- build the site first' % PREFIX)
    rem = remote()
    sums = {}
    with ThreadPoolExecutor(8) as ex:
        for k, h in zip(loc, ex.map(md5, loc.values())):
            sums[k] = h
    new = sorted(k for k in loc if k not in rem)
    changed = sorted(k for k in loc if k in rem and rem[k] != sums[k])
    orphans = sorted(k for k in rem if k not in loc)
    return loc, new, changed, orphans


def put(key, path):
    with open(path, 'rb') as fh:
        body = fh.read()
    AS._request('PUT', AS._object_url(key, DERIVED_BUCKET), data=body,
                headers={'Content-Type': 'text/plain; charset=utf-8',
                         'Content-Length': str(len(body))})


def report(loc, new, changed, orphans):
    print('%d files in dist: %d new to the bucket, %d changed, %d current; %d orphans in the bucket'
          % (len(loc), len(new), len(changed), len(loc) - len(new) - len(changed), len(orphans)))
    for k in orphans[:20]:
        print('  orphan (left alone):', k)


def stage(dest):
    """A copy of dist without the files the bucket serves. Hard links, so it costs no space
    and dist itself -- which the sitemap, search and prerender checks read -- stays whole."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    skip = os.path.join('docs', 'minutes', 'text') + os.sep
    n = 0
    for d, _, names in os.walk(DIST):
        rel = os.path.relpath(d, DIST)
        for name in names:
            r = os.path.normpath(os.path.join(rel, name))
            if r.startswith(skip) and name.endswith('.txt'):
                continue
            os.makedirs(os.path.join(dest, rel), exist_ok=True)
            os.link(os.path.join(d, name), os.path.join(dest, r))
            n += 1
    print('staged %d files in %s (Pages allows 20,000)' % (n, dest))
    if n > 20000:
        sys.exit('NOT DEPLOYABLE: %d files is past the limit' % n)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry-run', action='store_true')
    g.add_argument('--push', action='store_true')
    g.add_argument('--check', action='store_true')
    g.add_argument('--stage', metavar='DIR')
    a = ap.parse_args()
    if a.stage:
        return stage(a.stage)
    loc, new, changed, orphans = plan()
    report(loc, new, changed, orphans)
    if a.check:
        return 1 if (new or changed) else 0
    if a.dry_run:
        return 0
    todo = new + changed
    with ThreadPoolExecutor(4) as ex:
        for i, _ in enumerate(ex.map(lambda k: put(k, loc[k]), todo), 1):
            if i % 500 == 0:
                print('  %d of %d uploaded' % (i, len(todo)), flush=True)
    loc, new, changed, orphans = plan()
    print('after the push, read back by listing:')
    report(loc, new, changed, orphans)
    return 1 if (new or changed) else 0


if __name__ == '__main__':
    sys.exit(main())
