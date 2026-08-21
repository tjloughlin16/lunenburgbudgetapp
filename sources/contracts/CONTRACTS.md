# Lunenburg school employee contracts — what was agreed, and when it ends

All files pulled 2026-08-20. `pdf/` originals · `txt/` extracted text · `data/` derived CSV.

Sources:
- Lunenburg Public Schools, Personnel/HR → Forms & Documents
  <https://www.lunenburgschools.net/department-directory/personnel-human-resources/forms-documents>
- DESE Educator Contracts, org code 01620000
  <https://profiles.doe.mass.edu/profiles/general.aspx?orgcode=01620000&orgtypecode=5&leftNavId=16862>

Most of these are page scans with no text layer. They were read with the macOS Vision
text recogniser via `scripts/ocr_pdf.swift` — no network, no third-party install. **OCR
output is not a transcript.** Numeric grids in particular come back with columns
interleaved. Every figure quoted below was checked against the contract's own stated
arithmetic before being used; see "Verification" at the end.

---

## The headline: what teachers were actually given

**Lunenburg Education Association (teachers, nurses, athletics & stipends)**
Term **July 1, 2024 → June 30, 2027** (FY25, FY26, FY27). Article XX, §A.1:

> **Which copy this is.** The contract is posted twice — by the district on its HR page
> (70pp) and by DESE as a state filing (72pp). Their text agrees to 99.1%; the DESE copy
> is the same document plus a two-page appendix listing the paid leadership and stipend
> roles (curriculum content liaisons, building leadership teams, dean of students,
> technology leads). The superset is kept as `pdf/dese-teacher-contract.pdf`. The
> district copy's extracted text is kept at `txt/lea-teachers-2024-2027.txt` as the
> cross-check; its PDF was dropped rather than store 53MB twice.

| Year | Cost-of-living adjustment to the salary scale |
|---|---|
| FY25 | **2.5%** |
| FY26 | **4.0%** |
| FY27 | **3.5%** |

Compounded, the scale rose **10.33%** over the three years. The same percentages were
applied to the Athletic and Extra Curricular Salary Schedules.

**These percentages are not what an individual teacher's pay went up by.** They move the
whole grid. On top of the grid moving, an individual also advances:

- **Step increases** — one step a year until the maximum, for anyone in paid status at
  least 90 school days (Art. XVI §4). Across the 13-step scale the average step is worth
  **3.32%**; steps 1→11 run 2.8–3.7%, step 11→12 is **5.7%** (a flat $1,000 was folded in
  effective 7/1/2022), and step 12→13 is 2.1%.
- **Lane changes** — moving right across ten columns (Bach → B+15 → B+30 → Masters →
  M+15 … M+75 → Doctorate) on completed coursework or a degree. Each lane is worth roughly
  $2,600 at FY25 rates. Notice is due by November 15, transcripts by June 15.

So a teacher below the top step in FY26 saw roughly **4% + ~3% ≈ 7%**, while a teacher at
step 13 in the same lane saw the 4% only. This is why the district's blended salary growth
assumption is ~4% rather than the 3.5% COLA: the assumption already contains step and lane
drift, netted against retirements replaced at step 1.

**It expires June 30, 2027 — the end of the budget year now being planned.** Either side
may open negotiations by giving notice by **November 1, 2026**; absent notice it renews
one year at a time (Art. XXV §A). The contract may also be reopened by mutual agreement,
limited to athletic stipends, the extra-curricular schedule, and the evaluation appendix
(§C) — which is the mechanism that would be used to change athletics pay without
reopening the whole agreement.

### Salary scale, FY25 as printed (Appendix B)

Bachelor's step 1 **$50,790** → Doctorate step 13 **$102,459**.
By FY27 the same two cells are **$54,670** and **$110,287**.
Full 13 steps × 10 lanes × 3 years: `data/lea-teacher-salary-schedule.csv`.

Other pay provisions: $400 differential for the school psychologist, $200 for guidance
counselors; work beyond the teacher year paid at 1/183rd of base; new coaches start at
step 1 of the coaching scale.

---

## Every school unit, side by side

| Unit | Term | Raises by year | Expires |
|---|---|---|---|
| **Teachers** (LEA) | FY25–FY27 | 2.5% · 4.0% · 3.5% | **June 30, 2027** |
| **Paraprofessionals** (AFSCME Council 93, Local 503) | FY26–FY28 | 3.0% · 2.0% · 2.0% | June 30, 2028 |
| **Custodians** (AFSCME Council 93) | FY27–FY29 | 3.5% · 2.5% · 2.5% | June 30, 2029 |
| Custodians, prior agreement | FY24–FY26 | — | expired June 30, 2026 |
| **Secretaries** | 2025–2028 | *not public* | June 30, 2028 |
| **Cafeteria** | 2023–2026 | *not public* | June 30, 2026 |

Paraprofessional scale runs four classifications (Para 1–4) over 9–11 steps; FY26 Para 1
starts at **$16.82/hr** ($21,101 a year) and FY28 Para 1 tops out at **$27.89/hr**
($35,169). Steps advance on the first July payroll, one a year, to the maximum
(Art. VI) — again, on top of the percentages above.

Custodial scale is four grades over five steps; FY27 grade 1 step 1 is **$20.88/hr**,
grade 4 step 5 tops **$29.83/hr**. Longevity $500 at 5 years rising to $1,750 at 20+;
clothing allowance $455.

Town-side units, from the 2026 Annual Town Meeting warrant (Articles 21–23): Firefighters
FY27–FY29, Municipal Employees (AFSCME 93) FY27–FY29, DPW (Teamsters 170) FY26–FY28. All
three funded out of the Salary Reserve line.

---

## Administrators

DESE publishes only **expired** template contracts for Lunenburg:

- **Superintendent**, 7/1/2018–6/30/2021: $148,000 → $153,000 → $157,000 (+3.4%, +2.6%).
  The FY27 budget carries the superintendent line at $178,350 — **+13.6% against the last
  published contract figure**, over five years, under an agreement that is not published.
- **Principal** (template, executed 4/4/2019), 7/1/2019–6/30/2022: $117,000 → $119,340 →
  $121,727, i.e. **2.0% a year**. 15 sick days a year accruing to 200.

The "Non-Affiliated Salary Schedule" posted on the HR page is **not** district
administrators — it is an FY18–FY20 hourly schedule for extended-day aides, cafeteria
monitors, greenhouse assistant and COTA, at 2% a year.

**Gap: there is no current, public salary agreement for the superintendent, the business
manager, the principals or the district directors.** Every administrator figure in the
budget model comes from the FY27 budget's own line items, not from a contract.

---

## Decisions on the record (School Committee, 2026)

Agendas and minutes for calendar 2026 are archived in `../minutes/`. Relevant to pay and
benefits:

- **2026-03-18** — Committee approved an **enhanced health insurance opt-out**, negotiated
  with the Public Employee Committee: eligibility after **1 year** of enrolment instead of
  2, and the incentive rises from **$2,000/$4,000** (individual/family) to
  **$3,000/$6,000**. This is a real cost-containment measure on the health line and it is
  already decided.
- **2026-04-15** — Negotiating representatives assigned: Sculimbrene and Young for
  cafeteria, Brzozoski and Gilman for custodial. **No teacher-unit assignment was made**,
  consistent with LEA talks not opening until after November 1, 2026.
- **2026-07-29** — Executive session noticed for collective bargaining / non-union
  personnel negotiations.

---

## What is still missing

1. **The successor teacher agreement.** Does not exist yet. FY28's largest cost driver is
   an open negotiation, and no projection can do better than an assumption here.
2. **Secretaries (2025–2028) and cafeteria (2023–2026).** Linked from the HR page, but the
   Google Drive files are permission-restricted — the links redirect to a Google sign-in
   rather than serving the file. They need a records request or a direct ask.
3. **Current administrator contracts.** DESE's copies are three and four years stale.
4. **Headcount by step and lane.** Without it, the split between COLA and step/lane drift
   in the district's 4% salary assumption cannot be reproduced from published documents —
   only bounded.

Items 2 and 3 are a public records request to the district; item 4 is a question for the
Business Manager.

---

## Verification

- The contract states FY26 = FY25 × 1.04 and FY27 = FY26 × 1.035. Applying that to the
  FY25 grid reproduces the printed FY26 and FY27 cells exactly where OCR read them
  cleanly (Bachelor step 1: 50,790 → **52,822** printed / 52,822 computed → **54,671**
  printed / 54,670 computed; Doctorate step 1: 74,253 → **77,223** printed / 77,223
  computed). `data/lea-teacher-salary-schedule.csv` is therefore built from the FY25 grid
  and the contract's own multipliers, not from OCR of the FY26/FY27 grids.
- Every FY25 row was checked for uniform lane-to-lane spacing to catch transposed digits.
  No cell deviated more than $200 from its row's typical spacing.
- The paraprofessional percentages were confirmed twice: the schedule prints "3.00%" and
  "2.00%" markers, and the step-1 rates give 16.82 → 17.32 (+2.97%) → 17.67 (+2.02%).
