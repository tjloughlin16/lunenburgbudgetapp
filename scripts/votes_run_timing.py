#!/usr/bin/env python3
"""Per-chunk and total timing for an unattended extract_official_votes batch.

    python3 scripts/votes_run_timing.py [progress.log] [run.log]

WHY IT IS DERIVED AND NOT RECORDED. TJ: *"Make sure to time it for each batch and
total"* -- asked while the batch was already running, so the loop could not be changed
to print durations. It does print a wall-clock stamp at each chunk's start and end, and
the run log prints one line per meeting with its cost, so both are RECOVERABLE. This
reads them rather than estimating from a rate, which is the difference between a
measurement and a guess (rule 13).

A CHUNK'S COST IS BUCKETED BY WRITE ORDER, not by timestamp: the run log carries no
chunk markers, but the writes are sequential and each chunk is capped at 100, so the
first 100 priced writes are chunk 1. If a chunk ends short -- the queue ran out, or the
loop was stopped -- the boundary moves and is read off the progress log's own cumulative
count rather than assumed.
"""
import datetime as dt
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRESS = sys.argv[1] if len(sys.argv) > 1 else '/tmp/votes1000-progress.log'
RUN = sys.argv[2] if len(sys.argv) > 2 else '/tmp/votes1000.log'


def hhmmss(s):
    h, m, x = (int(v) for v in s.split(':'))
    return h * 3600 + m * 60 + x


def fmt(sec):
    if sec is None:
        return '--'
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return ('%dh%02dm' % (h, m)) if h else ('%dm%02ds' % (m, s))


def main():
    if not os.path.exists(PROGRESS):
        sys.exit('no progress log at %s' % PROGRESS)
    prog = open(PROGRESS, encoding='utf-8', errors='replace').read()
    starts = dict((int(n), hhmmss(t)) for n, t in
                  re.findall(r'=== chunk (\d+) of \d+\s+(\d\d:\d\d:\d\d)', prog))
    ends = {}
    for n, rc, cum, t in re.findall(
            r'=== chunk (\d+) done rc=(\d+)\s+cumulative writes=(\d+)\s+(\d\d:\d\d:\d\d)', prog):
        ends[int(n)] = (int(rc), int(cum), hhmmss(t))

    # COUNT THE FILES, NOT THE LOG LINES. The run log is Python's stdout redirected to a
    # file, so it is BLOCK-BUFFERED: at 13:12 it held 1,690 lines, every one a skip, and
    # said `wrote: 0` while 23 vote files were already on disk. Twenty minutes of real
    # progress invisible because ~8KB had not been flushed. A log is not a progress meter,
    # and reading one as though it were is the same mistake as every other instrument
    # failure in this repo: the tool was silent and the silence got reported as the fact.
    #
    # So the AUTHORITY for how many and how fast is the files' own mtimes. The log is used
    # for COST only, which is all it uniquely carries, and the cost therefore LAGS the
    # count -- said out loud below rather than quietly averaged away.
    written = sorted(os.path.getmtime(f) for f in
                     glob.glob(os.path.join(ROOT, 'sources', 'data', 'official-votes', '*', '*.json')))
    costs = [float(x) for x in re.findall(r'\(\$([0-9.]+)\)',
             open(RUN, encoding='utf-8', errors='replace').read())] if os.path.exists(RUN) else []

    print('chunk   start      end     elapsed   wrote   mean/mtg    cost   rc')
    prev_cum, t0, last_t = 0, None, None
    rows = []
    for n in sorted(starts):
        st = starts[n]
        if t0 is None:
            t0 = st
        rc, cum, en = ends.get(n, (None, None, None))
        wrote = (cum - prev_cum) if cum is not None else None
        el = (en - st) % 86400 if en is not None else None
        chunk_cost = sum(costs[prev_cum:cum]) if cum is not None else None
        rows.append((n, wrote, el, chunk_cost))
        if en is None:
            continue   # the open chunk is printed once, below, as RUNNING
        print('%5d  %s   %s  %8s  %6s  %9s  %6s  %s' % (
            n, dt.timedelta(seconds=st), dt.timedelta(seconds=en),
            fmt(el), '--' if wrote is None else wrote,
            fmt(el / wrote) if el and wrote else '--',
            '--' if chunk_cost is None else '$%.2f' % chunk_cost,
            '--' if rc is None else rc))
        prev_cum, last_t = cum, en
    # THE CHUNK IN FLIGHT COUNTS TOO. A reporter that says nothing until a chunk closes
    # is useless for the first hundred minutes of a ten-chunk run, which is exactly when
    # somebody asks how it is going. `wrote` lines in the run log are the live count, and
    # the open chunk's elapsed time runs from its own start stamp to now.
    today = dt.date.today()
    t0_abs = dt.datetime.combine(today, dt.time()) + dt.timedelta(seconds=min(starts.values()))
    mine = [t for t in written if t >= t0_abs.timestamp()]
    live = len(mine)
    if rows and rows[-1][2] is None and live > prev_cum:
        st = starts[rows[-1][0]]
        now = dt.datetime.now()
        el = (now.hour * 3600 + now.minute * 60 + now.second - st) % 86400
        n_in = live - prev_cum
        print('%5d  %s   RUNNING  %8s  %6d  %9s  %6s  --' % (
            rows[-1][0], dt.timedelta(seconds=st), fmt(el), n_in,
            fmt(el / n_in) if n_in else '--',
            '$%.2f' % sum(costs[prev_cum:]) if len(costs) > prev_cum else 'lagging'))

    done = [r for r in rows if r[2] is not None]
    total_w = live or sum(r[1] for r in done if r[1])
    now = dt.datetime.now()
    now_s = now.hour * 3600 + now.minute * 60 + now.second
    total_el = ((last_t if (last_t is not None and live <= prev_cum) else now_s) - t0) % 86400 \
        if t0 is not None else None
    print()
    priced = sum(costs)
    print('COMPLETE CHUNKS: %d  |  WRITTEN: %d (files on disk)  |  wall clock: %s'
          % (len(done), total_w, fmt(total_el)))
    print('COST so far: $%.2f (%.1f%% of a week) across the %d priced in the log%s'
          % (priced, priced / 5, len(costs),
             '  -- the log is block-buffered and lags the file count by %d' % (live - len(costs))
             if live > len(costs) else ''))
    if total_el and total_w:
        per = total_el / total_w
        print('mean per meeting: %s' % fmt(per))
        left = 1000 - live
        if left > 0:
            eta = dt.datetime.now() + dt.timedelta(seconds=per * left)
            print('IN FLIGHT: %d of 1000 done, %d left -> ~%s at this rate, finishing ~%s'
                  % (live, left, fmt(per * left), eta.strftime('%H:%M on %d %b')))
            rate = (priced / len(costs)) if costs else 0.113
            print('           projected total cost $%.0f (%.0f%% of a week) at $%.3f a meeting'
                  % (rate * 1000, rate * 1000 / 5, rate))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
