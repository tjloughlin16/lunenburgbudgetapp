"""Per-sport athletics costs.

Source: "Athletic Program Costs by Sport", Lunenburg Public Schools, published with the
FY26 budget materials. Participation counts and FY24 programmatic cost per sport.
The second cost column in that document ("Cost of Running Each Sport", from the 5/1/2024
Athletic Program Funding Overview deck) is retained as `deckCost` -- the two columns
disagree substantially for several sports and the district has not reconciled them.

`students` is participations, not unique athletes: one student playing three sports
counts three times. That matters for fee math -- a per-season fee is charged per
participation, so participations is the correct denominator.
"""

SPORTS = [
 dict(name='Football',              level='HS', students=32, cost=19805.28, deckCost=25774.45),
 dict(name='Cheer',                 level='HS', students=14, cost=5909.00,  deckCost=4960.50),
 dict(name='Field Hockey',          level='HS', students=30, cost=10458.50, deckCost=9865.99),
 dict(name='Cross Country',         level='HS', students=22, cost=10585.90, deckCost=6818.50),
 dict(name='Golf',                  level='HS', students=13, cost=7859.40,  deckCost=5930.97),
 dict(name="Boys' Soccer",          level='HS', students=35, cost=18950.33, deckCost=9336.50),
 dict(name="Girls' Soccer",         level='HS', students=34, cost=15250.33, deckCost=14983.50),
 dict(name='Unified Basketball',    level='HS', students=14, cost=3032.82,  deckCost=1907.82),
 dict(name='Softball',              level='HS', students=39, cost=17431.00, deckCost=4895.00),
 dict(name="Girls' Lacrosse",       level='HS', students=31, cost=12350.16, deckCost=1492.29),
 dict(name="Boys' Lacrosse",        level='HS', students=35, cost=10496.18, deckCost=612.79),
 dict(name='Baseball',              level='HS', students=15, cost=17777.36, deckCost=2573.50),
 dict(name='Outdoor Track',         level='HS', students=86, cost=15221.50, deckCost=1146.00),
 dict(name='Indoor Track',          level='HS', students=70, cost=32456.00, deckCost=17532.50),
 dict(name='Unified Track',         level='HS', students=12, cost=1593.00,  deckCost=353.00),
 dict(name="Girls' Basketball",     level='HS', students=23, cost=9881.00,  deckCost=14959.00),
 dict(name="Boys' Basketball",      level='HS', students=21, cost=13518.00, deckCost=20717.96),
 dict(name="Boys' Ice Hockey",      level='HS', students=40, cost=11994.27, deckCost=15069.70),
 dict(name="Girls' Ice Hockey",     level='HS', students=2,  cost=1100.00,  deckCost=1100.00),
 dict(name='Alpine Skiing',         level='HS', students=14, cost=9825.00,  deckCost=9825.00),
 dict(name='MS Cross Country',      level='MS', students=30, cost=6134.85,  deckCost=2428.65),
 dict(name='MS Field Hockey',       level='MS', students=25, cost=7180.25,  deckCost=3407.50),
 dict(name='MS Track',              level='MS', students=25, cost=4000.00,  deckCost=4000.00),
 dict(name="MS Girls' Basketball",  level='MS', students=14, cost=6764.25,  deckCost=2365.75),
 dict(name="MS Boys' Basketball",   level='MS', students=15, cost=6373.25,  deckCost=3298.75),
]

# Programs beyond athletics that a fee could in principle support. Participation for
# these is NOT published by the district -- the figures below are placeholders the user
# adjusts in the app, and are labelled as such.
OTHER_PROGRAMS = [
 dict(id='hs_music', name='High School Band & Chorus', cost=72440,
      participants=95, participantsKnown=False,
      note='Cost is our estimate of the 1.0 FTE music position. Participation is a '
           'placeholder — adjust it.'),
 dict(id='music_supplies', name='Band & Music Supplies, Equipment, Repair', cost=17073,
      participants=160, participantsKnown=False,
      note='Published line-item cost across all four schools. Participation is a placeholder.'),
 dict(id='clubs', name='Clubs & After-School Advisors (HS)', cost=11731,
      participants=120, participantsKnown=False,
      note='Published line-item cost. Participation is a placeholder.'),
 dict(id='band_transport', name='Band & Music Transportation', cost=5000,
      participants=160, participantsKnown=False,
      note='Published line-item cost, cut in the FY27 balanced budget.'),
]

# What neighbouring and comparable districts charge, for calibration.
FEE_BENCHMARKS = [
 dict(district='Lunenburg', fee=400, note='Raised for 2026-27: $400 first child, $300 second, $225 third, $1,500 family cap. Was $250/$140/$85 with a $475 cap.', local=True),
 dict(district='Duxbury', fee=300, note='Per season; hockey $500. Rising from $250.', local=False),
 dict(district='Winchester', fee=600, note='Up from $400, plus $845 hockey / $385 golf / $185 swim.', local=False),
 dict(district='Bridgewater-Raynham', fee=950, note='Considered $900–$1,000 to self-fund athletics entirely.', local=False),
 dict(district='Ashburnham-Westminster', fee=None, note='Collects $215,000/yr in student fees; reinstated girls ice hockey funded entirely by fees.', local=True),
 dict(district='Groton-Dunstable', fee=None, note='Reviewing athletic, kindergarten, preschool and activity fees.', local=True),
]

# The full athletics program as budgeted (FY27 level service), which is more than the sum
# of per-sport programmatic costs: it includes the AD, trainer, secretary, insurance,
# dues and district-wide transportation.
# PROGRAM_TOTAL_ADOPTED is what Town Meeting passed. But it funds ZERO athletic
# transportation, and a team that cannot reach an away game is not a team -- so the
# adopted figure is not an honest answer to "can athletics pay for itself". Hence the
# ladder below: each rung is a real budget line or scenario delta, and the reader can
# climb from what was funded to what the whole programme costs, one step at a time.
PROGRAM_TOTAL_LEVEL_SERVICE = 451830
PROGRAM_TOTAL_ADOPTED = 217908     # FY27 Balanced, as adopted 2 May 2026
PROGRAM_TOTAL_REMAINING = PROGRAM_TOTAL_ADOPTED   # older name, kept for callers
PROGRAM_TOTAL_RESTORATION = 466245                # FY27 Restoration / Core

ATHLETIC_TRANSPORTATION = 127550        # cut to $0 in the adopted budget
TRAINER_HALF = 34258.50                 # the trainer runs half-time in the adopted budget
COACHING_RESTORE = 72113                # coaching cut from $159,444 to $87,331
FRESHMAN_MS_COACHES = 14415             # the middle school and freshman teams themselves

# The rung that matters for the self-funding question: the teams that survived, able to
# travel. Not a scenario the district published -- our construction, and labelled as such.
PROGRAM_TOTAL_TRAVEL = PROGRAM_TOTAL_ADOPTED + ATHLETIC_TRANSPORTATION   # 345,458

# Each step's `add` is what that rung puts back on top of the one before it.
PROGRAM_LADDER = [
 dict(id='adopted', label='As adopted', add=None, total=217908.50,
      scenario='FY27 Balanced', published=True,
      sub='The athletics Town Meeting funded on 2 May 2026. No athletic transportation, '
          'a half-time trainer, coaching stipends cut by 45%, and no middle school or '
          'freshman teams.'),
 dict(id='travel', label='As adopted, able to travel', add=ATHLETIC_TRANSPORTATION,
      total=345458.50, scenario='FY27 Balanced + transportation', published=False,
      addLabel='Athletic transportation',
      sub='The same teams, with the buses put back. The adopted budget zeroed athletic '
          'transportation, but a team that cannot get to an away game is not a team. '
          'This is the honest floor for "does athletics pay for itself" — and it is our '
          'construction, not a budget the district published.'),
 dict(id='trainer', label='…plus a full-time trainer', add=TRAINER_HALF,
      total=379717.00, scenario='FY27 Balanced + transport + trainer', published=False,
      addLabel='The other half of the athletic trainer',
      sub='The adopted budget halves the athletic trainer. Restoring the other half is '
          'the next rung, and arguably a safety floor rather than an enhancement.'),
 dict(id='level_service', label='Full programme', add=COACHING_RESTORE, total=451830.00,
      scenario='FY27 Level Service', published=True,
      addLabel='Full coaching stipends',
      sub='The district\'s own Level Service column: athletics run as it was, with full '
          'coaching stipends restored. Still no middle school or freshman teams — Level '
          'Service cut those too.'),
 dict(id='restoration', label='Full programme, middle school back',
      add=FRESHMAN_MS_COACHES, total=466245.00,
      scenario='FY27 Restoration / Core', published=True,
      addLabel='Freshman & middle school coaches',
      sub='The district\'s Restoration and Core columns. The only scenarios in which '
          'middle school and freshman teams exist at all.'),
]

if __name__ == '__main__':
    n = sum(s['students'] for s in SPORTS)
    c = sum(s['cost'] for s in SPORTS)
    d = sum(s['deckCost'] for s in SPORTS)
    print(f'{len(SPORTS)} sports, {n} participations')
    print(f'  sum of per-sport programmatic cost : ${c:,.2f}')
    print(f'  sum of deck "cost of running"      : ${d:,.2f}')
    print(f'  full budgeted program (level svc)  : ${PROGRAM_TOTAL_LEVEL_SERVICE:,}')
    print(f'  average cost per participation     : ${c/n:,.2f}')
    print(f'  fee to fully fund per-sport costs  : ${c/n:,.0f}')
    print(f'  fee to fully fund whole program    : ${PROGRAM_TOTAL_LEVEL_SERVICE/n:,.0f}')
    print()
    for s in sorted(SPORTS, key=lambda x: -x['cost']/x['students']):
        print(f"  {s['name']:<24} {s['level']}  {s['students']:>3}  "
              f"${s['cost']:>10,.2f}  ${s['cost']/s['students']:>8,.2f}/athlete")


# ---------------------------------------------------------------------------
# CURRENT FEES -- Lunenburg already charges, and RAISED the athletic fee for
# the 2026-27 school year.
#
# Source of record for the new schedule: the Superintendent's email to families,
# August 2026 ("They are $400 for your first child, $300 for the second, and $225
# for the third. There is still a family cap of $1,500.").
#
# As of 2026-08-18 the new schedule is NOT posted anywhere we can find. The
# Lunenburg High School athletics "Frequently Asked Questions" (rschoolteams.com)
# still shows the OLD $250/$140/$85 schedule with the $475 cap, and neither the
# district site, the LHS athletics page nor the RevTrak payment portal publishes
# a fee table. That gap is itself worth reporting, so it is carried into the app.
# ---------------------------------------------------------------------------

# The schedule that was in force through 2025-26, still published on the LHS
# athletics FAQ. Kept so the app can show what changed.
PRIOR_ATHLETIC_FEES = dict(
    hs=[('1st student', 250), ('2nd student', 140), ('3rd student', 85)],
    hsCap=475,
    ms=[('1st student', 200), ('2nd student', 150)],
    source='LHS Athletics FAQ (rschoolteams.com) — still the posted schedule',
)

CURRENT_ATHLETIC_FEES = dict(
    effectiveFrom='2026-27 school year',
    tiers=[('1st child', 400), ('2nd child', 300), ('3rd child', 225)],
    familyCap=1500,
    prior=PRIOR_ATHLETIC_FEES,
    source="Superintendent's email to families, August 2026",
    sourcePublished=False,
    sourceNote='We could not find the new schedule posted publicly. The LHS athletics '
               'FAQ still shows the old $250/$140/$85 fees and a $475 cap, so a family '
               'checking the website today gets the wrong number.',
    notes=[
        'A 60% increase on the first child ($250 to $400), and a family cap more than '
        'three times the old one ($475 to $1,500).',
        'Unified Track was $100 under the old schedule; the email does not say whether '
        'that still holds.',
        'Boys ice hockey carries an additional booster-club fee for ice time.',
        'Girls ice hockey co-op players are billed a per-player assessment after the season.',
        'Students on free lunch have the fee waived; reduced-lunch families pay a reduced '
        'fee. The district does not publish how many waivers are granted.',
    ],
    unresolved=[
        'Whether middle school keeps a separate, lower schedule. The old FAQ charged '
        '$200/$150 for middle school and said middle and high school fees do not combine '
        'toward the sibling discount. The email announces one schedule and one cap and '
        'does not mention middle school at all — so we model it as a single district-wide '
        'schedule.',
        'Whether the $1,500 family cap is per season or per year. The old $475 cap was '
        'explicitly per season; the email says only "a family cap of $1,500".',
        'Whether the increase was voted by the School Committee and when. We found no '
        'agenda item or minutes recording it.',
    ],
)

# How the blended per-participation fee is derived.
#
# The fee is charged per child per season, with a sibling discount. To turn the
# schedule into a single number per participation we need the mix of participations
# by sibling rank, which the district does not publish. This is our assumption,
# stated openly so it can be argued with:
SIBLING_MIX = [('1st child', 0.70), ('2nd child', 0.25), ('3rd child', 0.05)]

def _blend(tiers):
    """Weighted average fee per participation under SIBLING_MIX."""
    by_rank = dict((k.replace('student', 'child'), v) for k, v in tiers)
    return sum(by_rank[rank] * w for rank, w in SIBLING_MIX)

# HS vs MS split of the 691 participations
MS_PARTICIPATIONS = sum(s['students'] for s in SPORTS if s['level'] == 'MS')
HS_PARTICIPATIONS = sum(s['students'] for s in SPORTS if s['level'] == 'HS')
PARTICIPATIONS = HS_PARTICIPATIONS + MS_PARTICIPATIONS

# ...but you cannot charge a fee for a team that does not exist. "Freshman & MS Coaches"
# is $0 in BOTH the Level Service and the adopted Balanced budget, so middle school teams
# do not run in FY27. The chargeable base is therefore high-school participations only.
# (Freshman teams were funded from that same line, so even 582 is a little generous.)
CHARGEABLE_PARTICIPATIONS = HS_PARTICIPATIONS

# Blended effective fee per participation. Below the first-child rate because of
# sibling discounts. The family cap does not bite in this model: three children at
# $400 + $300 + $225 is $925, still under the $1,500 cap, so only a fourth
# participating child would reach it. (Under the OLD schedule the $475 cap bound
# exactly at the third child, since $250 + $140 + $85 = $475.)
EFFECTIVE_ATHLETIC_FEE = round(_blend(CURRENT_ATHLETIC_FEES['tiers']))     # $366
PRIOR_EFFECTIVE_ATHLETIC_FEE = round(_blend(PRIOR_ATHLETIC_FEES['hs']))   # $214

# The app previously asserted a flat $210 for the old schedule with no derivation.
# The mix above reproduces $214 for that same schedule, so the jump below is driven
# by the fee increase, not by a change of method.

WAIVER_ASSUMPTION = 0.12


def _revenue(fee, payers=None):
    payers = CHARGEABLE_PARTICIPATIONS if payers is None else payers
    return round(fee * payers * (1 - WAIVER_ASSUMPTION))


# Both figures use the same chargeable base, so the difference between them is the fee
# increase and nothing else.
ESTIMATED_CURRENT_ATHLETIC_REVENUE = _revenue(EFFECTIVE_ATHLETIC_FEE)
ESTIMATED_PRIOR_ATHLETIC_REVENUE = _revenue(PRIOR_EFFECTIVE_ATHLETIC_FEE)
ESTIMATED_FEE_INCREASE_VALUE = (
    ESTIMATED_CURRENT_ATHLETIC_REVENUE - ESTIMATED_PRIOR_ATHLETIC_REVENUE)

# ---------------------------------------------------------------------------
# The fee curve, in Python, so the narrative figures and the interactive chart in the
# app cannot drift apart. Both use the same formula: raising the fee above today's
# raises more per family but prices some families out, so revenue peaks and then falls.
# ---------------------------------------------------------------------------
FEE_DROPOFF_PER_100 = 5.0     # % of participation lost per $100 ABOVE today's fee


def fee_revenue(fee, payers=None, dropoff=FEE_DROPOFF_PER_100, waiver=None):
    payers = CHARGEABLE_PARTICIPATIONS if payers is None else payers
    waiver = WAIVER_ASSUMPTION if waiver is None else waiver
    increase = max(0.0, fee - EFFECTIVE_ATHLETIC_FEE)
    retained = max(0.0, 1 - (increase / 100) * (dropoff / 100))
    return fee * payers * (1 - waiver) * retained


def self_funding_fee(target, step=5, ceiling=4000):
    """Cheapest fee that covers `target`, or None if no fee ever reaches it."""
    return next((f for f in range(0, ceiling + 1, step)
                 if fee_revenue(f) >= target), None)


PEAK_FEE, PEAK_REVENUE = max(
    ((f, fee_revenue(f)) for f in range(0, 4001, 5)), key=lambda x: x[1])


# What the old fee raised in FY26, when middle school teams still ran. The gap between
# this and ESTIMATED_PRIOR_ATHLETIC_REVENUE is the loss of 109 MS participations, not a
# change in the fee.
ESTIMATED_FY26_ATHLETIC_REVENUE = _revenue(PRIOR_EFFECTIVE_ATHLETIC_FEE, PARTICIPATIONS)

# Fee revenue does not appear in the FY27 budget document at all -- that document is
# expenditures only. Athletic and bus fees flow through revolving accounts, so the
# programme costs shown elsewhere in this app are GROSS, before fee offset.
FEE_REVENUE_IN_BUDGET = False


CURRENT_BUS_FEES = dict(
    full_single=180, full_family=270,
    reduced_single=50, reduced_family=75,
    notes=[
        'Grades K-6: charged only if the student lives under 2 miles from school. '
        'At 2 miles or more transport is free, as state law requires.',
        'Grades 7-12: all riders are charged.',
        'Free for families qualifying through the free/reduced application.',
        'Paid to the Town of Lunenburg; students unpaid by 1 June are removed from the roster.',
    ],
)

# ---------------------------------------------------------------------------
# Where does the fee money actually go? What we can and cannot establish.
# ---------------------------------------------------------------------------
FEE_ACCOUNTING = dict(
    established=[
        'The LPS FY27 budget document is expenditures only — 351 line items, no revenue '
        'side at all. Fee income is invisible in it either way, so nothing in that '
        'document tells you whether programme costs are shown gross or net of fees.',
        'The Town\'s revolving funds are authorised annually at Town Meeting under '
        'M.G.L. c.44 §53E½. The May 2026 warrant (Article 6) lists twelve of them — '
        'ambulance billing, library, parks, technology, and so on. Neither athletics nor '
        'student transportation is among them. The only school entry is Custodial Special '
        'Details at $13,000.',
        'Athletic and student-activity fees in Massachusetts are normally held under '
        'M.G.L. c.71 §47, a separate statute that lets school committees run athletic and '
        'activity accounts outside the §53E½ regime. Their absence from Article 6 is '
        'consistent with that.',
        'Bus fees are paid to the "Town of Lunenburg", not to the school department — so '
        'they most likely land as a town local receipt rather than offsetting the school '
        'transportation line directly.',
        'The district does use revolving money to offset appropriated costs: the FY27 '
        'addendum reallocates "$50,000 from school choice revolving/transportation to '
        'offset transportation costs."',
    ],
    unresolved=[
        'Whether the athletics figures in the budget are gross, or already net of fee '
        'income. This changes what a fee increase is actually worth, and we could not '
        'settle it from published documents.',
        'How much fee revenue is actually collected, and how many waivers are granted. '
        'The district publishes the fee schedule but not the collections.',
        'Whether band, music or club fees exist at all.',
        'Gate receipts are real money and invisible in everything here. The School '
        'Committee was told roughly $16,000 came in from ticket sales in the fall season '
        'alone. The budget document carries no revenue side at all, so ticket income sits '
        'outside every figure in this app.',
        'The $20,000 athletic director line appears to be out of date. After the FY27 '
        'budget was set the previous director left and the role was returned to full '
        'time — a change we can find in no published document. It would add something '
        'like $65,000-$75,000 to what athletics actually costs, which moves every fee '
        'coverage figure on this page.',
    ],
    ask='These are three good questions for the Business Manager at a School Committee '
        'meeting. The answers would materially sharpen every fee figure in this tool.',
)
