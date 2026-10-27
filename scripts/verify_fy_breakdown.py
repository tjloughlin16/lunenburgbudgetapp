#!/usr/bin/env python3
"""Recompute the FY breakdown by a second route, and fail if any figure differs.

    python3 scripts/verify_fy_breakdown.py

The generator (`fy_breakdown.py`, `build_fy_breakdown.py`) reads the journal through
`journal.py`. This reads the two CSVs with csv and Decimal and re-derives every definition
itself -- source codes, the scope, the footing, the payee key, the voted function codes, the
three match rules -- sharing ONLY the category definition (`build_school_surplus.category_of`),
which is what makes a category here the category on the published surplus pages. It asserts:

  1. every line's four parts sum to what the period-13 `gf-school` spreadsheet prints as
     available, less the orders the close zeroed (read here off NEXT July's `SOY` lines, not
     the `YEC` lines the generator reads), so the owed footing is tied by another document;
  2. each year's four totals sum to that year's surplus on the same footing;
  3. every line's four parts equal the ones recomputed here, to the cent;
  4. the two worked cases in notes/HANDOFF-FY-BREAKDOWN.md, exactly;
  5. every figure the payload prints, if it has been written (`--no-payload` skips it);
  6. the line files: every line's school-budget rows sum to what the CSV says it spent, and
     the weekly chart's bars to those rows.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_school_surplus import category_of  # noqa: E402  (the one shared definition)

DATA = os.path.join(ROOT, 'sources', 'data')
D0, CENT = Decimal(0), Decimal('0.01')
YEARS = (2023, 2024, 2025, 2026)
OPEN = 2026
PRIVATE = '0100-3-300-9300-51-1-06-2-535019'
COLLAB = '0100-3-300-9400-51-1-06-2-535023'
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', 'fy-breakdown.json')
bad = []


def check(ok, msg):
    if not ok:
        bad.append(msg)


def raw():
    acc = {a['account']: a for a in csv.DictReader(
        open(os.path.join(DATA, 'munis-school-journal-accounts.csv'), encoding='utf-8'))}
    rows = []
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')):
        r['y'], r['v'] = int(r['fiscal_year']), Decimal(r['amount'])
        rows.append(r)
    return acc, rows


def in_scope(acct):
    p = acct.split('-')
    return p[0] == '0100' and p[2] == '300'


def fn(acct):
    return acct.split('-')[3]


def cat(acct):
    return category_of(dict(account=acct, obj=acct.split('-')[-1]))


def key(r):
    """The payee: None for no payee, '' for a masked one."""
    if r['ref_type'] != 'VND':
        return None
    v = r['vendor'].strip()
    if v in ('', 'individual (redacted)'):
        return ''
    k = ' '.join(v.upper().split()).rstrip('.,;')
    return {'FLLAC EDUCATIONAL CO': 'FLLAC (KEYSTONE)'}.get(k, k)


def capital(fund):
    return fund[:2] in ('30', '31', '81', '90')


def recompute():
    acc, rows = raw()
    ex = [r for r in rows if acc[r['account']]['object'].startswith('5')]
    SPENT = {'API', 'APM', 'PRJ', 'PRH', 'GEN', 'GRV', 'CRP', 'POE', 'POL', 'POM', 'SOY', 'GEL'}
    # voted function codes: any 0100 expense budget posting, headings (x000) excluded
    voted = {fn(r['account']) for r in ex if r['fund'] == '0100' and r['source'] in ('BUC', 'BUA')
             and r['v'] != 0 and not fn(r['account']).endswith('000')}

    def is_line(code):
        return code in voted and code != '0000'

    pieces = defaultdict(lambda: defaultdict(Decimal))
    soy_docs = defaultdict(set)
    for r in ex:
        if in_scope(r['account']) and r['source'] == 'SOY':
            soy_docs[(r['y'], r['account'])].add(r['doc_no'])
    for r in ex:
        if not in_scope(r['account']):
            continue
        k, s, p = (r['y'], r['account']), r['source'], pieces[(r['y'], r['account'])]
        d = r['description']
        if s == 'BUC' or (s == 'BUA' and r['journal'] == '2025/01/000564' and r['y'] == 2025):
            p['V'] += r['v']
        elif s == 'BUA' and d.startswith('ENCUMBRANCE CARRY FORWARD'):
            p['CF'] += r['v']
        elif s == 'BUA':
            p['T'] += r['v']
        elif s in SPENT:
            p['G'] += r['v']
            if r['doc_no'] in soy_docs[k] and s in ('SOY', 'POL', 'POM', 'POE', 'GEL'):
                p['CE'] += r['v']
                if s == 'POL':
                    p['CP'] -= r['v']
            m = re.match(r'(\d\d)L2KEY', r['doc_no'])
            if s in ('API', 'APM') and m and int(m.group(1)) > r['y'] % 100:
                p['PP'] += r['v']

    O = defaultdict(Decimal)          # (y, account) -> other funds placed
    F = defaultdict(Decimal)          # (y, category) -> rule c
    used = set()
    back = defaultdict(Decimal)       # (y, account, fund) -> cost moved back onto the line
    paidf = defaultdict(Decimal)      # (y, account, fund) -> placed by payee
    js = defaultdict(list)
    for i, r in enumerate(ex):
        if r['source'] in ('GEN', 'GRV'):
            js[(r['y'], r['journal'])].append((i, r))
    for _, ir in js.items():
        rs = [r for _, r in ir]
        if len({r['fund'] for r in rs}) < 2 or abs(sum(r['v'] for r in rs)) > 1:
            continue
        sc = [r for r in rs if in_scope(r['account'])]
        if not sc or len(sc) == len(rs):
            continue
        # measured on the school side: each school line's own posting in the entry; a cost
        # taken OFF a line (negative) is that line's cost now paid by another fund
        lose = defaultdict(Decimal)
        for i, r in ir:
            if not in_scope(r['account']):
                lose[r['fund']] += r['v']
        lose = {f: -v for f, v in lose.items() if v < 0}
        # each school account's net in the entry: one line can be debited and credited at once
        net = defaultdict(Decimal)
        for i, r in ir:
            if in_scope(r['account']):
                net[(r['y'], r['account'])] += r['v']
            else:
                used.add(i)
        for (y_, a_), v in net.items():
            if v < 0:
                O[(y_, a_)] -= v
            elif v > 0 and lose:
                # moved BACK onto the line: from the funds that gave, in proportion
                for f, w in lose.items():
                    back[(y_, a_, f)] += v * w / sum(lose.values())
    paid = defaultdict(lambda: defaultdict(Decimal))
    for r in ex:
        if in_scope(r['account']) and r['source'] in ('API', 'APM') and key(r):
            paid[key(r)][r['account']] += r['v']
    for i, r in enumerate(ex):
        if i in used or in_scope(r['account']) or r['source'] not in SPENT:
            continue
        k = key(r)
        if k and k in paid and not capital(r['fund']):
            g = paid[k]
            cand = [a for a in g if fn(a) == fn(r['account'])] or list(g)
            best = max(cand, key=lambda a: (g[a], a))
            O[(r['y'], best)] += r['v']
            paidf[(r['y'], best, r['fund'])] += r['v']
        elif not capital(r['fund']) and is_line(fn(r['account'])):
            F[(r['y'], cat(r['account']))] += r['v']

    # a fund's direct payment moved back onto the same line is the school budget's cost
    for (y, a_, f), b in back.items():
        n = min(b, paidf[(y, a_, f)])
        if n > 0:
            O[(y, a_)] -= n
    out = {}
    for k in list(O):
        pieces[k]
    for k, p in pieces.items():
        cost = p['G'] - p['PP'] - p['CP'] - p['CE']
        out[k] = dict(voted_above_cost=p['V'] - cost - O[k], transfers=p['T'],
                      other_funds=O[k], another_year=p['CF'] - p['CP'] - p['CE'] - p['PP'],
                      prepaid=p['PP'])
    return out, F


def printed():
    """(y, account) -> the period-13 `available_budget`, and the orders the close zeroed, read
    off next July's SOY lines."""
    av = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['report'] == 'gf-school' and r['type'] == 'E' and r['period'] == '13':
            av[(int(r['fiscal_year']), r['account'])] = Decimal(r['available_budget']).quantize(CENT)
    acc, rows = raw()
    owed = defaultdict(Decimal)
    for r in rows:
        if r['source'] == 'SOY' and in_scope(r['account']):
            owed[(r['y'] - 1, r['account'])] += r['v']
    return av, owed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-payload', action='store_true')
    args = ap.parse_args(argv)
    import fy_breakdown as FB          # the generator's model, compared against, never trusted
    m = FB.model()
    mine, F = recompute()
    av, owed = printed()
    T = FB.TERMS
    gen = {(r['fy'], r['account']): r for r in m['rows'] if r['account']}
    for k in set(gen) | set(mine):
        g, me = gen.get(k), mine.get(k)
        if g is None or me is None:
            check(False, 'FY%d %s is in one route only' % k)
            continue
        for t in T:
            d = abs(g[t] - me[t])
            # a move back shared over several funds: its cents fall where the generator's
            # largest remainder puts them
            check(d < Decimal('0.05') if t in ('other_funds', 'voted_above_cost') else d == 0,
                  'FY%d %s %s: generator %s, recomputed %s' % (k[0], k[1], t, g[t], me[t]))
        target = av.get(k, D0) - (owed.get(k, D0) if k[0] != OPEN else D0)
        check(sum(g[t] for t in T) == target,
              'FY%d %s: parts sum %s; the period-13 report less orders owed gives %s'
              % (k[0], k[1], sum(g[t] for t in T), target))
    for (y, c), v in F.items():
        g = sum((r['other_funds'] for r in m['rows'] if r['fy'] == y and r['account'] is None
                 and r['category'] == c), D0)
        check(abs(g - v) < CENT, 'FY%d %s: same-function money %s vs %s' % (y, c, g, v))
    for y in YEARS:
        target = sum((v for (yy, _), v in av.items() if yy == y), D0) - (
            sum((v for (yy, _), v in owed.items() if yy == y), D0) if y != OPEN else D0)
        tot = m['years'][y]
        check(sum(tot['terms'].values()) == target == tot['left'],
              'FY%d: four totals %s, left %s, period-13 route %s'
              % (y, sum(tot['terms'].values()), tot['left'], target))
    # the worked cases
    p, c = gen[(2026, PRIVATE)], gen[(2026, COLLAB)]
    check(p['voted'] == Decimal('988630.00') and p['transfers'] == 0
          and p['other_funds'] == Decimal('287107.65') and p['left'] == Decimal('522629.18')
          and p['voted_above_cost'] == Decimal('235521.53'),
          'private tuition FY2026 no longer reproduces 988,630 - 753,108.47 + 287,107.65')
    check(dict(p['payers']) == {('payee', 'IDEA (special education)'): Decimal('287107.65')},
          'private tuition FY2026: the other-fund money is not all the IDEA grant')
    check(c['by_rule']['moved'] == Decimal('333494.89') and c['prepaid'] == Decimal('189276.75')
          and c['left'] == Decimal('-434107.56'),
          'collaborative tuition FY2026: reclass 333,494.89 / prepaid 189,276.75 / left -434,107.56')
    if not args.no_payload:
        payload_checks(m)
        line_file_checks()
        plan_checks()
        source_checks()
        overlap_checks()
    if bad:
        print('verify_fy_breakdown: %d FAILED' % len(bad))
        for b in bad[:40]:
            print('  ' + b)
        return 1
    print('verify_fy_breakdown: %d lines in %d years, every part recomputed and tied to the '
          'period-13 report' % (len(gen), len(YEARS)))
    return 0


def payload_checks(m):
    if not os.path.exists(PAYLOAD):
        check(False, 'no payload at %s (run build_fy_breakdown.py, or pass --no-payload)' % PAYLOAD)
        return
    import build_fy_breakdown as B
    text = open(PAYLOAD, encoding='utf-8').read()
    check(text == B.render(m), 'the payload does not reproduce from the model')
    p = json.loads(text)
    yr = {y: sum((r['left'] for r in m['rows'] if r['fy'] == y), D0) for y in YEARS}
    # every dollar figure the page prints, against the recomputed route
    mine, _ = recompute()
    left26 = sum((mine[k]['voted_above_cost'] + mine[k]['transfers'] + mine[k]['other_funds']
                  + mine[k]['another_year'] for k in mine if k[0] == 2026), D0)
    check('$%s' % format(round(left26), ',d') in p['finding']['text'],
          'the finding does not carry FY2026 left, recomputed %s' % left26)
    check(abs(left26 - yr[2026]) < 1, 'FY2026 left: model %s, recomputed %s' % (yr[2026], left26))
    # the weekly chart: each year's bars, summed, are the line files' rows, re-charges apart
    weeks = next(b for b in p['blocks'] if b.get('component') == 'fy-year-weeks')['data']
    for col in weeks['years']:
        y = int(col['fy'][2:])
        f = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'fy-breakdown',
                                        'lines-%d.json' % y), encoding='utf-8'))
        school = f['funds'].index('School budget')
        rech = {i for i, k in enumerate(f['kinds']) if k.startswith('Re-charged')}
        spend = sum((Decimal(str(x[8])) for L in f['lines'].values() for x in L['r'] if x[2] not in rech), Decimal(0))
        off = sum((Decimal(str(x[8])) for L in f['lines'].values() for x in L['r']
                   if x[2] in rech and x[6] == school and x[8] < 0), Decimal(0))
        drawn = sum((Decimal(str(v)) for w in col['weeks'] for _, v in w['f']), Decimal(0))
        drawn_rc = sum((Decimal(str(w['rc'])) for w in col['weeks']), Decimal(0))
        check(abs(drawn - spend) < 1 and abs(drawn_rc - off) < 1,
              'weekly %s draws %s and %s re-charged; the line files hold %s and %s'
              % (col['fy'], drawn, drawn_rc, spend, off))


def plan_checks():
    """Level 1, the plan against what happened, by routes of its own:
      - the circuit breaker each book counted on, re-read here by splitting the printed line into
        tokens, and tied to collaborative tuition's voted figure summed off the raw CSV;
      - each year's Left against this file's own recomputation;
      - every circuit breaker dollar (fund 2640, payments plus what was still owed at year end)
        lands once: on collaborative tuition, on another line, or matched to no line."""
    p = json.load(open(PAYLOAD, encoding='utf-8'))
    blk = next((b for b in p['blocks'] if b.get('component') == 'fy-plan'), None)
    if blk is None:
        check(False, 'no fy-plan block in the payload')
        return
    d = blk['data']
    acc, rows = raw()
    mine, _ = recompute()
    vote = defaultdict(Decimal)
    for r in rows:
        # voted, as recompute() reads it: the original budget, and the one FY2025 adjustment
        # that was the vote itself
        if r['fund'] == '0100' and r['account'].endswith('-535023') and (
                r['source'] == 'BUC' or (r['source'] == 'BUA' and r['journal'] == '2025/01/000564'
                                         and r['y'] == 2025)):
            vote[r['y']] += r['v']
    cb = defaultdict(Decimal)
    for r in rows:
        if r['fund'] == '2640' and r['object'].startswith('5'):
            if r['posts_to'] == 'actual':
                cb[('paid', r['y'])] += r['v']
            elif r['posts_to'] == 'encumbrance':
                cb[('open', r['y'])] += r['v']
                if r['source'] == 'SOY':
                    cb[('soy', r['y'])] += r['v']
    tok = lambda s: [Decimal(t.strip('-$()').replace(',', '')) * (-1 if t.startswith(('(', '-')) else 1)
                     for t in s.replace('$', ' $').split() if re.fullmatch(r'-?\(?\$?[\d,]+(\.\d+)?\)?\$?', t)]
    for y in d['years']:
        fy = int(y['fy'][2:])
        book = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                            os.path.basename(y['book'])[:-4] + '.txt')
        text = open(book, encoding='utf-8').read().split('\n')
        i = int(y['book_line']) - 1
        check(text[i].startswith('Collaborative Tuitions'), '%s: line %s is not collaborative tuition'
              % (y['fy'], y['book_line']))
        nxt = text[i + 1]
        if nxt.startswith('Circuit Breaker'):
            gross = [t for t in tok(text[i]) if t > 0]
            offs = [-t for t in tok(nxt.split(')', 2)[-1]) if t < 0]
            ok = [o for o in offs for g in gross if abs(g - o - vote[fy]) < Decimal('0.5')]
            check(y['cb']['plan'] is not None and ok and abs(Decimal(str(y['cb']['plan'])) - ok[0]) < CENT,
                  '%s: the book counts on %s of circuit breaker; the page says %s'
                  % (y['fy'], ok, y['cb']['plan']))
        else:
            check(y['cb']['plan'] is None, '%s: the book prints no circuit breaker line; the page '
                  'says it counted on %s' % (y['fy'], y['cb']['plan']))
        left = sum((mine[k]['voted_above_cost'] + mine[k]['transfers'] + mine[k]['other_funds']
                    + mine[k]['another_year'] for k in mine if k[0] == fy), D0)
        check(abs(Decimal(str(y['gf']['left'])) - left) < 1,
              '%s: Left %s, recomputed %s' % (y['fy'], y['gf']['left'], left))
        check(abs(Decimal(str(y['gf']['budget'] - y['gf']['spent'] - y['gf']['left']))) < CENT,
              '%s: budget less spent is not left' % y['fy'])
        # owed at year end: next year's SOY where the journal has next year, else what is open
        owed = cb[('soy', fy + 1)] if fy + 1 in YEARS else cb[('open', fy)]
        o = next(x for x in y['others'] if x['id'] == 'cb')
        drawn = sum((Decimal(str(v)) for v in (y['cb']['paid'], o['start'], o['later'], o['unmatched'])), D0)
        check(abs(drawn - cb[('paid', fy)] - owed) < CENT,
              '%s: circuit breaker drawn %s; fund 2640 paid %s and owed %s'
              % (y['fy'], drawn, cb[('paid', fy)], owed))


def source_checks():
    """The table of other funds: each fund's total recomputed straight off the CSV -- every
    expense posting outside the school budget's lines, payments and orders, the year-end closing
    entries left out (the owed footing) -- and every fund that spent anything is in the table."""
    p = json.load(open(PAYLOAD, encoding='utf-8'))
    blk = next((b for b in p['blocks'] if b.get('component') == 'fy-source-table'), None)
    if blk is None:
        check(False, 'no fy-source-table block in the payload')
        return
    acc, rows = raw()
    want = defaultdict(Decimal)
    for r in rows:
        if (not in_scope(r['account']) and acc[r['account']]['object'].startswith('5')
                and r['posts_to'] in ('actual', 'encumbrance') and r['source'] != 'YEC'):
            want[(r['y'], r['fund'])] += r['v']
    for y in blk['data']['years']:
        fy = int(y['fy'][2:])
        got = {r['key']: Decimal(str(r['n']['total'])) for r in y['rows']}
        for (yy, f), v in want.items():
            if yy != fy or abs(v) < Decimal('0.5'):
                continue
            check(f in got and abs(got[f] - v) < CENT,
                  '%s fund %s: the table says %s, the CSV gives %s' % (y['fy'], f, got.get(f), v))
        check(not set(got) - {f for (yy, f) in want if yy == fy},
              '%s: the table lists funds the CSV has no spending for' % y['fy'])


def overlap_checks():
    """The overlap bands hold exactly the dollars the table of funds holds, year by year; and the
    money on overlapping lines is the same bills and the same payees -- a function code places on
    a category, not a line."""
    p = json.load(open(PAYLOAD, encoding='utf-8'))
    blk = {b.get('component'): b['data'] for b in p['blocks'] if b.get('component')}
    if 'fy-overlap' not in blk:
        check(False, 'no fy-overlap block in the payload')
        return
    for oy, sy in zip(blk['fy-overlap']['years'], blk['fy-source-table']['years']):
        bands = sum((Decimal(str(v)) for v in oy['all']['n'].values()), D0)
        table = sum((Decimal(str(r['n']['total'])) for r in sy['rows']), D0)
        check(abs(bands - table) < Decimal('0.05'), '%s: bands %s, table of funds %s' % (oy['fy'], bands, table))
        n = oy['all']['n']
        # a bill sent back ends as the school budget's own spending, so it is on no line as
        # other funds' money: the lines hold exactly the same bills and the same payees
        check(abs(Decimal(str(oy['lines']['other_v'])) - Decimal(str(n['bills'])) - Decimal(str(n['payee'])))
              < Decimal('0.05'),
              '%s: other funds on overlapping lines %s; the same bills and payees %s'
              % (oy['fy'], oy['lines']['other_v'], n['bills'] + n['payee']))


def line_file_checks():
    """Every line's rows in /data/fy-breakdown/lines-<year>.json: the school budget's rows sum to
    what the line spent, recomputed here straight off the CSV."""
    acc, rows = raw()
    SPENT = {'API', 'APM', 'PRJ', 'PRH', 'GEN', 'GRV', 'CRP', 'POE', 'POL', 'POM', 'SOY', 'GEL'}
    spent = defaultdict(Decimal)
    for r in rows:
        if in_scope(r['account']) and acc[r['account']]['object'].startswith('5') and r['source'] in SPENT:
            spent[(r['y'], r['account'])] += r['v']
    for y in YEARS:
        path = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy-breakdown', 'lines-%d.json' % y)
        if not os.path.exists(path):
            check(False, 'no line file %s' % path)
            continue
        f = json.load(open(path, encoding='utf-8'))
        school = f['funds'].index('School budget')
        for k, v in spent.items():
            if k[0] != y or v == 0:
                continue
            got = sum((Decimal(str(x[8])) for x in f['lines'].get(k[1], {}).get('r', []) if x[6] == school),
                      Decimal(0))
            check(abs(got - v) < CENT, 'FY%d %s: the line file lists %s for the school budget; the '
                  'CSV gives %s' % (y, k[1], got, v))


if __name__ == '__main__':
    sys.exit(main())
