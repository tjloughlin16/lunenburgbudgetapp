# Show your work

Every figure this project publishes, and how it was arrived at.

It is written for the people who have to decide something with it — Finance
Committee, Town Manager, Select Board, School Committee. It assumes you read
budgets and does not assume you write software. Nothing in the body of it requires
a computer to follow; the files and commands are in Appendix A, for anyone who
wants to rerun the arithmetic themselves.

**The most useful thing here is not a number. It is the labels.** Every figure is
marked with where it came from, because you cannot judge an argument without
knowing which parts of it are somebody else’s work and which are ours:

| label | means |
|:--|:--|
| `published` | A figure stated in a document by the town, the district or the state. We transcribed it. |
| `contract` | A rate set by a signed collective bargaining agreement. |
| `statute` | Fixed by law. |
| `measured` | We calculated it from somebody else’s figures. The arithmetic is ours; the underlying numbers are not. |
| `ours` | An estimate, a classification or an assumption we made. These are the ones to argue with, and Section 12 lists every one of them in order of how much it matters. |

**If you have limited time, read Section 12.** It is every assumption in the model,
sorted by how much the answer moves if the assumption is wrong, with a plain
statement of what backs each one — including the two that are backed by nothing.

Every section is laid out the same way: the question being asked, what goes into
it, the arithmetic worked through, and then what we assumed and what would settle
it. That last heading appears in every section without exception.

## Two distinctions that everything here depends on

**A budget is not an actual.** A budget is what somebody voted or proposed. An
actual is what got spent. On some lines in this town the two differ by 59%.
 A growth rate measured from an actual in one year to a budget in the next is
partly real growth and partly the step between two different kinds of number, and
it produces an answer that looks authoritative and is wrong — that mistake once put
our special education growth rate a point and a half too high.

**Every projection here uses budget figures only.** Actual spending answers other
questions and is used for them. The two are never combined inside one calculation,
and that is enforced automatically rather than by good intentions.

**A one-time saving is not a change in direction.** A cut lowers the cost curve
once and leaves its slope alone. Only a change in a *growth rate* changes the
slope. Two figures growing at different rates move apart forever, no matter how
much you subtract from one of them once — which is the arithmetic behind why a town
can cut every year and face a larger gap every year. It is not mismanagement and it
is not anybody being alarmist.

Most of what follows is one or the other. Free cash, cuts and overrides change the
level. Sections 3 to 5 are about the rates.

**And a budget line is a net figure, in dollars.** The district budgets what the
town must raise after grants, fees and reimbursements have paid their share. A line
can rise because the thing got dearer, because a grant that was covering part of it
ended, or because a fee stopped being collected — and all three look identical on
the page. Nothing in this document measures what a service costs, how many people
it employs, or how many children it serves. It measures **appropriations**, which
is what Town Meeting votes on.

---

## 1. How the gap is projected

### The question

If the district keeps doing exactly what it does now, and the town raises revenue
the way the town says it raises revenue, how far apart are those two figures in
each of the next several years?

That is not a forecast of what will happen, because what will happen includes
decisions nobody has taken yet. It is the arithmetic of taking no decision at all.

### What goes in, on the revenue side

All of it from the Town Manager’s FY27 budget release of 17 April 2026 and the
enacted state budget.

| figure | FY27 | label |
|:--|--:|:--|
| Levy limit | $34,133,581.28 | `published` |
| Debt excluded from the limit | $2,199,352.52 | `published` |
| State aid | $11,876,038 | `published` |
| Local receipts | $3,508,024 | `published` |
| Omnibus budget as appropriated | $49,963,990.19 | `published` |
| School appropriation | $26,572,288 | `published` |
| September Town Meeting article | $350,000 | `published` |
| Programs that article restores | $453,722 | `published` |

### How next year’s revenue is worked out

Three figures grow, one is held flat, and one is subtracted.

> Next year’s levy limit = this year’s levy limit × 1.025 + new growth

```
Levy limit, FY27                                          $34,133,581
  plus Proposition 2½ growth of 2.5%                        +$853,340
  plus new growth                                           +$400,000
                                                      ---------------
Levy limit, FY28                                          $35,386,921
Debt excluded from the limit (held flat)                   $2,199,353
State aid, grown 2.0%                                     $12,113,559
Local receipts, grown 1.0%                                 $3,543,104
Less revenue not appropriated in the omnibus              −$1,753,006
                                                      ---------------
Town revenue available to appropriate, FY28               $51,489,931
The same figure for FY27                                  $49,963,990
Growth                                                          3.05%
```

**That subtraction is worth a word.** $1,753,006 of FY27 revenue does not appear
in the omnibus budget — assessments, the overlay, state charges and the rest. We do
not model it changing, so it is worked out once from the FY27 figures and taken off
every year. That is an assumption. If those charges grow faster than revenue does,
this projection is too generous.

**And then the schools get their share.**

> Next year’s school appropriation
>   = this year’s appropriation × (1 + the growth rate above)

**This is the single most consequential choice in the model, and it is ours.** It
assumes the schools hold the share of the town budget they hold today —
53.2% of the omnibus — and neither gain
nor lose ground against every other department. Nothing published commits the town
to that, in either direction. A year in which the schools’ share moves by a single
point swamps most of the growth rates in this document.

### What goes in, on the cost side

The adopted FY27 school budget, line by line, sorted into seven groups. Each group
grows at its own rate, because they behave nothing alike.

> Cost of the same services next year
>   = the sum of each group × (1 + that group’s growth rate)

The line items come to $26,572,290, against a published
appropriation of $26,572,288 — a difference of
$2, which is rounding in the
district’s own workbook and is not corrected here.

The $453,722 of programs restored at the September Special Town
Meeting is added to salaries, because that money is one-time and carrying those
programs into FY28 is itself a cost the district has to absorb.

| group | FY27 | share of the budget | grows at | that rate is |
|:--|--:|--:|--:|:--|
| Salaries, other than special education | $13,409,674 | 49.6% | 4.00% | `contract` |
| Special education, in district | $5,466,201 | 20.2% | 6.49% | `ours` |
| Health insurance and unemployment | $4,019,071 | 14.9% | 9.00% | `published` |
| Everything else | $1,772,053 | 6.6% | 3.00% | `published` |
| Transportation, other than special education | $1,053,360 | 3.9% | 6.00% | `ours` |
| Out-of-district tuition | $700,142 | 2.6% | 0.00% | `ours` |
| Utilities | $605,511 | 2.2% | 5.00% | `published` |
| **Total** | **$27,026,012** | **100.0%** | **5.18%** blended |  |

**Two things in that table are worth stopping on.**

*The cost side and the revenue side do not get the same addback.* Costs carry the
whole $453,722 restoration plan. Revenue carries only the
$350,000 Town Meeting article, because the balance —
$103,722 — came from health insurance
savings inside FY27 that do not recur. So the projection begins FY28 already
carrying that amount as gap. That is deliberate, and it is a judgement; anyone who
thinks those savings do recur should take it off.

*Unemployment compensation sits in the health insurance group.* It is
$25,000 of the
$4,019,071, it shares an account code with health
insurance, and so it grows at 9.0% along with it. Unemployment
does not behave like a health premium. It is too small to change any conclusion,
and it is written down here because somebody adding up the lines should not find a
figure they cannot account for.

### The gap, worked through for FY28

```
School appropriation, FY27                                $26,572,288
  plus the September Town Meeting article                   +$350,000
  grown at the town’s revenue growth of 3.05%               +$822,228
                                                      ---------------
Money available to the schools, FY28                      $27,744,516
                                                      ---------------
Cost of the same services, on the FY27 basis              $27,026,012
  each group grown at its own rate (blended 5.18%)        +$1,399,375
                                                      ---------------
Cost of the same services, FY28                           $28,425,387
Money available to the schools, FY28                      $27,744,516
                                                      ---------------
GAP                                                          $680,870
```

Those figures are recomputed from the steps above and checked against the model
before this document will save. If they ever disagreed, it would stop rather than
publish a walkthrough that does not reproduce the answer it is explaining.

### The projection

**Read the gap column carefully, because it is the figure most often
misunderstood.** Each row is *that year on its own* — what that single year’s
shortfall would be if nothing had been done in any earlier year. The rows are not
added together, and each one is not "the extra hole that year" either.

| year | cost of the same services | money available | shortfall that year, if nothing is done first | of which is new that year | town revenue growth |
|:--|--:|--:|--:|--:|--:|
| FY28 | $28,425,387 | $27,744,516 | $680,870 | $680,870 | 3.05% |
| FY29 | $29,908,680 | $28,586,377 | $1,322,303 | $620,775 | 3.03% |
| FY30 | $31,481,524 | $29,448,345 | $2,033,179 | $671,009 | 3.02% |
| FY31 | $33,149,963 | $30,330,907 | $2,819,056 | $724,943 | 3.00% |
| FY32 | $34,920,491 | $31,234,562 | $3,685,928 | $782,892 | 2.98% |
| FY33 | $36,800,078 | $32,159,821 | $4,640,257 | $845,152 | 2.96% |

**Three different questions, three different answers, and they get confused for
each other constantly:**

| the question | answer for FY29 |
|:--|:--|
| What is the shortfall in FY29, if the town does nothing in FY28? | **$1,322,303** — the gap column |
| How much of that is new in FY29, over and above the FY28 hole carried forward? | **$620,775** — the second column |
| What do the shortfalls come to across FY28–FY33 added together? | **$15,181,593** |

So FY29’s $1,322,303 is **not**
$680,870 plus something. It is what FY29 looks like
on its own if FY28 was left alone — the earlier shortfall is still
there, and a year of growth has been added on top of it.

**And the same word means something different in Section 10.** There, every year’s
gap is what is left *after* the previous years have been cut, which is a much
smaller number: FY29 is $1,322,303 here and
$563,678 there — 57% lower. Both are
correct. They answer different questions, and the distance between them is the
value of acting early rather than late.

**The gap widens because two figures grow at different rates.** Costs at
5.18%, town revenue at about 3.05% and drifting
down toward the statutory 2.5% as a fixed $400,000 of
new growth becomes a smaller share of a larger base. Nothing about the size of any
one budget line changes that. It is four numbers, and it is the whole argument.

### What we assumed, and what would settle it

- **The schools hold their present share of the town budget.** Nothing publishes a
  commitment to that. It is the assumption most capable of making everything else
  here beside the point.
- **New growth stays at $400,000 a year.** That is the town’s own
  estimate. The Assessors’ own series runs from
  $481,496 in
  FY2018 down to
  $234,383 in
  FY2023. Section 11.
- **Excluded debt, and the revenue outside the omnibus, are held flat.** Both will
  move. Neither is modelled.
- **There is no FY28 budget.** Everything after FY27 is projection. When the
  district publishes an FY28 request, that is the real number, and this is what it
  should be compared against.

---

## 2. Which budget lines actually drive the gap

### The question

The instinct in every budget meeting is to go after the biggest line. That is the
wrong ranking, and following it is how a town spends three meetings on athletics
and none on special education.

### How it is worked out

A line adds to the gap in proportion to its share of the budget **multiplied by**
how far its growth exceeds the levy cap.

> Contribution = share of the budget × (growth rate − 2.5%)

Neither figure means anything on its own. A very large line growing at 2½% adds
nothing. A small line growing at 9% adds a good deal.

The result is in percentage points of budget growth above the cap, and the column
adds up to the amount by which the whole budget outruns Proposition 2½.

| line | share | grows at | above the cap by | contribution | that rate is |
|:--|--:|--:|--:|--:|:--|
| Health insurance and unemployment | 14.9% | 9.00% | 6.50% | **0.97** | `published` |
| Special education, in district | 20.2% | 6.49% | 3.99% | **0.81** | `ours` |
| Salaries, other than special education | 49.6% | 4.00% | 1.50% | **0.74** | `contract` |
| Transportation, other than special education | 3.9% | 6.00% | 3.50% | **0.14** | `ours` |
| Utilities | 2.2% | 5.00% | 2.50% | **0.06** | `published` |
| Everything else | 6.6% | 3.00% | 0.50% | **0.03** | `published` |
| Out-of-district tuition | 2.6% | 0.00% | -2.50% | **-0.06** | `ours` |

**Total: 2.68 points.** That is the number that has to reach
zero. Blended cost growth is 5.18%, the levy cap is 2.5%,
and the difference between them is those 2.68 points.

### The same fact, two ways

**Salaries, other than special education** is the largest line in the budget at
$13,409,674 — 49.6% of all spending.
It grows at 4.00%, which is 1.50% above the
cap, so it contributes 0.74 points.

**Health insurance and unemployment** is 14.9% of spending — a line
3.3 times smaller — and contributes
**0.97 points**, more, because it grows
6.50% above the cap instead of 1.50%.

**A line held flat pulls the average down.** Out-of-district tuition is
2.6% of spending at 0.0%, so it
contributes -0.06 points — a negative number, which is
what "below the cap" looks like in this column.

Rank by contribution. Never by size, and never by rate alone.

### What we assumed, and what would settle it

- Every rate in that table gets its own section below. Three of the seven are ours.
- The shares are FY27 shares, held constant. In reality a faster-growing line
  becomes a bigger share of the budget each year, so this table slightly understates
  the top line over a long horizon. The projection itself grows each group
  separately and does not have that problem — only this ranking does.

---

## 3. Where each growth rate comes from

### The question

You cannot judge this projection without knowing which of its growth rates are the
district’s own, which are set by a signed contract or by statute, and which we
chose. Here is the whole list in one place.

| group | grows at | label | basis |
|:--|--:|:--|:--|
| Salaries, other than special education | 4.00% | `contract` | The teachers’ agreement — scale increases plus steps |
| Special education, in district | 6.49% | `ours` | A blend of two contracts and two measured trends. Section 4 |
| Health insurance and unemployment | 9.00% | `published` | The district’s own stated assumption for FY27 |
| Everything else | 3.00% | `published` | The district’s own stated assumption for FY27 |
| Transportation, other than special education | 6.00% | `ours` | The district assumed 10% for FY27. This is softer, and ours |
| Out-of-district tuition | 0.00% | `ours` | Held flat. Section 5 sets out why that is a finding rather than a gap |
| Utilities | 5.00% | `published` | The district’s own stated assumption for FY27 |

**Four of the seven are the district’s own stated assumptions or a signed
contract.** We did not invent them and we have not adjusted them. The three marked
`ours` are the ones to argue with, and two of them get a full section each: special
education in Section 4, out-of-district tuition in Section 5.

**The third is transportation.** The district assumed 10% for FY27. We use
6.0%, which is *softer* than the district’s own figure — so
the gap published here is smaller than the district’s own assumptions would
produce. It is ours, and unlike the other two it does not rest on any test of the
line’s own history. It is the least defended figure in the table, and it is named
as such in Section 12.

### Checking the rates against history

Every assumption is compared against what that line actually did, **budget to
budget** — never budget to actual, which would measure the step between two
different kinds of number as well as the growth.

Six lines have come back flagged. Three of those turned out to be one-time step
changes rather than trends, which is why the year-by-year has to be read before a
compound growth rate is believed. A three-year rate measured off a small base is
not a trend, and a line that goes to zero and reappears under a new name produces a
spectacular-looking rate that means nothing at all.

---

## 4. Special education, in district

The longest section, because this is the growth rate this project built rather than
transcribed, and it moves the answer more than any other single choice in the
model.

### The question

What should in-district special education be grown at, given that no contract
governs it, the state has no account code for it, and three budget years cannot
tell a one-time increase from a trend?

### Why it is separated out at all

The state’s account codes cannot separate special education from everything else.
One code covers paraprofessionals of both kinds; another covers transportation of
both. Grouping by code alone put roughly $5.7 million of special education staffing
in with general salaries, where it took the teachers’ contract rate.

That hid no money — the total was always right — but it averaged together two lines
that behave nothing alike. Teaching salaries move when a contract is bargained.
This line moves when a child arrives who needs a paraprofessional.

### The classification, which is ours

**This is the figure on the page most open to challenge, and it should be.** There
is no published quantity called "special education", so this total is a rule we
wrote:

1. **Eight account groups are special education outright**, and every line inside
   them counts — 46 lines.
2. **Inside groups that carry both kinds of cost**, a line counts when the
   district’s own label for it says special education — 8 lines. One
   of those, special education transportation, is most of the money.

That is 54 lines totalling $5,466,201 in the adopted FY27
budget. Every one of them is published as a list, so the total can be added up by
hand.

**What sits just outside, and why:**

| excluded | lines | FY27 | why |
|:--|--:|--:|:--|
| English Language Learner lines, wherever they appear | 2 | $279,342 | A different entitlement, serving different children, under a different part of the law — but the district files some of it inside groups that are otherwise special education, so a rule that took those groups at their word counted it. It did, until this was found. |
| 2330 - Paraprofessionals General Education | 4 | $0 | General education paras. The group next to the special education one, and the single boundary most likely to be crossed by accident in either direction. |
| 9300 / 9400 — out-of-district tuition | 4 | $700,142 | Special education, but escalated on its own because it is set by placement rather than by payroll, and it behaves nothing like staffing. |

**English Language Learner lines are the correction most worth knowing about.** The
district files some of that work inside groups that are otherwise special
education, so a rule that took those groups at their word counted it — and ours
did, until this was found. It is a different entitlement, serving different
children, under a different part of the law.

### The obvious answer, and why we did not use it

The obvious number is 5.77% — what the whole line did across
three budgets. It was our published choice for a day. Break the line into its parts
and the whole increase is one component moving once:

| part | FY25 budget | FY26 final | FY27 level service | FY26 change | FY27 change |
|:--|--:|--:|--:|--:|--:|
| Paraprofessionals | $1,376,893 | $1,344,373 | $1,874,411 | -2.4% | 39.4% |
| Special education transport | $445,328 | $565,734 | $649,953 | 27.0% | 14.9% |
| Speech, OT and summer services | $603,017 | $567,677 | $589,245 | -5.9% | 3.8% |
| Substitutes | $52,500 | $52,500 | $52,500 | 0.0% | 0.0% |
| Psychologists and testing | $270,675 | $295,355 | $207,723 | 9.1% | -29.7% |
| Special education teachers | $1,990,158 | $1,993,848 | $1,963,512 | 0.2% | -1.5% |
| Administration, legal, supplies and contracted work | $126,467 | $144,842 | $105,039 | 14.5% | -27.5% |
| **Whole line** | **$4,865,038** | **$4,964,329** | **$5,442,383** | **2.0%** | **9.6%** |

The paraprofessional increase is 111% of the whole
FY27 rise — every other part of special education fell that year. Take it out and
the rest of the line grew 1.14% a year, below the levy cap.

So 5.77% is not a growth rate. It is one hiring decision,
averaged over two years and then compounded forever. **Those paraprofessionals were
hired. Their cost is already inside the
$5,466,201 this projection starts from.**
Growing that base at 5.77% assumes the district hires
39% more paraprofessionals again next year, and again
the year after.

### The test that decides every rate below

Three budget years cannot tell a one-time increase from a trend. Our mirror of the
district’s budget page reaches back to FY17, so each line below is measured over
nine or ten budgets instead of two — **budget figures only, and always at the same
stage of the budget process**, because a year has several budget figures at
different stages and they are far apart. A series that takes whichever number each
document happens to lead with is a walk across stages, not a trend.

Each line gets the same two tests. The growth rate itself is the ordinary compound
one:

> Growth rate = (last year ÷ first year) raised to the power of (1 ÷ number of years), minus 1

**Does the line follow a trend at all?** The "fit" column runs from 0 to 1 and
measures how closely the years fall on a straight line. A figure near 1 means they
do. **A figure near 0 means there is no trend to measure, and stating a growth rate
anyway is a choice dressed up as a measurement.**

**How much does the answer depend on where you start counting?** The last column is
that same compound growth rate to FY27, worked from every possible starting year. A
narrow band means the answer is robust. A band running from very negative to very
positive means the "growth rate" is an artefact of the year you happened to pick.

| line | budgets | span | first | last | fit | direction | growth rate | growth rate by starting year |
|:--|--:|:--|--:|--:|--:|:--|--:|:--|
| Paraprofessionals | 10 | FY2018–FY2027 | $634,513 | $1,872,411 | 0.89 | 8 up / 1 down | 12.78% | 11.54% to 39.49% |
| Professional staff | 8 | FY2020–FY2027 | $1,617,268 | $1,945,512 | 0.84 | 4 up / 3 down | 2.67% | -1.68% to 2.67% |
| Transportation | 9 | FY2019–FY2027 | $417,585 | $649,953 | 0.33 | 6 up / 2 down | 5.69% | 5.50% to 24.61% |
| Out-of-district tuition | 11 | FY2017–FY2027 | $655,534 | $700,142 | 0.10 | 6 up / 4 down | 0.66% | -45.78% to 11.78% |

Read the last row against the first. Same test, same arithmetic, opposite verdicts:
paraprofessionals fit a trend at 0.89 and are grown at what
they have actually done. Tuition fits at 0.10 and is
held flat. That comparison **is** the argument, which is why both are published.

### The rate we do use

There is no special education bargaining unit. Professional staff are on the
teachers’ agreement and paraprofessionals on their own; the buses are a vendor
contract, and substitutes and supplies are not bargained at all. So the rate is a
weighted average of contracts signed for other reasons.

> Rate = the sum, across the parts, of
>   (that part’s share of the line × that part’s own growth rate)

**Each part grows at its contract where a contract governs it and the line has
behaved accordingly, and at what it has measurably done where no contract reaches
it.** Which of those applies is decided by the test above, not by preference.

| part | FY27 amount | share of the line | grows at | basis |
|:--|--:|--:|--:|:--|
| Professional staff | $2,865,519 | 52.7% | 2.67% | Measured over 8 budgets. Their agreement gives 3.5% and the line has run below it — headcount drifting down, not a smaller pay rise |
| Paraprofessionals | $1,874,411 | 34.4% | 12.78% | Measured over 10 budgets rather than taken from the 2.0% contract — this line is headcount, and no settlement reaches it |
| Transport | $649,953 | 11.9% | 5.69% | Vendor contract with no published escalator; measured over 9 budgets |
| Substitutes and supplies | $52,500 | 1.0% | 0.00% | Not bargained; identical in every budget held |
| **Blended rate** |  |  | **6.49%** |  |

**Two published contract rates are deliberately not used, and it cuts both ways.**
The teachers’ agreement gives 3.5% and this line has run *below*
it — which means headcount here has been drifting down, and using the contract rate
would have overstated this component. The paraprofessionals’ agreement gives
2.0%, and ten budgets show the line growing
12.78% a year, because no pay settlement governs how many
people are employed. Pricing them at their contract assumes the district stops
adding them.

### The range, published beside the rate

Five defensible answers to the same question. The one we use is neither the highest
nor the lowest, and anyone who prefers a different one can see what it costs.

| rate | reading | what it is |
|:--|:--|:--|
| **1.14%** | Special education apart from the paras, two budgets | What the rest of the line did while the paras were being added. Below the levy cap — and it is the paras, not the rest, that make this line a driver. |
| **2.53%** | If every settlement were the whole story | The two bargained agreements at their published rates and nothing else — no bus increase, no change in how many people are employed. Published here because it is what this model used to assume, and because the gap between it and the rate above is the part of this line that pay settlements do not explain. |
| **5.77%** | The whole line, two budgets | What the in-district line did between the last two budgets. Close to the rate used, and reached a different way. |
| **6.49%**  ← used | Each part at its contract, or at what it has measurably done | Professional staff at the teachers’ agreement; paras and buses at what ten and nine budgets show them doing, because no contract governs how many people are employed. Weighted by each part’s share of the line. |
| **9.63%** | FY27 by itself | The single steepest year. One observation, and the top of the range. |

### What we assumed, and what would settle it

- **We assume the FY27 hiring was a one-time step and not the first year of a
  climb.** If more paraprofessionals are hired every year — because more children
  arrive needing one, or because the ones here need more — this rate is too low and
  the projection understates the gap.
- **A budget line is dollars, not people.** Nothing here shows headcount. The
  district does not publish staff counts, so "the line grew" cannot be turned into
  "the district employs more paraprofessionals" without inventing the step between.
- **This is the one that carries the most weight.** This rate rests on a
  paraprofessional line, and a line that rises because a grant ended looks exactly
  like a line that rises because the district grew. **What would settle it is the
  state’s End of Year Financial Report**, which separates spending by fund. We do
  not hold it, and it is the single most valuable document this project is missing.
- **The classification is ours.** Anyone who draws the boundary differently gets a
  different total and a different blended rate.

---

## 5. Out-of-district tuition, and why we grow it at zero

### The question

What should a line be grown at when eleven years of it show no direction at all?

### What the eleven years show

The same test as Section 4, on the district’s own budget documents back to FY17,
always at the same budget stage. Three of those years reproduce the FY27 workbook
exactly, which is what makes the other eight worth trusting.

| measurement | value |
|:--|--:|
| Budgets | 11 |
| Span | FY2017 to FY2027 |
| Lowest | $489,918 (FY2023) |
| Highest | $1,291,293 (FY2026) |
| Highest over lowest | 2.64 times |
| Years up / years down | 6 / 4 |
| Fit to a straight line | 0.10 |
| Growth rate, first year to last | 0.66% |
| Growth rate, depending where you start | -45.78% to 11.78% |

**A figure that swings from -45.78% to 11.78% depending
on the year you start counting is not a measurement of anything.** Publishing the
first-to-last rate of 0.66%, because FY2017 happens to be the
earliest year our archive reaches, would be an arbitrary choice wearing a
measurement’s clothes.

So the rate is **0.0%**, and that is a finding rather than a
gap in the work. It says: nobody can say which way this line moves next.

| FY | private placements | collaboratives | total | stage |
|:--|--:|--:|--:|:--|
| FY2017 | $581,345 | $74,189 | $655,534 | proposed |
| FY2018 | $700,270 | $60,000 | $760,270 | settled |
| FY2019 | $694,480 | $60,000 | $754,480 | settled |
| FY2020 | $600,016 | $265,730 | $865,746 | settled |
| FY2021 | $589,156 | $130,113 | $719,269 | settled |
| FY2022 | $639,156 | $179,560 | $818,716 | settled |
| FY2023 | $303,364 | $186,554 | $489,918 | settled |
| FY2024 | $310,260 | $190,979 | $501,239 | proposed |
| FY2025 | $703,872 | $460,952 | $1,164,824 | proposed |
| FY2026 | $988,630 | $302,663 | $1,291,293 | settled |
| FY2027 | $536,400 | $163,742 | $700,142 | proposed |

### The risk is priced, not hidden

A slider here would invite a reader to pick whichever number suits their argument,
and the honest answer is that nobody knows which is right. So instead the range is
priced: each row below re-runs the whole projection with tuition set to that amount.

| scenario | tuition | FY28 gap | against the budgeted figure |
|:--|--:|--:|--:|
| As the district budgeted it for FY27 | $700,142 | $680,870 | — |
| Midway back | $1,000,000 | $980,728 | +$299,858 |
| Back to the FY25 budget | $1,164,824 | $1,145,552 | +$464,682 |
| Back to the FY26 budget | $1,291,293 | $1,272,021 | +$591,151 |

The full width of that range is $591,151 of FY28
gap. It is the widest single-assumption range anywhere in this model.

### What we assumed, and what would settle it

- **Holding a line flat is itself a bet**, not a neutral act. We chose it because
  every alternative rate turned out to be an artefact of a start year, and the risk
  is carried in the table above instead of buried inside a growth rate.
- **Dollars are not children.** A -46%
  move in this line could be fewer placements, or a more honest estimate after
  years of over-budgeting, or the same children at different rates. A budget cannot
  tell those apart. **What would settle it is a count of out-of-district placements
  by year**, which nobody publishes.

---

## 6. Health insurance

### The question

Health insurance is 14.9% of the school budget and grows at
9.0%, so it contributes 0.97 points — the
largest single contribution to the gap relative to its size. What can actually be
done about it, and what does each option cost an employee?

### What goes in

Premiums from the Town’s open enrolment notice of 21 April 2026. Rates rose
5.38% for FY27. The Town pays
75% of the premium and the employee
25%.

| plan | network | deductible | family, monthly | individual, monthly | employee pays, family | employee pays, individual |
|:--|:--|:--|--:|--:|--:|--:|
| Blue Care Elect | Broadest network | $500 | $3,662.52 | $1,392.63 | $10,988 | $4,178 |
| Network Blue New England | Regional network | $500 | $2,988.41 | $1,136.28 | $8,965 | $3,409 |
| Blue Select | Narrower network | $500 | $2,599.92 | $988.56 | $7,800 | $2,966 |
| Access Blue Saver | High deductible | $2,000 / $4,000 | $2,602.28 | $989.46 | $7,807 | $2,968 |

**One correction was made to the source, and it should be on the record.** In the
rate letter, one plan has its individual and family labels transposed — the figure
labelled "individual" is plainly the family rate, matching every other plan’s
ratio. We corrected it. Silently fixing a source is how a reader ends up unable to
reproduce a figure from the document it cites, so it is said out loud instead.

### The part that is ours, and it is substantial

**How many employees are on which plan, at which tier, is not published.** The
counts below are placeholders, and the tool on the site lets you change them.

They are not arbitrary. They are set so that the Town’s
75% share reconciles to the health insurance line in the
school budget. At 194 enrollees split
55% family and
45% individual, total premium comes to
$5,331,280, of which the Town’s share is $3,998,460 —
against a budgeted $3,994,071. That is a difference of
$4,389, or
0.11%.

**But that only pins down the total, not the mix.** Which plans people are actually
on is entirely our guess, and every per-plan figure below moves with it. They should
be replaced with real counts before anybody relies on them.

### Shifting the contribution split

> District saves = total premium × (the change in the town’s share)

**It saves the district precisely what it costs employees.** There is no efficiency
in this option — it is a transfer, and the site says so wherever it appears.

| split | district saves | employee on the broadest plan pays now | would pay | change |
|:--|--:|--:|--:|--:|
| 72% town / 28% employee | $159,938 | $10,988 | $12,306 | +$1,319 |
| 70% town / 30% employee | $266,564 | $10,988 | $13,185 | +$2,198 |
| 65% town / 35% employee | $533,128 | $10,988 | $15,383 | +$4,395 |

### Moving employees to a cheaper plan

> Saving = (the dearer annual premium − the cheaper one) × how many move,
>   worked separately for family and individual coverage

Moving 40 employees from the broadest plan to the narrower one saves
$367,806 of premium in total — $275,854 to the Town and
$91,951 to the employees, who are also the ones accepting the
narrower network.

### The statutory giveback, which is easy to miss

Plan design changes go through the Public Employee Committee under Chapter 32B,
sections 21 to 23, and **25% of first-year savings must
go back to employees as mitigation.** The saving in year one is therefore
75% of the headline figure:

```
Premium moved by shifting one percentage point                $53,313
  less the 25% statutory giveback                            −$13,328
                                                      ---------------
District keeps, in year one                                   $39,985
```

Our own health panel applied that and our savings tool did not, so for a while the
two answered 33% apart for the same change. Both
apply it now.

### What we assumed, and what would settle it

- The Town, not the school district, controls the insurance group. The schools cannot change this on their own.
- Contribution splits are bargained with each union. A shift is a pay cut in everything but name, to staff who have already absorbed position reductions.
- Enrollment by plan and tier is not published. The figures here move with the counts you set, and should be replaced with real ones before anybody relies on them.
- **The 9.0% growth rate is the district’s own stated assumption**,
  not a measurement we made. Premiums themselves rose only
  5.38% for FY27 — well under it — because the rate
  covers the whole line, including how many people enrol and at which tier, not the
  premium alone.
- **What would settle the per-plan figures is enrolment by plan and tier.** One
  table that nobody publishes.

---

## 7. Free cash

### A note on why this section exists at all

Everything else in this projection is built from budget figures. Free cash is the
opposite kind of number — it is what is left over once the year is done, which makes
it an actual.

We said at the top that the two must never be combined inside one calculation. Here
is how this does not break that rule: free cash is applied as a **one-time
subtraction after every growth rate has already run**. It touches no budget group,
no growth rate, and it never carries into the next year’s base. The difference
between "a growth rate measured across that boundary" and "a labelled one-time
amount taken off at the end" is the whole of why this is allowed. It is checked
automatically at nine different draw levels, and the build fails if enabling free
cash moves anything it should not.

### What goes in

| figure | value | label | source |
|:--|--:|:--|:--|
| Certified free cash, 1 July 2025 | $3,354,370 | `published` | State Division of Local Services free cash proof |
| Identified before deductions | $3,716,282 | `published` | The same proof |
| Unspent appropriations, 2025 | $2,457,761 | `published` | The same proof, one component of it |
| Unspent appropriations, 2021–24 average | $986,340 | `measured` | Averaged from the four prior years of the proof |
| Operating budget | $51,189,961 | `published` | FY26 original appropriation |
| Recommended range | 5%–7% | `published` | The Town’s own FY27 budget release, quoting DLS |

**Three different figures are all called "the operating budget", and none of them
is the same number.** $51,189,961 as originally appropriated,
$51,531,199 as revised at the third quarter, and
$50,441,654 implied by the Town’s own published figure of
6.65%, which we cannot reproduce. No conclusion turns on the difference —
every version lands inside the recommended range — but a ratio quoted to two decimal
places should not rest on a soft denominator without saying so.

**The recommended range comes from one document, and it carries weight.** It appears
once in everything we hold: the Town’s own budget release, quoting the state. We
hold no state publication saying it. That matters, because at a lower threshold the
same balance is *above* the range rather than comfortably inside it. So the caveat
travels with the figure everywhere it is used.

**A dating trap, confirmed rather than assumed.** The state dates free cash to the
1 July on which it is certified. The Town dates the same money to the fiscal year it
can be spent in. **They are one year apart.** Lunenburg’s three largest certified
balances are 2021, 2022 and 2025; add one to each and you get exactly the three
years the Town names as its good ones.

### How much there is, as a share

> Share = certified free cash ÷ operating budget

```
Certified free cash                                        $3,354,370
Operating budget                                          $51,189,961
                                                      ---------------
Free cash as a share of the budget                              6.55%
```

Inside the 5%–7% range, near the top of it.

### What a normal year produces — the most important figure here

**The question:** is this balance a policy, or an event?

Hold everything in the 2025 certification constant except the one component that
moved, and carry the ratio between certified and identified across unchanged.

```
Identified free cash, 2025                                 $3,716,282
  less unspent appropriations in 2025                     −$2,457,761
  plus unspent appropriations at their 2021–24 average        +$986,340
                                                      ---------------
Identified, in a normal year                               $2,244,861
  × the certified-to-identified ratio of 0.9026                      
                                                      ---------------
Certified free cash, in a normal year                      $2,026,212
As a share of the operating budget                              3.96%
```

**A normal year produces $2,026,212 — 3.96%,
below the bottom of the recommended range.** This year’s record exists because 2025
unspent appropriations were 2.49 times
the town’s own four-year average — the largest jump of the nine towns in the state’s
proof:

| town | 2025 unspent, against its own 2021–24 average | share of its free cash that is unspent appropriations |
|:--|--:|--:|
| Lunenburg | 2.49 times | 66.1% |
| Ayer | 1.44 times | 60.4% |
| Groton | 1.37 times | 23.4% |
| Littleton | 1.13 times | 32.9% |
| Westford | 1.13 times | 46.5% |
| Shirley | 1.14 times | 63.7% |
| Townsend | 1.31 times | 64.2% |
| Upton | 0.72 times | 22.5% |
| Uxbridge | 0.40 times | 11.7% |

**Two different measures, and they disagree in a way worth understanding.** The
middle column asks how unusual 2025 was *for that town*, and on it Lunenburg is the
clear outlier. The right-hand column asks what the balance is *made of*, and on that
Lunenburg is the highest of the nine at 66.1% — but inside
a cluster, with Townsend at 64.2%, Shirley at 63.7%, Ayer at 60.4% not far behind. A balance built out of money
appropriated and not spent is a different thing from one built out of revenue
beating forecast, and it implies a different remedy.

**What this table deliberately does not show, and cannot.** The obvious question is
how each town’s free cash sits against the same 5–7% range, and that needs each
town’s operating budget. **The state’s proof carries no denominator** — no
population, budget, revenue or levy for any of the nine, Lunenburg included. So
Littleton’s $10,021,469 against Shirley’s $266,093
says nothing about which is closer to its own target, and a percentage-of-budget
column here would be invented rather than measured. Composition is shown instead,
because a share compares across towns of different size and an absolute dollar
figure does not.

**What would settle it:** each town’s operating budget for the same years, from the
state’s municipal finance databank. It is obtainable, and we have not obtained it.

**The state certifies less than it identifies, and we do not hold the reason.** So
that gap is carried across as an observed ratio rather than explained. It is an
input to the figure above, and it is measured rather than understood.

### What drawing the balance down would release

> Released once = certified free cash − (operating budget × share kept back)

| draw the balance down to | which is | releases, once |
|:--|:--|--:|
| 8% | above the recommended range | $0 |
| 7% | top of the recommended range | $0 |
| 6% | middle of the recommended range | $282,972 |
| 5% | bottom of the recommended range | $794,872 |
| 4% | below the range — and about what a normal year generates | $1,306,772 |
| 3% | well below the range | $1,818,671 |
| 2% | well below the range | $2,330,571 |
| 1% | nearly nothing held back | $2,842,470 |
| 0% | spend everything, hold no reserve | $3,354,370 |

**$794,872 is the headline figure** — what could be
redirected while the retained balance stays inside the range the Town itself quotes.

### One-off against policy, and the two must never be blurred

Two completely different quantities, and running them together is the most common
error in this argument:

- **Drawing the balance down to a lower target releases the accumulated balance
  ONCE.**
- **Holding it there releases the annual flow EVERY year — and that annual figure
  does not depend on the target at all.** A lower target does not generate more
  money. It releases the accumulated balance sooner, and after that you are living
  on the flow either way.

The flow is what a normal year produces: **$2,026,212**.

**And here is the difficulty, which is the honest answer to "just be less
conservative".** The flow is produced *by* the underspending. Two thirds of the 2025
balance is money appropriated and not spent. Budget more tightly and you shrink the
gap — and you shrink the free cash you were going to fill it with. You cannot count
both.

Six years of gap under each policy:

| keep in reserve | which is | released once | plus, every year | gap remaining, one-off only | gap remaining, with the policy |
|:--|:--|--:|--:|--:|--:|
| 8% | above the recommended range | $0 | $2,026,212 | $15,181,593 | $3,024,321 |
| 7% | top of the recommended range | $0 | $2,026,212 | $15,181,593 | $3,024,321 |
| 6% | middle of the recommended range | $282,972 | $2,026,212 | $14,898,621 | $2,741,349 |
| 5% | bottom of the recommended range | $794,872 | $2,026,212 | $14,386,721 | $2,229,449 |
| 4% | below the range — and about what a normal year generates | $1,306,772 | $2,026,212 | $13,874,821 | $1,717,549 |
| 3% | well below the range | $1,818,671 | $2,026,212 | $13,362,922 | $1,205,650 |
| 2% | well below the range | $2,330,571 | $2,026,212 | $12,851,022 | $693,750 |
| 1% | nearly nothing held back | $2,842,470 | $2,026,212 | $12,339,123 | $181,851 |
| 0% | spend everything, hold no reserve | $3,354,370 | $2,026,212 | $11,827,223 | -$330,049 |

### Free cash against an override — a one-off against a permanent change

The clearest single comparison in this project. The same dollars, once, against the
same dollars permanently.

> Free cash lands in one year and is gone.
> An override raises the levy limit permanently, so its value in a later year
>   = the amount × 1.025 raised to the power of the years since.

At $794,872:

| FY | gap | free cash applied | gap after free cash | override worth | gap after override |
|:--|--:|--:|--:|--:|--:|
| FY28 | $680,870 | $794,872 | -$114,002 | $794,872 | -$114,002 |
| FY29 | $1,322,303 | $0 | $1,322,303 | $814,744 | $507,559 |
| FY30 | $2,033,179 | $0 | $2,033,179 | $835,112 | $1,198,067 |
| FY31 | $2,819,056 | $0 | $2,819,056 | $855,990 | $1,963,066 |
| FY32 | $3,685,928 | $0 | $3,685,928 | $877,390 | $2,808,538 |
| FY33 | $4,640,257 | $0 | $4,640,257 | $899,325 | $3,740,932 |

| six-year total gap | amount |
|:--|--:|
| Doing nothing | $15,181,593 |
| With the free cash draw | $14,386,721 |
| With an override of the same size | $10,104,160 |

**Note what this shows, and what it must not be made to say.** An override of this
size does not close the gap either. It grows at 2.5% while the gap
grows faster, so it loses ground every year. Only a change in the cost growth rates
changes the direction.

### What redirecting free cash would cost the capital programme

**Free cash is the capital programme’s money.** Saying an amount is "available
within the guideline" without saying that is half the story.

| figure | value | source |
|:--|--:|:--|
| FY27 funded capital programme | $1,830,203 | The FY27 capital plan |
| Planned from free cash, FY27 | $991,627 | Annual Town Meeting warrant, Article 13 |
| Planned from taxation | $244,576 | The capital plan, funding page |
| Planned from the Vehicle Use Stabilization Fund | $594,000 | The same funding page |
| Average free cash into capital, ten years | $591,286 | The plan’s own Average row |
| Ranked, costed, and already unfunded | $1,437,005 across 10 projects | The same plan, below the funding line |

**A third of the programme was never school money.** $594,000
is the Vehicle Use Special Purpose Stabilization Fund, adopted at the 2017 Annual
Town Meeting for vehicles and equipment and requiring a two-thirds vote. Cancelling
what it pays for frees nothing for the schools. **So a draw can strand
$1,236,203, not the whole programme.** An earlier version of
this model took projects off the bottom of the full funded list and stranded a front
end loader with free cash that had never been paying for it.

**How that assignment is known**, since no project-by-project funding table is
published: the plan footnotes exactly two projects as funded from that stabilization
fund, and they come to exactly the $594,000 its own funding
page shows against it. That is a reconciliation, not a guess, and the model refuses
to run if it ever stops tying.

| restricted project | rank | cost |
|:--|--:|--:|
| Fire — Engine 2 - 4x4 Brush Truck (replacement) | 3 | $335,000 |
| DPW — Front End Loader with Snow Plow (replacement, retain spare) | 11 | $259,000 |

#### The dollars are exact. Which projects stop is a range.

Two different quantities, and they are kept apart.

**Dollars** need no assumption. Redirect an amount and the programme is funded by
that much less. There is a queue of ranked, costed, unfunded work worth
$1,437,005, so no dollar removed creates slack anywhere.

**Which projects stop** is a claim about how the Capital Planning Committee would
behave, and it is reported as a range between two behaviours:

- **Holding the ranking rigid** — take projects off the bottom of the published list
  until the money is found. Because projects are indivisible, this overshoots.
- **Re-sequencing** — drop whatever combination comes closest to the money removed.

| redirect | dollars out | holding the ranking | re-sequencing | projects stopped |
|--:|--:|--:|--:|--:|
| $3,354,370 | $1,236,203 | $1,236,203 | $1,236,203 | 10 |
| $2,842,470 | $1,236,203 | $1,236,203 | $1,236,203 | 10 |
| $2,330,571 | $1,236,203 | $1,236,203 | $1,236,203 | 10 |
| $1,818,671 | $1,236,203 | $1,236,203 | $1,236,203 | 10 |
| $1,306,772 | $1,236,203 | $1,236,203 | $1,236,203 | 10 |
| $794,872 | $794,872 | $817,576 | $796,203 | 8 |
| $282,972 | $282,972 | $693,949 | $287,254 | 5 |

**The difference between those two columns is not a cost.** It is the price of
assuming projects are indivisible and the order cannot change. One rank in the
middle of the list is a large roof with only a little below it, so any draw that
reaches it removes the whole roof whether it needed to or not.

**Nothing here establishes which of the two actually happens.** We hold no instance
of the committee re-ranking after a funding cut. The published ranking is evidence
of preference, not of procedure.

#### The draw against what capital normally receives

The $794,872 ceiling exceeds the *whole year’s* free cash
contribution to capital in 7 of the
10 years the plan’s own table covers:

| FY | whole capital programme | of which free cash |
|:--|--:|--:|
| FY2017 | $619,475 | $250,000 |
| FY2018 | $633,317 | $290,019 |
| FY2019 | $1,455,214 | $215,736 |
| FY2020 | $1,684,100 | $582,732 |
| FY2021 | $1,142,213 | $647,880 |
| FY2022 | $1,597,825 | $804,041 |
| FY2023 | $2,162,849 | $983,034 |
| FY2024 | $1,039,010 | $467,269 |
| FY2025 | $1,317,120 | $1,016,722 |
| FY2026 | $1,225,000 | $655,424 |

That is the capital-side twin of the normal-year finding. The draw is affordable in
this year and in few others.

### What we assumed, and what would settle it

- **The recommended range is one sentence written by one party to the argument.**
  What would settle it is the state’s own published guidance.
- **The normal-year figure holds every other component constant.** It is a
  counterfactual on one line, not a forecast.
- **The certified-to-identified ratio is carried across unexplained.**
- **Which departments turned the money back is not published** — there is a
  town-wide total and no breakdown. That is the difference between a structural
  pattern and a run of one-offs, and we cannot tell which this is.
- **Free cash is one-time by construction**, and the state’s own guidance is that it
  should not fund ongoing operations. Everything above is a deferral of the gap, not
  a closing of it.

---

## 8. Athletic fees

The most heavily corrected calculation in this project, and the section where a
reader will find the most explicit statements of what we got wrong.

### The question

What do athletic user fees raise now, and what fee would make the programme pay for
itself?

### What goes in

| figure | value | label | source |
|:--|--:|:--|:--|
| 2026-27 fee schedule | $400 1st child / $300 2nd child / $225 3rd child, family cap $1,500 | `published` | Superintendent’s email to families, August 2026 |
| 2025-26 schedule | $325 high school, $275 middle school, 25% sibling discount | `published` | School Committee vote, 26 February 2025, by roll call |
| High school participations | 582 | `published` | District planning roster |
| Middle school participations | 109 | `published` | The same roster |
| Fee revenue actually collected, FY26 | $188,944.46 | `measured` | The athletics revolving fund’s own year-end reconciliation |
| Mix of first, second and third children | 90.5% / 8.5% / 1.0% | `measured` | Counted from the district’s own by-sport workbook. See below |
| Fee waivers | 12% | `ours` | Free-lunch families are waived. Still our estimate |
| Drop-off as the fee rises | 5% of participation per $100 | `ours` | Our assumption. No local figure has ever been measured |

**Only high school participations can be charged** —
582, not the full 691. You
cannot charge a fee for a team that does not exist, and the middle school and
freshman coaching line is zero in both the level-service and the adopted budget, so
those teams do not run in FY27.

### What the average participation actually pays

A published schedule is a set of tiers. What matters for revenue is the average
across them.

> Average fee = the sum, across the tiers, of
>   (that tier’s fee × the share of participations paying it)

```
$400 for a 1st child, at 90.5% of participations              $362.08
$300 for a 2nd child, at 8.5% of participations                $25.35
$225 for a 3rd child, at 1.0% of participations                 $2.32
                                                      ---------------
Average fee per participation                                    $390
```

The family cap does not bite. Three children at the current tiers comes to
$925, under the $1,500 cap, so
only a fourth participating child would reach it.

### What the fund actually collected, and the correction it forced

This is the important part, and it is a correction to our own arithmetic.

```
What our model produces for FY26                             $176,233
What the fund reports collecting, gross                   $194,609.45
  net of refunds                                          $188,944.46
                                                      ---------------
The model produces less than the fund collected, by        $12,711.46
  as a share of what the fund collected                         6.73%
  as a share of what the model produces                         7.21%
```

**What the receipts imply each participation paid**, against the rate the School
Committee voted for that year:

|  | gross receipts | participations | implied per participation | the rate that was voted |
|:--|--:|--:|--:|--:|
| High school | $167,511.49 | 533 | $314.28 | $325 |
| Middle school | $27,097.96 | 116 | $233.60 | $275 |

**Both sit under the voted rate, and that matters, because this project used to say
they did not.** When we priced FY26 on the previous year’s schedule — a right number
from the wrong year — the implied rates came out *above* the undiscounted fee, which
is arithmetically impossible, and we treated that as proof that a count somewhere
was wrong. Correcting the fee to what was actually voted removed the impossibility.
Nothing about the fund’s figures changed. Ours did.

**What remains is an ordinary disagreement, and it is not settled.** Our assumed
waiver rate discounts the published schedule by a little more than the receipts
imply. Fewer waivers, participations undercounted, or sport surcharges outside any
schedule we hold — ice hockey and skiing normally carry them — all fit the same
figures.

**So the model is anchored to the measurement rather than corrected to it**, and the
adjustment is named rather than buried. Anchoring on what was actually collected is
right, because it is the only observed figure. Carrying that adjustment forward to a
fee this town has never charged is an assumption, and it is labelled as one
everywhere it is used.

**The two explanations imply different answers, so both are carried:**

| reading | what it assumes | how revenue behaves as the fee rises |
|:--|:--|:--|
| Cautious | There are surcharges outside the published schedule | A surcharge does not rise when the base fee rises, so the difference stays a fixed amount |
| Generous | The chargeable base is larger than we think | The difference grows in proportion with the fee |

Both reproduce FY26 exactly, by construction. They separate as the fee rises, and
the cautious one is what the site leads with.

### The sibling mix was invented, and is now counted

The clearest example in this project of an assumption being **retired** rather than
defended, so the whole path is set out.

**What it was.** 70% 1st child / 25% 2nd child / 5% 3rd child — declared openly as ours, and supported by nothing. Searching every
document in the meeting archive finds the word "sibling" in two of them, and the
only athletics one is the School Committee vote of 26 February 2025, which sets the
**discount rate** at 25%
and says nothing about how many participations receive it. Those are different
quantities — how much comes off, against how many people get it — and the closeness
of the two figures is the likeliest explanation for where the estimate came from.
That is a hypothesis, and nothing here tests it.

**What it is now.** The district’s own by-sport workbook, obtained by records
request, records the fee category of every participation, and those categories add
up to its own total — so it is this quantity exactly, not a substitute for it.

| category | participations | share |
|:--|--:|--:|
| Full pay | 993 | 78.44% |
| 2nd sibling | 107 | 8.45% |
| 3rd sibling | 13 | 1.03% |
| Reduced fee | 20 | 1.58% |
| Full waiver | 133 | 10.51% |
| **Total** | **1,266** |  |

**Coverage, stated rather than implied.** 46 sport-years and
1,266 participations — meaning every sport, in every
year, whose fee categories add up to the total the workbook itself prints for that
sport. Rows that do not add up are left out, because where they disagree there is no
way to tell which figure is wrong. Three reasons they disagree, and only the first
would be ours to fix:

- **The workbook mixes units.** One sheet’s total row multiplies the counts by the
  fee and prints dollars, while the rows above it are counts of children. A few
  individual entries carry dollars in a column that otherwise holds counts.
- **Some of its totals are off by one** against the rows above them.
- **The 2025-26 fee-category columns are empty throughout**, which is why a separate
  one-page count sheet had to exist at all.

Every one of those mismatches is published rather than hidden or quietly repaired,
because those totals are wrong in the source document, and that is a fact about the
document rather than a defect in our reading of it.

**Two sources, two different years, one answer.** The workbook covers FY2024 and
FY2025. The one-page count sheet covers FY2026, the year the workbook leaves blank.
They are consecutive readings rather than a check on each other:

| source | year | took a sibling discount | received a full waiver |
|:--|:--|--:|--:|
| By-sport workbook | FY2024–FY2025 | 9.5% | 10.5% |
| One-page count sheet | FY2026 | 6.9% | 13.3% |
| What we used to assume | — | 30% | 12% |

**The waiver estimate survived. The sibling one did not.** One invented figure turned
out close, and the other was out by roughly a factor of four.

**Why correcting it moved the published figures less than you would expect.** The fee
model is anchored to what the fund actually collected, so raising what the model
produces lowered the adjustment by nearly as much, and the two offset. Revenue at
today’s fee barely moved; the average fee moved several percent. **That is exactly
why an input wrong by a factor of four survived as long as it did — nothing in the
output looked wrong.** The figure that did improve is the unexplained difference,
which is the thing the adjustment represents.

**What it still does not establish.** Two years, neither of them the year the current
fee schedule applies to. If the new schedule and the larger family cap change how
many families enrol a second child, this mix moves and nothing here would show it.

### What happens as the fee rises

Raising a fee raises more per family and prices some families out, so revenue rises,
peaks, and then falls.

> Revenue = fee × chargeable participations × (1 − the waiver rate) × the share who stay
> where the share who stay = 1 − (the increase ÷ $100) × 5%

| fee per season | revenue, cautious reading | revenue, generous reading |
|--:|--:|--:|
| $390 | $212,454 | $214,144 |
| $500 | $254,008 | $259,443 |
| $700 | $313,684 | $324,785 |
| $900 | $352,873 | $368,163 |
| $1,100 | $371,576 | $389,577 |
| $1,300 | $369,793 | $389,028 |

**Revenue peaks at about $1,185 a season and roughly
$373,322.** Anything above that is unreachable at any price, which is
the most useful single thing this curve says.

### What self-funding would take

The adopted budget funds $217,908 of athletics **and no
athletic transportation at all.** Put the $127,550 of
buses back — a team that cannot reach an away game is not a team — and the cost of
fielding these teams is $345,458.

| target | covered at today’s fee | fee that would cover it |
|:--|--:|--:|
| The adopted budget, no buses | 97.50% | $400–$405 |
| With athletic transportation restored | 61.50% | $785–$855 |

**Two figures rather than one**, because the data cannot say which reading of the
collection difference is right, and a single number on a page asking families to pay
it would be a false precision.

### What we assumed, and what would settle it

- **The waiver rate is still ours.** Free-lunch families have the fee waived; the
  district does not publish how many.
- **The drop-off as fees rise is ours.** No local figure has ever been measured. It
  is a shape, not a finding.
- **The adjustment carries a measured FY26 difference forward to fees this town has
  never charged.** That is the largest assumption in this section.
- **The sibling mix is no longer ours**, but it is measured over two years that are
  not the year the current schedule applies to.
- **A budget line is not what athletics costs.** The district published athletics
  against the revolving fund once, for FY19. In FY26 the general fund and the fund
  together came to $665,245.44, of which the fee-funded fund
  paid 22.08%. The fee figures here are modelled against the
  general fund programme because that is what the district publishes — which makes
  them a floor rather than the cost.
- **What would settle it: participation counts by fee category for the current year,
  and the revolving fund’s own ledger by object code.**

---

## 9. The other savings and revenue options

Each control on the site is one of four shapes, and the shape decides the
arithmetic.

| shape | how it is worked out | used by |
|:--|:--|:--|
| A fee | The curve in Section 8, with its own drop-off rate | Athletics, buses, activities |
| A contribution split | The premium moved, less the statutory giveback | Health insurance |
| A percentage of a line | That share of the line, capped | Technology |
| A list of named positions | The sum of the ones actually chosen | Administration |

**Fee options are not interchangeable.** A bus rider stops paying sooner than an
athlete does, so the drop-off differs between them.

### Every option, its base and its ceiling

| option | kind | base (people, or dollars) | base is | most it can raise |
|:--|:--|:--|:--|:--|
| Athletics user fees | revenue | 582 |  | $345,458 |
| Band, music & club fees | revenue | 375 | `ours` | $106,244 |
| School bus fees | revenue | 420 | `ours` | $1,053,360 |
| Health insurance — employee share | saving | $5,331,280 |  | $599,769 |
| Administration | saving | $2,116,910 |  | $736,468 |
| Software, licenses & devices | saving | $638,675 |  | $383,205 |

**The ceiling is the point of that table.** Every one of these is bounded, and
several are bounded well below the thing they are meant to pay for. General
education transportation costs $1,053,360 and bus fee revenue
peaks near $146,006.
Special education transportation, at $649,953, cannot be
charged for at all.

**Two of the bases are ours and are placeholders** — how many students take part in
activities, and how many ride the bus. The district publishes neither. Any figure
resting on them moves with counts nobody has confirmed, and the site marks them.

### Administration, and why it is a list rather than a percentage

**A percentage of administration is not a decision anybody can take.** Nobody votes
to reduce administration by a percentage. They vote to stop funding a Human Resource
Specialist, or they do not. So this is a list of real budget lines from the adopted
FY27 budget, ordered from what a district can genuinely absorb to what it legally
cannot give up.

**The amounts are the district’s. The ordering is ours**, and it is stated as such.

```
Administration, every line                                 $2,633,246
  as a share of the school appropriation                         9.9%
  of which central office                                  $1,040,389
  of which the four principals’ offices                    $1,183,773
                                                      ---------------
Positions a lawful budget could cut (14 of 21)               $736,468
  as a share of all administration                                28%
```

**The positions that cannot lawfully be cut are shown anyway, and flagged.** A
superintendent, a business manager, a special education administrator and four
principals are roles the Commonwealth requires. Refusing to show what cutting them
would save reads as evasion rather than rigour, and "what would that even save?" is
a question a resident is entitled to an answer to.

**One deliberate omission.** The two technology lines that sit inside administration
belong to the technology option and are not counted here. Counting a line in two
places is how a model quietly closes the same gap twice.

---

## 10. What happens if the gap is closed by cutting

### How it works

Each year, programmes are cut from the bottom of a priority ranking upward until
that year’s gap is closed. A cut permanently reduces the salary base, so it also
lowers every later year’s cost.

**That last point is the whole lesson.** A cut lowers the cost curve once and the
curve then climbs at exactly the rate it was climbing before. The money saved never
gets its raise either — and the gap still grows.

### The four rankings

| ranking | what it is |
|:--|:--|
| School Committee's revealed priorities | The order Lunenburg itself sacrificed things across its own four FY27 scenarios. Athletics and arts went first; special education, mandated services and classroom teachers were defended longest. |
| What comparable districts actually do | Observed sequence across Easthampton, Bridgewater-Raynham, South Hadley, Groton-Dunstable and Winchester: revenue levers and non-personnel first, then enrichment, then support staff, then classroom teachers last. |
| What we’d do | Early literacy first, because it is the one loss that cannot be made up later. Classrooms next, because class size is what makes families leave. Athletics and arts sit at the bottom NOT because they matter least, but because they are the only things here that can pay for themselves — fund them with fees and they never reach the cut line at all. |
| Academics above all | Protect instruction and advanced coursework at any cost to everything else. Shows how far enrichment alone can carry you -- and where it stops. |

Worked below with **School Committee's revealed priorities** — the order Lunenburg itself sacrificed things
across its own four FY27 scenarios, which is a revealed preference rather than a
stated one.

**The gap column here is not the gap column in Section 1.** There, each year
assumes nothing was ever done. Here, each year is what remains after every earlier
year has already been cut — which is why the figures are so much smaller. That
difference is the whole argument for acting early rather than late.

| FY | shortfall that year, after earlier years have been cut | cut | cumulative positions lost | still unclosed |
|:--|--:|--:|--:|--:|
| FY28 | $680,870 | $729,447 | 2.9 | — |
| FY29 | $563,678 | $563,993 | 4.9 | — |
| FY30 | $657,656 | $745,176 | 14.7 | — |
| FY31 | $613,530 | $666,309 | 19.2 | — |
| FY32 | $699,219 | $749,527 | 24.2 | — |

### Where the cutting stops, which is ours

**What actually happens in the model:** any programme we have classified as legally
mandated is skipped entirely. It appears in the year’s list, marked as blocked, and
its money never counts toward closing the gap. There is no partial cut of a mandated
programme — it is all or nothing, and it is nothing.

**A cascade has to stop somewhere, so we made it stop. No document we hold establishes a legal minimum for any of these programs.**

Between the FY26 and FY27 budgets the district cut ten special education lines totalling $224,049 — including an entire Elementary School Psychologist, from $98,784 to nothing. Cutting a service that is still owed does not save the money. It moves the cost somewhere a budget cannot see it.

So the honest statement is not "here is the floor". It is that every year the
district has taken a little more out of something it is legally obliged to provide,
and nobody has established where that stops.

### What we assumed, and what would settle it

- **The programme list is partly ours.** Some entries are priced from the district’s
  own cut and restoration lists. Some are our estimates, and the site marks which.
- **The rankings are preferences, not forecasts.** Three of the four are
  reconstructions of somebody’s revealed order; one is explicitly what we would do.
- **Cutting a service that is still legally owed does not save the money.** It moves
  the cost somewhere a budget cannot see it, and nothing in this model can follow it
  there.

---

## 11. The tax base, new growth, and overrides

Everything a resident meets on their own bill.

### What goes in

| figure | value | label |
|:--|--:|:--|
| FY26 tax rate, single rate | $14.39 per $1,000 | `published` |
| FY26 levy | $35,819,996 | `published` |
| Total taxable value | $2,489,228,353 | `measured` |
| Residential share of value | 91% | `published` |
| Commercial, industrial and personal | 9% | `published` |
| Average single-family value | $517,296 | `published` |
| Average tax bill | $7,444 | `published` |
| Chapter 70 aid, FY27 | $9,349,335 | `published` |
| District enrollment | 1,581 | `published` |

> Total taxable value = levy ÷ tax rate × 1,000

It is not read off an assessment report. It reproduces the Assessors’ own class
totals closely, but it is a calculation rather than a transcription.

### What one student costs the levy

```
School appropriation                                      $26,572,288
  less Chapter 70 aid                                     −$9,349,335
                                                      ---------------
Raised locally                                            $17,222,953
  ÷ 1,581 students                                                   
                                                      ---------------
Local cost per pupil                                          $10,894
                                                      ---------------
Schools as a share of the omnibus budget                       53.18%
School share of the average tax bill                           $3,959
                                                      ---------------
Average homes needed to educate one child                        2.75
```

**It takes about 3 average homes, in school-tax terms, to
educate one child.** That is the arithmetic behind why residential development does
not pay for itself and commercial development does.

### New growth

**New growth is permanent.** Value added to the tax rolls is added to the levy limit
at the prior year’s rate, and it stays there and grows at the cap thereafter.

> Revenue = new taxable value × $14.39 ÷ 1,000
> So $1,000,000 of new value = $14,390 a year, permanently

The town budgets $400,000 of new growth a year, which
implies about $27,797,081 of new taxable value being added
annually, most of it residential.

### The correction that halved this answer

**The schools do not receive a levy dollar.** New growth is added to the *town’s*
levy limit. The schools then receive their share of the town’s total available
revenue. Comparing gross new-growth revenue against the school gap — as this tool
once did — credits the schools with money that goes to the fire department, and
roughly doubles what commercial development appears to be worth.

```
A dollar added to the town’s levy limit                         $1.00
  of which reaches the schools                                  $0.54
                                                      ---------------
FY28 school gap                                              $680,870
  levy needed to close it                                  $1,263,599
  new taxable value needed, in one year                   $87,810,897
```

### The same requirement, in buildings

Abstractions do not survive a public meeting, so the same figure is expressed in
things a town actually permits.

| unit | assessed value | needed to close the FY28 gap in one year |
|:--|--:|--:|
| An average existing Lunenburg business | $658,001 | 72 of them |
| A typical mixed development | $3,005,000 | 15.7 of them |
| The town’s entire recent annual new growth | $17,348,853 | 2.7 times it |

72 average businesses is 31% of
every business in town — there are 234, per the 2024 Census
Business Patterns — added in a single year, and again the next year, because the gap
grows.

**The development values are ours**, order-of-magnitude estimates rather than
Lunenburg assessments, and the site lets you change them. They exist so that people
can reason in buildings rather than in millions. The one figure that is not ours is
the average existing business: $153,972,120 of commercial, industrial
and personal property across 234 establishments, from the tax
rolls.

### Does new growth lower my tax bill?

Almost not at all, and the arithmetic says why. **New growth adds revenue and
taxable value in nearly the same proportion**, so it barely moves the rate. The town
levies essentially to its maximum every year — excess capacity has been single-digit
thousands — so the levy rises by the cap plus new growth, and the rate is whatever
satisfies levy divided by value.

> Tax rate = levy ÷ total taxable value × 1,000

| new commercial value | rate without it | rate with it | effect on the average bill | revenue raised | share of the FY28 gap |
|--:|--:|--:|--:|--:|--:|
| $5,000,000 | $14.7498 | $14.7490 | -$0.36 | $71,950 | 11% |
| $15,000,000 | $14.7498 | $14.7476 | -$1.14 | $215,850 | 32% |
| $30,000,000 | $14.7498 | $14.7455 | -$2.22 | $431,700 | 63% |

**The benefit of commercial growth is not a lower rate. It is a bill that rises more
slowly than it otherwise would**, because the alternative to new growth is an
override or a cut.

### Overrides

A Proposition 2½ override raises the levy limit **once, permanently**. The base then
grows at 2.5% a year like the rest of the levy.

> Cost to one household = the override amount ÷ total taxable value × that home’s value

```
An override covering the whole FY28 school gap               $680,870
  cost to the average home, per year                          $141.49
                                                      ---------------
The same, if the question is town-wide rather than school-only       $1,263,599
  cost to the average home, per year                          $262.59
```

A general override has to be about 1.9 times the size to do the same
work for the schools, because the schools receive only 53.88% of a levy
dollar.

### How much a new override would have to raise, every year

**Residents hear "an override fixes it" and reasonably assume one ballot question.**
What the arithmetic asks for is a new one every spring. This is the amount by which
the gap grows in each year beyond what last year’s gap would have grown to on its
own — the fresh hole, over and above the one already there.

> Fresh gap = this year’s gap − (last year’s gap × (1 + the town’s revenue growth))

| FY | total gap | the fresh part of it | town-wide question needed to raise that |
|:--|--:|--:|--:|
| FY28 | $680,870 | $680,870 | $1,263,599 |
| FY29 | $1,322,303 | $620,775 | $1,152,071 |
| FY30 | $2,033,179 | $671,009 | $1,245,298 |
| FY31 | $2,819,056 | $724,943 | $1,345,392 |
| FY32 | $3,685,928 | $782,892 | $1,452,937 |
| FY33 | $4,640,257 | $845,152 | $1,568,483 |

Each town-wide question is about 1.9 times the fresh school gap,
because the schools receive only a share of a levy dollar.

**One warning about how overrides are often modelled, including by us.** It is easy
to build a projection in which an override passes *every year*. That is a different
and much rarer thing than one ballot question, and it overstates the effect by
roughly the number of years projected. The figures on the site use the one-time
model, which is what a ballot question actually does.

### What we assumed, and what would settle it

- **The development values are ours.** The 91% residential
  share, the rate, the levy and the average bill are the town’s own published
  figures.
- **Total taxable value is calculated, not transcribed.**
- **The town levies to its maximum.** True in every year we hold. Not a law.
- **New growth is assumed flat at $400,000.** The Assessors’ own
  series runs from $481,496 in
  FY2018 to
  $234,383 in
  FY2023 — not every year down, but ending well
  below the assumption. And every commercial class **shrank in absolute dollars** in
  the most recent year we hold. This is the assumption most likely to be optimistic.

---

## 12. Every assumption, what it is worth, and what backs it

**If you want to argue with this projection, start here.** A projection is
assumptions — the question is never whether a figure is assumed, but whether the
assumption is warranted and whether anything better is available.

This is the whole list, sorted by how much each one moves the answer, so an argument
can start where it matters rather than where it is easiest. The effects are the
change in the gap from moving that one assumption and nothing else. They are
produced by running the real projection twice, not estimated.

| assumption | currently | moved by | FY28 gap | FY33 gap | grade | what backs it |
|:--|--:|--:|--:|--:|:--|:--|
| Levy growth | 2.50% | +1 point | −$183,923 | −$1,314,411 | `given` | Proposition 2½. Fixed by statute |
| Salary growth | 4.00% | +1 point | +$134,097 | +$1,002,730 | `given` | The teachers’ agreement — scale increases plus steps |
| State aid growth | 2.00% | +1 point | −$63,992 | −$434,441 | **`BARE`** | Nothing. No stated source and no derivation — see below |
| Special education, in district | 6.49% | +1 point | +$54,662 | +$459,768 | `derived` | Two contracts and two measured trends, weighted by share — Section 4, with the trend tests and a five-point range published beside it |
| New growth per year | $400,000 | +$100,000 | −$53,883 | −$344,193 | `given` | The town’s own FY27 estimate — though its own series has been falling, Section 11 |
| Health insurance | 9.00% | +1 point | +$40,191 | +$379,645 | `given` | The district’s own stated assumption for FY27 |
| Local receipts growth | 1.00% | +1 point | −$18,902 | −$122,189 | **`BARE`** | Nothing. No stated source and no derivation — see below |
| Everything else | 3.00% | +1 point | +$17,721 | +$126,289 | `given` | The district’s own stated assumption for FY27 |
| Transportation | 6.00% | +1 point | +$10,534 | +$86,598 | `judged` | The district assumed 10%. This is softer, and ours, and rests on no trend test |
| Out-of-district tuition | 0.00% | +1 point | +$7,002 | +$43,073 | `derived` | Held flat because eleven budgets show no trend — Section 5. The risk is priced as scenarios instead |
| Utilities | 5.00% | +1 point | +$6,055 | +$47,486 | `given` | The district’s own stated assumption for FY27 |

| grade | means |
|:--|:--|
| `given` | Somebody else’s figure — a contract, a statute, or a number the town or district published. We transcribed it. |
| `derived` | We calculated it from their data, and the calculation is set out in this document with its own test. |
| `judged` | Our estimate, with a stated argument behind it. |
| **`BARE`** | A number with nothing behind it. Argue with these first — so do we. |

### The two with nothing behind them

State aid is assumed to grow at 2.0% a year and local
receipts at 1.0%. **Neither figure has a stated
source or a derivation.** Every other rate in this model carries one. These two
carry nothing, and we are naming them rather than waiting for somebody else to.

**State aid is the more serious of the two.** It is worth
$63,992 of FY28 gap for every point it moves —
the second largest revenue lever in the model, and larger than the entire
transportation growth rate by a factor of
6.

It also governs the single largest figure the town does not control. Chapter 70 is
about $9,349,335 of a $26,572,288 school budget,
and it is set in the Governor’s budget rather than by anything Lunenburg does. An
assumption about it ought to look like the priced scenarios in Section 5 rather than
a single figure with nothing beneath it.

**Local receipts matter less**, but the same objection applies.

**Neither has been changed.** Naming a weakness is not the same as fixing it, and
changing a rate changes published figures — which is a decision for the people who
have to defend them, not a correction we should make quietly.

### Assumptions that do not affect the projection

These move individual pages rather than the gap. Every one of them is ours.

| assumption | currently | affects | standing |
|:--|:--|:--|:--|
| Sibling mix in athletics | 9.5% take a discount | Every fee figure, Section 8 | **no longer an assumption** — counted over 1,266 participations |
| Athletic fee waivers | 12% | Every fee figure, Section 8 | still ours; two counts put it at 10.5% and 13.3% |
| Drop-off as fees rise | 5% per $100 | The fee curve, Section 8 | no local figure has ever been measured |
| Health enrolment by plan and tier | 194 enrollees | The per-plan figures, Section 6 | the total reconciles to the budget; the mix is ours |
| Development values | order of magnitude | The buildings-per-gap figures, Section 11 | ours, and editable on the site |
| Cut priority orders | four rankings | Which programme falls, Section 10 | preferences, not forecasts |

**The pattern worth naming.** How well an assumption is supported tracks how much it
matters, almost everywhere in this model. The four largest levers are a signed
contract, a statute, the district’s own figure, and the one rate we derived over ten
budgets with its test published beside it. The weakly founded assumptions are mostly
small ones. There are two exceptions, and they are named above: state aid, which is
large and bare, and — until it was corrected — the sibling mix, which was small and
wrong.

---

## 13. How this is checked

Every claim above is checked by something that runs automatically, because this
project’s own history is of checks that existed and were never run. The commands are
in Appendix A. What they prove is here.

| what is checked | what it proves |
|:--|:--|
| Budget figures never meet actual spending | No part of the projection reads a column of actual spending. The build fails if one ever does. |
| Free cash stays outside the growth rates | Enabling free cash at nine different draw levels moves nothing except the free cash figures themselves. |
| The assumptions against history | Every growth rate compared with what that line actually did, budget to budget. |
| The expense base rebuilds the appropriation | The line items add back up to the published school appropriation, within rounding. |
| Every source document is present | Everything catalogued is actually there and downloadable. |
| This document is not stale | It is regenerated and compared. A stale copy fails the build. |
| The published figures on the site match the model | The site is rebuilt and the figures it serves are compared against the model that produced them. |

### Three checks that refuse to publish rather than warn

- **The capital plan extract must reproduce the plan’s own printed average**, for
  free cash into capital and for the whole programme. It was two rows short of that
  for a while and nothing noticed, because the average printed beside it had been
  typed in rather than calculated.
- **The restricted capital projects must come to exactly what the plan’s funding
  page shows against that fund**, and the rest must come to free cash plus taxation.
  Both are checked before anything is calculated from them.
- **The town ledger extract must tie to the report’s own grand total.** It once
  silently dropped 16 of 67 departments, because the accounting system prints a zero
  as ".00" and our pattern expected a digit before the decimal point. $4,074,773 of
  revised budget was invisible for weeks, including a $2.4 million assessment.
  Nothing caught it because nothing compared the extract against the total the report
  itself prints. It does now, and it refuses to save if it does not tie.

**The general lesson, and the reason this section exists:** any instrument that
reformats a document before you read it is part of the finding, and has to be
checked like one.

---

## 14. What none of this can tell you

Some figures would settle more than any amount of further analysis. They are not
published, and no arithmetic on what *is* published substitutes for them.

- **A count of out-of-district special education placements by year.** Dollars
  cannot distinguish fewer children from a more honest estimate. Section 5 rests on
  this.
- **How grants and state funding map onto the budget lines.** The budget shows the
  general fund and nothing else, so a line rising because a grant ended looks exactly
  like a line rising because the district grew. **This is the one that carries the
  most weight**: the special education growth rate in Section 4 rests on a
  paraprofessional line, and it cannot currently be distinguished from grant money
  unwinding. The state’s End of Year Financial Report would answer it.
- **Whether budgeted positions were actually filled.** A budget line is an intention.
- **Health insurance enrolment by plan and tier.** Section 6 is calibrated to a total
  and guesses the shape.
- **Athletic participation by fee category for the current year**, and the revolving
  fund’s own ledger by object code.
- **FY26 year-end figures.** Everything we hold for FY26 stops at 31 March 2026.

### And the two mistakes this document exists to prevent

**An explanation is not a measurement.** A number calculated from the data is a
fact. An explanation for why that number moved is a hypothesis, however obvious it
feels, and it has to be labelled as one every time. Dollars are not students. A
budget line is not a filled position. A count of documents is not a count of
decisions. Where the actual quantity is not published, the honest sentence is that we
cannot say — not a number inferred from something adjacent to it.

**Quote the source, never your own rendering of it.** Every serious error in this
project has had the same shape: something we derived got quoted as though it had been
observed. Not invented — derived, which is exactly why it survives review. A tidy
table is for reading, never for quoting. If you cannot point to the page or the cell,
you have not checked it.

---

## Appendix A — For anyone reproducing the arithmetic

Nothing in this appendix is needed to follow the argument. It is here so that
somebody who wants to rerun any figure above can find it.

### Where each section is built

| section | built by | from |
|:--|:--|:--|
| 1, 2, 3 — the projection | `model/finance.py` | `sources/data/lps-budget-lines.csv` |
| 4, 5 — special education | `model/sped.py` | the same file, plus the budget history extracts |
| 6 — health insurance | `model/health.py` | the Town’s open enrolment notice |
| 7 — free cash | `model/freecash.py` | `sources/dls/`, `sources/data/capital-plan-fy27.csv` |
| 8 — athletic fees | `model/athletics.py` | `sources/munis-ledgers/account-details/`, `sources/data/athletics-by-sport.csv` |
| 9 — the options | `model/levers.py` | the FY27 line-item budget |
| 10 — the cut cascade | `model/cascade.py` | `model/catalog.py` |
| 11 — tax base and overrides | `model/taxbase.py` | the FY2023 Tax Classification Hearing |
| 12 — the assumption register | this script | the live model, run twice per assumption |

### Rebuilding and checking

```
python3 model/export.py                          regenerate the site’s data file
python3 scripts/build_show_your_work.py           regenerate this document
python3 scripts/build_show_your_work.py --check   fail if this document is stale
python3 scripts/audit_provenance.py               budgets never meet actuals, free
                                                  cash stays inert, and both of the
                                                  above are fresh
python3 scripts/backtest_rates.py                 assumptions against history
python3 scripts/build_source_index.py             every source present, catalogued
python3 scripts/verify_athletics.py               the athletics analysis, recomputed
python3 scripts/verify_free_cash.py               the free cash analysis, recomputed
npm run check:agents                              the live site matches the model
```

### The data, published directly

Everything the site computes is available as files, without going through the pages:

| file | what it holds |
|:--|:--|
| `/data/model.json` | every figure the site computes, including which are ours and which are published |
| `/data/budget-lines.csv` | the district budget, line by line, every year and scenario |
| `/data/sped-lines.csv` | every line counted as special education, and which rule caught it |
| `/data/ood-tuition-history.csv` | out-of-district tuition, FY17 to FY27 |
| `/data/free-cash-proof.csv` | the state’s free cash proof, nine towns, 2021–2025 |
| `/data/rate-register.csv` | every rate this project knows about, with the year it applies to and the document that set it |
| `/data/athletics-by-sport.csv` | the district’s own by-sport workbook, tidied |
| `/data/sources.json` | the whole document archive, with a checksum for each file |

---

## Appendix B — The interactive tools, and why they agree with this

Two pages on the site let you move the figures yourself: one that adjusts the growth
rates, and one that models redirecting free cash away from capital projects.

Both have to respond instantly to a dragged control, which means the arithmetic is
written a second time, in the language the browser runs. **The same rule implemented
twice is a discrepancy waiting to happen**, and this project has been caught by
exactly that before.

So each of them checks itself against the published model every time the page loads,
and shows a visible warning in the interface if the two ever disagree. The rate page
compares its projection year by year against the model’s and fails on a difference of
more than a dollar. The capital page compares its answer against the model’s at every
draw level the model publishes.

**One of those checks existed as an uncalled function for months.** A check that does
not run is not a check. Both now run on load, and both are also verified against the
live site after every deployment.

---

## Where to go from here

| for | see |
|:--|:--|
| The conclusions this arithmetic supports | the analyses on the site |
| Every source document, with its address and a checksum | `/sources` |
| Every rate, with the year it applies to and who set it | `/rate-register` |
| What this project knows it does not know | Section 14 above |

*Every figure in this document is generated from the model that produces the site.*
*If a number here disagrees with a page on the site, one of the two is stale — and*
*if a number here disagrees with a source document, the source document is right.*
