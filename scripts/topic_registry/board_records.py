"""The Boards shelf: what the town's boards and committees post, and who sits on them. See
scripts/topics.py for the model and the title rule.

Absorbs /boards/compared ('boardcompare', scripts/build_board_posting.py),
/analysis/board-composition, /analysis/open-seats and the board half of
scripts/build_tenure.py's data.

THE ID IS `board-records`, NOT `boards`. A category id is its hub's address, and /boards is
the live index of every board, with /boards/<slug> under it -- a whole subsystem this shelf
must not take over. So the hub lives at /board-records and its topics at
/board-records/<topic>. (fy28/public/data/board-records.json is a DIFFERENT, older payload --
the per-board records tab at /boards/<slug>/records; this shelf writes only under
fy28/public/data/topics/.)
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['board-minutes-posted'],
    id='board-records', shelf='Boards', title='Boards and committees', area='town',
    order=55,
    groups=[
        ('Meeting records', ['board-minutes-posted', 'board-minutes-by-year',
                             'board-recordings']),
        ('Seats', ['board-seats-filled', 'board-open-seats', 'board-sizes']),
        ('People', ['board-turnover', 'board-member-tenure']),
    ],
    elsewhere=[('/boards', 'Every board, one page each')])
GENERATOR = 'build_board_records_topics.py'
TOPICS = {
    'board-minutes-posted': 'Minutes posted',
    'board-minutes-by-year': 'Minutes by year',
    'board-recordings': 'Meeting recordings',
    'board-seats-filled': 'Seats filled',
    'board-open-seats': 'Open seats',
    'board-sizes': 'Board sizes',
    'board-turnover': 'Seats changing hands',
    'board-member-tenure': 'Member tenure',
}
