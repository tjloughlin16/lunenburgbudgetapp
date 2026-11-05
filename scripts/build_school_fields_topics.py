#!/usr/bin/env python3
"""SCHOOL BUILDINGS AND FIELDS: the rent groups pay the schools, where it goes and what it pays
for. Four topic pages on the whole-school-budget shelf.

    python3 scripts/build_school_fields_topics.py           # write the topic payloads
    python3 scripts/build_school_fields_topics.py --check   # fail if any would change

TJ, 5 November 2026: "clearly this money goes to the schools, not to parks ... this should likely
go under the school [committee] finance page and reports pages" and "showing how the money is put
into accounts, spent, etc like we have for other fund pages is critical." These pages sat on the
Parks shelf and said who paid, how much and when was unknown, with the school journal already
held. They now read it.

WHERE EACH FIGURE COMES FROM. Rule 13a keeps these apart:

  munis-school-journal.csv      the accounting system's own lines, fund 1306: EVIDENCE.
  school-fund-flows.csv         the same journal summed by build_fund_flows.py, tied to the town's
                                reports. Every total here must equal it, or nothing is written.
  field-rental-receipts-lysa.csv
                                a workbook the business office typed: STATED. Its amounts all
                                appear in the journal; its dates do not, and the page says so.
  school-field-maintenance.csv  the Superintendent's email: STATED.

A JOURNAL DESCRIPTION IS CUT OFF AT ABOUT THIRTY CHARACTERS, so `LUNENBURG YOUTH` may be soccer,
basketball or something else. A receipt counts as the league's only if the district's own list
holds its amount; one that merely could be is shown as that (rule 7). A name that is not printed
is not inferred, and the rough class it falls in says so.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import build_parks_topics as PK  # noqa: E402  (read-only: read_series, balances, sources)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
FUND = '1306'
YEARS = [2023, 2024, 2025, 2026]
PAYER = 'Lunenburg Youth Soccer Association'
ME = 'build_school_fields_topics.py'
MINE = [t for t, (_, _h, gen) in REG.TOPICS.items() if gen == ME]

# A group the description prints. Anything else is "no group named": never inferred.
NAMED = re.compile(r'LUNENBURG JUNIO|JR BA|BENGA|INDOOR SOCCER|DANCE|SUMMER LEAG|CUB S|MUSIC|'
                   r'THE CLUB|LACROSSE|TWIN CITY|HICKORY|CLASS OF|XC & TRA|LUNENBURG J|ASLYFC')
# Every group fund 1306's journal names, as it prints them. TJ, 5 November 2026: "all those groups
# for the schools need to be shown on the youth sports page". A label never says more than the
# description does, or than we have been told: "Lunenburg J" stays cut off.
SPORTS_GROUPS = [('“Lunenburg Junio…” or “Jr Ba…”, name cut off', r'LUNENBURG JUNIO|JR BA'),
                 ('“Lunenburg J…”, name cut off', r'LUNENBURG J$'),
                 ('Twin City Thunder', r'TWIN CITY'),
                 # ASLYFC is Ayer-Shirley-Lunenburg Youth Football & Cheerleading, the Bengals (TJ, 5
                 # November 2026), so the journal's two spellings are one group.
                 ('Ayer-Shirley-Lunenburg Bengals (ASLYFC)', r'BENGA|ASLYFC'),
                 ('Indoor soccer', r'INDOOR SOCCER'),
                 ('Summer league', r'SUMMER LEAG'),
                 ('Lacrosse', r'LACROSSE'),
                 ('Lunenburg XC & track', r'XC & TRA')]
OTHER_GROUPS = [('Dance schools', r'DANCE'), ('Hickory Hills', r'HICKORY'),
                ('Lunenburg Music', r'MUSIC'), ('The Club', r'THE CLUB'),
                ('Class of 2028', r'CLASS OF'), ('Lunenburg Cub Scouts', r'CUB S')]
MAYBE = re.compile(r'LUNENBURG YOUT|LUNENBURG SOCCER')
GROUNDS = re.compile(r'LANDSCAP|CUTTING|REPAIR, SEED|IRRIGATION|SPREADER|PAINT', re.I)
PAYEE_CLASSES = ['Field and grounds work', 'Concession stand supplies', 'Payroll', 'Other bills',
                 'Year-end entries moving cost']
PAYER_CLASSES = ['On the district’s list for this league', 'Could be the same league',
                 'Other named groups', 'No group named']


def fail(msg):
    raise SystemExit('build_school_fields_topics: ' + msg)


def usd2(x):
    return PK.usd2(x)


def rows(name):
    return list(csv.DictReader(open(os.path.join(D, name), encoding='utf-8')))


def read():
    J = [r for r in rows('munis-school-journal.csv')
         if r['fund'] == FUND and r['posts_to'] == 'actual']
    flows = {int(r['fiscal_year']): r for r in rows('school-fund-flows.csv') if r['fund'] == FUND}
    if sorted(flows) != YEARS:
        fail('school-fund-flows.csv no longer holds FY2023-FY2026 for %s' % FUND)
    listed = rows('field-rental-receipts-lysa.csv')
    want = {round(float(r['amount']), 2): r for r in listed}
    if len(want) != len(listed):
        fail('two listed receipts share an amount; matching on amount no longer identifies one')

    receipts, refunds, payments, used = [], [], [], set()
    for r in J:
        a = float(r['amount'])
        if r['object'].startswith('4'):
            if a > 0:
                refunds.append(r)
                continue
            d, amt = r['description'], round(-a, 2)
            if amt in want:
                cls = PAYER_CLASSES[0]
                used.add(amt)
            elif MAYBE.search(d):
                cls = PAYER_CLASSES[1]
            elif NAMED.search(d):
                cls = PAYER_CLASSES[2]
            else:
                cls = PAYER_CLASSES[3]
            receipts.append(dict(fy=int(r['fiscal_year']), date=r['effective_date'], amount=amt,
                                 desc=d, ref=r['doc_no'], cls=cls))
        elif r['object'].startswith('5') and abs(a) > 0.004:
            d = r['description']
            if r['source'] == 'GEN':
                cls = PAYEE_CLASSES[4]
            elif r['source'] == 'PRJ':
                cls = PAYEE_CLASSES[2]
            elif 'CONCESSION' in d.upper():
                cls = PAYEE_CLASSES[1]
            elif GROUNDS.search(d):
                cls = PAYEE_CLASSES[0]
            else:
                cls = PAYEE_CLASSES[3]
            payments.append(dict(fy=int(r['fiscal_year']), date=r['effective_date'], amount=round(a, 2),
                                 payee=r['vendor'] if r['source'] == 'API' else '', desc=d,
                                 cls=cls, source=r['source'], journal=r['journal']))
    if used != set(want):
        fail('listed receipts not found in fund %s: %s' % (FUND, sorted(set(want) - used)))

    # Rule 13: reconcile to the figures the fund's own flows print, or write nothing.
    for y in YEARS:
        got = sum(x['amount'] for x in receipts if x['fy'] == y) \
            - sum(float(r['amount']) for r in refunds if int(r['fiscal_year']) == y)
        if abs(got - float(flows[y]['received_outside'])) > 0.005:
            fail('FY%d receipts %.2f do not tie to school-fund-flows %s'
                 % (y, got, flows[y]['received_outside']))
        out = sum(x['amount'] for x in payments if x['fy'] == y)
        if abs(out - float(flows[y]['spent_actual'])) > 0.005:
            fail('FY%d payments %.2f do not tie to school-fund-flows %s'
                 % (y, out, flows[y]['spent_actual']))
        if float(flows[y]['transfers_in']) or float(flows[y]['transfers_out']):
            fail('FY%d now records a transfer; the page says none is recorded' % y)
    return dict(flows=flows, receipts=receipts, refunds=refunds, payments=payments,
                listed=listed, want=want)


def fy_of_date(iso):
    y, m = int(iso[:4]), int(iso[5:7])
    return y + 1 if m >= 7 else y


def day(iso):
    return PK.day(iso)


def build():
    Y = json.load(open(os.path.join(PUB, 'youth-sports.json'), encoding='utf-8'))
    src = {k: dict(v, key=k) for k, v in PK.sources().items()}
    for k, f_, what in (('journal', 'munis-school-journal.csv', 'the school MUNIS journal, one row a posting'),
                        ('flows', 'school-fund-flows.csv', 'each school fund’s money in and out, tied')):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f_)):
            fail('/docs/data/%s is not published' % f_)
        src[k] = dict(key=k, label='Lunenburg Budget Project — %s (%s)' % (f_, what), href='/docs/data/' + f_)
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con, cite = LD.fact, TP.conclusion, TP.cite
    funds = {x['fund']: x for x in Y['funds']}
    out = {}
    d = read()
    fl, rec, pay = d['flows'], d['receipts'], d['payments']
    n = lambda y, k: float(fl[y][k])
    fys = [C.fy(y) for y in YEARS]

    def by(items, classes):
        t = {c: {y: 0.0 for y in YEARS} for c in classes}
        for x in items:
            t[x['cls']][x['fy']] += x['amount']
        return {c: {y: round(v, 2) for y, v in t[c].items()} for c in classes}

    payers, payees = by(rec, PAYER_CLASSES), by(pay, PAYEE_CLASSES)
    listed_cls, maybe_cls, named_cls, none_cls = PAYER_CLASSES
    grounds = payees[PAYEE_CLASSES[0]]
    entries = [x for x in pay if x['source'] == 'GEN']
    entry25 = next((x for x in entries if x['fy'] == 2025 and x['amount'] < 0), None)
    if not entry25 or not entry25['journal'] == '2025/12/001348':
        fail('the FY2025 memo entry is no longer where it was')
    unnamed = round(sum(payers[none_cls].values()), 2)
    all_in = round(sum(x['amount'] for x in rec), 2)
    open_year = fl[2026]['year_open'] not in ('', '0', 'False', 'false', 'no')
    closed25 = n(2025, 'closing_balance')
    rise25 = n(2025, 'net')

    # ================================================================ School facilities fund
    sser = PK.read_series('School Facilities Use')
    sbal = PK.balances(FUND)
    s26 = funds[1306]
    if abs(sbal[2025] - closed25) > 0.005:
        fail('the journal’s FY2025 close no longer equals the annual report’s balance')
    league25 = payers[listed_cls][2025]
    srow = []
    for y in range(2023, 2010, -1):
        r = sser[y]
        srow.append(dict(label=C.fy(y), cells=[PK.cell(r['receipts']), PK.cell(r['disbursed']), PK.cell(r['carried'])]))
    flow_rows = [dict(label=C.fy(y) + (' to date' if y == 2026 and open_year else ''),
                      cells=[usd2(n(y, 'opening_balance')), usd2(n(y, 'received_outside')),
                             usd2(n(y, 'spent_actual')), usd2(n(y, 'closing_balance'))]) for y in YEARS]
    sum_row = lambda cl, t: [dict(label=c, cells=[usd2(t[c][y]) if t[c][y] else None for y in YEARS]
                                  + [usd2(sum(t[c].values()))]) for c in cl]
    refund_row = dict(label='Less refunds and double payments returned',
                      cells=[usd2(-sum(float(r['amount']) for r in d['refunds'] if int(r['fiscal_year']) == y))
                             if any(int(r['fiscal_year']) == y for r in d['refunds']) else None for y in YEARS]
                      + [usd2(-sum(float(r['amount']) for r in d['refunds']))])
    table = dict(caption='Fund %s, money in and money out' % FUND, views=[
        dict(key='flow', label='Each year', total_col=3, kinds=['ledger'] * 4,
             columns=['Opening balance', 'Money in', 'Money out', 'Closing balance'], rows=flow_rows,
             note='The school journal, posted actuals. Ties to the fund’s reports each closed year. '
                  'No transfer in or out is recorded in any year.'),
        dict(key='in', label='Money in, by payer', total_col=4, kinds=['ledger'] * 5,
             columns=fys + ['All years'], rows=sum_row(PAYER_CLASSES, payers) + [refund_row],
             note='By what the journal description prints, which is cut off at about thirty characters. '
                  'A payer is counted as the league only if the district’s own list holds the amount.'),
        dict(key='out', label='Money out, by purpose', total_col=4, kinds=['ledger'] * 5,
             columns=fys + ['All years'], rows=sum_row(PAYEE_CLASSES, payees),
             note='Purpose is our grouping of the journal descriptions. Every bill is listed in the Payments views.'),
        *[dict(key='receipts%d' % y, label='Receipts, %s' % C.fy(y), total_col=0, kinds=['ledger'] * 2,
               columns=['Amount', 'Description as printed'],
               rows=[dict(label=x['date'], cells=[usd2(x['amount']), x['desc']]) for x in rec if x['fy'] == y],
               note='Private individuals’ names are masked in the published journal.') for y in YEARS],
        *[dict(key='payments%d' % y, label='Payments, %s' % C.fy(y), total_col=0, kinds=['ledger'] * 3,
               columns=['Amount', 'Paid to', 'Description as printed'],
               rows=[dict(label=x['date'], cells=[usd2(x['amount']), x['payee'] or 'payroll or entry', x['desc']])
                     for x in pay if x['fy'] == y],
               note='Invoices, pay runs and journal entries, as posted.') for y in YEARS],
        dict(key='history', label='Older years', total_col=2, kinds=['ledger'] * 3,
             columns=['Taken in', 'Spent', 'Balance'], rows=srow,
             note='Annual town reports. FY2011–FY2023 each row ties forward + receipts − disbursements = '
                  'carried; FY2018 closed in deficit.'),
    ])
    money_chart = TP.series(
        'Money in, money out, balance', fys,
        [TP.track('Money in', [n(y, 'received_outside') for y in YEARS], 'published', 'bar'),
         TP.track('Money out', [n(y, 'spent_actual') for y in YEARS], 'published', 'bar'),
         TP.track('Balance at year end', [n(y, 'closing_balance') for y in YEARS], 'published', 'line')],
        '$', note='Fund %s, the school journal. %s is the year to date.' % (FUND, C.fy(2026)),
        note_allow=(FUND, C.fy(2026)))
    payer_chart = TP.series(
        'Who paid into the fund', fys,
        [TP.track(c, [payers[c][y] for y in YEARS], 'published', 'bar') for c in PAYER_CLASSES],
        '$', kind='bar', stacked=True,
        note='Before refunds. The name is what the journal prints; “no group named” is not inferred.')
    spend_chart = TP.series(
        'Where the fund’s money went', fys,
        [TP.track(c, [payees[c][y] for y in YEARS], 'published', 'bar') for c in PAYEE_CLASSES[:4]],
        '$', kind='bar', stacked=True,
        note='Before year-end entries, which move cost between funds; they are in the table. '
             'Purpose is our grouping of the journal’s descriptions.')
    out['school-facilities-fund'] = TP.page(
        'school-facilities-fund',
        'Fund %s took in %s in %s and paid out %s, which is why its balance jumped.'
        % (FUND, C.usd(n(2025, 'received_outside')), C.fy(2025), C.usd(n(2025, 'spent_actual'))),
        [f('in25', U(n(2025, 'received_outside')), 'money in, FY2025', 'published', allow=('FY2025',)),
         f('out25', U(n(2025, 'spent_actual')), 'money out, FY2025', 'published', allow=('FY2025',)),
         f('rise', U(rise25), 'the rise in the balance, FY2025', 'published', allow=('FY2025',)),
         f('held25', U(closed25), 'held at 30 June 2025', 'published', allow=('30', '2025')),
         f('out23', U(n(2023, 'spent_actual')), 'money out, FY2023', 'published', allow=('FY2023',)),
         f('g23', U(grounds[2023]), 'field and grounds work, FY2023', 'published', allow=('FY2023',)),
         f('g25', U(grounds[2025]), 'field and grounds work billed, FY2025', 'published', allow=('FY2025',)),
         f('moved', U(-entry25['amount']), 'moved to the general fund by a year-end entry, FY2025',
           'published', allow=('FY2025',)),
         f('l25', U(league25), 'the listed league receipts, FY2025', 'published', allow=('FY2025',)),
         f('none', U(unnamed), 'receipts that name no group, FY2023–FY2026', 'published',
           allow=('FY2023', 'FY2026')),
         f('who', None, 'who paid the receipts that name no group', 'gap',
           closes='the MUNIS cash receipt detail for fund 1306, by payer')],
        [con('%s came in and %s went out in FY2025, so the fund rose %s.'
             % (C.usd(n(2025, 'received_outside')), C.usd(n(2025, 'spent_actual')), C.usd(rise25)),
             ['in25', 'out25', 'rise', 'held25'],
             {'a': U(n(2025, 'received_outside')), 'b': U(n(2025, 'spent_actual')), 'c': U(rise25)},
             allow=('FY2025',),
             so='The rise is receipts outrunning bills. The journal records no transfer into the fund.'),
         con('Field and grounds bills fell from %s in FY2023 to %s in FY2025.'
             % (C.usd(grounds[2023]), C.usd(grounds[2025])), ['out23', 'g23', 'g25', 'moved'],
             {'a': U(grounds[2023]), 'b': U(grounds[2025])}, allow=('FY2023', 'FY2025'),
             notes=[step('Less work, or the same work charged somewhere else, both fit; this fund’s '
                         'journal cannot tell them apart.', 'hypothesis')],
             so='Rent kept coming in while far less of the field work was charged against it.'),
         con('The listed youth soccer receipts were %s of the money in during FY2025.' % C.usd(league25),
             ['l25', 'in25'], {'a': U(league25)}, allow=('FY2025',),
             so='One renter can move this fund’s year on its own.'),
         con('%s of receipts over the four years name no group.' % C.usd(unnamed), ['none', 'who'],
             {'a': U(unnamed)},
             so='Who rents school fields, and for how much, cannot be fully read from this journal.')],
        table=table, chart=money_chart, also=[spend_chart, payer_chart],
        sources=[src['journal'], src['flows'], src['sr26'], src['ar11'], src['ar23'], src['ar25'],
                 src['d-read'], src['d-funds']],
        finding_figures={'a': U(n(2025, 'received_outside')), 'b': U(n(2025, 'spent_actual'))},
        finding_allow=(FUND, 'FY2025'),
        flow=['finding', cite(('chart', 0), 'journal', 'flows'), cite('ladder', 'journal', 'flows', 'ar25'),
              cite(('chart', 1), 'journal'), cite(('chart', 2), 'journal'), 'related', cite('ledger', 'journal', 'flows', 'sr26'),
              cite(('table', 0), 'journal', 'flows', 'ar11', 'ar23', 'd-read', 'd-funds'), 'sources'])

    # ================================================================ School field upkeep
    mt = {r['item']: r for r in Y['maintenance']}
    for r in Y['maintenance']:
        if r['basis'] != 'stated':
            fail('a field-maintenance figure is no longer marked stated')
    autumn = float(mt['Landscaper, mowing the athletic grass fields, autumn']['amount'])
    spring = float(mt['Landscaper, mowing the athletic grass fields, spring']['amount'])
    repair = float(mt['Landscaper, summer field repair']['amount'])
    allg = float(mt['All fields and grounds maintenance']['amount'])
    veh = float(mt['Of that: vehicle and equipment maintenance and repair']['amount'])
    g24 = [x for x in pay if x['fy'] == 2024 and x['cls'] == PAYEE_CLASSES[0]]
    if len(g24) != 1 or abs(g24[0]['amount'] - repair) > 0.005:
        fail('fund 1306’s FY2024 grounds bills are no longer one bill equal to the stated repair')
    gf24 = [r for r in rows('munis-school-journal.csv')
            if r['fund'] == '0100' and r['fiscal_year'] == '2024' and r['posts_to'] == 'actual'
            and r['org_name'] == 'MAINTENANCE OF GROUNDS' and r['vendor'].startswith('JACOBS')]
    gf24_total = round(sum(float(r['amount']) for r in gf24), 2)
    if not gf24:
        fail('the FY2024 general-fund landscaping bill is no longer in the journal')
    if not n(2024, 'spent_actual') < allg:
        fail('the fund’s FY2024 spending no longer falls short of the stated grounds total')
    cut23 = round(sum(x['amount'] for x in pay if x['fy'] == 2023 and 'CUTTING' in x['desc'].upper()), 2)
    out['school-field-upkeep'] = TP.page(
        'school-field-upkeep',
        'The district says rent pays for mowing; fund %s shows one %s grounds bill, %s.'
        % (FUND, C.fy(2024), C.usd(repair)),
        [f('mow', U(autumn + spring), 'mowing, autumn and spring, FY2024 (stated)', 'published', allow=('FY2024',)),
         f('repair', U(repair), 'summer field repair, 2023 (stated)', 'published', allow=('2023',)),
         f('bill', U(g24[0]['amount']), 'the one grounds bill in the fund’s journal, FY2024', 'published',
           allow=('FY2024',)),
         f('gf', U(gf24_total), 'same landscaper, general fund grounds line, FY2024', 'published', allow=('FY2024',)),
         f('cut', U(cut23), 'field cutting bills in the fund’s journal, FY2023', 'published', allow=('FY2023',)),
         f('all', U(allg), 'all fields and grounds work, FY2024, approximate (stated)', 'published', allow=('FY2024',)),
         f('veh', U(veh), 'of that, vehicles and equipment, which also plough', 'published')],
        [con('The district puts FY2024 mowing at %s, from fund %s; that fund’s journal has no mowing bill.'
             % (C.usd(autumn + spring), FUND), ['mow', 'bill', 'gf'],
             {'a': U(autumn + spring)}, allow=('FY2024', FUND),
             notes=[step('The email’s year may differ from the ledger’s: this fund shows cutting bills a '
                         'year before. Or the general fund paid: the same landscaper’s %s bill there '
                         'is near the %s stated for autumn. Nothing links them.'
                         % (C.usd(gf24_total), C.usd(autumn)), 'hypothesis',
                         {'a': U(gf24_total), 'b': U(autumn)})],
             so='The stated source of the mowing money and the ledger do not line up for that year.'),
         con('The fund’s one FY2024 grounds bill, %s, equals the district’s summer repair figure.' % C.usd(repair),
             ['repair', 'bill'], {'a': U(repair)}, allow=('FY2024',),
             so='That figure matches the books; the mowing figure does not appear in this fund for that year.'),
         con('It puts all fields and grounds work at about %s for FY2024, vehicles included.' % C.usd(allg),
             ['all', 'veh'], {'a': U(allg)}, allow=('FY2024',),
             so='The fund paid out far less than that in all of FY2024, so most of it came from elsewhere.', so_allow=('FY2024',))],
        chart=TP.series('Stated cost against the books', ['Mowing', 'Summer repair'],
                        [TP.track('The district’s email', [autumn + spring, repair], 'stated', 'bar'),
                         TP.track('Fund bills in the journal', [0, g24[0]['amount']], 'published', 'bar')],
                        '$', kind='bar',
                        note='The Superintendent’s approximate figures, by email, against fund %s’s journal, %s.'
                             % (FUND, C.fy(2024)), note_allow=(FUND, C.fy(2024))),
        sources=[src['email'], src['d-maint'], src['journal']],
        finding_figures={'a': U(repair)}, finding_allow=(FUND, 'FY2024'))

    # ================================================================ Youth league payments
    listed = sorted(d['listed'], key=lambda r: r['receipt_date'])
    jmatch = {x['amount']: x for x in rec if x['cls'] == listed_cls}
    rows_l, gaps, moved_year = [], [], []
    import datetime as DT
    for r in listed:
        a = round(float(r['amount']), 2)
        j = jmatch[a]
        g = (DT.date.fromisoformat(r['receipt_date']) - DT.date.fromisoformat(j['date'])).days
        gaps.append(g)
        if r['fiscal_year_as_listed'] != C.fy(j['fy']):
            moved_year.append((a, r['fiscal_year_as_listed'], C.fy(j['fy'])))
        rows_l.append(dict(label=usd2(a), cells=[r['receipt_date'], r['fiscal_year_as_listed'], j['date'], C.fy(j['fy']), j['ref']]))
    if min(gaps) <= 0:
        fail('a workbook date is no longer later than the journal’s')
    if len(moved_year) != 1:
        fail('the receipts whose fiscal year differs are no longer exactly one: %s' % moved_year)
    rtot = round(sum(float(r['amount']) for r in listed), 2)
    maybe = [x for x in rec if x['cls'] == maybe_cls]
    maybe_tot = round(sum(x['amount'] for x in maybe), 2)
    maybe_rows = [dict(label=x['date'], cells=[C.fy(x['fy']), usd2(x['amount']), x['desc']]) for x in maybe]
    named = sorted((x for x in rec if x['cls'] == named_cls), key=lambda x: x['date'])
    if len(named) > TP.TABLE_ROWS_MAX:
        fail('the named receipts no longer fit one table view')
    named_rows = [dict(label=x['date'], cells=[C.fy(x['fy']), usd2(x['amount']), x['desc']]) for x in named]
    grp = {g: {y: 0.0 for y in YEARS} for g, _ in SPORTS_GROUPS + OTHER_GROUPS}
    for x in named:
        hits = [g for g, rx in SPORTS_GROUPS + OTHER_GROUPS if re.search(rx, x['desc'])]
        if len(hits) != 1:
            fail('receipt %r matches %d groups: %s' % (x['desc'], len(hits), hits))
        grp[hits[0]][x['fy']] += x['amount']
    if abs(sum(sum(v.values()) for v in grp.values()) - sum(x['amount'] for x in named)) > 0.005:
        fail('the groups no longer add to the named receipts')
    gsum = lambda names: round(sum(sum(grp[g].values()) for g in names), 2)
    sports_names = [g for g, _ in SPORTS_GROUPS]
    sports_tot = gsum(sports_names)
    other_tot = gsum([g for g, _ in OTHER_GROUPS])
    bengals = gsum(['Ayer-Shirley-Lunenburg Bengals (ASLYFC)'])
    if rtot <= max(gsum([g]) for g in grp):
        fail('the soccer league is no longer the most any named group paid')
    gcells = lambda t: [usd2(t[y]) if t[y] else None for y in YEARS] + [usd2(sum(t.values()))]
    glead = [dict(label=PAYER, cells=gcells(payers[listed_cls])),
             dict(label='Could be the soccer league, or another group', cells=gcells(payers[maybe_cls]))]
    grow = lambda names: [dict(label=g, cells=gcells(grp[g]))
                          for g in sorted(names, key=lambda g: -sum(grp[g].values()))]
    plan_bengals = float(re.search(r'\$([\d,]+) from the Bengals', Y['said'][0]['what']).group(1).replace(',', ''))
    # What the boards said, carried from the /youth-sports report this page replaced. Machine
    # captions are a finding aid: the words are ours to check against the video at that second.
    said_rows = []
    for s in sorted(Y['said'], key=lambda s: s['date']):
        t = s['t']
        stamp = '%d:%02d:%02d' % (t // 3600, t % 3600 // 60, t % 60)
        board = s['board'].lower().replace(' ', '-')
        cell = 'youtu.be/%s?t=%d (%s)' % (s['video'], t, stamp)
        row = dict(label=s['date'], cells=[s['board'], s['what'], cell])
        if os.path.exists(os.path.join(D, 'recording-minutes', board, '%s-%s.json' % (s['date'], s['video']))):
            row['links'] = [None, None, [dict(t=cell, href='/meeting-minutes/%s/%s-%s' % (board, s['date'], s['video']))]]
        said_rows.append(row)
    out['youth-league-payments'] = TP.page(
        'youth-league-payments',
        'Lunenburg Youth Soccer paid %s into the schools’ fund %s, the most of any group named.'
        % (usd2(rtot), FUND),
        [f('rtot', U2(rtot), 'in the district’s list for this league (stated)', 'published'),
         f('rn', N(len(listed), 'receipts'), 'receipts on the list, every amount found in fund 1306', 'published', allow=('1306',)),
         f('gmin', N(min(gaps), 'days'), 'shortest gap between list date and journal date', 'published'),
         f('gmax', N(max(gaps), 'days'), 'longest gap between list date and journal date', 'published'),
         f('moved', U2(moved_year[0][0]), 'listed under %s, posted in %s' % (moved_year[0][1], moved_year[0][2]),
           'published', allow=(moved_year[0][1], moved_year[0][2])),
         f('mn', N(len(maybe), 'receipts'), 'more journal receipts that could be this league', 'published'),
         f('mtot', U2(maybe_tot), 'what those receipts add up to', 'published'),
         f('ntot', U2(sports_tot), 'paid by other sports groups named, FY2023–FY2026', 'published',
           allow=('FY2023', 'FY2026')),
         f('ng', N(len(sports_names), 'groups'), 'other sports groups the journal names', 'published'),
         f('ben', U2(bengals), 'the Bengals, printed as Bengals and as ASLYFC', 'published'),
         f('settle', None, 'whether those receipts are this league’s', 'gap',
           closes='the MUNIS cash receipt detail for fund 1306, by payer')],
        [con('The list’s %s receipts, %s in all, are in the journal in fund %s, the schools’ rental fund.'
             % (C.num(len(listed)), usd2(rtot), FUND), ['rtot', 'rn'],
             {'n': N(len(listed)), 'a': U2(rtot)}, allow=(FUND,),
             so='This is school money: none of the seven posted to a Parks account.'),
         con('Every list date is later than the journal’s, by %s to %s days.' % (C.num(min(gaps)), C.num(max(gaps))),
             ['gmin', 'gmax', 'moved'], {'a': N(min(gaps)), 'b': N(max(gaps))},
             notes=[step('The workbook does not say what its dates record; a typed sheet is not the '
                         'books, so the journal’s date is the one used on this site.', 'hypothesis')],
             so='The amounts agree and the dates do not, so one receipt lands in a different year.'),
         con('The journal has %s more receipts, %s, that could be the same league.'
             % (C.num(len(maybe)), usd2(maybe_tot)), ['mn', 'mtot', 'settle'],
             {'n': N(len(maybe)), 'a': U2(maybe_tot)},
             notes=[step('Their descriptions stop at “Lunenburg Youth” or say “Lunenburg Soccer”; another '
                         'youth group fits as well. Two are from before the list starts.', 'hypothesis')],
             so='The list may be short of what the league paid; this journal cannot settle it.'),
         con('%s other sports groups are named, paying %s over the four years.'
             % (C.num(len(sports_names)), usd2(sports_tot)), ['ntot', 'ng', 'ben'],
             {'n': N(len(sports_names)), 'a': U2(sports_tot)},
             notes=[step('The Bengals paid %s under two names. A 2016 plan had them paying %s a year '
                         'toward the turf fund, which this journal does not cover, so that part may be '
                         'elsewhere.' % (usd2(bengals), C.usd(plan_bengals)), 'hypothesis',
                         {'a': U2(bengals), 'c': U(plan_bengals)}, allow=('2016',))],
             so='Each group’s total here is a floor: receipts that name no group may hold more.')],
        table=dict(caption='Who paid the schools’ rental fund', views=[
            dict(key='sports', label='Sports groups', total_col=4, kinds=['ledger'] * 5,
                 columns=fys + ['All years'], rows=glead + grow(sports_names),
                 note='By the year the journal posts them. Names are what its descriptions print, cut off at '
                      'about thirty characters. An indoor soccer receipt was followed days later by a refund '
                      'of the same amount. ASLYFC, Ayer-Shirley-Lunenburg Youth Football & Cheerleading, is the Bengals. '
                      'Little League appears nowhere in this journal.'),
            dict(key='othergroups', label='Other groups', total_col=4, kinds=['ledger'] * 5,
                 columns=fys + ['All years'], rows=grow([g for g, _ in OTHER_GROUPS]),
                 note='Groups renting school buildings or fields that are not sports leagues.'),
            dict(key='receipts', label='The district’s list', total_col=0, kinds=['stated', 'stated', 'ledger', 'ledger', 'ledger'],
                 columns=['Date on the list', 'Year on the list', 'Date in the journal', 'Year in the journal', 'Journal reference'],
                 rows=rows_l, note='Typed into a workbook by the district’s business office; the journal is the accounting system’s.'),
            dict(key='maybe', label='Could be the same league', total_col=1, kinds=['ledger'] * 3,
                 columns=['Fiscal year', 'Amount', 'Description as printed'], rows=maybe_rows,
                 note='Not on the district’s list. Shown because of what the description prints, not because anything says they are this league’s.'),
            dict(key='others', label='Other named groups', total_col=1, kinds=['ledger'] * 3,
                 columns=['Fiscal year', 'Amount', 'Description as printed'], rows=named_rows,
                 note='Fund 1306, as the journal prints them. A receipt that names no group is on the fund’s own page.'),
            dict(key='said', label='What boards said', total_col=None, kinds=['stated'] * 3,
                 columns=['Board', 'What was said', 'Where'], rows=said_rows,
                 note='From machine captions of the recordings: a way to find the moment, not a record. Check the video.')]),
        chart=TP.ranking('Sports groups named in the fund’s journal',
                         [('Lunenburg Youth Soccer', rtot), ('Could be the soccer league', maybe_tot)]
                         + [(g, gsum([g])) for g in sports_names], '$', highlight=('Lunenburg Youth Soccer',),
                         note='Fund %s, over the four years the journal covers. Receipts that name no group are '
                              'not here.' % FUND, note_allow=(FUND,)),
        sources=[src['journal'], src['receipts'], src['d-receipts']],
        finding_figures={'a': U2(rtot)}, finding_allow=(FUND,))

    # ================================================================ Artificial turf fund
    t26 = funds[1545]
    tbal = PK.balances('1545')
    if abs(tbal[2025] - t26['opening']) > 0.005:
        fail('fund 1545: the FY2025 annual-report balance no longer equals the FY26 opening')
    plan = Y['said'][0]
    if plan['date'] != '2016-05-03':
        fail('the 2016 turf plan is no longer the first record in youth-sports.json')
    amts = [float(x.replace(',', '')) for x in re.findall(r'\$([\d,]+)', plan['what'])]
    if len(amts) < 2 or abs(amts[0] + amts[1] - t26['revenue']) > 0.005:
        fail('the 2016 plan’s first two sums no longer add to the turf fund’s FY2026 revenue')
    f26 = json.load(open(os.path.join(PUB, 'parks.json'), encoding='utf-8'))['fund']['current']
    out['artificial-turf-fund'] = TP.page(
        'artificial-turf-fund',
        'The Artificial Turf fund took in %s in FY2026 and held %s at 31 March 2026.'
        % (C.usd(t26['revenue']), C.usd(t26['available'])),
        [f('in', U(t26['revenue']), 'into fund 1545, July–March FY2026', 'published', allow=('1545', 'FY2026')),
         f('out', U(t26['expenditure']), 'spent from it, July–March FY2026', 'published', allow=('FY2026',)),
         f('held', U(t26['available']), 'held, 31 March 2026', 'published', allow=('31', '2026')),
         f('b24', U(tbal[2024]), 'balance at 30 June 2024, annual report', 'published', allow=('30', '2024')),
         f('b25', U(tbal[2025]), 'balance at 30 June 2025, annual report', 'published', allow=('30', '2025')),
         f('split', None, 'who paid the FY2026 receipts', 'gap', allow=('FY2026',),
           closes='the receipt detail for fund 1545, which is not in the school journal')],
        [con('The fund took in %s and spent %s from July to March FY2026.'
             % (C.usd(t26['revenue']), C.usd(t26['expenditure'])), ['in', 'out', 'held'],
             {'a': U(t26['revenue']), 'b': U(t26['expenditure'])}, allow=('FY2026',),
             notes=[step('Machine captions of the Select Board on 3 May 2016 describe %s a year '
                         'from a cell tower and %s from a youth league; the two add to this '
                         'year’s receipts. No ledger splits them.'
                         % (C.usd(amts[0]), C.usd(amts[1])), 'hypothesis',
                         {'a': U(amts[0]), 'b': U(amts[1])}, allow=('3', '2016'))]),
         con('Its balance rose from %s at 30 June 2024 to %s at 31 March 2026.'
             % (C.usd(tbal[2024]), C.usd(t26['available'])), ['b24', 'b25', 'held', 'split'],
             {'a': U(tbal[2024]), 'b': U(t26['available'])}, allow=('30', '2024', '31', '2026'))],
        chart=TP.series('Artificial Turf fund balance',
                        [day('2024-06-30'), day('2025-06-30'), day(f26['as_of'])],
                        [TP.track('Balance', [tbal[2024], tbal[2025], t26['available']], 'published', 'bar')],
                        '$', kind='bar', note='Fund %s: the annual town reports, then the MUNIS fund report.' % '1545',
                        note_allow=('1545',)),
        sources=[src['sr26'], src['ar24'], src['ar25'], src['d-funds']],
        finding_figures={'a': U(t26['revenue']), 'b': U(t26['available'])},
        finding_allow=('FY2026', '31', '2026'))

    if sorted(out) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('school fields topics: %d outputs current' % len(outs))
        return 0
    for p, t in outs.items():
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(t)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
