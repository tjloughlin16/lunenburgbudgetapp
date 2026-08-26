# The Lunenburg Budget Project

lunenburgbudgetproject.org — an independent, checkable look at the Lunenburg
Public Schools budget: how big the FY28 gap is, why it comes back every year,
and the combinations that would actually keep it shut. Not affiliated with the
Town of Lunenburg, the School Committee or the school district.

An interactive projection of the Lunenburg Public Schools budget for FY28 and the four
years after, built for residents. Set your own priorities, then see where the cut line
falls and what year each program is lost.

```bash
npm install
npm run dev              # http://localhost:5173
npm run build            # -> dist/         multi-file build, for hosting
SINGLE=1 npm run build   # -> dist-single/  ONE self-contained .html, opens offline
```

**Sharing it.** `SINGLE=1 npm run build` inlines the JS, CSS and data into a single
~820KB HTML file that runs by double-click, with no server and no internet. A plain
`dist/` build will *not* open from `file://` — browsers block ES modules over that
protocol — so use the single-file build for anything you email or hand over.

## What this is

FY27 was adopted at the "Balanced" level after voters rejected both override questions
on 16 May 2026 (33% and 29% yes). There is **no FY28 budget yet** — that work begins in
January 2027. Everything here after FY27 is a model.

The model does three things:

1. **Projects the gap.** Grows the FY27 adopted budget by cost category (salaries, health
   insurance, transportation, out-of-district tuition, utilities, other) and grows revenue
   using the Town's published Proposition 2½ formula.
2. **Ranks what gets cut.** A catalog of 55 discrete programs, each with a cost, a staffing
   figure, a category and a mandate status. Users rank the categories; the engine cuts from
   the bottom up until each year's gap closes. Legally mandated items are skipped, not cut.
3. **Compounds it.** A cut permanently lowers the salary base, so it also lowers every later
   year's cost — which is why early cuts matter more than they look.

## Layout

| Path | Purpose |
|---|---|
| `src/model/engine.ts` | `project()` and `runCascade()` — the whole model |
| `src/data/model.json` | Generated data: catalog, presets, FY27 constants, published facts |
| `src/components/CutLine.tsx` | The slider and the ranked program list |
| `src/components/PriorityBuilder.tsx` | Category ranking + presets |
| `src/components/YearChart.tsx` | Cost vs revenue, FY28–FY32 |
| `src/components/Timeline.tsx` | Year-by-year cut lists and "the year each thing is lost" |
| `src/components/Assumptions.tsx` | Every growth rate and lever, editable |

## Regenerating the data

The JSON is generated from the repo root, not from here:

```bash
cd ..
python3 scripts/extract_lps_budget.py   # xlsx -> sources/data/lps-budget-lines.csv
python3 model/export.py                 # -> fy28/src/data/model.json
python3 model/finance.py                # print the projection
python3 model/cascade.py school_committee   # print a cut cascade
```

`model/finance.py` and `src/model/engine.ts` are parallel implementations and are checked
for exact parity. If you change one, change the other.

## Headline metrics (`model/headlines.py`)

Six numbers at the very top, assembled from the other modules rather than typed in, so the
banner and the conclusions cannot drift apart. Change a growth rate and all six move.

## Health insurance (`model/health.py`)

Real premiums from the Town's July 2026 rate sheet, at the published 75/25 split. Two
concrete levers — shift the contribution split, or move employees to a cheaper plan — each
showing the district saving *and* what it costs a family per year. Year-one saving is 75%
of headline because M.G.L. c.32B §§21-23 requires 25% of first-year savings go back to
employees as mitigation.

Default enrolment (194 across four plans) is calibrated so the town's 75% share reconciles
to the $3,994,071 school health line, within 0.1%. The plan *mix* within that total is an
assumption and is flagged as such in the UI.

## Local peer comparison

Six North Central Massachusetts districts, all from their own published FY27 budgets
(`../sources/peers/`). The headline: Lunenburg's schools grew **1.08%** while neighbours
grew 2.9%–6.5%, against health insurance up 8–14% and Chapter 70 up 1.5–2% everywhere.

Ashburnham-Westminster is the key contrast — it wrote "preserve athletics, arts and
music" into its district goals and cut two elementary teachers to honour it. Lunenburg
did the opposite. That is the clearest evidence that the ranking in this tool is a real
choice, not an arithmetic result.

Data lives in `model/peers.py`; edit there and re-run `model/export.py`.

## Fees, levers and the recommendation

Three later sections model everything *other* than cutting programmes:

- **Fees & self-funding** (`components/Athletics.tsx`, `components/FeeCurve.tsx`) —
  per-sport costs and participation from the district's own "Athletic Program Costs by
  Sport": 691 participations across 25 sports.

  **Lunenburg already charges fees.** Athletics is $250/$140/$85 per season with a $475
  family cap ($200/$150 middle school); buses are $180/year with a $270 family cap. So
  every fee lever models the **increment above today's fee**, not a fee from zero, and
  drop-off is applied to the *increase* rather than the absolute fee.

  Revenue is **non-monotonic** in the fee — it rises, peaks, then falls as families are
  priced out. Do not replace the scan in `feeFor` with a bisection; bisection is wrong on
  this curve and silently returns "unreachable" for everything. `FeeCurve` plots the whole
  curve with the peak and the programme-cost line, and the y-domain deliberately includes
  the target so the shortfall is visible.

  Result: **full self-funding is unreachable for athletics and buses.** Athletics peaks
  near $1,105/season raising ~$371k against a $452k programme; buses peak near $715 raising
  ~$146k against $1.05M of general-education transport.
- **Close the gap** (`components/Levers.tsx`, `model/levers.py`) — athletics/activity/bus
  fees, health-insurance plan design, administration reduction and technology cuts, each
  with a running total against the FY28 gap and an honest caveat.
- **What we'd do** (`components/Recommendation.tsx`, `model/recommendation.py`) — our own
  package. Finds ~$415k of the $613k gap without cutting a programme; the rest is an
  override or classroom positions. Reasoning is in the module docstring.

Key figures: all administration $2,633,246 · technology $638,675 · health insurance
$3,994,071 · general-ed transport $1,053,360 (special-ed transport cannot be charged for).

## The revenue side (`model/taxbase.py`, `components/TaxBase.tsx`)

A section on business growth as an alternative to overrides. Three parts:

1. **Tax structure** — $2.489B taxable value, 91% residential, single rate $14.39.
   Explains the Prop 2½ paradox: rising assessments do *not* raise revenue, because the
   rate falls to keep the levy under the cap. Only new growth adds to the limit.
2. **Growth calculator** — new commercial value per year → revenue now and in ten years,
   expressed in buildings via labelled archetype estimates. Charts business growth against
   an override of the same size; at $15M/yr of new value, growth overtakes a $613k override
   in **year 3** and keeps compounding.
3. **Residential paradox** — local cost per pupil is $10,894 after Chapter 70; the school
   share of an average tax bill is $3,959. So one child needs the school taxes of **2.75
   average homes**, and a two-child house runs about **−$17,800/year**. A commercial
   building of equal value pays the same and sends nobody.

Archetype assessed values are our order-of-magnitude estimates, not Lunenburg assessments,
and are labelled as such in the UI. The model counts commercial revenue but not the
municipal costs commercial development brings.

## Business registrations (`model/business.py`)

Reads the Town Clerk's business certificate records (copied to `sources/business/`) to
answer whether businesses are actually leaving. They are not — the surprise is that
formation is healthy while commercial building is not. Regenerate with `model/export.py`
like everything else.

Watch the coverage window: certificates run four years, so pre-2018 data is incomplete and
the current year is partial. `FORMATION_HISTORY` starts at 2018 and flags the partial year.

## Priority presets

- **School Committee's revealed priorities** — the order Lunenburg itself gave things up
  across its four published FY27 scenarios.
- **What comparable districts actually do** — the observed sequence in Easthampton,
  Bridgewater-Raynham, South Hadley, Groton-Dunstable, Winchester and Duxbury.
- **Academics above all** — protect instruction at any cost to everything else.

## Sources

See `../sources/` — `MANIFEST.md` lists every document, `FINDINGS.md` is the research
write-up, `PEER-PRECEDENT.md` covers what other districts did.

## Caveats to keep visible

- Programs marked *our estimate* (the AP catalog, the high school music program, middle
  school electives, guidance and social-work reductions) are **costed by us**. The district
  has not published prices for cutting them.
- The cut order is a model, not a plan. Nobody has decided any of this.
- The $453,722 restored at the September 2026 Special Town Meeting is one-time money.
  Carrying it into FY28 is treated as a new cost, because it is.

Not affiliated with, endorsed by, or approved by Lunenburg Public Schools or the Town of
Lunenburg.
