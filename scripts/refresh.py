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
  4. watch_youtube       what appeared on the town's channel (the RSS feed, no key)
  5. classification      which board a new video belongs to, from its title
  6. transcripts         captions for recent meetings -- re-tried every run, because
                         YouTube's auto-captions arrive hours to days after the upload
  7. minutes             OUR minutes, for recordings inside the approved POLICY only
  8. rebuild             the feed, the minutes payload, the notices, the index, the metrics
  9. push                the search index to D1, inside the day's write budget
 10. deploy              only with --deploy. Rule 10: nothing deploys without being asked.

THE POLICY FILE IS THE APPROVAL. `sources/data/recording-minutes-policy.csv` names which
boards, from which date, TJ has approved minutes for. Step 7 writes minutes for a
recording only if a policy row covers it, and at most MAX_MINUTES_PER_RUN of them, because
that step costs money per meeting and everything else here is free.

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
TRANSCRIPT_INDEX = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
RECORDED = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MAX_MINUTES_PER_RUN = 6
SEARCH_PUSH_LIMIT = 20000       # rows; leaves the day's budget for a data push too
TRANSCRIPT_WINDOW_DAYS = 21     # captions are retried for meetings this recent
RUN_COLS = ['ran_at', 'as_of', 'new_agendas', 'new_minutes', 'new_videos',
            'new_transcripts', 'new_our_minutes', 'deployed', 'seconds', 'timings', 'notes']


TIMINGS = []          # (step, seconds, exit code) -- printed at the end and written to the run row


def sh(args, check=True, quiet=False, **kw):
    import time
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    name = os.path.basename(args[1] if args[0].endswith('python3') or 'python' in args[0] else args[0])
    if len(args) > 2 and not args[2].startswith('-'):
        name += ' ' + ' '.join(a for a in args[2:] if not a.startswith('-'))[:40]
    print('\n$ ' + ' '.join(args), flush=True)
    t0 = time.monotonic()
    r = subprocess.run(args, cwd=ROOT, env=env, capture_output=quiet, text=True, **kw)
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
    return any(r['board_slug'] == board_slug and date >= r['since'] for r in rows)


def minutes_targets(rows):
    """Recordings inside the policy with a transcript on disk and no minutes yet."""
    out = []
    for t in read_csv(TRANSCRIPT_INDEX):
        if not covered(t['board_slug'], t['meeting_date'], rows):
            continue
        if not os.path.exists(os.path.join(ROOT, t['path'])):
            continue
        target = os.path.join(RECORDED, t['board_slug'], '%s-%s.json' % (t['meeting_date'], t['video_id']))
        if not os.path.exists(target):
            out.append(t)
    out.sort(key=lambda t: t['meeting_date'], reverse=True)
    return out


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
                         'url': '/what-was-said/%s/%s-%s' % (m['board_slug'], m['meeting_date'], m['video_id']),
                         'votes': sum(1 for v in m['minutes']['votes'] if not v.get('procedural'))})
    ours.sort(key=lambda x: (x['written'], x['date']), reverse=True)
    tr = [t for t in read_csv(TRANSCRIPT_INDEX) if (t.get('fetched_at') or '')[:10] >= since]
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
        'counts': {'agendas': sum(1 for e in me if e['kind'] == 'agenda'),
                   'minutes': sum(1 for e in me if e['kind'] == 'minutes'),
                   'videos': len(ye), 'transcripts': len(tr), 'our_minutes': len(ours)},
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
        for s, args in (('watch_meetings.py', ['--check']), ('watch_youtube.py', ['--check']),
                        ('write_recording_minutes.py', ['--check']), ('write_agenda_preview.py', ['--check']),
                        ('build_notices.py', ['--check']), ('build_meeting_feed.py', ['--check'])):
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
        year = a.as_of[:4]
        py('fetch_agendas.py', '--from', year, '--to', year)
        py('extract_minutes.py')
        py('build_minutes_searchable.py')
        if not a.no_minutes:
            py('write_agenda_preview.py', '--upcoming', '--as-of', a.as_of, check=False)

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

    # 8. Rebuild everything derived from the above.
    if not a.dry_run:
        py('build_meeting_feed.py')
        py('build_recording_minutes.py')
        py('build_notices.py')
        py('build_search_index.py', '--quiet')
        py('build_app_metrics.py')
        py('build_sitemap.py')
        # 9. The search index to D1 -- the analysis database push is NOT run here.
        if not a.no_push:
            py('sync_search_d1.py', '--limit', str(SEARCH_PUSH_LIMIT), check=False)

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
    if a.deploy and not a.dry_run:
        sh(['npm', 'run', 'build:site'], cwd=os.path.join(ROOT, 'fy28'))
        sh(['npx', 'wrangler', 'pages', 'deploy'], cwd=os.path.join(ROOT, 'fy28'))
        deployed = True

    if not a.dry_run:
        write_to_post(a.as_of)
        payload = whats_new(a.as_of)
        with open(WHATS_NEW, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False)
            fh.write('\n')
        runs = [r for r in read_csv(RUNS) if r['as_of'] != a.as_of]     # one row per day
        runs.append({'ran_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                     'as_of': a.as_of, 'new_agendas': delta['agendas'], 'new_minutes': delta['minutes'],
                     'new_videos': delta['videos'], 'new_transcripts': delta['transcripts'],
                     'new_our_minutes': delta['ours'], 'deployed': 'yes' if deployed else 'no',
                     'seconds': int(sum(t[1] for t in TIMINGS)),
                     'timings': ' '.join('%s=%d' % (n.replace(' ', '_'), int(sec)) for n, sec, _ in TIMINGS),
                     'notes': '; '.join(notes)})
        with open(RUNS, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=RUN_COLS)
            w.writeheader()
            for r in runs:
                w.writerow({c: r.get(c, '') for c in RUN_COLS})

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
