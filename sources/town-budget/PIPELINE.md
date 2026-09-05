# From the town's PDF to a row in the database

Every stage is written to disk, so any of them can be re-read or re-run without repeating
the ones before it. This matters because the expensive stage is the second one — roughly
two hours for the archive — and because a transformation nobody can inspect is a
transformation nobody can check.

| # | stage | written to | size | cost to redo |
|---|---|---|---|---|
| 1 | **The town's PDFs** — the primary source | `docs/` | 399 MB | re-download |
| 2 | **OCR geometry** — every recognised line with its position and confidence | `ocr/*.tsv` | 13 MB | ~2 hours |
| 3 | **Rendered page text** — two renderings per report | `pages/FY*.txt`, `pages/FY*.ocr.txt` | 24 MB | ~5 min |
| 4 | **Catalogues** — what tables each report holds, read page by page | `../data/inventory/*.json` | 1.1 MB | agent time |
| 5 | **Roster packets** — the pages, and what was read off them | `../data/rosters/` | 1.4 MB | agent time |
| 6 | **Datasets** — the CSVs | `../data/*.csv` | — | seconds |
| 7 | **Database** — a derived read model, rebuilt from the CSVs | `../data/lunenburg.db` | — | seconds |

## Why two renderings are kept at stage 3

`FY2011.txt` is the PDF's own text layer where there is one. `FY2011.ocr.txt` is the OCR
geometry rebuilt into a fixed-width page. **Neither is better in general.**

The text layer is the more faithful reading of the *words* — it is what the publisher
wrote, with no recognition step to get it wrong. But it preserves reading order, not
columns: `Regional Assessor Fund $30,907.25 $30,907.25` comes out with single spaces and
the column positions simply gone.

The OCR keeps position, and loses characters. On one election page it never recognised the
standalone `0` glyphs, so `6 0 0 11 17` came through as `6 … 11 17`.

So the choice is made per page, by the question being asked of it. A ruler-based extractor
reads the OCR; a pattern-based one reads the text layer; a tally table is read from
whichever yields more figures.

## What stage 2 is, exactly

`ocr/*.tsv` is `page, x, y, w, h, conf, text` — one row per recognised line, position
normalised with the origin at bottom-left, produced by Apple Vision at raster scale 6.0
with per-page orientation calibration. It is a **rendering, not a source**: the sources are
the PDFs beside it. But it is the expensive rendering, and everything from stage 3 onward
is a cheap function of it.

Regenerate with:

    for pdf in sources/town-budget/docs/*annual-town-report*.pdf; do
      swift scripts/ocr_pdf.swift "$pdf" \
        "sources/town-budget/ocr/$(basename "$pdf" .pdf).tsv" 6.0 --boxes
    done

## Checking a row back to the page

`sources/data/dataset-provenance.csv` maps every dataset-edition to its document, both
published addresses, the publisher's own label and a sha256. Every dataset row carries its
own `page`. To see the page a figure came from:

    python3 scripts/verify_against_page.py <dataset> <edition> --pages <n>

which renders the page upright beside the rows extracted from it.
