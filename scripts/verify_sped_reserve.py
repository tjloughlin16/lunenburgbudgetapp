#!/usr/bin/env python3
"""Recompute every figure on /special-education/special-education-overruns (the special
education reserve page) by a DIFFERENT ROUTE, and prove the two account definitions tie.

    python3 scripts/verify_sped_reserve.py

The generator (build_special_education_topics.py) reads the need series from
special-education-costs.json, the every-fund figures from build_school_all_funds.model(), and
the receipts from circuit-breaker.json and special-education-costs.json. This reads none of
those payloads' figures. It goes to the raw inputs, sums with Decimal, and compares the NUMBER
on the page -- fact values and table cells -- with what it gets:

  the 17-year general fund ledger    munis_school_ytd in the DATABASE (period 13) plus the
                                     Finance Committee workbook (gl-history.csv), classified by
                                     verify_sped_costs.kind(): function codes written out
  the statistics                     Decimal mean and sample standard deviation (n - 1)
  every fund, FY2023-FY2026          the raw journal CSV, classified HERE by the journal's
                                     labels (journal.py's list), at the cent; the circuit
                                     breaker also from the year-end report (fund 2640)
  receipts and allocations           dese-circuit-breaker.csv, special-revenue-read.csv, the
                                     database's fund 2640 receipts, dese-entitlement-allocations.csv

THE TIE. For FY2023-FY2026 the page shows the general fund two ways: its first two tables use
the period-13 ledger's definition (segment 51, less two ELL accounts, plus the account named
special education transportation); its third uses the school journal's (accounts whose labels
say special education, psychologists outside the total). They are different rules on different
documents. This prints, line by line and year by year, how far apart they are in CENTS, and
fails if any is more than a dollar.
"""
import csv
import json
import os
import re
import sqlite3
import sys
from decimal import Decimal as D, ROUND_HALF_EVEN

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_sped_costs as VSC  # noqa: E402
import journal as J  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', 'special-education-overruns.json')
LINES = ('indist', 'ood', 'trans')
bad = []


def r0(x):
    return int(D(x).quantize(D('1'), rounding=ROUND_HALF_EVEN))


def usd(n):
    return ('-' if n < 0 else '') + '$' + format(abs(int(n)), ',')


def check(name, got, want):
    if got != want:
        bad.append('%s: recomputed %r, page says %r' % (name, got, want))


def money(s):
    return None if s is None else int(s.replace('$', '').replace(',', ''))


def sample_sd(xs):
    n = len(xs)
    m = sum(D(x) for x in xs) / n
    return (sum((D(x) - m) ** 2 for x in xs) / (n - 1)).sqrt(), m


def foot(parts):
    """Largest-remainder rounding, written here in Decimal: whole dollars that add to the
    rounded total. The page's rule (conclusions.footed); not imported, so a change there that
    broke the rule would be caught here."""
    parts = [D(x) for x in parts]
    total = r0(sum(parts))
    base = [int(x.to_integral_value(rounding='ROUND_FLOOR')) for x in parts]
    order = sorted(range(len(parts)), key=lambda i: -(parts[i] - base[i]))
    for i in order[:total - sum(base)]:
        base[i] += 1
    return base


def ledger_cents():
    """(fy, line) -> [vote, spent] in cents, the period-13 ledger in the database."""
    db = sqlite3.connect(os.path.join(DATA, 'lunenburg.db'))
    out = {}
    for fy, acct, desc, typ, o, s, e in db.execute(
            "SELECT fiscal_year, account, description, type, original_approp, ytd_expended, "
            "encumbrances FROM munis_school_ytd WHERE period=13"):
        k = VSC.kind(acct, desc) if typ == 'E' else None
        if k:
            a = out.setdefault((int(fy), k), [D(0), D(0)])
            a[0] += D(str(o or 0))
            a[1] += D(str(s or 0)) + D(str(e or 0))
    return out


def journal_lines():
    """Special education postings by (fy, fund group, line, column), in cents, from the raw
    journal CSV. Which accounts are special education is journal.py's published list -- the
    definition under test -- but the summing, the fund grouping and the line mapping are here."""
    acc = {a['account']: a for a in csv.DictReader(open(J.ACCOUNTS_CSV, encoding='utf-8'))}
    line_of = {'535019': 'ood', '535022': 'ood', '535023': 'ood', '535026': 'trans'}
    out = {}
    for r in csv.DictReader(open(J.JOURNAL_CSV, encoding='utf-8')):
        a = acc[r['account']]
        # journal.py's definition -- the label list and the DESE items of
        # sources/data/sped-definition.csv -- decides which accounts are in the total.
        if not a['object'].startswith('5') or not J.in_sped_total(a):
            continue
        fund = ('gf' if r['fund'] == '0100' else 'cb' if r['fund'] == '2640'
                else 'grants' if re.search(r'#\s*(240|262|252|264|760|762|274|298|242)\b',
                                           a['fund_name']) else 'other:' + r['fund'])
        g = line_of.get(a['object'], 'indist')
        col = {'actual': 'spent', 'encumbrance': 'spent', 'original_budget': 'voted'}.get(r['posts_to'])
        if col:
            k = (int(r['fiscal_year']), fund, g, col)
            out[k] = out.get(k, D(0)) + D(r['amount'])
    return out


def main():
    p = json.load(open(PAY, encoding='utf-8'))
    fact = {f['id']: f['value']['value'] for f in p['facts'] if f['value']}
    tables = {t['caption']: t for t in [p['table']] + p['tables']}

    # ---- the 17-year ledger, recomputed
    led, munis_years = VSC.ledger()
    years = sorted(led)
    var = {y: {g: led[y][g][1] - led[y][g][0] for g in LINES} for y in years}
    need = {y: sum(max(0, v) for v in var[y].values()) for y in years}
    net = {y: sum(var[y].values()) for y in years}
    vals = [need[y] for y in years]
    n = len(vals)
    sd, mean = sample_sd(vals)
    avg, sdv = r0(mean), r0(sd)
    lv1, lv2 = avg + sdv, avg + 2 * sdv
    pairs = {years[i]: vals[i] + vals[i + 1] for i in range(n - 1)}
    two_fy = max(pairs, key=pairs.get)
    worst_fy = max(years, key=need.get)
    check('years', n, 17)
    check('average', avg, fact['mean'])
    check('sample SD', sdv, fact['sd'])
    check('average + 1 SD', lv1, fact['lvl1'])
    check('average + 2 SD', lv2, fact['lvl2'])
    check('worst year', need[worst_fy], fact['worst'])
    check('worst two running', pairs[two_fy], fact['two'])
    check('years needing', sum(1 for v in vals if v > 0), fact['needing'])
    check('years net over', sum(1 for y in years if net[y] > 0), fact['netover'])
    check('tuition years over', sum(1 for y in years if var[y]['ood'] > 0), fact['oodover'])
    cov = lambda lvl: sum(1 for v in vals if v <= lvl)
    want = ('Average plus two standard deviations, %s, would have met all %d years; plus one, %d.'
            % (usd(lv2), n, cov(lv1)))
    if cov(lv2) != n:
        bad.append('+2 SD no longer covers every year')
    check('conclusion 1', p['conclusions'][0]['text'], want)
    check('finding', p['finding']['text'],
          'Over %d years, special education needed %s a year beyond its vote on average; at most %s.'
          % (n, usd(avg), usd(need[worst_fy])))

    # table 1 and 2, cell by cell
    t1 = {r['label']: r['cells'] for r in tables['Voted and spent, general fund, each line, every year']['views'][0]['rows']}
    t2 = {r['label']: r['cells'] for r in tables['Over or under the vote, and the need it leaves']['views'][0]['rows']}
    # From the first MUNIS year the page rounds the three lines once from cents so they add to
    # the year's total; before it, the workbook's whole dollars. Recomputed that way here.
    lc = ledger_cents()
    fl = {}
    for y in years:
        if y in munis_years:
            v = foot([lc[(y, g)][0] for g in LINES])
            sp = foot([lc[(y, g)][1] for g in LINES])
            fl[y] = {g: (v[i], sp[i]) for i, g in enumerate(LINES)}
        else:
            fl[y] = {g: tuple(led[y][g]) for g in LINES}
    ov = {y: {g: fl[y][g][1] - fl[y][g][0] for g in LINES} for y in years}
    fnet = {y: sum(ov[y].values()) for y in years}
    for y in years:
        fy = 'FY%d' % y
        check('%s need, footed lines against the series' % fy,
              sum(max(0, x) for x in ov[y].values()), need[y])
        check('%s voted/spent' % fy, [fl[y][g][i] for g in LINES for i in (0, 1)],
              [money(c) for c in t1[fy][:6]])
        check('%s over/need' % fy, [ov[y]['indist'], ov[y]['ood'], ov[y]['trans'], need[y], fnet[y]],
              [money(c) for c in t2[fy]])
    lv = {r['label']: r['cells'] for r in tables['Reserve levels, and the years each would have met']['views'][0]['rows']}
    for lab, amt in (('Average', avg), ('Average + 1 SD', lv1), ('Average + 2 SD', lv2)):
        check('level %s' % lab, lv[lab], [usd(amt), '%d of %d' % (cov(amt), n), str(n - cov(amt)),
                                          '%d of %d' % (sum(1 for v in pairs.values() if v <= amt), n - 1)])

    # ---- THE TIE: two account definitions, FY2023-FY2026, in cents
    jl = journal_lines()
    db = sqlite3.connect(os.path.join(DATA, 'lunenburg.db'))
    ytd = {}
    for fy, acct, desc, typ, o, s, e in db.execute(
            "SELECT fiscal_year, account, description, type, original_approp, ytd_expended, "
            "encumbrances FROM munis_school_ytd WHERE period=13"):
        k = VSC.kind(acct, desc) if typ == 'E' else None
        if k:
            a = ytd.setdefault((int(fy), k), [D(0), D(0)])
            a[0] += D(str(o or 0))
            a[1] += D(str(s or 0)) + D(str(e or 0))
    print('THE TIE, general fund, journal labels minus period-13 segment 51 (cents):')
    for y in munis_years:
        row = []
        for g in LINES:
            dv = jl.get((y, 'gf', g, 'voted'), D(0)) - ytd[(y, g)][0]
            ds = jl.get((y, 'gf', g, 'spent'), D(0)) - ytd[(y, g)][1]
            row.append('%s voted %+.2f spent %+.2f' % (g, dv, ds))
            if abs(dv) > 1 or abs(ds) > 1:
                bad.append('FY%d %s: the two definitions part by %s / %s' % (y, g, dv, ds))
        print('  FY%d  %s' % (y, ';  '.join(row)))
    others = sorted({k[1] for k in jl if k[1].startswith('other:')})
    if others:
        bad.append('special education spending in funds this route does not group: %s' % others)

    # table 3, every fund: each year's totals against the journal, at the dollar
    t3 = tables['Every fund that paid, FY2023 to FY2026']
    cb_ytd = {}
    for fy, acct, typ, s, e in db.execute("SELECT fiscal_year, account, type, ytd_expended, "
                                          "encumbrances FROM munis_school_ytd WHERE period=13 AND fund='2640'"):
        if typ == 'E':
            cb_ytd[int(fy)] = cb_ytd.get(int(fy), D(0)) + D(str(s or 0)) + D(str(e or 0))
    for v in t3['views']:
        y = int(v['key'][2:])
        rows = {r['label']: [money(c) for c in r['cells']] for r in v['rows']}
        tot = rows['All three']
        sums = lambda fund, col: sum(jl.get((y, fund, g, col), D(0)) for g in LINES)
        want = [r0(sums('gf', 'voted')), r0(sums('gf', 'spent')), None, r0(sums('cb', 'spent')),
                r0(sums('grants', 'spent'))]
        for i in (0, 1, 3, 4):
            if abs(tot[i] - want[i]) > 1:
                bad.append('FY%d every fund col %d: %s against the journal %s' % (y, i, tot[i], want[i]))
        check('FY%d circuit breaker, year-end report' % y, tot[3], r0(cb_ytd[y]))
        for lab, r in rows.items():
            check('FY%d %s row foots' % (y, lab), r[5], r[1] + r[3] + r[4])
            check('FY%d %s over' % (y, lab), r[2], r[1] - r[0])
        for i in range(6):
            check('FY%d column %d foots' % (y, i), tot[i],
                  sum(rows[l][i] for l in rows if l != 'All three'))
        for lab, g in (('In-district', 'indist'), ('Out-of-district tuition', 'ood'),
                       ('Transportation', 'trans')):
            for i, col, fund in ((0, 'voted', 'gf'), (1, 'spent', 'gf'), (3, 'spent', 'cb'),
                                 (4, 'spent', 'grants')):
                if abs(rows[lab][i] - jl.get((y, fund, g, col), D(0))) > 1:
                    bad.append('FY%d %s col %d: %s against the journal %s'
                               % (y, lab, i, rows[lab][i], jl.get((y, fund, g, col), D(0))))
    wb = int(re.search(r'FY(\d{4})', next(f for f in p['facts'] if f['id'] == 'cbyr')['label']['text']).group(1))
    check('circuit breaker, the fact year', fact['cbyr'], r0(cb_ytd[wb]))
    # the upper bound: the account's tuition set back on the tuition line
    cbt = VSC.fund2640()
    check('need without the account', fact['upper'],
          max(0, led[wb]['ood'][1] + cbt[wb] - led[wb]['ood'][0])
          + max(0, var[wb]['indist']) + max(0, var[wb]['trans']))

    # ---- table 5: receipts and allocations
    t5 = {r['label']: [money(c) for c in r['cells']]
          for r in tables['Money that came in beside it, by year']['views'][0]['rows']}
    paid = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-circuit-breaker.csv'), encoding='utf-8')):
        if r['lea'] == '01620000':
            paid[int(r['fy'])] = r0(D(r['total_quarterly_payment'] or '0'))
    recd = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'special-revenue-read.csv'), encoding='utf-8')):
        if r['fund'] == '50/50 Grant Sped Tuitions':
            recd[int(r['fy'])] = r0(D(r['receipts'] or '0'))
    for fy, e in db.execute("SELECT fiscal_year, SUM(ytd_expended) FROM munis_school_ytd "
                            "WHERE period=13 AND fund='2640' AND type='R' GROUP BY fiscal_year"):
        if int(fy) not in recd:
            recd[int(fy)] = r0(-D(str(e)))
    idea = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['district_code'] == '0162' and r['fund_code'] == '0240':
            idea[int(r['fy'])] = int(r['amount'])
    for lab, cells in t5.items():
        y = int(lab[2:])
        check('%s received' % lab, [paid.get(y), recd.get(y), idea.get(y)], cells)

    # ---- THE BOARD MEMBER'S TABLE, every cell, FY2017-FY2026
    bmt = p['table']
    if bmt['views'][0]['columns'] != ['Special Education Operational Budget (general fund vote)',
                                      'IDEA Grant Funding (allocated)',
                                      'Circuit Breaker Funding (received)',
                                      'Actual Costs, general fund', 'Actual Costs, every fund',
                                      'General fund over (under) its vote', 'Needed beyond the vote']:
        bad.append('the board member\'s table is not first, or its columns moved')
    alloc = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['district_code'] == '0162' and r['fund_code'] in ('0240', '0262'):
            alloc[int(r['fy'])] = alloc.get(int(r['fy']), 0) + int(r['amount'])
    cball, statetr = {}, []
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-circuit-breaker.csv'), encoding='utf-8')):
        if r['lea'] == '01620000':
            cball[int(r['fy'])] = r0(sum(D(r[k] or '0') for k in (
                'total_quarterly_payment', 'extra_relief_payment', 'additional_supplemental_payment')))
        if r['level'] == 'state' and r['reimb_transport']:
            statetr.append(int(r['fy']))
    # the grant funds, by the names the annual reports print -- written out, not matched
    GRANT_FUNDS = {'PL 94-142 #240', 'Sped Early Childhood Grant', 'Early Childhood Grant #262',
                   'Sped Program Improvement Grant', 'Program Improvement Grant #274',
                   'FY21 Sped Program Improvement #298', 'FY22 ARP Idea #252', 'FY22 Idea ARP #264',
                   # FY2011-FY2016 names
                   'Sped Early Childhood', 'Early Childhood SPED ARRA', 'Idea Stimulus Program',
                   'PL 99-457', 'SPED Electronic Portfolio', 'Sped Curriculum Frameworks',
                   'Early Childhood Program Improvement', 'Early Childhood Sped Program Improvements'}
    disb = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'special-revenue-read.csv'), encoding='utf-8')):
        if r['fund'] in GRANT_FUNDS | {'50/50 Grant Sped Tuitions'} and r['row_ties'] == 'yes':
            disb[int(r['fy'])] = disb.get(int(r['fy']), D(0)) + D(r['disbursements'] or '0')
    change = min(statetr) - 1
    for r in bmt['views'][0]['rows']:
        y = int(r['label'][2:6])
        check('FY%d formula-change mark' % y, r['label'], 'FY%d' % y + ('*' if y == change else ''))
        cells = [None if c is None else money(c.split(' ')[0]) for c in r['cells']]
        if y in munis_years:
            gfv = r0(sum(jl.get((y, 'gf', g, 'voted'), D(0)) for g in LINES))
            gfs = r0(sum(jl.get((y, 'gf', g, 'spent'), D(0)) for g in LINES))
            allf = gfs + r0(sum(jl.get((y, 'cb', g, 'spent'), D(0)) for g in LINES)) \
                + r0(sum(jl.get((y, 'grants', g, 'spent'), D(0)) for g in LINES))
        else:
            gfv = sum(led[y][g][0] for g in LINES)
            gfs = sum(led[y][g][1] for g in LINES)
            allf = gfs + r0(disb[y]) if y in disb else None     # no schedule read: empty
        check('FY%d board member\'s row' % y, cells, [gfv, alloc.get(y), cball[y], gfs, allf,
                                                      gfs - gfv, need[y]])
        if allf is not None:
            check('FY%d every-fund marker' % y, r['cells'][4].endswith('§'), y not in munis_years)
    check('the table spans the need series',
          sorted(int(r['label'][2:6]) for r in bmt['views'][0]['rows']), years)
    check('the formula-change year', change, 2021)

    # ---- ONE QUANTITY, ONE FIGURE: anything printed in two tables prints identically
    ten = {int(r['label'][2:6]): [None if c is None else money(c.split(' ')[0]) for c in r['cells']]
           for r in bmt['views'][0]['rows']}
    t3v = {int(v['key'][2:]): {r['label']: [money(c) for c in r['cells']] for r in v['rows']}
           for v in t3['views']}
    LAB = {'indist': 'In-district', 'ood': 'Out-of-district tuition', 'trans': 'Transportation'}
    same = lambda what, *xs: len(set(xs)) == 1 or bad.append('%s prints differently: %s' % (what, xs))
    for y, row in ten.items():
        t1r = [money(c) for c in t1['FY%d' % y][:6]]
        t2r = [money(c) for c in t2['FY%d' % y]]
        same('FY%d vote' % y, row[0], sum(t1r[0::2]))
        same('FY%d general fund spent' % y, row[3], sum(t1r[1::2]))
        same('FY%d net' % y, row[5], t2r[4])
        same('FY%d need' % y, row[6], t2r[3])
        if y in t3v:
            a = t3v[y]['All three']
            same('FY%d vote, ten-year and every fund' % y, row[0], a[0])
            same('FY%d general fund spent, ten-year and every fund' % y, row[3], a[1])
            same('FY%d net, three tables' % y, row[5], a[2], t2r[4])
            same('FY%d every fund' % y, row[4], a[5])
            for i, g in enumerate(LINES):
                same('FY%d %s vote' % (y, g), t1r[2 * i], t3v[y][LAB[g]][0])
                same('FY%d %s spent' % (y, g), t1r[2 * i + 1], t3v[y][LAB[g]][1])
                same('FY%d %s over' % (y, g), t2r[i], t3v[y][LAB[g]][2])

    if bad:
        print('\n'.join(['FAIL'] + bad))
        return 1
    print('verify_sped_reserve: %d years, average %s, SD %s, +2 SD %s; six tables cell by cell, '
          'the every-fund table footed both ways, the two definitions tied' %
          (n, usd(avg), usd(sdv), usd(lv2)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
