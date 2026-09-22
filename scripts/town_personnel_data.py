#!/usr/bin/env python3
"""One reading of the town's people, for the two reports that split it.

TJ, 22 September 2026: *"town-personnel is focused on the volunteers. that should be a
separate for under 'the boards, compared'. Basically, 'board composition'. I want a
separate report about the paid personel though which i think town-personnel should be
for."*

He is right and the single page was answering two people at once. A resident asking WHERE
COULD I SERVE wants empty seats, terms and how often a board turns over. A resident asking
WHO WORKS FOR THIS TOWN wants the officers, the rosters and what each department says it
employs. Those are different questions with different answers and they were sharing a
stat row.

So: `board-composition` for the seats people volunteer for, and `town-personnel` for the
posts people are hired into. ONE loader, because two readers of one dataset that disagree
about how many people are in it is the defect this whole archive keeps finding.

THE LINE BETWEEN THEM IS THE DOCUMENT'S, not ours. A post that states a membership or a
term is a BOARD SEAT -- `Board of Assessors - (3 members) 3 year term`. A post that states
neither is an OFFICER -- `DPW DIRECTOR`. The listing prints the first kind under a heading
saying how it is constituted and the second as a title with a name beneath it, in every
year we can read. What it never says is what anybody is PAID, so this file does not claim
it: `officer` means a post somebody is appointed or hired into, which is the town's own
distinction and not a payroll.
"""
import collections
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SRC = os.path.join(ROOT, 'sources', 'data', 'town-personnel.csv')
STAFFING = os.path.join(ROOT, 'sources', 'data', 'department-staffing.csv')
ROSTERS = os.path.join(ROOT, 'sources', 'data', 'department-rosters.csv')
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
    # WHICH WAY A SEAT IS FILLED TRAVELS WITH IT. TJ, 22 September 2026: *"for open seats,
    # we should say whether or not its elected or appointed"*. It is the difference between
    # standing for election in May and writing to the Select Board, so a list of vacancies
    # that does not say which is telling somebody where to go and not how to get there.
    # The section header above the post is the town's own answer and it was already read.
    vac = collections.Counter()
    vac_how = {}
    for r in cur:
        if r['vacancies']:
            vac[r['post']] += r['vacancies']
            vac_how.setdefault(r['post'], r['section'])

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

    # ARE THE CHARTERED SEATS FILLED? TJ, 22 September 2026: *"The boards have a charter
    # that says how many seats are in them. why would that chagne?!"* -- which is the
    # right objection to a chart of seat COUNTS over time. A charter fixes the number, so
    # a line that moves is measuring our reading, not the town. What does move, and is
    # worth asking, is whether the seats a charter creates have somebody in them.
    #
    # Only bodies that state a plain size count: a body constituted as a RANGE (`no less
    # than 5 and no more than 22`) has no target to be short of. And a year can come out
    # ABOVE 100%, which is not an overfull board -- it is a mid-year replacement printed
    # beside the person replaced, so the figure is reported rather than capped.
    fill = []
    for y in years:
        seats, filled, bodies = 0, 0, set()
        for r in rows:
            if r['fy'] != y or not r['stated_members'] or '-' in r['stated_members']:
                continue
            if r['post'] not in bodies:
                bodies.add(r['post'])
                seats += int(r['stated_members'])
            if r['person'].strip():
                filled += 1
        if seats and len(bodies) >= 8:
            fill.append(dict(fy=y, seats=seats, filled=filled, bodies=len(bodies),
                             pct=round(filled / seats * 100, 1)))

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

    # THE NAMED ROSTERS, and the spread between them and what the department states.
    roster = []
    if os.path.exists(ROSTERS):
        roster = list(csv.DictReader(open(ROSTERS, encoding='utf-8')))
    rcount = collections.Counter((r['fy'], r['department']) for r in roster)
    stated = {f['fy']: (f['career'] + f['on_call_low'], f['career'] + f['on_call_high'])
              for f in fire_series}
    rost = []
    for (fy, dept), n in sorted(rcount.items()):
        lo_hi = stated.get(fy) if dept == 'Fire Department' else None
        rost.append(dict(fy=fy, department=dept, named=n,
                         stated_low=lo_hi[0] if lo_hi else '',
                         stated_high=lo_hi[1] if lo_hi else '',
                         agrees=('' if not lo_hi else
                                 'yes' if lo_hi[0] - 3 <= n <= lo_hi[1] + 3 else 'no')))

    return dict(rows=rows, years=years, per=per, checks=checks, posts=posts,
                roster=rost,
                last=last, named=named, vacancies=vac, vac_how=vac_how, terms=terms,
                ahead=ahead,
                body_churn=body, body_big=big, staffing=staff, fire=fire_series,
                fill=fill,
                distinct=len(who), held=len(named), multi=multi, churn=churn,
                ever=len(ever), served_all=served_all, sizes=sizes)


