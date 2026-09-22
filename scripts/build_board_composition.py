#!/usr/bin/env python3
"""Board composition: how the town's boards are made up, and how they turn over.

    python3 scripts/build_board_composition.py
    python3 scripts/build_board_composition.py --check

Writes `sources/analyses/board-composition.md` and
`fy28/public/data/board-composition.json`.

TJ, 22 September 2026: *"town-personnel is focused on the volunteers. that should be a
separate for under 'the boards, compared'. Basically, 'board composition'."*

WHAT THIS PAGE IS FOR, and what it deliberately is not. It is about how the boards BEHAVE:
which are big, which turn over, whether the establishment is growing. It is the companion
to `boards/compared`, which measures what each board POSTS.

It is not the place to look for a seat. That is `open-seats`, which is a list rather than
a report because somebody reads it and then does something. This page would bury the one
actionable table under four charts, which is how a page ends up useful to nobody.

THE FINDING THE CHARTS EXIST FOR. Seats and people move differently. The establishment is
nearly flat across ten years -- elected seats, appointed seats and officers all sit within
a narrow band -- while about a third of the PEOPLE in them change every year. Neither
number shows it alone, and the town-wide churn figure hides a further spread: some boards
replace half their seats a year and others have not changed at all.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import town_personnel_data as T                                 # noqa: E402
from conclusions import conclusion, emit, figure, num, pct      # noqa: E402

OUT = os.path.join(ROOT, 'sources', 'analyses', 'board-composition.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'board-composition.json')

KINDS = [('elected board seat', 'Elected seats', 'filled by the voters'),
         ('appointed board seat', 'Appointed board seats', 'filled by the Select Board')]


def _med(d):
    b = sorted(x['churn'] for x in d['body_big'])
    return b[len(b) // 2]


def _sources(d):
    return [dict(
        what='Every board and committee, its members and their term-expiry years, FY%s to '
             'FY%s' % (d['years'][0], d['years'][-1]),
        where='the ELECTED OFFICIALS and APPOINTED OFFICIALS listing in each annual town '
              'report — nine pages a year',
        basis='published',
        note='Read by scripts/extract_personnel.py. The format is not the same every year: '
             'the elected pages set headings in title case and the appointed pages in '
             'capitals, two or three pages a year are set in two columns, and five years '
             'print the section under no running header at all.')]


def _not_established():
    return [
        'Why anybody left a board. A term ending, a resignation and a move out of town '
        'look identical here.',
        'Whether a seat sat empty between one holder and the next.',
        'Hours, or what a seat asks of the person in it.',
        'Anything about pay. This listing never states it, and no salary is inferred here '
        'from a post’s name.',
    ]


def conclusions_for(d):
    last = d['last']
    churn = d['churn'][-1]
    turn = (churn['arrived'] + churn['left']) / 2.0 / d['held'] * 100
    big = d['body_big'][0]
    small = d['body_big'][-1]
    return emit('board-composition', [
        conclusion(
            id='seats-flat-people-not',
            claim='The number of seats has barely moved in ten years. Who sits in them has',
            lede='Two trends that look like one number until they are drawn: a stable '
                 'establishment, and a population turning over inside it.',
            detail='Elected seats and appointed board seats are both close to flat '
                   'across FY%s to FY%s. Underneath that, %s people arrived and %s left in '
                   'the last year alone, out of %s posts.'
                   % (d['years'][0], last, num(churn['arrived']), num(churn['left']),
                      num(d['held'])),
            figures={'in': figure(churn['arrived'], num(churn['arrived']),
                                  'arrived in a single year'),
                     'out': figure(churn['left'], num(churn['left']), 'left'),
                     'posts': figure(d['held'], num(d['held']), 'posts in total')},
            figure='in',
            kind='measured',
            bearing='sizes',
            basis='Posts by kind for each of the ten years, against names matched between '
                  'consecutive years.',
            not_shown='Whether a seat sat empty between one holder and the next.',
            so_what='The town is not adding committees. It is refilling the ones it has.',
            allow=('FY%s' % d['years'][0], 'FY%s' % last),
        ),
        conclusion(
            id='churn-is-uneven',
            claim='Some boards replace half their seats a year while others barely change',
            lede='The town-wide turnover figure hides a wide spread: the churn is not '
                 'shared evenly across the boards.',
            detail='Across %s boards of three seats or more, the median is %s of seats '
                   'changing hands a year. %s runs highest at %s; %s is among the '
                   'steadiest at %s.'
                   % (num(len(d['body_big'])), pct(_med(d), 0), big['post'],
                      pct(big['churn'], 0), small['post'], pct(small['churn'], 0)),
            figures={'n': figure(len(d['body_big']), num(len(d['body_big'])), 'boards'),
                     'med': figure(_med(d), pct(_med(d), 0),
                                   'of seats changing hands a year, the median board'),
                     'hi': figure(big['churn'], pct(big['churn'], 0), 'at the top'),
                     'lo': figure(small['churn'], pct(small['churn'], 0), 'at the bottom')},
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
    ranked = sorted(d['sizes'].items(), key=lambda a: (-a[1], a[0]))
    ones = sum(1 for _p, n in ranked if n == 1)
    churn = d['churn'][-1]
    t = ['# Board composition\n',
         '\nHow the town’s boards are made up, how big they are and how fast they turn '
         'over, FY%s to FY%s. Looking for a seat? That is [open seats]'
         '(/analysis/open-seats).\n' % (years[0], last)]

    t.append('\n## Where the seats are\n')
    t.append('\n![A pie of every filled post in FY%s by body. %s is the largest at %s '
             'people; the ten largest are named and %s smaller bodies and single-holder '
             'posts are grouped together.](charts/board-composition-where.svg)\n'
             % (last, ranked[0][0], num(ranked[0][1]), num(max(len(ranked) - 10, 0))))
    t.append('\n%s is the biggest body in the town at %s seats. %s posts have a single '
             'holder.\n' % (ranked[0][0], num(ranked[0][1]), num(ones)))

    t.append('\n## The seats barely move. The people in them do\n')
    t.append('\n![Two lines over ten fiscal years — elected seats and appointed board '
             'seats. Both are close to flat.](charts/board-composition-over-time.svg)\n')
    t.append('\n| | %s |\n|---|%s\n'
             % (' | '.join('FY%s' % c['fy'] for c in d['churn']),
                '---:|' * len(d['churn'])))
    for key, label in (('stayed', 'stayed from the year before'),
                       ('arrived', 'new that year'), ('left', 'gone from the year before')):
        t.append('| %s | %s |\n' % (label, ' | '.join(num(c[key]) for c in d['churn'])))
    t.append('\n%s of the %s people listed at any point across the ten years appear in all '
             'of them.\n' % (num(len(d['served_all'])), num(d['ever'])))

    t.append('\n## Which boards change most\n\nSeats changing hands each year, over bodies '
             'of three seats or more that appear in both years of at least two consecutive '
             'pairs. A one-seat post whose holder changed reads as a hundred per cent and '
             'is one person leaving a job, so it is left out. The median across the %s '
             'bodies here is %s.\n\n'
             '| board or committee | seats | year pairs | churn |\n|---|---:|---:|---:|\n'
             % (num(len(d['body_big'])), pct(_med(d), 0)))
    for b in d['body_big']:
        t.append('| %s | %s | %s | %s |\n'
                 % (b['post'], b['seats'], b['pairs'], pct(b['churn'], 0)))

    t.append('\n## The bodies, by size\n\nFY%s, filled seats only.\n\n'
             '| board, committee or post | people |\n|---|---:|\n' % last)
    for post, n in ranked:
        t.append('| %s | %s |\n' % (post, num(n)))

    t.append('\n## Seats by kind\n\n| | %s |\n|---|%s\n'
             % (' | '.join('FY%s' % y for y in years), '---:|' * len(years)))
    for key, label, gloss in KINDS:
        t.append('| %s — %s | %s |\n'
                 % (label, gloss, ' | '.join(str(d['per'][(y, key)]) for y in years)))

    t.append('\n## What this cannot show\n\n')
    for n in _not_established():
        t.append('- %s\n' % n)
    t.append('\n## How well we read it\n\nMost headings state their own membership, so the '
             'page checks itself: %s rows sit under a board where the stated size and the '
             'printed names agree, %s where they differ, and %s under a post that states '
             'no size. A difference is a vacancy, a mid-year replacement printed beside '
             'the person it replaced, or our reading of a page set in two columns — a note '
             'about our extraction rather than about the town.\n'
             % (num(d['checks']['checked']), num(d['checks']['check failed']),
                num(d['checks']['no check'])))
    t.append('\n## Where it comes from\n\n')
    for s in _sources(d):
        t.append('- **%s** — %s. %s\n' % (s['what'], s['where'], s['note']))
    return ''.join(t)


def payload(d):
    last = d['last']
    churn = d['churn'][-1]
    turn = (churn['arrived'] + churn['left']) / 2.0 / d['held'] * 100
    ranked = sorted(d['sizes'].items(), key=lambda a: (-a[1], a[0]))
    return dict(
        generated_by='scripts/build_board_composition.py',
        about='How the town’s boards are made up — which are biggest, how fast each turns '
              'over, and whether the establishment is growing.',
        grain='SEATS IN THE LISTING. One row is one named holder of one seat in one year. '
              'Not employees: a post somebody is hired into is on the town personnel '
              'report instead.',
        stats=[
            dict(value=num(ranked[0][1]),
                 label='seats on %s, the largest body in the town' % ranked[0][0]),
            dict(value=pct(turn, 0),
                 label='of seats changing hands in a single year'),
            dict(value='%s of %s' % (num(len(d['multi'])), num(d['distinct'])),
                 label='people holding more than one seat'),
        ],
        years=years_of(d), last=last,
        counts=[dict(fy=y, **{k: d['per'][(y, k)] for k, _l, _g in KINDS})
                for y in d['years']],
        churn=d['churn'], body_churn=d['body_big'],
        sizes=[dict(post=p, people=n) for p, n in ranked],
        multi=[dict(person=n, posts=c) for n, c in d['multi']],
        served_all=len(d['served_all']), ever=d['ever'], checks=dict(d['checks']),
        sources=_sources(d),
        not_established=_not_established(),
        conclusions=conclusions_for(d),
    )


def years_of(d):
    return d['years']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    d = T.load()
    files = {OUT: render(d),
             PAYLOAD: json.dumps(payload(d), indent=1, ensure_ascii=False,
                                 sort_keys=True) + '\n'}
    if a.check:
        stale = [os.path.basename(p) for p, want in files.items()
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else '') != want]
        if stale:
            print('STALE %s' % ', '.join(sorted(stale)), file=sys.stderr)
            return 1
        print('board-composition is current')
        return 0
    for p, want in files.items():
        open(p, 'w', encoding='utf-8').write(want)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
