# Reading a page the town published DIGITALLY

**28 September 2026.** Eight of the sixteen annual town reports are BORN DIGITAL and this
pipeline was running character recognition over every one of them.

| | |
|---|---|
| **digital** | FY2014 FY2015 FY2016 FY2017 FY2018 FY2020 FY2024 FY2025 |
| **scanned** | FY2011 FY2012 FY2013 FY2019 FY2021 FY2022 FY2023 FY2016-addendum |

One command answers which, and nobody had run it:

    python3 -c "import pdfplumber; print(len(pdfplumber.open(PDF).pages[N].extract_words()))"

Under ~40 words is a scan. Three hundred is a page whose characters are IN THE FILE.

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
