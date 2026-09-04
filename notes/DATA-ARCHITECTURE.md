# The data architecture

**What each report can answer, and why.** Three tiers and a supporting shelf. `CLAUDE.md`
is the rules; `notes/SCHEMA.md` is the database; `notes/MUNIS-REPORTS.md` is how to ask for
a MUNIS report by name. This is the model those three assume and none of them states.

**Nothing here is a source.** It is a claim about the archive. Check anything load-bearing
against the repo.

Started 4 September 2026.

---

## The one idea

**A tier is not how detailed a document looks. It is how far actual spending can be
followed in it.**

That distinction is the whole model, and it is counter-intuitive in exactly one place:

> **The final school budget is Tier 1 even though it has line items.**

It carries category codes, and un-coded line items by title, and about 350 of them. It is
still Tier 1, because it is the **plan** and has no concept of spend. Line detail with no
spend side cannot be followed anywhere. What a document *shows* and what it lets you
*trace* are different properties, and only the second decides which questions it answers.

The tier is stored on every row of the completeness matrix as `tier`, with a `tierNote`
saying why — so the model is in the data and not only in this file.

---

## Tier 1 — Top-level aggregates and totals

*How much. Never which.*

### The final school budget

The plan. Category codes over grouped lines, un-coded line items by title, and **no
actuals at all**. Tier 1 for that reason and no other.

What it gives: what was intended, line by line, at every stage a document was published —
proposed, approved, and prior years restated inside a later document.

What it cannot give: anything about spending. A line that rose tells you the plan changed
and nothing about what happened.

### General fund expenditures, totals — `glytdbud`, Print totals only **TRUE**, EXPENSE

High-level aggregates across departments. **The school is two rows, 300 and 301.**

What it gives: the highest level of actual spend against the school budget for the period.
The overall numbers can be compared.

What it cannot give: any traceable detail. No school budget line can be compared to
anything in it.

    FY2026 period 9, expense, department level ....... 67 rows for the whole town

---

## Tier 2 — Categorical totals: codified and categorised lines

*Where the budget meets the spend.*

### General fund expenditures, details — `glytdbud`, Print totals only **FALSE**, EXPENSE

Individual coded accounts per fund. Department 300 prints its accounts under codes like
`2710`, and the district prints `2710 - Guidance` over a group of budget lines.

**This is the join, and it is the only one.** 41 of the budget's 45 function codes are
shared with the ledger; 270 accounts carry a code. It is why the department reconciles to
$1.93 and why a category can be called over or under at all.

    FY2026 period 12, expense, account level ......... 635 rows

**Tier 1 and Tier 2 are the same report with one setting changed.** That is why
`account.level` records what a report was actually *run* at rather than what it is called,
and why one cell of the completeness matrix is amber where the one beside it is green.

**And the format decides it too.** The spreadsheet export carries the whole coded account:

    0100-3-300-2710-04-4-65-1-511024

The printed PDF drops it. The category comparison holds for FY2026 period 12 alone because
that is the one report that arrived as a spreadsheet.

---

## Tier 3 — Full resolution

*Where the money actually went, and when.*

### Account Details — the journal

The only way to match actual spend against an account. Keyed to the fund. **We hold it for
one fund only** — 1301, the athletics revolving fund, 277 rows — and that single document
is how we know what this report can answer.

What only Tier 3 gives:

- **Individual fund spending and turndown.** Nothing else reaches it.
- **RevTrak income**, which appears here and nowhere else.
- **Money spent straight out of a fund account** without being transferred first. That is
  how the athletics fund works. It may be how Chapter 70, school choice and the grants
  work too, and **no other report would show it** — which is why this is the tier the
  standing questions keep arriving at.

There is no reason to think it cannot be produced for every fund. It almost certainly can.

**What it still does not give.** Where the money actually went is heavily under-described:
no tags, no useful descriptions. A journal line names an account and an amount and a date
and leaves the purpose to inference. Tier 3 is the end of what the town's system records —
it is not the end of what somebody would need to know.

### Also Tier 3, and never held

- **Line-item transfers, with authority.** `ledger_snapshot` carries a cumulative
  transfers column, so the net movement is visible and the movements are not.
- **Purchase orders closed after the year's close.** The step that moved FY25's surplus
  from $582,115.44 to $603,885.97.

---

## Supporting documentation

*Real, and not joinable to the rest. Each fills a gap in the story.*

These are not a lower tier. They are off the axis: nothing maps them onto a school budget
line, and that is a property of the documents rather than a gap in our reading of them.

### Revenue report, details — `glytdbud`, Print totals only **FALSE**, REVENUE

The only view of every way the town brings money in, categorised. **Chapter 70 appears
here**, as `0100-01001-450600`.

No way to map it to anything in the school budget as it stands. 0 of 222 revenue accounts
carry a function code; state aid shares no org code with any expense account; there is no
Chapter 70 fund, unlike every grant, which has one.

### Special revenue

The titled grants and revolving funds with balances and totals — TITLE I, TITLE V, #240.
61 funds, of which 21 had FY2026 activity.

**A total report.** No individual items, no lines, no transfers. It says a fund spent
$229,398 and never what on.

### End of Year Financial Report, by fund

Supporting by shape, load-bearing by importance. Totals by fund is the one thing that
separates a grant paying for staff from the town paying for them — rule 11's entire
subject. Filed by the district with DESE every year; neither publishes the filing.

### Grant awards, and DESE all-funds per pupil

Award totals listed inside the district's own budget documents — the award is not the
spending and never says which line it paid for. And DESE's outside view, per pupil by
function, counting costs the school budget does not carry.

---

## What this predicts, and it keeps coming true

Every standing question in `CLAUDE.md` is a question that **needs a tier we do not hold**:

| question | needs |
|---|---|
| How grants and state funding map onto budget lines | Tier 3 per fund, or the EOYR |
| Whether budgeted positions were filled | below Tier 3 — nothing records it |
| Out-of-district placement counts | not in any tier; not a financial record |
| The FY26 year-end figures | Tier 2 at period 13 |

And the reverse holds. The one genuinely new thing this project has been able to say — that
the district's budget and the town's books meet at the category and stop below it — came
from the single Tier 2 document that happened to arrive as a spreadsheet.

**So the model is also the request.** What to ask for is whatever raises a year's tier, and
the two drafted requests are exactly that: `glytdbud` at Print totals only N for four years
(Tier 1 → Tier 2), Account Details for the school funds (→ Tier 3), and the EOYR
(supporting, and the one that unblocks the most).

---

## Two axes, not one

The tiers say **what a document can answer**. They do not say whether we have it, and
neither of those says whether what we have agrees with itself. Three questions, and the
completeness matrix spent two revisions collapsing them into one.

| axis | question | who can change it |
|---|---|---|
| **tier** | how far can spending be followed in this report | nobody — it is what the report is |
| **holding** | do we have it, for this year, at the grain we need | a records request |
| **quality** | do the documents we hold agree with each other | **nobody** |

The third is the one that keeps getting mistaken for the second. 24 cells of the matrix
are held in full and carry a disagreement, because the town published a year more than
once and revised lines in between. Nothing is missing. No request would settle it. Drawn
as a shade of *incomplete* it reads as a gap the requests failed to close — which is how
it looked until the two axes were separated.

So the matrix draws holding as the square and quality as a small `≠` beside it, and
counts them separately: **59 obtained, of which 24 carry a disagreement**, against exactly
one cell that is genuinely partial — Q3 FY2026, held as a department rollup where account
level was needed. That last one is the only not-green cell in the top half a request can
actually close.

---

## Where this lives in the code

- `scripts/export_ledger.py` — `TIERS`, and `tier` / `tierNote` on every row of the
  completeness matrix. The data room shows the tier on each row and in every hover.
- `notes/MUNIS-REPORTS.md` §2 — the same three tiers, MUNIS reports only, written first.
  It has no supporting shelf and its "what we hold" column is typed prose.
- `sources/analyses/connecting-the-budget.md` — the Tier 2 join, measured.
- `notes/SCHEMA.md` — `account.level` is Tier 1 versus Tier 2, in the schema.
