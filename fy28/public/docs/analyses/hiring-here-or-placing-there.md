# Hiring here instead of placing there



**Whether in-district special education staffing reduces out-of-district placements —
what the data shows, what it cannot show, and what would be needed to model it.**

Scoping note, September 2026.

This is **not a finished analysis.** It is a record of a question the district has put on
the public record, an account of why this project cannot currently answer it, and a list
of what would be required to. Nothing here should be quoted as a finding. Before any of
it reaches the site it needs the steps in `notes/process/WRITING-AN-ANALYSIS.md` and a
verifier that recomputes every figure.

---

## The short version

The district argues that hiring behavioural and special education staff in district avoids
out-of-district placements, which are far more expensive. **The argument is made without a
number attached to it** — no avoided cost, no placement count, no estimate of how much
in-district capacity buys how much avoidance.

Two things moved in the direction the argument predicts. Placements fell from **30 in
FY2015 to 10 in FY2025**. In-district special education spending rose from **$4,865,038**
in the FY25 budget to **$5,466,201** in FY27 Balanced, while the out-of-district tuition
line was budgeted **down from $1,291,293 to $700,142** in a single year.

**That is a correlation between two series and nothing more.** At least four other
explanations fit the same numbers equally well, and this project holds no data that can
separate them. The obstacle is not analytical effort. It is that the quantity the argument
turns on — what it would cost in staff to keep one particular child in district — is not
published by anybody.

---

## Where the claim comes from

On 26 August 2026 the Superintendent put three spending scenarios to the School Committee
for $418,056 of additional state education receipts. Scenario 3 proposed a full-time Board
Certified Behavior Analyst at $119,458, and argued for it this way:

> "BCBAs provide a massive return on investment by stabilizing students with behavioral
> needs within the district. This proactive, specialized care helps the district avoid
> highly expensive out-of-district private placements while building robust internal
> capabilities."
>
> — *Strategic Spending of an Additional $418,000 in State Aid for Education*, slide 17

The slide is headed "Delivering Significant Return on Investment (ROI)" and the figure
given for the return is the words "High ROI". **There is no dollar estimate, no count of
placements expected to be avoided, and no stated basis anywhere in the deck.**

Two things follow, and they point in opposite directions.

**The argument is a serious one and is not this district's invention.** Building in-district
capacity to reduce reliance on external placements is standard practice in Massachusetts
special education finance, and the deck ties it to a real and dated trigger: new DESE
regulations for 2026-27 restricting seclusion and redefining time-outs, which the district
says require "a shift to proactive de-escalation over reactive containment" (slide 16).
That is a mandate arriving with staffing consequences, whatever anybody thinks of the ROI
framing.

**And Scenario 3 is the one that did not pass.** The School Committee chose Scenario 2 —
class size reduction and literacy — on 26 August 2026, and Town Meeting appropriated it on
3 September. So the option built on this argument was the one set aside, which makes the
question live rather than settled: it will be asked again.

**A document stating intent is evidence of intent, not of outcome.** The deck shows what
the district believes and what it proposed. It does not show what a BCBA would have done,
and the district has not claimed otherwise in writing.

---

## What the data shows

Three series, all from budget columns or from the town's own annual reports.

**Placements, 1 March each year**, from the Special Services report in each annual town
report, sourced to SIMS Report 7 (`sources/data/placement-counts.csv`):

| | FY2015 | FY2020 | FY2023 | FY2025 |
|---|---:|---:|---:|---:|
| Collaborative | 9 | 3 | 3 | 6 |
| Day | 15 | 3 | 3 | 3 |
| Residential | 6 | 5 | 1 | 1 |
| **Total** | **30** | **11** | **7** | **10** |

**In-district special education**, budget to budget: $4,865,038 (FY25) → $4,964,329
(FY26) → $5,442,383 (FY27 level service) → $5,466,201 (FY27 Balanced).

**Out-of-district tuition**, budget to budget: $1,164,824 (FY25) → $1,291,293 (FY26) →
$700,142 (FY27), a fall of $591,151 in one year.

So placements fell by two thirds over a decade while in-district spending rose. **Both
statements are facts about published numbers.** Neither is a fact about cause.

---

## What the data does not show

**It cannot establish that in-district hiring caused placements to fall.** At least four
explanations fit the same series:

1. **In-district capacity absorbed children who would otherwise have been placed** — the
   district's argument.
2. **Fewer children needed placement.** Cohorts differ. A count measured on 1 March is a
   snapshot of who is placed, not a measure of who needed placing.
3. **Children aged out.** A residential placement ending because a student turned 22 looks
   identical in this series to one ending because the district built capacity.
4. **The classification or the reporting changed.** The categories are not stable across
   the run: FY2011 and FY2012 report collaborative placements as a subset of day
   placements, and every year from FY2014 reports them as a parallel category. FY2021 has
   a total and no parts.

**And the tuition line cannot be read as the cost of placements**, for two reasons that
are separate and both fatal.

A budget line is **net** — what the town must raise after everything else paying for the
thing is subtracted. Out-of-district tuition is offset by circuit breaker reimbursement
from the state, so the line can fall because reimbursement rose, with no change in what
any placement costs or in how many there are. `build_circuit_breaker.py` carries that
series; the two have never been reconciled against each other.

And the line has no direction to measure. Eleven budgets from FY17 to FY27 range from
$489,918 to $1,291,293, six years up and four down, with a straight-line fit of R² = 0.10.
The model holds it **flat** for exactly this reason — a compound rate off it runs from
-45.78% to +11.78% depending only on which year you start. So the FY27 fall of $591,151 is
a **level** change, and a level change cannot be evidence about a trend.

**Dollars are not children.** The count series and the dollar series measure different
things, and dividing one by the other would produce an average cost per placement that no
document states and that would be wrong in a specific way: it would mix collaborative, day
and residential placements, which differ in cost by a large multiple, and it would divide
a net figure by a headcount.

---

## What would be needed to model it

The model would have to answer: *if the district employs one more person of a given kind,
how many placements of a given kind does it avoid, and what does that save?* That decomposes
into five quantities, of which this project currently holds **none**.

1. **Cost per placement, by type, gross.** Collaborative, day and residential differ by a
   large multiple and the district budgets them as one line. Gross rather than net, so
   circuit breaker reimbursement is visible separately rather than silently inside it.
2. **Which placements were avoidable, and at what staffing.** This is the load-bearing one
   and it is the hardest: it is a judgment made child by child under an individual plan.
   No aggregate published anywhere implies it.
3. **The marginal relationship between staff and capacity.** How many additional
   in-district staff, of which kinds, create room for one additional child of a given need
   profile. The district may hold a working view of this; nothing published states one.
4. **The time profile of each side.** A placement avoided saves for as long as that child
   would have been placed — potentially many years. A position hired is a recurring cost
   forever, and grows at the salary rate. Those are different shapes and a single-year
   comparison of the two would favour whichever is measured over the shorter window.
5. **Which fund pays.** In-district staff may be paid by grants, circuit breaker, or the
   general fund; placements draw on circuit breaker. A saving that moves cost from one fund
   to another is not a saving to the town, and the budget cannot see the difference. This
   is the standing question in `CLAUDE.md` and it constrains this analysis as it
   constrains the special education escalator.

**What would settle it.** The two documents most likely to move this are DESE's End of Year
Financial Report, which separates spending by fund, and the district's own placement-level
cost detail — what each placement is billed at, by type, gross of reimbursement. Neither is
published. Both are askable.

Absent those, the honest sentence is that **the town cannot currently tell whether hiring
in district saves money on placements**, and that nobody in the public record has shown
that it does or that it does not.

---

## Registered as gaps

Per rule 7c, the limits above are registered in `sources/data/money-gaps.csv` rather than
living only here:

- *What does an out-of-district placement cost, by type?* — closes with the district's
  placement-level billing detail, gross of circuit breaker.
- *How much in-district staffing avoids one placement?* — closes with the district's own
  basis for the ROI claim, if one exists in writing.

---

## Sources

| | |
|---|---|
| *Strategic Spending of an Additional $418,000 in State Aid for Education* | Superintendent Jodi Fortuna, email to families 25 August 2026, 4:01 PM, via SchoolMessenger; presented to Town Meeting 3 September 2026. **Basis: `stated`** — a deck the district assembled, not a printout from the books (rule 13a). |
| Special Town Meeting warrant, 3 September 2026 | `sources/town-budget/text/4373-september-3-2026-special-town-meeting-warrant.txt` — Article 1, $418,056.00 |
| Placement counts FY2011-FY2025 | `sources/data/placement-counts.csv`, from the Special Services report in each annual town report, SIMS Report 7, measured 1 March |
| Budget lines | `sources/data/lps-budget-lines.csv`, budget columns only — `fy25_budget`, `fy26_final`, `fy27_level_service`, `fy27_balanced` |
| Classification of special education | `model/sped.py` — the groups, the exclusions, and why the state's function codes cannot draw the line |
