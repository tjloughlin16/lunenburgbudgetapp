"""The SERF report shelf: the Special Education Reserve Fund, at /special-education-reserve. See
scripts/topics.py for the model and the title rule.

Asked for by TJ, 24 October 2026, ahead of the Select Board's reserve policy (27 October) and
the Special Town Meeting article funding it (17 November): *"the Special Education Reserve
Fund (SERF) balance we should maintain, what we should expect for State and Federal Grants,
what level of budget we should have."* Three questions, answered on six pages, with the
year-by-year overrun table (home on Special education) listed here as well.

The shelf's spine is his correction, the same day: *"the school committee just talks about the
big additions in the year as if they are always a problem. 'we brought in a kid and it cost us
$100k'. Thats a problem because we already budgeted for that"* -- a gross arrival is not an
unbudgeted cost, and the pages measure the second.
"""
CATEGORY = dict(
    start=['reserve-options', 'surprise-costs'],
    id='special-education-reserve', shelf='SERF report', title='Special education reserve fund',
    # A special report (TJ, 24 Oct 2026): off the menu after the reserve's first full year.
    area='special', archive_after='2027-06-30', order=21,
    groups=[
        # In the order a board member asks (TJ, 24 October 2026: the story flow).
        ('What surprises, and when', ['surprise-costs', 'arrivals-and-the-budget']),
        ('What comes back, and when', ['how-tuition-is-paid', 'special-education-grants',
                                       'circuit-breaker-account']),
        # TJ, 24 October 2026: "propose ALL the options... and let someone pick".
        ('How big, and why a reserve', ['reserve-options', 'reserve-size', 'reserve-or-budget',
                                        'special-education-overruns']),
    ],
    elsewhere=[('/special-education', 'Special education costs'),
               ('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_serf_topics.py'
TOPICS = {
    'surprise-costs': 'Surprise costs',
    'arrivals-and-the-budget': 'Move-ins',
    'how-tuition-is-paid': 'Out-of-district tuition payments',
    'special-education-grants': 'Special education grants',
    'reserve-options': 'Reserve options',
    'reserve-size': 'Draw rules',
    'reserve-or-budget': 'Reserve or budget',
}
