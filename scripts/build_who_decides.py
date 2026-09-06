#!/usr/bin/env python3
"""Every dollar into the town, where it lands, and who actually decides how it is spent.

    python3 scripts/build_who_decides.py
    python3 scripts/build_who_decides.py --check

Writes `notes/reference/data-model/who-decides.html`.

WHY THIS AND NOT ANOTHER MONEY PAGE

`money-flow.html` follows money to the schools. This follows all of it, to all sixty-seven
departments, and adds the question none of the other pages ask: **who gets to decide.**

That turns out to be the answer a resident actually needs. A person at Town Meeting is
voting on an omnibus budget of $51.2M and reasonably believes they are deciding it. Most
of it is already decided — by an assessment the town cannot refuse, by a debt vote taken
years ago, by a bargaining agreement, or by another elected body that will allocate the
bottom line after the vote.

**Roughly a fifth of the budget is a line Town Meeting is actually setting.** Everything
else is real, legitimate and already committed, and nothing on the warrant says which is
which.

HOW CONTROL IS CLASSIFIED, AND HOW MUCH TO TRUST IT

Every class carries the evidence for it, because these are judgements about governance and
the reader should be able to disagree with each one separately:

  stated      the ledger's own name says it — `WRRS ASSESSMENT`, `PRINCIPAL SERIAL LOANS`
  minutes     established from the town's own meeting record, quoted
  outside     depends on knowing how Massachusetts municipal government works. Flagged
              every time, because it is the weakest kind of claim here
  residual    what is left after the others. `discretionary` is a residual and is marked
              as one -- it is not a positive finding about any department

**`delegated` does not mean Town Meeting has no say.** It sets the total, which is the
largest lever anyone has. It means it does not set the LINES, and the difference is exactly
what a resident asking "why can't we just cut X" runs into.
"""

import argparse
import html
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'notes', 'reference', 'data-model', 'who-decides.html')
FY, P_DEPT, P_ACCT = 2026, 9, 12

# dept -> (class, how, why). Anything not here falls to `discretionary`, which is a
# residual and says so.
CONTROL = {
    '820': ('assessed', 'stated', 'Named `WRRS ASSESSMENT`. The Worcester Regional '
            'Retirement System sets it; the town pays it.'),
    '825': ('assessed', 'stated', 'Named `STATE ASSESSMENTS` — the Cherry Sheet charges.'),
    '310': ('assessed', 'stated', 'Named `MONTY TECH ASSESSMENT`. A regional school '
            'district assesses its member towns.'),
    '841': ('assessed', 'outside', 'Montachusett Regional Planning Commission — a regional '
            'body assessing its members.'),
    '521': ('assessed', 'outside', 'Nashoba Associated Boards of Health — a regional '
            'district.'),
    '522': ('assessed', 'outside', 'Nashoba Nursing — same.'),
    '710': ('committed', 'stated', 'Named `PRINCIPAL SERIAL LOANS`. Repayment of borrowing '
            'authorised by votes already taken.'),
    '751': ('committed', 'stated', 'Named `INTEREST SERIAL LOANS`. Same.'),
    '754': ('committed', 'stated', 'Loan administrative fees.'),
    '300': ('delegated', 'minutes', 'Town Meeting votes the school bottom line; the School '
            'Committee allocates within it. Its own minutes carry `Review &amp; Approve Line '
            'Item Transfers` as a standing agenda item, with transfers voted line by line.'),
    '301': ('delegated', 'stated', 'School non-recurring, a separate article.'),
    '610': ('delegated', 'outside', 'A public library is governed by elected trustees.'),
    '914': ('bargained', 'outside', 'Health insurance, active and retiree. Rates and shares '
            'are set by bargaining and by the insurer, not by a vote on an amount.'),
    '912': ('bargained', 'outside', 'Workers compensation — claims driven.'),
    '913': ('bargained', 'outside', 'Unemployment compensation — claims driven.'),
    '945': ('bargained', 'outside', 'Liability insurance — premium driven.'),
    '993': ('transfer', 'stated', 'Named `TRANSFER TO CAPITAL PROJECT FD`.'),
    '996': ('transfer', 'stated', 'Named `TRANSFER TO TRUST FUNDS`.'),
}

CLASSES = [
    ('assessed', 'Assessed by somebody else',
     'A bill the town did not set and cannot refuse. Another body — a regional district, '
     'the state, the retirement system — decides the amount and sends it.'),
    ('committed', 'Committed by votes already taken',
     'Debt service. The decision was made when the borrowing was authorised, sometimes '
     'decades ago, and this year’s meeting cannot revisit it.'),
    ('delegated', 'Town Meeting votes a total; another elected body allocates',
     'The schools and the library. **Town Meeting still sets the total, which is the '
     'largest lever there is.** It does not set the lines inside it.'),
    ('bargained', 'Set by bargaining, claims and premiums',
     'Insurance and compensation. An amount is voted, but what drives it is agreements and '
     'events rather than a choice made at the meeting.'),
    ('transfer', 'Moved to capital and trust funds',
     'Voted as a transfer rather than as spending on anything.'),
    ('discretionary', 'Discretionary — the meeting sets the amount, a department spends it',
     '**A residual.** What is left once the classes above are taken out. It is not a '
     'positive finding about any of these departments.'),
]


def db():
    if not os.path.exists(DB):
        raise SystemExit(f'{DB} missing. Run: python3 scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def money(v):
    return f'${v:,.0f}'


def bars(rows, top=None):
    top = top or max((v for _, v, *_ in rows), default=1) or 1
    out = ['<div class="bars">']
    for label, value, *rest in rows:
        cls = rest[0] if rest else ''
        sub = rest[1] if len(rest) > 1 else ''
        out.append(
            f'<div class="row {cls}"><div class="lab">{html.escape(str(label))}'
            + (f'<span class="sub">{html.escape(sub)}</span>' if sub else '')
            + f'</div><div class="track"><div class="fill" '
              f'style="width:{max(0.6, value/top*100):.2f}%"></div></div>'
              f'<div class="amt">{money(value)}</div></div>')
    out.append('</div>')
    return '\n'.join(out)


def render(c):
    rev_gf = c.execute(f"""SELECT SUM(budgeted) FROM v_revenue
                           WHERE fy={FY} AND fund='0100'""").fetchone()[0]
    other = c.execute(f"""SELECT fund, fund_name, SUM(budgeted) v FROM v_revenue
                          WHERE fy={FY} AND fund<>'0100' GROUP BY fund
                          HAVING v>0 ORDER BY v DESC""").fetchall()
    sr = c.execute(f"""SELECT SUM(revenue) FROM v_fund_year
                       WHERE fy={FY} AND period={P_DEPT}""").fetchone()[0] or 0

    depts = c.execute(f"""SELECT a.dept, a.name, l.original v FROM ledger_snapshot l
                          JOIN account a USING (account_id)
                          WHERE l.fy={FY} AND l.period={P_DEPT} AND a.level='department'
                            AND a.account_type='expense' ORDER BY l.original DESC""").fetchall()
    omnibus = sum(r['v'] for r in depts)
    grouped = {}
    for r in depts:
        k = CONTROL.get(r['dept'], ('discretionary', 'residual', ''))[0]
        grouped.setdefault(k, []).append(r)

    P = []
    a = P.append

    a('<section class="stage"><h2>1 &middot; Every dollar into the town</h2>'
      '<p class="cap">FY2026. The general fund is budgeted revenue; the other funds are '
      'their own money and are shown on their own bases. <b>These are not added</b> — a '
      'budget and nine months of actuals are different quantities.</p>')
    rows = [('General fund — 192 revenue accounts', rev_gf, 'hi')]
    rows += [(f'{r["fund"]} {r["fund_name"].title()}', r['v'], '') for r in other]
    rows.append(('All special revenue funds (actual, 9 months)', sr, 'alt'))
    a(bars(rows))
    a('</section>')

    a('<section class="pot"><h2>2 &middot; The general fund is one pot</h2>'
      '<p>Every one of those 192 accounts pays into fund 0100 and loses its identity '
      'there. <b>No record ties a source to a department.</b> The town apportions by share '
      'when it presents a budget; that is a convention for explaining, not a route any '
      'dollar takes.</p>'
      '<p class="refuse">Which means the question “what does Chapter&nbsp;70 pay for?” has '
      'no answer, and the question “who decides how the pot is spent?” has a very good '
      'one. That is what the rest of this page is.</p></section>')

    a(f'<section class="stage"><h2>3 &middot; Who actually decides</h2>'
      f'<p class="cap">The omnibus budget is {money(omnibus)} across {len(depts)} '
      f'departments. A person at Town Meeting is voting on all of it and reasonably '
      f'believes they are deciding it.</p>')
    tots = [(lbl, sum(r['v'] for r in grouped.get(k, [])), 'hi' if k == 'discretionary'
             else '', f'{sum(r["v"] for r in grouped.get(k, []))/omnibus*100:.1f}% of the '
                      f'budget')
            for k, lbl, _ in CLASSES]
    a(bars(tots))
    disc = sum(r['v'] for r in grouped.get('discretionary', []))
    a(f'<p class="warn"><b>{disc/omnibus*100:.1f}% of the budget is a line Town Meeting is '
      f'actually setting.</b> Everything else is real, legitimate, and already decided — '
      f'by an assessment the town cannot refuse, a debt vote taken years ago, a bargaining '
      f'agreement, or another elected body that allocates the total after the vote. '
      f'<b>Nothing on the warrant says which is which.</b></p>')
    a('</section>')

    for k, lbl, blurb in CLASSES:
        rows = grouped.get(k, [])
        if not rows:
            continue
        sub = sum(r['v'] for r in rows)
        a(f'<section class="stage alt"><h2>{lbl} &mdash; {money(sub)}</h2>'
          f'<p class="cap">{blurb}</p>')
        a(bars([(r['name'].title(), r['v'], '', f'dept {r["dept"]}')
                for r in rows[:14]]))
        ev = [(d, CONTROL[d]) for d in CONTROL if CONTROL[d][0] == k]
        if ev:
            a('<table><tr><th>dept</th><th>how we know</th><th>why</th></tr>')
            for d, (_, how, why) in sorted(ev):
                a(f'<tr><td>{d}</td><td><code>{how}</code></td><td>{why}</td></tr>')
            a('</table>')
        if k == 'discretionary' and len(rows) > 14:
            a(f'<p class="cap">…and {len(rows)-14} more, every one under '
              f'{money(rows[14]["v"])}.</p>')
        a('</section>')

    a('<section class="stage"><h2>What this page cannot tell you</h2>'
      '<ul>'
      '<li><b>Which source paid for which department.</b> There is no such fact. See the '
      'pot above.</li>'
      '<li><b>Whether an assessment is fair.</b> Only that the town does not set it.</li>'
      '<li><b>What the special revenue funds were spent on.</b> We hold totals for them '
      'and no account detail — the town produces an expense report for the general fund '
      'and for each enterprise fund, and not for these.</li>'
      '<li><b>Who decides inside a delegated total.</b> The School Committee votes line '
      'item transfers in public and its minutes record them; the library’s equivalent is '
      'not in this archive.</li>'
      '</ul></section>')
    return PAGE.format(body='\n'.join(P))


PAGE = '''<meta charset="utf-8">
<title>Where every dollar lands, and who decides — Lunenburg FY2026</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ --bg:#fbfaf8; --card:#fff; --ink:#191919; --muted:#6b6b6b; --grid:#e2ded7;
  --traced:#1f5c3d; --hi:#9a4f14; --warn:#8a6d10; --warn-bg:#faf3de;
  --potbg:#2c2b28; --potink:#f2efe9; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#141412; --card:#1c1b19; --ink:#eeebe6; --muted:#a09b93; --grid:#34322e;
    --traced:#79c39f; --hi:#e2a068; --warn:#d9bd67; --warn-bg:#2c2718;
    --potbg:#e8e4dc; --potink:#1a1a18; }}
}}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  -webkit-text-size-adjust:100% }}
.wrap {{ max-width:820px; margin:0 auto; padding:22px 16px 80px }}
header {{ border-bottom:2px solid var(--ink); padding-bottom:14px }}
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
.lab {{ grid-area:lab; font-size:13.5px; font-weight:600; overflow-wrap:anywhere }}
.lab .sub {{ display:block; font-weight:400; font-size:11.5px; color:var(--muted) }}
.amt {{ grid-area:amt; text-align:right; font-size:13.5px; white-space:nowrap;
  font-family:ui-monospace,Menlo,monospace }}
.track {{ grid-area:bar; background:var(--grid); border-radius:3px; height:9px }}
.fill {{ background:var(--traced); height:100%; border-radius:3px; min-width:2px }}
.row.hi .fill {{ background:var(--hi) }}
.row.hi .lab {{ color:var(--hi) }}
.row.alt .fill {{ background:var(--muted) }}
.pot {{ background:var(--potbg); color:var(--potink); border-radius:10px; padding:18px 16px;
  margin:16px 0 }}
.pot h2 {{ color:var(--potink) }}
.pot p {{ font-size:14px; margin:8px 0 0 }}
.refuse {{ border-top:1px solid rgba(128,128,128,.4); padding-top:10px; margin-top:12px }}
.warn {{ background:var(--warn-bg); border-left:3px solid var(--warn);
  border-radius:0 6px 6px 0; padding:11px 13px; font-size:14px; margin:14px 0 0 }}
table {{ border-collapse:collapse; width:100%; margin-top:12px; font-size:13px }}
th,td {{ text-align:left; padding:6px 8px 6px 0; border-bottom:1px solid var(--grid);
  vertical-align:top }}
code {{ font-family:ui-monospace,Menlo,monospace; font-size:12px }}
ul {{ font-size:14px; padding-left:20px }} li {{ margin:6px 0 }}
.gen {{ margin-top:30px; font-size:12px; color:var(--muted) }}
@media (min-width:680px) {{
  .row {{ grid-template-columns:40% 1fr 20%; grid-template-areas:"lab bar amt"; gap:12px;
    align-items:center }}
  .track {{ height:11px }}
}}
</style>

<div class="wrap">
<header>
  <div class="kicker">Lunenburg Budget Project &middot; Data architecture</div>
  <h1>Where every dollar lands, and who decides</h1>
  <p class="standfirst">All money into the town in FY2026, where it comes to rest, and —
  the question the budget documents never answer — who actually gets to decide how it is
  spent.</p>
</header>

{body}

<p class="gen">Generated by <code>scripts/build_who_decides.py</code> from
<code>sources/data/lunenburg.db</code>. Every figure is computed; <code>--check</code>
fails if this file stops reproducing.</p>
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
                             f'  Run: python3 scripts/build_who_decides.py')
        print(f'ok: {rel} still reproduces')
        return
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print(f'wrote {rel} ({len(fresh):,} bytes)')


if __name__ == '__main__':
    main()
