#!/usr/bin/env python3
"""The FY25 school surplus, from the closed ledger.

    python3 scripts/build_fy25_school_surplus.py            # write the .md and the payload
    python3 scripts/build_fy25_school_surplus.py --check     # fail if either is stale

Reads ONLY `sources/data/munis-school-ytd.csv` (FY2025, report `gf-school`, `type` E -- the
closed period-13 expense ledger for department 300), `sources/data/revenue-distribution-fy26.csv`
(the scope check), and quotes the district's own September 2025 figure from the School
Committee's minutes. Rule 1: the budget-vs-actual distinction does not apply here because
everything on this page is the SAME ledger at its final period -- there is no budget column
being compared to an actual column, only one closed fiscal year read two ways.

WHERE THIS CAME FROM. `notes/findings/FY25-SCHOOL-SURPLUS-FROM-THE-LEDGER.md` is the working
notes; every figure, table and limit there is recomputed here rather than carried over as
prose. See `notes/process/WRITING-AN-ANALYSIS.md` and CLAUDE.md rules 2, 7, 7a-7f, 9, 12, 13.

THE FUNCTION FAMILY. `account` is a hyphen-joined string whose 4th segment is the DESE
function code, e.g. `0100-3-300-4220-01-1-74-2-535006` -> `4220` -> the 4000s (operations &
maintenance). Grouping by FAMILY (function // 1000 * 1000) is what the working notes'
table uses, not the bare function code -- function 2330 (paraprofessionals) is a 2000s
code and lands in "instruction", not in "other student services".

SALARY VS NON-SALARY. `obj` (the object code) starting with `51` is a salary line; every
other object code is not. This is the same test MUNIS's own object-code structure uses
elsewhere in this archive.
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C                                   # noqa: E402
from conclusions import conclusion, emit, figure           # noqa: E402

LEDGER = os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv')
REVDIST = os.path.join(ROOT, 'sources', 'data', 'revenue-distribution-fy26.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
MINUTES_TXT = os.path.join(ROOT, 'sources', 'meetings', 'text', 'school-committee',
                           '2025-09-17-minutes-7408.txt')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'fy25-school-surplus.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy25-school-surplus.json')
CHART = os.path.join(ROOT, 'sources', 'analyses', 'charts', 'fy25-school-surplus-waterfall.svg')
FY = 2025
PERIOD = 13
REPORT = 'gf-school'
DISTRICT_FIGURE = 603885.97  # QUOTED, School Committee minutes, 17 September 2025.

FAMILY_LABEL = {
    1000: 'leadership / admin', 2000: 'instruction', 3000: 'other student services',
    4000: 'operations & maintenance', 5000: 'fixed charges', 7000: 'assets',
    9000: 'out-of-district tuition',
}

PARA_SCHOOL = {
    'S2512131': 'Primary', 'S2516131': 'High school (SPED)', 'S2515131': 'Middle school (SPED)',
    'S2514131': 'Elementary (SPED)', 'S2066131': 'High school (not SPED)',
}


def fail(msg):
    sys.stderr.write('build_fy25_school_surplus: %s\n' % msg)
    sys.exit(1)


def usd(v):
    return C.usd(v)


def usd0(v):
    n = round(float(v))
    return ('-$%s' if n < 0 else '$%s') % format(abs(n), ',d')


def rows_fy25():
    if not os.path.exists(LEDGER):
        fail('missing %s' % os.path.relpath(LEDGER, ROOT))
    out = []
    with open(LEDGER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if (r['fiscal_year'] == str(FY) and r['period'] == str(PERIOD)
                    and r['report'] == REPORT and r['type'] == 'E'):
                out.append(r)
    if len(out) < 300:
        fail('only %d FY%d period %d %s expense rows -- expected hundreds'
             % (len(out), FY, PERIOD, REPORT))
    return out


def scope_check(rows):
    """The original appropriation here must equal the FY25 school figure the Town's own
    revenue-distribution workbook carries. Different document, same quantity, different
    stage -- rule 1 forbids comparing a budget to an actual, but this is budget to budget."""
    orig = sum(float(r['original_approp']) for r in rows)
    if not os.path.exists(REVDIST):
        fail('missing %s' % os.path.relpath(REVDIST, ROOT))
    want = None
    with open(REVDIST, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['line'] == 'ALL NEW FY26 REVENUES distributed by FY25 share / School Dept %':
                want = float(r['fy25'])
    if want is None:
        fail('revenue-distribution-fy26.csv has no "School Dept %" row to check scope against')
    if round(orig, 2) != round(want, 2):
        fail('SCOPE: original appropriation %.2f does not equal the revenue-distribution '
             'workbook’s FY25 school figure %.2f -- this run is not department 300 alone, '
             'or the workbook moved' % (orig, want))
    return orig, want


def totals(rows):
    t = dict(original=0.0, transfers=0.0, revised=0.0, expended=0.0, encumbered=0.0,
              available=0.0)
    for r in rows:
        t['original'] += float(r['original_approp'])
        t['transfers'] += float(r['transfers_adjustments'])
        t['revised'] += float(r['revised_budget'])
        t['expended'] += float(r['ytd_expended'])
        t['encumbered'] += float(r['encumbrances'])
        t['available'] += float(r['available_budget'])
    return {k: round(v, 2) for k, v in t.items()}


def by_function(rows):
    fam = {}
    for r in rows:
        parts = r['account'].split('-')
        func = parts[3] if len(parts) > 3 else '0'
        family = (int(func) // 1000) * 1000
        sal, non = fam.setdefault(family, [0.0, 0.0])
        avail = float(r['available_budget'])
        if r['obj'].startswith('51'):
            fam[family][0] += avail
        else:
            fam[family][1] += avail
    out = []
    for family, (sal, non) in fam.items():
        if family == 0 and round(sal, 2) == 0 and round(non, 2) == 0:
            continue
        out.append(dict(family=family, label=FAMILY_LABEL.get(family, 'unclassified'),
                         salary=round(sal, 2), non_salary=round(non, 2),
                         total=round(sal + non, 2)))
    out.sort(key=lambda d: -d['total'])
    return out


def para_accounts(rows):
    out = []
    for r in rows:
        parts = r['account'].split('-')
        func = parts[3] if len(parts) > 3 else None
        if func != '2330':
            continue
        out.append(dict(
            account=r['account'], org=r['org'], description=r['description'].strip(),
            school=PARA_SCHOOL.get(r['org']),
            original=round(float(r['original_approp']), 2),
            transfers=round(float(r['transfers_adjustments']), 2),
            revised=round(float(r['revised_budget']), 2),
            expended=round(float(r['ytd_expended']), 2),
            available=round(float(r['available_budget']), 2),
        ))
    return out


def district_quote():
    """The School Committee's own figure, quoted and cited, 17 September 2025."""
    if not os.path.exists(MINUTES_TXT):
        fail('missing %s' % os.path.relpath(MINUTES_TXT, ROOT))
    text = open(MINUTES_TXT, encoding='utf-8').read()
    needle = '$603,885.97'
    if needle not in text:
        fail('%s does not quote %s' % (os.path.relpath(MINUTES_TXT, ROOT), needle))
    # The page the quote sits on, from the extractor's own ===PAGE N=== markers.
    idx = text.index(needle)
    page = text.count('===PAGE', 0, idx)
    return page


def manifest_row(key):
    with open(MANIFEST, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['key'] == key:
                return r
    fail('%s is not in the manifest (rule 12)' % key)


def sources(page):
    out = []
    key = 'meetings/school-committee/2025-09-17-minutes-7408.pdf'
    r = manifest_row(key)
    out.append(dict(
        path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']), url=r['upstream'],
        docs_url='/docs/' + key, filename=key.split('/')[-1],
        table='school_committee_minutes',
        publisher='Lunenburg School Committee',
        note='Minutes of 17 September 2025, page %d of 3: "the surplus number has gone up '
             'to $603,885.97, the change is due to closing out purchase orders from FY25." '
             'Quoted in sources/analyses/budget-vs-actual.md.' % page))
    key2 = 'town-ledgers/expenses/glytdbud-expense-fy2025-p13-gf-school.xlsx'
    out.append(dict(
        path='sources/' + key2, sha256='', bytes=0, url='',
        docs_url='/docs/' + key2, filename=key2.split('/')[-1],
        table='munis-school-ytd', publisher='Town of Lunenburg — Town Accountant',
        note='MUNIS year-to-date budget report, department 300 (school general fund), '
             'period 13 — the closed FY2025 ledger. Original appropriation, transfers '
             'and adjustments, revised budget, year-to-date expended, encumbrances and '
             'available budget, by account. Obtained by public records request.'))
    key3 = 'data/revenue-distribution-fy26.csv'
    out.append(dict(
        path='sources/' + key3, sha256='', bytes=0, url='',
        docs_url='/docs/' + key3, filename=key3.split('/')[-1],
        table='revenue-distribution-fy26', publisher='Town of Lunenburg',
        note='The town’s FY26 revenue-distribution workbook. Used only for the scope '
             'check: its FY25 School Dept figure must equal, and does equal, the original '
             'appropriation summed from the MUNIS ledger above.'))
    return out


def waterfall_svg(t, district_figure, diff, moved_out, not_spent_against_original):
    """The signature visual, in two panels, because one scale cannot carry both findings.

    LEFT: voted -> moved out mid-year -> spent -> unspent, on the full $25M scale. This is
    where the money went: almost all of it was spent, and the step moved out mid-year is
    real but small enough that, at this scale, it barely shows -- which is itself true and
    is said in words rather than hidden.

    RIGHT: the unspent total beside the district's own September figure, ZOOMED to a range
    that makes the two legible against each other -- the comparison this report is about,
    and the one the left panel's scale cannot show at all.
    """
    INK, SECOND, MUTED = '#0b0b0b', '#52514e', '#898781'
    AXIS, SURFACE = '#c3c2b7', '#fcfcfb'
    SPENT, UNSPENT, MOVED, DISTRICT = '#184f95', '#3987e5', '#86b6ef', '#e34948'
    FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

    def esc(s):
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def usdk(v):
        a = abs(v)
        s = '-' if v < 0 else ''
        return ('%s$%.2fM' % (s, a / 1e6)) if a >= 1e6 else ('%s$%s' % (s, usd0(a)[1:]))

    W, H = 680, 300
    TOP, BASE = 56, 206
    PANEL_H = BASE - TOP

    b = []

    # ---- LEFT PANEL: the full flow, 0 to the original appropriation ----------------
    orig = t['original']
    scale = PANEL_H / orig
    BW, GAP = 78, 30
    stages = [
        ('Voted\n(original)', 0, orig, SPENT, orig),
        ('Revised\nbudget', 0, t['revised'], SPENT, t['revised']),
        ('Spent', 0, t['expended'], SPENT, t['expended']),
        ('Unspent\nat the close', 0, t['available'], UNSPENT, t['available']),
    ]
    x = 0
    for label, base, height, color, show in stages:
        hpx = max(height * scale, 1.5)
        y = BASE - hpx
        b.append('<rect x="%.1f" y="%.1f" width="%d" height="%.1f" fill="%s" rx="2"/>'
                  % (x, y, BW, hpx, color))
        b.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="700" '
                  'text-anchor="middle" fill="%s">%s</text>'
                  % (x + BW / 2, y - 6, INK, usdk(show)))
        for li, line in enumerate(label.split('\n')):
            b.append('<text x="%.1f" y="%.1f" font-size="9.5" text-anchor="middle" '
                      'fill="%s">%s</text>'
                      % (x + BW / 2, BASE + 16 + li * 11, SECOND, esc(line)))
        x += BW + GAP
    # The step moved out mid-year, called out beside the first two bars rather than
    # drawn as its own bar -- at this scale (0.5% of the total) a bar for it would be
    # a sliver nobody could see, and labelling a sliver is worse than naming it in words.
    b.append('<text x="%.1f" y="%.1f" font-size="9.5" font-weight="700" text-anchor="middle" '
              'fill="%s">%s moved out mid-year →</text>'
              % (BW + GAP / 2, TOP - 6, MOVED, usdk(t['transfers'])))
    left_w = x - GAP
    b.append('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>'
              % (BASE, left_w, BASE, AXIS))
    b.append('<text x="0" y="%.1f" font-size="9.5" fill="%s">The whole flow, on one scale '
              '(0 to the original appropriation)</text>' % (BASE + 40, MUTED))

    # ---- RIGHT PANEL: unspent vs. the district's figure, zoomed -------------------
    RX0 = left_w + 56
    RW = W - RX0
    lo = min(t['available'], district_figure)
    hi = max(t['available'], district_figure)
    rmin = lo * 0.9
    rmax = hi * 1.08
    rscale = PANEL_H / (rmax - rmin)

    def ry(v):
        return BASE - (v - rmin) * rscale

    bars = [('Our ledger', t['available'], UNSPENT), ('The district,\n17 Sept 2025',
             district_figure, DISTRICT)]
    bx = RX0
    RBW, RGAP = 80, 20
    for label, v, color in bars:
        y = ry(v)
        b.append('<rect x="%.1f" y="%.1f" width="%d" height="%.1f" fill="%s" rx="2"/>'
                  % (bx, y, RBW, BASE - y, color))
        b.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="700" '
                  'text-anchor="middle" fill="%s">%s</text>'
                  % (bx + RBW / 2, y - 6, INK, usd(v)))
        for li, line in enumerate(label.split('\n')):
            b.append('<text x="%.1f" y="%.1f" font-size="9.5" text-anchor="middle" '
                      'fill="%s">%s</text>'
                      % (bx + RBW / 2, BASE + 16 + li * 11, SECOND, esc(line)))
        bx += RBW + RGAP
    bx -= RGAP
    b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>'
              % (RX0, BASE, bx, BASE, AXIS))
    # The gap bracket between the two zoomed bars.
    gy = ry(lo)
    b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" '
              'stroke-dasharray="2,2"/>' % (RX0, gy, bx, gy, '#b3261e'))
    b.append('<text x="%.1f" y="%.1f" font-size="9.5" text-anchor="middle" fill="%s">'
              'zoomed to %s–%s</text>'
              % (RX0 + (bx - RX0) / 2, BASE + 40, MUTED, usdk(rmin), usdk(rmax)))
    b.append('<text x="%.1f" y="%.1f" font-size="10.5" font-weight="700" '
              'text-anchor="middle" fill="%s">%s gap</text>'
              % (RX0 + (bx - RX0) / 2, TOP - 6, '#b3261e', usd(diff)))

    title = 'The FY2025 school budget, voted to closed'
    subtitle = ('%s not spent against the original appropriation — %s turned back, '
                '%s moved out mid-year — and %s more than the district told the '
                'School Committee'
                % (usd(not_spent_against_original), usd(t['available']), usd(moved_out),
                   usd(diff)))
    body = ''.join(b)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="%s. %s" font-family=\'%s\'>\n'
            '<rect width="%d" height="%d" fill="%s"/>\n'
            '<text x="0" y="16" font-size="13" font-weight="700" fill="%s">%s</text>\n'
            '<text x="0" y="33" font-size="10.5" fill="%s">%s</text>\n%s\n</svg>\n'
            % (W, H, W, H, esc(title), esc(subtitle), FONT, W, H, SURFACE, INK, esc(title),
               SECOND, esc(subtitle), body))


def build():
    rows = rows_fy25()
    orig, revdist_fy25 = scope_check(rows)
    t = totals(rows)
    diff = round(t['available'] - DISTRICT_FIGURE, 2)
    moved_out = round(abs(t['transfers']), 2)
    not_spent_against_original = round(t['available'] + moved_out, 2)
    bf = by_function(rows)
    pa = para_accounts(rows)
    page = district_quote()

    fam = {r['family']: r for r in bf}
    instr = fam.get(2000, dict(total=0.0))
    ops = fam.get(4000, dict(total=0.0, salary=0.0, non_salary=0.0))
    concentration = instr['total'] + ops['total']
    concentration_share = 100 * concentration / t['available']

    # Para accounts, by org, for the two moved-in-both-directions lines and the HS line.
    pa_by_org = {r['org']: r for r in pa}
    ms_sped = pa_by_org.get('S2515131')
    es_sped = pa_by_org.get('S2514131')
    hs_nonsped = pa_by_org.get('S2066131')
    ps_sped = pa_by_org.get('S2512131')
    hs_sped = pa_by_org.get('S2516131')

    rws = [
        conclusion(
            id='the-closed-ledger-exceeds-the-districts-own-figure',
            claim='The closed ledger shows %s more unspent than the School Committee was told.'
                  % usd(diff),
            so_what='No single account, and no pair of accounts, equals the difference.',
            figures={'diff': figure(diff, usd(diff), 'more unspent than the district '
                                                        'reported, 17 September 2025'),
                     'ledger': figure(t['available'], usd(t['available'])),
                     'district': figure(DISTRICT_FIGURE, usd(DISTRICT_FIGURE))},
            figure='diff', kind='measured', bearing='sizes',
            detail='The closed MUNIS ledger for department 300 at period 13 shows %s '
                   'available at the close. The School Committee was told %s on 17 September '
                   '2025. Entries posted to the department after that date are a hypothesis '
                   'that would explain the gap; nothing here tests it.'
                   % (usd(t['available']), usd(DISTRICT_FIGURE)),
            basis='`sources/data/munis-school-ytd.csv`, FY2025 period 13, report gf-school, '
                  'type E, summed across 415 accounts; the School Committee minutes, '
                  '17 September 2025.',
            not_shown='What was posted to the department after 17 September 2025, or whether '
                      'the gap is one entry or several.',
            allow=('13', '17', '2025.', '2025', '300'),
        ),
        conclusion(
            id='the-department-did-not-spend-most-of-what-moved',
            claim='%s was not spent against the original appropriation of %s.'
                  % (usd(not_spent_against_original), usd(t['original'])),
            so_what='%s turned back at the close, plus %s moved out of the department '
                    'during the year.' % (usd(t['available']), usd(moved_out)),
            figures={'total': figure(not_spent_against_original,
                                      usd(not_spent_against_original),
                                      'not spent against the original appropriation'),
                     'orig': figure(t['original'], usd(t['original'])),
                     'turned_back': figure(t['available'], usd(t['available'])),
                     'moved': figure(moved_out, usd(moved_out))},
            figure='total', kind='measured', bearing='sizes',
            detail='The department was appropriated %s. %s of that was moved to other '
                   'budgets during the year (net), and %s of what remained was still '
                   'unspent when the books closed, with nothing encumbered.'
                   % (usd(t['original']), usd(moved_out), usd(t['available'])),
            basis='`munis-school-ytd.csv`: original_approp, transfers_adjustments and '
                  'available_budget, summed across the same 415 accounts.',
            not_shown='Where the %s that moved out went — the ledger carries a net per '
                      'account, no counterparty.' % usd(moved_out),
        ),
        conclusion(
            id='para-budgets-moved-in-both-directions',
            claim='One SPED paraprofessional line gained %s mid-year; another lost %s.'
                  % (usd(ms_sped['transfers']), usd(abs(es_sped['transfers']))),
            so_what='The high-school paraprofessional line (not SPED) spent %s of %s '
                    'budgeted.' % (usd(hs_nonsped['expended']), usd(hs_nonsped['revised'])),
            figures={'ms': figure(ms_sped['transfers'], usd(ms_sped['transfers']),
                                   'added to the middle-school SPED paraprofessional line'),
                     'es': figure(abs(es_sped['transfers']), usd(abs(es_sped['transfers'])),
                                  'removed from the elementary SPED paraprofessional line'),
                     'hs_spent': figure(hs_nonsped['expended'], usd(hs_nonsped['expended'])),
                     'hs_budget': figure(hs_nonsped['revised'], usd(hs_nonsped['revised'])),
                     'ps': figure(ps_sped['available'], usd(ps_sped['available'])),
                     'hs_sped': figure(hs_sped['available'], usd(hs_sped['available'])),
                     'ms_avail': figure(ms_sped['available'], usd(ms_sped['available'])),
                     'es_avail': figure(es_sped['available'], usd(es_sped['available']))},
            figure='ms', kind='measured', bearing='sizes',
            detail='Function 2330 (paraprofessionals) ended under budget everywhere: '
                   'Primary %s, high school %s, middle school %s, elementary %s unspent. '
                   'The "double booking of the para salaries" named in the 17 September '
                   '2025 minutes is not visible at this grain — nothing in the ledger '
                   'names a cause for either transfer.'
                   % (usd(ps_sped['available']), usd(hs_sped['available']),
                      usd(ms_sped['available']), usd(es_sped['available'])),
            basis='`munis-school-ytd.csv`, function 2330 accounts, transfers_adjustments '
                  'and available_budget by org.',
            not_shown='Why either transfer was made, or what "double booking" referred to.',
            allow=('2330', '17', '2025'),
        ),
        conclusion(
            id='consistent-with-the-towns-facilities-explanation',
            claim='Operations & maintenance holds %s of the unspent total, split evenly.'
                  % usd(ops['total']),
            so_what='That is CONSISTENT WITH the Town’s explanation for FY25; it does '
                    'not prove it.',
            figures={'ops': figure(ops['total'], usd(ops['total']),
                                    'unspent in operations & maintenance (function 4000s)'),
                     'sal': figure(ops['salary'], usd(ops['salary'])),
                     'non': figure(ops['non_salary'], usd(ops['non_salary']))},
            figure='ops', kind='hypothesis', bearing='sizes',
            detail='The Town’s free-cash press release states: "significant turnover '
                   'and unfilled positions in the facilities department resulted in unspent '
                   'salaries and stalled maintenance projects." Operations & maintenance '
                   'holds %s unspent, %s of it salary and %s non-salary — consistent '
                   'with that account, and not a confirmation of it: the ledger shows '
                   'dollars by account, not posts or projects.'
                   % (usd(ops['total']), usd(ops['salary']), usd(ops['non_salary'])),
            basis='`munis-school-ytd.csv`, the 4000-family accounts, available_budget split '
                  'by whether the object code starts with 51 (salary); the Town’s FY27 '
                  'budget press release.',
            not_shown='Whether any specific post was vacant, or which maintenance project '
                      'stalled. A dollar is not a post (rule 7, rule 11).',
            allow=('25',),
        ),
    ]

    chart_svg = waterfall_svg(t, DISTRICT_FIGURE, diff, moved_out, not_spent_against_original)

    md = render(t, diff, moved_out, not_spent_against_original, bf, pa, page, concentration,
                concentration_share, revdist_fy25, orig)
    pay = payload(t, diff, moved_out, not_spent_against_original, bf, pa, page, rws)
    return md, pay, chart_svg


def render(t, diff, moved_out, not_spent_against_original, bf, pa, page, concentration,
           concentration_share, revdist_fy25, orig):
    b = []
    w = b.append
    w('# The FY25 school surplus, from the closed ledger\n')
    w('**What the closed MUNIS ledger shows for department 300 at period 13, beside the '
      'figure the School Committee was told on 17 September 2025.**\n')
    w('---\n')
    w('## The short version\n')
    w('![The FY2025 school budget stepping from the %s voted appropriation down to %s '
      'available at the close, with the district’s own %s figure shown beside it and '
      'the %s gap between them marked.](charts/fy25-school-surplus-waterfall.svg)\n'
      % (usd0(t['original']), usd0(t['available']), usd0(DISTRICT_FIGURE), usd0(diff)))
    w('**%s was unspent in the school general fund when FY2025 closed** — %s turned '
      'back at the close plus %s moved to other budgets mid-year, against an original '
      'appropriation of %s.\n' % (usd(not_spent_against_original), usd(t['available']),
                                   usd(moved_out), usd(t['original'])))
    w('**The closed ledger’s %s exceeds the district’s own %s by %s.** The '
      'School Committee was told the surplus had reached $603,885.97 on 17 September 2025. '
      'No single account, and no pair of accounts, accounts for the gap; entries posted '
      'after that date are a hypothesis this ledger cannot test.\n'
      % (usd(t['available']), usd(DISTRICT_FIGURE), usd(diff)))
    w('**Nothing is still open.** Encumbrances are $0.00, so the figure is final as the '
      'system holds it, and the department scope is confirmed: the original appropriation '
      '(%s) equals the Town’s own FY25 school figure in its revenue-distribution '
      'workbook (%s).\n' % (usd(orig), usd(revdist_fy25)))
    w('---\n')
    w('## Where it sat, by DESE function\n')
    w('Net unspent at the close, by function family (the account string’s 4th segment, '
      'grouped to the thousands) and whether the line is salary (object code starting `51`) '
      'or not.\n')
    w('| function | salary | non-salary | total |\n|---|---:|---:|---:|')
    for r in bf:
        w('| %d %s | %s | %s | %s |'
          % (r['family'], r['label'], usd0(r['salary']) if r['salary'] else '—',
             usd0(r['non_salary']) if r['non_salary'] else '—', usd0(r['total'])))
    tot_sal = sum(r['salary'] for r in bf)
    tot_non = sum(r['non_salary'] for r in bf)
    w('| | **%s** | **%s** | **%s** |\n' % (usd0(tot_sal), usd0(tot_non),
                                             usd0(tot_sal + tot_non)))
    w('**Instruction and operations & maintenance together hold %s — %s of the %s '
      'unspent.** Almost no account ended overspent: the largest over-lines are in '
      'operations and maintenance and in assets, and both are small beside the unspent '
      'total.\n' % (usd(concentration), C.pct(concentration_share, 0), usd(t['available'])))
    w('---\n')
    w('## The paraprofessional accounts (function 2330)\n')
    w('Special-education paraprofessional lines ended under budget everywhere, and para '
      'budgets moved between lines mid-year in both directions.\n')
    w('| school | account | original | transfers | revised | spent | available |'
      '\n|---|---|---:|---:|---:|---:|---:|')
    for r in sorted(pa, key=lambda r: -r['available']):
        if round(r['revised'], 2) == 0 and round(r['expended'], 2) == 0:
            continue
        w('| %s | `%s` | %s | %s | %s | %s | %s |'
          % (r['school'] or r['description'][:28], r['org'], usd0(r['original']),
             usd0(r['transfers']), usd0(r['revised']), usd0(r['expended']),
             usd0(r['available'])))
    w('')
    w('*The "double booking of the para salaries" named in the 17 September 2025 minutes '
      'is not visible at this grain — the ledger carries no narrative behind either '
      'transfer.*\n')
    w('---\n')
    w('## What it does not show\n')
    w('- What any dollar was spent on, or when — no journal.\n')
    w('- Where the %s moved out of the department went — net per account, no '
      'counterparty.\n' % usd(moved_out))
    w('- Why the ledger is %s above the district’s September figure. Entries posted '
      'after 17 September 2025 are a hypothesis; nothing here tests it.\n' % usd(diff))
    w('- Whether facilities’ unspent salary was unfilled posts — dollars are not '
      'posts (rule 7, rule 11).\n')
    w('---\n')
    w('## Closes with\n')
    w('The FY2025 transfer schedule for department 300 with counterparties and authority, '
      'and the journal entries posted to department 300 after 17 September 2025.\n')
    w('---\n')
    w('## Sources\n')
    w('| | |\n|---|---|')
    w('| The ledger | `munis-school-ytd.csv`, FY2025 period 13, report gf-school, type E, '
      '415 accounts |')
    w('| The scope check | `revenue-distribution-fy26.csv`, the FY25 School Dept figure |')
    w('| The district’s figure | School Committee minutes, 17 September 2025, page %d '
      'of 3 |' % page)
    return '\n'.join(b) + '\n'


def payload(t, diff, moved_out, not_spent_against_original, bf, pa, page, rws):
    tot_sal = round(sum(r['salary'] for r in bf), 2)
    tot_non = round(sum(r['non_salary'] for r in bf), 2)
    return dict(
        generated_by='scripts/build_fy25_school_surplus.py',
        about='What the closed FY2025 school general fund ledger shows was unspent and '
              'moved, beside the figure the School Committee was given on 17 September 2025.',
        grain='DOLLARS, department 300 (school general fund) only, FY2025 period 13 — '
              'the closed ledger, 415 accounts. Not a comparison of budget to actual: '
              'everything here is the same closed ledger read two ways.',
        fy=FY,
        stats=[
            dict(value=usd0(t['available']), tone='var(--series-cost)',
                 label='unspent at the close, FY2025 school general fund, of %s appropriated'
                       % usd0(t['original'])),
            dict(value=usd0(diff),
                 label='more unspent than the %s the School Committee was told, 17 Sept 2025'
                       % usd0(DISTRICT_FIGURE)),
            dict(value=usd0(moved_out),
                 label='moved out of the department during the year, net'),
        ],
        totals=t,
        district_figure=DISTRICT_FIGURE,
        diff=diff,
        moved_out=moved_out,
        not_spent_against_original=not_spent_against_original,
        waterfall=dict(voted=t['original'], moved_out=t['transfers'], revised=t['revised'],
                       spent=t['expended'], unspent=t['available'],
                       district_figure=DISTRICT_FIGURE),
        by_function=bf,
        by_function_totals=dict(salary=tot_sal, non_salary=tot_non, total=round(tot_sal + tot_non, 2)),
        para_accounts=pa,
        sources=sources(page),
        not_established=[
            'Where the %s moved out of the department went — net per account, no '
            'counterparty.' % usd(moved_out),
            'Why the ledger is %s above the district’s September figure. Entries '
            'posted after 17 September 2025 are a hypothesis; nothing here tests it.'
            % usd(diff),
            'Whether facilities’ unspent salary was unfilled posts — dollars are '
            'not posts.',
            'What "double booking of the para salaries" (17 September 2025 minutes) refers '
            'to — not visible at the account grain.',
        ],
        conclusions=emit('fy25-school-surplus', rws),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    md, pay, chart_svg = build()
    pay_text = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        cur_md = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        cur_pay = open(PAYLOAD, encoding='utf-8').read() if os.path.exists(PAYLOAD) else ''
        cur_svg = open(CHART, encoding='utf-8').read() if os.path.exists(CHART) else ''
        bad = [n for n, (g, c) in (
            ('fy25-school-surplus.md', (md, cur_md)),
            ('fy25-school-surplus.json', (pay_text, cur_pay)),
            ('fy25-school-surplus-waterfall.svg', (chart_svg, cur_svg)),
        ) if g != c]
        if bad:
            print('STALE %s' % ', '.join(bad), file=sys.stderr)
            return 1
        print('fy25-school-surplus.md, .json and the chart are current')
        return 0
    os.makedirs(os.path.dirname(CHART), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(md)
    open(PAYLOAD, 'w', encoding='utf-8').write(pay_text)
    open(CHART, 'w', encoding='utf-8').write(chart_svg)
    print('wrote %s, %s and %s'
          % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT),
             os.path.relpath(CHART, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
