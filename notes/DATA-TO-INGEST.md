# Data to ingest — a running queue

Things TJ has found or downloaded that are not yet in the archive. **Nothing here has been
read, checked or believed.** A row leaves this file only when it is fetched, hashed,
catalogued with its address (rule 12), and either loaded or explicitly refused with a reason.

Drop files in `sources/inbox/` and add a line here. The inbox is a staging area, not a home:
`scripts/check_archive_layout.py` decides where a document actually belongs, keyed on how it
reached us.

---

## Downloaded, awaiting ingest

| what | where it came from | status |
|---|---|---|
| District Expenditures by Function Code | DESE `cnfs-edqq` — the `GEN_FUND` / `GRNTS_REVOLV` split | agent ingesting |
| District Expenditures by Spending Category | DESE `er3w-dyti` | agent ingesting; may duplicate `dese_measure` |
| School Expenditures by Spending Category | DESE `i5up-aez6` — school level, new granularity | agent ingesting |

## Identified, not yet downloaded

Ordered by the gap each closes. IDs are Socrata dataset ids on
`educationtocareer.data.mass.gov`; the catalog API lists 207 datasets, 102 of them
finance, staffing or enrolment related.

| id | dataset | closes |
|---|---|---|
| `vxt3-k35x` | Where Residents Go to School (Sending) | how many children leave and for where — VERIFIED, 2014-2026, 58 left via school choice in SY2026 |
| `8xyg-59b2` | Reasons for Student Enrollment by Town (Receiving) | the other direction — choice money in |
| `ab34-d3ma` | Special Education Circuit Breaker Reimbursements | a fund rule 11 names as unmapped |
| `5izv-jyrd` | Chapter 70 Foundation Budget and NSS | the formula behind the state-aid rate |
| `qt58-634r` | Chapter 70 Program Information and Data | the fuller Chapter 70 series |
| `5845-7546` | Educators | staffing headcount / FTE |
| `77fu-a6h8` | Teachers by Grade and Subject | grade-level staffing, currently answerable only in names |
| `vd2f-ib9q` | Teachers by Program Area | may separate special education staff |
| `4684-cw3t` | Elementary and Secondary Teacher Data | the general staffing series |
| `yamx-769q` | Special Education Indicators | |
| `n62c-bx65` | Special Education Program Characteristics | |
| `92x3-2qj9` | Special Education Placement Trajectory | |
| `8aww-sugs` | Students Moving In and Out of Special Education | |
| `t8td-gens` | Enrollment by Grade | denominators for all of the above |

## Arrived, not yet catalogued

Staged in `sources/inbox/`, hashed, unread.

| file | source | sha256 (first 12) | what it offers |
|---|---|---|---|
| `dese-teachers-by-grade-subject.xlsx` | DESE `77fu-a6h8`, 133 MB | `76a5498ba1b5` | **FTE by grade band AND subject AND school.** Breaks a limit recorded as structural: grade detail without FTE (town rosters) or FTE without grade detail (DESE) — this is both |
| `dese-residents-sending.xlsx` | DESE `vxt3-k35x`, 2.4 MB | `ef345000874d` | where resident children go, by receiving district and reason, 2014-2026 |
| `dese-enrollment-receiving.xlsx` | DESE `8xyg-59b2`, 2.2 MB | `b23f4106f6c0` | who comes IN, by sending town and reason — the mirror of the file above |
| `dese-circuit-breaker.xlsx` | DESE `ab34-d3ma`, 449 KB | `b710ba4f88fb` | high-cost special education reimbursement — **and a STUDENT COUNT**, `ELIG_STU_CLAIM_CNT` |
| `dese-ch70-foundation-nss.xlsx` | DESE `5izv-jyrd`, 328 KB | `2f581d1c6eda` | foundation budget, and **required vs actual net school spending** — 2008-2022 only |
| `dese-educators-retention.xlsx` | DESE `fz9c-2g33`, 1.6 MB | `be8a87c9471e` | **headcount by job class — including Administrator and Paraprofessional** — plus hires and retention. 2021-2023 only |
| `dese-teacher-data.xlsx` | DESE `4684-cw3t`, 25 MB | `4fbe81d65aee` | teacher counts, **student-teacher ratio**, licensure, experience, in-field, by school and subject |
| `dese-sped-indicators.xlsx` | DESE `yamx-769q`, 11.8 MB | `41d517465d59` | **a published COUNT of students with disabilities** (217-265), plus sped staffing ratios, outcomes, 2017-2026 |
| `dese-sped-placement-trajectory.xlsx` | DESE `92x3-2qj9`, 762 KB | `ff3e4c9e8dd8` | where a child STARTS against where they end up — the route into out-of-district, 2018-2026 |
| `dese-sped-program-characteristics.xlsx` | DESE `n62c-bx65`, 5.3 MB | `417435bddfca` | disability type and demographics behind the SWD count |
| `dese-sped-movement.xlsx` | DESE `8aww-sugs`, 1.1 MB | `2b5e67f3ba6b` | students entering and leaving special education each year |

Columns, recorded so nobody has to reopen a 133 MB file to find out:

    teachers:  SY DIST_CODE DIST_NAME ORG_CODE ORG_NAME ORG_TYPE SUBJ
               PK2_CNT PK2_PCT GRD_3_5_CNT GRD_3_5_PCT GRD_6_8_CNT GRD_6_8_PCT
               GRD_9_12_CNT GRD_9_12_PCT MULTI_GRD_CNT MULTI_GRD_PCT
               ALL_GRD_CNT ALL_GRD_PCT FTE_CNT

    sending:   SY TOWN_NAME ENR_REASON DIST_CODE DIST_NAME ENR_CNT

    receiving: SY DIST_CODE DIST_NAME ENR_REASON TOWN_NAME ENR_CNT

    circuit:   FY DIST_CODE DIST_NAME ELIG_STU_CLAIM_CNT TOT_ELIG_EXPENSES
               THRESHOLD_AMT NET_ELIG_INSTR_TUIT_COSTS NET_ELIG_TRANS_COSTS
               TOT_NET_CLAIM REIMB_INSTR_TUIT REIMB_SPEC_IND_INSTR_TUIT
               REIMB_TRANS REIMB_SPEC_IND_TRANS PRIOR_YEAR_ADJ
               TOT_QTLY_PAYMENT EXTRA_RELIEF_PAYMENT ADDL_SUPPL_PAYMENT COMMENTS

**Two reasons the circuit breaker file matters more than its size suggests.**

`ELIG_STU_CLAIM_CNT` is a count of CHILDREN, not dollars. This project repeatedly stops at
"dollars are not students" (rule 7); this is a published headcount of high-cost special
education students per district per year, and it stands beside the placement counts already
held.

And circuit breaker is one of the funds rule 11 names as unmapped — money that offsets
out-of-district and high-cost placements, which is the line the in-district special
education escalator rests on. It also splits reimbursement into instruction/tuition against
transportation, with prior-year adjustments and relief payments broken out, so a year's
receipt can be told apart from a year's entitlement.

**The Chapter 70 file answers a question nobody in town can currently put a number on:
does Lunenburg spend above or below the minimum the state requires?**

    SY      required NSS     actual NSS    over/under   % of required
    2017     15,538,425     19,861,673     4,323,248      1.28
    2020     17,948,505     22,275,868     4,327,363      1.24
    2022     18,731,996     23,919,189     5,187,193      1.28

About 128% of the floor, stable for six years, $4.3-5.2M above it.

**Publish the measurement and both readings, never a verdict.** "The town already spends
well above what the state requires" is true. So is "the required minimum is a floor, not a
standard of adequacy" — the foundation formula has been criticised for decades as
understating real costs, which is what the 2019 Student Opportunity Act addressed. A page
that gives one of those without the other is taking a side using a number.

**It stops at SY2022**, three years behind. Later years are probably in `qt58-634r`.

**CASELOAD MOVEMENT, and a duplicate row to check before anyone quotes it.**

    SY   enrolled  on IEP  moved IN  moved OUT   net
    2019     1518     254        28         40   -12
    2022     1439     207        33         28    +5
    2024     1448     222        38         17   +21
    2025     1448     222        38         17   +21

**SY2024 and SY2025 are identical across all four columns.** Four independent counts landing
on the same values two years running is not plausible; it is far more likely a row carried
forward. Check it against DESE before either year is used, and do not let the +21 be quoted
twice as though it were two years of the same movement.

The series otherwise gives the caseload dynamic behind the spending line — how many children
enter special education services each year and how many leave — which is the thing a
headcount alone cannot show.

**THE PLACEMENT TRAJECTORY SHOWS THE ROUTE INTO THE BIGGEST COST.** SY2026, K-12:

    started as                        n    no IEP  included  sub-sep  out-of-district
    Inclusive Setting               123     32.5%     60.2%     5.7%             1.6%
    Substantially Separate Classroom  28     10.7%     10.7%    64.3%            14.3%

A child starting in a substantially separate classroom is nine times more likely to end up
out of district than one starting included. Out-of-district tuition is the largest single
cost in the special education budget, so this is the pathway into it, and the district's
own stated strategy has been to keep children in district.

**The base is tiny and that governs how it may be used.** 14.3% of 28 is four children. One
year, one cohort. Nine years are in the file; a pattern across them would be worth
something, a single year is worth nothing, and quoting the percentage without the count
would be indefensible.

**TWO SOURCES DISAGREE ABOUT PARAPROFESSIONALS, AND THAT IS THE FINDING.**

`yamx-769q` publishes a real count of students with disabilities — 217 to 265 — which
closes a gap properly: the count was previously only reachable by multiplying a published
percentage by enrolment, which was our arithmetic and not a published figure.

It also gives special education paraprofessionals per 100 students with disabilities. Times
the count, that implies an FTE:

    SY2019  265 SWD x 18.5/100 = 49.0 FTE
    SY2021  249 SWD x 16.7/100 = 41.6 FTE
    SY2023  230 SWD x 10.4/100 = 23.9 FTE
    SY2026  246 SWD x  7.3/100 = 18.0 FTE

Against the district's own special education paraprofessional budget line, which rose 94%
over the same period. Divide one by the other:

    SY2019    672,872 / 49.0 FTE = 13,732 per FTE
    SY2023  1,018,072 / 23.9 FTE = 42,597 per FTE
    SY2025  1,244,894 / 18.0 FTE = 69,161 per FTE

**A paraprofessional does not cost $69,000.** So these two figures are not about the same
population: either DESE counts something narrower than the budget line, or the line carries
more than paraprofessionals, or a reclassification moved people between categories. What is
established is that the two cannot both be measurements of the same thing — not that
paraprofessionals became expensive.

**Do not publish either number as an answer to the paraprofessional question until this is
resolved.** It looks like the discrimination we have wanted all week (dollars against
people) and it is currently a contradiction wearing that costume.

**Related and probably the same defect:** `vd2f-ib9q` shows Lunenburg special education
teacher FTE falling 18.5 (2008) to 2.0 (2026) — a 90% collapse — while general education
FTE holds at 100-113 and total FTE is flat. Teachers being recoded from special education
to general education produces exactly that signature. Rule 6.

**A CORRECTION I OWE TJ: administrator headcount IS published.** I told him DESE gave
administration only as a spending category, not a count of people. `fz9c-2g33` gives both,
by job class group:

    SY     Administrator   Other-Lic   Other-Non-Lic   Paraprofessional   Teacher
    2021             28          28              74                120        228
    2022             34          32              78                112        234
    2023             38          28              76                118        246

**Read it carefully before it becomes a talking point.** Administrators rise 28 -> 38, +36%
in three years. But three years is thin, ten people is a small base, and a reclassification
would look identical — note `Other - Licensed` goes 28, 32, 28, which is the shape a recode
leaves behind. It is also HEADCOUNT, not FTE: a half-time director and a principal are one
each. A real signal, not yet a finding.

**The paraprofessional column is the prize.** 120 -> 112 -> 118, roughly flat, against a
spending line that roughly doubled. Headcount flat while dollars rise is exactly the
discrimination this project could not make — see the BOUNDED verdict in
`notes/findings/CAN-WE-ANSWER-IT.md`, which this may promote.

**Note the key is `FY`, not `SY`.** Every other file here is school year. Joining them
without checking that would be the fiscal-year type error this repo has already had once,
in the other direction.

**The two enrolment files are a matched pair and are worth more together.** Sending gives
where Lunenburg's resident children go; receiving gives who arrives and from where. Both
directions means a NET position, and the tuition that follows each way. This project holds
`School Choice Receiving` as one dollar line on the cherry sheet; these are the headcounts
behind it.

**A caution on the teachers file before anyone aggregates it.** It carries a `State` row
(`DIST_CODE 00000000`) alongside district rows, and a `SUBJ` of `All` alongside individual
subjects. Both are rollups sitting in the same column space as detail — the same shape that
produced $116M for a $26.6M district in the expenditure data. Establish the levels before
summing anything.

---

## What these sources ARE, so nobody over-reads them

DESE is not a third party and not an auditor. These are **statutory returns**: the
district's own figures, filed because the law requires it, on a schema DESE sets, alongside
300+ districts filing identically.

**The value is that the schema is not the filer's to choose.** The town's budget book can
present a line net of grants and never mark it as net — rule 11. On DESE's form `GEN_FUND`
and `GRNTS_REVOLV` are separate boxes and both must be completed.

**What they are still not:** self-reported and reviewed rather than audited line by line; an
annual return rather than transactions, so they say what fell in which bucket and never what
a payment bought; and a different quantity from the appropriation, so where they disagree
with the town both can be right about different things.

On the confidence ladder: **cross-checked, not traced.** A promotion for most of what this
project holds, and still not the top rung.
