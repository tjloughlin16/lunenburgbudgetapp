#!/usr/bin/env python3
"""What documents have APPEARED on the district's and the town's pages since we last looked.

    python3 scripts/watch_documents.py            # re-walk the listing pages; record what is NEW
    python3 scripts/watch_documents.py --check    # no network; the state holds together
    python3 scripts/watch_documents.py --dry-run  # walk and report; keep nothing
    python3 scripts/watch_documents.py --annual-reports   # the annual town reports only

The annual town reports are left out of the daily walk and looked for quarterly, as their
own row in source-cadence.csv (`annual-reports`). TJ, 28 October 2026: daily is too fast
for a document the town publishes once a year.

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

A NEW ROW MAY BE AN OLD DOCUMENT RE-POSTED. On 3 November 2026 the town replaced the 1997 and
1999 annual reports with rescans that add pages, at new addresses (View/4615, 4616), and let
the old ones (4523, 4525) 404. This filed them as two more "1997 Annual Town Report"s with
nothing linking them, and nothing re-read the added pages. So every new row is now given a
`kind`, by `replacement_verdict()`:

    new                   no held row in its folder carries its title
    replacement           exactly one does, and every address of that row now answers 404/410
    possible replacement  exactly one does, and that row is still served -- two live copies
                          under one title, which somebody has to look at
    new address           a document we already hold, catalogued under another address

and `replaces` names the held copy. A title shared by several held rows (a district agenda,
say) identifies nothing, so it stays `new`. The replaced copy is never removed: re-reading a
replacement is a person's decision (notes/findings/ANNUAL-REPORT-RESCANS-2026-11.md).
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
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from verify_source_copies import status_of  # noqa: E402
SRC = os.path.join(ROOT, 'sources')
EVENTS = os.path.join(ROOT, 'sources', 'data', 'document-watch-events.csv')
EVENT_COLS = ['first_seen', 'folder', 'label', 'upstream', 'local', 'bytes', 'kind', 'replaces']
# `town-annual-reports` is written by fetch_town_docs.py like the other two town mirrors and
# was missing here until 27 October 2026, so a new report raised no NEW event and its
# catalogue was the one a short crawl could shrink unchallenged.
FOLDERS = ['district-budget', 'town-budget', 'town-supplementary', 'town-annual-reports',
           'state-dese', 'state-dls']


def read_csv(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path, newline='', encoding='utf-8', errors='replace')))


def index_of(folder):
    return os.path.join(SRC, folder, 'index.csv')


def addresses(rows):
    """Every single address a set of index rows carries. `upstream` can hold several,
    space-joined, and gains one whenever a crawl finds the same bytes somewhere else -- so a
    joined string is not an identity and is never compared whole."""
    return {u for r in rows for u in (r.get('upstream') or '').split()}


def title_key(label):
    from fetch_town_docs import dedupe_key    # the crawler's own sameness, imported late
    return dedupe_key(label or '')


def replacement_verdict(row, held_rows, probe):
    """-> (kind, replaces) for one catalogue row the crawl found new. See the docstring.

    `held_rows` is the folder's catalogue BEFORE the crawl; `probe(url)` returns an HTTP
    status as a string. Pure apart from `probe`, so the 1997/1999 case replays offline.
    """
    from verify_source_copies import GONE
    if row.get('local') and row['local'] in {h.get('local') for h in held_rows}:
        return 'new address', row['local']
    k = title_key(row.get('label'))
    same = [h for h in held_rows if k and title_key(h.get('label')) == k]
    if len(same) != 1:
        return 'new', ''
    old = same[0]
    codes = [probe(u) for u in (old.get('upstream') or '').split()]
    if codes and all(c in GONE for c in codes):
        return 'replacement', old.get('local', '')
    return 'possible replacement', old.get('local', '')


def check():
    ev = read_csv(EVENTS)
    held = {f: addresses(read_csv(index_of(f))) for f in FOLDERS}
    bad = [e for e in ev if not set(e['upstream'].split()) <= held.get(e['folder'], set())]
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
    ap.add_argument('--annual-reports', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    if a.annual_reports:
        crawlers = [['fetch_town_docs.py', '--scope', 'annual-reports']]
    else:
        crawlers = [['fetch_school_budget_docs.py'], ['fetch_town_docs.py', '--scope', 'no-annual-reports']]

    before = {f: read_csv(index_of(f)) for f in FOLDERS}
    snap = tempfile.mkdtemp(prefix='index-snap-')
    for f in FOLDERS:
        if os.path.exists(index_of(f)):
            shutil.copy(index_of(f), os.path.join(snap, f + '.csv'))

    env = dict(os.environ)
    for c in crawlers:
        args = [sys.executable, os.path.join(ROOT, 'scripts', c[0]), *c[1:]]
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
        known = addresses(before[f])
        for r in after:
            mine = (r.get('upstream') or '').split()
            if not mine or set(mine) <= known:
                continue
            kind, replaces = replacement_verdict(r, before[f], status_of)
            fresh.append({'first_seen': a.as_of, 'folder': f, 'label': r.get('label', ''),
                          'upstream': ' '.join(u for u in mine if u not in known),
                          'local': r.get('local', ''), 'bytes': r.get('bytes', ''),
                          'kind': kind, 'replaces': replaces})
            print('%-11s %-18s %s%s' % (kind.upper() if kind != 'new' else 'NEW', f,
                                        r.get('label', '')[:60],
                                        '  (replaces %s)' % replaces if replaces and kind != 'new address' else ''))
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
