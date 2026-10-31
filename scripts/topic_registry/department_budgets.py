"""The Department budgets shelf: what Town Meeting votes each department, and who stands
behind it. See scripts/topics.py for the model and the title rule.

Absorbs /analysis/town-budgets, /analysis/town-personnel and the twelve
/analysis/town-budget-* department documents. Four pages on this shelf belong to other
categories and are only LISTED here: the FY2026 town unspent balance, snow and the Reserve
Fund, and school retiree insurance (FY2026 closeout), and the Monty Tech assessment
(Enrolment). One question, one page, one address.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['town-budget-growth', 'town-employee-benefits'],
    id='department-budgets', shelf='Department budgets', title='Town departments', area='town',
    order=52,
    groups=[
        # TJ, 31 October 2026: the whole Town general fund -- money in, money out, what is
        # left -- and which records hold each, at /town-funds/general-fund too
        ('The whole general fund', ['town-general-fund']),
        ('The whole budget', ['town-budget-shares', 'town-budget-growth', 'town-voted-total']),
        ('The four largest', ['town-schools-line', 'town-public-safety',
                              'town-employee-benefits', 'town-debt-service']),
        ('The other departments', ['town-general-government', 'town-public-works',
                                   'town-facilities-grounds', 'town-solid-waste',
                                   'town-library', 'town-smaller-departments']),
        ('People', ['town-staff-counts', 'town-headcount-coverage']),
        ('Related pages', ['fy2026-town-unspent', 'fy2026-snow-and-reserve-fund',
                           # monty-tech-assessment left 26 October 2026: Monty Tech pages are
                           # listed only on the Monty Tech shelf (TJ).
                           'fy2026-school-retiree-insurance']),
    ])
GENERATOR = 'build_department_budgets_topics.py'
TOPIC_GENERATORS = {'town-general-fund': 'build_town_general_fund.py'}
TOPICS = {
    'town-general-fund': 'Town general fund',
    'town-budget-shares': 'Budget by department',
    'town-budget-growth': 'Growth above the cap',
    'town-voted-total': 'Voted budget total',
    'town-schools-line': 'Schools in the omnibus',
    'town-public-safety': 'Police, fire and inspectors',
    'town-employee-benefits': 'Employee benefits',
    'town-debt-service': 'Debt service',
    'town-general-government': 'General government',
    'town-public-works': 'Public works',
    'town-facilities-grounds': 'Facilities and grounds',
    'town-solid-waste': 'Trash and recycling',
    'town-library': 'Library budget',
    'town-smaller-departments': 'Smaller departments',
    'town-staff-counts': 'Town staff counts',
    'town-headcount-coverage': 'Budgets without headcounts',
}
