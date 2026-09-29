# The annual-report page stream: what to do next

**28 September 2026.** Everything on this stream is now READ A PAGE, one year at a time,
one section at a time. The process is `notes/process/READING-A-REPORT-PAGE.md` and it is
not optional reading -- every rule in it was paid for today.

Where the 484 financial pages stand (`python3 scripts/map_annual_report_pages.py`):

    258 PROVEN    figures tie to something the page states about itself
    218 UNPROVEN  rows exist, nothing has checked them
      8 REFUSED   an extractor reached the page and wrote nothing
      1 BLOCKED   the page CANNOT be read; see sources/data/page-blocked.csv

Four years are at zero. Yesterday morning it was none.

    FY2025   23 of 23     FY2024   28 of 28     FY2023   34 of 35, one blocked
    FY2014   28 of 28

---

## THE ONE THING THAT CHANGED: STOP RUNNING OCR

TJ, 28 September 2026: *"i'm 100% done with OCR. that's totally a waste of my time and
credits."* Measured on FY2024's special revenue schedule, 164 rows, both readings of one
document:

    recognition   14 of 60 rows on one page, and DIFFERENT DIGITS for the same row at
                  different resolutions -- 90.61 and 0.61 -- so merging passes cannot help
    read          164 of 164, all six columns tying to the printed totals, first attempt,
                  about ten minutes

**A page that carries its own text is read with `pdfplumber`. A page that is a photograph is
RENDERED AND READ.** Not recognised, not as a cross-check, not as a fallback. If a
recognition cache already exists for a page it is not evidence and not a starting point.

---

## HOW THE WORK GOES NOW

**One year. Build the table once. Work the sections, top to bottom, committing each.**

    python3 -c "
    import csv, collections
    rs=[r for r in csv.DictReader(open('sources/data/annual-report-pages.csv')) if r['fy']=='2014']
    print(collections.Counter(r['state'] for r in rs))
    for r in sorted(rs, key=lambda r: int(r['page'])):
        if r['state']!='proven':
            print(r['page'], r['state'], r['subject'], '|', (r['failed_by'] or r['refused_by'] or '-'), '|', r['heading'][:40])"

Then, before reading anything in a section:

| | |
|---|---|
| **extent** | where does the table start and stop? Walk outward until it does. |
| **holes** | a page BETWEEN or BESIDE the run that the tracker does not list at all |
| **reader** | per PAGE: its own text, or a photograph? And what dpi? |
| **size** | what SHOULD it hold, from the page's shape rather than from our data? |

**THE HOLES ARE THE ONE THE LIST CANNOT TELL YOU**, and they are not hypothetical: five pages
of FY2024's gross wages and one page of FY2023's omnibus budget were absent from the tracker
entirely, each with a full table on it. A page is listed only when recognition found fifteen
money figures, so a page it failed on completely is not unfinished -- it does not appear.
A page somebody has READ is now added to the map, but nothing finds the ones nobody has
looked at yet.

**The subject label is a guess from the words at the top of the page.** FY2023's pages 164-167
are labelled trust-and-stabilization, payroll, payroll and regional-school, from the headings
`INFRA21-03`, `Reserve Fund`, `Police Lock Up` and `Traffic Signs & Devices`. They are one
omnibus budget. What says two pages are the same table is that the same EXTRACTOR holds rows
for both.

---

## WHAT A TRANSCRIPTION IS

`sources/data/page-reads/` -- 17 files, 3,342 figures. Each row carries the document, the
page, the column, who read it and what proves it. **It is DATA, never typed into an
extractor**, and `scripts/verify_page_reads.py` re-proves every one on every run. That is
the property recognition had and a read does not: the reading happens once, the check
happens for ever. It is in `check_generated.py`.

A transcription declares what checks it:

    kind=total        the figure the page prints, that the rows must foot to
    kind=check        `row_identity`  a,b,c=d  or  a-b-c=d   -- accumulates, a page may
                                      state several; the trust summary states five
                      `rows_per_page` / `ordered_by`  -- COVERAGE, for a page with no total
    kind=attested     WE READ IT RIGHT AND THE DOCUMENT DISAGREES WITH ITSELF. Excluded
                      from the check and REPORTED, loudly, every run. Never a tolerance.
    tolerance         only with a reason: a page printing DISPLAYED whole dollars over
                      figures carrying cents cannot tie to the cent

**What makes a read safe is the arithmetic, not the reader.** A person or a model reading a
page is a reading like any other (rule 13a). What settles it is 164 rows landing on six
printed totals, or 46 funds closing five identities each, or 115 figures matching a
different year's report.

---

## WHERE EACH YEAR STANDS

| year | pages | proven | left | notes |
|---|---:|---:|---:|---|
| FY2011 | 28 | 10 | 18 | all photographs |
| FY2012 | 27 | 10 | 17 | all photographs |
| FY2013 | 29 | 8 | 21 | all photographs |
| FY2014 | 28 | **28** | 0 | **at zero** -- and it GREW by one page while being read |
| FY2015 | 31 | 13 | 18 | 15 of 18 digital |
| **FY2016** | 41 | 12 | **29** | **28 of 29 digital -- the biggest digital haul, do this next** |
| FY2017 | 33 | 14 | 19 | 11 digital |
| FY2018 | 35 | 17 | 18 | 10 digital |
| FY2019 | 38 | 11 | 27 | all photographs |
| FY2020 | 39 | 16 | 23 | 4 digital |
| FY2021 | 37 | 16 | 21 | all photographs |
| FY2022 | 33 | 18 | 15 | 5 digital |
| FY2023 | 35 | **34** | 1 | **at zero** but for p25, blocked at 93 dpi |
| FY2024 | 28 | **28** | 0 | **at zero** |
| FY2025 | 23 | **23** | 0 | **at zero** |

Counts per page are generated into `notes/generated/TEXT-LAYER-COVERAGE.md` by
`scripts/survey_text_layer.py`; it is a property of the PAGE, not of the report, and the
per-report version of that table is what made FY2024 look like the cheapest year when it was
the most expensive.

**Take FY2016 next**, then FY2015. Those two hold 43 of the 47 digital pages left; after them
the remaining years are photographs and get read, not parsed.

---

## WHAT TO EXPECT, FROM THE THREE YEARS DONE

**Most `refused` pages were read correctly and refused for something that is not the page's
own arithmetic.** FY2023's balance sheet was refused on a CROSS-DOCUMENT comparison while
every one of its own identities closed in all six columns. Both receivables runs were
refused for `no single sign convention` when the page simply prints negatives in
parentheses. FY2023's debt schedule was refused because `the year header could not be read`
-- it reads fine once the IMAGE is turned.

**Some pages do not foot and the town is why.** FY2024's levy build-up is $55,184.33 short
in one of three columns; FY2023's tax recapitulation is $790,537.77 short, which is exactly
798,523.00 less 7,985.23, a decimal shift; FY2023's `Total General Government` misses its own
lines by eighty cents. Each is attested, registered in `document-defects.csv`, and says
plainly that WHICH FIGURE IS WRONG IS NOT ESTABLISHED.

**Reading part of a page is fine. Calling it finished is not.** The two debt schedules have
only their GRAND TOTAL blocks transcribed -- about fifty per-issue rows each are not -- and
that is a row in `money-gaps.csv`, not a footnote.

**A page can be unreadable and that is a finding.** `page-blocked.csv`, `blocked` in the
tracker. Measure dpi before rendering; it is dpi AND density, since FY2023 p24 reads
perfectly at 72 dpi and p25 is hopeless at 93.
