#!/usr/bin/env python3
"""INFLATION AND SCHOOL COSTS: one topic page on the School spending history shelf.

    python3 scripts/build_inflation_topic.py           # write fy28/public/data/topics/<id>.json
    python3 scripts/build_inflation_topic.py --check   # fail if it would change
    python3 scripts/verify_inflation_topic.py          # every headline figure, by another route

    inflation-and-school-costs   /school-spending-history/inflation-and-school-costs

WHY. TJ, 20 October 2026: "we need an INFLATION page... something that analyzes inflation
across the categories, to see the biggest hits of inflation. The schools have since claimed
inflation is a driver of deficits. lets see if thats true in this page." And: "start the
page with a school committee quote" -- so the page opens with the claim it tests, in the
words of the School Committee minutes, and then tests it.

WHAT IT MEASURES, AND WHAT IT CANNOT (rule 7). The data can show which kinds of school
spending grew faster or slower than prices. It cannot show that rising prices CAUSED a
deficit: a deficit is costs against revenue, a budget line is price times quantity (rule 11),
and household prices are not the prices a school pays. Every claim is a comparison of two
measured things; every cause is a hypothesis, and says so.

THE FOUR TESTS.
  1. SINCE FY2009 (the signature). Each spending type's dollars added, first DESE year to
     last, split in two: the part that KEPT UP WITH RISING PRICES -- the start-year amount
     times the rise in Boston-area prices -- and the part BEYOND PRICES, the rest (it can be
     negative). This is CLAUDE.md rule 4, weight times excess, drawn: the largest dollar
     "inflation hit" is wherever the base was largest; the pull beyond prices is the second
     part. The split is OUR arithmetic.
  2. THE INFLATION WINDOW. The longest run of fiscal years in which Boston-area prices rose
     faster than the 2.5% Proposition 2½ lets the levy limit rise -- FOUND from the data, not
     assumed -- and each type's growth across it, against prices. Because the start year
     moves the answer, the year before is computed too and printed beside it. Revenue is NOT
     modelled here: the levy limit is measured as DLS prints it, with any override in the
     window taken out and named (an override is a vote, not growth), and the forward version
     is /crisis/cost-and-revenue-growth.
  3. PER TEACHER. Teachers spending over teacher FTE, the closest the DESE data gets to a
     price; the same division /school-spending-history/pay-or-headcount publishes. Tuition is
     NOT divided by placements: /special-education/cost-per-placement says why that quotient
     is not a price, and this page does not contradict it.
  4. PAYMENT FOR PAYMENT (TJ, 20 October 2026: "compare payment for payment"). The school
     MUNIS journal, published and redaction-cleared, FY2023-FY2026, general fund and every
     school special fund. A SERIES is one shown payee on one account, paid by invoice in every
     one of the four years. It counts as LIKE FOR LIKE only if its cadence is fixed, by one of
     two tests declared here:
       installment  each year's payments sum to an exact whole number of the smallest amount
                    paid at least twice that year, and that number is the same every year
                    (a contract paid in equal instalments, some months paid together);
       monthly      ten to fourteen payments in each closed year (FY2023-FY2025), and at
                    least six in FY2026, whose close is not posted.
     The TYPICAL payment is the instalment, or the median monthly payment. It is set against
     Boston-area prices over the same fiscal years. A series holds the payee, the account and
     the number of payments constant; it does NOT hold constant what each payment buys -- the
     buses a day, the people insured, the kilowatt-hours -- and each is a registered gap.
     Masked payees (families) are never a series. Every matched account's yearly total is
     tied to the period-13 report the Town printed before anything is written.

  5. EACH KIND AGAINST ITS OWN INFLATION (TJ, 20 October 2026). Test 1 again, with each
     kind's start-year amount grown by a price index FOR THAT KIND OF THING -- school pay,
     public employers' benefit costs, groceries, home energy -- named with its reason in
     sources/data/inflation-cost-index-map.csv (ours) and landed by fetch_bls_cost_indexes.py.
     Buildings is split by DESE function code (custodians, heat and utilities, the rest),
     weighted by what DESE printed for each in the start year. A kind with no published index
     of its own is measured against household prices and starred. Every index is national or
     regional: what that kind of thing cost employers or households, not what Lunenburg paid.

PRICES. The BLS CPI-U for Boston-Cambridge-Newton, as fiscal-year averages July to May,
read by build_spending_staff_students_topics.cpi() -- one loader, so this page and every
other inflation-adjusted figure on the shelf cannot disagree. Called "Boston-area prices"
in the prose (TJ: "im not good at this finance language"); the index is named in sources.
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import journal as J  # noqa: E402
# The shelf's loaders, imported, never copied: DESE spending by function, the price index,
# the fifteen spending types. Importing it runs nothing (its main() is behind __main__).
import build_spending_staff_students_topics as SH  # noqa: E402

TID = 'inflation-and-school-costs'
ME = os.path.basename(__file__)
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % TID)
DATA = os.path.join(ROOT, 'sources', 'data')
MODEL = os.path.join(ROOT, 'fy28', 'public', 'data', 'model.json')
MINUTES = 'sources/meetings/text/school-committee/'
BUDGET_TXT = ('sources/district-budget/text/sc-meetings/'
              '2025-02-26-fy26-superintendent-s-proposed-budget-2-26-25.txt')
BUDGET_PDF = ('/docs/district-budget/docs/sc-meetings/'
              '2025-02-26-fy26-superintendent-s-proposed-budget-2-26-25.pdf')
YTD_CSV = os.path.join(DATA, 'munis-school-ytd.csv')
JY = J.YEARS                      # FY2023-FY2026
SERIES_SHOWN = 4                  # the largest matched series drawn; the table holds all
# A series must average $37,500 a year or more. Below it a health account carries one or two
# subscribers, and a change of plan tier moves the bill more than any price: OUR threshold.
SERIES_MIN = 150000

# The documents each limit would be closed by. Prose, no figures.
SCHOOL_PRICES = ('the district’s level-service worksheets, giving each line’s price and '
                 'quantity assumptions, from the Business Office')
UNIT_RATES = ('the rate sheets behind each bill: daily rate per bus and buses run, premium '
              'per plan tier and subscribers, rate per kWh')


def fail(msg):
    raise SystemExit('build_inflation_topic: ' + msg)


def rel(path):
    return os.path.relpath(path, ROOT)


# --------------------------------------------------------------------------- inputs

def levy_limits():
    """{fy: the levy limit DLS prints} for Lunenburg. DLS's new growth file prints each
    year's PRIOR levy limit, so a row for FY y gives the limit of FY y-1."""
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dls-new-growth.csv'), encoding='utf-8')):
        if r['municipality'] == 'Lunenburg' and r['prior_levy_limit']:
            out[int(r['fy']) - 1] = float(r['prior_levy_limit'])
    if not out:
        fail('no Lunenburg levy limits in dls-new-growth.csv')
    return out


def overrides():
    """{fy: $} of operating overrides Lunenburg PASSED, as DLS records them."""
    out = defaultdict(float)
    for r in csv.DictReader(open(os.path.join(DATA, 'dls-override-votes.csv'), encoding='utf-8')):
        if r['municipality'] == 'Lunenburg' and r['result'] == 'WIN' and r['vote_type'] == 'Override':
            out[int(r['fy'])] += float(r['amount'])
    return dict(out)


def printed_ytd():
    """{(account, fy): ytd_expended} from the period-13 reports the Town printed (the
    published spreadsheets, extracted to munis-school-ytd.csv)."""
    return {(r['account'], int(r['fiscal_year'])): Decimal(r['ytd_expended'])
            for r in csv.DictReader(open(YTD_CSV, encoding='utf-8'))
            if r['period'] == '13'}


def text_of(relpath):
    p = os.path.join(ROOT, relpath)
    if not os.path.exists(p):
        fail('%s is not on disk' % relpath)
    return TP._norm_quote(open(p, encoding='utf-8').read())


def said_from(relpath, quote, href, label, board='School Committee', date=None):
    if TP._norm_quote(quote) not in text_of(relpath):
        fail('quote is not verbatim in %s: %r' % (relpath, quote))
    date = date or re.search(r'(\d{4}-\d{2}-\d{2})', relpath).group(1)
    return dict(quote=' '.join(quote.split()), board=board, date=date, href=href, label=label)


# --------------------------------------------------------------------------- each kind's own inflation

# TJ, 20 October 2026: measure each kind of school spending against inflation FOR THAT KIND OF
# THING, not only against household prices. Which index stands for which kind, and why, is
# OUR choice and lives in one file, below the line; the indexes are BLS's, as landed by
# scripts/fetch_bls_cost_indexes.py. The household index stays the one loader the shelf uses.
COST_MAP = os.path.join(DATA, 'inflation-cost-index-map.csv')
HOUSEHOLD = SH.CPI_SERIES
# A fiscal year, July to June, as the months each frequency publishes. The Employment Cost
# Index is measured in the third month of each quarter (Sep, Dec, Mar, Jun).
FY_MONTHS = {'quarterly': (9, 12, 3, 6), 'monthly': (7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6)}


def cost_map():
    """[row] of inflation-cost-index-map.csv, every type of SH.types() named, parts of one
    type split by DESE function code."""
    rows = list(csv.DictReader(open(COST_MAP, encoding='utf-8')))
    if not rows:
        fail('%s is empty' % rel(COST_MAP))
    for r in rows:
        if (r['fallback'] == 'yes') != (r['series_id'] == HOUSEHOLD):
            fail('%s: %s is marked fallback=%s but measured against %s'
                 % (rel(COST_MAP), r['key'], r['fallback'], r['series_id']))
    return rows


def cost_index(series, frequency):
    """{fy: the July-to-June average of one BLS series}, from the responses as landed. A
    value BLS printed as '-' (not published) is skipped and never filled: a year missing any
    month is not computed."""
    if series == HOUSEHOLD:
        return SH.cpi()
    keys = sorted(r['key'] for r in csv.DictReader(open(SH.MANIFEST, encoding='utf-8'))
                  if re.fullmatch(r'federal-bls/%s-\d{4}-\d{4}\.json' % series, r['key']))
    if not keys:
        fail('no %s responses in archive-manifest.csv' % series)
    m = {}
    for k in keys:
        d = json.load(open(os.path.join(ROOT, 'sources', k), encoding='utf-8'))
        if d.get('status') != 'REQUEST_SUCCEEDED':
            fail('%s is not a successful BLS response' % k)
        s, = d['Results']['series']
        if s['seriesID'] != series:
            fail('%s holds %s, not %s' % (k, s['seriesID'], series))
        for x in s['data']:
            p = x['period']
            if x['value'] == '-' or p == 'M13':
                continue
            mo = int(p[1:]) * 3 if p.startswith('Q') else int(p[1:])
            km = (int(x['year']), mo)
            if km in m and m[km] != float(x['value']):
                fail('two responses disagree about %s %s' % (series, km))
            m[km] = float(x['value'])
    months = FY_MONTHS[frequency]
    out = {}
    for y in range(min(m)[0] + 1, max(m)[0] + 2):
        obs = [m.get((y - 1 if mo >= 7 else y, mo)) for mo in months]
        if all(v is not None for v in obs):
            out[y] = sum(obs) / len(obs)
    return out


def own_inflation(FX, g0, g1, T0):
    """{type key: (rise of its own price index g0 to g1, [(part, series, weight, rise)])}.
    A type in several parts (buildings) is weighted by what DESE printed for each part's
    function codes in g0 -- the start-year mix, grown by each part's own index. The last
    part listed for a type takes the remainder of its g0 total, and its codes must be
    exactly the codes DESE printed in g0 that no other part names."""
    rows = cost_map()
    idx, rise = {}, {}
    by = defaultdict(list)
    for r in rows:
        by[r['key']].append(r)
    if set(by) != set(T0):
        fail('%s names %s; the spending types are %s'
             % (rel(COST_MAP), sorted(by), sorted(T0)))
    out = {}
    for k, parts in by.items():
        got, used = [], 0.0
        for i, r in enumerate(parts):
            s = r['series_id']
            if s not in idx:
                idx[s] = cost_index(s, r['frequency'])
                if g0 not in idx[s] or g1 not in idx[s]:
                    fail('%s has no full fiscal-year average for FY%d or FY%d' % (s, g0, g1))
                rise[s] = idx[s][g1] / idx[s][g0] - 1
            if len(parts) == 1:
                w = T0[k][2]
            elif i < len(parts) - 1:
                codes = [c.strip() for c in r['dese_codes'].split(',')]
                w = sum(FX[g0]['code'].get(c, 0.0) for c in codes)
                used += w
            else:
                named = {c.strip() for p in parts[:-1] for c in p['dese_codes'].split(',')}
                rest = {c for c in FX[g0]['code'] if c[:1] == '4' and c not in named
                        and FX[g0]['code'][c]}
                listed = {c.strip() for c in r['dese_codes'].split(',')}
                if not rest <= listed:
                    fail('%s: FY%d prints %s codes %s that no part of the map names'
                         % (rel(COST_MAP), g0, k, sorted(rest - listed)))
                w = T0[k][2] - used
            got.append((r['part'], s, w, rise[s]))
        if abs(sum(w for _, _, w, _ in got) - T0[k][2]) > 1:
            fail('%s: the parts no longer add to the FY%d total' % (k, g0))
        out[k] = (sum(w * x for _, _, w, x in got) / T0[k][2], got)
    return out, rise, rows


# --------------------------------------------------------------------------- payment for payment

def series():
    """Every like-for-like recurring series in the journal (module docstring, test 4)."""
    A = J.accounts()
    g = defaultdict(lambda: defaultdict(list))
    for r in J.actuals():
        if J.KIND_OF[r['source']] != 'invoice':
            continue
        p = J.payee(r)
        if p is None or p is J.MASKED:      # a family is never a series
            continue
        g[(p, r['account'])][r['fy']].append(r['amt'])
    out = []
    for (p, acct), v in g.items():
        if not all(y in v for y in JY):
            continue
        total = sum(sum(v[y]) for y in JY)
        if total < SERIES_MIN:
            continue
        n = {y: len(v[y]) for y in JY}
        kind, typ = None, None
        ns, inst = set(), {}
        for y in JY:
            c = Counter(x for x in v[y] if x > 0)
            rep = sorted(a for a, k in c.items() if k >= 2)
            if not rep:
                break
            q = sum(v[y]) / rep[0]
            if q != int(q):
                break
            ns.add(int(q))
            inst[y] = rep[0]
        else:
            if len(ns) == 1:
                kind, typ = 'installment', inst
        if kind is None and all(10 <= n[y] <= 14 for y in JY[:-1]) and n[JY[-1]] >= 6:
            kind = 'monthly'
            typ = {y: statistics.median([x for x in v[y] if x > 0]) for y in JY}
        if kind is None:
            continue
        a = A[acct]
        out.append(dict(payee=p, account=acct, fund=a['fund'], fund_name=a['fund_name'],
                        desc=a['account_description'], kind=kind, n=n,
                        per_year=(ns.pop() if kind == 'installment' else None),
                        typical={y: float(typ[y]) for y in JY}, total=float(total),
                        year_total={y: float(sum(v[y])) for y in JY}))
    out.sort(key=lambda s: -s['total'])
    if not out:
        fail('no recurring series passes either cadence test')
    # RECONCILE (rule 13): every matched account's yearly total in the journal equals what the
    # Town's period-13 report prints for it. A series is checked inside a total the books foot.
    pr = printed_ytd()
    acc_total = defaultdict(Decimal)
    for r in J.actuals():
        acc_total[(r['account'], r['fy'])] += r['amt']
    for s in out:
        for y in JY:
            k = (s['account'], y)
            if k not in pr:
                fail('%s FY%d is not in the period-13 report' % k)
            if abs(acc_total[k] - pr[k]) > Decimal('0.005'):
                fail('%s FY%d: the journal sums to %s, the period-13 report prints %s'
                     % (k[0], y, acc_total[k], pr[k]))
            s.setdefault('printed', {})[y] = float(pr[k])
    return out


# --------------------------------------------------------------------------- the page

def build():
    src = SH.sources()
    P = SH.cpi()
    FX = SH.functions()
    g0, g1 = min(FX), max(FX)
    gy = sorted(FX)
    if any(y not in P for y in gy) or g0 - 1 not in P:
        fail('a spending year has no full fiscal-year price average')
    LEVY = 100 * json.load(open(MODEL, encoding='utf-8'))['assumptions']['levy_growth']
    T0, T1 = SH.types(FX[g0]), SH.types(FX[g1])
    if set(T0) != set(T1):
        fail('the spending types differ between FY%d and FY%d' % (g0, g1))
    tt0, tt1 = FX[g0]['total'], FX[g1]['total']
    px = P[g1] / P[g0] - 1
    name = {k: v[0] for k, v in T1.items()}
    added = {k: T1[k][2] - T0[k][2] for k in T1}
    kept = {k: T0[k][2] * px for k in T1}
    beyond = {k: added[k] - kept[k] for k in T1}
    add_t, kept_t = tt1 - tt0, tt0 * px
    beyond_t = add_t - kept_t
    if abs(sum(added.values()) - add_t) > 25:
        fail('the types no longer add to DESE’s total change')
    # THE NET HIDES THE PARTS (TJ, 20 October 2026: "hard to believe 8m of 10m was from
    # inflation given the numbers i see for 'on top of inflation'"). The types past inflation
    # and the types short of it are summed SEPARATELY, so a reader sees both, not only the net.
    up_k = sorted(k for k in beyond if beyond[k] >= 0)
    dn_k = sorted(k for k in beyond if beyond[k] < 0)
    up_t, dn_t = sum(beyond[k] for k in up_k), sum(beyond[k] for k in dn_k)
    if abs(up_t + dn_t - beyond_t) > 25 or not up_k or not dn_k:
        fail('the types past and short of inflation no longer add to the net')
    top_b = max(beyond, key=beyond.get)
    low_b = min(beyond, key=beyond.get)
    if top_b != 'BENE' or low_b != 'TCHR':
        fail('insurance is no longer furthest beyond prices, or teachers furthest under; '
             'the second conclusion names them')
    if not (kept_t > beyond_t > 0):
        fail('keeping up with prices is no longer the larger part of the rise')
    big_k = max(kept, key=kept.get)

    # ---- each kind against its OWN inflation (inflation-cost-index-map.csv)
    OWN, RISE, CMAP = own_inflation(FX, g0, g1, T0)
    own_kept = {k: T0[k][2] * OWN[k][0] for k in T1}
    own_beyond = {k: added[k] - own_kept[k] for k in T1}
    own_kept_t = sum(own_kept.values())
    own_beyond_t = add_t - own_kept_t
    fallback = {r['key'] for r in CMAP if r['fallback'] == 'yes' and r['part'] == 'all'}
    wage_rise = 100 * RISE['CIU3026110000000I']
    bene_rise = 100 * RISE['CIU3030000000000I']
    if not (0 < own_beyond['BENE'] < beyond['BENE']):
        fail('insurance no longer runs past its own index by less than past household prices; '
             'the second conclusion says it does')
    if '%.1f' % (own_beyond_t / 1e6) != '%.1f' % (beyond_t / 1e6):
        fail('the net past each kind’s own inflation no longer rounds to the net past household '
             'prices; conclusion 2 says it is the same')
    if abs(own_beyond['TCHR']) >= abs(beyond['TCHR']):
        fail('teachers are no longer closer to their own index than to household prices')

    # ---- the window: the longest run of years prices rose faster than the levy limit may
    yoy = {y: 100 * (P[y] / P[y - 1] - 1) for y in P if y - 1 in P}
    runs, cur = [], []
    for y in gy:
        if yoy[y] > LEVY:
            cur.append(y)
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    run = max(runs, key=len)
    w0, w1 = run[0] - 1, run[-1]
    nw = len(run)
    chg = lambda a, b: 100.0 * (b / a - 1)
    wp = chg(P[w0], P[w1])
    ws = chg(FX[w0]['total'], FX[w1]['total'])
    ep = chg(P[w0 - 1], P[w1])                 # one year earlier: the start year moves it
    es = chg(FX[w0 - 1]['total'], FX[w1]['total'])
    cap = 100 * ((1 + LEVY / 100) ** nw - 1)
    W0, W1 = SH.types(FX[w0]), SH.types(FX[w1])
    wg = {k: chg(W0[k][2], W1[k][2]) for k in W1}
    wb = {k: W1[k][2] - W0[k][2] * (1 + wp / 100) for k in W1}
    if not (ws < wp and es > ep):
        fail('the window no longer reads "under prices from %s, over from the year before"; '
             'the third conclusion says so' % C.fy(w0))
    LL = levy_limits()
    OV = overrides()
    ov_in = sum(v for y, v in OV.items() if w0 < y <= w1)
    ov_years = sorted(y for y in OV if w0 < y <= w1)
    wl = chg(LL[w0], LL[w1] - ov_in)
    ll_long = chg(LL[g0], LL[g1] - sum(v for y, v in OV.items() if g0 < y <= g1))

    # ---- per teacher
    SS = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'school-staffing.json'),
                        encoding='utf-8'))
    T = {r['fy']: r['fte'] for r in SS['composition']['district']}
    if any(y not in T for y in (g0, g1, w0, w1)):
        fail('a year needed for spending per teacher has no teacher FTE')
    Wt = {y: FX[y]['cat']['TCHR'] / T[y] for y in (g0, g1, w0, w1)}
    wt_long, wt_win = chg(Wt[g0], Wt[g1]), chg(Wt[w0], Wt[w1])
    if not wt_long > wage_rise:
        fail('spending per teacher no longer rose faster than school pay; conclusion 2 says it did')

    # ---- payment for payment
    S = series()
    j0, j1 = JY[0], JY[-1]
    jp = chg(P[j0], P[j1])
    for s in S:
        s['chg'] = chg(s['typical'][j0], s['typical'][j1])
    shown = S[:SERIES_SHOWN]
    hi = next((s for s in S if s['desc'] == 'HEALTH INSURANCE' and s['fund'] == '0100'), None)
    bus = next((s for s in S if s['kind'] == 'installment' and 'TRANSPORT' in s['desc']), None)
    if hi is None or bus is None or S[0] is not hi or S[1] is not bus:
        fail('the two largest like-for-like series are no longer general fund health insurance '
             'and the regular bus instalments; the fourth conclusion names them')
    if not (hi['chg'] > jp and bus['chg'] > jp):
        fail('health insurance or the buses no longer rose faster than prices')
    above = sum(1 for s in S if s['chg'] > jp)

    # ---- the district's own printed inflation rate, read off its budget, not typed
    btxt = text_of(BUDGET_TXT)
    m = re.search(r'Chapter 70 increased [\d.]+ %; rate of inflation (\d+)% \(FY 24\)', btxt)
    if not m:
        fail('the FY26 budget no longer prints a FY 24 rate of inflation where it did')
    d24 = float(m.group(1))

    # ---------------------------------------------------------------- formatters
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    U = lambda v: figure(v, C.usd(v))
    SU = lambda v: figure(v, ('+' if v >= 0 else '-') + C.usd(abs(v)))
    SP = lambda v: figure(v, '%+.1f%%' % v, 'percent')
    PC = lambda v, dp=1: figure(v, C.pct(v, dp), 'percent')
    # Millions for the headline figures: "$8.9 million" is what a resident can repeat at a
    # meeting; the exact dollars stay in the table (TJ, 20 October 2026: "can they understand
    # the phrasing and can repeat it?").
    M = lambda v: figure(v, '$%.1f million' % (v / 1e6))
    f, con = LD.fact, TP.conclusion
    span = {'a': F(g0), 'b': F(g1)}
    wspan = {'a': F(w0), 'b': F(w1)}
    jspan = {'a': F(j0), 'b': F(j1)}

    def slabel(s):
        what = {'HEALTH INSURANCE': 'Health insurance', 'ELECTRICITY CHARGES': 'Electricity'}.get(
            s['desc'], s['desc'].capitalize())
        if 'TRANSPORT' in s['desc']:
            what = 'Regular buses'
        fund = '' if s['fund'] == '0100' else ', %s' % s['fund_name'].title().replace(' Fund', '').replace(' Revolving', '')
        return '%s%s' % (what, fund)

    for s in S:
        s['label'] = slabel(s)
    if len({s['label'] for s in shown}) != len(shown):
        fail('two shown series share a label')

    # ---------------------------------------------------------------- the lead quote
    LQ = TP.lead_quote(
        'the cost in schools keep going up for two reasons. One is inflation if you look at '
        'inflation since 2020 we have experienced 18% inflation over that four year period. Our '
        'costs are going to go up at least that much because dollars are worth that much less.',
        who='Anthony Sculimbrene, Vice Chair', board='School Committee', date='2025-02-26',
        href='/docs/minutes/text/school-committee/2025-02-26-minutes-7076.txt',
        label='School Committee minutes, 26 February 2025',
        text=MINUTES + '2025-02-26-minutes-7076.txt')

    said = [
        said_from(BUDGET_TXT, 'Available revenue is not keeping pace with escalating expenses.',
                  BUDGET_PDF, 'Superintendent’s FY26 proposed budget, presented 26 February '
                              '2025, page 16', date='2025-02-26'),
        said_from(MINUTES + '2024-02-07-minutes-6395.txt',
                  'the bus contracts go up because of inflation, our money doesn’t stretch as '
                  'far as it used to.',
                  '/docs/minutes/text/school-committee/2024-02-07-minutes-6395.txt',
                  'School Committee minutes, 7 February 2024, answering a resident'),
    ]

    # The committee's own figure, read out of the quote rather than typed (rule 2).
    m18 = re.search(r'(\d+)% inflation', LQ['quote'])
    if not m18:
        fail('the lead quote no longer states an inflation percentage')
    said_pct = int(m18.group(1))

    # ---------------------------------------------------------------- facts
    # ONE VOCABULARY, for a resident: "inflation" (Boston-area prices, said once in each chart
    # note), "on top of inflation", "less than inflation", "the town's tax limit" for the levy
    # limit. Never "beyond prices", "FTE", "instalment" or "like for like" in a claim.
    facts = [
        f('kept', M(kept_t), 'of the increase was just inflation', 'estimate'),
        f('up', M(up_t), 'beyond inflation, in %s of %s kinds of spending'
          % (C.num(len(up_k)), C.num(len(beyond))), 'estimate',
          {'n': figure(len(up_k), C.num(len(up_k)), 'kinds'),
           'm': figure(len(beyond), C.num(len(beyond)), 'kinds')}),
        f('down', M(-dn_t), 'less than inflation, in the other %s' % C.num(len(dn_k)),
          'estimate', {'n': figure(len(dn_k), C.num(len(dn_k)), 'kinds')}),
        f('prices', SP(100 * px), 'inflation, %s to %s' % (C.fy(g0), C.fy(g1)),
          'published', span),
        f('bene', M(beyond[top_b]), 'insurance and retirement, on top of inflation',
          'estimate'),
        f('tchr', U(-beyond[low_b]), 'teachers: less than inflation alone', 'estimate'),
        f('w-spend', SP(ws), 'all school spending, %s to %s' % (C.fy(w0), C.fy(w1)),
          'published', wspan),
        f('w-price', SP(wp), 'inflation, the same %s years' % C.num(nw), 'published',
          {'n': figure(nw, C.num(nw), 'years')}),
        f('w-levy', SP(wl), 'the town’s tax limit, same years, without the override',
          'published'),
        f('pay-hi', SP(hi['chg']), 'the same monthly health insurance bill, %s to %s'
          % (C.fy(j0), C.fy(j1)), 'published', jspan),
        f('pay-bus', SP(bus['chg']), 'the same bus contract payment, same years', 'published'),
        f('pay-price', SP(jp), 'inflation, same years', 'published'),
    ]

    # ---------------------------------------------------------------- conclusions
    # THE PAGE SPEAKS THE WAY IT WAS EXPLAINED TO TJ (20 October 2026: "you are summarizing to
    # ME in great ways but making the page too financially jargoned"). Each claim: the plain
    # point first, then the figures that back it. No finance term in a claim.
    if j1 != J.OPEN_FY:
        fail('the last journal year is no longer the open one; conclusion 4 calls it not yet closed')
    conclusions = [
        con('The %s inflation figure holds up: prices rose %s from %s to %s.'
            % (C.pct(said_pct, 0), C.pct(wp), C.fy(w0), C.fy(w1)), ['w-price', 'prices'],
            {'q': PC(said_pct, 0), 'a': PC(wp), 'y': F(w0), 'z': F(w1)},
            notes=[step('Household prices, not a school’s.', 'gap',
                        closes=SCHOOL_PRICES)]),
        con('%s kinds of spending grew %s beyond inflation; the other %s grew %s less.'
            % (C.num(len(up_k)), '$%.1f million' % (up_t / 1e6), C.num(len(dn_k)),
               '$%.1f million' % (-dn_t / 1e6)), ['up', 'down', 'bene', 'tchr'],
            {'n': figure(len(up_k), C.num(len(up_k)), 'kinds'), 'a': M(up_t),
             'm': figure(len(dn_k), C.num(len(dn_k)), 'kinds'), 'b': M(-dn_t)},
            # EACH KIND AGAINST ITS OWN INFLATION (TJ, 20 October 2026) changes what the two
            # outliers mean, so the notes say it: most of insurance's excess is what benefits
            # cost public employers generally, and teachers ran close to school pay -- while
            # spending PER TEACHER rose faster than school pay (rule 7: not a pay rise; fewer
            # teachers, steps and experience fit the same number).
            notes=[step('Insurance and retirement: %s over; %s past public employers’ benefit '
                        'costs.' % ('$%.1f million' % (beyond[top_b] / 1e6),
                                        '$%.1f million' % (own_beyond[top_b] / 1e6)),
                        'estimate', {'a': M(beyond[top_b]), 'b': M(own_beyond[top_b])}),
                   step('Teachers: %s under; fewer, each costing %s more, against %s for '
                        'school pay.' % (C.usd(-beyond[low_b]), C.pct(wt_long), C.pct(wage_rise)),
                        'measured', {'b': U(-beyond[low_b]), 'c': PC(wt_long), 'd': PC(wage_rise)},
                        cite=('/school-spending-history/pay-or-headcount', 'Pay or headcount')),
                   step('Net %s, the same against each kind’s own inflation.'
                        % ('$%.1f million' % (beyond_t / 1e6)), 'estimate', {'a': M(beyond_t)})]),
        con('Meanwhile the town’s tax limit grew less than inflation: %s against %s.'
            % (C.pct(wl), C.pct(wp)), ['w-levy', 'w-price', 'w-spend'],
            {'a': PC(wl), 'b': PC(wp)},
            notes=[step('School spending grew %s, also less. From %s it grew more: %s against %s.'
                        % (C.pct(ws), C.fy(w0 - 1), C.pct(es), C.pct(ep)),
                        'measured', {'s': PC(ws), 'y': F(w0 - 1), 'a': PC(es), 'b': PC(ep)}),
                   step('It grows %s a year plus new building; no override.'
                        % C.pct(LEVY), 'measured', {'l': PC(LEVY)})]),
        con('Health insurance and buses rose faster than inflation, bill for bill: %s and %s against %s.'
            % (C.pct(hi['chg']), C.pct(bus['chg']), C.pct(jp)),
            ['pay-hi', 'pay-bus', 'pay-price'],
            {'a': PC(hi['chg']), 'b': PC(bus['chg']), 'c': PC(jp)},
            notes=[step('Same company, account and payments a year, %s to %s (still open): '
                        '%s of %s rose faster.'
                        % (C.fy(j0), C.fy(j1), C.num(above), C.num(len(S))),
                        'measured', dict(jspan, c=figure(above, C.num(above), 'bills'),
                                         d=figure(len(S), C.num(len(S)), 'bills'))),
                   step('A bigger bill can mean more buses or more people insured.', 'gap',
                        closes=UNIT_RATES)]),
    ]

    # ---------------------------------------------------------------- charts
    order = sorted(T1, key=lambda k: -added[k])
    # A BULLET CHART: the bar is what each type added, the tick what rising prices alone would
    # have added. It replaced a diverging stack whose second part sat left of zero for some
    # rows and right for others (TJ, 20 October 2026: "i dont know how to read the chart").
    chart = TP.ranking(
        'Each type against inflation',
        [(name[k], added[k]) for k in order], '$',
        marks={name[k]: kept[k] for k in order},
        value_label='Added', mark_label='Inflation alone', gap_label='on top of inflation',
        under_label='less than inflation',
        note='%s to %s, all school money, grants included. The tick: what keeping up with inflation '
             'alone would have added (Boston-area prices; ours).' % (C.fy(g0), C.fy(g1)),
        note_figures={'a': F(g0), 'b': F(g1)})
    # EACH KIND AGAINST ITS OWN INFLATION, drawn as the signature is drawn -- same bars, the
    # tick moved -- so the two read as one picture measured twice. It REPLACED the year-by-year
    # chart of prices against spending: that chart's figures are conclusion 3's and stay in
    # the table's second view; this measurement is new and had no picture. A star marks the
    # kinds with no published index of their own, measured against household prices instead.
    star = lambda k: name[k] + (' *' if k in fallback else '')
    own_chart = TP.ranking(
        'Each type against its own inflation',
        [(star(k), added[k]) for k in order], '$',
        marks={star(k): own_kept[k] for k in order},
        value_label='Added', mark_label='Its own inflation alone',
        gap_label='on top of its own inflation', under_label='less than its own inflation',
        note='The tick: school pay, public employers’ benefits, groceries or home energy, '
             'national or regional, not Lunenburg’s. * None published: household prices.')
    pay_chart = TP.ranking(
        # The chart sorts by RATE, so each bar carries its bill's SIZE: a $5,000 account
        # rising 29% must not read as the headline above a $300,000 one (rule 4).
        'The same bills, year to year', [('%s (%s a bill)' % (s['label'], C.usd(s['typical'][j1])), s['chg'])
                                         for s in shown]
        + [('Inflation', jp)], '%', decimals=1, highlight='Inflation',
        note='Typical bill, %s to %s: same company, same account, same number of payments each '
             'year. From the school department’s payment records.' % (C.fy(j0), C.fy(j1)),
        note_figures=jspan)

    # ---------------------------------------------------------------- table
    usd = C.usd

    def paid(s):
        ns = ', '.join(C.num(s['n'][y]) for y in JY)
        return ('%s instalments, paid as %s' % (C.num(s['per_year']), ns)
                if s['kind'] == 'installment' else ns)
    sgn = lambda v: ('+' if v >= 0 else '-') + usd(abs(v))
    SHORT = {'CIU3026110000000I': 'School pay', 'CIU3030000000000I': 'Public employers’ benefits',
             'CUURS11ASAF11': 'Groceries, Boston area', 'CUUR0100SAH21': 'Home energy, Northeast',
             HOUSEHOLD: 'Household prices (none of its own)'}
    PART = {'CIU3026110000000I': 'school pay', 'CUUR0100SAH21': 'home energy, Northeast',
            HOUSEHOLD: 'household prices'}

    def against(k):
        parts = OWN[k][1]
        if len(parts) == 1:
            return SHORT[parts[0][1]]
        s = '; '.join('%s: %s' % (p, PART[s]) for p, s, _, _ in parts)
        return s[:1].upper() + s[1:]
    table = dict(caption='Inflation and school costs', views=[
        dict(key='since', label='Since %s' % C.fy(g0), total_col=None, kinds=['ledger'] * 3,
             columns=['Added', 'Inflation alone', 'On top of inflation'],
             rows=[dict(label=name[k], cells=[sgn(added[k]), sgn(kept[k]), sgn(beyond[k])])
                   for k in order]
             + [dict(label='All school spending', cells=[sgn(add_t), sgn(kept_t), sgn(beyond_t)])],
             note='%s to %s, DESE spending by function, all funds. Inflation alone is the %s '
                  'amount grown by the %s rise in Boston-area prices; ours.'
                  % (C.fy(g0), C.fy(g1), C.fy(g0), C.pct(100 * px))),
        dict(key='own', label='Against its own inflation', total_col=None, kinds=['ledger'] * 5,
             columns=['Added', 'Its own inflation alone', 'On top of its own', 'Its index rose',
                      'Measured against'],
             rows=[dict(label=name[k], cells=[sgn(added[k]), sgn(own_kept[k]), sgn(own_beyond[k]),
                                              '%+.1f%%' % (100 * OWN[k][0]), against(k)])
                   for k in order]
             + [dict(label='All school spending', cells=[sgn(add_t), sgn(own_kept_t),
                                                         sgn(own_beyond_t), '', ''])],
             note='%s to %s. Each kind’s %s amount grown by its own BLS index, July-to-June '
                  'averages; buildings split by DESE code. Indexes and why each: '
                  'inflation-cost-index-map.csv. Ours.' % (C.fy(g0), C.fy(g1), C.fy(g0))),
        dict(key='window', label='%s to %s' % (C.fy(w0), C.fy(w1)), total_col=None,
             kinds=['ledger'] * 3,
             columns=[C.fy(w0), C.fy(w1), 'Growth'],
             rows=[dict(label=name[k], cells=[usd(W0[k][2]), usd(W1[k][2]), '%+.1f%%' % wg[k]])
                   for k in sorted(W1, key=lambda k: -wb[k])]
             + [dict(label='All school spending', cells=[usd(FX[w0]['total']), usd(FX[w1]['total']),
                                                         '%+.1f%%' % ws]),
                dict(label='Inflation (Boston-area prices)', cells=['', '', '%+.1f%%' % wp])],
             note='The %s years inflation ran above %s, ranked by dollars on top of inflation. '
                  'The district’s FY26 budget printed %s inflation for FY 24, naming no index; '
                  'Boston-area prices for that year rose %s.'
                  % (C.num(nw), C.pct(LEVY), C.pct(d24, 0), C.pct(yoy[2024]))),
        dict(key='payments', label='The same bills', total_col=None, kinds=['ledger'] * 4,
             columns=['Typical %s' % C.fy(j0), 'Typical %s' % C.fy(j1), 'Change',
                      'Payments a year'],
             rows=[dict(label='%s — %s' % (s['label'], s['payee']),
                        cells=[usd(s['typical'][j0]), usd(s['typical'][j1]), '%+.1f%%' % s['chg'],
                               paid(s)]) for s in S]
             + [dict(label='Inflation (Boston-area prices)', cells=['', '', '%+.1f%%' % jp, ''])],
             note='The school department’s payment records (MUNIS), %s to %s, every fund. Typical: '
                  'the contract payment, or the median monthly bill. Each account ties to the '
                  'Town’s year-end report.'
                  % (C.fy(j0), C.fy(j1))),
    ])

    COST_SRC = {'CIU3026110000000I': 'Employment Cost Index, wages and salaries, state and local '
                                     'government, elementary and secondary schools',
                'CIU3030000000000I': 'Employment Cost Index, benefits, state and local government',
                'CUURS11ASAF11': 'CPI-U food at home, Boston-Cambridge-Newton',
                'CUUR0100SAH21': 'CPI-U household energy, Northeast'}
    cost_src = [dict(label='US Bureau of Labor Statistics, %s — %s' % (COST_SRC[k.split('/')[1].rsplit('-', 2)[0]],
                                                                      k.split('/')[-1]),
                     href='/docs/' + k)
                for k in sorted(r['key'] for r in csv.DictReader(open(SH.MANIFEST, encoding='utf-8'))
                                if re.fullmatch(r'federal-bls/(%s)-\d{4}-\d{4}\.json' % '|'.join(COST_SRC),
                                                r['key']))]
    if len(cost_src) != 2 * len(COST_SRC):
        fail('expected two BLS responses for each cost index, found %d' % len(cost_src))
    cost_src += [dict(label='Lunenburg Budget Project — PROVENANCE-cost-indexes.md (where the cost '
                            'indexes came from, and the fiscal-year average)',
                      href='/docs/federal-bls/PROVENANCE-cost-indexes.md'),
                 dict(label='Lunenburg Budget Project — inflation-cost-index-map.csv (which index '
                            'each kind of spending is measured against, and why)',
                      href='/docs/data/inflation-cost-index-map.csv')]
    sources = [src['func'], src['func-csv']] + [src[k] for k in sorted(src) if k.startswith('cpi')] + cost_src + [
        src['teachers'],
        dict(label='Massachusetts DLS — new growth and prior levy limit, by town and year '
                   '(new_growth.xlsx), as extracted', href='/docs/data/dls-new-growth.csv'),
        dict(label='Massachusetts DLS — override and underride votes (OverrideUnderrideVotes.xlsx), '
                   'as extracted', href='/docs/data/dls-override-votes.csv'),
        dict(label='Town of Lunenburg — school MUNIS journal, FY2023–FY2026, our redacted reading',
             href=J.PUBLIC['journal']),
        dict(label='Town of Lunenburg — school period-13 year-to-date reports, FY2023–FY2026, as '
                   'extracted', href='/docs/data/munis-school-ytd.csv'),
        dict(label='Lunenburg Public Schools — Superintendent’s FY26 proposed budget, 26 February 2025',
             href=BUDGET_PDF),
        dict(label='School Committee minutes, 26 February 2025',
             href='/docs/meetings/school-committee/2025-02-26-minutes-7076.pdf'),
        dict(label='School Committee minutes, 7 February 2024',
             href='/docs/meetings/school-committee/2024-02-07-minutes-6395.pdf'),
    ]
    for s in sources:
        if s['href'].startswith('/docs/data/') and not os.path.exists(
                os.path.join(ROOT, 'fy28', 'public', s['href'].lstrip('/'))):
            fail('%s is not published' % s['href'])

    return TP.page(
        TID,
        # The sentence a resident repeats, in words first and figures second (TJ, 20 October
        # 2026). "Most" is a claim about the data, so it is asserted, not assumed.
        'Most of the rise in school spending since %s is inflation: %s of %s a year.'
        % (C.fy(g0), '$%.1f million' % (kept_t / 1e6), '$%.1f million' % (add_t / 1e6))
        if kept_t > add_t / 2 else fail('inflation is no longer most of the rise; the finding '
                                         'says it is'),
        facts, conclusions, chart=chart, also=[own_chart, pay_chart], table=table, said=said,
        sources=sources, lead_quote=LQ,
        finding_figures={'y': F(g0), 'a': M(kept_t), 'b': M(add_t)})


def output():
    return json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if REG.TOPICS.get(TID, (None, None, None))[2] != ME:
        fail('%s is not registered to %s in scripts/topic_registry/' % (TID, ME))
    text = output()
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        if cur != text:
            print('STALE %s' % rel(OUT), file=sys.stderr)
            return 1
        print('inflation topic: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % rel(OUT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
