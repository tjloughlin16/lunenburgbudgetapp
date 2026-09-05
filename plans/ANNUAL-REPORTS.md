# Turning fifteen years of annual town reports into data

**Opened 4 September 2026.** Sixteen documents, 2,751 pages, **819 blocks of structured
data** found by reading them end to end with no list of what to look for.

Status vocabulary: **done** · **doing** · **next** · **blocked** · **open**

The full account of how the reader was built and what broke it is in
`notes/findings/TOWN-ARCHIVE.md`. The catalogue of what the reports contain is
`sources/data/annual-report-catalogue.csv` and `notes/generated/ANNUAL-REPORT-CATALOGUE.md`.

---

## The rule this plan is built on

**Each report is its own document, and no pattern carries across years.** Fifteen years of
different town managers, superintendents and principals; nobody maintaining a format. Every
extractor written against a heading has silently succeeded for the years that matched and
failed for the rest — and *the years it missed read as years the town published nothing*.

Three times, three extractors, same shape: `SUMMARY OF RECEIPTS` lost FY2023's table,
`STAFF ROSTER` lost most of FY2025's rosters, `GRAND TOTAL` matched receipts detail against
a trust fund's total.

So every step below locates its table **from the catalogue**, which was built by reading,
not by matching.

---

## Stage 0 — Foundations already in place — **done**

| item | status |
|---|---|
| All 16 reports downloaded, FY2011–FY2025 | **done** |
| OCR at scale 6.0 with `/Rotate` honoured; 2,721 of 2,751 pages readable | **done** |
| `scripts/pdf_tables.py` — instrument selection, column ruler, OCR geometry, reconciliation | **done** |
| Per-page survey — `sources/data/annual-report-survey.csv` | **done** |
| Full discovery catalogue — 819 tables, `sources/data/inventory/FY*.json` | **done** |
| Receipts — 737 source-years, 401 reconciled + 336 partial, with provenance | **done** |
| Ballot questions — 7 records, every tally verified against its own precinct figures | **done** |

---

## Stage 1 — Finish what is half-built — **doing**

| # | item | status | why it matters |
|---|---|---|---|
| 1.1 | **Placement counts → CSV**, FY2013–FY2025 | **done** — 13 years, both checks pass | The biggest find of the day exists only in conversation. Rule 13: a conversation is not a source. Answers a standing question. |
| 1.2 | **Re-run the school rosters against the catalogue's true page ranges** | **partly done** — 84 pages located (was 29); the agent reading pass is NOT re-run, so the roster CSVs remain the old 29-page version — locator rewritten to read the catalogue; 84 pages across all 15 years, up from 29 across 10. Blocked on 1.6. | Current data was built by heading search *before* the catalogue. FY2025's rosters run pp100–110; four pages were read. The year-over-year series is distorted by missing pages, not by staffing. |
| 1.3 | **Move the OCR output into the repo** | **done** — `sources/town-budget/ocr/`, with a README on how to regenerate | 13MB of positioned text lives in a scratchpad. Until it has a home nothing here is reproducible. |
| 1.4 | FY2023 receipts — geometry-aware re-extraction | **partly** — the page reads now, but its SUMMARY OF RECEIPTS panel still does not, so the year stays partial | The page is printed sideways; OCR collapsed it to 7 lines. The table is there and has a GRAND TOTAL. |
| 1.5 | FY2011 payroll pp98,100 — re-OCR at 180° | **superseded by 1.6** | Scanned upside down; departments read `TOOHOS`. One case of the general problem below. |
| 1.6 | **Re-OCR with per-page orientation calibration** | **done** — all 16 documents, 0 sideways pages, verified per document | `/Rotate` does not say what the renderer will do, and orientation varies *within* a document — the 17-page FY2016 addendum needs three different rotations. About 700 pages across the archive were read sideways, and it was invisible: the text was all there, correctly spelled, in the wrong geometry. |

---

## Stage 2 — The datasets worth building, in order — **extracted, mostly unreconciled**

All twelve are captured and in the database. **Two reconcile; the rest do not**, and the
residual is recorded on every row. An unreconciled extract is a transcription, not a
verified figure — the rows are real, read at their own position in the column they were
printed in, but rule 13 governs what may be quoted and this may not be.

Closing those residuals is the next body of work, and the evidence says where to look:
columns 2 and 3 (receipts, disbursements) are consistently further out than columns 1 and 4
(opening, closing balances), which points at row loss or column splitting in the middle of
the table rather than at its ends.


Ordered by **years covered × has a printed total**. A table with a printed total can be
checked against itself; one without can be transcribed and never verified, and that
distinction decides what may be published.

| # | dataset | years | anchor | notes |
|---|---|---|---|---|
| 2.1 | **Appropriations by department** | 13 | GRAND TOTAL | The omnibus split over time. FY2024 has none — the accountant's section was replaced by MUNIS schedules. |
| 2.2 | **Special revenue funds** | 14 | per-fund | Turns `fund_activity` from a snapshot into a history. FY2016 p32 is an unheaded duplicate of p33 — 28 funds double-count if read naively. |
| 2.3 | **Trust funds** | 15 | printed totals | FY2013's rows survived OCR with *no* fund-name column; FY2014 labels them and its opening balances equal FY2013's closing. |
| 2.4 | **Outstanding debt / five-year debt** | 15 | printed totals | FY2018 silently corrects a $2.6M digit-drop in FY2017. |
| 2.5 | **Capital projects** | 15 | printed totals | FY2021 carries four different capital totals in one report. |
| 2.6 | **Employee gross wages** | ~8 | none | No heading in any year. FY2025 prints two side-by-side alphabetical runs; FY2016 starts mid-alphabet at BENOIT. Calendar year, not fiscal. |
| 2.7 | **Election results incl. ballot questions** | 7+ | printed totals | Extends `ballot-questions.csv`. FY2020 prints an entire primary twice. |
| 2.8 | **Town officials and committee rosters** | 12 | none | Who held which office, when. The civic record the money cannot show. |
| 2.9 | **Valuation, tax rate, new growth** | 13 | printed totals | FY2016 reprints FY2015 valuations with only the account count updated. |
| 2.10 | **Vital records** | 12 | none | FY2018's moved onto an election tally sheet; FY2021's page is a failed scan. |
| 2.11 | **Department activity** (fire, police, building, library) | 12+ | stated totals | Fire call categories fail to sum in most years — record both. |
| 2.12 | **MCAS and enrollment** | 10+ | none | Cross-checkable against DESE. |
| 2.13 | **Monty Tech** — assessments, enrollment by program | 6 | printed totals | A 20-year assessment history for 18 towns sits in FY2017 and vanishes in FY2018. |

---

## Stage 3 — Make it usable — **open**

| # | item | status |
|---|---|---|
| 3.1 | Every new CSV into `build_db.py`, with a provenance doc each | **done for what exists** — 8 datasets loaded, 19 of 19 existing reconciliations still tie. Rosters and receipts reload after 1.6. |
| 3.2 | A verifier per dataset that **recomputes** rather than re-reads | **open** |
| 3.3 | Cross-check every series against DESE where one exists | **doing** — placement counts done, and the answer is **DESE cannot check them**: its out-of-district FTE counts vocational + choice + charter + SPED together and runs ~10x larger. Recorded so nobody reaches for it. |
| 3.4 | Correct `CLAUDE.md` — placement counts and staff headcounts are **published** | **done** — both standing questions rewritten, and rule 11's "a headcount nobody publishes" corrected. Neither is presented as settled: a placement count says nothing about which fund paid, and a roster has no FTE. |
| 3.5 | Publish the catalogue so a resident can see what the town has printed and where | **open** |

---

## The same bug keeps arriving in different clothes

Worth naming, because it has now cost a day and every instance looked like a different
problem:

**Something we rendered got quoted as though it were the document.** Rule 13 states it;
these are the ways it has actually shown up here.

| what was matched | what the page says | what it cost |
|---|---|---|
| `SUMMARY OF RECEIPTS` | `SUMMARY OF RECEIPT S` | the window was never found, subtotals counted as detail — $120,579,065.28 against a printed $40,193,021.76 |
| `total number of students receiving services outside the district` | `studen ts`, `ou tside`, `out-  side` | four of twelve years of placement counts missed |
| `STAFF ROSTER` | `Faculty/Staff Roster`, `THMS STAFF ROSTER`, nothing at all | FY2025 read as a district a third smaller |
| `/Rotate 270` means rotate 270° | PDFKit had already applied it, and orientation varies *within* a document | ~700 pages read sideways, invisibly |

The fix is the same every time — match loosely, or locate from the catalogue built by
reading — and **the fix written for one instance was not carried to the next.** `loose()`
was written for the placement counts in the afternoon and re-derived for the receipts an
hour later.

Two things follow. A pattern matched against extracted text is matched against *our
rendering*, so it must tolerate the ways that rendering breaks. And every one of these
produced **plausible** output: $120M is not obviously absurd for a town with a $46M budget,
which is why the reconciliation gate exists rather than eyeballing the figures.

## Verification: reading the page is the only proof most of this can have

These reports are the official record — Town Manager and Finance Committee approved,
carrying MUNIS exports. There is nothing more authoritative to check them against, so the
question is never whether the town's figure is right. It is only ever **whether we captured
it faithfully**, and for a table that prints no total the only instrument that answers that
is the page itself.

`scripts/render_page.swift` renders a page upright; `scripts/verify_against_page.py` puts it
beside the rows extracted from it. Two verification passes over ten pages found nine defects,
**seven of which no arithmetic check could ever have surfaced**:

| defect | why nothing else finds it |
|---|---|
| Pages read a half-turn out — rows AND columns reversed | the output is orderly and mirrored, under correct-looking headings |
| Multi-panel pages read across instead of down | every figure real, every pairing false |
| Count tables (elections, enrolment, vital records) keyed on currency | zero figure rows, no ruler, dataset silently EMPTY |
| Character grid clipped at 190 columns | the labels survive and only the last column of figures goes |
| Rows the ruler could not cut, discarded | a missing row shifts nothing |
| Rows whose label OCR lost, discarded | same |
| A dataset reading another table's pages | rows carry real figures and the wrong labels |

The two that arithmetic *did* catch were caught by the reconciliation column, which reported
FY2020 short by exactly $31,793.00 — the disbursements figure of the one row being dropped.

**A fix upstream of a cache does nothing until the cache is rebuilt.** The flip correction
was verified working on the raw geometry, the extractors were re-run, and the output was
unchanged — because they read the pre-rendered page cache. That looked exactly like the fix
failing.

## What must not happen

- **A partial year summed with a complete one.** `status` travels on every row for this
  reason; the receipts CSV already carries it.
- **A count of names called a staffing level.** Rosters have no FTE and no funding source.
- **A cluster treated as a fact.** The catalogue's cross-year grouping is derived from
  plain-English names, not printed headings. It is a hypothesis about which tables are the
  same table.
- **An extractor keyed on a heading.** See the rule at the top.
