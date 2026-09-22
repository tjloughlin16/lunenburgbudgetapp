#!/usr/bin/env python3
"""Who runs the town: every post in the annual report's personnel listing.

    python3 scripts/build_town_personnel.py
    python3 scripts/build_town_personnel.py --check

Writes `sources/analyses/town-personnel.md` and `fy28/public/data/town-personnel.json`.

WHY THIS SITS BESIDE THE BUDGET PAGES. TJ: *"'cuts' are service reductions, which we have
to find in ways other than budget information. The immediate one is staffing."* A budget
line that falls is not a cut and a line that rises is not a hiring; the dollars cannot say
either. This is the nearest published thing to the other question -- how many posts the
town has and who is in them.

WHAT IT IS AND IS NOT A COUNT OF, and the distinction is the whole page.

It counts POSTS IN THE LISTING. That is every elected seat, every appointed board seat and
every appointed officer the town prints. It is NOT a headcount of the town's employees: a
DPW labourer, a library assistant and a town hall clerk hold no appointed post and appear
nowhere in it. The gross-wages list would give that, and it stopped naming departments
after FY2016 -- registered as a gap.

THE SPLIT IS THE TOWN'S OWN, twice over. TJ: *"its not OUR classification. its theirs...
we KNOW the select board is elected. We know the finance committted is appointed. We know
the superintendent of shcools is hired."* Elected against appointed is the section the
report prints it under; a board seat against an officer is whether the post states a
membership -- `Board of Assessors - (3 members) 3 year term` against `DPW DIRECTOR`.

WHAT A RESIDENT ACTUALLY ASKS, and the first version of this page answered none of it.

It led with `176 rows under a board whose stated size and printed names differ`. TJ:
*"I dont konw what this thinking is getting at ... Think from a citizen perspective. what
information about personel do we care about? the metrics you have dont seem to be the ones
we care about."* He is right, and the failure has a name in this repo already:
`conclusions.py` says a defect in a DOCUMENT is a footnote, never a headline, and that the
test is whether a thing is about the WORLD or about a document. A count of rows whose
extraction we are unsure of is about our reading. It went in a stat box.

The four questions this page is now built to answer, all of which the listing can:

  1. WHERE CAN I SERVE?     The town prints its empty seats. Eighteen of them in FY2025,
                            across twelve bodies, by name.
  2. WHEN DOES ONE OPEN?    Every seat prints the year its term runs out.
  3. IS IT A SMALL CLIQUE?  No, and that is worth saying: 174 distinct people hold 183
                            posts, and only nine hold more than one.
  4. DOES ANYBODY STAY?     Barely. About a third of the names change every year, and 46
                            people out of 359 ever listed served all four years.

AND THE HEADING IS THE CHECK. A post that states how many members it has is followed by
that many names, or it is not, and the rows split three ways on it. Nothing here may be
counted without splitting on `size_check` -- a board listing six people against five seats
is usually a mid-year replacement printed beside the person it replaced.
"""
import argparse
import collections
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from conclusions import conclusion, emit, figure, num, pct   # noqa: E402

SRC = os.path.join(ROOT, 'sources', 'data', 'town-personnel.csv')
STAFFING = os.path.join(ROOT, 'sources', 'data', 'department-staffing.csv')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'town-personnel.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'town-personnel.json')

KINDS = [('elected board seat', 'Elected seats', 'filled by the voters'),
         ('appointed board seat', 'Appointed board seats', 'filled by the Select Board'),
         ('appointed officer', 'Appointed officers', 'posts somebody is hired or named into')]


def load():
    rows = list(csv.DictReader(open(SRC, encoding='utf-8')))
    for r in rows:
        r['vacancies'] = int(r.get('vacancies') or 0)
    for r in rows:
        r['kindfull'] = '%s %s' % (r['section'], r['kind'])
    years = sorted({r['fy'] for r in rows})
    per = collections.Counter((r['fy'], r['kindfull']) for r in rows)
    checks = collections.Counter(r['size_check'] for r in rows)
    posts = {}
    for r in rows:
        posts.setdefault(r['post'], {'post': r['post'], 'kind': r['kindfull'],
                                     'years': set(), 'stated': r['stated_members']})
        posts[r['post']]['years'].add(r['fy'])
    for p in posts.values():
        p['years'] = sorted(p['years'])
    last = years[-1]
    cur = [r for r in rows if r['fy'] == last]
    named = [r for r in cur if r['person'].strip()]

    # 1. WHERE CAN I SERVE. The town's own printed vacancies, by body.
    vac = collections.Counter()
    for r in cur:
        if r['vacancies']:
            vac[r['post']] += r['vacancies']

    # 2. WHEN. The year each seat's term runs out.
    # THE NEXT CHANCE TO JOIN IS A FUTURE YEAR. Taking the earliest term year in the data
    # picked a seat already expiring in the report's own year -- one seat, presented as the
    # next opportunity, when thirty-five come up the year after.
    terms = collections.Counter(r['term_expires'] for r in named if r['term_expires'])
    ahead = sorted(y for y in terms if y.isdigit() and int(y) > int(last))

    # 3. HOW CONCENTRATED. Distinct people against posts held.
    who = collections.Counter(r['person'].strip() for r in named)
    multi = sorted(((n, c) for n, c in who.items() if c > 1), key=lambda a: (-a[1], a[0]))

    # 4. DOES ANYBODY STAY. Names carried over, arrived and gone, year to year.
    names = {y: {r['person'].strip() for r in rows
                 if r['fy'] == y and r['person'].strip()} for y in years}
    # ONLY CONSECUTIVE YEARS. The listing is readable for FY2016-18, FY2020 and FY2022-25,
    # and the gaps are real -- FY2019 and FY2021 print the section under a heading this
    # reader does not recognise, and FY2014-15 state no memberships at all. Differencing
    # FY2018 against FY2020 and calling it a year's churn would count two years of
    # arrivals as one and overstate the turnover by roughly double.
    churn = []
    for a, b in zip(years, years[1:]):
        if int(b) - int(a) != 1:
            continue
        churn.append(dict(fy=b, stayed=len(names[a] & names[b]),
                          arrived=len(names[b] - names[a]),
                          left=len(names[a] - names[b])))
    ever = collections.defaultdict(set)
    for r in rows:
        if r['person'].strip():
            ever[r['person'].strip()].add(r['fy'])
    served_all = sorted(n for n, y in ever.items() if len(y) == len(years))

    sizes = collections.Counter(r['post'] for r in named)

    # WHAT THE DEPARTMENTS SAY ABOUT THEMSELVES. A separate quantity from the listing and
    # kept separate: the listing counts POSTS, this counts the people a department says it
    # employs. They may not be added together.
    staff = []
    if os.path.exists(STAFFING):
        staff = [r for r in csv.DictReader(open(STAFFING, encoding='utf-8'))
                 if r['parsed'] == 'yes']
    fire = sorted([r for r in staff if r['measure'].startswith('career')],
                  key=lambda r: r['fy'])
    seen, fire_series = set(), []
    for r in fire:
        if r['fy'] in seen:
            continue
        seen.add(r['fy'])
        fire_series.append(dict(fy=r['fy'], career=int(r['career']),
                                on_call_low=int(r['on_call_low']),
                                on_call_high=int(r['on_call_high']),
                                page=r['page']))

    # TURNOVER BY BODY, over CONSECUTIVE years only and over bodies present in both ends
    # of a pair. A body seen in one year of a pair and not the other tells us nothing about
    # its churn -- it tells us the listing changed -- so it is skipped rather than counted
    # as a total replacement.
    #
    # A one-seat post whose holder changed reads as 100% turnover, which is true and
    # useless: it is one person leaving a job. So the page reports bodies of three seats or
    # more and says that is what it is doing.
    seats_by = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        if r['person'].strip():
            seats_by[r['post']][r['fy']].add(r['person'].strip())
    body = []
    for post, held in seats_by.items():
        ch = seats = obs = 0
        for a, b in zip(years, years[1:]):
            if int(b) - int(a) != 1 or a not in held or b not in held:
                continue
            ch += len(held[b] - held[a]) + len(held[a] - held[b])
            seats += len(held[a]) + len(held[b])
            obs += 1
        if obs < 2 or not seats:
            continue
        body.append(dict(post=post, seats=round(seats / (2.0 * obs), 1), pairs=obs,
                         changes=ch, churn=round(ch / seats * 100, 1)))
    body.sort(key=lambda b: -b['churn'])
    big = [b for b in body if b['seats'] >= 3]

    return dict(rows=rows, years=years, per=per, checks=checks, posts=posts,
                last=last, named=named, vacancies=vac, terms=terms, ahead=ahead,
                body_churn=body, body_big=big, staffing=staff, fire=fire_series,
                distinct=len(who), held=len(named), multi=multi, churn=churn,
                ever=len(ever), served_all=served_all, sizes=sizes)


def _sources(d):
    return [dict(
        what='Every elected and appointed post in the town, FY%s to FY%s'
             % (d['years'][0], d['years'][-1]),
        where='The ELECTED OFFICIALS and APPOINTED OFFICIALS listing in each annual town '
              'report — nine pages a year',
        basis='published',
        note='Read by scripts/extract_personnel.py. The format is not the same every '
             'year: the elected pages set their headings in title case and the appointed '
             'pages in capitals, and two or three pages a year are set in two columns.')]


def _not_established():
    return [
        'How many people the town EMPLOYS. This counts posts in the listing, and a DPW '
        'labourer, a library assistant and a town hall clerk hold no appointed post. The '
        'gross-wages list would give a headcount and it stopped naming departments after '
        'FY2016.',
        'What anybody is paid. The listing never says, and no salary is inferred here '
        'from a post’s name.',
        'Hours. A board seat and a full-time directorship are one row each, and the '
        'departments that state their staffing state no FTE either — a career post and an '
        'on-call post are not the same job and cannot be netted against each other.',
        'A town total. The departments that describe their staffing do it in whichever '
        'form that year’s department head chose — a count, a range, an establishment post '
        'by post, a list of names — and those are different quantities that may not be '
        'summed.',
        'Whether a post was actually filled for the whole year. The listing is a point in '
        'time and an appointment note is the only sign of a change within one.',
    ]


def _med(d):
    b = sorted(x['churn'] for x in d['body_big'])
    return b[len(b) // 2]


def conclusions_for(d):
    last = d['last']
    vac = sum(d['vacancies'].values())
    bodies = len(d['vacancies'])
    soon = sorted(d['terms'])[0] if d['terms'] else None
    churn = d['churn'][-1]
    turn = (churn['arrived'] + churn['left']) / 2.0 / d['held'] * 100
    return emit('town-personnel', [
        conclusion(
            id='seats-are-open',
            claim='The town printed empty seats on a dozen of its boards, and says which',
            lede='An empty seat is the one thing on this page a resident can act on '
                 'today, and the town publishes exactly where they are.',
            detail='The FY%s listing prints %s empty across %s different boards and '
                   'committees. They are named rather than counted: the listing puts the '
                   'word where the person would go.'
                   % (last, '%d seats' % vac, '%d' % bodies),
            figures={'seats': figure(vac, num(vac), 'empty seats the town printed'),
                     'bodies': figure(bodies, num(bodies), 'boards and committees')},
            figure='seats',
            kind='measured',
            bearing='lever',
            basis='The APPOINTED and ELECTED OFFICIALS listing in the FY%s annual report, '
                  'where a vacancy is printed in place of a name.' % last,
            not_shown='Whether a seat was still empty by the time the report was printed, '
                      'or how long it had been.',
            so_what='These are seats a resident can ask to fill, named by the town itself.',
            allow=('FY%s' % last,),
        ),
        conclusion(
            id='seats-turn-over',
            claim='About a third of the people on the town’s boards change every year',
            lede='The listing is not a stable roster. It is a heavy annual churn of '
                 'arrivals and departures around a small core.',
            detail='Between FY%s and FY%s, %s arrived and %s left, against %s who stayed '
                   '— roughly %s of the seats changing hands in a single year. Of %s '
                   'people listed at any point across the four years, %s appear in all '
                   'four.'
                   % (str(int(last) - 1), last, num(churn['arrived']), num(churn['left']),
                      num(churn['stayed']), pct(turn, 0), num(d['ever']),
                      num(len(d['served_all']))),
            figures={'in': figure(churn['arrived'], num(churn['arrived']), 'arrived'),
                     'out': figure(churn['left'], num(churn['left']), 'left'),
                     'stay': figure(churn['stayed'], num(churn['stayed']), 'stayed'),
                     'turn': figure(turn, pct(turn, 0), 'of seats changing hands in a year'),
                     'ever': figure(d['ever'], num(d['ever']), 'people listed at all'),
                     'all4': figure(len(d['served_all']), num(len(d['served_all'])),
                                    'who served all four years')},
            figure='turn',
            kind='measured',
            bearing='sizes',
            basis='Names matched between consecutive years of the listing, FY%s to FY%s.'
                  % (d['years'][0], last),
            not_shown='Why anybody left. A term ending, a resignation and a move out of '
                      'town look identical here.',
            so_what='Keeping the boards staffed is a recurring job, not a solved one.',
            allow=('FY%s' % str(int(last) - 1), 'FY%s' % last),
        ),
        conclusion(
            id='churn-is-uneven',
            claim='Some boards replace half their seats a year while others barely change',
            lede='The town-wide turnover figure hides a wide spread: the churn is not '
                 'shared evenly across the boards.',
            detail='Across %s boards of three seats or more, the median is %s of seats '
                   'changing hands a year. %s runs highest at %s; %s is among the '
                   'steadiest at %s.'
                   % (num(len(d['body_big'])), pct(_med(d), 0), d['body_big'][0]['post'],
                      pct(d['body_big'][0]['churn'], 0), d['body_big'][-1]['post'],
                      pct(d['body_big'][-1]['churn'], 0)),
            figures={'n': figure(len(d['body_big']), num(len(d['body_big'])), 'boards'),
                     'med': figure(_med(d), pct(_med(d), 0),
                                   'of seats changing hands a year, the median board'),
                     'hi': figure(d['body_big'][0]['churn'],
                                  pct(d['body_big'][0]['churn'], 0), 'at the top'),
                     'lo': figure(d['body_big'][-1]['churn'],
                                  pct(d['body_big'][-1]['churn'], 0), 'at the bottom')},
            figure='med',
            kind='measured',
            bearing='sizes',
            basis='Names matched between consecutive years of the listing, per body, over '
                  'bodies appearing in both years of at least two pairs.',
            not_shown='Why any board turns over faster. A board people leave and a board '
                      'whose terms are short look identical here.',
            so_what='A seat is far easier to get on some boards than on others.',
            allow=(),
        ),
        conclusion(
            id='fire-doubled',
            claim='The Fire Department doubled its career staff while its on-call roll shrank',
            lede='The one department that states its staffing the same way every year, and '
                 'it has changed a great deal.',
            detail='Career firefighters went from %s in FY%s to %s by FY%s. Over the same '
                   'period the on-call and per-diem roll fell from %s–%s to %s–%s. The '
                   'department states both figures in the prose of its own report, and '
                   'nothing else in the annual report counts them.'
                   % (num(d['fire'][0]['career']), d['fire'][0]['fy'],
                      num(d['fire'][-1]['career']), d['fire'][-1]['fy'],
                      num(d['fire'][0]['on_call_low']), num(d['fire'][0]['on_call_high']),
                      num(d['fire'][-1]['on_call_low']), num(d['fire'][-1]['on_call_high'])),
            figures={'was': figure(d['fire'][0]['career'], num(d['fire'][0]['career']),
                                   'career firefighters at the start'),
                     'now': figure(d['fire'][-1]['career'], num(d['fire'][-1]['career']),
                                   'career firefighters now'),
                     'clo': figure(d['fire'][0]['on_call_low'],
                                   num(d['fire'][0]['on_call_low']), 'on call, low end'),
                     'chi': figure(d['fire'][0]['on_call_high'],
                                   num(d['fire'][0]['on_call_high']), 'on call, high end'),
                     'nlo': figure(d['fire'][-1]['on_call_low'],
                                   num(d['fire'][-1]['on_call_low']), 'on call now, low'),
                     'nhi': figure(d['fire'][-1]['on_call_high'],
                                   num(d['fire'][-1]['on_call_high']), 'on call now, high')},
            figure='now',
            kind='measured',
            bearing='sizes',
            basis='The Fire Department\u2019s own staffing sentence in each annual report, '
                  'FY%s to FY%s.' % (d['fire'][0]['fy'], d['fire'][-1]['fy']),
            not_shown='Hours. A career post and an on-call post are not the same job, and '
                      'the report gives no FTE for either, so the two cannot be netted.',
            so_what='A department can grow and shrink at the same time, in different kinds of staff.',
            allow=('FY%s' % d['fire'][0]['fy'], 'FY%s' % d['fire'][-1]['fy']),
        ),
        conclusion(
            id='not-a-clique',
            claim='It is not a small group wearing many hats — almost everyone holds one seat',
            lede='A common assumption about small-town boards, and this listing does not '
                 'support it.',
            detail='%s distinct people hold the %s posts listed in FY%s. %s of them hold '
                   'more than one, and none holds more than two.'
                   % (num(d['distinct']), num(d['held']), last, num(len(d['multi']))),
            figures={'people': figure(d['distinct'], num(d['distinct']), 'distinct people'),
                     'posts': figure(d['held'], num(d['held']), 'posts listed'),
                     'multi': figure(len(d['multi']), num(len(d['multi'])),
                                     'holding more than one')},
            figure='people',
            kind='measured',
            bearing='sizes',
            basis='Distinct names against rows in the FY%s listing.' % last,
            not_shown='Anything about influence. Holding one seat and holding two says '
                      'nothing about what either person decides.',
            so_what='The work is spread across many residents rather than concentrated in a few.',
            allow=('FY%s' % last,),
        ),
    ])


def render(d):
    years, last = d['years'], d['last']
    t = ['# Who runs the town\n',
         '\nEvery elected seat, appointed board seat and appointed officer the town '
         'prints, FY%s to FY%s — where the empty ones are, when they come open, and how '
         'often they change hands.\n' % (years[0], last)]

    t.append('\n## Where you could serve\n\nSeats the town printed as empty in FY%s.\n\n'
             '| board or committee | empty seats |\n|---|---:|\n' % last)
    for post, n in sorted(d['vacancies'].items(), key=lambda a: (-a[1], a[0])):
        t.append('| %s | %s |\n' % (post, num(n)))
    t.append('| **total** | **%s** |\n' % num(sum(d['vacancies'].values())))

    t.append('\n## When a seat comes open\n\nThe year each filled seat’s term runs '
             'out, as printed beside the name.\n\n| term runs out | seats |\n|---|---:|\n')
    for y in sorted(d['terms']):
        t.append('| %s | %s |\n' % (y, num(d['terms'][y])))

    t.append('\n## How often seats change hands\n\n| | %s |\n|---|%s\n'
             % (' | '.join('FY%s' % c['fy'] for c in d['churn']),
                '---:|' * len(d['churn'])))
    for key, label in (('stayed', 'stayed from the year before'),
                       ('arrived', 'new that year'), ('left', 'gone from the year before')):
        t.append('| %s | %s |\n' % (label, ' | '.join(num(c[key]) for c in d['churn'])))
    t.append('\n%s of the %s people listed at any point across the four years appear in '
             'all four.\n' % (num(len(d['served_all'])), num(d['ever'])))

    if d['body_big']:
        med = sorted(b['churn'] for b in d['body_big'])[len(d['body_big']) // 2]
        t.append('\n## Which boards change most\n\nSeats changing hands each year, over '
                 'bodies of three seats or more that appear in both years of at least two '
                 'consecutive pairs. A one-seat post whose holder changed reads as a '
                 'hundred per cent and is one person leaving a job, so it is left out. The '
                 'median across the %s bodies here is %s.\n\n'
                 '| board or committee | seats | year pairs | churn |\n|---|---:|---:|---:|\n'
                 % (num(len(d['body_big'])), pct(med, 0)))
        for b in d['body_big']:
            t.append('| %s | %s | %s | %s |\n'
                     % (b['post'], b['seats'], b['pairs'], pct(b['churn'], 0)))
    if d['fire']:
        a, b = d['fire'][0], d['fire'][-1]
        t.append('\n## What the departments say about their own staffing\n\n'
                 'Not the same quantity as the listing above, and not addable to it: this '
                 'is what a department says it EMPLOYS, written in the prose of its own '
                 'report. No heading names it in any year.\n')
        t.append('\n### The Fire Department, year by year\n\n'
                 '| fiscal year | career | on call | page |\n|---|---:|---:|---:|\n')
        for r in d['fire']:
            t.append('| FY%s | %s | %s–%s | %s |\n'
                     % (r['fy'], r['career'], r['on_call_low'], r['on_call_high'],
                        r['page']))
        t.append('\nCareer firefighters went from %s to %s while the on-call roll fell '
                 'from %s–%s to %s–%s.\n'
                 % (a['career'], b['career'], a['on_call_low'], a['on_call_high'],
                    b['on_call_low'], b['on_call_high']))
        est = [r for r in d['staffing'] if 'establishment' in r['measure']]
        if est:
            t.append('\n### Stated post by post\n\n| fiscal year | department | as '
                     'printed |\n|---|---|---|\n')
            for r in est:
                t.append('| FY%s | %s | %s |\n'
                         % (r['fy'], r['department'], r['positions']))
            t.append('\nRead carelessly the Department of Public Works loses two heavy '
                     'equipment operators between those two years. It does not: FY2024 '
                     'prints `3 Heavy Equipment Operators, 2 Driver/Laborers` where FY2023 '
                     'printed `5 Heavy Equipment Operators`. Same five people, two titles '
                     'reclassified — which is why the sentence is stored as printed.\n')
    t.append('\n## The bodies, by size\n\nFY%s, filled seats only.\n\n'
             '| board, committee or post | people |\n|---|---:|\n' % last)
    for post, n in sorted(d['sizes'].items(), key=lambda a: (-a[1], a[0])):
        t.append('| %s | %s |\n' % (post, num(n)))

    t.append('\n## The posts\n\n| | %s |\n|---|%s\n'
             % (' | '.join('FY%s' % y for y in years), '---:|' * len(years)))
    for key, label, gloss in KINDS:
        t.append('| %s — %s | %s |\n'
                 % (label, gloss, ' | '.join(str(d['per'][(y, key)]) for y in years)))

    t.append('\n## What this cannot show\n\n')
    for n in _not_established():
        t.append('- %s\n' % n)
    t.append('\n## How well we read it\n\nMost headings state their own membership, so '
             'the page checks itself: %s rows sit under a board where the stated size and '
             'the printed names agree, %s where they differ, and %s under a post that '
             'states no size. A difference is a vacancy, a mid-year replacement printed '
             'beside the person it replaced, or our reading of a page set in two columns '
             '— and this is a note about our extraction rather than about the town.\n'
             % (num(d['checks']['checked']), num(d['checks']['check failed']),
                num(d['checks']['no check'])))
    t.append('\n## Where it comes from\n\n')
    for s_ in _sources(d):
        t.append('- **%s** — %s. %s\n' % (s_['what'], s_['where'], s_['note']))
    return ''.join(t)


def payload(d):
    last = d['last']
    vac = sum(d['vacancies'].values())
    churn = d['churn'][-1]
    turn = (churn['arrived'] + churn['left']) / 2.0 / d['held'] * 100
    return dict(
        generated_by='scripts/build_town_personnel.py',
        about='Every elected seat, appointed board seat and appointed officer the town '
              'prints — where the empty ones are, when they come open, and how often '
              'they change hands.',
        grain='POSTS IN THE LISTING, not people employed. One row is one named holder of '
              'one post in one year, or one empty seat the town printed. A DPW labourer '
              'or a town hall clerk holds no appointed post and is not here.',
        stats=[
            dict(value=num(vac), tone='var(--series-cost)',
                 label='seats the town printed EMPTY in FY%s, across %s boards'
                       % (last, num(len(d['vacancies'])))),
            dict(value=num(d['terms'][d['ahead'][0]]) if d['ahead'] else '—',
                 label='seats whose term runs out in %s — the next chance to join'
                       % (d['ahead'][0] if d['ahead'] else '')),
            dict(value=pct(turn, 0),
                 label='of seats changing hands in a single year'),
        ],
        years=d['years'], last=last,
        counts=[dict(fy=y, **{k: d['per'][(y, k)] for k, _l, _g in KINDS})
                for y in d['years']],
        vacancies=[dict(post=p, seats=n)
                   for p, n in sorted(d['vacancies'].items(), key=lambda a: (-a[1], a[0]))],
        terms=[dict(year=y, seats=d['terms'][y]) for y in sorted(d['terms'])],
        churn=d['churn'],
        sizes=[dict(post=p, people=n)
               for p, n in sorted(d['sizes'].items(), key=lambda a: (-a[1], a[0]))],
        distinct=d['distinct'], held=d['held'],
        multi=[dict(person=n, posts=c) for n, c in d['multi']],
        served_all=len(d['served_all']), ever=d['ever'],
        checks=dict(d['checks']),
        posts=sorted(d['posts'].values(), key=lambda p: p['post']),
        body_churn=d['body_big'],
        fire=d['fire'],
        staffing=[r for r in d['staffing'] if 'establishment' in r['measure']],
        sources=_sources(d),
        not_established=_not_established(),
        conclusions=conclusions_for(d),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    d = load()
    files = {OUT: render(d),
             PAYLOAD: json.dumps(payload(d), indent=1, ensure_ascii=False,
                                 sort_keys=True) + '\n'}
    if a.check:
        stale = [os.path.basename(p) for p, want in files.items()
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else '') != want]
        if stale:
            print('STALE %s' % ', '.join(sorted(stale)), file=sys.stderr)
            return 1
        print('town-personnel is current')
        return 0
    for p, want in files.items():
        open(p, 'w', encoding='utf-8').write(want)
    print('wrote %s and %s'
          % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
