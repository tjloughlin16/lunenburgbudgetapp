#!/usr/bin/env python3
"""THE POLICY CALCULATOR'S PAYLOAD: today's free cash rules, the state's draft, and the figures
they are applied to, for fy28/src/components/blocks/custom/policy-calculator.tsx.

    python3.11 scripts/build_policy_calculator.py           # write the payload
    python3.11 scripts/build_policy_calculator.py --check   # fail if it would change, or if the
                                                            # component's arithmetic disagrees

TJ, 27 November 2026: "a 'Policy calculator' that the finance committee can use to adjust to
show the outcomes towards free cash, that shows todays settings, policy suggestions, etc".
The plan is notes/plans/POLICY-CALCULATOR.md.

WHAT IT IS BUILT ON. Every figure comes from scripts/financial_policies_data.py, the module the
financial policy pages read (this script imports it and never edits it). Every RULE the
calculator applies is asserted here VERBATIM on the page that prints it -- the Select Board
section, or the pdf page of the DLS draft -- before its number is used, so a share the
calculator applies is a share a document sets (rule 13).

WHAT THE PAYLOAD IS. One `topic_blocks.custom` block, already validated (rule 2 over every
display string), under `block`, so whichever page hosts the calculator puts it in its flow as
it is. Beside it, `expected`: both presets worked at today's figures in Python. --check bundles
the component's own arithmetic (custom/policy-calculator-math.ts) with esbuild, runs it on the
same defaults, and fails if any dollar differs -- rule 9, recomputed rather than re-read.

RULE 8. The calculator recommends neither rule set. It applies each as printed and shows the
result; the component draws both in neutral series colours.

WHAT IT CANNOT KNOW, stated in the payload: today's third step (the special purpose deposit) is
"calculated each fiscal year during the capital planning process", so no figure is held for it
and it starts at zero as the user's input; and the stabilization balance at 30 June 2025 is
printed two ways (annual report and audit), so the calculator starts from the one the state's
databank also prints and names the other.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
from decimal import Decimal as D

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
import topic_blocks as TB  # noqa: E402
import financial_policies_data as FP  # noqa: E402
import build_financial_policies as BFP  # noqa: E402  (its sources and its inline(); never edited here)
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
from conclusions import figure  # noqa: E402

OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'policy-calculator.json')
# THE PAGE IT IS DRAWN ON: the hub of the New financial policies shelf, /financial-policies
# (scripts/topic_registry/financial_policies.py names this script as the hub's generator). TJ,
# 27 November 2026: "the calculator goes on the hub". The shelf is unlisted until TJ reviews it.
HUB = 'financial-policies'
PAGE = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', HUB + '.json')
MATH = os.path.join(ROOT, 'fy28', 'src', 'components', 'blocks', 'custom', 'policy-calculator-math.ts')
COMPONENT = 'policy-calculator'
BALANCE_FY = 2025   # the last year-end every balance below is printed for


def rule_today(section, phrase):
    FP.on_sb(section, phrase)
    return dict(source='Select Board policy, %s' % section, quote=phrase)


def rule_draft(page, phrase):
    FP.on_manual(page, phrase)
    return dict(source='State draft, pdf page %d' % page, quote=phrase)


# THE RULES, quoted. The number each one sets is beside it, and is checked against the words.
TODAY = [
    ('general', D('0.05'), 'five percent',
     rule_today('Section 3.03', 'The highest priority use of Free Cash should be to increase the balance of the Stabilization Account if necessary to a level of at least five percent of the current fiscal year omnibus budget')),
    ('opeb', D('0.10'), '10%',
     rule_today('Section 3.03', 'The next highest priority use of Free Cash should be to fund an amount equivalent to at last 10% of the previous fiscal year’s certified General Fund Free Cash for deposit into the OPEB Trust Fund')),
    ('special', None, None,
     rule_today('Section 3.03', 'The amount is to be calculated each fiscal year during the capital planning process')),
    ('left', None, None,
     rule_today('Section 3.03', 'Any monies that remain in Free Cash may be used to fund one-time expenditures')),
    ('floor', D('0.04'), 'four percent',
     rule_today('Section 3.04', 'The Town should maintain a balance in the general stabilization fund of no less than four percent of the prior year’s omnibus budget')),
    ('cap', D('0.10'), 'ten percent',
     rule_today('Section 3.04', 'The total of all funds should not exceed ten percent of the prior years’ omnibus budget')),
]
DRAFT = [
    ('keep', D('0.20'), '20 percent',
     rule_draft(29, 'Set aside at least 20 percent of the certified free cash amount as the starting balance for the next year’s free cash certification')),
    ('special', D('0.10'), '1 0 percent',
     rule_draft(29, 'Appropriate at least 1 0 percent to the special purpose stabilization funds')),
    ('general', D('0.05'), '5 percent',
     rule_draft(29, '5 percent to the Town’s general stabilization')),
    ('cap', D('0.10'), '10 percent',
     rule_draft(29, 'capped at 10 percent of the previous year’s total budget')),
    ('opeb', D('0.10'), '10 percent',
     rule_draft(29, 'Appropriate at least 10 percent to the Town’s other postemployment benefits (OPEB) trust fund')),
    ('capital_lo', D('0.20'), '20 percent',
     rule_draft(29, 'Apply at least 20 percent but no more than 30 percent to the cash capital budget')),
    ('capital_hi', D('0.30'), '30 percent',
     rule_draft(29, 'Apply at least 20 percent but no more than 30 percent to the cash capital budget')),
    ('other', D('0.10'), '10 percent',
     rule_draft(30, 'Use the lesser of 10 percent or $250,000 for noncapital special articles')),
    ('stab_annual_summary', D('0.0025'), '0.25%', rule_draft(28, '0.25% annual appropriation')),
    ('stab_annual_text', D('0.003'), '0.3 percent',
     rule_draft(30, 'with an annual appropriation of 0.3 percent of the current year general fund budget')),
]
for _set in (TODAY, DRAFT):
    for _k, _v, _words, _r in _set:
        if _words and _words not in _r['quote']:
            FP.fail('policy calculator: %r is %s but its quote does not say %r' % (_k, _v, _words))
if FP.OTHER_CAP != D('250000') or '$250,000' not in DRAFT[7][3]['quote']:
    FP.fail('policy calculator: the draft\'s cap on other one-time costs moved')
# The draft's shares as financial_policies_data applies them on the pages must be the shares here.
_dr = {k: v for k, v, _, _ in DRAFT}
for key, _, share in FP.SPLIT:
    want = {'keep': 'keep', 'general': 'general', 'special': 'special', 'opeb': 'opeb',
            'capital': 'capital_lo', 'other': 'other'}[key]
    if (share if share is not None else FP.OTHER_SHARE) != _dr[want]:
        FP.fail('policy calculator: the pages apply %s at %s, the calculator at %s' % (key, share, _dr[want]))
_tr = {k: v for k, v, _, _ in TODAY}

# THE BANDS drawn beside each result: the pages' own BANDS, as fractions.
BANDS = dict(general_draft=[FP.BANDS['stab'][0] / 100, FP.BANDS['stab'][1] / 100],
             special_draft=[FP.BANDS['special'][0] / 100, FP.BANDS['special'][1] / 100],
             fc_draft=[FP.BANDS['fc'][0] / 100, FP.BANDS['fc'][1] / 100],
             general_today=FP.BANDS['stab_today'] / 100)
if D(str(BANDS['general_today'])) != _tr['general']:
    FP.fail('policy calculator: today\'s band and today\'s top-up rule differ')

USES = [
    ('keep', 'Kept back for next year'),
    ('general', 'General stabilization'),
    ('special', 'Special purpose stabilization'),
    ('opeb', 'Retiree health trust'),
    ('capital', 'Cash capital'),
    ('other', 'Other one-time costs'),
    ('left', 'Left for Town Meeting to decide'),
]


# ---------------------------------------------------------------- the dials

# EVERY RULE IS A DIAL (TJ, 27 November 2026: "i assumed i would have dials to move"), applied in
# this order, each taking from what the ones before left: today's 3.03 is a priority list, and the
# draft's shares are each of the whole certification and add to less than all of it, so the order
# changes nothing they produce. `unit`: 'fc' a share of the free cash, 'budget' a share of the
# budget, 'usd' dollars. Today's and the draft's settings come from the asserted rules above; a
# dial neither sets is at zero for it, and says so.
NO_RULE = dict(source=None, quote=None)
DIALS = [
    # key, label, unit, feeds, today (value, rule), draft (value, rule)
    ('general_target', 'Top up general stabilization to', 'budget', 'general',
     (_tr['general'], TODAY[0][3]), (D(0), NO_RULE)),
    ('opeb', 'Retiree health trust', 'fc', 'opeb', (_tr['opeb'], TODAY[1][3]), (_dr['opeb'], DRAFT[4][3])),
    ('special_dollars', 'Special purpose deposit, in dollars', 'usd', 'special',
     (D(0), TODAY[2][3]), (D(0), NO_RULE)),
    ('general', 'General stabilization', 'fc', 'general', (D(0), NO_RULE), (_dr['general'], DRAFT[2][3])),
    ('special', 'Special purpose stabilization', 'fc', 'special', (D(0), NO_RULE), (_dr['special'], DRAFT[1][3])),
    ('keep', 'Kept back for next year', 'fc', 'keep', (D(0), NO_RULE), (_dr['keep'], DRAFT[0][3])),
    ('capital', 'Cash capital', 'fc', 'capital', (D(0), NO_RULE), (_dr['capital_lo'], DRAFT[5][3])),
    ('other', 'Other one-time costs', 'fc', 'other', (D(0), NO_RULE), (_dr['other'], DRAFT[7][3])),
    ('other_cap', 'Cap on other one-time costs', 'usd', 'other', (None, NO_RULE), (FP.OTHER_CAP, DRAFT[7][3])),
]
ORDER = [k for k, *_ in DIALS]


def settings(which, fc):
    """{dial: value} for 'today' or 'draft'. A cap no rule sets is the whole free cash: no cap."""
    i = 4 if which == 'today' else 5
    return {d[0]: (float(d[i][0]) if d[i][0] is not None else fc) for d in DIALS}


# ---------------------------------------------------------------- the arithmetic, in Python

def allocate(x, d):
    """The dials in order; `short` is what they asked for beyond the free cash there was."""
    st = dict(rem=x['fc'], asked=0.0)

    def take(want):
        w = max(0.0, want)
        st['asked'] += w
        t = min(st['rem'], w)
        st['rem'] -= t
        return t
    topup = take(d['general_target'] * x['budget'] - x['general'])
    opeb = take(d['opeb'] * x['fc'])
    sd = take(d['special_dollars'])
    g = take(d['general'] * x['fc'])
    sp = take(d['special'] * x['fc'])
    keep = take(d['keep'] * x['fc'])
    cap = take(d['capital'] * x['fc'])
    other = take(min(d['other'] * x['fc'], d['other_cap']))
    return dict(keep=keep, general=topup + g, special=sd + sp, opeb=opeb, capital=cap, other=other,
                left=st['rem'], short=max(0.0, st['asked'] - x['fc']))


def after(x, u):
    b = x['budget']
    g, s = x['general'] + u['general'], x['special'] + u['special']
    return dict(general_pct=g / b, special_pct=s / b, all_pct=(g + s) / b,
                deposits_pct=(u['general'] + u['special']) / b,
                opeb_trust=x['opeb_trust'] + u['opeb'],
                funded=(x['opeb_trust'] + u['opeb']) / x['opeb_liability'],
                next_fc=u['keep'], next_fc_pct=u['keep'] / b)


def independent(x, which):
    """The two rule sets worked straight from their own words, NOT through the dials, so the dial
    arithmetic is checked against something it did not produce."""
    fc = x['fc']
    if which == 'today':
        g = max(0.0, min(fc, float(_tr['general']) * x['budget'] - x['general']))
        o = min(fc - g, float(_tr['opeb']) * fc)
        return dict(keep=0.0, general=g, special=0.0, opeb=o, capital=0.0, other=0.0, left=fc - g - o, short=0.0)
    sp = {k: a for k, _, a in FP.split(D(str(fc)))}
    u = dict(keep=float(sp['keep']), general=float(sp['general']), special=float(sp['special']),
             opeb=float(sp['opeb']), capital=float(sp['capital']), other=float(sp['other']))
    return dict(u, left=fc - sum(u.values()), short=0.0)


# ---------------------------------------------------------------- the payload

def build():
    b = FP.build()
    st = FP.dls_stabilization()[('Lunenburg', BALANCE_FY)]
    s25 = b['stab25']
    op = b['opeb']
    if money(st['general']) != money(s25['report']):
        FP.fail('policy calculator: the databank and annual report general stabilization differ')
    if money(st['general']) + money(st['special']) != money(st['total']):
        FP.fail('policy calculator: the databank general and special do not add to its total')
    fc, budget = float(b['fc']), float(b['fc_budget'])
    trust, liab = float(op['rows']['trust'][BALANCE_FY]), float(op['rows']['total'][BALANCE_FY])
    figs = set()

    def U(v):
        t = C.usd(v)
        figs.add(t)
        return t

    def P(v, dp=0):
        t = C.pct(v, dp)
        figs.add(t)
        return t

    fy = lambda y: (figs.add(C.fy(y)) or C.fy(y))
    inputs = [
        dict(key='fc', label='Certified free cash', value=fc, text=U(fc),
             source='Certified by the state %s, available in %s' % (b['fc_date'], fy(b['latest']))),
        dict(key='budget', label='Operating budget', value=budget, text=U(budget),
             source='The budget the state measures this certification against (%s)' % fy(b['latest'] - 1)),
        dict(key='general', label='General stabilization balance', value=float(st['general']),
             text=U(st['general']), source='30 June 2025, the annual report and the state\'s databank'),
        dict(key='special', label='Special purpose stabilization balances', value=float(st['special']),
             text=U(st['special']), source='30 June 2025, the state\'s databank'),
        dict(key='opeb_trust', label='Retiree health trust balance', value=trust, text=U(trust),
             source='30 June 2025, the FY2025 audit'),
        dict(key='opeb_liability', label='Retiree health liability', value=liab, text=U(liab),
             source='30 June 2025, the FY2025 audit'),
    ]
    figs.update(('30 June 2025', b['fc_date'], 'FY2025'))
    audit_note = ('The FY2025 audit prints the general stabilization balance as %s, not %s; the '
                  'calculator starts from the figure the state\'s databank also prints.'
                  % (U(s25['audit']), U(st['general'])))

    allow = set()
    for rs in (TODAY, DRAFT):
        for _, _, _, r in rs:
            allow.add(r['quote'])
            allow.add(r['source'])
    allow.update(('3.03', '3.04', '3.07', 'April 2024', 'pdf pages 28-30'))

    # THE DIALS' RANGES are where a slider stops, not figures about the town: a share up to half the
    # free cash, a top-up target up to the draft's own top, dollars up to the whole free cash.
    span = dict(fc=(0, 0.5, 0.01), budget=(0, 2 * BANDS['general_draft'][1], 0.0025))
    dials = []
    for key, label, unit, feeds, (tv, tr), (dv, dr) in DIALS:
        lo, hi, step = span.get(unit, (0, fc, 5000))
        dials.append(dict(
            key=key, label=label, unit=unit, feeds=feeds, min=lo, max=hi, step=step,
            today=dict(value=float(tv) if tv is not None else None, **tr),
            draft=dict(value=float(dv), **dr)))
    capital_range = [float(_dr['capital_lo']), float(_dr['capital_hi'])]

    inp = {i['key']: i['value'] for i in inputs}
    data = dict(
        inputs=inputs, dials=dials, order=ORDER, capital_range=capital_range,
        uses=[dict(key=k, label=l) for k, l in USES],
        presets=[
            dict(key='today', label="Today's rules", source='Select Board policy, sections 3.03, 3.04 and 3.07',
                 settings=settings('today', fc)),
            dict(key='draft', label='State draft', source='DLS draft financial policy manual, April 2024, pdf pages 28-30',
                 settings=settings('draft', fc)),
        ],
        rules=dict(today=dict(floor=float(_tr['floor']), cap=float(_tr['cap'])),
                   draft=dict(cap=float(_dr['cap']),
                              stab_annual=[float(_dr['stab_annual_summary']), float(_dr['stab_annual_text'])])),
        bands=BANDS,
        defaults=inp,
        text=dict(
            audit_note=audit_note,
            budget_note=('One budget figure is used wherever a rule names the current or the prior '
                         'year\'s budget; edit it to test another year.'),
            cap_reading=('Our reading: today\'s "total of all funds" is taken as every stabilization '
                         'fund, general and special purpose together.'),
            annual_note=('The draft also sets a yearly stabilization deposit from the operating '
                         'budget, not from free cash: %s in its summary table, %s in its text.'
                         % (P(float(_dr['stab_annual_summary']) * 100, 2), P(float(_dr['stab_annual_text']) * 100, 1))),
            floors_note='The draft\'s shares are floors ("at least"); its setting puts each dial at its floor.',
            order_note=('The dials are applied in the order shown, each from what is left: today\'s policy '
                        'is written as a priority list.'),
        ),
    )
    so = ('Under today\'s rules most of the free cash is left for Town Meeting to decide; under the '
          'draft most of it is assigned before Town Meeting sees it.')
    ex = {}
    for k in ('today', 'draft'):
        u = allocate(inp, settings(k, fc))
        ind = independent(inp, k)
        if any(abs(u[f] - ind[f]) > 0.005 for f in ind):
            FP.fail('policy calculator: the dials set to %s do not reproduce its own rules: %s vs %s' % (k, u, ind))
        ex[k] = dict(uses=u, after=after(inp, u))
    if not ex['today']['uses']['left'] > fc / 2 or not ex['draft']['uses']['left'] < fc / 2:
        FP.fail('policy calculator: the "what it means" line no longer describes the defaults; rewrite it')
    blk = TB.custom(COMPONENT, 'Free cash, rule by rule', data, place='lead', figures=sorted(figs),
                    allow=sorted(allow), alt='A calculator with a dial for each free cash rule, set to '
                    'today\'s rules or the state\'s draft, applied to the latest certified free cash', so=so)
    return dict(block=blk, expected=ex)


def money(x):
    return D(str(x)).quantize(D('1'))


def page(payload):
    """The hub: the calculator is its signature, the two settings' results at today's figures under
    it as conclusions, then the stance and the documents. The four pages follow as the shelf's cards."""
    ex = payload['expected']
    t, d = ex['today']['uses'], ex['draft']['uses']
    fc = payload['block']['data']['defaults']['fc']
    U = lambda v: figure(float(v), C.usd(v), 'dollars')
    t_set = fc - t['left']
    # Half a dollar rounds UP, as the component's Math.round does, so the page and the bar agree;
    # the amount assigned is then the free cash less that, so the two foot.
    d_left = int(D(str(d['left'])).quantize(D('1'), rounding='ROUND_HALF_UP'))
    d_set = round(fc) - d_left
    if d_set + d_left != round(fc) or round(t_set) != round(t['opeb']):
        FP.fail('policy calculator page: the presets no longer foot to the free cash')
    f = LD.fact
    facts = [
        f('fc', U(fc), 'certified free cash, available in %s' % C.fy(FP.build()['latest']), 'published',
          label_figures={'y': figure(FP.build()['latest'], C.fy(FP.build()['latest']), 'fiscal year')}),
        f('today-left', U(t['left']), 'left to Town Meeting under today’s rules', 'estimate'),
        f('draft-set', U(d_set), 'assigned by the draft’s floors', 'estimate'),
        f('draft-left', U(d_left), 'left to Town Meeting under the draft', 'estimate'),
        f('keep', U(d['keep']), 'kept back for next year under the draft', 'estimate'),
        f('opeb', U(t['opeb']), 'to the retiree health trust, under either', 'estimate'),
    ]
    if round(t['opeb']) != round(d['opeb']):
        FP.fail('policy calculator page: the two presets no longer put the same sum in the trust')
    con = TP.conclusion
    cons = [
        con('Today’s rules assign %s of %s in free cash and leave %s to Town Meeting.'
            % (C.usd(t_set), C.usd(fc), C.usd(t['left'])), ['fc', 'today-left'],
            {'a': U(t_set), 'b': U(fc), 'c': U(t['left'])},
            so='General stabilization is already above five percent of the budget, so their first step takes nothing.'),
        con('The draft’s floors assign %s and leave %s, with %s kept for next year.'
            % (C.usd(d_set), C.usd(d_left), C.usd(d['keep'])), ['draft-set', 'draft-left', 'keep', 'opeb'],
            {'a': U(d_set), 'b': U(d_left), 'c': U(d['keep'])},
            so='Both put %s into the retiree health trust; the draft adds stabilization, capital and a reserve for next year.'
               % C.usd(t['opeb']), so_figures={'a': U(t['opeb'])}),
    ]
    import brief
    bad = []
    for i, c in enumerate(cons):
        bad += brief.check_unit(c, '%s conclusion %d' % (HUB, i + 1)) + brief.check_unit(c['so'], '%s conclusion %d means' % (HUB, i + 1))
    for x in facts:
        bad += brief.check_unit(x['label'], '%s fact %s' % (HUB, x['id']))
    if bad:
        FP.fail('\n  '.join(bad))
    calc = TB.claims(dict(payload['block'], place='lead'), cons, facts)   # under the one-line answer
    stance = TB.explain('What this page does not say', [BFP.L(
        'This project recommends neither rule set. The calculator applies each as printed to figures the '
        'town has published, and to any figures you type. The boards decide.')], place='end', tone='define')
    sources = [BFP.SRC_FACT, BFP.src_manual(), BFP.src_sb(), BFP.SRC_DLS_ST, BFP.SRC_AUDIT, BFP.SRC_AR25]
    docs = TB.explain('Where the figures and the rules come from', [BFP.L(
        'Every rule a dial applies is quoted from the document that sets it, and every starting figure is '
        'read from a published record.')], place='end', tone='plain',
        links=[(x['label'], x['href']) for x in sources])
    answer = ('Today\u2019s rules leave %s of %s in free cash to Town Meeting; the state\u2019s draft leaves %s. '
              'The dials apply either rule set, or any other, to these figures.' % (C.usd(t['left']), C.usd(fc), C.usd(d_left)))
    return TP.hub(HUB, answer, None, blocks=[calc, stance, docs],
                  answer_figures={'a': U(t['left']), 'b': U(fc), 'c': U(d_left)})


def run_math(payload):
    """The component's own arithmetic on the payload's defaults, through esbuild and node."""
    esb = os.path.join(ROOT, 'fy28', 'node_modules', '.bin', 'esbuild')
    with tempfile.TemporaryDirectory() as td:
        js = os.path.join(td, 'math.mjs')
        subprocess.run([esb, MATH, '--bundle', '--format=esm', '--log-level=error', '--outfile=' + js], check=True)
        drv = os.path.join(td, 'run.mjs')
        io.open(drv, 'w').write(
            "import * as M from './math.mjs'; import fs from 'fs';\n"
            "const d = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).block.data;\n"
            "const out = {};\n"
            "for (const p of d.presets) { const u = M.allocate(d.defaults, p.settings);"
            " out[p.key] = { uses: u, after: M.after(d.defaults, u) } }\n"
            "console.log(JSON.stringify(out));\n")
        pj = os.path.join(td, 'p.json')
        io.open(pj, 'w').write(json.dumps(payload))
        r = subprocess.run(['node', drv, pj], check=True, capture_output=True, text=True)
        return json.loads(r.stdout)


def compare(payload):
    got, want, bad = run_math(payload), payload['expected'], []
    for k in want:
        for part in ('uses', 'after'):
            for f, v in want[k][part].items():
                g = got[k][part].get(f)
                tol = 0.5 if part == 'uses' or f in ('opeb_trust', 'next_fc') else 1e-9
                if g is None or abs(g - v) > tol:
                    bad.append('%s.%s.%s: python %r, component %r' % (k, part, f, v, g))
    if bad:
        raise SystemExit('build_policy_calculator: the component\'s arithmetic disagrees:\n  ' + '\n  '.join(bad))
    return sum(len(want[k][p]) for k in want for p in ('uses', 'after'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    payload = build()
    n = compare(payload)
    dump = lambda o: json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
    out = {OUT: dump(payload), PAGE: dump(page(payload))}
    stale = [k for k, v in out.items() if not os.path.exists(k) or io.open(k, encoding='utf-8').read() != v]
    if a.check:
        if stale:
            raise SystemExit('build_policy_calculator: stale: %s' % ', '.join(os.path.relpath(k, ROOT) for k in stale))
        print('build_policy_calculator: %d outputs current; %d figures agree with the component' % (len(out), n))
        return
    for k, v in out.items():
        with io.open(k + '.tmp', 'w', encoding='utf-8', newline='\n') as f:
            f.write(v)
        os.replace(k + '.tmp', k)
    print('build_policy_calculator: wrote %d outputs (%d changed); %d figures agree with the component'
          % (len(out), len(stale), n))


if __name__ == '__main__':
    main()
