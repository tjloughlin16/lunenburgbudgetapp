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
hour, once $1 has been spent, over $1.00 a matched paid call trips -- $100 for one meeting cannot pass. A stall is no costed row for 15 minutes, unless the chain
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
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEND = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')
ALERT = os.path.join(ROOT, 'build', 'backlog-pace.ALERT')
OUT = os.path.join(ROOT, 'build', 'backlog-pace.log')
LO, HI, STALE_MIN = 2.0, 10.0, 15


OUT_DIRS = ('official-votes', 'recording-minutes', 'oml-reviews')   # oml-reviews: 8 Oct 2026, an OML review's paid call looked unpaid and stopped the evening run
# A FILE IS NOT JUDGED UNPAID UNTIL ITS STEP HAS CERTAINLY LOGGED. A step that reads two
# sets of minutes writes the first file, then the second, then ONE ledger row -- school-
# committee 2025-08-06 wrote at 15:48:43 and logged at 15:49:06, and a governed run's audit
# at 15:50 found the file with its row still inside the 2-minute grace: a false stop. No
# single step runs 15 minutes; a file that old with no row really has none.
FILE_SETTLE_S = 900


def audit(since_utc, now=None):
    """(matched, [unmatched rows], [unpaid files]) for every costed row at or after
    `since_utc` ('YYYY-MM-DDTHH:MM', UTC). See the docstring for what a match is."""
    now = now or dt.datetime.now(dt.timezone.utc)
    t = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    rows = [r for r in csv.DictReader(open(SPEND, encoding='utf-8'))
            if r.get('at', '') >= since_utc and (now - t(r['at'])).total_seconds() > 120
            # A FAILED STEP is not a paid call that produced nothing: it is a failure, logged
            # with no cost, and process_meeting stops on three in a row. Counted in guard(),
            # never matched here -- on 7 October one failed read from the run before stopped
            # the next run in its first minute.
            and r.get('result', 'ok') == 'ok']
    # ONE FILE CAN SERVE SEVERAL STEPS. Our minutes are written, then reconciled, in the SAME
    # file (parks-commission 2024-12-18, 7 October: `minutes` then `reconcile`), so a file is
    # spent once PER STREAM, and a recording-minutes file rewritten by a later step still
    # matches the earlier step's row.
    used, files_used, matched, bad = set(), set(), 0, []
    for r in rows:
        hit = None
        for d in OUT_DIRS:
            for f in glob.glob(os.path.join(ROOT, 'sources', 'data', d, r['board'], r['date'] + '*.json')):
                if (f, r['stream']) in used:
                    continue
                m = dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc)
                lag = (m - t(r['at'])).total_seconds()
                try:
                    j = json.load(open(f, encoding='utf-8'))
                except ValueError:
                    continue
                # BY CONTENT, WHEN THE CLOCK CANNOT SAY. A file that arrived by `git merge` or
                # `pull` carries the merge's mtime, not the time it was written (8 October: 14 of
                # the morning refresh's reads looked unpaid, and stopped the run). So a file also
                # matches when its own record says so: the exact cost a structured read stores,
                # or the `written.at` our minutes store.
                wrote = ((j.get('written') or {}).get('at') or '')
                by_content = (j.get('cost_usd') is not None and float(r['cost_usd'] or 0) > 0
                              and abs(float(j['cost_usd']) - float(r['cost_usd'])) <= 0.0001) or \
                             (wrote and abs((t(wrote) - t(r['at'])).total_seconds()) <= 600)
                if not (by_content or -120 <= lag <= 120 or (d == 'recording-minutes' and lag > 0)):
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
                    if (f, r['stream']) in used or not (-900 <= (m - t(r['at'])).total_seconds() <= 120):
                        continue
                    try:
                        c = json.load(open(f, encoding='utf-8')).get('cost_usd')
                    except ValueError:
                        continue
                    if c is not None:
                        group.append(f)
                        total += float(c)
            if len(group) > 1 and abs(total - float(r['cost_usd'] or 0)) <= 0.001:
                used.update((g, r['stream']) for g in group)
                files_used.update(group)
                matched += 1
                continue
        if hit:
            used.add((hit, r['stream']))
            files_used.add(hit)
            matched += 1
            # ONE STEP, SEVERAL FILES OF ITS OWN: a meeting with two recordings (lunenburg-water-
            # district 2024-08-28, 7 October) gets two minutes files from one paid step. Every
            # other file for this board and date written during the step is that step's too.
            for d in OUT_DIRS:
                for f in glob.glob(os.path.join(ROOT, 'sources', 'data', d, r['board'], r['date'] + '*.json')):
                    lag = (dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc) - t(r['at'])).total_seconds()
                    if f not in files_used and -900 <= lag <= 120:
                        files_used.add(f)
        else:
            bad.append('%s %s %s %s $%s' % (r['at'], r['stream'], r['board'], r['date'], r['cost_usd']))
    lo = t(since_utc + ':00Z' if len(since_utc) == 16 else since_utc)
    unpaid = [os.path.relpath(f, ROOT) for d in OUT_DIRS
              for f in glob.glob(os.path.join(ROOT, 'sources', 'data', d, '*', '*.json'))
              if f not in files_used and lo.timestamp() <= os.path.getmtime(f) <= now.timestamp() - FILE_SETTLE_S]
    # A FILE THAT ARRIVED BY MERGE has a fresh mtime and a payment from hours ago. Before
    # calling it unpaid, look for that payment by CONTENT anywhere in the ledger.
    if unpaid:
        ledger = {}
        for r in csv.DictReader(open(SPEND, encoding='utf-8')):
            if r.get('result', 'ok') == 'ok':
                ledger.setdefault((r['board'], r['date']), []).append(r)
        still = []
        for rel in unpaid:
            f = os.path.join(ROOT, rel)
            parts = rel.split('/')
            board, date = parts[-2], parts[-1][:10]
            try:
                j = json.load(open(f, encoding='utf-8'))
            except ValueError:
                still.append(rel)
                continue
            wrote = ((j.get('written') or {}).get('at') or '')
            paid = any((j.get('cost_usd') is not None and float(r['cost_usd'] or 0) > 0
                        and abs(float(j['cost_usd']) - float(r['cost_usd'])) <= 0.0001)
                       or (wrote and abs((t(wrote) - t(r['at'])).total_seconds()) <= 600)
                       for r in ledger.get((board, date), []))
            if not paid:
                still.append(rel)
        unpaid = still
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
    # OUTPUT WITH NO PAYMENT IS REPORTED, NOT A STOP. It is not money spent for nothing --
    # it is a file changed without a ledger row: a free --relink, a regenerated file, or a
    # writer that does not log (the refresh's own write_recording_minutes, found 8 October).
    # TJ's guard is "spend that produced nothing"; that is the payment-with-no-output check.
    notes = ['%d output file(s) with no ledger row (reported, not a stop): %s' % (len(unpaid), unpaid[0])] if unpaid else []
    # THE RATIO, which is what TJ asked for in so many words: *"if we spend $100 and get 1 or
    # 0 meetings, something should trip."* A meeting costs ~$0.14; trip at $0.50 a produced
    # file over the last hour, once at least $1 has been spent.
    # LIKE FOR LIKE: only the calls old enough to have been audited (audit() skips the last
    # 2 minutes), divided by the paid calls matched among them. The first version divided ALL
    # the hour's spend by only the audited files and stopped a healthy run at 22:22 on
    # 7 October ($1.34 over 1 file, when 3 of the 4 calls were too new to audit). And the
    # bar is per PAID CALL, at $1.00: our own minutes (sonnet, from a recording) are $0.30-0.80
    # a call, so $0.50 a file was a bar the honest work could not clear.
    aged = [r for r in rows if r.get('result', 'ok') == 'ok' and
            (now - dt.datetime.fromisoformat(r['at'].replace('Z', '+00:00'))).total_seconds() > 120]
    aged_usd = sum(float(r['cost_usd'] or 0) for r in aged)
    per = aged_usd / matched if matched else float('inf')
    if aged_usd >= 1 and per > 1.00:
        problems.append('$%.2f spent for %d matched call(s) in the last hour -- $%s each, expected under $1'
                        % (aged_usd, matched, 'inf' if not matched else '%.2f' % per))
    # REPEATING: the same step paid for the same meeting twice inside the hour. Every step
    # is skipped once done, so a second paid call means the save did not take and the run
    # is going round -- the shape of the 6 October runaway, which spun on refused calls.
    seen = {}
    for r in rows:
        if r.get('result', 'ok') != 'ok':
            continue
        k = (r['stream'], r['board'], r['date'])
        seen[k] = seen.get(k, 0) + 1
    failed = sum(1 for r in rows if r.get('result') == 'failed')
    if failed > 5:
        problems.append('%d failed steps this hour' % failed)
    again = [k for k, n in seen.items() if n > 1]
    if again:
        problems.append('REPEATING: %d meeting step(s) paid for twice this hour, e.g. %s %s %s'
                        % ((len(again),) + again[0]))
    guard.notes = notes
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
    # ONLY THE CURRENT RUN'S LINES: after the last chunk the chainer started, or the last
    # governed run's opening `[gov] ` line -- an earlier run's STOPPED is history.
    marks = [m.end() for m in re.finditer(r'chunk of|\n\[gov\] ', tail)]
    current = tail[marks[-1]:] if marks else tail
    waiting = bool(re.search(r'waiting for the (window to reset|[0-9:]+ reset)', current))
    problems, matched, n_unmatched = guard(now)
    if 'STOPPED' in current:
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
