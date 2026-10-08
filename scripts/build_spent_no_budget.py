#!/usr/bin/env python3
"""Spent with no budget -- report 12 of notes/REPORTS-TO-GENERATE.md.

    python3 scripts/build_spent_no_budget.py           # write the .md, the payload, the charts
    python3 scripts/build_spent_no_budget.py --check   # fail if any of them is stale

THE QUESTION. Which school budget lines spent money against a $0 appropriation, how much, and
does it recur? The worked case the report list names: kindergarten aides and
paraprofessionals, FY2026.

THE DATA. `munis-school-ytd.csv`, report `gf-school` (fund 0100, department 300), period 13
-- the closed year -- FY2023 to FY2026. One row per MUNIS account per year; the report prints
every account every year, zeros included, so a line voted at $0 is a row, not an absence.

THREE DEFINITIONS, NEVER MERGED. They answer different questions and overlap, so no figure
here is a sum across them:

  (a) ORIGINAL appropriation $0 and spent > 0 -- the line as voted did not describe what
      was spent on it;
  (b) REVISED budget $0 and spent > 0 -- still no budget on the line after every mid-year
      transfer, so the whole amount was covered by money left on other lines;
  (c) ORIGINAL $0 and REVISED > 0 -- a line that started at $0 and had money moved onto it
      during the year: the pattern that shows the money was found.

SPECIAL FUNDS ARE OUT OF SCOPE, AND THE REASON IS LAW, NOT CONVENIENCE. Revolving funds,
grants, the circuit breaker and gifts spend WITHOUT APPROPRIATION by statute -- their
authority is the fund, not a Town Meeting vote -- so a $0 budget on one of their lines is
the normal state and says nothing. The scale of that is measured and printed, so the
exclusion is visible rather than silent.

WHAT THE LEDGER CANNOT SAY. It gives one spent figure per line per year: not who or what was
paid, not which line a transfer came from. Both are registered gaps (rule 7c). A budget line
is not a position (rule 11): a line titled kindergarten aides is a place the books put money.

Nothing here explains WHY a line was voted at $0. Every reason offered is a hypothesis, and
the data cannot tell them apart (rule 7).
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conclusions import conclusion, emit, figure, usd, pct  # noqa: E402
import build_sitting_on_money as SOM  # noqa: E402  -- source(), manifest(), svg helpers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
ID = 'spent-with-no-budget'
MD = os.path.join(ROOT, 'sources', 'analyses', ID + '.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', ID + '.json')
CHARTS = os.path.join(ROOT, 'sources', 'analyses', 'charts')
CHART_NAMES = ('years', 'lines', 'kindergarten')
MUNIS = os.path.join(DATA, 'munis-school-ytd.csv')
GAPS = os.path.join(DATA, 'money-gaps.csv')
SWCI = os.path.join(ROOT, 'fy28', 'public', 'data', 'spending-what-comes-in.json')
SURPLUS = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy26-school-surplus.json')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
YEARS = (2023, 2024, 2025, 2026)
ZERO = 0.005
# Years and the zero itself are not derived figures; declared to the rule-2 check as literals.
LITERALS = ('FY2023 to FY2026', 'FY2023', 'FY2024', 'FY2025', 'FY2026', 'January 2026',
            'September 2025', '$0')

KG = ('0100-3-300-2330-03-2-12-1-511103', '0100-3-300-2330-03-2-13-1-511203')
KG_ORG = {'0100-3-300-2330-03-2-12-1-511103': 'S2032121',
          '0100-3-300-2330-03-2-13-1-511203': 'S2032131'}


def fail(msg):
    raise SystemExit('build_spent_no_budget: REFUSING TO WRITE -- ' + msg)


money = SOM.money
usdk = SOM.usdk

# ======================================================================================
# PLAIN NAMES. Ours, read off MUNIS's descriptions and the DESE function code in the account
# string (segment 4). A line that enters any definition and has no plain name here stops the
# build, so a new year cannot publish a MUNIS abbreviation as a resident's label.
# ======================================================================================
PLAIN = {
    '0100-3-300-1230-99-0-99-1-519103': 'School stipends (district-wide)',
    '0100-3-300-2210-01-4-08-1-511102': 'Elementary clerk-typist',
    '0100-3-300-2210-06-6-08-1-511019': 'High school accreditation salaries',
    '0100-3-300-2305-05-5-54-1-517005': 'Middle school master-teacher stipends',
    '0100-3-300-2325-51-4-71-1-511003': 'Elementary special education long-term substitutes',
    '0100-3-300-2325-51-6-71-1-511003': 'High school special education long-term substitutes',
    '0100-3-300-2330-03-2-12-1-511103': 'Kindergarten aides',
    '0100-3-300-2330-03-2-13-1-511203': 'Kindergarten paraprofessionals',
    '0100-3-300-2330-06-6-13-1-511203': 'High school paraprofessionals',
    '0100-3-300-2415-51-4-05-2-555055': 'Elementary special education teaching materials',
    '0100-3-300-2420-04-4-62-2-555005': 'Elementary physical education supplies',
    '0100-3-300-2420-06-6-63-2-555028': 'High school marching band',
    '0100-3-300-2451-99-1-52-2-535006': 'District technology, contracted services',
    '0100-3-300-2710-06-6-65-1-511002': 'High school guidance secretary',
    '0100-3-300-2800-07-2-06-1-511023': 'School psychologists',
    '0100-3-300-3200-99-1-56-2-531006': 'Health services, purchased (district-wide)',
    '0100-3-300-3510-06-6-67-1-519003': 'Athletic coaches',
    '0100-3-300-3510-06-6-67-2-535020': 'Athletics dues and fees',
    '0100-3-300-3510-06-6-67-2-535021': 'Athletic officials',
    '0100-3-300-3520-06-6-70-1-519003': 'High school after-school advisors',
}

# ======================================================================================
# WHAT WAS SAID. Each quote is checked verbatim against the minutes text on every build.
# ======================================================================================
QUOTES = [
    dict(file='finance-committee/2026-01-12-minutes-7597.txt', date='12 January 2026',
         body='Finance Committee',
         who='the minutes, recording the School Committee chair during the FY2027 budget discussion',
         text='the school department had already been significantly cut and could not sustain '
              'further reductions without affecting classroom performance, noting that '
              'kindergarten classrooms were operating with 25 students and no aides',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_01122026-7597'),
    dict(file='finance-committee/2026-02-26-minutes-7673.txt', date='26 February 2026',
         body='Finance Committee',
         who='the minutes, listing the schools’ FY2027 staffing increase requests',
         text='1 Kindergarten Paraprofessional: $22,205',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_02262026-7673'),
    dict(file='school-committee/2025-09-03-minutes-7385.txt', date='3 September 2025',
         body='School Committee',
         who='the minutes, approving the FY2025 line item transfers',
         text='$4900 out of business manager salary account to the stipends account',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_09032025-7385'),
    dict(file='school-committee/2025-09-03-minutes-7385.txt', date='3 September 2025',
         body='School Committee',
         who='the same minutes, same item',
         text='a discussion of transfer accounts regarding a double budget amount for '
              'paraprofessionals in the amount of $243,000',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_09032025-7385'),
]


def check_quotes():
    for q in QUOTES:
        p = os.path.join(MINUTES, q['file'])
        if not os.path.exists(p):
            fail('%s is not on disk -- run sync_archive.py --pull' % q['file'])
        if SOM.flat(q['text']) not in SOM.flat(open(p, encoding='utf-8').read()):
            fail('quote not verbatim in %s: %r' % (q['file'], q['text'][:60]))


# Gaps this report cites. The first two are its own; the last two were registered by other
# reports and this one hits the same wall.
GAP_WHATS = [
    'What was paid from the school budget lines that spent against a $0 budget, FY2023–FY2026',
    'Whether the FY2026 spending on the kindergarten aide lines paid for aides in kindergarten classrooms',
    "Where did the $122,502.44 that moved out of the FY2025 school department mid-year go, and what "
    "posted to department 300 after the School Committee's 17 September 2025 surplus statement?",
    'Whether a budgeted position was filled',
]


def check_gaps():
    have = {r['what'].strip() for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
    missing = [w for w in GAP_WHATS if w not in have]
    if missing:
        fail('these gaps are cited and not in money-gaps.csv: %s' % missing)


# ======================================================================================
# 1. THE LEDGER
# ======================================================================================

def read():
    rows, special = {}, defaultdict(lambda: [0, 0, 0.0, 0.0])
    desc = {}
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['period'] != '13':
            continue
        y = int(r['fiscal_year'])
        if y not in YEARS:
            fail('year %d outside %s' % (y, YEARS))
        if r['report'] == 'special-school':
            if r['type'] != 'E':
                continue
            s = money(r['ytd_expended'])
            if s > ZERO:
                t = special[y]
                t[0] += 1
                t[2] += s
                if abs(money(r['revised_budget'])) < ZERO:
                    t[1] += 1
                    t[3] += s
            continue
        if r['report'] != 'gf-school':
            continue
        if r['fund'] != '0100' or r['type'] != 'E':
            fail('a gf-school row outside fund 0100 / type E: %s' % r['account'])
        k = (y, r['account'])
        if k in rows:
            fail('account %s appears twice in FY%d' % (r['account'], y))
        rows[k] = dict(orig=money(r['original_approp']), trans=money(r['transfers_adjustments']),
                       rev=money(r['revised_budget']), spent=money(r['ytd_expended']),
                       enc=money(r['encumbrances']), avail=money(r['available_budget']),
                       org=r['org'], desc=r['description'].strip())
        desc[r['account']] = r['description'].strip()
    accts = sorted({a for _y, a in rows})
    for y in YEARS:
        n = sum(1 for (yy, _a) in rows if yy == y)
        if n != len(accts):
            fail('FY%d carries %d accounts, the four-year set is %d -- the report no longer '
                 'prints every account every year' % (y, n, len(accts)))
    return rows, accts, desc, special


def classify(r):
    z = lambda v: abs(v) < ZERO  # noqa: E731
    out = []
    if z(r['orig']) and r['spent'] > ZERO:
        out.append('a')
    if z(r['rev']) and r['spent'] > ZERO:
        out.append('b')
    if z(r['orig']) and r['rev'] > ZERO:
        out.append('c')
    return out


# ======================================================================================
# CHARTS FOR /docs AND THE PDF (the web page draws components; rule 7f)
# ======================================================================================
INK, MUTED, GRID = SOM.INK, SOM.MUTED, SOM.GRID
C_A, C_B, C_C = '#dc2626', '#7f1d1d', '#2b6cb0'
DEF_COLOR = {'a': C_A, 'b': C_B, 'c': C_C}


def years_svg(by_year):
    W, H, L, B, T = 860, 360, 70, 280, 56
    top = max(max(y['a_spent'], y['b_spent'], y['c_moved']) for y in by_year)
    sc = (B - T) / top
    gw = (W - L - 20) / len(by_year)
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Spending on school lines '
         'voted at $0, by year, three definitions (never added together)</text>' % INK,
         '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (L, B, W - 20, B, GRID)]
    for i, y in enumerate(by_year):
        x0 = L + i * gw + 18
        bw = (gw - 50) / 3
        for j, (key, c) in enumerate((('a_spent', C_A), ('b_spent', C_B), ('c_moved', C_C))):
            h = y[key] * sc
            x = x0 + j * (bw + 4)
            b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (x, B - h, bw, h, c))
            b.append('<text x="%.1f" y="%.1f" font-size="9.5" text-anchor="middle" fill="%s">%s</text>'
                     % (x + bw / 2, B - h - 4, INK, usdk(y[key])))
        b.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">FY%d</text>'
                 % (x0 + (3 * bw + 8) / 2, B + 16, MUTED, y['fy']))
    lg = [('(a) spent; the line was voted at $0', C_A), ('(b) spent; still $0 after transfers', C_B),
          ('(c) moved onto a line voted at $0', C_C)]
    for i, (t, c) in enumerate(lg):
        x = L + i * 255
        b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/><text x="%d" y="%d" '
                 'font-size="11" fill="%s">%s</text>' % (x, H - 30, c, x + 14, H - 21, INK, SOM.esc(t)))
    return SOM.svg_wrap(W, H, 'Spending on school lines voted at $0, by year', b)


def lines_svg(lines):
    rows = [ln for ln in lines if ln['a_total'] > ZERO]
    W, rh, lab = 900, 24, 340
    H = 70 + rh * len(rows) + 20
    top = max(ln['a_total'] for ln in rows)
    cols = {2023: '#fca5a5', 2024: '#f87171', 2025: '#dc2626', 2026: '#7f1d1d'}
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Each line that spent '
         'against a $0 vote, four-year total, by year</text>' % INK]
    for i, y in enumerate(YEARS):
        b.append('<rect x="%d" y="38" width="10" height="10" fill="%s"/><text x="%d" y="47" '
                 'font-size="11" fill="%s">FY%d</text>' % (lab + i * 80, cols[y], lab + i * 80 + 14, INK, y))
    for i, ln in enumerate(rows):
        yy = 62 + i * rh
        b.append('<text x="16" y="%d" font-size="11" fill="%s">%s</text>' % (yy + 14, INK, SOM.esc(ln['name'])))
        x = lab
        for y in ln['years']:
            if 'a' in y['defs']:
                w = y['spent'] / top * (W - lab - 90)
                b.append('<rect x="%.1f" y="%d" width="%.1f" height="16" fill="%s"/>' % (x, yy + 2, w, cols[y['fy']]))
                x += w
        b.append('<text x="%.1f" y="%d" font-size="10.5" fill="%s">%s</text>' % (x + 4, yy + 14, MUTED, usdk(ln['a_total'])))
    return SOM.svg_wrap(W, H, 'Each line that spent against a $0 vote', b)


def kg_svg(kg):
    W, H, L, B, T = 760, 320, 70, 240, 50
    top = max(max(y['voted'], y['spent']) for y in kg['years'])
    sc = (B - T) / top
    gw = (W - L - 20) / len(kg['years'])
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">The two kindergarten aide '
         'lines together: voted against spent</text>' % INK,
         '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (L, B, W - 20, B, GRID)]
    for i, y in enumerate(kg['years']):
        x0 = L + i * gw + 24
        bw = (gw - 60) / 2
        for j, (key, c) in enumerate((('voted', '#94a3b8'), ('spent', C_A))):
            h = y[key] * sc
            x = x0 + j * (bw + 4)
            b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (x, B - h, bw, h, c))
            b.append('<text x="%.1f" y="%.1f" font-size="10" text-anchor="middle" fill="%s">%s</text>'
                     % (x + bw / 2, B - h - 4, INK, usdk(y[key])))
        b.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">FY%d</text>'
                 % (x0 + bw + 2, B + 16, MUTED, y['fy']))
    b.append('<rect x="%d" y="%d" width="10" height="10" fill="#94a3b8"/><text x="%d" y="%d" '
             'font-size="11" fill="%s">voted (original appropriation)</text>' % (L, H - 40, L + 14, H - 31, INK))
    b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/><text x="%d" y="%d" '
             'font-size="11" fill="%s">spent at the close</text>' % (L + 260, H - 40, C_A, L + 274, H - 31, INK))
    return SOM.svg_wrap(W, H, 'Kindergarten aide lines, voted against spent', b)


# ======================================================================================
# THE REPORT
# ======================================================================================

def build():
    check_quotes()
    check_gaps()
    rows, accts, desc, special = read()

    # ---- by year, each definition ----------------------------------------------------
    by_year, dept = [], {}
    for y in YEARS:
        ry = {a: rows[(y, a)] for a in accts}
        A = [a for a in accts if 'a' in classify(ry[a])]
        B = [a for a in accts if 'b' in classify(ry[a])]
        C = [a for a in accts if 'c' in classify(ry[a])]
        tot_rev = sum(r['rev'] for r in ry.values())
        tot_spent = sum(r['spent'] for r in ry.values())
        tot_enc = sum(r['enc'] for r in ry.values())
        tot_avail = sum(r['avail'] for r in ry.values())
        if abs(tot_rev - tot_spent - tot_enc - tot_avail) > 1:
            fail('FY%d: revised - spent - encumbered does not equal available' % y)
        dept[y] = dict(revised=round(tot_rev, 2), spent=round(tot_spent, 2),
                       encumbered=round(tot_enc, 2), available=round(tot_avail, 2))
        if not set(B) <= set(A):
            fail('FY%d: a (b) line is not an (a) line -- the text says every one is' % y)
        a_sp = sum(ry[a]['spent'] for a in A)
        by_year.append(dict(
            fy=y,
            a_n=len(A), a_spent=round(a_sp, 2),
            a_over=round(sum(ry[a]['spent'] - ry[a]['rev'] for a in A), 2),
            b_n=len(B), b_spent=round(sum(ry[a]['spent'] for a in B), 2),
            c_n=len(C), c_also_a=len(set(C) & set(A)), c_moved=round(sum(ry[a]['rev'] for a in C), 2),
            c_spent=round(sum(ry[a]['spent'] for a in C), 2),
            enc_on_lines=round(sum(ry[a]['enc'] for a in set(A) | set(B) | set(C)), 2),
            share_pct=round(a_sp / tot_spent * 100, 2),
            dept_spent=round(tot_spent, 2), dept_available=round(tot_avail, 2),
        ))
    a_tot = sum(y['a_spent'] for y in by_year)
    b_tot = sum(y['b_spent'] for y in by_year)
    c_tot = sum(y['c_moved'] for y in by_year)
    max_share = max(y['share_pct'] for y in by_year)
    c_n_all = sum(y['c_n'] for y in by_year)
    c_a_all = sum(y['c_also_a'] for y in by_year)
    under_every_year = all(dept[y]['available'] > 0 for y in YEARS)
    if not under_every_year:
        fail('a year closed over its revised total -- the "covered inside the total" sentence '
             'no longer holds; rewrite it before building')

    # ---- line by line ----------------------------------------------------------------
    lines = []
    for a in accts:
        ys = []
        for y in YEARS:
            r = rows[(y, a)]
            ys.append(dict(fy=y, orig=r['orig'], trans=r['trans'], rev=r['rev'], spent=r['spent'],
                           enc=r['enc'], defs=classify(r)))
        if not any(y['defs'] for y in ys):
            continue
        if a not in PLAIN:
            fail('%s (%s) enters a definition and has no plain name in PLAIN' % (a, desc[a]))
        a_years = [y['fy'] for y in ys if 'a' in y['defs']]
        lines.append(dict(
            account=a, org=rows[(YEARS[0], a)]['org'], munis=desc[a], name=PLAIN[a],
            function=a.split('-')[3], years=ys,
            a_total=round(sum(y['spent'] for y in ys if 'a' in y['defs']), 2),
            b_total=round(sum(y['spent'] for y in ys if 'b' in y['defs']), 2),
            c_total=round(sum(y['rev'] for y in ys if 'c' in y['defs']), 2),
            a_years=a_years,
            voted_other_year=any(y['orig'] > ZERO for y in ys if y['fy'] not in a_years),
        ))
    lines.sort(key=lambda ln: (-ln['a_total'], -ln['c_total'], ln['account']))
    unused = set(PLAIN) - {ln['account'] for ln in lines}
    if unused:
        fail('PLAIN names lines that enter no definition: %s' % sorted(unused))

    a_lines = [ln for ln in lines if ln['a_years']]
    top_line = a_lines[0]
    top_inst = max(((ln, y) for ln in a_lines for y in ln['years'] if 'a' in y['defs']),
                   key=lambda t: t[1]['spent'])
    n_a_acc = len(a_lines)
    n_voted_other = sum(1 for ln in a_lines if ln['voted_other_year'])
    recurring = [ln for ln in a_lines if len(ln['a_years']) >= 2]
    recurring.sort(key=lambda ln: (-len(ln['a_years']), -ln['a_total']))
    # instances from FY2024 on, where the prior year is in the data: did the line spend then?
    inst_prior = [(ln, y) for ln in a_lines for y in ln['a_years'] if y > YEARS[0]]
    n_prior_spent = sum(1 for ln, y in inst_prior if rows[(y - 1, ln['account'])]['spent'] > ZERO)

    # ---- the worked case -------------------------------------------------------------
    kg_years = []
    for y in YEARS:
        kg_years.append(dict(fy=y, voted=round(sum(rows[(y, a)]['orig'] for a in KG), 2),
                             revised=round(sum(rows[(y, a)]['rev'] for a in KG), 2),
                             spent=round(sum(rows[(y, a)]['spent'] for a in KG), 2),
                             lines=[dict(account=a, org=rows[(y, a)]['org'], name=PLAIN[a],
                                         munis=desc[a], voted=rows[(y, a)]['orig'],
                                         revised=rows[(y, a)]['rev'], spent=rows[(y, a)]['spent'])
                                    for a in KG]))
    for a in KG:
        if rows[(YEARS[0], a)]['org'] != KG_ORG[a]:
            fail('%s is no longer org %s -- re-read the worked case' % (a, KG_ORG[a]))
    k26 = kg_years[-1]['spent']
    k25v = kg_years[-2]['voted']
    k26v = kg_years[-1]['voted']
    if abs(k26v) > ZERO:
        fail('the kindergarten lines are no longer voted at $0 in FY2026')
    k26_aides = rows[(2026, KG[0])]['spent']
    k26_paras = rows[(2026, KG[1])]['spent']
    if any(rows[(y, KG[0])]['spent'] > ZERO for y in YEARS[:-1]):
        fail('the kindergarten aides line spent before FY2026 -- the text says it did not')
    kg = dict(years=kg_years, fy2026_spent=k26, fy2025_voted=k25v)

    # ---- the FY26 surplus report's paraprofessional category, read, not typed --------
    sp = json.load(open(SURPLUS, encoding='utf-8'))
    sc = {c['id']: c for c in sp['conclusions']}.get('salary-lines-left-money-though-aides-ran-over')
    if not sc or 'paraprofessionals' not in sc['claim']:
        fail('fy26-school-surplus no longer carries its paraprofessional conclusion')
    para_over = sc['figures']['s_paras']['value']
    para_cat = {p['account']: p for p in sp.get('para_accounts', [])}
    if not all(a in para_cat for a in KG):
        fail('fy26-school-surplus does not count both kindergarten lines as paraprofessionals')

    # ---- athletics, read from spending-what-comes-in's PUBLISHED payload ---------------
    ath = {y['fy']: y for y in json.load(open(SWCI, encoding='utf-8'))['athletics']['years']}
    if not all(y in ath for y in YEARS):
        fail('spending-what-comes-in no longer carries athletics for every year')

    # ---- the special funds, measured so the exclusion is visible ----------------------
    special_rows = [dict(fy=y, lines_spending=special[y][0], at_zero=special[y][1],
                         spent=round(special[y][2], 2), spent_at_zero=round(special[y][3], 2))
                    for y in YEARS]
    sp_lines = sum(s['lines_spending'] for s in special_rows)
    sp_zero = sum(s['at_zero'] for s in special_rows)
    sp_share = sum(s['spent_at_zero'] for s in special_rows) / sum(s['spent'] for s in special_rows) * 100

    yr = {y['fy']: y for y in by_year}

    # =================================================================================
    # THE CONCLUSIONS
    # =================================================================================
    conc = []
    # (a)
    figs = {}
    figs['a_tot'] = figure(a_tot, usd(a_tot), 'spent on school lines voted at $0, four years')
    figs['share'] = figure(max_share, pct(max_share))
    parts = []
    for y in by_year:
        figs['a%d' % y['fy']] = figure(y['a_spent'], usd(y['a_spent']))
        figs['an%d' % y['fy']] = figure(y['a_n'], str(y['a_n']), 'budget lines')
        parts.append('FY%d %s on %s lines' % (y['fy'], usd(y['a_spent']), y['a_n']))
    conc.append(conclusion(
        id='spent-on-lines-voted-at-zero', bearing='sizes', kind='measured',
        claim='%s was spent on school budget lines voted at $0, FY2023 to FY2026.' % usd(a_tot),
        so_what='Never more than %s of a year’s school spending, and every year closed under '
                'its total budget.' % pct(max_share),
        detail='By year: %s. Spending against a zero line is not by itself improper: the '
               'department’s total stayed inside its budget in all four years, so the money was '
               'covered elsewhere in the total. What it shows is that the voted line-item budget '
               'did not describe what happened.' % '; '.join(parts),
        figures=figs, figure='a_tot',
        basis='`munis-school-ytd.csv`, report gf-school, period 13, FY2023-FY2026: every '
              'account with original_approp = 0 and ytd_expended > 0.',
        not_shown='What was paid from these lines, or why each was voted at zero. A line can be '
                  'voted at zero because the budget for the work sat on another line, because a '
                  'post was not expected to be filled, or by a coding change; the ledger cannot '
                  'tell these apart.',
        allow=LITERALS))
    # (b)
    figs = {'b_tot': figure(b_tot, usd(b_tot), 'spent on lines still at $0 after transfers')}
    parts = []
    for y in by_year:
        if y['b_n']:
            figs['b%d' % y['fy']] = figure(y['b_spent'], usd(y['b_spent']))
            figs['bn%d' % y['fy']] = figure(y['b_n'], str(y['b_n']), 'budget lines')
            parts.append('FY%d %s on %s lines' % (y['fy'], usd(y['b_spent']), y['b_n']))
        else:
            parts.append('none in FY%d' % y['fy'])
    conc.append(conclusion(
        id='still-zero-after-transfers', bearing='sizes', kind='measured',
        claim='%s went on lines that still had a $0 budget after every mid-year transfer.' % usd(b_tot),
        so_what='Those lines closed over budget by the full amount; money left on other lines '
                'covered it.',
        detail='By year: %s. This is the stricter definition and a subset of the spending '
               'counted above, not an addition to it.' % '; '.join(parts),
        figures=figs, figure='b_tot',
        basis='`munis-school-ytd.csv`, gf-school, period 13: revised_budget = 0 and '
              'ytd_expended > 0.',
        not_shown='Which lines the cover came from. The ledger shows each line’s own budget and '
                  'spending, never a pairing between an overspent line and an underspent one.',
        allow=LITERALS))
    # (c)
    figs = {'c_tot': figure(c_tot, usd(c_tot), 'moved onto lines voted at $0, four years')}
    parts = []
    for y in by_year:
        if y['c_n']:
            figs['c%d' % y['fy']] = figure(y['c_moved'], usd(y['c_moved']))
            figs['cn%d' % y['fy']] = figure(y['c_n'], str(y['c_n']), 'budget lines')
            parts.append('FY%d %s onto %s lines' % (y['fy'], usd(y['c_moved']), y['c_n']))
        else:
            parts.append('none in FY%d' % y['fy'])
    conc.append(conclusion(
        id='money-found-by-transfer', bearing='sizes', kind='measured',
        claim='%s was moved during the year onto lines that started the year at $0.' % usd(c_tot),
        so_what='Here the money was found mid-year; the budget as voted still did not show the '
                'spending.',
        detail='By year: %s. The School Committee approves line item transfers at its meetings; '
               'the ledger records each line’s net change, not the line it came from.'
               % '; '.join(parts),
        figures=figs, figure='c_tot',
        basis='`munis-school-ytd.csv`, gf-school, period 13: original_approp = 0 and '
              'revised_budget > 0. Transfers are the transfers_adjustments column, net per line.',
        not_shown='Where each transfer came from, and whether every net change is a School '
                  'Committee transfer rather than another adjustment. The ledger carries one '
                  'net figure per line.',
        allow=LITERALS))
    # persistence -- the lever
    figs = {'n_other': figure(n_voted_other, str(n_voted_other), 'budget lines'),
            'n_a': figure(n_a_acc, str(n_a_acc), 'budget lines'),
            'n_rec': figure(len(recurring), str(len(recurring)), 'budget lines'),
            'n_prior': figure(n_prior_spent, str(n_prior_spent), 'line-years'),
            'n_inst': figure(len(inst_prior), str(len(inst_prior)), 'line-years')}
    rec_txt = []
    for i, ln in enumerate(recurring):
        figs['r%d' % i] = figure(len(ln['a_years']), str(len(ln['a_years'])), 'years')
        rec_txt.append('%s (%s years)' % (ln['name'].lower(), len(ln['a_years'])))
    conc.append(conclusion(
        id='mostly-a-missing-year', bearing='lever', kind='measured',
        claim='%s of the %s lines that spent against a $0 vote had a voted budget in another year.'
              % (n_voted_other, n_a_acc),
        so_what='A line that spent last year and is voted at $0 this year can be asked about '
                'before the vote.',
        detail='Mostly a year missing from a line the district funds in other years, not a new '
               'kind of spending. Where the year before is in the data, %s of %s cases had '
               'spending on the same line the year before. %s lines did it in more than one year: %s.'
               % (n_prior_spent, len(inst_prior), len(recurring), '; '.join(rec_txt)),
        figures=figs, figure='n_other',
        basis='`munis-school-ytd.csv`, gf-school, period 13, each line followed across '
              'FY2023-FY2026.',
        not_shown='Whether the budget for those years was carried on a different line. Four '
                  'years is a short window: a line voted at zero in each of the four is '
                  'counted as never voted.',
        allow=LITERALS))
    # the worked case
    figs = {'k26': figure(k26, usd(k26), 'charged to the kindergarten aide lines, FY2026'),
            'k25v': figure(k25v, usd(k25v)),
            'kaid': figure(k26_aides, usd(k26_aides)),
            'kpar': figure(k26_paras, usd(k26_paras)),
            'pover': figure(para_over, usd(para_over))}
    conc.append(conclusion(
        id='kindergarten-aides-fy2026', bearing='sizes', kind='measured',
        claim='%s was charged to the two kindergarten aide lines in FY2026; both were voted at $0.'
              % usd(k26),
        so_what='The same two lines were voted %s the year before. Who was paid needs payroll '
                'detail.' % usd(k25v),
        detail='Kindergarten aides %s, kindergarten paraprofessionals %s. The FY2026 surplus '
               'report counts both among the paraprofessional lines, which together ran %s over '
               'budget. A January 2026 Finance Committee minute records the School Committee '
               'chair saying kindergarten classrooms had no aides; an account title is not a '
               'person in a classroom, and nothing published joins the two.'
               % (usd(k26_aides), usd(k26_paras), usd(para_over)),
        figures=figs, figure='k26',
        basis='`munis-school-ytd.csv`, gf-school, accounts %s (org S2032121) and %s (org '
              'S2032131), FY2023-FY2026; fy26-school-surplus.json for the category.' % KG,
        not_shown='Whether anyone paid from these lines worked in a kindergarten classroom. '
                  'Staff coded to the line while assigned elsewhere, a reclassification, or '
                  'posts moved between lines would all produce the same ledger.',
        see=[('fy26-school-surplus', 'Where the FY26 school surplus was left')],
        allow=LITERALS))
    conc = emit(ID, conc)

    # =================================================================================
    # THE MARKDOWN
    # =================================================================================
    b = []
    w = b.append
    w('# Spent with no budget: school lines voted at $0, FY2023 to FY2026')
    w('')
    w('**Which school budget lines spent money they were never voted, how much, and whether it '
      'happens every year.**')
    w('')
    w('---')
    w('')
    w('## The short version')
    w('')
    w('![Grouped bars for FY2023 to FY2026: spending on lines voted at $0 (definition a), '
      'spending on lines still at $0 after transfers (b), and money moved onto lines voted at $0 '
      '(c). The three are different questions and are never added.](charts/%s-years.svg)' % ID)
    w('')
    w('**%s was spent on school budget lines voted at $0**, FY2023 to FY2026: the general '
      'fund lines whose voted (original) appropriation was zero and which spent money anyway. '
      '**%s of it** went on lines that were still at $0 after every mid-year transfer. '
      'Separately, **%s was moved during the year onto lines that started at $0.** The three '
      'are different questions and are never added together.' % (usd(a_tot), usd(b_tot), usd(c_tot)))
    w('')
    w('**This is not by itself improper.** In all four years the school department’s total '
      'came in under its budget, so the spending was covered elsewhere in the total. It is '
      'never more than %s of a year’s school spending. What it shows is that **the voted '
      'line-item budget did not describe what happened** — and that is what a Finance Committee '
      'reading the line items is reading.' % pct(max_share))
    w('')
    w('**It is mostly a missing year, not new spending.** %s of the %s lines that spent against '
      'a $0 vote had a voted budget in another of the four years. The largest is **%s: %s '
      'against a $0 vote** over %s. **The worked case: %s charged to the two kindergarten aide '
      'lines in FY2026**, both voted at $0, after the same lines were voted %s in FY2025. In '
      'January 2026 a Finance Committee minute records the School Committee chair saying '
      'kindergarten classrooms had no aides; nothing published reconciles the two.'
      % (n_voted_other, n_a_acc, top_line['name'].lower(), usd(top_line['a_total']),
         ' and '.join('FY%d' % y for y in top_line['a_years']), usd(k26), usd(k25v)))
    w('')
    w('---')
    w('')
    w('## Three definitions, every year')
    w('')
    w('Three different questions, so three different columns, **never added together**: '
      '(a) the line was voted at $0 and spent; (b) the line was still at $0 after every '
      'transfer and spent; (c) the line was voted at $0 and money was moved onto it. Every '
      '(b) line in this period is also an (a) line; %s of the %s (c) cases also spent, and so '
      'are (a) lines too. The largest single case is %s in FY%d: %s.'
      % (c_a_all, c_n_all, top_inst[0]['name'].lower(), top_inst[1]['fy'], usd(top_inst[1]['spent'])))
    w('')
    w('| year | (a) lines | (a) spent | (b) lines | (b) spent | (c) lines | (c) moved on | '
      'department spent | (a) as share | department left unspent |')
    w('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for y in by_year:
        w('| FY%d | %d | %s | %d | %s | %d | %s | %s | %s | %s |'
          % (y['fy'], y['a_n'], usd(y['a_spent']), y['b_n'], usd(y['b_spent']), y['c_n'],
             usd(y['c_moved']), usd(y['dept_spent']), pct(y['share_pct'], 2),
             usd(y['dept_available'])))
    w('| **four years** | | **%s** | | **%s** | | **%s** | | | |' % (usd(a_tot), usd(b_tot), usd(c_tot)))
    w('')
    w('“Department left unspent” is the period-13 available balance across every line: '
      'revised budget, less spent, less still encumbered. It is positive in every year, which '
      'is what “covered elsewhere in the total” means here. No purchase orders were open at '
      'the close on any line counted above (encumbered: %s).'
      % usd(sum(y['enc_on_lines'] for y in by_year)))
    w('')
    w('## Line by line')
    w('')
    w('![One bar per line that spent against a $0 vote, longest first, split by year.](charts/%s-lines.svg)' % ID)
    w('')
    w('Every line that enters any of the three definitions in any year, ranked by what it spent '
      'against a $0 vote. Each cell is voted / revised / spent; the letters are the definitions '
      'the line meets that year. Names are ours, from MUNIS’s description and the DESE function '
      'code; the MUNIS description and account are in the last column.')
    w('')
    w('| line | ' + ' | '.join('FY%d' % y for y in YEARS) + ' | (a) four years | MUNIS |')
    w('|---|' + '---|' * len(YEARS) + '---:|---|')
    for ln in lines:
        cells = []
        for y in ln['years']:
            c = '%s / %s / %s' % (usdk(y['orig']), usdk(y['rev']), usdk(y['spent']))
            if y['defs']:
                c += ' **(%s)**' % ','.join(y['defs'])
            cells.append(c)
        w('| %s | %s | %s | %s `%s` |' % (ln['name'], ' | '.join(cells), usd(ln['a_total']),
                                         ln['munis'], ln['account']))
    w('')
    w('## Does it recur?')
    w('')
    w('**%s lines spent against a $0 vote in more than one of the four years:**' % len(recurring))
    w('')
    for ln in recurring:
        w('- **%s** — %s, %s in all.' % (ln['name'], ', '.join('FY%d' % y for y in ln['a_years']),
                                          usd(ln['a_total'])))
    w('')
    w('The rest did it once. Of the %s lines, **%s had a voted budget in another of the four '
      'years**. Where the year before is in the data, '
      '%s of %s cases had spending on the same line the year before: a line that was in use, '
      'then voted at zero.' % (n_a_acc, n_voted_other, n_prior_spent, len(inst_prior)))
    w('')
    coach = PLAIN['0100-3-300-3510-06-6-67-1-519003']
    if coach != top_line['name']:
        fail('athletic coaches is no longer the largest line -- rewrite the athletics note')
    cl = next(ln for ln in lines if ln['name'] == coach)
    w('**Athletics, beside the fee fund.** The athletic coaches line was voted $0 in FY2024 and '
      'FY2025. It spent %s across FY2023 to FY2026; in the same years the athletics fee fund '
      'spent %s ([/analysis/spending-what-comes-in](/analysis/spending-what-comes-in)). '
      '*Hypothesis, not tested here:* the split of coaching pay between the general fund and the '
      'fee fund moved from year to year, and the voted line did not follow it. Nothing published '
      'says so; the journal export below would.'
      % (', '.join('%s (FY%d)' % (usd(y['spent']), y['fy']) for y in cl['years']),
         ', '.join('%s (FY%d)' % (usd(ath[y]['fund_spent']), y) for y in YEARS)))
    w('')
    w('**What a reader can do with that.** A line that spent money last year and is voted at '
      '$0 this year is visible in the budget book before the vote, and it is a question a '
      'Finance Committee member can ask. That is the only lever this report names; which answer '
      'is right is not something the ledger can say.')
    w('')
    w('## The worked case: kindergarten aides and paraprofessionals')
    w('')
    w('![Voted against spent for the two kindergarten aide lines together, FY2023 to FY2026.](charts/%s-kindergarten.svg)' % ID)
    w('')
    w('Two lines: **kindergarten aides** (`%s`, org S2032121, MUNIS *%s*) and **kindergarten '
      'paraprofessionals** (`%s`, org S2032131, MUNIS *%s*). Account codes checked against the '
      'ledger before use.' % (KG[0], desc[KG[0]], KG[1], desc[KG[1]]))
    w('')
    w('| year | aides: voted / spent | paraprofessionals: voted / revised / spent | together voted | together spent |')
    w('|---|---:|---:|---:|---:|')
    for y in kg_years:
        l0, l1 = y['lines']
        w('| FY%d | %s / %s | %s / %s / %s | %s | %s |'
          % (y['fy'], usd(l0['voted']), usd(l0['spent']), usd(l1['voted']), usd(l1['revised']),
             usd(l1['spent']), usd(y['voted']), usd(y['spent'])))
    w('')
    w('**What the ledger shows.** In FY2024 and FY2025 the paraprofessional line was voted %s '
      'and %s, and spent %s and %s. In FY2026 both lines were voted $0 and **%s** was charged '
      'to them, %s of it to the aides line, which had spent nothing in the three years before.'
      % (usd(kg_years[1]['voted']), usd(kg_years[2]['voted']), usd(kg_years[1]['spent']),
         usd(kg_years[2]['spent']), usd(k26), usd(k26_aides)))
    w('')
    w('**What it does not show.** Who was paid. An account titled *kindergarten aides* is where '
      'the books put the money, not a person in a classroom (rule 11 of this project). Staff '
      'coded to the line while assigned elsewhere, a reclassification between the aide and '
      'paraprofessional titles, or posts moved from another line would all print the same '
      'ledger. The FY2026 surplus report counts both lines among the paraprofessional lines, '
      'which together ran **%s over budget** in FY2026 — see '
      '[/analysis/fy26-school-surplus](/analysis/fy26-school-surplus).' % usd(para_over))
    w('')
    w('**Beside it, in the same year.** A Finance Committee minute of 12 January 2026 records '
      'the School Committee chair saying kindergarten classrooms had no aides (quoted below), '
      'and the staffing increase requests the schools listed to the Finance Committee in February '
      '2026 included one kindergarten paraprofessional. The ledger '
      'and the minute are both real and nothing published reconciles them; a payroll '
      'distribution for the two accounts would (registered gap).')
    w('')
    w('## Why the special funds are left out')
    w('')
    w('Revolving funds, grants, the circuit breaker and gift funds spend **without '
      'appropriation, by law**: their authority is the fund, not a vote of Town Meeting. A $0 '
      'budget on one of their lines is the normal state. Measured, so the exclusion is visible: '
      'across the four years, %s of the %s cases of a special-fund expense line spending in a '
      'year had a $0 budget, carrying %s of all special-fund spending. Counting them would bury the general '
      'fund question under a fact about how those funds are authorised.'
      % (sp_zero, sp_lines, pct(sp_share)))
    w('')
    w('| year | special-fund lines spending | of them at $0 budget | spent | spent on $0 lines |')
    w('|---|---:|---:|---:|---:|')
    for s in special_rows:
        w('| FY%d | %d | %d | %s | %s |' % (s['fy'], s['lines_spending'], s['at_zero'],
                                         usd(s['spent']), usd(s['spent_at_zero'])))
    w('')
    w('## What was said')
    w('')
    w('Searched: School Committee and Finance Committee minutes from FY2023 on, for *no budget*, '
      '*unbudgeted*, *zero budget*, *not budgeted*, *zeroed out*, *kindergarten aide*, '
      '*kindergarten para* and paraprofessional budget discussion. No hit discusses a specific '
      'line voted at $0 — which says what these words found, not that nobody raised it in '
      'other words. What bears on these lines:')
    w('')
    for q in QUOTES:
        w('- **%s, %s** (%s): *“%s”* — [minutes](%s)' % (q['body'], q['date'], q['who'], q['text'], q['url']))
    w('')
    w('The September 2025 minute shows the School Committee approving FY2025 transfers into a '
      'stipends account, the year the district-wide stipends line started at $0 and had money '
      'moved onto it; the minute does not give the account number, so which stipends line it '
      'was is not established. The “double budget amount for paraprofessionals” is recorded '
      'as discussed, not explained.')
    w('')
    w('## What it does not show')
    w('')
    not_est = [
        'What was paid from any of these lines — the ledger gives one spent figure per line per '
        'year (registered gap: a journal or payroll export).',
        'Why any line was voted at $0. Budget carried on another line, a post not expected to be '
        'filled, a coding change: each fits the same numbers.',
        'Where mid-year transfers came from; the ledger gives a net change per line (registered gap).',
        'Whether anyone paid from the kindergarten lines worked in a kindergarten classroom '
        '(registered gap).',
        'Anything about the special funds, which spend without appropriation by law and are '
        'excluded.',
        'Years before FY2023: the period-13 ledgers delivered cover FY2023-FY2026 only.',
    ]
    for t in not_est:
        w('- ' + t)
    w('')
    w('## Closes with')
    w('')
    w('- **A MUNIS general ledger detail (journal) export for department 300, FY2023-FY2026, for '
      'the lines listed above** — who or what each line paid, with the warrant reference. It '
      'settles what the spending was.')
    w('- **The FY2026 payroll distribution for the two kindergarten accounts** — who was paid, '
      'and which building they were assigned to.')
    w('- **The schedule of line item transfers the School Committee approved each year**, with '
      'the from and to accounts — where the money moved onto the (c) lines came from.')
    w('')
    w('## Method')
    w('')
    w('- Source: `sources/data/munis-school-ytd.csv`, `report = gf-school` (fund 0100, '
      'department 300), `period = 13`, FY2023-FY2026. The report prints every account every '
      'year (%d accounts), so a zero line is a row, not an absence; the build refuses to write '
      'if that stops being true.' % len(accts))
    w('- “Voted” is `original_approp`; “revised” is `revised_budget` (original plus '
      '`transfers_adjustments`); “spent” is `ytd_expended` at the close. Zero means within half '
      'a cent. Spent is strictly positive; one line with a negative spent figure (a credit) '
      'meets no definition.')
    w('- The three definitions are computed independently and never summed into one another.')
    w('- Plain names are ours. Re-verified by `scripts/verify_spent_no_budget.py`, a second '
      'route in Decimal from the CSV.')
    w('')
    w('## Sources')
    w('')
    man = SOM.manifest()
    srcs = []
    for y in YEARS:
        srcs.append(SOM.source(man, 'town-ledgers/expenses/glytdbud-expense-fy%d-p13-gf-school.xlsx' % y,
                               'munis_school_ytd', 'Town of Lunenburg (MUNIS), by records request',
                               'School general fund, department 300, period 13, FY%d: voted, '
                               'transferred, revised, spent and encumbered for every line.' % y))
    for y in YEARS:
        srcs.append(SOM.source(man, 'town-ledgers/expenses/glytdbud-expense-fy%d-p13-special-school.xlsx' % y,
                               'munis_school_ytd', 'Town of Lunenburg (MUNIS), by records request',
                               'School special funds, period 13, FY%d: used only to measure the '
                               'excluded zero-budget lines.' % y))
    for q in QUOTES:
        stem = 'meetings/%s/%s.' % (q['file'].split('/')[0], os.path.basename(q['file'])[:-4])
        keys = sorted(k for k in man if k.startswith(stem))
        if not keys:
            fail('no archived document for the minutes %s (rule 12)' % q['file'])
        srcs.append(SOM.source(man, keys[0], 'minutes', 'Lunenburg %s' % q['body'],
                               'Minutes of %s: "%s"' % (q['date'], q['text'])))
    seen, uniq = set(), []
    for s in srcs:
        if s['path'] not in seen:
            seen.add(s['path'])
            uniq.append(s)
    srcs = uniq
    w('| document | what it gives here |')
    w('|---|---|')
    for s in srcs:
        w('| [%s](%s) | %s |' % (s['filename'], s['docs_url'], s['note'].replace('|', '/')))
    md = '\n'.join(b) + '\n'

    # =================================================================================
    # THE PAYLOAD
    # =================================================================================
    pay = dict(
        generated_by='scripts/build_spent_no_budget.py',
        about='Which school general fund lines spent money against a $0 budget, FY2023 to '
              'FY2026, by three separate definitions, and whether it recurs.',
        grain='DOLLARS spent at the close (period 13) per school general fund budget line '
              '(MUNIS account, fund 0100, department 300) per fiscal year. A line is a place '
              'the books put money — not a person or a position.',
        stats=[
            dict(value=usd(a_tot), tone='var(--series-cost)',
                 label='spent on school general fund lines voted at $0, FY2023–FY2026 '
                       '(original budget $0)'),
            dict(value=usd(b_tot),
                 label='of it on lines still at $0 after every mid-year transfer'),
            dict(value=usd(k26),
                 label='charged to the two kindergarten aide lines in FY2026, both voted at $0'),
        ],
        definitions=dict(
            a='original appropriation $0 and spent > 0: the voted line did not describe the spending',
            b='revised budget $0 and spent > 0: still unbudgeted after every transfer',
            c='original appropriation $0 and revised budget > 0: money moved onto the line mid-year'),
        years=list(YEARS),
        by_year=by_year,
        department=dept,
        lines=lines,
        recurring=[ln['account'] for ln in recurring],
        persistence=dict(lines_a=n_a_acc, voted_other_year=n_voted_other,
                         prior_year_spent=n_prior_spent, prior_year_cases=len(inst_prior)),
        kindergarten=kg,
        fy26_para_over=para_over,
        special_funds=special_rows,
        special_share_pct=round(sp_share, 2),
        quotes=QUOTES,
        gaps=GAP_WHATS,
        sources=srcs,
        not_established=not_est,
        conclusions=conc,
    )
    pay_text = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    svgs = {'years': years_svg(by_year), 'lines': lines_svg(lines), 'kindergarten': kg_svg(kg)}
    return md, pay_text, svgs


def outputs(md, pay_text, svgs):
    out = [(MD, md), (PAYLOAD, pay_text)]
    for n in CHART_NAMES:
        out.append((os.path.join(CHARTS, '%s-%s.svg' % (ID, n)), svgs[n]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    md, pay_text, svgs = build()
    out = outputs(md, pay_text, svgs)
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t in out
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        if stale:
            print('STALE: %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('%s.md, its payload and its three charts are current' % ID)
        return 0
    for p, t in out:
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(t)
        os.replace(tmp, p)
    print('wrote %s' % ', '.join(os.path.relpath(p, ROOT) for p, _ in out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
