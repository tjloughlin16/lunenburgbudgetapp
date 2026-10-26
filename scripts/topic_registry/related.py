"""RELATED PAGES: which topic pages a reader of one should be offered next, across shelves.

WHY. TJ, 23 October 2026: *"i think we need to figure out how to create 'related topic
pages'. /school-all-funds/grants-others-receive and /school-all-funds/grant-allocations-compared
need to somehow suggest each other."* A shelf gives a page its previous and next; it says
nothing about the page on ANOTHER shelf that answers the next question -- the reserve page
sits under Special education, the funds that paid the overrun under the whole school budget.

THE ONE PLACE. Not a module of its own category: scripts/topics.py reads every other file in
this folder as a shelf and skips this one. scripts/build_topics_index.py validates it and
writes each page's `related` list into fy28/public/data/topics.json, which the page reads.

THE SHAPE. A CLUSTER is a list of members, two or more. Every member is shown on every other
member's page -- symmetric by construction, so declaring A with B can never leave B silent
about A. A member is

    (id, why)              a topic id or a category (hub) id
    (path, title, why)     any other page on the site, e.g. '/grants-open-to-lunenburg'

`why` describes THAT member -- what a reader gets by going there -- and is drawn beside its
title. It is a phrase, not a finding: no figures (rule 2: a figure typed into prose is the
one thing here that can go silently wrong), at most WHY_MAX characters, no closing full stop.

A path member is linked FROM the topics in its cluster, but is not a topic page, so it draws
no Related block of its own. Its first segment must be a route the app declares
(fy28/src/routes.ts) -- checked, so a renamed page fails the build rather than linking to
nowhere.

THE RULES, enforced by check() in build_topics_index.py: every id is registered; nothing is
related to itself; no page is offered the same target twice; a page carries at most
MAX_PER_PAGE related pages. Past that it is a second shelf, not a short list.

    python3 scripts/build_topics_index.py --suggest-related   # candidates, ranked by shared
                                                              # sources; NOT accepted by it
"""
WHY_MAX = 70
MAX_PER_PAGE = 4

RELATED = [
    # The SERF report: what the reserve meets, against what it would cost to budget instead.
    [('arrivals-and-the-budget', 'Whether a mid-year arrival left the year short'),
     ('surprise-costs', 'Which special education lines run over their vote'),
     ('reserve-options', 'Seven sizes for the reserve, and which overspending it pays for')],
    [('reserve-options', 'Seven sizes for the reserve, and which overspending it pays for'),
     ('reserve-or-budget', 'The same money held once, or added to every vote')],
    [('reserve-or-budget', 'The same money held once, or added to every vote'),
     ('fy2026-snow-and-reserve-fund', 'How the town budgets another line that surprises')],
    # The grants a district gets, three ways: won in competition, allocated by formula, open now.
    [('grants-others-receive', 'Competitive grants comparable districts won that Lunenburg did not'),
     ('grant-allocations-compared', 'The formula grants every district gets, per pupil'),
     ('/grants-open-to-lunenburg', 'Grants open to Lunenburg',
      'The state grant programs the district can apply for now')],
    # Who grants and fees pay for (TJ, 24 October 2026): the athletic fee fund's pay, and the
    # posts the directory lists against the accounts that pay them.
    [('pay-moved-between-funds', 'Pay moved between the fee fund and the general fund'),
     ('fee-fund-ledger', 'The athletic fee fund’s cash, year by year')],
    [('positions-and-their-funds', 'Which fund pays each leadership post'),
     ('district-staff-directory', 'Who the district lists, by title')],
    # How grants are booked against the voted lines, and the total spent outside the vote.
    [('grant-coding', 'How much grant spending lands on a voted budget line'),
     ('outside-the-general-fund', 'What the funds outside the voted budget spent, as a share of the whole')],
    # Special education beyond its vote: how big, who paid, what is counted, what the state covers.
    [('special-education-overruns', 'What a reserve would have had to cover, year by year'),
     ('sped-all-funds', 'Which other funds paid when special education passed its vote'),
     ('sped-definition', 'Why our special education total differs from the state’s'),
     ('circuit-breaker', 'What the state reimburses for the costliest placements'),
     ('circuit-breaker-account', 'What the circuit breaker account holds at each year end')],
    # Special education grants: every stream by name, beside the grants a surprise may draw on.
    [('sped-grants', 'Every special education grant and the circuit breaker, by year'),
     ('special-education-grants', 'Which grants could pay for a mid-year surprise'),
     ('/special-education/circuit-breaker', 'Circuit breaker',
      'How the state works out its reimbursement')],
    # Money left over: carried as orders, held in funds, set against each budget line.
    [('carried-over-orders', 'Open orders carried from one year into the next'),
     ('unspent-by-fund', 'What each fund held unspent at the end of the year'),
     ('budget-lines-all-funds', 'Every budget line, with what all funds spent on it')],
    # The funds outside the vote: what came in, and what went out.
    [('school-money-in', 'What the funds outside the budget took in, and from where'),
     ('outside-the-general-fund', 'What the funds outside the voted budget spent, as a share of the whole')],
    # Accepted by TJ from --suggest-related, 23 October 2026.
    [('harvard-per-pupil', 'What Harvard spends a pupil, beside Lunenburg'),
     ('lunenburg-at-harvard-rate', 'Lunenburg’s budget at Harvard’s rate a pupil'),
     ('lunenburg-at-monty-tech-rate', 'Lunenburg’s budget at Monty Tech’s rate a pupil')],
    [('pay-or-headcount', 'Fewer teachers, each costing more: what moved the line'),
     ('salary-line-and-staffing', 'What holding the salary line does to positions'),
     ('teacher-contract', 'What the next teachers’ agreement moves in the gap')],
    [('cherry-sheet-variance', 'How state aid came in against the estimate'),
     ('free-cash-balance', 'How much free cash the state certified'),
     ('free-cash-sources', 'Where the free cash came from')],
    [('fy2026-tuition-lines', 'The tuition lines at year end, against next year’s budget'),
     ('fy2027-bus-budget', 'Next year’s bus budget, school-day and athletic')],
    # TJ could not find the Monty Tech and Lunenburg funding comparison from the hub.
    [('monty-tech-revenue', 'Monty Tech and Lunenburg schools, revenue by source'),
     ('monty-tech-funding', 'What pays Monty Tech’s operating budget'),
     ('monty-tech-per-pupil', 'What Monty Tech spends a pupil')],
]
