# The plan — 25 September 2026, revised the same day

Written to survive a context reset, at TJ's request, at the end of a long session, and
revised after the session that worked it. **Batch 13 is done, §3c is done, the queue is 28
pages from 31, the two scheduled jobs are loaded again, and the reading-time ratchet is
green.** What is left is §3b and one thing that was never on the list: the org chart and the
money pages are now cross-linked, and the BOARD pages are not.

**Nothing in this file is a source.** After a reset it reads exactly like something
already verified — that is precisely the trap CLAUDE.md rule 13 names. Every count here
was measured on 24–25 September; re-measure before you lean on one. The commands to
re-measure are given beside each.

Read `CLAUDE.md` first.

---

## 1. STOP — read this before running anything

**BOTH SCHEDULED JOBS ARE LOADED AGAIN**, 25 September, at TJ's request, with the sweep on
Thursday 02:00. The table below is what they were; it is kept because the reasons still
matter.

**AND LOADING THE REFRESH STARTS A RUN.** Its plist carries `RunAtLoad`, so
`launchctl load` fired a full `refresh.py --deploy` immediately -- an unrequested deploy,
and a second site build racing the one this session needed. It was stopped after ten
seconds and nothing was published. If you load it again, expect that, and know that the
run happens in the refresh WORKTREE at `origin/main`, so it cannot publish a working tree's
uncommitted changes.

**Two scheduled jobs were UNLOADED, deliberately.** TJ cancelled them at 99% weekly usage.

```
launchctl list | grep lunen          # only `status` should be loaded
```

| job | when it used to run | state |
|---|---|---|
| `org.lunenburgbudgetproject.refresh` | daily 07:00 | **unloaded** |
| `org.lunenburgbudgetproject.sweep` | now Thursday 02:00 (was Wednesday 18:00) | **unloaded** |
| `org.lunenburgbudgetproject.status` | writes the local dashboard | loaded, free, leave it |

To restore:

```
launchctl load ~/Library/LaunchAgents/org.lunenburgbudgetproject.refresh.plist
launchctl load ~/Library/LaunchAgents/org.lunenburgbudgetproject.sweep.plist
```

**The weekly reset is THURSDAY AT 11:00.** The sweep's own header said 22:59 Wednesday
for as long as it existed, so it quit twelve hours early every week — fixed on 24
September, but the fix has never actually run. **Watch its first real run.**

**DO NOT run `scripts/check_generated.py` while anything else is working.** It spawns 8
Python processes and rebuilds `lunenburg.db` on every pass. Running it repeatedly beside
two subagents and the daily refresh **crashed TJ's machine on 24 September.** Run it
ONCE, at the end, ideally `--serial`, with nothing else going. This is written in
CLAUDE.md and I did it anyway.

---

## 2. Where things actually stand

Measured 25 September. Re-check with the commands given.

- **Everything is committed and pushed.** `git log --oneline -1` → `4a92956d`.
  Three state files may be dirty (`archive-push-state.csv`, `d1-pushed*.txt`) — they are
  written by the D1 and archive pushes and are safe to commit.
- **The site is BUILT AND DEPLOYED**, verified from production: 400/400 routes render,
  today's datasets are served, and two PDFs fetched from the live site hash-match the
  archive (rule 10's own test). `https://lunenburgbudgetproject.org`.
- **D1 is synced** — 117 tables, 153,608 rows, read back and verified.
- **R2 backup is complete.** Five objects refused and all five are explained: three are
  documents already registered in `document-defects.csv` (the district edited its School
  Committee page; DLS regenerates two spreadsheets), and two are our own derived files
  that were revised after upload — an R2 object cannot be corrected, only superseded, and
  git holds the current version.

---

## 3. The work, in order

### 3a. Batch 13 — the staff directories. **DONE, 25 September.**

All seven addresses answered. Six are sheets; the seventh (`lunenburgschools.net/contact`) is
the district's own INDEX of the other six, and the anchor text on it is the school's name --
so `fetch_school_staff_directory.py` discovers the listings rather than carrying a list, and
a sixth building's sheet would appear here without anybody editing the script.

    python3 scripts/fetch_school_staff_directory.py --if-changed
    python3 scripts/extract_school_staff_directory.py

**527 rows across six listings**, in `sources/data/school-staff-directory.csv`, grain = A
PERSON AS ONE LISTING PRINTS THEM. Nothing is merged. `school-staff-shared.csv` carries the
28 people more than one school lists as its own; one of them is on four.

**One correction to the plan as written.** It called the first address "one sheet with town
staff and school staff". It is not: it is titled *Directory of Staff - All Lunenburg Public
Schools Staff* and holds 257 school employees and no town staff. The town's directory is a
separate source and was already held.

**What the two encodings do, and why both are kept.** The roll-up writes sharing into a
free-text school column (`Primary School & THES`); the five buildings write it by repetition.
They agree about five of the 28. Most of the apparent disagreement is the roll-up's COMBINED
value `Lunenburg Middle High School` for the building the two upper schools share -- so it is
structure, not noise, and neither side is corrected against the other.

**Three things found that were not expected, and each is now written into the code:**

1. **A published Google Sheet's HTML is not byte-reproducible.** Google stamps a fresh
   `nonce` into every `pubhtml` response and the district's Sites page comes back a different
   length on consecutive requests. The CSV exports ARE stable. So change detection compares
   the ROWS and keeps the rendering, and the HTML is registered in `document-defects.csv` so
   a copy check reporting it as drifted is read correctly. Checked, twice, before relying on
   it -- the town's own directory pages *are* reproducible.
2. **Turkey Hill's sheet is a different document from the other five.** A two-column-block
   office layout, first-name-first, no emails, group headings in the same column as the
   people, and a `/edit` address rather than a published one. It reads through a spatial
   reader; the other five announce themselves with a `Name` header. And it is internally
   inconsistent: its left block heads a column `Room #` and fills it with JOB TITLES while
   its right block heads the same column `Room #` and means it. A hand-built sheet, rule 13a.
3. **The join key is the email local part, and it is the first stable person-identifier this
   archive has held** -- but two of the five listings omit it. Primary prints no address for
   any of its paraprofessionals, so 22 rows are keyed on a NAME, which is the join the FY2022
   roster hunt was burned by. Every row says which of the three keys it has.

**Both directories are now on a WEEKLY recurring fetch**, gated in `refresh.py` on
`checked.csv` rather than on the weekday, so a missed day does not cost a week. A snapshot is
written only when the rows moved; every look is logged either way, because "it did not change
between July and October" and "nobody looked between July and October" must not read alike.
The town's directory was on NO schedule at all and had exactly one snapshot, 22 September.

**What it cannot say, now registered in `money-gaps.csv`:**

- **Which building a shared employee actually works in, and for how much of the week.** The
  repetition is the measurement; "a shared specialist" is a hypothesis and no sheet carries a
  fraction. Carol Saranich is listed by three schools and could be a third of a post in each.
  *Closes: the district's FTE-by-building assignment schedule.*
- **How many people the district employs.** The roll-up names 257; the five buildings name 45
  it does not, and it names people no building lists. Some of that is one person written two
  ways -- `Skye Abreu` against `Skye Abrue` -- and nothing published separates a second
  spelling from a second person. The existing "How many people the schools actually employ"
  row was extended rather than duplicated.

**And it reaches `/org-charts`.** `_rows_school_directory()` in `build_org_charts.py` puts
FY2027 in the chart: 280 named people across five subunits, and a shared person lands in two
subunits by construction, because `check_org_charts.py` groups by `(unit, fy, subunit)` and
its DOUBLED test therefore cannot fire on the finding. All shape checks pass with zero FY2027
issues.

### 3b. The annual-report queue — 28 pages left, from 109. **THE REMAINING WORK.**

    python3 scripts/map_annual_report_pages.py

| subject | pages | note |
|---|---:|---|
| receivables | 9 | cropped pages — see below |
| trust-and-stabilization | 6 | FY2023 needs a re-OCR, not a reader |
| balance-sheet | ~~4~~ **1** | the three enterprise pages are credited now, see 3c |
| regional-school | 4 | Monty Tech, untouched |
| tax-collection | 3 | FY2011–FY2013, torn scans |
| unknown / capital / enrollment / cultural-council | 5 | small, mostly misclassified |

**Several of these are NOT reading jobs and must not be treated as one:**

- **FY2019's receivables BALANCES column is off the right edge of every page** — the page
  is *cropped*, not faint. No re-scan or parser recovers a column that is not on the
  image. The remedy is asking the Town for an uncropped copy.
- **FY2023's trust table** prints its arithmetic correctly and the scanner returns the
  figure block as two tokens (`5=5=2255225229`). That closes with a re-OCR of pages 49
  and 51, not with any amount of work on the reader.
- **FY2011 p60, FY2011 p98, FY2012 p114** are pages where our PAGE CACHE renders almost
  nothing while the OCR holds a full table. 26 such pages exist archive-wide; see §5.

### 3c. Small, cheap, high value. **DONE.**

- **The three balance-sheet pages are credited.** The cause was one column over from where
  the plan said: `enterprise-balance-sheet.csv` names its page `page_pdf`, and the backlog
  join required the literal name `page`. `map_annual_report_pages.py` now has `PAGE_COLUMNS`
  beside `YEAR_COLUMNS`, in BOTH halves of the join (the CSV half and the database half --
  trap 2 below is about exactly that), and `page_printed` is deliberately excluded because it
  is the number in the corner of the page, not its index in the PDF. Queue: 31 -> 28,
  balance-sheet 4 -> 1.
- **`balance-sheet-refused.csv` is described**, and so are the other seven datasets that
  check was flagging: `debt-repayment-detail`, its refusals, `gross-wages-refused`,
  `report-appropriations-supplement`, its refusals, `salary-schedule` and its refusals.
  `build_source_index.py` is clean.

### 3d. Cross-linking the org chart and the money. **DONE — and not on the original plan.**

TJ, mid-session: *"i would like to cross link the org chart and the personell pages for each
department, so we can see the trends over time when needed, or directly se the people when
needed."*

`scripts/build_body_crosswalk.py` -> `sources/data/body-crosswalk.csv`. The name join lives
in ONE place and both payloads read it, because a map written twice is trap 6.

- **34 of 63 bodies** reach a money page, 32 reach a board page. The join is on a NAME, which
  is the weakest kind, so `MATCHES_FLOOR` fails the build if it drops.
- **The floor was invented before it was measured**, twice: the file said 40, then 36, and the
  run makes 34. Same defect as the sweep being precise about a reset time nobody had checked.
  The third number is the first measured one.
- **`/org-charts` gained a trend**: named people per year, as a COMPONENT (rule 7f) whose bars
  are clickable and move the chart to that year. Its caption says it counts NAMES the town
  printed and is not a staffing level -- the Fire Department reads 12 in FY2022 against 38 and
  40 either side, which is a statement about one page of one book.
- **`/departments/<slug>` and `/boards/<slug>/finance` gained the people**, with the YEAR
  attached, because the rosters end at FY2025 for most bodies and FY2027 for those read off
  the officials listing.
- **A money page can have TWO charts behind it.** The School Committee owns the district's
  accounts and this project draws both the committee's four seats and the district's 280
  staff against them. The first version wrote one and let the last row win, publishing
  `4 people` for a body that employs several hundred.

- **All three surfaces carry it.** `/boards/<slug>` is where a resident actually lands for a
  board, so `build_boards.py` reads the crosswalk too: 30 of 60 boards now show `The people: N
  named in ... in FY`, beside the Finance link that was already there. Two halves of one
  question about a board, and until now only one of them was on the page.
- **An empty chart is not a link.** `Board Of Assessors (staff)` is a real unit with nobody
  ever read into it, and the first version published `the 0 people named in ... in FY` for it
  on two pages. All three loaders skip a body whose chart holds nobody.

## 4. Open decisions — TJ's, not ours

**Both of the ones listed here are resolved.** Kept, with what was decided, because the
reasoning is what the next person needs.

- ~~The reading-time ratchet.~~ **FIXED WITHOUT `--allow-growth`, and the cause was not
  length.** `/analysis/monty-tech` was rendering its short version TWICE: the payload's three
  conclusion cards (902 words) above the markdown's own `## What this establishes` (759), the
  same claims in two voices. `Analysis.tsx` already fixed that defect for reports carrying a
  `stats` row and its gate was simply narrower than its reason -- `ownsShort` now reads
  `stats || conclusions`. Only that one page moves; athletics and budget-vs-actual open their
  documents with `Why this is a separate document...`, so `split` is null for them and there
  is no prose short version to drop. **And nothing was lost:** the three claims the prose
  carried alone are payload conclusions now -- the negotiable share of the bill, the per-pupil
  foundation gap, the routes out -- so they render inside the fold instead of off the page.
  Six conclusions where there were three.
  - Two things the validator and the data caught on the way: a bare `97` was refused for
    having no unit (rule 7b, mechanically), and the first draft read the assessment parts off
    the LATEST year that printed them, which put one card on FY2027 beside five on FY2026.
  - `verify_monty_tech.py` was already failing on three figures before any of this, and they
    are fixed too: the document said `8,899 of 12,015 meeting documents searchable — 74%`
    and the model says `10,919 of 12,055 — 91%`. Rule 2, in the file that tells everyone else
    never to type a figure into prose.
- ~~Whether to re-enable the refresh and sweep.~~ **Both loaded, 25 September.** See §1 for
  the `RunAtLoad` surprise.

## 4b. THE MANIFEST USED TO DROP DOCUMENTS. It cannot any more

**The single most important thing in this file.** 25 September 2026, TJ: *"i want to make
sure any file we downoad is ALWAYS saved before we can even think of deleting it or cleaning
a repo..."*

**What was wrong, and it was not the refresh.** `sync_archive.py --manifest` rebuilt the
index into an immutable bucket FROM WHATEVER THE CURRENT TREE HELD. The refresh fetches
documents in its own worktree; the documents are gitignored, so only the manifest ROW travels
to main. A session in the other tree then ran `--manifest`, did not find those files, and
dropped their rows:

| commit | |
|---|---|
| `ac033301` Daily refresh, 2026-09-21 | added 27 meeting documents |
| `c28c8d2b` an interactive session | removed them |
| `8fba3d31` Daily refresh, 2026-09-23 | added 33 more |
| `712f2009` an interactive session | removed them |

**39 documents lost their index that way.** The bucket does not allow listing and the
manifest is the only thing that names an object, so a dropped row ORPHANS it: 33 were
already byte-verified in R2 and became unreachable; 6 had never been pushed at all.

**Do not re-derive the wrong conclusion from a low count.** Two hours went into "33
documents are missing" before the truth: they were in the other worktree, and
`build_minutes_searchable.py` defines `held` as *index rows whose file exists on disk*, so
the number is TREE-LOCAL and nothing in the payload says so. A complete tree gives 12,088
held; the tree missing documents gave 12,055; a payload committed earlier said 12,072. All
three were "correct" about their own tree, which is the whole defect.

**The three invariants now in the code.**

1. **The manifest is append-only for frozen keys.** A key on no disk KEEPS its row and is
   reported as a `--pull` item. A frozen key whose bytes disagree with the record REFUSES
   the write -- a publisher's file does not change, so that is a defect, not a revision.
   Proved by re-running the exact operation that dropped 39 rows twice: it kept them.
2. **Nothing destructive runs while a document is held in one place.**
   `scripts/check_archive_backed_up.py` gates `daily_refresh.sh` before its `reset --hard`
   and `clean`, and `weekly_sweep.sh` before its reset. It is OFFLINE on purpose -- it reads
   `archive-push-state.csv`, which records pushes that were read back and compared -- so it
   cannot block a refresh because the network had a bad morning. Proved by planting an
   unbacked document: exit 1, named. Removed: exit 0.
3. **Documents are backed up WHEN THEY LAND.** The push was step 10 of 10 with
   `check=False`; its own comment already named a Stormwater agenda lost that way on 17
   September and it was still last and still silent. `back_up_documents()` now runs the
   moment agendas land and after the document watcher, and a failure becomes a NOTE that
   reaches the run registry and the notification.

**And `frozen()` no longer decides by file extension alone.** `.csv` is not in
`ORIGINAL_EXTS`, so the district's staff sheets -- the ROWS every figure in
`school-staff-directory.csv` is computed from -- were classified as OURS and nothing required
them to be backed up. `.csv` cannot simply be added, because every `sources/*/index.csv` is
our catalogue and changes constantly. So the second test is the PATH: **a file inside a
dated snapshot folder is the publisher's, whatever its extension.** Rule 13a pointed at
backup policy -- ask what produced it, never what it was saved as.

**The repair, done 25 September:** 39 index rows restored from git history; 13 documents
pushed and read back; 33 pulled from the bucket. The tree now holds every document its
catalogue names -- `0` meeting index rows without a file -- and all 13,241 are in the bucket.

**What is NOT done.** `daily_refresh.sh` still does `git reset --hard origin/main` and
`git clean -fd` (now excluding `/sources/`), and still commits with `git add -A`. TJ:
*"i think we need a new model. not a full git clean."* The clean exists ONLY to make
`add -A` safe -- the file says so itself -- so the replacement is to compute what the run
produced from a start-of-run fingerprint and never destroy anything. Not started.

## 5. Traps found in this session — do not rediscover these

Each cost real time. Each is now written into the code that has it.

1. **A join that matches nothing looks exactly like data that is absent.** The backlog
   credited a page only when a dataset cited a column literally named `fy`.
   `outstanding-debt.csv` names it `report_fy`, so 1,038 proven rows joined to nothing and
   the queue printed `debt 34 pages unread` the day after the debt tables were read to the
   dollar. `YEAR_COLUMNS` in `map_annual_report_pages.py` now accepts both — and
   deliberately NOT `as_of_fy` or `due_fy`, which are years a ROW is about.

2. **A refusal is not a reading, and a refusals register can credit its own pages.** Rows
   saying "this page refused" inside a data file marked those pages READ. Refusals now go
   in a separate `*-refused.csv` carrying a `state` column, which the queue skips as a
   catalogue. **The database half of that join had no such test** and
   `capital_plans_refused` was crediting pages through it — fixed, but check both halves
   if you add a register.

3. **`csv` swallows OCR lines.** A `"` in a recognised word makes Python's csv run a field
   on to the next quote — **9,848 boxes, 5.19% of the archive, in 15 of 16 reports**, and
   it can also raise `field larger than field limit`. Always read
   `sources/town-budget/ocr/*.tsv` with `quoting=csv.QUOTE_NONE`.

4. **"They are all scans" was never checked, and five are not.** FY2014, FY2015, FY2016,
   FY2018 and FY2025 carry real PDF text layers that read exact to the dollar. Check with
   `pdfplumber` (`len(page.chars)` vs `len(page.images)`) before accepting that a page
   cannot be read. Some are drawn rotated with `/Rotate` at 0 — the rotation is in each
   glyph's text matrix, so it is *exact*, not measured.

5. **A check can fail because its defect was FIXED.** `verify_school_staffing.py` demanded
   that a doubled Turkey Hill roster be *reported*, long after the doubling was
   deliberately removed from the data. Worse, the same root killed a PAGE:
   `/who-works-in-each-school` read `roster.doubled[0]` and prerendered to **zero
   characters** — a blank page in production. One symptom was loud, one silent.
   **Invert such a check rather than deleting it.**

6. **Three copies of one constant, drifted.** `NOT_A_REPORT` lived in `conclusions.py`,
   `build_master_report.py` and `verify_conclusions.py`. One gained `threads`; the others
   did not; the synthesis page refused to build. A check that two copies agree has already
   accepted that there are two copies.

7. **Our page cache loses 26 financial pages.** It renders under a quarter of the money
   figures the OCR holds — FY2023 p50 is **301 against 0**. Three extraction holes fall
   exactly on such pages. **THE CAUSE IS NOT ESTABLISHED:** a stale cache is the obvious
   candidate and the vintage does NOT separate them (16 lost pages in re-scanned editions,
   10 in editions of the cache's own vintage). Registered in `money-gaps.csv`. A rebuild
   would settle it and rewrites the input every other extractor reads.

8. **`SCANNED_MONEY` is anchored** (`^...$`, six alternatives). `findall` over a line of
   text never matches. Split the line and match each token — I used `findall` and got a
   confident, uniform, completely wrong result.

---

### Found on 25 September, and each is now in the code that had it

9. **A `RunAtLoad` plist starts a job the moment you enable it.** `launchctl load` on the
   refresh fired a full `refresh.py --deploy` -- an unrequested deploy, and a second site
   build racing the one this session needed. Loading a job is not the same as scheduling it.

10. **Half of what a fetcher downloads may not be byte-reproducible.** Google puts a fresh
    `nonce` in every `pubhtml` response, so two fetches a second apart differ while the people
    on the page are identical. Change detection on the whole set therefore reports CHANGED
    every run -- which would have written a snapshot a day, each one frozen in the bucket for
    ten years. Compare the DATA, keep the rendering. And CHECK which of the two you have: the
    town's directory pages are reproducible and the district's sheets are not, and there is no
    way to tell from the outside.

11. **A floor invented at a desk is a figure typed into prose.** `MATCHES_FLOOR` in
    `build_body_crosswalk.py` was written as 40 before anything was counted, then 36 with the
    map written but not run; the answer is 34. Rule 2 applies to a constant in a script as
    much as to a sentence on a page -- and the tell is the same one the sweep had: precision
    about a number nobody had measured.

12. **One key per person is an assumption, and it split a person in half.** Meredith Weiss is
    printed with an address by two listings and without one by two others, so she came out as
    `mweiss` on two and `name:meredithweiss` on two -- two people sharing two buildings each,
    where she is one person on four listings. A key that is MISSING on one sheet is not a
    different person. What the fix must not do is the reverse: `Skye Abrue` and `Skye Abreu`
    stay two keys, because collapsing those is a judgement that a typo is a typo.

13. **A check that counts the collapsed content of a `<details>` as read.** Not fixed, and
    deliberately: `build_reading_time.py` counts every word inside a `data-short` element,
    including an expansion a reader never opens, which is in tension with rule 7b's *additional
    context must go into the expansion*. Relaxing the measure to clear a red check is the same
    move as `--allow-growth`, so monty-tech was fixed by removing a duplicated section instead.
    **If this is ever changed, change it as a deliberate decision about what the five-minute
    budget MEANS, not as a way to make a page pass.**

14. **AND THERE ARE TWO ROUTES TO ONE REPORT, which cost a round trip.** Monty Tech is at
    `/monty-tech` (its own React page) AND `/analysis/monty-tech` (the document through
    `Analysis.tsx`). Fixing the second put the first over budget: `MontyTech.tsx` rendered
    `rows={d.conclusions}` -- ALL of them -- into its short version, which was fine at three
    and wrong at six, so its declared short version went 902 -> 1,613 words without a line of
    that file changing. Fixed with `splitConclusions`, which `/analysis/*` already used.

    **THE LATENT VERSION IS STILL THERE AND IS WORTH KNOWING BEFORE IT BITES.** Roughly
    fifteen report pages render `rows={d.conclusions}` whole and about ten use
    `splitConclusions`; two habits in one codebase. Every one of the first group is a page
    whose short version grows silently the next time somebody adds a conclusion to its
    generator. They all pass TODAY -- this is a shape, not an outage -- and unifying them is
    its own task. `build_reading_time.py --check` is the thing that would catch the next one.

15. **A CHECKER THAT FINDS A SECTION BY A PHRASE INSIDE A COMPONENT.**
    `check_org_html.mjs` locates the end of the chart with
    `html.indexOf('What this report counts')`, which is the `Grain` component's own heading.
    Using `Grain` for the new trend chart's caption -- ABOVE the chart -- truncated the page
    the check reads, and it reported `no bands rendered at all` for **51 of 63 bodies**, none
    of which had anything wrong with it. Worse, on a first partial read the twelve it happened
    to print looked like small single-person committees and were written off as pre-existing.
    They were not: with the caption fixed the check reports **63 of 63 units, zero problems**.

    Fixed on the merits rather than by relaxing the check -- a report has ONE grain block and
    that was a chart caption wearing the costume. But the brittleness is real and is rule 13b's
    own trap: **a position is not a name.** A reader that finds a section by a string living
    inside a component breaks the next time anybody reuses that component. Hardening it is its
    own task and has not been done.

## 6. What is NOT established

Keep these out of prose as facts. Each is a measurement with the explanation withheld, per
rule 7.

- **Why FY2018's receivables open $13,300.00 above where FY2017 closed.** Both are the
  town's own printed grand totals, in two books, verified on the pages. A prior-year
  adjustment, a reclassified charge and a typo all fit equally.
- **Why the same $1,085,674.86 appears twice in FY2015's opening** — once folded into
  `SEWER BETTERMENT` and once on a new `MEADOW WOODS WATER BETT` line.
- **Why FY2015's printed debt GRAND TOTAL omits the two MS-HS CONSTRUCTION bonds** in
  every year column, while both are printed in the table above it.
- **Why FY2021's valuation page reprints FY2020's TOTALS row**, $194,412,308 below what
  its own four class rows sum to.
- **Why FY2017's own report prints $51,797,859 six times** where its four successors all
  print $51,797,860. One dollar. Both kept.
- **Whether the page cache's 26 lost pages are a staleness problem** (trap 7).
- **That the FY2016 salary COLA was 2%.** The adopting article states intent; the
  arithmetic shows only that two figures stand in that relation.

---

- **How many people the district employs.** Its own roll-up says 257; the five buildings name
  45 it does not, and it names people no building lists. Part of the difference is one person
  spelled two ways and nothing published separates that from two people. Registered.
- **Whether a person on two schools' listings is a shared post.** The repetition is real and
  measured; the meaning is not. No sheet carries a fraction of a post.
- **Whether the 23 bodies with no money page have no account, or a name the two sides spell
  differently.** `build_body_crosswalk.py` prints them every run and does not guess. Most look
  like advisory committees the town votes nothing to; that has not been checked one by one.

## 7. Commands worth knowing here

```
python3 scripts/map_annual_report_pages.py     # THE QUEUE — what is left to ingest
python3 scripts/fetch_school_staff_directory.py --if-changed   # the district's six staff sheets
python3 scripts/extract_school_staff_directory.py              # ...and who is on two of them
python3 scripts/build_body_crosswalk.py        # the org chart joined to the money pages
python3 scripts/build_ingest_plan.py           # the ordered plan, batch 13 is the new work
bash scripts/status.sh --once && open build/status/index.html    # the dashboard
python3 scripts/check_generated.py --serial    # ONCE, at the end, nothing else running
python3 scripts/sync_archive.py --push         # back up to R2
python3 scripts/sync_d1.py                     # push the database
cd fy28 && npm run build:site                  # 400 routes; then check_prerender.py
```

Deploy needs Node 22: `nvm use 22 && npx wrangler pages deploy` from `fy28/`.
**Rule 10: nothing deploys without being asked.**
