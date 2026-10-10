#!/usr/bin/env python3
"""Recompute every headline figure in /analysis/transportation by a DIFFERENT ROUTE.

    python3 scripts/verify_transportation.py

The generator reads the ledgers from their CSV extracts, classifies accounts by function and
object code, sums in float, and reads the bid form's rates as a declared table that it tests
against the scan. This takes each figure another way:

  * the MUNIS years from the DATABASE (`munis_school_ytd`), selected by SQL on the account
    string, summed with Decimal;
  * the Finance Committee years from `gl-history.csv` selected by ORG AND OBJECT rather than
    by function code;
  * the contract's regular-route prices from the SUBTOTALS the bid form prints, read out of
    the scan's text layer with a regular expression, rather than from rate x buses x days;
  * the athletics totals from the database table, not the CSV;
  * the budget book from `lps_budget_lines` by row number;
  * every quotation re-read from the document its citation points at;
  * the audit figures the summary leads with (10 October 2026) from the MUNIS extract CSV
    itself, keyed on the ACCOUNT STRING and summed in Decimal: each overrun from the
    `available_budget` column MUNIS prints rather than by subtraction, and the two school
    funds by account prefix rather than by the `fund` column;
  * the model's transport rate from `model/finance.py` itself, not from model.json.

It asserts the NUMBER, never the prose around it: every figure a conclusion registers is
recomputed and compared to the value the payload carries, and every claim and supporting
line is looked for in the published markdown.
"""
import csv
import json
import os
import re
import sqlite3
import sys
from decimal import Decimal as D, ROUND_HALF_EVEN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'transportation.json')
MD = os.path.join(ROOT, 'sources', 'analyses', 'transportation.md')
BID = os.path.join(ROOT, 'sources', 'contracts', 'txt', 'dee-bus-bid-proposal-rates-fy26-fy30.txt')
OVERVIEW = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                        'school-department-fy26-budget-overview.txt')
LEA = '01620000'

# By ORG and OBJECT -- the generator keys on function and object. Two keys to one account.
ORG_OBJ = {
    'regular': [('S3991692', '535025')],
    'sped': [('S3991692', '535026')],
    'athletic': [('S3066672', '535016')],
    'band': [('S0055632', '535016'), ('S0066632', '535016')],
}
BOOK_ROWS = {'regular': [167], 'sped': [168], 'athletic': [170], 'band': [143, 144]}

bad = []


def check(name, got, want):
    if got != want:
        bad.append('%s: recomputed %r, payload says %r' % (name, got, want))


def r0(x):
    return int(D(str(x)).quantize(D('1'), rounding=ROUND_HALF_EVEN))


def r2(x):
    return D(str(x)).quantize(D('0.01'), rounding=ROUND_HALF_EVEN)


def p1(a, b):
    return float((D(a) * 100 / D(b)).quantize(D('0.1'), rounding=ROUND_HALF_EVEN))


def money(s):
    return D(re.sub(r'[^\d.]', '', s))


def main():
    pay = json.load(open(PAY, encoding='utf-8'))
    md = open(MD, encoding='utf-8').read()
    flat = re.sub(r'\s+', ' ', md)
    db = sqlite3.connect(os.path.join(DATA, 'lunenburg.db'))
    cards = {c['id']: c for c in pay['conclusions']}
    fig = lambda cid, k: cards[cid]['figures'][k]['value']

    # ---- the ledger, two routes ------------------------------------------------------
    led = {}
    for cat, pairs in ORG_OBJ.items():
        for org, obj in pairs:
            for fy, o, ex, en, rv in db.execute(
                    'SELECT fiscal_year, original_approp, ytd_expended, encumbrances, '
                    'revised_budget FROM munis_school_ytd WHERE period=13 AND fund=? AND '
                    'org=? AND obj=? AND type=?', ('0100', org, obj, 'E')):
                a = led.setdefault((int(fy), cat), [D(0), D(0), D(0)])
                a[0] += D(str(o))
                a[1] += D(str(ex)) + D(str(en))
                a[2] += D(str(rv))
    for r in csv.DictReader(open(os.path.join(DATA, 'gl-history.csv'), encoding='utf-8')):
        if r['sheet'] != 'general_fund' or r['actual_is_partial'] == 'true':
            continue
        fy = int(r['fiscal_year'])
        if fy >= 2023:
            continue
        for cat, pairs in ORG_OBJ.items():
            if (r['org'], r['object']) in pairs:
                a = led.setdefault((fy, cat), [D(0), D(0), D(0)])
                a[0] += D(r['original'])
                a[1] += D(r['actual'])
                a[2] += D(r['revised'])
    spent = lambda fy, c: r0(led[(fy, c)][1])
    budget = lambda fy, c: r0(led[(fy, c)][0])
    cats = list(ORG_OBJ)

    # every year of the payload's table
    for row in pay['by_year']:
        if row['fy'] > 2026:
            continue
        for c in cats:
            check('FY%d %s budget' % (row['fy'], c), budget(row['fy'], c), row[c + '_budget'])
            check('FY%d %s spent' % (row['fy'], c), spent(row['fy'], c), row[c + '_spent'])

    all26 = sum(spent(2026, c) for c in cats)
    allb26 = sum(budget(2026, c) for c in cats)
    # ---- the MUNIS year-end CSV, read directly in Decimal ---------------------------
    # A THIRD route for the audit figures: the extract itself, keyed on the ACCOUNT STRING
    # (fund prefix, org and object), summed in Decimal -- the generator reads the same file
    # through its function-code classifier and sums in float. For the overruns it uses the
    # column MUNIS itself prints, `available_budget`, rather than subtracting anything.
    mrows = [r for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-ytd.csv'),
                                            encoding='utf-8')) if r['period'] == '13']
    dz = lambda x: D(x.strip() or '0')

    def gl_row(fy, org, obj):
        hit = [r for r in mrows if r['fiscal_year'] == str(fy) and r['account'].startswith('0100-')
               and r['org'] == org and r['obj'] == obj]
        if len(hit) != 1:
            bad.append('FY%d %s/%s: %d rows in the MUNIS extract, not one' % (fy, org, obj, len(hit)))
            return None
        return hit[0]

    # 1. Special education, FY2026: spent past revised, from MUNIS's own printed balance.
    c1 = 'sped-buses-over-budget'
    s26 = gl_row(2026, 'S3991692', '535026')
    over26 = -dz(s26['available_budget'])
    check(c1 + ' over (MUNIS available_budget)', r0(over26), fig(c1, 'over'))
    check(c1 + ' voted', r0(dz(s26['original_approp'])), fig(c1, 'voted'))
    check(c1 + ' revised', r0(dz(s26['revised_budget'])), fig(c1, 'revised'))
    check(c1 + ' paid', r0(dz(s26['ytd_expended'])), fig(c1, 'paid'))
    check(c1 + ' committed', r0(dz(s26['encumbrances'])), fig(c1, 'committed'))
    sp26 = dz(s26['ytd_expended']) + dz(s26['encumbrances'])
    check(c1 + ' spent', r0(sp26), fig(c1, 'spent'))
    if abs(dz(s26['transfers_adjustments'])) > D('0.01') * over26:
        bad.append('a transfer now covers part of the FY2026 special education overrun')
    b27s = [D(str(v)) for v, in db.execute('SELECT fy27_balanced FROM lps_budget_lines WHERE row=168')][0]
    check(c1 + ' FY2027 budget', r0(b27s), fig(c1, 'b27'))
    check(c1 + ' FY2027 above FY2026 spent', r0(b27s - sp26), fig(c1, 'margin'))
    check(c1 + ' one-year rise', p1(spent(2026, 'sped') - spent(2025, 'sped'), spent(2025, 'sped')),
          fig(c1, 'rise'))
    check(c1 + ' FY2025 spent', spent(2025, 'sped'), fig(c1, 'spent25'))

    # FY2024, both school-day lines past revised -- the evidence section and the payload.
    fy24 = {o: -dz(gl_row(2024, 'S3991692', o)['available_budget']) for o in ('535025', '535026')}
    od = {(x['fy'], x['cat']): x['over'] for x in pay['audit']['overdrawn']}
    check('FY2024 regular past revised', r0(fy24['535025']), od.get((2024, 'regular')))
    check('FY2024 sped past revised', r0(fy24['535026']), od.get((2024, 'sped')))
    if '%s past their revised budgets together' % ('$' + format(r0(fy24['535025'] + fy24['535026']), ',d')) not in flat:
        bad.append('the FY2024 combined overrun in the markdown does not equal the MUNIS balances')

    # 2. The special education budget against its spending, FY2016-FY2023, via the DB+GL route.
    c2 = 'sped-budget-trailed-spending'
    under = {fy: budget(fy, 'sped') - spent(fy, 'sped') for fy in range(2016, 2024)}
    if min(under.values()) <= 0:
        bad.append('special education transportation was not under budget every year FY2016-FY2023')
    start = min(fy for fy, v in under.items() if v > 100000)
    cut = min(range(2016, 2024), key=lambda fy: budget(fy, 'sped'))
    check(c2 + ' window start', start, fig(c2, 'start'))
    check(c2 + ' window end', cut, fig(c2, 'cut'))
    check(c2 + ' window sum', sum(under[f] for f in range(start, cut + 1)), fig(c2, 'sum'))
    check(c2 + ' pre-closure', sum(under[f] for f in range(start, 2020)), fig(c2, 'pre'))
    check(c2 + ' smallest gap', min(under.values()), fig(c2, 'lo'))
    check(c2 + ' largest gap', max(under.values()), fig(c2, 'hi'))
    check(c2 + ' cut budget', budget(cut, 'sped'), fig(c2, 'cutb'))
    check(c2 + ' lowest since', max(fy for fy in range(2010, cut) if budget(fy, 'sped') <= budget(cut, 'sped')),
          fig(c2, 'since'))
    for fy in (2024, 2026):
        check(c2 + ' over voted FY%d' % fy, spent(fy, 'sped') - budget(fy, 'sped'), fig(c2, 'o%d' % fy))

    # 3. FY2027 school day against the total: the budget book by ROW NUMBER.
    c3 = 'school-day-rise-offset'
    bk = {}
    for row, a, b_ in db.execute('SELECT row, fy26_final, fy27_balanced FROM lps_budget_lines '
                                 'WHERE row IN (143, 144, 167, 168, 170)'):
        bk[int(row)] = (D(str(a)), D(str(b_)))
    sd26 = bk[167][0] + bk[168][0]
    sd27 = bk[167][1] + bk[168][1]
    al26 = sum(v[0] for v in bk.values())
    al27 = sum(v[1] for v in bk.values())
    check(c3 + ' school-day FY2026', r0(sd26), fig(c3, 'sd26'))
    check(c3 + ' school-day FY2027', r0(sd27), fig(c3, 'sd27'))
    check(c3 + ' school-day rise %', p1(sd27 - sd26, sd26), fig(c3, 'sd'))
    check(c3 + ' total FY2026', r0(al26), fig(c3, 'all26'))
    check(c3 + ' total rise %', p1(al27 - al26, al26), fig(c3, 'all'))
    check(c3 + ' athletic cut', r0(bk[170][0] - bk[170][1]), fig(c3, 'cut'))
    check(c3 + ' offset share', p1(bk[170][0] - bk[170][1], sd27 - sd26), fig(c3, 'off'))

    # ---- the contract, from the subtotals the form prints ---------------------------
    lines = open(BID, encoding='utf-8').read().split('\n')
    at = lambda n: lines[n - 1]
    printed = {
        2026: (money(re.search(r'\$(\d+)\.0000', at(26)).group(1)),
               money(re.search(r'([\d,]+) 00', at(29)).group(1))),
        2028: (money(re.search(r'\$([\d,]+)', at(193)).group(1)),
               money(re.search(r'\$([\d,]+)', at(195)).group(1))),
        2029: (money(re.search(r'\$ ([\d,]+)\.', at(306)).group(1)),
               money(re.search(r's ([\d,]+)\.', at(310)).group(1))),
        2030: (money(re.search(r'\$([\d,]+)\.00', at(392)).group(1)),
               money(re.search(r'\$([\d,]+)\.00', at(395)).group(1))),
    }
    reg = {fy: a + b for fy, (a, b) in printed.items()}
    # FY2027's 83-passenger subtotal is illegible in the text layer (`530240`); its
    # 77-passenger subtotal and the 83-passenger rate are legible, so it is rebuilt from them.
    reg[2027] = money(re.search(r'\$ ([\d,]+)\.00', at(113)).group(1)) + \
        3 * money(re.search(r'(\d+)\*', at(110)).group(1)) * 180
    b27 = [r0(v) for v, in db.execute('SELECT fy27_balanced FROM lps_budget_lines WHERE row=167')]
    if b27[0] != r0(reg[2027]):
        bad.append('the FY2027 budget no longer equals the contract’s second-year price')
    gt = money(re.search(r'([\d,]+\.\d\d)', at(268)).group(1))
    if gt != D('6086125.00'):
        bad.append('the Grand Total no longer reads 6,086,125.00 in the text layer')
    b25 = [r0(v) for v, in db.execute('SELECT fy25_budget FROM lps_budget_lines WHERE row=167')][0]
    ov = re.search(r'7\.6% line increase = \$([\d,]+)', open(OVERVIEW, encoding='utf-8').read())
    if not ov or money(ov.group(1)) != reg[2026] - b25:
        bad.append('the overview’s 7.6% dollar figure no longer equals the contract price less '
                   'the FY2025 budget')

    # 4. The bus fee's first year: the general fund, and fund 1308, from the CSV.
    c4 = 'bus-fee-and-the-bill'
    r26 = gl_row(2026, 'S3991692', '535025')
    check(c4 + ' voted', r0(dz(r26['original_approp'])), fig(c4, 'voted'))
    check(c4 + ' transfer', r0(dz(r26['transfers_adjustments'])), fig(c4, 'xfer'))
    paid = dz(r26['ytd_expended']) + dz(r26['encumbrances'])
    check(c4 + ' paid', r0(paid), fig(c4, 'paid'))
    check(c4 + ' contract price', r0(reg[2026]), fig(c4, 'price'))
    if paid != reg[2026]:
        bad.append('FY2026 regular routes no longer paid exactly the contract price')
    check(c4 + ' netted', r0(reg[2026] - dz(r26['original_approp'])), fig(c4, 'net'))
    f8 = [r for r in mrows if r['account'].startswith('1308-')]
    fee = {}
    for r in f8:
        if r['account'].endswith('-437601'):
            fee[int(r['fiscal_year'])] = -dz(r['ytd_expended'])
    check(c4 + ' FY2025 receipts', float(r2(fee[2025])), fig(c4, 'f25'))
    check(c4 + ' FY2026 receipts', float(r2(fee[2026])), fig(c4, 'f26'))
    check(c4 + ' FY2026 receipts, as the card registers it', float(r2(fee[2026])), fig(c4, 'rec'))
    check(c4 + ' two years', float(r2(fee[2025] + fee[2026])), fig(c4, 'both'))
    if fee[2023] or fee[2024]:
        bad.append('the bus fee account took in money before FY2025, which the page denies')
    t8 = [r['account'] for r in f8 if r['type'] == 'E' and (r['account'].split('-')[3] == '3300'
          or r['account'].split('-')[8] in ('535016', '535025', '535026')
          or re.search(r'TRANSP|\bBUS\b', r['description'], re.I))]
    if t8:
        bad.append('fund 1308 carries a transportation expense account: %s' % t8)
    x8 = [dz(r['ytd_expended']) + dz(r['encumbrances']) for r in f8
          if r['account'].split('-')[8] == '570014']
    if len(x8) != 4 or any(x8):
        bad.append('fund 1308’s transfer to the general fund is not zero in all four years: %s' % x8)

    # 5. The FY2027 restoration: from the quotation, and the FY2024 share from the database.
    c5 = 'restored-buses-on-the-fee-fund'
    said = {q['key']: q for q in pay['said']}
    nums = [money(x) for x in re.findall(r'\$[\d,]+', said['restore']['quote'])]
    check(c5 + ' estimate', r0(nums[0]), fig(c5, 'est'))
    check(c5 + ' town', r0(nums[2]), fig(c5, 'town'))
    check(c5 + ' fund', r0(nums[3]), fig(c5, 'fund'))
    check(c5 + ' fund share', p1(nums[3], nums[1]), fig(c5, 'pct'))
    check(c5 + ' town share', p1(nums[2], nums[1]), fig(c5, 't27'))
    sheet = {fy: r2(t) for fy, t in db.execute(
        "SELECT fy, SUM(value) FROM athletics_by_sport WHERE metric='Transportation' "
        "AND is_numeric=1 GROUP BY fy")}
    check(c5 + ' FY2024 sheet', float(sheet[2024]), fig(c5, 'sheet24'))
    check(c5 + ' FY2024 line', budget(2024, 'athletic'), fig(c5, 'line24'))
    check(c5 + ' FY2024 town share', p1(budget(2024, 'athletic'), sheet[2024]), fig(c5, 't24'))
    if 'athletic revolving fund' not in said['restore-vote']['quote']:
        bad.append('the restoration vote no longer names the athletic revolving fund')

    # 6. The athletic fee fund, keyed on the ACCOUNT PREFIX, in Decimal.
    c6 = 'fee-fund-receipts-against-spending'
    f1 = {}
    for r in mrows:
        if not r['account'].startswith('1301-'):
            continue
        d = f1.setdefault(int(r['fiscal_year']), [D(0), D(0)])
        if r['account'].split('-')[7] == '4':          # revenue: the account's 8th segment
            d[0] -= dz(r['ytd_expended'])
        else:
            d[1] += dz(r['ytd_expended']) + dz(r['encumbrances'])
    for fy in (2023, 2024, 2025, 2026):
        check(c6 + ' FY%d receipts' % fy, float(r2(f1[fy][0])), fig(c6, 'in%d' % fy))
        check(c6 + ' FY%d spending' % fy, float(r2(f1[fy][1])), fig(c6, 'out%d' % fy))
    check(c6 + ' FY2023-FY2024 short', r0(sum(f1[f][1] - f1[f][0] for f in (2023, 2024))),
          fig(c6, 'short'))
    check(c6 + ' FY2025-FY2026 ahead', r0(sum(f1[f][0] - f1[f][1] for f in (2025, 2026))),
          fig(c6, 'ahead'))
    sal = [dz(r['ytd_expended']) for r in mrows
           if r['account'] == '1301-3-300-3510-06-0-00-1-519999' and r['fiscal_year'] == '2025']
    check(c6 + ' FY2025 HS salaries', r0(sal[0]), fig(c6, 'sal'))
    a25 = gl_row(2025, 'S3066672', '535016')
    check(c6 + ' FY2025 reclass transfer', r0(dz(a25['transfers_adjustments'])), fig(c6, 'reclass'))
    check(c6 + ' FY2027 draw', r0(nums[3]), fig(c6, 'draw'))

    # 7. The contract against the model: the rate from model/finance.py itself.
    c7 = 'contract-outruns-the-model'
    sys.path.insert(0, os.path.join(ROOT, 'model'))
    import finance
    rate = D(str(finance.DEFAULT_ASSUMPTIONS['transport']))
    check(c7 + ' model rate', float(rate), fig(c7, 'rate'))
    check(c7 + ' model base', b27[0], fig(c7, 'base'))
    m28 = D(b27[0]) * (1 + rate)
    check(c7 + ' model FY2028', float(r2(m28)), fig(c7, 'm28'))
    check(c7 + ' contract FY2028', r0(reg[2028]), fig(c7, 'p28'))
    check(c7 + ' contract FY2027', r0(reg[2027]), fig(c7, 'p27'))
    check(c7 + ' contract rise into FY2028', p1(reg[2028] - reg[2027], reg[2027]), fig(c7, 'cpct'))
    check(c7 + ' gap', r0(reg[2028] - m28), fig(c7, 'gap'))
    check(c7 + ' option FY2029', r0(reg[2029]), fig(c7, 'o29'))
    check(c7 + ' option FY2030', r0(reg[2030]), fig(c7, 'o30'))

    # 8. The two sheets: the workbook from the database, the Finance Committee copy from its
    # CSV, every FY2024 row. The workbook's matched total is its whole total less the two
    # middle school spring sports, the only rows the second sheet does not print -- asserted.
    c8 = 'two-sheets-one-cost'
    fin = [D(r['value']) for r in csv.DictReader(open(os.path.join(DATA, 'athletics-fincom.csv'),
                                                      encoding='utf-8'))
           if r['metric'] == 'transportation_cost_fy24' and r['value'].strip()]
    msspring = [D(str(v)) for v, in db.execute(
        "SELECT value FROM athletics_by_sport WHERE metric='Transportation' AND is_numeric=1 "
        "AND fy=2024 AND level='MS' AND season='Spring'")]
    check(c8 + ' Finance Committee copy', r0(sum(fin)), fig(c8, 'lo'))
    check(c8 + ' workbook, matched sports', float(r2(sheet[2024] - sum(msspring))), fig(c8, 'hi'))
    check(c8 + ' sports compared', len(fin), fig(c8, 'n'))
    check(c8 + ' workbook total', float(sheet[2024]), fig(c8, 'all'))

    # ---- trips, OUR estimate, from the form's own words and rates (payload, not a card) --
    est = re.search(r'(\d+) fild trips.*?([\d,]+) miles', at(32))
    trips_n, miles = int(est.group(1)), int(est.group(2).replace(',', ''))
    hours = 4 if 'four (4) hours' in at(33) else None
    mrate = money(re.search(r'\$ ([\d.]+)', at(35)).group(1))
    wrate = money(re.search(r's (\d+)', at(73)).group(1))
    full = D(miles) / trips_n * mrate + hours * wrate
    nowait = D(miles) / trips_n * mrate
    check('trip price', float(r2(full)), pay['contract']['trip_full'])
    check('no-wait trip price', float(r2(nowait)), pay['contract']['trip_nowait'])
    for s in pay['sports']:
        if s['fy2025']:
            check('trips %s' % s['label'], float((D(str(s['fy2025'])) / full).quantize(D('0.1'))),
                  s['trips'])

    # ---- the brief (notes/process/REPORT-FORMAT.md): every figure, a second route --------
    # The stat row is gone; the brief's sentences carry the figures now. Each figure the brief
    # registers must appear in EXPECT below, recomputed here from the database, the MUNIS CSV,
    # the bid form's text layer or the quotation -- a figure with no entry is a failure, so
    # nothing in the top of the page goes unverified by omission.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import brief as BR
    bf = pay['brief']
    for p_ in BR.check(bf):
        bad.append('brief: ' + p_)
    tr = {}
    for fy, sport, v in db.execute(
            "SELECT fy, sport, value FROM athletics_by_sport WHERE metric='Transportation' "
            "AND is_numeric=1 AND level='HS'"):
        tr[(int(fy), sport)] = D(str(v))
    it24 = tr[(2024, 'Indoor Track - Boys')] + tr[(2024, 'Indoor Track - Girls')]
    if tr[(2024, 'Indoor Track - Boys')] != tr[(2024, 'Indoor Track - Girls')]:
        bad.append('the FY2024 indoor track rows are no longer identical')
    teams24 = {k[1]: v for k, v in tr.items() if k[0] == 2024 and 'Indoor Track' not in k[1]}
    if any(v >= it24 for v in teams24.values()):
        bad.append('a single FY2024 row now costs more than indoor track read as one team')
    fin_it24 = [D(r['value']) for r in csv.DictReader(open(os.path.join(DATA, 'athletics-fincom.csv'),
                                                           encoding='utf-8'))
                if r['metric'] == 'transportation_cost_fy24' and 'Indoor Track' in r['sport']][0]
    sp_rows = {fy: sum(D(str(v)) for v, in db.execute(
        "SELECT value FROM athletics_by_sport WHERE metric='Transportation' AND is_numeric=1 "
        "AND season='Spring' AND fy=?", (fy,))) for fy in (2024, 2025)}
    r25 = gl_row(2025, 'S3991692', '535025')
    r23o = -dz(gl_row(2023, 'S3991692', '535025')['available_budget'])
    r24 = gl_row(2024, 'S3991692', '535025')
    f1sum = lambda fys, sign: r0(sum(sign * (f1[f][1] - f1[f][0]) for f in fys))
    EXPECT = {
        ('sped/say', 'over'): r0(over26), ('sped/say', 'fy'): 2026,
        ('sped/step1', 'v'): r0(dz(s26['original_approp'])), ('sped/step1', 's'): r0(sp26),
        ('sped/step1', 'f'): 2010,
        ('sped/step2', 'a'): 2027, ('sped/step2', 'b'): r0(b27s),
        ('sped/step2', 'c'): r0(b27s - sp26), ('sped/step2', 'd'): 2026,
        ('sped/step3', 'a'): start, ('sped/step3', 'b'): cut,
        ('sped/step3', 's'): sum(under[f] for f in range(start, cut + 1)),
        ('sped/step3', 'o2024'): 2024, ('sped/step3', 'o2026'): 2026,
        ('regular/say', 'fy'): 2027, ('regular/say', 'p'): r0(reg[2027]),
        ('regular/step1', 'a'): 2025, ('regular/step1', 'b'): r0(dz(r25['ytd_expended']) + dz(r25['encumbrances'])),
        ('regular/step1', 'c'): 2026, ('regular/step1', 'd'): r0(paid),
        ('regular/step2', 'a'): 2023, ('regular/step2', 'b'): r0(r23o), ('regular/step2', 'c'): 2024,
        ('regular/step2', 'd'): r0(-dz(r24['available_budget'])),
        ('regular/step2', 'e'): r0(dz(r24['transfers_adjustments'])),
        ('regular/step3', 'a'): p1(reg[2027] - reg[2026], reg[2026]), ('regular/step3', 'b'): 2027,
        ('regular/step3', 'c'): p1(reg[2028] - reg[2027], reg[2027]), ('regular/step3', 'd'): 2028,
        ('regular/step4', 'a'): 2024, ('regular/step4', 'b'): 2025,
        ('regular/step4', 'c'): 2026, ('regular/step4', 'd'): p1(reg[2026] - b25, b25),
        ('fee/say', 'p'): r0(paid),
        ('fee/step1', 'a'): r0(reg[2026] - dz(r26['original_approp'])),
        ('fee/step1', 'b'): r0(dz(r26['original_approp'])),
        ('fee/step1', 'c'): r0(dz(r26['transfers_adjustments'])),
        ('fee/step2', 'a'): float(r2(fee[2026])), ('fee/step2', 'b'): 2026,
        ('athletic-fund/say', 'fy'): 2027, ('athletic-fund/say', 'p'): p1(nums[3], nums[1]),
        ('athletic-fund/step1', 'a'): r0(nums[2]), ('athletic-fund/step1', 'b'): r0(nums[3]),
        ('athletic-fund/step2', 'a'): f1sum((2023, 2024), 1), ('athletic-fund/step2', 'b'): 2023,
        ('athletic-fund/step2', 'c'): 2024,
        ('athletic-fund/step3', 'a'): f1sum((2025, 2026), -1), ('athletic-fund/step3', 'b'): 2025,
        ('athletic-fund/step3', 'c'): 2026,
        ('athletic-fund/step4', 'a'): r0(nums[3]),
        ('track/say', 'a'): float(it24), ('track/say', 'b'): 2024,
        ('track/step1', 'a'): float(tr[(2024, 'Indoor Track - Boys')]), ('track/step1', 'b'): 2024,
        ('track/step1', 'c'): float(it24), ('track/step1', 'd'): float(tr[(2024, 'Football')]),
        ('track/step1', 'e'): float(tr[(2024, 'Girls Soccer')]),
        ('track/step2', 'a'): 2025, ('track/step2', 'b'): 0.0,
        ('track/step2', 'c'): abs(p1(sp_rows[2025] - sp_rows[2024], sp_rows[2024])),
        ('track/step2', 'd'): 2024,
        ('track/step4', 'b'): 2026, ('track/step4', 'd'): 2027,
        ('track/step5', 'a'): 2024, ('track/step5', 'b'): float(fin_it24),
        ('fy27/say', 'a'): p1(sd27 - sd26, sd26), ('fy27/say', 'b'): 2027,
        ('fy27/say', 'c'): p1(al27 - al26, al26),
        ('fy27/step1', 'a'): r0(sd26), ('fy27/step1', 'b'): r0(sd27),
        ('fy27/step1', 'c'): r0(bk[170][0]), ('fy27/step1', 'd'): r0(bk[170][1]),
        ('fy27/step2', 'a'): p1(bk[170][0] - bk[170][1], sd27 - sd26),
        ('fy27/step3', 'a'): float(rate) * 100, ('fy27/step3', 'b'): r0(reg[2028] - m28),
        ('fy27/step3', 'c'): 2028,
    }
    # The waiting rates, from the bid form's own text layer: the FY2026 page (line 73,
    # `x s 130-`) and the FY2027 page (line 161, `x $ 140.00 x`), read by position.
    EXPECT[('track/step4', 'a')] = float(money(re.search(r's (\d+)', at(73)).group(1)))
    EXPECT[('track/step4', 'c')] = float(money(re.search(r'\$ ([\d.]+)', at(161)).group(1)))
    seen = set()
    for where, u in BR.units(bf):
        for k_, f_ in u['figures'].items():
            seen.add((where, k_))
            if (where, k_) not in EXPECT:
                bad.append('brief %s figure %r (%s) has no second route here' % (where, k_, f_['text']))
                continue
            want = EXPECT[(where, k_)]
            got = f_['value']
            if isinstance(want, float) or isinstance(got, float):
                if abs(float(want) - float(got)) > 0.005:
                    bad.append('brief %s %s: recomputed %r, payload says %r' % (where, k_, want, got))
            elif want != got:
                bad.append('brief %s %s: recomputed %r, payload says %r' % (where, k_, want, got))
    for k_ in sorted(set(EXPECT) - seen):
        bad.append('verifier expects brief figure %s, which the payload no longer carries' % (k_,))
    # Every sentence of the top is in the published markdown, so /docs and the PDF say it too.
    for where, u in BR.units(bf):
        if u['text'] not in flat:
            bad.append('brief %s is not in the markdown: %r' % (where, u['text'][:60]))
    # Every caption cited is still in the caption file at its moment.
    for c in pay['captions']:
        if '&t=' not in c['url']:
            bad.append('caption %s cites no timestamp' % c['key'])

    # ---- DESE: a third route to the school-day total, where it ties ------------------
    dese = {}
    for fy, code, gf in db.execute(
            "SELECT fy, func_code, gen_fund FROM dese_function_expenditure WHERE lea=? AND "
            "((func_code='3300' AND level='detail') OR func_code='ODTR')", (LEA,)):
        dese[int(fy)] = dese.get(int(fy), 0) + r0(gf)
    for fy in (2022, 2023, 2024):
        want = spent(fy, 'regular') + spent(fy, 'sped')
        if dese.get(fy) != want:
            bad.append('FY%d: DESE %s against the ledger %s' % (fy, dese.get(fy), want))

    # ---- quotations, verbatim, at the address cited ---------------------------------
    for q in pay['said']:
        path = os.path.join(ROOT, 'sources', q['cite'][len('/docs/'):].replace(
            'minutes/text/', 'meetings/text/', 1))
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8').read())
        if re.sub(r'\s+', ' ', q['quote']) not in text:
            bad.append('quote %r is not verbatim in %s' % (q['key'], q['cite']))
        if q['quote'] not in md and re.sub(r'\s+', ' ', q['quote']) not in flat:
            bad.append('quote %r is not in the published markdown' % q['key'])

    # ---- the prose: every card in the markdown; rule 2 against the payload ----------
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import conclusions
    for p in conclusions.check('transportation', pay['conclusions']):
        bad.append(p)
    for c in pay['conclusions']:
        for k in ('claim', 'so_what'):
            if c[k] not in flat:
                bad.append('%s %s is not in the markdown' % (c['id'], k))
        if c['kind'] == 'hypothesis' and 'our estimate' not in (c['claim'] + c['basis']).lower():
            bad.append('%s is an estimate and does not say so' % c['id'])

    if bad:
        print('verify_transportation: %d problem(s)' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    print('verify_transportation: every headline figure recomputed by a second route; %d '
          'conclusions, %d quotations checked' % (len(pay['conclusions']), len(pay['said'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
