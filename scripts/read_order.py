#!/usr/bin/env python3
"""WHICH RECORD OF A MEETING IS READ FIRST -- the one rule, in one place.

    python3 scripts/read_order.py select-board 2026-09-15     # the state of one meeting
    python3 scripts/read_order.py --summary                   # every set of official minutes, by state

TJ, 6 October 2026: *"we always read the YouTube transcripts first before we read the
meeting minutes if they're in existence ... if we're taking too long backfilling the
YouTube transcripts, then this catch should kick in."*

WHY THIS ORDER. Two records exist of a meeting with a recording: OUR minutes, written from
its captions, and the TOWN's, written by a clerk. Reading ours first means the reconcile can
run the moment the town's are read, in the same pass over the meeting, instead of waiting
for some later run to notice the pair. And it is almost always the natural order: the town's
minutes arrive at least 17 days after the meeting (every one of 43 measured), a recording
within days. (Folding the reconcile into the same MODEL CALL as the town's read was piloted
and is off -- see FOLD_RECONCILE in extract_official_votes.py.)

THE TWO READS STAY SEPARATE. Our minutes are written from the recording alone, never with
the town's text in view, because a comparison of two records only means something if
neither was written looking at the other. Each step saves its own file the moment it
succeeds, so a failure loses only the step that failed.

A meeting is in exactly one state:

  ours        our minutes exist                 -> read the town's minutes, then reconcile
  transcript  on our-minutes' own work list      -> write OURS FIRST, then the above
              (captions held, long enough, in policy)
  awaiting    a recording is known, no captions -> wait, up to GRACE_DAYS; then read the
              yet, captions not refused            town's minutes alone (the catch)
  none        no recording, a board outside the -> read the town's minutes alone
              policy, captions disabled or too short

THE CATCH, AND ITS CLOCK. GRACE_DAYS runs from the LATER of the day we first saw the town's
minutes and the day we first knew of the recording. Five days, inside the refresh's seven-day
window for new documents, so the fallback fires there rather than the minutes ageing out of
"new" while they wait. A meeting read alone this way is still reconciled later, by
reconcile_minutes.py, once our minutes exist.
"""
import csv
import datetime as dt
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')

GRACE_DAYS = 5

_cache = {}


def _rows(name):
    p = os.path.join(DATA, name)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def _load():
    if _cache:
        return _cache
    import refresh
    _cache['policy'] = refresh.policy()
    known = {}
    for r in _rows('youtube-video-boards.csv'):
        k = (r['board_slug'], r['meeting_date'])
        d = (r.get('classified_at') or '')[:10]
        known[k] = min(known.get(k, d) or d, d) if d else known.get(k, '')
    _cache['video'] = known
    _cache['nocap'] = {(r['board_slug'], r['meeting_date']) for r in _rows('youtube-no-captions.csv')}
    _cache['captions'] = {(r['board_slug'], r['meeting_date']) for r in _rows('youtube-transcript-index.csv')
                          if os.path.exists(os.path.join(ROOT, r['path']))}
    # OURS FIRST means exactly: on the list our-minutes would work. The same list, imported,
    # so a transcript it refuses (too short) can never hold the town's minutes back forever.
    _cache['writable'] = {(t['board_slug'], t['meeting_date']) for t in refresh.minutes_targets(_cache['policy'])}
    _cache['ours'] = {(p.split(os.sep)[-2], os.path.basename(p)[:10])
                      for p in glob.glob(os.path.join(DATA, 'recording-minutes', '*', '*.json'))}
    seen = {}
    for e in _rows('meeting-watch-events.csv'):
        if e['kind'] == 'minutes':
            k = (e['board_slug'], e['meeting_date'])
            seen[k] = min(seen.get(k, e['first_seen']), e['first_seen'])
    _cache['minutes_seen'] = seen
    return _cache


def reset():
    """Forget what was loaded -- after a step has written a file this module reads."""
    _cache.clear()


def state(board, date, today=None):
    """(state, why) for one meeting. See the module docstring for the four states."""
    import refresh
    c = _load()
    k = (board, date)
    if k in c['ours']:
        return 'ours', 'our minutes exist'
    if k not in c['video']:
        return 'none', 'no recording is known'
    if not refresh.covered(board, date, c['policy']):
        return 'none', 'the board is outside the recording-minutes policy'
    if k in c['nocap'] and k not in c['captions']:
        return 'none', 'the recording has captions disabled'
    if k in c['writable']:
        return 'transcript', 'captions held; our minutes come first'
    if k in c['captions']:
        return 'none', 'captions held but too short to write minutes from -- read alone'
    today = today or dt.date.today().isoformat()
    clock = max(c['minutes_seen'].get(k, ''), c['video'][k] or '')
    if not clock:
        return 'awaiting', 'a recording is known and no captions yet'
    waited = (dt.date.fromisoformat(today) - dt.date.fromisoformat(clock)).days
    if waited >= GRACE_DAYS:
        return 'none', 'no captions after %d days (grace %d) -- read alone, reconciled later' % (waited, GRACE_DAYS)
    return 'awaiting', 'no captions yet; waited %d of %d days' % (waited, GRACE_DAYS)


def main():
    import argparse
    import collections
    ap = argparse.ArgumentParser()
    ap.add_argument('board', nargs='?')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--summary', action='store_true')
    a = ap.parse_args()
    if a.board and a.date:
        print('%s %s  %s: %s' % ((a.board, a.date) + state(a.board, a.date)))
        return 0
    import extract_official_votes as E
    n = collections.Counter()
    for k in {(e['board_slug'], e['date']) for e in E.minutes_files()}:
        n[state(*k)[0]] += 1
    for s in ('ours', 'transcript', 'awaiting', 'none'):
        print('%-11s %5d' % (s, n[s]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
