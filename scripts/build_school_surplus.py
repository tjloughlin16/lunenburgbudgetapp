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
payload names it as its generator. That payload was held byte-identical until 8 October
2026, when both years gained the same "why there was money left over" and "was it thrift?"
sections from `why()` -- one presentation for both reports (rule 7d) -- and FY25 changed
on purpose.

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
# The FIVE special-education paraprofessional lines. S2511131 (printed "PARAPROFESSIONALS")
# is the ACE program's: the district's FY2027 workbook names it "ACE Special Ed
# Paraprofessionals" at the same FY2026 budget, $43,742, and the 29 July 2026 minutes list
# "the ACE, Primary School, Elementary School, Middle School and High School Special
# Education Paraprofessional accounts". Until 10 October 2026 this tuple had four, and the
# FY26 page said "4 of 4" lines ran over; it was five of five.
SPED_PARA_ORGS = ('S2511131', 'S2512131', 'S2514131', 'S2515131', 'S2516131')

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
# WHY THERE WAS MONEY LEFT OVER -- shared by every year, so both reports read alike
# ======================================================================================
#
# TJ, 8 October 2026: *"give some analysis on the reasons for the surplus ... in the short
# section, with some charts and graphs and easy to understand explanations"*; and then,
# *"the school leaders just said 'we were thrifty'. How do we confirm if that's accurate?"*
#
# Two halves, kept apart on purpose (rule 7):
#
#   * WHERE the money was left is MEASURED: every account goes into exactly one plain-
#     English category by the table below, and the categories are summed off the ledger.
#   * WHY it was left is not in the ledger at all. It comes only from a document that says
#     so, quoted verbatim and checked here against the archive's text, or it is printed as
#     a HYPOTHESIS with the one record that would settle it.
#
# THE CATEGORY TABLE -- one table, one place. First match wins. `func` is the DESE function
# code (the account string's 4th segment); `sal` is whether the object code starts `51`.
# `kind` is the thrift test: DISCRETIONARY lines are the ones a decision to spend less
# moves directly (supplies, materials, equipment, repairs and contracted upkeep, dues,
# travel, legal, other services); CIRCUMSTANTIAL lines follow staffing, placements,
# prices and enrolment (salaries, tuition, plan-required special-education services,
# transportation, utilities, insurance and benefits). That split is OURS, and the method
# section of each report says so.
CATEGORIES = (
    # key, label, kind, rule as printed in the method table, test(func, sal)
    ('teachers', 'Teachers & substitutes', 'circumstantial',
     'salary lines, functions 2300–2399 except 2330 (teachers, special-education teachers, '
     'specialists, substitutes, librarians)',
     lambda f, s: s and 2300 <= f < 2400 and f != 2330),
    ('counselors', 'Counselors & psychologists', 'circumstantial',
     'salary lines, functions 2700–2899 (guidance, social workers, psychologists)',
     lambda f, s: s and 2700 <= f < 2900),
    ('paras', 'Paraprofessionals', 'circumstantial',
     'salary lines, function 2330', lambda f, s: s and f == 2330),
    ('admin', 'Administrators & office staff', 'circumstantial',
     'salary lines, functions 1000–2299 (central office, directors, principals, secretaries)',
     lambda f, s: s and 1000 <= f < 2300),
    ('custodians', 'Custodians', 'circumstantial',
     'salary lines, functions 4000–4999', lambda f, s: s and 4000 <= f < 5000),
    ('other_staff', 'Nurses, coaches & other staff', 'circumstantial',
     'every other salary line (nurses, athletics, advisors, reserves)', lambda f, s: s),
    ('tuition', 'Out-of-district tuition', 'circumstantial',
     'functions 9000 and up (private and collaborative special-education tuition)',
     lambda f, s: f >= 9000),
    ('sped_services', 'Special-ed contracted services', 'circumstantial',
     'non-salary lines, functions 2310 and 2320 (contracted therapists, evaluations, '
     'tutoring)', lambda f, s: f in (2310, 2320)),
    ('transport', 'Transportation', 'circumstantial',
     'non-salary lines, function 3300 (regular and special-education buses)',
     lambda f, s: f == 3300),
    ('utilities', 'Heat, electricity & utilities', 'circumstantial',
     'non-salary lines, functions 4120 and 4130', lambda f, s: f in (4120, 4130)),
    ('benefits', 'Health insurance & benefits', 'circumstantial',
     'functions 5000–5999 (health insurance, Medicare, unemployment)',
     lambda f, s: 5000 <= f < 6000),
    ('buildings', 'Building & grounds upkeep', 'discretionary',
     'every other non-salary line in functions 4000–4999 (repairs, contracted maintenance, '
     'custodial and grounds supplies)', lambda f, s: 4000 <= f < 5000),
    ('equipment', 'Equipment & technology', 'discretionary',
     'functions 7000–7999, and 2451 (furniture, equipment, computers and their leases)',
     lambda f, s: 7000 <= f < 8000 or f == 2451),
    ('supplies', 'Supplies, services & everything else', 'discretionary',
     'every remaining non-salary line (classroom supplies, textbooks, professional '
     'development, legal, dues, athletics expenses, office services)',
     lambda f, s: True),
)
CAT_LABEL = {c[0]: c[1] for c in CATEGORIES}
# The same categories in two words, for a conclusion card's 95 characters.
CAT_SHORT = {'teachers': 'teachers', 'counselors': 'counselors', 'paras': 'paraprofessionals',
             'admin': 'administration', 'custodians': 'custodians',
             'other_staff': 'other staff', 'tuition': 'tuition',
             'sped_services': 'special-ed services', 'transport': 'transportation',
             'utilities': 'utilities', 'benefits': 'benefits', 'buildings': 'building upkeep',
             'equipment': 'equipment', 'supplies': 'supplies'}
CAT_KIND = {c[0]: c[2] for c in CATEGORIES}
KIND_LABEL = {'discretionary': 'discretionary — what spending less moves directly',
              'circumstantial': 'circumstantial — follows staff, placements, prices'}
HISTORY_YEARS = (2023, 2024, 2025, 2026)
EXPLAIN_MIN = 25000.0      # a category is explained in prose when it moved at least this
TOP_N, TOP_OVER_N = 8, 5

# Fund names exactly as the special-funds report PRINTS them, truncated where it truncates
# (the CSV carries the number only): `glytdbud-expense-fy2025-p13-special-school.xlsx` and
# the FY2026 report, the `Total <fund> <name>` rows -- e.g. row 411, "Total 2640 SPECIAL ED
# CIRCUIT BREAK". Rule 13: the printed label, never our gloss of it.
FUND_NAMES = {'1301': 'CHAPTER 658 REVOLVING FU', '1308': 'SCHOOL CHOICE REVOLVING',
              '1312': 'EXTENDED DAY REVOLVING F', '2200': 'SCHOOL LUNCH REVOLVING',
              '2622': 'FY25 FAMILY & COMMUNITY', '2640': 'SPECIAL ED CIRCUIT BREAK',
              '2681': 'COMP SCHOOL HEALTH SERV', '2713': 'FY25 TITLE I #305',
              '2781': 'FY22 #119 ESSER III GRAN'}

KIND_COLOR = {'discretionary': '#eb6834', 'circumstantial': '#3987e5'}
OVER_COLOR = '#b9b8ae'


def func_of(r):
    parts = r['account'].split('-')
    return int(parts[3]) if len(parts) > 3 else 0


def category_of(r):
    f, s = func_of(r), r['obj'].startswith('51')
    for key, _, _, _, test in CATEGORIES:
        if test(f, s):
            return key
    fail('no category for account %s' % r['account'])


def causes(rows):
    """Every category summed off the ledger. `unspent` is NET available (the surplus is a
    net figure); `under` and `over` are the accounts that ended under and over, kept apart
    so an offset inside a category is visible rather than netted away."""
    acc = {}
    for r in rows:
        k = category_of(r)
        a = acc.setdefault(k, dict(original=0.0, transfers=0.0, revised=0.0, expended=0.0,
                                   encumbered=0.0, unspent=0.0, under=0.0, over=0.0,
                                   accounts=0, functions=set()))
        av = float(r['available_budget'])
        a['original'] += float(r['original_approp'])
        a['transfers'] += float(r['transfers_adjustments'])
        a['revised'] += float(r['revised_budget'])
        a['expended'] += float(r['ytd_expended'])
        a['encumbered'] += float(r['encumbrances'])
        a['unspent'] += av
        if av > 0:
            a['under'] += av
        else:
            a['over'] += av
        a['accounts'] += 1
        a['functions'].add(func_of(r))
    out = []
    for key, label, kind, rule, _ in CATEGORIES:
        a = acc.get(key)
        if not a:
            continue
        row = {k: round(v, 2) for k, v in a.items() if isinstance(v, float)}
        row.update(key=key, label=label, kind=kind, accounts=a['accounts'],
                   functions=sorted(a['functions']))
        row['pct_of_revised'] = (round(100 * a['unspent'] / a['revised'], 1)
                                 if round(a['revised'], 2) else None)
        out.append(row)
    out.sort(key=lambda d: -d['unspent'])
    return out


def account_name(r):
    return '%s (%s)' % (r['description'].strip().title(), CAT_LABEL[category_of(r)].lower())


def top_accounts(rows):
    def one(r):
        return dict(account=r['account'], org=r['org'], obj=r['obj'],
                    name=account_name(r), category=category_of(r),
                    revised=round(float(r['revised_budget']), 2),
                    expended=round(float(r['ytd_expended']), 2),
                    encumbered=round(float(r['encumbrances']), 2),
                    available=round(float(r['available_budget']), 2))
    srt = sorted(rows, key=lambda r: (-float(r['available_budget']), r['account']))
    under = [one(r) for r in srt[:TOP_N] if float(r['available_budget']) > 0]
    over = [one(r) for r in reversed(srt[-TOP_OVER_N:]) if float(r['available_budget']) < 0]
    return under, over


def special_rows(fy):
    out = []
    with open(LEDGER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if (r['fiscal_year'] == str(fy) and r['period'] == str(PERIOD)
                    and r['report'] == 'special-school' and r['type'] == 'E'):
                out.append(r)
    if not out:
        fail('no FY%d special-school expense rows in %s' % (fy, rel(LEDGER)))
    return out


def special_overlap(fy, cats):
    """What the school's special funds (grants, revolving funds, the circuit breaker) spent
    on the SAME DESE function, salary or not, as a general-fund category. Rule 11: a
    general-fund line can look underspent because another fund paid. A special-fund account
    coded to a round thousand (2000, 0000) names no function and is NOT matched -- it is
    totalled separately and said to be unmatchable rather than guessed at."""
    by_cat = {c['key']: set(c['functions']) for c in cats}
    sal_of = {c['key']: c['key'] in ('teachers', 'counselors', 'paras', 'admin',
                                      'custodians', 'other_staff') for c in cats}
    matched, coarse = {}, 0.0
    for r in special_rows(fy):
        f, s = func_of(r), r['obj'].startswith('51')
        ex = float(r['ytd_expended'])
        if not round(ex, 2):
            continue
        if f % 1000 == 0:
            coarse += ex
            continue
        hit = None
        for key, funcs in by_cat.items():
            if f in funcs and sal_of[key] == s:
                hit = key
                break
        if hit is None:
            continue
        m = matched.setdefault(hit, {})
        m[r['fund']] = m.get(r['fund'], 0.0) + ex
    rows = []
    for key, funds in matched.items():
        for fund, ex in sorted(funds.items(), key=lambda kv: -kv[1]):
            if round(ex, 2):
                rows.append(dict(category=key, fund=fund, name=FUND_NAMES.get(fund),
                                 expended=round(ex, 2)))
    rows.sort(key=lambda d: -d['expended'])
    return rows, round(coarse, 2)


def history(cats_now, fy):
    """Net unspent by category for every closed year the CSV holds. Same lines left over
    every year reads as budgeted high, not run lean."""
    years = [y for y in HISTORY_YEARS]
    table = {}
    for y in years:
        for c in causes(ledger_rows(y)):
            table.setdefault(c['key'], {})[y] = c['unspent']
    out = []
    for c in cats_now:
        per = [table.get(c['key'], {}).get(y, 0.0) for y in years]
        out.append(dict(key=c['key'], label=c['label'], kind=c['kind'],
                        by_year=[round(v, 2) for v in per],
                        years_under=sum(1 for v in per if v > 0.5)))
    return dict(years=list(years), rows=out)


# ---- what the record says, per year ----------------------------------------------------

PRESS_RELEASE_KEY = ('town-budget/docs/4090-click-here-for-a-release-on-quot-understanding-'
                     'lunenburg-apos-s-fy27-budget-how-.pdf')
PRESS_RELEASE_TXT = os.path.join(ROOT, 'sources', 'town-budget', 'text',
                                 '4090-click-here-for-a-release-on-quot-understanding-'
                                 'lunenburg-apos-s-fy27-budget-how-.txt')
CAPTIONS = os.path.join(DATA, 'youtube-transcripts', 'school-committee')
CITE = 'https://lunenburgbudgetproject.org/docs/minutes/text/school-committee/%s'


def sc_minutes(name, date, quote, cats, note=''):
    return dict(kind='documented', board='School Committee', date=date, doc='minutes',
                text=os.path.join(SC_TEXT, name), quote=quote, categories=cats, note=note,
                cite=CITE % name, key='meetings/school-committee/%s' % name.replace('.txt', '.pdf'),
                town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_%s-%s'
                     % (date[5:7] + date[8:10] + date[:4], name.split('-')[-1][:-4]))


def caption(name, date, quote, cats, note=''):
    return dict(kind='caption', board='School Committee', date=date, doc='recording',
                # A caption is printed under "Was it thrift?" only, never as the explanation
                # of a category: it locates a moment, it is not a record (rule 7).
                text=os.path.join(CAPTIONS, name), quote=quote, categories=[], note=note,
                video='https://www.youtube.com/watch?v=%s' % name[11:-5])


RECORD = {
    2025: [
        dict(kind='documented', board='Town of Lunenburg', date='2026', doc='press release',
             text=PRESS_RELEASE_TXT, categories=['custodians', 'buildings'],
             quote='significant turnover and unfilled positions in the facilities department '
                   'resulted in unspent salaries and stalled maintenance projects',
             cite='https://lunenburgbudgetproject.org/docs/' + PRESS_RELEASE_KEY,
             key=PRESS_RELEASE_KEY,
             town='https://www.lunenburgma.gov/DocumentCenter/View/4090',
             note='The Town’s release “Understanding Lunenburg’s FY27 Budget”, naming '
                  'the first of two causes of the FY25 school surplus.'),
        dict(kind='documented', board='Town of Lunenburg', date='2026', doc='press release',
             text=PRESS_RELEASE_TXT, categories=['paras'],
             quote='several paraprofessional salaries were ultimately covered by newly '
                   'identified grants',
             cite='https://lunenburgbudgetproject.org/docs/' + PRESS_RELEASE_KEY,
             key=PRESS_RELEASE_KEY,
             town='https://www.lunenburgma.gov/DocumentCenter/View/4090',
             note='The same release, the second cause.'),
        sc_minutes('2025-09-03-minutes-7385.txt', '2025-09-03',
                   'a discussion of transfer accounts regarding a double budget amount for '
                   'paraprofessionals in the amount of $243,000', ['paras']),
        sc_minutes('2025-09-17-minutes-7408.txt', '2025-09-17',
                   'double booking of the para salaries, the music program and supply line '
                   'cuts', ['paras', 'supplies']),
        caption('2026-02-04-HsjpFotE9hc.json', '2026-02-04',
                'We are on a budget freeze', ['supplies', 'equipment', 'buildings'],
                note='A forum on the FY2025 surplus; a speaker recounting what teachers '
                     'were told.'),
    ],
    2026: [
        sc_minutes('2026-07-29-minutes-7930.txt', '2026-07-29',
                   '$81,075.96 from the High School Special Education Resource Room Teacher '
                   'account to Hospital Tutoring and the ACE, Primary School, Elementary '
                   'School, Middle School and High School Special Education Paraprofessional '
                   'accounts to cover overages in those areas', ['teachers', 'paras']),
        sc_minutes('2026-07-29-minutes-7930.txt', '2026-07-29',
                   'the funds were associated with a leave of absence', ['teachers']),
        sc_minutes('2026-07-29-minutes-7930.txt', '2026-07-29',
                   'regular transportation had been budgeted too low for FY26', ['transport'],
                   note='It is about the regular-route line, which closed exactly on its '
                        'budget after the transfer; the overrun in this category is all on '
                        'the special-education line, which no transfer covered.'),
        sc_minutes('2026-07-29-minutes-7930.txt', '2026-07-29',
                   '$11,000 from Heating Charges, where funds remained available, to Regular '
                   'Transportation to cover an overage', ['utilities', 'transport']),
        sc_minutes('2026-02-04-minutes-7634.txt', '2026-02-04',
                   'we have also had students move into the district that require out of '
                   'district placements', ['tuition'],
                   note='It does not say which tuition line those placements were charged '
                        'to.'),
        caption('2025-11-19-6PZ-J-oIAkQ.json', '2025-11-19',
                'last year there was a freeze, so we haven’t had that yet'.replace(
                    '’', "'"), ['supplies', 'equipment', 'buildings'],
                note='A speaker answering, in November, whether FY26 spending was on track.'),
        caption('2026-10-07-kPZcnFd5COw.json', '2026-10-07',
                "We were thrifty and we didn't spend every dime",
                ['supplies', 'equipment', 'buildings'],
                note='A speaker discussing what to do with the money left over.'),
    ],
}

# What fits the same numbers where no document explains a category -- printed as a
# HYPOTHESIS every time, with the one record that would settle it. Figure-free on
# purpose (rule 2): the figures beside them are interpolated.
HYPOTHESES = {
    'teachers': ('a post left vacant or filled late, a leave of absence covered for less '
                 'than the salary, or teachers hired at a lower step than budgeted',
                 'the district’s position-control roster by month: each budgeted post, '
                 'who held it, from when, and at what step'),
    'counselors': ('a counselor or psychologist post vacant or on leave for part of the '
                   'year, or the work bought from a contractor instead',
                   'the position-control roster by month for functions 2710 and 2800'),
    'paras': ('aides hired late or not at all, or aides paid from a grant instead',
              'paraprofessional payroll by month and by funding source'),
    'admin': ('a vacancy or a change of person in an administrative post',
              'the position-control roster by month'),
    'custodians': ('custodial vacancies or turnover',
                   'the custodial roster by month, with overtime'),
    'other_staff': ('stipends not paid for seasons or programs that did not run, or a '
                    'nurse post vacant for part of the year',
                    'the stipend and nursing payroll by month'),
    'tuition': ('fewer children placed than budgeted, placements starting later, a '
                'placement paid from the circuit breaker fund instead, or a placement '
                'billed to a different tuition line',
                'the placement list by setting, with start dates and the tuition invoice '
                'for each'),
    'sped_services': ('more children needing contracted therapy or evaluation than '
                      'budgeted, or contractors covering for vacant staff posts',
                      'the contracted-service invoices by service type'),
    'transport': ('route or contract prices above budget, or special-education routes added '
                  'mid-year', 'the transportation contract and the route list by month'),
    'utilities': ('weather, energy prices, or a bill for one year paid in another',
                  'the utility bills by month'),
    'benefits': ('fewer employees enrolled in the health plan than budgeted, staff opting '
                 'out, or premiums below the estimate',
                 'health-plan enrolment by month and the premium rates'),
    'buildings': ('maintenance projects postponed or not started, a shortage of facilities '
                  'staff to run them, or a deliberate hold on spending',
                  'the facilities work-order and project list with dates'),
    'equipment': ('purchases deferred, or made from another fund',
                  'the purchase-order list for these accounts'),
    'supplies': ('a deliberate hold on purchasing, or purchases made from grants and '
                 'revolving funds instead',
                 'the general-fund journal detail by month'),
}


def check_record(fy):
    """Every quote must be verbatim in the archive's text of its document (whitespace
    collapsed), and every caption quote in our captions of that recording -- or this
    refuses to write. Returns the entries with page / timestamp filled in."""
    out = []
    for e in RECORD.get(fy, []):
        e = dict(e)
        if e['kind'] == 'caption':
            d = json.load(open(e['text'], encoding='utf-8'))
            segs = d['segments']
            txt, starts = '', []
            for s in segs:
                starts.append((len(txt), s['start']))
                txt += ' '.join(s['text'].split()) + ' '
            at = txt.find(e['quote'])
            if at < 0:
                fail('%s does not caption %r' % (rel(e['text']), e['quote']))
            sec = int(max(st for off, st in starts if off <= at))
            e['seconds'] = sec
            e['at'] = '%d:%02d:%02d' % (sec // 3600, sec % 3600 // 60, sec % 60)
            e['cite'] = '%s&t=%ds' % (e['video'], sec)
        else:
            e['page'] = page_of(e['text'], e['quote'])
        e['text'] = rel(e['text'])
        out.append(e)
    return out


def minutes_posted(date):
    with open(MEETING_INDEX, encoding='utf-8') as fh:
        return any(r['board'] == 'School Committee' and r['date'] == date
                   and r['kind'] == 'minutes' for r in csv.DictReader(fh))


def record_line(e):
    """One record entry as a line of markdown: who, when, the verbatim words, the link."""
    if e['kind'] == 'caption':
        posted = minutes_posted(e['date'])
        return ('- *%s, %s — the recording at [%s](%s), our machine captions, not a record:* '
                '“%s”. %s%s' % (e['board'], long_date(e['date']), e['at'], e['cite'],
                                e['quote'], (e['note'] + ' ') if e['note'] else '',
                                'The archive holds the Town’s minutes of this meeting.'
                                if posted else
                                'The archive’s catalogue of the Town’s postings lists no '
                                'minutes for this meeting, so the recording is the only '
                                'record.'))
    when = long_date(e['date']) if len(e['date']) == 10 else e['date']
    where = ('page %d' % e['page']) if e.get('page') else e['doc']
    return ('- *%s %s, %s (%s):* “%s”. [Our copy](%s) · [the Town’s](%s).%s'
            % (e['board'], e['doc'], when, where, e['quote'], e['cite'], e['town'],
               (' ' + e['note']) if e['note'] else ''))


# ---- the two charts, as SVG for /docs and the PDF (the page draws components) --------

def _esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def causes_svg(cats, title, subtitle):
    """Where the money was left: net unspent by category, largest first, coloured by the
    thrift test. Over-budget categories run left of zero."""
    W, ROW, TOP, LBL = 680, 24, 64, 200
    H = TOP + ROW * len(cats) + 40
    lo = min(0.0, min(c['unspent'] for c in cats))
    hi = max(0.0, max(c['unspent'] for c in cats))
    span = (hi - lo) or 1.0
    x0, x1 = LBL + 70, W - 70
    sc = (x1 - x0) / span
    zx = x0 + (0 - lo) * sc
    b = []
    for i, c in enumerate(cats):
        y = TOP + i * ROW
        v = c['unspent']
        col = KIND_COLOR[c['kind']] if v >= 0 else OVER_COLOR
        bx = zx if v >= 0 else zx + v * sc
        b.append('<text x="%d" y="%.1f" font-size="11" text-anchor="end" fill="%s">%s</text>'
                 % (LBL, y + 14, INK, _esc(c['label'])))
        b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="16" fill="%s" rx="2"/>'
                 % (bx, y + 3, max(abs(v) * sc, 1), col))
        tx = (zx + v * sc + 4) if v >= 0 else (zx + v * sc - 4)
        b.append('<text x="%.1f" y="%.1f" font-size="10.5" font-weight="700" '
                 'text-anchor="%s" fill="%s">%s</text>'
                 % (tx, y + 15, 'start' if v >= 0 else 'end', INK, usd(v)))
    b.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>'
             % (zx, TOP, zx, TOP + ROW * len(cats), AXIS))
    ly = TOP + ROW * len(cats) + 22
    lx = 0
    for kind, text in (('discretionary', 'Discretionary (supplies, upkeep, equipment)'),
                       ('circumstantial', 'Circumstantial (staff, tuition, prices)')):
        b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/>'
                 % (lx, ly - 9, KIND_COLOR[kind]))
        b.append('<text x="%d" y="%d" font-size="10" fill="%s">%s</text>'
                 % (lx + 14, ly, SECOND, text))
        lx += 260
    b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/>' % (lx, ly - 9, OVER_COLOR))
    b.append('<text x="%d" y="%d" font-size="10" fill="%s">Over budget</text>'
             % (lx + 14, ly, SECOND))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="%s. %s" font-family=\'%s\'>\n'
            '<rect width="%d" height="%d" fill="%s"/>\n'
            '<text x="0" y="16" font-size="13" font-weight="700" fill="%s">%s</text>\n'
            '<text x="0" y="33" font-size="10.5" fill="%s">%s</text>\n%s\n</svg>\n'
            % (W, H, W, H, _esc(title), _esc(subtitle), FONT, W, H, SURFACE, INK,
               _esc(title), SECOND, _esc(subtitle), ''.join(b)))


BVS_CAP = 130.0   # the share axis stops here; a category spent past it says so in words


def bvs_rows(cats):
    """Per category, the revised budget split into spent / still committed / left, as
    shares of that budget, for the budget-vs-spent chart. Computed here, once, so the page
    component draws these numbers rather than computing its own (rule 2)."""
    out = []
    for c in sorted(cats, key=lambda c: -c['revised']):
        if not round(c['revised'], 2):
            continue
        sp = 100 * c['expended'] / c['revised']
        en = 100 * c['encumbered'] / c['revised']
        left = 100 - sp - en
        out.append(dict(key=c['key'], label=c['label'], revised=c['revised'],
                        spent_pct=round(sp, 1), committed_pct=round(en, 1),
                        left_pct=round(max(left, 0), 1), over_pct=round(max(-left, 0), 1),
                        spent_shown=round(min(sp, BVS_CAP), 1)))
    return out


def bvs_svg(rows, title, subtitle):
    W, ROW, TOP, LBL = 680, 24, 64, 200
    H = TOP + ROW * len(rows) + 40
    x0, x1 = LBL + 70, W - 40
    sc = (x1 - x0) / BVS_CAP
    b = []
    for i, r in enumerate(rows):
        y = TOP + i * ROW
        b.append('<text x="%d" y="%.1f" font-size="11" text-anchor="end" fill="%s">%s</text>'
                 % (LBL, y + 14, INK, _esc(r['label'])))
        b.append('<text x="%d" y="%.1f" font-size="10" text-anchor="end" fill="%s">%s</text>'
                 % (LBL + 64, y + 14, MUTED, usdk(r['revised'])))
        x = x0
        for w, col in ((min(r['spent_pct'], BVS_CAP), SPENT),
                       (r['committed_pct'], MOVED), (r['left_pct'], UNSPENT)):
            w = min(w, (x1 - x) / sc)
            if w > 0:
                b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="16" fill="%s"/>'
                         % (x, y + 3, w * sc, col))
                x += w * sc
        if r['over_pct'] or r['left_pct'] >= 1:
            txt = ('%s%% spent' % format(r['spent_pct'], '.0f')) if r['over_pct'] else \
                  ('%s%% left' % format(r['left_pct'], '.0f'))
            b.append('<text x="%.1f" y="%.1f" font-size="10" font-weight="700" fill="%s">%s</text>'
                     % (min(x + 4, x1 - 2), y + 15, '#b3261e' if r['over_pct'] else INK, txt))
    hx = x0 + 100 * sc
    b.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-dasharray="3,2"/>'
             % (hx, TOP - 4, hx, TOP + ROW * len(rows), '#b3261e'))
    b.append('<text x="%.1f" y="%d" font-size="9.5" text-anchor="middle" fill="%s">the budget '
             '(100%%)</text>' % (hx, TOP - 8, '#b3261e'))
    ly = TOP + ROW * len(rows) + 22
    lx = 0
    for col, text in ((SPENT, 'Spent'), (MOVED, 'Still committed (open orders)'),
                      (UNSPENT, 'Left over')):
        b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/>' % (lx, ly - 9, col))
        b.append('<text x="%d" y="%d" font-size="10" fill="%s">%s</text>'
                 % (lx + 14, ly, SECOND, text))
        lx += 200
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="%s. %s" font-family=\'%s\'>\n'
            '<rect width="%d" height="%d" fill="%s"/>\n'
            '<text x="0" y="16" font-size="13" font-weight="700" fill="%s">%s</text>\n'
            '<text x="0" y="33" font-size="10.5" fill="%s">%s</text>\n%s\n</svg>\n'
            % (W, H, W, H, _esc(title), _esc(subtitle), FONT, W, H, SURFACE, INK,
               _esc(title), SECOND, _esc(subtitle), ''.join(b)))


def why_sources(fy):
    """The documents the why-section quotes, plus the special-funds report it reads --
    rule 12, from the manifest. Captions are cited as the video at a timestamp."""
    out = [held_source('town-ledgers/expenses/glytdbud-expense-fy%d-p13-special-school.xlsx'
                       % fy, 'munis-school-ytd', 'Town of Lunenburg — Town Accountant',
                       'MUNIS year-to-date budget report, the school special funds (grants, '
                       'revolving funds, the circuit breaker), FY%d period 13. Read only to '
                       'see where another fund paid for the same DESE function.' % fy)]
    seen = set()
    for e in RECORD.get(fy, []):
        if e['kind'] != 'documented':
            continue
        key = e['key']
        if key in seen:
            continue
        seen.add(key)
        out.append(held_source(key, 'why_the_surplus', e['board'],
                               'Quoted in “Why there was money left over”: “%s”.'
                               % e['quote']))
    return out


WHY_NOT_ESTABLISHED = [
    'Why any category was left under budget. The ledger shows where money was left; '
    'vacancies, placements, prices and restraint all produce the same rows.',
    'Whether anyone chose to spend less. The discretionary share is the most thrift could '
    'explain, not a finding that it did; the monthly journal would show it and is not '
    'published.',
]


# ---- the whole section, for one year -----------------------------------------------

def why(fy, rows, t):
    """Everything the 'why' half of a report needs: the computed figures, the record, the
    markdown for the short version and for two sections, the conclusions, the charts."""
    slug = paths(fy)['slug']
    cats = causes(rows)
    total = t['available']
    under_tot = round(sum(c['under'] for c in cats), 2)
    over_tot = round(sum(c['over'] for c in cats), 2)
    if round(sum(c['unspent'] for c in cats), 2) != round(total, 2):
        fail('the categories sum to %.2f, not the unspent total %.2f'
             % (sum(c['unspent'] for c in cats), total))
    by = {c['key']: c for c in cats}
    disc = round(sum(c['unspent'] for c in cats if c['kind'] == 'discretionary'), 2)
    circ = round(total - disc, 2)
    disc_share = 100 * disc / total
    disc_enc = round(sum(c['encumbered'] for c in cats if c['kind'] == 'discretionary'), 2)
    sal = [c for c in cats if c['key'] in ('teachers', 'counselors', 'paras', 'admin',
                                            'custodians', 'other_staff')]
    sal_net = round(sum(c['unspent'] for c in sal), 2)
    top_u, top_o = top_accounts(rows)
    record = check_record(fy)
    hist = history(cats, fy)
    hist_by = {h['key']: h for h in hist['rows']}
    sf, sf_coarse = special_overlap(fy, cats)
    bvs = bvs_rows(cats)
    biggest = [c for c in cats if c['unspent'] > 0][:3]
    biggest_sum = round(sum(c['unspent'] for c in biggest), 2)
    overs = sorted([c for c in cats if c['unspent'] < 0], key=lambda c: c['unspent'])
    disc_cats = [c for c in cats if c['kind'] == 'discretionary']
    disc_repeat = [c for c in disc_cats if hist_by[c['key']]['years_under'] == len(
        hist['years'])]
    yrs = hist['years']
    span = '%s–FY%d' % (C.fy(yrs[0]), yrs[-1])

    # ---- charts ----
    svg_causes = causes_svg(
        cats, 'Where the FY%d money was left, by category' % fy,
        '%s left net: %s in accounts that ended under budget, %s over in the rest'
        % (usd(total), usd(under_tot), usd(abs(over_tot))))
    svg_bvs = bvs_svg(
        bvs, 'Budget against spending, FY%d, by category' % fy,
        'Each bar is that category’s revised budget; the figure beside the name is its size')

    # ---- markdown: the short version's addition ----
    s = []
    s.append('![Where the FY%d school surplus was left, by category: %s.](charts/%s-causes.svg)\n'
             % (fy, '; '.join('%s %s' % (c['label'], usd0(c['unspent'])) for c in cats),
                slug))
    s.append('**Where it came from. Three categories left the most:** %s. Accounts that ended '
             'over budget used %s of what the rest left%s.\n'
             % ('; '.join('%s, %s (%s of its budget)'
                          % (c['label'].lower(), usd(c['unspent']),
                             C.pct(c['pct_of_revised'])) for c in biggest),
                usd(abs(over_tot)),
                (', led by %s' % ' and '.join('%s, %s over' % (c['label'].lower(),
                                                                 usd(abs(c['unspent'])))
                                              for c in overs[:2])) if overs else ''))
    s.append('**Was it thrift? %s of it (%s) sat in discretionary lines — supplies, upkeep '
             'and equipment, the part a decision to spend less could explain.** The other %s '
             'sat in salaries, benefits, tuition and other lines that follow staffing, '
             'placements and prices. The split of lines into the two groups is ours; see '
             '*Was it thrift?* below.\n'
             % (usd(disc), C.pct(disc_share, 0), usd(circ)))

    # ---- markdown: the "why" section (restHead on the page) ----
    w = []
    w.append('## Why there was money left over\n')
    w.append('![Each category’s FY%d revised budget split into what was spent, what is still '
             'committed to open purchase orders, and what was left.](charts/%s-budget-vs-spent.svg)\n'
             % (fy, slug))
    w.append('Every one of the %s accounts is put in exactly one category by its DESE function '
             'and object code (the table is under *How the categories are built*). The '
             'surplus is net: accounts that ended under budget left %s, and accounts that '
             'ended over used %s of it.\n'
             % (C.num(len(rows)), usd(under_tot), usd(abs(over_tot))))
    w.append('| category | revised budget | spent | still committed | left over (net) | '
             '% of its budget | under-budget accounts | over-budget accounts |\n'
             '|---|---:|---:|---:|---:|---:|---:|---:|')
    for c in cats:
        w.append('| %s | %s | %s | %s | **%s** | %s | %s | %s |'
                 % (c['label'], usd0(c['revised']), usd0(c['expended']),
                    usd0(c['encumbered']) if c['encumbered'] else '—', usd0(c['unspent']),
                    C.pct(c['pct_of_revised']) if c['pct_of_revised'] is not None else '—',
                    usd0(c['under']) if c['under'] else '—',
                    usd0(c['over']) if c['over'] else '—'))
    w.append('| **Total** | %s | %s | %s | **%s** | %s | %s | %s |\n'
             % (usd0(t['revised']), usd0(t['expended']), usd0(t['encumbered']), usd0(total),
                C.pct(100 * total / t['revised']), usd0(under_tot), usd0(over_tot)))
    w.append('### What the ledger shows, and what explains it\n')
    w.append('For each category that moved by at least %s: first what the ledger shows '
             '(measured), then what a document says about why — quoted, never paraphrased — '
             'or, where no document here says, the causes that fit the same numbers, marked '
             'as a hypothesis, and the one record that would settle it.\n' % usd(EXPLAIN_MIN))
    explained = []
    for c in sorted(cats, key=lambda c: -abs(c['unspent'])):
        recs = [e for e in record if c['key'] in e['categories']]
        if abs(c['unspent']) < EXPLAIN_MIN and not [e for e in recs if e['kind'] == 'documented']:
            continue
        explained.append(c['key'])
        if c['unspent'] >= 0:
            fact = ('%s left %s of %s (%s of its budget).'
                    % (c['label'], usd(c['unspent']), usd(c['revised']),
                       C.pct(c['pct_of_revised'])))
        else:
            fact = ('%s ran %s over a budget of %s.'
                    % (c['label'], usd(abs(c['unspent'])), usd(c['revised'])))
        if c['under'] and c['over']:
            fact += (' Inside it, accounts under budget left %s and accounts over budget '
                     'used %s.' % (usd(c['under']), usd(abs(c['over']))))
        if c['encumbered']:
            fact += ' %s more is still committed to open orders.' % usd(c['encumbered'])
        h = hist_by[c['key']]
        fact += (' It ended under budget in %s of the %s closed years held (%s).'
                 % (C.num(h['years_under']), C.num(len(yrs)), span))
        paid = [r for r in sf if r['category'] == c['key']]
        if paid:
            fact += (' Other funds also paid on the same lines: %s.'
                     % '; '.join('fund %s%s, %s' % (r['fund'], (' “%s”' % r['name'])
                                                     if r['name'] else '', usd(r['expended']))
                                 for r in paid))
        w.append('**%s.** %s\n' % (c['label'], fact))
        docs = [e for e in recs if e['kind'] == 'documented']
        caps = [e for e in recs if e['kind'] == 'caption']
        if docs or caps:
            w.append('*On the record — evidence of what was said, not a test of it:*\n')
            for e in docs + caps:
                w.append(record_line(e))
            w.append('')
        hyp, settles = HYPOTHESES[c['key']]
        if not docs:
            w.append('*Possible causes, not established by any document here (a hypothesis):* '
                     '%s. *Would settle it:* %s.\n' % (hyp, settles))
        else:
            w.append('*What the record does not establish:* how much of the figure above it '
                     'accounts for. Other causes that fit: %s. *Would settle it:* %s.\n'
                     % (hyp, settles))
    w.append('### The largest single accounts\n')
    w.append('| left over | account | budget | spent | committed |\n|---:|---|---:|---:|---:|')
    for a in top_u:
        w.append('| %s | %s `%s` | %s | %s | %s |'
                 % (usd0(a['available']), a['name'], a['account'], usd0(a['revised']),
                    usd0(a['expended']), usd0(a['encumbered']) if a['encumbered'] else '—'))
    w.append('')
    if top_o:
        w.append('| over budget | account | budget | spent | committed |\n|---:|---|---:|---:|---:|')
        for a in top_o:
            w.append('| %s | %s `%s` | %s | %s | %s |'
                     % (usd0(a['available']), a['name'], a['account'], usd0(a['revised']),
                        usd0(a['expended']),
                        usd0(a['encumbered']) if a['encumbered'] else '—'))
        w.append('')
    w.append('---\n')

    # ---- markdown: "Was it thrift?" ----
    th = []
    th.append('## Was it thrift?\n')
    caps_thrift = [e for e in record if e['kind'] == 'caption']
    th.append('A statement that the district was careful is evidence that it was said, not of '
              'what happened (rule 7). The ledger can test it five ways; a sixth needs a '
              'record nobody has published.\n')
    th.append('**1. Which lines.** %s of the %s left over sat in discretionary lines (%s); '
              '%s sat in circumstantial ones. Salary lines alone, net: %s. Thrift shows up in '
              'the first group; the second follows vacancies, placements and prices whatever '
              'anyone decides about purchases.\n'
              % (usd(disc), usd(total), C.pct(disc_share, 0), usd(circ), usd(sal_net)))
    th.append('**2. Does it repeat?** Left over, net, by category, in every closed year the '
              'ledger holds. A line left over every year reads as budgeted high rather than '
              'run lean.\n')
    th.append('| category | kind | %s | years under |\n|---|---|%s---:|'
              % (' | '.join(C.fy(y) for y in yrs), '---:|' * len(yrs)))
    for h in hist['rows']:
        th.append('| %s | %s | %s | %s of %s |'
                  % (h['label'], h['kind'], ' | '.join(usd0(v) for v in h['by_year']),
                     C.num(h['years_under']), C.num(len(yrs))))
    th.append('')
    th.append('%s of the %s discretionary categories ended under budget in all %s years%s.\n'
              % (C.num(len(disc_repeat)), C.num(len(disc_cats)), C.num(len(yrs)),
                 (' (%s)' % ', '.join(c['label'].lower() for c in disc_repeat))
                 if disc_repeat else ''))
    th.append('**3. Budget moves during the year.** What was voted, what moved, and what the '
              'budget became, by category — slack moved from one line to cover another is '
              'not saving.\n')
    th.append('| category | voted | moved during the year | revised |\n|---|---:|---:|---:|')
    for c in sorted(cats, key=lambda c: -abs(c['transfers'])):
        if not round(c['transfers'], 2):
            continue
        th.append('| %s | %s | %s | %s |' % (c['label'], usd0(c['original']),
                                            usd0(c['transfers']), usd0(c['revised'])))
    th.append('')
    th.append('**4. Other funds paying.** The school’s special funds (grants, revolving funds, '
              'the circuit breaker) spent on the same DESE function as these categories:\n')
    if sf:
        for r in sf:
            th.append('- %s: fund %s%s spent %s.'
                      % (CAT_LABEL[r['category']], r['fund'],
                         (' “%s”' % r['name']) if r['name'] else '', usd(r['expended'])))
        th.append('')
    th.append('A match means the same kind of spending, not that it replaced general-fund '
              'spending: neither report says which staff member or child a payment covered.\n')
    th.append('%s more of special-fund spending is coded to a round function (2000, 0000 and '
              'the like) that names no line, so it cannot be matched to any category here. '
              'Where another fund paid, a general-fund line can look underspent without '
              'anyone having spent less (rule 11).\n' % usd(sf_coarse))
    th.append('**5. Committed is not saved.** %s is still committed to open purchase orders '
              '— %s of it in discretionary lines. It is not in the %s and is not savings until '
              'an order is released.\n' % (usd(t['encumbered']), usd(disc_enc), usd(total)))
    th.append('**6. A decision on record.** What the archive holds about a hold on spending:\n')
    for e in [e for e in record if e['kind'] == 'caption']:
        th.append(record_line(e))
    th.append('')
    th.append('No posted minutes in the archive record a vote or a directive to freeze FY%d '
              'spending; searched for *thrift*, *freeze*, *spending freeze*, *hold on '
              'spending*, *frugal* and *conservative* in School Committee, Finance Committee '
              'and Select Board documents. *Would settle it:* the general-fund journal by '
              'month — thrift would show as discretionary spending slowing late in the year '
              'against prior years.\n' % fy)
    th.append('---\n')

    # ---- method ----
    m = []
    m.append('## How the categories are built\n')
    m.append('One table in `scripts/build_school_surplus.py` (`CATEGORIES`), first match '
             'wins. *Function* is the account string’s 4th segment, the DESE function code; '
             '*salary* means the object code starts `51`. The discretionary / circumstantial '
             'split is ours, a judgement about which lines a decision to spend less moves '
             'directly, and it is stated so it can be disagreed with.\n')
    m.append('| category | kind | rule |\n|---|---|---|')
    for key, label, kind, rule, _ in CATEGORIES:
        m.append('| %s | %s | %s |' % (label, kind, rule))
    m.append('')
    m.append('---\n')

    # ---- conclusions ----
    lead = biggest[0]
    rws = [
        conclusion(
            id='where-the-surplus-was-left',
            claim='%s was left in three categories: %s, %s and %s.'
                  % (usd(biggest_sum), CAT_SHORT[biggest[0]['key']],
                     CAT_SHORT[biggest[1]['key']], CAT_SHORT[biggest[2]['key']]),
            so_what=('Accounts over budget used %s; the largest overrun was %s, %s over.'
                     % (usd(abs(over_tot)), CAT_SHORT[overs[0]['key']],
                        usd(abs(overs[0]['unspent']))))
                    if overs else
                    ('No category ran over, net; the largest, %s, left %s of its budget.'
                     % (CAT_SHORT[lead['key']], C.pct(lead['pct_of_revised']))),
            figures=dict(
                {'c_three': figure(biggest_sum, usd(biggest_sum),
                                   'left over in the three largest categories'),
                 'c_under': figure(under_tot, usd(under_tot)),
                 'c_total': figure(total, usd(total))},
                **({'c_over': figure(abs(overs[0]['unspent']), usd(abs(overs[0]['unspent']))),
                    'c_over_tot': figure(abs(over_tot), usd(abs(over_tot)))}
                   if overs else
                   {'c_lead_pct': figure(lead['pct_of_revised'],
                                         C.pct(lead['pct_of_revised']))}),
                **{'c_top%d' % i: figure(c['unspent'], usd(c['unspent']))
                   for i, c in enumerate(biggest)}),
            figure='c_three', kind='measured', bearing='sizes',
            detail='By category, net: %s. Accounts under budget left %s in all, and the '
                   'surplus is what remained, %s. The ledger shows where money was left, '
                   'never why.'
                   % ('; '.join('%s %s' % (c['label'].lower(), usd(c['unspent']))
                                for c in biggest),
                      usd(under_tot), usd(total)),
            basis='`sources/data/munis-school-ytd.csv`, FY%d period 13, report gf-school, '
                  'every account put in one category by `CATEGORIES` in the generator.' % fy,
            not_shown='Why any category was left under budget — vacancies, placements, '
                      'prices and restraint all produce the same ledger.',
            allow=('13', str(fy)),
        ),
        conclusion(
            id='how-much-thrift-could-explain',
            claim='%s of the surplus (%s) sat in discretionary lines thrift could explain.'
                  % (C.pct(disc_share, 0), usd(disc)),
            so_what='The other %s sat in staff, tuition and benefit lines, which follow '
                    'vacancies, placements and prices.' % usd(circ),
            figures={'c_disc_share': figure(disc_share, C.pct(disc_share, 0),
                                            'of the surplus in discretionary lines'),
                     'c_disc': figure(disc, usd(disc)),
                     'c_circ': figure(circ, usd(circ)),
                     'c_years': figure(len(yrs), C.num(len(yrs)), 'years'),
                     'c_rep': figure(len(disc_repeat), C.num(len(disc_repeat)),
                                     'categories'),
                     'c_ndisc': figure(len(disc_cats), C.num(len(disc_cats)),
                                       'categories')},
            figure='c_disc_share', kind='measured', bearing='sizes',
            detail='Discretionary means supplies, upkeep and equipment — the split is ours, '
                   'stated in the method table. %s of the %s discretionary categories were also '
                   'left under budget in all %s closed years held, which reads as budgeted high '
                   'as much as run lean. It is the most thrift could explain, not a finding '
                   'that it did.'
                   % (C.num(len(disc_repeat)), C.num(len(disc_cats)), C.num(len(yrs))),
            basis='`munis-school-ytd.csv`, FY2023 to FY2026 period 13, gf-school; the '
                  'category table in the generator.',
            not_shown='Whether anyone chose to spend less. That would show in the monthly '
                      'journal, which is not published.',
        ),
    ]
    payload = dict(
        categories=cats,
        category_rules=[dict(key=k, label=l, kind=kd, rule=r) for k, l, kd, r, _ in CATEGORIES],
        under_total=under_tot, over_total=over_tot,
        discretionary=dict(unspent=disc, share_pct=round(disc_share, 2), encumbered=disc_enc,
                           repeat_every_year=[c['key'] for c in disc_repeat]),
        circumstantial=dict(unspent=circ),
        salary_net=sal_net,
        top_unspent=top_u, top_over=top_o,
        budget_vs_spent=bvs, bvs_cap=BVS_CAP,
        history=hist,
        special_funds=sf, special_funds_unmatched=sf_coarse,
        record=[{k: v for k, v in e.items()} for e in record],
        explained=explained,
        hypotheses={k: dict(causes=h, settles=s) for k, (h, s) in HYPOTHESES.items()
                    if k in explained},
        explain_min=EXPLAIN_MIN,
    )
    return dict(short='\n'.join(s).rstrip('\n') + '\n', section='\n'.join(w) + '\n',
                thrift='\n'.join(th) + '\n', method='\n'.join(m) + '\n',
                conclusions=rws, payload=payload,
                charts={slug + '-causes': svg_causes, slug + '-budget-vs-spent': svg_bvs})


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
    y = why(fy, rows, t)

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

    # What caused it comes first: where the money sat, how much thrift could explain, and
    # the Town's own stated explanation. The comparison cards follow, in the fold.
    rws = y['conclusions'] + [rws[3]] + rws[:3]

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
    w(y['short'])
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
    w(y['section'])
    w(y['thrift'])
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
    w(y['method'])
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
        causes=y['payload'],
        sources=fy25_sources(page) + why_sources(fy),
        not_established=WHY_NOT_ESTABLISHED + [
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
    return md, pay, chart_svg, y['charts']


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


# ---- FY2026: the audit pass ---------------------------------------------------------
#
# notes/process/AUDIT-PASS.md, run against this ledger on 10 October 2026; the findings and
# how they were ranked are in notes/findings/FY26-SURPLUS-AUDIT.md. Every finding is a
# COMPARISON -- a figure set against something it was supposed to equal -- and every
# figure is computed here. The FY2027 budget is the district's own workbook
# (`lps-budget-lines.csv`, from budget-workbooks/fy27-proposals.xlsx), its Balanced column,
# read only as a budget: it is set beside an actual (rule 1 allows the comparison; nothing
# here projects anything), and each workbook line used is first TIED to the MUNIS FY2026
# original appropriation of the accounts it is set against, or this refuses to write.

BOOK = os.path.join(DATA, 'lps-budget-lines.csv')
BOOK_KEY = 'budget-workbooks/fy27-proposals.xlsx'
FY25_MINUTES_NOV = os.path.join(SC_TEXT, '2025-11-05-minutes-7496.txt')
FINCOM_FEB = os.path.join(ROOT, 'sources', 'meetings', 'text', 'finance-committee',
                          '2026-02-26-minutes-7673.txt')

# workbook line names (exactly as the sheet prints them) -> the MUNIS accounts they are
# the budget of. The tie is asserted, not assumed.
AUDIT_LINES = {
    'private': (('Special Ed Tuitions/Private',), ('0100-3-300-9300-51-1-06-2-535019',)),
    'collab': (('Collaborative Tuitions',), ('0100-3-300-9400-51-1-06-2-535023',)),
    'electricity': (('Electricity/System',), ('0100-3-300-4130-99-1-74-2-521011',)),
    'therapy': (('Spcl Ed Contrtd Related Services',), ('0100-3-300-2310-51-1-06-2-535012',)),
    'psych': (('P.S. Psychologist',), ('0100-3-300-2800-07-2-06-1-511023',)),
    'kinder': (('Kindergarten Aides/Regular', 'Kindergarten Paraprofessionals'),
               ('0100-3-300-2330-03-2-12-1-511103', '0100-3-300-2330-03-2-13-1-511203')),
    'sped_paras': (('ACE Special Ed Paraprofessionals', 'P.S. Special Ed Paraprofessionals*',
                    'E.S. Special Ed Paraprofessionals', 'M.S. Special Ed Paraprofessionals',
                    'H.S. Special Ed Paraprofessionals'),
                   ('0100-3-300-2330-51-1-13-1-511203', '0100-3-300-2330-51-2-13-1-511203',
                    '0100-3-300-2330-51-4-13-1-511203', '0100-3-300-2330-51-5-13-1-511203',
                    '0100-3-300-2330-51-6-13-1-511203')),
}
ACCT_HEALTH = '0100-3-300-5200-99-1-99-2-570001'
ACCT_HEATING = '0100-3-300-4120-99-1-74-2-521025'
ACCT_SC_DUES = '0100-3-300-1110-01-1-01-2-535003'
ACCT_BLDG_CONTRACTED = '0100-3-300-4220-01-1-74-2-535006'
FUND_CB = '2640'
# QUOTED, each verbatim (whitespace collapsed), and checked against the text on every run.
Q_JULY_START = 'The following line-item transfers were reviewed:'
Q_JULY_END = 'The Committee then discussed the overall status'
Q_JULY_PURPOSE = 'a series of year-end line-item transfers needed to cover overages within the FY26 budget'
Q_JULY_FORTHCOMING = 'additional year-end transfers may still be forthcoming'
Q_HEATING = '$11,000 from Heating Charges, where funds remained available, to Regular Transportation'
Q_SEARCH = ('transfer $13,500 from admin tech contracts to school committee dues, to cover '
            'superintendent search invoice')
Q_SOLAR = 'questions the impact of the solar panels'


def _flat(path):
    if not os.path.exists(path):
        fail('missing %s' % rel(path))
    return ' '.join(open(path, encoding='utf-8').read().split())


def _quoted(path, q):
    if q not in _flat(path):
        fail('%s no longer says %r' % (rel(path), q))
    return q


def fy26_audit(rows, t, cats):
    """The eight comparisons of AUDIT-PASS.md that found something, as figures, evidence
    markdown and conclusion cards. FY2026 only: FY2025's report is a different argument."""
    import re
    byacct = {}
    for y in HISTORY_YEARS:
        for r in ledger_rows(y):
            byacct.setdefault(r['account'], {})[y] = r
    for a, v in byacct.items():
        if len(v) != len(HISTORY_YEARS):
            fail('account %s is not in every closed year held' % a)

    def F(r, k):
        return float(r[k])

    def se(r):
        return F(r, 'ytd_expended') + F(r, 'encumbrances')

    def acct(a, y=2026):
        if a not in byacct:
            fail('account %s is not in the ledger' % a)
        return byacct[a][y]

    # ---- the workbook, tied line by line to the ledger ----------------------------------
    book = [r for r in csv.DictReader(open(BOOK, encoding='utf-8')) if r['kind'] == 'line']

    def num(x):
        return float(x) if x not in ('', None) else 0.0
    wb = {}
    for key, (names, accts) in AUDIT_LINES.items():
        rs = [r for r in book if r['line_item'] in names]
        if len(rs) != len(names):
            fail('the FY2027 workbook has %d rows for %s, not %d' % (len(rs), key, len(names)))
        d = {c: round(sum(num(r[c]) for r in rs), 2)
             for c in ('fy26_final', 'fy27_balanced', 'fy27_level_service', 'fy27_core',
                       'fy27_restoration')}
        munis = round(sum(F(acct(a), 'original_approp') for a in accts), 2)
        if abs(d['fy26_final'] - munis) > 0.5:
            fail('%s: the workbook FY26 final budget %.2f does not tie to the MUNIS FY2026 '
                 'original appropriation %.2f' % (key, d['fy26_final'], munis))
        d['rows'] = sorted(int(r['row']) for r in rs)
        d['accounts'] = list(accts)
        wb[key] = d
    tot = [r for r in csv.DictReader(open(BOOK, encoding='utf-8'))
           if r['line_item'] == 'TOTAL ACTUALS & BUDGET:']
    if len(tot) != 1:
        fail('the FY2027 workbook no longer prints one TOTAL ACTUALS & BUDGET row')
    level27, bal27 = num(tot[0]['fy27_level_service']), num(tot[0]['fy27_balanced'])

    # ---- 1. out-of-district tuition: FY27's budget against FY26's bill -----------------
    tu = {k: dict(voted=F(acct(wb[k]['accounts'][0]), 'original_approp'),
                  spent=F(acct(wb[k]['accounts'][0]), 'ytd_expended'),
                  committed=round(se(acct(wb[k]['accounts'][0])), 2),
                  fy27=wb[k]['fy27_balanced']) for k in ('private', 'collab')}
    gf_tuition26 = round(cats['tuition']['expended'] + cats['tuition']['encumbered'], 2)
    if abs(gf_tuition26 - sum(v['committed'] for v in tu.values())) > 0.005:
        fail('the tuition category is no longer exactly the private and collaborative lines')
    fy27_tuition = round(sum(v['fy27'] for v in tu.values()), 2)
    tuition_gap = round(gf_tuition26 - fy27_tuition, 2)
    same_every_scenario = all(
        wb[k]['fy27_balanced'] == wb[k][c] for k in ('private', 'collab')
        for c in ('fy27_level_service', 'fy27_core', 'fy27_restoration'))
    if not same_every_scenario:
        fail('the FY2027 tuition figure now differs between scenarios; the card that says it '
             'was not a cut must be rewritten')

    def cb_tuition(y):
        return round(sum(se(r) for r in special_rows(y)
                         if r['fund'] == FUND_CB and func_of(r) >= 9000), 2)

    def gf_tuition(y):
        return round(sum(se(r) for r in ledger_rows(y) if func_of(r) >= 9000), 2)
    cb_series = []
    for y in HISTORY_YEARS:
        g, c = gf_tuition(y), cb_tuition(y)
        cb_series.append(dict(fy=y, general_fund=g, circuit_breaker=c, total=round(g + c, 2),
                              cb_share_pct=round(100 * c / (g + c), 2)))
    cb26 = cb_series[-1]['circuit_breaker']

    # ---- 2. lines that closed past their revised budgets -------------------------------
    july = _flat(FY26_JULY_MINUTES)
    a, b = july.find(Q_JULY_START), july.find(Q_JULY_END)
    if a < 0 or b < a:
        fail('the 29 July 2026 minutes no longer list the year-end transfers')
    amounts = [float(x.replace(',', '')) for x in
               re.findall(r'•\s*\$([\d,]+(?:\.\d+)?) from', july[a:b])]
    if len(amounts) != july[a:b].count('•') or len(amounts) != 10:
        fail('the 29 July 2026 transfer list no longer reads as ten amounts')
    july_total = round(sum(amounts), 2)
    for q in (Q_JULY_PURPOSE, Q_JULY_FORTHCOMING, Q_HEATING):
        _quoted(FY26_JULY_MINUTES, q)
    years = []
    for y in HISTORY_YEARS:
        rr = ledger_rows(y)
        over = [r for r in rr if F(r, 'available_budget') < -0.004]
        years.append(dict(
            fy=y, accounts_over=len(over),
            over=round(sum(F(r, 'available_budget') for r in over), 2),
            transfers_in=round(sum(F(r, 'transfers_adjustments') for r in rr
                                   if F(r, 'transfers_adjustments') > 0), 2),
            transfers_out=round(sum(F(r, 'transfers_adjustments') for r in rr
                                    if F(r, 'transfers_adjustments') < 0), 2),
            closed_at_zero=sum(1 for r in rr if round(F(r, 'ytd_expended'), 2)
                               and round(F(r, 'available_budget'), 2) == 0)))
    yr = {d['fy']: d for d in years}
    over26 = sorted([r for r in rows if F(r, 'available_budget') < -0.004],
                    key=lambda r: (F(r, 'available_budget'), r['account']))
    if round(sum(F(r, 'available_budget') for r in over26), 2) != round(
            sum(c['over'] for c in cats.values()), 2):
        fail('the overdrawn accounts do not sum to the categories\' over-budget total')
    top5 = [dict(account=r['account'], description=r['description'].strip(),
                 original=F(r, 'original_approp'), transfers=F(r, 'transfers_adjustments'),
                 spent=F(r, 'ytd_expended'), encumbered=F(r, 'encumbrances'),
                 available=F(r, 'available_budget')) for r in over26[:5]]
    top5_sum = round(sum(x['available'] for x in top5), 2)
    no_transfer_over = [r for r in over26 if F(r, 'transfers_adjustments') <= 0.004]

    # ---- 3. the surplus beside the FY27 cuts --------------------------------------------
    cut27 = round(level27 - bal27, 2)
    ceiling = round(t['available'] + t['encumbered'], 2)
    floor_share = 100 * t['available'] / cut27
    ceiling_share = 100 * ceiling / cut27

    # ---- 4. lines voted below their spending every year ---------------------------------
    chronic = {}
    for k in ('electricity', 'therapy'):
        a0 = wb[k]['accounts'][0]
        per = [dict(fy=y, voted=F(byacct[a0][y], 'original_approp'),
                    spent=round(se(byacct[a0][y]), 2),
                    gap=round(F(byacct[a0][y], 'original_approp') - se(byacct[a0][y]), 2))
               for y in HISTORY_YEARS]
        chronic[k] = dict(account=a0, years=per, over_years=sum(1 for p in per if p['gap'] < 0),
                          total=round(-sum(p['gap'] for p in per), 2),
                          paid26=F(byacct[a0][2026], 'ytd_expended'), fy27=wb[k]['fy27_balanced'])
        if chronic[k]['over_years'] != len(HISTORY_YEARS):
            fail('%s no longer ran past its voted budget in every year held' % k)
        if chronic[k]['fy27'] >= chronic[k]['paid26']:
            fail('%s: FY2027 is no longer budgeted below what FY2026 paid' % k)
    chronic_total = round(sum(c['total'] for c in chronic.values()), 2)
    heat = [dict(fy=y, voted=F(byacct[ACCT_HEATING][y], 'original_approp'),
                 transfers=F(byacct[ACCT_HEATING][y], 'transfers_adjustments'),
                 spent=round(se(byacct[ACCT_HEATING][y]), 2),
                 available=F(byacct[ACCT_HEATING][y], 'available_budget'))
            for y in HISTORY_YEARS]
    _quoted(FINCOM_FEB, Q_SOLAR)

    # ---- 5. transfers in that ended unspent ---------------------------------------------
    given = [r for r in rows if F(r, 'transfers_adjustments') > 0.004
             and F(r, 'available_budget') > 0.5]
    given_in = round(sum(F(r, 'transfers_adjustments') for r in given), 2)
    given_left = round(sum(F(r, 'available_budget') for r in given), 2)
    given_rows = [dict(account=r['account'], description=r['description'].strip(),
                       original=F(r, 'original_approp'), transfers=F(r, 'transfers_adjustments'),
                       spent=F(r, 'ytd_expended'), encumbered=F(r, 'encumbrances'),
                       available=F(r, 'available_budget'))
                  for r in sorted(given, key=lambda r: (-min(F(r, 'transfers_adjustments'),
                                                             F(r, 'available_budget')),
                                                        r['account']))]
    dues, heat26, bldg = acct(ACCT_SC_DUES), acct(ACCT_HEATING), acct(ACCT_BLDG_CONTRACTED)
    _quoted(FY25_MINUTES_NOV, Q_SEARCH)
    search_transfer = 13500.0   # the "$13,500" in Q_SEARCH, checked against the ledger:
    if F(dues, 'transfers_adjustments') != search_transfer:
        fail('School Committee dues no longer shows the $13,500 transfer in')
    if F(dues, 'ytd_expended') >= F(dues, 'original_approp'):
        fail('School Committee dues now spent past its original budget; the card that says '
             'the search transfer went unused must be rewritten')
    heating_moved_out = 11000.0  # the "$11,000" in Q_HEATING
    heating_in_at_least = round(F(heat26, 'transfers_adjustments') + heating_moved_out, 2)
    for r in (dues, heat26, bldg):
        if r not in given:
            fail('%s is no longer a transfer-in that ended unspent' % r['account'])

    # ---- 6. supplies and upkeep, voted against spent -----------------------------------
    def cat_series(key):
        out = []
        for y in HISTORY_YEARS:
            rr = [r for r in ledger_rows(y) if category_of(r) == key]
            v = round(sum(F(r, 'original_approp') for r in rr), 2)
            s_ = round(sum(se(r) for r in rr), 2)
            out.append(dict(fy=y, voted=v, spent=s_, gap=round(v - s_, 2)))
        return out
    supplies = cat_series('supplies')
    buildings = cat_series('buildings')
    if not all(p['gap'] > 0 for p in supplies):
        fail('supplies were not voted above spending in every year held')
    supplies_total = round(sum(p['gap'] for p in supplies), 2)
    bldg_rise = 100 * (buildings[-1]['voted'] / buildings[0]['voted'] - 1)
    bldg_left = buildings[-1]['gap']

    # ---- 7. lines budgeted again ---------------------------------------------------------
    psych = acct(wb['psych']['accounts'][0])
    if F(psych, 'ytd_expended') != 0:
        fail('the primary psychologist line now shows spending; the card must be rewritten')
    kinder_spent = round(sum(F(acct(a), 'ytd_expended') for a in wb['kinder']['accounts']), 2)
    kinder_voted = round(sum(F(acct(a), 'revised_budget') for a in wb['kinder']['accounts']), 2)
    if kinder_voted != 0 or wb['kinder']['fy27_balanced'] != 0:
        fail('the kindergarten aide lines are no longer at $0 in FY2026 and FY2027 balanced')

    # ---- credit ----------------------------------------------------------------------------
    para_paid26 = round(sum(F(acct(a), 'ytd_expended') for a in wb['sped_paras']['accounts']), 2)
    para_over26 = round(sum(F(acct(a), 'available_budget')
                            for a in wb['sped_paras']['accounts']), 2)
    para27 = wb['sped_paras']['fy27_balanced']
    para_above = round(para27 - para_paid26, 2)
    if para_above <= 0:
        fail('FY2027 no longer budgets the special-education aides above FY2026 spending')
    hi = {y: byacct[ACCT_HEALTH][y] for y in HISTORY_YEARS}
    health_short = round(-(F(hi[2023], 'available_budget') + F(hi[2024], 'available_budget')), 2)
    health_left = F(hi[2026], 'available_budget')
    health_left_pct = 100 * health_left / F(hi[2026], 'revised_budget')
    if F(hi[2023], 'available_budget') >= 0 or F(hi[2024], 'available_budget') >= 0 \
            or health_left <= 0:
        fail('health insurance no longer ran short in FY2023 and FY2024 and under in FY2026')

    figs = dict(
        tuition=dict(lines=tu, general_fund_fy26=gf_tuition26, fy27=fy27_tuition,
                     gap=tuition_gap, circuit_breaker_fy26=cb26, by_year=cb_series,
                     workbook_rows={k: wb[k]['rows'] for k in ('private', 'collab')}),
        overdrawn=dict(by_year=years, top5=top5, top5_sum=top5_sum,
                       accounts_over_no_transfer_in=len(no_transfer_over),
                       july_transfers=amounts, july_total=july_total),
        fy27_cut=dict(level_service=level27, balanced=bal27, gap=cut27,
                      floor_share_pct=round(floor_share, 2),
                      ceiling_share_pct=round(ceiling_share, 2)),
        chronic=chronic, chronic_total=chronic_total, heating=heat,
        given=dict(accounts=len(given), transfers_in=given_in, left=given_left,
                   rows=given_rows, heating_in_at_least=heating_in_at_least),
        supplies=supplies, buildings=buildings, supplies_total=supplies_total,
        buildings_vote_rise_pct=round(bldg_rise, 2),
        psych=dict(account=wb['psych']['accounts'][0], voted=F(psych, 'original_approp'),
                   spent=F(psych, 'ytd_expended'), fy27=wb['psych']['fy27_balanced']),
        kinder=dict(accounts=wb['kinder']['accounts'], spent=kinder_spent,
                    voted=kinder_voted, fy27=wb['kinder']['fy27_balanced']),
        credit=dict(sped_paras_fy27=para27, sped_paras_paid_fy26=para_paid26,
                    sped_paras_over_fy26=para_over26, sped_paras_above=para_above,
                    health_short_fy23_fy24=health_short, health_left_fy26=health_left,
                    health_left_pct=round(health_left_pct, 2)),
    )

    # ---- the cards, ranked by the argument test (AUDIT-PASS.md) ------------------------
    lit = ('FY23', 'FY24', 'FY25', 'FY26', 'FY27', 'FY28', '29 July', 'March 2026')
    n_years = len(HISTORY_YEARS)
    cards = [
        conclusion(
            id='tuition-budgeted-below-last-years-bill',
            claim='FY27 budgets %s for out-of-district tuition; FY26 spent %s on the same lines.'
                  % (usd(fy27_tuition), usd(gf_tuition26)),
            so_what='The circuit breaker paid %s on top. The FY28 line has to say which '
                    'figure it plans from.' % usd(cb26),
            figures={'t27': figure(fy27_tuition, usd(fy27_tuition),
                                   'budgeted for FY2027 out-of-district tuition'),
                     't26': figure(gf_tuition26, usd(gf_tuition26)),
                     'tcb': figure(cb26, usd(cb26)),
                     'tgap': figure(tuition_gap, usd(tuition_gap)),
                     'tpriv27': figure(tu['private']['fy27'], usd(tu['private']['fy27'])),
                     'tcol27': figure(tu['collab']['fy27'], usd(tu['collab']['fy27'])),
                     'tcol26': figure(tu['collab']['committed'], usd(tu['collab']['committed'])),
                     'tcolv': figure(tu['collab']['voted'], usd(tu['collab']['voted']))},
            figure='t27', kind='measured', bearing='lever',
            detail='FY27 sits %s below FY26 on these two lines. Collaborative tuition alone was '
                   'voted %s for FY26, spent %s, and is budgeted %s for FY27; private '
                   'tuition is budgeted %s. Every FY27 scenario carries the same tuition '
                   'figure, so it is the district\'s estimate, not one of the cuts. Readings '
                   'that fit, none tested here: placements that end, more expected from the '
                   'circuit breaker, or FY27 tuition paid in advance out of FY26.'
                   % (usd(tuition_gap), usd(tu['collab']['voted']),
                      usd(tu['collab']['committed']), usd(tu['collab']['fy27']),
                      usd(tu['private']['fy27'])),
            basis='`munis-school-ytd.csv`, FY2026 period 13, accounts 535019 and 535023 '
                  '(spent and committed), and fund 2640 tuition; the district\'s FY2027 '
                  'workbook (`lps-budget-lines.csv`), Balanced column, tied to the MUNIS '
                  'FY2026 original appropriation.',
            not_shown='How many children each figure pays for, or for which months. A dollar '
                      'is not a placement (rule 7).',
            allow=lit),
        conclusion(
            id='lines-closed-past-their-budgets',
            claim='%s school accounts closed FY26 %s past their revised budgets; FY25 closed '
                  'with %s.' % (C.num(yr[2026]['accounts_over']), usd(-yr[2026]['over']),
                                C.num(yr[2025]['accounts_over'])),
            so_what='The 29 July transfers moved %s. FY23 and FY24 closed like FY26, with '
                    '%s and %s over.' % (usd(july_total), C.num(yr[2023]['accounts_over']),
                                         C.num(yr[2024]['accounts_over'])),
            figures={'o26': figure(-yr[2026]['over'], usd(-yr[2026]['over']),
                                   'past revised budgets at the FY2026 close'),
                     'n26': figure(yr[2026]['accounts_over'], C.num(yr[2026]['accounts_over']),
                                   'accounts'),
                     'n25': figure(yr[2025]['accounts_over'], C.num(yr[2025]['accounts_over']),
                                   'accounts'),
                     'n23': figure(yr[2023]['accounts_over'], C.num(yr[2023]['accounts_over']),
                                   'accounts'),
                     'n24': figure(yr[2024]['accounts_over'], C.num(yr[2024]['accounts_over']),
                                   'accounts'),
                     'jul': figure(july_total, usd(july_total)),
                     'o25': figure(-yr[2025]['over'], usd(-yr[2025]['over'])),
                     'top5': figure(-top5_sum, usd(-top5_sum)),
                     'z25': figure(yr[2025]['closed_at_zero'], C.num(yr[2025]['closed_at_zero']),
                                   'accounts'),
                     'z26': figure(yr[2026]['closed_at_zero'], C.num(yr[2026]['closed_at_zero']),
                                   'accounts')},
            figure='o26', kind='measured', bearing='lever',
            detail='FY25 closed %s over, with %s accounts spent to exactly their budget '
                   'against %s in FY26. Five accounts carry %s of the FY26 overruns. The '
                   'school appropriation is one bottom-line total, so a line past its budget '
                   'is not past the appropriation; but the line budgets are what the next '
                   'budget is built from. Whether more transfers will post is not shown.'
                   % (usd(-yr[2025]['over']), C.num(yr[2025]['closed_at_zero']),
                      C.num(yr[2026]['closed_at_zero']), usd(-top5_sum)),
            basis='`munis-school-ytd.csv`, FY2023 to FY2026 period 13, gf-school, '
                  'available_budget below zero; School Committee minutes, 29 July 2026, the '
                  'ten transfers listed.',
            not_shown='Whether any line overran by decision or by surprise, and whether the '
                      'year-end transfer schedule is complete.',
            allow=lit),
        conclusion(
            id='surplus-beside-the-fy27-cuts',
            claim='FY26 left %s unspent; the FY27 school budget was set %s below level service.'
                  % (usd(t['available']), usd(cut27)),
            so_what='The surplus goes to the town as free cash, and Town Meeting decides where '
                    'certified free cash is spent.',
            figures={'p13': figure(t['available'], usd(t['available']),
                                   'unspent and uncommitted at period 13'),
                     'cut': figure(cut27, usd(cut27)),
                     'fshare': figure(floor_share, C.pct(floor_share)),
                     'cshare': figure(ceiling_share, C.pct(ceiling_share)),
                     'ceil': figure(ceiling, usd(ceiling))},
            figure='p13', kind='measured', bearing='lever',
            detail='The floor is %s of the gap between the FY27 balanced and level-service '
                   'budgets; with every open order released, %s would be %s. The two were not '
                   'known together: the FY27 budget was set in March 2026, and this surplus '
                   'was measured in October.'
                   % (C.pct(floor_share), usd(ceiling), C.pct(ceiling_share)),
            basis='`munis-school-ytd.csv`, FY2026 period 13; the district\'s FY2027 workbook, '
                  'TOTAL ACTUALS & BUDGET row, Level Service and Balanced columns.',
            not_shown='What free cash the Town will certify, and whether any of it will be '
                      'appropriated to the schools.',
            allow=lit),
        conclusion(
            id='lines-voted-below-spending-every-year',
            claim='Electricity and contracted therapy ran past their voted budgets all %s '
                  'years, by %s.' % (C.num(n_years), usd(chronic_total)),
            so_what='FY27 budgets them at %s and %s; FY26 already paid %s and %s.'
                    % (usd(chronic['electricity']['fy27']), usd(chronic['therapy']['fy27']),
                       usd(chronic['electricity']['paid26']), usd(chronic['therapy']['paid26'])),
            figures={'ctot': figure(chronic_total, usd(chronic_total),
                                    'spent past the voted budget, FY2023 to FY2026'),
                     'cn': figure(n_years, C.num(n_years), 'years'),
                     'e27': figure(chronic['electricity']['fy27'],
                                   usd(chronic['electricity']['fy27'])),
                     'r27': figure(chronic['therapy']['fy27'], usd(chronic['therapy']['fy27'])),
                     'e26': figure(chronic['electricity']['paid26'],
                                   usd(chronic['electricity']['paid26'])),
                     'r26': figure(chronic['therapy']['paid26'],
                                   usd(chronic['therapy']['paid26'])),
                     'etot': figure(chronic['electricity']['total'],
                                    usd(chronic['electricity']['total'])),
                     'rtot': figure(chronic['therapy']['total'], usd(chronic['therapy']['total'])),
                     'rv': figure(chronic['therapy']['years'][0]['voted'],
                                  usd(chronic['therapy']['years'][0]['voted']))},
            figure='ctot', kind='measured', bearing='lever',
            detail='Electricity: %s past its voted budgets over the %s years. Contracted related '
                   'services (special-education therapy) was voted %s in every one of them '
                   'and ran %s past. At the Finance Committee in February a member raised '
                   'the solar panels; nothing here says what they save.'
                   % (usd(chronic['electricity']['total']), C.num(n_years),
                      usd(chronic['therapy']['years'][0]['voted']),
                      usd(chronic['therapy']['total'])),
            basis='`munis-school-ytd.csv`, FY2023 to FY2026 period 13, accounts 521011 and '
                  '535012, original appropriation against spent and committed; the FY2027 '
                  'workbook, Balanced column.',
            not_shown='Why: usage, rates, or more children needing therapy all fit. A '
                      'dollar is not a kilowatt-hour or a child.',
            allow=lit),
        conclusion(
            id='transfers-in-that-ended-unspent',
            claim='%s accounts were given %s by transfer in FY26 and still ended %s under.'
                  % (C.num(len(given)), usd(given_in), usd(given_left)),
            so_what='School Committee dues got %s for a search invoice and ended with %s '
                    'unspent.' % (usd(search_transfer), usd(F(dues, 'available_budget'))),
            figures={'gleft': figure(given_left, usd(given_left),
                                     'left unspent in accounts that received transfers'),
                     'gn': figure(len(given), C.num(len(given)), 'accounts'),
                     'gin': figure(given_in, usd(given_in)),
                     'st': figure(search_transfer, usd(search_transfer)),
                     'sl': figure(F(dues, 'available_budget'), usd(F(dues, 'available_budget'))),
                     'bt': figure(F(bldg, 'transfers_adjustments'),
                                  usd(F(bldg, 'transfers_adjustments'))),
                     'bl': figure(F(bldg, 'available_budget'), usd(F(bldg, 'available_budget'))),
                     'ho': figure(heating_moved_out, usd(heating_moved_out)),
                     'hn': figure(F(heat26, 'transfers_adjustments'),
                                  usd(F(heat26, 'transfers_adjustments'))),
                     'hl': figure(F(heat26, 'available_budget'), usd(F(heat26, 'available_budget')))},
            figure='gleft', kind='measured', bearing='sizes',
            detail='Building contracted services received %s and ended %s under. The July '
                   'minutes record %s moved out of heating; the ledger shows %s moved into '
                   'heating, net, and it ended %s under. The ledger is net per account and cannot say '
                   'where any transfer came from.'
                   % (usd(F(bldg, 'transfers_adjustments')), usd(F(bldg, 'available_budget')),
                      usd(heating_moved_out), usd(F(heat26, 'transfers_adjustments')),
                      usd(F(heat26, 'available_budget'))),
            basis='`munis-school-ytd.csv`, FY2026 period 13: accounts with transfers_adjustments '
                  'above zero and available_budget above zero; School Committee minutes, '
                  '5 November 2025 and 29 July 2026.',
            not_shown='When in the year each transfer was made, or whether the invoice was '
                      'paid from another line.',
            allow=lit + ('5 November 2025',)),
        conclusion(
            id='circuit-breaker-share-of-tuition-fell',
            claim='The circuit breaker paid %s of FY26 out-of-district tuition; in FY23 it '
                  'paid %s.' % (C.pct(cb_series[-1]['cb_share_pct']),
                               C.pct(cb_series[0]['cb_share_pct'])),
            so_what='Over the same years the general fund\'s tuition bill went from %s to %s.'
                    % (usd(cb_series[0]['general_fund']), usd(cb_series[-1]['general_fund'])),
            figures={'cb26': figure(cb_series[-1]['cb_share_pct'],
                                    C.pct(cb_series[-1]['cb_share_pct']),
                                    'of out-of-district tuition paid by the circuit breaker'),
                     'cb23': figure(cb_series[0]['cb_share_pct'],
                                    C.pct(cb_series[0]['cb_share_pct'])),
                     'g23': figure(cb_series[0]['general_fund'],
                                   usd(cb_series[0]['general_fund'])),
                     'g26': figure(cb_series[-1]['general_fund'],
                                   usd(cb_series[-1]['general_fund'])),
                     'a23': figure(cb_series[0]['total'], usd(cb_series[0]['total'])),
                     'a26': figure(cb_series[-1]['total'], usd(cb_series[-1]['total']))},
            figure='cb26', kind='measured', bearing='sizes',
            detail='Tuition from both funds was %s in FY23 and %s in FY26. A general-fund line '
                   'can rise because the cost rose or because another fund paid less, and '
                   'the two look identical (rule 11).'
                   % (usd(cb_series[0]['total']), usd(cb_series[-1]['total'])),
            basis='`munis-school-ytd.csv`, FY2023 to FY2026 period 13: gf-school functions '
                  '9000 and up, and fund 2640 (special-school) functions 9000 and up, spent '
                  'and committed.',
            not_shown='The circuit breaker\'s balance, and how much of each year\'s '
                      'reimbursement was already committed when it arrived.',
            allow=lit + ('rule 11',)),
        conclusion(
            id='supplies-voted-above-spending-every-year',
            claim='Supplies and services were voted above what they spent in all %s years, %s '
                  'in all.' % (C.num(n_years), usd(supplies_total)),
            so_what='Building upkeep\'s vote rose %s from FY23 to FY26; FY26 spent %s less '
                    'than voted.' % (C.pct(bldg_rise), usd(bldg_left)),
            figures={'sup': figure(supplies_total, usd(supplies_total),
                                   'voted above spending, FY2023 to FY2026'),
                     'sn': figure(n_years, C.num(n_years), 'years'),
                     'br': figure(bldg_rise, C.pct(bldg_rise)),
                     'bl26': figure(bldg_left, usd(bldg_left)),
                     'bv23': figure(buildings[0]['voted'], usd(buildings[0]['voted'])),
                     'bv26': figure(buildings[-1]['voted'], usd(buildings[-1]['voted']))},
            figure='sup', kind='measured', bearing='sizes',
            detail='Upkeep was voted %s in FY23 and %s in FY26. A line left under its vote '
                   'every year reads as budgeted high as much as run lean; this is the most '
                   'thrift could explain, not a finding that it did.'
                   % (usd(buildings[0]['voted']), usd(buildings[-1]['voted'])),
            basis='`munis-school-ytd.csv`, FY2023 to FY2026 period 13, the supplies and '
                  'building-upkeep categories of `CATEGORIES`, original appropriation against '
                  'spent and committed.',
            not_shown='Whether anyone chose to spend less; the monthly journal would show it '
                      'and is not published.',
            allow=lit),
        conclusion(
            id='lines-budgeted-again',
            claim='A %s psychologist line paid nobody in FY26; FY27 budgets the line at %s.'
                  % (usd(F(psych, 'original_approp')), usd(wb['psych']['fy27_balanced'])),
            so_what='Kindergarten aides went the other way: %s paid against no budget, and '
                    'FY27 budgets none.' % usd(kinder_spent),
            figures={'pv': figure(F(psych, 'original_approp'), usd(F(psych, 'original_approp')),
                                  'voted for the primary school psychologist line, FY2026'),
                     'p27': figure(wb['psych']['fy27_balanced'],
                                   usd(wb['psych']['fy27_balanced'])),
                     'ks': figure(kinder_spent, usd(kinder_spent))},
            figure='pv', kind='measured', bearing='lever',
            detail='Both are measured in the same two documents: the period-13 ledger for '
                   'FY26 and the district\'s FY27 workbook, Balanced column. A budget line '
                   'is not a post: neither shows who was employed, or whether the work was '
                   'paid from another line or fund.',
            basis='`munis-school-ytd.csv`, FY2026 period 13, account %s and the two '
                  'kindergarten accounts; the FY2027 workbook rows %s and %s.'
                  % (wb['psych']['accounts'][0], wb['psych']['rows'][0],
                     ', '.join(str(x) for x in wb['kinder']['rows'])),
            not_shown='Whether the psychologist post was vacant, on leave, or paid elsewhere; '
                      'what the kindergarten aides were hired to do.',
            allow=lit + ('period-13',) + tuple(str(x) for x in wb['psych']['rows'] + wb['kinder']['rows'])
                  + (wb['psych']['accounts'][0],)),
        conclusion(
            id='credit-budgets-that-caught-up',
            claim='Credit: FY27 budgets special-ed aides %s above what FY26 paid them, after '
                  'an overrun.' % usd(para_above),
            so_what='Health insurance, %s short over FY23 and FY24, closed FY26 %s under its '
                    'budget.' % (usd(health_short), usd(health_left)),
            figures={'pa': figure(para_above, usd(para_above),
                                  'FY2027 special-education aide budget above FY2026 spending'),
                     'hs': figure(health_short, usd(health_short)),
                     'hl': figure(health_left, usd(health_left)),
                     'p27': figure(para27, usd(para27)),
                     'p26': figure(para_paid26, usd(para_paid26)),
                     'po': figure(-para_over26, usd(-para_over26)),
                     'hp': figure(health_left_pct, C.pct(health_left_pct))},
            figure='pa', kind='measured', bearing='sizes',
            detail='The five special-education aide lines ran %s past their revised budgets '
                   'in FY26 and spent %s; FY27 budgets %s. Health insurance closed FY26 %s '
                   'under its budget, close to the line after two years short.'
                   % (usd(-para_over26), usd(para_paid26), usd(para27), C.pct(health_left_pct)),
            basis='`munis-school-ytd.csv`, FY2023 to FY2026 period 13, the five 2330 '
                  'special-education aide accounts and health insurance (570001); the FY2027 '
                  'workbook, Balanced column.',
            not_shown='Whether FY27\'s aide budget matches the posts the district will '
                      'fill.',
            allow=lit),
    ]
    sources = [
        held_source(BOOK_KEY, 'lps_budget_lines', 'Lunenburg Public Schools',
                    'The district\'s FY2027 budget workbook (`lps-budget-lines.csv`), Balanced, '
                    'Level Service, Core and Restoration columns; each line used here is tied '
                    'to the MUNIS FY2026 original appropriation first.'),
        held_source('meetings/school-committee/2025-11-05-minutes-7496.docx',
                    'school_committee_minutes', 'Lunenburg School Committee',
                    'Minutes of 5 November 2025: "%s".' % Q_SEARCH),
        held_source('meetings/finance-committee/2026-02-26-minutes-7673.pdf',
                    'finance_committee_minutes', 'Lunenburg Finance Committee',
                    'Minutes of 26 February 2026, the school budget presentation: "%s".'
                    % Q_SOLAR),
    ]
    return dict(figures=figs, cards=cards, sources=sources, wb=wb,
                given=given, dues=dues, heat26=heat26, bldg=bldg, search=search_transfer,
                heating_moved_out=heating_moved_out, top5=top5, years=years, tu=tu,
                cb_series=cb_series, chronic=chronic, supplies=supplies, buildings=buildings,
                july_total=july_total, amounts=amounts)


def fy26_audit_md(a, t):
    """The evidence behind each audit card: the comparison, the account strings and raw
    values, what it does not show, and the hypotheses -- labelled -- that fit it."""
    f = a['figures']
    w = []
    p = w.append
    p('## The audit: each finding against what it should equal\n')
    p('Every finding below sets a figure against something it was supposed to equal — a '
      'budget against its spending, one year against the next, a statement against the '
      'ledger. Accounts are cited by their full MUNIS string; raw values are to the cent. '
      'The FY2027 figures are the district’s FY2027 workbook, Balanced column, each line '
      'first tied to the MUNIS FY2026 original appropriation. Where a cause is offered it is '
      'a hypothesis and says so.\n')

    tu, cb = a['tu'], a['cb_series']
    p('### 1. Out-of-district tuition: the FY2027 budget against the FY2026 bill\n')
    p('| line | account | FY2026 voted | FY2026 spent | FY2026 spent and committed | '
      'FY2027 budget |\n|---|---|---:|---:|---:|---:|')
    for k, label in (('private', 'Private tuition'), ('collab', 'Collaborative tuition')):
        v = tu[k]
        p('| %s | `%s` | %s | %s | %s | %s |'
          % (label, a['wb'][k]['accounts'][0], usd2(v['voted']), usd2(v['spent']),
             usd2(v['committed']), usd2(v['fy27'])))
    p('| **Both** | | %s | %s | **%s** | **%s** |\n'
      % (usd2(sum(v['voted'] for v in tu.values())), usd2(sum(v['spent'] for v in tu.values())),
         usd2(f['tuition']['general_fund_fy26']), usd2(f['tuition']['fy27'])))
    p('The FY2027 budget is %s below what FY2026 spent and committed on the same two lines. '
      'The circuit breaker fund (2640) paid %s more tuition in FY2026, outside these lines. '
      'The FY2027 figure is the same in the Balanced, Level Service, Core and Restoration '
      'columns, so it was the district’s estimate rather than one of the spring’s cuts.\n'
      % (usd(f['tuition']['gap']), usd(f['tuition']['circuit_breaker_fy26'])))
    p('*What it does not show:* how many children either figure pays for, or for which months. '
      '*Readings that fit, none tested here (hypotheses):* placements ending in FY2027; more '
      'expected from the circuit breaker; FY2027 tuition paid in advance from FY2026 money, '
      'which would raise FY2026 and lower FY2027 by the same amount. *Would settle it:* the '
      'tuition invoices by service period, and the FY2027 placement list with the fund '
      'expected to pay each.\n')

    p('### 2. Lines that closed past their revised budgets\n')
    p('| fiscal year | accounts past revised budget | by | transfers in, gross | '
      'accounts spent to exactly $0 left |\n|---|---:|---:|---:|---:|')
    for d in a['years']:
        p('| %s | %s | %s | %s | %s |' % (C.fy(d['fy']), C.num(d['accounts_over']),
                                          usd(-d['over']), usd(d['transfers_in']),
                                          C.num(d['closed_at_zero'])))
    p('')
    p('FY2025 is the exception, not FY2026: it is the one year in four in which nearly every '
      'line was brought back to its budget by transfer. *That this was a deliberate year-end '
      'reconciliation after the FY2025 surplus became public is a hypothesis; nothing here '
      'records it.* The school appropriation is a single bottom-line total, so a line past '
      'its budget is not spending past the appropriation — but the lines are what the next '
      'budget is built from.\n')
    p('The five largest FY2026 overruns, %s of the %s:\n'
      % (usd(-f['overdrawn']['top5_sum']), usd(-a['years'][-1]['over'])))
    p('| account | description | voted | moved in | spent | committed | past budget |'
      '\n|---|---|---:|---:|---:|---:|---:|')
    for x in a['top5']:
        p('| `%s` | %s | %s | %s | %s | %s | %s |'
          % (x['account'], x['description'].title(), usd2(x['original']), usd2(x['transfers']),
             usd2(x['spent']), usd2(x['encumbered']), usd2(x['available'])))
    p('')
    p('The minutes of 29 July 2026 describe “%s” and list ten, totalling %s. They also record '
      'that “%s”. The period-13 run of %s shows no transfer posted after the period-12 run of '
      '%s. %s of the %s accounts past their budget received no transfer in at all.\n'
      % (Q_JULY_PURPOSE, usd2(a['july_total']), Q_JULY_FORTHCOMING, FY26_P13_RUN,
         FY26_P12_RUN, C.num(f['overdrawn']['accounts_over_no_transfer_in']),
         C.num(a['years'][-1]['accounts_over'])))

    fc = f['fy27_cut']
    p('### 3. The surplus beside the FY2027 cuts\n')
    p('| | |\n|---|---:|')
    p('| FY2027 school budget, Level Service | %s |' % usd2(fc['level_service']))
    p('| FY2027 school budget, Balanced (the no-override budget) | %s |' % usd2(fc['balanced']))
    p('| **The difference** | **%s** |' % usd2(fc['gap']))
    p('| FY2026 unspent at period 13 | %s (%s of the difference) |'
      % (usd2(t['available']), C.pct(fc['floor_share_pct'])))
    p('| …with every open purchase order released | %s (%s) |\n'
      % (usd2(round(t['available'] + t['encumbered'], 2)), C.pct(fc['ceiling_share_pct'])))
    p('Two measured things, side by side; neither explains the other. The FY2027 budget was '
      'set in March 2026, when the FY2026 year was nine months in; this surplus was measured '
      'in October. A school appropriation that is not spent lapses to the town’s general fund '
      'and reaches the free cash the state certifies; Town Meeting appropriates free cash. The '
      'district’s FY2027 projection of 23 March 2026 prints the same two totals, rounded to '
      'the dollar.\n')

    ch = a['chronic']
    p('### 4. Two lines voted below their spending in every year held\n')
    p('| line | account | %s | FY2027 budget |\n|---|---|%s---:|'
      % (' | '.join('%s voted − spent' % C.fy(y) for y in HISTORY_YEARS),
         '---:|' * len(HISTORY_YEARS)))
    for k, label in (('electricity', 'Electricity'),
                     ('therapy', 'Contracted related services (special-education therapy)')):
        p('| %s | `%s` | %s | %s |' % (label, ch[k]['account'],
                                      ' | '.join(usd(x['gap']) for x in ch[k]['years']),
                                      usd(ch[k]['fy27'])))
    p('')
    heat_above = [h['fy'] for h in f['heating'] if h['voted'] > h['spent']]
    heat_in = [h['fy'] for h in f['heating'] if h['transfers'] > 0]
    p('FY2026 had already paid %s for electricity and %s for therapy before anything still '
      'committed. Beside electricity, natural-gas heating (`%s`) was voted above its spending '
      'in %s and received transfers in, net, in %s: %s.\n'
      % (usd2(ch['electricity']['paid26']), usd2(ch['therapy']['paid26']), ACCT_HEATING,
         ', '.join(C.fy(y) for y in heat_above),
         'every year held' if len(heat_in) == len(HISTORY_YEARS)
         else ', '.join(C.fy(y) for y in heat_in),
         '; '.join('%s voted %s, moved %s, spent and committed %s'
                   % (C.fy(h['fy']), usd(h['voted']), usd(h['transfers']), usd(h['spent']))
                   for h in f['heating'])))
    p('At the Finance Committee on 26 February 2026 a member “%s”. *Hypotheses, untested:* '
      'buildings moving load from gas to electricity; rates; the solar arrangement. *Would '
      'settle it:* the utility bills by building, with kilowatt-hours and any solar credit.\n'
      % Q_SOLAR)

    g = f['given']
    p('### 5. Transfers in to lines that then ended unspent\n')
    p('%s accounts received %s, net, by transfer during FY2026 and closed with %s still '
      'unspent. The largest:\n' % (C.num(g['accounts']), usd2(g['transfers_in']), usd2(g['left'])))
    p('| account | description | voted | moved in, net | spent | committed | left |'
      '\n|---|---|---:|---:|---:|---:|---:|')
    for x in g['rows'][:6]:
        p('| `%s` | %s | %s | %s | %s | %s | %s |'
          % (x['account'], x['description'].title(), usd2(x['original']), usd2(x['transfers']),
             usd2(x['spent']), usd2(x['encumbered']), usd2(x['available'])))
    p('')
    d = a['dues']
    p('School Committee minutes, 5 November 2025: “%s”. The ledger shows that line received '
      '%s, spent %s of its original %s, and closed with %s left — so whatever paid the search '
      'invoice, this line did not, or did not yet. Two measured things; the reconciling '
      'explanation, if there is one, is not in any document held.\n'
      % (Q_SEARCH, usd2(float(d['transfers_adjustments'])), usd2(float(d['ytd_expended'])),
         usd2(float(d['original_approp'])), usd2(float(d['available_budget']))))
    h = a['heat26']
    p('And heating. The 29 July minutes record “%s”. The ledger shows natural-gas heating '
      'received %s, net, over the year — so at least %s moved into it from somewhere — and it '
      'closed with %s left and %s still committed. The ledger is net per account and cannot '
      'say which transfer was which.\n'
      % (Q_HEATING, usd2(float(h['transfers_adjustments'])), usd2(g['heating_in_at_least']),
         usd2(float(h['available_budget'])), usd2(float(h['encumbrances']))))

    p('### 6. Who paid for out-of-district tuition\n')
    p('| fiscal year | general fund (functions 9000+) | circuit breaker (fund 2640) | both | '
      'circuit breaker share |\n|---|---:|---:|---:|---:|')
    for x in cb:
        p('| %s | %s | %s | %s | %s |' % (C.fy(x['fy']), usd(x['general_fund']),
                                          usd(x['circuit_breaker']), usd(x['total']),
                                          C.pct(x['cb_share_pct'])))
    p('')
    p('Spent and committed, both funds. Measured: tuition from the two funds together rose, '
      'and the circuit breaker’s share of it fell, so the general-fund lines rose faster than '
      'the cost. Not measured: why its share fell. The reimbursement follows the year of the '
      'cost, at a rate the state sets, and the fund’s balance is not held here; any of those '
      'could move it (a hypothesis). A general-fund line is the town’s share, not the cost '
      '(rule 11).\n')

    p('### 7. Supplies and upkeep, voted against spent\n')
    p('| fiscal year | supplies & services voted | spent and committed | voted − spent | '
      'building upkeep voted | spent and committed | voted − spent |'
      '\n|---|---:|---:|---:|---:|---:|---:|')
    for s_, b_ in zip(a['supplies'], a['buildings']):
        p('| %s | %s | %s | %s | %s | %s | %s |'
          % (C.fy(s_['fy']), usd(s_['voted']), usd(s_['spent']), usd(s_['gap']),
             usd(b_['voted']), usd(b_['spent']), usd(b_['gap'])))
    p('')
    p('These are the categories of *Why there was money left over* below, measured against '
      'what was VOTED rather than the revised budget. A line left under its vote every year '
      'reads as budgeted high as much as run lean.\n')

    ps, kd = f['psych'], f['kinder']
    p('### 8. Lines budgeted again\n')
    p('| line | account(s) | FY2026 voted | FY2026 spent | FY2027 budget |\n|---|---|---:|---:|---:|')
    p('| Primary school psychologist | `%s` | %s | %s | %s |'
      % (ps['account'], usd2(ps['voted']), usd2(ps['spent']), usd2(ps['fy27'])))
    p('| Kindergarten aides and paraprofessionals | %s | %s | %s | %s |\n'
      % (', '.join('`%s`' % x for x in kd['accounts']), usd2(kd['voted']), usd2(kd['spent']),
         usd2(kd['fy27'])))
    p('*Hypotheses, untested:* the psychologist post was vacant or on leave, or paid from '
      'another line; the kindergarten aides were hired for children whose plans required them. '
      '*Would settle it:* the position-control roster by month, and payroll by account.\n')

    cr = f['credit']
    p('### Credit where the ledger shows it\n')
    p('- **Special-education aides.** The five lines ran %s past their revised budgets in '
      'FY2026 and spent %s. FY2027 budgets %s — %s above what FY2026 paid. A budget that '
      'moved toward its spending.'
      % (usd(-cr['sped_paras_over_fy26']), usd(cr['sped_paras_paid_fy26']),
         usd(cr['sped_paras_fy27']), usd(cr['sped_paras_above'])))
    p('- **Health insurance** (`%s`) closed FY2023 and FY2024 a combined %s past its budget; '
      'FY2026 closed %s under, %s of the budget.'
      % (ACCT_HEALTH, usd(cr['health_short_fy23_fy24']), usd(cr['health_left_fy26']),
         C.pct(cr['health_left_pct'])))
    p('- **The year-end transfers were voted in open session and itemised** in the 29 July '
      '2026 minutes, account by account, with a reason for each.\n')
    p('---\n')
    return '\n'.join(w) + '\n'


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
    y = why(fy, rows, t)
    ycat = {c['key']: c for c in y['payload']['categories']}
    audit = fy26_audit(rows, t, ycat)
    # The transportation quote on record names REGULAR routes; the category's overrun is
    # the special-education line. Asserted, because the note in RECORD says so.
    tr = {r['account']: r for r in rows if func_of(r) == 3300}
    if (round(float(tr['0100-3-300-3300-99-1-69-2-535025']['available_budget']), 2) != 0
            or round(float(tr['0100-3-300-3300-99-1-69-2-535026']['available_budget']), 2)
            != round(ycat['transport']['unspent'], 2)):
        fail('regular routes no longer closed at $0, or the transportation overrun is no '
             'longer all special-education transport: the note on the quote must change')
    sal_net = y['payload']['salary_net']
    paras_over = abs(ycat['paras']['unspent'])
    if ycat['paras']['unspent'] >= 0:
        fail('FY26 paraprofessionals no longer ran over; the salary card must be rewritten')
    salary_card = conclusion(
        id='salary-lines-left-money-though-aides-ran-over',
        claim='Salary lines left %s net, though paraprofessionals ran %s over.'
              % (usd(sal_net), usd(paras_over)),
        so_what='The record names one leave of absence; no document here says why counselor '
                'money was left.',
        figures={'s_net': figure(sal_net, usd(sal_net), 'left over in salary lines, net'),
                 's_paras': figure(paras_over, usd(paras_over)),
                 's_couns': figure(ycat['counselors']['unspent'],
                                   usd(ycat['counselors']['unspent'])),
                 's_teach': figure(ycat['teachers']['unspent'],
                                   usd(ycat['teachers']['unspent']))},
        figure='s_net', kind='measured', bearing='sizes',
        detail='Counselors & psychologists left %s and teachers & substitutes %s. The 29 July '
               '2026 minutes say money in a special-education teacher account "%s", and was '
               'moved to cover paraprofessional overages. Vacancies, leaves and hiring steps '
               'all fit the rest; the position-control roster would settle it.'
               % (usd(ycat['counselors']['unspent']), usd(ycat['teachers']['unspent']),
                  'was associated with a leave of absence'),
        basis='`munis-school-ytd.csv`, FY2026 period 13, salary lines (object 51xxxx) by '
              'category; School Committee minutes, 29 July 2026.',
        not_shown='Which posts were vacant or on leave, and for how long. A dollar is not a '
                  'post (rule 7, rule 11).',
        allow=('29 July 2026',),
    )

    rws = [
        conclusion(
            id='period-13-landed-at-the-bottom-of-the-june-range',
            claim='The FY26 school surplus stands at %s, %s more than the June ledger showed.'
                  % (usd(t['available']), usd2(moved)),
            so_what='Not one of the %s accounts in both runs changed its spending between them.'
                    % C.num(len(p12_dept)),
            figures={'p13': figure(t['available'], usd(t['available']),
                                   'unspent and uncommitted at period 13'),
                     'moved': figure(moved, usd2(moved)),
                     'accounts': figure(len(p12_dept), C.num(len(p12_dept)), 'accounts'),
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

    # THE AUDIT LEADS (notes/process/AUDIT-PASS.md; CLAUDE.md 7b, "a conclusion is a
    # COMPARISON, or it is inventory"). Its cards come first, ranked by the argument test;
    # the salary offset and the period-12 comparison follow. The shared why() cards --
    # where the surplus was left, how much thrift could explain -- and the operations card
    # are inventory, and stay in the sections below rather than on the cards. FY2025 is
    # untouched: this is FY2026's argument.
    rws = audit['cards'] + [salary_card] + [c for c in rws if c['id'] !=
                                            'operations-and-maintenance-holds-the-most-of-both']

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
    w('**%s was left unspent and uncommitted in the school general fund at period 13 of '
      'FY2026**, of a revised budget of %s — net of %s left on lines that came in under and '
      '%s spent past the budgets of the rest. Read against what each line was supposed to '
      'equal, it says this:\n'
      % (usd(t['available']), usd(t['revised']), usd(y['payload']['under_total']),
         usd(abs(y['payload']['over_total']))))
    credit = [c for c in rws if c['id'].startswith('credit-')]
    for c in rws:
        if c in credit:
            continue
        w('**%s** %s\n' % (c['claim'], c['so_what']))
    for c in credit:
        w('**Credit where the ledger shows it.** %s %s %s\n'
          % (c['claim'][len('Credit: '):], c['so_what'],
             'And the year-end transfers were voted in open session and itemised, one by '
             'one, in the minutes.'))
    w('Every figure is in the evidence below, with the account it comes from. Where a cause '
      'is offered it is a hypothesis, and it says so.\n')
    w('---\n')
    w(fy26_audit_md(audit, t))
    w(y['section'].replace('## Why there was money left over\n',
                           '## Why there was money left over\n\n' + y['short'], 1))
    w(y['thrift'])
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
    w(y['method'])
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
            dict(value=usd0(-audit['figures']['overdrawn']['by_year'][-1]['over']),
                 label='spent past their revised budgets in %s accounts at the close — what '
                       'the surplus is net of'
                       % C.num(audit['figures']['overdrawn']['by_year'][-1]['accounts_over'])),
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
        causes=y['payload'],
        audit=audit['figures'],
        sources=srcs + why_sources(fy) + audit['sources'],
        not_established=WHY_NOT_ESTABLISHED + [
            'Whether the %s still encumbered will be paid, released, or carried into '
            'FY2027.' % usd(t['encumbered']),
            'Where the %s moved into the department during the year came from — net per '
            'account, no counterparty.' % usd(abs(t['transfers'])),
            'What "expense accounts" meant in the 29 July 2026 minutes, and so whether the '
            'ledger agrees with "approximately 100.2% expended".',
            'Why operations & maintenance was left unspent — dollars are not posts.',
            'What the FY2027 out-of-district tuition budget assumes: which placements, for '
            'which months, and how much the circuit breaker is expected to pay.',
            'Whether further FY2026 year-end transfers will post against the accounts still '
            'past their revised budgets, and from which lines.',
            'Where any FY2026 transfer came from or went to: the ledger is net per account.',
            'Why electricity has run past its voted budget in every year held.',
            'What was said under "%s" on %s: no minutes for %s are held.'
            % (FY26_AGENDA_ITEM, agenda_dates_text,
               'either meeting' if len(no_minutes) == 2 else 'those meetings')
            if no_minutes else
            'Minutes for the year-end budget review meetings are held and unread here.',
        ],
        conclusions=emit(slug, rws),
    )
    return md, pay, chart_svg, y['charts']


STORIES = {2025: fy2025, 2026: fy2026}


def run(fy, check):
    p = paths(fy)
    md, pay, chart_svg, extra = STORIES[fy]()
    pay_text = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    charts_dir = os.path.dirname(p['chart'])
    outputs = [(p['md'], md), (p['payload'], pay_text), (p['chart'], chart_svg)] + [
        (os.path.join(charts_dir, name + '.svg'), svg) for name, svg in sorted(extra.items())]
    if check:
        def cur(path):
            return open(path, encoding='utf-8').read() if os.path.exists(path) else ''
        bad = [os.path.basename(path) for path, gen in outputs if gen != cur(path)]
        if bad:
            print('STALE %s' % ', '.join(bad), file=sys.stderr)
            return 1
        print('%s.md, .json and its %d charts are current' % (p['slug'], len(outputs) - 2))
        return 0
    os.makedirs(charts_dir, exist_ok=True)
    for path, text in outputs:
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(text)
        os.replace(tmp, path)
    print('wrote %s' % ', '.join(rel(path) for path, _ in outputs))
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
