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

The FY27 level-service budget rises **3.98%**. Hold one line where the year before had
it, and the same budget rises **6.23%**.

That line is out-of-district tuition — what the town pays other schools to educate children
it cannot serve here — budgeted **down 46%**, a fall of $591,151 in a single year.
Eleven budgets show it as low as $489,918 and as high as $1,291,293 with no direction to
it at all. So the fall is a **level** change rather than a slower rate of growth: it can
happen again, but it cannot keep happening, and the published 3.98% describes a year
whose arithmetic does not carry forward.

Underneath it, in-district special education escalates at **6.49%** — and the reason is
not pay. The paras are on a contract giving 2.0%; their budget line has grown **12.78% a
year across 10 budgets**, up in 8 of 9. The teachers are on a contract giving 3.5% and
theirs has grown 2.67%. **A contract sets what one person is paid. It says nothing
about how many people are employed**, and on this line that is where the movement is — in
both directions.

---

## What counts as special education here

**There is no account code for it.** The state's chart of accounts has no special
education total, and two of the groups the district reports carry both kinds of cost at
once: 2330 is paraprofessionals, general and special education together, and 3300 is
transportation, where the special education runs sit beside the yellow buses. Every figure
below therefore rests on a classification somebody made. This one is ours.

The rule has two parts:

1. **8 function groups are special education outright**, and every line inside them
   counts — except English Language Learner lines, which are excluded wherever they
   appear — 46 lines.
2. **Inside the mixed groups, a line counts when the district's own label says so** —
   8 lines.

Together, **54 lines totalling $5,466,201**, which is the amount every projection
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

- **2330 - Paraprofessionals General Education** — General education paras. The group next to the special education one, and the single boundary most likely to be crossed by accident in either direction. FY25 $121,233, FY26 $0, FY27 $0.
- **9300 / 9400 — out-of-district tuition** — Special education, but escalated on its own because it is set by placement rather than by payroll, and it behaves nothing like staffing. FY25 $1,164,824, FY26 $1,291,293, FY27 $700,142.

The general education paras are worth a second look. They are budgeted at nothing from
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
| Salaries | 12,801,345 | 13,503,716 | +702,371 | +5.5% | 67% |
| **Special education, in district** | **4,964,329** | **5,442,383** | **+478,054** | **+9.6%** | **46%** |
| Health insurance | 3,752,258 | 4,068,166 | +315,908 | +8.4% | 30% |
| Transportation | 965,500 | 1,053,360 | +87,860 | +9.1% | 8% |
| Utilities | 548,450 | 605,511 | +57,061 | +10.4% | 5% |
| Everything else | 1,964,301 | 1,960,011 | −4,290 | −0.2% | ~0% |
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
| As the district budgeted it for FY27, $700,142 | $680,870 | — |
| Midway back, $1,000,000 | $980,728 | **+$299,858** |
| Back to the FY25 budget, $1,164,824 | $1,145,552 | **+$464,682** |
| Back to the FY26 budget, $1,291,293 | $1,272,021 | **+$591,151** |

None of these is a forecast. They are the cost of being wrong about one line, and the
range is wider than any other single assumption in the model.

---

## Is the increase in paras a step, or a climb?

The whole in-district rate turns on this. If FY27's 39% increase in paraprofessionals was
a one-time step, its cost already sits in the $5,745,543 the model starts from and the
line should escalate at what the contracts give. If it is the latest year of a climb, it
should escalate at what the climb has been doing.

Two budget years cannot tell those apart. They look identical. Ten can.

| FY | paraprofessionals | change | stage |
|---|---:|---:|---|
| 2018 | $634,513 | — | settled |
| 2019 | $657,492 | +3.6% | settled |
| 2020 | $871,903 | +32.6% | settled |
| 2021 | $920,345 | +5.6% | settled |
| 2022 | $946,233 | +2.8% | settled |
| 2023 | $1,014,759 | +7.2% | settled |
| 2024 | $1,170,941 | +15.4% | proposed |
| 2025 | $1,366,893 | +16.7% | workbook |
| 2026 | $1,342,373 | -1.8% | workbook |
| 2027 | $1,872,411 | +39.5% | workbook |

| | |
|---|---:|
| FY18 to FY27 | $634,513 → $1,872,411 (**2.95×**) |
| Compound rate | **+12.78% a year** |
| Straight-line fit | **R² = 0.89** |
| Years up / down | **8 / 1** |
| Compound rate by start year | +11.5% to +17.0% |

**It is a climb.** 8 of 9 years up, an R² of 0.89, and a compound rate that barely moves
wherever you start it — the opposite of out-of-district tuition, whose rate swings from
-45.8% to +11.8% on the same test with an R² of 0.10. The FY27 increase is the
steepest year of a trend running since FY18, not a departure from one.

**And it is the paras, not the rest of the line, that make special education a driver.**
In FY27 the paraprofessional increase was **111% of the whole year's rise** in in-district
special education — every other part of the line fell. Take the paras out and the
remainder grew **1.14% a year** across the two most recent budgets, below the levy cap. One
part of this line is climbing and the rest is close to flat, which is precisely why a
single blended rate taken from the settlements gets it wrong.

**That is headcount, and no settlement reaches it.** The paras' contract gives 2.0%. Their
budget line has grown at 12.8%. Pricing them at their contract assumes the district stops
adding them, which it has not done in 8 of the last 9 budgets.

### What the district actually gets in grants, and what it lost

Rule 11 says the budget shows one funding stream and the others are invisible. That is true
of the budget documents. It is not true of the presentations: three of them carry grant
pages naming every entitlement and competitive grant with its amount.

**Where every figure below comes from.** Principally the **FY25 Superintendent's Budget
Update**, whose *Grants History* section gives one page per year:

| | |
|---|---|
| **The file, at the district** | https://drive.google.com/file/d/1yJNhIyBLVT8mu4GeJuQSjniKCPA41Oyq/view — **asks for a Google sign-in as of 29 August 2026** |
| **The district's name for it** | *FY25 Superintendent's Budget Update* — ask for it by this name if the link will not open |
| **Our copy, downloadable** | https://lunenburgbudgetproject.org/docs/district-budget-page/docs/fy25-superintendent-39-s-budget-update.pdf |
| **The extract we read** | https://lunenburgbudgetproject.org/data/grants-history.csv |
| Pages | 31–36 — ESSER on 31, then one page per year |
| sha256 | `9169e2700def0c1a2b6bebbc55d4e7f737ea5c3a7354657f4d804c017af5dc7c` |
| Where it is listed | the district's school budget information page, under Superintendent of Schools — an index, and indexes get reorganised, which is why the file link is above it |

Two other decks add years and are recorded per row: the **FY24** and **FY23**
superintendent's recommended budget presentations. Every row in
[`/data/grants-history.csv`](https://lunenburgbudgetproject.org/data/grants-history.csv)
names its document, its page, the district's link, our link and the hash, so any single
figure can be checked without taking the table on trust.

**Because the district's own copy now needs a sign-in, ours is the one a resident can
open.** The hash is how anybody who still has access confirms they are the same file.

| FY | federal | state | ordinary grants | ESSER |
|---|---:|---:|---:|---:|
| FY20 | $797,604 | $82,583 | **$880,187** | — |
| FY21 | $814,232 | $89,463 | **$903,695** | — |
| FY22 | $971,514 | $598,671 | **$1,570,185** | — |
| FY23 | $991,690 | $453,237 | **$1,444,927** | $588,834 |
| FY24 | $706,238 | $430,170 | **$1,136,408** | — |
| FY21–24 | | | | **$2,137,941** |

**Ordinary grant income did not collapse.** Special education grants specifically are
steadier still:

| FY | special education grants |
|---|---:|
| FY20 | $502,272 |
| FY21 | $520,296 |
| FY22 | $520,845 |
| FY23 | $520,223 |
| FY24 | $445,912 |

**What was lost was ESSER, and only ESSER.** ESSER 1 $198,073, ESSER 2 $588,834, ESSER 3
$1,351,034 — **$2,137,941 across FY21 to FY24** (p31), on top of everything above, then
nothing. Roughly half a million a year.

That matches what the town was told. A resident told the School Committee on 3 September
2025 that "the cuts that were made were ESSER cuts. So we didn't cut beyond ESSER."

### Where the district's own decks disagree

Six grants are stated at two different amounts by two of its presentations. All are small
and all look like a grant reported as awarded in one year's deck and as finally received in
a later one. They are kept and marked rather than averaged; the FY25 deck is preferred
because its Grants History pages are a deliberate retrospective.

| FY | grant | the two statements |
|---|---|---|
| FY22 | Special Education, 240 Grant | fy23-superintendent-recommended-budget-presentation p17: $397,343; fy25-superintendent-39-s-budget-update p34: $399,152 |
| FY22 | School Health Grant | fy25-superintendent-39-s-budget-update p34: $100,000; fy25-superintendent-39-s-budget-update p34: $14,000 |
| FY23 | Special Education, 240 Grant | fy24-superintendent-39-s-recommended-budget-presentation p16: $402,967; fy25-superintendent-39-s-budget-update p33: $404,772 |
| FY23 | Special Education, Early Childhood, 262 Gran | fy24-superintendent-39-s-recommended-budget-presentation p16: $13,033; fy25-superintendent-39-s-budget-update p33: $13,133 |
| FY23 | School Health Grant | fy24-superintendent-39-s-recommended-budget-presentation p16: $30,000; fy25-superintendent-39-s-budget-update p33: $100,000; fy25-superintendent-39-s- |
| FY23 | Family & Community Grant | fy24-superintendent-39-s-recommended-budget-presentation p16: $47,500; fy25-superintendent-39-s-budget-update p33: $45,700 |

**One caveat on coverage.** The FY25 deck supplies 67 of the 79 rows and is the only
consistent year-by-year series. FY22 and FY23 look higher than their neighbours partly
because the other two decks list grants for those years that the FY25 retrospective does
not. Compare years within the FY25 series before comparing across the whole table.

**And a retraction.** An earlier version of this section said the town's share of these
staff had gone from 52% to 84% — a handover from grants to the general fund. That was an
artifact of measuring early years by matching line names and later years by function code.
Measured consistently the share is **78% in FY17 and 78% in FY25**, dipping to 65% in FY24
when ESSER was at its peak. There is no handover. It is recorded because the wrong version
was the more interesting one, which is when a number needs checking hardest.

### The state publishes the headcount after all, and it changes the reading

Everything above assumes a budget line is the only thing available, because the district's
budget documents show dollars and never people. **That was wrong.** Massachusetts DESE
publishes paraprofessional FTE for every district, every year, on the state open-data
portal, and it answers a plain HTTP request.

| | |
|---|---|
| **The file, at the state** | https://educationtocareer.data.mass.gov/resource/er3w-dyti.csv?DIST_CODE=01620000 — open, no sign-in |
| **The state's name for it** | *District Expenditures by Spending Category*, dataset `er3w-dyti` |
| **Our copy, downloadable** | https://lunenburgbudgetproject.org/docs/dese/district-spending-categories.csv |
| Rebuild | `scripts/fetch_dese.py`; Lunenburg is district code 01620000 |

| FY | paraprofessionals, FTE |
|---|---:|
| 2017 | 59.5 |
| 2018 | 51.0 |
| 2019 | 53.0 |
| 2020 | 57.0 |
| 2021 | 59.5 |
| 2022 | 55.5 |
| 2023 | 59.0 |
| 2024 | 66.0 |
| 2025 | 67.0 |

Set that beside the budget. Taking **all** paraprofessional lines against **all**
paraprofessional FTE, so the two measure the same population:

| | FY17 | FY25 | a year |
|---|---:|---:|---:|
| Budgeted | $707,139 | $1,498,126 | **+9.84%** |
| Employed | 59.5 | 67.0 | **+1.50%** |
| Budgeted per para | $11,885 | $22,360 | **+8.22%** |

Their contract gives **2.0%**.

**What this establishes.** The para budget has grown roughly six times faster than the
number of paras. Most of the increase is not more people, and it is not bargained pay
either — dollars per counted para rose 8.22% a year against a 2.0% agreement.

**What it does not establish.** Why. The obvious explanation was that the town used to pay
only part of these costs and now pays more of them — and **that was checked and it is not
what happened.** The town's share of the function group these staff sit in is 78% in FY17
and 78% in FY25 (see above). There is no handover.

What is left fits paras moving from part-time to full-time hours, paras at higher
classifications or further up the step scale, or DESE counting heads on a different basis
from the one the budget pays against. Nothing published separates them, and none of them
is established here.

The same pattern holds on **actual spending**, not just budgets, which rules out a
budgeting artifact: FY18 to FY25, para spending grew 9.07% a year — 3.98% more paras
multiplied by 4.90% more per para — against a contract giving 2%.

**What it means for the rate, and this is unresolved.** The escalator projects the budget
line at 12.78%. If that growth is a cost migrating onto the general fund, it must
eventually stop — a cost can only move onto the town's books once — and the line would
then grow at headcount plus contract, somewhere near 3.5% to 6%. That is the same shape as
the out-of-district tuition finding: a level shift being read as a rate.

It is left at 12.78% because nothing establishes when or whether the migration ends,
and because the figure is honestly described: **it is what the town has appropriated.**
But a reader should know the alternative and what it is worth, so here it is:

| para component | blended rate | FY28 gap |
|---|---:|---:|
| What the budget line did — **used** | 12.78% | $680,870 |
| Headcount growth plus their contract | 5.98% | $552,922 |
| Their contract alone | 2.00% | $477,994 |

**What would settle it** is unchanged and now more valuable: DESE's End of Year Financial
Report separates spending by fund. See `notes/DATA-WANTED.md`.

### The one thing that could undermine this rate, and we cannot see it

The para series is a **general-fund budget** line. It is not a record of what the paras
cost or of how many there are — it is what the town appropriated for them. If some of
those positions were paid for from somewhere else, the line does not mean what it appears
to.

**A hypothesis, and it is only that.** Paraprofessional positions may be budgeted in the
general fund while being paid, in whole or part, by state or federal grants. When such a
grant ends the same people appear as a general-fund increase, and a budget series reads
that as growth when nothing about the staffing changed. The district's budget documents do
not show grant funding at all, so the two cases look identical from here.

If that is happening, some part of the 12.78% measured across 10 budgets is money moving
between funding sources rather than a district employing more people, and the rate is too
high.

**What the timing does and does not support.** Federal pandemic money ran out during FY25.
The para line rose 16.7% in FY25 and then *fell* 1.8% in FY26, and its steepest year is
FY27 — a year after the cliff. So the simplest version of this, a single federal
grant ending and its positions landing on the general fund, does not fit the shape. State
grants have their own timing and we cannot see any of them, so this is weak evidence and
not a refutation.

**What would settle it.** DESE's End of Year Financial Report separates district spending
by funding source, which is exactly the mapping the district's own budget documents omit.
The district's grant budgets would do it too. Neither is in this archive; both are
recorded in `notes/DATA-WANTED.md`.

**Until then, the rate stands as what it is: what the town has appropriated for this line,
measured over ten of its own budgets.** That is the right quantity for a model that
projects appropriations, which is what this one does. It is not a claim about how many
paras the district employs, and this page should never be read as making one.

### Special education teachers, tested the same way

The largest part of the line — 54% of it — and the last one still priced from a
contract rather than measured.

| FY | teachers | change | stage |
|---|---:|---:|---|
| 2020 | $1,617,268 | — | settled |
| 2021 | $1,723,153 | +6.5% | settled |
| 2022 | $1,795,020 | +4.2% | settled |
| 2023 | $1,890,708 | +5.3% | settled |
| 2024 | $1,828,571 | -3.3% | proposed |
| 2025 | $1,979,158 | +8.2% | workbook |
| 2026 | $1,978,848 | -0.0% | workbook |
| 2027 | $1,945,512 | -1.7% | workbook |

| | |
|---|---:|
| FY20 to FY27 | $1,617,268 → $1,945,512 |
| Compound rate | **+2.67% a year** |
| Straight-line fit | R² = 0.84 |
| Their contract gives | 3.5% |

**Below contract.** These staff get their bargained increase like everyone else, so a line
growing more slowly than the agreement means there are fewer of them each year. Escalating
this component at 3.5% assumed headcount held, and overstated it.

That is the same lesson as the paras, pointing the other way. **A contract sets what one
person is paid. It says nothing about how many people are employed** — and on this line
that is where the movement is, in both directions.

### Special education transportation, tested the same way

| | |
|---|---:|
| FY19 to FY27 | $417,585 → $649,953 |
| Compound rate | +5.69% a year |
| Straight-line fit | R² = 0.33 |
| Years up / down | 6 / 2 |

A far weaker fit — it fell for two years and then climbed for four. 5.69% is used because it
is the least bad figure available for a vendor contract that publishes no escalator, not
because the line is well behaved, and it is 12% of the total.

### Two things this does not cover, said plainly

**$920,007 of the line — 16.9% of it — is not measured.** The rate for professional
staff was measured on the teacher lines, $1,945,512 of a $2,865,519 component. The rest is
therapeutic services, psychologists, clerical and supplies, and it rides on the teachers'
rate. Extracting the speech and therapy lines was attempted and yielded three settled
years, which is not enough to test a trend on. It is the next thing worth doing if more of
the district's documents are mirrored.

**English Language Learner costs were being counted as special education, and are not any
more.** The district files "District Wide Specials (ELL)" inside function 2320, which is
otherwise therapeutic services, and ELL supplies inside 2110. A rule that takes those
groups at their word counted them — ours did, until this pass. ELL is a different
entitlement serving different children under a different part of the law. Removing it
takes the in-district line down by $279,342, and it is named in the excluded
list on the page. This is the cost of the classification being ours: the state's account
codes cannot draw this line, so we draw it, and everywhere we draw it differently from the
district has to be visible.

### What this forces

The line was escalated at **2.57%** — the two pay settlements weighted by share — on the
argument that FY27's increase in paras was a step already sitting in the base. **The
argument was sound and its premise was false.** With two budget years there is no way to
tell a step from a climb; with ten there is, and it is a climb.

The rate is now **6.49%**, and the projected gap went up rather than down. That is what
the evidence says, and the direction it moves the answer is not a reason to prefer the
other one.

Published at `/data/sped-para-history.csv` and `/data/sped-transport-history.csv`;
`scripts/extract_budget_history.py` regenerates both from the archive.

---

## What out-of-district tuition has actually done

The model escalated this line at **8% a year** and nothing supported that number — its
citation said only "our estimate", and the back-test flagged it as the worst-calibrated
assumption in the model. Three budget years is not enough to do better. The archive's
mirror of the district's budget page reaches back to FY17, and those documents carry lines
9300 and 9400.

**The extraction, and the trap in it.** Every one of those documents prints five or six
columns and most are actual spending, so nothing here is taken by position: each document
states its own columns and the script reads that header. Worse, and only visible once you
look, **a fiscal year does not have one budget figure for this line**. Collaborative
tuitions for FY25 were proposed at $369,415 in April 2024 and approved at $460,952 that
June; FY26 was approved at $782,867 in March 2025 and reported as a final budget of
$302,663 a year later. So the budget *stage* is held constant too. Three of the years below
reproduce the FY27 workbook exactly, which is what makes the other eight worth trusting.

| FY | budgeted | change | stage |
|---|---:|---:|---|
| 2017 | $655,534 | — | proposed |
| 2018 | $760,270 | +16.0% | settled |
| 2019 | $754,480 | -0.8% | settled |
| 2020 | $865,746 | +14.7% | settled |
| 2021 | $719,269 | -16.9% | settled |
| 2022 | $818,716 | +13.8% | settled |
| 2023 | $489,918 | -40.2% | settled |
| 2024 | $501,239 | +2.3% | proposed |
| 2025 | $1,164,824 | +132.4% | proposed |
| 2026 | $1,291,293 | +10.9% | settled |
| 2027 | $700,142 | -45.8% | proposed |

### There is no trend. There is a range.

| | |
|---|---:|
| Budgets | 11, FY17 to FY27 |
| Low | $489,918 (FY23) |
| High | $1,291,293 (FY26) |
| Ratio | **2.64×** |
| Average | $792,857 |
| Years up / down | 6 / 4 |
| Straight-line fit | **R² = 0.10** |

The obvious repair for an unsupported 8% is to measure the rate instead. The measurement
will not hold still:

| compound rate to FY27 | |
|---|---:|
| from FY17 | +0.66% |
| from FY18 | -0.91% |
| from FY19 | -0.93% |
| from FY20 | -2.99% |
| from FY21 | -0.45% |
| from FY22 | -3.08% |
| from FY23 | +9.34% |
| from FY24 | +11.78% |
| from FY25 | -22.47% |
| from FY26 | -45.78% |

**-45.8% to +11.8% on the same line, with the same endpoint, depending only on
which year you start counting.** A figure that moves that far on an arbitrary choice
measures nothing. Publishing +0.66% because FY17 happens to be the first year the archive
reaches would be the same error as pricing the paras at their 2.0% contract:
a number with a citation and no meaning for the line it is attached to.

**So the line is held flat**, and the risk is published as a range of priced scenarios
instead. That is the honest shape of what is known: nobody can say which direction this
line moves next, and the useful thing to publish is what it costs to be wrong either way.

### A correction this series forces

An earlier version of this file said the FY27 fall was a level change that **could not
repeat** — "there is no second 46%". That does not survive eleven budgets. This line fell
**45.8% in FY27** and then rose **132% in FY25**. And
$700,142 is **11.7% below** the 11-budget average of $792,857 — an ordinary
year for this line, not a floor.

What survives is the narrower claim, which is the one that matters to the curve: the fall
is a **level** change, so the published 3.98% does not describe a recurring rate.
What does not survive is the suggestion that the line has nowhere left to go.

The series is published at `/data/ood-tuition-history.csv`, and
`scripts/extract_tuition_history.py` regenerates it from the archive.

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
professional staff under the teachers' contract, paras under the paraprofessionals'. There
is no special education unit and no special education pay rate.

Weighting each part of the line by the contract that governs it:

| bargaining unit | share of the line | their contract |
|---|---:|---|
| Professional staff (LEA) | 52% | 3.5% FY27, plus steps |
| Paraprofessionals (AFSCME 503) | 33% | 2.0% FY28, plus steps |
| Transport (vendor) | 12% | vendor contract |
| Substitutes, supplies, legal | 3% | not bargained |

**Weighted, those two settlements come to 2.57%** — and the line has risen faster than that
in every budget we hold.

That gap is the whole question, and it is answered in *Is the increase in paras a step, or
a climb?* above: the paras' line has grown 12.8% a year across 10 budgets while their
contract gives 2.0%. So the model escalates
every part of it at what its own budgets show it doing, measured across eight to ten
years of them, which comes to **6.49%**.

> **Correction, 28 August 2026.** This file has carried five different rates for this line
> in one day. The sequence is kept because each step was a real error and the last one is
> only trustworthy to the extent the others are visible.
>
> **2.48%**, described as "contracts alone", priced special education transport at zero.
> That is 12% of the line and a vendor contract. A 0% that appears in no contract is
> an assumption wearing a contract's clothes.
>
> **5.77%**, what the whole line did over two budgets, was replaced because it looked like
> one hiring decision averaged and compounded.
>
> **2.57%**, the two settlements weighted by share, assumed FY27's increase in paras was
> a step already sitting in the base. Ten budgets say it is a climb.
>
> **6.80%** measured the paras and the buses but still took the largest component — the
> teachers, 54% of the line — from their contract, on three years showing it flat.
>
> **6.49%** measures all three. The teachers turn out to have grown 2.67% against a
> 3.5% agreement, so the contract rate had been overstating them.
>
> The lesson is not about any of the five numbers. It is that a contract sets what one
> person is paid and says nothing about how many people are employed, and that on this
> line the second thing moves more than the first — in both directions. And
> that a rate measured over two years cannot distinguish a step from a trend, and that
> "use the contract rate" is only conservative for a line a contract actually governs.

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
