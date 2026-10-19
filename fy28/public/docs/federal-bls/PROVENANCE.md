# federal-bls — where these files came from

Written by this project on 18 October 2026. The four `.json` files beside it are the
Bureau of Labor Statistics' own answers, saved byte for byte as the API returned them.

## What they are

**Consumer Price Index for All Urban Consumers (CPI-U), Boston-Cambridge-Newton,
MA-NH, all items, not seasonally adjusted. BLS series `CUURS11ASA0`. Index base
1982-84 = 100.** Bimonthly: BLS publishes this area in January, March, May, July,
September and November, January 1990 to September 2026 in these files.

| file | address it was fetched from |
|---|---|
| `cpi-u-CUURS11ASA0-1990-1999.json` | https://api.bls.gov/publicAPI/v2/timeseries/data/CUURS11ASA0?startyear=1990&endyear=1999 |
| `cpi-u-CUURS11ASA0-2000-2009.json` | https://api.bls.gov/publicAPI/v2/timeseries/data/CUURS11ASA0?startyear=2000&endyear=2009 |
| `cpi-u-CUURS11ASA0-2010-2019.json` | https://api.bls.gov/publicAPI/v2/timeseries/data/CUURS11ASA0?startyear=2010&endyear=2019 |
| `cpi-u-CUURS11ASA0-2020-2026.json` | https://api.bls.gov/publicAPI/v2/timeseries/data/CUURS11ASA0?startyear=2020&endyear=2026 |

The sha256 of each is in `sources/data/archive-manifest.csv`.

## The publisher's filename

**There is none.** An API answer is not a file the publisher named; the address above IS
its name, and asking BLS for "series CUURS11ASA0" is how a resident gets the same figures
back. The filenames here are ours.

## Why the API, and why four files

The flat file BLS publishes for this survey (`download.bls.gov/pub/time.series/cu/`),
which carries BLS's own annual averages, refused this project's requests with HTTP 403
on 18 October 2026. The public API, used without a registration key, answers at most ten
years a request and gives no annual averages, so the series arrived as four requests.

`CUURA103SA0`, the series code this area carried before BLS's 2018 geographic revision,
is no longer served ("Series does not exist"). BLS carries the area's history under the
new code back past 1990, so **nothing is spliced**: every value here is from one series.

## What we compute from it, and say is ours

A **fiscal-year average**: the six bimonthly values from July of the year before to May
of the fiscal year (FY2024 = July 2023 to May 2024), averaged. BLS publishes calendar-year
averages, not fiscal-year ones, so every fiscal-year figure is OUR arithmetic. It is used
by `scripts/build_spending_staff_students_topics.py` to restate school spending in FY2024
dollars, the latest year whose spending is actual rather than budgeted.
