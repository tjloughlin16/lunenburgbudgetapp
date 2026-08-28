"""Lunenburg health insurance: real premiums, and what plan changes cost employees.

Source: "Health Insurance / Open Enrollment - July 1, 2026", Payroll & Benefits
Coordinator, Town of Lunenburg, 21 April 2026. Rates rose 5.38% for FY27.

The Town pays 75% of premium and the employee 25%. (Town Employee Benefits page.)

Note on the source: in the rate letter the Access Blue Saver rows have the IND and FAM
labels transposed -- $2,602.28 is plainly the family rate and $989.46 the individual,
matching every other plan's ratio. Corrected here.
"""

TOWN_SHARE = 0.75
RATE_INCREASE_FY27 = 0.0538

# monthly total premium by plan and tier
PLANS = [
 dict(id='bce', name='Blue Care Elect', deductible='$500',
      network='Broadest network', family=3662.52, individual=1392.63),
 dict(id='nbne', name='Network Blue New England', deductible='$500',
      network='Regional network', family=2988.41, individual=1136.28),
 dict(id='bs', name='Blue Select', deductible='$500',
      network='Narrower network', family=2599.92, individual=988.56),
 dict(id='abs', name='Access Blue Saver', deductible='$2,000 / $4,000',
      network='High deductible', family=2602.28, individual=989.46),
]

# Enrollment by plan and tier is NOT published. These are placeholders the user adjusts.
# They are calibrated so that the town's 75% share reconciles to the $3,994,071 health
# insurance line in the FY27 school budget -- roughly 194 enrollees across ~253 FTE,
# which is a plausible take-up rate. The plan mix within that total is our assumption.
SCHOOL_HEALTH_BUDGET = 3_994_071
DEFAULT_ENROLMENT = dict(bce=85, nbne=55, bs=42, abs=12)   # family + individual combined
DEFAULT_FAMILY_SHARE = 0.55                                 # share of enrollees on family tier


def annual(monthly):
    return monthly * 12


def plan_cost(plan, enrolled, family_share=DEFAULT_FAMILY_SHARE):
    """Annual town and employee cost for one plan at a given enrollment."""
    fam, ind = enrolled * family_share, enrolled * (1 - family_share)
    total = annual(plan['family']) * fam + annual(plan['individual']) * ind
    return dict(total=total, town=total * TOWN_SHARE, employee=total * (1 - TOWN_SHARE))


def split_change(new_town_share, enrollment=None, family_share=DEFAULT_FAMILY_SHARE):
    """Shifting the contribution split. Saves the town exactly what it costs employees."""
    enrollment = enrollment or DEFAULT_ENROLMENT
    total = sum(plan_cost(p, enrollment.get(p['id'], 0), family_share)['total'] for p in PLANS)
    shift = TOWN_SHARE - new_town_share
    per_plan = []
    for p in PLANS:
        fam_now = annual(p['family']) * (1 - TOWN_SHARE)
        fam_new = annual(p['family']) * (1 - new_town_share)
        ind_now = annual(p['individual']) * (1 - TOWN_SHARE)
        ind_new = annual(p['individual']) * (1 - new_town_share)
        per_plan.append(dict(id=p['id'], name=p['name'],
                             familyNow=round(fam_now), familyNew=round(fam_new),
                             familyDelta=round(fam_new - fam_now),
                             individualNow=round(ind_now), individualNew=round(ind_new),
                             individualDelta=round(ind_new - ind_now)))
    return dict(districtSaves=round(total * shift), perPlan=per_plan)


def migration_saving(from_id, to_id, movers, family_share=DEFAULT_FAMILY_SHARE):
    """Moving employees from one plan to a cheaper one."""
    a = next(p for p in PLANS if p['id'] == from_id)
    b = next(p for p in PLANS if p['id'] == to_id)
    fam, ind = movers * family_share, movers * (1 - family_share)
    delta = (annual(a['family']) - annual(b['family'])) * fam \
          + (annual(a['individual']) - annual(b['individual'])) * ind
    return dict(total=round(delta), town=round(delta * TOWN_SHARE),
                employee=round(delta * (1 - TOWN_SHARE)))


# Why this lever is slow, in one place.
CONSTRAINTS = [
 'Plan design changes go through the Public Employee Committee under M.G.L. c.32B '
 '§§21-23, and the district must share 25% of first-year savings with employees as '
 'mitigation. The saving in year one is therefore 75% of the headline figure.',
 'The Town, not the school district, controls the insurance group. The schools cannot '
 'change this on their own.',
 'Contribution splits are bargained with each union. A shift is a pay cut in everything '
 'but name, to staff who have already absorbed position reductions.',
 'Enrollment by plan and tier is not published. The figures here move with the counts you '
 'set, and should be replaced with real ones before anybody relies on them.',
]

if __name__ == '__main__':
    print(f'Town pays {TOWN_SHARE:.0%}, employee {1-TOWN_SHARE:.0%}. FY27 rates +{RATE_INCREASE_FY27:.2%}\n')
    print(f"{'plan':<26}{'family/mo':>11}{'ind/mo':>10}{'emp fam/yr':>12}{'emp ind/yr':>12}")
    for p in PLANS:
        print(f"  {p['name']:<24}{p['family']:>11,.2f}{p['individual']:>10,.2f}"
              f"{annual(p['family'])*0.25:>12,.0f}{annual(p['individual'])*0.25:>12,.0f}")
    print()
    for share in (0.72, 0.70, 0.65):
        r = split_change(share)
        bce = r['perPlan'][0]
        print(f"Split {share:.0%}/{1-share:.0%}: district saves ${r['districtSaves']:,} | "
              f"Blue Care Elect family pays ${bce['familyNew']:,} (+${bce['familyDelta']:,})")
    print()
    for n in (20, 40):
        m = migration_saving('bce', 'bs', n)
        print(f'Moving {n} from Blue Care Elect to Blue Select: '
              f"total ${m['total']:,}, town saves ${m['town']:,}")
