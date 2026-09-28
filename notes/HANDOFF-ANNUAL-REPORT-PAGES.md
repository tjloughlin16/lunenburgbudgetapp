# The annual-report page stream: what to do next

27 September 2026. **Everything left on this stream is CODE. `UNREAD` is 0, and no amount of
model spend moves it.** That is the one sentence to carry away, because the metric spent a
day inviting the opposite purchase.

Where the 474 financial pages stand, from `python3 scripts/map_annual_report_pages.py`:

    162 PROVEN    rows tie to a total the page prints          done
    282 UNPROVEN  rows exist, nothing recorded a check         write the check   (code)
     30 REFUSED   an extractor reached it and wrote nothing    fix the extractor (code)
      0 UNREAD    nobody has looked                            read it           (TOKENS)
      0 reversed  the OCR came out mirrored                    re-OCR            (free)

The four states, why `read` was replaced, and the `PROOF` registry that decides which is
which are in `notes/HANDOFF-INGESTION-TRUST.md` §3h. This document is only the queue.

---

## THE JOBS, RANKED

### 1. The 12 debt-repayment pages — diagnosed, ready to write

    FY2011 p76   FY2012 p76, p77   FY2013 p81, p82   FY2018 p48, p51
    FY2019 p49   FY2020 p43, p44   FY2022 p45, p47

**The recorded refusal reason is WRONG and must not be trusted.** It says *"the page is a
scanned image; there is no text layer to read, and the issue columns are too narrow for
Vision"* — while its own evidence field says *"Vision reads 356 boxes, e.g. `$9,180`"*. Rule
13c: a matcher that found nothing was written down as a fact about the document.

What FY2011 p76 actually holds, read off the boxes:

* the title, `TOWN OF LUNENBURG DEBT REPAYMENT SCHEDULE AS OF JUNE 30`
* a year header at y≈0.925: `2019 2020 2021 2022 2023 2024 2025 [2026 2027] 2028 2029 2030`
  — every year its own box at a ~0.038 pitch, **except one merged box**
* 60 row labels at x<0.20, structured per bond issue: `PRINCIPAL`, `INTEREST`,
  `TOTAL MASS WATER POOL TRUST`
* 285 money boxes on a clean grid, ~0.04 pitch

**Why this is safe to read from OCR at all: the table states an identity about itself.**
`PRINCIPAL + INTEREST = TOTAL <issue>`, for every issue in every year column — roughly 15
issues × 11 columns of arithmetic that a wrong column assignment cannot survive. That is rule
13b's own argument, and `scripts/read_trust_table.py` is the worked example of the same shape.

The merged `2026 2027` box is the FY2017 p149 trap in a tractable form: both years are
PRINTED and READ, the pitch is measurable, and years ascend left to right, so the two column
centres are **predicted rather than invented**. Nothing is named from a position.

The order: read the year header, split merged boxes by the measured pitch, band the rows off
the label column, place figures by nearest column centre, and **publish only the columns
where principal + interest foots to the printed total.** Everything else goes in
`debt-repayment-detail-refused.csv` with its reason.

### 2. The 10 receivables pages — the pages grade the extractor

    FY2017 p43, p44, p45   FY2018 p54   FY2020 p49
    FY2021 p47, p49        FY2022 p51   FY2023 p55, p56

These were read and their rows DELETED for not summing to the totals their own pages print.
The work is fixing `scripts/extract_receivables.py`; the pages are legible and they grade it.
Registered as a gap, so the count falls as the extractor improves.

### 3. Five pages refused for a header or parse reason, each different

| page | why | remedy |
|---|---|---|
| FY2013 p83 | 50 figures carry trailing scanner marks (`$`, `S`, `\|`, a doubled paren) so they match no money pattern and its rows never form | a conservative gate stripping ONLY those marks recovers all 50 and takes the page from 124 figures to 174. Rows must be anchored on the label column at x≈0.131 (51 rows, 0.01135 pitch), **not** by clustering figures. A residual vertical offset still leaves 51 figures unassigned and must be MEASURED |
| FY2019 p198 | mid-table continuation, no header printed on the page | inherit the column map from the page where the table starts — **but see the open decision below** |
| FY2019 p203 | same; also prints its own number as `201`, and a stray `ZRATE` sits in the surname x-position | same |
| FY2023 p51 | only `ACCOUNT NUMBER` and `FUND NAME` survive; the rest of the header band is OCR garbage (`CAN GES`, `5=5=2255225229`). FY2023 prints TWO trust tables with different headers | read the header off the PDF text layer, not the OCR cache |
| FY2017 p149 | 16 town names occupy 8 OCR boxes — one reads `HARVARD HUBBARDSTON LUNENBURG ROYALSTON,` | word-level PDF geometry. Only Lunenburg's column matters to this project |

**FY2013 p83's stated reason was WRONG.** It said the page was rotated. Measured skew came
back exactly `0.00000`, which is that function's silent *"fewer than 8 usable pairs"*
fallback; correcting for a measured −0.0381 made the clustering worse, not better. **The page
is not rotated.** Same defect as the debt pages: a refusal that was a statement about our
instrument.

### 4. Three more singletons

    FY2012 p114   gross wages
    FY2017 p155   appropriations supplement — does not foot to its own subtotals
    FY2019 p44    treasurer's cash — the column does not foot; ours 11,763,248.59 against a
                  printed 15,084,021.00, both recorded in extraction-blocked.csv

### 5. THE 282 UNPROVEN PAGES — the largest bucket, and the least understood

This is the number that appeared when `read` was replaced, and nobody has worked it yet.
`failed_by` in `annual-report-pages.csv` splits it into two genuinely different jobs:

| subject | pages | what `failed_by` says |
|---|---:|---|
| appropriations | 78 | `appropriations` failed on 65, `capital-projects` on 9 |
| payroll | 56 | **nothing recorded on 37**; `appropriations` failed on 19 |
| unknown | 23 | nothing recorded on 18 |
| debt | 20 | nothing recorded on 8, `debt-repayment-detail` failed on 8 |
| special-revenue | 17 | `special-revenue-funds` failed on 11 |
| regional-school | 17 | `appropriations` failed on 12 |
| trust-and-stabilization | 16 | nothing recorded on 8, `trust-funds` on 6 |
| treasurers-cash | 14 | **nothing recorded on all 14** |

**A page with a name in `failed_by` and a page with nothing recorded are not the same work.**
The first has a check that ran and disagreed with the page — that is the 4,870-against-157 in
`report_appropriations`, and it is a real reconciliation problem. The second has no check at
all, and the remedy is to write one; `treasurers-cash` is the clean example, 14 pages with
nothing recorded anywhere.

Do not start here without splitting on that column first.

---

## THE OPEN DECISION, FOR TJ

**FY2019 p198 and p203 — the gross-wages table. Worth reading, or leave them REFUSED?**

`notes/generated/AGENTIC-BACKLOG.md` says this table is deliberately NOT published, and it is
registered in `money-gaps.csv` instead: the town stopped printing the department beside each
name after FY2016, and the two-column layout loses a third to a half of the given names.
Reading those two pages would move the counter and produce rows nobody consumes.

Nothing else waits on this. Both readings are defensible; the gap row already carries the
explanation either way.

---

## BEFORE STARTING ANY OF IT

    python3 scripts/db_freshness.py         # is lunenburg.db still true? milliseconds, offline
    python3 scripts/map_annual_report_pages.py    # the queue, and the four counts

**`map_annual_report_pages.py` refuses to write a count off a stale database**, so if
`db_freshness` is red, fix that first — on 27 September the page count was published off a
four-day-old copy for twelve hours.

**A dataset missing from `PROOF` FAILS the build.** If you add an extractor, add it there
with the column carrying its verdict, or `(None, NOTHING)` if it records none. The build stops
and names it rather than filing its pages as UNPROVEN, which would read as a finding about the
archive.

**A refusal register missing from `REFUSED_FAMILY`** in `build_extraction_gaps.py` fails the
same way, and needs the question a reader cannot answer plus the fix that would close it.

**AND A REFUSED PAGE IS NEVER RERUN.** It returns the same refusal and pays a model for it.

## WHEN FINISHED

    python3 scripts/check_generated.py --rebuild    # dependency-ordered, loops to fixpoint

One run, at the end, not as you go — it starts 8 checks at once and several agents each
running it takes the load average past 11. Verifiers that fail are reported separately as
*needing a person*, because a verifier failing is a defect and not staleness to be built away.

**Nine generators are excluded from `--rebuild` and the reason generalises.** Seven call
`claude -p`; two (`sync_d1.py`, `sync_search_d1.py`) push to a remote with a hard daily write
budget. The rule *drop `--check` and you have the generator* is true of every other entry —
and `sync_d1.py` is where it bit on the first run, pushing unasked minutes after the push had
been deferred to the next day's budget. **A CHECK AND ITS GENERATOR DO NOT ALWAYS SPEND THE
SAME THING.** Dropping a flag is a safe way to find the builder and not a safe way to decide
whether running it is free.

**A `--rebuild` run hung for nineteen minutes on 27 September and had to be killed**, with
five checks alive and no progress: `build_blog.py --check`, `verify_blog.py`,
`build_if_students_leave.py --check`, `build_peer_spending.py --check` and
`build_special_education.py --check`. Killing it lost the output, so which round it was in is
not known.

WHAT IS ESTABLISHED: those five ran over ten minutes and the run did not advance. WHAT IS
NOT: why. The trust handoff's §3d records `build_if_students_leave.py --check` writing to
`lunenburg.db` while another check holds it — a real concurrency defect — and that does NOT
explain `build_blog.py`, which never opens the database. Two explanations fit and nothing
distinguishes them yet.

Every check is now bounded by `TIMEOUT = 600`, so a hung one is reported as TIMED OUT by name
and the run continues. **That bounds the symptom and does not fix the cause**, which is still
open: the remaining question is what those five actually contend over. `--serial` runs clean,
which is the workaround and also a clue.

`money_gaps` changed on 27 September and has NOT reached D1. The next `python3
scripts/sync_d1.py` takes it; it is one small table. Do not run it the same day as a large
push — two runs that day already put ~74,000 rows through a 100,000-write daily budget.
