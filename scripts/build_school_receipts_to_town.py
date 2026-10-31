#!/usr/bin/env python3
"""SCHOOL RECEIPTS TO THE TOWN: what the schools bring in that the Town books as its own general
fund revenue -- preschool tuition, student parking fees, a school medical reimbursement -- year by
year, received against the Town's estimate. One topic page on the whole-school shelf.

    python3 scripts/build_school_receipts_to_town.py           # write the topic payload
    python3 scripts/build_school_receipts_to_town.py --check   # fail if it would change

TJ, 31 October 2026, on /town-funds/general-fund, which held exactly this and nothing else: *"it
seems focused on the school, but its not presented that way in the url or heading ... This is
the school finances in the town fund, so we can put that in school all funds, and retitle it.
then build another page for the town fund"* -- and *"this page starts with MISSING INFORMATION
which is hard to understand"*: it opened on FY2026, the one year with nothing per account. So
this page opens on what was received, and the missing years are a note on the chart and a gap
tile, not the first thing on the page.

Every figure is school_receipts.py, shared with the preschool page and the FY breakdown so the
three cannot disagree (rule 7d). Its docstring says where each year comes from.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402
import school_receipts as SR  # noqa: E402

ID = 'school-receipts-to-town'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)


def fail(msg):
    raise SystemExit('build_school_receipts_to_town: ' + msg)


def fl(x):
    return float(x)


def usd2(v):
    """Dollars and cents, as the Town's reports print a receipt."""
    v = float(v)
    return ('-$%s' if v < 0 else '$%s') % format(abs(v), ',.2f')


def plan_matches(S):
    """[(fy, account, plan, earlier fy or None)]: every per-account estimate the Town printed, and
    the earlier year whose receipt it equals to the dollar, if any. A measurement; why the plan was
    set that way is not recorded anywhere we hold (rule 7)."""
    out = []
    for fy in SR.YEARS_SHOWN:
        for a in SR.ACCOUNTS:
            e = S[fy].get(a['account'])
            if not e or e['estimate'] is None:
                continue
            m = [y for y in SR.YEARS_SHOWN if y < fy and S[y].get(a['account'])
                 and int(S[y][a['account']]['received']) == int(e['estimate'])]
            out.append((fy, a, e['estimate'], max(m) if m else None))
    return out


def page():
    S = SR.series()
    years = list(SR.YEARS_SHOWN)
    xs = [C.fy(y) for y in years]
    A = SR.ACCOUNTS
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    N = lambda n, unit: figure(n, C.num(n), unit)
    got = lambda fy, a: S[fy].get(a['account'])
    full = [fy for fy in years if all(got(fy, a) for a in A)]
    if not full:
        fail('no year holds all three accounts')
    last, first = max(full), min(full)
    tot = {fy: sum((got(fy, a)['received'] for a in A), SR.D0) for fy in full}
    est = {fy: sum((got(fy, a)['estimate'] for a in A), SR.D0) for fy in full
           if all(got(fy, a)['estimate'] is not None for a in A)}
    if last not in est:
        fail('FY%d holds every account but not every estimate' % last)
    tog24, tog26 = S[2024].get('together'), S[2026].get('together')
    if not (tog24 and tog24['received'] is not None and tog26 and tog26['estimate'] is not None):
        fail('the FY2024 slide figure or the FY2026 estimate did not read')
    blank = [fy for fy in years if not any(got(fy, a) for a in A) and not S[fy].get('together')]
    combined = [fy for fy in years if S[fy].get('together')]
    if blank != [2023] or combined != [2024, 2026]:
        fail('the years held changed: blank %s, combined only %s -- rewrite the note' % (blank, combined))
    times = fl(tot[last]) / fl(est[last])
    M = plan_matches(S)
    hit = [m for m in M if m[3]]
    pre_hits = sorted(m[0] for m in hit if m[1]['id'] == 'preschool')
    if pre_hits != [2020, 2025] or {m[3] for m in hit if m[1]['id'] == 'preschool'} != {2019}:
        fail('the preschool plan no longer equals FY2019 tuition in FY2020 and FY2025: %s' % hit)

    # ---- the signature: what came in, every year, against what the Town planned on
    plan = {fy: fl(est[fy]) for fy in est}
    plan[2026] = fl(tog26['estimate'])
    chart = TP.series(
        'Received against the Town’s plan', xs,
        [TP.track(a['name'], [fl(got(y, a)['received']) if got(y, a) else None for y in years],
                  'published', 'bar') for a in A]
        + [TP.track('All three, one slide figure',
                    [fl(tog24['received']) if y == 2024 else None for y in years], 'published', 'bar'),
           TP.track('What the Town planned on', [plan.get(y) for y in years], 'published', 'line')],
        '$', kind='bar', stacked=True,
        note='The plan is printed only for %s, %s and %s. No receipts are held for %s.'
             % (C.fy(2020), C.fy(2025), C.fy(2026), C.fy(2023)),
        note_figures={'a': F(2020), 'b': F(2025), 'c': F(2026), 'd': F(2023)})

    # ---- who pays each, and where it lands
    cards = []
    for a in A:
        e = got(last, a)
        cards.append(TB.panel(a['name'], [('Received', usd2(e['received']), 'good'),
                                          ('Planned by the Town', usd2(e['estimate']), None)],
                              sub=a['what']))
    panels = TB.panels('Three receipts, one destination', cards, note=(
        '%s, the Town’s MUNIS local receipts report. All three are Town general fund revenue, '
        'department 31, “Dept Rev - School”.' % C.fy(last), None, (C.fy(last), '31')),
        so='None of the three is credited to a school fund or a school budget line; each is Town revenue.')

    # ---- where the plan comes from: each printed plan against the earlier receipt it equals
    cols = sorted({m[3] for m in hit})
    rows = [TB.check_row(('%s, %s plan' % (m[1]['name'], C.fy(m[0])), None, (C.fy(m[0]),)),
                         ('Planned at %s.' % usd2(m[2]) + (' Equals %s’s receipt to the dollar.' % C.fy(m[3])
                                                          if m[3] else ' Equals no earlier receipt held.'),
                          None, (usd2(m[2]),) + tuple(C.fy(y) for y in cols)),
                         {cols.index(m[3])} if m[3] else set(), contrast=not m[3])
            for m in M]
    checks = TB.checks('Where the Town’s plan comes from', [('Equals the %s receipt' % C.fy(y), None, (C.fy(y),)) for y in cols], rows, first='The plan printed', second='Measured',
                       tone='good', note=('Each per-account plan the Town printed, against every earlier receipt '
                                          'held. %s of %s match a receipt to the dollar.'
                                          % (len(hit), len(M)), None, (str(len(hit)), str(len(M)))),
                       so=('Preschool tuition was planned at the %s figure in both %s and %s; nothing '
                           'we hold says how the plan is set.' % (C.fy(2019), C.fy(2020), C.fy(2025)),
                           None, (C.fy(2019), C.fy(2020), C.fy(2025))))

    # ---- which record holds each year: the gaps, drawn, not opened on
    def state(fy, a):
        e = got(fy, a)
        if e:
            return 'munis' if 'MUNIS' in e['src'] else 'annual'
        tg = S[fy].get('together')
        if tg:
            return 'slide' if tg['received'] is not None else 'plan'
        return None
    timeline = TB.timeline('Which record holds each year', ['FY' + str(y)[2:] for y in years],
                           [('By account', [TB.track(a['name'], [state(y, a) for y in years]) for a in A])],
                           [('annual', 'Annual town report', 'good'), ('munis', 'Town MUNIS report', 'good'),
                            ('slide', 'All three as one, on a slide', 'neutral'),
                            ('plan', 'Only the plan, all three as one', 'muted')],
                           note=(' '.join(SR.WHY_MISSING[y] for y in sorted(SR.WHY_MISSING)), None,
                                 tuple(re.findall(r'\d[\d,.]*', ' '.join(SR.WHY_MISSING.values())))))

    f = LD.fact
    facts = [
        f('tot', U(tot[last]), 'all three received by the Town, %s' % C.fy(last), 'published',
          label_figures={'y': F(last)}),
        f('est', U(est[last]), 'what the Town planned on, %s' % C.fy(last), 'published',
          label_figures={'y': F(last)}),
        f('times', figure(times, '%.1f' % times, 'times'), 'received, as a multiple of the plan', 'published'),
        f('match', figure(len(hit), '%d of %d' % (len(hit), len(M)), 'plans'),
          'printed plans equal to an earlier year’s receipt', 'published'),
        f('first', U(tot[first]), 'all three received, %s' % C.fy(first), 'published',
          label_figures={'y': F(first)}),
        f('gap23', None, 'received in %s' % C.fy(2023), 'gap', label_figures={'y': F(2023)},
          closes='A legible copy of the FY2023 annual town report’s receipts schedule'),
    ]
    con = TP.conclusion
    conclusions = [
        con('The schools brought in %s in %s, booked as Town general fund revenue.'
            % (C.usd(fl(tot[last])), C.fy(last)), ['tot'], {'a': U(tot[last]), 'y': F(last)},
            so='The school budget is set without it; none of it reaches a school account.'),
        con('The Town planned on %s and received %s times that.' % (C.usd(fl(est[last])), '%.1f' % times),
            ['est', 'times'], {'a': U(est[last]), 'b': figure(times, '%.1f' % times, 'times')},
            so='Receipts above plan are part of what the state counts when it certifies free cash.'),
        con('%s of the %s plans the Town printed equal an earlier year’s receipt to the dollar.'
            % (len(hit), len(M)), ['match'], {'a': N(len(hit), 'plans'), 'b': N(len(M), 'plans')},
            so='The plan reads as a figure carried forward, not a forecast; nothing written says so.'),
    ]

    rows_t = []
    for fy in reversed(years):
        tg = S[fy].get('together')
        cell = lambda a: usd2(got(fy, a)['received']) if got(fy, a) else '—'
        all3 = usd2(tot[fy]) if fy in tot else (usd2(tg['received']) if tg and tg['received'] is not None else '—')
        pl = usd2(est[fy]) if fy in est else (usd2(tg['estimate']) if tg and tg['estimate'] is not None else '—')
        rows_t.append(dict(label=C.fy(fy), cells=[cell(a) for a in A] + [all3, pl]))
    table = dict(caption='Every year, account by account', views=[dict(
        key='years', label='Received, by account', total_col=3, kinds=['ledger'] * 5,
        columns=[a['name'] for a in A] + ['All three', 'Town’s plan'], rows=rows_t,
        note='General fund 0100, accounts 431900, 437400 and 473000.')])

    sources = [
        dict(key='annual', label='Town of Lunenburg — annual town reports, receipts schedules, FY2011–FY2022',
             href='/docs/data/annual-report-receipts.csv'),
        dict(key='q4', label='Town of Lunenburg — MUNIS revenue report, FY2020 year end', href=SR.DOCS['q4']),
        dict(key='fy25', label='Town of Lunenburg — MUNIS local receipts report, FY2025', href=SR.DOCS['fy25']),
        dict(key='pres26', label='Town Manager — FY2026 budget presentation (FY2024 receipts, three together)',
             href=SR.DOCS['pres26']),
        dict(key='pres27', label='Town Manager — FY2027 budget presentation (FY2026 plan, three together)',
             href=SR.DOCS['pres27']),
    ]
    every = ('annual', 'q4', 'fy25', 'pres26', 'pres27')
    cite = TP.cite
    return TP.page(
        ID,
        'The schools brought in %s in %s that the Town books as general fund revenue, %s times its plan.'
        % (C.usd(fl(tot[last])), C.fy(last), '%.1f' % times),
        facts, conclusions, chart=chart, table=table, sources=sources,
        finding_figures={'a': U(tot[last]), 'y': F(last), 'b': figure(times, '%.1f' % times, 'times')},
        flow=['finding', cite(('chart', 0), *every), cite(panels, 'fy25'), cite(checks, 'q4', 'fy25', 'annual'),
              cite('ladder', *every), cite(timeline, *every), 'related', cite(('table', 0), *every), 'sources'],
        draft=None if ID in REG.TOPICS else dict(title='School receipts to the Town', home='school-all-funds'))


def render():
    return json.dumps(page(), ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('school receipts to the Town: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
