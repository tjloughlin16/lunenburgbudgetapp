"""Lunenburg's tax base, and what commercial growth is actually worth.

Everything here is derived from published figures:
  FY26 tax rate $14.39 / $1,000, single rate (Select Board declined a split rate)
  FY26 levy $35,819,996  -> total taxable value = levy / rate
  Residential ~91% of value; commercial + industrial + personal under 10%
  DESE FY27 Chapter 70: foundation enrollment 1,599; foundation budget $23,089,580;
    required local contribution $14,135,611; Chapter 70 aid $9,349,335;
    required net school spending $23,484,946
"""

TAX_RATE = 14.39                 # per $1,000, FY26, single rate
LEVY = 35_819_996                # FY26
TOTAL_VALUE = round(LEVY / TAX_RATE * 1000)
RESIDENTIAL_SHARE = 0.91
CIP_SHARE = 0.09                 # commercial + industrial + personal property

AVG_HOME_VALUE = 517_296
AVG_HOME_BILL = 7_444

# Split-rate scenario the Select Board considered and rejected for FY26
SPLIT_RATE = dict(residential=13.70, commercial=21.58,
                  avgCommercialIncrease=2_300.36)

# DESE FY27 Chapter 70
CH70 = dict(foundationEnrollment=1599, foundationBudget=23_089_580,
            requiredContribution=14_135_611, aid=9_349_335,
            requiredNSS=23_484_946)

LPS_APPROPRIATION = 26_572_288
ENROLLMENT = 1581
OMNIBUS = 49_963_990.19

# What one student costs the LEVY, after state aid
LOCAL_COST_PER_PUPIL = round((LPS_APPROPRIATION - CH70['aid']) / ENROLLMENT)
# Share of the omnibus that goes to the schools
SCHOOL_SHARE_OF_BUDGET = LPS_APPROPRIATION / OMNIBUS
# School portion of an average residential tax bill
SCHOOL_SHARE_OF_BILL = round(AVG_HOME_BILL * SCHOOL_SHARE_OF_BUDGET)
# Homes needed, in school-tax terms, to educate one child
HOMES_PER_PUPIL = round(LOCAL_COST_PER_PUPIL / SCHOOL_SHARE_OF_BILL, 2)

# Illustrative development archetypes. Assessed values are ORDER-OF-MAGNITUDE
# ESTIMATES by us, not Lunenburg assessments -- they exist so people can reason in
# buildings rather than millions. Users can edit the value.
# Illustrative development archetypes. Assessed values are ORDER-OF-MAGNITUDE
# ESTIMATES by us, not Lunenburg assessments -- they exist so people can reason in
# buildings rather than millions. `plausible` marks what actually fits Lunenburg:
# a town of 2,100 acres of commercial-zoned land, mostly without municipal sewer,
# whose existing commercial stock averages about $658,000 per establishment.
#
# The MIX is the default. It is a weighted blend of the plausible types, so one
# "typical development" is what the town might realistically permit -- rather than
# implying the answer is a distribution center nobody is going to build here.
MIX_RECIPE = [
    ('small_biz', 0.35), ('restaurant', 0.15), ('storage', 0.10),
    ('plaza', 0.15), ('solar', 0.10), ('light_ind', 0.15),
]

_BASE = {
    'small_biz':    dict(name='Small shop or office (5,000 sq ft)', value=1_200_000, plausible=True),
    'restaurant':   dict(name='Restaurant', value=900_000, plausible=True),
    'storage':      dict(name='Self-storage facility', value=3_000_000, plausible=True),
    'plaza':        dict(name='Retail plaza (20,000 sq ft)', value=4_000_000, plausible=True),
    'solar':        dict(name='Solar array (~5 MW)', value=5_000_000, plausible=True),
    'light_ind':    dict(name='Light industrial / warehouse (50k sq ft)', value=7_000_000, plausible=True),
    'distribution': dict(name='Distribution center (150k sq ft)', value=20_000_000, plausible=False),
    'house':        dict(name='Single-family home (town average)', value=AVG_HOME_VALUE, plausible=False),
}

MIX_VALUE = round(sum(_BASE[k]['value'] * w for k, w in MIX_RECIPE))
MIX_COMPOSITION = ' · '.join(
    f"{int(w * 100)}% {_BASE[k]['name'].split('(')[0].strip().lower()}"
    for k, w in MIX_RECIPE)

ARCHETYPES = [dict(id='mix', name='Typical Lunenburg development (mixed)',
                   value=MIX_VALUE, plausible=True, note=MIX_COMPOSITION)] + [
    dict(id=k, **v,
         note=('Not realistic for Lunenburg — no site, sewer or market for it'
               if k == 'distribution' else
               'Residential: pays the same tax but sends children to school'
               if k == 'house' else ''))
    for k, v in _BASE.items()
]

def new_growth_revenue(new_value, rate=TAX_RATE):
    """New growth adds permanently to the levy limit: value x prior-year rate."""
    return new_value * rate / 1000

def value_needed(target, rate=TAX_RATE):
    return target * 1000 / rate

if __name__ == '__main__':
    print(f'Total taxable value      ${TOTAL_VALUE:>15,}')
    print(f'  residential (91%)      ${round(TOTAL_VALUE*RESIDENTIAL_SHARE):>15,}')
    print(f'  commercial etc (9%)    ${round(TOTAL_VALUE*CIP_SHARE):>15,}')
    print(f'Each $1M of new value    ${new_growth_revenue(1_000_000):>15,.0f} per year, forever')
    print()
    gap = 613_238
    v = value_needed(gap)
    print(f'To cover the FY28 gap ({gap:,}) in one year of new growth:')
    print(f'  new assessed value needed  ${v:>15,.0f}')
    print(f'  = {v/TOTAL_VALUE*100:.2f}% of the entire town tax base, added in a single year')
    for a in ARCHETYPES[:7]:
        print(f'  or {v/a["value"]:>6.1f} x {a["name"]}')
    print()
    print(f'Chapter 70 aid per pupil       ${CH70["aid"]/CH70["foundationEnrollment"]:>10,.0f}')
    print(f'Local cost per pupil (levy)    ${LOCAL_COST_PER_PUPIL:>10,}')
    print(f'School share of avg tax bill   ${SCHOOL_SHARE_OF_BILL:>10,}')
    print(f'Average homes per pupil        {HOMES_PER_PUPIL:>11}')


# New growth already happening: the town budgets $400,000 of new growth in FY27,
# which at $14.39/$1,000 implies about $27.8M of new taxable value added each year,
# most of it residential.
CURRENT_NEW_GROWTH_REVENUE = 400_000
CURRENT_NEW_GROWTH_VALUE = round(CURRENT_NEW_GROWTH_REVENUE * 1000 / TAX_RATE)

LEVY_GROWTH = 0.025

def compound_new_growth(extra_value_per_year, years=10, rate=TAX_RATE,
                        levy_growth=LEVY_GROWTH):
    """New growth is permanent: once in the levy limit it stays and grows 2.5% a year.
    Returns the extra revenue available in each year, and the cumulative total."""
    out, base, cum = [], 0.0, 0.0
    for i in range(years):
        base = base * (1 + levy_growth) + new_growth_revenue(extra_value_per_year, rate)
        cum += base
        out.append(dict(year=i + 1, annual=round(base), cumulative=round(cum)))
    return out

def compound_override(amount, years=10, levy_growth=LEVY_GROWTH):
    """An override is also permanent and also grows 2.5% -- but it lands in full
    immediately, and it comes from existing taxpayers."""
    out, base, cum = [], 0.0, 0.0
    for i in range(years):
        base = amount * ((1 + levy_growth) ** i)
        cum += base
        out.append(dict(year=i + 1, annual=round(base), cumulative=round(cum)))
    return out

if __name__ == '__main__':
    print()
    print(f'Already happening: ${CURRENT_NEW_GROWTH_REVENUE:,}/yr of new growth')
    print(f'  implies ~${CURRENT_NEW_GROWTH_VALUE:,} of new value added each year')
    print()
    print('Compounding: adding $15M/yr of EXTRA commercial value')
    for r in compound_new_growth(15_000_000, 10)[:10:2]:
        print(f"  year {r['year']:>2}: +${r['annual']:>9,}/yr   cumulative ${r['cumulative']:>11,}")
    print()
    print('Versus a $613,238 override, same ten years')
    for r in compound_override(613_238, 10)[:10:2]:
        print(f"  year {r['year']:>2}: +${r['annual']:>9,}/yr   cumulative ${r['cumulative']:>11,}")


# ---------------------------------------------------------------------------
# Reality anchors for "what does $15M a year actually mean?"
# ---------------------------------------------------------------------------

# FY2023 Tax Classification Hearing (Board of Assessors) -- hard figures
FY23 = dict(
    residentialValue=1_957_462_820, residentialShare=0.927077,
    cipValue=153_972_120, cipShare=0.072923,
    totalValue=2_111_434_940,
    newGrowth=234_383,               # actual new growth added to the FY23 levy limit
    levyLimit=28_043_723,
    splitRateResidential=14.05, splitRateCIP=21.93,
    maxShiftResidentialSaving=0.039, maxShiftCIPIncrease=0.50,
)

# US Census Business Patterns, 2024
BUSINESSES = 234
EMPLOYEES = 2_172
PAYROLL = 126_716_000

AVG_COMMERCIAL_VALUE = round(FY23['cipValue'] / BUSINESSES)

# The town's real average, offered as a unit in the calculator so that one control
# drives every figure -- rather than a fixed "average business" count sitting beside
# an archetype count and appearing not to react.
ARCHETYPES.insert(1, dict(
    id='avg_existing', name='Average existing Lunenburg business',
    value=AVG_COMMERCIAL_VALUE, plausible=True,
    note=f"The real figure from the tax rolls: ${FY23['cipValue']:,} of commercial, "
         f"industrial and personal property across {BUSINESSES} establishments."))

FY23_PRIOR_RATE = 13.51            # FY22 rate, used to compute FY23 new growth
FY23_NEW_VALUE = round(FY23['newGrowth'] * 1000 / FY23_PRIOR_RATE)

COMMERCIAL_CONTEXT = dict(
    corridors=['Route 2A (Massachusetts Avenue)', 'Route 13 (Chase Road)',
               'Leominster-Shirley Road and Route 70, near Fitchburg/Leominster sewer'],
    anchor='The Route 2A retail strip is shadow-anchored by Walmart and Hannaford, with '
           'over 20,000 vehicles a day and roughly 2.6 million annual visits.',
    targets=['Advanced manufacturing', 'Healthcare and social assistance'],
    constraint='Commercial development clusters where municipal sewer reaches, which is '
               'why the same three corridors come up in every economic development '
               'conversation.',
)


def growth_in_context(extra_value_per_year):
    return dict(
        businessesEquivalent=extra_value_per_year / AVG_COMMERCIAL_VALUE,
        pctOfCommercialBase=extra_value_per_year / FY23['cipValue'] * 100,
        pctOfTotalBase=extra_value_per_year / FY23['totalValue'] * 100,
        vsActualNewGrowth=extra_value_per_year / FY23_NEW_VALUE,
        revenue=new_growth_revenue(extra_value_per_year),
        vsActualNewGrowthRevenue=new_growth_revenue(extra_value_per_year) / FY23['newGrowth'],
    )


if __name__ == '__main__':
    print()
    print(f'Businesses (Census 2024): {BUSINESSES}, {EMPLOYEES:,} employees')
    print(f'CIP value FY23: ${FY23["cipValue"]:,} ({FY23["cipShare"]*100:.2f}% of base)')
    print(f'Average value per establishment: ${AVG_COMMERCIAL_VALUE:,}')
    print(f'FY23 ACTUAL new growth: ${FY23["newGrowth"]:,} '
          f'(~${FY23_NEW_VALUE:,} of new value, all classes)')
    print()
    for v in (5_000_000, 15_000_000, 30_000_000):
        c = growth_in_context(v)
        print(f'${v/1e6:.0f}M/yr of new commercial value:')
        print(f'   ~{c["businessesEquivalent"]:.0f} more average businesses EVERY year')
        print(f'   +{c["pctOfCommercialBase"]:.1f}% of the commercial base every year')
        print(f'   {c["vsActualNewGrowth"]:.1f}x the town\'s entire recent new growth')
        print(f'   ${c["revenue"]:,.0f}/yr revenue = {c["vsActualNewGrowthRevenue"]:.1f}x FY23 new growth')
        print()


# ---------------------------------------------------------------------------
# Year-over-year series, from the FY2023 Tax Classification Hearing
# (Lunenburg Board of Assessors). These are the town's own published figures.
# ---------------------------------------------------------------------------

# New growth added to the levy limit, by fiscal year. Declining.
NEW_GROWTH_HISTORY = [
    dict(fy=2018, amount=481_496),
    dict(fy=2019, amount=472_536),
    dict(fy=2020, amount=366_231),
    dict(fy=2021, amount=308_732),
    dict(fy=2022, amount=430_254),
    dict(fy=2023, amount=234_383),
]

# Assessed value by class, FY22 -> FY23. Residential boomed; every commercial
# class SHRANK in absolute dollars.
VALUE_BY_CLASS = [
    dict(cls='Residential',       fy23=1_957_462_820, fy22=1_587_173_648),
    dict(cls='Commercial',        fy23=74_992_410,    fy22=75_178_002),
    dict(cls='Industrial',        fy23=23_827_000,    fy22=24_608_600),
    dict(cls='Personal property', fy23=55_152_710,    fy22=55_708_580),
]
for _v in VALUE_BY_CLASS:
    _v['change'] = _v['fy23'] - _v['fy22']
    _v['pct'] = round(_v['change'] / _v['fy22'] * 100, 2)

# The Proposition 2 1/2 paradox, in the town's own numbers: values up 52%,
# rate down 22%, bills up only 19%.
AVG_HOME_HISTORY = [
    dict(fy=2019, rate=18.68, value=308_900, bill=5_770.25),
    dict(fy=2020, rate=18.12, value=332_400, bill=6_023.09),
    dict(fy=2021, rate=17.74, value=351_400, bill=6_233.84),
    dict(fy=2022, rate=17.19, value=374_400, bill=6_435.94),
    dict(fy=2023, rate=14.62, value=470_164, bill=6_873.80),
]

# The town levies essentially to the maximum every year -- there is no slack.
EXCESS_LEVY_CAPACITY = [
    dict(fy=2019, amount=53_705.72), dict(fy=2020, amount=3.12),
    dict(fy=2021, amount=4_112.57), dict(fy=2022, amount=6_488.03),
    dict(fy=2023, amount=6_477.18),
]

if __name__ == '__main__':
    print('\nNEW GROWTH BY YEAR (town figures)')
    for g in NEW_GROWTH_HISTORY:
        print(f"  FY{g['fy']}  ${g['amount']:>9,}")
    d = NEW_GROWTH_HISTORY[-1]['amount'] / NEW_GROWTH_HISTORY[0]['amount'] - 1
    print(f"  FY18 -> FY23 change: {d*100:.0f}%")
    print('\nASSESSED VALUE BY CLASS, FY22 -> FY23')
    for v in VALUE_BY_CLASS:
        print(f"  {v['cls']:<18} ${v['fy22']:>15,} -> ${v['fy23']:>15,}  {v['pct']:>7.2f}%")
    print('\nAVERAGE SINGLE FAMILY')
    for h in AVG_HOME_HISTORY:
        print(f"  FY{h['fy']}  rate {h['rate']:>5}  value ${h['value']:>9,}  bill ${h['bill']:>8,.2f}")
    a, b = AVG_HOME_HISTORY[0], AVG_HOME_HISTORY[-1]
    print(f"  value +{(b['value']/a['value']-1)*100:.0f}%  rate {(b['rate']/a['rate']-1)*100:.0f}%  "
          f"bill +{(b['bill']/a['bill']-1)*100:.0f}%")


# ---------------------------------------------------------------------------
# The taxpayer's view. Does new growth lower my bill?
# ---------------------------------------------------------------------------

def rate_after(new_value, levy=LEVY, total=TOTAL_VALUE, rate=TAX_RATE,
               levy_growth=LEVY_GROWTH):
    """Next year's tax rate, with and without a given amount of new growth.

    Lunenburg levies essentially to its maximum every year (excess capacity has been
    single-digit thousands), so the levy rises by 2.5% plus new growth, and the rate is
    whatever satisfies levy / value. New growth adds revenue AND taxable value in almost
    the same proportion -- which is why it barely moves the rate.
    """
    base_levy = levy * (1 + levy_growth)
    without = base_levy / total * 1000
    with_growth = (base_levy + new_growth_revenue(new_value, rate)) / (total + new_value) * 1000
    return dict(without=round(without, 4), with_growth=round(with_growth, 4),
                difference=round(with_growth - without, 4))


def override_cost_per_home(amount, home_value=AVG_HOME_VALUE, total=TOTAL_VALUE):
    """What raising `amount` through an override costs one homeowner, per year."""
    return amount / total * home_value


def taxpayer_view(new_value, gap, home_value=AVG_HOME_VALUE):
    r = rate_after(new_value)
    revenue = new_growth_revenue(new_value)
    return dict(
        rateWithout=r['without'], rateWith=r['with_growth'], rateChange=r['difference'],
        billChange=r['difference'] * home_value / 1000,
        revenue=revenue,
        shareOfGap=revenue / gap * 100,
        overrideAvoidedPerHome=override_cost_per_home(revenue, home_value),
        fullGapOverridePerHome=override_cost_per_home(gap, home_value),
    )


if __name__ == '__main__':
    GAP = 613_238
    print(f'\nAn override covering the whole FY28 gap (${GAP:,}) would cost the average '
          f'home ${override_cost_per_home(GAP):,.2f} a year.\n')
    for v in (5_000_000, 15_000_000, 30_000_000):
        t = taxpayer_view(v, GAP)
        print(f'${v/1e6:.0f}M of new commercial value:')
        print(f"   tax rate without it   ${t['rateWithout']:.4f}")
        print(f"   tax rate with it      ${t['rateWith']:.4f}   (change {t['rateChange']:+.4f})")
        print(f"   effect on avg bill    ${t['billChange']:+,.2f} a year")
        print(f"   revenue raised        ${t['revenue']:,.0f}  = {t['shareOfGap']:.0f}% of the gap")
        print(f"   override avoided      ${t['overrideAvoidedPerHome']:,.2f} per home per year")
        print()


# ---------------------------------------------------------------------------
# What closing the gap with business growth alone would actually require.
# ---------------------------------------------------------------------------
GAP_FY28 = 613_238
GAP_AVG_ANNUAL = 579_125          # mean FY28-32 gap from the cut cascade

def businesses_needed(gap):
    v = value_needed(gap)
    n = v / AVG_COMMERCIAL_VALUE
    return dict(
        value=round(v),
        developments=round(v / MIX_VALUE, 1),
        businesses=round(n),
        pctOfToday=round(n / BUSINESSES * 100),
        vsActualNewGrowth=round(v / FY23_NEW_VALUE, 1),
        fiveYearAdded=round(n * 5),
        fiveYearTotal=round(BUSINESSES + n * 5),
        fiveYearPct=round(n * 5 / BUSINESSES * 100),
    )

GAP_IN_BUSINESSES = dict(fy28=businesses_needed(GAP_FY28),
                         sustained=businesses_needed(GAP_AVG_ANNUAL))
