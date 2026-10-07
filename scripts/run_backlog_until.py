#!/usr/bin/env python3
"""KEEP ONE BACKLOG RUN GOING UNTIL A CLOCK TIME -- serially, and never past a stop.

    python3 scripts/run_backlog_until.py --until 21:00 --resets 16:40

TJ, 7 October 2026: *"the goal is to reach session limit close to the end of the session,
which gives me flexibility to change direction at any time"* -- and *"DO NOT crush the
session immediately like we accidentally did before."* One serial `process_meeting.py`
run IS that pace (~16% of a five-hour window an hour, ~80% over five hours; its docstring
and notes/findings/METERED-BATCH-COST.md section 6). What it lacks is CONTINUITY: a chunk
ends and the window sits idle. This chains chunks, ONE AT A TIME, and adds no speed.

A WRAPPER LOOP IS HOW THE 6 OCTOBER RUNAWAY HAPPENED -- one spun three and a half hours on
169 refused calls. So this one stops, rather than retries, on everything but one case:

  * build/STOP-METERED exists                      stop (TJ's kill switch; never deleted here)
  * the clock passes --until                        stop (checked between chunks; chunks are
                                                    small so the overrun is under an hour)
  * a chunk finds nothing to do                     stop
  * a chunk STOPPED for any reason but a limit      stop
  * a chunk STOPPED on a usage/session LIMIT        wait for the next --resets time, then ONE
                                                    more chunk; a second limit stops for good
  * another process_meeting run holds the lock      wait for it to finish, then chain

Appends to build/process-meeting-<date>.log, the same log the watcher greps.
"""
import argparse
import datetime as dt
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOP = os.path.join(ROOT, 'build', 'STOP-METERED')


def at(hhmm):
    h, m = map(int, hhmm.split(':'))
    return dt.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)


def running():
    return subprocess.run(['pgrep', '-f', '[p]rocess_meeting.py --next'], capture_output=True).returncode == 0


def say(msg):
    print('[run_backlog_until %s] %s' % (dt.datetime.now().strftime('%H:%M'), msg), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--until', required=True, help='HH:MM today; no chunk starts after it')
    ap.add_argument('--resets', default='', help='HH:MM,... when the session window resets')
    ap.add_argument('--chunk', type=int, default=40, help='meetings per run (~1 hour at 40)')
    a = ap.parse_args()
    until = at(a.until)
    resets = sorted(at(t) for t in a.resets.split(',') if t)
    log = os.path.join(ROOT, 'build', 'process-meeting-%s.log' % dt.date.today().isoformat())
    limits = 0
    while True:
        if os.path.exists(STOP):
            return say('STOPPED: build/STOP-METERED exists') or 0
        if running():
            time.sleep(60)
            continue
        if dt.datetime.now() >= until:
            return say('done: it is past %s' % a.until) or 0
        say('chunk of %d' % a.chunk)
        with open(log, 'a') as fh:
            p = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'process_meeting.py'),
                                '--next', str(a.chunk)], stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT)
        tail = open(log, encoding='utf-8', errors='replace').read()[-3000:]
        if p.returncode == 0:
            if '\n0 meeting(s)' in tail or tail.rstrip().endswith('nothing to do'):
                return say('STOPPED: nothing left to do') or 0
            continue
        if 'STOPPED: a limit' in tail.rsplit('\n0 meeting', 1)[-1] and limits == 0:
            nxt = next((r for r in resets if r > dt.datetime.now()), None)
            if nxt and nxt < until:
                limits += 1
                say('a limit; waiting for the window to reset at %s' % nxt.strftime('%H:%M'))
                time.sleep((nxt - dt.datetime.now()).total_seconds() + 120)
                continue
        return say('STOPPED: the chunk exited %d -- see the log above' % p.returncode) or 1


if __name__ == '__main__':
    sys.exit(main())
