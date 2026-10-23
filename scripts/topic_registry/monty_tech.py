"""The Monty Tech shelf: the regional vocational school Lunenburg belongs to -- its pupils, what
Lunenburg pays, and what it spends a pupil. See scripts/topics.py for the model and the title rule.

TJ, 14-15 October 2026, after people in town said *"some districts include their capital
projects and some districts do not"* in per-pupil spending: *"Monty Tech might need to become a
hub?"* It took the address /monty-tech; the long report it came from moved to
/analysis/monty-tech, still served because sources cite it.

The enrolment, the assessment and the funding pages are HOME on Enrolment and stay there, so
their addresses do not change; "What per pupil counts" is HOME on School spending, because it
answers a question about every district. All four are listed here. One page, many shelves.
"""
CATEGORY = dict(
    # Start here: the pages that most directly answer this shelf (picked 19 October 2026).
    start=['monty-tech-per-pupil'],
    id='monty-tech', shelf='Monty Tech', title='Monty Tech finances', area='school', order=90,  # Other schools, last (TJ, 22 Oct 2026)
    groups=[
        ('Lunenburg’s pupils there', ['monty-tech-enrolment']),
        ('What Lunenburg pays', ['monty-tech-assessment']),
        ('Where its money comes from', ['monty-tech-funding', 'monty-tech-revenue']),
        ('What it spends a pupil', ['monty-tech-per-pupil', 'monty-tech-line-by-line',
                                    'per-pupil-line-by-line', 'lunenburg-at-monty-tech-rate',
                                    'what-per-pupil-counts']),
    ],
    elsewhere=[('/analysis/monty-tech', 'The full Monty Tech report')])
GENERATOR = 'build_monty_tech_topics.py'
TOPICS = {
    'monty-tech-per-pupil': 'Monty Tech per pupil',
    'monty-tech-line-by-line': 'Monty Tech per-pupil breakdown',
    'lunenburg-at-monty-tech-rate': 'Monty Tech rate scenario',
    # Retitled 23 Oct 2026: TJ could not find the Lunenburg comparison under 'Monty Tech revenue'.
    'monty-tech-revenue': 'Funding sources compared',
}
