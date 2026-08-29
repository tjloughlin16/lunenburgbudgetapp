"""FY28+ projection engine for Lunenburg Public Schools.

Base year is the FY27 budget as actually adopted (the Balanced scenario, $26,572,288)
plus the $453,722 of programs being restored at the 9/3/26 Special Town Meeting -- those
are one-time funded, so carrying them into FY28 is itself a cost the district must absorb.

Revenue is projected from the Town's own published FY27 formula (Town Manager press
release 4/17/26): Prop 2 1/2 levy limit growth + new growth + excluded debt, plus state
aid and local receipts.
"""
import csv, json
from collections import defaultdict

# ---------------------------------------------------------------- expense base
ESCALATOR_GROUPS = {          # DESE function-code prefix -> escalator key
    '5200': 'health', '3300': 'transport', '9300': 'sped_tuition',
    '9400': 'sped_tuition', '4120': 'utilities', '4130': 'utilities',
}

# Special education is bucketed and escalated in model/sped.py, which owns the whole of
# it -- the group membership, the decomposition, the contracts that govern the line, and
# the rate. It is separated out because the state's function codes cannot do it: 2330 is
# paraprofessionals of both kinds and 3300 is transportation of both, so bucketing on the
# code put about $5.7M of special education staffing inside `salaries` at the teachers'
# contract rate. That hid no money -- the total was always right -- but it averaged
# together two lines that behave nothing alike.
from sped import is_sped, RATE as SPED_RATE, TUITION_RATE

DEFAULT_ASSUMPTIONS = dict(
    salaries=0.040,        # contractual steps + lanes + COLA
    health=0.090,          # district assumed 9% for FY27
    transport=0.060,       # district assumed 10% for FY27; 6% is the softer default
    # Special education, in district. Derived in sped.py and NOT the rate the line did:
    # 5.89% is one hiring decision averaged over two years, and the paras it paid for are
    # already inside this model's starting amount. See sped.py for the whole argument and
    # for the range published beside it.
    sped=SPED_RATE,
    # Out-of-district placements. Held FLAT, and that is a finding rather than a
    # default: eleven budgets from FY17 to FY27 range from $489,918 to $1,291,293 with
    # six years up and four down and a straight-line fit of R^2 = 0.10. The compound
    # rate to FY27 runs from -45.78% to +11.78% depending only on which year you start
    # it, so there is no rate here to measure. The risk is the range, and the range is
    # priced scenario by scenario rather than hidden inside an escalator. See sped.py.
    sped_tuition=TUITION_RATE,
    utilities=0.050,
    other=0.030,
    # revenue
    levy_growth=0.025,     # Proposition 2 1/2 -- statutory
    new_growth=400_000,    # town's own FY27 estimate
    state_aid_growth=0.020,
    local_receipts_growth=0.010,
    school_share=0.562,    # Education as a share of the FY27 omnibus
    athletic_fee_revenue=0,       # lever: fee revenue ABOVE what the district already collects
    override_amount=0,            # lever: a successful FY28 override
)

# Town revenue facts, FY27 (all from the 4/17/26 press release + enacted state budget)
FY27 = dict(
    levy_limit=34_133_581.28, excluded_debt=2_199_352.52,
    state_aid=11_404_917 + 471_121, local_receipts=3_508_024,
    omnibus=49_963_990.19, lps_appropriation=26_572_288,
    stm_addbacks=453_722, monty_tech=1_452_426,
    # Of the $453,722 plan, $103,722 comes from FY27 health insurance savings and
    # $350,000 is the article the 3 September 2026 Special Town Meeting votes on.
    stm_appropriation=350_000,
)


def expense_base(csv_path='sources/data/lps-budget-lines.csv'):
    """FY27 Balanced spending bucketed by escalator."""
    buckets = defaultdict(float)
    for r in csv.DictReader(open(csv_path)):
        if r['kind'] != 'line':
            continue
        v = float(r['fy27_balanced']) if r['fy27_balanced'] else 0.0
        if not v:
            continue
        code = (r['function_group'] or '')[:4]
        # Tested before the prefix map, which is exactly what cannot see it.
        if is_sped(r):
            buckets['sped'] += v
        elif r['section'] == 'SALARIES' and code not in ESCALATOR_GROUPS:
            buckets['salaries'] += v
        else:
            buckets[ESCALATOR_GROUPS.get(code, 'other')] += v
    return dict(buckets)


def project(years=5, assumptions=None, cuts_by_year=None):
    a = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    buckets = expense_base()
    # carry the STM restorations forward as salary cost from FY28 on
    buckets['salaries'] += FY27['stm_addbacks']

    levy = FY27['levy_limit']
    aid = FY27['state_aid']
    receipts = FY27['local_receipts']
    approp = FY27['lps_appropriation'] + FY27['stm_appropriation']

    out = []
    for i in range(years):
        fy = 28 + i
        # --- revenue ---
        levy = levy * (1 + a['levy_growth']) + a['new_growth']
        aid *= (1 + a['state_aid_growth'])
        receipts *= (1 + a['local_receipts_growth'])
        town_available = levy + FY27['excluded_debt'] + aid + receipts \
            - (FY27['levy_limit'] + FY27['excluded_debt'] + FY27['state_aid']
               + FY27['local_receipts'] - FY27['omnibus'])
        prev = out[-1]['town_available'] if out else FY27['omnibus']
        growth_rate = town_available / prev - 1
        approp = approp * (1 + growth_rate) + a['override_amount']
        available = approp + a['athletic_fee_revenue']

        # --- level service cost ---
        for k in list(buckets):
            buckets[k] *= (1 + a[k])
        level_service = sum(buckets.values())

        deficit = level_service - available
        out.append(dict(fy=fy, level_service=round(level_service),
                        available=round(available), appropriation=round(approp),
                        town_available=town_available, deficit=round(deficit),
                        growth_rate=round(growth_rate, 5),
                        buckets={k: round(v) for k, v in buckets.items()}))
        # apply cuts -> permanently reduce the salary base
        cut = (cuts_by_year or {}).get(fy, 0)
        if cut:
            buckets['salaries'] -= cut
    return out


if __name__ == '__main__':
    b = expense_base()
    print('FY27 Balanced expense base by escalator bucket:')
    for k, v in sorted(b.items(), key=lambda x: -x[1]):
        print(f'  {k:<14} ${v:>13,.0f}')
    print(f'  {"TOTAL":<14} ${sum(b.values()):>13,.0f}   '
          f'(published: ${FY27["lps_appropriation"]:,})')
    print()
    print(f"{'FY':<6}{'Level Service':>16}{'Available':>14}{'Deficit':>13}{'Growth':>9}")
    for r in project():
        print(f"FY{r['fy']:<4}{r['level_service']:>16,}{r['available']:>14,}"
              f"{r['deficit']:>13,}{r['growth_rate']*100:>8.2f}%")
