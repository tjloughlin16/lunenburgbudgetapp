#!/usr/bin/env python3
"""WHO WORKS FOR THE DISTRICT, from the sheets the schools publish themselves.

    python3 scripts/fetch_school_staff_directory.py [--check]

Writes `sources/district-budget/docs/personnel/staff-directory/<YYYY-MM-DD>/` and appends
a row per sheet to `sources/district-budget/index.csv`.

TJ gave seven addresses on 24-25 September 2026: the district's own directory page, the
roll-up sheet of every employee, and the five listings the District Office and the four
schools each keep. This is the first source in this archive covering the DISTRICT'S people
from outside an annual report -- every other people-source here is read out of one, which
is why a body that files no report is invisible in `/org-charts`.

**TJ's reason for the per-school ones, in his words:** *"the reason the individual matters
is to show 'shared' resources across school, and sometimes there's more details."*

THE FIVE ARE NEVER MERGED, AND THAT IS THE WHOLE POINT. A person printed on two schools'
own listings IS the finding -- a shared specialist, counted once by the district and twice
by the buildings. Deduplicating on the way in destroys the only thing these addresses were
given for. So the grain of what this writes is A PERSON AS ONE LISTING PRINTS THEM, and
every row says which listing it came from. `extract_school_staff_directory.py` computes
the overlap afterwards, from rows that kept their source.

THE LANDING PAGE IS NOT THE SOURCE -- BUT IT IS WHERE THE SOURCES ARE NAMED. The district
page holds one anchor per listing and the anchor's own TEXT is the school's name
(`Turkey Hill Elementary School`, `District Office`). So the labels in this archive are
the publisher's rather than ours, a sheet added for a sixth building appears here without
anybody editing this file, and a sheet that is withdrawn stops appearing. Nothing about
which sheets exist is typed into this script. That is the same shape
`fetch_staff_directory.py` uses for the town's `did=N` pages, for the same reason.

AND IT IS UNDATED, WHICH IS WHY EVERY FETCH IS KEPT. A published Google Sheet is
overwritten in place: it carries today and no history, and the day somebody edits it the
person who held that job before is gone from the internet. There is no FY2026 version of
any of these anywhere. So the path carries the date, the catalogue carries the date, and
nothing is ever written over -- the archive is the only record of this that will exist.

BOTH THE PAGE AND THE ROWS ARE KEPT, per rule 12: the published HTML is what a resident
sees, and the CSV export is what our figures are computed from. Five of the six export
cleanly; the sixth is a `/edit` address rather than a published one and is fetched through
`/export?format=csv`, which works only while the sheet stays link-readable -- recorded in
the catalogue as the weaker address it is.
"""
import argparse
import csv
import datetime
import hashlib
import html
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot_log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'district-budget', 'docs', 'personnel',
                    'staff-directory')
INDEX = os.path.join(ROOT, 'sources', 'district-budget', 'index.csv')
LANDING = 'https://www.lunenburgschools.net/contact'
UA = {'User-Agent': 'lunenburgbudgetproject.org (public records archive)'}
FIELDS = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read',
          'page', 'school_year', 'meeting_date']


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def slug(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')


def listings(blob):
    """The sheets, and the district's own name for each, off the landing page's anchors.

    Returns [(name, url)] in the order the page prints them -- the roll-up first, because
    that is how the district lays the page out, and the order is information: the page
    calls the first one the full directory and the rest `Individual School Directories`.
    """
    s = html.unescape(blob.decode('utf-8', 'replace'))
    out, seen = [], set()
    for m in re.finditer(r'<a\b[^>]*href="([^"]*docs\.google\.com/spreadsheets[^"]*)"'
                         r'[^>]*>(.*?)</a>', s, re.S | re.I):
        url = m.group(1)
        name = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(2))).strip()
        if not name or url in seen:
            continue
        seen.add(url)
        out.append((name, url))
    return out


def csv_address(url):
    """The rows behind a sheet, as an address rather than a scrape.

    A published sheet answers `pub?...&output=csv`; its `pubhtml` renders the grid in
    JavaScript and holds no `<table>` at all, so the HTML a fetcher gets back carries the
    title and none of the people. An unpublished sheet shared by link answers
    `/export?format=csv`. Which of the two a listing is is a fact about how the district
    published it, so it is read off the address rather than assumed.
    """
    m = re.search(r'/spreadsheets/d/(e/2PACX-[\w-]+)', url)
    gid = (re.search(r'[?&]gid=(\d+)', url) or [None, None])[1]
    if m:
        return ('published', 'https://docs.google.com/spreadsheets/d/%s/pub?%soutput=csv'
                % (m.group(1), ('gid=%s&single=true&' % gid) if gid else ''))
    m = re.search(r'/spreadsheets/d/([\w-]{20,})', url)
    if not m:
        return (None, None)
    return ('link-shared', 'https://docs.google.com/spreadsheets/d/%s/export?format=csv%s'
            % (m.group(1), ('&gid=%s' % gid) if gid else ''))


def gid_of(pubhtml):
    """A published sheet's own tab id, read out of the frameset it returns.

    The address on the district's page has no `gid`, and `pub?output=csv` without one
    returns the FIRST tab, which is not necessarily the one the district linked to. The
    frameset names the tab it is showing, so it is read rather than guessed.
    """
    m = re.search(r'gid=(\d+)', pubhtml.decode('utf-8', 'replace'))
    return m.group(1) if m else None


def fetch(day, verbose=True):
    """Pull every listing into memory first; decide afterwards whether it is a snapshot.

    NOTHING IS WRITTEN UNTIL EVERY ADDRESS HAS ANSWERED. A fetch that dies halfway used to
    leave a dated folder holding three of six listings, which is not a snapshot of anything
    -- and `--check` would then report the missing three as a defect in the archive rather
    than as a run that failed.
    """
    landing = _get(LANDING)
    got = [('Directory of Staff (the district\'s own index of the listings)', LANDING,
            'directory-of-staff.html', landing, 'landing')]
    for name, url in listings(landing):
        kind, addr = csv_address(url)
        if not addr:
            print('  ?? no rows address for %s -- %s' % (name, url))
            continue
        base = slug(name)
        page = _get(re.sub(r'/(edit|pubhtml)\b.*$', '/pubhtml', url)
                    if '/d/e/' in url else url)
        if '/d/e/' in url and 'gid=' not in addr:
            g = gid_of(page)
            if g:
                addr = addr.replace('pub?', 'pub?gid=%s&single=true&' % g)
        rows = _get(addr)
        got.append(('%s (school staff directory)' % name, url, base + '.html', page, kind))
        got.append(('%s (school staff directory, rows)' % name, addr, base + '.csv',
                    rows, kind))
        if verbose:
            print('  %-34s %-12s %6d bytes html  %6d bytes csv'
                  % (name[:34], kind, len(page), len(rows)))
    return got


def write_snapshot(day, got):
    out = os.path.join(DOCS, day)
    os.makedirs(out, exist_ok=True)
    for _label, _up, name, blob, _kind in got:
        path = os.path.join(out, name)
        # A HELD SNAPSHOT IS NEVER OVERWRITTEN, not even by a second run the same day. The
        # district may have edited a sheet between the two, and the first bytes are the
        # ones the catalogue already carries a sha256 for.
        if os.path.exists(path):
            print('  %s already held; left alone' % os.path.relpath(path, ROOT))
            continue
        open(path, 'wb').write(blob)
    return out


def catalogue(day, got):
    """One catalogue row per file, with the fetch date in the label.

    The date is in the LABEL and not only in the path because the label is what the
    extractor reads to stamp a fiscal year onto every row -- the same arrangement
    `fetch_staff_directory.py` uses. A directory with no date in its own dataset is the
    thing this project spends its time warning other people about.
    """
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8'))) if os.path.exists(INDEX) else []
    have = {r['local'] for r in rows}
    added = 0
    for label, upstream, name, blob, kind in got:
        local = ('sources/district-budget/docs/personnel/staff-directory/%s/%s'
                 % (day, name))
        if local in have:
            continue
        rows.append({'label': '%s, fetched %s' % (label, day),
                     'upstream': upstream, 'local': local, 'text': '',
                     'bytes': str(len(blob)),
                     'sha256': hashlib.sha256(blob).hexdigest(), 'read': '1',
                     'page': '', 'school_year': '', 'meeting_date': ''})
        added += 1
    with open(INDEX, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in FIELDS})
    return added


def snapshots():
    if not os.path.isdir(DOCS):
        return []
    return sorted(d for d in os.listdir(DOCS)
                  if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d))


def check():
    """Every snapshot holds its landing page and matched HTML/CSV pairs, and is catalogued.

    IT DOES NOT CHECK THAT THE SHEETS STILL ANSWER. That is `check_source_links.py`'s job
    and it needs the network; this is the offline half, which is what a build can run.
    """
    bad = []
    snaps = snapshots()
    if not snaps:
        bad.append('no snapshot at all -- run without --check')
    cat = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))} \
        if os.path.exists(INDEX) else {}
    for day in snaps:
        d = os.path.join(DOCS, day)
        files = sorted(os.listdir(d))
        if 'directory-of-staff.html' not in files:
            bad.append('%s: no landing page' % day)
        sheets = {f[:-5] for f in files if f.endswith('.html')} - {'directory-of-staff'}
        for s in sorted(sheets):
            if s + '.csv' not in files:
                bad.append('%s: %s.html has no rows beside it' % (day, s))
        if not sheets:
            bad.append('%s: landing page held, no listings' % day)
        for f in files:
            local = ('sources/district-budget/docs/personnel/staff-directory/%s/%s'
                     % (day, f))
            r = cat.get(local)
            if not r:
                bad.append('%s: %s is on disk and in no catalogue' % (day, f))
            elif r['sha256'] != hashlib.sha256(open(os.path.join(d, f), 'rb').read()).hexdigest():
                bad.append('%s: %s does not match its catalogued sha256' % (day, f))
            elif day not in r['label']:
                bad.append('%s: %s label carries no fetch date' % (day, f))
    for b in bad:
        print('  !! %s' % b)
    print('%d snapshot(s): %s' % (len(snaps), ', '.join(snaps) or '-'))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--day', help='override the snapshot date (for a re-run of one day)')
    ap.add_argument('--if-changed', action='store_true',
                    help='keep a snapshot only when the bytes differ from the last one '
                         '(what the scheduled run uses); the check is logged either way')
    a = ap.parse_args()
    if a.check:
        return check()
    day = a.day or datetime.date.today().isoformat()
    got = fetch(day)
    blobs = {name: blob for _l, _u, name, blob, _k in got}
    if a.if_changed:
        # The rows only -- see snapshot_log.same_as_latest: the HTML carries a nonce
        # and differs on every fetch, so comparing it would make every run a change.
        last, same = snapshot_log.same_as_latest(
            DOCS, blobs, only=[n for n in blobs if n.endswith('.csv')])
        if same:
            snapshot_log.record(DOCS, day, False, snapshot=last, files=len(blobs),
                               note='identical to %s; nothing written' % last)
            print('unchanged since %s -- no snapshot written; logged in checked.csv' % last)
            return 0
    snapshot_log.record(DOCS, day, True, snapshot=day, files=len(blobs),
                       note='snapshot written')
    out = write_snapshot(day, got)
    n = catalogue(day, got)
    print('wrote %s -- %d files, %d catalogued' % (os.path.relpath(out, ROOT),
                                                   len(got), n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
