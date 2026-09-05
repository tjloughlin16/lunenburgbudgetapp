# The plan

**What this is.** The arc the work is on, what is done, what is next, and what each thing is
blocked by. `CLAUDE.md` is the rules; `notes/HANDOFF.md` is the standing state;
`notes/HANDOFF-2026-09-03.md` is what happened on one day. This is the shape of the whole
thing, and it is updated as work lands.

**Nothing in this file is a source.** It is a claim about the repo. Check anything
load-bearing against the repo itself.

Status vocabulary: **done** · **doing** · **next** · **blocked** · **open** · **parked**

Last updated 4 September 2026, overnight session.

---

## The goal

**A resident of Lunenburg can see what the FY28 budget gap is, what would close it, and what
each option costs somebody — and can check every figure against a document they can
download themselves.**

Rule 8 is the boundary. This explains how to fix the problem. It is not an audit, and a
discrepancy reaches the app only when it changes an assumption.

Three things have to be true for that to work, and they are the reason the tracks below are
in the order they are:

1. **We know what we hold.** A gap in the archive and a gap in our reading of it are
   different facts, and they were reported as one.
2. **The figures are what the documents say.** Not what a reader of our rendering would
   assume they say.
3. **Where a number cannot be established, the app says so and names the document that
   would settle it.**

---

## Where it actually stands

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org` — tag **`v9.3`** |
| **`main`** | at `v9.3` |
| **Branch `read-the-archive`** | `2f7a5ca` — all of Track 1. Not merged, not deployed |
| **Deploy** | Node 22 via nvm, `npm run build:site`, then `npm run check:agents`. Tag at deploy time. **Nothing deploys without being asked** |
| **Checks** | 19/19 database reconciliations tie; every verifier and builder exits 0 |
| **Archive read** | 31 of 85 documents; 26 more held with 20+ rows, each with a recorded reason |

---

## Track 1 — The archive must tell the truth about itself

*Everything downstream rests on this. A request that asks for a document already on disk
spends goodwill the next request needs, and an analysis built on a coverage matrix that
measures the wrong thing is built on nothing.*

### 1.1 Coverage must measure the archive, not the loader — **done**

The completeness matrix asked one question — *are there figures?* — and answered three:
on disk, in the `document` table, loaded into a fact table. A document held and never
parsed was indistinguishable from one the town never published.

- `extract_line_history.py` writes `sources/data/line-history-coverage.csv`: one row per
  document, read or not, with the reason quoted from that document's own header line and
  its line number. Printed on every run — the `search_minutes.py` discipline, because a
  reader that finds nothing prints nothing and nothing reads as absence.
- `export_ledger.py` gives a cell a fourth state, **`unread`**, and carries the held-but-
  unread documents into it. `DataRoom.tsx` renders it and keeps `unread` rows out of the
  "Ask &lt;publisher&gt;" grouping — that grouping is the mechanism that would have put ten
  held documents into a records request.
- Year attribution is capped at page-top headers naming ≤7 fiscal years. Without the cap
  the matrix claimed a line-level FY2010 budget off one chart axis: the same over-claim as
  calling a year absent, pointed the other way.

### 1.2 Read the documents we hold — **done** (31 of 85 read; 26 held and unread, each with a reason)

Every document now states which shape it is and why it did or did not read. That turned
the list from a complaint into a work queue, and then most of the queue got worked.

| shape | status |
|---|---|
| Kinds on one line (the original reader) | **done** — 24 documents |
| **Header wrapped** over several lines | **done** — the March 2026 FY27 budget documents. The site had been publishing February's figures from a document March superseded |
| **Single column** | **done** — the FY25 final approved budget, the document the School Committee voted, 341 rows, and the FY19 approved budget, 270 |
| **Kinds welded together** | **done** — `Recommendedincrease` in the PDF text layer left `\bRecommended\b` no word boundary, so both FY19 superintendent's budgets, 308 rows, read as nothing |
| **Kinds not in the vocabulary** | **done, in part** — where a document names its leading columns and not the rest, the named ones are read and the rest are left unread. The Town Manager's sheets give up their FY25 column that way, 325 rows and 326 |
| **Column-major text layer** | **open, and named** — 2 documents where the PDF emitted labels and figures in separate runs, so no line holds both. Needs re-extraction with coordinates, a different instrument |
| **Spreadsheet-shaped** (`===SHEET`) | **open** — needs its own reader; also the only form carrying the account code |
| Slide decks and notices | **correctly refused** — a median figure of 9, or no printed total to tie to |

**What made each read safe.** Two tests, and both refused a document that looked entirely
plausible: a newly-read document must agree line by line with any document already stating
the same column, and a single-column extract must tie to a total the document prints for
itself. The Town Manager's 12 March 2025 sheet agrees on **319 of 319** lines with the
approved budget the district published the same day; the 16 March FY27 projection agrees
on **420 of 420** with the 24 February one; the FY19 superintendent's budgets agree on
**1,072 of 1,076** prior-year actuals with two other FY19 documents, the four exceptions
being one line whose printed name appears twice in the source.

### 1.3 A scenario is not a disagreement — **done**

`budget_figure` carries `variant`: the document's own name for a column, `''` for the
documents that print one per stage. The FY27 budget prints four FY27 columns — Restoration,
Core Budget, Level Service, Balanced — and they are four proposals, not four opinions about
one figure. `v_line_budget_vs_actual` filters `variant = ''`; `v_budget_scenario` is the
other side. Documented in `notes/SCHEMA.md`. 1,000 scenario rows held where none were.

Which scenario became the budget is a fact about a vote. It is not in any of these
documents and nothing infers it.

### 1.4 Defects the reconciliations found — **done**

Every one of these was found by a check, not by reading. Both checks now stand:
*a newly-read document must agree line by line with any document already stating the same
column*, and *a single-column extract must tie to a total the document prints for itself*.

| defect | how far it went |
|---|---|
| A parenthetical in the line's name split the row | `P.S. Teachers/Regular (1-2)` — FY2023 and FY2024 published as **1, 2, 3 and 5** for two of the largest salary lines, for six years |
| The sign was dropped | `Circuit Breaker …-452,580` entered positive; the FY25 expense lines came out $905,169 over the document's own total |
| A percentage read as a dollar | `Kindergarten Paraprofessionals 0 -100.00%` read as an FY26 budget of 100 |
| A sentence read as a column header | budget lines called `making class sizes approximately` and `not be able to oversee sports in all three seasons`, two published as API endpoints |
| An enrolment table read as a budget table | `Lunenburg High School:`, `THES. K`, `grade`, `denominators`, with values of 12, 8 and 5 |
| The tiebreak was the filename | Python's sort is stable, so two documents about the same year tie-broke alphabetically — **135 published figures decided by what a file was called** |
| Retired API endpoints were never removed | 29 line endpoints still serving figures the database no longer held |

Consequence worth keeping: **FY23 coverage was never thin.** `budget-vs-actual.md` had
marked FY23 as the weak year throughout at 82% against 93–97% elsewhere. The missing $2.5M
was two teacher lines reading as single digits.

### 1.5 The negative figures — **done** (17 down to 4, and three of the four are real)

A years line ending `Increase/` or `Increase/Decrease` announces one more column than it
has years, and on a row where a figure was printed blank that change column slid forward
into a money column: `E.S. Library Books 4,000 3,500 -500` carries three numbers for four
columns, and FY18 was published as −500 where the real reading is 4,000 falling to 3,500.
Thirteen FY2018 figures came out negative that way.

The layout now carries a `None` for that column, so the row-length check demands the full
width and a short row is skipped rather than misread. Three of the four that remain are
genuine offsets the district prints as credits; the fourth is the same problem in a
document that writes its negatives in brackets. All four are printed by name on every run.
A budget line is not negative, and these are findable precisely because they are absurd.

### 1.5a Five more defects the new reads exposed — **done**

| defect | what it did |
|---|---|
| `Actuals to date` read as an actual | The 16 March 2026 projection carries a year-to-date FY26 column. Reading it as an actual made the whole-budget sweep report FY26 spending **42% under budget** with three and a half months of the year still to run — rule 1's exact shape |
| `Page 1 of 10` read as a budget line | A footer in 22 documents. Ten of them put $55 into the FY19 approved budget's extract |
| A four-line year read as a measurement | FY2016 and FY2017 resolve four usable lines each out of about 350. A stated floor of twenty now excludes them, by name, with the count |
| A sentence read as a column header | Both are "two or more FY tokens on a line". Every real header here carries at most two non-year tokens; every false one carries four to a hundred and twenty-one |
| An enrolment table read as a budget table | The same shape, different numbers. Median figure 9 against 1,750 for the smallest real budget document |

### 1.6 Commit and deploy Track 1 — **committed, not deployed**

Committed on branch **`read-the-archive`** as `2f7a5ca`, 495 files. The reader rewrite, the
`variant` column, the corrected analysis, the DataRoom state and the generated data-model
grids.

**Not deployed, and not merged.** Rule 10: nothing deploys without being asked, every
single time. Live is still `v9.3`.

---

## Track 2 — Ask for what is genuinely missing

*Blocked on 1.2 finishing, because the ask has to be derived from what is actually loaded.*

### 2.1 To the Town Accountant — **blocked** (draft complete)

`notes/sent-to-the-town-2026-09/REQUEST-EMAIL-DRAFT.md` — 5 report configurations, 23 runs,
FY2023–26, with `REQUEST-CHECKLIST.csv` carrying a `why_one_run` column. Accompanied by
`CONNECTING-THE-BUDGET.pdf`.

What it rests on, so it can be challenged rather than inherited:

- **Fund is not a row multiplier; year and period are.** The FY26 sewer report covers three
  funds at account level in one document. No document we hold spans two fiscal years or two
  periods.
- **The 61-fund special revenue file is a different report** — fund-level columns, no
  accounts — and is not evidence about `glytdbud`.
- **The quarterlies were cut deliberately.** They only show *when* in a year a variance
  appeared; Account Details gives that at day resolution, and leaving the quarterlies in
  offered an easy alternative to the hardest and most valuable item.
- **Account Details grain is unknown.** The June files were one account each. Thirteen named
  accounts are listed as the place to start if it cannot span accounts.

### 2.2 To the Superintendent — **blocked** (draft complete, needs re-deriving)

`REQUEST-EMAIL-SUPERINTENDENT-DRAFT.md`. Leads with the DESE End of Year Financial Report,
not with budget documents, because the EOYR reports spending **by fund** — the one thing
that separates "a grant paid for this" from "the town paid for this". Asks for placement
**counts**, never children, with suppression offered for small categories.

The budget-documents section was cut on 3 September: we hold all eight. **The FY25 approved
budget is now loaded too, so it must stay out.** The rest of the draft needs checking the
same way before it is sent.

### 2.3 Stamp `MANIFEST.json` when anything is sent — **open**

It records `REVIEW-DISCREPANCIES.pdf` and not the new PDF. A sent PDF is a fixed object held
by somebody else while ours can move without anybody touching a sentence, because both are
generated. `scripts/check_sent_documents.py` is the guard.

---

## Track 3 — The four standing questions

*Blocked on Track 2. These are not analysis problems; they are documents nobody publishes.*

| question | what would settle it | status |
|---|---|---|
| **How grants and state funding map onto budget lines** | DESE End of Year Financial Report, which separates spending by fund | **blocked** — load-bearing: the in-district special education escalator rests on a paraprofessional line and cannot be told apart from grant money unwinding |
| **Out-of-district placement counts by year** | A count by setting and year, from the district | **blocked** — dollars cannot distinguish fewer children from a more honest estimate |
| **FY26 year-end figures** | `glytdbud` at period 13, plus purchase orders closed after the close | **blocked** — everything we hold for FY26 stops at 31 March |
| **Whether budgeted positions were filled** | A headcount nobody publishes | **open** — a budget line is an intention |

Also standing: **Chapter 70 cannot be traced to spending.** 0 of 222 revenue accounts carry
a function code; state aid shares no org code with any expense account; there is no Chapter
70 fund, unlike every grant. But the general-fund attribution comes from a report *header*,
not from the account — the PDF drops the account string. Asked as a question in the Town
email, not asserted.

---

## Track 4 — What the site says

### 4.1 DataRoom: the `unread` state — **done**

### 4.2 DataRoom: Account Details and transfer rows, and a spreadsheet-vs-PDF flag — **next**

A PDF and a spreadsheet currently count the same, and only the spreadsheet carries the
account code. That distinction is the whole finding of `connecting-the-budget.md` and the
matrix does not show it.

### 4.3 Root-extension soft-404 — **open**

`/openapi.json` returns 200 with the home page. A soft 404 is worse than a hard one for an
agent: it looks like a document.

### 4.4 `notes/data-model/*.html` — **done for the grids**

`match-matrix.html` and `after-request.html` both carried the coverage matrix as
hand-written HTML, stating it as it stood on 3 September — so by the next morning they
said the archive lacked years it holds, which is the error the whole coverage rewrite was
about, sitting one directory from the fix.

`scripts/build_data_model_grids.py` now generates those grids from `ledger.json`, with a
`--check` that fails if either goes stale. The prose is left alone, and so is
`after-request.html`'s projection of what the two requests would fill — that is an
argument, not a derived thing. A first version rewrote it too and quietly replaced twelve
of its cells with today's state, which is a stale grid arriving from the other direction.

Still open: the other four pages are hand-built, and `lineage-graph.html` and
`schema.mmd` are generated but from scripts nobody runs on a schedule.

---

## Track 5 — Machinery

*The checks are the project. Each of these exists because something shipped wrong.*

| item | status |
|---|---|
| Every figure in a finished analysis recomputed by script | **done** for 5 of 13 analyses |
| The other 8 analyses have no verifier | **open** — `/reports` says so on each row rather than letting them look checked |
| `build_source_index.py` was exiting 1 and therefore never writing | **done** — the published index had been stale since v9.3; three v9.3 files were uncatalogued |
| Catalogue counts derived, not typed | **done** for `line-history.csv`; the rest of the catalogue is still typed prose |
| Retired API endpoints removed on rebuild | **done** |
| Persona review before publishing an analysis | **open** — `notes/PERSONAS.md`, six readers, one test each; three of six are about what a document omits |
| `v9` tag numbering not collapsed | **parked** — a deleted tag is a deleted answer to "which build is that" |

---

## Track 6 — The town's second document store, and fifteen years of annual reports

*Opened 4 September. Independent of Tracks 2 and 3: this is a store we already have, not a
request. `notes/findings/TOWN-ARCHIVE.md` carries the full account.*

| item | status |
|---|---|
| `/ArchiveCenter/` discovered — a second CivicPlus store no URL pattern in the fetcher matched | **done** |
| `discover_archive()` reads its javascript-rendered index by AMID/ADID | **done** — 12 categories, 124 items |
| Seeds added: `/838/Annual-Town-Reports`, `/287/Town-Manager-Reports` | **done** |
| `WANTED` pattern `fy\d\d` did not match `FY 2025`, rejecting all 16 annual reports | **done** — fixed |
| Fetcher prints its denominator: links seen, kept, rejected, and a sample of rejects | **done** — kept went 90 → 206 |
| Cross-store duplicates reconciled, both addresses kept in `upstream` | **done** — 18 matched |
| **All 16 annual town reports downloaded** | **done** — FY2011–FY2025 |
| **`scripts/pdf_tables.py` — the reader** | **done** — see below |
| `ocr_pdf.swift --boxes` emits position and confidence per line | **done** — default path unchanged |
| **Survey, text-layer pass** | **done** — `sources/data/annual-report-survey.csv`, per page. 1,588 of 2,751 pages readable; 440 carry figures; 1,163 have no text layer |
| **Survey, OCR pass** | **doing** — all 16 reports at scale 6 with rotation honoured |
| `appropriations`, `debt` and `payroll` found in **zero** years by text layer | **expected** — they are on the scanned pages; FY2011's OCR already shows payroll on pp. 60–64 |
| Receipts by source × year | **doing** — 4 years written (FY2014, 15, 17, 22), 401 source-years, every one tying to the report's own GRAND TOTAL on both checks; 11 years await the OCR pass |
| FY2011's receipts page is clipped in the town's own scan — no GRAND TOTAL, a third of the detail absent | **known limit** — skipped and reported, not published half-checked |
| Special revenue funds × year — turns `fund_activity` from a snapshot into a history | **open** |
| Appropriations by department × year | **open** |
| **Staff rosters → an org chart per year, per school, standardised so years compare** | **next, after parsing** — 25 pages, 10 years so far; harness built (`dump_roster_pages.py`, `build_staff_rosters.py`) |
| Names kept — the town publishes them annually and they make the aggregate checkable | **decided** — a name persisting across years separates a renamed post from a turned-over one |
| Rosters print **no total**, so reconciliation is unavailable | **handled** — the check is line accounting: every non-blank line claimed as entry or heading, leftovers counted and printed |
| At least five different name/role encodings across years and schools | **why it is agent-read per page** — `Name - Role`, `Role Name`, `Name, First – Role`, a two-column table, and grade codes standing in for roles |
| Position taxonomy: unrecognised titles stored blank, never bucketed as `Other` | **built** — an `Other` bucket makes the aggregate look complete while hiding that the taxonomy is wrong |
| `CLAUDE.md` says "for people it is a headcount nobody publishes" — the town has published one for a decade | **open** — correct the sentence, do not quietly drop it. Note the caveat survives: a roster has no FTE and no funding source, so it bounds the question rather than settling it |
| 35–55MB each against a 25MiB publishing limit | **open** — needs `ELSEWHERE` entries |

### What the reader established, and why it is not a detail

Three things were found by building it, and each changes what can be believed:

1. **The reports are three kinds of document.** Six are page scans with no font resources
   at all; ten have a text layer. pypdf returning nothing from FY2012 is correct, not
   broken.
2. **There is no correct extraction mode.** On one FY2025 page, `layout` is the only mode
   that sees a blank cell — plain mode shifts every figure a column left. Four pages
   earlier, `layout` recovers **zero** of the 61 money tokens plain mode reads. The mode is
   chosen per page by measurement and recorded, which is rule 13 made mechanical.
3. **Reconciliation is not sufficient.** OCR read `$22,399,495.70` off the FY2016 addendum
   and did not read `REAL ESTATE TAXES` beside it — the largest revenue line in the town,
   as a number with no name — and the figures still summed to the report's own printed
   GRAND TOTAL. A table can tie perfectly and have lost what half its rows are about. So
   there is a second check: every figure must have a label.

And the reason that happened is worth carrying to any future OCR work here: **raster scale
is a correctness parameter and it fails silently at confidence 1.000.** At scale 3.0 and
4.0 those labels are missing; at 6.0 they are read. Structure settles by 6.0; individual
characters never settle at all. Two passes, differenced.

---

## The order, and why it cannot move

1. **Track 1 before Track 2.** A request derived from a coverage matrix that measures the
   loader asks for what is already on the shelf.
2. **Track 2 before Track 3.** The four standing questions are answered by documents, not
   by analysis. Nothing in the archive settles them.
3. **Track 4 follows both.** The site reports what the database knows; changing the site
   before the database is honest publishes the same error in a nicer font.
4. **Track 5 runs alongside everything.** Every defect in 1.4, 1.5 and 1.5a was found by a
   check — a reconciliation against another document, or against a total the source prints
   for itself. Not one was found by reading the code or the output.
