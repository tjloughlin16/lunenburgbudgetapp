#!/usr/bin/env python3
"""IS THE BACKLOG RUN AT THE PACE IT SHOULD BE? One line and an exit code. Read-only, free.

    python3 scripts/backlog_pace.py          # e.g.  ok  $6.10/h  43 mtg/h  last 1m ago  chain up
    python3 scripts/backlog_pace.py --watch  # every 10 min to build/backlog-pace.log; on a
                                             # problem: build/backlog-pace.ALERT + a Mac
                                             # notification, and exit

TJ, 7 October 2026: *"check in to make sure its going as expected ... without you consume
massive context each time. last time we did something similar, you burned through 20-30%
of weekly usage with 0 gain."* A check-in by an agent costs a turn of a long session; this
costs nothing, and wakes the session only when there is something to look at.

EXPECTED, from process_meeting.py's docstring (one serial run, 7 October): ~$6 an hour,
~42 meetings an hour. The band is wide on purpose -- $2 to $10 an hour over the last 60
minutes -- because the point is to catch a runaway (two streams, a retry loop) or a stall,
not to police a slow meeting. And SPEND PER OUTPUT: over $0.50 a produced file in the last
hour (expected ~$0.14), once $1 has been spent, trips -- $100 for one meeting cannot pass. A stall is no costed row for 15 minutes, unless the chain
says it is waiting for the window to reset.

Health is read from OUTPUT (agentic-spend.csv), never from a process being alive --
sweep_health.py's lesson.

AND THE SPEND IS MATCHED TO THE OUTPUT, ONE TO ONE. TJ, 7 October 2026: *"i'd like you to
be able to directly check to make sure the spend is matching the output of minutes of the
period of time. no mistakes."* Every costed row in agentic-spend.csv must have a file it
paid for: a JSON under sources/data/official-votes/ or recording-minutes/ for the same
board and date, written within two minutes of the row, carrying the SAME cost_usd. An
official read must also be schema 2 and hash the minutes text it names as it is on disk
now. A paid row with no such file is money for nothing, and is a problem. A file written
in the window with no paid row is reported too. Rows under two minutes old are left for
the next pass (the file and the row are written moments apart).

    python3 scripts/backlog_pace.py --audit 2026-10-07T14:22   # every row since then (UTC)
"""
import csv
import glob
import hashlib
import json
import datetime as dt
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEND = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')
ALERT = os.path.join(ROOT, 'build', 'backlog-pace.ALERT')
OUT = os.path.join(ROOT, 'build', 'backlog-pace.log')
LO, HI, STALE_MIN = 2.0, 10.0, 15


OUT_DIRS = ('official-votes', 'recording-minutes')


def audit(since_utc, now=None):
    """(matched, [unmatched rows], [unpaid files]) for every costed row at or after
    `since_utc` ('YYYY-MM-DDTHH:MM', UTC). See the docstring for what a match is."""
    now = now or dt.datetime.now(dt.timezone.utc)
    t = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    rows = [r for r in csv.DictReader(open(SPEND, encoding='utf-8'))
            if r.get('at', '') >= since_utc and (now - t(r['at'])).total_seconds() > 120]
    used, matched, bad = set(), 0, []
    for r in rows:
        hit = None
        for d in OUT_DIRS:
            for f in glob.glob(os.path.join(ROOT, 'sources', 'data', d, r['board'], r['date'] + '*.json')):
                if f in used:
                    continue
                m = dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc)
                if abs((m - t(r['at'])).total_seconds()) > 120:
                    continue
                try:
                    j = json.load(open(f, encoding='utf-8'))
                except ValueError:
                    continue
                if j.get('cost_usd') is not None and abs(float(j['cost_usd']) - float(r['cost_usd'] or 0)) > 0.0001:
                    continue
                if d == 'official-votes' and r['stream'].startswith('official'):
                    src = (j.get('source') or {})
                    txt = os.path.join(ROOT, src.get('text', ''))
                    if (j.get('schema') or 0) < 2 or not os.path.exists(txt) or \
                            hashlib.sha256(open(txt, 'rb').read()).hexdigest() != src.get('sha256'):
                        continue
                hit = f
                break
            if hit:
                break
        if not hit:
            # ONE STEP, SEVERAL DOCUMENTS. A meeting the town filed two sets of minutes for
            # (conservation-commission 2025-12-17: -7569 and -7571) is read in one step and
            # logged as ONE row whose cost is the SUM. Match the row to every file for that
            # board and date written during the step whose costs add up to it.
            group, total = [], 0.0
            for d in OUT_DIRS:
                for f in glob.glob(os.path.join(ROOT, 'sources', 'data', d, r['board'], r['date'] + '*.json')):
                    m = dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc)
                    if f in used or not (-900 <= (m - t(r['at'])).total_seconds() <= 120):
                        continue
                    try:
                        c = json.load(open(f, encoding='utf-8')).get('cost_usd')
                    except ValueError:
                        continue
                    if c is not None:
                        group.append(f)
                        total += float(c)
            if len(group) > 1 and abs(total - float(r['cost_usd'] or 0)) <= 0.001:
                used.update(group)
                matched += 1
                continue
        if hit:
            used.add(hit)
            matched += 1
        else:
            bad.append('%s %s %s %s $%s' % (r['at'], r['stream'], r['board'], r['date'], r['cost_usd']))
    lo = t(since_utc + ':00Z' if len(since_utc) == 16 else since_utc)
    unpaid = [os.path.relpath(f, ROOT) for d in OUT_DIRS
              for f in glob.glob(os.path.join(ROOT, 'sources', 'data', d, '*', '*.json'))
              if f not in used and lo.timestamp() <= os.path.getmtime(f) <= now.timestamp() - 120]
    return matched, bad, unpaid


def guard(now=None):
    """The OUTPUT checks alone -- spend matched to files, cost per file, REPEATING -- over
    the last hour. [] when healthy. process_meeting.py --until-usage calls this before it
    starts each meeting, so a run whose spend stops producing minutes stops itself."""
    now = now or dt.datetime.now(dt.timezone.utc)
    hour_ago = (now - dt.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
    rows = [r for r in csv.DictReader(open(SPEND, encoding='utf-8')) if r.get('at', '') >= hour_ago]
    usd = sum(float(r['cost_usd'] or 0) for r in rows)
    problems = []
    matched, unmatched, unpaid = audit(hour_ago, now)
    if unmatched:
        problems.append('%d paid call(s) with no output: %s' % (len(unmatched), unmatched[0]))
    if unpaid:
        problems.append('%d output file(s) with no paid call: %s' % (len(unpaid), unpaid[0]))
    # THE RATIO, which is what TJ asked for in so many words: *"if we spend $100 and get 1 or
    # 0 meetings, something should trip."* A meeting costs ~$0.14; trip at $0.50 a produced
    # file over the last hour, once at least $1 has been spent.
    per = usd / matched if matched else float('inf')
    if usd >= 1 and per > 0.50:
        problems.append('$%.2f spent for %d output file(s) in the last hour -- $%s each, expected ~$0.14'
                        % (usd, matched, 'inf' if not matched else '%.2f' % per))
    # REPEATING: the same step paid for the same meeting twice inside the hour. Every step
    # is skipped once done, so a second paid call means the save did not take and the run
    # is going round -- the shape of the 6 October runaway, which spun on refused calls.
    seen = {}
    for r in rows:
        k = (r['stream'], r['board'], r['date'])
        seen[k] = seen.get(k, 0) + 1
    again = [k for k, n in seen.items() if n > 1]
    if again:
        problems.append('REPEATING: %d meeting step(s) paid for twice this hour, e.g. %s %s %s'
                        % ((len(again),) + again[0]))
    return problems, matched, len(unmatched)


def check():
    now = dt.datetime.now(dt.timezone.utc)
    rows = [r for r in csv.DictReader(open(SPEND, encoding='utf-8'))
            if r.get('at', '') >= (now - dt.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')]
    usd = sum(float(r['cost_usd'] or 0) for r in rows)
    last = max((dt.datetime.fromisoformat(r['at'].replace('Z', '+00:00')) for r in rows), default=None)
    ago = (now - last).total_seconds() / 60 if last else None
    chain = subprocess.run(['pgrep', '-f', '[r]un_backlog_until'], capture_output=True).returncode == 0
    run = subprocess.run(['pgrep', '-f', '[p]rocess_meeting.py --(next|until-usage)'], capture_output=True).returncode == 0
    log = os.path.join(ROOT, 'build', 'process-meeting-%s.log' % dt.date.today().isoformat())
    tail = open(log, encoding='utf-8', errors='replace').read()[-4000:] if os.path.exists(log) else ''
    waiting = 'waiting for the window to reset' in tail.rsplit('chunk of', 1)[-1]
    problems, matched, n_unmatched = guard(now)
    if 'STOPPED' in tail.rsplit('chunk of', 1)[-1]:
        problems.append('a run STOPPED')
    if not chain and not run:
        problems.append('nothing running')
    elif not waiting:
        if ago is None or ago > STALE_MIN:
            problems.append('STUCK: running, but no costed call for %s min' % ('60+' if ago is None else int(ago)))
    line = '%s  %s  $%.2f/h  %d mtg/h  %d/%d paid calls matched to output  last %s ago  chain %s%s' % (
        dt.datetime.now().strftime('%H:%M'), 'PROBLEM: ' + '; '.join(problems) if problems else 'ok',
        usd, len(rows), matched, matched + n_unmatched, '%dm' % ago if ago is not None else 'none', 'up' if chain else 'down',
        '  (waiting for reset)' if waiting else '')
    return line, problems


def main():
    if '--audit' in sys.argv:
        since = sys.argv[sys.argv.index('--audit') + 1]
        matched, unmatched, unpaid = audit(since)
        print('%d of %d paid calls since %s matched to an output file' % (matched, matched + len(unmatched), since))
        for u in unmatched:
            print('  PAID, NO OUTPUT:', u)
        for u in unpaid:
            print('  OUTPUT, NOT PAID:', u)
        return 1 if unmatched or unpaid else 0
    if '--watch' not in sys.argv:
        line, p = check()
        print(line)
        return 1 if p else 0
    # INTO THE RUN'S OWN LOG TOO, as `[watch HH:MM] ...` -- TJ tails that log through
    # `grep -E "^\[|wrote|FAILED|STOPPED|done|completed"`, and a line starting `[` shows up
    # there. A problem is written every pass while it lasts (STUCK or REPEATING in the
    # line); an `ok` once an hour, so silence there means the watcher is down, not well.
    # The ALERT file and the notification fire once, on the first problem.
    alerted, last_ok = False, 0
    while True:
        line, p = check()
        open(OUT, 'a').write(line + '\n')
        run_log = os.path.join(ROOT, 'build', 'process-meeting-%s.log' % dt.date.today().isoformat())
        if p or time.time() - last_ok >= 3600:
            open(run_log, 'a').write('[watch %s] %s\n' % (line[:5], line[7:]))
            if not p:
                last_ok = time.time()
        if p and not alerted:
            open(ALERT, 'w').write(line + '\n')
            subprocess.run(['osascript', '-e', 'display notification "%s" with title "Backlog run"'
                            % line.replace('"', "'")[:200]])
            alerted = True
        if p and 'nothing running' in line:
            return 1                     # the run is over; nothing left to watch
        time.sleep(600)


if __name__ == '__main__':
    sys.exit(main())
