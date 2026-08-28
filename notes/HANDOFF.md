# Handoff

Last updated 28 August 2026. Written to survive a context reset. Read `CLAUDE.md` first —
it holds the rules, and every one of them exists because it was broken here.

---

## 1. Where everything is

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org`, tag **`v2`** = `e5332e6`. Headline $552,621. |
| **`main`** | `e5332e6`, identical to `v2`. Pushed. |
| **Working branch** | **`sped-v3`** at `6d4dcce`, targeting a `v3` tag. **Not deployed.** |
| **`v1`** | `a0051c9` — the build before the source archive. The fallback. |

Deploying needs **Node 22 via nvm**; the system Node is 20 and wrangler fails on it. Verify
a deploy by hashing a document from production against `sources/` — the domain returns 403
to anything without a browser user-agent, so use curl with one. Rollback to the
66-document build is Cloudflare deployment `a3d2f394-103d-44e8-bad0-f6e0a59b40c0`.

## 2. What `sped-v3` changes, and what it does to the headline

| | live (`v2`) | `sped-v3` |
|---|---:|---:|
| FY28 gap | — | **$680,870** |
| Headline, FY28–30 average after cuts | $552,621 | **$634,068** |
| Special education | inside `salaries` at 4% | own bucket, **6.49%** |
| Out-of-district tuition | 8% a year | **held flat** |

**This is a public number moving 15%.** Deciding to ship it is a separate decision from
merging.

## 3. The special education work, in one page

**The rate is measured, not assumed.** Each component escalates at what its own budgets
show it doing, weighted by share:

| component | share | rate | measured over | fit |
|---|---:|---:|---:|---:|
| Professional staff | 52.7% | 2.67% | 8 budgets | R² 0.84 |
| Paraprofessionals | 34.4% | 12.78% | 10 budgets | R² 0.89 |
| Transport | 11.9% | 5.69% | 9 budgets | R² 0.33 |
| **Blend** | | **6.49%** | | |

**The finding that generalises:** a contract sets what one person is paid and says nothing
about how many people are employed. The aides' agreement gives 2.0% and their line has
grown 12.78% across 10 budgets; the teachers' gives 3.5% and theirs has grown 2.67%.
Both bargained, both wrong, opposite directions.

**Out-of-district tuition is held flat**, and that is a finding. Eleven budgets from
$489,918 to $1,291,293, R² 0.10, and a compound rate swinging -45.8% to +11.8% on the
choice of start year. There is no rate to measure. The range is priced instead.

**The published rate is flattered by a one-off.** FY27 level service rises 3.98%; hold
tuition where FY26 had it and it rises 6.23%.

**The classification is ours and is published.** 54 lines, $5,466,201, listed with
the reason each was counted, at `/data/sped-lines.csv`. Publishing it found English
Language Learner costs inside the special education total; they are now excluded.

## 4. The rate changed four times in one day. Do not "restore" an earlier one

Every version is on the page with the reason it was wrong, and the sequence is the point:

| | why it was wrong |
|---|---|
| 2.48% | priced special education transport at 0%, which is in no contract |
| 5.89% | the whole line over two budgets — one hiring step, averaged and compounded |
| 2.57% | the settlements alone; assumed the FY27 aide increase was a step. Ten budgets say climb |
| 6.80% | measured aides and buses, still took the teachers from their contract on three years |
| **6.49%** | **measures all three** |

**Two budget years cannot tell a step from a climb.** That is the lesson, and it is why
the extraction exists.

## 5. Claims that are NOT established — do not restate these as fact

| tempting to say | actually established |
|---|---|
| The district brought children back in district | Two budget lines moved opposite ways by similar amounts. The tuition line may simply have been over-budgeted for years. |
| More aides means more children needing them | The budget line grew. A budget shows dollars and never shows people. It could be classifications, hours, or recoding. |
| The aide trend will continue | It has for 10 budgets. Nothing in a budget column tests whether it continues. |
| Caseload is growing | The state's count fell 6.9% over eight years |
| Special education is out of control | On budget columns it is not growing faster than the rest. The district's own move — bringing placements home — is the right one. |

A document stating intent is evidence of intent, not of outcome.

## 6. What is still not measured

**$920,007, 16.9% of the in-district line.** The professional rate is measured on
the teacher lines, $1,945,512 of a $2,865,519 component; therapeutic services,
psychologists and clerical ride on it. Extracting the speech and therapy lines was
attempted and gave three settled years — not enough to test a trend. The attempt is
recorded in `scripts/extract_budget_history.py`. **This is the next thing worth doing if
more of the district's documents are mirrored.**

## 7. Running the checks

    python3 scripts/audit_provenance.py         # no projection reads actuals
    python3 scripts/backtest_rates.py           # assumptions against later budgets
    python3 scripts/verify_sped_analysis.py     # every figure in the analysis, recomputed
    python3 scripts/build_source_index.py       # catalogue vs archive
    python3 scripts/extract_budget_history.py   # re-read the budget series from the mirror
    python3 model/export.py                     # after ANY model/ change
    python3 scripts/build_agent_endpoints.py    # llms.txt and /data/*

Run all of them before any commit that touches the model. `verify_sped_analysis.py` has
caught stale prose four times in one day; it is not optional.

## 8. What is left

1. **The deploy decision** — §2. Nothing has been pushed to production.
2. **The therapy component** — §6.
3. `notes/DATA-WANTED.md` — four one-line emails to the Business Manager. Item 4, whether
   the budgeted aide positions were filled, is now the highest-value one in the file: the
   whole in-district rate rests on a headcount trend nobody can see directly.
