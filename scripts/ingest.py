#!/usr/bin/env python3
"""ONE DOOR FOR EVERY DOCUMENT THAT ARRIVES. Durable before it is archived.

    import ingest
    ingest.stage(key, blob, upstream)   # validated, written aside, registered
    ingest.secure()                     # pushed, read back, then filed and catalogued
    ingest.land(key, blob, upstream)    # both, for one document

    python3 scripts/ingest.py --status  # what is in flight
    python3 scripts/ingest.py --secure  # finish anything left in flight

TJ, 25 September 2026: *"i want to make sure any file we downoad is ALWAYS saved before we
can even think of deleting it or cleaning a repo..."* and, on why staging need not sit
outside the repository: *"we can back up anything unstaged, just the same way if i send you
a file to ingest, i expect you to back those up until they are fully ingested."*

THE INVARIANT: A DOCUMENT IS IN `sources/` IF AND ONLY IF IT IS IN THE BUCKET.

That is one sentence and it is the whole design. It is an invariant rather than a
procedure, which is the difference between a guarantee and a habit -- and it is checkable
at any moment by `check_archive_backed_up.py` without asking the network.

WHAT IT REPLACES. Fifteen fetchers wrote straight into `sources/`, which is a git working
directory, and the durable copy was the LAST step of the daily run -- `sync_archive.py
--push` at step 10 of 10, with its failure ignored. So the archive made its promise the
moment bytes hit the disk and only kept it an hour later, and everything in between was a
window where a document existed exactly once:

  * six agendas sat in that window unnoticed, fetched 25-30 September;
  * 39 documents were orphaned in the bucket when a second worktree rebuilt the manifest
    from its own partial view;
  * `git clean -fd` would have deleted a fetched `.csv`, which is untracked and not
    ignored;
  * and the write was not atomic, so a crash mid-write left a truncated file sitting at
    the real archival name, indistinguishable from a document except by a hash nothing had
    computed yet.

Every one of those is a consequence of publishing into the archive before saving.

THE THREE STEPS, AND WHY EACH IS WHERE IT IS.

  1. VALIDATE, BEFORE ANYTHING IS KEPT. An R2 object is write-once for ten years: it
     cannot be corrected, only superseded under a new key. So a sign-in page or an error
     page must be caught HERE -- after the push it is permanent. `fetch_agendas.py` already
     sniffed magic bytes for this reason and that check moves in here, where every caller
     gets it.
  2. STAGE, and register it. Bytes go to `build/ingest/<key>` and a row goes into
     `sources/data/ingest-pending.csv`, WHICH IS TRACKED IN GIT. The bytes are not durable
     yet, and the point of the register is that the archive knows something is in flight:
     an interrupted ingest becomes visible and resumable instead of six agendas nobody
     counted. If staging is wiped before the push, the register still names what was lost,
     and a document that never reached the archive is refetchable from the publisher.
  3. SECURE: push, read back, compare, and only then move into `sources/` and write the
     manifest row. The move is `os.replace`, which is atomic on one filesystem, so no
     partial file ever appears at an archival path.

A FAILED PUSH IS NOT A LOST DOCUMENT AND NOT A SILENT ONE. The bytes stay staged, the row
stays pending, and `check_archive_backed_up.py` refuses every destructive operation while
that is true -- so the next run retries rather than the next run destroying.

IT IS IDEMPOTENT. Landing a key the archive already holds with identical bytes does
nothing; landing one it holds with DIFFERENT bytes is refused, because a publisher's own
file does not change and that is a defect to look at rather than a revision to record.
"""
import argparse
import csv
import hashlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402

ROOT = os.path.dirname(HERE)
STAGE = os.path.join(ROOT, 'build', 'ingest')
PENDING = os.path.join(ROOT, 'sources', 'data', 'ingest-pending.csv')
FIELDS = ['key', 'bytes', 'sha256', 'upstream', 'staged_at', 'state', 'note']

# WHAT A REAL DOCUMENT LOOKS LIKE AT ITS FIRST BYTES. Moved here out of
# `fetch_agendas.py`, whose own comment records why it exists: the town's site answers a
# missing file with an HTML error page and HTTP 200, and the test used to be
# `blob.startswith(b'%PDF')` -- so anything that was not a PDF was treated as absent,
# and 39 Word documents the town had published were recorded as missing for months.
# A format is recognised POSITIVELY here, and an unrecognised blob is REFUSED rather
# than stored, because the bucket cannot take a correction later.
MAGIC = [
    (b'%PDF', '.pdf'),
    (b'PK\x03\x04', '.zip-family'),          # docx, xlsx, pptx and plain zip
    (b'\xd0\xcf\x11\xe0', '.ole2'),          # pre-2007 Word and Excel
    (b'{\\rtf', '.rtf'),
    (b'\xff\xd8\xff', '.jpg'),
    (b'\x89PNG', '.png'),
]
# A text document is not recognisable by magic, so it is accepted on its extension and
# refused if it decodes to something that is plainly an error page.
TEXTISH = {'.csv', '.txt', '.md', '.json', '.html', '.htm', '.xml'}
ERROR_PAGE = (b'<title>Error', b'ServiceLogin', b'>Page Not Found<', b'>404 ', b'>403 ')


def sniff(key, blob):
    """(ok, reason). What this document is, or why it is not one."""
    if not blob:
        return False, 'empty response'
    ext = os.path.splitext(key)[1].lower()
    for magic, _name in MAGIC:
        if blob.startswith(magic):
            return True, ''
    if ext in TEXTISH:
        head = blob[:4096]
        for bad in ERROR_PAGE:
            if bad in head:
                return False, 'the publisher answered with an error or sign-in page'
        return True, ''
    return False, ('unrecognised format: first bytes %r. A document the bucket cannot take '
                   'back is not stored on a guess.' % blob[:8])


def _rows():
    if not os.path.exists(PENDING):
        return []
    with open(PENDING, encoding='utf-8') as fh:
        return [r for r in csv.DictReader(fh) if r.get('key')]


def _write(rows):
    os.makedirs(os.path.dirname(PENDING), exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in sorted(rows, key=lambda r: r['key']):
        w.writerow({k: r.get(k, '') for k in FIELDS})
    open(PENDING, 'w', encoding='utf-8', newline='').write(buf.getvalue())


def pending():
    return _rows()


def _staged_path(key):
    return os.path.join(STAGE, key)


def _atomic_write(path, blob):
    """Write beside the target and rename onto it -- never a partial file at a real name."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.part'
    with open(tmp, 'wb') as fh:
        fh.write(blob)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def stage(key, blob, upstream='', when=''):
    """Validate a document and put it in flight. Returns (ok, reason)."""
    ok, why = sniff(key, blob)
    if not ok:
        return False, why
    sha = hashlib.sha256(blob).hexdigest()

    held = A.local_path(key)
    if os.path.exists(held):
        have = A.hash_file(held)[0]
        if have == sha:
            return True, 'already held, identical'
        return False, ('the archive already holds %s with different bytes (%s on disk, %s '
                       'arriving). A publisher’s own file does not change: that is a '
                       'defect, not a revision.' % (key, have[:12], sha[:12]))

    _atomic_write(_staged_path(key), blob)
    rows = [r for r in _rows() if r['key'] != key]
    rows.append({'key': key, 'bytes': str(len(blob)), 'sha256': sha, 'upstream': upstream,
                 'staged_at': when or __import__('datetime').datetime.now().isoformat(timespec='seconds'),
                 'state': 'staged', 'note': ''})
    _write(rows)
    return True, ''


def secure(quiet=False):
    """Push everything in flight, read it back, then file it and catalogue it.

    NOTHING IS FILED UNTIL ITS BYTES ARE IN THE BUCKET AND HAVE BEEN READ BACK. That
    ordering is the invariant; a caller cannot get it wrong because there is no other way
    into `sources/`.
    """
    rows = _rows()
    todo = [r for r in rows if r['state'] in ('staged', 'push-failed')]
    if not todo:
        if not quiet:
            print('nothing in flight')
        return 0, 0
    manifest = dict(A.read_manifest())   # already keyed by key
    done, failed = [], []
    for r in todo:
        key, sp = r['key'], _staged_path(r['key'])
        if not os.path.exists(sp):
            r['state'], r['note'] = 'lost', 'staged bytes are gone; refetch from the publisher'
            failed.append(r)
            continue
        try:
            A.put_object(key, sp)
            back = hashlib.sha256()
            A.get_object(key, sink=back)
            if back.hexdigest() != r['sha256']:
                r['state'] = 'push-failed'
                r['note'] = 'read-back does not match what was sent'
                failed.append(r)
                continue
        except Exception as exc:                       # noqa: BLE001 -- reported, not raised
            r['state'] = 'push-failed'
            r['note'] = '%s: %s' % (type(exc).__name__, str(exc)[:120])
            failed.append(r)
            continue
        # Durable. Only now does it become part of the archive.
        dest = A.local_path(key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.replace(sp, dest)
        manifest[key] = {'key': key, 'bytes': r['bytes'], 'sha256': r['sha256'],
                         'etag_md5': A.hash_file(dest)[1], 'upstream': r.get('upstream', '')}
        done.append(r)
    if done:
        A.write_manifest(sorted(manifest.values(), key=lambda r: r['key']))
    _write([r for r in rows if r['key'] not in {d['key'] for d in done}])
    if not quiet:
        print('secured %d, failed %d' % (len(done), len(failed)))
        for r in failed:
            print('  !! %s -- %s' % (r['key'], r['note']))
    return len(done), len(failed)


def land(key, blob, upstream=''):
    """One document, all the way in. Returns (ok, reason)."""
    ok, why = stage(key, blob, upstream)
    if not ok:
        return False, why
    if why == 'already held, identical':
        return True, why
    done, failed = secure(quiet=True)
    if failed:
        return False, 'staged but not yet in the bucket -- still in flight, nothing lost'
    return True, ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--secure', action='store_true')
    a = ap.parse_args()
    rows = _rows()
    if a.secure:
        done, failed = secure()
        return 1 if failed else 0
    print('%d document(s) in flight' % len(rows))
    for r in rows:
        print('  %-10s %-62s %s' % (r['state'], r['key'][:62], r['note'][:50]))
    return 1 if rows else 0


if __name__ == '__main__':
    sys.exit(main())
