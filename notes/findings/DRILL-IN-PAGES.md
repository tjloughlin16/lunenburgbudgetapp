# The drill-in analysis pages — what each one established, and what it did not

Written 7 September 2026, while the pages were being built, because the reasoning
behind a figure is the part that does not survive in the figure.

Each section below is a page under **The Money**. For each: the route, the findings
with the query that produced them, and — the part worth keeping — **what the page
deliberately does not claim**, and why. Rule 7 says a measurement is a fact and an
explanation for it is a hypothesis; most of the value in this document is in the
second half of each section, which is the half that gets lost.

The pages themselves type no figures. Everything here was recomputed against
`sources/data/lunenburg.db` at the time of writing; where a figure is quoted below
it is quoted **with the query**, so a reader can re-run it rather than trust it.

---

## 1. `/money-outside-the-budget` — the special revenue funds

**Commit** `308becb`. **Data**: `special_revenue_read`, 13 consecutive editions
(FY2011–FY2023), 1,882 rows, transcribed from rendered pages of the annual town
reports rather than OCR'd.

### What the data shows

```
carried  FY2011  $2,766,955  ->  FY2023  $10,031,100     = 3.6x
surplus in 12 of 13 years; the sole deficit is FY2012, -$704,333
```

- **34% of what is held is pandemic-era money** — eight named funds holding
  `$3,377,339` of `$10,031,100` in FY23, and **zero of it before FY20**. That is a
  cliff with a date on it, and it is the single most consequential number on the
  page: a third of the balance is money that arrived for a reason that has ended.
- **Most of it is not school money.** Five enterprise funds hold `$3,800,195`
  (38%); the school department holds `$1,753,708` (17%). The enterprise funds sit
  *inside* this schedule, so ratepayer money and school grant money are added
  together in the printed grand total. The page says this out loud, because it
  lives under The Money and a reader will otherwise assume schools.
- **FY23 was the first year since FY17 the school funds spent more than they took
  in** — receipts `$3,667,636` against disbursements `$4,333,280`.

### What it does not show

- **Not one dollar of this is traceable to a purpose.** The schedule is receipts,
  disbursements and balance per fund. What any fund *bought* is not in it.
- **A balance is not slack.** Several of these funds are legally restricted to the
  purpose that created them. A resident reading "$10M held" and hearing "$10M
  available" is the misreading this page most has to prevent.
- **The 3.6× is nominal.** No deflator is applied and none should be inferred.

### Chart detail worth keeping

The biggest-movers panels **share one denominator**. Drawn independently, an $85k
fall rendered the same length as an $893k rise — a chart that made a small thing
look like a big one. Any two panels a reader will compare must share a scale.

---

## 2. `/what-sports-cost` — athletics, both sides

**Commit** `3c7af74`. **Data**: `athletics_history` (town appropriation),
`athletics_by_sport` (the district's own sport-by-sport workbook),
`fund_1301_cash_journal` (the revolving fund's cashbook),
`athletic_fee_schedule`.

This page exists because athletics is the **only** part of school money where both
sides can be seen at once — an appropriation, and an independent statement of what
the same categories cost. That is why it carries weight far beyond its 1.7% of
spending: it is the control case for whether a budget line can be read as a cost.

### What the data shows

| | |
|---|---|
| FY2024 | town lines `$124,301` vs workbook `$351,642.89` on comparable categories — **35%** |
| FY2025 | transportation cost `$91,066`, line `$87,822` — 3.6% short, was **66%** in FY24 |
| FY2025 | **`$254,121.18` of `$390,299.87`** into fund 1301 was four `GEN` journal entries |
| FY24–26 | participations **−3.9%** (675 → 649) while the HS first-child fee rose **30%** |

**The journal-entry finding is the one to read twice**, and it reconciles exactly:

```sql
SELECT src, COUNT(*), ROUND(SUM(amount),2)
FROM fund_1301_cash_journal WHERE fy=2025 GROUP BY src;
--  GEN   4   254121.18
--  CRP  44   131481.37
--  SOY   1    33993.31   <- opening balance, not a receipt
--  GRV   3   -22582.82
--  PRJ  19  -124895.03
--  APP  21  -140878.92
```

`33,993.31 + 390,299.87 − 293,054.09 = 131,239.09`, which is FY2026's opening
balance — so the arithmetic closes against the next year's own printed figure
rather than against itself. Strike the four `GEN` entries and the fund closes
FY2025 at **−$122,882.09**. They are described in the ledger only as *per memo*.
**Two thirds of the year's inflow is a document we do not hold.** Registered as a
gap naming the five memos as what would close it.

### What it does not show

- **The fee did not necessarily move the participation.** Those are two
  measurements printed side by side with nothing joining them. Fees rose over
  exactly the years participation fell; that is a coincidence in time, and this
  data cannot promote it to a cause. Anyone quoting the pair as cause and effect
  is quoting the page wrong.
- **Participations are not children.** The workbook counts participations, and one
  child playing three sports is three of them. Some rows are *negative* —
  out-of-district athletes subtracted back out — so a season total is a net figure
  and not a headcount of bodies. How many children play sports is a registered gap;
  an unduplicated athlete roster would close it.
- **Whether the general fund athletics line is net of the revolving fund is
  unknown** (rule 11). Registered, closes with the `Account_Detail` export for orgs
  S3066672 / S3066671.
- **What the four `ADJ EXP` entries moved is unknown.** Not "probably a transfer" —
  unknown.

### It disagrees with the published analysis, on the page

Three places, rendered as a disagreement with which is which, not reconciled:

| | page | `athletics.md` |
|---|---|---|
| FY2024 general fund athletics | `$285,281` | `$314,319` (§7) |
| share of workbook cost covered, FY2024 | 35.35% | 44% (§5, `athletics-ledger.md`) |
| middle-school blended rate | `$224.78`, under the top tier | reported unresolved (§8) |

The first two are the same cause: commit `07aa298` withdrew three FY2024 rows
(Freshman & MS Coaches, Unified Sports Coach, Replacement of Uniforms) when it
fixed a column mapping, and the analysis predates that. The third closed because
`athletic_fee_schedule` now carries the $275 MS rate from School Committee minutes
of 26 Feb 2025.

**Rendering the disagreement was deliberate.** The analysis has a sha256 and a
published PDF. Silently agreeing with it would have been a derived thing quoted as
observed — rule 13, on our own prior work.

---

## 3. Rule-2 drift caught by a verifier, and why it survived every read-through

`verify_athletics.py` had been failing on two figures since a reclassification:

```
| `forward`   | proposed, requested, level service, balanced | 176 |  ->  172
| `narrative` | money discussed, no figure table             |  98 |  ->   75
```

Fixed in `05fae33`. The instructive part is **why nobody saw it**: the same table's
`ledger` (10) and `restatement` (65) counts still reproduced. Two of four figures
in one table were right, which made the table look computed. A figure typed beside
figures that are derived inherits their credibility and none of their maintenance.

That is the general shape of nearly every defect in this project — a derived thing
written down, the thing it derived from moved, and nothing connected the two —
and it is the argument for `check_generated.py` existing at all.

---

## 4. Open threads at the time of writing

- **State aid** and **free cash** pages in progress. For free cash the material is
  `free_cash_proof` — 630 rows of DLS proof workbooks covering peer towns, with a
  cross-foot that should tie components to the certified figure. If it ties, a
  resident can be shown the arithmetic that brings free cash into existence rather
  than told a number. `CL#6` / `CL#8` / `CL#11` decompose it into three different
  stories — conservative revenue estimating, aid surprises, and money appropriated
  and not spent — and **which one dominates is probably the most useful sentence
  that page could carry.**
- **The D1 push is held** by the site owner. `sync_d1.py --check` fails for that
  reason and only that reason; every other generator reproduces.
- **Still genuinely unread**: the FY2024/FY2025 combining balance sheets (~80 rows,
  with a $102,000 printed defect already located in FY2024), and the PEG
  revenue-vs-expenses statements (~11 editions, with a real cross-check).
- **FY2023 balance sheet** is transcribed and refused; the `$87,293.86` cross-check
  gap is open.
- **`sped_para_history` sign defect** is fixed. Parenthesised negatives were being
  eaten, and FY2024 was wrong by `$315,772` — twice the line, because the sign
  error doubles rather than zeroes. Other extracts may warrant the same audit; that
  audit has not been done.

---

## 5. The pattern these pages follow, and why

Set by the site owner: **insights / conclusions, then organised categorical data,
then raw data and context.** Now written down as CLAUDE.md rule 7b.

It is the shape a resident reads, and it is the opposite of the shape the data
arrives in — which is why it has to be a rule rather than an instinct. Everything
above the fold in a page's first draft got there because it seemed necessary
*before* the reader could understand what follows: true for the author, who has
just spent an hour on the caveats, and false for the reader, who came for a table.

Three years is a trend **here**. The boards in this town will not project two years
out, so a three-year series is more forward visibility than they currently use.
Plot it, and state the span on the chart so nobody mistakes three years for fifteen.
The general rule that replaces "short series are weak": judge a series against what
the reader currently has, not against what a statistician would want.

---

## 5b. `/state-aid` — the part nobody here votes on

**Uncommitted at the time of writing.** Data: `v_revenue` (FY2026 ledger),
`free_cash_proof` CL#8, `annual_report_receipts`, `ch70-fy27-summary.xlsx`,
`dese_measure`.

### What the data shows

- **Chapter 70 is 35.1% of the school appropriation.** `$9,229,410` of `$26,287,474`;
  the town raises the other `$17,058,064`. Both are budget figures from the same
  ledger, so rule 1 is clean.
- **Aid missed its own estimate by `$245,751` in an average year, FY2021–FY2025** —
  and I recomputed the series to the dollar: `+240,260 / +120,947 / +327,281 /
  −390,814 / +149,455`, mean absolute `$245,751`. Over the estimate in **4 of 5
  years**, so the direction is steadier than the size. The one shortfall was 17.2% of
  that year's certified free cash.
- **The state decides both halves of the minimum.** From `ch70-fy27-summary.xlsx`,
  sheet `alldistricts`, row 168 — read directly, not off a rendering:

  ```
  B168 'Lunenburg     '   D168 1599        E168 23,089,579.62
  F168 14,135,611         G168 9,349,335   H168 23,484,946
  F168 + G168 = 23,484,946 = H168     exactly
  ```

  39.8% state share, 60.2% required local — and the identity is asserted before the
  bar is drawn, so the chart cannot render a total that does not foot.

### The finding that matters most, and it is about us

**CLAUDE.md's rule 11 was wrong, and wrong in exactly the way rule 2 exists to
prevent.** It said *"Chapter 70 is roughly $11.4M of a $26.6M school budget"* — a
share near 43%. But `$11,404,917` is the Governor's FY27 figure for **all** state aid
to Lunenburg, the line the Town Manager's press release calls *State aid*, and
Chapter 70 is 78.7% of it. The rest is Unrestricted General Government Aid and other
cherry sheet receipts, none of it school money.

Two real figures, folded together, producing a share eight points too high **in the
document that instructs everyone else never to type a figure into prose.** It has been
corrected, with the error left visible rather than quietly overwritten.

A second error sat beside it: the same paragraph said the model projects *Chapter 70*
separately at 2%. `model/finance.py:84` carries `state_aid=11_404_917 + 471_121` as a
single field, so the 2% applies to the whole cherry sheet, not to Chapter 70. Also
corrected.

### What it does not show

- **The 4.47% is not a correction to the 2%.** Measured Chapter 70 receipts grew
  4.47%/yr FY2014–FY2022, actual to actual, on rows where `status='checked'`. The
  model's 2% applies to total state aid over a forward span. Different quantity,
  different span, different basis — so it is rendered as a *flag*, not a fix. It is
  still the first evidence the archive holds bearing on a rate `show-your-work.md`
  records as `BARE` — "no stated source and no derivation".
- **We hold no Cherry Sheet.** For any year. Every aid figure here is read off a
  ledger, a proof workbook or a DESE file — never off the document that actually
  states the aid. Registered.
- **Whether an aid shortfall falls on the schools or the town is unknown.** The
  −$390,814 year is a fact; who absorbed it is not in anything we hold.
- **Four different pupil counts.** Foundation enrolment is 1,599; DESE's own measures
  give 1,563, 1,568.9 and 1,665.9. They count different things and the page says so
  rather than picking one.

### What the town said (rule 15a)

A FinCom member, 27 January 2026, naming school choice revenue *"declined from
approximately $500,000 to $112,000 on the cherry sheet"* as a precondition for
supporting an override — **a cherry sheet figure we cannot check**, said by somebody
in the room, before we had registered that gap. That is rule 15a earning itself: the
quote and the gap were found by different methods and they are about the same hole.

The School Committee's own *"35% of the entire school budget"* (24 June 2026)
recomputes to 35.11%. The page says so, and would say so if it stopped agreeing.

---

## 5c. `/free-cash` — where the one-time money comes from

**Uncommitted at the time of writing.** **Data**: `free_cash_proof` — the Division of
Local Services' own Free Cash Proof for Lunenburg and eight comparable towns, 630 rows,
2021–2025, out of nine workbooks under `sources/state-dls/`; plus the Town's own
`Undesignated Fund Balance Roll-forward` out of the FY2024 and FY2025 annual reports.

**Extended in place rather than added beside.** `/free-cash` was a policy simulator and
is now a drill-in with the simulator inside it. A second page would have meant a resident
choosing between two free-cash addresses, and "where does this money come from" and "what
can it do" are two halves of one question.

### What the data shows

```
components -> Identified Free Cash July 1,   45 of 45 town-years, to the cent
certified  != identified                     45 of 45 town-years
local receipts above estimate                45 of 45 town-years, all nine towns
```

- **Free cash is mostly two estimating misses, not a saved surplus.** Over five years
  47.4% of Lunenburg's identified free cash is `Add Unencumbered/Unexpended
  Appropriations (CL#11)` — $6,403,120 — and 38.7% is `Excess/Shortfall Local Receipts
  (CL#6)` — $5,234,423. A further 11.3% is `Add Prior Year Free Cash Not Appropriated
  (CL#12)`, which is last year's free cash arriving again, so **five years of these
  totals is not five years of new money**.
- **The estimate has been beaten every single year — and so has every peer's.** All 45
  town-years in the set are positive on CL#6. That is the measurement behind the local
  "we are too conservative" argument, and it is also what a statewide convention looks
  like. The page states both readings and says the data cannot separate them.
- **The record year is an event against its own history, not against the group.** CL#11
  in 2025 is 2.49× Lunenburg's own 2021–24 average, the highest of nine; Upton (0.72) and
  Uxbridge (0.40) fell. On *composition* it is the highest of nine in 2025 (66.1%) but
  sits in a cluster with Townsend at 64.2% and Shirley at 63.7%, and on the five-year mean
  it is second, behind Ayer at 58.5%. The two measures disagree usefully and both are on
  the page.
- **DLS's proof cross-foots exactly, to a figure DLS does not certify.** The eleven
  component rows sum to `Identified Free Cash July 1,` to the cent in all 45 town-years,
  and the chain `Current Year Calculation`(N) = `Free Cash Certified Prior Year`(N+1)
  holds in all 36. But identified and certified differ in all 45 — $361,912 for Lunenburg
  in 2025, 69% for Uxbridge in 2024 — and the workbook prints no reconciling line.
- **Three numbers describe the same balance sheet.** At 30 June 2025 the Town's
  roll-forward gives $4,236,488.24; DLS identifies $3,716,282 and certifies $3,354,370.
  Both worksheets tie exactly to their own printed totals, and FY2024's closing balance
  is FY2025's opening one to the cent. **Neither is wrong and nothing joins them.**

### What it does not show

- **Which departments underspent, or why.** CL#11 is one town-wide figure across 67
  departments. Prudence, a post left vacant, a project that slipped and a line
  over-budgeted from the start are four facts about the world and one number on the page.
  §7 item 13, and now a registered gap.
- **How much of it is the schools'.** Neither publisher attributes a component to a
  department. This is the one a School Committee member arrives with and it is answered
  as unanswerable, early, rather than left for them to discover.
- **Whether the level is unusual.** The proof carries **no denominator** — no population,
  budget, revenue or levy, for any town including ours. So free cash as a share of the
  operating budget cannot be computed for a peer at all, and no dollar figure is compared
  across towns anywhere on the page. Composition and ratios-against-own-history are, and
  the last column of the peer table is captioned *to be read and not compared*.
- **Why the two publishers differ.** An undesignated fund balance and certified free cash
  are not the same quantity — receivables and deferred revenue sit between them — but the
  size of that adjustment is not published and it is not stable: $520,206.24 in 2025 and
  $719,262.80 in 2024.

### Two rule-13 things worth keeping

**`free_cash_proof.source_ref` is the wrong cell, and the page cites the right one.**
`extract_free_cash.py` writes `Sheet1!A<row>` for every year — that is the **label** cell
in column A. The amount for 2025 lives in column F. The generator derives the value
coordinate itself, prints `Sheet1!F10` beside each figure, and **re-opens the workbook to
assert that every one of the 70 cited cells holds the cited amount**. The extract was not
changed; the CSV and the database feed other things, and correcting a `source_ref`
convention is a separate decision. It is written down here and on the page instead.

**The instrument is part of the finding, and there are two of them.** The FY2025
roll-forward is read from the PDF's own text layer; the FY2024 page has none and is read
from the OCR (`sources/town-budget/ocr/...tsv`, page 30, tokens paired label-to-amount by
row). Both are named on the page rather than presented as one source. The printed footers
were checked: FY2024's page prints `30` and the PDF index is 30; FY2025's roll-forward is
PDF pages 31–33 printing 27–29, which is what the report's own table of contents names —
so `annual_report_catalogue` holds the PDF index for FY2025 and they coincide for FY2024.

### The step that only rule 15a produces

`search_minutes.py "conservative"` returned, from Finance Committee minutes of
**28 May 2026**, under an agenda item literally headed *Local Receipts Trends*:

> Ana Lockwood states for the last 10 years the town has not collected less than 4 million
> dollars in local receipts. This year's estimate is 3.535 million. Ana Lockwood suggests
> not being so conservative based on the data.

That is the Finance Committee reaching the CL#6 finding independently, from the town's own
receipts rather than from the state's proof, in the same window. Two routes, one
conclusion, and the page carries them side by side. Also on the page, from **3 September
2025**, the other half a persona review exists to find: *"an unknown surplus of money that
was not spent and instead was given back to the town"*, beside the measurement of what
that surplus actually was. Six quotes in all, each asserted verbatim against its own file
at build time.

---

## 5d. The deploy gate caught a defect three pages of rules had not

Worth recording separately, because it is the clearest case in this project of a
**check earning its keep against a rule that was written down and still not followed.**

`npm run check:agents` refused the v11 deploy with ten problems. Nine were one problem:

> every link to a file must be absolute, or a program cannot follow it

Nine pages linked to `/docs/…`, `/data/…` and `/api/…` as bare paths.

### Why it keeps happening

**A browser resolves a relative path against the page it is on.** So a relative file
link is not merely correct-looking to a human reviewer — it is *indistinguishable from
a working link* to every human who clicks it. It is broken only for readers who cannot
click, and there is no way to notice them by looking.

`model.json` records the two previous occurrences: 100 links across 18 pages, then 13
more. Each time the failure was identical — an assistant was told exactly where the
data was, could not fetch it because its tool only accepts addresses it has seen
written out in full, **reported the data missing from the very page built to hand it
over**, and went to the source repository instead.

### Why the rule did not prevent the third one

The rule existed. It lived as a comment on a local helper inside one component
(`AskAnAssistant.tsx`), and a second copy of the same helper lived in `DataTopLine.tsx`.
So every page built afterwards re-invented the bug, because the rule was not anywhere a
page author would look.

It is now `fy28/src/lib/abs.ts`, derived from `agent-manifest.json` — the same value
`llms.txt`, the footer and the agent prompt read — so the domain is not typed again.

### And the first fix was not enough, which is the more useful half

Rewriting `href="/docs/…"` in the source took ten problems to seven. **All seven
survivors were links that are not literals** — built at runtime out of a JSON field:

```
href={r.url}     href={q.cite}     href={`/${p.replace(/^sources\//, 'docs/')}`}
```

A source-text rewrite cannot see those, and neither can a reviewer reading the diff.
So `abs()` was made **prefix-guarded and idempotent** instead, and applied to every
href regardless of kind: a path under those four prefixes gets the site name, an in-app
route is returned untouched (prefixing one would turn a client-side navigation into a
full page load), and anything already absolute is returned unchanged.

**The generalisable form:** when a rule is about the *value* of something, enforcing it
at the point where the value is written only covers the values that are written. Put
the guard on the value itself and the constructed cases come along for free.

---

## 6. Decisions waiting on TJ

Not questions about the data — questions about what this project should do. Nothing
below is blocked on more analysis; each is blocked on somebody choosing.

| # | the decision | why it is yours and not mine | cost of leaving it |
|---|---|---|---|
| D1 | **Push the database to D1.** Held deliberately. A full replace is ~51,000 writes against a free-tier ceiling of 100,000 a day, and four re-imports took the endpoint dark on 5 September. | It spends a shared daily budget that residents' queries also draw on. | `/api/query` serves the older database. `sync_d1.py --check` fails, and it is the ONLY failing check — so a real failure has nowhere to hide. That is the actual cost. |
| D2 | **Deploy.** Several pages are built, checked and committed but not live: `/what-sports-cost`, `/money-outside-the-budget`, and whatever the state aid and free cash agents land. | Rule 10 — nothing deploys without being asked. | Residents see the previous build. Everything is tagged, so the decision is reversible. |
| D3 | **Resume the tax-rate and town-meeting extraction, or drop it.** Held after repeated `ECONNRESET`. Your instruction was to hold if the agents keep failing and continue if some make progress. | The balance-sheet and special-revenue extractions since then both succeeded, so the evidence has changed. | Two datasets stay uncaptured. Nothing else depends on them. |
| D4 | **What to do about `athletics.md` being stale.** `/what-sports-cost` renders three disagreements with it rather than reconciling them, because commit `07aa298` withdrew three FY2024 rows and the analysis predates that. | Editing a published analysis moves its sha256, its PDF and its `reports.json` entry — and somebody may have quoted it. | A resident who reads both sees two different numbers for FY2024 athletics. The page explains why; the analysis does not. |
| D5 | **Extract the FY2024/FY2025 enterprise-only combining balance sheets as a new dataset.** They cannot extend the combined series — different table — so this is a decision to start something, not to finish something. | It is scope, and enterprise funds are ratepayer money rather than tax money. | Two years of enterprise fund positions stay unread. |
| D6 | **The PEG revenue-vs-expenses statements**, ~11 editions with a real cross-check. Same shape of decision as D5, and the cross-check makes it the better bet of the two. | Scope. | Same. |
| D7 | **Send a records request.** The gaps registry now names specific documents rather than describing absences — the FY2023 trial balance, the five athletics memos, the `Account_Detail` export for orgs S3066672/S3066671, DESE's End of Year Financial Report. That is a letter, not a list. | It is outbound, to the Town, in your name. | The gaps stay gaps. Several are load-bearing. |
| D8 | **Audit the other extracts for the parenthesised-negative defect.** `sped_para_history` was wrong by $315,772 in FY2024 — twice the line, because a sign error doubles rather than zeroes. Fixed there; not looked for elsewhere. | It is unbounded work with an unknown yield, which is exactly the kind of thing to decide rather than drift into. | Unknown. That is the argument for doing it. |
| D10 | **Whether to re-derive the model's 2% state-aid rate.** It is recorded as `BARE` — no stated source, no derivation — and measured Chapter 70 receipts grew 4.47%/yr FY2014–FY2022. The two are not comparable (different quantity, different span, actual-to-actual vs forward), so this is not a bug report; it is a question about whether to go and build the comparable series. | Changing a projection rate moves every published figure downstream of it, and rule 14 says a correction that size makes *other* errors findable. That is a decision with a workload attached. | The rate stays unsupported, and the site keeps saying so honestly. Not urgent. |
| D11 | **Fix `source_ref` in `extract_free_cash.py`.** Every one of the 630 rows in `free_cash_proof` cites `Sheet1!A<row>` — the **label** cell in column A. The amounts are in another column (`Sheet1!F17` for Lunenburg 2025). So every provenance coordinate in that table points at the wrong cell: right row, wrong column. Confirmed directly — `Sheet1!A5` is recorded for a figure of `3,354,370`. | The CSV and the database feed other things, so re-extracting is a change with a blast radius, and the free-cash page already works around it by deriving the value coordinate itself and re-opening the workbook to assert all 70 cited cells. | Rule 12 says a figure is only checkable if somebody can get back to it. A citation that resolves to a label is a citation that fails exactly when somebody tries to use it — which is to say, never in testing. |
| D9 | **Whether `held` is the right fourth side** in the gaps registry, alongside `money_in`, `money_out`, `people` and `document_wanted`. Added for the balance-sheet gap: money the town is holding is genuinely neither in nor out. | A taxonomy is an editorial choice and it renders on a public page. | Nothing breaks. Sides are read off the data, so changing it is a CSV edit. |

## 7. Open questions — the data ones

These do not resolve by choosing. Each needs a document, and each names the one that
would close it. All are registered in `sources/data/money-gaps.csv` unless marked.

**Load-bearing, in the sense that other conclusions rest on them:**

1. **Which fund pays which post.** The in-district special education escalator is built
   on a paraprofessional line, and that line cannot be distinguished from grant money
   unwinding. This is the single most consequential unknown in the project.
   *Closes:* DESE's End of Year Financial Report, which separates spending by fund.
2. **Whether a general fund athletics line is net of the revolving fund.** Rule 11's
   problem at its sharpest, on the one programme where both sides are visible.
   *Closes:* the MUNIS `Account_Detail` export for orgs S3066672 and S3066671.

**Specific and probably closeable:**

3. **What the $87,293.86 is.** Two tables in the FY2023 annual report state the same
   quantity and differ. Not a misreading — the page ties to itself in all six columns.
   The `Sale of Cemetery Lots` explanation is tested and dead (§4 above).
   *Closes:* the Town's FY2023 trial balance as of 30 June 2023.
4. **The residual $14.23** inside that. No FY2023 fund carries it, positive or negative.
   Probably not independently meaningful, but it is unexplained and unexplained is the
   honest word.
5. **Whether the $87,293.86 is connected to the $17,861.24** the town restated in grant
   funds between the FY2022 and FY2023 reports. Two different amounts in the same year.
   *Nothing joins them* — that is a statement about the evidence, not a denial.
6. **What the four `GEN` journal entries moved.** $254,121.18 into fund 1301 in FY2025,
   two thirds of the year's inflow, described in the ledger only as *per memo*.
   *Closes:* the five memos.
7. **FY26 year-end.** Everything held for FY26 stops at 31 March.
8. **What any Cherry Sheet actually says.** We hold none, for any year — every aid
   figure in this project is read off a ledger, a proof workbook or a DESE file rather
   than off the document that states the aid.
   *Closes:* DLS forms CS 1-ER and CS 1-EB for Lunenburg, FY2021–FY2027.
9. **Whether an aid shortfall lands on the schools or on the town.** FY2024 came in
   $390,814 under estimate. Who absorbed it is in nothing we hold.
   *Closes:* the fiscal-year-end recap (Form A-1), beside the Cherry Sheet.
10. **How many children Chapter 70 is paid for.** Foundation enrolment is 1,599; DESE's
    own measures give 1,563, 1,568.9 and 1,665.9. Four counts of four different things.
    *Closes:* DESE's FY27 foundation enrolment worksheet.

**Bounded rather than answerable:**

11. **How many children play sports.** Two town documents give 593 and 649 for the same
   year and count different things. No unduplicated count is published.
12. **Whether the fee rises moved participation.** Fees +30%, participations −3.9%, over
   exactly the same years. This is not a data gap that a document closes — it is a
   causal question the data cannot carry, and I do not expect it ever to. Listed so that
   nobody re-opens it thinking a records request would settle it.
13. **Whether a large CL#11 is prudence, a hiring freeze, a slipped project or an
    over-budgeted line.** Relevant to the free cash page in progress; the components do
    not distinguish them.

## 8. How to use §6 and §7

The distinction is the whole point of keeping them apart. **§6 items go stale** — a
decision not taken is a decision taken by default, and D1/D2 in particular decay into
"the site is out of date and nobody chose that". **§7 items do not go stale.** They are
correctly parked, they are published on `/what-we-cannot-answer`, and the honest state
of a §7 item is open.

The failure mode to avoid is treating a §7 item as if it were a §6 one — deciding what
the $87,293.86 probably is, rather than asking for the trial balance. Rule 7 exists
because that conversion happens quietly and reads like progress.
