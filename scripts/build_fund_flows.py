#!/usr/bin/env python3
"""MONEY IN, MONEY OUT, PER SCHOOL FUND: what each fund other than the school general fund
RECEIVED, what it SPENT, the difference, and its balance at 30 June, FY2023 onward.

    python3 scripts/build_fund_flows.py           # writes sources/data/school-fund-flows.csv
    python3 scripts/build_fund_flows.py --check   # exit 1 if the file is not what this writes

TJ, 29 October 2026: "if the school received circuit breaker money, or idea grant money, or fee
money, or whatever, and didnt spend it, we need to show total revenue and total unspent revenue,
overall and on a per-fund basis ... And the year over year change of that will be important."
This writes the DATA for that. It builds no page.

=== WHAT EACH COLUMN IS (decided, not inferred) ===

One row per fund per fiscal year, for every fund other than 0100 that holds a line in the school
journal (`journal.py`). Every amount is from the ACTUAL column (`posts_to == 'actual'`). A
budgeted (estimated) revenue -- `BUC`/`BUA` on a revenue account -- is never read (rule 1).

  received_outside        receipts to the fund's revenue accounts (object 4xxxxx), less refunds
                          paid out of them (`API` on a revenue account), other than the transfers
                          below. Sign: money in is positive.
  received_not_in_journal revenue the period-13 special funds report PRINTS on an account the
                          journal does not hold (measured: five investment-income accounts,
                          1305-...-480100). Read off the Town's report, added to the receipts so the
                          balance is whole; zero everywhere else.
  transfers_in / _out     revenue-account actuals that move money BETWEEN funds rather than in from
                          outside: an operating transfer (object 49xxxx), or a journal entry
                          (`GEN`/`GRV`) whose journal also posts a revenue account of another fund.
                          Both positive numbers. No transfer-OUT object exists on any school
                          account in this run, so transfers_out is only the receipt reclasses.
  spent_actual            expense actuals (object 5xxxxx): invoices, pay runs, journal entries,
                          receipts credited to an expense. THE BALANCE USES THIS -- cash: an order
                          not yet paid has not left the fund.
  spent_with_owed         spent_actual plus encumbrances still open: the site's definition of
                          SPENT for comparing with a budget (journal.py). Equal to spent_actual in
                          every closed year by the close; differs only in the open year.
  cost_moved_by_entry     the part of spent_actual that arrived by journal entries whose journal
                          also posts an expense account of ANOTHER fund (the general fund
                          included): positive = cost put on this fund, negative = cost taken off.
                          Already inside spent_actual; shown so a reader can tell a bill paid from
                          a cost re-charged.
  net                     received_outside + received_not_in_journal + transfers_in
                          - transfers_out - spent_actual.
  opening_balance         the fund's balance on 1 July of the year. FY2023's is established below;
                          each later year's is the year before's closing.
  closing_balance         opening_balance + net: the balance at 30 June (the open year: to date).

=== WHERE THE 1 JULY 2022 BALANCE COMES FROM ===

Two documents, and they are compared rather than blended.

  1. THE TOWN'S SPECIAL REVENUE LEDGER AT 31 MARCH 2026 (`school-special-revenue-fy26-q3.csv`,
     our reading of the MUNIS FY26 period 9 special revenue report): a balance, and FY26-to-date
     revenue and spending. Its balance less its own FY26 flows is the fund's 1 July 2025 balance;
     less our FY2023-FY2025 net, it is the 1 July 2022 balance. DERIVED, from an accounting-system
     printout and the journal, and labelled so.
  2. THE FY2023 ANNUAL TOWN REPORT'S SPECIAL REVENUE SCHEDULE (`special-revenue-read.csv`, fy
     2023): FORWARD 7/1/2022, RECEIPTS, DISBURSEMENTS and the carried balance, PRINTED per fund by
     NAME. Which name is which fund is OUR mapping (`AR23_NAME`), declared one fund at a time.

(1) is used where it exists, because it reproduces a balance the Town's own system printed; (2) is
its independent test, and the opening where (1) does not reach. A fund in neither has no opening
balance and its rows say so -- registered in money-gaps.csv (rule 7c).

=== THE TIES ===

REFUSED if they fail -- the script writes nothing:
  * expense: per fund per year, the journal's actual expense equals the period-13 report's printed
    `ytd_expended` to the cent (`munis-school-ytd.csv`, report special-school, type E);
  * revenue: per ACCOUNT per year, the journal's actual revenue equals the report's printed revenue
    (type R) to the cent, wherever the journal holds the account. An account the report prints and
    the journal does not hold is carried in `received_not_in_journal` and named in the tie column.
A fund the period-13 report does not print is `no check`, never `checked`.

COMPARED and REPORTED, never claimed: the FY2023 annual report's receipts and disbursements, and
the balances it and the FY2024 and FY2025 editions print (`special-revenue-funds.csv`), and the
31 March 2026 ledger's FY26-to-date flows. Each says `ties` only when it ties to the cent, and
otherwise prints both figures.

FY2026 IS STILL OPEN (`journal.OPEN_FY`): its actuals can move until the close.
"""
import argparse
import csv
import io
import os
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal as J  # noqa: E402
import fy_breakdown as FB  # noqa: E402
import build_fy_breakdown as BFB  # noqa: E402

ROOT = J.ROOT
DATA = J.DATA
OUT = os.path.join(DATA, 'school-fund-flows.csv')
P13 = os.path.join(DATA, 'munis-school-ytd.csv')
Q3 = os.path.join(DATA, 'school-special-revenue-fy26-q3.csv')
AR_READ = os.path.join(DATA, 'special-revenue-read.csv')
AR_FUNDS = os.path.join(DATA, 'special-revenue-funds.csv')
Q3_PERIOD = 9           # the ledger is FY26 to 31 March 2026: period 9
Q3_FY = 2026
CENT = Decimal('0.01')
D0 = Decimal('0')

# THE FY2023 ANNUAL TOWN REPORT PRINTS SCHOOL FUNDS BY NAME, NOT NUMBER. Which printed name is
# which fund is OURS. Each was matched on the name and then tested: for every fund with FY2023
# activity, the printed receipts and disbursements were compared with the journal's (most tie to
# the cent -- the tie column says which), and every fund also in the 31 March 2026 ledger was
# back-cast to 1 July 2022 and compared with the printed FORWARD. Two printed rows share the name
# 'FY23 #262', so those two carry the printed receipts as well.
#   2787: the journal names it FY22 Title IV; the report prints it as '- FY21'. Mapped on its
#         receipts (8,626.00, identical) and its back-cast forward (3,816.00, identical).
#   2793: the journal names it SCHOOL WATER IMPROVEMENT GRANT; the report prints the second
#         'FY23 #262' row with the same receipts (6,000.00) and disbursements (1,998.11).
AR23_NAME = {
    '1300': 'Recovery for Lost Books', '1301': 'Chapter 658 School Athletics',
    '1302': 'Adult Education', '1303': 'Summer School Program', '1305': 'After School Activities',
    '1306': 'School Facilities Use', '1308': 'School Choice', '1309': 'Insurance Recoveries - School',
    '1310': 'Greenthumb Revolving', '1311': 'School Gift Fund', '1312': 'Extended Day Revolving Fund',
    '1314': 'Vending Machine Revolving', '1315': 'Family Network Gift Fund',
    '1549': 'Technology for School Children Gift Fund', '2200': 'School Lunch',
    '2582': 'EECBG Energy Efficiency Grant', '2640': '50/50 Grant Sped Tuitions',
    '2649': 'Displaced Students - Puerto Rico', '2650': 'Underground Storage Tank Grant',
    '2666': 'Family & Community Grant #237 - FY23', '2681': 'Comprehensive School Health',
    '2686': 'FY22 Foundation Reserve', '2687': 'FY23 528 Grant',
    '2709': 'Regional Dissemination Grant', '2727': 'Title I #305 - FY15',
    '2742': 'Program Improvement Grant #274 - FY17', '2755': 'Title IV - Part A #309 - FY19',
    '2765': 'Teacher Quality #140 - FY20', '2766': 'Title I #305 - FY20',
    '2767': 'Title IV - Part A #309 - FY20', '2768': 'FY21 ESSER #113',
    '2769': 'Teacher Quality #140 - FY21', '2771': 'Title I #305 - FY21',
    '2772': 'FY21 School Reopening #102', '2773': 'PL 94-142 #240 - FY21',
    '2775': 'FY21 Sped Program Improvement #298', '2776': 'Program Improvement Grant #274',
    '2779': 'FY22 #117 Evidence Based Learning', '2780': 'FY22 ESSER II #115',
    '2781': 'FY22 ESSER III #119', '2782': 'FY22 ARP Idea #252', '2783': 'FY22 Idea ARP #264',
    '2785': 'PL 94-142 #240 - FY22', '2786': 'Title I #305 - FY22',
    '2787': 'Title IV - Part A #309 - FY21', '2788': 'Teacher Quality #140',
    '2789': 'Literacy Learning #719/730 - FY22', '2791': 'FY23 #240',
    '2792': ('FY23 #262', '13083.00'), '2793': ('FY23 #262', '6000.00'),
    '2794': 'Title I #305 - FY23', '2795': 'Title IV - Part A #309 - FY23',
    '2796': 'Title II # 140 - FY23', '2797': 'Literacy Learning #719/730 - FY23',
    '2798': 'FY23 #117 Evidence Based Learning', '2799': 'Deeper Learning #105 - FY23',
    '2903': 'BC/BS Healthy Choices', '2911': 'Tech Prep Consortium',
    '2912': 'Tufts University Heat Grant', '2914': 'Hach Scientific Foundation Grant',
    '2915': 'Emergency Connectivity Fund', '9002': 'Custodian Special Details',
}

FIELDS = ['fiscal_year', 'fund', 'fund_name', 'program', 'payer_group', 'payer_label',
          'received_outside', 'received_not_in_journal', 'transfers_in', 'transfers_out',
          'spent_actual', 'spent_with_owed', 'cost_moved_by_entry', 'net',
          'opening_balance', 'opening_source', 'closing_balance',
          'tie_expense', 'tie_revenue', 'tie_annual_report_flows', 'balance_check', 'year_open']


def fail(msg):
    raise SystemExit('build_fund_flows.py: REFUSED -- ' + msg)


def c(x):
    return Decimal(str(x)).quantize(CENT) if x not in (None, '') else D0


def usd(v):
    return '{:,.2f}'.format(v)


def compare(label, printed, ours):
    return ('%s ties (%s)' % (label, usd(ours)) if printed == ours
            else '%s differs: printed %s, ours %s' % (label, usd(printed), usd(ours)))


# ------------------------------------------------------------------ the journal, per fund-year

def journal_flows():
    A, L = J.accounts(), J.lines()
    # which journals post to more than one fund, on each side
    rev_funds, exp_funds = defaultdict(set), defaultdict(set)
    for r in L:
        a = A[r['account']]
        if r['posts_to'] == 'actual' and r['source'] in ('GEN', 'GRV') and r['amt']:
            if J.is_revenue(a):
                rev_funds[(r['fy'], r['journal'])].add(a['fund'])
            elif J.is_expense(a):
                exp_funds[(r['fy'], r['journal'])].add(a['fund'])
    f = defaultdict(lambda: defaultdict(Decimal))
    acct_rev = defaultdict(Decimal)          # (fy, account) -> journal actual revenue, as posted
    funds = {}
    for r in L:
        a = A[r['account']]
        if a['fund'] == '0100':
            continue
        funds.setdefault(a['fund'], a)
        k, v = (r['fy'], a['fund']), r['amt']
        if J.is_revenue(a):
            if r['posts_to'] != 'actual':
                continue                      # budget postings and stray orders: never receipts
            acct_rev[(r['fy'], r['account'])] += v
            moved = (a['object'].startswith('49')
                     or (r['source'] in ('GEN', 'GRV') and len(rev_funds[(r['fy'], r['journal'])]) > 1))
            if moved:
                f[k]['transfers_in' if v < 0 else 'transfers_out'] += abs(v)
            else:
                f[k]['received_outside'] -= v
        elif J.is_expense(a):
            if r['posts_to'] == 'actual':
                f[k]['spent_actual'] += v
                if r['source'] in ('GEN', 'GRV') and len(exp_funds[(r['fy'], r['journal'])]) > 1:
                    f[k]['cost_moved_by_entry'] += v
            if r['posts_to'] in J.SPENT:
                f[k]['spent_with_owed'] += v
            if r['posts_to'] == 'actual' and r['fy'] == Q3_FY and int(r['period']) <= Q3_PERIOD:
                f[k]['q3_spent'] += v
        if J.is_revenue(a) and r['fy'] == Q3_FY and int(r['period']) <= Q3_PERIOD:
            f[k]['q3_received'] -= v
    return f, acct_rev, funds


# ------------------------------------------------------------------ the period-13 report

def p13_ties(f, acct_rev):
    A = J.accounts()
    exp, rev, rev_funds = defaultdict(Decimal), defaultdict(Decimal), set()
    for r in csv.DictReader(open(P13, encoding='utf-8', newline='')):
        if r['report'] != 'special-school':
            continue
        fy, fund, v = int(r['fiscal_year']), r['fund'], c(r['ytd_expended'])
        if r['type'] == 'E':
            exp[(fy, fund)] += v
        elif r['type'] == 'R':
            rev[(fy, r['account'])] += v
            rev_funds.add((fy, fund))
    exp_funds = {k for k in exp}
    tie_e, tie_r, extra = {}, {}, defaultdict(lambda: [D0, 0])
    for k in set(f) | exp_funds:
        if k[1] == '0100':
            continue
        if k in exp_funds:
            ours = f[k]['spent_actual'] if k in f else D0
            if ours != exp[k]:
                fail('FY%d fund %s: the period-13 report prints expended %s, the journal sums %s'
                     % (k[0], k[1], usd(exp[k]), usd(ours)))
    for (fy, acct), printed in rev.items():
        ours = acct_rev.get((fy, acct), D0)
        if ours == printed:
            continue
        if acct in A:
            fail('FY%d account %s: the period-13 report prints revenue %s, the journal sums %s'
                 % (fy, acct, usd(printed), usd(ours)))
        fund = acct.split('-')[0]
        extra[(fy, fund)][0] -= printed      # printed credit -> money in
        extra[(fy, fund)][1] += 1
    for k in f:
        tie_e[k] = ('checked: equals the period-13 report\'s expended, %s' % usd(f[k]['spent_actual'])
                    if k in exp_funds else 'no check: the period-13 report does not print this fund')
        if k in rev_funds:
            if k in extra:
                tie_r[k] = ('checked on every account the journal holds; the report prints %d '
                            'account(s) the journal does not hold, %s, added as received_not_in_journal'
                            % (extra[k][1], usd(extra[k][0])))
            else:
                tie_r[k] = 'checked: every revenue account equals the period-13 report'
        else:
            tie_r[k] = 'no check: the period-13 report prints no revenue for this fund'
    for k in extra:
        if k not in f:
            fail('FY%d fund %s: printed revenue on accounts the journal does not hold, and the '
                 'fund has no journal line at all' % k)
    return tie_e, tie_r, {k: v[0] for k, v in extra.items()}


# ------------------------------------------------------------------ the balance documents

def q3_ledger():
    out = {}
    for r in csv.DictReader(open(Q3, encoding='utf-8', newline='')):
        fund = r['fund'].lstrip("'")
        row = dict(name=r['name'], balance=c(r['balance']), received=c(r['revenue']),
                   spent=c(r['salaries']) + c(r['expenditure']), encumbered=c(r['encumbered']))
        if fund in out and out[fund] != row:
            fail('fund %s appears twice in %s with different figures' % (fund, os.path.basename(Q3)))
        out[fund] = row
    for fund, r in out.items():
        r['forward'] = r['balance'] - r['received'] + r['spent']     # 1 July 2025
    return out


def ar23():
    rows = [r for r in csv.DictReader(open(AR_READ, encoding='utf-8', newline=''))
            if r['fy'] == '2023' and r['group'] == 'SCHOOL DEPARTMENT']
    out = {}
    for fund, key in AR23_NAME.items():
        name, rec = key if isinstance(key, tuple) else (key, None)
        hit = [r for r in rows if r['fund'] == name and (rec is None or r['receipts'] == rec)]
        if len(hit) != 1:
            fail('AR23_NAME[%s] = %r matches %d rows of the FY2023 schedule' % (fund, key, len(hit)))
        r = hit[0]
        out[fund] = dict(name=name, page=r['page'], document=r['document'], forward=c(r['forward']),
                         receipts=c(r['receipts']), disbursements=c(r['disbursements']),
                         carried=c(r['carried']))
    return out


def ar_balances():
    """fund -> printed balance, for the FY2024 edition (fund_balance) and the FY2025 edition
    (v1, headed 'Fund Balance 6/30/2025'). Keyed on the fund number the editions print."""
    out = {2024: {}, 2025: {}}
    for r in csv.DictReader(open(AR_FUNDS, encoding='utf-8', newline='')):
        fy = int(r['fy'])
        if fy not in out or not r['fund'][:4].isdigit():
            continue
        v = r['fund_balance'] if fy == 2024 else r['v1']
        if v:
            out[fy].setdefault(r['fund'][:4], (c(v), r['page'], r['fund']))
    return out


# ------------------------------------------------------------------ build

def build():
    years = list(J.YEARS)
    f, acct_rev, funds = journal_flows()
    for fund in funds:
        for y in years:
            f[(y, fund)]                       # every fund, every year: a zero is a row
    tie_e, tie_r, extra = p13_ties(f, acct_rev)
    q3, a23, arb = q3_ledger(), ar23(), ar_balances()
    gaps = []
    out = []
    for fund in sorted(funds):
        a = funds[fund]
        py = FB.payer(a)
        pg = BFB.payer_group(py)
        nets = {}
        for y in years:
            g = f[(y, fund)]
            g['received_not_in_journal'] = extra.get((y, fund), D0)
            nets[y] = (g['received_outside'] + g['received_not_in_journal'] + g['transfers_in']
                       - g['transfers_out'] - g['spent_actual'])
        first = years[0]
        if fund in q3:
            opening = q3[fund]['forward'] - sum(nets[y] for y in years if y < Q3_FY)
            src = ('derived: the Town\'s special revenue ledger at 31 March 2026 '
                   '(school-special-revenue-fy26-q3.csv, fund %s) prints balance %s; less its '
                   'FY2026 revenue %s plus its FY2026 spending %s = %s at 1 July 2025; less this '
                   'file\'s FY2023-FY2025 net' % (fund, usd(q3[fund]['balance']),
                                                  usd(q3[fund]['received']), usd(q3[fund]['spent']),
                                                  usd(q3[fund]['forward'])))
            if fund in a23:
                src += '; ' + compare('FY2023 annual town report p%s %r FORWARD 7/1/2022'
                                      % (a23[fund]['page'], a23[fund]['name']),
                                      a23[fund]['forward'], opening)
        elif fund in a23:
            opening = a23[fund]['forward']
            src = ('printed: FY2023 annual town report (%s) p%s, %r, FORWARD 7/1/2022 = %s'
                   % (a23[fund]['document'], a23[fund]['page'], a23[fund]['name'],
                      usd(opening)))
        else:
            opening, src = None, ('not established: the fund is in neither the FY2023 annual '
                                  'report\'s schedule nor the 31 March 2026 ledger')
            gaps.append(fund)
        bal = opening
        for y in years:
            g = f[(y, fund)]
            close = None if bal is None else bal + nets[y]
            ar_flow = 'no check'
            if y == 2023 and fund in a23:
                p = a23[fund]
                ar_flow = '; '.join([
                    compare('receipts', p['receipts'], g['received_outside']
                            + g['received_not_in_journal'] + g['transfers_in'] - g['transfers_out']),
                    compare('disbursements', p['disbursements'], g['spent_actual'])])
            checks = []
            if close is not None:
                if y == 2023 and fund in a23:
                    checks.append(compare('FY2023 annual town report carried 6/30/2023',
                                          a23[fund]['carried'], close))
                if y in arb and fund in arb[y]:
                    v, page, nm = arb[y][fund]
                    checks.append(compare('FY%d annual town report p%s %r balance' % (y, page, nm),
                                          v, close))
                if y == Q3_FY - 1 and fund in q3:
                    checks.append('31 March 2026 ledger: n/a, the opening balance is derived from it')
                if y == 2025 and fund not in q3 and fund in a23:
                    checks.append('31 March 2026 ledger: fund not listed')
            if y == Q3_FY and fund in q3:
                checks.append(compare('31 March 2026 ledger FY2026 revenue', q3[fund]['received'],
                                      g['q3_received']))
                checks.append(compare('31 March 2026 ledger FY2026 spending', q3[fund]['spent'],
                                      g['q3_spent']))
            if y == J.OPEN_FY:
                checks.append('FY%d is still open: no year-end balance is printed yet' % y)
            out.append(dict(
                fiscal_year=y, fund=fund, fund_name=a['fund_name'].strip(),
                program=J.grant_program(a), payer_group=pg, payer_label=dict(BFB.PAYERS)[pg],
                received_outside=g['received_outside'],
                received_not_in_journal=g['received_not_in_journal'],
                transfers_in=g['transfers_in'], transfers_out=g['transfers_out'],
                spent_actual=g['spent_actual'], spent_with_owed=g['spent_with_owed'],
                cost_moved_by_entry=g['cost_moved_by_entry'], net=nets[y],
                opening_balance='' if bal is None else bal,
                opening_source=src if y == first else (
                    'carried: the FY%d closing balance' % (y - 1) if bal is not None else
                    'not established'),
                closing_balance='' if close is None else close,
                tie_expense=tie_e[(y, fund)], tie_revenue=tie_r[(y, fund)],
                tie_annual_report_flows=ar_flow,
                balance_check='; '.join(checks) or 'no check',
                year_open='yes' if y == J.OPEN_FY else 'no'))
            bal = close
    return out, gaps


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: (('%.2f' % v) if isinstance(v, Decimal) else v) for k, v in r.items()})
    return buf.getvalue()


def summary(rows):
    by = defaultdict(lambda: defaultdict(Decimal))
    for r in rows:
        for k in ('received_outside', 'received_not_in_journal', 'transfers_in', 'transfers_out',
                  'spent_actual', 'net'):
            by[(r['payer_group'], r['fiscal_year'])][k] += r[k]
            by[('ALL', r['fiscal_year'])][k] += r[k]
    print('%-6s %4s %14s %14s %14s %14s' % ('group', 'FY', 'received', 'transfers net',
                                             'spent', 'net'))
    for (g, y), d in sorted(by.items(), key=lambda kv: (kv[0][0] == 'ALL', kv[0])):
        print('%-6s %4d %14s %14s %14s %14s' % (
            g, y, usd(d['received_outside'] + d['received_not_in_journal']),
            usd(d['transfers_in'] - d['transfers_out']), usd(d['spent_actual']), usd(d['net'])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    rows, gaps = build()
    text = render(rows)
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8', newline='').read() if os.path.exists(OUT) else ''
        if have != text:
            print('STALE -- %s is not what the journal now produces. Run scripts/build_fund_flows.py.'
                  % rel)
            return 1
        print('ok -- %s reproduces' % rel)
        return 0
    with open(OUT + '.tmp', 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    os.replace(OUT + '.tmp', OUT)
    print('wrote %s -- %d rows, %d funds; opening balance not established for %d: %s'
          % (rel, len(rows), len({r['fund'] for r in rows}), len(gaps), ', '.join(gaps)))
    summary(rows)
    return 0


if __name__ == '__main__':
    sys.exit(main())
