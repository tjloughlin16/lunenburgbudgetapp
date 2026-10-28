#!/usr/bin/env python3
"""DESE's Special Education Direct Expenditure Trends workbook: land it, catalogue it.

    python3 scripts/fetch_dese_sped_expenditure.py           # fetch, validate, land, catalogue
    python3 scripts/fetch_dese_sped_expenditure.py --check   # held, catalogued, sha256 holds

WHAT IT IS

`direct-expenditure-trends.xlsx`, linked as *Special Education Direct Expenditure Trends* on
DESE's RADAR page (https://www.doe.mass.edu/research/radar/default.html). The old address
for this material, doe.mass.edu/finance/statistics/, now says *This page has moved* and
points at RADAR; /finance/statistics/per-pupil-exp.html answers 404. Checked 25 October 2026.

It is the only district-level SPECIAL EDUCATION spending series DESE publishes that this
project has found: per district, FY2008-FY2025, the special education share of each
district's End of Year Report spending, split into in-district (teaching, other
instructional, in-district transportation), out-of-district (Massachusetts public schools
and collaboratives, private and out-of-state schools, out-of-district transportation) and
other (non-public health services, grants and revolving funds), beside the district's
total expenditures.

WHAT IT IS NOT

A per-pupil figure. The workbook prints dollars only -- no count of students with
disabilities anywhere in it. A per-child figure needs a denominator from a different DESE
file (dese-sped-program.csv / dese-sped-indicator.csv), and dividing one by the other is
OUR derivation, to be labelled as such.

AN EDITION, NOT A FIXED FILE

DESE overwrites this workbook in place each year (this one is dated 12 May 2026 in its own
cell M1 and covers FY08-FY25). So the key carries the edition, and next year's edition
lands beside it under a new key rather than replacing it -- an R2 object cannot be
corrected, only superseded. The publisher's own filename is recorded in the catalogue
label, because that is what somebody asks DESE for when the link moves.

RUN UNATTENDED, so every outcome of a look is one of three, and only a failure to look exits
non-zero:

  * the same bytes as the edition held -- nothing lands, exit 0;
  * the same edition (same title) with different bytes -- DESE corrected it in place. The new
    bytes are archived as a dated version beside it (`state-dese/<YYYY-MM-DD>/<name>`) and
    the edition key, which the extractor reads, is left alone; exit 0, and said;
  * a NEW edition (the title names a later FY span) -- landed under its own key, computed
    from that title, and catalogued; extract_dese_sped_expenditure.py and the registry still
    read the old one until a person repoints them; exit 0, and said every run until then.

The file is byte-stable between requests (two fetches on 28 October 2026, sha256 c889a197...,
identical to ours; Last-Modified 22 May 2026), so a byte comparison is the right one here.
"""
import argparse
import csv
import hashlib
import io
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
SRC = os.path.join(ROOT, 'sources')
INDEX = os.path.join(SRC, 'state-dese', 'index.csv')

URL = 'https://www.doe.mass.edu/research/radar/direct-expenditure-trends.xlsx'
PAGE = 'https://www.doe.mass.edu/research/radar/default.html'
PUBLISHER_NAME = 'direct-expenditure-trends.xlsx'
KEY = 'state-dese/radar-sped-direct-expenditure-trends-fy2008-fy2025.xlsx'
EDITION_TITLE = 'Direct Special Education Expenditures, FY08 to FY25'
LABEL = ('DESE RADAR Special Education Direct Expenditure Trends, FY2008-FY2025 -- special '
         'education spending in district, out of district and from grants, every district; '
         'publisher filename direct-expenditure-trends.xlsx, linked from ' + PAGE)

UA = {'User-Agent': ('Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; '
                     '+https://lunenburgbudgetproject.org)')}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fetch():
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as res:
        return res.read()


def validate(blob):
    """It is a workbook with a `data` sheet; returns the edition title it prints. A sign-in
    page must not be landed under any key."""
    if not blob.startswith(b'PK'):
        raise SystemExit('%s did not return a spreadsheet (%d bytes). Nothing landed.'
                         % (URL, len(blob)))
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True)
    if 'data' not in wb.sheetnames:
        raise SystemExit('no `data` sheet; sheets are %s. Nothing landed.' % wb.sheetnames)
    row2 = next(wb['data'].iter_rows(min_row=2, max_row=2, values_only=True))
    title = next((v for v in row2 if v is not None), None)
    wb.close()
    return title


EDITION = re.compile(r'Direct Special Education Expenditures, FY(\d\d) to FY(\d\d)$')


def key_for(title):
    """The key an edition lands under, read off the title it prints -- the same shape as KEY,
    so next year's `FY08 to FY26` becomes ...-fy2008-fy2026.xlsx without anybody typing it.
    A title of any other shape is refused: the workbook has changed and a person looks."""
    if title == EDITION_TITLE:
        return KEY
    m = EDITION.match(title or '')
    if not m:
        raise SystemExit('the workbook is titled %r, which is not the shape %r. Nothing '
                         'landed; the workbook has changed shape.' % (title, EDITION_TITLE))
    a, b = (2000 + int(x) for x in m.groups())
    return 'state-dese/radar-sped-direct-expenditure-trends-fy%d-fy%d.xlsx' % (a, b)


def held_sha(key):
    path = os.path.join(SRC, key)
    if os.path.exists(path):
        return sha(open(path, 'rb').read())
    import archive_storage as A
    return A.read_manifest().get(key, {}).get('sha256')


def catalogue(entry):
    """Add or refresh this script's row in sources/state-dese/index.csv. The file is
    SHARED with other DESE fetchers: re-read immediately before writing, only our own
    `local` is touched, newline convention preserved, replaced atomically."""
    raw = open(INDEX, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8', newline='')))
    cols = list(rows[0].keys())
    mine = {c: str(entry.get(c, '')) for c in cols}
    if mine in rows:
        return            # already exactly so: a shared file is not rewritten for nothing
    rows = [r for r in rows if r['local'] != entry['local']] + [mine]
    tmp = INDEX + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator=nl)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, INDEX)


def check():
    path = os.path.join(SRC, KEY)
    rows = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
    bad = []
    if not os.path.exists(path):
        bad.append('not on disk: sources/%s (run sync_archive.py --pull)' % KEY)
    r = rows.get('sources/' + KEY)
    if not r:
        bad.append('not catalogued: sources/' + KEY)
    elif r['upstream'] != URL:
        bad.append('catalogued with the wrong upstream: %s' % r['upstream'])
    elif os.path.exists(path) and r['sha256'] != sha(open(path, 'rb').read()):
        bad.append('catalogue sha256 is stale: sources/' + KEY)
    for b in bad:
        print('  !!', b)
    print('%s: %s' % (KEY, 'ok' if not bad else '%d problems' % len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    import ingest
    blob = fetch()
    title = validate(blob)
    key = key_for(title)
    have = held_sha(key)
    if have == sha(blob):
        print('%s: unchanged (sha256 %s)' % (key, have[:12]))
        return 0
    span = re.search(r'fy(\d{4})-fy(\d{4})\.xlsx$', key).groups()
    label = LABEL.replace('FY2008-FY2025', 'FY%s-FY%s' % span)
    if have:
        # The same edition, revised in place. The edition key cannot take new bytes, so this
        # version goes beside it, dated; the extractor goes on reading the key it was built
        # against until a person decides the revision should replace it.
        from fetch_dese_socrata import archive_version
        ok, why, dated = archive_version(key, blob, URL)
        if not ok:
            print('  !! %s: %s' % (dated, why))
            return 1
        catalogue(dict(label=label + ' -- revised in place; fetched %s'
                       % __import__('datetime').date.today().isoformat(),
                       upstream=URL, local='sources/' + dated, text='', bytes=str(len(blob)),
                       sha256=sha(blob), read='budget-workbooks'))
        print('REVISED IN PLACE: %s differs from the %s held; archived as %s. The extractor '
              'still reads the old bytes.' % (title, key, dated))
        return 0
    ok, why = ingest.land(key, blob, URL)
    if not ok:
        print('  !! %s: %s' % (key, why))
        return 1
    catalogue(dict(label=label, upstream=URL, local='sources/' + key, text='',
                   bytes=str(len(blob)), sha256=sha(blob), read='budget-workbooks'))
    print('landed %s  %d bytes  sha256 %s%s' % (key, len(blob), sha(blob),
                                               ('  (%s)' % why) if why else ''))
    if key != KEY:
        print('NEW EDITION: %r. extract_dese_sped_expenditure.py, build_dese_registry.py and '
              'KEY here still name %s; repoint them to %s.' % (title, KEY, key))
    return 0


if __name__ == '__main__':
    sys.exit(main())
