# Transportation, read as an audit — 10 October 2026

The second pass over `/analysis/transportation`, run with `notes/process/AUDIT-PASS.md`.
**Nothing here is on the page yet.** Every figure was computed in this session from the
sources named; none is typed from the page. Before any of it ships it goes through
`build_transportation.py` and `verify_transportation.py` like every other figure (rule 2,
rule 9).

**Sources.** General fund school lines: `build_transportation.load_ledger()` — MUNIS
period 13 FY2023–FY2026, the Finance Committee ledger history before (tied to MUNIS to the
dollar in FY2023–24). Funds 1301 and 1308: `sources/data/munis-school-ytd.csv`, period 13,
`ytd_expended + encumbrances`. Accounts:

- regular routes `0100-3-300-3300-99-1-69-2-535025`
- special education `0100-3-300-3300-99-1-69-2-535026`
- athletic `0100-3-300-3510-06-6-67-2-535016`
- athletic fee fund: every row of fund `1301`
- bus fee candidate: `1308-3-300-0000-00-0-00-4-437601` `SCH. CHOICE BUS FEE`

## The findings, ranked by the argument test

### 1. Special education transportation closed FY2026 $67,556 over budget, uncovered

Voted $565,734, revised $565,735.26, spent $620,025.37 + $13,265.28 committed = $633,290.65.
`available_budget` = −$67,555.39. No transfer covered it. **FY2027 is budgeted at $649,953 —
$16,662 above what FY2026 spent**, on a line whose spending rose 45.6% from FY2025 to
FY2026. *Who answers:* School Committee (line authority), Finance Committee (FY2028).

### 2. The same line was budgeted far ABOVE its spending for years, then cut, then overran

| | |
|---|---|
| FY2016–FY2023 | under its voted budget every year, by $8,538 to $223,308 |
| FY2017–FY2019 alone (before the closures) | $348,067 under |
| FY2017–FY2022 | $747,316 under |
| FY2022 budget | $297,843, the lowest since FY2012 |
| FY2024, FY2026 | over, by $65,455 and $67,557 |

**What it shows:** the budget lagged the spending in both directions. **What it does not
show:** why. A budget set from the prior year's actual would produce this shape; so would
placements arriving and leaving between budget and year. *Hypothesis, untested.* What would
settle it: the van contract and a count of routes by year (both already registered gaps).

### 3. FY2027's school-day buses rise 11.2%; zeroing athletic buses hid most of it

School-day lines voted $1,531,234 (FY2026) → $1,703,313 (FY2027), +$172,079.
All transportation $1,662,784 → $1,703,313, **+2.4%**. The $127,550 athletic cut equals 74%
of the school-day rise. A reader seeing "+2.4%" sees a quiet line. It is not.

### 4. The FY2027 plan puts 83% of restored athletic buses back on the fee fund

Superintendent, 26 August 2026: $58,880, rounded to $60,000 — $10,000 town, $50,000 athletic
revolving. A School Committee member, 12 March 2025, on moving buses to the town line:
*"corrected from past practice that was done incorrectly."* In FY2024, the year before the
correction, the town line was $40,000 of the $117,555 the district's sheet states (34%).
The FY2027 plan's town share is 17%. **Measured both; the page should show both and ask
which policy holds.**

### 5. "The athletic revolving can not support these costs" — the fund's own ledger

| FY | fund 1301 receipts | spending | receipts − spending |
|---|---:|---:|---:|
| FY2023 | $144,949.68 | $314,863.84 | −$169,914.16 |
| FY2024 | $135,765.36 | $250,574.63 | −$114,809.27 |
| FY2025 | $131,481.37 | $32,796.47 | +$98,684.90 |
| FY2026 | $188,944.46 | $146,911.44 | +$42,033.02 |

The district's statement (FY2026 overview, early 2025) fits FY2023–24: $284,723 more out
than in. FY2025's surplus came **after** costs were reclassified out of the fund onto the
town line — the FY2025 salaries account `1301-…-3510-06-…-519999` is NEGATIVE, −$5,337,
which is what a reclass looks like. Two years later the fund is $140,718 to the good, and
FY2027 draws $50,000 from it. **Say all three in one card.** Not established: the balance —
nothing held states it after 30 June 2020 ($98,376.41, `fund-balances-fincom.csv`), so
whether the fund ran below zero in FY2024 is unknown. Register it.

**And one thing to ask:** in FY2026 the town line paid $110,650 for athletic buses, while the
fund's HS purchase-of-service account (`…3510-06-…-531006`, where buses used to be charged)
spent $113,602 — about what it spent in FY2024 ($115,994) when it still carried most of the
buses. What it bought in FY2026 is not itemised. *Hypotheses, all fitting:* officials and ice
time rose; some buses are still charged to the fund; reclassification timing. Register it.

### 6. The bus fee did not lower what the town paid for buses

FY2026 regular routes: voted $965,500 (the contract less $11,000 "for the fee"), +$11,000
transferred in, spent $976,500 — **the full contract price, from the general fund.** The
candidate fee account took in $50,628.44 (FY2025) and $52,717.04 (FY2026), $103,345.48.
Fund 1308 has **no account coded to transportation and no transfer out** in any of FY2023–26.
**Measured:** the general fund paid the whole contract. **Hypothesis:** the 1308 receipts are
the fees. Either way the fee's effect on the town's bus bill, on this ledger, is $0. That
is the contentious card; it is a question for the School Committee, not a charge.

### 7. FY2024: both school-day lines closed $112,490 past their revised budgets

Regular −$49,925 (after a +$28,800 transfer), special education −$62,565.22. And FY2024's
regular routes ($917,525) cost **more than FY2025's whole year** ($907,200) under the same
contract, which only escalates. Something extra was in FY2024. Not established what; the
old contract would say (a Finance Committee member asked for it on 14 March 2024).

### 8. The contract outruns the model

Contract: +7.9% into FY2027, +7.4% into FY2028 ($1,131,390, fixed). `model/finance.py`
grows `transport` at 6%: $1,116,562 for FY2028, **$14,828 under a price already signed.**
Small, but rule 4 and rule 6 both say a contracted rate beats a default. *This one changes
an assumption, so under rule 8 it reaches the app.* Note special education transport
($649,953) is not in that bucket; it rides `sped` at the sped rate.

### 9. The two district sheets disagree by 28% on the same sports

FY2024, the 24 sports both sheets print: by-sport workbook $113,765.50, Finance Committee copy
$81,553.00. The page's second card (*"the cost was already there"*, $117,555 against a $40,000
line) rests on the higher sheet without saying so. On the lower one the cost was ~2x the line,
not ~3x. **The current card must carry the spread** (rule 13a: publish the spread, never pick).

Also: paired sports carry identical figures in both years (Boys/Girls CC, Indoor Track,
Outdoor Track; MS Basketball in FY2025) — one bus split in half, so per-sport figures are
allocations. And FY2025 spring prints $0.00 for its season total while its rows sum to
$18,242.50, down 46% on FY2024; spring is 59% of the whole FY2024→FY2025 fall. *Hypothesis:*
the FY2025 spring section was unfinished when the sheet was made.

### 10. The FY2027 restoration estimate is tight

$58,880 for HS buses against $81,067 of HS buses in FY2025 on the district's sheet, at prices
that have since risen (trip rate $6.50 → $6.65 a mile, waiting $130 → $140 an hour). The
Superintendent's reasons — closer competitions, more home games, real schedules — are on the
record and the page should quote them. If the estimate is short, the overrun lands on the fee
fund or the town line. A comparison, not a forecast.

## Credit where the ledger shows it

Regular routes now run on a fixed-price contract and the FY2027 budget carries its price to
the dollar. FY2025 and FY2026 spent the line exactly. That is the one transportation line a
board can plan to the dollar three years out, and it was not true before FY2026.

## Gaps to register in `money-gaps.csv` (rule 7c)

- The athletic fee fund's balance at each 30 June, FY2021–FY2026 — *closes:* fund 1301
  balance sheet from the Town Accountant.
- What fund 1301's purchase of service bought in FY2026 — *closes:* the fund's AP detail.
- What made FY2024 regular routes cost more than FY2025's contract year — *closes:* the
  FY2021–FY2025 Dee Bus contract (already requested 9 October 2026).

## Proposed short version (draft, every figure to be generated)

1. **Special education buses closed FY2026 $67,556 over budget; FY2027's is $16,662 above that year's spending.**
2. **For six years that line was budgeted $747,316 above what it spent; then it was cut, and overran.**
3. **School-day buses rise 11.2% in FY2027; cutting athletic buses made the total look like +2.4%.**
4. **The bus fee left the town's bus bill unchanged: the general fund paid the full $976,500 contract.**
5. **FY2027 puts 83% of restored athletic buses back on families' fee fund — the practice called "incorrect" in 2025.**
6. **The fee fund "could not support" buses after a $284,723 two-year deficit; since they moved off it, it is $140,718 ahead.**
7. **The bus contract rises 7.4% into FY2028, already signed; the town's model assumes 6%.**
8. **The district's two athletic bus sheets differ by 28% on the same FY2024 sports.**

Cards 1, 3 and 7 are planning; 2, 4, 5, 6 and 8 are the contentious ones, each written as
two measured things side by side.
