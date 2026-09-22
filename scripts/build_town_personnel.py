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
from town_budget_data import GROUPS                              # noqa: E402
import town_budget_data as TB                                    # noqa: E402

# WHICH VOTED GROUP EACH DEPARTMENT'S PAYROLL SITS IN. Stated here rather than matched on
# names, because the two vocabularies genuinely differ: the town votes `Protection of
# persons & property` and the reports are written by the Police, the Fire Department and
# the Building Department, none of which contains the word protection.
# WHY A GROUP PUBLISHES NO HEADCOUNT. TJ: *"lets 1) confirm they are stated 'departments'
# and not just categories. and if there are no stated employees, we need to show that on
# the report too. IT for instance i think is outsourced, which might explain THAT"*.
#
# IT turned out NOT to be outsourced -- it names its whole team in four years, in a form
# nothing was reading -- and checking the rest found that the three answers are genuinely
# different, and only one of them is about a department being quiet:
#
#   an office that states no strength   the office exists, writes or is named, says no number
#   bought as a service                 the town buys the service; the people are not its own
#   a category of spending              not a department at all; no report, no staff
#
# Hand-stated, with the evidence beside it, because none of it is derivable: the omnibus
# line labels do not say what kind of thing a group is, and `department_lines` returns
# nothing at all for two of the twelve.
NO_COUNT = {
    'General Government': (
        'offices that state no strength',
        'Holds the Town Manager, Town Accountant, Treasurer, Tax Collector and Town '
        'Clerk, each with its own budget line and none stating a headcount. Two offices '
        'inside it DO: Information Technology — `Information Technology Dept.` in the '
        'omnibus, $402,222 in FY2025 — and the Assessing office.'),
    'Health & Sanitation': (
        'bought as a service',
        'The town’s health agent is the Nashoba Associated Boards of Health, a shared '
        'regional service that writes its own pages inside Lunenburg’s annual report '
        '(pages 72–75 in FY2024). `Nashoba Board of Health` and `Nashoba Nursing` are '
        'budget lines. The only salaried post in the group is `Animal Inspector Salary`, '
        'at $1,000.'),
    'Solid Waste & Recycling': (
        'bought as a service',
        'Collection is contracted out. The town ran ten years with Casella and moved to '
        'E.L. Harvey on 1 July 2021. The group is one line, `Recycling Program`.'),
    'Central Purchasing': (
        'a category of spending',
        'Not a department and there is no report for it. Its lines are Equipment '
        'Maintenance, Postage and Purchase of Service — what town hall buys, gathered '
        'under one heading.'),
    'Employee benefits & reserves': (
        'a category of spending',
        'Liability, workers compensation, group health and life insurance, Medicare, and '
        'the reserve funds. It pays for people who are counted under the department they '
        'work in, and employs nobody itself.'),
    'Maturing Debt & Interest': (
        'a category of spending',
        'Principal and interest on loans. Nobody works here; see the debt schedule.'),
    'Facilities & Grounds': (
        'a department with a budget and no paper trail',
        'Created by a RECORDED VOTE — Article 7 of the 2022 Annual Town Meeting, the '
        '`Administrative Organization Plan` of 5 April 2022, Yes-136 No-28 — which moved '
        'town facilities out from under the DPW Director, where the Town Manager had '
        'delegated them, and gave them a Facilities Director of their own. Since then it '
        'has filed NO annual report: it is on no contents page in FY2023, FY2024 or '
        'FY2025. There is no `Facilities Director` post in the appointed-officials '
        'listing in any year, and the person doing the job appears in that listing once, '
        'as a committee member under a different title. Before FY2023 its people are '
        'inside the DPW’s establishment, which still reads `one Executive Assistant '
        '(shared with Facilities)`.'),
}

BUDGET_GROUP = {
    'Schools': 'Schools',
    'Fire Department': 'Protection of persons & property',
    'Police Department': 'Protection of persons & property',
    'Building Department': 'Protection of persons & property',
    'Department of Public Works': 'Public Works',
    'Facilities Management': 'Facilities & Grounds',
    'Council on Aging': 'Assistance',
    'Board of Assessors': 'General Government',
    'Information Technology': 'General Government',
    'Library': 'Library',
}

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
                  'because the forms do not agree with each other and may not be summed. '
                  '%s forms so far, and the department head chooses: a list of names, an '
                  'establishment post by post, the same establishment written one article '
                  'at a time, a career count beside an on-call range, a number spelled out '
                  'in words, and — the Library’s only one — a headcount in an aside inside '
                  'a sentence about turnover.'
                  % word(len({e['kind'] for e in d['employers']})).capitalize()),
        dict(what='The Police and Fire rosters, by name',
             where='the Police `Department Personnel` and Fire `Roster of the Lunenburg '
                   'Fire Department` pages, both set in two columns',
             basis='published',
             note='Read by scripts/extract_department_rosters.py, from the WORD geometry '
                  'because a line box spans both columns.'),
    ]


TIMES = {2: 'twice', 3: 'three times', 4: 'four times', 5: 'five times',
         6: 'six times', 7: 'seven times', 8: 'eight times'}


def multiple(a, b):
    """How many times over `a` exceeds `b`, in words, never rounded up."""
    n = int(a // b) if b else 0
    return 'more than %s as many' % TIMES.get(n, '%d times' % n) if n >= 2 \
        else 'more'


WORD = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
        'ten', 'eleven', 'twelve']


def word(n):
    return WORD[n] if n < len(WORD) else num(n)


def _common_year(emp):
    """The fiscal year the most departments publish, and how many that is."""
    seen = collections.Counter()
    for e in emp:
        for p in e['series']:
            if not p.get('suspect'):
                seen[p['fy']] += 1
    fy, n = max(sorted(seen.items()), key=lambda kv: kv[1])
    return fy, n


def _not_established(d=None):
    emp = (d or {}).get('employers') or []
    forms = sorted({e['kind'] for e in emp})
    return [
        'What anybody is paid. No salary is read here, and none is inferred from a post’s '
        'name.',
        'How many people the town employs. %s departments state a figure, in %s different '
        'forms, and no year has all of them — the wage list that would give one town-wide '
        'headcount stopped naming departments after FY2016.'
        % (word(len(emp)).capitalize(), word(len(forms))),
        'FTE. A career post and an on-call post are not the same job and cannot be netted '
        'against each other.',
        'Whether a post was CUT. A roster is people IN post and a cut removes a POST, and '
        'those come apart both ways: someone retires and the post sits vacant but funded, '
        'so the count falls and nothing was cut; or a post is eliminated and its holder '
        'moves to another vacancy, so the count holds and something was. The town\u2019s own '
        'words for it are in the Assessing office\u2019s FY2024 report \u2014 \u201cwe are fully '
        'staffed for the first time in over a year\u201d \u2014 a year of posts that existed and '
        'were empty. A rise or a fall here is a change in PEOPLE PRESENT, never a '
        'decision about establishment.',
        'When in the year anybody was counted. A roster is a point in time and is undated '
        'within its year, so a September departure and a June one are the same figure.',
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
            # `six times over` WAS THE RATIO TO THE NEXT EMPLOYER, in a sentence about
            # the rest put together -- two different quantities under one phrase, and the
            # smaller one was the one the sentence named. 250 against 108 is a bit over
            # twice, not six times.
            claim='The schools employ %s people as the rest of the town put together'
                  % multiple(big['people'], others),
            lede='Before any question about who is growing: this is the scale of the '
                 'town’s workforce, and one part of it is nearly all of it.',
            # THE LIST IS DERIVED. It named three departments and stood while the count
            # went to nine, because a sentence listing the data does not fail when the
            # data grows.
            detail='The schools name %s members of staff in FY%s. Every other part of the '
                   'town that publishes a count — %s — comes to %s between them.'
                   % (num(big['people']), big['last_fy'],
                      ' and '.join(filter(None, [', '.join(e['department'] for e in rest[:-1]),
                                                 rest[-1]['department']])),
                      num(others)),
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
            claim='%s fewer people than when %s first published. The rest are flat or '
                  'larger' % ('%s department has' % word(len(shrank)).capitalize()
                              if len(shrank) == 1 else
                              '%s departments have' % word(len(shrank)).capitalize(),
                              'it' if len(shrank) == 1 else 'they'),
            lede='How many people each department printed, first year against last. A '
                 'change here is people present, not a decision about posts.',
            # ALSO DERIVED, AND THIS ONE WAS PUBLISHING A WRONG FIGURE. It read the last
            # row of the table as the DPW and said `the Department of Public Works
            # unchanged at 1 posts` -- the DPW has fourteen, and the last row had become
            # Facilities Management the moment five more departments were found. A
            # positional reference is not a name, which is rule 13 pointed at our own
            # output.
            detail='%s. %s %s larger or unchanged.'
                   % ('; '.join('%s is down %s, from %s to %s'
                                % (e['department'], num(abs(e['change'])),
                                   num(e['first']), num(e['people'])) for e in shrank),
                      'The other %s' % word(len(emp) - len(shrank)),
                      'department is' if len(emp) - len(shrank) == 1 else 'departments are'),
            figures=dict(
                {'shrank': figure(len(shrank), word(len(shrank)).capitalize(),
                                  'departments with fewer people than when they started'),
                 'rest': figure(len(emp) - len(shrank), word(len(emp) - len(shrank)),
                                'flat or larger')},
                **{'d%d' % i: figure(abs(e['change']), num(abs(e['change'])),
                                     'fewer at %s' % e['department'])
                   for i, e in enumerate(shrank)},
                **{'f%d' % i: figure(e['first'], num(e['first']),
                                     'at %s when it first published' % e['department'])
                   for i, e in enumerate(shrank)},
                **{'n%d' % i: figure(e['people'], num(e['people']),
                                     'at %s now' % e['department'])
                   for i, e in enumerate(shrank)}),
            figure='shrank',
            kind='measured',
            bearing='sizes',
            basis='Each department’s own published count, first published year against '
                  'last, with any year reading under half its predecessor dropped as a '
                  'short read rather than a cut.',
            not_shown='Whether any POST was cut. A count falls when somebody leaves a post '
                      'that is still funded, and holds when a post is eliminated and its '
                      'holder moves into another vacancy — the Assessing office reported '
                      'being “fully staffed for the first time in over a year” in FY2024, '
                      'which is a year of posts that existed and stood empty. Nor hours or '
                      'FTE: a call firefighter and a classroom teacher are one person each '
                      'here.',
            so_what='Only one part of the town has visibly fewer people, which is not the '
                    'same as a post being cut.',
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

    # THE SIGNATURE IMAGE FIRST, AND IT IS NOT A PIE. TJ: *"lets do something more
    # interesting than a pie chart too for the visual. In proportion, show PEOPLE that
    # represent each department as characters in proportion to the amounts... moving pie
    # chart down below for data."*
    #
    # A pie of nine departments where one is 69% is a correct chart and a forgettable
    # one. Drawn as people it is countable -- twenty-five figures against four -- and it
    # is made of the thing the page is about. Rule 7f: the signature is best drawn in the
    # units the subject is actually made of. The pie keeps its job further down, beside
    # the table, where a reader has come for the split rather than for the impression.
    t.append('\n![A crowd of small figures, one for every person the town publishes a '
             'count for, coloured by department. The schools are most of the crowd.]'
             '(charts/town-personnel-crowd.svg)\n')
    t.append('\n## How many people each part of the town employs\n')
    t.append('\n![A pie of the people the town publishes a count for, split between the '
             'departments that state a figure. One slice is most of it.]'
             '(charts/town-personnel-share.svg)\n')
    t.append('\n![Every department that publishes a headcount, one row each, drawn as '
             'figures — one figure for every ten people. The schools run to twenty-five '
             'and the next department to four.](charts/town-personnel-people.svg)\n')
    t.append('\n| part of the town | people | as of | first published | change | '
             'a year | what it counts |\n|---|---:|---|---:|---:|---:|---|\n')
    for e in emp:
        span = int(e['last_fy']) - int(e['first_fy'])
        t.append('| %s | %s | FY%s | %s in FY%s | %s%s | %s | %s |\n'
                 % (e['department'], num(e['people']), e['last_fy'], num(e['first']),
                    e['first_fy'], '+' if e['change'] >= 0 else '\u2212',
                    num(abs(e['change'])),
                    '—' if not span else
                    '%s%.1f' % ('+' if e['change'] >= 0 else '\u2212',
                                abs(e['change']) / span),
                    e['kind']))
    # POSTS AND PEOPLE ARE NOT ONE QUANTITY, and this table used to say they were: "they
    # are all answers to how many people work here". TJ: *"our headcount are people hired.
    # thats not to say their positions were cut if someone left... it could be unfilled
    # positions."* Seven departments report PEOPLE and two report POSTS, and the Assessing
    # office's own FY2024 report proves the difference matters -- "we are fully staffed for
    # the first time in over a year" is a year of posts that existed and stood empty.
    posts = [e for e in emp if 'establishment' in e['kind']]
    if posts:
        t.append('\n%s %s an ESTABLISHMENT rather than a headcount — the posts the '
                 'department states it has, not the people standing in them. A post can '
                 'sit vacant and still be printed here, and the Assessing office says so '
                 'itself: in FY2024 it reported being “fully staffed for the first time in '
                 'over a year”.\n'
                 % (' and '.join(e['department'] for e in posts),
                    'reports' if len(posts) == 1 else 'report'))
    t.append('\nThese are not identical measures — a named roster, a career count plus the '
             'low end of an on-call range, and an establishment of posts — and they are '
             'answers to two different questions: how many people are there, and how many '
             'posts the department says it has. Where a department states a range the '
             'LOW end is used, so none is flattered by its own vagueness.\n')

    # WHY EACH ROW COUNTS FROM A DIFFERENT YEAR, asked by TJ looking at the column:
    # *"why are they all different. shouldn't we standardize on a FY to compare to?"*
    #
    # Because no year exists that all of them publish. The best is FY%s at %s of %s, and
    # standardising on it would drop exactly the departments that STOPPED publishing --
    # the ones whose silence is the finding. So the span stays each department's own and
    # the comparable column is the RATE, which is what the budget report does with money
    # for the same reason.
    best, hits = _common_year(emp)
    # CONTRAST TWO REAL SPANS. The first version took the department with the FEWEST
    # YEARS, which is the Library at one -- span zero -- and printed `+0 over 0 years`.
    def span(e):
        return int(e['last_fy']) - int(e['first_fy'])

    # The pair has to ILLUSTRATE, so: the longest record, and the shortest one that
    # actually moved. A contrast between `+4 over 14 years` and `+0 over 1` shows nothing.
    hi = max(emp, key=lambda e: (span(e), abs(e['change'])))
    lo = min((e for e in emp if span(e) and e['change']), key=span)
    # `STOPPED PUBLISHING` IS A CLAIM ABOUT THE TOWN, so a department whose last year we
    # merely failed to read does not belong in it. The Police published FY2024 and we did
    # not find the page -- that is the suspect-year guard, and it is our gap.
    latest = max(int(e['last_fy']) for e in emp)
    stopped = [e for e in emp
               if int(e['last_fy']) < latest and not e['suspect']]
    t.append('\n**change** is measured over each department’s own record, and those '
             'records do not line up: the %s record spans %s years and the %s’s %s, so '
             '%+d and %+d are not the same claim. No year is published by all %s — the fullest is '
             'FY%s, with %s of them — and standardising on that would drop the %s that '
             'STOPPED publishing, which is the part worth seeing. **a year** is the change '
             'divided by the years it spans, and that column compares.\n'
             % (hi['department'], num(span(hi)), lo['department'], num(span(lo)),
                hi['change'], lo['change'], num(len(emp)), best, num(hits),
                word(len(stopped))))
    susp = [e for e in emp if e['suspect']]
    if susp:
        t.append('\nA year whose count reads under half the year before it is dropped as a '
                 'short read rather than published as a cut: %s. The Police roster comes '
                 'back as seven officers in FY2024 against twenty-five in FY2023, which is '
                 'a page this reader did not find, not three quarters of a police force.\n'
                 % '; '.join('%s FY%s' % (e['department'], ', FY'.join(e['suspect']))
                             for e in susp))

    t.append('\n## Headcount over time\n')
    t.append('\n![Every department that publishes a headcount, drawn on one people axis '
             'from FY%s to FY%s. The school line runs far above the rest; the Fire '
             'Department sits alone in the middle and seven departments share the floor. '
             'A break in a line is a year that department published no figure.]'
             '(charts/town-personnel-all.svg)\n'
             % (emp[0]['first_fy'], emp[0]['last_fy']))
    t.append('\nOn one scale the relation is plain, and it is the one the panels below '
             'deliberately hide: every other department that publishes a headcount fits '
             'inside the schools several times over. The panels answer how each one is '
             'MOVING; this answers how big each one is.\n')

    t.append('\n![%s small panels, one per part of the town that publishes a staff '
             'count, each showing headcount year by year on its own scale. A hollow point '
             'marks a year dropped as a misreading.](charts/town-personnel-counts.svg)\n'
             # THE CHART DROPS A ONE-YEAR DEPARTMENT, because a single point is not a
             # line, so the alt text has to count what is DRAWN rather than what is in
             # the table. It said nine and drew eight.
             % word(len([e for e in emp if len(
                 [p_ for p_ in e['series'] if not p_.get('suspect')]) >= 2])
             ).capitalize())

    # DERIVED, BECAUSE THE SET CHANGES. This paragraph named four departments and was
    # written when four was all there were; the check for departments we had missed found
    # five more, and a sentence that says `the Police Department and the DPW publish too
    # few years` is wrong the moment a sixth appears. Rule 2 covers every generated
    # surface, not only the model.
    def span(e):
        live = [p_['people'] for p_ in e['series'] if not p_.get('suspect')]
        return min(live), max(live)

    long_ = [e for e in emp if e['years'] >= 3]
    short = [e for e in emp if e['years'] < 3]
    sentences = []
    for e in sorted(long_, key=lambda e: -e['years'])[:3]:
        lo, hi = span(e)
        sentences.append('%s moves between %s and %s across %s published years'
                         % (e['department'], num(lo), num(hi), num(e['years']))
                         if lo != hi else
                         '%s holds at %s in each of its %s published years'
                         % (e['department'], num(lo), num(e['years'])))
    joined = '; '.join(sentences)
    t.append('\n%s.' % (joined[:1].upper() + joined[1:]))
    if short:
        names = [e['department'] for e in short]
        t.append(' %s %s too few years to show a trend at all.'
                 % (' and '.join(filter(None, [', '.join(names[:-1]), names[-1]])),
                    'publishes' if len(short) == 1 else 'publish'))
    t.append('\n')

    if sd['by_school']:
        t.append('\n## The schools, in detail\n\n%s times the next employer, so worth '
                 'breaking out. FY%s.\n\n| school | staff |\n|---|---:|\n'
                 % (word(round(emp[0]['people'] / emp[1]['people'])).capitalize(),
                    sd['fy']))
        for r in sd['by_school']:
            t.append('| %s | %s |\n' % (r['school'].replace('-', ' ').title(), num(r['people'])))
        if sd.get('district') and sd.get('sums_to') and sd['sums_to'] != sd['district']:
            t.append('\nThe school columns come to %s and the district employs %s. That is '
                     'not an error to tidy away: somebody who teaches at two schools is '
                     'staff at both and one employee of the district, so the two answer '
                     'different questions and are counted differently.\n'
                     % (num(sd['sums_to']), num(sd['district'])))
        t.append('\n| what they do | staff |\n|---|---:|\n')
        for r in sd['by_position'][:12]:
            t.append('| %s | %s |\n' % (r['position'], num(r['people'])))

    # WHICH PARTS OF THE BUDGET HAVE A HEADCOUNT BEHIND THEM, derived rather than
    # asserted. The old version of this section said a Council on Aging driver appeared in
    # no published count, and by then the Council on Aging had twelve years of rosters on
    # this very page. A hand-written absence goes stale the moment the gap is filled, and
    # says the town publishes less than it does.
    #
    # The two sides do not line up one to one: the budget is voted in twelve FUNCTIONAL
    # groups and the reports are written by departments, so Police, Fire and Building all
    # sit inside `Protection of persons & property` and the Assessors are one office
    # inside `General Government`. The crosswalk is stated, not guessed.
    covered = collections.defaultdict(list)
    for e in emp:
        g = BUDGET_GROUP.get(e['department'])
        if g:
            covered[g].append(e['department'])
    missing = [g for _slug, g, _m in GROUPS if g not in covered]
    t.append('\n## Which parts of the budget have a headcount behind them\n\n')
    t.append('Town Meeting votes the budget in %s groups. %s of them now have at least one '
             'department publishing how many people it employs; %s have none.\n\n'
             % (num(len(GROUPS)), num(len(covered)), num(len(missing))))
    t.append('| part of the budget | who publishes a count |\n|---|---|\n')
    for _slug, g, _m in GROUPS:
        # `covered[g]` ON A defaultdict INSERTS g. Rendering this table filled the
        # dictionary with all twelve groups, so the membership test below saw every one
        # as covered and the `no count` table came out empty.
        t.append('| %s | %s |\n' % (g, ', '.join(covered.get(g, ())) or '—'))
    t.append('\nA group with a count is not a group that is counted: `General Government` '
             'is voted as one figure covering half a dozen offices, and two of them state '
             'a number.\n')
    t.append('\n### The ones with no count, and why\n\n')
    t.append('Three different answers, and only one of them is a department being quiet.'
             '\n\n| part of the budget | voted, FY%s | what it is | what the reports '
             'show |\n|---|---:|---|---|\n' % TB.load()['detail_years'][-1])
    # THE MONEY BELONGS BESIDE THE SILENCE. TJ: *"we should flag that in this town
    # personel and budget report TBH... dont we have a budget for it though?"* We do:
    # Facilities & Grounds is over a million dollars a year and files nothing. A reader
    # deciding whether a blank row matters cannot decide it without the amount.
    voted = {r['name']: r['last'] for r in TB.table(TB.load())}
    for _slug, g, _m in GROUPS:
        if g in covered or g not in NO_COUNT:
            continue
        kind, why = NO_COUNT[g]
        amt = voted.get(g)
        t.append('| %s | %s | %s | %s |\n'
                 % (g, ('$%s' % format(int(round(amt)), ',')) if amt else '—',
                    kind, why))
    t.append('\nThe gross-wages list named a department beside each employee through '
             'FY2016 and stopped, so there has been no town-wide headcount by department '
             'since.\n')

    t.append('\n## What this cannot show\n\n')
    for n in _not_established(d):
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
                 label='school staff — %s as everywhere else that publishes a count, '
                       'put together'
                       % multiple(d['employers'][0]['people'],
                                  sum(e['people'] for e in d['employers'][1:]))),
            dict(value=num(sum(e['people'] for e in d['employers'][1:])),
                 label='in the other %s parts of the town that publish a count, added up'
                       % word(len(d['employers']) - 1)),
            dict(value='%s of %s' % (num(len(d['employers'])), num(len(d['sizes']))),
                 tone='var(--series-cost)',
                 label='parts of the town that publish any staff count at all'),
        ],
        # THE GLYPH TRAVELS WITH THE DATA. `Pictogram.tsx` draws whatever path the
        # payload gives it, so the printed SVG in the markdown and the interactive chart
        # on the page cannot come to disagree about what a figure looks like -- rule 2's
        # problem in a different medium, and rule 7f's answer to it.
        pictogram=dict(unit=10, unit_label='people',
                       glyph=__import__('pictograms').GLYPHS['person']),
        years=d['years'], last=last,
        fire=fire, roster=d['roster'], publishes=d['publishes'],
        employers=d['employers'], school_detail=d['school_detail'],
        staffing=[r for r in d['staffing'] if 'establishment' in r['measure']],
        officers=[dict(fy=y, officers=d['per'][(y, 'appointed officer')])
                  for y in d['years']],
        sources=_sources(d),
        not_established=_not_established(d),
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
