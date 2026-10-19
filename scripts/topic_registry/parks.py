"""The Parks and recreation shelf: what the town votes the Parks department, the fee funds
beside it, and the funds the youth leagues' field money runs through. See scripts/topics.py
for the model and the title rule.

Absorbs /parks-and-recreation (build_parks.py) and /youth-sports (build_youth_sports.py).
There is no full report. The Park Department's line inside the facilities group belongs to
Department budgets and is only LISTED here. One question, one page, one address.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['parks-budget'],
    id='parks', shelf='Parks and recreation', title='Parks department', area='town',
    order=56,
    groups=[
        ('The department', ['parks-budget', 'parks-spending', 'park-revolving-fund',
                            'other-parks-funds']),
        ('Programs and grounds', ['registration-sales', 'grounds-maintenance-bid']),
        ('Youth sports and fields', ['school-facilities-fund', 'school-field-upkeep',
                                     'youth-league-payments', 'artificial-turf-fund']),
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
    'school-facilities-fund': 'School facilities fund',
    'school-field-upkeep': 'School field upkeep',
    'youth-league-payments': 'Youth league payments',
    'artificial-turf-fund': 'Artificial turf fund',
}
