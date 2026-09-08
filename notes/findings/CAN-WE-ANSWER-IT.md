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

### A CORRECTION, made 7 September 2026, before this document was an hour old

**The first version of this said actuals per budget line exist for FY2014–FY2025.** They
do not. `budget_figure` has 3,316 rows carrying `stage='actual'`, and I read that label as
though it meant the accounting system. TJ caught it: *"actuals from budget sheets are not
ACTUALS. Actuals must come from the ledger."*

He is right, and rule 13 lists this exact error in its own table — *"the actuals sheet"*
against *"a forward budget workbook with a column headed ACTUALS."* I reproduced the
example while quoting the rule.

Here is what those rows actually are, classified by `document-basis.csv`:

| basis of the documents behind `stage='actual'` | count |
|---|---:|
| `restatement` — a prior year re-presented inside a document written by the party that spent it | **14** |
| `forward` — proposed, requested, level service, balanced | **2** |
| `ledger` — a figure exists because a transaction did | **0** |

Every one is a district budget book: `fy24-approved-budget`, `fy19-supt-proposed-expense-budget`,
`fy27-budget-projections-as-of-3-16-26`. **Not one is an accounting record.**

### What the archive holds that IS a ledger

Ten documents, and only these reach school spending:

| document | what it covers |
|---|---|
| `town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx` | **FY2026 general fund, all departments** |
| `district-budget/text/fy23-quarterly-budget-update.txt` | **one quarter of FY23** |
| `town-ledgers/account-details/account-details-fy2024/25/26-fund1301.xlsx` | the athletics revolving fund only |
| `town-budget/text/2420-fy23-lunenburg-financial-statements.txt` | FY23 town financial statements |

So: **`ledger_snapshot` and `munis_ledger`, 983 rows each, `fy 2026-2026`.** One year of the
town's books, plus one quarter of FY23, plus one revolving fund.

### Why this changes the verdicts and not the value

A restatement is still evidence. It is the district's own account of what it spent, it is
published, and it is the only multi-year series that exists. **What it is not is
independent.** Three consequences, and they are why the distinction is worth this much
space:

- **It cannot show money moved between lines mid-year.** Approved transfers do not appear
  in a budget document, so a line that was topped up and then spent looks identical to one
  that was budgeted correctly.
- **It is prepared by the party being audited**, from the same system, after the fact. That
  is not an accusation; it is what "restatement" means, and it is why the basis column
  exists.
- **It cannot settle over-budgeting**, which is the question that most needs a ledger — the
  claim is precisely that the budget and the spending diverge, and both numbers here come
  from the budget book.

**Verdicts below are stated against the LEDGER where the question is about what was spent,
and against the RESTATEMENT where that is the honest best and is labelled so.**

### And the grains do not join

An account is the accounting system's unit; a budget line is the district's. `crosswalk` is
deliberately empty because the mapping is an inference, not a record.

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

### 1a. Which lines underspent, and by how much — **FY2026 from the ledger. FY2014–FY2025 only as the district's own restatement.**

**From the ledger — the answer that would survive challenge — you have FY2026 and one
quarter of FY23.** `ledger_snapshot` carries `original`, `revised`, `expended`,
`encumbered` and `available` per account, which is the real shape of this question:
`revised` versus `original` is the mid-year movement a budget document cannot show you.

Everything below FY2026 is the district restating itself. Useful, published, the only
multi-year series there is — and not independent. This runs today:

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

**The page:** `/budget-vs-actual` exists and covers this — and its own caveat block
already says both columns are the town's net general-fund share and that over-budgeted and
did-not-happen are indistinguishable. What it should say more loudly, after this
correction, is which side of the ledger/restatement line each year sits on.

### 1b. Which function codes or areas — **PARTLY**

Line labels are named (`H.S. Guidance Counselor`), so you can group by school and by
category. **Function codes cannot be attached to school lines**: `crosswalk` is empty on
purpose because the district names lines and the town codes accounts, and joining them
would record an inference as a mapping. `v_function_budget_vs_ledger` does what can
honestly be done, through `account.function`, and only for FY2026.

### 1c. What wasn't paid for that previously was paid — **PARTLY, and it is still the strongest version of your question**

Compare `stage='actual'` across years for the same `line_key`: a line that was funded and
then was not is directly visible across twelve years.

**It survives the correction above better than 1a does, and it is worth being clear why.**
The variance question asks *did they spend what they said* — and answering that from the
same document that stated the budget is close to circular. This question asks *what stopped
being funded*, which is a claim about the district's own published account of itself. A
restatement is a perfectly good source for that: it is what they say they spent, year on
year, in their own book.

It also survives the netting problem — a line falling to zero is a fact about the document
whatever was paying for it.

**Nothing has been built for this yet.** It is the single highest-value page still
unbuilt, and it is fully supported by data we hold.

### 1d. Against the district's stated justifications — **PARTLY**

`scripts/search_minutes.py` covers 1,422 documents but **2025 onward only**. So for a
surplus in an earlier year, we can measure what happened and cannot retrieve what was said
about it at the time. Rule 15a's step works for recent years and not for older ones.

---

## Major Objective Two — are the schools over-budgeting?

### 2a. Do they spend what they budget — **NO for FY2014–FY2025, not to audit standard. YES for FY2026.**

**This is the question the correction hits hardest, and it is the one you most want.** The
claim under test is that the budget and the spending diverge. Both numbers in the twelve-year
series come out of the budget book, so the series cannot settle its own question — it can
only report what the district says about itself. For FY2026 the ledger answers it properly.

What the restatement series CAN establish is a **pattern in what the district reports**,
which is worth having and must be labelled as that. Two further conditions:

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

1. **"What stopped being funded"** — a line-level walk across FY2014–FY2025 showing every
   line that went to zero or fell sharply, and when. Built on the district's own
   restatement and labelled as that on every chart, because it is a claim about what the
   district reports, not about what the accounting system recorded. Nothing built; still
   the sharpest version of Objective One.

   **And a fourth, which the correction promoted:** a page that says plainly which years of
   school spending are ledger-backed and which are the district restating itself. Right now
   that is FY2026, one quarter of FY23, and one revolving fund against twelve years of
   restatement — and a reader has no way to tell them apart. `document-basis.csv` already
   holds the classification; nothing renders it against the spending series.
2. **Teacher FTE against out-of-district pupils, seventeen years.** Two published DESE
   series, both real FTE, moving in opposite directions. No page says this.
3. **Multi-year over-budgeting** — the same line, budget against actual, every year, ranked
   by how consistently it underspends. Objective Two, done properly.

And two gaps to register: **school choice and charter sending counts**, and **district FTE
per budget line**.
