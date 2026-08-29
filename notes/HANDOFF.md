# Handoff

Written 29 August 2026 to survive a context reset. Read `CLAUDE.md` first — it has twelve
rules now, and every one exists because it was broken here.

---

## 1. Where everything is

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org`, tag **`v3`** = `79b194c` |
| **`main`** | `ab3142e`, pushed. **14 commits ahead of what is deployed.** |
| **Live headline** | $634,068. FY28 gap $680,870. Unchanged since v3. |
| `v2` | `e5332e6` — the archive build |
| `v1` | `a0051c9` — before the archive existed |

Deploy needs **Node 22 via nvm**. Verify by hashing a document from production against
`sources/` using curl with a browser user-agent (the domain 403s otherwise).

**Nothing since v3 is deployed.** That includes everything below.

---

## 2. THE ONE THING THAT MATTERS MOST

**There is a live error in the deployed app. The athletics fee analysis counts fees twice.**

`model/athletics.py` asserts `FEE_REVENUE_IN_BUDGET = False`, on the reasoning that fees
flow through revolving accounts so the budget figures are gross. **That is backwards.**

Proof, from two documents that agree:

- In the general fund, `ATHLETIC OFFICIALS` and `REPLACEMENT OF UNIFORMS` are budgeted
  **$0** from FY26 on. They used to be funded ($1,510 and $12,672 in FY22).
- The athletics revolving fund — entirely fee-funded — pays **ArbiterSports $59,400**
  (officials) and **Prime Time Sports $25,421** (uniforms), inside $113,602 of purchase of
  service, plus $30,514 of salaries for four staff.

The same costs left one pot and arrived in the other. So `PROGRAM_TOTAL_ADOPTED = 217,908`
**excludes $146,911 of fee-funded athletics spending**, and the app then asks what fee
would cover $345,458 — while today's fee already covers $146,911 that is not in that
number.

**Consequences, all published and all wrong to some degree:** the $960 self-funding fee,
peak revenue $358,380, "fees cover 54%", and conclusion 5 ("athletics cannot pay for itself
once you put the buses back"). Gross athletics is about **$364,819** (general fund $217,908
+ revolving $146,911) and fees already pay ~40% of it.

**Not yet fixed.** Fixing it means rebuilding the fee curve on a gross base, and gross has
to be established first — $146,911 is a floor, not the answer. This is the highest-priority
item in the project.

---

## 3. The rule that generated that finding, and generalises well beyond it

**Rule 11 — a budget line is NET, and is not what the thing costs.** If paras cost $1.5M
and the state gives $500,000, the line says $1M. Nothing marks it as net.

The district does this deliberately. In `fy27-proposals.xlsx`, comments column, beside
General Education Transportation: *"Does this reflect a reduction of $50K to accound for
the money planned to come from the busing fees?"*

So a line can rise because the thing got more expensive, because a grant stopped covering
part of it, or because a fee stopped being collected — **and all three look identical**. A
rate measured off a net line is a rate of change in the **town's share**, not in the cost.
Above all of it sits Chapter 70, $11.4M of a $26.6M budget, set in the Governor's budget.

**Rule 12 — every source carries its address, its filename and our copy.** The direct link
to the file, not the index page. The publisher's own name for it, because links die. Our
downloadable copy. `build_source_index.py` now fails any source link that points at an
index rather than a document.

---

## 4. Budget versus actuals — what the sweep found

`sources/analyses/budget-vs-actual.md`, six findings, all rebuilt on five to six years.
`scripts/analyze_variance.py` is the sweep; `/data/variance-by-group.csv` is its output.

**548 usable line-years, 141 lines, FY18–FY23, covering 93–97% of the budget (82% in
FY23).** All 3,255 exclusions have a stated reason.

- **The whole budget is quiet**: −0.42%, −0.22%, −0.92%, −0.65%, **+0.53%**. Never 1% off.
- **Salaries −0.86%, everything else +0.87%.** They nearly cancel.
- **Almost nothing misses the same way twice.** Of groups with 4+ years, exactly one is
  over every year and one under. At line level, 7 of 141. **There is no systematic padding
  in this budget** — the most important finding, and a negative one.
- **What there is instead is drift** — 27 groups moved materially first-two-years to
  last-two.
- **The clearest case**: `COMPUTERS — Purchase & Lease` budgeted at $39,000 while spending
  ran $165,107 and $186,722 (+141%, +323%, +379%) — **and the FY26 budget is $243,450.**
  A line that drifted and was corrected, like athletics coaching in §4.
- **Health insurance is the one that matters to the gap**: +$293,023, on the only line big
  enough to move a projection, and drifting upward.
- **FY21 is not a usable year** — 117 of 120 lines have "actual" identical to budget. The
  books were not closed. Excluded everywhere.
- **The documents disagree with themselves** four times, up to $89,087 and 1.49% — larger
  than the effect being measured. That bounds everything.

**"The town spends less than it votes, every year" does not survive.** FY20 −0.34%, FY23
**+0.50%**. And FY25's figure is unresolvable: three published salary totals and two
expense totals give six possible budgets. The town's own minutes settle it at
**$603,885.97** (School Committee, 17 September 2025) — that is the figure to quote.

---

## 5. Special education — deployed as v3, and where it stands

Rate is **6.49%**, every component measured rather than assumed:

| component | share | rate | measured over | fit |
|---|---:|---:|---:|---:|
| Professional staff | 54% | 2.67% | 8 budgets | R² 0.84 |
| Paras | 33% | 12.78% | 10 budgets | R² 0.89 |
| Transport | 12% | 5.69% | 9 budgets | R² 0.33 |

Out-of-district tuition is **held flat**, and that decision is corroborated three ways from
sources with nothing in common — eleven budgets (R² 0.10), five years of actuals (+27% to
−51%), and the private/collaborative split (60–300% misses in opposite directions). That
corroboration is now shown in the app.

**The rate changed four times in a day: 2.48% → 5.89% → 2.57% → 6.80% → 6.49%.** Every
version and its error is on the page. Do not "restore" an earlier one.

**The para question, still open.** Paras grew 3.98%/yr in headcount and 9.07%/yr in actual
spending — 4.90%/yr more per para against a 2% contract. Ruled out: grants (the town ledger
shows special education grants paid only $89,184 of salaries in nine months, ~6% of the
line), double-booking (FY25 only), and a funding handover (the town's share of the function
group is 78% in FY17 and 78% in FY25). **What remains is hours, classification or steps,
and nothing published separates them.** Note rule 11: 9.07% is growth in the town's share.

---

## 6. Grants — ESSER was the whole of what was lost

From the FY25 Superintendent's Budget Update, *Grants History* pages, and two other decks.
`/data/grants-history.csv`, every row carrying its document, page, the district's link, our
copy and the hash.

| FY | ordinary grants | ESSER |
|---|---:|---:|
| 2020 | $880,187 | — |
| 2021 | $903,695 | — |
| 2022 | $1,570,185 | — |
| 2023 | $1,444,927 | $588,834 |
| 2024 | $1,136,408 | — |
| FY21–24 | | **$2,137,941** |

**Ordinary grants never collapsed.** Special education grants are flat at $432,335–$520,845.
ESSER was $2,137,941 across four years, on top, then nothing — about half a million a year.

**Coverage caveat that must travel with this table:** the FY25 deck supplies 67 of 79 rows
and is the only consistent series. FY22 and FY23 read high because other decks add grants
the retrospective omits. FY22→FY24 looks like a $434k fall; much of that is coverage.

---

## 7. Athletic transportation — the thread that was live at the reset

General fund, function **3510 Athletic Expenses** (not 3300). Actuals are recorded in MUNIS
like any other general fund line, and we have them:

| FY | budget | actual |
|---|---:|---:|
| FY23 | 40,000 | 39,880 |
| FY24 | 40,000 | **40,000 exactly** |
| FY25 | 40,000 | **87,822** |
| FY26 | 127,550 | $47,847 spent + $13,169 encumbered at Q3 |
| FY27 adopted | **0** | cut |

Two things unresolved: **FY24's actual is exactly the budget**, which real bus charters do
not do; and the district's own workbook comment on that row says *"Actuals in munis are
tracking well below FY26 budget, can FY27 be reduced? Yes, level funded"* — so the
$127,550 the app uses as the cost of putting buses back may be too high.

The revolving fund does **not** pay for athletic transportation — its $109,503 of named
vendors are officials, uniforms, video, race days and co-op fees, no bus company.

---

## 8. Claims that are NOT established — do not restate as fact

| tempting | actually established |
|---|---|
| The town gives back money every year | Two clean years: one −0.34%, one **+0.50%** |
| Grants drying up drove the para line | Ruled out. Town's share 78% → 78% |
| The para line measures staffing | It measures the town's share of staffing (rule 11) |
| The state is squeezing the district | Ordinary grants flat; ESSER was federal and scheduled |
| Athletics costs $345,458 | That excludes $146,911 the fees already pay |
| The district cannot budget | Almost nothing misses the same way twice |

---

## 9. Data and scripts added this session

**Data** — all catalogued, all under `/data/`:
`line-history.csv` (19,453 readings, 417 lines), `variance-by-group.csv`,
`grants-history.csv`, `school-special-revenue-fy26-q3.csv`, `town-ledger-fy26-q3.csv`,
`total-salaries-history.csv`, `total-expenses-history.csv`, `sped-para-history.csv`,
`sped-teacher-history.csv`, `sped-transport-history.csv`, `ood-tuition-history.csv`,
`sped-lines.csv`, `link-status.csv`, `dese/district-spending-categories.csv`.

**Scripts**

    python3 scripts/audit_provenance.py          # no projection reads actuals
    python3 scripts/backtest_rates.py            # assumptions vs later budgets
    python3 scripts/verify_sped_analysis.py      # every figure in the SPED analysis
    python3 scripts/verify_budget_vs_actual.py   # every figure in the actuals analysis
    python3 scripts/build_source_index.py        # catalogue; fails on index-page links
    python3 scripts/analyze_variance.py          # the whole-budget sweep
    python3 scripts/extract_line_history.py      # every line, budget and actual
    python3 scripts/extract_budget_history.py    # named series and district totals
    python3 scripts/extract_grants.py            # grants by name
    python3 scripts/extract_special_revenue.py   # school funds outside the appropriation
    python3 scripts/extract_town_ledger.py       # the Town Accountant's ledger
    python3 scripts/check_source_links.py        # whether publisher copies still open
    python3 model/export.py                      # after ANY model/ change
    python3 scripts/build_agent_endpoints.py     # llms.txt and /data/*

**Run the verifiers before any commit touching an analysis.** They have caught stale prose
six times, including a risk table $200,245 out and two figures I typed rather than derived.

---

## 10. Records-request documents — three of fourteen used

Used: `town-general-fund-expenditures-fy26-q3.pdf`, `town-special-revenue-fy26-q3.xlsx`,
`school-funds-fy26.xlsx`.

**Not yet opened**: `town-general-fund-revenue-fy26-q3.pdf`, `town-trust-agency-fy26-q3.xlsx`
(stabilisation and reserves — bears on the override argument), `fincom-memo-fy26-q3.docx`,
`fincom-deck-fy26-q3.pptx`.

Not school-related: the four enterprise funds (sewer, water, solid waste, PEG).

**And the workbook's comments column (S) is 351 rows of district commentary that has not
been read systematically.** It is where the transportation netting question and the "can
FY27 be reduced?" note came from. It is the single richest unread source held.

---

## 11. What to do next, in order

1. **Fix the athletics fee double-count** (§2). It is live and wrong.
2. **Read the workbook comments column** (§10). Cheap, and already produced two findings.
3. **Deploy or don't** — 14 commits are ahead of production, including the corroboration
   block and every budget-versus-actual finding. Nothing in them changes a projection.
4. **The para question** (§5) needs DESE's End of Year Financial Report, which is a filing
   and not downloadable — see `notes/DATA-WANTED.md` §3b for who to ask.
5. **FY26 year-end** settles athletic transportation, the circuit breaker, and the tuition
   line at once.

---

## 12. How to work with TJ

He will ask for a full analysis and mean it. Ranking by one measure and reporting the top
few is not a sweep — that method missed athletics entirely and he caught it. State coverage
alongside findings, always, so he can see what was not looked at. When a finding is
surprising, check it harder rather than reporting it faster: the 52%→84% "handover" was
wrong and was the most interesting thing said all day. And say "paras", not "aides".
