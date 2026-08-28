import sys, json, csv
sys.path.insert(0, 'model')
from catalog import PROGRAMS, CATEGORIES
from finance import DEFAULT_ASSUMPTIONS, FY27, expense_base
from cascade import PRESETS
from peers import PEERS, LESSONS
from athletics import (SPORTS, OTHER_PROGRAMS, FEE_BENCHMARKS, PROGRAM_TOTAL_LEVEL_SERVICE,
    PROGRAM_TOTAL_REMAINING, CURRENT_ATHLETIC_FEES, CURRENT_BUS_FEES, FEE_ACCOUNTING,
    HS_PARTICIPATIONS, MS_PARTICIPATIONS, EFFECTIVE_ATHLETIC_FEE,
    ESTIMATED_CURRENT_ATHLETIC_REVENUE, PRIOR_EFFECTIVE_ATHLETIC_FEE,
    PROGRAM_TOTAL_ADOPTED, CHARGEABLE_PARTICIPATIONS, ESTIMATED_FY26_ATHLETIC_REVENUE,
    PROGRAM_TOTAL_TRAVEL, PROGRAM_LADDER, self_funding_fee, fee_revenue,
    PEAK_FEE, PEAK_REVENUE, FEE_DROPOFF_PER_100,
    ESTIMATED_PRIOR_ATHLETIC_REVENUE, ESTIMATED_FEE_INCREASE_VALUE, SIBLING_MIX,
    WAIVER_ASSUMPTION)
from recommendation import PACKAGE, PRIORITY_WHY, CLOSING
from business import FORMATION_HISTORY, SUMMARY as BIZ_SUMMARY, TOP_CATEGORIES
from health import (PLANS as HEALTH_PLANS, TOWN_SHARE, RATE_INCREASE_FY27,
    DEFAULT_ENROLMENT, DEFAULT_FAMILY_SHARE, CONSTRAINTS as HEALTH_CONSTRAINTS,
    SCHOOL_HEALTH_BUDGET)
from headlines import HEADLINES
from conclusions import CONCLUSIONS, HEADLINE
from taxbase import (TAX_RATE, LEVY, TOTAL_VALUE, RESIDENTIAL_SHARE, CIP_SHARE,
    AVG_HOME_VALUE, AVG_HOME_BILL, SPLIT_RATE, CH70, ARCHETYPES, LOCAL_COST_PER_PUPIL,
    SCHOOL_SHARE_OF_BILL, SCHOOL_SHARE_OF_BUDGET, HOMES_PER_PUPIL,
    CURRENT_NEW_GROWTH_REVENUE, CURRENT_NEW_GROWTH_VALUE, ENROLLMENT,
    FY23, BUSINESSES, EMPLOYEES, PAYROLL, AVG_COMMERCIAL_VALUE, FY23_NEW_VALUE,
    COMMERCIAL_CONTEXT, NEW_GROWTH_HISTORY, VALUE_BY_CLASS, AVG_HOME_HISTORY,
    EXCESS_LEVY_CAPACITY, GAP_IN_BUSINESSES, MIX_VALUE)
import derivations
import citations
from levers import LEVERS, ADMIN_TOTAL, ADMIN_CENTRAL, ADMIN_BUILDING, TECH_TOTAL, HEALTH_TOTAL, TRANSPORT_GENED, TRANSPORT_SPED

data_ladder = [dict(r, selfFundFee=self_funding_fee(r['total']),
                    coverageNow=round(fee_revenue(EFFECTIVE_ATHLETIC_FEE) / r['total'], 4))
               for r in PROGRAM_LADDER]

scen = {'restoration': 28520816, 'core': 28172289,
        'level_service': 27333289, 'balanced': 26572288}

data = dict(
    meta=dict(generated='2026-08-18', base_year='FY27',
              note='FY28+ figures are projections built from published FY27 mechanics, '
                   'not published FY28 numbers.'),
    categories=CATEGORIES,
    programs=PROGRAMS,
    presets=PRESETS,
    assumptions=DEFAULT_ASSUMPTIONS,
    fy27=FY27,
    expenseBase=expense_base(),
    citations=citations.export(),
    scenarios=scen,
    peers=PEERS,
    sports=SPORTS,
    otherPrograms=OTHER_PROGRAMS,
    feeBenchmarks=FEE_BENCHMARKS,
    currentFees=dict(athletic=CURRENT_ATHLETIC_FEES, bus=CURRENT_BUS_FEES,
                     hsParticipations=HS_PARTICIPATIONS, msParticipations=MS_PARTICIPATIONS,
                     effectiveAthletic=EFFECTIVE_ATHLETIC_FEE,
                     estimatedAthleticRevenue=ESTIMATED_CURRENT_ATHLETIC_REVENUE,
                     priorEffectiveAthletic=PRIOR_EFFECTIVE_ATHLETIC_FEE,
                     estimatedPriorAthleticRevenue=ESTIMATED_PRIOR_ATHLETIC_REVENUE,
                     feeIncreaseValue=ESTIMATED_FEE_INCREASE_VALUE,
                     siblingMix=SIBLING_MIX, waiverAssumption=WAIVER_ASSUMPTION,
                     chargeableParticipations=CHARGEABLE_PARTICIPATIONS,
                     estimatedFy26Revenue=ESTIMATED_FY26_ATHLETIC_REVENUE),
    feeAccounting=FEE_ACCOUNTING,
    taxBase=dict(
        rate=TAX_RATE, levy=LEVY, totalValue=TOTAL_VALUE,
        residentialShare=RESIDENTIAL_SHARE, cipShare=CIP_SHARE,
        avgHomeValue=AVG_HOME_VALUE, avgHomeBill=AVG_HOME_BILL,
        splitRate=SPLIT_RATE, ch70=CH70, archetypes=ARCHETYPES,
        localCostPerPupil=LOCAL_COST_PER_PUPIL,
        schoolShareOfBill=SCHOOL_SHARE_OF_BILL,
        schoolShareOfBudget=round(SCHOOL_SHARE_OF_BUDGET, 4),
        homesPerPupil=HOMES_PER_PUPIL, enrollment=ENROLLMENT,
        currentNewGrowthRevenue=CURRENT_NEW_GROWTH_REVENUE,
        currentNewGrowthValue=CURRENT_NEW_GROWTH_VALUE,
        levyGrowth=0.025,
        fy23=FY23, businesses=BUSINESSES, employees=EMPLOYEES, payroll=PAYROLL,
        avgCommercialValue=AVG_COMMERCIAL_VALUE, fy23NewValue=FY23_NEW_VALUE,
        commercialContext=COMMERCIAL_CONTEXT,
        newGrowthHistory=NEW_GROWTH_HISTORY, valueByClass=VALUE_BY_CLASS,
        avgHomeHistory=AVG_HOME_HISTORY, excessLevyCapacity=EXCESS_LEVY_CAPACITY,
        gapInBusinesses=GAP_IN_BUSINESSES, mixValue=MIX_VALUE),
    business=dict(formationHistory=FORMATION_HISTORY, summary=BIZ_SUMMARY,
                  categories=TOP_CATEGORIES),
    health=dict(plans=HEALTH_PLANS, townShare=TOWN_SHARE,
                rateIncrease=RATE_INCREASE_FY27, enrolment=DEFAULT_ENROLMENT,
                familyShare=DEFAULT_FAMILY_SHARE, constraints=HEALTH_CONSTRAINTS,
                budget=SCHOOL_HEALTH_BUDGET),
    headlines=HEADLINES,
    conclusions=CONCLUSIONS,
    headline=HEADLINE,
    levers=LEVERS,
    recommendation=dict(package=PACKAGE, priorityWhy=PRIORITY_WHY, closing=CLOSING),
    athletics=dict(levelService=PROGRAM_TOTAL_LEVEL_SERVICE,
                   adopted=PROGRAM_TOTAL_ADOPTED,
                   travel=PROGRAM_TOTAL_TRAVEL,
                   ladder=data_ladder,
                   peakFee=PEAK_FEE, peakRevenue=round(PEAK_REVENUE),
                   dropoffPer100=FEE_DROPOFF_PER_100,
                   remaining=PROGRAM_TOTAL_REMAINING,
                   participations=sum(s['students'] for s in SPORTS),
                   chargeableParticipations=CHARGEABLE_PARTICIPATIONS,
                   msParticipations=MS_PARTICIPATIONS,
                   perSportTotal=round(sum(s['cost'] for s in SPORTS), 2)),
    extras=[
        dict(cat='athletics', label='Every sport, coach, trainer and athletic bus',
             total=466244,
             items=['All 25 sports and their coaches', 'Athletic transportation',
                    'Athletic trainer', 'Middle school & freshman sports',
                    'Athletic director, insurance, dues, equipment']),
        dict(cat='arts', label='Every band, chorus, art supply and music program',
             total=166056,
             items=['High school band & chorus', 'Art supplies, all four schools',
                    'Music teachers at the high school and Turkey Hill',
                    'Instruments, repairs and sheet music', 'Band transportation']),
        dict(cat='activities', label='Every club and after-school advisor',
             total=11731,
             items=['All advised clubs at the high school']),
    ],
    buckets=dict(admin=ADMIN_TOTAL, adminCentral=ADMIN_CENTRAL,
                 adminBuilding=ADMIN_BUILDING, tech=TECH_TOTAL,
                 health=HEALTH_TOTAL, transportGenEd=TRANSPORT_GENED,
                 transportSpEd=TRANSPORT_SPED),
    peerLessons=LESSONS,
    method=derivations.export(PROGRAMS, data_ladder),
    facts=dict(
        overrideQ1=dict(amount=2400000, yes=867, no=1753),
        overrideQ2=dict(amount=3300000, yes=760, no=1862),
        ballotsCast=2638, registered=9565,
        fy26TaxRate=14.39, avgHomeValue=517296, avgTaxBill=7444,
        levyOnlyIncrease=175.88, tier1TaxIncrease=506.95, tier2TaxIncrease=689.35,
        stmDate='2026-09-03', stmAmount=350000, stmPlanTotal=453722,
        enactedStateAid=471121,
        athleticsTotal=451830, athleticsRemaining=217908, athleticsAlreadyCut=233922,
        musicSupplies=17073, artSupplies=30685, clubs=11731,
    ),
)
json.dump(data, open('fy28/src/data/model.json', 'w'), indent=1)
print('wrote fy28/src/data/model.json', len(json.dumps(data)), 'bytes')
