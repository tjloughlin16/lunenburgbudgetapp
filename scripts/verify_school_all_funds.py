#!/usr/bin/env python3
"""VERIFY THE SCHOOL BUDGET, ALL FUNDS, by routes the generator does not take.

    python3 scripts/verify_school_all_funds.py     # exit 1 on any drift

The generator (build_school_all_funds.py) reads the journal through scripts/journal.py. This
reads the published payload (fy28/public/data/school-all-funds.json and the topic pages) and
recomputes every headline figure three other ways:

  1. RAW. The journal CSV with the csv module and Decimal: no journal.py loader, no rollup, the
     fund groups and function classes re-derived here from the fund number and the general
     fund's own budget lines. Every per-year total in the payload must match to the cent.
  2. THE TOWN'S SPREADSHEETS. The general fund's voted budget and spending per year from the
     period-13 `gf-school` spreadsheets (department 300) plus the journal's department 301,
     which the spreadsheets do not carry.
  3. OTHER PUBLISHERS. The circuit breaker, lunch, school choice and IDEA spending of FY2023
     against DESE's End of Year report, and the circuit breaker's FY2023 receipts and
     disbursements against the annual town report -- each to the dollar.

SPENT IS PAYMENTS PLUS WHAT WAS STILL OWED (TJ, 23 October 2026; scripts/journal.py, WHAT
"SPENT" MEANS). Re-derived here from the CSV's own `posts_to` column, not imported: a line is
spent if it posts to the report's actual or encumbrance column; the spreadsheet route adds the
spreadsheet's `encumbrances` to its `ytd_expended`. The ties to other publishers (route 3) and
the balances roll forward on payments alone, because those documents print actuals and a
balance is cash -- and that is checked too.

And THE PROSE: every figure a page states as a tile or in its finding is read back from the
page and compared with the recomputed value (rule 9: recomputed, not re-read).
"""
import csv
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'school-all-funds-model.json')
TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
YEARS = (2023, 2024, 2025, 2026)
SPENT = ('actual', 'encumbrance')     # payments plus what was still owed
bad = []


def check(what, ours, theirs, tol=Decimal('0.01')):
    if abs(Decimal(str(ours)) - Decimal(str(theirs))) > tol:
        bad.append('%s: payload %s, recomputed %s' % (what, ours, theirs))


def usd(x):
    n = round(float(x))
    return ('-$%s' if n < 0 else '$%s') % format(abs(n), ',d')


def group(fund):
    if fund == '0100':
        return 'General fund'
    if fund == '2640':
        return 'Circuit breaker'
    if fund[:2] in ('13', '15', '16') or fund == '2200':
        return 'Revolving funds and lunch'
    if fund[:2] in ('24', '25', '26', '27', '28', '29', '42', '46'):
        return 'Grants'
    return 'Capital and other'


def main():
    pay = json.load(open(PAY, encoding='utf-8'))
    rows = list(csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')))
    for r in rows:
        r['a'] = Decimal(r['amount'])
        r['fy'] = int(r['fiscal_year'])
        r['code'] = r['account'].split('-')[3]
        r['exp'] = r['object'].startswith('5')
        r['rev'] = r['object'].startswith('4')

    # ---- route 1: raw
    voted = defaultdict(Decimal)
    spent = defaultdict(Decimal)
    rec = defaultdict(Decimal)
    gfcodes = set()
    owed = defaultdict(Decimal)
    for r in rows:
        g = group(r['fund'])
        if r['exp'] and r['posts_to'] in SPENT:
            spent[(r['fy'], g)] += r['a']
        if r['exp'] and r['posts_to'] == 'encumbrance':
            owed[(r['fy'], g)] += r['a']
        if r['exp'] and g == 'General fund' and r['posts_to'] == 'original_budget':
            voted[r['fy']] += r['a']
        if r['exp'] and g == 'General fund' and r['posts_to'] in ('original_budget', 'transfer') and r['a']:
            gfcodes.add(r['code'])
        if r['rev'] and r['posts_to'] == 'actual':
            rec[(r['fy'], g)] -= r['a']
    lines = {c for c in gfcodes if not c.endswith('000')}

    def unattributed(code):
        if code == '0000' or code.endswith('000'):
            return True
        return (code not in lines and code.endswith('00')
                and any(c[:2] == code[:2] and c != code for c in lines))
    unat = defaultdict(Decimal)
    for r in rows:
        if r['exp'] and r['posts_to'] in SPENT and r['fund'] != '0100' and unattributed(r['code']):
            unat[r['fy']] += r['a']
    for y in YEARS:
        k = str(y)
        check('voted %d' % y, pay['gf_voted'][k], voted[y])
        check('general fund spent %d' % y, pay['gf_spent'][k], spent[(y, 'General fund')])
        allf = sum(v for (yy, _), v in spent.items() if yy == y)
        check('every fund spent %d' % y, pay['all_spent'][k], allf)
        check('outside spent %d' % y, pay['outside_spent'][k], allf - spent[(y, 'General fund')])
        check('unattributed %d' % y, pay['unattributed'][k], unat[y])
        for g, v in pay['by_group'][k].items():
            check('%s %d' % (g, y), v, spent[(y, g)])
        for g, v in pay['receipts'][k].items():
            check('receipts %s %d' % (g, y), v, rec[(y, g)])
        for g, v in pay['owed'][k].items():
            check('owed %s %d' % (g, y), v, owed[(y, g)])
            if y != YEARS[-1] and owed[(y, g)]:
                bad.append('%s %d is closed and still owes %s; the pages say only the open year does'
                           % (g, y, owed[(y, g)]))

    # ---- route 2: the Town's period-13 spreadsheets, general fund
    ytd = [r for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'), encoding='utf-8'))
           if r['report'] == 'gf-school']
    for y in YEARS:
        d301 = [r for r in rows if r['fy'] == y and r['fund'] == '0100' and r['account'].split('-')[2] == '301']
        sv = sum(Decimal(str(round(float(r['original_approp'] or 0), 2))) for r in ytd if int(r['fiscal_year']) == y)
        ss = sum(Decimal(str(round(float(r['ytd_expended'] or 0), 2)))
                 + Decimal(str(round(float(r['encumbrances'] or 0), 2)))
                 for r in ytd if int(r['fiscal_year']) == y)
        sv += sum(r['a'] for r in d301 if r['posts_to'] == 'original_budget')
        ss += sum(r['a'] for r in d301 if r['posts_to'] in SPENT)
        check('voted %d, spreadsheet route' % y, pay['gf_voted'][str(y)], sv)
        check('general fund spent %d, spreadsheet route' % y, pay['gf_spent'][str(y)], ss)

    # ---- route 3: DESE's End of Year report and the annual town report, FY2023
    eo = {r['column']: Decimal(r['amount']) for r in csv.DictReader(open(os.path.join(DATA, 'eoyr-schedule1.csv'), encoding='utf-8'))
          if r['fiscal_year'] == 'FY2023' and r['line'] == '3080'}
    fsp = defaultdict(Decimal)
    for r in rows:
        if r['fy'] == 2023 and r['exp'] and r['posts_to'] == 'actual':
            fsp[r['fund']] += r['a']
            if '#240' in r['fund_name'] or '# 240' in r['fund_name'] or r['fund_name'].rstrip().endswith('240 GRANT'):
                fsp['idea'] += r['a']
    for col, key in (('Revolving and Special Funds Circuit Breaker', '2640'), ('School Nutrition', '2200'),
                     ('Sch Choice & Other Day Tuition', '1308'), ('IDEA FC 240', 'idea')):
        check('EOYR FY2023 %s' % col, eo[col], round(fsp[key]), Decimal('0.5'))
    ar = {r['fund']: r for r in csv.DictReader(open(os.path.join(DATA, 'special-revenue-read.csv'), encoding='utf-8'))
          if r['fy'] == '2023' and r['group'] == 'SCHOOL DEPARTMENT'}
    cb = ar['50/50 Grant Sped Tuitions']
    check('circuit breaker FY2023 disbursements, town report', Decimal(cb['disbursements']), fsp['2640'])
    check('circuit breaker FY2023 receipts, town report', Decimal(cb['receipts']), rec[(2023, 'Circuit breaker')])
    # the balances roll forward on CASH: the town report's FY2023 balance, plus receipts, less
    # payments (actual alone) in FY2024-FY2026 -- an order still owed has not left the fund
    frec, fcash = defaultdict(Decimal), defaultdict(Decimal)
    for r in rows:
        if r['rev'] and r['posts_to'] == 'actual':
            frec[(r['fy'], r['fund'])] -= r['a']
        if r['exp'] and r['posts_to'] == 'actual':
            fcash[(r['fy'], r['fund'])] += r['a']
    for c in pay['carry']:
        want = Decimal(str(c['carried_fy2023'])) + sum(frec[(y, c['fund'])] - fcash[(y, c['fund'])]
                                                     for y in YEARS[1:])
        check('balance of fund %s, end of FY2026, on cash' % c['fund'], c['end'], want)

    # ---- the prose: tiles and findings read back off the pages
    hub = json.load(open(os.path.join(TOPICS, 'school-all-funds.json'), encoding='utf-8'))
    tiles = {f['id']: f['value']['text'] for t in hub['ladder']['tiers'] for f in t['facts'] if f['value']}
    a26 = sum(v for (yy, _), v in spent.items() if yy == 2026)
    if tiles['h-v'] != usd(voted[2026]):
        bad.append('hub tile h-v reads %s; recomputed %s' % (tiles['h-v'], usd(voted[2026])))
    if tiles['h-a'] != usd(a26):
        bad.append('hub tile h-a reads %s; recomputed %s' % (tiles['h-a'], usd(a26)))
    if tiles['h-g'] != usd(spent[(2026, 'General fund')]):
        bad.append('hub tile h-g reads %s; recomputed %s' % (tiles['h-g'], usd(spent[(2026, 'General fund')])))
    o26 = sum(v for (yy, _), v in owed.items() if yy == 2026)
    if tiles['h-w'] != usd(o26):
        bad.append('hub tile h-w reads %s; recomputed %s' % (tiles['h-w'], usd(o26)))
    if tiles['h-u'] != usd(unat[2026]):
        bad.append('hub tile h-u reads %s; recomputed %s' % (tiles['h-u'], usd(unat[2026])))
    if usd(a26 - voted[2026]) not in hub['answer']['text']:
        bad.append('hub answer does not state every fund less the vote, %s' % usd(a26 - voted[2026]))
    bl = json.load(open(os.path.join(TOPICS, 'budget-lines-all-funds.json'), encoding='utf-8'))
    out26 = a26 - spent[(2026, 'General fund')]
    for want in (usd(out26), usd(unat[2026])):
        if want not in bl['finding']['text']:
            bad.append('budget-lines finding does not state %s: %r' % (want, bl['finding']['text']))
    # the IDEA grants, grant by grant, from raw: what share of each grant sat on a voted line
    idea = defaultdict(lambda: defaultdict(Decimal))
    for r in rows:
        if r['exp'] and r['posts_to'] in SPENT and group(r['fund']) == 'Grants' and '240' in r['fund_name'] \
                and r['fund_name'].split()[0].upper().startswith("FY"):
            k = 'line' if r['code'] in lines else 'off'
            idea[r['fund']][k] += r['a']
    for gy, d in pay['idea_by_grant'].items():
        check('IDEA FY%s grant on a voted line' % gy, d['line'], idea[d['fund']]['line'])
        check('IDEA FY%s grant spent' % gy, d['total'], idea[d['fund']]['line'] + idea[d['fund']]['off'])
    # special education (H1): spent includes the year-end encumbrance, and on that basis the
    # general fund came in under its vote in every year but one -- the sentence says so
    over = [y for y, d in pay['sped'].items() if not d['gf_spent'] < d['voted']]
    if len(over) != 1:
        bad.append('sped: %d years with the general fund over its vote; the page says one' % len(over))

    if bad:
        print('verify_school_all_funds: %d problems' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    print('verify_school_all_funds: every figure recomputed by three routes, and the prose agrees')
    return 0


if __name__ == '__main__':
    sys.exit(main())
