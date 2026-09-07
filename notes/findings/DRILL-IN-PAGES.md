# The drill-in analysis pages — what each one established, and what it did not

Written 7 September 2026, while the pages were being built, because the reasoning
behind a figure is the part that does not survive in the figure.

Each section below is a page under **The Money**. For each: the route, the findings
with the query that produced them, and — the part worth keeping — **what the page
deliberately does not claim**, and why. Rule 7 says a measurement is a fact and an
explanation for it is a hypothesis; most of the value in this document is in the
second half of each section, which is the half that gets lost.

The pages themselves type no figures. Everything here was recomputed against
`sources/data/lunenburg.db` at the time of writing; where a figure is quoted below
it is quoted **with the query**, so a reader can re-run it rather than trust it.

---

## 1. `/money-outside-the-budget` — the special revenue funds

**Commit** `308becb`. **Data**: `special_revenue_read`, 13 consecutive editions
(FY2011–FY2023), 1,882 rows, transcribed from rendered pages of the annual town
reports rather than OCR'd.

### What the data shows

```
carried  FY2011  $2,766,955  ->  FY2023  $10,031,100     = 3.6x
surplus in 12 of 13 years; the sole deficit is FY2012, -$704,333
```

- **34% of what is held is pandemic-era money** — eight named funds holding
  `$3,377,339` of `$10,031,100` in FY23, and **zero of it before FY20**. That is a
  cliff with a date on it, and it is the single most consequential number on the
  page: a third of the balance is money that arrived for a reason that has ended.
- **Most of it is not school money.** Five enterprise funds hold `$3,800,195`
  (38%); the school department holds `$1,753,708` (17%). The enterprise funds sit
  *inside* this schedule, so ratepayer money and school grant money are added
  together in the printed grand total. The page says this out loud, because it
  lives under The Money and a reader will otherwise assume schools.
- **FY23 was the first year since FY17 the school funds spent more than they took
  in** — receipts `$3,667,636` against disbursements `$4,333,280`.

### What it does not show

- **Not one dollar of this is traceable to a purpose.** The schedule is receipts,
  disbursements and balance per fund. What any fund *bought* is not in it.
- **A balance is not slack.** Several of these funds are legally restricted to the
  purpose that created them. A resident reading "$10M held" and hearing "$10M
  available" is the misreading this page most has to prevent.
- **The 3.6× is nominal.** No deflator is applied and none should be inferred.

### Chart detail worth keeping

The biggest-movers panels **share one denominator**. Drawn independently, an $85k
fall rendered the same length as an $893k rise — a chart that made a small thing
look like a big one. Any two panels a reader will compare must share a scale.

---

## 2. `/what-sports-cost` — athletics, both sides

**Commit** `3c7af74`. **Data**: `athletics_history` (town appropriation),
`athletics_by_sport` (the district's own sport-by-sport workbook),
`fund_1301_cash_journal` (the revolving fund's cashbook),
`athletic_fee_schedule`.

This page exists because athletics is the **only** part of school money where both
sides can be seen at once — an appropriation, and an independent statement of what
the same categories cost. That is why it carries weight far beyond its 1.7% of
spending: it is the control case for whether a budget line can be read as a cost.

### What the data shows

| | |
|---|---|
| FY2024 | town lines `$124,301` vs workbook `$351,642.89` on comparable categories — **35%** |
| FY2025 | transportation cost `$91,066`, line `$87,822` — 3.6% short, was **66%** in FY24 |
| FY2025 | **`$254,121.18` of `$390,299.87`** into fund 1301 was four `GEN` journal entries |
| FY24–26 | participations **−3.9%** (675 → 649) while the HS first-child fee rose **30%** |

**The journal-entry finding is the one to read twice**, and it reconciles exactly:

```sql
SELECT src, COUNT(*), ROUND(SUM(amount),2)
FROM fund_1301_cash_journal WHERE fy=2025 GROUP BY src;
--  GEN   4   254121.18
--  CRP  44   131481.37
--  SOY   1    33993.31   <- opening balance, not a receipt
--  GRV   3   -22582.82
--  PRJ  19  -124895.03
--  APP  21  -140878.92
```

`33,993.31 + 390,299.87 − 293,054.09 = 131,239.09`, which is FY2026's opening
balance — so the arithmetic closes against the next year's own printed figure
rather than against itself. Strike the four `GEN` entries and the fund closes
FY2025 at **−$122,882.09**. They are described in the ledger only as *per memo*.
**Two thirds of the year's inflow is a document we do not hold.** Registered as a
gap naming the five memos as what would close it.

### What it does not show

- **The fee did not necessarily move the participation.** Those are two
  measurements printed side by side with nothing joining them. Fees rose over
  exactly the years participation fell; that is a coincidence in time, and this
  data cannot promote it to a cause. Anyone quoting the pair as cause and effect
  is quoting the page wrong.
- **Participations are not children.** The workbook counts participations, and one
  child playing three sports is three of them. Some rows are *negative* —
  out-of-district athletes subtracted back out — so a season total is a net figure
  and not a headcount of bodies. How many children play sports is a registered gap;
  an unduplicated athlete roster would close it.
- **Whether the general fund athletics line is net of the revolving fund is
  unknown** (rule 11). Registered, closes with the `Account_Detail` export for orgs
  S3066672 / S3066671.
- **What the four `ADJ EXP` entries moved is unknown.** Not "probably a transfer" —
  unknown.

### It disagrees with the published analysis, on the page

Three places, rendered as a disagreement with which is which, not reconciled:

| | page | `athletics.md` |
|---|---|---|
| FY2024 general fund athletics | `$285,281` | `$314,319` (§7) |
| share of workbook cost covered, FY2024 | 35.35% | 44% (§5, `athletics-ledger.md`) |
| middle-school blended rate | `$224.78`, under the top tier | reported unresolved (§8) |

The first two are the same cause: commit `07aa298` withdrew three FY2024 rows
(Freshman & MS Coaches, Unified Sports Coach, Replacement of Uniforms) when it
fixed a column mapping, and the analysis predates that. The third closed because
`athletic_fee_schedule` now carries the $275 MS rate from School Committee minutes
of 26 Feb 2025.

**Rendering the disagreement was deliberate.** The analysis has a sha256 and a
published PDF. Silently agreeing with it would have been a derived thing quoted as
observed — rule 13, on our own prior work.

---

## 3. Rule-2 drift caught by a verifier, and why it survived every read-through

`verify_athletics.py` had been failing on two figures since a reclassification:

```
| `forward`   | proposed, requested, level service, balanced | 176 |  ->  172
| `narrative` | money discussed, no figure table             |  98 |  ->   75
```

Fixed in `05fae33`. The instructive part is **why nobody saw it**: the same table's
`ledger` (10) and `restatement` (65) counts still reproduced. Two of four figures
in one table were right, which made the table look computed. A figure typed beside
figures that are derived inherits their credibility and none of their maintenance.

That is the general shape of nearly every defect in this project — a derived thing
written down, the thing it derived from moved, and nothing connected the two —
and it is the argument for `check_generated.py` existing at all.

---

## 4. Open threads at the time of writing

- **State aid** and **free cash** pages in progress. For free cash the material is
  `free_cash_proof` — 630 rows of DLS proof workbooks covering peer towns, with a
  cross-foot that should tie components to the certified figure. If it ties, a
  resident can be shown the arithmetic that brings free cash into existence rather
  than told a number. `CL#6` / `CL#8` / `CL#11` decompose it into three different
  stories — conservative revenue estimating, aid surprises, and money appropriated
  and not spent — and **which one dominates is probably the most useful sentence
  that page could carry.**
- **The D1 push is held** by the site owner. `sync_d1.py --check` fails for that
  reason and only that reason; every other generator reproduces.
- **Still genuinely unread**: the FY2024/FY2025 combining balance sheets (~80 rows,
  with a $102,000 printed defect already located in FY2024), and the PEG
  revenue-vs-expenses statements (~11 editions, with a real cross-check).
- **FY2023 balance sheet** is transcribed and refused; the `$87,293.86` cross-check
  gap is open.
- **`sped_para_history` sign defect** is fixed. Parenthesised negatives were being
  eaten, and FY2024 was wrong by `$315,772` — twice the line, because the sign
  error doubles rather than zeroes. Other extracts may warrant the same audit; that
  audit has not been done.

---

## 5. The pattern these pages follow, and why

Set by the site owner: **insights / conclusions, then organised categorical data,
then raw data and context.** Now written down as CLAUDE.md rule 7b.

It is the shape a resident reads, and it is the opposite of the shape the data
arrives in — which is why it has to be a rule rather than an instinct. Everything
above the fold in a page's first draft got there because it seemed necessary
*before* the reader could understand what follows: true for the author, who has
just spent an hour on the caveats, and false for the reader, who came for a table.

Three years is a trend **here**. The boards in this town will not project two years
out, so a three-year series is more forward visibility than they currently use.
Plot it, and state the span on the chart so nobody mistakes three years for fifteen.
The general rule that replaces "short series are weak": judge a series against what
the reader currently has, not against what a statistician would want.
