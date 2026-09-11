"""Who lives in Lunenburg — age, households, income by age, and tenure, from the Census.

    export CENSUS_API_KEY=...          # or put it in .census-key, which is gitignored
    python3 scripts/fetch_census_acs.py
    python3 scripts/fetch_census_acs.py --check

Writes `sources/data/census-acs.csv`, one row per table per variable per vintage, with the
ESTIMATE AND ITS MARGIN OF ERROR side by side. Catalogues each raw API response in
`sources/state-census/` with its sha256, because an API answer is a document like any other
and rule 12 does not exempt it for being JSON.

WHY THIS EXISTS

Two claims are made out loud in this town and neither is checkable against anything the
project holds. From TJ, reporting what he hears: *"This about the senior citizens who dont
have money to spend"* and *"this is good for the 30% of people who have students in the
school"*.

We hold DESE's detail on 1,568 children — by grade, by disability, by language, by income
band, back to 1992 — and effectively NOTHING about the other ten thousand residents. No age
distribution, no household composition, no income by age, no tenure. So the two groups
whose interests are being weighed against each other in public are one measured in depth
and one not measured at all, and that asymmetry has shaped every argument in town without
anybody naming it.

THE "30%" FIGURE IS UNPUBLISHABLE UNTIL THIS LANDS, in either direction. It has the
commonest error shape available: a count of HOUSEHOLDS with children read as a share of
PEOPLE. 1,568 students is about 13% of the town's residents and the household share is a
different denominator entirely. Publishing either number without the table would be this
project joining an argument with a figure it cannot source.

WHY ACS 5-YEAR AND NOT 1-YEAR

**1-year estimates are only published for geographies of 65,000 people or more.** Lunenburg
is about 11,800, so it does not appear in the 1-year product in any year, and never will.
The 5-year product covers every geography down to block group. The cost is that it is a
rolling five-year average rather than a single year -- which is the right trade here
anyway, because the question is what the town IS rather than what changed last year.

AND LUNENBURG IS A COUNTY SUBDIVISION. Massachusetts has no functioning county government
and its towns are county subdivisions in Census geography: `state:25`, `county:027`
(Worcester), `county subdivision:37420`. A query for `place:` finds nothing, because
Lunenburg is not an incorporated place in the Census sense.

EVERY FIGURE HERE IS AN ESTIMATE WITH A MARGIN OF ERROR, AND THAT IS NOT DECORATION

This is the part that matters for how these numbers may be used. A DESE enrolment count is
a census of children: 1,568 means 1,568. An ACS figure is a SAMPLE ESTIMATE, and for a town
of 11,800 the samples are small and the margins are wide -- it is routine for a subgroup
here to read `412 ± 180`. Two such figures whose intervals overlap are not different, and a
year-on-year change smaller than the margin is not a change.

So the `_M` variables are fetched beside every `_E` and stored in the same row, never
dropped. Anything built on this must print the margin or state a difference as
indistinguishable. Rule 7's territory: an estimate quoted as a count is a derived thing
being passed off as an observed one.

WHAT THIS CANNOT DO EVEN WHEN IT LANDS

It cannot say which households have children IN THE LUNENBURG SCHOOLS. B11005 counts
households with a child under 18 -- which includes children at Monty Tech, at a private
school, at a charter, and not yet of school age. That distinction is exactly the one the
"30%" claim elides, and this table bounds it rather than settling it.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'sources', 'state-census')
OUT = os.path.join(ROOT, 'sources', 'data', 'census-acs.csv')
KEYFILE = os.path.join(ROOT, '.census-key')

# Lunenburg town, Worcester County, Massachusetts.
# Verified against the API rather than looked up: a wrong COUSUB does not error, it
# returns HTTP 204 with an empty body, which a fetcher that checks the status code reads
# as success and writes as nothing. 37280 was my guess and it is Lunenburg in no state.
#   curl ".../acs5?get=NAME&for=county%20subdivision:*&in=state:25%20county:027"
STATE, COUNTY, COUSUB = '25', '027', '37420'
BASE = 'https://api.census.gov/data/%d/acs/acs5'

# The most recent 5-year release, and one older so a change can be looked at at all --
# knowing that consecutive 5-year releases OVERLAP by four years and are therefore not
# independent samples. A difference between them is not a trend and the CSV says so.
VINTAGES = (2023, 2018)

# The four tables that close the gap. Group queries (`group(B01001)`) return every
# variable in the table, estimates and margins together, which is why they are fetched
# whole rather than variable by variable: a hand-picked subset is a decision about what
# matters made before anybody has looked.
TABLES = {
    'B01001': 'Sex by age — the 65-and-over share, and every band beneath it',
    'B11005': 'Households by presence of people under 18 — the real denominator for '
              '"the 30% who have students in the school"',
    'B19049': 'Median household income in the past 12 months, by age of householder — '
              'what turns "seniors on fixed incomes" from a claim into a number',
    'B25003': 'Tenure — owner-occupied against renter-occupied',
}


def api_key():
    k = os.environ.get('CENSUS_API_KEY', '').strip()
    if not k and os.path.exists(KEYFILE):
        k = io.open(KEYFILE, encoding='utf-8').read().strip()
    if not k:
        raise SystemExit(
            'No Census API key. Put it in the CENSUS_API_KEY environment variable, or in\n'
            '  %s   (gitignored)\n'
            'Get one free at https://api.census.gov/data/key_signup.html — and note that\n'
            'activation is not instant: the key answers "Invalid Key" for a while after\n'
            'the confirmation page says it is live.' % os.path.relpath(KEYFILE, ROOT))
    return k


def fetch(vintage, table, key):
    """One table, one vintage, as the API returns it. Returns (rows, raw_bytes)."""
    url = ('%s?get=group(%s)&for=county%%20subdivision:%s&in=state:%s%%20county:%s&key=%s'
           % (BASE % vintage, table, COUSUB, STATE, COUNTY, key))
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                raw = r.read()
            break
        except TimeoutError as e:            # the API is slow under load, not broken
            last = e
            print('  %s %s: timed out, retrying (%d of 3)' % (table, vintage, attempt + 1))
    else:
        raise SystemExit('%s %s: timed out three times — %s' % (table, vintage, last))
    try:
        pass
    except urllib.error.HTTPError as e:
        raise SystemExit('%s %s: HTTP %s\n%s' % (table, vintage, e.code,
                                                 e.read()[:300].decode('utf-8', 'replace')))
    if not raw.strip():
        raise SystemExit(
            '%s %s: the API returned an EMPTY BODY. That is what a wrong GEOGRAPHY looks\n'
            'like here -- HTTP 204, not an error, which a fetcher checking the status code\n'
            'reads as success and writes as nothing. Lunenburg is state 25, county 027,\n'
            'county subdivision 37420.' % (table, vintage))
    # The API answers 200 with an HTML error page for a bad key, so the status is not the
    # check -- the SHAPE of the body is. A fetcher that trusts the status code records an
    # error page as data and reports success.
    if not raw.lstrip().startswith(b'['):
        head = raw[:400].decode('utf-8', 'replace')
        hint = ''
        if 'Invalid Key' in head:
            hint = ('\nThe key is not active yet. Census confirms activation before the '
                    'key starts working;\nit has taken tens of minutes. Nothing is wrong '
                    'with the query.')
        elif 'Missing Key' in head:
            hint = '\nNo key reached the API — check CENSUS_API_KEY.'
        raise SystemExit('%s %s: the API did not return JSON.%s\n\n%s'
                         % (table, vintage, hint, head))
    rows = json.loads(raw.decode('utf-8'))
    if len(rows) < 2:
        raise SystemExit('%s %s: no data rows. Lunenburg is a COUNTY SUBDIVISION '
                         '(%s/%s/%s), not a place.' % (table, vintage, STATE, COUNTY, COUSUB))
    return rows, raw


def save_raw(vintage, table, raw):
    os.makedirs(RAW, exist_ok=True)
    name = 'acs5-%d-%s-lunenburg.json' % (vintage, table)
    path = os.path.join(RAW, name)
    with open(path, 'wb') as fh:
        fh.write(raw)
    return name, hashlib.sha256(raw).hexdigest()


def pivot(rows):
    """The API's header/row pair into {variable: value}."""
    head, data = rows[0], rows[1]
    return dict(zip(head, data))


def collect(key):
    out = []
    for vintage in VINTAGES:
        for table, about in sorted(TABLES.items()):
            rows, raw = fetch(vintage, table, key)
            name, digest = save_raw(vintage, table, raw)
            rec = pivot(rows)
            # Pair every estimate with its margin. `_EA`/`_MA` are annotation flags and
            # carry no figure; `NAME` and the geography columns are not variables.
            ests = sorted(v for v in rec if v.endswith('E') and not v.endswith('EA')
                          and v.startswith(table))
            for var in ests:
                moe_var = var[:-1] + 'M'
                e, m = rec.get(var), rec.get(moe_var)
                out.append(dict(
                    vintage=vintage, table=table, variable=var, estimate=e,
                    moe=m if m not in (None, '') else '',
                    # A negative MOE sentinel means the estimate is controlled to a total
                    # and has no sampling error -- it is NOT a margin of zero.
                    moe_note=('controlled, no sampling error' if m == '-555555555'
                              else ''),
                    geography=rec.get('NAME', ''), about=about,
                    source_file=name, sha256=digest))
    if not out:
        raise SystemExit('nothing collected — refusing to write an empty census file')
    return out


COLS = ['vintage', 'table', 'variable', 'estimate', 'moe', 'moe_note', 'geography',
        'about', 'source_file', 'sha256']


def write(rows):
    with io.open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in COLS})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true',
                    help='re-fetch and fail if the published figures have changed')
    args = ap.parse_args()

    rows = collect(api_key())

    if args.check:
        if not os.path.exists(OUT):
            raise SystemExit('%s does not exist. Run without --check.'
                             % os.path.relpath(OUT, ROOT))
        with open(OUT, newline='', encoding='utf-8') as fh:
            have = list(csv.DictReader(fh))
        now = [{c: str(r.get(c, '')) for c in COLS} for r in rows]
        # sha256 moves whenever Census re-serves the same data, so compare the FIGURES.
        keyed = lambda rs: {(r['vintage'], r['variable']): (r['estimate'], r['moe'])
                            for r in rs}
        a, b = keyed(have), keyed(now)
        if a != b:
            diff = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
            raise SystemExit('census-acs.csv no longer matches the API — %d figure(s) '
                             'differ, e.g. %s' % (len(diff), diff[:4]))
        print('ok: %d figures across %d table(s) and %d vintage(s) still match the API'
              % (len(have), len(TABLES), len(VINTAGES)))
        return 0

    write(rows)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    print('  %d figures — %d tables x %d vintages, every estimate with its margin'
          % (len(rows), len(TABLES), len(VINTAGES)))
    print('  raw responses catalogued in %s' % os.path.relpath(RAW, ROOT))
    print('\n  EVERY FIGURE IS A SAMPLE ESTIMATE. For a town of this size the margins are')
    print('  wide; two figures whose intervals overlap are not different.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
