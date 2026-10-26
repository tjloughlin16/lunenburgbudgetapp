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
    start=['circuit-breaker', 'reserve-options', 'surprise-costs'],
    id='special-education-reserve', shelf='SERF report', title='Special education reserve fund',
    # A special report (TJ, 24 Oct 2026): off the menu after the reserve's first full year.
    area='special', archive_after='2027-06-30', order=21,
    groups=[
        # In the order a board member asks (TJ, 24 October 2026: the story flow).
        # TJ, 26 October 2026: the five-step explanation "is solid on its own" -- the shelf's
        # overview, read first.
        # Merged into Circuit breaker the next day (TJ: "maybe we merge and only have one
        # called 'circuit breaker'"): it is home on Special education and listed here first.
        ('How it works', ['circuit-breaker']),
        ('What surprises, and when', ['surprise-costs', 'arrivals-and-the-budget']),
        ('What comes back, and when', ['how-tuition-is-paid', 'special-education-grants',
                                       'circuit-breaker-account']),
        # TJ, 24 October 2026: "propose ALL the options... and let someone pick".
        ('How big, and why a reserve', ['reserve-options', 'reserve-or-budget',
                                        'special-education-overruns']),
    ],
    elsewhere=[('/special-education', 'Special education costs'),
               ('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_serf_topics.py'
TOPICS = {
    'surprise-costs': 'Surprise costs',
    'arrivals-and-the-budget': 'Move-ins',
    # Retitled 26 October 2026 when its circuit breaker figures moved to Circuit breaker.
    'how-tuition-is-paid': 'Tuition after repayment',
    'special-education-grants': 'Special education grants',
    'reserve-options': 'Reserve options',
    'reserve-or-budget': 'Reserve or budget',
}
