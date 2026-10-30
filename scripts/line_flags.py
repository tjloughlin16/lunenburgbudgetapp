#!/usr/bin/env python3
"""THE THREE LINE FLAGS -- underfunded, overbudgeted, restarted high -- in ONE place, for the
two pages that show them (TJ, 29 October 2026, notes/HANDOFF-FY-BREAKDOWN.md, "TJ DECIDED"
item 4: "one question per page: the year's story there, the pattern across years here"):

  * build_fy_breakdown.py: the picked year's flagged lines (block `fy-flags`) and a flag filter
    on its every-line table, journal years only;
  * build_budget_against_actual.py: every line, every year, FY2018 on, as a grid.

TWO RECORDS, NEVER MERGED INTO ONE LINE-YEAR.
  * FY2023 on: the school JOURNAL, the FY breakdown's model (`fy_breakdown.model()`), every line
    tied to the Town's period-13 report.
  * FY2018-FY2022: the Finance Committee's WORKBOOK (`gl-history.csv`, extract_gl_history.py),
    pasted together from per-year MUNIS exports -- `stated` evidence (rule 13a), labelled so
    wherever it is shown. `workbook_lines()` REFUSES unless, in every year both hold, every
    school line's vote, transfers, final budget and spending read off the workbook equal the
    journal's to the cent.

SPENT IS PAYMENTS PLUS ORDERS STILL OWED (the site's footing). The workbook's ACTUAL is payments
only: measured, on every line FY2023 and FY2024, it is the journal's spending less the orders
carried into the next year. So a workbook year's spending is its ACTUAL plus the next year's
orders carried in, which the workbook prints as REVISED less ORIGINAL less the two TRANSFERS
columns -- and the refusal above checks exactly that construction, line by line.

THE FLAGS are measured rules; their thresholds are OURS and printed on both pages:
  * UNDERFUNDED: transfers IN during the year, and the line spent past what was voted plus the
    orders carried in with their own money, by at least FLOOR and SHARE of the vote.
  * OVERBUDGETED: the vote plus carried orders exceeded spending by at least FLOOR and SHARE of
    the vote, and budget was moved OUT or left at year end.
  * RESTARTED HIGH: this year's VOTE exceeds last year's SPENDING by at least FLOOR and SHARE of
    that spending, the same account, the same record. A line on a new account has no prior year
    and is never flagged; one whose account spent nothing, or under half its final budget, the
    year before is flagged and MARKED (rule 6). In journal years last year's spending is read
    BEFORE re-charges to other funds; the workbook cannot separate re-charges, so in workbook
    years it is after them, and the page says so.
Rule 7: a flag is a measurement. Why a line was set where it was is not.
"""
import collections
import csv
import os
from decimal import Decimal

import conclusions as C
import build_school_surplus as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GL = os.path.join(ROOT, 'sources', 'data', 'gl-history.csv')
D0 = Decimal(0)

FLOOR = Decimal('5000')        # OURS: no flag under this many dollars (the FY breakdown's ADJ_MIN)
SHARE = Decimal('0.10')        # OURS: and at least this share of the vote (of prior spending, restarted)
THIN = Decimal('0.5')         # OURS: a prior year spending under half its final budget is marked (rule 6)
KEYS = ('under', 'over', 'restart')
WORKBOOK_YEARS = (2018, 2019, 2020, 2021, 2022)
SAL = {c[0] for c in S.CATEGORIES if c[3].startswith('salary lines')}


def fail(msg):
    raise SystemExit('line_flags: ' + msg)


def big(v, base):
    return v >= FLOOR and (base <= 0 or v >= SHARE * base)


def line_name(r):
    org = (r.get('org') or '').title()
    d = r['description'].title()
    return d if not org or org.lower() == d.lower() else '%s · %s' % (d, org)


def flag(r, prior, before_recharge):
    """One line-year: its final budget, its gap against its own money, and its flags.
    `r`: voted, transfers, carried_budget, gf_spent, left (and moved_off/moved_on when the
    record has them). `prior`: the same account's row the year before, in the same record."""
    budget = r['voted'] + r['transfers'] + r['carried_budget']
    if budget - r['gf_spent'] != r['left']:
        fail('FY%d %s: budget less spent is not left' % (r['fy'], r['account']))
    gap = r['gf_spent'] - (r['voted'] + r['carried_budget'])
    x = dict(fy=r['fy'], r=r, budget=budget, gap=gap, flags={})
    if r['transfers'] > 0 and big(gap, r['voted']):
        cov = min(r['transfers'], gap)
        x['flags']['under'] = dict(gap=gap, covered=cov, uncovered=gap - cov)
    if (r['transfers'] < 0 or r['left'] > 0) and big(-gap, r['voted']):
        x['flags']['over'] = dict(unspent=-gap, out=max(-r['transfers'], D0), left=max(r['left'], D0))
    if prior is not None:
        # LAST YEAR'S SPENDING ON THE LINE, BEFORE RE-CHARGES where the record shows them: a bill
        # the school budget paid and a journal entry later put on a grant was still this line's
        # spending (FY2024 special-education paras: -$157,886 against the after-re-charge figure).
        rc = (prior['moved_off'] - prior['moved_on']) if before_recharge else D0
        ps = prior['gf_spent'] + rc
        pb = prior['voted'] + prior['transfers'] + prior['carried_budget']
        x['prior'] = dict(spent=ps, budget=pb, transfers=prior['transfers'], voted=prior['voted'], recharged=rc)
        if big(r['voted'] - ps, ps):
            x['flags']['restart'] = dict(
                over=r['voted'] - ps, prior_spent=ps, prior_budget=pb, recharged=rc,
                cut=prior['transfers'] < 0, above_budget=r['voted'] > pb,
                # rule 6: an account that spent nothing, or under half its final budget, the year
                # before may have had its cost moved to another account. Marked, not dropped.
                thin=ps <= 0 or (pb > 0 and ps < THIN * pb))
    rc = r.get('moved_off', D0) - r.get('moved_on', D0)
    for k in ('under', 'over'):
        if k in x['flags']:
            x['flags'][k]['recharged'] = rc
    x['usable'] = (r['voted'] >= 10_000 and r['gf_spent'] >= 1_000
                   and Decimal('0.02') <= r['gf_spent'] / r['voted'] <= 20)
    x['sal'] = r['category'] in SAL
    return x


def journal_lines(m):
    """Every school line, every journal year, with the three flags. Lines by account."""
    import build_fy_breakdown as BFB   # it imports this module; keep the import one-way at load
    by = collections.defaultdict(dict)
    for r in m['rows']:
        if r['account']:
            by[r['account']][r['fy']] = r
    out = {}
    for fy in BFB.YEARS():
        rows = []
        for acct, ys in by.items():
            r = ys.get(fy)
            if not r or all(round(v) == 0 for v in (r['voted'], r['transfers'], r['carried_budget'], r['gf_spent'])):
                continue
            rows.append(flag(r, ys.get(fy - 1), True))
        out[fy] = rows
    return out, by


# ---------------------------------------------------------------- the Finance Committee workbook
def _gl():
    g = {}
    for r in csv.DictReader(open(GL, encoding='utf-8')):
        if r['sheet'] == 'general_fund' and '-3-300-' in r['account']:
            g[(r['account'], int(r['fiscal_year']))] = r
    return g


def workbook_lines(JL, by):
    """FY2017-FY2022 school lines read off the workbook, on the journal's footing, flagged
    FY2018-FY2022. Refuses unless every overlap year's every line equals the journal's."""
    gl = _gl()
    D = lambda s: Decimal(s or '0')

    def carried(a, fy):
        g = gl.get((a, fy))
        return D0 if g is None else D(g['revised']) - D(g['original']) - D(g['transfers_1']) - D(g['transfers_2'])

    def row(a, fy):
        g = gl.get((a, fy))
        if g is None or g['actual_is_partial'] == 'true' or (a, fy + 1) not in gl:
            return None
        j = next(iter(by.get(a, {}).values()), None)
        voted, tr = D(g['original']), D(g['transfers_1']) + D(g['transfers_2'])
        cb = D(g['revised']) - voted - tr
        spent = D(g['actual']) + carried(a, fy + 1)
        return dict(fy=fy, account=a, voted=voted, transfers=tr, carried_budget=cb, gf_spent=spent,
                    left=D(g['revised']) - spent, moved_off=D0, moved_on=D0, moves_in=[],
                    description=j['description'] if j else g['org_desc'], org=j['org'] if j else '',
                    category=j['category'] if j else S.category_of(dict(account=a, obj=a.split('-')[-1])))
    # THE TIE: in every year both records hold, every journal line read off the workbook.
    overlap = sorted(fy for fy in JL if any(y == fy for (_, y) in gl) and
                     not any(g['actual_is_partial'] == 'true' for (a, y), g in gl.items() if y == fy))
    tied = []
    for fy in overlap:
        for x in JL[fy]:
            r, w = x['r'], row(x['r']['account'], fy)
            if w is None:
                fail('FY%d %s: in the journal, not in the Finance Committee workbook' % (fy, r['account']))
            for k in ('voted', 'transfers', 'carried_budget', 'gf_spent'):
                if w[k] != r[k]:
                    fail('FY%d %s: the workbook reads %s %s, the journal %s'
                         % (fy, r['account'], k, w[k], r[k]))
        tied.append((fy, len(JL[fy])))
    if len(tied) < 2:
        fail('fewer than two years tie the workbook to the journal: %s' % tied)
    out = {}
    accts = {a for (a, _) in gl}
    for fy in WORKBOOK_YEARS:
        rows = []
        for a in sorted(accts):
            w = row(a, fy)
            if w is None or all(round(w[k]) == 0 for k in ('voted', 'transfers', 'carried_budget', 'gf_spent')):
                continue
            p = row(a, fy - 1)
            rows.append(flag(w, p, False))
        out[fy] = rows
    return out, tied


def workbook_totals():
    """{fy: (budget, spent)} for the whole school general fund, every complete workbook year,
    on the journal's footing (spent = ACTUAL plus the next year's orders carried in)."""
    gl = _gl()
    D = lambda s: Decimal(s or '0')
    tot = collections.defaultdict(lambda: [D0, D0])
    years = {y for (_, y) in gl}
    partial = {y for (_, y), g in gl.items() if g['actual_is_partial'] == 'true'}
    for (a, fy), g in gl.items():
        if fy in partial or fy + 1 not in years:
            continue
        n = gl.get((a, fy + 1))
        cin = D0 if n is None else D(n['revised']) - D(n['original']) - D(n['transfers_1']) - D(n['transfers_2'])
        tot[fy][0] += D(g['revised'])
        tot[fy][1] += D(g['actual']) + cin
    return {fy: tuple(v) for fy, v in sorted(tot.items())}


# ---------------------------------------------------------------- what the page says
def _num(T, n):
    t = C.num(n)
    T.figures.add(t)
    return t


def flag_text(T):
    fl_ = T.usd(FLOOR)
    sh = C.pct(float(SHARE) * 100, 0)
    T.figures.add(sh)
    return dict(
        under=dict(name='Underfunded', rule=T.lit(
            'Budget was transferred in during the year, and the line spent past its vote and any '
            'orders carried in by at least %s and %s of the vote.' % (fl_, sh)),
            means='The vote was below what the line cost that year; transfers from other lines closed '
                  'some or all of the gap.'),
        over=dict(name='Overbudgeted', rule=T.lit(
            'The vote and any orders carried in came to at least %s and %s of the vote more than '
            'the line spent, and budget was moved out or left at year end.' % (fl_, sh)),
            means='The line was voted more than it spent; the rest went to other lines or into the surplus.'),
        restart=dict(name='Restarted high', rule=T.lit(
            'This year’s vote is at least %s and %s above what the same account spent the year '
            'before, counting bills later re-charged to other funds.' % (fl_, sh)),
            means='The new budget started above what the line had just cost. Compared with the prior '
                  'year’s spending and its final budget; both are shown.'),
        ours=T.lit('Thresholds of ours: %s and %s, the same for all three flags.' % (fl_, sh)),
        why='A flag is a measurement. Why a line was set where it was is not shown by the books: a '
            'vacancy, a placement, a price or a plan can each produce it.')


def signed(T, v):
    import build_fy_breakdown as BFB
    return BFB.signed(T, v)


def moves_of(T, r, names):
    import build_fy_breakdown as BFB
    return [dict(date=T.lit(BFB.long_date(x['date'])), memo=T.lit(x['memo'].strip() or 'no memo'),
                 v=signed(T, x['amount']),
                 others=[T.lit(names.get(o['account'], o['description'].strip().title()))
                         for o in x.get('others', [])][:6])
            for x in sorted(r['moves_in'], key=lambda x: x['date'])]


def year_block(T, JL):
    """The FY breakdown's block: per journal year, ONLY the flagged lines, with their figures
    and the transfers behind them. Every string formatted here (rule 2)."""
    names = {x['r']['account']: line_name(x['r']) for rows in JL.values() for x in rows}
    years = []
    for fy in sorted(JL):
        rows = []
        for x in sorted(JL[fy], key=lambda x: line_name(x['r'])):
            fx, r = x['flags'], x['r']
            if not fx:
                continue
            row = dict(name=T.lit(line_name(r)), account=T.lit(r['account']), cat=S.CAT_LABEL[r['category']],
                       voted=T.usd(r['voted']), spent=T.usd(r['gf_spent']), f=sorted(fx))
            rc = lambda v: signed(T, -v) if round(v) else ''
            if 'under' in fx:
                u = fx['under']
                row['under'] = dict(gap=T.usd(u['gap']), covered=T.usd(u['covered']),
                                    uncovered=T.usd(u['uncovered']), n=round(float(u['gap']), 2),
                                    recharged=rc(u['recharged']))
            if 'over' in fx:
                o = fx['over']
                row['over'] = dict(unspent=T.usd(o['unspent']), out=T.usd(o['out']), left=T.usd(o['left']),
                                   n=round(float(o['unspent']), 2), recharged=rc(o['recharged']))
            if 'restart' in fx:
                h = fx['restart']
                row['restart'] = dict(over=T.usd(h['over']), prior_spent=T.usd(h['prior_spent']),
                                      prior_budget=T.usd(h['prior_budget']), cut=h['cut'],
                                      above_budget=h['above_budget'], thin=h['thin'],
                                      n=round(float(h['over']), 2))
            if r['moves_in']:
                row['moves'] = moves_of(T, r, names)
            rows.append(row)
        new = sum(1 for x in JL[fy] if 'prior' not in x and x['r']['voted'] > 0)
        years.append(dict(
            fy=T.fy(fy), rows=rows,
            counts={k: _num(T, sum(1 for x in JL[fy] if k in x['flags'])) for k in KEYS},
            lines=_num(T, len(JL[fy])),
            new=T.lit('%s lines on an account the year before did not have: never flagged '
                      'restarted high.' % _num(T, new)) if fy - 1 in JL else None,
            no_restart=T.lit('Not shown for %s: %s is not in the school journal, so no line has a '
                             'year before it in the same record.' % (T.fy(fy), T.fy(fy - 1)))
            if fy - 1 not in JL else None))
    return dict(years=years, flags=flag_text(T), text=dict(
        gap='Spent past the vote', covered='Covered by transfers', uncovered='Not covered',
        unspent='Not spent', moved_out='Moved out', left_end='Left at year end',
        over_by='Vote above last year’s spending', prior_spent='Spent the year before',
        prior_budget='Final budget the year before',
        cut='Budget was moved off it the year before',
        above='Above last year’s final budget too', below='At or below last year’s final budget',
        thin=T.lit('Spent under half its final budget the year before (a mark of ours): its history '
                   'may show the cost moved to another account.'),
        recharged='Re-charged to other funds after the school budget paid',
        transfers='Transfers', other_side='with', voted='Voted', spent='Spent',
        lines_n='lines', flagged='flagged', of='of',
        show_all='Show every flagged line', show_fewer='Show the largest',
        across=T.lit('Every line in every year since %s, flagged the same way: School lines against '
                     'budget.' % T.fy(min(WORKBOOK_YEARS))),
        across_href='/school-all-funds/budget-against-actual'))


def flags_by_line(JL):
    """{fy: {account: [flag keys]}}, for the every-line table's filter."""
    return {fy: {x['r']['account']: sorted(x['flags']) for x in rows if x['flags']} for fy, rows in JL.items()}
