"""The School spending shelf. See scripts/topics.py for the model and the title rule.

Absorbs /what-other-districts-spend ('peers', per-pupil-spending.md), spending-compared.md,
peer-districts.md and /budget-vs-actual ('variance'), and the School Committee's own finance page
(/boards/school-committee/finance, 'schoolfinance'), which stays served as the board's finance tab
and leaves the /reports shelves. Two different questions live here and are kept apart: what the schools spend for each pupil against other districts (DESE's all-funds
figures, reported after a year closes), and whether the school budget matched what was spent
(budget and actual side by side, same year, never differenced across years -- rule 1).

Every comparison says who chose the districts: the state (every district DESE publishes), the
families (where Lunenburg children actually went), or this project (the six-district set).

The Chapter 70 spending floor is HOME on the State aid shelf, the teacher ratio on School
staffing, children schooled elsewhere on Enrolment, the special education overruns on Special
education, the two school surpluses on FY2026 closeout and Monty Tech per pupil on Monty Tech;
each is listed here, one page on two shelves. "What per pupil counts" is HOME here and listed on
Monty Tech: it sets DESE's figure beside net school spending and the Census Bureau's.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['per-pupil-spending', 'spending-by-function'],
    id='school-spending', shelf='School spending', title='Spending compared', area='school',
    order=24,
    groups=[
        ('Against the state', ['per-pupil-spending', 'per-pupil-line-by-line',
                               'what-per-pupil-counts', 'spending-by-function',
                               'grants-in-school-spending', 'cost-of-the-median']),
        ('Against other districts', ['comparison-districts', 'spending-and-pupils',
                                     'gap-by-function', 'average-teacher-salary',
                                     'teacher-pay-compared',
                                     'destination-district-spending',
                                     'regional-district-spending']),
        ('Budget against actual', ['school-budget-against-actual', 'line-level-misses']),
        ('School Committee funds', ['school-committee-funds', 'school-revolving-funds',
                                    'school-grant-balances', 'revolving-fund-history']),
        ('Elsewhere on the site', ['net-school-spending', 'net-school-spending-rank',
                                   'required-local-contribution', 'teachers-per-pupil',
                                   'children-schooled-elsewhere', 'special-education-overruns',
                                   'surplus-bridge']),
    ],
    elsewhere=[('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_school_spending_topics.py'
TOPICS = {
    'per-pupil-spending': 'Spending per pupil',
    'per-pupil-line-by-line': 'Lunenburg per-pupil breakdown',
    'what-per-pupil-counts': 'What per pupil counts',
    'spending-by-function': 'Spending by function',
    'grants-in-school-spending': 'Grants and revolving funds',
    'cost-of-the-median': 'Reaching the state median',
    'comparison-districts': 'Comparison districts',
    'spending-and-pupils': 'Spending and pupils',
    'gap-by-function': 'Gap by function',
    'average-teacher-salary': 'Average teacher salary',
    'destination-district-spending': 'Destination districts',
    'regional-district-spending': 'Regional districts',
    'school-budget-against-actual': 'Budget against actual',
    'line-level-misses': 'Line-level misses',
    'school-committee-funds': 'School Committee funds',
    'school-revolving-funds': 'School revolving funds',
    'school-grant-balances': 'School grant balances',
    'revolving-fund-history': 'Revolving fund history',
}
