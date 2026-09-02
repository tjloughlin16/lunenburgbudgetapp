# FY26, as the books stood in June

> **Working state:** `notes/HANDOFF.md` carries the current branch and what is established
> versus assumed. `CLAUDE.md` carries the rules.

Analysis, 2 September 2026. Every figure recomputed by
`scripts/verify_fy26_closeout.py` from `sources/data/lunenburg.db`.

Each section is written twice: **In plain terms** for anyone, and **The evidence** for
anyone who wants to check it. The plain version never states anything the evidence does
not support.

---

## What this rests on, and what it is not

On 2 September 2026 the Town Manager sent the FY26 year-to-date budget report in two
forms, printed and as a spreadsheet. It is the **first account-level general fund
expenditure report this project has ever held.** Every prior one was run as a department
rollup, which renders the entire school district as a single row.

Here the school department is **258 accounts**, each with an org code, an object code and
a description.

**Three limits travel with every figure below, and none of them is a technicality.**

**It is period 12, not period 13.** Period 12 is June. Period 13 is the year-end close,
after purchase orders are cleared in the lapse period. The Town Manager said so in the
covering note: the figures *"are likely to continue to adjust as we continue the year-end
reconciliation process."* In FY25 that step moved the school figure by $21,770.53 between
two School Committee meetings a fortnight apart. **So nothing here is a surplus. It is a
position.**

**Zero-balance accounts are suppressed.** The report was run with `Suppress zero bal
accts: Y`. An account absent from it is not necessarily absent from the ledger, and
nothing below reasons from what is missing.

**It is expenditures only, Fund 0100.** No grants, no revolving funds, no school choice.
The district's budget is *net* — a line is what the town must raise after other money has
paid for part of the thing — so none of this says what anything costs.

---

## 1. The headline number is a residual, not a result

### In plain terms

The school department was **$482,101 under budget** in June. That single number is the
small remainder of two much larger flows running in opposite directions: about $1.68
million unspent across 160 accounts, and about $1.20 million overspent across 56.

Reading $482,101 as "the schools underspent by half a million" describes the arithmetic
correctly and the year not at all.

### The evidence

| | |
|---|---:|
| Original appropriation | $26,247,474.00 |
| Transfers and adjustments | $85,090.24 |
| Revised budget | $26,332,564.24 |
| Expended | $25,613,679.23 |
| Encumbered | $236,783.89 |
| **Unspent** | **$482,101.12** |

| | accounts | amount |
|---|---:|---:|
| Under their revised budget | 160 | $1,683,534.14 |
| Over their revised budget | 56 | $1,201,433.65 |
| **Net** | **258** | **$482,101.12** |

Town-wide at the same period: $51,189,965.10 appropriated, $2,826,046.42 transferred,
$52,163,984.85 spent, $529,325.69 encumbered, **$1,322,700.98 unspent.**

The Town's own release of 1 September 2026 put the school figure at "approximately
$470,000 to $600,000" and the town-wide figure at "roughly $1.63 million". The school
figure here sits inside that range near the bottom. **The town-wide figures differ and are
not reconciled here** — the release is preliminary, this is one report at one period, and
nothing published says how the release's figure was struck.

### What this does not show

Whether any of it survives the close. Encumbrances of $236,783.89 are still open, and
clearing purchase orders releases some of that back and commits the rest.

---

## 2. The biggest movers

### In plain terms

Two out-of-district special education lines account for most of the movement in both
directions, and they move opposite ways. Beneath them sit one of the district's four
psychologist accounts that spent nothing all year, a utility overrun, and
paraprofessional lines that all ran over.

### The evidence

| account | | revised | spent | encumbered | left |
|---|---|---:|---:|---:|---:|
| `S0511062` | SPED PRIVA — out-of-district, private | $988,630 | $466,001 | $0 | **+$522,629** |
| `S5511062` | COLL TUITI — out-of-district, collaborative | $302,663 | $678,062 | $58,708 | **−$434,108** |
| `S3991742` | ELEC CHGS — electricity | $271,132 | $319,109 | $62,362 | −$110,338 |
| `S1511062` | CONT SERV — special services contracted | $105,500 | $204,758 | $1,262 | −$100,520 |
| `S2072061` | PSYCHSALAR — one of four psychologist accounts, §4 | $98,784 | $0 | $0 | +$98,784 |
| `S2032121` | KINDAIDREG — kindergarten paras | **$0** | $93,691 | $0 | −$93,691 |
| `S3991692` | SPED TRANS — special ed transport | $565,735 | $620,025 | $13,265 | −$67,555 |
| 4 accounts | special education paraprofessionals | $1,352,508 | $1,458,152 | $0 | −$105,644 |

**The last column is `revised − spent − encumbered`, not `revised − spent`**, and the
encumbrance column is printed because without it the arithmetic does not appear to work.
`COLL TUITI` is the clearest case: $302,663 − $678,062 is $375,399, and the figure is
$434,108, because $58,708 is committed under purchase orders that have not yet been paid.
An earlier version of this table showed the variance and omitted the encumbrance it was
computed from.

**An encumbrance is money promised under a signed contract and not yet paid out.** At the
year-end close some of it is paid and the rest is released back, which is exactly the step
this report predates.

**The two out-of-district lines together**: $1,291,293 budgeted, $1,144,063 spent, a net
of **+$88,522**.

### What this does not show

**Why the two out-of-district lines moved in opposite directions.** It is tempting to read
a shift from private placements toward collaboratives. That precise inference — two budget
lines moving in opposite directions by similar amounts — is one of the three errors
`CLAUDE.md` records as having shipped here before being caught. What is established is the
two numbers. Placement counts by year are not published, so dollars cannot distinguish
fewer children from a different mix from a differently struck budget.

**Whether the special education paraprofessional overruns mean more staff.** They are
dollars. A budget line is not a filled position.

---

## 3. Kindergarten paraprofessionals — an open question

### In plain terms

The FY26 approved budget cut the kindergarten paraprofessional line to zero and published
it as a **−100% cut**. During FY26, **$99,064 was spent on kindergarten paraprofessionals
anyway**, against an appropriation of nothing and with no transfer covering it. In
February 2026, while that spending was happening, the district asked for a kindergarten
paraprofessional back as a **new** staffing request for FY27, at $22,205. It did not make
the FY27 proposed budget.

**No meeting document connects either the cut or the spending to a decision.**
Kindergarten paraprofessionals do appear in the minutes — twice — and both times as an
FY27 staffing request, never in relation to FY26. The distinction matters and an earlier
draft of this section did not make it.

**This is not presented as an impropriety.** Money is routinely spent and reconciled later
through a year-end transfer, and the FY26 transfer schedule is exactly what we do not
have.

### The evidence

**The cut, published.** FY26 School Committee approved budget, 12 March 2025, page 7,
under `2330 - Paraprofessionals General Education`:

    Kindergarten Paraprofessionals   77,699.88$   73,273.00$   (73,273.00)$  -100.00%   (73,273.00)$  -100.00%
    H.S. Paraprofessionals /Regular  18,435.23$   47,960.00$   (47,960.00)$  -100.00%   (47,960.00)$  -100.00%

**The history, from the FY27 workbook** (`fy27-proposals.xlsx`, sheet `FY27 Budget
Projection`, and identical in its traceable twin):

| cell | | value |
|---|---|---:|
| `C332` | FY23 actual | $75,501.66 |
| `D332` | FY24 actual | $77,699.88 |
| `E332` | FY25 actual | $83,765.97 |
| `F332` | FY25 budget | $73,273.00 |
| `G332` | FY26 final budget | `-` |
| `J332`–`M332` | every FY27 proposal | `-` |

Row 333, `Kindergarten Aides/Regular`, exists only from FY26: `G333 = 0`, `H333 =
59,709.10` of actuals to date. **That row is the ledger account surfacing in the workbook,
not a renamed budget line** — it does not appear in the FY26 approved budget at all.

**The spending, from the ledger at period 12:**

| account | object | original | transfers | revised | spent |
|---|---|---:|---:|---:|---:|
| `S2032121` KINDAIDREG | 511103 | $0 | $0 | $0 | $93,691.03 |
| `S2032131` KINDPARREG | 511203 | $0 | $0 | $0 | $5,373.12 |

**$99,064.15 against an appropriation of $0.**

**The mechanism exists and was used elsewhere.** Nine school accounts spent with no
original appropriation. Six received a transfer to cover it — `HS GUID SE` $42,967,
`DUES/FEES` $29,965, `PHYS ED SU` $550 among them. These two received nothing.

**The request, in the minutes.** Finance Committee, 26 February 2026, under *Staffing
Increase Requests — Primary School*:

    1 Interventionist to address the early literacy and math gaps: $72,441
    1 Kindergarten Paraprofessional: $22,205

and, in the same list, *"The above listed position costs do not include insurance costs."*
A resident named the same request in public comment to the School Committee on 10 March
2026.

**Both mentions are FY27 requests.** Neither refers to the FY26 cut or to the FY26
spending. That is the whole of what the minutes say.

### A partial conclusion, offered as one

The service continued. Kindergarten paraprofessionals were paid throughout FY26 at a level
comparable to prior years — $99,064 against actuals of $75,502, $77,700 and $83,766 in the
three years before — while the line carrying them was budgeted at zero.

### What this does not show, and three readings that fit equally well

1. **A recoding.** The appropriation landed under a different line and the spending did not
   follow it. `H.S. Paraprofessionals /Regular` was cut the same way and shows *no* FY26
   spending, so the cut was real somewhere; it is not established that it was real here.
2. **A grant expected to cover it.** The Town has stated that about $287,000 of
   out-of-district tuition was charged to the FY26 IDEA grant rather than the operating
   budget, so grant-shifting demonstrably happened in FY26. Nothing links it to this line.
3. **An unreconciled overrun** awaiting the year-end transfer that has not yet been voted.

**Do not treat the $22,205 request as the cost of the FY26 spending.** It is one position,
excluding insurance, in a different fiscal year. $99,064 ÷ $22,205 is arithmetic, not a
headcount.

### What would settle it

The FY26 year-end transfer schedule, by department and account, with the authority for
each. And Finance Committee minutes from 14 July 2026 onward.

---

## 4. Four psychologist lines, and one of them spent nothing

### In plain terms

The district carries four school psychologist accounts and four social worker accounts,
one per building. **Three of the four psychologist lines spent their budget in full or a
little over. The fourth spent nothing at all, all year — $98,784 budgeted, $0 out.**

The social worker lines are less stark but point the same way: two spent in full, one
spent 68%, one spent 23%.

Between them the eight accounts left $194,718 unspent, which is about 40% of the
department's entire net underspend.

### The evidence

| account | | budgeted | spent | |
|---|---|---:|---:|---:|
| `S2044061` | PSYCHSALAR | $98,784 | $101,510 | 103% |
| `S2055061` | PSYCHSALAR | $45,106 | $45,306 | 100% |
| `S2066061` | PSYCHSALAR | $45,106 | $45,306 | 100% |
| `S2072061` | PSYCHSALAR | $98,784 | **$0** | **0%** |
| | **four psychologist accounts** | **$287,780** | **$192,122** | |
| `S2044651` | SOCWORKSAL | $92,939 | $92,939 | 100% |
| `S2055651` | SOCWORKSAL | $92,939 | $63,214 | 68% |
| `S2066651` | SOCWORKSAL | $90,212 | $20,877 | 23% |
| `S2072651` | SOCWORKSAL | $92,939 | $92,939 | 100% |
| | **four social worker accounts** | **$369,029** | **$269,969** | |

All eight carry object code `511023` or `511024`, and none received a transfer.

### Why it matters beyond the money

`CLAUDE.md` lists as a standing question: *"Whether budgeted positions were filled. A
budget line is an intention."* For these eight lines, in this one year, the ledger comes
closer to answering it than anything this project has held before — three lines paid in
full look like filled posts, and one paid nothing does not.

### What this does not show

**That a post was vacant.** A line spending nothing is consistent with a vacancy, with a
person paid from a different account, with a grant-funded position, or with a coding
change. Rule 7: the measurement is the dollars.

**And it is deliberately not stated as "a school psychologist was cut".** An earlier draft
of this section quoted the zero line alone and described it as *a position budgeted and not
spent*, which read as a statement about the district's psychologists in general. It is one
of four. `scripts/verify_fy26_closeout.py` caught it because the figure it derived from the
database did not match the figure in the prose.

## 5. $85,090 moved into the schools, and no vote is on the record

### In plain terms

The ledger shows $85,090.24 of transfers into the school department during FY26. The
Finance Committee took up year-end transfers twice and no minutes exist in this archive
for either meeting.

### The evidence

Finance Committee, 11 June 2026:

> "**a. Year End Transfers** — The documents needed on this topic were not provided but
> should be available for the next meeting."

It returned to the agenda for 14 July 2026. The archive holds Finance Committee **agendas**
through 27 August 2026 and **minutes** only through 11 June 2026. Four meetings have an
agenda and no minutes, and the first of them is the one that took up transfers.

### What this does not show

That no vote happened. Minutes may not be posted yet, and not every transfer requires a
Finance Committee vote. What can be said is that **no document in this archive connects any
dollar of movement to a decision.**

---

## 6. What none of this can see

$1,736,376 was spent on the schools in FY26 from 61 funds outside the general fund —
school lunch, extended day, the IDEA grants, athletics, after-school. **Not one dollar of
it can be attached to a budget line**, because no published document maps a fund's
spending onto the district's lines.

So every figure above is the **town's share**. A line that fell may mean less service, or
may mean a grant paid for it. The expense side cannot tell them apart, and neither can
this document.

---

## What would change these findings

In order of how much each would settle:

1. **The FY26 period 13 report.** Turns every figure here from a position into a result.
2. **The year-end transfer schedule**, by account, with authority. Settles §3 and §5.
3. **The same report for funds other than 0100.** Turns the net budget into a gross one.
4. **Finance Committee minutes from 14 July 2026.**
5. **Out-of-district placement counts by year.** The only thing that would let §2's two
   tuition lines be read as anything other than two numbers.

## How to reproduce

    python3 scripts/build_db.py
    python3 scripts/verify_fy26_closeout.py
