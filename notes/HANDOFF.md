# Handoff

Written to survive a context reset. Read `CLAUDE.md` first — thirteen rules, every one of
them written because it was broken here.

**Nothing in this file is a source.** After a reset it reads exactly like something already
verified. It is a claim about the repo. Check anything load-bearing against the repo — and
note that this file has itself been wrong twice: it said `v3` was live when `v5` was, and it
said the athletics transportation sentence was "fixed on this branch" when it had never been
fixed anywhere. That second one got repeated to TJ as a reason to deploy.

---

## 0. STATE, as of 30 August 2026

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org` — commit **`58890b7`**, formerly tagged `v9` |
| **`main`** | 3 commits past that, pushed to GitHub, NOT deployed |
| **Newest tag** | **`v6`** (`56d7d37`). The site's own version says **`v7`** |
| **Deployed ≠ HEAD** | deliberately. TJ reviews on localhost before anything ships |
| **Dev server** | `cd fy28 && npm run dev` → localhost:5173 |

**The release numbering was closed up on 30 August, and four tags were deleted.** Five
builds shipped the free cash work over two days; they are one release note now, and the
numbering went with them so the panel would not read v11 then v6. `v7` will be re-created
at the deploying commit. What the retired tags pointed at, so no build becomes unfindable:

| retired tag | commit | what it was |
|---|---|---|
| `v7` | `5c76af5` | the town already published both sides of the free cash argument |
| `v8` | `083ff3a` | model free cash at any level, including spending it all |
| `v9` | `58890b7` | free cash as an opt-in model factor — **this is what is live** |
| `v10` | `f35b70d` | free cash as a standing policy lever |

**Two process rules, both learned the hard way:**

1. **Never deploy without asking, every single time.** Early on TJ approved `v4`–`v7`
   individually; the next three shipped on that as though it were standing permission. It
   is not. One went out while TJ was still specifying the design and was rolled back.
   The mechanical cause was bundling commit + deploy + push into one command so there was
   no natural pause. Do not do that.
2. **Push before deploying, not after.** For three deploys the built output was public
   while the source existed only on one laptop. Cloudflare had the artifact; nothing had
   the code.

Deploy needs **Node 22 via nvm**. Build with **`npm run build:site`**, never `npm run build`
— the latter ships the un-prerendered SPA. Then `npm run check:agents`, which fails if the
prerender was skipped, if `/data/model.json` is stale, or if HEAD is past the newest tag.

**`npm run check:agents` currently fails on purpose:** the site says `v7` and the newest tag
is `v6`. Tagging HEAD `v7` is the deploy's first step, not something to do in advance — the
failure is the guard that stops untagged work shipping.

## 0a. What this session did

Two records requests ingested, a fee error found and fixed, the site made readable by
machines, and a free cash model built from the state's own figures.

**The athletics ledger** (`sources/records-request-2026-06/`, `analyses/athletics-ledger.md`).
Three MUNIS journal exports — the first complete fiscal years of ledger data this project
has held for school money. `$254,121.18`, 65% of FY2025's receipts, is four journal entries
labelled `ADJ EXP` and described only as "per memo". **What they were for is not
established.** Getting those five memos is `DATA-WANTED §3d` and is still the highest-value
ask in the project.

**FY26 athletic fees were priced at $250 when the district charged $325** — a right number
from the wrong year, taken from an undated FAQ. Found via a School Committee vote of
26 February 2025. `sources/data/rate-register.csv` now carries 62 rates, each with the
fiscal year it applies to and the document that set it, so it cannot recur.

**The site is now readable without JavaScript.** All 16 routes prerender; the meeting
archive (1,383 documents, 40 boards) is published as full text; a missing archive document
returns a real 404 instead of the app shell. `/rate-register` and `/free-cash` are new pages.

**Free cash** (`sources/dls-free-cash/`, `analyses/free-cash.md`, `model/freecash.py`,
`/free-cash`, and a control on the rate board). The DLS proof for nine towns, 2021–2025.

---

## 0b. Free cash — what is established, and the numbers

- Lunenburg certified **$3,354,370** on 1 July 2025 — **6.55%** of a $51,189,961 budget.
- The Town quotes DLS at **5–7% of the annual budget** and says it is "well within" it.
  **That band is single-sourced**: the Town's own FY27 press release, quoting DLS. We hold
  no DLS document saying it, and the threshold is load-bearing.
- The same press release says the town was **below the recommendation in seven of the last
  ten years**. So both local arguments are right about different windows.
- **A normal year generates $2,026,212 — 3.96%, below the floor.** The record exists because
  unspent appropriations were 2.49× their own four-year average, the largest jump of nine
  towns.
- **About 24%, or $794,872 a year, could be redirected to the schools** while the retained
  balance stays inside the band. That is the number on the slider.
- **Free cash is the capital programme's money.** Departments ranked $3,267,208 of projects
  against $1,830,203 funded, so **$1,437,005 is already below the line**. A dollar out is a
  dollar of ranked work not done — in DOLLARS, exactly, which is the only part that is
  arithmetic.
- **A third of the capital programme is not school money and never could have been.**
  $594,000 of the $1,830,203 is the Vehicle Use Special Purpose Stabilization Fund,
  restricted to vehicles and equipment. The plan footnotes two projects as funded from it —
  Engine 2 ($335,000) and the front end loader ($259,000) — and they sum to exactly the
  $594,000 its funding page shows, which is how the assignment is known. **A draw can strand
  $1,236,203, not the whole programme.** The first version of this model took items off the
  bottom of the full funded list and stranded the loader with free cash that never paid for
  it.
- **Which projects stop is a range, not a number, and the site now says so.** Rank 7 is a
  $494,500 roof with only $199,449 of items below it, so held to the published ranking a
  $300,000 draw and a $500,000 draw both remove $693,949. Re-sequenced against the
  $1,437,005 queue, $300,000 removes $301,703. The rigid reading overstates a $300,000 draw
  by 131%, and the overshoot is an artifact of assuming indivisible items in a fixed order,
  not a cost of the policy. **We hold no instance of the committee re-ranking after a cut**
  — `DATA-WANTED §3e`.
- **The ceiling is larger than what free cash has usually given capital.** It funded
  $655,424 of last year's $1,225,000 capital plan, and averages $591,286 over the plan's own
  ten-year table, so $794,872 exceeds the whole year's contribution in seven of ten years.
  The capital-side twin of the normal-year finding.

**DLS dates free cash to the 1 July it is certified; the Town dates it to the fiscal year it
can be spent in. They are one year apart.** Confirmed, not assumed.

---

## 0c. Next, in order

1. **TJ's outstanding request: a popup showing the specific cuts.** The capital consequence
   line names a count and the largest project; he wants the full list of what falls off.
   The data is already exported — `MODEL.freeCash.capital.atDraw[i].projects` has rank,
   dept, project and cost for every item at every stop. It is a UI job only.
2. **Tag HEAD `v7` and deploy** — with TJ's explicit say-so. The release note is written.
3. **The five `ADJ EXP` memos.** `DATA-WANTED §3d`.
4. **DLS's own free cash guidance.** The 5–7% band is one sentence written by one party to
   the argument.
5. **Which departments turned back the $2,457,761.** Town-wide total, no breakdown. It is
   the difference between a structural pattern and a run of one-offs.

---

## 0d. Do NOT restate these as established

| tempting | actually |
|---|---|
| DLS recommends 5–7% | The **Town** says DLS does. We hold no DLS document |
| Lunenburg is hoarding free cash | Below the recommendation seven of ten years, on the Town's own account |
| Lunenburg is rebuilding | This year is a record and inside the band. Both claims are about different windows |
| The `ADJ EXP` entries moved costs to the general fund | Three readings fit. No memo held |
| Redirecting free cash costs capital one-for-one | In dollars yes, because of the queue. In projects it is a range: a $300,000 draw costs $693,949 if the CPC holds its ranking and $301,703 if it re-sequences, and nothing published says which |
| The two stabilization-funded projects are ranks 3 and 11 | They are the only two the plan footnotes and they sum to exactly the $594,000 its funding page shows. That is a reconciliation, not a published assignment — no project-by-project funding table exists |
| Tighter budgeting would free money AND keep free cash | The flow is produced by the underspending. It cannot be counted twice |
| The teaching board agrees with the model | It does — but `matchesEngine` was uncalled for months. It now runs and shows a visible warning |

---

## 0b. The site was invisible to anything that does not run JavaScript

Fixed on 29 August 2026, after a report that an assistant could not read the site.

**It was true.** Every one of the fourteen routes returned a byte-identical 6,122-byte
shell whose entire body was `<div id="root"></div>`. `/athletics` returned the home page
skeleton. The content only existed after React ran, so a fetch — an assistant checking a
figure, a crawler, a link preview — got an empty div.

`fy28/scripts/prerender.mjs` now renders each route in headless Chrome (via Chrome's own
`--dump-dom`; no Puppeteer, nothing added to `package.json`) and writes `dist/<slug>.html`.
Routes come from `src/routes.ts` so a new page cannot be missed.

**The interactivity is untouched, and this is checked rather than asserted.** `main.tsx`
uses `createRoot`, not `hydrateRoot`, so React discards the prerendered markup and renders
its own — there is no hydration contract to break. `npm run check:interactive` proves it on
the real build by stamping the prerendered nodes during parsing, then confirming React
removed them, attached, and responds to a click.

**Three things found while doing it, each of which had been wrong for a long time:**

1. **`_redirects` has never worked.** `wrangler pages dev` reports `Parsed 0 valid redirect
   rules` — Cloudflare rejects a 404 status outright, and rejects `/* /index.html 200` as
   an infinite loop. The SPA fallback that `_redirects`, `netlify.toml` and `routes.ts` all
   describe as load-bearing comes from the **Pages default**: with no root `404.html`, an
   unmatched path gets `index.html` with a 200. The file is kept, filled with this
   explanation, because "there is a `_redirects` file so redirects must be configured" is
   what hid it.
2. **The site answered 200 for archive documents that do not exist** — a soft 404. Nothing
   reading status codes could tell a missing source document from a present one. Now fixed
   by `fy28/functions/docs/[[path]].js` and `.../data/[[path]].js`, which return a real 404.
   **This makes the deployment a Pages Functions deployment rather than pure static**; if
   that is unwanted, deleting `fy28/functions/` reverts it and nothing else breaks.
   The error page must **not** be named `404.html` — that filename is a platform convention
   that overrides the SPA default and turns every stale shared link into a hard 404. It is
   `not-found.html`.
3. **`/athletics` was missing from `sitemap.xml`.** `prerender.mjs` now fails if a route in
   `routes.ts` is absent from the sitemap.

Verify the whole thing against a local Pages runtime, or against production:

    npm run build:site && npm run check:agents
    npm run check:agents -- --url https://lunenburgbudgetproject.org

---

## 1. Where everything is

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org`, tag **`v6`** |
| **Working branch** | merged. `main` is the live commit |
| **Ahead of production** | **nothing.** `main`, the newest tag and the deployed build are the same commit |
| `main` | pushed to GitHub, and it is what is live |

Deploy needs **Node 22 via nvm** (system node is 20 and fails). Cloudflare Pages,
`npx wrangler pages deploy` from `fy28/`.

**Build with `npm run build:site`, not `npm run build`.** `build` alone produces the
un-prerendered SPA, and deploying that silently undoes the agent-accessibility work — every
route goes back to serving the same empty shell. `build:site` is `build` followed by
`prerender`. Then run `npm run check:agents`, which fails loudly if the prerender was
skipped (it catches routes serving identical text).

~~Verify a deploy with a browser user-agent, the domain 403s otherwise.~~ **Not true, and
it was in this file for a while.** Every user-agent gets 200 — plain `curl`,
`python-requests`, `ClaudeBot`, no UA at all. Verify a deploy by hashing a document from
production against `sources/`; no special headers are needed.

**Use a cache-busting query param, and check it survived.** On 30 August an agent reported
the site was client-side rendered and had no body content, hours after it was prerendered
and deployed. It was reading a cached response. Its own `?nocache=` attempt was
*normalised away* — the param stripped and the request folded onto the same cache entry —
so it looked like a fresh fetch and was not. `?v=4` was left alone and came through clean.
A cache-buster that gets normalised is worse than none, because it produces a confident
wrong answer. Prefer `?v=<n>` over `?nocache=`, and confirm the param is still on the URL
that actually got fetched.

The site is **prerendered (SSG)**, not server-rendered (SSR): `prerender.mjs` writes static
HTML at build time. There is no server rendering per request, so there is nothing to fall
over and no hydration contract — see §0b.

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

## 4. The citizen workbook — its numbers are now sourced; the app is unchanged

> **Superseded in part on 29 August 2026.** The district's own sport-by-sport workbook arrived
> from the Town by records request and reproduces both central figures to the cent. The section
> below is kept because the reasoning in it is still how the workbook should be read — two of
> its four year-columns really are model output — but "we hold the analysis, not the ledger
> under it" is no longer true of the underlying data. See `analyses/athletics-ledger.md` §6.

## 4a. The original record — UNPROVEN, and acted on nowhere

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

~~Shipped in the deployed `v3` build, and fixed on this branch but not deployed:~~
**Fixed and deployed in `v6`.** It was ALSO not fixed when this section claimed it was —
the sentence lived on in `model/derivations.py` for another day because that claim was read
out of this file and believed. The note is now built by `_transport_note()` from the data.
The original wording, for the record:

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

1. ~~Deploy, or decide not to.~~ **Done.** v4, v5 and v6 all shipped on 29-30 August 2026.
   `main` is the deployed commit and is pushed. **Push before deploying, not after** — for
   three deploys the source existed only on one laptop while the built output was public,
   which is the wrong way round and TJ said so.
2. **Send `notes/REQUEST-3c.md`, narrowed.** Item 2 (fund 1301 ledger) is now partly filled —
   the cashbook arrived, the object detail did not. **Add a sixth item: the five memos** behind
   the `ADJ EXP` journal entries, dated 08/12/24, 01/30/25, 05/02/25, 07/02/25 and 08/20/2025.
   Those decide whether $304,046.18 across two years was a reclassification, a transfer or a
   correction — which is the difference between "the town's share rose" and "the cost rose".
   Items 1 (general fund athletics orgs), 3 (FY25 fund balance sheet) and 4 (vendor warrants)
   are untouched and all three are still needed.
3. **Decide what reaches the app.** This is the step `REQUEST-3c.md` says comes last, and it
   is now the open one. Three candidates, none of them made:
   - `athletics-history.csv` still marks the FY24/FY25 revolving figures `basis=unproven`.
     `model/export.py:61` keys the app's "partial fund data" marking off that exact string, so
     changing the label changes the published page.
   - `model/athletics.py` prices FY26 at $250 when the workbook says $325. Fixing it changes
     every fee figure on the site, and probably narrows the two-sided range.
   - The 44% appropriation-to-cost measurement is the sharpest statement of rule 11 the project
     has, and the app says nothing like it.
4. **The para question** still needs DESE's End of Year Financial Report — `DATA-WANTED.md`
   §3b.

---

## 9. Claims that are NOT established — do not restate as fact

| tempting | actually established |
|---|---|
| The revolving fund does not pay athletic transportation | Contradicted. It paid 59–69% of it in FY14–17 |
| The fund was drained and the town picked up the cost | The fund was at break-even and given officials to pay for. Same arithmetic, different blame |
| Athletic transportation cost $117,555 in FY24 | **Settled as to source.** It sums to the cent from the district's own workbook, supplied by the Town. The split between fund and town is still our subtraction |
| The app double-counts athletics fees | **Settled.** It runs the other way: the line was never the cost |
| $127,550 is over-budgeted | Not against the all-in cost. Only against an appropriation that was never the cost |
| The fund's 22% share is stable | Two observations, seven years apart. Two points cannot show a line |
| Athletics fees sit under c.71 §47 | The town books the fund as **1301 CHAPTER 658 REVOLVING FUND** |
| The town gives back money every year | Two clean years: one −0.34%, one **+0.50%** |
| The para line measures staffing | It measures the town's share of staffing (rule 11) |
| The athletics fund ran a $123,000 deficit in FY2025 | Its cash would have closed there without four journal entries. The entries are real and are the town's |
| The fund was overdrawn from November to May | That is *our* ordering of backdated rows. MUNIS gives no intra-day order and posts months late |
| The `ADJ EXP` entries moved costs to the general fund | An expense adjustment raising cash. Reclassification, transfer and correction all fit. We hold no memo |
| The fund's payroll was coaches | No name, position or object code on any payroll row |
| Athletics costs $384,135.65 | That is what the district's *operating workbook* totals for FY2024. It is not a ledger and does not reconcile to one |
| The general fund pays 44% of athletics | One year, one program, comparable categories only |
| Middle school fees exceed the middle school rate | The 2025-26 middle school rate is stated in no document we hold |
| 593 students played sports in 2025-26 | Two town documents say 593 and 649 and count different things |

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
