"""Who lives in Lunenburg — age, households, income by age, and tenure, from the Census.

    export CENSUS_API_KEY=...          # or put it in .census-key, which is gitignored
    python3 scripts/fetch_census_acs.py          # fetch, land what changed, rewrite the CSV
                                                 #   (the refresh runs exactly this)
    python3 scripts/fetch_census_acs.py --check  # re-fetch and compare; writes nothing

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

RUN UNATTENDED, ON A CADENCE, AND WHAT THAT CHANGES

Every raw response goes through `ingest`: a response not yet held is landed with
`ingest.land()`, pushed and read back before it is filed. A response that is held is
compared by its DATA -- the header and the values, parsed -- not by its bytes, because the
check below records that the sha256 has moved when Census re-served the same figures. Same
data lands nothing, and the CSV row keeps the sha256 of the copy we hold, so an unchanged
run leaves census-acs.csv byte-identical. Different data for a vintage already published is
Census revising it in place, and is landed as a version with `ingest.land_version()`, which
keeps the original in the bucket and the latest at the plain name.

A NEWER RELEASE IS REPORTED, NOT FETCHED. Census adds one five-year release a year, as a
new address (`/data/<year>/acs/acs5`). Which release is newest is computed from today by
asking that address, and when it is newer than VINTAGES the run says so and exits 0 -- it
looked. It does not land the new vintage, because three things are written against these
two by name and would fail the next build if one appeared unattended: build_source_index.py
catalogues every raw response here by filename, and build_property_owners.py and
build_homes_and_taxes_topics.py read 2023 and 2018 and refuse anything else ("re-read every
label here"). Moving to a new vintage is a decision about the pages, so it is a person's.

ONE FIXED COMMAND, BOUNDED. 14 requests (seven per vintage), each with a timeout, and the
whole run stops -- non-zero, as could-not-look -- once DEADLINE seconds have gone.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
# The refresh runs this unattended, so a slow API must not hold the run for hours: three
# tries at 180 seconds each, over 14 requests, was a worst case of two hours.
DEADLINE = 600
TIMEOUT = 90
_START = time.monotonic()

# The four tables that close the gap. Group queries (`group(B01001)`) return every
# variable in the table, estimates and margins together, which is why they are fetched
# whole rather than variable by variable: a hand-picked subset is a decision about what
# matters made before anybody has looked.
# One statewide table, fetched for EVERY Massachusetts municipality rather than for
# Lunenburg alone. A rank is a claim about 350 other places, and quoting one from a query
# nobody kept is a derived thing passed off as an observed one -- rule 13. So the whole
# column is stored and the rank is recomputed from it.
STATEWIDE = {
    'B19013_001E': 'Median household income — every Massachusetts municipality, so '
                   'Lunenburg can be ranked against them rather than described',
}

TABLES = {
    'B01001': 'Sex by age — the 65-and-over share, and every band beneath it',
    'B11005': 'Households by presence of people under 18 — the real denominator for '
              '"the 30% who have students in the school"',
    'B19049': 'Median household income in the past 12 months, by age of householder — '
              'what turns "seniors on fixed incomes" from a claim into a number',
    'B25003': 'Tenure — owner-occupied against renter-occupied',
    'B25038': 'Tenure by year the householder moved in — how long the owners have owned, '
              'in bands; the question behind "taxed out of a house bought decades ago"',
    'B25039': 'Median year the householder moved in, owners and renters',
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


def get(url, key, what):
    """The body at `url` with the key appended, or SystemExit -- which the refresh reads as
    could-not-look. The key is added HERE and nowhere else, so the address that is printed,
    recorded as `upstream` and published never carries it."""
    last = None
    for attempt in range(3):
        left = DEADLINE - (time.monotonic() - _START)
        if left < 5:
            raise SystemExit('%s: the run passed its %d-second deadline' % (what, DEADLINE))
        try:
            with urllib.request.urlopen(url + '&key=' + key, timeout=min(TIMEOUT, left)) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            raise SystemExit('%s: HTTP %s\n%s' % (what, e.code,
                                                   e.read()[:300].decode('utf-8', 'replace')))
        except (TimeoutError, urllib.error.URLError) as e:   # slow under load, not broken
            last = e
            print('  %s: %s, retrying (%d of 3)' % (what, type(e).__name__, attempt + 1))
    raise SystemExit('%s: failed three times — %s' % (what, last))


def fetch(vintage, table, key):
    """One table, one vintage, as the API returns it. Returns (rows, raw_bytes, url) --
    the url WITHOUT the key."""
    url = ('%s?get=group(%s)&for=county%%20subdivision:%s&in=state:%s%%20county:%s'
           % (BASE % vintage, table, COUSUB, STATE, COUNTY))
    raw = get(url, key, '%s %s' % (table, vintage))
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
    return rows, raw, url


def same_data(a, b):
    """Two API answers hold the same figures: the same header and the same rows, in any
    order. Parsed, because the bytes are not promised to be stable between two serves."""
    pa, pb = json.loads(a), json.loads(b)
    canon = lambda rs: (rs[0], sorted(json.dumps(dict(zip(rs[0], r)), sort_keys=True)
                                      for r in rs[1:]))
    return canon(pa) == canon(pb)


def keep_raw(vintage, table, raw, url, land):
    """The response as we hold it: (filename, sha256, bytes). With `land`, a response not
    held, or holding different figures, goes through ingest first; without it (--check),
    nothing is written and the answer is reported as fetched."""
    name = 'acs5-%d-%s-lunenburg.json' % (vintage, table)
    key = 'state-census/' + name
    path = os.path.join(RAW, name)
    held = open(path, 'rb').read() if os.path.exists(path) else None
    if held is not None and same_data(held, raw):
        return name, hashlib.sha256(held).hexdigest(), held
    if land:
        import ingest
        if held is None:
            ok, why = ingest.land(key, raw, upstream=url)
        else:
            print('  %s: Census has revised the figures; landing a version' % key)
            ok, why = ingest.land_version(key, raw, upstream=url)
        if not ok:
            raise SystemExit('%s: %s' % (key, why))
    return name, hashlib.sha256(raw).hexdigest(), raw


def newest_release():
    """The newest five-year release Census answers for, asked rather than assumed. A
    release for year Y comes out in the December of Y+1 -- the 2020-2024 release was
    there by 28 October 2026, 2021-2025 was not -- so the candidates are the last three
    years. The metadata address needs no key. None if none answers, which only a network
    failure explains, and the caller treats it as could-not-look."""
    y = datetime.date.today().year
    for v in range(y - 1, y - 4, -1):
        try:
            with urllib.request.urlopen(BASE % v + '.json', timeout=30) as r:
                if r.status == 200:
                    return v
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise SystemExit('newest release: HTTP %s from %s' % (e.code, BASE % v))
        except (TimeoutError, urllib.error.URLError) as e:
            raise SystemExit('newest release: %s' % e)
    return None


def pivot(rows):
    """The API's header/row pair into {variable: value}."""
    head, data = rows[0], rows[1]
    return dict(zip(head, data))


def collect_statewide(key, vintage, land):
    """Median household income for every county subdivision in Massachusetts."""
    var = sorted(STATEWIDE)[0]
    url = ('%s?get=NAME,%s,%s&for=county%%20subdivision:*&in=state:%s'
           % (BASE % vintage, var, var[:-1] + 'M', STATE))
    raw = get(url, key, 'statewide %s' % vintage)
    if not raw.lstrip().startswith(b'['):
        raise SystemExit('statewide %s: %s' % (vintage, raw[:200].decode('utf-8', 'replace')))
    name, digest, raw = keep_raw(vintage, 'B19013-massachusetts', raw, url, land)
    rows = json.loads(raw.decode('utf-8'))
    head, out = rows[0], []
    for r in rows[1:]:
        d = dict(zip(head, r))
        est = d.get(var)
        # -666666666 is the Census sentinel for "estimate not available", NOT a figure.
        if est in (None, '', '-666666666'):
            continue
        out.append(dict(
            vintage=vintage, table='B19013', variable=var, estimate=est,
            moe=d.get(var[:-1] + 'M', ''), moe_note='',
            geography=d.get('NAME', ''), about=STATEWIDE[var],
            source_file=name, sha256=digest))
    if len(out) < 300:
        raise SystemExit('statewide %s returned only %d municipalities — Massachusetts '
                         'has about 350, so something is filtered' % (vintage, len(out)))
    return out


def collect(key, land):
    """Every figure, from the responses AS HELD once `land` has brought them in."""
    out = []
    for vintage in VINTAGES:
        for table, about in sorted(TABLES.items()):
            _rows, raw, url = fetch(vintage, table, key)
            name, digest, raw = keep_raw(vintage, table, raw, url, land)
            rec = pivot(json.loads(raw.decode('utf-8')))
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
    for vintage in VINTAGES:
        out.extend(collect_statewide(key, vintage, land))
    if not out:
        raise SystemExit('nothing collected — refusing to write an empty census file')
    return out


COLS = ['vintage', 'table', 'variable', 'estimate', 'moe', 'moe_note', 'geography',
        'about', 'source_file', 'sha256']


def write(rows):
    """Beside the target and renamed onto it, and not at all when nothing changed -- so an
    unchanged run leaves the file, its mtime and git untouched."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, '') for c in COLS})
    if os.path.exists(OUT) and io.open(OUT, encoding='utf-8', newline='').read() == buf.getvalue():
        return False
    with io.open(OUT + '.tmp', 'w', encoding='utf-8', newline='') as fh:
        fh.write(buf.getvalue())
    os.replace(OUT + '.tmp', OUT)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true',
                    help='re-fetch and fail if the published figures have changed')
    args = ap.parse_args()

    rows = collect(api_key(), land=not args.check)
    newest = newest_release()
    if newest is None:
        raise SystemExit('could not reach %s for any recent year' % (BASE % 0).replace('/0/', '/<year>/'))
    if newest > max(VINTAGES):
        print('NOTICE: Census has released the %d-%d five-year estimates; this project '
              'publishes %s. Moving to it is a decision about the pages -- see the docstring.'
              % (newest - 4, newest, ' and '.join(map(str, VINTAGES))))

    if args.check:
        if not os.path.exists(OUT):
            raise SystemExit('%s does not exist. Run without --check.'
                             % os.path.relpath(OUT, ROOT))
        with open(OUT, newline='', encoding='utf-8') as fh:
            have = list(csv.DictReader(fh))
        now = [{c: str(r.get(c, '')) for c in COLS} for r in rows]
        # sha256 moves whenever Census re-serves the same data, so compare the FIGURES.
        # KEYED ON THE GEOGRAPHY TOO, and without it this check was fail-open. B19013 is
        # fetched for every Massachusetts municipality and every one of those 350 rows
        # carries the SAME variable, so a key of (vintage, variable) collapsed the whole
        # statewide column onto one entry -- the last row written -- and 349 of them could
        # have changed without this noticing. The rank and the overlap count on
        # /lunenburg-by-the-numbers are computed from exactly those rows.
        keyed = lambda rs: {(r['vintage'], r['variable'], r['geography']):
                            (r['estimate'], r['moe']) for r in rs}
        a, b = keyed(have), keyed(now)
        if a != b:
            diff = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
            raise SystemExit('census-acs.csv no longer matches the API — %d figure(s) '
                             'differ, e.g. %s' % (len(diff), diff[:4]))
        print('ok: %d figures across %d table(s) and %d vintage(s) still match the API'
              % (len(have), len(TABLES), len(VINTAGES)))
        return 0

    if not write(rows):
        print('unchanged: %s — %d figures, the API still answers what we hold'
              % (os.path.relpath(OUT, ROOT), len(rows)))
        return 0
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    print('  %d figures — %d tables x %d vintages, every estimate with its margin'
          % (len(rows), len(TABLES), len(VINTAGES)))
    print('  raw responses catalogued in %s' % os.path.relpath(RAW, ROOT))
    print('\n  EVERY FIGURE IS A SAMPLE ESTIMATE. For a town of this size the margins are')
    print('  wide; two figures whose intervals overlap are not different.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
