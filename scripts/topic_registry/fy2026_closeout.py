"""The FY2026 closeout shelf. See scripts/topics.py for the model and the title rule.

Absorbs fy26-closeout, fy26-closeout-town, fy26-school-surplus and fy25-school-surplus. Two
pages on its shelf belong to other categories and are only LISTED here: special education
transportation's FY2026 overrun (transportation) and the FY2026 athletics underspend
(athletics). One question, one page, one address.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    # 26 October 2026: the two start pages folded into the hub (TJ: "seems useless").
    # 24 November 2026: no start list. Its two pages are the whole Total section, which Start here
    # would swallow, dropping that section's figure; Total is the first section instead.
    id='fy2026-closeout', shelf='FY2026 school closeout', title='FY2026 school year end', area='special',
    # Lives under the whole school budget (TJ, 26 November 2026: "i like
    # /school-all-funds/fy2026-closeout better"); /fy2026-closeout still routes.
    under='school-all-funds',
    # A special report (TJ, 24 Oct 2026): off the menu once FY2027's close replaces it.
    archive_after='2027-10-31', order=95,
    # 26 October 2026, regrouped by the question a reader brings, not by which ledger answered
    # it (period-13 report or journal): how much and where; when in the year; what could change.
    # Lines over budget folded into Surplus by category, FY2025 school surplus into Surplus by
    # year (fy28/src/routes.ts TOPIC_MERGED).
    # 24 November 2026, regrouped on TJ's word (decision on the closeout report ticket):
    # six parts named by NOUNS, never sentences (TJ: "just dont use sentences forcategories"),
    # each drawn with a figure the hub's generator computes (hub payload `group_figures`).
    # Circuit breaker and surplus folded into FY2026 school surplus (routes.ts TOPIC_MERGED).
    # 27 November 2026, the review pass (T-VPW4S; TJ: "each of the sections is effectively the
    # same"): 13 pages became 10, one question each, grouped by the question. Two-year surplus and
    # Surplus suggestions folded into Repeat underspending; the 29 June circuit breaker entry moved
    # from FY2026 school surplus to Year-end tuition entries beside the 30 June payment;
    # Paraprofessional overrun and Psychologist line became Staff lines (routes.ts TOPIC_MERGED).
    groups=[
        ('How big', ['surplus-bridge', 'fy2026-surplus-by-category']),
        ('Tuition', ['fy2026-tuition-lines', 'fy2026-tuition-paid-early']),
        ('Where it was left', ['surplus-repeat-lines', 'fy2026-staff-lines', 'why-it-was-left',
                               'special-education-transportation', 'fy2026-athletics-underspend']),
        ('When', ['budget-burndown', 'sped-burndown']),
        ('Controls', ['fy2026-school-transfers', 'fy2026-budget-vs-munis']),
    ])
GENERATOR = 'build_fy2026_closeout_topics.py'
TOPIC_GENERATORS = {'fy2026-surplus-by-category': 'build_fy2026_school_surplus.py',
                    'fy2026-budget-vs-munis': 'build_budget_vs_munis.py',
                    'surplus-bridge': 'build_journal_surplus_topics.py',
                    'surplus-repeat-lines': 'build_journal_surplus_topics.py',
                    'budget-burndown': 'build_journal_surplus_topics.py',
                    'fy2026-tuition-paid-early': 'build_journal_surplus_topics.py',
                    'why-it-was-left': 'build_why_it_was_left.py'}
TOPICS = {
    'fy2026-budget-vs-munis': 'Budget against MUNIS',
    'fy2026-surplus-by-category': 'Surplus by category',
    'fy2026-school-transfers': 'Year-end transfers',
    'fy2026-tuition-lines': 'Tuition at year end',
    'fy2026-staff-lines': 'Staff lines',
    'surplus-bridge': 'Surplus by year',
    'surplus-repeat-lines': 'Repeat underspending',
    'budget-burndown': 'Budget burndown',
    'fy2026-tuition-paid-early': 'Year-end tuition entries',
    # TJ, 26 November 2026: "can we answer WHAT wasn't paid for that WAS paid for in previous
    # years?!" The id is the ticket's; the title is the noun the page answers.
    'why-it-was-left': 'Spending that stopped',
}
