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

# A GROUP SEPARATOR MAY BE A COMMA OR A FULL STOP, because a scanner cannot tell them
# apart and this archive's pages are scans. `money()` below has always coped -- it strips
# every separator and takes the last two digits as cents -- but this MATCHER accepted only
# commas in the body, so a figure like `$21.523.05` was never recognised as a figure at
# all. Not misread: invisible. It was not placed in a column, its row could not close the
# table's own identity, and the row went unpublished.
#
# FY2019's general Stabilization Fund row is the worked example: `$21.523.05` of net
# earnings and `S1.848.802.86` of ending cash, on a row whose other four figures read
# perfectly. One unmatched separator cost the year.
MONEY = re.compile(r'^\(?-?[$S]?-?[\d.,]{1,15}[.,]\d{2}\)?$')
# The same shape, found ANYWHERE in a string rather than anchored to it, so a box
# holding two cells can be taken apart. Anchored matching is what silently drops them.
MONEY_TOKEN = re.compile(r'\(?-?[$S]?-?[\d.,]{1,15}[.,]\d{2}\)?')
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


def split_merged(boxes):
    """Split a box holding several figures into one box per figure.

    THE SINGLE BIGGEST LOSS IN THIS READER, and it is silent. OCR sometimes returns two
    adjacent cells as one observation -- `$68,790.10 $250,000.00`, `$176.77
    ($19,111.10)`, `$92,795.20 $226,328.90` -- and every test here asks whether the WHOLE
    text is a money value. A merged box answers no, so it is not a misread figure, it is
    no figure at all: the column loses its value, the row loses its arithmetic, and the
    page is reported as unreadable while being perfectly legible to a person.

    TJ, 20 September 2026, sending the FY2024 page: "i can almost guarantee you this data
    is all in the annual town report. you prob missed it." It was, and this is how. FY2024
    page 35 prints ten funds with a GRAND TOTALS line and every row footing exactly, and
    this reader returned nothing from it.

    THE SPLIT IS BY CHARACTER POSITION, which is an estimate and is stated as one. These
    are fixed-pitch accounting printouts, so a token's share of the string is a good
    proxy for its share of the box, and the reader only ever uses the RIGHT EDGE to
    assign a column -- the end of the last character, which is the part this gets most
    nearly right. A token that lands in the wrong column cannot invent agreement: the
    row's identity has to close either way, which is what makes an estimate safe to make
    here at all.
    """
    out = []
    for b in boxes:
        t = (b['text'] or '').strip()
        parts = [m for m in MONEY_TOKEN.finditer(t)]
        if not t or not parts:
            out.append(b)
            continue
        # A FUND NAME AND ITS FIRST FIGURE ARRIVE AS ONE OBSERVATION TOO, and that case
        # needs no second figure to be worth splitting. Vision runs the name into the
        # column beside it where the table's rule is faint:
        #
        #   `VEHICLE/EQUIPMENT STABILIZATION (MAIN STREE* $1,201,170.65`   FY2022 p43
        #   `ZONING INCENTIVE STABILIZATION (TD E $227,884.96`             FY2017 p39
        #
        # One money token and a name in front of it, so the `< 2` test above left the box
        # whole -- and a box whose whole text is not a figure carries no figure at all.
        # Both rows lost their BEGINNING PRINCIPAL, which is the first term of the cash
        # identity, so both were refused on a page where every other row closed. FY2022's
        # vehicle/equipment stabilization fund -- $1,457,123.63, the second largest
        # balance the town holds -- went unpublished for exactly this reason.
        #
        # THE LABEL IS KEPT, NOT DISCARDED. Splitting used to emit only the figures, so a
        # merged box surrendered the fund NAME as well; the row then had no anchor of its
        # own and its figures were handed to the fund above. Three letters of prose in
        # front of the first figure is the test, which `S2,041,061.72` and `(580,568.57)`
        # both fail -- a currency mark misread as a letter is not a fund name.
        prefix = t[:parts[0].start()]
        label = sum(c.isalpha() for c in prefix) >= 3
        if len(parts) < 2 and not label:
            out.append(b)
            continue
        w = b.get('w', 0.0)
        n = float(len(t))
        if label:
            c = dict(b)
            c['text'] = prefix.strip()
            c['w'] = w * (parts[0].start() / n)
            c['split_from'] = t
            out.append(c)
        for m in parts:
            c = dict(b)
            c['text'] = m.group(0)
            c['x'] = b['x'] + w * (m.start() / n)
            c['w'] = w * ((m.end() - m.start()) / n)
            c['split_from'] = t
            out.append(c)
    return out


def upright(boxes):
    """Turn a page the right way up, if the scanner fed it in backwards.

    FY2024's trust table comes off the scanner rotated 180 degrees: the fund names sit to
    the RIGHT of the figures (label centroid x 0.619 against 0.392) and the rows run down
    an inverted y. Every other page in fifteen annual reports has the names on the left,
    so the centroids are the test -- it needs no header, no keyword, and nothing typed in.

    A 180-degree turn is `x -> 1-x`, `y -> 1-y`, and a box's left edge becomes its right,
    so the width has to be carried across with it or every figure lands a number's width
    from where it belongs. That is the same coordinate mistake that cost six proven rows
    once already, which is why it is spelled out here.

    Returns the boxes unchanged where the page is the right way up.
    """
    labels = [b for b in boxes
              if not MONEY.match(b['text'].strip()) and len(b['text'].strip()) > 10]
    figs = [b for b in boxes if MONEY.match(b['text'].strip())]
    if len(labels) < 5 or len(figs) < 5:
        return boxes
    lx = sum(b['x'] for b in labels) / len(labels)
    fx = sum(b['x'] for b in figs) / len(figs)
    if lx <= fx:
        return boxes
    out = []
    for b in boxes:
        c = dict(b)
        c['x'] = 1.0 - (b['x'] + b.get('w', 0.0))
        c['y'] = 1.0 - (b['y'] + b.get('h', 0.0))
        out.append(c)
    return out


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

# FY2019, PDF page 45, "TRUST FUNDS STABILIZATION FUNDS", header:
#   ACCOUNT NUMBER | FUND NAME | BEGINNING PRINCIPAL | BEGINNING EARNINGS |
#   NET EARNINGS | TRANSFERS OF PRINCIPAL | TRANSFERS OF EARNINGS |
#   ENDING CASH VALUE | UNREALIZED GAIN/LOSS
#
# Seven figure columns and NO ENDING MARKET VALUE on the page: the header prints one --
# a lone `E` at x=0.99 is all that survives of it -- and not a single figure sits under
# it. So the second identity cannot be checked here at all, and `SEVEN` does not fit
# because it has `ending_market` last and no `transfers_principal`.
SEVEN_NO_MARKET = ['begin_principal', 'begin_earnings', 'net_earnings',
                   'transfers_principal', 'transfers_earnings', 'ending_cash',
                   'unrealized']

MIN_PROVEN = 4

# FY2023, PDF page 50, "TRUST FUNDS / FISCAL YEAR 2023 SUMMARY", header read off the
# page and written down here rather than inferred -- rule 13b, rule 4. Fourteen figure
# columns, the widest table in the run, left to right by the x of each heading:
#
#   ACCOUNT NUMBER (.08) | FUND NAME (.16) | BEGINNING MARKET VALUE (.25) |
#   BEGINNING PRINCIPAL (.31) | BEGINNING EARNINGS (.36) | NET INCOME (.40) |
#   REALIZED GAIN/LOSS (.44) | NET EARNINGS (.49) | TRANSFERS OF PRINCIPAL (.53) |
#   TRANSFERS OF EARNINGS (.58) | ENDING PRINCIPAL (.63) | ENDING EARNINGS (.68) |
#   ENDING CASH VALUE (.72) | CHANGE IN UNREALIZED GAIN/LOSS (.77) |
#   UNREALIZED GAIN/LOSS (.82) | ENDING MARKET VALUE (.87)
#
# `NET INCOME` and `REALIZED GAIN/LOSS` are the two COMPONENTS of `NET EARNINGS`, and
# `ENDING PRINCIPAL`/`ENDING EARNINGS` are the two components of `ENDING CASH VALUE`.
# None of the four is in verify()'s inflow list, deliberately: adding them would count
# the same money twice and no row would ever close. They are named so the extract can
# say what the column IS, not so the identity can use it.
#
# The OCR prints `EY 2023` for `FY 2023` and `GAN LOSS` for `GAIN/LOSS`; both are read
# through, because the heading is being used to name a position and a misread letter in
# a heading cannot make wrong arithmetic close.
FOURTEEN = ['begin_market', 'begin_principal', 'begin_earnings', 'net_income',
            'realized', 'net_earnings', 'transfers_principal', 'transfers_earnings',
            'ending_principal', 'ending_earnings', 'ending_cash', 'change_unrealized',
            'unrealized', 'ending_market']

CANDIDATES = [FOURTEEN, TEN, NINE, BANKS, BANKS_6, EIGHT, SEVEN, SEVEN_NO_MARKET]

# WHY FOURTEEN IS A CANDIDATE AND NOT ONLY A YEAR'S ENTRY BELOW. It was read off FY2023
# and recorded against FY2023 alone, and `LAYOUTS` is consulted only AFTER every
# candidate and the inference have failed -- so the four later years that print the same
# fourteen columns had no way to reach it. FY2022, FY2024 and FY2025 each came back as
# `14 centres, all unnamed` off a table that foots to the cent on every row.
#
# Offering it as a candidate is not loosening anything: a candidate is accepted only when
# the DOCUMENT'S OWN arithmetic closes on at least MIN_PROVEN rows under it, and a
# fourteen-column layout applied to a nine-column page is never even tried, because the
# widths must match. It is the same test the other seven pass.

LAYOUTS = {
    2014: NINE, 2015: NINE, 2016: NINE, 2017: NINE,
    # FY2023 IS READ AND STILL REFUSES, AND THE REASON IS NOT THE LAYOUT. PDF page 51 --
    # the page carrying STABILIZATION, SEWER CAPITAL RESERVE, HEALTH INSURANCE, OPEB and
    # SEWER OPEB -- prints these same fourteen columns; the page was rendered and read by
    # eye to be sure. Vision did not read those five rows: their whole figure block came
    # back as two tokens, `5=5=2255225229` and `4883322 1833332`, while the SUBTOTALS
    # line under them reads perfectly. Nothing about the columns can fix that. The
    # remedy is a re-OCR of that page, not a new header.
    2023: FOURTEEN,
    # FY2022 PRINTS THE FOURTEEN-COLUMN TABLE, NOT THE NINE. CLAUDE.md recorded that
    # FY2022 "refused" the nine columns proposed from FY2014 -- no row closed -- and read
    # that as a year waiting for somebody to look at the page. Somebody has now. PDF page
    # 41, "TRUST FUNDS / FISCAL YEAR 2022 SUMMARY", header read off the page:
    #
    #   ACCOUNT NUMBER | FUND NAME | BEGINNING MARKET VALUE | BEGINNING PRINCIPAL |
    #   BEGINNING EARNINGS | NET INCOME | REALIZED GAIN/LOSS | NET EARNINGS |
    #   TRANSFERS OF PRINCIPAL | TRANSFERS OF EARNINGS | ENDING PRINCIPAL |
    #   ENDING EARNINGS | ENDING CASH VALUE | CHANGE IN UNREALIZED GAIN/LOSS |
    #   UNREALIZED GAIN/LOSS | ENDING MARKET VALUE
    #
    # The refusal was right about the layout and wrong about the remedy: nothing was
    # missing from the page, the wrong header had been proposed for it. Rule 13c.
    2022: FOURTEEN,
    # FY2024, PDF page 34, and FY2025, PDF page 36, print the same fourteen. FY2025
    # sub-labels two of them -- `BEGINNING PRINCIPAL (Non-Expend)` and `BEGINNING
    # EARNINGS (Expendable)` -- which says what the money may be spent on and is not a
    # different column.
    #
    # FY2025 PRINTS NO STABILIZATION SECTION IN THIS TABLE AT ALL. Its trust summary is
    # one page, running CEMETERY to MISCELLANEOUS to GRAND TOTALS, and the Bartholomew
    # stabilization and OPEB funds that FY2021-FY2024 all carry here are simply not on
    # it. They appear on PDF page 35 as bank balances, with no arithmetic beside them,
    # so nothing on that page can prove a row. That is a fact about the FY2025 report,
    # not a gap in this reader.
    2024: FOURTEEN, 2025: FOURTEEN,
    # FY2019 WAS READ AND WRITTEN DOWN AND NEVER WIRED IN. SEVEN_NO_MARKET above carries
    # this year's header, read off the page and commented with it -- and the year was
    # missing from this dict, so columns() named nothing, rows() built nothing, and the
    # general Stabilization Fund had no FY2019 reading. The layout existed; the lookup
    # did not. TJ, pointing at the page: "it's just called 'stabilization'".
    2019: SEVEN_NO_MARKET,
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


def infer_layout(centres, place):
    """Find the ending-cash column by testing every position against the cash identity.

    Returns (rows, cols) if some hypothesis closes on at least MIN_PROVEN rows, else
    ([], []).

    WHERE THE SUM ENDS. The cash identity says some column is the ending cash and the
    activity to its left sums to it. That is a testable claim about each position, and on
    a real table exactly one closes it across many rows.

    AND WHERE IT STARTS. FY2021's table opens with BEGINNING MARKET VALUE, which is a
    fact about the fund and not a term of the identity: $1,237.25 + $519.85 + $35.82 =
    $1,792.92, and the $1,812.80 printed to their left takes no part in it. Summing from
    column zero meant nothing closed anywhere on that page. So the first column is allowed
    to sit outside the sum, and `outside_0` is the whole of the claim -- calling it the
    beginning market value would be naming a column the arithmetic has only told us to
    leave alone.

    TWO GUARDS AGAINST AN ACCIDENT. A fund carried at cash prints the same figure under
    ENDING CASH and ENDING MARKET, so "column 4 equals column 3" closes for a reason that
    has nothing to do with the arithmetic -- a proving row must therefore have two
    non-zero terms on its left, on at least half the rows that close. And the more terms
    an identity has the less likely it closed by chance, so among hypotheses tied on rows
    proven, the one with more terms wins.
    """
    best = None
    for s0 in (0, 1):
        for i in range(s0 + 2, len(centres)):
            head = (['outside_%d' % k for k in range(s0)]
                    + ['activity_%d' % k for k in range(s0, i)] + ['ending_cash'])
            rest = len(centres) - i - 1
            # AND WHETHER THE LAST COLUMN IS A TOTAL AT ALL. FY2021's table ends at
            # CHANGE IN UNREALIZED GAIN/LOSS and prints no ending market value, so
            # reading the last column as one put $1.90 where $1,792.92 belonged and the
            # second identity refused every row on the page -- a table that foots
            # perfectly, rejected for having one column fewer than assumed. Both
            # readings are tried and the arithmetic picks.
            tails = [['unreal_%d' % k for k in range(rest)]]
            if rest:
                tails.insert(0, ['unreal_%d' % k for k in range(rest - 1)]
                             + ['ending_market'])
            for tail in tails:
                layout = head + tail
                got, cols = place(layout)
                ok = [verify(r['cells']) for r in got]
                closed = [r for r, (good, _) in zip(got, ok) if good]
                # ONE ROW IS ENOUGH IF IT IS STRONG ENOUGH. FY2023's page proves
                # exactly one: ARTS LOTTERY, $21,963.71 + $9,827.19 + $0.00 - $12,670.00
                # = $19,120.90, with the market value beside it agreeing. Four figures
                # summing to a fifth at cent precision AND that fifth closing the second
                # identity is not a coincidence, and the four-row minimum was refusing it
                # only because the other funds on the page are dormant -- OCR kept their
                # ending cash and ending market, which are equal, so they close trivially
                # under the WRONG layout and not at all under the right one. The two
                # guards were fighting: the trivial-closure test correctly refused the
                # wrong layout, and the row count then refused the right one.
                strong_rows = sum(
                    1 for r, (good, why) in zip(got, ok)
                    if good and why == 'both identities hold'
                    and sum(1 for k, v in r['cells'].items()
                            if k.startswith('activity_') and v) >= 3)
                rich = sum(1 for r in closed
                           if sum(1 for k, v in r['cells'].items()
                                  if k.startswith('activity_') and v) >= 2)
                if strong_rows < 1:
                    if len(closed) < MIN_PROVEN:
                        continue
                    if rich * 2 < len(closed):
                        continue
                # Both identities beat one, same as among the written-down candidates.
                strong = sum(1 for good, why in ok
                             if good and why == 'both identities hold')
                score = (strong_rows, strong, len(closed), i - s0)
                if best is None or score > best[0]:
                    best = (score, got, cols)
    return (best[1], best[2]) if best else ([], [])


def rows(boxes, fy):
    """Fund rows of one page: (code, name, {column: value}), before any verification."""
    boxes = split_merged(upright(boxes))
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

    # ONE ROW, NOT TWO. The account number and the fund name are printed on the same line
    # and arrive as separate boxes, and on some years the scan puts them far enough apart
    # in Y to become two anchors -- so the row's figures are divided between them and
    # neither half foots. FY2017: `8129` took the ending market value and `ZONING
    # INCENTIVE STABILIZATION (TD` took the beginning balance, and the page proved nothing.
    #
    # It also cost the account numbers. FY2019 and FY2025 published their rows with an
    # empty `code` for exactly this reason: the code was a whole anchor of its own,
    # carrying no name, and the row that got written was the nameless one's neighbour.
    #
    # A bare code is merged into the nearest named anchor within the row band, and the
    # code is put at the front of the text where `CODE.match` on the first word will find
    # it -- which is the shape the writer already expects.
    bare = [a for a in anchors if CODE.fullmatch(a['text'].strip())]
    named = [a for a in anchors if a not in bare]
    for c in bare:
        near = [a for a in named if abs(Y(a) - Y(c)) < band * 1.6]
        if not near:
            continue
        a = min(near, key=lambda a: abs(Y(a) - Y(c)))
        a['text'] = '%s %s' % (c['text'].strip(), a['text'].strip())
    if named:
        anchors = named

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
        ok = [verify(r['cells']) for r in got]
        n = sum(1 for good, _ in ok if good)
        # THE STRONGER BASIS WINS FIRST. Relaxing verify() to accept the cash identity
        # alone lets more layouts clear MIN_PROVEN, and a layout proving four rows on one
        # identity must never beat one proving four on two. Ranked on (both, either) so
        # the relaxation can only ever ADD years, never reinterpret a year that already
        # reads.
        strong = sum(1 for good, why in ok if good and why == 'both identities hold')
        score = (strong, n)
        if n >= MIN_PROVEN and (best is None or score > best[0]):
            best = (score, got, cols)
    if best:
        return best[1], best[2]

    # NOTHING WRITTEN DOWN FITS. Before giving up, let the page's own arithmetic say where
    # the columns are.
    #
    # THE REASON THIS EXISTS. Every candidate above is a header somebody read off a
    # photograph and typed in, and there are at least five distinct table shapes across
    # fifteen annual reports -- plus OCR that drops a column here and merges two there, so
    # the shape ON THE PAGE is not the shape IN THE FILE. Hand-authoring a layout per year
    # got four years read and left ten unread, and each new one costs an hour of squinting.
    #
    # WHAT IT INFERS, AND WHAT IT REFUSES TO. The cash identity says: some column is the
    # ending cash, and everything to its left sums to it. That is a testable claim about
    # each candidate position, and on a real table exactly one position closes it across
    # many rows. So the POSITION of ending cash is established by the document. What is NOT
    # established is which of the columns to its left is net earnings and which is
    # transfers of principal -- the identity is a sum and cannot see the difference -- so
    # they are named `activity_0..n` and stay that way. Rule 13: read `column_meaning`,
    # and say `not established` where it is not.
    got, cols = infer_layout(centres, place)
    if got:
        return got, cols

    # Fall back to the layout recorded for the year, so the caller can see
    # what it read, and the identities will reject the rows.
    layout = LAYOUTS.get(fy)
    if not layout or len(layout) != len(centres):
        return [], [dict(x=c, name=None) for c in centres]
    got, cols = place(layout)
    return got, cols


def verify_from_prior(cells, prior_ending, tol=0.02):
    """Prove a row from LAST year's proven ending cash instead of this year's beginnings.

    A fund's beginning balance IS the previous year's ending balance. The table prints
    both -- `BEGINNING PRINCIPAL` + `BEGINNING EARNINGS` this year, `ENDING CASH VALUE`
    last year -- so they are two printings of one quantity, and where one is misread the
    other can carry the row.

    THE CASE THIS WAS WRITTEN FOR. FY2019's general Stabilization Fund prints beginning
    principal as `$1,524,952.91`, and the 6 is a scanned 5: with it the row misses its own
    identity by exactly $100,000 and was refused, losing the year. Every other figure on
    the row is clean. Taking FY2018's PROVEN ending cash instead:

        1,740,279.81  (FY2018 ending, proven by its own page's identity)
      +    21,523.05  (net earnings, as printed)
      +    87,000.00  (transfers of principal, as printed)
      = 1,848,802.86  = ENDING CASH as printed, to the cent

    That uses none of the misread figure. It is a stricter test than the ordinary one in
    one respect and weaker in another, and both matter: stricter because it spans two
    documents that were produced a year apart and must agree, weaker because it cannot
    check the beginning split at all. So it returns its own basis and never claims `both
    identities hold`.

    It is NOT a fallback to reach for whenever a row refuses. It requires a PROVEN prior
    reading of the same fund, and it must close to the cent; a row that needs any slack
    stays refused.
    """
    if 'ending_cash' not in cells or prior_ending is None:
        return False, 'no prior proven ending to carry forward'
    activity = sum(cells.get(k, 0.0) for k in
                   ('net_earnings', 'transfers_principal', 'transfers_earnings',
                    'contrib_principal', 'disburse_principal'))
    activity += sum(v for k, v in cells.items() if k.startswith('activity_'))
    if abs(prior_ending + activity - cells['ending_cash']) > tol:
        return False, ('prior ending + activity != ending cash (%.2f vs %.2f)'
                       % (prior_ending + activity, cells['ending_cash']))
    return True, 'last year\u2019s proven ending cash + this year\u2019s activity = ending cash'


def verify(cells, tol=0.02):
    """The document's own identities. Returns (ok, why), and `why` is the BASIS.

    TWO IDENTITIES WHERE THE PAGE PRINTS TWO, ONE WHERE IT PRINTS ONE. Some years' tables
    carry no ENDING MARKET VALUE column -- FY2019 prints the heading and puts no figure
    under it on any row -- and demanding both identities there is not rigour, it is
    refusing to read a table that foots perfectly. The cash identity is what pins
    `ending_cash`, which is the figure this extract publishes, so a row that closes it is
    proven for what we take from it.

    What the weaker basis does NOT establish is the meaning of the individual inflow
    columns: the identity is a SUM, and a sum does not change when its terms are
    permuted. So a cash-only row fixes which column is ending cash and which set are
    activity, and says nothing about which of those is net earnings rather than transfers
    of principal. Rule 13's `column_meaning` distinction, in the one place it bites.
    """
    if 'ending_cash' not in cells:
        return False, 'no ending cash to check against'
    # A NAMED COLUMN OR AN INFERRED ONE, SUMMED THE SAME WAY. `activity_*` columns come
    # from infer_layout() below, which knows from the arithmetic that a column is part of
    # the activity and does NOT know which part. The identity cannot tell them apart --
    # it is a sum, and a sum is blind to the order of its terms -- so naming them would be
    # asserting something the document has not said.
    inflow = sum(cells.get(k, 0.0) for k in
                 ('begin_principal', 'begin_earnings', 'net_earnings',
                  'contrib_principal', 'transfers_principal', 'transfers_earnings',
                  'disburse_principal'))
    inflow += sum(v for k, v in cells.items() if k.startswith('activity_'))
    if abs(inflow - cells['ending_cash']) > tol:
        return False, 'beginning + activity != ending cash (%.2f vs %.2f)' % (
            inflow, cells['ending_cash'])
    if 'ending_market' not in cells:
        return True, 'beginning + activity = ending cash'
    opening_unreal = 0.0
    if 'begin_market' in cells:
        opening_unreal = cells['begin_market'] - (cells.get('begin_principal', 0.0)
                                                  + cells.get('begin_earnings', 0.0))
    end = cells['ending_cash'] + opening_unreal + cells.get('change_unrealized',
                                                            cells.get('unrealized', 0.0))
    end += sum(v for k, v in cells.items() if k.startswith('unreal_'))
    if abs(end - cells['ending_market']) > tol:
        return False, 'ending cash + unrealised != ending market (%.2f vs %.2f)' % (
            end, cells['ending_market'])
    return True, 'both identities hold'
