#!/usr/bin/env python3
"""What documents have APPEARED on the district's and the town's pages since we last looked.

    python3 scripts/watch_documents.py            # re-walk the listing pages; record what is NEW
    python3 scripts/watch_documents.py --check    # no network; the state holds together
    python3 scripts/watch_documents.py --dry-run  # walk and report; keep nothing

TJ, 12 September 2026: *"the refresh needs to look for new documents posted from the
school committee (budget related), as well as on the town pages from the areas we've
found."* The archive knows every document's own address and never re-read the LISTING
pages those came from. This does, daily, through the two crawlers that built the mirrors:

    fetch_school_budget_docs.py   the district's budget page -- a wall of Drive links
    fetch_town_docs.py            the town's budget hub, town meetings, finance pages

Both are idempotent (a file on disk is skipped) and both REWRITE their folder's
index.csv from what the listing shows today. That is the hazard `fetch_agendas.py` had:
a listing that lost a link would shrink the catalogue, and the search index and the
push would follow it down. So this snapshots every index first, runs the crawlers, and
if any index came back smaller it is RESTORED from the snapshot and the run says so --
a document the town took down is still a document we hold, with its address.

New rows -- an upstream address no index held before -- are the events, keyed on
(folder, upstream). The event log is the memory; a second run on a day writes nothing.
"""
import argparse
import csv
import datetime as dt
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
EVENTS = os.path.join(ROOT, 'sources', 'data', 'document-watch-events.csv')
EVENT_COLS = ['first_seen', 'folder', 'label', 'upstream', 'local', 'bytes']
FOLDERS = ['district-budget', 'town-budget', 'town-supplementary', 'state-dese', 'state-dls']
CRAWLERS = [['fetch_school_budget_docs.py'], ['fetch_town_docs.py']]


def read_csv(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path, newline='', encoding='utf-8', errors='replace')))


def index_of(folder):
    return os.path.join(SRC, folder, 'index.csv')


def check():
    ev = read_csv(EVENTS)
    held = set()
    for f in FOLDERS:
        held |= {(f, r.get('upstream', '')) for r in read_csv(index_of(f))}
    bad = [e for e in ev if (e['folder'], e['upstream']) not in held]
    dup = len(ev) - len({(e['folder'], e['upstream']) for e in ev})
    if bad or dup:
        print('FAIL: %d event(s) name a document no index holds; %d duplicated' % (len(bad), dup))
        return 1
    print('ok: %d document watch event(s), every one still catalogued' % len(ev))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    a = ap.parse_args()
    if a.check:
        return check()

    before = {f: read_csv(index_of(f)) for f in FOLDERS}
    snap = tempfile.mkdtemp(prefix='index-snap-')
    for f in FOLDERS:
        if os.path.exists(index_of(f)):
            shutil.copy(index_of(f), os.path.join(snap, f + '.csv'))

    env = dict(os.environ)
    for c in CRAWLERS:
        args = [sys.executable, os.path.join(ROOT, 'scripts', *c)]
        print('$ ' + ' '.join(args[1:]), flush=True)
        r = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=3600)
        tail = (r.stdout or '').strip().splitlines()[-3:]
        for line in tail:
            print('  ' + line)
        if r.returncode != 0:
            print('  crawler failed (exit %d); its indexes are restored from the snapshot' % r.returncode)
            print('  ' + (r.stderr or '')[-600:])

    fresh = []
    for f in FOLDERS:
        after = read_csv(index_of(f))
        if len(after) < len(before[f]):
            # A smaller catalogue is never accepted. Restore, and say so loudly.
            shutil.copy(os.path.join(snap, f + '.csv'), index_of(f))
            print('RESTORED %s/index.csv: the crawl returned %d rows against %d held. A listing lost a '
                  'link; the document is still ours. Check the listing page.' % (f, len(after), len(before[f])))
            continue
        # A crawl that found the same rows in a different order is not a change. Put the
        # file back as it was, so a daily run leaves git quiet unless something is new.
        key = lambda r: (r.get('upstream', ''), r.get('sha256', ''), r.get('local', ''))
        if sorted(map(key, after)) == sorted(map(key, before[f])) and os.path.exists(os.path.join(snap, f + '.csv')):
            shutil.copy(os.path.join(snap, f + '.csv'), index_of(f))
            continue
        known = {r.get('upstream', '') for r in before[f]}
        for r in after:
            if r.get('upstream', '') and r['upstream'] not in known:
                fresh.append({'first_seen': a.as_of, 'folder': f, 'label': r.get('label', ''),
                              'upstream': r['upstream'], 'local': r.get('local', ''), 'bytes': r.get('bytes', '')})
                print('NEW  %-18s %s' % (f, r.get('label', '')[:70]))
    if a.dry_run:
        for f in FOLDERS:
            if os.path.exists(os.path.join(snap, f + '.csv')):
                shutil.copy(os.path.join(snap, f + '.csv'), index_of(f))
        shutil.rmtree(snap, ignore_errors=True)
        print('dry run: %d new document(s) seen; indexes left as they were' % len(fresh))
        return 0
    shutil.rmtree(snap, ignore_errors=True)
    if not fresh:
        print('no new documents on the district or town pages')
        return 0
    events = read_csv(EVENTS)
    known = {(e['folder'], e['upstream']) for e in events}
    events += [e for e in fresh if (e['folder'], e['upstream']) not in known]
    tmp = EVENTS + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=EVENT_COLS)
        w.writeheader()
        for e in events:
            w.writerow({c: e.get(c, '') for c in EVENT_COLS})
    os.replace(tmp, EVENTS)
    print('%d new document(s) recorded' % len(fresh))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
