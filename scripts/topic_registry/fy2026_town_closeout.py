"""The FY2026 town year end shelf: the town (non-school) departments at the close. See
scripts/topics.py for the model and the title rule.

The town counterpart of fy2026-closeout, the school budget's year end (TJ, 26 November 2026:
"i think we ned a related [hub] for the town too, all other deparmtents"). Built on the town's
closed-year report (period 13), which the school hub's town pages predate: those three read
June (period 12) and are listed here until their home is settled.
"""
# Every office that closed FY2026 with at least two accounts off its budget (fewer, and it is
# drawn on Other town lines), by its office page's
# slug (build_town_office_pages.py). build_fy2026_town_closeout.py refuses if this list and the
# ledger disagree, so an office cannot gain or lose its page silently.
OFFICES = {
    'fy2026-close-town-manager': 'Town Manager closeout',
    'fy2026-close-dpw': 'Public works closeout',
    'fy2026-close-police': 'Police closeout',
    'fy2026-close-fire': 'Fire closeout',
    'fy2026-close-land-use': 'Land Use closeout',
    'fy2026-close-facilities': 'Facilities closeout',
    'fy2026-close-council-on-aging': 'Council on Aging closeout',
    'fy2026-close-assessors-administration': 'Assessors closeout',
    'fy2026-close-accounting': 'Accountant closeout',
    'fy2026-close-information-technology': 'Information technology closeout',
    'fy2026-close-treasurer-collector': 'Treasurer closeout',
    'fy2026-close-veterans-services': 'Veterans closeout',
    'fy2026-close-select-board': 'Select Board closeout',
    'fy2026-close-lunenburg-public-library': 'Library closeout',
    'fy2026-close-town-clerk': 'Town Clerk closeout',
    'fy2026-close-cemetery-department': 'Cemetery closeout',
    'fy2026-close-building-inspection': 'Building inspection closeout',
    'fy2026-close-general-health-expense': 'Health expense closeout',
    'fy2026-close-animal-control': 'Animal control closeout',
    'fy2026-close-dispatch': 'Dispatch closeout',
    'fy2026-close-finance-committee': 'Finance Committee closeout',
    'fy2026-close-historical-commission': 'Historical Commission closeout',
}

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
        # One closeout page per town office (TJ, 26 November 2026, of the every-account pages:
        # "the title, context, url do not seem like this is a closeout page ... we need charts to
        # show their biggest misses/overspends" -- "thats for all town pages"). Parks' closeout is
        # Parks spending, on the Parks shelf; it is listed, not rebuilt.
        ('By office', [t for t in OFFICES] + ['parks-spending', 'fy2026-town-exact']),
        ('June readings', ['fy2026-town-unspent', 'fy2026-snow-and-reserve-fund',
                           'fy2026-school-retiree-insurance']),
    ])
GENERATOR = 'build_fy2026_town_closeout.py'
# The three June readings moved home here from the school year end (TJ, 26 November 2026:
# "yes"); build_fy2026_closeout_topics.py still writes them.
TOPIC_GENERATORS = {t: 'build_fy2026_closeout_topics.py' for t in (
    'fy2026-town-unspent', 'fy2026-snow-and-reserve-fund', 'fy2026-school-retiree-insurance')}
TOPICS = {
    'fy2026-town-unspent': 'Town unspent balance',
    'fy2026-snow-and-reserve-fund': 'Snow and Reserve Fund',
    'fy2026-school-retiree-insurance': 'School retiree insurance',
    'fy2026-town-departments': 'Departments at close',
    'fy2026-town-exact': 'Other town lines',
}
TOPICS.update(OFFICES)
