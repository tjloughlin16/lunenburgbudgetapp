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

# ---------------------------------------------------------------------------
# The administration ladder.
#
# Every amount is the FY27 balanced column of the district's line-item budget
# (sources/data/lps-budget-lines.csv). The ORDER is our judgement about what a district
# can absorb before it stops being able to do the job, and nothing else. Rungs marked
# blocked are shown so the wall is visible: they are the roles a Massachusetts district
# must actually have.
# ---------------------------------------------------------------------------

def _rung(id, label, amount, fte, note, blocked=False):
    return dict(id=id, label=label, amount=amount, fte=fte, note=note, blocked=blocked)

ADMIN_RUNGS = [
 _rung('office', 'Dues, meetings, postage, ads and office supplies', 53_110, 0,
       'School Committee, superintendent and business office discretionary lines plus '
       'the four schools\' office supplies. The first thing every budget review takes, '
       'and 2% of administration.'),
 _rung('stipends', 'Stipends and secretarial overtime', 14_919, 0,
       'The Remote Coordinator ($5,000), curriculum leadership stipends ($6,719) and '
       '$800 of overtime in each of the four principals\' offices.'),
 _rung('legal', 'Half the legal budget', 25_000, 0,
       'Legal spending is mostly special education disputes and personnel matters — '
       'neither of which the district controls the timing of. Halving it is a bet; '
       'zeroing it is not available.'),
 _rung('transition', 'Transition / Leadership Team', 32_001, 0,
       'District-wide administration line 1230. Not a person — a budgeted allowance for '
       'leadership transition work.'),
 _rung('clerk_ms', 'Middle School clerk typist', 19_275, 1.0,
       'Attendance, scheduling and records for the middle school.'),
 _rung('clerk_hs', 'High School clerk typist', 19_275, 1.0,
       'Attendance, scheduling, transcripts and records for the high school.'),
 _rung('hr', 'Human Resource Specialist', 73_485, 1.0,
       'One person does hiring, contracts, benefits, licensure and evaluation tracking '
       'for the whole district. There is no second one.'),
 _rung('sped_clerical', 'Special Education clerical', 69_382, 1.0,
       'IEP scheduling, notices and compliance paperwork run to statutory deadlines. '
       'The work does not disappear with the post — it lands on the teachers and the '
       'special education administrator instead.'),
 _rung('curriculum', 'Instructional Services Director (Curriculum)', 132_480, 1.0,
       'Curriculum adoption, professional development and state assessment coordination '
       'for four schools.'),
 _rung('business_clerical', 'Business office clerical', 110_270, 1.0,
       'Payroll, accounts payable and purchasing for roughly 250 employees.'),
 _rung('sec_ms', 'Middle School administrative secretary', 31_764, 1.0,
       'With the clerk typist gone too, this is the entire middle school front office.'),
 _rung('sec_hs', 'High School administrative secretary', 31_764, 1.0,
       'With the clerk typist gone too, this is the entire high school front office.'),
 _rung('sec_ps', 'Primary School administrative secretary', 62_066, 1.0,
       'The Primary School has one office person. This is her.'),
 _rung('sec_es', 'Turkey Hill administrative secretary', 61_677, 1.0,
       'Turkey Hill has one office person. This is her.'),

 # --- the wall: roles a Massachusetts district is required to have. Cutting these is
 # --- not lawful, and the app lets you do it anyway, flagged, because "what would it
 # --- even save?" is a question people are entitled to an answer to.
 _rung('sped_admin', 'Student Services Coordinator (Special Education)', 155_418, 1.0,
       'Massachusetts requires a district special education administrator. This post '
       'cannot simply not exist.', blocked=True),
 _rung('business_mgr', 'Business Manager', 124_200, 1.0,
       'The district must keep books, file with DESE and run a payroll. There is one.',
       blocked=True),
 _rung('superintendent', 'Superintendent', 178_350, 1.0,
       'Statutorily required. A district without one is not a district.', blocked=True),
 # The four school leadership lines. Each is ONE budget line covering the principal and
 # the assistant principal together — the district does not publish the split, and the
 # figure is identical in all four FY27 scenarios, so there is no delta to infer it from.
 # Assistant principals are cut and rehired often enough in Lunenburg that they deserve
 # their own switch, and they have one: the district prices them in its cut and
 # restoration lists rather than in the salary lines, and both of those are separate
 # controls elsewhere on this page. Inventing a per-school split here would be a number
 # we made up sitting next to numbers we did not.
 _rung('principal_ps', 'Primary School principal and assistant principal', 218_279, 0,
       'One budget line covering both posts; the district does not publish the split. '
       'Every school must have a principal. The FY27 budget cut one assistant principal '
       'by attrition, so the Primary School and Turkey Hill now share the one that is '
       'left — priced at $152,829 in the district\'s own cut list, and available to put '
       'back on the board below.', blocked=True),
 _rung('principal_es', 'Turkey Hill principal and assistant principal', 224_500, 0,
       'One budget line covering both posts; the district does not publish the split. '
       'Turkey Hill shares its assistant principal with the Primary School after the '
       'FY27 cut.', blocked=True),
 _rung('principal_ms', 'Middle School principal and assistant principal', 195_929, 0,
       'One budget line covering both posts. The district has never published a separate '
       'price for the middle school assistant principal, so this tool does not offer one.',
       blocked=True),
 _rung('principal_hs', 'High School principal and assistant principal', 283_766, 0,
       'One budget line covering both posts. The high school assistant principal was cut '
       'to half time and is being restored to full time with one-time state money — the '
       'district prices that half at $90,450, and it is its own switch in the September '
       'restorations below.', blocked=True),
]

ADMIN_RUNGS_CUTTABLE = [r for r in ADMIN_RUNGS if not r['blocked']]
ADMIN_LADDER_CAP = sum(r['amount'] for r in ADMIN_RUNGS_CUTTABLE)
ADMIN_LADDER_POOL = sum(r['amount'] for r in ADMIN_RUNGS)

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
             'these programs self-fund on paper, but that is a steep charge for a club, '
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
      benchmark='Health insurance rose 8–14% across every neighboring district in FY27; '
                'Lunenburg premiums rose 5.38% for FY27'),

 # Administration, cut one nameable thing at a time.
 #
 # A percentage of administration is not a decision anybody can take. Nobody votes to
 # reduce administration 14%; they vote to stop funding a Human Resource Specialist, or
 # they don't. So this lever is a ladder of real budget lines from the FY27 balanced
 # column, ordered from what a district can genuinely absorb to what it legally cannot
 # give up. The ordering is OUR judgement and is stated as such; the amounts are not.
 #
 # The two 1450 technology lines ($154,981 contracted services, $145,884 technology
 # personnel) are deliberately absent — they belong to the technology lever, and counting
 # them in both is how a model quietly closes a gap twice.
 dict(id='admin_cut', name='Administration', kind='saving',
      unit='cut one position or line at a time', max=len(ADMIN_RUNGS), step=1,
      default=0, isLadder=True, rungs=ADMIN_RUNGS,
      basis=ADMIN_LADDER_POOL,
      cap=ADMIN_LADDER_CAP,
      what=f'Administration totals ${ADMIN_TOTAL:,} — 9.9% of the budget — split into '
           f'${ADMIN_CENTRAL:,} of central office and ${ADMIN_BUILDING:,} for the four '
           f'principals\' offices. Everything in the ladder is a line in the district\'s '
           f'FY27 balanced budget. Taking every rung a lawful budget can '
           f'reach saves ${ADMIN_LADDER_CAP:,}, which is '
           f'{ADMIN_LADDER_CAP / ADMIN_TOTAL:.0%} of administration. Past that point sit a '
           f'superintendent, a business manager, a special education administrator and '
           f'four principals — roles the Commonwealth requires. You can cut those here '
           f'too, flagged, because seeing what it would save is the fastest way to '
           f'understand why it is not the answer.',
      caveat='The most commonly suggested cut, and much smaller than people expect. '
             'Lunenburg already runs one superintendent, one business manager and one HR '
             'specialist for four schools, and the FY27 budget already cut an Assistant '
             'Principal so the Primary School and Turkey Hill now share one. Clerical work '
             'does not vanish when the clerk does — IEP paperwork, payroll and state '
             'reporting are legal obligations with penalties attached.',
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
