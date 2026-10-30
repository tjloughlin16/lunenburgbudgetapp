# What reading the 1959-2010 annual town reports found

Internal. Not published, not linked from the site. Written 30 October 2026 at the close of the
work (commits 4b660cac7, 08ce38003). Every count below is a snapshot of that day; re-derive before
quoting (commands at the end). The working history is
`notes/HANDOFF-ANNUAL-REPORTS-1959-2010.md`.

## The short version

- **52 older reports read** (calendar 1959-2010), on top of FY2011-FY2025. **1,818 financial
  pages: 1,647 proven, 171 blocked, nothing else.** Every block has a reason and the document that
  would settle it in `sources/data/page-blocked.csv`.
- **The town's own arithmetic fails on about 105 pages.** These are printed errors, not ours: a
  total that does not equal its lines, confirmed against a render of the page and, where a digit
  was in doubt, a blind second reading.
- **Textract misread figures often enough to matter.** 99 cells corrected by witness, 179 cells
  re-read from Textract's own line text, and one false pass caught (below). Nothing was corrected
  silently: every change names the printed value.
- **"Proven" is weaker than it sounds in two specific ways** (below). Read them before quoting a
  figure from these years as checked.

## 1. Errors in the town's printed books (the documents, not our reading)

About 105 of the 171 blocked pages are blocked because **the page's own arithmetic does not close
as printed.** The rest: 17 where the scan cannot settle a digit, 48 that are not checkable tables
(salary schedules, fee lists, pie charts, comparisons printing no total), 1 the reader cannot land.

The ones worth knowing, by size:

| edition, page | what the page prints | what its own lines require |
|---|---|---|
| 1998 p62 | outstanding debt TOTAL $2,875,830 | $3,535,830: one $660,000 issue left out of the total |
| 1965 p44 | bonded debt grand total principal $168,200 | 1,682,000 (a digit dropped in print) |
| 1961 p35 | Chapter 90 available 3,000.00 | 30,000 |
| 1990 p22 | receipts GRAND TOTAL $8,174,269.84 | the 125 lines read sum to $7,193,802.84 |
| 1975 p76 | a row printing 117,316.71 | 177,316.71 by both of its identities |
| 2005 p85 | FY2006 omnibus TOTAL $22,368,960 | $22,341,960, the category sum AND the Article 3 vote |
| 2007 p55 | Assessors' class valuation TOTALS $1,285,947,900 | lines sum to $1,285,915,200 |
| 1967 p71-72 | voted budget TOTAL $1,612,336.00 | the 81 lines sum to $1,621,336.00 |
| 1987 p31-36 | Voting Machines: 17,420 expended, 18,000 total expended | the schedule's grand total is off by that $580 |

**A pattern, offered as a hypothesis:** a large share of the misses are exactly $10, $100, $200 or
$1,000, or a transposed digit (1969: 595.26 against 595.62; 1997 omnibus $200; 2005-2009
accountant subtotals off $100 again and again). That is the signature of hand-keyed figures, which
fits typed and adding-machine schedules. Nothing here tests it.

**What none of this shows:** that money went missing or was misspent. A printed total that
disagrees with its lines is a typing or printing error until a ledger says otherwise, and every
block names the ledger that would settle it.

## 1a. Years with missing, cut-off or out-of-order pages (the town's PDFs)

These are defects in the copy the town publishes, not in our reading. They come from
`sources/data/document-defects.csv`, the structural checks in
`notes/generated/annual-report-discrepancies.csv` (the index against the folios), and the blocks.

**Content actually missing:**

| edition | what is missing | effect |
|---|---|---|
| 1999 | printed pages 105-106 are not in the PDF, in the middle of the school wage list (it jumps from `Gloria A O'Brien` to `Tamara L Yourk`) | the 278 school rows held sum to $6,018,558.34 against the printed $8,198,325.62; about $2.18M of names are not in the file |
| 1997 | the town employees' wage list stops at `GENDRON` (bottom of the page cut off), and the next two PDF pages are blank scans | no town total is printed, so how much is missing cannot be measured; the school list is complete |
| 1992 | the index names 13 pages the file does not hold, and the PDF has pages after the index's last | the worst-indexed edition; 26 index headings sit on other pages |
| 2000 | the index runs past the last page (it names printed pages up to 132, and the file ends at 131); 2 indexed pages are absent | the 2000 report we hold is the copy the Select Board chair supplied (27 Oct) |
| 1968, 1981, 1988, 1996, 1997, 1999, 2001, 2002, 2005-2007 | 1-2 indexed pages absent in each | none affects a financial table we know of |
| 1994 p42-43 | figures printed short (`$9.50`, `$49.73`) | blocked |
| 1977 p37 | a cash-flow chart printed with a title panel over seven of its twelve columns and the right side run off the page | blocked |

**Scans too poor to settle a digit** (blocked, and each block names the ledger that would settle
it): 1980 p55, 1985 p73-74, 1990 p31, 1993 p30, 1995 p56, 1998 p61, 2000 p89, 2004 p56, 2006
p52/p55, 2007 p61, and 2010 p24, p59-61 and p72-73. 2010 is the poorest scan of the run (200 dpi;
3, 5, 6 and 8 merge).

**Structural oddities that cost nothing but confuse a reader:**

- **Duplicate printed page numbers:** 1983, 1986, 1994-1997, 2000, 2002, 2006, 2007 and 2010.
- **Pages out of order:** 1981, 1983, 1988, 1995, 1997, 2000-2002 and 2005-2007.
- **Extra unindexed pages:** 1965, 1966, 1968 and 2005-2007.
- **Warrant article numbers that skip:** 1984, 1986, 2005, 2006, 2009 and 2010.
- **Pages printed sideways or upside down:** many debt and trust schedules, for example 2006 p69
  and p89, 1965 p44 and 1983 p56-62. All of them are read.

**No school roster printed at all:** 1976, 1986, 1987, 1994. Partial: 1988-1999.

## 2. Errors in OUR reading, found and fixed

- **Textract misreads.** Typical: `$` read as `8`, a dropped leading digit (2010 p61: `8,265.39`
  for 88,265.39), 1987 Police `350,514.20` for the printed $358,514.20, stacked cells merged, a
  comma read as a decimal point.
  - **99 cells corrected by the witness.** Arithmetic pins the cell, a blind scripted reading
    confirms it, and only an exact match is accepted.
  - **179 `cell_readings`.** These cells were re-split from Textract's line text. Of them, 9 were
    blind-confirmed in the 1971-1980 pass.
- **A false pass.** 1970 p49 had been "proven" with the Total Expended figures in the Balance
  column. It now proves honestly in the right column. A check that passes for the wrong reason
  looks identical to one that passes for the right one.
- **A defective tool.** The scratchpad `bwapply.py` kept blind readings whenever nothing on the
  page still failed, even where no identity tested that cell. An audit re-tested all 94 readings
  in 1991-2010 and withdrew 6; one of them was contradicted outright (2005 p55). Do not reuse it
  without the pin test.
- **A missing wire.** `page-blocked.csv` was never applied to the older editions: a blocked page
  stayed `unproven` until 30 October. `read_report_tables.py` now writes `blocked` (and proven
  still outranks it).
- **A footnote nobody read.** 1985 p164 salaries `$3,559,109.26 #`, where `#Includes Escrow`. The
  identity now adds the $101,352.96 escrow.
- **15 pages wrongly blocked.** They had been blocked for "layout our reading cannot separate",
  which is our limit and not the town's. All 15 were withdrawn and proven.

## 3. Things to be aware of before using these years

1. **A proven page is not a page with every row checked.** A page is `proven` when ANY dataset on
   it closes cleanly; another dataset failing on the same page does not demote it. That is the
   FY2011+ rule too. 236 pages across all years are proven with a non-empty `failed_by` (9 of them
   in 1959-2010; 2005 p85 is the example). Row `status` is the grain to check, not page state.
2. **1,798 `declared_identities` were named by eye.** An agent reads an identity the page prints
   (a total row, a stated difference) and the code does the arithmetic. A sample of 20 was checked
   against the renders, and all were printed identities, not fitted sums. The rest rest on the
   agents' discipline.
3. **The $1 tolerance (TJ, 29-30 Oct)** covers printed totals AND a row's own identity. Those rows
   say `within $1 rounding tolerance`; the caveat on /analysis/annual-reports is computed. TJ said
   we would come back to these cases.
4. **Calendar years, not fiscal years.** Editions 1959-2010 carry `fy` = the calendar year of the
   report. The 1973-74 edition covers an 18-month transition. Never difference a 1990 figure
   against FY2011 as if the years were the same kind.
5. **The rosters are names, not staffing.** 1976, 1986, 1987 and 1994 print no roster, and
   1988-1999 is partial. A run of years is a name printed repeatedly; same name is not same person
   (Genevieve Nass). `build_staffing_charts.py` stays FY2011+ (`ROSTERS_FROM_FY`) for this reason.
6. **The tax rate is a rate within one assessment.** Three revaluations (1970, 1982, 1989) break
   the series. Six editions' rates were not read off the fact page: 1972, 1980, 2011-2013 and 2021.
7. **Census figures disagree between editions.** For example, 1980 is 8,375 in the 1983 report and
   8,710 in the 1989 report. Both are kept and neither is charted.
8. **Everything printed is published (TJ, 30 Oct).** That includes named payees, pension
   allowances, pupils' prizes, births, marriages and deaths. The Facebook post deliberately names
   staff and officials only, not vital records.

## 4. Still open (small)

- 2004 p82: one marriage row (Carlos A. Costa) has no date read.
- Brooks House is tagged `central-office`, and 1990 p31 is blocked on one illegible digit. Both are
  defaults TJ may reverse.
- Per-edition `NEEDS.md` "decision for TJ" items on births and marriages are stale. They are now
  landed.
- Not this work, noticed during it: `build/STOP-METERED` still pauses the meeting backlog (its
  note says lift after these reports), and 13 staff-directory files fetched 30 Oct have no
  manifest row.

## 5. What it cost

- **Textract.** October: $59.83 overnight, plus about $0.25 of re-reads on 30 Oct, under the $70
  cap.
- **Scripted `claude -p` witness reads.** About $10 API-equivalent.
- **Agent sessions.** The parallel agents exhausted one 5-hour window on the morning of 30 Oct.
  Per CLAUDE.md, quote a batch like this in both bars before starting.

## Re-derive

    python3 - <<'X'
    import csv,collections
    print(collections.Counter(r['state'] for r in csv.DictReader(open('sources/data/annual-report-pages.csv')) if int(r['fy'])<=2010))
    print(collections.Counter(r['reason'] for r in csv.DictReader(open('sources/data/page-blocked.csv')) if int(r['fy'])<=2010).most_common())
    X
