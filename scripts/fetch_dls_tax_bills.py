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

Saved as the publisher's own export name under sources/state-dls/, hashed, and extracted
to sources/data/dls-avg-tax-bill.csv with the columns as printed.
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
TOWNS = ['Lunenburg', 'Ayer', 'Groton', 'Littleton', 'Shirley', 'Townsend', 'Westford',
         'Leominster', 'Fitchburg', 'Lancaster', 'Harvard']
OUT_XLSX = os.path.join(ROOT, 'sources', 'state-dls', 'AvgSingleFamTaxBill.xlsx')
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
    offered = set(re.findall(r'name="iclMuni"[^>]*value="([^"]*)"', page))
    missing = [t for t in TOWNS if t not in offered]
    if missing:
        raise SystemExit('the DLS form does not list %s' % missing)
    fields = ([('iclMuni', t) for t in TOWNS] + [('iclYear', y) for y in years]
              + [('rdreport', 'averagesingletaxbill.singlefamtaxbill_wrange'), ('lgxver', ''),
                 ('iclMuni_rdExpandedCollapsedHistory', ''), ('iclYear_rdExpandedCollapsedHistory', ''),
                 ('rdShowElementHistory', ''), ('tabAvgSingFamTaxBill', '')])
    req = urllib.request.Request(EXPORT, data=urllib.parse.urlencode(fields).encode(), headers=ua)
    r = urllib.request.urlopen(req, timeout=180)
    data = r.read()
    if not data.startswith(b'PK'):
        raise SystemExit('the export was not a workbook (%s, %d bytes)' % (r.headers.get('Content-Type'), len(data)))
    os.makedirs(os.path.dirname(OUT_XLSX), exist_ok=True)
    with open(OUT_XLSX, 'wb') as fh:
        fh.write(data)
    return years


def extract():
    import openpyxl
    wb = openpyxl.load_workbook(OUT_XLSX, read_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    head = [str(c or '').strip() for c in rows[0]]
    expect = ['DOR Code', 'Municipality', 'Fiscal Year', 'Single-Family Values', 'Single-Family Parcels',
              'Average Single-Family Value', 'Single-Family Tax Bill', 'Single-Family Tax Bill as % of Value',
              'DOR Income Per Capita', 'Average Tax Bill as a % of Income', 'Rank']
    if head != expect:
        raise SystemExit('the workbook’s columns moved: %s' % head)
    digest = sha256(OUT_XLSX)
    out = []
    for r in rows[1:]:
        if not r or r[1] is None:
            continue
        vals = ['' if v in (None, '') else v for v in r]
        out.append(dict(zip(COLS, list(vals) + [os.path.basename(OUT_XLSX), digest])))
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


def write_index(years):
    rows = []
    if os.path.exists(INDEX):
        rows = [r for r in csv.DictReader(open(INDEX, encoding='utf-8')) if r['local'] != 'state-dls/AvgSingleFamTaxBill.xlsx']
    rows.append(dict(local='state-dls/AvgSingleFamTaxBill.xlsx', url=EXPORT,
                     title='Average Single-Family Tax Bill, %s, FY%s–FY%s' % (', '.join(TOWNS), years[0], years[-1]),
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
        print('ok — %s reproduces from %s' % (os.path.relpath(OUT_CSV, ROOT), os.path.basename(OUT_XLSX)) if same
              else 'STALE %s — run fetch_dls_tax_bills.py' % os.path.relpath(OUT_CSV, ROOT))
        return 0 if same else 1
    years = fetch()
    rows = extract()
    write_csv(rows)
    write_index(years)
    lun = [r for r in rows if r['municipality'] == 'Lunenburg' and r['avg_sf_bill']]
    print('%s: %d rows, %d towns, FY%s–FY%s; Lunenburg FY%s bill $%s on an average $%s home'
          % (os.path.relpath(OUT_CSV, ROOT), len(rows), len({r['municipality'] for r in rows}), years[0], years[-1],
             lun[0]['fy'], lun[0]['avg_sf_bill'], lun[0]['avg_sf_value']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
