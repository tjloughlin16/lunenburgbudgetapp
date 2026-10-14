"""The Enrolment shelf: who is in Lunenburg's schools, who leaves, and where they go. See
scripts/topics.py for the model and the title rule.

Absorbs /who-is-in-the-schools (enrollment), /which-grades-students-leave (attrition),
/where-students-go-instead (outflow), /if-students-leave (leaving) and /monty-tech
(montytech). There is no full report: every question those five answered has one page here.
Two pages on the shelf belong to Special education and are only LISTED here -- the count of
children with a plan, and the children placed out of district. One question, one page, one
address.
"""
CATEGORY = dict(
    id='enrolment', shelf='Enrolment', title='Students and schools', area='school', order=21,
    groups=[
        ('How many', ['enrolment-by-year', 'enrolment-by-grade-band', 'high-needs-students',
                      'nearby-district-enrolment']),
        ('Who leaves, and when', ['grade-to-grade-loss', 'grade-8-loss-trend',
                                  'leaving-and-arriving']),
        ('Where they go', ['children-schooled-elsewhere', 'school-choice-flows',
                           'departure-scenario']),
        ('Monty Tech', ['monty-tech-enrolment', 'monty-tech-assessment', 'monty-tech-funding']),
        ('High school to high school', ['high-school-enrolment', 'high-school-spending']),
        ('Students with plans', ['students-with-an-iep', 'out-of-district-placements']),
    ],
    elsewhere=[('/if-students-leave', 'The departure scenario, with its dials')])
GENERATOR = 'build_enrolment_topics.py'
TOPICS = {
    'enrolment-by-year': 'Enrolment by year',
    'enrolment-by-grade-band': 'Enrolment by grade band',
    'high-needs-students': 'High-needs students',
    'nearby-district-enrolment': 'Nearby district enrolment',
    'grade-to-grade-loss': 'Grade-to-grade loss',
    'grade-8-loss-trend': 'Grade 8 loss trend',
    'leaving-and-arriving': 'Leaving and arriving',
    'children-schooled-elsewhere': 'Children schooled elsewhere',
    'school-choice-flows': 'School choice flows',
    'departure-scenario': 'Departure scenario',
    'monty-tech-enrolment': 'Monty Tech enrolment',
    'monty-tech-assessment': 'Monty Tech assessment',
    'monty-tech-funding': 'Monty Tech funding',
    'high-school-enrolment': 'High school enrolment',
    'high-school-spending': 'High school spending',
}
