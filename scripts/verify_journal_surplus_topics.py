#!/usr/bin/env python3
"""Recompute every figure on /fy2026-closeout/surplus-bridge and /surplus-repeat-lines by a
DIFFERENT ROUTE.

    python3 scripts/verify_journal_surplus_topics.py

The generator reads the journal through scripts/journal.py. This reads two files directly,
with csv and Decimal, and shares no code with it but the category definition:

  * the PUBLISHED period-13 spreadsheets (`munis-school-ytd.csv`, report gf-school), which the
    generator never reads: what was left, the budget, the transfers, the actuals and the open
    orders, every year and every category. The journal must reproduce them.
  * the journal CSV itself, read raw, for what the spreadsheets cannot split: payroll,
    invoices, journal entries and receipts by their source codes written out here, and the
    carried-forward orders checked against the start-of-year re-encumbrances (`SOY`), a
    different set of lines from the transfers (`BUA`) the generator counts.

The ONE thing shared is build_school_surplus.category_of: it is a definition, and the point of
these pages is that their categories are the published surplus pages' categories.

Then every fact on both pages is compared with its recomputed value, and every money figure in
the prose must be one of them.
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_school_surplus import category_of, CATEGORIES  # noqa: E402  (the definition)

DATA = os.path.join(ROOT, 'sources', 'data')
TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
YEARS = (2023, 2024, 2025, 2026)
Y0, Y1 = 2025, 2026
KIND = {'PRJ': 'pay', 'PRH': 'pay', 'API': 'inv', 'APM': 'inv', 'GEN': 'je', 'GRV': 'je',
        'CRP': 'rec'}
bad = []


def suggestions(left, cat):
    """The suggestions page's measurements, from the period-13 spreadsheets: how spread out
    FY2025's leftover was, and how many accounts were under budget every year; and from the raw
    journal, the June transfers of FY2025. Its building-upkeep figures are checked by
    verify_buildings_topics.py, from the same sources."""
    acct = defaultdict(D)
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['period'] == '13' and r['report'] == 'gf-school' and r['type'] == 'E':
            acct[(int(r['fiscal_year']), r['account'])] += D(r['available_budget']).quantize(D('0.01'))
    names = {a for (_, a) in acct}
    v25 = sorted((acct[(2025, a)] for a in names if acct[(2025, a)] > 0), reverse=True)
    every = [a for a in names if all(acct[(y, a)] > 0 for y in YEARS)]
    moved = sum(D(r['amount']) for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'),
                                                            encoding='utf-8'))
                if r['fund'] == '0100' and r['account'].split('-')[2] == '300' and r['source'] == 'BUA'
                and r['fiscal_year'] == '2025' and r['period'] == '12' and D(r['amount']) > 0
                and not r['description'].startswith('ENCUMBRANCE CARRY FORWARD'))
    over26 = -sum(acct[(2026, a)] for a in names if acct[(2026, a)] < 0)
    p = json.load(open(os.path.join(TOPICS, 'surplus-suggestions.json'), encoding='utf-8'))
    facts = {x['id']: x['value']['value'] for x in p['facts'] if x.get('value')}
    want = {'n25': len(v25), 'top': 100.0 * float(v25[0]) / float(sum(v25)), 'every': len(every),
            'mv': moved, 'ov': over26}
    for k, v in want.items():
        if abs(float(facts[k]) - float(v)) > 0.006:
            bad.append('surplus-suggestions %s: page %r, recomputed %r' % (k, facts[k], float(v)))


def burndowns(col):
    """The two burndown pages, from the raw journal: the general fund's budget and cumulative
    spending by period, tied at June to the period-13 spreadsheet's YTD expended; the circuit
    breaker's special education spending before June and in June. The special education
    account list is journal.in_sped_total -- a definition, shared on purpose."""
    import journal as J
    A = J.accounts()
    bud, act = defaultdict(D), defaultdict(D)
    sbud, sact, cb, gfm = defaultdict(D), defaultdict(D), defaultdict(D), defaultdict(D)
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')):
        y, p, a = int(r['fiscal_year']), int(r['period']), D(r['amount'])
        sped = J.in_sped_total(A[r['account']])
        if sped and r['fund'] == '2640' and r['source'] in KIND:
            cb[(y, 'june' if p == 12 else 'early')] += a
        if r['fund'] != '0100' or r['account'].split('-')[2] != '300':
            continue
        if r['source'] in ('BUC', 'BUA'):
            bud[y] += a
            if sped:
                sbud[y] += a
        elif r['source'] in KIND:
            act[(y, p)] += a
            if sped:
                sact[(y, p)] += a
                gfm[(y, p)] += a
    left = lambda b, c, y, p: 100.0 * (1 - float(sum(c[(y, q)] for q in range(p + 1))) / float(b[y]))
    for y in YEARS:
        if sum(act[(y, q)] for q in range(13)) != col[(y, 'ytd_expended')]:
            bad.append('burndown FY%d: June does not tie to the period-13 YTD expended' % y)
    p = json.load(open(os.path.join(TOPICS, 'budget-burndown.json'), encoding='utf-8'))
    facts = {x['id']: x['value']['value'] for x in p['facts'] if x.get('value')}
    want = {'m23': left(bud, act, 2023, 9), 'm24': left(bud, act, 2024, 9),
            'm25': left(bud, act, 2025, 9), 'm26': left(bud, act, 2026, 9),
            'j23': left(bud, act, 2023, 12), 'j26': left(bud, act, 2026, 12)}
    for k, v in want.items():
        if abs(facts[k] - v) > 0.01:
            bad.append('budget-burndown %s: page %r, recomputed %r' % (k, facts[k], v))
    for t in p['chart']['series']:
        y = int(t['name'][2:])
        for i, v in enumerate(t['values']):
            if abs(v - round(left(bud, act, y, i), 1)) > 0.051:
                bad.append('budget-burndown chart %s point %d: %r' % (t['name'], i, v))
    q = json.load(open(os.path.join(TOPICS, 'sped-burndown.json'), encoding='utf-8'))
    facts = {x['id']: x['value']['value'] for x in q['facts'] if x.get('value')}
    want = {'cb0': cb[(2025, 'early')], 'cb1': cb[(2026, 'early')], 'cbj': cb[(2026, 'june')],
            'so0': gfm[(2025, 3)] + gfm[(2025, 4)], 'so1': gfm[(2026, 3)] + gfm[(2026, 4)]}
    for k, v in want.items():
        if abs(facts[k] - float(v)) > 0.006:
            bad.append('sped-burndown %s: page %r, recomputed %r' % (k, facts[k], float(v)))
    bars = {t['name']: t['values'] for t in q['chart']['series']}
    for i, y in enumerate(YEARS):
        for name, key in (('July to May', 'early'), ('June', 'june')):
            if abs(bars[name][i] - float(cb[(y, key)])) > 0.006:
                bad.append('sped-burndown bars %s %d: %r' % (name, y, bars[name][i]))
    for t in q['also'][0]['series']:
        y = int(t['name'][2:])
        for i, v in enumerate(t['values']):
            if abs(v - round(left(sbud, sact, y, i), 1)) > 0.051:
                bad.append('sped-burndown chart %s point %d: %r' % (t['name'], i, v))


def main():
    # ---- route 1: the period-13 spreadsheets
    left, cat, col, acct = defaultdict(D), defaultdict(D), defaultdict(D), defaultdict(D)
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['period'] != '13' or r['report'] != 'gf-school' or r['type'] != 'E':
            continue
        y = int(r['fiscal_year'])
        av = D(r['available_budget']).quantize(D('0.01'))
        left[y] += av
        cat[(y, category_of(r))] += av
        acct[(y, r['account'])] += av
        for c in ('original_approp', 'transfers_adjustments', 'ytd_expended', 'encumbrances'):
            col[(y, c)] += D(r[c]).quantize(D('0.01'))

    # ---- route 2: the journal, raw
    kind, soy, bua, adj = defaultdict(D), defaultdict(D), defaultdict(D), []
    left301 = D(0)
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')):
        if r['fund'] != '0100':
            continue
        dept, y, a = r['account'].split('-')[2], int(r['fiscal_year']), D(r['amount'])
        if dept == '301' and y == Y1:
            left301 += a if r['source'] in ('BUC', 'BUA') else -a
        if dept != '300':
            continue
        if r['source'] in KIND:
            kind[(y, KIND[r['source']])] += a
        if r['source'] == 'SOY':
            soy[y] += a
        if r['source'] == 'BUA':
            bua[y] += a
        if r['source'] == 'BUA' and r['description'] == 'ADJ FY25 BUDGET':
            adj.append(a)
    for y in YEARS:
        if sum(kind[(y, k)] for k in ('pay', 'inv', 'je', 'rec')) != col[(y, 'ytd_expended')]:
            bad.append('FY%d: the journal actuals do not tie to the spreadsheet' % y)
        if bua[y] != col[(y, 'transfers_adjustments')]:
            bad.append('FY%d: the journal transfers do not tie to the spreadsheet' % y)
    carry = {y: soy[y] for y in YEARS}
    other = {y: col[(y, 'transfers_adjustments')] - carry[y] for y in YEARS}
    budget = {y: col[(y, 'original_approp')] + col[(y, 'transfers_adjustments')] for y in YEARS}
    dk = lambda k: kind[(Y1, k)] - kind[(Y0, k)]
    open1 = col[(Y1, 'encumbrances')]

    # Left counting orders owed: a closed year's close moves its open orders into next July's
    # budget, where they arrive as the start-of-year re-encumbrances (SOY) read above. So what
    # a closed year left, counting what it still owed, is its printed figure less the next
    # year's SOY; the open year's printed figure already counts its open orders.
    owed = {y: left[y] - (carry[y + 1] if y + 1 in carry else 0) for y in YEARS}
    # What the Committee was told for FY2025, read from the minutes themselves.
    sc = ' '.join(open(os.path.join(ROOT, 'sources', 'meetings', 'text', 'school-committee',
                                    '2025-09-17-minutes-7408.txt'), encoding='utf-8').read().split())
    told = D(re.search(r'surplus number has gone up to \$([\d,]+\.\d\d)', sc).group(1).replace(',', ''))

    cats = [c[0] for c in CATEGORIES]
    both = [c for c in cats if cat[(Y0, c)] > 0 and cat[(Y1, c)] > 0]
    every = [c for c in cats if all(cat[(y, c)] > 0 for y in YEARS)]
    lead = max(both, key=lambda c: cat[(Y0, c)] + cat[(Y1, c)])
    names = {a for (_, a) in acct}
    a_both = [a for a in names if acct[(Y0, a)] > 0 and acct[(Y1, a)] > 0]
    want = {
        'surplus-bridge': dict(
            dict(('o%d' % y, owed[y]) for y in YEARS),
            p0=left[Y0], p1=left[Y1] + open1, c0=carry[Y1], open=open1, told=told,
            diff=left[Y0] - told, db=budget[Y1] - budget[Y0],
            ds=col[(Y1, 'ytd_expended')] - col[(Y0, 'ytd_expended')]),
        'surplus-repeat-lines': dict(
            n=len(both), b0=sum(cat[(Y0, c)] for c in both), b1=sum(cat[(Y1, c)] for c in both),
            s0=left[Y0], s1=left[Y1], e=len(every),
            e4=sum(cat[(y, c)] for c in every for y in YEARS),
            l0=cat[(Y0, lead)], l1=cat[(Y1, lead)], an=len(a_both),
            ab1=sum(acct[(Y1, a)] for a in a_both)),
    }
    if len(adj) != 1:
        bad.append('expected one ADJ FY25 BUDGET line; found %d' % len(adj))
    # Every money figure the prose may state: the facts, plus the ones the notes and chart use.
    extra = [left[Y1] + col[(Y1, 'encumbrances')], left[Y0] - left[Y1], left301, left[Y1] + left301, -left301] + [carry[y] for y in YEARS[1:]] \
        + [owed[Y0] - owed[Y1], left[Y1] + open1 - left[Y0], dk('pay'), dk('inv'), dk('je'), -sum(adj)] \
        + [budget[Y1] - budget[Y0]] \
        + [col[(Y1, 'original_approp')] - col[(Y0, 'original_approp')]]
    money = {'$' + format(abs(round(float(v))), ',') for f in want.values() for v in f.values()}
    money |= {'$' + format(abs(round(float(v))), ',') for v in extra}
    money.add('$' + format(told, ',.2f'))   # quoted to the cent, as the minutes print it
    pct = lambda a, b, dp: '%.*f%%' % (dp, 100.0 * float(a) / float(b))
    top = sorted(a_both, key=lambda a: -(acct[(Y0, a)] + acct[(Y1, a)]))[:30]
    percents = {pct(dk('pay'), kind[(Y0, 'pay')], 1), pct(dk('inv'), kind[(Y0, 'inv')], 1),
                pct(dk('pay'), col[(Y1, 'ytd_expended')] - col[(Y0, 'ytd_expended')], 0),
                pct(want['surplus-repeat-lines']['b0'], left[Y0], 0),
                pct(sum(acct[(y, a)] for a in top for y in (Y0, Y1)),
                    sum(acct[(y, a)] for a in a_both for y in (Y0, Y1)), 0)}

    for tid, fig in want.items():
        p = json.load(open(os.path.join(TOPICS, '%s.json' % tid), encoding='utf-8'))
        facts = {x['id']: x for x in p['facts']}
        for k, v in fig.items():
            got = facts[k]['value']['value']
            if abs(float(got) - float(v)) > 0.006:
                bad.append('%s %s: page %r, recomputed %r' % (tid, k, got, float(v)))
        units = [p['finding']] + p['conclusions'] + [n for cc in p['conclusions']
                                                    for n in cc.get('notes', [])]
        for u in units:
            for f in u['figures'].values():
                t = f['text'].lstrip('-')
                if t.endswith('%') and t not in percents:
                    bad.append('%s: %r in %r is not a recomputed share' % (tid, t, u['text'][:60]))
                if t.startswith('$') and t not in money:
                    bad.append('%s: %r in %r is not a recomputed figure' % (tid, t, u['text'][:60]))
        for v in (p.get('table') or {}).get('views', []):
            if v['key'] != 'accounts':
                continue
            if [r['cells'][0] for r in v['rows']] != top:
                bad.append('%s: the account table is not the 30 largest by the spreadsheet' % tid)
            for r in v['rows']:
                a = r['cells'][0]
                for cell, y in zip(r['cells'][1:3], (Y0, Y1)):
                    if cell != '$' + format(round(float(acct[(y, a)])), ','):
                        bad.append('%s: account %s %d reads %s; the spreadsheet %s'
                                   % (tid, a, y, cell, acct[(y, a)]))
        units += [c['so'] for c in p['conclusions'] if c.get('so')]
        for u in units[-4:]:
            for f in u['figures'].values():
                t = f['text'].lstrip('-')
                if (t.startswith('$') and t not in money) or (t.endswith('%') and t not in percents):
                    bad.append('%s: %r in a meaning is not a recomputed figure' % (tid, t))
        ch = p['chart']
        if tid == 'surplus-bridge':
            tr = {t['name']: t['values'] for t in ch['series']}
            if [round(v, 2) for v in tr['Counting orders owed']] != [round(float(owed[y]), 2) for y in YEARS]:
                bad.append('%s: the owed track is not the spreadsheet less next July’s SOY' % tid)
            printed = [v for v in tr['As a closed year’s report prints it'] if v is not None]
            if [round(v, 2) for v in printed] != [round(float(left[y]), 2) for y in YEARS[:-1]]:
                bad.append('%s: the printed track is not the closed reports' % tid)
            ch = next(b['spec'] for b in p.get('blocks', []) if b['block'] == 'chart'
                      and b['spec']['type'] == 'bridge')
        if ch['type'] == 'bridge':
            if abs(ch['start']['value'] - float(left[Y0])) > 0.006 or \
                    abs(ch['end']['value'] - float(left[Y1])) > 0.006:
                bad.append('%s: the bridge does not start and end on the spreadsheet' % tid)
            want_steps = [col[(Y1, 'original_approp')] - col[(Y0, 'original_approp')],
                          carry[Y1] - carry[Y0], other[Y1] - other[Y0], -dk('pay'), -dk('inv'),
                          -dk('je'), -dk('rec'), -open1]
            for s, w in zip(ch['steps'], want_steps):
                if abs(s['value'] - float(w)) > 0.006:
                    bad.append('%s: bridge step %r is %r, recomputed %r'
                               % (tid, s['label'], s['value'], float(w)))
        else:
            for r in ch['rows']:
                c = next(k for k, lab, *_ in CATEGORIES if lab == r['label'])
                for v, y in zip(r['values'], (Y0, Y1)):
                    if abs(v - float(cat[(y, c)])) > 0.006:
                        bad.append('%s: %s %d is %r, recomputed %r' % (tid, c, y, v, float(cat[(y, c)])))
            if len(ch['rows']) != len(both):
                bad.append('%s: the chart draws %d categories; %d were under both years'
                           % (tid, len(ch['rows']), len(both)))

    burndowns(col)
    prepaid(owed, left)
    suggestions(left, cat)
    why_left(cat, acct)
    if bad:
        print('verify_journal_surplus_topics: %d problem(s)' % len(bad))
        print('\n'.join('  ' + b for b in bad))
        return 1
    n = sum(len(v) for v in want.values())
    print('verify_journal_surplus_topics: %d facts, every bridge step and every chart bar '
          'recomputed from the period-13 spreadsheets and the raw journal; FY2023-FY2026 tie '
          'on actuals and transfers' % n)
    return 0



def prepaid(owed, left):
    """/fy2026-closeout/fy2026-tuition-paid-early, from the raw journal CSV: the nine FLLAC
    invoices numbered 27..., the 29 June reclass, the line before 30 June, and the surplus with
    the payment taken out. Shares nothing with the generator but the file."""
    COLLAB = '0100-3-300-9400-51-1-06-2-535023'
    rows = list(csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')))
    early = [r for r in rows if r['doc_no'].startswith('27L2KEY')]
    paid = sum(D(r['amount']) for r in early)
    recl = sum(D(r['amount']) for r in rows if r['fiscal_year'] == '2026' and r['fund'] == '0100'
               and r['source'] == 'GEN' and 'RECLASS COLLABORATIVE' in r['description'])
    line = [r for r in rows if r['account'] == COLLAB and r['fiscal_year'] == '2026']
    budget = sum(D(r['amount']) for r in line if r['source'] in ('BUC', 'BUA'))
    before = sum(D(r['amount']) for r in line if r['source'] in KIND
                 and r['effective_date'] < '2026-06-30')
    want = {'paid': paid, 'recl': -recl, 'before': before, 'budget': budget, 'left': left[Y1],
            'without': left[Y1] + paid, 'owed25': owed[Y0]}
    p = json.load(open(os.path.join(TOPICS, 'fy2026-tuition-paid-early.json'), encoding='utf-8'))
    facts = {x['id']: x for x in p['facts']}
    if len(early) != 9 or {r['effective_date'] for r in early} != {'2026-06-30'} \
            or {r['account'] for r in early} != {COLLAB}:
        bad.append('tuition-paid-early: the 27-numbered invoices are not nine, on 30 June, on '
                   'the general fund collaborative line')
    if facts['n']['value']['value'] != len(early):
        bad.append('tuition-paid-early: the page counts %r invoices' % facts['n']['value']['value'])
    for k, v in want.items():
        got = facts[k]['value']['value']
        if abs(float(got) - float(v)) > 0.006:
            bad.append('tuition-paid-early %s: page %r, recomputed %r' % (k, got, float(v)))


def why_left(cat, acct):
    """The hub's "Why it was left" block, /fy2026-closeout: every dollar in it, recomputed from
    the period-13 spreadsheets (category nets, the two tuition accounts) and the raw journal
    (May Institute by fund, the 27-numbered FLLAC invoices). Every money figure in the block
    must be one of these, and every one of these must be in the block."""
    PRIV, COLL = '0100-3-300-9300-51-1-06-2-535019', '0100-3-300-9400-51-1-06-2-535023'
    budget = defaultdict(D)
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['period'] == '13' and r['report'] == 'gf-school' and r['fiscal_year'] == '2026':
            budget[r['account']] += D(r['revised_budget']).quantize(D('0.01'))
    may, early = defaultdict(D), D(0)
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')):
        if r['source'] == 'API' and 'MAY INST' in r['vendor'].upper():
            may[(int(r['fiscal_year']), r['fund'] == '0100')] += D(r['amount'])
        if r['doc_no'].startswith('27L2KEY') and r['fund'] == '0100':
            early += D(r['amount'])
    c = lambda y, *ks: sum(cat[(y, k)] for k in ks)
    sal = c(Y1, 'teachers', 'counselors', 'paras', 'admin', 'custodians', 'athletics_staff',
            'other_staff')
    aides = -sum(acct[(Y1, a)] for (y, a) in list(acct) if y == Y1 and acct[(y, a)] < 0
                 and a.split('-')[3] == '2330' and a.split('-')[-1].startswith('51'))
    want = [acct[(Y1, PRIV)], budget[PRIV], may[(2025, True)], may[(2026, False)],
            -acct[(Y1, COLL)], early, sal, aides, c(Y1, 'buildings', 'supplies'),
            c(Y1, 'benefits'), -c(2023, 'benefits'), -c(2024, 'benefits'),
            -c(Y1, 'sped_services', 'transport', 'utilities'), sum(acct[(Y1, a)] for (y, a) in acct if y == Y1)]
    want = {'$' + format(round(v), ',') for v in want}
    p = json.load(open(os.path.join(TOPICS, 'fy2026-closeout.json'), encoding='utf-8'))
    blk = [b for b in p.get('blocks', []) if b.get('title') == 'Why it was left']
    if len(blk) != 1:
        bad.append('fy2026-closeout: no "Why it was left" block')
        return
    text = ' '.join([r['why']['text'] for r in blk[0]['rows']] + [blk[0]['note']['text']])
    got = set(re.findall(r'\$[\d,]+', text))
    if got != want:
        bad.append('why it was left: in the block, not recomputed %s; recomputed, not in the block %s'
                   % (sorted(got - want), sorted(want - got)))

if __name__ == '__main__':
    sys.exit(main())
