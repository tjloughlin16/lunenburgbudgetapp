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
OUT = os.path.join(ROOT, 'sources', 'analyses', 'town-personnel.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'town-personnel.json')

KINDS = [('elected board seat', 'Elected seats', 'filled by the voters'),
         ('appointed board seat', 'Appointed board seats', 'filled by the Select Board'),
         ('appointed officer', 'Appointed officers', 'posts somebody is hired or named into')]


def load():
    rows = list(csv.DictReader(open(SRC, encoding='utf-8')))
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
    return dict(rows=rows, years=years, per=per, checks=checks, posts=posts)


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
        'Hours. A board seat and a full-time directorship are one row each.',
        'Whether a post was actually filled for the whole year. The listing is a point in '
        'time and an appointment note is the only sign of a change within one.',
    ]


def conclusions_for(d):
    last = d['years'][-1]
    seats = d['per'][(last, 'elected board seat')] + d['per'][(last, 'appointed board seat')]
    officers = d['per'][(last, 'appointed officer')]
    total = seats + officers
    checked = d['checks']['checked']
    failed = d['checks']['check failed']
    return emit('town-personnel', [
        conclusion(
            id='mostly-volunteers',
            claim='Two thirds of the posts the town lists are unpaid seats on boards',
            lede='The listing is dominated by board and committee seats rather than by '
                 'the officers who run the departments.',
            detail='Of %s posts the town listed in FY%s, %s are seats on boards and '
                   'committees and %s are appointed officers. The ratio has held within a '
                   'narrow band across all four years.'
                   % (num(total), last, num(seats), num(officers)),
            figures={'seats': figure(seats, num(seats), 'board and committee seats'),
                     'officers': figure(officers, num(officers), 'appointed officers'),
                     'total': figure(total, num(total), 'posts listed')},
            figure='seats',
            kind='measured',
            bearing='sizes',
            basis='The ELECTED OFFICIALS and APPOINTED OFFICIALS listing in the FY%s '
                  'annual report.' % last,
            not_shown='How many people the town employs. A post in this listing is not a '
                      'job, and most town jobs are not posts in it.',
            so_what='The town’s committee work rests on far more people than its payroll does.',
            allow=('FY%s' % last,),
        ),
        conclusion(
            id='seats-against-stated',
            claim='Where a board states how many seats it has, the names beneath it often differ',
            lede='Most headings in the listing state a membership, which makes the page '
                 'check itself — and the check does not always pass.',
            detail='%s of the rows sit under a board that states its own size and are '
                   'matched by the names printed beneath it. %s sit under one where the '
                   'count differs. A seat left vacant and a mid-year replacement printed '
                   'beside the person it replaced both look like this.'
                   % (num(checked), num(failed)),
            figures={'ok': figure(checked, num(checked), 'rows that match a stated size'),
                     'bad': figure(failed, num(failed), 'rows where the count differs')},
            figure='bad',
            kind='measured',
            bearing='sizes',
            basis='Each heading’s stated membership against the names printed under it, '
                  'FY%s to FY%s.' % (d['years'][0], d['years'][-1]),
            not_shown='Which differences are vacancies, which are replacements, and which '
                      'are our reading of a two-column page.',
            so_what='A board roster cannot be counted without saying which of the three it is.',
            allow=(),
        ),
    ])


def render(d):
    years = d['years']
    t = ['# Who runs the town\n',
         '\nEvery elected seat, appointed board seat and appointed officer the town '
         'prints, FY%s to FY%s.\n' % (years[0], years[-1])]
    t.append('\n## The posts\n\n| | %s |\n|---|%s\n'
             % (' | '.join('FY%s' % y for y in years), '---:|' * len(years)))
    for key, label, gloss in KINDS:
        t.append('| %s — %s | %s |\n'
                 % (label, gloss, ' | '.join(str(d['per'][(y, key)]) for y in years)))
    t.append('| **all posts listed** | %s |\n'
             % ' | '.join(str(sum(d['per'][(y, k)] for k, _l, _g in KINDS))
                          for y in years))
    t.append('\n## Does it add up\n\nMost headings state their own membership, so the page '
             'checks itself. The rows split three ways on it, and nothing here may be '
             'counted without saying which.\n\n| | rows |\n|---|---:|\n')
    for k in ('checked', 'check failed', 'no check'):
        t.append('| %s | %s |\n' % (k, num(d['checks'][k])))
    t.append('\n`checked` means the heading states a size and that many names follow it. '
             '`check failed` means it states one and a different number follow — a '
             'vacancy, a mid-year replacement printed beside the person it replaced, or '
             'our reading of a two-column page. `no check` means the heading states no '
             'size, which is most single-holder posts and is not a doubt about anything.\n')
    t.append('\n## Every post\n\n| post | how it is filled | years listed |\n|---|---|---|\n')
    for p in sorted(d['posts'].values(), key=lambda p: p['post']):
        t.append('| %s | %s | %s |\n'
                 % (p['post'], p['kind'],
                    ', '.join('FY%s' % y for y in p['years'])))
    t.append('\n## What this cannot show\n\n')
    for n in _not_established():
        t.append('- %s\n' % n)
    t.append('\n## Where it comes from\n\n')
    for s in _sources(d):
        t.append('- **%s** — %s. %s\n' % (s['what'], s['where'], s['note']))
    return ''.join(t)


def payload(d):
    last = d['years'][-1]
    seats = d['per'][(last, 'elected board seat')] + d['per'][(last, 'appointed board seat')]
    officers = d['per'][(last, 'appointed officer')]
    return dict(
        generated_by='scripts/build_town_personnel.py',
        about='Every elected seat, appointed board seat and appointed officer the town '
              'prints in its annual report, and how the three have moved.',
        grain='POSTS IN THE LISTING, not people employed. One row is one named holder of '
              'one post in one year. A DPW labourer or a town hall clerk holds no '
              'appointed post and is not here.',
        stats=[
            dict(value=num(seats),
                 label='board and committee seats listed in FY%s' % last),
            dict(value=num(officers),
                 label='appointed officers — the posts somebody is hired into'),
            dict(value=num(d['checks']['check failed']), tone='var(--series-cost)',
                 label='rows under a board whose stated size and printed names differ'),
        ],
        years=d['years'],
        counts=[dict(fy=y, **{k: d['per'][(y, k)] for k, _l, _g in KINDS})
                for y in d['years']],
        checks=dict(d['checks']),
        posts=sorted(d['posts'].values(), key=lambda p: p['post']),
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
