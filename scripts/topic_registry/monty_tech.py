"""The Monty Tech shelf: the regional vocational school Lunenburg belongs to -- its pupils, what
Lunenburg pays, and what it spends a pupil. See scripts/topics.py for the model and the title rule.

TJ, 14-15 October 2026, after people in town said *"some districts include their capital
projects and some districts do not"* in per-pupil spending: *"Monty Tech might need to become a
hub?"* It took the address /monty-tech; the long report it came from moved to
/analysis/monty-tech, still served because sources cite it.

The enrolment, the assessment and the funding pages were HOME on Enrolment until 26 October 2026,
when TJ asked that "all the monty tech pages should show up ONLY in the monty tech section". They
are home here now (still written by build_enrolment_topics.py); their old /enrolment/ addresses
still open them, because a topic is fetched by id. "What per pupil counts" stays HOME on School
spending, because it answers a question about every district, and is listed here too.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['monty-tech-per-pupil'],
    # TJ, 26 October 2026: a section of its own on /reports, "comparison districts".
    id='monty-tech', shelf='Monty Tech', title='Monty Tech finances', area='compare', order=90,
    groups=[
        ('Lunenburg’s pupils there', ['monty-tech-enrolment']),
        ('What Lunenburg pays', ['monty-tech-assessment', 'monty-tech-history']),
        ('Where its money comes from', ['monty-tech-funding', 'monty-tech-revenue']),
        ('What it spends a pupil', ['monty-tech-per-pupil', 'monty-tech-line-by-line',
                                    'per-pupil-line-by-line', 'lunenburg-at-monty-tech-rate',
                                    'what-per-pupil-counts']),
    ],
    elsewhere=[('/analysis/monty-tech', 'The full Monty Tech report')])
GENERATOR = 'build_monty_tech_topics.py'
TOPIC_GENERATORS = {'monty-tech-enrolment': 'build_enrolment_topics.py',
                    'monty-tech-assessment': 'build_enrolment_topics.py',
                    'monty-tech-funding': 'build_enrolment_topics.py',
                    'monty-tech-history': 'build_monty_tech_history.py'}
TOPICS = {
    'monty-tech-enrolment': 'Monty Tech enrolment',
    'monty-tech-assessment': 'Monty Tech assessment',
    'monty-tech-funding': 'Monty Tech funding',
    # TJ, 31 October 2026: when Lunenburg joined, and what it has paid every year since.
    'monty-tech-history': 'Monty Tech history',
    'monty-tech-per-pupil': 'Monty Tech per pupil',
    'monty-tech-line-by-line': 'Monty Tech per-pupil breakdown',
    'lunenburg-at-monty-tech-rate': 'Monty Tech rate scenario',
    # Retitled 23 Oct 2026: TJ could not find the Lunenburg comparison under 'Monty Tech revenue'.
    'monty-tech-revenue': 'Funding sources compared',
}
