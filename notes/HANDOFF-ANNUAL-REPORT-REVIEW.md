# Handoff: the annual-report review (P6) on debt schedules

**Read this before running `report_review.py` on a newly Textracted report.** Written 28 October
2026. The rest of P6 is in `notes/PLAN-ANNUAL-REPORT-PIPELINE.md` sections 7 and 8; this note is
only the one known hole, and what to do about it the next time a report arrives.

## The hole

On FY2011's two debt-schedule pages (PDF 76-77) -- pages a person already PROVED -- the review
leaves **35 totals open, and calls 19 of them `printed_error` suspects.** Every one is a false
alarm: the page is proven, so the town's arithmetic there closes.

    python3 -c "import sys; sys.path.insert(0,'scripts'); import triage_totals as T; \
      f,_=T.run('4117-fy-2011-annual-town-report',{76,77}); print(len(f), sum(not t.settled for _,t in f))"

Measured, by row:

| what | rows | size of the miss |
|---|---|---|
| `GRAND TOTAL PRINCIPAL` / `GRAND TOTAL INTEREST` / `TOTAL DEBT`, p76r63-65 and p77r59-61 | 29 checks | $0.4M to $13M -- whole blocks, not digits |
| `TOTAL MASS WATER POLL TRUST`, p77r6/10/14/22/30 | 5 | $47,803 to $13.4M |
| `TOTAL MASS WATER POLL TRUST`, p76r14 | 1 | $200 -- a real misread, cleared by the second reader (25,888 read for 25,688) |

**What the data shows:** 34 of the 35 misses are thousands to millions of dollars, so they are not
misread digits. **A hypothesis, not tested:** the block a total closes on is wrong for this layout
-- the grand totals sum the wrong set of rows, and the 19-column table (one column per future
fiscal year) has cells Textract places on the wrong row. Opening PDF 76 and listing which rows
each grand total should sum would settle it.

## Why it matters for the next report

Every report prints a debt schedule. Run unattended, the review will put that report's debt pages
in the register as `printed_error` suspects -- claims that the town's arithmetic is wrong -- when
the defect is ours. Nothing public is written without `--accept`, so this is noise, not harm; but
it buries any real error in the register under 20-odd fake ones.

## What to do when the next report is Textracted

1. Run `python3 scripts/report_review.py STEM`, then look at the register rows on its debt pages
   (labels `GRAND TOTAL PRINCIPAL`, `GRAND TOTAL INTEREST`, `TOTAL DEBT`, `MASS WATER`).
2. Fix the cause in `validate_totals.py`, not the symptom: teach VALIDATE the debt-schedule block
   structure (which rows a grand total sums), and test it on FY2011 PDF 76-77 AND the new report.
   The bar: FY2011's 35 fall to the one real misread, and the existing answer key still holds
   (`python3 scripts/test_validate_totals.py`, `test_page_integrity.py`).
3. Cheap guard worth adding in `triage_totals.py` either way: a miss larger than some share of
   the total itself is a grouping failure, not a printed error. Do not let it be called
   `printed_error`.
4. **Do not clear these by sending them to the second reader** (`reconcile_totals.py --limit N`).
   About $0.25-0.40 API-equivalent each, and it fixes these pages only; the next report pays again.

## Not this hole, but nearby

- The 2000 report's town-meeting pages (PDF 105-106) print two columns of text side by side and
  the reading order across them is wrong; their open totals are the same kind of noise.
- The 2000 report's debt schedule (PDF 89) has `$` read as `8`; TRIAGE settles most of them.
- Cross-column row identities (beginning + additions - deductions = ending) are not checked. On
  the 2000 Colonial trust funds they were what showed the printed total, not the rows, was wrong
  -- worth adding as a third witness.

## 28 October 2026: the guard is in, and two instrument defects found on the 2010 report

- **Guard (step 3 above) added** in `triage_totals.py`: a miss larger than `GROUPING_SHARE` (10%)
  of the printed total, with no single-digit explanation, is `grouping`, never `printed_error`.
  FY2011 PDF 76-77: 35 open, now 33 grouping, 1 misread, 1 printed_error (was 19 printed_error).
  The block structure of the debt schedule (step 2) is still NOT taught to VALIDATE.
- **`page_integrity.document()` picked the wrong cache** for any two reports with the same page
  count (2010 and 1997, both 100 pages), so 2010's register rows were filed under the 1997 PDF and
  `validate_totals.word_confidence()` read another document's confidences. It now looks the PDF's
  own sha up in the manifest first, and for a file outside the archive matches the cache by its
  LINE text. This is also what had broken `test_validate_totals.py`'s Colonial case once the 52
  new caches arrived.
- **`validate_totals.parse()` reads the accountant's `fwd` mark** (`$81,153.16 fwd`, read as
  fwd/twd/1wd): fifty such cells in the 2010 report were unparseable.
