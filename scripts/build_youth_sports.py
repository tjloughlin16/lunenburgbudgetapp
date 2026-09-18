#!/usr/bin/env python3
"""Youth sports and the town: what the leagues pay to use the fields, where it lands,
and what the record says about the arrangement.

    python3 scripts/build_youth_sports.py           # write fy28/public/data/youth-sports.json
    python3 scripts/build_youth_sports.py --check   # fail if it no longer reproduces

TJ, 17 September 2026: "Youth Sports report ;) Please build, starting with this" -- after
a records request produced Lunenburg Youth Soccer's field-rental receipts and the
archive turned out to hold where they land.

THREE KINDS OF EVIDENCE, KEPT APART (rules 7, 13, 13a):
  evidence   the town's FY26 special-revenue report (a MUNIS printout, period 9): fund
             1306 School Facilities Use Revolving, fund 1545 Artificial Turf Revolving,
             fund 1500 Park Revolving -- revenue, expenditure and balance, as printed
  stated     the district's records-request answer: seven receipts from Lunenburg Youth
             Soccer, FY2024-FY2026, typed into a workbook by the business office
  transcribed the annual town reports' special-revenue schedules, FY2011-FY2023, read by
             scripts/extract_special_revenue.py -- and NOT reconciled to the totals those
             pages print. Shown as a series with that label; no conclusion rests on it.
And the recordings: what was said about the arrangement, cited to the video at its
second, which is a finding aid and never a figure.

WHAT IS NOT HERE. What any league pays in total, or what a field costs to keep: the fund's
journal (which would list every payer) is not in the archive, and the schools' grounds
cost is split by no programme. Both are registered in money-gaps.csv.
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C                                           # noqa: E402
from conclusions import conclusion, emit, figure                  # noqa: E402

SPECIAL = os.path.join(ROOT, 'sources', 'town-ledgers', 'fund-balances', 'special-revenue-fy2026-p09.xlsx')
SERIES = os.path.join(ROOT, 'sources', 'data', 'special-revenue-funds.csv')
RECEIPTS = os.path.join(ROOT, 'sources', 'data', 'field-rental-receipts-lysa.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'youth-sports.json')
FUNDS = {1306: 'School Facilities Use Revolving', 1545: 'Artificial Turf Revolving', 1500: 'Park Revolving', 1301: 'Chapter 658 (athletics) Revolving'}
# The leagues the town's own Parks Commission page lists as "Local Sports Organization
# Contacts ... provided as a courtesy and are not run or managed by the Parks Commission".
LEAGUES = ['Ayer-Shirley-Lunenburg Bengals', 'Lunenburg Little League (Baseball and Softball)',
           'Lunenburg Youth Soccer Association', 'Lunenburg Jr Basketball']
# What was said, on the record, about the arrangement -- the video at its second.
SAID = [
    dict(board='Select Board', date='2016-05-03', video='Lj-VhDQJaDM', t=5765,
         what='The turf replacement funding plan: $30,000 a year from the cell tower, $15,000 a year from Lunenburg Youth Soccer and $7,500 from the Bengals, “to achieve the goal of paying for the replacement of the field over its lifetime.”'),
    dict(board='Select Board', date='2017-10-10', video='eh_p2pv29rI', t=1587,
         what='“They cut us a check every season” — the Bengals and youth soccer paying a set fee toward the turf bond.'),
    dict(board='School Committee', date='2017-11-16', video='0HNw4Nak1r4', t=5477,
         what='Field costs moved out of the operating budget into facilities-use funding, with the money received from youth soccer for the fields going there.'),
    dict(board='School Committee', date='2019-05-22', video='dJvXvSzbuXw', t=7260,
         what='Reworking the facilities-use rates: “we were collecting a lot more from Lunenburg Youth Soccer than we might otherwise need.”'),
    dict(board='School Committee', date='2019-09-04', video='9RytVr2VrMo', t=5403,
         what='Youth soccer’s fall field requests “didn’t closely match up with what I expected as far as number of hours.”'),
    dict(board='Select Board', date='2019-03-05', video='jdoMxZPiJBM', t=3977,
         what='“Are some of the organizations like Lunenburg Youth Soccer really associated with the public schools, or are they just Lunenburg-based sports organizations?”'),
    dict(board='Finance Committee', date='2022-02-17', video='Qx7EgjovsNE', t=6704,
         what='“Talk to the presidents of Lunenburg Bengals, Lunenburg Youth Soccer Association, Lunenburg Youth Basketball Association — all these organizations that use our facilities.”'),
    dict(board='School Committee', date='2022-08-31', video='RWhw7yqXjjk', t=496,
         what='The athletic and facilities directors working out schedules with the leaders of youth soccer and the Bengals; a shared two-week look-ahead for every field.'),
    dict(board='School Committee', date='2014-12-03', video='0x44owqvTxI', t=5986,
         what='$1,800 to replace soccer goals owned by youth soccer, taken when the league moved its practices off the high school fields.'),
]


def fail(msg):
    raise SystemExit('build_youth_sports: ' + msg)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fy26_funds():
    """Fund rows off the town's period-9 report, by the header row's own column letters."""
    import openpyxl
    ws = openpyxl.load_workbook(SPECIAL, read_only=True, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = {str(v).strip(): i for i, v in enumerate(rows[6]) if v}
    need = ('FUND', 'ACCOUNT BALANCE', 'REVENUE', 'SALARIES', 'EXPENDITURE', 'FUND BALANCE')
    for n in need:
        if n not in hdr:
            fail('the special-revenue report’s header row lacks %r: %s' % (n, sorted(hdr)))
    out = {}
    for r in rows[7:]:
        f = r[hdr['FUND']]
        if isinstance(f, (int, float)) and int(f) in FUNDS:
            # THE COLUMNS THE ARITHMETIC IDENTIFIES, and only those. The export's header row
            # carries fewer labels than the row has columns, so a label cannot be trusted
            # by position -- TJ, 17 September 2026, read one cell as a prior-year balance
            # that the FY24 annual report labels deferred revenue. What can be trusted is
            # the identity opening + revenue - salaries - expenditure = closing, which the
            # four cells below satisfy to the cent for every fund here, and is asserted.
            opening = -(num(r[hdr['ACCOUNT BALANCE']]) or 0)
            revenue = -(num(r[hdr['REVENUE']]) or 0)
            salaries = num(r[hdr['SALARIES']]) or 0
            expenditure = num(r[hdr['EXPENDITURE']]) or 0
            closing = -(num(r[hdr['FUND BALANCE']]) or 0)
            if abs(opening + revenue - salaries - expenditure - closing) > 0.02:
                fail('fund %d does not foot: %.2f + %.2f - %.2f - %.2f != %.2f' % (int(f), opening, revenue, salaries, expenditure, closing))
            out[int(f)] = dict(fund=int(f), name=FUNDS[int(f)], opening=round(opening, 2), revenue=round(revenue, 2),
                               salaries=round(salaries, 2), expenditure=round(expenditure + salaries, 2), available=round(closing, 2))
    for f in FUNDS:
        if f not in out:
            fail('fund %d not found in %s' % (f, os.path.relpath(SPECIAL, ROOT)))
    asof = str(rows[3][0])[:10]
    return out, asof


def series():
    rows = [r for r in csv.DictReader(open(SERIES, encoding='utf-8')) if r['fund'].strip() == 'School Facilities Use' and r['edition'] == r['edition'].split('-')[0]]
    out = []
    for r in rows:
        out.append(dict(fy=int(r['fy']), forward=num(r['v1']), receipts=num(r['v2']), disbursed=num(r['v3']), carried=num(r['v4']),
                        status=r['status'], page=int(r['page']) if r['page'] else None))
    # FY2024 IS PRINTED IN A DIFFERENT SHAPE: the FY2024 annual report carries a "Special
    # Revenue Fund Balance Detail as of June 30, 2024" with a balance column and no
    # receipts or disbursements, and the extract's positional v2 for fund 1306 is that
    # balance -- $3,010.67 under "Fund Balance 6/30/2024" on the page (TJ, 17 September
    # 2026, with the page in front of him; the first reading here took v2 for the second
    # header, which is the mistake rule 13 names). Carried as a balance only.
    fy24 = [r for r in csv.DictReader(open(SERIES, encoding='utf-8')) if r['fy'] == '2024' and r['fund'].strip().startswith('1306')]
    if fy24:
        out.append(dict(fy=2024, forward=None, receipts=None, disbursed=None, carried=num(fy24[0]['v2']),
                        status='balance only, as printed', page=int(fy24[0]['page']) if fy24[0]['page'] else None))
    out.sort(key=lambda x: x['fy'])
    if len(out) < 8:
        fail('only %d years of School Facilities Use in the extract' % len(out))
    return out


def receipts():
    rows = list(csv.DictReader(open(RECEIPTS, encoding='utf-8')))
    if len(rows) < 5:
        fail('the receipts extract holds %d rows' % len(rows))
    return [dict(fy=r['fiscal_year_as_listed'], date=r['receipt_date'], amount=float(r['amount']), payer=r['payer_as_printed'], munis=r['munis_description']) for r in rows]


def sources():
    man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = []
    for key, table, publisher, note in (
        ('town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx', 'Special revenue funds, FY26 through 31 March 2026', 'Town of Lunenburg (MUNIS)',
         'The town’s own printout of every special-revenue fund: revenue, expenditure and balance. Funds 1306, 1545 and 1500 are read from it.'),
        ('town-ledgers/account-details/field-rental-receipts-fy2024-fy2026-lysa.xlsx', 'Field rental receipts from Lunenburg Youth Soccer, FY2024–FY2026', 'Lunenburg Public Schools, by records request',
         'Seven receipts typed into a workbook by the district’s business office; one carries a pasted MUNIS receipt record.'),
        ('data/special-revenue-funds.csv', 'Special revenue funds as the annual town reports print them, FY2011–FY2024', 'This project, from the town’s annual reports',
         'Transcribed page by page and NOT reconciled to the pages’ own totals; the School Facilities Use rows are drawn as a series and rest no conclusion.'),
    ):
        r = man.get(key) or fail('%s is not in the manifest (rule 12)' % key)
        out.append(dict(path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']), url=r.get('upstream') or '',
                        docs_url='/docs/' + key, table=table, publisher=publisher, note=note))
    return out


def build():
    funds, asof = fy26_funds()
    ser = series()
    rec = receipts()
    f1306, f1545 = funds[1306], funds[1545]
    total = sum(r['amount'] for r in rec)
    fy26 = [r for r in rec if r['fy'] == 'FY2026']
    fy26_total = sum(r['amount'] for r in fy26)
    by_fy = {}
    for r in rec:
        by_fy[r['fy']] = by_fy.get(r['fy'], 0) + r['amount']
    peak = max(ser, key=lambda y: y['receipts'] or 0)
    latest = [y for y in ser if y['fy'] == max(y['fy'] for y in ser)][0]

    funds_total_in = sum(funds[k]['revenue'] for k in (1306, 1545, 1500, 1301))
    funds_total_held = sum(funds[k]['available'] for k in (1306, 1545, 1500, 1301))
    funds_total_out = sum(funds[k]['expenditure'] for k in (1306, 1545, 1500, 1301))
    rows = [
        conclusion(
            id='the-funds',
            claim='Four funds take in field and facility money, and held %s at 31 March 2026.'
                  % C.usd(funds_total_held),
            so_what='%s came in and %s went out in nine months of FY2026, none of it appropriated by Town Meeting.'
                    % (C.usd(funds_total_in), C.usd(funds_total_out)),
            figures={'held': figure(funds_total_held, C.usd(funds_total_held), 'held across the four field and facility funds at 31 March 2026'),
                     'in': figure(funds_total_in, C.usd(funds_total_in)), 'out': figure(funds_total_out, C.usd(funds_total_out)),
                     **{'f%d' % k: figure(funds[k]['available'], C.usd(funds[k]['available'])) for k in (1306, 1545, 1500, 1301)}},
            figure='held', kind='measured', bearing='sizes',
            detail='School Facilities Use (1306) takes rent from outside groups using school buildings and fields and held %s. Artificial Turf (1545) held %s. '
                   'Park Revolving (1500), the Parks Commission’s own fee fund, held %s. Chapter 658 athletics (1301), which is the school teams rather than '
                   'the outside leagues, held %s. A revolving fund may be spent on the thing that raised it without an appropriation, which is why these '
                   'balances sit outside the budget argument the town has every spring.'
                   % (C.usd(funds[1306]['available']), C.usd(funds[1545]['available']), C.usd(funds[1500]['available']), C.usd(funds[1301]['available'])),
            basis='sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx, the rows for funds 1306, 1545, 1500 and 1301, read by the identity opening + revenue − salaries − expenditure = closing.',
            not_shown='Who paid into each fund, and for what. The report is balances, not transactions; only fund 1301 has a journal in the archive.',
            see=[('/accounts', 'Every account, once')],
            allow=('1306', '1545', '1500', '1301', '658', 'FY2026', '2026', '31'),
        ),
        conclusion(
            id='what-the-fields-take-in',
            claim='Field and facility rent ran %s into the schools’ fund in nine months of FY2026.'
                  % C.usd(f1306['revenue']),
            so_what='%s went out; the fund holds %s, which the schools may spend on facilities without a vote.'
                    % (C.usd(f1306['expenditure']), C.usd(f1306['available'])),
            figures={'revenue': figure(f1306['revenue'], C.usd(f1306['revenue']), 'into the School Facilities Use fund, FY2026 through March'),
                     'spent': figure(f1306['expenditure'], C.usd(f1306['expenditure'])),
                     'held': figure(f1306['available'], C.usd(f1306['available'])),
                     'fy24_close': figure(latest['carried'] or 0, C.usd(latest['carried'] or 0)),
                     'fy26_open': figure(f1306['opening'], C.usd(f1306['opening']))},
            figure='revenue', kind='measured', bearing='sizes',
            detail='Fund 1306 is where a group renting a school field or gym pays. Nine months of FY2026: %s in, %s out, %s available. The annual reports carry the '
                   'same fund back to FY2011 under the name “School Facilities Use”, and the archive cannot see FY2025 at all — the balance moved from %s at 30 June 2024 '
                   'to %s a year later with no schedule in between.'
                   % (C.usd(f1306['revenue']), C.usd(f1306['expenditure']), C.usd(f1306['available']), C.usd(latest['carried'] or 0), C.usd(f1306['opening'])),
            basis='The FY26 special-revenue report for the current year; sources/data/special-revenue-funds.csv for the annual-report series, which is transcribed and does not tie to its own printed totals.',
            not_shown='What the %s was spent on, and what a field costs the town to keep. Grounds, custodial and utility costs are coded to no programme.' % C.usd(f1306['expenditure']),
            see=[('/parks-and-recreation', 'Parks and Recreation — the department, its fund, its grounds')],
            allow=('1306', 'FY2026', 'FY2011', 'FY2025', '2026', '2024', '30'),
        ),
        conclusion(
            id='who-uses-the-fields',
            claim='Four youth leagues use the fields; one league’s payments are the only ones we hold records for.',
            so_what='%s of receipts, FY2024–FY2026, by records request. What the others pay is published nowhere.'
                    % C.usd(total),
            figures={'paid': figure(total, C.usd(total), 'in receipts from the one league whose payments the archive holds'),
                     'n': figure(len(rec), C.num(len(rec)))},
            figure='paid', kind='measured', bearing='sizes',
            detail='The leagues that use town and school fields are %s. What any of them pays is published nowhere. A records request to the district produced one '
                   'league’s receipts — Lunenburg Youth Soccer, %s across %s payments, FY2024 to FY2026 — and that is a start rather than a finding about that league: '
                   'it is the one we asked for first. The same request to the town and the district for every user group would make this a comparison instead of a sample.'
                   % (', '.join(LEAGUES), C.usd(total), C.num(len(rec))),
            basis='sources/town-ledgers/account-details/field-rental-receipts-fy2024-fy2026-lysa.xlsx, every row; the leagues as the town’s own Parks Commission page lists them.',
            not_shown='What every other league pays, and on what terms. One league’s receipts cannot say whether the arrangement is the same for all of them, and nothing here suggests it is not.',
            see=[('/what-sports-cost', 'What school sports cost, and who pays')],
            allow=('FY2024', 'FY2026', '2026', '1306') + tuple(LEAGUES),
        ),
        conclusion(
            id='the-turf-fund',
            claim='The Artificial Turf fund took in %s in FY2026, the figure the 2016 plan adds up to.' % C.usd(f1545['revenue']),
            so_what='The 2016 plan as said: $30,000 a year from the cell tower, $15,000 from a youth league. No ledger splits it.',
            figures={'revenue': figure(f1545['revenue'], C.usd(f1545['revenue']), 'into the Artificial Turf fund, FY2026'),
                     'spent': figure(f1545['expenditure'], C.usd(f1545['expenditure'])), 'held': figure(f1545['available'], C.usd(f1545['available']))},
            figure='revenue', kind='hypothesis', bearing='sizes',
            detail='The fund’s FY2026 revenue is %s, its expenditure %s, its available balance %s — all as printed. That the %s is $30,000 of cell-tower rent plus $15,000 from a '
                   'youth league is what the Select Board said the plan was in May 2016 (the recording, at 1:36:05), and it matches to the dollar. It is not established by any '
                   'ledger the archive holds, which is why this card is a hypothesis: the receipt detail for fund 1545 would settle it, and would say which groups are inside it.'
                   % (C.usd(f1545['revenue']), C.usd(f1545['expenditure']), C.usd(f1545['available']), C.usd(f1545['revenue'])),
            basis='The same FY26 report, the row for fund 1545; the Select Board recording of 3 May 2016 at 5,765 seconds, machine captions.',
            not_shown='Whether the arrangement is still what was described in 2016, or who signed it. A recording is a finding aid; the agreement itself is not in the archive.',
            see=[('/meeting-minutes', 'Our minutes of the recordings')],
            allow=('30,000', '15,000', '1:36:05', '5,765', '1545', '2016', '2026', 'FY2026'),
        ),
    ]
    return dict(
        generated_by='scripts/build_youth_sports.py',
        about='Youth sports and the town: the funds that field and facility money runs through, what goes in and out of them, which leagues use the fields, and what the boards have said about the arrangement since 2014.',
        grain='DOLLARS as three different documents print them — a MUNIS fund report (evidence), a records-request workbook (stated), and the annual reports’ schedules (transcribed, unreconciled) — kept apart on the page. Not what a field costs, and not what any league pays in total.',
        as_of=asof, leagues=LEAGUES,
        funds=[funds[k] for k in (1306, 1545, 1500, 1301)],
        receipts=rec, receipts_total=round(total, 2), receipts_by_fy=by_fy,
        series=ser, series_peak=dict(fy=peak['fy'], receipts=peak['receipts']), series_latest=latest,
        said=SAID,
        sources=sources(),
        not_established=[
            'Who else pays into fund 1306, and how much: the fund’s journal detail (the report the archive holds for fund 1301) would list every receipt by payer.',
            'What happened in FY2025: the fund stood at $3,010.67 on 30 June 2024 (the annual report) and at $65,241.82 on 30 June 2025 (the FY26 report’s opening balance), and nothing in the archive shows the year’s receipts and spending — the FY2025 special-revenue report would.',
            'Whether the $45,000 a year in the turf fund is still $30,000 of cell-tower rent and $15,000 from youth soccer, as described in 2016, and where the Bengals’ $7,500 goes.',
            'What the fields cost the town to keep. The schools’ grounds, custodial and utility costs are coded to no programme.',
        ],
        conclusions=emit('youthsports', rows),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        if have != data:
            print('STALE %s — run build_youth_sports.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the fund report, the receipts and the annual-report extract' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('%s: %d receipts totalling %s; fund 1306 FY26 revenue %s; %d years of the series; %d conclusions'
          % (os.path.relpath(OUT, ROOT), len(data['receipts']), C.usd(data['receipts_total']), C.usd(data['funds'][0]['revenue']), len(data['series']), len(data['conclusions'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
