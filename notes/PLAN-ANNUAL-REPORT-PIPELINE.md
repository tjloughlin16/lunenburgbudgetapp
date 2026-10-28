# Plan: annual reports from the town archive to proven figures, paced by what each step spends

Written 27 October 2026. TJ's ask, in his words:

> *"annual report found in the archive, downloaded (fetched), processed (via AWS process or
> local Mac Vision), and ingested (in DBs, searchable, etc etc). That needs to be HYPER clear in
> the dashboard if all things are fully through that process."*

> *"once we hit a spend limit, it needs to hard stop and process no more, and wait for the
> 'pacing' to capture those ... minutes consume agent rates but annual reports consume aws
> spend ... there's still an agentic rate spend required to finish each FY report ... so its
> some combination for sure"*

Why now: Renee Emkey (Select Board chair) is uploading ALL the town reports to the town
archive -- about 30 more, ~100-135 pages each, back to the 1980s. The last fifteen took 2-3
weeks of hand reading.

## 1. The stages, each checked from a file, never assumed

| # | stage | true when | evidence |
|---|---|---|---|
| 1 | **Found** | the town's archive lists it | a row in `sources/town-annual-reports/index.csv` from the daily crawl, with its upstream address |
| 2 | **Fetched** | we hold the bytes and they are backed up | the file on disk AND its sha256 in `archive-manifest.csv` (the bucket) |
| 3 | **Processed** | every page has been read into words | OCR output covers every page; the engine is named (`textract` or `vision`) |
| 4 | **Ingested** | searchable, its financial pages located, figures loaded | text in the search index; rows in `annual-report-pages.csv`; its tables in `lunenburg.db` |
| 5 | **Proven** | every financial page closes on totals it prints itself | `annual-report-pages.csv` state `proven` or `blocked` -- today's definition of done |

**Stage 5 is separate on purpose.** 1-4 can be automated now. Proving is the 2-3 weeks of hand
work, and nothing automatic does it yet. Folding it into "ingested" would paint the dashboard
green for reports whose numbers nobody has checked.

## 2. What blocks the automatic path today (mapped 27 October)

- **Discovery mostly works**: `fetch_town_docs.py` crawls every ArchiveCenter category daily, via
  `watch_documents.py` from `refresh.py`. But:
  - `watch_documents.FOLDERS` omits `town-annual-reports`, so a new report raises no NEW event and
    that `index.csv` is not protected against a short crawl;
  - the label filter wants `annual town report`; a 1980s upload labelled "Town Report 1985" is
    dropped or misfiled under `town-supplementary` (`town_document_home.py`);
  - `dedupe_key()` turns `FY85` into `fy2085`.
- **Everything after fetch is by hand**, and keyed on `fy-YYYY` in the filename: `report_pages.py`
  crashes without it, `map_annual_report_pages.py` skips the file, `build_annual_reports.py`
  cannot place it. Calendar-year reports ("Town Report 2000") have no `fy-` at all.
- **Year-specific code** a new year would have to be added to by hand: `read_trust_table.LAYOUTS`,
  `extract_tables.TEXT_LAYER_RUNS` / `SUPERSEDED`, `map_annual_report_pages.REPRINTS`,
  `extract_balance_sheet.py`'s document list, the `inventory/FY*.json` files.
- **The dashboard cannot see a new report** until it has an OCR file and a page-map row, and
  `annual_report_progress.py` then says "every year is done" -- a year not in the map does not exist to it.

## 3. Two resources, and the pacer has to know both

| work | spends | governed by today |
|---|---|---|
| meeting minutes, votes, budget state | the Claude plan (5-hour window + week) | `usage_governor.py`, through `process_meeting.py --until-usage` |
| annual report: Textract every page | **AWS dollars** | `textract_spend.py`: run ceiling, $50/month cap, latch -- a CAP, not a PACE |
| annual report: prove the figures | the Claude plan | nothing; it does not exist as automation yet |

**Proposal: one digest queue, many resources.** Every unit of undigested work is an item with a
priority and the resource(s) it spends. A scheduler takes the highest-priority item whose
resources all say yes:

- **Claude plan**: `usage_governor.decide()`, exactly as now.
- **AWS dollars**: a new `textract_spend.allow()` that paces against the month the way the governor
  paces against the week: a straight line from $0 on the 1st to the cap at month end, with a little
  ahead allowed. At the cap: HARD STOP, the latch, nothing more until the 1st or a person.
- **A resource that says no blocks only the items that need it.** An exhausted AWS month stops
  annual-report reading; meetings keep going on the plan, and vice versa.
- An annual report's year is finished only when BOTH resources have done their part: read (AWS),
  then proven (plan).

Whether this is `process_meeting.py --until-usage` grown a second resource, or a new `digest.py`
that runs both, is a build decision; the shared piece is the priority list and the two governors.

## 4. The order of work -- DECIDED 28 October 2026

TJ, 28 October 2026, when 52 reports (1959-2010) arrived in one crawl: *"annual reports
processing from aws can happen at the same time as meetings. but agentic processing is shared.
so realistically, it can be 'both', with agentic overlap spending landing on annual reports
first. I want to get through the reports as soon as we can."*

So it is resource management, not one ordered list:

- **AWS (reading) runs in parallel with everything.** It competes with nothing on the plan.
  Order: **newest year first**, stopping hard at the monthly cap; the rest wait for the 1st.
- **The Claude plan is the one shared resource.** Where both streams want it, **annual reports
  first** (proving), then new meetings, then the meeting backlog.

The default this replaced put new meetings ahead of everything.

## 4a. The 1959-2010 reports: extract what is THERE, not what FY2011 had -- DECIDED 28 October 2026

52 reports, calendar 1959 to 2010, fetched 28 October 2026 (the quarterly `annual-reports` source;
`scripts/read_annual_reports.py` reads them). TJ, the same day:

> *"if these reports are in any way different, meaning they have different data sets or unique
> information, these go back to the 50s. So we need to be flexible and capture information from
> tables and finances that may no longer exist ... processing the data as it's found in there,
> mapping it to the tables we have, and then if they don't map ... we need to create the new
> things to land them in the database to make them searchable."*

So extraction runs from the PAGE outward, never from our dataset list inward:

1. **Inventory first.** Every table on every page is catalogued with its PRINTED heading
   (`annual-report-catalogue.csv`'s grain), before anything is mapped. What the report prints
   is the list of things to land.
2. **Map to an existing dataset only where it is the same quantity** -- same thing counted,
   same stage (rule 1: budget vs actual), same grain. A similar heading is not a match.
3. **What does not map gets a NEW dataset**, named for what the page prints, with the same
   furniture as the others: `document`, `page`, `status` (`checked` / `check failed` /
   `no check`), provenance, loaded into `lunenburg.db` and searchable. A 1960s table with no
   modern counterpart is a finding, not a misfit.
4. **What a modern dataset has and an old report does not print is a GAP**, registered in
   `money-gaps.csv` (rule 7c) -- never filled, never inferred from an adjacent table.

**The pilot is the ten newest, 2001-2010, taken to the finish line the FY reports reached**:
pages proven or blocked, datasets, database, search, the app. Tables (Textract) on every page of
those ten, so the financial-page finder has an answer key; then one report end to end (2010)
to measure what the agentic part costs, quoted before the other nine.

## 5. Build phases

| phase | what | done when (measured) |
|---|---|---|
| **P1 Find & fetch** | `town-annual-reports` into `watch_documents.FOLDERS` and `REFRESH_WRITES`; widen the label rule; one year parser for `FY85`, `FY1985`, `1985`, `Town Report 2000`, recorded with whether it is fiscal or calendar. **SAME BYTES, SECOND ROUTE (TJ, 27 Oct):** when the crawl fetches a file whose sha256 the archive already holds, it is NOT a new document: append the new address to the existing row's `upstream` and process nothing. The 2000 report is the case: landed 27 Oct from a copy Renee Emkey sent TJ directly, before the town has uploaded it | a fixture of real labels parses; a crawl files an older report under `town-annual-reports/`; a fetched file identical to a held one adds an upstream and creates no new row, object or OCR job |
| **P2 Read** | refresh step: Textract EVERY page of a fetched, unread report, through the meter. `textract_pages.py` also writes the Vision-format TSV (`page x y w h conf text`) so every downstream reader works unchanged. Vision only by explicit flag (TJ: *"fallback in case i REALLY need something OCRd but dont want to spend more"*) | the 2000 report read end to end; the monthly pace line holds; the latch stops a run cold in a test |
| **P3 Dashboard** | an "Annual town reports" stream in the style of the OML card: a by-year bar split into the five stages, empty slots for years the town has not uploaded, the AWS month line beside it, and the pending list | every held report appears at its true stage; a report with no OCR shows as `fetched`, not missing |
| **P4 Ingest** | year parsing in `report_pages`, `map_annual_report_pages`, `build_annual_reports`; search index picks up the text; page map built automatically | the 2000 report's financial pages located with no hand step |
| **P5 Pace** | the shared queue with both governors and the agreed order | both resources visible on the dashboard; one exhausted does not stop the other |
| **P6 Prove** | the automatic prove step: Textract cells -> rows -> the page's own identities; refused pages queue for a person. `claude -p` only where judgment is needed. **Designed in section 7 below** | scored on the 511 proven pages (answer key) before it touches a new year |

**Acceptance test for P1-P4: the 2000 report**, kept OUT of the archive at TJ's instruction (test only,
not recorded). It runs through a scratch path; nothing of it reaches `sources/` or the bucket.

## 6. Facts measured so far

- FY2011, 29 scanned proven pages, Textract tables, $0.435: 2,738 of 2,839 proven figures of 100 or
  more returned on their page (96.4%); Vision 87.5% vs Textract 99.7% on the 20 pages both read.
  A proxy, not a proof: `scripts/textract_score.py`, `build/textract/score-fy2011.md`.
- The 2000 report: 134 pages, every one a scan; financial sections at printed pp. 62-87 and
  wages 120-132; births, marriages and deaths at 88-94 (names -- the redaction gate's territory if
  it is ever archived). Vision OCR of all 134 pages: 41,782 words, local, in the scratchpad only.
- Setup and spend limits: `notes/process/TEXTRACT-SETUP.md`.

## 7. P6 in detail: validate, triage, reconcile agentically

TJ, 27 October 2026: *"we need validation on the aws process on our side, to call out
discrepancies, flag them and figure out if there's something we can do to reconcile them --
agentically."*

### The worked example this is built from (2000 report, done by hand the same day)

- **Balance sheet, PDF p67:** 25 of 25 printed totals closed to the cent, five fund columns,
  straight from Textract's cells. Nothing to reconcile.
- **Trust funds, PDF pp86-88:** 21 totals closed. Three kinds of discrepancy turned up, and
  they are the three the design must tell apart:
  1. **The town's own arithmetic.** Colonial dividends: 12 cells sum to $12,274.58, the page
     prints $12,276.93, off $2.35. All 12 cells were read off a 5x render of the page and match
     Textract digit for digit. A page defect -- it belongs in `document-defects.csv`, and the
     figures are kept as printed (rule 13a: never "fix" a published number).
  2. **A grouping error of OURS.** The p86 `TOTAL:` block and the p88 Century block missed by
     thousands. The blocks contain sub-blocks and continue across pages; the quick checker
     summed the wrong rows. Not a misread and not a defect -- a checker bug.
  3. **A misread** -- not seen on these pages, and it is the case everything else must be
     distinguishable from.
- **The trap found on the way:** the page is a landscape table scanned onto a portrait page;
  the first two crops missed the column. Crops must be taken in reading orientation (rotate
  until Textract's own text geometry runs left-to-right), not by guessed coordinates.

### Three layers, cheapest first

**NOTHING WAITS ON A DISCREPANCY.** TJ, 27 October 2026: *"basically after processing, log the
discrepancies from the analysis, and then we can review after the fact."* Processing runs to the
end; validation and reconciliation run after it and LOG what they find. A report with open
discrepancies is processed, with a count of what is open -- it is not stuck. The register is a
review queue TJ works through later, on the dashboard.

**1. VALIDATE -- no model, runs on every page Textract returns.**
- Find what the page asserts about itself: TOTAL / SUBTOTAL / GRAND TOTAL rows; balance-sheet
  identities (assets = liabilities + fund equity); row identities learned from the proven
  pages (begin + in - out = end; principal + interest = total); allocation shares summing to 1.
- Group rows into blocks properly: a block runs from its first data row to its TOTAL, may
  contain sub-blocks with their own totals, and may CONTINUE across a page break (a table on
  page n+1 with no header row is a continuation).
- Every check is recorded: closed, or off by an exact amount. Decimal arithmetic, no tolerance
  unless the page itself shows rounding (rule 13: the identity is the arbiter).

**2. TRIAGE -- no model, classifies each open check by its fingerprint.**
- **Misread suspect:** the difference is one digit's worth (a single-digit change in one cell
  explains it exactly), or a cell in the column has low Textract confidence.
- **Grouping suspect:** the difference equals the sum of a contiguous run of rows, a sub-block
  total, or a block on the adjacent page.
- **Printed-error suspect:** every cell is high-confidence and no single-digit or grouping
  explanation exists.

**3. RECONCILE -- `claude -p` with images, only for what triage could not settle.**
- Inputs: a high-resolution crop of the suspect column and its total, IN READING ORIENTATION;
  the cells as Textract read them; the difference; the triage guess.
- The agent answers in a fixed schema: `misread` (which cell, what it actually says),
  `grouping` (which rows the total covers), `printed_error`, or `cannot_tell`.
- **THE AGENT PROPOSES, THE ARITHMETIC DECIDES.** A misread correction is accepted only if it
  makes the identity close EXACTLY; a grouping answer only if the named rows sum to the total.
  `printed_error` is accepted only when the agent's own digit-by-digit reading matches
  Textract's and still does not close -- two independent readers agreeing, and the page wrong.
  Anything else stays open for a person.
- Every verdict goes into one register (a `discrepancies.csv`: page, check, cells, difference,
  triage, verdict, who decided, the crop's path) -- never into the figures themselves. A
  corrected misread is recorded as a correction beside the Textract value, not over it.
- Printed errors are copied to `document-defects.csv`, the archive's existing register for
  defects in the documents themselves.

### Spend and pacing

Layers 1-2 are free. Layer 3 spends the Claude plan (images, so not the cheapest call): it is
the "agentic rate" part of an annual report in section 3, paced by `usage_governor.py`. Expect
it to be rare -- on the 2000 pages checked, one real discrepancy in 47 totals.

### Done when (measured)

- On the 511 proven pages: every printed total the existing datasets proved also closes here,
  and nothing proven is flagged as a discrepancy (false alarms are counted, not waved off).
- On the 2000 report: the balance sheet closes 25 of 25; the Colonial dividends are recorded
  as a printed error of $2.35 with the crop that shows it; the Century and `TOTAL:` blocks close
  once grouped correctly.
- The dashboard shows, per report: totals found, closed, open, and each verdict class.

## 8. Page integrity: is the scan complete and in order? (every report, before anything else)

TJ, 27 October 2026: *"we can't FULLY trust that these reports are in-order or have all the
pages.... these are hardcopies that may have been accidentally moved around and things lost or
changed."* The older reports are scans of paper copies; a page can be lost, shuffled or
duplicated before it ever reached a scanner.

**The check, no model, runs on the OCR output:**
1. **Folios.** Every page's printed page number -- a bare number in the top or bottom margin
   band (Textract gives each line's position). Expect printed = PDF page + a constant offset;
   report every page off that line, every duplicate folio, every missing number, every page with
   no folio. Numbers mid-page are NOT folios (2000 report: "132" at PDF 102 is a vote count).
2. **Runs that must continue.** Alphabetical lists (wages, staff) and numbered lists (town
   meeting articles, accounts) must carry on from one page to the next; a break at a page
   boundary is a missing or misplaced page even where the folio is unreadable.
3. **The index against the body.** The report's own index says where each section starts;
   check the heading is on that page.
4. **Result per report:** `pages_ok`, or the exact pages missing / out of order / duplicated,
   logged to the same review register as the discrepancies (section 7). A shuffled page is
   REORDERED in our reading (never in the archived scan), and the reordering is recorded.

**What it cannot catch:** a page replaced by one with the same number from another year, or a
figure altered by hand. Those surface only as identities that fail to close -- section 7.

**The 2000 report, checked by hand 27 October:** 130 of 130 numbered pages (printed 2-131) at
printed = PDF - 3, no duplicates, no gaps. PDF 1-4 are unnumbered front matter (cover, a
page, the index, a blank). **Printed page 132 is absent from the file**: the index puts wages
through 132; no page carries folio 132; the school wages list runs unbroken A to `Valois` on the
last page with no later names anywhere. Missing, not shuffled. If the town's own upload has it,
the two files differ and are kept as two documents.
