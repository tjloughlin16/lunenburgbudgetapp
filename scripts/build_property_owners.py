#!/usr/bin/env python3
"""Who owns the homes, how long they have owned them, and what the bill has done.

    python3 scripts/build_property_owners.py          # write fy28/public/data/property-owners.json
    python3 scripts/build_property_owners.py --check  # fail if it no longer reproduces

TJ, 13 September 2026: "how many households in Lunenburg have been owned for 10 or more
years? Basically, to confirm if people are being taxed out from purchasing half a century
ago" -- and then: a small report in The town beside Lunenburg by the numbers, "including
the tax rates for average house of lunenburg (in a table...), taxes per year, and taxes per
year of nearby towns. Include data and table about the owned since data."

TWO SOURCES FOR "OWNED SINCE", AND THEY MEASURE DIFFERENT THINGS.

  * ACS table B25038 counts HOUSEHOLDS by the year the householder moved in -- a sample,
    with margins, 2019-2023. It is the answer to "how long have the people been here".
  * The assessor's FY2026 parcel file (MassGIS Level 3) carries the LAST RECORDED DEED for
    every parcel -- a count, no margin, but a deed is not an arrival: a third of them are
    nominal transfers (into a trust, between family) that reset the date without moving
    anybody. So tenure read off deeds is a LOWER BOUND, and the page says so.

What the parcel file settles that the Census cannot is the BILL: every parcel's assessed
value is in it, and the bill is value x rate. So the median bill by how long the home has
been held is computed, not inferred -- which is the question behind "taxed out".

Nearby towns' bills are NOT here. The Division of Local Services publishes them, behind a
bot check this project cannot pass by script (see sources/state-dls/PROVENANCE.md). It is a
registered gap, on the page and in the registry.
"""
import argparse
import csv
import io
import json
import math
import os
import statistics
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from taxbase import TAX_RATE, AVG_HOME_VALUE, AVG_HOME_BILL, AVG_HOME_HISTORY   # noqa: E402
from conclusions import conclusion, emit, figure                                # noqa: E402

OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'property-owners.json')
CENSUS = os.path.join(ROOT, 'sources', 'data', 'census-acs.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
PARCELS_KEY = 'state-massgis/L3_SHP_M162_LUNENBURG.zip'
PARCELS = os.path.join(ROOT, 'sources', PARCELS_KEY)
ASSESS_DBF = 'L3_SHP_M162_Lunenburg/M162Assess_CY26_FY26.dbf'
REPORT = 'owners'
FY_NOW = 2026
NOMINAL = 1000          # a deed under this price is a transfer, not a sale
WINDOW = {2018: '2014–2018', 2023: '2019–2023'}

# B25038: owner-occupied by year householder moved in. Variables 003-008, oldest last.
ACS_BANDS = [('B25038_003E', '2021 or later'), ('B25038_004E', '2018–2020'),
             ('B25038_005E', '2010–2017'), ('B25038_006E', '2000–2009'),
             ('B25038_007E', '1990–1999'), ('B25038_008E', '1989 or earlier')]
ACS_BANDS_2018 = [('B25038_003E', '2017 or later'), ('B25038_004E', '2015–2016'),
                  ('B25038_005E', '2010–2014'), ('B25038_006E', '2000–2009'),
                  ('B25038_007E', '1990–1999'), ('B25038_008E', '1989 or earlier')]
OWNERS_TOTAL = 'B25038_002E'
MEDIAN_MOVED_IN_OWNERS = 'B25039_002E'

# Deed bands for the parcel side, newest first; the boundary years are FY_NOW minus 5, 10...
DEED_BANDS = [('2021 or later', 2021, 9999), ('2016–2020', 2016, 2020), ('2011–2015', 2011, 2015),
              ('2006–2010', 2006, 2010), ('1996–2005', 1996, 2005), ('1986–1995', 1986, 1995),
              ('before 1986', 0, 1985)]


def fail(msg):
    print('FAIL: ' + msg)
    raise SystemExit(1)


# ------------------------------------------------------------------------------ census

def tenure():
    """B25003: every occupied home, owner against renter -- the denominator the page opens on."""
    rows = {r['variable']: r for r in csv.DictReader(open(CENSUS, encoding='utf-8'))
            if 'Lunenburg' in r['geography'] and r['table'] == 'B25003' and r['vintage'] == '2023'}
    tot, own, rent = (float(rows[v]['estimate']) for v in ('B25003_001E', 'B25003_002E', 'B25003_003E'))
    return dict(households=tot, households_moe=float(rows['B25003_001E']['moe']),
                owners=own, owners_moe=float(rows['B25003_002E']['moe']),
                renters=rent, renters_moe=float(rows['B25003_003E']['moe']),
                owner_share=own / tot, window=WINDOW[2023])


def census():
    rows = [r for r in csv.DictReader(open(CENSUS, encoding='utf-8'))
            if 'Lunenburg' in r['geography'] and r['table'] in ('B25038', 'B25039')]
    if not rows:
        fail('census-acs.csv holds no B25038/B25039 rows for Lunenburg; run fetch_census_acs.py')
    by = {(int(r['vintage']), r['variable']): r for r in rows}
    out = {}
    for vintage, bands in ((2023, ACS_BANDS), (2018, ACS_BANDS_2018)):
        total = by[(vintage, OWNERS_TOTAL)]
        T = float(total['estimate'])
        rs = []
        for var, label in bands:
            r = by[(vintage, var)]
            e, m = float(r['estimate']), float(r['moe'])
            rs.append(dict(label=label, households=e, moe=m, share=e / T,
                           # share of a total with its own margin: the ratio formula
                           share_moe=math.sqrt(m ** 2 - (e / T) ** 2 * float(total['moe']) ** 2) / T
                           if m ** 2 > (e / T) ** 2 * float(total['moe']) ** 2 else m / T))
        older = [x for x in rs if x['label'] in ('2000–2009', '1990–1999', '1989 or earlier')]
        before2010 = sum(x['households'] for x in older)
        before2010_moe = math.sqrt(sum(x['moe'] ** 2 for x in older))
        out[vintage] = dict(
            vintage=vintage, window=WINDOW[vintage], owners=T, owners_moe=float(total['moe']),
            bands=rs,
            before_2010=dict(households=before2010, moe=before2010_moe, share=before2010 / T),
            since_1980s=dict(households=rs[-1]['households'], moe=rs[-1]['moe'], share=rs[-1]['share']),
            median_moved_in=int(float(by[(vintage, MEDIAN_MOVED_IN_OWNERS)]['estimate'])),
            source_file=total['source_file'], sha256=total['sha256'])
    return out


# ----------------------------------------------------------------------------- parcels

def read_dbf(blob):
    hdr = blob[:32]
    n = struct.unpack('<I', hdr[4:8])[0]
    hl = struct.unpack('<H', hdr[8:10])[0]
    rl = struct.unpack('<H', hdr[10:12])[0]
    fields, pos = [], 32
    while blob[pos] != 0x0d:
        b = blob[pos:pos + 32]
        fields.append((b[:11].split(b'\0')[0].decode(), b[16]))
        pos += 32
    out, pos = [], hl
    for _ in range(n):
        rec = blob[pos:pos + rl]
        pos += rl
        if rec[:1] == b'*':
            continue
        row, p = {}, 1
        for name, ln in fields:
            row[name] = rec[p:p + ln].decode('latin-1').strip()
            p += ln
        out.append(row)
    return out


def parcels():
    with zipfile.ZipFile(PARCELS) as z:
        rows = read_dbf(z.read(ASSESS_DBF))
    fy = {r['FY'] for r in rows}
    if fy != {str(FY_NOW)}:
        fail('the parcel file is not FY%d: %s' % (FY_NOW, sorted(fy)))
    sf = [r for r in rows if r['USE_CODE'].startswith('101') and r['TOTAL_VAL']]
    if len(sf) < 3000:
        fail('only %d single-family parcels read; expected several thousand' % len(sf))
    year = lambda r: int(r['LS_DATE'][:4])
    price = lambda r: float(r['LS_PRICE'] or 0)
    value = lambda r: float(r['TOTAL_VAL'])
    bill = lambda r: value(r) * TAX_RATE / 1000
    bands = []
    for label, a, b in DEED_BANDS:
        g = [r for r in sf if a <= year(r) <= b]
        arm = [r for r in g if price(r) >= NOMINAL]
        bands.append(dict(
            label=label, homes=len(g), share=len(g) / len(sf),
            median_value=statistics.median(value(r) for r in g),
            median_bill=statistics.median(bill(r) for r in g),
            nominal_share=1 - len(arm) / len(g) if g else None,
            median_sale_price=statistics.median(price(r) for r in arm) if arm else None,
            arm_length=len(arm)))
    nominal = sum(1 for r in sf if price(r) < NOMINAL)
    held = lambda yrs: sum(1 for r in sf if year(r) <= FY_NOW - 1 - yrs)
    all_bill = statistics.median(bill(r) for r in sf)
    return dict(
        fy=FY_NOW, rate=TAX_RATE, parcels=len(rows), single_family=len(sf),
        median_value=statistics.median(value(r) for r in sf), median_bill=all_bill,
        bands=bands,
        held=[dict(years=y, homes=held(y), share=held(y) / len(sf)) for y in (10, 20, 30)],
        nominal=dict(deeds=nominal, share=nominal / len(sf)),
        owner_in_town=dict(homes=sum(1 for r in sf if r['OWN_CITY'].upper().startswith('LUNENBURG')),
                           share=sum(1 for r in sf if r['OWN_CITY'].upper().startswith('LUNENBURG')) / len(sf)),
        oldest_deed=min(year(r) for r in sf),
        earliest_band_bill_ratio=bands[-1]['median_bill'] / bands[0]['median_bill'])


# ------------------------------------------------------------------------- the tax bill

def bills():
    hist = [dict(h) for h in AVG_HOME_HISTORY]
    hist.append(dict(fy=FY_NOW, rate=TAX_RATE, value=AVG_HOME_VALUE, bill=AVG_HOME_BILL))
    a, b = hist[0], hist[-1]
    missing = [fy for fy in range(a['fy'], b['fy'] + 1) if fy not in {h['fy'] for h in hist}]
    return dict(rows=hist, first_fy=a['fy'], last_fy=b['fy'], missing_fy=missing,
                value_change=b['value'] / a['value'] - 1, rate_change=b['rate'] / a['rate'] - 1,
                bill_change=b['bill'] / a['bill'] - 1)


# ----------------------------------------------------------------------------- sources

def sources(c):
    man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = []
    for vintage in (2023, 2018):
        for table in ('B25038', 'B25039'):
            key = 'state-census/acs5-%d-%s-lunenburg.json' % (vintage, table)
            r = man.get(key) or fail('%s is not in the manifest' % key)
            out.append(dict(path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']),
                            url='https://api.census.gov/data/%d/acs/acs5' % vintage,
                            docs_url='/docs/' + key, table='%s, %s' % (table, WINDOW[vintage]),
                            publisher='United States Census Bureau',
                            note=('Tenure by year the householder moved in' if table == 'B25038'
                                  else 'Median year the householder moved in')))
    r = man.get(PARCELS_KEY) or fail('%s is not in the manifest' % PARCELS_KEY)
    if not r['upstream']:
        fail('%s carries no upstream address (rule 12)' % PARCELS_KEY)
    out.append(dict(path='sources/' + PARCELS_KEY, sha256=r['sha256'], bytes=int(r['bytes']),
                    url=r['upstream'], docs_url='/docs/' + PARCELS_KEY, table='FY2026 assessing extract',
                    publisher='MassGIS, Commonwealth of Massachusetts',
                    note=('Level 3 parcels: the assessor’s FY2026 values, use codes and last '
                          'recorded deed for every parcel. Owner names are in the file and are '
                          'not used here.')))
    return out


# ------------------------------------------------------------------------- conclusions

def conclusions(c, p, b):
    c23 = c[2023]
    usd = lambda n: '$' + format(round(n), ',')
    pc = lambda x: '%.0f%%' % (x * 100)
    n0 = lambda n: format(round(n), ',')
    rows = []
    before = c23['before_2010']
    rows.append(conclusion(
        'before-2010',
        claim='%s of Lunenburg’s owner households moved in before 2010 — about %s of them.'
              % (n0(before['households']), pc(before['share'])),
        so_what='Half the town’s homeowners have been in the house since before 2010; a sixth since the 1980s.',
        detail=('%s ± %s of %s owner-occupied households, on the Census Bureau’s %s five-year sample; '
                '%s ± %s have been in the house since 1989 or earlier. The median owner moved in in %d.'
                % (n0(before['households']), n0(before['moe']), n0(c23['owners']), c23['window'],
                   n0(c23['since_1980s']['households']), n0(c23['since_1980s']['moe']),
                   c23['median_moved_in'])),
        figures={'n': figure(before['households'], n0(before['households']), 'owner households'),
                 'share': figure(before['share'] * 100, pc(before['share'])),
                 'moe': figure(before['moe'], n0(before['moe'])),
                 'owners': figure(c23['owners'], n0(c23['owners'])),
                 'old': figure(c23['since_1980s']['households'], n0(c23['since_1980s']['households'])),
                 'oldmoe': figure(c23['since_1980s']['moe'], n0(c23['since_1980s']['moe'])),
                 'median': figure(c23['median_moved_in'], str(c23['median_moved_in']))},
        figure='n', kind='measured', bearing='sizes',
        basis='Census Bureau, ACS five-year estimates, tables B25038 and B25039, 2019–2023, Lunenburg town.',
        not_shown=('Whether those households can afford the bill. The Census does not publish tenure '
                   'against income for a town this size.'),
        allow=('2010', '1989', '1980s', '2019–2023', 'B25038', 'B25039')))
    oldest, newest = p['bands'][-1], p['bands'][0]
    rows.append(conclusion(
        'bill-by-tenure',
        claim='A home last deeded before 1986 pays a median %s a year; one deeded since 2021 pays %s.'
              % (usd(oldest['median_bill']), usd(newest['median_bill'])),
        so_what='The bill barely falls with tenure — long-held homes pay %s of what newcomers pay.'
                % pc(p['earliest_band_bill_ratio']),
        detail=('Every single-family parcel in the assessor’s FY%d file, %s of them, at the %s rate: '
                'median assessed value %s for homes last deeded before 1986 against %s for those '
                'deeded since 2021. A house bought decades ago is taxed on what it is worth now, '
                'not on what it cost.'
                % (p['fy'], n0(p['single_family']), '$%.2f' % p['rate'],
                   usd(oldest['median_value']), usd(newest['median_value']))),
        figures={'old': figure(oldest['median_bill'], usd(oldest['median_bill']), 'a year'),
                 'new': figure(newest['median_bill'], usd(newest['median_bill'])),
                 'ratio': figure(p['earliest_band_bill_ratio'] * 100, pc(p['earliest_band_bill_ratio'])),
                 'n': figure(p['single_family'], n0(p['single_family'])),
                 'rate': figure(p['rate'], '$%.2f' % p['rate']),
                 'oldval': figure(oldest['median_value'], usd(oldest['median_value'])),
                 'newval': figure(newest['median_value'], usd(newest['median_value'])),
                 'fy': figure(p['fy'], 'FY%d' % p['fy'])},
        figure='old', kind='measured', bearing='sizes',
        basis='MassGIS Level 3 parcels, Lunenburg, FY2026 assessing extract; bill = assessed value × the FY2026 rate.',
        not_shown=('What any household earns, or whether the deed date is when they arrived: a third of '
                   'deeds are nominal transfers that reset the date. Exemptions and abatements are not '
                   'applied.'),
        allow=('1986', '2021', 'FY2026')))
    h10 = p['held'][0]
    rows.append(conclusion(
        'held-ten-years',
        claim='At least %s single-family homes — %s — have not changed hands in ten years or more.'
              % (n0(h10['homes']), pc(h10['share'])),
        so_what='A floor, not the figure: %s of deeds are nominal transfers that reset the date.'
                % pc(p['nominal']['share']),
        detail=('%s of %s single-family parcels carry a last deed of %d or earlier; %s at twenty years, '
                '%s at thirty. %s deeds record a price under $1,000 — a trust, an estate, a family '
                'transfer — so a home held since the 1970s can show a deed from last year. The Census '
                'sample, which asks when the household ARRIVED, puts the ten-year-plus share of owner '
                'households at about %s.'
                % (n0(h10['homes']), n0(p['single_family']), FY_NOW - 1 - 10, n0(p['held'][1]['homes']),
                   n0(p['held'][2]['homes']), n0(p['nominal']['deeds']), pc(before['share']))),
        figures={'n': figure(h10['homes'], n0(h10['homes']), 'homes'),
                 'share': figure(h10['share'] * 100, pc(h10['share'])),
                 'nominal': figure(p['nominal']['share'] * 100, pc(p['nominal']['share'])),
                 'total': figure(p['single_family'], n0(p['single_family'])),
                 'year': figure(FY_NOW - 1 - 10, str(FY_NOW - 1 - 10)),
                 'h20': figure(p['held'][1]['homes'], n0(p['held'][1]['homes'])),
                 'h30': figure(p['held'][2]['homes'], n0(p['held'][2]['homes'])),
                 'ndeeds': figure(p['nominal']['deeds'], n0(p['nominal']['deeds'])),
                 'acs': figure(before['share'] * 100, pc(before['share']))},
        figure='n', kind='measured', bearing='sizes',
        basis='MassGIS Level 3 parcels, Lunenburg, FY2026: LS_DATE and LS_PRICE for every single-family parcel; ACS B25038 for the household figure.',
        not_shown='The true tenure of any home whose last deed was a transfer rather than a sale.',
        allow=('$1,000', '1970s')))
    rows.append(conclusion(
        'bill-history',
        claim='The average home’s value rose %s from FY%d to FY%d; the rate fell %s; the bill rose %s.'
              % (pc(b['value_change']), b['first_fy'], b['last_fy'],
                 pc(-b['rate_change']), pc(b['bill_change'])),
        so_what='Proposition 2½ caps the levy, not the bill on any one house — values decide who pays it.',
        detail=('From %s on a $%s home in FY%d to %s on a $%s home in FY%d. The rate went from $%.2f to '
                '$%.2f per $1,000. The years between are in the table; FY%d and FY%d are not held.'
                % (usd(b['rows'][0]['bill']), n0(b['rows'][0]['value']), b['first_fy'],
                   usd(b['rows'][-1]['bill']), n0(b['rows'][-1]['value']), b['last_fy'],
                   b['rows'][0]['rate'], b['rows'][-1]['rate'], b['missing_fy'][0], b['missing_fy'][-1])),
        figures={'value': figure(b['value_change'] * 100, pc(b['value_change'])),
                 'rate': figure(-b['rate_change'] * 100, pc(-b['rate_change'])),
                 'bill': figure(b['bill_change'] * 100, pc(b['bill_change']), 'more on the average bill'),
                 'first': figure(b['first_fy'], 'FY%d' % b['first_fy']),
                 'last': figure(b['last_fy'], 'FY%d' % b['last_fy']),
                 'b0': figure(b['rows'][0]['bill'], usd(b['rows'][0]['bill'])),
                 'v0': figure(b['rows'][0]['value'], '$' + n0(b['rows'][0]['value'])),
                 'b1': figure(b['rows'][-1]['bill'], usd(b['rows'][-1]['bill'])),
                 'v1': figure(b['rows'][-1]['value'], '$' + n0(b['rows'][-1]['value'])),
                 'r0': figure(b['rows'][0]['rate'], '$%.2f' % b['rows'][0]['rate']),
                 'r1': figure(b['rows'][-1]['rate'], '$%.2f' % b['rows'][-1]['rate']),
                 'm0': figure(b['missing_fy'][0], 'FY%d' % b['missing_fy'][0]),
                 'm1': figure(b['missing_fy'][-1], 'FY%d' % b['missing_fy'][-1])},
        figure='bill', kind='measured', bearing='sizes',
        basis='Town tax classification hearings FY2019–FY2023 and the FY2026 rate, as carried in model/taxbase.py.',
        not_shown='Any other town’s bill. The state publishes every town’s average single-family bill and the page that does sits behind a bot check this project cannot pass by script.',
        allow=('2½', '$1,000')))
    return emit(REPORT, rows)


def build():
    c = census()
    p = parcels()
    b = bills()
    return dict(
        about=('Who owns Lunenburg’s homes and for how long — from the Census sample and from the '
               'assessor’s own parcel file — and what the bill on an average home has done.'),
        grain=('HOUSEHOLDS from the Census, a five-year sample with margins; PARCELS from the assessor, '
               'a count of single-family homes by last recorded deed, which is not the same as when the '
               'family arrived; DOLLARS from the town’s own rate and values.'),
        tenure=tenure(), census={str(k): v for k, v in c.items()}, parcels=p, bills=b,
        conclusions=conclusions(c, p, b),
        not_established=[
            'What other towns’ average single-family tax bills are, year by year. The Division of Local '
            'Services publishes them for every municipality; its gateway is behind a bot check this '
            'project cannot pass by script, and no copy has been pulled by hand.',
            'The average bill for FY2024 and FY2025; the town’s classification hearings for those years '
            'are not in the archive.',
            'Whether long-tenured owners are being taxed out — that needs tenure against income or '
            'against the bill, which neither the Census nor the assessor publishes together.',
        ],
        sources=sources(c), generated_by='scripts/build_property_owners.py')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        if have != data:
            print('STALE %s — run build_property_owners.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('%s: %d conclusions; %d single-family parcels; %s owner households'
          % (os.path.relpath(OUT, ROOT), len(data['conclusions']), data['parcels']['single_family'],
             format(round(data['census']['2023']['owners']), ',')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
