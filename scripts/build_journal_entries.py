#!/usr/bin/env python3
"""JOURNAL ENTRIES IN THE SCHOOL BOOKS: how much moves by journal entry each year, against the years
before it, and which entries look unusual. A monitor and a topic page, from one pass.

    python3.11 scripts/build_journal_entries.py           # write the flags CSV and the topic payload
    python3.11 scripts/build_journal_entries.py --check   # fail if either would change
    python3.11 scripts/build_journal_entries.py --show    # print the year table and every flag

TJ, 27 November 2026: *"lets do a shcool year 'reclassification' report, comparing to previous
years"*, and then: *"we're going to need to be able to judge the reclassifications happening in
any given year. historically and live. almost lik emonitoring a system ;) a high rate of
relcassification and moving between accounts in odd ways souuld be flagged"*.

WHAT IT READS. `scripts/journal_join.py`'s entries (sources/data/munis-school-journal-entries.csv),
rebuilt in memory and required to match the file, so a page can never be built on a stale join.
Every figure is a posting to a SCHOOL account (journal.py, rule 11). Where an entry's other side is
a Town account it is not in Report 1, and the page says "the other side is not in the school
books", never what the other side was.

THE MONITOR, in two layers, both declared below as OURS:
  * YEAR RATES (`RATES`): a handful of measures per fiscal year, each compared with the MEDIAN of
    the years before it in the run (the baseline). A year is flagged on a rate when it exceeds
    `RATE_X` times its baseline and the floor `RATE_FLOOR` -- a ratio alone would flag $40 becoming
    $90. The first year has no baseline and says so; the second has a baseline of one year.
  * ENTRY RULES (`RULES`): the red flags of journal entry testing -- the auditing standard's
    screen for entries that need a second look (AU-C 240 / ISA 240 name entries made at the
    period end, entries reversed or corrected, round or unexplained entries, and unusual account
    combinations). Each rule here is one of those, with its threshold and its reason. A flag
    says an entry is UNUSUAL. It never says it is wrong (rule 7, rule 8).

LIVE, WITHOUT A FEED. The journal arrives by records request, not daily. When a delivery holds a
year that is still open and short of June, every year is cut at that year's last period
(`through`), so a part-year is compared with the same months of the years before it -- like for
like (rule 6) -- and the newest year is flagged with no code change.
"""
import argparse
import csv
import io
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import journal as J  # noqa: E402
import journal_join as JJ  # noqa: E402

FLAGS_CSV = os.path.join(J.DATA, 'journal-entry-flags.csv')
ID = 'journal-entries'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
D0 = Decimal(0)

# ---------------------------------------------------------------- thresholds, ours
BIG = Decimal(10000)        # an entry this size or more is worth a second look on these rules
REWORK_MIN = Decimal(1000)  # a reversal or correction smaller than this is housekeeping
LATE_MONTHS = 2             # booked this many months after the month its own tag names
RATE_X = 2                  # a year rate past twice its baseline ...
RATE_FLOOR = {'dollars': Decimal(25000), 'count': 5, 'share': Decimal('0.005')}  # ... and past this

FISCAL_MONTH = {m: (m - 7) % 12 + 1 for m in range(1, 13)}   # July = 1 ... June = 12


def money(d):
    return '%.2f' % d


# ---------------------------------------------------------------- loading
def entries():
    rows = JJ.build()
    if JJ.render(rows) != (open(JJ.OUT, encoding='utf-8', newline='').read()
                           if os.path.exists(JJ.OUT) else ''):
        raise SystemExit('build_journal_entries: %s is stale; run scripts/journal_join.py first'
                         % os.path.relpath(JJ.OUT, ROOT))
    for r in rows:
        r['fy'] = int(r['fiscal_year'])
        for f in ('debits', 'credits', 'net', 'moved'):
            r[f] = Decimal(r[f])
        r['chain_net'] = Decimal(r['chain_net'])
        r['p'] = int(r['period'])
    return rows


def through():
    """The last period of the newest year; every year is cut there. 13 when the year is complete."""
    last = J.YEARS[-1]
    ps = {int(r['period']) for r in J.lines() if r['fy'] == last}
    return 13 if (J.OPEN_FY != last or max(ps) >= 12) else max(ps)


def spending(cut):
    """School spending, every fund, by year: actuals and encumbrances on expense accounts, the
    site's 'spent' (journal.is_spent). The denominator of a share."""
    A = J.accounts()
    out = defaultdict(Decimal)
    for r in J.lines():
        if J.is_spent(r) and J.is_expense(A[r['account']]) and int(r['period']) <= cut:
            out[r['fy']] += r['amt']
    return dict(out)


def one_sided(e):
    """The part of an entry whose other side is not in the school books, counted once per chain:
    on the chain's first entry, as the chain's net. Accruals and Town charges included."""
    if e['chain'] and e['chain'] != e['entry']:
        return D0
    return abs(e['chain_net'])


def lines_of(rows):
    """The journal lines of these entries, by entry id."""
    want = {(r['fy'], r['journal']) for r in rows}
    by = defaultdict(list)
    for l in J.lines():
        if l['source'] in JJ.SOURCES and (l['fy'], l['journal']) in want:
            by[(l['fy'], l['journal'])].append(l)
    out = {}
    for (fy, j), v in by.items():
        parts = JJ.split(v)
        for i, g in enumerate(parts, 1):
            out[j if len(parts) == 1 else '%s-%d' % (j, i)] = g
    return out


# ---------------------------------------------------------------- the entry rules
def _fund_shift(lines):
    """Dollars an entry moves between fund groups: per group net, half the absolute sum."""
    A = J.accounts()
    g = defaultdict(Decimal)
    for l in lines:
        g[J.fund_group(A[l['account']])] += l['amt']
    net = sum(g.values(), D0)
    # Only what moves INSIDE the school books: a one-sided entry's net arrives from outside and
    # is not a move between two school fund groups.
    return (sum((abs(v) for v in g.values()), D0) - abs(net)) / 2, dict(g)


def _tag_gap(e):
    """Months from the month an entry's own tag names to the month it is dated, -5..6. Positive:
    booked after the month it names. Negative: the tag names a LATER month than the entry's date
    (`JE JUL` on an entry dated 17 June) -- keyed after the date it carries."""
    if not e['month_tag']:
        return 0
    d = (e['posted_month'] - int(e['month_tag'])) % 12
    return d - 12 if d > 6 else d


MEMO_DATE = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b')


def _after_close(e):
    """Dated in the last period, but its own text cites a memo dated after the fiscal year ended
    (`RECLASS SCHOOL MEMO 10/11/24` on an entry dated 30 June 2024), or its month tag names a
    month after June. Either way the entry was made after the year it is dated in had ended."""
    if e['p'] < 12 or e['kind'] == 'payroll accrual':   # an accrual names the later PAY date
        return False
    end = (e['fy'], 6, 30)
    for m, d, y in MEMO_DATE.findall(e['description']):
        y = int(y) + (2000 if len(y) == 2 else 0)
        if 1 <= int(m) <= 12 and (y, int(m), int(d)) > end:
            return True
    return _tag_gap(e) < 0


RULES = [
    ('outside', 'Other side not in the school books',
     'An entry of %s or more whose other side is a Town account -- not an accrual, not a recurring '
     'Town charge. The school books show money arriving or leaving, not where from.' % '{BIG}',
     lambda e, L: e['kind'] not in ('payroll accrual', 'town charge') and one_sided(e) >= BIG),
    ('rework', 'Reversed or corrected',
     'An entry that undoes or re-posts an earlier one, %s or more. A correction is how a ledger '
     'should fix a mistake; a year with many is a year with many mistakes to fix.' % '{REWORK_MIN}',
     lambda e, L: e['kind'] in ('reversal', 'correction')
     and max(e['moved'], abs(e['net'])) >= REWORK_MIN),
    ('duplicate', 'Undoes a duplicate',
     'The entry says it reverses a duplicate posting: the same thing was posted twice.',
     lambda e, L: 'DUPLICATE' in e['description'].upper()),
    ('funds', 'Moves cost between fund groups',
     'Moves %s or more between the general fund, the grants, the revolving funds, the circuit '
     'breaker or capital, inside the school books. Which fund pays is what a budget vote '
     'controls.' % '{BIG}',
     lambda e, L: _fund_shift(L)[0] >= BIG),
    ('late', 'Booked months after the month it names',
     'Its own month tag names a month %d or more months before the date it carries.' % LATE_MONTHS,
     lambda e, L: _tag_gap(e) >= LATE_MONTHS),
    ('after', 'Cites a date after the year closed',
     'Dated in June, but its own description cites a memo from after 30 June, or its month tag '
     'names a later month: a post-closing entry. An entry cannot cite a memo before the memo '
     'exists, so it was made after the year it is dated in had ended.',
     lambda e, L: _after_close(e)),
    ('blank', 'No description',
     'Posted with no description at all, so the ledger does not say what it was.',
     lambda e, L: not e['description'].strip()),
]
RULE_IDS = tuple(r[0] for r in RULES)


def rule_text(t):
    return t.replace('{BIG}', '$%s' % format(BIG, ',.0f')).replace(
        '{REWORK_MIN}', '$%s' % format(REWORK_MIN, ',.0f'))


def flag(rows):
    L = lines_of(rows)
    out = []
    for e in rows:
        for rid, name, why, test in RULES:
            if test(e, L[e['entry']]):
                out.append((e, rid))
    return out


# ---------------------------------------------------------------- the year rates
RATES = [
    ('entries', 'Journal entries', 'count', lambda Y: Y['n']),
    ('moved', 'Moved between school accounts', 'dollars', lambda Y: Y['moved']),
    ('outside', 'Other side outside the school books, not accruals or Town charges', 'dollars',
     lambda Y: Y['outside']),
    ('rework', 'In entries that reverse or re-post another', 'dollars', lambda Y: Y['rework']),
    ('funds', 'Moved between fund groups', 'dollars', lambda Y: Y['funds']),
    ('after', 'Citing a date after the year closed', 'dollars', lambda Y: Y['after']),
    ('share', 'Everything journal entries moved, as a share of school spending', 'share',
     lambda Y: Y['share']),
]


def years(rows, cut):
    sp = spending(cut)
    L = lines_of(rows)
    out = {}
    for fy in J.YEARS:
        es = [e for e in rows if e['fy'] == fy and e['p'] <= cut]
        Y = dict(fy=fy, n=len(es), spent=sp.get(fy, D0))
        Y['by_kind'] = {k: dict(n=sum(1 for e in es if e['kind'] == k),
                                moved=sum((e['moved'] for e in es if e['kind'] == k), D0),
                                outside=sum((one_sided(e) for e in es if e['kind'] == k), D0))
                        for k in JJ.KINDS}
        Y['moved'] = sum((e['moved'] for e in es), D0)
        Y['onesided'] = sum((one_sided(e) for e in es), D0)
        Y['outside'] = sum((one_sided(e) for e in es
                            if e['kind'] not in ('payroll accrual', 'town charge')), D0)
        Y['rework'] = sum((max(e['moved'], abs(e['net'])) for e in es
                           if e['kind'] in ('reversal', 'correction')), D0)
        Y['funds'] = sum((_fund_shift(L[e['entry']])[0] for e in es), D0)
        Y['after'] = sum((e['moved'] + one_sided(e) for e in es if _after_close(e)), D0)
        Y['june'] = sum((e['moved'] + one_sided(e) for e in es if e['p'] >= 12), D0)
        Y['total'] = Y['moved'] + Y['onesided']
        Y['share'] = (Y['total'] / Y['spent']) if Y['spent'] else D0
        fs = defaultdict(Decimal)
        for e in es:
            for g, v in _fund_shift(L[e['entry']])[1].items():
                if e['kind'] not in ('payroll accrual', 'town charge') and Decimal(e['net']) == 0:
                    fs[g] += v
        Y['fund_net'] = dict(fs)
        out[fy] = Y
    return out


RATE_IDS = tuple(r[0] for r in RATES)
SHORT = {'entries': 'Entries', 'moved': 'Moved inside', 'outside': 'No school-side match',
         'rework': 'Undone or re-posted', 'funds': 'Between funds', 'after': 'Later-dated memo',
         'share': 'Share of spending'}


# What each measure MEANS, shown when a reader hovers or taps its column on the page.
MEANS = {
    'entries': 'How many journal entries the year holds: postings that move money between accounts '
               'rather than pay a bill or a payroll.',
    'moved': 'Dollars moved from one school account to another. Both sides are school accounts.',
    'outside': 'Dollars in entries whose other side is not a school account, leaving out summer pay '
               'owed at year end and the recurring Town charges (fuel, postage, rent, turf).',
    'rework': 'Dollars in entries that undo an earlier entry, or post it again after undoing it.',
    'funds': 'Dollars moved from one kind of fund to another: the general fund, grants, revolving '
             'funds, the circuit breaker, capital.',
    'after': 'Dollars in entries dated 30 June whose own description cites a memo dated after the '
             'year ended.',
    'share': 'Everything journal entries moved, as a share of what the schools spent from every fund.',
}


def baseline(Y, fy, f):
    prior = [f(Y[y]) for y in J.YEARS if y < fy]
    return statistics.median(prior) if prior else None


def rate_flags(Y):
    out = []
    for fy in J.YEARS:
        for rid, name, unit, f in RATES:
            b = baseline(Y, fy, f)
            v = f(Y[fy])
            if b is None:
                continue
            if v >= RATE_FLOOR[unit] and v > RATE_X * b:
                out.append((fy, rid, v, b))
    return out




# ---------------------------------------------------------------- the page
TITLE = 'School journal entries'
HOME = 'school-all-funds'
TRACKS = [  # the signature's bands: (label, value of a year). Every dollar an entry moved, once.
    ('Summer-pay accruals', lambda Y: Y['by_kind']['payroll accrual']['outside']),
    ('Town charges', lambda Y: Y['by_kind']['town charge']['outside']),
    ('Moves inside school accounts', lambda Y: Y['by_kind']['reclass']['moved']
     + Y['by_kind']['one-sided']['moved']),
    ('Reversed or corrected', lambda Y: Y['rework']),
    ('Other side outside the school books', lambda Y: Y['outside']),
]


def page(d):
    import conclusions as C
    from conclusions import figure
    import ladder as LD
    import topic as TP
    import topic_blocks as TB
    import topics as REG
    Y, cut, fl = d['Y'], d['cut'], d['flags']
    ys = list(J.YEARS)
    last, prev, first = ys[-1], ys[-2], ys[0]
    F = lambda y: figure(y, C.fy(y), 'fiscal year')                      # noqa: E731
    U = lambda v: figure(float(v), C.usd(float(v)), '$')                 # noqa: E731
    N = lambda n, unit: figure(n, C.num(n), unit)                         # noqa: E731
    xs = [C.fy(y) for y in ys]

    def fail(m):
        raise SystemExit('build_journal_entries: ' + m)

    # ---- the signature: every dollar journal entries moved, by what kind of entry
    chart = TP.series('What journal entries moved, by kind', xs,
                      [TP.track(n, [float(f(Y[y])) for y in ys], 'published', 'bar')
                       for n, f in TRACKS],
                      '$', kind='bar', stacked=True,
                      note='Every fund, school accounts only. %s’s year-end close is not in this '
                           'delivery.' % C.fy(J.OPEN_FY) if J.OPEN_FY else 'Every fund, school accounts only.',
                      note_figures={'y': F(J.OPEN_FY)} if J.OPEN_FY else None)
    acc = [Y[y]['by_kind']['payroll accrual']['outside'] for y in ys]
    out_last, out_prev = Y[last]['outside'], Y[prev]['outside']
    if not out_last > 10 * max(out_prev, 1):
        fail('the newest year no longer stands out on money with its other side outside; rewrite')
    f = LD.fact
    facts0 = [
        f('acclo', U(min(acc)), 'smallest summer-pay accrual, %s to %s' % (C.fy(first), C.fy(last)),
          'published', label_figures={'a': F(first), 'b': F(last)}),
        f('acchi', U(max(acc)), 'largest, the same years', 'published'),
        f('outl', U(out_last), 'other side outside the school books, %s' % C.fy(last), 'published',
          label_figures={'y': F(last)}),
        f('outp', U(out_prev), 'the same, %s' % C.fy(prev), 'published', label_figures={'y': F(prev)}),
    ]
    HEALTH = ('570001', '570008')     # health insurance and unemployment: the FY2026 entries
    Lh = lines_of(d['rows'])
    health = sum((one_sided(e) for e in d['rows'] if e['fy'] == last
                  and e['kind'] not in ('payroll accrual', 'town charge')
                  and all(l['object'] in HEALTH for l in Lh[e['entry']])), D0)
    if not health > out_last / 2:
        fail('health insurance is no longer most of %s’s one-sided entries; rewrite' % C.fy(last))
    con = TP.conclusion
    c0 = con('The summer-pay accrual was between %s and %s every year.'
             % (C.usd(float(min(acc))), C.usd(float(max(acc)))), ['acclo', 'acchi'],
             {'a': U(min(acc)), 'b': U(max(acc))},
             so='The largest entry each year is routine: pay earned in the school year, booked to it, paid in summer.')
    c1 = con('%s moved with its other side outside the school books in %s, against %s in %s.'
             % (C.usd(float(out_last)), C.fy(last), C.usd(float(out_prev)), C.fy(prev)),
             ['outl', 'outp'], {'a': U(out_last), 'y': F(last), 'b': U(out_prev), 'p': F(prev)},
             so='Health insurance entries are %s of it. The Town’s side of them is not held.'
                % C.usd(float(health)), so_figures={'h': U(health)})
    chart_block = TB.claims(TB.chart(chart, place='body', so='Accruals are the floor every year; '
                                     'what changes is what sits on top.'), [c0, c1], facts0)

    # ---- the monitor: what stood out each year, against that year's own usual level.
    # TJ, 27 November 2026, on the first version (rows = rates, cells "FY2024 $x (before: $y)"):
    # "i dont knwo what this is telling me". So a row is a YEAR, the sentence says what jumped and
    # by how many times, and the reader never divides.
    rated = [y for y in ys if y != first]
    rf = {(fy, rid): (v, b) for fy, rid, v, b in d['rate_flags']}
    fmtv = lambda unit, v: ('%.1f%%' % (100 * float(v))) if unit == 'share' else (  # noqa: E731
        C.num(int(v)) if unit == 'count' else C.usd(float(v)))

    def times(v, b):
        x = float(v) / float(b)
        return ('%.1f' % x) if x < 10 else C.num(int(round(x)))
    rows = []
    for fy in rated:
        hits = sorted([r for r in RATES if (fy, r[0]) in rf],
                      key=lambda r: -float(rf[(fy, r[0])][0]) / max(float(rf[(fy, r[0])][1]), 1.0))
        bits, allow = [], [C.fy(fy)]
        for rid, name, unit, fn in hits:
            v, b = rf[(fy, rid)]
            if b:
                bits.append('%s %s, %s times the usual %s' % (SHORT[rid].lower(), fmtv(unit, v),
                                                              times(v, b), fmtv(unit, b)))
                allow += [fmtv(unit, v), times(v, b), fmtv(unit, b)]
            else:
                bits.append('%s %s, where earlier years had none' % (SHORT[rid].lower(), fmtv(unit, v)))
                allow += [fmtv(unit, v)]
        if fy == J.OPEN_FY:
            bits.append('later-dated memos cannot be checked yet')
        why = ('; '.join(bits) + '.') if bits else 'Nothing more than double its usual level.'
        rows.append(TB.check_row((C.fy(fy), None, (C.fy(fy),)), (why[0].upper() + why[1:], None,
                                                                  tuple(allow)),
                                 {RATE_IDS.index(r[0]) for r in hits}))
    nflag = len(rf)
    monitor = TB.checks('What stood out each year', [SHORT[r[0]] for r in RATES], rows,
                        first='Year', second='What jumped, against its usual level',
                        tone='bad',
                        column_notes=[(MEANS[r[0]], None, ('30',) if '30' in MEANS[r[0]] else ())
                                      for r in RATES],
                        note=('Usual: the middle value of the years before. A mark: more than double '
                              'it. %s is the first year held, so it has nothing to compare with.'
                              % C.fy(first), None, (C.fy(first),)),
                        so=('A mark says a year is unusual against its own history, not that '
                            'anything in it was wrong.', None, ()))
    worst = max(rated, key=lambda y: sum(1 for (fy, _r) in rf if fy == y))
    nworst = sum(1 for (fy, _r) in rf if fy == worst)
    facts1 = [f('marks', N(nflag, 'marks'), 'measures more than double their usual, all years',
                'published'),
              f('worst', N(nworst, 'measures'), 'that stood out in %s, the most of any year'
                % C.fy(worst), 'published', label_figures={'y': F(worst)})]
    c2 = con('%s stood out on %s of %s measures, more than any other year.'
             % (C.fy(worst), C.num(nworst), C.num(len(RATES))), ['marks', 'worst'],
             {'y': F(worst), 'a': N(nworst, 'measures'), 'b': N(len(RATES), 'measures')},
             so='Each new delivery is scored the same way; a part-year against the same months before.')
    monitor = TB.claims(monitor, [c2], facts1)

    # ---- made after the year closed
    aft = {y: Y[y]['after'] for y in ys}
    na = Counter(e['fy'] for e, r in fl if r == 'after')
    closed = [y for y in ys if y != J.OPEN_FY]
    top = max(closed, key=lambda y: aft[y])
    cards = []
    for y in ys:
        if y == J.OPEN_FY:
            cards.append(TB.panel((C.fy(y), None, (C.fy(y),)), [('Citing a later date', 'not yet known', None)],
                                  sub='The year’s close was not in the delivery.'))
        else:
            cards.append(TB.panel((C.fy(y), None, (C.fy(y),)), [('Citing a later date', C.usd(float(aft[y])),
                                             'bad' if aft[y] else 'good'),
                                            ('Entries', C.num(na[y]), None)]))
    panels = TB.panels('Entries citing a date after the close', cards,
                       note=('Dated 30 June, citing a memo from after it, or tagged with a later '
                             'month. Accruals, which name a later pay date, are left out.', None, ('30',)),
                       so='A change to a year already closed moves what that year is reported to have spent.')
    facts2 = [f('aft', U(aft[top]), 'citing a date after the close, %s' % C.fy(top), 'published',
                label_figures={'y': F(top)}),
              f('aftn', N(na[top], 'entries'), 'entries, the same year', 'published')]
    c3 = con('%s of %s’s entries, %s, cite a memo or month after that year ended.'
             % (C.num(na[top]), C.fy(top), C.usd(float(aft[top]))), ['aft', 'aftn'],
             {'n': N(na[top], 'entries'), 'y': F(top), 'a': U(aft[top])},
             so='Each changes a year that had ended; the ledger does not record who approved it.')
    panels = TB.claims(panels, [c3], facts2)

    # ---- every flagged entry, newest first
    names = {r[0]: r[1] for r in RULES}
    by_e = defaultdict(list)
    for e, r in fl:
        by_e[e['entry']].append((e, r))
    views = []
    for y in reversed(ys):
        es = sorted({e['entry'] for e, r in fl if e['fy'] == y})
        if not es:
            continue
        rws = []
        for eid in es:
            e = by_e[eid][0][0]
            amt = max(e['moved'], abs(e['net']))
            rws.append(dict(label=eid, cells=[e['effective_date'], e['kind'], C.usd(float(amt)),
                                              '; '.join(names[r] for _e, r in by_e[eid]),
                                              e['description'] or '(none)']))
        views.append(dict(key='fy%d' % y, label=C.fy(y), total_col=None, kinds=['ledger'] * 5,
                          columns=['Dated', 'Kind', 'Amount', 'Flags', 'Description'], rows=rws,
                          note='Amount: what the entry moved inside school accounts, or its net '
                               'where the other side is outside them.'))
    table = dict(caption='Every flagged entry', views=views)

    # ---- the year table, with the change printed
    trows = []
    for y in reversed(ys):
        b = Y[y - 1] if y - 1 in Y else None
        ch = lambda k: ('+' if Y[y][k] >= b[k] else '') + C.usd(float(Y[y][k] - b[k])) if b else '—'  # noqa: E731
        trows.append(dict(label=C.fy(y), cells=[
            C.num(Y[y]['n']), C.usd(float(Y[y]['moved'])), ch('moved'), C.usd(float(Y[y]['onesided'])),
            C.usd(float(Y[y]['outside'])), ch('outside'), C.usd(float(Y[y]['rework'])),
            C.usd(float(Y[y]['funds'])), '%.1f%%' % (100 * float(Y[y]['share']))]))
    years_table = dict(caption='Each year against the last', views=[dict(
        key='years', label='By year', total_col=None, kinds=['ledger'] * 9,
        columns=['Entries', 'Moved inside', 'Change', 'One-sided', 'Outside, not accruals or charges',
                 'Change', 'Reversed or corrected', 'Between fund groups', 'Share of spending'],
        rows=trows,
        note='One-sided: an entry whose other side is not a school account, counted once per '
             'correction chain. Share: everything moved, over school spending, every fund.')])

    sources = [
        dict(key='journal', label='Lunenburg Budget Project — munis-school-journal.csv (every school '
                                  'journal line, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(key='entries', label='Lunenburg Budget Project — munis-school-journal-entries.csv (the '
                                  'lines joined into entries, with their other sides)',
             href='/docs/data/munis-school-journal-entries.csv'),
        dict(key='flags', label='Lunenburg Budget Project — journal-entry-flags.csv (every flag and '
                                'the rule that raised it)', href='/docs/data/journal-entry-flags.csv'),
        dict(key='provenance', label='Town of Lunenburg — how the journal reached us, and what was redacted',
             href='/docs/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md'),
    ]
    cite = TP.cite
    flow = ['finding',
            cite(chart_block, 'journal', 'entries'),
            cite(monitor, 'entries', 'flags'),
            cite(panels, 'entries', 'flags', 'journal'),
            cite(('table', 0), 'flags', 'entries', 'provenance'),
            cite(('table', 1), 'entries', 'journal'),
            'related', 'sources']
    return TP.page(
        ID,
        'Leaving out accruals and Town charges, %s of %s entries had no school-side match; %s: %s.'
        % (C.usd(float(out_last)), C.fy(last), C.fy(prev), C.usd(float(out_prev))),
        [], [], chart=None, table=table, tables=[years_table], sources=sources, flow=flow,
        finding_figures={'a': U(out_last), 'y': F(last), 'b': U(out_prev), 'p': F(prev)},
        draft=None if ID in REG.TOPICS else dict(title=TITLE, home=HOME))


NOT_ESTABLISHED = [
    'Why any entry was made. A flag says an entry is unusual against the rules and the years before; '
    'it does not say the entry was wrong.',
    'What the other side of a one-sided entry was: Report 1 holds school accounts only, and the '
    'Town’s ledger is held as account totals.',
    'Who approved an entry made after the year closed, or when it was keyed: the journal carries '
    'the date an entry is effective, and the memo date only where its description gives one.',
    'Whether FY2026 has entries made after its close: the delivery predates it.',
]


def render(d):
    p = page(d)
    p['not_established'] = NOT_ESTABLISHED
    return json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


# ---------------------------------------------------------------- outputs
FLAG_COLUMNS = ['fiscal_year', 'entry', 'rule', 'rule_name', 'kind', 'effective_date', 'period',
                'moved', 'net', 'chain_net', 'description', 'pairs_with', 'first_page']


def render_flags(fl):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FLAG_COLUMNS, lineterminator='\n')
    w.writeheader()
    names = {r[0]: r[1] for r in RULES}
    for e, rid in sorted(fl, key=lambda x: (x[0]['fy'], x[0]['entry'], RULE_IDS.index(x[1]))):
        w.writerow(dict(fiscal_year=e['fy'], entry=e['entry'], rule=rid, rule_name=names[rid],
                        kind=e['kind'], effective_date=e['effective_date'], period=e['period'],
                        moved=money(e['moved']), net=money(e['net']),
                        chain_net=money(e['chain_net']), description=e['description'],
                        pairs_with=e['pairs_with'], first_page=e['first_page']))
    return buf.getvalue()


def data():
    rows = entries()
    cut = through()
    Y = years(rows, cut)
    fl = [(e, r) for e, r in flag(rows) if e['p'] <= cut]
    return dict(rows=rows, cut=cut, Y=Y, flags=fl, rate_flags=rate_flags(Y))


def show(d):
    Y = d['Y']
    print('through period', d['cut'])
    print('%4s %4s %12s %12s %12s %12s %12s %12s %12s %7s' % ('FY', 'n', 'moved', 'onesided', 'outside',
                                                         'rework', 'funds', 'after', 'spent', 'share'))
    for fy in J.YEARS:
        y = Y[fy]
        print('%4d %4d %12.0f %12.0f %12.0f %12.0f %12.0f %12.0f %12.0f %6.2f%%' % (
            fy, y['n'], y['moved'], y['onesided'], y['outside'], y['rework'], y['funds'], y['after'],
            y['spent'], 100 * y['share']))
        print('      kinds', {k: (v['n'], int(v['moved']), int(v['outside']))
                             for k, v in y['by_kind'].items()})
        print('      fund_net', {k: int(v) for k, v in y['fund_net'].items()})
    for f in d['rate_flags']:
        print('RATE', f)
    c = Counter((e['fy'], r) for e, r in d['flags'])
    for fy in J.YEARS:
        print(fy, {r: c[(fy, r)] for r in RULE_IDS})
    for e, r in d['flags']:
        print('FLAG', e['fy'], r, e['entry'], e['kind'], e['moved'], e['net'], e['chain_net'],
              e['description'][:40])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()
    d = data()
    if a.show:
        show(d)
        return 0
    outs = [(FLAGS_CSV, render_flags(d['flags']))]
    outs.append((OUT, render(d)))
    if a.check:
        bad = [p for p, t in outs if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        for p in bad:
            print('STALE %s' % os.path.relpath(p, ROOT), file=sys.stderr)
        if bad:
            return 1
        print('journal entries: current (%d flags, %d year-rate flags)'
              % (len(d['flags']), len(d['rate_flags'])))
        return 0
    for p, t in outs:
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(t)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    c = Counter((e['fy'], r) for e, r in d['flags'])
    for fy in J.YEARS:
        print('FY%d flags: %d  (%s)' % (fy, sum(c[(fy, r)] for r in RULE_IDS),
                                        ', '.join('%s %d' % (r, c[(fy, r)]) for r in RULE_IDS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
