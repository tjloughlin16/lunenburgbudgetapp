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

  1. A NAMED ROSTER. Police and Fire only, every year, by rank and assignment.
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
    fire = d['fire']
    a, b = fire[0], fire[-1]
    roster = [r for r in d['roster'] if r['agrees']]
    disagree = [r for r in roster if r['agrees'] == 'no']
    cmp_ = latest_both(d)
    return emit('town-personnel', [
        conclusion(
            id='fire-doubled',
            claim='The Fire Department doubled its career staff while its on-call roll shrank',
            lede='The one department that states its staffing the same way every year, and '
                 'it has changed a great deal.',
            detail='Career firefighters went from %s in FY%s to %s by FY%s. Over the same '
                   'period the on-call and per-diem roll fell from %s–%s to %s–%s. The '
                   'department states both in the prose of its own report, and nothing '
                   'else in the annual report counts either.'
                   % (num(a['career']), a['fy'], num(b['career']), b['fy'],
                      num(a['on_call_low']), num(a['on_call_high']),
                      num(b['on_call_low']), num(b['on_call_high'])),
            figures={'was': figure(a['career'], num(a['career']),
                                   'career firefighters at the start'),
                     'now': figure(b['career'], num(b['career']),
                                   'career firefighters now'),
                     'clo': figure(a['on_call_low'], num(a['on_call_low']),
                                   'on call, low end'),
                     'chi': figure(a['on_call_high'], num(a['on_call_high']),
                                   'on call, high end'),
                     'nlo': figure(b['on_call_low'], num(b['on_call_low']),
                                   'on call now, low'),
                     'nhi': figure(b['on_call_high'], num(b['on_call_high']),
                                   'on call now, high')},
            figure='now',
            kind='measured',
            bearing='sizes',
            basis='The Fire Department’s own staffing sentence in each annual report, FY%s '
                  'to FY%s.' % (a['fy'], b['fy']),
            not_shown='Hours. A career post and an on-call post are not the same job and '
                      'the report gives no FTE for either.',
            so_what='A department can grow and shrink at the same time, in different kinds of staff.',
            allow=('FY%s' % a['fy'], 'FY%s' % b['fy']),
        ),
        conclusion(
            id='the-book-disagrees',
            claim='The Fire Department is counted twice in one book and the two counts differ',
            lede='A sentence states the strength and a roster names everybody, a few pages '
                 'apart. They should agree.',
            detail='In FY%s the roster names %s firefighters against a strength the same '
                   'report states as %s to %s. It runs short in %s of the %s years where '
                   'both are printed, so this page shows both rather than averaging them '
                   'into a third figure the town never published.'
                   % (cmp_['fy'], num(cmp_['named']), num(cmp_['stated_low']),
                      num(cmp_['stated_high']), num(len(disagree)), num(len(roster))),
            figures={'named': figure(cmp_['named'], num(cmp_['named']), 'names printed'),
                     'lo': figure(cmp_['stated_low'], num(cmp_['stated_low']),
                                  'stated, low'),
                     'hi': figure(cmp_['stated_high'], num(cmp_['stated_high']),
                                  'stated, high'),
                     'bad': figure(len(disagree), num(len(disagree)), 'years they differ'),
                     'yrs': figure(len(roster), num(len(roster)),
                                   'years where both are printed')},
            figure='bad',
            kind='measured',
            bearing='sizes',
            basis='The named roster against the strength stated in prose, per year.',
            not_shown='Which of the two is right. Either the roster omits people the '
                      'sentence counts, or our reading of it does.',
            so_what='Quote the range, not either end of it.',
            allow=('FY%s' % cmp_['fy'],),
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
    fire = d['fire']
    t = ['# Who works for the town\n',
         '\nThe posts the town hires or appoints somebody into, and what each department '
         'says it employs, FY%s to FY%s. The seats people volunteer for are '
         '[board composition](/analysis/board-composition); the ones going spare are '
         '[open seats](/analysis/open-seats).\n' % (years[0], last)]

    t.append('\n## The Fire Department, the one that states its own strength\n')
    t.append('\n![The Fire Department’s career firefighters as a rising line against the '
             'on-call roll drawn as a band, because the town states it as a range. The two '
             'move in opposite directions.](charts/town-personnel-fire.svg)\n')
    t.append('\n| fiscal year | career | on call | page |\n|---|---:|---:|---:|\n')
    for r in fire:
        t.append('| FY%s | %s | %s–%s | %s |\n'
                 % (r['fy'], r['career'], r['on_call_low'], r['on_call_high'], r['page']))
    t.append('\nCareer firefighters went from %s to %s while the on-call roll fell from '
             '%s–%s to %s–%s.\n'
             % (fire[0]['career'], fire[-1]['career'], fire[0]['on_call_low'],
                fire[0]['on_call_high'], fire[-1]['on_call_low'], fire[-1]['on_call_high']))

    t.append('\n## The two departments that print every name\n\nPolice and Fire list their '
             'staff by name and assignment in every annual report. The Fire Department '
             'also states its strength in a sentence, so the book gives the same quantity '
             'twice — and the two do not agree.\n\n'
             '| fiscal year | department | names printed | strength stated | agree |\n'
             '|---|---|---:|---:|---|\n')
    for r in d['roster']:
        st = ('%s–%s' % (r['stated_low'], r['stated_high'])
              if r['stated_low'] != '' else '—')
        t.append('| FY%s | %s | %s | %s | %s |\n'
                 % (r['fy'], r['department'], num(r['named']), st,
                    {'yes': 'yes', 'no': 'NO', '': '—'}[r['agrees']]))
    t.append('\nThe named roster runs below the stated strength in most years. Either it '
             'omits people the sentence counts, or this reading of it does — and until '
             'that is settled the count to quote is the range, not either end.\n')

    est = [r for r in d['staffing'] if 'establishment' in r['measure']]
    if est:
        t.append('\n## Stated post by post\n\n| fiscal year | department | as printed |\n'
                 '|---|---|---|\n')
        for r in est:
            t.append('| FY%s | %s | %s |\n' % (r['fy'], r['department'], r['positions']))
        t.append('\nRead carelessly the Department of Public Works loses two heavy '
                 'equipment operators between those two years. It does not: FY2024 prints '
                 '`3 Heavy Equipment Operators, 2 Driver/Laborers` where FY2023 printed '
                 '`5 Heavy Equipment Operators`. Same five people, two titles reclassified '
                 '— which is why the sentence is stored as printed.\n')

    t.append('\n## The appointed posts\n\nPosts that state no membership and no term: the '
             'directors, chiefs, inspectors and clerks the town appoints rather than '
             'elects.\n\n| | %s |\n|---|%s\n'
             % (' | '.join('FY%s' % y for y in years), '---:|' * len(years)))
    t.append('| appointed officers | %s |\n'
             % ' | '.join(str(d['per'][(y, 'appointed officer')]) for y in years))

    t.append('\n## What this cannot show\n\n')
    for n in _not_established():
        t.append('- %s\n' % n)
    t.append('\n## Where it comes from\n\n')
    for s in _sources(d):
        t.append('- **%s** — %s. %s\n' % (s['what'], s['where'], s['note']))
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
            dict(value=num(fire[-1]['career']),
                 label='career firefighters in FY%s, from %s in FY%s'
                       % (fire[-1]['fy'], num(fire[0]['career']), fire[0]['fy'])),
            dict(value=num(officers),
                 label='appointed posts in FY%s — directors, chiefs, inspectors, clerks'
                       % last),
            dict(value='2 of %s' % num(len(d['sizes'])), tone='var(--series-cost)',
                 label='departments that publish a named roster: Police and Fire'),
        ],
        years=d['years'], last=last,
        fire=fire, roster=d['roster'],
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
