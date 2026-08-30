# Free cash: is Lunenburg hoarding, or rebuilding?

Two claims are being made about the same number.

- **That the town is too conservative** — sitting on money it could comfortably spend, and
  making the budget tighter than it needs to be.
- **That free cash is "not up to standard"**, so the town is in a rebuilding state and the
  balance is not available to spend down.

Both are testable. Neither is tested here, and the reason is worth stating before any
figure: **the data required to settle it is a ratio, and what we hold is a numerator.**

---

## What we now hold

The Division of Local Services publishes a Free Cash Proof for every community — the
year-end calculation, broken into its components. `sources/dls-free-cash/` holds it for
Lunenburg and eight comparable towns for 2021 to 2025, and
`sources/data/free-cash-proof.csv` is the extract.

It reconciles to itself twice over: the components sum to the total the sheet prints, and
each year's calculation equals the next year's opening figure. **81 checks across nine towns
and five years, all tie to the dollar.** `scripts/extract_free_cash.py` refuses to write
otherwise.

This closes `notes/DATA-WANTED.md` §5, which had been blocked because DLS sits behind bot
protection.

## Certified free cash, 2021 to 2025

| town | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| Ayer | 2,528,927 | 1,936,459 | 1,677,665 | 3,261,808 | 2,912,510 |
| Groton | 2,347,087 | 2,115,125 | 2,423,442 | 2,757,118 | 2,641,998 |
| Littleton | 9,428,814 | 9,458,083 | 10,108,103 | 12,317,002 | 11,317,633 |
| **Lunenburg** | **2,666,962** | **2,923,290** | **1,870,612** | **2,270,060** | **3,354,370** |
| Shirley | 706,703 | 532,074 | 515,190 | 518,752 | 272,197 |
| Townsend | 1,075,155 | 489,030 | 379,327 | 628,955 | 558,880 |
| Upton | 2,447,191 | 3,091,598 | 3,541,598 | 4,187,711 | 3,948,723 |
| Uxbridge | 5,394,393 | 4,481,807 | 1,628,312 | 5,622,785 | 3,869,693 |
| Westford | 5,323,393 | 6,199,092 | 5,870,108 | 5,653,000 | 6,201,595 |

**Do not read down this table.** These are absolute dollars for towns of very different
size, and nothing in the source carries a population, a budget or a levy. Littleton having
four times Lunenburg's balance is a fact about Littleton's size before it is a fact about
Littleton's policy.

What the table does support is reading **across**. Lunenburg's balance fell 36% between
2022 and 2023, and has risen every year since to its highest point in the five. Shirley
(−61% over the period) and Townsend (−48%) went the other way.

## The one ratio we can compute, and its limits

Free cash is certified as of 1 July, so the balance identified 1 July 2025 is what was
available at the **start of FY26** — which makes FY26's own budget the correct denominator.

For Lunenburg we hold that denominator: the Town Accountant's own year-to-date general fund
report, obtained by records request, showing a revised FY26 budget of **$51,531,199** across
67 departments. No enterprise funds are in it, which is what makes it the right base.

> **$3,354,370 certified ÷ $51,531,199 = 6.51%**

**We cannot compute this for any peer**, because we hold no equivalent budget figure for
them. So the ratio places Lunenburg against a standard; it does not place Lunenburg against
its neighbours.

**And we do not hold the standard.** The Town Manager's claim invokes one, and the honest
position is that we have not read it. Two documents would settle it and neither is in the
archive:

1. **Lunenburg's Financial Policies Manual, April 2024** — `DATA-WANTED.md` §9. A town's own
   policy normally sets its free cash target explicitly. If Lunenburg's manual sets a
   target, that number is the standard being referred to, and 6.51% either meets it or does
   not. This is the single document that would resolve the disagreement.
2. **DLS's own guidance on free cash levels.** It is commonly summarised as a percentage of
   the operating budget, but this project has not read the source and will not quote a
   threshold it cannot cite.

So: the arithmetic is done and the benchmark is missing. That is a one-document gap, not an
analytical one.

## What the composition shows, and this part does compare

A share has no size, so the make-up of each town's free cash can be compared even when the
totals cannot. The largest component in most years is money that was appropriated and never
spent.

**Unspent and unencumbered appropriations, as a share of identified free cash:**

| town | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| Ayer | 53% | 57% | 74% | 47% | 60% |
| Groton | 27% | 19% | 16% | 18% | 23% |
| Littleton | 39% | 23% | 26% | 28% | 33% |
| **Lunenburg** | **51%** | **24%** | **31%** | **60%** | **66%** |
| Shirley | 53% | 22% | 6% | 2% | 64% |
| Townsend | 43% | 55% | 25% | 36% | 64% |
| Upton | 52% | 40% | 33% | 29% | 22% |
| Uxbridge | 54% | 26% | 14% | 1% | 12% |
| Westford | 56% | 37% | 38% | 36% | 47% |

Lunenburg's 2025 proof in full:

```
 2,457,761  Unencumbered/unexpended appropriations (CL#11)
 1,225,720  Excess local receipts (CL#6)
   270,669  Prior year free cash not appropriated (CL#12)
   149,455  Excess cherry sheet receipts (CL#8)
    14,256  Other adjustments
     7,139  Revenue received but not estimated (CL#7)
  -170,954  Net change in adjustment to free cash
  -237,764  Outstanding receivables
 ─────────
 3,716,282  Identified free cash, 1 July 2025
 3,354,370  Certified
```

**Two thirds of Lunenburg's free cash in 2025 is money the town appropriated and did not
spend** — $2,457,761, against $1,225,720 from local receipts coming in above estimate. That
share has risen from 31% in 2023 to 60% and then 66%.

## What this does and does not establish

**It does not mean waste, and it is not the schools.** Every town turns money back;
departments do not spend to the penny, and a balance of zero would mean a town had budgeted
with no margin anywhere. The figure is town-wide across all 67 departments, not a school
figure, and nothing here apportions it.

**Uxbridge is the unusual one, not Lunenburg.** At 1% in 2024 and 12% in 2025, Uxbridge's
free cash comes almost entirely from revenue rather than underspending. Lunenburg at 60–66%
sits with Ayer, Shirley and Townsend.

**What it does establish** is the *shape* of Lunenburg's free cash, and the shape bears on
the argument. A balance built mainly from **underspending** is a different thing from one
built from **revenue outperformance**. The first says the operating budget is being set
above what departments use; the second says revenue is beating forecast. They imply
different remedies, and Lunenburg's is increasingly the first.

That is directly relevant to `budget-vs-actual.md`, which asks how far appropriations
diverge from spending and could only answer it for the school side, from restatements.

**What would settle the disagreement, in order:**

1. **Lunenburg's Financial Policies Manual (April 2024).** The target. One document.
2. **Operating budget or total general fund revenue for the eight peers**, so the ratio can
   be compared rather than just computed. DLS Schedule A would carry it —
   `DATA-WANTED.md` §6, also behind bot protection.
3. **Abington's free cash proof**, correctly exported. The file supplied under that name
   contains Lunenburg's data.
4. **The department-level detail behind the $2,457,761.** The proof gives a town-wide total
   and no breakdown. Which departments turned money back, and whether it is the same ones
   each year, is the difference between a structural pattern and a run of one-offs.

## How to reproduce

```
python3 scripts/extract_free_cash.py     # 81 reconciliations, all must tie
```

Sources in `sources/dls-free-cash/` with `PROVENANCE.md` beside them. The denominator is
`sources/data/town-ledger-fy26-q3.csv`, extracted by `scripts/extract_town_ledger.py`, which
reconciles to the report's own GRAND TOTAL before it will write.
