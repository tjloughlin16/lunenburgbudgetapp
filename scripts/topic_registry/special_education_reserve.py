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
    # TJ, 26 October 2026: "the circuit breaker is not a 'start here' page ... 'reserve or
    # budget' is likely a start here".
    start=['reserve-or-budget', 'reserve-options', 'surprise-costs'],
    id='special-education-reserve', shelf='SERF report', title='Special education reserve fund',
    # A special report (TJ, 24 Oct 2026): off the menu after the reserve's first full year.
    area='special', archive_after='2027-06-30', order=21,
    groups=[
        # In the order a board member asks (TJ, 24 October 2026: the story flow).
        ('What surprises, and when', ['surprise-costs', 'arrivals-and-the-budget']),
        # Circuit breaker (merged with the five steps, 26 October 2026) leads what comes back.
        ('What comes back, and when', ['circuit-breaker', 'how-tuition-is-paid',
                                       'special-education-grants', 'circuit-breaker-account']),
        # TJ, 24 October 2026: "propose ALL the options... and let someone pick".
        ('How big, and why a reserve', ['reserve-or-budget', 'reserve-options']),
        # TJ, 26 October 2026: "supporting data that is captured in the other pages". Its totals
        # are on Reserve options; the line-by-line years and the levels table are only here.
        ('The year-by-year record', ['special-education-overruns']),
    ],
    elsewhere=[('/special-education', 'Special education costs'),
               ('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_serf_topics.py'
TOPICS = {
    'surprise-costs': 'Surprise costs',
    'arrivals-and-the-budget': 'Move-ins',
    # Retitled 26 October 2026 when its circuit breaker figures moved to Circuit breaker.
    'how-tuition-is-paid': 'Tuition after repayment',
    # Retitled 26 October 2026: it answers what can meet a surprise; every special education grant
    # is on /special-education/sped-grants (TJ: "the title is 'special education grants' not
    # related to surprises").
    'special-education-grants': 'Grants for surprises',
    'reserve-options': 'Reserve options',
    'reserve-or-budget': 'Reserve or budget',
}
