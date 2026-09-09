#!/usr/bin/env python3
"""What has APPEARED on the town's AgendaCenter since the last time we looked.

    python3 scripts/watch_meetings.py --seed          # first run: adopt what we already hold
    python3 scripts/watch_meetings.py                 # crawl the town, report what is NEW
    python3 scripts/watch_meetings.py --check         # no network; is the state self-consistent
    python3 scripts/watch_meetings.py --source index  # observe from sources/meetings/index.csv

WHAT THIS IS, AND WHAT KIND OF THING IT IS NOT (phase three's first design decision)

Every other dataset in this repository is a MEASUREMENT: a figure checkable against a
document. This is not one. This is an OBSERVATION LOG -- what this project's crawler could
see on the town's website on a given day. It belongs in the announcements category and its
output is labelled that way so it cannot be read beside a budget figure as the same kind of
number.

DETERMINISM IS THE REQUIREMENT

A feed must never say "new" about something it has already announced. So:

  * The state file is the memory, it is committed, and a person can read it in a diff.
  * A document's identity is (board, date, kind, file id) -- the town's own file id, not a
    path, not a hash, and not a position in a listing.
  * Everything already known is skipped. `--seed` adopts the whole existing index without
    announcing a single row, so the first live run cannot dump twelve thousand
    "new" documents into a feed.
  * A second run on the same day rewrites the same run row instead of appending another,
    so running twice leaves all three files byte-identical. That is the acceptance test and
    it is in tests/test_watch_meetings_idempotent.py.

WHAT `first_seen` IS AND IS NOT (rule 7)

`first_seen` is THE DAY OUR CRAWLER FIRST SAW THE DOCUMENT. It is not the day the town
posted it. The AgendaCenter publishes no posting timestamp, so the gap between a meeting
date and a first_seen date is an UPPER BOUND on how long minutes took to appear, and it is
named that way in every column and every payload. A row carried in by `--seed` has no
first_seen at all, because we genuinely do not know -- an empty cell, not a guess.

FAIL-CLOSED

An empty listing is a fetch failure, not a town that stopped meeting. A crawl returning no
boards, or a crawl that would delete state, refuses to write.
"""
import argparse
import csv
import datetime as dt
import importlib.util
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The two environment overrides exist for ONE caller: the idempotence test, which has to
# run the detector twice for real without touching the committed state. A test that stubs
# out the code path it is testing proves nothing, so it runs this file as a subprocess and
# only moves where it reads and writes.
DATA = os.environ.get('MEETING_WATCH_DIR') or os.path.join(ROOT, 'sources', 'data')
STATE = os.path.join(DATA, 'meeting-watch-state.csv')
EVENTS = os.path.join(DATA, 'meeting-watch-events.csv')
RUNS = os.path.join(DATA, 'meeting-watch-runs.csv')
INDEX = (os.environ.get('MEETING_WATCH_INDEX')
         or os.path.join(ROOT, 'sources', 'meetings', 'index.csv'))

STATE_FIELDS = ['board', 'board_slug', 'date', 'kind', 'file_id', 'url',
                'first_seen', 'basis']
EVENT_FIELDS = ['first_seen', 'board', 'board_slug', 'meeting_date', 'kind', 'file_id',
                'url', 'days_after_meeting_upper_bound']
RUN_FIELDS = ['ran', 'source', 'boards_listed', 'documents_listed', 'boards_unanswered',
              'new_agendas', 'new_minutes']


def _fetcher():
    spec = importlib.util.spec_from_file_location(
        'fa', os.path.join(ROOT, 'scripts', 'fetch_agendas.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read(path, fields):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for f in fields:
            r.setdefault(f, '')
    return rows


def write(path, fields, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def key(r):
    return (r['board_slug'], r['date'], r['kind'], str(r['file_id']))


# ---------------------------------------------------------------- observation sources

def observe_index(fa):
    """What sources/meetings/index.csv holds. No network. The seed, and the test fixture."""
    if not os.path.exists(INDEX):
        raise SystemExit('sources/meetings/index.csv is absent; there is nothing to '
                         'observe. Refusing to write.')
    out, boards = [], set()
    for r in csv.DictReader(open(INDEX, encoding='utf-8', errors='replace')):
        if r.get('kind') not in ('agenda', 'minutes') or not r.get('file_id'):
            continue
        boards.add(r['board'])
        out.append({'board': r['board'], 'board_slug': fa.slug(r['board']),
                    'date': r['date'], 'kind': r['kind'], 'file_id': r['file_id'],
                    'url': r['url']})
    if not out:
        raise SystemExit('the meetings index parsed to zero documents. A listing that '
                         'matches nothing looks exactly like a town with no meetings.')
    return out, len(boards), 0


def observe_live(fa, first, last, pause=0.35):
    """What the AgendaCenter lists right now. The authority on what EXISTS.

    A board-year that FAILS to fetch and a board-year with no meetings both come back as
    an empty listing, and `fetch_agendas.listing` cannot tell them apart -- so this reads
    the raw response itself. The town rate-limits (HTTP 429) and the retry gives up after
    three tries, which is exactly the silent-zero shape rule 3 of check_generated.py is
    about: a board whose listing failed looks identical to a board that stopped meeting.

    A failed board-year cannot produce a false "new" -- nothing is ever removed from the
    state file -- but it can DELAY one, and it makes the run log lie about how much was
    looked at. So failures are counted, printed, and past a threshold they refuse the run.
    """
    cats = fa.categories()
    if not cats:
        raise SystemExit('the AgendaCenter listed no boards at all. That is a fetch '
                         'failure, not a town with no committees -- refusing to write.')
    out, seen, failed = [], set(), []
    for cid, name in sorted(cats.items(), key=lambda kv: kv[1]):
        for year in range(first, last + 1):
            body = fa.get('%s/AgendaCenter/UpdateCategoryList' % fa.BASE,
                          {'year': year, 'catID': cid})
            if not body:
                failed.append((name, year))
                continue
            h = body.decode('utf-8', 'replace')
            for kind, date, fid in re.findall(
                    r'ViewFile/(Agenda|Minutes)/_(\d{8})-(\d+)', h):
                if date[4:] != str(year):
                    continue
                kind = kind.lower()
                k = (kind, fid)
                if k in seen:            # boards share files for joint meetings
                    continue
                seen.add(k)
                out.append({
                    'board': name, 'board_slug': fa.slug(name),
                    'date': '%s-%s-%s' % (date[4:], date[:2], date[2:4]),
                    'kind': kind, 'file_id': fid,
                    'url': '%s/AgendaCenter/ViewFile/%s/_%s-%s'
                           % (fa.BASE, kind.capitalize(), date, fid)})
            time.sleep(pause)
    attempted = len(cats) * (last - first + 1)
    if failed:
        print('  ! %d of %d board-years did not answer: %s'
              % (len(failed), attempted,
                 ', '.join('%s %d' % f for f in failed[:5])
                 + (' ...' if len(failed) > 5 else '')))
    if len(failed) > attempted // 5:
        raise SystemExit('%d of %d board-years failed to fetch. That is a rate limit or '
                         'an outage, not a quiet town -- refusing to write a run this '
                         'incomplete.' % (len(failed), attempted))
    if not out:
        raise SystemExit('%d boards listed and not one document across %d-%d. That is a '
                         'fetch failure -- refusing to write.' % (len(cats), first, last))
    return out, len(cats), len(failed)


# ---------------------------------------------------------------------------- checks

def consistency(state, events):
    """Every invariant the feed depends on. No network. Returns a list of failures."""
    bad = []
    keys = [key(r) for r in state]
    if not state:
        bad.append('the state file holds no documents at all')
    if len(set(keys)) != len(keys):
        dupes = {k for k in keys if keys.count(k) > 1}
        bad.append('%d duplicate keys in the state file, e.g. %s'
                   % (len(dupes), sorted(dupes)[:3]))
    known = set(keys)
    orphan = [e for e in events
              if (e['board_slug'], e['meeting_date'], e['kind'], e['file_id']) not in known]
    if events and len(orphan) == len(events):
        bad.append('NO event joined to the state file. A join that matches nothing looks '
                   'exactly like data that is absent.')
    elif orphan:
        bad.append('%d events name a document the state file does not hold' % len(orphan))
    # Every observed row must have announced itself exactly once, and no seeded row may.
    announced = {(e['board_slug'], e['meeting_date'], e['kind'], e['file_id'])
                 for e in events}
    for r in state:
        if r['basis'] == 'observed' and key(r) not in announced:
            bad.append('observed but never announced: %s' % (key(r),))
            break
        if r['basis'] == 'seed' and key(r) in announced:
            bad.append('seeded rows must never be announced as new: %s' % (key(r),))
            break
        if r['basis'] == 'seed' and r['first_seen']:
            bad.append('a seeded row carries a first_seen date, which we do not know: %s'
                       % (key(r),))
            break
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', choices=['live', 'index'], default='live')
    ap.add_argument('--seed', action='store_true',
                    help='adopt every document we already hold WITHOUT announcing any')
    ap.add_argument('--check', action='store_true',
                    help='no network; assert the state file is self-consistent')
    ap.add_argument('--as-of', default=dt.date.today().isoformat(),
                    help='the observation date to record (default today)')
    ap.add_argument('--from', dest='first', type=int, default=dt.date.today().year - 1)
    ap.add_argument('--to', dest='last', type=int, default=dt.date.today().year)
    ap.add_argument('--dry-run', action='store_true', help='report, write nothing')
    a = ap.parse_args()

    state = read(STATE, STATE_FIELDS)
    events = read(EVENTS, EVENT_FIELDS)

    if a.check:
        bad = consistency(state, events)
        if bad:
            print('INCONSISTENT — the meeting watch state does not hold together:')
            for b in bad:
                print('  ' + b)
            return 1
        print('ok — %d documents watched, %d announced, no duplicates, every event joins'
              % (len(state), len(events)))
        return 0

    fa = _fetcher()
    if a.seed:
        a.source = 'index'
    seen, boards, failed = (observe_index(fa) if a.source == 'index'
                            else observe_live(fa, a.first, a.last))

    known = {key(r) for r in state}
    fresh = []
    for r in seen:
        if key(r) in known:
            continue
        known.add(key(r))
        fresh.append(r)

    # A crawl NEVER removes a row. The town takes documents down and reposts them, and a
    # state file that forgot one would announce it again the next day -- the exact defect
    # this file exists to prevent.
    new_events = []
    for r in fresh:
        row = dict(r)
        if a.seed:
            row['first_seen'] = ''          # we do not know. Not a guess, an empty cell.
            row['basis'] = 'seed'
        else:
            row['first_seen'] = a.as_of
            row['basis'] = 'observed'
            try:
                lag = (dt.date.fromisoformat(a.as_of)
                       - dt.date.fromisoformat(r['date'])).days
            except ValueError:
                lag = ''
            new_events.append({
                'first_seen': a.as_of, 'board': r['board'], 'board_slug': r['board_slug'],
                'meeting_date': r['date'], 'kind': r['kind'], 'file_id': r['file_id'],
                'url': r['url'],
                'days_after_meeting_upper_bound': lag if lag != '' and lag >= 0 else ''})
        state.append(row)

    # The day's announcement counts are DERIVED from the event log rather than
    # accumulated across runs. An accumulator is a second copy of the truth and drifts
    # from it the moment anything is edited by hand; this cannot.
    # A seed announces nothing by definition, so its run row counts nothing -- otherwise
    # a seed run on the same day as a crawl would claim the crawl's announcements.
    day_events = ([] if a.seed else
                  [e for e in events + new_events if e['first_seen'] == a.as_of])
    n_ag = sum(1 for e in day_events if e['kind'] == 'agenda')
    n_mi = sum(1 for e in day_events if e['kind'] == 'minutes')
    fresh_ag = sum(1 for e in new_events if e['kind'] == 'agenda')
    fresh_mi = sum(1 for e in new_events if e['kind'] == 'minutes')

    # One run row per (day, source). A second run on the same day REPLACES it rather than
    # appending, which is what makes running twice byte-identical rather than merely
    # silent.
    label = 'seed' if a.seed else a.source
    all_runs = read(RUNS, RUN_FIELDS)
    prior = next((r for r in all_runs if r['ran'] == a.as_of and r['source'] == label),
                 None)
    runs = [r for r in all_runs if not (r['ran'] == a.as_of and r['source'] == label)]

    def _best(field, value, better=max):
        return value if prior is None else better(int(prior[field] or 0), value)

    # The day's row is the day's BEST look, not its last one. A re-run throttled by the
    # town's rate limiter sees fewer documents than the run before it, and letting that
    # overwrite a fuller observation would make the log churn on every retry -- the
    # opposite of deterministic. Counts of what was NEW are cumulative for the day;
    # counts of what was LOOKED AT keep the widest, and unanswered keeps the fewest.
    runs.append({'ran': a.as_of, 'source': label,
                 'boards_listed': _best('boards_listed', boards),
                 'documents_listed': _best('documents_listed', len(seen)),
                 'boards_unanswered': _best('boards_unanswered', failed, min),
                 'new_agendas': n_ag, 'new_minutes': n_mi})

    print('%s: %d boards, %d documents listed; %d new (%d agendas, %d minutes)'
          % (a.source, boards, len(seen), len(fresh), fresh_ag, fresh_mi))
    for e in new_events[:20]:
        print('  + %-9s %-38s %s' % (e['kind'], e['board'][:38], e['meeting_date']))
    if len(new_events) > 20:
        print('  ... and %d more' % (len(new_events) - 20))

    if a.dry_run:
        print('dry run — nothing written')
        return 0

    state.sort(key=key)
    events = events + new_events
    events.sort(key=lambda e: (e['first_seen'], e['board_slug'], e['meeting_date'],
                               e['kind'], e['file_id']))
    runs.sort(key=lambda r: (r['ran'], r['source']))
    write(STATE, STATE_FIELDS, state)
    write(EVENTS, EVENT_FIELDS, events)
    write(RUNS, RUN_FIELDS, runs)

    bad = consistency(read(STATE, STATE_FIELDS), read(EVENTS, EVENT_FIELDS))
    if bad:
        print('WROTE AN INCONSISTENT STATE:')
        for b in bad:
            print('  ' + b)
        return 1
    print('state -> %s (%d documents), events -> %s (%d announced)'
          % (os.path.relpath(STATE, ROOT), len(state),
             os.path.relpath(EVENTS, ROOT), len(events)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
