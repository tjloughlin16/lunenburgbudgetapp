#!/usr/bin/env python3
"""One run that brings the archive up to today, deterministically, and says what changed.

    python3 scripts/refresh.py                # watch, fetch, write, rebuild; deploy nothing
    python3 scripts/refresh.py --deploy       # ...and build the site and deploy it
    python3 scripts/refresh.py --dry-run      # watch only; write nothing, fetch nothing
    python3 scripts/refresh.py --no-minutes   # skip the model step (costs money per meeting)
    python3 scripts/refresh.py --check        # every watcher's state holds together

QUEUE item 12. TJ: "deterministic". Every step here is a script that already answers
"what changed since last time" from a committed state file and is idempotent on its own;
this runs them in the order their outputs feed each other, and ends with a digest that is
DERIVED from their event logs rather than accumulated across runs.

THE ORDER, AND WHY IT CANNOT MOVE

  1. watch_meetings      what appeared on the town's AgendaCenter (agendas, minutes)
  2. fetch_agendas       the documents themselves, for this year -- resumable, skips held
  3. extract_minutes     text out of anything new (Word and Excel too)
  3b. agenda previews    the UPCOMING notice: what is on a policy-board agenda dated today
                         or later, quoted from the agenda, with a Facebook text to paste
  3c. watch_feeds        the town's news flash and alert feeds; linked, never republished
  3d. watch_documents    new documents on the district's budget page and the town's finance
                         pages, through the crawlers that built the mirrors
  4. watch_youtube       what appeared on the town's channel (the RSS feed, no key)
  5. classification      which board a new video belongs to, from its title
  6. transcripts         captions for recent meetings -- re-tried every run, because
                         YouTube's auto-captions arrive hours to days after the upload
  7. minutes             OUR minutes, for recordings inside the approved POLICY only
  7b. reconcile          ours against the town's minutes where both exist: caption
                         errors resolved beside the as-heard reading, real differences flagged
  8. rebuild             the feed, the minutes payload, the notices, the index, the metrics
  9. push                the search index to D1, inside the day's write budget
 10. deploy              only with --deploy. Rule 10: nothing deploys without being asked.

THE POLICY FILE IS THE APPROVAL. `sources/data/recording-minutes-policy.csv` names which
boards, from which date, TJ has approved minutes for. Step 7 writes minutes for a
recording only if a policy row covers it, and at most MAX_MINUTES_PER_RUN of them, because
that step draws on the Max plan's weekly allowance (~0.09% a meeting) and everything else
here is free. Rows carry a `priority`; `*` covers any board.

TWO THINGS IT REFUSES TO DO AT ONCE. If the transcript backfill is running it skips the
caption fetch rather than competing for the same rate limit (the pattern is written so it
cannot match its own argv -- see CLAUDE.md on pgrep). And it never runs the analysis
database push (`sync_d1.py`), which shares the D1 write budget: that stays a decision.
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')
POLICY = os.path.join(ROOT, 'sources', 'data', 'recording-minutes-policy.csv')
RUNS = os.path.join(ROOT, 'sources', 'data', 'refresh-runs.csv')
WHATS_NEW = os.path.join(ROOT, 'fy28', 'public', 'data', 'whats-new.json')
MEETING_EVENTS = os.path.join(ROOT, 'sources', 'data', 'meeting-watch-events.csv')
YOUTUBE_EVENTS = os.path.join(ROOT, 'sources', 'data', 'youtube-watch-events.csv')
FEED_EVENTS = os.path.join(ROOT, 'sources', 'data', 'feed-watch-events.csv')
FEED_SOURCES = os.path.join(ROOT, 'sources', 'data', 'feed-sources.csv')
DOC_EVENTS = os.path.join(ROOT, 'sources', 'data', 'document-watch-events.csv')
TRANSCRIPT_INDEX = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
RECORDED = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
# THREE A DAY. Measured 13-14 September 2026: one minutes run is about 0.09% of the Max
# plan's weekly allowance, so three a day is ~2% a week -- the pace TJ set. The whole
# backlog of transcripts (~880) clears in about ten months at this pace; raise it here
# if he wants faster, never past ~20 (2% a DAY). See ~/.claude/CLAUDE.md.
MAX_MINUTES_PER_RUN = 3
# The town's own minutes, read for their votes: cheap (a short document, the small model,
# every quote checked) but 4,600 of them, so newest first and capped, every board.
MAX_OFFICIAL_VOTES_PER_RUN = 40
MAX_OCR_PER_RUN = 40             # ~20 minutes of local CPU; nothing charged to the plan
SEARCH_PUSH_LIMIT = 20000       # rows; leaves the day's budget for a data push too
TRANSCRIPT_WINDOW_DAYS = 21     # captions are retried for meetings this recent
RUN_COLS = ['ran_at', 'as_of', 'new_agendas', 'new_minutes', 'new_videos',
            'new_transcripts', 'new_our_minutes', 'deployed', 'seconds', 'timings', 'notes',
            # `incomplete` until the run reaches its own end. A row that stays incomplete
            # is a run that died, and that is a fact worth keeping rather than an absence
            # to be guessed at. Old rows have no value here and read as finished, which
            # they are.
            'state']


TIMINGS = []          # (step, seconds, exit code) -- printed at the end and written to the run row



def record_run(a, delta, deployed, state, notes=()):
    """One row per day in refresh-runs.csv, written TWICE: once before the steps that can
    die, and again when the run finishes.

    The first write is the tombstone. Until 19 September 2026 this happened only at the
    end, so three consecutive failures left no trace at all and looked like quiet days.
    """
    runs = [r for r in read_csv(RUNS) if r['as_of'] != a.as_of]     # one row per day
    runs.append({'ran_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'as_of': a.as_of, 'new_agendas': delta['agendas'], 'new_minutes': delta['minutes'],
                 'new_videos': delta['videos'], 'new_transcripts': delta['transcripts'],
                 'new_our_minutes': delta['ours'], 'deployed': 'yes' if deployed else 'no',
                 'seconds': int(sum(t[1] for t in TIMINGS)),
                 'timings': ' '.join('%s=%d' % (n.replace(' ', '_'), int(sec)) for n, sec, _ in TIMINGS),
                 'notes': '; '.join(notes), 'state': state})
    with open(RUNS, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=RUN_COLS)
        w.writeheader()
        for r in sorted(runs, key=lambda r: r['as_of']):
            w.writerow({c: r.get(c, '') for c in RUN_COLS})


def sh(args, check=True, quiet=False, **kw):
    import time
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    name = os.path.basename(args[1] if args[0].endswith('python3') or 'python' in args[0] else args[0])
    if len(args) > 2 and not args[2].startswith('-'):
        name += ' ' + ' '.join(a for a in args[2:] if not a.startswith('-'))[:40]
    print('\n$ ' + ' '.join(args), flush=True)
    t0 = time.monotonic()
    kw.setdefault('cwd', ROOT)
    r = subprocess.run(args, env=env, capture_output=quiet, text=True, **kw)
    secs = time.monotonic() - t0
    TIMINGS.append((name, secs, r.returncode))
    print('  [%s: %.1fs, exit %d]' % (name, secs, r.returncode), flush=True)
    if check and r.returncode != 0:
        if quiet:
            print((r.stdout or '') + (r.stderr or ''))
        raise SystemExit('step failed: %s' % ' '.join(args))
    return r


def py(script, *args, **kw):
    return sh([sys.executable, os.path.join(SCRIPTS, script), *args], **kw)


def backfill_running():
    r = subprocess.run(['pgrep', '-f', '[r]un_transcript_backfill|[f]etch_youtube_transcripts'],
                       capture_output=True, text=True)
    return r.returncode == 0


def read_csv(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path, newline='', encoding='utf-8')))


def policy():
    return [r for r in read_csv(POLICY) if r.get('board_slug') and r.get('since')]


def covered(board_slug, date, rows):
    """The policy row that covers this recording, or None. `*` covers any board."""
    hits = [r for r in rows if r['board_slug'] in (board_slug, '*') and date >= r['since']]
    return min(hits, key=lambda r: int(r.get('priority') or 9)) if hits else None


def minutes_targets(rows):
    """Recordings inside the policy with a transcript on disk and no minutes yet."""
    out = []
    for t in read_csv(TRANSCRIPT_INDEX):
        row = covered(t['board_slug'], t['meeting_date'], rows)
        if not row:
            continue
        if not os.path.exists(os.path.join(ROOT, t['path'])):
            continue
        target = os.path.join(RECORDED, t['board_slug'], '%s-%s.json' % (t['meeting_date'], t['video_id']))
        if not os.path.exists(target):
            out.append(dict(t, priority=int(row.get('priority') or 9)))
    # THE LAST TWO YEARS FIRST, ACROSS EVERY BOARD; then priority; newest first inside
    # each. TJ, 17 September 2026: "work them in priority order, newest first. Last 2
    # years is most important across everything than deeper for more." Three a day at
    # the calibrated 0.09% of the weekly allowance per meeting.
    out.sort(key=lambda t: (0 if t['meeting_date'] >= recent_since() else 1, t['priority'], -int(t['meeting_date'].replace('-', ''))))
    return out


RECENT_YEARS = 2


def recent_since():
    return (dt.date.today() - dt.timedelta(days=365 * RECENT_YEARS)).isoformat()


MEETINGS_INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')


def adopt_new_meeting_documents(as_of):
    """Rows the watcher first saw today, appended to sources/meetings/index.csv with an
    empty path, for `fetch_agendas.py --backfill` to fetch. Never removes a row."""
    import re
    events = [e for e in read_csv(MEETING_EVENTS) if e['first_seen'] == as_of]
    if not events:
        return 0
    cols = ['board', 'board_id', 'date', 'kind', 'file_id', 'path', 'url']
    rows = read_csv(MEETINGS_INDEX)
    held = {(r['file_id'], r['kind']) for r in rows}
    board_id = {r['board']: r['board_id'] for r in rows if r.get('board_id')}
    added = 0
    for e in events:
        if (e['file_id'], e['kind']) in held:
            continue
        rows.append({'board': e['board'], 'board_id': board_id.get(e['board'], ''),
                     'date': e['meeting_date'], 'kind': e['kind'], 'file_id': e['file_id'],
                     'path': '', 'url': e['url']})
        held.add((e['file_id'], e['kind']))
        added += 1
    if added:
        rows.sort(key=lambda r: (r['board'], r['date'], r['kind']))
        tmp = MEETINGS_INDEX + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, '') for c in cols})
        os.replace(tmp, MEETINGS_INDEX)
        print('adopted %d new meeting document(s) into the catalogue' % added)
    return added


def whats_new(as_of, days=14):
    """The last two weeks of every event log, as one announcement payload."""
    since = (dt.date.fromisoformat(as_of) - dt.timedelta(days=days)).isoformat()
    me = [e for e in read_csv(MEETING_EVENTS) if e['first_seen'] >= since]
    ye = [e for e in read_csv(YOUTUBE_EVENTS) if e['first_seen'] >= since]
    ours = []
    for f in glob.glob(os.path.join(RECORDED, '*', '*.json')):
        m = json.load(open(f, encoding='utf-8'))
        when = (m.get('written') or {}).get('at', '')[:10]
        if when >= since:
            ours.append({'written': when, 'board': m['board'], 'board_slug': m['board_slug'],
                         'date': m['meeting_date'],
                         'url': '/meeting-minutes/%s/%s-%s' % (m['board_slug'], m['meeting_date'], m['video_id']),
                         'votes': sum(1 for v in m['minutes']['votes'] if not v.get('procedural'))})
    ours.sort(key=lambda x: (x['written'], x['date']), reverse=True)
    tr = [t for t in read_csv(TRANSCRIPT_INDEX) if (t.get('fetched_at') or '')[:10] >= since]
    fe = [e for e in read_csv(FEED_EVENTS) if e['first_seen'] >= since]
    de = [e for e in read_csv(DOC_EVENTS) if e['first_seen'] >= since]
    srcs = read_csv(FEED_SOURCES)
    return {
        'category': 'announcement',
        'not_a_measurement': 'What our watchers first saw, by the day they saw it. first_seen is our '
                             'crawl date, not the day the town posted anything.',
        'as_of': as_of,
        'window_days': days,
        'agendas': sorted([e for e in me if e['kind'] == 'agenda'], key=lambda e: (e['first_seen'], e['meeting_date']), reverse=True),
        'minutes': sorted([e for e in me if e['kind'] == 'minutes'], key=lambda e: (e['first_seen'], e['meeting_date']), reverse=True),
        'videos': sorted(ye, key=lambda e: (e['first_seen'], e['uploaded']), reverse=True),
        'transcripts': sorted([{'board_slug': t['board_slug'], 'date': t['meeting_date'], 'video_id': t['video_id'],
                                'fetched': (t.get('fetched_at') or '')[:10]} for t in tr],
                              key=lambda t: (t['fetched'], t['date']), reverse=True),
        'our_minutes': ours,
        'feeds': sorted(fe, key=lambda e: (e['published'], e['first_seen']), reverse=True),
        'documents': sorted([{**e, 'url': '/docs/' + e['local'][len('sources/'):] if e.get('local', '').startswith('sources/') else e.get('upstream', '')} for e in de],
                            key=lambda e: e['first_seen'], reverse=True),
        'feed_sources': {'watched': sum(1 for s in srcs if s.get('url')),
                         'without_a_feed': [s['source'] for s in srcs if not s.get('url')]},
        'counts': {'agendas': sum(1 for e in me if e['kind'] == 'agenda'),
                   'minutes': sum(1 for e in me if e['kind'] == 'minutes'),
                   'videos': len(ye), 'transcripts': len(tr), 'our_minutes': len(ours), 'feeds': len(fe), 'documents': len(de)},
    }


def write_to_post(as_of):
    """The Facebook texts, ready to paste, in build/ (gitignored) -- NOT on the site, which
    carries nothing addressed to us. One file, newest first, upcoming then retro."""
    p = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'notices.json'), encoding='utf-8'))
    out = os.path.join(ROOT, 'build', 'notices-to-post.md')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # NEW means written by this run: the preview or the minutes carry today's date. A
    # notice from an earlier day is still in the file -- the window is two weeks -- but
    # the heading says so, so the morning question "what do I post today" is the first
    # lines, not a diff.
    new_up = [u for u in p['upcoming'] if u.get('written') == as_of]
    new_re = [r for r in p['retro'] if r.get('written') == as_of]
    L = ['# Notices ready to post — as of %s' % as_of, '',
         '**New today: %d upcoming, %d what-happened.** Copy a block into Facebook. Nothing posts itself.'
         % (len(new_up), len(new_re)), '']
    for u in p['upcoming']:
        tag = 'NEW TODAY — ' if u.get('written') == as_of else ''
        L += ['## %sUPCOMING — %s, %s (%d day%s away)' % (tag, u['board'], u['date'], u['days_away'], '' if u['days_away'] == 1 else 's'), '', '```', u['facebook'], '```', '']
    for r in p['retro']:
        tag = 'NEW TODAY — ' if r.get('written') == as_of else ''
        L += ['## %sWHAT HAPPENED — %s, %s' % (tag, r['board'], r['date']), '', '```', r['facebook'], '```', '']
    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('\nREADY TO POST (%s): %d upcoming (%d new today), %d what-happened (%d new today)'
          % (os.path.relpath(out, ROOT), len(p['upcoming']), len(new_up), len(p['retro']), len(new_re)))
    for u in new_up:
        print('  NEW  upcoming  %s %s — %s' % (u['board'], u['date'], u['one_line'][:90]))
    for r in new_re:
        print('  NEW  happened  %s %s — %d vote(s), %d transfer(s)' % (r['board'], r['date'], r['votes'], r['transfers']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--deploy', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-minutes', action='store_true')
    ap.add_argument('--no-push', action='store_true', help='skip the search index push to D1')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    a = ap.parse_args()

    if a.check:
        bad = 0
        for s, args in (('watch_meetings.py', ['--check']), ('watch_youtube.py', ['--check']), ('watch_feeds.py', ['--check']), ('watch_documents.py', ['--check']),
                        ('write_recording_minutes.py', ['--check']), ('write_agenda_preview.py', ['--check']),
                        ('build_notices.py', ['--check']), ('build_meeting_feed.py', ['--check']),
                        ('build_boards.py', ['--check']), ('build_budget_feed.py', ['--check'])):
            bad += py(s, *args, check=False).returncode != 0
        return 1 if bad else 0

    before = {
        'agendas': sum(1 for e in read_csv(MEETING_EVENTS) if e['kind'] == 'agenda'),
        'minutes': sum(1 for e in read_csv(MEETING_EVENTS) if e['kind'] == 'minutes'),
        'videos': len(read_csv(YOUTUBE_EVENTS)),
        'transcripts': len(read_csv(TRANSCRIPT_INDEX)),
        'ours': len(glob.glob(os.path.join(RECORDED, '*', '*.json'))),
    }
    notes = []

    # 1-3. The town's documents.
    py('watch_meetings.py', '--as-of', a.as_of, *(['--dry-run'] if a.dry_run else []))
    if not a.dry_run:
        # THE WATCHER'S LISTING IS THE FETCHER'S LIST. The fetcher used to re-list all 51
        # boards a minute after the watcher had -- the same requests twice. Now the
        # documents the watcher saw today are adopted into the catalogue with no path,
        # and `--backfill` fetches exactly those rows and fills the path in.
        n = adopt_new_meeting_documents(a.as_of)
        if n:
            py('fetch_agendas.py', '--backfill')
        py('extract_minutes.py')
        py('build_minutes_searchable.py')
        if not a.no_minutes:
            py('write_agenda_preview.py', '--upcoming', '--as-of', a.as_of, check=False)

    # 3d. New DOCUMENTS on the district's budget page and the town's finance pages --
    # the listing pages the archive was built from, re-walked; a shrunken index is
    # refused. TJ: "look for new documents posted from the school committee (budget
    # related), as well as on the town pages from the areas we've found."
    py('watch_documents.py', '--as-of', a.as_of, *(['--dry-run'] if a.dry_run else []), check=False)
    # 4a. A NEW BUDGET DOCUMENT IS READ THE MORNING IT APPEARS. TJ, 16 September 2026:
    # "anytime a new doc is 'found', we need to identify if it impacts the budget feed and
    # process it right then and there." One read per document, page-cited, into the same
    # budget-state shape the feed and the season boards already draw from.
    if not a.dry_run:
        py('write_document_budget_state.py', '--new', '--as-of', a.as_of, '--limit', '3', check=False)

    # 3c. The town's and the community's feeds -- news, alerts, registrations. Linked and
    # attributed, never republished (QUEUE 13, 14).
    py('watch_feeds.py', '--as-of', a.as_of, *(['--dry-run'] if a.dry_run else []), check=False)

    # 4-6. The town's recordings.
    py('watch_youtube.py', '--as-of', a.as_of, *(['--dry-run'] if a.dry_run else []))
    if not a.dry_run:
        py('build_youtube_classification.py')
        if backfill_running():
            notes.append('transcript fetch skipped: the backfill is running')
            print('\nthe transcript backfill is running; not competing with it for captions')
        else:
            since = (dt.date.fromisoformat(a.as_of) - dt.timedelta(days=TRANSCRIPT_WINDOW_DAYS)).isoformat()
            py('fetch_youtube_transcripts.py', '--since', since, '--limit', '12', '--sleep', '45', check=False)

    # 7. Our minutes, inside the policy, capped.
    if not a.dry_run and not a.no_minutes:
        rows = policy()
        targets = minutes_targets(rows)
        if len(targets) > MAX_MINUTES_PER_RUN:
            notes.append('%d recordings await minutes; wrote %d' % (len(targets), MAX_MINUTES_PER_RUN))
        for t in targets[:MAX_MINUTES_PER_RUN]:
            py('write_recording_minutes.py', t['board_slug'], t['meeting_date'], check=False)

    # 7b. SCANNED MINUTES, OCR'D -- local, free, about half a minute each; newest first.
    if not a.dry_run and not a.no_minutes:
        py('ocr_scanned_minutes.py', '--limit', str(MAX_OCR_PER_RUN), check=False)

    # 7c. THE TOWN'S MINUTES, READ FOR THEIR VOTES -- every board, newest first, capped.
    # build_boards.py joins these with our recording minutes at build time, so the two
    # records can arrive in either order (TJ, 17 September 2026). Runs after the OCR so
    # a scan read today is read for its votes today.
    if not a.dry_run and not a.no_minutes:
        py('extract_official_votes.py', '--limit', str(MAX_OFFICIAL_VOTES_PER_RUN), check=False)

    # 7a. The budget state of the three budget boards' recordings -- the deficit, the cuts,
    # the warnings as put on the record -- newest first, capped like the minutes. A file
    # behind the extraction's schema counts as work, so a schema change backfills itself
    # at MAX_MINUTES_PER_RUN a day rather than in one expensive batch.
    if not a.dry_run and not a.no_minutes:
        since = (dt.date.fromisoformat(a.as_of) - dt.timedelta(days=400)).isoformat()
        # ONLY THE CATCH-UP. A new meeting's budget state now comes out of the same read
        # as its minutes (step 6), so this reads only meetings that already have minutes
        # from before the merge, or files behind the schema -- never a meeting the minutes
        # step will read anyway. TJ: "it will save both TOKENS and time."
        py('write_budget_state.py', '--since', since, '--limit', str(MAX_MINUTES_PER_RUN), '--with-minutes-only', check=False)

    # 7a'. The live season's board, re-read from the record: warnings straight onto the
    # page, figures and cuts PROPOSED into budget-seasons/fy28.proposed.csv for a person to
    # confirm by copying a row into fy28.csv. Nothing with a figure appears unconfirmed.
    if not a.dry_run:
        py('build_budget_season.py', 'fy28', check=False)
        try:
            import csv as _csv
            pp = os.path.join(ROOT, 'sources', 'data', 'budget-seasons', 'fy28.proposed.csv')
            n = sum(1 for _ in _csv.DictReader(open(pp, encoding='utf-8'))) if os.path.exists(pp) else 0
            if n:
                notes.append('%d row(s) proposed for the FY28 board in sources/data/budget-seasons/fy28.proposed.csv -- confirm by copying into fy28.csv' % n)
        except Exception as e:
            notes.append('could not count proposed season rows: %s' % e)

    # 7b. Against the town's minutes, wherever both now exist. Official minutes appear
    # weeks after a meeting, so this is asked every day and does work only when new.
    if not a.dry_run and not a.no_minutes:
        py('reconcile_minutes.py', check=False)

    # 8. Rebuild everything derived from the above.
    if not a.dry_run:
        # THE ONE MEETING RECORD, before anything that lists meetings reads it.
        py('extract_document_timestamps.py', '--quiet')
        py('build_meeting_register.py')
        py('build_meeting_feed.py')
        py('build_recording_minutes.py')
        py('build_notices.py')
        py('build_boards.py', '--as-of', a.as_of)
        py('build_budget_feed.py', '--as-of', a.as_of)
        py('build_feeds.py')
        # A new budget episode the feed thinks it sees -- a Special Town Meeting date, an
        # override, the Governor's budget, the season opening -- is PROPOSED here, with its
        # evidence, for TJ or the agent to confirm by adding a row to budget-episodes.csv.
        try:
            feed = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'budget-feed.json')))
            for p in feed.get('proposed_episodes', []):
                notes.append('possible new budget episode: %s (%s) -- add to sources/data/budget-episodes.csv if real' % (p['signal'], p['evidence']))
            # A story forming that no thread names -- 'athletics' in 23 lines across 9 meetings --
            # is proposed the same way; a row in sources/data/budget-threads.csv makes it one.
            for p in feed.get('proposed_threads', [])[:5]:
                notes.append('a budget story may be forming: %s -- %d lines across %d meetings, %s to %s; add to sources/data/budget-threads.csv to give it a thread'
                             % (p['name'], p['rows'], p['meetings'], p['first'], p['last']))
        except Exception as e:
            notes.append('could not read proposed episodes: %s' % e)
        # The finished seasons, rebuilt too: their calendars and minutes counts move as the
        # archive fills in. Each closes on its election day (sources/data/budget-cycles.csv).
        for fy, closes in (('fy26', '2025-05-17'), ('fy27', '2026-05-16')):
            py('build_budget_feed.py', '--as-of', closes, '--out', 'fy28/public/data/budget-feed-%s.json' % fy)
        py('tag_document_affinity.py', check=False)     # only documents not yet tagged; cents
        py('build_search_index.py', '--quiet')
        py('build_app_metrics.py')
        py('build_sitemap.py')
        # WHAT READERS HAVE ASKED, pulled off the questions database so an unanswered
        # question cannot sit with no sign of it anywhere a person looks. Counts only --
        # no bodies, no email addresses. check=False because a courtesy must not fail the
        # night's ingestion.
        py('pull_questions.py', check=False)
        py('build_agentic_backlog.py', check=False)     # where every machine-reading stream stands, notes/generated/AGENTIC-BACKLOG.md
        # 9. The search index to D1 -- the analysis database push is NOT run here.
        if not a.no_push:
            py('sync_search_d1.py', '--limit', str(SEARCH_PUSH_LIMIT), check=False)
        # 10. THE DOCUMENTS THEMSELVES TO THE BUCKET. The refresh fetches the town's new
        # PDFs into its own worktree, but git carries only the manifest and the text --
        # so a document fetched here and never pushed exists on one disk and nowhere
        # else (a Stormwater agenda went that way on 17 September 2026). New keys only.
        if not a.no_push:
            py('sync_archive.py', '--manifest', check=False)
            py('sync_archive.py', '--push', check=False)

    after = {
        'agendas': sum(1 for e in read_csv(MEETING_EVENTS) if e['kind'] == 'agenda'),
        'minutes': sum(1 for e in read_csv(MEETING_EVENTS) if e['kind'] == 'minutes'),
        'videos': len(read_csv(YOUTUBE_EVENTS)),
        'transcripts': len(read_csv(TRANSCRIPT_INDEX)),
        'ours': len(glob.glob(os.path.join(RECORDED, '*', '*.json'))),
    }
    delta = {k: after[k] - before[k] for k in after}

    # 10. The site, only when asked.
    deployed = False
    # DEPLOY ONLY FROM MAIN, or from the refresh tree's branch that IS main. Cloudflare
    # Pages sends any other branch to a preview alias and the log would still say
    # "deployed" -- which is exactly what happened on 15 September 2026.
    if a.deploy and not a.dry_run:
        branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
        if branch not in ('main', 'refresh'):
            print('  NOT deploying: on branch %r, and only main deploys to production. '
                  'Run the refresh from the refresh tree (scripts/daily_refresh.sh) or check out main.' % branch)
            a.deploy = False
    if a.deploy and not a.dry_run:
        sh(['npm', 'run', 'build:site'], cwd=os.path.join(ROOT, 'fy28'))
        sh(['npx', 'wrangler', 'pages', 'deploy'], cwd=os.path.join(ROOT, 'fy28'))
        deployed = True

    # THE ROW GOES IN BEFORE THE RISKY PART, NOT AFTER IT.
    #
    # It used to be appended at the very end, so a run that died anywhere earlier left
    # NOTHING -- and no row reads as a quiet day, not as a failure. The refresh failed on
    # 16, 17 and 18 September 2026 (build_search_index.py, `database or disk is full`) and
    # refresh-runs.csv simply stopped at the 15th. Nobody knew for four days.
    #
    # A registry written only by success cannot record a failure, which is the one thing
    # it most needs to record. So the row is written here, marked `incomplete`, and
    # updated to the finished state at the end. A run that dies now leaves its own
    # tombstone with what it had found before it went.
    if not a.dry_run:
        record_run(a, delta, deployed=False, state='incomplete')
        write_to_post(a.as_of)
        payload = whats_new(a.as_of)
        with open(WHATS_NEW, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False)
            fh.write('\n')
        record_run(a, delta, deployed, 'ok', notes)

    total = sum(t[1] for t in TIMINGS)
    print('\n=== refresh %s — %d min %d s ===' % (a.as_of, total // 60, total % 60))
    print('  %-46s %8s' % ('step', 'seconds'))
    for name, secs, rc in sorted(TIMINGS, key=lambda t: -t[1]):
        print('  %-46s %8.1f%s' % (name[:46], secs, '' if rc == 0 else '  exit %d' % rc))
    print('  new agendas %d · new minutes %d · new videos %d · new transcripts %d · our minutes +%d'
          % (delta['agendas'], delta['minutes'], delta['videos'], delta['transcripts'], delta['ours']))
    for n in notes:
        print('  note: ' + n)
    print('  deployed' if deployed else '  not deployed (pass --deploy)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
