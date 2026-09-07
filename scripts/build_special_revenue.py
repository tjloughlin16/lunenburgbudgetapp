#!/usr/bin/env python3
"""The special-revenue page's series, pre-rendered from the database.

    python3 scripts/build_special_revenue.py            # write it
    python3 scripts/build_special_revenue.py --check    # fail if it is stale

WHAT THIS IS. `special_revenue_read` is the Special Revenue Funds schedule out of thirteen
consecutive annual town reports, FY2011-FY2023 -- balance brought forward, total receipts,
total disbursements, balance carried forward, one row per fund. It was read off the
rendered page rather than OCR'd, and it is trustworthy for two reasons neither of which is
that a model produced it: every year ties to its own printed GRAND TOTAL on all four
columns, and every row satisfies `forward + receipts - disbursements = carried`. See
`sources/data/PROVENANCE-special-revenue-read.md`.

WHY A FILE AND NOT A QUERY. Same reason as `build_variance_charts.py`: D1's free tier
stops at 5 million rows read a day, `special_revenue_read` is 1,882 rows, and a few
hundred page loads of a scan would take the endpoint dark until tomorrow. Nothing here
changes between database rebuilds, so it is computed once and served static.

WHAT THIS RECONCILES TO. Every year's four columns are summed from the fund rows and
compared to `special_revenue_printed_totals` -- the GRAND TOTAL the town printed. The
script REFUSES TO WRITE if a single year disagrees by more than a cent, if the join
matches nothing, or if any row's identity fails. A join that matches nothing looks exactly
like data that is absent.

RULE 7. Everything computed here is a measurement: dollars in, dollars out, dollars held.
None of it establishes WHY a fund moved. The classification below is the one place this
file makes a judgement, and it is a judgement about NAMES, not about funds -- so the funds
that went into each band are published with the band, and the page says whose reading it
is.

RULE 11 POINTED THE OTHER WAY. This is the money OUTSIDE the appropriation. A budget line
that rose because a grant ended and one that rose because the thing got dearer are
identical on the expense page; this schedule is where the other side is visible at all.
What it still does not do is map a fund to a budget line -- nothing published does.

RULE 13. `group` is transcribed as the report prints it, and the report prints two spellings
of one department (`HIGHWAY DEPT.` in the early editions, `HIGHWAY DEPARTMENT` later).
Merging them is OUR rendering, so it is done in one named place, counted, and reported.
"""
import argparse
import collections
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/special-revenue.json')

# Two printed spellings of one department. Merging is our rendering of the town's page,
# so it lives here rather than being done inline three times.
GROUP_ALIASES = {'HIGHWAY DEPT.': 'HIGHWAY DEPARTMENT'}

# ---------------------------------------------------------------- the bands
#
# NAMED FUNDS, NOT A PATTERN. The first version of this matched on a regular expression
# and swept in `Citizens Relief Fund` -- a $200 fund that has sat in the schedule since
# FY2011 and has nothing to do with the pandemic -- because the pattern held `Relief
# Fund`. A list of names can be checked by a reader against the page; a regex cannot.
#
# These are the names as the reports print them. A name that stops appearing is not a fund
# that closed: see the chain exception, and the fund-name counts this file publishes.
ENTERPRISE = [
    'PEG Access Enterprise Fund',
    'Sewer Betterment Fund',
    'Sewer Enterprise Fund',
    'Solid Waste/Recycling Enterprise Fund',
    'Water Enterprise Fund',
]
PANDEMIC = [
    'ARPA Funds',
    'Cares Act Funding - COVID',
    'Covid Prevention Grant',
    'FEMA #4496 - COVID Grant',
    'FY21 ESSER #113',
    'FY22 #437 Covid 19 Summer Programming',
    'FY22 ESSER II #115',
    'FY22 ESSER III #119',
    'HHS Provider Relief Fund',
    'Remote Learning Tech #117/118',
]
SCHOOL_GROUP = 'SCHOOL DEPARTMENT'

# Assignment is by PRECEDENCE and every fund-year lands in exactly one band. Enterprise
# first because those five are the reason "special revenue" here is not school money;
# pandemic second because ESSER is a school fund and belongs with ARPA rather than with
# the school lunch account; the printed group last.
BANDS = [
    ('enterprise', 'Enterprise funds'),
    ('pandemic', 'Pandemic-era funds'),
    ('school', 'School department'),
    ('other', 'Everything else the town runs'),
]

# The chain break the town made and the provenance file records: between FY2022 and FY2023
# the grant funds were re-cut by year, and FY2023's brought-forward column does not equal
# FY2022's carried. Pinned to the cent so a silent drift is not read as this.
KNOWN_CHAIN_BREAK = {2023: 17861.24}

CENT = 0.005


def band_of(group, fund):
    if fund in ENTERPRISE:
        return 'enterprise'
    if fund in PANDEMIC:
        return 'pandemic'
    if group == SCHOOL_GROUP:
        return 'school'
    return 'other'


def rows_and_totals():
    """The fund rows and the town's own printed GRAND TOTALs, from the read model.

    Both are asserted non-empty. `special_revenue_read` is a derived table rebuilt by
    build_db.py from the CSV, and a rebuild that dropped it would otherwise produce a page
    of zeroes that looks exactly like a town that raised nothing.
    """
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        'SELECT fy, edition, page, "group", fund, forward, receipts, disbursements, '
        'carried, row_ties, document, read_by FROM special_revenue_read ORDER BY fy, page')]
    tot = {int(r['fy']): dict(r) for r in con.execute(
        'SELECT fy, edition, page, forward, receipts, disbursements, carried, quote '
        'FROM special_revenue_printed_totals')}
    con.close()
    if not rows:
        raise SystemExit('special_revenue_read is empty — nothing to publish. '
                         'Run scripts/build_db.py.')
    if not tot:
        raise SystemExit('special_revenue_printed_totals is empty — there is nothing to '
                         'reconcile the fund rows against, and an unreconciled reading is '
                         'not publishable. Run scripts/build_db.py.')
    return rows, tot


def num(v):
    return float(v) if v not in (None, '') else 0.0


COLS = ('forward', 'receipts', 'disbursements', 'carried')


def build():
    raw, printed = rows_and_totals()
    rows = []
    merged_groups = 0
    for r in raw:
        g = r['group']
        if g in GROUP_ALIASES:
            merged_groups += 1
            g = GROUP_ALIASES[g]
        rows.append(dict(
            fy=int(r['fy']), edition=r['edition'], page=r['page'], group=g,
            printed_group=r['group'], fund=r['fund'],
            band=band_of(g, r['fund']), document=r['document'], read_by=r['read_by'],
            **{c: round(num(r[c]), 2) for c in COLS}))

    years = sorted({r['fy'] for r in rows})

    # ------------------------------------------------ the two checks, recomputed here
    #
    # Not trusted from the provenance note. Rule 13: a summary in a document is a claim
    # about the data, not the data.
    bad_rows = [r for r in rows
                if abs(r['forward'] + r['receipts'] - r['disbursements'] - r['carried']) > CENT]
    if bad_rows:
        raise SystemExit(
            f'{len(bad_rows)} row(s) fail forward + receipts − disbursements = carried, '
            f'first: FY{bad_rows[0]["fy"]} {bad_rows[0]["fund"]!r}. The dataset\'s whole '
            'claim is that this holds; nothing is published while it does not.')

    reconciliation, missing = [], []
    for y in years:
        p = printed.get(y)
        if not p:
            missing.append(y)
            continue
        ours = {c: round(sum(r[c] for r in rows if r['fy'] == y), 2) for c in COLS}
        theirs = {c: round(num(p[c]), 2) for c in COLS}
        off = {c: round(ours[c] - theirs[c], 2) for c in COLS}
        if any(abs(v) > CENT for v in off.values()):
            raise SystemExit(
                f'FY{y} does not tie to its own printed GRAND TOTAL: {off}. '
                f'Source: {p["quote"]}.')
        reconciliation.append(dict(
            fy=y, edition=p['edition'], page=p['page'], quote=p['quote'],
            funds=sum(1 for r in rows if r['fy'] == y),
            printed=theirs, summed=ours, ties=True))
    if missing:
        raise SystemExit(
            f'no printed GRAND TOTAL held for FY{", FY".join(map(str, missing))} — the '
            'reconciliation that makes this dataset worth publishing cannot be run.')
    if len(reconciliation) != len(years):
        raise SystemExit('the reconciliation join matched fewer years than the data holds')

    # ------------------------------------------------ the year-to-year chain
    chain = []
    for i, y in enumerate(years):
        fwd = round(sum(r['forward'] for r in rows if r['fy'] == y), 2)
        prev = (round(sum(r['carried'] for r in rows if r['fy'] == years[i - 1]), 2)
                if i else None)
        gap = None if prev is None else round(fwd - prev, 2)
        expected = KNOWN_CHAIN_BREAK.get(y)
        if gap is not None and abs(gap) > CENT:
            if expected is None or abs(gap - expected) > CENT:
                raise SystemExit(
                    f'FY{y} brought forward {fwd:,.2f} does not equal FY{years[i-1]} '
                    f'carried {prev:,.2f} — a break of {gap:,.2f} that is not the one '
                    'recorded in the provenance file.')
        chain.append(dict(fy=y, forward=fwd, prior_carried=prev, gap=gap,
                          known_break=expected is not None))

    # ------------------------------------------------ the series
    def totals(subset):
        return {c: round(sum(r[c] for r in subset), 2) for c in COLS}

    by_year = []
    for y in years:
        s = [r for r in rows if r['fy'] == y]
        t = totals(s)
        by_year.append(dict(fy=y, funds=len(s), net=round(t['receipts'] - t['disbursements'], 2), **t))

    band_series = []
    for y in years:
        row = dict(fy=y)
        for key, _ in BANDS:
            s = [r for r in rows if r['fy'] == y and r['band'] == key]
            row[key] = round(sum(r['carried'] for r in s), 2)
            row[key + '_receipts'] = round(sum(r['receipts'] for r in s), 2)
            row[key + '_disbursements'] = round(sum(r['disbursements'] for r in s), 2)
            row[key + '_funds'] = len(s)
        row['total'] = round(sum(row[k] for k, _ in BANDS), 2)
        band_series.append(row)

    # Everything the schools held, pandemic grants included -- the band chart splits them
    # and a reader will reasonably want the sum.
    school_all = []
    for y in years:
        s = [r for r in rows if r['fy'] == y and r['group'] == SCHOOL_GROUP]
        t = totals(s)
        school_all.append(dict(fy=y, funds=len(s),
                               net=round(t['receipts'] - t['disbursements'], 2), **t))

    groups = sorted({r['group'] for r in rows})
    by_group = []
    for g in groups:
        series = []
        for y in years:
            s = [r for r in rows if r['fy'] == y and r['group'] == g]
            t = totals(s)
            series.append(dict(fy=y, funds=len(s),
                               net=round(t['receipts'] - t['disbursements'], 2), **t))
        by_group.append(dict(group=g, series=series,
                             first=series[0], last=series[-1],
                             receipts_total=round(sum(x['receipts'] for x in series), 2),
                             disbursements_total=round(sum(x['disbursements'] for x in series), 2)))
    by_group.sort(key=lambda r: -r['last']['carried'])

    # ------------------------------------------------ fund-name stability, counted
    seen = collections.defaultdict(set)
    for r in rows:
        seen[r['fund']].add(r['fy'])
    all_years = sorted(k for k, v in seen.items() if len(v) == len(years))
    one_year = [k for k, v in seen.items() if len(v) == 1]
    span_hist = collections.Counter(len(v) for v in seen.values())

    # ------------------------------------------------ movers, on funds printed in both
    first_fy, last_fy = years[0], years[-1]
    a = {r['fund']: r for r in rows if r['fy'] == first_fy}
    b = {r['fund']: r for r in rows if r['fy'] == last_fy}
    both = sorted(set(a) & set(b))
    moves = sorted(
        (dict(fund=k, group=b[k]['group'], band=b[k]['band'],
              first=a[k]['carried'], last=b[k]['carried'],
              change=round(b[k]['carried'] - a[k]['carried'], 2))
         for k in both),
        key=lambda r: -r['change'])

    # ------------------------------------------------ what routinely runs a deficit
    #
    # Only funds printed in EVERY year: a fund present twice can look like it always
    # overspends on a sample of two.
    persistent = []
    for k in all_years:
        s = sorted((r for r in rows if r['fund'] == k), key=lambda r: r['fy'])
        rc = round(sum(r['receipts'] for r in s), 2)
        di = round(sum(r['disbursements'] for r in s), 2)
        drawn = sum(1 for r in s if r['disbursements'] > r['receipts'])
        persistent.append(dict(
            fund=k, group=s[-1]['group'], band=s[-1]['band'],
            receipts=rc, disbursements=di, net=round(rc - di, 2),
            years_drawn_down=drawn, years=len(s),
            first_carried=s[0]['carried'], last_carried=s[-1]['carried']))
    persistent.sort(key=lambda r: -r['receipts'])

    latest = sorted((r for r in rows if r['fy'] == last_fy),
                    key=lambda r: -r['carried'])

    docs = sorted({r['document'] for r in rows})
    readers = sorted({r['read_by'] for r in rows})

    return dict(
        generated_by='scripts/build_special_revenue.py',
        source='sources/data/special-revenue-read.csv',
        provenance='sources/data/PROVENANCE-special-revenue-read.md',
        tables=['special_revenue_read', 'special_revenue_printed_totals'],
        documents=docs,
        read_by=readers,
        coverage=dict(
            first_fy=first_fy, last_fy=last_fy, years=years, editions=len(years),
            fund_years=len(rows), fund_names=len(seen),
            names_every_year=len(all_years), names_one_year_only=len(one_year),
            groups=len(groups), merged_group_rows=merged_groups,
            printed_group_spellings=len({r['printed_group'] for r in rows}),
            span_histogram=[dict(years=k, funds=span_hist[k]) for k in sorted(span_hist)],
        ),
        reconciliation=reconciliation,
        chain=chain,
        chain_break=[dict(fy=k, amount=v)
                     for k, v in sorted(KNOWN_CHAIN_BREAK.items())],
        by_year=by_year,
        bands=[dict(id=k, label=lbl,
                    funds=(ENTERPRISE if k == 'enterprise' else
                           PANDEMIC if k == 'pandemic' else None))
               for k, lbl in BANDS],
        band_series=band_series,
        by_group=by_group,
        school=school_all,
        movers=dict(first_fy=first_fy, last_fy=last_fy, in_both=len(both),
                    risers=moves[:8], fallers=moves[-8:][::-1]),
        persistent=persistent[:24],
        latest=[dict(fund=r['fund'], group=r['group'], band=r['band'],
                     **{c: r[c] for c in COLS}) for r in latest],
        rows=[[r['fy'], r['group'], r['fund'], r['forward'], r['receipts'],
               r['disbursements'], r['carried']] for r in rows],
        row_fields=['fy', 'group', 'fund', 'forward', 'receipts', 'disbursements', 'carried'],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {os.path.relpath(OUT, ROOT)} is not what the database now '
                  f'produces. Run scripts/build_special_revenue.py.')
            return 1
        print(f'ok — {os.path.relpath(OUT, ROOT)} reproduces from the database')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    c = d['coverage']
    print(f"wrote {os.path.relpath(OUT, ROOT)} — {c['editions']} editions "
          f"FY{c['first_fy']}–FY{c['last_fy']}, {c['fund_years']} fund-years, "
          f"{c['fund_names']} distinct printed fund names, every year tied to its own "
          f"printed GRAND TOTAL on all four columns")
    return 0


if __name__ == '__main__':
    sys.exit(main())
