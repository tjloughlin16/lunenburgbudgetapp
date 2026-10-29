#!/usr/bin/env python3
"""SCHOOL BUDGET AGAINST ACTUAL, LINE BY LINE: one page that reads every school line's vote
against what it spent, across every year the archive can compare, then one year at a time.

    python3 scripts/build_budget_against_actual.py           # write the topic payload
    python3 scripts/build_budget_against_actual.py --check   # fail if it would change

TJ, 29 October 2026 (notes/HANDOFF-FY-BREAKDOWN.md, item 3): *"map over time the same info
thats in the fy breakdowns, but focus entirely on the school lines that are over or under
budget ... flag this as 'underfunded' ... or the money moved elsewhere ('overbudgeted') ... if
a budget starts significantly higher than the previous year spending, that should be
flagged."* Agreed the same day: ONE report, to replace `sources/analyses/budget-vs-actual.md`
as the page once TJ has seen it, degrading gracefully by evidence.

TWO SOURCES, NEVER MERGED INTO ONE NUMBER.
  * FY2018-FY2022: the district's BUDGET DOCUMENTS (`line-history.csv`, built by
    `extract_line_history.py`): a budget column and an actual column the district printed.
    Read with the August report's own rules -- `usable()`, `THIN_YEARS` and the groups are
    copied from `verify_budget_vs_actual.py`, and `book_years()` REFUSES unless its figures
    equal that report's payload (`fy28/public/data/budget-vs-actual.json`) to the dollar.
  * FY2023-FY2026: the school JOURNAL (MUNIS), the FY breakdown's own model
    (`fy_breakdown.model()`), whose every line ties to the Town's period-13 report
    (`verify_fy_breakdown.py`). Spent is payments plus orders still owed (the site's footing).

THE THREE FLAGS are measured rules; their thresholds are OURS and printed on the page:
  * UNDERFUNDED: transfers IN during the year, and the line spent past what was voted plus the
    orders carried in with their own money, by at least FLOOR and SHARE of the vote.
  * OVERBUDGETED: the vote plus carried orders exceeded spending by at least FLOOR and SHARE of
    the vote, and budget was moved OUT or left at year end.
  * RESTARTED HIGH: this year's VOTE exceeds last year's SPENDING by at least FLOOR and SHARE of
    that spending. Lines are matched by ACCOUNT NUMBER: a line on a new account has no prior
    year and is never flagged; one whose account spent nothing, or under half its final budget, the year
    before is flagged and MARKED, because a line emptied and replaced under another account
    looks the same (rule 6). Last year's spending is read BEFORE re-charges to other funds.
Rule 7: a flag is a measurement. Why a line was set where it was is not, and the page says so.
Rule 1: this is an analysis of budget against actual; nothing here feeds a projection.
"""
import argparse
import collections
import csv
import importlib.util
import json
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402
import journal as J  # noqa: E402
import build_school_surplus as S  # noqa: E402
import fy_breakdown as FB  # noqa: E402
import build_fy_breakdown as BFB  # noqa: E402

ID = 'budget-against-actual'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
DATA = os.path.join(ROOT, 'sources', 'data')
AUGUST = os.path.join(ROOT, 'fy28', 'public', 'data', 'budget-vs-actual.json')
D0 = Decimal(0)

# ---------------------------------------------------------------- thresholds, ours
FLOOR = Decimal('5000')        # OURS: no flag under this many dollars (the FY breakdown's ADJ_MIN)
SHARE = Decimal('0.10')        # OURS: and at least this share of the vote (of prior spending, restarted)
THIN = Decimal('0.5')         # OURS: a prior year spending under half its final budget is marked (rule 6)
TRACK = 0.02                   # the August report's own: a miss within 2% is not a miss (same-way test)

BOOK_YEARS = (2018, 2019, 2020, 2021, 2022)


def fail(msg):
    raise SystemExit('build_budget_against_actual: ' + msg)


def fl(x):
    return float(x)


class Texts(BFB.Texts):
    def pct(self, x, dp=1, signed=True):
        t = ('%+.*f%%' % (dp, x)).replace('-', '−') if signed else '%.*f%%' % (dp, x)
        self.figures.add(t)
        return t

    def num(self, n):
        t = C.num(n)
        self.figures.add(t)
        return t


def spct(x, dp=1):
    """A signed percentage the way the prose prints it: +0.5%, −2.6%."""
    return ('%+.*f%%' % (dp, x)).replace('-', '−')


# ---------------------------------------------------------------- the budget documents
# COPIED FROM verify_budget_vs_actual.py, which states each guard's reason; book_years()
# below refuses unless what this computes equals the August report's own payload.
def _elh():
    sp = importlib.util.spec_from_file_location('elh', os.path.join(ROOT, 'scripts/extract_line_history.py'))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def usable(fy, b, a):
    return (fy != 2021 and b and a and not b[1] and not a[1]
            and b[0] >= 10_000 and a[0] >= 1_000 and 0.02 <= a[0] / b[0] <= 20)


def book_cells():
    cell, label = collections.defaultdict(dict), {}
    for r in csv.DictReader(open(os.path.join(DATA, 'line-history.csv'), encoding='utf-8')):
        if r.get('variant'):
            continue
        cell[(r['key'], int(r['fy']))][r['stage']] = (float(r['value']), r['documents_disagree'] == '1')
        label.setdefault(r['key'], r['label'])
    return cell, label


def book_years():
    """The August report's measures, recomputed, and tied to its payload."""
    cell, label = book_cells()
    n = collections.Counter(fy for (k, fy), v in cell.items()
                            if usable(fy, v.get('settled'), v.get('restated')))
    thin = {fy for fy, c in n.items() if c < 20}
    recs = [(k, fy, v['settled'][0], v['restated'][0]) for (k, fy), v in cell.items()
            if fy not in thin and usable(fy, v.get('settled'), v.get('restated'))]
    elh = _elh()
    wb = [r for r in csv.DictReader(open(os.path.join(DATA, 'lps-budget-lines.csv'), encoding='utf-8'))
          if r['kind'] == 'line']
    sec = {elh.norm(r['line_item']): r['section'] for r in wb}
    by_year = collections.defaultdict(lambda: [0.0, 0.0, 0])
    sections = collections.defaultdict(lambda: [0.0, 0.0, 0])
    tuition = collections.defaultdict(lambda: [0.0, 0.0])
    per = collections.defaultdict(list)
    for k, fy, b, a in recs:
        by_year[fy][0] += b
        by_year[fy][1] += a
        by_year[fy][2] += 1
        s = sec.get(k)
        if s in ('SALARIES', 'EXPENSES'):
            sections[s][0] += b
            sections[s][1] += a
            sections[s][2] += 1
        if 'tuition' in k:
            tuition[fy][0] += b
            tuition[fy][1] += a
        per[k].append(a / b - 1)
    multi = {k: v for k, v in per.items() if len(v) >= 4}
    same = [k for k, v in multi.items() if all(d > TRACK for d in v) or all(d < -TRACK for d in v)]
    # TIED TO THE AUGUST REPORT. A different reading of the same documents would be a second
    # version of its findings beside it -- the one thing rule 7d forbids.
    aug = json.load(open(AUGUST, encoding='utf-8'))
    for y in aug['by_year']:
        b, a, c = by_year[y['fy']]
        if round(b) != round(y['budgeted']) or round(a) != round(y['spent']) or c != y['lines']:
            fail('FY%d: the budget documents read %s / %s on %d lines; the August report %s / %s on %d'
                 % (y['fy'], b, a, c, y['budgeted'], y['spent'], y['lines']))
    if set(by_year) != {y['fy'] for y in aug['by_year']}:
        fail('the years differ from the August report')
    for s in aug['sections'][:2]:
        b, a, c = sections['SALARIES' if s['section'] == 'Salaries' else 'EXPENSES']
        if round(b) != round(s['budgeted']) or round(a) != round(s['spent']) or c != s['line_years']:
            fail('%s: %s / %s on %d, the August report %s / %s on %d'
                 % (s['section'], b, a, c, s['budgeted'], s['spent'], s['line_years']))
    for t in aug['tuition']:
        b, a = tuition[t['fy']]
        if round(b) != round(t['budgeted']) or round(a) != round(t['spent']):
            fail('tuition FY%d differs from the August report' % t['fy'])
    if len(multi) != aug['lines_with_four_years'] or len(same) != len(aug['same_way']):
        fail('the same-way test: %d of %d, the August report %d of %d'
             % (len(same), len(multi), len(aug['same_way']), aug['lines_with_four_years']))
    fy21 = [(v['settled'][0], v['restated'][0]) for (k, fy), v in cell.items()
            if fy == 2021 and 'settled' in v and 'restated' in v and v['settled'][0] > 10_000]
    if (len(fy21), sum(1 for b, a in fy21 if abs(b - a) < 1)) != (aug['fy21']['lines'], aug['fy21']['identical']):
        fail('FY21: the identical-to-the-dollar count differs from the August report')
    return dict(cell=cell, label=label, sec=sec, thin=thin, recs=recs, by_year=dict(by_year),
                sections=dict(sections), tuition=dict(tuition), multi=len(multi), same=len(same),
                fy21=(len(fy21), sum(1 for b, a in fy21 if abs(b - a) < 1)))


# ---------------------------------------------------------------- the journal
SAL = {c[0] for c in S.CATEGORIES if c[3].startswith('salary lines')}


def journal_lines(m):
    """Every school line, every journal year, with the three flags. Lines by account."""
    by = collections.defaultdict(dict)
    for r in m['rows']:
        if r['account']:
            by[r['account']][r['fy']] = r
    out = {}
    for fy in BFB.YEARS():
        rows = []
        for acct, ys in by.items():
            r = ys.get(fy)
            if not r:
                continue
            budget = r['voted'] + r['transfers'] + r['carried_budget']
            if budget - r['gf_spent'] != r['left']:
                fail('FY%d %s: budget less spent is not left' % (fy, acct))
            vals = (r['voted'], r['transfers'], r['carried_budget'], r['gf_spent'])
            if all(round(v) == 0 for v in vals):
                continue
            own = r['voted'] + r['carried_budget']
            gap = r['gf_spent'] - own
            big = lambda v, base: v >= FLOOR and (base <= 0 or v >= SHARE * base)
            x = dict(fy=fy, r=r, budget=budget, gap=gap, flags={})
            if r['transfers'] > 0 and big(gap, r['voted']):
                cov = min(r['transfers'], gap)
                x['flags']['under'] = dict(gap=gap, covered=cov, uncovered=gap - cov)
            if (r['transfers'] < 0 or r['left'] > 0) and big(-gap, r['voted']):
                x['flags']['over'] = dict(unspent=-gap, out=max(-r['transfers'], D0),
                                          left=max(r['left'], D0))
            p = ys.get(fy - 1)
            if p is not None:
                # LAST YEAR'S SPENDING ON THE LINE, BEFORE RE-CHARGES: a bill the school budget paid
                # and a journal entry later put on a grant was still this line's spending. Against
                # the after-re-charge figure, a line a grant took over at year end would read as one
                # that stopped costing anything (FY2024 special-education paras: -$157,886).
                ps = p['gf_spent'] + p['moved_off'] - p['moved_on']
                pb = p['voted'] + p['transfers'] + p['carried_budget']
                x['prior'] = dict(spent=ps, budget=pb, transfers=p['transfers'], voted=p['voted'],
                                  recharged=p['moved_off'] - p['moved_on'])
                if big(r['voted'] - ps, ps):
                    x['flags']['restart'] = dict(
                        over=r['voted'] - ps, prior_spent=ps, prior_budget=pb,
                        recharged=p['moved_off'] - p['moved_on'],
                        cut=p['transfers'] < 0, above_budget=r['voted'] > pb,
                        # rule 6: an account that spent nothing, or under half its final budget, the
                        # year before may have had its cost moved to another account. Marked, not
                        # dropped: the page says to read its history (THIN, ours).
                        thin=ps <= 0 or (pb > 0 and ps < THIN * pb))
            rc = r['moved_off'] - r['moved_on']
            for k in ('under', 'over'):
                if k in x['flags']:
                    x['flags'][k]['recharged'] = rc
            x['usable'] = (r['voted'] >= 10_000 and r['gf_spent'] >= 1_000
                           and Decimal('0.02') <= r['gf_spent'] / r['voted'] <= 20)
            x['sal'] = r['category'] in SAL
            rows.append(x)
        out[fy] = rows
    return out, by


def same_way_journal(J_):
    per = collections.defaultdict(list)
    for fy, rows in J_.items():
        for x in rows:
            if x['usable']:
                per[x['r']['account']].append(fl(x['r']['gf_spent'] / x['r']['voted']) - 1)
    full = {k: v for k, v in per.items() if len(v) == len(J_)}
    same = [k for k, v in full.items() if all(d > TRACK for d in v) or all(d < -TRACK for d in v)]
    return full, same


# ---------------------------------------------------------------- payload pieces
def ratio_label(r):
    return spct((r - 1) * 100, 0)


def across(T, B, JL):
    """The signature: every comparable line, every year, as dots around its own vote."""
    years = []
    for fy in sorted(set(BOOK_YEARS) | set(JL)):
        if fy in JL:
            rs = [x for x in JL[fy] if x['usable']]
            lines = [dict(name=T.lit(BFB.line_name(x['r'])), b=round(fl(x['r']['voted'])),
                          a=round(fl(x['r']['gf_spent'])), s=1 if x['sal'] else 0,
                          bt=T.usd(x['r']['voted']), at=T.usd(x['r']['gf_spent']),
                          pt=T.pct(fl(x['r']['gf_spent'] / x['r']['voted'] - 1) * 100))
                     for x in rs]
            src = 'ledger'
        elif fy == 2021:
            lines, src = [], 'none'
        else:
            lines = []
            for k, y, b, a in B['recs']:
                if y != fy:
                    continue
                s = B['sec'].get(k)
                lines.append(dict(name=T.lit(B['label'][k]), b=round(b), a=round(a),
                                  s=1 if s == 'SALARIES' else 0 if s == 'EXPENSES' else 2,
                                  bt=T.usd(b), at=T.usd(a), pt=T.pct((a / b - 1) * 100)))
            src = 'books'
        tb, ta = sum(l['b'] for l in lines), sum(l['a'] for l in lines)
        flags = None
        if fy in JL:
            flags = {k: T.num(sum(1 for x in JL[fy] if k in x['flags'])) for k in ('under', 'over', 'restart')}
            if fy - 1 not in JL:
                flags['restart'] = '—'
        years.append(dict(fy=T.fy(fy), src=src, lines=sorted(lines, key=lambda l: l['a'] / l['b']),
                          n=T.num(len(lines)) if lines else '',
                          total=T.pct((ta / tb - 1) * 100, 2) if lines else '',
                          tr=round(ta / tb, 5) if lines else None, flags=flags))
    ticks = [(0.25, '−75%'), (0.5, '−50%'), (1, 'the vote'), (2, '+100%'), (4, '+300%')]
    return dict(years=years, ticks=[dict(r=r, t=T.lit(t)) for r, t in ticks], lo=0.25, hi=4,
                text=dict(
                    books=T.lit('Budget documents'), ledger=T.lit('Accounting system'),
                    none=T.lit('Not comparable'),
                    books_note='The district’s budget and actual columns, side by side',
                    ledger_note='The school journal, tied to the Town’s year-end report',
                    none_note='The budget documents print the budget in the actual column',
                    sal='Salary lines', oth='Everything else', unk='Not in today’s budget workbook',
                    total='All the dots together', lines='lines compared',
                    flags='Lines flagged', under='Underfunded', over='Overbudgeted',
                    restart='Restarted high', not_read='not read', dash_note=T.lit(
                        '— : not shown. The budget documents print no transfers, and %s has no '
                        'year before it in the journal.' % T.fy(min(JL))),
                    clipped='Beyond the edge: drawn at it',
                    hover='Hover or tap a dot for the line'))


def flag_text(T):
    fl_ = T.usd(FLOOR)
    sh = T.pct(fl(SHARE) * 100, 0, signed=False)
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


def moves_of(T, r, names):
    return [dict(date=T.lit(BFB.long_date(x['date'])), memo=T.lit(x['memo'].strip() or 'no memo'),
                 v=BFB.signed(T, x['amount']),
                 others=[T.lit(names.get(o['account'], o['description'].strip().title()))
                         for o in x.get('others', [])][:6])
            for x in sorted(r['moves_in'], key=lambda x: x['date'])]


def year_views(T, B, JL):
    names = {}
    for rows in JL.values():
        for x in rows:
            names[x['r']['account']] = BFB.line_name(x['r'])
    out = []
    for fy in sorted(set(BOOK_YEARS) | set(JL)):
        if fy in JL:
            rows = []
            for x in sorted(JL[fy], key=lambda x: (S.CAT_LABEL[x['r']['category']], BFB.line_name(x['r']))):
                r = x['r']
                n = dict(voted=r['voted'], transfers=r['transfers'], carried=r['carried_budget'],
                         budget=x['budget'], spent=r['gf_spent'], left=r['left'])
                row = dict(name=T.lit(BFB.line_name(r)), account=T.lit(r['account']),
                           cat=S.CAT_LABEL[r['category']],
                           n={k: round(fl(v), 2) for k, v in n.items()},
                           t={k: (BFB.signed(T, v) if k == 'transfers' and v else T.usd(v)) for k, v in n.items()},
                           f=sorted(x['flags']))
                fx = x['flags']
                if 'under' in fx:
                    u = fx['under']
                    row['under'] = dict(gap=T.usd(u['gap']), covered=T.usd(u['covered']),
                                        uncovered=T.usd(u['uncovered']), n=round(fl(u['gap']), 2),
                                        recharged=BFB.signed(T, -u['recharged']) if round(u['recharged']) else '')
                if 'over' in fx:
                    o = fx['over']
                    row['over'] = dict(unspent=T.usd(o['unspent']), out=T.usd(o['out']),
                                       left=T.usd(o['left']), n=round(fl(o['unspent']), 2),
                                       recharged=BFB.signed(T, -o['recharged']) if round(o['recharged']) else '')
                if 'restart' in fx:
                    h = fx['restart']
                    row['restart'] = dict(over=T.usd(h['over']), prior_spent=T.usd(h['prior_spent']),
                                          prior_budget=T.usd(h['prior_budget']), cut=h['cut'],
                                          above_budget=h['above_budget'], thin=h['thin'],
                                          recharged=BFB.signed(T, -h['recharged']) if round(h['recharged']) else '',
                                          n=round(fl(h['over']), 2))
                if 'prior' in x:
                    row['prior'] = dict(spent=T.usd(x['prior']['spent']), budget=T.usd(x['prior']['budget']))
                if r['moves_in'] and fx:
                    row['moves'] = moves_of(T, r, names)
                rows.append(row)
            new = sum(1 for x in JL[fy] if 'prior' not in x and x['r']['voted'] > 0)
            out.append(dict(fy=T.fy(fy), src='ledger', rows=rows,
                            counts={k: T.num(sum(1 for x in JL[fy] if k in x['flags']))
                                    for k in ('under', 'over', 'restart')},
                            new=T.lit('%s lines on an account the year before did not have: never '
                                      'flagged restarted high.' % T.num(new)) if fy - 1 in JL else None,
                            no_restart=T.lit('Not shown for %s: %s is not in the school journal this '
                                             'page reads, so no line has a year before it.'
                                             % (T.fy(fy), T.fy(fy - 1))) if fy - 1 not in JL else None,
                            totals=dict(voted=T.usd(sum((x['r']['voted'] for x in JL[fy]), D0)),
                                        spent=T.usd(sum((x['r']['gf_spent'] for x in JL[fy]), D0)),
                                        left=T.usd(sum((x['r']['left'] for x in JL[fy]), D0)))))
            continue
        rows = []
        for (k, y), v in B['cell'].items():
            if y != fy or 'settled' not in v or 'restated' not in v:
                continue
            b, a = v['settled'], v['restated']
            if fy == 2021:
                why = 'actual printed as the budget'
            elif usable(fy, b, a):
                why = ''
            elif b[1] or a[1]:
                why = 'documents disagree'
            elif b[0] < 10_000:
                why = 'budget under %s' % T.usd(10_000)
            else:
                why = 'not comparable'
            rows.append(dict(name=T.lit(B['label'][k]), b=round(b[0]), a=round(a[0]),
                             bt=T.usd(b[0]), at=T.usd(a[0]), dt=BFB.signed(T, round(a[0] - b[0])),
                             d=round(a[0] - b[0]),
                             pt=T.pct((a[0] / b[0] - 1) * 100) if b[0] else '', why=T.lit(why)))
        rows.sort(key=lambda r: -r['b'])
        out.append(dict(fy=T.fy(fy), src='none' if fy == 2021 else 'books', rows=rows,
                        counted=T.num(sum(1 for r in rows if not r['why']))))
    return out


def year_text(T, JL, B):
    first = min(JL)
    return dict(
        banner_books=T.lit('From the district’s budget documents only. They print no mid-year '
                           'transfers and no account numbers, so the three flags are not shown. The '
                           'accounting system’s figures for each line this year are in a Finance '
                           'Committee workbook this page does not read yet.'),
        banner_none=T.lit('From the district’s budget documents only, and not comparable: in %s of '
                          '%s lines the documents print this year’s budget, to the dollar, in the '
                          'column headed actual.' % (T.num(B['fy21'][1]), T.num(B['fy21'][0]))),
        banner_ledger=T.lit('From the school journal: the Town’s accounting system, every line tied '
                            'to its year-end report. Spent counts orders still owed at 30 June.'),
        not_shown='Not shown for this year: it needs each line’s transfers, which the budget documents do not print.',
        not_shown_restart='Not shown for this year: this flag matches lines by account number, and the '
                          'budget documents print names, not accounts.',
        books_cols=dict(name='Line, as the documents name it', b='Budget', a='Actual', d='Difference',
                        p='Against budget', why='Counted'),
        books_counted='lines counted across the years', yes='counted', no_link=T.lit(
            'Lines here are the district’s printed names, not account numbers, so they do not link '
            'to a line’s page; those pages begin in %s.' % T.fy(first)),
        cols=dict(name='School line', cat='Category', voted='Voted', transfers='Transfers',
                  carried='Carried in', budget='Final budget', spent='Spent', left='Left', flags='Flags'),
        means=dict(
            voted='What Town Meeting voted for this line.',
            transfers='Budget moved to or from other lines during the year.',
            carried='Last year’s orders still owed, carried in with the money to pay them.',
            budget='Voted, plus transfers, plus carried in.',
            spent=T.lit('Payments, plus orders still owed at 30 June.'),
            left='Final budget less spent. Above zero it added to the surplus.'),
        flagged='flagged', every='Every line', only='Flagged lines only', filter='Find a line',
        show_all='Show every flagged line', show_fewer='Show the largest', open='Its page',
        gap='Spent past the vote', covered='Covered by transfers', uncovered='Not covered',
        unspent='Not spent', moved_out='Moved out', left_end='Left at year end',
        over_by='Vote above last year’s spending', prior_spent='Spent the year before',
        prior_budget='Final budget the year before',
        cut='Budget was moved off it the year before',
        above='Above last year’s final budget too', below='At or below last year’s final budget',
        thin=T.lit('Spent under half its final budget the year before (a mark of ours): its history '
                   'may show the cost moved to another account.'),
        recharged='Re-charged to other funds after the school budget paid',
        transfers='Transfers', other_side='with', none='None this year.',
        total='All lines', lines_n='lines', sort='Click a heading to sort')


# ---------------------------------------------------------------- the page
def page(m=None):
    m = m or FB.model()
    B = book_years()
    JL, by = journal_lines(m)
    ys = sorted(JL)
    first, last = ys[0], ys[-1]
    T = Texts()
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    P = lambda v, dp=1: figure(v, spct(v, dp), '%')
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    N = lambda n, unit: figure(n, C.num(n), unit)

    # --- what the journal shows, by year and in all
    sal = {}
    for fy in ys:
        rs = [x for x in JL[fy] if x['usable']]
        for k, pick in (('sal', lambda x: x['sal']), ('oth', lambda x: not x['sal'])):
            v = sum((x['r']['voted'] for x in rs if pick(x)), D0)
            s_ = sum((x['r']['gf_spent'] for x in rs if pick(x)), D0)
            sal[(fy, k)] = fl(s_ / v - 1) * 100
    sal_under = [fy for fy in ys if sal[(fy, 'sal')] < 0]
    oth_over = [fy for fy in ys if sal[(fy, 'oth')] > 0]
    full, same = same_way_journal(JL)
    bsal = B['sections']['SALARIES']
    both = B['sections']['EXPENSES']
    bs_pct = (bsal[1] / bsal[0] - 1) * 100
    bo_pct = (both[1] / both[0] - 1) * 100
    # out-of-district tuition: the district's own category (fy_items.GROUPS), journal side
    tu = {}
    for fy in ys:
        rs = [x for x in JL[fy] if x['r']['category'] == 'tuition']
        v = sum((x['r']['voted'] for x in rs), D0)
        s_ = sum((x['r']['gf_spent'] for x in rs), D0)
        tu[fy] = fl(s_ / v - 1) * 100
    btu = {fy: (a / b - 1) * 100 for fy, (b, a) in B['tuition'].items()}
    allt = list(btu.values()) + list(tu.values())
    t_hi, t_lo = max(allt), min(allt)
    # flags
    cnt = {(fy, k): sum(1 for x in JL[fy] if k in x['flags']) for fy in ys for k in ('under', 'over', 'restart')}
    rs_years = [fy for fy in ys if fy - 1 in JL]
    restarts = [x for fy in rs_years for x in JL[fy] if 'restart' in x['flags']]
    after_cut = [x for x in restarts if x['flags']['restart']['cut']]
    thin_n = sum(1 for x in restarts if x['flags']['restart']['thin'])
    cut_lines = [x for fy in rs_years for x in JL[fy] if 'prior' in x and x['prior']['transfers'] < 0]
    under_tot = {fy: sum((x['flags']['under']['gap'] for x in JL[fy] if 'under' in x['flags']), D0) for fy in ys}
    within = {fy: sum(1 for x in JL[fy] if x['usable'] and abs(fl(x['r']['gf_spent'] / x['r']['voted']) - 1) <= TRACK)
              for fy in ys}
    usable_n = {fy: sum(1 for x in JL[fy] if x['usable']) for fy in ys}

    f = LD.fact
    span = '%s–%s' % (C.fy(first), C.fy(last))
    bspan = '%s–%s' % (C.fy(min(B['by_year'])), C.fy(max(B['by_year'])))
    facts = [
        f('bsal', P(bs_pct, 2), 'salary lines against budget, documents, %s' % bspan, 'published',
          label_figures={'a': F(min(B['by_year'])), 'b': F(max(B['by_year']))}),
        f('both', P(bo_pct, 2), 'everything else against budget, documents, %s' % bspan, 'published',
          label_figures={'a': F(min(B['by_year'])), 'b': F(max(B['by_year']))}),
        f('jsal', N(len(sal_under), 'years'), 'years of %d salary lines spent under the vote, journal'
          % len(ys), 'published', label_figures={'n': N(len(ys), 'years')}),
        f('joth', N(len(oth_over), 'years'), 'years of %d everything else spent over the vote, journal'
          % len(ys), 'published', label_figures={'n': N(len(ys), 'years')}),
        f('jsame', N(len(same), 'lines'), 'lines of %d missing the same way all %d journal years'
          % (len(full), len(ys)), 'published',
          label_figures={'n': N(len(full), 'lines'), 'y': N(len(ys), 'years')}),
        f('bsame', N(B['same'], 'lines'), 'lines of %d missing the same way every year, documents'
          % B['multi'], 'published', label_figures={'n': N(B['multi'], 'lines')}),
        f('thi', P(t_hi), 'out-of-district tuition, its worst year over', 'published'),
        f('tlo', P(t_lo), 'out-of-district tuition, its worst year under', 'published'),
        f('cut', N(len(after_cut), 'line-years'), 'restarted high after budget was moved off them',
          'published'),
        f('cuts', N(len(cut_lines), 'line-years'), 'line-years that gave budget up mid-year', 'published'),
        f('track', N(within[last], 'lines'), 'lines of %d within 2%% of their vote, %s'
          % (usable_n[last], C.fy(last)), 'published',
          label_figures={'y': F(last), 'n': N(usable_n[last], 'lines')}, allow=('2%',)),
    ]

    def con(text, rests, figs, so, so_figs=None):
        return TP.conclusion(text, rests, figs, so=so, so_figures=so_figs)
    conclusions = [
        con('Salary lines came in under their vote in %d of %d journal years; the documents agree, at %s.'
            % (len(sal_under), len(ys), spct(bs_pct, 2)), ['jsal', 'joth', 'bsal', 'both'],
            {'a': N(len(sal_under), 'years'), 'b': N(len(ys), 'years'), 'c': P(bs_pct, 2)},
            'A salary vote leaves room the year usually does not use; that room is where a surplus '
            'starts. Why, post by post, the books do not say.'),
        con('Only %d of %d lines missed the same way in all %d journal years; in the documents, %d of %d.'
            % (len(same), len(full), len(ys), B['same'], B['multi']), ['jsame', 'bsame'],
            {'a': N(len(same), 'lines'), 'b': N(len(full), 'lines'), 'y': N(len(ys), 'years'),
             'c': N(B['same'], 'lines'), 'd': N(B['multi'], 'lines')},
            'Lines miss in both directions and cancel; a total near its vote says little about any line in it.'),
        con('Out-of-district tuition missed from %s to %s, in both directions, %s–%s.'
            % (spct(t_hi), spct(t_lo), C.fy(min(btu)), C.fy(last)), ['thi', 'tlo'],
            {'a': P(t_hi), 'b': P(t_lo), 'x': F(min(btu)), 'y': F(last)},
            'No trend to project: the site’s projection holds this line flat rather than growing it at a rate.'),
        con('%d of %d times a line gave budget up mid-year, its next vote was %s or more above its spending.'
            % (len(after_cut), len(cut_lines), C.pct(fl(SHARE) * 100, 0)), ['cut', 'cuts'],
            {'a': N(len(after_cut), 'line-years'), 'b': N(len(cut_lines), 'line-years'),
             's': figure(fl(SHARE) * 100, C.pct(fl(SHARE) * 100, 0), '%')},
            'Each is a question for the next budget: was the cut a one-year saving, or a line set high?'),
    ]
    yrs = sorted(set(BOOK_YEARS) | set(JL))
    sig = across(T, B, JL)
    views = year_views(T, B, JL)
    ftext = flag_text(T)
    ytext = year_text(T, JL, B)
    blocks = [
        TB.custom('bva-across', 'Every line, every year', sig, place='lead',
                  figures=sorted(T.figures), allow=sorted(T.literals),
                  basis=('record', 'The budget documents, then the school journal; never added together'),
                  alt='Dot chart, one column per fiscal year from %s to %s: each dot one school line, '
                      'placed by what it spent against what it was voted, salary lines and the rest in '
                      'two colours, with a mark for all the lines together; the years from the budget '
                      'documents and from the accounting system shaded apart, and a row of flag counts '
                      'under each journal year' % (C.fy(yrs[0]), C.fy(yrs[-1])),
                  so=('Each year’s mark sits near the vote while its dots spread far above and below '
                      'it: the total is quiet because lines miss both ways and cancel.', None, ())),
        TB.custom('fy-year-picker', 'Fiscal year', dict(
            bare=True, years=[C.fy(y) for y in yrs], label='Change year',
            spans={C.fy(y): '1 July %d to 30 June %d' % (y - 1, y) for y in yrs}),
                  place='end', figures=[C.fy(y) for y in yrs],
                  allow=['1 July %d to 30 June %d' % (y - 1, y) for y in yrs],
                  alt='The fiscal year the line-by-line view below shows',
                  so=('The view below shows the year picked here; how much it can show depends on '
                      'which record holds that year.', None, ())),
        TB.custom('bva-year', 'Line by line', dict(years=views, flags=ftext, text=ytext),
                  place='end', figures=sorted(T.figures), allow=sorted(T.literals),
                  basis=('record', 'Each line’s vote, transfers and spending, from the record named in the banner'),
                  alt='For the fiscal year picked: a banner naming the record it comes from; for a '
                      'journal year, the lines flagged underfunded, overbudgeted and restarted high, '
                      'each with its figures and threshold, then every school line with voted, '
                      'transfers, carried in, final budget, spent and left; for a budget-document '
                      'year, every line’s budget against its actual',
                  so=('A flag marks where the vote and the year parted; the transfers listed under it '
                      'show where the budget went. The books do not record why.', None, ())),
        TB.explain('How the two records differ', [
            ('**The budget documents** print a budget and an actual column the district wrote. Lines '
             'are read with the rules of the August analysis: a line under $10,000, a cell two '
             'documents disagree about, and FY2021 are not counted.', None, ('$10,000', 'FY2021')),
            '**The school journal** is the Town’s own accounting record, and every line here ties to '
            'its year-end report. It records transfers between lines, which the documents never do.',
            '**They are never added together.** Where both cover a year, this page reads the journal.',
        ], place='end', tone='define'),
    ]
    tu_chart = TP.series(
        'Out-of-district tuition against its vote', [C.fy(y) for y in sorted(set(btu) | set(tu))],
        [TP.track('Budget documents', [btu.get(y) if y not in tu else None
                                       for y in sorted(set(btu) | set(tu))], 'stated', 'bar'),
         TP.track('School journal', [tu.get(y) for y in sorted(set(btu) | set(tu))], 'published', 'bar')],
        '%', kind='bar', decimals=1,
        note='Spent against the vote, private and collaborative tuition together. The documents’ '
             'years before the journal; the journal’s from %s.' % C.fy(first),
        note_figures={'y': F(first)})
    return TP.page(
        ID,
        'School lines land near their vote in total every year, and far from it one by one, in '
        'both directions.',
        facts, conclusions, chart=tu_chart, blocks=blocks,
        sources=[
            dict(label='Lunenburg Budget Project — line-history.csv (every line the district’s '
                       'budget documents print, budget and actual)', href='/data/line-history.csv'),
            dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                       'line, %s)' % span, href=J.PUBLIC['journal']),
            dict(label='Town of Lunenburg — school general fund period-13 reports, %s (each line '
                       'tied to the cent)' % span, href=BFB.ledger_doc(last, 'gf-school')),
            dict(label='Lunenburg Budget Project — Budget versus actual, August 2026 (the findings '
                       'from the budget documents carried over here)',
                 href='/docs/analyses/budget-vs-actual.md')],
        # LISTED (TJ, 29 October 2026, by way of the coordinator: built as a normal page now that
        # the FY breakdown goes public). Registered in scripts/topic_registry/school_all_funds.py;
        # the draft form remains only so the page still builds before that registration exists.
        draft=None if ID in REG.TOPICS else dict(title='School lines against budget', home='school-all-funds'))


def render(m=None):
    p = page(m)
    p['not_established'] = [
        'Why any line was voted above or below what it spent: a vacancy, a placement, a price '
        'change and a plan all produce the same figures.',
        'Which line a renamed line continued: lines are matched by account number only.',
        'Transfers before %s: the Finance Committee workbook that holds them is not read here yet.'
        % C.fy(min(BFB.YEARS())),
    ]
    return json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('budget against actual: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
