# The town's other document store, and three filters that hid it

**Found 4 September 2026.** The town runs **two** document stores and this project had only
ever walked one. It also publishes fifteen years of annual town reports that the archive
held none of, and the reason in every case was the same: **a filter found nothing and said
nothing, and nothing read as absence.**

**Nothing in this file is a source.** Check anything load-bearing against the repo.

---

## What was missing

### 1. `/ArchiveCenter/` — a second store, never touched

`fetch_town_docs.py` discovered documents by matching `/DocumentCenter/View/<id>`. CivicPlus
runs a second store at `/ArchiveCenter/ViewFile/Item/<id>`, indexed at `/Archive.aspx`, and
**no URL in it matches that pattern.** Twelve categories:

| category | what it holds |
|---|---|
| Annual Town Reports | FY11–FY25, fifteen years |
| Town Meeting & Budget Documents | **one category per year, FY12 through FY25** |
| Town Meeting Booklets | 2015–2024 |
| State and National Elections · Town Election Results | results |

Item 188, which surfaced this, is the **FY2024 Preliminary Budget, Town Manager
Recommendation**, 16 February 2023, 38 pages — revenue, levy and free cash detail. Named
items in other categories include a *revenue-expense sheet*, a *line item budget*, and a
*ten-year capital plan by funding source*.

`grep` across `notes/`, `plans/`, `scripts/`, `CLAUDE.md` and **every commit on every
branch** returns nothing before today. Wherever this was first noticed, it was never
written down.

**And link-walking could never have found it.** `/Archive.aspx` renders its categories and
items in javascript: the HTML a fetcher receives contains *no archive links at all* — one
stylesheet reference and nothing else. The ids are in the markup even though the links are
not, which is what makes it reachable:

    <label for="amidDDN52">Annual Town Reports:</label>          AMID 52 — the category
    <a href="Archive.aspx?ADID=201"><span>FY24-FY33: …</span></a>  ADID 201 — an item

So `discover_archive()` reads the categories off the index, asks each category page for its
items, and takes the file from `/ArchiveCenter/ViewFile/Item/<ADID>` — the address a
resident would use. Twelve categories, 124 items:

| AMID | items | category |
|---:|---:|---|
| 52 | 15 | Annual Town Reports |
| 51 | 10 | FY12–FY18 Town Meeting and Budget Documents |
| 38 · 45 · 44 · 43 · 42 | 4 · 9 · 9 · 4 · 4 | FY19 · FY20 · FY21 · FY22 · FY23 |
| 50 | 28 | FY24 Town Meeting and Budget Documents |
| 53 | 13 | FY25 Town Meeting and Budget Documents |
| 40 | 20 | Town Meeting Booklets, 2015–2024 |
| 57 · 37 | 4 · 4 | Elections |

Also missed and now seeded: **`/287/Town-Manager-Reports`**.

### The same document at two addresses

The town publishes the annual town reports in **both** stores and does not title them
alike — DocumentCenter says `FY 2025 Annual Town Report`, the ArchiveCenter says
`FY25 Annual Town Report (PDF)`. Slugging alone leaves those as two documents, and a naive
run re-downloads 487MB it already holds and stores every report twice under two ids.

`dedupe_key()` normalises the year to four digits and drops the format suffix. **18 items
matched.** The duplicate is not discarded: a document with two addresses is one document,
and rule 12 wants both kept — when one link dies the other may not have. So the second
address is recorded in `upstream` against the copy we keep.

### 2. The annual town reports were filtered out twice

First because no seed page linked them. Then, after `/838/Annual-Town-Reports` was added as
a seed, **because the `WANTED` pattern `fy\d\d` does not match `FY 2025`** — there is a
space. Sixteen documents, rejected by a pattern written to catch them.

### 3. And the fetcher never said so

It prints what it retrieved. It does not print how many links it saw, how many the filter
rejected, or a sample of the rejects. `search_minutes.py` prints its denominator on every
run precisely because a search that finds nothing prints nothing — the fetcher has the same
failure and none of the defence.

**The fix is the same as it was there: print the denominator.** Links seen, links rejected,
and enough of the rejects to notice sixteen annual town reports going past. It now says:

    744 document links seen · 206 kept · 347 rejected by the WANTED filter
      a sample of what was rejected — read it, that is the point:

The kept count went from **90 to 206** the moment the second store was reachable.

---

## What the annual reports actually contain

From the FY2012 table of contents and the FY2025 body. This is more than was being asked
for anywhere.

| section | what it gives | what the archive holds today |
|---|---|---|
| **Receipts** | revenue by source, line by line | FY2026 only |
| **Accounts, Summary** | appropriations by department | FY2026 only |
| **Special Revenue Funds** | every school Fund by name — Title I #305, PL 94-142 #240, Chapter 658 athletics, After School, School Facilities Use, Non-Resident Tuition, Adult Education, School Lunch | FY2026 Q3 only |
| **Balance Sheet · Bonded Indebtedness · Trust Funds** | — | nothing |
| **Payroll Report** | — | nothing |
| **Town Meeting Minutes** | the votes themselves | partial |
| **School Reports** | **per-school staff rosters**, every position named | nothing — but present in 10 years of reports |

**Fifteen years of it.** `fund_activity` currently holds one year; this would make it a
series, which is the difference between *"fund 2813 spent $229,398"* and knowing whether
that is normal.

### The staff roster, and a line in CLAUDE.md that is wrong

**It is not one year. It is ten.** The survey finds `STAFF ROSTER` in every report that has
a readable text layer -- FY2014, FY2015, FY2016, FY2017, FY2018, FY2020, FY2022, FY2023,
FY2024 and FY2025 -- on 24 pages in total, and the remaining years are pure scans that have
not been OCR'd yet rather than years that lack one.

| FY | pages |
|---|---|
| 2014 | 102, 109 |
| 2015 | 107, 114 |
| 2016 | 110, 113, 116 |
| 2017 | 108, 112, 115, 119 |
| 2018 | 121, 124, 128, 132 |
| 2020 | 123 |
| 2022 | 117 |
| 2023 | 126, 138 |
| 2024 | 104, 105 |
| 2025 | 100, 102, 105, 109 |

They carry names *and roles*. FY2018 page 121, `Staff Roster 2018-2019`, plain text layer,
no OCR needed:

    Steve McKenna, Principal            2A-Vickie Barbier
    Chad Adams-Asst. Principal          Ellie Lorigan - Para
    Denise Galloway-Admin Secty         2B-Jackie Favreau
    Lisa Lavery-School Nurse            Amy Cowley - Para
    Karyn Savell - Guidance Counselor   2C-Sara Kenney

FY2025 pages 100 and 102 carry **LUNENBURG PRIMARY SCHOOL STAFF ROSTER** and **THES STAFF
ROSTER**. Roughly 41 `Para` mentions across pages 100, 103 and 110.

`CLAUDE.md` says, under the standing questions:

> Whether budgeted positions were **filled**. A budget line is an intention.
> …for people it is a headcount nobody publishes.

**The town publishes a headcount**, by school, by position, on its own website, and has done
for at least a decade. The sentence should be corrected rather than quietly dropped — and it lands on the load-bearing question,
because the in-district special education escalator rests on a paraprofessional line that
cannot currently be told apart from grant money unwinding.

**What it does not give**, and this matters before anybody calls it an answer:

- **No FTE.** A 0.4 music teacher and a full-timer look identical on a roster.
- **No funding source.** It does not say which Fund pays a person, which is the actual
  question.
- **A point in time**, undated within the year.
- **Partial in most years** — the number of roster pages moves between one and four, and a
  year with one page is not a year with one school. FY2020 and FY2022 show a single page
  each; nothing establishes whether the other schools stopped being printed or are on a
  page the heading regex does not match.
- **A name on a page is not a filled position.** Counting rows gives a count of names the
  town printed, which is a proxy. Rule 7: dollars are not students, and names are not FTE.

So it **bounds** the question. It does not settle it, and rule 7 applies: a roster is not a
staffing level, and a name is not a full-time equivalent.

---

## How the reports get read

**All sixteen annual reports are downloaded.** Reading them is a separate problem, and it
turned out to have a different answer than expected. `scripts/pdf_tables.py` is the
result; what follows is why it is shaped the way it is, because every rule in it was put
there by a document that broke the previous one.

### The reports are not scanned or digital. Each one is both

Six reports -- FY2011, FY2012, FY2013, the FY2016 addendum, FY2019 and FY2021 -- have no
text layer on any page. That much was clear from sampling the first 25 pages of each, and
it is also as far as sampling gets you, because **the other ten are hybrids**: a typed
front section and scanned appendices, in proportions that differ every year.

FY2025 is 187 pages, of which only 53 are typed. The financial tables the project actually
wants -- appropriations by department, the payroll report, bonded indebtedness -- are on
the scanned side even in the years that looked digital. So OCR is not the minority path
here to be dealt with later. It is the main one, which is why the rotation and raster-scale
findings below are load-bearing rather than incidental.

`sources/data/annual-report-survey.csv` records this per page rather than per document,
because per document is the granularity that produced the wrong answer.

FY2012 is the pure case: 116 pages with **no font resources at all** -- page 58 is a single
4400x3400 `CCITTFaxDecode` image. pypdf returning zero characters from it is the right answer, not a
failure, and the 298KB of text the archive holds for it came from `ocr_pdf.swift`, which
`fetch_town_docs.py:262` already falls back to when a text layer yields under 200
characters. Worth stating plainly because a zero-byte extraction looks exactly like a
broken tool.

### There is no correct extraction mode, only a correct one for the page

pypdf offers `plain` and `extraction_mode='layout'`, and on the *same document* each is
catastrophically wrong where the other is right.

On FY2025 page 26, the special revenue fund detail, layout mode is the only one that gets
the columns:

    1303  SUMMER SCH   $   340.00                          $   -
                       ^ Fund Balance       ^ BLANK         ^ Deficits

Plain mode renders that row as `$ 340.00 $ -` -- two values in a three-column table -- so a
parser assigns 340 to Fund Balance and `-` to *Receipts*, shifting every figure one column
left. **The blank cell exists only as a position.**

Four pages earlier, on the combining balance sheet, layout mode recovers **zero** money
tokens off a page that holds 61, spreading each row across 3,469 characters. Plain mode
reads it correctly.

So `instrument()` runs both, counts what each recovers, and records which won. Rule 13 says
an instrument that reformats before you see it is part of the finding; this is that, made
mechanical, and every table the module returns carries the mode that produced it.

### Columns come from a ruler, and the ruler comes from the rows with figures

A gutter is a run of character positions blank in ~92% of rows -- not all of them, because
one long label crossing into the next column would erase a boundary thirty other rows
agree on.

The ruler is measured over **only the lines carrying money**. Measured over every line, the
centred `TOWN OF LUNENBURG` heading and the date span the full width, cross every gutter,
and the ruler finds boundaries in the title's word gaps instead of the table's.

Each cut is then **snapped to a blank position in that row**. Cutting at the gutter's edge
sliced `45.00` to `45.0` and, worse, cut `(62.84)` to `(62.84` -- and a negative that loses
its bracket reads as a positive. A row with nothing blank anywhere in a gutter genuinely
spans the boundary and comes back marked `!` so it can be dropped rather than parsed.

### The scans go through the same ruler

`ocr_pdf.swift --boxes` now writes every recognised line with its position and confidence
instead of joined text. Reading order is fine for prose and useless for a table, and these
tables have columns that exist only as geometry. `layout_from_boxes()` rebuilds a
fixed-width page from those coordinates, so one column algorithm serves both kinds of
document -- and the three-up newspaper layout of the receipts page resolves correctly.

### Two checks, because neither one is sufficient

**Reconcile to a total the report prints.** The FY2025 capital project fund detail sums to
$3,096,913.16 across 14 rows and the report prints $3,096,913.16. `extract_munis_report.py`
refuses to write when it does not tie; so should these.

**And check that every figure has a label**, because reconciliation provably cannot. On
page 1 of the FY2016 addendum, Vision read `$22,399,495.70` and did not read
`REAL ESTATE TAXES` beside it -- the largest revenue line in the town, extracted as a
number with no name. It also lost `TAX LIENS REDEEMED` and, by position, Chapter 70 at
$5,834,483.00. **The figures still summed to the report's printed GRAND TOTAL**, because a
missing label does not change a total. A table can tie perfectly and have lost what half
its rows are about.

### Raster scale is a correctness parameter, and it fails at confidence 1.000

The dropped labels above are not a resolution artefact in the ordinary sense. Vision's
recognizer revision and language correction make no difference at all. Raster scale makes
all of it:

| scale | left-column rows | `REAL ESTATE TAXES` | `TAX LIENS REDEEMED` |
|---|---|---|---|
| 3.0 | 38 | missing | missing |
| 4.0 | 38 | missing | missing |
| 6.0 | 39 | **read** | **read** |
| 8.0 | 39 | read | read |

Every reading, including the truncated ones, is reported at **confidence 1.000**. So
confidence cannot find them and only a second pass can.

Going higher does not converge either. Between 6.0 and 8.0 no rows are gained or lost, but
`PERSONAL PROPERTY TAXES` degrades to `PERSONAL PROPERTY TAXE` and `TEREST` becomes
`ITEREST`. **Structure settles; characters do not.** `differential()` therefore reports
them separately: a row seen by both passes is a row that exists, and text the two passes
spell differently is text that has not been read.

Some labels are unrecoverable at any scale. `INTEREST REAL ESTATE` comes back as
`TEREST REAL ESTAT` every time, because its first and last characters touch the cell rule.

### /Rotate is the third trap, and it does not mean what it says

Most of the financial tables in the FY2011 report sit on landscape pages carrying
`/Rotate 90`. PDFKit hands back the *unrotated* mediaBox and draws unrotated, so Vision was
reading the page sideways -- and it reads sideways text perfectly well, returning boxes that
are tall and narrow:

    x=0.14390  y=0.11842  w=0.0116  h=0.0959   TAXES & EXCISES:
    x=0.15262  y=0.11842  w=0.0131  h=0.1523   PERSONAL PROPERTY TAXES

Every label in a column shares one `y`, so row banding collapsed the entire table into a
single line of labels followed by a single line of amounts. Nothing about the text was
wrong; the geometry was ninety degrees out.

**The obvious fix -- read `/Rotate` and apply it -- is wrong, and wrong in a way that looks
right.** Measured against the pages themselves:

| page | `/Rotate` | rotation that actually produces upright text |
|---|---|---|
| FY2011 p58 | 90 | **90°** |
| FY2011 p37, p60 | 90 | **not 90°** |
| FY2019 p124 | 270 | **0° — PDFKit had already applied it** |
| FY2016 addendum p1 | 270 | **0°** |
| FY2016 addendum p2, p4, p5 | 270 | **90°** |

`/Rotate` does not say what the renderer will do with the page, and **orientation varies
within a single document** -- the 17-page FY2016 addendum needs three different rotations
across its pages. Applying one answer per document is wrong for part of every document that
needs one at all. Trusting the flag "fixed" FY2011 p58 and left 89 of its 101 pages
sideways, which was not visible in any output: the text was all there, correctly spelled,
in the wrong geometry.

So `ocr_pdf.swift` now **calibrates per page, by measurement**: render at each of the four
orientations, recognise, and keep the one with the highest *fraction* of boxes wider than
they are tall. Horizontal text in horizontal boxes is the only assumption. Most pages are
already upright, so 0° is tried first at low resolution and accepted when it clearly wins;
only the pages that fail pay for the other three.

**The fraction matters, not the count.** Scoring by how many horizontal boxes an
orientation produces rewards whichever one shatters the page into the most fragments: on
the FY2016 addendum the count chose 90° (338 boxes against 110) while the fraction chooses
correctly, 100% against 0%. That is the same error as ranking budget lines by size instead
of by pull -- a bigger number that measures the wrong thing.

### A page with no figures is not a page with no text

The first version of `instrument()` returned "no text layer" whenever both extraction modes
recovered zero *money tokens*. A survey built on it reported 2,311 of 2,751 pages as
unreadable scans.

That was counting figures and calling their absence an absence of text. FY2025's school
staff rosters are lists of names -- 1,653 characters on page 100, extracted perfectly, and
not one dollar sign. The survey reported `staff_roster` as appearing in **no year at all**,
of a table this file had already quoted from.

It is `search_minutes.py`'s failure exactly: an instrument that finds none of what it
counts, reporting nothing, and nothing being read as absence. `instrument()` now falls back
to character count and returns None only when neither mode produces meaningful text, and
the survey reports "readable" and "carries figures" as two separate columns.

### One page is clipped, and only looking at it shows that

FY2011's receipts page carries the whole year's revenue in three label/amount columns. The
third column's amounts are not there. Neither is the `SUMMARY OF RECEIPTS` block's, nor the
`GRAND TOTAL`'s -- the labels print and the figures do not:

    LOCK UP FEES            (no figure)
    MISC. REVENUE           (no figure)
    TAXES & EXCISES         (no figure)
    GRAND TOTAL             (no figure)

The first guess was that Vision had dropped them, which is a thing it demonstrably does.
It had not. **The town's own scan is clipped at the right edge**, and rendering the page
shows it immediately: the third column's labels are cut off mid-word --
`SALE OF TOWN PROPERTY/EQUIPME`, `MEDICARE PART D REIMBURSEMEN` -- because the paper ran
out. The facing page is a pie chart, not a continuation.

So for FY2011 there is no total to reconcile to and roughly a third of the detail does not
exist in the document. `extract_annual_receipts.py` skips the year and says why, which is
the right answer: a year that cannot be checked must not be published as though it had
been. What is recoverable is still real -- `CH 70 SCHOOL AID $4,523,464.00` is on the page
in a column that was not clipped -- but it is a part of a table, not the table.

Two things follow. **A missing figure has more than one cause**, and OCR is only the first
one you think of; the others are a clipped scan, a page that continues elsewhere, and a
figure the publisher never printed. And **the check is to look at the page**, which is rule
13 in its plainest form: check what a reader sees, not only what the file holds.

### The digital years repair the scanned ones

The town reuses its own line names year after year, and ten of the sixteen reports were
typed rather than scanned. So the correct spelling of `TEREST REAL ESTAT` is sitting in
FY2020's receipts table, and the archive can repair itself from the half of it that has a
text layer. `repair_label()` matches against that vocabulary:

    'TEREST REAL ESTAT'          -> INTEREST REAL ESTATE           0.919
    'TEREST MOTOR VEHICLE EXCIS' -> INTEREST MOTOR VEHICLE EXCISE  0.945
    'PRO FORMA/ROLL BACK TAXE!'  -> PRO FORMA/ROLL BACK TAXES      0.960
    'ZQX FOO'                    -> (no match)                     0.250

**A repair is a derived thing and is never written in place.** What was observed is
`TEREST REAL ESTAT`; `INTEREST REAL ESTATE` is an inference, however good. Rule 7 applies
to a corrected label exactly as it applies to anything else, so both are stored and the
ratio with them.

### What the reconciliation actually caught

`extract_annual_receipts.py` wrote **nothing** on its first run, and every failure was
worth having:

| year | difference | what it was |
|---|---|---|
| FY2014 | detail $31,842,581.89 vs printed $2,209,000.67 | lines pooled across pages -- receipts detail was being checked against a trust fund's total |
| FY2022 | ±$2,415,590.84, exactly equal and opposite | `TRANSFERS FROM OTHER FUNDS $2,391,150.83` + `INVESTMENT INCOME $24,440.01` -- labels printed **twice** on the page, once as detail and once as their own summary category, at the same value, because those categories have one member |
| FY2016 (earlier) | ±$3,333,429.48 | five categories whose summary names differ from their detail headings (`LICENSES AND PERMITS` vs `LICENSES/PERMITS`) |
| FY2022 (earlier) | $32,522.00 | `STATE OWNED LAND`, a detail row that happened to end its own line inside the summary window |

None of these would have been visible in the output. Each produces a plausible table of
plausible figures; only the arithmetic says otherwise, and the equal-and-opposite signature
names the cause almost exactly.

The fix needed **both** tests, because each alone fails where the other holds: the window
alone sweeps in a detail row that ends its line inside the block, and the category list
alone claims both copies of a twice-printed label. Position would settle it and is not
available -- plain mode is the only instrument that reads this page, and the coordinate
walk reports every run at `x=0` because each line is a single text-showing operation with
the columns spaced by kerning.

Four years now tie exactly on both checks -- FY2014, FY2015, FY2017 and FY2022, 401
source-years. Verified back to the source rather than to the pipeline:

    4120-fy-2014-annual-town-report.pdf, page 22, mode=plain, line 37:
      'SEALING FEES $3,195.00 CH 70 SCHOOL AID $5,516,107.00'
    ...line 35:
      'CABLE T.V. $1,594.50 VET/BLIND/... $42,717.00 GRAND TOTAL $30,789,379.47'

And because both sums tie, **nothing was dropped**: a source missing in one year is a line
the town did not print that year, not a line the extractor lost. That is a stronger
guarantee than the extraction itself, and it is the reason for reconciling rather than
spot-checking.

### Each report is its own document, and no pattern carries across years

**This is the rule the rest of this file kept discovering the hard way, one extractor at a
time.** Fifteen annual reports span fifteen years of different town managers, different
superintendents and different principals. Nobody was maintaining a format. So there is no
house style to key on, and **any pattern written against one year will silently succeed for
the years that happen to match and silently fail for the rest** -- producing a series that
looks continuous and is actually a record of which years used a particular word.

It has now happened three times, in three different extractors, and the failure is the same
shape every time:

| what was keyed on | what it cost |
|---|---|
| `SUMMARY OF RECEIPTS` as the receipts page's signature | FY2023 and FY2024 reported as having no receipts table. They both have one, across pages 34-40 and 22-29; they do not use that heading. |
| `STAFF ROSTER` as the roster page's signature | FY2025 yielded 143 names against FY2018's 226. Its rosters actually run p100-p110; four pages carry those two words and the rest -- p103 with 45 names, p106, p110 with 70 -- do not. |
| `GRAND TOTAL` as the anchor's signature | receipts detail from one page reconciled against a trust fund's total on another |

And the cost is worse than a gap, because a gap is visible. **A pattern that matches some
years produces a comparable-looking series across the years it matched**, and the years it
missed read as years the town published nothing. The FY2025 roster count did not look
broken. It looked like a school district that had shrunk by a third.

**What to do instead.** Locate a table by *what it contains*, per report, and let the
reconciliation decide whether it was read correctly:

- Score every page on content -- density of label/amount pairs, density of name-like
  tokens, presence of any printed total -- rather than matching a heading.
- Take the anchor from **the same page** as the detail, whatever that year happens to call
  it.
- Where a year prints no total, say so and mark the year partial. Do not fall back to a
  pattern from a neighbouring year, because the neighbouring year was written by somebody
  else.
- **Print the denominator per year**, not just overall. A year contributing far fewer rows
  than its neighbours is the signal, and it only shows up if the per-year count is on the
  page.

**And it applies to everything here** -- every CSV this project builds from these reports,
and every table in them. Receipts, appropriations, special revenue, trust funds, debt,
payroll, rosters. None of them may assume a heading, a page range, a column order or a
label spelling carries from one year to the next.

The general form is that **consistency across a series is a hypothesis, not a property**,
and rule 7 applies to it like anything else: we observed that four pages say `STAFF ROSTER`;
we inferred that those were the rosters. The inference was wrong and nothing in the output
said so.

### An external series is the check a single-source series cannot have

DESE publishes Teacher FTE, Paraprofessional FTE, enrollment and per-pupil spending for
Lunenburg for **FY2009-FY2025 unbroken** -- `sources/data/dese-radar.csv`, 497 rows for the
district. It is compiled by somebody else from a different return, which is exactly what
makes it useful.

It caught the FY2025 roster shortfall immediately. 143 names off four schools against 226
in FY2018, while DESE has Teacher FTE moving only 115.1 to 105.1 over the same span --
a fall nowhere near large enough to explain it. Nothing internal to the roster extraction
could have raised that, because the extraction was self-consistent.

This does not make DESE a source of truth for anything the reports measure: a roster is a
count of names printed and FTE is a different quantity, and rule 7 forbids treating one as
the other. It makes DESE a **detector of missing pages**, and that is worth having on every
series the reports produce.

### The order of work

1. **Survey before extracting.** A 2011 report and a 2025 report are not the same document.
   Which pages carry which table, in what shape, which columns pair with which, and what
   printed total anchors each one -- written down before a line of extractor. This is the
   step `orphans()` cannot do without: which column holds the label is a fact about the
   table, and the receipts page has three label/value pairs across one physical row.
2. **Digital years first.** They are ten of the sixteen, they need no OCR, and they build
   the label vocabulary the six scanned years are repaired against.
3. **One extractor, reconciled, before any others.**
4. **Then the scans**, two passes at scale 6.0, differenced.
5. **Then the rest**, cheapest question first:
   - **Receipts by source x year** -- fifteen years of revenue history against the one
     year we hold.
   - **Special revenue funds x year** -- the school Fund series, which turns
     `fund_activity` from a snapshot into a history and would show whether FY2026 is
     typical.
   - **Appropriations by department x year** -- the omnibus split over time; how the
     school's 51.2% has moved.
   - **Staff rosters** -> **counts by position and school, not names.** The analysis needs
     "nine paras at Primary"; it does not need who they are, and storing names creates an
     obligation the project has no use for. The names stay in the archived PDF where the
     town published them.
6. **Size.** These are 35-55MB each, roughly 600MB in total, and the source index enforces
   a 25MiB per-file publishing limit. They will need `ELSEWHERE` entries, the same
   mechanism the 40MB bridge assessment already uses.

### What this does not solve

Reading a table is not the same as knowing what it means, and none of the above touches
rule 11. A receipts line still does not say which fund pays for what, and a staff roster
still has no FTE and no funding source on it.

---

## Why this belongs in findings rather than the handoff

The handoff carries state and open decisions. It has nowhere to put a **lead** — a place we
have not looked yet — and that is exactly what went missing here. `DATA-WANTED.md` is about
documents we know we need; this is about **stores we did not know existed**, which is a
different and more dangerous category, because nothing in the archive can tell you it is
incomplete in that direction.
