"""The Budget options shelf: what each way of closing the school gap yields, and who bears it.
See scripts/topics.py for the model and the title rule.

Absorbs /override, /fees (feelever), /extras (extraslever), /classrooms (positionslever),
/salaries (salarylever), /analysis/fy27-and-the-override and /analysis/fy27-cut-reconciliation,
and /what-families-pay (families): what a household is charged, by tier, and what has no price.
There is no full report: every question those answered has one page here.

Options answered on other shelves are LISTED here, one page on two shelves, never rebuilt:
free cash for schools and the stabilization fund (Town reserves), the athletic fee
(Athletics), the bus fee (Transportation), the cut lists (School programs).
"""
CATEGORY = dict(
    id='budget-options', shelf='Budget options', title='Closing the gap', area='options',
    order=70,
    groups=[
        ('Overrides', ['override-history', 'fy2027-override', 'override-duration',
                       'override-scope']),
        ('Fees', ['family-fees', 'reduced-and-waived-fees', 'unpriced-school-charges',
                  'school-user-fees', 'athletic-fee', 'bus-fee']),
        ('Cuts', ['extracurricular-cuts', 'classroom-positions', 'fy2027-cut-size',
                  'announced-cuts', 'override-cut-lists']),
        ('Pay', ['teacher-contract', 'salary-line-and-staffing']),
        ('Reserves', ['free-cash-redirect', 'reserves-and-the-gap']),
    ],
    elsewhere=[('/health-insurance', 'Health insurance options')])
GENERATOR = 'build_budget_options_topics.py'
TOPICS = {
    'override-history': 'Override history',
    'fy2027-override': 'The FY2027 override',
    'override-duration': 'Override duration',
    'override-scope': 'Townwide or school-only',
    'family-fees': 'Family fees',
    'reduced-and-waived-fees': 'Reduced and waived fees',
    'unpriced-school-charges': 'Unpriced school charges',
    'school-user-fees': 'School user fees',
    'extracurricular-cuts': 'Extracurricular cuts',
    'classroom-positions': 'Classroom positions',
    'fy2027-cut-size': 'FY2027 cut size',
    'teacher-contract': 'Teacher contract',
    'salary-line-and-staffing': 'Salary line and staffing',
}
