# Handoff: making the ingestion numbers trustworthy

27 September 2026. TJ: *"we need ingestion to be bullet proof. please. please. numbers need
to mean numbers."*

This is what was done that day, what it fixed, and what is still open. The companion
document is `notes/findings/COUNT-5-TO-15.md`, which is the worked case that prompted all
of it. `notes/HANDOFF-INGEST-COST.md` covers what ingest COSTS and where it must run; this
one is about whether its counts can be believed.

**If you are here to DO the remaining work rather than to understand the counts, go to
`notes/HANDOFF-ANNUAL-REPORT-PAGES.md`.** It is the queue, ranked, with the page numbers, the
diagnosis for each job and the one decision still outstanding. Everything left on that stream
is code; `UNREAD` is 0.

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
| Annual report pages | 162 PROVEN of 474 | 312 pages unfinished | one PAGE of a report |

**The annual-report page queue is finished as a reading job, and the metric now says so.**
All 474 pages have been looked at. **UNREAD is 0**, and no amount of model spend moves this
stream; everything unfinished is code. See section 3h, which is now DONE:

    162 PROVEN    rows tie to a total the page prints          done
    282 UNPROVEN  rows exist, nothing recorded a check         write the check   (code)
     30 REFUSED   an extractor reached it and wrote nothing    fix the extractor (code)
      0 UNREAD    nobody has looked                            read it           (TOKENS)
      0 reversed  the OCR came out mirrored                    re-OCR            (free)

`read` is KEPT as a derived column -- proven + unproven, 444 -- so nothing that already
reads the CSV breaks, and the dashboard's headline is now **312 of 474 pages unfinished**
with those five terms itemised inside the panel rather than a `done` that had to pick one
meaning of done.

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

### 2b. A third state, because `unread` was carrying two facts (now FOUR -- see 3h)

A page nobody has opened needs somebody to read it. A page an extractor READ and then
REFUSED needs the extractor fixed — the page is legible and the reader exists. Those are
different jobs for different people, and the queue could not say which.

    445 of 474 pages READ
     29 of 474 pages READ AND REFUSED -- the rows would not prove
      0 of 474 pages NOT YET READ

`map_annual_report_pages.py` marks a page `refused` when a `*-refused.csv` cites it, or when
an `annual-report-reads/*.json` returned no rows. `refused` outranks `unread` and never
outranks `read`.

**That was the right direction and one state short.** `read` still meant *any dataset cites
this page*, which lumps a page one row was taken from together with a page whose whole table
foots to its own printed total. Section 3h replaced it with four states and is DONE; the
counts above are the last figures the three-state version produced.

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

### 3c. `money_gaps` OWED SIX ROWS -- DONE, AND GENERATED

Ten receivables pages cannot be published because their rows will not prove. Under rule 7c
that is a registered gap, not merely a queue entry.

`build_extraction_gaps.py` now emits one `extraction` row **per refusing extractor**, read
off the page map's new `refused_by` column, because the remedy is per extractor and a gap
with no named remedy is a grievance:

| register | pages | years |
|---|---:|---|
| `debt-repayment-detail-refused` | 12 | FY2011, FY2012, FY2013, FY2018, FY2019, FY2020, FY2022 |
| `receivables-refused` | 11 | FY2013, FY2017, FY2018, FY2020, FY2021, FY2022, FY2023 |
| `gross-wages-refused` | 3 | FY2012, FY2019 |
| `read-and-refused` (a model read that returned no rows) | 3 | FY2013, FY2017, FY2019, FY2023 |
| `appropriations-supplement-refused` | 1 | FY2017 |
| `extraction-blocked` (treasurer's cash) | 1 | FY2019 |

Three things about the shape, each of which was got wrong first:

- **GENERATED, for rule 2's reason.** These counts fall as each extractor is fixed, and a
  hand-typed *ten pages* would be wrong the first time one was -- which is the same failure
  the state machine was rewritten to stop.
- **The source is the page map, not the refusal files.** A page one extractor refused and
  another read is READ: nothing is missing and there is no gap. `state == 'refused'` is the
  join already made -- refused by somebody, cited by nobody.
- **The years are LISTED, never a range.** The first draft said `FY2013-FY2023`, which
  claims eleven years of silence where there are seven, and a resident reading the gaps page
  has no way to tell which. A range is only honest when it is contiguous.
- **A register missing from `REFUSED_FAMILY` fails the build** rather than going
  unregistered, which is the same discipline as `PROOF` below.

### 3d. Two verifier problems that are not data problems

- **`build_if_students_leave.py --check` fails inside `check_generated.py` and passes when
  run alone**, twice each. `check_generated` runs 8 checks in parallel and this one WRITES
  to `lunenburg.db` while another holds it. A concurrency defect in the verifier.
- **`write_recording_minutes.py --check` is red** on five pre-existing files needing
  `--retag`, which calls `claude` — about $0.25. Predates this work.

### 3e. Rebuild ORDER -- DONE: `check_generated.py --rebuild`

`check_generated.py` went 7 stale → 12 → 7 → 4 across passes because rebuilding one
generator changed inputs for another. It is four rounds of guessing every time, and it is
why a "quick rebuild" took an hour.

    python3 scripts/check_generated.py --rebuild

It checks, rebuilds what is stale in dependency order, and **re-checks and goes again until
nothing is stale.** Four things it had to get right:

- **The graph is INCOMPLETE ON PURPOSE and the loop is what makes that safe.** There are 157
  generators and nothing has ever mapped every edge; a graph claimed to be complete would be
  the worst of the three options, because it would be believed. `PREREQ` declares only the
  edges somebody has been bitten by. The graph makes it converge in fewer rounds; the loop is
  what makes it converge at all. Past six rounds it stops and says an edge is missing.
- **A VERIFIER IS NOT STALENESS AND MAY NOT BE BUILT AWAY.** A check is rebuildable exactly
  when it was invoked with `--check`; dropping the flag is the generator. The other 29
  entries recompute a published figure or assert every source is catalogued, and running one
  again reports the same failure and changes nothing -- the same trap as rerunning a refused
  page. They are listed separately as *needing a person*.
- **Seven generators may never be rebuilt by it.** `SPENDS_ALLOWANCE` names the ones that
  call `claude -p`. A convenience flag must not outrun the caps the refresh drips them at,
  and rule 7g says interactive work on something a process covers needs TJ to agree in that
  turn.
- **A cycle is reported, not recursed into.** An undeclared cycle among 157 generators is
  possible and a `RecursionError` is a terrible way to be told.

One edge learned writing this, and it is the reverse of the intuition: **`build_db` comes
AFTER `build_extraction_gaps`**, because the database reads `money-gaps.csv`, which the gap
generator writes. A gap registry is not downstream of the data.

`build_pipeline_state.py` was NOT in `CHECKS` at all, which is why its staleness went
unnoticed until it was run by hand -- a generator outside that list is a generator whose
staleness is invisible. Added.

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

**CAUGHT UP, in one session rather than two days.** Two runs on 27 September landed the
9 remaining tables -- 5 tables / 36,388 rows, then 4 / 37,687 -- and the consistency check
passes: `ok: D1 matches -- 119 tables, 153,414 rows`. Ordinary changes from here are a few
thousand rows and land in one run.

**One thing that did not add up and is worth not relying on.** 74,075 rows at the ~2x
write-with-indexes estimate is about 148,000 writes against a 100,000-a-day free tier, and
both runs succeeded. So either the multiplier is pessimistic or the cap counts something
other than what the estimate assumes. The incremental push is right either way; the
arithmetic in the note above is not a budget anybody should plan against.

**`money_gaps` changed today (3c) and has not been pushed.** It is one small table; the next
`sync_d1.py` takes it.

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

### 3h. THE METRIC -- REPLACED, DONE

TJ, 27 September 2026, after the count moved three times in a day: *"i think we need a
different metric then. read and refused as separate? (refused need to be... rerun?!)"*

**No -- a refused page must NEVER be rerun.** Rerunning returns the same refusal and pays
for it. That misunderstanding was the dashboard's fault: `15 left` invites exactly that
purchase, and it is the clearest evidence the metric was wrong rather than merely noisy.

WHY IT KEPT MOVING. `read` meant *any dataset mentions this page*. That is a property of our
FILING, so it changed whenever a file was added -- which happened twice on one day, in both
directions. It was not a property of the archive, and it answered a question nobody asked.

THE REPLACEMENT, shipped. Four states, each mapping to exactly ONE action, and only one of
them costing model tokens:

| state | means | to fix it | costs | now |
|---|---|---|---|---:|
| PROVEN | rows tie to a total the page prints | nothing, it is done | -- | 162 |
| UNPROVEN | rows exist, nothing proved them | write the check | code | 282 |
| REFUSED | an extractor reached it and wrote nothing, with a reason | fix the extractor | code | 30 |
| UNREAD | nobody has looked | read it | TOKENS | **0** |

**UNREAD is 0. No amount of spend moves this stream**, and the old card was inviting a
purchase that does not exist. **PROVEN is 162, not 445**, because most of those pages are
cited by rows that never reconciled -- better to publish that than to be corrected a fourth
time.

#### The registry is the part worth keeping

`PROOF` in `map_annual_report_pages.py` names, for every one of the 49 datasets that cites a
page, **the column carrying its verdict and the style that column is written in**. It is
declared rather than sniffed because the vocabulary is genuinely heterogeneous -- nine
different columns, because each table family states a different identity about itself -- and
a script guessing which column meant `proved` would be reading a position as a name, which
is rule 13's own trap. Five styles:

    VERDICT       a `checked` / `check failed` / `no check` column          19 datasets
    NOTHING       nothing anywhere records a check                          16
    CLOSED        filled ONLY with an identity that closed; empty is silence  6
    YES           the affirmative value is the literal `yes`                  3
    PROSE         a real check, recorded in a sentence no script can read     3
    CONSTRUCTION  published only when it footed; the rest are in `*-refused`  2

`PROSE` is the one to notice: `none -- the page states no total` and `Checked the identity
... it held exactly` sit in the same field of `annual-report-reads.csv`. Those pages are
UNPROVEN, and the remedy is to record the verdict in a column, **not to parse the
sentence**.

**A dataset missing from `PROOF` FAILS the build**, in the ordinary run as well as under
`--check`, because a new extractor landing silently in UNPROVEN would read as a finding about
the archive -- the silent-zero shape CLAUDE.md names as four of thirteen defects in a day.
It earned that on its first run: `revenue_history` cites pages, exists only in the database
with no CSV, and was absent from the survey that built the registry. (It is a projection of
`annual_report_receipts WHERE status='checked'`, so its WHERE clause is its verdict.)

#### Three details that were wrong first

- **PROVEN NEEDS A CLEAN READING, not a lucky row.** A dataset proves a page when its check
  closed there AND nothing it read there failed. `any row passed` would call
  `report_appropriations` proven on pages where 4,870 rows failed beside 157 that passed --
  the aggregation CLAUDE.md forbids without splitting on `status`. 100 unproven pages carry
  `appropriations` in the new `failed_by` column, which is 3i at page grain.
- **REFUSED went 29 to 30.** `extraction-blocked.csv` is a refusals register that predates
  the `*-refused.csv` naming, so neither the column test nor the name test caught it, and it
  was the ONLY thing citing FY2019 p44 -- a page counted READ on the strength of a record
  that our reading of it FAILED. **Third instance of that one inversion.** FY2015 p4, its
  other page, has too few figures to be in the map at all.
- **`table-corrections.csv` is excluded too**, as a log about another dataset's cells rather
  than a table of figures. All four of its pages are cited by `report-appropriations` anyway,
  so excluding it moved nothing -- which is the point of doing it before it does.

#### What it touched

`read` survives as a DERIVED column (proven + unproven = 444), so nothing already reading the
CSV breaks, and `proved_by` / `failed_by` / `refused_by` were added so a state can be audited
back to the identity behind it rather than taken on the state's word. Converted:
`build_ingest_status.py` (the card), `build_ingest_plan.py` and `build_pipeline_state.py`
(both now read the derived `read`, because both mean *located*, not *proven*).

**The dashboard headline is `unfinished`, not `done`.** TJ, 27 September 2026: *"the upper
metric for that annual report page needs to be 'unfinished' with an itemized breakdown inside
the panel with these specific terms"*. Right, and for a reason the other five streams do not
have: the remainder here is four different jobs. A headline counting what is DONE has to pick
one definition of done and every choice was wrong -- `read` drifted with our filing, `proven`
is honest and reads as though 312 pages were unstarted. `unfinished` is true whichever job
you mean, the five terms are itemised beneath it uncollapsed, and the pill carries the only
figure spend can move: *nothing left to READ -- every unfinished page is code.* A zero row
is KEPT, because `UNREAD 0` is the most useful line on the card and a row that vanishes at
zero cannot say it.

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

## 5. AND A SECOND RULE, FROM THE METRIC ITSELF

**A PROGRESS COUNT MUST BE A PROPERTY OF THE WORK, NOT OF OUR FILING. Where it cannot be,
count what is UNFINISHED.**

`read` moved twice in one day, in both directions, without the archive changing — because it
meant *some file of ours mentions this page*. Adding a dataset moved it up; classifying one
as a catalogue moved it down. Neither event was progress, and both were published as
progress. `proven` cannot do that: it depends on whether the page's own printed total agrees
with our rows, which changes only when the arithmetic changes.

**The corollary is the headline.** Any count of DONE has to pick one definition of done, and
where the remainder is several different jobs every choice misleads. `unfinished` is true
whichever job you mean. So: **the upper metric is what is left, the panel itemises what kinds
of left, and each kind names its ONE action and whether that action costs model tokens.** A
zero stays on the board — `UNREAD 0` is the most useful line on this card, and it is the line
that says no amount of spend moves the stream.

**And the enforcement lives in a declared registry that fails the build.** `PROOF` (what
proves a page) and `REFUSED_FAMILY` (what would close a refusal) both refuse to run when a
new dataset is absent from them. That is the difference between this and the three earlier
attempts at the same count: the failure mode of an unmapped dataset is now a build that stops
and names it, rather than a number that quietly reads as a finding about the town.
