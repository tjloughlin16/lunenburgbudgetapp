#!/usr/bin/env python3
"""EVERY SOURCE, HOW OFTEN WE LOOK AT IT AGAIN, AND WHEN WE LAST DID. One register, one
due-check, run by the daily refresh -- there is no separate weekly or monthly script.

    python3 scripts/source_cadence.py              # live: last look, next due, what changed
    python3 scripts/source_cadence.py --due        # what the next refresh would run
    python3 scripts/source_cadence.py --write      # notes/reference/SOURCE-CADENCE.md, the reference
    python3 scripts/source_cadence.py --check      # that file reproduces, and the register is whole

TJ, 28 October 2026: *"we dont make a separate script, and that we just put it all in the
daily refresh script. but the 'cadence' of each source is known, checked against daily, and
if the either next scheduled run is hit or past, it fetches those sources too."*

That is catch-up scheduling -- anacron rather than cron: what is recorded is when each source
was last looked at, and a source is due when its cadence has elapsed SINCE THEN, so a missed
morning is made up the next one instead of waiting a whole cycle. The refresh already did
this three separate times by hand (oml_due, directory_due on two checked.csv files); this is
the one copy of it.

THE FILES

  sources/data/source-cadence.csv   the register, hand-kept: one row per source job
  sources/data/source-checks.csv    every look the refresh took, appended; ok=1 only when the
                                    job exited 0, so a failure is retried the next morning
  sources/data/copy-status.csv      per document: is our copy still the publisher's?
  sources/data/socrata-status.csv   per DESE dataset: have its rows changed since our copy?

A ROW'S `runs`

  step    its own step in refresh.py, every day; listed here so the table is complete
  gated   its own step in refresh.py, run only when due() says so
  job     run by the refresh's generic slow-sources step when due
  slice   run by that step EVERY day; the command itself picks the documents whose own last
          check is `cadence_days` old, a few at a time, so a big set is spread across the cycle
  (blank) not run by the refresh -- `manual` rows are run by hand, `never` rows arrive only
          when we ask for them

A CHANGE IS A FINDING. `check` rows never land a new copy: they record what moved, the refresh
names it in its notes, and `python3 scripts/source_cadence.py` lists it. A person lands the new copy through the
fetcher named for that source and re-runs what reads it.
"""
import argparse
import csv
import datetime as dt
import os
import re
import shlex
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')
DATA = os.path.join(ROOT, 'sources', 'data')
REGISTER = os.path.join(DATA, 'source-cadence.csv')
CHECKS = os.path.join(DATA, 'source-checks.csv')
COPIES = os.path.join(DATA, 'copy-status.csv')
SOCRATA = os.path.join(DATA, 'socrata-status.csv')
RUNS = os.path.join(DATA, 'refresh-runs.csv')
OUT = os.path.join(ROOT, 'notes', 'reference', 'SOURCE-CADENCE.md')

MODES = ('fetch', 'check', 'manual', 'never')
RUNS_KINDS = ('step', 'gated', 'job', 'slice', '')
TIERS = [(1, 'Daily'), (7, 'Weekly'), (30, 'Monthly'), (90, 'Quarterly'), (365, 'Yearly')]
# Fetchers that are not a source of their own: one is the documents step's crawler, one feeds
# the youtube watcher. Every OTHER scripts/fetch_*.py must be named by a register row, so a
# new fetcher cannot be written and silently never re-run -- the staff-directory gap.
PART_OF = {'fetch_agendas.py': 'meetings', 'fetch_school_budget_docs.py': 'documents',
           'fetch_town_docs.py': 'documents', 'fetch_youtube_index.py': 'youtube',
           'fetch_youtube_transcripts.py': 'youtube',
           # superseded by fetch_dese_socrata.py, whose --promote runs it for its three ids
           'fetch_dese_finance.py': 'socrata-dese-fetch',
           # the daily document watcher already lands every presentation on the FY27 hub
           'fetch_budget_presentations.py': 'documents'}


def _rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def register():
    return _rows(REGISTER)


def row(source_id):
    for r in register():
        if r['id'] == source_id:
            return r
    raise KeyError('no source %r in %s' % (source_id, os.path.relpath(REGISTER, ROOT)))


def cadence(r):
    return int(r['cadence_days']) if r['cadence_days'] else None


def last_ok(source_id, checks=None):
    days = [c['checked'] for c in (checks if checks is not None else _rows(CHECKS))
            if c['id'] == source_id and c['ok'] == '1']
    return max(days) if days else None


def next_due(r, checks=None):
    """-> 'YYYY-MM-DD' the source is next due, or None if it has never been looked at (so it
    is due now), or '' if the refresh does not run it."""
    if r['runs'] not in ('gated', 'job') or cadence(r) is None:
        return ''
    last = last_ok(r['id'], checks)
    if last is None:
        return None
    return (dt.date.fromisoformat(last) + dt.timedelta(days=cadence(r))).isoformat()


def due(source_id, as_of):
    """Should the refresh run this source on `as_of`? Due when its cadence has elapsed since
    the last SUCCESSFUL look -- on the day, or any day after it (catch-up)."""
    r = row(source_id)
    if r['runs'] in ('step', 'slice'):
        return True
    if r['runs'] not in ('gated', 'job'):
        return False
    nd = next_due(r)
    return nd is None or nd <= as_of


def record(source_id, as_of, ok, note=''):
    """Append one look. Re-reads nothing and rewrites nothing: an append cannot clobber a row
    another writer added, and the file's newline convention is kept as written."""
    row(source_id)
    new = not os.path.exists(CHECKS)
    with open(CHECKS, 'a', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, lineterminator='\n')
        if new:
            w.writerow(['id', 'checked', 'ok', 'note'])
        w.writerow([source_id, as_of, '1' if ok else '0', note])


def argv(r):
    """The refresh-runnable command of a job or slice row: [script, *args]."""
    return shlex.split(r['command'])


def writes(r):
    """The files a source's job writes that other scripts read, as declared in `writes`."""
    return r.get('writes', '').split()


def fingerprint(r):
    """{path: sha256} of what a job writes, so the refresh can tell whether a run CHANGED
    anything -- every fetcher exits 0 whether or not it did."""
    import hashlib
    out = {}
    for w in writes(r):
        full = os.path.join(ROOT, w)
        paths = ([os.path.join(dp, f) for dp, _, fs in os.walk(full) for f in fs]
                 if w.endswith('/') else [full])
        for pth in paths:
            if os.path.isfile(pth):
                with open(pth, 'rb') as fh:
                    out[pth] = hashlib.sha256(fh.read()).hexdigest()
    return out


def downstream(r):
    """-> [script]: every scripts/build_*.py that names a file this source writes. DERIVED,
    NOT LISTED: a hand-kept list of consumers is the stale-copy failure this repo keeps
    hitting, and the day somebody adds a page reading dls-tax-rates.csv it joins this list
    without anybody remembering to. A file is named by its basename, a folder by its own
    name (`federal-bls`)."""
    tokens = {os.path.basename(w.rstrip('/')) for w in writes(r)}
    if not tokens:
        return []
    out = []
    for f in sorted(os.listdir(SCRIPTS)):
        if f.startswith('build_') and f.endswith('.py'):
            with open(os.path.join(SCRIPTS, f), encoding='utf-8', errors='replace') as fh:
                text = fh.read()
            if any(t in text for t in tokens):
                out.append(f)
    return out


def runnable():
    return [r for r in register() if r['runs'] in ('job', 'slice')]


def changes(on=None):
    """-> [{found_by, what, detail, kind}]: what the checks found. kind `changed` is the
    publisher's copy moving; kind `ours` is a defect in our archive the same check exposed --
    kept apart, because reporting our own filing error as an edit by the district is rule 13's
    failure exactly. `on` limits it to findings recorded that day."""
    out = []
    # Only documents the copy checker still checks. copy-status.csv keeps a row for a path
    # until that path is checked again, so a document since RE-FILED under a new path leaves
    # its old row behind -- a finding about an address the archive no longer uses.
    sys.path.insert(0, SCRIPTS)
    import verify_source_copies as V
    live = set(V.eligible())
    rows = _rows(COPIES)
    # A PATH WITH TWO ADDRESSES, ONE OF WHICH MATCHES, is not an edit. The district publishes
    # some documents twice under near-identical titles ("CC & C.1", "CC & C 1") and the
    # crawler slugged both to one filename, so the archive holds one of two different
    # documents. All eight `differs` among the district's on 28 October 2026 were this.
    matched = {c['path'] for c in rows if c['state'] == 'identical'}
    for c in rows:
        if (c['state'] in ('differs', 'page, not file') and (c['path'], c['url']) in live
                and (on is None or c['checked'] == on)):
            kind = 'ours'
            if c['state'] == 'page, not file':
                what = 'our recorded address is a page, not the file (checked %s)'
            elif c['path'] in matched:
                what = ('a DIFFERENT document: this address and another were filed under one '
                        'name, and only the other is held (checked %s)')
            else:
                what, kind = 'content differs from the publisher\u2019s copy (checked %s)', 'changed'
            out.append(dict(found_by='copy check', what=c['path'], detail=what % c['checked'],
                            url=c['url'], kind=kind))
    for s in _rows(SOCRATA):
        if s['state'] == 'updated since our copy' and (on is None or s['checked'] == on):
            out.append(dict(found_by='DESE portal', what=s['name'],
                            detail='rows updated %s; our copy %s (checked %s)'
                            % (s['rows_updated'], s['our_copy'], s['checked']),
                            url='', kind='changed'))
    return out


def _prefixes(r):
    a = argv(r)
    return [a[i + 1] for i, x in enumerate(a) if x == '--prefix' and i + 1 < len(a)]


def coverage(r, as_of, copies=None):
    """A slice row -> (checked within its cadence, eligible). The eligible list is the copy
    checker's own, so the denominator is what it would check, not a count kept here."""
    sys.path.insert(0, SCRIPTS)
    import verify_source_copies as V
    items = V.eligible(_prefixes(r))
    seen = {(c['path'], c['url']): c['checked'] for c in (copies if copies is not None
                                                           else _rows(COPIES))}
    cut = (dt.date.fromisoformat(as_of) - dt.timedelta(days=cadence(r))).isoformat()
    return sum(1 for it in items if seen.get(it, '') > cut), len(items)


def as_of_date():
    """The newest date any of the files records. The README is dated by its DATA, never by the
    clock, so --check reproduces it tomorrow."""
    days = [c['checked'] for c in _rows(CHECKS)]
    days += [c['checked'] for c in _rows(COPIES) if c.get('checked')]
    days += [s['checked'] for s in _rows(SOCRATA) if s.get('checked')]
    days += [x.get('as_of', '') for x in _rows(RUNS)[-1:]]
    return max(d for d in days if d)


def validate():
    """-> [problem]: the register is whole and every command it names exists."""
    bad, ids, named = [], set(), set()
    for r in register():
        if r['id'] in ids:
            bad.append('duplicate id %s' % r['id'])
        ids.add(r['id'])
        if r['mode'] not in MODES:
            bad.append('%s: mode %r is not one of %s' % (r['id'], r['mode'], MODES))
        if r['runs'] not in RUNS_KINDS:
            bad.append('%s: runs %r is not one of %s' % (r['id'], r['runs'], RUNS_KINDS))
        if r['runs'] in ('gated', 'job', 'slice') and cadence(r) is None:
            bad.append('%s: runs %s with no cadence_days' % (r['id'], r['runs']))
        if r['mode'] == 'never' and r['runs']:
            bad.append('%s: a never source cannot be run' % r['id'])
        for s in re.findall(r'[\w]+\.py', r['command']):
            named.add(s)
            if not os.path.exists(os.path.join(SCRIPTS, s)):
                bad.append('%s: names %s, which does not exist' % (r['id'], s))
        for w in writes(r):
            if not os.path.exists(os.path.join(ROOT, w)):
                bad.append('%s: writes %s, which does not exist' % (r['id'], w))
    for c in _rows(CHECKS):
        if c['id'] not in ids:
            bad.append('source-checks.csv names %s, which is not in the register' % c['id'])
    for f in sorted(os.listdir(SCRIPTS)):
        if f.startswith('fetch_') and f.endswith('.py') and f not in named and f not in PART_OF:
            bad.append('%s is not in source-cadence.csv: give it a row and a cadence' % f)
    return bad


def _every(n):
    if n is None:
        return '\u2014'
    return {1: 'daily', 7: 'weekly', 30: 'monthly', 90: 'every 90 days',
            365: 'yearly'}.get(n, 'every %d days' % n)


def _how(r):
    return {'step': 'every refresh', 'gated': 'refresh, when due', 'job': 'refresh, when due',
            'slice': 'refresh, a slice a day'}.get(r['runs'], 'by hand' if r['mode'] == 'manual'
                                                    else 'when we ask')


REFRESH_PLIST = os.path.expanduser(
    '~/Library/LaunchAgents/org.lunenburgbudgetproject.refresh.plist')


def refresh_time():
    """(hour, minute) the daily refresh is scheduled for, read off its launchd job -- the one
    place the schedule actually lives -- or None where there is no such job (another machine)."""
    import plistlib
    try:
        with open(REFRESH_PLIST, 'rb') as fh:
            when = plistlib.load(fh).get('StartCalendarInterval') or {}
        return int(when['Hour']), int(when.get('Minute', 0))
    except (OSError, KeyError, ValueError, TypeError):
        return None


def next_refresh(now=None):
    """The next morning the refresh will run: today if today's has not run yet, else
    tomorrow. Read off refresh-runs.csv, so a run that has not happened is not assumed."""
    now = now or dt.datetime.now()
    runs = _rows(RUNS)
    ran_today = bool(runs) and runs[-1].get('as_of') == now.date().isoformat()
    day = now.date() + dt.timedelta(days=1 if ran_today else 0)
    hm = refresh_time() or (0, 0)
    return dt.datetime.combine(day, dt.time(*hm))


def status_rows(now=None):
    """-> one dict per scheduled source: when it was last fetched, when it will next be, and
    whether anything is wrong. THE ONE COPY of this logic: the dashboard's Sources card and
    `python3 scripts/source_cadence.py` both read it, so they cannot disagree.

      last_ok    the day of the last SUCCESSFUL look, from source-checks.csv, or None
      last_fail  the day of a failed look AFTER that, or None
      next       the refresh morning it will next be fetched on (a datetime), or None
      state      ok | due (overdue, will be retried) | failed | never | unscheduled
      detail     for a slice, how much of its set was checked within the cadence
    """
    now = now or dt.datetime.now()
    nxt = next_refresh(now)
    checks, copies = _rows(CHECKS), _rows(COPIES)
    out = []
    for r in register():
        if r['mode'] == 'never':
            continue
        mine = [c for c in checks if c['id'] == r['id']]
        ok = max((c['checked'] for c in mine if c['ok'] == '1'), default=None)
        bad = max((c['checked'] for c in mine if c['ok'] != '1'), default=None)
        fail = bad if bad and (ok is None or bad > ok) else None
        row = dict(id=r['id'], source=r['source'], cadence=cadence(r), runs=r['runs'],
                   last_ok=ok, last_fail=fail, next=None, detail='')
        if not r['runs']:
            row['state'] = 'unscheduled'
        else:
            due_day = next_due(r, checks) if r['runs'] in ('gated', 'job') else ''
            if due_day and due_day > nxt.date().isoformat():
                row['next'] = dt.datetime.combine(dt.date.fromisoformat(due_day), nxt.time())
            else:
                row['next'] = nxt
            if r['runs'] == 'slice':
                n, of = coverage(r, now.date().isoformat(), copies)
                row['detail'] = '%d of %d checked in the last %d days' % (n, of, cadence(r))
            if fail:
                row['state'] = 'failed'
            elif ok is None:
                row['state'] = 'never'
            elif (dt.date.fromisoformat(ok) + dt.timedelta(days=cadence(r))
                  < nxt.date()) and r['runs'] in ('gated', 'job', 'step'):
                row['state'] = 'due'
            else:
                row['state'] = 'ok'
        out.append(row)
    return out


def _state(row):
    """(last fetched, next) as table cells for the live terminal view."""
    last = row['last_ok'] or 'never'
    if row['last_fail']:
        last += ' (failed %s)' % row['last_fail']
    if row['state'] == 'unscheduled':
        return last, 'NOT SCHEDULED'
    nxt = row['next'].strftime('%a %d %b %H:%M') if row['next'] else '\u2014'
    return last, nxt + ('; ' + row['detail'] if row['detail'] else '')


def _cell(s):
    return str(s).replace('|', '\\|').replace('\n', ' ')


def partial_tree():
    """-> [key]: documents a slice counts that THIS tree does not hold. Coverage is counted off
    files on disk, so a partial tree would publish a smaller denominator as though it were
    the archive's (CLAUDE.md: a partial tree may not publish a count)."""
    sys.path.insert(0, SCRIPTS)
    import archive_storage as AS
    return [k for r in register() if r['runs'] == 'slice'
            for pre in _prefixes(r) for k in AS.incomplete('sources/' + pre)]


def render(live=False):
    """The reference document, or with `live` the same tables with each source's last look,
    next due date and what the checks have found -- for the terminal.

    THE FILE IS A REFERENCE, NOT A STATUS REPORT. TJ, 28 October 2026: *"i want this doc
    permanently [kept] and used as reference. its not a temporal doc."* So the written file
    holds only what the register says -- what each source is, how often, how it is run -- and
    changes only when the register does. Anything dated lives in the check logs and is read
    live by running this script."""
    regs = register()
    n_by = {m: sum(1 for r in regs if r['mode'] == m) for m in MODES}
    auto = sum(1 for r in regs if r['runs'])
    L = ['# Every source, and how often we look at it again', '',
         '*Generated by `scripts/source_cadence.py` from `sources/data/source-cadence.csv`. '
         'Do not edit; edit the register. For each source\u2019s last look, next due date and '
         'anything the checks have found, run `python3 scripts/source_cadence.py`.*', '',
         '**%d sources. %d are re-checked by the daily refresh; %d are run by hand; %d arrive '
         'only when we ask.** The refresh runs every morning and looks at each source whose '
         'cadence has come round, or passed, since it was last looked at successfully.'
         % (len(regs), auto, n_by['manual'], n_by['never']), '']
    if live:
        gone = partial_tree()
        if gone:
            raise SystemExit('REFUSING: this tree is missing %d archived documents (%s ...), so '
                             'its coverage counts would understate the archive. Run python3 '
                             'scripts/sync_archive.py --pull' % (len(gone), gone[0]))
        as_of = as_of_date()
        status = {x['id']: x for x in status_rows()}
        pub = [c for c in changes() if c['kind'] == 'changed']
        L += ['## Changed at the publisher (as of %s)' % as_of, '']
        if pub:
            L += ['| found by | what | detail |', '|---|---|---|']
            L += ['| %s | %s | %s |' % tuple(_cell(c[k]) for k in ('found_by', 'what', 'detail'))
                  for c in pub]
        else:
            L += ['Nothing the checks have found.']
        L += ['']
    for days, name in TIERS:
        rs = [r for r in regs if cadence(r) == days and r['mode'] != 'never']
        if not rs:
            continue
        head = ['source', 'publisher', 'does', 'how'] + (['last fetched', 'next fetch'] if live else [])
        L += ['## %s' % name, '', '| %s |' % ' | '.join(head),
              '|%s' % ('---|' * len(head))]
        for r in rs:
            cells = ['**%s** `%s`' % (r['source'], r['id']), r['publisher'],
                     'checks' if r['mode'] == 'check' or r['command'].startswith(('check_', 'verify_'))
                     else 'fetches', _how(r)]
            if live:
                cells += list(_state(status[r['id']]) if r['id'] in status
                              else ('\u2014', '\u2014'))
            L.append('| %s |' % ' | '.join(_cell(x) for x in cells))
        L.append('')
    rest = [r for r in regs if cadence(r) is None]
    if rest:
        L += ['## No schedule', '', '| source | publisher | why |', '|---|---|---|']
        L += ['| **%s** `%s` | %s | %s |' % tuple(_cell(x) for x in (r['source'], r['id'],
                                                                    r['publisher'], r['note']))
              for r in rest]
        L.append('')
    if live:
        return '\n'.join(L)
    L += ['## What each source is, and how it is run', '',
          '| id | command | covers | note |', '|---|---|---|---|']
    L += ['| `%s` | %s | %s | %s |' % tuple(_cell(x) for x in (
        r['id'], '`%s`' % r['command'] if r['command'] else '\u2014', r['covers'], r['note']))
        for r in regs]
    L += ['', '## How it works', '',
          '- **does: fetches** lands a new copy when the publisher\u2019s changed. **checks** '
          'only compares and reports; nothing is downloaded into the archive.',
          '- **when due** means the cadence has elapsed since the last *successful* look. A '
          'failed look is recorded as failed and tried again the next morning.',
          '- **a slice a day** spreads a large set across its cycle: each morning checks the '
          'documents whose own last check is oldest, a few dozen at most, so no single '
          'morning carries the whole set.',
          '- **by hand** rows have a target cadence and no schedule yet. A row stays here until '
          'its fetcher has been reviewed for running unattended.',
          '- Every look is a row in `sources/data/source-checks.csv`; per-document results are '
          'in `copy-status.csv`, per-dataset results in `socrata-status.csv`.', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--write', action='store_true')
    g.add_argument('--check', action='store_true')
    g.add_argument('--due', action='store_true')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    a = ap.parse_args()
    bad = validate()
    if bad:
        for b in bad:
            print('  REGISTER: ' + b)
        return 1
    if a.due:
        for r in register():
            if r['runs'] in ('gated', 'job', 'slice') and due(r['id'], a.as_of):
                print('  %-26s %s' % (r['id'], r['command']))
        return 0
    if not (a.check or a.write):
        print(render(live=True))
        return 0
    text = render()
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != text:
            print('%s is stale: run python3 scripts/source_cadence.py --write'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('%s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    if a.write:
        tmp = OUT + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(text)
        os.replace(tmp, OUT)
        print('wrote %s' % os.path.relpath(OUT, ROOT))
        return 0


if __name__ == '__main__':
    sys.exit(main())
