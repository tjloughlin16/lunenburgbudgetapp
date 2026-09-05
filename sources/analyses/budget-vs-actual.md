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

The **FY27 workbook** (`sources/budget-workbooks/fy27-proposals.xlsx`) gives 351 line items with both
halves for FY25, and eight months of FY26. That is what the first version of this document
worked from.

The **mirrored budget documents** (`sources/district-budget/`) go back to FY17 and
print actual columns beside budget columns, with each document stating its own column
kinds. `scripts/extract_budget_history.py` reads them, taking only the column a document
itself labels, and the series are published at `/data/total-salaries-history.csv` and
`/data/total-expenses-history.csv`.

Where the two overlap they agree closely: FY25 actuals are identical to the dollar, and
FY23 and FY24 differ by $10,000 and $5,000 on roughly $15.6M of salaries — 0.06% and 0.03%.

`scripts/extract_line_history.py` does the same for **every line** the documents print,
not just the totals — 24,337 readings across 32 documents, normalised to 397 distinct
lines, published at `/data/line-history.csv`. That is what makes it possible to ask
whether the same lines miss every year, which is the question §2 and §3 turn on.

**What that series can and cannot support.** Each line's budget and actual are read from
the same row of the same document, so a per-line comparison is sound. The lines do NOT sum
back to the district totals — between 0.11% and 2.68% out, worst in FY19 and closest in
FY23, measured as the sum of the settled lines against the documents' own TOTAL rows. So
this file never apportions the total variance between lines. It asks which lines miss and how often, and that is all it asks.

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

### FY21 is not a usable year

Every document that reports FY21 gives it an "actual" column, and in **116 of 117 lines
that column is identical to the budget, to the dollar** — 99%. In ordinary years the
figure is 10% to 21%, and those are lines that genuinely do not move: fixed stipends,
flat contracts.

A district does not spend its budget exactly on 117 lines. That column is the budget,
printed under an "actual" heading — most likely because the books were not closed when the
document went out. FY21 was the first full COVID year, which is the obvious candidate for
why, though nothing published says so.

**So FY21 is excluded from every comparison below.** It had been one of three years
supporting §1, which is the sort of thing that only shows up when you go line by line.

### Two words used below

- **Appropriation** — the amount Town Meeting votes. Not the same as what gets spent.
- **Encumbered** — money promised under a signed contract but not yet paid out.

**And one thing we DO have, which an earlier version of this document said we did not.**
The Town Accountant's own year-to-date budget report for FY26 through 31 March, obtained by
records request. It is the ledger rather than a budget document: original appropriation,
transfers and adjustments, revised budget, expended, encumbrances, for all 67 general fund
departments. Extracted to `/data/town-ledger-fy26-q3.csv`, which reconciles to the report's
own GRAND TOTAL before it will write.

It matters because this document repeatedly says money moved between lines mid-year is
invisible from here. At department level it is not. In FY26, **28 of the 67 departments had
money moved into or out of them: $489,411 in, $148,177 out, of which $76,394 went to the
school department** — while school non-recurring expenses gave up $4,223. Transfers are
real, ordinary and routine, and now they can be pointed at.

What it does not do is settle which school LINES moved: the whole school department is a
single row. And it is one snapshot of one year.

**What we still do not have:** the individual payments, the school department's own
line-level ledger, and any year but FY26. Most of what follows still compares columns in
budget documents. That is enough to see *that* a number moved. It is not enough to say
*why*.

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

Two years where the district's documents give both figures, no document contradicts
itself about either, and the year is a real one — see the note on FY21 above:

| FY | voted | spent | difference | |
|---|---:|---:|---:|---:|
| FY20 | $20,795,863 | $20,724,828 | −$71,035 | **-0.34%** |
| FY23 | $22,325,309 | $22,436,810 | +$111,501 | **+0.50%** |

One lands within a third of a percent and the other is **over**. Against FY25's −3.01%
they are a different order of magnitude, and they do not point the same way. Read the
line-by-line totals in §2 alongside them: five years there, never more than 0.9% off.

### The FY25 budget is stated two ways, and one of them is explicable

FY25 is the year the original claim rested on: a shortfall of $761,249 against a budget of
$25,321,760.

There are two published totals for FY25 salaries in the workbook and a third in the FY26
approved budget document, and **a line-by-line comparison explains the salary side
entirely**. Of 117 FY25 lines both sources state, **115 are identical**. Two are not:

| line | workbook | FY26 document | |
|---|---:|---:|---:|
| Salary Reserve | $347,338 | $379,220 | +$31,882 |
| Dues/Meetings | $10,971 | $5,000 | −$5,971 |

**Salary Reserve is $347,338 — exactly the workbook's internal salary difference.** Its
function group is literally `TOTAL SALARIES`; it is a contingency line that sits in the
totals block, and one of the workbook's two totals counts it while the other does not.
That is not two sources disagreeing. It is one total struck before a contingency and one
struck after, which is ordinary, and the earlier version of this section was wrong to
present it as a contradiction.

**The expenses are a different matter and are not explained.** The workbook says
$8,165,299 and the FY26 document $7,695,034 — $470,265 apart. Matching the expense lines
between the two sources by name, 142 line up and **only three differ, by about $1,000
between them.** The lines agree and the totals do not, and nothing published resolves it.

So the range on FY25's budget is narrower than this document previously claimed, and it
does not cross zero:

| | budget | against $24,560,511 spent |
|---|---:|---:|
| Lowest defensible | $24,851,495 | −$290,984 (−1.17%) |
| Highest | $25,353,641 | −$793,130 (−3.13%) |

**FY25 came in under budget by somewhere between $290,984 and $793,130.** The
original $761,249 sits inside that range at the top of it. What cannot be said is which
end is right, and the $470,265 of it that turns on the expense total is unresolved.

### The town has its own number for this, and it is $603,885.97

None of the arithmetic above was necessary to establish that FY25 came in under. The
district said so itself, in public, and the figure is in its own minutes.

**School Committee, 3 September 2025.** The Chair read a statement about a memo from the
Superintendent to himself, the Town Manager and the Chair of the Finance Committee
"regarding a budget surplus that was recently discovered in the amount of **$582,115.44**",
and described "the unhappy discovery of this surplus".

**School Committee, 17 September 2025.** "the surplus number has gone up to
**$603,885.97**, the change is due to closing out purchase orders from FY25."

The minutes record what that meant in the room: a member describing "an unknown surplus of
money that was not spent and instead was given back to the town", another that "we had
drastic reductions in services to students. We really could have used those funds to keep
some of the positions."

**$603,885.97 sits inside the range this analysis derived** — $290,984 to $793,130 — and
nearer the top of it. It is also the better figure to quote, for a reason that has nothing
to do with arithmetic: it is the town's own, arrived at by closing the books rather than
by subtracting two columns, and it is what the people who voted the budget were told.

**What this project should say about FY25 is that figure.** Not $761,249, which is one
subtraction among several, and not a range, which invites an argument the town has already
settled.

### One thing named in those minutes that we cannot check

The 17 September minutes list, among the issues discovered, "**double booking of the para
salaries**". That phrase appears once in 1,383 meeting documents and is never explained,
and it points at the exact line the in-district special education rate is built on.

So it was tested. **It cannot move that rate.** The para escalator is a compound rate
anchored on FY18 and FY27, and FY25 is an interior point: dropping FY25 entirely leaves
the rate at 12.78%, and so does assuming FY25 was overstated by 15%. The straight-line fit
moves from R² 0.89 to 0.85. The rate is what it was.

**What we cannot say** is what was double-booked, in which year, or by how much. The
phrase is evidence that the district found something and said so. It is not a quantity,
and it is not treated as one here.

### What this does not affect

**Nothing the app computes.** Every projection starts from the FY27 adopted column, and
the two lines that differ — a salary contingency and a dues line — are not special
education and appear in none of the FY25 figures the model reads. Checked line by line
rather than assumed.

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

## 2. The total is quiet. Everything inside it is not

### In plain terms

This was the strongest finding in the first version and it survives — the difference is
that it rested on one year and now rests on five.

The district lands within about one percent of its budget every year. Underneath that,
individual lines miss by tens and hundreds of percent, in both directions, and cancel out.

### The evidence

| FY | budgeted | spent | miss |
|---|---:|---:|---:|
| FY18 | $17,502,644 | $17,496,413 | **-0.0%** |
| FY19 | $19,155,686 | $19,113,746 | **-0.2%** |
| FY20 | $19,748,349 | $19,569,555 | **-0.9%** |
| FY22 | $20,889,212 | $20,752,649 | **-0.7%** |
| FY23 | $20,804,700 | $20,917,634 | **+0.5%** |
| FY25 | $7,662,709 | $7,462,928 | **-2.6%** |

Five years, never more than 0.9% off. Now the lines inside those totals:

| line | usable years | worst under | worst over |
|---|---:|---:|---:|
| COMPUTERS — Purchase & Lease | 6 | −3% | **+379%** |
| P.S. Regular Substitutes | 6 | −36% | +333% |
| Collaborative Tuitions | 6 | −45% | +319% |
| E.S. Special Ed Substitutes | 6 | −52% | +206% |
| Unemployment Compensation | 6 | −47% | +126% |

### What is new, and it changes the reading

**98 lines have four or more usable years. Seven of them miss the same way every
year, and all seven are small** — the largest averages $20,754 on a $20 million budget.

So the misses are **noise, not padding.** Nobody is quietly over-providing a line year
after year. Lines overshoot and undershoot and the total comes out flat because there are
a hundred of them and they are independent.

That is a better answer than the first version gave, and a less suspicious one.

### What we cannot tell

Districts move money between lines during the year with proper approvals. A line that
overspent may have been topped up legitimately, and we cannot see those votes.

---

## 2b. The whole budget, every group, every year

An earlier version of this section ranked groups by pooled dollar variance, looked at the
top six and called it a sweep. That is the method this very document shows does not work:
a group whose overspends and underspends cancel reads as quiet when nothing inside it is,
and athletics — which §4 is entirely about — never appeared. `scripts/analyze_variance.py`
replaces it and reports every group, every year, four ways.

### Coverage first

**576 usable line-years, 143 distinct lines, FY18 to FY25** — covering **89% to 96% of the
district's budget** in FY18–FY23. **FY25 is new and it is thinner**: 43 lines against 106
in FY23, because only one document so far restates FY25 line by line. Its −2.61% is
measured on $7.7M, not on the whole budget, and should be read as a first reading rather
than as the year's verdict.

FY23 read as 82% until September 2026, and the thinness was ours: `P.S. Teachers/Regular
(1-2)` and `E.S. Teachers/Regular (3-5)` carry a grade range in the line's name, the
reader split each row at that opening bracket, and 1 and 2 went in at the front of the
figures with every real one shifted along behind them. FY23 and FY24 for both lines were
published as 1, 2, 3 and 5. About $2.5M of FY23 salary fell out of the measured base as a
result. It is in.

3,158 line-years were excluded and each exclusion has a stated reason: 2,046 have only one
of the two figures, 750 are under $10,000, 301 are FY21, 51 are cells two documents
disagree about, 8 are in FY16 and FY17 — four usable lines each, which is not a
measurement of a budget and is excluded by a stated floor of twenty — and 2 are parse
artifacts. **212 lines in the FY27 workbook are never measured
here at all** — mostly lines the older documents do not carry.

### The four measures, because one hides what another shows

- **net** — pooled variance, what a treasurer feels
- **gross** — over and under added as absolutes, what a budget officer feels
- **churn** — gross over net. 1.0 means every year misses the same way; high means the
  group only looks calm because its years offset
- **spread** — worst year to best

### The whole budget, by year

| FY | lines | budgeted | spent | |
|---|---:|---:|---:|---:|
| FY18 | 89 | $17,502,644 | $17,496,413 | −0.04% |
| FY19 | 108 | $19,155,686 | $19,113,746 | −0.22% |
| FY20 | 111 | $19,748,349 | $19,569,555 | −0.91% |
| FY22 | 119 | $20,889,212 | $20,752,649 | −0.65% |
| FY23 | 106 | $20,804,700 | $20,917,634 | **+0.54%** |
| FY25 | 43 | $7,662,709 | $7,462,928 | **−2.61%** |

Never more than one percent off in either direction, and one year over.

### Salaries come in under. Everything else comes in over.

| | line-years | budgeted | spent | |
|---|---:|---:|---:|---:|
| Salaries | 346 | $68,873,714 | $68,320,829 | **−0.80%** |
| Everything else | 195 | $34,166,827 | $34,244,058 | **+0.23%** |

(The two do not sum to 576: 35 line-years are on lines the FY27 workbook no longer carries,
so they have no section to be filed under.)

The shape of a district provisioning payroll for a roster it does not always fill, and
provisioning everything else about right. Both are within one percent, and they very
nearly cancel — which is why the whole-budget figures above are so quiet.

### Almost nothing misses the same way twice

Of every group with four or more measured years, **exactly one is over in every year**
(custodial supplies, +$83,408) and **exactly one is under in every year** (general
education paraprofessionals, −$49,298). Both are small.

At line level it is the same: **7 lines out of 141 miss the same way every year**, the
largest averaging $20,754.

**There is no systematic padding in this budget.** That is the single most important
finding in this section and it is a negative one.

### What there is instead is drift

27 groups moved materially between their first two measured years and their last two:

| group | first two | last two | |
|---|---:|---:|---:|
| Collaborative tuitions | +251% | −9% | −260 pts |
| **Replace equipment** | **+1%** | **+232%** | **+231 pts** |
| After school advisors | −26% | +116% | +142 pts |
| District-wide administration | +3% | +97% | +95 pts |
| Private tuitions | +1% | −61% | −62 pts |
| Info management & tech | −5% | +51% | +56 pts |

### The clearest case: a line that stopped being maintained, and was then fixed

`COMPUTERS — Purchase & Lease`:

| FY18 | FY19 | FY20 | FY22 | FY23 |
|---:|---:|---:|---:|---:|
| −3% | −1% | +141% | +323% | **+379%** |

The budget sat at $39,000 while spending ran $165,107 and $186,722. **Then the FY26 budget
is $243,450.** Equipment leases did the same thing — $30,420 budgeted against $96,907
spent, then $85,000 in FY26.

**So this is not a district that cannot budget. It is a line that drifted for four years
and was then corrected**, which is the same shape as the athletics coaching line in §4.
Both are worth saying because a reader looking only at the middle years would conclude
something else.

### By function group, the largest net movers

| overspent | net | | underspent | net |
|---|---:|---|---|---:|
| Replace equipment (7400) | **+$548,442** (+75.2%) | | Private tuitions (9300) | **−$440,436** (−12.1%) |
| Insurance programs (5200) | +$444,611 (+2.6%) | | Student transportation (3300) | −$333,248 (−5.5%) |
| Collaborative tuitions (9400) | +$149,735 (+19.9%) | | Special education teachers (2310) | −$183,301 (−2.7%) |
| Custodial supplies (4110) | +$83,408 (+40.4%) | | Custodial services (4110) | −$145,579 (−3.7%) |

### And the largest movers, line by line

| overspent | | underspent | |
|---|---:|---|---:|
| Computers — purchase & lease | +$380,070 | Private tuitions | −$440,436 |
| **Health insurance** | **+$293,023** | General education transport | −$161,735 |
| Collaborative tuitions | +$149,735 | Special education transport | −$161,107 |
| Admin tech contracted services | +$99,729 | H.S. resource room teacher | −$106,964 |
| Equipment, maintenance & lease | +$90,496 | Maintenance salaries | −$103,769 |

**Health insurance is the one that matters to the gap.** Only +1%, +0%, −1%, +3%, +7% —
but on the largest non-salary line in the budget that is $293,023, and it is drifting
upward. It is the only overspend attached to a line big enough to move the projection, and
the model already escalates it at 9%.

### And the groups that cancel themselves out

Ranked by churn — these look calm in the net and are not:

| group | net | gross | churn | by year |
|---|---:|---:|---:|---|
| Networking / telecoms | +$3,494 | $37,778 | 10.8× | +17% −30% −13% −19% +76% |
| School nurses | +$6,189 | $33,323 | 5.4× | −0% +0% +0% +6% −5% |
| **Athletic expenses** | **−$6,787** | **$28,895** | **4.3×** | −11% +29% −14% −0% −8% |
| Special education substitutes | −$48,128 | $153,472 | 3.2× | +98% −35% −66% −35% −7% |
| Collaborative tuitions | +$149,735 | $453,727 | 3.0× | +184% +319% −45% −18% +0% |
| Heating of buildings | +$37,906 | $114,006 | 3.0× | −29% +3% +28% +25% +25% |

**Athletics is in that table, and that is why the first attempt missed it.** Its net is
−$6,787 on athletic expenses and −$69,968 on athletic salaries — unremarkable numbers
hiding years that run from −19% to +29%. §4 is about the year those swings were largest.

---

## 3. One cost cannot be predicted — and it misses in BOTH directions

### In plain terms

**This is still the most important finding here, and half of it was wrong.**

When a child's plan requires a school the district cannot provide, the town pays another
school. It does not set the price, does not choose how many children need it, and cannot
say no.

The first version said the district *pads what it can predict and under-provides what it
cannot*. The first half roughly holds. **The second does not.** Out-of-district tuition is
not systematically under-budgeted — it is unpredictable, and it misses badly in whichever
direction it feels like.

### The evidence

Out-of-district tuition, budgeted against spent:

| FY | budgeted | spent | miss |
|---|---:|---:|---:|
| FY18 | $760,270 | $868,927 | **+14.3%** |
| FY19 | $754,480 | $958,495 | **+27.0%** |
| FY20 | $865,746 | $869,557 | **+0.4%** |
| FY22 | $818,716 | $397,233 | **-51.5%** |
| FY23 | $489,918 | $304,748 | **-37.8%** |
| FY25 | $1,164,824 | $732,298 | **-37.1%** |

Three years over, three under, and a range from **+27.0% to −51.5%**. Twice it cost
a quarter more than budgeted; twice it cost half of what was set aside. FY25, newly
measurable, lands −37.1% — the third consecutive year it came in far under, which is the
first thing in this series that looks like a pattern rather than noise. Three years is
still three years, and rule 6 says so.

Special education staffing over the same years:

| FY | budgeted | spent | miss |
|---|---:|---:|---:|
| FY18 | $2,434,649 | $2,450,453 | **+0.6%** |
| FY19 | $2,959,132 | $2,783,630 | **-5.9%** |
| FY20 | $3,044,407 | $3,005,557 | **-1.3%** |
| FY22 | $3,685,393 | $3,671,157 | **-0.4%** |
| FY23 | $3,498,424 | $3,387,386 | **-3.2%** |
| FY25 | $445,328 | $434,922 | **-2.3%** |

Five of six under, and never by more than 5.9% — modest, and much steadier than tuition.
**FY25 rests on a single line**, $445,328 of it, because only one document restates FY25
at line level so far. It is consistent with the others and it is not independent evidence
of anything.

So the shape is real but the language has to change: **this is a line nobody can forecast,
not a line anybody is short-changing.**

### What this already changed in the app

The special education work of 28 August reached the same conclusion from a completely
different direction — eleven budgets of the tuition line with a straight-line fit of
R² 0.10 and no trend to measure — and the model now holds the line flat and publishes a
range of priced scenarios instead of a rate. These two methods disagree about nothing,
which is the most reassuring thing in this document.

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

## 5. A correction to our own argument — and then a correction to the correction

### In plain terms

The first version of this section said special education is *budgeted above what gets
spent*, and used it to argue that the district manages the line carefully. It rested on
FY25, where the gap was −12.4%.

Across five years it is not that clean.

### The evidence

Special education, staffing and tuition together:

| FY | budgeted | spent | miss |
|---|---:|---:|---:|
| FY18 | $3,194,919 | $3,319,380 | **+3.9%** |
| FY19 | $3,713,612 | $3,742,125 | **+0.8%** |
| FY20 | $3,910,153 | $3,875,114 | **-0.9%** |
| FY22 | $4,504,109 | $4,068,390 | **-9.7%** |
| FY23 | $3,988,342 | $3,692,134 | **-7.4%** |
| FY25 | $1,610,152 | $1,167,220 | **-27.5%** |

Two years over, four under, and the three largest misses are the three most recent.
FY25's −27.5% is measured on a much smaller base than the years above it — $1.6M against
$4.0M — so it belongs in the direction of travel and not in the magnitude. This is
not a line consistently provisioned above what it costs; it is a line that moves around,
mostly because the tuition half of it does.

### And a figure that has to be withdrawn

The first version supported this with **"13% a year while the rest of the budget grew
3.4%"**. That comparison ran from an FY23 **actual** to an FY26 **budget** — the exact
error rule 1 exists to prevent, and it is corrected at the head of
`analyses/sped-and-funds.md`. Budget to budget the figure is nothing like 13%.

The sentence it was supporting can stand on its own without it: special education staffing
comes in close to budget, and the app should never describe those lines as overrunning.
**Only the tuition line does that, and it does the opposite just as often.**

### What we cannot tell

Whether the FY22 and FY23 underspends are unfilled positions, delayed placements, or
money moved elsewhere with approval. The three look identical from here.

## 6. The one year the para budget did not match what was spent

The FY25 minutes name "double booking of the para salaries" as one of the things the
district found. It is never explained anywhere else. But it is testable, because the para
lines have a budget and an actual for six years:

| FY | budgeted | spent | |
|---|---:|---:|---:|
| FY18 | $726,734 | $728,898 | +0.3% |
| FY19 | $768,625 | $781,314 | +1.7% |
| FY20 | $988,455 | $993,419 | +0.5% |
| FY22 | $1,069,410 | $1,104,945 | +3.3% |
| FY23 | $1,014,759 | $1,018,072 | +0.3% |
| **FY25** | **$1,498,126** | **$1,338,477** | **−10.7%** |

For five years the para budget and the para spending track within about three percent, and
the actual usually comes in slightly *above*. **FY25 is the only year that breaks it**, and
it breaks it by $159,649 — a quarter of the $603,886 surplus the district reported for
exactly that year.

That is what a double-booked line looks like from outside: money budgeted twice, spent
once. It does not prove the district's account, but it is consistent with it in the right
year and in no other, which is about as much as an outside check can offer.

**What it does not do is move any rate.** The escalator on this line is anchored on FY18
and FY27, so FY25 is an interior point — removing it entirely changes nothing. And the
same growth appears in actual spending as in budgets: 9.07% a year against 10.89%.

---

## 7. The athletics budget is net of fees, and the app does not know it

Found while sweeping, and it is the one finding here that changes something published.

**In the general fund**, two athletics lines are budgeted at nothing from FY26 on:

| line | FY22 actual | FY25 actual | FY26 | FY27 |
|---|---:|---:|---:|---:|
| ATHLETIC OFFICIALS | $1,510 | $0 | **$0** | **$0** |
| REPLACEMENT OF UNIFORMS | $12,672 | $6,650 | **$0** | **$0** |

**In the athletics revolving fund**, which is funded entirely by user fees, the same two
costs appear by vendor: **ArbiterSports $59,400** for officials and scheduling, and
**Prime Time Sports $25,421** for uniforms — within $113,602 of purchase of service, on top
of $30,514 of salaries for four staff. Total fee-funded athletics spending: **$146,911**.

The costs left one pot and arrived in the other. That is rule 11 in its plainest form: the
general fund line is **net** of what fees pay for, and nothing marks it as net.

**What that does to the app.** `PROGRAM_TOTAL_ADOPTED` is $217,908 and the fee model asks
what fee would cover $345,458 — while today's fee already covers $146,911 that is not
inside either figure. Gross athletics is about **$364,819** and fees already pay roughly
40% of it. The published $960 self-funding fee, the $358,380 revenue peak, "fees cover 54%"
and conclusion 5 are all built on a base that excludes what the fee already buys.

`model/athletics.py` states the opposite in a comment — `FEE_REVENUE_IN_BUDGET = False`,
because "fees flow through revolving accounts, so the program costs shown are GROSS". Fees
flowing through a revolving account is precisely how the general fund line ends up net.

**Not corrected yet**, because correcting it means rebuilding the fee curve on a gross base
and $146,911 is a floor rather than an established total.

### And athletic transportation, which is not the same story

Athletic transportation sits in the general fund under 3510, and its actuals are recorded
there like any other line — $39,880, $40,000, **$87,822**, then $127,550 budgeted for FY26
and cut to nothing in the FY27 adopted budget.

It is **not** fee-funded: none of the revolving fund's $109,503 of named vendors is a bus
company. But two things about it are unresolved. FY24's actual is **exactly** its $40,000
budget, which charter invoices do not do. And the district's own comment on that row reads
*"Actuals in munis are tracking well below FY26 budget, can FY27 be reduced? Yes, level
funded"* — with $47,847 spent and $13,169 encumbered at three quarters through, against
$127,550. The app treats $127,550 as the cost of putting the buses back.

---

## What would change any of this

1. **Which FY25 budget figure is right.** $25,321,760 or $24,883,376. One question, and
   $438,384 of a $761,249 headline turns on it.
2. **The town's accounting records.** Everything here compares columns in budget documents.
   It cannot see money moved between lines during the year — the normal, approved way a
   district covers an overspend, and the ordinary explanation for several findings above.
3. **FY26 year-end.** Nothing here reaches it.
4. **Why FY21's actual column is its budget.** Probably books not closed in a COVID year.
   Probably. It is currently an inference from a pattern in the numbers.

## Still to do

- **Findings 2, 3 and 5 have been redone across five years. Finding 4 has not** — it is
  specific to FY25 athletics, and it describes a gap that was found and corrected, so it
  is the one finding that does not need a longer series to mean what it says.
- Reconcile the line-level series to the district totals. It is 0.1% to 1.6% out, which is
  fine for the per-line questions asked here and not fine for apportioning a total.
- Extend the series past FY23. Coverage thins because fewer documents report recent
  actuals; the FY27 workbook covers FY23 to FY25 and has not been merged in line by line.
- Ask how coaching pay was handled in FY25 against a $0 line (finding 4).
- Check the athletics general-fund lines against the athletics revolving fund.
