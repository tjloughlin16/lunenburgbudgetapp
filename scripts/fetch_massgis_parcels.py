#!/usr/bin/env python3
"""THE PARCELS: MassGIS's Level 3 assessors' parcels for Lunenburg (town 162), landed
through `ingest` whenever MassGIS publishes a new edition.

    python3 scripts/fetch_massgis_parcels.py           # fetch; land it if it is new
                                                       #   (the refresh runs exactly this)
    python3 scripts/fetch_massgis_parcels.py --check   # every edition held matches the
                                                       #   manifest and opens; no network

WHY. The parcel package -- polygons, and the town assessor's own CAMA extract for one fiscal
year -- is what /property-owners and the homes-and-taxes pages are computed from. It was
downloaded once, by hand, on 13 September 2026 (sources/state-massgis/PROVENANCE.md), and
nothing looked at it again. MassGIS does not keep editions: it OVERWRITES the one file at
its one address. Checked 28 October 2026: the address now answers with a different file
(Last-Modified 29 September 2026, 1,870,921 bytes against our 1,697,201), whose assessing
table is `M162Assess_CY26_FY27.dbf` where ours is `..._FY26.dbf`. The FY2026 edition is
gone from MassGIS, and our copy is now the only one. That is the reason this exists: an
edition not taken while it is up is not available afterwards.

ONE ADDRESS, DIRECTLY. The file is on MassGIS's public S3 bucket, and the address is the
file itself, as rule 12 wants -- not the data page that lists it
(https://www.mass.gov/info-details/massgis-data-property-tax-parcels).

A NEW EDITION LANDS BESIDE THE ONE THE PAGES READ, AND DOES NOT REPLACE IT. Each new edition
is landed with `ingest.land()` under `state-massgis/<date>/L3_SHP_M162_LUNENBURG.zip`, the
dated folder that archive_storage freezes and build_source_index.py already treats as an
edition of the catalogued file. The plain name is NOT rewritten, which is the one way this
differs from `ingest.land_version()`, and on purpose: build_property_owners.py reads the
member `M162Assess_CY26_FY26.dbf` from the plain name and sets `FY_NOW = 2026`, and
PROVENANCE.md describes that file as FY2026. Swapping FY2027 in underneath them
unattended would break the first and make the other two wrong. Moving the pages to a new
fiscal year is a decision about the pages, so the run says when one is waiting and leaves
it to a person.

IDEMPOTENT. MassGIS serves a static object, so the bytes are the test: an edition whose
sha256 we already hold -- at the plain name or under any date -- lands nothing. Exit 0
means it looked, changed or not; non-zero only means it could not.

One request, about 1.9 MB.
"""
import argparse
import csv
import datetime
import glob
import hashlib
import io
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
MANIFEST = os.path.join(SRC, 'data', 'archive-manifest.csv')

KEY = 'state-massgis/L3_SHP_M162_LUNENBURG.zip'
URL = ('https://s3.us-east-1.amazonaws.com/download.massgis.digital.mass.gov/shapefiles/'
       'l3parcels/L3_SHP_M162_LUNENBURG.zip')
UA = {'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org research)'}
# A version is `state-massgis/<YYYY-MM-DD>/L3_SHP_M162_LUNENBURG.zip`, or with the first
# eight of its sha256 after the stem for a second new edition on one day.
VERSION = re.compile(r'^state-massgis/\d{4}-\d{2}-\d{2}/L3_SHP_M162_LUNENBURG(-[0-9a-f]{8})?\.zip$')


def fail(msg):
    raise SystemExit('fetch_massgis_parcels: ' + msg)


def edition(blob):
    """The fiscal year the package says it is, read off its assessing table's NAME
    (`M162Assess_CY26_FY27.dbf`), or why the blob is not a parcel package at all. S3
    answers a missing key with XML, and the ingest sniff would refuse that anyway; this
    also refuses a zip that is not the package, before anything is kept."""
    try:
        names = zipfile.ZipFile(io.BytesIO(blob)).namelist()
    except zipfile.BadZipFile:
        return None, 'not a zip'
    hit = [n for n in names if re.search(r'/M162Assess_CY\d{2}_FY\d{2}\.dbf$', n)]
    if len(hit) != 1:
        return None, 'no single M162Assess_*.dbf in it (%d members)' % len(names)
    return 'FY20' + hit[0][-6:-4], ''


def manifest():
    with open(MANIFEST, encoding='utf-8') as fh:
        return {r['key']: r['sha256'] for r in csv.DictReader(fh) if r.get('key')}


def held():
    """{sha256: key} for every edition we hold: the plain name and each dated version, from
    the manifest -- which names what the BUCKET holds, so a clone missing a file on disk
    does not land it twice."""
    return {s: k for k, s in manifest().items() if k == KEY or VERSION.match(k)}


def run():
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=120) as r:
            blob, modified = r.read(), r.headers.get('Last-Modified', '?')
    except (urllib.error.URLError, TimeoutError) as e:
        fail('%s: %s' % (URL, e))
    fy, why = edition(blob)
    if not fy:
        fail('%s did not answer with the parcel package: %s' % (URL, why))
    sha = hashlib.sha256(blob).hexdigest()
    have = held()
    reading = edition(open(os.path.join(SRC, KEY), 'rb').read())[0] \
        if os.path.exists(os.path.join(SRC, KEY)) else None
    if sha in have:
        print('same  %s %s (%s, Last-Modified %s) -- held as %s'
              % (fy, sha[:12], '{:,} bytes'.format(len(blob)), modified, have[sha]))
        if reading and fy != reading:
            print('NOTICE: MassGIS publishes %s; the pages still read the %s edition at %s.'
                  % (fy, reading, KEY))
        return 0
    import ingest
    day = datetime.date.today().isoformat()
    dated = 'state-massgis/%s/L3_SHP_M162_LUNENBURG.zip' % day
    if dated in manifest() or glob.glob(os.path.join(SRC, dated)):
        dated = 'state-massgis/%s/L3_SHP_M162_LUNENBURG-%s.zip' % (day, sha[:8])
    ok, why = ingest.land(dated, blob, upstream=URL)
    if not ok:
        fail('%s: %s' % (dated, why))
    print('landed %s: %s %s (%s, Last-Modified %s)'
          % (dated, fy, sha[:12], '{:,} bytes'.format(len(blob)), modified))
    if reading and fy != reading:
        print('NOTICE: a new edition, %s, is held at %s; the pages still read the %s edition '
              'at %s. Moving them is a decision -- see the docstring.' % (fy, dated, reading, KEY))
    return 0


def check():
    import archive_storage as A
    man, bad, n = manifest(), [], 0
    for k in sorted(k for k in man if k == KEY or VERSION.match(k)):
        p = os.path.join(SRC, k)
        if not os.path.exists(p):
            bad.append('%s not on disk; sync_archive.py --pull' % k)
            continue
        if A.hash_file(p)[0] != man[k]:
            bad.append('%s does not match its manifest row' % k)
            continue
        fy, why = edition(open(p, 'rb').read())
        if not fy:
            bad.append('%s: %s' % (k, why))
            continue
        print('ok    %s  %s' % (k, fy))
        n += 1
    if KEY not in man:
        bad.append('%s is not in the manifest' % KEY)
    if bad:
        fail('\n  '.join([''] + bad))
    print('fetch_massgis_parcels: %d edition(s) held, hashed and readable' % n)
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    sys.exit(check() if a.check else run())
