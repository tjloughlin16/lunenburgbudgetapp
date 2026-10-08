#!/usr/bin/env python3
"""EVERY MEETING'S RECORDS, PROCESSED NEWEST FIRST -- the one command for the backlog.

    python3 scripts/process_meeting.py --next 10 --dry-run   # which 10, which steps, what it should cost
    python3 scripts/process_meeting.py --next 10             # do them
    python3 scripts/process_meeting.py --next 100            # a bigger chunk; same command
    python3 scripts/process_meeting.py select-board 2026-09-15   # one meeting
    python3 scripts/process_meeting.py --status              # how many meetings still need anything

TJ, 6 October 2026: *"start with the newest meetings and work from the transcripts and the
official minutes, process them, reconcile them, and update and work backwards. And I can
say, do a chunk of 10, do a chunk of 100 ... it has to be bulletproof, it has to work, and
it can't be runaway."* That afternoon a wrapper loop around sweep_backlog.py had spun for
three and a half hours on 169 refused calls, and run two streams nobody asked for.

THE UNIT IS A MEETING. For each one, newest meeting date first, only the steps it still
needs, in this order (the order is read_order.py's rule, not this file's):

  1. ours       write OUR minutes from the recording's captions        write_recording_minutes.py
  2. official   read the TOWN's minutes, structured                    extract_official_votes.py --schema 2
  3. reconcile  ours against the town's, wherever both exist and were  reconcile_minutes.py (sonnet)
                never compared -- its own call; folding it into step 2
                on haiku was piloted and lost too much (FOLD_RECONCILE)

Every step saves its own file the moment it succeeds and is skipped once done, so a run
that fails or is stopped loses only the step in progress -- and re-running the same command
picks up exactly there. A step that fails ends THAT MEETING (the later steps depend on it)
and the run moves to the next meeting.

WHY IT CANNOT RUN AWAY. Every one of these stops the whole run, says why, and exits 1:

  * a usage or session limit, in any step's output                (the CLI's own words, printed)
  * the kill switch: build/STOP-METERED exists                    (checked before every step)
  * the dollar ceiling: --max-usd, default twice the estimate     (checked before every meeting)
  * no progress: a meeting whose steps all "succeeded" and that still needs the same steps --
    twice in a row. Judged by RE-READING what is on disk, never by what a step printed.
  * three failed meetings in a row
  * another run already holds the lock                            (one at a time, never two)

And it runs ONE STEP AT A TIME. Parallel runs cost the same dollars and spend them faster,
which is what exhausts the five-hour window and takes TJ's own session down with it.

THE PACE IS THE POINT, AND IT HAS A NUMBER. TJ, 7 October 2026: *"80% in 5 hours is a
perfect pace."* One serial run of this script, measured that day from
`sources/data/agentic-spend.csv`: **~$6 an hour, ~42 meetings an hour, ~$0.14 a meeting.**
Against a five-hour window ESTIMATED at ~$37 (one confounded reading; not yet measured on an
idle account) that is ~16% of the window an hour -- ~80% over five hours, leaving room for
interactive work. Two runs at once would be ~32% an hour and fill a window in about three.
So: ONE run, and the lock above enforces it.

THE ONE EXCEPTION: `--oldest --gap SECONDS`, a SLOW second run from the other end of the
queue, to use what one run leaves of a window (TJ, 7 October 2026: *"15% remaining in the
session is quite a lot"*). It takes its OWN lock, so there is still never more than one run
per end; it works oldest-first, so it cannot reach a meeting the newest-first run is on --
the two ends are thousands of meetings apart; and it sleeps `--gap` seconds between
meetings, so it adds a measured trickle rather than doubling the rate. Give it a `--max-usd`
equal to the headroom in dollars. Quote a batch with `--dry-run` (it prints % of
the week); the window share is hours x 16%. The derivation, and the `/usage` reading that
would confirm the $37, is `notes/findings/METERED-BATCH-COST.md` section 6.
"""
import argparse
import csv
import datetime as dt
import fcntl
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
LOCK = os.path.join(ROOT, 'build', 'process-meeting.lock')
MAX_FAILED_IN_A_ROW = 3
MAX_STUCK_IN_A_ROW = 2


def _official(board, date):
    """The town's minutes for this meeting that still need the structured read."""
    import extract_official_votes as E
    out = []
    for e in E.minutes_files(board):
        if e['date'] != date:
            continue
        if len(E.norm(open(e['path'], encoding='utf-8', errors='replace').read())) < E.MIN_CHARS:
            continue                            # a stub the extractor refuses as `no text`
        p = E.out_path(e)
        if os.path.exists(p):
            d = json.load(open(p, encoding='utf-8'))
            if E.schema_of(d) >= 2 and d.get('source', {}).get('sha256') == E.sha256_of(e['path']):
                continue
        out.append(e)
    return out


def _ours_needed(board, date):
    import refresh
    return any(t['board_slug'] == board and t['meeting_date'] == date
               for t in refresh.minutes_targets(refresh.policy()))


def _reconcile_needed(board, date):
    import reconcile_minutes as R
    import write_recording_minutes as W
    for p in glob.glob(os.path.join(W.OUT, board, date + '-*.json')):
        m = json.load(open(p, encoding='utf-8'))
        off_path, _ = R.official_for(m)
        if not off_path:
            continue
        rc = m.get('reconciliation')
        if not rc or rc.get('official_sha256') != R.sha256_of(off_path):
            return True
    return False


def snapshot():
    """Every index steps() needs, read ONCE. queue() asks about ~6,000 meetings; reading the
    indexes per meeting made a status check take minutes."""
    import extract_official_votes as E
    import refresh
    import reconcile_minutes as R
    import write_recording_minutes as W
    import read_order
    import review_queue as Q
    read_order.reset()
    held = Q.open_keys()
    official, has_official = {}, set()
    for e in E.minutes_files():
        has_official.add((e['board_slug'], e['date']))
        if len(E.norm(open(e['path'], encoding='utf-8', errors='replace').read())) < E.MIN_CHARS:
            continue
        p = E.out_path(e)
        if os.path.exists(p):
            d = json.load(open(p, encoding='utf-8'))
            if E.schema_of(d) >= 2 and d.get('source', {}).get('sha256') == E.sha256_of(e['path']):
                continue
        official.setdefault((e['board_slug'], e['date']), []).append(e)
    ours = {(t['board_slug'], t['meeting_date']) for t in refresh.minutes_targets(refresh.policy())}
    recon = set()
    for p in glob.glob(os.path.join(W.OUT, '*', '*.json')):
        m = json.load(open(p, encoding='utf-8'))
        off_path, _ = R.official_for(m)
        if not off_path:
            continue
        rc = m.get('reconciliation')
        if not rc or rc.get('official_sha256') != R.sha256_of(off_path):
            recon.add((m['board_slug'], m['meeting_date']))
    # A meeting HELD FOR REVIEW is pulled out of every one of these, not merely left out of
    # the final queue: `has_official` feeds the reconcile test in steps() too, and a held
    # meeting must not back that up either.
    official = {k: v for k, v in official.items() if k not in held}
    has_official = {k for k in has_official if k not in held}
    ours = {k for k in ours if k not in held}
    recon = {k for k in recon if k not in held}
    return dict(official=official, ours=ours, reconcile=recon, has_official=has_official, held=held)


STEPS = threading.Lock()


def steps(board, date, snap=None):
    """Thread-safe wrapper: read_order keeps a module-level cache that `reset()` empties, and
    two governed workers calling this at once had one wipe it while the other read it --
    `KeyError: 'ours'`, 2 times in 8 on a threaded test, 7 October 2026. One at a time."""
    with STEPS:
        return _steps(board, date, snap)


def _steps(board, date, snap=None):
    """The steps this meeting still needs, in order. Without `snap`, read fresh from disk --
    which is how the run re-checks a meeting after working it.

    A meeting with an OPEN review-queue row needs NOTHING: `review_queue.held()` is the
    one place that decides this, imported here and by build_backlog_depth.py, so the two
    can never disagree about which meetings are pulled out of the normal flow (TJ, 7
    October 2026: "pulled out of the normal flow of processing so they can't back
    anything up")."""
    import read_order
    import review_queue as Q
    k = (board, date)
    if (k in snap['held']) if snap else Q.held(board, date):
        return []
    if snap is None:
        read_order.reset()
    need = []
    if (k in snap['ours']) if snap else _ours_needed(board, date):
        need.append('ours')
    if (k in snap['official']) if snap else _official(board, date):
        st, _ = read_order.state(board, date)
        # `transcript` means ours come first: allowed only if step 1 is in this same plan.
        if st != 'awaiting' and (st != 'transcript' or 'ours' in need):
            need.append('official')
    # RECONCILE, its own sonnet call, wherever both records exist and were never compared:
    # ours written in this plan with the town's minutes on disk, or a pair already waiting.
    # A pair compared against the current text stays as it is.
    import extract_official_votes as E
    has_official = ('ours' in need and ((k in snap['has_official']) if snap
                                        else any(e['date'] == date for e in E.minutes_files(board))))
    if E.FOLD_RECONCILE and 'official' in need:
        pass                                    # the official read reconciles in the same call
    elif ('ours' in need and has_official) or ((k in snap['reconcile']) if snap else _reconcile_needed(board, date)):
        need.append('reconcile')
    return need


def queue():
    """Every meeting that needs anything, newest meeting date first."""
    snap = snapshot()
    cand = set(snap['official']) | snap['ours'] | snap['reconcile']
    out = []
    for board, date in sorted(cand, key=lambda k: (k[1], k[0]), reverse=True):
        s = steps(board, date, snap)
        if s:
            out.append((board, date, s))
    return out


COMMAND = {
    'ours': lambda b, d: ['python3', 'scripts/write_recording_minutes.py', b, d],
    'official': lambda b, d: ['python3', 'scripts/extract_official_votes.py', b, d, '--schema', '2'],
    'reconcile': lambda b, d: ['python3', 'scripts/reconcile_minutes.py', b, d],
}


def cost_in(text):
    """Every `cost $x` a step printed, summed: one step can make several model calls."""
    found = [float(x) for x in re.findall(r'^cost \$([0-9.]+)', text, flags=re.M)]
    if found:
        return sum(found)
    m = re.search(r'\(\$([0-9.]+)\)', text)
    return float(m.group(1)) if m else 0.0


PRINT = threading.Lock()     # several workers share one log; a line is never torn
LEDGER = threading.Lock()    # ...and one spend ledger


def say(msg):
    with PRINT:
        print(msg, flush=True)


def run_step(step, board, date, quiet=False):
    """(ok, cost, output). Serial: the step's output streamed as it arrives. Parallel
    (`quiet`): only its `wrote` / failure lines, each tagged with the meeting, so several
    workers' output stays readable in one log."""
    cmd = COMMAND[step](board, date)
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    seen = []
    for line in p.stdout:
        if not quiet:
            say('      ' + line.rstrip('\n'))
        elif re.search(r'wrote|FAIL|Error|limit', line, flags=re.I):
            say('      [%s %s] %s' % (date, board, line.strip()))
        seen.append(line)
    out = ''.join(seen)
    return p.wait() == 0, cost_in(out), out


def stream_for(step, board, date):
    """The ledger's name for a step -- the same keys the backlog charts use."""
    if step != 'official':
        return 'minutes' if step == 'ours' else 'reconcile'
    import extract_official_votes as E
    held = [E.out_path(e) for e in E.minutes_files(board) if e['date'] == date]
    return 'official-v1' if any(os.path.exists(p) for p in held) else 'official'


def estimate(plan):
    import build_backlog_depth as B
    c = B.unit_costs()
    price = {'ours': c.get('minutes') or 0.39, 'official': c.get('official') or 0.16,
             'reconcile': c.get('reconcile') or 0.27}
    return sum(price[s] for _, _, st in plan for s in st)


def main():
    import sweep_backlog as S
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('board', nargs='?')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--next', type=int, help='process the N newest meetings that need anything')
    ap.add_argument('--max-usd', type=float, help='stop once this much is spent (default: twice the estimate, at least $1)')
    ap.add_argument('--dry-run', action='store_true', help='show the plan and its estimate; call nothing')
    ap.add_argument('--oldest', action='store_true', help='work from the OLDEST end, under its own lock (see the docstring)')
    ap.add_argument('--gap', type=float, default=0, help='seconds to wait between meetings: a slow second run')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--until-usage', action='store_true', help='run the backlog until a usage cap, paced by the live bars (the governor)')
    ap.add_argument('--session-cap', type=float, default=95.0, help='governor: stop starting meetings at this %% of the 5-hour window')
    ap.add_argument('--week-cap', type=float, default=90.0, help='governor: stop at this %% of the week')
    ap.add_argument('--by', help='governor: reach the session cap by +1h, +30m, 16:30 or "thu 23:00" (default: the reset)')
    ap.add_argument('--ramp', type=float, default=300, help='governor: seconds between adding workers (the brake on a fast fill)')
    ap.add_argument('--max-jobs', type=int, default=3, help='governor: most workers at once (one is ~16%%/h of a window)')
    a = ap.parse_args()

    if a.status:
        import review_queue as Q
        q = queue()
        by = {}
        for _, _, st in q:
            for s in st:
                by[s] = by.get(s, 0) + 1
        print('%d meetings need something: %s' % (len(q), ', '.join('%s %d' % kv for kv in sorted(by.items()))))
        if q:
            print('newest: %s %s   oldest: %s %s' % (q[0][0], q[0][1], q[-1][0], q[-1][1]))
        held_n = len(Q.open_keys())
        if held_n:
            print('%d meeting(s) held for review (scripts/review_queue.py --list)' % held_n)
        return 0

    if a.board and a.date:
        import review_queue as Q
        if Q.held(a.board, a.date):
            print('%s %s: held for review -- scripts/review_queue.py --list' % (a.board, a.date))
            return 0
        plan = [(a.board, a.date, steps(a.board, a.date))]
        if not plan[0][2]:
            print('%s %s: nothing to do' % (a.board, a.date))
            return 0
    elif a.next or a.until_usage:
        q = queue()[::-1] if a.oldest else queue()
        plan = q[:a.next] if a.next else q
    else:
        ap.error('name a board and date, or --next N')

    est = estimate(plan)
    # TWICE THE ESTIMATE, never less than a dollar: room for a long meeting, not for a spin.
    ceiling = a.max_usd if a.max_usd is not None else max(1.0, round(2 * est, 2))
    if a.until_usage and a.max_usd is None:
        # THE GOVERNOR'S BACKSTOP: the dollars the weekly headroom is worth, plus a fifth. The
        # caps stop it first; this is what stops it if the bars are wrong.
        import usage_governor as G
        h = G.readings()
        week_left = max(0.0, a.week_cap - (h[-1]['u7'] if h else 0.0))
        ceiling = min(ceiling, max(1.0, round(week_left * S.PCT_DOLLARS * 1.2, 2)))
    print('%d meeting(s), %s first; estimated $%.2f (~%.1f%% of the week); ceiling $%.2f'
          % (len(plan), 'OLDEST' if a.oldest else 'newest', est, est / S.PCT_DOLLARS, ceiling), flush=True)
    for board, date, st in (plan[:15] if a.until_usage else plan):
        print('  %s %-40s %s' % (date, board, ' -> '.join(st)), flush=True)
    if a.until_usage:
        import usage_governor as G
        G.fetch(force=True)
        print('  ... (%d in all)\n[gov] %s' % (len(plan), G.describe(
            G.Plan(a.session_cap, a.week_cap, parse_by(a.by), a.max_jobs), G.readings(), time.time())), flush=True)
    if a.dry_run:
        return 0

    if S.kill_switch():
        sys.exit('not starting -- %s' % S.kill_switch())
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    lock_path = LOCK.replace('.lock', '-oldest.lock') if a.oldest else LOCK
    lock = open(lock_path, 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('not starting -- another process_meeting.py run holds %s' % os.path.relpath(lock_path, ROOT))
    lock.write(str(os.getpid()))
    lock.flush()

    if a.until_usage:
        return run_governed(plan, a, S, ceiling)
    return run_serial(plan, a, S, ceiling)


def work_meeting(board, date, S, label, quiet=False):
    """ONE MEETING, every step it still needs, with every per-step guard. Shared by the
    serial run and the governed one, so the two cannot drift apart.
    -> (outcome, cost, stop): outcome is 'done' | 'failed' | 'stuck' | 'stopped'."""
    todo = steps(board, date)              # fresh: an earlier meeting's step may have done this one's
    say('\n[%s] %s %s: %s' % (label, date, board, ' -> '.join(todo) or 'nothing left'))
    cost_total = 0.0
    for step in todo:
        if S.kill_switch():
            return 'stopped', cost_total, S.kill_switch()
        if step != 'ours' and step not in steps(board, date):
            continue                        # already done -- by an earlier step or meeting
        ok, cost, out = run_step(step, board, date, quiet)
        cost_total += cost
        with LEDGER:
            S.log(dict(at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       stream=stream_for(step, board, date) if ok else step, board=board, date=date,
                       cost_usd='%.4f' % cost if cost else '', result='ok' if ok else 'failed'))
        low = out.lower()
        hit = next((w for w in S.HARD_LIMIT_WORDS if w in low), None)
        if hit:
            return 'stopped', cost_total, 'a limit (%r) in %s. It said: %s' % (
                hit, step, out.strip()[-300:].replace('\n', ' '))
        if not ok:
            say('    [%s %s] %s FAILED; the rest of this meeting waits for the next run' % (date, board, step))
            return 'failed', cost_total, None
    left = steps(board, date)
    if left and left == todo:
        say('    [%s %s] NO PROGRESS: every step reported success and the meeting still needs %s'
            % (date, board, ' -> '.join(left)))
        return 'stuck', cost_total, None
    return 'done', cost_total, None


class Tally:
    """Spend and the in-a-row counters, shared by however many workers there are."""

    def __init__(self):
        self.lock = threading.Lock()
        self.spent, self.done, self.failed_row, self.stuck_row = 0.0, 0, 0, 0

    def add(self, outcome, cost):
        """-> a stop reason, or None."""
        with self.lock:
            self.spent += cost
            if outcome == 'failed':
                self.failed_row += 1
                if self.failed_row >= MAX_FAILED_IN_A_ROW:
                    return '%d meetings in a row failed' % self.failed_row
                return None
            self.failed_row = 0
            if outcome == 'stuck':
                self.stuck_row += 1
                if self.stuck_row >= MAX_STUCK_IN_A_ROW:
                    return 'no progress on %d meetings in a row -- steps say ok, the files say otherwise' % self.stuck_row
                return None
            if outcome == 'done':
                self.stuck_row = 0
                self.done += 1
            return None


def finish(T, plan_n, stop, S):
    say('\n%s' % ('STOPPED: ' + stop if stop else 'done'))
    say('%d of %d meeting(s) completed; $%.2f (~%.2f%% of the week)'
        % (T.done, plan_n, T.spent, T.spent / S.PCT_DOLLARS))
    return 1 if stop else 0


def run_serial(plan, a, S, ceiling):
    T, stop = Tally(), None
    for i, (board, date, _) in enumerate(plan, 1):
        if T.spent >= ceiling:
            stop = 'the ceiling: $%.2f spent of $%.2f' % (T.spent, ceiling)
            break
        if a.gap and i > 1:
            time.sleep(a.gap)
            if S.kill_switch():
                stop = S.kill_switch()
                break
        outcome, cost, why = work_meeting(board, date, S, '%d/%d' % (i, len(plan)))
        stop = why or T.add(outcome, cost)
        if stop:
            break
    return finish(T, len(plan), stop, S)


def run_governed(plan, a, S, ceiling):
    """THE GOVERNOR (notes/HANDOFF-USAGE-GOVERNOR.md): 1 to --max-jobs workers on ONE queue,
    how many decided every TICK seconds by usage_governor.decide() from the live usage bars,
    and the output guard (backlog_pace.guard) checked before every new meeting. A meeting is
    handed out once, by this loop alone, so no two workers can ever pay for the same one.
    On any stop, nothing new starts and the meetings in flight finish -- a step killed half
    way is paid for and produces nothing."""
    import concurrent.futures as cf
    import backlog_pace as BP
    import usage_governor as G
    by = parse_by(a.by)
    gp = G.Plan(session_cap=a.session_cap, week_cap=a.week_cap, by=by, max_jobs=a.max_jobs, ramp=a.ramp)
    G.fetch(force=True)
    say('[gov %s] %s' % (dt.datetime.now().strftime('%H:%M'), G.describe(gp, G.readings(), time.time())))
    T, stop = Tally(), None
    pool = cf.ThreadPoolExecutor(max_workers=a.max_jobs)
    active = {}
    nxt, n = 0, len(plan)
    d, last_tick, last_line, last_guard = None, 0.0, None, 0.0
    try:
        while True:
            for f in [f for f in active if f.done()]:
                board, date = active.pop(f)
                try:
                    outcome, cost, why = f.result()
                except Exception as e:                       # noqa: BLE001 -- a worker crash is a stop
                    import traceback
                    say(traceback.format_exc())
                    outcome, cost, why = 'stopped', 0.0, 'worker crashed on %s %s: %r' % (date, board, e)
                stop = stop or why or T.add(outcome, cost)
            if stop:
                break
            if S.kill_switch():
                stop = S.kill_switch()
                break
            if T.spent >= ceiling:
                stop = 'the ceiling: $%.2f spent of $%.2f' % (T.spent, ceiling)
                break
            now = time.time()
            if now - last_tick >= TICK:
                last_tick = now
                G.fetch()                                  # the server's figure, at most once a minute
                h = G.readings()
                if h and now - h[-1]['t'] < G.STALE_S:
                    gp.measured(T.done, h[-1]['u5'])
                d = G.decide(gp, h, now, in_flight=len(active))
                line = '5h %s (target %s) workers %d/%d  %s  [%.2f pt/meeting]' % (
                    ('%g%%' % h[-1]['u5']) if h else '?',
                    ('%.0f%%' % d['target']) if d['target'] is not None else '-',
                    len(active), d['jobs'], d['note'], gp.per_meeting)
                if d['note'] != (last_line or ('', ''))[1] or d['jobs'] != (last_line or (0,))[0]:
                    say('[gov %s] %s' % (dt.datetime.now().strftime('%H:%M'), line))
                    last_line = (d['jobs'], d['note'])
                if d['stop']:
                    stop = d['stop']
                    break
            if now - last_guard >= GUARD_EVERY:
                last_guard = now
                problems = BP.guard()[0]
                if problems:
                    stop = 'the output guard: ' + '; '.join(problems)
                    break
            if d and d['wait_reset'] and not active:
                say('[gov %s] session cap reached -- waiting for the window to reset' % dt.datetime.now().strftime('%H:%M'))
                while not S.kill_switch():
                    time.sleep(30)
                    h = G.readings()
                    if h and h[-1]['reset'] != gp.window and time.time() - h[-1]['t'] < G.STALE_S:
                        break
                last_tick = 0
                continue
            if nxt >= n and not active:
                break
            if d and d['start'] and nxt < n and len(active) < d['jobs']:
                board, date, _ = plan[nxt]
                nxt += 1
                fut = pool.submit(work_meeting, board, date, S, '%d/%d' % (nxt, n), a.max_jobs > 1)
                active[fut] = (board, date)
                last_tick = 0 if len(active) < d['jobs'] else last_tick   # fill up promptly
                continue
            time.sleep(2)
    finally:
        if active:
            say('[gov %s] %d meeting(s) in flight -- letting them finish' % (dt.datetime.now().strftime('%H:%M'), len(active)))
        for f in list(active):
            try:
                outcome, cost, why = f.result()
            except Exception:                                  # noqa: BLE001
                outcome, cost, why = 'stopped', 0.0, None
            T.add(outcome, cost)
        pool.shutdown(wait=True)
    return finish(T, n, stop, S)


TICK = 30            # seconds between governor decisions (the bars refresh every 60)
GUARD_EVERY = 60     # seconds between output-guard audits


def parse_by(v):
    """'+1h' / '+30m' / '16:30' / 'thu 23:00' -> epoch, or None."""
    if not v:
        return None
    v = v.strip().lower()
    now = dt.datetime.now()
    m = re.fullmatch(r'\+(\d+(?:\.\d+)?)\s*([hm])', v)
    if m:
        n = float(m.group(1))
        return (now + dt.timedelta(hours=n) if m.group(2) == 'h' else now + dt.timedelta(minutes=n)).timestamp()
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    m = re.fullmatch(r'(?:(mon|tue|wed|thu|fri|sat|sun)\s+)?(\d{1,2}):(\d{2})', v)
    if not m:
        raise SystemExit('--by: give +1h, +30m, 16:30 or "thu 23:00"; got %r' % v)
    t = now.replace(hour=int(m.group(2)), minute=int(m.group(3)), second=0, microsecond=0)
    if m.group(1):
        t += dt.timedelta(days=(days.index(m.group(1)) - now.weekday()) % 7)
    if t <= now:
        t += dt.timedelta(days=7 if m.group(1) else 1)
    return t.timestamp()


if __name__ == '__main__':
    raise SystemExit(main())
