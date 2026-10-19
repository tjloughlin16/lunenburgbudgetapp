#!/usr/bin/env python3
"""TAKING A DOCUMENT BACK OUT OF THE PUBLIC ARCHIVE -- written down, backed up, and checked.

    python3 scripts/takedown.py --status            # every taken-down key: where its bytes are now
    python3 scripts/takedown.py --status --offline  # ...without asking the buckets or the site
    python3 scripts/takedown.py --write-module      # regenerate fy28/functions/docs/_takedowns.js
    python3 scripts/takedown.py --check             # the module reproduces; no tree holds a taken-down key
    python3 scripts/takedown.py --dry-run           # exactly what --delete would do, and whether it may
    python3 scripts/takedown.py --delete            # delete them from the PUBLIC bucket. TJ's call only.
    python3 scripts/takedown.py --delete --key K    # ...only K (repeatable)

TJ, 6 October 2026: *"we HAVE to have a way to delete things. it can't truly be permanent.
thats silly."* And the condition: *"we need a full backup made to make sure we don't lose
data. You can make an OOPSY and BOOM, We're screwed."* The design is
notes/HANDOFF-TAKEDOWN.md; how to use it is notes/process/REMOVING-FROM-THE-ARCHIVE.md.

THREE STEPS, AND THE FIRST TWO NEED NO BUCKET CHANGE.

  1. THE REGISTER, `sources/data/takedowns.csv`. One row per key: its sha256, the reason (in
     words fit to print -- the 410 shows it), who decided and when, the state, the public
     replacement if there is one, and where the raw is held privately. States:
     `stopped serving` -> `deleted`.
  2. STOP SERVING. This script writes the register into `fy28/functions/docs/_takedowns.js`
     -- generated, never read at runtime, the `_tablesizes.js` pattern -- and `/docs/<key>`
     answers 410 Gone with the reason once that is DEPLOYED. `--check` fails if the module is
     stale, and is run by check_generated.py and by deploy_site.sh before a deploy.
  3. DELETE (`--delete`). Refuses unless, for every key:
       * the register says `stopped serving`, and the live site already answers 410 for it;
       * the raw is in the PRIVATE bucket and reads back to the registered sha256;
       * `backup_snapshot.py --covers <key>` finds it in a VERIFIED snapshot, and the
         snapshot's file hashes to the registered sha256;
       * the public bucket lists it, with the etag the manifest records;
       * check_archive_backed_up.py is green (nothing in flight, nothing unbacked).
     Then: save the lock configuration, lift it, DELETE each object, confirm each is gone
     BY LISTING, and -- in a `finally`, on every path -- put the saved configuration back
     and confirm it reads back identical. Only then the register (`deleted`), the manifest
     (row removed) and archive-orphans.csv (row added, so check_manifest_history.py knows
     the row left on purpose).

R2 ANSWERS A DELETE ON A LOCKED OBJECT WITH SUCCESS AND KEEPS THE OBJECT (found 5 October
2026). So the DELETE response is never read as evidence. Gone means a listing of the exact
key comes back without it.

THE LOCK IS SET THROUGH THE REST API, not wrangler's prompts. `GET .../lock` returns the
configuration as `{"rules": [...]}`, and `PUT .../lock` with that same body restores it
exactly -- the body `wrangler r2 bucket lock set --file` takes. Lifting it is a PUT of
`{"rules": []}`. The restored configuration is compared to the saved one field by field,
and `wrangler r2 bucket lock list` is printed as a second, independent reading.

Never touches the private bucket except to READ the raw back. Never deletes anything there.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402

ROOT = os.path.dirname(HERE)
REGISTER = A.TAKEDOWNS
MODULE = os.path.join(ROOT, 'fy28', 'functions', 'docs', '_takedowns.js')
ORPHANS = os.path.join(A.SRC, 'data', 'archive-orphans.csv')
ORPHAN_FIELDS = ['key', 'sha256', 'superseded_by', 'last_indexed_at', 'last_indexed_date',
                 'commit_subject', 'why']
COLS = ['key', 'sha256', 'bytes', 'reason', 'decided_by', 'decided_on', 'state',
        'superseded_by', 'private_key', 'deleted_on', 'note']
STATES = ('stopped serving', 'deleted')
SITE = 'https://lunenburgbudgetproject.org'
LOCK_URL = A.API + '/lock'
UA = 'lunenburgbudgetproject-takedown/1 (+https://lunenburgbudgetproject.org)'


# --- the register -------------------------------------------------------------------------

def load():
    if not os.path.exists(REGISTER):
        return []
    with open(REGISTER, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def save(rows):
    """Rewrite the register in place, re-read first by the caller. LF, as committed."""
    tmp = REGISTER + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in COLS})
    os.replace(tmp, REGISTER)


def doc_path(key):
    """The published /docs/ path for a bucket key -- the inverse of _bucket.js bucketKey()."""
    return ('minutes/' + key[len('meetings/'):]) if key.startswith('meetings/') else key


# --- the module the site reads -------------------------------------------------------------

def render_module(rows):
    entries = {}
    for r in sorted(rows, key=lambda r: r['key']):
        entries[r['key']] = {
            'reason': r['reason'],
            'decided_on': r['decided_on'],
            'state': r['state'],
            'replacement': ('/docs/' + doc_path(r['superseded_by'])) if r.get('superseded_by') else '',
        }
    body = json.dumps(entries, indent=2, ensure_ascii=False, sort_keys=True)
    return ('// GENERATED by scripts/takedown.py from sources/data/takedowns.csv. Do not edit.\n'
            '// Every bucket key here answers 410 Gone at /docs/<path>, with its reason.\n'
            '// `python3 scripts/takedown.py --check` fails if this no longer matches the register.\n'
            f'export const TAKEN_DOWN = {body}\n')


def write_module(rows=None):
    text = render_module(load() if rows is None else rows)
    tmp = MODULE + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, MODULE)
    print(f'wrote {os.path.relpath(MODULE, ROOT)}  ({len(load() if rows is None else rows)} key(s))')


def problems_offline(rows):
    """Everything that can be wrong without asking the network."""
    out = []
    seen = set()
    manifest = A.read_manifest()
    for r in rows:
        k = r['key']
        if k in seen:
            out.append(f'{k}: registered twice')
        seen.add(k)
        if r['state'] not in STATES:
            out.append(f'{k}: unknown state {r["state"]!r}')
        if len(r.get('sha256', '')) != 64:
            out.append(f'{k}: no sha256')
        if not r.get('reason') or not r.get('decided_by') or not r.get('decided_on'):
            out.append(f'{k}: a takedown needs a reason, who decided and when')
        if not r.get('private_key'):
            out.append(f'{k}: no private copy named -- the raw must be held before it is taken down')
        if os.path.exists(A.local_path(k)):
            out.append(f'{k}: taken down but present in sources/ -- move it out (the raw is private)')
        if r['state'] == 'deleted' and k in manifest:
            out.append(f'{k}: deleted but the manifest still names it')
        if r['state'] == 'stopped serving' and k in manifest and \
                manifest[k].get('sha256') and manifest[k]['sha256'] != r['sha256']:
            out.append(f'{k}: register sha256 differs from the manifest')
    return out


def check():
    rows = load()
    probs = problems_offline(rows)
    want = render_module(rows)
    have = open(MODULE, encoding='utf-8').read() if os.path.exists(MODULE) else ''
    if have != want:
        probs.append(f'{os.path.relpath(MODULE, ROOT)} is stale: run '
                     'python3 scripts/takedown.py --write-module')
    if probs:
        sys.exit('\n'.join(probs))
    print(f'ok: {len(rows)} taken-down key(s); the 410 module reproduces; none held in sources/')
    return 0


# --- network readings -----------------------------------------------------------------------

def head_status(url):
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA})
    try:
        res = urllib.request.urlopen(req, timeout=60)
        return res.status, res.headers.get('x-archive-source', '')
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('x-archive-source', '')
    except Exception as e:  # noqa: BLE001 -- reported, not fatal, for a status line
        return f'error {type(e).__name__}', ''


def listed(key, bucket=A.BUCKET):
    """The bucket's own listing entry for exactly this key, or None. THE test of gone."""
    return next((o for o in A.list_objects(key, bucket=bucket) if o['key'] == key), None)


def private_sha(r):
    try:
        return A.get_object(r['private_key'], bucket=A.PRIVATE_BUCKET)[0]
    except A.NotFound:
        return None


def snapshot_for(key):
    p = subprocess.run([sys.executable, os.path.join(HERE, 'backup_snapshot.py'), '--covers', key],
                       capture_output=True, text=True, cwd=ROOT)
    return p.stdout.strip() if p.returncode == 0 else None


def snapshot_sha(snap, key):
    path = os.path.join(snap, 'public', key)
    return A.hash_file(path)[0] if os.path.exists(path) else None


def get_lock():
    payload = json.loads(A._request('GET', LOCK_URL).read())
    if not payload.get('success'):
        raise RuntimeError(f'lock read failed: {payload.get("errors")}')
    return {'rules': (payload.get('result') or {}).get('rules') or []}


def put_lock(config):
    body = json.dumps(config).encode()
    payload = json.loads(A._request('PUT', LOCK_URL, data=body,
                                    headers={'Content-Type': 'application/json'}).read())
    if not payload.get('success'):
        raise RuntimeError(f'lock write failed: {payload.get("errors")}')


def canon(config):
    return json.dumps(sorted(config['rules'], key=lambda r: r.get('id', '')), sort_keys=True)


def wrangler_lock_list():
    env = dict(os.environ, PATH=A.NODE22 + os.pathsep + os.environ.get('PATH', ''))
    p = subprocess.run(['npx', 'wrangler', 'r2', 'bucket', 'lock', 'list', A.BUCKET],
                       cwd=os.path.join(ROOT, 'fy28'), env=env, capture_output=True, text=True,
                       timeout=300)
    lines = [l for l in (p.stdout + p.stderr).splitlines()
             if l.split(':')[0].strip() in ('name', 'enabled', 'prefix', 'condition')]
    return '\n'.join('    ' + l for l in lines) or '    (wrangler printed no rules)'


# --- status ---------------------------------------------------------------------------------

def status(offline=False):
    rows = load()
    manifest = A.read_manifest()
    print(f'{len(rows)} key(s) in {os.path.relpath(REGISTER, ROOT)}\n')
    for r in rows:
        k = r['key']
        print(f'{k}')
        print(f'  state            {r["state"]}  (decided {r["decided_on"]}, {r["decided_by"]})')
        print(f'  sha256           {r["sha256"]}')
        print(f'  replacement      {r.get("superseded_by") or "(none)"}')
        print(f'  in sources/      {"YES -- should not be" if os.path.exists(A.local_path(k)) else "no"}')
        print(f'  in the manifest  {"yes" if k in manifest else "no"}')
        if offline:
            print()
            continue
        pub = listed(k)
        print(f'  public bucket    {"listed, " + str(pub["size"]) + " bytes" if pub else "NOT listed"}')
        ps = private_sha(r)
        print(f'  private copy     {r["private_key"]}: '
              + ('missing' if ps is None else ('sha256 matches' if ps == r['sha256'] else 'SHA256 DIFFERS')))
        snap = snapshot_for(k)
        if snap:
            ss = snapshot_sha(snap, k)
            print(f'  snapshot         {snap} ({"sha256 matches" if ss == r["sha256"] else "SHA256 DIFFERS"})')
        else:
            print('  snapshot         NOT in a verified snapshot')
        code, src = head_status(f'{SITE}/docs/{doc_path(k)}')
        print(f'  site /docs/      {code}' + (f'  (x-archive-source: {src})' if src else ''))
        code, _ = head_status(f'{A.PUBLIC_BASE}/{k}')
        print(f'  r2.dev           {code}')
        print()
    probs = problems_offline(rows)
    if probs:
        print('PROBLEMS:\n  ' + '\n  '.join(probs))
        return 1
    return 0


# --- delete ---------------------------------------------------------------------------------

def preflight(rows):
    """(plan, refusals). Every precondition, each one read from the thing itself."""
    manifest = A.read_manifest()
    refusals, plan = [], []
    gate = subprocess.run([sys.executable, os.path.join(HERE, 'check_archive_backed_up.py'), '--quiet'],
                          capture_output=True, text=True, cwd=ROOT)
    if gate.returncode != 0:
        refusals.append('check_archive_backed_up.py is not green -- nothing destructive runs '
                        'while a document is unbacked or in flight')
    for r in rows:
        k, why = r['key'], []
        if r['state'] != 'stopped serving':
            why.append(f'state is {r["state"]!r}, not "stopped serving"')
        code, src = head_status(f'{SITE}/docs/{doc_path(k)}')
        if code != 410:
            why.append(f'the live site answers {code} for /docs/{doc_path(k)}, not 410 -- deploy the '
                       'takedown module first')
        ps = private_sha(r)
        if ps != r['sha256']:
            why.append('the private copy is ' + ('missing' if ps is None else 'a different file'))
        snap = snapshot_for(k)
        if not snap:
            why.append('not in a VERIFIED snapshot -- run python3 scripts/backup_snapshot.py first')
        elif snapshot_sha(snap, k) != r['sha256']:
            why.append(f'the snapshot copy in {snap} does not hash to the registered sha256')
        elif os.path.basename(snap)[:10] < r['decided_on']:
            # THE BACKUP MUST BE FRESH, not merely present. HANDOFF-TAKEDOWN.md: an older
            # snapshot "is a floor, not a licence". So it must postdate the decision.
            why.append(f'the newest verified snapshot ({os.path.basename(snap)}) predates the '
                       f'decision ({r["decided_on"]}) -- take a fresh one: '
                       'python3 scripts/backup_snapshot.py')
        pub = listed(k)
        if not pub:
            why.append('the public bucket does not list it (already gone? then mark it by hand, after looking)')
        elif manifest.get(k, {}).get('etag_md5') and pub.get('etag', '').strip('"') != manifest[k]['etag_md5']:
            why.append('the bucket etag differs from the manifest')
        plan.append((r, snap, pub, why))
        refusals.extend(f'{k}: {w}' for w in why)
    return plan, refusals


def describe(plan, lock):
    print('WHAT --delete WOULD DO\n')
    print(f'  bucket: {A.BUCKET} (public). The private bucket is only read.')
    print(f'  lock now: {canon(lock)}\n')
    print('  1. save the lock configuration above (GET .../lock)')
    print('  2. lift it: PUT .../lock {"rules": []}, then GET and confirm no rules')
    for i, (r, snap, pub, _) in enumerate(plan):
        print(f'  3.{i + 1} DELETE {r["key"]}  ({r["sha256"][:16]}, {pub["size"] if pub else "?"} bytes;'
              f' backup {snap or "NONE"})')
    print('  4. list each key again; it must be absent. The DELETE response is not evidence.')
    print('  5. finally, on every path: PUT the saved lock back, GET it, compare to the saved one;')
    print('     print `wrangler r2 bucket lock list` as a second reading')
    print('  6. only for keys confirmed gone:')
    print('       takedowns.csv        state -> deleted, deleted_on -> today')
    print('       archive-manifest.csv row removed')
    print('       archive-orphans.csv  row added (why: deleted by takedown.py), so')
    print('                            check_manifest_history.py knows the row left on purpose')
    print('       _takedowns.js        regenerated (the 410 stays: the address keeps saying why)')


def delete(rows, really):
    lock = get_lock()
    plan, refusals = preflight(rows)
    describe(plan, lock)
    if refusals:
        print('\nREFUSED -- nothing was changed:\n  ' + '\n  '.join(refusals))
        return 1
    if not really:
        print('\n(dry run: every precondition passed; nothing was changed)')
        return 0
    if not lock['rules']:
        print('\nREFUSED: the bucket has NO lock rule to restore. Re-read it by hand first.')
        return 1

    saved = json.loads(json.dumps(lock))
    gone, kept = [], []
    try:
        put_lock({'rules': []})
        if get_lock()['rules']:
            raise RuntimeError('the lock did not lift; nothing deleted')
        print('\nlock lifted')
        for r, _, _, _ in plan:
            k = r['key']
            assert k == r['key'] and A.BUCKET != A.PRIVATE_BUCKET
            try:
                A._request('DELETE', A._object_url(k, A.BUCKET))
            except Exception as e:  # noqa: BLE001 -- the listing below decides
                print(f'  DELETE {k}: {e}')
            (kept if listed(k) else gone).append(k)
            print(f'  {k}: {"GONE (not listed)" if k in gone else "STILL LISTED"}')
    finally:
        put_lock(saved)
        back = get_lock()
        if canon(back) != canon(saved):
            print('\n!! THE LOCK DID NOT READ BACK AS SAVED. Restore it by hand NOW:')
            print('   saved: ' + canon(saved))
            print('   now:   ' + canon(back))
        else:
            print('\nlock restored and read back identical: ' + canon(back))
        print('wrangler r2 bucket lock list:\n' + wrangler_lock_list())

    if gone:
        record_deleted(gone)
    if kept:
        print(f'\n{len(kept)} key(s) still listed -- NOT recorded as deleted:\n  ' + '\n  '.join(kept))
        return 1
    return 0


def record_deleted(keys):
    today = datetime.date.today().isoformat()
    rows = load()
    for r in rows:
        if r['key'] in keys:
            r['state'], r['deleted_on'] = 'deleted', today
    save(rows)

    man = A.read_manifest()
    sha = {k: man.get(k, {}).get('sha256', '') for k in keys}
    A.write_manifest([v for k, v in sorted(man.items()) if k not in keys])

    log = subprocess.run(['git', 'log', '-1', '--format=%h|%cs|%s', '--',
                          'sources/data/archive-manifest.csv'],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip().split('|', 2)
    log += [''] * (3 - len(log))
    with open(ORPHANS, 'a', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=ORPHAN_FIELDS, lineterminator='\n')
        for k in keys:
            w.writerow({'key': k, 'sha256': sha[k], 'superseded_by': '',
                        'last_indexed_at': log[0], 'last_indexed_date': log[1],
                        'commit_subject': log[2][:90],
                        'why': f'deleted from the bucket by scripts/takedown.py on {today}, '
                               'confirmed gone by listing; see data/takedowns.csv'})
    write_module(rows)
    print(f'\nrecorded {len(keys)} deletion(s): takedowns.csv, archive-manifest.csv, archive-orphans.csv')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--status', action='store_true')
    g.add_argument('--write-module', action='store_true')
    g.add_argument('--check', action='store_true')
    g.add_argument('--dry-run', action='store_true')
    g.add_argument('--delete', action='store_true')
    ap.add_argument('--offline', action='store_true', help='--status without network reads')
    ap.add_argument('--key', action='append', help='limit --dry-run/--delete to these keys')
    a = ap.parse_args()
    if a.status:
        return status(a.offline)
    if a.write_module:
        write_module()
        return 0
    if a.check:
        return check()
    rows = [r for r in load() if r['state'] == 'stopped serving' and (not a.key or r['key'] in a.key)]
    if a.key and len(rows) != len(set(a.key)):
        sys.exit('a --key is not in the register at state "stopped serving"')
    if not rows:
        print('nothing at state "stopped serving"')
        return 0
    return delete(rows, really=a.delete)


if __name__ == '__main__':
    raise SystemExit(main())
