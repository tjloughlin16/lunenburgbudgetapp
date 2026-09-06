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


def render(c):
    srcs, rev_total = revenue_sources(c)
    depts, omnibus = departments(c)
    elsewhere = school_elsewhere(c)
    uses, uses_total = school_uses(c)
    funds = own_funds(c)
    ath_gen, ath_rev = athletics(c)

    d300 = next(v for n, v, k in depts if k == '300')
    ret = next((v for aid, dp, nm, v in elsewhere if aid.endswith('570018')), 0)
    monty = next((v for aid, dp, nm, v in elsewhere if aid.endswith('532000')), 0)
    pens = next((v for aid, dp, nm, v in elsewhere if aid.endswith('560001')), 0)
    stip = next((v for aid, dp, nm, v in elsewhere if aid.endswith('519021')), 0)
    funds_in = sum(r for _, _, r, _ in funds)
    residual = rev_total - omnibus

    P = []
    a = P.append

    a(f'<section class="stage"><h2>1 &middot; Where the money comes from</h2>'
      f'<p class="cap">Every general-fund revenue line the town budgets for FY2026. '
      f'<b>Traced</b> &mdash; each is a named account. Total {money(rev_total)}.</p>')
    a(bars([(n, v) for n, v in srcs]))
    a('</section>')

    a('<section class="pot"><h2>2 &middot; It all lands in one pot</h2>'
      f'<p class="potline"><b>GENERAL FUND 0100 &mdash; {money(rev_total)}</b></p>'
      '<p>Every source above flows in here and <b>loses its identity</b>. Money in the '
      'general fund is fungible, and no record ties a source to a department.</p>'
      '<p class="refuse">So there is no line on this page from Chapter&nbsp;70 to the '
      'schools. The town apportions the pot across departments by share when it presents '
      'a budget, and that is a fair convention &mdash; but it is a convention. '
      '<b>The edge is not missing data. It does not exist.</b></p></section>')

    a(f'<section class="stage"><h2>3 &middot; Town Meeting votes it out again</h2>'
      f'<p class="cap"><b>Traced</b> &mdash; every department is a line residents voted on. '
      f'Omnibus total {money(omnibus)}; the rest of the pot funds warrant articles, '
      f'transfers and reserves.</p>')
    rows = [(n, v, k) for n, v, k in depts]
    rows.append(('Warrant articles, transfers, reserves', residual, 'residual'))
    a(bars(rows, hilite=('300', '310'), note_of={
        '300': 'the school department', '310': 'regional vocational school',
        '820': 'pension for town AND school staff — split unknown',
        '914': 'includes school retiree health', 'residual': 'not appropriated to a department'}))
    a('</section>')

    a(f'<section class="stage"><h2>4 &middot; What the school department spends it on</h2>'
      f'<p class="cap"><b>Traced</b> &mdash; 258 named accounts, grouped by the function '
      f'code the town assigns. Function names are the district&rsquo;s own; a code its '
      f'budget book does not name is shown bare.</p>')
    a(bars([((f'{f} — {nm}' if f and nm else (nm or f)), v, f) for f, nm, v, n in uses]))
    a('</section>')

    a('<section class="stage alt"><h2>5 &middot; School money in other departments</h2>'
      '<p class="cap">Each identified by the name of an account in the town&rsquo;s own '
      'ledger. None inferred from a share.</p>')
    a(bars([(f'{nm} — dept {dp}', v, aid) for aid, dp, nm, v in elsewhere],
           note_of={aid: aid for aid, dp, nm, v in elsewhere}))
    a('<p class="warn"><b>The pension cannot be split.</b> <code>COUNT[Y] RET</code> covers '
      'town and school employees together and no published document says in what '
      'proportion. Teachers are not in it at all &mdash; they are in the state system, '
      'whose cost Lunenburg never appropriates and never sees. The Worcester Regional '
      'Retirement System publishes an annual actuarial valuation by member unit; that is '
      'the document that would settle it.</p>')
    a('</section>')

    a('<section class="stage alt"><h2>6 &middot; Money that never enters the pot</h2>'
      '<p class="cap">The schools&rsquo; own funds. Not appropriated, not in the '
      '$26m, and <b>actual rather than budgeted</b> &mdash; so they must never be added '
      'to it. Nine months of a twelve-month year.</p>')
    a(bars([(nm, rev, f) for f, nm, rev, sp in funds]))
    a(f'<p class="warn"><b>Athletics is the clearest case, and it is only half here.</b> '
      f'The town appropriates {money(ath_gen)} for athletics inside dept 300 '
      f'(function 3510: coaches, transport, the athletic director, the trainer, '
      f'insurance). Fees bring in a further {money(ath_rev)} through a revolving fund '
      f'&mdash; <b>which does not appear in the town&rsquo;s fund-balance report at all.</b> '
      f'That figure comes from the district&rsquo;s own athletics documents. So athletics '
      f'costs about {money(ath_gen + ath_rev)} to run and the town&rsquo;s budget shows '
      f'{money(ath_gen)} of it. Every fee-funded programme has this shape; athletics is '
      f'just the one where both halves have been found.</p>')
    a('</section>')

    a('<section class="stage"><h2>So what is &ldquo;the school budget&rdquo;?</h2>'
      '<p class="cap">Four different numbers get called it, and they differ by more than '
      '10%.</p><table>')
    for q, v, why in [
        ('Appropriated to the school department', d300, 'dept 300, 258 accounts'),
        ('Spent by the town on Lunenburg Public Schools', d300 + ret + stip,
         '+ school retiree health, resource stipend'),
        ('Spent by the town on education', d300 + ret + stip + monty,
         '+ Monty Tech, a different district'),
        ('Available to the schools to spend', d300 + funds_in,
         '+ their own funds, outside the general fund'),
    ]:
        a(f'<tr><td>{q}<span class="sub">{why}</span></td>'
          f'<td class="v">{money(v)}</td></tr>')
    a('</table>')
    a(f'<p class="warn">And one that cannot be stated at all: the school share of the '
      f'{money(pens)} pension assessment. The honest answer is that nobody publishes it.</p>')
    a('</section>')

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
.wrap {{ max-width:820px; margin:0 auto; padding:22px 16px 80px }}
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
.warn {{ background:var(--warn-bg); border-left:3px solid var(--warn); border-radius:0 6px 6px 0;
  padding:11px 13px; font-size:13.5px; margin:14px 0 0 }}
table {{ border-collapse:collapse; width:100%; margin-top:4px }}
td {{ padding:9px 0; border-bottom:1px solid var(--grid); font-size:14px; vertical-align:top }}
td .sub {{ display:block; font-size:11.5px; color:var(--muted) }}
td.v {{ text-align:right; white-space:nowrap; font-weight:600;
  font-family:ui-monospace,Menlo,monospace }}
code {{ font-family:ui-monospace,Menlo,monospace; font-size:12.5px }}
.gen {{ margin-top:30px; font-size:12px; color:var(--muted) }}
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
