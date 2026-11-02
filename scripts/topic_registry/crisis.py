"""The Budget crisis shelf: why the school budget comes up short every year, broken out of the
/crisis walkthrough (fy28/src/pages/Walkthrough.tsx). See scripts/topics.py for the model and
the title rule.

TJ, 18 October 2026: break the walkthrough into hub and spoke so residents can look directly at
one piece of it. The walkthrough was eleven rooms in a fixed order; each room's question is
either a page here or a page another shelf already holds, LISTED here and never copied:

  room 1  what has already happened      fy2027-cut-size, announced-cuts, fy2027-override
  room 2  level service                  level-service-cost                         (here)
  room 3  the levy ceiling               fy2028-revenue-increase                    (here)
  room 4  costs against revenue          level-service-cost, fy2028-revenue-increase
  room 5  the line within its means      gap-by-cost-line                           (here)
  room 6  two rates                      cost-and-revenue-growth, projected-gap     (here)
  room 7  what cuts are worth            all-cuts-combined (here); extracurricular-cuts,
                                         classroom-positions, school-user-fees
  room 8  what one override buys         override-duration, override-scope, free-cash-redirect
  room 9  commercial development         commercial-development (here); new-growth,
                                         business-building-pace
  room 10 the State House                chapter-70-needed (here); total-state-aid,
                                         state-aid-growth, foundation-budget
  room 11 what "solved" requires         long-run-balance-rate (here); teacher-contract,
                                         salary-line-and-staffing, health-insurance-options

AREA. 'options', beside Closing the gap: this shelf is the problem the options on that shelf
answer, and every page here is the projection (ours), not a record of the schools. The school
area holds what the district published; a forward projection sitting among those records would
read as one of them.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['gap-by-cost-line', 'all-cuts-combined'],
    id='crisis', shelf='Budget crisis', title='The structural gap', area='crisis',
    order=1,
    # TWO PARTS, THE PROBLEM AND THE SOLUTIONS. TJ, 2 November 2026, after searching for the
    # commercial development page and not finding it: *"when people bring up something they
    # think is a solution, I want to just go straight there, find the link and share it"*. So
    # each solution is a group named the way people SAY it, and the Budget options shelf is
    # folded in here as that part (topic_registry/budget_options.py, `merged_into`).
    sections={'The gap': 'The problem', 'Why it comes back': 'The problem',
              'What has happened': 'The problem',
              'Commercial development': 'Solutions', 'An override': 'Solutions',
              'Cuts': 'Solutions', 'Fees': 'Solutions', 'Reserves and free cash': 'Solutions',
              'More state aid': 'Solutions', 'Pay and insurance': 'Solutions'},
    groups=[
        ('The gap', ['projected-gap', 'level-service-cost', 'fy2028-revenue-increase']),
        ('Why it comes back', ['gap-by-cost-line', 'cost-and-revenue-growth',
                               'long-run-balance-rate']),
        ('What has happened', ['fy2027-cut-size', 'announced-cuts']),
        ('Commercial development', ['commercial-development', 'new-growth',
                                    'business-building-pace', 'commercial-share']),
        ('An override', ['override-history', 'fy2027-override', 'override-duration',
                         'override-scope']),
        ('Cuts', ['all-cuts-combined', 'extracurricular-cuts', 'classroom-positions',
                  'override-cut-lists']),
        ('Fees', ['family-fees', 'reduced-and-waived-fees', 'unpriced-school-charges',
                  'school-user-fees', 'athletic-fee', 'bus-fee']),
        ('Reserves and free cash', ['free-cash-redirect', 'reserves-and-the-gap']),
        ('More state aid', ['chapter-70-needed', 'total-state-aid', 'state-aid-growth',
                            'foundation-budget']),
        ('Pay and insurance', ['teacher-contract', 'salary-line-and-staffing',
                               'health-insurance-options']),
    ],
    elsewhere=[('/commercial-development', 'Commercial development, the full report'),
               ('/try-growth', 'Growth dials'), ('/solutions', 'Every solution, priced')])
GENERATOR = 'build_budget_crisis_topics.py'
TOPICS = {
    'projected-gap': 'Projected school gap',
    'level-service-cost': 'Level service cost',
    'fy2028-revenue-increase': 'FY2028 revenue increase',
    'gap-by-cost-line': 'Gap by cost line',
    'cost-and-revenue-growth': 'Cost and revenue growth',
    'long-run-balance-rate': 'Long-run balance rate',
    'all-cuts-combined': 'All cuts combined',
    'commercial-development': 'Commercial development',
    'chapter-70-needed': 'Chapter 70 needed',
}
