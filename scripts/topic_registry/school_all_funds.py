"""The school budget, all funds. See scripts/topics.py for the model and the title rule.

Phase 3 of notes/MASTER-PLAN.md. TJ, 22 October 2026: *"the schools' 'budget' is just the
general fund. They layer in grants and stuff to their PowerPoints, but how that gets budgeted
is SUPER unclear."* So this shelf shows every one of the district's own budget lines with ALL
the money behind it, from the school MUNIS journal, FY2023 to FY2026: what came in and from
where, what each line was voted and what every fund spent on it, what was left unspent, and
what is paid from outside the general fund. The special education page is the same report,
filtered.

Order 5 puts it first among the school shelves (Phase 4, item 16: "the complete school budget
as a category at the TOP").
"""
CATEGORY = dict(
    start=['budget-lines-all-funds', 'grant-coding'],
    id='school-all-funds', shelf='School budget, all funds', title='The whole school budget',
    area='school', order=5,
    groups=[
        ('Money in and out', ['school-money-in', 'budget-lines-all-funds',
                              'outside-the-general-fund']),
        ('Left unspent', ['unspent-by-fund', 'carried-over-orders']),
        ('How grants are booked', ['grant-coding']),
        ('Grants compared', ['grant-allocations-compared', 'grants-others-receive']),
        ('Special education', ['sped-all-funds']),
        # TJ, 24 October 2026: "for all the grants.... have we broken down how that money is
        # spent? I want to have reports on that." Every post read alike; none singled out.
        ('Who grants and fees pay for', ['pay-from-grants-and-fees', 'pay-moved-between-funds',
                                         'positions-and-their-funds']),
    ])
GENERATOR = 'build_school_all_funds.py'
# DESE's allocations against the comparison districts (MASTER-PLAN item 10): a different source
# from the journal, so its own generator.
# Orders carried from one year into the next (TJ, 23 October 2026): the same journal, read for
# one question the all-funds generator does not ask, so its own generator.
TOPIC_GENERATORS = {'grant-allocations-compared': 'build_grant_comparison_topics.py',
                    'grants-others-receive': 'build_grant_comparison_topics.py',
                    'carried-over-orders': 'build_carryover_topics.py',
                    'pay-from-grants-and-fees': 'build_pay_by_fund_topics.py',
                    'pay-moved-between-funds': 'build_pay_by_fund_topics.py',
                    'positions-and-their-funds': 'build_pay_by_fund_topics.py'}
TOPICS = {
    'school-money-in': 'School money in',
    'budget-lines-all-funds': 'Budget lines, all funds',
    'outside-the-general-fund': 'Paid outside the general fund',
    'unspent-by-fund': 'Unspent money by fund',
    'grant-coding': 'Grant spending by line',
    'grant-allocations-compared': 'Grant allocations compared',
    'grants-others-receive': 'Grants other districts get',
    'carried-over-orders': 'Carried-over orders',
    'pay-from-grants-and-fees': 'Pay from grants and fees',
    'pay-moved-between-funds': 'Pay moved between funds',
    'positions-and-their-funds': 'Positions and their funds',
}
