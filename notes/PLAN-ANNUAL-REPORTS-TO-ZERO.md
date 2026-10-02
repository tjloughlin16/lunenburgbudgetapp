# Getting the annual reports to zero: the plan

**BEFORE ANYTHING, RUN THIS. It answers *what is done* and *what is next*:**

    python3 scripts/annual_report_progress.py

A year is DONE when every financial page the map holds for it is `proven` -- the page
closed on an identity the page itself prints. That is the ONLY definition; row-level
`status` across the `report-*` CSVs measures whether a table was EXHAUSTED, which is a
different question, and a year can be done with most of its rows still `check failed`.
Confusing the two cost an hour on 1 October 2026 -- learning loop entry 9.

**28 September 2026.** TJ: *"can you make this systematic man. its been days days days
... we keep finding major mistakes ... write a PLAN. work from it. iterate. test. improve."*

He is right, and the reason it has taken days is now measurable rather than a feeling.

## What is actually wrong, and it is not the town's data

Every defect found today was a BROKEN OR STALE INSTRUMENT. Not one was a hard document.

| what we believed | what was true |
|---|---|
| FY2021 is short $22.5M | the page cache was built 5 Sep; the OCR it derives from was rebuilt 21 Sep. The $21.65M School Department line was in the OCR the whole time |
| FY2019 is missing rows | its OCR TSV is a CLIPPED RENDER — `/Rotate 270` without swapping width and height, so the top 22.7% of every page fell off before Vision saw it |
| FY2017 is structurally broken | `plan_for()` scraped page numbers out of a PROSE COMMENT in the plan's `pages` cell, inventing a run that starts mid-table. The real run reconciles at −0.51 |
| the debt pages are unreadable | six of them were fed to the scanner upside down and nothing ever tested for it |
| rows and labels do not line up | the row band was the median gap over ALL boxes, which is the within-row jitter, not the row pitch — wrong by 3x to 8x, in THREE extractors independently |
| the town's tables are messy | `best_ruler` scored a ruler by how many cells parse as numbers, INCLUDING the halves it made by cutting a figure in two |
| some figures are enormous | `amount()` glued two adjacent cells into one number: `$13,260.96 $2,451.81` → `13,260,962,451.81`. $140 BILLION across 16 cells |
| Treasurer's Cash has no check | it reconciles every column to the printed total and discards what does not tie. The REGISTRY said otherwise |

**The common shape: a derived artefact outlived its input and kept answering confidently.**
That is cache invalidation, and this repo already has the discipline for it —
`check_generated.py` re-runs every generator's `--check`. The page cache, the OCR renders
and the extraction plan are simply not among the things it checks.

## The order, and why it cannot move

**Nothing below step 2 is worth doing until step 1 and 2 are done.** Every hour spent
debugging an extractor against a stale cache is an hour spent debugging a ghost, and that
is most of the last three days.

### PHASE 0 — make every instrument state its own freshness
1. `report_pages.py` writes the sha256 of each source TSV into the `.ocr.txt` header;
   `load()` refuses a cache older than its input. Add to `check_generated.py`.
2. An OCR TSV records the renderer version and the page geometry it assumed. A TSV whose
   boxes cannot cover the page's own mediaBox is a clipped render and must say so.
3. `extraction-plan.csv` splits `pages` into a machine-readable range and a `pages_note`.
   A field doing two jobs, parsed permissively, is what invented FY2017's phantom run.

### PHASE 1 — rebuild every derived input from source, in dependency order
4. Re-OCR whole documents whose TSV predates the rotation fix (FY2019 certainly; audit all).
5. `report_pages.py --rebuild`.
6. Re-run every extractor. EXPECT REGRESSIONS: the rebuild takes FY2023 from +0.80 to
   +6,995,550.80 and splits FY2016. A rebuild is correct and not free.

### PHASE 2 — re-measure before fixing anything
7. Re-run `map_annual_report_pages.py`. Most structural failures should vanish.
8. Only then look at what is left.

### PHASE 3 — the residue is READ, not coded
9. What survives is a handful of figures per year that OCR genuinely did not capture.
   THE INSTRUMENT FOR A MANGLED SCAN IS EYES ON THE PAGE. `table-corrections.csv` already
   exists for exactly this: `kind=read` records what the page says, with the coordinate
   and the evidence. FY2015 closed to the cent today from ONE such row.
10. Parallelise: one agent per year, reading the rendered page, emitting correction rows.

### PHASE 4 — attest what the TOWN got wrong
11. Some checks can never close because the document does not foot. FY2018 p156 over-prints
    its own subtotal by 709.00; FY2016 p145 under-prints by 45.00 — both verified against
    the PDFs' own text layers. `kind=attested` records that we read it right and the town's
    arithmetic disagrees with itself. An extractor that made those close would be WRONG.

## The rule this plan exists to enforce

**Check the instrument before you debug the data.** Every time a figure looks absent, the
first question is whether our reading of the page is current and complete — not what the
town did. Rule 13c already says a matcher that finds nothing is a statement about our
instrument. This plan is that rule applied to the whole pipeline instead of one regex.

---

## The learning loop

TJ, 28 September 2026: *"i need you to have a learning loop built into this. i need you
to review what is taking so long at every step, and improve it."*

Each entry is a thing that cost real time, what it cost, and the change made so the next
one is cheaper. Append to it; do not rewrite it.

### 1. We debugged a four-week-stale cache for three days
`pages/*.ocr.txt` is derived from `ocr/*.tsv` and had no dependency link to it, so a
rebuilt OCR left the cache silently wrong. FY2021 read as $22.5M short when the figure was
in the OCR the whole time.
**Changed:** the cache now writes the sha256 of every TSV it was built from, and
`report_pages.stale(edition)` answers whether it is current.
**Rule:** check the instrument before you debug the data.

### 2. We fought OCR on pages that have a digital TEXT LAYER
FY2014 and FY2020's pages read cleanly with `pdfplumber` — exact characters, no
mishearing. Two whole years were diagnosed in minutes once an agent tried it, after hours
of arguing with OCR boxes.
**Rule:** before reading a page by geometry, ask whether it has a text layer. Not every
year does -- FY2021 and FY2013 have none -- so ASK, never assume either way.

### 3. The same four steps are written nine times, and the shared library is ignored
`pdf_tables.py` holds twenty functions and nineteen scripts import it -- including
`looks_flipped()` and `unflip()`, which ONE script uses. I hand-wrote half-turn detection
today that was already there, better documented.
**Rule:** grep `pdf_tables.py` before writing any geometry. If the primitive is missing,
add it THERE.

### 4. A correction could mend a row but never supply one
The figures that matter most are the ones OCR dropped whole -- FY2020 p151 line 19 is the
entire reconciliation gap for that year and is absent from the extract.
**Changed:** a `read` correction that matches no row now inserts it, flagged
`inserted_row` so it can never be mistaken for something we extracted.

### 5. An agent needs the exact contract, not a description of it
Two agents wrote `column=v1` where the file's convention is `1`, so every correction built
`vv1` and silently did nothing. The run reported no error because the rows "matched".
**Rule:** when delegating, give the exact header AND one real example row from the file.

### 6. No extractor has a `--year` or `--page` flag
Every hypothesis costs a full run over sixteen reports. That is the single largest
remaining tax on iteration.
**Not yet changed.** Next.

### 7. Entry 2 named the problem and did not make it a RULE, so I did it again

Entry 2 above says, in its own heading, that we fought OCR on pages that carry a digital
text layer. Three tables later I opened FY2025's trust listing, found 30 rows where the
page prints 40, and spent the time diagnosing three of them as a disagreement between two
TOWN documents -- a finding about Lunenburg's books -- without once checking that the
reader had been given a photograph of a page that carries its own text. TJ, before I got
there: *"im assuming you used the OCR data."*

**The gap was not knowledge. It was that the process doc had the fact and not the GATE.**
Step 0 asked *"was this OCR'd too?"* and then said nothing about what to do when the
answer is yes, so it read as a diagnostic curiosity rather than a stop. A question with no
consequence attached gets answered and walked past.

`READING-A-REPORT-PAGE.md` now opens the process with a gate instead: a text layer
supersedes OCR, the OCR reading of that page is discarded rather than reconciled, and the
one-line word-count test that decides it. TJ: *"this process needs to throw out OCR data
if we have a digital text layer for the data. its more reliable. OCR is a fallback."*

**The cost, counted:** ten of forty rows silently absent, and a wrong conclusion about the
town nearly written up. **What it buys:** the test is one second and half the archive is
born-digital.

### 8. The extractor FORMAT is what I keep failing on, not the tables

TJ, 28 September 2026: *"i think we may need an updated extractor format. you fail very
often on the extractor and spin a lot."*

The afternoon is a controlled experiment. Four extractors, one archive, one reader. Three
were written on word boxes carrying x and y -- the trust matrix, Monty Tech, the capital
plans -- and each took about twenty minutes and closed on the page's own arithmetic. The
fourth extended `extract_special_revenue.py`, which is built on the page flattened to TEXT
LINES, and ate the rest of the day without closing.

**The tables were not the difficulty.** The trust matrix prints its fund names SIDEWAYS and
closed first time. Special revenue is a plain grid.

**What differs is whether the coordinates survive.** `layout_from_boxes` turns each word's x
into a character offset, and after that a column is a run of spaces most rows agree on --
so a column no row fills does not exist, and a CENTRED heading never lines up with a
RIGHT-ALIGNED figure. Three attempts to recover the names from that failed. The headings sit
at x=0.554 on all four pages, to three decimals, in the boxes I had all along.

**The cost:** an afternoon, three wrong explanations offered to TJ before anybody opened the
page, and a half-finished migration reverted. **What it buys:** `notes/process/AN-EXTRACTOR.md`,
and the rule that a new extractor starts from the boxes.

**And the migration is its own work.** Trying it inside a page fix is exactly what went
wrong; `extract_special_revenue.py` is 2,422 rows across sixteen editions and five of them
tie today.

### 9. I could not say which years were DONE, and spent an hour getting it wrong twice

TJ, 1 October 2026, asking what years were fully done and to process the next one:
*"I really don't understand..."*, then *"I don't understand. We already finished this
year."*, and finally: **"By now you could have been done processing a FY."**

He was right at every step. The answer is four years and one command; it took eleven tool
calls and two confidently wrong answers to produce.

| I said | where it came from | what was true |
|---|---|---|
| "FY2022 is the only year closed" | `git log \| grep -iE "FY20[0-9]{2} closed"` | four years are done. I grepped COMMIT MESSAGE WORDING and reported the miss as a fact about the work |
| "FY2021 is the next year, recommended" | the same grep | FY2021 already has a proven stabilization row. FY2023 is next, one page short |
| "no year is fully done; FY2024 is best at 22%" | ROW-level `status` across twelve `report-*` CSVs | FY2014, FY2022, FY2024 and FY2025 are done. Rows are not the unit |
| "step 1 for FY2025" (ran it) | — | FY2025 was finished three days earlier, by `595148b1`, whose message says the same thing step 1 printed |

**The first and second failures are rule 13c, for the third time in this file.** A matcher
that finds nothing is a statement about our instrument. `grep` over commit subjects is an
instrument, and this project records a finished year in `annual-report-pages.csv`, not in
how somebody phrased a commit.

**The third failure is the one worth keeping, because it was not sloppiness.** Both numbers
were real and they answer different questions:

- **A year is DONE when every financial page the map holds for it is `proven`** -- the page
  closed on an identity the page itself prints. `595148b1`: *"FY2025 is read: 23 of 23
  pages, every one tied to arithmetic the page states."*
- **Row `status` measures whether a table was EXHAUSTED**, which is `verify_report_tables.py`'s
  question. A year can be DONE with most of its rows still `check failed`.

I reported the second as the answer to the first, then watched it contradict the ingestion
dashboard and concluded the DASHBOARD was coarse. The dashboard was right. This is the
proxy error CLAUDE.md rule 7 names, pointed at our own progress instead of at the town's:
**a count of checked rows is not a count of finished years**, the same way dollars are not
students.

**And the fourth is navigation.** `notes/PLAN-ANNUAL-REPORTS-TO-ZERO.md` -- this file --
answers all of it in one read, including the definition of done and the phase order. I had
read `INGESTING-A-TABLE-FAMILY.md` and `HANDOFF-ANNUAL-REPORTS.md` and never opened the
PLAN, because nothing pointed at it from where I started. Its own first line is TJ asking
for this to stop happening.

**Changed:** `scripts/annual_report_progress.py` -- the single authoritative answer.
Prints the board, names the years that are done, and NAMES THE NEXT YEAR with its most
blocking state and the action for it. `--next` gives the bare year for a script; `--check`
fails if the page map is stale. It is listed in CLAUDE.md's checks and named from the top
of this file and from `ANNUAL-REPORTS.md`.

**And it refuses to answer off a stale map**, because every defect in this plan's own table
was a stale instrument answering confidently. It fired on its first run: the FY2023 work
then in flight had moved an input, so the board was one step behind and said so.

**Rule:** before reporting what is done, run the script that defines done. Never derive
project state from commit messages, and never from a count at a different grain than the
thing being asked about.

**A latent trap found while building it**, which did NOT cause the above but would hide a
failure: `python3 script.py --check | tail -5; echo $?` reports TAIL's exit code, not the
script's. Check an exit code without a pipe, or use `PIPESTATUS`.

**The cost:** about an hour, in which a year could have been processed. **What it buys:**
one command, and a definition of done that lives in code instead of in four documents.

### 10. Two instruments disagreed about what `blocked` MEANS, and the board re-opened a closed page

FY2023 was marked `blocked` on page 25 on 28 September, by TJ, who had opened the page
himself: *"its too blurry. we need to mark it as TOO BLURRY and call it HARD BLOCKED. and
move on."* `map_annual_report_pages.blocked_pages()` wrote that down in its own docstring --
**HARD BLOCKED IS NOT UNFINISHED** -- and gave the reason: *"leaving both in one bucket
means the backlog never stops containing the second kind -- every pass rediscovers it,
re-renders it, and re-concludes it."*

`annual_report_progress.py`, written three days later, counted `blocked` as not done. So the
board named FY2023 as NEXT, one page short, for three days -- and on 1 October an agent did
precisely what the register was built to stop: extracted the embedded bitmap, measured its
grid by projection, rendered the amount columns at 7x, 13x and 20x, and re-reached the
conclusion already sitting in `page-blocked.csv`. The archive did not move.

**The register was right and the scoreboard was the stale instrument** -- which is this
plan's own rule, pointed at our progress rather than at the town. Entry 9 built the
scoreboard to stop project state being derived from the wrong grain; it then defined `done`
without reading the register it queries.

**What it cost:** a session. **What it bought:** two things, and the second is the general one.

- `annual_report_progress.py` counts a year done when every page is `proven` OR `blocked`.
  A blocked page is never called PROVEN: it keeps its own column, a year carrying one is
  flagged `YES*` and not `YES`, and the pages are named under the board with the reason and
  the one document that would remove the block. The claim is *nothing is left to do here*,
  not *this was fully read*.
- **A terminal state has to be terminal in every instrument that reads it, or it is not a
  state -- it is a label.** `blocked` existed, was documented, was populated by a person, and
  still cost a full re-read, because the one script anybody runs first scored it as work. When
  adding a state, grep every consumer before claiming the state does anything.

**And the re-read did produce one new fact, which is now in the register so it is not found a
third time.** `money-gaps.csv` said the gap closes on *"a better scan of this one page, or the
Treasurer's own FY2023 receipts file"*. A better scan is not a remedy that exists: of the two
publisher addresses on record, `DocumentCenter/View/4131` returns HTTP 404 and
`ArchiveCenter/ViewFile/Item/160` returns 18,274,143 bytes -- byte-for-byte the copy held
here. The town publishes one copy and we have it. **A gap whose named remedy cannot be
obtained is a gap with no remedy named**, and rule 7c's `— closes:` is worth exactly as much
as whether anybody checked that the document can still be got.

### 11. The RENDERER clipped the page, and the clip is invisible in a picture

FY2021 p40 is the trust and OPEB summary: ten money columns, and the last two --
`UNREALIZED GAIN/LOSS` and `ENDING MARKET VALUE` -- are the two every row identity on
the page closes into. `scripts/render_page.swift` wrote a **612x792** image of a page
whose mediaBox is **792x612**. The right 180 points went in the bin. Nothing said so.

**A clipped render does not look clipped.** It looks like a page with a wide margin, and
the margin is where the answer was. That is the same defect the top of this file records
costing 20% of every landscape document in FY2019 -- found there by `/Rotate` handling in
`ocr_pdf.swift`, and still live in the diagnostic script that step 3.4 of the process tells
every agent to run. The mechanism is the one `render_pdf_page.swift` documents in its own
header: PDFKit's `bounds(for:)` applies `/Rotate` and `draw(with:to:)` does not, so a tool
built on PDFKit can size a canvas for one page and draw a different one into it.
`render_pdf_page.swift` goes through `CGPDFPage` precisely so the two agree.

**What it cost here: nothing, by luck.** The previous agent had used
`render_pdf_page.swift` and read all ten columns; the clipped render was mine, and the two
disagreed in a way that was only noticeable because a *header* was missing rather than a
figure. Had it been the other way round, the page would have been transcribed eight columns
wide and the row identities -- which need all ten -- could not have been stated at all.

**Changed:** `render_page.swift` now prints the mediaBox and the page size it actually
drew, and says `*** CLIPPED OR REORIENTED` when they differ. It says "or reorientated"
because the script cannot tell which, and claiming a clip it has not established would be
the same error pointed at ourselves. Two of FY2021's pages trip it, 40 and 57.

**Not changed, deliberately:** the orientation logic itself. `upright()` scores four
rotations by how wide Vision thinks the text is, and rewriting it would change every
render in the archive on an afternoon's evidence. The warning makes the defect visible,
which is what was missing; the fix needs its own pass.

**Rule:** a renderer is an instrument and the picture is its reading, so it states the
geometry it assumed. **For a landscape page use `render_pdf_page.swift`.** And when a
table seems to have fewer columns than the handoff says, check the image against the
mediaBox before concluding anything about the document.

### 12. OUR OWN DOCUMENTS SENT AGENTS AFTER A GHOST, SIX TIMES IN TWO DAYS

Every one of these is a document written to PREVENT an error, carrying one. Each recorded
a symptom in the present tense and was never revisited when the symptom was fixed or
disproved.

| what we told an agent | what was true |
|---|---|
| rule 13c: FY2023's stabilization funds are on the NARROWER trust table | they are on the fourteen-column one at p51 |
| the plan: `Monty Tech $967,652.00` is printed on FY2016 p30 and absent from its OCR | it is the COUNTY RETIREMENT assessment, it IS in the text layer, and it is NOT printed on the page |
| the handoff: FY2012's grand total row `is not one`, at $1,032,000.00 | recognition noise in a `printed_total` cell, shifting the string one column; fixed in a correction row five days earlier |
| the handoff: FY2013 pp.67-68 and FY2012 pp.60-64's columns `cannot be established` | both print a clean six-column header at 518 dpi; the CACHE was degraded, not the document |
| CLAUDE.md: FY2011 p64 has `55 of 98 figures parse as nothing` | 8 of 126 on today's cache, six of them labels and the folio |
| our notes: FY2016 p49's title is `cut mid-word -- FY2016 COLLECTION OF TAXE` | the layer holds `SEXAT`, which un-mirrors to `TAXES`, with zero characters outside the page rectangle |

**THE SHAPE IS ALWAYS THE SAME: a statement about OUR INSTRUMENT, written down as a
statement about the TOWN.** Rule 13c says a matcher that finds nothing is a statement about
our instrument. These are that rule's output, promoted to prose and then quoted back as
evidence.

**And the sixth one exposed the deeper fault.** FY2016 pp.23 and 49 were called `clipped`
by an agent that had, four lines earlier in its own report, correctly recorded that both
pages are BORN-DIGITAL. A born-digital page has no scan to clip. The gate asked the right
question, got the right answer, and NOTHING SAID WHAT FOLLOWS FROM IT -- so the answer was
recorded and walked past, exactly as entry 7 describes. `READING-A-REPORT-PAGE.md` now
carries the consequence: a fixed list of scan words that cannot be used about a page whose
text layer we hold, and the two conclusions that remain available.

**Changed:** the consequence clause above. **And a rule for briefing:** before telling an
agent what is wrong with a year, `git log --oneline -- sources/data/table-corrections.csv`
and grep that file for the year. A finding already in the archive is a FINDING, NOT A TASK.
The plan's own defect table needs a `fixed in` column; until it has one, every row in it
reads as open.

**The cost, counted:** two agents re-derived `attested` findings already on record, one was
sent to re-render a page that was in the hard-block register, and one afternoon went on a
phantom page range. **What it buys:** the clause, and the habit of asking the data instead
of the write-up.

### What is now proven to work, end to end
An agent reads the page, writes a `read` or `attested` row into
`sources/data/table-corrections.csv` with its evidence, the extractor re-runs, the year's
arithmetic closes, and the pages move to PROVEN. FY2015 and FY2021 both closed this way
today. It parallelises: one agent per year, and they do not contend.
