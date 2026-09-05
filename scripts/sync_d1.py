#!/usr/bin/env python3
"""Push the analysis database to D1, which is what `/api/query` reads.

    python3 scripts/sync_d1.py [--check]

`sources/data/lunenburg.db` is rebuilt from the CSVs on every run of `build_db.py`. D1 is
a SECOND copy of it, live at the edge, and a second copy is a thing that can disagree with
the first. That failure has happened repeatedly in this project -- a page cache serving a
pre-reorg extraction, an API index a day out of date, a provenance join left pointing at a
folder its documents had left -- and every time it looked like working software.

So: `--check` compares the row count of every table against the local database and fails
on any difference. Run it after `build_db.py`, and before believing an answer that came
out of `/api/query`.

The import is a full replace: every table is dropped and recreated from a fresh dump. The
database is 16MB and 50,000 rows; a differential sync would be faster and would be one
more thing that can be subtly wrong.
"""
import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
APP = os.path.join(ROOT, 'fy28')
NAME = 'lunenburg-budget'
# Wrangler needs Node 22; the system Node is 20 and fails with a version error.
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
# The sha256 of the database last successfully imported. Tracked in git, so a clone knows
# whether the live copy is the one this repository describes.
PUSHED = os.path.join(ROOT, 'sources', 'data', 'd1-pushed.txt')


def db_sha256():
    import hashlib
    h = hashlib.sha256()
    with open(DB, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def wrangler(*args, timeout=1800):
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    return subprocess.run(['npx', 'wrangler', *args], cwd=APP, env=env,
                          capture_output=True, text=True, timeout=timeout)


def remote_counts():
    """{table: rows} as D1 reports it, in one round trip."""
    local = sqlite3.connect(DB)
    tables = [r[0] for r in local.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    # Small UNION batches via --command.
    #
    # Not --file: with a file, wrangler returns a SUMMARY ("Total queries executed: 54")
    # rather than the rows, so the counts never arrive. And not one big UNION either: a
    # twelve-table union was rejected by the API while two worked. Three is under whatever
    # the limit is, and a count query that fails is indistinguishable from a table that is
    # empty -- the wrong way for a consistency check to be wrong.
    out = {}
    for i in range(0, len(tables), 3):
        chunk = tables[i:i + 3]
        sql = ' UNION ALL '.join(
            f"SELECT '{t}' AS t, COUNT(*) AS n FROM \"{t}\"" for t in chunk)
        r = wrangler('d1', 'execute', NAME, '--remote', '--json', '--command', sql, '-y')
        if r.returncode != 0:
            sys.exit('d1 count query failed for ' + ', '.join(chunk) + '\n'
                     + (r.stderr or r.stdout)[-700:])
        payload = json.loads(re.sub(r'^[^\[{]*', '', r.stdout.strip(), count=1))
        for block in (payload if isinstance(payload, list) else [payload]):
            for x in block.get('results', []):
                vals = list(x.values()) if isinstance(x, dict) else list(x)
                if len(vals) >= 2:
                    out[str(vals[0])] = int(vals[1])
    return out


def local_counts():
    db = sqlite3.connect(DB)
    return {t: db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            for (t,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def compare():
    want, got = local_counts(), remote_counts()
    bad = []
    for t in sorted(set(want) | set(got)):
        a, b = want.get(t), got.get(t)
        if a != b:
            bad.append(f'{t}: local {a}, D1 {b}')
    return want, got, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='compare row counts and fail on any difference')
    ap.add_argument('--force', action='store_true',
                    help='import even if this database has already been imported')
    args = ap.parse_args()

    if not os.path.exists(DB):
        sys.exit('no database; run scripts/build_db.py first')

    if args.check:
        want, got, bad = compare()
        if bad:
            print(f'D1 disagrees with {DB} on {len(bad)} table(s):')
            for b in bad[:12]:
                print('  ' + b)
            print('\n  Run: python3 scripts/sync_d1.py')
            return 1
        print(f'ok: D1 matches the local database — {len(want)} tables, '
              f'{sum(want.values()):,} rows')
        return 0

    here = db_sha256()
    last = open(PUSHED).read().strip() if os.path.exists(PUSHED) else ''
    rows = sum(local_counts().values())
    if here == last and not args.force:
        print(f'nothing to do: D1 already holds this database ({here[:12]}).\n'
              f'  A full replace writes about {rows:,} rows against a free-tier limit of\n'
              f'  100,000 a day, so it is not run for a database that has not changed.\n'
              f'  Use --force if you believe the live copy has drifted, or --check to ask it.')
        return 0
    print(f'importing {rows:,} rows (~{rows * 2:,} writes with indexes) — the free tier '
          f'allows 100,000 a day')

    src = sqlite3.connect(DB)
    with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as fh:
        n = 0
        for line in src.iterdump():
            # D1 rejects transaction control and does not use sqlite_sequence.
            if line.startswith(('BEGIN TRANSACTION', 'COMMIT')) or 'sqlite_sequence' in line:
                continue
            fh.write(line + '\n')
            n += 1
        dump = fh.name
    print(f'{n:,} statements, {os.path.getsize(dump) / 1e6:.1f} MB')

    # A full replace: drop what is there, then load. Anything else leaves rows from a
    # previous shape of the data sitting under a table that has since changed.
    #
    # Children before parents. The first attempt dropped in alphabetical order and D1
    # answered `FOREIGN KEY constraint failed` -- the schema has real foreign keys, so the
    # order is not arbitrary. Computed from the local schema rather than hand-listed,
    # because a hand-listed order is a thing that goes stale when a table is added.
    deps = {}
    for t in local_counts():
        deps[t] = {r[2] for r in src.execute(f'PRAGMA foreign_key_list("{t}")')}
    order, seen = [], set()

    def visit(t):
        if t in seen:
            return
        seen.add(t)
        for parent in deps.get(t, ()):  # a parent must be dropped AFTER its children
            visit(parent)
        order.append(t)

    for t in deps:
        visit(t)
    order.reverse()   # parents first in `order`; reverse gives children first
    # Views first: they are defined over the tables, so they must go before them. The
    # dump recreates them, and D1 answered `view ... already exists` when they did not.
    views = [v for (v,) in src.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
    drops = '; '.join([f'DROP VIEW IF EXISTS "{v}"' for v in views]
                      + [f'DROP TABLE IF EXISTS "{t}"' for t in order])
    r = wrangler('d1', 'execute', NAME, '--remote', '--command', drops, '-y')
    if r.returncode != 0:
        sys.exit(f'could not clear D1:\n{r.stderr[-1200:]}')

    r = wrangler('d1', 'execute', NAME, '--remote', '--file', dump, '-y')
    os.unlink(dump)
    if r.returncode != 0:
        sys.exit(f'import failed:\n{r.stderr[-1500:]}')
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'imported')

    want, got, bad = compare()
    if bad:
        print(f'\nFAIL: D1 still disagrees on {len(bad)} table(s):')
        for b in bad[:12]:
            print('  ' + b)
        return 1
    with open(PUSHED, 'w') as fh:
        fh.write(here + '\n')
    print(f'ok: D1 matches — {len(want)} tables, {sum(want.values()):,} rows')
    return 0


if __name__ == '__main__':
    sys.exit(main())
