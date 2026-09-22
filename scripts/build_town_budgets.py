#!/usr/bin/env python3
"""Budgets across town: what every department was voted, and which ones move the total.

    python3 scripts/build_town_budgets.py
    python3 scripts/build_town_budgets.py --check

Writes the cross-department report and one report per department, each as a markdown
document and a payload, rule 7d.

THE QUESTION THIS EXISTS TO ANSWER, in TJ's words: *"do ALL departments show deficits, or
just the schools, and why"* and *"what are the RATES for the other departments (and
compared to the schools)? ... Are they showing CUTS too?"*

The first has to be answered by refusing its premise, and the refusal is the most useful
thing on the page. **An omnibus budget cannot show a deficit.** It is what Town Meeting
voted, and a town may not vote an unbalanced budget, so every figure in it is the balanced
result AFTER the cuts. What it records is not who is short; it is who absorbed it.

The second it answers directly, and the answer surprised me: the schools are 57% of the
budget and are NOT the fastest-growing line in it. Ten of twelve departments grew faster
than the levy cap, and insurance and retirement -- one sixth the size of the schools --
moves the total more than the schools do. That is rule 4 exactly: rank by share times
excess rate, never by size and never by rate.

WHAT IS NOT HERE, and none of it is a detail.

A CUT IS A SERVICE REDUCTION, and this document cannot see one. TJ: *"'cuts' are service
reductions, which we have to find in ways other than budget information."* A department
can hold its dollars and cut its hours, and the dollars will not say so. Two routes exist
and both are registered as gaps: the personnel listing, which is read; and the activity
statistics in each department's own narrative -- calls for service, items circulated,
permits issued -- which are not.

WHAT WAS REQUESTED is not here either, and that is where a cut actually lives: the
difference between what a department asked for and what Town Meeting voted. The annual
report prints only the second.

AND THE DETAIL STOPS. FY2026 has no department table anywhere in the FY2025 report --
Article 10 is printed as prose -- so the last year in the series is a single total with
nothing beneath it.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import town_budget_data as D                                        # noqa: E402
import town_personnel_data as P                                     # noqa: E402
from conclusions import conclusion, emit, figure, usd, pct          # noqa: E402

ANALYSES = os.path.join(ROOT, 'sources', 'analyses')
PAYLOADS = os.path.join(ROOT, 'fy28', 'public', 'data')
MAIN = 'town-budgets'


def _sources(data):
    ys = data['detail_years']
    return [
        dict(what='The FY%d, FY%d and FY%d omnibus budgets, department by department'
                  % (ys[0], ys[1], ys[2]),
             where='The annual town reports for FY%d, FY%d and FY%d — each prints the '
                   'omnibus for the year AHEAD, as voted at that spring’s Town Meeting'
                   % (ys[0] - 1, ys[1] - 1, ys[2] - 1),
             basis='published',
             note='Every one of these reconciles against every total the table prints '
                  'about itself. FY%d and FY%d land on the town’s own +$0.80, recorded '
                  'as an attested reading rather than a defect in ours.' % (ys[0], ys[1])),
        dict(what='The voted total for every year from FY2012 to FY2025',
             where='The GRAND TOTAL each annual report prints at the foot of its omnibus',
             basis='published',
             note='A single printed figure per year. The department detail beneath it is '
                  'only reconciled for the last three.'),
        dict(what='The FY2026 total',
             where='Article 10 of the 3 May 2025 Annual Town Meeting, printed as prose on '
                   'page %d of the FY2025 annual report' % data['prose']['page'],
             basis='published',
             note='No department table is printed for FY2026 in any form. The five '
                  'funding sources the article names sum to the total exactly, which is '
                  'the only check available on it, and it passes.'),
    ]


def _not_established():
    return [
        'What any department ASKED for. The omnibus is what Town Meeting voted, which is '
        'already balanced — the difference between a request and a vote is where a cut '
        'lives, and the annual report prints only the second.',
        'What was actually spent. Voted and spent are different quantities and rule 1 '
        'forbids mixing them in one calculation.',
        'Whether any department reduced SERVICE. A department can hold its dollars and '
        'cut its hours, and a dollar figure will not say so.',
        'Why any line moved. The omnibus states an amount and gives no reason for it, so '
        'every explanation of a movement here would be a hypothesis.',
        'Anything about FY2026 below the total. The FY2025 annual report prints no '
        'department figures at all.',
        'That growing faster than the levy cap is a problem. Proposition 2½ limits the '
        'LEVY, not the budget: the budget is the levy plus state aid, local receipts and '
        'transfers, and new growth raises the levy limit on top of the 2.5%. The cap is '
        'used here as a common reference point every board in town already uses — it is '
        'not a ceiling anybody breached.',
    ]


def conclusions_for(data, rows):
    ys = data['detail_years']
    first, last = ys[0], ys[-1]
    tot_first = sum(data['groups'][first].values())
    tot_last = sum(data['groups'][last].values())
    above = [r for r in rows if r['rate'] is not None and r['rate'] > D.LEVY_CAP]
    measured = [r for r in rows if r['rate'] is not None]
    schools = next(r for r in rows if r['slug'] == 'schools')
    top = max((r for r in rows if r['pull'] is not None), key=lambda r: r['pull'])
    debt = next(r for r in rows if r['slug'] == 'maturing-debt')
    T = {y: sum(data['groups'][y].values()) for y in ys}
    sch = {y: data['groups'][y]['schools'] for y in ys}
    non = {y: T[y] - sch[y] for y in ys}
    nond = {y: non[y] - data['groups'][y]['maturing-debt'] for y in ys}
    r_sch = D.rate(sch[first], sch[last], last - first)
    r_non = D.rate(non[first], non[last], last - first)
    r_nond = D.rate(nond[first], nond[last], last - first)
    totals = data['totals']
    yrs = sorted(totals)
    steps = [(y, (totals[y] / totals[y - 1] - 1) * 100) for y in yrs[1:] if y - 1 in totals]
    biggest = max(steps, key=lambda s: s[1])

    big = max((r for r in rows if r['last']), key=lambda r: r['last'])
    small = min((r for r in rows if r['last']), key=lambda r: r['last'])
    ratio = big['last'] / small['last']
    four = sorted((r for r in rows if r['share']), key=lambda r: -r['share'])[:4]
    four_share = sum(r['share'] for r in four)
    out = []
    out.append(conclusion(
        id='who-gets-it',
        claim='More than half the town budget is the schools, and four departments are five sixths of it',
        lede='Before any question about growth: this is how one voted budget divides '
             'between the twelve departments that share it.',
        detail='%s takes %s of the FY%d voted budget. Adding Protection, employee '
               'benefits and debt service brings four departments to %s of the whole. The '
               'largest department is %s times the size of the smallest.'
               % (big['name'], pct(big['share']), last, pct(four_share),
                  format(int(round(ratio)), ',d')),
        figures={'share': figure(big['share'], pct(big['share']),
                                 'of the voted budget, the school line'),
                 'four': figure(four_share, pct(four_share),
                                'in the four largest departments'),
                 'ratio': figure(ratio, format(int(round(ratio)), ',d'),
                                 'times: the largest department against the smallest')},
        figure='share',
        kind='measured',
        bearing='sizes',
        basis='The twelve group totals the FY%d omnibus prints, as shares of the grand '
              'total on the same page.' % last,
        not_shown='What any department buys with it, or how many people it employs.',
        so_what='Most of what the town votes on is one department, and most of the rest is three.',
        allow=('FY%d' % last,),
    ))
    out.append(conclusion(
        id='not-one-department',
        claim='Ten of the twelve departments grew faster than the levy cap, not one of them',
        lede='Every department in the voted budget except Central Purchasing and debt '
             'service outgrew the 2.5% the levy may rise by.',
        detail='Across the three years the town publishes department detail for, %s grew '
               'faster than %s a year. Only Central Purchasing, which is nearly flat, and '
               'maturing debt, which falls as bonds are paid off, did not. The budget rose '
               '%s a year in total over the same period.'
               % ('%d of %d departments' % (len(above), len(measured)), pct(D.LEVY_CAP),
                  pct(D.rate(tot_first, tot_last, last - first))),
        figures={'above': figure(len(above), '%d of %d' % (len(above), len(measured)),
                                 'departments'),
                 'cap': figure(D.LEVY_CAP, pct(D.LEVY_CAP), 'a year'),
                 'total': figure(D.rate(tot_first, tot_last, last - first),
                                 pct(D.rate(tot_first, tot_last, last - first)), 'a year')},
        figure='above',
        kind='measured',
        bearing='sizes',
        basis='The twelve group totals each omnibus prints, FY%d against FY%d.'
              % (first, last),
        not_shown='Why any of them grew. An amount voted gives no reason for itself.',
        so_what='An argument about one department is an argument about part of the problem.',
        allow=(),
    ))
    out.append(conclusion(
        id='schools-are-not-the-fastest',
        claim='The schools are the biggest line in the budget and not the fastest growing one',
        lede='At %s of the budget the school line dominates the total, but eight '
             'departments grew faster than it did.' % pct(schools['share']),
        detail='The school appropriation grew %s a year across the three years, which is '
               'slower than eight of the eleven departments that grew at all. What grew '
               'fastest of the large lines is employee benefits and reserves — seven '
               'tenths of it group health insurance — at %s a year.'
               % (pct(schools['rate']), pct(top['rate'])),
        figures={'schools': figure(schools['rate'], pct(schools['rate']),
                                   'a year, the school line'),
                 'share': figure(schools['share'], pct(schools['share']),
                                 'of the voted budget'),
                 'top': figure(top['rate'], pct(top['rate']), 'a year')},
        figure='schools',
        kind='measured',
        bearing='sizes',
        basis='Total Schools against the other eleven group totals, FY%d to FY%d.'
              % (first, last),
        not_shown='What the school line buys, or whether it kept buying the same things.',
        so_what='Size and growth are different questions and the school line answers them differently.',
        allow=(),
    ))
    out.append(conclusion(
        id='pull-not-size',
        claim='Employee benefits move the total more than the schools do',
        lede='Weight times excess growth, not weight alone: a small line growing fast can '
             'push the total harder than a huge line growing slowly.',
        detail='Employee benefits and reserves are %s of the voted budget and grew %s a '
               'year, which is %s a year more than the levy cap would carry. The schools '
               'are %s of it and grew more slowly, at %s a year above the cap. The '
               'smaller line does more of the pushing, and seven tenths of it is group '
               'health insurance.'
               % (pct(top['share']), pct(top['rate']), usd(top['excess']),
                  pct(schools['share']), usd(schools['excess'])),
        figures={'tshare': figure(top['share'], pct(top['share'])),
                 'trate': figure(top['rate'], pct(top['rate']), 'a year'),
                 'tpull': figure(top['excess'], usd(top['excess']),
                                 'a year above the cap, from employee benefits'),
                 'sshare': figure(schools['share'], pct(schools['share'])),
                 'spull': figure(schools['excess'], usd(schools['excess']),
                                 'a year above the cap, from the schools')},
        figure='tpull',
        kind='measured',
        bearing='sizes',
        basis='Each group’s own FY%d figure times how far its growth exceeds the levy '
              'cap — dollars a year, not an index.' % last,
        not_shown='How much of the health insurance is school staff. The budget does not split it.',
        so_what='Ranking departments by size points at the wrong one to ask questions about.',
        allow=(),
    ))
    out.append(conclusion(
        id='debt-rolled-off',
        claim='Debt service fell by a third and the budget still grew — the room was absorbed',
        lede='Maturing debt and interest is the only line in the voted budget that falls, '
             'and it falls a long way.',
        detail='Debt service fell from %s to %s across the three years, freeing %s a year. '
               'The total still rose, so the room the roll-off created went to other '
               'lines rather than to the levy.'
               % (usd(debt['first']), usd(debt['last']), usd(-debt['change'])),
        figures={'was': figure(debt['first'], usd(debt['first'])),
                 'now': figure(debt['last'], usd(debt['last'])),
                 'freed': figure(-debt['change'], usd(-debt['change']),
                                 'a year freed by debt rolling off')},
        figure='freed',
        kind='measured',
        bearing='sizes',
        basis='Total Maturing Debt in the FY%d and FY%d omnibus budgets.' % (first, last),
        not_shown='Which lines the freed money went to. The budget does not trace it.',
        so_what='Debt coming off a budget is real room, and it is already spent here.',
        allow=(),
    ))
    out.append(conclusion(
        id='town-side-without-debt',
        claim='Take retiring debt out and the town side grew more than twice as fast as the schools',
        lede='The non-school budget looks restrained until you notice that most of its '
             'restraint is bonds being paid off rather than anything anybody decided.',
        detail='Everything except the schools grew %s a year — below the levy cap, and a '
               'figure that invites the conclusion the town side held the line. It did '
               'not: that average contains debt service falling as bonds retire. Debt is '
               'not a service. Excluding it, the rest of the town grew %s a year against '
               'the schools’ %s.'
               % (pct(r_non), pct(r_nond), pct(r_sch)),
        figures={'non': figure(r_non, pct(r_non), 'a year, everything but the schools'),
                 'nond': figure(r_nond, pct(r_nond),
                                'a year, once retiring debt is taken out'),
                 'sch': figure(r_sch, pct(r_sch), 'a year, the schools')},
        figure='nond',
        kind='measured',
        bearing='sizes',
        basis='The twelve group totals, FY%d against FY%d, aggregated three ways.'
              % (first, last),
        not_shown='Why the town side grew. This says where the money went, not what it '
                  'bought or whether anybody got more of anything.',
        so_what='An average that contains debt rolling off will understate every service in it.',
        allow=(),
    ))
    out.append(conclusion(
        id='detail-stopped',
        claim='The largest rise in fifteen years is also the first year with no detail published',
        lede='FY2026 is a single number. The table that would show which departments it '
             'went to is not printed anywhere in the report.',
        detail='The voted budget rose %s into FY%d, the largest one-year rise in the '
               'series that starts in FY2012. It is also the first year the annual report '
               'prints no department figures at all — Article 10 appears as prose, and '
               'the appropriations schedule that ran through FY2023 has stopped too.'
               % (pct(biggest[1]), biggest[0]),
        figures={'rise': figure(biggest[1], pct(biggest[1]),
                                'in one year, the largest since FY2012'),
                 'year': figure(biggest[0], 'FY%d' % biggest[0])},
        figure='rise',
        kind='measured',
        bearing='sizes',
        basis='The printed grand total of every omnibus, FY2012 to FY2025, and Article 10 '
              'of the 3 May 2025 Annual Town Meeting for FY2026.',
        not_shown='Which departments the rise went to. That is the figure that is missing.',
        so_what='The year worth explaining is the year the town stopped publishing the explanation.',
        allow=('FY2012', 'FY2023', 'Article 10'),
    ))
    return emit(MAIN, out)


def md_table(rows, ys):
    head = '| department | ' + ' | '.join('FY%d' % y for y in ys) + \
           ' | a year | share | above the cap |\n|---|' + '---:|' * (len(ys) + 3) + '\n'
    body = ''
    for r in rows:
        cells = [usd(r['series'][y]) if r['series'].get(y) else '—' for y in ys]
        body += '| %s | %s | %s | %s | %s |\n' % (
            r['name'], ' | '.join(cells),
            pct(r['rate']) if r['rate'] is not None else '—',
            pct(r['share']) if r['share'] is not None else '—',
(('+' if r['excess'] >= 0 else '\u2212') + usd(abs(r['excess'])) + '/yr') if r.get('excess') is not None else '—')
    return head + body


def render_main(data, rows):
    ys = data['detail_years']
    totals = data['totals']
    t = ['# Budgets across town\n',
         'What Town Meeting voted for every department, and which departments move the '
         'total.\n']
    above = [r for r in rows if r['rate'] is not None and r['rate'] > D.LEVY_CAP]
    measured = [r for r in rows if r['rate'] is not None]
    top = max((r for r in rows if r['pull'] is not None), key=lambda r: r['pull'])
    schools = next(r for r in rows if r['slug'] == 'schools')
    big = max((r for r in rows if r['last']), key=lambda r: r['last'])
    small = min((r for r in rows if r['last']), key=lambda r: r['last'])
    tot_last = sum(data['groups'][ys[-1]].values())
    # THE SIGNATURE IMAGE FIRST, AND IT IS NOT THE PIE. TJ: *"a conceptual image that
    # shows some stereotypical image that represents each department (a police car for
    # police, fire truck for fire, construction vehicle for DPW, etc) in size proportion
    # to the dollar amounts"*, and *"moving pie chart down below for data"*.
    #
    # Rule 7f's signature note: a reader remembers one image per page, and the one that
    # sticks is drawn in the units the subject is made of. Twenty-five schoolhouses beside
    # one wrench is the budget; a pie of the same numbers is correct and forgettable. The
    # pie keeps its job under the heading, beside the table, where a reader has come for
    # the split rather than for the impression.
    t.append('\n![The voted budget drawn as a town: schoolhouses, police cars, dump '
             'trucks, a town hall and a library, one icon for every $100,000, coloured by '
             'department.](charts/town-budgets-town.svg)\n')
    t.append('\n## Who gets the money\n')
    t.append('\n![A pie of the FY%d voted budget split twelve ways. %s is %s of it; the '
             'next three are %s at %s, %s at %s and %s at %s; five departments are under '
             'two per cent each.](charts/town-budgets-share.svg)\n'
             % (ys[-1], big['name'], pct(big['share']),
                *sum(([r['name'], pct(r['share'])] for r in
                      sorted((x for x in rows if x['share']),
                             key=lambda x: -x['share'])[1:4]), [])))
    t.append('\n| department | FY%d | share of the budget |\n|---|---:|---:|\n' % ys[-1])
    for r in sorted((x for x in rows if x['last']), key=lambda x: -x['last']):
        # LINKED, because a reader who wants to know what `Maturing Debt & Interest` IS
        # should not have to find its page. TJ: *"I want the departments in the first table
        # to be clickable to go to their page, that describes what each dept is."*
        t.append('| [%s](/analysis/town-budget-%s) | %s | %s |\n'
                 % (r['name'], r['slug'], usd(r['last']), pct(r['share'])))
    t.append('| **all twelve** | **%s** | **100%%** |\n' % usd(tot_last))
    t.append('\n%s is the largest department and %s the smallest — %s times the size, in '
             'the same budget.\n'
             % (big['name'], small['name'],
                format(int(round(big['last'] / small['last'])), ',d')))
    t.append('\n## How each department is growing\n')
    t.append('\n![Twelve small panels, one per department, each showing its voted budget '
             'across FY%d, FY%d and FY%d on its own vertical scale. Eleven rise; only '
             'Maturing Debt & Interest falls.](charts/town-budgets-trends.svg)\n'
             % (ys[0], ys[1], ys[2]))
    t.append('\n![Twelve lines on one dollar axis across three years. The school line '
             'runs far above the rest; ten departments are crowded near the floor.]'
             '(charts/town-budgets-all.svg)\n')
    t.append('\n![Horizontal bars, one per department, of compound annual growth, with a '
             'dashed line at the %s the levy may rise by. Ten of the twelve bars extend '
             'past it.](charts/town-budgets-rates.svg)\n' % pct(D.LEVY_CAP))
    t.append('\n## Which departments outgrow the levy cap\n')
    t.append('\n![Diverging bars, one per department, ranked by how much of the budget’s '
             'growth each accounts for. %s runs furthest right at %+.2f, ahead of Schools '
             'at %+.2f; Maturing Debt & Interest is the only bar on the left, at %+.2f.]'
             '(charts/town-budgets-pull.svg)\n'
             % (top['name'], top['pull'], schools['pull'],
                next(r for r in rows if r['slug'] == 'maturing-debt')['pull']))
    t.append('\n## Every department, every measure\n')
    t.append('\n%s\n' % md_table(rows, ys))
    t.append('\n**above the cap** is the department’s own money times how far its growth '
             'exceeds the %s the levy may rise by — dollars a year, and the ranking this '
             'page uses, because neither size nor rate means anything alone. The twelve '
             'net to %s a year.\n'
             % (pct(D.LEVY_CAP), usd(sum(r['excess'] or 0 for r in rows))))
    yrs = sorted(totals)
    t.append('\n## The voted total, FY%d to FY%d\n' % (yrs[0], yrs[-1]))
    t.append('\n![One column per fiscal year from FY%d to FY%d, rising from %s to %s. '
             'The last column is drawn in amber because FY%d is a total with no department '
             'table printed behind it.](charts/town-budgets-total.svg)\n'
             % (yrs[0], yrs[-1], usd(totals[yrs[0]]), usd(totals[yrs[-1]]), yrs[-1]))
    t.append('\n| fiscal year | voted | change |\n'
             '|---|---:|---:|\n')
    prev = None
    for y in sorted(totals):
        ch = '%+.1f%%' % ((totals[y] / prev - 1) * 100) if prev else '—'
        t.append('| FY%d | %s | %s |\n' % (y, usd(totals[y]), ch))
        prev = totals[y]
    t.append('\n## Does it add up\n\nThe twelve group totals against the grand total the '
             'same page prints.\n\n| fiscal year | twelve groups | printed total | '
             'difference |\n|---|---:|---:|---:|\n')
    for y in ys:
        rc = data['reconcile'][y]
        t.append('| FY%d | %s | %s | %s |\n'
                 % (y, usd(rc['groups']), usd(rc['printed']),
                    ('%+.2f' % rc['difference']) if rc['difference'] else 'nil'))
    t.append('\nFY%d is thirty cents short and the thirty cents are the town’s: it prints '
             '`Total Health & Sanitation` at $99,259.60 over five lines that come to '
             '$99,259.90, and foots its grand total on the correct figure rather than on '
             'the subtotal it printed.\n' % ys[0])
    t.append('\n## What this cannot show\n\n')
    for n in _not_established():
        t.append('- %s\n' % n)
    t.append('\n## Where it comes from\n\n')
    for s in _sources(data):
        t.append('- **%s** — %s. %s\n' % (s['what'], s['where'], s['note']))
    return ''.join(t)


def payload_main(data, rows):
    ys = data['detail_years']
    above = [r for r in rows if r['rate'] is not None and r['rate'] > D.LEVY_CAP]
    measured = [r for r in rows if r['rate'] is not None]
    tot_last = sum(data['groups'][ys[-1]].values())
    big = max((r for r in rows if r['last']), key=lambda r: r['last'])
    small = min((r for r in rows if r['last']), key=lambda r: r['last'])
    import build_town_budgets_charts as C
    import pictograms as G
    return dict(
        # THE GLYPHS TRAVEL WITH THE DATA, so the printed SVG in the markdown and the
        # interactive chart on the page cannot disagree about what a fire truck is.
        pictogram=dict(unit=1000000, unit_label='dollars',
                       glyphs={slug: G.GLYPHS[name]
                               for slug, name in C.GROUP_GLYPH.items()}),
        biggest=big, smallest=small, voted_total=tot_last,
        generated_by='scripts/build_town_budgets.py',
        about='What Town Meeting voted for every town department, and which departments '
              'move the total.',
        grain='DOLLARS VOTED at Town Meeting, in the omnibus budget for the year ahead. '
              'Not what any department requested, not what it spent, and not a service '
              'level. A voted budget is already balanced, so it records who absorbed the '
              'pressure rather than who is short.',
        stats=[
            dict(value=pct(big['share']),
                 label='of the voted budget goes to %s, the largest department'
                       % big['name']),
            dict(value='%d of %d' % (len(above), len(measured)),
                 label='departments growing faster than the %s the levy may rise by'
                       % pct(D.LEVY_CAP)),
            dict(value=usd(data['totals'][max(data['totals'])]),
                 tone='var(--series-cost)',
                 label='voted for FY%d — a total with no department detail published'
                       % max(data['totals'])),
        ],
        levy_cap=D.LEVY_CAP,
        departments=rows,
        totals=[dict(fy=y, voted=data['totals'][y], status=data['status'].get(y, ''))
                for y in sorted(data['totals'])],
        detail_years=ys,
        prose=data['prose'],
        reconcile=data['reconcile'],
        sources=_sources(data),
        not_established=_not_established(),
        conclusions=conclusions_for(data, rows),
    )



def _key(label):
    """A line's identity across years: its printed label, normalised.

    NOT its line number. The schedule renumbers -- FY2023 runs to 82 and FY2025 to 81, and
    a line inserted as `35A` shifts nothing while a line removed shifts everything after
    it. The label is what stays: `Snow Removal Expense` is the same line in all three
    years and `70` is not.

    Matching is therefore only as good as OCR's reading of the label, and where a label is
    damaged the line simply does not join and is shown per year instead of as a movement.
    That is the safe direction to fail in: a line that does not join is reported as not
    joined, where a wrongly joined pair would be published as a change that never happened.
    """
    t = re.sub(r'[^a-z0-9 ]+', ' ', (label or '').lower())
    return re.sub(r'\s+', ' ', t).strip()


def movers(data, slug):
    """The lines of one department that joined across all three years, biggest move first."""
    lines = D.department_lines(data, slug)
    ys = data['detail_years']
    first, last = ys[0], ys[-1]
    by = {}
    for y in ys:
        for r in lines[y]:
            if r['amount'] is None:
                continue
            by.setdefault(_key(r['label']), {})[y] = r
    out = []
    for k, per in by.items():
        if first not in per or last not in per:
            continue
        a, b = per[first]['amount'], per[last]['amount']
        out.append(dict(label=per[last]['label'], key=k, first=a, last=b, change=b - a,
                        series={y: (per[y]['amount'] if y in per else None) for y in ys}))
    out.sort(key=lambda r: -abs(r['change']))
    return lines, out


def conclusions_for_dept(data, row, moves):
    ys = data['detail_years']
    first, last = ys[0], ys[-1]
    if not moves or row['change'] is None:
        return []
    top = moves[0]
    if abs(top['change']) < 1000:
        return []
    share_of = (abs(top['change']) / abs(row['change']) * 100) if row['change'] else None
    label = re.sub(r'[0-9]+', '', top['label']).strip(' -.')
    rising = row['change'] > 0
    claim = ('%s is the line that moved most inside %s'
             % (label, row['name']))[:95]
    detail = ('%s went from %s to %s between FY%d and FY%d, a move of %s. The department '
              'as a whole moved %s over the same period.'
              % (label, usd(top['first']), usd(top['last']), first, last,
                 usd(top['change']), usd(row['change'])))
    figs = {'moved': figure(abs(top['change']), usd(abs(top['change'])),
                            'the largest move of any line in %s' % row['name']),
            'was': figure(top['first'], usd(top['first'])),
            'now': figure(top['last'], usd(top['last'])),
            'dept': figure(row['change'], usd(row['change']),
                           'the department’s own move')}
    so_what = ('Most of what this department did is one line, not the department.'
               if share_of and share_of >= 60 else
               'The department’s change is spread across its lines rather than sitting in one.')
    return emit('town-budget-' + row['slug'], [conclusion(
        id='largest-move',
        claim=claim,
        lede='The lines a department is made of move at different speeds, and one usually '
             'carries the department.',
        detail=detail,
        figures=figs,
        figure='moved',
        kind='measured',
        bearing='sizes',
        basis='The department’s own printed lines in the FY%d and FY%d omnibus budgets, '
              'joined on the printed label.' % (first, last),
        not_shown='Why it moved, or whether the service behind it changed.',
        so_what=so_what,
        allow=('FY%d' % first, 'FY%d' % last),
    )])


def render_dept(data, row, lines, moves):
    ys = data['detail_years']
    t = ['# %s: what the town votes for it\n' % row['name'],
         '\nOne of twelve departments in the omnibus budget Town Meeting votes each '
         'spring. [All twelve together](/analysis/town-budgets).\n']
    gloss = D.WHAT_IT_IS.get(row['slug'])
    if gloss:
        t.append('\n## What it is\n\n%s\n' % gloss)
    t.append('\n## The department\n\n| | %s |\n|---|%s\n'
             % (' | '.join('FY%d' % y for y in ys), '---:|' * len(ys)))
    t.append('| voted | %s |\n' % ' | '.join(
        usd(row['series'][y]) if row['series'].get(y) else '—' for y in ys))
    if row['rate'] is not None:
        pad = ' | ' * (len(ys) - 1)
        t.append('| a year | %s%s |\n| share of the budget | %s%s |\n'
                 '| pull on total growth | %s%s |\n'
                 % (pct(row['rate']), pad, pct(row['share']), pad,
                    '%+.2f' % (row['pull'] + 0.0), pad))
    t.append('\n## Its lines, as printed\n')
    for y in ys:
        t.append('\n### FY%d\n\n| line | label | voted |\n|---|---|---:|\n' % y)
        for r in lines[y]:
            t.append('| %s | %s | %s |\n'
                     % (r['line_no'] or '', r['label'],
                        usd(r['amount']) if r['amount'] is not None else '—'))
        got = sum(r['amount'] or 0 for r in lines[y])
        t.append('| | **total** | **%s** |\n' % usd(got))
        printed = row['series'].get(y)
        if printed is not None:
            d = round(got - printed, 2)
            t.append('\nThe page prints **%s** for this department. %s\n'
                     % (usd(printed),
                        'The lines above come to the same.' if not d
                        else 'The lines above come to %s, a difference of %+.2f.'
                             % (usd(got), d)))
    # THE PEOPLE, BESIDE THE MONEY, on the department page rather than the aggregate one.
    # TJ: *"town-personnel is super focusd on the fire department ... I would expect some
    # of this fire-department focused charts on the fire deparmtnet page directly, not this
    # aggregate page."* Right: a cross-town lens filled up with the one department that
    # states its strength in a plottable form, which is a page organised around what is
    # easy to draw rather than what the reader came for.
    if row['slug'] == 'protection':
        fire = P.load().get('fire') or []
        if fire:
            a, b = fire[0], fire[-1]
            t.append('\n## The people behind the money: the Fire Department\n\nThe Fire '
                     'Department is the only part of this group that states its own '
                     'strength, in the prose of its annual report, the same way every '
                     'year.\n')
            t.append('\n![The Fire Department’s career firefighters as a rising line '
                     'against the on-call roll drawn as a band, because the town states it '
                     'as a range. The two move in opposite directions.]'
                     '(charts/town-personnel-fire.svg)\n')
            t.append('\n| fiscal year | career | on call |\n|---|---:|---:|\n')
            for r in fire:
                t.append('| FY%s | %s | %s–%s |\n'
                         % (r['fy'], r['career'], r['on_call_low'], r['on_call_high']))
            t.append('\nCareer firefighters went from %s to %s while the on-call roll fell '
                     'from %s–%s to %s–%s: the department grew and shrank at once, in '
                     'different kinds of staff. Police states no strength at all, so the '
                     'other half of this budget group has no published headcount to set '
                     'beside its money.\n'
                     % (a['career'], b['career'], a['on_call_low'], a['on_call_high'],
                        b['on_call_low'], b['on_call_high']))

    if row['slug'] == 'maturing-debt' and moves:
        prin = next((m for m in moves if m['label'].lower().startswith('principal')), None)
        intr = next((m for m in moves if 'interest' in m['label'].lower()
                     and 'temporary' not in m['label'].lower()), None)
        if prin:
            t.append('\n## Why it is falling\n\nDebt service drops when bonds finish and '
                     'the town has not issued new ones to replace them. Almost all of the '
                     'fall here is PRINCIPAL — the capital being repaid — rather than '
                     'interest:\n\n| | FY%d | FY%d | change |\n|---|---:|---:|---:|\n'
                     % (ys[0], ys[-1]))
            for m in (prin, intr):
                if m:
                    t.append('| %s | %s | %s | %s%s |\n'
                             % (m['label'], usd(m['first']), usd(m['last']),
                                '+' if m['change'] >= 0 else '\u2212',
                                usd(abs(m['change']))))
            t.append('\nWhat this does NOT say is WHICH bonds finished. That is in the '
                     'town’s debt repayment schedule, which the annual report prints and '
                     'this project has not yet read properly — the FY2025 extract of it is '
                     'the trust-fund table by mistake.\n')
    if moves:
        t.append('\n## What moved\n\nLines that appear in FY%d and FY%d under the same '
                 'printed label, biggest move first.\n\n| line | FY%d | FY%d | change |\n'
                 '|---|---:|---:|---:|\n' % (ys[0], ys[-1], ys[0], ys[-1]))
        for m in moves[:12]:
            t.append('| %s | %s | %s | %s |\n'
                     % (m['label'], usd(m['first']), usd(m['last']),
                        ('%s%s' % ('+' if m['change'] >= 0 else '-',
                                   usd(abs(m['change'])))) ))
    t.append('\n## What this cannot show\n\n')
    for n in _not_established():
        t.append('- %s\n' % n)
    return ''.join(t)


def payload_dept(data, row, lines, moves):
    ys = data['detail_years']
    stats = [dict(value=usd(row['series'][ys[-1]]) if row['series'].get(ys[-1]) else '—',
                  label='voted for %s in FY%d' % (row['name'], ys[-1]))]
    if row['rate'] is not None:
        stats.append(dict(value=pct(row['rate']),
                          tone=('var(--series-cost)' if row['rate'] > D.LEVY_CAP else None),
                          label='a year, against the %s the levy may rise by'
                                % pct(D.LEVY_CAP)))
        stats.append(dict(value='%+.2f' % (row['pull'] + 0.0),
                          label='points of the whole budget’s growth it accounts for'))
    return dict(
        generated_by='scripts/build_town_budgets.py',
        about='What Town Meeting voted for %s, line by line.' % row['name'],
        grain='DOLLARS VOTED at Town Meeting for the year ahead — not requested, not '
              'spent, and not a service level.',
        stats=[s for s in stats if s.get('value')],
        department=row, lines={str(y): lines[y] for y in ys}, movers=moves,
        detail_years=ys,
        sources=_sources(data),
        not_established=_not_established(),
        conclusions=conclusions_for_dept(data, row, moves),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = D.load()
    rows = D.table(data)
    files = {os.path.join(ANALYSES, MAIN + '.md'): render_main(data, rows),
             os.path.join(PAYLOADS, MAIN + '.json'):
                 json.dumps(payload_main(data, rows), indent=1, ensure_ascii=False,
                            sort_keys=True) + '\n'}
    for row in rows:
        lines, moves = movers(data, row['slug'])
        slug = 'town-budget-' + row['slug']
        files[os.path.join(ANALYSES, slug + '.md')] = render_dept(data, row, lines, moves)
        files[os.path.join(PAYLOADS, slug + '.json')] = json.dumps(
            payload_dept(data, row, lines, moves), indent=1, ensure_ascii=False,
            sort_keys=True) + '\n'
    if a.check:
        stale = [os.path.basename(p) for p, want in files.items()
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else '') != want]
        if stale:
            print('STALE %s' % ', '.join(sorted(stale)), file=sys.stderr)
            return 1
        print('%s is current' % MAIN)
        return 0
    for p, want in files.items():
        open(p, 'w', encoding='utf-8').write(want)
    print('wrote %d file(s) for %s' % (len(files), MAIN))
    return 0


if __name__ == '__main__':
    sys.exit(main())
