#!/usr/bin/env python3
"""Read and triage the question inbox.

    python3 scripts/questions.py                  # everything new
    python3 scripts/questions.py --all            # every status
    python3 scripts/questions.py --status spam
    python3 scripts/questions.py --set <id> answered --note "..." --url /what-sports-cost
    python3 scripts/questions.py --stats          # how full today is

WHY THIS IS A SCRIPT AND NOT A PAGE

A review queue on the public site is a second thing to secure, and the questions carry
optional email addresses. This reads the database directly through wrangler, which is
already authenticated as the account owner, so there is no new surface to protect.

WHAT IT WILL NOT SHOW YOU. The `source_hash` is a truncated hash of the caller's address
plus a salt, never the address. It is here to spot ONE source flooding, and it cannot be
turned back into a person. That is deliberate: a public budget site holding residents' IP
addresses would be a poor trade for a rate limit.
"""
import argparse
import json
import os
import subprocess
import sys

DB = 'lunenburg-questions'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FY28 = os.path.join(ROOT, 'fy28')


def sql(statement):
    """Run one statement against the remote database and return its rows."""
    out = subprocess.run(
        ['npx', 'wrangler', 'd1', 'execute', DB, '--remote', '--json',
         '--command', statement],
        cwd=FY28, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit('wrangler failed:\n' + (out.stderr or out.stdout))
    text = out.stdout[out.stdout.index('['):]          # wrangler prints a banner first
    return json.loads(text)[0]['results']


def show(rows):
    if not rows:
        print('  nothing')
        return
    for r in rows:
        print(f"\n  {r['asked_at'][:16].replace('T', ' ')}  [{r['status']}]  {r['id']}")
        if r.get('topic'):
            print(f"  topic: {r['topic']}", end='')
            print(f"   from: {r.get('country') or '?'}")
        for line in (r['body'] or '').splitlines():
            print(f"    {line}")
        if r.get('email'):
            print(f"  reply to: {r['email']}")
        if r.get('note'):
            print(f"  note: {r['note']}")
        if r.get('answered_url'):
            print(f"  answered at: {r['answered_url']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--status', default='new')
    ap.add_argument('--stats', action='store_true')
    ap.add_argument('--set', nargs=2, metavar=('ID', 'STATUS'))
    ap.add_argument('--note', default=None)
    ap.add_argument('--url', default=None)
    a = ap.parse_args()

    if a.set:
        qid, status = a.set
        if status not in ('new', 'reviewing', 'answered', 'declined', 'spam'):
            sys.exit(f'unknown status {status!r}')
        esc = lambda v: "NULL" if v is None else "'" + v.replace("'", "''") + "'"
        sql("UPDATE question SET status = %s, note = COALESCE(%s, note), "
            "answered_url = COALESCE(%s, answered_url) WHERE id = %s"
            % (esc(status), esc(a.note), esc(a.url), esc(qid)))
        print(f'{qid} -> {status}')
        return

    if a.stats:
        by = sql('SELECT status, COUNT(*) AS n FROM question GROUP BY status')
        today = sql("SELECT COUNT(*) AS n FROM question "
                    "WHERE substr(asked_at,1,10) = date('now')")[0]['n']
        srcs = sql("SELECT source_hash, COUNT(*) AS n FROM question "
                   "WHERE asked_at > datetime('now','-1 day') "
                   "GROUP BY source_hash ORDER BY n DESC LIMIT 5")
        print('by status:', {r['status']: r['n'] for r in by} or 'empty')
        print(f'accepted today: {today} of 300 (the endpoint refuses past that)')
        if srcs:
            print('busiest sources, last 24h:')
            for r in srcs:
                print(f"  {r['source_hash']}  {r['n']}")
        return

    where = '' if a.all else "WHERE status = '%s'" % a.status.replace("'", "''")
    show(sql('SELECT * FROM question %s ORDER BY asked_at DESC LIMIT 200' % where))


if __name__ == '__main__':
    main()
