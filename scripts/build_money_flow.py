#!/usr/bin/env python3
"""The money flow as a diagram — drawn from the ledger, with traced and assumed told apart.

    python3 scripts/build_money_flow.py
    python3 scripts/build_money_flow.py --check     # fail if the output is stale

Writes `notes/reference/data-model/money-flow.html`, beside `money-in.html` rather than
replacing it, so the two can be read against each other.

WHY A SECOND DIAGRAM RATHER THAN AN EDIT

`money-in.html` is organised around *"the level at which each trail goes cold"*, and it has
the cold point in the wrong place. On the REVENUE side the trail genuinely does go cold:
Chapter 70 lands in fund `0100` as unrestricted money and is thereafter indistinguishable
from property tax. Nothing closes that. But on the SPENDING side it does not go cold at
all — `dept 300` is 258 named accounts, and school money appropriated to other departments
is identifiable by account name.

The old page applied revenue-side uncertainty to the spending side and concluded it could
not know things the ledger states outright. **It understates what is knowable**, and every
figure on it is hand-typed besides. So this one is generated, and its whole design job is
to make the difference between a traced number and an apportioned one impossible to miss.

WHY BARS AND NOT A SANKEY

The first version was a four-column Sankey and it failed on its own terms. Height carried
value, so a $6,000 line became a two-pixel box with unreadable text stacked on it, and the
canvas was 1500px wide -- unusable on the phone most residents will open it on.

So: **bar LENGTH carries value, row height is fixed.** Every row is legible whatever it is
worth, the whole thing is one column that scrolls DOWN, and nothing needs a horizontal
scrollbar. A stage is a bar chart; the flow between stages is shown by ordering and by the
pot sitting between them, not by ribbons that cross.

The one thing the Sankey did well is kept: the diagonal edge is still refused. That is the
point of the pot. Every revenue line flows into fund `0100` and
**loses its identity there**. Money is fungible; no record ties a source to a department.
So the diagram deliberately refuses to draw a ribbon from Chapter 70 to the schools, which
is exactly what the old page drew seven of. What replaces them is the pot itself, drawn as
a single opaque block, with the loss stated on it.

Everything left of the pot is traced. Everything right of it is traced. The one thing
nobody can trace is the diagonal, and no amount of data will fix it.

TWO GRAINS, AND THE FILTERS THAT KEEP THEM APART

`ledger_snapshot` holds the same FY26 general fund twice: 67 department rows at period 9
and 635 account rows at period 12, tying within $4 on $51.2M. Three filters are
load-bearing on every query here and each has already been got wrong once — `level`, or
department rows sum on top of their own detail; `account_type`, or revenue stored NEGATIVE
nets against expense and the town's budget comes out as minus $997,871; and `period`, or
two different reports are added together.
"""

import argparse
import html
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'notes', 'reference', 'data-model', 'money-flow.html')
OUT2 = os.path.join(ROOT, 'notes', 'reference', 'data-model', 'money-flow-v2.html')

FY = 2026
P_DEPT = 9      # the report that carries department-level rows
P_ACCT = 12     # the report that carries account-level rows

# Layout. Heights are proportional to dollars throughout; nothing here is drawn to a
# size chosen for looks, because a diagram whose bars lie is worse than a table.
W, H = 1500, 980
TOP, BOT = 120, 60
COL = {'src': 60, 'pot': 470, 'dept': 830, 'use': 1230}
BOXW = 190
GAP = 5


def db():
    if not os.path.exists(DB):
        raise SystemExit(f'{DB} missing. Run: python3 scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def revenue_sources(c, top=9):
    """Every general-fund revenue line, biggest first, with a remainder block.

    A remainder rather than a truncation: dropping the tail would make the column shorter
    than the pot it flows into, and a reader would have no way to see that it had been cut.
    """
    rows = c.execute(f"""
        SELECT name, SUM(budgeted) v FROM v_revenue
        WHERE fy={FY} AND fund='0100' GROUP BY name
        HAVING v > 0 ORDER BY v DESC""").fetchall()
    total = sum(r['v'] for r in rows)
    head = [(r['name'], r['v']) for r in rows[:top]]
    rest = total - sum(v for _, v in head)
    if rest > 0:
        head.append((f'{len(rows)-top} smaller lines', rest))
    return head, total


def departments(c):
    """Where the appropriation goes, with the school-relevant departments named.

    The residual block is not decoration either: revenue budgeted exceeds what the omnibus
    appropriates, and the difference funds warrant articles, transfers and reserves. Left
    out, the diagram would silently fail to balance and look tidier for it.
    """
    rows = c.execute(f"""
        SELECT a.dept, a.name, l.original v
        FROM ledger_snapshot l JOIN account a USING (account_id)
        WHERE l.fy={FY} AND l.period={P_DEPT} AND a.level='department'
          AND a.account_type='expense' AND a.fund='0100'""").fetchall()
    by = {r['dept']: (r['name'], r['v']) for r in rows}
    omnibus = sum(v for _, v in by.values())
    named = ['300', '310', '820', '914']
    out = [(by[d][0], by[d][1], d) for d in named if d in by]
    out.append(('All other departments (63)',
                omnibus - sum(v for _, v, _ in out), 'other'))
    return out, omnibus


def school_elsewhere(c):
    """Accounts outside dept 300 whose own NAME identifies them as school money.

    Named, never inferred from a share. `SCHRESSTIP` is included with its abbreviation
    shown because the amount is immaterial and the expansion is a guess; the pension is
    included as a split we cannot make rather than a number we can.
    """
    rows = c.execute(f"""
        SELECT a.account_id, a.dept, a.name, l.original v
        FROM ledger_snapshot l JOIN account a USING (account_id)
        WHERE l.fy={FY} AND l.period={P_ACCT} AND a.level='account'
          AND a.fund='0100' AND a.dept <> '300' AND l.original > 0
          AND a.account_id IN ('0100-19142-570018','0100-13102-532000',
                               '0100-18202-560001','0100-12101-519021')
        ORDER BY l.original DESC""").fetchall()
    return [(r['account_id'], r['dept'], r['name'], r['v']) for r in rows]


def function_names(c):
    """DESE function codes as the DISTRICT's own book names them, not as we remember them.

    `budget_line` carries 45 labels of the form `2710 - Guidance Exp.`. A code with no such
    label is drawn as the bare code: naming it from general knowledge of the DESE chart of
    accounts would be a derived thing quoted as an observed one, which is the failure this
    whole project is organised against.
    """
    names = {}
    for (label,) in c.execute("SELECT DISTINCT label FROM budget_line"):
        m = re.match(r'^(\d{4})\s*[-–]\s*(.+)$', (label or '').strip())
        if m and m.group(1) not in names:
            names[m.group(1)] = m.group(2).strip()
    return names


def school_uses(c, top=11):
    """What dept 300's 258 accounts pay for, grouped by function code."""
    rows = c.execute(f"""
        SELECT a.function f, SUM(l.original) v, COUNT(*) n
        FROM ledger_snapshot l JOIN account a USING (account_id)
        WHERE l.fy={FY} AND l.period={P_ACCT} AND a.dept='300' AND a.function IS NOT NULL
        GROUP BY a.function ORDER BY v DESC""").fetchall()
    names = function_names(c)
    total = sum(r['v'] for r in rows)
    out = [(r['f'], names.get(r['f']), r['v'], r['n']) for r in rows[:top]]
    rest = total - sum(v for _, _, v, _ in out)
    if rest > 0:
        out.append((None, f'{len(rows)-top} smaller functions', rest, 0))
    return out, total


def own_funds(c):
    """The schools' own funds — enumerated by NUMBER, never matched on name.

    This function used to filter on names containing SCHOOL, EXTENDED DAY, ATHLETIC or
    CIRCUIT. That silently dropped **fund 1301, the athletics revolving fund**, because the
    town calls it `CHAPTER 658 REVOLVING FUND`. The bug survived being written about twice
    — `LEDGER-STRUCTURE.md` says never identify a thing by its name in this ledger, and
    `MONEY-NODES.md` lists 1301 as the proof — and was finally caught by the diagram,
    which drew Athletics with no source box at all.

    That is the argument for the diagram, incidentally. A missing row in a table looks like
    a short table. A missing box under a line looks wrong.
    """
    return [(r['fund'], r['name'], r['revenue'] or 0, r['spent'] or 0)
            for r in c.execute(f"""
        SELECT fund, name, revenue, spent FROM v_fund_year
        WHERE fy={FY} AND period={P_DEPT} AND revenue > 0
          AND (fund LIKE '13%' OR fund LIKE '15%' OR fund LIKE '22%' OR fund LIKE '26%'
               OR fund LIKE '27%' OR fund LIKE '28%' OR fund LIKE '29%')
        ORDER BY revenue DESC""")]


# ---------------------------------------------------------------- the programme map
#
# A PROGRAMME is a thing the town does. It is not a fund and not a function code, and that
# is the whole point of this page: **a programme's money arrives from more than one place,
# and the budget shows one of them.**
#
# `inside`  function codes within dept 300 — appropriated, traced to named accounts
# `outside` funds that pay for the same programme without entering the appropriation
# `edge`    how sure we are the outside money goes here:
#             traced      an account or journal shows it
#             restricted  the fund exists for this and nothing else, but no expense report
#                         for special revenue funds exists, so it is NOT OBSERVED
#             missing     the money is known to be collected and cannot be located at all
PROGRAMMES = [
    ('Special education', ['2110', '2310', '2320', '2330', '9300', '9400'],
     [('2640', 'restricted'), ('2813', 'restricted'), ('2814', 'restricted'),
      ('2832', 'restricted'), ('2758', 'restricted')],
     'The largest programme in the budget and the one with the most money outside it. The '
     'circuit breaker reimburses high-cost placements; the #240 grants are read as IDEA '
     'from outside this archive, and they are the two biggest grant spends.'),
    ('Transportation', ['3300'],
     [('BUSFEES', 'missing')],
     'The appropriation is NET — the district subtracts expected fee revenue before asking '
     'the town. Its own workbook says so. **The fees are charged and cannot be located in '
     'any ledger we hold.**'),
    ('Athletics', ['3510'],
     [('1301', 'restricted')],
     'Fund 1301 is the athletics revolving fund — the town calls it CHAPTER 658, which is '
     'why every name-based search missed it. Fees in, programme costs out.'),
    ('Food service', [],
     [('2200', 'restricted')],
     '**Entirely outside the appropriation.** There is no food service function code inside '
     'dept 300 at all. A reader of the school budget sees nothing about feeding children.'),
    ('Extended day and after school', [],
     [('1312', 'restricted'), ('1305', 'restricted'), ('1306', 'restricted')],
     '**Entirely outside the appropriation.** Fee-funded programmes that appear nowhere in '
     'the $26m.'),
    ('Everything else in the school budget', None, [], ''),
]

# School money the town appropriates to OTHER departments. Not a programme split -- these
# never touch dept 300 at all.
ELSEWHERE_MAP = [
    ('0100-13102-532000', 'Monty Tech assessment',
     'A different school district, assessed on the town. Education spending that the '
     'Lunenburg school budget does not contain and the School Committee does not control.'),
    ('0100-19142-570018', 'School retiree health insurance',
     'Health insurance for former school employees, appropriated under the insurance '
     'department.'),
    ('0100-18202-560001', 'Pension — school share unknown',
     'The county retirement assessment covers town and school staff together. Teachers are '
     'in the state system instead, and that cost Lunenburg never sees at all.'),
    ('0100-12101-519021', 'School resource stipend',
     'Inside the police department. The expansion of the abbreviation is inferred.'),
]


# ---------------------------------------------------------------- rendering


def money(v):
    return f'${v:,.0f}'


def athletics(c):
    """Both sides of athletics, which is the clearest case of the whole problem.

    The appropriated side is function 3510 inside dept 300. The fee side is a revolving
    fund -- and that fund is NOT in the town's fund-balance report, so it is known only
    from the district's own athletics documents. A page about how money reaches the
    schools that showed the first and not the second would be describing half a program
    and would look complete doing it.
    """
    gen = c.execute(f"""SELECT SUM(l.original) FROM ledger_snapshot l
                        JOIN account a USING (account_id)
                        WHERE l.fy={FY} AND l.period={P_ACCT} AND a.dept='300'
                          AND a.function='3510'""").fetchone()[0] or 0
    rev = c.execute("""SELECT SUM(amount) FROM athletics_history
                       WHERE fy=? AND side='revolving'""", (FY,)).fetchone()[0] or 0
    return gen, rev


def bars(rows, hilite=(), note_of=None):
    """A stage, as rows of label + proportional bar + amount.

    Scaled to the biggest row in the STAGE, not across stages: a stage whose largest item
    is small would otherwise render as a row of slivers, which is the failure this replaced.
    """
    top = max((v for _, v, *_ in rows), default=1) or 1
    out = ['<div class="bars">']
    for label, value, *rest in rows:
        key = rest[0] if rest else None
        cls = ' hi' if key in hilite else ''
        pct = max(0.6, value / top * 100)
        sub = (note_of or {}).get(key, '')
        out.append(
            f'<div class="row{cls}">'
            f'<div class="lab">{html.escape(str(label))}'
            + (f'<span class="sub">{html.escape(sub)}</span>' if sub else '')
            + f'</div>'
            f'<div class="track"><div class="fill" style="width:{pct:.2f}%"></div></div>'
            f'<div class="amt">{money(value)}</div>'
            f'</div>')
    out.append('</div>')
    return '\n'.join(out)


def programme_rows(c, fundnames):
    """Each programme: what is inside the appropriation, and what is outside it."""
    inside = {r['f']: r['v'] for r in c.execute(f"""
        SELECT a.function f, SUM(l.original) v FROM ledger_snapshot l
        JOIN account a USING (account_id)
        WHERE l.fy={FY} AND l.period={P_ACCT} AND a.dept='300' AND a.function IS NOT NULL
        GROUP BY a.function""")}
    d300 = sum(inside.values())
    fundrow = {r['fund']: r for r in c.execute(f"""
        SELECT fund, revenue, spent, closing_balance FROM v_fund_year
        WHERE fy={FY} AND period={P_DEPT}""")}
    spent = {f: (r['spent'] or 0) for f, r in fundrow.items()}
    held = {f: (r['closing_balance'] or 0) for f, r in fundrow.items()}
    claimed, out = set(), []
    for name, fns, funds, why in PROGRAMMES:
        if fns is None:
            continue
        ins = sum(inside.get(f, 0) for f in fns)
        claimed.update(fns)
        outs = [(f, spent.get(f, 0), how, fundnames.get(f, '')) for f, how in funds]
        out.append(dict(name=name, inside=ins, fns=fns, outs=outs, why=why))
    rest = d300 - sum(p['inside'] for p in out)
    out.append(dict(name='Everything else in the school budget', inside=rest, fns=[],
                    outs=[], why='Teaching, buildings, administration, guidance, health, '
                                 'technology — the {} function codes not claimed above.'
                                 .format(len(inside) - len(claimed))))
    return out, d300


# The vertical layout, as explicit rows. Each row may hold a left box, a right box, or
# both, and a row with a gap on one side is deliberate.
#
# WHY THE ORDER IS HAND-SET RATHER THAN COMPUTED
#
# Because the readability of this diagram is almost entirely about CROSSINGS, and the fix
# is to put a source beside the thing it pays for: the school lunch fund across from food
# service, the athletics fund across from athletics. Sorting either column by size — the
# obvious automatic rule — guarantees the opposite. A gap opposite a box costs nothing and
# buys a horizontal line instead of a diagonal one.
#
# `general-other` is the general fund drawn a SECOND time, lower down, feeding the school
# costs appropriated to other departments. Same source, two boxes, because one box at the
# top with four long sweeping edges is unreadable and says nothing extra.
LAYOUT = [
    ('appropriation', 'core'),
    (None, '0100-13102-532000'),
    (None, '0100-19142-570018'),
    (None, '0100-18202-560001'),
    (None, '0100-12101-519021'),
    (None, None),
    ('2640', 'Special education'),
    ('grants', None),
    ('BUSFEES', 'Transportation'),
    ('1301', 'Athletics'),
    ('2200', 'Food service'),
    ('1312', 'Extended day and after school'),
    ('1305', None),
    ('1306', None),
    ('1308', 'Other own-fund activity'),
    ('1311', None),
    ('1300', None),
    ('1302', None),
]

# Which left box feeds which right box, beyond what the programme map already says.
EXTRA_EDGES = [
    ('1308', 'Other own-fund activity', 'restricted'),
    ('1311', 'Other own-fund activity', 'restricted'),
    ('1300', 'Other own-fund activity', 'restricted'),
    ('1302', 'Other own-fund activity', 'restricted'),
    ('appropriation', '0100-13102-532000', 'traced'),
    ('appropriation', '0100-19142-570018', 'traced'),
    ('appropriation', '0100-18202-560001', 'unknown'),
    ('appropriation', '0100-12101-519021', 'traced'),
]


def diagram(progs, funds, d300, grant_spend, elsewhere):
    """The flow, laid out so a source sits beside the thing it pays for.

    The line style is the finding, not decoration:

      solid       traced — an account or journal shows this money going here
      dashed      restricted — the fund exists for this and nothing else, and no expense
                  report for the special revenue funds exists, so it is NOT observed
      dotted      collected and cannot be located anywhere at all

    Box heights are uniform and the amount is printed in each. **The geometry carries the
    connection and never the magnitude** — a diagram implying a scale it does not have
    would be worse than the list it replaced.
    """
    LH, GAP, BW = 46, 12, 254
    LX, RX, W = 20, 610, 890

    fundmeta = {f: (nm, rev) for f, nm, rev, sp in funds}
    # ONE box for the general fund. It was briefly drawn twice, lower down, to shorten
    # the edges to the school costs in other departments — TJ, correctly: "dont SPLIT one
    # source like that." A source drawn twice tells a reader there are two sources.
    # The fix is to reorder the RIGHT column so everything the general fund feeds sits
    # together at the top, which shortens the same edges without inventing a box.
    gf_total = d300 + sum(elsewhere[a]['v'] for a, _, _ in ELSEWHERE_MAP
                          if a in elsewhere and not a.endswith('560001'))
    lbox = {
        'appropriation': ('General fund — appropriated', gf_total, 'core'),
        'grants': ('Federal and state grants', grant_spend, 'grant'),
        'BUSFEES': ('Bus fees — charged', None, 'missing'),
    }
    for f, (nm, rev) in fundmeta.items():
        lbox[f] = (f'{f} {nm.title()[:26]}', rev, 'fund')

    rbox = {'core': ('THE SCHOOL BUDGET', d300, 'core'),
            'Other own-fund activity': ('Other own-fund activity',
                                        sum(fundmeta.get(f, ('', 0))[1]
                                            for f in ('1308', '1311', '1300', '1302')),
                                        'prog')}
    edges = [('appropriation', 'core', 'traced')]
    for p in progs:
        if not p['outs']:
            continue
        rbox[p['name']] = (p['name'], p['inside'] + sum(v for _, v, _, _ in p['outs']),
                           'prog')
        for f, v, how, nm in p['outs']:
            src = f if f in lbox else ('BUSFEES' if how == 'missing' else 'grants')
            edges.append((src, p['name'], how))
    for aid, label, why in ELSEWHERE_MAP:
        r = elsewhere.get(aid)
        if r:
            rbox[aid] = (label[:32], r['v'], 'alt')
    edges += EXTRA_EDGES

    ly, ry, row = {}, {}, 0
    for lk, rk in LAYOUT:
        y = 48 + row * (LH + GAP)
        if lk and lk in lbox:
            ly[lk] = y
        if rk and rk in rbox:
            ry[rk] = y
        row += 1
    H = 48 + row * (LH + GAP) + 14

    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="flow" '
         f'role="img" aria-label="Sources of school money and where each lands">',
         '<text class="dhd" x="20" y="26">SOURCES</text>',
         f'<text class="dhd" x="{RX}" y="26">WHERE IT LANDS</text>']
    seen = set()
    for src, dst, how in edges:
        if src not in ly or dst not in ry or (src, dst) in seen:
            continue
        seen.add((src, dst))
        y1, y2 = ly[src] + LH / 2, ry[dst] + LH / 2
        x1, x2, mx = LX + BW, RX, (LX + BW + RX) / 2
        o.append(f'<path class="e {how}" d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}"/>')
    for boxes, ys, x in ((lbox, ly, LX), (rbox, ry, RX)):
        for key, y in ys.items():
            label, val, kind = boxes[key]
            o.append(f'<g class="b {kind}"><rect x="{x}" y="{y}" width="{BW}" '
                     f'height="{LH}" rx="5"/>'
                     f'<text class="bl" x="{x+10}" y="{y+19}">{html.escape(label)}</text>'
                     f'<text class="bv" x="{x+10}" y="{y+35}">'
                     f'{money(val) if val is not None else "not found"}</text></g>')
    o.append('</svg>')
    return '\n'.join(o)


def render(c):
    fundnames = {r[0]: r[1] for r in c.execute('SELECT fund, name FROM fund')}
    srcs, rev_total = revenue_sources(c)
    funds = own_funds(c)
    progs, d300 = programme_rows(c, fundnames)
    ath_gen, ath_rev = athletics(c)

    grant_spend = c.execute(f"""SELECT SUM(spent) v FROM v_fund_year
                                WHERE fy={FY} AND period={P_DEPT} AND spent>0
                                  AND (revenue IS NULL OR revenue=0)""").fetchone()['v'] or 0
    elsewhere = {r['account_id']: r for r in c.execute(f"""
        SELECT a.account_id, a.name, l.original v FROM ledger_snapshot l
        JOIN account a USING (account_id)
        WHERE l.fy={FY} AND l.period={P_ACCT}""")}

    P = []
    a = P.append

    # The three metrics, computed here so the diagram cannot drift from its own headline.
    #
    # NOT the sum of the right column. The programme boxes OVERLAP the school budget box —
    # $5.9M of "Special education" is inside the $26m, all of "Transportation" is — so
    # adding the column down double-counts most of it. What is summed instead is each
    # quantity once: the appropriation, the district's own money, and the town's education
    # spending appropriated elsewhere.
    appr2 = c.execute(f"""SELECT original FROM ledger_snapshot WHERE fy={FY}
                          AND period={P_DEPT} AND account_id='0100-301'""").fetchone()
    appr = d300 + (appr2['original'] if appr2 else 0)
    ownrev = sum(rev for _, _, rev, _ in funds)
    els = {a: elsewhere[a]['v'] for a, _, _ in ELSEWHERE_MAP if a in elsewhere}
    pens = els.get('0100-18202-560001', 0)
    outside_town = sum(v for k, v in els.items() if not k.endswith('560001'))
    resources = appr + ownrev + grant_spend
    outside = ownrev + grant_spend + outside_town

    a('<section class="metrics">'
      f'<div class="m"><div class="mk">Appropriated to the schools</div>'
      f'<div class="mv">{money(appr)}</div>'
      f'<div class="ms">Departments 300 and 301, as Town Meeting voted. '
      f'<b>The number in every headline.</b></div></div>'
      f'<div class="m"><div class="mk">What the school system actually has</div>'
      f'<div class="mv">{money(resources)}</div>'
      f'<div class="ms">…plus its own funds ({money(ownrev)}) and grant spending '
      f'({money(grant_spend)}).</div></div>'
      f'<div class="m hi"><div class="mk">Outside the tax appropriation</div>'
      f'<div class="mv">+{money(outside)}</div>'
      f'<div class="ms"><b>{outside/appr*100:.1f}%</b> more than the school budget — the '
      f'district’s own funds and grants, plus {money(outside_town)} of education the town '
      f'appropriates to other departments.</div></div>'
      '</section>'
      f'<p class="warn"><b>These are not one basis and cannot be added carelessly.</b> The '
      f'appropriation is a budget as voted; the funds and grants are nine months of '
      f'ACTUAL spending, because the town publishes no twelve-month fund report. And the '
      f'school share of the {money(pens)} pension assessment is in none of these figures, '
      f'because nobody publishes it — so every number above is a floor.</p>'
      '<p class="cap">The three are not the right column added up. The programme boxes '
      '<b>overlap</b> the school budget box — $5.9M of special education is inside the '
      '$26m, all of transportation is — so summing the column downwards would count most '
      'of it twice.</p>')

    a('<section class="intro"><p>Two columns. On the left, every source of money the '
      'schools use. On the right, where it comes to rest — starting with the one number '
      'everybody knows, and then <b>every other place school money is spent that the '
      '$26m does not contain</b>.</p>'
      '<p class="cap">Bars are proportional within each column. A source and a landing '
      'place are not the same kind of thing and are never added across the two.</p>'
      '</section>')

    a('<div class="scroll">' + diagram(progs, funds, d300, grant_spend, elsewhere)
      + '</div>')
    a('<div class="key"><span><i class="k traced"></i>traced — an account shows it</span>'
      '<span><i class="k restricted"></i>restricted — the fund exists for this and nothing '
      'else, and is <b>not observed</b></span>'
      '<span><i class="k missing"></i>collected, and cannot be located</span></div>')

    a('<div class="cols">')

    # ------------------------------------------------------------------ column one
    a('<div class="col"><h2>Sources</h2>')
    a('<div class="colnote">Where the money comes from.</div>')
    a('<h3>Appropriated by Town Meeting</h3>')
    a(bars([('General fund — department 300', d300, 'core')]))
    a('<h3>The schools’ own funds — never enter the general fund</h3>')
    a(bars([(nm, rev, f) for f, nm, rev, sp in funds]))
    a('<h3>Grants</h3>')
    a(bars([('Federal and state grants, spent side only', grant_spend, 'g')]))
    a('<div class="miss"><b>Bus fees — charged, and not found.</b> $180 a family, $270 for '
      'two or more, School Committee policy 3601.01. The general-fund account '
      '<code>STUDENTBUS</code> is zero and no transportation fund exists. This is a source '
      'we know is real and cannot place.</div>')
    a('</div>')

    # ------------------------------------------------------------------ column two
    a('<div class="col"><h2>Where it lands</h2>')
    a('<div class="colnote">What the money is spent on.</div>')
    a(f'<div class="core"><div class="corehd">THE SCHOOL BUDGET</div>'
      f'<div class="coreamt">{money(d300)}</div>'
      f'<div class="coresub">Department 300 — 258 accounts. This is the number in every '
      f'headline, and every box below is money spent on the schools that it does not '
      f'contain.</div></div>')

    a('<h3>Programmes paid for from more than one place</h3>')
    for p in progs:
        if not p['outs'] and p['inside'] == 0:
            continue
        tot = p['inside'] + sum(v for _, v, _, _ in p['outs'])
        a(f'<div class="prog"><div class="proghd">{html.escape(p["name"])}'
          f'<span class="progtot">{money(tot)}</span></div>')
        if p['inside']:
            a(f'<div class="line in"><span class="tag">inside the $26m</span>'
              f'<span class="v">{money(p["inside"])}</span>'
              f'<span class="src">function {", ".join(p["fns"])}</span></div>')
        for f, v, how, nm in p['outs']:
            if how == 'missing':
                a('<div class="line missing"><span class="tag">outside — NOT FOUND</span>'
                  '<span class="v">?</span><span class="src">bus fees are charged and '
                  'cannot be located</span></div>')
            else:
                a(f'<div class="line out {how}"><span class="tag">outside — {how}</span>'
                  f'<span class="v">{money(v)}</span>'
                  f'<span class="src">fund {f} {html.escape(nm.title())}</span></div>')
        if p['why']:
            a(f'<div class="progwhy">{p["why"]}</div>')
        a('</div>')

    a('<h3>School money the town appropriates elsewhere</h3>')
    a('<div class="colnote">These never touch department 300.</div>')
    for aid, label, why in ELSEWHERE_MAP:
        r = elsewhere.get(aid)
        if not r:
            continue
        unknown = aid.endswith('560001')
        a(f'<div class="prog alt"><div class="proghd">{html.escape(label)}'
          f'<span class="progtot">{"share unknown" if unknown else money(r["v"])}</span>'
          f'</div><div class="line out"><span class="tag">'
          f'{"of " + money(r["v"]) if unknown else "traced"}</span>'
          f'<span class="v"></span><span class="src"><code>{aid}</code></span></div>'
          f'<div class="progwhy">{why}</div></div>')
    a('</div></div>')

    a('<section class="stage"><h2>How to read the outside column</h2>'
      '<table><tr><th>label</th><th>means</th></tr>'
      '<tr><td><b>traced</b></td><td>an account or a journal shows this money going '
      'here.</td></tr>'
      '<tr><td><b>restricted</b></td><td>the fund exists for this and nothing else, so the '
      'money almost certainly goes here — <b>but no expense report for the special revenue '
      'funds exists, so it is not observed.</b> A presumption, not evidence.</td></tr>'
      '<tr><td><b>NOT FOUND</b></td><td>the money is known to be collected and cannot be '
      'located in any ledger we hold.</td></tr></table>'
      '<p class="warn">Every <b>restricted</b> row on this page becomes <b>traced</b> with '
      'one document: <code>glytdbud-expense</code> run for the special revenue funds — the '
      'same report the town already produces for the general fund and for each of its four '
      'enterprise funds.</p></section>')

    a(f'<section class="stage"><h2>Athletics, in full, as the worked case</h2>'
      f'<p>The town appropriates <b>{money(ath_gen)}</b> for athletics inside dept 300 — '
      f'coaches, transport, the athletic director, the trainer, insurance. The district’s '
      f'own athletics documents record a further <b>{money(ath_rev)}</b> through the '
      f'revolving fund. So the programme costs about <b>{money(ath_gen + ath_rev)}</b> and '
      f'the town’s budget shows {money(ath_gen)} of it.</p>'
      f'<p class="cap">The town ledger and the district’s documents give different figures '
      f'for the fund, on different bases and periods. Neither is wrong; they answer '
      f'different questions. Every fee-funded programme has this shape — athletics is only '
      f'the one where both halves have been found.</p></section>')

    return PAGE.format(body='\n'.join(P))


PAGE = '''<meta charset="utf-8">
<title>How money reaches the schools — Lunenburg FY2026</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --bg:#fbfaf8; --card:#fff; --ink:#191919; --muted:#6b6b6b; --grid:#e2ded7;
  --traced:#1f5c3d; --traced-bg:#dfeee6;
  --school:#9a4f14; --school-bg:#f7e7d8;
  --warn:#8a6d10; --warn-bg:#faf3de;
  --potbg:#2c2b28; --potink:#f2efe9;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#141412; --card:#1c1b19; --ink:#eeebe6; --muted:#a09b93; --grid:#34322e;
    --traced:#79c39f; --traced-bg:#1d3129; --school:#e2a068; --school-bg:#33231a;
    --warn:#d9bd67; --warn-bg:#2c2718; --potbg:#e8e4dc; --potink:#1a1a18; }}
}}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  -webkit-text-size-adjust:100%; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:22px 16px 80px }}
header {{ border-bottom:2px solid var(--ink); padding-bottom:14px; margin-bottom:8px }}
.kicker {{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted) }}
h1 {{ font-size:27px; line-height:1.15; margin:8px 0; letter-spacing:-.02em }}
.standfirst {{ font-size:16px; color:var(--muted); margin:0 }}
.stage {{ background:var(--card); border:1px solid var(--grid); border-radius:10px;
  padding:16px 15px; margin:16px 0 }}
.stage.alt {{ background:transparent }}
h2 {{ font-size:17px; margin:0 0 6px; letter-spacing:-.01em }}
.cap {{ font-size:13.5px; color:var(--muted); margin:0 0 14px }}
.bars {{ display:flex; flex-direction:column; gap:9px }}
.row {{ display:grid; grid-template-columns:1fr 34%; grid-template-areas:"lab amt" "bar bar";
  gap:3px 10px; align-items:baseline }}
.lab {{ grid-area:lab; font-size:13.5px; font-weight:600; min-width:0;
  overflow-wrap:anywhere }}
.lab .sub {{ display:block; font-weight:400; font-size:11.5px; color:var(--muted) }}
.amt {{ grid-area:amt; text-align:right; font-size:13.5px; white-space:nowrap;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace }}
.track {{ grid-area:bar; background:var(--grid); border-radius:3px; height:9px; width:100% }}
.fill {{ background:var(--traced); height:100%; border-radius:3px; min-width:2px }}
.row.hi .fill {{ background:var(--school) }}
.row.hi .lab {{ color:var(--school) }}
.pot {{ background:var(--potbg); color:var(--potink); border-radius:10px;
  padding:18px 16px; margin:16px 0 }}
.pot h2 {{ color:var(--potink) }}
.pot p {{ font-size:14px; margin:8px 0 0 }}
.potline {{ font-family:ui-monospace,Menlo,monospace; font-size:15px; margin:0 }}
.refuse {{ border-top:1px solid rgba(128,128,128,.4); padding-top:10px; margin-top:12px }}
.warnbox {{ border-color:var(--warn); border-width:2px }}
.warnbox td .sub {{ display:block; font-size:11px; color:var(--muted) }}
.warn {{ background:var(--warn-bg); border-left:3px solid var(--warn); border-radius:0 6px 6px 0;
  padding:11px 13px; font-size:13.5px; margin:14px 0 0 }}
.metrics {{ display:grid; gap:10px; margin:16px 0 10px }}
.m {{ border:1px solid var(--grid); border-radius:9px; padding:12px 13px;
  background:var(--card) }}
.m.hi {{ border-color:var(--school); border-width:2px; background:var(--school-bg) }}
.mk {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase; font-weight:700;
  color:var(--muted) }}
.m.hi .mk {{ color:var(--school) }}
.mv {{ font-size:25px; font-weight:700; letter-spacing:-.02em; margin:2px 0 3px;
  font-family:ui-monospace,Menlo,monospace }}
.ms {{ font-size:12.5px; color:var(--muted); line-height:1.45 }}
@media (min-width:760px) {{ .metrics {{ grid-template-columns:repeat(3,1fr) }} }}
.scroll {{ overflow-x:auto; border:1px solid var(--grid); border-radius:10px;
  background:var(--card); padding:10px; margin:14px 0 }}
svg.flow {{ display:block; min-width:900px; height:auto }}
.dhd {{ font-size:11px; font-weight:700; letter-spacing:.11em; fill:var(--muted) }}
.b rect {{ fill:var(--card); stroke:var(--grid); stroke-width:1.5 }}
.b.core rect {{ fill:var(--school-bg); stroke:var(--school); stroke-width:2.5 }}
.b.fund rect {{ fill:var(--traced-bg); stroke:var(--traced) }}
.b.grant rect {{ fill:var(--traced-bg); stroke:var(--traced); stroke-dasharray:5 3 }}
.b.missing rect {{ fill:var(--warn-bg); stroke:var(--warn); stroke-dasharray:3 3 }}
.b.prog rect {{ fill:var(--school-bg); stroke:var(--school) }}
.b.alt rect {{ fill:none; stroke:var(--muted); stroke-dasharray:5 4 }}
.bl {{ font-size:12.5px; font-weight:600; fill:var(--ink) }}
.bs {{ font-size:10px; fill:var(--muted) }}
.bv {{ font-size:12px; fill:var(--muted); font-family:ui-monospace,Menlo,monospace }}
.e {{ fill:none; stroke-width:2 }}
.e.traced {{ stroke:var(--school); opacity:.55 }}
.e.restricted {{ stroke:var(--traced); opacity:.75; stroke-dasharray:7 5 }}
.e.missing {{ stroke:var(--warn); stroke-dasharray:2 5; stroke-width:2.5 }}
.e.unknown {{ stroke:var(--muted); stroke-dasharray:2 4; opacity:.8 }}
.key {{ display:flex; flex-wrap:wrap; gap:8px 18px; font-size:12px; color:var(--muted);
  margin:-4px 0 6px }}
.key span {{ display:flex; align-items:center; gap:6px }}
.k {{ width:22px; height:0; border-top:2px solid; display:inline-block }}
.k.traced {{ border-color:var(--school) }}
.k.restricted {{ border-top-style:dashed; border-color:var(--traced) }}
.k.missing {{ border-top-style:dotted; border-width:3px; border-color:var(--warn) }}
/* Two columns on a wide screen, one on a phone. The columns are a reading aid, not
   the information: every landing box names its own sources, so nothing is lost when
   they stack. Connector lines were tried and are unreadable at this density. */
.cols {{ display:grid; gap:16px; margin:16px 0 }}
.col {{ background:var(--card); border:1px solid var(--grid); border-radius:10px;
  padding:15px 14px; min-width:0 }}
.col h2 {{ margin:0 }}
.colnote {{ font-size:12.5px; color:var(--muted); margin:2px 0 12px }}
.col h3 {{ font-size:12px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--muted); margin:18px 0 8px; font-weight:700 }}
.intro {{ margin:14px 0 }}
.intro p {{ margin:0 0 6px }}
.core {{ background:var(--school-bg); border:2px solid var(--school); border-radius:8px;
  padding:13px 14px }}
.corehd {{ font-size:11px; letter-spacing:.1em; font-weight:700; color:var(--school) }}
.coreamt {{ font-size:26px; font-weight:700; letter-spacing:-.02em;
  font-family:ui-monospace,Menlo,monospace }}
.coresub {{ font-size:12.5px; color:var(--muted); margin-top:4px }}
.prog {{ border:1px solid var(--grid); border-radius:8px; padding:11px 12px; margin:9px 0 }}
.prog.alt {{ border-style:dashed }}
.proghd {{ display:flex; justify-content:space-between; gap:10px; align-items:baseline;
  font-weight:700; font-size:14.5px }}
.progtot {{ font-family:ui-monospace,Menlo,monospace; font-size:13px; white-space:nowrap;
  color:var(--muted); font-weight:400 }}
.line {{ display:grid; grid-template-columns:auto auto 1fr; gap:8px; align-items:baseline;
  font-size:12.5px; margin-top:7px; padding-top:6px; border-top:1px dotted var(--grid) }}
.tag {{ font-size:10px; letter-spacing:.05em; text-transform:uppercase; font-weight:700;
  padding:1px 6px; border-radius:3px; white-space:nowrap }}
.line.in .tag {{ background:var(--school-bg); color:var(--school) }}
.line.out .tag {{ background:var(--traced-bg); color:var(--traced) }}
.line.restricted .tag {{ background:var(--warn-bg); color:var(--warn) }}
.line.missing .tag {{ background:var(--warn-bg); color:var(--warn);
  outline:1px dashed var(--warn) }}
.line .v {{ font-family:ui-monospace,Menlo,monospace; font-weight:600; white-space:nowrap }}
.line .src {{ color:var(--muted) }}
.progwhy {{ font-size:12.5px; color:var(--muted); margin-top:8px }}
.miss {{ background:var(--warn-bg); border-left:3px solid var(--warn); padding:10px 12px;
  border-radius:0 6px 6px 0; font-size:13px; margin-top:12px }}
table {{ border-collapse:collapse; width:100%; margin-top:4px }}
td {{ padding:9px 0; border-bottom:1px solid var(--grid); font-size:14px; vertical-align:top }}
td .sub {{ display:block; font-size:11.5px; color:var(--muted) }}
td.v {{ text-align:right; white-space:nowrap; font-weight:600;
  font-family:ui-monospace,Menlo,monospace }}
code {{ font-family:ui-monospace,Menlo,monospace; font-size:12.5px }}
.gen {{ margin-top:30px; font-size:12px; color:var(--muted) }}
@media (min-width:900px) {{
  .cols {{ grid-template-columns:minmax(0,0.85fr) minmax(0,1.15fr); align-items:start }}
}}
@media (min-width:680px) {{
  .row {{ grid-template-columns:38% 1fr 22%; grid-template-areas:"lab bar amt"; gap:12px;
    align-items:center }}
  .track {{ height:11px }}
}}
</style>

<div class="wrap">
<header>
  <div class="kicker">Lunenburg Budget Project &middot; Data architecture</div>
  <h1>How money reaches the schools</h1>
  <p class="standfirst">FY2026, from every source the town budgets to the 258 accounts the
  school department spends from &mdash; and the one connection in the middle that cannot be
  drawn, because no record ties a source to a department.</p>
</header>

{body}

<p class="gen">Generated by <code>scripts/build_money_flow.py</code> from
<code>sources/data/lunenburg.db</code>. Every figure is computed; <code>--check</code>
fails if this file stops reproducing. Companion to <code>money-in.html</code>, kept
unchanged beside it.</p>
</div>
'''


# The layout for v2. Same idea — a source beside the thing it pays for — but the right
# column now holds each dollar ONCE, so it can be added down.
LAYOUT2 = [
    ('appropriation', 'core'),
    (None, 'MONTY'),
    (None, 'RETHLTH'),
    (None, 'PENSION'),
    (None, 'STIPEND'),
    (None, None),
    ('2640', 'sp-2640'),
    ('grants', 'sp-grants'),
    ('BUSFEES', 'sp-bus'),
    ('1301', 'sp-1301'),
    ('2200', 'sp-2200'),
    ('1312', 'sp-1312'),
    ('1305', 'sp-1305'),
    ('1306', 'sp-1306'),
    ('1308', 'sp-other'),
    ('1311', None),
    ('1300', None),
    ('1302', None),
]


def render_v2(c):
    """The same money, drawn so that every dollar appears exactly once.

    WHY THIS EXISTS BESIDE THE FIRST VERSION

    In `money-flow.html` the right column mixes two kinds of thing: a CONTAINER (the school
    budget) and PROGRAMMES that are partly inside it. `Special education $6,329,681` sits
    under `THE SCHOOL BUDGET $26,247,474` and $5.9M of it is already counted there. A column
    of numbers invites being added, and that one cannot be. TJ: *"it cannot be
    'incorrect'."*

    So here the right column is **where money is spent, each dollar once**: the
    appropriation, the education the town appropriates to other departments, and each
    fund's own spending. It adds.

    WHAT IS LOST, AND WHERE IT WENT

    The programme totals — the finding that athletics really costs $618,801 against a
    budget line of $518,334 — are the best thing on the first version. They move to a table
    below the diagram, under their own heading, marked as a different lens. They are not
    deleted; they are moved out of a column somebody would sum.

    WHAT A FUND BOX ON THE RIGHT CAN AND CANNOT SAY

    Only that the fund spent the money. **Not what it bought.** No expense report exists for
    the special revenue funds, and even fund 1301 — the one fund with a transaction journal
    — records no vendor on any of its 46 FY26 payments. So every fund box says *purpose
    presumed*, and the presumption is the statute or the grant award, never an observation.

    NO OFFSET EDGES YET. The district documents three (Extended Day $71,247, Facilities
    $25,000, Athletic $20,000) and publishes none for lunch, choice, the circuit breaker or
    the grants. Drawing an edge only where an amount happens to be published would imply
    the others have no offset, which is a stronger claim than we can make. The mechanism is
    described in text below instead.
    """
    fundnames = {r[0]: r[1] for r in c.execute('SELECT fund, name FROM fund')}
    funds = own_funds(c)
    progs, d300 = programme_rows(c, fundnames)
    ath_gen, ath_rev = athletics(c)
    grant_spend = c.execute(f"""SELECT SUM(spent) v FROM v_fund_year
                                WHERE fy={FY} AND period={P_DEPT} AND spent>0
                                  AND (revenue IS NULL OR revenue=0)""").fetchone()['v'] or 0
    fundrow = {r['fund']: r for r in c.execute(f"""
        SELECT fund, revenue, spent, closing_balance FROM v_fund_year
        WHERE fy={FY} AND period={P_DEPT}""")}
    spent = {f: (r['spent'] or 0) for f, r in fundrow.items()}
    held = {f: (r['closing_balance'] or 0) for f, r in fundrow.items()}
    els = {a: c.execute(f"""SELECT original v FROM ledger_snapshot WHERE fy={FY}
              AND period={P_ACCT} AND account_id=?""", (a,)).fetchone() for a, _, _ in ELSEWHERE_MAP}
    els = {a: (r['v'] if r else 0) for a, r in els.items()}

    SCH = ("(fund LIKE '13%' OR fund LIKE '15%' OR fund LIKE '22%' OR fund LIKE '26%'"
           " OR fund LIKE '27%' OR fund LIKE '28%' OR fund LIKE '29%')")
    agg = c.execute(f"""SELECT SUM(revenue) i, SUM(spent) o, SUM(closing_balance) h
                        FROM v_fund_year WHERE fy={FY} AND period={P_DEPT} AND {SCH}""").fetchone()
    f_in, f_out, f_held = agg['i'] or 0, agg['o'] or 0, agg['h'] or 0
    f_open = f_held - f_in + f_out

    LH, GAP, BW = 58, 11, 254
    LX, RX, W = 20, 610, 890
    fundrev = {f: rev for f, nm, rev, sp in funds}
    lbox = {'appropriation': ('General fund — appropriated',
                              d300 + sum(v for k, v in els.items()
                                         if not k.endswith('560001')), 'core',
                              'excludes the pension share, which is unknown'),
            'grants': ('Federal and state grants', grant_spend, 'grant',
                       'spent side only — no FY26 revenue booked'),
            'BUSFEES': ('Bus fees — charged', None, 'missing',
                        '$180 / $270, policy 3601.01')}
    for f, nm, rev, sp in funds:
        lbox[f] = (f'{f} {nm.title()[:26]}', rev, 'fund', 'received, nine months')

    OTHER = ('1308', '1311', '1300', '1302')
    # A fund box carries what is SITTING there as well as what moved. A fund that took in
    # $325,970 and spent $4,005 is not a small programme — it is a reserve accumulating,
    # and the "spent" figure alone actively hides that. The mirror case is school lunch,
    # which spends $167,355 MORE than it receives and is drawing a balance down.
    def fb(key, label):
        r = fundrow.get(key)
        if not r:
            return (label, 0, 'prog', '')
        inn, sp, hl = r['revenue'] or 0, r['spent'] or 0, r['closing_balance'] or 0
        net = inn - sp
        mark = '↑' if net > 0 else ('↓' if net < 0 else '')
        return (label, sp, 'prog', f'in {money(inn)} · held {money(hl)} {mark}')

    rbox = {
        'core': ('THE SCHOOL BUDGET', d300, 'core', 'department 300, as voted'),
        'MONTY': ('Monty Tech assessment', els['0100-13102-532000'], 'alt',
                  'a different district'),
        'RETHLTH': ('School retiree health', els['0100-19142-570018'], 'alt',
                    'former school employees'),
        'PENSION': ('Pension — share unknown', els['0100-18202-560001'], 'alt',
                    'town AND school staff together'),
        'STIPEND': ('School resource stipend', els['0100-12101-519021'], 'alt',
                    'inside the police department'),
        'sp-2640': fb('2640', 'Circuit breaker fund'),
        'sp-grants': ('Grant funds spent', grant_spend, 'prog',
                      'balances are NEGATIVE — spent ahead of reimbursement'),
        'sp-bus': ('Bus fee spending', None, 'missing', 'no account found'),
        'sp-1301': fb('1301', 'Athletics fund'),
        'sp-2200': fb('2200', 'School lunch fund'),
        'sp-1312': fb('1312', 'Extended day fund'),
        'sp-1305': fb('1305', 'After school fund'),
        'sp-1306': fb('1306', 'Facilities use fund'),
        'sp-other': ('Other own funds spent', sum(spent.get(f, 0) for f in OTHER), 'prog',
                     'held ' + money(sum(held.get(f, 0) for f in OTHER))),
    }
    edges = [('appropriation', k, 'unknown' if k == 'PENSION' else 'traced')
             for k in ('core', 'MONTY', 'RETHLTH', 'PENSION', 'STIPEND')]
    edges += [('2640', 'sp-2640', 'restricted'), ('grants', 'sp-grants', 'restricted'),
              ('BUSFEES', 'sp-bus', 'missing'), ('1301', 'sp-1301', 'restricted'),
              ('2200', 'sp-2200', 'restricted'), ('1312', 'sp-1312', 'restricted'),
              ('1305', 'sp-1305', 'restricted'), ('1306', 'sp-1306', 'restricted')]
    edges += [(f, 'sp-other', 'restricted') for f in OTHER]

    ly, ry, row = {}, {}, 0
    for lk, rk in LAYOUT2:
        y = 48 + row * (LH + GAP)
        if lk and lk in lbox:
            ly[lk] = y
        if rk and rk in rbox:
            ry[rk] = y
        row += 1
    H = 48 + row * (LH + GAP) + 14

    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="flow" '
         f'role="img" aria-label="Where each dollar of school money is spent, counted once">',
         '<text class="dhd" x="20" y="26">MONEY IN — this year</text>',
         f'<text class="dhd" x="{RX}" y="26">MONEY OUT — this year, each dollar once</text>']
    for src, dst, how in edges:
        if src not in ly or dst not in ry:
            continue
        y1, y2 = ly[src] + LH / 2, ry[dst] + LH / 2
        x1, x2, mx = LX + BW, RX, (LX + BW + RX) / 2
        o.append(f'<path class="e {how}" d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}"/>')
    for boxes, ys, x in ((lbox, ly, LX), (rbox, ry, RX)):
        for key, y in ys.items():
            label, val, kind, *rest = boxes[key]
            sub = rest[0] if rest else ''
            o.append(f'<g class="b {kind}"><rect x="{x}" y="{y}" width="{BW}" '
                     f'height="{LH}" rx="5"/>'
                     f'<text class="bl" x="{x+10}" y="{y+18}">{html.escape(label)}</text>'
                     f'<text class="bv" x="{x+10}" y="{y+34}">'
                     f'{money(val) if val is not None else "not found"}</text>'
                     + (f'<text class="bs" x="{x+10}" y="{y+49}">{html.escape(sub)}</text>'
                        if sub else '') + '</g>')
    o.append('</svg>')

    right_total = sum(v for _, v, *_ in rbox.values() if v is not None)
    P = [f'<section class="metrics">'
         f'<div class="m"><div class="mk">Appropriated to the schools</div>'
         f'<div class="mv">{money(d300)}</div><div class="ms">Department 300. '
         f'<b>The number in every headline.</b></div></div>'
         f'<div class="m"><div class="mk">Every box on the right, added</div>'
         f'<div class="mv">{money(right_total)}</div>'
         f'<div class="ms"><b>This column adds.</b> Each dollar appears exactly once, '
         f'which is the whole change from version one.</div></div>'
         f'<div class="m hi"><div class="mk">Not in the school budget</div>'
         f'<div class="mv">+{money(right_total - d300)}</div>'
         f'<div class="ms">Education the town appropriates elsewhere, plus everything the '
         f'district spends from its own funds and grants.</div></div></section>',
         f'<p class="warn"><b>Mixed bases, and it cannot be helped.</b> The appropriation '
         f'is a budget as voted; fund and grant figures are nine months of ACTUAL spending, '
         f'because the town publishes no twelve-month fund report. The pension is included '
         f'at its full {money(els["0100-18202-560001"])} even though only some of it is '
         f'schools — <b>so the right-hand total is an over-count by an unknown amount, and '
         f'every other figure here is a floor.</b></p>',
         f'<div class="scroll">{chr(10).join(o)}</div>',
         '<div class="key"><span><i class="k traced"></i>traced</span>'
         '<span><i class="k restricted"></i>the fund spent it — <b>purpose presumed, never '
         'observed</b></span>'
         '<span><i class="k missing"></i>collected, cannot be located</span></div>',
         f'<section class="stage warnbox"><h2>The two columns do not balance, and that is '
         f'the point</h2>'
         f'<p><b>Revenue is not spending.</b> A fund is a tank, not a pipe: it can spend '
         f'less than it receives and accumulate, or more than it receives and draw a '
         f'balance down. Reading across a row tells you what a fund took in and what it '
         f'paid out — <b>it does not tell you those are the same money.</b></p>'
         f'<p>Across all the schools’ own funds in FY2026 to 31 March:</p>'
         f'<table><tr><td>money in</td><td class="v">{money(f_in)}</td></tr>'
         f'<tr><td>money out</td><td class="v">{money(f_out)}</td></tr>'
         f'<tr><td><b>net</b></td><td class="v"><b>{f_in - f_out:+,.0f}</b></td></tr>'
         f'<tr><td>opening balance <span class="sub">derived from the fund identity; '
         f'the town’s report does not print it</span></td>'
         f'<td class="v">{money(f_open)}</td></tr>'
         f'<tr><td>held at 31 March</td><td class="v">{money(f_held)}</td></tr></table>'
         f'<p><b>The funds collectively spent {money(f_out - f_in)} more than they took '
         f'in.</b> That money is real and it came from balances built in earlier years. A '
         f'diagram that balanced would be hiding it.</p>'
         f'<p class="cap">School lunch is the clearest single case — '
         f'in $572,231, out $739,586, holding $287,771. The programme is solvent this year '
         f'and has a smaller cushion next year, and neither the appropriation nor the '
         f'“spent” figure shows that.</p></section>',
         '<section class="stage"><h2>What a fund box on the right does NOT say</h2>'
         '<p>Only that the fund spent the money. <b>Not what it bought.</b> There is no '
         'expense report for the special revenue funds, and fund 1301 — the one fund with a '
         'transaction journal — records <b>no vendor on any of its 46 FY26 payments</b>. '
         'So “Athletics fund spent” means money left that fund. That it went to athletics '
         'is the statute talking, not the ledger.</p>'
         '<p class="cap">No offset edges are drawn. The district publishes three amounts '
         '(Extended Day $71,247, Facilities $25,000, Athletic $20,000) and none for lunch, '
         'school choice, the circuit breaker or the grants. Drawing an edge only where an '
         'amount happens to be published would imply the others have no offset, which is a '
         'stronger claim than we can make.</p></section>']

    P.append('<section class="stage"><h2>The programme view — a different lens</h2>'
             '<p class="cap">What each programme costs across both sides. <b>These figures '
             'overlap the diagram above and must never be added to it</b> — most of each '
             'row is already inside the school budget box.</p>'
             '<table><tr><th>programme</th><th class="v">in the budget</th>'
             '<th class="v">from funds</th><th class="v">total</th></tr>')
    for p in progs:
        if not p['outs']:
            continue
        out = sum(v for _, v, _, _ in p['outs'])
        P.append(f'<tr><td>{html.escape(p["name"])}</td>'
                 f'<td class="v">{money(p["inside"]) if p["inside"] else "—"}</td>'
                 f'<td class="v">{money(out) if out else "not found"}</td>'
                 f'<td class="v"><b>{money(p["inside"] + out)}</b></td></tr>')
    P.append('</table>'
             f'<p class="warn"><b>Athletics is the case to read.</b> The town appropriates '
             f'{money(ath_gen)} and the district’s own athletics documents record a further '
             f'{money(ath_rev)} through the revolving fund. And the district’s FY26 budget '
             f'overview says why the line moves: it was cut <i>“with anticipation that '
             f'athletic revolving may be enough to offset this reduction in the budget '
             f'line”</i> — and the next year, <i>“athletic revolving can not support these '
             f'increased costs”</i>, at a 254% line increase.</p></section>')
    return PAGE.format(body='\n'.join(P))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    c = db()
    fresh = render(c)
    rel = os.path.relpath(OUT, ROOT)
    if args.check:
        if not os.path.exists(OUT):
            raise SystemExit(f'{rel} does not exist. Run without --check.')
        if not os.path.exists(OUT2) or open(OUT2, encoding='utf-8').read() != render_v2(c):
            raise SystemExit(f'STALE: money-flow-v2.html no longer reproduces.\n'
                             f'  Run: python3 scripts/build_money_flow.py')
        if open(OUT, encoding='utf-8').read() != fresh:
            raise SystemExit(f'STALE: {rel} no longer reproduces.\n'
                             f'  Run: python3 scripts/build_money_flow.py')
        print(f'ok: {rel} still reproduces')
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print(f'wrote {rel} ({len(fresh):,} bytes)')
    v2 = render_v2(c)
    with open(OUT2, 'w', encoding='utf-8') as fh:
        fh.write(v2)
    print(f'wrote {os.path.relpath(OUT2, ROOT)} ({len(v2):,} bytes)')


if __name__ == '__main__':
    main()
