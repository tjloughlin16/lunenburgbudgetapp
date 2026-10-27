#!/usr/bin/env python3
"""What people searched for, pulled off the search log so the dashboard can show it.

    python3 scripts/pull_searches.py            # refresh build/search-log.csv (the last 90 days)
    python3 scripts/pull_searches.py --check    # does the file parse and hold together

TJ, 27 October 2026: "do we have logging on the search bar? We should have logging, and it
should feed into the backlog dashboard just like the questions do." It came out of a search
for an employee that showed nothing: the word had been corrected while an earlier search ran,
the corrected one never went, and nothing anywhere recorded either search.

WHERE IT COMES FROM. /api/search writes one row per search into `search_log` in the
`lunenburg-questions` D1 database (functions/api/search.js, logSearch; the table is
fy28/sql/search-log.sql). This reads it through wrangler, exactly as pull_questions.py reads
the questions.

THE WORDS ARE PULLED, AND THEY STAY OFF GIT. Unlike a question's body, a search's words are
the whole point of the log -- what people looked for and did not find is what tells us what
the archive is missing. But a search can be a person's name, so the file lives in build/,
which is gitignored, and is never published or committed. No IP address, user agent or
identifier exists in the log to pull.
"""
import argparse
import csv
import datetime as dt
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from pull_questions import query  # noqa: E402  -- one reader of that database, not two
OUT = os.path.join(ROOT, 'build', 'search-log.csv')
CHECKED = os.path.join(ROOT, 'build', 'search-log-checked.txt')
DB = 'lunenburg-questions'
DAYS = 90
FIELDS = ['at', 'q', 'board', 'since', 'sort', 'via', 'hits', 'ms', 'rows_read', 'cache', 'error', 'country']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    if a.check:
        if not os.path.exists(OUT):
            print('no search-log.csv yet — run without --check')
            return 0
        rows = list(csv.DictReader(open(OUT, encoding='utf-8')))
        bad = [r for r in rows if not r.get('at') or not r.get('q')]
        if bad:
            print('%d row(s) missing at or q' % len(bad), file=sys.stderr)
            return 1
        print('%d search(es), %d found nothing'
              % (len(rows), sum(1 for r in rows if r.get('hits') == '0')))
        return 0

    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS)).isoformat()
    rows = query("SELECT %s FROM search_log WHERE at >= '%s' ORDER BY at DESC"
                 % (', '.join(FIELDS), since[:19]))
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: '' if r.get(k) is None else r.get(k) for k in FIELDS})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + '.tmp'
    open(tmp, 'w', encoding='utf-8', newline='').write(s.getvalue())
    os.replace(tmp, OUT)
    # WHEN IT WAS CHECKED, not when the file changed -- the dashboard shows it beside the figures
    open(CHECKED, 'w').write(dt.datetime.now().astimezone().isoformat(timespec='seconds') + '\n')
    print('wrote %s — %d search(es) in %d days, %d found nothing'
          % (os.path.relpath(OUT, ROOT), len(rows), DAYS, sum(1 for r in rows if r.get('hits') == 0)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
