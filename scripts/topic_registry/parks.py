"""The Parks and recreation shelf: what the town votes the Parks department and the fee funds
beside it. The leagues' field rent goes to the SCHOOLS' fund 1306, so those pages moved to the
whole school budget shelf on 5 November 2026 (TJ: "clearly this money goes to the schools, not
to parks"). See scripts/topics.py for the model and the title rule.

Absorbs /parks-and-recreation (build_parks.py) and /youth-sports (build_youth_sports.py).
There is no full report. The Park Department's line inside the facilities group belongs to
Department budgets and is only LISTED here. One question, one page, one address.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['parks-budget'],
    id='parks', shelf='Parks and recreation', title='Parks department', area='town',
    # TJ, 5 November 2026: "move these reports and relate them to the parks-commission BOARD, not
    # be under a /parks". The reports live at /boards/parks-commission/reports; /parks still routes.
    board='parks-commission', under_board=True,
    order=56,
    groups=[
        ('The department', ['parks-budget', 'parks-spending', 'park-revolving-fund',
                            'other-parks-funds']),
        ('Programs and grounds', ['registration-sales', 'grounds-maintenance-bid']),
        ('Related pages', ['town-facilities-grounds']),
    ],
    elsewhere=[('/athletics', 'Athletics costs')])
GENERATOR = 'build_parks_topics.py'
TOPICS = {
    'parks-budget': 'Parks budget',
    'parks-spending': 'Parks spending',
    'park-revolving-fund': 'Park revolving fund',
    'other-parks-funds': 'Smaller parks funds',
    'registration-sales': 'Registration sales',
    'grounds-maintenance-bid': 'Grounds maintenance bid',
}
