# Correcting a Textract misread: arithmetic locates the cell, an independent reader confirms it

Written 29 October 2026 for the 1991-2010 annual-report tables. A figure Textract misread
(`$` as `8`, `5` as `6`, a dropped digit) breaks the identities the page prints about itself.
Re-reading with Textract does not fix it: same engine, same pixels, same error (rule 13b).

## The four steps

    python3 scripts/locate_cell_misreads.py --all          # 1 LOCATE   no network, seconds
    python3 scripts/witness_cell_crops.py crops            # 2 CROP     no network
    python3 scripts/witness_cell_crops.py read --limit N   # 3 READ     `claude -p`, costs usage
    python3 scripts/witness_cell_crops.py reading KEY TEXT --reader NAME [--illegible]   # 3' a person
    python3 scripts/witness_cell_crops.py decide           # 4 ACCEPT / LOG

then, per edition touched: `read_report_tables.py <ed>` and `--check`, `merge_report_tables.py`
and `--check`, `build_db.py`, `map_annual_report_pages.py`.

1. **Locate.** A cell is a candidate only when a failing ROW identity and an OPEN COLUMN total
   both contain it and each, solved for that cell alone, asks for the same value; and the value
   is ONE digit edit from Textract's text. One failing identity is not enough, and two
   coincident ones that need a two-digit change are not a misread (1992 p36, 8 such, dropped).
   Output: `build/cell-witness/candidates-<ed>.csv` (cell, Textract text, required value, both
   identities, Textract's bounding box). `locate_cell_misreads.py` adds one identity
   of its own, for the debt repayment schedule only: a row's TOTAL column is the sum of its
   year columns.
2. **Crop.** The cell's own Textract box from the cached response, rendered at 432 dpi with a
   small margin, turned to reading orientation. `build/cell-witness/crops/` (gitignored).
3. **Read, blind.** The reader sees the crop and nothing else: no Textract text, no required
   value. `read` runs `claude -p --json-schema` (sonnet, Read tool) one cell per call; or a
   person reads the crop and enters it with `reading`. Readings land in
   `build/cell-witness/readings.csv`.
4. **Decide.** Accept only when the reading, parsed, EQUALS the required value exactly. Then
   `report-tables/<ed>/witnessed-cells.csv` gets the cell, applied by
   `read_report_tables.apply_witnessed_cells` (a per-edition opt-in: no file, no change). The
   emitted row keeps Textract's text in its cell and says `cell witness: Textract ..., corrected
   to ...` in `repaired_cells` / `reconciliation`. A reading that differs corrects nothing; it is
   logged in `cell-witness-log.csv` (every outcome, per edition) and stamped
   `witness_disagrees` on the matching row of `notes/generated/annual-report-discrepancies.csv`.

## Cost

- Locate and crop: no network, no model. All 20 editions in well under a minute.
- A scripted read: **$0.35 per cell API-equivalent** measured (one successful call), about
  0.07% of the week by the repo's convention of $5 per 1%, mostly the fixed cost of a
  `claude -p` session (about 130k cache-creation tokens), not the crop. A second call hit the
  `--max-budget-usd 0.5` ceiling and failed; the scripted reader needs the ceiling raised or a
  lighter session before it is run over a batch. Quote it in the week before a batch.
- A read by a person at the keyboard costs a session turn per image at session prices; do it
  fresh, not in a long session (rule 7g).

## What it will not do

- It cannot fix a PRINTED error. The 1998 `TOTAL` that leaves a $660,000 bond out of its column
  is located as a one-cell pin and the reader sees what the page prints; the page stays open.
- It cannot see a cell whose misread leaves no identity pinned: a wage list prints no total,
  a cell with no row identity, a cell whose row and column both fail by different amounts.
- It cannot read what the scan cannot show. Five against six, and eight against three, are
  unresolved at some of these resolutions; the reader is then `illegible` or disagrees, and
  nothing is corrected. The 1993 p54 `$6,280` is such a case: arithmetic says 5,280, an earlier
  by-eye note says the glyph is 5, both readers in the pilot saw 6. It stays open.
- Crops can be offset: some boxes land one line off, so a crop shows two lines and the reader
  must choose which is the cell. Where it cannot, mark it illegible rather than guess.
- A +-1 pin on a total (1999 p86, 2007 p64, 2007 p76) is usually the town's own rounding. The
  reader will report what is printed, the two will differ, and nothing is corrected.
- Not blind enough in the pilot: the person who read the crops had seen the candidate list. A
  scripted reader is blind by construction; prefer it for the batch.

## Pilot, 29 October 2026

26 candidates from 20 editions; 25 read (2 by `claude -p`, one failed on the budget ceiling;
25 by a person), 1 illegible. 13 accepted, 12 disagreed. Accepted cells landed in seven
editions (1996, 1998, 2000, 2001, 2006, 2009, 2010) and moved two pages to proven (2009 p60,
2010 p69); the other cells closed their identity on pages that stay unproven for other
reasons. `locate_cell_misreads.py --all` now lists 13 candidates, every one read and not
confirmed.
