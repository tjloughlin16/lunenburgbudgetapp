# Reading a page out of an annual town report

**28 September 2026.** Every page in this archive is one of two things, and which one
decides everything that follows. Ask first, in one command, per PAGE:

    python3 -c "import pdfplumber; print(len(pdfplumber.open(PDF).pages[N].extract_words()))"

Under ~40 words is a photograph. Three hundred is a page whose characters are IN THE FILE.

| the page carries its own text | **the gate**: read it, discard the OCR |
|---|---|
| **the page is a photograph** | **the other half of the gate**: count what you hold against what it prints, and LOOK at it |

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
Check the reader's INPUT, not its output. `RP.load(edition, ocr=True)`, or a path under
`sources/town-budget/ocr/`, means recognition. Then check whether the page even needed it
-- the one-line test is below. Seven times out of seven today the answer was: digital page,
recognised anyway. If the answer is yes and the page is digital, STOP and read the gate.

**"What is left to do to MOVE IT TO FINISHED?"**
And finished means ONE thing: *the page leaves the unfinished count.* Not "the data is
right", not "I read it into a scratch file". If the answer has an intermediate state in
it, it is not an answer -- say which of the three steps below are outstanding.

Answer all four before writing any code. On FY2025 they took about a minute each and they
are what stopped four tables being rebuilt that did not need rebuilding.

## THE GATE -- A TEXT LAYER OUTRANKS OCR. ALWAYS. THROW THE OCR AWAY

TJ, 28 September 2026: *"this process needs to throw out OCR data if we have a digital text
layer for the data. its more reliable. OCR is a fallback."*

**The one-line test, before anything else:**

    python3 -c "import pdfplumber,sys; d=pdfplumber.open(sys.argv[1]); print(len(d.pages[int(sys.argv[2])-1].extract_words()))" <pdf> <page>

More than a handful of words means the page carries its own text. From that moment the OCR
reading of that page is not a second opinion, it is **superseded**, and the work is to
REPLACE it -- not to reconcile the two, not to fill the text layer's gaps from it, and above
all not to diagnose the OCR read's disagreements as findings about the town.

**Why it is not a judgement call.** This is rule 13 in the archive's own terms: *quote the
source, never your rendering of it.* OCR output IS a rendering -- a model's guess at what
ink was on a page. The text layer is the bytes the publisher embedded. They are not two
readings of one document; one is the document and the other is a photograph of it. Where
they disagree the text layer is right, and there is nothing to weigh.

**And OCR fails QUIETLY, which is what makes an existing OCR read so dangerous.** It does
not refuse a page, it returns a shorter one. FY2025 p31 prints 32 trust accounts and the
OCR-derived CSV holds 30 -- `8116 School Prize Fund` and `8140 Health Insurance
Stabilization` simply absent, with nothing anywhere saying a row was lost. A missing row
looks exactly like a fund the town does not have (rule 13c), and three rows in that same
read disagreed with the ledger and were about to be written up as a reconciliation problem
in the town's books. They were a reading problem in ours.

**So the order is fixed, and the first question is not "is there OCR on disk":**

| | |
|---|---|
| the page has a text layer | read it. Delete the OCR path for that page. |
| the page has none | OCR, and say so in the extractor. |
| we are unsure | run the one-line test. It costs a second. |

**Doing this leaves the extractor with two readers, and that is fine** -- what is not fine
is leaving the choice to whichever ran first or to which cache happened to be warm. Pick on
the DOCUMENT: a `TEXT_LAYER` set naming the editions and pages that carry one, consulted
before the OCR branch, exactly as `extract_gross_wages.py` and `extract_special_revenue.py`
now do. Eight of the sixteen annual reports are born-digital -- FY2014, FY2015, FY2016,
FY2017, FY2018, FY2020, FY2024, FY2025 -- so this is half the archive, not an edge case.

**Re-check every verdict that rested on an OCR read of a digital page.** A check that passed
on a short read passed on less than the page, and a check that failed may have been failing
on ink, not on arithmetic.

## THE OTHER HALF OF THE GATE -- IF THERE IS NO TEXT LAYER, LOOK AT THE PAGE

TJ, 28 September 2026: *"for non digital text data, even with OCR data, the agent should
review the pages directly to see if there is anything to learn about the page, to match it
to what is found on the OCR data. using pure OCR data is not working when there are
mismatches."*

The first half of the gate says a text layer supersedes OCR. This is what to do when there
is no text layer, and it is not *trust the OCR*. **Recognition is a reading, and a reading
gets checked against the page.**

**WHAT HAPPENED, BECAUSE IT IS THE WHOLE ARGUMENT.** FY2024 pages 23-26, the special revenue
listing. Placing figures by column instead of by order made four of five columns tie to the
town's own printed totals to the penny. The fifth was short by $15,101.86, and three
explanations were offered for it before anybody opened the page: that blank cells were
shifting the columns, that the scan had been rendered too small and figures destroyed, that
the town's own total might not foot. All three were wrong.

The page is clean, printed and completely legible. **It prints 60 fund rows and our OCR held
figures for 14.** Re-running recognition at six resolutions never got close, and worse, the
scales disagreed with each other on the DIGITS -- `90.61` at one scale and `0.61` at
another, `94.65` and `4.65`, `214.00` and `211.00` -- so there was no majority to take and
merging the passes could not help. Read off the render by eye, the 60 rows summed to
$46,940.59 and the section landed on $4,963,068.15 exactly, which is a total the town
printed and nothing here had ever used.

**Two steps, and the first is free.**

### 1. COUNT THE ROWS THE PAGE PRINTS AGAINST THE ROWS YOU HOLD

Mechanical, instant, and it would have caught this before any of the three wrong
explanations. Count something the page has one of per row that OCR reads reliably -- here
the four-digit fund number, which came through perfectly on every row -- and compare it to
how many rows carry a figure.

    fund rows printed on pages 23-26 ......... 185
    rows carrying a figure ................... 140

A gap is not proof of a defect; 15 of page 25's rows print a DASH rather than a zero, and a
closed grant with nothing in it is a real row with no figure. But a gap is the alarm, and
an alarm is what was missing. Any extractor reading a scan should publish this ratio beside
its output, the way `search_minutes.py` prints its denominator on every run and for the same
reason: **a reader who is told nothing assumes nothing was lost.**

### 2. RENDER THE PAGE AND READ IT

    swift scripts/render_page.swift <pdf> <page> /tmp/p.png 4

`render_page.swift` says in its own header that it exists *"for reading with human or model
eyes"*, and this is the case it was written for. Read the page, and compare it to what the
extract holds -- not the other way round. The question is never *does the OCR look
plausible*, it is *what does the page say, and did we get it*.

**Where the two disagree, the page wins and the OCR is discarded for that page** -- the same
rule as the text-layer gate, for the same reason. What comes out is a TRANSCRIPTION, and it
is stored as data with its provenance, never typed into code: which document, which page,
who read it. The transcription is then a source like any other and the extractor consumes
it.

**AND THE TOTAL IS WHAT MAKES IT SAFE, NOT THE READER.** A model read and a machine read are
both readings; one of them can see the page and neither is trustworthy on its own. What
settles it is the arithmetic the page states about itself -- 60 rows landing on a printed
$4,963,068.15 cannot be luck, and a single wrong digit anywhere breaks it. So:

- **Where the page prints a total, read it and prove it.** That is a complete answer.
- **Where it prints none**, a read by eye is a HAND-BUILT figure in rule 13a's sense --
  an argument somebody assembled -- and it is worth exactly as much as the care taken. Say
  so, and look for a second printing of the same quantity elsewhere in the document before
  publishing it as established.

**DO IT IN ISOLATION, NEVER IN A LONG SESSION (rule 7g).** Reading a page has no dependency
on a conversation's history: it takes a page and a rule and produces rows. Every turn
re-sends the whole conversation, so the same read costs several times more at turn 200 than
at turn 3. It belongs in `claude -p`, the way `write_recording_minutes.py` and
`extract_official_votes.py` already work. The test is the one rule 7g gives: *could this run
with none of this conversation in front of it?* For a page read the answer is always yes.

**What this is NOT.** It is not a licence to transcribe instead of extracting. An extractor
that reads a page is reproducible and a transcription is not -- run twice, recognition gives
the same answer and a reader may not. That is why the transcription becomes the durable
artefact and the arithmetic re-proves it on every run: the reading happens once, the check
happens every time. Reach for it when the count is short and recognition cannot be made to
close, not before.


## THE PROCESS -- three steps, in this order

### 1. READ the text layer into the CSV
`pdfplumber.extract_words()` gives every word with `x0` and `top`. Band by `top` into
printed lines, then split each line into columns by `x0`. Two things bite every time:

- **A figure arrives SPLIT.** `2@351 | 22,940.64@355` is one cell, 222,940.64. Join the
  fragments inside a column; never take them as separate values.
- **A dash glues itself to its neighbour.** A `-` placeholder at x=463 concatenated onto
  the column at 398-455 makes `1,072,661.74-`, which parses as nothing -- so the column
  silently vanishes. Drop `-` and `$` tokens before joining.

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
