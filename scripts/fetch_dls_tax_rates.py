#!/usr/bin/env python3
"""The Division of Local Services' Tax Rates by Class, every municipality, every year.

    python3 scripts/fetch_dls_tax_rates.py          # fetch through ingest.land, catalogue, extract
    python3 scripts/fetch_dls_tax_rates.py --check  # the extract still reproduces from the file

WHY IT EXISTS. The regional-school-share page needs each town's TOTAL TAX LEVY, and nothing
in this archive held it for every town: the annual-report extracts carry Lunenburg's levy for
some years only, and DLS's new-growth file carries the prior LEVY LIMIT, which is a ceiling and
not the tax raised. The levy is the sum, over the five classes, of the class's assessed value
times its rate -- the tax recapitulation's own arithmetic -- and DLS publishes both halves:
values by class (fetch_dls_property.py, already held for all 351) and the rate for each class,
here. So the levy on the page is OUR ARITHMETIC on two published files, and says so.

WHERE IT COMES FROM. The DLS Gateway Logi report
`PropertyTaxInformation.taxratesbyclass.taxratesbyclass` on dlsgateway.dor.state.ma.us -- the
same host as Assessed Values by Class. The page shell (`..._main`) wraps it in an iframe; the
sub-report is the form. Municipalities and years are checkbox lists and Export Table POSTs the
same form back with `rdReportFormat=NativeExcel`, exactly as fetch_dls_tax_bills.py does.

WHAT THE FILE HOLDS, per municipality per fiscal year: the tax rate per $1,000 for Residential,
Open Space, Commercial, Industrial and Personal Property. FY2003 onward; the newest year is a
blank row until the rate is set. A single-rate town prints one rate five times (open space is
often 0 where the class is empty); a classified town prints a lower residential rate.

THE DOOR. The export lands through ingest.land -- staged, pushed to the bucket, read back, and
only then filed under sources/state-dls/ -- named by export_name() so a re-fetch is a new key.
An export whose CONTENT matches the file the extract was read from lands nothing and exits 0
(fetch_dls_tax_bills.land_export), which is what makes it safe to run on a cadence.

RECONCILED before anything is written: every rate row is either all blank (the uncertified
year) or all numeric, and Lunenburg is DOR code 162.
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
from fetch_dls_tax_bills import INDEX, current_export, land_export, newest_export  # noqa: E402

PAGE = ('https://dlsgateway.dor.state.ma.us/reports/rdPage.aspx'
        '?rdReport=PropertyTaxInformation.taxratesbyclass.taxratesbyclass')
EXPORT = (PAGE + '&rdReportFormat=NativeExcel&rdExportTableID=tbl_taxratesbyclass'
          '&rdExportFilename=taxratesbyclass&rdShowGridlines=True&rdExcelOutputFormat=Excel2007')
UA = {'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org research)'}
DIR = os.path.join(ROOT, 'sources', 'state-dls')
STEM = 'taxratesbyclass'
OUT_CSV = os.path.join(ROOT, 'sources', 'data', 'dls-tax-rates.csv')
HEAD = ['DOR Code', 'Municipality', 'Fiscal Year', 'Residential', 'Open Space', 'Commercial',
        'Industrial', 'Personal Property']
COLS = ['dor_code', 'municipality', 'fy', 'residential', 'open_space', 'commercial', 'industrial',
        'personal_property']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def newest():
    return newest_export(DIR, STEM, '.xlsx')


def fetch():
    page = urllib.request.urlopen(urllib.request.Request(PAGE, headers=UA), timeout=120).read().decode('utf-8', 'replace')
    years = sorted(set(re.findall(r'name="iclYear"[^>]*value="(\d+)"', page)))
    munis = [m for m in re.findall(r'name="iclMuni"[^>]*value="([^"]*)"', page) if m]
    if len(years) < 20:
        raise SystemExit('the DLS form offered %d years; expected FY2003 onward' % len(years))
    if len(munis) < 340 or 'Lunenburg' not in munis:
        raise SystemExit('the DLS form listed %d municipalities; expected 351 with Lunenburg' % len(munis))
    fields = ([('iclMuni', m) for m in munis] + [('iclYear', y) for y in years]
              + [('rdreport', 'propertytaxinformation.taxratesbyclass.taxratesbyclass'), ('lgxver', '')])
    req = urllib.request.Request(EXPORT, data=urllib.parse.urlencode(fields).encode(),
                                 headers=dict(UA, Referer=PAGE))
    resp = urllib.request.urlopen(req, timeout=180)
    blob = resp.read()
    if not blob.startswith(b'PK'):
        raise SystemExit('the export was not a workbook (%s, %d bytes)' % (resp.headers.get('Content-Type'), len(blob)))
    # COMPARED BY CONTENT, NOT BY BYTES, before anything lands. ingest.land already refuses
    # to land identical bytes twice, but the Gateway re-zips every export with the time of
    # the request, so no two fetches are ever byte-identical and every scheduled run would
    # have landed a new copy of an unchanged file. land_export says why and how.
    key, changed = land_export(STEM, '.xlsx', blob, EXPORT,
                               current=current_export(OUT_CSV, DIR, newest()), check=extract, directory=DIR)
    return years, key, changed


def extract(src=None):
    import openpyxl
    src = src or newest()
    rows = list(openpyxl.load_workbook(src, read_only=True).worksheets[0].iter_rows(values_only=True))
    head = [str(c or '').strip() for c in rows[0]]
    if head != HEAD:
        raise SystemExit('the workbook’s columns moved: %s' % head)
    digest = sha256(src)
    out, bad = [], []
    for r in rows[1:]:
        if not r or r[1] is None:
            continue
        vals = ['' if v in (None, '') else v for v in r]
        rates = vals[3:8]
        if any(v == '' for v in rates) and any(v != '' for v in rates):
            bad.append('%s FY%s: some rates blank, some not' % (vals[1], vals[2]))
        if vals[1] == 'Lunenburg' and str(vals[0]) != '162':
            bad.append('Lunenburg is not DOR code 162')
        out.append(dict(zip(COLS + ['source_file', 'sha256'], list(vals) + [os.path.basename(src), digest])))
    if bad:
        raise SystemExit('%s:\n  %s' % (os.path.basename(src), '\n  '.join(bad[:10])))
    if len({o['municipality'] for o in out}) < 340:
        raise SystemExit('%s: fewer than 340 municipalities' % os.path.basename(src))
    return out


def write_csv(rows):
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS + ['source_file', 'sha256'])
        w.writeheader()
        w.writerows(rows)


def write_index(years, src=None):
    local = 'state-dls/' + os.path.basename(src or newest())
    rows = [r for r in csv.DictReader(open(INDEX, encoding='utf-8')) if r['local'] != local]
    rows.append(dict(local=local, url=EXPORT,
                     title='Tax Rates by Class, every municipality, FY%s–FY%s' % (years[0], years[-1]),
                     note='DLS Gateway export (POST of the report form with every town and year; '
                          'see fetch_dls_tax_rates.py)'))
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
        print('ok — %s reproduces from %s' % (os.path.relpath(OUT_CSV, ROOT), os.path.basename(newest())) if same
              else 'STALE %s — run fetch_dls_tax_rates.py' % os.path.relpath(OUT_CSV, ROOT))
        return 0 if same else 1
    years, key, changed = fetch()
    if not changed:
        print('unchanged: DLS still publishes what %s holds; nothing landed, nothing rewritten'
              % os.path.basename(key))
        return 0
    # From the key land_export named, which need not be the newest file by mtime.
    src = os.path.join(ROOT, 'sources', key)
    rows = extract(src)
    write_csv(rows)
    write_index(years, src)
    lun = [r for r in rows if r['municipality'] == 'Lunenburg' and r['residential'] != '']
    print('%s: %d rows; Lunenburg FY%s residential rate %s'
          % (os.path.relpath(OUT_CSV, ROOT), len(rows), lun[-1]['fy'], lun[-1]['residential']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
