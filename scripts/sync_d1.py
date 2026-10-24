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

import d1_incremental as INC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
APP = os.path.join(ROOT, 'fy28')
NAME = 'lunenburg-budget'
# Wrangler needs Node 22; the system Node is 20 and fails with a version error.
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
# The sha256 of the database last successfully imported. Tracked in git, so a clone knows
# whether the live copy is the one this repository describes.
PUSHED = os.path.join(ROOT, 'sources', 'data', 'd1-pushed.txt')
# What the last push actually SENT, recorded so `--plan` can say which tables the
# published copy is missing without asking the network — which is the one thing you
# cannot do when the reason you are planning is that the budget is spent.
PUSHED_TABLES = os.path.join(ROOT, 'sources', 'data', 'd1-pushed-tables.txt')


def _last_tables():
    """Tables the last recorded push sent. Empty when we have never recorded one."""
    if not os.path.exists(PUSHED_TABLES):
        return []
    return [l.strip() for l in open(PUSHED_TABLES) if l.strip()]


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


def remote_digests():
    """What D1 says it holds, per table, from its own `synced_table`.

    A missing table is not an error: it means the remote has never had an incremental push
    and every table counts as new. That is the correct reading -- we genuinely do not know
    what is there -- and it is why this returns {} rather than failing.
    """
    r = wrangler('d1', 'execute', NAME, '--remote', '--json', '--command',
                 'SELECT name, sha256, rows FROM %s' % INC.SYNC_TABLE, '-y')
    if r.returncode != 0:
        return {}
    try:
        payload = json.loads(re.sub(r'^[^\[{]*', '', r.stdout.strip(), count=1))
    except ValueError:
        return {}
    rows = []
    for block in (payload if isinstance(payload, list) else [payload]):
        rows.extend(block.get('results', []) or [])
    return INC.parse_remote(rows)


def _rows(sql):
    r = wrangler('d1', 'execute', NAME, '--remote', '--json', '--command', sql, '-y')
    if r.returncode != 0:
        return None
    try:
        payload = json.loads(re.sub(r'^[^\[{]*', '', r.stdout.strip(), count=1))
    except ValueError:
        return None
    out = []
    for block in (payload if isinstance(payload, list) else [payload]):
        out.extend(block.get('results', []) or [])
    return out


def remote_stages():
    """{table: (sha256, rows already loaded)} for every table being loaded in pieces.

    The loaded count is COUNT(*) of the staging table itself, never a number we wrote down:
    a run that failed part-way leaves a prefix of its slice behind, and only the count says
    where that prefix ends (see d1_incremental.plan_staged). No `synced_stage` table means
    nothing has ever been staged.
    """
    out = {}
    for x in _rows('SELECT name, sha256 FROM %s' % INC.STAGE_TABLE) or []:
        name, sha = (list(x.values()) if isinstance(x, dict) else list(x))[:2]
        got = _rows('SELECT COUNT(*) AS n FROM "%s"' % INC.stage_name(name))
        if got is None:
            continue                # a registered stage with no table: start it again
        n = list(got[0].values())[0] if got and isinstance(got[0], dict) else 0
        out[str(name)] = (str(sha), int(n))
    return out


def local_indexes():
    """{index name: CREATE INDEX IF NOT EXISTS ...} for every index the schema declares.

    Autoindexes (a PRIMARY KEY or UNIQUE constraint) have no SQL and come with the table."""
    db = sqlite3.connect(DB)
    out = {}
    for name, sql in db.execute("SELECT name, sql FROM sqlite_master "
                                "WHERE type='index' AND sql IS NOT NULL ORDER BY name"):
        out[name] = re.sub(r'^CREATE\s+(UNIQUE\s+)?INDEX\s+(?!IF NOT EXISTS)',
                           lambda m: 'CREATE %sINDEX IF NOT EXISTS ' % (m.group(1) or ''),
                           sql.strip(), count=1).rstrip(';') + ';'
    return out


def ensure_indexes(dry=False):
    """Create on D1 every local index it does not hold. Returns (missing names, rc).

    THE INCREMENTAL PUSH NEVER SENT INDEXES, found 24 October 2026: a table rebuilt on the
    remote (`new`, `reshaped`, and now a staged swap) is DROPped, which drops its indexes,
    and nothing put them back -- D1 held 9 of the 12. A missing index does not change an
    answer, only what it costs: every query on that column becomes a full scan, and rows
    read are the billed unit. One read of the remote's index names; creates only what is
    missing, so a run that changed nothing writes nothing.
    """
    want = local_indexes()
    got = {str(list(x.values())[0]) for x in (_rows(
        "SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL") or [])
        if isinstance(x, dict)}
    missing = sorted(set(want) - got)
    if not missing or dry:
        return missing, 0
    r = wrangler('d1', 'execute', NAME, '--remote', '-y', '--command',
                 ' '.join(want[n] for n in missing))
    if r.returncode != 0:
        print('  index create failed:\n' + (r.stderr or r.stdout)[-800:])
        return missing, 1
    print('  indexes: created %d missing on D1 -- %s' % (len(missing), ', '.join(missing)))
    return missing, 0


def push_incremental(limit, dry=False):
    """Send only the tables whose digest differs. Returns (sent, deferred, rc)."""
    local = INC.local_state(DB)
    remote = remote_digests()
    if not remote:
        print('  D1 records no per-table digests yet, so every table counts as new.\n'
              '  This first run will take several days at the free tier; each one clears\n'
              '  what fits and names what is left.')
    deps = INC.parents(DB)
    send, drop, deferred, total = INC.plan(local, remote, limit, deps)
    for line in INC.describe(send, drop, deferred, total, limit):
        print('  ' + line)
    # A TABLE OVER THE CEILING IS SENT IN SLICES -- d1_incremental.plan_staged. Only when
    # one is deferred, so an ordinary push makes no extra request.
    staged = None
    if any(r > limit for _, _, r in deferred):
        stages = remote_stages()
        staged = INC.plan_staged(local, remote, stages, deferred, total, limit, deps)
        if staged:
            t, start, end, swap = staged
            print('  STAGED %s: rows %s-%s of %s%s' % (
                t, '{:,}'.format(start + 1), '{:,}'.format(end), '{:,}'.format(local[t][1]),
                ' -- complete, so it replaces the live table in this run' if swap
                else '; the next run continues from the remote\'s own count'))
            if swap:
                deferred = [d for d in deferred if d[0] != t]
    if dry or (not send and not drop and not staged):
        return len(send), len(deferred), 0
    sch = INC.schema(DB)
    sql = INC.batch_sql(local, send, drop, sch)
    if staged:
        t, start, end, swap = staged
        sql += '\n'.join(INC.stage_sql(local, t, start, end, restart=start == 0)) + '\n'
        if swap:
            sql += INC.batch_sql(local, [(t, 'swap', local[t][1])], [], sch)
    with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as fh:
        fh.write(sql)
        path = fh.name
    print('  sending %.1f MB' % (os.path.getsize(path) / 1e6))
    r = wrangler('d1', 'execute', NAME, '--remote', '--file', path, '-y')
    os.unlink(path)
    if r.returncode != 0:
        print('  push failed:\n' + (r.stderr or r.stdout)[-1200:])
        return len(send), len(deferred), 1
    return len(send), len(deferred), 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='compare row counts and fail on any difference')
    ap.add_argument('--force', action='store_true',
                    help='import even if this database has already been imported')
    ap.add_argument('--full', action='store_true',
                    help='replace EVERY table (needs ~2 rows of writes per row; the free '
                         'tier allows 100,000 a day and this database is past that)')
    ap.add_argument('--limit', type=int, default=40000,
                    help='most rows to send in one run (default 40,000)')
    ap.add_argument('--plan', action='store_true',
                    help='say what a push WOULD do, without touching the network')
    args = ap.parse_args()

    if not os.path.exists(DB):
        sys.exit('no database; run scripts/build_db.py first')

    if args.check:
        want, got, bad = compare()
        missing, _rc = ensure_indexes(dry=True)
        bad += ['index %s: local only' % n for n in missing]
        if bad:
            print(f'D1 disagrees with {DB} on {len(bad)} table(s) or index(es):')
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

    if args.plan:
        # OFFLINE ON PURPOSE. When the daily write budget is gone the honest question is
        # "is a push still owed, and how big is it" — and answering that by asking D1
        # spends a request against the thing you are already out of. Everything here is
        # read from the local database and the recorded sha of the last push.
        counts = local_counts()
        con = sqlite3.connect(DB)
        idx = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'"
                          ).fetchone()[0]
        due = here != last
        print('D1 push plan — nothing was sent, nothing was read from the network\n')
        print(f'  local database   {here[:12]}  {len(counts)} tables, {rows:,} rows')
        print(f'  last pushed      {(last[:12] or "never"):12}  '
              f'{"DIFFERENT — a push is owed" if due else "identical — nothing to push"}')
        print(f'  indexes          {idx}')
        # THE PLAN MUST DESCRIBE THE PUSH THAT WOULD ACTUALLY RUN, and it described a
        # different one. `--plan` printed the FULL-replace arithmetic -- `a full replace
        # writes ~154,054 rows` against a 100,000/day limit -- while a bare `sync_d1.py`
        # has been INCREMENTAL by default for weeks and sends only the tables whose digest
        # differs, capped at `--limit` (40,000).
        #
        # On 4 October 2026 two tables were behind by 97 rows in total, about 200 writes.
        # The plan made that look like a six-figure operation that could take /api/query
        # dark for the day, so it was not run -- a planner that overstates by three orders
        # of magnitude does not protect the budget, it protects the backlog.
        #
        # The incremental size is computed from the same per-table digests the push uses,
        # and the full-replace figure stays BELOW it, as the thing `--full` would do.
        # THE PLAN MUST DESCRIBE THE PUSH THAT WOULD ACTUALLY RUN, and it described a
        # different one. `--plan` printed the FULL-replace arithmetic -- `a full replace
        # writes ~154,054 rows` against a 100,000/day limit -- while a bare `sync_d1.py`
        # has been INCREMENTAL by default for weeks: only the tables whose digest differs,
        # capped at `--limit` (40,000).
        #
        # On 4 October 2026 two tables were behind by 97 rows in total, about 200 writes.
        # The plan made that look like a six-figure operation that could take /api/query
        # dark for the day, so it was not run -- a planner that overstates by three orders
        # of magnitude does not protect the budget, it protects the backlog.
        #
        # It stays OFFLINE, which is the whole point of `--plan`: the remote digests need
        # a request, so the local side is shown in full and the one unknown is NAMED
        # rather than guessed at. The full-replace figure stays, below, as what `--full`
        # would do.
        local_state = INC.local_state(DB)
        print(f'\n  WHAT A BARE `sync_d1.py` WOULD DO -- incremental, the DEFAULT:')
        print(f'    {len(local_state)} table(s) locally, {rows:,} rows in total')
        print(f'    it sends only the tables whose digest differs from the remote\'s, at')
        print(f'    most {40000:,} rows a run. Which tables that is needs ONE request to')
        print(f'    D1 for its recorded digests, so it is not computed here -- run')
        print(f'    `python3 scripts/sync_d1.py` and it names the tables and the row')
        print(f'    count BEFORE sending anything.')
        known = _last_tables()
        if known:
            new_t = sorted(set(counts) - set(known))
            print(f'    tables the published copy has never held: '
                  f'{len(new_t)}{" -- " + ", ".join(new_t) if new_t else ""}')
        print(f'\n  and `--full`, which is NOT the default:')
        print(f'  a full replace writes ~{rows:,} rows plus index maintenance.')
        print(f'  The free tier allows 100,000 writes a day. This database is larger than')
        print(f'  that, and the last full replace still succeeded, so the accounting is')
        print(f'  not simply rows x 2 — but it is the right order of magnitude and four')
        print(f'  re-imports in a day is what exhausted the budget on 5 September.')
        if due:
            known = _last_tables()
            new_t = sorted(set(counts) - set(known)) if known else []
            if not known:
                print('\n  (which tables the published copy holds is not recorded yet — '
                      'the next\n   push writes d1-pushed-tables.txt and this line gets '
                      'specific.)')
            if new_t:
                print(f'\n  tables NOT yet in the published copy: {", ".join(new_t)}')
                print(f'  Until this is pushed, anything querying the API for them gets')
                print(f'  "no such table" — including the schema page\'s own modal.')
            print(f'\n  When the budget resets:  python3 scripts/sync_d1.py')
        return 0

    if here == last and not args.force:
        _missing, rc = ensure_indexes()
        if rc:
            return rc
        print(f'nothing to do: D1 already holds this database ({here[:12]}).\n'
              f'  A full replace writes about {rows:,} rows against a free-tier limit of\n'
              f'  100,000 a day, so it is not run for a database that has not changed.\n'
              f'  Use --force if you believe the live copy has drifted, or --check to ask it.')
        return 0
    # INCREMENTAL BY DEFAULT, because a full replace no longer fits in a day. 153,414
    # rows is ~306,828 writes against a 100,000/day free tier, so the whole-database path
    # cannot complete however many times it is retried -- and a push route that only works
    # while the data barely changes is not a push route.
    if not args.full:
        print(f'incremental push — only tables whose digest differs are sent')
        sent, deferred, rc = push_incremental(args.limit)
        if rc:
            return rc
        _missing, rc = ensure_indexes()
        if rc:
            return rc
        # THE CONSISTENCY CHECK CANNOT RUN MID-CONVERGENCE, and must not be mistaken for
        # a failure when it does. compare() counts EVERY table, including ones this run
        # deliberately deferred -- and a COUNT over a table the remote does not have yet
        # errors, which killed an otherwise successful push after it had landed 100 tables.
        # A partial sync is the designed state while a backlog drains, so it reports what
        # is left and stops, rather than asking a question that has no answer yet.
        if deferred:
            print(f'\n{deferred} table(s) still to send; run again when the daily budget '
                  f'resets. The consistency check is skipped until then, because counting '
                  f'a table D1 does not hold yet errors rather than returning zero.')
            return 0
        want, got, bad = compare()
        if bad:
            print(f'\nFAIL: D1 still disagrees on {len(bad)} table(s):')
            for b in bad[:12]:
                print('  ' + b)
            return 1
        with open(PUSHED, 'w') as fh:
            fh.write(here + '\n')
        with open(PUSHED_TABLES, 'w') as fh:
            fh.write('\n'.join(sorted(want)) + '\n')
        print(f'ok: D1 matches — {len(want)} tables, {sum(want.values()):,} rows')
        return 0

    print(f'FULL replace: {rows:,} rows (~{rows * 2:,} writes with indexes) — the free tier '
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
    with open(PUSHED_TABLES, 'w') as fh:
        fh.write('\n'.join(sorted(want)) + '\n')
    print(f'ok: D1 matches — {len(want)} tables, {sum(want.values()):,} rows')
    return 0


if __name__ == '__main__':
    sys.exit(main())
