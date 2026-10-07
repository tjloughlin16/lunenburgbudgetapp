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
not to police a slow meeting. A stall is no costed row for 15 minutes, unless the chain
says it is waiting for the window to reset.

Health is read from OUTPUT (agentic-spend.csv), never from a process being alive --
sweep_health.py's lesson.
"""
import csv
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


def check():
    now = dt.datetime.now(dt.timezone.utc)
    rows = [r for r in csv.DictReader(open(SPEND, encoding='utf-8'))
            if r.get('at', '') >= (now - dt.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')]
    usd = sum(float(r['cost_usd'] or 0) for r in rows)
    last = max((dt.datetime.fromisoformat(r['at'].replace('Z', '+00:00')) for r in rows), default=None)
    ago = (now - last).total_seconds() / 60 if last else None
    chain = subprocess.run(['pgrep', '-f', '[r]un_backlog_until'], capture_output=True).returncode == 0
    run = subprocess.run(['pgrep', '-f', '[p]rocess_meeting.py --next'], capture_output=True).returncode == 0
    log = os.path.join(ROOT, 'build', 'process-meeting-%s.log' % dt.date.today().isoformat())
    tail = open(log, encoding='utf-8', errors='replace').read()[-4000:] if os.path.exists(log) else ''
    waiting = 'waiting for the window to reset' in tail.rsplit('chunk of', 1)[-1]
    problems = []
    if 'STOPPED' in tail.rsplit('chunk of', 1)[-1]:
        problems.append('a run STOPPED')
    if not chain and not run:
        problems.append('nothing running')
    elif not waiting:
        if ago is None or ago > STALE_MIN:
            problems.append('no costed call for %s min' % ('60+' if ago is None else int(ago)))
        if usd > HI:
            problems.append('spend $%.2f/h is above $%g -- too fast' % (usd, HI))
    line = '%s  %s  $%.2f/h  %d mtg/h  last %s ago  chain %s%s' % (
        dt.datetime.now().strftime('%H:%M'), 'PROBLEM: ' + '; '.join(problems) if problems else 'ok',
        usd, len(rows), '%dm' % ago if ago is not None else 'none', 'up' if chain else 'down',
        '  (waiting for reset)' if waiting else '')
    return line, problems


def main():
    if '--watch' not in sys.argv:
        line, p = check()
        print(line)
        return 1 if p else 0
    while True:
        line, p = check()
        open(OUT, 'a').write(line + '\n')
        if p:
            open(ALERT, 'w').write(line + '\n')
            subprocess.run(['osascript', '-e', 'display notification "%s" with title "Backlog run"'
                            % line.replace('"', "'")])
            return 1
        time.sleep(600)


if __name__ == '__main__':
    sys.exit(main())
