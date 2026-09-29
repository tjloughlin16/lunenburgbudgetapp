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

## STEP 0 OF STEP 0 -- OPEN THE RUN SHEET BEFORE YOU OPEN A PAGE

**`notes/process/runs/FY<YEAR>.md`. Create it, or append to it, as the FIRST action of the
year -- before the tracker is queried, before a PDF is opened.** Then work from it.

TJ, 29 September 2026: *"I want a process report when you run these. So the first step
should be to create or append to an existing doc with all the steps for the FY, and fill in
the status with a comment for each step. Always work from this so you don't fuck up again."*

**Why it is a FILE and not a habit.** FY2014 skipped step 1 of this document -- *do not
write the reading code again, `page_table.py` is it* -- three separate times, and nobody
noticed until TJ asked afterwards whether the process had been followed. Nothing was
concealed and nothing failed; the step simply was not in front of me, because I was working
from my memory of this document rather than from this document. That is rule 13's own trap
(*a summary in this conversation is not a source*) pointed at the process instead of the
data, and a checklist written before the work is the only thing that catches it.

**Every step is a ROW, at `todo`, before any page is read.** Pre-filled, all of them, for
every section of the year. A step that is not on the page gets skipped. `notes/process/runs/FY2022.md`
is the worked example: nine sections, eight steps each, seventy-two rows, written before
page one.

    | step                                          | status | comment |
    |-----------------------------------------------|--------|---------|
    | **extent** -- where does this table START and STOP  | DONE   | walked p22-p27; the table is p23-26, p27 is prose |
    | **holes** -- a page the tracker does not list       | DONE   | p25 absent and carries a full table |
    | **reader** -- own text or photograph, at what dpi   | DONE   | photographs, 150 dpi, legible |
    | **size** -- what it SHOULD hold, from the page      | DONE   | 60 rows, counted off the printed page |
    | **1 READ** -- `page_table.py`, layout DECLARED      | DONE   | PT.boxes + declare(); heading agreed |
    | **2 DURABLE** -- a row per figure in `page-reads/`  | DONE   | fy2022-p23-special-revenue.csv, 360 figures |
    | **3 VERDICT** -- verify, then re-map the tracker    | DONE   | 60 of 60 rows, all six columns tie |
    | **committed**                                      | DONE   | 9ecdae77 |

**A STATUS WITH NO COMMENT IS NOT A REPORT, and `DONE` with a figure in it is worth ten
without one.** `60 of 60 rows, all six columns tie` says the step happened. `read it` says
somebody typed a word. The comment is where a `blocked` earns its blocking and an `n/a`
earns its exemption.

**The sheet also carries what the year TAUGHT**, in a table at its foot, which is what gets
folded back into this document when the year closes. Not a diary -- a thing that cost real
time and the change that stops it costing again.

---

## START WITH THE YEAR, NOT THE PAGE

TJ, 28 September 2026: *"lets make this a system. maybe update the process to be full year
focused. answer the question `whats left for FYXYZ?` then work through that table section by
section until the FY is completed using the process."*

**Take one report. Build the table once. Then work the table.** Not page by page as the
tracker happens to list them -- the tracker lists PAGES and the work is in SECTIONS, and
every expensive mistake here has lived in that gap.

### 1. What is left, as sections

    python3 -c "
    import csv, collections
    rs=[r for r in csv.DictReader(open('sources/data/annual-report-pages.csv')) if r['fy']=='2023']
    print(collections.Counter(r['state'] for r in rs))
    for r in sorted(rs, key=lambda r: int(r['page'])):
        if r['state']!='proven':
            print(r['page'], r['state'], r['subject'], '|', (r['failed_by'] or r['refused_by'] or '-'), '|', r['heading'][:40])"

Then group the pages into sections BY HAND, and the grouping is the judgement the table
cannot make for you:

- **Adjacent pages are usually one table**, whatever subject each is labelled.
- **THE SUBJECT LABEL IS A GUESS FROM THE WORDS AT THE TOP OF THE PAGE**, so on a table that
  runs for several pages it is whatever line item happens to be printed first. FY2023 pages
  164 to 167 are labelled `trust-and-stabilization`, `payroll`, `payroll` and
  `regional-school`, from the headings `INFRA21-03`, `Reserve Fund`, `Police Lock Up` and
  `Traffic Signs & Devices`. They are four pages of ONE appropriations schedule.
- **What actually says two pages are the same table is that the same EXTRACTOR holds rows
  for both.** That is a fact about the archive; the heading is a guess about a page.

### 2. For each section, before reading anything

| | |
|---|---|
| **extent** | where does the table start and stop? Walk outward until it does. |
| **holes** | is there a page BETWEEN or BESIDE the run that the tracker does not list at all? |
| **reader** | per PAGE: does it carry its own text, or is it a photograph? |
| **held** | what does a dataset already hold, and what is its verdict? |
| **size** | what SHOULD the whole thing hold, from the page's shape rather than from our data? |

That last one is what actually catches a short read, and it is free. 47 printed rows in two
columns is 94 names a page; against that, `111 rows across four pages` for a wage list is
visibly wrong before a single page is rendered. Ask it before reading, not after.

**THE HOLES ARE THE ONE THE LIST CANNOT TELL YOU.** A page enters the tracker only when
recognition found fifteen money figures on it, so a page it failed on entirely is not
unfinished -- it is ABSENT. Five pages of FY2024's gross wages were invisible that way, each
with a full table on it. In FY2023 the same check flags pages 23, 26, 45, 47, 57, 163 and
168 as sitting beside a run and listed nowhere. Open each one. Most will be prose; the cost
of the one that is not is telling a resident the town does not publish something it does.

    python3 -c "
    import csv
    have={int(r['page']) for r in csv.DictReader(open('sources/data/annual-report-pages.csv')) if r['fy']=='2023'}
    print([p for p in range(LO,HI) if p not in have])"

### 3. Work the sections one at a time, all the way through

Each one goes through the whole of this document -- gate, read, durable, verdict -- and gets
committed before the next begins. **Do not read a page until the section's extent is
settled**, and do not start a second section while the first is half done.

**Order them by what will teach you the most, not by page number.** A section whose
extractor says `check failed` often means the reading is right and the DOCUMENT does not
foot -- FY2024's levy build-up was exactly that -- and those are quick. A section holding
`no check` needs the arithmetic found. A `refused` section usually means the extractor was
looking for a rule the page does not follow.

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

## A LANDSCAPE PAGE: ROTATE IT FIRST, THEN CROP ONCE YOU CAN SEE THE GRID

FY2024 page 37 is the debt repayment schedule -- about fifty debt issues against twenty-three
fiscal years, roughly 1,200 figures, printed sideways. It cost six wasted image reads before
anything was recorded, and every one of them was the same mistake: **aiming a crop at
coordinates I had guessed.**

**WHY THE GUESSING FAILS.** The renderer calibrates orientation per page and the recognition
TSV uses a bottom-left origin, so the two disagree about where anything is. A crop aimed from
one lands somewhere else in the other, and a blank crop looks exactly like an empty region of
the page. Worse, the OCR could not find the words `GRAND TOTAL` at all, so it could not even
be used to locate the block.

**THE ORDER THAT WORKS.**

1. **Rotate the page into its own one-page PDF**, so the table is the right way up and crop
   coordinates mean what they look like:

        python3 -c "import pypdf; r=pypdf.PdfReader(SRC); p=r.pages[N-1]; p.rotate(90); \
                    w=pypdf.PdfWriter(); w.add_page(p); w.write('/tmp/rot.pdf')"

2. **Render the WHOLE rotated page once, at a low scale, and look at it.** That read is not
   overhead -- it is how you learn where the header row, the label column and the total block
   actually are. Guessing costs more reads than looking.
3. **Then crop to bands you can now name**, at a high scale.

**WHY CROPPING IS NEEDED AT ALL.** The image is downsampled to a fixed budget of roughly
1546x2000 whatever scale it was rendered at, so what limits a read is PIXELS PER CELL. A
portrait page of sixty rows and one money column is comfortable in one read; a landscape
table of fifty rows and twenty-four money columns is not, and no render scale fixes that.
Cropping is how you spend the budget on fewer cells.

## A PAGE THAT PRINTS DISPLAYED FIGURES CANNOT TIE TO THE CENT

The debt schedule shows whole dollars over amounts that carry cents, so its printed total is
the ROUNDED SUM and not the sum of the rounded parts. Across twenty-three years the interest
column misses by $1 and principal-and-interest by $2.

**What makes that safe to accept rather than a misread:** the two columns with no cents under
them -- bond principal, and the MWPAT admin fees -- tie EXACTLY, principal at $33,256,561
across twenty-three values. That contrast is the evidence. It is not proof: the page does not
say it rounds, and a single wrong digit usually misses by more than a dollar but need not.

So a transcription may DECLARE a `tolerance` on its total row, and only with the reason
written beside it in `proof`. The default is a cent. Never widen one to make a read pass.

## READING PART OF A PAGE IS FINE. CALLING IT FINISHED IS NOT

Only page 37's GRAND TOTAL block was transcribed -- the town's debt service by year, which is
the series anybody would chart. The fifty per-issue rows were not, so a resident still cannot
see which bond ends in which year.

That limit is now a row in `sources/data/money-gaps.csv`, which is rule 7c: *when an analysis
stops short because the data will not carry it, that stopping point is a finding and it gets
REGISTERED*, not left in the prose of one page. Say it in the transcription's `proof` too, in
capitals, so the next reader of the file meets it.

**The failure to avoid is the quiet one:** a partial read that clears the tracker and leaves
nobody any way to know what is missing.

## SOME PAGES CANNOT BE READ AT ALL, AND THE DPI SAYS SO BEFORE YOU TRY

A photograph is stored at some resolution and no render scale adds detail that is not in
the file. Measure it first:

    python3 -c "
    import pdfplumber; d=pdfplumber.open(PDF)
    for p in PAGES:
        pg=d.pages[p-1]
        for im in pg.images:
            print(p, im['srcsize'], round(im['srcsize'][0]/pg.width*72), 'dpi')"

FY2023, the same report, page by page: 183 dpi on page 50 and 156 on page 53, both legible;
**93 dpi on page 25**, which packs about 150 line items across three column-pairs of a
LANDSCAPE page and cannot be read at any magnification -- `588` and `568`, `405` and `465`
are the same handful of pixels.

**It is dpi AND density, not dpi alone.** Page 24 is stored at 72 dpi and read perfectly:
portrait, one table, large type. What decides it is how many characters are crammed into the
pixels there are.

**WHEN A PAGE CANNOT BE READ, STOP. DO NOT LET THE ARITHMETIC PICK THE DIGIT.** The summary
block on page 25 reads to a total $20 from the printed GRAND TOTAL, which is exactly what one
misread digit looks like -- and choosing the digit that makes it close is fitting the answer
to the check. That is the compensating-error trap rule 14 describes, manufactured on purpose.

**MARK IT AND MOVE ON.** TJ, 28 September 2026, having opened the page himself: *"its too
blurry. we need to mark it as TOO BLURRY and call it HARD BLOCKED. and move on."*

`sources/data/page-blocked.csv` is the register, and `blocked` is a state of its own in the
page tracker, beside `proven`, `unproven` and `refused`.

**A page nobody has got to yet and a page nobody CAN get to are different facts**, and
leaving both in one bucket means the backlog never stops containing the second kind: every
pass rediscovers it, re-renders it, and re-concludes it. That is the cost this state removes.

Nothing infers a block. An extractor that cannot read a page says `refused`, which is a
statement about the EXTRACTOR; `blocked` is a statement about the DOCUMENT and a person has
to have looked. The row records what was tried, what the obstacle measures, and the one
thing that would remove it -- here, a better scan of the one page or the Treasurer's own
receipts file. Register the question in `money-gaps.csv` too, and go to the next section.

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

## A PAGE THAT PRINTS NO TOTAL IS CHECKED ON COVERAGE, AND THE CHECK IS DECLARED

The wage lists print no total anywhere, so there is no arithmetic to close. The page still
asserts things about its own shape, and the transcription DECLARES them in `kind=check` rows
that `verify_page_reads.py` asserts on every run:

    column `rows_per_page`   every page but the last carries exactly this many rows
    column `ordered_by`      the named column never goes backwards through the whole run

**Both, or neither is worth much.** The sequence catches a page or a block dropped and
cannot see a single name skipped; the count catches a skipped name and cannot see a dropped
page. FY2024: seven full pages at 94 rows, and `ABRAHAM` to `ZRATE` without going backwards
once in 675 rows.

**A coverage check is weaker than arithmetic and should say so.** It proves the shape, not
the figures: a misread digit survives both assertions untouched. Where a second printing of
the same quantity exists anywhere in the archive, reconcile to it instead.

## FY2022, AND THE FIVE THINGS THAT WENT INTO THE TOOL RATHER THAN BESIDE IT

FY2022 was taken to zero on 29 September 2026. It opened at 18 of 33 pages proven and closed
at **41 of 41** -- it GREW by eight pages, and every one of the eight was a hole the tracker
could not have named. Two of them, pages 46 and 48, carry the town's WHOLE forward debt
service, FY2023 to FY2047, and had never been read by anything.

**THE HOLES ARE THE WHOLE JOB, AND THEY ARE NOT WHERE YOU EXPECT.** The run sheet predicted
one, off FY2024's wage run, and it was right -- five of seven gross wage pages were missing.
It did not predict the other three, which were the grand-total pages of the debt schedule and
the HEADER PAGE of the omnibus budget. The pattern: **a page enters the tracker on fifteen
money figures, so the pages that carry a table's TOTALS and the page that carries its COLUMN
HEADINGS are the ones most likely to be invisible** -- five rows and a header are not fifteen
figures. Those are also the two pages a table cannot be proved without.

**A PAGE MARKED `proven` IS NOT A PAGE FULLY READ.** Page 42 was proven, by an extractor that
reads five of its 46 funds. Page 41 is `Page 1 of 2` of the same statement and prints no grand
total, so it could not be proved without 42. Walk the extent outward past `proven` pages too,
and look at what actually proved them.

Four changes went into `page_table.py` and `verify_page_reads.py`, and each was paid for:

**`rows()` now measures the ZERO-JITTER case.** A typeset page puts every token of a printed
row at exactly the same `top`, so the small population the ratio rule looks for is not small,
it is EMPTY -- the biggest ratio jump then lands between the section gap and the page gap.
On the omnibus budget that put the band at 46.8pt against a pitch of 14.76, which bands a
whole table into four rows and **looks like a page of headings rather than like a failure**.
The test is the ABSENCE of a small population, not the presence of ties: a first cut on ties
alone broke page 38 of the same report, which has 497 ties and a real 1.281pt jitter.

**`one(row, x_from)` is new: the single figure of a ONE-COLUMN table.** There is no ruler to
place against when there is one column, and the figures still arrive split -- `$ 1, 000.00`
is three tokens and `amount()` on each in turn returns None, None and 0.00. It also reads
`$ -` as the explicit zero FY2014 paid $16,687,431 to learn it is.

**`cells_per_row` is new in the verifier: what a GRID states when it states nothing else.**
The salary schedule prints 20 grades against `STEP 1` to `STEP 8` and no total anywhere, so
there is no arithmetic to close -- but the printed header says how wide every row is, and a
row that came out seven cells long is a figure lost.

**`ordered_by` was a check with no power to fail on any numeric key.** It stripped every
character but A-Z before comparing, so `GRADE 1` through `GRADE 20` all collapsed to the same
string and the sequence could not go backwards however the rows were ordered. It now compares
numbers as numbers.

### Three more things this year taught

**COMPUTE EVERY SUBTOTAL THE PAGE PRINTS, NOT ONLY THE GRAND TOTAL, AND DO IT BEFORE
WRITING.** The trust statement asserts five identities per fund and `change in unrealized
gain/loss` appears in none of them, so for that column the group subtotal is the ONLY check.
It failed twice, and both were real misreads. **A column that no row identity touches is
exactly where a read needs the subtotal.**

**TEST A REGULARITY BEFORE OFFERING IT AS A CHECK.** The salary schedule's steps sit about 3%
apart and it is tempting to use that as the arithmetic the page lacks. It does not hold --
`round(step_1 x 1.03^(n-1))` misses 50 of 140 cells -- and publishing it would have been a
hypothesis dressed as a proof. Where the test fails, the ABSENCE is the finding: register it.

**TWO COLUMNS ON A PAGE NEED NOT BE ONE LIST.** The gross wage pages print two columns and
each is alphabetised A to Z independently across all seven pages -- ABRAHAM to ZRATE on the
left, BIERY to YOURK on the right. Read left to right row by row they produce a list in no
order at all. Nothing in the document says what separates them, so they are transcribed as
two groups and NOT merged: merging them would be our claim and not the document's.

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

---

## A TOKEN IS NOT A CELL. FY2014, AND THE SIX WAYS ONE PAGE HID MONEY

FY2014 was the fourth year taken to zero and the first where nothing was a photograph.
Every page carried its own text, and the text layer still lost money six different ways.
Each one looked, at the moment it happened, like the town not printing something.

**1. A MIRRORED, VERTICAL TEXT LAYER.** pp.34, 37-38 and 40-41 come out backwards --
`SDNUF TCEJORP LATIPAC`. Reverse each word, flip x (`W - x1`), and the page TRANSPOSES: a
constant-y band is a table COLUMN and a constant-x run is a ROW. Nothing else about the
reading changes once that is done.

**2. TWO FIGURES IN ONE TOKEN.** `($7,367.79)$2,503,900.36` is one word spanning two
columns. Split it into its money substrings and assign them to the bands the token's own
vertical extent covers.

**3. A NAME PRINTED OVER A FIGURE.** The zoning stabilization row holds
`)0H9T.1R2O8N,6K2N2$AB` -- letters and digits interleaved, character by character. Partition
into alphabetic and non-alphabetic: `BANKNORTH` and `$226,821.90`. **That is a hypothesis
until the arithmetic takes it**, and here it did, to the cent, against the printed grand
total -- then the figure was read off the rendered page as well.

**4. THE FIGURE COLUMN SAT ONE ROW OFF ITS LABELS.** On p42 every figure belongs to the
label one row pitch (11.2pt) ABOVE it. **Do not settle that by eye.** At +11.2 the TOTAL
column reproduces the sum of the two preceding pages for 37 of 41 rows; at 0 or -11.2 almost
nothing ties. An independent total is what decides an alignment, never the look of it.

**5. THE COLUMN RULER CHANGES BETWEEN PAGES OF ONE TABLE.** The omnibus budget puts its
amounts at x=405, then 256, then 291. Measure the ruler on every page off that page's own
`$` glyphs. Read with the previous page's ruler, p141 swept every figure into the account
name and looked like a page of headings.

**6. `$ -` IS AN EXPLICIT ZERO, AND A TOTAL ROW NEED NOT BE LABELLED.** Reading the dash as
a missing figure turned a line into a section heading and dropped $16,687,431 out of Total
Schools. And Health & Sanitation is closed by a row with a `$`, a figure, and no words at
all -- so a reader that skips nameless rows loses the only place that section's total is
stated. A row with no `$` anywhere is a heading; a row with a `$` always carries a figure,
even when the figure is nil.

### AND ABSENT IS NOT ZERO, IN THE CHECKER AS WELL AS THE READER

`verify_page_reads.py` was scoring an identity with `cells.get(col, 0.0)`, so a row that
prints its components and NO total read as `a + b = 0` and was reported as the town's
arithmetic failing. Four FY2014 debt rows were named that way and all four were the document
simply leaving the group total blank.

Rows that do not print the whole are now **counted and named separately** -- not passed, not
failed. Which immediately paid for itself elsewhere: FY2014's appropriations had been
reporting `81 of 81 rows close` while five of those rows printed no balance at all and were
passing on `0 = 0`. A check with no power to fail, in the exact shape rule 13 describes.

### THE ARITHMETIC IS WHAT MAKES ANY OF THIS SAFE

Six unusual decodings went into FY2014 and not one of them is asserted. The trust pages foot
on two identities across 45 funds, six group subtotals and two grand totals in nine columns;
the debt schedule closes on 156 of 156 checkable cells and sums to its printed grand total to
the DOLLAR in both principal and interest; the omnibus budget's line items foot ten of eleven
section totals exactly. **A wrong un-mirroring, a wrong split or a wrong row offset cannot
make real arithmetic close.** Where it did not close, the gap was the document's -- and four
FY2014 defects are now in `document-defects.csv` saying which figures disagree and that which
one is wrong is not established.
