#!/usr/bin/env python3
"""The school surplus for one fiscal year, from the period-13 MUNIS ledger.

    python3 scripts/build_school_surplus.py --fy 2026           # write the .md, payload, chart
    python3 scripts/build_school_surplus.py --fy 2026 --check   # fail if any is stale
    python3 scripts/build_school_surplus.py --all --check        # every year this builds

ONE GENERATOR, ONE REPORT PER YEAR. The ledger reading -- which rows, the totals, the DESE
function families, the salary split, the paraprofessional accounts, the signature chart
and the write/check -- is shared and lives here once. What differs by year is what the
year is BEING COMPARED WITH, and that is not a parameter, it is a different argument:

  * FY2025 is set beside the figure the School Committee was told on 17 September 2025.
    The year was fully closed (nothing encumbered), so the comparison is one figure to one
    figure. `fy2025()`.
  * FY2026 is set beside the RANGE the period-12 ledger allowed (fy26-closeout.md, built
    from the 1 September 2026 run), because the period-13 run of 6 October 2026 still
    carries open purchase orders. The comparison is a figure to a floor and a ceiling, and
    account by account, period 12 to period 13. `fy2026()`.

So each year has its own story function -- the conclusions, the prose, the payload's
year-specific fields -- and everything they compute from goes through the shared readers.

`scripts/build_fy25_school_surplus.py` is kept as a thin wrapper (`--fy 2025`): the FY25
payload names it as its generator, and that payload is held byte-identical.

Reads ONLY `sources/data/munis-school-ytd.csv` (report `gf-school`, `type` E -- department
300's period-13 expense ledger, extracted from the PUBLISHED spreadsheets; the PDFs of the
same reports are private, CLAUDE.md 13e), `sources/data/munis-ledger.csv` (FY2026 period
12, for the FY26 comparison), `sources/data/revenue-distribution-fy26.csv` (the FY25 scope
check), the School Committee's minutes and agendas, and the archive manifest. Rule 1: no
budget column is compared to an actual column here -- every comparison is the same ledger
at two periods, or the same quantity in two documents.

THE FUNCTION FAMILY. `account` is a hyphen-joined string whose 4th segment is the DESE
function code, e.g. `0100-3-300-4220-01-1-74-2-535006` -> `4220` -> the 4000s (operations &
maintenance). Grouping by FAMILY (function // 1000 * 1000) -- function 2330
(paraprofessionals) is a 2000s code and lands in "instruction".

SALARY VS NON-SALARY. `obj` (the object code) starting with `51` is a salary line.
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

DATA = os.path.join(ROOT, 'sources', 'data')
LEDGER = os.path.join(DATA, 'munis-school-ytd.csv')
P12_LEDGER = os.path.join(DATA, 'munis-ledger.csv')
REVDIST = os.path.join(DATA, 'revenue-distribution-fy26.csv')
MANIFEST = os.path.join(DATA, 'archive-manifest.csv')
MEETING_INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
SC_TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text', 'school-committee')
PERIOD = 13
REPORT = 'gf-school'
YEARS = (2025, 2026)

FAMILY_LABEL = {
    1000: 'leadership / admin', 2000: 'instruction', 3000: 'other student services',
    4000: 'operations & maintenance', 5000: 'fixed charges', 7000: 'assets',
    9000: 'out-of-district tuition',
}

PARA_SCHOOL = {
    'S2512131': 'Primary', 'S2516131': 'High school (SPED)', 'S2515131': 'Middle school (SPED)',
    'S2514131': 'Elementary (SPED)', 'S2066131': 'High school (not SPED)',
}
SPED_PARA_ORGS = ('S2512131', 'S2514131', 'S2515131', 'S2516131')

# The chart's palette, shared by every year's signature visual.
INK, SECOND, MUTED = '#0b0b0b', '#52514e', '#898781'
AXIS, SURFACE = '#c3c2b7', '#fcfcfb'
SPENT, UNSPENT, MOVED, DISTRICT = '#184f95', '#3987e5', '#86b6ef', '#e34948'
CEILING = '#b9b8ae'
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def paths(fy):
    slug = 'fy%02d-school-surplus' % (fy % 100)
    return dict(
        slug=slug,
        md=os.path.join(ROOT, 'sources', 'analyses', slug + '.md'),
        payload=os.path.join(ROOT, 'fy28', 'public', 'data', slug + '.json'),
        chart=os.path.join(ROOT, 'sources', 'analyses', 'charts', slug + '-waterfall.svg'),
    )


def fail(msg):
    sys.stderr.write('build_school_surplus: %s\n' % msg)
    sys.exit(1)


def usd(v):
    return C.usd(v)


def usd0(v):
    n = round(float(v))
    return ('-$%s' if n < 0 else '$%s') % format(abs(n), ',d')


def usd2(v):
    v = round(float(v), 2)
    return ('-$%s' if v < 0 else '$%s') % format(abs(v), ',.2f')


def usdk(v):
    a = abs(v)
    s = '-' if v < 0 else ''
    return ('%s$%.2fM' % (s, a / 1e6)) if a >= 1e6 else ('%s$%s' % (s, usd0(a)[1:]))


def rel(p):
    return os.path.relpath(p, ROOT)


# ---- the shared readers --------------------------------------------------------------

def ledger_rows(fy):
    """Department 300's period-13 expense rows for one fiscal year."""
    if not os.path.exists(LEDGER):
        fail('missing %s' % rel(LEDGER))
    out = []
    with open(LEDGER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if (r['fiscal_year'] == str(fy) and r['period'] == str(PERIOD)
                    and r['report'] == REPORT and r['type'] == 'E'):
                out.append(r)
    if len(out) < 300:
        fail('only %d FY%d period %d %s expense rows -- expected hundreds'
             % (len(out), fy, PERIOD, REPORT))
    return out


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


def family_of(r):
    parts = r['account'].split('-')
    func = parts[3] if len(parts) > 3 else '0'
    return (int(func) // 1000) * 1000


def by_function(rows, with_encumbered=False):
    """Net unspent by function family, split salary / non-salary. With `with_encumbered`
    the still-encumbered amount rides along; FY25 has none and its payload never had the
    key, so it is only added when asked for."""
    fam = {}
    for r in rows:
        family = family_of(r)
        acc = fam.setdefault(family, [0.0, 0.0, 0.0])
        avail = float(r['available_budget'])
        if r['obj'].startswith('51'):
            acc[0] += avail
        else:
            acc[1] += avail
        acc[2] += float(r['encumbrances'])
    out = []
    for family, (sal, non, enc) in fam.items():
        if family == 0 and round(sal, 2) == 0 and round(non, 2) == 0 and round(enc, 2) == 0:
            continue
        row = dict(family=family, label=FAMILY_LABEL.get(family, 'unclassified'),
                   salary=round(sal, 2), non_salary=round(non, 2),
                   total=round(sal + non, 2))
        if with_encumbered:
            row['encumbered'] = round(enc, 2)
        out.append(row)
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


def page_of(path, needle):
    """The page a quote sits on, from the extractor's own ===PAGE N=== markers. Matched
    with whitespace collapsed, because the text layer wraps lines."""
    if not os.path.exists(path):
        fail('missing %s' % rel(path))
    text = open(path, encoding='utf-8').read()
    if needle in text:
        return text.count('===PAGE', 0, text.index(needle))
    flat_needle = ' '.join(needle.split())
    # Walk the text keeping a map from collapsed offsets back to raw ones.
    out, idx = [], []
    prev_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                out.append(' ')
                idx.append(i)
            prev_space = True
        else:
            out.append(ch)
            idx.append(i)
            prev_space = False
    flat = ''.join(out)
    at = flat.find(flat_needle)
    if at < 0:
        fail('%s does not quote %r' % (rel(path), needle))
    return text.count('===PAGE', 0, idx[at])


def manifest_row(key):
    with open(MANIFEST, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['key'] == key:
                return r
    fail('%s is not in the manifest (rule 12)' % key)


def held_source(key, table, publisher, note):
    """A source entry with the manifest's sha256 and size -- rule 12 -- for a document
    the archive holds."""
    r = manifest_row(key)
    return dict(path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']),
                url=r['upstream'], docs_url='/docs/' + key, filename=key.split('/')[-1],
                table=table, publisher=publisher, note=note)


def function_table(bf, w, with_encumbered=False):
    if with_encumbered:
        w('| function | salary | non-salary | unspent | still encumbered |\n'
          '|---|---:|---:|---:|---:|')
    else:
        w('| function | salary | non-salary | total |\n|---|---:|---:|---:|')
    for r in bf:
        cells = [usd0(r['salary']) if r['salary'] else '—',
                 usd0(r['non_salary']) if r['non_salary'] else '—', usd0(r['total'])]
        if with_encumbered:
            cells.append(usd0(r['encumbered']) if r['encumbered'] else '—')
        w('| %d %s | %s |' % (r['family'], r['label'], ' | '.join(cells)))
    tot_sal = sum(r['salary'] for r in bf)
    tot_non = sum(r['non_salary'] for r in bf)
    cells = ['**%s**' % usd0(tot_sal), '**%s**' % usd0(tot_non),
             '**%s**' % usd0(tot_sal + tot_non)]
    if with_encumbered:
        cells.append('**%s**' % usd0(sum(r['encumbered'] for r in bf)))
    w('| | %s |\n' % ' | '.join(cells))


def para_table(pa, w):
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


def waterfall_svg(t, moved_note, unspent_label, compare, rbw, gap_text, title, subtitle,
                  note_below=False):
    """The signature visual, in two panels, because one scale cannot carry both findings.

    LEFT: voted -> revised -> spent -> unspent, on the full $25M scale. Almost all of it was
    spent, and the step moved mid-year is real but too small to show at this scale -- so it
    is named in words above the bars rather than drawn as a sliver nobody could see.

    RIGHT: the unspent figure beside what it is being compared with -- the district's own
    figure for FY25, the period-12 floor and ceiling for FY26 -- ZOOMED to a range that
    makes them legible against each other, which the left panel's scale cannot do at all.
    `compare` is a list of (label, value, colour).
    """
    def esc(s):
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

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
        (unspent_label, 0, t['available'], UNSPENT, t['available']),
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
    # Above the bars, the note collides with the tallest bar's own label; FY25 shipped it
    # there and is held byte-identical, so a later year sets it below the axis instead.
    if note_below:
        b.append('<text x="0" y="%.1f" font-size="9.5" font-weight="700" fill="%s">%s</text>'
                 % (BASE + 54, SPENT, moved_note))
    else:
        b.append('<text x="%.1f" y="%.1f" font-size="9.5" font-weight="700" '
                 'text-anchor="middle" fill="%s">%s</text>'
                 % (BW + GAP / 2, TOP - 6, MOVED, moved_note))
    left_w = x - GAP
    b.append('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>'
             % (BASE, left_w, BASE, AXIS))
    b.append('<text x="0" y="%.1f" font-size="9.5" fill="%s">The whole flow, on one scale '
             '(0 to the original appropriation)</text>' % (BASE + 40, MUTED))

    # ---- RIGHT PANEL: the comparison, zoomed ---------------------------------------
    RX0 = left_w + 56
    values = [v for _, v, _ in compare]
    lo, hi = min(values), max(values)
    rmin = lo * 0.9
    rmax = hi * 1.08
    rscale = PANEL_H / (rmax - rmin)

    def ry(v):
        return BASE - (v - rmin) * rscale

    bx = RX0
    RGAP = 20
    for label, v, color in compare:
        y = ry(v)
        b.append('<rect x="%.1f" y="%.1f" width="%d" height="%.1f" fill="%s" rx="2"/>'
                 % (bx, y, rbw, BASE - y, color))
        b.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="700" '
                 'text-anchor="middle" fill="%s">%s</text>'
                 % (bx + rbw / 2, y - 6, INK, usd(v)))
        for li, line in enumerate(label.split('\n')):
            b.append('<text x="%.1f" y="%.1f" font-size="9.5" text-anchor="middle" '
                     'fill="%s">%s</text>'
                     % (bx + rbw / 2, BASE + 16 + li * 11, SECOND, esc(line)))
        bx += rbw + RGAP
    bx -= RGAP
    if bx > W:
        fail('the comparison panel is %.0fpx wide and runs off a %dpx chart' % (bx, W))
    b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>'
             % (RX0, BASE, bx, BASE, AXIS))
    gy = ry(lo)
    b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" '
             'stroke-dasharray="2,2"/>' % (RX0, gy, bx, gy, '#b3261e'))
    b.append('<text x="%.1f" y="%.1f" font-size="9.5" text-anchor="middle" fill="%s">'
             'zoomed to %s–%s</text>'
             % (RX0 + (bx - RX0) / 2, BASE + 40, MUTED, usdk(rmin), usdk(rmax)))
    b.append('<text x="%.1f" y="%.1f" font-size="10.5" font-weight="700" '
             'text-anchor="middle" fill="%s">%s</text>'
             % (RX0 + (bx - RX0) / 2, TOP - 6, '#b3261e', gap_text))

    body = ''.join(b)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="%s. %s" font-family=\'%s\'>\n'
            '<rect width="%d" height="%d" fill="%s"/>\n'
            '<text x="0" y="16" font-size="13" font-weight="700" fill="%s">%s</text>\n'
            '<text x="0" y="33" font-size="10.5" fill="%s">%s</text>\n%s\n</svg>\n'
            % (W, H, W, H, esc(title), esc(subtitle), FONT, W, H, SURFACE, INK, esc(title),
               SECOND, esc(subtitle), body))


# ======================================================================================
# FY2025 -- against the figure the School Committee was told, 17 September 2025
# ======================================================================================

FY25_MINUTES_TXT = os.path.join(SC_TEXT, '2025-09-17-minutes-7408.txt')
FY25_DISTRICT_FIGURE = 603885.97  # QUOTED, School Committee minutes, 17 September 2025.


def fy25_scope_check(rows):
    """The original appropriation here must equal the FY25 school figure the Town's own
    revenue-distribution workbook carries. Different document, same quantity, different
    stage -- rule 1 forbids comparing a budget to an actual, but this is budget to budget."""
    orig = sum(float(r['original_approp']) for r in rows)
    if not os.path.exists(REVDIST):
        fail('missing %s' % rel(REVDIST))
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


def fy25_sources(page):
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


def fy2025():
    fy = 2025
    DISTRICT_FIGURE = FY25_DISTRICT_FIGURE
    rows = ledger_rows(fy)
    orig, revdist_fy25 = fy25_scope_check(rows)
    t = totals(rows)
    diff = round(t['available'] - DISTRICT_FIGURE, 2)
    moved_out = round(abs(t['transfers']), 2)
    not_spent_against_original = round(t['available'] + moved_out, 2)
    bf = by_function(rows)
    pa = para_accounts(rows)
    page = page_of(FY25_MINUTES_TXT, '$603,885.97')

    fam = {r['family']: r for r in bf}
    instr = fam.get(2000, dict(total=0.0))
    ops = fam.get(4000, dict(total=0.0, salary=0.0, non_salary=0.0))
    concentration = instr['total'] + ops['total']
    concentration_share = 100 * concentration / t['available']

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

    chart_svg = waterfall_svg(
        t, '%s moved out mid-year →' % usdk(t['transfers']), 'Unspent\nat the close',
        [('Our ledger', t['available'], UNSPENT),
         ('The district,\n17 Sept 2025', DISTRICT_FIGURE, DISTRICT)],
        80, '%s gap' % usd(diff),
        'The FY2025 school budget, voted to closed',
        '%s not spent against the original appropriation — %s turned back, '
        '%s moved out mid-year — and %s more than the district told the '
        'School Committee'
        % (usd(not_spent_against_original), usd(t['available']), usd(moved_out), usd(diff)))

    # ---- the markdown ----
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
    function_table(bf, w)
    w('**Instruction and operations & maintenance together hold %s — %s of the %s '
      'unspent.** Almost no account ended overspent: the largest over-lines are in '
      'operations and maintenance and in assets, and both are small beside the unspent '
      'total.\n' % (usd(concentration), C.pct(concentration_share, 0), usd(t['available'])))
    w('---\n')
    w('## The paraprofessional accounts (function 2330)\n')
    w('Special-education paraprofessional lines ended under budget everywhere, and para '
      'budgets moved between lines mid-year in both directions.\n')
    para_table(pa, w)
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
    md = '\n'.join(b) + '\n'

    # ---- the payload ----
    tot_sal = round(sum(r['salary'] for r in bf), 2)
    tot_non = round(sum(r['non_salary'] for r in bf), 2)
    pay = dict(
        generated_by='scripts/build_fy25_school_surplus.py',
        about='What the closed FY2025 school general fund ledger shows was unspent and '
              'moved, beside the figure the School Committee was given on 17 September 2025.',
        grain='DOLLARS, department 300 (school general fund) only, FY2025 period 13 — '
              'the closed ledger, 415 accounts. Not a comparison of budget to actual: '
              'everything here is the same closed ledger read two ways.',
        fy=fy,
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
        by_function_totals=dict(salary=tot_sal, non_salary=tot_non,
                                total=round(tot_sal + tot_non, 2)),
        para_accounts=pa,
        sources=fy25_sources(page),
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
    return md, pay, chart_svg


# ======================================================================================
# FY2026 -- against the range the period-12 ledger allowed
# ======================================================================================

# The period-12 report: dept 300 of the Town Accountant's 1 September 2026 run, as
# extracted into munis-ledger.csv. fy26-closeout.md stated its range from these rows.
FY26_P12_DOC = 'sources/town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx'
FY26_P12_RUN = '1 September 2026'      # PROVENANCE-fy2026-p12.md: "Report generated: 09/01/2026"
FY26_P13_RUN = '6 October 2026'        # PROVENANCE-fy2023-fy2026-p13-school.md: "10/06/2026"
FY26_JULY_MINUTES = os.path.join(SC_TEXT, '2026-07-29-minutes-7930.txt')
# QUOTED from the 29 July 2026 minutes, each verbatim (whitespace collapsed). The two
# halves sit either side of a page break, so they are quoted separately rather than
# stitched -- rule 13: quote the source, never a rendering of it.
FY26_QUOTE_RETURNED = 'the approximately $600,000 that had been returned'
FY26_QUOTE_SHARE = 'estimated during the discussion to represent approximately 2.5% of the budget'
FY26_QUOTE_BELOW = ('he was confident the remaining amount would be well below that '
                    'figure')
FY26_QUOTE_EXPENSE = 'expense accounts were approximately 100.2% expended'
FY26_QUOTE_SALARY = ('expected final salary expenditures to be close to, but below, 100% of '
                     'the budget')
FY26_STATED_RETURNED = 600000.0       # the "$600,000" in the quote above
FY26_STATED_SHARE = 2.5               # the "2.5%" in the quote above
FY26_STATED_EXPENSE_PCT = 100.2       # the "100.2%" in the quote above
FY26_AGENDA_ITEM = 'FY26 Year End Budget review'


def fy26_p12_rows():
    if not os.path.exists(P12_LEDGER):
        fail('missing %s' % rel(P12_LEDGER))
    out = []
    with open(P12_LEDGER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if (r['fy'] == '2026' and r['period'] == '12' and r['fund'] == '0100'
                    and r['account_type'] == 'expense' and r['level'] == 'account'):
                out.append(r)
    if not out:
        fail('munis-ledger.csv holds no FY2026 period 12 general fund expense rows')
    docs = {r['doc_id'] for r in out}
    if docs != {FY26_P12_DOC}:
        fail('FY2026 period 12 rows come from %s, expected only %s' % (sorted(docs),
                                                                       FY26_P12_DOC))
    return out


def fy26_p12_totals(rows):
    t = dict(original=0.0, transfers=0.0, revised=0.0, expended=0.0, encumbered=0.0,
             available=0.0)
    for r in rows:
        for k in t:
            t[k] += float(r[k])
    return {k: round(v, 2) for k, v in t.items()}


def fy26_compare(p12_rows, p13_rows):
    """Account by account, period 12 to period 13. The join is on (org, object), which is
    what makes a MUNIS account unique; it must match every period-12 account, or this
    refuses -- a join that matches nothing looks exactly like nothing having changed."""
    P12_KEYS = ('original', 'transfers', 'revised', 'expended', 'encumbered', 'available')
    P13_KEYS = ('original_approp', 'transfers_adjustments', 'revised_budget', 'ytd_expended',
                'encumbrances', 'available_budget')
    p13 = {}
    for r in p13_rows:
        k = (r['org'], r['obj'])
        if k in p13:
            fail('period 13 carries two accounts keyed %s/%s' % k)
        p13[k] = r
    changed, matched = [], 0
    p12_keys = set()
    for r in p12_rows:
        k = (r['org'], r['object'])
        p12_keys.add(k)
        q = p13.get(k)
        if q is None:
            fail('period-12 account %s/%s (%s) is not in the period-13 report'
                 % (k[0], k[1], r['name']))
        matched += 1
        a = [round(float(r[x]), 2) for x in P12_KEYS]
        b = [round(float(q[x]), 2) for x in P13_KEYS]
        if a != b:
            changed.append(dict(
                org=k[0], obj=k[1], account=q['account'], description=q['description'].strip(),
                **{'%s_p12' % n: v for n, v in zip(P12_KEYS, a)},
                **{'%s_p13' % n: v for n, v in zip(P12_KEYS, b)}))
    # An account period 13 prints that period 12 suppressed must be all zeros, or it is a
    # change too. Period 12 was run with `Suppress zero bal accts: Y`.
    for k, q in p13.items():
        if k in p12_keys:
            continue
        if any(round(float(q[x]), 2) != 0 for x in P13_KEYS):
            changed.append(dict(org=k[0], obj=k[1], account=q['account'],
                                description=q['description'].strip(), new_at_p13=True,
                                **{'%s_p13' % n: round(float(q[x]), 2)
                                   for n, x in zip(P12_KEYS, P13_KEYS)}))
    return matched, changed


def fy26_open_encumbrances(rows):
    out = []
    for r in rows:
        enc = round(float(r['encumbrances']), 2)
        if enc:
            out.append(dict(org=r['org'], obj=r['obj'], account=r['account'],
                            description=r['description'].strip(),
                            family=family_of(r), encumbered=enc,
                            available=round(float(r['available_budget']), 2)))
    out.sort(key=lambda d: (-d['encumbered'], d['org'], d['obj']))
    return out


def fy26_minutes_index():
    """Which School Committee meetings since the July meeting the archive's catalogue of
    the Town's AgendaCenter lists, and whether minutes are among them."""
    out = {}
    with open(MEETING_INDEX, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['board'] != 'School Committee' or r['date'] < '2026-07-30':
                continue
            out.setdefault(r['date'], set()).add(r['kind'])
    return out


def fy26_agendas_with_item():
    hits = []
    for name in sorted(os.listdir(SC_TEXT)):
        if not (name.startswith('2026-') and '-agenda-' in name and name.endswith('.txt')):
            continue
        if name[:10] < '2026-07-30':
            continue
        text = open(os.path.join(SC_TEXT, name), encoding='utf-8').read()
        if FY26_AGENDA_ITEM in text:
            hits.append(name)
    return hits


def long_date(iso):
    import datetime
    d = datetime.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, d.strftime('%B'), d.year)


def fy2026():
    fy = 2026
    slug = paths(fy)['slug']
    rows = ledger_rows(fy)
    t = totals(rows)
    p12_rows = fy26_p12_rows()
    p12_dept = [r for r in p12_rows if r['dept'] == '300']
    p12 = fy26_p12_totals(p12_dept)
    # SCOPE: the voted appropriation is the same quantity in two independent runs.
    if t['original'] != p12['original']:
        fail('SCOPE: period-13 original appropriation %.2f is not period 12\'s %.2f'
             % (t['original'], p12['original']))
    matched, changed = fy26_compare(p12_dept, rows)
    if matched != len(p12_dept):
        fail('matched %d of %d period-12 accounts' % (matched, len(p12_dept)))
    other_depts = sorted({r['dept'] for r in p12_rows if r['dept'].startswith('30')
                          and r['dept'] != '300'})
    dept301 = round(sum(float(r['original']) for r in p12_rows if r['dept'] == '301'), 2)

    floor12 = p12['available']
    ceiling12 = round(p12['available'] + p12['encumbered'], 2)
    ceiling13 = round(t['available'] + t['encumbered'], 2)
    moved = round(t['available'] - floor12, 2)
    spent_moved = round(t['expended'] - p12['expended'], 2)
    above_floor = moved
    below_ceiling = round(ceiling12 - t['available'], 2)
    opens = fy26_open_encumbrances(rows)
    n_open = len(opens)
    bf = by_function(rows, with_encumbered=True)
    pa = para_accounts(rows)
    fam = {r['family']: r for r in bf}
    fy25_enc = totals(ledger_rows(2025))['encumbered']

    # Shares of the revised budget, beside the minutes' "approximately 2.5%".
    floor_share = 100 * t['available'] / t['revised']
    ceiling_share = 100 * ceiling13 / t['revised']

    # Salary vs non-salary, for the 29 July statement about "expense accounts".
    def split(sal):
        rr = [r for r in rows if r['obj'].startswith('51') == sal]
        rv = sum(float(r['revised_budget']) for r in rr)
        ex = sum(float(r['ytd_expended']) for r in rr)
        en = sum(float(r['encumbrances']) for r in rr)
        return dict(revised=round(rv, 2), expended=round(ex, 2), encumbered=round(en, 2),
                    spent_pct=round(100 * ex / rv, 1),
                    committed_pct=round(100 * (ex + en) / rv, 1))
    salary, non_salary = split(True), split(False)

    # Where it sat: rank the families on each measure from the data.
    by_unspent = sorted(bf, key=lambda r: -r['total'])
    by_open = sorted(bf, key=lambda r: -r['encumbered'])
    top_u, next_u = by_unspent[0], by_unspent[1]
    top_o, next_o = by_open[0], by_open[1]
    if top_u['family'] != top_o['family']:
        fail('the family holding the most unspent (%d) is not the one holding the most '
             'still encumbered (%d) -- the conclusion that says they are the same must be '
             'rewritten' % (top_u['family'], top_o['family']))

    # The paraprofessional lines.
    pa_sped = [r for r in pa if r['org'] in SPED_PARA_ORGS]
    sped_over = [r for r in pa_sped if r['available'] < -0.5]
    sped_net = round(sum(r['available'] for r in pa_sped), 2)
    sped_in = [r for r in pa_sped if r['transfers'] > 0]
    kinder = [r for r in pa if r['org'] in ('S2032121', 'S2032131')]
    kinder_spent = round(sum(r['expended'] for r in kinder), 2)
    kinder_budget = round(sum(r['revised'] for r in kinder), 2)

    # The meeting record.
    p_ret = page_of(FY26_JULY_MINUTES, FY26_QUOTE_RETURNED)
    p_below = page_of(FY26_JULY_MINUTES, FY26_QUOTE_BELOW)
    page_of(FY26_JULY_MINUTES, FY26_QUOTE_SHARE)
    p_exp = page_of(FY26_JULY_MINUTES, FY26_QUOTE_EXPENSE)
    page_of(FY26_JULY_MINUTES, FY26_QUOTE_SALARY)
    agendas = fy26_agendas_with_item()
    if not agendas:
        fail('no School Committee agenda since July carries "%s" -- the section that says '
             'two did must be rewritten' % FY26_AGENDA_ITEM)
    idx = fy26_minutes_index()
    agenda_dates = [a[:10] for a in agendas]
    no_minutes = [d for d in agenda_dates if 'minutes' not in idx.get(d, set())]
    with_minutes = [d for d in agenda_dates if d not in no_minutes]
    agenda_dates_text = ' and '.join(long_date(d) for d in agenda_dates)

    if len(changed) == 1:
        ch = changed[0]
        changed_text = ('%s of a purchase order released in one account, %s `%s` %s'
                        % (usd2(round(ch['encumbered_p12'] - ch['encumbered_p13'], 2)),
                           ch['description'].title(), ch['org'], ch['obj']))
    else:
        changed_text = '%d accounts' % len(changed)


    if spent_moved != 0:
        fail('spending moved between period 12 and period 13 (%s); the report says it did '
             'not and must be rewritten' % usd2(spent_moved))

    rws = [
        conclusion(
            id='period-13-landed-at-the-bottom-of-the-june-range',
            claim='The FY26 school surplus stands at %s, %s more than the June ledger showed.'
                  % (usd(t['available']), usd2(moved)),
            so_what='Not one of the %s accounts changed its spending between the two runs.'
                    % C.num(len(rows)),
            figures={'p13': figure(t['available'], usd(t['available']),
                                   'unspent and uncommitted at period 13'),
                     'moved': figure(moved, usd2(moved)),
                     'accounts': figure(len(rows), C.num(len(rows)), 'accounts'),
                     'floor': figure(floor12, usd(floor12)),
                     'ceiling': figure(ceiling12, usd(ceiling12))},
            figure='p13', kind='measured', bearing='sizes',
            detail='The period-12 report run on %s allowed the year to close anywhere '
                   'between %s and %s. The period-13 report run on %s lands at the bottom '
                   'of that range: the only change between them is %s of a purchase order '
                   'released in one supplies account.'
                   % (FY26_P12_RUN, usd(floor12), usd(ceiling12), FY26_P13_RUN, usd2(moved)),
            basis='`sources/data/munis-school-ytd.csv`, FY2026 period 13, report gf-school, '
                  'type E; `sources/data/munis-ledger.csv`, FY2026 period 12, department '
                  '300; joined account by account on org and object.',
            not_shown='Whether period 13 is complete: the report was run while purchase '
                      'orders were still open.',
            allow=(FY26_P12_RUN, FY26_P13_RUN, 'FY26', 'period-12', 'period-13'),
        ),
        conclusion(
            id='still-committed-to-open-purchase-orders',
            claim='%s is still committed to open purchase orders, across %s accounts.'
                  % (usd(t['encumbered']), C.num(n_open)),
            so_what='Paid, the surplus stays at %s; released, it can rise to at most %s.'
                    % (usd(t['available']), usd(ceiling13)),
            figures={'enc': figure(t['encumbered'], usd(t['encumbered']),
                                   'still encumbered at period 13'),
                     'n': figure(n_open, C.num(n_open), 'accounts'),
                     'p13': figure(t['available'], usd(t['available'])),
                     'ceiling': figure(ceiling13, usd(ceiling13)),
                     'top1': figure(opens[0]['encumbered'], usd(opens[0]['encumbered'])),
                     'top2': figure(opens[1]['encumbered'], usd(opens[1]['encumbered'])),
                     'fy25': figure(fy25_enc, usd(fy25_enc))},
            figure='enc', kind='measured', bearing='sizes',
            detail='The two largest are %s (%s) and %s (%s). The FY2025 report of the same '
                   'department, run the same day, shows %s encumbered: that year is fully '
                   'closed and this one is not.'
                   % (opens[0]['description'].lower(), usd(opens[0]['encumbered']),
                      opens[1]['description'].lower(), usd(opens[1]['encumbered']),
                      usd(fy25_enc)),
            basis='`munis-school-ytd.csv`, FY2026 and FY2025 period 13, the encumbrances '
                  'column, department 300.',
            not_shown='Which orders will be paid, released, or carried into the next year.',
            allow=('FY2025',),
        ),
        conclusion(
            id='what-the-school-committee-was-told-in-july',
            claim='In July the Committee heard FY26 would return well below FY25’s %s.'
                  % usd(FY26_STATED_RETURNED),
            so_what='The floor, %s, is below it; the ceiling, %s, is above it.'
                    % (usd(t['available']), usd(ceiling13)),
            figures={'stated': figure(FY26_STATED_RETURNED, usd(FY26_STATED_RETURNED),
                                      'returned in FY25, as stated in the minutes'),
                     'p13': figure(t['available'], usd(t['available'])),
                     'ceiling': figure(ceiling13, usd(ceiling13)),
                     'share_stated': figure(FY26_STATED_SHARE, C.pct(FY26_STATED_SHARE)),
                     'floor_share': figure(floor_share, C.pct(floor_share)),
                     'ceiling_share': figure(ceiling_share, C.pct(ceiling_share))},
            figure='stated', kind='measured', bearing='sizes',
            detail='The minutes of 29 July 2026 record the business manager as "confident '
                   'the remaining amount would be well below that figure" — the FY25 '
                   'return, put at about %s of the budget. As a share of FY26’s revised '
                   'budget the floor is %s and the ceiling %s. Whether the statement holds '
                   'depends on the open purchase orders.'
                   % (C.pct(FY26_STATED_SHARE), C.pct(floor_share), C.pct(ceiling_share)),
            basis='School Committee minutes, 29 July 2026, pages %d to %d; '
                  '`munis-school-ytd.csv`, FY2026 period 13.' % (p_ret, p_below),
            not_shown='What the business manager meant by "that figure", the dollars or the '
                      'share; and a minute is a summary, not a transcript.',
            allow=('FY26', 'FY25', '29 July 2026'),
        ),
        conclusion(
            id='operations-and-maintenance-holds-the-most-of-both',
            claim='Operations & maintenance holds %s of the surplus and %s of what is still open.'
                  % (usd(top_u['total']), usd(top_u['encumbered'])),
            so_what='Next largest: %s, %s unspent; %s, %s still open.'
                    % (next_u['label'], usd(next_u['total']),
                       next_o['label'], usd(next_o['encumbered'])),
            figures={'ops': figure(top_u['total'], usd(top_u['total']),
                                   'unspent in operations & maintenance (function 4000s)'),
                     'ops_enc': figure(top_u['encumbered'], usd(top_u['encumbered'])),
                     'next_u': figure(next_u['total'], usd(next_u['total'])),
                     'next_o': figure(next_o['encumbered'], usd(next_o['encumbered'])),
                     'sal': figure(top_u['salary'], usd(top_u['salary'])),
                     'non': figure(top_u['non_salary'], usd(top_u['non_salary']))},
            figure='ops', kind='measured', bearing='sizes',
            detail='Of the operations & maintenance surplus, %s is salary and %s is not. '
                   'The Town’s explanation for FY25’s surplus was unfilled facilities '
                   'posts; nothing in this ledger says whether FY26 is the same story — '
                   'it shows dollars by account, not posts.'
                   % (usd(top_u['salary']), usd(top_u['non_salary'])),
            basis='`munis-school-ytd.csv`, FY2026 period 13, available_budget and '
                  'encumbrances grouped by the 4th segment of the account string.',
            not_shown='Why any of it was left unspent. A dollar is not a post (rule 7, '
                      'rule 11).',
            allow=('FY25', 'FY26'),
        ),
    ]

    compare = [('June ledger,\nfloor', floor12, MOVED),
               ('Period 13,\n6 Oct 2026', t['available'], UNSPENT),
               ('June ledger,\nceiling', ceiling12, CEILING)]
    chart_svg = waterfall_svg(
        t, '%s moved into the budget mid-year, net' % usdk(t['transfers']),
        'Unspent\nat period 13',
        compare, 60, '%s still open' % usd(t['encumbered']),
        'The FY2026 school budget, voted to period 13',
        '%s unspent at period 13 — %s above the June floor of %s; %s still '
        'encumbered, so at most %s' % (usd(t['available']), usd2(moved), usd(floor12),
                                       usd(t['encumbered']), usd(ceiling13)),
        note_below=True)

    # ---- the markdown ----
    b = []
    w = b.append
    w('# The FY26 school surplus, from the period-13 ledger\n')
    w('**What the school general fund’s period-13 ledger, run %s, shows was left '
      'unspent in FY2026 — set against the range the June ledger allowed and what the '
      'School Committee was told.**\n' % FY26_P13_RUN)
    w('---\n')
    w('## The short version\n')
    w('![The FY2026 school budget stepping from the %s voted appropriation to %s unspent '
      'at period 13, beside the period-12 floor of %s and ceiling of %s; %s is still '
      'encumbered.](charts/%s-waterfall.svg)\n'
      % (usd0(t['original']), usd0(t['available']), usd0(floor12), usd0(ceiling12),
         usd0(t['encumbered']), slug))
    w('**%s was unspent and uncommitted in the school general fund at period 13 of '
      'FY2026**, of a revised budget of %s (%s voted, %s %s during the year).\n'
      % (usd(t['available']), usd(t['revised']), usd(t['original']),
         usd(abs(t['transfers'])), 'moved in' if t['transfers'] > 0 else 'moved out'))
    w('**It landed at the bottom of the period-12 range: %s above the %s the June ledger '
      'showed.** Spending did not change by a cent in any of the %s accounts between the '
      'run of %s and the run of %s. The one change was %s.\n'
      % (usd2(moved), usd(floor12), C.num(len(rows)), FY26_P12_RUN, FY26_P13_RUN,
         changed_text))
    w('**It is not final. %s is still encumbered — committed to open purchase orders — '
      'across %s accounts.** Paid, the surplus stays at %s; released, it rises to at most '
      '%s, the same ceiling the June ledger gave. The FY2025 report of the same department, '
      'run the same day, shows %s encumbered.\n'
      % (usd(t['encumbered']), C.num(n_open), usd(t['available']), usd(ceiling13),
         usd(fy25_enc)))
    w('---\n')
    w('## Against the period-12 range\n')
    w('`fy26-closeout.md` read the period-12 report and said the year would close between '
      '%s (every open order paid) and %s (every open order released). Department 300, the '
      'same %s accounts, both runs:\n' % (usd(floor12), usd(ceiling12), C.num(len(p12_dept))))
    w('| | period 12, run %s | period 13, run %s | change |\n|---|---:|---:|---:|'
      % (FY26_P12_RUN, FY26_P13_RUN))
    for k, label in (('original', 'Original appropriation'),
                     ('transfers', 'Transfers and adjustments'),
                     ('revised', 'Revised budget'), ('expended', 'Expended'),
                     ('encumbered', 'Encumbered'), ('available', '**Unspent**')):
        w('| %s | %s | %s | %s |' % (label, usd2(p12[k]), usd2(t[k]),
                                       usd2(round(t[k] - p12[k], 2))))
    w('| Ceiling (unspent + encumbered) | %s | %s | %s |\n'
      % (usd2(ceiling12), usd2(ceiling13), usd2(round(ceiling13 - ceiling12, 2))))
    w('**%s of %s accounts changed.**' % (C.num(len(changed)), C.num(len(p12_dept))))
    for ch in changed:
        w('`%s` %s — encumbered %s at period 12, %s at period 13; unspent %s, then %s.'
          % (ch['account'], ch['description'], usd2(ch.get('encumbered_p12', 0)),
             usd2(ch['encumbered_p13']), usd2(ch.get('available_p12', 0)),
             usd2(ch['available_p13'])))
    w('')
    w('No account’s spending moved, net, so no late invoice posted to the year between '
      'the two runs; and no other encumbrance was paid or released. The period-13 report '
      'is the year as the system held it on %s, not necessarily the year as it will '
      'close.\n' % FY26_P13_RUN)
    w('---\n')
    w('## What the School Committee was told\n')
    w('The minutes of **29 July 2026** (page %d) record the business manager reporting that '
      '"%s, while salary accounts were still being reconciled", and that he "%s". The '
      'Committee discussed "%s, which was %s"; asked how FY26 would compare, "%s" (page %d).\n'
      % (p_exp, FY26_QUOTE_EXPENSE, FY26_QUOTE_SALARY, FY26_QUOTE_RETURNED,
         FY26_QUOTE_SHARE, FY26_QUOTE_BELOW, p_below))
    w('Set beside the period-13 ledger — a statement is evidence of what was said, not of '
      'what happened:\n')
    w('| | stated, 29 July 2026 | period 13 |\n|---|---|---:|')
    w('| What is left | "well below" about %s, or about %s of the budget | %s to %s; '
      '%s to %s of the revised budget |'
      % (usd(FY26_STATED_RETURNED), C.pct(FY26_STATED_SHARE), usd(t['available']),
         usd(ceiling13), C.pct(floor_share), C.pct(ceiling_share)))
    w('| Salary lines | "close to, but below, 100%%" | %s spent |'
      % C.pct(salary['spent_pct']))
    w('| "Expense accounts" | about %s expended | non-salary lines: %s spent, %s spent or '
      'encumbered |\n' % (C.pct(FY26_STATED_EXPENSE_PCT), C.pct(non_salary['spent_pct']),
                          C.pct(non_salary['committed_pct'])))
    w('The floor is below the July expectation and the ceiling above it, so the open '
      'purchase orders decide whether it holds. *Reading "expense accounts" as every '
      'non-salary line is ours; the minutes do not define it, and the statement was made '
      'more than two months before this run, so the two rows are not a test of each '
      'other.*\n')
    if no_minutes:
        w('The agendas of %s carried "%s". The archive’s catalogue of the Town’s postings '
          'lists %s for %s, so there is no written record here of what was said under '
          'that item.\n'
          % (agenda_dates_text, FY26_AGENDA_ITEM,
             'no minutes' if len(no_minutes) == len(agenda_dates) else 'minutes for some',
             'either meeting' if len(no_minutes) == len(agenda_dates) == 2
             else 'those meetings'))
    else:
        w('The agendas of %s carried "%s"; minutes for those meetings are now held and '
          'have not been read into this report.\n' % (agenda_dates_text, FY26_AGENDA_ITEM))
    w('---\n')
    w('## What is still open\n')
    w('%s accounts carry %s of purchase orders not yet paid or released. The three largest '
      'hold %s of it.\n'
      % (C.num(n_open), usd(t['encumbered']),
         usd(sum(o['encumbered'] for o in opens[:3]))))
    w('| account | description | function | encumbered | unspent |\n|---|---|---|---:|---:|')
    for o in opens:
        w('| `%s` %s | %s | %d %s | %s | %s |'
          % (o['org'], o['obj'], o['description'].title(), o['family'],
             FAMILY_LABEL.get(o['family'], 'unclassified'), usd2(o['encumbered']),
             usd2(o['available'])))
    w('| | | | **%s** | |\n' % usd2(t['encumbered']))
    w('---\n')
    w('## Where it sat, by DESE function\n')
    w('Net unspent at period 13, by function family (the account string’s 4th segment, '
      'grouped to the thousands) and whether the line is salary (object code starting `51`), '
      'with what is still encumbered beside it.\n')
    function_table(bf, w, with_encumbered=True)
    overs = [r for r in bf if r['total'] < 0]
    w('**%s holds the most of both: %s unspent and %s still open.** %s'
      % (top_u['label'].capitalize(), usd(top_u['total']), usd(top_u['encumbered']),
         ('%s ended over, net: %s.' % (
             ' and '.join(r['label'] for r in overs).capitalize(),
             ', '.join('%s %s' % (r['label'], usd(r['total'])) for r in overs)))
         if overs else 'No family ended over, net.'))
    w('')
    w('---\n')
    w('## The paraprofessional accounts (function 2330)\n')
    w('%s of %s special-education paraprofessional lines ended over their revised budget, '
      '%s over between them, after mid-year transfers into %s of them. Two kindergarten '
      'accounts with %s budgeted spent %s; `fy26-closeout.md` §3 reads them.\n'
      % (C.num(len(sped_over)), C.num(len(pa_sped)), usd(abs(sped_net)),
         C.num(len(sped_in)), usd(kinder_budget), usd(kinder_spent)))
    para_table(pa, w)
    w('---\n')
    w('## What it does not show\n')
    w('- Whether the %s still encumbered will be paid, released, or carried into FY2027 — '
      'the ledger shows the commitment, not its fate.\n' % usd(t['encumbered']))
    w('- What any dollar was spent on, or when — no journal.\n')
    w('- Where the %s moved into the department came from — net per account, no '
      'counterparty.\n' % usd(abs(t['transfers'])))
    if other_depts:
        w('- Department%s %s — the separate %s curriculum adoption appropriation in the '
          'period-12 report — is outside this report, and its period-13 figures are not '
          'held.\n' % ('' if len(other_depts) == 1 else 's', ', '.join(other_depts),
                       usd(dept301)))
    w('- What free cash the Town will certify. The school figure is one input to it, '
      'and certification is a separate step.\n')
    w('---\n')
    w('## Closes with\n')
    w('The FY2026 period-13 report run again after the year-end close is complete, and the '
      'Town Accountant’s list of FY2026 encumbrances carried forward into FY2027, by '
      'account.\n')
    w('---\n')
    w('## Sources\n')
    w('| | |\n|---|---|')
    w('| Period 13 | `munis-school-ytd.csv`, FY2026 period 13, report gf-school, type E, '
      '%s accounts; run %s |' % (C.num(len(rows)), FY26_P13_RUN))
    w('| Period 12 | `munis-ledger.csv`, FY2026 period 12, department 300, %s accounts; '
      'run %s |' % (C.num(len(p12_dept)), FY26_P12_RUN))
    w('| FY2025, for the encumbrance comparison | `munis-school-ytd.csv`, FY2025 period 13 |')
    w('| What the Committee was told | School Committee minutes, 29 July 2026, pages %d to '
      '%d |' % (min(p_exp, p_ret), p_below))
    w('| The year-end agenda item | School Committee agendas, %s |' % agenda_dates_text)
    md = '\n'.join(b) + '\n'

    # ---- the payload ----
    tot = dict(salary=round(sum(r['salary'] for r in bf), 2),
               non_salary=round(sum(r['non_salary'] for r in bf), 2),
               encumbered=round(sum(r['encumbered'] for r in bf), 2))
    tot['total'] = round(tot['salary'] + tot['non_salary'], 2)
    srcs = [
        held_source('town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-school.xlsx',
                    'munis-school-ytd', 'Town of Lunenburg — Town Accountant',
                    'MUNIS year-to-date budget report, department 300 (school general '
                    'fund), FY2026 period 13, run %s. Obtained by the records request of '
                    '4 September 2026; see PROVENANCE-fy2023-fy2026-p13-school.md.'
                    % FY26_P13_RUN),
        held_source('town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx',
                    'munis-ledger', 'Town of Lunenburg — Town Accountant',
                    'MUNIS year-to-date budget report, every general fund department, '
                    'FY2026 period 12, run %s; sent by the Town Manager. The report '
                    'fy26-closeout.md was written from. See PROVENANCE-fy2026-p12.md.'
                    % FY26_P12_RUN),
        held_source('town-ledgers/expenses/glytdbud-expense-fy2025-p13-gf-school.xlsx',
                    'munis-school-ytd', 'Town of Lunenburg — Town Accountant',
                    'The FY2025 period-13 report of the same department, run the same day; '
                    'used only to compare what is still encumbered.'),
        held_source('meetings/school-committee/2026-07-29-minutes-7930.pdf',
                    'school_committee_minutes', 'Lunenburg School Committee',
                    'Minutes of 29 July 2026, pages %d to %d: "%s"; "%s"; "%s, which was '
                    '%s"; "%s".' % (min(p_exp, p_ret), p_below, FY26_QUOTE_EXPENSE,
                                    FY26_QUOTE_SALARY, FY26_QUOTE_RETURNED,
                                    FY26_QUOTE_SHARE, FY26_QUOTE_BELOW)),
    ] + [
        held_source('meetings/school-committee/%s' % a.replace('.txt', '.pdf'),
                    'school_committee_agendas', 'Lunenburg School Committee',
                    'Agenda of %s, item "%s (5 min)".' % (long_date(a[:10]),
                                                          FY26_AGENDA_ITEM))
        for a in agendas
    ]
    pay = dict(
        generated_by='scripts/build_school_surplus.py --fy 2026',
        about='What the FY2026 school general fund ledger at period 13 shows was left '
              'unspent, against the range the period-12 ledger allowed and what the School '
              'Committee was told in July 2026.',
        grain='DOLLARS, department 300 (school general fund) only, FY2026 period 13 as run '
              'on %s, %s accounts — compared account by account with the period-12 run of '
              '%s. Not a comparison of budget to actual: one ledger at two periods.'
              % (FY26_P13_RUN, C.num(len(rows)), FY26_P12_RUN),
        fy=fy,
        stats=[
            dict(value=usd0(t['available']), tone='var(--series-cost)',
                 label='unspent and uncommitted at period 13, FY2026 school general fund, '
                       'of %s revised budget' % usd0(t['revised'])),
            dict(value=usd0(t['encumbered']),
                 label='still encumbered in %s accounts — the most the surplus can still rise'
                       % C.num(n_open)),
            dict(value=usd2(moved),
                 label='the whole change from the June ledger — no spending moved'),
        ],
        totals=t,
        period12=dict(totals=p12, run=FY26_P12_RUN, doc=FY26_P12_DOC,
                      accounts=len(p12_dept)),
        range=dict(floor_p12=floor12, ceiling_p12=ceiling12, p13=t['available'],
                   ceiling_p13=ceiling13, above_floor=above_floor,
                   below_ceiling=below_ceiling),
        moved_since_p12=moved,
        spending_moved_since_p12=spent_moved,
        accounts_changed=changed,
        open_encumbrances=opens,
        fy25_encumbered=fy25_enc,
        salary_split=dict(salary=salary, non_salary=non_salary),
        stated=dict(date='2026-07-29', returned_fy25=FY26_STATED_RETURNED,
                    share_fy25_pct=FY26_STATED_SHARE,
                    expense_accounts_pct=FY26_STATED_EXPENSE_PCT,
                    quotes=[FY26_QUOTE_EXPENSE, FY26_QUOTE_SALARY, FY26_QUOTE_RETURNED,
                            FY26_QUOTE_SHARE, FY26_QUOTE_BELOW],
                    floor_share_pct=round(floor_share, 2),
                    ceiling_share_pct=round(ceiling_share, 2)),
        year_end_agenda=dict(item=FY26_AGENDA_ITEM, dates=agenda_dates,
                             minutes_held=with_minutes),
        waterfall=dict(voted=t['original'], moved_out=t['transfers'], revised=t['revised'],
                       spent=t['expended'], unspent=t['available'],
                       compare=[dict(label=l.replace('\n', ' '), value=v)
                                for l, v, _ in compare],
                       gap_label='still encumbered', gap=t['encumbered']),
        by_function=bf,
        by_function_totals=tot,
        para_accounts=pa,
        sources=srcs,
        not_established=[
            'Whether the %s still encumbered will be paid, released, or carried into '
            'FY2027.' % usd(t['encumbered']),
            'Where the %s moved into the department during the year came from — net per '
            'account, no counterparty.' % usd(abs(t['transfers'])),
            'What "expense accounts" meant in the 29 July 2026 minutes, and so whether the '
            'ledger agrees with "approximately 100.2% expended".',
            'Why operations & maintenance was left unspent — dollars are not posts.',
            'What was said under "%s" on %s: no minutes for %s are held.'
            % (FY26_AGENDA_ITEM, agenda_dates_text,
               'either meeting' if len(no_minutes) == 2 else 'those meetings')
            if no_minutes else
            'Minutes for the year-end budget review meetings are held and unread here.',
        ],
        conclusions=emit(slug, rws),
    )
    return md, pay, chart_svg


STORIES = {2025: fy2025, 2026: fy2026}


def run(fy, check):
    p = paths(fy)
    md, pay, chart_svg = STORIES[fy]()
    pay_text = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if check:
        def cur(path):
            return open(path, encoding='utf-8').read() if os.path.exists(path) else ''
        bad = [os.path.basename(path) for path, gen in (
            (p['md'], md), (p['payload'], pay_text), (p['chart'], chart_svg),
        ) if gen != cur(path)]
        if bad:
            print('STALE %s' % ', '.join(bad), file=sys.stderr)
            return 1
        print('%s.md, .json and the chart are current' % p['slug'])
        return 0
    os.makedirs(os.path.dirname(p['chart']), exist_ok=True)
    for path, text in ((p['md'], md), (p['payload'], pay_text), (p['chart'], chart_svg)):
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(text)
        os.replace(tmp, path)
    print('wrote %s, %s and %s' % (rel(p['md']), rel(p['payload']), rel(p['chart'])))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--fy', type=int, choices=YEARS)
    g.add_argument('--all', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    rc = 0
    for fy in (YEARS if a.all else (a.fy,)):
        rc |= run(fy, a.check)
    return rc


if __name__ == '__main__':
    sys.exit(main())
