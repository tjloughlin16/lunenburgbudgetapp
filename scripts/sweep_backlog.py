#!/usr/bin/env python3
"""The pre-reset sweep: spend the week's unused allowance on the backlog, and stop the
moment the plan says no.

    python3 scripts/sweep_backlog.py --until 22:55          # run until this local time, then stop
    python3 scripts/sweep_backlog.py --until 22:55 --now    # ...even though TJ is active right now
    python3 scripts/sweep_backlog.py --dry-run

WHY. The Max plan is a weekly cap that resets Wednesday 10:59 pm (America/New_York) and a
rolling five-hour window; what is unused at the reset is gone. TJ, 17 September 2026:
"I want to optimize to use every possible token available for the month ... make sure I
can still work with you on a lot of projects and not max out for this agentic processing,
but at the end I don't want wasted tokens that could have cleared this backlog."

So: the daily caps in refresh.py stay small all week, and this runs in the last stretch
before the reset, working the backlog newest-first, one job at a time per stream, until
one of four things happens:

  * the clock reaches --until (set it a few minutes before the reset);
  * the CLI refuses for a usage or rate limit -- the signal that the week is spent, and
    harmless this close to the reset;
  * a job fails for any other reason (stop rather than guess);
  * TJ is working: a session transcript under ~/.claude/projects changed in the last
    ACTIVE_MINUTES. Overridden by --now, for a night he is watching it run.

Every job's cost lands in sources/data/agentic-spend.csv, so the week's scripted spend
is a number and not a feeling. Order: votes from the town's minutes (cheap, many), then
our minutes of recordings (dearer), each newest first and inside the two-year window
before anything older -- the same order the refresh uses.
"""
import argparse
import csv
import datetime as dt
import glob
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
LEDGER = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')
ACTIVE_MINUTES = 30
MAX_FAILURES = 3
# TWO KINDS OF "NO", AND THEY ARE NOT THE SAME NIGHT.
#
# 18 September 2026: one job failed, the word `overloaded` appeared in its output, and
# the sweep stopped with "the week is spent" -- 17 jobs in, $1.10 spent, two days after
# the reset. The same job succeeded on the next attempt. A 529 from the API is the
# SERVER being busy for a moment; it says nothing whatever about the plan's allowance,
# and neither does a 429 in the rolling five-hour window, which clears by waiting.
#
# HARD is the plan saying the money is gone: nothing but the weekly reset fixes it, so
# stop. TRANSIENT is the service saying not right now: back off and put the job back on
# the queue. Conflating them cost a night of backlog and, worse, printed a confident
# wrong sentence about the allowance -- the failure this project calls quoting a
# rendering rather than the source (rule 13). So the CLI's own words are now printed
# with the stop, rather than our interpretation of them standing alone.
HARD_LIMIT_WORDS = ('usage limit', 'limit reached', 'out of credits', 'quota',
                    'weekly limit', 'insufficient credit')
TRANSIENT_WORDS = ('rate limit', 'too many requests', '429', '529', 'overloaded',
                   'timed out', 'timeout', 'connection', 'econnreset', 'socket hang up',
                   'internal server error', '500', '502', '503')
BACKOFF = (60, 300, 900, 1800)      # what to wait before retrying a transient refusal
MY_SESSION = os.environ.get('CLAUDE_SESSION_FILE', '')


def tj_active():
    cutoff = time.time() - ACTIVE_MINUTES * 60
    for p in glob.glob(os.path.expanduser('~/.claude/projects/*/*.jsonl')):
        if os.path.getmtime(p) > cutoff:
            return True
    return False


def log(row):
    new = not os.path.exists(LEDGER)
    with io.open(LEDGER, 'a', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['at', 'stream', 'board', 'date', 'cost_usd', 'result'], lineterminator='\n')
        if new:
            w.writeheader()
        w.writerow(row)


def jobs():
    """Every job the sweep may run, in order."""
    import refresh
    import extract_official_votes as E
    out = []
    have = {os.path.relpath(p, E.OUT)[:-5] for p in glob.glob(os.path.join(E.OUT, '*', '*.json'))}
    votes = [e for e in E.minutes_files() if '%s/%s-%s' % (e['board_slug'], e['date'], e['docid']) not in have]
    recent = refresh.recent_since()
    for e in votes:                                # already newest first
        out.append(dict(stream='votes', board=e['board_slug'], date=e['date'], recent=e['date'] >= recent,
                        cmd=['python3', 'scripts/extract_official_votes.py', e['board_slug'], e['date']]))
    for t in refresh.minutes_targets(refresh.policy()):
        out.append(dict(stream='minutes', board=t['board_slug'], date=t['meeting_date'], recent=t['meeting_date'] >= recent,
                        cmd=['python3', 'scripts/write_recording_minutes.py', t['board_slug'], t['meeting_date']]))
    # Both streams' recent work before either stream's older work; votes (cheap) before
    # minutes inside each; newest first.
    out.sort(key=lambda j: (0 if j['recent'] else 1, 0 if j['stream'] == 'votes' else 1, -int(j['date'].replace('-', ''))))
    return out


def cost_of(text):
    for line in text.splitlines():
        if '$' in line:
            try:
                return float(line.split('$')[1].split(')')[0].split()[0])
            except (ValueError, IndexError):
                pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--until', required=True, help='local time HH:MM to stop at')
    ap.add_argument('--now', action='store_true', help='run even while a session is active')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--max', type=int, default=10_000)
    ap.add_argument('--parallel', type=int, default=4, help='jobs at once; the first sweep (17 Sep 2026) ran serial and cleared 77 in 65 minutes for 1.4%% of the week -- time, not allowance, was the limit')
    a = ap.parse_args()
    hh, mm = map(int, a.until.split(':'))
    now = dt.datetime.now()
    until = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if until <= now:
        until += dt.timedelta(days=1)
    js = jobs()
    print('%d jobs queued (%d in the last two years); running until %s' % (len(js), sum(1 for j in js if j['recent']), until.strftime('%H:%M')))
    if a.dry_run:
        for j in js[:20]:
            print('  ', j['stream'], j['board'], j['date'], 'recent' if j['recent'] else 'older')
        return
    spent = 0.0
    n = 0
    stop_reason = None
    failures = 0          # non-limit failures; a transient one (a timeout, a hiccup) should not end the night
    transient = 0         # consecutive service refusals (529, 429, a dropped socket)
    requeue = []          # jobs a transient refusal interrupted, to be tried again
    from concurrent.futures import ThreadPoolExecutor, as_completed
    it = iter(js)

    def run(j):
        r = subprocess.run(j['cmd'], capture_output=True, text=True, cwd=ROOT)
        return j, r.returncode == 0, r.stdout + r.stderr

    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        pending = set()
        while stop_reason is None:
            while len(pending) < a.parallel and n + len(pending) < a.max:
                if dt.datetime.now() >= until:
                    stop_reason = 'reached %s' % a.until; break
                if not a.now and tj_active():
                    stop_reason = 'a session is active'; break
                j = requeue.pop(0) if requeue else next(it, None)
                if j is None:
                    stop_reason = 'the queue is empty'; break
                pending.add(pool.submit(run, j))
            if not pending:
                break
            fut = next(as_completed(pending))
            pending.remove(fut)
            j, ok, out = fut.result()
            cost = cost_of(out)
            log(dict(at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), stream=j['stream'], board=j['board'],
                     date=j['date'], cost_usd='%.4f' % cost if cost is not None else '', result='ok' if ok else 'failed'))
            n += 1
            spent += cost or 0
            print('  %s %s %s  %s%s' % (j['stream'], j['board'], j['date'], 'ok' if ok else 'FAILED', (' $%.2f' % cost) if cost else ''), flush=True)
            if not ok:
                low = out.lower()
                said = out.strip()[-300:].replace('\n', ' ')
                if any(w in low for w in HARD_LIMIT_WORDS):
                    stop_reason = ('the plan refused — the allowance is spent. It said: %s'
                                   % said)
                elif any(w in low for w in TRANSIENT_WORDS):
                    # NOT the week. Back off, put the job back, and carry on; only a run
                    # of them is evidence of anything.
                    transient += 1
                    wait = BACKOFF[min(transient, len(BACKOFF)) - 1]
                    print('    transient (%d): waiting %ds and requeueing — %s'
                          % (transient, wait, said), flush=True)
                    requeue.append(j)
                    if transient > len(BACKOFF):
                        stop_reason = ('%d transient refusals in a row — the service is '
                                       'not answering. It said: %s' % (transient, said))
                    else:
                        time.sleep(wait)
                else:
                    failures += 1
                    print('    failed (%d of %d tolerated): %s' % (failures, MAX_FAILURES, said), flush=True)
                    if failures >= MAX_FAILURES:
                        stop_reason = '%d jobs failed for reasons other than a limit — stopping rather than guessing' % failures
            else:
                transient = 0        # a success clears the streak
        # Let what is in flight finish; nothing new is submitted once a reason is set.
        for fut in pending:
            j, ok, out = fut.result()
            cost = cost_of(out)
            log(dict(at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), stream=j['stream'], board=j['board'],
                     date=j['date'], cost_usd='%.4f' % cost if cost is not None else '', result='ok' if ok else 'failed'))
            n += 1
            spent += cost or 0
    print(stop_reason or 'done', flush=True)
    print('%d jobs, $%.2f API-equivalent (~%.1f%% of the week)' % (n, spent, spent / 5))


if __name__ == '__main__':
    main()
