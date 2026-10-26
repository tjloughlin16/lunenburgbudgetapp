# Handoff: one fiscal year, broken down -- why a surplus happened

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
