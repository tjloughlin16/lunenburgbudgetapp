#!/usr/bin/env python3
"""Move the archive's bytes between this disk and the public R2 bucket.

    python3 scripts/sync_archive.py --manifest          # hash every file under sources/
    python3 scripts/sync_archive.py --push [--only S] [--limit N] [--dry-run]
    python3 scripts/sync_archive.py --pull [--only S]   # a fresh clone gets its binaries
    python3 scripts/sync_archive.py --verify-lock KEY   # prove the bucket refuses an overwrite

**Copy, verify, then untrack — in that order, per file.** A push uploads, then reads the
object back out of the bucket and compares its sha256 to the file on disk. Nothing is
recorded as stored until that matches. A failure at any point leaves the file exactly as
it was, which is the state we started in, and the bytes exist in three places throughout:
the bucket, this disk, and the 3.1 GB backup.

**Reading back is the whole point.** An upload that returned 200 is a claim about the
upload; the archive's claim is about the object. Rule 13 in CLAUDE.md is that something
derived must never be quoted as though it were observed, and "the PUT succeeded" is
derived. So the hash compared here is computed from bytes that came back over the wire.

**The bucket lock makes every write one-way.** `immutable-sources` blocks deletion *and*
overwriting for 3650 days across all prefixes. So:

  * a key that is absent is uploaded
  * a key that is present with the same sha256 is left alone and counted as done
  * a key that is present with a DIFFERENT sha256 is an error and is not touched. It
    cannot be corrected in place; the answer is a new key and a repointed manifest

`--push` is resumable: `sources/data/archive-push-state.csv` records what has been
uploaded and read back, so a second run does not re-download 1.4 GB to rediscover it.
That file is a cache and a claim, not a source. `check_archive_storage.py` asks the bucket
itself and never reads it.
"""
import argparse
import concurrent.futures
import csv
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_storage as A  # noqa: E402

STATE_COLS = ['key', 'bytes', 'sha256', 'verified_at']


def build_manifest(quiet=False):
    """Hash every file under sources/ and write the manifest.

    The manifest is the index into the bucket, and it is the reason it stays in git while
    the binaries leave: held only in R2, a fresh clone would have to ask the network what
    exists before it could ask for any of it.
    """
    upstream = A.upstream_urls()
    keys = A.walk_sources()
    rows, total = [], 0
    for i, key in enumerate(keys, 1):
        sha, md5, n = A.hash_file(A.local_path(key))
        rows.append({'key': key, 'bytes': n, 'sha256': sha, 'etag_md5': md5,
                     'upstream': upstream.get(key, '')})
        total += n
        if not quiet and i % 500 == 0:
            print(f'  hashed {i}/{len(keys)}', flush=True)
    A.write_manifest(rows)
    if not quiet:
        print(f'{A.MANIFEST}: {len(rows)} files, {total / 1e9:.2f} GB')
    return rows


def read_state():
    if not os.path.exists(A.STATE):
        return {}
    with open(A.STATE, newline='') as fh:
        return {r['key']: r for r in csv.DictReader(fh)}


def write_state(state):
    tmp = A.STATE + '.tmp'
    with open(tmp, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=STATE_COLS)
        w.writeheader()
        for key in sorted(state):
            w.writerow({c: state[key].get(c, '') for c in STATE_COLS})
    os.replace(tmp, A.STATE)


def push(only=None, limit=None, dry_run=False, recheck=False, workers=6,
         frozen_only=False):
    rows = A.read_manifest()
    if not rows:
        sys.exit('No manifest. Run --manifest first.')
    state = read_state()
    todo = [r for r in rows.values() if not only or only in r['key']]
    if frozen_only:
        todo = [r for r in todo if A.frozen(r['key'])]
    if not recheck:
        todo = [r for r in todo
                if state.get(r['key'], {}).get('sha256') != r['sha256']]
    todo.sort(key=lambda r: r['key'])
    if limit:
        todo = todo[:limit]
    if not todo:
        print('Nothing to push: every manifest row is already stored and verified.')
        return 0

    nbytes = sum(int(r['bytes']) for r in todo)
    print(f'{len(todo)} objects, {nbytes / 1e9:.2f} GB'
          + (' (dry run)' if dry_run else ''), flush=True)
    if dry_run:
        for r in todo[:20]:
            print(f'  would push {r["key"]} ({int(r["bytes"]):,} B)')
        if len(todo) > 20:
            print(f'  ... and {len(todo) - 20} more')
        return 0

    lock = threading.Lock()
    counts = {'uploaded': 0, 'already': 0, 'superseded': 0, 'failed': 0, 'done': 0}
    failures, superseded = [], []
    started = time.time()

    def one(row):
        key, want = row['key'], row['sha256']
        path = A.local_path(key)
        if not os.path.exists(path):
            return key, 'failed', 'in the manifest, not on disk'
        try:
            got, _, _ = A.get_object(key)
            if got == want:
                return key, 'already', ''
            if not A.frozen(key):
                # Ours, and re-derived since it was uploaded. The lock forbids replacing
                # it, and nothing needs replacing: the current version is in git and is
                # what the site serves, because build assets are checked before the
                # bucket. Reported, not failed -- a push that failed every time an
                # extractor improved would stop being run.
                return key, 'superseded', (
                    f'the bucket holds an older rendering ({got[:12]}..., disk is '
                    f'{want[:12]}...)')
            return key, 'failed', (
                f'the bucket holds different bytes under this key\n'
                f'      bucket {got}\n      disk   {want}\n'
                f'      This is a published document, so a difference is a defect. The '
                f'lock forbids correcting it: upload under a new key and repoint the '
                f'manifest.')
        except A.NotFound:
            pass
        except Exception as e:                                  # noqa: BLE001
            # Could not find out whether the object is there. Not knowing is not the same
            # as knowing it is absent, and uploading on a guess is how a locked bucket
            # acquires an object nobody meant to put in it.
            return key, 'failed', f'could not check the bucket: {e}'
        try:
            A.put_object(key, path)
        except Exception as e:                                  # noqa: BLE001
            return key, 'failed', f'upload failed: {e}'
        try:
            got, _, n = A.get_object(key)
        except Exception as e:                                  # noqa: BLE001
            return key, 'failed', f'uploaded but could not read back: {e}'
        if got != want:
            return key, 'failed', (
                f'read back as {got}, expected {want} -- the object in the bucket is '
                f'not the file on disk')
        if n != int(row['bytes']):
            return key, 'failed', f'read back {n} bytes, expected {row["bytes"]}'
        return key, 'uploaded', ''

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for key, outcome, detail in pool.map(one, todo):
            with lock:
                counts[outcome] += 1
                counts['done'] += 1
                if outcome == 'failed':
                    failures.append((key, detail))
                    print(f'  FAILED {key}\n      {detail}', flush=True)
                elif outcome == 'superseded':
                    superseded.append((key, detail))
                else:
                    state[key] = {
                        'key': key,
                        'bytes': rows[key]['bytes'],
                        'sha256': rows[key]['sha256'],
                        'verified_at': time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                                     time.gmtime())}
                if counts['done'] % 50 == 0:
                    write_state(state)
                    rate = counts['done'] / max(1e-9, time.time() - started)
                    print(f'  {counts["done"]}/{len(todo)}  '
                          f'uploaded {counts["uploaded"]}  already {counts["already"]}  '
                          f'failed {counts["failed"]}  ({rate:.1f}/s)', flush=True)

    write_state(state)
    print(f'\nuploaded {counts["uploaded"]}  already there {counts["already"]}  '
          f'older rendering in the bucket {counts["superseded"]}  '
          f'failed {counts["failed"]}  in {time.time() - started:.0f}s')
    if superseded:
        print(f'\n{len(superseded)} of our own files have been re-derived since they '
              f'were uploaded.\nThe bucket keeps the older copy and cannot be updated; '
              f'git and the site have the current one:')
        for key, detail in superseded[:10]:
            print(f'  {key}')
        if len(superseded) > 10:
            print(f'  ... and {len(superseded) - 10} more')
    if failures:
        print('\nFailures:')
        for key, detail in failures:
            print(f'  {key}: {detail.splitlines()[0]}')
    return 1 if failures else 0


def pull(only=None, workers=6):
    """Fetch every manifest row missing from this disk, and verify each sha256.

    This is what makes a fresh clone buildable: the binaries are no longer in git, so
    `sources/` arrives with its manifests, its extracted text and holes where 371 PDFs
    and spreadsheets should be. Reads from the public URL, so it needs no credential.
    """
    import urllib.request
    rows = A.read_manifest()
    if not rows:
        sys.exit('No manifest. A clone should have one; run --manifest if this is not one.')
    todo = [r for r in rows.values()
            if (not only or only in r['key']) and not os.path.exists(A.local_path(r['key']))]
    if not todo:
        print('Nothing to pull: every file in the manifest is already on disk.')
        return 0
    print(f'{len(todo)} files missing, {sum(int(r["bytes"]) for r in todo) / 1e9:.2f} GB',
          flush=True)
    failures = []

    def one(row):
        key = row['key']
        path = A.local_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.part'
        url = f'{A.PUBLIC_BASE}/{key}'
        # An honest User-Agent, and not optional: r2.dev answers 403 to urllib's default
        # `Python-urllib/3.11`, so the first real recovery this script was asked to do
        # failed nine times over with a permission error against a bucket whose public
        # access was enabled and working.
        req = urllib.request.Request(url, headers={
            'User-Agent': 'lunenburgbudgetproject.org archive sync'})
        try:
            with urllib.request.urlopen(req, timeout=300) as res, open(tmp, 'wb') as fh:
                while True:
                    chunk = res.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
        except Exception as e:                                  # noqa: BLE001
            return key, f'download failed: {e}'
        sha, _, n = A.hash_file(tmp)
        if sha != row['sha256']:
            os.remove(tmp)
            return key, f'downloaded {n} bytes hashing {sha}, manifest says {row["sha256"]}'
        os.replace(tmp, path)
        return key, ''

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (key, err) in enumerate(pool.map(one, todo), 1):
            if err:
                failures.append((key, err))
                print(f'  FAILED {key}: {err}', flush=True)
            if i % 100 == 0:
                print(f'  {i}/{len(todo)}', flush=True)
    print(f'\npulled {len(todo) - len(failures)}, failed {len(failures)}')
    return 1 if failures else 0


def verify_lock(key):
    """Prove the bucket refuses to overwrite an object that is already there.

    The safety story rests on the lock, and asserting it from the dashboard is asserting
    it from a rendering. So it is tested against the bucket -- and tested by re-uploading
    a file's OWN bytes, so that if the lock turns out not to hold, the only thing that
    happens is that an object is replaced by an identical one.
    """
    rows = A.read_manifest()
    if key not in rows:
        sys.exit(f'{key} is not in the manifest')
    path = A.local_path(key)
    got, _, _ = A.get_object(key)
    if got != rows[key]['sha256']:
        sys.exit(f'{key} in the bucket does not match the manifest; not touching it')
    print(f'{key} is in the bucket and matches. Re-uploading its own bytes...')
    try:
        A.put_object(key, path)
    except RuntimeError as e:
        print(f'REFUSED, as the lock promises:\n  {e}')
        return 0
    print('NOT REFUSED. The bucket accepted an overwrite.\n'
          '  The object is unchanged -- it was rewritten with identical bytes -- but the\n'
          '  lock does not do what plans/ARCHIVE-STORAGE.md says it does. Fix the rule\n'
          '  before pushing anything else.')
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--manifest', action='store_true')
    p.add_argument('--push', action='store_true')
    p.add_argument('--pull', action='store_true')
    p.add_argument('--verify-lock', metavar='KEY')
    p.add_argument('--only', metavar='SUBSTRING')
    p.add_argument('--limit', type=int)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--recheck', action='store_true',
                   help='ask the bucket about every object, ignoring the push cache')
    p.add_argument('--frozen', action='store_true',
                   help="only the publishers' own files -- see archive_storage.frozen()")
    p.add_argument('--workers', type=int, default=6)
    args = p.parse_args()

    if args.manifest:
        build_manifest()
        return 0
    if args.verify_lock:
        return verify_lock(args.verify_lock)
    if args.push:
        return push(args.only, args.limit, args.dry_run, args.recheck, args.workers,
                    args.frozen)
    if args.pull:
        return pull(args.only, args.workers)
    p.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
