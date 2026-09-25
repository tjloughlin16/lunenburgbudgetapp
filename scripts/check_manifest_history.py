#!/usr/bin/env python3
"""NO DOCUMENT EVER LEAVES THE INDEX. Checked against the manifest's own history.

    python3 scripts/check_manifest_history.py [--commits N]

Exit 0 means every publisher document the manifest has EVER named, within the window
checked, is still named. Exit 1 means one is not, and an object in the bucket has been
orphaned.

WHY THIS EXISTS. On 21 and again on 23 September 2026 the daily refresh added documents to
the index and an interactive session removed them:

    ac033301  Daily refresh, 2026-09-21   added 27 meeting documents
    c28c8d2b  an interactive session      removed them
    8fba3d31  Daily refresh, 2026-09-23   added 33 more
    712f2009  an interactive session      removed them

39 documents in all. `sync_archive.py --manifest` rebuilt the index from whatever the
current tree held, and the refresh works in a second worktree where the gitignored
documents stay -- so a session in the other tree found them absent and dropped their rows.

**A DROPPED ROW DOES NOT DELETE THE OBJECT. IT ORPHANS IT.** The bucket forbids deletion
and overwriting for ten years and does not allow listing, so the manifest is the only thing
that can name what is in there. 33 of the 39 were already byte-verified in R2 and became
unreachable: present, permanent, and unfindable.

**AND NOTHING WOULD HAVE CAUGHT IT.** `check_archive_storage.py` reconciles the manifest
against the bucket, so it compares two things that both lacked the row. `--manifest` is now
append-only for frozen keys, which stops the cause -- but a hand edit, a bad merge or a
future script could still drop one, and the writer that refuses is not the same thing as a
check that notices. This is the check that notices.

WHAT IT CANNOT SEE, stated rather than implied. It reads the last N commits that touched
the manifest, so a row dropped before that window and never restored is outside it. The
window is printed on every run with the date it reaches back to, because a check whose
coverage is invisible invites exactly the mistake it exists to prevent -- a clean result
read as "nothing was ever dropped" when it means "nothing was dropped in the part I looked
at."
"""
import argparse
import csv
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402

ROOT = os.path.dirname(HERE)
REL = 'sources/data/archive-manifest.csv'
PUSH_STATE = os.path.join(ROOT, 'sources', 'data', 'archive-push-state.csv')
# THE ONLY POSSIBLE REMEDY FOR AN ORPHAN, because the bucket forbids deletion for ten
# years: write it down. A key that was pushed and then left the index cannot be removed and
# cannot be found by listing, so the manifest alone stops describing the bucket. This
# register plus the manifest together describe it again -- the same move
# `document-defects.csv` makes for a document that cannot be corrected.
ORPHANS = os.path.join(ROOT, 'sources', 'data', 'archive-orphans.csv')
ORPHAN_FIELDS = ['key', 'sha256', 'superseded_by', 'last_indexed_at',
                 'last_indexed_date', 'commit_subject', 'why']


def git(*args):
    return subprocess.run(['git'] + list(args), cwd=ROOT, capture_output=True,
                          text=True).stdout


def keys_at(ref):
    text = git('show', '%s:%s' % (ref, REL))
    if not text:
        return set()
    return {r['key'] for r in csv.DictReader(io.StringIO(text))
            if r.get('key') and A.frozen(r['key'])}


def rows_at(ref):
    """The full historical rows, so an orphan's sha256 can be recovered."""
    text = git('show', '%s:%s' % (ref, REL))
    if not text:
        return {}
    return {r['key']: r for r in csv.DictReader(io.StringIO(text)) if r.get('key')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--record', action='store_true',
                    help='register an orphan that cannot be undone, so the bucket stays '
                         'fully described')
    ap.add_argument('--commits', type=int, default=40,
                    help='how many commits that touched the manifest to look back over')
    a = ap.parse_args()

    log = [l.split('\t') for l in
           git('log', '--format=%H\t%ad\t%s', '--date=short', '-n', str(a.commits),
               '--', REL).strip().splitlines() if l]
    if not log:
        print('no manifest history to check')
        return 0

    now = keys_at('HEAD')
    # The manifest on disk, not just at HEAD: a drop that is staged or uncommitted is the
    # one worth catching BEFORE it becomes history.
    on_disk = set()
    p = os.path.join(ROOT, REL)
    if os.path.exists(p):
        with open(p, encoding='utf-8') as fh:
            on_disk = {r['key'] for r in csv.DictReader(fh)
                       if r.get('key') and A.frozen(r['key'])}
    current = now | on_disk if not on_disk else on_disk

    pushed = set()
    if os.path.exists(PUSH_STATE):
        with open(PUSH_STATE, encoding='utf-8') as fh:
            pushed = {r['key'] for r in csv.DictReader(fh) if r.get('key')}
    known = set()
    if os.path.exists(ORPHANS):
        with open(ORPHANS, encoding='utf-8') as fh:
            known = {r['key'] for r in csv.DictReader(fh) if r.get('key')}

    lost = {}
    for sha, date, subject in log:
        for k in keys_at(sha) - current:
            lost.setdefault(k, (sha[:8], date, subject))

    # TWO KINDS, AND ONLY ONE IS A PROBLEM. A key that left the index having NEVER been
    # pushed is a RE-FILE: the archive renamed a document, the bucket never held the old
    # name, and nothing is orphaned. This archive re-files on purpose -- it is keyed on
    # provenance and `views/` exists for the rest -- so that must not read as data loss.
    #
    # A key that WAS pushed and then left the index is an ORPHAN: the object is in a bucket
    # that cannot be listed, under a name nothing records. It cannot be deleted for ten
    # years. All eleven found on 25 September 2026 came from one cause -- the filename slug
    # changed how it renders an apostrophe (`town-manager-s` to `town-manager-39-s`), so a
    # rename in an immutable store duplicated them permanently.
    orphans = {k: v for k, v in lost.items() if k in pushed}
    refiled = {k: v for k, v in lost.items() if k not in pushed}
    new_orphans = {k: v for k, v in orphans.items() if k not in known}

    oldest = log[-1]
    print('checked %d commit(s) that touched the manifest, back to %s (%s)'
          % (len(log), oldest[1], oldest[2][:56]))
    print('%d frozen key(s) in the index now; %d orphan(s) already registered'
          % (len(current), len(known)))
    if refiled:
        print('%d key(s) left the index and were never pushed -- re-filed, nothing '
              'orphaned' % len(refiled))

    if a.record and new_orphans:
        rows = []
        if os.path.exists(ORPHANS):
            with open(ORPHANS, encoding='utf-8') as fh:
                rows = [r for r in csv.DictReader(fh) if r.get('key')]
        # WHICH KEY HOLDS THE DOCUMENT NOW, MATCHED BY CONTENT. A name is a guess -- these
        # eleven differ only in how a slug renders an apostrophe -- but a sha256 is the
        # document. So the register says `superseded_by` where the same bytes are held under
        # another key, and leaves it EMPTY where they are not, which is the difference
        # between a permanent duplicate and something nobody holds any more.
        by_sha = {}
        for key, row in A.read_manifest().items():
            if row.get('sha256'):
                by_sha.setdefault(row['sha256'], key)
        for k, (sha_commit, date, subject) in sorted(new_orphans.items()):
            was = rows_at(sha_commit).get(k, {})
            digest = was.get('sha256', '')
            twin = by_sha.get(digest, '')
            rows.append({
                'key': k, 'sha256': digest, 'superseded_by': twin,
                'last_indexed_at': sha_commit, 'last_indexed_date': date,
                'commit_subject': subject[:90],
                'why': ('a duplicate: the same bytes are held under another key, so this '
                        'object is a rename the bucket could not take back'
                        if twin else
                        'pushed to the bucket, then dropped from the manifest, and the '
                        'bytes are held under no other key. The object is the only copy '
                        'and nothing but this row names it.')})
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=ORPHAN_FIELDS, lineterminator='\n')
        w.writeheader()
        for r in sorted(rows, key=lambda r: r['key']):
            w.writerow({k: r.get(k, '') for k in ORPHAN_FIELDS})
        open(ORPHANS, 'w', encoding='utf-8', newline='').write(buf.getvalue())
        print('recorded %d orphan(s) in %s' % (len(new_orphans),
                                               os.path.relpath(ORPHANS, ROOT)))
        return 0

    if not new_orphans:
        print('ok: no document has left the index unaccounted for within that window.')
        return 0

    print('%d OBJECT(S) ORPHANED IN THE BUCKET -- pushed, then dropped from the index. The '
          'bucket cannot be listed, so nothing can find them, and the ten-year lock means '
          'they cannot be removed:' % len(new_orphans))
    for k, (sha, date, subject) in sorted(new_orphans.items())[:25]:
        print('    %s\n        last indexed at %s %s  %s' % (k, sha, date, subject[:52]))
    if len(new_orphans) > 25:
        print('    ... and %d more' % (len(new_orphans) - 25))
    print('  If the document is still held under another key, this is a rename and the only '
          'remedy is to record it: re-run with --record.\n'
          '  If it is NOT held under another key, restore its manifest row from the commit '
          'named above -- the bytes are in the bucket.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
