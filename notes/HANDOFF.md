# Handoff

Written to survive a context reset. Read `CLAUDE.md` first — thirteen rules now, and every
one exists because it was broken here. **Rule 13 is new and is about how to read a source
without fooling yourself; it was written from four errors made in one day.**

**Nothing in this file is a source.** After a reset it reads exactly like something already
verified. It is a claim about the repo. Check anything load-bearing against the repo.

---

## 0. What arrived on 29 August 2026, and what it settled

**A records request was answered.** Five files from the Town, dated 17 June 2026, filed by
a resident and forwarded to us. They are ingested, catalogued, hashed and read.

**Do not name the requester** — in the archive, in an analysis, in a commit message or in the
app. TJ asked for this explicitly on 29 August 2026. The request and its date are the
document's address; the person who asked is not.

- `sources/records-request-2026-06/` — the documents, with `PROVENANCE.md` beside them
- `sources/analyses/athletics-ledger.md` — the analysis
- `python3 scripts/verify_records_request_2026_06.py` — **165 checks, 0 failed**

**This is the first ledger this project has held for a complete fiscal year of school money.**
Three MUNIS journal exports give the athletics revolving fund's cashbook for FY2024, FY2025 and
FY2026 (to 12 June 2026), every receipt and payment with a date. `document-basis.csv` went from
15 ledger documents to 18. The general fund still rests on one quarter of FY23 — these are a
revolving fund.

The four things most likely to be got wrong by somebody arriving fresh:

1. **The three files named `Account_Detail` are not account detail.** Every row in all three is
   one account, `1301-…-104000`, `CASH`. There is no object code, no transportation object, and
   **no vendor name on any payment row**. Request item 1 was not filled.
2. **$254,121.18 — 65% of FY2025's receipts — is four journal entries labelled `ADJ EXP` and
   described only as "per memo".** Take them away and the year closes at −$122,882.09. **What
   they were for is not established**, and three readings fit. Getting those five memos is now
   the highest-value ask in the project.
3. **The citizen workbook's figures reproduce to the cent** — $117,555.00 for FY24 athletic
   transportation and $91,066.06 for FY25 — from a workbook **the Town supplied**. What changed
   is the provenance, not the arithmetic. `athletics-history.csv` still says `basis=unproven`
   and `model/export.py` still keys off that string; **that was deliberately not changed**,
   because it changes published figures.
4. **The high school athletic fee in 2025-26 was $325, not $250** (`Spring!G3`, against
   `E3=250` and `F3=250`). The model prices FY26 at $250 and that is the main thing
   `FEE_CALIBRATION` has been absorbing. The middle school rate for that year is stated
   nowhere we hold.

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
