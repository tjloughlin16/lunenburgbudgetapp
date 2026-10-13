"""The State aid shelf. See scripts/topics.py for the model and the title rule.

Absorbs /why-we-only-get-minimum-aid (minaid), /how-chapter-70-works (formula) and
/what-the-state-requires-us-to-spend (required), and covers total state aid from /state-aid
beside Chapter 70 -- always as two quantities (CLAUDE.md rule 11: Chapter 70 is not state aid).
The circuit breaker is HOME on the Special education shelf and transportation reimbursement on
the Transportation shelf; both are listed here, one page on two shelves.
"""
CATEGORY = dict(
    id='state-aid', shelf='State aid', title='Chapter 70 aid', area='school', order=23,
    groups=[
        ('Chapter 70', ['chapter-70-by-year', 'minimum-aid', 'foundation-budget',
                        'required-local-contribution', 'aid-per-pupil']),
        ('The spending floor', ['net-school-spending', 'net-school-spending-rank']),
        ('All state aid', ['total-state-aid', 'chapter-70-school-budget-share',
                           'state-aid-growth', 'cherry-sheet-variance',
                           'cherry-sheet-assessments']),
        ('Other state money', ['circuit-breaker', 'state-reimbursement']),
    ],
    elsewhere=[('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_state_aid_topics.py'
TOPICS = {
    'chapter-70-by-year': 'Chapter 70 by year',
    'minimum-aid': 'Minimum aid',
    'foundation-budget': 'Foundation budget',
    'required-local-contribution': 'Required local contribution',
    'aid-per-pupil': 'Aid per pupil',
    'net-school-spending': 'Net school spending',
    'net-school-spending-rank': 'Spending against the median',
    'total-state-aid': 'Total state aid',
    'chapter-70-school-budget-share': 'Share of the school budget',
    'state-aid-growth': 'State aid growth',
    'cherry-sheet-variance': 'Cherry sheet variance',
    'cherry-sheet-assessments': 'Cherry sheet assessments',
}
