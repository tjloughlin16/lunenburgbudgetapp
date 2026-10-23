"""The Special education shelf. See scripts/topics.py for the model and the title rule.

Absorbs /special-education and the reports behind it (special-education-costs, sped-and-funds,
sped-and-the-curve, hiring-here-or-placing-there, /what-special-education-costs,
/how-many-students-are-on-an-iep, /who-ends-up-out-of-district), /circuit-breaker and
/special-education-class-size. Special education transportation is HOME on the
Transportation shelf and is listed here, one page on two shelves.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['in-district-special-education', 'tuition-budget'],
    id='special-education', shelf='Special education', title='Special education costs',
    area='school', order=20,
    groups=[
        ('What it costs', ['out-of-district-tuition', 'cost-per-placement',
                           'in-district-special-education', 'special-education-transportation']),
        ('What comes back', ['circuit-breaker', 'circuit-breaker-account']),
        # The same budget against every fund, home on the School budget, all funds shelf.
        # sped-all-funds: the vote beside every fund that paid, written by
        # build_school_all_funds.py (merged 23 October 2026 with the budget page that repeated it).
        ('Budgets and surprises', ['tuition-budget', 'special-education-overruns',
                                   'sped-all-funds']),
        ('Children and placements', ['students-with-an-iep', 'out-of-district-placements',
                                     'hiring-versus-placing', 'class-size-limits']),
        # The school MUNIS journal, every fund, posting by posting (notes/plans/
        # MUNIS-JOURNAL-REPORTS.md, Hub A). Written by build_journal_sped_topics.py.
        ('Who is paid, and from where', ['sped-providers', 'sped-burndown']),
    ],
    elsewhere=[('/enrolment/children-schooled-elsewhere', 'Children schooled elsewhere'),
               ('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_special_education_topics.py'
TOPIC_GENERATORS = {'sped-all-funds': 'build_school_all_funds.py',
                    'sped-providers': 'build_journal_sped_topics.py',
                    'sped-burndown': 'build_journal_surplus_topics.py'}
TOPICS = {
    'out-of-district-tuition': 'Out-of-district tuition',
    'cost-per-placement': 'Cost per placement',
    'in-district-special-education': 'In-district special education',
    'circuit-breaker': 'Circuit breaker',
    'circuit-breaker-account': 'Circuit breaker account',
    'tuition-budget': 'Tuition budget',
    'special-education-overruns': 'Special education overruns',
    'students-with-an-iep': 'Students with an IEP',
    'out-of-district-placements': 'Out-of-district placements',
    'hiring-versus-placing': 'Hiring versus placing',
    'class-size-limits': 'Class size limits',
    'sped-all-funds': 'Special education, all funds',
    'sped-providers': 'Special education providers',
    'sped-burndown': 'Special education burndown',
}
