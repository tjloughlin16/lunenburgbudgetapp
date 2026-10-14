"""The Stabilization funds shelf, at /town-reserves. See scripts/topics.py for the model and
the title rule.

Until 14 October 2026 this shelf was "Town reserves" and held free cash too; free cash is now
its own shelf (topic_registry/free_cash.py, hub /free-cash), because a reader searching for it
by name found nothing. The address stays /town-reserves so these six pages do not move.

Absorbs /analysis/stabilization-funds and /analysis/stabilization-option. There is no full
report: every question they answered has one page here.
"""
CATEGORY = dict(
    id='town-reserves', shelf='Stabilization funds', title='Stabilization funds', area='town',
    order=50,
    groups=[
        ('The funds', ['stabilization-balances', 'general-stabilization-fund',
                       'who-may-spend-it']),
        ('Money in and out', ['stabilization-deposits', 'stabilization-withdrawals',
                              'reserves-and-the-gap']),
    ],
    elsewhere=[('/free-cash', 'Free cash')])
GENERATOR = 'build_town_reserves_topics.py'
TOPICS = {
    'stabilization-balances': 'Stabilization fund balances',
    'general-stabilization-fund': 'General stabilization fund',
    'who-may-spend-it': 'Who may spend it',
    'stabilization-deposits': 'Stabilization deposits',
    'stabilization-withdrawals': 'Stabilization withdrawals',
    'reserves-and-the-gap': 'Reserves against the gap',
}
