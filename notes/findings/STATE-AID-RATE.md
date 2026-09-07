# The state aid growth rate — decision D10

`model/finance.py` grows state aid at **2.0% a year**. `sources/analyses/show-your-work.md`
grades that `BARE`: *"Nothing. No stated source and no derivation."* This is the
investigation that was supposed to fix that. **It is evidence, not a change.** Nothing in
`model/` or `sources/analyses/` was touched.

Every figure below is either a row of `notes/findings/state-aid-budget-series.csv` —
which `scripts/build_state_aid_series.py --check` regenerates and `check_generated.py`
runs — or a named line of a named document. The rates the note states are asserted inside
that generator (`RATE_CLAIMS`), so a figure that drifts stops the build rather than going
on being published here.

---

## 1. What this establishes

**A like-for-like series exists, and it is long.** Twenty-three consecutive fiscal years
of the town's own **budgeted** total cherry sheet aid, FY2005 to FY2027, budget stage
throughout, out of the town's own revenue/expenditure worksheets. That is the series the
2.0% has to be argued against, and until now nothing in this project held it.

**The 2.0% is below every long-run measurement of that series and above the most recent
short one.** Median annual step over all 22 steps: **2.7277%**. Over the last ten:
**2.6218%**. Compound FY2005→FY2027: **3.5724%**. Compound FY2019→FY2027: **2.8112%**.
Compound FY2023→FY2027: **1.9144%**.

**The recommendation is 2.75% a year, with moderate confidence, and it is a smaller change
than it looks.** It is the median annual step of the town's own budgeted aid, it is within
0.1 point of both the ten-year median and the FY2019→FY2027 compound rate, and moving the
model from 2.0% to 2.75% narrows the FY2033 gap by **$323,838** and the six-year cumulative
gap by **$1,090,588** — about 7%. State aid is 23.8% of the FY27 omnibus, so a
three-quarter-point change on it moves whole-town revenue growth by 0.18 points.

**The single largest quantity that cannot be measured is not growth, it is error.** The
Division of Local Services' own `Excess/Shortfall Cherry Sheet Receipts (CL#8)` line puts
Lunenburg's cherry sheet estimate error between **−$390,814 (2024)** and **+$327,281
(2023)** across five years. That range is roughly ±3% of aid, which is larger than any
annual growth rate measured here. **A one-year forecast error on this line is bigger than
a year of its growth**, and no rate fixes that.

**The town publishes two state aid growth rates that its own worksheets do not reproduce.**
The FY2027 Town Meeting booklet says *"From FY13-FY23 state aid increased at an annual rate
of 5.3%, but in the last four years, it has slowed to approximately 1.4%"*
(`sources/town-budget/text/3765-town-meeting-booklet-including-warrant.txt`, line 338).
The same town's `Subtotal State Aid` line gives **4.5660%** for FY2013→FY2023 and
**1.9144%** for FY2023→FY2027. The booklet does not say which quantity it measured.
Registered in `money-gaps.csv`.

**What none of this establishes** is in §6, and it is the important half.

---

## 2. The series, and what each one measures

| # | series | span | stage | quantity | rate it implies |
|---|---|---|---|---|---|
| A | Town's `Subtotal State Aid` | FY2005–FY2027, 23 yrs | **budget** | all cherry sheet receipts | median step **2.7277%**; CAGR **3.5724%** |
| B | `annual_report_receipts`, `status='checked'` | FY2014–FY2022, 5 points | **actual** | Chapter 70 only | **4.4653%** compound |
| C | `free_cash_proof` CL#8 | 2021–2025, 5 yrs | actual **minus** estimate | all cherry sheet receipts | not a rate — an error band |
| D | `v_state_aid` (FY2026 ledger, p09) | one year | budget, revised **and** received | 45xx general fund objects | not a rate — a within-year pair |
| E | `dese_radar` / `dese_measure` | FY2009–FY2025 | — | **holds no aid measure at all** | none |

**A and B are not comparable and must never be differenced.** A is budget to budget; B is
actual to actual. A covers the whole cherry sheet; B covers Chapter 70, which is 82.0% of
it in FY2027 ($9,349,335 of $11,404,917 — `model/taxbase.CH70`, and the FY2027 booklet's
own narrative at line 335). A rate measured from B applied to the model's base would be rule 1's exact
error — a rate that is partly growth and partly the step between an estimate and a receipt,
applied to a quantity 22% larger than the one it was measured on.

**A is the like-for-like one.** The model's `state_aid` field is a budgeted estimate of the
whole cherry sheet, and A is a series of budgeted estimates of the whole cherry sheet.

**E is worth stating because it is where everybody looks first.** `dese_radar` holds 2,982
rows over FY2009–FY2025 for seven districts, and thirty distinct measures — enrolment,
demographics, per-pupil expenditure by function, MCAS, teacher and paraprofessional FTE,
average salary. **Not one of them is Chapter 70 or any other aid figure.** DESE publishes
Chapter 70 per district per year; this archive does not hold it.

---

## 3. Series A, in full — and read year by year (rule 6)

`notes/findings/state-aid-budget-series.csv`. Amounts are the `Subtotal State Aid` line of
the town's own worksheets; the CSV carries the document, the sheet or line number, and the
printed column heading for every row.

| FY | budgeted aid | step | FY | budgeted aid | step |
|---:|---:|---:|---:|---:|---:|
| 2005 | 5,233,166 | — | 2017 | 7,998,947 | +6.4% |
| 2006 | 5,370,530 | +2.6% | 2018 | 8,972,793 | **+12.2%** |
| 2007 | 5,913,294 | **+10.1%** | 2019 | 9,074,334 | +1.1% |
| 2008 | 6,296,172 | +6.5% | 2020 | 9,308,929 | +2.6% |
| 2009 | 6,638,386 | +5.4% | 2021 | 9,308,929 | **0.0%** |
| 2010 | 6,015,508 | **−9.4%** | 2022 | 9,440,371 | +1.4% |
| 2011 | 5,982,319 | −0.6% | 2023 | 10,500,128 | **+11.2%** |
| 2012 | 6,001,062 | +0.3% | 2024 | 10,793,838 | +2.8% |
| 2013 | 6,718,759 | **+12.0%** | 2025 | 10,682,086 | **−1.0%** |
| 2014 | 6,855,401 | +2.0% | 2026 | 11,034,268 | +3.3% |
| 2015 | 7,194,650 | +4.9% | 2027 | 11,327,588 | +2.7% |
| 2016 | 7,518,492 | +4.5% | | | |

**This is not a smooth line and no single compound rate describes it.** Four of the
twenty-two steps are double digits (FY2007, FY2013, FY2018, FY2023); one is −9.4%
(FY2010); one is exactly zero (FY2021). Between the steps the series moves 0–4% a year.
**A compound rate is therefore hostage to whether its window contains a step**, which is
why every window that starts on FY2023 lands near 1.7–1.9% and every window that contains
FY2018 or FY2023 lands near 3.5–4%:

| window | compound rate | contains a step year? |
|---|---:|---|
| FY2005→FY2027 (22y) | 3.5724% | four |
| FY2005→FY2019 (14y) | 4.0100% | three |
| FY2013→FY2023 (10y) | 4.5660% | two |
| FY2017→FY2027 (10y) | 3.5405% | two |
| FY2019→FY2027 (8y) | 2.8112% | one |
| FY2019→FY2026 (7y) | 2.8330% | one |
| FY2022→FY2026 (4y) | 3.9773% | one |
| **FY2023→FY2026 (3y)** | **1.6677%** | **none** |
| **FY2023→FY2027 (4y)** | **1.9144%** | **none** |
| FY2025→FY2027 (2y) | 2.9771% | none |

**The median annual step is the robust statistic here**, because it is not moved by whether
a window happens to straddle a policy event: **2.7277%** over all 22 steps, **2.6218%**
over the last ten, **2.7972%** over the last five. Three windows of very different length
agree to within 0.18 of a point, which none of the compound rates do.

### The two stage seams, stated rather than smoothed

FY2005–FY2017 come from one workbook at the **town manager recommended** stage; FY2018 is a
**recap** column; FY2019–FY2024 are **final budget** columns; FY2025–FY2027 are the FY2027
Town Meeting booklet's own columns. Two things make the stitch checkable rather than
assumed:

- **Five documents restate the same prior years, and they agree to the cent.** FY2022
  appears in two worksheets, FY2023 in three, FY2024 in two. The generator refuses to write
  if any two disagree.
- **The FY2019 seam is visible and small.** The FY19 workbook's own `FY19 BUDGETED` column
  says 9,034,019; the FY2020 worksheet's `FY19 FINAL BUDGET` column says 9,074,334 — 0.45%
  apart, the state budget having been enacted in between. The series uses the later stage.

### The definitional break, and the source's own proof of it

The FY2027 Town Meeting booklet counts `School Choice Receiving` tuition inside its cherry
sheet `Total Receipts`; every earlier worksheet's `Subtotal State Aid` does not. **The
booklet prints both, so the bridge is arithmetic and not judgement**
(`3765-town-meeting-booklet-including-warrant.txt`, lines 2436–2448):

```
                                    FY25 BUDGETED   FY26 BUDGETED   FY27 PROJECTED
Education                             9,266,673       9,476,620       9,726,003
Unrestricted General Government Aid   1,222,658       1,330,763       1,349,272
Veterans Benefits                        52,875          51,599          66,218
Exemp: VBS and Elderly                   56,888          92,232         102,040
State Owned Land                         48,606          48,606          49,237
Library                                  34,386          34,448          34,818
                                     ----------      ----------      ----------
  = the older Subtotal State Aid     10,682,086      11,034,268      11,327,588
School Choice Receiving                  94,912         104,835          77,329
Total Receipts                       10,776,998      11,139,103      11,404,917
```

`10,776,998 − 94,912 = 10,682,086`, and **10,682,086 is exactly what the 2024 Annual Town
Meeting booklet prints as `Subtotal State Aid` for FY2025** in an entirely different
document. The generator asserts that equality and refuses to write without it. The
published series uses the older, school-choice-excluding definition throughout.

### Where the growth is, FY2025→FY2027

| component | FY2025 | FY2027 | rate | share of FY2027 |
|---|---:|---:|---:|---:|
| Education — Chapter 70 **and other school receipts** | 9,266,673 | 9,726,003 | +2.45%/yr | 85.3% |
| Unrestricted General Government Aid | 1,222,658 | 1,349,272 | +5.05%/yr | 11.8% |
| Exemp: VBS and Elderly | 56,888 | 102,040 | +33.93%/yr | 0.9% |
| Veterans Benefits | 52,875 | 66,218 | +11.91%/yr | 0.6% |
| School Choice Receiving | 94,912 | 77,329 | −9.74%/yr | 0.7% |
| State Owned Land | 48,606 | 49,237 | +0.65%/yr | 0.4% |
| Library | 34,386 | 34,818 | +0.63%/yr | 0.3% |

**`Education` is not the same thing as Chapter 70.** The booklet's narrative (line 335)
puts the FY2027 Chapter 70 Governor's figure at **$9,349,335**; the `Education` cherry
sheet line above is **$9,726,003**. The $376,668 between them is charter tuition
reimbursement, Smart Growth and offset receipts — school money, not Chapter 70. Chapter 70
alone is 82.0% of the Governor's `Total Receipts` and **78.7%** of the base
`model/finance.py` actually grows. Rule 11's paragraph in `CLAUDE.md` was wrong about this
for months in the other direction; it is worth not being wrong about it in this one.

**One line decides this rate.** Education is 85.3% of the total; UGGA is 11.8%; everything
else together is 2.9%, and the two fastest-growing lines in the table are two of the three
smallest. Rule 4 applies to a revenue line exactly as it does to a spending one: rank by
share times rate, never by rate.

---

## 4. Series B and C — the actual side, kept separate

**B. Chapter 70 received.** `annual_report_receipts` holds thirteen Chapter 70 rows,
FY2011–FY2022, and **`status` splits them three ways**. Only five are `checked`:

| FY | received | status |
|---:|---:|---|
| 2014 | 5,516,107 | checked |
| 2015 | 5,605,872 | checked |
| 2017 | 6,351,257 | checked |
| 2018 | 7,272,505 | checked |
| 2022 | 7,823,618 | checked |

Compound FY2014→FY2022: **4.4653%**. Read step by step it is not a trend either — +1.63%,
then +6.44%, then **+14.50%** in FY2018 alone, then +1.84% over the four years to FY2022.
The eight unusable rows are unusable for real reasons and two of them are instructive:
FY2019 and FY2021 hold `7.53` and `7.77`, an extractor having lost the thousands
separators, and FY2020's row is printed as `FEES CH 70 SCHOOL AID` — two columns run
together. **A series built across all thirteen would be a measurement of our extractor.**

**C. The estimate error, which is the state's own subtraction.** CL#8 on the DLS free cash
proof is the only place in this archive where a receipt is subtracted from an estimate by
somebody entitled to do it:

| year | Lunenburg CL#8 | as % of that year's budgeted aid |
|---:|---:|---:|
| 2021 | +240,260 | ≈ +2.6% |
| 2022 | +120,947 | ≈ +1.3% |
| 2023 | +327,281 | ≈ +3.1% |
| 2024 | −390,814 | ≈ −3.6% |
| 2025 | +149,455 | ≈ +1.4% |

Mean +89,426 over five years — close to unbiased — with a spread of $718,095 between the
best and worst year. **Lunenburg's swings are the largest of the nine towns in the file**
(Ayer's five years run −36,221 to +29,052; Shirley's −45,083 to +13,729). Whether that is
a fact about Lunenburg's aid or about how Lunenburg estimates it is not established here.

**D. The FY2026 ledger, one year, three stages on one row.** `v_state_aid` is the only
place in this archive holding `budgeted`, `revised` and `received` for the same accounts:
Chapter 70 budgeted 9,229,410, received 6,870,136 at period 9 (74.4% of a year, at 75% of
the way through it); UGGA budgeted 1,316,438, received 987,327 (75.0%). It is a like-for-
like pair for one year and it says the town is being paid on schedule. It cannot make a
rate.

---

## 5. The recommendation

> **2.75% a year, moderate confidence.** Range for scenario work: **1.5% to 3.5%**.

**Why 2.75%.** It is the median annual step of the town's own budgeted aid over 22 years
(2.7277%), it is within 0.11 of a point of the same median over the last ten steps
(2.6218%), within 0.07 of the last five (2.7972%), and within 0.09 of a point of the
FY2019→FY2027 compound rate (2.8112%). Five different ways of asking the question over three different
spans land between 2.62% and 2.81%. Nothing else in this investigation converges like that.

**Why not the compound rate.** 3.5724% over 22 years is real and it is the wrong statistic
for a five-year forward projection, because it is carried by four policy step-years and a
projection that assumes one arrives on schedule is assuming a legislature.

**Why not 1.9%.** FY2023→FY2027 is four years that happen to contain no step. Rule 6:
*a three-year rate off a small base is not a trend*, and the same applies to a four-year
rate that starts the year after a 11.2% jump. It is the right number for *"what has
happened lately"* and the wrong one for *"what happens next"*.

**Why moderate and not high.** Three reasons, and the third is the real one.

1. Series A's last two points are one stage earlier than the rest (FY2027 is `PROJECTED`,
   on the Governor's budget). The enacted budget came in **$471,121 above** it.
2. The CL#8 band (§4) is ±3% of aid — larger than the rate itself. This rate is a central
   tendency around a quantity that misses by more than its own growth every single year.
3. **Chapter 70 is 78.7% of the model's base and it is a formula, not a trend.** Foundation enrolment,
   the required local contribution and the minimum-aid increment are the inputs, and they
   move independently of anything measured here. A past growth rate is a summary of what
   the formula produced under the rules that then applied — including the Student
   Opportunity Act ramp, which is what most of FY2023's +11.2% is. **Nothing in this
   archive tests whether the formula's next five years look like its last five.** The
   document that would speak to it is DESE's Chapter 70 district summary, and it is only
   ever published one year ahead.

**What it is worth.** Running `finance.project(years=6, assumptions=dict(state_aid_growth=r))`:

| rate | FY2028 gap | FY2033 gap | six-year cumulative |
|---:|---:|---:|---:|
| 1.40% (the town's own "last four years") | 719,266 | 4,890,895 | 16,034,779 |
| **2.00% (current)** | **680,870** | **4,640,257** | **15,181,593** |
| **2.75% (recommended)** | **632,876** | **4,316,419** | **14,091,005** |
| 3.57% (FY2005→FY2027 compound) | 580,403 | 3,948,569 | 12,867,315 |

**The grade should move from `BARE` to `derived`, not to `given`.** 2.75% is our
calculation off the town's published series, not a figure anybody published.

---

## 6. What this does NOT establish

- **That aid will grow at any rate.** §5, point 3. This is a measurement of 23 budgets, and
  Chapter 70 is a formula whose inputs are not modelled here.
- **That the growth measured is growth in aid rather than in what aid is defined to
  include.** The school-choice bridge caught one definitional change *because the booklet
  printed both sides of it*. There is no reason to think it is the only one in 23 years,
  and the older worksheets print one line where the newer ones print seven.
- **That any of this is money for schools.** Rule 11. `Education` is a cherry sheet
  category, not an appropriation to the district, and `connecting-the-budget.md` establishes
  that the state aid accounts share no organisation code with any expense account, 0 of 222.
  A rate on aid is a rate on what the town does **not** have to raise. It is not a rate on
  any cost, and nothing here says what any of it paid for.
- **That the model's FY2027 base is a clean gross figure.** `model/finance.py:84` reads
  `state_aid=11_404_917 + 471_121`. The first is the Governor's gross cherry sheet
  `Total Receipts`. The second is recorded in `fy27-and-the-override.md` as **net**:
  *"+$471,121 net (Ch.70, charter/choice receiving tuition, Smart Growth, UGGA,
  vets/elderly exemptions; offset by higher charter assessments)"*. A gross figure and a
  net figure are being added. Nothing in this archive splits the second, so the true gross
  FY2027 receipt estimate is not established. Registered in `money-gaps.csv`.
- **That the town's own published rates are wrong.** They are unreproducible from the
  town's own worksheets, which is a different claim. The booklet may be measuring Chapter
  70 alone, or net aid, or the Cherry Sheets themselves — it does not say. Registered.

---

## 7. Rule 14 — what the 2.0% is absorbing, and what moving it would make findable

**A residual is a slush fund.** The 2.0% has no derivation, which means nothing about it
was ever chosen to be *right* — it was chosen to be plausible, and everything downstream
of it has been quietly benefiting from that. Four specific things become the next question
the day it moves.

**1. The revenue wedge is frozen, and it is $1,753,006.** `finance.project` computes
`town_available` as levy + excluded debt + aid + receipts **minus a constant**:

```
34,133,581.28 + 2,199,352.52 + 11,876,038 + 3,508,024 − 49,963,990.19 = 1,753,005.61
```

That constant is cherry sheet **assessments**, the Assessors' overlay, and the levy
directed to capital, and it is held at its FY2027 value in every projected year while every
term around it grows. Cherry sheet assessments alone are $1,069,349 of it — 61.0%. **So the
2.0% has been doing double duty as a net-of-assessments rate**, and correcting it upward
without deciding what the wedge does is a change to two things at once.

The direction here is not what I expected and it matters: **the town's cherry sheet charges
have been falling, not rising.** `Subtotal CS Charges` reads 1,301,877 in the FY2019 final
budget column (`a91-fy20-preliminary-budget-revenue-expense-sheet-pdf.txt`, line 43) and
1,181,609 in the FY2025 column (`a157-2024-may-annual-town-meeting-booklet-pdf.txt`, line
1902) — about −1.6% a year. The `Choice/Charter Assessments` line inside it falls from
1,002,610 (FY2023 final) to 934,947 (FY2024 final) to 865,150 (FY2025), all three printed
on line 1899 of that same booklet. **Freezing the wedge is therefore conservative, not optimistic**, and a corrected
aid rate would make that visible instead of leaving it inside a rate nobody derived. It is
the second-order item this whole exercise surfaces, and it has never been examined.

**2. `local_receipts_growth = 1.0%` is the other `BARE` rate, and it is next.** At a 2.0%
aid rate the two BARE rates are of a piece — two round numbers, neither derived. Move one
onto measured ground and the other stops being a matched pair and starts being an outlier.
Local receipts are $3,508,024 of FY27 revenue and the same worksheets that carry
`Subtotal State Aid` carry `Subtotal Receipts`, 23 years of it, in the same columns. **The
series is already sitting in the documents this generator opens.**

**3. The base impurity in §6 stops being invisible.** $471,121 is 4.0% of the model's aid
base, and it is a net figure inside a gross one. While the growth rate is undefended, a 4%
question about the base reads as pedantry. Once the rate is derived to two decimal places
off 23 budgets, a base that is not the quantity the rate was measured on is the obvious
next defect — and it is exactly the shape of every error rule 13 catalogues.

**4. Whether school aid should be projected separately from town aid.** The model carries
one `state_aid` field, so the 2.0% applies to the whole cherry sheet. §3 shows the
components moving at −9.7%, +0.6%, +2.45% and +5.05% a year. At a 2.0% rate that spread is
noise inside an assumption nobody defends. At a derived rate it is the question: **the
Education line and the UGGA line grew at different rates over FY2025–FY2027, and 85.3% of
the total is the slower one.** `fy28/src/model/rates.ts:561` already has a `ch70OnlyGrowth`
helper for exactly this decomposition, and nothing currently drives it from a measurement.

**And the general warning.** Correcting this rate does not merely improve a number. It
shrinks a residual, and shrinking a residual presents the bill for everything that residual
was paying for. Expect items 1 and 3 to arrive immediately.

---

## 8. Method, and how to re-run it

```
python3 scripts/build_state_aid_series.py           # write the series
python3 scripts/build_state_aid_series.py --check   # fail if it is stale
python3 scripts/check_generated.py                  # it is registered there
```

The generator refuses to write on six conditions, listed in its docstring. The two worth
knowing: the FY19 budget handout workbook's year labels sit on **two** header rows and
three of its twenty columns are a projection, an **ACTUAL** and a duplicate override
column, all three of which are asserted by cell and excluded by name; and the series is
only publishable while the school-choice bridge ties to the cent.

**Documents.** All seven are in `sources/town-budget/`, all seven carry a
`www.lunenburgma.gov` address in `sources/town-budget/index.csv`, and the FY19 handout is
the workbook itself rather than a rendering of it:

| document | what it gave |
|---|---|
| `a53-fy19-budget-handout-for-annual-town-meeting-xlsx.xlsx` | FY2005–FY2019, one sheet, row 19 |
| `a91-fy20-preliminary-budget-revenue-expense-sheet-pdf` | FY2018 recap, FY2019 final |
| `a79-fiscal-year-2021-revenue-expense-worksheet-may-7-2020-pdf` | FY2020 final |
| `a72-fy23-preliminary-budget-revenue-expense-sheet-pdf` | FY2021, FY2022 final |
| `a189-fy24-revenue-expense-worksheet-february-16-2023-pdf` | FY2022, FY2023 final |
| `a138-fy25-town-manager-s-preliminary-budget-recommendation-pdf` | FY2023, FY2024 final |
| `a157-2024-may-annual-town-meeting-booklet-pdf` | FY2025 town meeting |
| `3765-town-meeting-booklet-including-warrant` | FY2025–FY2027, by component |

**If the recommendation is accepted**, the follow-on work is: promote
`state-aid-budget-series.csv` into `sources/data/` and the database so `/api/query` can
reach it; add it to `/state-aid`, which currently has to say the 4.47% receipt rate is not
a correction; move the `show-your-work.md` grade from `BARE` to `derived` with this
document as the derivation; and decide the wedge question in §7 in the same commit, because
deciding it later is how a residual gets paid twice.
