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

WHAT THE SHAPES MEAN, AND WHY THE POT IS DRAWN THE WAY IT IS

Three kinds of edge, and the distinction is the finding:

  SOLID     traced. A named account in the town's ledger holds this figure.
  HATCHED   a real quantity whose SPLIT is unknown — the pension assessment covers town
            and school staff and no published document says in what proportion.
  (absent)  the edge that cannot be drawn at all: source to department.

That last one is the point of the pot. Every revenue line flows into fund `0100` and
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
    """The school's own funds — money that never enters the general fund at all."""
    rows = c.execute(f"""
        SELECT fund, name, revenue, spent, closing_balance FROM v_fund_year
        WHERE fy={FY} AND period={P_DEPT} AND revenue > 0
          AND (upper(name) LIKE '%SCHOOL%' OR upper(name) LIKE '%EXTENDED DAY%'
               OR upper(name) LIKE '%CIRCUIT%')
        ORDER BY revenue DESC""").fetchall()
    return [(r['fund'], r['name'], r['revenue'], r['spent']) for r in rows]


# ---------------------------------------------------------------- drawing

def money(v):
    return f'${v:,.0f}'


def build(c):
    srcs, rev_total = revenue_sources(c)
    depts, omnibus = departments(c)
    elsewhere = school_elsewhere(c)
    uses, uses_total = school_uses(c)
    funds = own_funds(c)

    # One scale for every column, so a block twice as tall is twice the money everywhere.
    span = H - TOP - BOT
    scale = span / rev_total

    def lay(pairs, x, y0=TOP):
        boxes, y = [], y0
        for label, value, *extra in pairs:
            h = max(3.0, value * scale)
            boxes.append(dict(label=label, value=value, x=x, y=y, h=h,
                              extra=extra[0] if extra else None))
            y += h + GAP
        return boxes

    src_boxes = lay([(n, v) for n, v in srcs], COL['src'])
    pot_h = rev_total * scale
    dept_boxes = lay([(n, v, d) for n, v, d in depts], COL['dept'])
    # The pot appropriates less than it receives; the rest funds articles and reserves.
    residual = rev_total - omnibus
    dept_boxes.append(dict(label='Warrant articles, transfers, reserves',
                           value=residual, x=COL['dept'],
                           y=dept_boxes[-1]['y'] + dept_boxes[-1]['h'] + GAP,
                           h=max(3.0, residual * scale), extra='residual'))
    use_boxes = lay([((f'{f} — {nm}' if f and nm else (nm or f or 'unclassified')), v, n)
                     for f, nm, v, n in uses], COL['use'])

    p = []
    a = p.append

    def rect(b, cls, sub=''):
        a(f'<g class="box {cls}">')
        a(f'<rect x="{b["x"]}" y="{b["y"]:.1f}" width="{BOXW}" height="{b["h"]:.1f}"/>')
        a(f'<text class="lbl" x="{b["x"]+8}" y="{b["y"]+14:.1f}">'
          f'{html.escape(str(b["label"])[:34])}</text>')
        a(f'<text class="amt" x="{b["x"]+8}" y="{b["y"]+29:.1f}">{money(b["value"])}</text>')
        if sub:
            a(f'<text class="sub" x="{b["x"]+8}" y="{b["y"]+42:.1f}">{html.escape(sub)}</text>')
        a('</g>')

    def ribbon(x1, y1, h1, x2, y2, h2, cls):
        """A flow. Cubic beziers so two ribbons crossing stay readable."""
        mx = (x1 + x2) / 2
        a(f'<path class="rib {cls}" d="M{x1},{y1:.1f} C{mx},{y1:.1f} {mx},{y2:.1f} '
          f'{x2},{y2:.1f} L{x2},{y2+h2:.1f} C{mx},{y2+h2:.1f} {mx},{y1+h1:.1f} '
          f'{x1},{y1+h1:.1f} Z"/>')

    a(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
      f'role="img" aria-label="How money reaches the Lunenburg schools, FY2026">')
    a('''<defs>
      <pattern id="hatch" width="7" height="7" patternTransform="rotate(45)"
               patternUnits="userSpaceOnUse">
        <rect width="7" height="7" fill="var(--unknown-bg)"/>
        <line x1="0" y1="0" x2="0" y2="7" stroke="var(--unknown)" stroke-width="3"/>
      </pattern>
    </defs>''')

    for x, t in ((COL['src'], 'EVERY SOURCE'), (COL['pot'], 'ONE POT'),
                 (COL['dept'], 'APPROPRIATED BY VOTE'), (COL['use'], 'WHAT IT PAYS FOR')):
        a(f'<text class="hd" x="{x}" y="{TOP-58}">{t}</text>')
    a(f'<text class="hdsub" x="{COL["src"]}" y="{TOP-38}">traced — each is a named '
      f'revenue account</text>')
    a(f'<text class="hdsub" x="{COL["pot"]}" y="{TOP-38}">where provenance ends</text>')
    a(f'<text class="hdsub" x="{COL["dept"]}" y="{TOP-38}">traced — Town Meeting voted '
      f'each one</text>')
    a(f'<text class="hdsub" x="{COL["use"]}" y="{TOP-38}">traced — 258 named accounts</text>')

    # sources -> pot
    for b in src_boxes:
        ribbon(b['x'] + BOXW, b['y'], b['h'], COL['pot'],
               TOP + (b['y'] - TOP) * (pot_h / (span)), b['h'], 'in')
    # pot -> departments
    for b in dept_boxes:
        cls = 'out school' if b.get('extra') in ('300', '310') else 'out'
        if b.get('extra') == 'residual':
            cls = 'out residual'
        ribbon(COL['pot'] + BOXW, TOP + (b['y'] - TOP) * (pot_h / span), b['h'],
               b['x'], b['y'], b['h'], cls)
    # dept 300 -> its functions
    d300 = next(b for b in dept_boxes if b.get('extra') == '300')
    yy = d300['y']
    for b in use_boxes:
        share = b['h'] / max(1, sum(u['h'] for u in use_boxes)) * d300['h']
        ribbon(d300['x'] + BOXW, yy, share, b['x'], b['y'], b['h'], 'use')
        yy += share

    a(f'<g class="box pot"><rect x="{COL["pot"]}" y="{TOP}" width="{BOXW}" '
      f'height="{pot_h:.1f}"/>')
    a(f'<text class="lbl" x="{COL["pot"]+8}" y="{TOP+18}">GENERAL FUND 0100</text>')
    a(f'<text class="amt" x="{COL["pot"]+8}" y="{TOP+34}">{money(rev_total)}</text>')
    for i, line in enumerate(['Every source above flows in',
                              'here and loses its identity.',
                              'No record ties a source to a',
                              'department, so the diagonal',
                              'edge — Chapter 70 to the',
                              'schools — cannot be drawn.',
                              'It is not missing. It does',
                              'not exist.']):
        a(f'<text class="potnote" x="{COL["pot"]+8}" y="{TOP+58+i*15}">{line}</text>')
    a('</g>')

    for b in src_boxes:
        rect(b, 'src')
    for b in dept_boxes:
        d = b.get('extra')
        cls = 'dept school' if d in ('300', '310') else (
            'dept residual' if d == 'residual' else 'dept')
        rect(b, cls, f'dept {d}' if d and d not in ('other', 'residual') else '')
    for b in use_boxes:
        rect(b, 'use', f'{b["extra"]} accounts' if b.get('extra') else '')

    a('</svg>')
    return '\n'.join(p), dict(srcs=srcs, rev_total=rev_total, depts=depts,
                              omnibus=omnibus, elsewhere=elsewhere, uses=uses,
                              funds=funds, residual=residual)


PAGE = '''<meta charset="utf-8">
<title>How money reaches the schools — Lunenburg FY2026</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --bg:#fbfaf8; --ink:#1a1a1a; --muted:#6b6b6b; --grid:#e0dcd5;
  --traced:#1f5c3d; --traced-bg:#e7f0ea;
  --school:#8a4b17; --school-bg:#f6ece2;
  --pot:#3a3a3a; --pot-bg:#ecebe8;
  --unknown:#9a7b1f; --unknown-bg:#f7f1dd;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#151513; --ink:#eceae6; --muted:#9c9890; --grid:#33322e;
    --traced:#7fc2a0; --traced-bg:#1b2b22; --school:#e0a06a; --school-bg:#2e2119;
    --pot:#b9b6b0; --pot-bg:#222220; --unknown:#d8bd6a; --unknown-bg:#2b2617; }}
}}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
.wrap {{ max-width:1560px; margin:0 auto; padding:28px 22px 70px }}
header {{ border-bottom:2px solid var(--ink); padding-bottom:14px; margin-bottom:22px }}
.kicker {{ font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted) }}
h1 {{ font-size:30px; margin:6px 0 8px; letter-spacing:-.02em }}
.standfirst {{ font-size:17px; color:var(--muted); max-width:60em; margin:0 }}
h2 {{ font-size:19px; margin:34px 0 8px }}
p {{ max-width:62em }}
.key {{ display:flex; gap:26px; flex-wrap:wrap; margin:18px 0 6px; font-size:13px }}
.key div {{ display:flex; gap:8px; align-items:center }}
.sw {{ width:26px; height:13px; border:1.5px solid }}
.sw.t {{ background:var(--traced-bg); border-color:var(--traced) }}
.sw.s {{ background:var(--school-bg); border-color:var(--school) }}
.sw.u {{ background:var(--unknown-bg); border-color:var(--unknown) }}
.sw.p {{ background:var(--pot-bg); border-color:var(--pot) }}
.scroll {{ overflow-x:auto; border:1px solid var(--grid); border-radius:6px;
  background:var(--bg); margin-top:10px }}
svg {{ display:block; min-width:1500px }}
.hd {{ font-size:12px; font-weight:700; letter-spacing:.1em; fill:var(--ink) }}
.hdsub {{ font-size:11px; fill:var(--muted) }}
.box rect {{ stroke-width:1.5 }}
.box.src rect {{ fill:var(--traced-bg); stroke:var(--traced) }}
.box.pot rect {{ fill:var(--pot-bg); stroke:var(--pot); stroke-width:2 }}
.box.dept rect {{ fill:var(--traced-bg); stroke:var(--traced) }}
.box.dept.school rect {{ fill:var(--school-bg); stroke:var(--school); stroke-width:2 }}
.box.dept.residual rect {{ fill:none; stroke:var(--muted); stroke-dasharray:4 3 }}
.box.use rect {{ fill:var(--school-bg); stroke:var(--school) }}
.lbl {{ font-size:11.5px; font-weight:600; fill:var(--ink) }}
.amt {{ font-size:12px; fill:var(--ink);
  font-family:ui-monospace,Menlo,monospace }}
.sub {{ font-size:10px; fill:var(--muted) }}
.potnote {{ font-size:10.5px; fill:var(--muted) }}
.rib {{ stroke:none }}
.rib.in {{ fill:var(--traced); opacity:.13 }}
.rib.out {{ fill:var(--traced); opacity:.13 }}
.rib.out.school {{ fill:var(--school); opacity:.22 }}
.rib.out.residual {{ fill:var(--muted); opacity:.08 }}
.rib.use {{ fill:var(--school); opacity:.16 }}
table {{ border-collapse:collapse; width:100%; max-width:62em; margin:10px 0 6px;
  font-size:14px }}
th,td {{ text-align:left; padding:5px 10px 5px 0; border-bottom:1px solid var(--grid);
  vertical-align:top }}
td.v {{ text-align:right; font-family:ui-monospace,Menlo,monospace; white-space:nowrap }}
code {{ font-family:ui-monospace,Menlo,monospace; font-size:12.5px; color:var(--muted) }}
.note {{ border-left:3px solid var(--unknown); background:var(--unknown-bg);
  padding:12px 14px; margin:16px 0; max-width:62em; font-size:14px }}
.gen {{ margin-top:44px; padding-top:14px; border-top:1px solid var(--grid);
  font-size:12px; color:var(--muted) }}
</style>

<div class="wrap">
<header>
  <div class="kicker">Lunenburg Budget Project · Data architecture</div>
  <h1>How money reaches the schools</h1>
  <p class="standfirst">FY2026, from every source the town budgets to the 258 accounts the
  school department spends from — and the one edge in the middle that cannot be drawn
  because no record ties a source to a department.</p>
</header>

<div class="key">
  <div><span class="sw t"></span> traced — a named account holds this figure</div>
  <div><span class="sw s"></span> school money</div>
  <div><span class="sw p"></span> where provenance ends</div>
  <div><span class="sw u"></span> real, but the split is unknown</div>
</div>

<div class="scroll">{svg}</div>

{body}

<p class="gen">Generated by <code>scripts/build_money_flow.py</code> from
<code>sources/data/lunenburg.db</code>. Do not edit — every figure is computed, and
<code>--check</code> fails if this file stops reproducing. Companion to
<code>money-in.html</code>, which is kept unchanged beside it.</p>
</div>
'''


def body_html(d, c):
    p = []
    a = p.append

    a('<h2>The $26m is four different numbers</h2>')
    a('<p>“The school budget” names the appropriation to department 300. Three other '
      'quantities get called the same thing, and they differ by up to 20%.</p>')
    d300 = next(v for n, v, k in d['depts'] if k == '300')
    ret = next((v for aid, dp, nm, v in d['elsewhere'] if aid.endswith('570018')), 0)
    monty = next((v for aid, dp, nm, v in d['elsewhere'] if aid.endswith('532000')), 0)
    pens = next((v for aid, dp, nm, v in d['elsewhere'] if aid.endswith('560001')), 0)
    stip = next((v for aid, dp, nm, v in d['elsewhere'] if aid.endswith('519021')), 0)
    funds_in = sum(r for _, _, r, _ in d['funds'])
    a('<table><tr><th>what is being asked</th><th></th><th class="v">FY2026</th></tr>')
    for q, v, why in [
        ('What the town appropriates to the school department', d300, 'dept 300, 258 accounts'),
        ('What the town spends on Lunenburg Public Schools', d300 + ret + stip,
         'plus school retiree health and the resource stipend, both outside dept 300'),
        ('What the town spends on education', d300 + ret + stip + monty,
         'plus the Monty Tech assessment — a different district'),
        ('What the schools have to spend', d300 + funds_in,
         'plus their own funds, which never enter the general fund'),
    ]:
        a(f'<tr><td>{q}</td><td><code>{why}</code></td><td class="v">{money(v)}</td></tr>')
    a('</table>')
    a(f'<p>And one that cannot be stated at all: the school share of the '
      f'<strong>{money(pens)}</strong> pension assessment.</p>')

    a('<h2>School money appropriated to other departments</h2>')
    a('<p>Each of these is identified by the name of an account in the town’s own ledger. '
      'None is inferred from a share.</p>')
    a('<table><tr><th>account</th><th>dept</th><th>name</th><th class="v">as voted</th></tr>')
    for aid, dept, nm, v in d['elsewhere']:
        a(f'<tr><td><code>{aid}</code></td><td>{dept}</td><td>{html.escape(nm)}</td>'
          f'<td class="v">{money(v)}</td></tr>')
    a('</table>')
    a('<div class="note"><strong>The pension line is the one that cannot be split.</strong> '
      f'<code>COUNT[Y] RET</code> covers town and school employees together and no '
      'published document says in what proportion. Teachers are not in it at all — they '
      'belong to the state system, whose cost Lunenburg never appropriates and never sees. '
      'The Worcester Regional Retirement System publishes an annual actuarial valuation by '
      'member unit; that is the document that would settle it.</div>')

    a('<h2>What the school department’s money pays for</h2>')
    a('<p>The 258 accounts, grouped by the function code the town assigns them. Function '
      'names are the district’s own, taken from its budget book; a code the book does not '
      'name is shown bare rather than named from general knowledge.</p>')
    a('<table><tr><th>function</th><th class="v">accounts</th><th class="v">as voted</th></tr>')
    for f, nm, v, n in d['uses']:
        label = f'{f} — {html.escape(nm)}' if f and nm else html.escape(str(nm or f))
        a(f'<tr><td>{label}</td><td class="v">{n or ""}</td><td class="v">{money(v)}</td></tr>')
    a('</table>')

    a('<h2>Money that never enters the general fund</h2>')
    a('<p>These are the schools’ own funds. They are not appropriated, they do not appear '
      'in the $26m, and they are actual rather than budgeted — so they must never be added '
      'to it.</p>')
    a('<table><tr><th>fund</th><th>name</th><th class="v">in</th><th class="v">out</th></tr>')
    for fund, nm, rev, sp in d['funds']:
        a(f'<tr><td><code>{fund}</code></td><td>{html.escape(nm)}</td>'
          f'<td class="v">{money(rev)}</td><td class="v">{money(sp or 0)}</td></tr>')
    a('</table>')
    a('<p><em>Nine months of a twelve-month year — the ledger we hold stops at 31 March.</em></p>')

    a('<h2>Why there is no line from Chapter 70 to the schools</h2>')
    a('<p>Because there is no such line to draw. Chapter 70 arrives as <strong>unrestricted '
      'revenue</strong> into fund 0100 and is thereafter indistinguishable from property '
      'tax. The town apportions general fund revenue across departments by share when it '
      'presents a budget, and that is a reasonable convention, but it is a convention: no '
      'dollar of state aid can be followed to a classroom.</p>')
    a('<p>The old diagram drew seven such lines, each labelled with a figure. This one '
      'refuses to, and states the refusal on the pot. <strong>The edge is not missing '
      'data. It does not exist.</strong></p>')
    return '\n'.join(p)


def render(c):
    svg, d = build(c)
    return PAGE.format(svg=svg, body=body_html(d, c))


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
        if open(OUT, encoding='utf-8').read() != fresh:
            raise SystemExit(f'STALE: {rel} no longer reproduces.\n'
                             f'  Run: python3 scripts/build_money_flow.py')
        print(f'ok: {rel} still reproduces')
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print(f'wrote {rel} ({len(fresh):,} bytes)')


if __name__ == '__main__':
    main()
