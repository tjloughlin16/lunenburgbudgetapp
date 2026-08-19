"""Our own recommended package. This is analysis, not a district proposal.

Reasoning, in order:

1. The gap compounds. Groton-Dunstable cut in FY24, FY25 and FY26 and still starts FY27
   below level service. Cutting programs to close a structural gap buys one year and
   makes the next year's arithmetic worse.

2. Personnel is ~90% of the budget, so any large program cut is a teacher cut whatever
   it is labeled. Easthampton: 93% of its cuts were personnel.

3. Athletics has already moved. The district raised the fee to $400/$300/$225 for
   2026-27, worth about $78,000 a year across the 582 high-school participations that
   remain chargeable. That covers 54% of what it costs to field the surviving teams AND
   bus them to away games -- not the whole program, and nothing like the full $451,830
   one. The remaining fee headroom is small and the returns fall away fast.

4. Fees must come with real waivers, or they become a tax on the families least able to
   pay and participation collapses among exactly the students who benefit most.

5. Early literacy is the worst thing to lose per dollar. The FY27 reading specialists and
   Ignite seats are one-time funded and disappear unless FY28 absorbs them. The district's
   own cited research: 88% of students not reading at benchmark by the end of grade 1 are
   still behind a year later.

6. Administration is the most-suggested cut and one of the weakest. It is $2.63M, but DESE
   puts Lunenburg's administration below every peer here except one, an Assistant Principal
   was already cut, and state reporting failures carry financial penalties.

7. Health insurance is the only lever big enough to change the trajectory -- 15% of the
   budget growing 8-9% a year -- and the slowest to move.

8. None of this closes the whole gap. Say so plainly.
"""
import sys
sys.path.insert(0, 'model')
from athletics import (SPORTS, CHARGEABLE_PARTICIPATIONS,
                       ESTIMATED_FEE_INCREASE_VALUE as ATHLETIC_FEE_INCREASE_VALUE)
from levers import ADMIN_TOTAL, TECH_TOTAL, HEALTH_TOTAL

PARTICIPATIONS = CHARGEABLE_PARTICIPATIONS   # MS teams are unfunded; only HS pays


def fee_yield(fee, participants, dropoff_per_100=5.0, waiver_pct=12.0, current=0.0):
    """Gross revenue at `fee`. Participation is lost only on the increase ABOVE what is
    already charged -- families paying today are not driven off by a fee they already
    pay. This matches the curve the app draws; measuring drop-off from $0 would penalise
    a fee for money the district already collects."""
    increase = max(0.0, fee - current)
    retained = max(0.0, 1 - (increase / 100) * (dropoff_per_100 / 100))
    return fee * participants * retained * (1 - waiver_pct / 100)


def fee_new_money(fee, participants, current=0.0, **kw):
    """What a fee change is actually worth: gross at the new fee, minus what the existing
    fee already brings in. Only this is new money to the budget."""
    return (fee_yield(fee, participants, current=current, **kw)
            - fee_yield(current, participants, current=current, **kw))


BUS_FEE_NOW = 180        # what the district already charges per rider, per year
BUS_FEE_PROPOSED = 300
BUS_RIDERS = 420         # placeholder: the district does not publish rider counts


PACKAGE = [
 dict(id='athletic_fees', name='Athletics fee — already raised to $400 for 2026-27',
      value=ATHLETIC_FEE_INCREASE_VALUE,
      why='This one is done. The district raised the first-child fee from $250 to $400 '
          '($300 second, $225 third, $1,500 family cap) for 2026-27 — worth roughly '
          '$78,000 a year if participation holds. We count it here because it is real '
          'money already committed, not because we are proposing it. It takes fee '
          'coverage from about 32% to 54% of what it costs to field the surviving teams '
          'with transport. Going further is possible but the returns fall away fast: '
          'self-funding that basis needs $960 a season and revenue peaks near $1,185, so '
          'the full program cannot be bought back at any price. The open task is not a '
          'bigger fee — it is publishing the schedule, the waiver policy and the '
          'collections, none of which is posted today.',
      difficulty='Already in force. What is missing is publication: the athletics FAQ '
                 'still shows the old $250 schedule.'),
 dict(id='activity_fees', name='Band, music & club fee — $100 per activity',
      value=round(fee_yield(100, 375, dropoff_per_100=6.0, waiver_pct=15.0)),
      why='We could not confirm that any activity fee exists today, so this is treated as '
          'a new charge and the whole amount is new money. Small, but it protects the '
          'music position and club advisors — cheap, and disproportionately visible to '
          'families deciding whether to stay in town.',
      difficulty='School Committee vote. Participation is a PLACEHOLDER — 375 students is '
                 'our guess, not a district figure, so this value is the softest in the '
                 'package. Publish participation first.'),
 dict(id='bus_fees',
      name=f'Bus fee, grades 7–12 — ${BUS_FEE_PROPOSED} per rider (from ${BUS_FEE_NOW})',
      value=round(fee_new_money(BUS_FEE_PROPOSED, BUS_RIDERS, current=BUS_FEE_NOW,
                                dropoff_per_100=8.0, waiver_pct=15.0)),
      why=f'Lunenburg ALREADY charges ${BUS_FEE_NOW} a year per rider with a $270 family '
          f'cap, so only the increase above that is new money — this figure is the '
          f'increase, not the whole fee. ${BUS_FEE_PROPOSED} sits mid-range for '
          'Massachusetts, where $200–$500 with a family cap is common. Massachusetts only '
          'requires free transport for K–6 beyond two miles, and transport is one of the '
          'fastest-growing lines in the budget.',
      difficulty='School Committee vote. Expect more car traffic at the secondary campus. '
                 'Rider counts are not published, so the yield is our estimate.'),
 dict(id='tech_cut', name='Technology & licence audit — 12%',
      value=round(TECH_TOTAL * 0.12),
      why='Duplicate and unused licences are common and nobody loses a teacher. '
          'Ashburnham-Westminster took 5.8%; 12% assumes a real audit, not a trim.',
      difficulty='Administrative. Needs someone with time to run it — itself an argument '
                 'against gutting the business office.'),
 dict(id='admin_cut', name='Administration trim — 3%',
      value=round(ADMIN_TOTAL * 0.03),
      why='Enough to answer voters who ask for it, small enough not to trigger reporting '
          'failures. Deeper cuts here cost more than they save.',
      difficulty='Attrition and reorganization, not layoffs.'),
 dict(id='health_design', name='Health insurance redesign — start now, bank it for FY30',
      value=0,
      why=f'${HEALTH_TOTAL:,}, 15% of the budget, growing 8–9% a year. The only lever big '
          'enough to change the trajectory — and it cannot be delivered by next July.',
      difficulty='Public Employee Committee bargaining under M.G.L. c.32B §§21–23, and the '
                 'town controls the insurance group. Multi-year.'),
]

PRIORITY_ORDER = ['literacy', 'core_classroom', 'sped', 'wellness', 'advanced',
                  'leadership', 'technology', 'operations', 'arts', 'activities',
                  'athletics']

PRIORITY_WHY = (
    'Early literacy first, because it is the one loss that cannot be made up later and the '
    'district has already funded it with money that runs out. Classrooms next, because '
    'class size is what makes families leave. Special education and mental health follow '
    'because they are mandated, needed, or both. Athletics, arts and clubs sit at the '
    'bottom NOT because they matter least — but because they are the only things on this '
    'list that can pay for themselves. Fund them with fees and they never reach the cut '
    'line at all.'
)

# Deliberately states no fraction: the share of the gap is computed and displayed live
# above this text, and the gap itself moves with the assumption sliders. A number written
# here would contradict the panel the moment anyone touched a slider.
CLOSING = (
    'This package finds roughly half the FY28 gap without cutting a single '
    'program — the exact share is above, and it moves as you change assumptions. The '
    'rest is the honest part: it is either an override, or '
    'classroom positions. Anyone who tells you there is a painless third option has not '
    'added up the line items.'
)

if __name__ == '__main__':
    tot = sum(p['value'] for p in PACKAGE)
    gap = 613238
    print(f'{PARTICIPATIONS} athletic participations\n')
    for p in PACKAGE:
        print(f"  {p['name'][:58]:<60} ${p['value']:>9,}")
    print(f"  {'TOTAL FOUND':<60} ${tot:>9,}")
    print(f"  {'FY28 gap':<60} ${gap:>9,}")
    print(f"  {'Still to find':<60} ${gap-tot:>9,}   ({(gap-tot)/102510:.1f} teaching positions)")
