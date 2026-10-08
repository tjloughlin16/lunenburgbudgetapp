#!/usr/bin/env python3
"""Verify every figure in a school surplus report, recomputed by a DIFFERENT route than
the generator: `decimal.Decimal` arithmetic straight off the CSV, rather than the
generator's own `float` accumulation and helper functions -- and, for FY2026's period-12
comparison, the analysis DATABASE (`lunenburg.db`, the route verify_fy26_closeout.py uses)
rather than the CSV the generator reads. Rule 9 and `notes/process/WRITING-AN-ANALYSIS.md`
§5: assert the number, never the prose around it.

    python3 scripts/verify_school_surplus.py --fy 2025
    python3 scripts/verify_school_surplus.py --fy 2026
    python3 scripts/verify_school_surplus.py --all

The expected values below are written down on purpose. A verifier that only compared the
generator to itself would pass on any input; these are the figures the ledger held when the
report was written, so a re-extraction that moves one fails here and somebody looks.

`verify_fy25_school_surplus.py` and `verify_fy26_school_surplus.py` are thin wrappers, so
`build_reports_index.py` finds each report's verifier by its name.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
LEDGER = os.path.join(DATA, 'munis-school-ytd.csv')
REVDIST = os.path.join(DATA, 'revenue-distribution-fy26.csv')
DB = os.path.join(DATA, 'lunenburg.db')
SC_TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text', 'school-committee')
ANALYSES = os.path.join(ROOT, 'sources', 'analyses')
PAYLOADS = os.path.join(ROOT, 'fy28', 'public', 'data')
YEARS = (2025, 2026)
D = Decimal


class Run:
    def __init__(self, fy):
        self.fy = fy
        self.slug = 'fy%02d-school-surplus' % (fy % 100)
        self.fails = []
        self.md = open(os.path.join(ANALYSES, self.slug + '.md'), encoding='utf-8').read()
        self.pay = json.load(open(os.path.join(PAYLOADS, self.slug + '.json'),
                                  encoding='utf-8'))

    def check(self, cond, msg):
        if not cond:
            self.fails.append(msg)

    def need(self, text, label):
        self.check(text in self.md, '%s (%s) not found verbatim in the markdown'
                   % (label, text))


# ---- shared, by the Decimal route ---------------------------------------------------

def rows_for(fy):
    out = []
    with open(LEDGER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['fiscal_year'] == str(fy) and r['period'] == '13' \
                    and r['report'] == 'gf-school' and r['type'] == 'E':
                out.append(r)
    return out


def sums(rows):
    return dict(
        original=sum(D(r['original_approp']) for r in rows),
        transfers=sum(D(r['transfers_adjustments']) for r in rows),
        revised=sum(D(r['revised_budget']) for r in rows),
        expended=sum(D(r['ytd_expended']) for r in rows),
        encumbered=sum(D(r['encumbrances']) for r in rows),
        available=sum(D(r['available_budget']) for r in rows),
    )


def families(rows):
    """{family: [salary unspent, non-salary unspent, encumbered]}, grouped independently
    of the generator's family_of()."""
    fam = {}
    for r in rows:
        family = (int(r['account'].split('-')[3]) // 1000) * 1000
        acc = fam.setdefault(family, [D('0'), D('0'), D('0')])
        v = D(r['available_budget'])
        if r['obj'].startswith('51'):
            acc[0] += v
        else:
            acc[1] += v
        acc[2] += D(r['encumbrances'])
    return fam


def para(rows):
    out = {}
    for r in rows:
        if r['account'].split('-')[3] != '2330':
            continue
        out[r['account']] = dict(
            org=r['org'], original=D(r['original_approp']),
            transfers=D(r['transfers_adjustments']), revised=D(r['revised_budget']),
            expended=D(r['ytd_expended']), available=D(r['available_budget']))
    return out


def check_identities(run, s):
    run.check(s['original'] + s['transfers'] == s['revised'],
              'revised budget does not equal original + transfers: %s != %s'
              % (s['original'] + s['transfers'], s['revised']))
    run.check(s['revised'] - s['expended'] - s['encumbered'] == s['available'],
              'available does not equal revised - expended - encumbered')


def check_expected(run, s, expect):
    for k, v in expect.items():
        run.check(s[k] == v, '%s recomputed as %s, expected %s' % (k, s[k], v))


def check_payload_totals(run, s):
    pt = run.pay['totals']
    for k in ('original', 'transfers', 'revised', 'expended', 'encumbered', 'available'):
        run.check(D(str(pt[k])) == s[k], 'payload totals.%s %s does not match %s'
                  % (k, pt[k], s[k]))


def check_payload_families(run, expect_family, with_enc):
    by_func = {r['family']: r for r in run.pay['by_function']}
    for family, want in expect_family.items():
        r = by_func.get(family)
        run.check(r is not None, 'payload by_function is missing family %d' % family)
        if not r:
            continue
        run.check(D(str(r['salary'])) == want[0], 'payload family %d salary mismatch' % family)
        run.check(D(str(r['non_salary'])) == want[1],
                  'payload family %d non-salary mismatch' % family)
        if with_enc:
            run.check(D(str(r['encumbered'])) == want[2],
                      'payload family %d encumbered mismatch' % family)


def check_conclusions(run, want_figures):
    for c in run.pay['conclusions']:
        prose = ' '.join([c['claim'], c.get('so_what', ''), c['detail']])
        for name, f in c['figures'].items():
            key = '%s/%s' % (c['id'], name)
            want = want_figures.get(key, want_figures.get(name))
            if want is not None:
                got = D(str(f['value']))
                ok = got == want if not isinstance(want, tuple) else \
                    abs(got - want[0]) <= want[1]
                run.check(ok, 'conclusion %s figure %s = %s, recomputed as %s'
                          % (c['id'], name, got, want))
            run.check(f['text'] in prose, 'conclusion %s: figure %s renders as %r but that '
                      'string is not in its own prose' % (c['id'], name, f['text']))


def flat(text):
    return ' '.join(text.split())


# ---- why there was money left over: the category section, by the Decimal route ------
#
# The categories are recomputed here from their written RULES, as ranges -- not by
# importing the generator's table -- so a change to one that is not made to the other
# fails. Same order as the generator's table: first match wins.

SALARY_KEYS = ('teachers', 'counselors', 'paras', 'admin', 'custodians', 'other_staff')
DISCRETIONARY = ('buildings', 'equipment', 'supplies')


def cat_of(func, sal):
    if sal:
        if func == 2330:
            return 'paras'
        if 2300 <= func <= 2399:
            return 'teachers'
        if 2700 <= func <= 2899:
            return 'counselors'
        if 1000 <= func <= 2299:
            return 'admin'
        if 4000 <= func <= 4999:
            return 'custodians'
        return 'other_staff'
    if func >= 9000:
        return 'tuition'
    if func in (2310, 2320):
        return 'sped_services'
    if func == 3300:
        return 'transport'
    if func in (4120, 4130):
        return 'utilities'
    if 5000 <= func <= 5999:
        return 'benefits'
    if 4000 <= func <= 4999:
        return 'buildings'
    if 7000 <= func <= 7999 or func == 2451:
        return 'equipment'
    return 'supplies'


def categories(rows):
    out = {}
    for r in rows:
        k = cat_of(int(r['account'].split('-')[3]), r['obj'].startswith('51'))
        c = out.setdefault(k, dict(revised=D('0'), expended=D('0'), encumbered=D('0'),
                                   unspent=D('0'), under=D('0'), over=D('0'),
                                   original=D('0'), transfers=D('0')))
        a = D(r['available_budget'])
        c['revised'] += D(r['revised_budget'])
        c['expended'] += D(r['ytd_expended'])
        c['encumbered'] += D(r['encumbrances'])
        c['original'] += D(r['original_approp'])
        c['transfers'] += D(r['transfers_adjustments'])
        c['unspent'] += a
        if a > 0:
            c['under'] += a
        else:
            c['over'] += a
    return out


def money(v):
    n = int(D(v).quantize(D('1'), rounding='ROUND_HALF_EVEN'))
    return ('-$%s' if n < 0 else '$%s') % format(abs(n), ',d')


def verify_causes(run, rows, s, expect):
    """Every figure in the 'why' section and the thrift test, recomputed. `expect` holds
    the values written down when the section was built: total discretionary, the three
    largest categories, and the years-under counts."""
    cats = categories(rows)
    pc = {c['key']: c for c in run.pay['causes']['categories']}
    run.check(set(pc) == set(cats), 'payload categories %s, recomputed %s'
              % (sorted(pc), sorted(cats)))
    for k, c in cats.items():
        p = pc.get(k)
        if not p:
            continue
        for f in ('revised', 'expended', 'encumbered', 'unspent', 'under', 'over',
                  'original', 'transfers'):
            run.check(D(str(p[f])) == c[f], 'category %s %s: payload %s, recomputed %s'
                      % (k, f, p[f], c[f]))
        want_kind = 'discretionary' if k in DISCRETIONARY else 'circumstantial'
        run.check(p['kind'] == want_kind, 'category %s is %s, expected %s'
                  % (k, p['kind'], want_kind))
    run.check(sum(c['unspent'] for c in cats.values()) == s['available'],
              'the categories do not sum to the unspent total')
    disc = sum(cats[k]['unspent'] for k in DISCRETIONARY if k in cats)
    circ = s['available'] - disc
    run.check(disc == expect['disc'], 'discretionary recomputed as %s, expected %s'
              % (disc, expect['disc']))
    pd = run.pay['causes']['discretionary']
    run.check(D(str(pd['unspent'])) == disc, 'payload discretionary.unspent mismatch')
    share = disc / s['available'] * 100
    run.check(abs(D(str(pd['share_pct'])) - share) < D('0.01'), 'payload share mismatch')
    sal_net = sum(cats[k]['unspent'] for k in SALARY_KEYS if k in cats)
    run.check(D(str(run.pay['causes']['salary_net'])) == sal_net, 'salary_net mismatch')
    order = sorted(cats, key=lambda k: -cats[k]['unspent'])
    run.check(order[:3] == expect['top3'], 'the three largest categories are %s, expected %s'
              % (order[:3], expect['top3']))
    top3 = sum(cats[k]['unspent'] for k in order[:3])
    under = sum(c['under'] for c in cats.values())
    over = sum(c['over'] for c in cats.values())
    overs = sorted((k for k in cats if cats[k]['unspent'] < 0), key=lambda k: cats[k]['unspent'])

    # Does it repeat: every closed year, recomputed.
    hist = run.pay['causes']['history']
    years = hist['years']
    per_year = {y: categories(rows_for(y)) for y in years}
    rep_disc = 0
    for h in hist['rows']:
        got = [per_year[y].get(h['key'], {}).get('unspent', D('0')) for y in years]
        run.check([D(str(v)) for v in h['by_year']] == got,
                  'history %s: payload %s, recomputed %s' % (h['key'], h['by_year'], got))
        n_under = sum(1 for v in got if v > D('0.5'))
        run.check(h['years_under'] == n_under, 'history %s years_under mismatch' % h['key'])
        if h['key'] in DISCRETIONARY and n_under == len(years):
            rep_disc += 1
    for k, n in expect['years_under'].items():
        got = [h for h in hist['rows'] if h['key'] == k][0]['years_under']
        run.check(got == n, 'years under for %s is %d, expected %d' % (k, got, n))

    # Other funds: the circuit breaker's tuition spending, straight off the CSV.
    cb = sum(D(r['ytd_expended']) for r in csv.DictReader(open(LEDGER, encoding='utf-8'))
             if r['fiscal_year'] == str(run.fy) and r['report'] == 'special-school'
             and r['type'] == 'E' and r['fund'] == '2640'
             and int(r['account'].split('-')[3]) >= 9000)
    sf = [x for x in run.pay['causes']['special_funds']
          if x['fund'] == '2640' and x['category'] == 'tuition']
    run.check(len(sf) == 1 and D(str(sf[0]['expended'])) == cb,
              'circuit-breaker tuition spending: payload %s, recomputed %s' % (sf, cb))
    run.check(cb == expect['circuit_breaker'], 'circuit breaker tuition recomputed as %s'
              % cb)

    # Largest single account, recomputed.
    top = max(rows, key=lambda r: D(r['available_budget']))
    run.check(run.pay['causes']['top_unspent'][0]['account'] == top['account'],
              'largest unspent account mismatch')

    # Every quote on record still verbatim in the text the payload says it came from.
    for e in run.pay['causes']['record']:
        path = os.path.join(ROOT, e['text'])
        if e['kind'] == 'caption':
            d = json.load(open(path, encoding='utf-8'))
            txt = ' '.join(' '.join(x['text'].split()) for x in d['segments'])
            run.check(e['quote'] in txt, 'caption quote not in %s: %r' % (e['text'], e['quote']))
        else:
            run.check(e['quote'] in flat(open(path, encoding='utf-8').read()),
                      'quote not verbatim in %s: %r' % (e['text'], e['quote']))
        run.need(e['quote'], 'a quote on record')

    for text, label in ((money(disc), 'discretionary total'), (money(circ), 'the rest'),
                        (money(under), 'under-budget accounts'),
                        (money(-over), 'over-budget accounts')):
        run.need(text, label)
    for k in order[:3]:
        run.need(money(cats[k]['unspent']), 'category %s' % k)

    wants = {'c_three': top3, 'c_under': under, 'c_total': s['available'],
             'c_disc': disc, 'c_circ': circ, 'c_disc_share': (share, D('0.000001')),
             'c_years': D(len(years)), 'c_rep': D(rep_disc),
             'c_ndisc': D(len(DISCRETIONARY)),
             's_net': sal_net}
    for i, k in enumerate(order[:3]):
        wants['c_top%d' % i] = cats[k]['unspent']
    if overs:
        wants['c_over'] = -cats[overs[0]]['unspent']
        wants['c_over_tot'] = -over
        wants['s_paras'] = -cats['paras']['unspent']
    else:
        wants['c_lead_pct'] = (cats[order[0]]['unspent'] / cats[order[0]]['revised'] * 100,
                               D('0.05'))
    if 'counselors' in cats:
        wants['s_couns'] = cats['counselors']['unspent']
        wants['s_teach'] = cats['teachers']['unspent']
    return wants


# ---- FY2025 -------------------------------------------------------------------------

def verify_2025(run):
    DISTRICT_FIGURE = D('603885.97')
    MINUTES_TXT = os.path.join(SC_TEXT, '2025-09-17-minutes-7408.txt')
    rows = rows_for(2025)
    run.check(len(rows) == 415, 'expected 415 FY2025 period-13 gf-school expense rows, got %d'
              % len(rows))
    s = sums(rows)
    check_expected(run, s, dict(original=D('25304074.00'), transfers=D('-122502.44'),
                                revised=D('25181571.56'), expended=D('24554454.70'),
                                encumbered=D('0.00'), available=D('627116.86')))
    check_identities(run, s)

    diff = s['available'] - DISTRICT_FIGURE
    run.check(diff == D('23230.89'), 'diff vs district recomputed as %s, expected 23230.89'
              % diff)
    moved_out = -s['transfers']
    run.check(moved_out == D('122502.44'), 'moved out recomputed as %s' % moved_out)
    not_spent = s['available'] + moved_out
    run.check(not_spent == D('749619.30'), 'not spent against original recomputed as %s'
              % not_spent)

    want = None
    with open(REVDIST, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['line'] == 'ALL NEW FY26 REVENUES distributed by FY25 share / School Dept %':
                want = D(r['fy25'])
    run.check(want is not None, 'revenue-distribution-fy26.csv has no School Dept FY25 row')
    run.check(want == s['original'], 'scope check failed: revenue-distribution-fy26.csv says '
              '%s, the ledger says %s' % (want, s['original']))

    run.check(os.path.exists(MINUTES_TXT), 'missing %s' % os.path.relpath(MINUTES_TXT, ROOT))
    minutes = open(MINUTES_TXT, encoding='utf-8').read()
    run.check('$603,885.97' in minutes, 'the minutes no longer quote $603,885.97')
    run.check('the surplus number has gone up to $603,885.97' in flat(minutes),
              'the exact sentence around the district’s figure has changed')

    fam = families(rows)
    EXPECT_FAMILY = {
        2000: (D('136171.16'), D('112326.42')),
        4000: (D('113828.89'), D('113745.59')),
        7000: (D('0'), D('64747.51')),
        3000: (D('5192.12'), D('24915.45')),
        9000: (D('0'), D('29945.74')),
        1000: (D('8850.07'), D('11764.71')),
        5000: (D('0'), D('5629.20')),
    }
    for family, (esal, enon) in EXPECT_FAMILY.items():
        sal, non, _ = fam.get(family, (D('0'), D('0'), D('0')))
        run.check(sal == esal, 'family %d salary recomputed as %s, expected %s'
                  % (family, sal, esal))
        run.check(non == enon, 'family %d non-salary recomputed as %s, expected %s'
                  % (family, non, enon))
    total_fam = sum((a + b) for a, b, _ in fam.values())
    run.check(total_fam == s['available'], 'the function families do not sum to the '
              'available total: %s != %s' % (total_fam, s['available']))
    concentration = sum(fam[2000][:2]) + sum(fam[4000][:2])
    run.check(concentration == D('476072.06'), 'instruction + operations concentration '
              'recomputed as %s' % concentration)

    pa = {v['org']: v for v in para(rows).values()}
    EXPECT_PARA = {
        'S2512131': dict(available=D('48824.80')),
        'S2516131': dict(available=D('21767.92')),
        'S2515131': dict(available=D('5873.68'), transfers=D('53674.00')),
        'S2514131': dict(available=D('3154.40'), transfers=D('-65000.00')),
        'S2066131': dict(available=D('30174.26'), expended=D('4785.74'),
                         revised=D('34960.00')),
    }
    for org, want in EXPECT_PARA.items():
        got = pa.get(org)
        run.check(got is not None, 'no function-2330 account %s in the recomputation' % org)
        if got:
            for k, v in want.items():
                run.check(got[k] == v, 'para account %s %s recomputed as %s, expected %s'
                          % (org, k, got[k], v))

    for text, label in (('$627,117', 'the available total'), ('$23,231', 'the diff'),
                        ('$122,502', 'the moved-out total'),
                        ('$749,619', 'the not-spent-against-original total'),
                        ('$603,885.97', 'the district’s exact figure'),
                        ('$136,171', 'instruction salary'), ('$113,829', 'operations salary'),
                        ('$48,825', 'primary SPED para available')):
        run.need(text, label)

    check_payload_totals(run, s)
    run.check(D(str(run.pay['diff'])) == diff, 'payload diff does not match')
    run.check(D(str(run.pay['moved_out'])) == moved_out, 'payload moved_out does not match')
    run.check(D(str(run.pay['not_spent_against_original'])) == not_spent,
              'payload not_spent_against_original does not match')
    run.check(D(str(run.pay['district_figure'])) == DISTRICT_FIGURE,
              'payload district_figure does not match the quoted $603,885.97')
    check_payload_families(run, {k: (a, b, None) for k, (a, b) in EXPECT_FAMILY.items()},
                           with_enc=False)
    pa_by_org = {r['org']: r for r in run.pay['para_accounts']}
    for org, want in EXPECT_PARA.items():
        r = pa_by_org.get(org)
        run.check(r is not None, 'payload para_accounts is missing %s' % org)
        if r:
            for k, v in want.items():
                run.check(D(str(r[k])) == v, 'payload para %s %s mismatch' % (org, k))

    wants = verify_causes(run, rows, s, dict(
        disc=D('240114.95'), top3=['supplies', 'paras', 'custodians'],
        circuit_breaker=D('473650.35'),
        years_under={'buildings': 4, 'supplies': 4, 'custodians': 4, 'equipment': 1}))
    check_conclusions(run, dict(wants, **{
        'diff': diff, 'ledger': s['available'], 'district': DISTRICT_FIGURE,
        'total': not_spent, 'orig': s['original'], 'turned_back': s['available'],
        'moved': moved_out, 'ops': sum(fam[4000][:2]), 'sal': fam[4000][0],
        'non': fam[4000][1],
    }))
    return '415 accounts, %d function families, %d para accounts, %d conclusions' % (
        len(fam), len(para(rows)), len(run.pay['conclusions']))


# ---- FY2026 -------------------------------------------------------------------------

FY26_QUOTES = (
    'expense accounts were approximately 100.2% expended',
    'expected final salary expenditures to be close to, but below, 100% of the budget',
    'the approximately $600,000 that had been returned',
    'estimated during the discussion to represent approximately 2.5% of the budget',
    'he was confident the remaining amount would be well below that figure',
)


def verify_2026(run):
    rows = rows_for(2026)
    run.check(len(rows) == 415, 'expected 415 FY2026 period-13 gf-school expense rows, got %d'
              % len(rows))
    s = sums(rows)
    check_expected(run, s, dict(original=D('26247474.00'), transfers=D('85090.24'),
                                revised=D('26332564.24'), expended=D('25613679.23'),
                                encumbered=D('236766.94'), available=D('482118.07')))
    check_identities(run, s)

    # ---- period 12, by the OTHER route: the analysis database ----------------------
    run.check(os.path.exists(DB), 'missing %s -- run build_db.py' % os.path.relpath(DB, ROOT))
    db = sqlite3.connect(DB)
    q = db.execute("""SELECT a.org, a.object, l.original, l.transfers, l.revised,
                             l.expended, l.encumbered, l.available
                      FROM ledger_snapshot l JOIN account a USING (account_id)
                      WHERE l.fy=2026 AND l.period=12 AND a.dept='300'""").fetchall()
    run.check(len(q) == 258, 'expected 258 period-12 department-300 accounts in the '
              'database, got %d' % len(q))
    p12 = {(o, ob): [D(str(round(x, 2))) for x in vals] for o, ob, *vals in q}
    p12_enc = sum(v[4] for v in p12.values())
    p12_avail = sum(v[5] for v in p12.values())
    p12_exp = sum(v[3] for v in p12.values())
    run.check(p12_avail == D('482101.12'), 'period-12 unspent recomputed as %s' % p12_avail)
    run.check(p12_enc == D('236783.89'), 'period-12 encumbered recomputed as %s' % p12_enc)
    floor = p12_avail
    ceiling12 = p12_avail + p12_enc
    ceiling13 = s['available'] + s['encumbered']
    run.check(ceiling12 == D('718885.01'), 'period-12 ceiling recomputed as %s' % ceiling12)
    run.check(ceiling13 == ceiling12, 'the ceiling moved between periods: %s -> %s'
              % (ceiling12, ceiling13))
    moved = s['available'] - floor
    run.check(moved == D('16.95'), 'the move since period 12 recomputed as %s' % moved)
    run.check(s['expended'] == p12_exp, 'spending moved between periods: %s -> %s'
              % (p12_exp, s['expended']))

    # Account by account: exactly one account differs, and it is the one the report names.
    p13 = {(r['org'], r['obj']): [D(r[k]) for k in (
        'original_approp', 'transfers_adjustments', 'revised_budget', 'ytd_expended',
        'encumbrances', 'available_budget')] for r in rows}
    missing = [k for k in p12 if k not in p13]
    run.check(not missing, 'period-12 accounts absent at period 13: %s' % missing[:5])
    diffs = [k for k in p12 if k in p13 and p12[k] != p13[k]]
    extra = [k for k in p13 if k not in p12 and any(p13[k])]
    run.check(diffs == [('S2510042', '545001')] and not extra,
              'accounts that changed between periods: %s, new non-zero: %s' % (diffs, extra))

    # The closeout's stated range is the one recomputed here -- if fy26-closeout.md ever
    # restates it, this report's comparison is against a range that no longer exists.
    closeout = flat(open(os.path.join(ANALYSES, 'fy26-closeout.md'), encoding='utf-8')
                    .read()).replace('**', '')
    run.check('between $482,101 and $718,885' in closeout,
              'fy26-closeout.md no longer states the range "between $482,101 and $718,885"')

    # ---- what is still open --------------------------------------------------------
    opens = sorted(((D(r['encumbrances']), r['org'], r['obj']) for r in rows
                    if D(r['encumbrances']) != 0), reverse=True)
    run.check(len(opens) == 27, 'expected 27 accounts still encumbered, got %d' % len(opens))
    run.check(opens[0][1:] == ('S3991742', '521011') and opens[0][0] == D('62362.13'),
              'the largest open encumbrance is %s' % (opens[0],))
    run.check(opens[1][1:] == ('S5511062', '535023') and opens[1][0] == D('58708.07'),
              'the second open encumbrance is %s' % (opens[1],))
    top3 = sum(o[0] for o in opens[:3])
    run.check(top3 == D('144593.70'), 'the three largest open encumbrances sum to %s' % top3)
    fy25_enc = sums(rows_for(2025))['encumbered']
    run.check(fy25_enc == 0, 'FY2025 period 13 now carries %s encumbered' % fy25_enc)

    # ---- by function ---------------------------------------------------------------
    fam = families(rows)
    EXPECT_FAMILY = {
        4000: (D('11352.16'), D('174141.77'), D('106098.37')),
        2000: (D('158075.19'), D('-45797.35'), D('10064.55')),
        5000: (D('0'), D('107003.35'), D('0')),
        9000: (D('0'), D('88521.62'), D('58708.07')),
        1000: (D('-2915.50'), D('24019.66'), D('20303.81')),
        3000: (D('25699.53'), D('-41549.00'), D('36788.78')),
        7000: (D('0'), D('-16433.36'), D('4803.36')),
    }
    for family, want in EXPECT_FAMILY.items():
        got = fam.get(family, [D('0')] * 3)
        for i, name in enumerate(('salary', 'non-salary', 'encumbered')):
            run.check(got[i] == want[i], 'family %d %s recomputed as %s, expected %s'
                      % (family, name, got[i], want[i]))
    run.check(sum(a + b for a, b, _ in fam.values()) == s['available'],
              'the function families do not sum to the available total')
    run.check(sum(c for _, _, c in fam.values()) == s['encumbered'],
              'the function families do not sum to the encumbered total')

    # ---- salary / non-salary ------------------------------------------------------
    def split(sal):
        rr = [r for r in rows if r['obj'].startswith('51') == sal]
        rv = sum(D(r['revised_budget']) for r in rr)
        ex = sum(D(r['ytd_expended']) for r in rr)
        en = sum(D(r['encumbrances']) for r in rr)
        return ex / rv * 100, (ex + en) / rv * 100
    sal_spent, _ = split(True)
    non_spent, non_committed = split(False)
    for got, want, label in ((sal_spent, '98.9%', 'salary spent'),
                             (non_spent, '94.3%', 'non-salary spent'),
                             (non_committed, '96.9%', 'non-salary spent or encumbered')):
        run.check('%.1f%%' % got == want, '%s recomputed as %.3f, the report says %s'
                  % (label, got, want))
        run.need(want, label)
    floor_share = s['available'] / s['revised'] * 100
    ceiling_share = ceiling13 / s['revised'] * 100
    run.need('%.1f%% to %.1f%% of the revised budget' % (floor_share, ceiling_share),
             'the floor and ceiling as shares of the revised budget')

    # ---- the paraprofessional accounts --------------------------------------------
    pa = para(rows)
    sped = [v for v in pa.values() if v['org'] in ('S2512131', 'S2514131', 'S2515131',
                                                    'S2516131')]
    run.check(len(sped) == 4 and all(v['available'] < 0 for v in sped),
              'not every SPED paraprofessional line is over')
    sped_net = sum(v['available'] for v in sped)
    run.check(sped_net == D('-105644.46'), 'SPED para net recomputed as %s' % sped_net)
    run.check(sum(1 for v in sped if v['transfers'] > 0) == 3,
              'transfers into SPED para lines are no longer three')
    kinder = sum(v['expended'] for v in pa.values() if v['org'] in ('S2032121', 'S2032131'))
    run.check(kinder == D('99064.15'), 'kindergarten para spending recomputed as %s' % kinder)

    # ---- the meeting record, verbatim ---------------------------------------------
    minutes = flat(open(os.path.join(SC_TEXT, '2026-07-29-minutes-7930.txt'),
                        encoding='utf-8').read())
    for qt in FY26_QUOTES:
        run.check(qt in minutes, 'not verbatim in the 29 July 2026 minutes: %r' % qt)
        run.need(qt, 'a quote from the 29 July 2026 minutes')
    for name in ('2026-09-02-agenda-7990.txt', '2026-09-09-agenda-8002.txt'):
        text = open(os.path.join(SC_TEXT, name), encoding='utf-8').read()
        run.check('FY26 Year End Budget review' in text,
                  '%s no longer carries the year-end budget review item' % name)
    held_minutes = [n for n in os.listdir(SC_TEXT)
                    if n.startswith(('2026-09-02-minutes', '2026-09-09-minutes'))]
    if held_minutes:
        run.check('lists no minutes for either meeting' not in run.md,
                  'minutes are now held (%s) and the report still says none are'
                  % held_minutes)

    # ---- the markdown and the payload against the same figures --------------------
    for text, label in (('$482,118', 'period-13 unspent'), ('$236,767', 'still encumbered'),
                        ('$718,885', 'the ceiling'), ('$482,101', 'the period-12 floor'),
                        ('$16.95', 'the move since period 12'), ('$144,594', 'top three open'),
                        ('$185,494', 'O&M unspent'), ('$106,098', 'O&M encumbered'),
                        ('$105,644', 'SPED para net over'), ('$99,064', 'kindergarten para'),
                        ('$62,362.13', 'electricity encumbered'),
                        ('1 of 258 accounts changed', 'the account count')):
        run.need(text, label)
    check_payload_totals(run, s)
    rg = run.pay['range']
    for k, v in (('floor_p12', floor), ('ceiling_p12', ceiling12), ('p13', s['available']),
                 ('ceiling_p13', ceiling13)):
        run.check(D(str(rg[k])) == v, 'payload range.%s %s does not match %s' % (k, rg[k], v))
    run.check(D(str(run.pay['moved_since_p12'])) == moved, 'payload moved_since_p12 mismatch')
    run.check(len(run.pay['open_encumbrances']) == len(opens),
              'payload open_encumbrances count mismatch')
    check_payload_families(run, EXPECT_FAMILY, with_enc=True)

    tol = (D('0.000001'),)
    wants = verify_causes(run, rows, s, dict(
        disc=D('283991.32'), top3=['buildings', 'counselors', 'teachers'],
        circuit_breaker=D('333494.89'),
        years_under={'buildings': 4, 'counselors': 4, 'teachers': 4, 'paras': 3}))
    check_conclusions(run, dict(wants, **{
        'p13': s['available'], 'moved': moved, 'accounts': D(len(rows)), 'floor': floor,
        'period-13-landed-at-the-bottom-of-the-june-range/ceiling': ceiling12,
        'still-committed-to-open-purchase-orders/ceiling': ceiling13,
        'what-the-school-committee-was-told-in-july/ceiling': ceiling13,
        'enc': s['encumbered'], 'n': D(len(opens)), 'top1': opens[0][0],
        'top2': opens[1][0], 'fy25': fy25_enc, 'stated': D('600000.0'),
        'share_stated': D('2.5'),
        'floor_share': (floor_share,) + tol, 'ceiling_share': (ceiling_share,) + tol,
        'ops': sum(fam[4000][:2]), 'ops_enc': fam[4000][2], 'next_u': sum(fam[2000][:2]),
        'next_o': fam[9000][2], 'sal': fam[4000][0], 'non': fam[4000][1],
    }))
    return ('415 accounts, 258 joined to period 12, 1 changed, 27 still encumbered, '
            '%d conclusions' % len(run.pay['conclusions']))


VERIFY = {2025: verify_2025, 2026: verify_2026}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--fy', type=int, choices=YEARS)
    g.add_argument('--all', action='store_true')
    a = ap.parse_args(argv)
    rc = 0
    for fy in (YEARS if a.all else (a.fy,)):
        run = Run(fy)
        summary = VERIFY[fy](run)
        name = 'verify_%s' % run.slug.replace('-', '_')
        if run.fails:
            sys.stderr.write('%s: %d failure(s)\n' % (name, len(run.fails)))
            for m in run.fails:
                sys.stderr.write('  - %s\n' % m)
            rc = 1
        else:
            print('%s: all figures recomputed and matched (%s)' % (name, summary))
    return rc


if __name__ == '__main__':
    sys.exit(main())
