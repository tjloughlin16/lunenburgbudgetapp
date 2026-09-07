# Can we answer it? Every question, against what the data actually holds

Written 7 September 2026, by running each question against `sources/data/lunenburg.db`
rather than against memory. Every verdict below was tested with a query; where a query is
quoted, it ran.

**Verdicts used:**

| | |
|---|---|
| **YES** | The data answers it now. A page may or may not exist yet. |
| **PARTLY** | Answerable for some years, some departments, or with a caveat that changes what the answer means. |
| **BOUNDED** | The data constrains the answer without settling it. Saying more would be rule 7's error — a proxy quoted as the thing. |
| **NO** | Nothing published closes it. The remedy is a document, and it is named. |

---

## The one fact that shapes almost every answer below

**Actuals per ACCOUNT exist for FY2026 and nothing else.** `ledger_snapshot` and
`munis_ledger` are 983 rows each, `fy 2026-2026`. That is the town's accounting system,
and we hold one year of it.

**But actuals per BUDGET LINE exist for FY2014–FY2025** on the school side, in
`budget_figure` where `stage='actual'` — 3,316 rows across twelve years. This is the
workhorse for most of what you asked, and it is better than I expected before checking.

The two are different grains and they do not join. An account is the accounting system's
unit; a budget line is the district's. `crosswalk` is deliberately empty because the
mapping is an inference, not a record.

---

## Core objective: a full audit

**PARTLY — and the honest framing is that this is an audit of the SCHOOL side, from
budget documents, not an audit of the town's books.**

What supports it: twelve years of line-level budget against actual, the FY2026 general
ledger, thirteen years of special revenue funds, twelve years of the town-wide balance
sheet, and DESE's all-funds figures FY2009–FY2025.

What does not: nobody has given us the town's general ledger for any year before FY2026.
Everything historical is read off published *reports*, which are summaries prepared by the
people being audited. That is a real limit and it is not a criticism of the town — it is
what a public archive can reach.

**And one rule governs the whole objective (rule 11):** a budget line is what the town has
to raise after grants, fees and state aid have paid their share. It is not what the thing
costs. Any sentence of the form "the schools spend X on Y" needs that qualification or it
is wrong.

---

## Major Objective One — why was there a surplus, and where?

### 1a. Which lines underspent, and by how much — **YES, FY2014–FY2025**

This runs today:

```sql
SELECT b.label, b.value AS budgeted, a.value AS actual, a.value - b.value AS variance
FROM budget_figure b
JOIN budget_figure a ON a.line_key = b.line_key AND a.fy = b.fy AND a.stage = 'actual'
WHERE b.stage = 'proposed' AND b.fy = 2024
ORDER BY (a.value - b.value) ASC;
```

FY2024's largest shortfalls against plan, from that query:

| line | budgeted | actual | variance |
|---|---:|---:|---:|
| ACE Special Ed Paraprofessionals | 30,271 | **−157,886** | −188,157 |
| H.S. Guidance Counselor | 154,209 | 26,266 | −127,943 |
| H.S. Teachers/Regular | 2,899,395 | 2,805,886 | −93,509 |
| P.S. Special Ed Speech Pathologists | 188,547 | 99,055 | −89,492 |
| Maintenance/System Salaries | 309,153 | 237,421 | −71,732 |
| Elementary School Psychologist | 71,367 | 9,385 | −61,982 |

**Read the first row as a warning, not a finding.** An "actual" of −$157,886 is not
underspending; it is an accounting entry — a transfer out, a reclassification, or a credit.
Anyone summing this column without looking at it will produce a number that means nothing.
This is exactly the row whose sign the extractor once ate.

**The page:** `/budget-vs-actual` exists and covers this.

### 1b. Which function codes or areas — **PARTLY**

Line labels are named (`H.S. Guidance Counselor`), so you can group by school and by
category. **Function codes cannot be attached to school lines**: `crosswalk` is empty on
purpose because the district names lines and the town codes accounts, and joining them
would record an inference as a mapping. `v_function_budget_vs_ledger` does what can
honestly be done, through `account.function`, and only for FY2026.

### 1c. What wasn't paid for that previously was paid — **YES, and this is the strongest
version of your question**

Because there are twelve years of actuals per line, a line that was funded and then was not
is directly visible: compare `stage='actual'` across years for the same `line_key`. That is
a better question than the variance, because it survives the netting problem — a line
falling to zero is a fact about the document whatever paid for it.

**Nothing has been built for this yet.** It is the single highest-value page still
unbuilt, and it is fully supported by data we hold.

### 1d. Against the district's stated justifications — **PARTLY**

`scripts/search_minutes.py` covers 1,422 documents but **2025 onward only**. So for a
surplus in an earlier year, we can measure what happened and cannot retrieve what was said
about it at the time. Rule 15a's step works for recent years and not for older ones.

---

## Major Objective Two — are the schools over-budgeting?

### 2a. Do they spend what they budget — **YES, FY2014–FY2025**, with two conditions

Same join as 1a. The two conditions are load-bearing:

- **Compare like with like.** `budget_figure` carries three stages: `proposed`
  (4,110 rows, FY2017–FY2027), `settled` (2,077, FY2016–FY2026), `actual` (3,316,
  FY2014–FY2025). *Proposed* is what they asked for; *settled* is what was voted. Which one
  you compare the actual against changes the answer, and "over-budgeting" usually means
  against what they asked for.
- **A pattern needs several years.** One year's underspend is a story; the same line
  underspending eight years running is a budgeting practice. The data supports the second
  and the page currently emphasises the first.

### 2b. All revenue for the whole town, every department — **PARTLY, and this is the
weakest area relative to how much you want it**

- **FY2026: YES, in detail.** `v_revenue` carries every revenue account with `budgeted`,
  `revised` and `received` — permit fees, fire fees, inflow fees, and the rest, department
  by department.
- **FY2011–FY2025: PARTLY.** `annual_report_receipts` has 1,137 rows by source and year —
  but `status` splits into `checked` / `check failed` / `no check`, and **nothing may be
  aggregated without splitting on it.** For Chapter 70 alone that is 5 checked against 7
  unchecked.
- **Money outside the general fund: YES for FY2011–FY2023** — `special_revenue_read`, 1,882
  rows, thirteen editions that tie to their own printed totals. Published at
  `/money-outside-the-budget`.

### 2c. Follow revenue into how it is spent — **NO. This is the project's central gap.**

Money entering the general fund **loses its origin on arrival**. There is no record, in
anything Lunenburg publishes, connecting a source of revenue to a line of spending. This is
not a hole in our archive; it is how municipal accounting works.

The one place both halves are visible is athletics, and only because the fund is separate.
That is why `/what-sports-cost` exists — it is the control case, not the general answer.
`/what-we-cannot-answer` renders the traceability ladder that says how far each route goes.

---

## Major Objective Three — the all-in cost of each line

**NO, and I want to be blunt about why, because it is the objective most likely to be
believed possible.**

A budget line is **net**. Paras costing $1.5M with $500k of grant against them appear as a
$1M line, and nothing marks the line as net. To produce an all-in cost you would need, per
line: the general fund appropriation (we have it), plus the grants, plus the fees, plus the
revolving funds, plus the circuit-breaker reimbursement — **each mapped to that line**.

**That mapping is not published by anyone.** The district's own workbook shows the problem
in its comments column, asking whether a transportation line already reflects a reduction
for busing fees. The people writing the budget were unsure which of their own lines were
net.

What would close it: **DESE's End of Year Financial Report**, which separates spending by
fund. It is a registered gap. Even then it reconciles at the category level, not per line —
so the honest ceiling is *all-in cost by category*, not by line.

**What we can do instead, and should:** state the appropriation, state what else is known
to touch that area, and say the two cannot be added. `/money-outside-the-budget` is that
shape.

---

## The specific questions

### How much on coaches per year, athletic transportation per year — **YES**

`athletics_history` carries both sides FY2014–FY2026 by item. Athletic Transportation runs
17,000 (FY14) to 127,550 (FY26) on the general fund, with the revolving fund's share
alongside. Published at `/what-sports-cost`. **This is the one programme where the district
publishes an independent statement of cost**, which is why it can be done here and not
elsewhere.

### Teacher and para counts over time — **YES, and better than the project has assumed**

DESE publishes per district, FY2009–FY2025, seventeen years:

| measure | FY2009 | FY2025 |
|---|---:|---:|
| Teacher FTE | 120.2 | **105.1** |
| Student Headcount | 1,739 | **1,563** |
| Total FTE Pupils | 1,833.8 | 1,665.9 |
| Out-of-District FTE Pupils | 83.8 | **97.0** |
| Students with disabilities % | 14.7% | **15.8%** |

**Teacher FTE has fallen 12.6% while out-of-district pupils rose 16%.** That is real, it is
FTE rather than a count of names, and nothing on the site says it yet.

**Administration FTE is NOT held** — DESE's `Administration` is a spending category in
dollars, not a headcount. So *"has admin count increased"* is **NO** from DESE. The staff
rosters bound it: `staff_roster_entries`, 3,815 rows FY2011–FY2025, names and positions, no
FTE. A count of names is not a staffing level.

### Grade-specific staffing trends — **BOUNDED**

The rosters are per school, so primary/elementary/middle/high can be separated. But no FTE,
so a 0.4 music teacher and a full-timer are one row each. DESE's FTE has no grade
breakdown. **You can have grade-level trends in names, or district-level trends in FTE,
never both.**

### The special education para question — **BOUNDED, and much closer than before**

This is the one you couldn't answer. Here it is now:

| FY | sped para $ | Paraprofessional FTE (DESE) |
|---:|---:|---:|
| 2018 | 641,635 | 51.0 |
| 2021 | 920,345 | 59.5 |
| 2025 | 1,244,894 | 67.0 |

FY2018→FY2025: **dollars +94%, FTE +31%.** So headcount explains part and not all.

**Why this is BOUNDED and not YES, and the distinction matters:** DESE's figure is *all*
paraprofessionals district-wide; the dollars are the *special education* para line only.
**Different populations.** Dividing one by the other produces a number that looks like a
unit cost and is not one. It bounds the question — headcount clearly rose, and clearly not
by enough to explain the money — but it cannot separate the remainder into salary steps,
hours, reclassification, or grant money unwinding.

What would settle it: the district's own FTE by line, or DESE's End of Year Financial
Report to remove the grant question.

### How many children left the district each year — **NO, not directly**

School choice sending is not in `annual_report_receipts` under that name and not in
`dese_measure`. What we hold is *enrolment*, which falls for many reasons — families
moving, birth cohorts shrinking, choice, charter. **Enrolment decline is not departure.**
Treating one as the other is rule 7's error with a proxy.

What would close it: DESE's school choice and charter sending reports, per year. Worth
adding to the gap register.

### How many special education students — **YES, as a percentage; PARTLY as a count**

`Students with disabilities % Headcount` runs FY2009–FY2025: 14.7% → 15.8%. Against a 1,563
headcount that is about 247 students, but **that is our multiplication, not a published
count.**

Separately, `placement_counts` gives **out-of-district placements** FY2011–FY2025, from the
Special Services report, measured 1 March, split collaborative / day / residential, with
the parts summing to the stated total. Those are children placed outside the district — a
different and much smaller number than students with disabilities.

### Athletes per sport, cost per sport, cost drivers — **YES, FY2024–FY2026**

`athletics_by_sport`, 960 rows, carries participation and cost by sport and by category:
`Coaches`, `Official`, `Dues & Fees`, `Costs for all 3 Seasons`, plus the fee structure
(`Full Pay`, `2nd Sibling`, `Full Waiver`). Published at `/what-sports-cost`, with cost per
participation by sport.

**Three years only, and that is deliberate** — the district's workbook does not go back
further. Three years is a real trend for a board that will not project two.

---

## What I would build next, given all of the above

1. **"What stopped being funded"** — a line-level walk across FY2014–FY2025 actuals showing
   every line that went to zero or fell sharply, and when. Fully supported, nothing built,
   and it is the sharpest version of Objective One.
2. **Teacher FTE against out-of-district pupils, seventeen years.** Two published DESE
   series, both real FTE, moving in opposite directions. No page says this.
3. **Multi-year over-budgeting** — the same line, budget against actual, every year, ranked
   by how consistently it underspends. Objective Two, done properly.

And two gaps to register: **school choice and charter sending counts**, and **district FTE
per budget line**.
