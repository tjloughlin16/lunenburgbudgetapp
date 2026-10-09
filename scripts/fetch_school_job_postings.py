#!/usr/bin/env python3
"""THE DISTRICT'S OPEN JOBS, as its own applicant system lists them -- kept on every change.

    python3 scripts/fetch_school_job_postings.py [--if-changed] [--check] [--day YYYY-MM-DD]
    python3 scripts/fetch_school_job_postings.py --dry-run   # fetch and report; write nothing

Writes `sources/district-budget/docs/personnel/job-postings/<YYYY-MM-DD>/` through
`ingest.stage()` / `ingest.secure()`, appends a row per file to
`sources/district-budget/index.csv`, and a row per LOOK to `job-postings/checked.csv`.

TJ, 5 October 2026: *"put this on the refresh list to see if new job postings are added or
some removed... and keep the history as a table."* He pointed at Indeed, then at
SchoolSpring.

WHERE THE POSTINGS ACTUALLY LIVE. Indeed's company page is a SYNDICATION of somebody
else's listing, answers scripts with HTTP 403, and forbids scraping in its terms -- so it
is not the source and nothing here touches it. Lunenburg Public Schools posts through
SCHOOLSPRING (a PowerSchool product): employer id `11047`, named `Lunenburg Public Schools`
in SchoolSpring's own organisation lookup, with `@lunenburgschools.net` contacts on every
posting. That is the district's own account, so this is the publisher's copy, not a
reseller's. SchoolSpring's `robots.txt` disallows nothing.

`lunenburg.schoolspring.com` 302s to the SchoolSpring homepage and the district's website
links no employment page (checked 5 October 2026: the home page nav, `/district`,
`/about-the-district`, `/contact`, the superintendent's page, and `/employment`, `/careers`,
`/jobs`, `/human-resources` -- all 404 or silent). So the address is the one the
SchoolSpring web app itself calls, read out of its JavaScript bundle: a public, unauthenti-
cated JSON API at `api.schoolspring.com`. It is MACHINE-READABLE and byte-stable -- two
fetches a second apart return identical bytes, unlike the staff directories' HTML -- so the
raw response is the document and no scraping of rendered pages happens at all.

WHAT IS FETCHED, AND THE SHAPE THAT KEEPS THE BUCKET SMALL.

  * `listing.json` -- the search API's answer for `organization=e-11047`: one row per open
    posting with its id, title, the school SchoolSpring prints as the employer, location and
    display date. Written into EVERY snapshot, because it is what says which postings were
    open on that date.
  * `job-<id>.json` -- the detail API's answer for one posting: categories, job type, pay,
    post date, close date, description. Written ONLY when that posting's detail is new or
    differs from the newest copy already held. A posting open for a month is therefore held
    once, not thirty times -- every file in a dated folder is frozen in the bucket for ten
    years (`archive_storage.frozen`), so an unchanged copy is a permanent cost that says
    nothing. The extractor resolves each posting's detail as the newest copy held at or
    before the snapshot it is reading.

A SNAPSHOT ONLY ON CHANGE, A LOG OF EVERY LOOK. `--if-changed` writes nothing when the
listing and every detail match what is held, and still appends a row to `checked.csv`,
because "the postings did not change between Monday and Friday" and "nobody looked" must
not read the same (`snapshot_log`). The extractor reads that log to bound `last_seen` and
`removed_seen` by the days we actually looked.

THE COUNT IS ASSERTED. SchoolSpring answers a separate count endpoint; a listing whose
length disagrees with it is refused, because a page that silently came back short would
otherwise record real postings as REMOVED -- the one thing this table exists to say.

SCREENED, AND NOTED -- NOT REFUSED. Postings are published to the world by the district, so
they have a public upstream and the redaction gate passes them. Each blob is still run
through `pii_screen` as text and any finding is printed, but it no longer stops the
snapshot: a public posting is not confidential (TJ, 9 October 2026, after "diagnosis" in an
occupational therapist's duties held the whole batch). A posting names its hiring contact (a district
work address) -- that is the district's own publication, and is what the screen should
not and does not flag.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot_log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL = 'district-budget/docs/personnel/job-postings'
DOCS = os.path.join(ROOT, 'sources', REL)
INDEX = os.path.join(ROOT, 'sources', 'district-budget', 'index.csv')
FIELDS = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read',
          'page', 'school_year', 'meeting_date']

EMPLOYER = 'e-11047'          # SchoolSpring's id for Lunenburg Public Schools (MA)
EMPLOYER_NAME = 'Lunenburg Public Schools'
API = 'https://api.schoolspring.com/api/Jobs'
DOMAIN = 'www.schoolspring.com'
PAGE_SIZE = 100
SEARCH = ('%s/{what}?domainName=%s&keyword=&location=&category=&gradelevel=&jobtype='
          '&organization=%s&swLat=&swLon=&neLat=&neLon=' % (API, DOMAIN, EMPLOYER))
UA = {'User-Agent': 'lunenburgbudgetproject.org (public records archive)',
      'Accept': 'application/json'}


def listing_url(page):
    return (SEARCH.format(what='GetPagedJobsWithSearch')
            + '&page=%d&size=%d&sortDateAscending=false' % (page, PAGE_SIZE))


def count_url():
    return SEARCH.format(what='GetJobsCountWithSearch')


def detail_url(job_id):
    return '%s/%s?domainName=%s' % (API, job_id, DOMAIN)


# HOW THIS FAILS, IN TWO KINDS, because refresh.py treats them differently.
#
# The API is UNDOCUMENTED -- read out of SchoolSpring's own JavaScript, with no published
# terms -- and TJ chose, 5 October 2026, to "build against it until it's locked down".
# So the day it is locked down has to be unmissable, and a slow afternoon must not look
# like it:
#
#   LOCKED (exit 3)     an answer that says the API is no longer ours to read: any 4xx
#                       but 429 (a renamed endpoint answers 400), a login page or anything else that is not JSON, or JSON
#                       without `success`. refresh.py raises a full-width notice and a
#                       desktop alert EVERY run until it clears.
#   TRANSIENT (exit 2)  no answer, or a server error: a timeout, DNS, a 429, a 5xx. A note,
#                       escalating to the same notice once it has lasted three days.
#
# Either way nothing is snapshotted, and nothing is appended to `checked.csv` -- so a
# lockout can never be read as every posting being REMOVED.
LOCKED, TRANSIENT = 3, 2


class Locked(SystemExit):
    def __init__(self, msg):
        print('SCHOOLSPRING LOCKED: ' + msg, file=sys.stderr)
        super().__init__(LOCKED)


class Transient(SystemExit):
    def __init__(self, msg):
        print('SCHOOLSPRING UNREACHABLE: ' + msg, file=sys.stderr)
        super().__init__(TRANSIENT)


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        # Every 4xx but a rate limit means the request we know how to make is no longer
        # accepted -- an endpoint renamed answers 400, which is a change, not a hiccup.
        if 400 <= e.code < 500 and e.code != 429:
            raise Locked('HTTP %d from %s' % (e.code, url))
        raise Transient('HTTP %d from %s' % (e.code, url))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Transient('%s: %s' % (url, e))


def _ok(blob, what):
    """The parsed `value` of a SchoolSpring answer, or a refusal naming what failed."""
    try:
        d = json.loads(blob)
    except ValueError:
        raise Locked('%s: not JSON (first bytes %r) -- refusing to snapshot' % (what, blob[:60]))
    if not isinstance(d, dict) or d.get('success') is not True or 'value' not in d:
        raise Locked('%s: SchoolSpring did not answer success (%r) -- refusing'
                         % (what, str(d)[:200]))
    return d['value']


def fetch(verbose=True):
    """Everything into memory first. Nothing is written until every address has answered.

    Returns (files, ids): files is {name: (upstream, blob)}, ids the posting ids listed.
    """
    expected = _ok(_get(count_url()), 'count')
    files, ids, page = {}, [], 1
    while True:
        url = listing_url(page)
        blob = _get(url)
        rows = _ok(blob, 'listing page %d' % page)['jobsList'] or []
        files['listing.json' if page == 1 else 'listing-p%d.json' % page] = (url, blob)
        ids += [str(r['jobId']) for r in rows]
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    if len(ids) != expected or len(set(ids)) != len(ids):
        raise SystemExit('the listing holds %d postings (%d distinct) and SchoolSpring\'s own '
                         'count says %d -- refusing: a short page would record real postings '
                         'as removed' % (len(ids), len(set(ids)), expected))
    for i in ids:
        url = detail_url(i)
        blob = _get(url)
        info = _ok(blob, 'job %s' % i)['jobInfo']
        if str(info.get('jobId')) != i or info.get('employerName') != EMPLOYER_NAME:
            raise SystemExit('job %s: detail answers for job %s at %r -- refusing'
                             % (i, info.get('jobId'), info.get('employerName')))
        files['job-%s.json' % i] = (url, blob)
    if verbose:
        print('  SchoolSpring lists %d posting(s) for %s (count endpoint: %d)'
              % (len(ids), EMPLOYER_NAME, expected))
    return files, ids


def snapshots():
    return snapshot_log.snapshots(DOCS)


def held_details():
    """{file name: sha256 of the NEWEST held copy} for every job-<id>.json in any snapshot."""
    out = {}
    for day in snapshots():
        d = os.path.join(DOCS, day)
        for f in os.listdir(d):
            if f.startswith('job-') and f.endswith('.json'):
                out[f] = hashlib.sha256(open(os.path.join(d, f), 'rb').read()).hexdigest()
    return out


def held_listing():
    """{name: sha256} of the listing file(s) in the newest snapshot."""
    day = snapshot_log.latest(DOCS)
    if not day:
        return None, {}
    d = os.path.join(DOCS, day)
    return day, {f: hashlib.sha256(open(os.path.join(d, f), 'rb').read()).hexdigest()
                 for f in os.listdir(d) if f.startswith('listing')}


def what_changed(files):
    """(names to write, reason). Empty names means nothing moved."""
    last, listing = held_listing()
    got_listing = {n: hashlib.sha256(b).hexdigest() for n, (_u, b) in files.items()
                   if n.startswith('listing')}
    details = held_details()
    new_details = [n for n, (_u, b) in files.items() if n.startswith('job-')
                   and details.get(n) != hashlib.sha256(b).hexdigest()]
    if got_listing == listing and not new_details:
        return [], 'identical to %s' % last
    names = sorted(got_listing) + sorted(new_details)
    why = []
    if got_listing != listing:
        why.append('listing changed' if last else 'first snapshot')
    if new_details:
        why.append('%d posting detail(s) new or edited' % len(new_details))
    return names, '; '.join(why)


def screen(files, names):
    import pii_screen
    bad = []
    for n in names:
        for f in pii_screen.screen(n + '.txt', files[n][1]):
            bad.append('%s: %s' % (n, f))
    return bad


def catalogue(day, files, names):
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8'))) if os.path.exists(INDEX) else []
    have = {r['local'] for r in rows}
    added = 0
    for n in names:
        up, blob = files[n]
        local = 'sources/%s/%s/%s' % (REL, day, n)
        if local in have:
            continue
        what = ('the open postings SchoolSpring lists for Lunenburg Public Schools'
                if n.startswith('listing') else 'SchoolSpring posting %s, detail' % n[4:-5])
        rows.append({'label': 'Job postings: %s, fetched %s' % (what, day),
                     'upstream': up, 'local': local, 'text': '',
                     'bytes': str(len(blob)), 'sha256': hashlib.sha256(blob).hexdigest(),
                     'read': '1', 'page': '', 'school_year': '', 'meeting_date': ''})
        added += 1
    with open(INDEX, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in FIELDS})
    return added


def check():
    """Offline: every snapshot has a listing, every posting it lists has a detail held at or
    before it, and every file is catalogued with a matching sha256 and a dated label."""
    bad = []
    snaps = snapshots()
    if not snaps:
        bad.append('no snapshot at all -- run without --check')
    cat = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))} \
        if os.path.exists(INDEX) else {}
    seen_details = set()
    for day in snaps:
        d = os.path.join(DOCS, day)
        files = sorted(os.listdir(d))
        seen_details |= {f for f in files if f.startswith('job-')}
        if 'listing.json' not in files:
            bad.append('%s: no listing.json' % day)
        else:
            for p in sorted(f for f in files if f.startswith('listing')):
                for r in json.load(open(os.path.join(d, p)))['value']['jobsList'] or []:
                    if 'job-%s.json' % r['jobId'] not in seen_details:
                        bad.append('%s: posting %s listed, no detail held at or before it'
                                   % (day, r['jobId']))
        for f in files:
            r = cat.get('sources/%s/%s/%s' % (REL, day, f))
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
    ap.add_argument('--day', help='override the snapshot date')
    # ACCEPTED FOR PARITY WITH THE DIRECTORY FETCHERS, AND ALWAYS ON. Unlike their HTML,
    # every byte here is reproducible, so there is no full-photograph mode worth having:
    # a snapshot is written only when something moved, and every look is logged.
    ap.add_argument('--if-changed', action='store_true',
                    help='the default and only behaviour; accepted so refresh.py can call '
                         'this exactly as it calls the directory fetchers')
    ap.add_argument('--dry-run', action='store_true', help='fetch and say what would change')
    a = ap.parse_args()
    if a.check:
        return check()
    day = a.day or datetime.date.today().isoformat()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise SystemExit('--day must be YYYY-MM-DD')
    files, ids = fetch()
    names, why = what_changed(files)
    if a.dry_run:
        print('dry run: %s -- would write %d file(s)' % (why, len(names)))
        return 0
    if not names:
        snapshot_log.record(DOCS, day, False, snapshot=snapshot_log.latest(DOCS),
                            files=0, note='%s; %d open; nothing written' % (why, len(ids)))
        print('unchanged (%s) -- no snapshot written; logged in checked.csv' % why)
        return 0
    if os.path.isdir(os.path.join(DOCS, day)):
        # A HELD SNAPSHOT IS NEVER OVERWRITTEN. A second change on the same day waits for
        # the next run, and the log says so rather than nothing.
        snapshot_log.record(DOCS, day, True, snapshot=day, files=0,
                            note='%s; a snapshot for today is already held -- waits' % why)
        print('changed (%s), but %s is already held; the change waits for the next run'
              % (why, day))
        return 0
    # NOTED, NOT REFUSED. TJ, 9 October 2026, after the screen held an occupational
    # therapist's posting over "the identification and diagnosis of students" in its list of
    # duties: *"i dont know how a job posting can be considered confidential or sensitive"*.
    # It cannot. The district published it to a public job board; rule 13e's gate is for
    # documents with NO public address, and this one has one. Refusing here stopped the
    # district's own publication over a word every therapist and nurse posting carries. The
    # screen still runs, so a finding is in the log beside the snapshot, and nothing waits.
    bad = screen(files, names)
    for b in bad:
        print('  note: pii_screen matched %s -- a public posting, kept' % b)

    import ingest
    for n in names:
        up, blob = files[n]
        ok, reason = ingest.stage('%s/%s/%s' % (REL, day, n), blob, upstream=up)
        if not ok:
            raise SystemExit('%s: %s' % (n, reason))
    done, failed = ingest.secure(quiet=True)
    if failed:
        snapshot_log.record(DOCS, day, True, snapshot='', files=len(names),
                            note='%s; staged, push failed -- still in flight' % why)
        raise SystemExit('%d file(s) staged but not yet in the bucket; ingest.py --secure '
                         'retries. Nothing lost.' % failed)
    n = catalogue(day, files, names)
    snapshot_log.record(DOCS, day, True, snapshot=day, files=len(names),
                        note='%s; %d open; snapshot written' % (why, len(ids)))
    print('wrote sources/%s/%s -- %d file(s) (%s), %d catalogued, %d open postings'
          % (REL, day, len(names), why, n, len(ids)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
