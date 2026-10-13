#!/usr/bin/env python3
"""THE REGISTRY OF TOPIC PAGES: which categories exist, which pages are in each, what each
is called, and where it lives. The one place a page's existence is decided.

WHY. TJ, 12 October 2026: *"nobody will ever read these full reports... we need to break
up all these long reports into smaller pages everywhere"* -- starting with athletics and
transportation, as "a model that makes sense and we can replicate". An inventory of the
site found the same questions answered in three to seven places each (athletic buses
moving from fees to the town: seven). So splitting is also DEDUPLICATING: every question
gets exactly one page, and every other place links to it.

THE MODEL.
    category      a shelf on /reports, and a hub page at /<category>
    hub           the matrix of facts, the conclusions, a card per topic   (~3 min)
    topic         one question, one chart, two to four conclusions         (< 5 min)
    shared topic  ONE address, listed on every shelf it belongs to -- never two copies
    reference     year-by-year tables, what was said, method, sources

TITLES ARE DESCRIPTIVE, NOT QUESTIONS AND NOT FINDINGS. TJ: *"i dont like the question
format... we need a more clear title. a more direct title."* A title is the subject in
two to four words; the line under it -- the payload's `finding` -- is what it shows.
Descriptive titles scan in a list and do not go stale when a number moves.

A topic's address is /<home>/<id>; `home` is the category it belongs to first. A topic
listed on another shelf keeps that one address.
"""

CATEGORIES = [
    dict(
        id='transportation', shelf='Transportation', title='School bus costs',
        full_report=('/analysis/transportation', 'School transportation, the full report'),
        groups=[
            (None, ['dee-bus-contract', 'special-education-transportation',
                    'state-reimbursement', 'bus-fee', 'fy2027-bus-budget']),
            ('Athletic transportation', ['athletic-bus-funding', 'fy2027-athletic-bus-cut',
                                         'bus-cost-by-sport', 'away-trips-by-sport']),
        ]),
    dict(
        id='athletics', shelf='Athletics', title='Athletics costs',
        full_report=('/analysis/athletics', 'Athletics, the full report'),
        groups=[
            (None, ['total-athletics-cost', 'town-budget-and-fee-fund', 'cost-per-sport',
                    'spending-by-category', 'participation', 'athletic-fee',
                    'fee-fund-ledger', 'fy2026-athletics-underspend']),
            ('Athletic transportation', ['athletic-bus-funding', 'fy2027-athletic-bus-cut',
                                         'bus-cost-by-sport', 'away-trips-by-sport']),
        ],
        # Pages elsewhere on the site that belong on this shelf too, as they are.
        elsewhere=[('/youth-sports', 'Youth sports and town fields'),
                   ('/fees', 'Raising school fees'),
                   ('/extras', 'Cutting the extras')]),
]

# id -> (title, home category, generator that writes its payload)
TOPICS = {
    'dee-bus-contract': ('Dee Bus contract', 'transportation', 'build_transportation.py'),
    'special-education-transportation': ('Special education transportation', 'transportation',
                                         'build_transportation.py'),
    'state-reimbursement': ('State reimbursement', 'transportation', 'build_transportation.py'),
    'bus-fee': ('Bus fee', 'transportation', 'build_transportation.py'),
    'fy2027-bus-budget': ('FY2027 bus budget', 'transportation', 'build_transportation.py'),
    'athletic-bus-funding': ('Athletic bus funding', 'transportation', 'build_transportation.py'),
    'fy2027-athletic-bus-cut': ('FY2027 athletic bus cut', 'transportation',
                                'build_transportation.py'),
    'bus-cost-by-sport': ('Bus cost by sport', 'transportation', 'build_transportation.py'),
    'away-trips-by-sport': ('Away trips by sport', 'transportation', 'build_transportation.py'),

    'total-athletics-cost': ('Total athletics cost', 'athletics', 'build_athletics_topics.py'),
    'town-budget-and-fee-fund': ('Town budget and fee fund', 'athletics',
                                 'build_athletics_topics.py'),
    'cost-per-sport': ('Cost per sport', 'athletics', 'build_athletics_topics.py'),
    'spending-by-category': ('Spending by category', 'athletics', 'build_athletics_topics.py'),
    'participation': ('Participation', 'athletics', 'build_athletics_topics.py'),
    'athletic-fee': ('Athletic fee', 'athletics', 'build_athletics_topics.py'),
    'fee-fund-ledger': ('Fee fund ledger', 'athletics', 'build_athletics_topics.py'),
    'fy2026-athletics-underspend': ('FY2026 athletics underspend', 'athletics',
                                    'build_athletics_topics.py'),
}


def category(cid):
    return next(c for c in CATEGORIES if c['id'] == cid)


def path(tid):
    """The one address of a topic, or of a hub when given a category id."""
    if any(c['id'] == tid for c in CATEGORIES):
        return '/' + tid
    return '/%s/%s' % (TOPICS[tid][1], tid)


def shelves_of(tid):
    """Every category a topic is listed under, its home first."""
    home = TOPICS[tid][1]
    rest = [c['id'] for c in CATEGORIES
            if c['id'] != home and any(tid in ids for _, ids in c['groups'])]
    return [home] + rest


def check():
    """Every listed topic is registered, every registered topic is listed at home, and no
    topic appears twice on one shelf."""
    bad = []
    for c in CATEGORIES:
        seen = [t for _, ids in c['groups'] for t in ids]
        for t in seen:
            if t not in TOPICS:
                bad.append('%s lists %r, which is not registered' % (c['id'], t))
        if len(set(seen)) != len(seen):
            bad.append('%s lists a topic twice' % c['id'])
    for t, (_, home, _) in TOPICS.items():
        if not any(t in ids for _, ids in category(home)['groups']):
            bad.append('%r is not listed on its home shelf %r' % (t, home))
    return bad


if __name__ == '__main__':
    import sys
    b = check()
    print('\n'.join(b) or 'topics: %d categories, %d topics' % (len(CATEGORIES), len(TOPICS)))
    sys.exit(1 if b else 0)
