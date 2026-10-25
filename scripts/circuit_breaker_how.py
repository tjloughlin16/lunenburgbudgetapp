"""HOW THE CIRCUIT BREAKER ACCOUNT WORKS, as numbered steps, for every page that shows it.

TJ, 24 October 2026, on this explanation as first written in conversation: *"your definition
of circuit breaker and how it works above is PERFECT. can you make sure thats on the page
somewhere... super easy to follow."* It is drawn on the SERF hub and on the circuit breaker
account page, so it lives here once: two copies of one explanation drift apart.

Every figure comes from the account's own year rows (special-education-costs.json
cb_account.years: opening, received, spent, closing, budgeted), so the worked example moves
when the ledger does.
"""
import conclusions as C
from conclusions import figure
import topic as TP


def steps(years):
    """years: the cb_account year rows. Returns topic.how()."""
    cy = {r['fy']: r for r in years}
    ys = sorted(cy)
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    planned = [y for y in ys if cy[y]['budgeted'] and cy[y]['budgeted'] > 1]
    if not planned:
        raise SystemExit('circuit_breaker_how: no year records planned spending from the account')
    py = planned[0]
    left = sorted(sorted(ys, key=lambda y: cy[y]['spent'] - cy[y]['received'])[:3])
    if any(cy[y]['received'] <= cy[y]['spent'] for y in left):
        raise SystemExit('circuit_breaker_how: fewer than three years the account was not fully spent')
    dy = max(ys, key=lambda y: cy[y]['spent'] - cy[y]['received'])
    d = cy[dy]
    below = [y for y in ys if cy[y]['closing'] < 0]
    if below != list(range(below[0], below[-1] + 1)):
        raise SystemExit('circuit_breaker_how: the years below zero are not one run: %s' % below)
    return TP.how('How the circuit breaker account works', [
        'Lunenburg pays a placement’s out-of-district tuition this year, out of the general fund.',
        ('The next year the state sends back part of it: the circuit breaker. That money goes into '
         'a separate account, fund 2640, not the general fund.', None, ('2640',)),
        # The district's own words (2023-2024 circuit breaker presentation): "may be expended by
        # the school committee in the year received or in the following... for any special
        # education-related purposes, without further appropriation."
        'The School Committee can spend it on special education without a Town Meeting vote, in '
        'the year it arrives or the next, mostly on out-of-district tuition. Every dollar paid '
        'from it is one the general fund does not pay.',
        # Planned, not proven: whether the voted tuition line is set LOWER because of it is a
        # registered gap on the account page; the planned spending is what the ledger shows.
        ('So part of the tuition bill is planned to come from the account, not the general fund '
         'budget: for %s the district planned to spend %s from it.' % (C.fy(py), C.usd(cy[py]['budgeted'])),
         {'y': F(py), 'a': U(cy[py]['budgeted'])}),
        ('Not fully spent: the state sent more than the account paid that year. The leftover stays, '
         'the balance grows, and it cushions a later year, as in %s, %s and %s.'
         % tuple(C.fy(y) for y in left), {'a': F(left[0]), 'b': F(left[1]), 'c': F(left[2])}),
        ('Overspent: the account paid more than the state sent, so it used savings. In %s the state '
         'sent %s and the account paid %s; the balance fell from %s to %s.'
         % (C.fy(dy), C.usd(d['received']), C.usd(d['spent']), C.usd(d['opening']), C.usd(d['closing'])),
         {'y': F(dy), 'a': U(d['received']), 'b': U(d['spent']), 'c': U(d['opening']), 'd': U(d['closing'])}),
        ('From %s to %s it paid out more than it had and closed below zero.'
         % (C.fy(below[0]), C.fy(below[-1])), {'y': F(below[0]), 'z': F(below[-1])}),
        'So the account works as an unvoted reserve: a surprise paid from it never shows on the '
        'general fund line. A reserve fund would do the same job in the open.',
    ])
