#!/usr/bin/env python3
"""Finding and fetching annual town reports, exercised. No network, nothing outside build/.

    python3 scripts/test_annual_report_fetch.py      # exit 0 when every case holds

Phase P1 of notes/PLAN-ANNUAL-REPORT-PIPELINE.md. Four things, each of which was wrong on
27 October 2026:

  1. THE YEAR. `report_year()` against labels the town has actually written -- every item in
     the ArchiveCenter's Annual Town Reports category (AMID 52) and every DocumentCenter
     report, read off the live listings that day -- and the older forms the reports back to
     the 1980s are expected to take. `FY85` used to become 2085.
  2. THE SHELF. Every real label still routes where it did, and a report titled only by year
     now routes to town-annual-reports/ instead of town-supplementary/.
  3. A CRAWL, end to end, through fetch_town_docs.main() with the town and the bucket stood
     in for: an older report is filed under town-annual-reports/ with its address.
  4. SAME BYTES, NEW ADDRESS. A fetched file whose sha256 the archive holds adds an address
     to the held copy's row and creates no file, no row and no object; the next crawl does
     not even download it. Run against the real 2000 report when this tree holds it.
"""
import csv
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402
import fetch_town_docs as F  # noqa: E402
from report_year import report_year  # noqa: E402
from town_document_home import home  # noqa: E402

SANDBOX = os.path.join(ROOT, 'build', 'test-annual-report-fetch', str(os.getpid()))
FAILS = []

# label, year, basis -- and where the label was seen. `None` means no single year.
LABELS = [
    # ArchiveCenter, Annual Town Reports (AMID 52), live listing 27 October 2026: ADID, label.
    *[(f'FY{yy:02d} Annual Town Report (PDF)', 2000 + yy, 'fiscal') for yy in range(11, 26)],
    # DocumentCenter, linked from /838/Annual-Town-Reports, 4117-4132.
    *[(f'FY {y} Annual Town Report', y, 'fiscal') for y in range(2011, 2026)],
    ('FY 2016 Annual Town Report, Addendum', 2016, 'fiscal'),
    # Other real labels off the same crawl, which the parser must not misread.
    ('9.30.25 FY27 Preliminary Budget Presentation (PDF)', 2027, 'fiscal'),
    ('FY24-FY33: Capital Plan', None, None),
    ('II. Attachment A - Police Budget As Expended FY15-FY23', None, None),
    ('3/25/2024 Presentation: How Can We Help You- Property Tax Exemptions', 2024, 'calendar'),
    ('FY27 DETAIL RATES', 2027, 'fiscal'),
    # The forms the older uploads are expected to take (P1's brief). Not yet seen on the
    # town's site: the Select Board chair is uploading them now.
    ('FY85 Annual Town Report', 1985, 'fiscal'),
    ('FY 85 Annual Town Report', 1985, 'fiscal'),
    ('FY1985 Annual Town Report', 1985, 'fiscal'),
    ('FY-1999 Annual Town Report', 1999, 'fiscal'),
    ('FY00 Annual Town Report', 2000, 'fiscal'),
    ('FY49 Annual Town Report', 2049, 'fiscal'),
    ('FY50 Annual Town Report', 1950, 'fiscal'),
    ('1985', 1985, 'calendar'),
    ('Town Report 1985', 1985, 'calendar'),
    ('Town Report 2000', 2000, 'calendar'),
    ('Annual Town Report 1999-2000', 2000, 'fiscal'),
    ('Annual Town Report 1999-00', 2000, 'fiscal'),
    ('Town Report 1987-1989', None, None),
    ('Annual Town Report', None, None),
]

# label, category, folder
ROUTES = [
    *[(f'FY{yy:02d} Annual Town Report (PDF)', 'Annual Town Reports', 'town-annual-reports')
      for yy in range(11, 26)],
    ('Town Report 1985', '', 'town-annual-reports'),
    ('Town Report 2000', 'Annual Town Reports', 'town-annual-reports'),
    ('Lunenburg 1987', 'Annual Town Reports', 'town-annual-reports'),
    ('Town Reports 1990', '', 'town-annual-reports'),
    ('Town Manager Report January 2025', '', 'town-supplementary'),
    ('Town Report', '', 'town-supplementary'),
    ('FY27 Preliminary Budget Presentation (PDF)', 'FY25 Town Meeting and Budget Documents',
     'town-budget'),
]


def check(ok, what):
    print(('  ok    ' if ok else '  FAIL  ') + what)
    if not ok:
        FAILS.append(what)


def test_years():
    print('report_year: %d labels' % len(LABELS))
    for label, year, basis in LABELS:
        got = report_year(label)
        want = None if year is None else (year, basis)
        check((got[:2] if got else None) == want, '%-58r -> %s' % (label, got[:2] if got else None))


def test_routes():
    print('home: %d labels, and every label the three town mirrors already hold' % len(ROUTES))
    for label, cat, folder in ROUTES:
        check(home(label, cat) == folder, '%-45r %-24r -> %s' % (label, cat, folder))
    # The widening only decides annual report or not, so that is what is asserted. Three
    # held labels already sit outside their routed folder (two board pages written by
    # fetch_board_pages.py, one presentation kept where it was first filed), and they are
    # not this rule's business.
    moved = []
    for f in ('town-budget', 'town-supplementary', 'town-annual-reports'):
        for r in F.read_index(os.path.join(ROOT, 'sources', f, 'index.csv')):
            if (home(r['label']) == 'town-annual-reports') != (f == 'town-annual-reports'):
                moved.append((f, r['label']))
    check(not moved, 'every held label is still an annual report or not, as filed (%d changed)'
          % len(moved))
    check(F.dedupe_key('FY85 Annual Town Report (PDF)') == F.dedupe_key('FY 1985 Annual Town Report')
          == 'fy1985annualtownreport', 'dedupe_key: FY85 is fy1985, not fy2085')


# --- the crawl, with the town and the bucket stood in for ---------------------------------

class Stand:
    """fetch_town_docs pointed at a sandbox: its own sources/, manifest and listing."""

    def __init__(self):
        shutil.rmtree(SANDBOX, ignore_errors=True)
        self.src = os.path.join(SANDBOX, 'sources')
        os.makedirs(os.path.join(self.src, 'data'))
        self.manifest = os.path.join(self.src, 'data', 'archive-manifest.csv')
        A.write_manifest([], self.manifest)
        self.listing, self.bodies, self.fetched, self.staged = [], {}, [], []
        self.saved = dict(F_ROOT=F.ROOT, A_SRC=A.SRC, A_MANIFEST=A.MANIFEST,
                          discover=F.discover, get=F.get, extract=F.extract,
                          stage=F.ingest.stage, secure=F.ingest.secure, argv=sys.argv)
        F.ROOT, A.SRC, A.MANIFEST = SANDBOX, self.src, self.manifest
        F.discover = lambda: list(self.listing)
        F.get = self.get
        F.extract = lambda path, out, ocr=True: 'test: not read'
        F.ingest.stage = self.stage
        F.ingest.secure = self.secure
        sys.argv = ['fetch_town_docs.py']

    def get(self, url):
        self.fetched.append(url)
        return self.bodies[url], 'application/pdf'

    def stage(self, key, blob, upstream=''):
        self.staged.append((key, blob))
        return True, ''

    def secure(self, quiet=False):
        # What a successful push leaves behind: the bytes at their archival path.
        for key, blob in self.staged:
            os.makedirs(os.path.dirname(A.local_path(key)), exist_ok=True)
            open(A.local_path(key), 'wb').write(blob)
        return len(self.staged), 0

    def hold(self, key, blob, label, upstream=''):
        """A document the archive already holds, catalogued in its folder's index."""
        top = key.split('/')[0]
        path = A.local_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(blob)
        idx = os.path.join(self.src, top, 'index.csv')
        with open(idx, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=['label', 'upstream', 'local', 'text', 'bytes',
                                               'sha256', 'read'])
            w.writeheader()
            w.writerow({'label': label, 'upstream': upstream, 'local': 'sources/' + key,
                        'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()})
        m = A.read_manifest(self.manifest)
        m[key] = {'key': key, 'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
                  'etag_md5': '', 'upstream': upstream}
        A.write_manifest(list(m.values()), self.manifest)

    def run(self):
        self.staged = []
        F.main()

    def index(self, top):
        return F.read_index(os.path.join(self.src, top, 'index.csv'))

    def close(self):
        s = self.saved
        F.ROOT, A.SRC, A.MANIFEST = s['F_ROOT'], s['A_SRC'], s['A_MANIFEST']
        F.discover, F.get, F.extract = s['discover'], s['get'], s['extract']
        F.ingest.stage, F.ingest.secure, sys.argv = s['stage'], s['secure'], s['argv']
        shutil.rmtree(SANDBOX, ignore_errors=True)


def test_older_report_is_filed():
    print('a crawl files an older report')
    t = Stand()
    try:
        url = F.BASE + '/ArchiveCenter/ViewFile/Item/250'
        t.listing = [dict(id='a250', label='Town Report 1985', url=url,
                          category='Annual Town Reports')]
        t.bodies[url] = b'%PDF-1.4\n% the 1985 town report, stood in for\n'
        t.run()
        key = 'town-annual-reports/docs/a250-town-report-1985.pdf'
        check([k for k, _ in t.staged] == [key], 'staged through ingest as ' + key)
        check(os.path.exists(A.local_path(key)), 'filed under town-annual-reports/ only after secure()')
        rows = t.index('town-annual-reports')
        check([(r['local'], r['upstream']) for r in rows] == [('sources/' + key, url)],
              'catalogued with its address')
        y = report_year(rows[0]['label']) if rows else None
        check(y is not None and y[:2] == (1985, 'calendar'), 'its year: %s' % (y,))
    finally:
        t.close()


def test_same_bytes_new_address():
    real = 'correspondence/2026-10-27-2000-annual-town-report-select-board-chair.pdf'
    path = os.path.join(ROOT, 'sources', real)
    if os.path.exists(path):
        key, blob = real, open(path, 'rb').read()
        print('same bytes, new address: the real 2000 report (%s)' % hashlib.sha256(blob).hexdigest()[:12])
    else:
        key, blob = 'correspondence/2000-report.pdf', b'%PDF-1.4\n% 2000, stood in for\n'
        print('same bytes, new address: a stand-in (this tree does not hold the 2000 report)')
    t = Stand()
    try:
        t.hold(key, blob, 'Town Report 2000, sent by the Select Board chair')
        url = F.BASE + '/ArchiveCenter/ViewFile/Item/260'
        t.listing = [dict(id='a260', label='Town Report 2000', url=url, category='Annual Town Reports')]
        t.bodies[url] = blob
        objects = len(A.read_manifest(t.manifest))
        t.run()
        rows = t.index('correspondence')
        check(rows[0]['upstream'] == url, 'the address is appended to the held copy\'s row')
        check(t.staged == [], 'nothing staged, so nothing pushed and no object')
        check(len(A.read_manifest(t.manifest)) == objects, 'the manifest holds no new key')
        check(not os.listdir(os.path.join(t.src, 'town-annual-reports', 'docs')),
              'no second file under town-annual-reports/')
        check(t.index('town-annual-reports') == [], 'no new row: one document, one row')
        before = len(t.fetched)
        t.run()
        check(len(t.fetched) == before, 'the next crawl does not download it again')
        check(t.index('correspondence')[0]['upstream'] == url, 'and records the address once')
    finally:
        t.close()


def test_held_but_uncatalogued():
    print('same bytes as a document the bucket holds and no index names')
    t = Stand()
    try:
        blob = b'%PDF-1.4\n% landed, not yet catalogued\n'
        key = 'correspondence/landed.pdf'
        m = {key: {'key': key, 'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
                   'etag_md5': '', 'upstream': ''}}
        A.write_manifest(list(m.values()), t.manifest)
        url = F.BASE + '/ArchiveCenter/ViewFile/Item/261'
        t.listing = [dict(id='a261', label='Town Report 2001', url=url, category='Annual Town Reports')]
        t.bodies[url] = blob
        t.run()
        check(t.staged == [] and t.index('town-annual-reports') == [],
              'still not filed twice; the run says the address was not recorded')
    finally:
        t.close()


def test_address_survives_rewrite():
    print('an address, and a row, recorded on an earlier run survive the index rewrite')
    t = Stand()
    try:
        blob = b'%PDF-1.4\n% FY25\n'
        key = 'town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf'
        dc, old = F.BASE + '/DocumentCenter/View/4130', F.BASE + '/ArchiveCenter/ViewFile/Item/213'
        t.hold(key, blob, 'FY 2025 Annual Town Report', upstream=dc + ' ' + old)
        t.listing = [dict(id='4130', label='FY 2025 Annual Town Report', url=dc, category='')]
        t.run()
        check(t.index('town-annual-reports')[0]['upstream'] == dc + ' ' + old,
              'the ArchiveCenter address is kept although today\'s listing lacks it')
        t.listing = []
        t.run()
        check([r['local'] for r in t.index('town-annual-reports')] == ['sources/' + key],
              'and the row is kept when the listing stops linking it at all')
    finally:
        t.close()


def main():
    test_years()
    test_routes()
    test_older_report_is_filed()
    test_same_bytes_new_address()
    test_held_but_uncatalogued()
    test_address_survives_rewrite()
    print()
    if FAILS:
        print('%d FAILED' % len(FAILS))
        return 1
    print('every case holds')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
