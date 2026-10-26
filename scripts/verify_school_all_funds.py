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

    # THE CIRCUIT BREAKER NETTING (26 October 2026). The vote is net of the expected circuit
    # breaker; FY2025 was loaded gross and netted on 1 July 2024 by one one-sided entry, which is
    # part of the vote (build_sped_costs.net_fy2025, journal.NETTING). Named here rather than
    # imported, so this route stays independent; it must exist, alone, with no other side.
    NET_J = (2025, '2025/01/000564')
    net_rows = [r for r in rows if (r['fy'], r['journal']) == NET_J]
    if len(net_rows) != 1 or net_rows[0]['description'].strip() != 'ADJ FY25 BUDGET':
        raise SystemExit('verify_school_all_funds: the FY2025 netting entry is not one line as read')
    is_net = lambda r: (r['fy'], r['journal']) == NET_J

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
        if r['exp'] and g == 'General fund' and (r['posts_to'] == 'original_budget' or is_net(r)):
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
        sv += sum(r['a'] for r in rows if is_net(r) and r['fy'] == y)
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

    # special education grants (sped-grants): each stream from raw, by the '#code' in the fund's
    # own name and fund 2640, every expense line spent; the circuit breaker's receipts; DESE's
    # allocations from its CSV; and the finding and conclusions read back off the page.
    import re
    sgp = pay['sped_grants']
    codes = [k for k in sgp['streams']['2023'] if k != 'CB']
    sgr = defaultdict(Decimal)
    for r in rows:
        if not (r['exp'] and r['posts_to'] in SPENT):
            continue
        mm = re.search(r'#\s*(\d{3})\b', r['fund_name'])
        k = 'CB' if r['fund'] == '2640' else (mm.group(1) if mm and group(r['fund']) == 'Grants' else None)
        if k == 'CB' or k in codes:
            sgr[(r['fy'], k)] += r['a']
    for y in YEARS:
        for k, v in sgp['streams'][str(y)].items():
            check('sped-grants %s %d' % (k, y), v, sgr[(y, k)])
        check('sped-grants total %d' % y, sgp['total'][str(y)], sum(v for (yy, _), v in sgr.items() if yy == y))
        check('sped-grants total %d is sped-all-funds other funds' % y, sgp['total'][str(y)],
              pay['sped'][str(y)]['outside'])
        check('circuit breaker received %d' % y, sgp['cb_received'][str(y)], rec[(y, 'Circuit breaker')])
    al = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['district_code'] == '0162' and r['fund_code'].lstrip('0') in codes:
            al['%s-%s' % (r['fund_code'].lstrip('0'), r['fy'])] = Decimal(r['amount'])
    if set(al) != set(sgp['allocations']):
        bad.append('sped-grants allocations: payload holds %s, DESE CSV %s' % (sorted(sgp['allocations']), sorted(al)))
    for k, v in sgp['allocations'].items():
        check('sped-grants allocation %s' % k, v, al.get(k, 0))
    sg = json.load(open(os.path.join(TOPICS, 'sped-grants.json'), encoding='utf-8'))
    tot = lambda y: sum(v for (yy, _), v in sgr.items() if yy == y)
    for want in (usd(tot(2023)), usd(tot(2026))):
        if want not in sg['finding']['text']:
            bad.append('sped-grants finding does not state %s: %r' % (want, sg['finding']['text']))
    ctext = ' '.join(c['text'] + ' ' + c.get('so', {}).get('text', '') for c in sg['conclusions'])
    lag = Decimal(str(sgp['cb_paid']['2024'])) - rec[(2024, 'Circuit breaker')]
    for want in (usd(sgp['cb_paid']['2026']), usd(rec[(2026, 'Circuit breaker')]), usd(sgr[(2026, 'CB')]),
                 usd(sgr[(2023, '252')] + sgr[(2023, '264')]), usd(lag), usd(al['240-2025']),
                 usd(al['240-2027']), usd(al['262-2026'])):
        if want not in ctext:
            bad.append('sped-grants conclusions do not state %s' % want)
    if any(sgr[(y, c)] for y in YEARS[1:] for c in ('252', '264')):
        bad.append('sped-grants: the pandemic IDEA grants spent after FY2023; the page says they did not')

    # school grants and aid (school-money-in): Chapter 70 against the cherry sheet (another
    # publisher's printing of the same aid), DESE's allocations from its CSV with Decimal, grant
    # and ESSER spending from raw, and the finding and conclusions read back off the page.
    mi = pay['money_in']
    cs = {int(r['fy']): Decimal(r['amount']) for r in csv.DictReader(open(os.path.join(DATA, 'dls-cherry-sheet.csv'), encoding='utf-8'))
          if r['name'] == 'Lunenburg' and r['line'] == 'Chapter 70' and r['flow'] == 'Receipts'}
    both = [y for y in map(int, mi['chapter70_dese']) if y in cs]
    if len(both) < 4:
        bad.append('school-money-in: the cherry sheet overlaps DESE’s Chapter 70 in only %d years' % len(both))
    for y in both:
        check('Chapter 70 %d, cherry sheet' % y, mi['chapter70_dese'][str(y)], cs[y], Decimal('0.5'))
    for y, v in mi['chapter70_next'].items():
        check('Chapter 70 %s, cherry sheet' % y, v, cs[int(y)])
    al2 = defaultdict(Decimal)
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['district_code'] == '0162':
            k = r['fund_code'].lstrip('0')
            if k in mi['yearly_codes']:
                al2[('yearly', int(r['fy']))] += Decimal(r['amount'])
            if k in mi['pandemic_codes']:
                al2[('pandemic', int(r['fy']))] += Decimal(r['amount'])
    for y, v in mi['yearly_allocated'].items():
        check('yearly grants allocated %s' % y, v, al2[('yearly', int(y))])
    for y, v in mi['pandemic_allocated'].items():
        check('pandemic grants allocated %s' % y, v, al2[('pandemic', int(y))])
    gsp, esp = defaultdict(Decimal), defaultdict(Decimal)
    for r in rows:
        if r['exp'] and r['posts_to'] in SPENT and group(r['fund']) == 'Grants':
            gsp[r['fy']] += r['a']
            mm = re.search(r'#\s*(\d{3})\b', r['fund_name']) or re.match(r"\s*FY\s*'?\d\d\s+(\d{3})\b", r['fund_name'])
            if mm and mm.group(1) in ('115', '119'):
                esp[r['fy']] += r['a']
    for y in YEARS:
        check('grants spent %d' % y, mi['grants_spent'][str(y)], gsp[y])
        check('ESSER spent %d' % y, mi['esser_spent'][str(y)], esp[y])
        check('grants by name add up, %d' % y, sum(Decimal(str(v)) for v in mi['by_grant'][str(y)].values()), gsp[y])
    smi = json.load(open(os.path.join(TOPICS, 'school-money-in.json'), encoding='utf-8'))
    pct = lambda a, b: '%.1f%%' % abs(round(float(100 * (b - a) / a), 1))
    f0 = mi['formula_from']
    c70 = {int(y): Decimal(str(v)) for y, v in mi['chapter70_dese'].items()}
    for want in (usd(c70[2025]), usd(gsp[2025])):
        if want not in smi['finding']['text']:
            bad.append('school-money-in finding does not state %s: %r' % (want, smi['finding']['text']))
    ctext = ' '.join(c['text'] for c in smi['conclusions'])
    for want in (pct(c70[f0], c70[2026]), pct(al2[('yearly', f0)], al2[('yearly', 2026)]),
                 usd(gsp[2023]), usd(gsp[2026]), usd(esp[2023])):
        if want not in ctext:
            bad.append('school-money-in conclusions do not state %s' % want)
    if not (c70[2026] > c70[f0] and al2[('yearly', 2026)] < al2[('yearly', f0)] and esp[2026] == 0):
        bad.append('school-money-in: the conclusions’ directions no longer hold')

    if bad:
        print('verify_school_all_funds: %d problems' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    print('verify_school_all_funds: every figure recomputed by three routes, and the prose agrees')
    return 0


if __name__ == '__main__':
    sys.exit(main())
