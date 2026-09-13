#!/usr/bin/env python3
"""THE ONE BIG REPORT, rebuilt as the numbers a resident needs to frame the problem.

    python3 scripts/build_big_picture.py            # write fy28/public/data/big-picture.json
    python3 scripts/build_big_picture.py --check    # fail if it no longer reproduces

TJ, 13 September 2026: "change the one big report to something more meaningful to people.
Something like: deficit per year each year for 5 years; how many years a 2m, 5m override
covers; key drivers of rates and deficits; how many commercial developments per year and
for how many years to bring in $1m per year...; some 'high level facts' that are not
conclusions... census facts like percent that have school age children, percent that are
seniors, total staff/FTEs at the school, total admins, change ... over the last 10 years,
total students (and change), total athletes (and change). We dont need EVERY fact. Just the
ones that draw a pretty serious and absolute conclusion."

FIVE SECTIONS, EVERY FIGURE COMPUTED HERE OR READ FROM A CHECKED PAYLOAD.

  1. THE HOLE, YEAR BY YEAR -- model/cascade.py's own run, the one the site's headline gap
     is averaged from: each year's shortfall after the year before's cuts stay cut, and
     what the cascade takes to close it.
  2. WHAT AN OVERRIDE BUYS -- a one-time school override raises the levy base once and
     grows at the cap; it holds for as long as the level-service gap stays under it. The
     same arithmetic as fy28/src/model/rates.ts `run()` (overrideLevy), and asserted to
     agree with it on one known value below.
  3. WHAT DRIVES IT -- each budget line's share of spending times how far its growth
     exceeds the levy cap (rule 4), from the model's own expense base and rates.
  4. WHAT BUILDING WOULD DO -- the new taxable value that yields $1M a year at the town's
     rate, in typical developments; and how many years at a given pace, compounding the
     way new growth does in the levy limit (model/taxbase.py).
  5. THE FACTS -- census shares from the by-the-numbers payload (already checked against
     the ACS files); teacher FTE, paraprofessional FTE, student headcount and per-pupil
     administration spending from DESE's own district files, ten years apart; athletes
     from the athletics payload, which holds three seasons of counts and no more.

WHAT IS DELIBERATELY NOT HERE. An ADMINISTRATOR HEADCOUNT. The annual-report rosters
classify department liaisons as administrators, print no central office at all in FY2025,
and carry no FTE; a series read off them would show administration falling 25% in a year
in which nothing of the kind happened. DESE publishes administration as DOLLARS PER PUPIL
and that is what is here, labelled as dollars. The headcount is a registered gap.
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from finance import project, expense_base, DEFAULT_ASSUMPTIONS, FY27       # noqa: E402
from cascade import run, PRESETS, expand                                    # noqa: E402
from catalog import PROGRAMS                                                # noqa: E402
from taxbase import CH70                                                    # noqa: E402
from taxbase import (TAX_RATE, TOTAL_VALUE, AVG_HOME_VALUE, MIX_VALUE, MIX_COMPOSITION,   # noqa: E402
                     CURRENT_NEW_GROWTH_VALUE, new_growth_revenue, value_needed,
                     compound_new_growth, LPS_APPROPRIATION, OMNIBUS)

OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'big-picture.json')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
RADAR = os.path.join(ROOT, 'sources', 'data', 'dese-radar.csv')
TEACHERS = os.path.join(ROOT, 'sources', 'data', 'dese-teacher-program-area.csv')
BY_THE_NUMBERS = os.path.join(ROOT, 'fy28', 'public', 'data', 'lunenburg-by-the-numbers.json')
ATHLETICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'athletics.json')

YEARS = 5
OVERRIDES = [2_000_000, 5_000_000]
TARGET_LEVY = 1_000_000          # "bring in $1m per year"
PACES = [2, 4, 8]                # developments a year, to show how the years fall
LEVY_CAP = DEFAULT_ASSUMPTIONS['levy_growth']
HORIZON = 30
# The one-time override rates.ts prices to hold exactly five years at today's rates, on
# 13 September 2026. If the two engines drift this fails, and that is the point.
RATES_TS_FIVE_YEAR_OVERRIDE = 3_100_460

LINE_LABEL = dict(salaries='Salaries', health='Health insurance', transport='Transportation',
                  sped='Special education, in district', sped_tuition='Out-of-district special education',
                  utilities='Utilities', other='Everything else')
LINE_WHO = dict(salaries='bargained with the unions', health='the Town buys the insurance',
                transport='contracted', sped='each child’s plan, and the law',
                sped_tuition='state rates and which children enrol', utilities='the market',
                other='the School Committee')


def fail(msg):
    print('FAIL: ' + msg)
    raise SystemExit(1)


def manifest():
    with open(MANIFEST, encoding='utf-8') as fh:
        return {r['key']: r for r in csv.DictReader(fh)}


def source(rows, key, note):
    r = rows.get(key)
    if not r:
        fail('%s is not in the manifest (rule 12)' % key)
    if not r['upstream']:
        fail('%s carries no upstream address (rule 12)' % key)
    return dict(key=key, path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']),
                url=r['upstream'], docs_url='/docs/' + key, filename=key.split('/')[-1], note=note)


# ------------------------------------------------------------------ 1. the hole

def the_hole():
    years = run(PRESETS['school_committee']['order'], DEFAULT_ASSUMPTIONS, YEARS)
    out = []
    for y in years:
        cuts = [c for c in y['cuts'] if not c['blocked']]
        out.append(dict(fy=2000 + y['fy'], short=y['deficit'], cut=y['cut_total'],
                        unclosed=y['unclosed'], cum_fte=y['cum_fte'],
                        fte=round(sum(c['fte'] for c in cuts), 1),
                        # the three largest things the cascade takes that year, by cost
                        takes=[c['name'] for c in sorted(cuts, key=lambda c: -c['cost'])[:3]]))
    total = sum(y['short'] for y in out)
    return dict(years=out, total=total, average=round(total / len(out)),
                order=PRESETS['school_committee']['order'],
                note=('Each year’s shortfall after the year before’s cuts stay cut, in the order '
                      'the School Committee has said it would cut. Level service means the same '
                      'people, the same programs, the same buildings, one year older.'))


# ------------------------------------------------------------- 2. what an override buys

def level_service_gaps(years=HORIZON):
    return [y['deficit'] for y in project(years=years)]


def years_held(levy, gaps):
    n = 0
    for i, g in enumerate(gaps):
        # Rounded to the dollar before the test, as rates.ts rounds its gap.
        if round(g - levy * (1 + LEVY_CAP) ** i) <= 0:
            n += 1
        else:
            break
    return n


def on_average_home(levy):
    return round(AVG_HOME_VALUE * (levy * 1000 / TOTAL_VALUE) / 1000)


def overrides():
    gaps = level_service_gaps()
    # Parity with rates.ts: its five-year override must hold five years here and not six.
    held = years_held(RATES_TS_FIVE_YEAR_OVERRIDE, gaps)
    if held != 5:
        fail('a %s override holds %d year(s) here; rates.ts says 5 -- the two engines disagree'
             % (f'${RATES_TS_FIVE_YEAR_OVERRIDE:,}', held))
    school_share = LPS_APPROPRIATION / OMNIBUS
    rows = []
    for amt in OVERRIDES:
        n = years_held(amt, gaps)
        rows.append(dict(amount=amt, years=n, reopens_fy=2028 + n if n < HORIZON else None,
                         on_average_home=on_average_home(amt),
                         # a GENERAL override has to be this big for the schools' share to be amt
                         townwide=round(amt / school_share),
                         townwide_on_average_home=on_average_home(amt / school_share)))
    return dict(rows=rows, school_share=round(school_share, 4), first_gap=gaps[0],
                note=('A school-only override: the levy base rises once by this amount, all of it '
                      'to the schools, and grows 2.5% a year after. It holds while the level-'
                      'service gap stays under it. A general override has to be larger, because '
                      'the schools take only their share of the town budget.'))


# ---------------------------------------------------------------- 3. what drives it

def drivers():
    base = expense_base()
    base['salaries'] += FY27['stm_addbacks']
    total = sum(base.values())
    rows = []
    for k, amt in base.items():
        rate = DEFAULT_ASSUMPTIONS[k]
        rows.append(dict(key=k, label=LINE_LABEL[k], who=LINE_WHO[k], amount=round(amt),
                         share=round(amt / total, 4), rate=rate,
                         pull=round(amt / total * (rate - LEVY_CAP), 5)))
    rows.sort(key=lambda r: -r['pull'])
    blended = sum(r['share'] * r['rate'] for r in rows)
    spread_over_cap = blended - LEVY_CAP
    top2 = rows[0]['pull'] + rows[1]['pull']
    return dict(rows=rows, blended=round(blended, 5), cap=LEVY_CAP,
                spread_over_cap=round(spread_over_cap, 5),
                top2_share=round(top2 / sum(r['pull'] for r in rows if r['pull'] > 0), 3),
                note=('A line matters in proportion to its share of spending times how far its '
                      'growth exceeds the 2.5% levy cap (rule 4). Neither number alone means '
                      'anything: the biggest line is not the biggest driver.'))


# ---------------------------------------------- 3b. when does cutting alone stabilise it

def cost_per_fte():
    """What a position costs, from the catalogue's own items -- rates.ts COST_PER_FTE."""
    items = [p for p in expand(PROGRAMS) if p['fte'] > 0]
    return round(sum(p['cost'] for p in items) / sum(p['fte'] for p in items))


def stabilise():
    """TJ, 13 September 2026: "how many staff need to be cut to bring the rate of growth to
    the revenue we get from prop 2.5? IOW when does the problem self stabilize due to cuts."

    The same equation as rates.ts salaryRateToBalance / workforceShrink, read from the
    other end. Costs grow at the blended rate; revenue, far enough out for new growth's
    flat dollars to have finished decaying, grows at the long-run rate. If every other
    line grows as assumed, the SALARY line has to grow at whatever rate makes the blend
    equal revenue -- and if people still get the contract raise, the only way the line
    grows more slowly is that there are fewer of them every year. Forever: a cut made
    once shifts the level and the rates reopen it; only a cut made every year is a rate."""
    base = expense_base()
    base['salaries'] += FY27['stm_addbacks']
    total = sum(base.values())
    w = {k: v / total for k, v in base.items()}
    target = project(years=HORIZON)[-1]['growth_rate']
    others = sum(w[k] * DEFAULT_ASSUMPTIONS[k] for k in base if k != 'salaries')
    salary_rate = (target - others) / w['salaries']
    contract = DEFAULT_ASSUMPTIONS['salaries']
    per_year = (1 + contract) / (1 + salary_rate) - 1
    cpf = cost_per_fte()
    headcount = round(base['salaries'] / cpf)
    after = lambda n: 1 - ((1 + salary_rate) / (1 + contract)) ** n
    return dict(target=round(target, 5), others=round(others, 5), salary_rate=round(salary_rate, 5),
                contract=contract, possible=salary_rate >= 0,
                shrink_per_year=round(per_year, 5), positions_per_year=round(base['salaries'] * per_year / cpf, 1),
                cost_per_fte=cpf, headcount=headcount,
                after10=round(after(10), 4), after20=round(after(20), 4),
                positions_after10=round(headcount * after(10)),
                note=('Revenue grows at the levy cap plus new growth, which decays toward the cap; '
                      'the rate used is the long-run one. Every other line grows as the model '
                      'assumes. Positions are at the catalogue’s own cost per position, an estimate; '
                      'the salary line covers stipends and part-time roles too.'))


# ------------------------------------------------------------ 4. what building would do

def development():
    value = value_needed(TARGET_LEVY)                  # new taxable value for $1M a year
    at_once = value / MIX_VALUE
    paces = []
    for per_year in PACES:
        # years until the compounding levy from `per_year` developments a year reaches the target
        series = compound_new_growth(per_year * MIX_VALUE, years=40)
        yrs = next((s['year'] for s in series if s['annual'] >= TARGET_LEVY), None)
        paces.append(dict(per_year=per_year, years=yrs))
    return dict(target=TARGET_LEVY, value=round(value), tax_rate=TAX_RATE,
                per_development=round(new_growth_revenue(MIX_VALUE)),
                development_value=MIX_VALUE, development_mix=MIX_COMPOSITION,
                at_once=round(at_once, 1), paces=paces,
                current_pace_value=CURRENT_NEW_GROWTH_VALUE,
                current_pace_developments=round(CURRENT_NEW_GROWTH_VALUE / MIX_VALUE, 1),
                share_of_town=round(value / TOTAL_VALUE, 4),
                note=('New growth adds to the levy limit permanently and then grows 2.5% a year, '
                      'so a steady pace compounds. The town budgets about $400,000 of new growth '
                      'a year today, most of it houses — which pay the same tax and send children '
                      'to school.'))


# --------------------------------------------------------------------- 5. the facts

def radar(measure):
    with open(RADAR, encoding='utf-8') as fh:
        rows = [r for r in csv.DictReader(fh)
                if 'Lunenburg' in r['district'] and r['measure'] == measure and r['value'] != '']
    return {int(r['fy']): float(r['value']) for r in rows}


def teachers():
    with open(TEACHERS, encoding='utf-8') as fh:
        rows = [r for r in csv.DictReader(fh)
                if 'Lunenburg' in r['district'] and r['org_level'] == 'district']
    return {int(r['fy']): dict(total=float(r['total_fte']), gen=float(r['gen_ed_fte']),
                               sped=float(r['sped_fte'])) for r in rows}


def change(series, last, span=10, key=None):
    first = last - span
    if first not in series or last not in series:
        fail('series lacks FY%d or FY%d' % (first, last))
    a = series[first][key] if key else series[first]
    b = series[last][key] if key else series[last]
    return dict(first_fy=first, last_fy=last, first=a, last=b, change=round(b - a, 4),
                pct=round((b - a) / a, 4) if a else None)


def facts():
    btn = json.load(open(BY_THE_NUMBERS, encoding='utf-8'))
    ath = json.load(open(ATHLETICS, encoding='utf-8'))
    senior = next(g for g in btn['ages']['groups'] if g['key'] == 'senior')
    child = next(g for g in btn['ages']['groups'] if g['key'] == 'children')
    hh = btn['households']
    t = teachers()
    t_last = max(t)
    heads = radar('Student Headcount')
    paras = radar('Paraprofessional FTE')
    admin = radar('Administration')
    total_pp = radar('Total Expenditures')
    r_last = max(heads)
    tot = ath['participation_totals']
    low = radar('Low-Income % Headcount')
    swd = radar('Students with disabilities % Headcount')
    return dict(
        low_income=dict(grain='share of students DESE counts as low-income', **change(low, r_last)),
        disabilities=dict(grain='share of students with disabilities, DESE', **change(swd, r_last)),
        state_aid=dict(grain='Chapter 70 aid against the school appropriation, FY26',
                       aid=CH70['aid'], appropriation=LPS_APPROPRIATION,
                       share=round(CH70['aid'] / LPS_APPROPRIATION, 4)),
        census=dict(vintage=btn['vintage'], window=btn['window'],
                    households_with_child=dict(share=hh['share'], share_moe=hh['share_moe'],
                                               n=hh['with_child']['estimate'], of=hh['households']['estimate']),
                    seniors=dict(share=senior['share'], share_moe=senior['share_moe'], n=senior['estimate']),
                    children=dict(share=child['share'], share_moe=child['share_moe'], n=child['estimate'])),
        students=dict(grain='DESE student headcount, October 1', **change(heads, r_last)),
        teachers=dict(grain='teacher FTE as DESE counts it — per assignment, not per person',
                      # The general/special split is NOT published: DESE's program-area
                      # coding moves special education teachers into general education
                      # across these years (10.8 -> 2.0 FTE), which is a coding change
                      # wearing the clothes of a finding. The total is what is stable.
                      **change(t, t_last, key='total')),
        paras=dict(grain='paraprofessional FTE, DESE', **change(paras, r_last)),
        admin_per_pupil=dict(grain='administration spending per pupil, DESE — dollars, not people',
                             **change(admin, r_last), total_per_pupil=change(total_pp, r_last)),
        athletes=dict(grain='participations, by season — a two-sport athlete counts twice',
                      first_fy=tot[0]['fy'], last_fy=tot[-1]['fy'], first=tot[0]['total'],
                      last=tot[-1]['total'], change=tot[-1]['total'] - tot[0]['total'],
                      pct=round((tot[-1]['total'] - tot[0]['total']) / tot[0]['total'], 4),
                      years=len(tot)),
    )


# ---------------------------------------------------------------------------- build

def build():
    rows = manifest()
    f = facts()
    return dict(
        about=('The numbers that frame the problem, on one page: the hole year by year, what '
               'an override buys, what drives it, what building would do, and the facts about '
               'the town and its schools that any solution has to fit.'),
        grain=('Dollars from the model the rest of this site runs on; people and children from '
               'DESE’s own district files, ten years apart; residents from the Census Bureau’s '
               'five-year survey, with its margins.'),
        hole=the_hole(), overrides=overrides(), drivers=drivers(), stabilise=stabilise(),
        development=development(),
        facts=f,
        not_established=[
            'How many ADMINISTRATORS the district employs, and how that changed. The annual-report '
            'rosters carry names without FTE, classify department liaisons as administrators, and '
            'print no central office at all in FY2025; DESE publishes administration as dollars '
            'per pupil, which is what this page shows. Closes: the district’s position control '
            'list, by FTE and funding source, for any two years.',
            'How many athletes there are over ten years. The district has published season '
            'participation counts for three years; earlier years exist in athletic department '
            'reports the archive does not hold.',
            'Which fund pays which teacher. DESE’s FTE counts every assignment whatever pays for '
            'it; a grant ending and a position ending look the same in the town’s budget and '
            'different here, and nothing joins the two.',
        ],
        sources=[
            source(rows, 'state-dese/radar-district-comparison.xlsx',
                   'DESE RADAR district comparison: student headcount, paraprofessional FTE and '
                   'per-pupil spending by function, FY2009–FY2025.'),
            source(rows, 'state-dese/dese-teacher-data.xlsx',
                   'DESE teacher data: teacher FTE by district and program area, FY2008–FY2026.'),
        ] + btn_sources(),
        generated_by='scripts/build_big_picture.py',
    )


def btn_sources():
    btn = json.load(open(BY_THE_NUMBERS, encoding='utf-8'))
    return [s for s in btn['sources'] if s['table'].startswith(('B01001', 'B11005'))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        if have != data:
            print('STALE %s — run build_big_picture.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the model and the DESE files' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    h = data['hole']
    print('%s: FY%d–FY%d short %s in total; $2M holds %d years, $5M %d; %s'
          % (os.path.relpath(OUT, ROOT), h['years'][0]['fy'], h['years'][-1]['fy'],
             f"${h['total']:,}", data['overrides']['rows'][0]['years'],
             data['overrides']['rows'][1]['years'], data['development']['paces']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
