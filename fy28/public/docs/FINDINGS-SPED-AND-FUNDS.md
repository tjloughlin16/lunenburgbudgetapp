# Special education, and the money outside the operating budget

> ## Correction, 28 August 2026 — read this first
>
> Two growth figures below were derived by comparing **actual spending** in FY23 to a
> **budget** in FY26. Those are different quantities — budgets for some lines run about 7%
> above what is actually spent — so part of what is described here as growth is really the
> step from spent to budgeted.
>
> On a like-for-like basis, comparing budgets to budgets (FY25 adopted to FY27 level
> service), the picture is materially different:
>
> | claim below | as written | budget to budget |
> |---|---:|---:|
> | Special education growth | 13.0%/yr | **1.9%/yr** |
> | Everything else | 3.4%/yr | **2.6%/yr** |
> | Special education share of all growth | 51% | **19%** |
>
> **What still holds:** special education is about 24.5% of the budget on every basis
> tested; out-of-district tuition is budgeted down 46% for FY27; the circuit breaker
> account and its balances come from the town's own balance sheet and are unaffected; and
> the paraprofessional-for-tuition swap is budget-to-budget throughout.
>
> **What does not:** any statement here that special education is growing far faster than
> the rest of the budget. On appropriations it is not.
>
> The underlying question — whether actual spending has been rising faster than the
> appropriations that fund it — is real and is being worked separately. It is not settled,
> and nothing here should be read as though it were.

Research notes, 27 Aug 2026. Companion to `FINDINGS.md`, which covers the FY27
appropriation and the override. This file covers two things that document does not:
**special education as a cost driver**, and **the school and town funds that sit
outside the operating appropriation entirely**.

Everything here is reproducible from files under `sources/`. Where a figure is an
inference rather than a published number, it says so.

---

## Part 1 — Special education

### 1.1 It is a quarter of the budget and it was half of the growth

Totalling every SPED-coded line in `data/lps-budget-lines.csv` — functions 2110,
2310 (SPED teachers), 2320 (therapeutic), 2325 (SPED subs), 2330 (SPED paras), 2800
(psych), 3300 (SPED transport), 9300 (private tuitions), 9400 (collaborative tuitions):

| | FY23 actual | FY26 final | FY27 balanced |
|---|---:|---:|---:|
| Special education | $4,469,881 | $6,449,500 | $6,445,685 |
| Everything else | $17,956,929 | $19,837,976 | $20,126,605 |
| **SPED share of budget** | **19.9%** | **24.5%** | **24.3%** |

FY23 → FY26 growth: SPED **13.0%/yr**, everything else **3.4%/yr**. In dollars, SPED
added $1,979,619 of the $3,860,666 total increase — **51.3% of all budget growth was
special education**, while enrollment fell.

DESE confirms the shape independently (`xlsx/dese-all-districts.xlsx`). FY18 → FY24,
Lunenburg's **Other Teaching Services** — where DESE books paras, therapists, tutors —
grew **+51%** against **+32%** for Teachers, on enrollment **−2.5%**.

### 1.2 The model in the app escalates the wrong 2.6%

`fy28/src/data/model.json` carries `expenseBase.sped_tuition = 700,142` at 8%. That is
$56,011 of the $1,313,594 of year-one escalation the model generates — **4.3%**. The
other ~$5.75M of SPED is folded into `salaries` at 4% and `transport` at 6%.

Observed rates say otherwise. In-district SPED (SPED total less tuition less SPED
transport) ran $3,844,889 → $4,592,473 FY23→FY26 = **6.1%/yr**. SPED transport ran
$320,244 → $649,953 = **+103% in four years**; the district itself budgeted it at +10%
for FY27 while the model blends all transport at 6%.

The concept: the six buckets are modelled as **cash-limited** — you set an amount and
that is what gets spent. SPED is **demand-led**: the entitlement sets the cost and the
appropriation only records it. A demand-led line inside a cash-limited model always
understates, because the model cannot represent caseload, which is the thing that
actually sets the number.

Escalating SPED at its own observed rates adds roughly **$130k–$140k/yr** of gap on top
of the $552,621 headline — about 25% more hole, compounding.

### 1.3 The out-of-district cliff

| | FY23 | FY24 | FY25 | FY26 budget | FY27 budget |
|---|---:|---:|---:|---:|---:|
| Private (9300) | $118,194 | $397,529 | $703,341 | $988,630 | $536,400 |
| Collaborative (9400) | $186,554 | $190,979 | $28,957 | $302,663 | $163,742 |
| **Total** | **$304,748** | **$588,508** | **$732,298** | **$1,291,293** | **$700,142** |

Out-of-district tuition **quadrupled in three years**, then FY27 budgets it 46% below FY26.

FY26 was itself short. As of the Feb/Mar 2026 workbook, actuals-to-date plus
encumbrances were **$1,530,182** against a $1,291,293 budget — collaborative tuitions
alone had spent $607,587 against a $302,663 line, with $171,965 more encumbered.

So FY27 budgets $700,142 against a committed FY26 run-rate of ~$1.53M. **An ~$830,000
exposure in one line** — more than the entire annual structural gap — before any
circuit breaker offset (see §2.1, which changes this materially).

The district knew. School Committee, 4 Feb 2026: *"we currently have students on our
radar that may require out of district placement and we have also had students move
into the district that require out of district placements."*
(`minutes/text/school-committee/2026-02-04-minutes-7634.txt`)

This line also carries a risk shape nothing else in the budget has: **tail risk**. One
new residential placement is $150k–$400k arriving mid-year with no vote and no warning.

### 1.4 The make-or-buy move — the one real structural bend

FY26 → FY27 level service, two entries that almost exactly offset:

- Out-of-district tuition **−$591,151**
- SPED paraprofessionals **+$530,038** (+39% in one year — the largest single-year
  increase of any line group in the FY27 budget, larger than the school-side health
  insurance increase of ~$293k)

Tri-Board minutes, 27 Jan 2026, state the strategy outright: *"The School Committee had
voted mid-year to add paraprofessionals to respond to individual students with acute
needs, partly to avoid far more expensive out-of-district placements."*
(`minutes/text/finance-committee/2026-01-27-minutes-7619.txt`)

This is a **make-or-buy decision** — produce the capability in-house rather than
purchase it — and on the model's own logic it is correct: it converts a demand-led line
inflating at 8%+ into headcount inflating at contract rates of ~4%. It is the only
structural curve-bend anyone in Lunenburg has actually executed, and the app does not
mention it.

It is fragile in one specific way: it only works if placements genuinely come back
in-district and stay. If a parent rejects the in-district program at a Team meeting, the
district pays the tuition **and** keeps the paras. Downside-only. Worth modelling as a
scenario.

### 1.5 Compliance exposure is already on the public record

Tri-Board, 27 Jan 2026: a Turkey Hill teacher testified that after the FY26 cuts her
role was split between SPED and MTSS interventionist, and that **"seven of my IEP
students with significant pull-out service needs were being seen by a paraprofessional
rather than a certified special education teacher."**

A para delivering specially designed instruction that an IEP assigns to a certified SPED
teacher is a compliance finding waiting for a parent to file, and the remedy is
compensatory services — retrospective, unbudgeted, uncapped.

The honest framing: SPED cuts do not reduce spending, they **defer it into liability**.
The cost reappears later, larger, and outside the appropriation.

### 1.6 The peer comparison omits the fastest-growing SPED cost

`xlsx/dese-all-districts.xlsx` is **Total In-District Expenditures**. DESE's in-district
measure excludes out-of-district tuition — a separate reporting category. So the app's
conclusion #3, comparing Lunenburg's growth to its neighbours, is computed on a basis
that omits the line that quadrupled.

The claim survives — in-district Lunenburg grew +21% FY18→FY24 against Groton-Dunstable
+34%, Littleton +32%, Leominster +42%, and is bottom-of-pack alongside Wachusett's +20%.
But it is an unstated scope limitation on a load-bearing conclusion.

---

## Part 2 — The money outside the operating budget

Sources: `xlsx/school-funds-fy26.xlsx` (period 13, i.e. FY26 year-end) and
`munis-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx` (as of 3/31/2026). The two cross-validate:
School Choice opens at $246,902.71 in both, Athletics at $110,247.89, Gift at $89,822.59.

Column mapping in the special revenue workbook, confirmed against its own totals rows:
`col8 = beginning balance + col10 = revenue + col13 = expenditure = col15 = ending balance`.
Balance-sheet sign convention: fund balances are shown negative (credit); figures below
are flipped to positive-as-money-available.

### 2.1 Special Ed Circuit Breaker — Fund 2640

**This is the single most important finding in this document.**

| | |
|---|---:|
| Balance 7/1/2025 | $293,335 |
| FY26 receipts through 3/31/26 | +$325,970 |
| FY26 spent through 3/31/26 | −$4,005 |
| **Balance 3/31/2026** | **$615,301** |

The district holds **$615,301** in a restricted special-education account — **81% of the
entire $761,000 FY27 net budget reduction** — and had drawn **$4,005** from it in nine
months. Six-tenths of one percent, in a year the general fund carried $1.29M of
out-of-district tuition.

**Caveat, and it is a real one.** Many districts book the circuit breaker offset as a
single year-end journal entry, so a low Q3 draw may not mean a low annual draw. The FY26
year-end figure would settle it; this file stops at March. **Get it before quoting the
$615,301 as idle money.**

**Effective reimbursement rate.** FY26 receipts of $325,970 reimburse FY25 claims. FY25
out-of-district tuition was $732,298 — a **~45% effective offset**, or ~28% if the claim
also covered the $434,922 of FY25 SPED transport (eligible at 75% since FY25; see
`minutes/text/school-committee/2025-05-07-minutes-7207.txt`, which records the rate
rising from 44%). Applied forward to FY26's $1.29M–$1.53M of out-of-district cost,
roughly **$575k–$680k of circuit breaker revenue should arrive during FY27**.

Every out-of-district figure in the app is **gross** of this. The model has no offset.

**The open question.** FY26 gross out-of-district was $1,291,293. Net of a ~45% offset
that is ~$710k. The FY27 budget line is **$700,142**. Close enough to be worth asking
the Business Manager directly: *is the FY27 tuition line gross, or already net of
expected circuit breaker?* If it is net, the make-or-buy explanation in §1.4 is wrong
and the real story is an accounting change.

Peer datapoint: Groton-Dunstable's FY27 budget book states *"The District is planning to
offset $2M of expenses with Circuit Breaker Funding ($500K higher than FY26)."*
(`peers/groton-dunstable-fy27-budget-book.txt`)

### 2.2 Athletics revolving fund — the app understates fee revenue by 45%

FY26 year-end, under the **old** $250 / $140 / $85 schedule with a $475 family cap:

| | Gross | Refunds | Net |
|---|---:|---:|---:|
| High school user fees | $167,511 | $4,641 | $162,871 |
| Middle school user fees | $27,098 | $1,024 | $26,074 |
| **Total revenue** | **$194,609** | **$5,665** | **$188,944** |

Expenditures $146,911 — salaries (4 revolving-fund staff) $30,514; purchase of service
(officials, uniforms, **transportation**) $113,602; general supplies $2,795.
Beginning balance $110,248 → **ending balance $152,281**.

Three consequences:

1. **The app's base is wrong.** `model.json` carries `estimatedFy26Revenue: 130129`;
   actual was **$188,944**, 45% higher. Worse, `estimatedAthleticRevenue: 187451` is the
   app's estimate of revenue *after* the increase to $400 — but the old schedule already
   collected more than that. `feeIncreaseValue: 77849` and the $960 self-funding fee are
   both calibrated off a base that is too low.
2. **Athletic transportation was already partly running through this fund.** The
   $113,602 purchase-of-service category names transportation explicitly. "We cut all
   athletic transportation, $127,550" is therefore not the clean statement it appears
   to be.
3. **The fund gained $42,033 in FY26** and ended holding $152,281 — in the same year the
   town said it could not afford $127,550 of athletic buses. Revolving-fund spending is
   capped by annual Town Meeting authorisation, so this is not automatically available,
   but it is a fair question and nobody appears to have asked it.

Also: MS fees brought in $26,074 in FY26, and FY27 eliminated middle school sports. That
revenue goes with it.

This answers two of the three questions in `model.json → feeAccounting.unresolved`.

### 2.3 School choice revolving fund

FY26 year-end: bus fee $52,717 net + state/local choice aid $63,314 = **$116,031
revenue**; expenditures **$36,653**; beginning $246,903 → **ending $326,281**.

Only 32% of what came in was spent. The fund grew $79,378 in a year the district cut
$761,000. School choice funds are restricted to school purposes but are broadly usable
within that.

### 2.4 Everything else on the school side

| Fund | Balance | As of |
|---|---:|---|
| Special Ed Circuit Breaker | $615,301 | 3/31/26 |
| School Choice revolving | $326,281 | 6/30/26 |
| School Lunch revolving | $287,771 | 3/31/26 |
| Athletics revolving | $152,281 | 6/30/26 |
| After School Activities | $148,578 | 3/31/26 |
| School Gift Fund | $101,418 | 6/30/26 |
| School Facilities Use | $71,559 | 3/31/26 |
| Adult Education revolving | $12,744 | 3/31/26 |
| Technology for School Children | $10,000 | 3/31/26 |
| Insurance Recoveries — School | $1,299 | 3/31/26 |
| Summer School revolving | $340 | 3/31/26 |
| **Total** | **~$1,727,572** | |

**This is not $1.73M of free money** and must never be presented as such. Lunch must stay
in food service under federal rules; gifts are donor-restricted; circuit breaker is
SPED-only. But it is $1.73M that never enters the budget conversation, against a
$761,000 cut — and the two largest pots are circuit breaker (restricted to the exact
cost driver eating the budget) and school choice (broadly usable).

This is the mirror image of the app's conclusion #13. That one says one-time money is
funding recurring costs. This says **recurring restricted money is not being spent at all**.

### 2.5 Town stabilization and trust funds

From `munis-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx`, as of 3/31/2026:

| Stabilization fund | Balance |
|---|---:|
| General stabilization | $3,244,478 |
| Vehicle & equipment | $2,653,764 |
| OPEB | $1,929,754 |
| Conservation trust | $1,013,577 |
| Opioid settlement | $288,152 |
| Playground | $255,604 |
| Sewer capital stabilization | $216,710 |
| Health insurance stabilization | $11,368 |
| Sewer stabilization | $10,755 |
| **Total stabilization** | **$9,624,161** |
| Trust funds (separate) | $1,161,151 |

Stabilization grew **$562,740** in nine months of FY26.

Read this carefully and fairly. Stabilization requires a two-thirds Town Meeting vote,
and spending reserves on recurring costs is the same error the app already flags at
$453,722 — just larger. Strong reserves are also what protects the bond rating.

The defensible observation is narrower: general stabilization ($3.24M) plus certified
free cash ($3.354M, from `FINDINGS.md`) is **~$6.6M against a $49.96M omnibus — about
13%**, at the top of the 5–15% range DLS considers healthy. A town at the top of that
range cutting $761,000 is making a **policy choice**, not bowing to arithmetic. That is
a fair thing to say. "They have $9.6M and won't spend it" is not.

One genuine oddity: the **health insurance stabilization fund holds $11,368** against a
$4M health insurance line growing 9%/yr. The fund exists in name only.

---

## Part 3 — Why none of this surfaced during the budget debate

`town-budget/docs/fincom-memo-fy26-q3.docx`, from the Finance Director, is dated **11 August
2026** and reports the quarter ending **31 March 2026** — a four-and-a-half month lag,
and explicitly the first of a resumed series (*"In moving forward, I hope to present
these reports quarterly to the Finance Committee"*).

Her own account of why, quoted from the memo: the Town Accountant of 38 years retired at
the end of FY24; the successor gave notice after 18 months; the payroll person retired
and went to the school; the town lost the Assistant Town Accountant. The Assistant Town
Accountant was hired December 2025, the Payroll Benefits Coordinator March 2026, and the
Finance Director herself **at the end of January 2026**.

So the FY27 budget was built in February–March 2026 and the override went to ballot on
**16 May 2026** without current quarterly financial reporting, during a near-total
turnover of the finance office.

This is not an accusation and should never be written as one. It is the stated record,
and it is the most plausible explanation for how $615,301 can sit in a special-education
account while the district cuts $761,000 and eliminates middle school sports.

### Also in the Q3 report: revenue the FY27 debate did not count

- **Local receipts came in at 116% of budget** — $3,961,722 against $3,415,624, an
  overage of **$546,098**, attributed to "Investment Income and MVE exceeding budget."
- **$318,000 of Smart Growth funds** had not yet been received as of 3/31/26.
- Property taxes 75% collected, state aid 73% — both on pace.
- General fund expenditures $36,845,129 against a revised $51,531,201 budget (71.5%),
  including ~$2.6M of encumbrances.
- School Department: revised budget $26,323,868; expended $15,736,641 plus $1,668,043
  encumbered = 66.1%; $8,919,184 remaining.

---

## What would change in the app

Recorded, not yet implemented — deliberately.

1. **Add a circuit breaker offset to the SPED model.** Biggest available correction, and
   it moves the gap in the *favourable* direction, which makes the rest harder to
   dismiss as advocacy.
2. **Re-base the athletics fee model** on $188,944 actual rather than $130,129 estimated.
   Several downstream figures move, including the $960 self-funding fee.
3. **Escalate SPED at its own observed rates** rather than folding it into salaries.
4. **Add a "money outside the budget" section** — $1.73M school-side, honestly annotated
   for what is restricted and what is not.
5. **Record the make-or-buy move** on the bend-the-curve page, with its fragility stated.
6. **Note the reporting lag** in Context or Structural.

## Still missing

- **FY26 year-end circuit breaker balance and draw.** The one number that would settle
  §2.1. Everything else here is solid; this is the load-bearing caveat.
- Out-of-district **placement counts** by year, not just dollars. Dollars ÷ count gives
  the average tuition, which is what actually escalates.
- FY26 year-end actuals on 9300/9400 — did the $1.53M committed hold?
- In-district SPED enrolment and the district SPED rate against the Chapter 70
  foundation budget's assumed rate. Where actual exceeds the assumption the town eats
  100% of the difference, and a hold-harmless district never catches up.
- Whether the FY27 tuition line is gross or net of circuit breaker (§2.1).
- Sept 3, 2026 STM warrant and result; FY27 certified free cash post-STM.

---

## Part 4 — What this actually changes in the app

Worked through 27 Aug 2026, before any code changed. Three of the fourteen conclusions
move; roughly half the app is untouched.

### 4.1 The headline gap: a range, not a number, until one figure arrives

The app headlines **$552,621/yr** average shortfall FY28–FY30. Two corrections pull in
opposite directions:

| | $/yr |
|---|---:|
| Headline gap | 552,621 |
| **+** SPED escalated at its own observed rates (§1.2) | +135,000 |
| **= Branch B** — circuit breaker draw is a year-end timing artifact | **687,621** |
| **−** circuit breaker offset at FY26 actual receipts ($326k) | → **361,621** |
| **−** circuit breaker offset at FY27 projected receipts (~$600k) | → **87,621** |

**The gap is somewhere between ~$88,000 and ~$688,000 a year — a 7.8× spread — and
which end depends entirely on the FY26 year-end circuit breaker figure.** In Branch A
the accumulated $615,301 is additionally available as a one-time bridge; in Branch B it
is float and worth nothing.

This is the single highest-leverage unknown in the project. One question to the Business
Manager settles it.

Caveat on Branch A: the recurring offset is the *annual receipt*, not the balance. Once
the district draws it down, the fund runs at steady state and the $615,301 is spent
once. The offset is also capped by actual eligible SPED costs and cannot be spent on
anything else.

### 4.2 Conclusions that move

**#5 — "Athletics cannot pay for itself once you put the buses back" ($960/season).**
This is the one that may flip. Actual FY26 collection was **$279.85 per HS
participation** against the model's assumed $214 — a factor of **1.308**. Scaling
through:

- self-funding fee: $960 → **~$734**
- peak revenue at the revenue-maximising fee: $358,380 → **~$468,652**

The app's headline says restoring the full $451,830 program is "out of reach at any
fee." At $468,652 it is **no longer out of reach** — just barely reachable, at a fee
around $1,185 and a loss of roughly 30% of participants. The conclusion needs rewriting
from "impossible" to "possible but self-defeating," which is a different argument.
Requires proper recomputation in `price.ts` — the 1.308 scaling is indicative, not exact,
because the demand-dropoff curve interacts with it.

**#3 — "Grew 1.08% while neighbours grew 2.9–6.5%."** Survives, needs a footnote: DESE
in-district expenditure excludes out-of-district tuition by construction (§1.6).

**#14 — "Nothing closes the gap without either an override or teachers" (68%).** Holds
in Branch B. In Branch A, with a $326k–$600k recurring offset plus higher realized fee
revenue, it is **materially overstated** and may be wrong. Do not restate this
conclusion either way until §4.1 resolves.

### 4.3 Conclusions that do not move

**#6 through #12 — the entire tax-base and business-formation argument.** New growth,
commercial share, homes-per-pupil, the $42.6M break-even, business counts. None of it
touches SPED or fees. About half the app is unaffected.

**#1, #2, #4, #13** hold, and #1 and #2 get *stronger*: a larger SPED share means a
smaller cuttable base, so "cutting every extra buys one year" and "only classroom
positions are big enough" are more true, not less.

### 4.4 Rates and figures in `model.json` that are wrong

| Field | Current | Should be |
|---|---|---|
| `currentFees.estimatedFy26Revenue` | 130,129 | **188,944** (actual) |
| `currentFees.priorEffectiveAthletic` | 214 | **~280** (162,871 ÷ 582) |
| `currentFees.estimatedPriorAthleticRevenue` | 109,602 | **162,871** HS only |
| `currentFees.waiverAssumption` | 0.12 | too high — realized collection was 31% above model |
| `currentFees.estimatedAthleticRevenue` | 187,451 | understated; old schedule already collected $188,944 |
| `currentFees.feeIncreaseValue` | 77,849 | likely **$100–115k** |
| `athletics.peakRevenue` / `peakFee` | 358,380 / 1,185 | recompute |
| `levers[athletic_fees].selfFunding` | 960 | **~735**, recompute |
| `expenseBase.sped_tuition` | 700,142 | needs a gross-vs-net decision (§2.1) |
| SPED inside `salaries` @ 4% | — | observed **6.1%/yr**; needs its own rate |

Note `chargeableParticipations: 582` excludes middle school, but MS fees of **$26,074**
were actually collected in FY26. FY27 eliminated MS sports, so that revenue disappears —
which the model does not currently show either way.

### 4.5 Charts and components affected

**Deep — engine-level, everything downstream moves:**
`model/rates.ts` (the six-bucket escalator), `model/engine.ts`. SPED currently splits
across `salaries` / `transport` / `sped_tuition` at three rates none of which match its
behaviour. Either a seventh bucket or a SPED-specific rate. Touching this moves
`YearChart`, `Magnitude`, `CutLine`, `Forever`, `LevelVsSlope`, `Walkthrough` and the
headline automatically.

**Direct — fee model:**
`FeeCurve`, `SportCutter`, `Athletics`, `Levers`, `PriceList`, `Packages`,
`Recommendation`, `model/price.ts`, `model/answers.ts`.

**Copy only:**
`Peers` (add the in-district scope footnote), `Conclusions` (#3, #5, #14).

**New, parallel to the athletics treatment:**
A SPED analysis section — composition, the make-or-buy move, the out-of-district cliff,
the circuit breaker. Plus a "money outside the budget" section for §2.4/§2.5.

**Untouched:**
`TaxBase`, `TaxBaseMix`, `CommercialTrend`, `BusinessFormation`, `GrowthDial`,
`Development`, `TaxpayerView`.

### 4.6 Order of work, when the time comes

1. **Ask the Business Manager the circuit breaker question.** Nothing else should be
   built until §4.1 resolves — it determines whether the app's central claim stands.
2. Re-base the fee model on FY26 actuals. Self-contained, no dependency on step 1.
3. Give SPED its own escalation rate.
4. Add the SPED analysis section.
5. Rewrite conclusions #3, #5, #14 last, once 1–3 have settled the numbers.
