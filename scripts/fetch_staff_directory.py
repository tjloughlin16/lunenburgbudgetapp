#!/usr/bin/env python3
"""The town's STAFF DIRECTORY, one page per department, fetched and catalogued.

    python3 scripts/fetch_staff_directory.py [--check]

Writes `sources/town-supplementary/docs/staff-directory/did-<N>.html` and appends a row
per page to `sources/town-supplementary/index.csv`.

TJ, 22 September 2026, on being shown the directory had been read but not ingested:
*"did you 'ingest' that page as a source? those 2 pages? So we have provenance."* It had
not been. The bytes were on disk with a note beside them and in no catalogue, which is
rule 12's own failure mode -- 43 primary documents in this archive have no address at all
because they were gathered before the catalogue existed and nobody wrote down where they
came from.

THE LANDING PAGE IS NOT THE SOURCE. `https://www.lunenburgma.gov/m/directory` renders only
the list of DEPARTMENTS into its HTML; the people sit behind a tab that needs a click, so
a headless fetch of that address returns no names at all. Each department has its own
address and those render fully, so the SOURCE is 28 pages rather than one:

    https://www.lunenburgma.gov/m/directory/department?did=<N>

The `did` is the town's own department identifier, which is what makes a later fetch
comparable with this one -- a department renamed keeps its number.

AND IT IS UNDATED. The directory carries no date, no fiscal year and no `as of`: it is
whoever the town is publishing on the day it was fetched. The fetch date is therefore the
only date this source has, and it belongs in the catalogue rather than in the file.
"""
import argparse
import csv
import datetime
import hashlib
import html
import io
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'town-supplementary', 'docs', 'staff-directory')
INDEX = os.path.join(ROOT, 'sources', 'town-supplementary', 'index.csv')
LANDING = 'https://www.lunenburgma.gov/m/directory'
PAGE = 'https://www.lunenburgma.gov/m/directory/department?did=%s'
FIELDS = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read']
UA = {'User-Agent': 'lunenburgbudgetproject.org (public records archive)'}


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def dids():
    """The department numbers, read off the directory's own links."""
    return sorted({int(d) for d in
                   re.findall(r'/m/directory/department\?did=(\d+)',
                              _get(LANDING).decode('utf-8', 'replace'))})


def department_of(blob):
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', blob.decode('utf-8', 'replace'),
               flags=re.S | re.I)
    rows = [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', s)).split('\n')
            if x.strip()]
    for i, t in enumerate(rows[:60]):
        if t.lower() == 'directory' and i + 1 < len(rows):
            return rows[i + 1].strip()
    return ''


def catalogue(rows):
    """Append to the shared index, preserving what is already in it.

    A generated file with several authors gets CLOBBERED, not merged -- `money-gaps.csv`
    was rewritten whole twice in one day. So: re-read immediately before writing, append
    only what is not already there, and keep the file's own newline convention.
    """
    raw = open(INDEX, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    have = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    known = {r['local'] for r in have}
    added = [r for r in rows if r['local'] not in known]
    if not added:
        return 0
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=FIELDS, lineterminator=nl)
    w.writeheader()
    w.writerows(have + added)
    open(INDEX, 'wb').write(out.getvalue().encode('utf-8'))
    return len(added)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='every held page is catalogued and its sha256 still matches')
    a = ap.parse_args()
    today = datetime.date.today().isoformat()

    if a.check:
        have = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
        bad = []
        for f in sorted(os.listdir(DOCS)):
            if not f.endswith('.html'):
                continue
            rel = os.path.relpath(os.path.join(DOCS, f), ROOT)
            row = have.get(rel)
            if not row:
                bad.append('%s is on disk and in no catalogue' % rel)
                continue
            got = hashlib.sha256(open(os.path.join(DOCS, f), 'rb').read()).hexdigest()
            if got != row['sha256']:
                bad.append('%s has changed since it was catalogued' % rel)
        for b in bad:
            print(b)
        return 1 if bad else 0

    os.makedirs(DOCS, exist_ok=True)
    rows = []
    for did in dids():
        blob = _get(PAGE % did)
        path = os.path.join(DOCS, 'did-%d.html' % did)
        open(path, 'wb').write(blob)
        name = department_of(blob) or 'department %d' % did
        rows.append(dict(
            label='%s (staff directory, fetched %s)' % (name, today),
            upstream=PAGE % did,
            local=os.path.relpath(path, ROOT), text='',
            bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(), read=''))
    n = catalogue(rows)
    print('%d department pages held; %d newly catalogued in %s'
          % (len(rows), n, os.path.relpath(INDEX, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
