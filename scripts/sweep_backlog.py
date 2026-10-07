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
# THE CALIBRATION, from CLAUDE.md: 1% of the weekly allowance is about $5 of the
# API-equivalent cost the CLI reports, measured twice over 49 overnight runs.
PCT_DOLLARS = 5.0


def week_start():
    """The most recent Thursday 23:00 America/New_York, as a UTC datetime.

    23:00, NOT 11:00. `/usage` read twice on 5 October 2026: *"resets Oct 8 at 10:59pm"*
    and *"Oct 8 at 11pm"*. The 11:00 this used before came from "reset is TOMORROW at 11"
    (23 September), read as morning; the plan's own screen says evening. Counting from
    11:00 started every week twelve hours early, so Thursday afternoon's spend was billed
    to the week that was about to end.

    The plan's weekly allowance resets then. This file's own sibling had it as Wednesday
    22:59 for weeks and handed back half of every sweep window as a result, so the day is
    read from one place and not retyped.
    """
    now = dt.datetime.now().astimezone()
    back = (now.weekday() - 3) % 7          # Thursday is 3
    start = (now - dt.timedelta(days=back)).replace(hour=23, minute=0, second=0,
                                                    microsecond=0)
    if start > now:
        start -= dt.timedelta(days=7)
    return start.astimezone(dt.timezone.utc)


def spend_this_week():
    """What every scripted run has cost since that reset, in API-equivalent dollars."""
    if not os.path.exists(LEDGER):
        return 0.0
    cut = week_start()
    total = 0.0
    with open(LEDGER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if not r.get('cost_usd'):
                continue
            try:
                at = dt.datetime.strptime(r['at'], '%Y-%m-%dT%H:%M:%SZ').replace(
                    tzinfo=dt.timezone.utc)
            except ValueError:
                continue
            if at >= cut:
                total += float(r['cost_usd'])
    return total
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
                    'weekly limit', 'insufficient credit',
                    # the five-hour window. Not the week -- but waiting it out inside a
                    # sweep holds the window shut on TJ's own session, so stop cleanly.
                    'session limit')
TRANSIENT_WORDS = ('rate limit', 'too many requests', '429', '529', 'overloaded',
                   'timed out', 'timeout', 'connection', 'econnreset', 'socket hang up',
                   'internal server error', '500', '502', '503',
                   # The CLI briefly vanishing during its own auto-update: three jobs on
                   # 5 October 2026 failed with FileNotFoundError: 'claude' and ended the
                   # night. The binary returns within minutes; that is a wait, not a defect.
                   "no such file or directory: 'claude'")
BACKOFF = (60, 300, 900, 1800)      # what to wait before retrying a transient refusal
MY_SESSION = os.environ.get('CLAUDE_SESSION_FILE', '')


# THE KILL SWITCH. While this file exists nothing metered starts: not the sweep, not a
# metered step of the refresh. `touch build/STOP-METERED` stops everything at the next job
# boundary, including a loop some session left running unattended; delete it to resume.
# A file rather than a flag because the thing it must stop is a process nobody is
# attached to any more -- on 6 October 2026 that was a relaunch loop reparented to launchd.
KILL_SWITCH = os.path.join(ROOT, 'build', 'STOP-METERED')


def kill_switch():
    """The reason metered work is switched off, or None."""
    if not os.path.exists(KILL_SWITCH):
        return None
    why = open(KILL_SWITCH, encoding='utf-8', errors='replace').read().strip()
    return 'the kill switch is on (%s)%s' % (os.path.relpath(KILL_SWITCH, ROOT),
                                            ': ' + why[:200] if why else '')


# NO PROGRESS IS A STOP. A job that exits 0, costs nothing and writes nothing did no work,
# and the queue it came from will hand it back next time. On 6 October 2026 that was 5,145
# jobs in a row -- the same 169 meetings for three and a half hours, every one a refused
# call the extractor reported as success. Ten in a row ends the run, and says why.
NO_PROGRESS = 10

# THE BACKLOG MUST GO DOWN. Cost and exit codes are what a job SAYS; whether it left the
# queue is what it DID. After every job the backlog is counted again (0.3s) and the job is
# looked for in it. A job still queued after it ran -- refused, written somewhere nothing
# reads, failed quietly, or charged for and dropped -- made no progress whatever it cost or
# returned. Of the last STUCK_WINDOW jobs, if STUCK_MAX are still queued, the run stops.
# TJ, 6 October 2026: *"If the job doesn't produce results (like a decrease in a metric
# from the backlog) then it also means something is spinning."*
STUCK_WINDOW = 10
STUCK_MAX = 5


def key(j):
    return (j['stream'], j['board'], j['date'])


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
    # THE TOWN'S OFFICIAL MINUTES, IN TWO STATES. TJ, 6 October 2026: the target is the
    # STRUCTURED read (schema 2: attendees, votes, decisions, budget items, transfers,
    # public comment, topics), and for a while the archive holds both kinds -- so a set of
    # minutes is one of three things, and two of them are work:
    #
    #   official      never read at all                       -> read, structured
    #   official-v1   read for VOTES ONLY, before schema 2     -> re-read, structured
    #   (done)        structured
    #
    # Two stream keys rather than one so every chart and count can show the split TJ asked
    # for: which meetings have not had their official minutes processed THIS way. Both run
    # the same command. A v1 file stays valid and in use until its meeting is re-read.
    # (The stream was called `votes` until this day, after the extractor; the ledger keeps
    # that name on its older rows.)
    state = {}
    for p in glob.glob(os.path.join(E.OUT, '*', '*.json')):
        k = os.path.relpath(p, E.OUT)[:-5]
        state[k] = 2 if '"schema": 2' in open(p, encoding='utf-8').read() else 1
    todo = []
    for e in E.minutes_files():
        st = state.get('%s/%s-%s' % (e['board_slug'], e['date'], e['docid']))
        if st == 2:
            continue
        todo.append((e, 'official' if st is None else 'official-v1'))
    # A stub the extractor will refuse as `no text` is not work. It exits 0 and writes
    # nothing, so it was logged `ok` at $0 and re-queued by every sweep -- the first seven
    # jobs on 5 October 2026 were these, and looked like a sweep that was not calling the
    # model. Same test the extractor applies, imported rather than restated.
    todo = [(e, s_) for e, s_ in todo
            if len(E.norm(open(e['path'], encoding='utf-8', errors='replace').read())) >= E.MIN_CHARS]
    recent = refresh.recent_since()
    seen = set()
    for e, stream in todo:                         # already newest first
        if (stream, e['board_slug'], e['date']) in seen:
            continue                               # one run reads every set for that board and date
        seen.add((stream, e['board_slug'], e['date']))
        out.append(dict(stream=stream, board=e['board_slug'], date=e['date'], recent=e['date'] >= recent,
                        cmd=['python3', 'scripts/extract_official_votes.py', e['board_slug'], e['date'], '--schema', '2']))
    for t in refresh.minutes_targets(refresh.policy()):
        out.append(dict(stream='minutes', board=t['board_slug'], date=t['meeting_date'], recent=t['meeting_date'] >= recent,
                        cmd=['python3', 'scripts/write_recording_minutes.py', t['board_slug'], t['meeting_date']]))
    # RECONCILE, WHICH HAD NO DRAIN AT ALL UNTIL NOW. Our minutes of a recording against
    # the minutes the town published for the same meeting. It was only ever worked by
    # `refresh.py`, which called it with no cap, so on 28 September 2026 it ran two hours
    # inside the daily refresh and spent $22.73 with 157 pairs still to go. The refresh is
    # now bounded, and a bounded daily step with no second drain is a backlog that never
    # clears -- so it belongs here, where the week's unused allowance pays for it and a
    # person working stops it.
    #
    # A pair is work when we hold BOTH records and have not compared them. That is the
    # same test `reconcile_minutes.py` applies, imported rather than restated so the two
    # cannot disagree about what is outstanding.
    import json
    import reconcile_minutes as RM
    import write_recording_minutes as W
    for f in sorted(glob.glob(os.path.join(W.OUT, '*', '*.json'))):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if d.get('reconciliation') or not RM.official_for(d)[0]:
            continue
        board, date = d.get('board_slug', ''), d.get('meeting_date', '')
        if not board or not date:
            continue
        out.append(dict(stream='reconcile', board=board, date=date, recent=date >= recent,
                        cmd=['python3', 'scripts/reconcile_minutes.py', board, date]))
    # Both streams' recent work before either stream's older work; votes (cheap) before
    # minutes inside each; newest first.
    # Recent work in every stream before any stream's older work; inside a tier, cheapest
    # first -- votes ~$0.15, reconcile ~$0.32, minutes ~$0.45 -- then newest first.
    order = {'official': 0, 'official-v1': 1, 'reconcile': 2, 'minutes': 3}
    out.sort(key=lambda j: (0 if j['recent'] else 1, order.get(j['stream'], 9),
                            -int(j['date'].replace('-', ''))))
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
    # SUPERSEDED BY process_meeting.py (TJ, 6 October 2026: "anytime I ask you to kick that
    # process off ... it has to be super clear"). Two ways to work one backlog is how a
    # request for one stream ended up running three. jobs(), the stops and the ledger stay
    # here because the backlog charts and process_meeting.py read them; running the sweep
    # itself needs --i-know, so nobody reaches for it by accident.
    if '--i-know' not in sys.argv:
        sys.exit('sweep_backlog.py is superseded. Work the backlog newest first with:\n'
                 '  python3 scripts/process_meeting.py --next 10 --dry-run\n'
                 '  python3 scripts/process_meeting.py --next 10')
    sys.argv.remove('--i-know')
    ap = argparse.ArgumentParser()
    ap.add_argument('--until', required=True, help='local time HH:MM to stop at')
    ap.add_argument('--now', action='store_true', help='run even while a session is active')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--budget-pct', type=float, default=None,
                    help='stop once the WEEK\u2019s scripted spend reaches this share of '
                         'the plan\u2019s weekly allowance (1%% ~ $5 API-equivalent). '
                         'Counted across every run since the Thursday 23:00 reset, not '
                         'just this one, so several nights add up to one ceiling.')
    ap.add_argument('--max', type=int, default=10_000)
    ap.add_argument('--streams', default=None,
                    help='comma-separated streams to run (official, official-v1, reconcile, minutes); '
                         'default all. `--streams official` is the town\u2019s minutes never read; '
                         '`official-v1` is those read for votes only, to re-read structured')
    ap.add_argument('--parallel', type=int, default=4, help='jobs at once; the first sweep (17 Sep 2026) ran serial and cleared 77 in 65 minutes for 1.4%% of the week -- time, not allowance, was the limit')
    a = ap.parse_args()
    hh, mm = map(int, a.until.split(':'))
    now = dt.datetime.now()
    until = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if until <= now:
        until += dt.timedelta(days=1)
    if kill_switch():
        sys.exit('sweep: not starting -- %s' % kill_switch())
    js = jobs()
    if a.streams:
        keep = set(a.streams.split(','))
        js = [j for j in js if j['stream'] in keep]
    print('%d jobs queued (%d in the last two years); running until %s' % (len(js), sum(1 for j in js if j['recent']), until.strftime('%H:%M')))
    if a.dry_run:
        for j in js[:20]:
            print('  ', j['stream'], j['board'], j['date'], 'recent' if j['recent'] else 'older')
        return
    spent = 0.0
    n = 0
    stop_reason = None
    # A CEILING THE SWEEP STOPS AT, rather than one the plan enforces by refusing.
    #
    # TJ, 26 September 2026, going away for the week: *"i want to burn a bunch of credits
    # ... leaving around 80% before tues morning"* -- he chose SPENDING about 80%. Until
    # now the only stop was a hard refusal from the CLI, which is 100% by definition and
    # leaves nothing for the interactive work he comes back to.
    #
    # It counts the WHOLE WEEK, not this run, because reaching a total across several
    # nights is the thing being asked for; a per-run cap would be three separate 80%s.
    # The week begins at the Thursday 23:00 reset (America/New_York) -- see
    # weekly_sweep.sh for why that date is written down rather than assumed.
    week_before = spend_this_week()
    budget = (a.budget_pct * PCT_DOLLARS) if a.budget_pct else None
    if budget is not None:
        print('   week so far: $%.2f API-equivalent (~%.1f%%); ceiling $%.2f (~%.0f%%)'
              % (week_before, week_before / PCT_DOLLARS, budget, a.budget_pct))
    from collections import deque
    recent_stuck = deque(maxlen=STUCK_WINDOW)   # True for each recent job still queued after it ran
    keep_streams = set(a.streams.split(',')) if a.streams else None

    def backlog():
        return {key(x) for x in jobs() if keep_streams is None or x['stream'] in keep_streams}
    start_backlog = len(backlog())
    idle = 0              # consecutive jobs that exited 0 and cost nothing -- see NO_PROGRESS
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
                if kill_switch():
                    stop_reason = kill_switch(); break
                if budget is not None and week_before + spent >= budget:
                    stop_reason = ('the %.0f%% ceiling for the week ($%.2f spent)'
                                   % (a.budget_pct, week_before + spent)); break
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
            left = backlog()
            recent_stuck.append(key(j) in left)
            if stop_reason is None and sum(recent_stuck) >= STUCK_MAX:
                stop_reason = ('the backlog is not going down: %d of the last %d jobs are still '
                               'queued after running (backlog %d at the start, %d now). Last: '
                               '%s %s %s -- it said: %s'
                               % (sum(recent_stuck), len(recent_stuck), start_backlog, len(left),
                                  j['stream'], j['board'], j['date'],
                                  out.strip()[-300:].replace('\n', ' ')))
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
                idle = 0 if cost else idle + 1
                if idle >= NO_PROGRESS:
                    stop_reason = ('no progress: %d jobs in a row exited 0 and cost nothing, so '
                                   'nothing was written and they will only be queued again. '
                                   'Last: %s %s %s -- it said: %s'
                                   % (idle, j['stream'], j['board'], j['date'],
                                      out.strip()[-300:].replace('\n', ' ')))
        # Let what is in flight finish; nothing new is submitted once a reason is set.
        for fut in pending:
            j, ok, out = fut.result()
            cost = cost_of(out)
            log(dict(at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), stream=j['stream'], board=j['board'],
                     date=j['date'], cost_usd='%.4f' % cost if cost is not None else '', result='ok' if ok else 'failed'))
            n += 1
            spent += cost or 0
    print(stop_reason or 'done', flush=True)
    print('backlog: %d -> %d' % (start_backlog, len(backlog())), flush=True)
    print('%d jobs, $%.2f API-equivalent (~%.1f%% of the week)' % (n, spent, spent / 5))


if __name__ == '__main__':
    main()
