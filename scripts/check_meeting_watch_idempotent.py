#!/usr/bin/env python3
"""The acceptance test for the meeting watch: running it twice produces ONE result.

    python3 scripts/check_meeting_watch_idempotent.py

TJ's requirement for every refresh mechanism was one word -- DETERMINISTIC -- and the
failure it rules out is a feed announcing the same document twice. That is not something a
reader can check and it is not something a --check on a generated file can catch, because
a double-announced document reproduces perfectly well. It needs a test that actually runs
the detector twice.

WHAT IS ACTUALLY EXERCISED

Nothing is stubbed. `watch_meetings.py` runs as a subprocess, four times, with its state
directory and its observation source pointed at a temporary copy -- so the diff, the state
merge, the event log and the run log are the real ones.

  1. SEED from a truncated copy of the meetings index. Announces nothing, by definition.
  2. OBSERVE the same truncated copy. Nothing is new; nothing may be announced.
  3. OBSERVE the FULL index. Exactly the withheld documents must be announced -- and it
     must announce them as agendas and minutes in the right proportions, not merely the
     right count.
  4. OBSERVE the full index AGAIN. Nothing new, and all three files byte-identical to
     step 3. This is the acceptance test.

Step 2 is the one worth having separately: a detector that announced everything it saw
would still pass step 4, because by then it has seen everything.
"""
import csv
import filecmp
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH = os.path.join(ROOT, 'scripts', 'watch_meetings.py')
INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
WITHHOLD = 40          # documents kept back from the seed, then revealed
FILES = ['meeting-watch-state.csv', 'meeting-watch-events.csv', 'meeting-watch-runs.csv']


def run(tmp, index, *args):
    env = dict(os.environ, MEETING_WATCH_DIR=tmp, MEETING_WATCH_INDEX=index)
    r = subprocess.run([sys.executable, WATCH, '--source', 'index',
                        '--as-of', '2026-01-01', *args],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('watch_meetings.py failed:\n' + (r.stdout + r.stderr))
    return r.stdout


def announced(tmp):
    p = os.path.join(tmp, 'meeting-watch-events.csv')
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p, encoding='utf-8')))


def digests(tmp):
    return {f: hashlib.sha256(open(os.path.join(tmp, f), 'rb').read()).hexdigest()
            for f in FILES}


def main():
    if not os.path.exists(INDEX):
        print('FAIL — sources/meetings/index.csv is absent; nothing to test against')
        return 1
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8', errors='replace')))
    rows = [r for r in rows if r.get('kind') in ('agenda', 'minutes') and r.get('file_id')]
    if len(rows) < WITHHOLD * 10:
        print('FAIL — the meetings index holds only %d documents; too few to test'
              % len(rows))
        return 1

    # Withhold the most recent documents -- the ones a live crawl would actually be first
    # to see -- rather than an arbitrary slice, and take HALF FROM EACH KIND. The newest
    # rows by date are all agendas for meetings that have not happened yet, so a plain
    # tail would test the agenda path and leave the minutes path -- the surface this whole
    # thing exists for -- unexercised.
    rows.sort(key=lambda r: (r['date'], r['kind'], r['file_id']))
    by_kind = {k: [r for r in rows if r['kind'] == k] for k in ('agenda', 'minutes')}
    held_back = (by_kind['agenda'][-(WITHHOLD // 2):]
                 + by_kind['minutes'][-(WITHHOLD - WITHHOLD // 2):])
    withheld_keys = {(r['board'], r['date'], r['kind'], r['file_id']) for r in held_back}
    kept = [r for r in rows
            if (r['board'], r['date'], r['kind'], r['file_id']) not in withheld_keys]
    want_ag = sum(1 for r in held_back if r['kind'] == 'agenda')
    want_mi = sum(1 for r in held_back if r['kind'] == 'minutes')

    tmp = tempfile.mkdtemp(prefix='meeting-watch-test-')
    try:
        full = os.path.join(tmp, 'index-full.csv')
        part = os.path.join(tmp, 'index-part.csv')
        shutil.copy(INDEX, full)
        with open(part, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(kept)

        fails = []

        run(tmp, part, '--seed')
        if announced(tmp):
            fails.append('the SEED announced %d documents. A seed adopts what is already '
                         'known and must announce nothing.' % len(announced(tmp)))

        run(tmp, part)
        if announced(tmp):
            fails.append('a crawl over documents already seeded announced %d of them as '
                         'new.' % len(announced(tmp)))

        run(tmp, full)
        got = announced(tmp)
        got_ag = sum(1 for e in got if e['kind'] == 'agenda')
        got_mi = sum(1 for e in got if e['kind'] == 'minutes')
        if (len(got), got_ag, got_mi) != (WITHHOLD, want_ag, want_mi):
            fails.append('revealing %d withheld documents (%d agendas, %d minutes) '
                         'announced %d (%d agendas, %d minutes).'
                         % (WITHHOLD, want_ag, want_mi, len(got), got_ag, got_mi))
        before = digests(tmp)

        run(tmp, full)
        after = digests(tmp)
        if len(announced(tmp)) != len(got):
            fails.append('the SECOND identical run announced %d more documents.'
                         % (len(announced(tmp)) - len(got)))
        drifted = [f for f in FILES if before[f] != after[f]]
        if drifted:
            fails.append('running twice changed %s. Running twice must produce one '
                         'result, not two.' % ', '.join(drifted))

        if fails:
            print('FAIL — the meeting watch is not deterministic:')
            for f in fails:
                print('  ' + f)
            return 1
        print('ok — seed announced nothing; %d withheld documents (%d agendas, %d '
              'minutes) announced exactly once; a second identical run announced nothing '
              'and left all %d state files byte-identical'
              % (WITHHOLD, want_ag, want_mi, len(FILES)))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
