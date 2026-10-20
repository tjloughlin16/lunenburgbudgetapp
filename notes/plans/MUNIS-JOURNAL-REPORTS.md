# Plan: every report the school MUNIS journal can carry

Started 19 October 2026. **This is the tracking document for the whole journal workstream:**
what gets built, in what order, and where each piece stands. Update the status table in the
same commit as the work it reports, never from memory (rule 2 applies to a status column too).

TJ, 19 October 2026: *"lets create a section that will likely be a FEW HUBS of interrelated
reports.... i cant imagine we can do a single hub or even a single report."*

## What the journal is, and why it supports reports nothing else here can

`sources/data/munis-school-journal.csv`: every posting behind every school account, **general
fund and every school special fund**, FY2023 p0 to FY2026 p13, with payee, date, source code,
purchase order and description. `munis-school-journal-accounts.csv`: the 3,356 accounts with
the totals the report prints. Both are our redacted reading of the Town's Report 1
(`scripts/extract_munis_school_journal.py`; the raw is private, see `redactions.csv`).

The town and district publish totals by line, general fund only. The journal has
**postings, across all funds, with the payee and the date**. Every report below asks a
question only that combination answers.

**The redaction principle the data is published under** (TJ, 19 October 2026): *"remove
ANYBODY who is directly named as a parent or child getting services from the school. anybody
contributing to those services as vendors should be ID'd. It's not NAMES that I'm worried
about. It's associating a name to a disability."* Providers are named; recipients are not. No
report may re-derive a masked recipient. Aggregates are fine, but a breakdown that isolates
one masked family or child is not.

## Phase 0: the gate. Nothing below starts until all of this is done

| step | state |
|---|---|
| Extractor redaction fixed to TJ's principle, three privacy reads plus a final read | **done** 19 Oct: final read found nothing confidential visible; last round checked as a diff |
| Clean CSVs back in `sources/data/`; `fy28/public/docs/data/` copy | **done** `2ee126b2f` |
| `redactions.csv` row names our CSV as the public copy (`public_key`, `public_sha256`) | **done** `2ee126b2f` |
| `build_db.py` loads the tables (with `name_basis`); `describe_data.py` semantics for both tables | **done** `2ee126b2f`; the hold guard in build_db stays, harmless |
| `build_source_index.py` catalogue entries committed with the CSVs | **done** `2ee126b2f`; `sources.json` not regenerated in git (other agents' entries mixed in) |
| Committed by path; D1 picks it up on the daily refresh (never `sync_d1.py` by hand) | committed; D1 waits for the refresh |
| History rewrite of the unpushed range before any push (see memory: open items 19 Oct) | waiting for the other agents to pause |
| The **journal data page**: grain, sources, the redaction rule, what it cannot show | not started |

**Settle before any report** (each changes figures in several reports). SETTLED 19 October
2026, each by measurement; `journal.py` and `/analysis/school-journal` carry the answers:
- **Payroll grain: one line per ACCOUNT per pay run, never per person.** All 9,564 `PRJ`/`PRH`
  lines have an empty vendor and invoice and a `WARRANT=<n>P<yy>` description, and no account
  carries two `PRJ` lines in one journal. 35, 33, 31 and 36 pay runs posted FY2023-FY2026.
  So there is no person to mask, and payroll dollars are still not staff (rule 7).
  `journal.PAYROLL_GRAIN`.
- **The FY2026 close** is not posted in this run (encumbrances still open). Every FY26 figure
  that depends on it says so (`journal.OPEN_FY`).
- **Open FY26 purchase orders: both figures are right, for different scopes.** The journal's
  general fund holds $246,766.94 open in 28 accounts; $10,000.00 of it is one account in
  department 301 (org 13012, CURRICULUM ADOPTION). Department 300 alone, the scope of the
  period-13 spreadsheets, holds $236,766.94 in 27 accounts. Not a typo.
- **Org 13012 belongs in the school general fund, as the district states its own budget.**
  Department 301's FY2026 original budget is $40,000, and department 300's is $26,247,474;
  together they are $26,287,474, which is exactly the district's own printed "Total FY26
  Budget" (LPS FY2027-2029 projections deck, slide 38, `fincom-presentation-tables.csv`; and
  "TOTAL ACTUALS & BUDGET" in the FY27 proposed budget document). The School Committee voted a
  $4,222.59 line-item transfer out of "the curriculum adoption line" on 17 September 2025
  (`board-transfers.csv`), and the journal posts it on 13012 (`BUA`, PER MEMO 09/18/25). At
  the run, 13012 had revised $35,777.41, actual $43,639.08, encumbered $10,000.00, available
  -$17,861.67. So the FY26 surplus including it is $482,118.07 - $17,861.67 = $464,256.40
  (before the close). Hub B decides how to show it; `fy26-school-surplus` (dept 300 only) is
  correct for its stated scope and should say that 13012 is outside it.

## The hubs

Five shelves. Two exist and gain topics; three are new. A topic lives at ONE address
(`/<home>/<id>`) and is listed on every shelf it belongs to (`scripts/topics.py`: a group may
list a topic another category is home to). Titles are 2–4 word nouns, never sentences or
questions; the finding is the line under the title.

Every topic page carries: one question, one chart (component, never an image, rule 7f),
two to four conclusions, each a **comparison** (`notes/process/AUDIT-PASS.md`), its sources,
and its limits registered in `money-gaps.csv` (rule 7c). Each generator emits a payload
through `scripts/conclusions.py`, and a verifier recomputes every figure by a second route
(rule 9).

### Hub A: Special education money, at the journal level. EXTENDS `special-education`

TJ: *"knowing exactly how we pay out special education, and which parts of the costs are
rising each year will be critical, at the journal level."*

The existing hub has out-of-district tuition, the circuit breaker and in-district cost from
budget documents. The journal adds who is paid, from which fund, and which components are
rising. New group on that shelf: **Who is paid, and from where.**

| id | title | the question | signature |
|---|---|---|---|
| `sped-all-funds` | Special education, all funds | What special education costs across general fund, circuit breaker, IDEA and other grants, by year | stacked bars by fund, FY23–FY26 |
| `sped-providers` | Special education providers | Who is paid for special education services, how much, and how that changed | a block per provider, split by paying fund |
| `sped-cost-growth` | Rising special education costs | Which components (tuition, transport, contracted services, therapies, evaluations, in-district pay) grow fastest, year to year | small multiples, one per component, growth called out |
| `sped-fund-shifts` | Costs moving between funds | Where a cost left one fund and appeared in another: grants taking over or ending; the circuit breaker's share | paired lines per cost, by fund |
| `sped-contracted-services` | Contracted therapy and services | Contracted related services and evaluations by provider; how far past budget, every year | bars, budget vs actual, by year |
| `sped-transportation-journal` | Special education transport | Contract carriers vs family mileage (totals only), by month and year | monthly bars, two series |
| `out-of-district-providers` | Placements by provider | Tuition by school/collaborative over time, general fund plus circuit breaker | a line per provider |

Leads to TEST, not state:
- the kindergarten/special ed aide payroll moving accounts in FY26 with no budget transfer recorded (this bears on the escalator in `finance.py`);
- the circuit breaker's year-end tuition reclassification;
- a psychologist salary line paying nobody while a contracted psychologist is billed.

The standing question this hub is aimed at (CLAUDE.md, *the standing questions*): **how
grants and state funding map onto the budget lines.** Say plainly how far the journal
settles it and what stays unsettled: town-side benefits are not in a school journal.

### Hub B: The surplus bridge. EXTENDS `fy2026-closeout`

TJ: *"surplus bridge is what the town manager thinks Im using this all for, so this is
critical."* Full method in `notes/plans/SCHOOL-SURPLUS-BRIDGE.md`; the topics it produces:

| id | title | the question | signature |
|---|---|---|---|
| `surplus-bridge` | Surplus, step by step | FY25 → FY26: the surplus split into budget changes, payroll, vendors, reclassifications, open POs, money moved to other funds | waterfall |
| `surplus-repeat-lines` | Under budget twice | Categories under budget in both FY25 and FY26, and what was not spent in each | ranked bars, two years side by side |
| `surplus-payroll` | Unspent salaries | Salary lines under budget: when the payroll stopped or shrank, and whether it moved to another fund | monthly lines per account |
| `open-purchase-orders` | Open purchase orders | What was still committed at year end, to whom, opened when, and how firm it looks | table sorted by firmness |
| `year-end-close` | How the year closes | June POs, June reclassifications and year-end transfers, compared over four years | share of each year settled in June |

### Hub C: School vendors. NEW category

TJ: *"knowing who we pay and how much is critical."*

| id | title | the question | signature |
|---|---|---|---|
| `school-vendors` | Who the schools pay | Every vendor, four years, ranked; a resident can look one up | treemap by category |
| `vendor-concentration` | Largest vendors | How much of spending goes to the few largest payees, and whether that is growing | top-N share over time |
| `vendor-changes` | New and departed vendors | Who appeared, who stopped, who grew fastest | slope chart |
| `vendor-lookup` | Vendor lookup | Search any payee: every payment, account and fund (shown payees only) | searchable table |

### Hub D: School funds, beyond the budget. NEW category

The all-funds view: every special fund the schools run, and what it pays for. TJ also wrote
*"who pays the schools"*, which this hub answers from the money-IN side: grants, fees, the
circuit breaker, school choice, gifts.

| id | title | the question | signature |
|---|---|---|---|
| `school-funds-overview` | School special funds | Every fund: receipts in, spending out, balance, FY23–FY26 | one row per fund, small multiples |
| `grant-funded-costs` | What grants pay for | Grant spending by object (salaries, services, supplies); which salary accounts are grant-paid | stacked bars by grant |
| `revolving-funds` | Fee-funded programs | Extended day, athletics, lunch, after-school: fees in vs costs out, including benefits charged to them | in/out bars per fund |
| `benefits-on-funds` | Benefits charged to funds | Health insurance and other benefits paid from revolving funds rather than the general fund | bars by fund |
| `school-choice-money` | School choice money | School choice receipts and what they paid for | in/out |
| `gift-and-scholarship-funds` | Gifts and scholarships | Gift funds and scholarship awards by fund and year | bars by fund |

### Hub E: transport and other existing shelves. TOPICS LISTED, not new hubs

Journal-level topics that belong on shelves that already exist:
- `transportation`: `bus-contract-payments` (Dee Bus / Van Pool by month and year, against the contract).
- `health-insurance`: `school-health-postings` (MIIA by fund, invoices vs June reclassifications).
- `athletics`: `athletics-journal` (the athletics revolving fund, all postings, cross-checked against the fund 1301 cashbook).

## Cadence: one or two at a time, TJ reviews each

TJ, 19 October 2026: *"we can roll out maybe 1 or 2 reports at a time, ill check, then we
can go though the full plan... lets not do them all at once."*

Build one or two topics, stop, and hand them to TJ to review: the payload, the page
rendered locally, and its verifier passing. The next pair starts only after he has looked.
Nothing deploys without being asked (rule 10). What he says in review feeds back into
this plan before the next pair, because the first pages will set the pattern the rest
follow.

## Build order

1. **Phase 0** (the gate) and the **journal data page**.
2. **Hub A**, starting with `sped-all-funds` and `sped-providers`. Most of the rest of A, and
   much of B and D, reads from the fund-by-object rollup these build.
3. **Hub B**, the surplus bridge.
4. **Hub C**, vendors.
5. **Hub D**, funds.
6. **Hub E** topics.

**Shared code, built once** (memory: *no corner cutting*): `scripts/journal.py` (BUILT
19 October 2026; the extractor now imports `COLUMN_OF` and `SPED_ACCOUNTS` from it, and its
`--check` still reproduces the published CSVs byte for byte), holding:
- the journal loader;
- the source-code classes (actual, encumbrance, budget, reclass);
- the fund and object rollups;
- the special-ed account/fund list (the same list the extractor's redaction uses: ONE
  definition);
- the vendor normaliser (`T COONEY` = `TINA COONEY`, but only for shown payees).

Every generator imports it. A second copy of any of these is a defect.

## Rules that bite here

- **Postings are facts; reasons are hypotheses** (rule 7). "Payroll on this line stopped in
  November" is a fact; "a teacher left" is a hypothesis.
- **Every line is net** (rule 11). The all-funds view narrows the gap; it does not close it.
- **Budgets and actuals stay separate** (rule 1). An actual here may test a model rate; it
  never feeds one.
- **Persona review and a minutes search** for every finding before publishing (rules 15, 15a).
- **No report may isolate a masked recipient**: no breakdown fine enough to point at one
  family or child.

## Status

One row per topic. States: `not started` → `generator` → `verified` → `reviewed` (personas
plus minutes) → `built` → `deployed`.

| hub | id | state | commit | note |
|---|---|---|---|---|
| 0 | gate (Phase 0) | data published `2ee126b2f` | | history rewrite + data page left |
| 0 | journal data page | generator | | `/analysis/school-journal`, UNLISTED; `build_school_journal.py --check`; awaiting TJ |
| A | sped-all-funds | verified | | `build_journal_sped_topics.py`; `verify_journal_sped_topics.py`; persona/minutes review and TJ next |
| A | sped-providers | verified | | same generator and verifier; FLLAC labelled FLLAC (Keystone) via journal.ALIASES (correction, TJ 19 Oct: an earlier "never named in the minutes" was a search for the wrong name, rule 13c). Keystone minutes and the Keystone reports in district-budget/docs/sc-meetings read; FinCom 2024-03-14 quoted; none gives Lunenburg's own count |
| A | sped-cost-growth | not started | | |
| A | sped-fund-shifts | not started | | |
| A | sped-contracted-services | not started | | |
| A | sped-transportation-journal | not started | | |
| A | out-of-district-providers | not started | | |
| B | surplus-bridge | not started | | method: SCHOOL-SURPLUS-BRIDGE.md |
| B | surplus-repeat-lines | not started | | |
| B | surplus-payroll | not started | | needs payroll grain |
| B | open-purchase-orders | not started | | settle the $10,000 |
| B | year-end-close | not started | | |
| C | school-vendors | not started | | |
| C | vendor-concentration | not started | | |
| C | vendor-changes | not started | | |
| C | vendor-lookup | not started | | |
| D | school-funds-overview | not started | | |
| D | grant-funded-costs | not started | | |
| D | revolving-funds | not started | | |
| D | benefits-on-funds | not started | | |
| D | school-choice-money | not started | | |
| D | gift-and-scholarship-funds | not started | | |
| E | bus-contract-payments | not started | | |
| E | school-health-postings | not started | | |
| E | athletics-journal | not started | | |

## Cost

Building is session work: judgement about what each page means. Ingest-type work, like
reading OCR or bulk classification, has no place here (rule 7g), since the data is already
extracted. Quote each hub's build in % of the week before starting it.
