# OCR geometry for the annual town reports

Written by `scripts/ocr_pdf.swift --boxes` at **raster scale 6.0**, one TSV per report:
`page, x, y, w, h, conf, text` — one row per recognised line, position normalised with the
origin at bottom-left.

**This is a derived rendering, not a source.** The sources are the PDFs in `../docs/`. These
files exist because the reports are overwhelmingly page scans — 1,163 of 2,751 pages have no
text layer at all, and the rest are hybrids — and because a table's columns in a scan exist
only as geometry. `pdf_tables.layout_from_boxes()` rebuilds a fixed-width page from these
coordinates so the same column algorithm serves scanned and digital pages alike.

## Two things that are not obvious and cost real time

**Raster scale is a correctness parameter, and it fails silently at confidence 1.000.** At
scale 3.0 and 4.0 the FY2016 addendum loses `REAL ESTATE TAXES` and `TAX LIENS REDEEMED`
entirely — the largest revenue lines on the page, dropped with every surviving reading
reported at full confidence. At 6.0 they come back. Structure settles by 6.0; individual
characters never settle at all, so a second pass at a different scale is the only way to
tell a reading from a guess. Regenerate at 6.0 or the output will not match.

**`/Rotate` must be honoured when rasterising.** Most of FY2011's financial tables are
landscape pages marked `/Rotate 90`; PDFKit returns the unrotated mediaBox and draws
unrotated, so Vision read them sideways and returned boxes that are tall and narrow. Every
label in a column then shares one `y`, and row banding collapses the whole table into a
single line of labels followed by a single line of amounts. It looks like a text problem
and is a geometry one.

## Regenerating

    for pdf in sources/town-budget/docs/*annual-town-report*.pdf; do
      swift scripts/ocr_pdf.swift "$pdf" \
        "sources/town-budget/ocr/$(basename "$pdf" .pdf).tsv" 6.0 --boxes
    done

Roughly 90 minutes for all sixteen. Apple Vision, on-device, no network.
