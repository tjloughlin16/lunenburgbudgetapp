#!/usr/bin/env python3
"""SPENDING THAT STOPPED: what the FY2026 school budget assumed from FY2025 that the ledger does not
show happening in FY2026. One topic page on the FY2026 school year end shelf.

    python3 scripts/build_why_it_was_left.py           # write fy28/public/data/topics/why-it-was-left.json
    python3 scripts/build_why_it_was_left.py --check   # fail if it would change

TJ, 26 November 2026: *"what we tried to do in other places is to answer it from the ledger ...
Something has to show in the ledger"* and *"can we answer WHAT wasn't paid for that WAS paid for
in previous years?!"* -- and, on the spine: *"what did they budget for they didnt end up paying
for, because they use last year's budget for the next year, but that assumes the needs are
driving from the same place. we should be able to tell that from the ledger."*

THREE TESTS, each read off the MUNIS journal (scripts/journal.py), scope fund 0100 department 300
-- the scope of the period-13 `gf-school` spreadsheets, to which the journal ties to the cent:

1. BUDGET AGAINST LAST YEAR'S SPENDING. For the six categories that left the most in FY2026
   (out-of-district tuition among them -- TJ, 27 November 2026, on finding it left out: "no its
   not excluded"), the FY2026 budget and the FY2026
   spending, each as a change on what FY2025 actually spent. Categories, and what was left in
   each, are build_journal_surplus_topics.data()'s, asserted to foot here.
2. PAYROLL BY MONTH. Every salary account in those categories that posted payroll in at least
   three months of FY2025 in which it posted none in FY2026. A RECODE CHECK beside each: any
   other general fund account with the same object code whose payroll in those months rose
   above FY2025's. Payroll lines carry no person (journal.PAYROLL_GRAIN), so a silent account
   is NOT a vacancy: a leave, pay moved to another account, or a grant paying would all post the
   same way. The page says "no payroll posted", never more.
3. RECURRING PURCHASES. Every named vendor paid in both FY2024 and FY2025 on the school general
   fund whose FY2026 payments (invoices and orders open at the close) fell by MIN_DROP or more,
   with each year's amount and the invoice descriptions saying what was bought. Each is checked
   against three other routes the same thing could have been paid by, and the route found is
   printed beside it rather than the row being dropped:
     - a later name for the same vendor (RENAMED, declared one at a time with its basis);
     - the same vendor paid from another school fund in FY2026;
     - journal entries with no payee on the same accounts in FY2026 (how most of FY2026's
       health insurance was charged -- the MIIA invoices alone fall by $847k while the account's
       spending rose).
   And the reverse: vendors whose FY2026 payments rose by MIN_DROP or more, so the page is not
   one-sided.

RULE 7. Every figure is a posting. Why a payment stopped -- a contract ended, a service moved,
a need fell away, a bill not yet sent -- is not in a ledger, and the page says so.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
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
import build_journal_surplus_topics as JS  # noqa: E402
import build_school_surplus as S  # noqa: E402

ID = 'why-it-was-left'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
Y0, Y1 = 2025, 2026
D0 = Decimal(0)
SPEND = ('payroll', 'invoice', 'journal entry', 'receipt', 'encumbrance')
TOP_CATS = 6                 # the categories that left the most in FY2026
EXPECT_CATS = ['buildings', 'counselors', 'teachers', 'benefits', 'tuition', 'supplies']
SILENT_MONTHS = 3            # months FY2025 paid and FY2026 did not, for a salary account to show
MIN_DROP = Decimal(5000)     # a recurring vendor shows when FY2026 is this much below FY2025
NEW_ROWS = 15
MONTHS = ('07', '08', '09', '10', '11', '12', '01', '02', '03', '04', '05', '06')
MONTH_NAME = dict(zip(MONTHS, ('Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar',
                               'Apr', 'May', 'Jun')))
# A LATER NAME FOR THE SAME VENDOR, declared one at a time with the evidence. Not merged: the row
# stays, and the payment under the new name is printed beside it.
RENAMED = {
    # FY2025 invoices to POWERSCHOOL GROUP LL read `SCHOOL SPRING 2024` and `SCHOOL MESSENGER 2`;
    # FY2026 invoices to POWERSCHOOL HOLDINGS read `SCHOOL SPRING FY 2` and `SCHOOL MESSENGER/H`,
    # on the same account (CONTRACTED SERVICES, 1450). Same products, same account.
    'POWERSCHOOL GROUP LL': 'POWERSCHOOL HOLDINGS',
}
PSYCH_PAGE = 'fy2026-staff-lines'


def fail(msg):
    raise SystemExit('build_why_it_was_left: ' + msg)


def fl(x):
    return float(x)


def usd2(x):
    x = float(x)
    return ('-$' if x < 0 else '$') + format(abs(x), ',.2f')


def is_payroll(r):
    return r['posts_to'] == 'actual' and J.KIND_OF[r['source']] == 'payroll'


def data():
    A = J.accounts()
    L = J.lines()
    gf = [r for r in L if J.in_surplus_scope(A[r['account']])]
    js = JS.data()
    label = {c[0]: c[1] for c in S.CATEGORIES}
    d = dict(label=label)

    # ---- 1. budget against last year's spending, by category
    pc = lambda y, c, p: js['cat'].get((y, c, p), D0)
    bud = lambda y, c: pc(y, c, 'original_budget') + pc(y, c, 'carry_forward') + pc(y, c, 'transfer')
    spent = lambda y, c: sum((pc(y, c, p) for p in SPEND), D0)
    for y in J.YEARS:
        for c in label:
            if bud(y, c) - spent(y, c) != js['cat_left'][(y, c)]:
                fail('%s in %d: budget less spending is not what was left' % (c, y))
    ranked = sorted(label, key=lambda c: -js['cat_left'][(Y1, c)])
    cats = ranked[:TOP_CATS]
    if cats != EXPECT_CATS:
        fail('the six categories that left most are now %s; rewrite the page' % cats)
    d['cats'] = cats
    d['bud'] = {(y, c): bud(y, c) for y in J.YEARS for c in cats}
    d['spent'] = {(y, c): spent(y, c) for y in J.YEARS for c in cats}
    d['left'] = {(y, c): js['cat_left'][(y, c)] for y in J.YEARS for c in cats}
    d['orig'] = {(y, c): pc(y, c, 'original_budget') for y in J.YEARS for c in cats}

    # ---- 2. payroll by month, per salary account
    pay = defaultdict(lambda: defaultdict(lambda: D0))
    for r in gf:
        if is_payroll(r):
            pay[(r['account'], r['fy'])][r['effective_date'][5:7]] += r['amt']
    silent = []
    for a in sorted({r['account'] for r in gf if JS.cat_of(r) in cats}):
        p0, p1 = pay.get((a, Y0), {}), pay.get((a, Y1), {})
        gone = [m for m in MONTHS if p0.get(m, D0) > 0 and p1.get(m, D0) <= 0]
        if len(gone) < SILENT_MONTHS:
            continue
        budget = sum((r['amt'] for r in gf if r['account'] == a and r['fy'] == Y1
                      and r['posts_to'] in ('original_budget', 'transfer')), D0)
        paid1 = sum(pay.get((a, Y1), {}).values(), D0)
        # Only what the FY2026 budget ASSUMED: budgeted, and paid less than that budget. An account
        # with no FY2026 budget, or paid past it, is not where money was left.
        if budget <= 0 or paid1 >= budget:
            continue
        # THE RECODE CHECK: like accounts -- same DESE function and object code, another building
        # -- whose payroll in the silent months rose on FY2025's.
        obj, fn = A[a]['object'], a.split('-')[3]
        moved = []
        for b in sorted({k for (k, y) in pay if k != a and A[k]['object'] == obj
                         and k.split('-')[3] == fn}):
            q0, q1 = pay.get((b, Y0), {}), pay.get((b, Y1), {})
            up = sum((q1.get(m, D0) - q0.get(m, D0) for m in gone), D0)
            if up > 0:
                moved.append((b, up))
        cat = JS.cat_of(dict(account=a, object=obj))
        silent.append(dict(account=a, desc=A[a]['account_description'], cat=cat, gone=gone,
                           pay={y: dict(pay.get((a, y), {})) for y in (Y0, Y1)},
                           paid={y: sum(pay.get((a, y), {}).values(), D0) for y in (Y0, Y1)},
                           budget=budget, moved=moved, lost=sum((p0.get(m, D0) for m in gone), D0)))
    d['silent'] = silent

    # ---- 3. recurring vendors, and the other routes checked
    spent_lines = [r for r in L if r['posts_to'] in ('actual', 'encumbrance')]
    v = defaultdict(lambda: D0)          # (payee, fy) on the general fund scope
    accts = defaultdict(set)              # payee -> accounts (general fund scope)
    by_cat = defaultdict(lambda: D0)      # (payee, fy, category): where the money went
    what = defaultdict(list)              # (payee, fy) -> descriptions, largest first
    other_fund = defaultdict(lambda: D0)  # (payee, fy) outside the scope
    for r in spent_lines:
        p = J.payee(r)
        if p is None or p is J.MASKED:
            continue
        if J.in_surplus_scope(A[r['account']]):
            v[(p, r['fy'])] += r['amt']
            accts[p].add(r['account'])
            by_cat[(p, r['fy'], JS.cat_of(r))] += r['amt']
            if r['posts_to'] == 'actual' and r['description'].strip():
                what[(p, r['fy'])].append((r['amt'], r['description'].strip()))
        else:
            other_fund[(p, r['fy'])] += r['amt']
    no_payee = defaultdict(lambda: D0)    # account -> FY2026 journal entries with no payee
    for r in gf:
        if r['fy'] == Y1 and r['posts_to'] == 'actual' and r['ref_type'] != 'VND' and not is_payroll(r):
            no_payee[r['account']] += r['amt']
    # FOOTING: named vendors, masked payees and lines with no payee make up the scope's spending.
    rest = J.rollup([r for r in spent_lines if J.in_surplus_scope(A[r['account']])
                     and (J.payee(r) is None or J.payee(r) is J.MASKED)], 'fy')
    for y in J.YEARS:
        named = sum((a for (p, yy), a in v.items() if yy == y), D0)
        if named + rest.get((y,), D0) != sum((d['spent'][(y, c)] for c in cats), D0) + sum(
                (sum((js['cat'].get((y, c, pp), D0) for pp in SPEND), D0)
                 for c in label if c not in cats), D0):
            fail('vendors in %d do not foot to the scope’s spending' % y)
    for old, new in RENAMED.items():
        if not v.get((old, Y0)) or not v.get((new, Y1)):
            fail('rename %s -> %s: no longer paid under the old name in FY%d and the new in FY%d'
                 % (old, new, Y0, Y1))
    yrs = J.YEARS
    payees = {p for (p, _) in v}

    def cat_of(p, y):
        got = {c: a for (q, yy, c), a in by_cat.items() if q == p and yy == y and a > 0}
        return max(sorted(got), key=lambda c: got[c])

    def descs(p, y, n=3):
        seen, out = set(), []
        for amt, t in sorted(what.get((p, y), []), key=lambda x: -x[0]):
            if t.upper() not in seen:
                seen.add(t.upper())
                out.append(t)
        return out[:n]

    stopped, grew = [], []
    for p in payees:
        s = {y: v.get((p, y), D0) for y in yrs}
        if s[2024] > 0 and s[Y0] > 0 and s[Y0] - s[Y1] >= MIN_DROP:
            routes = []
            if p in RENAMED and v.get((RENAMED[p], Y1)):
                routes.append(('renamed', v[(RENAMED[p], Y1)]))
            if other_fund.get((p, Y1), D0) > 0:
                routes.append(('fund', other_fund[(p, Y1)]))
            jn = sum((no_payee[a] for a in accts[p]), D0)
            if jn > 0:
                routes.append(('journal', jn))
            cat = cat_of(p, Y0)
            net = max(D0, s[Y0] - s[Y1] - sum((x for _, x in routes), D0))
            stopped.append(dict(payee=p, s=s, drop=s[Y0] - s[Y1], routes=routes, cat=cat, net=net,
                                was=descs(p, Y0), now=descs(p, Y1)))
        if p not in RENAMED.values() and s[Y1] - s[Y0] >= MIN_DROP:
            cat = cat_of(p, Y1)
            grew.append(dict(payee=p, s=s, rise=s[Y1] - s[Y0], cat=cat, now=descs(p, Y1)))
    stopped.sort(key=lambda x: -x['drop'])
    grew.sort(key=lambda x: -x['rise'])
    d['stopped'], d['grew'] = stopped, grew
    # the two cases the header names, asserted so the prose about them cannot drift
    by = {x['payee']: x for x in stopped}
    miia = by.get('MIIA HEALTH BENEFITS')
    if not miia or not any(k == 'journal' for k, _ in miia['routes']):
        fail('MIIA no longer appears with its payee-less journal entries beside it')
    if 'POWERSCHOOL GROUP LL' not in by or not any(k == 'renamed' for k, _ in by['POWERSCHOOL GROUP LL']['routes']):
        fail('PowerSchool no longer appears with its new name beside it')
    return d


def page(d):
    cats, label = d['cats'], d['label']
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    N = lambda n, unit: figure(n, C.num(n), unit)
    P = lambda x, dp=1: figure(round(fl(x), dp), C.pct(x, dp), 'percent')
    fy0, fy1 = C.fy(Y0), C.fy(Y1)
    many = {5: 'five', 6: 'six', 7: 'seven'}[len(cats)]   # the count, as the prose says it

    # ---- 1. the signature: FY2026's budget and spending, each against FY2025's spending
    chg = lambda num, c: 100 * (fl(num) / fl(d['spent'][(Y0, c)]) - 1)
    b_up = {c: chg(d['bud'][(Y1, c)], c) for c in cats}
    s_up = {c: chg(d['spent'][(Y1, c)], c) for c in cats}
    above = [c for c in cats if b_up[c] > 0]
    fell = [c for c in cats if s_up[c] < 0]
    left5 = sum((d['left'][(Y1, c)] for c in cats), D0)
    gap = {c: b_up[c] - s_up[c] for c in cats}
    widest = max(cats, key=lambda c: gap[c])
    if above != cats:
        fail('the conclusion says all five were budgeted above FY2025 spending; now %s' % above)
    if widest != 'buildings':
        fail('the conclusion names building upkeep as the widest gap; it is now %s' % widest)
    chart = TP.series(
        'Budget and spending against last year', [label[c] for c in cats],
        [TP.track('%s budget, change on %s spending' % (fy1, fy0), [round(b_up[c], 1) for c in cats],
                  'published', 'bar'),
         TP.track('%s spending, change on %s spending' % (fy1, fy0), [round(s_up[c], 1) for c in cats],
                  'published', 'bar')],
        '%', kind='bar', decimals=1,
        note='School general fund. The gap between the two bars is what each category left in %s.' % fy1,
        note_figures={'y': F(Y1)})

    def year_view(y):
        prior = lambda c: d['spent'].get((y - 1, c))
        return dict(key='fy%d' % y, label=C.fy(y), total_col=None, kinds=['ledger'] * 4,
                    columns=['Budget', 'Spent', 'Left', 'Budget against last year’s spending'],
                    rows=[dict(label=label[c], cells=[
                        C.usd(fl(d['bud'][(y, c)])), C.usd(fl(d['spent'][(y, c)])),
                        C.usd(fl(d['left'][(y, c)])),
                        C.pct(100 * (fl(d['bud'][(y, c)]) / fl(prior(c)) - 1), 1) if prior(c) else '—'])
                          for c in cats],
                    note='Budget includes orders carried in and every transfer; spent includes orders '
                         'open at the close.')
    years_table = dict(caption='Budget, spending and what was left, four years',
                       views=[year_view(y) for y in reversed(J.YEARS)])

    f = LD.fact
    facts = [
        f('left5', U(left5), 'left by these %s categories in %s' % (many, fy1), 'published',
          label_figures={'y': F(Y1)}),
        f('above', figure(len(above), '%d of %d' % (len(above), len(cats)), 'categories'),
          'categories budgeted above last year’s spending', 'published'),
        f('fell', figure(len(fell), '%d of %d' % (len(fell), len(cats)), 'categories'),
          'categories that spent less than the year before', 'published'),
        f('upk', P(b_up['buildings']), 'building upkeep budget, above %s spending' % fy0, 'published',
          label_figures={'y': F(Y0)}),
    ]
    con = TP.conclusion
    conclusions = [
        con('All %d were budgeted above what they spent in %s; %d of them then spent less than that.'
            % (len(cats), fy0, len(fell)), ['left5', 'above', 'fell'],
            {'n': N(len(cats), 'categories'), 'y': F(Y0), 'f': N(len(fell), 'categories')},
            so='The budget carried last year’s needs forward and more; the spending did not follow.'),
        con('Building upkeep was budgeted %s above its %s spending and spent %s less.'
            % (C.pct(b_up['buildings'], 1), fy0, C.pct(-s_up['buildings'], 1)), ['upk'],
            {'a': P(b_up['buildings']), 'y': F(Y0), 'b': P(-s_up['buildings'])},
            so='The widest gap of the %s: the budget grew while the bills fell.' % many),
    ]

    # ---- 2. payroll by month
    sil = d['silent']
    if len(sil) < 1:
        fail('no salary account went silent; rewrite the page')
    tracks = []
    for s in sil:
        code = s['account'].split('-')[3] + '-' + s['account'].split('-')[4]
        tracks.append(((s['desc'].title() + ' · ' + code, None, (code,)),
                       [TB.track((C.fy(y), {'y': F(y)}),
                                 ['paid' if s['pay'][y].get(m, D0) > 0 else 'none' for m in MONTHS])
                        for y in (Y0, Y1)]))
    lost = sum((s['lost'] for s in sil), D0)
    moved = sum((x for s in sil for _, x in s['moved']), D0)
    if not moved < lost / 2:
        fail('pay on like accounts now covers half the silent months; rewrite the conclusion')
    timeline = TB.timeline(
        'Payroll posted, month by month', [MONTH_NAME[m] for m in MONTHS], tracks,
        [('paid', 'Payroll posted', 'good'), ('none', 'No payroll posted', 'muted')],
        note=('Salary accounts in these categories with payroll in %d or more months of %s and none '
              'in those months of %s. A payroll line names no person.' % (SILENT_MONTHS, fy0, fy1),
              {'k': N(SILENT_MONTHS, 'months'), 'a': F(Y0), 'b': F(Y1)}))
    facts += [
        f('silent', N(len(sil), 'salary accounts'), 'salary accounts with months of no payroll',
          'published'),
        f('lost', U(lost), 'paid in %s in the months that went silent' % fy0, 'published',
          label_figures={'y': F(Y0)}),
        f('moved', U(moved), 'rise in those months on like accounts', 'published'),
    ]
    if sorted(s['desc'] for s in sil) != ['PSYCHOLOGISTS SALARIES', 'SOCIAL WORKERS SALARIES']:
        fail('the silent accounts are now %s; rewrite the conclusion' % [s['desc'] for s in sil])
    conclusions.append(con(
        'A social worker and a psychologist account posted no payroll in months that paid %s in %s.'
        % (C.usd(fl(lost)), fy0), ['silent', 'lost', 'moved'],
        {'a': U(lost), 'y': F(Y0)},
        so='Like accounts rose %s in those months. A silent account may be a vacancy, a leave or a grant.'
           % C.usd(fl(moved)), so_figures={'m': U(moved)}))

    # ---- 3. the recurring purchases
    def route_text(routes):
        if not routes:
            return 'None found'
        words = {'renamed': 'Paid under a later name %s', 'fund': 'Another school fund paid %s',
                 'journal': 'Entries with no payee on its accounts, %s'}
        return '; '.join(words[k] % C.usd(fl(a)) for k, a in routes)

    st = d['stopped']
    unexplained = [x for x in st if x['net'] > 0]
    drop_all = sum((x['drop'] for x in st), D0)
    drop_net = sum((x['net'] for x in st), D0)
    yrs = (2024, Y0, Y1)    # the test reads these three; FY2023 is in the journal CSV
    # THE DIFFERENCE IS PRINTED, not left to the reader. TJ, 27 November 2026: "i want to see the
    # DIFFs too. i am mentally doing the math constantly to find the problem lines."
    chg = 'Change on %s' % fy0
    cols = [C.fy(y) for y in yrs] + [chg, 'Still short', 'Other route in %s' % fy1,
                                     'What was bought']
    kinds = ['ledger'] * len(cols)
    stop_rows = [dict(label='%s · %s' % (x['payee'], label[x['cat']]),
                      cells=[C.usd(fl(x['s'][y])) for y in yrs]
                      + [C.usd(-fl(x['drop'])), C.usd(fl(x['net'])), route_text(x['routes']),
                         '; '.join(x['was']) + ((' → ' + '; '.join(x['now'])) if x['now'] else '')])
                 for x in st]
    gcols = [C.fy(y) for y in yrs] + [chg, 'What was bought']
    new_rows = [dict(label='%s · %s' % (x['payee'], label[x['cat']]),
                     cells=[C.usd(fl(x['s'][y])) for y in yrs] + ['+' + C.usd(fl(x['rise'])), '; '.join(x['now'])])
                for x in d['grew'][:NEW_ROWS]]
    table = dict(caption='Vendors paid every year until %s, and the reverse' % fy1, views=[
        dict(key='stopped', label='Paid in %s and %s, far less in %s' % (C.fy(2024), fy0, fy1),
             total_col=None, kinds=kinds, columns=cols, rows=stop_rows,
             note='School general fund, invoices and orders open at the close, by vendor. What was '
                  'bought: the largest invoices, %s then %s, cut short by the ledger. Entries with no '
                  'payee count for every vendor on that account. Still short: the fall less every other '
                  'route found.' % (fy0, fy1)),
        dict(key='grew', label='Up the most in %s' % fy1, total_col=None, kinds=['ledger'] * len(gcols),
             columns=gcols,
             rows=new_rows,
             note='The %s vendors whose %s payments rose most on %s.' % (C.num(NEW_ROWS), fy1, fy0))])
    facts += [
        f('nstop', N(len(st), 'vendors'), 'recurring vendors paid far less in %s' % fy1, 'published',
          label_figures={'y': F(Y1)}),
        f('dropall', U(drop_all), 'less paid to them than in %s' % fy0, 'published',
          label_figures={'y': F(Y0)}),
        f('dropnet', U(drop_net), 'of it after every other route found', 'published'),
        f('nnet', N(len(unexplained), 'vendors'), 'vendors still short after other routes', 'published'),
    ]
    conclusions.append(con(
        '%s vendors paid in %s and %s got %s less in %s, %s after every other route.'
        % (C.num(len(st)), C.fy(2024), fy0, C.usd(fl(drop_all)), fy1, C.usd(fl(drop_net))),
        ['nstop', 'dropall', 'dropnet', 'nnet'],
        {'n': N(len(st), 'vendors'), 'a': F(2024), 'b': F(Y0), 'c': F(Y1), 'd': U(drop_all), 'e': U(drop_net)},
        so='The purchases the budget assumed would recur; why each did not is not in the ledger.'))

    sources = [
        dict(key='journal', label='Lunenburg Budget Project — munis-school-journal.csv (every school '
                                  'journal line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(key='accounts', label='Lunenburg Budget Project — munis-school-journal-accounts.csv '
                                   '(every school account)', href=J.PUBLIC['accounts']),
        dict(key='provenance', label='Town of Lunenburg — how the journal reached us, and what was redacted',
             href='/docs/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md'),
    ]
    cite = TP.cite
    flow = [
        'finding',
        cite(('chart', 0), 'journal', 'accounts'),
        ('conclusion', 0), ('conclusion', 1),
        cite(('table', 1), 'journal', 'accounts'),
        cite(timeline, 'journal', 'accounts', 'provenance'),
        ('conclusion', 2),
        cite(('table', 0), 'journal', 'accounts', 'provenance'),
        ('conclusion', 3),
        'related',
        'sources',
    ]
    return TP.page(
        ID,
        '%s categories left %s in %s; %s of recurring vendor payments did not recur.'
        % (many.capitalize(), C.usd(fl(left5)), fy1, C.usd(fl(drop_net))),
        facts, conclusions, chart=chart, table=table, tables=[years_table], sources=sources, flow=flow,
        finding_figures={'a': U(left5), 'y': F(Y1), 'd': U(drop_net)})


def render(d=None):
    p = page(d or data())
    p['not_established'] = [
        'Why any payment stopped: a contract ended, the work moved, the need fell away, or a bill '
        'was not yet sent all post the same way.',
        'Whether a salary account with no payroll was a vacancy, a leave, or pay charged elsewhere.',
        'Whether the FY2026 budget was built by carrying FY2025’s forward; the ledger shows the two '
        'figures, not how one was set.',
    ]
    return json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--show', action='store_true', help='print the measured rows')
    a = ap.parse_args()
    d = data()
    if a.show:
        for s in d['silent']:
            print('SILENT', s['account'], s['desc'], [MONTH_NAME[m] for m in s['gone']],
                  'lost', s['lost'], 'budget26', s['budget'], 'paid', s['paid'], 'moved', s['moved'])
        for x in d['stopped']:
            print('STOP %10.0f %-22s %s %s' % (x['drop'], x['payee'], x['routes'], x['was']))
    text = render(d)
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('why it was left: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
