#!/usr/bin/env python3
"""What Lunenburg would have to spend to reach the middle, and to match where its own
children go.

    python3 scripts/build_spending_target.py           # write sources/analyses/spending-compared.md
    python3 scripts/build_spending_target.py --check   # fail if it is stale

TJ, 20 September 2026: "the state medians for spending per student. so we could
technically produce the 'target budget' lunenburg would have to have to reach that median
spending amount" -- and then the sharper version: "To match Leominster or Monty Tech, our
budget would have to be X."

IT IS A COMPARISON REPORT, AND THAT IS THE FRAME. TJ, 20 September 2026: "I think this
report should be a 'compare to other towns' report, for that median -> budget math."
Right -- the rank is what a reader wants first, and the multiplication is what makes the
rank mean something.

DISTRICTS, NOT TOWNS, AND THE DISTINCTION IS NOT PEDANTRY. Half this table is not a town:
Montachusett is a regional vocational district drawing from many towns, and Sizer and
Francis W. Parker are charters. A resident comparing Lunenburg to "other towns" and
finding Monty Tech at the top would be comparing a K-12 district to a vocational school
that most of its pupils travel to. The page says districts throughout.

WHY THIS IS A REPORT AND NOT A LINE ON AN EXISTING PAGE. `per-pupil-spending.md` already
establishes where Lunenburg sits: below the statewide first quartile in 17 of 17 years,
310th of 318 in FY2025. That is a RANK, and a rank does not tell a resident what it would
cost to move. This turns the same published figures into the one number a Town Meeting
argument actually needs -- what the bill would be.

EVERY FIGURE IS DERIVED. Rule 2. The medians and quartiles are DESE's own, the district
figures are DESE's own, and the multiplication is the only thing this file adds.

--------------------------------------------------------------------------------------
THE ONE THING THAT MAKES THIS EASY TO MISREAD
--------------------------------------------------------------------------------------

DESE's per-pupil expenditure is ALL FUNDS. Lunenburg's $30.0M on this basis is not the
$26.3M Town Meeting votes -- it is the general fund PLUS grants and revolving funds, and
the archive can now say how much each is, because
`dese_function_expenditure` carries the split and it reconciles.

So a target computed here is a target for TOTAL SPENDING, not for the appropriation.
Rule 11: a budget line is what the town must raise after everything else paying for the
thing is subtracted, and a third of the distance to the median could in principle be
closed by grants that nobody in Lunenburg votes on. Saying "the budget would have to be
$39M" without that sentence would be the same error this project has documented three
times already, in the direction that flatters the argument.
"""
import argparse
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'spending-compared.md')
FY = 2025

usd = lambda x: '${:,.0f}'.format(x)


def q(db, sql, args=()):
    db.row_factory = sqlite3.Row
    return db.execute(sql, args).fetchall()


def local_burden(db):
    """What each town is REQUIRED to put in, per foundation pupil, and what the state
    sends alongside it.

    THIS IS THE METRIC THE REGIONALISATION ARGUMENT NEEDS and the spending table does not
    have. DESE's per-pupil expenditure is what a district SPENDS, whoever paid. This is
    what the town must RAISE. TJ, 20 September 2026: "the amount the district itself pays
    per pupil, and how."

    Two things it is not, and both matter:
      - It is the REQUIRED minimum, not what the town actually raises, which is higher.
      - The denominator is FOUNDATION enrolment, the formula's own count, not the total
        FTE pupils the spending table divides by. The two are not interchangeable.
    """
    db.row_factory = sqlite3.Row
    fy = db.execute('SELECT MAX(fy) FROM dese_ch70_formula').fetchone()[0]
    out, state = [], None
    for r in db.execute('SELECT district, required_local_contribution rlc, ch70_aid, '
                        'foundation_enrollment fe FROM dese_ch70_formula WHERE fy=?', (fy,)):
        if not r['fe'] or not r['rlc']:
            continue
        fe = float(r['fe'])
        row = dict(district=r['district'], local=float(r['rlc']) / fe,
                   aid=float(r['ch70_aid'] or 0) / fe)
        if r['district'] == 'STATE TOTAL':
            state = row
        else:
            out.append(row)
    out.sort(key=lambda x: x['local'])
    return fy, out, state


# Structure, ours, by name -- there is no field in the Chapter 70 files that says which
# districts are regional.
STRUCTURE = {
    'ASHBURNHAM WESTMINSTER': 'regional', 'NORTH MIDDLESEX': 'regional',
    'AYER SHIRLEY': 'regional', 'GROTON DUNSTABLE': 'regional',
    'LUNENBURG': 'single town', 'HARVARD': 'single town',
}


def gather():
    db = sqlite3.connect(DB)
    lun = q(db, "SELECT gen_fund, grants_revolving, total, per_pupil FROM "
                "dese_function_expenditure WHERE district LIKE 'Lunenburg%' AND fy=? "
                "AND func_code='TTPP'", (FY,))[0]
    state = q(db, "SELECT per_pupil_p25, per_pupil_median, per_pupil_p75, "
                  "lunenburg_rank_of_districts, districts FROM dese_function_statewide "
                  "WHERE fy=? AND func_code='TTPP'", (FY,))[0]
    peers = q(db, "SELECT district, CAST(value AS REAL) v FROM dese_radar WHERE "
                  "measure='Total Expenditures' AND \"group\"='Expenditures Per Pupil' "
                  "AND fy=? AND district NOT LIKE 'Lunenburg%' ORDER BY v DESC", (FY,))
    # The denominator is stated rather than assumed: total / per-pupil is the pupil count
    # DESE actually divided by, and it matches Total FTE Pupils in the radar file.
    pupils = lun['total'] / lun['per_pupil']
    ch70_fy, burden, ch70_state = local_burden(db)
    return dict(lun=lun, state=state, peers=peers, pupils=pupils,
                ch70_fy=ch70_fy, burden=burden, ch70_state=ch70_state)


# WHICH OF THESE ARE REGIONAL, and this classification is OURS -- read off each
# district's name and structure, not off a field in a DESE file. Labelled as ours on the
# page for that reason. "Regionalize and we'll get more money" is one of the loudest
# arguments in town, and it deserves an answer built on something checkable.
REGIONAL = {
    'Montachusett Regional Vocational Technical': 'regional vocational, many towns',
    'Groton-Dunstable': 'regional, two towns',
    'North Middlesex': 'regional, three towns',
    'Ayer Shirley School District': 'regional, two towns \u2014 regionalised FY2012',
    'Ashburnham-Westminster': 'regional, two towns',
}


def render(d):
    lun, st, pupils = d['lun'], d['state'], d['pupils']
    med_need = st['per_pupil_median'] * pupils
    p25_need = st['per_pupil_p25'] * pupils
    b = []
    w = b.append
    w('# How Lunenburg compares, and what matching would cost\n')
    w('> **Working state:** `notes/HANDOFF.md` carries the current branch and what is\n'
      '> established versus assumed. `CLAUDE.md` carries the rules.\n')
    w('**Where Lunenburg sits among all %s Massachusetts school districts on spending '
      'for each pupil \u2014 and what it would cost, in dollars, to move.**\n'
      % st['districts'])
    w('Analysis, September 2026. Every figure is DESE\u2019s, for FY%d, and the only '
      'arithmetic here is a multiplication.\n' % FY)
    w('---\n')
    w('## The short version\n')
    # `lunenburg_rank_of_districts` already reads "310 of 318" -- appending `districts`
    # printed "310 of 318 of 318". The field is a sentence, not a numerator.
    w('Lunenburg spent **%s** for each pupil in FY%d, against a statewide median of '
      '**%s** \u2014 **%s districts**.\n'
      % (usd(lun['per_pupil']), FY, usd(st['per_pupil_median']),
         st['lunenburg_rank_of_districts']))
    w('**To reach the median, Lunenburg would have to spend %s. It spends %s. The '
      'difference is %s \u2014 %.0f%% more than it spends now.**\n'
      % (usd(med_need), usd(lun['total']), usd(med_need - lun['total']),
         (med_need / lun['total'] - 1) * 100))
    w('To reach merely the **first quartile** \u2014 the line below which a quarter of '
      'districts sit \u2014 would take %s, or %s more.\n'
      % (usd(p25_need), usd(p25_need - lun['total'])))
    w('---\n')
    w('## What the target is a target FOR\n')
    w('DESE\u2019s per-pupil figure is **all funds**, and that is not the number Town '
      'Meeting votes on. Of Lunenburg\u2019s %s:\n' % usd(lun['total']))
    w('| | FY%d | share |\n|---|---:|---:|' % FY)
    w('| General fund \u2014 what the town appropriates | %s | %.1f%% |'
      % (usd(lun['gen_fund']), lun['gen_fund'] / lun['total'] * 100))
    w('| Grants and revolving funds | %s | %.1f%% |'
      % (usd(lun['grants_revolving']), lun['grants_revolving'] / lun['total'] * 100))
    w('| **All funds** | **%s** | **100%%** |\n' % usd(lun['total']))
    w('So **%s is a target for total spending, not for the appropriation.** A district '
      'can close part of such a gap with grants nobody in town votes on, and %.1f%% of '
      'what Lunenburg already spends arrives that way. What share of the distance to the '
      'median a town could close without raising its own levy is not established here, '
      'and this project holds no document that settles it.\n'
      % (usd(med_need), lun['grants_revolving'] / lun['total'] * 100))
    w('---\n')
    w('## To match each district, one at a time\n')
    w('These are the districts this project holds comparable figures for, and the set '
      'is not arbitrary: most children educated outside Lunenburg Public Schools attend '
      'districts that spend **more** for each pupil than Lunenburg does \u2014 the '
      'detail is in `per-pupil-spending.md`. **They are districts and not towns.** '
      'Montachusett is a regional vocational district drawing from many towns; Sizer and '
      'Francis W. Parker are charters. Each row is what matching that district would '
      'cost at Lunenburg\u2019s own %s pupils.\n' % '{:,.1f}'.format(pupils))
    w('| to match | spends per pupil | Lunenburg would have to spend | more than now |')
    w('|---|---:|---:|---:|')
    for p in d['peers']:
        need = p['v'] * pupils
        if need < lun['total']:
            continue
        w('| %s | %s | %s | %s |'
          % (p['district'][:46], usd(p['v']), usd(need), '+' + usd(need - lun['total'])))
    w('| **Lunenburg now** | **%s** | **%s** | \u2014 |\n'
      % (usd(lun['per_pupil']), usd(lun['total'])))
    w('---\n')
    w('## \u201cRegionalise and we would get more money\u201d\n')
    w('It is one of the most common things said about this deficit, so it is worth '
      'setting out what these figures do and do not settle.\n')
    w('**Regional districts do not systematically spend more.** Five of the districts '
      'above are regional, and they span nearly the whole range \u2014 from the one that '
      'spends almost exactly what Lunenburg does to the one that spends most:\n')
    w('| district | structure | per pupil | against Lunenburg |\n|---|---|---:|---:|')
    for p in d['peers']:
        if p['district'] not in REGIONAL:
            continue
        w('| %s | %s | %s | %s |'
          % (p['district'][:44], REGIONAL[p['district']], usd(p['v']),
             '+' + usd(p['v'] - lun['per_pupil'])))
    w('| **Lunenburg** | single town, K\u201312 | **%s** | \u2014 |\n'
      % usd(lun['per_pupil']))
    w('Ashburnham-Westminster is regional and spends **%s** more for each pupil than '
      'Lunenburg. Being regional plainly does not decide the number.\n'
      % usd(next(p['v'] for p in d['peers']
                 if p['district'] == 'Ashburnham-Westminster') - lun['per_pupil']))
    w('**And the one local case cannot be measured here, which is worth saying plainly.** '
      'Ayer and Shirley regionalised for FY2012, next door and in living memory. This '
      'archive holds `Ayer` for FY2009\u2013FY2011 and `Ayer Shirley School District` '
      'from FY2012 \u2014 and nothing for Shirley on its own beforehand. So the figure '
      'before regionalisation is one town and the figure after is two, which is a '
      'different denominator rather than a change. Comparing them would produce a '
      'confident number about the wrong thing.\n')
    w('### What the town itself has to raise\n')
    w('Spending per pupil is what a district SPENDS, whoever paid for it. The argument is '
      'about what the TOWN pays, and Chapter 70 states that directly: the **required '
      'local contribution**, which is the minimum a town must put in, beside the aid the '
      'state sends. Per foundation pupil, FY%d:\n' % d['ch70_fy'])
    w('| district | structure | the town must raise | state sends |\n|---|---|---:|---:|')
    for r in d['burden']:
        mark = '**' if r['district'] == 'LUNENBURG' else ''
        w('| %s%s%s | %s | %s%s%s | %s |'
          % (mark, r['district'].title(), mark, STRUCTURE.get(r['district'], '?'),
             mark, usd(r['local']), mark, usd(r['aid'])))
    # NOT `st` -- that is the statewide per-pupil row bound at the top of render(), and
    # rebinding it here made the closing section read a key this row does not have.
    ch70_st = d['ch70_state']
    w('| *Every district in the state* | | *%s* | *%s* |\n'
      % (usd(ch70_st['local']), usd(ch70_st['aid'])))
    w('**The regional districts hold both ends of that table** \u2014 the lowest local '
      'burden for each pupil and the highest. Being regional does not decide it.\n')
    w('What decides it is in the formula\u2019s own inputs, which this archive holds: '
      '`equalized_valuation`, `property_local_effort` and `income_local_effort`. **The '
      'required contribution is computed from a town\u2019s property wealth and its '
      'residents\u2019 income.** Regionalising changes neither; it averages them with '
      'whichever town you join. Join a poorer one and the share for each pupil can fall, '
      'and the aid rise. Join a wealthier one and it goes the other way.\n')
    w('Two things that table is not. It is the **required minimum**, not what Lunenburg '
      'actually raises, which is higher. And its denominator is **foundation enrolment**, '
      'the formula\u2019s own count \u2014 not the FTE pupils the spending tables above '
      'divide by. The two are not interchangeable.\n')
    w('### Chapter 70 is not the only mechanism\n')
    w('It is the largest, and it is the one these figures cover. There is at least one '
      'more, and the town\u2019s own record names it. School Committee minutes of '
      '16 April 2025, reporting on a state bill:\n')
    w('> \u201cKey provisions to the bill were a full 100% reimbursement for FY25 '
      'regional transportation up from 82%, a 75% reimbursement increased from 44% for '
      'FY out of district special education transportation cost through circuit '
      'breaker\u201d\n')
    w('**Regional districts are reimbursed for transportation under c.71 \u00a716C and '
      'single-town districts are not.** At 82% rising to 100% that is not a rounding '
      'error, and it is money Lunenburg cannot receive in its present form.\n')
    w('**This archive holds no dollar figure for it, for any district.** So the honest '
      'position is: the largest term in the comparison \u2014 the required local '
      'contribution \u2014 is set by a town\u2019s wealth and not by its structure, and '
      'at least one further term exists that favours regional districts and cannot be '
      'sized from anything held here. Anyone claiming to know the net is claiming more '
      'than the record supports, in either direction. Registered in `money-gaps.csv`.\n')
    w('The decision itself is on the record too. A School Committee member, '
      '24 January 2024: \u201cLunenburg decided to not regionalize and to stay a small '
      'school, so scheduling in our middle high school is so hard and there isn\u2019t '
      'really a clear path to fix that.\u201d That is evidence about what was decided '
      'and why it still matters to people \u2014 not evidence about what it cost.\n')
    w('---\n')
    w('## What this does not show\n')
    w('- **That spending more would buy more.** This is a price, not a promise. Nothing '
      'here measures what any district gets for its money, and the two districts that '
      'spend least on this list are virtual schools, which are not comparable.\n')
    w('- **That the median is a target anybody has set.** No document says Lunenburg '
      'should spend the median. It is a position in a distribution, and it is used here '
      'because a rank of %s is not a quantity a resident can act on.\n'
      % st['lunenburg_rank_of_districts'])
    w('- **That this is the appropriation.** See above, and rule 11. The general fund is '
      '%.1f%% of it.\n' % (lun['gen_fund'] / lun['total'] * 100))
    w('- **Why Lunenburg spends less.** A figure is a fact; a reason is a hypothesis. '
      'This page measures the distance and does not explain it.\n')
    w('---\n')
    w('## Sources\n')
    w('| | |\n|---|---|')
    w('| Per-pupil expenditure, by district and function | '
      '`sources/state-dese/district-expenditures-by-function.xlsx`, via '
      '`dese_function_expenditure` \u2014 `reconciles: yes` |')
    w('| Statewide distribution, quartiles and rank | `dese_function_statewide`, '
      'func_code `TTPP` |')
    w('| The comparison districts | `dese_radar`, from '
      '`sources/state-dese/radar-district-comparison.xlsx` |')
    return '\n'.join(b) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out = render(gather())
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if out != cur:
            print('spending-compared.md is stale — run: '
                  'python3 scripts/build_spending_target.py', file=sys.stderr)
            return 1
        print('spending-compared.md is current')
        return 0
    open(OUT, 'w', encoding='utf-8').write(out)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
