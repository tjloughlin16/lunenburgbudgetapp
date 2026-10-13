#!/usr/bin/env python3
"""State aid, split into topic pages: twelve pages and the Chapter 70 hub.

    python3 scripts/build_state_aid_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_state_aid_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, one to four conclusions resting on them. The State aid shelf absorbs
/why-we-only-get-minimum-aid, /how-chapter-70-works and /what-the-state-requires-us-to-spend,
and covers total state aid from /state-aid beside Chapter 70. The circuit breaker
(special education) and transportation reimbursement (transportation) are listed on the shelf
and written by their own generators.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD. Every figure comes from a payload or a
published dataset already in the repository, and the script refuses to write if two of them
stop agreeing where they are supposed to:

  fy28/public/data/minimum-aid.json          build_minimum_aid.py: DESE's Chapter 70 Trends
                                             workbook, FY2007 to FY2026, term by term.
  fy28/public/data/ch70-formula.json         build_ch70_formula.py: the same workbook, the
                                             formula read at the margin (OUR ESTIMATES there).
  fy28/public/data/spending-vs-required.json build_spending_vs_required.py: DESE's district
                                             profile, net school spending against the minimum.
  fy28/public/data/state-aid.json            build_state_aid.py: the FY2027 Chapter 70 summary,
                                             the free cash proofs' CL#8 line, the model's rate.
  sources/data/dls-cherry-sheet.csv          fetch_dls_cherry_sheet.py: every cherry sheet line,
                                             receipts and assessments, final state budget,
                                             FY2010 to FY2027 (published at /docs/data/).
  fy28/public/docs/data/town-ledger-fy26-q3.csv
                                             the FY2026 school appropriation, departments 300
                                             and 301, original budget.
  model/finance.py                           the projection's state aid base and rate (OURS).

RULE 11. Chapter 70 is not state aid. Every page names which of the two it means, and the
share of the school budget is computed with Chapter 70 alone, never the cherry sheet total.

RULE 1. Budget against budget, actual against actual. Net school spending is ACTUAL to FY2024
and BUDGETED after, and the two stages are tabulated with their stage and never differenced.
The Governor's FY2027 figure and the final state budget's are two stages of one year: both are
shown, neither is subtracted from the other.
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT, 'model'))  # after scripts/: model/ has its own conclusions.py
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import finance as FIN  # noqa: E402

PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
CHERRY = os.path.join(ROOT, 'sources', 'data', 'dls-cherry-sheet.csv')
CHERRY_SRC = os.path.join(ROOT, 'sources', 'data', 'dls-cherry-sheet-sources.csv')
PROOF = os.path.join(ROOT, 'sources', 'data', 'free-cash-proof.csv')
LEDGER = os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', 'town-ledger-fy26-q3.csv')
CH70 = 'Chapter 70'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == 'state-aid' and gen == 'build_state_aid_topics.py']


def fail(msg):
    raise SystemExit('build_state_aid_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def said(payload, key):
    """One quotation a payload already verified, re-checked against our copy of the minutes
    where that copy is on this disk."""
    s = next((x for x in payload['said'] if x['key'] == key), None)
    if s is None:
        fail('quotation %r is no longer in its payload' % key)
    if not s['cite'].startswith('/docs/'):
        fail('quotation %r does not cite our copy' % key)
    path = os.path.join(ROOT, 'sources', s['cite'][len('/docs/'):])
    if os.path.exists(path):
        flat = lambda t: ' '.join(t.replace('ﬁ', 'fi').split())
        if flat(s['quote']) not in flat(open(path, encoding='utf-8', errors='replace').read()):
            fail('quotation %r is not verbatim in %s' % (key, s['cite']))
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'],
                label='%s minutes, %s' % (s['board'], s['date']))


def cherry():
    """Lunenburg's cherry sheet, {fy: {flow: {line: amount}}}, final state budget."""
    out = {}
    for r in csv.DictReader(open(CHERRY, encoding='utf-8')):
        if r['name'] == 'Lunenburg' and r['population'] == 'Municipalities':
            out.setdefault(int(r['fy']), {}).setdefault(r['flow'], {})[r['line']] = float(r['amount'])
    for fy, d in out.items():
        rec = d['Receipts']
        parts = sum(v for k, v in rec.items() if k not in ('Total Receipts', 'Net Receipts'))
        if abs(parts - rec['Total Receipts']) > 1:
            fail('cherry sheet %d: the receipt lines no longer sum to Total Receipts' % fy)
        ass = d['Assessments']
        if abs(rec['Total Receipts'] - ass['Total Assessments'] - rec['Net Receipts']) > 1:
            fail('cherry sheet %d: receipts less assessments is not Net Receipts' % fy)
    return out


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = {}
    docs = {
        'dese-ch70-key-factors.xlsx': ('state-dese/dese-ch70-key-factors.xlsx',
                                       'Massachusetts DESE, Chapter 70 Trends workbook'),
        'dese-ch70-district-profile.xlsx': ('state-dese/dese-ch70-district-profile.xlsx',
                                            'Massachusetts DESE, Chapter 70 district profiles'),
        'ch70-fy27-summary.xlsx': ('budget-workbooks/ch70-fy27-summary.xlsx',
                                   'Massachusetts DESE, FY2027 Chapter 70 summary (Governor)'),
        'free-cash-proof-lunenburg.xlsx': ('state-dls/free-cash-proof-lunenburg.xlsx',
                                           'Massachusetts DLS, free cash proof'),
    }
    for r in csv.DictReader(open(CHERRY_SRC, encoding='utf-8')):
        if r['population'] == 'Municipalities' and r['fy'] in ('2026', '2027'):
            docs[r['source_file']] = ('state-dls/' + r['source_file'],
                                      'Massachusetts DLS, cherry sheet %s, FY%s'
                                      % (r['flow'].lower(), r['fy']))
    for name, (key, pub) in docs.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[name] = dict(label='%s — %s' % (pub, name), href='/docs/' + key)
    for f, what in (('dls-cherry-sheet.csv', 'every cherry sheet line, FY2010 to FY2027'),
                    ('free-cash-proof.csv', 'the free cash proofs, line by line'),
                    ('town-ledger-fy26-q3.csv', 'the FY2026 town ledger, by department')):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[f] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    if 'analyses/show-your-work.md' not in man:
        fail('analyses/show-your-work.md is not in archive-manifest.csv')
    out['show-your-work.md'] = dict(
        label='Lunenburg Budget Project — show-your-work.md (every rate the projection uses)',
        href='/docs/analyses/show-your-work.md')
    return out


def build():
    MA = load('minimum-aid.json')
    CF = load('ch70-formula.json')
    SR = load('spending-vs-required.json')
    SA = load('state-aid.json')
    CS = cherry()
    src = sources()
    S = lambda *names: [src[n] for n in names]
    yrs27 = [n for n in src if n.startswith('CherrySheet-2027-')]
    yrs26 = [n for n in src if n.startswith('CherrySheet-2026-')]
    rec27 = next(n for n in yrs27 if 'Receipts' in n)
    rec26 = next(n for n in yrs26 if 'Receipts' in n)
    ass27 = next(n for n in yrs27 if 'Assessments' in n)
    ass26 = next(n for n in yrs26 if 'Assessments' in n)
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    OF = lambda a, b, unit: figure(a, '%s of %s' % (C.num(a), C.num(b)), unit or None)
    f, con = LD.fact, TP.conclusion
    out = {}

    # ------------------------------------------------ the cross-checks
    ser = {r['fy']: r for r in MA['series']}
    hd = dict(MA['headline'])
    y26 = hd['fy']
    s26 = ser[y26]
    # The headline carries the district's figures by cell; the required contribution is read
    # off the same year's series row, and must equal what the formula page and the floor use.
    hd['required_local_contribution'] = s26['required_local_contribution']
    if hd['required_local_contribution'] != MA['why_zero']['required_local_contribution']:
        fail('FY2026: the series and why_zero disagree on the required contribution')
    for k in ('aid', 'foundation_budget', 'required_local_contribution', 'enrollment', 'prior_aid'):
        if abs(hd[k] - CF[k]) > 0.5:
            fail('minimum-aid.json and ch70-formula.json disagree on %s' % k)
    if abs(hd['per_pupil'] * hd['enrollment'] - hd['increase']) > 0.5:
        fail('the FY2026 increase is no longer the minimum rate times the pupils')
    wz = MA['why_zero']
    if abs(wz['prior_aid'] - (wz['foundation_budget'] - wz['required_local_contribution'])
           - wz['headroom']) > 0.5:
        fail('the headroom is no longer last year’s aid less the formula’s need')
    agree = [fy for fy in sorted(ser) if fy in CS]
    for fy in agree:
        if abs(ser[fy]['aid'] - CS[fy]['Receipts'][CH70]) > 1:
            fail('FY%d: DESE’s Chapter 70 and the cherry sheet’s disagree' % fy)
    bud = {r['fy']: r for r in SR['budgeted']}
    act = {r['fy']: r for r in SR['actual']}
    if abs(hd['required_local_contribution'] + hd['aid'] - bud[y26]['required']) > 1:
        fail('FY2026: required contribution plus Chapter 70 is no longer required net school '
             'spending')
    fm = SA['formula']
    if abs(fm['required'] + fm['aid'] - fm['nss']) > 1:
        fail('FY2027: the summary’s required plus aid no longer equals its net school spending')
    led = {r['dept']: float(r['original']) for r in csv.DictReader(open(LEDGER, encoding='utf-8'))}
    approp = led['300'] + led['301']
    if abs(approp - SA['ledger']['school_appropriation']) > 0.5:
        fail('the ledger CSV and state-aid.json disagree on the school appropriation')
    if abs(SA['ledger']['ch70']['budgeted'] - CS[y26]['Receipts'][CH70]) > 0.5:
        fail('FY2026: the town ledger’s Chapter 70 budget is not the cherry sheet’s')
    base, rate = FIN.FY27['state_aid'], FIN.DEFAULT_ASSUMPTIONS['state_aid_growth']
    if base != SA['assumption']['base'] or abs(rate - SA['assumption']['rate']) > 1e-9:
        fail('model/finance.py and state-aid.json disagree on the state aid base or rate')
    cl8 = {int(r['year']): float(r['amount']) for r in csv.DictReader(open(PROOF, encoding='utf-8'))
           if r['town'] == 'Lunenburg' and r['line'].startswith('Excess/Shortfall Cherry Sheet')}
    vt = SA['variance']['town']
    if {r['year']: r['amount'] for r in vt['series']} != cl8:
        fail('state-aid.json’s CL#8 series is no longer the free cash proofs’')

    # ------------------------------------------------ Chapter 70 by year
    a07 = ser[MA['fy_first']]
    changes = [r for r in MA['series'] if r['change'] is not None]
    big = max(changes, key=lambda r: r['change'])
    fell = [r for r in changes if r['change'] < 0]
    worst = min(fell, key=lambda r: r['change'])
    unrec = [r['fy'] for r in changes if r['reconciles'] is False]
    gov27, fin27 = fm['aid'], CS[2027]['Receipts'][CH70]
    if fm['fy'] != 2027:
        fail('the Chapter 70 summary is no longer FY2027')
    agree_n = len(agree)
    out['chapter-70-by-year'] = TP.page(
        'chapter-70-by-year',
        'Chapter 70 was %s in %s and %s in %s; it fell in %s of %s years.'
        % (C.usd(hd['aid']), C.fy(y26), C.usd(a07['aid']), C.fy(a07['fy']), C.num(len(fell)),
           C.num(len(changes))),
        [f('a26', U(hd['aid']), 'Chapter 70, %s, DESE' % C.fy(y26), 'published', {'y': F(y26)},
           allow=(CH70,)),
         f('a07', U(a07['aid']), 'Chapter 70, %s' % C.fy(a07['fy']), 'published',
           {'y': F(a07['fy'])}, allow=(CH70,)),
         f('big', U(big['change']), 'largest one-year rise, %s' % C.fy(big['fy']), 'published',
           {'y': F(big['fy'])}),
         f('cut', U(-worst['change']), 'largest one-year fall, %s' % C.fy(worst['fy']),
           'published', {'y': F(worst['fy'])}),
         f('fell', OF(len(fell), len(changes), 'years'), 'years in which the aid fell',
           'published'),
         f('gov27', U(gov27), '%s, the Governor’s figure' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('fin27', U(fin27), '%s, the final state budget’s cherry sheet' % C.fy(2027),
           'published', {'y': F(2027)}),
         f('agree', OF(agree_n, agree_n, 'years'),
           'years DESE’s figure equals the cherry sheet’s, to the dollar', 'published')],
        [con('Chapter 70 rose from %s in %s to %s in %s.'
             % (C.usd(a07['aid']), C.fy(a07['fy']), C.usd(hd['aid']), C.fy(y26)),
             ['a07', 'a26'], {'a': U(a07['aid']), 'y': F(a07['fy']), 'b': U(hd['aid']),
                              'z': F(y26)}, allow=(CH70,)),
         con('The largest rise was %s in %s; the largest fall was %s in %s.'
             % (C.usd(big['change']), C.fy(big['fy']), C.usd(-worst['change']),
                C.fy(worst['fy'])), ['big', 'cut', 'fell'],
             {'a': U(big['change']), 'y': F(big['fy']), 'b': U(-worst['change']),
              'z': F(worst['fy'])},
             notes=[step('In %s the aid moved by more than DESE’s own components, and the '
                         'workbook prints no residual.'
                         % (', '.join(C.fy(y) for y in unrec[:-1]) + ' and ' + C.fy(unrec[-1])),
                         'gap',
                         {('y%d' % y): F(y) for y in unrec}, allow=(CH70,),
                         closes='DESE’s preliminary Chapter 70 calculation for Lunenburg for each '
                                'of those years, stating every component')]),
         con('For %s the Governor proposed %s; the final state budget carries %s.'
             % (C.fy(2027), C.usd(gov27), C.usd(fin27)), ['gov27', 'fin27'],
             {'y': F(2027), 'a': U(gov27), 'b': U(fin27)}),
         con('DESE’s workbook and the state’s cherry sheet print the same aid in all %s '
             'years both cover.' % C.num(agree_n), ['agree'], {'n': N(agree_n)})],
        table=dict(caption='Chapter 70 by year', views=[dict(
            key='aid', label='DESE’s Chapter 70 calculation', total_col=-1,
            kinds=['ledger'] * 3, columns=['Chapter 70', 'Change', 'Foundation pupils'],
            rows=[dict(label=C.fy(r['fy']),
                       cells=[C.usd(r['aid']), C.usd(r['change']) if r['change'] is not None
                              else None, C.num(r['enrollment'])])
                  for r in sorted(MA['series'], key=lambda r: -r['fy'])],
            note='DESE’s Chapter 70 Trends workbook, sheet dataAid: the aid as DESE ran it for '
                 'each year. Not a Governor’s proposal and not a receipt.')]),
        chart=TP.series('Chapter 70 by year', [C.fy(y) for y in sorted(ser)], [
            TP.track('Chapter 70, DESE’s calculation', [ser[y]['aid'] for y in sorted(ser)],
                     'published', 'bar')], '$'),
        said=[said(SA, 'estimate')],
        sources=S('dese-ch70-key-factors.xlsx', 'ch70-fy27-summary.xlsx', rec27,
                  'dls-cherry-sheet.csv'),
        finding_figures={'a': U(hd['aid']), 'y': F(y26), 'b': U(a07['aid']), 'z': F(a07['fy']),
                         'n': N(len(fell)), 'm': N(len(changes))},
        finding_allow=(CH70,))

    # ------------------------------------------------ minimum aid
    last5 = [r for r in MA['series'] if r['fy'] > y26 - 5]
    minyrs = [r for r in last5 if r['minimum_aid'] > 0]
    rates = {r['fy']: r['per_pupil'] for r in minyrs}
    if [r['fy'] for r in minyrs] != MA['on_floor'] or rates[y26] != hd['per_pupil']:
        fail('the minimum-aid years are no longer the payload’s on_floor years')
    flo = next(x for x in MA['floor'] if x['fy'] == y26)
    early = [y for y in sorted(rates) if y != y26]
    rate_txt = ', '.join(C.usd(rates[y]) for y in early) + ' and ' + C.usd(rates[y26])
    # The chart draws the last ten years as DESE splits each rise. It is only the whole rise
    # where the two components are the only ones operating, so that is asserted, not assumed.
    win = [y for y in sorted(ser) if y > y26 - 10]
    if any(ser[y]['other_increments'] or ser[y]['reduction'] for y in win):
        fail('minimum aid chart: another component paid in the last ten years; draw it too')
    out['minimum-aid'] = TP.page(
        'minimum-aid',
        'All of %s’s %s increase was the Legislature’s minimum: %s for each of %s pupils.'
        % (C.fy(y26), C.usd(hd['increase']), C.usd(hd['per_pupil']), C.num(hd['enrollment'])),
        [f('inc', U(hd['increase']), 'rise in Chapter 70, %s' % C.fy(y26), 'published',
           {'y': F(y26)}, allow=(CH70,)),
         f('rate', U(hd['per_pupil']), 'minimum aid a pupil, %s, set by the Legislature'
           % C.fy(y26), 'statute', {'y': F(y26)}),
         f('pupils', N(hd['enrollment'], 'pupils'), 'foundation pupils, %s' % C.fy(y26),
           'published', {'y': F(y26)}),
         f('fa', U(hd['foundation_aid_increment']), 'from the formula’s foundation aid, %s'
           % C.fy(y26), 'published', {'y': F(y26)}),
         f('need', U(wz['need']), 'foundation budget less required contribution, %s'
           % C.fy(y26), 'published', {'y': F(y26)}),
         f('prior', U(wz['prior_aid']), 'Chapter 70 already paid, %s' % C.fy(y26 - 1),
           'published', {'y': F(y26 - 1)}, allow=(CH70,)),
         f('head', U(wz['headroom']), 'by which that exceeds the need (our arithmetic)',
           'published'),
         f('years', OF(len(minyrs), len(last5), 'years'), 'recent years in which minimum aid '
           'was paid', 'published')]
        + [f('r%d' % y, U(rates[y]), 'minimum aid a pupil, %s' % C.fy(y), 'statute',
             {'y': F(y)}) for y in early]
        + [f('peers', OF(flo['districts_at_rate'], flo['districts'], 'districts'),
             'compared districts at the same rate, %s' % C.fy(y26), 'published',
             {'y': F(y26)})],
        [con('The formula’s own foundation aid paid %s for %s; the whole rise was %s a pupil.'
             % (C.usd(hd['foundation_aid_increment']), C.fy(y26), C.usd(hd['per_pupil'])),
             ['inc', 'rate', 'pupils', 'fa'],
             {'a': U(hd['foundation_aid_increment']), 'y': F(y26), 'b': U(hd['per_pupil'])}),
         con('The need was %s against %s already paid, so the formula added nothing.'
             % (C.usd(wz['need']), C.usd(wz['prior_aid'])), ['need', 'prior', 'head'],
             {'a': U(wz['need']), 'b': U(wz['prior_aid'])},
             notes=[step('How large a rise in the foundation budget would take the town off the '
                         'minimum is not modelled in any document held.', 'gap', allow=(CH70,),
                         closes='DESE’s preliminary Chapter 70 calculation for Lunenburg for the '
                                'year in question')]),
         con('Minimum aid was paid in %s years, at %s a pupil.' % (
             OF(len(minyrs), len(last5), 'years')['text'] + ' recent', rate_txt),
             ['years', 'rate'] + ['r%d' % y for y in early],
             dict({'n': OF(len(minyrs), len(last5), 'years')},
                  **{('r%d' % y): U(rates[y]) for y in rates}),
             notes=[step('The Legislature votes the rate each year in the state budget, so '
                         'nothing published says what it will be next year.', 'gap',
                         closes='the enacted state budget for the year in question')])],
        chart=TP.series('Where each year’s rise came from', [C.fy(y) for y in win], [
            TP.track('Foundation aid, the formula', [ser[y]['foundation_aid'] for y in win],
                     'published', 'bar'),
            TP.track('Minimum aid, the Legislature', [ser[y]['minimum_aid'] for y in win],
                     'published', 'bar')], '$', stacked=True,
            note='DESE’s own split of each year’s rise; no other component paid anything in '
                 'these years.'),
        said=[said(MA, 'house'), said(MA, 'passed')],
        sources=S('dese-ch70-key-factors.xlsx'),
        finding_figures={'y': F(y26), 'a': U(hd['increase']), 'b': U(hd['per_pupil']),
                         'n': N(hd['enrollment'])})

    # ------------------------------------------------ foundation budget
    fpp = hd['foundation_per_pupil']
    sh26 = 100 * hd['aid_share_of_foundation']
    out['foundation-budget'] = TP.page(
        'foundation-budget',
        'The state priced Lunenburg’s schools at %s for %s; Chapter 70 equals %s of that.'
        % (C.usd(hd['foundation_budget']), C.fy(y26), C.pct(sh26)),
        [f('fb26', U(hd['foundation_budget']), 'foundation budget, %s' % C.fy(y26), 'published',
           {'y': F(y26)}),
         f('pupils', N(hd['enrollment'], 'pupils'), 'foundation pupils, %s' % C.fy(y26),
           'published', {'y': F(y26)}),
         f('fpp', U(fpp), 'a pupil, on average (our division)', 'published'),
         f('share26', P(sh26), 'Chapter 70 as a share of it, %s' % C.fy(y26), 'published',
           {'y': F(y26)}, allow=(CH70,)),
         f('fb07', U(a07['foundation_budget']), 'foundation budget, %s' % C.fy(a07['fy']),
           'published', {'y': F(a07['fy'])}),
         f('fb27', U(fm['foundation']), 'foundation budget, %s, Governor’s figure' % C.fy(2027),
           'published', {'y': F(2027)}),
         f('share27', P(100 * fm['aid_share']), 'Chapter 70 as a share of it, %s' % C.fy(2027),
           'published', {'y': F(2027)}, allow=(CH70,)),
         f('median27', P(100 * fm['median_aid_share']), 'the median operating district’s '
           'share, %s' % C.fy(2027), 'published', {'y': F(2027)}),
         f('rank27', OF(fm['rank'], fm['operating_districts'], 'districts'),
           'by that share, highest first, %s' % C.fy(2027), 'published', {'y': F(2027)})],
        [con('The foundation budget is the state’s estimate of an adequate budget for the schools: '
             '%s for %s.' % (C.usd(hd['foundation_budget']), C.fy(y26)), ['fb26', 'pupils', 'fpp'],
             {'a': U(hd['foundation_budget']), 'y': F(y26)},
             notes=[step('It is built from per-pupil rates that differ by grade and category, '
                         'and DESE’s workbook does not print Lunenburg’s rates, so the average is '
                         'not the cost of any one pupil.', 'gap',
                         closes='DESE’s foundation budget calculation for Lunenburg, by enrolment '
                                'category and rate')]),
         con('It rose from %s in %s to %s in %s.' % (C.usd(a07['foundation_budget']),
                                                  C.fy(a07['fy']), C.usd(hd['foundation_budget']),
                                                  C.fy(y26)), ['fb07', 'fb26'],
             {'a': U(a07['foundation_budget']), 'y': F(a07['fy']),
              'b': U(hd['foundation_budget']), 'z': F(y26)}),
         con('For %s Chapter 70 equals %s of it, against %s for the median operating district.'
             % (C.fy(2027), C.pct(100 * fm['aid_share']), C.pct(100 * fm['median_aid_share'])),
             ['share27', 'median27', 'rank27', 'fb27'],
             {'y': F(2027), 'a': P(100 * fm['aid_share']), 'b': P(100 * fm['median_aid_share'])},
             allow=(CH70,))],
        chart=TP.series('Foundation budget against Chapter 70', [C.fy(y) for y in sorted(ser)], [
            TP.track('Foundation budget', [ser[y]['foundation_budget'] for y in sorted(ser)]),
            TP.track('Chapter 70', [ser[y]['aid'] for y in sorted(ser)])], '$'),
        sources=S('dese-ch70-key-factors.xlsx', 'ch70-fy27-summary.xlsx'),
        finding_figures={'a': U(hd['foundation_budget']), 'y': F(y26), 'p': P(sh26)},
        finding_allow=(CH70,))

    # ------------------------------------------------ required local contribution
    sn, sh, wl = MA['since'], MA['share'], MA['wealth']
    if (sn['from_fy'], sn['to_fy']) != (wl['fy_from'], wl['fy_to']):
        fail('the required-contribution and wealth comparisons no longer span the same years')
    yA, yB = sn['from_fy'], sn['to_fy']
    out['required-local-contribution'] = TP.page(
        'required-local-contribution',
        'What the state requires the town to put in rose %s from %s to %s; Chapter 70 rose %s.'
        % (C.pct(100 * sn['required_pct']), C.fy(yA), C.fy(yB), C.pct(100 * sn['aid_pct'])),
        [f('rlc-a', U(sn['required_from']), 'required local contribution, %s' % C.fy(yA),
           'published', {'y': F(yA)}),
         f('rlc-b', U(sn['required_to']), 'required local contribution, %s' % C.fy(yB),
           'published', {'y': F(yB)}),
         f('rpct', P(100 * sn['required_pct']), 'rise in the requirement, %s to %s'
           % (C.fy(yA), C.fy(yB)), 'published', {'y': F(yA), 'z': F(yB)}),
         f('apct', P(100 * sn['aid_pct']), 'rise in Chapter 70, the same years', 'published',
           allow=(CH70,)),
         f('en-a', N(sn['enrollment_from'], 'pupils'), 'foundation pupils, %s' % C.fy(yA),
           'published', {'y': F(yA)}),
         f('en-b', N(sn['enrollment_to'], 'pupils'), 'foundation pupils, %s' % C.fy(yB),
           'published', {'y': F(yB)}),
         f('sh-a', P(100 * sh['first']), 'required share of the foundation budget, %s'
           % C.fy(sh['first_fy']), 'published', {'y': F(sh['first_fy'])}),
         f('sh-l', P(100 * sh['low']), 'the same share, %s, its lowest' % C.fy(sh['low_fy']),
           'published', {'y': F(sh['low_fy'])}),
         f('sh-b', P(100 * sh['last']), 'the same share, %s' % C.fy(sh['last_fy']), 'published',
           {'y': F(sh['last_fy'])}),
         f('eqv', P(100 * wl['eqv_growth']), 'rise in equalized valuation, %s to %s'
           % (C.fy(yA), C.fy(yB)), 'published', {'y': F(yA), 'z': F(yB)}),
         f('eqvmed', P(100 * wl['eqv_median']), 'the median of %s municipalities'
           % C.num(wl['municipalities']), 'published', {'n': N(wl['municipalities'])})],
        [con('The requirement rose from %s to %s while foundation pupils fell from %s to %s.'
             % (C.usd(sn['required_from']), C.usd(sn['required_to']),
                C.num(sn['enrollment_from']), C.num(sn['enrollment_to'])),
             ['rlc-a', 'rlc-b', 'rpct', 'apct', 'en-a', 'en-b'],
             {'a': U(sn['required_from']), 'b': U(sn['required_to']),
              'c': N(sn['enrollment_from']), 'd': N(sn['enrollment_to'])}),
         con('The town’s required share of the foundation budget was %s in %s, %s in %s, %s in %s.'
             % (C.pct(100 * sh['first']), C.fy(sh['first_fy']), C.pct(100 * sh['low']),
                C.fy(sh['low_fy']), C.pct(100 * sh['last']), C.fy(sh['last_fy'])),
             ['sh-a', 'sh-l', 'sh-b'],
             {'a': P(100 * sh['first']), 'y': F(sh['first_fy']), 'b': P(100 * sh['low']),
              'z': F(sh['low_fy']), 'c': P(100 * sh['last']), 'w': F(sh['last_fy'])}),
         con('It is worked out from property values and incomes; valuation rose %s, the median '
             '%s.' % (C.pct(100 * wl['eqv_growth']), C.pct(100 * wl['eqv_median'])),
             ['eqv', 'eqvmed'],
             {'a': P(100 * wl['eqv_growth']), 'b': P(100 * wl['eqv_median'])})],
        chart=TP.series('Required contribution against Chapter 70',
                        [C.fy(y) for y in sorted(ser)], [
            TP.track('Required local contribution',
                     [ser[y]['required_local_contribution'] for y in sorted(ser)]),
            TP.track('Chapter 70', [ser[y]['aid'] for y in sorted(ser)])], '$'),
        sources=S('dese-ch70-key-factors.xlsx'),
        finding_figures={'a': P(100 * sn['required_pct']), 'y': F(yA), 'z': F(yB),
                         'b': P(100 * sn['aid_pct'])}, finding_allow=(CH70,))

    # ------------------------------------------------ aid per pupil
    tn = {t['key']: t for t in CF['three_numbers']}
    avg, marg = tn['aid_per_pupil'], tn['marginal_per_pupil']
    if abs(avg['value'] - hd['aid'] / hd['enrollment']) > 0.01:
        fail('aid per pupil is no longer the aid over the foundation pupils')
    cuts = sorted(CF['cut_years'], key=lambda r: r['fy'])
    if [c['fy'] for c in cuts] != [r['fy'] for r in MA['series'] if r['reduction']]:
        fail('the cut years in the two payloads disagree')
    th = CF['threshold']
    nprov = len(CF['reductions'])
    zero = th['pupils_at_zero']
    out['aid-per-pupil'] = TP.page(
        'aid-per-pupil',
        'Chapter 70 averaged %s a pupil in %s, yet one pupil more or fewer moved it by %s.'
        % (avg['text'], C.fy(y26), marg['text']),
        [f('avg', figure(avg['value'], avg['text']), 'Chapter 70 a foundation pupil, %s (our '
           'division)' % C.fy(y26), 'published', {'y': F(y26)}, allow=(CH70,)),
         f('marg', figure(marg['value'], marg['text']), 'what one pupil moves it by, %s (ours)'
           % C.fy(y26), 'estimate', {'y': F(y26)}),
         f('prov', N(nprov, 'provisions'), 'provisions in DESE’s definitions that cut aid',
           'published')]
        + [f('cut%d' % c['fy'], U(c['amount']), 'across-the-board reduction, %s' % C.fy(c['fy']),
             'published', {'y': F(c['fy'])}) for c in cuts]
        + [f('zero', N(zero, 'pupils'), 'pupils at which the formula’s need turns negative '
           '(ours)', 'estimate'),
           f('rshare', P(100 * th['required_share']), 'required contribution against the '
             'foundation budget, %s' % C.fy(y26), 'published', {'y': F(y26)})],
        [con('Aid is last year’s aid plus an increase, so a pupil moves only the increase: %s.'
             % marg['text'], ['avg', 'marg'], {'a': figure(marg['value'], marg['text'])},
             notes=[step('Measured at the margin with everything else held at its %s value; it '
                         'is not a rate to multiply by a fall in enrolment.' % C.fy(y26), 'gap',
                         {'y': F(y26)}, allow=(CH70,),
                         closes='DESE’s preliminary Chapter 70 calculation for Lunenburg for the '
                                'year in question')]),
         con('DESE’s definitions name %s things that cut aid; fewer pupils at a district running '
             'schools is neither.' % C.num(nprov), ['prov'], {'n': N(nprov)}),
         con('Aid was cut across the board in %s, and never since.'
             % ', '.join('%s (%s)' % (C.fy(c['fy']), C.usd(c['amount'])) for c in cuts),
             ['cut%d' % c['fy'] for c in cuts],
             dict(**{('y%d' % c['fy']): F(c['fy']) for c in cuts},
                  **{('a%d' % c['fy']): U(c['amount']) for c in cuts})),
         con('Below about %s foundation pupils the formula’s need would turn negative; not in %s '
             'published years.' % (C.num(zero), C.num(th['years_checked'])), ['zero', 'rshare'],
             {'n': N(zero), 'm': N(th['years_checked'])})],
        chart=TP.series('Average pupil against one more pupil',
                        ['Average a pupil', 'One pupil more or fewer'], [
            TP.track('Chapter 70 over foundation pupils', [avg['value'], None], 'published', 'bar'),
            TP.track('What one pupil moves it by, ours', [None, marg['value']], 'estimate', 'bar')],
            '$', stacked=True,
            note='%s: %s on average, %s for one pupil. The first is our division of DESE’s '
                 'figures, the second our reading of the formula.' % (C.fy(y26), avg['text'],
                                                                     marg['text']),
            note_figures={'y': F(y26), 'a': figure(avg['value'], avg['text']),
                          'b': figure(marg['value'], marg['text'])}),
        sources=S('dese-ch70-key-factors.xlsx'),
        finding_figures={'a': figure(avg['value'], avg['text']), 'y': F(y26),
                         'b': figure(marg['value'], marg['text'])}, finding_allow=(CH70,))

    # ------------------------------------------------ net school spending
    la = SR['latest_actual']
    b26 = bud[y26]
    if la['fy'] != max(act):
        fail('latest_actual is not the last actual year')
    met = sum(1 for r in SR['actual'] if r['ratio'] >= 1)
    if met != len(SR['actual']) or len(SR['actual']) != SR['years_measured']:
        fail('the minimum is no longer met in every actual year measured')
    narrow = min(SR['actual'], key=lambda r: r['ratio'])
    c0 = next(c for c in SR['conclusions'] if 'required_pct' in c['figures'])
    fg = c0['figures']
    yb = fg['base_fy']['value']
    if abs(act[la['fy']]['required'] / act[yb]['required'] - 1 - fg['required_pct']['value'] / 100) > 1e-3:
        fail('the requirement’s rise no longer recomputes from the actual series')
    rq_pct = 100 * (act[la['fy']]['required'] / act[yb]['required'] - 1)
    sp_pct = 100 * (act[la['fy']]['spent'] / act[yb]['spent'] - 1)
    a0, aN = min(act), max(act)

    def nss_rows(lo, hi):
        rows = []
        for fy in range(hi, lo - 1, -1):
            r, stage = (act[fy], 'actual') if fy in act else (bud[fy], 'budgeted')
            rows.append(dict(label=C.fy(fy), cells=[C.usd(r['required']), C.usd(r['spent']),
                                                    C.pct(100 * r['ratio']), stage]))
        return rows
    split = 2009
    nss_x = list(range(a0, y26 + 1))
    if any(y not in act and y not in bud for y in nss_x):
        fail('net school spending: a year between the first actual and %s is in neither stage'
             % y26)
    out['net-school-spending'] = TP.page(
        'net-school-spending',
        'Lunenburg spent %s of the state’s minimum in %s, and met the minimum in all %s years.'
        % (C.pct(100 * la['ratio']), C.fy(la['fy']), C.num(met)),
        [f('req26', U(b26['required']), 'required net school spending, %s' % C.fy(y26),
           'published', {'y': F(y26)}),
         f('rlc26', U(hd['required_local_contribution']), 'of it the town’s required '
           'contribution', 'published'),
         f('aid26', U(hd['aid']), 'of it Chapter 70', 'published', allow=(CH70,)),
         f('req24', U(la['required']), 'required, %s' % C.fy(la['fy']), 'published',
           {'y': F(la['fy'])}),
         f('sp24', U(la['spent']), 'spent, %s, actual' % C.fy(la['fy']), 'published',
           {'y': F(la['fy'])}),
         f('r24', P(100 * la['ratio']), 'of the minimum, %s' % C.fy(la['fy']), 'published',
           {'y': F(la['fy'])}),
         f('met', OF(met, len(SR['actual']), 'years'), 'years the minimum was met, %s to %s'
           % (C.fy(a0), C.fy(aN)), 'published', {'y': F(a0), 'z': F(aN)}),
         f('narrow', P(100 * narrow['ratio']), 'of the minimum, the narrowest year, %s'
           % C.fy(narrow['fy']), 'published', {'y': F(narrow['fy'])}),
         f('rqp', P(rq_pct), 'rise in the minimum, %s to %s' % (C.fy(yb), C.fy(la['fy'])),
           'published', {'y': F(yb), 'z': F(la['fy'])}),
         f('spp', P(sp_pct), 'rise in spending, the same years', 'published'),
         f('rb26', P(100 * b26['ratio']), 'of the minimum, %s, budgeted' % C.fy(y26),
           'published', {'y': F(y26)})],
        [con('The %s minimum, %s, is the town’s required contribution plus Chapter 70.'
             % (C.fy(y26), C.usd(b26['required'])), ['req26', 'rlc26', 'aid26'],
             {'y': F(y26), 'a': U(b26['required'])}, allow=(CH70,)),
         con('Lunenburg spent %s against a minimum of %s in %s, %s of it.'
             % (C.usd(la['spent']), C.usd(la['required']), C.fy(la['fy']),
                C.pct(100 * la['ratio'])), ['sp24', 'req24', 'r24', 'met', 'narrow'],
             {'a': U(la['spent']), 'b': U(la['required']), 'y': F(la['fy']),
              'p': P(100 * la['ratio'])}),
         con('From %s to %s the minimum rose %s and spending rose %s.'
             % (C.fy(yb), C.fy(la['fy']), C.pct(rq_pct), C.pct(sp_pct)), ['rqp', 'spp'],
             {'y': F(yb), 'z': F(la['fy']), 'a': P(rq_pct), 'b': P(sp_pct)}),
         con('The %s figure, %s of the minimum, is a budget; it is never set against an actual.'
             % (C.fy(y26), C.pct(100 * b26['ratio'])), ['rb26'],
             {'y': F(y26), 'a': P(100 * b26['ratio'])},
             notes=[step('Net school spending leaves out debt service, capital and transport, '
                         'so no line in the town’s or the district’s budget equals it.', 'gap',
                         closes='the district’s End of Year Financial Report to DESE, which '
                                'produces the actual figure')])],
        table=dict(caption='Net school spending against the minimum', views=[
            dict(key='recent', label='%s to %s' % (C.fy(split + 1), C.fy(y26)), total_col=-1,
                 kinds=['ledger'] * 4,
                 columns=['Required', 'Net school spending', 'Of the minimum', 'Stage'],
                 rows=nss_rows(split + 1, y26),
                 note='DESE’s district profiles. Actual to %s, budgeted after: two stages of one '
                      'quantity, never differenced.' % C.fy(aN)),
            dict(key='early', label='%s to %s' % (C.fy(a0), C.fy(split)), total_col=-1,
                 kinds=['ledger'] * 4,
                 columns=['Required', 'Net school spending', 'Of the minimum', 'Stage'],
                 rows=nss_rows(a0, split),
                 note='DESE’s district profiles, actual spending.')]),
        chart=TP.series('Spending against the state minimum', [C.fy(y) for y in nss_x], [
            TP.track('Of the minimum, actual', [100 * act[y]['ratio'] if y in act else None
                                                for y in nss_x]),
            TP.track('Of the minimum, budgeted', [100 * bud[y]['ratio'] if y not in act else None
                                                  for y in nss_x])], '%',
            reference=(100, 'The state minimum'), from_zero=False,
            note='Actual and budgeted years are two stages, drawn apart and never joined.'),
        said=[said(SR, 'definition')],
        sources=S('dese-ch70-district-profile.xlsx', 'dese-ch70-key-factors.xlsx'),
        finding_figures={'p': P(100 * la['ratio']), 'y': F(la['fy']), 'n': N(met)})

    # ------------------------------------------------ spending against the median
    c1 = next(c for c in SR['conclusions'] if 'gap' in c['figures'])
    if abs(c1['figures']['gap']['value'] - la['short_of_median']) > 0.5:
        fail('the gap to the median disagrees with latest_actual')
    br = SR['best_rank']
    out['net-school-spending-rank'] = TP.page(
        'net-school-spending-rank',
        'In %s Lunenburg ranked %s districts on spending against its minimum; in %s it was %s.'
        % (C.fy(la['fy']), OF(la['rank'], la['districts'], '')['text'], C.fy(yb),
           OF(act[yb]['rank'], act[yb]['districts'], '')['text']),
        [f('lun24', P(100 * la['ratio']), 'Lunenburg against its minimum, %s' % C.fy(la['fy']),
           'published', {'y': F(la['fy'])}),
         f('med24', P(100 * la['state_median']), 'the median district, %s' % C.fy(la['fy']),
           'published', {'y': F(la['fy'])}),
         f('rank24', OF(la['rank'], la['districts'], 'districts'), 'rank, highest first, %s'
           % C.fy(la['fy']), 'published', {'y': F(la['fy'])}),
         f('rank18', OF(act[yb]['rank'], act[yb]['districts'], 'districts'), 'rank, %s'
           % C.fy(yb), 'published', {'y': F(yb)}),
         f('best', OF(br['rank'], br['districts'], 'districts'), 'best rank, %s' % C.fy(br['fy']),
           'published', {'y': F(br['fy'])}),
         f('gap', U(la['short_of_median']), 'more at the median’s ratio, %s (our arithmetic)'
           % C.fy(la['fy']), 'published', {'y': F(la['fy'])}),
         f('atmed', OF(SR['years_at_or_above_median'], SR['years_measured'], 'years'),
           'years at or above the median district', 'published'),
         f('rank26', OF(b26['rank'], b26['districts'], 'districts'), 'rank, %s, budgeted'
           % C.fy(y26), 'published', {'y': F(y26)})],
        [con('Lunenburg spent %s of its minimum in %s; the median district spent %s of its own.'
             % (C.pct(100 * la['ratio']), C.fy(la['fy']), C.pct(100 * la['state_median'])),
             ['lun24', 'med24', 'rank24'],
             {'a': P(100 * la['ratio']), 'y': F(la['fy']), 'b': P(100 * la['state_median'])}),
         con('At the median district’s ratio it would have spent %s more in %s.'
             % (C.usd(la['short_of_median']), C.fy(la['fy'])), ['gap'],
             {'a': U(la['short_of_median']), 'y': F(la['fy'])},
             notes=[step('Nothing published separates a choice from a ceiling here: the levy '
                         'limit, the district’s request and the Town Meeting vote all land in '
                         'this one number.', 'gap',
                         closes='no single document: the district’s requests, the levy limit and '
                                'Town Meeting’s votes, year by year, set side by side')]),
         con('Its rank was %s in %s and %s in %s; its best was %s in %s.'
             % (OF(act[yb]['rank'], act[yb]['districts'], '')['text'], C.fy(yb),
                OF(la['rank'], la['districts'], '')['text'], C.fy(la['fy']),
                OF(br['rank'], br['districts'], '')['text'], C.fy(br['fy'])),
             ['rank18', 'rank24', 'best'],
             {'a': OF(act[yb]['rank'], act[yb]['districts'], ''), 'y': F(yb),
              'b': OF(la['rank'], la['districts'], ''), 'z': F(la['fy']),
              'c': OF(br['rank'], br['districts'], ''), 'w': F(br['fy'])}),
         con('It spent at or above the median district in %s years measured.'
             % OF(SR['years_at_or_above_median'], SR['years_measured'], '')['text'], ['atmed'],
             {'a': OF(SR['years_at_or_above_median'], SR['years_measured'], '')})],
        chart=TP.series('Lunenburg against the median district', [C.fy(y) for y in sorted(act)], [
            TP.track('Lunenburg, of its minimum', [100 * act[y]['ratio'] for y in sorted(act)]),
            TP.track('The median district, of its own',
                     [100 * act[y]['state_median'] for y in sorted(act)])], '%',
            note='Actual spending only. Each district is measured against its own minimum.'),
        sources=S('dese-ch70-district-profile.xlsx'),
        finding_figures={'y': F(la['fy']), 'a': OF(la['rank'], la['districts'], ''),
                         'z': F(yb), 'b': OF(act[yb]['rank'], act[yb]['districts'], '')})

    # ------------------------------------------------ total state aid (the cherry sheet)
    fys = sorted(CS)
    R = lambda fy, line: CS[fy]['Receipts'][line]
    tot26, ch26, ug26 = R(y26, 'Total Receipts'), R(y26, CH70), R(y26, 'UGGA')
    oth26 = tot26 - ch26 - ug26
    tot27, ch27 = R(2027, 'Total Receipts'), R(2027, CH70)
    y0 = fys[0]
    # Parts of one total each year, so stacked; the third is our subtraction and says so.
    total_chart = TP.series('All cherry sheet aid by year', [C.fy(fy) for fy in fys], [
        TP.track('Chapter 70', [R(fy, CH70) for fy in fys], 'published', 'bar'),
        TP.track('General government aid', [R(fy, 'UGGA') for fy in fys], 'published', 'bar'),
        TP.track('Every other line, our subtraction',
                 [R(fy, 'Total Receipts') - R(fy, CH70) - R(fy, 'UGGA') for fy in fys],
                 'published', 'bar')], '$', stacked=True,
        note='The final state budget’s cherry sheet for each year: the state’s estimates, not '
             'receipts.')
    out['total-state-aid'] = TP.page(
        'total-state-aid',
        'The state’s cherry sheet carries %s for Lunenburg for %s; Chapter 70 is %s of it.'
        % (C.usd(tot26), C.fy(y26), C.pct(100 * ch26 / tot26)),
        [f('tot26', U(tot26), 'all cherry sheet aid, %s' % C.fy(y26), 'published',
           {'y': F(y26)}),
         f('ch26', U(ch26), 'of it Chapter 70', 'published', allow=(CH70,)),
         f('sh26', P(100 * ch26 / tot26), 'Chapter 70’s share, %s' % C.fy(y26), 'published',
           {'y': F(y26)}, allow=(CH70,)),
         f('ug26', U(ug26), 'Unrestricted General Government Aid, %s' % C.fy(y26), 'published',
           {'y': F(y26)}),
         f('oth26', U(oth26), 'every other receipt line, %s' % C.fy(y26), 'published',
           {'y': F(y26)}),
         f('tot27', U(tot27), 'all cherry sheet aid, %s' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('ch27', U(ch27), 'of it Chapter 70, %s' % C.fy(2027), 'published', {'y': F(2027)},
           allow=(CH70,)),
         f('tot0', U(R(y0, 'Total Receipts')), 'all cherry sheet aid, %s' % C.fy(y0),
           'published', {'y': F(y0)})],
        [con('Of %s in %s, Chapter 70 was %s and general government aid %s.'
             % (C.usd(tot26), C.fy(y26), C.usd(ch26), C.usd(ug26)),
             ['tot26', 'ch26', 'sh26', 'ug26', 'oth26'],
             {'a': U(tot26), 'y': F(y26), 'b': U(ch26), 'c': U(ug26)}, allow=(CH70,)),
         con('For %s the final state budget carries %s, %s of it Chapter 70.'
             % (C.fy(2027), C.usd(tot27), C.usd(ch27)), ['tot27', 'ch27'],
             {'y': F(2027), 'a': U(tot27), 'b': U(ch27)}, allow=(CH70,)),
         con('All cherry sheet aid was %s in %s and %s in %s.'
             % (C.usd(R(y0, 'Total Receipts')), C.fy(y0), C.usd(tot26), C.fy(y26)),
             ['tot0', 'tot26'],
             {'a': U(R(y0, 'Total Receipts')), 'y': F(y0), 'b': U(tot26), 'z': F(y26)})],
        table=dict(caption='The cherry sheet, receipts by year', views=[dict(
            key='receipts', label='Final state budget', total_col=3, kinds=['ledger'] * 4,
            columns=['Chapter 70', 'General government aid', 'Every other line', 'All aid'],
            rows=[dict(label=C.fy(fy), cells=[
                C.usd(R(fy, CH70)), C.usd(R(fy, 'UGGA')),
                C.usd(R(fy, 'Total Receipts') - R(fy, CH70) - R(fy, 'UGGA')),
                C.usd(R(fy, 'Total Receipts'))]) for fy in reversed(fys)],
            note='Division of Local Services cherry sheets at the final state budget: the '
                 'state’s estimates for the year, not receipts. Every other line includes '
                 'school choice tuition received, charter reimbursement and library aid.')]),
        chart=total_chart,
        sources=S(rec26, rec27, 'dls-cherry-sheet.csv'),
        finding_figures={'a': U(tot26), 'y': F(y26), 'p': P(100 * ch26 / tot26)},
        finding_allow=(CH70,))
    # ------------------------------------------------ share of the school budget
    shs = 100 * ch26 / approp
    sc = SA['corroboration']
    if abs(round(shs, 2) - 100 * sc['recomputed']) > 0.01 or not sc['agrees']:
        fail('Chapter 70’s share of the school appropriation no longer recomputes')
    rest = approp - ch26
    out['chapter-70-school-budget-share'] = TP.page(
        'chapter-70-school-budget-share',
        'Chapter 70 was %s of the %s school appropriation; the School Committee said %s.'
        % (C.pct(shs), C.fy(y26), C.pct(100 * sc['stated'], 0)),
        [f('ch26', U(ch26), 'Chapter 70, %s budget' % C.fy(y26), 'published', {'y': F(y26)},
           allow=(CH70,)),
         f('app', U(approp), 'school appropriation, %s, departments 300 and 301' % C.fy(y26),
           'published', {'y': F(y26)}, allow=('300', '301')),
         f('share', P(shs), 'Chapter 70 of the appropriation (our division)', 'published',
           allow=(CH70,)),
         f('rest', U(rest), 'the rest of the appropriation', 'published'),
         f('said', P(100 * sc['stated'], 0), 'stated by the School Committee, %s'
           % sc['stated_on'], 'published', allow=(sc['stated_on'],)),
         f('tot26', U(tot26), 'all cherry sheet aid, %s' % C.fy(y26), 'published',
           {'y': F(y26)}),
         f('ug26', U(ug26), 'of it general government aid', 'published')],
        [con('Chapter 70 of %s against a school appropriation of %s is %s.'
             % (C.usd(ch26), C.usd(approp), C.pct(shs)), ['ch26', 'app', 'share'],
             {'a': U(ch26), 'b': U(approp), 'p': P(shs)}, allow=(CH70,)),
         con('The School Committee’s %s matches that division of two budget figures.'
             % C.pct(100 * sc['stated'], 0), ['said', 'share'],
             {'p': P(100 * sc['stated'], 0)}),
         con('The other %s is not covered by Chapter 70.' % C.usd(rest), ['rest'],
             {'a': U(rest)}, allow=(CH70,),
             notes=[step('Which of the town’s other revenues pays it is not traced in any '
                         'document held.', 'gap', closes='a revenue-to-appropriation allocation from the Town '
                                       'Accountant for the school budget')]),
         con('All state aid, %s, includes %s of general government aid that is not Chapter 70.'
             % (C.usd(tot26), C.usd(ug26)), ['tot26', 'ug26'],
             {'a': U(tot26), 'b': U(ug26)}, allow=(CH70,))],
        chart=TP.parts('The school appropriation', [
            ('Chapter 70', ch26), ('The rest, our subtraction', rest)], '$',
            note='Departments %s and %s, original %s budget, against the cherry sheet’s Chapter 70.'
                 % ('300', '301', C.fy(y26)), note_figures={'y': F(y26)},
            note_allow=('300', '301', CH70)),
        said=[said(SA, 'share')],
        sources=S(rec26, 'town-ledger-fy26-q3.csv', 'dls-cherry-sheet.csv'),
        finding_figures={'p': P(shs), 'y': F(y26), 's': P(100 * sc['stated'], 0)},
        finding_allow=(CH70,))

    # ------------------------------------------------ state aid growth
    steps_ = [(b, R(b, 'Total Receipts') / R(a, 'Total Receipts') - 1) for a, b in zip(fys, fys[1:])]
    med = 100 * statistics.median(s for _, s in steps_)
    cagr = 100 * ((R(fys[-1], 'Total Receipts') / R(y0, 'Total Receipts'))
                  ** (1.0 / (len(fys) - 1)) - 1)
    top3 = sorted(steps_, key=lambda t: -t[1])[:3]
    top3.sort()
    nfall = sum(1 for _, s in steps_ if s < 0)
    rg = SA['receipts']['growth']
    yN = fys[-1]
    out['state-aid-growth'] = TP.page(
        'state-aid-growth',
        'Our projection grows all state aid %s a year; the cherry sheet’s median yearly rise '
        'was %s.' % (C.pct(100 * rate, 2), C.pct(med, 2)),
        [f('rate', P(100 * rate, 2), 'a year, our projection, all state aid', 'estimate'),
         f('med', P(med, 2), 'median yearly rise, cherry sheet, %s to %s' % (C.fy(y0), C.fy(yN)),
           'published', {'y': F(y0), 'z': F(yN)}),
         f('cagr', P(cagr, 2), 'compound a year, the same years', 'published')]
        + [f('s%d' % y, P(100 * s), 'rise in %s' % C.fy(y), 'published', {'y': F(y)})
           for y, s in top3]
        + [f('nfall', OF(nfall, len(steps_), 'years'), 'years in which the total fell',
             'published'),
           f('base', U(base), 'our %s starting figure' % C.fy(2027), 'estimate', {'y': F(2027)}),
           f('fin27', U(tot27), '%s, the final state budget' % C.fy(2027), 'published',
             {'y': F(2027)}),
           f('rcpt', P(100 * rg['cagr'], 2), 'a year, Chapter 70 RECEIPTS, %s to %s'
             % (C.fy(rg['first_fy']), C.fy(rg['last_fy'])), 'published',
             {'y': F(rg['first_fy']), 'z': F(rg['last_fy'])}, allow=(CH70,))],
        [con('Our %s a year sits beside the cherry sheet’s median yearly rise of %s.'
             % (C.pct(100 * rate, 2), C.pct(med, 2)), ['rate', 'med', 'nfall'],
             {'a': P(100 * rate, 2), 'b': P(med, 2)},
             notes=[step('Chapter 70 is most of the total and is a formula, not a trend; nothing '
                         'here tests whether its next years resemble its last.', 'gap',
                         allow=(CH70,),
                         closes='DESE’s Chapter 70 district summary, which is published one '
                                'year ahead')]),
         con('The compound rate is %s; single years rose %s, %s and %s.'
             % ((C.pct(cagr, 2),) + tuple(C.pct(100 * s) for _, s in top3)),
             ['cagr'] + ['s%d' % y for y, _ in top3],
             dict({'a': P(cagr, 2)}, **{('s%d' % y): P(100 * s) for y, s in top3})),
         con('Our %s starting figure is %s; the final state budget’s cherry sheet is %s.'
             % (C.fy(2027), C.usd(base), C.usd(tot27)), ['base', 'fin27'],
             {'y': F(2027), 'a': U(base), 'b': U(tot27)},
             notes=[step('Ours adds an enacted change recorded as net to the Governor’s gross '
                         'total, so the two are not the same quantity.', 'gap',
                         closes='the line-by-line change between the Governor’s cherry sheet '
                                'and the final one for the year in question')]),
         con('Chapter 70 receipts rose %s a year from %s to %s; an actual is never set against '
             'a budget.' % (C.pct(100 * rg['cagr'], 2), C.fy(rg['first_fy']),
                            C.fy(rg['last_fy'])), ['rcpt'],
             {'a': P(100 * rg['cagr'], 2), 'y': F(rg['first_fy']), 'z': F(rg['last_fy'])},
             allow=(CH70,))],
        chart=TP.series('Yearly rise in all state aid', [C.fy(y) for y, _ in steps_] + ['Our rate'], [
            TP.track('Cherry sheet, year on year', [100 * s for _, s in steps_] + [None],
                     'published', 'bar'),
            TP.track('Our projection, a year', [None] * len(steps_) + [100 * rate], 'estimate',
                     'bar')], '%', stacked=True, decimals=2,
            note='Each bar is a final state budget against the one before: budget against budget.'),
        sources=S('dls-cherry-sheet.csv', rec27, 'show-your-work.md'),
        finding_figures={'a': P(100 * rate, 2), 'b': P(med, 2)})

    # ------------------------------------------------ cherry sheet variance (CL#8)
    ser8 = sorted(vt['series'], key=lambda r: r['year'])
    hi = max(ser8, key=lambda r: r['amount'])
    lo = min(ser8, key=lambda r: r['amount'])
    peers = SA['variance']['peers']
    nxt = max(peers, key=lambda r: r['swing'])
    if abs(hi['amount'] - lo['amount'] - vt['swing']) > 0.5 or vt['swing'] <= nxt['swing']:
        fail('the CL#8 swing or its rank no longer recomputes')
    Yr = lambda y: figure(y, str(y), 'year')
    out['cherry-sheet-variance'] = TP.page(
        'cherry-sheet-variance',
        'Cherry sheet receipts came in %s short of the estimate in %s and %s over in %s.'
        % (C.usd(-lo['amount']), str(lo['year']), C.usd(hi['amount']), str(hi['year'])),
        [f('y%d' % r['year'], U(r['amount']), 'over or under the estimate, %d proof'
           % r['year'], 'published', allow=(str(r['year']),)) for r in ser8]
        + [f('swing', U(vt['swing']), 'from the worst year to the best', 'published'),
           f('rank', OF(SA['variance']['rank'], SA['variance']['of'], 'towns'),
             'by the size of that swing, largest first', 'published'),
           f('next', U(nxt['swing']), 'the next largest swing, %s' % nxt['town'], 'published'),
           f('over', OF(vt['over'], len(ser8), 'years'), 'years receipts beat the estimate',
             'published')],
        [con('The line ran from %s in the %s proof to %s in the %s proof.'
             % (C.usd(lo['amount']), str(lo['year']), C.usd(hi['amount']), str(hi['year'])),
             ['y%d' % lo['year'], 'y%d' % hi['year'], 'over'],
             {'a': U(lo['amount']), 'y': Yr(lo['year']), 'b': U(hi['amount']),
              'z': Yr(hi['year'])}),
         con('That swing, %s, is the largest of %s towns compared; the next is %s.'
             % (C.usd(vt['swing']), C.num(SA['variance']['of']), C.usd(nxt['swing'])),
             ['swing', 'rank', 'next'],
             {'a': U(vt['swing']), 'n': N(SA['variance']['of']), 'b': U(nxt['swing'])},
             notes=[step('Whether this is a fact about the aid or about how the town estimates '
                         'it is not established.', 'gap',
                         closes='the town’s cherry sheet estimates and receipts, line by line, '
                                'for each of those years')])],
        table=dict(caption='Excess or shortfall of cherry sheet receipts', views=[dict(
            key='cl8', label='Free cash proof, line CL#8', total_col=-1, kinds=['ledger', 'ledger'],
            columns=['Over or under the estimate', 'Free cash certified'],
            rows=[dict(label=str(r['year']), cells=[C.usd(r['amount']), C.usd(r['certified'])])
                  for r in reversed(ser8)],
            note='The Division of Local Services’ free cash proof for Lunenburg. A positive '
                 'figure is receipts above the cherry sheet estimate.')]),
        chart=TP.series('Receipts against the cherry sheet estimate',
                        [str(r['year']) for r in ser8], [
            TP.track('Over or under, free cash proof', [r['amount'] for r in ser8], 'published',
                     'bar')], '$',
            note='Above the line, receipts beat the estimate; below it, they fell short. By the '
                 'year of each proof.'),
        sources=S('free-cash-proof-lunenburg.xlsx', 'free-cash-proof.csv'),
        finding_figures={'a': U(-lo['amount']), 'y': Yr(lo['year']), 'b': U(hi['amount']),
                         'z': Yr(hi['year'])})

    # ------------------------------------------------ cherry sheet assessments
    A = lambda fy, line: CS[fy]['Assessments'][line]
    at26 = A(y26, 'Total Assessments')
    scs, chs = A(y26, 'School Ch Sending Tuition'), A(y26, 'Chart Sch Sending Tuition')
    net26 = R(y26, 'Net Receipts')
    at27 = A(2027, 'Total Assessments')
    fq = said(SA, 'assessments')
    m = re.search(r'\$([\d,]+)', fq['quote'])
    fincom = float(m.group(1).replace(',', ''))
    out['cherry-sheet-assessments'] = TP.page(
        'cherry-sheet-assessments',
        'The cherry sheet charged Lunenburg %s for %s; %s was tuition for pupils schooled '
        'elsewhere.' % (C.usd(at26), C.fy(y26), C.pct(100 * (scs + chs) / at26)),
        [f('at26', U(at26), 'cherry sheet charges, %s' % C.fy(y26), 'published', {'y': F(y26)}),
         f('tot26', U(tot26), 'cherry sheet aid, %s' % C.fy(y26), 'published', {'y': F(y26)}),
         f('net26', U(net26), 'aid less charges, %s' % C.fy(y26), 'published', {'y': F(y26)}),
         f('scs', U(scs), 'school choice tuition, pupils sent elsewhere', 'published'),
         f('chs', U(chs), 'charter school tuition', 'published'),
         f('two', P(100 * (scs + chs) / at26), 'of the charges, those two together',
           'published'),
         f('at27', U(at27), 'charges, %s, final state budget' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('fincom', U(fincom), 'charges read to the Finance Committee, %s' % fq['date'],
           'published', allow=(fq['date'],))],
        [con('Charges of %s came off %s of aid in %s, leaving %s.'
             % (C.usd(at26), C.usd(tot26), C.fy(y26), C.usd(net26)), ['at26', 'tot26', 'net26'],
             {'a': U(at26), 'b': U(tot26), 'y': F(y26), 'c': U(net26)}),
         con('School choice and charter tuition were %s and %s, %s of the charges.'
             % (C.usd(scs), C.usd(chs), C.pct(100 * (scs + chs) / at26)), ['scs', 'chs', 'two'],
             {'a': U(scs), 'b': U(chs), 'p': P(100 * (scs + chs) / at26)},
             notes=[step('How many pupils the tuition is for, and where they went, is not on the '
                         'cherry sheet.', 'gap',
                         closes='DESE’s school choice and charter tuition reports for Lunenburg, '
                                'by receiving district')]),
         con('The %s final cherry sheet charges %s; the Finance Committee heard %s in February.'
             % (C.fy(2027), C.usd(at27), C.usd(fincom)), ['at27', 'fincom'],
             {'y': F(2027), 'a': U(at27), 'b': U(fincom)})],
        table=dict(caption='Cherry sheet charges by year', views=[dict(
            key='charges', label='Final state budget', total_col=2, kinds=['ledger'] * 4,
            columns=['School choice tuition', 'Charter tuition', 'All charges', 'Aid less charges'],
            rows=[dict(label=C.fy(fy), cells=[
                C.usd(A(fy, 'School Ch Sending Tuition')), C.usd(A(fy, 'Chart Sch Sending Tuition')),
                C.usd(A(fy, 'Total Assessments')), C.usd(R(fy, 'Net Receipts'))])
                for fy in reversed(fys)],
            note='Division of Local Services cherry sheets at the final state budget. Charges '
                 'are deducted from the aid before the town receives it.')]),
        chart=TP.parts('What the cherry sheet charged', [
            ('School choice tuition', scs), ('Charter school tuition', chs),
            ('Every other charge, our subtraction', at26 - scs - chs)], '$',
            note='The %s final cherry sheet. Charges come off the aid before the town receives it.'
                 % C.fy(y26), note_figures={'y': F(y26)}),
        said=[fq],
        sources=S(ass26, ass27, 'dls-cherry-sheet.csv'),
        finding_figures={'a': U(at26), 'y': F(y26), 'p': P(100 * (scs + chs) / at26)})

    # ------------------------------------------------ the hub
    h = {}
    h['h-ch70'] = f('h-ch70', U(hd['aid']), 'Chapter 70, %s' % C.fy(y26), 'published',
                    {'y': F(y26)}, allow=(CH70,))
    h['h-inc'] = f('h-inc', U(hd['increase']), 'its rise, all minimum aid', 'published')
    h['h-fa'] = f('h-fa', U(hd['foundation_aid_increment']), 'from the formula’s foundation aid',
                  'published')
    h['h-fb'] = f('h-fb', U(hd['foundation_budget']), 'foundation budget, %s' % C.fy(y26),
                  'published', {'y': F(y26)})
    h['h-rlc'] = f('h-rlc', U(hd['required_local_contribution']), 'the town’s required '
                   'contribution, %s' % C.fy(y26), 'published', {'y': F(y26)})
    h['h-ratio'] = f('h-ratio', P(100 * la['ratio']), 'spent against the minimum, %s'
                     % C.fy(la['fy']), 'published', {'y': F(la['fy'])})
    h['h-met'] = f('h-met', OF(met, len(SR['actual']), 'years'), 'years the minimum was met',
                   'published')
    h['h-rank'] = f('h-rank', OF(la['rank'], la['districts'], 'districts'), 'rank on that ratio, '
                    '%s' % C.fy(la['fy']), 'published', {'y': F(la['fy'])})
    h['h-tot'] = f('h-tot', U(tot26), 'all cherry sheet aid, %s' % C.fy(y26), 'published',
                   {'y': F(y26)})
    h['h-share'] = f('h-share', P(shs), 'Chapter 70 of the school appropriation', 'published',
                     allow=(CH70,))
    h['h-rate'] = f('h-rate', P(100 * rate, 2), 'a year, our projection of all state aid',
                    'estimate')
    h['h-worst'] = f('h-worst', U(lo['amount']), 'receipts against the estimate, %d proof'
                     % lo['year'], 'published', allow=(str(lo['year']),))
    tiers = [
        LD.tier('Chapter 70', [h['h-ch70'], h['h-inc'], h['h-fa'], h['h-fb'], h['h-rlc']]),
        LD.tier('The spending floor', [h['h-ratio'], h['h-met'], h['h-rank']]),
        LD.tier('All state aid', [h['h-tot'], h['h-share'], h['h-rate'], h['h-worst']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Chapter 70 was %s in %s; all of its %s rise was the Legislature’s minimum.'
                      % (C.usd(hd['aid']), C.fy(y26), C.usd(hd['increase'])),
                      ['h-ch70', 'h-inc', 'h-fa'],
                      {'a': U(hd['aid']), 'y': F(y26), 'b': U(hd['increase'])}, allow=(CH70,)),
        LD.conclusion('The town’s required contribution, %s, is worked out from property and '
                      'incomes, not pupils.'
                      % C.usd(hd['required_local_contribution']), ['h-rlc', 'h-fb'],
                      {'a': U(hd['required_local_contribution'])}),
        LD.conclusion('Lunenburg met the state minimum in every year measured; in %s it spent %s '
                      'of it.' % (C.fy(la['fy']), C.pct(100 * la['ratio'])),
                      ['h-met', 'h-ratio', 'h-rank'],
                      {'y': F(la['fy']), 'p': P(100 * la['ratio'])}),
        LD.conclusion('Chapter 70 is %s of the school appropriation; all state aid is a larger, '
                      'different figure.' % C.pct(shs), ['h-share', 'h-tot'], {'p': P(shs)},
                      allow=(CH70,)),
        LD.conclusion('We project all state aid at %s a year; receipts once fell %s short of the '
                      'cherry sheet.'
                      % (C.pct(100 * rate, 2), C.usd(-lo['amount'])), ['h-rate', 'h-worst'],
                      {'a': P(100 * rate, 2), 'b': U(-lo['amount'])}),
    ])
    out['state-aid'] = TP.hub(
        'state-aid',
        'Chapter 70 was %s of the %s the state’s cherry sheet gave Lunenburg for %s. All of that '
        'year’s rise was the Legislature’s %s-a-pupil minimum; the formula itself added %s.'
        % (C.usd(hd['aid']), C.usd(tot26), C.fy(y26), C.usd(hd['per_pupil']),
           C.usd(hd['foundation_aid_increment'])),
        hub_ladder, chart=total_chart,
        answer_figures={'a': U(hd['aid']), 'b': U(tot26), 'y': F(y26), 'c': U(hd['per_pupil']),
                        'd': U(hd['foundation_aid_increment'])},
        answer_allow=(CH70,))

    if sorted(k for k in out if k != 'state-aid') != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = []
        for p, text in outs.items():
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                stale.append(os.path.relpath(p, ROOT))
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('state aid topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
