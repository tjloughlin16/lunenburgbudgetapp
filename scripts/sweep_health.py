#!/usr/bin/env python3
"""HOW LONG SINCE THE AGENTIC STREAMS LAST PRODUCED ANYTHING. Read-only.

    python3 scripts/sweep_health.py           # a line per stream, and an exit code
    python3 scripts/sweep_health.py --json

WHY THIS EXISTS. On the night of 26 September 2026 both backlog streams stopped producing
at about 23:00 -- the sweep hit the rolling five-hour session limit and went into
exponential backoff, and the votes backfill died with `FileNotFoundError: claude` -- and
both processes stayed ALIVE AND IDLE for eight hours. Nothing noticed, because the only
signals were a log that buffers through `sed` and a ledger nobody reads while it is being
written. A process being up is not a process working, and `pgrep` cannot tell them apart.

So health is measured by OUTPUT, never by liveness:

  * the sweep writes a costed row to agentic-spend.csv for every job it finishes;
  * the votes backfill writes a JSON file under sources/data/official-votes/;
  * the minutes stream writes one under sources/data/recording-minutes/.

The newest of those, per stream, is the only honest answer to `is it working`.

EXIT CODE. 0 if at least one stream produced inside --stale-minutes, 1 if none did. That
is what makes it usable from a supervisor and from a shell prompt alike.
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')


def newest_file(pattern):
    """The most recent mtime under a glob, as an aware UTC datetime, or None.

    Walks rather than sorting every path: these directories hold thousands of files and
    this runs from a supervisor every few minutes.
    """
    best = None
    for p in glob.iglob(pattern, recursive=True):
        try:
            m = os.path.getmtime(p)
        except OSError:
            continue
        if best is None or m > best:
            best = m
    return dt.datetime.fromtimestamp(best, dt.timezone.utc) if best else None


def newest_ledger_row():
    """When the sweep last LOGGED a finished job -- costed or not."""
    if not os.path.exists(LEDGER):
        return None
    best = None
    with open(LEDGER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            try:
                at = dt.datetime.strptime(r['at'], '%Y-%m-%dT%H:%M:%SZ').replace(
                    tzinfo=dt.timezone.utc)
            except (ValueError, KeyError):
                continue
            if best is None or at > best:
                best = at
    return best


def streams():
    return [
        ('sweep ledger', newest_ledger_row()),
        ('votes written', newest_file(os.path.join(
            ROOT, 'sources', 'data', 'official-votes', '**', '*.json'))),
        ('minutes written', newest_file(os.path.join(
            ROOT, 'sources', 'data', 'recording-minutes', '**', '*.json'))),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stale-minutes', type=int, default=45)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for name, at in streams():
        mins = None if at is None else (now - at).total_seconds() / 60.0
        out.append(dict(stream=name, last=at.isoformat() if at else None,
                        minutes_ago=None if mins is None else round(mins, 1),
                        fresh=bool(mins is not None and mins <= a.stale_minutes)))
    if a.json:
        print(json.dumps(dict(stale_minutes=a.stale_minutes, streams=out), indent=1))
    else:
        for r in out:
            print('  %-16s %s' % (
                r['stream'],
                'never' if r['minutes_ago'] is None
                else '%6.1f min ago%s' % (r['minutes_ago'], '' if r['fresh'] else '   STALE')))
    return 0 if any(r['fresh'] for r in out) else 1


if __name__ == '__main__':
    raise SystemExit(main())
