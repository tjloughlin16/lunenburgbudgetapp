---
status: open
updated: 2026-11-04
next: (1) write scripts/extract_scholarship_funds.py -- read_trust_table.rows() over every year's trust pages, keep the scholarship rows, prove each, write sources/data/scholarship-funds.csv. (2) Textract cells for the years the Vision read leaves short. (3) what each scholarship is for. (4) add the payout charts to build_school_scholarships.py, THEN deploy.
---

# School scholarships: every fund, what it is for, and what it pays out each year

TJ, 4 November 2026, on the first version of `/school-all-funds/school-scholarships`: *"this page
is lacking for sure. we should get details on every scholarship (what they are for), and it seems
the annual reports print info? we should fetch that info before deploying, and build additional
charts with the info. im looking to see how much is given out each year by each scholarship."*

**The page is built and committed (621e72c27) and NOT deployed. Hold it until the payouts are in.**

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
