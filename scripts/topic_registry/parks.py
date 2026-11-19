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
        ('The department', ['parks-year-changes', 'parks-budget', 'parks-spending',
                            'park-revolving-fund', 'other-parks-funds']),
        ('Programs and grounds', ['parks-programmes', 'registration-sales',
                                  'grounds-maintenance-bid']),
        ('Related pages', ['town-facilities-grounds']),
    ],
    # Every fund and account the Parks Commission owns has its own page, posting by posting
    # (pages/TownFund.tsx, from build_parks_ledger.py). TJ, 19 November 2026: "i cant find the
    # details page for the parks revolving account".
    elsewhere=[('/town-funds/park-revolving-1500', 'Fund 1500, every posting'),
               ('/town-funds/park-gift-1523', 'Fund 1523, every posting'),
               ('/town-lines/parks-recreation-650', 'Department 650, every account'),
               ('/athletics', 'Athletics costs')])
GENERATOR = 'build_parks_topics.py'
# TJ, 19 November 2026: "a page that compared year over year to identify what changed in either
# revenue or spending" and "where did they spend? On what? for which program".
TOPIC_GENERATORS = {'parks-year-changes': 'build_parks_ledger.py',
                    'parks-programmes': 'build_parks_ledger.py'}
TOPICS = {
    'parks-budget': 'Parks budget',
    'parks-spending': 'Parks spending',
    'park-revolving-fund': 'Park revolving fund',
    'other-parks-funds': 'Smaller parks funds',
    'registration-sales': 'Registration sales',
    'grounds-maintenance-bid': 'Grounds maintenance bid',
    'parks-year-changes': 'Money in and out',
    'parks-programmes': 'Programme payments',
}
