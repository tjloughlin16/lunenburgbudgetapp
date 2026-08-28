# Special education and the curve


> **Working state:** `notes/HANDOFF.md` carries the current branch, the open
> decisions and what is established versus assumed. `CLAUDE.md` carries the rules.

**How special education bears on the rate problem — using budgets only.**

Analysis, August 2026.

Every figure here comes from a budget column: what was voted or proposed. No
actual-spending column is used anywhere. That is a deliberate constraint, because this
site projects appropriations, and a rate measured from what was spent to what was budgeted
is partly growth and partly the gap between those two things. What the town actually spent
is a separate question, in `budget-vs-actual.md`.

---

## The short version

The FY27 level-service budget rises **3.98%**. Strip out one line and it rises **6.23%**.

That line is out-of-district tuition, which the district budgeted **down 46%** — a fall of
$591,151 in a single year. It masks a **9.5% increase in in-district special education**,
which is the second-largest contributor to cost growth in the whole budget.

A 46% fall in purchased placements is a **level** change. It can happen once. The 9.5% is
a **rate**, and rates keep going.

---

## What counts as special education here

**There is no account code for it.** The state's chart of accounts has no special
education total, and two of the groups the district reports carry both kinds of cost at
once: 2330 is paraprofessionals, general and special education together, and 3300 is
transportation, where the special education runs sit beside the yellow buses. Every figure
below therefore rests on a classification somebody made. This one is ours.

The rule has two parts:

1. **8 function groups are special education outright**, and every line inside them
   counts — 48 lines.
2. **Inside the mixed groups, a line counts when the district's own label says so** —
   8 lines.

Together, **56 lines totalling $5,745,543**, which is the amount every projection
here starts from.

The groups taken whole:

- `2110 - Special Education`
- `2110 - Special Education Clerical`
- `2310 - Teachers Specialists - Special Education`
- `2320 - Therapeutic Services`
- `2325 - Special Education Substitutes`
- `2330 - Paraprofessionals Special Education *** (LTP notes)`
- `2800 - Psych. Services`
- `2800 - Psychological Services`

The 8 lines caught by their name rather than their group, one of which is most of the
money:

| line | FY27 |
|---|---:|
| Special Education Transportation - System | $649,953 |
| Special Ed Hospital Tutoring | $10,000 |
| Special Ed Contrctd Evaluations | $8,000 |
| Special Ed Equipment | $4,000 |
| E.S. Special Education Instr. Materials | $3,317 |
| H.S. Special Education Instr. Materials | $2,215 |
| P.S. Special Education Instr. Materials | $1,800 |
| M.S. Special Education Instr. Materials | $452 |

**What was deliberately left out.** A classification is defined as much by its edges as by
its middle.

- **2330 - Paraprofessionals General Education** — General education aides. The group next to the special education one, and the single boundary most likely to be crossed by accident in either direction. FY25 $121,233, FY26 $0, FY27 $0.
- **9300 / 9400 — out-of-district tuition** — Special education, but escalated on its own because it is set by placement rather than by payroll, and it behaves nothing like staffing. FY25 $1,164,824, FY26 $1,291,293, FY27 $700,142.

The general education aides are worth a second look. They are budgeted at nothing from
FY26 onward, so in FY27 that boundary costs nothing either way — but they were
$121,233 in FY25, which is the base year of the two-year rates below. A boundary can
be irrelevant in the year you show and matter in the year you are comparing against.

Every line is published as a spreadsheet at `/data/sped-lines.csv`, with the reason each
was counted, so the total can be added up without taking any of this on trust.

---

## What "the curve" means here

The site's central argument is that Lunenburg has a rate problem rather than a bad year:
Proposition 2½ caps the levy at 2.5%, costs rise faster, and two things compounding at
different speeds pull apart for ever.

The cleanest measure of the cost rate is the district's own. **Level service** is its
arithmetic for what the same staff, the same programs and the same children cost one
year later. That is the definition of an escalator, and it needs no assumption from us.

| | |
|---|---:|
| FY26 budget | $26,287,476 |
| FY27 level service | $27,333,289 |
| **Increase** | **$1,045,813 — 3.98%** |

Against a 2.5% levy cap, a 1.48-point gap.

---

## Where that increase comes from

| bucket | FY26 | FY27 level service | change | rate | share of the increase |
|---|---:|---:|---:|---:|---:|
| Salaries | 12,615,467 | 13,308,517 | +693,050 | 5.5% | 66% |
| **Special education, in district** | **5,158,207** | **5,649,284** | **+491,077** | **9.5%** | **47%** |
| Health insurance | 3,752,258 | 4,068,166 | +315,908 | 8.4% | 30% |
| Transportation | 965,500 | 1,053,360 | +87,860 | 9.1% | 8% |
| Utilities | 548,450 | 605,511 | +57,061 | 10.4% | 5% |
| Everything else | 1,956,301 | 1,948,309 | −7,992 | −0.4% | −1% |
| **Out-of-district tuition** | **1,291,293** | **700,142** | **−591,151** | **−45.8%** | **−57%** |

Shares exceed 100% because one line runs the other way.

In-district special education is the **second-largest single contributor to cost growth**,
at more than twice the blended rate. Taken all in — including tuition — special education
made the level-service budget $100,074 *smaller*.

Both statements are true. Which one is useful depends on whether the tuition fall repeats.

---

## The whole thing is one trade

Split special education into its parts and the year is not a general increase. It is two
entries moving in opposite directions:

| part | FY25 budget | FY26 budget | FY27 level service | change | rate |
|---|---:|---:|---:|---:|---:|
| **Paraprofessionals** | 1,376,893 | 1,344,373 | **1,874,411** | **+530,038** | **+39.4%** |
| Special education transport | 445,328 | 565,734 | 649,953 | +84,219 | +14.9% |
| Speech, OT and summer services | 768,573 | 753,555 | 784,444 | +30,889 | +4.1% |
| Substitutes | 52,500 | 52,500 | 52,500 | 0 | 0% |
| Administration, legal, supplies | 145,467 | 167,842 | 134,741 | −33,101 | −19.7% |
| Special education teachers | 1,979,158 | 1,978,848 | 1,945,512 | −33,336 | −1.7% |
| Psychologists and testing | 270,675 | 295,355 | 207,723 | −87,632 | −29.7% |
| **Out-of-district tuition** | 1,164,824 | 1,291,293 | **700,142** | **−591,151** | **−45.8%** |

Teachers are flat. Therapists are near flat. Substitutes are identical. The year is
**+$530,038 of paraprofessionals against −$591,151 of purchased placements**, and
everything else is noise around it.

**What the budget shows:** those two lines moved by nearly the same amount, in opposite
directions, in the same year. That is all the budget shows. It does not show that any
child moved, that the two decisions were connected, or that one caused the other.

**What a document says:** the district's FY27 presentation to the Finance Committee states
its own reasoning — *"Investing in internal staff is significantly more cost-effective
than tuition and transportation for OOD placements."* That is the district describing its
intent, in writing. It is evidence of intent. It is not evidence of what happened.

---

## Why it matters to the curve

**The published rate is flattered by a one-off.**

| | FY26 → FY27 level service | gap to the 2.5% cap |
|---|---:|---:|
| As published | **3.98%** | 1.48 points |
| If tuition had held flat | **6.23%** | **3.73 points** |

One line bends the published cost rate down by **2.25 points**. Remove it and the gap to
the levy cap is two and a half times wider.

**The two halves of the trade are not equally durable.**

- The tuition reduction is a level change that cannot repeat. Placements can be brought
  home once. There is no second 46%.
- The paraprofessional increase is permanent headcount. It escalates at the AFSCME
  agreement's rate — 3.0%, 2.0%, 2.0% through FY28 — for ever after.

So the district enters FY28 carrying a **$1.87M paraprofessional base**, up from $1.34M,
with a tuition line that has no further room to fall.

---

## What that risks

The model grows the FY27 tuition line of $700,142 at 8%. If that reduction does not hold —
if placements return, or if the FY27 figure was optimistic — FY28 looks materially worse:

| FY28 out-of-district tuition | FY28 gap | against the model |
|---|---:|---:|
| As the district budgeted it for FY27, $700,142 | $617,091 | — |
| Midway back, $1,000,000 | $940,938 | **+$323,847** |
| Back to the FY25 budget, $1,164,824 | $1,118,948 | **+$501,857** |
| Back to the FY26 budget, $1,291,293 | $1,255,534 | **+$638,443** |

None of these is a forecast. They are the cost of being wrong about one line, and the
range is wider than any other single assumption in the model.

---

## What this does not claim

**Not that special education is out of control.** On budget columns it is not growing
faster than everything else over two years — FY25 to FY27, special education all in rises
more slowly than the rest of the budget, precisely because of the tuition reduction.

**Not that anybody is hiding anything.** The tuition figure is published, the level-service
column is published, and the reduction is exactly what a district trying to control this
cost would attempt. It is the right move.

**Not that the paraprofessional increase is waste.** It is the cheaper half of the trade.
That is the point of making it.

The claim is narrower and only about the curve: **a one-time reduction is doing 2.25 points
of work in a rate that is supposed to describe a recurring problem**, and the underlying
recurring rate is 6.23%, not 3.98%.

---

## Two things learned after this was written

### The pay rise is not the story. There is no special education contract.

Special education staff are paid under the **same two agreements as everyone else** —
professional staff under the teachers' contract, aides under the paraprofessionals'. There
is no special education unit and no special education pay rate.

Weighting each part of the line by the contract that governs it:

| bargaining unit | share of the line | their contract |
|---|---:|---|
| Professional staff (LEA) | 52% | 3.5% FY27, plus steps |
| Paraprofessionals (AFSCME 503) | 33% | 2.0% FY28, plus steps |
| Transport (vendor) | 12% | vendor contract |
| Substitutes, supplies, legal | 3% | not bargained |

**Weighted, those contracts come to 4.28%** — and that is the rate this model
now uses, because the alternative turned out to be worse.

> **Correction, 28 August 2026.** This file previously reported **2.48%** as the
> contracts-only figure and used **5.89%**, what the whole line did, as the model's rate.
> Both were wrong, in opposite directions.
>
> The 2.48% priced **special education transport at zero**. That is 11.5% of the line, it
> is a vendor contract, and it moved +14.9% between the two budgets. A 0% that appears in
> no contract is an assumption wearing a contract's clothes. The bus line has no published
> escalator, so it has to be measured, and the measurement is sensitive: the blend is
> 3.72% at the district's own transport assumption of 10%, 4.28% at the most
> recent year, and 4.96% at the two-year rate. The middle one is used.
>
> The 5.89% was the larger error. Decompose the two years and the line is one decision
> moving once: paraprofessionals rose 39.4% in FY27, $530,038,
> which is **108% of the whole year's increase** — every other part of special
> education fell that year. Take the aides out and the rest of the line grew
> 1.53% a year across the two budgets, below the levy cap.
>
> So 5.89% was not a growth rate. It was a hiring decision averaged over two years and
> then compounded forever — which is the same error this file accuses the district's
> 3.98% of making, pointed the other way. Those aides were hired; their cost is already
> inside the amount the model starts from. Escalating it at 5.89% assumes they are hired
> again every year.
>
> What the new rate assumes, and it is not nothing: that the FY27 hiring was a step rather
> than the first year of a climb. Nothing in a budget column can test that.

**What that establishes:** the increase cannot be explained by the bargained pay rates
alone. Something other than the contract percentages accounts for the rest.

**What it does not establish:** what that something is. It could be more staff, staff at
higher classifications or further along the step scale, more hours, or a change in which
account a position is coded to. The budget shows dollars per line and never people, and
the district does not publish staff counts. We cannot say which.

What does follow is narrower and still useful: describing this line with a single growth
rate conflates the bargained part with the unexplained part, and it wrongly implies
special education staff receive larger increases than other staff. They do not — they are
in the same bargaining units as everyone else.

### And the number of students has not grown

The state publishes the count. Lunenburg, students with disabilities as of 1 October:

| FY | students | % of enrollment |
|---|---:|---:|
| 2019 | **277** | **16.7%** |
| 2020 | 255 | 15.4% |
| 2021 | 261 | 16.3% |
| 2022 | 227 *(low)* | 14.1% |
| 2023 | 234 | 14.9% |
| 2024 | 233 | 14.7% |
| 2025 | 248 | 15.8% |
| 2026 | **258** | **16.3%** |

All 8 years the state publishes, not a chosen three — an earlier version of this
file quoted FY2019, FY2022 and FY2026, and FY2022 is the low point of the series.

Over the whole series the count **fell 6.9%** — 277 to 258 — and the share of
enrollment is close to where it started, 16.7% against 16.3%. Measured from the
FY2022 low of 227 it is up 13.7%. Any three of these years can be picked to
show a rise or a fall, which is the reason for printing all of them.

That cuts against a simple "caseload is growing" reading. But the district's own FY27
presentation to the Finance Committee shows, for FY23 to FY26, full inclusion 156 to 174
and **sub-separate programs 30 to 43 — up 43%**. Sub-separate is the intensive end.

These two are not directly comparable. DESE counts every student with a disability;
the district's chart splits students by program type and its totals do not match DESE's
for the same years. We cannot reconcile them from what is published.

**A possible explanation, offered as a hypothesis and nothing more:** the number of
children could be roughly flat while more of them require intensive support, which would
let a staffing line rise faster than a headcount. Nothing here tests that. It would need
the program-type counts as numbers rather than a chart image, and staff assigned per
program, neither of which is published. It is written down so it can be checked, not
because it is established.

---

## What would settle it

1. **The FY28 out-of-district tuition line**, when the district publishes it. If it holds
   near $700,000 the trade worked. If it returns toward $1.2M, the FY27 rate was borrowed
   from a year that had not happened yet.
2. **Placement counts, not dollars.** Every figure here is money. The number of children
   placed out of district, year by year, would say whether the reduction is a change in
   need, a change in provision, or a change in budgeting.
3. **Whether the paraprofessional positions were filled.** A budget line is an intention.
4. **Special education enrollment by program type, as numbers rather than a chart image.**
   The count is flat over seven years while intensive placements appear to be up 43%. If
   the mix really is shifting, that is the mechanism behind the whole thing, and it is
   currently readable only off a picture.

---

## Sources

Budget figures from `xlsx/fy27-proposals.xlsx`, the FY27 budget workbook, columns
`fy25_budget`, `fy26_final`, `fy27_level_service` and `fy27_balanced`. Contract rates from
`contracts/pdf/paraprofessional-fy26-fy28.pdf` and `contracts/pdf/dese-teacher-contract.pdf`.
Student counts from `dese/selected-populations.csv`, pulled from the state's own report,
and from the FY27 presentation to the Finance Committee in the mirrored district budget
page — which carries them as a chart image, read by optical character recognition.
