# The shape an extractor has to have

TJ, 28 September 2026, after watching one extractor eat an afternoon while three others
were written in twenty minutes each:

> *"i think we may need an updated extractor format. you fail very often on the extractor
> and spin a lot."*

He is right, and the day is a controlled experiment, because four extractors were written
against the same archive on the same afternoon by the same reader.

| what | built on | how long | outcome |
|---|---|---|---|
| the trust matrix, 462 figures | word boxes with x and y | ~20 min | five identities close on all 33 columns |
| Monty Tech, off an embedded chart | word boxes with x and y | ~20 min | the total closes in all three years |
| the two capital plans | word boxes with x and y | ~20 min | every running total closes |
| special revenue, FY2024 | page flattened to TEXT LINES | a whole afternoon | abandoned mid-migration |

The difference is not the difficulty of the tables. The trust matrix prints its fund names
SIDEWAYS, one per column, and closed first time. The special revenue schedule is a plain
grid and did not close at all.

## The difference is whether the coordinates survive

**A page arrives as words with real positions.** `ocr_words.swift` writes one row per word
with an x, a y and a width, and `pdfplumber.extract_words()` gives the same thing for a page
that carries its own text. Both instruments hand over the geometry.

**The old path throws it away.** `report_pages.load()` renders a page back into TEXT LINES:
`layout_from_boxes` turns each word's x into a character offset in a string, and from then
on a column is a run of spaces that most rows agree on. That works while every row is
full. It fails exactly where it matters:

- **A column no row fills is not there at all.** FY2024 page 23 has no fund with a receipts
  figure, so there is no gutter between Fund Balance and Receipts and the page rules into
  two money columns where page 26 rules into six. The same slot number then means a
  different printed column on two pages of one table, and summing it adds Fund Balance to
  Deferred Revenue. That is the $19,435 that took an afternoon.
- **Headings and figures do not share a character position.** Figures are right-aligned and
  headings are CENTRED over their column. Cutting `Fund Balance` at a ruler measured from
  the figures yields `F` and `und Balance`, and `und balance` matches nothing. Three
  attempts to recover the names from the flattened text failed for this reason; the
  headings sit at x=0.554 on all four pages, to three decimals, in the boxes.
- **A slot has no name, so nothing can be checked.** 2,422 rows sat at `no check` beside a
  total the town printed on the page, because you cannot sum a column you cannot identify.

## The shape that works

    words with x and y
      -> rows        banded on the page's MEASURED gap, never a rounded grid
      -> columns     placed at the nearest MEASURED heading centre, never by order
      -> names       read off the printed heading, never inferred from position
      -> a verdict   an identity the page states about itself, or write nothing

Every clause has a rule behind it and every one was earned today:

- **Band on the gap, do not round to a grid.** Rounding y split four of nine rows on the
  Monty Tech chart, because 0.427 and 0.430 round apart at any divisor near the pitch while
  two adjacent rows can round together. Measure the within-row spread and the between-row
  pitch; here they were 0.004 and 0.035 and no threshold between them can be wrong.
- **Place by position, except where position means something else.** On a TABLE, x is the
  column (rule 13b). On a BAR CHART, x is the value -- a label sits at the end of its
  segment -- so there the order is the column and a row without one figure per series is
  refused. Know which kind of page you are on and say so in the code.
- **Name from a heading you read.** A position is not a name. The fourteen measures on the
  trust matrix are declared against the token set each must match, and a year whose page
  does not match them is REFUSED rather than aligned.
- **Refuse rather than publish.** Every one of the three that worked writes nothing at all
  unless the page's own arithmetic closes, so a row's existence is the verdict.

## What follows

**A new extractor starts from the boxes.** Not from `report_pages.load()`, and not by
copying a working extractor's text-line handling.

**The three that worked each hand-rolled the same forty lines** -- band, place, name,
check -- and that is the thing to lift into one place next, rather than a fifth copy. The
old text-line path stays for prose and for the three-column newspaper layouts whose columns
are kerned rather than positioned, which is what `report_pages` documents it for.

**Migrating `extract_special_revenue.py` is its own piece of work**, not something to do
inside another task. It is 2,422 rows across sixteen editions and the check that exists
today ties five of them; a migration has to keep those tied while naming the columns, and
attempting it mid-afternoon inside a FY2024 page fix is how the afternoon went.
