#!/usr/bin/env python3
"""HAS DESE CHANGED A DATASET SINCE WE TOOK OUR COPY? Asked of the portal, not of the bytes.

    python3 scripts/check_socrata_sources.py           # every socrata row of the registry

The datasets in sources/data/dese-source-registry.csv marked `socrata` live on
educationtocareer.data.mass.gov. Their exports are generated per download, so a sha256 of a
fresh export never matches the last one and says nothing about whether the data moved. The
portal states it directly: `rowsUpdatedAt` on /api/views/<id>.json is when the rows last
changed. So this asks for that -- one small request per dataset -- and compares it with when
we took our copy.

WHEN WE TOOK OUR COPY is the date of the commit that first recorded our copy's sha256 in the
registry. That is a ceiling, not the moment of download: a copy fetched on the 1st and
committed on the 8th reads as the 8th, so an update in between would be missed. It is the
only date the repository holds for it, and it is stated as what it is.

Why this exists: on 26 October 2026 a manual recheck found the circuit breaker dataset's rows
updated on 7 October, after our copy -- and FY2023's count of claimed students now withheld
as "less than 6", a count our pages still published. notes/plans/MONTHLY-SOURCE-REFRESH.md.

REPORTS, NEVER RE-DOWNLOADS. A changed dataset is a finding for a person: landing the new
copy goes through ingest and every generator reading it is re-run (rerun-everything-
downstream), which is not a thing to do unattended.

Writes sources/data/socrata-status.csv. Exit 0 when the check ran (changes are findings,
read off the file); 2 when the portal answered for none of them.
"""
import csv
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, 'sources', 'data', 'dese-source-registry.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'socrata-status.csv')
UA = ('Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; '
      '+https://lunenburgbudgetproject.org)')
FIELDS = ['name', 'dataset_id', 'local', 'our_copy', 'rows_updated', 'state', 'checked']


def our_copy_date(sha):
    """The first commit recording this sha in the registry, as YYYY-MM-DD, or ''."""
    if not sha:
        return ''
    r = subprocess.run(['git', 'log', '--format=%ad', '--date=short', '-S' + sha, '--',
                        os.path.relpath(REGISTRY, ROOT)],
                       cwd=ROOT, capture_output=True, text=True)
    days = r.stdout.split()
    return days[-1] if days else ''


def rows_updated(row):
    host = urllib.parse.urlsplit(row['api_endpoint'] or row['portal_page']).netloc
    url = 'https://%s/api/views/%s.json' % (host, row['dataset_id'])
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        meta = json.load(resp)
    ts = meta.get('rowsUpdatedAt') or meta.get('viewLastModified')
    return datetime.datetime.fromtimestamp(ts).date().isoformat() if ts else ''


def main():
    with open(REGISTRY, newline='', encoding='utf-8') as fh:
        rows = [r for r in csv.DictReader(fh) if r['source_kind'] == 'socrata']
    prev = {}
    if os.path.exists(OUT):
        with open(OUT, newline='', encoding='utf-8') as fh:
            prev = {r['dataset_id']: r for r in csv.DictReader(fh)}
    today = datetime.date.today().isoformat()
    out, answered = [], 0
    for n, r in enumerate(rows):
        if n:
            time.sleep(1)
        ours = our_copy_date(r['sha256'])
        try:
            upd = rows_updated(r)
            answered += 1
            if not upd or not ours:
                state = 'cannot compare'
            elif upd > ours:
                state = 'updated since our copy'
            else:
                state = 'current'
            checked = today
        except Exception as e:                       # noqa: BLE001 -- a host's bad minute
            # The last answer stands, dated when it was given; this run says it could not ask.
            old = prev.get(r['dataset_id'], {})
            upd, checked = old.get('rows_updated', ''), old.get('checked', '')
            state = 'unreachable'
            print('  unreachable  %s: %s' % (r['dataset_id'], str(e)[:120]))
        out.append(dict(name=r['name'], dataset_id=r['dataset_id'], local=r['local'],
                        our_copy=ours, rows_updated=upd, state=state, checked=checked))
        if state != 'current':
            print('  %-24s %s  (ours %s, rows %s)' % (state, r['name'][:50], ours or '?', upd or '?'))
    tmp = OUT + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(out)
    os.replace(tmp, OUT)
    moved = sum(1 for o in out if o['state'] == 'updated since our copy')
    print('%d datasets asked, %d answered, %d updated since our copy -> %s'
          % (len(rows), answered, moved, os.path.relpath(OUT, ROOT)))
    return 0 if answered else 2


if __name__ == '__main__':
    sys.exit(main())
