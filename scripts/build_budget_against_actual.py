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
import line_flags as LF  # noqa: E402

ID = 'budget-against-actual'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
DATA = os.path.join(ROOT, 'sources', 'data')
AUGUST = os.path.join(ROOT, 'fy28', 'public', 'data', 'budget-vs-actual.json')
D0 = Decimal(0)

# ---------------------------------------------------------------- thresholds, ours
FLOOR, SHARE = LF.FLOOR, LF.SHARE   # OURS, line_flags.py: the same for both pages
TRACK = 0.02                   # the August report's own: a miss within 2% is not a miss (same-way test)
# THE USUAL MISS (TJ, 30 October 2026: "something that shows if its generally over or under budget
# ... 10% over/under or 50k over or under on 'average' (median?)"). OURS: a line's MEDIAN year,
# spent against its vote, at least TREND_SHARE off (and FLOOR in dollars, the flags' own floor,
# so a $400 supply line is not a trend) or TREND_DOLLARS off, over at least TREND_YEARS years.
TREND_SHARE = Decimal('0.10')
TREND_DOLLARS = Decimal('50000')
TREND_YEARS = 3

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

    def dpct(self, x, dp=1):
        self.figures.add('%.*f%%' % (dp, abs(x)))
        return dpct(x, dp)


def spct(x, dp=1):
    """A signed percentage the way the prose prints it: +0.5%, −2.6%."""
    return ('%+.*f%%' % (dp, x)).replace('-', '−')


def dpct(x, dp=1):
    """Spent against the vote, in words, because a bare percentage does not say which way it is
    read (TJ, 30 October 2026): 12.0% over budget, 2.6% under budget."""
    t = '%.*f%%' % (dp, abs(x))
    return t + (' over budget' if x > 0 else ' under budget' if x < 0 else ' on budget')


def median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


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
                fy21=(len(fy21), sum(1 for b, a in fy21 if abs(b - a) < 1)), aug=aug)


# ---------------------------------------------------------------- the journal and the workbook
# The flags, the journal's line-years and the workbook's are line_flags.py's, shared with the FY
# breakdown, so one rule cannot read two ways on two pages.
journal_lines = LF.journal_lines


# ---------------------------------------------------------------- payload pieces
def ratio_label(r):
    return spct((r - 1) * 100, 0)


def across(T, B, JL, WL):
    """The signature: every comparable line, every year, as dots around its own vote. FY2021's
    budget documents print the budget in the actual column, so that one year is read from the
    Finance Committee workbook instead -- the record the grid below reads for it."""
    years = []
    for fy in sorted(set(BOOK_YEARS) | set(JL)):
        if fy in JL or fy == 2021:
            rs = [x for x in (JL[fy] if fy in JL else WL[fy]) if x['usable']]
            lines = [dict(name=T.lit(BFB.line_name(x['r'])), b=round(fl(x['r']['voted'])),
                          a=round(fl(x['r']['gf_spent'])), s=1 if x['sal'] else 0,
                          bt=T.usd(x['r']['voted']), at=T.usd(x['r']['gf_spent']),
                          pt=T.dpct(fl(x['r']['gf_spent'] / x['r']['voted'] - 1) * 100))
                     for x in rs]
            src = 'ledger' if fy in JL else 'workbook'
        else:
            lines = []
            for k, y, b, a in B['recs']:
                if y != fy:
                    continue
                s = B['sec'].get(k)
                lines.append(dict(name=T.lit(B['label'][k]), b=round(b), a=round(a),
                                  s=1 if s == 'SALARIES' else 0 if s == 'EXPENSES' else 2,
                                  bt=T.usd(b), at=T.usd(a), pt=T.dpct((a / b - 1) * 100)))
            src = 'books'
        tb, ta = sum(l['b'] for l in lines), sum(l['a'] for l in lines)
        years.append(dict(fy=T.fy(fy), src=src, lines=sorted(lines, key=lambda l: l['a'] / l['b']),
                          total=T.dpct((ta / tb - 1) * 100, 2) if lines else '',
                          tr=round(ta / tb, 5) if lines else None))
    ticks = [(0.25, '75%', 'under budget'), (0.5, '50%', 'under budget'), (1, 'the vote', ''),
             (2, '100%', 'over budget'), (4, '300%', 'over budget')]
    n21, same21 = B['fy21']
    return dict(years=years, ticks=[dict(r=r, t=T.lit(t), sub=w) for r, t, w in ticks], lo=0.25, hi=4,
                text=dict(
                    books=T.lit('Budget documents'), ledger=T.lit('Accounting system'),
                    workbook=T.lit('Workbook'),
                    books_note='The district’s budget and actual columns, side by side',
                    ledger_note='The school journal, tied to the Town’s year-end report',
                    workbook_note=T.lit(
                        '%s only. The district’s budget documents print the budget in its actual column '
                        'that year (%s of %s lines identical to the dollar), so the year is read from the '
                        'Finance Committee workbook, which the grid below reads too'
                        % (T.fy(2021), T.num(same21), T.num(n21))),
                    sal='Salary lines', oth='Everything else', unk='Not in today’s budget workbook',
                    total='All the dots together',
                    clipped='Beyond the edge: drawn at it',
                    hover='Hover or tap a dot for the line'))


def short_usd(T, v):
    """A cell's miss, short enough for a grid of nine years: +$640, −$12k, +$1.2M."""
    v = float(v)
    a = abs(v)
    t = ('$%.0f' % a if a < 1000 else '$%.0fk' % (a / 1000) if a < 999_500
         else '$%.1fM' % (a / 1_000_000))
    t = ('+' if v > 0 else '−' if v < 0 else '') + t
    T.figures.add(t)
    return t


def usual(xs):
    """A line's usual miss: the MEDIAN year's spent-against-vote share and dollars, and which way
    it leans by the page's rule (TREND_*), or '' when it does not. `xs`: its line-years."""
    if len(xs) < TREND_YEARS:
        return None
    sh = [x['r']['gf_spent'] / x['r']['voted'] - 1 for x in xs if x['r']['voted'] > 0]
    misses = [x['r']['gf_spent'] - x['r']['voted'] for x in xs]
    md = median(misses)
    mp = median(sh) if sh else None
    o = (mp is not None and mp >= TREND_SHARE and md >= FLOOR) or md >= TREND_DOLLARS
    u = (mp is not None and mp <= -TREND_SHARE and md <= -FLOOR) or md <= -TREND_DOLLARS
    return dict(share=mp, dollars=md, years=len(xs), misses=misses,
                way='over' if o and not u else 'under' if u and not o else '')


def grid(T, JL, WL, tied):
    """EVERY LINE, EVERY YEAR, FY2018 ON: one row per account, one column per year, each cell
    that year's miss (spent less the vote) with its flags. Workbook years and journal years are
    each one record; a line-year is never read from both (line_flags.py)."""
    years = sorted(set(WL) | set(JL))
    src = {fy: 'ledger' if fy in JL else 'workbook' for fy in years}
    rows = {}
    for fy in years:
        for x in (JL.get(fy) or WL.get(fy)):
            a = x['r']['account']
            rows.setdefault(a, dict(cells={}, names={}, cat={}))
            rows[a]['cells'][fy] = x
            rows[a]['names'][fy] = LF.line_name(x['r'])
            rows[a]['cat'][fy] = x['r']['category']
    out, trend = [], []
    for a, v in rows.items():
        last = max(v['names'])
        us = usual([v['cells'][fy] for fy in sorted(v['cells'])])
        cells, tot, nf = [], D0, 0
        for fy in years:
            x = v['cells'].get(fy)
            if x is None:
                cells.append(None)
                continue
            r = x['r']
            miss = r['gf_spent'] - r['voted']
            tot += abs(miss)
            nf += 1 if x['flags'] else 0
            cells.append([short_usd(T, miss), ''.join(k[0] for k in LF.KEYS if k in x['flags']),
                          round(fl(r['gf_spent'] / r['voted']), 3) if r['voted'] > 0 else None,
                          T.usd(r['voted']), T.usd(r['gf_spent'])])
        u = None
        if us:
            u = [T.dpct(fl(us['share']) * 100, 0) if us['share'] is not None else '',
                 short_usd(T, us['dollars']), us['way'],
                 round(fl(us['share']) + 1, 3) if us['share'] is not None else None,
                 round(fl(us['dollars'])), [round(fl(m)) for m in us['misses']]]
            if us['way']:
                trend.append(dict(name=v['names'][last], account=a,
                                  **{k: w for k, w in us.items() if k != 'misses'}))
        out.append(dict(name=T.lit(v['names'][last]), account=T.lit(a), cat=S.CAT_LABEL[v['cat'][last]],
                        c=cells, s=round(fl(tot)), nf=nf, u=u))
    out.sort(key=lambda r: (-r['s'], r['name']))
    first_j = min(JL)
    cols = []
    for fy in years:
        rs = JL.get(fy) or WL.get(fy)
        cnt = {k: sum(1 for x in rs if k in x['flags']) for k in LF.KEYS}
        no_restart = fy - 1 not in JL and fy in JL
        cols.append(dict(fy=T.fy(fy), src=src[fy],
                         href='/school-all-funds/fy-breakdown?fy=%s' % C.fy(fy) if fy in JL else None,
                         n={k: ('—' if k == 'restart' and no_restart else LF._num(T, cnt[k])) for k in LF.KEYS},
                         lines=LF._num(T, len(rs))))
    ftext = LF.flag_text(T)
    tie = ' and '.join('%s lines in %s' % (LF._num(T, n), T.fy(fy)) for fy, n in tied)
    rule = trend_rule(T)
    return dict(years=cols, rows=out, flags={k: ftext[k]['name'] for k in LF.KEYS}, text=dict(
        usual='Usual year', usual_sub='the median', usual_over='usually over', usual_under='usually under',
        usual_note=rule, only_usual='Usually over or under',
        workbook=T.lit('Finance Committee workbook'), ledger=T.lit('School journal'),
        workbook_note=T.lit(
            '%s to %s: the Finance Committee’s workbook, built from MUNIS exports a year at a time. '
            'Assembled by a person, so stated, not proof. Read against the journal where both exist, '
            'it gives the same vote, transfers, final budget and spending on every line: %s.'
            % (T.fy(min(WL)), T.fy(max(WL)), tie)),
        workbook_restart=T.lit(
            'In the workbook years, last year’s spending is after re-charges to other funds: the '
            'workbook cannot show them. From %s it is before them.' % T.fy(first_j + 1)),
        no_restart=T.lit('%s: no restarted-high count. %s is in the workbook, not the journal, and a '
                         'flag reads one record.' % (T.fy(first_j), T.fy(first_j - 1))),
        ledger_note='From the school journal, every line tied to the Town’s year-end report.',
        cell='Each cell: spent less the vote that year. Shaded by how far, against the vote.',
        open_year='Open the year in the FY breakdown',
        line='School line', cat='Category', flagged_years='Years flagged',
        filter='Find a line', every='Every line', only='Flagged in any year',
        show_all='Show every line', show_fewer='Show the largest', lines_n='lines',
        sort='Sorted by the size of its misses, all years together; click a heading to sort',
        none='not on this account that year',
        mark=dict(u='U', o='O', r='R'), over='spent past the vote', under='spent under the vote',
        scroll='More years: scroll the table sideways')), trend


def trend_rule(T):
    """The usual-miss rule in words, the same sentence wherever it is applied (rule 2)."""
    sh = C.pct(fl(TREND_SHARE) * 100, 0)
    T.figures.add(sh)
    return T.lit('Usual year: the median of a line’s years, spent against its vote. A line usually '
                 'misses one way when that median is %s or more over or under budget (and at least %s), '
                 'or %s or more either way, over %s or more years. Thresholds of ours.'
                 % (sh, T.usd(FLOOR), T.usd(TREND_DOLLARS), T.num(TREND_YEARS)))


def fund_series(JL):
    """The whole school general fund, FY2010 on: what its final budget left unspent, workbook
    years then journal years, on one footing (carried from the retired school-budget-against-
    actual page, 30 October 2026)."""
    wt = LF.workbook_totals()
    out = {}
    for fy, (b, sp) in wt.items():
        if fy not in JL:
            out[fy] = ('workbook', b, sp)
    for fy in JL:
        out[fy] = ('ledger', sum((x['budget'] for x in JL[fy]), D0), sum((x['r']['gf_spent'] for x in JL[fy]), D0))
    for fy in set(wt) & set(JL):
        jb, js = out[fy][1], out[fy][2]
        if abs(wt[fy][0] - jb) > 1 or abs(wt[fy][1] - js) > 1:
            fail('FY%d: the workbook’s school fund reads %s / %s, the journal %s / %s'
                 % (fy, wt[fy][0], wt[fy][1], jb, js))
    ys = sorted(out)
    if ys != list(range(ys[0], ys[-1] + 1)):
        fail('the school fund series has a hole: %s' % ys)
    if any(b - sp <= 0 for _, b, sp in out.values()):
        fail('a year spent past its final budget; the page says none did')
    return out


# ---------------------------------------------------------------- the page
def page(m=None):
    m = m or FB.model()
    B = book_years()
    JL, by = journal_lines(m)
    ys = sorted(JL)
    first, last = ys[0], ys[-1]
    T = Texts()
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    P = lambda v, dp=1: figure(v, dpct(v, dp), '%')
    Pt = lambda v, dp=1: figure(v, dpct(v, dp).replace(' budget', ''), '%')   # a tile: 14 characters
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

    WL, tied = LF.workbook_lines(JL, by)
    G = Texts()
    gr, trend = grid(G, JL, WL, tied)
    t_over = [x for x in trend if x['way'] == 'over']
    t_n = sum(1 for r in gr['rows'] if r['u'])
    fund = fund_series(JL)
    f0, f1 = min(fund), max(fund)
    BV = B['aug']
    ly, w2 = BV['coverage']['line_years'], BV['within_2pct']

    f = LD.fact
    span = '%s–%s' % (C.fy(first), C.fy(last))
    bspan = '%s–%s' % (C.fy(min(B['by_year'])), C.fy(max(B['by_year'])))
    facts = [
        f('bsal', Pt(bs_pct, 2), 'salary lines against budget, documents, %s' % bspan, 'published',
          label_figures={'a': F(min(B['by_year'])), 'b': F(max(B['by_year']))}),
        f('both', Pt(bo_pct, 2), 'everything else against budget, documents, %s' % bspan, 'published',
          label_figures={'a': F(min(B['by_year'])), 'b': F(max(B['by_year']))}),
        f('jsal', N(len(sal_under), 'years'), 'years of %d salary lines spent under the vote, journal'
          % len(ys), 'published', label_figures={'n': N(len(ys), 'years')}),
        f('joth', N(len(oth_over), 'years'), 'years of %d everything else spent over the vote, journal'
          % len(ys), 'published', label_figures={'n': N(len(ys), 'years')}),
        f('trend', N(len(trend), 'lines'), 'lines of %d usually missing one way, by median'
          % t_n, 'published', label_figures={'n': N(t_n, 'lines')}),
        f('tover', N(len(t_over), 'lines'), 'of them usually over budget', 'published'),
        f('w2', N(w2, 'line-years'), 'line-years of %d within 2%% of budget, documents' % ly,
          'published', label_figures={'n': N(ly, 'line-years')}, allow=('2%',)),
        f('thi', Pt(t_hi), 'out-of-district tuition, its worst year over', 'published'),
        f('tlo', Pt(t_lo), 'out-of-district tuition, its worst year under', 'published'),
        f('cut', N(len(after_cut), 'line-years'), 'of %d giving budget up, restarted high next year'
          % len(cut_lines), 'published', label_figures={'n': N(len(cut_lines), 'line-years')}),
        f('track', N(within[last], 'lines'), 'lines of %d within 2%% of their vote, %s'
          % (usable_n[last], C.fy(last)), 'published',
          label_figures={'y': F(last), 'n': N(usable_n[last], 'lines')}, allow=('2%',)),
        f('fund', N(len(fund), 'years'), 'years of %d the school fund spent under its final budget'
          % len(fund), 'published', label_figures={'n': N(len(fund), 'years')}),
    ]

    def con(text, rests, figs, so, so_figs=None):
        return TP.conclusion(text, rests, figs, so=so, so_figures=so_figs)
    conclusions = [
        con('Salary lines came in under their vote in %d of %d journal years; the documents agree, at %s.'
            % (len(sal_under), len(ys), dpct(bs_pct, 2)), ['jsal', 'joth', 'bsal', 'both'],
            {'a': N(len(sal_under), 'years'), 'b': N(len(ys), 'years'), 'c': P(bs_pct, 2)},
            'A salary vote leaves room the year usually does not use; that room is where a surplus '
            'starts. Why, post by post, the books do not say.'),
        con('%d of %d lines usually miss one way, %s–%s: %d over budget, %d under.'
            % (len(trend), t_n, C.fy(min(WL)), C.fy(last), len(t_over), len(trend) - len(t_over)),
            ['trend', 'tover', 'w2'],
            {'a': N(len(trend), 'lines'), 'b': N(t_n, 'lines'), 'x': F(min(WL)), 'y': F(last),
             'c': N(len(t_over), 'lines'), 'd': N(len(trend) - len(t_over), 'lines')},
            'Most lines miss both ways and cancel; the few that lean one way are where a vote and its '
            'line part company year after year.'),
        con('Out-of-district tuition ran from %s to %s, %s–%s.'
            % (dpct(t_hi), dpct(t_lo), C.fy(min(btu)), C.fy(last)), ['thi', 'tlo'],
            {'a': P(t_hi), 'b': P(t_lo), 'x': F(min(btu)), 'y': F(last)},
            'No trend to project: the site’s projection holds this line flat rather than growing it at a rate.'),
        con('%d of %d times a line gave budget up mid-year, its next vote was %s or more above its spending.'
            % (len(after_cut), len(cut_lines), C.pct(fl(SHARE) * 100, 0)), ['cut'],
            {'a': N(len(after_cut), 'line-years'), 'b': N(len(cut_lines), 'line-years'),
             's': figure(fl(SHARE) * 100, C.pct(fl(SHARE) * 100, 0), '%')},
            'Each is a question for the next budget: was the cut a one-year saving, or a line set high?'),
    ]
    yrs = sorted(set(BOOK_YEARS) | set(JL))
    sig = across(T, B, JL, WL)
    fsrc = lambda k: [fl(fund[y][1] - fund[y][2]) if fund[y][0] == k else None for y in sorted(fund)]
    fund_chart = TP.series(
        'What the school fund left unspent', [C.fy(y) for y in sorted(fund)],
        [TP.track('Finance Committee workbook', fsrc('workbook'), 'stated', 'bar'),
         TP.track('School journal', fsrc('ledger'), 'published', 'bar')], '$', kind='bar',
        note='The school general fund, final budget less spent, orders still owed counted. The '
             'workbook to %s, the journal from %s; where both exist they agree.'
             % (C.fy(first - 1), C.fy(first)),
        note_figures={'a': F(first - 1), 'b': F(first)})
    blocks = [
        TB.custom('bva-across', 'Every line, every year', sig, place='lead',
                  figures=sorted(T.figures), allow=sorted(T.literals),
                  basis=('record', 'The budget documents (one year the workbook), then the school journal; never added'),
                  alt='Dot chart, one column per fiscal year from %s to %s: each dot one school line, '
                      'placed by what it spent against what it was voted, salary lines and the rest in '
                      'two colours, with a mark for all the lines together; the years from the budget '
                      'documents, the workbook and the accounting system shaded apart' % (C.fy(yrs[0]), C.fy(yrs[-1])),
                  so=('Each year’s mark sits near the vote while its dots spread far above and below '
                      'it: the total is quiet because lines miss both ways and cancel.', None, ())),
        TB.chart(fund_chart, place='lead',
                 so=('Every bar is above zero: the fund as a whole never spent past its final budget, '
                     'while the lines inside it missed both ways.', None, ())),
        TB.custom('bva-grid', 'Each line, year by year', gr, place='lead',
                  figures=sorted(G.figures), allow=sorted(G.literals),
                  basis=('record', 'The Finance Committee workbook, then the school journal; a year from one only'),
                  alt='Table, one row per school line and one column per fiscal year from %s to %s: each '
                      'cell what the line spent less what it was voted that year, shaded by how far, '
                      'marked U, O or R where it was flagged underfunded, overbudgeted or restarted '
                      'high; each column headed with its flag counts, and the journal years linking to '
                      'that year in the FY breakdown' % (C.fy(min(WL)), C.fy(last)),
                  so=('A line flagged year after year is a pattern in how it is budgeted; one flagged '
                      'once is a year’s event, and that year’s FY breakdown shows what moved.', None, ())),
        TB.explain('How the three records differ', [
            ('**The budget documents** print a budget and an actual column the district wrote. Lines '
             'are read with the rules of the August analysis: a line under $10,000, a cell two '
             'documents disagree about, and FY2021 are not counted: that year the documents print the '
             'budget in the actual column. The dot chart reads them, and FY2021 from the workbook.',
             None, ('$10,000', 'FY2021')),
            ('**The Finance Committee workbook** pastes per-year MUNIS exports side by side, by '
             'account, with transfers. A person assembled it, so it is stated, not proof; in %s and '
             '%s it equals the journal on every line. The grid reads it before %s.'
             % (C.fy(tied[0][0]), C.fy(tied[1][0]), C.fy(first)),
             {'a': F(tied[0][0]), 'b': F(tied[1][0]), 'c': F(first)}, ()),
            '**The school journal** is the Town’s own accounting record, and every line here ties to '
            'its year-end report. It also records re-charges to other funds, which the workbook does not.',
            '**They are never added together.** A line-year is read from one record only.',
        ], place='end', tone='define'),
    ]
    tu_chart = TP.series(
        'Out-of-district tuition against its vote', [C.fy(y) for y in sorted(set(btu) | set(tu))],
        [TP.track('Budget documents', [btu.get(y) if y not in tu else None
                                       for y in sorted(set(btu) | set(tu))], 'stated', 'bar'),
         TP.track('School journal', [tu.get(y) for y in sorted(set(btu) | set(tu))], 'published', 'bar')],
        '%', kind='bar', decimals=1,
        note='Private and collaborative tuition: above zero, spent over budget; below, under. The '
             'documents, then the journal from %s.' % C.fy(first),
        note_figures={'y': F(first)})
    # THE SAME LIST AS THE GRID'S "Usual year" column (TJ, 30 October 2026: "'Lines that missed
    # the same way every year' should feed off the same list"): every line whose median year
    # leans one way by the page's rule. It replaced the August report's every-year test here.
    tw = sorted(trend, key=lambda x: (x['way'] != 'over', -abs(x['dollars'])))
    table = dict(caption='Lines that usually miss the same way', views=[dict(
        key='usual', label='Usual year', total_col=-1, kinds=['stated'] * 4,
        columns=['Usually', 'Years', 'Usual year, share of the vote', 'Usual year, dollars'],
        rows=[dict(label=x['name'], cells=[
            'over budget' if x['way'] == 'over' else 'under budget', C.num(x['years']),
            C.pct(abs(fl(x['share'])) * 100, 0) if x['share'] is not None else None,
            C.usd(abs(fl(x['dollars'])))]) for x in tw],
        note=trend_rule(Texts()) + ' %s–%s: the Finance Committee workbook, then the school journal.'
             % (C.fy(min(WL)), C.fy(last)))])
    return TP.page(
        ID,
        'School lines land near their vote in total every year, and far from it one by one, in '
        'both directions.',
        facts, conclusions, chart=tu_chart, table=table, blocks=blocks,
        sources=[
            dict(label='Lunenburg Budget Project — line-history.csv (every line the district’s '
                       'budget documents print, budget and actual)', href='/data/line-history.csv'),
            dict(label='Finance Committee — General fund budget against actuals, %s, by account '
                       '(a workbook assembled from MUNIS exports; stated)' % ('%s–%s' % (C.fy(2010), C.fy(2025))),
                 href='/docs/budget-workbooks/finance-committee/fy26-budget/general-fund-budget-vs-actuals-history.xlsx'),
            dict(label='Lunenburg Budget Project — gl-history.csv (that workbook, one row an account '
                       'a year)', href='/docs/data/gl-history.csv'),
            dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                       'line, %s)' % span, href=J.PUBLIC['journal']),
            dict(label='Town of Lunenburg — school general fund period-13 reports, %s (each line '
                       'tied to the cent)' % span, href=BFB.ledger_doc(last, 'gf-school')),
            dict(label='Lunenburg Budget Project — Budget versus actual, August 2026 (the findings '
                       'from the budget documents carried over here)',
                 href='/docs/analyses/budget-vs-actual.md')],
        draft=None if ID in REG.TOPICS else dict(title='School lines against budget', home='school-all-funds'))


def render(m=None):
    p = page(m)
    p['not_established'] = [
        'Why any line was voted above or below what it spent: a vacancy, a placement, a price '
        'change and a plan all produce the same figures.',
        'Which line a renamed line continued: lines are matched by account number only.',
        'Re-charges to other funds before %s: the Finance Committee workbook carries the general '
        'fund only, so a workbook year’s restarted-high flag reads spending after them.'
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
