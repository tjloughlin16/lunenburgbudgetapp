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

Columns, recorded so nobody has to reopen a 133 MB file to find out:

    teachers:  SY DIST_CODE DIST_NAME ORG_CODE ORG_NAME ORG_TYPE SUBJ
               PK2_CNT PK2_PCT GRD_3_5_CNT GRD_3_5_PCT GRD_6_8_CNT GRD_6_8_PCT
               GRD_9_12_CNT GRD_9_12_PCT MULTI_GRD_CNT MULTI_GRD_PCT
               ALL_GRD_CNT ALL_GRD_PCT FTE_CNT

    sending:   SY TOWN_NAME ENR_REASON DIST_CODE DIST_NAME ENR_CNT

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
