"""The FY2026 closeout shelf. See scripts/topics.py for the model and the title rule.

Absorbs fy26-closeout, fy26-closeout-town, fy26-school-surplus and fy25-school-surplus. Two
pages on its shelf belong to other categories and are only LISTED here: special education
transportation's FY2026 overrun (transportation) and the FY2026 athletics underspend
(athletics). One question, one page, one address.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    # 26 October 2026: the two start pages folded into the hub (TJ: "seems useless").
    start=['fy2026-surplus-by-category', 'surplus-bridge'],  # TJ: by category is "the main school based surplus page"
    id='fy2026-closeout', shelf='FY2026 closeout', title='FY2026 year end', area='special',
    # A special report (TJ, 24 Oct 2026): off the menu once FY2027's close replaces it.
    archive_after='2027-10-31', order=95,
    # 26 October 2026, regrouped by the question a reader brings, not by which ledger answered
    # it (period-13 report or journal): how much and where; when in the year; what could change.
    # Lines over budget folded into Surplus by category, FY2025 school surplus into Surplus by
    # year (fy28/src/routes.ts TOPIC_MERGED).
    groups=[
        (None, ['fy2026-surplus-by-category', 'surplus-bridge', 'fy2026-circuit-breaker',
                'fy2026-tuition-paid-early',
                'surplus-repeat-lines', 'surplus-suggestions']),
        ('Through the year', ['budget-burndown', 'sped-burndown', 'fy2026-school-transfers']),
        ('School lines', ['fy2026-tuition-lines', 'fy2026-paraprofessional-overrun',
                          'fy2026-psychologist-line', 'special-education-transportation',
                          'fy2026-athletics-underspend']),
        ('Town side', ['fy2026-town-unspent', 'fy2026-snow-and-reserve-fund',
                       'fy2026-school-retiree-insurance']),
    ])
GENERATOR = 'build_fy2026_closeout_topics.py'
TOPIC_GENERATORS = {'surplus-bridge': 'build_journal_surplus_topics.py',
                    'surplus-repeat-lines': 'build_journal_surplus_topics.py',
                    'budget-burndown': 'build_journal_surplus_topics.py',
                    'surplus-suggestions': 'build_journal_surplus_topics.py',
                    'fy2026-tuition-paid-early': 'build_journal_surplus_topics.py',
                    'fy2026-circuit-breaker': 'build_circuit_breaker_surplus.py'}
TOPICS = {
    'fy2026-surplus-by-category': 'Surplus by category',
    'fy2026-school-transfers': 'Year-end transfers',
    'fy2026-tuition-lines': 'Tuition at year end',
    'fy2026-paraprofessional-overrun': 'Paraprofessional overrun',
    'fy2026-psychologist-line': 'Psychologist line',
    'fy2026-town-unspent': 'Town unspent balance',
    'fy2026-snow-and-reserve-fund': 'Snow and Reserve Fund',
    'fy2026-school-retiree-insurance': 'School retiree insurance',
    'surplus-bridge': 'Surplus by year',
    'surplus-repeat-lines': 'Repeat underspending',
    'budget-burndown': 'Budget burndown',
    'surplus-suggestions': 'Surplus suggestions',
    'fy2026-tuition-paid-early': 'Year-end tuition payment',
    'fy2026-circuit-breaker': 'Circuit breaker and surplus',
}
