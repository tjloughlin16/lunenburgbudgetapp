#!/usr/bin/env python3
"""WHO GRANTS AND FEES PAY FOR: school pay by fund, pay moved between funds, and the posts the
ledger can follow by name. Three topic pages on the whole-school shelf (school-all-funds).

TJ, 24 October 2026: *"for all the grants.... have we broken down how that money is spent? I
want to have reports on that."* -- how grant and fee money is spent on pay, and whether any
post is offset by a grant or a fee fund, read the same way for every post. No post is singled
out: the positions page reads every leadership account alike.

WHAT THE LEDGER CAN AND CANNOT SAY. Payroll posts one line per ACCOUNT per pay run, never per
person (journal.PAYROLL_GRAIN). So:

  * a general fund account named for one post (ATHLETIC DIRECTOR'S SALARY) can be followed by
    name, year by year;
  * grant pay posts to accounts named for a KIND of work (GRNT NON INSTR/SUPPRT SALARIES), so a
    grant's pay can be totalled and split by kind, never by post;
  * pay is also MOVED between funds after the pay run, by journal entry (GEN, reversed by GRV).
    A move is found as a journal whose lines touch pay in two or more funds and net to zero
    (on its pay lines or on all its expense lines) -- the accrual and duplicate-reversal
    journals, which only add or only subtract, are not moves.

Which posts a grant pays is therefore NOT in this ledger, and it is registered as a gap.

THE CROSSWALK (sources/data/position-funds-crosswalk.csv) is OURS: each post's directory title,
budget-book line and ledger account, with the basis for each pairing written beside it. Every
account it names must exist in the journal, or this refuses to write.

    python3 scripts/build_pay_by_fund_topics.py          # write the three pages
    python3 scripts/build_pay_by_fund_topics.py --check  # fail if any is stale
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
from brief import step  # noqa: E402
import journal as J  # noqa: E402
import topic_blocks as TB  # noqa: E402
# The DESE function code is the school's budget line; its name and its class (a voted line, a
# heading, no code, no voted line) come from the same place budget-lines-all-funds reads them,
# so a line is named once across the shelf.
from build_school_all_funds import code_names  # noqa: E402
# RE-CHARGED OFF A SCHOOL LINE: the school-line pages' own reading of year-end journal entries
# (fy_breakdown, rule a, one memo at a time), and their own name for a line, so this page and
# /school-lines/<line> report the same re-charge under the same name.
# Both imported inside build(): build_fy_breakdown imports fy_salaries, which imports this module.

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
CROSSWALK = os.path.join(ROOT, 'sources', 'data', 'position-funds-crosswalk.csv')
Y = J.YEARS
F0, F1 = Y[0], Y[-1]
# Pay: object 51xxxx, less the two 51-objects that are not wages (grant fringe benefits are
# benefits; 519016 is CONTRACTED SERVICES filed under the 51 series).
NOT_PAY = ('517001', '519016')
# Grant names: journal.GRANT_PROGRAM and journal.grant_program, shared with the all-funds pages.
PROGRAM = J.GRANT_PROGRAM
KIND = [('ADMINISTRATOR', 'Administrators'), ('NON INSTR', 'Support staff'),
        ('INSTR', 'Instructional staff'),
        ('STIPEND', 'Stipends')]
ESSER = ('115', '119')
# What each function class means on the voted budget (journal.FUNCTION_CLASSES), in words.
LINE_CLASS = {'line': 'a voted line', 'heading': 'a heading, no one line',
              'none': 'no function code', 'other': 'a code with no voted line'}
FEE_FUND = '1301'                      # Chapter 658 school athletics: the athletic fee fund
MOVE_ROW_MIN = 5000


def fail(msg):
    raise SystemExit('build_pay_by_fund_topics: ' + msg)


def is_pay(a):
    return a['object'][:2] == '51' and a['object'] not in NOT_PAY


program = J.grant_program


def short(names, n=3):
    return ', '.join(names[:n]) + (', and others' if len(names) > n else '')


def kind_of(a):
    d = a['account_description'].upper()
    for k, label in KIND:
        if k in d:
            return label
    return 'Other pay'


def model():
    A, L = J.accounts(), J.lines()
    pay = defaultdict(float)            # (fy, group)
    prog = defaultdict(float)           # (fy, program) outside the general fund
    kind = defaultdict(float)           # (fy, kind) grants only
    acct = defaultdict(float)           # (fy, account) every pay account
    jr = defaultdict(list)
    for r in L:
        a = A[r['account']]
        if not (J.is_expense(a) and J.is_spent(r)):
            continue
        amt = float(r['amt'])
        if r['source'] in ('GEN', 'GRV'):
            jr[(r['fy'], r['journal'])].append(r)
        if not is_pay(a):
            continue
        g = J.fund_group(a)
        pay[(r['fy'], g)] += amt
        acct[(r['fy'], r['account'])] += amt
        if g != 'General fund':
            prog[(r['fy'], program(a))] += amt
        if g == 'Grants':
            kind[(r['fy'], kind_of(a))] += amt
    # MOVES: journals that shift pay between funds.
    moved = defaultdict(float)          # (fy, account)
    other = defaultdict(set)            # (fy, account) -> programs on the other side
    why = defaultdict(list)             # (fy, account) -> journal descriptions
    n_moves = 0
    for (fy, j), rs in jr.items():
        pr = [r for r in rs if is_pay(A[r['account']])]
        if len({r['fund'] for r in pr}) < 2 and not (
                pr and len({r['fund'] for r in rs}) >= 2):
            continue
        net_pay = sum(float(r['amt']) for r in pr)
        net_all = sum(float(r['amt']) for r in rs)
        gross = sum(abs(float(r['amt'])) for r in rs)
        if not pr or not (abs(net_pay) <= 1 or abs(net_all) <= 1) or gross < 1:
            continue
        if len({r['fund'] for r in rs}) < 2:
            continue
        n_moves += 1
        for r in pr:
            a = A[r['account']]
            moved[(fy, r['account'])] += float(r['amt'])
            sign = float(r['amt']) > 0
            for o in rs:
                if o['fund'] != r['fund'] and (float(o['amt']) > 0) != sign:
                    other[(fy, r['account'])].add(program(A[o['account']]))
            d = r['description'].strip()
            if d and d not in why[(fy, r['account'])]:
                why[(fy, r['account'])].append(d)
    return dict(A=A, pay=pay, prog=prog, kind=kind, acct=acct, moved=moved, other=other,
                why=why, n_moves=n_moves)


def sources():
    return [
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                   'line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(label='Lunenburg Budget Project — munis-school-journal-accounts.csv (every school '
                   'account)', href=J.PUBLIC['accounts']),
        dict(label='Lunenburg Budget Project — position-funds-crosswalk.csv (each post’s title, '
                   'budget line and account, paired by us)',
             href='/docs/data/position-funds-crosswalk.csv'),
        dict(label='Lunenburg Public Schools — district staff directory (school-staff-directory.csv)',
             href='/docs/data/school-staff-directory.csv'),
        dict(label='Town of Lunenburg — how the journal reached us, and what was redacted',
             href='/docs/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md'),
    ]


def build():
    m = model()
    A = m['A']
    U = lambda v: figure(round(v), C.usd(round(v)))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    X = [C.fy(y) for y in Y]
    src = sources()
    out = {}
    OUTS = [g for g in J.FUND_GROUPS[1:] if any(abs(m['pay'][(y, g)]) >= 1 for y in Y)]
    out_y = {y: sum(m['pay'][(y, g)] for g in OUTS) for y in Y}
    all_y = {y: out_y[y] + m['pay'][(y, 'General fund')] for y in Y}
    out4 = sum(out_y.values())
    grants4 = sum(m['pay'][(y, 'Grants')] for y in Y)
    rev4 = sum(m['pay'][(y, 'Revolving funds and lunch')] for y in Y)
    share1 = 100.0 * out_y[F1] / all_y[F1]

    # ================================================== pay from grants and fees
    progs = sorted({p for (_, p) in m['prog']}, key=lambda p: -sum(m['prog'][(y, p)] for y in Y))
    idea = PROGRAM['240']
    idea4 = sum(m['prog'][(y, idea)] for y in Y)
    if progs[0] not in (idea, 'Extended Day Revolving Fund', 'School Lunch Revolving'):
        fail('the largest payer outside the general fund is unexpected: %s' % progs[0])
    gprogs = [p for p in progs if p in PROGRAM.values() or p.startswith('#')]
    if gprogs[0] != idea:
        fail('the page says IDEA paid the most grant pay; %s did' % gprogs[0])
    idea_sup = sum(m['prog'][(y, idea)] for y in Y)
    sup4 = sum(m['kind'][(y, 'Support staff')] for y in Y)
    adm = {y: m['kind'][(y, 'Administrators')] for y in Y}
    adm_y = [y for y in Y if adm[y] >= 1]
    adm4 = sum(adm.values())
    # What the administrators' label holds, read line by line (TJ: "how do you know grants paid
    # specifically for admins?" -- we do not; the account is NAMED for them).
    runs = defaultdict(int)
    adm_out = 0.0
    for r in J.lines():
        a = A[r['account']]
        if J.fund_group(a) != 'Grants' or 'ADMINISTRATOR' not in a['account_description'] \
                or not J.is_spent(r) or r['fy'] != F0:
            continue
        if r['source'] == 'PRJ':
            runs[float(r['amt'])] += 1
        if r['source'] == 'GEN' and float(r['amt']) < 0 and J.grant_code(a['fund_name']) == '305':
            adm_out += -float(r['amt'])
    run_amt, run_n = max(runs.items(), key=lambda kv: kv[1])
    if run_n < 20:
        fail('the administrators note says one amount recurs in most %s pay runs' % F0)
    esser = {y: sum(m['prog'][(y, PROGRAM[c])] for c in ESSER) for y in Y}
    if esser[F1] > 1 or esser[F0] < 1:
        fail('the page says ESSER paid pay in %s and none in %s' % (F0, F1))
    g0, g1 = m['pay'][(F0, 'Grants')], m['pay'][(F1, 'Grants')]
    if not g1 < g0:
        fail('the page says grant pay fell')
    prog_rows = [dict(label=p, cells=[C.usd(round(m['prog'][(y, p)])) if abs(m['prog'][(y, p)]) >= 0.5
                                      else '' for y in Y]
                      + [C.usd(round(sum(m['prog'][(y, p)] for y in Y)))])
                 for p in progs if abs(sum(m['prog'][(y, p)] for y in Y)) >= 0.5]
    if len(prog_rows) > 30:
        fail('the program table runs past 30 rows: %d' % len(prog_rows))
    # SALARIES BY SCHOOL BUDGET LINE. The account's function code is the line it was charged to;
    # the account's own description is the kind of work. Neither names a post (PAYROLL_GRAIN).
    names = code_names()
    OUT_G = [g for g in OUTS]
    bl = defaultdict(float)             # (fy, group, code)
    ba = defaultdict(float)             # (fy, code, row label) -> one fund program's account
    for (y, k), v in m['acct'].items():
        a = A[k]
        g = J.fund_group(a)
        if g == 'General fund':
            continue
        c = J.function(k)
        if c not in names:
            fail('function code %s has no name; budget-lines-all-funds names every code' % c)
        bl[(y, g, c)] += v
        ba[(y, c, '%s — %s' % (program(a), a['account_description'].title()))] += v
    line_y = lambda y, c, gs=OUT_G: sum(bl[(y, g, c)] for g in gs)
    if any(abs(sum(line_y(y, c) for c in {k[2] for k in bl}) - out_y[y]) > 0.01 for y in Y):
        fail('salaries by budget line do not foot to salaries outside the general fund')
    codes = sorted({k[2] for k in bl}, key=lambda c: (-line_y(F1, c), -sum(line_y(y, c) for y in Y)))
    lbl = lambda c: '%s %s' % (c, names[c])
    cls = {c: J.function_class(c) for c in codes}
    on_line4 = sum(line_y(y, c) for y in Y for c in codes if cls[c] == 'line')
    on_line1 = sum(line_y(F1, c) for c in codes if cls[c] == 'line')
    line_codes = [c for c in codes if cls[c] == 'line']
    usd_or_blank = lambda v: C.usd(round(v)) if abs(v) >= 0.5 else ''

    def line_view(key, label, gs):
        rows = [dict(label=lbl(c), cells=[LINE_CLASS[cls[c]]]
                     + [usd_or_blank(line_y(y, c, gs)) for y in Y]
                     + [C.usd(round(sum(line_y(y, c, gs) for y in Y)))])
                for c in codes if any(abs(line_y(y, c, gs)) >= 0.5 for y in Y)]
        return dict(key=key, label=label, kinds=['stated'] + ['ledger'] * (len(Y) + 1),
                    columns=['On the voted budget'] + X + ['Four years'], rows=rows,
                    note='The line is the grant or fee account’s own function code, mostly a '
                         'heading. Pay re-charged off a school line lands here under that code. '
                         'Stipends included; no account names a position.')
    line_views = [line_view('all', 'Grants and fees', OUT_G)] + [
        line_view('g%d' % i, {'Revolving funds and lunch': 'Fee funds and lunch'}.get(g, g), [g])
        for i, g in enumerate(OUT_G)]
    acct_views = []
    for c in codes:
        labels = sorted({k[2] for k in ba if k[1] == c},
                        key=lambda l: (-ba[(F1, c, l)], -sum(ba[(y, c, l)] for y in Y), l))
        rows = [dict(label=l, cells=[usd_or_blank(ba[(y, c, l)]) for y in Y]
                     + [C.usd(round(sum(ba[(y, c, l)] for y in Y)))])
                for l in labels if any(abs(ba[(y, c, l)]) >= 0.5 for y in Y)]
        if len(rows) > 30:
            fail('%s: more than 30 accounts on one line' % lbl(c))
        if rows:
            acct_views.append(dict(key='c' + c, label=lbl(c), kinds=['ledger'] * (len(Y) + 1),
                                   columns=X + ['Four years'], rows=rows,
                                   note='Each row is a fund and the account’s own name for the '
                                        'kind of work. The ledger posts one line per account per '
                                        'pay run, so it cannot name the positions behind a row.'))
    # Re-charges: pay first booked to a school budget line, then moved onto a grant or fee fund
    # by a year-end entry. The grant side carries the grant account's code, so those dollars
    # sit above under that code, never under the school line they came off.
    import fy_breakdown as FB
    from build_fy_breakdown import line_name
    rc = defaultdict(float)             # (fy, line name) -> re-charged off it
    rc_to = defaultdict(set)            # (fy, line name) -> the funds on the other side
    for r in FB.model()['rows']:
        if not r['account'] or not is_pay(A[r['account']]):
            continue
        for (rule, py), v in r['payers'].items():
            if rule == 'moved' and not py.startswith('General fund') and v:
                rc[(r['fy'], line_name(r))] += float(v)
                rc_to[(r['fy'], line_name(r))].add(py)
    rc_views = []
    for y in Y:
        rows = sorted([(n, v) for (fy, n), v in rc.items() if fy == y and round(v)],
                      key=lambda kv: (-kv[1], kv[0]))
        if len(rows) > 30:
            fail('%s: more than 30 school lines re-charged' % C.fy(y))
        rc_views.append(dict(key='rc%d' % y, label=C.fy(y), kinds=['ledger', 'ledger'],
                             columns=['Re-charged off the line', 'Onto'],
                             rows=[dict(label=n, cells=[C.usd(round(v)), ', '.join(sorted(rc_to[(y, n)]))])
                                   for n, v in rows],
                             note='The school-line pages show the same entries as Re-charged to. '
                                  'One entry can move several lines onto several funds; it does '
                                  'not pair each line with one fund.'))
    line_rank = TB.chart(
        TP.ranking('Grant and fee salaries by budget line',
                   [(lbl(c), [round(sum(bl[(y, g, c)] for y in Y)) for g in OUT_G]) for c in codes],
                   '$', highlight=[lbl(c) for c in line_codes], stack=OUT_G,
                   note='Four years, %s to %s, by the function code each salary account carries. '
                        'Highlighted: the voted budget lines.' % (C.fy(F0), C.fy(F1)),
                   note_figures={'y': F(F0), 'z': F(F1)}),
        place='body',
        so=('Of %s in grant and fee salaries over four years, %s sat on a line the budget votes; '
            'the rest is booked to a heading, no code, or food services, so no voted line shows it.'
            % (C.usd(round(out4)), C.usd(round(on_line4))), {'a': U(out4), 'b': U(on_line4)}))
    KINDS = [k for _, k in KIND] + ['Other pay']
    out['salaries-from-grants-and-fees'] = TP.page(
        'salaries-from-grants-and-fees',
        'Grants and fee funds paid %s of school salaries in four years; no account names the job.'
        % C.usd(round(out4)),
        [f('p-out4', U(out4), 'salaries outside the general fund, %s to %s' % (C.fy(F0), C.fy(F1)),
           'published', {'y': F(F0), 'z': F(F1)}),
         f('p-share', P(share1), 'of all school salaries, %s' % C.fy(F1), 'published', {'y': F(F1)}),
         f('p-gr4', U(grants4), 'from grants, four years', 'published'),
         f('p-rv4', U(rev4), 'from fee funds and lunch, four years', 'published'),
         f('p-idea', U(idea4), 'from the IDEA special education grant', 'published'),
         f('p-sup', U(sup4), 'grant pay booked as support salaries', 'published'),
         f('p-adm', U(adm4), 'on grant accounts named for administrators, net', 'published'),
         f('p-g0', U(g0), 'grant pay, %s' % C.fy(F0), 'published', {'y': F(F0)}),
         f('p-g1', U(g1), 'grant pay, %s' % C.fy(F1), 'published', {'y': F(F1)}),
         f('p-es', U(esser[F0]), 'of it from the pandemic grants, %s' % C.fy(F0), 'published',
           {'y': F(F0)}),
         f('p-who', None, 'which jobs each grant pays', 'gap',
           closes='the Town’s payroll distribution report: each employee’s pay by fund and account')],
        [con('Grants and fee funds paid %s of school salaries in four years, and %s of all of them in %s.'
             % (C.usd(round(out4)), C.pct(share1), C.fy(F1)), ['p-out4', 'p-share', 'p-gr4', 'p-rv4'],
             {'a': U(out4), 'p': P(share1), 'y': F(F1)}),
         con('IDEA paid the most grant pay, %s; grants booked %s of their pay as support salaries.'
             % (C.usd(round(idea4)), C.usd(round(sup4))), ['p-idea', 'p-sup', 'p-who'],
             {'a': U(idea4), 'b': U(sup4)},
             notes=[step('A support salary may be a paraprofessional, a therapist or another post; '
                         'the account does not say which.', 'gap',
                         closes='the Town’s payroll distribution report, or the district’s IDEA '
                                'grant budget filed with DESE')]),
         con('Grant accounts named for administrators’ pay held %s net over four years; the name is a label.'
             % C.usd(round(adm4)), ['p-adm', 'p-who'], {'a': U(adm4)},
             notes=[step('In %s, %s pay runs charged the same %s to them, first Title I, then Title IV.'
                         % (C.fy(F0), C.num(run_n), C.usd(run_amt)), 'measured',
                         {'y': F(F0), 'n': N(run_n), 'a': figure(run_amt, C.usd(run_amt))}),
                    step('A school memo then moved %s of the Title I part to instructional salaries.'
                         % C.usd(round(adm_out)), 'measured', {'a': U(adm_out)}),
                    step('The family engagement grant’s account also paid parent stipends by invoice.',
                         'measured')]),
         con('Grant pay fell from %s in %s to %s in %s; pandemic grants paid %s of the first.'
             % (C.usd(round(g0)), C.fy(F0), C.usd(round(g1)), C.fy(F1), C.usd(round(esser[F0]))),
             ['p-g0', 'p-g1', 'p-es'],
             {'a': U(g0), 'y': F(F0), 'b': U(g1), 'z': F(F1), 'c': U(esser[F0])})],
        chart=TP.series('School salaries outside the general fund', X,
                        [TP.track(g, [round(m['pay'][(y, g)]) for y in Y]) for g in OUTS],
                        '$', kind='bar', stacked=True, totals=True,
                        note='Wages posted to grants and other funds, with pay moved in or out by '
                             'journal entry. Benefits are left out.'),
        also=[TP.series('Grant salaries, by kind of work', X,
                        [TP.track(k, [round(m['kind'][(y, k)]) for y in Y]) for k in KINDS
                         if any(abs(m['kind'][(y, k)]) >= 1 for y in Y)],
                        '$', kind='bar', stacked=True,
                        note='The kind is the account’s own name. No account names a job.')],
        tables=[dict(caption='Salaries by fund or grant, each year', views=[dict(
            key='programs', label='Four years', kinds=['ledger'] * (len(Y) + 1),
            columns=X + ['Four years'], rows=prog_rows,
            note='Grants by their DESE program, every award year together; other funds by name. '
                 'Program names are ours.')]),
            dict(caption='Salaries by school budget line, each year', views=line_views),
            dict(caption='Which accounts paid salaries on each line', views=acct_views),
            dict(caption='School salary lines re-charged onto grants and fees', views=rc_views)],
        blocks=[line_rank],
        finding_figures={'a': U(out4)},
        sources=src)

    # ================================================== pay moved between funds
    mv = m['moved']
    gf_off = {y: -sum(v for (fy, k), v in mv.items() if fy == y and v < 0
                       and J.fund_group(A[k]) == 'General fund') for y in Y}
    gf_on = {y: sum(v for (fy, k), v in mv.items() if fy == y and v > 0
                    and J.fund_group(A[k]) == 'General fund') for y in Y}
    off4, on4 = sum(gf_off.values()), sum(gf_on.values())
    gf_moves = [(fy, k, v) for (fy, k), v in mv.items() if J.fund_group(A[k]) == 'General fund']
    big = min(gf_moves, key=lambda t: t[2])
    big_to = sorted(m['other'][(big[0], big[1])])
    # One memo can move several lines onto several grants, so a line is not paired with one
    # grant: the page says "onto grants", and only if every other side is a grant.
    grant_names = {program(a) for a in A.values() if J.fund_group(a) == 'Grants'}
    if any(p_ not in grant_names for p_ in big_to):
        fail('the largest move is no longer onto grants alone: %s' % big_to)
    fee = {y: sum(v for (fy, k), v in mv.items() if fy == y and A[k]['fund'] == FEE_FUND) for y in Y}
    fee_y = min(Y, key=lambda y: fee[y])
    if not fee[fee_y] < -100000:
        fail('the page says the athletic fee fund had pay moved off it in one year')
    coach = [k for (fy, k), v in mv.items() if fy == fee_y and v > 0
             and A[k]['account_description'] == 'ATHLETIC COACHES']
    if len(coach) != 1:
        fail('the fee fund move is no longer to the athletic coaches account')
    coach_v = mv[(fee_y, coach[0])]
    # Read on the grant's side: the #237 pay moved against extended day (fund 1312), each year.
    g237 = defaultdict(float)
    for (fy, k), v in mv.items():
        if J.grant_code(A[k]['fund_name']) == '237' and \
                any('Extended Day' in o for o in m['other'][(fy, k)]):
            g237[fy] += v
    pair = [round(abs(g237[y])) for y in Y]
    if pair != [35400] * len(Y):
        fail('the extended day / #237 move is no longer $35,400 every year: %s' % pair)
    views = []
    for y in Y:
        rows = sorted([(k, v) for (fy, k), v in mv.items() if fy == y and abs(v) >= MOVE_ROW_MIN],
                      key=lambda kv: kv[1])
        if len(rows) > 30:
            fail('%s: more than 30 moves past the floor' % C.fy(y))
        views.append(dict(key='fy%d' % y, label=C.fy(y), kinds=['ledger', 'ledger', 'ledger'],
                          columns=['Moved', 'The other side', 'Entry, as printed'],
                          rows=[dict(label='%s — %s' % (program(A[k]), A[k]['account_description'].title()),
                                     cells=[C.usd(round(v)), short(sorted(m['other'][(y, k)])),
                                            '; '.join(m['why'][(y, k)])[:80]])
                                for k, v in rows],
                          note='Below zero: pay taken off this account and put on the other side. '
                               'Moves under %s are left out.' % C.usd(MOVE_ROW_MIN)))
    out['pay-moved-between-funds'] = TP.page(
        'pay-moved-between-funds',
        'Journal entries moved %s of general fund pay onto other funds in four years, and %s back.'
        % (C.usd(round(off4)), C.usd(round(on4))),
        [f('m-off', U(off4), 'general fund pay moved onto other funds', 'published'),
         f('m-on', U(on4), 'other funds’ pay moved onto the general fund', 'published'),
         f('m-n', N(m['n_moves'], 'entries'), 'journal entries that moved pay, %s to %s'
           % (C.fy(F0), C.fy(F1)), 'published', {'y': F(F0), 'z': F(F1)}),
         f('m-big', U(-big[2]), '%s, %s' % (A[big[1]]['account_description'].lower()[:28], C.fy(big[0])),
           'published', {'y': F(big[0])}, allow=tuple(re.findall(r'\d+', A[big[1]]['account_description']))),
         f('m-fee', U(-fee[fee_y]), 'athletic fee fund pay moved off it, %s' % C.fy(fee_y),
           'published', {'y': F(fee_y)}),
         f('m-coach', U(coach_v), 'of it onto general fund coaches’ pay', 'published'),
         f('m-35', U(35400), 'between extended day and one grant, each year', 'published'),
         f('m-why', None, 'why each entry was made', 'gap',
           closes='the school business office memos the entries cite')],
        [con('Year-end entries moved %s of general fund pay onto grants and fees; %s came back.'
             % (C.usd(round(off4)), C.usd(round(on4))), ['m-off', 'm-on', 'm-n'],
             {'a': U(off4), 'b': U(on4)},
             notes=[step('Most cite a school memo; the memos are not in this archive.', 'gap',
                         closes='the school business office memos the entries cite')]),
         con('The largest: %s of %s pay moved onto grants in one %s entry.'
             % (C.usd(round(-big[2])), A[big[1]]['account_description'].lower(), C.fy(big[0])),
             ['m-big'], {'a': U(-big[2]), 'y': F(big[0])},
             allow=tuple(re.findall(r'\d+', A[big[1]]['account_description'])),
             notes=[step('The same entry put pay on %s; it does not pair each line with one grant.'
                         % short(big_to, 4), 'measured',
                         allow=tuple(re.findall(r'\d+', ' '.join(big_to))))]),
         con('In %s, %s of the athletic fee fund’s pay moved onto the general fund, %s to coaches.'
             % (C.fy(fee_y), C.usd(round(-fee[fee_y])), C.usd(round(coach_v))),
             ['m-fee', 'm-coach'], {'y': F(fee_y), 'a': U(-fee[fee_y]), 'b': U(coach_v)},
             notes=[step('So that year the general fund carried coaches’ pay first booked to the fee '
                         'fund, not the other way round.', 'measured')]),
         con('%s moved between extended day and the family engagement grant in each of the four years.'
             % C.usd(35400), ['m-35'], {'a': U(35400)},
             notes=[step('The %s entry calls it a portion of one person’s pay; the name is redacted.'
                         % C.fy(F0), 'measured', {'y': F(F0)})])],
        chart=TP.series('General fund pay moved by journal entry', X, [
            TP.track('Moved onto other funds', [round(gf_off[y]) for y in Y]),
            TP.track('Moved back onto the general fund', [round(gf_on[y]) for y in Y])],
            '$', kind='bar',
            note='Entries that move pay between funds and net to zero; accruals and duplicate '
                 'reversals are left out.'),
        tables=[dict(caption='Every pay move over the floor, by year', views=views)],
        finding_figures={'a': U(off4), 'b': U(on4)},
        sources=src)

    # ================================================== positions and their funds
    cw = list(csv.DictReader(open(CROSSWALK, encoding='utf-8')))
    for r in cw:
        if r['account'] and r['account'] not in A:
            fail('crosswalk: %s names account %s, which the journal does not hold'
                 % (r['role'], r['account']))
        if r['account'] and not is_pay(A[r['account']]):
            fail('crosswalk: %s names a non-pay account' % r['role'])
    byrole = {r['role']: r for r in cw}
    paid = lambda r, y: m['acct'][(y, r['account'])] if r['account'] else None
    moved_r = lambda r: sum(mv.get((y, r['account']), 0.0) for y in Y) if r['account'] else 0.0
    pos_rows = []
    for r in cw:
        mvv = moved_r(r)
        pos_rows.append(dict(label=r['role'], cells=[r['budget_line'] or 'none by this title']
                             + [C.usd(round(paid(r, y))) if r['account'] else '—' for y in Y]
                             + [C.usd(round(mvv)) if abs(mvv) >= 1 else 'none']))
    ad, ssc, food = (byrole['Athletic Director'], byrole['Student Services Coordinator (Spec Ed)'],
                     byrole['Director of Food Services'])
    if A[ad['account']]['fund'] != '0100' or abs(moved_r(ad)) >= 1:
        fail('the page says the athletic director is general fund pay and none was moved')

    gf_lead = [r for r in cw if r['account'] and A[r['account']]['fund'] == '0100']
    gf_moved = [r['role'] for r in gf_lead if abs(moved_r(r)) >= 1]
    if len(gf_moved) != 2:
        fail('the page names two leadership accounts with pay moved: %s' % gf_moved)
    moved_detail = [('%s, %s' % (r['role'], 'moved off' if mv.get((y, r['account']), 0) < 0
                                 else 'moved on'), y, abs(mv[(y, r['account'])]))
                    for r in gf_lead for y in Y if abs(mv.get((y, r['account']), 0)) >= 1]
    out['positions-and-their-funds'] = TP.page(
        'positions-and-their-funds',
        'Of %s general fund leadership accounts, %s had any pay moved to or from another fund.'
        % (C.num(len(gf_lead)), C.num(len(gf_moved))),
        [f('q-ad0', U(paid(ad, F0)), 'athletic director’s account, %s' % C.fy(F0), 'published',
           {'y': F(F0)}),
         f('q-ad1', U(paid(ad, F1)), 'the same, %s' % C.fy(F1), 'published', {'y': F(F1)}),
         f('q-food', U(paid(food, F1)), 'lunch fund department-head pay, %s' % C.fy(F1), 'published',
           {'y': F(F1)}),
         f('q-n', N(len(gf_lead), 'posts'), 'general fund leadership accounts read', 'published'),
         f('q-mv', N(len(gf_moved), 'posts'), 'of them with pay moved to another fund', 'published'),
         f('q-who', None, 'which post each grant support salary pays', 'gap',
           closes='the Town’s payroll distribution report: each employee’s pay by fund and account')],
        [con('The athletic director’s pay came from the general fund: %s in %s, %s in %s.'
             % (C.usd(round(paid(ad, F0))), C.fy(F0), C.usd(round(paid(ad, F1))), C.fy(F1)),
             ['q-ad0', 'q-ad1'],
             {'a': U(paid(ad, F0)), 'y': F(F0), 'b': U(paid(ad, F1)), 'z': F(F1)},
             notes=[step('The fee fund paid coaches, not the director, as coded; see pay moved '
                         'between funds.', 'measured')]),
         con('Only %s of %s general fund leadership accounts had any pay moved to or from another fund.'
             % (C.num(len(gf_moved)), C.num(len(gf_lead))),
             ['q-n', 'q-mv'], {'a': N(len(gf_moved)), 'n': N(len(gf_lead))},
             notes=[step('%s %s: %s.' % (C.fy(y_), r_, C.usd(round(v_))), 'measured',
                         {'y': F(y_), 'a': U(v_)})
                    for r_, y_, v_ in moved_detail]),
         con('One post is paid from a fee fund by name: the lunch fund’s department head, %s in %s.'
             % (C.usd(round(paid(food, F1))), C.fy(F1)), ['q-food'],
             {'a': U(paid(food, F1)), 'y': F(F1)},
             notes=[step('That it pays the Director of Food Services is our reading of its name.',
                         'hypothesis')])],
        chart=TP.series('Leadership pay by account', X,
                        [TP.track(r['role'], [round(paid(r, y)) for y in Y]) for r in
                         [ad, ssc, byrole['Superintendent'], byrole['Instructional Services Director'],
                          food]],
                        '$', note='Each account as the ledger names it. Paid includes pay moved in '
                                  'or out by journal entry.'),
        tables=[dict(caption='Leadership posts: budget line, account paid, and pay moved', views=[dict(
            key='posts', label='Posts', kinds=['stated'] + ['ledger'] * (len(Y) + 1),
            columns=['Budget book line, FY2027 workbook'] + X + ['Moved to or from another fund'],
            rows=pos_rows,
            note='Which post an account pays is our pairing of title, budget line and account name; '
                 'the basis for each is in position-funds-crosswalk.csv.')])],
        finding_figures={'n': N(len(gf_lead)), 'a': N(len(gf_moved))},
        sources=src)
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t): json.dumps(p, indent=1, ensure_ascii=False,
                                                              sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != text]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('pay by fund: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
