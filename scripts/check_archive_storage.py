#!/usr/bin/env python3
"""Does the bucket hold what the manifest says it holds, and nothing else?

    python3 scripts/check_archive_storage.py [--deep] [--prefix P]

**Reconciles both ways**, because each direction catches a different mistake:

  * in the manifest, not in the bucket -- a document the site will offer and the bucket
    cannot serve. This is the one a visitor meets as a 404.
  * in the bucket, not in the manifest -- an object nothing describes. The bucket lock
    means it can never be removed, so the archive is stuck with it and the honest thing
    is to say so out loud rather than let it sit there unexplained.
  * in both, different bytes -- our copy and the archive's copy have diverged, which is
    the failure this whole project is built against.

**It asks the bucket, never the push log.** `sync_archive.py` keeps a cache of what it
believes it uploaded; this reads none of it. A summary of a run is a claim about the run,
and rule 13 is that something derived must never be quoted as though it were observed.

**Two depths.** By default it compares size and the object's etag, which for a single-part
upload is the MD5 of the bytes -- a full listing costs four requests and no downloads.
`--deep` fetches every object and compares its sha256, which is the real check and moves
1.5 GB, so it is run occasionally rather than in the build.

**Drift means different things eitherside of one line.** A publisher's document does not
change, so drift on one is always a defect. Our extracted text and derived CSVs do change,
and the bucket cannot accept the new version -- the lock refuses an overwrite -- so drift
there means the bucket holds an older rendering. That is reported separately and in those
words, never folded into the failures, because a check that cries wolf on the expected
case stops being read.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_storage as A  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--deep', action='store_true',
                   help='download every object and compare sha256')
    p.add_argument('--prefix', default='', help='limit to one part of the archive')
    args = p.parse_args()

    manifest = A.read_manifest()
    if not manifest:
        sys.exit(f'No manifest at {A.MANIFEST}. Run sync_archive.py --manifest.')
    if args.prefix:
        manifest = {k: v for k, v in manifest.items() if k.startswith(args.prefix)}

    print(f'manifest {len(manifest)} objects, '
          f'{sum(int(r["bytes"]) for r in manifest.values()) / 1e9:.2f} GB')
    objects = {o['key']: o for o in A.list_objects(args.prefix)}
    print(f'bucket   {len(objects)} objects, '
          f'{sum(o["size"] for o in objects.values()) / 1e9:.2f} GB\n')

    missing = sorted(set(manifest) - set(objects))
    orphans = sorted(set(objects) - set(manifest))
    wrong_size, drift, stale, uncomparable = [], [], [], []

    for key in sorted(set(manifest) & set(objects)):
        row, obj = manifest[key], objects[key]
        if obj['size'] != int(row['bytes']):
            # Same split as everywhere else: a published document that is a different
            # size is a defect; one of ours is a rendering we have since redone, and the
            # lock forbids replacing it. Size was the one place this check still treated
            # the two alike, and it reported MANIFEST.md -- a file we had just rewritten
            # on purpose -- as a failure.
            (wrong_size if A.frozen(key) else stale).append(
                (key, f'{obj["size"]:,} B', f'{int(row["bytes"]):,} B'))
            continue
        etag = (obj.get('etag') or '').strip('"')
        if '-' in etag:
            # A multipart upload's etag is a hash of the part hashes, not of the bytes.
            # Nothing can be concluded from it without downloading the object.
            uncomparable.append(key)
            continue
        if etag != row['etag_md5']:
            (drift if A.frozen(key) else stale).append((key, etag, row['etag_md5']))

    if args.deep:
        print('--deep: reading every object back out of the bucket...')
        deep_bad = []
        for i, key in enumerate(sorted(set(manifest) & set(objects)), 1):
            got, _, n = A.get_object(key)
            if got != manifest[key]['sha256']:
                target = deep_bad if A.frozen(key) else stale
                target.append((key, got, manifest[key]['sha256']))
            if i % 200 == 0:
                print(f'  {i}/{len(objects)}', flush=True)
        drift.extend(deep_bad)
        uncomparable = []

    def report(title, rows, fmt):
        if rows:
            print(f'{title}: {len(rows)}')
            for r in rows[:20]:
                print('  ' + fmt(r))
            if len(rows) > 20:
                print(f'  ... and {len(rows) - 20} more')
            print()

    report('IN THE MANIFEST, NOT IN THE BUCKET', missing, lambda k: k)
    report('IN THE BUCKET, IN NO MANIFEST', orphans, lambda k: k)
    report('SIZE DIFFERS', wrong_size,
           lambda r: f'{r[0]}  bucket {r[1]}, disk {r[2]}')
    report('BYTES DIFFER -- a published document is not our copy of it', drift,
           lambda r: f'{r[0]}  bucket {r[1]}  disk {r[2]}')
    report('THE BUCKET HOLDS AN OLDER RENDERING -- ours, re-derived since it was '
           'uploaded.\n  The lock forbids replacing it; the current version is in git '
           'and is what the site serves', stale,
           lambda r: f'{r[0]}  bucket {r[1]}  disk {r[2]}')
    if uncomparable:
        print(f'NOT COMPARED without --deep (multipart upload, etag is not a hash of the '
              f'bytes): {len(uncomparable)}')
        for k in uncomparable[:5]:
            print('  ' + k)
        print()

    failures = len(missing) + len(orphans) + len(wrong_size) + len(drift)
    if failures:
        print(f'FAIL: {failures} findings')
        return 1
    print(f'OK: {len(manifest)} manifest rows reconcile with {len(objects)} objects'
          + (f'; {len(stale)} of ours '
             f'{"is an older rendering" if len(stale) == 1 else "are older renderings"} '
             f'in the bucket' if stale else '')
          + ('  (etag comparison; --deep for sha256)' if not args.deep else
             '  (sha256, read back)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
