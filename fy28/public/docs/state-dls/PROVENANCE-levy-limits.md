# DLS Proposition 2 1/2 files: levy limits, levies by class, new growth, exclusions

Written by us, 3 November 2026. Covers the sixteen files `scripts/fetch_dls_levy_limits.py`
landed that day through `ingest.land`, and the extract `sources/data/dls-levy-limits.csv`
that `scripts/extract_levy_limits.py` builds from them.

## Two publications, one series

The Massachusetts Department of Revenue, Division of Local Services, publishes the same
Proposition 2 1/2 tables in two places. Neither reaches back on its own.

### 1. The DLS Gateway (current)

Logi reports on `dlsgateway.dor.state.ma.us`, linked from the panels of the "Category 3a -
Proposition 2 1/2" dashboard, `https://dls-gw.dor.state.ma.us/reports/rdPage.aspx?rdReport=Dashboard.Cat3aPropTaxStat`.
Each export is a POST of the report's own form with every municipality and every year ticked,
to the address in the `url` column of `index.csv`. The export filename is the publisher's
(`rdExportFilename`), and our copy adds the fetch date and the first twelve characters of its
sha256 (`fetch_dls_tax_bills.export_name`).

| our copy | report (`rdReport=`) | years offered |
|---|---|---|
| `ExcessLevyAndOverrideCap-2026-11-03-3484edd04f68.xlsx` | `Prop2.5.ExcessLevyCapandOverride_10_pres` | FY2007-FY2027 |
| `Taxlevybyclass-2026-11-03-f83ad53e0af5.xlsx` | `PropertyTaxInformation.TaxLevies.LeviesByClass` | FY2003-FY2027 |
| `DebtExcLevyAmt-2026-11-03-d985398c450f.xlsx` | `Votes.Prop2_5.DebtExclusionLevyAmt` | FY2002-FY2029 |
| `AllDebtlExclusionResults-2026-11-03-55db12aa2c1f.xlsx` | `Votes.Prop2_5.DebtExclusionVotes` | FY1989-FY2027 |
| `CapitalExclusionVotes-2026-11-03-d65463ae3d9c.xlsx` | `Votes.Prop2_5.Capital` | FY1988-FY2027 |

FY2027 is a blank row in each until the year's rate is set.

The override votes file this archive already held, `OverrideUnderrideVotes.xlsx`, carries the
publisher's export name of `rdReport=Votes.Prop2_5.OverrideUnderride` on the same host. Its
address was recorded as unknown; that report is the likely source. It has NOT been re-fetched
and compared here, so that remains a candidate address, not a checked one (rule 12).

### 2. The retired Municipal Databank

Before the Gateway, DLS posted the same tables as Excel 97 files under
`http://www.mass.gov/Ador/docs/dls/mdmstuf/`. Those addresses no longer serve them. The
Internet Archive holds captures, and the `id_` form of a capture address returns the bytes as
served. Each file is held under the publisher's own filename; `index.csv` gives the capture
address and the original address.

| our copy | original path under `mdmstuf/` | capture | holds |
|---|---|---|---|
| `excp8589.xls` | `Prop2_LevyCap_RefVotes/excp8589.xls` | 20080720052055 | Excess Levy Capacity FY1985-FY1989 |
| `excp9099.xls` | `Prop2_LevyCap_RefVotes/excp9099.xls` | 20080720052110 | Excess Levy Capacity FY1990-FY1999 |
| `excp0009.xls` | `Prop2_LevyCap_RefVotes/excp0009.xls` | 20090912201840 | Excess Levy Capacity FY2000-FY2009 |
| `lvcl8689.xls` | `PropertyTax/lvcl8689.xls` | 20080720052942 | Levies by Class FY1986-FY1989 |
| `lvcl9099.xls` | `PropertyTax/lvcl9099.xls` | 20080720053100 | Tax Levies by Class FY1990-FY1999 |
| `lvcl0009.xls` | `PropertyTax/lvcl0009.xls` | 20090912202243 | Tax Levies by Class FY2000-FY2009 |
| `Grow9299.xls` | `Prop2_LevyCap_RefVotes/Grow9299.xls` | 20080720052050 | New Growth FY1992-FY1999 |
| `grow0009.xls` | `Prop2_LevyCap_RefVotes/grow0009.xls` | 20090912201822 | New Growth FY2000-FY2009 |
| `DebtEx.xls` | `Prop2_LevyCap_RefVotes/DebtEx.xls` | 20080720052059 | Debt exclusion applied to the levy limit FY1989-FY2007 |
| `DebtVotes.xls` | `Prop2_LevyCap_RefVotes/DebtVotes.xls` | 20080720052121 | Every debt exclusion vote, FY1982 on |
| `capital.xls` | `Prop2_LevyCap_RefVotes/capital.xls` | 20080720052140 | Capital exclusion votes FY1988-FY2008 |

**Not landed:** `excp10.xls`, `excp11.xls`, `excp12.xls` and the same years of the other
series. Their captures are blank shells, every figure empty, taken before the year was
certified. The Gateway report covers FY2007 onward, so no year is lost.

## What was looked for and not found

- **New growth before FY1992.** Neither publication has it. Checked: the Internet Archive's
  full listing of `mdmstuf/Prop2_LevyCap_RefVotes/` and `mdmstuf/PropertyTax/`, where the
  first new growth file is `Grow9299.xls`; and the Gateway's new growth report, which starts
  at FY2003. So the components identity cannot be tested for FY1986-FY1991.
- **A published line-by-line levy limit calculation.** DLS's levy limit form (the
  `LL` worksheet of the tax recap) itemises amended prior-year growth and other adjustments.
  No public report of it was found on the Gateway. Checked: the eleven DLS databank
  collection pages on mass.gov (via their Internet Archive captures), the Category 3 and 3a
  dashboards and every report they link, and some sixty guessed report ids under `Prop2.5.`,
  `LevyLimit.`, `TaxRateRecap.` and `PropertyTaxInformation.`. That is why four years
  (FY2013, FY2017, FY2022, FY2025) leave a residual in the components identity.

## How the extract checks itself

See the docstring of `scripts/extract_levy_limits.py`. In short: the components identity and
the exclusions identity are cross-document and must close exactly, or their parts are not
written; the excess-capacity identity and the class sum are a row's own printed arithmetic
and close within $1, labelled. Each row carries the files it was read from and their sha256.
