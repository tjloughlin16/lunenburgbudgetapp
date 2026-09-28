#!/usr/bin/env python3
"""PUSH ONLY THE TABLES THAT CHANGED. What makes the D1 copy reachable again.

WHY THIS HAD TO EXIST. `sync_d1.py` replaces the whole database: drop every table, load a
fresh dump. On 27 September 2026 that stopped being possible at all --

    importing 153,414 rows (~306,828 writes with indexes)
    the free tier allows 100,000 a day

-- so the published copy could not be brought up to date on that day, or any later day, by
any number of retries. The header of sync_d1.py said the database was "16MB and 50,000
rows" and that "a differential sync would be faster and would be one more thing that can be
subtly wrong". The first half went stale; the second half is still true and is why this file
is careful.

**The real cost is not the staleness, it is losing the ability to deploy.** TJ, 27 September
2026: *"We need to make the d1 sync work. I dont want to leave that sitting broken. Thats a
deployment issue and we can't react in an emergency."* A push path that only works when
nothing has changed much is not a push path.

HOW IT DECIDES WHAT TO SEND. A digest per table -- sha256 over that table's CREATE statement
and every INSERT the dump produces for it, in the dump's own order. The remote keeps its own
`synced_table` row per table, so the diff needs one small read rather than a comparison of
content. A table whose digest matches is not sent at all.

Row counts were the obvious alternative and are not enough: a corrected figure leaves the
count identical, which is exactly the class of drift `--check` exists to catch and would
have been invisible here.

TWO KINDS OF CHANGE, BECAUSE THEY NEED DIFFERENT SQL.

  * The CREATE is the same and only rows differ -> DELETE then INSERT. The table keeps its
    identity, so nothing referencing it has to be touched.
  * The CREATE differs, or the table is new -> DROP, CREATE, INSERT.

FOREIGN KEYS ARE WHY THE OLD ONE DROPPED EVERYTHING. This schema has real foreign keys and
D1 enforces them; the full replace hit `FOREIGN KEY constraint failed` and had to compute a
child-before-parent order. Emptying one table in the middle of that graph would hit the same
wall -- so every batch opens with

    PRAGMA defer_foreign_keys = true;

which holds enforcement until the transaction commits. `wrangler d1 execute --file` runs a
file as one transaction, so the end state is what gets checked, and a parent may be emptied
and refilled inside it. The constraints are still enforced -- just at the end, on the state
that will actually persist.

THE BUDGET IS A CEILING, NOT A HOPE. Each run sends whole tables while the running total of
rows stays under `--limit` (default 40,000, which leaves room for index maintenance inside
the free tier's 100,000 writes a day). What does not fit is named and waits for tomorrow, so
a large change converges over days instead of failing forever. Tables are taken smallest
first: it clears the most tables per run, and a table pushed is a table `/api/query` can
answer about.
"""
import hashlib
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYNC_TABLE = 'synced_table'
SYNC_SCHEMA = (
    'CREATE TABLE IF NOT EXISTS %s ('
    '  name TEXT PRIMARY KEY,'
    '  sha256 TEXT NOT NULL,'
    '  rows INTEGER NOT NULL'
    ')' % SYNC_TABLE
)


def _q(v):
    """A value as SQL. Mirrors what sqlite3's iterdump emits."""
    if v is None:
        return 'NULL'
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, bytes):
        return "X'%s'" % v.hex()
    return "'" + str(v).replace("'", "''") + "'"


def table_sql(db, table):
    """Every statement that recreates one table: its CREATE, then an INSERT per row.

    Taken from the live schema and the live rows rather than from `iterdump()`, because
    iterdump streams the WHOLE database and this needs one table at a time. The INSERT shape
    matches iterdump's so a digest computed here is comparable run to run.
    """
    create = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not create or not create[0]:
        return None, []
    cols = [r[1] for r in db.execute('PRAGMA table_info("%s")' % table)]
    collist = ', '.join('"%s"' % c for c in cols)
    inserts = []
    for row in db.execute('SELECT %s FROM "%s"' % (collist, table)):
        inserts.append('INSERT INTO "%s" (%s) VALUES (%s);'
                       % (table, collist, ', '.join(_q(v) for v in row)))
    return create[0].strip(), inserts


def digest(create, inserts):
    """sha256 of one table's whole content, CREATE included.

    The CREATE is in the digest on purpose: a column added with no row change must count as
    a change, or the remote keeps an old shape while reporting the right row count.
    """
    h = hashlib.sha256()
    h.update((create or '').encode())
    for s in inserts:
        h.update(b'\n')
        h.update(s.encode())
    return h.hexdigest()


def local_state(db_path):
    """{table: (sha256, rows, create, inserts)} for every table in the local database."""
    db = sqlite3.connect(db_path)
    out = {}
    for (t,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if t == SYNC_TABLE:
            continue          # bookkeeping about the push, never pushed content
        create, inserts = table_sql(db, t)
        out[t] = (digest(create, inserts), len(inserts), create, inserts)
    return out


def parents(db_path):
    """{table: {tables it references}} from the live schema, never hand-listed."""
    db = sqlite3.connect(db_path)
    out = {}
    for (t,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"):
        refs = {r[2] for r in db.execute('PRAGMA foreign_key_list("%s")' % t)}
        out[t] = {r for r in refs if r != t}
    return out


def plan(local, remote, limit, deps=None):
    """What to send, what to drop, and what does not fit in this run.

    Returns (send, drop, deferred). `send` is a list of (table, reason) with reason one of
    `new`, `reshaped` or `rows`; `deferred` is what a later run must still carry.
    """
    send, drop, deferred = [], [], []
    for t in sorted(local, key=lambda t: local[t][1]):     # smallest first
        sha, rows, create, _ = local[t]
        if t not in remote:
            reason = 'new'
        elif remote[t][0] == sha:
            continue
        elif remote[t][1] is not None and remote[t][1] != create:
            reason = 'reshaped'
        else:
            reason = 'rows'
        send.append((t, reason, rows))
    for t in sorted(remote):
        if t not in local and t != SYNC_TABLE:
            drop.append(t)
    # A PARENT MUST EXIST BEFORE ITS CHILDREN'S ROWS. `PRAGMA defer_foreign_keys` defers
    # CHECKING; it does not make a referenced table exist. Sorting purely by size put a
    # small child ahead of `document`, which it references, and D1 answered
    # `no such table: main.document` -- at INSERT, after the child had been created.
    #
    # So two constraints on top of the size order: a child is only eligible once every
    # parent is already on the remote or earlier in this same batch, and within the batch
    # parents are emitted first. Both are computed from the live schema, because a
    # hand-listed order is a thing that goes stale the next time a table is added.
    deps = deps or {}
    have = set(remote)
    kept, total, pending = [], 0, list(send)
    progress = True
    while pending and progress:
        progress = False
        still = []
        for t, reason, rows in pending:
            missing = {p for p in deps.get(t, ()) if p not in have}
            if missing:
                still.append((t, reason, rows))
                continue
            if total + rows > limit and kept:
                still.append((t, reason, rows))
                continue
            kept.append((t, reason, rows))
            have.add(t)
            total += rows
            progress = True
        pending = still
    deferred.extend(pending)
    return kept, drop, deferred, total


def batch_sql(local, send, drop):
    """One transaction's worth of SQL: defer the keys, then replace only what changed."""
    out = ['PRAGMA defer_foreign_keys = true;', SYNC_SCHEMA + ';']
    for t in drop:
        out.append('DROP TABLE IF EXISTS "%s";' % t)
        out.append('DELETE FROM %s WHERE name = %s;' % (SYNC_TABLE, _q(t)))
    for t, reason, _rows in send:
        sha, rows, create, inserts = local[t]
        if reason == 'rows':
            # Same shape: keep the table, replace its contents. Nothing referencing it is
            # touched, which is the whole point of splitting the two cases.
            out.append('DELETE FROM "%s";' % t)
        else:
            out.append('DROP TABLE IF EXISTS "%s";' % t)
            out.append(create.rstrip(';') + ';')
        out.extend(inserts)
        out.append('DELETE FROM %s WHERE name = %s;' % (SYNC_TABLE, _q(t)))
        out.append('INSERT INTO %s (name, sha256, rows) VALUES (%s, %s, %d);'
                   % (SYNC_TABLE, _q(t), _q(sha), rows))
    return '\n'.join(out) + '\n'


def parse_remote(rows):
    """{table: (sha256, rows_or_None, create_or_None)} from a synced_table read."""
    out = {}
    for r in rows or []:
        vals = list(r.values()) if isinstance(r, dict) else list(r)
        if len(vals) >= 3:
            out[str(vals[0])] = (str(vals[1]), None, None)
    return out


def describe(send, drop, deferred, total, limit):
    lines = []
    if not send and not drop:
        return ['nothing to send: every table matches the digest D1 recorded']
    if send:
        lines.append('%d table(s), %s row(s) — within the %s-row ceiling for one run:'
                     % (len(send), '{:,}'.format(total), '{:,}'.format(limit)))
        for t, reason, rows in send[:14]:
            lines.append('    %-40s %-9s %s row(s)' % (t, reason, '{:,}'.format(rows)))
        if len(send) > 14:
            lines.append('    ... and %d more' % (len(send) - 14))
    if drop:
        lines.append('%d table(s) gone locally, dropped remotely: %s'
                     % (len(drop), ', '.join(drop[:8])))
    if deferred:
        d = sum(r for _, _, r in deferred)
        lines.append('DEFERRED to a later run — %d table(s), %s row(s):'
                     % (len(deferred), '{:,}'.format(d)))
        for t, reason, rows in deferred[:8]:
            lines.append('    %-40s %-9s %s row(s)' % (t, reason, '{:,}'.format(rows)))
        lines.append('    Run again tomorrow; the ceiling is a day of the free tier.')
    return lines
