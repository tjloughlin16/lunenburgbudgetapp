# Handoff

Written 28 August 2026, to survive a context reset. Read `CLAUDE.md` first — it holds the
ten rules, and every one of them exists because it was broken here.

---

## 1. Where everything is right now

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org`, asset `index-CyEVczOb.js`, built from tag **`v2`** |
| **`main`** | `d9ec52c` — identical to `v2`. Pushed. |
| **Working branch** | **`sped-curve`**, 10 commits ahead of `v2`. Never deployed, never pushed. |
| **`v1`** | `a0051c9` — the build before the source archive existed. The fallback. |
| **Archive** | 237 documents: 58 primary sources, 170 held for reference, 9 written by us |

**Nothing deploys without being asked.** To put the site back to `v1`, Cloudflare kept the
build:

    wrangler pages deployment rollback a3d2f394-103d-44e8-bad0-f6e0a59b40c0 --project-name lunenburg-fy28

Other branches in the repo (`sped`, `sources-only`, `review-a0051c9`, and four older ones)
are history. **`sped` is superseded** — it carries a 7.4% special education rate derived by
comparing an actual to a budget, which is the error rule 1 exists to prevent. Do not merge
it.

---

## 2. What is on `sped-curve` and not yet live

Three things, all uncommitted to `main`:

**Special education split out of salaries.** The state's function codes could not separate
it — 2330 is paraprofessionals of both kinds, 3300 is transportation of both — so about
$5.7M sat inside `salaries` at the teachers' contract rate. Split out:

| bucket | FY27 base |
|---|---:|
| salaries (non-SPED) | $12,688,312 |
| **sped** | **$5,745,543** |
| health | $4,019,071 |
| transport (gen-ed only) | $1,053,360 |
| sped_tuition | $700,142 |

Ties to the published $26,572,288 within $2. This part is solid and worth keeping.

**`MANDATE_FLOOR` labeled as an assumption**, not a legal boundary, and exports a note
saying so. The town cut a school psychologist from $98,784 to zero between FY26 and FY27,
so there is no established floor.

**The special education rate is set to 5.9% — and that is wrong.** See §4.

---

## 3. What was established this session

Everything here is measured, not inferred. Anything inferred is marked as such in §5.

### The whole-budget driver ranking

Budget to budget, FY25 adopted → FY27 level service, against a 2.5% levy cap:

| line | share | 2-yr rate | points of gap |
|---|---:|---:|---:|
| **Health insurance** | 15.1% | 13.4% | **+1.66** |
| **Special education** | 21.6% | 5.9% | **+0.73** |
| Utilities | 2.3% | 15.0% | +0.28 |
| Athletics | 0.8% | 31.8% | +0.24 |
| Transport (gen ed) | 4.0% | 7.8% | +0.21 |
| **Teaching & other salaries** | **35.7%** | **2.5%** | **+0.01** |
| Out-of-district tuition | 2.6% | −22.5% | −0.66 |

**Two findings, neither about special education:**

1. **The largest line in the budget is not a driver.** Teaching and other salaries are
   35.7% of spending and grew at exactly the levy cap. The app calls salaries "the largest
   single lever, because two thirds of the budget moves with it" and models it at 4%.
   That copy is now corrected on this branch; the underlying 4% assumption is not, and
   should not be — it is the contract rate, and the model projects level service.

2. **No single line closes the gap.** Health alone is 1.66 points of a 1.40-point gap,
   which reads as though it were the whole problem — but only because the falling tuition
   line flatters everything else. Strip out health *and* that fall and the remainder still
   grows at 3.67%.

### The FY27 level-service year

| | |
|---|---:|
| As published | 3.98% |
| With out-of-district tuition held flat | **6.23%** |

One line bends the published rate down by 2.25 points. Out-of-district tuition was
budgeted down 46%, from $1,291,293 to $700,142.

### Special education, decomposed

FY26 budget → FY27 level service. The year is two entries moving opposite ways:

| | change | rate |
|---|---:|---:|
| Paraprofessionals | **+$530,038** | +39.4% |
| Out-of-district tuition | **−$591,151** | −45.8% |
| Special education teachers | −$33,336 | −1.7% |
| Substitutes | $0 | 0% |

### There is no special education contract

Professional staff are on the teachers' agreement, aides on the paraprofessionals'. Same
units as everyone else. Weighting the line by the contract governing each part:

| unit | share of the line | contract |
|---|---:|---|
| Professional (LEA) | 52% | 3.5% FY27 + steps |
| Paraprofessionals (AFSCME 503) | 33% | 2.0% FY28 + steps |
| Transport (vendor) | 12% | vendor contract |
| Substitutes, supplies, legal | 3% | not bargained |

**Contract-only escalation: 2.48%.** The line rose more than that. What accounts for the
difference is **not established** — see §5.

### Student counts (DESE, saved locally)

| FY | students with disabilities | % of enrollment |
|---|---:|---:|
| 2019 | 277 | 16.7% |
| 2022 | 227 | 14.1% |
| 2026 | 258 | 16.3% |

Down 6.9% over seven years; up 10.3% over the last three. Share of enrollment essentially
unchanged since FY19.

The district's own FY27 FinCom deck reports, FY23→FY26, full inclusion 156→174 and
sub-separate 30→43. **Its totals do not match DESE's for the same years.** The two count
different things and cannot be reconciled from what is published.

---

## 4. The open decision — this is where to pick up

The model needs one growth rate for special education. Three candidates, all defensible,
$403,337 apart in the FY28 gap:

| assume | because | FY28 gap |
|---|---|---:|
| **2.48%** | It is what the contracts give. Provable. | $513,681 |
| **5.9%** *(current)* | It is what two years of budgets did | $710,179 |
| **9.5%** | It is what the most recent year did | $917,018 |

**Why 5.9% is wrong as it stands:** it is one step rather than a trend (paras fell 2.4%
then rose 39.4%; everything else went +4.2% then −1.0%), and it merges the bargained part
with an unexplained part into one number that looks measured.

**Proposal put to TJ, not yet decided:** default to **2.48%** — the number a contract can
be pointed at — and put the remainder on a visible dial starting at zero, labeled that the
budget grew faster than the contracts explain, that we do not know why, and what it costs
if it continues. Cost of that choice: the headline gap drops to about $514k, lower than
the app shows today, and someone could reasonably say we are understating.

**TJ's last message said the framing was still unclear. The decision is his and is
outstanding.**

---

## 5. Claims that are NOT established — do not restate these as fact

Rule 7 exists because each of these shipped before being caught:

| tempting to say | actually established |
|---|---|
| The district brought children back in district | Two budget lines moved opposite ways by similar amounts. The tuition line may simply have been over-budgeted for years — FY25 was budgeted $1,164,824 and spent $732,298. |
| The unexplained increase is more staff | The increase exceeds what contract percentages produce. It could be classifications, steps, hours, or recoding. The budget never shows people. |
| The mix shifted toward intensity | Two sources report different counts and cannot be reconciled |
| Caseload is growing | DESE's count fell 6.9% over seven years |

A document stating intent is evidence of intent, not outcome. The district's FinCom deck
says *"investing in internal staff is significantly more cost-effective than tuition and
transportation for OOD placements"* — that shows what it meant to do, not what happened.

---

## 6. Where things live

**Analyses, published in the archive** (`sources/analyses/`)
- `sped-and-the-curve.md` — the special education work. Most current.
- `budget-vs-actual.md` — the actuals thread, deliberately separate from the projection
- `fy27-cut-reconciliation.md` — why the FY27 cut is both $1,174,933 and $761,000
- `fy27-and-the-override.md`, `peer-districts.md`, `sped-and-funds.md`

**Internal, never published** (`notes/`)
- `PASSES.md` — the working log, one entry per pass
- `DATA-WANTED.md` — 14 things to pull, with suggested wording. **Give this to TJ.**
- `BUDGET-VS-ACTUAL.md` — the internal copy of the actuals thread
- `HANDOFF.md` — this file

**Scripts** — all idempotent, all re-runnable

    python3 scripts/audit_provenance.py        # no projection reads actuals; model.json fresh
    python3 scripts/backtest_rates.py          # assumptions vs the district's own later budgets
    python3 scripts/build_source_index.py      # catalogue; fails if it drifts from the archive
    python3 scripts/build_agent_endpoints.py   # llms.txt and /data/*
    python3 model/export.py                    # after ANY model/ change
    python3 scripts/fetch_school_budget_docs.py # re-crawl the district page
    python3 scripts/fetch_town_docs.py          # re-crawl the town finance pages
    python3 scripts/fetch_dese.py               # re-pull the state enrollment series

**Run the first three before any commit that touches the model.**

---

## 7. Known gaps and dead ends

- **mass.gov returns 403 to anything automated**, browser user-agent included. DLS free
  cash, Schedule A and the levy limit history are all in `DATA-WANTED.md` for TJ to pull.
- **Job postings** are on SchoolSpring with no district URL, and show what is open now
  rather than what was filled. Whether the budgeted aide positions were filled has to be
  asked, not scraped.
- **One town document held but not served** — a 40MB bridge engineering report, over the
  host's per-file cap and outside the budget. Named in the index with the reason.
- **The 53MB teachers' agreement** is served from R2 because it exceeds the host cap.
  `ELSEWHERE` in `build_source_index.py` names the exception.

---

## 8. If you do only one thing next

Settle §4 with TJ, then rebuild the rate as two terms — contract escalation as a sourced
fact, the residual as a labeled unknown. Everything else on this branch is ready.
