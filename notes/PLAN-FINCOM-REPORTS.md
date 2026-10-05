# Reports to build from the Finance Committee data

Agreed with TJ, 5 October 2026, after the delivery was read into tables (37 of 37 tasks, see
`notes/generated/FINANCE-COMMITTEE-INGEST.md`). Not started: the week's usage was spent on the
reading. Build each one the model-driven way (CLAUDE.md 7d): a generator, a payload, a verifier,
conclusions through `scripts/conclusions.py`, charts as components, persona review before it is
linked. Every figure below comes from the datasets; every *why* is a hypothesis (rule 7).

The draft that already exists and these build on: `sources/analyses/department-budgets.md`
(unlisted), from `scripts/build_department_budgets.py`.

---

## Town

### 1. The town's own deficit, year by year
**Question:** does the town side have level-service gaps the way the schools do, and how big?
**Data:** `town-budget-fy26-fy27.csv` (FY27 request, balanced, Tier 1, Tier 2), the FY27 impact
statements (text), `town-budget-versions.csv` (FY24-FY25 preliminary vs voted), `gl-history.csv`.
**Method:** per department, requested/level-service vs adopted, by year where a request exists;
the FY2027 season in full.
**Limit:** level-service requests are held for FY24-FY27 only; earlier years are a registered gap
(money-gaps: "what a level-service budget for each town department would have cost").

### 2. Where the town's money actually goes: budget against spending, FY2010-FY2024
**Question:** which departments spend what they are given, which leave money unspent every year,
and which are topped up mid-year?
**Data:** `gl-history.csv` (original, transfers in/out, revised, actual, every account).
**Measured already:** highway maintenance left 27.4% of its final budgets unspent over FY10-FY24;
legal 16.1%; the schools 1.0%; snow removal spent 51.5% above its starting budgets (allowed by
law). Revised exceeds original + transfers by an unexplained residual every year -- registered.
**Limit:** FY2025 actuals are part-year; never use them.

---

## The schools' other money (the FY2024 year-end ledger, every fund)

Source: `fincom-ledgers.csv`, report `fy24-ytd-school` -- MUNIS glytdbud, FY2024 period 13,
46 funds, 461 account lines (fund x org x object), budget and actual per line, revenue lines
included. No transactions, vendors, positions or fund balances. FY2025 exists only part-year
(37 funds, July-January); FY2023 only for the general fund. Pair with `eoyr-schedule3.csv`
(spending by fund and function, FY23-FY24) for a second year.

### 3. The school budget beyond the vote
**Question:** how much do the schools spend that Town Meeting never votes on, and on what?
**Measured:** FY2024 general fund 22,499,823.26; all other funds 4,641,071.23 = 17.1% of school
spending; 59% of the other funds' spending is under payroll objects.
**Say plainly:** outside the vote is lawful and on the town's books; what is missing is
visibility in the budget residents vote on.

### 4. Who is paid outside the voted budget
**Question:** how much payroll runs through grants and revolving funds, of what kind, in which
programs?
**Data:** objects 51xxxx outside fund 0100 -- the ledger's own labels separate grant
instructional (519997), grant non-instructional (519998), revolving (519999), stipends,
administrators; the org code carries the program/building.
**Pair with:** `school-staff-fte.csv` (FTE by DESE job code, district-wide) and the rosters.
**Limit:** dollars, not people or posts (rule 11). One person can be paid from two funds. Which
fund pays which POST stays a registered gap; the remedy is the district's position control report.

### 5. The grant cliff
**Question:** ESSER III paid 785,625 in FY2024 and is one-time federal money. What replaced it?
**Data:** FY24 period 13 against the FY25 part-year ledger (same funds), and the general fund's
FY25 lines. Tests, in part, the registry's open question about the FY2025 general fund jump.
**Limit:** FY25 is part-year; say so on every figure.

### 6. Special education, every source together
**Question:** what does special education cost when the circuit breaker, IDEA and the general
fund are added together?
**Measured:** circuit breaker spent 466,296 and IDEA (#240, FY23 award) 532,661 in FY24; the
general fund's private tuition line ran 464,031 under budget over FY22-FY24.
**Hypothesis to test, not to state:** that the other funds absorb tuition the general fund
budgeted. The object codes can test it line by line.

### 7. Are we spending what comes in? (and do the revolving funds pay their own way?)
TJ, 5 October 2026: *"are we spending what we are earning? If we take in a ton of money from fees
and grants, are we actually spending it?"*
**Measured (special revenue funds, all together, as each annual report prints them --
`special-revenue-printed-totals.csv`):** money in exceeded money out in 11 of 13 years, FY2011-FY2023;
the balance carried grew from 2.69M forward into FY2011 to 10.03M carried out of FY2023, faster
after FY2020. The schools' FY2024 outside funds went the other way: revolving and gifts spent
383,599 more than came in (a drawdown); grants' gap is mostly reimbursement timing.
**Not established:** why the balance grew -- federal COVID money paid upfront (ARPA, timing),
fees above program cost, or restricted money. Settled by the PER-FUND balances in
`special-revenue-funds.csv` (stored as printed per page: read `columns_as_printed`, not
`fund_balance`, which is empty for most rows -- a first query read the wrong field).
**Also register:** FY2022 carried 8,645,489 but FY2023 opens at 8,663,350.
**The constructive finding, if it holds (rule 8):** a fee fund carrying years of surplus could
lower the fee or pay costs the general fund now carries.

**Question:** for each fee-funded fund, receipts against spending in the same year.
**Measured:** lunch 827,319 in / 837,499 out; school choice 80,540 in / 214,516 out.
**Caution:** spending above receipts means a drawdown of earlier balances for a revolving fund,
but is usually TIMING for a grant (reimbursed after it spends). The ledger holds no balances;
the annual reports' special revenue tables do.

---

## The key that places every school dollar by building and program

Found 5 October 2026. A school org code is a compression of the account string: `S0511061` =
`S0` + segments 51-1-06-1 of `0100-3-300-2330-51-1-06-1-519015`. Grant and revolving org codes
keep the last three of those segments: `13082061` = fund 1308 + 2-06-1. So one key places
general fund, grant and revolving money alike.

| segment (in `gl-history.csv` account) | meaning | evidence |
|---|---|---|
| 3 | DESE function (2305 teachers, 2330 paras, 2210 principals...) | known; NOT carried into grant/revolving org codes -- use `eoyr-schedule3.csv` for fund x function |
| 5 | BUILDING: 1 district-wide; 2, 4, 5, 6 the four schools | four separate principal-office line sets (2210) under 2/4/5/6 |
| 5 = 6 | the High School | graduation, accreditation and every athletics line sit only there |
| 5 = 2, 4, 5 | Primary, Turkey Hill, Middle -- WHICH IS WHICH IS A HYPOTHESIS (teacher budgets ascend 2->4->5, as grade would) | closes with the district's MUNIS location-code list, one line in a records request |
| 6 | PROGRAM (08 school office, 11 paras/aides, 06 special education...) | descriptions grouped under each value |
| 7 | salary/expense split (1, 2, 4) | pattern |

### 8. What each part of Lunenburg really costs -- town departments AND schools
TJ, 5 October 2026: *"the combined appropriated budgets (for school AND for Town) with their spent
funds outside the budget."*
**Three layers per department / school / program, shown stacked, NEVER blended into one figure:**
1. **Appropriated** -- the voted general fund, spent (`gl-history.csv`, both sides). Observed.
2. **Spent outside the vote** -- grants, revolving, special revenue. Observed. Schools: FY24 period
   13, account x building x program (the key above). Town: fund-level receipts and disbursements
   per year from the annual reports (`special-revenue-funds.csv`, `special-revenue-printed-totals.csv`),
   attributed to a department by fund name -- OUR mapping, labelled as such.
3. **Carried elsewhere** -- retiree health, county retirement, building debt, facilities, booked in
   another department. Needs an allocation method: OURS, labelled, shown separately.
**The asymmetry, said on the page:** the schools' outside money is account-level, the town's is
fund-level, so the town's will look lumpier -- a property of the data, not of the town. Remedy (a
registered gap): the town's `glytdbud` report for its special revenue funds.
**Traps the generator must handle:** interfund transfers netted out (or they count twice);
enterprise funds (sewer, PEG Access) shown separately, not inside a department.
**For the schools, also:** whether outside money is substitution or supplement (report 5's test;
Title I and IDEA must legally supplement, not supplant -- ESSER did not have to).
