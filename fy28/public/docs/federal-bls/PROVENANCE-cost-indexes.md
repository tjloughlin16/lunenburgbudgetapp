# federal-bls — the cost indexes, and where they came from

Written by this project on 20 October 2026. The eight `.json` files named by a series ID
(`CIU…`, `CUUR…`) are the Bureau of Labor Statistics' own answers, saved byte for byte as
the API returned them, through `scripts/fetch_bls_cost_indexes.py` and `ingest.land()`.
The household price index beside them (`cpi-u-CUURS11ASA0-*.json`) is described in
`PROVENANCE.md`.

## What they are, and the address of each

| series | what BLS calls it | frequency |
|---|---|---|
| `CIU3026110000000I` | Employment Cost Index, wages and salaries, state and local government workers, elementary and secondary schools; index, December 2005 = 100, not seasonally adjusted | quarterly |
| `CIU3030000000000I` | Employment Cost Index, benefits, state and local government workers, all industries; index, December 2005 = 100, not seasonally adjusted | quarterly |
| `CUURS11ASAF11` | CPI-U, food at home, Boston-Cambridge-Newton, MA-NH; 1982-84 = 100, not seasonally adjusted | monthly |
| `CUUR0100SAH21` | CPI-U, household energy, Northeast region; 1982-84 = 100, not seasonally adjusted | monthly |

Each series was asked for twice, because the API without a registration key answers at
most ten years a request:

    https://api.bls.gov/publicAPI/v2/timeseries/data/<series>?startyear=2008&endyear=2017
    https://api.bls.gov/publicAPI/v2/timeseries/data/<series>?startyear=2018&endyear=2026

saved as `<series>-2008-2017.json` and `<series>-2018-2026.json`. The sha256 of each is in
`sources/data/archive-manifest.csv`, and the address it came from is its `upstream`.

## The publisher's filename

**There is none.** As for the household index: an API answer is not a file the publisher
named. The series ID is the name a resident asks BLS for. The filenames are ours.

## What was asked for and is NOT here

- **A benefits index for schools alone.** `CIU3036110000000I` -- the benefits twin of the
  school wage series -- does not exist ("Series does not exist", 20 October 2026). The
  all-workers state and local government benefits series is the nearest BLS publishes.
- **A price index for school buses.** `PCU485410485410` (producer prices, school and employee
  bus transportation) and the wider ground passenger transport groups tried do not exist.
- **Boston-area household energy for FY2025.** `CUURS11ASAH21` is published to December
  2024 and not after, so a July-to-June FY2025 average cannot be built from it. The
  Northeast series is used instead, for every year, so nothing is spliced.
- BLS's flat files (`download.bls.gov/pub/time.series/`) answered 403, as on 18 October.

A value printed `-` is one BLS did not publish (footnote: *"Data unavailable due to the
2025 lapse in appropriations"*, October 2025). It falls outside every year this project
uses, and it is skipped, never filled.

## What we compute from them, and say is ours

A **fiscal-year average**, July to June: for the Employment Cost Index, the four quarterly
values for September and December of the year before and March and June of the fiscal year
(the ECI is measured in the pay period including the 12th of the third month of each
quarter); for a monthly CPI series, the twelve months July to June. BLS publishes neither.
Which series stands for which kind of school spending, and why, is OUR choice, in
`sources/data/inflation-cost-index-map.csv`, and it is used by
`scripts/build_inflation_topic.py` for /school-spending-history/inflation-and-school-costs.

A national or regional index is not Lunenburg's price. It says what that kind of thing cost
employers or households generally, not what the district paid.
