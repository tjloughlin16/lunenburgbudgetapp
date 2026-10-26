"""The Special education shelf. See scripts/topics.py for the model and the title rule.

Absorbs /special-education and the reports behind it (special-education-costs, sped-and-funds,
sped-and-the-curve, hiring-here-or-placing-there, /what-special-education-costs,
/how-many-students-are-on-an-iep, /who-ends-up-out-of-district), /circuit-breaker and
/special-education-class-size. Special education transportation is HOME on the
Transportation shelf and is listed here, one page on two shelves.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    # TJ, 26 October 2026: "i think 'sped-all-funds' should be the 'start here' for the special
    # education hub" -- the whole of what it costs, every fund, before any one line.
    start=['sped-all-funds', 'tuition-budget', 'circuit-breaker'],
    id='special-education', shelf='Special education', title='Special education costs',
    area='school', order=20,
    # EVERY SPECIAL EDUCATION PAGE ON THE SITE, wherever it is home (TJ, 26 October 2026: "we
    # have a BUNCH of reports about special education, but spread out across the reports page
    # ... collect all those into a hub"). A page listed here stays home on its own shelf. The
    # paraprofessional pages are NOT here: they count every paraprofessional, and which ones
    # serve special education is not published (rule 7).
    groups=[
        ('What it costs', ['sped-all-funds', 'out-of-district-tuition', 'cost-per-placement',
                           'in-district-special-education', 'special-education-transportation',
                           'sped-providers']),
        ('What comes back', ['sped-grants', 'circuit-breaker', 'circuit-breaker-account',
                             'special-education-grants', 'how-tuition-is-paid']),
        ('Budgets and surprises', ['tuition-budget', 'special-education-overruns',
                                   'fy2026-tuition-lines', 'sped-burndown']),
        # The reserve is a special report with its own hub; it is one door here.
        ('The reserve fund', ['special-education-reserve']),
        ('Children and placements', ['students-with-an-iep', 'out-of-district-placements',
                                     'hiring-versus-placing', 'class-size-limits']),
        # DESE's definition beside our three, function code by function code. Written by
        # build_sped_crosswalk.py, with the permanent list at sources/data/sped-crosswalk.csv.
        ('How it is counted', ['sped-definition']),
    ],
    elsewhere=[('/enrolment/children-schooled-elsewhere', 'Children schooled elsewhere'),
               ('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_special_education_topics.py'
TOPIC_GENERATORS = {'sped-all-funds': 'build_school_all_funds.py',
                    'sped-grants': 'build_school_all_funds.py',
                    # Merged 26 October 2026 with the SERF shelf's five steps, which need
                    # that script's measures (TJ: "only have one called 'circuit breaker'").
                    'circuit-breaker': 'build_serf_topics.py',
                    'sped-providers': 'build_journal_sped_topics.py',
                    'sped-burndown': 'build_journal_surplus_topics.py',
                    'sped-definition': 'build_sped_crosswalk.py'}
TOPICS = {
    'out-of-district-tuition': 'Out-of-district tuition',
    'cost-per-placement': 'Cost per placement',
    'in-district-special-education': 'In-district special education',
    'circuit-breaker': 'Circuit breaker',
    'circuit-breaker-account': 'Circuit breaker account',
    'tuition-budget': 'Tuition budget',
    # Retitled 23 October 2026 to 'Special education reserve', and back on 24 October when the
    # SERF report took that name for its own shelf (/special-education-reserve), which lists
    # this page too. The address is unchanged (it was shared).
    'special-education-overruns': 'Special education overruns',
    'students-with-an-iep': 'Students with an IEP',
    'out-of-district-placements': 'Out-of-district placements',
    'hiring-versus-placing': 'Hiring versus placing',
    'class-size-limits': 'Class size limits',
    'sped-all-funds': 'Special education, all funds',
    # Every special education stream outside the vote, by name (TJ, 26 October 2026: "we ALSO
    # need a general 'special education grants' page that does it all").
    'sped-grants': 'Special education grants',
    'sped-providers': 'Special education providers',
    'sped-burndown': 'Special education burndown',
    'sped-definition': 'Special education definition',
}
