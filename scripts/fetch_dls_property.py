#!/usr/bin/env python3
"""The Division of Local Services' two property-base reports, every year, our towns:
assessed value BY CLASS, and NEW GROWTH split residential against everything else.

    python3 scripts/fetch_dls_property.py          # fetch both, catalogue, extract
    python3 scripts/fetch_dls_property.py --check  # both extracts still reproduce from their files

WHY TWO REPORTS. Assessed value by class says how big the commercial base IS, and a
revaluation moves it as much as a building does -- Lunenburg's residential value rose 23%
in FY2023 with nothing built. New growth is what the assessors certify was ADDED: new
construction and new personal property, valued and put on the levy limit, by class. The
first answers "what share of the town is business"; the second answers "how much got
built". Reading the first as the second was the trap TJ's four-year export set on
16 September 2026 -- it started at FY2023, the last flat year, and made a 41% "boom" out of
a series that had been flat for seventeen years.

WHERE THEY COME FROM. Two DLS Gateway Logi reports, both found by TJ on 16 September
2026 -- on two different hosts, which is why nothing guessed from the tax-bill report's
address answered:

    dlsgateway.dor.state.ma.us  PropertyTaxInformation.AssessedValuesbyClass.assessedvaluesbyclass   FY2002 onward
    dls-gw.dor.state.ma.us      NewGrowth.NewGrowth_dash_v2_test                                     FY2003 onward

Each is the same shape as fetch_dls_tax_bills.py's: municipalities and years are checkbox
lists, and the Export Table button POSTs the form back with `rdReportFormat=NativeExcel`.
`rdExcelOutputFormat=Excel2007` asks for .xlsx rather than the binary .xls the button
gives by default, so openpyxl reads it and nothing new is installed. The newest fiscal
year is a blank row until the town's values are certified.

WHAT EACH FILE HOLDS, per municipality per fiscal year, as the columns are printed.
  assessedvalues.xlsx   Residential, Open Space, Commercial, Industrial, Personal Property,
                        Total, and the RO and CIP shares of it.
  new_growth.xlsx       residential new growth VALUE and the levy dollars it ADDED; total
                        new growth value and levy dollars; residential as a share; the
                        prior year's levy limit; the addition as a share of it.

RECONCILED TO THE FILE'S OWN ARITHMETIC before anything is written (rule 13): the five
classes foot to the total and the CIP share recomputes; residential new growth is no
more than total, and the addition-as-share recomputes from the prior levy limit.

The model's own new-growth series (`model/taxbase.py`, from the FY2023 tax classification
hearing) is six years of the same figures, and build_commercial_base.py asserts the two
agree to the dollar where they overlap -- so the town's document and the state's file
are checked against each other every build rather than trusted separately.
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
from fetch_dls_tax_bills import TOWNS, INDEX, export_name, newest_export   # noqa: E402

UA = {'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org research)'}

REPORTS = {
    'assessed-values': dict(
        host='dlsgateway', report='PropertyTaxInformation.AssessedValuesbyClass.assessedvaluesbyclass',
        table='tblassessedvalues', export='assessedvalues', min_years=20,
        file='assessedvalues.xlsx', csv='dls-assessed-values.csv',
        title='Assessed Values by Class, %s, FY%s–FY%s',
        head=['DOR Code', 'Municipality', 'Fiscal Year', 'Residential', 'Open Space', 'Commercial', 'Industrial',
              'Personal Property', 'Total', 'RO% of Total', 'CIP% of Total'],
        cols=['dor_code', 'municipality', 'fy', 'residential', 'open_space', 'commercial', 'industrial',
              'personal_property', 'total', 'ro_pct', 'cip_pct'],
        # EVERY MUNICIPALITY, for the reason spelled out under health-insurance below: a peer
        # set chosen in the fetcher is a judgment baked into the archive. It became load-bearing
        # on 26 September 2026, when `build_town_comparison.py` had to find the districts that
        # resemble Lunenburg across all 351 towns rather than inside a list of twelve -- which
        # cannot be done from an archive that only ever held twelve.
        all_towns=True,
    ),
    # HEALTH INSURANCE, TOWN BY TOWN. TJ, 18 September 2026, on finding it: "we should
    # build analysis into the health insurance report that compares!" Schedule A Parts 2
    # and 6, FY2002 onward, one dollar figure per town-year.
    #
    # TWO TRAPS DLS PRINTS ITSELF AND THIS FILE CANNOT FIX. For a SELF-INSURED town the
    # figure includes the EMPLOYEE share; for a town accounting through a trust it can
    # include workers' compensation and OPEB as well. Nothing in the export flags which
    # town is which, so a raw town-against-town comparison compares different quantities.
    # Lunenburg is fully insured through the MIIA joint purchase group (c.32B §12), so its
    # own figure is the town's premium share alone -- notes/findings/MA-MUNICIPAL-HEALTH-INSURANCE.md.
    'health-insurance': dict(
        host='dls-gw', report='ScheduleA.HealthInsurance.HealthInsExpenditures',
        table='ctHealthExp', export='health_insurance', min_years=20,
        file='health-insurance-expenditures.xlsx', csv='dls-health-insurance.csv',
        title='Health insurance expenditures, %s, FY%s–FY%s',
        head=None,          # read from the workbook: the year columns move every autumn
        cols=None,
        # EVERY MUNICIPALITY, not the eleven peers. The control is checked for all 351 by
        # default and the export is small; a peer set chosen in the fetcher is a judgment
        # baked into the archive, and this way the judgment stays in the analysis where it
        # can be argued with.
        all_towns=True,
    ),
    # WHO PAYS CLAIMS, AND WHO BUYS A PREMIUM. The companion to the report above, and the
    # only published axis on which towns' health spending can be told apart: a town
    # reporting a health trust fund on Schedule A Part 6 is SELF-INSURED and its figure
    # includes the employee share; a town with no trust buys premiums and its figure is
    # the employer share alone. Which POOL a town buys through -- MIIA, a regional group,
    # the GIC, a carrier direct -- is recorded in no state dataset at all (money-gaps).
    'self-insured': dict(
        host='dls-gw', report='ScheduleA.HealthInsurance.Self_InsuredFunds',
        table='TblPt6_HealthFund', export='self_insured', min_years=20,
        file='health-self-insured-funds.xlsx', csv='dls-health-self-insured.csv',
        title='Self-insured health trust funds, %s, FY%s–FY%s',
        head=['DOR Code', 'Municipality', 'Fiscal Year', 'Starting Balance', 'Revenues',
              'Expenditures', 'Fund Balance', 'Self-insured (Y/N)'],
        cols=['dor_code', 'municipality', 'fy', 'starting_balance', 'revenues',
              'expenditures', 'fund_balance', 'flag'],
        # THE MUNICIPALITY LIST IS NOT IN THIS PAGE. Unlike its companion, this report
        # fills its checklist by AJAX, so there are no codes to post -- and posting none
        # is what returns every municipality, which is what this wants. The check that it
        # worked is the row count in extract_wide's caller.
        all_towns=True, no_muni_field=True,
    ),
    'new-growth': dict(
        host='dls-gw', report='NewGrowth.NewGrowth_dash_v2_test',
        table='tblNewGrowth', export='new_growth', min_years=20,
        file='new_growth.xlsx', csv='dls-new-growth.csv',
        title='New Growth, residential and total, %s, FY%s–FY%s',
        head=['DOR Code', 'Municipality', 'Fiscal Year', 'Residential New Growth Value',
              'Residential New Growth Applied to the Levy Limit', 'Total New Growth Value',
              'Total New Growth Applied to Levy Limit', 'Res New Growth as a % of Total New Growth',
              "Prior Year's Levy Limit", 'Total New Growth Applied to Limit as a % of PY Levy Limit'],
        cols=['dor_code', 'municipality', 'fy', 'res_value', 'res_levy', 'total_value', 'total_levy',
              'res_pct_of_total', 'prior_levy_limit', 'levy_pct_of_prior_limit'],
        all_towns=True,
    ),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def page_url(r):
    return 'https://%s.dor.state.ma.us/reports/rdPage.aspx?rdReport=%s' % (r['host'], r['report'])


def export_url(r):
    return (page_url(r) + '&rdReportFormat=NativeExcel&rdExportTableID=%s&rdExportFilename=%s'
            '&rdShowGridlines=True&rdExcelOutputFormat=Excel2007' % (r['table'], r['export']))


def xlsx_path(r, blob=None):
    """Where one export lands. Hashed into the name -- see `export_name` in
    fetch_dls_tax_bills.py for why a DLS export may never reuse a key."""
    stem, ext = os.path.splitext(r['file'])
    d = os.path.join(ROOT, 'sources', 'state-dls')
    if blob is None:
        return newest_export(d, stem, ext, legacy=r['file'])
    return os.path.join(d, export_name(stem, ext, blob))


def csv_path(r):
    return os.path.join(ROOT, 'sources', 'data', r['csv'])


def fetch(r):
    page = urllib.request.urlopen(urllib.request.Request(page_url(r), headers=UA), timeout=120).read().decode('utf-8', 'replace')
    years = sorted(set(re.findall(r'name="iclYear"[^>]*value="(\d+)"', page)))
    if len(years) < r['min_years']:
        raise SystemExit('%s: the DLS form offered %d years; expected %d or more' % (r['report'], len(years), r['min_years']))
    if r.get('no_muni_field'):
        fields = [('iclYear', y) for y in years] + [('rdreport', r['report'].lower()), ('lgxver', '')]
    elif r.get('all_towns'):
        # The control's values are DOR codes, and its labels are the town names; both are
        # taken from the page so a renamed or renumbered municipality cannot go missing.
        # THE CONTROL IS KEYED DIFFERENTLY ON DIFFERENT REPORTS, and assuming one shape
        # made this refuse to fetch at all. The Schedule A reports key it by DOR CODE with
        # the town name in a following <span>; Assessed Values by Class and New Growth key
        # it by the town NAME itself. Read whichever the page offers and check the same
        # invariant either way -- that Lunenburg is in the list and the list is 351 long.
        codes = re.findall(r'name="iclMuni"[^>]*value="(\d+)"\s*/><span>([^<]+)</span>', page)
        if codes:
            values = [c for c, _ in codes]
            names = {n.strip() for _, n in codes}
            if {c for c, n in codes if n.strip() == 'Lunenburg'} != {'162'}:
                raise SystemExit('%s: DOR code 162 is not Lunenburg -- the codes have moved' % r['report'])
        else:
            values = sorted(set(re.findall(r'name="iclMuni"[^>]*value="([^"]*)"', page)))
            values = [v for v in values if v]
            names = set(values)
        if len(values) < 340:
            raise SystemExit('%s: the DLS form listed %d municipalities; expected 351'
                             % (r['report'], len(values)))
        if 'Lunenburg' not in names:
            raise SystemExit('%s: the DLS form does not list Lunenburg' % r['report'])
        fields = ([('iclMuni', v) for v in values] + [('iclYear', y) for y in years]
                  + [('rdreport', r['report'].lower()), ('lgxver', '')])
    else:
        offered = set(re.findall(r'name="iclMuni"[^>]*value="([^"]*)"', page))
        missing = [t for t in TOWNS if t not in offered]
        if missing:
            raise SystemExit('%s: the DLS form does not list %s' % (r['report'], missing))
        fields = ([('iclMuni', t) for t in TOWNS] + [('iclYear', y) for y in years]
                  + [('rdreport', r['report'].lower()), ('lgxver', '')])
    req = urllib.request.Request(export_url(r), data=urllib.parse.urlencode(fields).encode(),
                                 headers=dict(UA, Referer=page_url(r)))
    resp = urllib.request.urlopen(req, timeout=180)
    data = resp.read()
    if not data.startswith(b'PK'):
        raise SystemExit('%s: the export was not a workbook (%s, %d bytes)' % (r['report'], resp.headers.get('Content-Type'), len(data)))
    path = xlsx_path(r, data)
    with open(path, 'wb') as fh:
        fh.write(data)
    print('  wrote %s (%d bytes)' % (os.path.relpath(path, ROOT), len(data)))
    return years


def num(v):
    return None if v in (None, '') else float(v)


def extract_wide(key):
    """A report whose columns are YEARS, not fields: DOR code, municipality, FY…FY.

    The year columns move every autumn as a new one is certified, so the header is read
    rather than asserted; what IS asserted is that the years are consecutive and that
    Lunenburg's row is present."""
    import openpyxl
    r = REPORTS[key]
    wb = openpyxl.load_workbook(xlsx_path(r), read_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    head = [str(c or '').strip() for c in rows[0]]
    if head[:2] != ['DOR Code', 'Municipality']:
        raise SystemExit('%s: expected DOR Code and Municipality, found %s' % (r['file'], head[:2]))
    years = []
    for c in head[2:]:
        m = re.search(r'(\d{4})', c)
        if m:
            years.append(int(m.group(1)))
    if len(years) < 10 or years != list(range(years[0], years[0] + len(years))):
        raise SystemExit('%s: the year columns are not consecutive: %s' % (r['file'], head[2:]))
    digest = sha256(xlsx_path(r))
    out, towns = [], set()
    for row in rows[1:]:
        name = str(row[1] or '').strip()
        if not name or name.lower().startswith('total'):
            continue
        towns.add(name)
        for i, fy in enumerate(years):
            v = row[2 + i]
            out.append(dict(dor_code=str(row[0] or '').strip(), municipality=name, fy=fy,
                            # DLS prints 0 for a year whose Schedule A is not yet filed --
                            # an empty cell, not a town that spent nothing. Kept as blank.
                            expenditure='' if v in (None, '', 0) else v,
                            source_file=os.path.basename(xlsx_path(r)), sha256=digest))
    if 'Lunenburg' not in towns:
        raise SystemExit('%s: no Lunenburg row' % r['file'])
    if len(towns) < 340:
        raise SystemExit('%s: only %d municipalities' % (r['file'], len(towns)))
    return out


def extract(key):
    import openpyxl
    r = REPORTS[key]
    if r.get('head') is None:
        return extract_wide(key)
    wb = openpyxl.load_workbook(xlsx_path(r), read_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    head = [str(c or '').strip() for c in rows[0]]
    if head != r['head']:
        raise SystemExit('%s: the workbook’s columns moved: %s' % (r['file'], head))
    digest = sha256(xlsx_path(r))
    out = []
    for row in rows[1:]:
        if not row or row[1] is None:
            continue
        vals = ['' if v in (None, '') else v for v in row]
        out.append(dict(zip(r['cols'] + ['source_file', 'sha256'], list(vals) + [os.path.basename(xlsx_path(r)), digest])))
    if key == 'self-insured':
        if len({o['municipality'] for o in out}) < 340:
            raise SystemExit('%s: only %d municipalities' % (r['file'], len({o['municipality'] for o in out})))
        # The report's own Y/N flag is not reliable -- Abington prints N in every year
        # while reporting millions of trust expenditures -- so nothing is asserted from
        # it here. What the rows carry is the trust's own money, and that is what
        # build_health_options.py classifies on.
        return out
    bad = []
    for o in out:
        if o['fy'] and num(o.get('total') if key == 'assessed-values' else o.get('total_value')) is None:
            continue   # the uncertified year: a blank row
        if key == 'assessed-values':
            parts = sum(num(o[c]) for c in ('residential', 'open_space', 'commercial', 'industrial', 'personal_property'))
            if abs(parts - num(o['total'])) > 1:
                bad.append('%s FY%s: classes foot to %.0f, total printed %.0f' % (o['municipality'], o['fy'], parts, num(o['total'])))
            cip = 100 * (num(o['commercial']) + num(o['industrial']) + num(o['personal_property'])) / num(o['total'])
            if abs(cip - num(o['cip_pct'])) > 0.01:
                bad.append('%s FY%s: CIP share recomputes to %.4f, printed %s' % (o['municipality'], o['fy'], cip, o['cip_pct']))
        else:
            if num(o['res_value']) > num(o['total_value']) + 1 or num(o['res_levy']) > num(o['total_levy']) + 1:
                bad.append('%s FY%s: residential new growth exceeds total' % (o['municipality'], o['fy']))
            if num(o['prior_levy_limit']):
                share = 100 * num(o['total_levy']) / num(o['prior_levy_limit'])
                if abs(share - num(o['levy_pct_of_prior_limit'])) > 0.01:
                    bad.append('%s FY%s: addition as share of prior limit recomputes to %.2f, printed %s'
                               % (o['municipality'], o['fy'], share, o['levy_pct_of_prior_limit']))
    if bad:
        raise SystemExit('%s does not foot to itself:\n  %s' % (r['file'], '\n  '.join(bad[:10])))
    return out


def write_csv(key, rows):
    r = REPORTS[key]
    cols = r['cols'] or ['dor_code', 'municipality', 'fy', 'expenditure']
    with open(csv_path(r), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols + ['source_file', 'sha256'])
        w.writeheader()
        w.writerows(rows)


def write_index(key, years):
    r = REPORTS[key]
    # NAME THE FILE WE ACTUALLY READ. `r['file']` is the stem's legacy name; the export
    # on disk carries a date and a content hash, and a catalogue row for a name nobody
    # fetched is rule 12's first requirement missed by a constant.
    local = 'state-dls/' + os.path.basename(xlsx_path(r))
    rows = [x for x in csv.DictReader(open(INDEX, encoding='utf-8'))] if os.path.exists(INDEX) else []
    rows = [x for x in rows if x['local'] != local]
    who = 'every municipality' if r.get('all_towns') else ', '.join(TOWNS)
    rows.append(dict(local=local, url=export_url(r), title=r['title'] % (who, years[0], years[-1]),
                     note='DLS Gateway export (POST of the report form with these towns and years; see fetch_dls_property.py)'))
    with open(INDEX, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['local', 'url', 'title', 'note'])
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        ok = True
        for key, r in REPORTS.items():
            rows = extract(key)
            have = list(csv.DictReader(open(csv_path(r), encoding='utf-8'))) if os.path.exists(csv_path(r)) else []
            same = [{k: str(v) for k, v in x.items()} for x in rows] == have
            print(('ok — %s reproduces from %s' if same else 'STALE %s — run fetch_dls_property.py (from %s)')
                  % (os.path.relpath(csv_path(r), ROOT), r['file']))
            ok = ok and same
        return 0 if ok else 1
    for key, r in REPORTS.items():
        years = fetch(r)
        rows = extract(key)
        write_csv(key, rows)
        write_index(key, years)
        last = (r['cols'] or ['dor_code', 'municipality', 'fy', 'expenditure'])[-1]
        lun = [x for x in rows if x['municipality'] == 'Lunenburg' and x[last] != '']
        print('%s: %d rows, %d towns, FY%s–FY%s; Lunenburg through FY%s'
              % (os.path.relpath(csv_path(r), ROOT), len(rows), len({x['municipality'] for x in rows}), years[0], years[-1], lun[-1]['fy']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
