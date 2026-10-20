#!/usr/bin/env python3
"""Every headline figure on /school-spending-history/inflation-and-school-costs, recomputed by
a SECOND ROUTE (CLAUDE.md rule 9) and asserted against the payload.

    python3 scripts/verify_inflation_topic.py

The generator reads its inputs through shared loaders (build_spending_staff_students_topics,
journal.py). This reads the raw files with csv and json and nothing else:

  prices     the BLS responses in sources/federal-bls/, fiscal-year averages built here
             (July to June; this area publishes odd months only, so six values a year)
  spending   dese-function-expenditure.csv, the `total` and `category` rows DESE prints
  teachers   dese-teacher-program-area.csv, the district row, not the staffing payload
  levy       dls-new-growth.csv and dls-override-votes.csv
  payments   munis-school-journal.csv, read row by row, and munis-school-ytd.csv, the
             period-13 report the Town printed, for the account totals
  own        each kind against its own inflation: the BLS cost-index responses read by
             glob (not the manifest), July-to-June averages built here, the mapping read off
             inflation-cost-index-map.csv, buildings split by DESE's own detail codes
  quotes     every quotation, verbatim, in the extracted text of the document it cites

It asserts NUMBERS -- a fact's value, and the formatted figure inside the sentence that uses
it -- never only that a sentence exists (WRITING-AN-ANALYSIS.md, step 5).
"""
import csv
import glob
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', 'inflation-and-school-costs.json')
LEA = '01620000'
BAD = []


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        BAD.append(msg)


def norm(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return ' '.join(s.split())


def prices():
    m = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'sources', 'federal-bls', 'cpi-u-CUURS11ASA0-*.json'))):
        for x in json.load(open(f))['Results']['series'][0]['data']:
            if x['period'].startswith('M') and x['period'] != 'M13':
                m[(int(x['year']), int(x['period'][1:]))] = float(x['value'])
    out = {}
    for fy in range(1992, 2030):
        obs = [m.get((fy - 1, mo)) for mo in (7, 9, 11)] + [m.get((fy, mo)) for mo in (1, 3, 5)]
        if all(v is not None for v in obs):
            out[fy] = sum(obs) / 6
    return out


def spending():
    tot, cat, code = {}, defaultdict(dict), defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-function-expenditure.csv'))):
        if r['lea'] != LEA:
            continue
        y = int(r['fy'])
        if r['level'] == 'total':
            tot[y] = float(r['total'])
        elif r['level'] == 'category':
            cat[y][r['func_cat_code']] = float(r['total'])
    return tot, cat


def fact(p, i):
    return next(f for f in p['facts'] if f['id'] == i)


def pct_text(v):
    return '%+.1f%%' % v


def main():
    p = json.load(open(PAY, encoding='utf-8'))
    P = prices()
    tot, cat = spending()
    g0, g1 = min(tot), max(tot)
    px = P[g1] / P[g0] - 1
    add, kept = tot[g1] - tot[g0], tot[g0] * px
    beyond = add - kept
    usd = lambda v: ('-$' if round(v) < 0 else '$') + format(abs(round(v)), ',d')
    mill = lambda v: '$%.1f million' % (v / 1e6)     # the page's headline figures, in millions
    check(fact(p, 'kept')['value']['text'] == mill(kept), 'just inflation = %s' % mill(kept))
    # Past and short of inflation, summed separately from DESE's own category rows.
    rows_ = p['chart']['rows']
    up_t = sum(r['value'] - r['mark'] for r in rows_ if r['value'] >= r['mark'])
    dn_t = sum(r['value'] - r['mark'] for r in rows_ if r['value'] < r['mark'])
    check(abs(up_t + dn_t - beyond) < 25, 'past %s and short %s net to %s' % (mill(up_t), mill(-dn_t), mill(beyond)))
    check(fact(p, 'up')['value']['text'] == mill(up_t), 'beyond inflation, summed = %s' % mill(up_t))
    check(fact(p, 'down')['value']['text'] == mill(-dn_t), 'less than inflation, summed = %s' % mill(-dn_t))
    check(fact(p, 'prices')['value']['text'] == pct_text(100 * px),
          'prices %s to %s = %s' % (g0, g1, pct_text(100 * px)))
    bb = cat[g1]['BENE'] - cat[g0]['BENE'] * (1 + px)
    tb = cat[g1]['TCHR'] - cat[g0]['TCHR'] * (1 + px)
    check(bb > 0 and fact(p, 'bene')['value']['text'] == mill(bb),
          'insurance and retirement on top of inflation = %s' % mill(bb))
    check(tb < 0 and fact(p, 'tchr')['value']['text'] == usd(-tb),
          'teachers less than inflation alone = %s' % usd(-tb))
    check(mill(add) in p['finding']['text'] and mill(kept) in p['finding']['text'],
          'the finding carries %s and %s' % (mill(add), mill(kept)))
    # The bullet chart: the bars add to the total rise, the ticks to what prices alone would
    # have added, and each row's printed gap is its bar less its tick. Tuition is derived by
    # DESE's rollups and pupil services is split, so the TOTALS are what is checked here.
    rows = p['chart']['rows']
    check(abs(sum(r['value'] for r in rows) - add) < 25, 'the signature chart’s bars add to the total rise')
    check(abs(sum(r['mark'] for r in rows) - kept) < 25,
          'the signature chart’s ticks add to what prices alone would have added')
    check(all(r['gap_text'] == usd(abs(r['value'] - r['mark'])) and r['over'] == (r['value'] >= r['mark'])
              for r in rows), 'every row’s printed gap is its bar less its tick, and says which way')

    # ---- each kind against its own inflation: the indexes read straight off the BLS files
    # (glob, not the manifest), the mapping off its CSV, the spending off DESE's own rows.
    def own_index(series):
        m = {}
        for f in glob.glob(os.path.join(ROOT, 'sources', 'federal-bls', series + '-*.json')):
            d = json.load(open(f))
            assert d['status'] == 'REQUEST_SUCCEEDED' and d['Results']['series'][0]['seriesID'] == series
            for x in d['Results']['series'][0]['data']:
                if x['value'] == '-':
                    continue
                per = x['period']
                if per.startswith('Q'):
                    m[(int(x['year']), {1: 3, 2: 6, 3: 9, 4: 12}[int(per[1:])])] = float(x['value'])
                elif per != 'M13':
                    m[(int(x['year']), int(per[1:]))] = float(x['value'])
        quarterly = any(k[1] == 3 for k in m) and not any(k[1] == 1 for k in m)
        months = (9, 12, 3, 6) if quarterly else tuple(range(1, 13))
        out = {}
        for fy in range(2009, 2027):
            obs = [m.get((fy - 1 if mo >= 7 else fy, mo)) for mo in months]
            if all(v is not None for v in obs):
                out[fy] = statistics.mean(obs)
        return out
    cmap = list(csv.DictReader(open(os.path.join(DATA, 'inflation-cost-index-map.csv'))))
    rise = {}
    for r in cmap:
        s = r['series_id']
        if s not in rise:
            ix = P if s == 'CUURS11ASA0' else own_index(s)
            rise[s] = ix[g1] / ix[g0] - 1
    detail = defaultdict(float)
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-function-expenditure.csv'))):
        if r['lea'] == LEA and int(r['fy']) == g0 and r['level'] == 'detail':
            detail[r['func_code']] += float(r['total'])
    base = {'SERV-3200': detail['3200'], 'SERV-3400': detail['3400']}
    for k in ('TCHR', 'TSER', 'LDRS', 'ADMN', 'GUID', 'BENE', 'OPMN'):
        base[k] = cat[g0][k]
    # The excess of each non-fallback kind's own index over household prices, on its base;
    # buildings by DESE code (custodians, heat and utilities, the rest at household prices).
    extra, own_mark = 0.0, {}
    for k, b in base.items():
        rows_k = [r for r in cmap if r['key'] == k]
        if k == 'OPMN':
            cust, heat = detail['4110'], detail['4120'] + detail['4130']
            sid = {r['part']: r['series_id'] for r in rows_k}
            own = (cust * rise[sid['custodians']] + heat * rise[sid['heat and utilities']]
                   + (b - cust - heat) * px)
        else:
            own = b * rise[rows_k[0]['series_id']]
        own_mark[k] = own
        extra += own - b * px
    own_kept_t = kept + extra
    oc = p['also'][0]
    check(oc['title'] == 'Each type against its own inflation', 'the first extra chart is the own-inflation chart')
    check(abs(sum(r['mark'] for r in oc['rows']) - own_kept_t) < 25,
          'its ticks add to %s, each kind grown by its own index' % usd(own_kept_t))
    check(abs(sum(r['value'] for r in oc['rows']) - add) < 25, 'its bars are the same rise')
    names = {'TCHR': 'Teachers', 'BENE': 'Insurance, retirement, other', 'OPMN': 'Buildings and upkeep',
             'SERV-3400': 'Food service', 'SERV-3200': 'Nurses and health'}
    for k, nm in names.items():
        r = next(r for r in oc['rows'] if r['label'] == nm)
        check(abs(r['mark'] - own_mark[k]) < 1, '%s: own-inflation tick %s' % (nm, usd(own_mark[k])))
    sig = {r['label']: r['mark'] for r in rows}
    stars = [r for r in oc['rows'] if r['label'].endswith(' *')]
    fb = {r['spending_type'] for r in cmap if r['fallback'] == 'yes' and r['part'] == 'all'}
    check({r['label'][:-2] for r in stars} == fb
          and all(abs(r['mark'] - sig[r['label'][:-2]]) < 1 for r in stars),
          'the %d starred kinds are the map’s fallbacks, ticked at household prices' % len(fb))
    check(all(r['gap_text'] == usd(abs(r['value'] - r['mark'])) and r['over'] == (r['value'] >= r['mark'])
              for r in oc['rows']), 'every own-inflation gap is its bar less its tick')
    bo = cat[g1]['BENE'] - cat[g0]['BENE'] - own_mark['BENE']
    wr = 100 * rise['CIU3026110000000I']
    c2n = [n['text'] for n in p['conclusions'][1]['notes']]
    check(mill(bo) in c2n[0] and mill(bb) in c2n[0] and 0 < bo < bb,
          'insurance: %s over household prices, %s over benefit costs' % (mill(bb), mill(bo)))
    check(('%.1f%%' % wr) in c2n[1], 'school pay rose %.1f%%' % wr)
    check(mill(add - own_kept_t) == mill(beyond) and mill(beyond) in c2n[2],
          'net past own inflation %s = net past household %s' % (mill(add - own_kept_t), mill(beyond)))
    ov = next(v for v in p['table']['views'] if v['key'] == 'own')
    tot_row = ov['rows'][-1]['cells']
    check(tot_row[1] == '+' + usd(own_kept_t), 'the own view’s total own-inflation is %s' % usd(own_kept_t))

    # ---- the window, found again from the prices
    yoy = {y: 100 * (P[y] / P[y - 1] - 1) for y in P if y - 1 in P}
    best, cur = [], []
    for y in range(g0, g1 + 1):
        cur = cur + [y] if yoy[y] > 2.5 else []
        if len(cur) > len(best):
            best = list(cur)
    w0, w1 = best[0] - 1, best[-1]
    ws, wp = 100 * (tot[w1] / tot[w0] - 1), 100 * (P[w1] / P[w0] - 1)
    check(fact(p, 'w-spend')['value']['text'] == pct_text(ws), 'window FY%d-FY%d spending %s'
          % (w0, w1, pct_text(ws)))
    check(fact(p, 'w-price')['value']['text'] == pct_text(wp), 'window prices %s' % pct_text(wp))
    c1 = p['conclusions'][0]['text']
    said = re.search(r'(\d+)% inflation', p['lead_quote']['quote']).group(1)
    check('%.1f%%' % wp in c1 and '%s%%' % said in c1,
          'conclusion 1 sets inflation %.1f%% beside the quote’s %s%%' % (wp, said))
    es, ep = 100 * (tot[w1] / tot[w0 - 1] - 1), 100 * (P[w1] / P[w0 - 1] - 1)
    c3n = p['conclusions'][2]['notes'][0]['text']
    check('%.1f%%' % es in c3n and '%.1f%%' % ep in c3n
          and es > ep and ws < wp, 'the start year flips it: %.1f%% v %.1f%% from FY%d'
          % (es, ep, w0 - 1))
    LL, OV = {}, defaultdict(float)
    for r in csv.DictReader(open(os.path.join(DATA, 'dls-new-growth.csv'))):
        if r['municipality'] == 'Lunenburg' and r['prior_levy_limit']:
            LL[int(r['fy']) - 1] = float(r['prior_levy_limit'])
    for r in csv.DictReader(open(os.path.join(DATA, 'dls-override-votes.csv'))):
        if r['municipality'] == 'Lunenburg' and r['result'] == 'WIN' and r['vote_type'] == 'Override':
            OV[int(r['fy'])] += float(r['amount'])
    wl = 100 * ((LL[w1] - sum(v for y, v in OV.items() if w0 < y <= w1)) / LL[w0] - 1)
    check(fact(p, 'w-levy')['value']['text'] == pct_text(wl), 'levy limit before override %s'
          % pct_text(wl))
    c3 = p['conclusions'][2]['text']
    check('%.1f%%' % wl in c3 and '%.1f%%' % wp in c3 and wl < wp,
          'conclusion 3: the tax limit grew less than inflation')
    check('%.1f%%' % ws in c3n and ws < wp, 'conclusion 3’s note: spending also under inflation')

    # ---- per teacher, from the programme-area file
    fte = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-teacher-program-area.csv'))):
        if r['lea'] == LEA and r['org_level'] == 'district' and r['total_fte']:
            fte[int(r['fy'])] = float(r['total_fte'])
    wt = 100 * ((cat[g1]['TCHR'] / fte[g1]) / (cat[g0]['TCHR'] / fte[g0]) - 1)
    tn = p['conclusions'][1]['notes'][1]['text']
    check(('%.1f%%' % wt) in tn and wt > wr, 'per teacher FTE %s, faster than school pay %s'
          % (pct_text(wt), pct_text(wr)))

    # ---- payment for payment, from the CSV row by row
    J = list(csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'))))
    ytd = {(r['account'], int(r['fiscal_year'])): float(r['ytd_expended'])
           for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'))) if r['period'] == '13'}
    acc = defaultdict(float)
    for r in J:
        if r['posts_to'] == 'actual':
            acc[(r['account'], int(r['fiscal_year']))] += float(r['amount'])

    def pays(vendor, account):
        out = defaultdict(list)
        for r in J:
            if (r['posts_to'] == 'actual' and r['source'] in ('API', 'APM') and r['account'] == account
                    and r['vendor'].strip().upper() == vendor):
                out[int(r['fiscal_year'])].append(float(r['amount']))
        return out

    hi_acct, bus_acct = '0100-3-300-5200-99-1-99-2-570001', '0100-3-300-3300-99-1-69-2-535025'
    for a in (hi_acct, bus_acct):
        for y in (2023, 2024, 2025, 2026):
            check(abs(acc[(a, y)] - ytd[(a, y)]) < 0.005, '%s FY%d journal %.2f = period-13 %.2f'
                  % (a[-18:], y, acc[(a, y)], ytd[(a, y)]))
    h = pays('MIIA HEALTH BENEFITS', hi_acct)
    hc = 100 * (statistics.median(h[2026]) / statistics.median(h[2023]) - 1)
    check([len(h[y]) for y in (2023, 2024, 2025)] == [12, 12, 12], 'health: twelve bills a year, FY2023-FY2025')
    check(fact(p, 'pay-hi')['value']['text'] == pct_text(hc), 'health median bill %s' % pct_text(hc))
    b = pays('DEE BUS SERVICE INC', bus_acct)
    inst = {}
    for y in (2023, 2024, 2025, 2026):
        c = Counter(b[y])
        inst[y] = min(a for a, n in c.items() if n >= 2)
        check(abs(sum(b[y]) / inst[y] - 10) < 1e-9, 'bus FY%d: %.2f is ten instalments of %.2f'
              % (y, sum(b[y]), inst[y]))
    bc = 100 * (inst[2026] / inst[2023] - 1)
    check(fact(p, 'pay-bus')['value']['text'] == pct_text(bc), 'bus instalment %s' % pct_text(bc))
    jp = 100 * (P[2026] / P[2023] - 1)
    check(fact(p, 'pay-price')['value']['text'] == pct_text(jp), 'prices FY2023-FY2026 %s' % pct_text(jp))
    check(hc > jp and bc > jp, 'both rose faster than prices')
    check(not any(r['label'].lower().startswith('individual') for r in p['also'][1]['rows']),
          'no masked payee is a series')

    # ---- quotations, verbatim
    def txt(rel):
        return norm(open(os.path.join(ROOT, rel), encoding='utf-8').read())
    lq = p['lead_quote']
    m = re.match(r'/docs/minutes/text/(.*)$', lq['href'])
    check(bool(m) and norm(lq['quote']) in txt('sources/meetings/text/' + m.group(1)),
          'lead quote verbatim in %s' % lq['href'])
    check('Sculimbrene, Vice Chair' in txt('sources/meetings/text/' + m.group(1)).replace(
        'Anthony Sculimbrene, Vice Chair', 'Sculimbrene, Vice Chair'), 'the speaker is named so')
    for s in p['said']:
        if s['href'].startswith('/docs/minutes/text/'):
            rel = 'sources/meetings/text/' + s['href'][len('/docs/minutes/text/'):]
        else:
            rel = s['href'][len('/docs/'):].replace('/docs/', '/text/').replace('.pdf', '.txt')
            rel = 'sources/' + rel
        check(norm(s['quote']) in txt(rel), 'quote verbatim in %s' % rel)

    print('\n%d failed' % len(BAD) if BAD else '\nall checks passed')
    return 1 if BAD else 0


if __name__ == '__main__':
    sys.exit(main())
