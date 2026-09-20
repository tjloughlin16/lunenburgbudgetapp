#!/usr/bin/env python3
"""What readers have asked, pulled off the questions database so the dashboard can show it.

    python3 scripts/pull_questions.py            # refresh sources/data/reader-questions.csv
    python3 scripts/pull_questions.py --check    # does the file parse and hold together

TJ, 20 September 2026: "can you put the QUESTIONS (historical and open) from the site into
our dashboard (basically, the refresh loop should pull the questions and put them in the
dash)."

WHY IT HAS TO BE PULLED. `/ask-a-question` writes into its OWN D1 database,
`lunenburg-questions`, deliberately kept apart from the analysis database so a spam burst
cannot exhaust the write budget the public site runs on. Nothing on this machine reads it,
so a question could sit unanswered for a week with no sign of it anywhere a person looks.

NO BODIES, NO EMAIL ADDRESSES, NO SOURCE HASHES. A resident who writes to this project has
not published anything. The dashboard needs to know that a question arrived, when, on what
topic, and whether it is still open -- it does not need the words, and the words must not
land in a file that could be committed by accident. The body is reduced to its length.
`sources/data/reader-questions.csv` is gitignored for the same reason notes/feedback is.

COUNTS, NOT CONTENT, is also what makes this safe to run unattended in the refresh.
"""
import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'reader-questions.csv')
DB = 'lunenburg-questions'
FIELDS = ['id', 'asked_at', 'status', 'topic', 'body_chars', 'has_email', 'country']


def query(sql):
    """One read against the questions database, through wrangler.

    Node 22 is required by wrangler and the system node is 20, so the nvm shim is sourced
    the same way `fy28/` deploys do. A failure here is not fatal to the caller: the
    dashboard showing nothing is better than the refresh dying over a courtesy.
    """
    cmd = ('source ~/.nvm/nvm.sh >/dev/null 2>&1; nvm use 22 >/dev/null 2>&1; '
           'npx wrangler d1 execute %s --remote --json --command %s'
           % (DB, json.dumps(sql)))
    r = subprocess.run(['bash', '-lc', cmd], cwd=os.path.join(ROOT, 'fy28'),
                       capture_output=True, text=True)
    m = re.search(r'\[\s*\{.*\}\s*\]', r.stdout, re.S)
    if not m:
        raise SystemExit('could not read %s: %s' % (DB, (r.stderr or r.stdout)[-300:]))
    return json.loads(m.group())[0].get('results', [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    if a.check:
        if not os.path.exists(OUT):
            print('no reader-questions.csv yet — run without --check')
            return 0
        rows = list(csv.DictReader(open(OUT, encoding='utf-8')))
        bad = [r for r in rows if not r.get('asked_at') or not r.get('status')]
        if bad:
            print('%d row(s) missing asked_at or status' % len(bad), file=sys.stderr)
            return 1
        print('%d question(s), %d still open'
              % (len(rows), sum(1 for r in rows if r['status'] not in ('answered',))))
        return 0

    rows = query(
        "SELECT id, asked_at, status, topic, length(body) AS body_chars, "
        "CASE WHEN email IS NULL OR email='' THEN 0 ELSE 1 END AS has_email, country "
        "FROM question ORDER BY asked_at DESC")
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in FIELDS})
    open(OUT, 'w', encoding='utf-8', newline='').write(s.getvalue())
    opn = sum(1 for r in rows if (r.get('status') or '') != 'answered')
    print('wrote %s — %d question(s), %d open'
          % (os.path.relpath(OUT, ROOT), len(rows), opn))
    return 0


if __name__ == '__main__':
    sys.exit(main())
