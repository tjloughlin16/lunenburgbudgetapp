"""The Athletics shelf. See scripts/topics.py for the model and the title rule."""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['total-athletics-cost', 'town-budget-and-fee-fund'],
    id='athletics', shelf='Athletics', title='Athletics costs', area='school', order=11,
    full_report=('/analysis/athletics', 'Athletics, the full report'),
    groups=[
        (None, ['total-athletics-cost', 'town-budget-and-fee-fund', 'cost-per-sport',
                'spending-by-category', 'participation', 'athletic-fee',
                'fee-fund-ledger', 'fy2026-athletics-underspend']),
        ('Athletic transportation', ['athletic-bus-funding', 'fy2027-athletic-bus-cut',
                                     'bus-cost-by-sport', 'away-trips-by-sport']),
    ],
    # The three long pages these pointed at are UNLISTED now; each question has a topic page.
    elsewhere=[('/parks/youth-league-payments', 'Youth league field payments'),
               ('/budget-options/school-user-fees', 'School user fees'),
               ('/budget-options/extracurricular-cuts', 'Extracurricular cuts')])
GENERATOR = 'build_athletics_topics.py'
TOPICS = {
    'total-athletics-cost': 'Total athletics cost',
    'town-budget-and-fee-fund': 'Town budget and fee fund',
    'cost-per-sport': 'Cost per sport',
    'spending-by-category': 'Spending by category',
    'participation': 'Participation',
    'athletic-fee': 'Athletic fee',
    'fee-fund-ledger': 'Fee fund ledger',
    'fy2026-athletics-underspend': 'FY2026 athletics underspend',
}
