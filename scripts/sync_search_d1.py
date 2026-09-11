#!/usr/bin/env python3
"""Push the search index to D1, incrementally, inside the write budget.

    python3 scripts/sync_search_d1.py                # push what has changed
    python3 scripts/sync_search_d1.py --plan         # say what a push would do; send nothing
    python3 scripts/sync_search_d1.py --limit 60000  # stop after this many rows written
    python3 scripts/sync_search_d1.py --check        # fail if the two copies disagree

`sources/data/search-fts.db` is built by `build_search_index.py`. This is its live copy,
the database `lunenburg-search`, which `/api/search` reads. A second copy is a thing that
can disagree with the first, and `--check` is the whole reason this file is more than a
loop of INSERTs.

WHY IT IS INCREMENTAL WHEN `sync_d1.py` IS A FULL REPLACE

D1 on the Workers Free plan does not bill, it stops: **100,000 rows written a day, across
every database on the account.** The analysis database is 51,000 rows and is replaced
whole because that is simpler and fits. This index is 97,000 rows and does NOT fit beside
it -- a whole replace would take `/api/query` dark for the rest of the day -- and it grows
by a few hundred rows every time a transcript arrives. So it is pushed by FILE: the remote
keeps its own `indexed_file` table with a sha256 per file, this diffs the local one against
it, and only files that are new or changed are sent. A changed file is deleted remotely
and re-sent whole; a removed one is deleted.

The remote `indexed_file` is the remote's own claim about itself. It is read, never
assumed, and `--check` recounts every corpus on both sides rather than trusting it.

THE BUDGET IS ENFORCED HERE, NOT REMEMBERED

Every run estimates its writes before sending anything -- one per row, plus one per file
record, measured on 11 September 2026 at 1,002 for 1,000 rows -- and refuses past
`--limit` (default 90,000, leaving room for the day's other writes). A first load is
therefore two runs on two days, and that is the design: a file is recorded remotely only
after its rows are, so a run cut off by the limit or by the network leaves the remote
consistent and the next run picks up where it stopped.

Do not run `sync_d1.py` on the same day as a large run of this. The quota is shared.

WRANGLER'S SHAPE, WHICH DECIDES HOW THIS IS WRITTEN

`wrangler d1 execute --file` uploads the file and runs it in batches, but returns a
SUMMARY rather than rows, so anything that needs rows back goes through `--command`. Rows
are sent as `--file`, several hundred per INSERT, a few thousand per file; state is read
back with `--command` in pages.
"""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import build_search_index as B  # noqa: E402

APP = os.path.join(ROOT, 'fy28')
NAME = 'lunenburg-search'
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')

# D1 refuses a statement past about 100KB (`statement too long: SQLITE_TOOBIG`, hit on
# the first trial with 150 annual-report pages in one INSERT), so statements are sized by
# BYTES, not rows.
STATEMENT_BYTES = 80_000
INSERTS_PER_FILE = 120         # ~10MB of SQL per upload
DEFAULT_LIMIT = 90000


def wrangler(*args, timeout=3600):
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    return subprocess.run(['npx', 'wrangler', 'd1', 'execute', NAME, '--remote', *args],
                          cwd=APP, env=env, capture_output=True, text=True, timeout=timeout)


def command(sql):
    """Rows back from one statement. Fails loudly: an empty answer must not read as data."""
    r = wrangler('--json', '--command', sql)
    out = r.stdout
    i = out.find('[')
    if r.returncode != 0 or i < 0:
        raise SystemExit('wrangler failed:\n%s\n%s' % (r.stdout[-2000:], r.stderr[-2000:]))
    d = json.loads(out[i:])
    return d[0]['results'], d[0]['meta']


def run_file(path, attempts=4):
    """Upload and run one SQL file, retrying a dropped connection.

    A first full push died at 8,811 rows on `fetch failed` -- one lost request in an
    hour of them. The file is a batch of whole documents and D1 runs a file as a
    transaction, so re-sending it cannot double-insert: either the batch landed or it
    did not. A SQL error is not retried; that is a bug, not weather.
    """
    import time
    for i in range(attempts):
        r = wrangler('--file', path)
        if r.returncode == 0:
            return r.stdout
        text = r.stdout + r.stderr
        if 'fetch failed' in text or 'ECONNRESET' in text or 'ETIMEDOUT' in text:
            wait = 15 * (i + 1)
            print('  network error on upload; retrying in %ds (%d/%d)' % (wait, i + 1, attempts))
            time.sleep(wait)
            continue
        raise SystemExit('wrangler failed on %s:\n%s\n%s'
                         % (path, r.stdout[-2000:], r.stderr[-2000:]))
    raise SystemExit('gave up on %s after %d network failures' % (path, attempts))


def q(v):
    if v is None:
        return 'NULL'
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


# --------------------------------------------------------------------------- remote state

def ensure_schema():
    ddl = (B.SCHEMA.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ')
           + B.fts_ddl().replace('CREATE VIRTUAL TABLE', 'CREATE VIRTUAL TABLE IF NOT EXISTS') + ';')
    with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as fh:
        fh.write(ddl)
    run_file(fh.name)
    os.unlink(fh.name)


def remote_files():
    """Every file the remote says it holds, paged, with its sha256."""
    out, page = {}, 5000
    offset = 0
    while True:
        rows, _ = command('SELECT file_key, sha256, rows FROM indexed_file '
                          'ORDER BY file_key LIMIT %d OFFSET %d' % (page, offset))
        for r in rows:
            out[r['file_key']] = r
        if len(rows) < page:
            return out
        offset += page


def remote_counts():
    rows, _ = command('SELECT corpus, COUNT(*) n FROM search GROUP BY corpus')
    return {r['corpus']: r['n'] for r in rows}


# ------------------------------------------------------------------------------- the push

def plan(local):
    """(to_send, to_delete): file_keys, from the local index's own record of itself."""
    have = remote_files()
    want = {r['file_key']: dict(r) for r in local.execute('SELECT * FROM indexed_file')}
    to_delete = [k for k in have if k not in want or have[k]['sha256'] != want[k]['sha256']]
    to_send = [k for k in want if k not in have or have[k]['sha256'] != want[k]['sha256']]
    # Smallest corpora first, so a run cut off by the budget has sent the pages, the
    # posts and the documents whole and left only transcripts for tomorrow.
    order = {c: i for i, c in enumerate(('post', 'page', 'source', 'minutes', 'transcript'))}
    to_send.sort(key=lambda k: (order.get(want[k]['corpus'], 9), k))
    return want, have, to_send, to_delete


def push(limit, dry_run):
    local = sqlite3.connect(B.DB)
    local.row_factory = sqlite3.Row
    ensure_schema()
    want, have, to_send, to_delete = plan(local)
    rows_to_send = sum(want[k]['rows'] for k in to_send)
    print('remote holds %d file(s); local %d; %d to send (%d rows), %d to delete'
          % (len(have), len(want), len(to_send), rows_to_send, len(to_delete)))
    if dry_run:
        return 0
    written_aff = push_affinity(local)
    if not to_send and not to_delete:
        print('nothing to send; restating the remote counts')
        return record_counts(written_aff)

    # Deletions first, so a changed file is never present twice.
    if to_delete:
        with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as fh:
            for i in range(0, len(to_delete), 200):
                keys = ','.join(q(k) for k in to_delete[i:i + 200])
                fh.write('DELETE FROM search WHERE file_key IN (%s);\n' % keys)
                fh.write('DELETE FROM indexed_file WHERE file_key IN (%s);\n' % keys)
        run_file(fh.name)
        os.unlink(fh.name)
        print('deleted %d file(s) remotely' % len(to_delete))

    # Then inserts, file by file, in SQL files of a few thousand rows. A file's
    # indexed_file row is written in the SAME SQL file as its last rows, after them, so a
    # run that dies mid-way leaves files either wholly present or wholly absent.
    written, sent_files, batch, batch_rows, n_files = 0, 0, [], 0, 0
    cols = ','.join(B.COLS)

    def flush():
        nonlocal batch, batch_rows, n_files, written, sent_files
        if not batch:
            return
        with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as fh:
            fh.write('\n'.join(batch) + '\n')
        run_file(fh.name)
        os.unlink(fh.name)
        written += batch_rows
        sent_files += n_files
        print('  sent %d row(s) in %d file(s); %d rows written so far' % (batch_rows, n_files, written))
        batch, batch_rows, n_files = [], 0, 0

    stmts_in_batch = 0
    for k in to_send:
        f = want[k]
        if written + batch_rows + f['rows'] + 1 > limit:
            flush()
            print('STOPPED at the write limit (%d): %d file(s) remain; run again tomorrow'
                  % (limit, len(to_send) - sent_files))
            break
        rows = local.execute('SELECT %s FROM search WHERE file_key=?' % cols, (k,)).fetchall()
        vals, size = [], 0
        for r in rows:
            v = '(%s)' % ','.join(q(r[c]) for c in B.COLS)
            if vals and size + len(v) > STATEMENT_BYTES:
                batch.append('INSERT INTO search (%s) VALUES %s;' % (cols, ',\n'.join(vals)))
                stmts_in_batch += 1
                vals, size = [], 0
            vals.append(v)
            size += len(v) + 2
        if vals:
            batch.append('INSERT INTO search (%s) VALUES %s;' % (cols, ',\n'.join(vals)))
            stmts_in_batch += 1
        batch.append('INSERT OR REPLACE INTO indexed_file VALUES (%s,%s,%s,%s,%s);'
                     % (q(k), q(f['corpus']), q(f['sha256']), q(f['bytes']), q(f['rows'])))
        batch_rows += len(rows) + 1
        n_files += 1
        if stmts_in_batch >= INSERTS_PER_FILE:
            flush()
            stmts_in_batch = 0
    else:
        flush()
        built = local.execute("SELECT v FROM build_meta WHERE k='built'").fetchone()
        with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as fh:
            fh.write("INSERT OR REPLACE INTO build_meta VALUES ('built', %s);\n"
                     % q(built['v'] if built else ''))
            fh.write("INSERT OR REPLACE INTO build_meta VALUES ('tokenize', %s);\n" % q(B.TOKENIZE))
        run_file(fh.name)
        os.unlink(fh.name)
        print('complete: remote is current as of %s' % (built['v'] if built else '?'))
    return record_counts(written)


def push_affinity(local):
    """The affinity table, replaced whole: it is ~80 rows and it is curated, so a
    changed tag must land on the next run without anybody diffing it."""
    rows = local.execute('SELECT tags, doc_key, corpus, title, cite_url FROM affinity').fetchall()
    with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as fh:
        fh.write('DROP TABLE IF EXISTS affinity;\n')
        fh.write(B.AFFINITY_DDL + ';\n')
        for i in range(0, len(rows), 100):
            vals = ',\n'.join('(%s)' % ','.join(q(v) for v in r) for r in rows[i:i + 100])
            fh.write('INSERT INTO affinity (tags, doc_key, corpus, title, cite_url) VALUES %s;\n' % vals)
    run_file(fh.name)
    os.unlink(fh.name)
    print('affinity: %d row(s) replaced' % len(rows))
    return len(rows)


def record_counts(written):
    """What the remote now holds, per corpus, written INTO the remote.

    /api/search states its denominators from these rather than counting 97,000 rows on
    every call. One full read, once per push, on every run -- complete, cut off, or
    nothing to send -- so the figure is never older than the last change.
    """
    import datetime as dt
    rc = remote_counts()
    with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as fh:
        for c in ('post', 'page', 'source', 'minutes', 'transcript'):
            fh.write("INSERT OR REPLACE INTO build_meta VALUES ('rows:%s', %s);\n" % (c, q(str(rc.get(c, 0)))))
        fh.write("INSERT OR REPLACE INTO build_meta VALUES ('pushed', %s);\n"
                 % q(dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))
    run_file(fh.name)
    os.unlink(fh.name)
    print('%d row(s) written this run; remote holds %s'
          % (written, ', '.join('%s %d' % (c, n) for c, n in sorted(rc.items()))))
    return 0


def check():
    local = sqlite3.connect(B.DB)
    local.row_factory = sqlite3.Row
    lc = {r['corpus']: r['n'] for r in
          local.execute('SELECT corpus, COUNT(*) n FROM search GROUP BY corpus')}
    rc = remote_counts()
    bad = 0
    for c in sorted(set(lc) | set(rc)):
        flag = '' if lc.get(c, 0) == rc.get(c, 0) else '   <-- DIFFERS'
        bad += bool(flag)
        print('  %-12s local %8d   remote %8d%s' % (c, lc.get(c, 0), rc.get(c, 0), flag))
    if bad:
        print('FAIL: %d corpus(es) differ; run sync_search_d1.py' % bad)
        return 1
    print('ok: every corpus counts the same on both sides')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--limit', type=int, default=DEFAULT_LIMIT)
    a = ap.parse_args()
    if not os.path.exists(B.DB):
        raise SystemExit('no local index; run build_search_index.py first')
    if a.check:
        return check()
    return push(a.limit, a.plan)


if __name__ == '__main__':
    raise SystemExit(main())
