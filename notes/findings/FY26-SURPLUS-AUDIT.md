# The FY26 school surplus, read as an audit — 10 October 2026

The second pass over `/analysis/fy26-school-surplus` (unlisted), run with
`notes/process/AUDIT-PASS.md`. Unlike the transportation audit, **these findings are already
on the page**: `scripts/build_school_surplus.py --fy 2026` computes every figure below in
`fy26_audit()`, and `scripts/verify_school_surplus.py` recomputes each one by a different
route (Decimal, accounts keyed by org and object, workbook lines keyed by sheet row). This
note is a snapshot of what the audit found and why it was ranked as it was; the generator
is the source.

**Sources, all already readable by the generator (rule 13e).** `sources/data/munis-school-ytd.csv`
— the PUBLISHED spreadsheets of the period-13 MUNIS reports, FY2023 to FY2026, `gf-school`
(department 300, 415 accounts each year) and `special-school`; the private PDFs of the same
reports were not touched. `sources/data/munis-ledger.csv` for FY2026 period 12.
`sources/data/lps-budget-lines.csv` — the district's FY2027 workbook
(`budget-workbooks/fy27-proposals.xlsx`), read only as a budget, each line first tied to the
MUNIS FY2026 original appropriation of the accounts it is set against. School Committee
minutes of 5 November 2025 and 29 July 2026; Finance Committee minutes of 26 February 2026.

**What changed on the page.** The cards used to lead with inventory — where the surplus was
left, how much of it was discretionary, which function family held most. They now lead with
nine comparisons, ranked below; the salary offset and the period-12 comparison follow.
FY2025's report is unchanged and still passes its `--check`.

## The findings, ranked by the argument test

### 1. FY2027 budgets out-of-district tuition $502,629 below what FY2026 spent on the same lines

| line | account | FY26 voted | FY26 spent + committed | FY27 Balanced |
|---|---|---:|---:|---:|
| private | `0100-3-300-9300-51-1-06-2-535019` | $988,630.00 | $466,000.82 | $536,400.00 |
| collaborative | `0100-3-300-9400-51-1-06-2-535023` | $302,662.56 | $736,770.12 | $163,742.00 |
| both | | $1,291,292.56 | **$1,202,770.94** | **$700,142.00** |

The circuit breaker (fund 2640) paid $333,494.89 more in FY2026. The FY2027 figure is
identical in all four scenarios (workbook rows 225 and 227), so it is the district's
estimate, not a spring cut. *Hypotheses, none tested:* placements ending; a larger circuit
breaker share expected; FY2027 tuition prepaid out of FY2026 money (which would explain the
collaborative overrun AND the low FY2027 figure at once — the single most useful thing to
ask). *Who answers:* School Committee and Finance Committee, for FY2028. Largest dollars,
and the FY2028 line is being built now.

### 2. 57 accounts closed FY2026 $1,201,433.81 past their revised budgets; FY2025 closed with 4

| FY | accounts past revised | by | transfers in, gross | accounts spent to exactly $0 left |
|---|---:|---:|---:|---:|
| FY2023 | 70 | $753,697 | $590,339 | 26 |
| FY2024 | 52 | $1,167,996 | $486,257 | 23 |
| FY2025 | 4 | $22,275 | $1,463,210 | 91 |
| FY2026 | 57 | $1,201,434 | $394,929 | 29 |

The 29 July 2026 minutes list ten year-end transfers "needed to cover overages", totalling
$148,364.31 (parsed from the minutes, checked against the ledger: e.g. the HS special
education resource room teacher account `…2310-51-6-06-1-511001` shows −$81,075.96 to the
cent), and say more "may still be forthcoming". None posted between the 1 September and
6 October runs. Five accounts carry $811,010 of the overrun: collaborative tuition
(−$434,107.56), electricity (−$110,338.43), contract related services (−$100,520.05),
kindergarten aides `…2330-03-2-12-1-511103` (−$93,691.03, $0 voted, no transfer), HS
regular teachers (−$72,353.42). **FY2025 is the outlier, not FY2026**: 91 accounts closed
at exactly zero, against 23–29 in the other years. *Hypothesis:* a line-by-line
reconciliation after the FY2025 surplus became public. The school appropriation is a bottom
line, so this is not spending past the appropriation (said in the same card, rule 8).

### 3. FY2026 left $482,118; the FY2027 school budget was set $761,000 below level service

Workbook row 404: Level Service $27,333,288.00, Balanced $26,572,287.50. The floor is 63.4%
of the gap, the ceiling ($718,885.01) 94.5%. Not known together (budget set in March,
surplus measured in October). The lever is free cash, appropriated by Town Meeting —
stated, not urged. This is the comparison the community is already making (School
Committee minutes, 20 May 2026: "The combination of the surplus and the general difficulty
of selling an override").

### 4. Electricity and contracted therapy ran past their voted budgets in all four years, $489,283

| account | FY23 | FY24 | FY25 | FY26 | FY27 budget | FY26 paid |
|---|---:|---:|---:|---:|---:|---:|
| electricity `…4130-99-1-74-2-521011` | −$13,633 | −$105,732 | −$67,266 | −$116,471 | $316,250 | $319,108.72 |
| contract related services `…2310-51-1-06-2-535012` | −$14,197 | −$41,922 | −$27,042 | −$103,020 | $130,000 | $204,757.65 |

(voted minus spent and committed). Therapy was voted $103,000 in every year. Both FY2027
budgets are below what FY2026 had already PAID. Natural-gas heating beside electricity was
voted above its spending FY2024–FY2026 and received transfers in every year. Finance
Committee, 26 February 2026: a member "questions the impact of the solar panels". Also
found, not carded: regular substitutes are voted $58,000 a year across five lines
(`…2325-*-71-1-512103`) and FY2026 spent $108,912.60; FY2027 votes $58,000 again.

### 5. 20 accounts were given $117,626.28 by transfer and still ended $223,360.98 under

- Building contracted services `…4220-01-1-74-2-535006`: +$31,291.13, ended $75,660.20 under.
- School Committee dues `…1110-01-1-01-2-535003`: 5 November 2025 minutes, "transfer
  $13,500 from admin tech contracts to school committee dues, to cover superintendent search
  invoice". The line received $13,500.00, spent $6,311.00 of its original $6,500.00, closed
  with $13,689.00. Whatever paid the invoice, this line did not (or not yet).
- Heating `…4120-99-1-74-2-521025`: the 29 July minutes record "$11,000 from Heating Charges
  … to Regular Transportation"; the ledger shows heating **+$11,024.22 net**, so at least
  $22,024.22 went in from somewhere. Two measured things; the ledger is net per account.

### 6. The circuit breaker paid 61.9% of out-of-district tuition in FY2023 and 21.7% in FY2026

| FY | general fund | circuit breaker | both | CB share |
|---|---:|---:|---:|---:|
| FY2023 | $304,748 | $494,968 | $799,715 | 61.9% |
| FY2024 | $588,508 | $466,296 | $1,054,804 | 44.2% |
| FY2025 | $732,298 | $473,650 | $1,205,949 | 39.3% |
| FY2026 | $1,202,771 | $333,495 | $1,536,266 | 21.7% |

Rule 11 in one table: the general-fund line rose faster than the cost. Also: in FY2025 the
circuit breaker paid PRIVATE tuition (9300) $460,990 and collaborative $12,660; in FY2026
private $0 and collaborative $333,495 — the same flip the general-fund lines show.

### 7. Supplies were voted above their spending in all four years, $375,174.98

$37,694 / $71,669 / $172,966 / $92,846. Building upkeep's vote rose 96.4%, $332,016 →
$652,033, and FY2026 spent $156,984 less than voted. This is the measured version of the
7 October 2026 recording's "we were thrifty" (captions, not a record): a line under its vote
every year reads as budgeted high as much as run lean.

### 8. Lines budgeted again

The primary-school psychologist line `…2800-07-2-06-1-511023` was voted $98,784 and paid
$0; FY2027 budgets it $102,227 (row 359). The kindergarten aide lines spent $99,064.15
against $0, no transfer, and FY2027 Balanced budgets $0 (rows 332–333; only the Core
scenario restored one aide).

## Credit where the ledger shows it

- Special-education aides: five lines ran $111,018 past revised budgets in FY2026 and spent
  $1,526,466.69; FY2027 budgets $1,823,788, **$297,321 above** what FY2026 paid.
- Health insurance `…5200-99-1-99-2-570001`: $328,770.72 past its budget across FY2023–FY2024;
  FY2026 closed $78,313.35 under, 2.1%.
- The year-end transfers were voted in open session and itemised, one by one, with reasons.
- Regular-route transportation closed at exactly $0 after its transfer (see the
  transportation audit).

## The three cheap sheet checks

- **Identical figures in paired rows.** The workbook budgets the middle- and high-school
  psychologists at $45,106 each and three social workers at $92,939 each; MUNIS shows the
  MS and HS psychologist lines spending $45,305.97 and $45,306.03, and in FY2025 $43,571
  each. Allocations of one salary, probably; per-school figures are not measurements.
- **A printed total that does not foot.** The workbook's TOTAL ACTUALS & BUDGET row is $2
  below the sum of its printed expense and salary subtotals in both the FY2026 and FY2027
  columns. Immaterial; noted.
- **A cheaper year under an escalating contract.** Teachers & substitutes spent
  $10,840,407 in FY2025 and $10,841,411 in FY2026 (+$1,004). *Hypothesis:* the FY2026
  approved budget's position cuts, turnover to lower steps, leaves. Not carded.

## Said against did — finding aids only, not on the page

Machine captions locate a moment; none of these may be quoted as a figure.
School Committee 24 June 2026 [1:32:54] (a member praising a spending rate);
15 April 2026 [0:56:01] ("We don't want another surplus"); 4 February 2026 forum [0:02:05]
(a typical surplus of "$100,000 and $200,000" — the ledger shows $106,827 for FY2023 and
$215,776 for FY2024, consistent). Each needs checking at the video.

## Corrections to the page as it stood (loudly)

1. **"4 of 4 special-education paraprofessional lines ended over … $105,644" was wrong.**
   There are five: the ACE program's `S2511131` ("PARAPROFESSIONALS", $43,742 voted — the
   workbook's "ACE Special Ed Paraprofessionals", and named in the 29 July minutes) was
   left out of `SPED_PARA_ORGS`. Five of five, $111,018, transfers into four.
2. **The transportation quote was set beside the wrong line.** "Regular transportation had
   been budgeted too low" sat under a category overrun of $67,555 that is entirely the
   special-education line; regular routes closed at $0. The quote now carries that note,
   and the generator asserts it.
3. **"Not one of the 415 accounts changed"** — only 258 accounts are in both runs; the
   other 157 are empty at period 13. Now says 258.
4. *Not wrong, but masking:* the "years under" history measures against the REVISED budget,
   which hides chronic under-voting — contracted therapy shows "under in 2 of 4" against
   revised and ran past its VOTED budget in all four. Findings 4 and 7 measure against the
   vote.

**Outside this report, found on the way:** `sources/data/budget-seasons/fy27.csv` gives
level service as "$27,333,289" and the gap as "$761,001"; the 23 March 2026 projection it
cites prints $27,333,288, a $761,000 gap. And `fy26-closeout.md` §8 says this project holds
one year at account level; FY2023–FY2026 are now held, which is exactly what §8 asked for.

## Gaps registered in `money-gaps.csv` (rule 7c)

- Whether the 57 accounts past their revised budgets will be covered, and from which lines
  — *closes:* the posted FY2026 year-end transfer schedule with its votes.
- What the FY2027 tuition budget assumes — *closes:* the FY2027 tuition worksheet and the
  service period of every FY2026 tuition invoice.
- Where each FY2026 transfer came from and went to (heating, the search invoice) —
  *closes:* the MUNIS budget transfer report, gross, with counterparties.
- Why electricity runs past its vote every year — *closes:* utility bills by building and
  month, with kWh and solar credit.

Already registered and cited rather than duplicated: the open encumbrances (row 215),
counselor and psychologist vacancies (219), private against collaborative tuition (220),
the circuit breaker balance (224), lines spending against a $0 budget (227).
