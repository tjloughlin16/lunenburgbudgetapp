#!/usr/bin/env python3
"""The whole town: every dollar in, every dollar out, and what it can be told about itself.

    python3 scripts/build_town_flow.py
    python3 scripts/build_town_flow.py --check

Writes `notes/reference/data-model/town-money-flow.html`.

WHY THIS EXISTS

`money-flow-v2.html` does this for the schools. Doing it for the whole town was TJ's
instruction — *"LETS SEE WHAT WE LEARN FROM THAT"* — and the answer is that the town
version has a shape the school version does not, because the town has four separate money
systems and only one of them is the thing anybody argues about.

WHAT IT INHERITS FROM THE SCHOOL VERSION, DELIBERATELY

Four rules, every one of which was learned by breaking it first:

  1. **Each dollar appears exactly once**, so the right column adds. The first school
     diagram had programme boxes overlapping the budget box and its total was meaningless.
  2. **In, spent and held are three numbers, never one.** A fund is a tank, not a pipe.
     The circuit breaker received $325,970, spent $4,005, and holds $615,301 — and "spent"
     alone made it look like a small programme rather than a reserve.
  3. **Never identify anything by its name.** Ten characters truncates BUSINESS and BUS to
     the same string, and TRANSFER and TRANSPORTATION likewise.
  4. **The columns do not balance and should not.** Revenue is not spending; the
     difference is the change in what is held.

WHAT IS NEW HERE

The town runs **four money systems that do not mix**, and the general fund — the only one
Town Meeting really debates — is 93% of the money and the only one where a dollar's origin
cannot be followed. The enterprise funds are the opposite: rate-funded, self-contained, and
traceable end to end. Putting them beside each other is the point of the page.
"""

import argparse
import html
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'notes', 'reference', 'data-model', 'town-money-flow.html')
SCHOOL = os.path.join(ROOT, 'notes', 'reference', 'data-model', 'money-flow-v2.html')
FY, P_DEPT, P_ACCT = 2026, 9, 12

# Revenue, by who SETS the amount. Exact names — never prefixes. See rule 3.
REV = {
    'levy': (['RE TAXES', 'PP TAXES', 'SUPPLE TAX', 'RE FY27', 'PP FY27', 'PREPAYPP',
              'ROLL BACK', 'MISCTAXOVE', 'DEF PROP'],
             'Property tax levy', 'Set by the town, inside the Proposition 2½ cap'),
    'state': (['CH 70 AID', 'UGGA', 'SCHCOSTREI', 'SPED REIMB', 'CHARTER', 'STATE LAND',
               'VET ABATE', 'ABATE ELDE', 'ABATE SPOU', 'BLIND ABAT', 'S6CH115VET',
               'MSBA REIMB', 'ADD AID LB', 'ADDAIDAPPR', 'ADDAIDESTR', "ADD'L ASST",
               'MUN RELIEF', 'LOC AID AD', 'STATE REVE', 'MUN STAB', 'SCHOOL TRA',
               'ERATEREIMB', 'MED D DRUG', 'MEDRECMRC', 'QUINN BILL', 'CH 81'],
              'State aid', 'Set by the Legislature. No local say at all'),
    'onetime': (['FBCYBUDGET', 'PY BAL', 'BOND PROC', 'PREMIUMS', 'INS SETTLR',
                 'SALE TOWNP', 'SALE STAND'],
                'One-time money', 'Free cash and proceeds. Spendable once'),
    'transfer': (['TRANS ENT', 'TRANSOFFSE', 'TRANSRECRE', 'OP TRAN AG', 'OP TRAN CP',
                  'OP TRAN SR', 'OP TRAN TR'],
                 'Transfers in', 'From the town’s own other funds. Not new money'),
}

# Spending, by who DECIDES. Same table as who-decides.html, kept in step by hand because
# the two pages answer different questions with the same classification.
CONTROL = {
    '820': 'assessed', '825': 'assessed', '310': 'assessed', '841': 'assessed',
    '521': 'assessed', '522': 'assessed',
    '710': 'committed', '751': 'committed', '754': 'committed',
    '300': 'delegated', '301': 'delegated', '610': 'delegated',
    '914': 'bargained', '912': 'bargained', '913': 'bargained', '945': 'bargained',
    '993': 'transfer', '996': 'transfer',
}
CLASS_LABEL = {
    'delegated': 'Voted as a total, allocated by another elected body',
    'discretionary': 'Discretionary — the meeting sets the amount',
    'assessed': 'Assessed by somebody else',
    'bargained': 'Insurance and compensation',
    'committed': 'Debt service, already committed',
    'transfer': 'Transfers to capital and trust',
}


def db():
    if not os.path.exists(DB):
        raise SystemExit(f'{DB} missing. Run: python3 scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def money(v):
    return f'${v:,.0f}' if v is not None else 'not found'


def gather(c):
    d = {}
    d['rev'] = {r['name']: r['v'] for r in c.execute(f"""
        SELECT name, SUM(budgeted) v FROM v_revenue WHERE fy={FY} AND fund='0100'
        GROUP BY name HAVING v > 0""")}
    idx = {n: k for k, (names, _, _) in REV.items() for n in names}
    d['revclass'] = {}
    for n, v in d['rev'].items():
        d['revclass'].setdefault(idx.get(n, 'local'), 0)
        d['revclass'][idx.get(n, 'local')] += v
    d['rev_total'] = sum(d['rev'].values())

    d['ent_in'] = [(r['fund'], r['fund_name'], r['v']) for r in c.execute(f"""
        SELECT fund, fund_name, SUM(budgeted) v FROM v_revenue
        WHERE fy={FY} AND fund <> '0100' GROUP BY fund HAVING v > 0 ORDER BY v DESC""")]
    d['ent_out'] = {r['fund']: r['v'] for r in c.execute(f"""
        SELECT a.fund, SUM(l.original) v FROM ledger_snapshot l JOIN account a USING (account_id)
        WHERE l.fy={FY} AND a.fund <> '0100' AND a.account_type='expense'
        GROUP BY a.fund HAVING v > 0""")}

    depts = c.execute(f"""SELECT a.dept, a.name, l.original v FROM ledger_snapshot l
        JOIN account a USING (account_id) WHERE l.fy={FY} AND l.period={P_DEPT}
          AND a.level='department' AND a.account_type='expense'
        ORDER BY l.original DESC""").fetchall()
    d['omnibus'] = sum(r['v'] for r in depts)
    d['depts'] = depts
    d['byclass'] = {}
    for r in depts:
        k = CONTROL.get(r['dept'], 'discretionary')
        d['byclass'].setdefault(k, []).append(r)

    sr = c.execute(f"""SELECT SUM(revenue) i, SUM(spent) o, SUM(closing_balance) h
        FROM v_fund_year WHERE fy={FY} AND period={P_DEPT}""").fetchone()
    d['sr_in'], d['sr_out'], d['sr_held'] = sr['i'] or 0, sr['o'] or 0, sr['h'] or 0
    d['srfunds'] = c.execute(f"""SELECT fund, name, revenue, spent, closing_balance
        FROM v_fund_year WHERE fy={FY} AND period={P_DEPT} AND revenue > 0
        ORDER BY revenue DESC""").fetchall()
    d['srspend'] = c.execute(f"""SELECT fund, name, revenue, spent, closing_balance
        FROM v_fund_year WHERE fy={FY} AND period={P_DEPT} AND spent > 0
        ORDER BY spent DESC""").fetchall()
    return d


# GAPS, drawn as boxes rather than described in a paragraph.
#
# A diagram that shows only what is known reads as complete. These are the things the
# town's own records cannot answer, and they belong in the picture at the same size as
# everything else — on the side of the flow where they would sit if they could be seen.
GAPS_IN = [
    ('Bus fees', 'charged by published policy · no destination found in any ledger'),
    ('Trust fund income', 'scholarships, cemetery, stabilisation · extract is check-failed'),
    ('Student activity accounts', 'held by the school under its own authority · not in the '
                                  'town’s books at all'),
    ('Grants received in earlier years', 'spent now, booked then · nine funds, no FY26 '
                                         'revenue'),
]
GAPS_OUT = [
    ('School share of the pension', 'inside WRRS · town and school staff together, no '
                                    'published split'),
    ('Debt service by project', 'two accounts for ALL town borrowing · school buildings '
                                'cannot be separated'),
    ('What the capital transfers bought', 'two transfer lines · no project detail'),
    ('What any special revenue fund bought', 'no expense report exists for these funds · '
                                             'purpose is presumed, never observed'),
]


def diagram(d):
    """Three columns, because two would be a lie.

    The school diagram is two columns — sources on the left, where it lands on the right —
    and that works there because the school's money either IS the appropriation or comes
    from a fund that bypasses it. For the town it would be dishonest: drawing a line from
    `property tax` to `police department` asserts a connection no record supports, and that
    connection not existing is the main finding of this whole workstream.

    So the general fund sits in the middle as a single tall box, and every source on the
    left connects to IT rather than to any department. Money is fungible once it lands
    there; the diagram stops at the boundary where the evidence stops.

    **The enterprise funds bypass it entirely**, drawn as long lines running under the pot
    from their own revenue to their own spending. That bypass is the point of the picture:
    it is the same town, the same accountants, and a dollar can be followed the whole way —
    because the fund IS the boundary.

    Line styles carry certainty, as everywhere else here:
      solid       traced
      dashed      restricted — the fund exists for one purpose, and its spending is
                  not observed because no expense report for these funds exists
    """
    LH, GAP = 54, 11
    LX, MX, RX, BW, MW = 20, 350, 680, 250, 200
    W = 950

    lrows = [('levy', 'Property tax levy', d['revclass'].get('levy', 0), 'gf'),
             ('state', 'State aid', d['revclass'].get('state', 0), 'gf'),
             ('local', 'Local receipts', d['revclass'].get('local', 0), 'gf'),
             ('onetime', 'One-time money', d['revclass'].get('onetime', 0), 'gf'),
             ('transfer', 'Transfers in', d['revclass'].get('transfer', 0), 'gf')]
    ent = [(f, nm.title()[:24], v) for f, nm, v in d['ent_in']]
    for f, nm, v in ent:
        lrows.append((f'ent-{f}', nm, v, 'ent'))
    lrows.append(('sr', 'Special revenue — ALL school', d['sr_in'], 'sr'))

    # DEPARTMENTS, not governance categories. The right column of the school diagram is
    # concrete places money lands -- the school budget, athletics, food service, Monty Tech
    # -- and the town's has to be the same thing or the two are not the same model. The
    # "who decides" classification is a different lens and lives on `who-decides.html`; it
    # was imported here without being asked for and changed what the column meant.
    top = d['depts'][:10]
    rest = sum(r['v'] for r in d['depts'][10:])
    rrows = [(f'd{r["dept"]}', r['name'].title()[:28], r['v'], 'gf') for r in top]
    rrows.append(('drest', f'The other {len(d["depts"])-10} departments', rest, 'gf'))
    for f, nm, v in ent:
        if d['ent_out'].get(f):
            rrows.append((f'ento-{f}', nm + ' — spent', d['ent_out'][f], 'ent'))
    rrows.append(('sro', 'Special revenue spent — ALL school', d['sr_out'], 'sr'))

    ly = {k: 52 + i * (LH + GAP) for i, (k, *_) in enumerate(lrows)}
    ry = {k: 52 + i * (LH + GAP) for i, (k, *_) in enumerate(rrows)}
    H = 52 + max(len(lrows), len(rrows)) * (LH + GAP) + 16
    pot_top, pot_bot = ly['levy'], ly['transfer'] + LH

    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="flow" '
         f'role="img" aria-label="Every dollar into Lunenburg and where it goes">',
         '<text class="dhd" x="20" y="30">MONEY IN</text>',
         f'<text class="dhd" x="{MX}" y="30">WHERE IT POOLS</text>',
         f'<text class="dhd" x="{RX}" y="30">MONEY OUT</text>']

    def edge(x1, y1, x2, y2, cls, dip=0):
        mx = (x1 + x2) / 2
        if dip:
            o.append(f'<path class="e {cls}" d="M{x1},{y1} C{mx},{y1+dip} {mx},{y2+dip} '
                     f'{x2},{y2}"/>')
        else:
            o.append(f'<path class="e {cls}" d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}"/>')

    for k, *_ in lrows[:5]:
        edge(LX + BW, ly[k] + LH / 2, MX, pot_top + (pot_bot - pot_top) / 2, 'traced')
    for k, lab, v, kind in rrows:
        if kind == 'gf':
            edge(MX + MW, pot_top + (pot_bot - pot_top) / 2, RX, ry[k] + LH / 2, 'traced')
    for f, nm, v in ent:
        if d['ent_out'].get(f):
            edge(LX + BW, ly[f'ent-{f}'] + LH / 2, RX, ry[f'ento-{f}'] + LH / 2,
                 'bypass', dip=120)
    edge(LX + BW, ly['sr'] + LH / 2, RX, ry['sro'] + LH / 2, 'restricted', dip=140)

    o.append(f'<g class="b pot"><rect x="{MX}" y="{pot_top}" width="{MW}" '
             f'height="{pot_bot - pot_top}" rx="7"/>'
             f'<text class="bl pw" x="{MX+12}" y="{pot_top+24}">GENERAL FUND 0100</text>'
             f'<text class="bv pw" x="{MX+12}" y="{pot_top+44}">'
             f'{money(d["rev_total"])}</text>')
    for i, line in enumerate(['Every source on the left flows',
                              'in here and loses its identity.',
                              'No record ties a source to a',
                              'department, so no line crosses',
                              'this box — the diagonal edge',
                              'does not exist.']):
        o.append(f'<text class="potnote" x="{MX+12}" y="{pot_top+70+i*15}">{line}</text>')
    o.append('</g>')

    for rows, ys, x, w in ((lrows, ly, LX, BW), (rrows, ry, RX, BW)):
        for k, label, v, kind in rows:
            y = ys[k]
            sub = ''
            if k == 'sr':
                sub = f'{len(d["srfunds"])} funds · holding {money(d["sr_held"])}'
            elif k == 'sro':
                sub = f'{len(d["srspend"])} funds · itemised in the table below'
            elif kind == 'ent':
                sub = 'rate-funded · bypasses the pot'
            o.append(f'<g class="b {kind}"><rect x="{x}" y="{y}" width="{w}" '
                     f'height="{LH}" rx="5"/>'
                     f'<text class="bl" x="{x+10}" y="{y+20}">{html.escape(label)}</text>'
                     f'<text class="bv" x="{x+10}" y="{y+37}">{money(v)}</text>'
                     + (f'<text class="bs" x="{x+10}" y="{y+49}">{html.escape(sub)}</text>'
                        if sub else '') + '</g>')
    # The gaps, at the foot of each column, at the same size as everything else.
    gy = 52 + max(len(lrows), len(rrows)) * (LH + GAP) + 34
    o.append(f'<text class="dhd gap" x="{LX}" y="{gy-12}">MONEY IN WE CANNOT SEE</text>')
    o.append(f'<text class="dhd gap" x="{RX}" y="{gy-12}">SPENDING WE CANNOT SPLIT</text>')
    for i, (label, why) in enumerate(GAPS_IN):
        y = gy + i * (LH + GAP)
        o.append(f'<g class="b gap"><rect x="{LX}" y="{y}" width="{BW}" height="{LH}" '
                 f'rx="5"/><text class="bl gl" x="{LX+10}" y="{y+20}">'
                 f'{html.escape(label)}</text>'
                 f'<text class="bs" x="{LX+10}" y="{y+36}">{html.escape(why[:44])}</text>'
                 f'<text class="bs" x="{LX+10}" y="{y+47}">{html.escape(why[44:88])}</text>'
                 f'</g>')
    for i, (label, why) in enumerate(GAPS_OUT):
        y = gy + i * (LH + GAP)
        o.append(f'<g class="b gap"><rect x="{RX}" y="{y}" width="{BW}" height="{LH}" '
                 f'rx="5"/><text class="bl gl" x="{RX+10}" y="{y+20}">'
                 f'{html.escape(label)}</text>'
                 f'<text class="bs" x="{RX+10}" y="{y+36}">{html.escape(why[:44])}</text>'
                 f'<text class="bs" x="{RX+10}" y="{y+47}">{html.escape(why[44:88])}</text>'
                 f'</g>')
    o[0] = o[0].replace(f'viewBox="0 0 {W} {H}"',
                        f'viewBox="0 0 {W} {gy + len(GAPS_IN)*(LH+GAP) + 16}"')
    o.append('</svg>')
    return '\n'.join(o)


def bars(rows):
    top = max((v for _, v, *_ in rows), default=1) or 1
    o = ['<div class="bars">']
    for label, value, *rest in rows:
        cls, sub = (rest + ['', ''])[:2]
        o.append(f'<div class="row {cls}"><div class="lab">{html.escape(str(label))}'
                 + (f'<span class="sub">{html.escape(sub)}</span>' if sub else '')
                 + f'</div><div class="track"><div class="fill" '
                   f'style="width:{max(0.6, value/top*100):.2f}%"></div></div>'
                   f'<div class="amt">{money(value)}</div></div>')
    o.append('</div>')
    return '\n'.join(o)


def render(c):
    d = gather(c)
    P = []
    a = P.append
    ent_in_total = sum(v for _, _, v in d['ent_in'])
    ent_out_total = sum(d['ent_out'].values())
    town_in = d['rev_total'] + ent_in_total + d['sr_in']
    town_out = d['omnibus'] + ent_out_total + d['sr_out']

    a(f'<section class="metrics">'
      f'<div class="m"><div class="mk">Every dollar into the town</div>'
      f'<div class="mv">{money(town_in)}</div><div class="ms">General fund, enterprise '
      f'funds and special revenue funds. <b>Mixed bases — see below.</b></div></div>'
      f'<div class="m"><div class="mk">Every dollar out</div>'
      f'<div class="mv">{money(town_out)}</div><div class="ms">The omnibus budget, the '
      f'enterprise funds and the special revenue funds.</div></div>'
      f'<div class="m hi"><div class="mk">Sitting in accounts, unspent</div>'
      f'<div class="mv">{money(d["sr_held"])}</div><div class="ms">Held across the special '
      f'revenue funds at 31 March. Not income, not spending: money that arrived and '
      f'stopped.</div></div>'
      f'<div class="m"><div class="mk">The general fund’s share of it all</div>'
      f'<div class="mv">{d["rev_total"]/town_in*100:.0f}%</div>'
      f'<div class="ms">The one system Town Meeting debates — and the only one where a '
      f'dollar’s origin cannot be followed.</div></div></section>')

    a('<div class="scroll">' + diagram(d) + '</div>')
    a('<div class="key"><span><i class="k traced"></i>traced</span>'
      '<span><i class="k bypass"></i>bypasses the general fund entirely — rate-funded and '
      'ring-fenced</span>'
      '<span><i class="k restricted"></i>the fund spent it; <b>purpose not observed</b>'
      '</span></div>')

    n_rev = len(d['rev'])
    a(f'<section class="stage"><h2>Can this page say “here is every way money comes in, '
      f'itemised”?</h2>'
      f'<p><b>Not quite, and the difference matters.</b> It is <i>classified</i>, not '
      f'<i>itemised</i>. Each box on the left is a group: the five general-fund classes '
      f'stand for <b>{n_rev} revenue accounts</b> that carry money, and 113 more that '
      f'carry none. On the right, ten departments are named and <b>{len(d["depts"])-10} '
      f'are collapsed into one box</b>. Inside each department are the 635 accounts the '
      f'ledger actually holds.</p>'
      f'<p>So the honest claim is: <b>every dollar the town’s ledger records is on this '
      f'page somewhere</b>, at the grain a page can hold. What it is <i>not</i> is a list '
      f'you could audit a cheque against.</p>'
      f'<p class="warn"><b>And eight things are not on it at all, because the town’s '
      f'records cannot answer them.</b> They are drawn at the foot of each column, at the '
      f'same size as everything else, so the picture does not read as complete when it is '
      f'not. Four are money coming in that cannot be seen; four are spending that cannot '
      f'be split. Every one of them is a real quantity — none is a rounding difference or '
      f'a missing file.</p>'
      f'<p class="cap">The largest single unknown is the school share of the pension. The '
      f'largest lumped one is debt service: two accounts for all town borrowing, with '
      f'school buildings inside and no way to separate them.</p></section>')

    a(f'<section class="stage"><h2>Every dollar of special revenue in this town is school '
      f'money</h2>'
      f'<p>The single box marked “Special revenue funds — {money(d["sr_in"])}” on the left '
      f'is not a town-wide category with a school share inside it. <b>It is entirely '
      f'school money.</b> Twelve funds carry revenue in FY2026 — school lunch, the special '
      f'education circuit breaker, extended day, Chapter 658 athletics, after school, '
      f'school choice, family and community engagement, the school gift fund, facilities '
      f'use, comprehensive school health, adult education, and lost books — and no other '
      f'town department runs one at all.</p>'
      f'<p class="cap">Which is why the school page itemises these and this page does not: '
      f'same money, finer grain, and the school page is where the grain belongs. The one '
      f'thing this page does <b>not</b> carry that the school page does is the '
      f'grant funds’ spending — nine funds that spent '
      f'money in FY2026 while booking no revenue, so a revenue-side box cannot show them. '
      f'They appear here only in the gaps.</p></section>')

    a(f'<section class="stage"><h2>What is inside the special revenue box, itemised</h2>'
      f'<p class="cap">The diagram carries these as one box on each side because there are '
      f'{len(d["srspend"])} of them and a box each would swamp the picture. <b>Nothing is '
      f'excluded from the totals</b> — every fund below is inside the '
      f'{money(d["sr_out"])}, and each of these is school money.</p>'
      f'<table><tr><th>fund</th><th></th><th class="v">in</th><th class="v">spent</th>'
      f'<th class="v">held 31 Mar</th></tr>')
    for r in d['srspend']:
        a(f'<tr><td><code>{r["fund"]}</code></td><td>{r["name"].title()}</td>'
          f'<td class="v">{money(r["revenue"] or 0)}</td>'
          f'<td class="v">{money(r["spent"] or 0)}</td>'
          f'<td class="v">{money(r["closing_balance"] or 0)}</td></tr>')
    a(f'<tr><td></td><td><b>total</b></td><td class="v"><b>{money(d["sr_in"])}</b></td>'
      f'<td class="v"><b>{money(d["sr_out"])}</b></td>'
      f'<td class="v"><b>{money(d["sr_held"])}</b></td></tr></table>'
      f'<p class="cap">School choice, for example, took in $83,116, spent $30,558 and '
      f'holds $299,461 — all three inside the single box on the diagram.</p></section>')

    a('<section class="stage"><h2>The town runs four money systems that do not mix</h2>'
      '<p class="cap">This is the thing the school view cannot show, because the schools '
      'live in only two of them.</p>'
      '<table><tr><th>system</th><th class="v">in</th><th class="v">out</th>'
      '<th>can a dollar be followed?</th></tr>'
      f'<tr><td><b>General fund</b><span class="sub">67 departments, one pot</span></td>'
      f'<td class="v">{money(d["rev_total"])}</td><td class="v">{money(d["omnibus"])}</td>'
      f'<td><b>No.</b> Every source lands in fund 0100 and loses its identity. This is '
      f'{d["rev_total"]/town_in*100:.0f}% of the money and the only system with this '
      f'problem</td></tr>'
      f'<tr><td><b>Enterprise funds</b><span class="sub">sewer, water, PEG, solid '
      f'waste</span></td><td class="v">{money(ent_in_total)}</td>'
      f'<td class="v">{money(ent_out_total)}</td>'
      f'<td><b>Yes.</b> Rate-funded and self-contained: the people who pay are the people '
      f'served, and the accounts are separate end to end</td></tr>'
      f'<tr><td><b>Special revenue funds</b><span class="sub">61 of them, and <b>every '
      f'one that carries money is a school fund</b></span></td>'
      f'<td class="v">{money(d["sr_in"])}</td>'
      f'<td class="v">{money(d["sr_out"])}</td>'
      f'<td><b>Half.</b> The source is known exactly, the use is not observed at all — no '
      f'expense report exists for them</td></tr>'
      f'<tr><td><b>Trust funds</b><span class="sub">scholarships, cemetery, '
      f'stabilisation</span></td><td class="v">—</td><td class="v">—</td>'
      f'<td><b>Not held.</b> The annual-report extract is <code>check failed</code> on '
      f'ordinal columns and cannot be aggregated</td></tr></table>'
      '<p class="warn"><b>The asymmetry is the finding.</b> The system nobody argues about '
      '— the enterprise funds — is fully traceable, because it is rate-funded and '
      'ring-fenced. The system every Town Meeting argues about is the one where no dollar '
      'can be followed from where it came from to what it bought. That is not an accident '
      'of record-keeping; it is what a general fund IS.</p></section>')

    a('<div class="cols"><div class="col"><h2>Money in</h2>'
      '<div class="colnote">Who sets each dollar. The general fund, by class.</div>')
    order = ['levy', 'state', 'local', 'onetime', 'transfer']
    lbl = {k: REV[k][1] for k in REV}
    lbl['local'] = 'Local receipts'
    note = {k: REV[k][2] for k in REV}
    note['local'] = 'Fees, permits, excise, fines. A residual'
    a(bars([(lbl[k], d['revclass'].get(k, 0), 'hi' if k == 'state' else '', note[k])
            for k in order if d['revclass'].get(k)]))
    a('<h3>Outside the general fund</h3>')
    a(bars([(nm.title(), v, 'alt', f'fund {f}') for f, nm, v in d['ent_in']]
           + [('Special revenue funds', d['sr_in'], 'alt',
               f'61 funds · holding {money(d["sr_held"])} at 31 March')]))
    a('</div>')

    a('<div class="col"><h2>Money out</h2>'
      '<div class="colnote">Where it actually lands. The omnibus budget, by '
      'department.</div>')
    a(bars([(r['name'].title(), r['v'], 'hi' if r['dept'] in ('300', '310') else '',
             f'dept {r["dept"]} · {r["v"]/d["omnibus"]*100:.1f}% of the omnibus')
            for r in d['depts'][:12]]
           + [(f'The other {len(d["depts"])-12} departments',
               sum(r['v'] for r in d['depts'][12:]), '',
               'every one under ' + money(d['depts'][12]['v']))]))
    a('<h3>Outside the general fund</h3>')
    a(bars([(nm.title(), d['ent_out'].get(f, 0), 'alt', f'fund {f}')
            for f, nm, v in d['ent_in'] if d['ent_out'].get(f)]
           + [('Special revenue funds', d['sr_out'], 'alt',
               f'spent {money(d["sr_out"])} against {money(d["sr_in"])} received')]))
    a('</div></div>')

    a(f'<p class="warn"><b>The two columns do not balance, and should not.</b> Money in is '
      f'{money(town_in)} and money out is {money(town_out)}. A fund is a tank, not a pipe: '
      f'the special revenue funds alone spent {money(d["sr_out"] - d["sr_in"])} more than '
      f'they took in, drawing down balances built in earlier years. And the bases are '
      f'mixed — the general fund and enterprise figures are budgets as voted, the special '
      f'revenue funds are nine months of actual, because the town publishes no '
      f'twelve-month fund report.</p>')

    a('<section class="stage"><h2>What the town view shows that the school view cannot</h2>'
      '<ul>'
      f'<li><b>Scale.</b> The school department is {sum(r["v"] for r in d["byclass"]["delegated"])/d["omnibus"]*100:.0f}% '
      f'of the omnibus budget once the library is counted with it — more than everything '
      f'else the town does, combined.</li>'
      '<li><b>The enterprise funds are the control case.</b> Rate-funded, ring-fenced, '
      'traceable. They prove the tracing problem is a property of the general fund rather '
      'than of the town’s record-keeping.</li>'
      '<li><b>Two revenue lines are 83% of everything.</b> Property tax and Chapter 70. '
      'The other 190 accounts share the rest, and 113 of them carry nothing.</li>'
      '<li><b>The same gaps recur outside the schools.</b> Debt service is two lumped '
      'accounts for all town borrowing; capital is two transfer lines with no project '
      'detail; the pension covers everybody with no split. These are not school problems, '
      'they are how the town books things.</li>'
      '</ul></section>')

    a('<section class="stage"><h2>The schools, in the same model</h2>'
      '<p class="cap">Reproduced from <code>money-flow-v2.html</code> unchanged, so the '
      'two can be read against each other. The school system is one of the four above and '
      'lives in two of them: the general fund appropriation, and the special revenue '
      'funds it runs itself.</p>'
      f'<p><a href="money-flow-v2.html">Open the school diagram →</a></p></section>')
    return PAGE.format(body='\n'.join(P))


PAGE = '''<meta charset="utf-8">
<title>The whole town — every dollar in, every dollar out — Lunenburg FY2026</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ --bg:#fbfaf8; --card:#fff; --ink:#191919; --muted:#6b6b6b; --grid:#e2ded7;
  --traced:#1f5c3d; --hi:#9a4f14; --warn:#8a6d10; --warn-bg:#faf3de; --ent:#1c4f7a; --traced-bg2:#e7f0ea;
  --potbg:#2c2b28; --potink:#f2efe9; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#141412; --card:#1c1b19; --ink:#eeebe6; --muted:#a09b93; --grid:#34322e;
    --traced:#79c39f; --hi:#e2a068; --warn:#d9bd67; --warn-bg:#2c2718; --ent:#7fb4dd; --traced-bg2:#1b2b22;
    --potbg:#e8e4dc; --potink:#1a1a18; }}
}}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  -webkit-text-size-adjust:100% }}
.wrap {{ max-width:1100px; margin:0 auto; padding:22px 16px 80px }}
header {{ border-bottom:2px solid var(--ink); padding-bottom:14px }}
.kicker {{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted) }}
h1 {{ font-size:28px; line-height:1.15; margin:8px 0; letter-spacing:-.02em }}
.standfirst {{ font-size:16px; color:var(--muted); margin:0 }}
.metrics {{ display:grid; gap:10px; margin:16px 0 }}
.m {{ border:1px solid var(--grid); border-radius:9px; padding:12px 13px; background:var(--card) }}
.m.hi {{ border-color:var(--hi); border-width:2px }}
.mk {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase; font-weight:700;
  color:var(--muted) }}
.mv {{ font-size:24px; font-weight:700; letter-spacing:-.02em; margin:2px 0 3px;
  font-family:ui-monospace,Menlo,monospace }}
.ms {{ font-size:12.5px; color:var(--muted); line-height:1.45 }}
.stage {{ background:var(--card); border:1px solid var(--grid); border-radius:10px;
  padding:16px 15px; margin:16px 0 }}
h2 {{ font-size:18px; margin:0 0 6px }}
h3 {{ font-size:12px; letter-spacing:.09em; text-transform:uppercase; color:var(--muted);
  margin:18px 0 8px }}
.cap {{ font-size:13.5px; color:var(--muted); margin:0 0 14px }}
.cols {{ display:grid; gap:16px; margin:16px 0 }}
.col {{ background:var(--card); border:1px solid var(--grid); border-radius:10px;
  padding:15px 14px; min-width:0 }}
.colnote {{ font-size:12.5px; color:var(--muted); margin:2px 0 12px }}
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
.scroll {{ overflow-x:auto; border:1px solid var(--grid); border-radius:10px;
  background:var(--card); padding:10px; margin:14px 0 6px }}
svg.flow {{ display:block; min-width:950px; height:auto }}
.dhd {{ font-size:11px; font-weight:700; letter-spacing:.11em; fill:var(--muted) }}
.b rect {{ fill:var(--card); stroke:var(--grid); stroke-width:1.5 }}
.b.gf rect {{ fill:var(--traced-bg2); stroke:var(--traced) }}
.b.ent rect {{ fill:none; stroke:var(--ent); stroke-width:2 }}
.b.sr rect {{ fill:none; stroke:var(--warn); stroke-width:2; stroke-dasharray:6 4 }}
.b.gap rect {{ fill:var(--warn-bg); stroke:var(--warn); stroke-width:1.5;
  stroke-dasharray:3 3 }}
.gl {{ fill:var(--warn) }}
.dhd.gap {{ fill:var(--warn) }}
.b.pot rect {{ fill:var(--potbg); stroke:var(--potbg) }}
.bl {{ font-size:13px; font-weight:600; fill:var(--ink) }}
.bv {{ font-size:13px; fill:var(--ink); font-family:ui-monospace,Menlo,monospace }}
.bs {{ font-size:10px; fill:var(--muted) }}
.pw {{ fill:var(--potink) }}
.potnote {{ font-size:10.5px; fill:var(--potink); opacity:.75 }}
.e {{ fill:none; stroke-width:2 }}
.e.traced {{ stroke:var(--traced); opacity:.45 }}
.e.bypass {{ stroke:var(--ent); opacity:.75; stroke-width:2.5 }}
.e.restricted {{ stroke:var(--warn); opacity:.8; stroke-dasharray:7 5 }}
.key {{ display:flex; flex-wrap:wrap; gap:8px 18px; font-size:12px; color:var(--muted);
  margin-bottom:10px }}
.key span {{ display:flex; align-items:center; gap:6px }}
.k {{ width:24px; height:0; border-top:2px solid; display:inline-block }}
.k.traced {{ border-color:var(--traced) }}
.k.bypass {{ border-color:var(--ent); border-top-width:3px }}
.k.restricted {{ border-top-style:dashed; border-color:var(--warn) }}
.warn {{ background:var(--warn-bg); border-left:3px solid var(--warn);
  border-radius:0 6px 6px 0; padding:11px 13px; font-size:14px; margin:14px 0 }}
table {{ border-collapse:collapse; width:100%; font-size:13.5px; margin-top:6px }}
th,td {{ text-align:left; padding:8px 8px 8px 0; border-bottom:1px solid var(--grid);
  vertical-align:top }}
td.v {{ text-align:right; white-space:nowrap; font-family:ui-monospace,Menlo,monospace }}
td .sub {{ display:block; font-size:11.5px; color:var(--muted); font-weight:400 }}
code {{ font-family:ui-monospace,Menlo,monospace; font-size:12.5px }}
ul {{ font-size:14px; padding-left:20px }} li {{ margin:7px 0 }}
a {{ color:var(--hi) }}
.gen {{ margin-top:30px; font-size:12px; color:var(--muted) }}
@media (min-width:760px) {{ .metrics {{ grid-template-columns:repeat(2,1fr) }} }}
@media (min-width:1000px) {{
  .metrics {{ grid-template-columns:repeat(4,1fr) }}
  .cols {{ grid-template-columns:1fr 1fr }}
  .row {{ grid-template-columns:44% 1fr 24%; grid-template-areas:"lab bar amt"; gap:10px;
    align-items:center }}
}}
</style>

<div class="wrap">
<header>
  <div class="kicker">Lunenburg Budget Project &middot; Data architecture</div>
  <h1>The whole town — every dollar in, every dollar out</h1>
  <p class="standfirst">FY2026. The same model built for the schools, applied to all of
  Lunenburg: who sets each dollar coming in, who decides how it goes out, and what is
  sitting still.</p>
</header>

{body}

<p class="gen">Generated by <code>scripts/build_town_flow.py</code> from
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
                             f'  Run: python3 scripts/build_town_flow.py')
        print(f'ok: {rel} still reproduces')
        return
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print(f'wrote {rel} ({len(fresh):,} bytes)')


if __name__ == '__main__':
    main()
