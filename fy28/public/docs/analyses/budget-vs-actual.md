# Budget versus actual


> **Working state:** `notes/HANDOFF.md` carries the current branch, the open
> decisions and what is established versus assumed. `CLAUDE.md` carries the rules.

Analysis, August 2026. Published here as part of the source archive, and deliberately
**not** part of the app's projection — see the interface rule below for why those are
different things.

Every section below is written twice: **In plain terms** for anyone, and **The evidence**
for anyone who wants to check it. The plain version never states anything the evidence
does not support — it is the same finding in fewer syllables, not a softer one.

---

## Why this is a separate document from the app

The app answers: *how big is the gap, and what would close it?* It is built from the
budgets the town published, and someone can disagree with every assumption in it and still
accept the arithmetic.

This document answers something else: *did the money the town budgeted match the money it
actually spent?*

That second question is a much heavier thing to say out loud. It needs much better
evidence, and if any part of it turns out to be wrong, it hands a critic a free way to
throw out the first question along with it. So the two stay apart, and the traffic between
them runs one way:

> **Something learned here can change a number the app assumes.
> The app never repeats an accusation from here.**

Each finding is tagged **CROSSES** (it changes the app) or **STAYS** (it does not leave
this page).

---

## What we are working from, and what we are missing

**Two sources, and they do not always agree.**

The **FY27 workbook** (`sources/xlsx/fy27-proposals.xlsx`) gives 351 line items with both
halves for FY25, and eight months of FY26. That is what the first version of this document
worked from.

The **mirrored budget documents** (`sources/district-budget-page/`) go back to FY17 and
print actual columns beside budget columns, with each document stating its own column
kinds. `scripts/extract_budget_history.py` reads them, taking only the column a document
itself labels, and the series are published at `/data/total-salaries-history.csv` and
`/data/total-expenses-history.csv`.

Where the two overlap they agree closely: FY25 actuals are identical to the dollar, and
FY23 and FY24 differ by $10,000 and $5,000 on roughly $15.6M of salaries — 0.06% and 0.03%.

### The limit that bounds everything below

**The documents disagree with themselves, by more than the effect this document is trying
to measure.**

Four times in the corpus, a single document prints the same total for the same year twice
and gives two different numbers:

| | year | | | |
|---|---|---:|---:|---:|
| Expenses | FY19 | $6,299,651 | $6,388,738 | $89,087 (1.41%) |
| Expenses | FY22 | $5,920,581 | $6,008,705 | $88,124 (1.49%) |
| Salaries | FY14 | $10,976,481 | $11,044,481 | $68,000 (0.62%) |

In `fy24-approved-budget.txt` the two FY22 expense totals sit 257 lines apart, one after
the salary tables and one after the expense tables, in the same file.

The budget-versus-actual variances measured below run between **0.1% and 0.5%**. The
documents' disagreement with themselves runs to **1.5%**. So a year where a document
contradicts itself cannot be used, and the three years that survive are the three where
nothing does.

This is not an accusation. Summary blocks printed at two points in a long document, one of
them updated and one not, is the most ordinary thing in the world. It is a limit on what
can be concluded, and it is the reason this document is careful about small percentages.

### Two words used below

- **Appropriation** — the amount Town Meeting votes. Not the same as what gets spent.
- **Encumbered** — money promised under a signed contract but not yet paid out.

**What we still do not have:** the town's accounting records, the individual payments, and
the votes that move money between lines mid-year. Everything here compares columns in
budget documents. That is enough to see *that* a number moved. It is not enough to say
*why*, and in several cases below there is an ordinary explanation we cannot see.

**Nothing in this document should be described as anything stronger than a gap that has
not been explained yet.**

---

## 1. "The town spends less than it votes, every year" — that is not what the record shows

### In plain terms

The earlier version of this document said the town votes more than it spends, every year,
and rested it on **one year**. FY25 was the only year where both halves existed.

The archive changed that. The district's own budget documents go back to FY17 and print
actual columns beside budget columns, so the comparison can now be made for several years.
It does not hold.

### The evidence

Three years where the district's documents give both figures and no document contradicts
itself about either:

| FY | voted | spent | difference | |
|---|---:|---:|---:|---:|
| FY20 | $20,795,863 | $20,724,828 | −$71,035 | **-0.34%** |
| FY21 | $21,123,603 | $21,100,143 | −$23,460 | **-0.11%** |
| FY23 | $22,325,309 | $22,436,810 | +$111,501 | **+0.50%** |

Two of the three land within a third of a percent. One is **over**. Against FY25's −3.01%,
these are a different order of magnitude entirely, and they do not point the same way.

### And most of the FY25 figure is not an underspend at all

FY25 is the year the original claim rested on: budgeted $25,321,760, spent
$24,560,511, a shortfall of $761,249. That budget figure comes from the FY27
workbook.

**The district's own FY26 budget document states a different FY25 budget.**

| FY25 budgeted | workbook | FY26 budget document | difference |
|---|---:|---:|---:|
| Salaries | $17,156,461 | $17,188,342 | +$31,881 |
| Expenses | $8,165,299 | $7,695,034 | **−$470,265** |
| **Total** | **$25,321,760** | **$24,883,376** | **−$438,384** |

The FY26 document is internally consistent: it prints FY26 expenses as $9,117,566 and an
18.49% increase, and $7,695,034 × 1.1849 reproduces that. So this is not a typo we can
resolve by inspection. Two of the district's own documents state different FY25 budgets.

Measured against the other one, FY25's underspend is **$322,865, −1.30%** — in line
with the other years rather than an outlier.

**$438,384 of the $761,249 headline — 58% of it — is two sources disagreeing about what
was budgeted, not money voted and left unspent.**

### What we cannot tell

Which figure is right. Both are the district's own. The likeliest ordinary explanation is
that they are drawn at different moments — an appropriation as voted against one revised
during the year — but nothing published says so, and we are not going to guess at it.

### What this means for the app

Nothing, and that is worth stating. Every projection on the site is computed from budget
columns only, and this is a question about the distance between two columns rather than
about how fast a line grows. **It does mean the earlier "three-quarters of a million a
year" framing should not be repeated.** It was one year, measured against one of two
sources that disagree.

---

## 2. That calm 3% is hiding a lot of noise

### In plain terms

A three percent underspend sounds like a quiet year. It was not. Underneath it, individual
lines missed their mark wildly in both directions and happened to cancel out.

One line spent **6 cents of every budgeted dollar**. Another spent **more than double**
what it was given. If you only read the bottom line, you would never know.

This matters because the bottom line is the only number most people ever see.

### The evidence

The extremes in FY25:

| line | budgeted | actually spent | difference |
|---|---:|---:|---:|
| Collaborative tuitions | $460,952 | $28,957 | **−94%** |
| Custodial services | $888,929 | $660,214 | −26% |
| Athletics salaries | $165,280 | $390,254 | **+136%** |
| Special detail / athletic events | $5,000 | $72,864 | **+1,357%** |
| Athletic transportation | $40,000 | $87,822 | +120% |

### What we cannot tell

Districts routinely move money between lines during the year with the proper approvals. A
line that overspent may have been topped up legitimately. We cannot see those movements,
so a big number in the right-hand column is a question, not a verdict.

**STAYS**, except for the piece carved out in section 4.

---

## 3. One cost cannot be predicted — and it is the one nobody controls

### In plain terms

**This is the most important finding here.**

When a child's education plan requires a school the district cannot provide itself, the
town pays another school to take them. The town does not choose the price, does not choose
how many children will need it, and cannot say no.

Look at what happens when you try to budget that:

- In FY25 the district set aside about **$1.16 million** and spent **$732,000**. It
  over-provided by more than a third.
- In FY26 it set aside about **$1.29 million** and had already committed **$1.53 million**
  with four months still to go.

Missed low by 37%, then missed high, on the same line, in back-to-back years.

And here is the part that makes it clear this is not carelessness. Split special education
into its two halves and they behave in opposite directions. **The staff — teachers, aides,
therapists — are budgeted generously and consistently come in under. The out-of-district
tuition is budgeted tightly and blows through.**

The district pads what it can predict and under-provides what it cannot. That is not a
failure of budgeting. It is what happens when a cost is set by how many children turn up
needing help, rather than by anything anyone votes on.

### The evidence

Out-of-district tuition, same line, two years:

| | budgeted | spent or committed | miss |
|---|---:|---:|---:|
| FY25 | $1,164,824 | $732,298 | **−37.1%** |
| FY26 (8 months) | $1,291,293 | $1,530,182 | **+18%** |

The two halves of special education, side by side:

| | FY25 | FY26 at 8 months (67% = on pace) |
|---|---:|---:|
| Staff and services | −6.7% | **57%** — running under |
| Out-of-district tuition | −37.1% | **118%** — already over |

### What we cannot tell

Whether FY26's overrun held through June, or whether a placement ended and it came back
into line. The year-end figures would settle it.

**CROSSES.** This is the best evidence we have that out-of-district tuition should be
modeled as a *range* rather than one number, and it supports the argument on the special
education page from a completely different direction than the growth rate does.

*What to change:* give the tuition line a plausible band instead of a single rate, and say
in the app that this line missed by 37% one way and 18% the other inside two years.

---

## 4. Some lines were set at zero and spent against anyway

### In plain terms

FY25 athletics spent **$281,665 more than it was budgeted** — more than double. That looks
bad until you look at where it came from.

**$155,614 of it was coaching pay on a line budgeted at zero dollars** — while coaches
were, obviously, being paid all year. It was not an overspend so much as a cost that was
not written down.

The following year it was fixed: coaching was budgeted at $159,444, close to what it had
actually been costing. Athletic transportation got the same treatment after overspending —
$40,000 the year it cost $87,822, then $127,550 the year after.

So the honest read is: **a gap in the budget paperwork, found and corrected.** Worth saying
because if you only looked at FY25 it would look like something was being hidden, and it
was not.

### The evidence

| athletics line | FY25 budgeted | FY25 spent | FY26 budgeted |
|---|---:|---:|---:|
| Athletic coaches | **$0** | $155,614 | $159,444 |
| Athletic transportation | $40,000 | $87,822 | $127,550 |
| Special detail / events | $5,000 | $72,864 | $7,100 |

Total FY25 athletics overspend $281,665, of which **$155,614 was on lines budgeted at $0**.

### Why we checked, and the good news

The app's whole argument about athletics fees rests on what athletics costs. If those
figures were built on broken numbers, the fee analysis would collapse.

**They are not.** The app uses the **FY27** budget — two years after the correction. We
checked this specifically because it could have gone the other way.

**STAYS.**

---

## 5. A correction to our own argument

### In plain terms

We have been saying special education is a runaway cost. That needs one honest
qualification, and it should be made in our own words before someone else makes it for us.

Special education **is** growing fast — 13% a year while the rest of the budget grew 3.4%.
That part is solid.

But it is also **budgeted above what gets spent**. In FY25 the district set aside 12.4%
more for special education than it used, and the staffing side is running under budget
again this year.

Those are two different claims, and only one of them is ours to make. **Special education
is growing quickly, and the district is managing it carefully.** Both are true at once. We
should never describe the staffing lines as "overrunning" — they do not. Only the
out-of-district tuition line does that, for the reasons in section 3.

### The evidence

| special education, all in | budgeted | spent | difference |
|---|---:|---:|---:|
| FY25 | $6,203,418 | $5,435,077 | **−12.4%** |

Against growth of **13.0% a year** FY23→FY26, versus 3.4% for everything else.

**CROSSES**, as a correction to our own language rather than a new number. The special
education page must not imply the district is failing to control this. The argument is
about the *rate the cost is climbing*, not about competence.

---

## What would change any of this

1. **FY26 year-end figures.** Everything about FY26 here is eight months old, and the
   tuition line especially could land anywhere.
2. **The town's actual accounting records.** Everything above compares two columns in a
   spreadsheet. It cannot see money moved between lines during the year — which is the
   normal, approved way a district covers an overspend, and would explain several of these
   with nothing irregular involved at all.
3. **The mid-year transfer votes.** A line budgeted at zero and spent against was very
   possibly funded by a transfer that is invisible from where we are standing.

## Still to do

- **Re-run findings 2 to 5 against the multi-year series.** Only finding 1 has been
  redone. Everything below it is still measured on FY25 alone plus eight months of FY26,
  which is exactly the weakness finding 1 turned out to have.
- **Ask which FY25 budget figure is right.** One question to the Business Manager settles
  §1: the FY27 workbook says $25,321,760 and the FY26 budget document says $24,883,376,
  and $438,384 of a $761,249 headline turns on it.
- Extend the extraction below the totals. Salaries and expenses are done; a line-by-line
  budget-versus-actual across ten years would say *which* lines carry the variance, which
  is the question findings 2 to 5 are really asking.
- FY26 year-end, which nothing here reaches.
- Ask how coaching pay was handled in FY25 against a $0 line (finding 4).
- Check the athletics general-fund lines against the athletics revolving fund.
