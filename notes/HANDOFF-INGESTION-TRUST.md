# Handoff: making the ingestion numbers trustworthy

27 September 2026. TJ: *"we need ingestion to be bullet proof. please. please. numbers need
to mean numbers."*

This is what was done that day, what it fixed, and what is still open. The companion
document is `notes/findings/COUNT-5-TO-15.md`, which is the worked case that prompted all
of it. `notes/HANDOFF-INGEST-COST.md` covers what ingest COSTS and where it must run; this
one is about whether its counts can be believed.

---

## 0. WHERE THE NUMBERS STAND

From `bash scripts/status.sh --once`, and every figure carries what it counts:

| stream | done | remaining | one unit is |
|---|---|---|---|
| Captions for recordings | 2,669 of 2,669 | complete | a recording with captions held |
| OCR of scanned minutes | 1,687 of 1,687 | complete | a scanned set of minutes read |
| Votes from the town's minutes | 1,607 of 4,487 | 2,880 sets of minutes still to read | one set of minutes |
| Our minutes of recordings | 549 of 2,433 | 1,884 recordings still to write up | one recording |
| Reconciling annual-report tables | 567 of 13,789 | 13,222 rows still to reconcile | one row that must tie to a printed total |
| Annual report pages | 459 of 474 | 15 pages still to prove | one PAGE of a report |

**The annual-report page queue is finished as a reading job.** All 474 pages have been
looked at. 459 produced rows that prove; 15 were read and REFUSED. **None is waiting for a
first reading**, and spending model tokens on them returns the same refusals.

## 1. THE FOUR FAILURES OF THAT DAY, AND WHAT EACH ONE COST

Worth keeping because each defence below exists for one of them.

| failure | cost |
|---|---|
| Two processes read the same 16 pages at once | ~$4 of duplicate model spend |
| The 5-hour rolling window was blown, not the weekly cap | 4 pages refused with 429; the wrong limit had been quoted |
| The page count was published off a 4-day-old database | a wrong number on the dashboard for 12 hours |
| `unread` meant two different jobs | ten pages described as unstarted work that was actually a broken extractor |

**None of the four was caught by a check.** Every one was caught by a person looking.

## 2. WHAT IS NOW IN PLACE

### 2a. The database records what it was built from — and a count refuses if it has moved

`build_db.py` hashes every CSV it reads into a `build_inputs` table (116 files), with the
build time in `build_meta`. Hooked at `rows()`, the single door, plus the two direct
readers, so nothing slips past.

    python3 scripts/db_freshness.py
    # ok: lunenburg.db still matches all 116 csv file(s) it was built from

`scripts/db_freshness.py` is the ONE place that answers *is this database still true?*
Offline, milliseconds. `map_annual_report_pages.py` calls `require_fresh()` and **refuses
to write a count** rather than publish one taken from a stale copy.

**It compares content hashes, not timestamps.** An mtime moves every time any generator
rewrites a file byte-for-byte, which is every run of everything here, so a time-based check
would cry stale hourly and be ignored inside a day. A check nobody believes is worse than
no check.

**Proven able to fail.** Altering one byte of `receivables.csv` makes both the checker and
the mapper exit 1 and name the file and the remedy; restoring it makes them pass. This
repository has shipped two checks that had no power to fail, so a new one does not count
until it has been made to.

The tables are created with the SCHEMA, not at the end of the build: `table-semantics.csv`
publishes a worked query for every table and `build_db.py` executes all of them mid-build,
so a table created last fails its own example.

### 2b. A third state, because `unread` was carrying two facts

A page nobody has opened needs somebody to read it. A page an extractor READ and then
REFUSED needs the extractor fixed — the page is legible and the reader exists. Those are
different jobs for different people, and the queue could not say which.

    459 of 474 pages READ
     15 of 474 pages READ AND REFUSED -- the rows would not prove
      0 of 474 pages NOT YET READ

`map_annual_report_pages.py` marks a page `refused` when a `*-refused.csv` cites it, or when
an `annual-report-reads/*.json` returned no rows. `refused` outranks `unread` and never
outranks `read`.

### 2c. Refusals are written down, not printed

`extract_receivables.py` refused 39 pages and said so on stdout, where it was read once and
lost — which is why ten of them looked like pages nobody had opened. It now writes
`sources/data/receivables-refused.csv`: the fiscal year, the page, and the reason in its own
words. Seven other extractors already followed this convention.

The `state` column is what keeps it honest: the mapper treats any file carrying `state` as a
catalogue rather than a reading, so recording a refusal cannot accidentally credit the page.
`--check` covers the refusals file as well as the rows, because a refusal that quietly
stopped being recorded would put its page back to looking unopened.

### 2d. Every count carries its unit, and nothing is summed across units

Rule 7b applied to the dashboard. `459 done` did not say done of what.

- Each stream declares a triple: the singular, the plural, and **a separate phrase for the
  remainder**. `15 pages with proven rows left` said the opposite of the truth about those
  fifteen pages; it now reads `15 pages still to prove`.
- The backlog headline said **`18,001 still to process`**, which added 13,222 ROWS to 2,880
  SETS OF MINUTES to 1,884 RECORDINGS to 15 PAGES. Nothing in the world is 18,001 of
  anything. It now names the streams instead: *4 of 6 streams have work outstanding; the
  largest is 13,222 rows still to reconcile.*
- The per-stream breakdown labels each group with which KIND of work it is, so
  "let's work on X" picks a real job: `receivables — read & REFUSED, fix the extractor: 10`.

### 2e. Automatic spend is off

At TJ's instruction, `sweep-supervisor` (every 30 min), `sweep-away` (02:00 Sun+Mon,
uncapped) and `sweep` (02:00 Thu) are booted out, `launchctl disable`d, and their plists
renamed `.plist.disabled` — **disabled, not deleted**; `mv` back and `launchctl enable`
restores them. `refresh` (07:00 daily) and `status` (local, free) remain.

The refresh still spends about **$8.40 a day, ~1.7% of the week**: 3 minutes, 40 votes, 3
budget-state readings. Captions and OCR are free.

## 3. WHAT IS STILL OPEN

### 3a. NO LEASE ON THE PAGE QUEUE — the one that costs money

Two processes read the same 16 pages on 27 September because the work list is DERIVED from
`annual-report-pages.csv` and nothing claims a page while it is being read. A page in flight
is byte-identical to a page nobody has touched.

`scripts/ingest.py` already solved this for documents: `sources/data/ingest-pending.csv`
registers one as IN FLIGHT so the next run retries rather than duplicates. The page reader
has no equivalent. **This is the only one of the four failures that costs dollars rather
than credibility, and it is not fixed.**

Note also that `bash scripts/status.sh` reported `0 running` while a duplicate pass was
under way — it tracks the votes and minutes sweeps, and `benchmark_ingest.py` is not one of
its streams. So the check that would have caught it had no power to.

### 3b. THE 15 REFUSED PAGES — engineering time, not model time

**Ten receivables pages** were read and their rows deleted for not summing to the totals
their own pages print. The work is fixing `extract_receivables.py`, and the pages grade it:

    FY2017 p43, p44, p45   FY2021 p47, p49   FY2023 p55, p56
    FY2018 p54             FY2022 p51
    FY2020 p49

**Five pages refused for a header or parse reason**, each different:

| page | why | remedy |
|---|---|---|
| FY2013 p83 | 50 figures carry trailing scanner marks (`$`, `S`, `|`, a doubled paren) so they match no money pattern and its rows never form | a conservative gate that strips ONLY those marks recovers all 50 and takes the page from 124 figures to 174. Rows must be anchored on the label column at x≈0.131 (51 rows, 0.01135 pitch), not by clustering figures. A residual vertical offset still leaves 51 figures unassigned and must be MEASURED |
| FY2019 p198 | mid-table continuation, no header printed on the page | inherit the column map from the page where the table starts |
| FY2019 p203 | same; also prints its own number as `201`, and a stray `ZRATE` sits in the surname x-position | same |
| FY2023 p51 | only `ACCOUNT NUMBER` and `FUND NAME` survive; the rest of the header band is OCR garbage (`CAN GES`, `5=5=2255225229`). FY2023 prints TWO trust tables with different headers | read the header off the PDF text layer, not the OCR cache |
| FY2017 p149 | 16 town names occupy 8 OCR boxes — one reads `HARVARD HUBBARDSTON LUNENBURG ROYALSTON,` | word-level PDF geometry. Only Lunenburg's column matters to this project |

**FY2013 p83's stated reason was WRONG.** It said the page was rotated. Measured skew came
back exactly `0.00000`, which is that function's silent "fewer than 8 usable pairs"
fallback; correcting for a measured −0.0381 made the clustering worse, not better. The page
is not rotated. This is rule 13c: a pattern that does not match is not an absence, and the
refusal was a statement about our instrument.

**Decision still outstanding:** FY2019 p198/p203 are the gross-wages table, which
`AGENTIC-BACKLOG.md` says is deliberately NOT published and registered in `money-gaps.csv`
instead — the town stopped printing the department beside each name after FY2016 and the
two-column layout loses a third to a half of the given names. Reading those two pages would
move the counter and produce rows nobody consumes. TJ has not said whether that is worth
doing.

### 3c. `money_gaps` may owe a row

Ten receivables pages cannot be published because their rows will not prove. Under rule 7c
that is a registered gap, not merely a queue entry. Not yet added.

### 3d. Two verifier problems that are not data problems

- **`build_if_students_leave.py --check` fails inside `check_generated.py` and passes when
  run alone**, twice each. `check_generated` runs 8 checks in parallel and this one WRITES
  to `lunenburg.db` while another holds it. A concurrency defect in the verifier.
- **`write_recording_minutes.py --check` is red** on five pre-existing files needing
  `--retag`, which calls `claude` — about $0.25. Predates this work.

### 3e. Rebuild ORDER is undocumented and was learned by failing

`check_generated.py` went 7 stale → 12 → 7 → 4 across passes because rebuilding one
generator changed inputs for another. The dependencies that bit:

    build_db            before  build_finance, build_money_flow, build_town_flow
    build_feeds/notices/meeting_feed   before  build_boards
    map_annual_report_pages            before  build_ingest_plan

Nothing encodes this. It is four rounds of guessing every time, and it is why a "quick
rebuild" took an hour.

## 4. THE RULE THAT CAME OUT OF IT

**A count is a claim about the archive, and it may only be published by something that can
prove its inputs have not moved.** The database is not a source — it is a copy with a date
on it, and on 27 September the date had been wrong since breakfast. Every count on the
dashboard now names what it counts, and the one that reads the database refuses rather than
guesses.
