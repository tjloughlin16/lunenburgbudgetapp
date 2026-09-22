#!/usr/bin/env python3
"""Who works for the town: the posts somebody is hired into, and what each department says.

    python3 scripts/build_town_personnel.py
    python3 scripts/build_town_personnel.py --check

Writes `sources/analyses/town-personnel.md` and `fy28/public/data/town-personnel.json`.

TJ, 22 September 2026: *"I want a separate report about the paid personel though which i
think town-personnel should be for."* This is that half. The seats people volunteer for
are `board-composition`; the ones going spare are `open-seats`.

WHAT `PAID` MEANS HERE, and the honest limit on it. The listing never states a salary, so
nothing on this page is read off a payroll. What it does state is a distinction the town
itself draws: a post that says how it is constituted -- `(5 members) 3 year term` -- is a
seat on a body, and a post that says nothing of the kind -- `DPW DIRECTOR`, `TOWN
ACCOUNTANT`, `FIRE CHIEF` -- is a post somebody is appointed or hired into. That is the
line this page follows, and where it is a proxy for `paid` it is a good one and still a
proxy.

THE THREE THINGS THE TOWN PUBLISHES ABOUT ITS STAFF, in descending order of how much they
tell you and ascending order of how many departments they cover:

  1. A NAMED ROSTER. Police and Fire, by rank and assignment, and the SCHOOLS, per
     school, in every annual report from FY2011 -- those are read by a different
     extractor and live in `staff-roster-counts.csv`.
  2. A STATED STRENGTH. Fire gives a count and a range in prose; the DPW gives an
     establishment post by post; the Building Department gives a list of names.
  3. AN APPOINTED POST IN THE LISTING. Every department has these, and they are the
     directors and inspectors rather than the people who do the work.

Nothing published covers the rest -- a DPW labourer, a library assistant, a town hall
clerk appear in none of the three. The gross-wages list tagged each name with a department
through FY2016 and stopped.
"""
import argparse
import collections
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import town_personnel_data as T                                  # noqa: E402
from conclusions import conclusion, emit, figure, num, pct       # noqa: E402

OUT = os.path.join(ROOT, 'sources', 'analyses', 'town-personnel.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'town-personnel.json')


def _sources(d):
    return [
        dict(what='Every appointed post and its holder, FY%s to FY%s'
                  % (d['years'][0], d['years'][-1]),
             where='the APPOINTED OFFICIALS listing in each annual town report',
             basis='published',
             note='Read by scripts/extract_personnel.py. A post that states no membership '
                  'and no term is an officer rather than a board seat — the town’s own '
                  'distinction, not ours.'),
        dict(what='What each department says it employs',
             where='the prose of each department’s own report; no heading names it in any '
                   'year',
             basis='published',
             note='Read by scripts/extract_department_staffing.py. Stored as printed, '
                  'because the forms do not agree with each other and may not be summed.'),
        dict(what='The Police and Fire rosters, by name',
             where='the Police `Department Personnel` and Fire `Roster of the Lunenburg '
                   'Fire Department` pages, both set in two columns',
             basis='published',
             note='Read by scripts/extract_department_rosters.py, from the WORD geometry '
                  'because a line box spans both columns.'),
    ]


def _not_established():
    return [
        'What anybody is paid. No salary is read here, and none is inferred from a post’s '
        'name.',
        'How many people the town employs. A DPW labourer, a library assistant and a town '
        'hall clerk hold no appointed post and appear in no roster — the wage list that '
        'would give a headcount stopped naming departments after FY2016.',
        'FTE. A career post and an on-call post are not the same job and cannot be netted '
        'against each other.',
        'A town total. The departments that describe their staffing do it in whichever '
        'form that year’s department head chose — a count, a range, an establishment post '
        'by post, a list of names — and those are different quantities.',
    ]


def conclusions_for(d):
    last = d['last']
    pub = d['publishes']
    officers = d['per'][(last, 'appointed officer')]
    named = [p for p in pub if 'a named roster' in p['forms']]
    return emit('town-personnel', [
        conclusion(
            id='three-of-them',
            claim='Three parts of the town name their staff. Every other department names none',
            lede='What the town publishes about who works for it, taken as a whole rather '
                 'than one department at a time.',
            detail='Three parts of the town — the Police Department, the Fire Department '
                   'and the schools — print every member of staff by name, in every annual '
                   'report. No other department does. The Department of Public Works states an establishment post by '
                   'post instead, and the rest state nothing at all — so of the %s '
                   'appointed posts the town lists in FY%s, most belong to departments '
                   'whose staff appear in no published count.'
                   % (num(officers), last),
            figures={'named': figure(len(named), 'Three',
                                     'parts of the town naming their staff'),
                     'posts': figure(officers, num(officers),
                                     'appointed posts the town lists')},
            figure='named',
            kind='measured',
            bearing='sizes',
            basis='Every department report in the annual reports, read for a roster, a '
                  'stated strength or an establishment.',
            not_shown='Whether an unnamed department is large or small. Publishing nothing '
                      'is not evidence of either.',
            so_what='Most of the town’s workforce appears in no published count at all.',
            allow=('FY%s' % last,),
        ),
        conclusion(
            id='four-forms',
            claim='What the town says about its staff comes in four forms that cannot be added',
            lede='Not a single figure anywhere: four different kinds of quantity, chosen '
                 'department by department.',
            detail='A named roster, a stated strength given as a count and a RANGE, an '
                   'establishment listed post by post, and a sentence with no number in '
                   'it. Those are four different quantities and no arithmetic joins them, '
                   'so this project publishes no town staffing total and there is no '
                   'honest way to produce one from what is printed.',
            figures={'forms': figure(4, 'four', 'kinds of quantity, none addable to another')},
            figure='forms',
            kind='measured',
            bearing='sizes',
            basis='The form each department uses in its own annual-report section.',
            not_shown='A town headcount. It is not that nobody has added these up; it is '
                      'that adding them would be wrong.',
            so_what='Anybody quoting one town staffing number is quoting something nobody published.',
            allow=(),
        ),
    ])


def latest_both(d):
    """The most recent year where the Fire Department BOTH states a strength and prints a
    roster, because only such a year can compare the two.

    The last year of each series is not the same year: FY2025 states a strength and has no
    roster read yet. Taking `fire[-1]` and looking for its roster returned nothing and the
    conclusion would have published `the roster names 0 firefighters` -- a collapse, from
    a join that missed."""
    both = [r for r in d['roster']
            if r['department'] == 'Fire Department' and r['agrees']]
    return max(both, key=lambda r: r['fy']) if both else None


def render(d):
    years, last = d['years'], d['last']
    t = ['# Who works for the town\n',
         '\nWhat the town publishes about the people who work for it, FY%s to FY%s. The '
         'seats people volunteer for are [board composition](/analysis/board-composition); '
         'the ones going spare are [open seats](/analysis/open-seats).\n'
         % (years[0], last)]

    t.append('\n## What each part of the town publishes\n\nFour different kinds of '
             'quantity, chosen department by department, and none of them addable to '
             'another.\n\n| part of the town | what it publishes |\n|---|---|\n')
    for p_ in d['publishes']:
        t.append('| %s | %s |\n' % (p_['department'], '; '.join(p_['forms'])))
    t.append('| every other department | nothing |\n')
    t.append('\nThat last row is most of the town. A DPW labourer, a library assistant and '
             'a town hall clerk hold no appointed post and appear in no roster, and the '
             'gross-wages list that once tagged each name with a department stopped doing '
             'so after FY2016.\n')

    t.append('\n## The appointed posts\n\nPosts that state no membership and no term: the '
             'directors, chiefs, inspectors and clerks the town appoints rather than '
             'elects. These are posts, not people employed — a department of twenty may '
             'appear here once.\n\n| | %s |\n|---|%s\n'
             % (' | '.join('FY%s' % y for y in years), '---:|' * len(years)))
    t.append('| appointed posts | %s |\n'
             % ' | '.join(str(d['per'][(y, 'appointed officer')]) for y in years))

    est = [r for r in d['staffing'] if 'establishment' in r['measure']]
    if est:
        t.append('\n## Stated post by post\n\nThe Department of Public Works is the only '
                 'department that lists its establishment in prose.\n\n'
                 '| fiscal year | department | as printed |\n|---|---|---|\n')
        for r in est:
            t.append('| FY%s | %s | %s |\n' % (r['fy'], r['department'], r['positions']))
        t.append('\nRead carelessly it loses two heavy equipment operators between those '
                 'two years. It does not: FY2024 prints `3 Heavy Equipment Operators, 2 '
                 'Driver/Laborers` where FY2023 printed `5 Heavy Equipment Operators`. '
                 'Same five people, two titles reclassified — which is why the sentence is '
                 'stored as printed.\n')

    t.append('\n## The named rosters\n\nPolice and Fire list their staff by rank and '
             'assignment. The schools list theirs per school, read by a different '
             'extractor into `staff-roster-counts.csv`.\n\n'
             '| fiscal year | department | names read |\n|---|---|---:|\n')
    for r in d['roster']:
        t.append('| FY%s | %s | %s |\n' % (r['fy'], r['department'], num(r['named'])))
    t.append('\nTHESE COUNTS RUN SHORT AND THE SHORTFALL IS OURS. This page said for a day '
             'that the book counted the Fire Department twice and disagreed with itself — '
             'a serious thing to publish about somebody’s accounts, and wrong. The rosters '
             'are set in two columns, and on FY2023 page 94 the right-hand column of the '
             'call-firefighter list is simply absent from the line-level reading; the '
             'word-level pass has it. The names were printed and we did not read them. '
             'Where a department also states a strength, that is the better figure.\n')
    t.append('\nThe Fire Department states its own strength every year, and what has '
             'happened to it is on [Protection of persons & property]'
             '(/analysis/town-budget-protection), beside the money.\n')

    t.append('\n## What this cannot show\n\n')
    for n in _not_established():
        t.append('- %s\n' % n)
    t.append('\n## Where it comes from\n\n')
    for s_ in _sources(d):
        t.append('- **%s** — %s. %s\n' % (s_['what'], s_['where'], s_['note']))
    return ''.join(t)


def payload(d):
    last, fire = d['last'], d['fire']
    officers = d['per'][(last, 'appointed officer')]
    return dict(
        generated_by='scripts/build_town_personnel.py',
        about='The posts the town hires or appoints somebody into, and what each '
              'department says it employs.',
        grain='POSTS AND NAMED STAFF, never a payroll. One row is one appointed post, or '
              'one person named on a department roster. No salary is read or inferred.',
        stats=[
            dict(value='3', tone='var(--series-cost)',
                 label='parts of the town that name their staff: Police, Fire and the '
                       'schools — every other department names none'),
            dict(value=num(officers),
                 label='appointed posts in FY%s — directors, chiefs, inspectors, clerks'
                       % last),
            # THREE, NOT TWO. TJ: *"this cant be true. schools publish too"* -- and they
            # do, per school, in every annual report FY2011 to FY2025, already extracted
            # into staff-roster-counts.csv. Counting only the two this page happens to
            # read was counting our own attention and publishing it as the town's habit.
            dict(value='four',
                 label='kinds of quantity the town publishes about staffing, none of them '
                       'addable to another'),
        ],
        years=d['years'], last=last,
        fire=fire, roster=d['roster'], publishes=d['publishes'],
        staffing=[r for r in d['staffing'] if 'establishment' in r['measure']],
        officers=[dict(fy=y, officers=d['per'][(y, 'appointed officer')])
                  for y in d['years']],
        sources=_sources(d),
        not_established=_not_established(),
        conclusions=conclusions_for(d),
    )


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
        print('town-personnel is current')
        return 0
    for p, want in files.items():
        open(p, 'w', encoding='utf-8').write(want)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
