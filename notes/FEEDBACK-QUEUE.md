# Feedback queue — raised while reading, not yet done

TJ reads the generated pages and gives feedback faster than it can be acted on. Losing an
item because it arrived mid-task is the failure this file exists to prevent. Anything here
is **agreed and not yet built**; when it ships it moves to the bottom with the commit that
did it.

Nothing in this file is a claim about the data. It is a work list.

---

## Open

### 4. The four never-extracted families — balance sheet first

*Raised 7 Sept 2026, on `notes/reference/EXTRACTION-GAPS.md`.* TJ: *"we need all that
info. the balance sheet seems critical."*

Four table families are surveyed in every annual report, counted, recorded in
`annual_report_contents`, named in `extraction_plan` — and no dataset holds any of them.

| family | years | figure rows | why it matters |
|---|---:|---:|---|
| `balance_sheet` | 14 | 488 | **TJ's priority.** What the town HOLDS, against the flow tables the archive already has. Everything here measures money moving; nothing measures what is sitting still, at the town level. |
| `enterprise` | 15 | 954 | Water, sewer, solid waste, PEG. The **control case** — the only part of the town where money in and money out can both be traced. |
| `town_meeting` | 15 | 924 | What was VOTED, article by article. We hold the appropriation, which is the output of these votes, not the decision. |
| `tax_rate` | 15 | 216 | The number every resident actually feels. |

**Do the balance sheet first**, and expect it to be harder than special revenue rather
than easier: `pdf_tables.py` names the combining balance sheet specifically as a page
where plain extraction mode wins and layout mode recovers **zero** of its 61 money
tokens. The read-from-the-page method now proven on special revenue does not care about
that, which is the argument for using it here too.

The check to reconcile against is the balance sheet's own identity — assets = liabilities
+ fund equity — plus whatever totals each year prints. Establish that BEFORE transcribing
a year, not after; a table with no independent check is not worth reading into a dataset.

### 3. $26m + $2m does not visibly equal the $27m spent

*Raised 7 Sept 2026, on `school-money-flow.html`.* TJ: *"$26m + $2m, I expected 'what the
schools actually spent' to be the 26+2, but its $27. I'm not sure how to understand
that."*

The cards currently invite that subtraction and then do not explain it. Both halves of the
answer are real and neither is on the page:

- **Not all of the budget was spent.** Card 1 is an appropriation — permission to spend —
  and card 3 is spending. The unspent remainder of the appropriation is a genuine figure
  and it is nowhere in the four cards.
- **Money in is not money out, per fund.** Card 2 counts revenue *received*; card 3 counts
  what was *spent*. A fund can take in more than it spends (the circuit breaker) or spend
  more than it takes in (school lunch, drawing a balance down). Card 4 is where that
  difference comes to rest, but nothing says so.

So the three figures do not reconcile because they are a permission, an inflow and an
outflow — three different kinds of quantity, which was deliberate — and the page never
says what closes the gap.

**Fix:** show the bridge explicitly rather than leaving the reader to attempt the sum.
Budget + funding in − spent = what is left, split into *appropriation not spent* and
*fund balances*, and check that it actually adds. If it does not add, say what is missing
rather than adjusting a card until it does — the mixed bases (period 12 for the
appropriation, period 9 for the funds) mean it may genuinely not close, and that is a
finding rather than an error to hide.

---

## Done

### 2. The top metrics did not tell a story — `1613275`..HEAD, 7 Sept 2026

*Raised and cleared 7 Sept 2026.* The four cards on `school-money-flow.html` were
`appropriated / spent / sitting unspent / town spent beyond`, which is a list of true
things in no particular order. TJ set the order, and the order is the argument:

| | card | figure |
|---|---|---|
| 1 | The school budget | departments 300 **and 301**, as voted |
| 2 | Funding beyond the budget | own-fund revenue, plus grants floored by their spending |
| 3 | What the schools actually spent | appropriation spending plus fund spending |
| 4 | Unspent, sitting in accounts | quieter styling — context, not the point |

Each card is **one** quantity: a budget, then money in, then money out, then a balance.
That rule is here because the opposite shipped once — `$335,856 through the revolving
fund` was revenue *plus* spending added together.

Two things fell out of building it. Card 1 first read `$26,247,474`, because `0100-301`
was queried at `P_ACCT` (period 12) where only `P_DEPT` (period 9) carries
department-level rows — the appropriation silently lost $40,000 and the card went on
looking right. It now **fails** rather than returning zero. And grants book no FY26
revenue at all, so what they provided is unknown; their spending is used as a floor and
labelled as one, because a floor is not a measurement.

### 1. A fund name on the right-hand side did not read as a use of money — `1613275`..HEAD

*Raised and cleared 7 Sept 2026.* TJ: *"putting a 'fund' on the right is awkward. I can't
understand how to read it."* The right column answers *what the money was spent on*, so
`After school fund` named a place money sits where a use of money belongs — and implied a
destination we do not know.

The right-hand label is now **derived from the left box**, its fund number stripped, plus
the word *spent*: `1305 After School Activities Fund` → `After School Activities Fund
spent`. Derived rather than typed again, so the two sides cannot drift; and `spent_label`
**raises** if stripping the number changes nothing, because a silent no-op would leave the
old confusing label in place and nothing would fail.

It also exposed an older defect. Fund names were cut at a hard 26 characters, which was
invisible while the right column was hand-written and surfaced immediately as
`Extended Day Revolving Fun spent` once the string was used twice. Trimming is now on a
word boundary. `SCHOOL FACILITIES USE REVOLV` is **not** ours — that is the town's own
truncation in the ledger, and it is printed as published.
