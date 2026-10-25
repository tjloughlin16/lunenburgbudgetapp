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
"""
import argparse
import csv
import hashlib
import io
import os
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
    """It is a workbook, and it is the edition this key names. A sign-in page, or next
    year's edition arriving at the same URL, must not be landed under this key."""
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
    if title != EDITION_TITLE:
        raise SystemExit('the workbook is titled %r, not %r. A new edition: give it a new '
                         'KEY and EDITION_TITLE rather than landing it under this one.'
                         % (title, EDITION_TITLE))


def catalogue(entry):
    """Add or refresh this script's row in sources/state-dese/index.csv. The file is
    SHARED with other DESE fetchers: re-read immediately before writing, only our own
    `local` is touched, newline convention preserved, replaced atomically."""
    raw = open(INDEX, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8', newline='')))
    cols = list(rows[0].keys())
    rows = [r for r in rows if r['local'] != entry['local']] + \
        [{c: entry.get(c, '') for c in cols}]
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
    validate(blob)
    ok, why = ingest.land(KEY, blob, URL)
    if not ok:
        print('  !! %s: %s' % (KEY, why))
        return 1
    catalogue(dict(label=LABEL, upstream=URL, local='sources/' + KEY, text='',
                   bytes=str(len(blob)), sha256=sha(blob), read='budget-workbooks'))
    print('landed %s  %d bytes  sha256 %s%s' % (KEY, len(blob), sha(blob),
                                               ('  (%s)' % why) if why else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
