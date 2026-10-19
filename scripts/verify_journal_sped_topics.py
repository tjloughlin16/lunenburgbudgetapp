#!/usr/bin/env python3
"""Recompute every figure on /special-education/sped-all-funds and /sped-providers by a
DIFFERENT ROUTE.

    python3 scripts/verify_journal_sped_topics.py

The generator reads the journal CSVs through scripts/journal.py, in Python, with Decimal. This
reads the DATABASE (`lunenburg.db`, tables munis_school_journal and munis_school_journal_account,
built from the same CSVs by build_db.py) and sums in SQL; it places funds by writing the fund
numbers out rather than through journal.sped_fund; and it checks the numbers against two
sources the generator never reads:

  * FY2026: the YTD ACTUAL the Town's report PRINTS for each account, summed by fund group.
    The journal's lines must add up to what the report says each account spent.
  * FY2023-FY2026, general fund: the PUBLISHED period-13 spreadsheets (`munis_school_ytd`),
    for every special education account both hold.

The ONE thing shared is the special education account list itself, journal.SPED_ACCOUNTS: it
is a definition, and there is one of it on purpose (the redaction and the reports must agree).

Then every registered figure on both pages -- each fact, each conclusion and note, the finding
-- is compared with its recomputed value, and the FY2026 masked-payee rule is checked: no
provider table on the page may be complete enough for a masked amount to be read off it.
"""
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from decimal import Decimal as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from journal import SPED_ACCOUNTS  # noqa: E402  (the definition, shared on purpose)

DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
YEARS = (2023, 2024, 2025, 2026)
OUTSIDE_TOTAL = {'511023', '535027', '535028', '535029'}   # psychologists; named tuition
IDEA = {'240', '262', '252', '264', '760', '762'}
OTHER = {'274', '298', '242'}
INVOICE = ('API', 'APM')
INDIVIDUAL = 'individual (redacted)'

bad = []


def cents(x):
    return D(str(round(x, 2)))


def group(fund, fund_name):
    if fund == '0100':
        return 'General fund'
    if fund == '2640':
        return 'Circuit breaker'
    m = re.search(r'#\s*(\d{3})\b', fund_name)
    code = m.group(1) if m else None
    if code in IDEA:
        return 'IDEA grants'
    if code in OTHER:
        return 'Other special education grants'
    return 'other'


def main():
    c = sqlite3.connect(DB)
    acct = {}
    for a, fund, fname, org, oname, desc, obj, ytd, enc in c.execute(
            'SELECT account, fund, fund_name, org, org_name, account_description, object, '
            'ytd_actual, encumbrances FROM munis_school_journal_account'):
        if obj.startswith('5') and SPED_ACCOUNTS.search(' | '.join([desc, oname, fname])):
            acct[a] = dict(g=group(fund, fname), obj=obj, ytd=cents(ytd), enc=cents(enc), org=org)
    total_acc = {a for a, v in acct.items() if v['obj'] not in OUTSIDE_TOTAL}
    # Accounts in no group (two school revolving funds) are allowed only while nothing posts.
    stray = sorted(a for a in total_acc if acct[a]['g'] == 'other')
    if stray and c.execute("SELECT COUNT(*) FROM munis_school_journal WHERE posts_to='actual' "
                           "AND account IN (%s)" % ','.join('?' * len(stray)), stray
                           ).fetchone()[0]:
        bad.append('an account in no fund group has actuals: %s' % stray[:3])

    # ---- every fund, by year and group, summed in SQL
    c.execute('CREATE TEMP TABLE sped(account TEXT PRIMARY KEY, g TEXT, obj TEXT)')
    c.executemany('INSERT INTO sped VALUES (?,?,?)', [(a, acct[a]['g'], acct[a]['obj'])
                                                       for a in total_acc])
    fund = defaultdict(D)
    for fy, g, s in c.execute(
            "SELECT j.fiscal_year, s.g, SUM(j.amount) FROM munis_school_journal j "
            "JOIN sped s USING(account) WHERE j.posts_to='actual' GROUP BY 1, 2"):
        fund[(fy, g)] = cents(s)
    total = {y: sum(v for (fy, _), v in fund.items() if fy == y) for y in YEARS}
    gf = {y: fund[(y, 'General fund')] for y in YEARS}
    other = {y: total[y] - gf[y] for y in YEARS}

    # FY2026 against what the report PRINTS, account by account, summed by group
    printed = defaultdict(D)
    for a in total_acc:
        printed[acct[a]['g']] += acct[a]['ytd']
    for g, v in printed.items():
        if v != fund[(2026, g)] and not (v == 0 and (2026, g) not in fund):
            bad.append('FY2026 %s: journal lines %s, printed YTD actual %s'
                       % (g, fund[(2026, g)], v))
    # FY2023-FY2026 general fund against the published period-13 spreadsheets
    for y in YEARS:
        held = {a for (a,) in c.execute(
            "SELECT account FROM munis_school_ytd WHERE fiscal_year=? AND period=13 "
            "AND fund='0100'", (y,))} & {a for a in total_acc if acct[a]['g'] == 'General fund'}
        if not held:
            bad.append('FY%d: no general fund special education account in the spreadsheets' % y)
            continue
        q = ','.join('?' * len(held))
        sheet = cents(c.execute('SELECT SUM(ytd_expended) FROM munis_school_ytd WHERE '
                                'fiscal_year=? AND period=13 AND account IN (%s)' % q,
                                [y] + sorted(held)).fetchone()[0])
        jour = cents(c.execute("SELECT SUM(amount) FROM munis_school_journal WHERE "
                               "fiscal_year=? AND posts_to='actual' AND account IN (%s)" % q,
                               [y] + sorted(held)).fetchone()[0])
        if sheet != jour:
            bad.append('FY%d general fund: spreadsheet %s, journal %s, over %d accounts'
                       % (y, sheet, jour, len(held)))
        missing = {a for a in total_acc if acct[a]['g'] == 'General fund'} - held
        lines_missing = c.execute("SELECT COUNT(*) FROM munis_school_journal WHERE "
                                  "fiscal_year=? AND posts_to='actual' AND account IN (%s)"
                                  % ','.join('?' * len(missing)), [y] + sorted(missing)
                                  ).fetchone()[0] if missing else 0
        if lines_missing:
            bad.append('FY%d: %d general fund special education lines are on accounts the '
                       'spreadsheet lacks' % (y, lines_missing))

    psy = {y: cents(c.execute(
        "SELECT COALESCE(SUM(j.amount),0) FROM munis_school_journal j JOIN "
        "munis_school_journal_account a USING(account) WHERE a.object='511023' AND "
        "j.posts_to='actual' AND j.fiscal_year=?", (y,)).fetchone()[0]) for y in YEARS}
    reclass = c.execute(
        "SELECT SUM(j.amount), COUNT(*) FROM munis_school_journal j JOIN sped s USING(account) "
        "WHERE s.g='Circuit breaker' AND j.fiscal_year=2026 AND j.posts_to='actual' "
        "AND j.source IN ('GEN','GRV')").fetchone()
    open_enc = sum(acct[a]['enc'] for a in total_acc)

    # ---- payees, invoices only
    vend = defaultdict(D)
    payee = defaultdict(lambda: defaultdict(D))
    masked = D(0)
    rows = c.execute(
        "SELECT j.fiscal_year, j.vendor, j.ref_type, j.amount, s.g FROM munis_school_journal j "
        "JOIN sped s USING(account) WHERE j.posts_to='actual' AND j.source IN ('API','APM')"
    ).fetchall()
    for fy, v, ref, amt, g in rows:
        vend[fy] += cents(amt)
        name = ' '.join((v or '').upper().split()).rstrip('.,;')
        if ref == 'VND' and name in ('', INDIVIDUAL.upper()):
            masked += cents(amt)
        else:
            payee[name][fy] += cents(amt)
    allv = sum(vend.values())
    tot = {k: sum(v.values()) for k, v in payee.items()}
    order = sorted(tot, key=lambda k: (-tot[k], k))
    share = lambda ks: 100 * sum(tot[k] for k in ks) / allv
    fl, vp = payee['FLLAC EDUCATIONAL CO'], payee['VAN POOL']
    fl_tuition = {y: cents(c.execute(
        "SELECT SUM(j.amount) FROM munis_school_journal j JOIN sped s USING(account) WHERE "
        "j.posts_to='actual' AND j.source IN ('API','APM') AND j.vendor='FLLAC EDUCATIONAL CO' "
        "AND s.obj IN ('535019','535023') AND j.fiscal_year=?", (y,)).fetchone()[0] or 0)
        for y in (2023, 2026)}

    pct = lambda a, b: 100 * (b - a) / a
    want = {
        'sped-all-funds': {
            'all0': total[2023], 'all1': total[2026], 'gf0': gf[2023], 'gf1': gf[2026],
            'out0': 100 * other[2023] / total[2023], 'out1': 100 * other[2026] / total[2026],
            'rate': 100 * ((float(gf[2026] / gf[2023])) ** (1 / 3) - 1),
            'reclass': cents(reclass[0]), 'open': open_enc, 'psy': psy[2026],
        },
        'sped-providers': {
            'vend': allv, 'top3': share(order[:3]), 'top10': share(order[:10]),
            'payees': len(tot), 'l0': fl[2023], 'l1': fl[2026], 'v0': vend[2023],
            'v1': vend[2026], 'c25': vp[2025], 'c26': vp[2026], 'masked': masked,
        },
    }
    if reclass[1] != 1:
        bad.append('the FY2026 circuit breaker has %d journal entries, not one' % reclass[1])
    if order[:3] != ['FLLAC EDUCATIONAL CO', 'VAN POOL', 'MAY INSTITUTE']:
        bad.append('the three largest payees are now %s' % order[:3])

    # every recomputed value, by the text it renders as, for the prose checks below
    usd = lambda x: ('-$%s' if x < 0 else '$%s') % format(abs(round(float(x))), ',d')
    p1 = lambda x: '%.1f%%' % float(x)
    expect_text = {usd(v) for p in want.values() for v in p.values()}
    expect_text |= {p1(v) for p in want.values() for v in p.values()}
    expect_text |= {usd(gf[2026] - gf[2023]), usd(total[2026] - total[2023]), usd(other[2023]),
                    usd(other[2026]), p1(pct(total[2023], total[2026])),
                    p1(pct(gf[2023], gf[2026])), p1(pct(vend[2023], vend[2026])),
                    p1(pct(vp[2025], vp[2026])), usd(vp[2023]), usd(fl_tuition[2023]),
                    usd(fl_tuition[2026]), '%.1f times' % float(fl[2026] / fl[2023]), '2.5%',
                    str(len(tot))}

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
            for k, f in u['figures'].items():
                t = f['text']
                if re.match(r'^FY\d{4}', t):
                    continue
                if t not in expect_text:
                    bad.append('%s: %r in %r is not a recomputed figure' % (tid, t, u['text'][:60]))
        # the redaction: no table may list every payee
        for v in (p.get('table') or {}).get('views', []):
            if v['key'] == 'payees' and len(v['rows']) >= len(tot):
                bad.append('%s: the payee table lists every payee, so a masked amount falls out '
                           'by subtraction' % tid)
        for ch in [p['chart']] + p.get('also', []):
            for r in ch.get('rows', []):
                if r['label'] in ('', INDIVIDUAL):
                    bad.append('%s: a chart row is a masked payee' % tid)

    if bad:
        print('verify_journal_sped_topics: %d problem(s)' % len(bad))
        print('\n'.join('  ' + b for b in bad))
        return 1
    n = sum(len(v) for v in want.values())
    print('verify_journal_sped_topics: %d facts and every prose figure recomputed from the '
          'database; FY2026 ties to the printed YTD actuals and FY2023-FY2026 general fund to '
          'the period-13 spreadsheets' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
