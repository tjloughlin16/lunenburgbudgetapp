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
a large change converges over days instead of failing forever. A single table bigger than
the ceiling is loaded in slices instead -- see plan_staged. Tables are taken smallest
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
        elif remote[t][1] is None or remote[t][1] != create:
            # AN UNKNOWN SHAPE IS NOT THE SAME SHAPE. Where the remote never recorded a
            # table's CREATE, this used to assume it matched and send `rows` -- a DELETE and
            # INSERTs into the OLD table. 9 October 2026: special_revenue_funds had gained
            # `fund_balance` locally and the push died on `no column named fund_balance`.
            # Rebuilding costs the same writes as replacing every row, which `rows` does.
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
        # A PARENT BEING RESENT IS NOT YET THERE. `have` starts as every table the remote
        # holds, so a child whose parent is ALSO in this push was eligible at once and, being
        # smaller, went first -- ahead of the parent rows it points at. 9 October 2026: the
        # trial-balance tables (17 and 102 rows) went ahead of `document` (2,595 rows, 1,175
        # of them new to D1) and every push failed SQLITE_CONSTRAINT_FOREIGNKEY. Deferring
        # the check did not save it, so the hypothesis below does not hold for D1 and the
        # order must. A parent waiting in this push blocks its children until it is kept.
        waiting = {x for x, _, _ in pending}
        for t, reason, rows in pending:
            missing = {p for p in deps.get(t, ()) if p not in have or p in waiting}
            if missing:
                still.append((t, reason, rows))
                continue
            # OVER THE CEILING ON ITS OWN -> plan_staged sends it in slices. It used to go
            # whole on a run where nothing smaller was owed, which with a daily refresh
            # changing small tables every morning is a run that may never come.
            if rows > limit or (total + rows > limit and kept):
                still.append((t, reason, rows))
                continue
            kept.append((t, reason, rows))
            have.add(t)
            waiting.discard(t)
            total += rows
            progress = True
        pending = still
    deferred.extend(pending)
    return kept, drop, deferred, total


def schema(db_path):
    """{table: (pk columns, [(child, child cols, parent cols)])} from the live schema."""
    db = sqlite3.connect(db_path)
    out = {}
    names = [t for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                       "AND name NOT LIKE 'sqlite_%'")]
    for t in names:
        pk = [r[1] for r in sorted(db.execute('PRAGMA table_info("%s")' % t), key=lambda r: r[5]) if r[5]]
        out[t] = (pk, [])
    for c in names:
        fks = {}
        for r in db.execute('PRAGMA foreign_key_list("%s")' % c):
            fks.setdefault(r[0], (r[2], [], []))
            fks[r[0]][1].append(r[3])
            fks[r[0]][2].append(r[4])
        for parent, ccols, pcols in fks.values():
            if parent in out and parent != c:
                out[parent][1].append((c, ccols, pcols))
    return out


def _cols(cs):
    return ', '.join('"%s"' % c for c in cs)


def _tuple(cs, alias=''):
    cs = ['%s"%s"' % (alias, c) for c in cs]
    return cs[0] if len(cs) == 1 else '(%s)' % ', '.join(cs)


def _prune_children(sch, table, doomed, out, touched, depth=0):
    """DELETE every row, at any depth, that references a row of `table` matched by `doomed`
    (a SELECT of `table`'s rows that are about to go), deepest first."""
    if depth > 8:
        raise SystemExit('foreign keys nest deeper than 8 below %s; refusing' % table)
    for child, ccols, pcols in sch.get(table, ((), []))[1]:
        hit = '%s IN (SELECT %s FROM "%s" WHERE %s)' % (_tuple(ccols), _cols(pcols), table, doomed)
        _prune_children(sch, child, hit, out, touched, depth + 1)
        out.append('DELETE FROM "%s" WHERE %s;' % (child, hit))
        touched.add(child)


def _descendants(sch, table, depth=0):
    """Every table referencing `table`, at any depth, deepest first."""
    if depth > 8:
        raise SystemExit('foreign keys nest deeper than 8 below %s; refusing' % table)
    out = []
    for child, _c, _p in sch.get(table, ((), []))[1]:
        for d in _descendants(sch, child, depth + 1) + [child]:
            if d not in out:
                out.append(d)
    return out


def batch_sql(local, send, drop, sch=None):
    """One transaction's worth of SQL: defer the keys, then replace only what changed.

    A PARENT IS UPSERTED, NEVER EMPTIED -- the fix for the failure described below, chosen
    10 October 2026. For a same-shape table that other tables reference: every local row
    goes in as INSERT ... ON CONFLICT(pk) DO UPDATE, so no row a child points at is ever
    missing, in any batch. Rows removed locally are then removed remotely, matched against a
    scratch table of the local keys (no read of the remote's keys, so no rows-read cost),
    and only after every remote row referencing them -- at any depth -- has gone first. A
    child pruned that way has its synced_table row cleared, so the next push resends it
    whole instead of trusting a digest that no longer describes the remote.

    WHAT IT USED TO DO, AND WHY THAT FAILED. On 4 October
    2026 a 14-table, 12,846-row incremental push failed outright:

        FOREIGN KEY constraint failed: SQLITE_CONSTRAINT_FOREIGNKEY

    `PRAGMA defer_foreign_keys` is emitted first and is TRANSACTION-SCOPED. A HYPOTHESIS,
    and the only one that fits: `wrangler d1 execute --file` runs the file in BATCHES --
    sync_d1.py's own header says so -- so each batch is its own transaction and the pragma
    covers the first one only. `DELETE FROM "document";` then runs with keys enforced while
    tables NOT in this batch still reference its rows, and the whole push is refused.

    Nothing partial landed -- /api/query answered in 22ms afterwards -- so the live copy is
    intact and merely a few tables behind. It is availability that is at risk here, never
    correctness.

    WHAT WOULD FIX IT, none of them a one-liner, and the choice is a real decision:

      * `INSERT OR REPLACE` instead of `DELETE` + `INSERT` for a same-shape table, so no
        row is ever deleted and no child is ever orphaned. Cheapest, and WRONG where a row
        was removed locally: the remote keeps it for ever.
      * Send a parent and every table referencing it in ONE batch, so the deletes and the
        reinserts are always in the same transaction. Correct, and it makes the batch as
        large as the subgraph -- `document` has many children, which is how a 97-row lag
        became a 12,846-row push in the first place.
      * Delete only the keys that are actually going away, computed by diffing local
        against remote. Correct and minimal, and it needs a read of the remote's keys,
        which is rows-read against the daily budget.

    The upsert is the first with the third's correctness, and it needs no remote read. Do not
    reach for `PRAGMA foreign_keys = OFF`: it is connection-scoped, D1 gives no guarantee
    about the connection between batches, and a push that silently breaks referential
    integrity is worse than one that refuses.
    """
    out = ['PRAGMA defer_foreign_keys = true;', SYNC_SCHEMA + ';']
    sch = sch or {}
    stale_children = set()
    for t in drop:
        out.append('DROP TABLE IF EXISTS "%s";' % t)
        out.append('DELETE FROM %s WHERE name = %s;' % (SYNC_TABLE, _q(t)))
    for t, reason, _rows in send:
        sha, rows, create, inserts = local[t]
        pk, children = sch.get(t, ([], []))
        if reason == 'rows' and children and pk:
            out.extend(_upsert_parent(t, pk, children, create, inserts, sch, stale_children))
            out.append('DELETE FROM %s WHERE name = %s;' % (SYNC_TABLE, _q(t)))
            out.append('INSERT INTO %s (name, sha256, rows) VALUES (%s, %s, %d);'
                       % (SYNC_TABLE, _q(t), _q(sha), rows))
            continue
        # A RESHAPED PARENT TAKES ITS CHILDREN WITH IT. 13 October 2026: `document` gained a
        # column, so it was dropped and rebuilt -- and `ledger_snapshot` and `crosswalk`, not
        # in the push, still pointed at its rows. D1 enforced the key at the DROP (the
        # deferral does not span the import's batches, as above) and rolled everything back,
        # four times. So: empty every descendant NOT already in this push (deepest first),
        # rebuild the parent, then reload those descendants whole (parents first), all here.
        # The children are usually small; `document`'s two were 11 rows between them.
        # A descendant that IS in this push still holds its OLD rows on the remote until its
        # own block runs, later -- so it is cleared here too (the second failure the same day:
        # the trial-balance tables were in the push, after `document`, and still orphaned).
        # DROP IF EXISTS, not DELETE: a table new to the remote may not be there to empty.
        tail_reload = []
        if reason != 'rows' and children:
            how = {x: r for x, r, _ in send}
            desc = _descendants(sch, t)
            for c in desc:
                if how.get(c) == 'rows':
                    out.append('DELETE FROM "%s";' % c)
                else:
                    out.append('DROP TABLE IF EXISTS "%s";' % c)
            tail_reload = [c for c in reversed(desc) if c not in how and c in local]
        if reason == 'rows':
            # Same shape, and nothing references it: keep the table, replace its contents.
            out.append('DELETE FROM "%s";' % t)
            out.extend(inserts)
        elif reason == 'swap':
            # A STAGED TABLE, WHOLE ON THE REMOTE UNDER ITS STAGING NAME (see stage_sql):
            # the live table is replaced by a rename, so its rows are not sent again.
            out.append('DROP TABLE IF EXISTS "%s";' % t)
            # LEGACY RENAME, because the modern one re-parses every VIEW in the schema and
            # refuses if any names a table missing at that instant -- and the children of a
            # parent are exactly that, dropped above and reloaded below (found in the local
            # test: `v_revenue_classified` names `ledger_snapshot`).
            out.append('PRAGMA legacy_alter_table = ON;')
            out.append('ALTER TABLE "%s" RENAME TO "%s";' % (stage_name(t), t))
            out.append('PRAGMA legacy_alter_table = OFF;')
            out.append('DELETE FROM %s WHERE name = %s;' % (STAGE_TABLE, _q(t)))
        else:
            out.append('DROP TABLE IF EXISTS "%s";' % t)
            out.append(create.rstrip(';') + ';')
            out.extend(inserts)
        out.append('DELETE FROM %s WHERE name = %s;' % (SYNC_TABLE, _q(t)))
        out.append('INSERT INTO %s (name, sha256, rows) VALUES (%s, %s, %d);'
                   % (SYNC_TABLE, _q(t), _q(sha), rows))
        for c in tail_reload:
            csha, crows, ccreate, cinserts = local[c]
            out.append('DROP TABLE IF EXISTS "%s";' % c)
            out.append(ccreate.rstrip(';') + ';')
            out.extend(cinserts)
            out.append('DELETE FROM %s WHERE name = %s;' % (SYNC_TABLE, _q(c)))
            out.append('INSERT INTO %s (name, sha256, rows) VALUES (%s, %s, %d);'
                       % (SYNC_TABLE, _q(c), _q(csha), crows))
    sent = {t for t, _, _ in send}
    for c in sorted(stale_children - sent):
        out.append('DELETE FROM %s WHERE name = %s;' % (SYNC_TABLE, _q(c)))
    return '\n'.join(out) + '\n'


KEEP = '_sync_keep'
KEEP_CHUNK = 400          # keys per INSERT: well under D1's ~100 KB statement limit


def _upsert_parent(t, pk, children, create, inserts, sch, stale_children):
    cols = _insert_cols(inserts[0]) if inserts else list(pk)     # an emptied parent: every row goes
    upd = [c for c in cols if c not in pk]
    tail = (' ON CONFLICT(%s) DO UPDATE SET %s;' % (_cols(pk), ', '.join('"%s" = excluded."%s"' % (c, c) for c in upd))
            if upd else ' ON CONFLICT(%s) DO NOTHING;' % _cols(pk))
    out = ['DROP TABLE IF EXISTS "%s";' % KEEP,
           'CREATE TABLE "%s" (%s);' % (KEEP, ', '.join('"%s"' % c for c in pk))]
    idx = [cols.index(c) for c in pk]
    keys = [[_values(s)[i] for i in idx] for s in inserts]
    for i in range(0, len(keys), KEEP_CHUNK):
        out.append('INSERT INTO "%s" (%s) VALUES %s;' % (
            KEEP, _cols(pk), ', '.join('(%s)' % ', '.join(k) for k in keys[i:i + KEEP_CHUNK])))
    doomed = '%s NOT IN (SELECT %s FROM "%s")' % (_tuple(pk), _cols(pk), KEEP)
    touched = set()
    _prune_children(sch, t, doomed, out, touched)
    stale_children.update(touched)
    out.append('DELETE FROM "%s" WHERE %s;' % (t, doomed))
    out.extend(s.rstrip().rstrip(';') + tail for s in inserts)
    out.append('DROP TABLE "%s";' % KEEP)
    return out


def _insert_cols(stmt):
    """The column list of one INSERT that table_sql() wrote."""
    m = re.match(r'INSERT INTO "[^"]+" \(([^)]*)\) VALUES', stmt)
    return [c.strip().strip('"') for c in m.group(1).split(',')]


def _values(stmt):
    """The literal values of one INSERT that table_sql() wrote, as SQL text, in order.
    A tokenizer, not a split on commas: a quoted string may hold commas and doubled quotes."""
    body = stmt[stmt.index(') VALUES (') + len(') VALUES ('):].rstrip().rstrip(';')[:-1]
    out, cur, q, i = [], '', False, 0
    while i < len(body):
        ch = body[i]
        if q:
            cur += ch
            if ch == "'":
                if i + 1 < len(body) and body[i + 1] == "'":
                    cur += "'"
                    i += 1
                else:
                    q = False
        elif ch == "'":
            q, cur = True, cur + ch
        elif ch == ',':
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
        i += 1
    out.append(cur.strip())
    return out


# A TABLE LARGER THAN THE CEILING IS LOADED IN PIECES, NEVER LEFT BEHIND. TJ, 24 October
# 2026: *"'never sent at all' can never be a thing."* It was: plan() sends WHOLE tables
# under --limit, so the school journal (49,043 rows) waited behind a 40,000 ceiling every
# run, for ever, and /api/query answered "no such table" until somebody raised the limit
# by hand.
#
# So a table over the ceiling goes to the remote under a STAGING NAME, a slice a run, and
# the live table is replaced only once the staged copy is whole -- by a rename, inside the
# usual batch, so a reader never sees half of it. Three things make that safe:
#
#   * WHICH ROWS ARE LOADED IS COUNTED ON THE REMOTE, NOT REMEMBERED. The resume point is
#     COUNT(*) of the staging table. `wrangler --file` applies a file in batches, so a run
#     that fails part-way leaves a PREFIX of the slice behind, and counting it resumes from
#     exactly there. A counter written at the end of the file would be wrong after that.
#   * THE STAGE IS TIED TO A DIGEST. If the table changes while it is being loaded, the
#     slices already sent describe the old table, so the stage is dropped and starts again.
#     A table that changes more often than it can be loaded never converges, and describe()
#     says so rather than pretending.
#   * EACH RUN GIVES IT AT LEAST HALF THE CEILING, whatever the small tables took, so it
#     always advances. A run may therefore send up to 1.5x --limit.
STAGE_TABLE = 'synced_stage'
STAGE_SCHEMA = ('CREATE TABLE IF NOT EXISTS %s (name TEXT PRIMARY KEY, sha256 TEXT NOT NULL)'
                % STAGE_TABLE)
STAGE_PREFIX = '_stage__'


def stage_name(t):
    return STAGE_PREFIX + t


def plan_staged(local, remote, stages, deferred, total, limit, deps=None):
    """Pick up to one over-ceiling table from `deferred` and the slice of it to send now.

    `stages` is {table: (sha256, rows already on the remote)}. Returns
    (table, start, end, swap) or None. `swap` is True when this slice completes it.
    """
    deps = deps or {}
    waiting = {t for t, _, _ in deferred}
    for t, reason, rows in sorted(deferred, key=lambda x: x[2]):
        if rows <= limit:
            continue                    # fits whole; an ordinary later run sends it
        if any(p not in remote or p in waiting for p in deps.get(t, ())):
            continue                    # a parent must be on the remote first
        sha = local[t][0]
        start = stages[t][1] if t in stages and stages[t][0] == sha else 0
        budget = max(limit - total, limit // 2)
        end = min(rows, start + budget)
        return t, start, end, end == rows
    return None


def stage_sql(local, t, start, end, restart):
    """Statements that add rows [start, end) of `t` to its staging table on the remote."""
    sha, _rows, create, inserts = local[t]
    st = stage_name(t)
    out = [STAGE_SCHEMA + ';']
    if restart:
        out.append('DROP TABLE IF EXISTS "%s";' % st)
        # The local CREATE, renamed. The rename at swap time renames it back, so the live
        # table ends up with exactly the schema the local one has.
        out.append(re.sub(r'^CREATE TABLE\s+(?:"[^"]+"|\S+)', 'CREATE TABLE "%s"' % st,
                          create.rstrip(';'), count=1) + ';')
        out.append('DELETE FROM %s WHERE name = %s;' % (STAGE_TABLE, _q(t)))
        out.append('INSERT INTO %s (name, sha256) VALUES (%s, %s);'
                   % (STAGE_TABLE, _q(t), _q(sha)))
    head = 'INSERT INTO "%s" (' % t
    for stmt in inserts[start:end]:
        assert stmt.startswith(head), stmt[:80]
        out.append('INSERT INTO "%s" (' % st + stmt[len(head):])
    return out


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
        lines.append('    The next run carries what is left.')
    return lines
