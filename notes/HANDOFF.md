# Handoff

Last updated 28 August 2026, evening. Written to survive a context reset. Read `CLAUDE.md`
first — it holds the ten rules, and every one of them exists because it was broken here.

---

## 1. Where everything is right now

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org`, built from tag **`v2`** = `e5332e6` |
| **`main`** | `e5332e6` — identical to `v2`. Pushed. |
| **Working branch** | **`sped-curve`**, `4450ffa`. Pushed. `main` merged in, so it is not behind. |
| **`v1`** | `a0051c9` — the build before the source archive existed. The fallback. |
| **Archive, live** | 236 documents in 14 groups, 354 MB, plus 1,383 meeting documents |

**The archive shipped on the evening of 28 August.** The `v2` tag was force-moved from the
66-document build of that morning, which the public never saw, and pushed with `--force`.
That earlier build is no longer named by any tag; it remains addressable only as Cloudflare
deployment `a3d2f394-103d-44e8-bad0-f6e0a59b40c0`, which is also the rollback:

    wrangler pages deployment rollback a3d2f394-103d-44e8-bad0-f6e0a59b40c0 --project-name lunenburg-fy28

Deploying needs **Node 22 via nvm**; the system Node is 20 and wrangler fails on it.
Verified after deploy by hashing one document from each archive section off production
against `sources/` — all three byte-identical.

**What went live that was not there before**

- The district's budget page and the town's finance pages mirrored in full, back to FY18,
  and the state enrollment series. 66 → 236 documents.
- A third archive section, *Everything else the district and the town publish*, for the
  mirrored material that feeds no figure.
- `/llms.txt` and `/data/{model,sources,budget-lines,district-page-index,minutes-index}`.
- **An Updated bar** on every page and a release-notes dialog. `model/releases.py` holds
  the history; `RELEASES[0]` is the current build and its `tag` must match the git tag
  actually deployed. Release notes are the one place in this project where a figure is
  typed rather than derived, and the module says why.

**Three false claims fixed on the way out**, all of the same shape — a categorical
statement about the corpus that a member of the corpus contradicted:

- The sources page said none of its documents was obtained by request while carrying 15
  that were, one group of which said so in its own blurb.
- The reference section was titled *not used in the analysis* over 15 files that are
  byte-identical copies of primary sources listed above.
- `llms.txt` published "special education 0.0%" on any build without that bucket.

Every count the sources page now states about itself is computed at build time. Rule 2 was
written about figures; a categorical claim goes stale the same way.

---

## 2. What is on `sped-curve` and not yet live

Three things, none of them yet on `main`:

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

**The special education rate is set to 5.9%**, and §4 explains why that is the right
choice rather than the cautious-looking one.

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

## 4. The rate decision — settled 28 August

**Special education is modeled at 5.9%.** Settled after TJ made the argument that reframed
it, and the reframing is the part worth keeping.

5.9% is a **measurement**: what the line did in the district's own budgets, FY25 adopted
$5,038,594 → FY26 adopted $5,158,207 → FY27 level service $5,649,284. A near-flat year
(+2.4%) and a steep one (+9.5%), averaging 5.9%. It already sits between the two extremes
rather than needing to be blended toward them.

The model projects **what the line has done**. It claims nothing about why.

**Why 2.48% was not the safer option**, which is where I had it wrong. Escalating at the
blended contract rate would assume nothing but bargained pay moves this line — and two
years of the district's own budgets contradict that. A lower number that assumes something
the data denies is not caution. It is an unsupported assumption that happens to be smaller.

The range is documented in `model/finance.py`, in the citation, and on the rate page:

| | |
|---|---:|
| contracts alone, if nothing else changes | 2.48% |
| **what the line did, two years** | **5.90%** |
| what it did in FY27 alone | 9.52% |

FY28 gap at 5.9%: **$710,179**.

Note for whoever picks this up: TJ believes headcount rose, and that is very likely the
explanation. It is deliberately **not** written anywhere as a finding, because staff counts
are not published and rule 7 applies. The model does not need the explanation to be right —
it projects the line, not the cause.

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

**Integrate the special education analysis into the app.** `sources/analyses/sped-and-the-curve.md`
is finished and now catalogued; the app carries special education as a *bucket* — in the
composition chart, the assumptions dial, the structural chart and the `#leverage` ranking
on Bend the Curve, where it correctly sits second behind health — but carries none of the
*analysis*. Four findings, all budget-only, none of them in the app:

1. **The published rate is flattered by a one-off.** FY27 level service rises 3.98%; hold
   out-of-district tuition flat and it rises 6.23%. One line bends the published rate down
   2.25 points. Most load-bearing of the four: 3.98% is the number residents are quoted,
   and the site's whole thesis is that this is a rate problem. The named concept is a
   **base effect**, and the standard treatment is to quote both — headline 3.98%,
   underlying 6.23%.
2. **The year is one trade.** Paraprofessionals +$530,038 against placements −$591,151,
   everything else flat. Ships only with the rule 7 split: two lines moved opposite ways by
   similar amounts, and that is *all* the budget shows.
3. **The tuition risk.** $700,142 as budgeted → $1,291,293 back at FY26 moves the FY28 gap
   $613,238 → $1,148,377. The widest single-assumption range in the model.
4. **The rate has bookends.** 2.48% contracts-only / 5.90% used / 9.52% FY27-alone, visible
   next to the dial rather than only in a `finance.py` comment and a citation string.

**Placement, and the shape of #3, are decided.** TJ's steer, 28 August: a slider that lets
a reader pick their own tuition number is worse than a range we can defend. So #3 is not a
control — it is an analysis of **how the district has budgeted out-of-district placements
across its own past budgets**, from which a projection is chosen with a stated confidence,
or a range and its problems flagged. Budget columns only. That analysis has not been done.

Placement on the page was still open when the archive shipped: a section on Bend the Curve
between `#leverage` and `#proof` is the recommendation, since the finding *is* a curve
finding, but TJ had not picked.

**Not this yet:** the athletics fee re-base on FY26 actual collections. It is real — the
model is calibrated on $130,129 against $188,944 actually collected, and conclusion #5 may
flip from *impossible* to *possible but self-defeating* — but it runs on actuals, and
budget-versus-actual is its own conversation that has not happened.
