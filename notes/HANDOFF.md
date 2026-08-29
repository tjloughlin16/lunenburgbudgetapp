# Handoff

Written to survive a context reset. Read `CLAUDE.md` first — thirteen rules now, and every
one exists because it was broken here. **Rule 13 is new and is about how to read a source
without fooling yourself; it was written from four errors made in one day.**

**Nothing in this file is a source.** After a reset it reads exactly like something already
verified. It is a claim about the repo. Check anything load-bearing against the repo.

---

## 1. Where everything is

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org`, tag **`v3`** = `6fb5e2c` |
| **Working branch** | **`source-basis-classification`**, `2ab62f6` |
| **Ahead of production** | **27 commits.** Verify: `git rev-list --count v3..HEAD` |
| `main` | untouched today — the branch has not been merged |

Deploy needs **Node 22 via nvm** (system node is 20 and fails). Cloudflare Pages,
`npx wrangler pages deploy` from `fy28/`. Verify a deploy by hashing a document from
production against `sources/` using curl with a browser user-agent (the domain 403s
otherwise).

**A deploy is queued and was explicitly NOT run.** See §8.

---

## 2. What this session actually established

The session began intending to fix an athletics fee double-count. It found something else,
and the correction runs the **opposite way** from what the previous handoff said.

**The archive called restatements "actuals".** An "actual" in a school budget document is a
prior year re-presented by the party that spent it, inside the argument for next year's
budget. That is not a ledger figure and the two are not interchangeable.

`sources/data/document-basis.csv` now classifies all 216 financial documents:

```
ledger        15     a figure exists because a transaction did
restatement   46     a prior year re-presented by the spender
forward      103     proposed / requested / level service / balanced
narrative     52     money discussed, no figure table
```

**Of the fifteen ledger documents, exactly one reaches school budget lines** —
`district-budget-page/text/fy23-quarterly-budget-update.txt`, one quarter of FY23.
Everything else the school analysis rests on is restatement. Regenerate with
`scripts/classify_document_basis.py`; every row quotes the raw header text it rests on.

---

## 3. Athletics — the whole finding

`sources/analyses/athletics.md`, 742 lines, seven sections, verified by
`scripts/verify_athletics.py`. `sources/data/athletics-history.csv` is the data spine.
There is a page in the app at **`/athletics`**.

**The district published athletics against the Chapter 658 revolving fund once**, for FY19,
line by line. It is the only document in 3,230 that shows both sides. In every year it
reports as actual the fund paid **more** of athletic transportation than the town did —
59% to 69%. The FY26 budget overview says the same in words: the athletics line was
*"reduced from Level Service with anticipation that athletic revolving may be enough to
offset this reduction in the budget line"*.

**The fund's share of all athletics is unchanged where we can compare it** — 22.2% (FY19)
against 22.1% (FY26). It did not withdraw. Transportation moved fund → town; officials and
uniforms moved town → fund, within about $8,000 of each other at the trade.

**The reported actuals on the transportation line are encumbrances.** The one ledger view
shows `Expended 0.00 / Encumbrances 40,000.00` — the whole year committed as one purchase
order. Four of nine usable years have an "actual" equal to the budget to the dollar.

**The fund never had slack.** FY14–17 margins ran +$3,217, +$28,810, +$7,736, **−$22,200**.
It went negative in FY17 and shed coaches entirely in FY18 to recover. FY24 it took on
officials (~$51,000, roughly its whole margin) and landed at **−$872** on a $128,000 fund.
FY25 it shed transportation. **Nothing about transportation changed; what changed is what
else the fund was asked to carry.**

**The FY25 deficit is reported, not established.** Three references in one window — a
resident telling School Committee (3 Sept 2025) the fund "was running in a deficit, I was
told over $100,000"; the Finance Committee (8 July 2025) wanting revolving accounts
budgeted "to prevent negative balances from going unnoticed"; a resident on budget approval
day (12 March 2025) on splitting everything into revolving funds. The fund closed FY25 at
**+$110,248**. We hold the endpoint and not the path — there is no FY25 fund report.

---

## 4. The citizen workbook — UNPROVEN, and acted on nowhere

`Athletics_v10.xlsx`, sha256 `63fc34d428ea09d9…`. A resident's analysis built on a
c.66 request that produced three years of the athletics GL plus the district's sport-by-sport
file. **We hold the analysis, not the ledger under it. It is not published in the archive**
— it is someone else's work product and permission has not been asked. TJ has requested the
raw GL from the originator.

Two of its four year-columns are model output: 25/26 is 24/25 escalated 6.5%, which its own
cell `A2` declares and the arithmetic confirms to the cent. **Only 23/24 and 24/25 are
observations.**

Those say athletic transportation cost **$117,555 in FY24** against a general fund line of
**$40,000**, and **$91,066 in FY25** against **$87,822**. If it holds, the migration dates
to FY25 and three anomalies resolve at once. It is internally inconsistent in ways recorded
in `athletics.md` §6 — a duplicated Spring revenue cell, incomplete total rows, inconsistent
column layouts across its three season sheets.

**Direction matters, and it is the thing most likely to be got wrong on a fresh read.** The
previous handoff said the app *overstates* athletics costs by double-counting fees. This
says the app *understates* the transportation line. Both cannot be the shape of the error,
and neither is settled.

---

## 5. What is live and wrong right now

Shipped in the deployed `v3` build, and fixed on this branch but not deployed:

> *"Budgeted well above what athletics has ever actually spent. Actuals were $39,880 (FY23),
> $40,000 (FY24) and $87,822 (FY25)…"*

That takes the town's share, calls it what athletics spent, and concludes the budget is
padded. It is rule 11 broken in one sentence, in public.

---

## 6. The fee model — rewritten, and why it is a range

`model.json` carried `estimatedFy26Revenue = $130,129`. The fund's own year-end
reconciliation reports **$188,944 net** ($194,609 gross). The model was 31% low.

The gap has two candidate causes and **they imply different curves**, so both are carried
rather than one being chosen. Both reproduce FY26 exactly by construction:

- `scaled` — participations undercounted, so the gap grows with the fee
- `flat` — surcharges outside the published schedule, which do not rise with the base fee

```
                          published    now
self-funding, buses back       $960    $500–$695
coverage at today's fee         54%    71%–79%
```

`FEE_REVENUE_IN_BUDGET` was `False` on backwards reasoning and is now `True`: fees pay for
officials and uniforms, those lines are budgeted **$0** in the general fund, so the cost
never appears and the appropriation is already net of them.

**Conclusion 7 was rewritten.** It said *"Athletics cannot pay for itself once you put the
buses back."* On the measured base it can. Its figures are interpolated now, not typed.

**Still unresolved:** the measurement implies $287.82 per high school participation against
a $250 first-child fee. A blended rate cannot exceed its top tier. Either participations are
undercounted or there are surcharges in no schedule we hold. That is why every fee figure is
a range.

---

## 7. Defects found and fixed in the tooling

- **`extract_town_ledger.py` silently dropped 16 of 67 departments** — MUNIS prints zero as
  `.00` and the regex required a digit before the point. $4,074,773 of revised budget,
  invisible, including a $2.4M assessment. It now reconciles to the report's own GRAND
  TOTAL before it will write. Three figures in `budget-vs-actual.md` were wrong as a result
  and are corrected: 51 → **67** departments, 25 → **28** with transfers, $452,971 →
  **$489,411 in / $148,177 out**.
- **Two copies of the same workbook hide different columns.** `fy27-proposals.xlsx` hides
  `C` (FY23 actuals); `fy27-budget-projection-3-25-26.xlsx` hides `F` instead. `MANIFEST.md`
  called them identical — corrected. Both hide `H` and `I`, the FY26 actuals-to-date and
  encumbrances.
- **`verify_athletics.py` passed on a false claim** because it checked a sentence was
  present rather than that its count was right. Hardened; it immediately caught "four of
  eight usable years" when there are nine.

---

## 8. What to do next, in order

1. **Deploy, or decide not to.** 27 commits, all checks pass, production build clean.
   Recommended: deploy — what is live is wrong in ways this fixes (§5, §6), and none of it
   depends on the unproven workbook. **TJ was asked and had not answered when context was
   cleared. Do not deploy without asking again.**
2. **Send `notes/REQUEST-3c.md`.** Written and ready. Five items; the two to keep if the
   office pushes back are the FY25 fund report and the fund 1301 ledger.
3. **Process the raw GL when it arrives.** TJ has asked the originator. `REQUEST-3c.md`
   ends with what to do with it, in order — and the last step is *then* decide whether it
   changes a published figure, not before.
4. **The para question** still needs DESE's End of Year Financial Report — `DATA-WANTED.md`
   §3b.

---

## 9. Claims that are NOT established — do not restate as fact

| tempting | actually established |
|---|---|
| The revolving fund does not pay athletic transportation | Contradicted. It paid 59–69% of it in FY14–17 |
| The fund was drained and the town picked up the cost | The fund was at break-even and given officials to pay for. Same arithmetic, different blame |
| Athletic transportation cost $117,555 in FY24 | One unsourced spreadsheet, two of whose four year-columns are model output |
| The app double-counts athletics fees | The previous handoff's claim. The error appears to run the other way |
| $127,550 is over-budgeted | Not against the all-in cost. Only against an appropriation that was never the cost |
| The fund's 22% share is stable | Two observations, seven years apart. Two points cannot show a line |
| Athletics fees sit under c.71 §47 | The town books the fund as **1301 CHAPTER 658 REVOLVING FUND** |
| The town gives back money every year | Two clean years: one −0.34%, one **+0.50%** |
| The para line measures staffing | It measures the town's share of staffing (rule 11) |

---

## 10. How to work with TJ

He will ask for a full analysis and mean it. Ranking by one measure and reporting the top
few is not a sweep. State coverage alongside findings, always, so he can see what was not
looked at. When a finding is surprising, check it harder rather than reporting it faster.
Say "paras", not "aides".

**And he will catch you.** Three times in one session he pointed at something I had quoted
as observed that was actually derived — a stitched column header, a hidden column, a budget
workbook called an actuals sheet. Each time he was right. That is what rule 13 is for. When
he says a document does not say what you claim it says, **open it by cell reference before
defending the claim.**
