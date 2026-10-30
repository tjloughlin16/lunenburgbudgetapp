# FY breakdown, preschool and free cash — working notes, 29–30 October 2026

TJ's review copy of one long session: the analysis and the answers, in one place. Not served by the
app. The work queue is `notes/HANDOFF-FY-BREAKDOWN.md`; this file is the why.

---

## 1. What shipped

| page | address | what it does |
|---|---|---|
| FY breakdown | /school-all-funds/fy-breakdown | one fiscal year, every fund; now public, on the school all-funds shelf |
| line / fund / group pages | /school-lines/…, /school-funds/…, /school-groups/… | 340 pages, public and in the sitemap (drawn in the browser) |
| School lines against budget | /school-all-funds/budget-against-actual | every school line's vote against spending, FY2018–FY2026 |
| Preschool | /school-all-funds/preschool | tuition goes to the Town; identifiable cost beside it |
| Town general fund | /town-funds/general-fund | school-generated Town receipts by year |

New on the FY breakdown page:
- **Chart / Table toggle** on "What it connects to" (the In / Out lists are gone).
- **The plan and what happened**: one label per fund, on a slant; circuit breaker one part; the
  figures table titled and centred.
- **The bridge**: constant step names, the year's wording underneath.
- **The biggest changes from last year**: cost every fund / final budget / left, top 8 by dollars.
- **Money in, money out**: every fund other than the general fund — received, spent, difference,
  balance at 30 June, against the year before. Capital articles left out (their money is voted, not
  received in the journal).
- **Where each source's money went**: one bar per source, split by the lines it paid, a tick at
  what it received.
- **School money that goes to the Town**: preschool tuition, student parking, a medical reimbursement.

Line pages: "What the bills were for" stacked; "Where its other payers went" now stacked bars per
payer with this line at the bottom. Fund pages: a money in / money out chart with the balance.

**Deploy lesson:** a Pages upload that dies mid-way (EPIPE / ECONNRESET) keeps nothing, so retries
never converge. Push the stage in three chunks to a preview branch (`--branch upload-staging`), then
deploy — 0 files left.

---

## 2. Money in, money out — what it found (measurements)

Circuit breaker (fund 2640):

| | FY2023 | FY2024 | FY2025 | FY2026 (open) |
|---|---:|---:|---:|---:|
| received | $415,750 | $301,589 | $608,818 | $325,970 |
| spent | $494,968 | $466,296 | $498,451 | $337,499 |
| held at 30 June | $347,676 | $182,969 | $293,335 | $281,806 |

- Opening balance 1 July 2022: $426,893.23 — derived from the March 2026 MUNIS ledger worked back
  through the journal, and equal to the FY2022 annual report's printed carried balance.
- $333,494.89 of the circuit breaker's FY2026 spending is ONE entry, 2026/12/000692, 29 June 2026,
  "RECLASS COLLABORATIVE TUITION", moving that cost off the general fund. NOT established why.
- IDEA received $0 in FY2026 against $435,542 spent (balance −$300,476). Hypothesis only: the grant
  is drawn after the money is spent.
- Two definitions on one page, on purpose: "Money in, money out" counts CASH (balances);
  "Where each source's money went" counts payments plus orders owed at 30 June (the site's "spent").
  Example: ARPA fund 2595, $75,000 ordered Jan 2025, paid Sep 2025.

---

## 3. The FY2025 annual report disagrees with the books (recorded in document-defects.csv)

The FY2025 town report's "Fund Balance 6/30/2025" column differs from our balances for 17 school
funds. Both editions were read by eye against our extraction — our reading is correct, signs included.

- **10 funds** (1300, 1301, 1305, 1308, 1311, 1312, 2200, 2640, 2750, 2793): four sources agree with
  us (FY2023 report's 1 July 2022, FY2024 report's 30 June 2024, the journal tied to period 13, the
  March 2026 MUNIS ledger); only the FY2025 edition differs. Circuit breaker: printed $333,494.89,
  ours $293,335.18 (+$40,159.71).
- **Sign flips:** 2750 printed (18.50) in FY2024, 18.50 in FY2025; 2793 4,001.89 then (4,001.89) —
  for funds that did not move. One edition has the sign wrong; ours matches FY2024.
- **6 funds** (2622, 2672, 2758, 2778, 2800, 2813): MUNIS ledger alone against the report.
- **1 fund** (2797): ours is the odd one out, by 12 cents.
- For most, the printed figure is not the fund's balance on ANY day of FY2025–FY2026 — not a
  different cutoff. 2758 and 2778 match partway through 30 June 2025 (a year-end-entry cutoff).
- The circuit breaker's printed $333,494.89 equals the 29 June 2026 reclass exactly. Not explained.
- Settles it: the Town's MUNIS special revenue fund-balance report at 30 June 2025 (records
  request), or — next spring — the FY2026 report's balance less FY2026's flows.

---

## 4. Budget against actual — decisions and what is left

- One report replaces the August one as the page; the old markdown stays archived.
- FY2018–FY2022 from the district's budget documents; FY2023+ from the journal, with three flags
  (underfunded, overbudgeted, restarted high; $5,000 and 10%, ours).
- **Decided, not yet built:** switch /budget-vs-actual to it; fill FY2018–FY2022 transfers and flags
  from the Finance Committee workbook (gl-history.csv — votes match the journal on every line,
  transfers differ on 12 of 269 and 15 of 265 lines, so labelled); merge the two older pages;
  restructure — per-year flags move to the FY breakdown, the report becomes a line × year grid.
- Next after that: each year's SIGNATURES at the top of the FY breakdown — the announced surplus,
  deficit, cuts, override — as said by whom, beside our figures.

---

## 5. Preschool — everything we established

**The money goes to the Town.** Families' tuition is a Town general fund receipt:

| segment | value | means |
|---|---|---|
| fund | 0100 | the general fund (the same fund the school budget's lines are in) |
| org | 01001 | the Town's general revenue department |
| object | 431900 | PRE-SCHOOL TUITION (4 = revenue) |

- Named "PRE-SCHOOL TUITION" in the Finance Committee's FY2025 local-receipts ledger; "PS TUITION"
  in the MUNIS revenue report; printed among Town receipts in the annual reports back to 1987.
- One fund, two kinds of account: revenue (4-codes) and expense (5-codes). The tuition is booked
  under the Town's revenue department, the preschool's costs under school lines; nothing links them.
- The school journal has NO preschool receipt in any fund, FY2023–FY2026, and none credited against
  an expense line. So the school budget carries the preschool at FULL cost; tuition offsets none of it.

**Tuition by year (selected):** FY2011 $29,404 · FY2014 $22,799 · FY2017 $38,697 · FY2018 $37,126 ·
FY2019 $16,591 · FY2020 $18,633 · FY2021 $11,648.82 (our dataset says 11.64 — a defect, fix it) ·
FY2022 $36,883 · FY2025 $70,247 · FY2026 to 31 March $75,279.

**The Town's estimate** (what it budgeted to receive): FY2025 $16,590 — and FY2020 also $16,590.
Both equal FY2019's receipts with the cents dropped. Why it is set there is not recorded anywhere.

**What the estimate means.** The Town budgets money IN as well as out ("estimated receipts" / "local
receipts"); with the levy and state aid they must cover what is voted. The estimate is counted when
the budget is balanced; anything received above it is unbudgeted and falls to the year-end surplus.
That practice is **conservative revenue estimating**.

**How it reaches free cash** (FY2025):

| | amount | where it goes |
|---|---:|---|
| the estimate | $16,590 | counted in balancing the budget — pays for general fund spending |
| above the estimate | $53,657 | the year-end surplus → part of "receipts over estimate" → free cash |
| received | $70,247 | |

None of it returns to the school budget for the preschool. Free cash can be spent on anything Town
Meeting votes. The only way to measure preschool's part is revenue minus estimate, line by line —
the surplus is the NET of every line, some over and some under.

**Only the general fund reaches free cash.** The school's special revenue funds (circuit breaker,
IDEA, athletic fee fund, revolving funds) keep their balances and carry forward. Preschool tuition is
NOT one of those — it is a revenue account inside the general fund. Contrast Extended Day (fund
1312): its own fund, fees in and staff out, balance kept for next year.

**The free cash calculation** (DLS proof, `state-dls/free-cash-proof-lunenburg.xlsx`):

| proof year | receipts over estimate (CL#6) | unspent appropriations (CL#11) |
|---|---:|---:|
| 2021 | $590,516 | $1,377,642 |
| 2022 | $1,049,137 | $754,201 |
| 2023 | $1,006,025 | $588,680 |
| 2024 | $1,363,025 | $1,224,836 |
| 2025 | $1,225,720 | $2,457,761 |

Preschool's excess is one part of CL#6; the school turnback one part of CL#11. NOT checked: whether
"proof year 2025" is FY2025's close or the certification date. No MUNIS posting says "to free cash" —
the journal we hold has no fund-balance accounts; its year-end entries only cancel open orders.

**The cost side.**
- No budget line, account or org names preschool. "P.S." means PRIMARY SCHOOL, never preschool.
- That does NOT mean the preschool has no budget: its staff are most likely inside Primary School
  lines. The finding is that the budget does not SHOW what the preschool costs.
- IDEA preschool grants (262, 264, 298): $13,373 spent in FY2025.
- Staff the annual report's Primary School roster lists under "Pre-School": 2 classroom teachers
  and 4 paraprofessionals (FY2020, FY2021, FY2025). Their printed gross pay, our name match:
  FY2020 $234,348 · FY2021 $237,861 · FY2025 $278,946. Pay only — no benefits, no staff listed
  elsewhere who also work there, and no FTE or funding source (the grant may pay part of it, so the
  two are shown side by side, never added).
- How it runs (TJ): integrated into the Primary School; special education children mixed in with
  tuition-paying peers; children on education plans attend without tuition.
- Tuition rate is voted by the School Committee each year: FY2025 2-day $1,897.11, 4-day $3,548.58
  (minutes 7 Feb 2024); an increase was on the 21 Jan 2026 agenda.

**What would show the individual receipts:** the MUNIS account detail report for
0100-01001-431900 — deposits by date and description (memo). The revenue report we hold is a
summary: one line per account, no memo, no payee. If requested, family names must be masked.

---

## 6. DESE — chart of accounts

- We do NOT hold DESE's chart of accounts (three scripts already say so). Queued: fetch it and the
  End of Year Financial Report instructions, to settle whether DESE has a preschool / early
  childhood category and whether districts must report preschool spending.
- DESE function codes describe what money buys, not the grade (Lunenburg's account numbers carry
  them: 2310 teachers, 2330 paras, 4110 custodians).
- Lunenburg's own End of Year Report is still outstanding (TJ requested it).

---

## 7. Decisions waiting on TJ

1. **The Town's March 2026 MUNIS reports print a Town user's login and first name.** They are
   already in the public bucket and were never through the privacy gate. Take them down
   (`takedown.py`) or accept as a work login on a Town report?
2. Records requests to add: the special revenue fund-balance report at 30 June 2025; the account
   detail for 0100-01001-431900 (names masked).
3. Queue a "free cash" section on the Town general fund page (school receipts over estimate and the
   school turnback against CL#6 / CL#11)?
4. The preschool card could say "2 teachers, 4 paras" instead of "6 posts".

## 8. To restart

Open a fresh session and say: **"continue the FY breakdown handoff"**.

## Vocabulary from these two days

- **object constancy** — the same thing keeps its colour and place across views, so the eye follows
  the change, not a reshuffle.
- **graceful degradation / progressive enhancement** — the budget-against-actual page shows every
  year at the level its record supports; built from the base up, the journal years are the enhancement.
- **estimated receipts / local receipts** — the revenue side of a town budget.
- **conservative revenue estimating** — budgeting receipts low; the excess becomes free cash.
- **free cash** — the general fund's certified year-end surplus, spendable by Town Meeting vote.
