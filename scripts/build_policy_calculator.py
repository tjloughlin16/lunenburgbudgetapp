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
# THE PAGE IT IS DRAWN ON, a draft like the four financial policy pages: not in the registry, so on
# no shelf, not in the sitemap and not prerendered, served at /town-reserves/policy-calculator to
# whoever is given the address. Registering it is how it joins the site.
PAGE_ID, PAGE_TITLE, HOME = 'policy-calculator', 'Policy calculator', 'town-reserves'
PAGE = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', PAGE_ID + '.json')
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


# ---------------------------------------------------------------- the arithmetic, in Python

def today(x):
    """Select Board 3.03, in its order: each step takes from what the step before left."""
    fc, rem = x['fc'], x['fc']
    g = min(rem, max(0.0, float(_tr['general']) * x['budget'] - x['general'])); rem -= g
    o = min(rem, float(_tr['opeb']) * fc); rem -= o
    s = min(rem, max(0.0, x['special_plan'])); rem -= s
    return dict(keep=0.0, general=g, special=s, opeb=o, capital=0.0, other=0.0, left=rem)


def draft(x):
    """The draft's floors, each a share of the whole certification (pdf pages 29-30)."""
    fc = x['fc']
    u = dict(keep=float(_dr['keep']) * fc, general=float(_dr['general']) * fc,
             special=float(_dr['special']) * fc, opeb=float(_dr['opeb']) * fc,
             capital=x['capital_share'] * fc,
             other=min(float(_dr['other']) * fc, float(FP.OTHER_CAP)))
    u['left'] = fc - sum(u.values())
    return u


def after(x, u):
    b = x['budget']
    g, s = x['general'] + u['general'], x['special'] + u['special']
    return dict(general_pct=g / b, special_pct=s / b, all_pct=(g + s) / b,
                deposits_pct=(u['general'] + u['special']) / b,
                opeb_trust=x['opeb_trust'] + u['opeb'],
                funded=(x['opeb_trust'] + u['opeb']) / x['opeb_liability'],
                next_fc=u['keep'], next_fc_pct=u['keep'] / b)


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
        dict(key='special_plan', label='Special purpose deposit under today\'s rules', value=0.0,
             text=U(0), source='Set each year in capital planning; no figure is held, so it starts at zero',
             basis='input'),
    ]
    for i in inputs:
        i.setdefault('basis', 'published')
    figs.add('30 June 2025')
    figs.add(b['fc_date'])
    audit_note = ('The FY2025 audit prints the general stabilization balance as %s, not %s; the '
                  'calculator starts from the figure the state\'s databank also prints.'
                  % (U(s25['audit']), U(st['general'])))
    figs.add('FY2025')

    def rules(rs):
        out = []
        for k, v, _, r in rs:
            out.append(dict(key=k, value=float(v) if v is not None else None, source=r['source'], quote=r['quote']))
        return out

    allow = set()
    for rs in (TODAY, DRAFT):
        for _, _, _, r in rs:
            allow.add(r['quote'])
            allow.add(r['source'])
    allow.update(('3.03', '3.04', '3.07', 'April 2024', 'pdf pages 28-30'))

    defaults = {i['key']: i['value'] for i in inputs}
    defaults['capital_share'] = float(_dr['capital_lo'])
    data = dict(
        inputs=inputs,
        uses=[dict(key=k, label=l) for k, l in USES],
        presets=[
            dict(key='today', label="Today's rules",
                 source='Select Board policy, sections 3.03, 3.04 and 3.07', rules=rules(TODAY)),
            dict(key='draft', label='State draft',
                 source='DLS draft financial policy manual, April 2024, pdf pages 28-30', rules=rules(DRAFT)),
            dict(key='custom', label='Custom', source='Your own shares of the free cash', rules=[]),
        ],
        params=dict(
            today=dict(general=float(_tr['general']), opeb=float(_tr['opeb']),
                       floor=float(_tr['floor']), cap=float(_tr['cap'])),
            draft=dict(keep=float(_dr['keep']), general=float(_dr['general']), special=float(_dr['special']),
                       opeb=float(_dr['opeb']), capital=[float(_dr['capital_lo']), float(_dr['capital_hi'])],
                       other=float(_dr['other']), other_cap=float(FP.OTHER_CAP), cap=float(_dr['cap']),
                       stab_annual=[float(_dr['stab_annual_summary']), float(_dr['stab_annual_text'])]),
            bands=BANDS),
        defaults=defaults,
        text=dict(
            audit_note=audit_note,
            budget_note=('One budget figure is used wherever a rule names the current or the prior '
                         'year\'s budget; edit it to test another year.'),
            cap_reading=('Our reading: today\'s "total of all funds" is taken as every stabilization '
                         'fund, general and special purpose together.'),
            annual_note=('The draft also sets a yearly stabilization deposit from the operating '
                         'budget, not from free cash: %s in its summary table, %s in its text.'
                         % (P(float(_dr['stab_annual_summary']) * 100, 2), P(float(_dr['stab_annual_text']) * 100, 1))),
            floors_note='The draft\'s shares are floors ("at least"); the calculator applies each floor.',
        ),
    )
    # The draft's yearly deposit, in dollars at today's budget, for the note's figures.
    so = ('Under today\'s rules most of the free cash is left for Town Meeting to decide; under the '
          'draft most of it is assigned before Town Meeting sees it.')
    ex = {k: dict(uses=f(defaults), after=after(defaults, f(defaults))) for k, f in (('today', today), ('draft', draft))}
    if not ex['today']['uses']['left'] > fc / 2 or not ex['draft']['uses']['left'] < fc / 2:
        FP.fail('policy calculator: the "what it means" line no longer describes the defaults; rewrite it')
    blk = TB.custom(COMPONENT, 'Free cash, rule by rule', data, place='lead', figures=sorted(figs),
                    allow=sorted(allow), alt='A calculator applying today\'s free cash rules or the '
                    'state\'s draft to the latest certified free cash', so=so)
    return dict(block=blk, expected=ex)


def money(x):
    return D(str(x)).quantize(D('1'))


def page(payload):
    """The draft topic page: the calculator first, the two presets' results at today's figures
    under it as conclusions, then the stance and the links to the four policy pages."""
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
    stance = TB.explain('What this page does not say', [BFP.L(
        'This project recommends neither rule set. The calculator applies each as printed to figures the '
        'town has published, and to any figures you type. The boards decide.')], place='end', tone='define')
    links = TB.explain('The financial policy pages', [BFP.L(
        'What each rule says, how the reserves have moved against them, the retiree health liability, and '
        'the public argument.')], place='end', tone='plain',
        links=[(BFP.PAGES[k], BFP.path(k)) for k in BFP.PAGES])
    cite = TP.cite
    sources = [BFP.SRC_FACT, BFP.src_manual(), BFP.src_sb(), BFP.SRC_DLS_ST, BFP.SRC_AUDIT, BFP.SRC_AR25]
    flow = ['finding', cite(payload['block'], 'factsheet', 'manual', 'today', 'dlsst', 'audit', 'ar25'),
            ('conclusion', 0), ('conclusion', 1), cite(stance, 'manual', 'today'), cite(links, 'manual'), 'sources']
    finding = 'Today’s rules leave %s of %s in free cash to Town Meeting; the draft leaves %s.' % (
        C.usd(t['left']), C.usd(fc), C.usd(d_left))
    return TP.page(PAGE_ID, finding, [], [], sources=sources,
                   finding_figures={'a': U(t['left']), 'b': U(fc), 'c': U(d_left)},
                   flow=BFP.inline(PAGE_ID, flow, facts, cons), draft=dict(title=PAGE_TITLE, home=HOME))


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
            "for (const k of ['today','draft']) { const u = M.uses(k, d.params, d.defaults);"
            " out[k] = { uses: u, after: M.after(d.defaults, u) } }\n"
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
