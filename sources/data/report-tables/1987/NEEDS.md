# 1987 edition: what the shared code needs (for the integration pass)

Edition: calendar 1987 annual town report, `4486-1987-annual-town-report.pdf`, 76 pages. Tables were
read on the 40 pages `find_financial_pages.py --list 1987` picked; 29 of those returned at least one
table (40 tables). The other picked pages (pp12, 15, 18, 24, 50, 53-55, 59, 64, 65, ...) are
department prose and warrant-article prose with dollar figures in sentences; Textract found no table
on them. Every hand check below was computed from the cells in `build/textract/out/`, not typed from
the page.

`edition.json` carries `unlabeled_subtotals: true` and `rounding_tolerance_usd: 1`.

## FINDER MISSES

None: no page without cells prints a money TABLE. Lines on a page that WAS sent but that Textract
returned outside any table are listed under 4 below.

## ROSTER PAGES

None. The 1987 report prints no staff roster (searched: faculty, staff, teachers, principal,
custodian; p73 `STAFF` is one paragraph of prose). `rosters.csv` is header-only.

## 1. Accountant schedule (pp31-36): five marks the reader does not accept after a first-column figure

The first column of pp31-36 prints `$amount` followed by a one-word mark: `fwd`, `RF`, `rct`, `ret`,
`Ewd`, `RCT`, `TR` (cells like `$2523.60 rct`, `$5400.00 RF`). Of these the reader accepts `fwd`
(`V.FWD`) and, as a result, `ret`, `rct`, `Ewd`, `RCT` and `RF` cells are not read as figures, so the
row's later figures shift one column to the LEFT: `$2523.60 rct | $2523.60 Town Record Gift Fund |
$122.46 | $122.46 | | $2401.14` comes out `v1=122.46 v2=122.46 v3=2401.14` (a WRONG value in v1, not
an absence). Counts of tagged first-column cells on pp31-36: fwd 40, RF 24, rct 19, ret 17, Ewd 2
(an OCR of `fwd`), RCT 1.

Proof that this is the whole defect: the column of first-column figures sums, with the tags
accepted, to 10,476,375.72, to the cent, the printed GRAND TOTALS figure (p36 r29). The reader's
column sums 9,400,537.94, short by 1,075,837.78 = ret 557,018.75 + rct 305,624.01 + RF 130,000.00 +
RCT 72,461.00 + Ewd 10,734.02 (also exact to the cent). The label cell's embedded TOTAL FUNDS
AVAILABLE ties to 10,476,375.72 too; TOTAL EXPENDED (9,942,030.90), BALANCE REVENUE (36,141.69) and
BALANCE FY 88 (498,203.13) tie.

**Change:** accept any of `fwd rct ret Ewd RCT RF TR` (case-insensitive, `E` for `f`) as a mark on a
first-column figure in the accountant-schedule layout, as `fwd` is accepted. Pages 31-36: 219 of 223
accountant-schedule rows are `check failed` today for this reason alone.

AMOUNT EXPENDED (col 3) is short of its printed total by exactly 8,580.00: two rows print TOTAL
EXPENDED larger than AMOUNT EXPENDED with no transfer line shown beside them -- p32 r3 Voting
Machines (17,420.00 against 18,000.00, a 580.00 gap) and p32 r21 Police Department (350,514.20 against
358,514.20, an 8,000.00 gap; Textract confidence 72.1% on that cell). The other TR-explained gaps
(p31 r18/19, p34 r3/4, p36 r1/2) are printed as their own `TR` figures and are counted. A cell witness
should decide p32 r21 (is the leading digit `8` read as `0`?) and p32 r3; nothing here corrects them.

## 2. Omnibus budget (pp51-52): a split TOTAL label and a split row

Textract returned `TOTAL GENERAL | GOVERNMENT - 100 SERIES | $ 432,974.` as col 1 = `TOTAL GENERAL`,
col 2 = `GOVERNMENT - 100 SERIES`. The reader treats `TOTAL GENERAL` as an identifier and the series
subtotal as an item row, so the pooled LIST TOTAL (stated_total 8,502,150) sums items and subtotals
together: 17,003,392. By hand: the 81 item rows (code | name | amount) sum to 8,500,401; the Montachusett
Regional Planning line is printed over two lines (`841 | MONTACHUSETT REGIONAL PLANNING |` then
` | COMMISSION ASSESSMENT | $ 1,749.`) and adds 1,749: **8,502,150, the printed TOTAL BUDGET VOTED, to the
dollar.** Each of the eight series subtotals also ties to its items (432,974; 721,922; 5,515,512;
689,231; 104,785; 132,527; 253,760; 649,690). `TOTAL SCHOOL: $5,450,000.` (p52 r13) is a further
subtotal inside the 300 series (5,405,000 + 45,000). `TOTAL MONT. REG. PLANNING COMM. $ 1.749.` prints
a full stop for the comma.

**Changes:** (a) a row whose col 1 begins `TOTAL` is a subtotal, not an identifier; (b) a code-only
row (`841`) is a label, with the amount on the next row; (c) `$ 1.749.` read as 1,749 under the
whole-dollar rule. 92 omnibus rows are `check failed` today.

## 3. Treasurer's reconciliation, Revenue Sharing Fund (p30 table 2)

The roll-forward is correct on the page: 77,047.52 + 49,065.37 = 126,112.89; less 50,000.00 =
76,112.89 = the cash-book balance printed twice. The emitter reports `opening + net receipts
126,112.89 != 125,178.26 (off 934.63)`: 934.63 is 77,047.52 - 76,112.89, i.e. it takes the row
`BALANCE JUNE 30, 1987 PER CASH BOOK` (r12) as the opening balance because its label begins
`BALANCE JUNE 30`. **Change:** the opening balance is the row `BALANCE JUNE 30, <year before the
period>`; a `PER CASH BOOK` row is the closing balance. The map gives this table its own family,
`cash-reconciliation-revenue-sharing`, so its ledger balance is never summed with the General
Fund's (p28). 22 rows `check failed` for this reason; the General Fund reconciliation (p28)
`checked`, 9 rows.

## 4. Lines below a table on p36 that no table holds (UNREAD)

p36's table ends at `GRAND TOTALS`. Below it the page lines print, outside any table: `Petty Cash
Advances $3185.00 rct`; `Revenue Cash Invested $9180388.83`; `REFUNDS` (1986 Real Estate Taxes $876.97,
$16577.73; Tax Title $175.00; 1985 MVE $162.00; 1986 MVE $3945.15; 1987 MVE $667.27; Rescue Wagon
$139.28; Veterans Benefits $2325.00; total $24868.40); `TRUST & INVESTMENTS` disbursements (Arts
Lottery Council $4372.08; Energy Conservation $1000.00; Library Book Interest $1440.34; Library All
Purpose Interest $208.35; George Wakefield Scholarship $1500.00; Playground Fund $2300.00; School
Prize Fund $60.00; total $10880.77). These are the Treasurer's cash disbursements by kind. Not
landed (no table, rule 13c: they are on the page). **Change if wanted:** a lines-based reader for
`REFUNDS` / `TRUST & INVESTMENTS` blocks, or a records-style table dataset.

Observed, not explained: the 26 agency-fund rows on p37 sum to 2,015,485.10, which is 10,880.77 below
the page's printed 2,026,365.87 (p37 r27, on the same line as `Gas Permits $10.00`), and 10,880.77
is the p36 TRUST & INVESTMENTS total. Whether one explains the other is not established.

## 5. Receipts (pp29-30): the GRAND TOTAL is on the next page

The detailed statement is two side-by-side column blocks (`groups:2`) over two pages; the one
GRAND TOTAL ($8,395,750.78) and the SUMMARY OF RECEIPTS are at the foot of p30. The receipts
emitter checks each TABLE on its own and cannot read the SUMMARY: 36 rows `check failed` (`accounts
sum 8,089,760.29 vs the printed GRAND TOTAL not read` on p29; `8,701,941.29 vs 8,395,750.78;
categories ... sum 0.00` on p30). By hand: the eight SUMMARY categories (taxes and excises
4,893,507.09; charges for services 1,633.00; fees 63,828.07; licenses and permits 110,737.62; state
revenue 2,979,159.63; intergovernmental 77,902.33; miscellaneous 91,160.48; other financing sources
177,822.56) sum to **8,395,750.78**, the GRAND TOTAL, and the category TOTAL column of pp29-30 (cols 3
and 7) sums to 8,395,750.78 as well. **Change:** pool the receipts tables of a page SPAN against the
one GRAND TOTAL and read the SUMMARY block, as 1991 NEEDS asked for the split-table case.
Printed arithmetic that does not hold, on the page: `PRO FORMA TAXES $647.23 | $447.23` (p29 r7,
SUB TOTAL and TOTAL differ by 200.00), `INTEREST 1987 REAL ESTATE $7373.36 | $7373.34` (r17).

## 6. Debt repayment schedule (p40): `$` read as a digit in six cells (CELL WITNESS CANDIDATES)

Each cell lacks its `$` and reads as a longer number. The correction that makes the printed
TOTAL close is shown; none is applied here.

| cell | read | closes as | why |
|---|---:|---:|---|
| p40 r33 col 4 (TOTAL SCHOOL REMODELING) | 127645 | 27645 | 19,000 + 8,645 |
| p40 r37 col 11 (TOTAL AMBULANCE) | 176603 | 76603 | 65,000 + 11,603 |
| p40 r41 col 11 (TOTAL FRONT END LOADER) | 184168 | 84168 | 71,580 + 12,588 |
| p40 r47 col 3 (GRAND TOTAL INTEREST) | 544745 | 44745 | column interest sum |
| p40 r47 col 5 (GRAND TOTAL INTEREST) | 125080 | 25080 | column interest sum |
| p40 r48 col 4 (TOTAL DEBT) | 145641 | 45641 | 32,861 + 112,780 |
| p40 r48 col 11 (TOTAL DEBT) | 11028519 | 1028519 | 818,120 + 210,399 |

(p40 r25 col 9 `35640` is `$35,640`, a missing `$` only.) With these the nine year columns and the
TOTAL column close on principal, interest and total. Debt by issue (p39) closes on every column
(`checked` 20 rows) with one source-side oddity: STREET BETTERMENTS 1985 prints total payments
interest `$90002` (p39 r7 col 11) where paid previous years 5,003 + due 3,999 = 9,002; the column
TOTAL 878,338 is the sum WITH the 90,002, so the town's own total carries the figure.

## 7. Enrollment (p66 table 2): MIDDLE SCHOOL total

`TOTAL/MIDDLE SCHOOL` 9/02/87 prints 437; the grade rows read 327 (off 110). The reader's triage
calls it grouping (a whole row missing from the block). Not examined further; 4 rows `check failed`.

## 8. New datasets / families this edition proposes (rule: reuse an existing name if it is the same quantity)

- `report-auditor-cash-schedule` (families `cash`, `investments`): the AUDITOR's schedule of cash and
  investments, opening and closing balance by fund with the composition by bank (p9). It is a
  second printing of the stock `treasurers-cash` (p28) holds, by a different officer and with an
  opening balance; kept separate because `treasurers-cash` has one column and the Treasurer's
  roll-forward is another quantity. If the integration pass would rather fold the closing composition
  into `treasurers-cash`, the 6/30/87 figures are identical (the seven investment accounts plus
  four cash lines are the eleven accounts of p28 r1-r11). The rows are `no check` (checks=none: the
  opening amount is merged into the label cell on p9 table 2, so it is a string, not a figure).
  Observed on the page: the General Fund investments are 1,454,631.89 in the line above the
  composition, and the composition's own printed total is 1,454,631.49 -- the seven accounts sum to
  1,454,631.49, so the two printed totals are 0.40 apart.
- `report-tax-levy-history` (family `tax-levy-history`): the Town Clerk page's tax levy by fiscal year,
  FY1982-FY1988, with a percent increase. The percent column recomputes from the levy column on all
  six rows (2.50%, 3.08%, 5.66%, 5.08%, 6.18%, 9.18% against 2.5, 3.1, 5.7, 5.1, 6.2, 9.2).
- `report-agency-funds` (family `agency-funds`): money the Town held for others at the close
  (payroll withholdings, union dues, guarantee deposits), 26 lines, no header; last line prints two
  figures in one cell.
- family `trust-fund-accounts` and family `trust-fund-rollforward` in `report-trust-funds`: the
  1987 trust book (pp42-44) prints, per fund, the bank accounts holding it (bequest and income) and
  then a Balance July 1, 1986 + interest/gifts - purchases = Balance June 30, 1987 roll-forward. A
  FOURTH trust layout: never summed with `trust-funds-book`, `trust-funds`, `trust-investment-accounts`.
  `trust-fund-rollforward` closes on its unlabelled subtotals (21 rows `checked`). Fund balances
  tie to the summary (p42 table 1: 10 funds = 300,926.23 = p10 = the balance sheet's trust and
  agency TOTAL FUND EQUITY, p38: $300,926).
- family `cash-reconciliation-revenue-sharing` in `report-treasurers-cash-reconciliation` (see 3).
- the exemption clauses (p8) land in the existing `report-property-tax-exemptions` /
  `exemption-clauses` (named by 1991); the amounts are in prose beside each clause, so the rows
  carry labels only.

## 9. Unlanded tables (not financial, no dataset)

`3/1-3` (about the town, office hours, meeting schedule), `56/1` (by-law fine headings in warrant
prose). Officials (14/1 water committee, 17/1 zoning board, 66/1 school committee) land in
`report-officials`; police activity (19/1-2) in `report-dept-activity`.

## What was done with each item (integration pass, 29 October 2026)

- **Names.** `report-auditor-cash-schedule` -> `report-auditors-cash-schedule`, families `cash-by-fund` (9/1)
  and `investments-by-fund` (9/2). `report-tax-levy-history` -> `report-valuation`, family
  `tax-levy-history`, as 1988 p30 (2000-2010 print the same quantity in `report-valuation`).
  `report-agency-funds` kept (new).
- **1 accountant marks.** APPLIED as opt-in `accountant_marks` (1991 prints `RF` too). The APPROPRIATED
  FORWARD column now closes on GRAND TOTALS 10,476,375.72. The pages stay unproven on the AMOUNT EXPENDED
  column, 8,580.00 short of its printed total -- the two rows the worker named (p32 r3, p32 r21). No row
  identity reaches them (the header cells are merged), so the cell witness cannot locate them.
- **2 omnibus.** APPLIED: opt-in `id_column_words` (the line-number column holding `TOTAL GENERAL`,
  `PROTECTION`), and `$ 1.749.` read by the always-on full-stops rule. 0 of 99 omnibus rows fail; pp51-52
  proven. The code-only row (`841`) needed nothing more: it lands with no amount and its amount lands on
  the next line, as printed.
- **3 PER CASH BOOK.** APPLIED, always on: a second `BALANCE` line is not the opening; the fund's own
  `REV.SHARING LEDGER BALANCE` is its ledger; the map's family is kept. 31 of 31 rows `checked`.
- **4 lines below p36.** SKIPPED: a lines-based reader for REFUNDS / TRUST & INVESTMENTS is a new reader,
  not an integration fix. The figures are in the page lines and searchable.
- **5 receipts.** APPLIED as opt-in `receipts_span` (pp29-30 one statement, SUMMARY read). The accounts sum
  to 8,395,950.80 against GRAND TOTAL 8,395,750.78: off 200.02, which is the two places the page prints a
  SUB TOTAL that its own TOTAL does not carry (PRO FORMA TAXES 647.23 | 447.23, INTEREST 1987 REAL ESTATE
  7373.36 | 7373.34). `check failed`, correctly; not adjusted.
- **6 debt `$` as a digit.** CELL WITNESS: three cells located (p40 r33 c4, r37 c11, r41 c11) and accepted by
  the blind scripted reader, `witnessed-cells.csv`. The four GRAND TOTAL / TOTAL DEBT cells are not pinned
  by two identities and stay as read. p39's MIDDLE SCHOOL row prints TOTAL PAYMENTS PRINCIPAL 1,390,000
  against 1,275,000 + 65,000; the column total carries it, so it is the page's figure.
- **7 enrollment.** Not a code item; unchanged.
