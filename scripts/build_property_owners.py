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
from taxbase import TAX_RATE, AVG_HOME_HISTORY                                   # noqa: E402
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

DLS = os.path.join(ROOT, 'sources', 'data', 'dls-avg-tax-bill.csv')
DLS_KEY = 'state-dls/AvgSingleFamTaxBill.xlsx'
SPAN = 10                       # the ten-year change the town plans in
NEIGHBOURS = ['Ayer', 'Groton', 'Littleton', 'Shirley', 'Townsend', 'Westford', 'Leominster',
              'Fitchburg', 'Lancaster', 'Harvard']


def bills():
    """Every year DLS publishes, for Lunenburg; the neighbours for the latest year.

    The RATE is derived -- bill / average value, per $1,000 -- because the DLS table carries
    the bill and the value and not the rate. For a single-rate town it IS the rate (FY2026:
    $7,444 / $517,296 = $14.39, which is the rate the town set), and it is labelled as the
    effective rate on the page so a split-rate town's figure is not mistaken for a levy rate.
    Asserted against the five years typed into model/taxbase.py from the town's own hearings."""
    rows = [r for r in csv.DictReader(open(DLS, encoding='utf-8')) if r['avg_sf_bill'] not in ('', '0')]
    lun = sorted((r for r in rows if r['municipality'] == 'Lunenburg'), key=lambda r: int(r['fy']))
    series = [dict(fy=int(r['fy']), parcels=int(r['sf_parcels']), value=float(r['avg_sf_value']),
                   bill=float(r['avg_sf_bill']), rate=float(r['avg_sf_bill']) / float(r['avg_sf_value']) * 1000,
                   bill_pct_income=float(r['bill_pct_of_income']) / 100 if r['bill_pct_of_income'] else None,
                   rank=int(r['rank']) if r['rank'] else None) for r in lun]
    by = {h['fy']: h for h in series}
    for h in AVG_HOME_HISTORY:
        d = by.get(h['fy'])
        if not d or abs(d['bill'] - h['bill']) > 1.5 or abs(d['value'] - h['value']) > 100:
            fail('FY%d: DLS says bill %s value %s; the town’s hearing says %s / %s' % (h['fy'], d and d['bill'], d and d['value'], h['bill'], h['value']))
    if abs(by[FY_NOW]['rate'] - TAX_RATE) > 0.01:
        fail('FY%d effective rate %.2f from DLS; the town set %.2f' % (FY_NOW, by[FY_NOW]['rate'], TAX_RATE))
    last, prev = by[FY_NOW], by[FY_NOW - SPAN]
    first = series[0]
    latest_rows = [r for r in rows if int(r['fy']) == FY_NOW]
    nb = sorted((dict(town=r['municipality'], parcels=int(r['sf_parcels']), value=float(r['avg_sf_value']),
                      bill=float(r['avg_sf_bill']), rate=float(r['avg_sf_bill']) / float(r['avg_sf_value']) * 1000,
                      bill_pct_income=float(r['bill_pct_of_income']) / 100 if r['bill_pct_of_income'] else None,
                      income_per_capita=float(r['income_per_capita']) if r['income_per_capita'] else None,
                      rank=int(r['rank']) if r['rank'] else None)
                 for r in latest_rows if r['municipality'] in NEIGHBOURS + ['Lunenburg']),
                key=lambda r: -r['bill'])
    position = [r['town'] for r in nb].index('Lunenburg') + 1
    return dict(rows=series, first_fy=first['fy'], last_fy=last['fy'], span=SPAN, span_from_fy=prev['fy'],
                ten=dict(value_change=last['value'] / prev['value'] - 1, rate_change=last['rate'] / prev['rate'] - 1,
                         bill_change=last['bill'] / prev['bill'] - 1, value_from=prev['value'], value_to=last['value'],
                         rate_from=prev['rate'], rate_to=last['rate'], bill_from=prev['bill'], bill_to=last['bill']),
                since_first=dict(value_change=last['value'] / first['value'] - 1, rate_change=last['rate'] / first['rate'] - 1,
                                 bill_change=last['bill'] / first['bill'] - 1),
                neighbours=nb, position=position, of=len(nb), statewide_rank=last['rank'], statewide_of=351,
                bill_pct_income=last['bill_pct_income'],
                neighbour_median_bill=statistics.median(r['bill'] for r in nb if r['town'] != 'Lunenburg'))


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
    r = man.get(DLS_KEY) or fail('%s is not in the manifest' % DLS_KEY)
    if not r['upstream']:
        fail('%s carries no upstream address (rule 12)' % DLS_KEY)
    out.append(dict(path='sources/' + DLS_KEY, sha256=r['sha256'], bytes=int(r['bytes']), url=r['upstream'],
                    docs_url='/docs/' + DLS_KEY, table='Average Single-Family Tax Bill, FY1988–FY2026',
                    publisher='Massachusetts DOR, Division of Local Services',
                    note=('Every town’s single-family parcels, average value, average bill, the bill as a share '
                          'of value and of income, and rank — exported from the DLS Gateway by script.')))
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

def conclusions(c, p, b, t):
    c23 = c[2023]
    usd = lambda n: '$' + format(round(n), ',')
    pc = lambda x: '%.0f%%' % (x * 100)
    n0 = lambda n: format(round(n), ',')
    rows = []
    last = b['rows'][-1]
    # 1. THE HOMES. The denominator every other figure is a share of. TJ: "the top level
    #    conclusion should be something like total homes, rates dropping, values going up."
    rows.append(conclusion(
        'the-homes',
        claim='Lunenburg has %s single-family homes on %s parcels, and %s of households own theirs.'
              % (n0(last['parcels']), n0(p['parcels']), pc(t['owner_share'])),
        so_what='Four households in five own, so a change in the tax bill reaches most of the town directly.',
        detail=('%s single-family parcels in the state’s FY%d count, %s in the assessor’s file; %s parcels of '
                'every kind. %s ± %s occupied households on the Census %s sample, %s ± %s of them owned and '
                '%s ± %s rented.'
                % (n0(last['parcels']), last['fy'], n0(p['single_family']), n0(p['parcels']), n0(t['households']),
                   n0(t['households_moe']), t['window'], n0(t['owners']), n0(t['owners_moe']), n0(t['renters']),
                   n0(t['renters_moe']))),
        figures={'sf': figure(last['parcels'], n0(last['parcels']), 'single-family homes'),
                 'parcels': figure(p['parcels'], n0(p['parcels'])),
                 'share': figure(t['owner_share'] * 100, pc(t['owner_share'])),
                 'hh': figure(t['households'], n0(t['households'])),
                 'hhmoe': figure(t['households_moe'], n0(t['households_moe'])),
                 'sf2': figure(p['single_family'], n0(p['single_family'])),
                 'fy': figure(last['fy'], 'FY%d' % last['fy']),
                 'own': figure(t['owners'], n0(t['owners'])), 'ownmoe': figure(t['owners_moe'], n0(t['owners_moe'])),
                 'rent': figure(t['renters'], n0(t['renters'])), 'rentmoe': figure(t['renters_moe'], n0(t['renters_moe']))},
        figure='sf', kind='measured', bearing='sizes',
        basis='DLS Average Single-Family Tax Bill (parcels, FY2026); MassGIS Level 3 parcels, FY2026; ACS B25003, 2019–2023.',
        not_shown='Condominiums, two- and three-family homes and apartments, which the single-family count leaves out.',
        allow=('2019–2023', 'FY2026')))
    # 2. THE BILL. Ten years: value up, rate down, bill up -- the Proposition 2 1/2 paradox in
    #    the town's own DLS series.
    ten = b['ten']
    rows.append(conclusion(
        'the-bill',
        claim='In ten years the average home’s value rose %s and the tax rate fell %s; the bill rose %s.'
              % (pc(ten['value_change']), pc(-ten['rate_change']), pc(ten['bill_change'])),
        so_what='Residents feel higher taxes and see a falling rate. Both are true: the levy is capped, values are not.',
        detail=('FY%d to FY%d: the average single-family value from %s to %s, the effective rate from $%.2f to '
                '$%.2f per $1,000, the average bill from %s to %s. Since FY%d, the first year the state publishes, '
                'the value is up %s and the bill %s. Proposition 2½ caps how fast the LEVY grows; the rate is '
                'whatever divides that levy into the year’s total value, so as values rise the rate falls and '
                'the bill does neither.'
                % (b['span_from_fy'], b['last_fy'], usd(ten['value_from']), usd(ten['value_to']), ten['rate_from'],
                   ten['rate_to'], usd(ten['bill_from']), usd(ten['bill_to']), b['first_fy'],
                   pc(b['since_first']['value_change']), pc(b['since_first']['bill_change']))),
        figures={'value': figure(ten['value_change'] * 100, pc(ten['value_change'])),
                 'rate': figure(-ten['rate_change'] * 100, pc(-ten['rate_change'])),
                 'bill': figure(ten['bill_change'] * 100, pc(ten['bill_change']), 'more on the average bill in ten years'),
                 'fy0': figure(b['span_from_fy'], 'FY%d' % b['span_from_fy']),
                 'fy1': figure(b['last_fy'], 'FY%d' % b['last_fy']),
                 'v0': figure(ten['value_from'], usd(ten['value_from'])), 'v1': figure(ten['value_to'], usd(ten['value_to'])),
                 'r0': figure(ten['rate_from'], '$%.2f' % ten['rate_from']), 'r1': figure(ten['rate_to'], '$%.2f' % ten['rate_to']),
                 'b0': figure(ten['bill_from'], usd(ten['bill_from'])), 'b1': figure(ten['bill_to'], usd(ten['bill_to'])),
                 'ff': figure(b['first_fy'], 'FY%d' % b['first_fy']),
                 'sv': figure(b['since_first']['value_change'] * 100, pc(b['since_first']['value_change'])),
                 'sb': figure(b['since_first']['bill_change'] * 100, pc(b['since_first']['bill_change']))},
        figure='bill', kind='measured', bearing='sizes',
        basis='DLS Average Single-Family Tax Bill, Lunenburg, FY1988–FY2026; rate derived as bill ÷ value per $1,000.',
        not_shown='Any one household’s bill: this is the town-wide average home, and the exemptions and abatements a household may hold.',
        allow=('2½', '$1,000')))
    # 3. THE NEIGHBOURS.
    lun = next(r for r in b['neighbours'] if r['town'] == 'Lunenburg')
    rows.append(conclusion(
        'the-neighbours',
        claim='At %s, Lunenburg’s average bill is %s of %s nearby towns and cities — %s statewide.'
              % (usd(lun['bill']), ordinal(b['position']), b['of'], ordinal(b['statewide_rank'])),
        so_what='The bill takes %s of income per capita here; the median of the ten neighbours is %s.'
                % (pc(lun['bill_pct_income']), usd(b['neighbour_median_bill'])),
        detail=('FY%d, DLS: Lunenburg %s on an average home worth %s, ranked %s of %s municipalities. The '
                'towns above and below are in the table, with each one’s bill as a share of its income per capita.'
                % (b['last_fy'], usd(lun['bill']), usd(lun['value']), ordinal(b['statewide_rank']), b['statewide_of'])),
        figures={'bill': figure(lun['bill'], usd(lun['bill']), 'a year, the average single-family bill'),
                 'pos': figure(b['position'], ordinal(b['position'])), 'of': figure(b['of'], str(b['of'])),
                 'rank': figure(b['statewide_rank'], ordinal(b['statewide_rank'])),
                 'pct': figure(lun['bill_pct_income'] * 100, pc(lun['bill_pct_income'])),
                 'med': figure(b['neighbour_median_bill'], usd(b['neighbour_median_bill'])),
                 'fy': figure(b['last_fy'], 'FY%d' % b['last_fy']),
                 'value': figure(lun['value'], usd(lun['value'])),
                 'sw': figure(b['statewide_of'], str(b['statewide_of']))},
        figure='bill', kind='measured', bearing='sizes',
        basis='DLS Average Single-Family Tax Bill, FY2026, for Lunenburg and ten neighbours.',
        not_shown='What each town gets for the bill — services, schools, debt — which the bill alone does not say.',
        allow=('FY2026',)))
    # 4. WHO HAS BEEN HERE HOW LONG -- demoted below the bill, kept because it is the question
    #    that started the page.
    before = c23['before_2010']
    rows.append(conclusion(
        'before-2010',
        claim='%s of Lunenburg’s owner households moved in before 2010 — about %s of them.'
              % (n0(before['households']), pc(before['share'])),
        so_what='Half the town’s homeowners have been in the house since before 2010; a sixth since the 1980s.',
        detail=('%s ± %s of %s owner-occupied households, on the Census Bureau’s %s five-year sample; '
                '%s ± %s have been in the house since 1989 or earlier. The median owner moved in in %d.'
                % (n0(before['households']), n0(before['moe']), n0(c23['owners']), c23['window'],
                   n0(c23['since_1980s']['households']), n0(c23['since_1980s']['moe']), c23['median_moved_in'])),
        figures={'n': figure(before['households'], n0(before['households']), 'owner households'),
                 'share': figure(before['share'] * 100, pc(before['share'])),
                 'moe': figure(before['moe'], n0(before['moe'])), 'owners': figure(c23['owners'], n0(c23['owners'])),
                 'old': figure(c23['since_1980s']['households'], n0(c23['since_1980s']['households'])),
                 'oldmoe': figure(c23['since_1980s']['moe'], n0(c23['since_1980s']['moe'])),
                 'median': figure(c23['median_moved_in'], str(c23['median_moved_in']))},
        figure='n', kind='measured', bearing='sizes',
        basis='Census Bureau, ACS five-year estimates, tables B25038 and B25039, 2019–2023, Lunenburg town.',
        not_shown='Whether those households can afford the bill. The Census does not publish tenure against income for a town this size.',
        allow=('2010', '1989', '1980s', '2019–2023', 'B25038', 'B25039')))
    oldest, newest = p['bands'][-1], p['bands'][0]
    rows.append(conclusion(
        'bill-by-tenure',
        claim='A home last deeded before 1986 pays a median %s a year; one deeded since 2021 pays %s.'
              % (usd(oldest['median_bill']), usd(newest['median_bill'])),
        so_what='The bill barely falls with tenure — long-held homes pay %s of what newcomers pay.'
                % pc(p['earliest_band_bill_ratio']),
        detail=('Every single-family parcel in the assessor’s FY%d file, %s of them, at the %s rate: median '
                'assessed value %s for homes last deeded before 1986 against %s for those deeded since 2021; the '
                'median price those older homes last sold for was %s. A house bought decades ago is taxed on '
                'what it is worth now, not on what it cost.'
                % (p['fy'], n0(p['single_family']), '$%.2f' % p['rate'], usd(oldest['median_value']),
                   usd(newest['median_value']), usd(oldest['median_sale_price']))),
        figures={'old': figure(oldest['median_bill'], usd(oldest['median_bill']), 'a year'),
                 'new': figure(newest['median_bill'], usd(newest['median_bill'])),
                 'ratio': figure(p['earliest_band_bill_ratio'] * 100, pc(p['earliest_band_bill_ratio'])),
                 'n': figure(p['single_family'], n0(p['single_family'])), 'rate': figure(p['rate'], '$%.2f' % p['rate']),
                 'oldval': figure(oldest['median_value'], usd(oldest['median_value'])),
                 'newval': figure(newest['median_value'], usd(newest['median_value'])),
                 'sale': figure(oldest['median_sale_price'], usd(oldest['median_sale_price'])),
                 'fy': figure(p['fy'], 'FY%d' % p['fy'])},
        figure='old', kind='measured', bearing='sizes',
        basis='MassGIS Level 3 parcels, Lunenburg, FY2026 assessing extract; bill = assessed value × the FY2026 rate.',
        not_shown=('What any household earns, or whether the deed date is when they arrived: a third of deeds are '
                   'nominal transfers that reset the date. Exemptions and abatements are not applied.'),
        allow=('1986', '2021', 'FY2026')))
    return emit(REPORT, rows)


def ordinal(n):
    n = int(n)
    suf = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return '%d%s' % (n, suf)


def build():
    c = census()
    p = parcels()
    b = bills()
    t = tenure()
    return dict(
        about=('Lunenburg’s homes and the tax bill: how many there are, what the average one is worth and '
               'pays, year by year and against the neighbours — and, behind that, how long the owners have '
               'been here and what a long-held home pays.'),
        grain=('HOUSEHOLDS from the Census, a five-year sample with margins; PARCELS from the assessor, '
               'a count of single-family homes by last recorded deed, which is not the same as when the '
               'family arrived; DOLLARS from the town’s own rate and values.'),
        tenure=t, census={str(k): v for k, v in c.items()}, parcels=p, bills=b,
        conclusions=conclusions(c, p, b, t),
        not_established=[
            'Whether long-tenured owners are being taxed out — that needs tenure against income or against '
            'the bill, which neither the Census nor the assessor publishes together.',
            'Any one household’s bill: exemptions, abatements and the split between land and building are '
            'not applied; every figure here is the average or the median home.',
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
