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
Check the reader's input, not the output. `RP.load(edition, ocr=True)` means recognition.
Then check whether the page even needed it -- see the one-line test below. Seven times out
of seven today the answer was: digital page, recognised anyway.

**"What is left to make it FINISHED?"**
And finished means ONE thing: *the page leaves the unfinished count.* Not "the data is
right", not "I read it into a scratch file". If the answer has an intermediate state in
it, it is not an answer -- say which of the three steps below are outstanding.

Answer all four before writing any code. On FY2025 they took about a minute each and they
are what stopped four tables being rebuilt that did not need rebuilding.

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
