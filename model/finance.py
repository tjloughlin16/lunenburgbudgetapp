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
    # 5.77% is one hiring decision averaged over two years, and the paras it paid for are
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
    # 2.75% -- the MEDIAN annual step in the town's own `Subtotal State Aid` line,
    # FY2005-FY2027, twenty-three consecutive BUDGET years. Like for like with what this
    # field is: a forward estimate of the whole cherry sheet, not of Chapter 70 alone.
    # See notes/findings/STATE-AID-RATE.md and notes/findings/state-aid-budget-series.csv,
    # which is generated and --checked.
    #
    # The median rather than the 3.5724% CAGR, because the CAGR is carried by four policy
    # step-years -- FY2007 +10.1%, FY2013 +12.0%, FY2018 +12.2%, FY2023 +11.2% -- and
    # projecting it forward assumes a legislature. Not the 1.9% of the last four years
    # either: that window opens the year AFTER an 11.2% jump, which is rule 6's warning
    # about reading a rate without reading the year-by-year.
    #
    # Confidence is MODERATE, not high. Chapter 70 is 78.7% of this base and it is a
    # FORMULA whose inputs move independently, not a trend. Nothing tests whether its next
    # five years resemble its last five. Was 0.020, with no stated source or derivation.
    state_aid_growth=0.0275,
    local_receipts_growth=0.010,
    school_share=0.562,    # Education as a share of the FY27 omnibus
    athletic_fee_revenue=0,       # lever: fee revenue ABOVE what the district already collects
    # WARNING: this is added to the appropriation in EVERY projected year, which models a
    # new override passing annually -- not one ballot question. A real Prop 2½ override
    # raises the levy limit ONCE and the base then grows at the cap. Using this to answer
    # "what would an override do" overstates it by roughly the number of years projected:
    # $1M here closes $6,466,144 of the FY33 gap rather than about $1.16M.
    # The corrected one-time model is `overrideLevy` in fy28/src/model/rates.ts, and it is
    # what the Override page uses. This field is kept because removing it would change
    # published figures, and because "an override every year" is itself a scenario the
    # Override page discusses.
    override_amount=0,            # lever: an override passing EVERY year -- see above
    # LEVER: a standing policy of appropriating this much free cash EVERY year, rather
    # than accumulating it. This is the argument people actually make -- "be less
    # conservative" is a policy, not a windfall. Zero by default, so the published
    # projection is unchanged unless somebody moves it.
    #
    # It is capped in the loop at that year's gap, and it is the ONLY actuals-derived
    # input allowed near the projection. It touches no bucket and no growth rate, which
    # audit_provenance.py asserts at every draw -- that boundary is what rule 1 protects,
    # and a one-time subtraction after the rates have run does not cross it.
    #
    # What the projection CANNOT tell you is whether the draw is sustainable. That depends
    # on how much free cash the town generates in a year, which is about $2.0M in a normal
    # one -- and which is generated BY the underspending a tighter budget would remove.
    # freecash.SUSTAINABLE_DRAW carries the number; the page carries the paradox.
    free_cash_annual=0,
)

# Town revenue facts, FY27 (all from the 4/17/26 press release + enacted state budget)
FY27 = dict(
    levy_limit=34_133_581.28, excluded_debt=2_199_352.52,
    state_aid=11_404_917 + 471_121, local_receipts=3_508_024,
    omnibus=49_963_990.19, lps_appropriation=26_572_288,
    stm_addbacks=392_264, monty_tech=1_452_426,
    # WHAT THE 3 SEPTEMBER 2026 SPECIAL TOWN MEETING ACTUALLY DID, read off the electronic
    # voting display in the meeting's own recording rather than off the warrant or the
    # district's deck -- both of which say something different, and one of them by a factor
    # of five.
    #
    #   ARTICLE 1  $418,056.00 raised and appropriated, 2/3 required, 263-40-0 of 303.
    #              "as voted under Article 10 of the May 2, 2026 Annual Town Meeting."
    #   ARTICLE 3  $30,308.00 transferred from the Winter Recovery Assistance Program
    #              (WRAP) Special Revenue Fund, majority, 224-29-0 of 253.
    #   ARTICLE 2  passed over.
    #
    # The warrant asked $151,338.38 from Certified FREE CASH for Article 3. The motion on
    # the floor moved $30,308.00 from a special revenue fund instead -- a fifth of the
    # money and a different source, which also changed the vote threshold. Citing the
    # warrant alone would have published a figure five times too large. Rule 13: the
    # warrant is the authoritative ARTICLE, the motion is the authoritative AMOUNT.
    #
    # WHAT CARRIES FORWARD, AND WHAT DOES NOT. `stm_addbacks` is the part of the plan that
    # becomes RECURRING SALARY, and it is $392,264 rather than the $418,000 appropriated:
    #
    #   Primary — Second Grade Teacher       103,722   salary, carries
    #   THES — 1.0 Reading Specialist        103,722   salary, carries
    #   LHS — .5 Assistant Principal          90,450   salary, carries
    #   LHS — .4 Music Teacher                26,370   salary, carries
    #   District — 1.0 COTA                   68,000   salary, carries
    #   LMHS — Literacy Prof. Development     15,736   one-off, does NOT carry
    #   Athletics — Transportation            10,000   annual cost, NOT salary; see below
    #                                        -------
    #                                        418,000   (the deck's total; the warrant's is
    #                                                   $418,056, and the split is the
    #                                                   deck's -- it is the only document
    #                                                   that gives one)
    #
    # The $10,000 of athletic transportation is deliberately out of the salary bucket: it
    # is an annual operating cost rather than payroll, it does not take the salary
    # escalator, and whether it recurs at all is a budget decision rather than a fact.
    # TJ, 19 September 2026, choosing this over carrying the whole $418,000.
    #
    # THE CLIFF, which is the reason any of this is in the cost base at all. Article 1 is
    # one year of state receipts above what the town budgeted -- the Governor signed the
    # FY27 state budget on 7 July 2026 -- and Article 3 is a transfer from a fund created
    # by Select Board vote the day before Town Meeting. The money arrives once. The people
    # it hired are still employed the year after, so $392,264 of salary lands in FY28 with
    # no recurring revenue behind it and takes the salary rate every year thereafter. A
    # restoration funded this way is a cut DEFERRED, not a cut reversed.
    #
    # 9.2 positions were cut in the FY27 cycle and 3.9 are restored here -- a second grade
    # teacher, a reading specialist, half an assistant principal, four tenths of a music
    # teacher and a COTA. The net is 5.3, and the net is the wrong figure to publish,
    # because it says three point nine came back rather than came back for a year.
    # ZERO, AND THAT IS THE WHOLE POINT. This field enters `approp`, which then COMPOUNDS
    # forward every year -- so a non-zero value here asserts that the town hands the schools
    # that much extra every year from now on. It held $350,000 (an early estimate of
    # Article 1) and was therefore quietly projecting a one-year state windfall as a
    # permanent raise, which made the gap look smaller than it is.
    #
    # Article 1 is one year of receipts above what the town budgeted, because the Governor
    # signed the FY27 state budget on 7 July 2026. Article 3 is a transfer from a fund
    # created by Select Board vote the day before Town Meeting. Neither recurs.
    #
    # AND THE REVENUE IS ALREADY HERE ANYWAY, which is the trap this field would spring
    # twice. `state_aid` above is 11,404,917 + 471,121: the Governor's gross cherry sheet
    # plus the ENACTED budget's increase over it. The warrant's $418,056 is the
    # education-specific part of that same enacted increase. Adding it again as
    # appropriation would count one windfall twice.
    #
    # So the money sits in revenue once, for one year, and the $392,264 of salary it bought
    # sits in the cost base for ever. That asymmetry IS the finding. TJ, 20 September 2026.
    #
    # THE TOWN'S OWN FRAMING, and it is the shared premise rather than the argument. The
    # Finance Committee of 13 August 2026 debates this money in exactly these words --
    # "we have used one-time funds to fund operations. We did it for fiscal year 26 that we
    # just ended" (the recording at 0:21:25) and "I for one am not hindered by the use of
    # one-time funds to fund this ... there is now precedent" (0:22:05). What is CONTESTED
    # there is whether spending it on operations is wise. That it does not recur is what
    # both sides assume in order to have the argument at all.
    #   https://www.youtube.com/watch?v=v4qvpgKlYRg&t=1285s
    #   https://www.youtube.com/watch?v=v4qvpgKlYRg&t=1325s
    # Cited as the RECORDING at a timestamp, never as minutes: those lines are our machine
    # captions, which are a finding aid and not a record. The decision above rests on the
    # warrant, which is a legal instrument and says the same thing in the town's own hand:
    # the enacted state budget "made available $418,056.00 more in education-specific
    # receipts than the Town's FY27 budget initially anticipated."
    stm_appropriation=0,
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


def project(years=5, assumptions=None, cuts_by_year=None, free_cash=None):
    """Project the gap. `free_cash` is OFF unless deliberately passed.

    RULE 1 AND WHY THIS IS NOT THE THING IT FORBIDS. Rule 1 exists because a growth rate
    measured from an actual to a budget is partly growth and partly the step between them —
    that error put the special education escalator 1.5 points high. Free cash is
    actuals-derived, so it belongs nowhere near a rate. It is used here as a ONE-TIME
    SUBTRACTION from a single year's deficit, after every rate has been applied. It touches
    no bucket, no escalator, no growth rate, and it does not carry into the next year's
    base. That is arithmetic on two labelled quantities, not a rate across the boundary.

    THE SAFETY PROPERTY, and it is proven rather than promised. `deficit` is never modified.
    Free cash is reported in two ADDITIONAL fields — `free_cash_applied` and
    `deficit_after_free_cash` — so a caller that does not know about them gets exactly the
    numbers it got before, and nothing downstream can shift because somebody enabled this.
    `scripts/audit_provenance.py` asserts all of it: that the default output is identical,
    that no bucket or growth rate moves at any draw, and that only the new fields respond.

    `free_cash` is dict(amount=..., years=n) — n spreads the draw over the first n years.
    """
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
        # Free cash is REVENUE in the year it is appropriated -- that is what it is, and
        # treating it as a gap adjustment instead made the teaching board's chart refuse to
        # move when the control was dragged. Applied after every rate has run.
        fc = max(float(a.get('free_cash_annual') or 0), 0.0)
        if free_cash:
            fc = max(float(free_cash.get('annual', 0) or 0), 0.0)
            if i == 0:
                fc += float(free_cash.get('one_time', 0) or 0)
            if free_cash.get('amount'):
                spread = max(1, int(free_cash.get('years', 1)))
                if i < spread:
                    fc += free_cash['amount'] / spread
        # Rounded to whole dollars BEFORE it is added. Adding an integer shifts every
        # downstream rounding by exactly that integer, so revenue, the gap and the
        # pre-free-cash gap all stay consistent with each other. Adding the raw float
        # instead put them off by a dollar, which audit_provenance.py caught.
        fc = float(round(fc))
        available = approp + a['athletic_fee_revenue'] + fc

        # --- level service cost ---
        for k in list(buckets):
            buckets[k] *= (1 + a[k])
        level_service = sum(buckets.values())

        deficit = level_service - available

        # One-time money, applied after everything rate-driven is finished. Reported
        # alongside the deficit and never inside it.
        fc_applied = fc

        out.append(dict(fy=fy, level_service=round(level_service),
                        available=round(available), appropriation=round(approp),
                        town_available=town_available,
                        # `deficit` is NET of the free cash lever, so the lever behaves like
                        # every other lever on the site. At the default of zero it is the
                        # same number it has always been. The gross figure is kept beside
                        # it so nothing has to be reverse-engineered.
                        deficit=round(deficit),
                        deficit_before_free_cash=round(deficit) + round(fc_applied),
                        growth_rate=round(growth_rate, 5),
                        free_cash_applied=round(fc_applied),
                        # Rounded from the ALREADY-ROUNDED pair, not from the raw
                        # difference: round(a) - round(b) is not round(a - b), and a
                        # published "after" figure that does not equal the two numbers
                        # printed beside it is the kind of thing somebody screenshots.
                        # audit_provenance.py caught this within a minute of existing.
                        deficit_after_free_cash=round(deficit),
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
