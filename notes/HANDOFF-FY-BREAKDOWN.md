# Handoff: one fiscal year, broken down -- why a surplus happened

## REBUILT AROUND THE LINE TABLE, 27 October 2026. Still hidden (draft), not deployed

TJ cut everything below the table ("those charts dont help"): the alluvial, the pool, the moves
timeline and the category table are gone, components and generator code with them. The page is
now: the line table (two sums; re-charges apart from money other funds paid from the start;
each line opens a popup -- Summary, Expenses with every row and who paid, Analysis by week,
payee and memo, from /data/fy-breakdown/lines-<year>.json), then `fy-year-weeks`, every week of
the year across every line. Companion page: /fy2026-closeout/fy2026-circuit-breaker (registered,
on the shelf). Vocabulary settled with TJ: "re-charged", never "moved" (a re-charge sends the
BILL to another fund; no money goes into it).

## SHELVED, 26 October 2026 (late). HIDDEN, NOT RELEASED. TJ is taking a different approach

TJ, after reading it: *"im struggling to undersand this ... and how it helps undersand the
moves"*, then: *"lets put this page into a hidden section where we wont release it."* The page is
built as a DRAFT (`draft=` in `build_fy_breakdown.py`), so it is on no shelf, not in topics.json,
not in the sitemap and not prerendered; the address /fy2026-closeout/fy2026-breakdown still opens.
Model, verifier and components are kept; `check_generated.py` still runs both.

**Why it did not land, in one line:** it opened on the all-funds identity (other funds paid
$1.6M toward the lines, voted $1.0M below cost), which is mostly STRUCTURAL -- fee funds paying
their own staff's insurance every year -- and it buried the part that changed between years: the
moves. What finally made sense in conversation was one table, measured from the journal:

| | FY2025 | FY2026 |
|---|---:|---:|
| left, as reported (owed counted) | $554,945 | $482,118 |
| bills moved between the school budget and other funds | $253,382 onto it | $366,899 off it |
| next year's tuition paid early | none | $189,277 |
| last year's orders never paid | $38,354 | $41,377 |
| left before those moves (our arithmetic) | $769,973 | $263,119 |

Run the model before quoting any of it (rule 2). TJ declined rebuilding the page around it.

## BUILT, 26 October 2026 (night): the data, the identity, the verifier, the alluvial. Not committed, not deployed

- `scripts/fy_breakdown.py`: the model. The identity closes to the cent on every line, every year;
  owed footing (FY2023 $32,022 / FY2024 $31,705 / FY2025 $554,945 / FY2026 $482,118 -- run it, do
  not quote this line). Both worked cases reproduce. Match rules a/b/c are declared in its docstring,
  with two decisions made here: CAPITAL ARTICLES are matched only by journal entry (by payee they
  pulled ~$818k of HVAC work onto operating lines); a cost moved BACK onto the general fund is left
  with its own account (IDEA's aide payroll on fund 2813 is function 0000, unmatched -- placing the
  move-back on the aide lines made a phantom negative).
- `scripts/verify_fy_breakdown.py`: own CSV reader, shares only `category_of`; ties every line to
  the period-13 `available_budget` less next July's SOY, and the alluvial's columns to every school
  expense dollar. Power-tested three ways (shifted term, one cent, broken prepay rule): all fail it.
  Found one real defect while being written: placed money on a line with no postings that year was
  silently dropped ($48,910 in FY2026). Fixed in both routes; the model now asserts it.
- `scripts/build_fy_breakdown.py` -> `/fy2026-closeout/fy2026-breakdown`, "Surplus in four parts":
  alluvial (`fy-alluvial.tsx`, `?block=tuition` opens on one block), waterfall of the four parts,
  4 conclusions with meanings, 12 facts, the four-way table by category with a tab per year. In
  `check_generated.py`. Phone width checked (400px, clean). Registry: lead group of the shelf.
- money-gaps: new last row (which line a grant dollar pays toward; closes: DESE-approved grant
  budgets, End of Year Financial Report). Public copies not regenerated (refresh does it).
- ALSO BUILT (same night, TJ: "build everything you planned"): `fy-pool` (under lines -> one pool
  -> over lines + left; no line-to-line edges), `fy-moves-timeline` (transfers / fund moves /
  money crossing years, July-June, the Town's memo on each), `fy-line-table` (every line, sortable,
  each opening on its own waterfall and its payers with the matching rule; unmatched money listed).
  All three carry FY2023-FY2026 tabs. The payload is ~950 KB, mostly the line table. Waiting on
  TJ's comparison against what he thinks will reveal the most.

Written 26 October 2026 (late), for a FRESH session. Load the `building-a-page` skill first,
then read this file, then `notes/HANDOFF-SURPLUS-PAGES.md` (the surplus work this grows out of).

## What TJ asked, in his words

> *"a lot of money moves in and out of the school budget. and from a lot of sources. generally
> speaking, how can someone actually say why a surplus happened? moving costs into general fund
> and out of grants muddies the water and makes it hard to find the true causes here. there HAS
> to be a way to see why they had leftover money."*

> *"im struggling to truly understand the surplus ... the only answer i have right now is 'its
> too complicated to understand why we have a surplus', but it feels like the shell game"*

He pictured: a single page per fiscal year, from the ledger, journal and budget, showing what
was spent, from which source, onto which function code, and where money was NOT spent; a
timeline of transfers; and "a node graph where money is moved from one bucket to another".

**The job of the page is to replace "it's too complicated" with four numbers.** Not to say
anybody played a shell game (rule 8: the effect on the figure, never intent). The concept that
makes it feel like one is FUNGIBILITY: inside one appropriation a dollar left on one line pays
for another, and a cost moved between funds changes what a line shows without changing what
anything cost. The page has to make that movement visible, which is what dissolves the feeling.

## The method: an identity, not an estimate

For every general fund line (and so for the year, by summing):

    left on the line  =  (voted - all-funds cost)        budgeted above or below what it cost
                      +  transfers in, less out          budget moved between lines (BUA)
                      +  paid by other funds             grants, circuit breaker, revolving, reclasses
                      -  paid this year for another year prepayments; carried orders (SOY/YEC/POE)

It is accounting arithmetic: GF spend = all-funds cost - other funds' share, and left = voted +
transfers - GF spend. Every term is measured off the journal, so the four totals sum to the
surplus to the cent or the build fails.

**Worked test case the page MUST reproduce (FY2026 private tuition, 535019):** voted $988,630;
all-funds cost $753,109 ($466,001 GF + $287,108 IDEA grant fund 2814 to May Institute);
transfers $0. So (988,630 - 753,109) + 0 + 287,108 = **$522,629**, the line's printed
available. 45% budgeted above cost, 55% a change of payer.

Second test case (collaborative tuition, 535023): the 29 June reclass of $333,494.89 to fund
2640 is "paid by other funds"; the 30 June $189,276.75 on `27L2KEY` invoices is "paid this year
for another year". Both are on /fy2026-closeout/fy2026-tuition-paid-early; tie to it.

## The hard part: "the same thing" across funds

**Function codes alone do not join the funds.** The IDEA grant booked May Institute's tuition as
CONTRACTED SERVICES, not tuition (/school-all-funds/grant-coding documents that FY2025 grants
moved off the teaching headings). A function-code view would have shown "grant spent on
services, tuition came in under" and never connected them. So "all-funds cost of a line" needs:

1. **Payee match first, for invoices** (`API`/`APM`, vendor present): a payee paid from the GF
   line in any year, paid from another fund in this year, counts toward that line. Payee names
   through `journal.payee()` / `vendor_key()`.
2. **Function code for the rest**, where both funds book the same heading.
3. **Payroll has no payee** (3,176 of 6,583 FY2026 actual lines carry a vendor; payroll does not,
   by design: names masked). Payroll moved between funds is already measured on
   /school-all-funds/pay-moved-between-funds (journal entries moving GF pay to other funds and
   back); reuse that logic, do not re-derive it.
4. **Anything unmatched stays visibly unmatched**, its own row, never folded into "budgeted
   above cost". Rule 13 3/sub-cause 3: a join that matches nothing looks like absence.

Every match rule is OUR reading and says so (rule 7); the identity's arithmetic is not.

## The page: one FY at a time, four pictures (settled with TJ, 26 Oct 2026, late)

TJ: *"there has to be a way to visualize fungibility then. this has to be a solved problem?"*
It is two problems, and only one is drawable.

**Across funds (who paid) -- solved.** An ALLUVIAL diagram (a Sankey across years). **This is
the page's opening picture.** Columns FY2023 to FY2026; in each, stacked blocks by function group
(`build_school_surplus.CATEGORIES`), each block split by payer (GF, each grant via
`journal.grant_program()`, circuit breaker, revolving). Bands flow year to year. A payer shift
reads as a band keeping its height and changing colour: May Institute, GF blue in FY2025, grant
orange in FY2026. Cost held, payer changed. The state publishes the all-funds-by-function half
(DESE End of Year Financial Report; `fetch_dese_radar.py`): use it as the outside check on our
journal sums. The literature's name for the question is the flypaper effect / supplanting.

**Inside one appropriation (which leftover covered which overrun) -- NOT drawable.** The books
record no pairing between a line's leftover and another line's overrun; the money is a pool.
Any line-to-line arrow is invented (the private-covered-collaborative story in the surplus
handoff is exactly such an invention -- say so where it appears). So draw a HUB-AND-SPOKE: under
lines pour into a central pool, over lines draw from it, the net is what was left. The only
direct edges are those the books record with both ends named: `BUA` transfers and `GEN`
reclasses, solid and dated. **Second picture.**

**Unmatched money is its own grey band/spoke, labelled unmatched** -- payroll moved between funds
has no payee, and a grant may book tuition as services. Never fold it into "voted above cost".

| question | picture | block |
|---|---|---|
| Who paid for what, and did it change? | alluvial, FY2023-FY2026 | `TB.custom`, new component |
| What did the pool absorb? | hub-and-spoke, one FY | `TB.custom`, new component |
| Why is each line under? | waterfall per line + sortable four-way table | `TP.bridge` / table |
| When did money move? | timeline of transfers, reclasses, prepayments | `TB.timeline` or custom |

Opening line: the year's four totals as a comparison (AUDIT-PASS), e.g. "Of $482,118 left: $X
voted above cost, $Y paid by other funds, $Z moved by transfer, -$W paid for next year."
Plus conclusions with `so=` on every one (`topic.MEANINGS_REQUIRED`), a not-established block,
sources, money-gaps citations. Build order: data + identity + verifier, then the alluvial, then
the pool, then the rest. TJ's aim, verbatim: *"i want to find a way to analyze these FYs to
figure this out."* The page is an instrument for that first, a publication second.

## Data, and what to check before writing a sentence

- `sources/data/munis-school-journal.csv` via `scripts/journal.py` (`lines()`, `accounts()`,
  `COLUMN_OF` maps source codes to actual / encumbrance / original_budget / transfer,
  `fund_group()`, `in_surplus_scope()`, `left()`). FY2023-FY2026, 93 funds.
- FY2026 actuals by fund group (journal, expense accounts): General fund $25,657,318; Revolving
  and lunch $1,856,768; Grants $1,021,253; Capital and other $788,956; Circuit breaker $337,499.
  Recompute, do not quote.
- **FIRST STEP: tie every year and every fund to the period-13 reports** (GF:
  `munis-school-ytd.csv`; special funds: the period-13 special funds report). money-gaps row 225
  says that report leaves some special revenue funds out against the annual town report -- so
  state which funds the page covers, and that the rest is not held.
- Budgets exist for the GF only (BUC/BUA). Other funds have no "voted" column in the same
  sense; they enter the identity only as "paid by other funds".
- FY2025 closes on a different footing from FY2026 (`HANDOFF-SURPLUS-PAGES.md`, item 1): use
  the owed footing throughout and say so.

## The verifier, written before the prose (rule 15)

A `verify_fy_breakdown.py` that recomputes the four terms from the raw CSV with Decimal,
sharing only the category definition, and asserts: the four sum to each line's printed
available; the year's four sum to the surplus; the two test cases above reproduce exactly.

## Cost

A generator, a Sankey component, a verifier: a few hours. Fresh session (rule 7g). The
interactive session is the expensive part, so keep OCR-style reading out of it.

## Not this page's job

Whether any shift was proper. Lawfulness of the prepayment is on its own page (c.71 s.71D).
Supplement-not-supplant / IDEA maintenance of effort was raised in conversation on 26 October
as a QUESTION, unchecked: MOE is tested in aggregate with allowable exceptions, so one payer
shift establishes nothing. Do not put it on a page without the regulation and the district's
MOE figures in hand.
