"""The School spending shelf. See scripts/topics.py for the model and the title rule.

Absorbs /what-other-districts-spend ('peers', per-pupil-spending.md), spending-compared.md,
peer-districts.md and /budget-vs-actual ('variance'). Two different questions live here and are
kept apart: what the schools spend for each pupil against other districts (DESE's all-funds
figures, reported after a year closes), and whether the school budget matched what was spent
(budget and actual side by side, same year, never differenced across years -- rule 1).

Every comparison says who chose the districts: the state (every district DESE publishes), the
families (where Lunenburg children actually went), or this project (the six-district set).

The Chapter 70 spending floor is HOME on the State aid shelf, the teacher ratio on School
staffing, children schooled elsewhere on Enrolment, the special education overruns on Special
education and the two school surpluses on FY2026 closeout; each is listed here, one page on
two shelves.
"""
CATEGORY = dict(
    id='school-spending', shelf='School spending', title='Spending compared', area='school',
    order=24,
    groups=[
        ('Against the state', ['per-pupil-spending', 'spending-by-function',
                               'grants-in-school-spending', 'cost-of-the-median']),
        ('Against other districts', ['comparison-districts', 'spending-and-pupils',
                                     'gap-by-function', 'average-teacher-salary',
                                     'destination-district-spending',
                                     'regional-district-spending']),
        ('Budget against actual', ['school-budget-against-actual', 'line-level-misses']),
        ('Elsewhere on the site', ['net-school-spending', 'net-school-spending-rank',
                                   'required-local-contribution', 'teachers-per-pupil',
                                   'children-schooled-elsewhere', 'special-education-overruns',
                                   'fy2025-school-surplus', 'fy2026-school-surplus']),
    ],
    elsewhere=[('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_school_spending_topics.py'
TOPICS = {
    'per-pupil-spending': 'Spending per pupil',
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
}
