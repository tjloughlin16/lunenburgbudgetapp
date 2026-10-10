#!/usr/bin/env python3
"""THE TOWN'S OPEN JOBS, as its own website lists them -- kept on every change.

    python3 scripts/fetch_town_job_postings.py [--if-changed] [--check] [--day YYYY-MM-DD]
    python3 scripts/fetch_town_job_postings.py --dry-run   # fetch and report; write nothing

Writes `sources/town-supplementary/docs/job-postings/<YYYY-MM-DD>/listing.html` through
`ingest.stage()` / `ingest.secure()`, appends a row to `sources/town-supplementary/index.csv`,
and a row per LOOK to `job-postings/checked.csv`. The school district's postings are a
separate source with their own fetcher (`fetch_school_job_postings.py`): the district hires
through SchoolSpring, the town through its own CivicPlus site, and neither lists the other's.

TJ, 10 October 2026: *"make sure the boards and department pages have a JOB POSTINGS page
linked for any jobs available. And a history on that same page of openings and fills."*
The school side existed; the town side did not, so a department page had nothing to link.

WHERE THE POSTINGS LIVE. `https://www.lunenburgma.gov/Jobs.aspx`, the town's own job board
(checked 10 October 2026: two postings, Data Collector and Videographer). Two easier routes
were tried first and are NOT used, so nobody tries them again expecting otherwise:

  * the RSS feed the page advertises (`RSSFeed.aspx?ModID=66&CID=All-0`, and the per-category
    `CID=NonBenefitted-Positions-100`) answers a valid, EMPTY channel while the page lists
    two jobs. An empty feed is a statement about the feed, not about the town (CLAUDE.md
    13c), and building on it would record every posting as taken down;
  * each posting's own page (`Jobs.aspx?...&JobID=Data-Collector-95`) returns, to a script,
    the site's job-SUBMISSION form shell -- the description is not in the bytes. Only the
    `og:description` meta carries the same truncated summary the listing already prints.

So the LISTING is the document. It prints, per posting: the town's own numeric job id (the
`jobTitle_95` anchor), the title, `Posted <date> | <closing terms>` and a summary that opens
`Job Title : ... Department: ...`. The extractor reads those; this file only keeps the page.

THE PAGE IS NOT BYTE-REPRODUCIBLE. ASP.NET stamps a fresh encrypted view state into every
response, so two fetches a second apart differ while the jobs on it are identical (checked:
two consecutive sha256s differ). Comparing bytes would write a snapshot every day, each frozen
in the bucket for ten years. So the comparison is on the PARSED POSTINGS -- `parse()` below,
the same function the extractor uses -- and the page is kept only when they move. Compare the
data, keep the rendering: `snapshot_log`'s own rule for the district's pages.

THE PARSE MUST TIE TO THE PAGE'S OWN COUNT. A redesign that renames the `job` class would
parse to zero postings and record every open job as taken down -- the one thing this exists
to say. The search form prints a count per category (`Non-Benefitted Positions (2)`), and a
parse that disagrees with their sum stops the run, exit 3, with nothing logged as a look.
"""
import argparse
import csv
import datetime
import hashlib
import html
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot_log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL = 'town-supplementary/docs/job-postings'
DOCS = os.path.join(ROOT, 'sources', REL)
INDEX = os.path.join(ROOT, 'sources', 'town-supplementary', 'index.csv')
FIELDS = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read']
URL = 'https://www.lunenburgma.gov/Jobs.aspx'
UA = {'User-Agent': 'lunenburgbudgetproject.org (public records archive)'}
LOCKED, TRANSIENT = 3, 2

# `class="job"` or `class="job first"` -- NOT `jobsListingContent`, the wrapper, which a
# looser `job[^"]*` matched first and so swallowed the first posting's anchor into itself.
JOB = re.compile(r'<div class="job(?: [^"]*)?">(.*?)</div>', re.S)
TITLE = re.compile(r'<a id="jobTitle_(\d+)" href="([^"]+)">(.*?)</a>', re.S)
POSTED = re.compile(r'<span>\s*Posted ([^<|]+?)\s*(?:\|\s*([^<]*?))?\s*</span>', re.S)
SUMMARY = re.compile(r'<p>(.*?)(?:&nbsp;)?<a ', re.S)
CATEGORY = re.compile(r'<div id="cat(\d+)" class="listing[^"]*">.*?<h2[^>]*>\s*(.*?)\s*</h2>', re.S)
# The search form's category checkboxes print a count per category: `Non-Benefitted
# Positions (2)`. The sidebar's links print the names alone.
CATEGORY_COUNT = re.compile(r'<label for="chk_\d+">[^<(]*\((\d+)\)\s*</label>')


def _text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def parse(blob):
    """Every posting the listing prints, as dicts, in page order. Pure: no network, no disk.

    `category` is the heading the posting sits under; `department` is read out of the town's
    own summary line (`Department: Assessor`) and is blank where the summary does not say.
    """
    s = blob.decode('utf-8', errors='replace') if isinstance(blob, bytes) else blob
    # Which category heading each job id sits under, by position on the page.
    cats = [(m.start(), _text(m.group(2))) for m in CATEGORY.finditer(s)]
    out = []
    for m in JOB.finditer(s):
        t = TITLE.search(m.group(1))
        if not t:
            continue
        p = POSTED.search(m.group(1))
        summ = SUMMARY.search(m.group(1))
        summary = _text(summ.group(1)) if summ else ''
        dept = re.search(r'Department\s*:\s*(.+?)\s+(?:Grade|Created Date|Reports to|FLSA|Hours)\b', summary)
        cat = [c for pos, c in cats if pos < m.start()]
        out.append({
            'job_id': t.group(1),
            'title': _text(t.group(3)),
            'href': html.unescape(t.group(2)),
            'posted_as_printed': _text(p.group(1)) if p else '',
            'closing_as_printed': _text(p.group(2)) if p and p.group(2) else '',
            'category': cat[-1] if cat else '',
            'department_as_printed': dept.group(1).strip() if dept else '',
            'summary': summary.rstrip('. ').rstrip(),
        })
    return out


def category_total(blob):
    """The page's own count of open postings, summed over its categories; None if absent."""
    n = CATEGORY_COUNT.findall(blob.decode('utf-8', errors='replace'))
    return sum(int(x) for x in n) if n else None


def _get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        print('TOWN JOBS %s: HTTP %d' % ('LOCKED' if 400 <= e.code < 500 and e.code != 429
                                         else 'UNREACHABLE', e.code), file=sys.stderr)
        raise SystemExit(LOCKED if 400 <= e.code < 500 and e.code != 429 else TRANSIENT)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print('TOWN JOBS UNREACHABLE: %s' % e, file=sys.stderr)
        raise SystemExit(TRANSIENT)


def fetch():
    blob = _get(URL)
    jobs = parse(blob)
    if b'jobsListingContent' not in blob:
        print('TOWN JOBS LOCKED: the page no longer carries a job listing at all -- refusing',
              file=sys.stderr)
        raise SystemExit(LOCKED)
    # THE COUNT IS ASSERTED, as the school fetcher asserts SchoolSpring's: the page prints
    # its own total per category, and a parse that disagrees would record real postings as
    # taken down. Absent counts are tolerated only when the parse found something.
    total = category_total(blob)
    if (total is not None and total != len(jobs)) or (total is None and not jobs):
        print('TOWN JOBS LOCKED: the page counts %s posting(s) and %d parsed -- refusing '
              'rather than recording them as taken down' % (total, len(jobs)), file=sys.stderr)
        raise SystemExit(LOCKED)
    return blob, jobs


def held_jobs():
    """(day, parsed postings) of the newest snapshot held, or (None, None)."""
    day = snapshot_log.latest(DOCS)
    if not day:
        return None, None
    return day, parse(open(os.path.join(DOCS, day, 'listing.html'), 'rb').read())


def catalogue(day, blob):
    raw = open(INDEX, 'rb').read() if os.path.exists(INDEX) else b''
    nl = '\r\n' if b'\r\n' in raw else '\n'
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8')))) if raw else []
    cols = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))).fieldnames or FIELDS) if raw else FIELDS
    local = 'sources/%s/%s/listing.html' % (REL, day)
    if any(r['local'] == local for r in rows):
        return 0
    rows.append({'label': 'Job postings: the open postings the Town of Lunenburg lists on its '
                          'job board, fetched %s' % day,
                 'upstream': URL, 'local': local, 'text': '', 'bytes': str(len(blob)),
                 'sha256': hashlib.sha256(blob).hexdigest(), 'read': '1'})
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=cols, lineterminator=nl)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in cols})
    tmp = INDEX + '.tmp'
    open(tmp, 'wb').write(out.getvalue().encode('utf-8'))
    os.replace(tmp, INDEX)
    return 1


def check():
    bad = []
    snaps = snapshot_log.snapshots(DOCS)
    if not snaps:
        bad.append('no snapshot at all -- run without --check')
    cat = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
    for day in snaps:
        p = os.path.join(DOCS, day, 'listing.html')
        local = 'sources/%s/%s/listing.html' % (REL, day)
        if not os.path.exists(p):
            bad.append('%s: no listing.html' % day)
            continue
        blob = open(p, 'rb').read()
        r = cat.get(local)
        if not r:
            bad.append('%s: listing.html is in no catalogue' % day)
        elif r['sha256'] != hashlib.sha256(blob).hexdigest():
            bad.append('%s: listing.html does not match its catalogued sha256' % day)
        if category_total(blob) not in (None, len(parse(blob))):
            bad.append('%s: the page counts %s postings and %d parse' % (day, category_total(blob), len(parse(blob))))
    for b in bad:
        print('  !! %s' % b)
    print('%d snapshot(s): %s' % (len(snaps), ', '.join(snaps) or '-'))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--day', help='override the snapshot date')
    ap.add_argument('--if-changed', action='store_true',
                    help='the default and only behaviour; accepted so refresh.py can call '
                         'this exactly as it calls the other snapshot fetchers')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    day = a.day or datetime.date.today().isoformat()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise SystemExit('--day must be YYYY-MM-DD')
    blob, jobs = fetch()
    last, held = held_jobs()
    same = held is not None and held == jobs
    why = 'identical postings to %s' % last if same else (
        'first snapshot' if held is None else 'postings changed since %s' % last)
    print('  the town lists %d posting(s): %s' % (len(jobs), '; '.join(j['title'] for j in jobs) or '-'))
    if a.dry_run:
        print('dry run: %s' % why)
        return 0
    os.makedirs(DOCS, exist_ok=True)
    if same:
        snapshot_log.record(DOCS, day, False, snapshot=last, files=0,
                            note='%s; %d open; nothing written' % (why, len(jobs)))
        print('unchanged (%s) -- no snapshot written; logged in checked.csv' % why)
        return 0
    if os.path.isdir(os.path.join(DOCS, day)):
        snapshot_log.record(DOCS, day, True, snapshot=day, files=0,
                            note='%s; a snapshot for today is already held -- waits' % why)
        print('changed, but %s is already held; the change waits for the next run' % day)
        return 0
    import ingest
    ok, reason = ingest.stage('%s/%s/listing.html' % (REL, day), blob, upstream=URL)
    if not ok:
        raise SystemExit('listing.html: %s' % reason)
    done, failed = ingest.secure(quiet=True)
    if failed:
        snapshot_log.record(DOCS, day, True, snapshot='', files=1,
                            note='%s; staged, push failed -- still in flight' % why)
        raise SystemExit('staged but not yet in the bucket; ingest.py --secure retries.')
    n = catalogue(day, blob)
    snapshot_log.record(DOCS, day, True, snapshot=day, files=1,
                        note='%s; %d open; snapshot written' % (why, len(jobs)))
    print('wrote sources/%s/%s/listing.html (%s), %d catalogued, %d open postings'
          % (REL, day, why, n, len(jobs)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
