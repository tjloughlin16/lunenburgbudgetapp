#!/usr/bin/env python3
"""Boards and committees, split into topic pages: eight pages and the hub at /board-records.

    python3 scripts/build_board_records_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_board_records_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, facts first, one to
four conclusions resting on them. This shelf absorbs /boards/compared (what each board POSTS),
/analysis/board-composition and /analysis/open-seats (who SITS on them), and the board half of
build_tenure.py's data (how long they stay). Its id is `board-records`, not `boards`, because
/boards is the live board index and this shelf must not take over its address.

TWO INSTRUMENTS, AND EACH PAGE SAYS WHICH IT READS.

  the Agenda Center    the town's own list of agendas and minutes, per board, as of the day
                       build_board_posting.py read it. A meeting is a date with a posted
                       agenda; it has minutes if minutes are LISTED for the same board and
                       date. That is a statement about what the town's site holds on that
                       day (rule 13c) -- not about what a board wrote, held or approved, and
                       nothing here says a board broke a rule. Rule 8: this is not an audit.
  the officials listing  the ELECTED and APPOINTED OFFICIALS pages of each annual town report,
                       FY2016-FY2025: each heading, its stated size, the names printed under
                       it and their term years. A snapshot printed once a year.

NAMES. Boards are named; people never are. open-seats.md prints who holds each expiring seat;
these pages count seats and do not carry a name.

IT COMPUTES ONLY WHAT IT CANNOT READ, and says where:

  fy28/public/data/board-posting.json      minutes and recordings, by board and fiscal year.
                                           The all-board totals are summed here from its
                                           per-board rows, and asserted equal to its `totals`.
  fy28/public/data/board-composition.json  seats filled, sizes, turnover by body, churn.
  fy28/public/data/open-seats.json         seats printed empty; terms by the year they end.
  scripts/town_personnel_data.py           the listing rows behind both payloads -- read here
                                           for ONE like-for-like comparison the payload does not
                                           make: seats filled over the bodies stating a size in
                                           both FY2020 and FY2025.
  sources/data/org-chart.csv               board tenure, from the OFFICIALS LISTING ROWS ONLY.
                                           tenure.json's board units also carry chairs named in
                                           pre-FY2016 report prose and the FY2027 staff
                                           directory -- three instruments in one span -- so its
                                           board medians are not used; build_tenure.py's own
                                           identity rule and censoring are, on the clean rows.

DEFECTS FOUND IN THE SOURCES, not fixed here (this script may not edit them):
  - board-composition.json `stats` and its third conclusion state 60 distinct people hold the
    182 posts listed in FY2025. 60 is a stale loop variable in town_personnel_data.py (`who`
    is rebound by the school-roster loop); the listing holds 173 distinct names. Not used.
  - board-posting.json's first conclusion says its 1,284 of 1,934 is over the 30 ranked
    boards; it is over all 39. These pages say 39.
"""
import argparse
import collections
import csv
import datetime
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
from build_tenure import identity  # noqa: E402
import town_personnel_data as TPD  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
DOCS = os.path.join(ROOT, 'fy28', 'public', 'docs')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
ORG = os.path.join(ROOT, 'sources', 'data', 'org-chart.csv')
HUB = 'board-records'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == HUB and gen == 'build_board_records_topics.py']

# The documents a gap would be closed by. Prose, no figures; said once.
CANCELLED = 'a list of each board’s cancelled meetings; the Agenda Center does not mark one'
UNPOSTED = 'each board’s approved minutes not yet posted to the Agenda Center'
VIDEO_MAP = 'the town’s own list of which recording is of which meeting'
CURRENT = 'a current list of board vacancies from the town, dated'
DATED = 'dated appointment, oath and resignation records, by board'
RENAMES = 'the town’s record of when each board was renamed or re-formed'
CHARTERS = 'the town’s list of boards and committees, with each one’s charter size'

THE_THREE = ('school-committee', 'select-board', 'finance-committee')


def fail(msg):
    raise SystemExit('build_board_records_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def day(iso):
    d = datetime.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, d.strftime('%B'), d.year)


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = {}
    for k, key in (('ar16', 'town-annual-reports/docs/4123-fy-2016-annual-town-report.pdf'),
                   ('ar25', 'town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf')):
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='Town of Lunenburg — annual town report, officials listing — %s'
                      % key.split('/')[-1], href='/docs/' + key)
    out['agenda'] = dict(label='Town of Lunenburg — Agenda Center (agendas and minutes, by board)',
                         href='https://www.lunenburgma.gov/AgendaCenter')
    for k, f, what in (
            ('register', 'data/meeting-register.csv', 'one row per board and date, every artifact'),
            ('videos', 'data/youtube-video-boards.csv', 'each town video matched to a board and date'),
            ('personnel', 'data/town-personnel.csv', 'the officials listing, row by row'),
            ('org', 'data/org-chart.csv', 'every named person by body and year'),
            ('comp-md', 'analyses/board-composition.md', 'how the boards are made up'),
            ('seats-md', 'analyses/open-seats.md', 'seats empty and terms ending')):
        if not os.path.exists(os.path.join(DOCS, f)):
            fail('/docs/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f.split('/')[-1], what),
                      href='/docs/' + f)
    for k, f, what in (('posting', 'board-posting.json', 'minutes and recordings by board and year'),
                       ('comp', 'board-composition.json', 'seats, sizes and turnover'),
                       ('open', 'open-seats.json', 'seats printed empty, terms by year')):
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what), href='/data/' + f)
    return out


def board_tenure():
    """Board memberships from the officials listing only, measured build_tenure.py's way:
    one membership is one identity (surname and first initial) on one body; its length is the
    number of the body's own published listings it spans; one present in the body's first or
    last listing is CENSORED -- its length is a lower bound, not a length."""
    rows = [r for r in csv.DictReader(open(ORG, encoding='utf-8'))
            if r['unit_kind'] == 'board' and r['source'].startswith('officials listing')
            and r['person'].strip()]
    if not rows:
        fail('org-chart.csv holds no officials-listing board rows')
    pub, mem = collections.defaultdict(set), collections.defaultdict(set)
    for r in rows:
        pub[r['unit']].add(int(r['fy']))
        k = identity(r['person'])
        if k:
            mem[(r['unit'], k)].add(int(r['fy']))
    settled, censored = [], 0
    for (unit, _), ys in mem.items():
        p = sorted(pub[unit])
        if min(ys) == p[0] or max(ys) == p[-1]:
            censored += 1
            continue
        settled.append(sum(1 for y in p if min(ys) <= y <= max(ys)))
    years = sorted({int(r['fy']) for r in rows})
    return dict(memberships=len(mem), settled=len(settled), censored=censored,
                median=statistics.median(settled), single=sum(1 for s in settled if s == 1),
                first=years[0], last=years[-1])


def like_for_like(a, b):
    """Seats filled over the SAME bodies in two years: those stating a plain size in both.
    Headings are matched ignoring case, because the listing sets the same body in capitals
    one year and title case the next. Counted exactly as town_personnel_data.py counts `fill`."""
    d = TPD.load()
    per = collections.defaultdict(lambda: [0, 0])
    for y in (a, b):
        seen = set()
        for r in d['rows']:
            if r['fy'] != y or not r['stated_members'] or '-' in r['stated_members']:
                continue
            k = (y, r['post'].casefold())
            if k not in seen:
                seen.add(k)
                per[k][0] += int(r['stated_members'])
            if r['person'].strip():
                per[k][1] += 1
    both = sorted(p for (y, p) in per if y == a and (b, p) in per)
    return len(both), {y: (sum(per[(y, p)][0] for p in both), sum(per[(y, p)][1] for p in both))
                       for y in (a, b)}


def build():
    BP = load('board-posting.json')
    BC = load('board-composition.json')
    OS = load('open-seats.json')
    src = sources()
    S = lambda *names: [src[n] for n in names]

    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    P0 = lambda v: figure(v, C.pct(v, 0), 'percent')
    KN = lambda k, n, unit='meetings': figure(round(k / n, 4) if n else 0,
                                              '%s of %s' % (C.num(k), C.num(n)), unit)
    YR = lambda v: figure(int(v), str(int(v)), 'year')
    f, con = LD.fact, TP.conclusion
    out = {}

    # ---------------------------------------------------------------- the inputs, checked
    fys = BP['fys']
    f0, f1 = fys[0], fys[-1]
    asof = day(BP['as_of'])
    lag = BP['lag_days']
    boards = BP['boards']
    ranked = [b for b in boards if b['ranked']]
    by = {b['slug']: b for b in boards}
    for s in THE_THREE + ('library-board-of-trustees', 'zoning-board-of-appeals',
                          'board-of-registrars', 'capital-planning-committee'):
        if s not in by:
            fail('board %r is no longer in board-posting.json' % s)
    all_n = sum(b['meetings'] for b in boards)
    all_k = sum(b['with_minutes'] for b in boards)
    all_rec = sum(b['recorded'] for b in boards)
    t = BP['totals']
    if (all_n, all_k) != (t['meetings'], t['with_minutes']):
        fail('the per-board rows no longer sum to board-posting.json totals')
    if t['boards_ranked'] != len(ranked):
        fail('boards_ranked no longer counts the ranked rows')
    share = 100 * all_k / all_n
    yr = lambda b, fy: next(y for y in b['years'] if y['fy'] == fy)
    per_fy = {fy: (sum(yr(b, fy)['meetings'] for b in boards),
                   sum(yr(b, fy)['with_minutes'] for b in boards),
                   sum(yr(b, fy)['recorded'] for b in boards)) for fy in fys}
    hi90 = sum(1 for b in ranked if b['share'] >= 90)
    lo50 = sum(1 for b in ranked if b['share'] < 50)
    best = ranked[0]
    lib, zba, reg, cpc = (by['library-board-of-trustees'], by['zoning-board-of-appeals'],
                          by['board-of-registrars'], by['capital-planning-committee'])
    if best['slug'] != lib['slug']:
        fail('the Library Board of Trustees is no longer the best-posting board')
    if ranked[-1]['slug'] != reg['slug']:
        fail('the Board of Registrars is no longer last of the ranked boards')
    min_m = BP['min_meetings']
    no_rec = sum(1 for b in ranked if b['recorded'] == 0)
    sc, sb, fc = (by[s] for s in THE_THREE)
    dlv = BP['delivered']

    pf = lambda: [f('pf-gap', None, 'which posted agendas were for meetings later cancelled',
                    'gap', closes=CANCELLED)]

    # ================================================================ minutes posted
    out['board-minutes-posted'] = TP.page(
        'board-minutes-posted',
        'On the town’s Agenda Center, %s of %s board meetings from %s to %s have minutes listed, %s.'
        % (C.num(all_k), C.num(all_n), C.fy(f0), C.fy(f1), C.pct(share, 0)),
        [f('all-k', N(all_k, 'meetings'), 'meetings with minutes listed, %s to %s'
           % (C.fy(f0), C.fy(f1)), 'published', {'a': F(f0), 'b': F(f1)}),
         f('all-n', N(all_n, 'meetings'), 'meetings with a posted agenda, the same years',
           'published'),
         f('share', P0(share), 'of those meetings with minutes listed', 'published'),
         f('boards', N(len(boards), 'boards'), 'boards with a posted agenda in those years',
           'published'),
         f('ranked', N(len(ranked), 'boards'), 'boards with %s or more meetings, ranked' % C.num(min_m),
           'published', {'m': N(min_m)}),
         f('hi90', N(hi90, 'boards'), 'ranked boards listing minutes for %s or more' % C.pct(90, 0),
           'published', {'p': P0(90)}),
         f('lo50', N(lo50, 'boards'), 'ranked boards listing minutes for under half', 'published'),
         f('lib', KN(lib['with_minutes'], lib['meetings']), 'Library Board of Trustees meetings '
           'with minutes', 'published'),
         f('reg', KN(reg['with_minutes'], reg['meetings']), 'Board of Registrars meetings with '
           'minutes', 'published'),
         f('zba', KN(zba['with_minutes'], zba['meetings']), 'Zoning Board of Appeals meetings '
           'with minutes', 'published')] + pf(),
        [con('%s of %s ranked boards list minutes for %s or more of meetings; %s list them for '
             'under half.' % (C.num(hi90), C.num(len(ranked)), C.pct(90, 0), C.num(lo50)),
             ['hi90', 'lo50', 'ranked'],
             {'a': N(hi90), 'n': N(len(ranked)), 'p': P0(90), 'b': N(lo50)}),
         con('The Library Board of Trustees lists minutes for %s meetings; the Board of '
             'Registrars for %s.' % (KN(lib['with_minutes'], lib['meetings'])['text'],
                                     KN(reg['with_minutes'], reg['meetings'])['text']),
             ['lib', 'reg', 'zba'],
             {'a': KN(lib['with_minutes'], lib['meetings']),
              'b': KN(reg['with_minutes'], reg['meetings'])}),
         con('This counts what the Agenda Center listed on %s, not what each board wrote.' % asof,
             ['all-k', 'all-n', 'pf-gap'], allow=(asof,),
             notes=[step('Meetings in the last %s days are left out: minutes are approved at the '
                         'next meeting and posted after it.' % C.num(lag), 'gap', {'l': N(lag)},
                         closes=UNPOSTED),
                    step('Why a board’s minutes are not listed -- a vacancy, a policy, minutes '
                         'approved and not uploaded -- is not in this record.', 'gap',
                         closes=UNPOSTED)])],
        table=dict(caption='Meetings with minutes listed, %s to %s, ranked boards'
                   % (C.fy(f0), C.fy(f1)), views=[dict(
                       key='boards', label='By board', total_col=2, kinds=['ledger'] * 3,
                       columns=['Meetings', 'With minutes', 'Share'],
                       rows=[dict(label=b['name'], cells=[C.num(b['meetings']),
                                                          C.num(b['with_minutes']),
                                                          C.pct(b['share'], 1)])
                             for b in ranked],
                       note='A meeting is a date with a posted agenda. Boards with fewer than %s '
                            'meetings are counted in the totals and not ranked. Read %s.'
                            % (C.num(min_m), asof))]),
        sources=S('agenda', 'register', 'posting'),
        finding_figures={'k': N(all_k), 'n': N(all_n), 'a': F(f0), 'b': F(f1), 's': P0(share)})

    # ================================================================ minutes by year
    ys = {fy: 100 * per_fy[fy][1] / per_fy[fy][0] for fy in fys}
    lo_y, hi_y = min(ys.values()), max(ys.values())
    sc0, sc1, sb0, sb1, fc1 = yr(sc, f0), yr(sc, f1), yr(sb, f0), yr(sb, f1), yr(fc, f1)
    KY = lambda y: KN(y['with_minutes'], y['meetings'])
    out['board-minutes-by-year'] = TP.page(
        'board-minutes-by-year',
        'All boards together list minutes for %s to %s of meetings a year; the School '
        'Committee, %s in %s.' % (C.pct(lo_y, 0), C.pct(hi_y, 0), KY(sc0)['text'], C.fy(f0)),
        [f('y-%d' % fy, P0(ys[fy]), 'of meetings with minutes listed, every board, %s' % C.fy(fy),
           'published', {'y': F(fy)}) for fy in fys]
        + [f('sc0', KY(sc0), 'School Committee meetings with minutes, %s' % C.fy(f0), 'published',
             {'y': F(f0)}),
           f('sc1', KY(sc1), 'School Committee meetings with minutes, %s' % C.fy(f1), 'published',
             {'y': F(f1)}),
           f('sb0', KY(sb0), 'Select Board meetings with minutes, %s' % C.fy(f0), 'published',
             {'y': F(f0)}),
           f('sb1', KY(sb1), 'Select Board meetings with minutes, %s' % C.fy(f1), 'published',
             {'y': F(f1)}),
           f('fc1', KY(fc1), 'Finance Committee meetings with minutes, %s' % C.fy(f1), 'published',
             {'y': F(f1)}),
           f('dlv', N(dlv['n'], 'sets of minutes'), 'Select Board minutes sent to us, not posted',
             'published')],
        [con('Across every board the share with minutes listed runs %s to %s a year.'
             % (C.pct(lo_y, 0), C.pct(hi_y, 0)), ['y-%d' % fy for fy in fys],
             {'a': P0(lo_y), 'b': P0(hi_y)}),
         con('The School Committee lists minutes for %s meetings in %s and %s in %s.'
             % (KY(sc0)['text'], C.fy(f0), KY(sc1)['text'], C.fy(f1)), ['sc0', 'sc1'],
             {'a': KY(sc0), 'y': F(f0), 'b': KY(sc1), 'z': F(f1)},
             notes=[step('Whether those minutes exist elsewhere is not tested: this counts the '
                         'town’s Agenda Center, where the district’s own site sends readers for '
                         'them.', 'gap', closes=UNPOSTED)]),
         con('The Select Board lists %s in %s and %s in %s; the Finance Committee %s.'
             % (KY(sb0)['text'], C.fy(f0), KY(sb1)['text'], C.fy(f1), KY(fc1)['text']),
             ['sb0', 'sb1', 'fc1', 'dlv'],
             {'a': KY(sb0), 'y': F(f0), 'b': KY(sb1), 'z': F(f1), 'c': KY(fc1)},
             notes=[step('%s sets of Select Board minutes the town had not posted were sent to '
                         'this project on %s. They are not counted: this page counts what the '
                         'town posted.' % (C.num(dlv['n']), dlv['when']), 'gap',
                         {'n': N(dlv['n'])}, allow=(dlv['when'],), closes=UNPOSTED)])],
        table=dict(caption='Meetings with minutes listed, by fiscal year', views=[dict(
            key='years', label='By year', total_col=0, kinds=['ledger'] * 4,
            columns=['Every board', 'School Committee', 'Select Board', 'Finance Committee'],
            rows=[dict(label=C.fy(fy), cells=[
                '%s of %s' % (C.num(per_fy[fy][1]), C.num(per_fy[fy][0]))]
                + [KY(yr(b, fy))['text'] for b in (sc, sb, fc)]) for fy in fys],
            note='As listed on the Agenda Center on %s. Meetings in the last %s days are left out.'
                 % (asof, C.num(lag)))]),
        sources=S('agenda', 'register', 'posting'),
        finding_figures={'a': P0(lo_y), 'b': P0(hi_y), 'c': KY(sc0), 'y': F(f0)})

    # ================================================================ recordings
    r0, r1 = per_fy[f0][2], per_fy[f1][2]
    KR = lambda b: KN(b['recorded'], b['meetings'])
    out['board-recordings'] = TP.page(
        'board-recordings',
        '%s of %s meetings, %s to %s, have a town video matched; %s of %s ranked boards have none.' % (C.num(all_rec), C.num(all_n), C.fy(f0), C.fy(f1), C.num(no_rec),
                               C.num(len(ranked))),
        [f('rec', N(all_rec, 'meetings'), 'meetings with a video matched, %s to %s'
           % (C.fy(f0), C.fy(f1)), 'published', {'a': F(f0), 'b': F(f1)}),
         f('rec-n', N(all_n, 'meetings'), 'meetings with a posted agenda, the same years',
           'published'),
         f('none', N(no_rec, 'boards'), 'ranked boards with no video matched', 'published'),
         f('r0', N(r0, 'meetings'), 'meetings with a video, %s' % C.fy(f0), 'published', {'y': F(f0)}),
         f('r1', N(r1, 'meetings'), 'meetings with a video, %s' % C.fy(f1), 'published', {'y': F(f1)}),
         f('zba-r', KR(zba), 'Zoning Board of Appeals meetings with a video', 'published'),
         f('zba-m', KN(zba['with_minutes'], zba['meetings']), 'the same meetings with minutes listed',
           'published'),
         f('cpc-r', KR(cpc), 'Capital Planning Committee meetings with a video', 'published'),
         f('cpc-m', KN(cpc['with_minutes'], cpc['meetings']), 'the same meetings with minutes listed',
           'published'),
         f('lib-r', KR(lib), 'Library Board of Trustees meetings with a video', 'published'),
         f('lib-m', KN(lib['with_minutes'], lib['meetings']), 'the same meetings with minutes listed',
           'published')],
        [con('The Zoning Board of Appeals has a video for %s meetings and minutes listed for %s.'
             % (KR(zba)['text'], KN(zba['with_minutes'], zba['meetings'])['text']),
             ['zba-r', 'zba-m', 'cpc-r', 'cpc-m'],
             {'a': KR(zba), 'b': KN(zba['with_minutes'], zba['meetings'])}),
         con('The Library Board of Trustees has minutes for %s and a video for %s.'
             % (KN(lib['with_minutes'], lib['meetings'])['text'], KR(lib)['text']),
             ['lib-r', 'lib-m', 'none'],
             {'a': KN(lib['with_minutes'], lib['meetings']), 'b': KR(lib)}),
         con('Meetings with a video went from %s in %s to %s in %s.'
             % (C.num(r0), C.fy(f0), C.num(r1), C.fy(f1)), ['r0', 'r1', 'rec', 'rec-n'],
             {'a': N(r0), 'y': F(f0), 'b': N(r1), 'z': F(f1)},
             notes=[step('A video is matched to a board and date by its title on the town’s '
                         'channel, so a mislabelled video is missed or misplaced.', 'gap',
                         closes=VIDEO_MAP),
                    step('A recording and a set of minutes are different records; neither '
                         'count says what was decided.', 'gap', closes=UNPOSTED)])],
        table=dict(caption='Meetings with a video and with minutes, %s to %s, ranked boards'
                   % (C.fy(f0), C.fy(f1)), views=[dict(
                       key='boards', label='By board', total_col=-1, kinds=['ledger'] * 3,
                       columns=['Meetings', 'With a video', 'With minutes'],
                       rows=[dict(label=b['name'], cells=[C.num(b['meetings']), C.num(b['recorded']),
                                                          C.num(b['with_minutes'])])
                             for b in sorted(ranked, key=lambda b: (-b['recorded_share'], b['name']))],
                       note='Sorted by the share of meetings with a video. Read %s.' % asof)]),
        sources=S('agenda', 'register', 'videos', 'posting'),
        finding_figures={'r': N(all_rec), 'n': N(all_n), 'a': F(f0), 'b': F(f1), 'x': N(no_rec),
                         'm': N(len(ranked))})

    # ================================================================ seats filled
    fill = {int(r['fy']): r for r in BC['fill']}
    fa, fz = min(fill), max(fill)
    A, Z = fill[fa], fill[fz]
    nb, ll = like_for_like(str(fa), str(fz))
    if (sum(ll[str(fz)]) == 0) or abs(100 * A['filled'] / A['seats'] - A['pct']) > 0.1:
        fail('the fill rows no longer reproduce from the listing')
    lla = 100 * ll[str(fa)][1] / ll[str(fa)][0]
    llz = 100 * ll[str(fz)][1] / ll[str(fz)][0]
    vac = {v['post']: v for v in OS['vacancies']}
    pers = vac.get('PERSONNEL COMMITTEE')
    if not pers:
        fail('the Personnel Committee is no longer printed with empty seats')
    out['board-seats-filled'] = TP.page(
        'board-seats-filled',
        'The %s listing prints %s names against %s seats its boards state, %s; %s read %s.'
        % (C.fy(fz), C.num(Z['filled']), C.num(Z['seats']), C.pct(Z['pct'], 0), C.fy(fa),
           C.pct(A['pct'], 0)),
        [f('z-pct', P0(Z['pct']), 'of stated seats with a name printed, %s' % C.fy(fz), 'published',
           {'y': F(fz)}),
         f('z-names', N(Z['filled'], 'names'), 'names printed under those boards, %s' % C.fy(fz),
           'published', {'y': F(fz)}),
         f('z-seats', N(Z['seats'], 'seats'), 'seats those boards state, %s' % C.fy(fz), 'published',
           {'y': F(fz)}),
         f('z-bodies', N(Z['bodies'], 'boards'), 'boards stating a plain size, %s' % C.fy(fz),
           'published', {'y': F(fz)}),
         f('a-pct', P0(A['pct']), 'the same measure, %s, over %s boards' % (C.fy(fa), C.num(A['bodies'])),
           'published', {'y': F(fa), 'n': N(A['bodies'])}),
         f('ll-n', N(nb, 'boards'), 'boards stating a size in both %s and %s' % (C.fy(fa), C.fy(fz)),
           'published', {'a': F(fa), 'b': F(fz)}),
         f('ll-a', P0(lla), 'of their seats with a name printed, %s' % C.fy(fa), 'published',
           {'y': F(fa)}),
         f('ll-z', P0(llz), 'of their seats with a name printed, %s' % C.fy(fz), 'published',
           {'y': F(fz)}),
         f('pers', N(pers['seats'], 'seats'), 'Personnel Committee seats printed empty, %s' % C.fy(fz),
           'published', {'y': F(fz)}),
         f('later', None, 'whether a seat printed empty was filled later that year', 'gap',
           closes=CURRENT)],
        [con('Over the %s boards stating a size in both years, names fill %s of seats in %s and '
             '%s in %s.' % (C.num(nb), C.pct(lla, 0), C.fy(fa), C.pct(llz, 0), C.fy(fz)),
             ['ll-n', 'll-a', 'll-z', 'a-pct', 'z-pct'],
             {'n': N(nb), 'a': P0(lla), 'y': F(fa), 'b': P0(llz), 'z': F(fz)},
             notes=[step('More names than seats is read here as a replacement printed beside the '
                         'person replaced; the listing does not mark which.', 'hypothesis')]),
         con('The Personnel Committee is printed with %s seats empty in %s.'
             % (C.num(pers['seats']), C.fy(fz)), ['pers', 'z-seats', 'z-names'],
             {'a': N(pers['seats']), 'y': F(fz)}),
         con('The listing is printed once a year; it does not show a seat filled since.',
             ['later', 'z-bodies'],
             notes=[step('Why a seat is empty -- nobody applied, an appointment not yet made, a '
                         'board winding down -- is not in the listing.', 'gap', closes=DATED)])],
        chart=dict(id='board-composition-fill', source='/data/board-composition.json'),
        table=dict(caption='Stated seats and names printed, boards stating a plain size',
                   views=[dict(
                       key='years', label='By year', total_col=3, kinds=['ledger'] * 4,
                       columns=['Boards', 'Seats stated', 'Names printed', 'Filled'],
                       rows=[dict(label=C.fy(y), cells=[C.num(fill[y]['bodies']),
                                                        C.num(fill[y]['seats']),
                                                        C.num(fill[y]['filled']),
                                                        C.pct(fill[y]['pct'], 0)])
                             for y in sorted(fill)],
                       note='The set of boards differs year to year; the like-for-like figures '
                            'above hold it fixed. A body stated as a range has no size to fill.')]),
        sources=S('ar25', 'ar16', 'personnel', 'comp-md', 'comp'),
        finding_figures={'y': F(fz), 'a': N(Z['filled']), 'b': N(Z['seats']), 'p': P0(Z['pct']),
                         'z': F(fa), 'q': P0(A['pct'])})

    # ================================================================ open seats
    fy_os = int(OS['fy'])
    if fy_os != fz:
        fail('open-seats.json reads FY%s and the composition reads FY%s' % (fy_os, fz))
    nvac = sum(v['seats'] for v in OS['vacancies'])
    napp = sum(v['seats'] for v in OS['vacancies'] if v['filled_by'] == 'appointed')
    nele = sum(v['seats'] for v in OS['vacancies'] if v['filled_by'] == 'elected')
    if napp + nele != nvac:
        fail('a vacancy is neither appointed nor elected')
    exp = {int(e['year']): len(e['seats']) for e in OS['expiring']}
    ahead = sorted(y for y in exp if y > fy_os)[:3]
    e1, e2, e3 = ahead
    out['board-open-seats'] = TP.page(
        'board-open-seats',
        'The %s annual report prints %s seats empty under %s headings: %s appointed, %s elected.'
        % (C.fy(fy_os), C.num(nvac), C.num(len(OS['vacancies'])), C.num(napp), C.num(nele)),
        [f('vac', N(nvac, 'seats'), 'seats printed empty, %s listing' % C.fy(fy_os), 'published',
           {'y': F(fy_os)}),
         f('heads', N(len(OS['vacancies']), 'headings'), 'headings with a seat printed empty',
           'published'),
         f('app', N(napp, 'seats'), 'of them under the appointed officials', 'published'),
         f('ele', N(nele, 'seats'), 'of them under the elected officials', 'published'),
         f('pers-v', N(pers['seats'], 'seats'), 'printed empty on the Personnel Committee', 'published'),
         f('e1', N(exp[e1], 'seats'), 'filled seats whose term ends in %s' % e1, 'published',
           {'y': YR(e1)}),
         f('e2', N(exp[e2], 'seats'), 'filled seats whose term ends in %s' % e2, 'published',
           {'y': YR(e2)}),
         f('e3', N(exp[e3], 'seats'), 'filled seats whose term ends in %s' % e3, 'published',
           {'y': YR(e3)}),
         f('today', None, 'which seats are open today', 'gap', closes=CURRENT)],
        [con('The Personnel Committee accounts for %s of the %s seats printed empty.'
             % (C.num(pers['seats']), C.num(nvac)), ['pers-v', 'vac', 'app', 'ele'],
             {'a': N(pers['seats']), 'b': N(nvac)}),
         con('The report prints %s terms ending in %s, %s in %s and %s in %s.'
             % (C.num(exp[e1]), e1, C.num(exp[e2]), e2, C.num(exp[e3]), e3), ['e1', 'e2', 'e3'],
             {'a': N(exp[e1]), 'x': YR(e1), 'b': N(exp[e2]), 'y': YR(e2), 'c': N(exp[e3]),
              'z': YR(e3)}),
         con('The %s terms have come up since the report was printed; it cannot say who holds '
             'those seats now.' % e1, ['e1', 'today'], {'x': YR(e1)})],
        table=dict(caption='Seats printed empty, %s annual report' % C.fy(fy_os), views=[dict(
            key='vacancies', label='By heading', total_col=-1, kinds=['ledger', 'stated'],
            columns=['Seats empty', 'Section'],
            rows=[dict(label=v['post'], cells=[C.num(v['seats']),
                                               v['filled_by']])
                  for v in OS['vacancies']],
            note='Headings as the town prints them. Two are posts rather than boards. Names of '
                 'seat holders are in the full list, not here.')]),
        sources=S('ar25', 'seats-md', 'open'),
        finding_figures={'y': F(fy_os), 'v': N(nvac), 'h': N(len(OS['vacancies'])), 'a': N(napp),
                         'e': N(nele)})

    # ================================================================ board sizes
    sizes = BC['sizes']
    held = sum(s['people'] for s in sizes)
    single = sum(1 for s in sizes if s['people'] == 1)
    three = sum(1 for s in sizes if s['people'] >= 3)
    top = sizes[0]
    sz = {s['post'].casefold(): s['people'] for s in sizes}
    if top['post'] != 'COUNCIL ON AGING':
        fail('the Council on Aging is no longer the largest heading')
    out['board-sizes'] = TP.page(
        'board-sizes',
        'The %s listing prints %s holders under %s headings; the Council on Aging is largest, with %s.'
        % (C.fy(fz), C.num(held), C.num(len(sizes)), C.num(top['people'])),
        [f('heads', N(len(sizes), 'headings'), 'headings with a name printed, %s' % C.fy(fz),
           'published', {'y': F(fz)}),
         f('held', N(held, 'holders'), 'holders printed under them', 'published'),
         f('coa', N(top['people'], 'holders'), 'Council on Aging, the largest', 'published'),
         f('single', N(single, 'headings'), 'headings with a single holder', 'published'),
         f('three', N(three, 'headings'), 'headings with three or more holders', 'published'),
         f('sb', N(sz['select board'], 'holders'), 'Select Board', 'published'),
         f('sc', N(sz['school committee'], 'holders'), 'School Committee', 'published'),
         f('fc', N(sz['finance committee'], 'holders'), 'Finance Committee', 'published')],
        [con('Of %s headings, %s print a single holder and %s print three or more.'
             % (C.num(len(sizes)), C.num(single), C.num(three)), ['heads', 'single', 'three'],
             {'n': N(len(sizes)), 'a': N(single), 'b': N(three)},
             notes=[step('A heading is as the town prints it: some are single posts, and some, '
                         'such as associate members, are parts of a board.', 'gap',
                         closes=CHARTERS)]),
         con('The Council on Aging prints %s holders; the Finance Committee %s, the Select Board %s.'
             % (C.num(top['people']), C.num(sz['finance committee']), C.num(sz['select board'])),
             ['coa', 'fc', 'sb', 'sc', 'held'],
             {'a': N(top['people']), 'b': N(sz['finance committee']), 'c': N(sz['select board'])})],
        chart=dict(id='board-composition-where', source='/data/board-composition.json'),
        table=dict(caption='Holders printed per heading, %s' % C.fy(fz), views=[dict(
            key='sizes', label='Headings with four or more', total_col=-1, kinds=['ledger'],
            columns=['Holders printed'],
            rows=[dict(label=s['post'], cells=[C.num(s['people'])]) for s in sizes
                  if s['people'] >= 4],
            note='Filled seats only, as printed. Smaller headings are in the full listing.')]),
        sources=S('ar25', 'personnel', 'comp-md', 'comp'),
        finding_figures={'y': F(fz), 'h': N(held), 'n': N(len(sizes)), 'c': N(top['people'])})

    # ================================================================ seats changing hands
    churn_rows = BC['body_churn']
    med = next(c for c in BC['conclusions'] if c['id'] == 'churn-is-uneven')['figures']['med']['value']
    if med != statistics.median_high(sorted(b['churn'] for b in churn_rows)):
        fail('the composition payload’s median no longer reproduces from body_churn')
    hi = churn_rows[0]
    lo = churn_rows[-1]
    bc = {b['post'].casefold(): b for b in churn_rows}
    for k in ('school committee', 'select board', 'finance committee', 'board of selectmen'):
        if k not in bc:
            fail('%r is no longer in body_churn' % k)
    Pc = lambda b: P0(b['churn'])
    measured = [b for b in churn_rows if b['pairs'] >= 4]
    out['board-turnover'] = TP.page(
        'board-turnover',
        'Across %s bodies of three or more seats, the median sees %s of its seats change hands a year.'
        % (C.num(len(churn_rows)), C.pct(med, 0)),
        [f('n', N(len(churn_rows), 'bodies'), 'bodies of three or more seats measured', 'published'),
         f('med', P0(med), 'of seats changing hands a year, median body', 'published'),
         f('hi', Pc(hi), '%s, the highest' % hi['post'], 'published'),
         f('lo', Pc(lo), '%s, the lowest' % lo['post'], 'published'),
         f('sc', Pc(bc['school committee']), 'School Committee, a year', 'published'),
         f('sb', Pc(bc['select board']), 'Select Board, a year', 'published'),
         f('fc', Pc(bc['finance committee']), 'Finance Committee, a year', 'published'),
         f('bos', Pc(bc['board of selectmen']), 'Board of Selectmen, the earlier heading',
           'published'),
         f('why', None, 'why any member left: a term ending, a resignation, a move', 'gap',
           closes=DATED)],
        [con('The median body changes %s of its seats a year; the range runs from %s to %s.'
             % (C.pct(med, 0), Pc(lo)['text'], Pc(hi)['text']), ['med', 'hi', 'lo', 'n'],
             {'m': P0(med), 'a': Pc(lo), 'b': Pc(hi)}),
         con('The Finance Committee changes %s a year, the School Committee %s, the Select Board %s.'
             % (Pc(bc['finance committee'])['text'], Pc(bc['school committee'])['text'],
                Pc(bc['select board'])['text']), ['fc', 'sc', 'sb', 'bos'],
             {'a': Pc(bc['finance committee']), 'b': Pc(bc['school committee']),
              'c': Pc(bc['select board'])},
             notes=[step('A board renamed in the listing is measured as two: the Board of '
                         'Selectmen and the Select Board are separate rows.', 'gap',
                         closes=RENAMES)]),
         con('A name leaving the listing is not a resignation: a term ending and a move look '
             'the same.', ['why', 'med'])],
        table=dict(caption='Seats changing hands a year, bodies measured four or more times',
                   views=[dict(
                       key='bodies', label='By body', total_col=2, kinds=['ledger'] * 3,
                       columns=['Seats', 'Years compared', 'Changing hands'],
                       rows=[dict(label=b['post'], cells=['%.1f' % b['seats'], C.num(b['pairs']),
                                                          C.pct(b['churn'], 0)])
                             for b in measured],
                       note='Names matched between consecutive listings. Seats is the average '
                            'printed. Bodies compared fewer times are in the median, not here.')]),
        sources=S('ar25', 'ar16', 'personnel', 'comp-md', 'comp'),
        finding_figures={'n': N(len(churn_rows)), 'm': P0(med)})

    # ================================================================ member tenure
    T = board_tenure()
    if (str(T['first']), str(T['last'])) != (BC['years'][0], BC['years'][-1]):
        fail('the officials listing in org-chart.csv no longer spans the composition years')
    span = len(BC['years'])
    last_ch = BC['churn'][-1]
    out['board-member-tenure'] = TP.page(
        'board-member-tenure',
        'Of %s people printed in the town’s listings from %s to %s, %s appear in all %s.'
        % (C.num(BC['ever']), C.fy(T['first']), C.fy(T['last']), C.num(BC['served_all']),
           C.num(span)),
        [f('ever', N(BC['ever'], 'people'), 'people in the listing, %s to %s' % (C.fy(T['first']),
                                                                          C.fy(T['last'])),
           'published', {'a': F(T['first']), 'b': F(T['last'])}),
         f('all', N(BC['served_all'], 'people'), 'printed in all %s listings' % C.num(span),
           'published', {'n': N(span)}),
         f('mem', N(T['memberships'], 'memberships'), 'board memberships: one person on one board',
           'published'),
         f('settled', N(T['settled'], 'memberships'), 'that began and ended inside the record',
           'published'),
         f('median', figure(T['median'], '%s listings' % C.num(T['median']), 'annual listings'),
           'median length of those memberships', 'published'),
         f('single', N(T['single'], 'memberships'), 'of them printed in one listing only',
           'published'),
         f('cens', N(T['censored'], 'memberships'), 'under way at the first listing or the last',
           'published'),
         f('new', N(last_ch['arrived'], 'names'), 'names new to the listing, %s' % C.fy(last_ch['fy']),
           'published', {'y': F(last_ch['fy'])}),
         f('gone', N(last_ch['left'], 'names'), 'names from the year before not printed, %s'
           % C.fy(last_ch['fy']), 'published', {'y': F(last_ch['fy'])})],
        [con('Of %s board memberships that began and ended inside the record, the median spans %s.'
             % (C.num(T['settled']), '%s listings' % C.num(T['median'])), ['settled', 'median', 'single'],
             {'a': N(T['settled']), 'm': figure(T['median'], '%s listings' % C.num(T['median']))},
             notes=[step('A listing is printed once a year, so a span of N listings is at least '
                         'N less one years of service and at most N.', 'gap', closes=DATED)]),
         con('%s of %s memberships were under way at the first listing or the last, so their '
             'length is unknown.' % (C.num(T['censored']), C.num(T['memberships'])),
             ['cens', 'mem'], {'a': N(T['censored']), 'b': N(T['memberships'])}),
         con('In %s, %s names are new to the listing and %s from the year before are gone.'
             % (C.fy(last_ch['fy']), C.num(last_ch['arrived']), C.num(last_ch['left'])),
             ['new', 'gone', 'ever', 'all'],
             {'y': F(last_ch['fy']), 'a': N(last_ch['arrived']), 'b': N(last_ch['left'])})],
        table=dict(caption='Names in the listing, year on year', views=[dict(
            key='churn', label='By year', total_col=-1, kinds=['ledger'] * 3,
            columns=['Stayed', 'New', 'Gone'],
            rows=[dict(label=C.fy(c['fy']), cells=[C.num(c['stayed']), C.num(c['arrived']),
                                                   C.num(c['left'])]) for c in BC['churn']],
            note='Every heading in the listing, posts as well as boards. A memberships count is '
                 'boards only, and matches a name by surname and first initial.')]),
        sources=S('ar25', 'ar16', 'org', 'personnel', 'comp'),
        finding_figures={'n': N(BC['ever']), 'a': F(T['first']), 'b': F(T['last']),
                         'k': N(BC['served_all']), 's': N(span)})

    # ================================================================ the hub
    h = {}
    h['h-share'] = f('h-share', P0(share), 'meetings with minutes listed, %s to %s'
                     % (C.fy(f0), C.fy(f1)), 'published', {'a': F(f0), 'b': F(f1)})
    h['h-sc0'] = f('h-sc0', KY(sc0), 'School Committee meetings with minutes, %s' % C.fy(f0),
                   'published', {'y': F(f0)})
    h['h-sc1'] = f('h-sc1', KY(sc1), 'School Committee meetings with minutes, %s' % C.fy(f1),
                   'published', {'y': F(f1)})
    h['h-rec'] = f('h-rec', N(all_rec, 'meetings'), 'meetings with a video matched, same years',
                   'published')
    h['h-fill'] = f('h-fill', P0(Z['pct']), 'stated seats with a name printed, %s' % C.fy(fz),
                    'published', {'y': F(fz)})
    h['h-fill0'] = f('h-fill0', P0(A['pct']), 'the same measure, %s' % C.fy(fa), 'published',
                     {'y': F(fa)})
    h['h-vac'] = f('h-vac', N(nvac, 'seats'), 'seats printed empty, %s' % C.fy(fz), 'published',
                   {'y': F(fz)})
    h['h-med'] = f('h-med', P0(med), 'of seats changing hands a year, median body', 'published')
    h['h-ten'] = f('h-ten', figure(T['median'], '%s listings' % C.num(T['median']), 'annual listings'),
                   'median finished board membership', 'published')
    h['h-all'] = f('h-all', KN(BC['served_all'], BC['ever'], 'people'),
                   'people printed in all %s listings' % C.num(span), 'published', {'n': N(span)})
    hub_ladder = LD.ladder([
        LD.tier('Meeting records', [h['h-share'], h['h-sc0'], h['h-sc1'], h['h-rec']]),
        LD.tier('Seats', [h['h-fill'], h['h-fill0'], h['h-vac']]),
        LD.tier('People', [h['h-med'], h['h-ten'], h['h-all']]),
    ], [
        LD.conclusion('%s of %s meetings have minutes listed; by board the share runs %s to %s.'
                      % (C.num(all_k), C.num(all_n), C.pct(ranked[-1]['share'], 0),
                         C.pct(best['share'], 0)), ['h-share', 'h-rec'],
                      {'a': N(all_k), 'b': N(all_n), 'c': P0(ranked[-1]['share']),
                       'd': P0(best['share'])}),
        LD.conclusion('The School Committee lists minutes for %s meetings in %s and %s in %s.'
                      % (KY(sc0)['text'], C.fy(f0), KY(sc1)['text'], C.fy(f1)), ['h-sc0', 'h-sc1'],
                      {'a': KY(sc0), 'y': F(f0), 'b': KY(sc1), 'z': F(f1)}),
        LD.conclusion('Stated seats with a name printed: %s in %s, %s in %s.'
                      % (C.pct(A['pct'], 0), C.fy(fa), C.pct(Z['pct'], 0), C.fy(fz)),
                      ['h-fill0', 'h-fill', 'h-vac'],
                      {'a': P0(A['pct']), 'y': F(fa), 'b': P0(Z['pct']), 'z': F(fz)}),
        LD.conclusion('The median body changes %s of its seats a year; a finished membership '
                      'spans %s.' % (C.pct(med, 0), '%s listings' % C.num(T['median'])),
                      ['h-med', 'h-ten', 'h-all'],
                      {'m': P0(med), 't': figure(T['median'], '%s listings' % C.num(T['median']))}),
        LD.conclusion('Each figure is what the town posted or printed, as read; none says why.',
                      ['h-share', 'h-fill']),
    ])
    out[HUB] = TP.hub(
        HUB,
        'Across every board, %s of %s to %s meetings have minutes listed on the town’s site. '
        'In %s, %s of the seats the boards state had a name printed, and the median body '
        'changes %s of its seats a year.'
        % (C.pct(share, 0), C.fy(f0), C.fy(f1), C.fy(fz), C.pct(Z['pct'], 0), C.pct(med, 0)),
        hub_ladder,
        chart=dict(id='board-composition-fill', source='/data/board-composition.json'),
        answer_figures={'s': P0(share), 'a': F(f0), 'b': F(f1), 'y': F(fz), 'p': P0(Z['pct']),
                        'm': P0(med)})

    if sorted(k for k in out if k != HUB) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = []
        for p, text in outs.items():
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                stale.append(os.path.relpath(p, ROOT))
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('board records topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
