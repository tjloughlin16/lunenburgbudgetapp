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
import build_capital_unranked as BU  # noqa: E402

DATA = os.path.join(ROOT, 'sources', 'data', 'capital-rankings.csv')
UDATA = BU.DATA   # requests made and never ranked: scripts/build_capital_unranked.py
OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
HUB = 'capital-planning'
YEARS = (2023, 2024, 2025, 2026, 2027)
# The Town's capital cost test (Article 13, FY2027 Capital Plan, page 2; FY2024 budget message). TJ, 21
# November 2026: "20k it is, lets keep that as the threshold" -- drawn on the request-sizes chart.
CAPITAL_LINE = 20000
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
    'unranked': ('Lunenburg Budget Project — capital-requests-unranked.csv, every request made and never '
                 'ranked, with the page, line or second it was read from', None),
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


def load_unranked():
    """Requests made and never ranked (scripts/build_capital_unranked.py, which validates them and
    derives ranked_in). Only kinds that ARE a request for that year and never ranked are drawn as
    unranked; `merged` rows are listed apart on the year page; `out-year` rows stay in the data."""
    if not os.path.exists(UDATA):
        fail('%s is not built -- python3.11 scripts/build_capital_unranked.py' % os.path.relpath(UDATA, ROOT))
    out = []
    for r in csv.DictReader(open(UDATA, encoding='utf-8')):
        r['fy'] = int(r['cycle_fy'])
        r['amt'] = float(r['amount']) if r['amount'] else None
        r['ok'], r['cpc'] = False, None
        out.append(r)
    return out


def drawn(UN, fy=None):
    return [u for u in UN if u['kind'] in BU.UNRANKED and u['fy'] in YEARS and (fy is None or u['fy'] == fy)]


WHAT = {'dropped': 'dropped before ranking', 'withdrawn': 'withdrawn', 'not-ranked': 'left unrated',
        'merged': 'folded into a ranked request'}


def what(u):
    if u['kind'] == 'moved':
        return 'moved to %s' % C.fy(int(u['money_fy'])) if u['money_fy'] else 'moved to a later year'
    return WHAT[u['kind']]


def amount_text(u):
    return C.usd(u['amt']) if u['amt'] is not None else 'amount not printed'


def _href(u):
    path = u['reason_source'].split(';')[0].strip()
    if not path:
        return None
    if 'youtube-transcripts' in path:
        m = [w for w in (u['reason_where'] + ' ' + u['reason_source']).split() if w.startswith('https://')]
        return m[0].rstrip(';,') if m else None
    if path.startswith('meetings/text/') and path.endswith('.txt'):   # link the minutes, not our text
        pdf = 'meetings/' + path[len('meetings/text/'):-4] + '.pdf'
        if os.path.exists(os.path.join(ROOT, 'sources', pdf)):
            path = pdf
    return '/docs/' + path


def unranked_block(fy, UN):
    """Every request made for the year that the committee's list does not hold, with its reason."""
    rows, merged, allow, figs = [], [], set(), set()
    for u in [x for x in UN if x['fy'] == fy and x['kind'] in BU.UNRANKED + ('merged',)]:
        b = u['reason_basis']
        basis, btext = {'document': ('document', 'document'),
                        'document (match ours)': ('ours', 'document; that it is this request is our match'),
                        'captions (finding aid)': ('captions', 'meeting recording, captions'),
                        'none recorded': ('none', 'minutes and recordings searched')}[b]
        reason = 'none recorded' if b == 'none recorded' else u['reason']
        rt = u['ranked_in'].replace('never ranked FY2023-FY2027', 'never, FY2023 to FY2027')
        item = dict(project=u['project'], dept=u['department'] or 'department not printed',
                    amount_text=amount_text(u), what=what(u), reason=reason, basis=basis, basis_text=btext,
                    href=_href(u) if basis != 'none' else None, ranked_text=rt)
        (merged if u['kind'] == 'merged' else rows).append(item)
        if u['amt'] is not None:
            figs.add(item['amount_text'])
        allow |= {u['project'], reason, rt, item['what'], item['dept']}
        if item['href']:
            allow.add(item['href'])
    n = len(rows)
    stated = sum(1 for r in rows if r['basis'] != 'none')
    data = dict(rows=rows, merged=merged, text=dict(
        merged='Folded into requests the committee did rank', reason='Why:', ranked='Ranked in:'),
        note='Requests found in the committee’s minutes, the department and Town Manager decks, the '
             'committee’s workbooks and the School Committee’s plans. The departments’ own complete '
             'lists are not held, so there may be more. A reason is shown only where a document or a '
             'speaker states one.')
    blk = TB.custom('capital-unranked-list', 'Requested, never ranked', data, place='body',
                    figures=sorted(figs), allow=sorted(a for a in allow if a),
                    alt='%s: each capital request made for the year that the committee did not rank, '
                        'what happened to it, and the reason where one is recorded.' % C.fy(fy),
                    so='The ranked list is not every request; these never reached it.')
    f = LD.fact
    facts = [f('asked', N(n, 'requests'), 'requested and never ranked', 'published'),
             f('stated', figure(stated, '%d of %d' % (stated, n), 'requests'),
               'with a reason a document or recording states', 'published')]
    con = TP.conclusion('%s requests made for %s never reached the ranked list; %s have a stated reason.'
                        % (C.num(n), C.fy(fy), '%d of %d' % (stated, n)), ['asked', 'stated'],
                        {'a': N(n, 'requests'), 'y': F(fy), 'b': figure(stated, '%d of %d' % (stated, n), 'requests')},
                        so='The list the committee ranked is what reached it, not every request a '
                           'department made.')
    return TB.claims(blk, [con], facts)


def src(key):
    label, path = DOC[key]
    data = '/docs/data/capital-requests-unranked.csv' if key == 'unranked' else '/docs/data/capital-rankings.csv'
    return dict(key=key, label=label, href='/docs/' + path if path else data)


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


def year_page(fy, rs, UN):
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
    flow.append(cite(unranked_block(fy, UN), 'unranked'))

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
    gaps.append(('Every request each department filed for %s, including any never presented or minuted. '
                 'Closes: each department’s complete request list, requested by records request on '
                 '20 November 2026.' % C.fy(fy), None, (C.fy(fy), '20 November 2026')))
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

    keys = list(OrderedDict.fromkeys(ranks + [first_doc, out, 'data', 'unranked']))
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
# TJ, 20 November 2026: "you should assume if they have different codes, that they are different
# projects." So two rows carrying different town codes are never joined, and these were settled
# by that rule rather than judged. (A suffix split, X-1 under X, is one code and still joins.)
DIFFERENT = [
    'FD23-01 radio system (FY2024) and FD23-02 (FY2025): different codes',
    'FM23-03 Whalom Lake/Marshall Pond (FY2024) and FM23-36 Marshall Pond (FY2025): different codes',
    'LPS23-06 turf field feasibility study (FY2024) and LPS20-04-A turf field site survey (FY2025): different codes',
    'FM20-05 Senior Center parking lot (FY2023, FY2024) and FM24-08 parking lot design (FY2025): different codes',
    'FM19-06A Ritter, Vertex year 0-1 (FY2023) and FM19-06C-1/-2 Ritter items (FY2024): different codes',
]
# Rows of FY2026 and FY2027 print no codes, so the rule cannot decide these.
DOUBTFUL = [
    'DPW23-18 / DPW 17-14 six-wheel trucks (FY2024, funded) and the FY2027 six-wheel replacement',
    'DPW17-09 one-ton dump (FY2023, funded) and the FY2027 one-ton replacement',
    'LPS19-10 mower (FY2023, funded) and the FY2027 mower replacement',
    'FM19-08A Old Primary abatement (FY2023, funded) and FY2027 TC Passios hazmat abatement',
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


def unranked_edges(R, D):
    """Lines to the requests made and never ranked: the same town number on a ranked list (the
    nearest year before and after), or the ranked request the row's `same_as` names (ours, by name,
    where the later year prints no number -- TJ's rule: different codes are different projects)."""
    out = []
    for d in D:
        same = [r for r in R if d['project_number'] and r['project_number'] == d['project_number']]
        before = [r for r in same if r['fy'] < d['fy']]
        after = [r for r in same if r['fy'] > d['fy']]
        if before:
            out.append((max(before, key=lambda r: r['fy']), d, False))
        if after:
            out.append((d, min(after, key=lambda r: r['fy']), False))
        for ref in filter(None, (x.strip() for x in d['same_as'].split(';'))):
            fy, _, k = ref.partition(':')
            r = _row(R, int(fy), k)
            if r in same or r['fy'] == d['fy']:
                continue
            out.append((r, d, True) if r['fy'] < d['fy'] else (d, r, True))
    return out


def thread_table_block(R, UN):
    E0 = edges(R)
    T0 = threads(R, E0)            # the facts count ranked projects only, as before
    D = drawn(UN)
    E = E0 + unranked_edges(R, D)
    T = threads(R + D, E)
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
        never = [u for u in D if u['fy'] == y]
        slots += never
        cells, cut = [], None
        for s, r in enumerate(slots):
            if r is None:
                cells.append(dict(gap=True))
                continue
            where[id(r)] = (c, s)
            rank = C.num(r['cpc']) if r['cpc'] else None
            amt = C.usd(r['amt']) if r['amt'] is not None else 'amount not printed'
            figs |= {amt} | ({rank} if rank else set())
            names.add(r['project'])
            if cut is None and r['cpc'] and not r['ok']:
                cut = s
            cell = dict(project=r['project'], rank_text=rank, amount_text=amt, funded=r['ok'],
                        dept=r['department'] or 'department not printed', thread=tid.get(id(r)))
            if 'kind' in r:
                cell.update(never=True, status_text=what(r))
                names.add(cell['status_text'])
            cells.append(cell)
        n, m = C.num(len(yr)), C.num(len(never))
        figs |= {C.fy(y), n, m}
        cols.append(dict(label=C.fy(y), count_text='%s on the list · %s never ranked' % (n, m), cells=cells, cut=cut))
    lines = [dict(a=where[id(a)], b=where[id(b)], ours=ours, thread=tid[id(a)]) for a, b, ours in E]
    data = dict(columns=cols, lines=lines, text=dict(
        funded='Funded', unfunded='Not funded', town='Same project, by the town’s project number',
        ours='Same project, joined by us by name', cut='Highest-ranked request left unfunded',
        gap='Rank not in the documents held', unranked='unranked', hint='Tap a request to follow it across years.',
        never='Requested that year, never ranked'),
        note='Each column is one year’s full ranked list in the Capital Planning Committee’s order. Below it, '
             'dotted: requests made for that year that the committee never ranked, as found in its minutes, '
             'the department and Town Manager decks and the recordings. The departments’ own complete lists '
             'are not held, so there may be more. Each year’s page gives the reason, where one is recorded.')
    blk = TB.custom('capital-thread-table', 'Every request, every year', data, place='lead',
                    figures=sorted(figs), allow=sorted(names),
                    alt='Every capital request the committee ranked, in each year’s order, then the requests it never ranked, with lines joining the same project across years.',
                    so='Most requests appear in one year only; the lines show the few that came back, and where '
                       'each stood against the funding line each time.')
    n, back, never = len(T0), sum(t['back'] for t in T0), sum(not t['ever'] for t in T0)
    total = len(R)
    stated = sum(1 for d in D if d['reason_basis'] != 'none recorded')
    f = LD.fact
    facts = [f('all', N(total, 'requests'), 'ranked on the five lists, all drawn', 'published'),
             f('again', N(n, 'projects'), 'on the lists in two or more years', 'published'),
             f('back', N(back, 'projects'), 'unfunded the first year, funded on a later list', 'published'),
             f('never', N(never, 'projects'), 'on two or more lists and never funded in these years', 'published'),
             f('asked', N(len(D), 'requests'), 'requested and never ranked, five years', 'published'),
             f('stated', figure(stated, '%d of %d' % (stated, len(D)), 'requests'),
               'never ranked, with a reason a document or recording states', 'published')]
    cons = [TP.conclusion('Of %s ranked requests on the five lists, %s projects came back in a later year.'
                          % (C.num(total), C.num(n)), ['all', 'again'],
                          {'a': N(total, 'requests'), 'b': N(n, 'projects')},
                          so='A dashed line is our join, by name; where the town’s number joins two years the line is solid.'),
            TP.conclusion('%s were unfunded the first time and funded later; %s never were.'
                          % (C.num(back), C.num(never)), ['back', 'never'],
                          {'a': N(back, 'projects'), 'b': N(never, 'projects')},
                          so='One year’s outcome was not the last word on those projects.'),
            TP.conclusion('At least %s more requests were made and never ranked; %s have a stated reason.'
                          % (C.num(len(D)), '%d of %d' % (stated, len(D))), ['asked', 'stated'],
                          {'a': N(len(D), 'requests'), 'b': figure(stated, '%d of %d' % (stated, len(D)), 'requests')},
                          so='At least, because the departments’ own lists are not held; the rest were '
                             'found in minutes, decks and recordings.')]
    return TB.claims(blk, cons, facts)


# ---------------------------------------------------------------- what we hold for every year
# TJ, 20 November 2026: "put a table on the page, probably toward the bottom, that shows the
# information we have for every year." One row per fiscal year, as far back as any held source
# reaches. The planning documents are a REGISTER, sources/data/capital-coverage.csv, one row per
# (year, part) naming the document and the page it was read from; every document must be in the
# archive, and the register is checked against the datasets that also hold these ranks below. The
# funded column and the minutes column are computed from their datasets and nothing else.
CDATA = os.path.join(ROOT, 'sources', 'data', 'capital-coverage.csv')
PARTS = [('requests', 'Every department’s requests'), ('dept', 'Departments’ own order'),
         ('sc', 'School Committee’s order'), ('cpc_own', 'Committee’s ranked list, its own sheet'),
         ('cpc_copy', 'Committee’s ranked list, as others printed it'), ('tm', 'Town Manager’s plan'),
         ('funded', 'What was funded'), ('minutes', 'Committee minutes')]
REGISTERED = {'requests', 'dept', 'sc', 'cpc_own', 'cpc_copy', 'tm'}
STATES = ('held', 'part', 'spoken', 'none')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')


def _rows(name):
    return list(csv.DictReader(open(os.path.join(ROOT, 'sources', 'data', name), encoding='utf-8')))


def _docs():
    return {l.split(',', 1)[0] for l in open(os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv'),
                                             encoding='utf-8')}


def _link(path):
    """A document's address on the site; a recording's transcript links the video it transcribes."""
    if 'youtube-transcripts' in path:
        vid = os.path.basename(path)[len('YYYY-MM-DD-'):-len('.json')]
        return 'https://www.youtube.com/watch?v=' + vid
    return '/docs/' + path


def _doc_label(path):
    b = os.path.basename(path)
    return 'recording' if 'youtube-transcripts' in path else b


def coverage(R):
    """{(fy, part): cell} and the year range. A cell: state, text, where, links [(label, href)]."""
    man = _docs()
    cells, figs = {}, set()
    for r in _rows('capital-coverage.csv'):
        y, part, state = int(r['cycle_fy']), r['part'], r['state']
        if part not in REGISTERED or state not in STATES or (y, part) in cells:
            fail('capital-coverage.csv: %s %s %s is not a part, a state, or is a repeat' % (y, part, state))
        docs = [d.strip() for d in r['document'].split(';') if d.strip()]
        for d in docs:
            if d not in man and not os.path.exists(os.path.join(ROOT, 'sources', d)):
                fail('capital-coverage.csv: %s %s names %s, not in the archive' % (y, part, d))
        cells[(y, part)] = dict(state=state, text=r['what'], where=r['where'],
                                links=[dict(label=_doc_label(d), href=_link(d)) for d in docs])
    # the register agrees with the ranking dataset: every document a year's ranks were read from is
    # registered as that year's committee list, and a year whose departments' order fills every row
    # is registered as held
    for y, keys in RANKS_FROM.items():
        reg = {l['href'] for p in ('cpc_own', 'cpc_copy') for l in cells.get((y, p), {}).get('links', [])}
        miss = [k for k in keys if DOC[k][1] and '/docs/' + DOC[k][1] not in reg]
        if miss:
            fail('capital-coverage.csv: %s ranks were read from %s, not registered as its committee list'
                 % (C.fy(y), miss))
    for y in YEARS:
        rs = [r for r in R if r['fy'] == y]
        full = all(r['dept_rank'] for r in rs)
        if full != (cells.get((y, 'dept'), {}).get('state') == 'held'):
            fail('capital-coverage.csv: %s departments’ order is %s in the dataset, not in the register'
                 % (C.fy(y), 'complete' if full else 'incomplete'))
    for t in _rows('track-field-capital-history.csv'):   # a printed School Committee ranking table
        if t['body'] == 'School Committee' and t['kind'] == 'ranking' and t['basis'] == 'document' \
                and (int(t['cycle_fy']), 'sc') not in cells:
            fail('capital-coverage.csv: %s holds a School Committee ranking (%s), unregistered'
                 % (t['cycle_fy'], t['doc']))
    if any(s['rank'] for s in _rows('capital-submissions-fy28.csv')) and (2028, 'dept') not in cells:
        fail('capital-coverage.csv: the FY2028 submission forms carry ranks, unregistered')

    # WHAT WAS FUNDED, computed: the ranked lists' outcomes; else the voted item lists the annual
    # reports print; else the funding total; else the capital project fund balances, which show
    # money held, not the year's vote.
    funded = {}
    for y in YEARS:
        rs = [r for r in R if r['fy'] == y]
        a, b = C.num(sum(r['ok'] for r in rs)), C.num(len(rs))
        funded[y] = dict(state='held', text='%s of %s ranked requests, with their outcome' % (a, b),
                         where='', links=[dict(label=_doc_label(DOC[OUTCOME_FROM[y]][1]),
                                               href=_link(DOC[OUTCOME_FROM[y]][1]))])
        figs |= {a, b}
    plans = {}
    for p in _rows('capital-plans.csv'):
        plans.setdefault(int(p['plan_fiscal_year']), {}).setdefault(p['copy'], []).append(p)
    for y, by in plans.items():
        if y in funded:
            continue
        copy = 'town meeting article' if 'town meeting article' in by else 'committee report'
        ps = by[copy]
        # a page can print more than one list (cash and borrowing): quote each printed total
        tots = list(OrderedDict.fromkeys(C.usd(float(p['printed_total'])) for p in ps))
        n, tot = C.num(len(ps)), ' and '.join(tots)
        doc = 'town-annual-reports/docs/' + ps[0]['document']
        if doc not in man:
            fail('capital-plans.csv cites %s, not in the archive' % doc)
        figs.update(tots)
        funded[y] = dict(state='held', text='%s items, item by item; printed %s %s'
                         % (n, 'totals' if len(tots) > 1 else 'total', tot),
                         where='p%s' % ps[0]['page'], links=[dict(label=_doc_label(doc), href=_link(doc))])
        figs.add(n)
    for h in _rows('capital-funding-history.csv'):
        y = int(h['fy'])
        if y not in funded:
            t = C.usd(float(h['total']))
            funded[y] = dict(state='part', text='the plan’s total, %s; no item list read' % t, where='',
                             links=[dict(label='capital-funding-history.csv', href='/docs/data/capital-funding-history.csv')])
            figs.add(t)
    for y in sorted({int(r['fy']) for r in _rows('report-capital-projects.csv')}):
        if y not in funded:
            funded[y] = dict(state='part', text='capital project fund balances only, not the year’s vote',
                             where='', links=[dict(label='report-capital-projects.csv',
                                                   href='/docs/data/report-capital-projects.csv')])
    for y, c in funded.items():
        cells[(y, 'funded')] = c

    # COMMITTEE MINUTES, computed from the meeting index. The committee ranks in the autumn and
    # winter for the year after next July, so a meeting is counted toward the fiscal year AFTER the
    # one it was held in -- our mapping, by date, and the note says so.
    mins = {}
    for m in csv.DictReader(open(os.path.join(ROOT, 'sources', 'meetings', 'index.csv'), encoding='utf-8')):
        if m['board'] != 'Capital Planning Committee' or not m['path']:
            continue
        yy, mm = int(m['date'][:4]), int(m['date'][5:7])
        cyc = (yy + 1 if mm >= 7 else yy) + 1
        mins.setdefault(cyc, {}).setdefault(m['kind'], 0)
        mins[cyc][m['kind']] += 1
    for y, k in mins.items():
        n, a = k.get('minutes', 0), k.get('agenda', 0)
        if n:
            t = C.num(n)
            cells[(y, 'minutes')] = dict(state='held', text='%s sets of minutes' % t, where='',
                                         links=[dict(label='minutes', href='/minutes/capital-planning-committee/')])
        else:
            t = C.num(a)
            cells[(y, 'minutes')] = dict(state='part', text='%s agendas, no minutes posted' % t, where='',
                                         links=[dict(label='agendas', href='/minutes/capital-planning-committee/')])
        figs.add(t)
    years = list(range(max(y for y, _ in cells), min(y for y, _ in cells) - 1, -1))
    return cells, years, figs, mins


def _gap(what_has):
    """The money-gaps row whose question contains every string given; the build fails without it."""
    for g in _rows('money-gaps.csv'):
        if all(s in g['what'] for s in what_has):
            return g
    fail('no row in money-gaps.csv asks %r -- register the gap (CLAUDE.md rule 7c)' % (what_has,))


def coverage_block(R):
    cells, years, figs, mins = coverage(R)
    for y in years:
        figs.add(C.fy(y))
    rows = []
    for y in years:
        rc = []
        for k, _ in PARTS:
            c = cells.get((y, k))
            rc.append(c if c else dict(state='none', text='', where='', links=[]))
        rows.append(dict(label=C.fy(y), cells=rc))
    st = lambda k, s: [y for y in years if cells.get((y, k), {}).get('state') in s]   # noqa: E731
    fund = st('funded', ('held',))
    plan = sorted(set(st('cpc_own', ('held',))) | set(st('cpc_copy', ('held',))))
    own = st('cpc_own', ('held',))
    copies = [y for y in st('cpc_copy', ('held',)) if y not in own]
    deptfull = st('dept', ('held',))
    scp, scs = st('sc', ('held',)), st('sc', ('spoken',))
    first_min = min(y for y, k in mins.items() if k.get('minutes'))
    reqnone = [y for y in range(first_min, max(YEARS) + 1)
               if cells.get((y, 'requests'), {}).get('state') not in ('held', 'part')]
    noown = [y for y in YEARS if y not in own]
    g_req = _gap([C.fy(y) for y in reqnone] + ['request'])
    g_own = _gap([C.fy(y) for y in noown] + ['own ranking sheet'])
    g_sc = _gap([C.fy(y) for y in scs] + ['School Committee'])
    g_dept = _gap(['department rank its own'])
    data = dict(columns=[dict(key=k, label=l) for k, l in PARTS], rows=rows, text=dict(
        held='held', part='part of it', spoken='heard in a recording only', none='nothing held',
        year='Fiscal year', gaps='Registered as questions the documents cannot yet answer'),
        gaps=[dict(what=g['what'], href='/what-we-cannot-answer') for g in (g_own, g_req, g_sc, g_dept)],
        note='Each mark links the document it was read from. A ranked list is the year the money is for; '
             'committee minutes are counted toward the year after the one the meeting was held in (our '
             'mapping, by date). Nothing held means nothing found in what this archive holds, not that '
             'the town never produced it.')
    allow = sorted({c['where'] for r in rows for c in r['cells'] if c['where']}
                   | {l[k] for r in rows for c in r['cells'] for l in c['links'] for k in ('label', 'href')}
                   | {r['what'] for r in _rows('capital-coverage.csv')}   # register text: dates quoted
                   | {g['what'] for g in data['gaps']})
    blk = TB.custom('capital-coverage', 'What we hold, year by year', data, place='end',
                    figures=sorted(figs), allow=allow,
                    alt='For every fiscal year, which capital planning documents are held: requests, each '
                        'body’s order, the committee’s ranked list, the Town Manager’s plan, what was funded, '
                        'and the committee’s minutes.',
                    so='The outcome of most years is on the record; how the ranking was reached is held '
                       'for only the most recent few.')
    f = LD.fact
    facts = [f('fund', F(min(fund)), 'earliest year with the funded items held', 'published'),
             f('plan', F(min(plan)), 'earliest year with the committee’s full ranked list', 'published'),
             f('own', N(len(own), 'years'), 'with the committee’s own ranking sheet', 'published'),
             f('copy', N(len(copies), 'years'), 'with the ranked list only as a printed copy', 'published'),
             f('dept', N(len(deptfull), 'years'), 'with every department’s own order', 'published'),
             f('scp', N(len(scp), 'years'), 'with the School Committee’s order printed', 'published')]
    yrs = lambda n: 'year' if n == 1 else 'years'   # noqa: E731
    cons = [TP.conclusion('What was funded is held back to %s; the committee’s full ranked list only from %s.'
                          % (C.fy(min(fund)), C.fy(min(plan))), ['fund', 'plan'],
                          {'a': F(min(fund)), 'b': F(min(plan))},
                          so='For the earlier years the outcome is on the record and the ranking behind it is not.'),
            TP.conclusion('The committee’s own ranking sheet is held for %s %s, and %s more only as printed copies.'
                          % (C.num(len(own)), yrs(len(own)), C.num(len(copies))), ['own', 'copy'],
                          {'a': N(len(own), 'years'), 'b': N(len(copies), 'years')},
                          so='A copy is the Town Manager’s or the town report’s printing of the order, not '
                             'the committee’s own record of it.'),
            TP.conclusion('Every department’s own order is held for %s %s; the School Committee’s printed for %s.'
                          % (C.num(len(deptfull)), yrs(len(deptfull)), C.num(len(scp))), ['dept', 'scp'],
                          {'a': N(len(deptfull), 'years'), 'b': N(len(scp), 'years')},
                          so='In other years no printed document shows which of its requests each body put on top.')]
    return TB.claims(blk, cons, facts)


def dept_years_block(st):
    """THE DEPARTMENT TABLE AS A CHART (TJ, 20 November 2026: "another chart AND table that shows the
    same info as 'Each department, year by year'"). Small multiples: a row per department, a cell
    per year, a bar as long as the dollars requested with the funded part filled. One scale across
    every cell, so a long bar is a big year for that department against all of them."""
    rows, figs = [], set()
    for k in DEPTS:
        if not any(k in st[y]['d'] for y in YEARS):
            continue
        cells = []
        for y in YEARS:
            v = st[y]['d'].get(k)
            if not v:
                cells.append(None)
                continue
            t = '%s of %s' % (C.usd(v['famt']), C.usd(v['amt']))
            figs |= {C.usd(v['famt']), C.usd(v['amt'])}
            cells.append(dict(req=v['amt'], fun=v['famt'], text=t))
        rows.append(dict(label=k, cells=cells))
    years = [C.fy(y) for y in YEARS]
    figs |= set(years)
    data = dict(years=years, rows=rows, text=dict(funded='Funded', unfunded='Requested, not funded', none='no request'),
                note='Each bar is one department’s requests in one year, on one scale for every cell; the filled '
                     'part was funded. The table below gives the same figures.')
    blk = TB.custom('capital-dept-years', 'Each department, each year', data, place='body', figures=sorted(figs),
                    alt='For each department and each fiscal year, the dollars requested as a bar with the dollars funded filled in.',
                    so='Where a bar is mostly unfilled, most of that department’s requested dollars that year went unfunded.')
    # the department-year with the most dollars left unfunded, and the one with the most funded
    cand = [(st[y]['d'][k]['amt'] - st[y]['d'][k]['famt'], k, y) for y in YEARS for k in st[y]['d']]
    gap, gk, gy = max(cand)
    top = max(((st[y]['d'][k]['famt'], k, y) for y in YEARS for k in st[y]['d']))
    share = 100 * top[0] / sum(st[y]['d'][top[1]]['famt'] for y in YEARS if top[1] in st[y]['d'])
    f = LD.fact
    facts = [f('gap', U(gap), '%s %s, requested and not funded' % (gk, C.fy(gy)), 'published', {'y': F(gy)}),
             f('top', U(top[0]), '%s %s, funded' % (top[1], C.fy(top[2])), 'published', {'y': F(top[2])})]
    cons = [TP.conclusion('%s in %s left %s unfunded, the most of any department in one year.'
                          % (gk, C.fy(gy), C.usd(gap)), ['gap'], {'a': U(gap), 'y': F(gy)},
                          so='That year’s tab lists which of its requests those were.'),
            TP.conclusion('The most funded in one year was %s in %s: %s.' % (top[1], C.fy(top[2]), C.usd(top[0])),
                          ['top'], {'a': U(top[0]), 'y': F(top[2])},
                          so='That one year is %s of %s’ five-year funded total.' % (C.pct(share), top[1]),
                          so_figures={'s': P(share)})]
    return TB.claims(blk, cons, facts)


def sizes_block(R):
    """WHO GOT THE MOST, AND HOW BIG THEY ASKED (TJ, 20 November 2026: "which dept got the most
    funding ... esp including somehow based on their requests (do they not make a lot of big
    requests?!)"). A row per department, most funded first: every ranked request a dot on one
    dollar scale (log, so a $20,000 request and a $900,000 one both show), filled if funded; and
    beside it the five-year totals as a table. Request sizes are what the documents print; nothing
    here says why a request was or was not funded."""
    import statistics
    stats, figs = [], set()
    for k in DEPTS:
        x = [r for r in R if r['department'] == k]
        if not x:
            continue
        a = [r['amt'] for r in x]
        fu = sum(r['amt'] for r in x if r['ok'])
        stats.append(dict(k=k, n=len(x), fn=sum(r['ok'] for r in x), req=sum(a), fun=fu,
                          med=statistics.median(a), own=100 * fu / sum(a), x=x))
    allfun = sum(s['fun'] for s in stats)
    stats.sort(key=lambda s: -s['fun'])
    rows = []
    for s in stats:
        cells = dict(n_text='%s of %s' % (C.num(s['fn']), C.num(s['n'])), med_text=C.usd(s['med']),
                     req_text=C.usd(s['req']), fun_text=C.usd(s['fun']), own_text=C.pct(s['own'], 0),
                     share_text=C.pct(100 * s['fun'] / allfun, 0))
        figs |= set(cells.values()) | {C.num(s['fn']), C.num(s['n'])}
        dots = []
        for r in sorted(s['x'], key=lambda r: r['amt']):
            figs |= {C.usd(r['amt']), C.fy(r['fy'])}
            dots.append(dict(amt=r['amt'], ok=r['ok'], tip='%s, %s, %s' % (r['project'], C.fy(r['fy']), C.usd(r['amt']))))
        rows.append(dict(label=s['k'], dots=dots, **cells))
    ticks = [10000, 100000, 1000000]
    figs |= {C.usd(t) for t in ticks}
    data = dict(rows=rows, ticks=[dict(v=t, text=C.usd(t)) for t in ticks], text=dict(
        funded='Funded', unfunded='Not funded', dept='Department', dots='Each request, by its cost',
        n='Requests funded', med='Typical request (median)', req='Requested', fun='Funded',
        own='Of its own dollars', share='Of all funded'),
        line=dict(v=CAPITAL_LINE, text='The capital threshold, %s' % C.usd(CAPITAL_LINE)),
        note='%s to %s together, the requests on the committee’s ranked lists. The scale is logarithmic: each '
             'step is ten times the one before. Most funded first.' % (C.fy(YEARS[0]), C.fy(YEARS[-1])))
    figs |= {C.fy(YEARS[0]), C.fy(YEARS[-1]), C.usd(CAPITAL_LINE)}
    names = sorted({d['tip'] for r in rows for d in r['dots']})
    blk = TB.custom('capital-request-sizes', 'Who got the most, and how big they asked', data, place='body',
                    figures=sorted(figs), allow=names,
                    alt='For each department, every capital request as a dot on a dollar scale, filled if funded, '
                        'with the number funded, the median request, and the dollars requested and funded over five years.',
                    so='A row of dots shows whether a department requested a few large things or many small ones.')
    top, second = stats[0], stats[1]
    big = max(stats, key=lambda s: s['med'])
    most = max(stats, key=lambda s: s['n'])
    two = 100 * (top['fun'] + second['fun']) / allfun
    TOPN = 20                                 # "among the 20 largest": a cut of ours, stated in the line
    cut = sorted((r['amt'] for r in R), reverse=True)[TOPN - 1]
    inbig = sum(r['amt'] >= cut for r in big['x'])
    f = LD.fact
    facts = [f('top', U(top['fun']), '%s, funded in five years' % top['k'], 'published'),
             f('second', U(second['fun']), '%s, funded in five years' % second['k'], 'published'),
             f('bigmed', U(big['med']), '%s, median request' % big['k'], 'published'),
             f('bigown', figure(big['fn'], '%d of %d' % (big['fn'], big['n']), 'requests'),
               '%s requests funded' % big['k'], 'published'),
             f('most', N(most['n'], 'requests'), '%s, ranked requests in five years' % most['k'], 'published'),
             f('mostown', P(most['own']), '%s, share of its requested dollars funded' % most['k'], 'published'),
             f('mostmed', U(most['med']), '%s, median request' % most['k'], 'published')]
    cons = [TP.conclusion('%s received the most in five years, %s; %s next, %s.'
                          % (top['k'], C.usd(top['fun']), second['k'], C.usd(second['fun'])), ['top', 'second'],
                          {'a': U(top['fun']), 'b': U(second['fun'])},
                          so='Together, %s of every funded dollar in five years; the share column gives each department’s part.'
                             % C.pct(two), so_figures={'s': P(two)}),
            TP.conclusion('%s’s requests were large and funded: a median of %s, and %s funded.'
                          % (big['k'], C.usd(big['med']), '%d of %d' % (big['fn'], big['n'])), ['bigmed', 'bigown'],
                          {'a': U(big['med']), 'b': figure(big['fn'], '%d of %d' % (big['fn'], big['n']), 'requests')},
                          so='%s of its requests were among the %s largest of all %s on the lists.'
                             % (C.num(inbig), C.num(TOPN), C.num(len(R))),
                          so_figures={'a': N(inbig, 'requests'), 'b': N(TOPN, 'requests'), 'c': N(len(R), 'requests')}),
            TP.conclusion('%s made the most requests, %s, median %s; %s of its dollars were funded.'
                          % (most['k'], C.num(most['n']), C.usd(most['med']), C.pct(most['own'])),
                          ['most', 'mostmed', 'mostown'],
                          {'a': N(most['n'], 'requests'), 'b': U(most['med']), 'c': P(most['own'])},
                          so='Many smaller requests, and the lowest funded share of its own dollars of any department.'
                             if most['own'] == min(x['own'] for x in stats) else
                             'Many smaller requests, typically below the median of every other department.')]
    return TB.claims(blk, cons, facts)


def unranked_dept(u):
    """A never-ranked request's department, on the ranked list's own grouping: the project number's
    prefix where one is printed (extract_capital_rankings.PREFIX), else the department its source names."""
    from extract_capital_rankings import PREFIX
    if u['project_number']:
        for p, d in PREFIX:
            if u['project_number'].upper().startswith(p):
                return d
    n = u['department'].lower()
    for word, d in (('school', 'Schools'), ('police', 'Police'), ('fire', 'Fire'), ('public works', 'Public Works'),
                    ('highway', 'Public Works'), ('facilit', 'Facilities'), ('it', 'IT')):
        if n == word or (len(word) > 2 and word in n):
            return d
    return 'Department not printed' if not n else fail('no department for never-ranked %r' % u['department'])


def omnibus():
    """{fy: dollars} -- the omnibus budget Town Meeting voted, as /town-budgets reads it
    (scripts/build_town_budgets.py). A budget figure, like the capital it is set against (rule 1)."""
    p = os.path.join(ROOT, 'fy28', 'public', 'data', 'town-budgets.json')
    return {t['fy']: t['voted'] for t in json.load(open(p, encoding='utf-8'))['totals']}


def hub(R, UN):
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
    # TJ, 20 November 2026: "a total COUNT of requests per FY per dept, and a total amount requested,
    # and a total amount funded and a total amount funded by percent of the overall budget".
    D = drawn(UN)
    for u in D:
        u['dgroup'] = unranked_dept(u)
    crows = []
    for k in DEPTS + ['Department not printed']:
        ns = [(sum(r['department'] == k for r in R if r['fy'] == y), sum(u['dgroup'] == k for u in D if u['fy'] == y))
              for y in YEARS]
        if any(a or b for a, b in ns):
            crows.append(dict(label=k, cells=['%s ranked · %s never ranked' % (C.num(a), C.num(b)) for a, b in ns]))
    crows.append(dict(label='All departments', cells=[
        '%s ranked · %s never ranked' % (C.num(sum(r['fy'] == y for r in R)), C.num(sum(u['fy'] == y for u in D)))
        for y in YEARS]))
    omni = omnibus()
    srows = []
    for k in DEPTS:
        if any(k in st[y]['d'] for y in YEARS):
            srows.append(dict(label=k, cells=['—' if k not in st[y]['d'] else C.pct(st[y]['d'][k]['share_fun'], 0)
                                              for y in YEARS]))
    srows.append(dict(label='All capital funded, of the omnibus budget', cells=[
        '%s of %s · %s' % (C.usd(st[y]['fun']), C.usd(omni[y]), C.pct(100 * st[y]['fun'] / omni[y], 1))
        if y in omni else '%s · omnibus total not held' % C.usd(st[y]['fun']) for y in YEARS]))
    table = dict(caption='Each department, year by year', views=[
        dict(key='years', label='Funded of requested', kinds=['published'] * len(YEARS), columns=cols, rows=trows,
             note='Dollars funded of dollars requested, and the percent. Requests the committee ranked.'),
        dict(key='count', label='Number of requests', kinds=['published'] * len(YEARS), columns=cols, rows=crows,
             note='Requests on the committee’s ranked list, and requests made for that year it never ranked (found in '
                  'minutes, decks and recordings; at least that many, since the departments’ own lists are not held). '
                  'A never-ranked request is placed by its project number, or by the department the source names.'),
        dict(key='share', label='Share of what was funded', kinds=['published'] * len(YEARS), columns=cols, rows=srows,
             note='Each department’s share of the year’s funded capital dollars. The last row sets the year’s funded '
                  'capital against the omnibus budget Town Meeting voted for the same year (/town-budgets), both voted '
                  'budget figures.')])
    return TP.hub(
        HUB,
        'Five years of capital requests, each ranked by the Capital Planning Committee: between %s and %s '
        'of the dollars requested were funded, and in %s years the money did not follow the committee’s order.'
        % (C.pct(st[lo]['share']), C.pct(st[hi]['share']), C.num(len(out_order))),
        None, table=table, blocks=[thread_table_block(R, UN), yblk, bblk, dept_years_block(st), sizes_block(R), coverage_block(R)],
        answer_figures={'a': P(st[lo]['share']), 'b': P(st[hi]['share']), 'n': N(len(out_order), 'years')})


def build():
    R = load()
    UN = load_unranked()
    out = {HUB: hub(R, UN)}
    for y in YEARS:
        out['capital-fy%d' % y] = year_page(y, [r for r in R if r['fy'] == y], UN)
    # the years, one at a time, on their own page; the hub keeps what spans them (TJ, 20 Nov 2026)
    out['capital-years'] = TP.tabs_page(
        'capital-years', 'Each year’s requests, rankings and funding, one year at a time.',
        'Each fiscal year', ['capital-fy%d' % y for y in sorted(YEARS, reverse=True)])
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
