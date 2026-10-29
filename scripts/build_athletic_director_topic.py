#!/usr/bin/env python3
"""THE ATHLETIC DIRECTOR POST, FY2011-FY2027: who held it, what each document says it cost,
and whether any of it was ever paid from the athletic fee fund (1301).

    python3 scripts/build_athletic_director_topic.py           # write fy28/public/data/topics/athletic-director.json
    python3 scripts/build_athletic_director_topic.py --check   # fail if it would change

    athletic-director   /athletics/athletic-director   Athletic director

On the Athletics shelf (scripts/topic_registry/athletics.py, through TOPIC_GENERATORS). Asked for
28 October 2026: TJ had "for years ... been discussing and talking about the AD being paid from the
athletic fees in some portion". The page answers from the documents, either way, and its shape is
a TIMELINE (rule 7h): the answer is a sequence of who held the post and which line paid it.

THE QUESTION, AND WHAT EACH SOURCE CAN SAY ABOUT IT:
  * the general fund ATHLETIC DIRECTOR line by year: budget books (line-history.csv: `restated`
    is an actual printed in a later book, `settled` a budget, `proposed` a proposal), and from
    FY2023 the school journal, tied to the Town's period-13 report to the cent;
  * the fee fund's own side: itemised for FY2014-FY2019 in the district's FY19 athletics
    document (athletics-history.csv), which prints an Athletic Secretary (658) and no director;
    totals only for FY2020-FY2022 (annual reports); every pay run FY2023-FY2026 (journal);
  * what each director EARNED: the annual town reports' gross wages, which are CALENDAR years
    and all funds (gross-wages.csv). A calendar year straddles two fiscal years, so it is set
    beside the two general fund figures it falls between, never subtracted from one;
  * who held the post: the school rosters printed in each annual report (staff-roster-entries.csv),
    one OCR page for FY2019, agendas and minutes for the changes.

TWO READINGS OF OURS, labelled everywhere they appear:
  * THE REGULAR SLICE. Beside three season lumps a year, the fee fund's high school salary
    account is charged a small amount in nearly every pay run. In FY2025 and FY2026 every such
    line is a whole number of half-hours at one rate ($23.77, then $24.72) -- asserted below.
    An hourly wage is not a director's salary; that it is the part-time athletic secretary,
    whom the FY26 budget book says was "paid w/Athletic Revolving account", is our reading.
  * THE $13,691.53. The 20 August 2025 memo entry moved FY2025's high school fee-fund pay to
    the general fund: whole dollars to ATHLETIC COACHES, and $13,691.53 to H.S. PRINCIPAL/ASST
    PRINCIPAL. That the second is the whole of that pay less its whole-dollar part is our
    arithmetic, asserted below. Which post it was is in the memo, which we do not hold.

REDACTION: directors and the athletic secretary are public employees named in the Town's own
reports; they are named. No family or child is.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import journal as J  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
ME = os.path.basename(__file__)
TID = 'athletic-director'
MINE = sorted(t for t, (_, _, gen) in REG.TOPICS.items() if gen == ME)
DATA = os.path.join(ROOT, 'sources', 'data')
TXT = os.path.join(ROOT, 'sources', 'district-budget', 'text')
MEET = os.path.join(ROOT, 'sources', 'meetings', 'text')
CAPS = os.path.join(DATA, 'youtube-transcripts')
AD_ACCT = '0100-3-300-3510-06-6-67-1-511026'
SEC_ACCT = '0100-3-300-3510-06-6-67-1-511032'
HSP_ACCT = '0100-3-300-2210-01-6-08-1-511001'
FEE_HS_PAY = '1301-3-300-3510-06-0-00-1-519999'
MEMO_JR = '2025/12/001339'
REGULAR_MAX = Decimal(1100)           # a pay-run line under this is the regular slice; above, a season lump
RATES = {2025: Decimal('23.77'), 2026: Decimal('24.72')}
YEARS = list(range(2011, 2028))
ZERO = Decimal(0)

WHICH_CLOSES = ('payroll account detail for the athletic director, FY2011 to FY2017, naming the '
                'account each payment was charged to')
MEMO_CLOSES = 'the memo of 20 August 2025 behind journal entry 2025/12/001339'
WHO_CLOSES = 'payroll detail by employee for the fee fund’s high school salary account, FY2023 to FY2026'
FY27_CLOSES = 'the FY2027 school budget as voted, and the half-time director’s appointment terms'

# WHO HELD THE POST, as each document names them. (fy, name, document, coordinate, raw text)
# The roster rows are read from staff-roster-entries.csv; the rest are declared here with the
# line that names them, and each is checked against the file.
DECLARED = [
    (2019, 'James Bunnell', 'sources/town-budget/pages/FY2019.ocr.txt', 'James Bunnell-AD',
     'FY2019 annual town report, school roster (OCR page)'),
    (2022, 'James Bunnell', 'sources/meetings/text/school-advisory-councils-committees/2022-06-06-agenda-4419.txt',
     'James Bunnell, Lunenburg Schools Athletic Director', 'Athletic Advisory Council agenda, 6 June 2022'),
    (2023, 'Kevin Bigelow', 'sources/meetings/text/school-advisory-councils-committees/2022-08-22-agenda-4420.txt',
     'Kevin Bigelow, Lunenburg Schools Athletic Director', 'Athletic Advisory Council agenda, 22 August 2022'),
    (2025, 'Kevin Bigelow', 'sources/meetings/text/athletic-advisory-council/2025-02-04-agenda-6979.txt',
     'Kevin Bigelow, Athletic Director', 'Athletic Advisory Committee agenda, 4 February 2025'),
    (2026, 'Yanina Burns', 'sources/meetings/text/school-committee/2025-06-04-minutes-7251.txt',
     'the part time Assistant Principal and part time Athletic Director for the next school year',
     'School Committee minutes, 4 June 2025'),
    (2027, 'Robert Papazian', 'sources/meetings/text/school-committee/2026-07-29-minutes-7930.txt',
     '.5 Athletic Director, replacing Ms. Burns', 'School Committee minutes, 29 July 2026'),
]
# THE ROSTER THAT IS WRITTEN FROM A LATER VANTAGE. The FY2025 annual report is "written from a
# February 2026 vantage" (report-anomalies.csv); its roster names the FY2026 director.
LATER_VANTAGE = {2025}
SEC_DECLARED = [
    (2019, 'Darlene Steele', 'sources/town-budget/pages/FY2019.ocr.txt', 'Darlene Steele-AD Secretary'),
    (2027, 'Courtney Fuller', 'sources/data/school-staff-directory.csv', 'Fuller, Courtney",Athletics Secretary'),
]
PEOPLE = ['Peter McCauliff', 'James Bunnell', 'Kevin Bigelow', 'Yanina Burns', 'Robert Papazian']
WAGE_KEYS = {'Peter McCauliff': 'MCCAULIFF PETER', 'James Bunnell': 'BUNNELL JAMES',
             'Kevin Bigelow': 'BIGELOW KEVIN', 'Yanina Burns': 'BURNS YANINA'}
SECRETARIES = ['Darlene Steele', 'Courtney Fuller']

# THE MEETING RECORD of the FY2026 offset: (board, date, video id, start second, verbatim words)
CAPTIONS = [
    ('school-committee', '2025-04-16', '1ZVK0_sfUqw', 9608,
     'in the budget is the athletic director\'s salary minus 20,000 offset from athletic'),
    ('finance-committee', '2025-03-20', 'PV-DE3N8_PU', 2974,
     'because you\'re funding with the revolving account in part'),
]
BOOK26 = os.path.join(TXT, 'final-fy26-town-manager-39-s-target-budget.txt')
BOOK26_LINE = 'Athletic Director 92,455              94,813 94,813 74,406 -19.52%'
SUPT26 = os.path.join(TXT, 'sc-meetings', '2025-02-26-fy26-superintendent-s-proposed-budget-2-26-25.txt')
SUPT26_LINE = '(3)Eliminate Part-time Secretary (paid w/Athletic Revolving account); apply'
FY25BOOK = os.path.join(TXT, 'sc-meetings', '2023-2024-superintendent-s-fy25-proposed-budget.txt')
FY25BOOK_LINE = 'Position was made full-time in FY19 to improve:'
FY27BOOK = os.path.join(TXT, 'final-budget-document.txt')
FY27BOOK_LINE = 'Athletic Director $74,406 $20,000 $20,000 $20,000'


def fail(msg):
    raise SystemExit('build_athletic_director_topic: ' + msg)


def D(*texts):
    return tuple(re.findall(r'\d[\d,.]*\d|\d', ' '.join(texts)))


def long_date(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return '%d %s %d' % (d, ('January February March April May June July August September October '
                             'November December').split()[m - 1], y)


def usd2(v):
    v = Decimal(v)
    return ('-$%s' if v < 0 else '$%s') % format(abs(v), ',.2f')


def has(path, words):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if words not in open(p, encoding='utf-8').read():
        fail('%s no longer holds %r' % (os.path.relpath(p, ROOT), words))


def caption_check(board, date, vid, t0, words):
    ps = glob.glob(os.path.join(CAPS, board, '%s-%s.json' % (date, vid)))
    if len(ps) != 1:
        fail('no caption file for %s %s' % (board, date))
    S = json.load(open(ps[0], encoding='utf-8'))['segments']
    near = ' '.join(s['text'] for s in S if t0 - 5 <= s['start'] <= t0 + 30)
    if words not in near:
        fail('the %s %s captions no longer say %r near %ds' % (board, date, words, t0))
    return 'https://www.youtube.com/watch?v=%s&t=%ds' % (vid, t0)


# ------------------------------------------------------------------ the general fund line
def gf_line():
    """fy -> (value, basis, document). Actuals first: the journal from FY2023 (tied to the
    period-13 report), else a later book's actual column (`restated`), else a budget."""
    lh = defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(DATA, 'line-history.csv'), encoding='utf-8')):
        if r['key'] == 'athletic director' and not r['variant']:
            lh[int(r['fy'])][r['stage']] = (Decimal(r['value']), r['source'])
    out = {}
    for y in range(2014, 2023):
        if 'restated' not in lh[y]:
            fail('FY%d: no actual for the athletic director line' % y)
        out[y] = (lh[y]['restated'][0], 'actual, a later budget book', lh[y]['restated'][1])
    # the FY2018 book budgeted half a post: kept beside the actual
    if lh[2018].get('settled', (None,))[0] != Decimal(48000):
        fail('FY2018 budget is no longer 48,000')
    if lh[2019].get('proposed', (None,))[0] != Decimal(49440):
        fail('FY2019 proposal is no longer 49,440')
    A = J.accounts()
    L = [r for r in J.lines() if r['account'] in (AD_ACCT, SEC_ACCT)]
    ytd = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8')):
        if r['account'] in (AD_ACCT, SEC_ACCT) and r['period'] == '13':
            ytd[(int(r['fiscal_year']), r['account'])] = (Decimal(r['ytd_expended']), Decimal(r['original_approp']))
    for y in J.YEARS:
        for acct in (AD_ACCT, SEC_ACCT):
            act = sum((r['amt'] for r in L if r['fy'] == y and r['account'] == acct
                       and r['posts_to'] == 'actual'), ZERO)
            bud = sum((r['amt'] for r in L if r['fy'] == y and r['account'] == acct
                       and r['posts_to'] == 'original_budget'), ZERO)
            if (act, bud) != ytd[(y, acct)]:
                fail('FY%d %s: journal %s/%s; period-13 report %s' % (y, acct, act, bud, ytd[(y, acct)]))
            if acct == AD_ACCT:
                out[y] = (act, 'actual, the school journal', 'munis-school-journal.csv')
    sec26 = ytd[(2026, SEC_ACCT)]
    if any(ytd[(y, SEC_ACCT)] != (ZERO, ZERO) for y in J.YEARS if y != 2026):
        fail('the general fund carried an athletic secretary before FY2026')
    # FY2026: the book's level service and its vote, and the secretary line
    has(BOOK26, BOOK26_LINE)
    lvl26, voted26 = Decimal(94813), Decimal(74406)
    if out[2026][0] != voted26 or sec26[1] != lvl26 - voted26:
        fail('FY2026: the line or the secretary budget no longer matches the book')
    has(FY27BOOK, FY27BOOK_LINE)
    if not any(v == Decimal(20000) for v, _ in [lh[2027].get('proposed', (None, None))]) and \
            not any(r for r in csv.DictReader(open(os.path.join(DATA, 'line-history.csv'), encoding='utf-8'))
                    if r['key'] == 'athletic director' and r['fy'] == '2027' and r['value'] == '20000'):
        fail('FY2027: the last draft no longer proposes 20,000')
    return out, dict(lvl26=lvl26, voted26=voted26, sec26_budget=sec26[1], sec26_spent=sec26[0],
                     fy18_budget=Decimal(48000), fy19_prop=Decimal(49440), fy27_last=Decimal(20000))


# ------------------------------------------------------------------ the fee fund's pay runs
def fee_pay():
    L = J.lines()
    A = J.accounts()
    if not any(r['fund'] == '1301' for r in L):
        fail('no fund 1301 in the journal')
    # 1. no fund 1301 line names the director, in a memo, a vendor or a comment
    for r in L:
        if r['fund'] == '1301' and re.search(r'ATHLETIC DIR|\bA\.?D\.? SAL', ' '.join(
                (r['description'], r['comment'], r['account_description'])).upper()):
            fail('a fund 1301 line names the athletic director: %s' % r['journal'])
    pay = [r for r in L if r['account'] == FEE_HS_PAY and r['source'] in ('PRJ', 'PRH')]
    reg = defaultdict(list)
    for r in pay:
        if r['amt'] < REGULAR_MAX:
            reg[r['fy']].append(r)
    # 2. the regular slice is a whole number of half-hours at one rate, FY2025 and FY2026
    for y, rate in RATES.items():
        for r in reg[y]:
            k = (r['amt'] / rate * 2).to_integral_value()
            if (rate * k / 2).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP') != r['amt']:
                fail('FY%d: %s is not a whole number of half-hours at %s' % (y, r['amt'], rate))
    dup = sum((r['amt'] for r in L if r['account'] == FEE_HS_PAY and r['source'] == 'GRV'), ZERO)
    lumps = {y: sum((r['amt'] for r in pay if r['fy'] == y and r['amt'] >= REGULAR_MAX), ZERO) for y in J.YEARS}
    regular = {y: sum((r['amt'] for r in reg[y]), ZERO) for y in J.YEARS}
    slice26 = sum((r['amt'] for r in reg[2026]), ZERO) + dup
    last25 = max(r['effective_date'] for r in pay if r['fy'] == 2025)
    # 3. the 20 August 2025 memo: both ends, and the arithmetic of the $13,691.53
    m = [r for r in L if r['journal'] == MEMO_JR]
    hsp = sum((r['amt'] for r in m if r['account'] == HSP_ACCT), ZERO)
    hs25 = sum((r['amt'] for r in pay if r['fy'] == 2025), ZERO)
    if hsp != Decimal('13691.53'):
        fail('the memo entry no longer moves 13,691.53 to the principal line')
    whole = hs25 - hsp
    if whole != whole.to_integral_value():
        fail('FY2025 high school fee-fund pay less the principal-line amount is not whole dollars')
    # the same entry takes MORE out of the fee account than FY2025's pay runs charged it
    out25 = -sum((r['amt'] for r in m if r['account'] == FEE_HS_PAY), ZERO)
    if out25 <= hs25:
        fail('the memo no longer moves more out of the fee account than FY2025 pay charged')
    # THE $13,691.53 FITS THE HOURLY RATE: a whole number of hours at FY2025's rate, to a cent
    # (our arithmetic; it does not say whose hours)
    hrs = (hsp / RATES[2025]).to_integral_value()
    if abs(hrs * RATES[2025] - hsp) > Decimal('0.01'):
        fail('the principal-line amount is no longer a whole number of hours at %s' % RATES[2025])
    # 4. the AD's own reimbursements from the fund (not pay): read, declared
    reimb = [r for r in L if r['fund'] == '1301' and r['source'] == 'API'
             and r['vendor'].startswith('BIGELOW KEVIN')]
    reimb_t = sum((r['amt'] for r in reimb), ZERO)
    return dict(slice26=slice26, rate25=RATES[2025], rate26=RATES[2026], n26=len(reg[2026]),
                last25=last25, hsp=hsp, hs25=hs25, whole=whole, reimb=reimb_t, out25=out25, hrs=int(hrs), lumps=lumps, regular=regular,
                reimb_n=len(reimb))


# ------------------------------------------------------------------ people and wages
def people():
    held = defaultdict(set)          # name -> fys
    src = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(DATA, 'staff-roster-entries.csv'), encoding='utf-8')):
        role = (r['role_raw'] + ' ' + r['position'] + ' ' + r['grade_or_dept']).lower()
        y = int(r['fy'])
        if ('athletic director' in role or r['role_raw'].strip() == 'AD') and 'secret' not in role:
            if y in LATER_VANTAGE:
                continue
            held[r['name'].replace('Bunnell, James', 'James Bunnell')].add(y)
    for y, name, path, words, label in DECLARED:
        has(path, words)
        held[name].add(y)
    sec = defaultdict(set)
    for r in csv.DictReader(open(os.path.join(DATA, 'staff-roster-entries.csv'), encoding='utf-8')):
        role = (r['role_raw'] + ' ' + r['grade_or_dept']).lower()
        y = int(r['fy'])
        if re.search(r'athletic\W*sec|ad secretary', role):
            # the FY2025 report's roster is written from February 2026: it names FY2026's staff
            sec[r['name'].replace('Steele, Darlene', 'Darlene Steele')].add(2026 if y in LATER_VANTAGE else y)
    for y, name, path, words in SEC_DECLARED:
        has(path, words)
        sec[name].add(y)
    if sorted(held) != sorted(PEOPLE):
        fail('the directors named are %s' % sorted(held))
    wages = defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(DATA, 'gross-wages.csv'), encoding='utf-8')):
        for who, key in WAGE_KEYS.items():
            nm = r['name'].replace('SCHOOL ', '').strip()
            if nm == key or (key == 'MCCAULIFF PETER' and nm == 'MCCAULIFF' and r['fy'] == '2015'):
                wages[who][int(r['fy'])] = (Decimal(r['amount']), r['page'], r['as_printed'])
    return held, sec, wages


def build():
    gf, B = gf_line()
    fp = fee_pay()
    held, sec, wages = people()
    U = lambda v: figure(float(v), C.usd(v))
    U2 = lambda v: figure(float(v), usd2(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    f, con = LD.fact, TP.conclusion

    # CALENDAR EARNINGS BESIDE THE TWO FISCAL YEARS EACH STRADDLES (our arithmetic). Asserted
    # for every Bunnell year held: earnings fall between the two general fund actuals.
    bun = wages['James Bunnell']
    for cy, (amt, _, _) in bun.items():
        lo, hi = sorted([gf[cy][0], gf[cy + 1][0]])
        if not lo <= amt <= hi:
            fail('calendar %d: Bunnell earned %s, outside the line’s %s and %s' % (cy, amt, lo, hi))
    mc = wages['Peter McCauliff']
    if any(gf[y][0] != 0 for y in range(2014, 2018)):
        fail('the line is no longer zero FY2014-FY2017')
    mc17 = mc[2017][0]

    # captions and book lines
    hrefs = [caption_check(*c) for c in CAPTIONS]
    has(SUPT26, SUPT26_LINE)
    has(FY25BOOK, FY25BOOK_LINE)

    px = {}
    px['gf26'] = f('gf26', U(B['voted26']), 'director line, FY2026, voted and spent', 'published', {'y': F(2026)})
    px['lvl26'] = f('lvl26', U(B['lvl26']), 'the same line at level service, FY2026', 'published', {'y': F(2026)})
    px['sec26'] = f('sec26', U(B['sec26_budget']), 'athletic secretary line added, FY2026', 'published', {'y': F(2026)})
    px['sec26s'] = f('sec26s', U(B['sec26_spent']), 'spent on that secretary line, FY2026', 'published', {'y': F(2026)})
    px['slice'] = f('slice', U(fp['slice26']), 'regular hourly pay on the fee fund, FY2026 (ours)', 'estimate',
                    {'y': F(2026)})
    px['rate'] = f('rate', U2(fp['rate26']), 'the hour rate every such FY2026 line fits', 'estimate', {'y': F(2026)})
    px['hsp'] = f('hsp', U2(fp['hsp']), 'fee-fund pay moved to the principal line, FY2025', 'published',
                  {'y': F(2025)})
    px['fy18'] = f('fy18', U(gf[2018][0]), 'director line, FY2018, actual: a half post', 'published', {'y': F(2018)})
    px['mc17'] = f('mc17', U(mc17), 'what the director earned, calendar 2017', 'published', allow=('2017',))
    px['which'] = f('which', None, 'which line paid the director, FY2011 to FY2017', 'gap',
                    closes=WHICH_CLOSES, allow=D('FY2011 FY2017', WHICH_CLOSES))
    px['memo'] = f('memo', None, 'which post the $13,691.53 paid', 'gap', closes=MEMO_CLOSES,
                   allow=D('$13,691.53', MEMO_CLOSES))
    px['fy27'] = f('fy27', None, 'the FY2027 line as voted', 'gap', closes=FY27_CLOSES, allow=D('FY2027', FY27_CLOSES))

    b20 = bun[2020][0]
    concl = [
        con('No record held pays the director from the fee fund; the FY19 document’s fee side has no director line.',
            ['gf26', 'fy18', 'which'], allow=('FY19',),
            so='Where fees and the director meet in the record, it is a budget offset for FY2026, not a payment.',
            so_figures={'y': F(2026)},
            notes=[step('The journal, %s to %s, holds no fee-fund line that names the director, and his '
                        'own line is the general fund’s.' % (C.fy(J.YEARS[0]), C.fy(J.YEARS[-1])), 'measured',
                        {'a': F(J.YEARS[0]), 'b': F(J.YEARS[-1])}),
                   step('%s to %s the fund is totals only. Bunnell’s calendar 2020 pay, %s, sits between the '
                        'line’s %s and %s actuals: our arithmetic.'
                        % (C.fy(2020), C.fy(2022), C.usd(b20), C.fy(2020), C.fy(2021)), 'estimate',
                        {'a': F(2020), 'b': F(2022), 'c': U(b20), 'e': F(2021)}, allow=('2020', '2019', '2021')),
                   step('Expense reimbursements to the director, %s in %d payments, are not pay.'
                        % (usd2(fp['reimb']), fp['reimb_n']), 'measured',
                        {'a': U2(fp['reimb']), 'n': figure(fp['reimb_n'], str(fp['reimb_n']), 'payments')})]),
        con('For FY2026 the director line was voted %s, %s below level service; meetings called it a fee offset.'
            % (C.usd(B['voted26']), C.usd(B['lvl26'] - B['voted26'])), ['gf26', 'lvl26', 'sec26', 'sec26s'],
            {'y': F(2026), 'a': U(B['voted26']), 'b': U(B['lvl26'] - B['voted26'])},
            so='A general fund line can be net of fee money; this one was, by design, for FY2026.',
            so_figures={'y': F(2026)},
            notes=[step('“the athletic director’s salary minus 20,000 offset from athletic revolving”', 'caption',
                        allow=('20,000',), cite=(hrefs[0], 'School Committee, 16 April 2025, video')),
                   step('An athletic secretary line of %s was then added to the general fund and spent %s.'
                        % (C.usd(B['sec26_budget']), C.usd(B['sec26_spent'])), 'measured',
                        {'a': U(B['sec26_budget']), 'b': U(B['sec26_spent'])})]),
        con('The fee fund’s regular pay is hourly: every FY2026 line fits %s an hour, %s in all.'
            % (usd2(fp['rate26']), C.usd(fp['slice26'])), ['slice', 'rate', 'sec26s'],
            {'a': U2(fp['rate26']), 'b': U(fp['slice26']), 'y': F(2026)},
            so='Our reading: it is the part-time athletic secretary, whom the FY26 book says the fund paid.',
            so_allow=('FY26',),
            notes=[step('FY2025’s lines fit %s an hour, and stop after %s.' % (usd2(fp['rate25']), long_date(fp['last25'])),
                        'measured', {'a': U2(fp['rate25']), 'y': F(2025)}, allow=D(long_date(fp['last25']))),
                   step('The FY26 proposal: “%s”.' % SUPT26_LINE, 'quote', allow=D('FY26', SUPT26_LINE)),
                   step('The journal names no one on a pay run.', 'gap', allow=D(WHO_CLOSES), closes=WHO_CLOSES)]),
        # WHAT THE JOURNAL SHOWS vs OUR READING (rule 7). TJ recalls a one-year assistant
        # principal / director split; the split on record is FY2026's, and this is FY2025 money.
        con('In FY2025 the Town moved %s of fee-fund pay onto the high school principal line.' % usd2(fp['hsp']),
            ['hsp', 'memo'], {'y': F(2025), 'a': U2(fp['hsp'])},
            so='Our arithmetic: it is %d hours at that year’s %s hourly rate, to a cent.'
               % (fp['hrs'], usd2(fp['rate25'])),
            so_figures={'h': figure(fp['hrs'], str(fp['hrs']), 'hours'), 'r': U2(fp['rate25'])},
            notes=[step('The entry took %s from the fee fund’s high school pay account; FY2025 pay runs charged '
                        '%s.' % (usd2(fp['out25']), usd2(fp['hs25'])), 'measured',
                        {'a': U2(fp['out25']), 'b': U2(fp['hs25']), 'y': F(2025)}),
                   step('Two readings fit: the hourly secretary, whose rate it matches, or the FY2026 assistant '
                        'principal and director split.', 'hypothesis', {'y': F(2026)})]),
    ]

    # ---- the timeline: who, and which line paid, FY2011-FY2027
    per = [('FY%02d' % (y % 100)) for y in YEARS]
    ix = {y: i for i, y in enumerate(YEARS)}
    who = []
    for name in PEOPLE:
        ys = sorted(held[name])
        who.append(TB.track(name, ['held' if y in held[name] else None for y in YEARS],
                            note=None))
    if sorted(sec) != sorted(SECRETARIES):
        fail('the athletic secretaries named are %s' % sorted(sec))
    secs = [TB.track(n, ['held' if y in sec[n] else None for y in YEARS]) for n in SECRETARIES]
    line_states = []
    for y in YEARS:
        if y < 2014:
            line_states.append(None)
        elif y <= 2017:
            line_states.append('absent')
        elif y in (2018,):
            line_states.append('half')
        elif y == 2026:
            line_states.append('net')
        elif y == 2027:
            line_states.append('half')
        else:
            line_states.append('full')
    fee_states = []
    for y in YEARS:
        # LOOKED FOR AND NOT FOUND is drawn as an absence (a dashed empty box), never a fill:
        # TJ, 28 October 2026, read a solid green here as "the AD is paid from fee funds".
        if 2014 <= y <= 2019:
            fee_states.append('absent')
        elif 2023 <= y <= 2026:
            fee_states.append('absent')
        elif 2020 <= y <= 2022:
            fee_states.append('totals')
        else:
            fee_states.append(None)
    sec_fee = ['secfee' if (2015 <= y <= 2019 or 2023 <= y <= 2026) else None for y in YEARS]
    tl = TB.timeline(
        'Who held the post, and which line paid it', per,
        [('Athletic director', who),
         ('How the director was paid', [
             TB.track('Town budget director line', line_states,
                      note=('FY14–FY17 print no director line; FY18 a half post; full-time from FY19; FY26 voted '
                            'net of a fee offset; FY27 a half post.', None, D('FY14 FY17 FY18 FY19 FY26 FY27')),
                      basis=('budget', 'District budget books; the school journal')),
             TB.track('Director pay in the fee fund', fee_states,
                      note=('Looked for, none found: no director on the fee side in FY14–FY17 actuals, FY18–FY19 '
                            'budgets or the FY23–FY26 journal. FY20–FY22: totals only.', None,
                            D('FY14 FY17 FY18 FY19 FY23 FY26 FY20 FY22')),
                      basis=('record', 'FY19 athletics document; annual reports; the school journal'))]),
         ('Athletic secretary', secs + [
             TB.track('Secretary pay in the fee fund', sec_fee,
                      note=('FY15–FY19 itemised by the district; FY23–FY26 our reading of hourly pay runs.',
                            None, D('FY15 FY19 FY23 FY26')),
                      basis=('reading', 'FY19 athletics document; our reading of the journal'))])],
        # Tones carry no verdict (rule 8): grey for a director line, green only where fee money
        # touches a post, a dashed empty box for looked-for-and-absent.
        [('held', 'Named in that year’s record', 'neutral'),
         ('full', 'Director line: full-time', 'muted'),
         ('half', 'Director line: a half post', 'muted', 'half'),
         ('net', 'Director line: voted net of a fee offset', 'good', 'half'),
         ('absent', 'Looked for: none found', 'muted', 'empty'),
         ('totals', 'Fee fund totals only: not itemised', 'muted', 'outline'),
         ('secfee', 'Secretary paid from the fee fund', 'good')],
        place='lead', marker=(ix[2025], ('The FY2026 offset is voted', None, ('FY2026',))),
        note=('Names are from the school rosters in each annual report and from agendas and minutes. The '
              'FY2025 report’s roster is written from a February 2026 vantage, and names the FY2026 director; '
              'it is not used for FY2025. Agendas name James Bunnell in June 2022 and Kevin Bigelow from August 2022.',
              None, D('FY2025 2026 FY2026 FY2025 2022 2022')))

    # ---- THE SIGNATURE: the director's pay as a LINE, every year a record carries (TJ, 28 October
    # 2026: "a line chart showing the salary for the AD over time"). One track per basis, never
    # mixed (rule 1): the general fund ACTUAL; the FY2026 LEVEL-SERVICE budget beside it, which
    # marks the fee offset; the FY2027 PROPOSAL; and the WAGES the Town printed, which are
    # calendar years and every fund. Calendar 2025 is left out of the wage line: two directors
    # were paid that year, one of them also an assistant principal.
    cy = list(range(2014, 2027))
    xs = list(range(2014, 2028))
    wage_line = {}
    for who_ in ('Peter McCauliff', 'James Bunnell'):
        for y, (amt, _, _) in wages[who_].items():
            if y in wage_line:
                fail('calendar %d: two directors on the wage line' % y)
            wage_line[y] = amt
    if any(y >= 2022 for y in wage_line):
        fail('the wage line now reaches calendar %d: decide how to draw it' % max(wage_line))
    lone = [y for y in sorted(wages['Kevin Bigelow']) + sorted(wages['Yanina Burns'])]
    if sorted(set(lone)) != [2025]:
        fail('wages for Bigelow and Burns are no longer calendar 2025 only: %s' % lone)
    mc_lo = min(mc[y][0] for y in mc if y <= 2017)
    mc_hi = max(mc[y][0] for y in mc if y <= 2017)
    line = TP.series('The athletic director’s pay, by year', [C.fy(y) for y in xs], [
        TP.track('Paid, general fund line (actual)', [float(gf[y][0]) if y in gf else None for y in xs],
                 'published'),
        TP.track('Level service, before the fee offset', [float(B['lvl26']) if y == 2026 else None for y in xs],
                 'published'),
        TP.track('Last draft, a proposal', [float(B['fy27_last']) if y == 2027 else None for y in xs],
                 'published'),
        TP.track('Wages the Town printed (calendar year)', [float(wage_line[y]) if y in wage_line else None
                                                            for y in xs], 'published')], '$', kind='line',
        note='Actuals: later budget books to FY2022, the journal from FY2023. Wages: annual reports, calendar '
             'years, every fund, at the year of that number; 2025 left out.',
        note_allow=D('FY2022 FY2023 2025'))
    line_block = TB.chart(line, place='lead', so=(
        '%s to %s the general fund director line shows $0 actual, while the Town printed the director’s '
        'calendar 2014 to 2017 wages at %s to %s: which account paid is not held.'
        % (C.fy(2014), C.fy(2017), C.usd(mc_lo), C.usd(mc_hi)),
        {'a': F(2014), 'b': F(2017), 'c': U(mc_lo), 'd': U(mc_hi)}, ('0', '2014', '2017')))

    # ---- the main chart: what the fee fund's high school pay account was charged, by kind.
    # A season lump is a pay-run line over REGULAR_MAX; the rest is the regular slice.
    fy_ = list(J.YEARS)
    chart = TP.series('The fee fund’s high school pay, by kind', [C.fy(y) for y in fy_], [
        TP.track('Season lumps', [float(fp['lumps'][y]) for y in fy_], 'published'),
        TP.track('Small regular lines', [float(fp['regular'][y]) for y in fy_], 'published')],
        '$', kind='bar', stacked=True, totals=True,
        note='As pay runs charged it. A lump is a line over %s. In FY2025 a memo moved all of it to the '
             'general fund.' % C.usd(REGULAR_MAX),
        note_figures={'a': U(REGULAR_MAX), 'y': F(2025)})

    # ---- tables
    gl = []
    for y in cy:
        v, basis, doc = gf[y]
        gl.append(dict(label=C.fy(y), cells=[usd2(v) if v else '$0', basis, doc]))
    gl.insert(gl.index(next(r for r in gl if r['label'] == 'FY2018')) + 1,
              dict(label='FY2018 budget', cells=[usd2(B['fy18_budget']), 'budget', 'fy19-proposed-athletics-budget.pdf']))
    gl.append(dict(label='FY2026 level service', cells=[usd2(B['lvl26']), 'budget, level service',
                                                        os.path.basename(BOOK26)]))
    gl.append(dict(label='FY2026 athletic secretary', cells=['%s budget, %s spent' % (usd2(B['sec26_budget']),
                                                             usd2(B['sec26_spent'])),
                                                             'actual, the school journal', 'munis-school-journal.csv']))
    gl.append(dict(label='FY2027 last draft', cells=[usd2(B['fy27_last']), 'proposal, 25 March 2026',
                                                     os.path.basename(FY27BOOK)]))
    t_line = dict(caption='The town budget director line, by year', views=[dict(
        key='line', label='By year', kinds=['ledger', 'stated', 'stated'],
        columns=['Amount', 'What it is', 'Document'], rows=gl,
        note='FY2023 to FY2026 tie to the Town’s period-13 report to the cent.')])
    wr = []
    for who_, ys in wages.items():
        for y in sorted(ys):
            amt, page, raw = ys[y]
            wr.append(dict(label='%s · calendar %d' % (who_, y),
                           cells=[usd2(amt), 'p%s' % page, raw[:60]]))
    t_wages = dict(caption='What each director earned, as the Town printed it', views=[dict(
        key='wages', label='Calendar years', kinds=['ledger', 'stated', 'stated'],
        columns=['Gross wages', 'Page', 'As printed'], rows=wr,
        note='Gross wages in each annual town report: calendar years, every fund and every post a person '
             'held. Years whose wage pages are not yet legible in our text are absent.')])

    sources = [
        dict(label='Lunenburg Public Schools — Proposed FY19 MSHS Athletic Budget (both sides, FY14–FY19)',
             href='/docs/district-budget/docs/fy19-proposed-athletics-budget.pdf'),
        dict(label='Lunenburg Public Schools — FY26 Superintendent’s proposed budget, 26 February 2025 '
                   '(page 66: the part-time secretary paid from the athletic revolving account)',
             href='/docs/district-budget/docs/fy26-superintendent-39-s-proposed-budget-2-26-25-updated-3-12-25.pdf'),
        dict(label='Lunenburg Public Schools — FY26 Town Manager’s target budget, approved 12 March 2025',
             href='/docs/district-budget/text/final-fy26-town-manager-39-s-target-budget.txt'),
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal line, '
                   'FY2023–FY2026)', href=J.PUBLIC['journal']),
        dict(label='Town of Lunenburg — annual town reports, school rosters and gross wages',
             href='/docs/data/gross-wages.csv'),
        dict(label='Lunenburg School Committee — minutes, 4 June 2025 and 29 July 2026',
             href='/docs/meetings/text/school-committee/2026-07-29-minutes-7930.txt'),
        dict(label='Lunenburg School Committee — video, 16 April 2025, at the offset', href=hrefs[0]),
        dict(label='Lunenburg Finance Committee — video, 20 March 2025, at the offset', href=hrefs[1]),
    ]

    page = TP.page(
        TID,
        'No record held pays the director from the fee fund. The FY2026 vote set his line %s below level service.'
        % C.usd(B['lvl26'] - B['voted26']),
        list(px.values()), concl, chart=chart, tables=[t_line, t_wages], sources=sources,
        blocks=[line_block, tl],
        finding_figures={'a': U(B['lvl26'] - B['voted26']), 'y': F(2026)})
    page['not_established'] = [
        'Which line paid the director from FY2011 to FY2017, when no budget prints a director line.',
        'Who was paid the fee fund’s regular hourly pay. The journal names no one on a pay run.',
        'Which post the $13,691.53 moved to the principal line in FY2025 paid.',
        'How the FY2027 half-time director is paid. The last draft held proposed $20,000.',
        'What each director earned in calendar 2016, 2018 and 2022 to 2024: those wage pages are not legible in our text.',
    ]
    if [TID] != MINE:
        fail('the registry gives this script %s; it builds %s' % (MINE, [TID]))
    return {TID: page}


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
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != text]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('athletic director: %d output current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
