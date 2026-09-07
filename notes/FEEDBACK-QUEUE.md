# Feedback queue — raised while reading, not yet done

TJ reads the generated pages and gives feedback faster than it can be acted on. Losing an
item because it arrived mid-task is the failure this file exists to prevent. Anything here
is **agreed and not yet built**; when it ships it moves to the bottom with the commit that
did it.

Nothing in this file is a claim about the data. It is a work list.

---

## Open

*(nothing outstanding)*

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
