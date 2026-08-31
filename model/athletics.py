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
# adjusts in the app, and are labeled as such.
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

# What neighboring and comparable districts charge, for calibration.
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
# climb from what was funded to what the whole program costs, one step at a time.
PROGRAM_TOTAL_LEVEL_SERVICE = 451830
PROGRAM_TOTAL_ADOPTED = 217908     # FY27 Balanced, as adopted 2 May 2026
PROGRAM_TOTAL_REMAINING = PROGRAM_TOTAL_ADOPTED   # older name, kept for callers
PROGRAM_TOTAL_RESTORATION = 466245                # FY27 Restoration / Core

ATHLETIC_TRANSPORTATION = 127550        # cut to $0 in the adopted budget
TRAINER_HALF = 34258.50                 # the trainer runs half-time in the adopted budget
COACHING_RESTORE = 72113                # coaching cut from $159,444 to $87,331
FRESHMAN_MS_COACHES = 14415             # the middle school and freshman teams themselves

# The rung that matters for the self-funding question: the teams that survived, able to
# travel. Not a scenario the district published -- our construction, and labeled as such.
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
 dict(id='level_service', label='Full high school program', add=COACHING_RESTORE,
      total=451830.00,
      scenario='FY27 Level Service', published=True,
      addLabel='Full coaching stipends',
      sub='The district\'s own Level Service column: athletics run as it was, with full '
          'coaching stipends restored. Still no middle school or freshman teams — Level '
          'Service cut those too.'),
 dict(id='restoration', label='The full program',
      add=FRESHMAN_MS_COACHES, total=466245.00,
      scenario='FY27 Restoration / Core', published=True,
      addLabel='Freshman & middle school coaches',
      sub='The district\'s Restoration and Core columns — every team the schools used to '
          'field, high school and middle school alike. This is the only rung on which '
          'middle school and freshman sports exist at all, so it is the only one that is '
          'honestly a whole athletics program rather than a surviving piece of one.'),
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
# The schedule in force in FY24 and FY25 -- NOT FY26. It was applied to FY26 for months,
# which is the error this module now guards against: the LHS athletics FAQ states these
# rates and states no year anywhere in the document, so nothing stopped a stale schedule
# being used for a year it had never covered. See sources/data/athletic-fee-schedule.csv,
# where every rate carries the year it applies to and the document that set it.
PRIOR_ATHLETIC_FEES = dict(
    hs=[('1st student', 250), ('2nd student', 140), ('3rd student', 85)],
    hsCap=475,
    ms=[('1st student', 200), ('2nd student', 150)],
    appliesTo=['FY24', 'FY25'],
    source='LHS Athletics FAQ (rschoolteams.com) — still the posted schedule, and undated',
)

# The schedule actually in force in FY26, voted by the School Committee on 26 February 2025
# under "Increasing New & Existing Revenues" and approved by roll call:
#
#   "increase fee for high school up to $325 and $275 for Middle School. A 25% discount for
#    siblings. Reduced fee for high school to $50 and $40 for middle school with a family
#    cap of $1500."
#
# Three of those figures are independently confirmed cell by cell in the district's own
# athletics workbook (Spring!G3 = 325, Spring!S3 = 50, Spring!V3 = 40). The middle school
# rate appears only in the vote.
FY26_ATHLETIC_FEES = dict(
    effectiveFrom='2025-26 school year (FY26)',
    hsFullPay=325,
    msFullPay=275,
    siblingDiscountPct=25,
    hsReduced=50,
    msReduced=40,
    familyCap=1500,
    appliesTo=['FY26'],
    source='School Committee minutes, 26 February 2025 (voted, roll call)',
    sourcePublished=True,
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
# MEASURED, from the district's own workbook, and it replaces an assumption that was out
# by a factor of four.
#
# What it used to be: [('1st child', 0.70), ('2nd child', 0.25), ('3rd child', 0.05)] --
# invented on 18 August, declared openly as ours, and supported by nothing. Searching all
# 1,383 documents in the meeting archive finds "sibling" in two of them, and the only
# athletics one is the School Committee vote of 26 February 2025, which sets the DISCOUNT
# RATE at 25% and says nothing about how many participations receive it. Those are
# different quantities -- how much comes off, against how many people get it -- and their
# adjacency is the most likely explanation for where 30% came from. That is a hypothesis;
# nothing tests it.
#
# What it is now: counted. `athletics-by-sport-fy24-fy26.xlsx`, from the Town by records
# request on 17 June 2026, gives Full Pay / 2nd Sibling / 3rd sibling / Full Waiver /
# Reduced Fee per sport per year, and the categories partition Total Athletes -- so it is
# exactly this quantity rather than a proxy for it.
#
#     Full pay      993   78.44%
#     2nd sibling   107    8.45%
#     3rd sibling    13    1.03%
#     Reduced fee    20    1.58%
#     Full waiver   133   10.51%
#
# COVERAGE, stated rather than implied. 46 sport-years and 1,266 participations, being
# every row whose five category cells sum to its own Total Athletes cell. Rows that do not
# tie are excluded, because where they disagree there is no way to tell which cell is
# wrong. Three reasons they disagree, and only the first is ours to fix:
#   * the workbook mixes units -- Fall's total row multiplies counts by the fee and prints
#     DOLLARS (22 x $140 = 3,080 at H26) while the rows beneath it are counts, and a few
#     per-sport cells carry dollars in a count column (Field Hockey 24/25 reads 200)
#   * some of its totals are simply off by one against the rows above them
#   * the 25/26 fee-category columns are empty throughout, which is why the separate
#     one-page count sheet had to exist at all
# `scripts/extract_athletics_by_sport.py` publishes every mismatch to
# sources/data/athletics-by-sport-reconciliation.csv rather than hiding or refusing them.
#
# The answer is stable however it is cut: 10.1% of participations took a sibling discount
# in 23/24 and 9.1% in 24/25, and the separate FY26 count sheet says 6.9%. Nothing lands
# near 30%.
#
# WHAT THIS DOES NOT ESTABLISH. Two years, and neither is the year the current fee schedule
# applies to. If the new $400/$300/$225 schedule and the $1,500 family cap change how many
# families enrol a second child, this mix moves and nothing here would show it.
SIBLING_MIX = [('1st child', 0.9052), ('2nd child', 0.0845), ('3rd child', 0.0103)]
# What it was, kept as a constant rather than only in the note above, so anything
# describing the change interpolates it instead of quoting a number from prose.
PRIOR_SIBLING_MIX = [('1st child', 0.70), ('2nd child', 0.25), ('3rd child', 0.05)]
# The counted detail behind SIBLING_MIX, published so the mix can be added up by hand.
# Every figure is from the tying rows described above.
MEASURED_SPORT_YEARS = 46
MEASURED_FEE_CATEGORIES = [
    ('Full pay', 993), ('2nd sibling', 107), ('3rd sibling', 13),
    ('Reduced fee', 20), ('Full waiver', 133),
]
MEASURED_CATEGORY_TOTAL = sum(v for _, v in MEASURED_FEE_CATEGORIES)
MEASURED_SIBLING_SHARE = round(
    sum(v for k, v in MEASURED_FEE_CATEGORIES if 'sibling' in k) / MEASURED_CATEGORY_TOTAL, 4)
MEASURED_WAIVER_SHARE = round(
    dict(MEASURED_FEE_CATEGORIES)['Full waiver'] / MEASURED_CATEGORY_TOTAL, 4)
# The mix must be what the counts say, or one of the two has been edited without the other.
assert abs(dict(SIBLING_MIX)['2nd child']
           - dict(MEASURED_FEE_CATEGORIES)['2nd sibling'] / MEASURED_CATEGORY_TOTAL) < 5e-4
assert abs(dict(SIBLING_MIX)['3rd child']
           - dict(MEASURED_FEE_CATEGORIES)['3rd sibling'] / MEASURED_CATEGORY_TOTAL) < 5e-4

SIBLING_MIX_BASIS = (
    'Counted from the district\u2019s own by-sport workbook, FY2024 and FY2025: 46 '
    'sport-years and 1,266 participations, being every row whose fee categories sum to '
    'its own Total Athletes cell.')

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

# ---------------------------------------------------------------------------
# The district's own fee-category counts, and what they say about the two
# assumptions above. OBSERVED, and used in NO calculation here.
# ---------------------------------------------------------------------------
# `athletic-fee-counts-2025-2026.docx`, one page, headed ATHLETIC FEES 2025-2026, from the
# Town by records request. The only source giving fee-category counts for that year -- the
# workbook's columns for it are empty.
#
# They are published here rather than folded into the model because they do not reconcile
# with the workbook and should not be silently adopted: they total 593 participations
# against the workbook's 649 for the same year, they do not separate high school from
# middle school, and the season labels disagree with each other -- Spring records a
# "second sibling" where Fall and Winter record a "first".
#
# But the comparison they license is not close, and hiding it would be worse than
# publishing it with its caveats. SIBLING_MIX assumes 30% of participations take a sibling
# discount. These counts show about 7%. WAIVER_ASSUMPTION assumes 12%; they show about 13%.
# One of our two invented inputs is nearly right and the other is out by a factor of four.
FY26_FEE_CATEGORY_COUNTS = [
    dict(season='Fall',   full_pay=176, reduced=8, sibling=14 + 2, waiver=33),
    dict(season='Winter', full_pay=149, reduced=4, sibling=8 + 1,  waiver=26),
    dict(season='Spring', full_pay=130, reduced=6, sibling=15 + 1, waiver=20),
]
FY26_COUNTED_PARTICIPATIONS = sum(
    c['full_pay'] + c['reduced'] + c['sibling'] + c['waiver']
    for c in FY26_FEE_CATEGORY_COUNTS)
FY26_COUNTED_SIBLING_SHARE = round(
    sum(c['sibling'] for c in FY26_FEE_CATEGORY_COUNTS) / FY26_COUNTED_PARTICIPATIONS, 4)
FY26_COUNTED_WAIVER_SHARE = round(
    sum(c['waiver'] for c in FY26_FEE_CATEGORY_COUNTS) / FY26_COUNTED_PARTICIPATIONS, 4)
# Our assumed share of participations taking ANY sibling discount, for comparison.
# Share of participations taking any sibling discount. Named `ASSUMED_` when it was one;
# it is measured now, and the old name is kept only because removing it would be a
# silent break for anything reading it.
SIBLING_DISCOUNT_SHARE = round(sum(w for r, w in SIBLING_MIX if r != '1st child'), 4)
ASSUMED_SIBLING_SHARE = SIBLING_DISCOUNT_SHARE   # deprecated alias
FEE_COUNTS_SOURCE = ('athletic-fee-counts-2025-2026.docx, obtained from the Town by '
                     'records request, 17 June 2026. The town\u2019s own filename is '
                     'ATHLETIC FEES 2025.docx.')
FEE_COUNTS_CAVEAT = (
    'These counts total {counted} participations against the workbook\u2019s {workbook} for '
    'the same year, do not separate high school from middle school, and use season labels '
    'that disagree with each other. They establish the order of magnitude and not the '
    'figure.')


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
# The measurement, and the calibration it forces
# ---------------------------------------------------------------------------
# What the old fee ACTUALLY raised in FY26, from the athletics revolving fund's own
# year-end reconciliation (xlsx/school-funds-fy26.xlsx, sheet "Athletics Revolving",
# period 1-13). This is a measured figure from a ledger-derived source, not an estimate.
MEASURED_FY26_FEE_REVENUE = 188944.46        # net of $5,664.99 of refunds
# The two sides of the gross, named rather than left in a comment, because the per
# participation figures below are the whole of the argument about what the gap is and a
# figure that lives only in a comment cannot be recomputed when something moves.
MEASURED_FY26_HS_GROSS = 167511.49
MEASURED_FY26_MS_GROSS = 27097.96
MEASURED_FY26_FEE_REVENUE_GROSS = 194609.45   # as the reconciliation prints it
# The halves are transcribed from the same sheet as the total, so they must tie to it.
# Written as an assertion against the PRINTED total rather than by summing the halves into
# it: floating point makes 167,511.49 + 27,097.96 land a hair under, and a published
# figure that acquires a tail because of how we stored it is exactly the kind of drift
# rule 13 is about.
assert abs((MEASURED_FY26_HS_GROSS + MEASURED_FY26_MS_GROSS)
           - MEASURED_FY26_FEE_REVENUE_GROSS) < 0.005, (
    'the high school and middle school receipts no longer sum to the gross the '
    'reconciliation prints')

# Participations in FY26 itself, from the district's own workbook. The SPORTS list above
# is the FY27 planning roster and is the wrong denominator for a FY26 measurement.
FY26_HS_PARTICIPATIONS = 533
FY26_MS_PARTICIPATIONS = 116
FY26_PARTICIPATIONS = FY26_HS_PARTICIPATIONS + FY26_MS_PARTICIPATIONS

# A flat 25% sibling discount, not the old tiered $140/$85, so the blend is the full rate
# reduced by 25% on whatever share of participations are siblings under SIBLING_MIX.
_SIBLING_SHARE = sum(w for rank, w in SIBLING_MIX if rank != '1st child')
_FY26_BLEND = 1 - _SIBLING_SHARE * (FY26_ATHLETIC_FEES['siblingDiscountPct'] / 100)

FY26_EFFECTIVE_HS_FEE = round(FY26_ATHLETIC_FEES['hsFullPay'] * _FY26_BLEND, 2)
FY26_EFFECTIVE_MS_FEE = round(FY26_ATHLETIC_FEES['msFullPay'] * _FY26_BLEND, 2)

# What this model produces for the fee actually charged, in the year it was charged.
MODELLED_FY26_FEE_REVENUE = round(
    (FY26_EFFECTIVE_HS_FEE * FY26_HS_PARTICIPATIONS
     + FY26_EFFECTIVE_MS_FEE * FY26_MS_PARTICIPATIONS) * (1 - WAIVER_ASSUMPTION))

# Kept for comparison: what the model used to produce, pricing FY26 on the FY25 schedule.
MODELLED_FY26_ON_STALE_SCHEDULE = _revenue(PRIOR_EFFECTIVE_ATHLETIC_FEE, PARTICIPATIONS)

# And they do not agree: the model comes in below what the fund reports collecting, and
# the shortfall is FEE_CALIBRATION below.
#
# THIS PARAGRAPH USED TO SAY SOMETHING STRONGER AND IT WAS STALE. It said the model was
# 31% low, and that the measurement implied a per-participation rate ABOVE the
# undiscounted top tier -- an arithmetic impossibility, and therefore proof that an input
# was wrong. Both statements were computed when this module priced FY26 at $250, which was
# the FY25 schedule. With the fee corrected to what the School Committee actually voted,
# neither holds: the implied rates below sit UNDER their published top tiers, on both
# sides. Nothing about the fund's figures changed; our own input did. It is written out
# here rather than deleted because "the model is 31% low" was quoted for a while.
#
# WHAT IS ACTUALLY LEFT, AND IT IS NOT ESTABLISHED. The gap is now the ordinary kind: our
# assumed sibling mix and waiver rate together discount the published schedule by more
# than the fund's receipts imply. Fewer waivers, fewer siblings, sport surcharges outside
# the schedule -- hockey and skiing normally carry them -- or participations undercounted
# all fit, and we cannot tell which. They have different consequences for what a fee
# increase is worth, which is why two readings are carried below rather than one.
#
# So the model is CALIBRATED to the measurement rather than corrected, and the factor is
# named rather than buried. Anchoring on the measured figure is right because it is the
# only observed one; carrying the factor forward to a fee this town has never charged is
# an assumption, and it is labelled as one everywhere it is used.
FEE_CALIBRATION = round(MEASURED_FY26_FEE_REVENUE / MODELLED_FY26_FEE_REVENUE, 4)

# What the fund's receipts imply each participation paid, against the rate the School
# Committee voted for that year. Both sit under their top tier, which is what makes the
# residual an ordinary disagreement about discounts rather than an impossibility.
MEASURED_FY26_HS_PER_PARTICIPATION = round(
    MEASURED_FY26_HS_GROSS / FY26_HS_PARTICIPATIONS, 2)
MEASURED_FY26_MS_PER_PARTICIPATION = round(
    MEASURED_FY26_MS_GROSS / FY26_MS_PARTICIPATIONS, 2)

# Kept under its old name because callers and the app both read it, but it is now the
# measurement rather than our estimate of it.
ESTIMATED_FY26_ATHLETIC_REVENUE = MEASURED_FY26_FEE_REVENUE

# The whole athletics program in FY26, both sides: the general fund 3510 functions plus
# what the fee-funded revolving fund spent. Every other total in this module is the
# general fund portion only, which is what the district publishes and is not what
# athletics costs. Used for context, not as a fee target -- the ladder is built on FY27
# scenarios and this is FY26, so they must not be mixed in one calculation.
ALL_IN_FY26 = 665245.44          # general fund 518,334.00 + revolving fund 146,911.44
FUND_SHARE_FY26 = round(146911.44 / ALL_IN_FY26, 4)

# Fee revenue does not appear in the FY27 budget document, which is expenditures only.
# But that does NOT make the program figures gross, which is what this constant used to
# assert. The mechanism runs the other way: fees land in the revolving fund, the fund
# pays for officials and uniforms, and those lines are budgeted $0 in the general fund
# from FY26 on. The costs are absent, so the appropriation is already net of them.
FEE_REVENUE_IN_BUDGET = True


# ---------------------------------------------------------------------------
# The fee curve, in Python, so the narrative figures and the interactive chart in the
# app cannot drift apart. Both use the same formula: raising the fee above today's
# raises more per family but prices some families out, so revenue peaks and then falls.
# ---------------------------------------------------------------------------
FEE_DROPOFF_PER_100 = 5.0     # % of participation lost per $100 ABOVE today's fee


# The gap between model and measurement has two candidate causes, and THEY IMPLY
# DIFFERENT CURVES. The data cannot distinguish them, so both are carried:
#
#   'scaled'  the fee base is bigger than we think -- participations undercounted. Then
#             the gap scales with the fee, and revenue is the model times FEE_CALIBRATION.
#   'flat'    there are surcharges outside the published schedule -- hockey and skiing
#             normally carry them. A surcharge does not rise when the base fee rises, so
#             the gap is a constant and revenue is the model plus FEE_SURCHARGE_GAP.
#
# Both reproduce the FY26 measurement exactly, by construction. They diverge as the fee
# rises, and 'flat' is the conservative one, so it is what the app leads with.
FEE_SURCHARGE_GAP = round(MEASURED_FY26_FEE_REVENUE - MODELLED_FY26_FEE_REVENUE, 2)
FEE_MODES = ('flat', 'scaled')


def fee_revenue(fee, payers=None, dropoff=FEE_DROPOFF_PER_100, waiver=None, mode='flat'):
    """Revenue at a given fee, anchored on what the fund actually collected.

    `mode` picks which reading of the model-to-measurement gap to apply -- see FEE_MODES.
    Pass mode=None for the uncalibrated model, which reproduces a figure we know to be
    31% below what the fund reports collecting.
    """
    payers = CHARGEABLE_PARTICIPATIONS if payers is None else payers
    waiver = WAIVER_ASSUMPTION if waiver is None else waiver
    increase = max(0.0, fee - EFFECTIVE_ATHLETIC_FEE)
    retained = max(0.0, 1 - (increase / 100) * (dropoff / 100))
    raw = fee * payers * (1 - waiver) * retained
    if mode == 'scaled':
        return raw * FEE_CALIBRATION
    if mode == 'flat':
        # The surcharge travels with participation, so it falls off with the same
        # retention the base fee does. It does not rise with the fee.
        return raw + FEE_SURCHARGE_GAP * retained
    return raw


def self_funding_fee(target, step=5, ceiling=4000, mode='flat'):
    """Cheapest fee that covers `target`, or None if no fee ever reaches it."""
    return next((f for f in range(0, ceiling + 1, step)
                 if fee_revenue(f, mode=mode) >= target), None)


def self_funding_range(target):
    """The fee that covers `target` under each reading of the gap, cheapest first.

    Two numbers rather than one, because the data cannot say which reading is right and
    a single figure here would be a false precision on a page asking families to pay it.
    """
    fees = sorted(f for f in (self_funding_fee(target, mode=m) for m in FEE_MODES)
                  if f is not None)
    return dict(low=fees[0] if fees else None, high=fees[-1] if fees else None)


PEAK_FEE, PEAK_REVENUE = max(
    ((f, fee_revenue(f)) for f in range(0, 4001, 5)), key=lambda x: x[1])



# ---------------------------------------------------------------------------
# The one document that showed both sides
# ---------------------------------------------------------------------------
# Everything else in this app measures the general fund appropriation, because that is
# all the district publishes. Once -- for FY19, submitted by the athletic director to the
# superintendent -- it published athletics with the revolving fund set beside the
# appropriation, line by line. It is the only document in the archive that does, and it
# shows that the appropriated athletics lines were NET of a large revolving contribution.
#
# This is worth pointing a reader at rather than burying. It is the district doing the
# thing that would make every other year legible, and the format has not appeared since.
#
# Provenance: sources/district-budget-page/index.csv. Off the district's own budget page,
# link live as of 2026-08-29. sha256 e0a7c5baa041112c484f4059130f2ec2348325d1fe29b01e52af42d549430858
SPLIT_REPORTING = dict(
    title='Proposed FY19 MSHS Athletic Budget',
    subtitle='Submitted to the Superintendent of Schools, amended proposed budget',
    doc='district-budget-page/docs/fy19-proposed-athletics-budget.pdf',
    link='https://drive.google.com/file/d/1UYTAQzmTbbv2kBVus4zR8lN3i0jqzaTn/view?usp=sharing',
    fund='Chapter 658 revolving fund — the same fund the town books as 1301',
    # Athletic Transportation appears twice in this document: once as an appropriated line
    # and once as "(658)", the revolving fund. Both are reproduced here exactly.
    transportation=[
        dict(fy=2014, general=17000, revolving=30085, basis='actual'),
        dict(fy=2015, general=21600, revolving=40742, basis='actual'),
        dict(fy=2016, general=23000, revolving=33308, basis='actual'),
        dict(fy=2017, general=23000, revolving=50986, basis='actual'),
        dict(fy=2018, general=33500, revolving=27450, basis='budgeted'),
        dict(fy=2019, general=24975, revolving=40000, basis='requested'),
    ],
    # The whole programme on the same basis, as the document totals it.
    programme=[
        dict(fy=2014, general=194316, revolving=108147, stated=302462, revenue=110474),
        dict(fy=2015, general=224799, revolving=111938, stated=336738, revenue=140748),
        dict(fy=2016, general=210911, revolving=113819, stated=324730, revenue=121555),
        dict(fy=2017, general=222695, revolving=156550, stated=379245, revenue=109351),
        dict(fy=2018, general=326478, revolving=103001, stated=429479, revenue=108000),
        dict(fy=2019, general=307931, revolving=87902,  stated=395833, revenue=108000),
    ],
    revenueLabel='Fees and gate receipts',
    # The document's own grand totals are $1 off its own columns in FY14 and FY15 and
    # exact in the other four years. Stated here so the app can say so rather than look
    # as though it disagrees with the source.
    roundingNote='In FY14 and FY15 the document\u2019s stated grand total differs by $1 '
                 'from the sum of its own two columns. The other four years tie exactly.',
    credit='The district published this. It is the clearest account of how athletics is '
           'actually paid for that exists anywhere in the record, and it came off the '
           'schools\u2019 own budget page.',
    establishes='For these years the appropriated athletics lines were net of a large '
                'revolving-fund contribution, and the appropriation alone understates '
                'what athletics cost.',
    doesNotEstablish='Whether the split continued after FY19. No document published '
                     'since shows both sides, so the ratio cannot be seen for any later '
                     'year — including every year this app projects from.',
    wouldSettle='An athletics budget in this format for any year after FY19, or the '
                'revolving fund\u2019s account detail history.',
)


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
        'document tells you whether program costs are shown gross or net of fees.',
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
        'How much fee revenue is collected is no longer a guess. The athletics revolving '
        'fund reports $194,609 gross and $188,944 net for FY26 in its own year-end '
        'reconciliation, against $146,911 of spending \u2014 so the fees already pay about a '
        'fifth of what athletics costs all in, and the fund ended the year holding '
        '$152,281. The fee model in this app is anchored on that measurement rather than '
        'on our estimate of it.',
        'The fund is the one the town books as 1301, CHAPTER 658 REVOLVING FUND. That is '
        'the statute, from the town\u2019s own ledger \u2014 not an inference from its absence '
        'from the annual \u00a753E\u00bd warrant article.',
        'For FY14 through FY17 the appropriated athletics lines were NET of a large '
        'revolving-fund contribution, and the district showed both sides itself. Its '
        'FY19 athletics budget lists Athletic Transportation twice \u2014 once as an '
        'appropriation and once as the Chapter 658 revolving fund \u2014 and the '
        'revolving side is the larger of the two in every year it reports as actual. '
        'So an appropriated athletics line is not what athletics costs.',
    ],
    unresolved=[
        'WHY the fund collects more than the published fee schedule can explain. It took '
        'in $188,944 net in FY26, which is 45% above what the schedule and our sibling and '
        'waiver assumptions produce, and implies $287.82 per high school participation '
        'against a $250 first-child fee. A blended rate cannot exceed its top tier, so '
        'either participations are undercounted or there are surcharges outside any '
        'schedule we hold. The two imply different answers to what a fee rise is worth, '
        'so every fee figure here is a range rather than a number.',
        'Whether today\u2019s athletics figures are gross, or already net of fee income. '
        'For FY14\u2013FY17 the district\u2019s own FY19 athletics budget settles it \u2014 they '
        'were net, and the revolving fund paid the larger share of transportation. No '
        'document published since shows both sides, so for every year this app projects '
        'from, the question is open again. This changes what a fee increase is worth.',
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
