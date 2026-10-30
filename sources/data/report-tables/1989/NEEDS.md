# 1989 edition: what the shared code needs (for the integration pass)

Edition: calendar 1989 annual town report, `4488-1989-annual-town-report.pdf`, 84 pages. Tables read on the 37 pages
`find_financial_pages.py --list 1989` picked; 38 tables, all mapped. Hand checks below were computed from the cells.

## 1. Receipts: the spread is two PAGES, pooled per page (p27-p28)
Four label|amount tables (27/1, 27/2, 28/1, 28/2); the one GRAND TOTAL ($9,425,007.82) is the last row of 28/1. Pooling is by
page (`receipts_pool`), so p27 reports "GRAND TOTAL not read" and p28 sums its accounts AND the seven category rows
(28/1 r31-r37: TAXES & EXCISES ... MISCELLANEOUS REVENUE, no `SUMMARY OF RECEIPTS` heading in the cells) -> all 127 rows
`check failed` for a structural reason. BY HAND it ties exactly: the accounts of 27/1, 27/2, 28/1 r1-r30 and 28/2 sum to
$9,425,007.82, and the seven categories sum to $9,425,007.82. Change: pool a spread across consecutive pages when the
earlier page prints no GRAND TOTAL, and treat a run of unlabelled-by-heading category rows ending in GRAND TOTAL as the
summary (else the 7 category rows land as accounts and double the total). Until then those 7 rows (p28) are NOT accounts.

## 2. treasurers-cash refused (p38/2): 0 rows
The accounts sum to $1,282,509 by hand (500+500+55,490+181,071+145-101,071+1,045,114+6,047+2,714+60,467+31,532). The emitter
sums $2,666,089 because the total row `TREASURER'S CASH JUNE 30, 1989` ($1,282,509) is not recognised as a total (its label
matches neither `V.TOTAL` nor `ledger balance`) so it is summed as an account; and the overdrawn
`($101,071) *` cell (whole dollars, footnote mark) is not read as a figure. Change: take `TREASURER'S CASH JUNE` as the
total label and read `($101,071) *`. Map carries stated_total 1282509.

## 3. Debt p40: three printed-total misses are a printing error
WELL SITES STUDY INTEREST TOTAL prints $45,690 (= its TOTAL row), where the four years sum to $5,694. With 5,694 every
interest total sums to the printed GRAND TOTAL INTEREST $149,518 and TOTAL DEBT ties. 4 rows `check failed` (TOTAL SCHOOL
REMODELING, GRAND TOTAL PRINCIPAL, GRAND TOTAL INTEREST x2): TOTAL SCHOOL REMODELING ties by hand (19,000+8,645=27,645 ...
167,580); the validator's block walk grouping fails it, as for the repeated heading `ELEMENTARY SCHOOL REMODELING:` (twice).
`validator_drop_titles` changes nothing here (tried).

## 4. accountant-schedule (p29-p35): 168 rows `no check`, 1 `check failed`
Layout as 1991 p25: Textract merges TOTAL FUNDS AVAILABLE into the PROGRAM NAME cell (`$11314.30 Lake Shirley Study`), figures
unseparated by thousands, columns shift by row, so no identity can be applied from p30 onward (`header_from` 29/1 tried: it
only imports the wrong names `PROGRAM NAME GENERAL GOVERNMENT`). A GRAND TOTALS row is printed (p35 r32): 11,364,143.19 |
11,364,416.19 | 10,986,367.79 | 10,985,367.79 | 73,771.45 | 323,832.66 -- the 11,364,416.19 vs 11,364,143.19 and
10,986,367.79 vs 10,985,367.79 pairs differ by 273 and 1,000 on the page itself. Change: an identity for this layout
(AVAILABLE = APPROPRIATED + FWD; BALANCE = AVAILABLE - EXPENDED) keyed on the label-embedded figure.
p29 `Lake Shirley Study` (`check failed`): reads fwd 11,314.30, available 11,314.30, expended 15,685.70, balance 11,314.30.
11,314.30 + 15,685.70 = 27,000.00, so the available cell is probably 27,000.00 but nothing here tests that
(HYPOTHESIS; a pixel read of p29 would). Left as printed.

## 5. `.28` not read (p65/1, last row)
`Article 6 (Street Numbering) of the 1984 ATM ... .28` -- a figure with no leading digit; the row lands with no value, its
label carrying `Finance Committee recommends approval. VOTED` from the line below. The other 13 rows sum to $33,164.79 by
hand (+ 0.28 = $33,165.07); no total is printed. Change: read `.28` as a figure in a column of amounts with cents.

## 6. New family names (reuse of the settled datasets)
- `report-debt` family `debt-temporary-borrowing` (p39/2: six notes dated 12/22/89 due June 22, 1990). Stage: borrowed, not bonded.
- `report-warrant-article-amounts` family `unexpended-articles-reappropriated` (p64/2, p65/1): unused balances of earlier
  articles used as a source / reappropriated; voted, but not appropriations by line.
- `report-appropriations` family `stm-budget-adjustments` (p64/1): the supplement ALONE (additional appropriation), no NEW TOTAL column.

## 7. New columns / identities
- Trust (p42-p44) rides the 1991 `trust-investment-accounts` identity; 89 of 92 rows check. The 3 `no check` rows are single
  accounts printed without a TOTAL (STABILIZATION FUND, ARTS LOTTERY COUNCIL, PLAYGROUND FUND).

## FINDER MISSES: 0
Every page of the report with a money table was among the 37 sent. Not sent, no money tables: p17 (continuation of the police
motor vehicle list), p66 (election returns), p67/p72 (enrollment: counts only, out of scope).

## ROSTER PAGES
p76 T.C. PASSIOS ELEMENTARY SCHOOL STAFF; p78 MIDDLE SCHOOL STAFF; p79 HIGH SCHOOL STAFF (listed in rosters.csv).
Staff rosters carry no FTE and no funding source; none was sent for tables.

## NOT LANDED (no dataset)
p3 about-the-town facts, office hours and meeting schedule; p13/p14 burials by month (names and ages of the deceased --
the integration pass should decide whether names belong in the public database at all).

## What was done with each item (integration pass, 29 October 2026)

- **1 receipts.** APPLIED as opt-in `receipts_span`: the seven category rows above the GRAND TOTAL are the
  summary (they sum to it while the accounts do too); 120 accounts `checked` against 9,425,007.82.
- **2 treasurer's cash.** APPLIED, always on: `TREASURER'S CASH JUNE 30, 1989` is the total and `($101,071) *`
  reads. 11 accounts published.
- **3 debt printing error.** Not code: WELL SITES STUDY prints 45,690 where its years sum to 5,694. p40 stays
  unproven; a candidate for `page-blocked.csv` in the residue unit.
- **4 accountant identity on a label-embedded figure.** SKIPPED: the columns shift by row once the figure is
  in the label, so an identity would be checked on columns we assigned, not ones the page printed. 1991 has
  the same layout and was left the same way. Lake Shirley Study stays as printed.
- **5 `.28`.** APPLIED, always on (cents with no leading zero).
- **Opt-ins also set:** `accountant_marks` (it reads APPROPRIATED FORWARD figures carrying a mark, 298 -> 315 rows; no row changed status: 129 checked, 1 failed as before) and `recon_net_on_transfer_line` (the reconciliation is unchanged, 10 of 10 `checked`).
- **Privacy.** pp13-14 burials NOT landed, as the worker mapped them; not widened.
- **Rosters.** pp76, 78, 79 dumped and read into `sources/data/rosters/1989-*.json`.
