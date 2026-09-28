# Getting the annual reports to zero: the plan

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
