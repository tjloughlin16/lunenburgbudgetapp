#!/usr/bin/env python3
"""DESE's COMPETITIVE GRANT AWARDS: the two listings, and every award document they link.

    python3 scripts/fetch_dese_awards.py            # fetch; land what is new or changed
    python3 scripts/fetch_dese_awards.py --dry-run  # fetch and compare, land nothing
    python3 scripts/fetch_dese_awards.py --check    # every held file is catalogued

TJ, 23 October 2026, on /school-all-funds/grants-others-receive: *"i was hoping to see which
grants our neighbors/comparisons are getting that we aren't... almost a PUSH to the school
committee to look into other grants."* The allocation pages that page was built from are
DESE's *"State and Federal Entitlement And Allocation Grants"* -- formula money only, by
DESE's own page title. Who WON a competitive grant is published somewhere else, and this
fetches it.

THE SOURCE. https://www.doe.mass.edu/grants/awards.html, "Grant Allocations & Awards", links
two listings under the heading *Competitive Awards*:

    /grants/awards.aspx         current fiscal year, by fund code
    /grants/fy26-awards.html    FY2026, by fund code

Each row links ONE Word document per grant, `/grants/<FY>/awards/<code>.docx`, which prints
the program, `Funds Allocated`, `Funds Requested`, the number of proposals received and
recommended, and a Recipients | Amounts table. extract_dese_awards.py reads them.

ONLY TWO YEARS ARE PUBLISHED. `fy25-awards.html`, `fy24-` and `fy23-` redirect to DESE's 404
page (checked 23 October 2026). So the archive's copies are the only history of these that
will exist once FY2026's listing goes the same way, and every file is landed through
ingest.land_version(): a new version under a dated folder, the fixed name as the working copy.
Listings and documents were byte-stable between two fetches a minute apart (23 October 2026).

POLITE: one request a second, a User-Agent that says who is asking. About 40 requests.
"""
import argparse
import datetime
import hashlib
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import snapshot_log  # noqa: E402
from fetch_dese_grants import catalogue as _catalogue  # noqa: E402  (shared index writer)

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
BASE = 'https://www.doe.mass.edu'
KEYDIR = 'state-dese/awards'
LISTINGS = [('/grants/awards.aspx', 'awards.html', 'current fiscal year'),
            ('/grants/fy26-awards.html', 'fy26-awards.html', 'FY2026')]
LOG_ROOT = os.path.join(SRC, KEYDIR)
INDEX = os.path.join(SRC, 'state-dese', 'index.csv')
UA = {'User-Agent': 'lunenburgbudgetproject.org (public records archive of Lunenburg, MA; '
                    'DESE competitive grant awards)'}
PAUSE = 1.0
DOC = re.compile(r'href="(/grants/(\d{4})/awards/([^"/]+\.(?:docx|pdf|xlsx)))"', re.I)


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 -- retried, then reported
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError('%s: %s' % (url, last))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def held_sha(key):
    p = os.path.join(SRC, key)
    return sha(open(p, 'rb').read()) if os.path.exists(p) else None


def doc_key(fy, name):
    """`/grants/2026/awards/0181.docx` -> `state-dese/awards/fy2026/0181.docx`: the
    publisher's own filename, in a folder for the fiscal year its path names."""
    return '%s/fy%s/%s' % (KEYDIR, fy, name)


def catalogue(entries):
    """sources/state-dese/index.csv is shared; fetch_dese_grants.catalogue re-reads it,
    touches only the `local` paths passed, and preserves its newline convention."""
    _catalogue(entries)


def held_docs():
    out = []
    base = os.path.join(SRC, KEYDIR)
    for d in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if re.fullmatch(r'fy\d{4}', d):
            out += ['%s/%s/%s' % (KEYDIR, d, f) for f in sorted(os.listdir(os.path.join(base, d)))
                    if os.path.isfile(os.path.join(base, d, f))]
    return out


def check():
    import csv
    rows = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
    held = ['%s/%s' % (KEYDIR, k) for _, k, _ in LISTINGS] + held_docs()
    bad = []
    for k in held:
        r = rows.get('sources/' + k)
        if not os.path.exists(os.path.join(SRC, k)):
            bad.append('not on disk: sources/' + k)
        elif not r or not r['upstream'].startswith(BASE):
            bad.append('not catalogued with its DESE address: sources/' + k)
        elif r['sha256'] != held_sha(k):
            bad.append('catalogue sha256 is stale: sources/' + k)
    for local in rows:
        if local.startswith('sources/%s/' % KEYDIR) and not os.path.exists(os.path.join(ROOT, local)):
            bad.append('catalogued but not on disk: ' + local)
    for b in bad:
        print('  !!', b)
    print('%d held files, %d problems' % (len(held), len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    today = datetime.date.today().isoformat()
    files = {}
    for path, name, what in LISTINGS:
        url = BASE + path
        blob = fetch(url)
        files['%s/%s' % (KEYDIR, name)] = (url, blob, 'DESE competitive grant awards, %s, by fund '
                                                       'code (the listing)' % what)
        links = sorted(set(DOC.findall(blob.decode('utf-8', 'replace'))))
        if not links:
            raise SystemExit('fetch_dese_awards: %s links no award documents -- the page moved' % url)
        for href, fy, fname in links:
            key = doc_key(fy, fname)
            if key in files:
                continue
            time.sleep(PAUSE)
            files[key] = (BASE + href, fetch(BASE + href),
                          'DESE competitive grant award, FY%s, %s' % (fy, fname.rsplit('.', 1)[0]))
        time.sleep(PAUSE)
    print('%d files fetched (%d listings, %d award documents)'
          % (len(files), len(LISTINGS), len(files) - len(LISTINGS)))
    if a.dry_run:
        changed = [k for k, (_, b, _) in files.items() if held_sha(k) != sha(b)]
        print('dry run: %d of %d differ from what is held; nothing landed' % (len(changed), len(files)))
        return 0
    import ingest
    changed, failed, entries = [], [], []
    for key, (url, b, label) in files.items():
        if held_sha(key) != sha(b):
            ok, why = ingest.land_version(key, b, url)
            if not ok:
                failed.append('%s: %s' % (key, why))
                continue
            changed.append(key)
        entries.append(dict(label=label, upstream=url, local='sources/' + key, bytes=str(len(b)),
                            sha256=sha(b), read='html' if key.endswith('.html') else 'docx'))
    catalogue(entries)
    snapshot_log.record(LOG_ROOT, today, bool(changed), today if changed else '', files=len(files),
                        note='%d files; %d new or changed%s'
                        % (len(files), len(changed), '; %d FAILED' % len(failed) if failed else ''))
    print('%d of %d new or changed and landed; %d failed' % (len(changed), len(files), len(failed)))
    for f in failed:
        print('  !!', f)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
