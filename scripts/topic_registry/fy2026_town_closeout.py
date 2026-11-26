"""The FY2026 town year end shelf: the town (non-school) departments at the close. See
scripts/topics.py for the model and the title rule.

The town counterpart of fy2026-closeout, the school budget's year end (TJ, 26 November 2026:
"i think we ned a related [hub] for the town too, all other deparmtents"). Built on the town's
closed-year report (period 13), which the school hub's town pages predate: those three read
June (period 12) and are listed here until their home is settled.
"""
CATEGORY = dict(
    id='fy2026-town-closeout', shelf='FY2026 town closeout', title='FY2026 town year end',
    area='special',
    # Lives under the Town departments hub, as the school year end lives under the whole
    # school budget: /department-budgets/fy2026-town-closeout.
    under='department-budgets',
    # A special report: off the menu once FY2027's close replaces it.
    archive_after='2027-10-31', order=96,
    groups=[
        ('By department', ['fy2026-town-departments']),
        ('June readings', ['fy2026-town-unspent', 'fy2026-snow-and-reserve-fund',
                           'fy2026-school-retiree-insurance']),
    ])
GENERATOR = 'build_fy2026_town_closeout.py'
TOPICS = {
    'fy2026-town-departments': 'Departments at close',
}
