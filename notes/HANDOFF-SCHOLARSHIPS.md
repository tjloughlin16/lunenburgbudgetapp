---
status: open
updated: 2026-11-04
next: (5) DEPLOY -- only when TJ says so (rule 10); build the site once, check /school-all-funds/school-scholarships at phone width, then deploy and sync_d1.py (two new tables, and money_gaps lost a row). Steps 1-4 are DONE, nothing committed -- see "Where it stands".
---

# School scholarships: every fund, what it is for, and what it pays out each year

TJ, 4 November 2026, on the first version of `/school-all-funds/school-scholarships`: *"this page
is lacking for sure. we should get details on every scholarship (what they are for), and it seems
the annual reports print info? we should fetch that info before deploying, and build additional
charts with the info. im looking to see how much is given out each year by each scholarship."*

**The page is built and committed (621e72c27) and NOT deployed. Hold it until the payouts are in.**

## Where it stands (4 November 2026, steps 1 and 2 done, not committed)

`scripts/extract_scholarship_funds.py` writes `sources/data/scholarship-funds.csv`: **174 proven
rows, every year FY2011-FY2025**, 7 to 12 of the 14 funds a year. Read by BOTH instruments --
Vision 79 rows, Textract (cached, no new spend) 83, `trust-fund-matrix.csv` 12 for FY2025.
**Cross-check the proofs do not use: each fund's ending cash ties to its next beginning balance,
135 of 135 links, to the cent.**

What it took, so nobody re-learns it:
- **Textract pages set sideways** (FY2023 p49 and others) report geometry in the image frame;
  `textract_boxes()` turns them back from each line's polygon. 0 -> 11 rows on that page.
- **`UNITIL STOCK` rows are a second account** of the Mabel Allen and Harwood prizes, keyed
  `account = stock`. Keyed on the fund alone they took the prize row's slot.
- **FY2017 came out positional** (`activity_0..5`) though `R.LAYOUTS[2017]` is NINE and the page
  prints NINE; `name_positional()` applies it only on an exact fit. Not fixed in the shared
  reader -- that would move `extract_stabilization.py` output too, and wants its own look.
- **`paid_out` is the NET of the outflow columns**, never per column: Mabel Allen and Harwood
  take earnings IN most years. An exact contribution/transfer offset on one row is an
  earnings-to-principal move (`reclassified`; Cowdry FY2017, $12,528.46), not an award. A
  general contribution is NOT netted -- gifts and awards share rows (Nelson FY2012).
- **Not in `check_generated.py`**, like `extract_gross_wages.py`: it reads a gitignored cache.
  It refuses to run without that cache rather than write a short file.

**Paid out, all funds** (our reading of money leaving a fund as awards; rule 7):
FY2012-FY2014 about $13,600-$15,600 a year; FY2015-FY2022 $0-$8,346; **FY2011, FY2017, FY2023
and FY2024 print $0 for every fund** -- checked against the page for FY2017 and FY2023 (the
transfer columns read $0.00 and Cowdry's earnings accumulate), so a real printed zero, cause
unknown. FY2025 $9,852. Regenerate these from the CSV before quoting them anywhere (rule 2).

Still open in the data: Nelson and Crouse FY2014, Curtis FY2020 have no proven row; Linde
Sacksen FY2019/23/24 print balances only (payout unknown); Geof Lucier and Vincent Joseph never
prove. **FY2025's "scholarship funds" group also holds CHESTER MOSSMAN TEEN CENTER and LUNENBURG
ATHLETIC BOOSTER**, which are not on `FUNDS` -- whether they belong on a school scholarship page
is TJ's call.

## Steps 3 and 4 (4 November 2026, done, not committed)

**Purposes:** `sources/data/scholarship-purposes.csv`, seven rows, every quote re-found verbatim in its
text on each build of the page (`purposes()`). Stated by a document: Vincent Joseph (SC minutes
2025-01-08: "to go to an athlete that is pursuing college"), Beth N. Curtis (award sheet), Joseph
Harwood ("Promotes a spirit of cooperation", 1970 report p121), Mabel Allen ("ENGLISH AWARD", 1965
p117), Geof Lucier (SC minutes 2024-06-12). Wakefield is NAMED only (1985 p140). Pete Lincoln rests on
CAPTIONS only (SC recording 2025-01-08, 45:19, "Liberal Arts") and is counted apart. Searched and NOT
found for Cowdry, Busque, Crouse, Stanley, Czelusniak, Nelson, Sacksen: annual reports 1959-2025,
SC and Select Board minutes, SC captions. Next place to look: the Town Meeting votes that ACCEPTED
each gift, and the trust documents (`fy27-budget/trust-funds/background-information/`).

**The page** (`build_school_scholarships.py`, rebuilt): leads on paid out by fund by year (stacked,
four largest + the rest), then WHAT EACH FUND HOLDS (ranking, FY2025 ending cash -- TJ asked for it
back: the $430k Cowdry fund beside the near-empty ones is the obvious picture), then earned against paid out, then per-fund totals, purposes, coverage.
Lead: four funds that once held over $1,000 now hold under $200 (Stanley $14); Cowdry paid out about
half what it earned and grew. Both thresholds are OURS, said in the code.

Registered: `build_source_index.py` (both CSVs published at /docs/data/), `build_db.py` REFERENCE,
`table-semantics.csv`. Gaps: the history row is removed (answered); the awards row is reworded.

## The finding that makes this cheap: the reader already proves these rows

The scholarship funds print on the same trust fund summary pages as the stabilization funds, and
`scripts/read_trust_table.py` reads those pages year by year (CLAUDE.md 13b). `R.rows(boxes, fy,
geom={})` returns EVERY row it reads (`name`, `cells`), not only stabilization; `R.verify(cells)`
proves a row on the table's own identity. Load a year's boxes the way `extract_stabilization.py`
does: `pdf_tables.read_boxes(path)` with `path` from `extract_stabilization.year_files()`.

**The payout is two columns:** `disburse_principal` + `transfers_earnings`, negative = paid out.
FY2018 p45, every scholarship row proven: Nelson -1,198.71 + -101.29 = **$1,300**; Stanley -941.50
+ -58.50 = **$1,000**; Curtis -434.79 + -65.21 = **$500**; Busque **$500**; Cowdry **$2,000**. The
round totals read as awards. That is OUR reading: the table says money left the fund, not why.
A POSITIVE `disburse_principal` is money IN (Pete Lincoln FY2018: +15,000.00, the fund's start).

**Scholarship rows proven per year off the Vision boxes** (probe, 4 Nov 2026; a `SCHOLAR|PRIZE|AWARD`
name filter, so prizes named only `SCHOOL` -- Harwood -- are missed by it):

| FY | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rows | 5 | 0 | 7 | 0 | 7 | 5 | 1 | 9 | 4 | 6 | 1 | 5 | 0 | 4 |

Pages: FY2011 p74, FY2013 p79, FY2014 p38, FY2015 p39, FY2016 p41, FY2017 p38, FY2018 p45, FY2019
p46-47, FY2020 p40-41, FY2021 p41, FY2022 p42-43, FY2023 p49, FY2024 p34-35. FY2025 is already
proven in `trust-fund-matrix.csv`. The probe: a few lines over `R.rows` -- rewrite it as the
extractor, do not keep it.

## The plan, in order

1. **The extractor.** `extract_scholarship_funds.py` writes one row per fund per year: the printed
   columns, `paid_out` (the two columns above, sign-flipped), the page, and the proof. Use
   `verify_from_prior` where `verify` alone does not close, as `extract_stabilization.py` does. Key
   funds by surname (the list in `build_school_scholarships.py`, `FUNDS`): one fund prints as
   COWDRY and COWDREY.
2. **The short years** (FY2012, FY2014, FY2017, FY2021, FY2023). Vision lost figures. Textract has
   cached cells for the annual reports' financial pages (`build/textract/cache`, see
   `extract_gross_wages.py` `_textract_words` for loading words); try those boxes through the same
   `R.rows`. A page still short is refused and registered, never guessed.
3. **What each is for.** Five reports name the funds in prose (FY2011, FY2014, FY2019, FY2021,
   FY2025: `grep -il cowdry sources/town-annual-reports/text/41*.txt`). Also
   `python3 scripts/search_minutes.py "scholarship" --board school-committee`. A purpose is quoted
   with its document and page; a fund with none found says so. RECIPIENTS ARE STUDENTS: if a report
   prints award winners by name, check `notes/process/DATA-PRIVACY.md` before using them; the page
   needs amounts and counts, not names.
4. **The charts.** Paid out by fund by year, stacked bars (composition); each fund's balance as
   small multiples or a line (trend); the coverage chart already on the page shows the years read.
5. **Then deploy**, and update the two money-gaps rows the page registered (the history row closes
   once the years are read).

## Cost

Steps 1, 2 and 4 are code over files already held: no reading spend. Step 3 is search. None of it is
page-by-page ingest, so it does not need isolated agents unless step 2 leaves pages to read by eye.
