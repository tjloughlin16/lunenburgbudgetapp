#!/usr/bin/env python3
"""ONE PAGE PER TOWN FUND, /town-funds/<slug> (pages/TownFund.tsx): the Town's side of the money
the schools generate. The school funds have their pages (/school-funds/<slug>, fy_items.py); this
is the same mechanism for a fund the TOWN holds.

    python3 scripts/build_town_funds.py           # write the files
    python3 scripts/build_town_funds.py --check   # fail if any would change

TJ, 29 October 2026: *"I think we probably need a fund page slug for the town general fund. So
you'll have to create that mechanism. And it should work the same as the schools."*

ONE FUND SO FAR: the Town general fund (0100), and on it only what the schools bring in --
school_receipts.py, read once and shared with the preschool report and the FY breakdown. A Town
fund is added by adding an entry to FUNDS with the reader that fills it; the page, the route, the
sitemap (build_sitemap.py town_fund_pages) and the browser-only list read the index.

    /data/town-funds/index.json      every fund: slug, name, what; the page's strings
    /data/town-funds/<slug>.json     one fund: its accounts, and each year's figures
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
import school_receipts as SR  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'town-funds')
BASE = '/town-funds/'


def usd2(v):
    """Dollars and cents, as the Town's reports print a receipt."""
    v = float(v)
    return ('-$%s' if v < 0 else '$%s') % format(abs(v), ',.2f')


def general_fund():
    S = SR.series()
    accounts = [dict(id=a['id'], account=a['account'], name=a['name'], what=a['what'],
                     printed=' · '.join(dict.fromkeys(a['printed'])))
                for a in SR.ACCOUNTS]
    years = []
    for fy in SR.YEARS_SHOWN:
        rows = []
        for a in SR.ACCOUNTS:
            e = S[fy].get(a['account'])
            rows.append(dict(id=a['id'], received=float(e['received']) if e else None,
                             estimate=float(e['estimate']) if e and e['estimate'] is not None else None,
                             t=dict(received=usd2(e['received']) if e else '',
                                    estimate=usd2(e['estimate']) if e and e['estimate'] is not None else ''),
                             src=e['src'] if e else '', href=e['doc'] if e else '',
                             check=e['check'] if e else ''))
        tog = S[fy].get('together')
        held = [r for r in rows if r['received'] is not None]
        years.append(dict(
            fy=C.fy(fy), rows=rows,
            together=dict(received=float(tog['received']) if tog and tog['received'] is not None else None,
                          estimate=float(tog['estimate']) if tog and tog['estimate'] is not None else None,
                          t=dict(received=usd2(tog['received']) if tog and tog['received'] is not None else '',
                                 estimate=usd2(tog['estimate']) if tog and tog['estimate'] is not None else ''),
                          src=tog['src'], href=tog['doc']) if tog else None,
            total=dict(v=sum(r['received'] for r in held), t=usd2(sum(r['received'] for r in held)))
            if len(held) == len(rows) else None,
            why=SR.WHY_MISSING.get(fy, '')))
    return dict(slug='general-fund', name='Town general fund', fund='0100',
                what='What the schools bring in that the Town books as its own general fund receipt: '
                     'preschool tuition, student parking fees and a school medical reimbursement. '
                     'None of it is booked to a school fund.',
                accounts=accounts, years=years,
                links=[dict(label='Preschool', href='/school-all-funds/preschool'),
                       dict(label='FY breakdown', href='/school-all-funds/fy-breakdown')],
                sources=[dict(label='Town of Lunenburg — annual town reports, receipts schedules, FY2011–FY2022',
                              href='/data/annual-report-receipts.csv'),
                         dict(label='Town of Lunenburg — MUNIS revenue report, FY2020 year end', href=SR.DOCS['q4']),
                         dict(label='Town of Lunenburg — MUNIS local receipts report, FY2025', href=SR.DOCS['fy25']),
                         dict(label='Town Manager — FY2026 budget presentation (FY2024 receipts, three together)',
                              href=SR.DOCS['pres26']),
                         dict(label='Town Manager — FY2027 budget presentation (FY2026 estimate, three together)',
                              href=SR.DOCS['pres27'])])


FUNDS = [general_fund]

TEXT = dict(
    k_fund='Town fund', received='Received', estimate='Town’s estimate', account='Account',
    printed='Printed as', source='Source', check='How it was read', together='The three together',
    total='All three', none='Not held', year='Fiscal year', history_h='Every year held',
    history_note='Each bar is what the Town received; a tick is what it estimated, where a record prints it. '
                 'A blank year is one no record we hold prints.',
    year_h='The year', sources='Sources', parent='FY breakdown', parent_href='/school-all-funds/fy-breakdown',
    not_found='No such Town fund', see='Read with',
    not_school='These are Town receipts: no account in the school journal, in any fund, is named for any of them.')


def render():
    files = {}
    funds = [f() for f in FUNDS]
    for f in funds:
        files[f['slug'] + '.json'] = f
    files['index.json'] = dict(funds=[dict(slug=f['slug'], name=f['name'], what=f['what'])
                                      for f in funds], base=BASE, text=TEXT)
    return {k: json.dumps(v, ensure_ascii=False, sort_keys=True, indent=1) + '\n' for k, v in files.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    files = render()
    os.makedirs(OUT_DIR, exist_ok=True)
    stale = [k for k, v in files.items() if not os.path.exists(os.path.join(OUT_DIR, k))
             or open(os.path.join(OUT_DIR, k), encoding='utf-8').read() != v]
    extra = [k for k in os.listdir(OUT_DIR) if k.endswith('.json') and k not in files]
    if a.check:
        for k in stale + extra:
            print('STALE fy28/public/data/town-funds/%s' % k, file=sys.stderr)
        if stale or extra:
            return 1
        print('town funds: current')
        return 0
    for k in stale:
        p = os.path.join(OUT_DIR, k)
        with open(p + '.tmp', 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(files[k])
        os.replace(p + '.tmp', p)
    for k in extra:
        os.remove(os.path.join(OUT_DIR, k))
    print('town funds: wrote %d, removed %d' % (len(stale), len(extra)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
