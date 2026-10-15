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
    id='monty-tech', shelf='Monty Tech', title='Monty Tech finances', area='school', order=22,
    groups=[
        ('Lunenburg’s pupils there', ['monty-tech-enrolment']),
        ('What Lunenburg pays', ['monty-tech-assessment', 'monty-tech-funding']),
        ('What it spends a pupil', ['monty-tech-per-pupil', 'what-per-pupil-counts']),
    ],
    elsewhere=[('/analysis/monty-tech', 'The full Monty Tech report')])
GENERATOR = 'build_monty_tech_topics.py'
TOPICS = {
    'monty-tech-per-pupil': 'Monty Tech per pupil',
}
