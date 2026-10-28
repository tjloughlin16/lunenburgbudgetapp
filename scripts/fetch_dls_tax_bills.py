#!/usr/bin/env python3
"""The Division of Local Services' Average Single-Family Tax Bill, every year, our towns.

    python3 scripts/fetch_dls_tax_bills.py          # fetch, catalogue, extract
    python3 scripts/fetch_dls_tax_bills.py --check  # the extract still reproduces from the file

WHERE IT COMES FROM. The DLS Gateway report `AverageSingleTaxBill.SingleFamTaxBill_wRange`
-- the address TJ found on 13 September 2026 after the databank one this project had
carried for a month turned out to be dead. It is a Logi form: municipalities and fiscal
years are checkbox lists, and the Export Table button POSTs the same form to the page with
`rdReportFormat=NativeExcel`. That POST is what this script makes, so the address recorded
below is the whole of it: the page, the report, and the towns and years asked for. It
answered a plain request with a real workbook; the bot check that stops the OLD gateway
does not apply here.

WHAT THE FILE HOLDS, per municipality per fiscal year: total single-family assessed value,
the number of single-family parcels, the average single-family value, the average
single-family tax bill, the bill as a share of value, DOR income per capita, the bill as a
share of income, and the town's rank among the 351. FY1988 to the current year; the newest
year is a blank row until the town's rate is set.

Landed through ingest.land under sources/state-dls/, named by export_name, and extracted
to sources/data/dls-avg-tax-bill.csv with the columns as printed. A fetch whose workbook
says exactly what the extract's own source file says lands nothing and exits 0
(land_export), so the refresh can run it on a cadence.
"""
import argparse
import csv
import hashlib
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

PAGE = 'https://dls-gw.dor.state.ma.us/reports/rdpage.aspx?rdreport=averagesingletaxbill.singlefamtaxbill_wrange'
EXPORT = ('https://dls-gw.dor.state.ma.us/reports/rdPage.aspx?rdReport=AverageSingleTaxBill.SingleFamTaxBill_wRange'
          '&rdReportFormat=NativeExcel&rdExportTableID=tblSinglefamtaxbill&rdExportFilename=AvgSingleFamTaxBill'
          '&rdShowGridlines=True&rdExcelOutputFormat=Excel2007')
# Lunenburg and the towns this project already compares it with, plus the two cities it
# borders. The DLS form takes municipality NAMES as values.
# EVERY TOWN THAT SHARES A BORDER WITH LUNENBURG, plus the peers this project compares it
# with. The six neighbours are not a memory: they are computed from the Census TIGERweb
# boundary polygons held at `state-census/tigerweb-cousub-worcester-middlesex.json`, by
# shared boundary vertices -- Ashby, Fitchburg, Lancaster, Leominster, Shirley, Townsend.
#
# ASHBY WAS MISSING until 26 September 2026, so every comparison this project published
# covered five of its six neighbours while reading as though it covered them all.
# AND THE TOWNS BEHIND THE SCHOOLS LUNENBURG CHILDREN ACTUALLY LEAVE FOR, which is a
# different question from which towns resemble Lunenburg and is kept as a separate set in
# `build_town_comparison.py`. Gardner is a municipal destination; Bolton and Stow are the
# other members of Nashoba; Pepperell is the third member of North Middlesex. Together with
# the twelve above, every destination district that is a municipal or small regional school
# has a tax bill here for every town that funds it. The charters, the Commonwealth virtual
# schools and Montachusett's eighteen-town assessment do not, and cannot -- there is no one
# town's tax base behind them, which is a finding rather than a gap in this list.
TOWNS = ['Lunenburg', 'Ashby', 'Ayer', 'Groton', 'Littleton', 'Shirley', 'Townsend',
         'Westford', 'Leominster', 'Fitchburg', 'Lancaster', 'Harvard',
         'Gardner', 'Pepperell', 'Bolton', 'Stow']

# ONE FILE PER FETCH, NAMED FOR ITS DAY. The export used to overwrite a single
# `AvgSingleFamTaxBill.xlsx`, which stopped being possible the day these became FROZEN
# documents: the bucket refuses to overwrite an object for ten years, and the manifest
# refuses to record a frozen key whose bytes changed. An object cannot be corrected, only
# superseded under a new key -- so a re-fetch is a new document, which is also the truth of
# it, because DLS adds a fiscal year every cycle and a town whenever this list grows.
OUT_DIR = os.path.join(ROOT, 'sources', 'state-dls')


def export_name(stem, ext, blob, day=None):
    """The archive name for one Gateway export: `<stem>-<day>-<first twelve of its sha256><ext>`.

    WHY EVERY DLS EXPORT IS NAMED THIS WAY. These are FROZEN documents: the bucket refuses
    to overwrite an object for ten years and the manifest refuses to record a frozen key
    whose bytes changed. So a fetch that lands on a key already taken cannot be corrected --
    only superseded under a new key -- and on 26 September 2026 two fetches of the tax-bill
    report, one for twelve towns and one for sixteen, collided on a name carrying only the
    date. Nothing failed; the bytes on disk simply stopped being the bytes in the bucket,
    and only a hand-run sha256 said so.

    Hashing the content into the name makes collision impossible by construction: the same
    export fetched twice lands on the same key and is recognised as already held; a
    different export can never land on a key that is taken. It is rule 12's `our processed
    copy` and rule 13's `an instrument that reformats before you see it` in one filename.
    """
    import datetime
    stamp = day or datetime.date.today().isoformat()
    return '%s-%s-%s%s' % (stem, stamp, hashlib.sha256(blob).hexdigest()[:12], ext)


def newest_export(directory, stem, ext, legacy=None):
    """The most recently fetched export for a stem, by MODIFICATION TIME.

    Not by name: the name carries a content hash after the date, so two exports from one day
    sort by hash rather than by which arrived second. `legacy` is the fixed name used before
    this rule existed -- still a real export, still catalogued, and the answer when no
    hashed one has been fetched yet."""
    import glob
    found = glob.glob(os.path.join(directory, '%s-*%s' % (stem, ext)))
    if found:
        return max(found, key=os.path.getmtime)
    return os.path.join(directory, legacy or (stem + ext))


def export_content(src):
    """A fingerprint of what a Gateway export SAYS, blind to when the Gateway generated it.

    WHY NOT ITS SHA256. Measured 28 October 2026: the same cherry-sheet export fetched twice,
    eight seconds apart, came back with two different hashes -- and every one of its ten zip
    members byte-identical, to each other and to the copy fetched on 26 September. The only
    difference was the timestamp the Gateway stamps on each member as it zips. So a byte
    hash says every fetch is a new document, and a fetcher deduplicating on it would land
    the same workbook again on every run, forever, into a bucket that cannot delete it.

    What this hashes is each member's NAME and its UNCOMPRESSED BYTES, in name order. Any
    change to a cell, a header, a style or a sheet changes it; the zip's clock does not.
    `src` is a blob or a path."""
    import io
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(src) if isinstance(src, bytes) else src)
    h = hashlib.sha256()
    for name in sorted(z.namelist()):
        h.update(name.encode('utf-8') + b'\0' + hashlib.sha256(z.read(name)).digest())
    return h.hexdigest()


def current_export(extract_csv, directory, fallback):
    """The export the PUBLISHED extract was read from: what a new fetch is compared against.

    Taken from the extract's own `source_file` column rather than from `newest_export`,
    because modification time is not a record of anything -- a `sync_archive.py --pull`
    into a fresh tree stamps every file with the moment it arrived, in whatever order -- and
    the question a scheduled fetch asks is whether the figures on the site still match the
    publisher, which is a question about the file those figures came from."""
    if os.path.exists(extract_csv):
        with open(extract_csv, newline='', encoding='utf-8') as fh:
            first = next(csv.DictReader(fh), None)
        if first and first.get('source_file'):
            path = os.path.join(directory, first['source_file'])
            if os.path.exists(path):
                return path
    return fallback


def land_export(stem, ext, blob, upstream, current=None, check=None, directory=OUT_DIR):
    """Land one Gateway export through ingest.land, unless what it says is already held.

    Returns (key, changed), where `key` is the archive key holding this content.

      changed=False  it says exactly what `current` says -- the file the published extract
                     was read from. NOTHING is landed (not a second copy under today's
                     date, which is what `export_name` alone would produce, since its name
                     carries the day), and the caller leaves its extract as it is.
      changed=True   the extract has to be rebuilt from `key`. Usually `key` is newly
                     landed. But if some OTHER held export of this stem already says the
                     same thing, `key` is that one and nothing is landed: a run that landed
                     a change and then died before rewriting its extract must not land the
                     same content again the next morning, and neither must a figure DLS
                     moved and then moved back.

    `check(path)` is the caller's extract, run against the blob in a scratch file BEFORE it
    lands, so a workbook that does not reconcile is refused while that still costs nothing.
    After the push it would be permanent -- and on a schedule the next run would see the
    same change and try again. Refuses (SystemExit) if ingest does, because a document that
    could not be secured is a run that could not finish."""
    import glob
    import ingest
    import tempfile
    import zipfile
    mine = export_content(blob)
    if current and os.path.exists(current) and export_content(current) == mine:
        return 'state-dls/' + os.path.basename(current), False
    for path in sorted(glob.glob(os.path.join(directory, '%s-*%s' % (stem, ext)))):
        try:
            same = export_content(path) == mine
        except (zipfile.BadZipFile, OSError):
            continue
        if same:
            print('  already held as %s; nothing landed' % os.path.basename(path))
            return 'state-dls/' + os.path.basename(path), True
    key = 'state-dls/' + export_name(stem, ext, blob)
    if check is not None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, os.path.basename(key))
            with open(path, 'wb') as fh:
                fh.write(blob)
            check(path)
    ok, why = ingest.land(key, blob, upstream)
    if not ok:
        raise SystemExit('ingest.land refused %s: %s' % (key, why))
    print('  landed %s (%d bytes)%s' % (key, len(blob), ' -- ' + why if why else ''))
    return key, True


def out_xlsx(blob=None, day=None):
    """This report's export path. See `export_name` for why the sha is in the name."""
    if blob is None:
        return os.path.join(OUT_DIR, 'AvgSingleFamTaxBill.xlsx')
    return os.path.join(OUT_DIR, export_name('AvgSingleFamTaxBill', '.xlsx', blob, day))


def newest_xlsx():
    """The most recent export held. Every earlier one stays exactly as it was received."""
    return newest_export(OUT_DIR, 'AvgSingleFamTaxBill', '.xlsx',
                         legacy='AvgSingleFamTaxBill.xlsx')


OUT_CSV = os.path.join(ROOT, 'sources', 'data', 'dls-avg-tax-bill.csv')
INDEX = os.path.join(ROOT, 'sources', 'state-dls', 'index.csv')
COLS = ['dor_code', 'municipality', 'fy', 'sf_value_total', 'sf_parcels', 'avg_sf_value', 'avg_sf_bill',
        'bill_pct_of_value', 'income_per_capita', 'bill_pct_of_income', 'rank', 'source_file', 'sha256']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch():
    ua = {'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org research)', 'Referer': PAGE}
    page = urllib.request.urlopen(urllib.request.Request(PAGE, headers=ua), timeout=120).read().decode('utf-8', 'replace')
    years = sorted(set(re.findall(r'name="iclYear"[^>]*value="(\d+)"', page)))
    if len(years) < 30:
        raise SystemExit('the DLS form offered %d years; expected FY1988 onward' % len(years))
    offered = sorted({m for m in re.findall(r'name="iclMuni"[^>]*value="([^"]*)"', page) if m})
    missing = [t for t in TOWNS if t not in offered]
    if missing:
        raise SystemExit('the DLS form does not list %s' % missing)
    # EVERY MUNICIPALITY THE FORM OFFERS, not the sixteen named above. The named list stays
    # because other scripts import it and because the checks above prove the form still
    # knows each of them, but the ARCHIVE holds all 351 -- for the reason
    # `fetch_dls_property.py` gives beside health insurance: a peer set chosen in the
    # fetcher is a judgment baked into the archive, and a comparison that has to find the
    # towns resembling Lunenburg cannot be made from a file that only ever held twelve.
    if len(offered) < 340:
        raise SystemExit('the DLS form listed %d municipalities; expected 351' % len(offered))
    fields = ([('iclMuni', t) for t in offered] + [('iclYear', y) for y in years]
              + [('rdreport', 'averagesingletaxbill.singlefamtaxbill_wrange'), ('lgxver', ''),
                 ('iclMuni_rdExpandedCollapsedHistory', ''), ('iclYear_rdExpandedCollapsedHistory', ''),
                 ('rdShowElementHistory', ''), ('tabAvgSingFamTaxBill', '')])
    req = urllib.request.Request(EXPORT, data=urllib.parse.urlencode(fields).encode(), headers=ua)
    r = urllib.request.urlopen(req, timeout=180)
    data = r.read()
    if not data.startswith(b'PK'):
        raise SystemExit('the export was not a workbook (%s, %d bytes)' % (r.headers.get('Content-Type'), len(data)))
    # THROUGH INGEST, NOT open(..., 'wb'). Until 28 October 2026 this wrote the export
    # straight into sources/, so between the fetch and the day's `sync_archive.py --push`
    # the only copy of it was a file in a git working tree -- the window ingest.py exists to
    # close. It also made the fetch unsafe to schedule: every run wrote a new file whether
    # or not DLS had changed a figure. See land_export for both halves of the fix.
    key, changed = land_export('AvgSingleFamTaxBill', '.xlsx', data, EXPORT,
                               current=current_export(OUT_CSV, OUT_DIR, newest_xlsx()), check=extract)
    return years, offered, key, changed


def extract(src=None):
    import openpyxl
    src = src or newest_xlsx()
    wb = openpyxl.load_workbook(src, read_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    head = [str(c or '').strip() for c in rows[0]]
    expect = ['DOR Code', 'Municipality', 'Fiscal Year', 'Single-Family Values', 'Single-Family Parcels',
              'Average Single-Family Value', 'Single-Family Tax Bill', 'Single-Family Tax Bill as % of Value',
              'DOR Income Per Capita', 'Average Tax Bill as a % of Income', 'Rank']
    if head != expect:
        raise SystemExit('the workbook’s columns moved: %s' % head)
    digest = sha256(src)
    out = []
    for r in rows[1:]:
        if not r or r[1] is None:
            continue
        vals = ['' if v in (None, '') else v for v in r]
        out.append(dict(zip(COLS, list(vals) + [os.path.basename(src), digest])))
    # Reconcile: average value x parcels should be the total value, to the rounding of an average.
    bad = 0
    for o in out:
        if o['sf_parcels'] and o['avg_sf_value'] and o['sf_value_total']:
            if abs(float(o['sf_parcels']) * float(o['avg_sf_value']) - float(o['sf_value_total'])) > float(o['sf_parcels']):
                bad += 1
    if bad:
        raise SystemExit('%d rows where parcels x average value does not foot to total value' % bad)
    return out


def write_csv(rows):
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def write_index(years, towns=None, src=None):
    # NAME THE FILE WE ACTUALLY WROTE. This said `AvgSingleFamTaxBill.xlsx` while the fetch
    # wrote a dated one, so the catalogue described a file nobody had fetched today and the
    # dated export was uncatalogued -- rule 12's first requirement, missed by a constant.
    local = 'state-dls/' + os.path.basename(src or newest_xlsx())
    rows = []
    if os.path.exists(INDEX):
        rows = [r for r in csv.DictReader(open(INDEX, encoding='utf-8')) if r['local'] != local]
    who = ('every municipality' if towns is None or len(towns) > 300
           else ', '.join(towns))
    rows.append(dict(local=local, url=EXPORT,
                     title='Average Single-Family Tax Bill, %s, FY%s–FY%s' % (who, years[0], years[-1]),
                     note='DLS Gateway export (POST of the report form with these towns and years; see fetch_dls_tax_bills.py)'))
    with open(INDEX, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['local', 'url', 'title', 'note'])
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        rows = extract()
        have = list(csv.DictReader(open(OUT_CSV, encoding='utf-8'))) if os.path.exists(OUT_CSV) else []
        same = [{k: str(v) for k, v in r.items()} for r in rows] == have
        print('ok — %s reproduces from %s' % (os.path.relpath(OUT_CSV, ROOT), os.path.basename(newest_xlsx())) if same
              else 'STALE %s — run fetch_dls_tax_bills.py' % os.path.relpath(OUT_CSV, ROOT))
        return 0 if same else 1
    years, offered, key, changed = fetch()
    if not changed:
        # UNCHANGED IS SUCCESS. The extract and the catalogue already describe exactly
        # this content, so nothing is rewritten and the run exits 0 -- which is what lets
        # the refresh run this on a cadence without every run looking like a change.
        print('unchanged: DLS still publishes what %s holds; nothing landed, nothing rewritten'
              % os.path.basename(key))
        return 0
    # FROM THE KEY land_export NAMED, not the newest file by modification time: when the
    # content was already held, the file holding it need not be the newest one.
    src = os.path.join(ROOT, 'sources', key)
    rows = extract(src)
    write_csv(rows)
    write_index(years, offered, src)
    lun = [r for r in rows if r['municipality'] == 'Lunenburg' and r['avg_sf_bill']]
    print('%s: %d rows, %d towns, FY%s–FY%s; Lunenburg FY%s bill $%s on an average $%s home'
          % (os.path.relpath(OUT_CSV, ROOT), len(rows), len({r['municipality'] for r in rows}), years[0], years[-1],
             lun[0]['fy'], lun[0]['avg_sf_bill'], lun[0]['avg_sf_value']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
