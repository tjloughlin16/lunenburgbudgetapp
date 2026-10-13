"""The Town reserves shelf: free cash and the stabilization funds. See scripts/topics.py for
the model and the title rule.

Absorbs /analysis/free-cash, /analysis/stabilization-funds, /analysis/stabilization-option
and the /free-cash-for-schools lever page. There is no full report: every question those four
answered has one page here.
"""
CATEGORY = dict(
    id='town-reserves', shelf='Town reserves', title='Free cash and stabilization', area='town',
    order=50,
    groups=[
        ('Free cash', ['free-cash-balance', 'free-cash-guideline', 'free-cash-sources',
                       'free-cash-and-capital', 'free-cash-redirect']),
        ('Stabilization funds', ['stabilization-balances', 'general-stabilization-fund',
                                 'who-may-spend-it', 'stabilization-deposits',
                                 'stabilization-withdrawals', 'reserves-and-the-gap']),
    ])
GENERATOR = 'build_town_reserves_topics.py'
TOPICS = {
    'free-cash-balance': 'Free cash balance',
    'free-cash-guideline': 'Free cash guideline',
    'free-cash-sources': 'Free cash sources',
    'free-cash-and-capital': 'Free cash and capital',
    'free-cash-redirect': 'Free cash for schools',
    'stabilization-balances': 'Stabilization fund balances',
    'general-stabilization-fund': 'General stabilization fund',
    'who-may-spend-it': 'Who may spend it',
    'stabilization-deposits': 'Stabilization deposits',
    'stabilization-withdrawals': 'Stabilization withdrawals',
    'reserves-and-the-gap': 'Reserves against the gap',
}
