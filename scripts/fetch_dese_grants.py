#!/usr/bin/env python3
"""DESE's CURRENT GRANT FUNDING OPPORTUNITIES: the list, and every program's own page.

    python3 scripts/fetch_dese_grants.py --if-changed   # what the weekly refresh runs
    python3 scripts/fetch_dese_grants.py --dry-run      # fetch and parse, land nothing
    python3 scripts/fetch_dese_grants.py --check        # every held page is catalogued

TJ, 22 October 2026: *"the state or other resources have to post GRANTS somewhere... I want
to create a fetcher and a page that lists available grants to Lunenburg. This page I hope to
post the schools at to know they should be applying."*

THE SOURCE. https://www.doe.mass.edu/grants/grants.aspx -- "Find All Current Grant Funding
Opportunities" -- is one plain HTML table: fund code, program name, date posted, date due,
grant type, state or federal, program unit, contact. Each program links to its own page,
`/grants/<FY>/<code>/`, which carries the Purpose, the Eligibility, the Funding and the
Date Due as a definition list.

IT IS CURRENT-ONLY. There is no fiscal-year parameter and no history: a program that closes
leaves the list and its page is eventually replaced by next year's. So THE ARCHIVE'S
SNAPSHOTS ARE THE ONLY HISTORY OF WHAT DESE OFFERED, and every page is kept on change.

ON CHANGE, NOT ON EVERY LOOK. DESE overwrites these pages in place, and the pages are
byte-stable between requests (checked 22 October 2026: the list and a detail page each
fetched twice, identical sha256). So each page goes through `ingest.land_version()`: a NEW
version is landed -- staged, pushed, read back, catalogued -- under a dated folder beside
the fixed name, and the fixed name is the working copy the extractor reads. An unchanged
page lands nothing. Every run appends a row to `sources/state-dese/grants/checked.csv`
whether or not anything moved (snapshot_log), so "nothing changed since July" is
distinguishable from "nobody looked". `--if-changed` names that behaviour for the refresh;
it is the only behaviour this script has, because land_version never lands a duplicate.

POLITE: one request a second, a User-Agent that says who is asking. About 75 requests.
"""
import argparse
import csv
import datetime
import hashlib
import html as H
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import snapshot_log  # noqa: E402

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
BASE = 'https://www.doe.mass.edu'
LIST_URL = BASE + '/grants/grants.aspx'
KEYDIR = 'state-dese/grants'
LIST_KEY = KEYDIR + '/grants.html'
DETAIL_DIR = KEYDIR + '/detail'
LOG_ROOT = os.path.join(SRC, KEYDIR)
INDEX = os.path.join(SRC, 'state-dese', 'index.csv')
UA = {'User-Agent': 'lunenburgbudgetproject.org (public records archive of Lunenburg, MA; '
                    'weekly check of DESE current grant opportunities)'}
PAUSE = 1.0


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 -- retried, then reported
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError('%s: %s' % (url, last))


def _text(fragment):
    """Visible text of an HTML fragment. DESE writes every abbreviation twice -- a
    `visually-hidden` expansion and the `<abbr>` -- so the hidden half is dropped first, or
    "DESE" reads "Department of Elementary and Secondary Education DESE"."""
    s = re.sub(r'<span class="visually-hidden">.*?</span>', '', fragment, flags=re.S)
    s = re.sub(r'<(script|style)\b.*?</\1>', '', s, flags=re.S)
    s = re.sub(r'<br\s*/?>|</p>|</li>|</div>', '\n', s)
    s = re.sub(r'<li\b[^>]*>', '\n- ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = H.unescape(s).replace('\xa0', ' ')
    lines = [re.sub(r'[ \t\r\f\v]+', ' ', ln).strip() for ln in s.split('\n')]
    return '\n'.join(ln for ln in lines if ln)


def parse_list(page):
    """Rows of the current-grants table, in the order printed. Refuses a page whose table
    is missing or whose header has moved, rather than reading the wrong columns."""
    m = re.search(r'<table[^>]*id="[^"]*currentGrant"[^>]*>(.*?)</table>', page, re.S)
    if not m:
        raise ValueError('the current-grants table is not on the page')
    table = m.group(1)
    head = [_text(h).replace('▲', '').replace('▼', '').strip()
            for h in re.findall(r'<th\b[^>]*>(.*?)</th>', table, re.S)]
    want = ['Fund Code', 'Program Name', 'Date Posted', 'Date Due', 'Grant Type',
            'Type of Funding', 'Program Unit', 'Contact']
    if head != want:
        raise ValueError('the table header changed: %r' % head)
    rows = []
    for tr in re.findall(r'<tr>(.*?)</tr>', table, re.S):
        cells = re.findall(r'<td\b[^>]*>(.*?)</td>', tr, re.S)
        if len(cells) != len(want):
            continue
        href = re.search(r'href="([^"]+)"', cells[1]) or re.search(r'href="([^"]+)"', cells[0])
        r = dict(zip(want, (_text(c) for c in cells)))
        r['href'] = H.unescape(href.group(1)) if href else ''
        rows.append(r)
    if not rows:
        raise ValueError('the current-grants table has no rows')
    return rows


def detail_url(href):
    return href if href.startswith('http') else BASE + href


def detail_key(href):
    """`/grants/2027/0005-0006-7061-9611/` -> `.../detail/2027-0005-0006-7061-9611.html`.
    Only DESE's own /grants/ pages are fetched; anything else is left as a link."""
    m = re.match(r'^(?:https?://www\.doe\.mass\.edu)?/grants/([^?#]+?)/?$', href)
    if not m:
        return None
    slug = re.sub(r'[^A-Za-z0-9]+', '-', m.group(1)).strip('-').lower()
    return '%s/%s.html' % (DETAIL_DIR, slug)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def held_sha(key):
    p = os.path.join(SRC, key)
    return sha(open(p, 'rb').read()) if os.path.exists(p) else None


def catalogue(entries):
    """Add or refresh this script's rows in sources/state-dese/index.csv. The file is SHARED
    with other DESE fetchers, so it is re-read immediately before writing, only our own
    `local` paths are touched, and it is replaced atomically with its newline convention."""
    raw = open(INDEX, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8', newline='')))
    cols = list(rows[0].keys())
    ours = {e['local'] for e in entries}
    rows = [r for r in rows if r['local'] not in ours] + \
        [{c: e.get(c, '') for c in cols} for e in entries]
    tmp = INDEX + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator=nl)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, INDEX)


def check():
    """Every working copy held is catalogued with its upstream, and every catalogued one is
    held. Exit 1 otherwise."""
    rows = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
    bad = []
    held = [LIST_KEY] + ['%s/%s' % (DETAIL_DIR, f)
                         for f in sorted(os.listdir(os.path.join(SRC, DETAIL_DIR)))
                         if f.endswith('.html')] if os.path.isdir(os.path.join(SRC, DETAIL_DIR)) else []
    for k in held:
        r = rows.get('sources/' + k)
        if not r or not r['upstream'].startswith(BASE):
            bad.append('not catalogued with its DESE address: sources/' + k)
        elif r['sha256'] != held_sha(k):
            bad.append('catalogue sha256 is stale: sources/' + k)
    for local in rows:
        if local.startswith('sources/' + KEYDIR + '/') and not os.path.exists(os.path.join(ROOT, local)):
            bad.append('catalogued but not on disk: ' + local)
    for b in bad:
        print('  !!', b)
    print('%d held pages, %d problems' % (len(held), len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--if-changed', action='store_true',
                    help='land a version only when its bytes changed (always the behaviour)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    import ingest

    today = datetime.date.today().isoformat()
    blob = fetch(LIST_URL)
    rows = parse_list(blob.decode('utf-8', 'replace'))
    pages = {LIST_KEY: (LIST_URL, blob, 'DESE current grant funding opportunities (the list)')}
    seen = set()
    for r in rows:
        key = detail_key(r['href'])
        if not key or key in seen:
            continue
        seen.add(key)
        time.sleep(PAUSE)
        url = detail_url(r['href'])
        try:
            b = fetch(url)
        except RuntimeError as e:
            print('  !! %s' % e)
            continue
        pages[key] = (url, b, 'DESE grant program page: %s (fund code %s)'
                      % (r['Program Name'], r['Fund Code']))
    print('%d programs listed, %d program pages fetched' % (len(rows), len(pages) - 1))
    if a.dry_run:
        changed = [k for k, (_, b, _) in pages.items() if held_sha(k) != sha(b)]
        print('dry run: %d of %d pages differ from what is held; nothing landed'
              % (len(changed), len(pages)))
        return 0

    changed, failed, entries = [], [], []
    for key, (url, b, label) in pages.items():
        before = held_sha(key)
        if before != sha(b):
            ok, why = ingest.land_version(key, b, url)
            if not ok:
                failed.append('%s: %s' % (key, why))
                continue
            changed.append(key)
        entries.append(dict(label=label, upstream=url, local='sources/' + key,
                            bytes=str(len(b)), sha256=sha(b), read='html'))
    catalogue(entries)
    snapshot_log.record(LOG_ROOT, today, bool(changed), today if changed else '',
                        files=len(pages),
                        note='%d programs; %d pages changed%s'
                        % (len(rows), len(changed), '; %d FAILED' % len(failed) if failed else ''))
    print('%d of %d pages new or changed and landed; %d failed' % (len(changed), len(pages), len(failed)))
    for f in failed:
        print('  !!', f)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
