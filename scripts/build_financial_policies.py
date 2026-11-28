#!/usr/bin/env python3
"""FINANCIAL POLICIES: the Town's rules in force, the state's draft that would replace them, and
what each setting does to today's figures. Four topic pages and one markdown report.

    python3.11 scripts/build_financial_policies.py           # write the payloads and the report
    python3.11 scripts/build_financial_policies.py --check   # fail if any output would change

UNLISTED UNTIL TJ REVIEWS IT (27 November 2026). The four pages are registered on the New
financial policies shelf (scripts/topic_registry/financial_policies.py), served at
/financial-policies/<id>, under the hub the policy calculator draws (build_policy_calculator.py).
The shelf is `unlisted`: off /reports, the menu, search, the sitemap and the prerender until the
flag is deleted. The report is in sources/analyses/UNLISTED.

NO NEW COMPONENT: every part is an existing topic block or chart (matrix, bridge, series,
ranking, panels, timeline, checks, explain), so the bundle does not change and nothing forces a
full render (notes/plans/NO-FULL-RENDERS.md).

RULE 8. The project recommends neither direction -- neither saving more nor spending more. The
pages show what each setting would do to today's figures and stop there.

THE TWO DIALS. Every rule here turns one of two dials: MONEY IN (how much must be set aside, and
from where) and MONEY OUT (what a fund may pay for, and what vote spending it takes). The
signature matrix is those two dials, policy by policy: today's rule against the draft, with the
statute beside where the law sets a limit. Its verdicts are OUR reading of two documents and are
drawn as such.

Every figure is in financial_policies_data.py, which asserts each rule verbatim on the page that
prints it and refuses to write if two records of the same money disagree where they should not.
"""
import argparse
import csv
import io
import json
import os
import sys
from decimal import Decimal as D

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
import financial_policies_data as FP  # noqa: E402

HOME = 'financial-policies'   # the New financial policies shelf (topic_registry/financial_policies.py)
PAGES = {
    'financial-policy-rules': 'Financial policy rules',
    'policies-in-practice': 'The rules in practice',
    'retiree-health-liability': 'Retiree health liability',
    'financial-policy-debate': 'The policy debate',
}
TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
REPORT_ID = 'financial-policies'
REPORT = os.path.join(ROOT, 'sources', 'analyses', REPORT_ID + '.md')
RECORD = os.path.join(ROOT, 'sources', 'data', 'financial-policy-record.csv')

fl = float
U = lambda v: figure(fl(v), C.usd(v), 'dollars')
pc = lambda v, dp=2: C.pct(v, dp)
P = lambda v, dp=2: figure(fl(v), pc(v, dp), 'percent')
F = lambda y: figure(int(y), C.fy(y), 'fiscal year')
N = lambda n, unit: figure(n, C.num(n), unit)
Y = lambda y: figure(int(y), str(int(y)), 'year')
RULE = lambda v, text: figure(fl(v), text, 'percent')      # a rule's own figure, as printed


def path(pid):
    return '/%s/%s' % (HOME, pid)


def T(fmt, _allow=(), **figs):
    """A block's prose: (text, figures, allow). `fmt` names figures as {key}; `_allow` are literals."""
    return (fmt.format(**{k: v['text'] for k, v in figs.items()}), figs, tuple(_allow))


def L(text, *lits):
    """Prose whose only digits are literals quoted from a record (a date, a vote, a section)."""
    return (text, None, tuple(lits))


WORD = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten'}


def ordinal(n):
    return '%d%s' % (n, 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))



def inline(pid, flow, facts, cons, links=None):
    """CONCLUSIONS UNDER THE VISUAL THEY EXPLAIN, WITH A LINK WHERE ANOTHER PAGE HOLDS THE DETAIL.
    TJ, 27 November 2026: the four pages are linked "directly in the above sections when its related
    to whats there", not only in a list at the foot. A placed ('conclusion', i) is drawn without a
    link, so each one is attached to the block before it (topic_blocks.claims), which draws
    "Shown on <page>". page() does not re-check claims on a topic page, so rule 2 is checked here."""
    import brief
    links = links or {}
    bad = []
    for i, c in enumerate(cons):
        bad += brief.check_unit(c, '%s conclusion %d' % (pid, i + 1))
        if c.get('so'):
            bad += brief.check_unit(c['so'], '%s conclusion %d means' % (pid, i + 1))
    for f in facts:
        bad += brief.check_unit(f['label'], '%s fact %s label' % (pid, f['id']))
    if bad:
        FP.fail('\n  '.join(bad))
    by = {f['id']: f for f in facts}
    out, attach = [], {}
    last = None
    for x in flow:
        if isinstance(x, tuple) and x[0] == 'conclusion':
            if last is None:
                FP.fail('%s: conclusion %d has no block before it' % (pid, x[1] + 1))
            c = dict(cons[x[1]])
            if x[1] in links:
                c['link'] = dict(href=path(links[x[1]]), title=PAGES[links[x[1]]])
            attach.setdefault(last, []).append(c)
            continue
        if isinstance(x, dict) and 'cite' in x and isinstance(x['cite'], dict) and 'block' in x['cite']:
            last = len(out)
        out.append(x)
    for i, cs in attach.items():
        rested = [by[r] for r in dict.fromkeys(r for c in cs for r in c['rests_on'])]
        out[i] = dict(out[i], cite=TB.claims(out[i]['cite'], cs, rested))
    used = {r for cs in attach.values() for c in cs for r in c['rests_on']}
    if set(by) - used:
        FP.fail('%s: facts %s rest under no conclusion' % (pid, sorted(set(by) - used)))
    return out



def band(n, key, floor_name='The draft\u2019s floor', top_name='The draft\u2019s top'):
    """A target drawn as coloured lines in the chart's legend, not the grey reference line (TJ,
    27 November 2026: "the light gray is too subtle"). The colour is the renderer's palette, so the
    look changes with no new component. Values are FP.BANDS, asserted against the draft's words."""
    v = FP.BANDS[key]
    lo, hi = (v, None) if not isinstance(v, tuple) else v
    out = [TP.track(floor_name, [lo] * n, 'published', 'line', colour=3)]
    if hi is not None:
        out.append(TP.track(top_name, [hi] * n, 'published', 'line', colour=3))
    return out


# ------------------------------------------------------------------------------ sources

def src_manual(key='manual'):
    return dict(key=key, label='Division of Local Services, Town of Lunenburg Financial Policies Manual '
                '(draft, April 2024), pdf pages 21-47', href='/docs/' + FP.MANUAL)


def src_sb(key='today'):
    return dict(key=key, label='Select Board Policies and Procedures, Article III, sections 3.01-3.07 '
                '(the rules in force)', href='/docs/' + FP.SBPOL)


def src_law(k, label):
    return dict(key='law' + k, label=label, href=FP.LAW[k])


SRC_FACT = dict(key='factsheet', label='Town of Lunenburg, Free Cash Fact Sheet (FY27 warrant packet), '
                'certified free cash FY2016-FY2026',
                href='/docs/budget-workbooks/finance-committee/fy27-budget/tm-warrant/free-cash-fact-sheet.docx')
SRC_DLS_FC = dict(key='dlsfc', label='Division of Local Services, Municipal Databank: Certified Free Cash as a '
                  '% of the Budget (export of 25 November 2026)', href='/docs/' + FP.DLS_FC)
SRC_DLS_ST = dict(key='dlsst', label='Division of Local Services, Municipal Databank: Stabilization Fund '
                  'Balances as a % of Budget (export of 25 November 2026)', href='/docs/' + FP.DLS_STAB)
SRC_DLS_DEBT = dict(key='dlsdebt', label='Division of Local Services, Municipal Databank: General Fund Debt '
                    'Service as a % of Budget (export of 25 November 2026)', href='/docs/' + FP.DLS_DEBT)
SRC_AUDIT = dict(key='audit', label='Town of Lunenburg, FY2025 audited financial statements: fund balance '
                 '(pdf p. 67), stabilization note, OPEB schedules (pdf pp. 78-79)', href='/docs/' + FP.AUDIT)
SRC_AR25 = dict(key='ar25', label='Town of Lunenburg, FY2025 annual town report: trust fund balances at '
                '30 June 2025, unaudited (p. 30), and treasurer’s cash', href='/docs/' + FP.AR25)
SRC_ARS = dict(key='ars', label='Town annual reports, trust fund tables FY2017-FY2024, as extracted '
               '(general stabilization ending cash)', href='/docs/data/stabilization-balances.csv')
SRC_CAP = dict(key='capital', label='FY27 capital plan, ten-year funding table FY2017-FY2026',
               href='/docs/data/capital-funding-history.csv')


# ------------------------------------------------------------------------------ page 1

# WHICH KIND OF CHANGE EACH RULE IS (TJ, 27 November 2026: "i want to see the poilcies, and know if
# theya re changing targets or polices ... guidelines of behavior"). A TARGET is a level the town
# plans toward (a balance, a ceiling, a share of the budget); a GUIDELINE OF BEHAVIOR is how money is
# set aside or spent (a split, a deposit, a draw, a method). Our reading of the draft against today's
# rules, cell by cell of the matrix below; an absent cell is one the draft leaves as it is. Drawn as
# chips on the rules page and rolled up per policy on the hub, never on the calculator.
KIND_LABEL = {'target': 'Changes a target', 'guideline': 'Changes a guideline of behavior'}
KINDS = {
    (0, 0): ('target',), (0, 1): ('guideline',),
    (1, 0): ('target', 'guideline'), (1, 1): ('guideline',),
    (2, 0): ('target', 'guideline'),
    (4, 0): ('guideline',),
    (5, 0): ('guideline',),
    (6, 0): ('guideline',), (6, 1): ('target',),
    (7, 0): ('guideline',),
}
POLICY_ROWS = ['Free cash', 'General stabilization', 'Special purpose funds', 'Reserve fund',
               'Retiree health (OPEB)', 'Capital', 'Debt', 'Revenue estimates']


def row_kinds(r):
    return [k for k in ('target', 'guideline') if any(k in KINDS.get((r, c), ()) for c in (0, 1))]


def practice_measures(b):
    """TODAY IN PRACTICE, by cell of the rules matrix: the town's own figures beside the rule. Only
    where a figure is held; the rules page draws these under each rule and the hub draws them per
    policy (TJ, 27 November 2026: "we also need 'Today in practice'"), from this one function."""
    M, pub, est = TB.measure, 'published', 'estimate'
    import statistics
    fcp = b['fc_pct']
    yrs = sorted(fcp)
    sp25 = b['stab_pct'][2025]
    flows = json.load(io.open(os.path.join(ROOT, 'fy28', 'public', 'data', 'stabilization-funds.json'),
                              encoding='utf-8'))['flows']
    general_out = [x for x in flows['spends'] if 'opioid' not in x['subject'].lower()]
    gen_in = next(x for x in flows['by_fund'] if x['fund'] == 'Stabilization Fund (general)')
    cap25 = b['capital'][2025]['total']
    cap_share = cap25 / (b['budget25'] - D(str(b['debt25']))) * 100
    return {
        (0, 0): M('In practice', 'Latest %s; median %s since %s' % (
            pc(fcp[yrs[-1]]), pc(statistics.median(fcp.values())), C.fy(yrs[0])), est),
        (1, 0): M('In practice', '%s of the budget, %s' % (pc(sp25), C.fy(2025)), pub),
        (1, 1): M('In practice, Town Meeting votes held', 'No withdrawal, %s to %s' % (
            C.fy(flows['first_fy']), C.fy(flows['last_fy'])) if not general_out else
            '%d withdrawals' % len(general_out), est),
        (2, 0): M('In practice, all special funds', '%s of the budget, %s' % (pc(b['special25_pct']), C.fy(2025)), pub),
        (4, 0): M('In practice', '%s into the trust, %s' % (C.usd(b['opeb']['rows']['contrib'][2025]), C.fy(2025)), pub),
        (5, 0): M('In practice', '%s, %s net of debt, %s' % (C.usd(cap25), pc(cap_share), C.fy(2025)), est),
        (6, 1): M('In practice', '%s of the budget, all debt, %s' % (pc(b['peer_debt']['Lunenburg']), C.fy(2025)), pub),
    }


def dials_matrix(b):
    """The two dials, policy by policy. Verdicts are our reading of today's rule against the draft."""
    fs = '{fc}'
    rows = POLICY_ROWS
    cols = ['Money in: what is set aside', 'Money out: what may be spent, by what vote']
    R = ('reading', 'Our reading of both documents')
    W = ('law', 'Statute: M.G.L. c. 40, §5B')
    W6 = ('law', 'Statute: M.G.L. c. 40, §6')
    cells = {
        (0, 0): TB.cell('new', 'The draft sets a target for free cash itself', L(
            'Today: no target for free cash. Draft: certifications of five to seven percent of the budget '
            'each year, reached through conservative revenue estimates and budget turnbacks.'), R),
        (0, 1): TB.cell('more', 'The draft splits every year’s free cash by rule', L((
            'Today: top up general stabilization to five percent, then at least 10% to the OPEB trust, then '
            'the special purpose fund, then any one-time use. Draft: a minimum share for each of ' + WORD[len(FP.SPLIT)] + ' uses.'), '10%'), R),
        (1, 0): TB.cell('more', 'A wider band and a yearly deposit', L(
            'Today: at least five percent of the budget, all stabilization funds together no more than ten '
            'percent. Draft: five to eight percent, plus a set deposit every year.'), R),
        (1, 1): TB.cell('more', 'Harder to draw, sooner to refill', L(
            'Both: emergencies, ideally only above five percent, by a two-thirds vote. Draft adds: below it, '
            'take no more than one third, and refill within two years, not three.'), W),
        (2, 0): TB.cell('new', 'A target for the special funds together', L(
            'Today: a deposit sized in each year’s capital planning. Draft: three to five percent of the '
            'budget across the funds, and at least 10% of free cash.', '10%'), R),
        (2, 1): TB.cell('same', 'Town Meeting sets each fund’s purpose', L(
            'Today’s rule asks two thirds to spend from any stabilization fund. State law asks a majority '
            'for a special purpose fund. The draft sets no vote.'), W),
        (3, 0): TB.cell('none', 'The draft sets no size', L(
            'Today: $50,000, and no more than one half of one percent of the budget. The draft does not '
            'size the Finance Committee’s reserve fund at all.', '$50,000'), R),
        (3, 1): TB.cell('none', 'Transfers stay with the Finance Committee', L(
            'State law: up to five percent of last year’s levy, for extraordinary or unforeseen costs, '
            'transferred by the Finance Committee. The draft adds nothing.'), W6),
        (4, 0): TB.cell('more', 'Ten percent becomes a step toward full funding', L(
            'Today: at least 10% of certified free cash each year. Draft: keeps the 10% as one option, and '
            'states an intention to pay the full actuarially determined contribution.', '10%'), R),
        (4, 1): TB.cell('same', 'Current retirees stay on the budget', L(
            'Today: the trust does not pay current retirees, and moving money in or out takes a Town Meeting '
            'vote. The draft adds a valuation every two years.'), ('law', 'Statute: M.G.L. c. 32B, §20')),
        (5, 0): TB.cell('new', 'A yearly amount for capital in cash', L(
            'Today: a project is anything over $20,000; no spending level. Draft: two to three percent of '
            'the budget, net of debt, in cash each year, and 20% to 30% of free cash.', '$20,000', '20%', '30%'), R),
        (5, 1): TB.cell('same', 'Borrow only for large, long-lived projects', L(
            'Both: long-term debt only for projects over $100,000 with at least ten years of life.',
            '$100,000'), R),
        (6, 0): TB.cell('new', 'Maturing debt keeps its place in the budget', L(
            'Draft: when a non-excluded bond is paid off and not replaced, its yearly payment goes to a '
            'special purpose fund. Today’s rule has no such step.'), R),
        (6, 1): TB.cell('other', 'A different base for the limits', L(
            'Today: limits as a share of the tax levy (4% regular, 14% all). Draft: of the general fund '
            'budget (2% to 4% within the levy, 5% to 11% all, of operating revenues).',
            '4%', '14%', '2%', '5%', '11%'), R),
        (7, 0): TB.cell('new', 'Receipts capped at last year’s collections', L(
            'Today: no written rule. Draft: local receipts estimated at no more than 90% of last year’s '
            'collections without firm evidence, and each forecast checked against the year that followed.',
            '90%'), R),
        (7, 1): TB.cell('none', 'Not a spending rule', L(
            'The draft says estimates set too low leave excess revenue that cannot help the public in the '
            'year it comes in.'), R),
    }
    # THE BEFORE AND AFTER, AS CALLED-OUT METRICS (TJ, 27 November 2026: "put the before/after
    # metrics ... in bold called out metrics"). Each value is the rule's own figure as the document
    # prints it (asserted in financial_policies_data.py), so it is 'published'; the two dollar
    # amounts are the rules applied to the latest free cash, ours, so 'estimate'.
    pub, est = 'published', 'estimate'
    M = TB.measure
    claimed, fixed = C.usd(b['claimed']), C.usd(b['today_fixed'])
    MS = {
        (0, 0): [M('Today', 'No target', pub), M('Draft', '5% to 7% of the budget', pub)],
        (0, 1): [M('Today, on the latest free cash', fixed, est), M('Draft, on the same', claimed, est)],
        (1, 0): [M('Today', 'At least 5% of the budget', pub), M('Draft', '5% to 8%, plus 0.3% a year', pub)],
        (1, 1): [M('Today', 'Refill within 3 years', pub), M('Draft', 'At most a third; refill in 2', pub)],
        (2, 0): [M('Today', 'Set each year', pub), M('Draft', '3% to 5% of the budget', pub)],
        (2, 1): [M('Today', 'Two-thirds vote', pub), M('State law', 'Majority vote', pub)],
        (3, 0): [M('Today', '$50,000, at most 0.5%', pub), M('Draft', 'No size', pub)],
        (3, 1): [M('State law', 'Up to 5% of last year\u2019s levy', pub)],
        (4, 0): [M('Today', 'At least 10% of free cash', pub), M('Draft', '10%, aiming at the full contribution', pub)],
        (4, 1): [M('Today', 'No valuation schedule', pub), M('Draft', 'Valuation every 2 years', pub)],
        (5, 0): [M('Today', 'No yearly level', pub), M('Draft', '2% to 3% of the budget', pub)],
        (5, 1): [M('Both', 'Debt only over $100,000', pub)],
        (6, 0): [M('Today', 'No step', pub), M('Draft', 'Retired debt payment to savings', pub)],
        (6, 1): [M('Today', '4% and 14% of the levy', pub), M('Draft', '2% to 4% and 5% to 11%', pub)],
        (7, 0): [M('Today', 'No written rule', pub), M('Draft', 'At most 90% of last year', pub)],
    }
    # IN PRACTICE, beside the rule (TJ, 27 November 2026: "theres a difference in 'No policy today'
    # and the in-practice numbers"). Only where a figure is held; a cell with no compiled actual
    # (the reserve fund's yearly size, revenue estimates against collections) gets no line rather
    # than a guess. A share the state databank prints is 'published'; a share we compute, or a
    # reading of Town Meeting votes, is 'estimate'.
    practice = practice_measures(b)
    for k, m in practice.items():
        MS[k].append(m)
    for k, ms in MS.items():
        cells[k]['measures'] = ms
    for k, ks in KINDS.items():
        if cells[k]['verdict'] in ('same', 'none'):
            FP.fail('rules matrix: %s is classed as a change but its verdict is %r' % (k, cells[k]['verdict']))
        cells[k]['chips'] = [(KIND_LABEL[x], 'reading') for x in ks]
    for k, c in cells.items():
        if k not in KINDS and c['verdict'] not in ('same', 'none'):
            FP.fail('rules matrix: %s changes something and has no kind' % (k,))
    legend = [('new', 'Draft sets what today’s rules do not', 'other'),
              ('more', 'Draft sets more by rule', 'other'),
              ('same', 'Much the same', 'neutral'),
              ('other', 'Measured another way', 'neutral'),
              ('none', 'Draft is silent', 'muted')]
    m = TB.matrix('Two dials, policy by policy', rows, cols, cells, legend, place='lead',
                  row_label='Policy', col_label='Dial',
                  note=L('Money in is what is set aside before a budget is drawn up. Money out is what a '
                         'fund may pay for, and the vote it takes. The verdicts, and whether a change is to '
                         'a target or to a guideline of behavior, are our reading of the two documents.'))
    verdicts = [cells[(r, c)]['verdict'] for r in range(len(rows)) for c in range(2)]
    set_by_draft = sum(1 for v in verdicts if v in ('new', 'more'))
    on_in = sum(1 for r in range(len(rows)) if cells[(r, 0)]['verdict'] in ('new', 'more'))
    return m, set_by_draft, on_in, len(verdicts), len(rows)


def page_rules(b):
    pid = 'financial-policy-rules'
    fc, claimed, fixed = b['fc'], b['claimed'], b['today_fixed']
    share = claimed / fc * 100
    s26 = b['stab25']['report'] / b['budget26'] * 100
    sources = [SRC_FACT, src_manual(), src_sb(), src_law('5B', 'M.G.L. c. 40, §5B (stabilization funds)'),
               src_law('6', 'M.G.L. c. 40, §6 (reserve fund)'), src_law('32B', 'M.G.L. c. 32B, §20 (OPEB trust)'),
               SRC_DLS_ST, SRC_AUDIT, SRC_DLS_DEBT, SRC_CAP]
    m, set_by_draft, on_in, n_dials, n_rows = dials_matrix(b)

    steps = [(lab, -fl(a)) for _, lab, a in b['split']]
    bridge = TP.bridge('The draft’s minimums on the latest free cash', ('Certified free cash', fl(fc)),
                       steps, ('No set use', fl(b['unclaimed'])), '$',
                       note='Certified %s, available in %s. The capital share is a floor of 20%%.'
                            % (C.usd(fc), C.fy(b['latest'])),
                       note_figures={'a': U(fc), 'y': F(b['latest'])}, note_allow=('20%',))

    lo, hi = b['stab_deposit']
    rlo, rhi = b['reserves_band']
    clo, chi = b['capital_band']
    c25 = b['capital'][2025]['total']
    panels = TB.panels('More figures the draft would set', [
        TB.panel('Yearly stabilization deposit', [
            ('At the summary’s rate', C.usd(lo), None), ('At the text’s rate', C.usd(hi), None)],
            sub=(T('0.25% and 0.3% of the {y} budget of {b}.', y=F(2025), b=U(b['budget25']))[0],
                 {'y': F(2025), 'b': U(b['budget25'])}, ('0.25%', '0.3%'))),
        TB.panel('All reserves together', [
            ('The draft’s band', '%s to %s' % (C.usd(rlo), C.usd(rhi)), None),
            ('General fund balance, audited', C.usd(b['fund_balance']['total']), None)],
            sub=(T('13% to 20% of {b}; the audit counts {s} of stabilization inside the fund balance.',
                   b=U(b['fc_budget']), s=figure(6.3, '$6.3 million', 'dollars'))[0],
                 {'b': U(b['fc_budget']), 's': figure(6.3, '$6.3 million', 'dollars')}, ('13%', '20%'))),
        TB.panel('Cash capital each year', [
            ('The draft’s range', '%s to %s' % (C.usd(clo), C.usd(chi)), None),
            ('Capital funded that year', C.usd(c25), None)],
            sub=(T('2% to 3% of the {y} budget less {d} of general fund debt service.', y=F(2025), d=U(b['debt25']))[0],
                 {'y': F(2025), 'd': U(b['debt25'])}, ('2%', '3%'))),
    ], note=L('Each figure applies a draft percentage to a budget the town has already passed. The draft '
              'would apply it to the budget of the year in question.'),
        so=T('On these figures the town already holds more than the draft’s reserve band, and funded '
             'capital inside its cash range in {y}.', y=F(2025)))

    links = TB.explain('The rest of this report', [L(
        'How the reserves have moved against these targets, and where Lunenburg sits among peer towns; the '
        'retiree health liability; and the public argument, meeting by meeting.')], place='end', tone='plain',
        links=[(PAGES[k], path(k)) for k in PAGES if k != pid])
    practice_link = TB.explain('Each figure in practice, year by year', [L(
        'The in-practice lines above, drawn over the years against today\u2019s rule and the draft\u2019s.')],
        place='lead', tone='plain', links=[('The rules in practice', path('policies-in-practice'))])
    stance = TB.explain('What this page does not say', [L(
        'This project recommends neither direction: not to save more, and not to spend more. It shows what '
        'each setting would do to figures the town has already published. The boards decide.'),
        L('The draft itself says its targets are recommended for towns like Lunenburg, and that the town '
          'is to test them against its own finances before adopting them.')], place='lead', tone='define',
        links=[('Who has argued for each direction, meeting by meeting', path('financial-policy-debate'))])

    f = LD.fact
    facts = [
        f('dials', N(set_by_draft, 'dials'), 'dials of %d the draft sets by rule where today’s do not'
          % n_dials, 'estimate', label_figures={'n': N(n_dials, 'dials')}),
        f('fc', U(fc), 'certified free cash, available in %s' % C.fy(b['latest']), 'published',
          label_figures={'y': F(b['latest'])}),
        f('claimed', U(claimed), 'claimed by the draft’s minimum shares', 'estimate'),
        f('fixed', U(fixed), 'spoken for by today’s rules: the retiree health share', 'estimate'),
        f('s26', P(s26), 'general stabilization, as a share of the %s budget' % C.fy(2026), 'estimate',
          label_figures={'y': F(2026)}),
        f('lo', U(lo), 'deposit at the summary’s 0.25%', 'estimate', allow=('0.25%',)),
        f('hi', U(hi), 'deposit at the text’s 0.3%', 'estimate', allow=('0.3%',)),
    ]
    con = TP.conclusion
    cons = [
        con('The draft sets %s of %s dials by rule that today’s policies leave open or set lower.'
            % (C.num(set_by_draft), C.num(n_dials)), ['dials'],
            {'a': N(set_by_draft, 'dials'), 'b': N(n_dials, 'dials')},
            so='%s of the %s policies move on the money-in dial: more is set aside before a budget is drawn up.'
               % (C.num(on_in), C.num(n_rows)),
            so_figures={'a': N(on_in, 'policies'), 'b': N(n_rows, 'policies')}),
        con('The draft’s minimums claim %s of %s in free cash, %s of it.' % (C.usd(claimed), C.usd(fc), pc(share, 0)),
            ['fc', 'claimed'], {'a': U(claimed), 'b': U(fc), 'c': P(share, 0)},
            so='That leaves %s with no set use. Every point of a share moves %s.' % (C.usd(b['unclaimed']), C.usd(b['point'])),
            so_figures={'a': U(b['unclaimed']), 'b': U(b['point'])}),
        con('Today’s rules decide where only the retiree health share goes, %s; stabilization is at %s.'
            % (C.usd(fixed), pc(s26)), ['fixed', 's26'], {'a': U(fixed), 'b': P(s26)},
            so='Stabilization is above today’s five percent floor, so its first priority requires no deposit.'),
        con('The draft gives the yearly stabilization deposit as 0.25% in one place and 0.3% in another.',
            ['lo', 'hi'], allow=('0.25%', '0.3%'),
            so='On the %s budget the two readings are %s and %s a year.' % (C.fy(2025), C.usd(lo), C.usd(hi)),
            so_figures={'y': F(2025), 'a': U(lo), 'b': U(hi)}),
    ]
    cite = TP.cite
    flow = ['finding', cite(m, 'manual', 'today', 'law5B', 'law6', 'law32B'), ('conclusion', 0),
            cite(practice_link, 'dlsst'), cite(stance, 'manual'),
            cite(TB.chart(bridge, place='body', so=T('Under today’s rules only {x} of the same free cash is spoken '
                                                    'for; Town Meeting decides the rest.', x=U(fixed))),
                 'factsheet', 'manual'),
            ('conclusion', 1), ('conclusion', 2),
            cite(panels, 'manual', 'dlsst', 'audit', 'dlsdebt', 'capital'), ('conclusion', 3),
            cite(links, 'manual'), 'sources']
    sp = {k: a for k, _, a in b['split']}
    (keep, save, spend), _tot = C.footed([sp['keep'], sp['general'] + sp['special'] + sp['opeb'], sp['capital'] + sp['other']])
    if _tot != round(claimed):
        FP.fail('the three parts of the split do not foot to the claimed total')
    finding = 'Of %s in free cash, the draft would keep back %s, save %s and spend %s on set uses.' % (
        C.usd(fc), C.usd(keep), C.usd(save), C.usd(spend))
    page = TP.page(pid, finding, [], [], sources=sources,
                   finding_figures={'a': U(fc), 'b': U(keep), 'c': U(save), 'd': U(spend)},
                   flow=inline(pid, flow, facts, cons, {2: 'retiree-health-liability', 3: 'policies-in-practice'}))
    return page, dict(keep=keep, save=save, spend=spend, set_by_draft=set_by_draft, n_dials=n_dials, on_in=on_in, n_rows=n_rows, share=share, s26=s26)


# ------------------------------------------------------------------------------ page 2

def page_targets(b):
    pid = 'policies-in-practice'
    years = sorted(b['stab_pct'])
    sp = b['stab_pct']
    chart_s = TP.series('General stabilization, share of the budget', [C.fy(y) for y in years],
                        [TP.track('Lunenburg', [fl(sp[y]) for y in years])] + band(len(years), 'stab', 'Floor, today and the draft'),
                        '%', decimals=2, from_zero=True,
                        note='Year-end balance over that year’s operating budget, %s to %s.'
                             % (C.fy(years[0]), C.fy(years[-1])),
                        note_figures={'a': F(years[0]), 'b': F(years[-1])})
    fyears = sorted(b['fc_pct'])
    fp = b['fc_pct']
    chart_f = TP.series('Certified free cash, share of the budget', [C.fy(y) for y in fyears],
                        [TP.track('Lunenburg', [fl(fp[y]) for y in fyears])] + band(len(fyears), 'fc'), '%', decimals=2,
                        note='By the year it is available, over the year before’s budget, %s to %s.'
                             % (C.fy(fyears[0]), C.fy(fyears[-1])),
                        note_figures={'a': F(fyears[0]), 'b': F(fyears[-1])})
    in_range = [y for y in fyears if 5 <= fp[y] <= 7]
    above_since = min(y for y in years if all(sp[z] >= 5 for z in years if z >= y))

    rank = lambda d: sorted(d, key=lambda t: -d[t]).index('Lunenburg') + 1
    ps, pf, pd = b['peer_stab'], b['peer_fc'], b['peer_debt']
    rk_s, rk_f, rk_d = rank(ps), rank(pf), rank(pd)
    n = len(b['peers'])
    r_s = TP.ranking('General stabilization by town',
                     sorted([(t, fl(v)) for t, v in ps.items()], key=lambda r: -r[1]), '%', highlight='Lunenburg',
                     decimals=2, note='Share of each town’s own %s operating budget.' % C.fy(2025),
                     note_figures={'y': F(2025)})
    r_f = TP.ranking('Certified free cash by town', sorted([(t, fl(v)) for t, v in pf.items()], key=lambda r: -r[1]),
                     '%', highlight='Lunenburg', decimals=2,
                     note='Available in %s, over each town’s prior-year budget.' % C.fy(b['latest']),
                     note_figures={'y': F(b['latest'])})
    r_d = TP.ranking('General fund debt service by town', sorted([(t, fl(v)) for t, v in pd.items()], key=lambda r: -r[1]),
                     '%', highlight='Lunenburg', decimals=2,
                     note='%s, over each town’s total budget.' % C.fy(2025), note_figures={'y': F(2025)})

    s = b['stab25']
    diff = s['audit'] - s['report']
    db = b['draft_bal']
    two = TB.panels('One balance, two figures', [
        TB.panel('Annual town report', [('Fund balance at year-end', '$' + format(s['report'], ',.2f'), None)],
                 sub=L('Trust fund table, marked unaudited; the treasurer’s cash list prints the same figure.')),
        TB.panel('Audited statements', [('General stabilization at year-end', C.usd(s['audit']), None)],
                 sub=T('Higher by {d}; the state’s databank carries the annual report’s figure.', d=U(diff))),
    ], note=L('The chart uses the annual report’s figure, as the state’s databank does.', ),
        so=T('Nothing we hold reconciles the two; the share for {y} moves by under a fifth of a point either way.',
             y=F(2025)))
    draft_note = TB.explain('The draft’s own table', [T(
        'The draft prints a general stabilization balance for each year, and each is the balance at the '
        'previous 30 June: its {y} figure, {v}, is the {p} year-end.', _allow=('30',), y=F(2024), v=U(db[2024]), p=F(2023))],
        place='body', tone='plain')

    f = LD.fact
    facts = [
        f('s0', P(sp[years[0]]), 'general stabilization, %s' % C.fy(years[0]), 'published', label_figures={'y': F(years[0])}),
        f('s1', P(sp[years[-1]]), 'general stabilization, %s' % C.fy(years[-1]), 'published', label_figures={'y': F(years[-1])}),
        f('inr', figure(len(in_range), '%d of %d' % (len(in_range), len(fyears)), 'certifications'),
          'certifications inside the draft’s five to seven percent', 'published'),
        f('rks', figure(rk_s, '%s of %d' % (ordinal(rk_s), n), 'rank'), 'Lunenburg’s place for general stabilization, %s'
          % C.fy(2025), 'published', label_figures={'y': F(2025)}),
        f('rkf', figure(rk_f, '%s of %d' % (ordinal(rk_f), n), 'rank'), 'Lunenburg’s place for free cash, %s'
          % C.fy(b['latest']), 'published', label_figures={'y': F(b['latest'])}),
        f('fcl', P(fp[b['latest']]), 'free cash, share of the budget, %s' % C.fy(b['latest']), 'published',
          label_figures={'y': F(b['latest'])}),
    ]
    lo_t = min(ps, key=ps.get)
    hi_t = max(ps, key=ps.get)
    con = TP.conclusion
    cons = [
        con('General stabilization rose from %s of the budget in %s to %s in %s.'
            % (pc(sp[years[0]]), C.fy(years[0]), pc(sp[years[-1]]), C.fy(years[-1])), ['s0', 's1'],
            {'a': P(sp[years[0]]), 'y': F(years[0]), 'b': P(sp[years[-1]]), 'z': F(years[-1])},
            so='It has stayed above five percent since %s, so today’s first free cash priority has required no deposit.'
               % C.fy(above_since), so_figures={'y': F(above_since)}),
        con('Free cash landed inside the draft’s five to seven percent in %d of %d certifications.'
            % (len(in_range), len(fyears)), ['inr'],
            {'a': figure(len(in_range), '%d of %d' % (len(in_range), len(fyears)), 'certifications')},
            so='The draft would make that range a yearly aim, met through cautious revenue estimates.'),
        con('Lunenburg ranked %s of %d towns compared on general stabilization in %s.' % (ordinal(rk_s), n, C.fy(2025)),
            ['rks'], {'a': figure(rk_s, '%s of %d' % (ordinal(rk_s), n), 'rank'), 'y': F(2025)},
            so='The towns ran from %s in %s to %s in %s; the draft’s band sits inside that spread.'
               % (pc(ps[lo_t]), lo_t, pc(ps[hi_t]), hi_t),
            so_figures={'a': P(ps[lo_t]), 'b': P(ps[hi_t])}),
        con('Lunenburg’s latest free cash, %s of its budget, ranked %s of %d.'
            % (pc(fp[b['latest']]), ordinal(rk_f), n), ['fcl', 'rkf'],
            {'a': P(fp[b['latest']]), 'b': figure(rk_f, '%s of %d' % (ordinal(rk_f), n), 'rank')},
            so='The two certifications before it were %s and %s: high for Lunenburg, middling for the group.'
               % (pc(fp[b['latest'] - 2]), pc(fp[b['latest'] - 1])),
            so_figures={'a': P(fp[b['latest'] - 2]), 'b': P(fp[b['latest'] - 1])}),
    ]
    # THE OTHER DIALS IN PRACTICE (TJ, 27 November 2026: "we'll need charts to show the
    # in-practice realities too"). Each is drawn against the rule it sits beside in the matrix.
    st_all, dt_all, cap_all = FP.dls_stabilization(), FP.dls_debt(), b['capital']
    py = [y for y in range(FP.TREND_FROM, 2026)]
    bud = {y: D(str(st_all[('Lunenburg', y)]['budget'])) for y in py}
    spec = {y: D(str(st_all[('Lunenburg', y)]['special'])) / bud[y] * 100 for y in py}
    dsv = {y: D(str(dt_all[('Lunenburg', y)]['service'])) for y in py}
    debt_pct = {y: dsv[y] / D(str(dt_all[('Lunenburg', y)]['budget'])) * 100 for y in py}
    cap_pct = {y: cap_all[y]['total'] / (bud[y] - dsv[y]) * 100 for y in py if y in cap_all}
    xs = [C.fy(y) for y in py]
    span = {'a': F(py[0]), 'b': F(py[-1])}
    c_spec = TP.series('Special purpose stabilization, share of budget', xs,
                       [TP.track('Lunenburg', [fl(spec[y]) for y in py])] + band(len(py), 'special'), '%', decimals=2,
                       note='Every special fund the state counts, sewer funds included, %s to %s.' % (C.fy(py[0]), C.fy(py[-1])),
                       note_figures=span)
    c_cap = TP.series('Capital funded, share of budget less debt', [C.fy(y) for y in py if y in cap_pct],
                      [TP.track('Lunenburg', [fl(cap_pct[y]) for y in py if y in cap_pct])] + band(len(cap_pct), 'capital'),
                      '%', decimals=2,
                      note='Every source the capital plan lists, %s to %s; the draft counts cash only.' % (C.fy(py[0]), C.fy(py[-1])),
                      note_figures=span)
    c_debt = TP.series('General fund debt service, share of the budget', xs,
                       [TP.track('Lunenburg', [fl(debt_pct[y]) for y in py])] + band(len(py), 'debt_target', 'The draft\u2019s target, bottom',
                                                                   'The draft\u2019s target, top')
                       + [TP.track('The draft\u2019s ceiling', [FP.BANDS['debt_ceiling']] * len(py), 'published', 'line', colour=4)],
                       '%', decimals=2,
                       note='Voter-approved debt included. The draft measures against operating revenues.')
    fc_av = b['fact_sheet']
    oy = [y for y in py if y >= 2018]
    c_opeb = TP.series('Trust deposits against today\u2019s ten percent', [C.fy(y) for y in oy],
                       [TP.track('Deposited into the trust', [fl(b['opeb']['rows']['contrib'][y]) for y in oy], 'published', 'bar'),
                        TP.track('Ten percent of that year\u2019s free cash', [fl(fc_av[y][0] / 10) for y in oy], 'estimate', 'line')],
                       '$', kind='bar',
                       note='Free cash by the year it is available. Nothing held ties a deposit to one certification.')
    above_debt = [y for y in py if debt_pct[y] > FP.BANDS['debt_ceiling']]
    in_cap = [y for y in cap_pct if FP.BANDS['capital'][0] <= round(cap_pct[y], 2) <= FP.BANDS['capital'][1]]   # as printed, so 3.00% counts
    over10 = [y for y in oy if b['opeb']['rows']['contrib'][y] >= fc_av[y][0] / 10]
    import re as _re
    _pcts = _re.findall(r'Percentage to GF Budget ([\d.]+%) ([\d.]+%) ([\d.]+%) ([\d.]+%)', FP.manual_page(31))
    if len(_pcts) != 2:
        FP.fail('the draft\u2019s page 31 no longer prints two percentage rows')
    draft_spec = figure(float(_pcts[1][3].rstrip('%')), _pcts[1][3], 'percent')   # special funds, FY2024 column
    cite = TP.cite
    practice_parts = [
        cite(TB.chart(c_spec, place='body', so=T('The state\u2019s count rose from {a} to {b}; the draft\u2019s own table, '
                                                 'leaving out the sewer funds, put {c} at {d}.',
                                                 a=P(spec[py[0]]), b=P(spec[py[-1]]), c=F(2024),
                                                 d=draft_spec)), 'dlsst', 'manual'),
        cite(TB.chart(c_cap, place='body', so=T('Capital funded landed inside the draft\u2019s two to three percent in '
                                                '{n} years, counting every source.',
                                                n=figure(len(in_cap), '%d of %d' % (len(in_cap), len(cap_pct)), 'years'))),
             'capital', 'dlsst', 'dlsdebt'),
        cite(TB.chart(c_debt, place='body', so=T('Debt service was above the draft\u2019s ceiling in {n}; by {y} it was {p}.',
                                                 n=figure(len(above_debt), (C.fyspan(above_debt[0], above_debt[-1]) if len(above_debt) > 1 else C.fy(above_debt[0]))
                                                          if above_debt else 'no year', 'years'), y=F(py[-1]),
                                                 p=P(debt_pct[py[-1]]))), 'dlsdebt'),
        cite(TB.chart(c_opeb, place='body', so=T('The deposit met ten percent of that year\u2019s free cash in {n} years; '
                                                 'the timing between the two is not established.',
                                                 n=figure(len(over10), '%d of %d' % (len(over10), len(oy)), 'years'))),
             'audit', 'factsheet'),
    ]
    others = [t for t in sorted(b['peers']) if t != 'Lunenburg']
    peers_note = TB.explain('Which towns', [L(
        'The %s towns this project already compares on free cash: %s and %s. Each is measured against its '
        'own budget, by the state’s figures. This is where Lunenburg sits, not a ranking of better or worse.'
        % (WORD[len(others)], ', '.join(others[:-1]), others[-1]))], place='body', tone='define')
    cite = TP.cite
    flow = ['finding',
            cite(TB.chart(chart_s, place='lead', so=T('The draft’s band runs five to eight percent; {y} sits in it.',
                                                       y=F(years[-1]))), 'dlsst', 'ars'),
            ('conclusion', 0),
            cite(two, 'ar25', 'audit', 'dlsst'),
            cite(draft_note, 'manual', 'ars'),
            cite(TB.chart(chart_f, place='body', so=L('Free cash is what the year left over; a higher share leaves more for one-time uses and savings.')),
                 'factsheet', 'dlsfc'),
            ('conclusion', 1),
            *practice_parts,
            cite(peers_note, 'dlsst'),
            cite(TB.chart(r_s, place='body', so=L('Lunenburg sits in the middle of the group.')), 'dlsst'), ('conclusion', 2),
            cite(TB.chart(r_f, place='body', so=L('One year’s free cash moves with one year’s turnbacks and receipts.')),
                 'dlsfc'), ('conclusion', 3),
            cite(TB.chart(r_d, place='body', so=T('Lunenburg ranks {r} on debt service, a share that has been falling.',
                                                  r=figure(rk_d, '%s of %d' % (ordinal(rk_d), n), 'rank'))), 'dlsdebt'),
            'sources']
    sources = [SRC_DLS_ST, SRC_ARS, SRC_AR25, SRC_AUDIT, src_manual(), SRC_FACT, SRC_DLS_FC, SRC_DLS_DEBT, SRC_CAP]
    finding = 'General stabilization held %s of the %s budget; the draft’s range is five to eight percent.' % (
        pc(sp[years[-1]]), C.fy(years[-1]))
    page = TP.page(pid, finding, [], [], sources=sources,
                   finding_figures={'a': P(sp[years[-1]]), 'y': F(years[-1])},
                   flow=inline(pid, flow, facts, cons, {0: 'financial-policy-rules', 1: 'financial-policy-rules'}))
    return page, dict(in_range=in_range, fyears=fyears, rk_s=rk_s, rk_f=rk_f, rk_d=rk_d, n=n, above_since=above_since,
                      lo_t=lo_t, hi_t=hi_t, diff=diff)


# ------------------------------------------------------------------------------ page 3

def page_opeb(b):
    pid = 'retiree-health-liability'
    o = b['opeb']
    ys = o['years']
    R = o['rows']
    total, trust = R['total'], R['trust']
    grew = all(trust[ys[i]] > trust[ys[i - 1]] for i in range(1, len(ys)))
    if not grew:
        FP.fail('the trust did not grow every year; rewrite the first conclusion')
    swamped = [y for y in ys if abs(R['assumptions'][y]) > trust[y]]
    chart = TP.series('The liability and the trust', [C.fy(y) for y in ys],
                      [TP.track('Total liability', [fl(total[y]) for y in ys]),
                       TP.track('Held in the trust', [fl(trust[y]) for y in ys])], '$',
                      secondary=dict(name='Funded', values=[fl(o['funded'][y]) for y in ys], unit='%', decimals=2),
                      note='At each 30 June, %s to %s, as the audit’s schedule prints them.' % (C.fy(ys[0]), C.fy(ys[-1])),
                      note_figures={'a': F(ys[0]), 'b': F(ys[-1])}, note_allow=('30',))
    paid = TP.series('What the Town paid each year', [C.fy(y) for y in ys],
                     [TP.track('Current retirees’ health care', [fl(R['contrib_payg'][y]) for y in ys], 'published', 'bar'),
                      TP.track('Deposits into the trust', [fl(R['contrib'][y]) for y in ys], 'published', 'bar')],
                     '$', kind='bar', stacked=True, totals=True,
                     note='Employer contributions, %s to %s.' % (C.fy(ys[0]), C.fy(ys[-1])),
                     note_figures={'a': F(ys[0]), 'b': F(ys[-1])})
    fc10 = b['today_fixed']
    adc = TB.panels('The draft’s goal against the last year', [
        TB.panel('Actuarially determined contribution', [('The last year', C.usd(o['adc']), None)],
                 sub=L('What the actuary says would fund the promise over time.')),
        TB.panel('What the Town put in', [('Retirees and trust together', C.usd(o['contributed']), None)],
                 sub=L('Pay-as-you-go health care for current retirees, plus the trust deposit.')),
        TB.panel('The difference', [('Short of the contribution', C.usd(o['deficiency']), None),
                                    ('Today’s share of the latest free cash', C.usd(fc10), None)],
                 sub=L('The audit’s own schedule of contributions.')),
    ], so=T('Today’s ten percent of free cash covers about {s} of the difference.',
            s=P(fc10 / o['deficiency'] * 100, 0)))
    f = LD.fact
    facts = [
        f('trust', U(trust[ys[-1]]), 'held in the trust, 30 June 2025', 'published', allow=('30', '2025')),
        f('total', U(total[ys[-1]]), 'total retiree health liability, 30 June 2025', 'published', allow=('30', '2025')),
        f('payg', U(R['contrib_payg'][ys[-1]]), 'paid for current retirees, %s' % C.fy(ys[-1]), 'published',
          label_figures={'y': F(ys[-1])}),
        f('dep', U(R['contrib'][ys[-1]]), 'deposited into the trust, %s' % C.fy(ys[-1]), 'published',
          label_figures={'y': F(ys[-1])}),
        f('short', U(o['deficiency']), 'short of the actuarially determined contribution, %s' % C.fy(ys[-1]),
          'published', label_figures={'y': F(ys[-1])}),
        f('val', None, 'a valuation after the two held, 2017 and 2018', 'gap', allow=('2017', '2018'),
          closes='The Town’s most recent OPEB actuarial valuation report'),
    ]
    con = TP.conclusion
    cons = [
        con('The trust has grown every year since %s, to %s against a liability of %s.'
            % (C.fy(ys[0]), C.usd(trust[ys[-1]]), C.usd(total[ys[-1]])), ['trust', 'total'],
            {'y': F(ys[0]), 'a': U(trust[ys[-1]]), 'b': U(total[ys[-1]])},
            so='In %d of %d years, changed assumptions alone moved the liability by more than the trust held.'
               % (len(swamped), len(ys)),
            so_figures={'a': figure(len(swamped), '%d of %d' % (len(swamped), len(ys)), 'years')}),
        con('In %s the Town paid %s for current retirees and put %s into the trust.'
            % (C.fy(ys[-1]), C.usd(R['contrib_payg'][ys[-1]]), C.usd(R['contrib'][ys[-1]])), ['payg', 'dep'],
            {'y': F(ys[-1]), 'a': U(R['contrib_payg'][ys[-1]]), 'b': U(R['contrib'][ys[-1]])},
            so='Current retirees are paid from the budget each year; the trust is for those still working.'),
        con('Paying the full actuarially determined contribution would have taken %s more in %s.'
            % (C.usd(o['deficiency']), C.fy(ys[-1])), ['short'], {'a': U(o['deficiency']), 'y': F(ys[-1])},
            so='The draft names full funding as its intention; we find no date in it by which to reach it.'),
        con('The archive holds actuarial reports for 2017 and 2018; the draft sets one every two years.',
            ['val'], allow=('2017', '2018'),
            so='The audit carries the totals each year, but not the valuation behind them.'),
    ]
    cite = TP.cite
    flow = ['finding', cite(TB.chart(chart, place='lead', so=T('The trust covered {a} of the promise at the last count.',
                                                                 a=P(o['funded'][ys[-1]]))), 'audit'),
            ('conclusion', 0),
            cite(TB.chart(paid, place='body', so=L('Nearly all of what the Town pays goes to retirees now, not to the trust.')), 'audit'),
            ('conclusion', 1),
            cite(adc, 'audit', 'factsheet', 'manual'), ('conclusion', 2), ('conclusion', 3),
            cite(TB.explain('Why peer towns are not compared here', [L(
                'Many nearby towns send their pupils to regional school districts, which carry the teachers’ '
                'retiree health costs. Lunenburg carries its own school staff, so a funded share against those towns '
                'compares unlike liabilities.')], place='end', tone='plain'), 'audit'),
            'sources']
    sources = [SRC_AUDIT, SRC_FACT, src_manual(), src_sb()]
    sources[-1]['key'] = 'today'
    flow.insert(-1, cite(TB.explain('Today’s rule', [L(
        'Section 3.07, approved in January 2018: at least 10% of certified free cash to the trust each year; '
        'current retirees paid as they go.', '3.07', '2018', '10%')], place='end', tone='plain',
        links=[('Today\u2019s rule against the draft, policy by policy', path('financial-policy-rules'))]), 'today'))
    finding = 'At 30 June 2025 the retiree health trust held %s of a %s liability: %s funded.' % (
        C.usd(trust[ys[-1]]), C.usd(total[ys[-1]]), pc(o['funded'][ys[-1]]))
    page = TP.page(pid, finding, [], [], sources=sources,
                   finding_figures={'a': U(trust[ys[-1]]), 'b': U(total[ys[-1]]), 'c': P(o['funded'][ys[-1]])},
                   finding_allow=('30', '2025'), flow=inline(pid, flow, facts, cons, {2: 'financial-policy-rules'}))
    return page, dict(swamped=swamped)


# ------------------------------------------------------------------------------ page 4

def record():
    rows = list(csv.DictReader(io.open(RECORD, encoding='utf-8')))
    for r in rows:
        if r['evidence'] not in ('minutes', 'captions', 'both', 'agenda'):
            FP.fail('record %s: evidence %r' % (r['date'], r['evidence']))
        if r['thread'] not in ('rules', 'draft', 'argument') or r['dial'] not in ('in', 'out', 'none'):
            FP.fail('record %s: thread or dial' % r['date'])
    return rows


def agenda_titles():
    import re
    t = io.open(os.path.join(ROOT, 'sources', 'meetings', 'text', 'finance-committee', '2026-12-03-agenda-8154.txt'),
                encoding='utf-8').read()
    got = [x.strip() for x in re.findall(r'^\s*\d+\.\s+([A-Z][^\n]*?)\s*$', t.split('Financial Planning Policies')[1], re.M)]
    import pypdf
    r = pypdf.PdfReader(os.path.join(FP.SRC, FP.MANUAL))
    toc = r.pages[8].extract_text() + r.pages[9].extract_text()
    titles = [re.sub(r'\s*\.{3,}.*', '', l).strip() for l in toc.split('\n') if '....' in l]
    titles = [x for x in titles if x not in ('FINANCIAL PLANNING', 'FINANCIAL OPERATION', 'POLICY LOG')]
    canon = lambda s: s.upper().replace('OTHER POSTEMPLOYMENT BENEFITS', 'OPEB')
    if [canon(x) for x in got] != [canon(x) for x in titles]:
        FP.fail('the 3 December agenda titles no longer match the draft, title for title:\n%s\n%s' % (got, titles))
    return got


def page_debate(b):
    pid = 'financial-policy-debate'
    rows = record()
    titles = agenda_titles()
    years = list(range(2013, 2027))
    state = {}
    for r in rows:
        y = int(r['date'][:4])
        key = {'rules': 'rules', 'draft': 'draft'}.get(r['thread'])
        if r['thread'] == 'argument':
            key = 'in' if r['dial'] == 'in' else 'out' if r['dial'] == 'out' else 'said'
        state.setdefault(key, {})[y] = 'raised' if key in ('in', 'out') else key
    lab = lambda k: [state.get(k, {}).get(y) for y in years]
    timeline = TB.timeline('The rules and the argument, year by year', [str(y)[2:] if i else str(y) for i, y in enumerate(years)],
                           [('The rules', [TB.track('Today’s rules adopted or amended', lab('rules')),
                                           TB.track('The state’s draft before a board', lab('draft'))]),
                            ('The argument', [TB.track('Money in: how much to set aside', lab('in')),
                                              TB.track('Money out: what reserves may pay for', lab('out')),
                                              TB.track('The town’s reserves described', lab('said'))])],
                           [('rules', 'A vote on today’s rules', 'neutral'), ('draft', 'The draft discussed', 'other'),
                            ('raised', 'Raised at a meeting', 'other'),
                            ('said', 'Reported at a meeting', 'muted')],
                           place='lead', note=L('Each mark is a dated meeting in the list below; years run 2013 to 2026.',
                                                '2013', '2026'))
    long_date = lambda d: '%d %s %s' % (int(d[8:]), ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                                                       'August', 'September', 'October', 'November', 'December'][int(d[5:7]) - 1], d[:4])
    kind = {'minutes': 'minutes', 'captions': 'our machine captions only', 'both': 'minutes, part in captions only',
            'agenda': 'the agenda'}
    srcs, crow = [], []
    for i, r in enumerate(rows):
        key = 'm%d' % i
        srcs.append(dict(key=key, label='%s, %s: %s%s' % (r['board'], long_date(r['date']),
                                                            'video at ' if r['evidence'] == 'captions' else '',
                                                            r['where']), href=r['url']))
        import re
        why = '%s, %s (%s): %s' % (r['board'], long_date(r['date']), kind[r['evidence']], r['what'])
        crow.append(TB.check_row(('%s, %s' % (r['who'][0].upper() + r['who'][1:], long_date(r['date'])), None,
                                  tuple(re.findall(r'\d[\d,.]*', long_date(r['date'])))),
                                 (why, None, tuple(sorted(set(re.findall(r'\$?\d[\d,.]*%?', why))))),
                                 {'rules': {0}, 'draft': {1}, 'argument': {2}}[r['thread']],
                                 contrast=r['evidence'] == 'captions'))
    checks = TB.checks('Meeting by meeting', ['Today’s rules', 'The draft', 'The argument'], crow,
                       place='body', first='Who, when', second='What the record shows', tone='good',
                       note=L('A row drawn apart rests on our machine captions alone: a caption locates a moment, and '
                              'no figure heard in one is given here.'),
                       so=L('Arguments on both dials have been made for years; the draft has been before the boards '
                            'since June 2024 without a vote on it.', '2024'))
    n_cap = sum(1 for r in rows if r['evidence'] == 'captions')
    f = LD.fact
    facts = [
        f('titles', N(len(titles), 'titles'), 'policy titles on the 3 December 2026 agenda', 'published',
          allow=('3', '2026')),
        f('nodraft', None, 'the draft text the committee will review', 'gap',
          closes='The draft policies as attached to the Finance Committee’s 3 December 2026 packet'),
        f('rows', N(len(rows), 'meetings'), 'dated meetings in the record below', 'published'),
        f('cap', N(n_cap, 'meetings'), 'of them heard only in our machine captions', 'published'),
    ]
    con = TP.conclusion
    cons = [
        con('The %d titles on the 3 December 2026 agenda match the April 2024 draft’s, title for title.' % len(titles),
            ['titles', 'nodraft'], {'a': N(len(titles), 'titles')}, allow=('3', '2026', '2024'),
            so='No policy text is attached, so whether the draft has been edited since is not established.'),
        con('%d of the %d dated meetings here are known only from our machine captions.' % (n_cap, len(rows)),
            ['rows', 'cap'], {'a': N(n_cap, 'meetings'), 'b': N(len(rows), 'meetings')},
            so='Those mark where something was said; the minutes, where they exist, are what the town recorded.'),
    ]
    cite = TP.cite
    allkeys = [s['key'] for s in srcs]
    flow = ['finding', cite(timeline, *allkeys[:1] + allkeys[1:]), ('conclusion', 0),
            cite(checks, *allkeys), ('conclusion', 1), 'sources']
    sources = srcs
    finding = 'The town’s financial policies date from 2014; the state’s replacement draft has waited since June 2024.'
    page = TP.page(pid, finding, [], [], sources=sources, finding_allow=('2014', '2024'),
                   flow=inline(pid, flow, facts, cons, {0: 'financial-policy-rules'}))
    return page, dict(titles=titles, n_cap=n_cap, n_rows=len(rows), rows=rows)


# ------------------------------------------------------------------------- the hub's policy list

# WHAT THE MEETING RECORD SHOWS, per policy: rows of financial-policy-record.csv by date and board,
# each restated short. Every date is asserted present in the record with that board, so the hub
# cites only meetings the debate page lists. A policy no meeting raises says so (TJ, 27 November
# 2026: "im confused why the finance committee might be concerned"): the record shows WHAT was said,
# and no line here says why anybody holds a view (rule 7).
RECORD_BY_POLICY = {
    'Free cash': [('2018-08-23', 'Finance Committee', 'voted 6-0 to recommend a change to the free cash policy', ('6-0',)),
                  ('2026-03-16', 'Select Board', 'the Town Manager cautioned that less free cash will be generated', ())],
    'General stabilization': [('2025-04-03', 'Finance Committee', 'voted 6-0 to take no action on free cash to it', ('6-0',)),
                              ('2026-04-14', 'Select Board', 'a resident questioned adding to reserves while schools face cuts', ())],
    'Special purpose funds': [('2025-04-03', 'Finance Committee', 'voted 6-0 to take no action on free cash to them', ('6-0',))],
    'Reserve fund': [('2025-04-03', 'Finance Committee', 'in public comment, called an account for emergencies, not a piggy bank', ()),
                     ('2026-05-28', 'Finance Committee', 'a larger reserve fund raised, in our captions only', ())],
    'Retiree health (OPEB)': [('2018-01-02', 'Board of Selectmen', 'approved today’s 10% funding policy', ('10%',))],
    'Capital': [('2026-10-22', 'Finance Committee', 'in public comment, the capital planning process called unwieldy and undemocratic, in our captions only', ())],
    'Debt': [],
    'Revenue estimates': [('2024-09-12', 'Finance Committee', 'receipts said to be estimated well below collections, in our captions only', ()),
                          ('2026-05-28', 'Finance Committee', 'local receipts said not to have come in under $4 million in ten years', ('$4',))],
}
# The Town Manager's goal of 14 July 2026 names four policies to adopt by December (the record's own words:
# "OPEB, stabilization and reserves, free cash, and revenue projections").
JULY_GOAL = ('2026-07-14', 'Select Board', ('OPEB', 'stabilization and reserves', 'free cash', 'revenue projections'))
ON_JULY_LIST = {'Free cash', 'General stabilization', 'Special purpose funds', 'Reserve fund',
                'Retiree health (OPEB)', 'Revenue estimates'}


def _long(d):
    return '%d %s %s' % (int(d[8:]), ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                      'September', 'October', 'November', 'December'][int(d[5:7]) - 1], d[:4])


def policy_list(b):
    """THE HUB'S POLICY LIST: every policy area, which kind of change the draft makes to it, what that
    would change in the next budget, and what the meeting record shows. Returns the matrix with its
    conclusion attached (topic_blocks.claims)."""
    rec = record()
    have = {(r['date'], r['board']) for r in rec}
    for pol, xs in RECORD_BY_POLICY.items():
        for d, board, _, _ in xs:
            if (d, board) not in have:
                FP.fail('policy list: %s cites %s %s, which is not in the meeting record' % (pol, board, d))
    jr = [r for r in rec if (r['date'], r['board']) == JULY_GOAL[:2]]
    if len(jr) != 1 or not all(x in jr[0]['what'] for x in JULY_GOAL[2]):
        FP.fail('policy list: the July 2026 goal no longer names the four policies')
    if set(RECORD_BY_POLICY) != set(POLICY_ROWS):
        FP.fail('policy list: the record map and the policy rows differ')

    fc, claimed, fixed = b['fc'], b['claimed'], b['today_fixed']
    sp = dict((k, v) for k, _, v in b['split'])
    dep_lo, dep_hi = b['stab_deposit']
    cap_lo, cap_hi = b['capital_band']
    cap25 = b['capital'][2025]['total']
    debt = b['peer_debt']['Lunenburg']
    sbl, sbh = FP.BANDS['stab']
    spl, sph = FP.BANDS['special']
    dtl, dth = FP.BANDS['debt_target']
    dc = FP.BANDS['debt_ceiling']
    if not sbl <= b['stab_pct'][2025] <= sbh or not b['special25_pct'] > sph or not cap_lo <= cap25 <= cap_hi \
            or not dtl <= debt <= dth:
        FP.fail('policy list: a "next budget" line no longer describes where the balance sits; rewrite it')
    if sp['opeb'] != fixed:
        FP.fail('policy list: today and the draft no longer put the same sum in the OPEB trust')
    R = lambda v: RULE(v, '%s%%' % v)
    fy25 = F(2025)
    # What each rule set would change in the next budget, from the model (rule 2).
    nxt = {
        'Free cash': ('moves', T('On the latest {fc} of free cash, the draft’s floors assign {c} before Town Meeting; '
                                 'today’s rules assign {f}.', fc=U(fc), c=U(claimed), f=U(fixed))),
        'General stabilization': ('moves', T('The draft adds {g} from free cash and a yearly deposit printed as {lo} or '
                                             '{hi}; the balance, {p} of the budget in {y}, is inside its band.',
                                             g=U(sp['general']), lo=U(dep_lo), hi=U(dep_hi), p=P(b['stab_pct'][2025]), y=fy25)),
        'Special purpose funds': ('moves', T('The draft asks at least {s} of free cash, though the funds stood at {p} of '
                                             'the budget in {y}, above its top of {t}.', s=U(sp['special']),
                                             p=P(b['special25_pct']), y=fy25, t=R(sph))),
        'Reserve fund': ('quiet', L('The draft sets nothing here, so it would change nothing in the next budget on its own.')),
        'Retiree health (OPEB)': ('moves', T('Either rule set puts {o} of free cash in the trust; the full actuarial '
                                             'contribution the draft aims at is not in the documents held here.', o=U(sp['opeb']))),
        'Capital': ('measures', T('The draft’s level is {lo} to {hi} a year in cash; {y}’s capital plan funded {c}, inside it.',
                                  lo=U(cap_lo), hi=U(cap_hi), y=fy25, c=U(cap25))),
        'Debt': ('measures', T('Debt service was {d} of the {y} budget by the state’s measure, inside the draft’s target of {a} to {z} and its '
                               'ceiling of {c}.', d=P(debt), y=fy25, a=R(dtl), z=R(dth), c=R(dc))),
        'Revenue estimates': ('unheld', L('A lower estimate leaves more to fall to free cash a year later; the town’s '
                                          'estimates against collections are not compiled here.')),
    }
    rec_text = {}
    for pol in POLICY_ROWS:
        parts, lits = [], []
        for d, board, what, lit in RECORD_BY_POLICY[pol]:
            parts.append('%s, %s: %s.' % (board, _long(d), what))
            lits += [_long(d).split(' ')[0], d[:4]] + list(lit)
        if pol in ON_JULY_LIST:
            parts.append('Named in the Town Manager’s July 2026 goal.')
            lits += ['2026']
        rec_text[pol] = ('raised', ' '.join(parts), tuple(dict.fromkeys(lits))) if RECORD_BY_POLICY[pol] else \
            ('unraised', ' '.join(parts) or 'No meeting in the record raises it.', tuple(dict.fromkeys(lits)))
    # Today's rule beside the draft's, in a line, per policy: the kind it is, and both rules.
    rule_line = {
        'Free cash': L('Target: free cash of five to seven percent of the budget; today there is none. Guideline: a '
                       'minimum share for each of six uses, where today’s rules set a priority order.'),
        'General stabilization': L('Target: five to eight percent of the budget, where today’s floor is five. '
                                   'Guideline: a yearly deposit, and a draw of at most a third, refilled in two years, not three.'),
        'Special purpose funds': L('Target: three to five percent of the budget across the funds; today there is none. '
                                   'Guideline: at least 10% of free cash, where today the deposit is set in capital planning.', '10%'),
        'Reserve fund': L('Today: $50,000, and no more than one half of one percent of the budget. The draft sets no '
                          'size and adds nothing on how it is spent.', '$50,000'),
        'Retiree health (OPEB)': L('Today: at least 10% of free cash to the trust. Guideline: the draft keeps that as one '
                                   'option, aims at the full actuarial contribution, and values the liability every two years.', '10%'),
        'Capital': L('Today: no yearly level for capital in cash. Guideline: two to three percent of the budget, net of '
                     'debt, each year, and 20% to 30% of free cash.', '20%', '30%'),
        'Debt': L('Target: limits as a share of the budget (2% to 4% within the levy, 5% to 11% all) instead of the '
                  'levy (4% and 14%). Guideline: a retired bond’s payment goes to savings.',
                  '2%', '4%', '5%', '11%', '14%'),
        'Revenue estimates': L('Today: no written rule. Guideline: local receipts estimated at no more than 90% of last '
                               'year’s collections without firm evidence, each forecast checked afterwards.', '90%'),
    }
    # TODAY IN PRACTICE: the rules page's own in-practice figures, per policy, with a line saying what
    # each is measured against. A policy with none compiled says so (rule 7c).
    pm = practice_measures(b)
    flows = json.load(io.open(os.path.join(ROOT, 'fy28', 'public', 'data', 'stabilization-funds.json'),
                              encoding='utf-8'))['flows']
    if [x for x in flows['spends'] if 'opioid' not in x['subject'].lower()] or not b['stab_pct'][2025] > sbl \
            or not b['special25_pct'] > sph:
        FP.fail('policy list: a "today in practice" line no longer describes the figures; rewrite it')
    practice_line = {
        'Free cash': L('Today’s rules set no target, so these are the certifications as they came.'),
        'General stabilization': L('Above today’s five percent floor, with no withdrawal voted in the years held.'),
        'Special purpose funds': L('Above the draft’s top of five percent; today’s rules set no level for them.'),
        'Reserve fund': L('How large the fund was each year, and what it paid for, are not compiled here.'),
        'Retiree health (OPEB)': L('Paid into the trust that year, from every source the statements count.'),
        'Capital': L('Today’s rules set no level; measured net of debt, as the draft measures it.'),
        'Debt': L('By the state databank’s measure, all debt, against the total budget.'),
        'Revenue estimates': L('The town’s estimates against its collections, year by year, are not compiled here.'),
    }
    gap_value = {'Reserve fund': 'Yearly size not compiled', 'Revenue estimates': 'Estimates against collections'}
    title = {('target', 'guideline'): 'A target and a guideline', ('target',): 'A target',
             ('guideline',): 'A guideline of behavior', (): 'Neither'}
    kind_key = {('target', 'guideline'): 'both', ('target',): 'target', ('guideline',): 'guideline', (): 'neither'}
    reading = ('reading', 'Our reading of both documents')
    cells = {}
    for r, pol in enumerate(POLICY_ROWS):
        ks = tuple(row_kinds(r))
        cells[(r, 0)] = TB.cell(kind_key[ks], title[ks], rule_line[pol], reading)
        ms = [pm[(r, c)] for c in (0, 1) if (r, c) in pm]
        if bool(ms) == (pol in gap_value):
            FP.fail('policy list: %s in practice: figures and the gap list disagree' % pol)
        cells[(r, 1)] = TB.cell('held' if ms else 'notheld', 'Today in practice' if ms else 'Not compiled',
                                practice_line[pol], ('record', 'The town’s own figures') if ms
                                else ('reading', 'Gap in what is held'),
                                measures=ms or [TB.measure('In practice', gap_value[pol], 'gap')])
        v, why = nxt[pol]
        cells[(r, 2)] = TB.cell(v, {'moves': 'Moves dollars', 'measures': 'Sets a level', 'quiet': 'No change',
                                    'unheld': 'Not measured here'}[v], why,
                                ('reading', 'Our estimate, the rules applied to published figures'))
        v, text, lits = rec_text[pol]
        cells[(r, 3)] = TB.cell(v, {'raised': 'Raised at meetings', 'unraised': 'Not raised'}[v], (text, None, lits),
                                ('record', 'Meeting record, on the debate page'))
    legend = [('both', 'Changes a target and a guideline', 'other'),
              ('target', 'Changes a target', 'other'),
              ('guideline', 'Changes a guideline of behavior', 'other'),
              ('neither', 'Draft changes neither', 'muted'),
              ('held', 'Today, from the town’s own figures', 'neutral'),
              ('notheld', 'Not compiled here', 'muted'),
              ('moves', 'Would move dollars in the next budget', 'neutral'),
              ('measures', 'Sets a level the budget is measured against', 'neutral'),
              ('quiet', 'No change to the next budget', 'muted'),
              ('unheld', 'Effect not measured here', 'muted'),
              ('raised', 'Raised at a meeting in the record', 'neutral'),
              ('unraised', 'No meeting in the record raises it', 'muted')]
    m = TB.matrix('Every policy, and what it changes', POLICY_ROWS,
                  ['What the draft changes', 'Today in practice', 'In the next budget', 'In the meeting record'], cells, legend,
                  place='body', row_label='Policy', col_label='',
                  note=L('A target is a level the town plans toward; a guideline of behavior is how money is set '
                         'aside or spent. Which is which is our reading. Dollars apply each rule to the latest '
                         'published figures.'))
    n = len(POLICY_ROWS)
    n_t = sum(1 for r in range(n) if 'target' in row_kinds(r))
    n_g = sum(1 for r in range(n) if 'guideline' in row_kinds(r))
    left = [POLICY_ROWS[r] for r in range(n) if not row_kinds(r)]
    if left != ['Reserve fund']:
        FP.fail('policy list: the conclusion names the reserve fund as the one left alone; it no longer is')
    n_raised = sum(1 for p in POLICY_ROWS if RECORD_BY_POLICY[p])
    f = LD.fact
    Nn = lambda x: N(x, 'policy areas')
    facts = [f('guide', Nn(n_g), 'policy areas whose guideline of behavior the draft changes', 'estimate'),
             f('target', Nn(n_t), 'policy areas whose target the draft changes', 'estimate'),
             f('raised', Nn(n_raised), 'policy areas raised at a meeting in the record', 'published')]
    cons = [TP.conclusion('The draft changes a guideline in %d of %d policy areas and a target in %d; it leaves the '
                          'reserve fund alone.' % (n_g, n, n_t), ['guide', 'target'],
                          {'a': Nn(n_g), 'b': Nn(n), 'c': Nn(n_t)},
                          so='Most of the draft is about how money is set aside and spent, more than the levels it reaches.'),
            TP.conclusion('%d of the %d have been raised at a meeting in the record; debt is the one that has not.'
                          % (n_raised, n), ['raised'], {'a': Nn(n_raised), 'b': Nn(n)},
                          so='The record shows what was said at each meeting; it does not show why anybody holds a view.')]
    if n - n_raised != 1 or RECORD_BY_POLICY['Debt']:
        FP.fail('policy list: the second conclusion names debt as the one not raised; it no longer is')
    import brief
    bad = []
    for i, c in enumerate(cons):
        bad += brief.check_unit(c, 'policy list conclusion %d' % (i + 1)) + brief.check_unit(c['so'], 'policy list means %d' % (i + 1))
    for x in facts:
        bad += brief.check_unit(x['label'], 'policy list fact %s' % x['id'])
    if bad:
        FP.fail('\n  '.join(bad))
    return TB.claims(m, cons, facts)


# ------------------------------------------------------------------- already where the draft wants it

def already_there(b):
    """WHAT IS ALREADY AT THE DRAFT'S LEVEL, AND WHAT KEEPS IT THERE (TJ, 28 November 2026: "show what
    things already are at the balance And that and within range but need to be put into a policy").
    Each level the draft sets, against the town's latest figure, and whether a rule of today's holds it.
    A balance already above a level is a flag, not a failure: no budget setting can lower a balance."""
    sbl, sbh = FP.BANDS['stab']
    spl, sph = FP.BANDS['special']
    fcl, fch = FP.BANDS['fc']
    dtl, dth = FP.BANDS['debt_target']
    cap_lo, cap_hi = b['capital_band']
    g, sp_, fcp = b['stab_pct'][2025], b['special25_pct'], b['fc_pct'][b['latest']]
    cap, debt = b['capital'][2025]['total'], b['peer_debt']['Lunenburg']
    fy25, fyl = F(2025), F(b['latest'])
    R = lambda v: RULE(v, '%s%%' % v)
    # (label, the town's figure inside the draft's level, above its top, held by today's rule, why)
    rows = [
        ('General stabilization', sbl <= g <= sbh, g > sbh, g >= FP.BANDS['stab_today'],
         T('{p} of the budget in {y}; the draft asks {a} to {z}. Today’s five percent floor holds the bottom.',
           p=P(g), y=fy25, a=R(sbl), z=R(sbh))),
        ('Special purpose funds', spl <= sp_ <= sph, sp_ > sph, False,
         T('{p} of the budget in {y}, above the draft’s {a} to {z}; no rule today sets a level for them.',
           p=P(sp_), y=fy25, a=R(spl), z=R(sph))),
        ('Free cash', fcl <= fcp <= fch, fcp > fch, False,
         T('The {y} certification was {p} of the budget; the draft aims at {a} to {z}. Today sets no target.',
           p=P(fcp), y=fyl, a=R(fcl), z=R(fch))),
        ('Capital in cash', cap_lo <= cap <= cap_hi, cap > cap_hi, False,
         T('{y}’s plan funded {c}, inside the draft’s {a} to {z}. Today sets no yearly level.',
           c=U(cap), y=fy25, a=U(cap_lo), z=U(cap_hi))),
        ('Debt service', dtl <= debt <= dth, debt > dth, False,
         T('{p} of the {y} budget, inside the draft’s {a} to {z}; today’s limits are on the levy, not the budget.',
           p=P(debt), y=fy25, a=R(dtl), z=R(dth))),
    ]
    if any(not (inn or above) for _, inn, above, _, _ in rows):
        FP.fail('already there: a level is no longer met; this block lists only levels already met, rewrite it')
    blk = TB.checks('Already at the draft’s level',
                    ['Within the draft’s level', 'Above its top', 'Held there by a rule today'],
                    [dict(label=lab, why=why, contrast=False,
                          marks=[i for i, on in enumerate((inn, above, held)) if on])
                     for lab, inn, above, held, why in rows],
                    place='body', tone='good', first='Level', second='Where it stands',
                    column_notes=[L('The town’s latest figure sits inside the range the draft sets.'),
                                  L('Above the top of the draft’s range: a balance no budget setting lowers. The draft’s '
                                    'stabilization ranges are minimums, so above is not short of it.'),
                                  L('A rule the town has adopted today keeps it at that level.')],
                    note=L('Latest year held for each. Which rule holds a level is our reading of both documents.'))
    n = len(rows)
    n_held = sum(1 for r in rows if r[3])
    f = LD.fact
    Nn = lambda x: N(x, 'levels')
    facts = [f('met', Nn(n), 'levels the town already meets in the draft’s terms', 'estimate'),
             f('held', Nn(n_held), 'of them held there by a rule of today’s', 'estimate')]
    if n_held != 1:
        FP.fail('already there: the conclusion says one level is held by today\'s rules; it no longer is')
    cons = [TP.conclusion('All %d of these levels are already met; a rule of today’s holds only %d of them.'
                          % (n, n_held), ['met', 'held'], {'a': Nn(n), 'b': Nn(n_held)},
                          so='Adopting the draft would write down levels the town already reaches; '
                             'today no adopted rule keeps the others there.')]
    import brief
    bad = []
    for i, c in enumerate(cons):
        bad += brief.check_unit(c, 'already there conclusion %d' % (i + 1)) + brief.check_unit(c['so'], 'already there means %d' % (i + 1))
    if bad:
        FP.fail('\n  '.join(bad))
    return TB.claims(blk, cons, facts)


# ------------------------------------------------------------------------------ the report

def report(b, x1, x2, x3, x4):
    """The markdown twin: what /docs serves, the PDF is made from, and an agent without JavaScript
    reads. Every figure comes from the same build() the pages use."""
    o = b['opeb']
    s = b['stab25']
    L_ = []
    a = L_.append
    a('# Financial policies: the rules, the draft, and the figures\n')
    a('*An analysis written by this project. Unlisted while it is reviewed. Built by '
      '`scripts/build_financial_policies.py`; every figure is recomputed by `scripts/verify_financial_policies.py`.*\n')
    a('## The short version\n')
    a('- On the latest certified free cash, **%s** (certified %s, available in %s), the state’s draft policies '
      'would keep back **%s**, save **%s** and spend **%s** on set uses: **%s** in all, %s of it. Today’s rules decide '
      'one share: **%s** to the retiree health trust. Each point of a share is worth %s.' % (
          C.usd(b['fc']), b['fc_date'], C.fy(b['latest']), C.usd(x1['keep']), C.usd(x1['save']), C.usd(x1['spend']),
          C.usd(b['claimed']), pc(x1['share'], 0), C.usd(b['today_fixed']), C.usd(b['point'])))
    a('- The draft sets **%d of %d** dials by rule that today’s policies leave open or set lower (our reading of '
      'the two documents).' % (x1['set_by_draft'], x1['n_dials']))
    a('- General stabilization was **%s** of the %s budget, inside the draft’s five to eight percent, and %s of %d '
      'among the towns compared.' % (pc(b['stab_pct'][2025]), C.fy(2025), ordinal(x2['rk_s']), x2['n']))
    a('- The retiree health trust held **%s** against a liability of **%s** at 30 June 2025: **%s** funded. Paying the full '
      'actuarially determined contribution would have taken %s more in %s.' % (
          C.usd(o['rows']['trust'][2025]), C.usd(o['rows']['total'][2025]), pc(o['funded'][2025]),
          C.usd(o['deficiency']), C.fy(2025)))
    a('- The %d policy titles on the Finance Committee’s 3 December 2026 agenda match the April 2024 draft title '
      'for title. No policy text is attached to the agenda.\n' % len(x4['titles']))
    a('**This project recommends neither direction**: not to save more and not to spend more. It shows what each '
      'setting would do to figures the town has already published. The boards decide.\n')
    a('The pages: ' + ', '.join('[%s](%s)' % (PAGES[k], path(k)) for k in PAGES) + '.\n')

    a('## The free cash split\n')
    a('| Share (the draft’s minimum) | On %s |' % C.usd(b['fc']))
    a('|---|---:|')
    for _, lab, amt in b['split']:
        a('| %s | %s |' % (lab, C.usd(amt)))
    a('| **Claimed by the minimums** | **%s** |' % C.usd(b['claimed']))
    a('| No set use | %s |\n' % C.usd(b['unclaimed']))
    a('Source: the draft, pdf pages 29-30 ([%s](/docs/%s)); certified free cash from the Town’s fact sheet, equal to '
      'the state databank. Capital is a floor of 20%%, up to 30%%; other one-time costs are the lesser of 10%% or '
      '$250,000. Most of this free cash was already appropriated at Town Meeting: this shows how the rule would work, '
      'not what happened.\n' % ('DLS manual', FP.MANUAL))

    a('## Today’s rules against the draft\n')
    a('| Policy | Today (Select Board policies, Article III) | The draft (DLS, April 2024) | State law |')
    a('|---|---|---|---|')
    a('| Free cash | Stabilization to five percent, then at least 10% to OPEB, then special funds, then one-time uses | '
      'Target of five to seven percent of the budget; a minimum share for each use (table above) | Spent by Town Meeting '
      'once the state certifies it |')
    a('| General stabilization | At least five percent of the budget; all funds no more than ten percent; refill '
      'within about three years | Five to eight percent; a yearly deposit of 0.25% (summary) or 0.3% (text) of the '
      'budget; below five percent take at most one third and refill within two years | Any amount may go in; '
      'spending takes two thirds (c. 40, §5B) |')
    a('| Special purpose funds | Deposit sized in capital planning; two thirds to spend | Three to five percent of the '
      'budget together; at least 10% of free cash | Spending takes a majority (c. 40, §5B) |')
    a('| Reserve fund | $50,000, at most one half of one percent of the budget | No size set | Up to five percent of '
      'last year’s levy; the Finance Committee votes transfers (c. 40, §6) |')
    a('| OPEB | At least 10% of certified free cash | Keeps the 10% as one option; intends to pay the full '
      'actuarially determined contribution; a valuation every two years | Funding allowed, not required (c. 32B, §20) |')
    a('| Capital | A project is anything over $20,000 | Two to three percent of the budget, net of debt, in cash; '
      '20% to 30% of free cash | |')
    a('| Debt | Regular debt service at most 4% of the regular levy; all at most 14% of the total levy | Within the levy '
      '2% to 4% of the budget; all debt 5% to 11% of operating revenues | |')
    a('| Revenue estimates | No written rule | Local receipts at most 90% of last year’s collections without firm '
      'evidence; check each forecast against the year that followed | |\n')
    a('Today’s stabilization section still quotes two caps (ten percent of the prior year’s tax levy for a '
      'deposit, ten percent of equalized value in total) that the current text of c. 40, §5B does not contain. It '
      'also asks two thirds to spend from any stabilization fund, where the statute asks a majority for a special '
      'purpose fund.\n')
    a('What the law allows and what the state recommends are kept apart here. The statute sets the limits in the last '
      'column. The draft’s targets are what the Division of Local Services recommends **for towns like Lunenburg**, '
      'and the draft itself says the Town is to test them against its own finances before adopting them (pdf page 3). '
      'The Government Finance Officers Association recommends unrestricted general fund balance of no less than two '
      'months of regular revenues or expenditures ([GFOA, 2015](%s)); that counts free cash and stabilization together. '
      'The FY2025 audit puts total general fund balance at %s, 25%% of general fund expenditures.\n'
      % (FP.LAW['gfoa'], C.usd(b['fund_balance']['total'])))

    a('## The rules in practice\n')
    a('| Year | General stabilization, share of budget | Free cash available that year, share of prior budget |')
    a('|---|---:|---:|')
    for y in range(2016, b['latest'] + 1):
        a('| %s | %s | %s |' % (C.fy(y), pc(b['stab_pct'][y], 2) if y in b['stab_pct'] else '', pc(b['fc_pct'][y], 2)
                               if y in b['fc_pct'] else ''))
    st_all, dt_all = FP.dls_stabilization(), FP.dls_debt()
    a('\n| Year | Special funds, share of budget | Capital funded, share of budget less debt | Debt service, share of budget | Into the OPEB trust | Ten percent of that year\u2019s free cash |')
    a('|---|---:|---:|---:|---:|---:|')
    for y in range(FP.TREND_FROM, 2026):
        bd = D(str(st_all[('Lunenburg', y)]['budget']))
        sv = D(str(dt_all[('Lunenburg', y)]['service']))
        cp = b['capital'].get(y)
        a('| %s | %s | %s | %s | %s | %s |' % (
            C.fy(y), pc(D(str(st_all[('Lunenburg', y)]['special'])) / bd * 100),
            pc(cp['total'] / (bd - sv) * 100) if cp else '', pc(sv / D(str(dt_all[('Lunenburg', y)]['budget'])) * 100),
            C.usd(b['opeb']['rows']['contrib'][y]), C.usd(b['fact_sheet'][y][0] / 10)))
    a('\nFree cash landed inside the draft’s five to seven percent in %d of %d certifications. Stabilization is '
      'shown from %s, the first year the state databank’s general fund figure equals the annual report’s to '
      'the dollar; before it the databank’s figure includes the zoning incentive fund.\n'
      % (len(x2['in_range']), len(x2['fyears']), C.fy(FP.TREND_FROM)))
    a('**One balance, two figures.** At 30 June 2025 the annual report prints general stabilization at $%s (unaudited) '
      'and the audit at %s, %s higher. Nothing held reconciles them.\n' % (format(s['report'], ',.2f'),
                                                                         C.usd(s['audit']), C.usd(x2['diff'])))
    a('**The draft’s table.** Each general stabilization balance in the '
      'draft’s table (pdf page 31) is the balance at the previous 30 June, to the dollar: its %s figure, %s, is '
      'the %s year-end.\n' % (C.fy(2024), C.usd(b['draft_bal'][2024]), C.fy(2023)))
    a('### Peer towns\n')
    a('| Town | General stabilization %s | Free cash %s | Debt service %s |' % (C.fy(2025), C.fy(b['latest']), C.fy(2025)))
    a('|---|---:|---:|---:|')
    for t in sorted(b['peers'], key=lambda t: -b['peer_stab'][t]):
        a('| %s | %s | %s | %s |' % ('**%s**' % t if t == 'Lunenburg' else t, pc(b['peer_stab'][t], 2),
                                     pc(b['peer_fc'][t], 2), pc(b['peer_debt'][t], 2)))
    a('\nEach town against its own budget, from the state’s Municipal Databank. This is where Lunenburg sits, not '
      'a ranking of better or worse.\n')

    a('## Retiree health (OPEB)\n')
    a('| 30 June | Total liability | Trust | Funded | Paid for current retirees | Into the trust |')
    a('|---|---:|---:|---:|---:|---:|')
    for y in o['years']:
        R = o['rows']
        a('| %d | %s | %s | %s | %s | %s |' % (y, C.usd(R['total'][y]), C.usd(R['trust'][y]), pc(o['funded'][y], 2),
                                              C.usd(R['contrib_payg'][y]), C.usd(R['contrib'][y])))
    a('\nFrom the FY2025 audit’s schedule (pdf page 78); every identity it prints re-adds. In FY2025 the actuarially '
      'determined contribution was %s; the Town contributed %s, %s short. Peer towns are not compared, because many '
      'send pupils to regional districts that carry those retirees.\n' % (C.usd(o['adc']), C.usd(o['contributed']),
                                                                         C.usd(o['deficiency'])))

    a('## The record, meeting by meeting\n')
    a('Speakers are named by role. *Captions* means our machine captions of the recording, which locate a moment and '
      'are not a record; no figure heard only in captions is given.\n')
    for r in x4['rows']:
        a('- **%s, %s** (%s), %s: %s [source](%s)' % (r['board'], r['date'], r['evidence'], r['who'], r['what'], r['url']))
    a('')
    a('## What this does not establish\n')
    a('- Whether the draft the Finance Committee will review is the April 2024 manual unchanged. The agenda lists the '
      'same titles and attaches no text.')
    a('- Which FY2025 general stabilization figure is right: the annual report’s or the audit’s.')
    a('- What the liability looks like in any actuarial valuation after the two held (2017 and 2018).')
    a('- Where the reserve fund’s $50,000 figure came from; no record found gives its origin.')
    a('- What the FY2028 figures will be. The worked example uses the latest certification; the next (as of 1 July '
      '2026) was not in the state databank on 25 November 2026.\n')
    a('## Sources\n')
    for sname, href in [('DLS, Town of Lunenburg Financial Policies Manual, April 2024 (draft)', '/docs/' + FP.MANUAL),
                        ('Select Board Policies and Procedures (in force)', '/docs/' + FP.SBPOL),
                        ('FY2025 audited financial statements', '/docs/' + FP.AUDIT),
                        ('FY2025 annual town report', '/docs/' + FP.AR25),
                        ('Free Cash Fact Sheet', SRC_FACT['href']),
                        ('DLS Municipal Databank exports, 25 November 2026', '/docs/' + FP.DLS_STAB),
                        ('M.G.L. c. 40, §5B', FP.LAW['5B']), ('M.G.L. c. 40, §6', FP.LAW['6']),
                        ('M.G.L. c. 32B, §20', FP.LAW['32B']), ('GFOA, Fund Balance Guidelines', FP.LAW['gfoa']),
                        ('The meeting record (our dataset)', '/docs/data/financial-policy-record.csv')]:
        a('- [%s](%s)' % (sname, href))
    return '\n'.join(L_) + '\n'


def data():
    """The figures every financial policy page reads: FP.build() plus the databank's FY2025 and FY2026 rows."""
    b = FP.build()
    import financial_policies_data as _  # noqa
    s = FP.dls_stabilization()
    b['budget26'] = D(str(s[('Lunenburg', 2025)]['budget']))
    b['special25_pct'] = D(str(s[('Lunenburg', 2025)]['special'])) / D(str(s[('Lunenburg', 2025)]['budget'])) * 100
    # The FY2026 operating budget, for today's five-percent test, from the databank's FY2026 row.
    for r in FP._xlsx(FP.DLS_STAB):
        if r['Municipality'] == 'Lunenburg' and int(r['Schedule A Fiscal Year']) == 2026:
            b['budget26'] = D(str(r['Operating Budget']))
    return b


def outputs():
    b = data()
    p1, x1 = page_rules(b)
    p2, x2 = page_targets(b)
    p3, x3 = page_opeb(b)
    p4, x4 = page_debate(b)
    out = {os.path.join(TOPICS, '%s.json' % p['id']): json.dumps(p, ensure_ascii=False, sort_keys=True,
                                                                 separators=(',', ':')) + '\n'
           for p in (p1, p2, p3, p4)}
    out[REPORT] = report(b, x1, x2, x3, x4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out = outputs()
    stale = [k for k, v in out.items() if not os.path.exists(k) or io.open(k, encoding='utf-8').read() != v]
    if a.check:
        if stale:
            raise SystemExit('build_financial_policies: stale: %s' % ', '.join(os.path.relpath(k, ROOT) for k in stale))
        print('build_financial_policies: %d outputs current' % len(out))
        return
    for k, v in out.items():
        with io.open(k + '.tmp', 'w', encoding='utf-8', newline='\n') as f:
            f.write(v)
        os.replace(k + '.tmp', k)
    print('build_financial_policies: wrote %d outputs (%d changed)' % (len(out), len(stale)))


if __name__ == '__main__':
    main()
