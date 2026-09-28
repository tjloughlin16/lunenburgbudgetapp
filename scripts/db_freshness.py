#!/usr/bin/env python3
"""IS THE DATABASE STILL TRUE? Asked offline, in one place, by anything that quotes it.

`lunenburg.db` is a derived read model, rebuilt from the CSVs every run. Nothing is ever
edited in it. That makes it safe to throw away and it does NOT make it safe to quote,
because a derived thing goes on answering confidently after the thing it derived from has
moved.

WHAT THIS EXISTS BECAUSE OF. On 27 September 2026 the annual-report page queue published
`469 read, 5 left`. The true figures were 459 and 15. `map_annual_report_pages.py` marks a
page read if EITHER a CSV or the DATABASE cites its fiscal year and page, and the database
still held a four-day-old import of `receivables.csv` -- 342 rows that had already been
deleted for not proving against the totals their own pages print. So ten pages were
credited on the strength of rows that no longer existed anywhere.

Nothing was wrong with the database except its age. No check could see it, and it was
found by a person reading the dashboard and asking why a number went the wrong way.

THE RULE THIS MAKES MECHANICAL. A count derived from the database may not be published
while the database disagrees with the files it was built from. `build_db.py` hashes every
CSV it reads into `build_inputs`; this compares those hashes to what is on disk now. It is
offline, it reads no network, and it is a few milliseconds.

    import db_freshness
    db_freshness.require_fresh()      # raises SystemExit naming the files and the remedy

A caller that would rather degrade than refuse asks instead:

    changed = db_freshness.stale()    # [] when the database still matches its inputs

WHY IT COMPARES HASHES AND NOT TIMES. An mtime moves when a generator rewrites a file
byte-for-byte, which happens on every run of everything here, so a time comparison would
cry stale constantly and be ignored within a day. A hash only moves when the CONTENT moved,
which is the only thing that can change an answer. A check nobody believes is worse than
no check, because it trains the reader to skip the real one.
"""
import os
import hashlib
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')


def _sha(path):
    try:
        with open(path, 'rb') as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def recorded(db_path=DB):
    """What the database says it was built from: {repo-relative path: sha256}.

    An empty dict means the database predates `build_inputs` and cannot answer. That is
    reported as a distinct state rather than as freshness, because "it does not say" and
    "it says yes" are different answers and only one of them is reassuring.
    """
    if not os.path.exists(db_path):
        return {}
    db = sqlite3.connect('file:%s?mode=ro' % db_path, uri=True)
    try:
        have = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='build_inputs'"
        ).fetchone()
        if not have:
            return {}
        return {p: s for p, s in db.execute('SELECT path, sha256 FROM build_inputs')}
    finally:
        db.close()


def stale(db_path=DB):
    """The files whose CONTENT has changed since the database imported them.

    Returns a list of (path, why) with `why` one of `changed` or `gone`. Empty means every
    file the build read still hashes to what it hashed then.
    """
    out = []
    for path, sha in sorted(recorded(db_path).items()):
        now = _sha(os.path.join(ROOT, path))
        if now is None:
            out.append((path, 'gone'))
        elif now != sha:
            out.append((path, 'changed'))
    return out


def unknown(db_path=DB):
    """True when the database cannot say what it was built from."""
    return not recorded(db_path)


def require_fresh(db_path=DB, what='a count'):
    """Refuse rather than publish a figure off a database that no longer matches its inputs.

    `what` names the thing that would have been published, because the useful sentence for
    whoever hits this is what they were about to get wrong, not that a check failed.
    """
    if unknown(db_path):
        raise SystemExit(
            'REFUSING to publish %s: %s records nothing about what it was built from.\n'
            'Rebuild it so it does, then this check can answer:\n'
            '    python3 scripts/build_db.py'
            % (what, os.path.relpath(db_path, ROOT)))
    bad = stale(db_path)
    if bad:
        lines = '\n'.join('    %-56s %s' % (p, why) for p, why in bad)
        raise SystemExit(
            'REFUSING to publish %s: the database was built from files that have since '
            'moved, so a figure taken from it is about the past.\n%s\n'
            'Rebuild it and run this again:\n'
            '    python3 scripts/build_db.py'
            % (what, lines))


def main():
    if unknown():
        print('lunenburg.db records nothing about what it was built from — '
              'run: python3 scripts/build_db.py')
        return 1
    bad = stale()
    n = len(recorded())
    if not bad:
        print('ok: lunenburg.db still matches all %d csv file(s) it was built from' % n)
        return 0
    print('STALE: %d of %d input file(s) have changed since the database was built'
          % (len(bad), n))
    for p, why in bad:
        print('  %-56s %s' % (p, why))
    print('Run: python3 scripts/build_db.py')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
