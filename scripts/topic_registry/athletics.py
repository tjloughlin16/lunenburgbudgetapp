"""The Athletics shelf. See scripts/topics.py for the model and the title rule."""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['total-athletics-cost', 'town-budget-and-fee-fund'],
    id='athletics', shelf='Athletics', title='Athletics costs', area='school', order=11,
    full_report=('/analysis/athletics', 'Athletics, the full report'),
    groups=[
        (None, ['total-athletics-cost', 'town-budget-and-fee-fund', 'cost-per-sport',
                'spending-by-category', 'participation', 'athletic-fee',
                'fee-fund-ledger', 'fee-fund-history', 'athletic-director',
                'fy2026-athletics-underspend']),
        ('Athletic transportation', ['athletic-bus-funding', 'fy2027-athletic-bus-cut',
                                     'bus-cost-by-sport', 'away-trips-by-sport']),

        ('The turf field', ['turf-field-capital-plans']),
    ],
    # The three long pages these pointed at are UNLISTED now; each question has a topic page.
    elsewhere=[('/parks/youth-league-payments', 'Youth league field payments'),
               ('/budget-options/school-user-fees', 'School user fees'),
               ('/budget-options/extracurricular-cuts', 'Extracurricular cuts')])
GENERATOR = 'build_athletics_topics.py'
# The turf field's capital-plan history, written from sources/data/capital-plan-field-lines.csv.
TOPIC_GENERATORS = {'turf-field-capital-plans': 'build_turf_plans_topic.py',
                    # fund 1301 across every year held, and the athletic director post (28 Oct 2026)
                    'fee-fund-history': 'build_fee_fund_history_topic.py',
                    'athletic-director': 'build_athletic_director_topic.py'}
TOPICS = {
    'total-athletics-cost': 'Total athletics cost',
    'town-budget-and-fee-fund': 'Town budget and fee fund',
    'cost-per-sport': 'Cost per sport',
    'spending-by-category': 'Spending by category',
    'participation': 'Participation',
    'athletic-fee': 'Athletic fee',
    'fee-fund-ledger': 'Fee fund ledger',
    'fee-fund-history': 'Fee fund history',
    'athletic-director': 'Athletic director',
    'fy2026-athletics-underspend': 'FY2026 athletics underspend',
    'turf-field-capital-plans': 'Turf field capital plans',
}
