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
    emp = d['employers']
    big, rest = emp[0], emp[1:]
    others = sum(e['people'] for e in rest)
    grew = [e for e in emp if e['change'] > 0]
    shrank = [e for e in emp if e['change'] < 0]
    return emit('town-personnel', [
        conclusion(
            id='schools-are-the-employer',
            claim='The schools employ more people than the rest of the town put together, six times over',
            lede='Before any question about who is growing: this is the scale of the '
                 'town’s workforce, and one part of it is nearly all of it.',
            detail='The schools name %s members of staff in FY%s. Every other part of the '
                   'town that publishes a count — the Fire Department, the Police '
                   'Department and the Department of Public Works — comes to %s between '
                   'them.'
                   % (num(big['people']), big['last_fy'], num(others)),
            figures={'schools': figure(big['people'], num(big['people']),
                                       'school staff, named'),
                     'others': figure(others, num(others),
                                      'in every other department that publishes a count')},
            figure='schools',
            kind='measured',
            bearing='sizes',
            basis='The per-school staff rosters in the annual report, against the Fire and '
                  'Police rosters and the DPW establishment.',
            not_shown='The departments that publish nothing. Their staff are in no count '
                      'here and their absence is not a small number.',
            so_what='A conversation about town staffing is mostly a conversation about the schools.',
            allow=('FY%s' % big['last_fy'],),
        ),
        conclusion(
            id='who-grew-who-cut',
            claim='One department has fewer people than it did. The rest are flat or larger',
            lede='Who added staff and who lost it, over the years each one publishes.',
            detail='The Fire Department is down %s, from %s to %s, all of it in the on-call '
                   'roll while its career staff doubled. The schools are up %s since '
                   'FY%s, the Police Department up %s, and the Department of Public Works '
                   'unchanged at %s posts.'
                   % (num(abs(shrank[0]['change'])), num(shrank[0]['first']),
                      num(shrank[0]['people']), num(grew[0]['change']),
                      grew[0]['first_fy'], num(grew[1]['change']),
                      num(emp[-1]['people'])),
            figures={'fire': figure(abs(shrank[0]['change']), num(abs(shrank[0]['change'])),
                                    'fewer at the Fire Department'),
                     'was': figure(shrank[0]['first'], num(shrank[0]['first']), 'then'),
                     'now': figure(shrank[0]['people'], num(shrank[0]['people']), 'now'),
                     'sch': figure(grew[0]['change'], num(grew[0]['change']),
                                   'more school staff'),
                     'pol': figure(grew[1]['change'], num(grew[1]['change']),
                                   'more police officers'),
                     'dpw': figure(emp[-1]['people'], num(emp[-1]['people']),
                                   'posts at the DPW, unchanged')},
            figure='fire',
            kind='measured',
            bearing='sizes',
            basis='Each department’s own published count, first published year against '
                  'last, with any year reading under half its predecessor dropped as a '
                  'short read rather than a cut.',
            not_shown='Hours or FTE. A call firefighter and a classroom teacher are one '
                      'person each here.',
            so_what='Only one part of the town has visibly shed people, and not the part usually named.',
            allow=('FY%s' % grew[0]['first_fy'],),
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
    emp = d['employers']
    sd = d['school_detail']
    t = ['# Who works for the town\n',
         '\nHow many people each part of the town employs, which are growing and which '
         'have shed staff. The seats people volunteer for are '
         '[board composition](/analysis/board-composition).\n']

    t.append('\n## How many people each part of the town employs\n')
    t.append('\n![Bars, one per part of the town that publishes a staff count. The school '
             'bar is far longer than the rest put together.]'
             '(charts/town-personnel-employers.svg)\n')
    t.append('\n| part of the town | people | as of | first published | change | what it counts |\n'
             '|---|---:|---|---:|---:|---|\n')
    for e in emp:
        t.append('| %s | %s | FY%s | %s in FY%s | %s%s | %s |\n'
                 % (e['department'], num(e['people']), e['last_fy'], num(e['first']),
                    e['first_fy'], '+' if e['change'] >= 0 else '\u2212',
                    num(abs(e['change'])), e['kind']))
    t.append('\nThese are not identical measures — a named roster, a career count plus the '
             'low end of an on-call range, and an establishment of posts — and they are all '
             'answers to how many people work here. Where a department states a range the '
             'LOW end is used, so none is flattered by its own vagueness.\n')
    susp = [e for e in emp if e['suspect']]
    if susp:
        t.append('\nA year whose count reads under half the year before it is dropped as a '
                 'short read rather than published as a cut: %s. The Police roster comes '
                 'back as seven officers in FY2024 against twenty-five in FY2023, which is '
                 'a page this reader did not find, not three quarters of a police force.\n'
                 % '; '.join('%s FY%s' % (e['department'], ', FY'.join(e['suspect']))
                             for e in susp))

    if sd['by_school']:
        t.append('\n## The schools, in detail\n\nSix times the next employer, so worth '
                 'breaking out. FY%s.\n\n| school | staff |\n|---|---:|\n' % sd['fy'])
        for r in sd['by_school']:
            t.append('| %s | %s |\n' % (r['school'].replace('-', ' ').title(), num(r['people'])))
        t.append('\n| what they do | staff |\n|---|---:|\n')
        for r in sd['by_position'][:12]:
            t.append('| %s | %s |\n' % (r['position'], num(r['people'])))

    t.append('\n## Who publishes nothing\n\nEvery other department. A DPW labourer '
             'appears because the DPW states an establishment; a library assistant, a town '
             'hall clerk, an assessor’s clerk and a Council on Aging driver appear in no '
             'published count at all. The gross-wages list named a department beside each '
             'employee through FY2016 and stopped, so there has been no town-wide headcount '
             'by department since.\n')

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
            dict(value=num(d['employers'][0]['people']),
                 label='school staff — more people than the rest of the town put '
                       'together, six times over'),
            dict(value=num(sum(e['people'] for e in d['employers'][1:])),
                 label='in every other part of the town that publishes a count: Fire, '
                       'Police and the DPW'),
            dict(value='%s of %s' % (num(len(d['employers'])), num(len(d['sizes']))),
                 tone='var(--series-cost)',
                 label='parts of the town that publish any staff count at all'),
        ],
        years=d['years'], last=last,
        fire=fire, roster=d['roster'], publishes=d['publishes'],
        employers=d['employers'], school_detail=d['school_detail'],
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
