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
| Annual report pages | 445 of 474 | 29 pages still to prove | one PAGE of a report |

**The annual-report page queue is finished as a reading job.** All 474 pages have been
looked at. 445 produced rows that prove; 29 were read and REFUSED. **None is waiting for a
first reading**, and spending model tokens on them returns the same refusals.

The figure fell from 459 to 445 later the same day, and the archive did not change. Four of
the eight `*-refused.csv` files carry no `state` column, so each was CREDITING the pages it
refused -- recording that an extractor could not read a page marked the page READ. Twelve of
the fourteen were debt pages. A refusal file is now skipped by NAME as well as by column, in
both halves of the join. See section 2b.

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

    445 of 474 pages READ
     29 of 474 pages READ AND REFUSED -- the rows would not prove
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
  those pages; it now reads `N pages still to prove`, the done phrase and the
  remaining phrase being different sentences about different sets.
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

### 3a. THE LEASE — DONE

`scripts/worklease.py`, claimed inside `benchmark_ingest.py`. **The claim is on the PAGE and
not on the batch**, which is the whole lesson: a lock around the batch would not have helped,
because the second run was a second batch holding its own lock over the same pages.

Four behaviours tested, because a lease that cannot be shown to block is not a lease:

  * skips a real read in 0.164s, spending nothing
  * releases when its holder exits, including on an exception
  * a DEAD holder's lease is ignored and taken over
  * an EXPIRED lease is taken over even when its pid is alive, so a recycled pid cannot
    park a page forever

`O_EXCL` makes the check and the claim one operation. A read followed by a write is the
check-then-act race that caused the duplicate.

Still true and worth knowing: `bash scripts/status.sh` reported `0 running` while the
duplicate pass was under way, because it tracks the votes and minutes sweeps and
`benchmark_ingest.py` is not one of its streams. The check that would have caught it had no
power to.

### 3b. THE 29 REFUSED PAGES — engineering time, not model time

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

### 3f. D1 — FIXED, AND IT CONVERGES OVER DAYS

The push was broken in a way that no retry could fix:

    importing 153,414 rows (~306,828 writes with indexes)
    the free tier allows 100,000 a day

`sync_d1.py` replaced the whole database, so the published copy could not be brought up to
date on that day or any later one. CLAUDE.md said "a full replace is ~51,000 rows" until it was corrected that night;
that is stale by 3x.

TJ, 27 September 2026: *"We need to make the d1 sync work. I dont want to leave that sitting
broken. Thats a deployment issue and we can't react in an emergency."* Right, and that is
the real cost -- not the staleness, the loss of a push route.

**`scripts/d1_incremental.py` sends only the tables whose DIGEST differs**, and is now the
default; `--full` forces the old behaviour. Measured: run one sent 100 tables / 39,891 rows,
run two sent 10 more / 39,448 rows, 9 tables / 74,075 rows remain and it exits 0 telling you
to run again. The remote holds a `synced_table` row per table, and `/api/query` now answers
about `build_meta`.

Four things it had to get right, each learned by failing:

  * **A digest, not a row count.** A corrected figure leaves the count identical, which is
    exactly the drift `--check` exists to catch. The digest covers the CREATE too, so a new
    column counts as a change even with no row moved.
  * **Two kinds of change.** Same CREATE and different rows -> `DELETE` then `INSERT`, so
    nothing referencing the table is touched. Different CREATE, or new -> `DROP`, `CREATE`,
    `INSERT`.
  * **`PRAGMA defer_foreign_keys = true`** opens every batch, because the schema has real
    foreign keys and D1 enforces them. It defers CHECKING -- it does NOT make a referenced
    table exist, which is the next one.
  * **A parent must exist before its children's rows.** Sorting purely by size put a small
    child ahead of `document`, which it references, and D1 answered `no such table:
    main.document` at INSERT. A child is now only eligible once every parent is already
    remote or earlier in the same batch, computed from the live schema.

And the consistency check is SKIPPED while tables are deferred: `compare()` counts every
table, and a COUNT over a table the remote does not hold yet errors rather than returning
zero -- which killed an otherwise successful push after it had landed 100 tables. A partial
sync is the designed state while a backlog drains.

**What is left:** run `python3 scripts/sync_d1.py` on each of the next two days to clear the
remaining 9 tables. After that, ordinary changes are a few thousand rows and land in one run.

### 3g. THE DEBT PAGES — diagnosed, ready to write

The 12 debt pages are the biggest single bucket of the 29, and **the recorded refusal reason
is wrong**. It says *"the page is a scanned image; there is no text layer to read, and the
issue columns are too narrow for Vision"* while its own evidence says *"Vision reads 356
boxes, e.g. `$9,180`"*.

What FY2011 p76 actually holds, read off the boxes:

  * the title, `TOWN OF LUNENBURG DEBT REPAYMENT SCHEDULE AS OF JUNE 30`
  * a full year header at y~0.925: `2019 2020 2021 2022 2023 2024 2025 [2026 2027] 2028
    2029 2030` -- every year its own box at a ~0.038 pitch, EXCEPT one merged box
  * 60 row labels at x<0.20, structured per bond issue: `PRINCIPAL`, `INTEREST`,
    `TOTAL MASS WATER POOL TRUST`
  * 285 money boxes on a clean grid, ~0.04 pitch

**The table states an identity about itself: `PRINCIPAL + INTEREST = TOTAL <issue>`**, for
every issue in every year column -- roughly 15 issues x 11 columns of arithmetic that a
wrong column assignment cannot survive. That is what makes this safe to read from OCR at
all, and it is rule 13b's own argument.

The merged `2026 2027` box is the FY2017 p149 trap in a tractable form: both years are
PRINTED and READ, the pitch is measurable, and years ascend left to right, so the two column
centres are predicted rather than invented. Nothing is named from a position.

So: read the year header, split merged boxes by the measured pitch, band the rows off the
label column, place figures by nearest column centre, and publish only the columns where
principal + interest foots to the printed total. `read_trust_table.py` is the worked example
of the same shape.

### 3h. THE METRIC ITSELF IS STILL WRONG, and TJ said so

TJ, 27 September 2026, after the count moved three times in a day: *"i think we need a
different metric then. read and refused as separate? (refused need to be... rerun?!)"*

**No -- a refused page must NEVER be rerun.** Rerunning returns the same refusal and pays
for it. That misunderstanding is the dashboard's fault: `15 left` invites exactly that
purchase, and it is the clearest evidence the metric is wrong rather than merely noisy.

WHY IT KEEPS MOVING. `read` means *any dataset mentions this page*. That is a property of
our FILING, so it changes whenever a file is added -- which happened twice on one day, in
both directions. It is not a property of the archive, and it answers a question nobody asked.

THE REPLACEMENT, four states, each mapping to exactly ONE action, and only one of them
costing model tokens:

| state | means | to fix it | costs |
|---|---|---|---|
| PROVEN | rows tie to a total the page prints | nothing, it is done | -- |
| UNPROVEN | rows exist, nothing proved them | write the check | code |
| REFUSED | an extractor reached it and wrote nothing, with a reason | fix the extractor | code |
| UNREAD | nobody has looked | read it | TOKENS |

Two things to say out loud when it ships:

  * **UNREAD is 0 for this stream.** No amount of spend moves it. Everything left is code,
    and the current card has been inviting a purchase that does not exist.
  * **PROVEN will be LOWER than 445**, because some of those pages are cited by rows that
    never reconciled. Better to publish that than to be corrected a fourth time.

`proven` cannot drift the way `read` does: it depends on whether the page's own printed
total agrees with our rows, which changes only when the arithmetic changes.

Touches `map_annual_report_pages.py` (the state machine) and `build_ingest_status.py` (the
card). Keep `read` as a derived total so nothing currently reading the CSV breaks.

### 3i. TWO THINGS FOUND WHILE DOING THE ABOVE, both worse than they look

**FY2023 GROSS WAGES IS EFFECTIVELY UNREAD AND LOOKS FINE.** Adding refusal recording to
`extract_gross_wages.py` took its recorded refusals from 2 to 24, and the distribution is
the finding: FY2023 has SEVEN silent pages, and the year published **one name totalling
$73**. Seven pages of a payroll listing produced one row and nothing anywhere said so. The
whole year needs re-reading, and until it is, nothing may cite FY2023 wages.

**report_appropriations: 4,870 rows `check failed` against 157 `checked`.** Read off the
table's own `status` column. CLAUDE.md already says nothing may be aggregated without
splitting on `status`; this is the scale of why. A page-level `read` count says nothing about
it, which is part of 3h's argument.

### 3j. DEFERRED, BY DECISION: the cosmetic title leftovers

**TJ, 27 September 2026: "defer title change deploy is fine then." Not an oversight -- a
decision, so it does not need re-deciding.**

Live and verified already: the markdown de-listing, the `X-Robots-Tag: noindex` headers,
`Source documents`, and the renamed page headings. What is NOT live is a handful of labels:
two door tiles on `/the-money` and `/reports` still read `What stopped being funded`.

Why it needs a whole build rather than a file copy: a door title is prerendered into HTML
from `reports.json`, so `dist/` holds it in four files and only a rebuild clears them. The
payloads themselves are already correct in `fy28/public/data/`. It rides along with the next
build anybody runs.

THE RENAME HAD THREE LAYERS AND THAT IS THE LESSON. `LABEL` in `routes.ts` drives the nav; a
separate `TITLE` constant in each page drives its own heading; and a GENERATED payload drives
the door tiles. Each was found only by checking the live site after deploying, never by a
check. Three times in one day the same mistake was made -- change one consumer of a value,
assume the rest -- on the sitemap, then the titles, then the payload.

Worth knowing for any future deploy: **`MAX_UPLOAD_GATEWAY_ERRORS = 5` is hardcoded in
wrangler**, and at 17,105 files five dropped sockets anywhere in a run aborts everything. It
failed three times before succeeding on the fourth, and the reason a retry works is that
uploads are content-addressed -- the successful run reported `Uploaded 803 files (16299
already uploaded)`. If it starts failing consistently, 12,019 of those files are
`dist/docs/minutes`, and they cannot simply be dropped: the bucket's copy of our DERIVED
files is a frozen 5 September snapshot and objects there cannot be overwritten, so serving
them from R2 would quietly publish three-week-old extractions.

## 4. THE RULE THAT CAME OUT OF IT

**A count is a claim about the archive, and it may only be published by something that can
prove its inputs have not moved.** The database is not a source — it is a copy with a date
on it, and on 27 September the date had been wrong since breakfast. Every count on the
dashboard now names what it counts, and the one that reads the database refuses rather than
guesses.
