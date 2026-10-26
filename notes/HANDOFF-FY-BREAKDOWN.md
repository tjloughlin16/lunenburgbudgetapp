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

## The page: one FY at a time, three pictures

Probably a hub per year or one page with a year switch; decide at build time. Opening line is
the four totals for the year, as a comparison (AUDIT-PASS), e.g. "Of $482,118 left: $X voted
above cost, $Y paid by other funds, $Z moved in by transfer, -$W paid for next year."

1. **Sankey (the node graph).** Left: sources -- town appropriation (GF), each grant program
   (`journal.grant_program()` names), circuit breaker, revolving funds. Middle: function groups
   (`build_school_surplus.CATEGORIES`, one naming site-wide). Right: spent / left / paid for
   another year. Band width in dollars. A custom block (`TB.custom` +
   `fy28/src/components/blocks/custom/`); no Sankey exists yet. Rule 7f: a component from the
   payload, never an image.
2. **The four-way table, every line,** sortable by each term. Sorted by "paid by other funds",
   the payer shifts surface by themselves -- that is how May Institute should have been found.
   This is the instrument; the Sankey is the signature.
3. **The timeline of moves.** Months across; one row per move between lines or funds (BUA
   transfers, GEN reclasses, prepayments), sized by dollars. June will be dense; that is a
   finding to state with figures, not a charge. `TB.timeline` may do; if not, custom.

Plus the usual: conclusions with `so=` on every one (the closeout shelf is on
`topic.MEANINGS_REQUIRED`), a not-established block, sources, money-gaps citations.

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
