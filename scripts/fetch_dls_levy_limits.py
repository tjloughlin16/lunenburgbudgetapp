#!/usr/bin/env python3
"""The Division of Local Services' Proposition 2 1/2 files: levy limits, levies by class, new
growth and exclusions, every municipality, as far back as DLS ever published them.

    python3 scripts/fetch_dls_levy_limits.py            # land anything new, write index rows
    python3 scripts/fetch_dls_levy_limits.py --dry-run  # say what would be fetched

Then `python3 scripts/extract_levy_limits.py` builds `sources/data/dls-levy-limits.csv`.

TWO PUBLICATIONS, ONE SERIES. DLS publishes the same Proposition 2 1/2 figures in two places,
and neither reaches back on its own:

1. THE GATEWAY (current). Logi reports on dlsgateway.dor.state.ma.us, found 3 November 2026 from
   the "Category 3a - Proposition 2 1/2" dashboard (`rdReport=Dashboard.Cat3aPropTaxStat`), whose
   panels link every report below. Same shape as fetch_dls_tax_rates.py: municipalities, years
   (and for the vote reports departments and win/loss) are checkbox lists, and Export Table POSTs
   the form back with `rdReportFormat=NativeExcel`. Every box is ticked, so the export is every
   town and every year the form offers.

   | report | export file | years offered (3 Nov 2026) |
   |---|---|---|
   | Prop2.5.ExcessLevyCapandOverride_10_pres | ExcessLevyAndOverrideCap | FY2007-FY2027 |
   | PropertyTaxInformation.TaxLevies.LeviesByClass | Taxlevybyclass | FY2003-FY2027 |
   | Votes.Prop2_5.DebtExclusionLevyAmt | DebtExcLevyAmt | FY2002-FY2029 |
   | Votes.Prop2_5.DebtExclusionVotes | AllDebtlExclusionResults | FY1989-FY2027 |
   | Votes.Prop2_5.Capital | CapitalExclusionVotes | FY1988-FY2027 |

   The export filename is the publisher's own (`rdExportFilename`), misspelling included.

2. THE OLD MUNICIPAL DATABANK (retired). Before the Gateway, DLS posted the same tables as
   Excel files under `www.mass.gov/Ador/docs/dls/mdmstuf/`. Those addresses are dead; the
   Internet Archive holds the captures, and a capture's address (`web.archive.org/web/<stamp>id_/
   <original>`) is the deepest address there is -- the `id_` form returns the bytes as served,
   not a rewritten page. Each file is landed under the PUBLISHER'S filename, and the capture
   stamp is recorded beside it, because the same address held different bytes over the years
   (`excp10.xls` was captured blank, before FY2010 was certified).

   | file | holds |
   |---|---|
   | excp8589.xls, excp9099.xls, excp0009.xls | levy limit, maximum levy, tax levy, excess capacity, FY1985-FY2009 |
   | lvcl8689.xls, lvcl9099.xls, lvcl0009.xls | tax levy by class, FY1986-FY2009 |
   | Grow9299.xls, grow0009.xls | new growth applied to the levy limit, FY1992-FY2009 |
   | DebtEx.xls | debt exclusion amount applied to the levy limit, FY1989-FY2008 |
   | DebtVotes.xls, capital.xls | every debt and capital exclusion vote, FY1982/FY1988 onward |

   Not landed, and why: `excp10/11/12.xls` and their siblings were captured as blank shells
   (every figure empty); the Gateway report covers FY2007 onward, so nothing is lost. No new
   growth file before FY1992 exists in either publication (searched: the archive's full listing
   of mdmstuf/Prop2_LevyCap_RefVotes/ and mdmstuf/PropertyTax/, and the Gateway's new growth
   report, which starts at FY2003).

THE DOOR. Gateway exports land through fetch_dls_tax_bills.land_export (content-compared, named
by export_name). Archive captures land through ingest.land; ingest refuses identical bytes twice,
and a capture's bytes never change, so a re-run lands nothing.
"""
import argparse
import csv
import html
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from fetch_dls_tax_bills import INDEX, land_export, newest_export  # noqa: E402

UA = {'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org research)'}
HOST = 'https://dlsgateway.dor.state.ma.us/reports/'
DIR = os.path.join(ROOT, 'sources', 'state-dls')

# report id -> (export stem, title, minimum years the form must offer)
GATEWAY = {
    'Prop2.5.ExcessLevyCapandOverride_10_pres':
        ('ExcessLevyAndOverrideCap', 'Excess Levy Capacity and Override Capacity, every municipality', 20),
    'PropertyTaxInformation.TaxLevies.LeviesByClass':
        ('Taxlevybyclass', 'Tax Levies by Class, every municipality', 20),
    'Votes.Prop2_5.DebtExclusionLevyAmt':
        ('DebtExcLevyAmt', 'Debt Exclusion Amount Applied to the Levy Limit, every municipality', 20),
    'Votes.Prop2_5.DebtExclusionVotes':
        ('AllDebtlExclusionResults', 'Proposition 2 1/2 Debt Exclusion Votes, every municipality', 30),
    'Votes.Prop2_5.Capital':
        ('CapitalExclusionVotes', 'Proposition 2 1/2 Capital Exclusion Votes, every municipality', 30),
}

ARCHIVE = 'http://www.mass.gov/Ador/docs/dls/mdmstuf/'
# publisher's path under mdmstuf/ -> (capture stamp, title)
CAPTURES = {
    'Prop2_LevyCap_RefVotes/excp8589.xls': ('20080720052055', 'Excess Levy Capacity, FY1985-FY1989'),
    'Prop2_LevyCap_RefVotes/excp9099.xls': ('20080720052110', 'Excess Levy Capacity, FY1990-FY1999'),
    'Prop2_LevyCap_RefVotes/excp0009.xls': ('20090912201840', 'Excess Levy Capacity, FY2000-FY2009'),
    'PropertyTax/lvcl8689.xls': ('20080720052942', 'Levies by Class, FY1986-FY1989'),
    'PropertyTax/lvcl9099.xls': ('20080720053100', 'Tax Levies by Class, FY1990-FY1999'),
    'PropertyTax/lvcl0009.xls': ('20090912202243', 'Tax Levies by Class, FY2000-FY2009'),
    'Prop2_LevyCap_RefVotes/Grow9299.xls': ('20080720052050', 'New Growth Analysis, FY1992-FY1999'),
    'Prop2_LevyCap_RefVotes/grow0009.xls': ('20090912201822', 'New Growth Analysis, FY2000-FY2009'),
    'Prop2_LevyCap_RefVotes/DebtEx.xls': ('20080720052059',
                                          'Debt Exclusion Amount Applied to the Levy Limit, FY1989-FY2008'),
    'Prop2_LevyCap_RefVotes/DebtVotes.xls': ('20080720052121', 'All Debt Exclusion Votes Recorded, FY1982-FY2008'),
    'Prop2_LevyCap_RefVotes/capital.xls': ('20080720052140', 'Capital Exclusions, FY1988-FY2008'),
}


def capture_url(path):
    stamp = CAPTURES[path][0]
    return 'https://web.archive.org/web/%sid_/%s%s' % (stamp, ARCHIVE, path)


def get(url, data=None, referer=None):
    headers = dict(UA, Referer=referer) if referer else UA
    req = urllib.request.Request(url, data=data, headers=headers)
    return urllib.request.urlopen(req, timeout=300).read()


def gateway_export(report):
    """(export url, workbook bytes, years offered) for one Gateway report, every box ticked."""
    page_url = HOST + 'rdPage.aspx?rdReport=' + report
    page = get(page_url).decode('utf-8', 'replace')
    m = re.search(r'rdPage\.aspx\?rdReport=[^"\']*NativeExcel[^"\']*', page)
    if not m:
        raise SystemExit('%s: the page carries no Excel export link' % report)
    export = HOST + html.unescape(m.group(0))
    fields = []
    for tag in re.findall(r'<input[^>]*>', page):
        n, v = re.search(r'name="(icl\w+)"', tag), re.search(r'value="([^"]*)"', tag)
        if n and v and v.group(1):
            fields.append((n.group(1), html.unescape(v.group(1))))
    years = sorted({v for n, v in fields if n == 'iclYear'})
    munis = [v for n, v in fields if n == 'iclMuni']
    stem, _title, min_years = GATEWAY[report]
    if len(years) < min_years:
        raise SystemExit('%s offered %d years; expected at least %d' % (report, len(years), min_years))
    if not munis:
        raise SystemExit('%s listed no municipalities' % report)
    fields += [('rdreport', report.lower()), ('lgxver', '')]
    blob = get(export, urllib.parse.urlencode(fields).encode(), referer=page_url)
    if not blob.startswith(b'PK'):
        raise SystemExit('%s: the export was not a workbook (%d bytes)' % (report, len(blob)))
    return export, blob, years


def index_rows():
    with open(INDEX, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def write_index(new):
    """Add or replace index rows by `local`, keeping everybody else's rows as they are."""
    rows = [r for r in index_rows() if r['local'] not in {n['local'] for n in new}] + new
    with open(INDEX, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['local', 'url', 'title', 'note'])
        w.writeheader()
        w.writerows(rows)


def main():
    import ingest
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    new = []
    for report, (stem, title, _m) in GATEWAY.items():
        if a.dry_run:
            print('gateway', report, '->', stem)
            continue
        export, blob, years = gateway_export(report)
        key, changed = land_export(stem, '.xlsx', blob, export,
                                   current=newest_export(DIR, stem, '.xlsx'), directory=DIR)
        print('%s: %s%s' % (report, key, '' if changed else ' (unchanged)'))
        new.append(dict(local=key, url=export, title='%s, FY%s-FY%s' % (title, years[0], years[-1]),
                        note='DLS Gateway export: POST of the report form rdReport=%s with every '
                             'municipality and year ticked (see fetch_dls_levy_limits.py). The '
                             'publisher names the export %s.xlsx.' % (report, stem)))
    for path, (stamp, title) in CAPTURES.items():
        name = os.path.basename(path)
        key = 'state-dls/' + name
        if a.dry_run:
            print('capture', capture_url(path), '->', key)
            continue
        blob = get(capture_url(path))
        if not blob.startswith(b'\xd0\xcf\x11\xe0'):
            raise SystemExit('%s: the capture is not an Excel 97 workbook' % path)
        ok, why = ingest.land(key, blob, capture_url(path))
        if not ok:
            raise SystemExit('ingest.land refused %s: %s' % (key, why))
        print('%s: landed %s %s' % (path, key, why))
        new.append(dict(local=key, url=capture_url(path), title='%s, every municipality' % title,
                        note='DLS Municipal Databank, retired. Published at %s%s (dead); this is '
                             'the Internet Archive capture of %s, fetched 3 November 2026. '
                             'Publisher filename %s.' % (ARCHIVE, path, stamp, name)))
    if not a.dry_run:
        write_index(new)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
