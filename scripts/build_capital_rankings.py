#!/usr/bin/env python3
"""CAPITAL PLANNING RANKINGS: the hub (the five years side by side) and one page per fiscal year
-- what each department asked for, every ranking the year's documents print, in rank order, and
what was funded.

    python3.11 scripts/build_capital_rankings.py           # write the six payloads
    python3.11 scripts/build_capital_rankings.py --check   # fail if any would change

TJ, 20 November 2026: *"i want to clik into a FY and see what was asked for by department, then
what was prioritized, in rank order. with data to show breakdowns and percents by department of
who got prioritized"*.

Every figure is sources/data/capital-rankings.csv (scripts/extract_capital_rankings.py), which
quotes each rank from its page or cell and checks each year against totals its documents print.
Two things on these pages are OURS and say so: the department grouping (read off the project
number; it reproduces every department total the documents print), and the count of funded
projects ranked below an unfunded one, which is arithmetic on the printed ranks.

"Funded" is what the outcome document says. A department's share of what was funded is a share
of DOLLARS. Nothing here says why any project was or was not funded: where a document gives a
reason (FY2024's two removals, FY2026's Option 2) the page quotes where it is, and nothing else.
"""
import argparse
import csv
import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402

DATA = os.path.join(ROOT, 'sources', 'data', 'capital-rankings.csv')
OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
HUB = 'capital-rankings'
YEARS = (2023, 2024, 2025, 2026, 2027)
DEPTS = ['Public Works', 'Facilities', 'Schools', 'Fire', 'Police', 'IT', 'General government']

DOC = {   # every document a page cites: label and the archive address
    'a75': ('Town Manager — FY2023 Capital Investment Plan presentation, 18 January 2022',
            'town-budget/docs/a75-fy23-capital-plan-presentation-pdf.pdf'),
    'a194': ('Capital Planning Committee — FY2024 composite project ranking',
             'town-budget/docs/a194-fy24-composite-project-ranking-by-capital-planning-committee-pdf.pdf'),
    'a195': ('Town Manager — FY2024 capital plan presentation',
             'town-budget/docs/a195-fy24-town-manager-capital-plan-presentation-pdf.pdf'),
    '1504': ('Town Manager — FY2025-FY2034 preliminary capital plan presentation',
             'town-budget/docs/1504-fy25-fy34-town-manager-preliminary-capital-plan-presentation.pdf'),
    'cpc25': ('Capital Planning Committee — FY2025 capital requests by department, final (workbook)',
              'budget-workbooks/finance-committee/fy25-budget/capital-planning-committee-files/'
              'fy25-capital-requests-by-department-final-cpc.xlsx'),
    'cpc24': ('Capital Planning Committee — FY2024 composite rankings, Rev. B (sent by its Chair, 20 November 2026)',
              'correspondence/2026-11-20-cpc-fy24-composite-rankings-rev-b.xlsx'),
    'cpc26': ('Capital Planning Committee — FY2026 final rankings, voted 16 December 2024 (sent by its Chair)',
              'correspondence/2026-11-20-cpc-fy26-final-rankings.xlsx'),
    'cpc27': ('Capital Planning Committee — FY2027 priorities list, each member’s rank (sent by its Chair)',
              'correspondence/2026-11-20-cpc-fy27-priorities-list-working-final.xlsx'),
    'plan27': ('FY2027 capital plan workbook, CPC rank and average',
               'budget-workbooks/finance-committee/fy27-budget/capital-planning/fy27-capital-plan.xlsx'),
    'pre27': ('Town Manager — preliminary FY2027 capital program, 1 February 2026',
              'budget-workbooks/finance-committee/fy27-budget/capital-planning/preliminary-capital-program-2.1.26.pdf'),
    'w26': ('Annual Town Meeting warrant, May 2026, Article 13',
            'town-budget/docs/3765-town-meeting-booklet-including-warrant.pdf'),
    'ar22': ('Town of Lunenburg — FY2022 annual town report (Article 6, May 2022)',
             'town-annual-reports/docs/4129-fy-2022-annual-town-report.pdf'),
    'ar23': ('Town of Lunenburg — FY2023 annual town report (Article 6, May 2023)',
             'town-annual-reports/docs/4131-fy-2023-annual-town-report.pdf'),
    'ar24': ('Town of Lunenburg — FY2024 annual town report (Article 6, May 2024)',
             'town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf'),
    'ar25': ('Town of Lunenburg — FY2025 annual town report (FY2026 options, May 2025)',
             'town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf'),
    'data': ('Lunenburg Budget Project — capital-rankings.csv, every row and its page or cell',
             None),
}
RANKS_FROM = {2023: ['a75'], 2024: ['a195', 'a194', 'cpc24'], 2025: ['cpc25', '1504'], 2026: ['cpc26', 'ar25'],
              2027: ['plan27', 'cpc27', 'pre27']}
OUTCOME_FROM = {2023: 'ar22', 2024: 'ar23', 2025: 'ar24', 2026: 'ar25', 2027: 'w26'}
SCHEMES = [('cpc_rank', 'cpc', 'Capital Planning Committee', False),
           ('tm_rank', 'tm', 'Town Manager', False),
           ('composite_average', 'avg', 'Members’ average rank', False),
           ('collins_score', 'collins', 'Collins Center score', True),
           ('dept_rank', 'dept', 'The department’s own order', False)]


def fail(msg):
    raise SystemExit('build_capital_rankings: ' + msg)


def load():
    if not os.path.exists(DATA):
        fail('%s is not built -- python3.11 scripts/extract_capital_rankings.py' % os.path.relpath(DATA, ROOT))
    rows = list(csv.DictReader(open(DATA, encoding='utf-8')))
    for r in rows:
        r['fy'] = int(r['fiscal_year'])
        r['amt'] = float(r['amount'])
        r['ok'] = r['funded'] == 'yes'
        r['cpc'] = int(r['cpc_rank']) if r['cpc_rank'] else None
    if {r['fy'] for r in rows} != set(YEARS):
        fail('the dataset holds years %s' % sorted({r['fy'] for r in rows}))
    return rows


def src(key):
    label, path = DOC[key]
    return dict(key=key, label=label, href='/docs/' + path if path else '/data/capital-rankings.csv')


def P(x):
    return figure(x, C.pct(x), 'percent')


def U(x):
    return figure(x, C.usd(x), 'dollars')


def N(n, unit):
    return figure(n, C.num(n), unit)


def F(y):
    return figure(y, C.fy(y), 'fiscal year')


def poss(name):
    return name + ('’' if name.endswith('s') else '’s')


def year_stats(rs):
    tot = sum(r['amt'] for r in rs)
    fun = sum(r['amt'] for r in rs if r['ok'])
    d = OrderedDict()
    for k in DEPTS:
        x = [r for r in rs if r['department'] == k]
        if x:
            d[k] = dict(n=len(x), amt=sum(r['amt'] for r in x), fn=sum(r['ok'] for r in x),
                        famt=sum(r['amt'] for r in x if r['ok']))
    for k, v in d.items():
        v['share_req'] = 100 * v['amt'] / tot
        v['share_fun'] = 100 * v['famt'] / fun if fun else 0
        v['own'] = 100 * v['famt'] / v['amt']
    ranked = [r for r in rs if r['cpc'] is not None]
    worst_unfunded = min((r['cpc'] for r in ranked if not r['ok']), default=None)
    below = sorted((r for r in ranked if r['ok'] and worst_unfunded is not None and r['cpc'] > worst_unfunded),
                   key=lambda r: r['cpc'])
    unranked_funded = [r for r in rs if r['ok'] and r['cpc'] is None]
    tm = [r for r in rs if r['tm_rank']]
    differ = [r for r in tm if int(r['tm_rank']) != r['cpc']]
    return dict(n=len(rs), tot=tot, fn=sum(r['ok'] for r in rs), fun=fun, share=100 * fun / tot, d=d,
                first_left=worst_unfunded, below=below, unranked_funded=unranked_funded, tm=tm, differ=differ)


def option_swap(rs):
    """FY2026: what Option 2 took out of Option 1 and put in. Returned only when every request
    moved is one department's and the two sides cost the same to the dollar -- a measurement,
    stated as one; the vote record gives no reason and neither does this."""
    out_ = [r for r in rs if r['tm_preliminary'] == 'yes' and not r['ok']]
    in_ = [r for r in rs if r['tm_preliminary'] == 'no' and r['ok']]
    depts = {r['department'] for r in out_ + in_}
    a, b = sum(r['amt'] for r in out_), sum(r['amt'] for r in in_)
    if len(depts) != 1 or len(in_) != 1 or round(a, 2) != round(b, 2):
        fail('FY2026: Option 2 no longer swaps like for like (%s out, %s in, %s) -- rewrite the conclusion'
             % (a, b, depts))
    return dict(n=len(out_), dept=depts.pop(), out=a, **{'in': b})


# ---------------------------------------------------------------------- the signature
def ladder_block(fy, rs):
    rs = sorted(rs, key=lambda r: (r['cpc'] is None, r['cpc'] or 0, r['project']))
    present = [(col, key, label, high) for col, key, label, high in SCHEMES if any(r[col] for r in rs)]
    depts = [k for k in DEPTS if any(r['department'] == k for r in rs)]
    figs, rows = set(), []
    for r in rs:
        at = C.usd(r['amt'])
        figs.add(at)
        ranks, texts = {}, {}
        for col, key, _, _ in present:
            if r[col]:
                ranks[key] = float(r[col])
                texts[key] = r[col]
                figs.add(r[col])
        rows.append(dict(project=r['project'], dept=depts.index(r['department']), amount=r['amt'],
                         amount_text=at, funded=r['ok'], ranks=ranks, rank_text=texts))
    data = dict(
        schemes=[dict(key=key, label=label, high_first=high) for _, key, label, high in present],
        depts=[dict(label=k) for k in depts], rows=rows,
        text=dict(funded='Funded', unfunded='Not funded', order='In the order of', unranked='not ranked',
                  rank='rank', score='score', line='The highest-ranked request left unfunded'),
        note=('One bar a request, as long as its cost; solid bars were funded. Department is our '
              'grouping of the project numbers the documents print.'))
    names = [r['project'] for r in rs]
    return TB.custom('capital-ladder', 'Every request, in rank order', data, place='lead',
                     figures=sorted(figs), allow=names,
                     alt='%s capital requests in the Capital Planning Committee’s order, each bar sized by its '
                         'cost and marked funded or not.' % C.fy(fy),
                     so=('Read down the list: where the solid bars stop is where the money ran out, '
                         'and any solid bar below that point was funded out of order.'))


# ---------------------------------------------------------------------- one year
# THE YEAR, COMPOSED FOR ITS SUBJECT (TJ, 20 November 2026, on the first build: "you followed the
# base template agai :(" ... "we need to cut that template"). A capital year is a PROCESS that
# narrows a list, so the page follows the list: its path from ranked to funded; the list itself in
# rank order with the funding line drawn; where two printed orders disagree; and who asked against
# who got. Each conclusion sits under the visual it explains, its facts beside it.

# The middle stage of each year's path: the Town Manager's first plan, named as the year's own
# document names it. `tm_preliminary` in the dataset says which requests were in it.
FIRST = {2023: ('In the Town Manager’s plan as presented', 'a75'),
         2024: ('In the Town Manager’s plan as presented', 'a195'),
         2025: ('In the Town Manager’s preliminary plan', '1504'),
         2026: ('Option 1, the first of the two options', 'ar25'),
         2027: ('In the Town Manager’s preliminary program', 'pre27')}
FINAL = {2023: 'Funded at Town Meeting', 2024: 'Funded at Town Meeting', 2025: 'Funded at Town Meeting',
         2026: 'Option 2, voted at Town Meeting',
         2027: 'In Article 13, which Town Meeting passed (known from the recording)'}
FAR = 3    # a move of this many places or more between two orders is drawn strong and named


def path_block(fy, rs, s):
    first_label, first_doc = FIRST[fy]
    pre = [r for r in rs if r['tm_preliminary'] == 'yes']
    added = [r for r in rs if r['ok'] and r['tm_preliminary'] != 'yes']
    dropped = [r for r in rs if not r['ok'] and r['tm_preliminary'] == 'yes']
    pamt = sum(r['amt'] for r in pre)
    figs = {C.num(len(rs)), C.usd(s['tot']), C.num(len(pre)), C.usd(pamt), C.num(s['fn']), C.usd(s['fun']),
            C.num(len(rs) - len(pre)), C.num(len(added)), C.num(len(dropped))}
    reqs = lambda n: '%s request%s' % (C.num(n), '' if n == 1 else 's')
    def said(n, where, verb):        # "1 request ranked here was not in it", "6 requests ... were"
        return '%s %s %s %s' % (reqs(n), where, 'was' if n == 1 else 'were', verb)
    left_out = len(rs) - len(pre)
    moves = [said(left_out, 'ranked here', 'not in it') if left_out else None,
             '; '.join(x for x in [said(len(added), 'it left out', 'added') if added else '',
                                   said(len(dropped), 'in it', 'not funded') if dropped else ''] if x) or None]
    docs = [DOC[k][0] for k in RANKS_FROM[fy][:1]] + [DOC[first_doc][0], DOC[OUTCOME_FROM[fy]][0]]
    data = dict(stages=[
        dict(label='Ranked by the Capital Planning Committee', doc=docs[0],
             count_text=reqs(len(rs)), amount_text=C.usd(s['tot']), amount=s['tot']),
        dict(label=first_label, doc=docs[1], count_text=reqs(len(pre)), amount_text=C.usd(pamt), amount=pamt),
        dict(label=FINAL[fy], doc=docs[2], count_text=reqs(s['fn']), amount_text=C.usd(s['fun']),
             amount=s['fun'], final=True)],
        moves=moves,
        note='Each bar is that stage’s dollars against the ranked total. Stage names are the year’s own '
             'documents’.')
    so = ('The final plan was larger than the Town Manager’s first one; the first draft was not the ceiling.'
          if s['fun'] > pamt + 0.5 else
          'What the Town Manager put in the first plan is what was funded, request for request.'
          if not added and not dropped else
          'The final plan swapped requests in and out of the first one at the same total.')
    blk = TB.custom('capital-path', 'From ranked to funded', data, place='lead', figures=sorted(figs),
                    allow=docs + [first_label, FINAL[fy]],
                    alt='%s: requests ranked, then in the first plan, then funded, each as a count and dollars.' % C.fy(fy),
                    so=so)
    return blk, dict(pre=len(pre), pamt=pamt, added=len(added), dropped=len(dropped))


def two_orders_block(fy, rs):
    """CPC rank against the Town Manager's, the years both are printed (FY2023-FY2025)."""
    tm = [r for r in rs if r['tm_rank'] and r['cpc'] is not None]
    if not tm:
        return None, None
    rows = [dict(project=r['project'], a=r['cpc'], b=int(r['tm_rank']), funded=r['ok']) for r in tm]
    moves = [abs(x['a'] - x['b']) for x in rows]
    n = max(max(x['a'] for x in rows), max(x['b'] for x in rows))
    data = dict(left='Committee rank', right='Town Manager rank', n=n, far=FAR, rows=rows,
                text=dict(funded='Funded', unfunded='Not funded'),
                note='A flat line is the two ranks agreeing; lines moving %s places or more are drawn strong. '
                     'Both ranks as the year’s presentation prints them.' % C.num(FAR))
    blk = TB.custom('capital-two-orders', 'Two orders of one list', data, place='body',
                    figures=[C.num(FAR)], allow=[r['project'] for r in tm],
                    alt='%s: each request’s Capital Planning Committee rank joined to its Town Manager rank.' % C.fy(fy),
                    so='Where the lines cross, the two printed orders disagree about what comes first.')
    return blk, dict(n=len(tm), differ=sum(1 for m in moves if m), far=sum(1 for m in moves if m >= FAR),
                     biggest=max(moves))


def bands_block(d, title, place, alt, note, so, allow=(), highlight=None):
    depts = sorted(d.items(), key=lambda kv: -kv[1]['amt'])
    data = dict(depts=[dict(label=k, req=v['share_req'], fun=v['share_fun'], req_text=C.pct(v['share_req']),
                            fun_text=C.pct(v['share_fun'])) for k, v in depts],
                text=dict(req='Requested', fun='Funded'), note=note, highlight=highlight)
    figs = [C.pct(v['share_req']) for _, v in depts] + [C.pct(v['share_fun']) for _, v in depts]
    return TB.custom('capital-share-bands', title, data, place=place, figures=figs, alt=alt, so=so,
                     allow=list(allow))


def year_page(fy, rs):
    s = year_stats(rs)
    pid = 'capital-fy%d' % fy
    d = s['d']
    lag = min(d, key=lambda k: d[k]['share_fun'] - d[k]['share_req'])
    f, con = LD.fact, TP.conclusion
    pblk, pth = path_block(fy, rs, s)
    oblk, two = two_orders_block(fy, rs)
    facts = [
        f('req', N(s['n'], 'requests'), 'ranked requests', 'published'),
        f('fn', N(s['fn'], 'projects'), 'funded', 'published'),
        f('pre', N(pth['pre'], 'requests'), 'in the first plan', 'published'),
        f('share', P(s['share']), 'of the requested dollars funded', 'published'),
        f('lagreq', P(d[lag]['share_req']), '%s share of the dollars requested' % poss(lag), 'published'),
        f('lagfun', P(d[lag]['share_fun']), '%s share of the dollars funded' % poss(lag), 'published'),
    ]
    cons, flow = [], []
    cite = TP.cite
    ranks, out = RANKS_FROM[fy], OUTCOME_FROM[fy]
    first_doc = FIRST[fy][1]

    # 1. the path
    cons.append(con('%s of %s requests were funded, %s of the dollars; the first plan held %s.'
                    % (C.num(s['fn']), C.num(s['n']), C.pct(s['share']), C.num(pth['pre'])),
                    ['fn', 'req', 'share', 'pre'],
                    {'a': N(s['fn'], 'projects'), 'b': N(s['n'], 'requests'), 'c': P(s['share']),
                     'd': N(pth['pre'], 'requests')},
                    so='The rest was not cancelled by this vote; the road-back grid on the hub shows '
                       'which requests came back.'))
    flow += [cite(pblk, *list(OrderedDict.fromkeys(ranks[:1] + [first_doc, out]))), ('conclusion', 0)]

    # 2. the list in rank order, the funding line drawn
    lb = ladder_block(fy, rs)
    swap = option_swap(rs) if fy == 2026 else None
    if swap:
        facts.append(f('swap', U(swap['out']), 'of %s requests Option 2 dropped' % swap['dept'], 'published',
                       allow=('Option 2',)))
        cons.append(con('Option 2 dropped %s %s requests costing %s and added one unranked project costing %s.'
                        % (C.num(swap['n']), swap['dept'], C.usd(swap['out']), C.usd(swap['in'])), ['swap'],
                        {'n': N(swap['n'], 'requests'), 'a': U(swap['out']), 'b': U(swap['in'])},
                        allow=('Option 2',),
                        so='The Schools dollars in the plan did not change, what they bought did; the '
                           'report records the vote, not the reason.'))
    elif s['below']:
        facts.append(f('below', N(len(s['below']), 'projects'), 'funded below the first unfunded rank (ours)',
                       'estimate'))
        cons.append(con('%s funded projects sat below rank %s, the highest-ranked request left unfunded.'
                        % (C.num(len(s['below'])), s['first_left']), ['below'],
                        {'a': N(len(s['below']), 'projects'), 'r': figure(s['first_left'], str(s['first_left']), 'rank')},
                        so='Funding did not stop at one line in the committee’s order; the outcome '
                           'document records the vote, not the reason.'))
    else:
        cons.append(con('Every funded project ranked above every unfunded one in the committee’s order.',
                        ['fn'], so='Here the funding line is one clean cut across the committee’s list.'))
    flow += [cite(lb, *ranks, out), ('conclusion', len(cons) - 1)]

    # 3. two orders, where both are printed
    if oblk:
        facts.append(f('differ', figure(two['differ'], '%d of %d' % (two['differ'], two['n']), 'requests'),
                       'requests the two ranks place differently', 'published'))
        facts.append(f('biggest', N(two['biggest'], 'places'), 'the largest move between the two', 'published'))
        cons.append(con('The Town Manager’s rank differed from the committee’s on %s of %s requests, by up to %s places.'
                        % (C.num(two['differ']), C.num(two['n']), C.num(two['biggest'])), ['differ', 'biggest'],
                        {'a': N(two['differ'], 'requests'), 'b': N(two['n'], 'requests'), 'c': N(two['biggest'], 'places')},
                        so='Two printed orders exist for this year; neither alone says what comes first.'))
        flow += [cite(oblk, ranks[0]), ('conclusion', len(cons) - 1)]

    # 4. who asked, who got
    bb = bands_block(d, 'Who asked, who got', 'body',
                     '%s: each department’s share of the dollars requested, joined to its share of the dollars funded.' % C.fy(fy),
                     'Shares of dollars. Department is our grouping of the printed project numbers; it matches every '
                     'department total the year’s documents print.',
                     'A band that narrows was a smaller share of what was funded than of what was requested.',
                     highlight=lag)
    cons.append(con('%s requested %s of the dollars and received %s of what was funded.'
                    % (lag, C.pct(d[lag]['share_req']), C.pct(d[lag]['share_fun'])),
                    ['lagreq', 'lagfun'], {'a': P(d[lag]['share_req']), 'b': P(d[lag]['share_fun'])},
                    so='A share of dollars, not of projects: one large request moves it more than '
                       'several small ones.'))
    flow += [cite(bb, out, 'data'), ('conclusion', len(cons) - 1)]

    # 5. what is not held (rule 7c; each is a row in money-gaps.csv)
    gaps = []
    if fy in (2023, 2024, 2026, 2027):
        gaps.append(('Each department’s own order of its requests. Closes: each department’s %s priority list, '
                     'requested by records request on 20 November 2026.' % C.fy(fy), None,
                     (C.fy(fy), '20 November 2026')))
    if fy == 2027:
        gaps.append(('The Town Clerk’s written record of the Article 13 vote. The vote is known from the meeting '
                     'recording only.', None, ('Article 13',)))
    flow.append('related')

    # ---- the raw: every request and every rank; each department's shares
    trow = []
    for k, v in sorted(d.items(), key=lambda kv: -kv[1]['amt']):
        trow.append(dict(label=k, cells=['%d of %d' % (v['fn'], v['n']), C.usd(v['amt']), C.pct(v['share_req']),
                                          C.usd(v['famt']), C.pct(v['share_fun']), C.pct(v['own'])]))
    shares = dict(caption='Each department’s share', views=[dict(
        key='shares', label='By department', kinds=['published'] * 6,
        columns=['Funded of requested', 'Requested', 'Share of requests', 'Funded', 'Share of funded',
                 'Its own dollars funded'],
        rows=trow, note='Shares of dollars. Requested means every request the committee’s list holds.')])
    present = [(col, label) for col, _, label, _ in SCHEMES if any(r[col] for r in rs)]
    cols = ['Department', 'Cost'] + [l for _, l in present] + ['Funded']

    def trows(sub):
        return [dict(label=r['project'], cells=[r['department'], C.usd(r['amt'])] + [r[c] or '—' for c, _ in present]
                     + ['yes' if r['ok'] else 'no']) for r in sorted(sub, key=lambda r: (r['cpc'] is None, r['cpc'] or 0))]
    views = ([dict(key='funded', label='Funded', kinds=['published'] * len(cols), columns=cols,
                   rows=trows([r for r in rs if r['ok']])),
              dict(key='unfunded', label='Not funded', kinds=['published'] * len(cols), columns=cols,
                   rows=trows([r for r in rs if not r['ok']]))]
             if len(rs) > TP.TABLE_ROWS_MAX else
             [dict(key='all', label='Every request', kinds=['published'] * len(cols), columns=cols, rows=trows(rs))])
    table = dict(caption='Every request and every rank', views=views)
    flow += [cite(('table', 0), *ranks, out, 'data'), cite(('table', 1), out, 'data')]
    if gaps:
        flow.append(cite(TB.explain('What the documents do not show', [(t, fi, al) for t, fi, al in gaps],
                                    place='end', tone='plain'), *ranks, out))
    flow.append('sources')

    keys = list(OrderedDict.fromkeys(ranks + [first_doc, out, 'data']))
    sources = [src(k) for k in keys]
    finding = ('%s of %s capital requests were funded, %s of the dollars requested.'
               % (C.num(s['fn']), C.num(s['n']), C.pct(s['share'])))
    ff = {'a': N(s['fn'], 'projects'), 'b': N(s['n'], 'requests'), 'c': P(s['share'])}
    return TP.page(pid, finding, facts, cons, table=table, tables=[shares], sources=sources,
                   finding_figures=ff, flow=['finding'] + flow)


# ---------------------------------------------------------------------- the hub
# Lines between years in the full table. The TOWN's numbering joins most of them: a request
# printed under the same project number in two years, or under a number the town wrote as a part
# of an earlier one (LPS23-07-A, -B, -C after LPS23-07). These are OURS, joined by name, because
# the number changed or (FY2026, FY2027) no number is printed. Each pair is one line on the table,
# drawn dashed. Pairs we judged too doubtful to draw are listed in DOUBTFUL so the next reader
# sees they were looked at, not missed.
LINKS = [
    ((2024, 'FD23-01'), (2025, 'FD23-02')),            # radio system, phase 1 then phase 2
    ((2024, 'FM23-03'), (2025, 'FM23-36')),            # Whalom Lake/Marshall Pond, then Marshall Pond
    ((2024, 'LPS23-06'), (2025, 'LPS20-04-A')),        # the MS/HS turf field: feasibility study, then site survey
    ((2025, 'FM23-36'), (2026, 'Marshall Pond Weed Treatment')),
    ((2025, 'LPS23-04'), (2026, 'Primary School Designer Services, Playground Equipment')),
    ((2026, 'Primary School Designer Services, Playground Equipment'), (2027, 'Primary School Playground (Design)')),
    ((2025, 'LPS23-05'), (2026, 'Primary School Feasibility Study for Entry & Drive Way Expansion')),
    ((2026, 'Primary School Feasibility Study for Entry & Drive Way Expansion'),
     (2027, 'Primary School Entry and Driveway Expansion (Design)')),
    ((2025, 'LPS23-07-B'), (2026, 'Primary School Window Safety Film')),
    ((2026, 'Primary School Window Safety Film'), (2027, 'Primary School Window Safety Film')),
    ((2025, 'DPW24-06'), (2026, 'North Cemetery Expansion Area Prep')),
    ((2025, 'FM24-06'), (2026, 'Public Safety Building 2nd Floor Design – Office/File Space')),
    ((2025, 'FM24-08'), (2026, 'Senior Center Parking Design')),
    ((2025, 'DPW22-01'), (2027, 'Front End Loader with Snow Plow (replacement, retain spare)')),
]
DOUBTFUL = [
    'FM20-05 Senior Center parking lot (FY2023, FY2024) and FM24-08 parking lot design (FY2025): a new number, a design request',
    'DPW23-18 / DPW 17-14 six-wheel trucks (FY2024, funded) and the FY2027 six-wheel replacement',
    'DPW17-09 one-ton dump (FY2023, funded) and the FY2027 one-ton replacement',
    'LPS19-10 mower (FY2023, funded) and the FY2027 mower replacement',
    'FM19-08A Old Primary abatement (FY2023, funded) and FY2027 TC Passios hazmat abatement',
    'FM19-06A Ritter, Vertex year 0-1 (FY2023) and FM19-06C-1/-2 Ritter items (FY2024)',
]


def _row(R, fy, k):
    m = [r for r in R if r['fy'] == fy and (r['project_number'] == k or (not r['project_number'] and r['project'] == k))]
    if len(m) != 1:
        fail('LINKS: %s %r matches %d rows' % (fy, k, len(m)))
    return m[0]


def edges(R):
    """Every line on the table: (earlier row, later row, ours)."""
    out = []
    nums = {}
    for r in sorted(R, key=lambda r: r['fy']):
        if r['project_number']:
            nums.setdefault(r['project_number'], []).append(r)
    for k, rows in nums.items():
        if len({r['fy'] for r in rows}) != len(rows):
            fail('project number %s appears twice in one year' % k)
        out += [(a, b, False) for a, b in zip(rows, rows[1:])]
        if '-' in k:
            parent = nums.get(k.rsplit('-', 1)[0])
            if parent:
                before = [p for p in parent if p['fy'] < rows[0]['fy']]
                if before:
                    out.append((before[-1], rows[0], False))
    for a, b in LINKS:
        ra, rb = _row(R, *a), _row(R, *b)
        if ra['fy'] >= rb['fy']:
            fail('LINKS: %s runs backwards' % (a,))
        if any(x is ra and y is rb for x, y, _ in out):
            fail('LINKS: %s to %s is already joined by its number' % (a, b))
        out.append((ra, rb, True))
    return out


def threads(R, E):
    """Projects joined across two or more years: groups of rows the lines connect."""
    up = {id(r): id(r) for r in R}

    def root(x):
        while up[x] != x:
            up[x] = up[up[x]]
            x = up[x]
        return x
    for a, b, _ in E:
        up[root(id(a))] = root(id(b))
    groups = OrderedDict()
    for r in R:
        groups.setdefault(root(id(r)), []).append(r)
    out = []
    for rows in groups.values():
        if len({r['fy'] for r in rows}) < 2:
            continue
        rows.sort(key=lambda r: (r['fy'], r['cpc'] or 99))
        first = rows[0]['fy']
        out.append(dict(rows=rows, back=not any(r['ok'] for r in rows if r['fy'] == first)
                        and any(r['ok'] for r in rows if r['fy'] > first),
                        ever=any(r['ok'] for r in rows)))
    return out


def thread_table_block(R):
    E = edges(R)
    T = threads(R, E)
    tid = {id(r): i for i, t in enumerate(T) for r in t['rows']}
    figs, names = set(), set()
    cols, where = [], {}
    for c, y in enumerate(YEARS):
        yr = [r for r in R if r['fy'] == y]
        ranked = sorted((r for r in yr if r['cpc']), key=lambda r: r['cpc'])
        if len({r['cpc'] for r in ranked}) != len(ranked):
            fail('%s prints a rank twice' % C.fy(y))
        slots = []
        top = ranked[-1]['cpc'] if ranked else 0
        by = {r['cpc']: r for r in ranked}
        for k in range(1, top + 1):
            slots.append(by.get(k))
        slots += [r for r in yr if not r['cpc']]
        cells, cut = [], None
        for s, r in enumerate(slots):
            if r is None:
                cells.append(dict(gap=True))
                continue
            where[id(r)] = (c, s)
            rank = C.num(r['cpc']) if r['cpc'] else None
            amt = C.usd(r['amt'])
            figs |= {amt} | ({rank} if rank else set())
            names.add(r['project'])
            if cut is None and r['cpc'] and not r['ok']:
                cut = s
            cells.append(dict(project=r['project'], rank_text=rank, amount_text=amt, funded=r['ok'],
                              dept=r['department'], thread=tid.get(id(r))))
        n = C.num(len(yr))
        figs |= {C.fy(y), n}
        cols.append(dict(label=C.fy(y), count_text='%s requests' % n, cells=cells, cut=cut))
    lines = [dict(a=where[id(a)], b=where[id(b)], ours=ours, thread=tid[id(a)]) for a, b, ours in E]
    data = dict(columns=cols, lines=lines, text=dict(
        funded='Funded', unfunded='Not funded', town='Same project, by the town’s project number',
        ours='Same project, joined by us by name', cut='Highest-ranked request left unfunded',
        gap='Rank not in the documents held', unranked='unranked', hint='Tap a request to follow it across years.'),
        note='Each column is one year’s full ranked list in the Capital Planning Committee’s order. A request '
             'withdrawn or set aside before the committee ranked it is not drawn: the departments’ own '
             'lists are not held.')
    blk = TB.custom('capital-thread-table', 'Every ranked request, every year', data, place='lead',
                    figures=sorted(figs), allow=sorted(names),
                    alt='Every capital request the committee ranked, in each year’s order, with lines joining the same project across years.',
                    so='Most requests appear in one year only; the lines show the few that came back, and where '
                       'each stood against the funding line each time.')
    n, back, never = len(T), sum(t['back'] for t in T), sum(not t['ever'] for t in T)
    total = len(R)
    f = LD.fact
    facts = [f('all', N(total, 'requests'), 'ranked on the five lists, all drawn', 'published'),
             f('again', N(n, 'projects'), 'on the lists in two or more years', 'published'),
             f('back', N(back, 'projects'), 'unfunded the first year, funded on a later list', 'published'),
             f('never', N(never, 'projects'), 'on two or more lists and never funded in these years', 'published')]
    cons = [TP.conclusion('Of %s ranked requests on the five lists, %s projects came back in a later year.'
                          % (C.num(total), C.num(n)), ['all', 'again'],
                          {'a': N(total, 'requests'), 'b': N(n, 'projects')},
                          so='A dashed line is our join, by name; where the town’s number joins two years the line is solid.'),
            TP.conclusion('%s were unfunded the first time and funded later; %s never were.'
                          % (C.num(back), C.num(never)), ['back', 'never'],
                          {'a': N(back, 'projects'), 'b': N(never, 'projects')},
                          so='One year’s outcome was not the last word on those projects.')]
    return TB.claims(blk, cons, facts)


def hub(R):
    st = {y: year_stats([r for r in R if r['fy'] == y]) for y in YEARS}
    full = list(YEARS)
    lo = min(full, key=lambda y: st[y]['share'])
    hi = max(full, key=lambda y: st[y]['share'])
    inorder = [y for y in YEARS if not st[y]['below'] and not st[y]['unranked_funded']]
    out_order = [y for y in YEARS if y not in inorder]
    f = LD.fact

    # the year by year chart, with its conclusions
    chart = TP.series('Requested and funded, by year', [C.fy(y) for y in YEARS], [
        TP.track('Funded', [st[y]['fun'] for y in YEARS], 'published', 'bar'),
        TP.track('Not funded', [st[y]['tot'] - st[y]['fun'] for y in YEARS], 'published', 'bar'),
    ], '$', kind='bar', stacked=True, totals=True)
    yfacts = [f('lo', P(st[lo]['share']), '%s, share of requested dollars funded' % C.fy(lo), 'published', {'y': F(lo)}),
              f('hi', P(st[hi]['share']), '%s, share of requested dollars funded' % C.fy(hi), 'published', {'y': F(hi)}),
              f('inord', figure(len(inorder), '%d of %d' % (len(inorder), len(YEARS)), 'years'),
                'years funded strictly in the committee’s order (ours)', 'estimate')]
    ycons = [LD.conclusion('Between %s (%s) and %s (%s) of the requested dollars were funded.'
                           % (C.pct(st[lo]['share']), C.fy(lo), C.pct(st[hi]['share']), C.fy(hi)), ['lo', 'hi'],
                           {'a': P(st[lo]['share']), 'b': P(st[hi]['share']), 'y': F(lo), 'z': F(hi)}),
             LD.conclusion('Funding followed the committee’s order exactly in %s; in %s it did not.'
                           % (' and '.join(C.fy(y) for y in inorder), ', '.join(C.fy(y) for y in out_order)),
                           ['inord'], dict({('i%d' % y): F(y) for y in inorder}, **{('o%d' % y): F(y) for y in out_order}),
                           so='Each year’s tab shows which projects moved, and what document records it.')]
    yblk = TB.claims(TB.chart(chart, place='body',
                              so='The unfunded part of each bar is the unshaded requests in that year’s column above.'), ycons, yfacts)

    # who asked, who got, every year together
    agg = OrderedDict()
    for y in full:
        for k, v in st[y]['d'].items():
            a = agg.setdefault(k, dict(amt=0.0, famt=0.0))
            a['amt'] += v['amt']
            a['famt'] += v['famt']
    all_req = sum(v['amt'] for v in agg.values())
    all_fun = sum(v['famt'] for v in agg.values())
    for v in agg.values():
        v['share_req'] = 100 * v['amt'] / all_req
        v['share_fun'] = 100 * v['famt'] / all_fun
    always = [k for k in DEPTS if all(st[y]['d'][k]['own'] == 100 for y in full if k in st[y]['d'])
              and sum(k in st[y]['d'] for y in full) >= 3]
    fac = agg['Facilities']
    bfacts = [f('facr', P(fac['share_req']), 'Facilities’ share of dollars requested', 'published'),
              f('facf', P(fac['share_fun']), 'Facilities’ share of dollars funded', 'published')]
    bcons = [LD.conclusion('Facilities requested %s of the dollars in five years and received %s of what was funded.'
                           % (C.pct(fac['share_req']), C.pct(fac['share_fun'])), ['facr', 'facf'],
                           {'a': P(fac['share_req']), 'b': P(fac['share_fun'])},
                           so='A share of dollars over five years; each year’s tab shows which Facilities requests were funded.')]
    for k in always:
        i = 'all-' + k.lower().replace(' ', '-')
        bfacts.append(f(i, U(sum(st[y]['d'][k]['amt'] for y in full if k in st[y]['d'])),
                        '%s requests, every one funded' % k, 'published'))
    if always:
        bcons.append(LD.conclusion('%s received every dollar it requested, in each year it made a request.'
                                   % ' and '.join(always), ['all-' + k.lower().replace(' ', '-') for k in always],
                                   so='The year tabs list each of those requests.'))
    bblk = TB.claims(bands_block(agg, 'Who asked, who got, five years', 'body',
                                 'Each department’s share of the dollars requested in five years, joined to its share of the dollars funded.',
                                 '%s to %s together. Shares of dollars.' % (C.fy(YEARS[0]), C.fy(YEARS[-1])),
                                 'A band that narrows was a smaller share of what was funded than of what was requested.',
                                 allow=[C.fy(y) for y in YEARS], highlight='Facilities'),
                     bcons, bfacts)

    cols = [C.fy(y) for y in YEARS]
    trows = []
    for k in DEPTS:
        if not any(k in st[y]['d'] for y in YEARS):
            continue
        cells = []
        for y in YEARS:
            v = st[y]['d'].get(k)
            cells.append('—' if not v else '%s of %s · %s' % (C.usd(v['famt']), C.usd(v['amt']), C.pct(v['own'], 0)))
        trows.append(dict(label=k, cells=cells))
    trows.append(dict(label='All departments', cells=['%s of %s · %s' % (C.usd(st[y]['fun']), C.usd(st[y]['tot']),
                                                                         C.pct(st[y]['share'], 0)) for y in YEARS]))
    table = dict(caption='Each department, year by year', views=[dict(
        key='years', label='Funded of requested', kinds=['published'] * len(YEARS), columns=cols, rows=trows,
        note='Dollars funded of dollars requested, and the percent.')])
    return TP.hub(
        HUB,
        'Five years of capital requests, each ranked by the Capital Planning Committee: between %s and %s '
        'of the dollars requested were funded, and in %s years the money did not follow the committee’s order.'
        % (C.pct(st[lo]['share']), C.pct(st[hi]['share']), C.num(len(out_order))),
        None, table=table, blocks=[thread_table_block(R), yblk, bblk],
        tabs=('Each fiscal year', ['capital-fy%d' % y for y in sorted(YEARS, reverse=True)]),
        answer_figures={'a': P(st[lo]['share']), 'b': P(st[hi]['share']), 'n': N(len(out_order), 'years')})


def build():
    R = load()
    out = {HUB: hub(R)}
    for y in YEARS:
        out['capital-fy%d' % y] = year_page(y, [r for r in R if r['fy'] == y])
    mine = sorted(t for t, (_, home, gen) in REG.TOPICS.items() if home == HUB and gen == 'build_capital_rankings.py')
    if sorted(k for k in out if k != HUB) != mine:
        fail('the pages built are not the registry’s: %s' % sorted(set(mine) ^ set(out)))
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t): json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('capital rankings: %d outputs current' % len(outs))
        return 0
    for p, t in outs.items():
        with open(p + '.tmp', 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(t)
        os.replace(p + '.tmp', p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
