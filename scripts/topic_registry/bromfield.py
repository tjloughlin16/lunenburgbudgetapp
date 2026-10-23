"""The Bromfield shelf: Harvard Public Schools, the district The Bromfield School belongs to, as a
benchmark beside Lunenburg -- what it spends a pupil, what that buys category by category, and
Lunenburg's spending at Harvard's rate. See scripts/topics.py for the model and the title rule.

TJ, 15 October 2026: "Can you build a hub and similar pages for Bromfield as we have for Monty
Tech" -- and then, on scope: "I just mean a comparison, per pupil spend comparison, how that
breaks down, you know, that kind of thing." So this shelf is spending only: no results pages.

Lunenburg pays Harvard nothing beyond a handful of school choice tuitions, so this is NOT the
Monty Tech "what we pay" shelf. It is a neighbouring K-12 district's spending set beside
Lunenburg's, on DESE's one measure. "Reaching the state median" is HOME on School spending and
listed here, one page on two shelves, because the rate scenario reads it.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['harvard-per-pupil'],
    id='bromfield', shelf='Bromfield', title='Harvard and Bromfield', area='school', order=91,  # Other schools, last (TJ, 22 Oct 2026)
    groups=[
        ('What Harvard spends a pupil', ['harvard-per-pupil', 'harvard-line-by-line']),
        ('Lunenburg at other rates', ['lunenburg-at-harvard-rate', 'cost-of-the-median']),
    ])
GENERATOR = 'build_bromfield_topics.py'
TOPICS = {
    'harvard-per-pupil': 'Harvard per pupil',
    'harvard-line-by-line': 'Harvard per-pupil breakdown',
    'lunenburg-at-harvard-rate': 'Harvard rate scenario',
}
