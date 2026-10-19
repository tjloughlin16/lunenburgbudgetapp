"""The School spending history shelf (/school-spending-history): the schools' spending, their teaching staff and their
pupils, set side by side over as many years as each is published. See scripts/topics.py for
the model and the title rule.

Asked for by older residents, relayed by TJ on 18 October 2026: "They want to see as far back
as we have data to relate the budget and the spending to the FTE counts and the enrollment
count." The shelf MEASURES; it neither confirms nor rebuts anybody's reading of the measures
(CLAUDE.md rules 7 and 8).

There is no full report. Five pages are new. The single-measure pages already on other
shelves -- enrolment by year, teachers over time, teachers per pupil, paraprofessionals,
spending per pupil against the state, net school spending against the state minimum -- are
LISTED here and live at their one address. One question, one page.
"""
CATEGORY = dict(
    id='school-spending-history', shelf='School spending history',
    title='School spending history', area='school', order=26,
    groups=[
        # Led by the pages that answer the question directly -- where the growth went, by
        # type -- TJ, 19 October 2026.
        ('Side by side', ['growth-by-spending-type', 'spending-by-type-over-time',
                          # TJ, 19 October 2026: "did the increase cost from more teachers,
                          # or higher pay per teacher?" -- and how pay compares nearby.
                          'pay-or-headcount', 'teacher-pay-compared',
                          # TJ, 19 October 2026: DESE's average puts Lunenburg second of
                          # six while residents call its scale the lowest -- where on the
                          # scale the teachers sit, from the town's own wage list.
                          'teachers-on-the-scale',
                          'growth-side-by-side',
                          'teachers-and-other-staff', 'spending-per-child-enrolled',
                          'long-run-school-spending']),
        ('What the counts cannot settle', ['fy2011-teacher-reading']),
        ('Each measure on its own', ['enrolment-by-year', 'teacher-fte-over-time',
                                     'teachers-per-pupil', 'paraprofessional-fte',
                                     'headcount-and-fte', 'per-pupil-spending',
                                     'spending-and-pupils', 'net-school-spending',
                                     'chapter-70-by-year']),
    ],
    # The page that answers the residents' question most directly (TJ, 19 October 2026).
    start=['growth-by-spending-type', 'spending-by-type-over-time', 'pay-or-headcount'],
    elsewhere=[('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_spending_staff_students_topics.py'
TOPICS = {
    'growth-by-spending-type': 'Growth by spending type',
    'spending-by-type-over-time': 'Spending by type over time',
    'growth-side-by-side': 'Growth side by side',
    'long-run-school-spending': 'Long-run school spending',
    'spending-per-child-enrolled': 'Spending per child enrolled',
    'teachers-and-other-staff': 'Teachers and other staff',
    'fy2011-teacher-reading': 'FY2011 teacher reading',
    'pay-or-headcount': 'Pay or headcount',
    'teacher-pay-compared': 'Teacher pay compared',
    'teachers-on-the-scale': 'Teachers on the scale',
}
