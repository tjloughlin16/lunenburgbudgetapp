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
    read_order.reset()
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
    return dict(official=official, ours=ours, reconcile=recon, has_official=has_official)


def steps(board, date, snap=None):
    """The steps this meeting still needs, in order. Without `snap`, read fresh from disk --
    which is how the run re-checks a meeting after working it."""
    import read_order
    if snap is None:
        read_order.reset()
    k = (board, date)
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


def run_step(step, board, date):
    """(ok, cost, output) -- the step's output streamed to the terminal as it arrives."""
    cmd = COMMAND[step](board, date)
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    seen = []
    for line in p.stdout:
        print('      ' + line, end='', flush=True)
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
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()

    if a.status:
        q = queue()
        by = {}
        for _, _, st in q:
            for s in st:
                by[s] = by.get(s, 0) + 1
        print('%d meetings need something: %s' % (len(q), ', '.join('%s %d' % kv for kv in sorted(by.items()))))
        if q:
            print('newest: %s %s   oldest: %s %s' % (q[0][0], q[0][1], q[-1][0], q[-1][1]))
        return 0

    if a.board and a.date:
        plan = [(a.board, a.date, steps(a.board, a.date))]
        if not plan[0][2]:
            print('%s %s: nothing to do' % (a.board, a.date))
            return 0
    elif a.next:
        plan = queue()[:a.next]
    else:
        ap.error('name a board and date, or --next N')

    est = estimate(plan)
    # TWICE THE ESTIMATE, never less than a dollar: room for a long meeting, not for a spin.
    ceiling = a.max_usd if a.max_usd is not None else max(1.0, round(2 * est, 2))
    print('%d meeting(s), newest first; estimated $%.2f (~%.1f%% of the week); ceiling $%.2f'
          % (len(plan), est, est / S.PCT_DOLLARS, ceiling), flush=True)
    for board, date, st in plan:
        print('  %s %-40s %s' % (date, board, ' -> '.join(st)), flush=True)
    if a.dry_run:
        return 0

    if S.kill_switch():
        sys.exit('not starting -- %s' % S.kill_switch())
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    lock = open(LOCK, 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('not starting -- another process_meeting.py run holds %s' % os.path.relpath(LOCK, ROOT))
    lock.write(str(os.getpid()))
    lock.flush()

    spent, done, failed_row, stuck_row, stop = 0.0, 0, 0, 0, None
    for i, (board, date, _) in enumerate(plan, 1):
        if spent >= ceiling:
            stop = 'the ceiling: $%.2f spent of $%.2f' % (spent, ceiling)
            break
        todo = steps(board, date)              # fresh: an earlier meeting's step may have done this one's
        print('\n[%d/%d] %s %s: %s' % (i, len(plan), date, board, ' -> '.join(todo) or 'nothing left'), flush=True)
        failed = False
        for step in todo:
            if S.kill_switch():
                stop = S.kill_switch()
                break
            if step != 'ours' and step not in steps(board, date):
                continue                        # already done -- by an earlier step or meeting
            ok, cost, out = run_step(step, board, date)
            spent += cost
            S.log(dict(at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       stream=stream_for(step, board, date) if ok else step, board=board, date=date,
                       cost_usd='%.4f' % cost if cost else '', result='ok' if ok else 'failed'))
            low = out.lower()
            hit = next((w for w in S.HARD_LIMIT_WORDS if w in low), None)
            if hit:
                stop = 'a limit (%r) in %s. It said: %s' % (hit, step, out.strip()[-300:].replace('\n', ' '))
                break
            if not ok:
                failed = True
                print('    %s FAILED; the rest of this meeting waits for the next run' % step, flush=True)
                break
        if stop:
            break
        left = steps(board, date)
        if failed:
            failed_row += 1
            if failed_row >= MAX_FAILED_IN_A_ROW:
                stop = '%d meetings in a row failed' % failed_row
                break
            continue
        failed_row = 0
        if left and left == todo:
            stuck_row += 1
            print('    NO PROGRESS: every step reported success and the meeting still needs %s'
                  % ' -> '.join(left), flush=True)
            if stuck_row >= MAX_STUCK_IN_A_ROW:
                stop = 'no progress on %d meetings in a row -- steps say ok, the files say otherwise' % stuck_row
                break
            continue
        stuck_row = 0
        done += 1
    print('\n%s' % ('STOPPED: ' + stop if stop else 'done'), flush=True)
    print('%d of %d meeting(s) completed; $%.2f (~%.2f%% of the week)'
          % (done, len(plan), spent, spent / S.PCT_DOLLARS), flush=True)
    return 1 if stop else 0


if __name__ == '__main__':
    raise SystemExit(main())
