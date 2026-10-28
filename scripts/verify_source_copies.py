#!/usr/bin/env python3
"""Is our copy of each document still the publisher's copy?

`check_source_links.py` asks whether the publisher's link still opens. This asks the
harder question underneath it: if it opens, does it hand back the same bytes we archived?

A Drive file can be replaced in place without its URL changing. Nothing in a link check
would notice, and nothing on the sources page would stop saying "our copy" about a
document that had quietly become a different one. So the hash is checked against the
publisher, not only recorded at download time.

**Three ways bytes can differ and only one of them is a finding.**

  * `identical`   -- same sha256. The document is the document.
  * `repackaged`  -- a zip (docx/xlsx/pptx) whose every member is byte-identical but whose
                     container differs. Google re-zips a Doc on every export, so the sha
                     changes while the document does not. Our instrument, not their edit.
  * `resaved`     -- a PDF whose extracted text is identical but whose bytes are not. The
                     same document re-saved by another producer.
  * `reflowed`    -- a PDF whose text is identical once every space is removed. A producer
                     split a text run in a different place, so `Recommendations\nand next
                     steps` became `Recommendation\ns and next steps` -- note the break
                     falls INSIDE the word, which is why splitting on whitespace does not
                     catch it and why the comparison strips whitespace rather than
                     normalising it. Every character and every digit is the same; only
                     where the line broke moved. What this cannot see is a change that is
                     purely whitespace, and that is the entire cost of it -- which is why
                     it gets its own word instead of being folded into `resaved`.
  * `differs`     -- content actually differs. This is the one to look at.
  * `rerendered`  -- a web page we hold as a web page, whose bytes differ because pages
                     re-render on every request. Says nothing about its content.
  * `page, not file` -- HTML came back where we hold a file, from a host that is not
                     Google: our recorded address is the page listing the file. Ours to fix.
  * `restricted`  -- the host answered 2xx and returned HTML. That is what a Google
                     sign-in wall looks like: the request succeeded, and what succeeded
                     was being shown a login page. Nothing can be compared, and our copy
                     is the only public one -- which is the archive's entire reason for
                     existing.
  * `unreachable` -- a network or host failure, including any non-2xx. Not a claim about
                     the document and not a claim about permissions. A 503 once came back
                     labelled `restricted` here, because the classifier looked at the body
                     before the status code; a host having a bad minute was being reported
                     as the district having locked a file.

Slow on purpose: one request at a time, no concurrency, the same honest user agent the
crawlers use. Run it occasionally, never in the build.

    python3 scripts/verify_source_copies.py [--only SUBSTRING] [--limit N]
    python3 scripts/verify_source_copies.py --prefix district-budget/ --due-days 30 --max 40

The second form is what the daily refresh runs, one slice per document set, on the cadence
in sources/data/source-cadence.csv -- so "occasionally" is now a schedule.

Writes sources/data/copy-status.csv.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'fy28/src/data/sources.json')
SRC = os.path.join(ROOT, 'sources')
OUT = os.path.join(ROOT, 'sources/data/copy-status.csv')
# The same identity the crawlers and the link checker use. A request that disguises itself
# as a browser measures what a disguised request gets, not what a resident gets.
UA = ('Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; '
      '+https://lunenburgbudgetproject.org)')

# Addresses that are generated on submission and have no per-file URL. There is nothing to
# download, so there is nothing to compare; they are reported and skipped rather than
# counted as failures. Kept in step with FORM_ONLY in build_source_index.py.
# Also here: a data-portal landing page. `xlsx/dese-all-districts.xlsx` was built by hand
# from a Socrata dataset, so its recorded address is the dataset rather than a file, on
# purpose -- see SOURCE_URLS in build_source_index.py. Fetching it returns the portal's
# HTML, which this script would otherwise report as a sign-in wall. That would be the
# instrument's answer presented as the publisher's, which is the failure rule 13 names.
NO_FILE = re.compile(r'dls-gw\.dor\.state\.ma\.us|profiles\.doe\.mass\.edu/statereport/'
                     r'selectedpopulations|data\.mass\.gov/d/[\w-]+$')

# CHECKED BY SOMETHING ELSE, so not here. A dated snapshot folder holds every version a
# weekly fetcher landed, and only the newest can match the live page -- the rest would be
# reported as `differs` every time, which is the publisher's history read as an edit. Those
# folders are re-checked by their own fetchers on the cadence in source-cadence.csv. And a
# Socrata export is generated per download, so its bytes never match twice; whether the
# DATA changed is asked of the portal by check_socrata_sources.py instead.
SNAPSHOTS = ('state-dese/entitlements/', 'state-dese/grants/', 'state-dese/awards/')
SNAPSHOT_PARTS = ('/staff-directory/', '/job-postings/')
REGISTRY = os.path.join(ROOT, 'sources/data/dese-source-registry.csv')


def socrata_locals():
    with open(REGISTRY, newline='', encoding='utf-8') as fh:
        return {r['local'][len('sources/'):] for r in csv.DictReader(fh)
                if r['source_kind'] == 'socrata' and r['local'].startswith('sources/')}


def eligible(prefixes=()):
    """-> [(path, upstream)]: every held document with a per-file address that THIS script is
    the check for. source_cadence.py counts its coverage off the same list, so the two
    cannot disagree about what there is to check."""
    doc = json.load(open(INDEX))
    # A path can appear twice with two different addresses -- the district's budget page
    # links the same FY26 presentation under two Drive ids, and both are real addresses for
    # the same document. Both are checked and both are written out; collapsing them here
    # would throw away the fact that the page publishes it twice.
    items = [(i['path'], i['upstream']) for g in doc['groups'] for i in g['items']
             if i.get('upstream') and not NO_FILE.search(i['upstream'])]
    skip = socrata_locals()
    return [(p, u) for p, u in items
            if os.path.isfile(os.path.join(SRC, p))
            and not p.startswith(SNAPSHOTS)
            and not any(s in p for s in SNAPSHOT_PARTS)
            and p not in skip
            and (not prefixes or p.startswith(tuple(prefixes)))]


def last_checked():
    """-> {(path, url): 'YYYY-MM-DD'} from the last run of every row."""
    if not os.path.exists(OUT):
        return {}
    with open(OUT, newline='') as fh:
        return {(r['path'], r['url']): r['checked'] for r in csv.DictReader(fh)}


def sha(path):
    m = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            m.update(chunk)
    return m.hexdigest()


def direct(url):
    """The URL that returns the bytes rather than a viewer page.

    Drive publishes a document under several shapes -- /file/d/<id>/view, open?id=<id>,
    and the Docs editor -- and every one of them serves HTML to a script. Getting this
    wrong looks exactly like a changed document: 83KB of sign-in page against our PDF.
    That is what it looked like here for six files before the open?id= form was handled.
    """
    m = re.search(r'drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([\w-]+)', url)
    if m:
        return (f'https://drive.usercontent.google.com/download'
                f'?id={m.group(1)}&export=download&confirm=t')
    m = re.search(r'docs\.google\.com/document/d/([\w-]+)', url)
    if m:
        return f'https://docs.google.com/document/d/{m.group(1)}/export?format=docx'
    m = re.search(r'docs\.google\.com/spreadsheets/d/([\w-]+)', url)
    if m:
        return f'https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx'
    return url


def zip_members_equal(a, b):
    """Same document, different zip. True when every member is byte-identical."""
    try:
        with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
            if sorted(za.namelist()) != sorted(zb.namelist()):
                return False
            return all(za.read(n) == zb.read(n) for n in za.namelist())
    except Exception:
        return False


def pdf_text(path):
    """Needs pypdf; absent, we decline to make any claim about the text."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        return ''.join((pg.extract_text() or '') for pg in PdfReader(path).pages) or None
    except Exception:
        return None


HTML = ('.html', '.htm')


def classify(remote, local, code, url=''):
    # The status code first. HTML behind a 2xx is a sign-in wall; HTML behind anything
    # else is a host that did not serve the file, which says nothing about who may read it.
    if not code.startswith('2'):
        return 'unreachable'
    if sha(remote) == sha(local):
        return 'identical'
    # Leading whitespace before the first tag is common, and missing it sent DESE's
    # chapter70 index page down to `differs` -- an HTML page compared byte for byte with a
    # workbook. (28 October 2026, the first scheduled run.)
    head = open(remote, 'rb').read(512).lstrip()[:4]
    if head[:1] == b'<':
        # A WEB PAGE WE HOLD AS A WEB PAGE re-renders on every request -- navigation, a
        # token, a date -- so its bytes never match twice. Nineteen town board pages and
        # DESE regulation pages came back `differs` on that run with nothing edited. A byte
        # check cannot say whether such a page's CONTENT moved; the fetcher that mirrors it
        # can, and this says which it is rather than raising a finding.
        if local.lower().endswith(HTML):
            return 'rerendered'
        # HTML where we hold a FILE, from a host that is not Google: the recorded address is
        # a page that lists the file, not the file. A defect in our address (rule 12), not a
        # sign-in wall and not a change.
        if url and not re.search(r'google\.com', url):
            return 'page, not file'
        return 'restricted'
    if head == b'PK\x03\x04' and zip_members_equal(remote, local):
        return 'repackaged'
    if head == b'%PDF':
        a, b = pdf_text(remote), pdf_text(local)
        if a and b:
            if a == b:
                return 'resaved'
            if ''.join(a.split()) == ''.join(b.split()):
                return 'reflowed'
    return 'differs'


def check(url, local_path, tmp, tries=2):
    """Fetch once, and once more after a pause if the host did not serve the file.

    Retried because a single bad response would otherwise be written into the archive's
    record as a fact about the document. One retry separates a host having a bad minute
    from a document that is really gone.
    """
    for attempt in range(tries):
        r = subprocess.run(['curl', '-sL', '--max-time', '180', '-A', UA,
                            '-w', '%{http_code}', '-o', tmp, direct(url)],
                           capture_output=True, text=True)
        code = r.stdout.strip() or '000'
        if not os.path.exists(tmp) or not os.path.getsize(tmp):
            state = 'unreachable'
        else:
            state = classify(tmp, local_path, code, url)
        if state != 'unreachable' or attempt == tries - 1:
            break
        time.sleep(5)
    return code, state, sha(tmp) if state != 'unreachable' and os.path.getsize(tmp) else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help='check only paths containing this substring')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--prefix', action='append', default=[],
                    help='check only paths starting with this (repeatable)')
    # THE DAILY SLICE (source-cadence.csv). Only documents whose last check is at least this
    # many days old, never-checked first and then oldest, at most --max of them -- so a set
    # of 900 on a thirty-day cadence costs about thirty requests a morning instead of 900
    # on one of them.
    ap.add_argument('--due-days', type=int)
    ap.add_argument('--max', type=int)
    args = ap.parse_args()

    items = [(p, u) for p, u in eligible(args.prefix) if not args.only or args.only in p]
    if args.due_days is not None:
        seen = last_checked()
        cut = (datetime.date.today() - datetime.timedelta(days=args.due_days)).isoformat()
        items = sorted((it for it in items if seen.get(it, '') <= cut),
                       key=lambda it: seen.get(it, ''))
        if args.max:
            items = items[:args.max]
    if args.limit:
        items = items[:args.limit]

    print(f'comparing {len(items)} documents against the publisher, one at a time\n')
    rows, counts = [], {}
    fd, tmp = tempfile.mkstemp()
    os.close(fd)
    try:
        for n, (path, url) in enumerate(items, 1):
            local = os.path.join(SRC, path)
            code, state, remote = check(url, local, tmp)
            counts[state] = counts.get(state, 0) + 1
            rows.append((path, url, code, state, remote, sha(local)))
            if state not in ('identical',):
                print(f'  {state:12} {path[:62]}')
            if n % 25 == 0:
                print(f'  ... {n}/{len(items)}')
    finally:
        os.path.exists(tmp) and os.remove(tmp)

    today = datetime.date.today().isoformat()
    # A partial run updates the rows it checked and leaves the rest alone. Writing only
    # what --only or --limit looked at would silently replace a full survey with two
    # lines, and the file is what the sources page counts its verified copies from.
    keep = []
    checked = {(r[0], r[1]) for r in rows}
    if os.path.exists(OUT):
        with open(OUT, newline='') as fh:
            keep = [r for r in csv.DictReader(fh)
                    if (r['path'], r['url']) not in checked]
    with open(OUT, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['path', 'url', 'code', 'state', 'remote_sha256', 'local_sha256',
                    'checked'])
        fresh = [[*r, today] for r in rows]
        old = [[r['path'], r['url'], r['code'], r['state'], r['remote_sha256'],
                r['local_sha256'], r['checked']] for r in keep]
        for row in sorted(fresh + old):
            w.writerow(row)
    if keep:
        print(f'  ({len(keep)} rows from an earlier run left in place)')

    print()
    for state in sorted(counts, key=lambda s: -counts[s]):
        print(f'  {counts[state]:>4} {state}')
    print(f'\nwrote {OUT}')
    # A document that differs is a claim on the sources page that has stopped being true.
    # Under --due-days the run is a scheduled check and a difference is its FINDING, not its
    # failure: exit 0, so the refresh records the check as done and the finding is read off
    # copy-status.csv -- otherwise a found change would be retried, and re-found, every day.
    if args.due_days is not None:
        return 0
    return 1 if counts.get('differs') else 0


if __name__ == '__main__':
    sys.exit(main())
