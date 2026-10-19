"""The Free cash shelf. See scripts/topics.py for the model and the title rule.

Split from Town reserves on 14 October 2026, because a reader searching the site for "free
cash" found no shelf of that name -- it was one group inside "Town reserves". TJ: "Yes, split
free cash and stabilization funds." The hub takes /free-cash, which was the older standalone
page (tab `freecash`); these five pages were at /town-reserves/<id> until then, and those
addresses still resolve (the Town reserves category still routes, and a topic is fetched by
id), with Topic.tsx moving the address bar to the page's own path.

Absorbs /analysis/free-cash, the /free-cash page and the /free-cash-for-schools lever page.
Written by the same generator as the stabilization funds, from the same data.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['free-cash-redirect', 'free-cash-sources'],
    id='free-cash', shelf='Free cash', title='Free cash', area='town', order=49,
    groups=[
        ('The balance', ['free-cash-balance', 'free-cash-guideline', 'free-cash-sources']),
        ('Where it goes', ['free-cash-and-capital', 'free-cash-redirect']),
    ],
    elsewhere=[('/town-reserves', 'Stabilization funds'), ('/free-cash-calculator', 'Free cash calculator')])
GENERATOR = 'build_town_reserves_topics.py'
TOPICS = {
    'free-cash-balance': 'Free cash balance',
    'free-cash-guideline': 'Free cash guideline',
    'free-cash-sources': 'Free cash sources',
    'free-cash-and-capital': 'Free cash and capital',
    'free-cash-redirect': 'Free cash for schools',
}
