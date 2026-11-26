#!/usr/bin/env python3
"""THE FY2026 SCHOOL SURPLUS: one topic page, at the address Surplus by category had.

    python3.11 scripts/build_fy2026_school_surplus.py           # write fy28/public/data/topics/fy2026-surplus-by-category.json
    python3.11 scripts/build_fy2026_school_surplus.py --check   # fail if it would change

    fy2026-surplus-by-category   /fy2026-closeout/fy2026-surplus-by-category   FY2026 school surplus

TJ, 24 November 2026, after reading the draft this page was built from
(build/fy26-closeout/FY26-CLOSEOUT-EXPLAINED.md, decision on the closeout report ticket): the
report REPLACES Surplus by category rather than sitting beside it, and it absorbs Circuit breaker
and surplus, whose address now opens this page (fy28/src/routes.ts TOPIC_MERGED).

WHAT IT RESTS ON, all printed in a document:
  - the school general fund's period-13 reports, FY2023-FY2026 (munis-school-ytd.csv, via
    build_fy2026_closeout_topics.school), for the surplus, its two halves and the categories
    (build_school_surplus.py's payload, tied to the ledger before use);
  - the school journal, for the 29 June 2026 entry (journal 2026/12/000692), the 30 June
    prepayment and what the circuit breaker fund paid, by date (build_circuit_breaker_surplus.data,
    which ties the fund to the Town's special-revenue report);
  - the reclassification form, the Town's journal proof and the printed 31 August-1 September
    email thread the Town Manager handed over on 24 November 2026 (sources/correspondence/), every
    quotation asserted verbatim against our transcription of its page;
  - the FY2025 annual town report's special revenue schedule (special-revenue-funds.csv).

WHAT IS OURS, and drawn as ours (rule 7): the categories; the circuit breaker money due to lapse
(the fund's 1 July balance less what it spent before June -- one fund holds every year's money);
the surplus with each entry removed; and every possible explanation, which the page lays out
against the record without choosing one, because no document does.
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
import journal as J  # noqa: E402
import build_circuit_breaker_surplus as CB  # noqa: E402
import build_journal_surplus_topics as JS  # noqa: E402
import build_fy2026_closeout_topics as CT  # noqa: E402

ID = 'fy2026-surplus-by-category'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
TXT = os.path.join(ROOT, 'sources', 'correspondence', 'text')
CORR = '/docs/correspondence/'
FORM = '2026-11-24-reclassification-collaborative-tuition-fy2026.jpg'
PROOF = '2026-11-24-journal-692-entry-proof.jpg'
INVOICES = '2026-11-23-town-vendor-invoice-list-check-218995.pdf'
ATR25 = 'town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf'
D0 = Decimal(0)


def fail(msg):
    raise SystemExit('build_fy2026_school_surplus: ' + msg)


def thread(n):
    return '2026-11-24-collaborative-tuition-reclass-thread-p%d.jpg' % n


def quote(name, text):
    """A quotation, asserted verbatim (whitespace folded) against our transcription."""
    body = ' '.join(open(os.path.join(TXT, name + '.txt'), encoding='utf-8').read().split())
    if ' '.join(text.split()) not in body:
        fail('quotation not in %s: %r' % (name, text[:60]))
    return text


def fl(x):
    return float(x)


# --------------------------------------------------------------------------- the figures

def data():
    d = CB.data()
    y0, y1 = d['years'][2025], d['years'][2026]
    charged, left = d['charged'], y1['left']
    older = d['held_jul'] - y1['drawn_early']        # ours: the money due to lapse on 30 June
    if not (charged > older > 0):
        fail('the page says the reclass used all the fund’s older money')

    # The school ledger, period 13, recomputed and tied to the surplus payload (as the hub does).
    S = CT.load('fy26-school-surplus.json')
    A = S['audit']
    L = {fy: CT.school(fy) for fy in (2023, 2024, 2025, 2026)}
    s26 = CT.tot(L[2026], CT.SK)
    if not CT.near(s26['available_budget'], fl(left)) or not CT.near(s26['available_budget'],
                                                                    S['totals']['available']):
        fail('the period-13 report, the journal and the surplus payload disagree on what was left')
    over, under = {}, {}
    for fy in L:
        o = [r for r in L[fy] if r['available_budget'] < -0.004]
        over[fy] = (len(o), round(-sum(r['available_budget'] for r in o), 2))
        under[fy] = round(sum(r['available_budget'] for r in L[fy] if r['available_budget'] > 0.004), 2)
    by_year = {y['fy']: y for y in A['overdrawn']['by_year']}
    for fy in L:
        if over[fy][0] != by_year[fy]['accounts_over'] or not CT.near(-over[fy][1], by_year[fy]['over']):
            fail('FY%d accounts past budget no longer match the surplus payload' % fy)
    if not CT.near(under[2026] - over[2026][1], fl(left)):
        fail('the two halves no longer net to the surplus')
    if not (over[2025][0] < 10 < min(over[y][0] for y in (2023, 2024, 2026))):
        fail('the page says FY2025 alone closed with only a handful of accounts past budget')
    no_tr = sum(1 for r in L[2026] if r['available_budget'] < -0.004
                and r['transfers_adjustments'] <= 0.004)
    if no_tr != A['overdrawn']['accounts_over_no_transfer_in']:
        fail('accounts past budget with no transfer in: ledger against payload')
    cats = S['causes']['categories']
    if not CT.near(sum(c['unspent'] for c in cats), fl(left)):
        fail('the categories no longer sum to the surplus')
    ood = [c for c in cats if c['label'] == 'Out-of-district tuition']
    if len(ood) != 1:
        fail('no single out-of-district tuition category')
    acct = {r['account']: r for r in L[2026]}
    co = acct[CB.COLLAB]
    pr = acct[CB.PRIVATE]
    top5 = A['overdrawn']['top5']
    for r in top5:
        if not CT.near(acct[r['account']]['available_budget'], r['available']):
            fail('top overrun %s no longer matches the ledger' % r['account'])
    ch = A['chronic']
    chron = round(-(sum(y['gap'] for y in ch['electricity']['years'])
                    + sum(y['gap'] for y in ch['therapy']['years'])), 2)
    if not CT.near(chron, A['chronic_total']):
        fail('electricity and therapy no longer sum to the payload’s shortfall')

    # The prepayment: nine FLLAC invoices numbered for FY2027, charged 30 June 2026.
    rows = [r for r in J.lines() if r['vendor'].startswith('FLLAC') and r['fy'] == 2026
            and r['effective_date'] == '2026-06-30' and J.COLUMN_OF[r['source']] == 'actual'
            and (r['doc_no'] or '').startswith('27L2KEY')]
    early = sum((r['amt'] for r in rows), D0)
    if len(rows) != 9 or early != y1['early'] or {r['account'] for r in rows} != {CB.COLLAB}:
        fail('the prepayment is no longer nine FY2027-numbered invoices on the collaborative line')
    if len({r['journal'] for r in rows}) != 1:
        fail('the prepayment is no longer one journal')
    if sum((r['amt'] for r in J.lines() if r['check_no'] == JS.CHECK['no']), D0) != JS.CHECK['amount']:
        fail('check %s no longer ties to its register line' % JS.CHECK['no'])

    # No reversal in the journal we hold, and no other FY2026 entry of the same amount.
    later = [r for r in J.lines() if r['fy'] == 2026 and r['effective_date'] > '2026-06-29'
             and r['source'] == 'GEN' and (r['account'] == CB.COLLAB or
                                          (r['fund'] == CB.CB_FUND and r['account'].endswith('535023')))]
    if later:
        fail('an entry after 29 June now touches the reclassed accounts: the page says none does')
    same = [r for r in J.lines() if r['fy'] == 2026 and abs(r['amt']) == charged]
    if {r['journal'] for r in same} != {d['journal']}:
        fail('another FY2026 entry carries the reclass amount; the explanations say none does')
    if d['journal'] != '2026/12/000692':
        fail('the 29 June entry is no longer journal 2026/12/000692, which the form and proof name')

    # The FY2025 annual town report's printed balance for fund 2640.
    ar = [r for r in csv.DictReader(open(os.path.join(ROOT, 'sources/data/special-revenue-funds.csv'),
                                         encoding='utf-8'))
          if r['fy'] == '2025' and r['fund'].startswith('2640')]
    if len(ar) != 1:
        fail('fund 2640 is not one row of the FY2025 annual report')
    printed = Decimal(ar[0]['v1']).quantize(Decimal('0.01'))
    if printed != charged or printed == d['held_jul']:
        fail('the FY2025 annual report no longer prints the reclass amount for fund 2640')

    # The FY2025 surplus on FY2026's footing, from the module Surplus by year uses.
    jd = JS.data()
    if not CT.near(fl(jd['left'][2026]), fl(left)):
        fail('the journal no longer reproduces the FY2026 surplus')
    left25 = Decimal(str(round(float(jd['left'][2025] - jd['closed'][2025]), 2)))
    if left25 != y0['left']:
        fail('FY2025 counted the same way differs between the two journal readings')

    return dict(d=d, y0=y0, y1=y1, charged=charged, left=left, reversed=left - charged,
                share=100 * fl(charged) / fl(left), older=older, early=early,
                no_prepay=left + early, plan=d['book'][2026][1], printed=printed, left25=left25,
                over=over, under=under, by_year=by_year, no_tr=no_tr, cats=cats, ood=ood[0],
                co=co, pr=pr, top5=top5, chron=chron, ch=ch, s26=s26, journal=d['journal'],
                n_early=len(rows), years=d['years'])


# --------------------------------------------------------------------------- the page

def quotes():
    return dict(
        incorrect=quote(thread(4), 'This was incorrect and needs to be reversed'),
        # the written-out reversal: two lines of one red answer, asserted one by one and joined
        reverse=(quote(thread(4), 'This was incorrect and needs to be reversed so that it should be:')
                 + ' ' + quote(thread(4), 'FROM Circuit Breaker 2640942-535023 TO Sp. Ed '
                                          'Transportation S5511062-535023')),
        acct=quote(thread(4), 'Sp. Ed Transportation'),
        bottom=quote(thread(4), 'there may be additional encumbrances in certain lines that should '
                                'not be there which would increase our bottom line'),
        errors=quote(thread(4), 'these are not all of the errors'),
        brochu=quote(thread(6), 'Historically, Karen Brochu handled these adjustments'),
        ask=quote(thread(2), 'Are you stating that this journal was in error?'),
        holding=quote(thread(1), 'I am holding out on sending out anything at this point.'),
        cbref=quote(thread(1), 'I am not sure as to the reference to Special Ed Circuit breaker.'),
        respond=quote(thread(1), 'Please respond as to the attached reclassification request.'),
        form=quote(FORM, 'To reclass collaborative tuitions to cb - collaborative tuitions'),
    )


def sources():
    src = CT.sources()
    out = [
        dict(src['p13-26'], key='p13-26'), dict(src['p13-25'], key='p13-25'),
        dict(src['p13-24'], key='p13-24'), dict(src['p13-23'], key='p13-23'),
        dict(src['d-munis'], key='d-munis'),
    ]
    out += [dict(s, key=k) for s, k in zip(JS.sources(), ('journal', 'accounts', 'provenance'))]
    out += [
        dict(key='form', label='Lunenburg Public Schools — Reclassification of expenses, fiscal '
                               '2026, signed 6/29/26 (from the Town Manager, 24 November 2026)',
             href=CORR + FORM),
        dict(key='proof', label='Town of Lunenburg — MUNIS journal proof, journal 692 (from the '
                                'Town Manager, 24 November 2026)', href=CORR + PROOF),
    ]
    out += [dict(key='thread%d' % n,
                 label='Email thread, 31 August–1 September 2026, printed page %d of 6 (from the '
                       'Town Manager, 24 November 2026)' % n, href=CORR + thread(n))
            for n in range(1, 7)]
    out += [
        dict(key='invoices', label='Town of Lunenburg — vendor invoice list, check 218995',
             href=CORR + INVOICES),
        dict(src['sc0729'], key='sc0729'),
        dict(key='fincom', label='Finance Committee recording, 22 October 2026 (machine captions)',
             href=JS.OCT22_HREF),
        dict(key='book', label='Lunenburg Public Schools — FY2026 budget, 3-12-25 Town Manager’s '
                               'budget (collaborative tuition and its circuit breaker line)',
             href=JS.BOOK),
        dict(key='specrev', label='Town of Lunenburg — special-revenue-fy2026-p09.xlsx (fund '
                                  'balances, 31 March 2026)',
             href='/docs/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx'),
        dict(key='dese', label='DESE — circuit breaker FAQ (spending within a year of receipt)',
             href=JS.DESE_CB_FAQ),
        dict(key='atr25', label='Town of Lunenburg — FY2025 annual town report, special revenue '
                                'schedule (4130-fy-2025-annual-town-report.pdf)',
             href='/docs/' + ATR25),
    ]
    man = {r['key'] for r in csv.DictReader(open(CT.MANIFEST, encoding='utf-8'))}
    for k in (FORM, PROOF, INVOICES) + tuple(thread(n) for n in range(1, 7)):
        if 'correspondence/' + k not in man:
            fail('correspondence/%s is not in the archive manifest' % k)
    if ATR25 not in man:
        fail('%s is not in the archive manifest' % ATR25)
    return out


def trail(f, q):
    """What happened to the entry, dated, each row linked to the record it is read from."""
    U2 = lambda v: CT.usd2(v)
    rows = [
        dict(when='29 June 2026', who='School department',
             what='A reclassification form moves %s of collaborative tuition onto the circuit '
                  'breaker. Signed over Superintendent and Director of Finance. Posted as journal '
                  '%s.' % (U2(f['charged']), f['journal']),
             quote=q['form'], links=[dict(label='The form', href=CORR + FORM),
                                     dict(label='Journal proof', href=CORR + PROOF)]),
        dict(when='30 June 2026', who='School department',
             what='%s FLLAC invoices numbered for %s, %s, are charged to the same line.'
                  % (C.num(f['n_early']), C.fy(2027), U2(f['early'])),
             links=[dict(label='Year-end tuition payment', href='/fy2026-closeout/fy2026-tuition-paid-early'),
                    dict(label='Check %s' % JS.CHECK['no'], href=CORR + INVOICES)]),
        dict(when='29 July 2026', who='School Committee',
             what='Told the year would close “well below” the year before. Neither entry is '
                  'mentioned.', links=[dict(label='Minutes', href=CT.sources()['sc0729']['href'])]),
        dict(when='31 August 2026', who='Town Manager',
             what='Asks the school office about grants and accrued payroll, after a call with the '
                  'School Committee Chair.', quote=q['brochu'],
             links=[dict(label='Thread, page 6', href=CORR + thread(6))]),
        dict(when='1 September, 11:25', who='School office',
             what='Lists the reclass first among errors the School Committee Chair read from her '
                  'notes, naming the account “%s”, and writes out the reversal. It gives no '
                  'reason; the other items listed each say what is wrong.' % q['acct'],
             quote=q['reverse'], links=[dict(label='Thread, page 4', href=CORR + thread(4))]),
        dict(when='1 September, 12:35', who='Town Manager', what='Attaches the journal entry.',
             quote=q['ask'], links=[dict(label='Thread, page 2', href=CORR + thread(2))]),
        dict(when='1 September, 12:53', who='Town Manager',
             what='To the Superintendent and the School Committee Chair only.',
             quote=q['holding'], links=[dict(label='Thread, page 1', href=CORR + thread(1))]),
        dict(when='2 and 9 September', who='School Committee',
             what='The year-end budget review is on the agenda: not recorded or minuted on the '
                  '2nd, passed over on the 9th.',
             links=[dict(label='The meeting record', href='/fy2026-closeout/fy2026-tuition-paid-early')]),
        dict(when='6 October 2026', who='Town Accountant',
             what='The period-13 reports are run. The entry stands; the school fund shows %s left.'
                  % U2(f['left']), links=[dict(label='Period-13 report', href=CT.sources()['p13-26']['href'])]),
        dict(when='22 October 2026', who='Finance Committee',
             what='Hears that a first quarter of tuition may be prepaid from the circuit breaker. '
                  'The prepayment was charged to the general fund.', quote=JS.OCT22_QUOTE,
             links=[dict(label='Recording', href=JS.OCT22_HREF)]),
    ]
    figs = [U2(f['charged']), U2(f['early']), U2(f['left']), C.num(f['n_early']), C.fy(2027)]
    allow = ('29 June 2026', '30 June 2026', '29 July 2026', '31 August 2026', '1 September',
             '11:25', '12:35', '12:53', '2 and 9 September', '6 October 2026', '22 October 2026',
             f['journal'], JS.CHECK['no'], '2nd', '9th', 'page 1', 'page 2', 'page 4', 'page 6',
             '13', '1st', q['form'], JS.OCT22_QUOTE, q['brochu'])
    allow += tuple(l['href'] for r in rows for l in r['links'])
    allow += tuple(r['quote'] for r in rows if r.get('quote'))   # the record's words, quoted
    return TB.custom(
        'entry-trail', 'The entry, dated', dict(rows=rows), figures=figs, allow=allow,
        basis=('record', 'the form, the journal and the printed thread'),
        alt='Ten dated events from the 29 June entry to the Finance Committee in October, each '
            'linked to its record.',
        so=('The school office wrote that the entry was wrong; the Town Manager asked whether it '
            'meant that and held back year-end figures. The ledger still carries it.'))


def explanations(f, q, U):
    U2 = lambda v: CT.usd2(v)
    legend = [('fits', 'Fits the record', 'good'), ('against', 'Does not fit', 'bad'),
              ('test', 'Would test it', 'neutral')]
    rows = [
        ('A year-end clean-up; the email was mistaken', (
            ('The vote assumes the circuit breaker pays part of the line, and the entry used the '
             'fund’s older money before it lapsed. The form’s wording matches the entry.', None, ()),
            ('Why all of it on 29 June, after the year before drew the fund bill by bill? Why put '
             'the request to reverse it in writing?', None, ('29 June',)),
            ('The school’s written answer to “%s”' % q['ask'], None, (q['ask'],)))),
        ('The school meant a different entry', (
            ('The email calls the account “%s”, and says the ledger holds more errors than it '
             'listed.' % q['acct'], None, (q['acct'],)),
            ('The amount, both account numbers and the date match the 29 June entry. No other '
             '%s entry carries that amount.' % C.fy(2026), {'y': figure(2026, C.fy(2026))},
             ('29 June',)),
            ('The “FY26 problems worksheet” attached to the school’s email, which is not held.',
             None, ('FY26',)))),
        ('Sized from the annual report’s balance', (
            ('The %s annual town report prints the fund at exactly %s.'
             % (C.fy(2025), U2(f['printed'])),
             {'y': figure(2025, C.fy(2025)), 'p': figure(fl(f['printed']), U2(f['printed']))}, ()),
            ('The Town’s ledger shows the fund held %s on 31 March 2026. The report may instead '
             'have picked up the reclass figure.' % U(f['d']['held_mar']),
             {'m': figure(fl(f['d']['held_mar']), U(f['d']['held_mar']))}, ('31 March 2026',)),
            ('The date that schedule was prepared, and its working papers.', None, ()))),
        ('Reversing it keeps money with the schools', (
            ('A reversal takes %s off free cash and puts it back in a fund the schools spend '
             'without a Town Meeting vote.' % U(f['charged']),
             {'c': figure(fl(f['charged']), U(f['charged']))}, ()),
            ('It lowers the school’s own surplus, and %s of the fund reached DESE’s one-year '
             'limit on 30 June. Nothing in writing gives this reason.' % U(f['older']),
             {'o': figure(fl(f['older']), U(f['older']))}, ('30 June',)),
            ('The district’s circuit breaker spending plan, and whether DESE was asked.', None, ()))),
        ('The reclass and the prepayment were one plan', (
            ('Same account, one day apart: the reclass freed %s and the prepayment used %s. '
             'Neither was announced at a meeting.' % (U(f['charged']), U(f['early'])),
             {'c': figure(fl(f['charged']), U(f['charged'])),
              'e': figure(fl(f['early']), U(f['early']))}, ()),
            ('No document links them, and the surplus still rose %s net.'
             % U(f['charged'] - f['early']),
             {'n': figure(fl(f['charged'] - f['early']), U(f['charged'] - f['early']))}, ()),
            ('The signed original of batch %s and any approval of it.' % JS.BATCH, None,
             (JS.BATCH,)))),
        ('The rest: a purchasing hold, late orders, high budgets', (
            ('Building upkeep left %s of its budget; teachers left %s.'
             % (C.pct(f['cat']['bldg']), C.pct(f['cat']['teach'])),
             {'b': figure(f['cat']['bldg'], C.pct(f['cat']['bldg'])),
              't': figure(f['cat']['teach'], C.pct(f['cat']['teach']))}, ()),
            ('A ledger records what was spent, not why; all of these fit the same rows.', None, ()),
            ('The district’s line-by-line budget build-up, with the basis for each line.', None, ()))),
    ]
    cells = {}
    for i, (_, cs) in enumerate(rows):
        for j, (k, title) in enumerate((('fits', 'Fits'), ('against', 'Does not fit'),
                                        ('test', 'Would test it'))):
            text, figs, allow = cs[j]
            basis = ('record', 'a document not yet held') if k == 'test' else \
                ('reading', 'our reading of the record')
            cells[(i, j)] = TB.cell(k, title, (text, figs, allow), basis)
    return TB.matrix(
        'Possible explanations', [r[0] for r in rows],
        ['Fits the record', 'Does not fit', 'Would test it'], cells, legend, place='body',
        note=('Our reading. None of these is established, more than one can be true, and they '
              'are set out because the district has not offered one. The first five are about '
              'the 29 June entry; the last is about the rest of the surplus.', None, ('29 June',)),
        row_label='Explanation', col_label='Against the record')


def page(f):
    """THE ORDER, TJ's (25 November 2026): the four years first, because FY2026 is the SECOND
    anomalous year and FY2025 is no baseline ("you have to look before FY 25"); then the tuition
    line against its circuit breaker plan; then how the fund was drawn against the years before;
    then the two halves. The 29 June entry's record and a short 'If the entry were reversed'
    follow the core: the reversal is a possible event with consequences, never a reading of the
    surplus ("it shouldn't be the core write up of the surplus")."""
    q = quotes()
    U = lambda v: C.usd(fl(v))
    UF = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    P = lambda v, dp=0: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    fact, con = LD.fact, TP.conclusion
    y1, ov, un, Y = f['y1'], f['over'], f['under'], f['years']
    cats = {c['key']: c for c in f['cats']}
    f['cat'] = dict(bldg=cats['buildings']['pct_of_revised'], teach=cats['teachers']['pct_of_revised'])
    if not cats['buildings']['pct_of_revised'] > 10 * cats['teachers']['pct_of_revised']:
        fail('the explanations say upkeep left a far larger share than teachers')
    owed = {y: Y[y]['left'] for y in (2023, 2024, 2025, 2026)}
    about = round(fl(max(owed[2023], owed[2024])), -3)
    if not all(abs(fl(owed[y]) - about) < 500 for y in (2023, 2024)):
        fail('FY2023 and FY2024 are no longer both within $500 of %s' % C.usd(about))
    if not min(owed[2025], owed[2026]) > 10 * max(owed[2023], owed[2024]):
        fail('the page says FY2025 and FY2026 each left over ten times FY2023-FY2024')
    gross, plan = f['d']['book'][2026]
    own, gfv = f['d']['own'], gross - plan
    past_plan = own - gross
    if not (own > gross > plan > f['charged'] > 0):
        fail('the plan panel says the year’s bills ran past the whole plan and the fund was '
             'charged less than its share')
    early_prior = min(Y[y]['drawn_early'] for y in (2023, 2024, 2025))
    if not early_prior > 100 * y1['drawn_early']:
        fail('the page says FY2023-FY2025 drew the fund through the year and FY2026 did not')
    co_over = -f['co']['available_budget']

    facts = [
        fact('left', UF(f['left']), 'left unspent, school general fund, %s' % C.fy(2026),
             'published', {'y': F(2026)}),
        fact('left25', UF(owed[2025]), 'left in %s, counted the same way' % C.fy(2025), 'published',
             {'y': F(2025)}),
        fact('left23', UF(owed[2023]), 'left in %s (%s: %s)' % (C.fy(2023), C.fy(2024),
                                                                 U(owed[2024])), 'published',
             {'y': F(2023), 'z': F(2024), 'b': UF(owed[2024])}),
        fact('plan', UF(plan), 'circuit breaker the budget planned for this tuition', 'published'),
        fact('charged', UF(f['charged']), 'charged to the circuit breaker, all on 29 June',
             'published', allow=('29 June',)),
        fact('own', UF(own), 'this year’s collaborative tuition bills', 'published'),
        fact('may26', UF(y1['drawn_early']), 'tuition the fund paid July to May, %s' % C.fy(2026),
             'published', {'y': F(2026)}),
        fact('older', UF(f['older']), 'of the fund’s money due to lapse on 30 June (our sum)',
             'estimate', allow=('30 June',)),
        fact('under', UF(un[2026]), 'left on accounts that came in under', 'published'),
        fact('over', UF(ov[2026][1]), 'spent past budget on the accounts that went over',
             'published'),
        fact('n26', N(ov[2026][0], 'accounts'), 'accounts past budget at the close', 'published'),
    ]
    conclusions = [
        con('%s and %s each left about %s; %s left %s and %s %s.'
            % (C.fy(2023), C.fy(2024), C.usd(about), C.fy(2025), U(owed[2025]), C.fy(2026),
               U(f['left'])), ['left23', 'left25', 'left'],
            {'a': F(2023), 'b': F(2024), 'c': figure(about, C.usd(about)), 'd': F(2025),
             'e': UF(owed[2025]), 'f': F(2026), 'g': UF(f['left'])},
            so='%s was itself the outlier, so the years to judge %s against are the two before it.'
               % (C.fy(2025), C.fy(2026)), so_figures={'a': F(2025), 'b': F(2026)}),
        con('The circuit breaker was planned to pay %s of this tuition; it paid %s, all on 29 June.'
            % (U(plan), U(f['charged'])), ['plan', 'charged', 'own'],
            {'p': UF(plan), 'c': UF(f['charged'])}, allow=('29 June',),
            so='The year’s own bills ran %s past the whole plan, before any %s invoices.'
               % (U(past_plan), C.fy(2027)), so_figures={'x': UF(past_plan), 'y': F(2027)}),
        con('%s to %s the fund paid at least %s of tuition by May; %s, %s.'
            % (C.fy(2023), C.fy(2025), U(early_prior), C.fy(2026), U(y1['drawn_early'])),
            ['may26', 'older'],
            {'a': F(2023), 'b': F(2025), 'e': UF(early_prior), 'y': F(2026),
             'm': UF(y1['drawn_early'])},
            so='%s of the fund was due to lapse on 30 June; the one charge used all of it.'
               % U(f['older']), so_figures={'o': UF(f['older'])}, so_allow=('30 June',)),
        con('The %s is a net: %s left on some accounts, %s spent past others.'
            % (U(f['left']), U(un[2026]), U(ov[2026][1])), ['under', 'over', 'n26'],
            {'a': UF(f['left']), 'u': UF(un[2026]), 'o': UF(ov[2026][1])},
            so='Salaries landed close to budget, so how closely lines were budgeted shows in the '
               'halves, not the total.',
            notes=[CT.step('%s accounts closed past budget; %s had %s, %s %s, and %s only %s.'
                           % (C.num(ov[2026][0]), C.fy(2023), C.num(ov[2023][0]), C.fy(2024),
                              C.num(ov[2024][0]), C.fy(2025), C.num(ov[2025][0])), 'measured',
                           {'n': N(ov[2026][0]), 'a': F(2023), 'b': N(ov[2023][0]), 'c': F(2024),
                            'd': N(ov[2024][0]), 'z': F(2025), 'm': N(ov[2025][0])})]),
    ]

    yrs = (2023, 2024, 2025, 2026)
    four = TB.chart(TP.series(
        'School budget left at year end', [C.fy(y) for y in yrs],
        [TP.track('Left unspent, orders owed counted as spent', [fl(owed[y]) for y in yrs],
                  'published', 'bar')], '$', kind='bar',
        note='School general fund, closed-year reports, the same footing every year. Earlier years '
             'are not held.'),
        place='top',
        so=('Two years landed within about %s of budget; the next two left more than ten times '
            'that.' % C.usd(about), {'b': figure(about, C.usd(about))}, ()))
    plan_panels = TB.panels('Collaborative tuition against its plan', [
        TB.panel('The plan, budget book', [
            ('The whole line', U(gross), None),
            ('From the circuit breaker', U(plan), None),
            ('From the general fund, voted', U(gfv), None)]),
        TB.panel('The year, ledger', [
            ('This year’s bills', U(own), 'bad'),
            ('Charged to the circuit breaker, last week of June', U(f['charged']), None),
            ('Next year’s invoices, charged to this year', U(f['early']), None),
            ('Past its budget at the close', U(co_over), 'bad')])],
        note=('The budget voted the line net of the circuit breaker share. Next year’s invoices are '
              'nine for %s, charged to %s.' % (C.fy(2027), C.fy(2026)),
              {'a': F(2027), 'b': F(2026)}, ('nine',)),
        so=('The bills ran past the whole plan and the fund paid less than its share, so the '
            'general fund carried both.', None, ()))
    draws = TB.chart(TP.series(
        'What the circuit breaker paid on tuition', [C.fy(y) for y in yrs],
        [TP.track('July to May', [fl(Y[y]['drawn_early']) for y in yrs], 'published', 'bar'),
         TP.track('June', [fl(Y[y]['drawn_june']) for y in yrs], 'published', 'bar')],
        '$', kind='bar', stacked=True,
        note='Fund 2640, special education tuition charged to it, by when it was charged. School '
             'journal.', note_allow=('2640',)),
        place='body',
        so=('Every earlier year the fund paid tuition as the bills came; in %s it paid almost '
            'nothing until 29 June.' % C.fy(2026), {'y': F(2026)}, ('29 June',)))

    trail_block = trail(f, q)
    reversal = TB.explain('If the entry were reversed', [
        ('On 1 September the school office called the 29 June entry incorrect, with no reason '
         'given. On 6 October it still stood. A reversal would mean:', None,
         ('1 September', '29 June', '6 October')),
        ('**Free cash** certified from %s would fall by %s.' % (C.fy(2026), U(f['charged'])),
         {'y': F(2026), 'c': UF(f['charged'])}, ()),
        ('**None** of the %s of circuit breaker money the budget planned for this tuition would '
         'have been used.' % U(plan), {'p': UF(plan)}, ()),
        ('%s of the fund reached DESE’s one-year limit on 30 June (our sum). Whether it can still '
         'be spent is a question for DESE.' % U(f['older']), {'o': UF(f['older'])}, ('30 June',)),
    ], place='body', tone='callout')
    settle = TB.explain('What would settle it', [
        ('**The school department’s written answer to the Town Manager’s 1 September request '
         'about the reclassification.** It would say whether the district stands by the entry '
         'and, if not, why.', None, ('1 September',)),
        ('Behind it: any correcting entry after 6 October, or a rerun of the period-13 reports; the '
         'Town Accountant’s fund 2640 balances at 30 June 2025 and 2026; the “FY26 problems '
         'worksheet”; the signed original of batch %s.' % JS.BATCH, None,
         ('6 October', '13', '2640', '30 June 2025', '2026', 'FY26', JS.BATCH)),
    ], tone='callout')
    credit = TB.explain('Credit where the record shows it', [
        'The Town Manager answered the school office within the hour, asked in writing whether the '
        'journal was in error, and held back year-end figures rather than send ones in dispute.',
    ], tone='plain')

    cat_table = dict(
        caption='Where the %s school surplus was left, by category' % C.fy(2026),
        views=[dict(
            key='categories', label='Department 300, period 13', total_col=3, kinds=['ledger'] * 4,
            columns=['Budget after transfers', 'Paid', 'Still committed', 'Left'],
            rows=[dict(label=c['label'], cells=[C.usd(c['revised']), C.usd(c['expended']),
                                               C.usd(c['encumbered']), C.usd(c['unspent'])])
                  for c in f['cats']]
            + [dict(label='All categories', cells=[
                C.usd(f['s26']['revised_budget']), C.usd(f['s26']['ytd_expended']),
                C.usd(f['s26']['encumbrances']), C.usd(f['s26']['available_budget'])])],
            note='Categories are ours, each account placed by its DESE function and object code; '
                 'the figures are the ledger’s. Out-of-district tuition includes the 29 June '
                 'charge to the circuit breaker.')])
    years_table = dict(caption='School accounts past their budgets at the close, by year', views=[
        dict(key='years', label='Department 300, period 13', total_col=-1, kinds=['ledger'] * 3,
             columns=['Accounts past budget', 'By how much', 'Transfers in, gross'],
             rows=[dict(label=C.fy(fy), cells=[C.num(ov[fy][0]), C.usd(ov[fy][1]),
                                               C.usd(f['by_year'][fy]['transfers_in'])])
                   for fy in (2026, 2025, 2024, 2023)],
             note='Past budget means the report’s own available column is below zero. %s of '
                  '%s’s %s received no transfer in. Electricity and contracted therapy were voted '
                  'below their spending in all four years, by %s.'
                  % (C.num(f['no_tr']), C.fy(2026), C.num(ov[2026][0]), C.usd(f['chron'])))])
    top_table = dict(caption='The five largest overruns, %s' % C.fy(2026), views=[
        dict(key='top', label='Department 300, period 13', total_col=-1, kinds=['ledger'] * 4,
             columns=['Voted', 'Paid', 'Still committed', 'Past budget'],
             rows=[dict(label=r['description'].capitalize(), cells=[
                 C.usd(r['original']), C.usd(r['spent']), C.usd(r['encumbered']),
                 C.usd(-r['available'])]) for r in f['top5']],
             note='Kindergarten aides had no budget and received no transfer. Collaborative '
                  'tuition is after the 29 June entry.')])

    cite = TP.cite
    flow = [
        'finding',
        cite(four, 'p13-26', 'p13-25', 'p13-24', 'p13-23', 'journal'), ('conclusion', 0),
        cite(plan_panels, 'book', 'p13-26', 'journal', 'invoices'), ('conclusion', 1),
        cite(draws, 'journal', 'specrev', 'dese'), ('conclusion', 2),
        cite(('chart', 0), 'p13-26', 'd-munis'), cite(('table', 0), 'p13-26', 'd-munis'),
        ('conclusion', 3),
        cite(('table', 1), 'p13-26', 'p13-25', 'p13-24', 'p13-23', 'd-munis'),
        cite(('table', 2), 'p13-26', 'accounts'),
        cite(trail_block, 'form', 'proof', 'journal', 'thread1', 'thread2', 'thread4', 'thread6',
             'invoices', 'sc0729', 'p13-26', 'fincom'),
        cite(reversal, 'thread4', 'p13-26', 'book', 'journal', 'dese'),
        cite(explanations(f, q, U), 'thread3', 'thread5', 'atr25', 'specrev', 'journal', 'dese',
             'provenance'),
        cite(settle, 'thread1', 'specrev'), cite(credit, 'thread2'),
        'sources',
    ]
    return TP.page(
        ID,
        '%s left %s, the second year running far above the %s that %s and %s each left.'
        % (C.fy(2026), U(f['left']), C.usd(about), C.fy(2023), C.fy(2024)),
        facts, conclusions,
        chart=dict(id='fy26-school-surplus-causes', source=CT.SRC26),
        table=cat_table, tables=[years_table, top_table],
        sources=sources(), flow=flow,
        finding_figures={'y': F(2026), 'a': UF(f['left']), 'b': figure(about, C.usd(about)),
                         'c': F(2023), 'd': F(2024)})


def render(f=None):
    p = page(f or data())
    p['not_established'] = [
        'Whether the school department stands by the 29 June 2026 entry, or has reversed it.',
        'Why the circuit breaker was not drawn from July to May in FY2026.',
        'Whether the 29 June charge and the 30 June prepayment were decided together.',
        'Why any line came in under or over budget.',
    ]
    return json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('fy2026 school surplus: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
