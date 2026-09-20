#!/usr/bin/env python3
"""Read a trust-fund table off a scanned annual-report page, and prove every row.

A library, used by `extract_stabilization.py`. Nothing here trusts a reading: a row is
returned only if the arithmetic the table itself states closes on it.

--------------------------------------------------------------------------------------
THE THREE THINGS THAT MAKE THESE PAGES HARD, AND WHAT EACH NEEDS
--------------------------------------------------------------------------------------

**1. They are photographs, slightly rotated.** A row's own observations do not share a y
and two adjacent rows do, so no clustering tolerance works: at 0.004 two funds merge, at
0.003 one fund splits from its own account number. The rotation is MEASURABLE from the
observations -- take each figure's nearest neighbour to the right, take the median slope
-- and once measured it is removable: `Y = y - slope*x`. FY2020 page 41 is -0.01033 from
158 pairs. In that coordinate a row shares a value and ordinary clustering works.

**2. The columns are different in different years.** FY2014 prints nine columns beginning
with PRINCIPAL BEGINNING BALANCE. FY2020 prints ten, beginning with BEGINNING MARKET
VALUE. Assuming one layout and checking it against the other is what made a correct
extraction look wrong. So the header is READ, per page, and the columns are mapped from
it -- never inferred from how many figures a row happens to carry.

**3. Values must be placed by POSITION, not by order.** A fund with no activity prints
nothing in those columns, so the figures that are present would shift left and every one
would land under the wrong heading. Each figure is assigned to the column whose centre it
is nearest, and an absent column stays absent.

--------------------------------------------------------------------------------------
THE PROOF
--------------------------------------------------------------------------------------

Two identities, both stated by the table, both checked on every row:

    principal + earnings + net earnings + transfers        =  ENDING CASH VALUE
    ending cash + opening unrealised + change in unrealised =  ENDING MARKET VALUE

where opening unrealised is itself derived -- beginning market less beginning principal
and earnings -- so the second identity ties the two ends of the row together through a
quantity the table never prints.

This matters more here than anywhere else in the archive, because these are OCR readings.
The cache visibly contains `S2,041,061.72`, `$1,968,108,91` and `$9,587,16`. A misread
digit does not survive both identities. A row that does is verified by the document
against itself.
"""
import re
import statistics

MONEY = re.compile(r'^\(?-?[$S]?-?[\d,]{1,15}[.,]\d{2}\)?$')
CODE = re.compile(r'^8\d{3}$')

# Column headings as the reports print them, mapped to one name each. The labels arrive as
# separate observations -- `BEGINNING` on one line and `MARKET VALUE` under it -- so they
# are matched on the words present in the column's x band rather than on a whole string.
HEADINGS = [
    (('BEGINNING', 'MARKET'), 'begin_market'),
    (('BEGINNING', 'PRINCIPAL'), 'begin_principal'),
    (('PRINCIPAL', 'BEGINNING'), 'begin_principal'),
    (('BEGINNING', 'EARNINGS'), 'begin_earnings'),
    (('EARNINGS', 'BEGINNING'), 'begin_earnings'),
    (('NET', 'EARNINGS'), 'net_earnings'),
    (('CONTRIB',), 'contrib_principal'),
    (('TRANSFERS', 'PRINCIPAL'), 'transfers_principal'),
    (('TRANSFERS', 'EARNINGS'), 'transfers_earnings'),
    (('DISBURSE',), 'disburse_principal'),
    (('ENDING', 'CASH'), 'ending_cash'),
    (('CHANGE', 'UNREALIZED'), 'change_unrealized'),
    (('UNREALIZED', 'GAIN'), 'unrealized'),
    (('ENDING', 'MARKET'), 'ending_market'),
]


def money(text):
    """A figure as printed, including the ways OCR mangles one.

    `S` for `$` and a comma where the decimal point belongs are both in the cache, and
    both are recoverable without guessing: the last two digits are always cents.
    """
    t = text.strip()
    neg = t.startswith('(') or t.endswith(')')
    t = t.strip('()').lstrip('$S').replace(',', '').replace('.', '')
    if not t.isdigit():
        raise ValueError(text)
    v = float(t[:-2] + '.' + t[-2:]) if len(t) > 2 else float(t)
    return -v if neg else v


def skew(boxes):
    """The page's rotation, measured from its own figures. See the module docstring."""
    vals = [b for b in boxes if MONEY.match(b['text'].strip())]
    slopes = []
    for v in vals:
        right = [w for w in vals if 0.02 < w['x'] - v['x'] < 0.18]
        if not right:
            continue
        w = min(right, key=lambda w: abs(w['y'] - v['y']))
        if abs(w['y'] - v['y']) < 0.01:
            slopes.append((w['y'] - v['y']) / (w['x'] - v['x']))
    return statistics.median(slopes) if len(slopes) >= 8 else 0.0


# WHAT EACH YEAR'S COLUMNS ARE, READ OFF ITS OWN HEADER AND WRITTEN DOWN.
#
# Not inferred. Two attempts to name columns from the heading words automatically both
# produced confident nonsense -- three columns claiming to be `begin_principal`, and a
# proportional word-split turning `TRANSFERS OF TRANSFERS OF ENDING CASH` (one Vision
# observation over three columns) into `TRANSFERS PRINCIPAL / OF EARNINGS / TRANSFERS
# VALUE`. Inferring a column's meaning from its position is the exact mistake
# `column_meaning` exists in this archive to prevent.
#
# So each layout is READ from the report's printed header and recorded here, in left-to-
# right order, and the identities below are what prove the reading was right. A year
# whose centre count does not match its recorded layout is refused rather than guessed at.
#
# FY2020, printed page 41, header reads:
#   ACCOUNT NUMBER | FUND NAME | BEGINNING MARKET VALUE | BEGINNING PRINCIPAL |
#   BEGINNING EARNINGS | NET EARNINGS | TRANSFERS OF PRINCIPAL | TRANSFERS OF EARNINGS |
#   ENDING CASH VALUE | CHANGE IN UNREALIZED GAIN/LOSS | UNREALIZED GAIN/LOSS |
#   ENDING MARKET VALUE
#
# FY2014, printed page 37-38, header reads:
#   FUND NAME | PRINCIPAL BEGINNING BALANCE | EARNINGS BEGINNING BALANCE |
#   CONTRIB TO PRINCIPAL | EARNINGS NET | DISBURSE FROM PRINCIPAL |
#   TRANSFERS OF EARNINGS | ENDING CASH VALUE | UNREALIZED GAIN/LOSS |
#   ENDING MARKET VALUE
#
# The same nine appear in FY2015, FY2016, FY2017 and FY2022. That is a PROPOSAL about
# those years, not a reading of each -- and the identities are what test it: a layout
# applied to the wrong table does not make the arithmetic close on real rows. Any year
# whose rows then fail is refused and needs its own header read.
NINE = ['begin_principal', 'begin_earnings', 'contrib_principal', 'net_earnings',
        'disburse_principal', 'transfers_earnings', 'ending_cash', 'unrealized',
        'ending_market']

# FY2020, printed page 41, header reads:
#   ACCOUNT NUMBER | FUND NAME | BEGINNING MARKET VALUE | BEGINNING PRINCIPAL |
#   BEGINNING EARNINGS | NET EARNINGS | TRANSFERS OF PRINCIPAL | TRANSFERS OF EARNINGS |
#   ENDING CASH VALUE | CHANGE IN UNREALIZED GAIN/LOSS | UNREALIZED GAIN/LOSS |
#   ENDING MARKET VALUE
TEN = ['begin_market', 'begin_principal', 'begin_earnings', 'net_earnings',
       'transfers_principal', 'transfers_earnings', 'ending_cash',
       'change_unrealized', 'unrealized', 'ending_market']

# EIGHT: the same nine without a contributions column, which several years do not print.
EIGHT = ['begin_principal', 'begin_earnings', 'net_earnings', 'disburse_principal',
         'transfers_earnings', 'ending_cash', 'unrealized', 'ending_market']

# SEVEN: no contributions and no separate unrealised column.
SEVEN = ['begin_principal', 'begin_earnings', 'net_earnings', 'transfers_earnings',
         'ending_cash', 'unrealized', 'ending_market']

# THE CANDIDATES, and why offering several is not guessing. Each was READ off a printed
# header; what is not known is which report uses which. Rather than assign one per year by
# eye across fifteen reports, every candidate of the right width is tried and the one the
# DOCUMENT'S OWN ARITHMETIC accepts is kept -- and only if it closes on enough rows to
# mean something. A wrong layout does not make real figures add up, which is what makes
# this a test rather than a preference.
# FY2025, printed page 33, "TRUST & STABILIZATION FUNDS HELD BY OTHER BANKS", header:
#   FUND NAME | BEGINNING PRINCIPAL | NET EARNINGS | TRANSFERS OF PRINCIPAL |
#   EXPENDITURES | ENDING CASH VALUE | CHANGE IN UNREALIZED GAIN/LOSS |
#   UNREALIZED GAIN/LOSS | ENDING MARKET VALUE
#
# A SECOND TABLE IN THE SAME REPORT, and the reason FY2025 looked unreadable: the pages
# I was reading carry a plain `TRUST FUND BALANCE` listing -- fund, balance, receipts,
# a dash -- which states no arithmetic and so can never prove a row. This one does.
# TJ found it by searching the PDF for "stabilization" while I was believing my own
# pipeline's report that the year had no table wide enough to be one.
BANKS = ['begin_principal', 'net_earnings', 'transfers_principal', 'disburse_principal',
         'ending_cash', 'change_unrealized', 'unrealized', 'ending_market']

# The same "held by other banks" table with its two unrealised columns empty, which is
# what FY2025 prints: nothing is carried at anything other than cash value that year, so
# those columns exist in the header and hold no figure anywhere on the page.
BANKS_6 = ['begin_principal', 'net_earnings', 'transfers_principal',
           'disburse_principal', 'ending_cash', 'ending_market']

CANDIDATES = [TEN, NINE, BANKS, BANKS_6, EIGHT, SEVEN]
MIN_PROVEN = 4

LAYOUTS = {
    2014: NINE, 2015: NINE, 2016: NINE, 2017: NINE, 2022: NINE,
    2020: ['begin_market', 'begin_principal', 'begin_earnings', 'net_earnings',
           'transfers_principal', 'transfers_earnings', 'ending_cash',
           'change_unrealized', 'unrealized', 'ending_market'],
}


def columns(boxes, Y, first_data_y, fy):
    """Column centres, named from the layout recorded for this year.

    Centres come from the FIGURES rather than the labels, because the figures are
    right-aligned and are what has to be assigned. The layout says what each one means.
    """
    vals = [b for b in boxes if MONEY.match(b['text'].strip()) and Y(b) < first_data_y + 1e-9]
    if not vals:
        return []
    # THE RIGHT EDGE, NOT THE LEFT. These figures are right-aligned, so `$91.78` and
    # `$2,254,933.99` in the same column begin thirty thousandths apart and END together.
    # Clustering on x0 split one column into three and merged others: a nine-column FY2025
    # page came back as five, all unnamed. Every year was losing columns this way.
    xs = sorted(b['x'] + b.get('w', 0.0) for b in vals)
    groups, cur = [], [xs[0]]
    for a, b in zip(xs, xs[1:]):
        if b - a > 0.025:
            groups.append(cur); cur = [b]
        else:
            cur.append(b)
    groups.append(cur)
    # TWO, NOT THREE. A column is a column even if only two funds have a figure in it --
    # and the "held by other banks" tables are small, eight rows or so, where transfers
    # and expenditures are used once or twice. Requiring three found five columns on a
    # nine-column FY2025 page and named none of them.
    # EVERY GROUP, even one of a single figure. On the "held by other banks" tables
    # EXPENDITURES is used once in the whole year, and dropping it shifted every column
    # right of it by one -- which the identities then refused, correctly and unhelpfully.
    centres = [statistics.median(g) for g in groups]

    return centres


def rows(boxes, fy):
    """Fund rows of one page: (code, name, {column: value}), before any verification."""
    m = skew(boxes)
    Y = lambda b: b['y'] - m * b['x']
    vals = [b for b in boxes if MONEY.match(b['text'].strip())]
    if not vals:
        return [], []

    SKIP = ('SUBTOTAL', 'GRAND', 'TOTAL', 'FUNDS HELD', 'STABILIZATION FUNDS',
            'TRUST FUNDS', 'FISCAL YEAR', 'FUND NAME', 'ACCOUNT')
    anchors = []
    for b in sorted(boxes, key=lambda b: -Y(b)):
        t = b['text'].strip()
        if MONEY.match(t):
            continue
        if not (CODE.match(t) or (len(t) > 6 and t[0].isalpha())):
            continue
        if any(s in t.upper() for s in SKIP):
            continue
        if anchors and abs(Y(anchors[-1]) - Y(b)) < 0.004:
            anchors[-1]['text'] += ' ' + t
            continue
        a = dict(b); a['text'] = t
        anchors.append(a)
    if not anchors:
        return [], []



    # WHERE THE DATA STARTS is the highest anchor that actually has figures beside it --
    # not simply the highest anchor. `TOWN OF LUNENBURG` is a line of text at the top of
    # every page and passes any name-shaped test, so taking the topmost anchor put the
    # boundary above the header and left every column unnamed.
    with_figures = [a for a in anchors
                    if sum(1 for v in vals if abs(Y(v) - Y(a)) < 0.006) >= 2]
    if not with_figures:
        return [], []

    # THE HEADER IS NOT A ROW. `CHANGE IN`, `NET EARNINGS`, `GAIN/LOSS` all look like fund
    # names to a name-shaped test, and once they are anchors the nearest-anchor rule hands
    # them the figures of the first real rows. The data boundary was already computed and
    # only used to find the header; it has to prune the anchors too.
    boundary = max(Y(a) for a in with_figures)
    anchors = [a for a in anchors if Y(a) <= boundary + 1e-9]

    # THE BAND IS HALF THE PAGE'S OWN ROW PITCH, and it has to be measured AFTER the
    # header is pruned. A column heading set on four tight lines -- `CHANGE IN`,
    # `GAIN/LOSS`, `NET EARNINGS` -- gives gaps of 0.004 where the real rows sit 0.0101
    # apart, so including them halved the band, no row kept enough figures to prove, and
    # the page came back empty rather than wrong. A constant would not have this problem
    # and would be wrong on any page set differently, which is why it is measured.
    ys = sorted((Y(a) for a in anchors), reverse=True)
    gaps = [a - b for a, b in zip(ys, ys[1:]) if 0.002 < a - b < 0.05]
    band = (statistics.median(gaps) / 2) if len(gaps) >= 3 else 0.004

    centres = columns(boxes, Y, boundary, fy)
    if not centres:
        return [], []

    # A FIGURE GOES TO ITS NEAREST ROW, within a looser cap than the band.
    #
    # A symmetric band cannot serve both failures seen here. Too tight and a tall row
    # loses its own ending cash and ending market -- the two columns everything is checked
    # against -- which is FY2015 and FY2017. Too loose and a row steals its neighbours',
    # arriving with fourteen figures for nine columns, which is FY2022.
    #
    # Nearest-anchor stops the stealing because a figure closer to the next fund goes
    # there; the looser cap catches a wrapped value that sits just outside its own row.
    def owner(v):
        return min(anchors, key=lambda a: abs(Y(v) - Y(a)))

    def place(layout):
        cols = [dict(x=c, name=n) for c, n in zip(centres, layout)]
        got = []
        for a in anchors:
            mine = [v for v in vals
                    if owner(v) is a and abs(Y(v) - Y(a)) < band * 1.6]
            cells = {}
            for v in mine:
                # RIGHT EDGE AGAINST RIGHT EDGE. `columns()` clusters on x0+w because the
                # figures are right-aligned; matching a value by its LEFT edge against a
                # column expressed as a right edge compares two different coordinates, and
                # the error is the width of the number. `$2,254,933.99` begins 0.055 left
                # of where it ends -- past the 0.05 cap -- so the widest figure in each
                # column was dropped or handed to the column before it. Six of seven proven
                # rows disappeared that way, and the one that survived moved page.
                right = v['x'] + v.get('w', 0.0)
                c = min(cols, key=lambda c: abs(c['x'] - right))
                if abs(c['x'] - right) > 0.05 or not c['name']:
                    continue
                try:
                    cells[c['name']] = money(v['text'])
                except ValueError:
                    pass
            code = CODE.match(a['text'].split()[0])
            got.append(dict(code=code.group(0) if code else '',
                            name=' '.join(a['text'].split()[1:] if code
                                          else a['text'].split()),
                            cells=cells, n_figures=len(mine)))
        return got, cols

    # Try every candidate of this page's width and keep whichever the arithmetic accepts.
    best = None
    for layout in CANDIDATES:
        if len(layout) != len(centres):
            continue
        got, cols = place(layout)
        n = sum(1 for r in got if verify(r['cells'])[0])
        if n >= MIN_PROVEN and (best is None or n > best[0]):
            best = (n, got, cols)
    if best:
        return best[1], best[2]

    # Nothing closed: fall back to the layout recorded for the year, so the caller can see
    # what it read, and the identities will reject the rows.
    layout = LAYOUTS.get(fy)
    if not layout or len(layout) != len(centres):
        return [], [dict(x=c, name=None) for c in centres]
    got, cols = place(layout)
    return got, cols


def verify(cells, tol=0.02):
    """The two identities. Returns (ok, why)."""
    need = ('ending_cash', 'ending_market')
    if not all(k in cells for k in need):
        return False, 'no ending cash or ending market to check against'
    inflow = sum(cells.get(k, 0.0) for k in
                 ('begin_principal', 'begin_earnings', 'net_earnings',
                  'contrib_principal', 'transfers_principal', 'transfers_earnings',
                  'disburse_principal'))
    if abs(inflow - cells['ending_cash']) > tol:
        return False, 'beginning + activity != ending cash (%.2f vs %.2f)' % (
            inflow, cells['ending_cash'])
    opening_unreal = 0.0
    if 'begin_market' in cells:
        opening_unreal = cells['begin_market'] - (cells.get('begin_principal', 0.0)
                                                  + cells.get('begin_earnings', 0.0))
    end = cells['ending_cash'] + opening_unreal + cells.get('change_unrealized',
                                                            cells.get('unrealized', 0.0))
    if abs(end - cells['ending_market']) > tol:
        return False, 'ending cash + unrealised != ending market (%.2f vs %.2f)' % (
            end, cells['ending_market'])
    return True, 'both identities hold'
