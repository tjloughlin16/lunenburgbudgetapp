"""Revenue and savings levers other than cutting programs.

Each lever carries what it is worth, what it actually requires, and an honest caveat.
Dollar figures are from the FY27 adopted budget unless noted.
"""

ADMIN_TOTAL = 2_633_246          # every administration line, FY27 balanced
ADMIN_CENTRAL = 1_040_389        # superintendent, business, HR, legal, admin tech, directors
ADMIN_BUILDING = 1_183_773       # the four principals' offices and their secretaries
TECH_TOTAL = 638_675             # contracts, licences, device leases, tech personnel
HEALTH_TOTAL = 3_994_071         # FY27 balanced
TRANSPORT_GENED = 1_053_360
TRANSPORT_SPED = 649_953
ATHLETIC_PARTICIPATIONS = 691

# The 2026-27 athletic fee, blended per participation, and the base it can be charged on.
# Middle school teams are unfunded in the adopted budget, so only the 582 high-school
# participations are chargeable. Derived in athletics.py.
from athletics import (EFFECTIVE_ATHLETIC_FEE as ATHLETIC_FEE_NOW,
                       CHARGEABLE_PARTICIPATIONS, PROGRAM_TOTAL_ADOPTED,
                       PROGRAM_TOTAL_TRAVEL)

LEVERS = [
 dict(id='athletic_fees', name='Athletics user fees', kind='revenue',
      unit='new fee per season, per athlete', max=1400, step=25,
      current=ATHLETIC_FEE_NOW, default=960, selfFunding=960,
      peakFee=1185, peakYield=358380, currentYield=187451,
      basis=CHARGEABLE_PARTICIPATIONS,
      cap=PROGRAM_TOTAL_TRAVEL,
      what='Lunenburg ALREADY charges, and just raised the fee. For 2026-27 it is $400 '
           'for a first child, $300 for a second and $225 for a third, with a $1,500 '
           'family cap — up from $250/$140/$85 and a $475 cap. Blended across sibling '
           'discounts that is roughly $366 per chargeable participation, raising an '
           'estimated $187,000. That is 86% of the $217,908 the adopted budget funds — '
           'but the adopted budget funds no athletic transportation at all. Add the '
           '$127,550 of buses back and the real cost of fielding these teams is '
           '$345,458, fees cover 54%, and self-funding takes $960 a season.',
      caveat='$960 a season is roughly a 140% increase on a fee that just rose 60%, and '
             'it buys only the teams that survived — no full-time trainer, no restored '
             'coaching stipends, no middle school. Everything above $345,458 is '
             'unreachable at any price: revenue peaks near $1,185 at about $358,000. And '
             'the budgeted athletic director line is a $20,000 stipend that no longer '
             'reflects a full-time role, so even these targets are understated.',
      benchmark='Lunenburg $400 (was $250) · Duxbury $300 · Winchester $600 · Bridgewater-Raynham considered $950'),

 dict(id='activity_fees', name='Band, music & club fees', kind='revenue',
      unit='fee per student, per activity', max=900, step=10,
      current=0, default=465, selfFunding=465, peakFee=835, peakYield=132812,
      currentYield=0,
      basis=375, basisKnown=False,
      cap=106_244,
      what='Covers the high school music position, music supplies, band transportation '
           'and club advisors — $106,244 in total. We could not confirm whether the '
           'district charges an activity fee today; the default here assumes none.',
      caveat='Participation is a placeholder: the district does not publish it. At $465 '
             'these programmes self-fund on paper, but that is a steep charge for a club, '
             'and the students who quit first are the ones for whom the club is the reason '
             'they come to school.',
      benchmark='Ashburnham-Westminster collects $215,000/yr in student fees overall'),

 dict(id='bus_fees', name='School bus fees', kind='revenue',
      unit='new fee per rider, per year', max=900, step=25,
      current=180, default=715, selfFunding=None, peakFee=715, peakYield=146006,
      currentYield=64260,
      basis=420, basisKnown=False,
      cap=TRANSPORT_GENED,
      what='Lunenburg ALREADY charges: $180 per student, $270 family cap, with $50/$75 '
           'reduced rates and free transport for qualifying families. Grades 7–12 all pay; '
           'K–6 pay only if they live under two miles from school, since state law requires '
           'free transport beyond that.',
      caveat='Self-funding transport is not remotely reachable — general-education '
             'transport costs $1,053,360 and revenue peaks near $146,000. Special education '
             'transport ($649,953) cannot be charged for at all. Higher fees also push '
             'families into cars, which raises per-rider cost on the routes that remain.',
      benchmark='Common across Massachusetts at $200–$500 per rider, usually with a family cap'),

 dict(id='health_design', name='Health insurance — employee share', kind='saving',
      unit='employee share of the premium', max=40, step=1, default=25,
      current=25, isPercentPoint=True, basis=5_331_280,
      cap=5_331_280 * 0.15 * 0.75,
      # M.G.L. c.32B §§21-23 requires 25% of first-year savings back to employees as
      # mitigation, so the district keeps only three quarters of the shift. The health
      # panel already applied this; this lever did not, and the two disagreed by 25%.
      mitigation=0.75,
      what='The Town pays 75% of the premium and the employee 25%. Every point shifted to '
           'employees moves about $53,300 of premium — but 25% of first-year savings must '
           'go back to employees as mitigation, so the district keeps roughly $40,000 a '
           'point. It costs a family on the broadest plan about $440 a year.',
      caveat='This is a pay cut in everything but name. Plan design changes go through the '
             'Public Employee Committee under M.G.L. c.32B §§21-23 and 25% of first-year '
             'savings must go back to employees as mitigation. The Town, not the district, '
             'controls the insurance group. Multi-year, and bargained.',
      benchmark='Health insurance rose 8–14% across every neighbouring district in FY27; '
                'Lunenburg premiums rose 5.38% for FY27'),

 dict(id='admin_cut', name='Administration reduction', kind='saving',
      unit='% of all administration', max=25, step=1, default=0, isPercent=True,
      basis=ADMIN_TOTAL,
      cap=ADMIN_TOTAL * 0.25,
      what=f'All administration totals ${ADMIN_TOTAL:,} — 9.9% of the budget. That splits '
           f'into ${ADMIN_CENTRAL:,} central office and ${ADMIN_BUILDING:,} for the four '
           'principals\' offices and their secretaries.',
      caveat='The most commonly suggested cut, and smaller than people expect. Lunenburg '
             'already runs one superintendent, one business manager and one HR specialist '
             'for four schools, and the FY27 budget cut an Assistant Principal so the '
             'Primary School and Turkey Hill now share one. State reporting is a legal '
             'obligation with financial penalties attached.',
      benchmark='DESE puts Lunenburg administration at $1,158,507 in FY24 — below every '
                'peer district except Ashburnham-Westminster'),

 dict(id='tech_cut', name='Software, licences & devices', kind='saving',
      unit='% of technology spend', max=60, step=5, default=0, isPercent=True,
      basis=TECH_TOTAL,
      cap=TECH_TOTAL * 0.6,
      what=f'Technology totals ${TECH_TOTAL:,}: ${185_065:,} device leases, '
           f'${154_981:,} administrative contracts, ${55_230:,} networking, '
           f'${13_800:,} guidance software, plus per-school contracts and tech staff.',
      caveat='Real money and genuinely reviewable — duplicate licences are common. But '
             'state testing, IEP management, student information and payroll all run on '
             'these systems, and devices that are not replaced still have to be repaired. '
             'Ashburnham-Westminster cut technology 5.8%, not 60%.',
      benchmark='Ashburnham-Westminster reduced technology 5.8% in FY27'),
]
if __name__ == '__main__':
    for l in LEVERS:
        print(f"{l['name']:<34} {l['kind']:<8} cap ${l['cap']:>10,.0f}")
