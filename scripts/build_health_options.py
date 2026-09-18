#!/usr/bin/env python3
"""What the town may lawfully do about health insurance, and what every other town spends.

    python3 scripts/build_health_options.py           # write fy28/public/data/health-options.json
    python3 scripts/build_health_options.py --check

TJ, 18 September 2026: "I'm not following the options in terms of which insurance is
available, at what %, etc etc" -- and, on the law: "we cannot break the law or let people
and need to tell them why it can't go below that."

TWO DATASETS, ONE PAYLOAD.

`sources/data/health-insurance-law.csv` is the menu: one row per thing a Massachusetts
town can or cannot do, each with the section that permits or forbids it, who decides, the
threshold, and who the change lands on. Every row links to the statute on
malegislature.gov, so a reader can check the sentence rather than take ours. The research
behind it is notes/findings/MA-MUNICIPAL-HEALTH-INSURANCE.md.

`sources/data/dls-health-insurance.csv` is what every municipality in the Commonwealth
actually spent, FY2002 onward, from Schedule A via the DLS Gateway.

AND THE COMPARISON IS NOT AS SIMPLE AS THE FILE LOOKS. DLS prints its own warning: for a
SELF-INSURED town the figure includes the EMPLOYEE share, and a town accounting through a
trust may have workers' compensation and OPEB inside it -- and nothing in the export says
which town is which. So this payload ranks towns on GROWTH, where a level difference in
what the figure contains cancels, and says so on the page. Lunenburg is fully insured
through the MIIA joint purchase group, so its own figure is the town's premium share.
"""
import argparse
import csv
import io
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
LAW = os.path.join(ROOT, 'sources', 'data', 'health-insurance-law.csv')
SPEND = os.path.join(ROOT, 'sources', 'data', 'dls-health-insurance.csv')
SELF = os.path.join(ROOT, 'sources', 'data', 'dls-health-self-insured.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'health-options.json')
TOWN = 'Lunenburg'
SPAN = 10          # years over which growth is compared
BANDS = [(-100, 0), (0, 2), (2, 4), (4, 6), (6, 8), (8, 10), (10, 100)]
NEIGHBOURS = ['Lunenburg', 'Ayer', 'Groton', 'Littleton', 'Shirley', 'Townsend',
              'Westford', 'Leominster', 'Fitchburg', 'Lancaster', 'Harvard']


def rows(p):
    with io.open(p, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def series():
    by = {}
    for r in rows(SPEND):
        if r['expenditure'] == '':
            continue
        by.setdefault(r['municipality'], {})[int(r['fy'])] = float(r['expenditure'])
    if TOWN not in by:
        raise SystemExit('no %s in %s' % (TOWN, os.path.relpath(SPEND, ROOT)))
    return by


def funding_type(first, last):
    """Self-insured or fully insured, over the window, from the town's own Schedule A.

    TJ, 18 September 2026: "can you create a chart ... based on insurance type? Do we have
    that?" Partly, and the part we have is the one that matters for reading the money. A
    town reporting a HEALTH TRUST FUND pays claims itself: DLS says its figure therefore
    includes the EMPLOYEE share. A town with no trust buys premiums, and its figure is the
    employer share alone. That is the axis on which the two are not the same quantity.

    WHAT IS NOT AVAILABLE, and it is the question most people mean: which POOL a town buys
    through -- MIIA, a regional joint purchase group, the GIC, a carrier direct. No state
    dataset records it (money-gaps.csv), and the GIC's own member list is served only to a
    browser. So this classifies funding arrangement, never carrier, and says so.

    The report's Y/N flag is NOT used: Abington prints N in every year while reporting
    millions in trust expenditures. What is used is whether the trust actually moved money.
    """
    trust = {}
    for r in rows(SELF):
        fy = int(r['fy'])
        if first <= fy <= last:
            try:
                spend = float(r['expenditures'] or 0)
            except ValueError:
                spend = 0.0
            trust.setdefault(r['municipality'], []).append(spend > 0)
    out = {}
    for town, years in trust.items():
        n = sum(1 for y in years if y)
        out[town] = ('self-insured' if n >= len(years) - 1 and n >= 9
                     else 'fully insured' if n == 0 else 'changed in the window')
    return out


def cagr(a, b, years):
    return (b / a) ** (1.0 / years) - 1 if a > 0 and b > 0 and years else None


def build():
    by = series()
    latest = max(by[TOWN])
    first = latest - SPAN
    peers = []
    for town, s in by.items():
        if first in s and latest in s and s[first] > 0:
            g = cagr(s[first], s[latest], SPAN)
            if g is not None:
                peers.append(dict(municipality=town, first=s[first], last=s[latest], growth=round(100 * g, 2)))
    peers.sort(key=lambda p: p['growth'])
    if len(peers) < 300:
        raise SystemExit('only %d municipalities have both FY%d and FY%d' % (len(peers), first, latest))
    me = next(p for p in peers if p['municipality'] == TOWN)
    rank = peers.index(me) + 1
    growths = [p['growth'] for p in peers]
    # IS THE SCENARIO EVEN POSSIBLE? TJ, 18 September 2026: "'Held to 4%' is not
    # believable ... we can't just 'hold it to 4%'. Everyone would choose that obviously.
    # so the conclusion has to be 1 step higher. is it POSSIBLE to hold it to 4%?"
    #
    # It is a fair objection to a modelled rate, and it is answerable with this file rather
    # than with an opinion: count the municipalities that DID hold it, over the same ten
    # years, and count the decades in which Lunenburg itself did. Neither is a promise that
    # it can be done again -- what a town's premium does is claims and a pool, not a policy
    # choice -- but "45% of the Commonwealth" is a different kind of sentence from "if we
    # held it to 4%".
    achievable = []
    for thr in (2.5, 4.0, 5.0, 6.0):
        n = sum(1 for p in peers if p['growth'] < thr)
        achievable.append(dict(threshold=thr, towns=n, of=len(peers), share=round(100.0 * n / len(peers), 1)))
    s_town = by[TOWN]
    rolling = [dict(fy=fy, growth=round(100 * cagr(s_town[fy - SPAN], s_town[fy], SPAN), 2))
               for fy in sorted(s_town) if fy - SPAN in s_town and s_town[fy - SPAN] > 0]
    under = [r for r in rolling if r['growth'] < 4]
    # AND IS THE TOWN UNUSUAL, OR DID EVERYONE TURN? TJ, 18 September 2026: "Are we unique
    # in our % increasing, or did all towns see it above 4% at FY24" -- a fair question to
    # put to a card that says the town crossed 4% in FY2024, and the file answers it. Each
    # of the last four years: what the median municipality's premium did that year, how
    # many were over 4%, and where Lunenburg sat. The honest answer turns out to be both
    # things at once, which is why it is a table and not a sentence.
    recent = []
    for fy in range(latest - 3, latest + 1):
        vals = sorted(100 * (s2[fy] / s2[fy - 1] - 1) for s2 in by.values()
                      if fy in s2 and fy - 1 in s2 and s2[fy - 1] > 0)
        mine = 100 * (by[TOWN][fy] / by[TOWN][fy - 1] - 1)
        recent.append(dict(fy=fy, median=round(statistics.median(vals), 2), towns=len(vals),
                           over_4=sum(1 for v in vals if v > 4),
                           over_4_share=round(100.0 * sum(1 for v in vals if v > 4) / len(vals), 1),
                           town=round(mine, 2), rank=sorted(vals).index(min(vals, key=lambda v: abs(v - mine))) + 1))
    kinds = funding_type(first, latest)
    by_type = {}
    for p in peers:
        k = kinds.get(p['municipality'], 'not known')
        t = by_type.setdefault(k, [])
        t.append(p['growth'])
    types = []
    for k, vals in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        vals.sort()
        types.append(dict(funding=k, towns=len(vals), median=round(statistics.median(vals), 2),
                          quartile_low=round(vals[len(vals) // 4], 2), quartile_high=round(vals[3 * len(vals) // 4], 2),
                          under_4=sum(1 for v in vals if v < 4),
                          under_4_share=round(100.0 * sum(1 for v in vals if v < 4) / len(vals), 1),
                          has_town=kinds.get(TOWN) == k))
    law = rows(LAW)
    if not any(r['available_to_lunenburg'] == 'no' for r in law):
        raise SystemExit('the law file lists nothing the town cannot do; that is not this statute')
    return dict(
        generated_by='scripts/build_health_options.py',
        about='What Massachusetts law lets a town do about health insurance, what each option costs somebody, and what every municipality in the Commonwealth has spent since FY2002.',
        grain='LAW as the statute states it, linked section by section; DOLLARS as each town filed them on Schedule A. The spending figure is a net appropriation and is not the same quantity in every town — see `comparison_caveat`.',
        research='notes/findings/MA-MUNICIPAL-HEALTH-INSURANCE.md',
        options=law,
        can=[r['id'] for r in law if r['available_to_lunenburg'] != 'no'],
        cannot=[r['id'] for r in law if r['available_to_lunenburg'] == 'no'],
        town=dict(
            municipality=TOWN, fy=latest, spent=by[TOWN][latest],
            series=[dict(fy=fy, spent=by[TOWN][fy]) for fy in sorted(by[TOWN])],
            growth=me['growth'], rank=rank, of=len(peers),
            median_growth=round(statistics.median(growths), 2),
            faster_than_median=round(me['growth'] - statistics.median(growths), 2),
            # Every ten-year window the town has data for, so "can it be held" is answered
            # by its own record before anybody else's.
            rolling=rolling,
            decades_under_4=len(under),
            decades=len(rolling),
            last_decade_under_4=under[-1]['fy'] if under else None,
            best_decade=min(rolling, key=lambda r: r['growth']) if rolling else None,
        ),
        achievable=achievable,
        by_funding=dict(
            town_is=kinds.get(TOWN, 'not known'),
            basis='Whether the town reports a health TRUST FUND on Schedule A Part 6: a trust means it pays claims itself (self-insured), no trust means it buys premiums (fully insured). The report’s own Y/N flag is not used — it prints N for towns with millions in trust spending.',
            not_available='Which POOL a town buys through — MIIA, a regional joint purchase group, the GIC, a carrier direct — is recorded in no state dataset, so nothing here is a comparison of carriers.',
            types=types,
        ),
        recent_years=recent,
        peers=dict(
            span_years=SPAN, from_fy=first, to_fy=latest, count=len(peers),
            fastest=peers[-8:][::-1], slowest=peers[:8], all=peers,
            # THE DISTRIBUTION, for the chart: how many towns fall in each band of annual
            # growth, and which band holds Lunenburg. A rank alone ("301 of 343") tells a
            # reader where the town sits and not whether the pack is tight or spread.
            histogram=[dict(band=b, low=lo, high=hi,
                            towns=sum(1 for p in peers if lo <= p['growth'] < hi),
                            has_town=lo <= me['growth'] < hi)
                       for b, (lo, hi) in enumerate(BANDS)],
        ),
        # THE NEIGHBOURS, year by year, for the lines on the chart. The eleven the rest of
        # this project compares against (scripts/fetch_dls_tax_bills.TOWNS), each as its own
        # series so a reader can see whose curve bends and whose does not.
        neighbours=[dict(municipality=t, series=[dict(fy=fy, spent=by[t][fy]) for fy in sorted(by[t])])
                    for t in NEIGHBOURS if t in by],
        comparison_caveat=(
            'DLS prints two warnings on this report and both bite. For a SELF-INSURED town the figure '
            'includes the employee share, and a town accounting through a trust may have workers’ '
            'compensation and OPEB inside it — and nothing in the file says which town is which. So the '
            'LEVEL is not comparable across towns; the GROWTH is, because whatever a town’s figure '
            'contains it contains in both years. Lunenburg is fully insured through the MIIA joint '
            'purchase group, so its figure is the town’s premium share alone.'),
        sources=[
            dict(title='Health Insurance Expenditures, every municipality, FY2002 onward',
                 publisher='Massachusetts Division of Local Services',
                 url='https://dls-gw.dor.state.ma.us/reports/rdPage.aspx?rdReport=ScheduleA.HealthInsurance.HealthInsExpenditures',
                 local='sources/data/dls-health-insurance.csv'),
            dict(title='M.G.L. Chapter 32B — municipal group insurance', publisher='The General Court',
                 url='https://malegislature.gov/Laws/GeneralLaws/PartI/TitleIV/Chapter32B',
                 local='sources/data/health-insurance-law.csv'),
        ],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    d = build()
    text = json.dumps(d, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            raise SystemExit('STALE %s — run: python3 scripts/build_health_options.py' % os.path.relpath(OUT, ROOT))
        print('ok — %d options, %d municipalities compared' % (len(d['options']), d['peers']['count']))
        return
    open(OUT, 'w', encoding='utf-8').write(text)
    t = d['town']
    print('wrote %s: %d options (%d the town cannot do); %s FY%d $%s, growth %.2f%%/yr over %d years — %d of %d, median %.2f%%'
          % (os.path.relpath(OUT, ROOT), len(d['options']), len(d['cannot']), t['municipality'], t['fy'],
             format(int(t['spent']), ','), t['growth'], SPAN, t['rank'], t['of'], t['median_growth']))


if __name__ == '__main__':
    main()
