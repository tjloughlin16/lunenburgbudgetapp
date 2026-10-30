#!/usr/bin/env python3
"""PRESCHOOL: what families pay in tuition, where it goes, and what of the preschool's cost the
records let anyone identify.

    python3 scripts/build_preschool.py           # write the topic payload
    python3 scripts/build_preschool.py --check   # fail if it would change

TJ, 29 October 2026: *"let's do a preschool report and put it in the school page ... on the
preschool page, we should do a fiscal year chart that shows the total budget in the budget docs
that we can identify directly to preschool, if that's possible, and then compare that to how much
was made."* And on how it runs: the preschool is INTEGRATED into the Primary School -- children on
education plans and tuition-paying peers share one program.

WHAT IS ESTABLISHED, and from where:
  * TUITION IS A TOWN RECEIPT. General fund 0100, account 431900, in the Town's books, never the
    school department's: the school journal (FY2023-FY2026) holds no preschool receipt in any
    fund and none credited to an expense line. Read by school_receipts.py.
  * NO SCHOOL BUDGET LINE IS NAMED FOR PRESCHOOL. Checked, not assumed: no account, org or fund
    name in the journal matches pre-school / preschool / pre-K / early childhood except the grant
    funds below; no value of the program segment of the account string holds a preschool account
    (that segment marks athletics, nurses, libraries; none preschool); the building segment puts
    the preschool in with the whole Primary School. "P.S." in a line name is the PRIMARY SCHOOL,
    never preschool. The district's budget documents (line-history.csv, lps-budget-lines.csv)
    print no preschool line either. CHECKED BELOW at build time, or nothing is written.
  * THE IDEA PRESCHOOL GRANTS are identifiable: DESE codes 262, 264 and 298 (journal.GRANT_PROGRAM),
    spent per school-fund-flows.csv.
  * PAY OF STAFF THE ROSTER LISTS UNDER PRESCHOOL. The annual town report prints the Primary
    School's roster with a "Pre-School" heading, and a gross wage list. A name matched across the
    two is OUR match (surname exact, first name's first three letters or a declared nickname, one
    wage row only); a year is shown only when every rostered preschool post matched. Totals and
    counts only, never a name or one person's pay. It is pay, not cost: no benefits, no shared
    staff, no FTE, and the wage list's period is the one that report prints.

WHAT IS NOT: the general fund cost of the preschool (registered in money-gaps.csv); why the Town
estimates the tuition low (rule 7); whether the grant paid any of the same people (the two are
never added).
"""
import argparse
import collections
import csv
import json
import os
import re
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402
import journal as J  # noqa: E402
import school_receipts as SR  # noqa: E402

ID = 'preschool'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
DATA = os.path.join(ROOT, 'sources', 'data')
D0 = Decimal(0)
PRESCHOOL_PROGRAMS = ('IDEA (preschool)', 'IDEA preschool (pandemic relief)',
                      'Preschool special education program improvement')
FUND_PAGE = {'IDEA (preschool)': '/school-funds/idea-preschool',
             'IDEA preschool (pandemic relief)': '/school-funds/idea-preschool-pandemic-relief',
             'Preschool special education program improvement':
                 '/school-funds/preschool-special-education-program-improvement'}
TOWN_FUND = '/town-funds/general-fund'
NAMED = re.compile(r'PRE[- ]?SCH|PRESCH|PRE-?K\b|EARLY CHILD', re.I)
# OURS: nicknames the roster prints for the wage list's legal first name, declared one by one.
NICKNAMES = {'SUE': 'SUSAN'}


def fail(msg):
    raise SystemExit('build_preschool: ' + msg)


def fl(x):
    return float(x)


# ---------------------------------------------------------------- the checks behind "no line"
def assert_no_named_line():
    """The page says no school account, org or budget line is named for preschool. Prove it."""
    # Grant funds ARE named for it (#262, and the old #296 early childhood grant); the claim is
    # about the school budget, the general fund.
    for a in J.accounts().values():
        txt = ' '.join([a['account_description'], a['org_name'], a['fund_name']])
        if J.grant_program(a) == 'General fund' and NAMED.search(txt):
            fail('a general fund school account is now named for preschool (%s): the page says none is'
                 % a['account'])
    for fn in ('line-history.csv', 'lps-budget-lines.csv'):
        p = os.path.join(DATA, fn)
        if os.path.exists(p) and NAMED.search(open(p, encoding='utf-8').read()):
            fail('%s now prints a preschool line: the page says the budget documents print none' % fn)


def grant_spent():
    """{fy: {program: spent with orders owed}} for the preschool grant programs."""
    out = collections.defaultdict(lambda: collections.defaultdict(Decimal))
    for r in csv.DictReader(open(os.path.join(DATA, 'school-fund-flows.csv'), encoding='utf-8')):
        if r['program'] in PRESCHOOL_PROGRAMS:
            out[int(r['fiscal_year'])][r['program']] += Decimal(r['spent_with_owed'])
    if not out:
        fail('no preschool grant fund in school-fund-flows.csv: the join matched nothing')
    return {fy: dict(v) for fy, v in out.items()}


def roster_pay():
    """{fy: dict(posts, matched, total, checked)} -- our match of the roster's preschool posts to
    the wage list in the same report. Names never leave this function."""
    tok = lambda s: re.sub(r"[^A-Z' -]", ' ', s.upper()).replace('-', ' ').split()
    wages = collections.defaultdict(list)
    for w in csv.DictReader(open(os.path.join(DATA, 'gross-wages.csv'), encoding='utf-8')):
        wages[w['fy']].append((tok(w['name']), Decimal(w['amount']), w['status']))
    posts = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(DATA, 'staff-roster-entries.csv'), encoding='utf-8')):
        if re.search(r'pre-?\s?school|presch', r['grade_or_dept'], re.I) and int(r['fy']) >= SR.FIRST_FY:
            posts[r['fy']].append(r)
    if not posts:
        fail('no roster post under preschool: the join matched nothing')
    out = {}
    for fy, rs in posts.items():
        got, total, status = 0, D0, set()
        for r in rs:
            t = tok(r['name'])
            if len(t) < 2:
                continue
            first, last = NICKNAMES.get(t[0], t[0]), t[-1]
            hit = [w for w in wages.get(fy, []) if last in w[0]
                   and any(x[:3] == first[:3] for x in w[0] if x != last)]
            if len(hit) == 1:
                got += 1
                total += hit[0][1]
                status.add(hit[0][2])
        out[int(fy)] = dict(posts=len(rs), matched=got, total=total,
                            teachers=sum(1 for r in rs if r['position'] == 'Classroom Teacher'),
                            checked=status == {'checked'}, page=rs[0]['page'], doc=rs[0]['document'])
    return out


# ---------------------------------------------------------------- the page
def page():
    assert_no_named_line()
    S = SR.series()
    tu = {fy: S[fy].get('431900') for fy in SR.YEARS_SHOWN}
    G = grant_spent()
    P = roster_pay()
    full = {fy: p for fy, p in P.items() if p['matched'] == p['posts'] and p['posts']}
    if not full:
        fail('no year matched every rostered preschool post')
    years = list(SR.YEARS_SHOWN)
    xs = [C.fy(y) for y in years]
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    N = lambda n, unit: figure(n, C.num(n), unit)
    gyrs = sorted(G)
    gtot = {fy: sum(G[fy].values(), D0) for fy in gyrs}
    est = {fy: tu[fy]['estimate'] for fy in years if tu[fy] and tu[fy]['estimate'] is not None}
    held = [fy for fy in years if tu[fy]]
    lastp = max(full)
    r25, e25 = tu[2025]['received'], tu[2025]['estimate']
    r19 = tu[2019]['received']
    same = [fy for fy, e in est.items() if e == int(r19)]
    if sorted(same) != [2020, 2025]:
        fail('the estimate-equals-FY2019 finding no longer holds: %s' % same)
    rate = (fl(r25) / fl(e25))
    share = fl(e25) / fl(r25) * 100

    chart = TP.series(
        'Tuition received beside identifiable cost', xs,
        [TP.track('Tuition received, a Town receipt', [fl(tu[y]['received']) if tu[y] else None for y in years],
                  'published', 'bar'),
         TP.track('Town’s estimate of the tuition', [fl(est[y]) if y in est else None for y in years],
                  'published', 'bar'),
         TP.track('IDEA preschool grants spent', [fl(gtot[y]) if y in gtot else None for y in years],
                  'published', 'bar'),
         TP.track('Pay of staff rostered under preschool, our match',
                  [fl(full[y]['total']) if y in full else None for y in years], 'estimate', 'bar')],
        '$', kind='bar',
        note='Side by side, never added: the grant may pay some of the same staff. A gap is a year no '
             'record we hold prints. No general fund cost is identifiable.')

    f = LD.fact
    facts = [
        f('tu25', U(r25), 'tuition received by the Town, %s' % C.fy(2025), 'published', label_figures={'y': F(2025)}),
        f('es25', U(e25), 'the Town’s estimate of it, %s' % C.fy(2025), 'published', label_figures={'y': F(2025)}),
        f('tu19', U(r19), 'tuition received, %s' % C.fy(2019), 'published', label_figures={'y': F(2019)}),
        f('gr25', U(gtot[2025]), 'IDEA preschool grant spent, %s' % C.fy(2025), 'published', label_figures={'y': F(2025)}),
        f('pay', U(full[lastp]['total']), 'pay of %d staff rostered under preschool, %s, ours'
          % (full[lastp]['posts'], C.fy(lastp)), 'estimate',
          label_figures={'n': N(full[lastp]['posts'], 'staff'), 'y': F(lastp)}),
        f('gf', None, 'general fund cost of the preschool', 'gap',
          closes='A program cost report from the district: preschool staff by FTE and fund'),
    ]
    con = lambda text, rests, figs, so, so_figs=None: TP.conclusion(text, rests, figs, so=so, so_figures=so_figs)
    conclusions = [
        con('Families paid %s in preschool tuition in %s; it went to the Town’s general fund, not the schools.'
            % (C.usd(fl(r25)), C.fy(2025)), ['tu25'], {'a': U(r25), 'y': F(2025)},
            'The school budget carries the preschool at full cost; the tuition offsets none of it there.'),
        con('The Town estimated %s of it, and received %s times that.'
            % (C.usd(fl(e25)), '%.1f' % rate), ['es25', 'tu25'],
            {'a': U(e25), 'b': figure(rate, '%.1f' % rate, 'times')},
            'The difference reaches the Town as unbudgeted receipts. Why the estimate is low is not recorded.'),
        con('The %s estimate and the %s one were both %s: %s’s tuition, cents dropped.'
            % (C.fy(2020), C.fy(2025), C.usd(fl(e25)), C.fy(2019)), ['tu19', 'es25'],
            {'a': F(2020), 'b': F(2025), 'c': U(e25), 'd': F(2019)},
            'The figure looks carried forward from one year; nothing written says how it was set.'),
        con('The IDEA preschool grant spent %s in %s; no general fund cost is identifiable at all.'
            % (C.usd(fl(gtot[2025])), C.fy(2025)), ['gr25', 'gf', 'pay'],
            {'a': U(gtot[2025]), 'y': F(2025)},
            'What taxes carry for the preschool cannot be read from any public record we hold.'),
    ]
    T_lit = ['P.S.', '262', '264', '298', '$1,897.11', '$3,548.58', '4%', 'FY2025', 'FY2026', 'FY2027',
             '7 February 2024', '22 January 2025', '21 January 2026']
    blocks = [
        TB.panels('Who carries what', [
            TB.panel('Tuition, to the Town', [('Received', C.usd(fl(r25)), None),
                                              ('The Town’s estimate', C.usd(fl(e25)), None)],
                     sub='A Town general fund receipt', so='Pays into the Town’s general fund, not the school budget.'),
            TB.panel('IDEA preschool grant', [('Spent', C.usd(fl(gtot[2025])), None)],
                     sub='A federal grant to the schools', so='Federal money, awarded to the district year by year.'),
            TB.panel('Rostered preschool staff', [
                ('Pay, our match', C.usd(fl(full[lastp]['total'])), None),
                ('Posts on the roster', C.num(full[lastp]['posts']), None)],
                     sub='Every fund; pay only, no benefits', so='The grant may pay part of this pay, so the two do not add.'),
        ], place='lead', note=('%s, from three different records and payers. None of them is what the preschool '
                               'costs.' % C.fy(2025), None, (C.fy(2025),))),
        TB.explain('What could be identified', [
            '**The school budget names no preschool line.** No account, organization or budget line is named for '
            'it, and the account codes put the preschool in with the whole Primary School. A “P.S.” in a line '
            'name is the Primary School, never the preschool.',
            ('**Only the IDEA preschool grants are identifiable**: DESE codes 262, 264 and 298, each on its own '
             'fund page.', None, ('262', '264', '298')),
            '**Staff pay is our match**: the annual report’s Primary School roster lists teachers and '
            'paraprofessionals under a preschool heading, and its wage list prints each name’s gross pay. We '
            'matched the two and publish only the total. A year is shown only when every post matched.',
            '**The preschool is integrated**: children on education plans and tuition-paying children share '
            'it, so even a full staff cost would not separate the two.',
        ], place='end', tone='define'),
        TB.explain('How the tuition is set', [
            ('The School Committee votes the rate each year. On 7 February 2024 it raised the FY2025 rate by '
             '4%: two days a week to $1,897.11, four days to $3,548.58. It approved 4% again for FY2026 on '
             '22 January 2025, and for FY2027 on 21 January 2026, adding a five-day option.', None,
             tuple(T_lit)),
        ], place='end', tone='plain'),
    ]
    sources = [
        dict(label='Town of Lunenburg — annual town reports, receipts schedules, FY2011–FY2022',
             href='/data/annual-report-receipts.csv'),
        dict(label='Town of Lunenburg — MUNIS revenue report, FY2020 year end (Finance Committee files)',
             href=SR.DOCS['q4']),
        dict(label='Town of Lunenburg — MUNIS local receipts report, FY2025 (Finance Committee files)',
             href=SR.DOCS['fy25']),
        dict(label='Lunenburg Budget Project — school-fund-flows.csv (every school fund, FY2023–FY2026)',
             href='/docs/data/school-fund-flows.csv'),
        dict(label='Town of Lunenburg — annual town reports, Primary School rosters and gross wage lists',
             href='/data/staff-roster-entries.csv'),
        dict(label='School Committee minutes, 7 February 2024 (the FY2025 tuition rate)',
             href='/docs/minutes/text/school-committee/2024-02-07-minutes-6395.txt'),
        dict(label='Lunenburg Budget Project — the Town general fund page: every school receipt it books',
             href=TOWN_FUND),
    ]
    p = TP.page(
        ID,
        'Families’ preschool tuition goes to the Town, not the schools; in %s the Town had budgeted '
        'for %s of it.' % (C.fy(2025), C.pct(share, 0)),
        facts, conclusions, finding_figures={'y': F(2025), 'p': figure(share, C.pct(share, 0), '%')}, chart=chart, blocks=blocks, sources=sources,
        draft=None if ID in REG.TOPICS else dict(title='Preschool', home='school-all-funds'))
    p['not_established'] = [
        'The general fund cost of the preschool: no line, account or program code separates it from the Primary School.',
        'Why the Town estimates the tuition where it does.',
        'Whether the IDEA preschool grant paid any of the rostered preschool staff.',
        'Tuition for FY2023, FY2024 and FY2026 alone: ' + ' '.join(SR.WHY_MISSING[y] for y in (2023, 2024, 2026)),
    ]
    return p


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
        print('preschool: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
