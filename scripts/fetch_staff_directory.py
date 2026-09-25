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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot_log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'town-supplementary', 'docs', 'staff-directory')

# EVERY FETCH IS KEPT, IN A FOLDER NAMED FOR ITS DAY. TJ: *"staff directory will be
# updated every year -- it has no historical lens so WE have to keep it."*
#
# That is the whole reason this is in an archive rather than a cache. The town overwrites
# its directory in place: there is no FY2026 version of it anywhere, and the day somebody
# updates a page the person who held that job before is gone from the internet. A fetcher
# that writes `did-6.html` and overwrites it next year would destroy exactly the record
# it exists to keep -- and it would do it silently, which is worse.
#
# So the path carries the date, the catalogue carries the date, and the extractor reads
# EVERY snapshot rather than the newest. Nothing is ever written over.
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
    ap.add_argument('--if-changed', action='store_true',
                    help='keep a snapshot only when the pages differ from the last one '
                         '(what the scheduled run uses); the check is logged either way')
    a = ap.parse_args()
    today = datetime.date.today().isoformat()

    if a.check:
        have = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
        bad = []
        held = [os.path.join(dp, f) for dp, _d, fs in os.walk(DOCS)
                for f in fs if f.endswith('.html')]
        for full in sorted(held):
            rel = os.path.relpath(full, ROOT)
            row = have.get(rel)
            if not row:
                bad.append('%s is on disk and in no catalogue' % rel)
                continue
            got = hashlib.sha256(open(full, 'rb').read()).hexdigest()
            if got != row['sha256']:
                bad.append('%s has changed since it was catalogued' % rel)
        for b in bad:
            print(b)
        return 1 if bad else 0

    os.makedirs(DOCS, exist_ok=True)

    # EVERY PAGE IS FETCHED BEFORE ANY IS KEPT, so a run that dies partway leaves no
    # half-snapshot -- and so `--if-changed` can compare the whole set rather than
    # deciding one page at a time, which would keep 27 pages to record one edit.
    #
    # THIS PAGE IS BYTE-REPRODUCIBLE, unlike the district's sheets: the town's directory
    # returns the same bytes on consecutive requests, so the comparison is the strict one
    # and needs no `only=`. Checked before relying on it, because the district's pages
    # looked the same way and are not.
    # ONE LISTING OF THE DEPARTMENTS, NOT TWO. `dids()` fetches the landing page, and
    # calling it again for the write loop asked the town for it twice per run.
    numbers = dids()
    pages = {'did-%d.html' % did: _get(PAGE % did) for did in numbers}
    if a.if_changed:
        last, same = snapshot_log.same_as_latest(DOCS, pages)
        if same:
            snapshot_log.record(DOCS, today, False, snapshot=last, files=len(pages),
                                note='identical to %s; nothing written' % last)
            print('unchanged since %s -- no snapshot written; logged in checked.csv' % last)
            return 0
    snapshot_log.record(DOCS, today, True, snapshot=today, files=len(pages),
                        note='snapshot written')

    rows = []
    for did in numbers:
        blob = pages['did-%d.html' % did]
        day = os.path.join(DOCS, today)
        os.makedirs(day, exist_ok=True)
        path = os.path.join(day, 'did-%d.html' % did)
        # A SNAPSHOT IS NEVER OVERWRITTEN, not even by a second run on the same day --
        # the town may have changed a page between them, and the first bytes are the ones
        # the catalogue already carries a sha256 for.
        if os.path.exists(path):
            print('  %s already held; left alone' % os.path.relpath(path, ROOT))
        else:
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
