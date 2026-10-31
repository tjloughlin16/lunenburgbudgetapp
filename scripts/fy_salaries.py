"""SALARIES PAID FROM OUTSIDE THE GENERAL FUND, ONE YEAR (fy-breakdown). TJ, 28 October 2026: "we
must now have the information if a non-general fund source paid some portion or all of a salary
or salary LINE (school line). I'd like to create yet another section to show 'salaries paid
from outside the general fund'."

The FY breakdown's lens on what two pages already total across four years
(/school-all-funds/salaries-from-grants-and-fees by fund, /school-all-funds/pay-moved-between-funds by
entry): ONE year, read two ways, from the same placements the rest of the page uses.

  BY SCHOOL SALARY LINE. Measured: a year-end journal entry that took pay off a school line and
  put it on a grant or fee fund names both (fy_breakdown rule a, `moved_off`), and one that
  moved pay back names both too (`moved_on`). So for each school salary line: what the school
  budget paid, what was re-charged off it and to which funds, what came back, and the share of
  the line's pay another fund carried in the end.

  BY FUND. Every other fund's pay in the year, by where the model placed it: moved by journal
  entry to or from a school line; booked to the same kind of work as a school line (function
  code, OUR match, to a category and never one line); or on no school line. Payroll carries no
  payee and a grant's salary accounts name a kind of work, never a post, so a grant's own
  payroll can never be pinned to one school line. That is the ledger's limit, said beside it.

PAY is build_pay_by_fund_topics.is_pay (object 51xxxx less the two that are not wages), one
copy. OTHER FUNDS are every fund but 0100. Each year's other-fund pay ties to that page's own
model, and the share of all school pay to the one it publishes, or this refuses.
"""
import re
import statistics
from collections import defaultdict
from decimal import Decimal

import journal as J
from build_pay_by_fund_topics import is_pay, model as pay_model

D0 = Decimal(0)
GF = '0100'
RUN = ('PRJ', 'PRH')
COLS = ('run', 'moved', 'adj')
# where the model put pay-run pay, for the fund's own breakdown (kinds of work are named by category)
WHERE_RUN = {'none': 'No school line', 'capital': 'A capital article', 'payee': 'No school line',
             'between': 'Moved between two other funds'}


# PAID EVERY PAY PERIOD (TJ, 28 October 2026, after the athletic fee fund's pay was found to hold
# a steady slice every run, re-filed once as principal pay: "i want to make sure our fy breakdown
# analysis catches things like that automatically ... to identify that payment structure"). An
# account outside the general fund that pays a steady amount run after run is what a POSITION
# looks like in a payroll ledger that never names people; season-end stipends are lumps. OUR
# thresholds, said on the page: at least STEADY_RUNS runs within STEADY_BAND of the account's own
# median run.
STEADY_RUNS, STEADY_BAND = 8, Decimal('0.25')


def warrant(r):
    m_ = re.search(r'WARRANT=(\S+)', r['description'])
    return m_.group(1) if m_ else r['journal']


def run_no(w):
    m_ = re.match(r'(\d+)P', w)
    return int(m_.group(1)) if m_ else 99


def regular(fy, A, L, names, fund_label, T, long_date):
    per = defaultdict(lambda: defaultdict(Decimal))
    for r in L:
        if r['fy'] != fy or r['source'] not in RUN or r['posts_to'] != 'actual':
            continue
        if r['fund'] != GF and is_pay(A[r['account']]):
            per[r['account']][warrant(r)] += r['amt']
    # every adjusting entry in the year, for the moves off each account
    adj = defaultdict(list)
    for r in L:
        if r['fy'] == fy and r['source'] in ('GEN', 'GRV') and r['posts_to'] == 'actual':
            adj[r['journal']].append(r)
    out = []
    for a, d in per.items():
        pos = [v for v in d.values() if v > 0]
        if len(pos) < STEADY_RUNS:
            continue
        med = Decimal(statistics.median(pos))
        steady = [v for v in pos if abs(v - med) <= STEADY_BAND * med]
        if len(steady) < STEADY_RUNS:
            continue
        total = sum(d.values(), D0)
        moves = []
        for j, rs in adj.items():
            mine = sum((r['amt'] for r in rs if r['account'] == a), D0)
            if not round(mine, 2):
                continue
            for r in rs:
                if r['fund'] == GF and is_pay(A[r['account']]) and (r['amt'] > 0) == (mine < 0) and round(r['amt'], 2):
                    moves.append(dict(date=T.lit(long_date(r['effective_date'])), memo=T.lit(r['description'].strip() or 'no memo'),
                                      line=T.lit(names.get(r['account'], r['account_description'].strip().title())),
                                      dir='to' if mine < 0 else 'from', text=T.usd(abs(r['amt'])), v=round(float(abs(r['amt'])), 2)))
        acct = A[a]
        out.append(dict(
            name=T.lit(fund_label(acct['fund'], A)), account=T.lit(acct['org_name'].strip().title()),
            n=dict(steady=len(steady), typical=round(float(med), 2), steady_total=round(float(sum(steady)), 2),
                   other=round(float(total - sum(steady)), 2), total=round(float(total), 2)),
            t=dict(steady=T.lit(str(len(steady))), typical=T.usd(med), steady_total=T.usd(sum(steady)),
                   other=T.usd(total - sum(steady)) if round(total - sum(steady), 2) else '', total=T.usd(total)),
            runs=[[T.lit(w), round(float(v), 2)] for w, v in sorted(d.items(), key=lambda kv: (run_no(kv[0]), kv[0])) if round(v, 2)],
            moves=sorted(moves, key=lambda x: -x['v'])))
    out.sort(key=lambda x: -x['n']['steady_total'])
    return out


def data(m, T, line_name, fund_label, cat_label, long_date, fail):
    A = J.accounts()
    L = J.lines()
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}
    pm = pay_model()
    years = []
    for fy in J.YEARS:
        # ---- by school salary line: what the journal entries moved, both ends named
        lines = []
        for r in m['rows']:
            if r['fy'] != fy or not r['account'] or not is_pay(A[r['account']]):
                continue
            if not (r['moved_off'] or r['moved_on']):
                continue
            before = r['gf_spent'] + r['moved_off'] - r['moved_on']
            funds = defaultdict(Decimal)
            moves = []
            for mv in r['fund_moves']:
                for py, v in mv['payers'].items():
                    funds[py] += v if mv['amount'] < 0 else -v
                moves.append(dict(date=T.lit(long_date(mv['date'])), memo=T.lit(mv['memo'] or 'no memo'),
                                  dir='off' if mv['amount'] < 0 else 'on', text=T.usd(abs(mv['amount'])),
                                  funds=T.lit(', '.join(sorted(mv['payers'])))))
            net = r['moved_off'] - r['moved_on']
            # % KEPT, the payee table's measure (TJ, 28 October 2026: "is this column really just
            # 'out of the general fund' in the same way"): what the general fund carried in the end
            # over what it paid first. Over 100 is pay it took on from other funds
            share = (100 * r['gf_spent'] / before) if before > 0 else None
            lines.append(dict(
                line=T.lit(line_name(r)), cat=cat_label[r['category']],
                n=dict(before=round(float(before), 2), off=round(float(r['moved_off']), 2),
                       on=round(float(r['moved_on']), 2), kept=round(float(r['gf_spent']), 2),
                       share=None if share is None else round(float(share), 1)),
                t=dict(before=T.usd(before), off=T.usd(r['moved_off']) if r['moved_off'] else '',
                       on=T.usd(r['moved_on']) if r['moved_on'] else '', kept=T.usd(r['gf_spent']),
                       share='' if share is None else T.lit('%d%%' % Decimal(share).quantize(Decimal(1))),
                       dir='' if share is None or not net else 'off' if net > 0 else 'on'),
                funds=[dict(name=T.lit(k), text=T.usd(abs(v)), dir='off' if v > 0 else 'on')
                       for k, v in sorted(funds.items(), key=lambda kv: -abs(kv[1])) if round(v, 2)],
                moves=moves))
        lines.sort(key=lambda x: -abs(x['n']['off'] - x['n']['on']))

        # ---- by fund: every other fund's pay, by HOW IT GOT THERE (TJ, 28 October 2026: "its
        # unclear if these payments paid back the general fund, or the salaries were not
        # originally put onto the general fund"). Three ways, and the books tell them apart:
        #   run    paid by the fund in its own pay run (PRJ/PRH): never on the school budget
        #   moved  moved in or out by journal entry, net: re-charged from a school line (the
        #          school budget paid, the entry moved the expense, so the fund covers it), moved
        #          back onto one, or passed between two other funds
        #   adj    other entries on the fund's pay accounts that are not moves: accruals,
        #         reversals, an invoice on a salary account
        col = defaultdict(lambda: defaultdict(Decimal))
        kinds = defaultdict(lambda: defaultdict(Decimal))
        nets = defaultdict(Decimal)
        for (y, f), rs in m['src_rows'].items():
            if y != fy or f == GF:
                continue
            for r, kind, dest in rs:
                if not is_pay(A[r['account']]):
                    continue
                if kind == 'journal':
                    nets[(f, dest)] += r['amt']
                elif r['source'] in RUN:
                    col[f]['run'] += r['amt']
                    kinds[f][cat_label[dest] if kind == 'function' else WHERE_RUN.get(kind, 'No school line')] += r['amt']
                else:
                    col[f]['adj'] += r['amt']
        # ONE NET PER FUND. An entry that moves pay between a school line and several funds is
        # shared over those funds by the model in proportion to all they received, pay or not,
        # so a fund-level "came off the school budget" would be our sharing. The school side is
        # exact (the lines, above), and the summary carries it.
        for (f, _), v in nets.items():
            col[f]['moved'] += v
        funds = []
        for f, c in col.items():
            tot = sum(c.values(), D0)
            if not any(round(v, 2) for v in c.values()):
                continue
            funds.append(dict(
                name=T.lit(fund_label(f, A)),
                n={k: round(float(c[k]), 2) for k in COLS} | {'total': round(float(tot), 2)},
                t={k: (T.usd(c[k]) if round(c[k], 2) else '') for k in COLS} | {'total': T.usd(tot)},
                kinds=[dict(name=k, text=T.usd(v)) for k, v in sorted(kinds[f].items(), key=lambda kv: -kv[1]) if round(v, 2)]))
        funds.sort(key=lambda x: -x['n']['total'])
        out = sum((sum(c.values(), D0) for c in col.values()), D0)

        # ---- the two ties: the pay page's own model, by a different route
        theirs = sum(v for (y, g), v in pm['pay'].items() if y == fy and g != 'General fund')
        gf_other = sum((r['amt'] for (y, f), rs in m['src_rows'].items() if y == fy and f == GF
                        for r, _, _ in rs if is_pay(A[r['account']])), D0)
        if abs(float(out) - theirs) > 0.5:
            fail('FY%d: other funds’ pay is %s here and %.2f on the pay page' % (fy, out, theirs))
        all_pay = sum(v for (y, g), v in pm['pay'].items() if y == fy)
        share = 100 * float(out) / all_pay if all_pay else 0
        sums = {k: sum((c[k] for c in col.values()), D0) for k in COLS}
        if sum(sums.values(), D0) != out:
            fail('FY%d: the ways in do not sum to the funds’ pay' % fy)
        # the school side, exact: what the year's entries took off school salary lines and put
        # back on them; whatever else the funds' moves net to passed between other funds
        took = sum((Decimal(str(l['n']['off'])) for l in lines), D0)
        gave = sum((Decimal(str(l['n']['on'])) for l in lines), D0)
        sums = dict(run=sums['run'], took=took, gave=gave, between=sums['moved'] - took + gave, adj=sums['adj'])
        years.append(dict(
            fy=T.fy(fy), lines=lines, funds=funds,
            total=T.usd(out), share=T.lit('%.1f%%' % share),
            sums={k: (T.usd(abs(v)) if k in ('took', 'gave') else T.usd(v)) for k, v in sums.items()},
            n_lines=len(lines), gf_outside=T.usd(gf_other) if round(gf_other, 2) else '',
            regular=regular(fy, A, L, names, fund_label, T, long_date)))
    return years
