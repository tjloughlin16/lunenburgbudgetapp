# MassGIS Level 3 assessors' parcels — Lunenburg (town 162), FY2026

## Where it came from

**MassGIS (Bureau of Geographic Information), Commonwealth of Massachusetts.** Downloaded
13 September 2026 by this project, by script, from the direct file address:

<https://s3.us-east-1.amazonaws.com/download.massgis.digital.mass.gov/shapefiles/l3parcels/L3_SHP_M162_LUNENBURG.zip>

The index page that lists it is MassGIS's *Property Tax Parcels* data page
(<https://www.mass.gov/info-details/massgis-data-property-tax-parcels>). The package is the
Level 3 standard: parcel polygons plus the town assessor's own CAMA extract for the fiscal
year, joined by LOC_ID. The assessing table here is `M162Assess_CY26_FY26.dbf` — **FY2026,
5,303 records** — with, per parcel: assessed building, land and total value; use code; last
sale date and price (LS_DATE, LS_PRICE); year built; lot size; owner name and mailing
address.

## What it is, and is not

- The values are the assessor's FY2026 assessments — the same figures the tax bill is
  computed from. A parcel's bill is its TOTAL_VAL × the FY2026 rate.
- **LS_DATE is the last recorded deed, not the date the household arrived.** About a third
  of the deeds carry a nominal price (under $1,000): transfers into trusts, between family
  members, on a death. Each of those resets the date without changing who lives there, so a
  tenure read off LS_DATE is a LOWER BOUND — the true share of long-held homes is higher.
- **Owner names and mailing addresses are in the file.** They are public record and the
  state publishes them; this project uses the file in aggregate only and publishes no name.

## The file

| our copy | sha256 | bytes |
|---|---|---|
| `L3_SHP_M162_LUNENBURG.zip` | `cb0e39d142b1b353d114cc9dc1dc89be5e11b467f974228aaa94ee7e6d6ca69d` | 1697201 |
