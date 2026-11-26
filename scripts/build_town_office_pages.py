#!/usr/bin/env python3
"""ONE PAGE PER TOWN OFFICE, at the close: /town-lines/<slug>, account by account.

    python3 scripts/build_town_office_pages.py           # write fy28/public/data/town-funds/<slug>.json
    python3 scripts/build_town_office_pages.py --check   # fail if any would change

TJ, 26 November 2026, on the FY2026 town year end: "do we have a per-department breakdown
possible?" and, of the two ways to cut it, "i think per office". The rule it serves: every fund
and every account gets its own page (building-a-page skill). Parks and Recreation (650) was the
first town line with one (build_parks_ledger.py); this script writes the rest, in the same shape,
drawn by the same renderer (pages/TownFund.tsx). Rule 7d: one renderer, many payloads.

WHAT AN OFFICE IS. sources/data/departments.csv, our register, groups the town's department
codes into the office that runs them: the Town Manager's ten codes (insurance among them), the
DPW's eight. A code the register does not place is NOT guessed into an office here: it gets a
page of its own, named as MUNIS names it, until the register says otherwise. Grouping is a
claim about who runs a line, and the register is where that claim is written down and
reviewed. Parks (650) is not rewritten; the existing page is linked.

THE LEDGER. build_fy2026_town_closeout.ledger(): fund 0100 at period 13, FY2025 and FY2026,
already tied to the report's printed grand totals there. Every non-school code with money lands
on exactly one page, and the pages' FY2026 left adds back to the town total; the build refuses
otherwise.

THE TWO YEARS ARE NOT ON ONE FOOTING: FY2025's report prints no orders still owed at its close,
FY2026's counts them as spent. Each page says so beside the years.
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
import build_fy2026_town_closeout as TC  # noqa: E402
import topics as REG  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT = os.path.join(PUB, 'town-funds')
DEPTS = os.path.join(ROOT, 'sources', 'data', 'departments.csv')
K = TC.K
PARKS = ('650', 'parks-recreation-650')       # build_parks_ledger.py owns this page
LABEL = dict(original='Voted', transfers='Transfers', revised='Budget', expended='Spent',
             encumbered='Owed at the close', available='Left')
MEANS = dict(original='what Town Meeting voted', transfers='moved in or out during the year',
             revised='voted plus transfers', expended='paid by the close',
             encumbered='ordered and not yet paid', available='budget less spent and owed')
YEARS = (2025, 2026)


def fail(msg):
    raise SystemExit('build_town_office_pages: ' + msg)


def usd2(x):
    x = float(x)
    return ('-$' if x < -0.004 else '$') + format(abs(x), ',.2f')


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower().replace('&', 'and').replace("'", '')).strip('-')


def offices(live, nm):
    """[{slug, name, codes, head, board, kind, registered}] covering every live code once."""
    out, seen = [], set()
    for r in csv.DictReader(open(DEPTS, encoding='utf-8')):
        codes = [c for c in r['dept_codes'].split(';') if c in live]
        if not codes:
            continue
        out.append(dict(slug='%s-%s' % (r['slug'], min(codes)), name=r['name'], codes=sorted(codes),
                        head=r['head'], board=r['board'], kind=r['kind'], registered=True))
        seen.update(codes)
    for c in sorted(set(live) - seen):
        if c == PARKS[0]:
            continue
        name = TC.title(nm[c])
        out.append(dict(slug='%s-%s' % (slugify(name), c), name=name, codes=[c], head='',
                        board='', kind='department', registered=False))
    every = [c for o in out for c in o['codes']] + [PARKS[0]]
    if sorted(every) != sorted(live) or len(every) != len(set(every)):
        fail('the offices do not cover every live code exactly once')
    return out


def build():
    L = TC.ledger()
    nm = TC.names()
    town = {fy: [r for r in rs if r['dept'] not in TC.SCHOOL] for fy, rs in L.items()}
    live = {r['dept'] for fy in YEARS for r in town[fy] if r['revised'] or r['expended']}
    for c in live:
        if c not in nm:
            rs = {r['name'] for fy in YEARS for r in town[fy] if r['dept'] == c
                  and (r['revised'] or r['expended'])}
            if len(rs) != 1:
                fail('code %s has no name and more than one account' % c)
            nm[c] = rs.pop()
    offs = offices(live, nm)
    hub = REG.path(TC.HUB)
    dep_page = REG.path('fy2026-town-departments')
    out, left26 = {}, 0.0
    for o in offs:
        rows_of = {fy: sorted((r for r in town[fy] if r['dept'] in o['codes']),
                              key=lambda r: (r['dept'], r['object'])) for fy in YEARS}
        acc, stats = {}, {}
        for fy in YEARS:
            rows = []
            for r in rows_of[fy]:
                zero = all(abs(r[c]) < 0.005 for c in K)
                rows.append(dict(key=r['account'], name=TC.title(r['name']), side='out', zero=zero,
                                 code=('%s %s · %s' % (TC.title(nm[r['dept']]), r['dept'], r['object'])
                                       if len(o['codes']) > 1 else r['object']),
                                 t={c: usd2(r[c]) for c in K}))
            t = {c: round(sum(r[c] for r in rows_of[fy]), 2) for c in K}
            acc[C.fy(fy)] = dict(rows=rows, total=dict(name=o['name'], t={c: usd2(t[c]) for c in K}))
            stats[C.fy(fy)] = [dict(value=usd2(t['original']), label='voted by Town Meeting'),
                               dict(value=usd2(t['revised']), label='budget after transfers'),
                               dict(value=usd2(t['expended'] + t['encumbered']),
                                    label='spent, counting what was owed'),
                               dict(value=usd2(t['available']), label='left at the close')]
            if fy == 2026:
                left26 += t['available']
        across = None
        if len(o['codes']) > 1:
            def spent(fy, c):
                return sum(r['expended'] + r['encumbered'] for r in town[fy] if r['dept'] == c)
            across = dict(label='Each department code, both years', columns=[C.fy(y) for y in YEARS],
                          rows=[dict(name='%s (%s)' % (TC.title(nm[c]), c), side='out',
                                     cells=[usd2(spent(fy, c)) for fy in YEARS]) for c in o['codes']],
                          note='Spent, counting what was still owed. FY2025’s report prints no '
                               'orders still owed at its close, so the two years are not on one '
                               'footing.')
        codes = ', '.join(o['codes'])
        kicker = ('General fund · %s %s · %s'
                  % ('codes' if len(o['codes']) > 1 else 'department', codes,
                     'an assessment the town pays' if o['kind'] == 'external'
                     else 'voted by Town Meeting'))
        owner = (dict(name=o['head'] or o['name'],
                      href='/boards/%s' % o['board'] if o['board'] else hub))
        read = [dict(h='One row is one account',
                     p='Salaries and expenses as the Town numbers them. Voted plus transfers is the '
                       'budget; the budget less what was spent and what was still owed is what was '
                       'left.'),
                dict(h='The two years are counted differently',
                     p='FY2026’s report counts orders still owed at the close as spent. FY2025’s '
                       'prints none, so a difference between the years is partly a difference in '
                       'counting.'),
                dict(h='A budget line is the town’s share',
                     p='Grants, fees and revolving funds that also pay for this office are not in '
                       'the general fund, and are not on this page.')]
        if len(o['codes']) > 1:
            read.insert(1, dict(h='What makes this one office',
                                p='Our department register groups these codes under one office. '
                                  'MUNIS keeps them as separate departments.'))
        elif not o['registered']:
            read.insert(1, dict(h='Why this code stands alone',
                                p='Our department register does not yet place this code under an '
                                  'office, so it has a page of its own rather than a guessed home.'))
        out[o['slug']] = dict(
            slug=o['slug'], path='/town-lines/' + o['slug'], code=codes, name=o['name'],
            kicker=kicker, owner=owner,
            about=(('What the town budgeted for %s, an assessment it pays from the general fund, '
                    'and how it closed, account by account.' % o['name'])
                   if o['kind'] == 'external' else
                   ('What Town Meeting voted %s from the general fund, mostly taxes, and how it '
                    'closed, account by account.'
                    % (o['name'] if o['name'].startswith('The ') else 'the ' + o['name']))),
            years=[C.fy(y) for y in YEARS], spans={C.fy(y): TC_span(y) for y in YEARS},
            as_of='The Town’s general fund budget report at the close (period 13), unaudited.',
            stats=stats,
            accounts=dict(columns=[dict(id=c, label=LABEL[c], means=MEANS[c]) for c in K],
                          years=acc),
            across=across,
            postings=None,
            postings_none='The report at the close prints each account’s totals, not the payments '
                          'behind them, so this page stops at the account.',
            gaps=[dict(label='Which payments make up these accounts',
                       href='/what-we-cannot-answer')],
            read=read,
            related=[dict(label='FY2026 town year end', href=hub),
                     dict(label='Departments at close', href=dep_page),
                     dict(label='Town departments', href=REG.path('department-budgets'))],
            sources=[dict(label='Lunenburg Budget Project — munis-gf-p13-reading.csv (the general '
                                'fund at the close, FY2025 and FY2026, our reading)',
                          href='/docs/data/munis-gf-p13-reading.csv'),
                     dict(label='Lunenburg Budget Project — departments.csv (which codes each '
                                'office runs, our register)',
                          href='/docs/data/departments.csv')],
            generated_by='scripts/build_town_office_pages.py')
    parks = sum(r['available'] for r in town[2026] if r['dept'] == PARKS[0])
    total = sum(r['available'] for r in town[2026])
    if not TC.near(left26 + parks, total):
        fail('the office pages’ FY2026 left (%.2f) plus Parks does not add to the town’s (%.2f)'
             % (left26, total))
    for p in ('departments.csv', 'munis-gf-p13-reading.csv'):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', p)):
            fail('/docs/data/%s is not published' % p)
    return out


def TC_span(fy):
    return '1 July %d to 30 June %d' % (fy - 1, fy)


def page_of():
    """{department code: its page's address}, for the pages that link to them."""
    out = {PARKS[0]: '/town-lines/' + PARKS[1]}
    for slug, p in build().items():
        for c in p['code'].split(', '):
            out[c] = p['path']
    return out


def outputs():
    return {os.path.join(OUT, '%s.json' % s): json.dumps(p, indent=1, ensure_ascii=False,
                                                          sort_keys=True) + '\n'
            for s, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('town office pages: %d outputs current' % len(outs))
        return 0
    for p, t in outs.items():
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(t)
    print('wrote %d office pages to %s' % (len(outs), os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
