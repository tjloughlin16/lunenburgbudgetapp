# Reading a page out of an annual town report

**28 September 2026.** Every page in this archive is one of two things, and which one
decides everything that follows. Ask first, in one command, per PAGE:

    python3 -c "import pdfplumber; print(len(pdfplumber.open(PDF).pages[N].extract_words()))"

Under ~40 words is a photograph. Three hundred is a page whose characters are IN THE FILE.

| the page carries its own text | read it with `pdfplumber`, and discard any recognition of it |
|---|---|
| **the page is a photograph** | **render it and READ it** -- never recognition. Count what it prints against what you hold. |

**IT IS A PROPERTY OF THE PAGE, NOT OF THE REPORT.** This file used to open with a table of
eight digital reports against eight scanned ones, and that table was used to choose a year's
work and chose wrong. FY2024 carries its own text on page 53 and is a photograph on the ten
other pages that are unfinished; FY2020, FY2022 and FY2023 are mixed the same way. A report
can be typeset for most of its length and paste in a photographed section, which is exactly
what the Treasurer's and payroll sections are in several years. The counts live in
`notes/generated/TEXT-LAYER-COVERAGE.md`, which is GENERATED, because a figure typed into
prose is the one thing here that can be silently wrong.

**And the screen is not a proof.** A page can pass the word count and still hold its TABLE as
an image -- FY2025 page 115 does, and it is the only reason that chart got read. Apply the
test to the REGION the figures are in, not only to the page.

## What it cost to not ask

- FY2025 gross wages: 532 names read, **612 printed**. 80 people and $3,728,578 missing --
  not lost, unrecognised. Pages 177-179 read well and 180-182 did not, and the six are
  identical in form.
- FY2025 special revenue: the first row came out `fund: 'as'`, sliced out of the page's own
  heading `as of June 30, 2025`.
- Days spent hunting figures that were never lost.

## STEP 0 -- ASK WHAT WE ALREADY HAVE, BEFORE TOUCHING ANYTHING

TJ, 28 September 2026: *"the process needs to start with my questions too."* These are his,
in his order, and every one of them changed what the work turned out to be:

**"What format do we have the data currently in?"**
Name the actual file and show a row. `sources/data/<x>.csv`, its columns, three real rows.
Half the answers to "what is left to do" turn out to be "it is already there".

**"Is it in a CSV already?"**
FY2025 gross wages was -- 532 rows. That sounds finished and was not: the page prints 612.
*Having rows is not having the data.* Count what the page holds and compare.

**"Was this OCR'd too?"**
Check the reader's INPUT, not its output. A path under `sources/town-budget/ocr/`, or
`RP.load(edition, ocr=True)`, means recognition -- and recognition is no longer a reader
here. **If the answer is yes, the existing rows are not a starting point. Throw them away
and read the page.** Seven times out of seven on one day the answer was yes, and every one
of those readings was short.

**"What is left to do to MOVE IT TO FINISHED?"**
And finished means ONE thing: *the page leaves the unfinished count.* Not "the data is
right", not "I read it into a scratch file". If the answer has an intermediate state in
it, it is not an answer -- say which of the three steps below are outstanding.

Answer all four before writing any code. On FY2025 they took about a minute each and they
are what stopped four tables being rebuilt that did not need rebuilding.

## THE GATE -- TWO KINDS OF PAGE, TWO READERS, AND NEITHER IS OCR

TJ, 28 September 2026: *"i'm 100% done with OCR. that's totally a waste of my time and
credits"* and *"you spend more time in model costs rebuilding and rebuilding and rebuilding
off of broken ocr."*

| the page carries its own text | `pdfplumber.extract_words()`. Exact, free, reproducible. |
|---|---|
| **the page is a photograph** | **RENDER IT AND READ IT.** Not recognition. |

**DO NOT RUN OCR ON A TABLE IN THIS ARCHIVE.** Not as a first pass, not as a cross-check,
not as a fallback. If a recognition cache already exists for a page, it is not evidence and
it is not a starting point -- discard it.

## WHY, MEASURED, ON ONE DAY

Two tables, both of which had been read by recognition and were sitting in the archive as
done.

**The trust fund listing, FY2025 pages 30-31.** Recognition held 30 accounts; the page
prints 40. Two of the missing ones -- `8116 School Prize Fund` and `8140 Health Insurance
Stabilization` -- were simply absent, and three of the surviving rows were about to be
written up as a disagreement between two town documents. Read off the text layer: 40 of 40,
and 36 tie to the general ledger to the cent.

**The special revenue schedule, FY2024 pages 23-26, 164 fund rows.**

    recognition   14 of 60 rows on page 25 -- and re-running at six resolutions returned
                  DIFFERENT DIGITS for the same row: 90.61 and 0.61, 94.65 and 4.65,
                  214.00 and 211.00. There was no majority to take, so merging the passes
                  could not help either. Lower resolution was better than higher. An
                  afternoon went into machinery built around that failure, and three wrong
                  explanations were offered for the gap it left -- shifted columns, a scan
                  rendered too small, the town's own total not footing. All three wrong.

    read          164 of 164 rows, and ALL SIX columns tie to the totals the page prints,
                  first attempt, in about ten minutes.

The pages are clean, printed and completely legible. Recognition simply cannot read them,
and every hour spent making an extractor robust to that is an hour spent on the instrument
rather than the archive.

## HOW TO READ A PHOTOGRAPHED PAGE

    swift scripts/render_page.swift <pdf> <page> /tmp/p.png 4

Then read it, and write the rows down. `render_page.swift` says in its own header that it
exists *"for reading with human or model eyes"*; this is the case it was written for.

**The transcription is a SOURCE, not code.** It goes in `sources/data/page-reads/` with the
document, the page, the column, who read it and what proves it. Never typed into an
extractor.

**WHAT MAKES A READ SAFE IS THE ARITHMETIC, NOT THE READER.** A person or a model reading a
page is a reading like any other, and rule 13a is explicit that something a person assembled
is an argument rather than a record. What settles it is that 164 rows land on six totals the
town printed and we had never used: `83.86 / 83.86 / 4,963,068.15 / 116,241.96 / 0.00 /
(719,886.84)`. One wrong digit anywhere breaks all six.

`scripts/verify_page_reads.py` re-proves every transcription on every run, which is the one
property recognition had and a read does not: **the reading happens once, the check happens
for ever.**

**A page that prints no total cannot be checked this way.** That is a property of the PAGE,
not of the reader -- recognition had exactly the same limit. Such a page needs a coverage
check (every figure printed is captured, counted against the rows the page prints) or a
second printing of the same quantity elsewhere in the document. Say which, in the
transcription's `proof` column, and never let it pass as established without one.

**DO IT IN ISOLATION (rule 7g).** Reading a page has no dependency on a conversation: it
takes a page and a rule and produces rows. Every turn re-sends the whole conversation, so the
same read costs several times more at turn 200 than at turn 3. One `claude -p` job per page,
the way `write_recording_minutes.py` and `extract_official_votes.py` already work.

## COUNT WHAT THE PAGE PRINTS AGAINST WHAT YOU HOLD

Free, instant, and it is the alarm that was missing all along. Count something the page has
exactly one of per row -- a fund number, an account code, a line number -- and compare it to
how many rows carry a figure.

    fund rows printed on FY2024 pages 23-26 ......... 185
    rows recognition held a figure for ............. 140

A gap is not proof of a defect: 15 of page 25's rows print a DASH rather than a zero, and a
closed grant is a real row with no figure. But nothing compared those two numbers, and that
is why 46 missing rows looked exactly like 46 funds the town does not have (rule 13c).
`page_table.coverage()` computes it; publish it beside any extract, the way
`search_minutes.py` prints its denominator on every run and for the same reason: **a reader
who is told nothing assumes nothing was lost.**

## THE PROCESS -- three steps, in this order

### 1. READ the page into a CSV -- with `page_table.py`, not by hand

**Do not write the reading code again.** `scripts/page_table.py` is it. Four extractors were
written against this archive on one afternoon; the three built on word boxes took about
twenty minutes each and closed on the page's own arithmetic, and the one that re-derived the
reading from a page flattened to text lines took the whole day and was abandoned. The
difference was never the table -- the trust matrix prints its fund names SIDEWAYS and closed
first time. See `notes/process/AN-EXTRACTOR.md`.

    import page_table as PT

    LAYOUT = {'project_cost': (395, 470, 'Project Cost'),      # x from, x to, what it SAYS
              'cumulative':   (470, 540, 'Cumulative Cost')}
    BAND, BODY = (290, 315), (315, 760)                        # the heading, then the table

    ws   = PT.words(pdf, page)            # or PT.boxes(tsv, page) for a photograph
    cols = PT.declare(ws, BAND, LAYOUT)   # refuses if the page's heading disagrees
    run  = 0
    for r in PT.rows(ws, within=BODY):    # banded on the page's MEASURED gap
        cell = PT.place(r, cols)          # each figure under the column it is printed in
        ...
    PT.check('FY2025 Option 1', ('the projects against the printed Total', run, total))

Measured on FY2025's two capital plans: `p138  20 projects  1,225,000  breaks 0` and
`p139  16 projects  1,225,000  breaks 0`, in twenty-five lines, the same figures the
hand-written extractor produces.

**DECLARE THE LAYOUT. DO NOT INFER IT.** This is rule 13b's fourth rule and it is the one I
keep trying to automate. It cannot be done: `Project Cost` sits at x=404 and `Cumulative
Cost` at x=480, so the gap between `Cost` and `Cumulative` is SMALLER than the gap between
`Project` and `Cost`, and no clustering rule separates them. A person reading the page
separates them instantly. So a person reads the page, writes the layout down, and
`declare()` refuses any page whose printed heading disagrees with it -- which is what makes
one year's layout safe to try on another. FY2014's nine columns were proposed for four other
years; two accepted them and two refused, and the two that refused were right to.

**Four things bite every time, and `page_table` handles three of them.**

- **A bare integer is not money.** `1`, `2`, `13` are CPC rankings, warrant line numbers, the
  page number at the foot. Read as figures they land in whatever column they are nearest and
  join the sums: one capital page came out $50,000 high and the other $2, and the $2 was
  `Option 2` in the heading. A figure must carry a currency sign, a thousands separator or
  cents.
- **A thousands group is three digits.** `[\d,]+` accepts `3,` and `2,025`, so `May 3, 2025`
  in the prose under a table yields two figures.
- **A page is not a table.** Bound the body. FY2025 page 138 carries two tables and page 139
  carries a table and then the vote that adopted it, `$1,225,000` and all.
- **A figure arrives SPLIT, and a dash glues itself to its neighbour.** `2@351 |
  22,940.64@355` is one cell, 222,940.64; a `-` placeholder at x=463 concatenated onto the
  column at 398-455 makes `1,072,661.74-`, which parses as nothing, so the column silently
  vanishes. This one is still the caller's to handle -- join fragments inside a column, and
  drop `-` and `$` before joining.

**And x does not always mean a column.** On a TABLE it does. On a BAR CHART x is the VALUE --
a label sits at the end of its segment -- so there the ORDER is the series and a row without
one figure per series is refused. `PT.place` is for tables; `PT.series` is for charts.

### 2. Make it DURABLE
A reading done in a shell is gone on the next run, and the next run will overwrite it with
the OCR. The text-layer path belongs IN the extractor, keyed by (dataset, edition), and it
must REPLACE the OCR reading of those pages rather than adding to it -- two readings of one
page are not more data.

`TEXT_LAYER_RUNS` in `extract_tables.py` is the worked example: document, pages, the
COLUMNS read off the printed header with their x ranges, and the pattern of the row the
table foots to.

**The column names are the part a machine cannot supply.** A text layer gives exact
characters and exact positions; it does not say what the columns MEAN. Writing them down is
what turns `v1` from "the first column of that page that held figures" into `fund balance`.

### 3. Record the VERDICT, and register it
A page is finished when something records that its figures were checked AND the map knows
where to look.

- Find the identity the table states about itself. **It is not always called `Total`** --
  the special revenue table foots to a row labelled `FUND BALANCE`, and searching for
  `total|grand` found nothing and concluded there was none. That is rule 13c again.
- Where a table genuinely prints no total -- a wage list does not -- the identity is
  COVERAGE: every money figure printed on the page is captured. It can fail: under OCR,
  FY2025's wage pages covered 87 of 104, 54 of 104 and 89 of 102.
- Write the verdict into a column on the rows, and make sure `PROOF` in
  `map_annual_report_pages.py` names that column for that dataset. A verdict nothing reads
  is not a verdict -- three datasets today were registered `(None, NOTHING)` while their
  own code refused to write a year that did not tie.

## What "done" means

The page leaves the unfinished count. Not "the data is right" -- that is step 1 of three.

## Measured, FY2025

| pages | table | result |
|---|---|---|
| 177-182 | gross wages | 532 -> 612 rows, coverage 100% on every page |
| 25 | balance sheet | verifier 20 failures -> 0 |
| 26-29 | special revenue | ties to a printed total in all 3 columns |
| 30 | capital projects | 15 rows sum to the printed 3,096,913.16 |

About four minutes a table.
