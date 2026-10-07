#!/usr/bin/env python3
"""A FULL BACKUP THAT NOTHING IN THIS REPOSITORY CAN DELETE -- taken before anything deletes.

    python3 scripts/backup_snapshot.py               # take a snapshot (both buckets, git, the working tree)
    python3 scripts/backup_snapshot.py --verify DIR  # re-check a snapshot against its own manifest
    python3 scripts/backup_snapshot.py --covers KEY  # is this bucket key in a verified snapshot? (exit 0/1)

TJ, 6 October 2026, agreeing that the archive needs a way to DELETE things: *"we need a full
backup made to make sure we don't lose data. You can make an OOPSY and BOOM, We're screwed."*

THE COPIES WE HAD PROTECT AGAINST A DISK, NOT AGAINST US. Tree, git and the R2 bucket survive
a failed drive. They do not survive a deletion tool with a bug in it, because the bucket is
the thing that tool deletes from. So a snapshot lives OUTSIDE the repository
(~/lunenburg-backups/<timestamp>/ by default), where `git clean`, a branch switch and the
takedown tool cannot reach, and it holds:

  public/     every object in the public bucket, as the bucket lists it
  private/    every object in the private bucket
  repo.bundle `git bundle --all`: every branch and commit
  worktree.tar.gz   every modified or untracked file in the working tree -- several
                    sessions' uncommitted work, which exists nowhere else
  MANIFEST.csv      bucket, key, size, md5, sha256 for every object; VERIFIED.txt only once
                    every object has been re-read from disk and compared

VERIFIED MEANS RE-READ. An object is checked against the bucket's own etag (the MD5 of a
single-part upload) and its size; a multipart etag (`-N` suffix) is checked on size and
recorded with our sha256. A snapshot with any mismatch is left without VERIFIED.txt, and
--covers will not count it.

Only reads from the buckets. Never writes, never deletes.
"""
import argparse
import csv
import datetime as dt
import hashlib
import os
import subprocess
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import archive_storage as A  # noqa: E402

DEST = os.path.expanduser('~/lunenburg-backups')
WORKERS = 6


def fetch(bucket, obj, base):
    key = obj['key']
    path = os.path.join(base, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    want = int(obj.get('size') or 0)
    etag = (obj.get('etag') or '').strip('"')
    if os.path.exists(path) and os.path.getsize(path) == want:
        pass                                    # resumed run: re-verified below, not trusted
    else:
        tmp = path + '.part'
        with open(tmp, 'wb') as fh:
            A.get_object(key, sink=fh, bucket=bucket)
        os.replace(tmp, path)
    blob = open(path, 'rb').read()
    md5 = hashlib.md5(blob).hexdigest()
    ok = len(blob) == want and ('-' in etag or md5 == etag)
    return dict(bucket=bucket, key=key, size=len(blob), md5=md5,
                sha256=hashlib.sha256(blob).hexdigest(), ok='yes' if ok else 'NO')


def safe_fetch(bucket, obj, base):
    """fetch(), but a failure is RETURNED, never raised. On 7 October 2026 the first
    snapshot died at 5.5 of 7.5 GB because one object timed out (HTTP 524) and the
    exception ended the whole run. One slow object must not cost the other 32,000."""
    try:
        return fetch(bucket, obj, base)
    except Exception as e:                       # noqa: BLE001 -- recorded and retried
        return dict(bucket=bucket, key=obj['key'], size='', md5='', sha256='', ok='NO', error=str(e)[:200])


RETRY_PASSES = 3


def take(dest, resume=None):
    stamp = dt.datetime.now().strftime('%Y-%m-%d-%H%M%S')
    snap = resume or os.path.join(dest, stamp)
    os.makedirs(snap, exist_ok=True)
    print('snapshot -> %s' % snap, flush=True)
    rows = []
    for name, bucket in (('public', A.BUCKET), ('private', A.PRIVATE_BUCKET)):
        objs = A.list_objects('', bucket=bucket)
        print('  %s: %d objects, %.2f GB listed' % (bucket, len(objs), sum(int(o.get('size') or 0) for o in objs) / 1e9),
              flush=True)
        base = os.path.join(snap, name)
        done, got = 0, []
        with ThreadPoolExecutor(WORKERS) as pool:
            for r in pool.map(lambda o: safe_fetch(bucket, o, base), objs):
                got.append(r)
                done += 1
                if done % 2000 == 0:
                    print('    %d / %d' % (done, len(objs)), flush=True)
        # Failures get further passes, one at a time and after a pause, before the
        # snapshot is judged.
        byk = {o['key']: o for o in objs}
        for attempt in range(1, RETRY_PASSES + 1):
            failed = [r for r in got if r.get('error')]
            if not failed:
                break
            print('    retry pass %d: %d object(s)' % (attempt, len(failed)), flush=True)
            import time
            time.sleep(20 * attempt)
            redo = {r['key']: safe_fetch(bucket, byk[r['key']], base) for r in failed}
            got = [redo.get(r['key'], r) if r.get('error') else r for r in got]
        rows.extend(got)
    with open(os.path.join(snap, 'MANIFEST.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['bucket', 'key', 'size', 'md5', 'sha256', 'ok', 'error'])
        w.writeheader()
        w.writerows(rows)
    subprocess.run(['git', 'bundle', 'create', os.path.join(snap, 'repo.bundle'), '--all'], cwd=ROOT, check=True,
                   capture_output=True)
    subprocess.run(['git', 'bundle', 'verify', os.path.join(snap, 'repo.bundle')], cwd=ROOT, check=True,
                   capture_output=True)
    changed = subprocess.run(['git', 'ls-files', '-m', '-o', '--exclude-standard', '-z'], cwd=ROOT,
                             capture_output=True, check=True).stdout.decode().split('\0')
    with tarfile.open(os.path.join(snap, 'worktree.tar.gz'), 'w:gz') as tar:
        for f in (c for c in changed if c and os.path.isfile(os.path.join(ROOT, c))):
            tar.add(os.path.join(ROOT, f), arcname=f)
    bad = [r for r in rows if r['ok'] != 'yes']
    if bad:
        print('NOT VERIFIED: %d object(s) did not match their listing, e.g. %s' % (len(bad), bad[0]['key']))
        return 1
    with open(os.path.join(snap, 'VERIFIED.txt'), 'w') as fh:
        fh.write('%s: %d objects re-read and matched; git bundle verified; %d working-tree files archived\n'
                 % (dt.datetime.now().isoformat(timespec='seconds'), len(rows), len([c for c in changed if c])))
    print('VERIFIED: %d objects, git bundle, %d working-tree files' % (len(rows), len([c for c in changed if c])))
    return 0


def verify(snap):
    bad = 0
    for r in csv.DictReader(open(os.path.join(snap, 'MANIFEST.csv'))):
        p = os.path.join(snap, 'public' if r['bucket'] == A.BUCKET else 'private', r['key'])
        if not os.path.exists(p) or hashlib.sha256(open(p, 'rb').read()).hexdigest() != r['sha256']:
            bad += 1
            print('MISSING OR CHANGED', r['bucket'], r['key'])
    print('%s: %s' % (snap, 'ok' if not bad else '%d problem(s)' % bad))
    return 1 if bad else 0


def covers(key, dest=DEST):
    """True if the newest VERIFIED snapshot holds this public-bucket key."""
    snaps = sorted(d for d in os.listdir(dest) if os.path.exists(os.path.join(dest, d, 'VERIFIED.txt'))) \
        if os.path.isdir(dest) else []
    for s in reversed(snaps):
        for r in csv.DictReader(open(os.path.join(dest, s, 'MANIFEST.csv'))):
            if r['bucket'] == A.BUCKET and r['key'] == key and r['ok'] == 'yes':
                return os.path.join(dest, s)
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', default=DEST)
    ap.add_argument('--verify')
    ap.add_argument('--covers')
    ap.add_argument('--resume', help='continue an unverified snapshot directory; every file already there is re-checked, not trusted')
    a = ap.parse_args()
    if a.verify:
        return verify(a.verify)
    if a.covers:
        s = covers(a.covers, a.dest)
        print(s or 'NOT covered by a verified snapshot')
        return 0 if s else 1
    return take(a.dest, a.resume)


if __name__ == '__main__':
    raise SystemExit(main())
