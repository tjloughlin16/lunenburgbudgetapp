# The plan — 25 September 2026

Written to survive a context reset, at TJ's request, at the end of a long session.

**Nothing in this file is a source.** After a reset it reads exactly like something
already verified — that is precisely the trap CLAUDE.md rule 13 names. Every count here
was measured on 24–25 September; re-measure before you lean on one. The commands to
re-measure are given beside each.

Read `CLAUDE.md` first.

---

## 1. STOP — read this before running anything

**Two scheduled jobs are UNLOADED, deliberately.** TJ cancelled them at 99% weekly usage.

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

### 3a. Batch 13 — the staff directories. **Start here.**

    python3 scripts/build_ingest_plan.py        # batch 13 carries all seven addresses

TJ gave seven addresses on 24–25 September: one sheet with **town staff and school
staff**, the district contact page, and **five per-school listings**.

**Why it matters more than another roster.** Every people-source in this archive is read
out of an annual report or the officials listing, so a body that files no report is
invisible. That is why `/org-charts` shows the Library employing one person when it told
the town it employs ten, and why four real departments appear in no annual report at all.
A school-staff directory is the first source here covering the district's people from
outside the annual report.

**TJ's reason for the per-school ones, in his words:** *"the reason the individual matters
is to show 'shared' resources across school, and sometimes there's more details."*

That question this archive has already tripped over. The FY2022 roster hunt found twenty
apparent duplicates and concluded they were people at TWO SCHOOLS — shared specialists,
legitimately printed twice. That is why `who-works-in-each-school` counts district staff
as distinct NAMES while keeping the school columns per-school, and why the DESE
corroboration was withdrawn. **But it rests on OUR names matching across two scans.**
Per-school directories would establish it from the schools' own lists.

**THE ONE INSTRUCTION: do not merge the five into one list.** A person appearing on two
school directories IS the finding. Deduplicating on the way in destroys the only thing
those addresses were given for.

**It must be a RECURRING fetch, not a one-off.** A published Google Sheet is overwritten
in place — it carries today and no history. And the directory we already have is in the
same position:

> `fetch_staff_directory.py` is named in **no scheduled script** — not `refresh.py`, not
> `daily_refresh.sh`, not `weekly_sweep.sh`. There is exactly ONE snapshot on disk,
> `2026-09-22`.

So the town's people are a single photograph with nothing arranged to take the next one,
and the failure is silent: the file keeps answering correctly about a day that recedes.
Follow the pattern `fetch_staff_directory.py` already holds — one dated folder per fetch,
fiscal year derived from the folder rather than typed — and put **both** directories on
the recurring fetch. That is what makes batch 13 *permanent* rather than one more
extractor.

One of the five is an `/edit?gid=0` address rather than a published `pubhtml` one, so it
may not read the same way, or at all. **Nothing has opened any of them.**

### 3b. The annual-report queue — 31 pages left, from 109

    python3 scripts/map_annual_report_pages.py

| subject | pages | note |
|---|---:|---|
| receivables | 9 | cropped pages — see below |
| trust-and-stabilization | 6 | FY2023 needs a re-OCR, not a reader |
| balance-sheet | 4 | 3 are the enterprise sheet, see 3c |
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

### 3c. Small, cheap, high value

- **Three balance-sheet pages are read but uncredited.** `enterprise-balance-sheet.csv`
  names its columns `fy`/`page_pdf`, and the backlog join reads `report_fy`/`page`. Two
  lines. This exact bug hid 13 pages earlier in the session.
- **`balance-sheet-refused.csv` has no `build_source_index.py` entry**, so that check
  keeps flagging it.

---

## 4. Open decisions — TJ's, not ours

- **The reading-time ratchet.** `build_reading_time.py --check` refuses because
  `/analysis/monty-tech` runs **1,661 words against a 1,150 budget** and declares no short
  version. `--allow-growth` moves the baseline *on purpose*; the alternative is trimming
  it. **Do not use `--allow-growth` to clear a red check** — that retires the guard.
- **Whether to re-enable the refresh and sweep**, and when.

---

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

## 7. Commands worth knowing here

```
python3 scripts/map_annual_report_pages.py     # THE QUEUE — what is left to ingest
python3 scripts/build_ingest_plan.py           # the ordered plan, batch 13 is the new work
bash scripts/status.sh --once && open build/status/index.html    # the dashboard
python3 scripts/check_generated.py --serial    # ONCE, at the end, nothing else running
python3 scripts/sync_archive.py --push         # back up to R2
python3 scripts/sync_d1.py                     # push the database
cd fy28 && npm run build:site                  # 400 routes; then check_prerender.py
```

Deploy needs Node 22: `nvm use 22 && npx wrangler pages deploy` from `fy28/`.
**Rule 10: nothing deploys without being asked.**
