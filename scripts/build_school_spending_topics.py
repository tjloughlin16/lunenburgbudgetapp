#!/usr/bin/env python3
"""School spending, split into topic pages: twelve pages and the Spending compared hub.

    python3 scripts/build_school_spending_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_school_spending_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, one to four conclusions resting on them. The School spending shelf absorbs
/what-other-districts-spend (per-pupil-spending.md), spending-compared.md, peer-districts.md,
/budget-vs-actual and the School Committee's finance page (school_committee_fund_pages, below,
read off fy28/public/data/finance.json). The Chapter 70 floor, the teacher ratio, children schooled elsewhere, the
special education overruns and the two school surpluses already have pages on other shelves and
are only LISTED here.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD:

  fy28/public/data/peer-spending.json     build_peer_spending.py: DESE's end-of-year finance
                                          collection (all funds, per pupil, by function), the
                                          statewide distribution, RADAR, the residents-sending
                                          files, and the quotations it verified.
  fy28/public/data/budget-vs-actual.json  build_variance_charts.py: the district's budget books,
                                          each year's budget against the same year's RESTATED
                                          figure, line by line.
  sources/data/gl-history.csv             extract_gl_history.py: the Finance Committee's general
                                          fund workbook, FY2010-FY2025, assembled from MUNIS
                                          (rule 13a: stated). Its school sheet is checked here
                                          against the period-13 MUNIS reports where both exist.
  sources/data/munis-school-ytd.csv       extract_munis_school_ytd.py: the school general fund at
                                          period 13, FY2023-FY2026, MUNIS printouts.
  sources/data/dls-cherry-sheet.csv       every cherry sheet line, municipalities and regional
                                          school districts.

THE PROXY RULE (CLAUDE.md rule 7). Every per-pupil figure on these pages is DESE's own. No page
divides dollars by a headcount. The one piece of arithmetic that runs the other way -- the state
median a pupil times DESE's own pupil count -- is labelled an estimate, ours, every time.

RULE 1. Budget and actual are shown side by side for the SAME year and never differenced across
years. Where a page states how far spending landed from the budget, it is that year against
that year's own budget.

WHO CHOSE THE DISTRICTS. Statewide figures cover every district DESE publishes. The six-district
set is this project's, and no document records the criterion -- every page that uses it says so.
Destination districts are where Lunenburg children actually went, from DESE's files.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import per_pupil_measures as PPM  # noqa: E402
# Lunenburg's two districts. The six this project compares are K-12 and regional districts,
# so Monty Tech -- Lunenburg's own vocational district -- is in none of these sets; the page
# says so under the comparison it is missing from (lunenburg_districts.topic_step()).
import lunenburg_districts as DIST  # noqa: E402

PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
DOCS_DATA = os.path.join(ROOT, 'fy28', 'public', 'docs', 'data')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
GL = os.path.join(ROOT, 'sources', 'data', 'gl-history.csv')
YTD = os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv')
CHERRY = os.path.join(ROOT, 'sources', 'data', 'dls-cherry-sheet.csv')
CHERRY_SRC = os.path.join(ROOT, 'sources', 'data', 'dls-cherry-sheet-sources.csv')

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == 'school-spending' and gen == 'build_school_spending_topics.py']

# The six-district set, and which of the compared districts are regional. Both are OURS: the
# set has no recorded criterion, and no DESE field says which districts are regional -- it is
# read off each district's name and structure. Said on every page that uses either.
REGIONAL = ('Montachusett Regional Vocational Technical', 'Groton-Dunstable', 'North Middlesex',
            'Ayer Shirley School District', 'Ashburnham-Westminster')
CHERRY_NAME = {'Montachusett Regional Vocational Technical': 'Montachusett',
               'Groton-Dunstable': 'Groton Dunstable', 'North Middlesex': 'North Middlesex',
               'Ayer Shirley School District': 'Ayer Shirley',
               'Ashburnham-Westminster': 'Ashburnham Westminster'}
# Short names for DESE's functions, for a tile label; the table carries DESE's own names.
FN = {'TCHR': 'teachers', 'SERV': 'pupil services', 'LDRS': 'instructional leadership',
      'OPMN': 'operations and maintenance', 'MATL': 'materials and technology',
      'PDEV': 'professional development', 'TSER': 'other teaching services'}
# The same, for the three functions only the chart names. A chart row is a label, not prose.
FN_CHART = dict(FN, ADMN='administration', GUID='guidance, counselling and testing',
                BENE='insurance, retirement and other', ODTR='out-of-district transportation')
SHORT = {'Montachusett Regional Vocational Technical': 'Monty Tech',
         'Ayer Shirley School District': 'Ayer Shirley'}
# Shorter still, for a chart's category axis, where six names share one line.
AXIS = {'Ashburnham-Westminster': 'Ashburnham-W.', 'Groton-Dunstable': 'Groton-Dunst.'}

# Two quotations this page carries that no payload verified. Each is re-read from our copy of
# the minutes on every build and refused if it is not there verbatim.
QUOTES = {
    'transport-bill': ('school-committee/2025-04-16-minutes-7171.txt', 'School Committee',
                       '2025-04-16',
                       'Key provisions to the bill were a full 100% reimbursement for FY25 '
                       'regional transportation up from 82%'),
    'not-regionalize': ('school-committee/2024-01-24-minutes-6375.txt', 'School Committee',
                        '2024-01-24',
                        'Lunenburg decided to not regionalize and to stay a small school'),
}


def fail(msg):
    raise SystemExit('build_school_spending_topics: ' + msg)


# PUPIL SERVICES, SPLIT BY ITS OWN FUNCTION CODES. DESE's "Pupil Services" files buses,
# meals, nurses, sport, clubs, attendance officers and school security under one name, and
# these pages drew it as one row (TJ, 19 October 2026, on an invented grouping: "that was
# bad!"). Each part below is DESE's own function row. Athletics and other student activities
# stay apart here because each is compared with its own statewide median, and medians of
# parts do not add.
SERV_CODES = (('3300', 'buses'), ('3400', 'food service'), ('3200', 'nurses and health'),
              ('3510', 'athletics'), ('3520', 'other student activities'),
              ('3100', 'attendance and parent liaison'), ('3600', 'school security'))
SERV_NAME = dict(SERV_CODES)
FUNC_CSV = os.path.join(ROOT, 'sources', 'data', 'dese-function-expenditure.csv')
STATEWIDE_CSV = os.path.join(ROOT, 'sources', 'data', 'dese-function-statewide.csv')


def serv_totals(fy, district):
    """{func_code: all-funds total} for one district's pupil services, and the category
    total DESE prints, read off dese-function-expenditure.csv."""
    parts, cat = {}, None
    for r in csv.DictReader(open(FUNC_CSV, encoding='utf-8')):
        if r['fy'] != str(fy) or r['district'] != district or r['func_cat_code'] != 'SERV':
            continue
        if r['level'] == 'category':
            cat = float(r['total'])
        elif r['level'] == 'detail':
            if r['func_code'] not in SERV_NAME:
                fail('FY%d %s: pupil services carries %s, which the split does not name'
                     % (fy, district, r['func_code']))
            parts[r['func_code']] = parts.get(r['func_code'], 0.0) + float(r['total'])
    if cat is None or abs(sum(parts.values()) - cat) > 2:
        fail('FY%d %s: pupil services parts do not add to the category DESE prints'
             % (fy, district))
    return parts, cat


def serv_statewide(fy):
    """Each pupil-services function code against its own statewide distribution, in the
    shape peer-spending.json gives a category. Codes Lunenburg reports nothing under are
    returned separately: a function with no row is not a function measured at zero."""
    got, none = [], []
    for r in csv.DictReader(open(STATEWIDE_CSV, encoding='utf-8')):
        if r['fy'] != str(fy) or r['level'] != 'detail' or r['func_cat_code'] != 'SERV':
            continue
        if r['func_code'] not in SERV_NAME:
            fail('FY%d: statewide pupil services carries %s, which the split does not name'
                 % (fy, r['func_code']))
        if not r['lunenburg_per_pupil']:
            none.append(dict(code=r['func_code'], desc=r['func_desc'],
                             median=float(r['per_pupil_median']), districts=int(r['districts'])))
            continue
        m = re.fullmatch(r'(\d+) of (\d+)', r['lunenburg_rank_of_districts'])
        rank, of = int(m.group(1)), int(m.group(2))
        lun, med = float(r['lunenburg_per_pupil']), float(r['per_pupil_median'])
        got.append(dict(code=r['func_code'], desc='Pupil services: ' + r['func_desc'],
                        districts=of, median=med, lunenburg=lun, rank=rank,
                        spend_less=of - rank, share_of_median=round(lun / med, 4),
                        in_bottom_quarter=rank > of * 0.75))
    if not got:
        fail('FY%d: no statewide pupil-services detail rows' % fy)
    return got, none


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def _flat(t):
    return ' '.join(t.replace('ﬁ', 'fi').split())


def said(payload, key):
    """One quotation a payload already verified, re-checked against our copy of the minutes."""
    s = next((x for x in payload['said'] if x['key'] == key), None)
    if s is None:
        fail('quotation %r is no longer in its payload' % key)
    if not s['cite'].startswith('/docs/'):
        fail('quotation %r does not cite our copy' % key)
    path = os.path.join(ROOT, 'sources', s['cite'][len('/docs/'):])
    if os.path.exists(path) and _flat(s['quote']) not in _flat(
            open(path, encoding='utf-8', errors='replace').read()):
        fail('quotation %r is not verbatim in %s' % (key, s['cite']))
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'],
                label='%s minutes, %s' % (s['board'], s['date']))


def quote(key):
    rel, board, date, q = QUOTES[key]
    path = os.path.join(ROOT, 'sources', 'meetings', 'text', rel)
    if not os.path.exists(path):
        fail('%s is not on this disk; the quotation cannot be checked' % rel)
    if _flat(q) not in _flat(open(path, encoding='utf-8', errors='replace').read()):
        fail('quotation %r is not verbatim in %s' % (key, rel))
    return dict(quote=q, board=board, date=date, href='/docs/meetings/text/' + rel,
                label='%s minutes, %s' % (board, date))


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = {}
    docs = {
        'district-expenditures-by-function.xlsx': (
            'state-dese/district-expenditures-by-function.xlsx',
            'Massachusetts DESE, expenditures by function, all funds'),
        'radar-district-comparison.xlsx': ('state-dese/radar-district-comparison.xlsx',
                                           'Massachusetts DESE, RADAR district comparison'),
        'general-fund-budget-vs-actuals-history.xlsx': (
            'budget-workbooks/finance-committee/fy26-budget/'
            'general-fund-budget-vs-actuals-history.xlsx',
            'Lunenburg Finance Committee, assembled from MUNIS'),
    }
    for fy in (2023, 2024, 2025, 2026):
        name = 'glytdbud-expense-fy%d-p13-gf-school.xlsx' % fy
        docs[name] = ('town-ledgers/expenses/' + name, 'Town of Lunenburg — Town Accountant (MUNIS)')
    for r in csv.DictReader(open(CHERRY_SRC, encoding='utf-8')):
        if r['population'] == 'Regional Schools' and r['fy'] == '2026' and r['flow'] == 'Receipts':
            docs[r['source_file']] = ('state-dls/' + r['source_file'],
                                      'Massachusetts DLS, cherry sheet receipts, regional schools, '
                                      'FY2026')
    for name, (key, pub) in docs.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[name] = dict(label='%s — %s' % (pub, name), href='/docs/' + key)
    for f, what in (('dese-function-statewide.csv', 'DESE’s statewide distribution, by function'),
                    ('dese-function-expenditure.csv', 'DESE’s spending by district and function'),
                    ('dese-radar.csv', 'DESE’s RADAR rows for the compared districts'),
                    ('dese-town-enrollment.csv', 'where Lunenburg children are enrolled'),
                    ('dls-cherry-sheet.csv', 'every cherry sheet line'),
                    ('gl-history.csv', 'the Finance Committee’s ledger history, by account'),
                    ('munis-school-ytd.csv', 'the period-13 school reports, one row an account'),
                    ('line-history.csv', 'every district budget line, budget and restated')):
        if not os.path.exists(os.path.join(DOCS_DATA, f)):
            fail('/docs/data/%s is not published' % f)
        out[f] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    return out


def school_ledger():
    """The school general fund, {fy: dict(original, revised, spent, committed, source)}.

    FY2010-FY2022 from the Finance Committee's workbook (its 'School Only' account rows, summed;
    never its printed total row, which extract_gl_history.py shows does not tie). FY2023-FY2026
    from the MUNIS period-13 reports. Where both exist -- FY2023 and FY2024 -- they must agree to
    the dollar, or nothing is written. FY2025 in the workbook is part-year and is never used."""
    gl = defaultdict(lambda: dict(original=0.0, revised=0.0, spent=0.0, partial=False))
    for r in csv.DictReader(open(GL, encoding='utf-8')):
        if r['sheet'] != 'school_only':
            continue
        g = gl[int(r['fiscal_year'])]
        for k, col in (('original', 'original'), ('revised', 'revised'), ('spent', 'actual')):
            g[k] += float(r[col] or 0)
        g['partial'] = g['partial'] or r['actual_is_partial'] == 'true'
    led = defaultdict(lambda: dict(original=0.0, revised=0.0, spent=0.0, committed=0.0))
    for r in csv.DictReader(open(YTD, encoding='utf-8')):
        if r['report'] != 'gf-school' or r['period'] != '13' or r['type'] != 'E':
            continue
        g = led[int(r['fiscal_year'])]
        for k, col in (('original', 'original_approp'), ('revised', 'revised_budget'),
                       ('spent', 'ytd_expended'), ('committed', 'encumbrances')):
            g[k] += float(r[col] or 0)
    both = sorted(set(gl) & set(led))
    tied = []
    for fy in both:
        if gl[fy]['partial']:
            continue
        for k in ('original', 'revised', 'spent'):
            if abs(gl[fy][k] - led[fy][k]) > 1:
                fail('FY%d: the workbook’s school %s no longer ties to the period-13 report'
                     % (fy, k))
        if led[fy]['committed'] > 0.5:
            fail('FY%d: the period-13 report carries encumbrances the workbook cannot' % fy)
        tied.append(fy)
    if len(tied) < 2:
        fail('fewer than two years tie the workbook to the ledger: %s' % tied)
    out = {}
    for fy, g in gl.items():
        if g['partial'] or fy in led:
            continue
        out[fy] = dict(original=g['original'], revised=g['revised'], spent=g['spent'],
                       committed=0.0, source='workbook')
    for fy, g in led.items():
        out[fy] = dict(g, source='ledger')
    yrs = sorted(out)
    if yrs != list(range(yrs[0], yrs[-1] + 1)):
        fail('the school ledger series has a hole: %s' % yrs)
    return out, tied


def binlabel(b):
    """A spread bin as a short axis label, from its edges rather than its printed name:
    '-50/-25' reads in the width a bar has. The edges are fractions; 99 is open-ended."""
    pc = lambda v: ('%+d' % round(100 * v)).replace('-', '\u2212')
    if b['lo'] <= -1:
        return '<%s' % pc(b['hi'])
    if b['hi'] >= 99:
        return '>%s' % pc(b['lo'])
    if b['centred']:
        return '\u00b1%d' % round(100 * b['hi'])
    return '%s/%s' % (pc(b['lo']), pc(b['hi']))


def short(d):
    """A district's name short enough for a chart row; refused rather than cut mid-word."""
    n = SHORT.get(d, d).replace(' (District)', '').replace(
        ' Commonwealth Virtual School District', ', virtual')
    if len(n) > TP.LABEL_MAX:
        fail('no short chart name for %r' % d)
    return n


def what_counts():
    """WHAT PER PUPIL COUNTS: three official measures of one district's school spending, in one
    year, side by side -- DESE's per-pupil figure, Chapter 70 net school spending, and the Census
    Bureau's -- with what each counts and who set the rule. The page that answers "some districts
    include capital and some do not". Figures from per_pupil_measures.py (DESE's workbook and the
    Census table) and spending-vs-required.json (net school spending); the rules quoted from the
    documents that set them, all held in the archive."""
    M = PPM.measures()
    cen = M['federal']
    y = cen['fy']
    by = {r['fy']: r for r in M['by_year']}
    if y not in by:
        fail('DESE’s file has no FY%d, the Census year' % y)
    SVR = load('spending-vs-required.json')
    nss = next((r for r in SVR['actual'] if r['fy'] == y), None)
    if nss is None:
        fail('net school spending has no ACTUAL figure for FY%d' % y)
    lun, mt = cen['by_lea'][PPM.LUNENBURG], cen['by_lea'][PPM.MONTY]
    edge = M['edge_by_year'][y]
    trans = edge['lunenburg'].get('3300')
    mteq = edge['monty'].get('2420')
    if not trans or not mteq:
        fail('FY%d: no transportation row for Lunenburg or equipment row for Monty Tech' % y)
    capital_rows = sum(v for k, v in M['census'].items() if k in '678')
    d = by[y]
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    N = lambda v: figure(v, C.num(v))
    f, con = LD.fact, TP.conclusion
    statute = '/docs/state-law/2026-10-15/section2.html'
    eoyr = '/docs/state-dese/dese-eoyr-fy2025-printing-version.xlsx'
    cdoc = '/docs/state-census/census-school24doc.docx'
    src = [dict(label='Massachusetts DESE, expenditures by function, all funds — '
                      'district-expenditures-by-function.xlsx', href='/docs/' + PPM.KEY),
           dict(label='M.G.L. c.70 §2, the definition of net school spending — malegislature.gov, '
                      'Section2.html', href=statute),
           dict(label='Massachusetts DESE, Chapter 70 district profile — '
                      'dese-ch70-district-profile.xlsx', href=SVR['source']['docs_url']),
           dict(label='Massachusetts DESE, End of Year Financial Report FY2025, printing version '
                      '— printing-version.xlsx', href=eoyr),
           dict(label='US Census Bureau, Annual Survey of School System Finances FY2024 — '
                      'elsec24.xlsx', href='/docs/' + cen['key']),
           dict(label='US Census Bureau, the same survey’s technical documentation — '
                      'school24doc.docx', href=cdoc)]
    yl = {'y': F(y)}
    return TP.page(
        'what-per-pupil-counts',
        'Three official measures of school spending count different things; neither state one '
        'counts capital.',
        [f('dese', U(d['lunenburg_total']), 'Lunenburg, DESE’s per-pupil total, %s' % C.fy(y),
           'published', yl),
         f('nss', U(nss['spent']), 'Lunenburg, net school spending, %s' % C.fy(y), 'published', yl),
         f('cen', U(lun['TCURELSC']), 'Lunenburg, Census current spending, %s' % C.fy(y),
           'published', yl),
         f('cap', U(lun['TCAPOUT']), 'Lunenburg, Census capital outlay', 'published'),
         f('int', U(lun['I86']), 'Lunenburg, Census interest on school debt', 'published'),
         f('grants', U(d['lunenburg_grants']), 'grants and revolving funds in DESE’s total',
           'published'),
         f('trans', U(trans['total']), 'transportation in DESE’s total', 'published'),
         f('rows', N(capital_rows), 'capital or debt rows in DESE’s per-pupil file', 'published'),
         f('mteq', U(mteq['total']), 'Monty Tech instructional equipment, DESE, counted',
           'published'),
         f('mtk', U(mt['K09']), 'Monty Tech instructional equipment, Census capital',
           'published')],
        [con('One year, three rules: %s by DESE, %s net school spending, %s by the Census.'
             % (C.usd(d['lunenburg_total']), C.usd(nss['spent']), C.usd(lun['TCURELSC'])),
             ['dese', 'nss', 'cen'],
             {'a': U(d['lunenburg_total']), 'b': U(nss['spent']), 'c': U(lun['TCURELSC'])}),
         con('Net school spending leaves out grants and transportation; DESE’s figure counts both.',
             ['nss', 'dese', 'grants', 'trans'],
             notes=[step('The statute: it “shall not include any spending for school construction, '
                         'long-term debt service, school meals, transportation of students to and '
                         'from their homes”.', 'quote', cite=(statute, 'M.G.L. c.70 §2'))]),
         con('Neither state measure counts capital; the Census does, %s for Lunenburg in %s.'
             % (C.usd(lun['TCAPOUT']), C.fy(y)), ['cap', 'int', 'rows'],
             {'a': U(lun['TCAPOUT']), 'y': F(y)},
             notes=[step('Census, on Massachusetts: bond-funded construction is “accounted for in '
                         'the fiscal year that the bond principal is repaid”.', 'quote',
                         cite=(cdoc, 'Census Bureau, technical documentation, Massachusetts'))]),
         con('The rules split equipment: Monty Tech’s was %s to DESE and %s of capital to the Census.'
             % (C.usd(mteq['total']), C.usd(mt['K09'])), ['mteq', 'mtk'],
             {'a': U(mteq['total']), 'b': U(mt['K09'])},
             notes=[step('DESE’s form puts vocational equipment in 2420, counted, “irrespective of '
                         'unit cost”.', 'quote', allow=('2420',),
                         cite=(eoyr, 'DESE End of Year Report form, lines 3524-3529')),
                    step('Possibly the Census counts as capital only what districts code 7000. '
                         'Nothing here tests it.', 'hypothesis', allow=('7000',)),
                    step('Whether every district draws that line the same way is not visible.',
                         'gap', allow=('7000',),
                         closes='each district’s End of Year Financial Report workbook, '
                                       'with its 7000 and lease schedules')])],
        chart=TP.ranking('Lunenburg school spending under three rules', [
            ('DESE per-pupil total', [d['lunenburg_total'], None, None]),
            ('Net school spending', [nss['spent'], None, None]),
            ('Census Bureau', [lun['TCURELSC'], lun['TCAPOUT'], lun['I86']])], '$',
            stack=['Operating', 'Capital outlay', 'Interest on debt'],
            note='%s, the latest year all three publish. All three are spending after the year '
                 'closed, not budgets.' % C.fy(y), note_figures=yl),
        table=dict(caption='What each measure counts', views=[dict(
            key='rules', label='Who set the rule',
            note='DESE: its expenditures-by-function file and End of Year Report form. Net school '
                 'spending: M.G.L. c.70 §2. Census: its survey documentation.',
            columns=['DESE per pupil', 'Net school spending', 'Census Bureau'],
            kinds=['ledger', 'statute', 'ledger'],
            rows=[dict(label=a, cells=list(b)) for a, b in (
                ('School construction', ('Not counted', 'Not counted', 'Counted, apart')),
                ('Other capital, code 7000', ('Not counted', 'Not stated in §2', 'Counted, apart')),
                ('Debt service', ('Not counted', 'Not counted', 'Interest only, apart')),
                ('Transportation', ('Counted', 'Not counted', 'Counted')),
                ('School meals', ('Counted', 'Not counted', 'Counted')),
                ('Grants and revolving funds', ('Counted', 'Not counted', 'Not split by fund')),
                ('Instructional equipment, 2420', ('Counted', 'Not excluded by §2',
                                                   'A capital item')),
                ('Tuition to other districts', ('Counted', 'Counted', 'Counted, apart')))])]),
        sources=src)


def line_by_line():
    """PER PUPIL, LINE BY LINE. TJ, 15 October 2026: *"If we already report the health insurance
    to DESE, then we just need a page that breaks down the cost per pupil so it's very
    obvious."* DESE's per-pupil total for Lunenburg, split into the categories it is built
    from and footed to DESE's own total by per_pupil_measures.breakdown(); the twin of Monty
    Tech's page, drawn by the same two helpers so the two read alike. What the school BUDGET
    holds is read off the School health insurance page's payload (the FY2026 MUNIS ledger), not
    recomputed here."""
    b = PPM.breakdown(PPM.LUNENBURG, PPM.measures()['last_fy'])
    y = b['fy']
    cat = {c['code']: c for c in b['cats']}
    by_pp = sorted(b['cats'], key=lambda c: -c['pp'])
    if [c['code'] for c in by_pp[:2]] != ['TCHR', 'BENE']:
        fail('teachers then insurance are no longer the two largest categories, which the page '
             'says')
    lines = {r['code']: r for r in b['lines'] if r['where'] == 'In-District'}
    top = max(b['lines'], key=lambda r: r['grants'])
    if top['code'] != '3400':
        fail('food services is no longer the largest line grants and revolving funds paid')
    if top['gen'] != 0:
        fail('food services now has general fund money in it; the page says it had none')
    ret = lines['5250']
    SHI = {x['id']: x for x in load('topics/school-health-insurance.json')['facts']}
    app, sret, act = SHI['app']['value'], SHI['ret']['value'], SHI['act']['value']
    # The year the ledger figures are for is the payload's, read off its own labels.
    ly = {int(m) for k in ('app', 'act') for m in re.findall(r'FY(\d{4})', SHI[k]['label']['text'])}
    if len(ly) != 1:
        fail('school-health-insurance.json labels name no single year: %s' % sorted(ly))
    ly = ly.pop()
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    N = lambda v: figure(v, C.num(v))
    PU = figure(b['fte_total'], '{:,.1f}'.format(b['fte_total']), 'FTE pupils')
    f, con = LD.fact, TP.conclusion
    tc, be = cat['TCHR'], cat['BENE']
    src = [dict(label='Massachusetts DESE, expenditures by function, all funds — '
                      'district-expenditures-by-function.xlsx', href='/docs/' + PPM.KEY),
           dict(label='Lunenburg Budget Project — dese-radar.csv (DESE’s FTE pupil counts, '
                      'from RADAR)', href='/docs/data/dese-radar.csv'),
           dict(label='Town of Lunenburg — Town Accountant (MUNIS), general fund, FY2026 '
                      'period 12', href='/docs/town-ledgers/expenses/'
                                        'glytdbud-expense-fy2026-p12-gf-all.xlsx')]
    yl = {'y': F(y)}
    return TP.page(
        'per-pupil-line-by-line',
        'Lunenburg’s %s a pupil in %s, by what it paid for: insurance and grants are in it, '
        'capital is not.' % (C.usd(b['pp']), C.fy(y)),
        [f('pp', U(b['pp']), 'a pupil, all funds, %s, DESE' % C.fy(y), 'published', yl),
         f('total', U(b['total']), 'spent, all funds, %s' % C.fy(y), 'published', yl),
         f('fte', PU, 'FTE pupils DESE divides by', 'published'),
         f('tchr', U(tc['pp']), 'teachers, a pupil (our division)', 'published'),
         f('bene', U(be['pp']), 'insurance, retirement and other, a pupil', 'published'),
         f('ret', U(ret['total']), 'insurance for retired school staff, counted by DESE',
           'published'),
         f('grants', U(b['grants']), 'paid by grants and revolving funds', 'published'),
         f('food', U(top['grants']), 'food services, paid wholly by them', 'published'),
         f('cap', N(b['capital_rows']), 'rows coded capital (7000) or debt (8000) in DESE’s file',
           'published', allow=('7000', '8000')),
         f('app', app, 'the %s school appropriation' % C.fy(ly), 'published', {'y': F(ly)}),
         f('act', act, 'staff health insurance, inside that budget', 'published'),
         f('sret', sret, 'school retirees’ insurance, in the town’s budget', 'published')],
        [con('Teachers were %s of the %s a pupil; insurance, retirement and other, %s, came next.'
             % (C.usd(tc['pp']), C.usd(b['pp']), C.usd(be['pp'])), ['tchr', 'pp', 'bene', 'fte'],
             {'a': U(tc['pp']), 'b': U(b['pp']), 'c': U(be['pp'])}),
         con('Grants and revolving funds paid %s of it; their largest line, food services, was %s.'
             % (C.usd(b['grants']), C.usd(top['grants'])), ['grants', 'food', 'total'],
             {'a': U(b['grants']), 'b': U(top['grants'])}),
         con('None of it is capital or debt service: %s rows in DESE’s file carry those codes.'
             % C.num(b['capital_rows']), ['cap'], {'n': N(b['capital_rows'])}),
         con('The %s school budget holds %s of staff insurance; %s for its retirees is in the '
             'town’s.' % (C.fy(ly), act['text'], sret['text']), ['app', 'act', 'sret', 'ret'],
             {'y': F(ly), 'a': act, 'b': sret},
             notes=[step('How DESE’s general fund total reconciles to the school appropriation, '
                         'line by line, has not been worked out.', 'gap',
                         closes='the district’s End of Year Financial Report as filed with DESE, '
                                'schedule by schedule, for the same year')])],
        chart=PPM.breakdown_chart(b),
        table=PPM.breakdown_table(b),
        sources=src,
        finding_figures={'a': U(b['pp']), 'y': F(y)})


def build():
    PS = load('peer-spending.json')
    BV = load('budget-vs-actual.json')
    src = sources()
    S = lambda *names: [src[n] for n in names]
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    OF = lambda a, b, unit=None: figure(a, '%s of %s' % (C.num(a), C.num(b)), unit or None)
    f, con = LD.fact, TP.conclusion
    out = {}

    hd = PS['headline']
    fy = hd['fy']
    sw = {r['fy']: r for r in PS['statewide']}
    lun = next(r for r in PS['last_year'] if r['district'] == 'Lunenburg')
    six = sorted(PS['last_year'], key=lambda r: r['rank'])
    # ---------------------------------------------------------- the cross-checks
    if sw[fy]['lunenburg'] != hd['per_pupil'] or sw[fy]['rank'] != hd['statewide_rank']:
        fail('the headline and the statewide series disagree for FY%d' % fy)
    if lun['per_pupil'] != hd['per_pupil'] or abs(lun['total'] - hd['total']) > 0.5:
        fail('the headline and the six-district rows disagree for Lunenburg')
    if abs(hd['gen_fund'] + hd['grants_revolving'] - hd['total']) > 1:
        fail('general fund plus grants is no longer DESE’s total')
    if hd['statewide_spend_less'] != sw[fy]['districts'] - sw[fy]['rank']:
        fail('the rank and the count spending less no longer agree')
    if abs(hd['statewide_median'] - hd['per_pupil'] - hd['statewide_below_median']) > 0.5:
        fail('the distance below the median no longer recomputes')
    # DESE's per-pupil total is its total over TOTAL FTE pupils (per-pupil-spending.md, "a note
    # on the instrument"); the arithmetic below relies on it, so it is asserted, not assumed.
    if abs(hd['total'] / hd['fte_total'] - hd['per_pupil']) > 1:
        fail('DESE’s per-pupil total is no longer its total over total FTE pupils')
    bq_years = [r for r in PS['statewide'] if r['in_bottom_quarter']]
    if any(r['lunenburg'] >= r['p25'] for r in bq_years) or len(bq_years) != len(PS['statewide']):
        fail('the bottom-quarter claim no longer holds for every year')

    # ---------------------------------------------------------- spending per pupil
    y0 = min(sw)
    r0 = sw[y0]
    best = max(PS['statewide'], key=lambda r: r['spend_less'] / r['districts'])
    RK = lambda r: OF(r['rank'], r['districts'])
    swy = sorted(sw)
    pp_chart = TP.series('Spending a pupil against the state', [C.fy(y) for y in swy], [
        TP.track('Lunenburg', [sw[y]['lunenburg'] for y in swy]),
        TP.track('State median', [sw[y]['median'] for y in swy]),
        TP.track('First quartile', [sw[y]['p25'] for y in swy])], '$',
        note='All funds, over total FTE pupils, as DESE reports each closed year.')
    out['per-pupil-spending'] = TP.page(
        'per-pupil-spending',
        'Lunenburg spent %s a pupil in %s, all funds, against a state median of %s.'
        % (C.usd(hd['per_pupil']), C.fy(fy), C.usd(hd['statewide_median'])),
        [f('pp', U(hd['per_pupil']), 'a pupil, all funds, %s, DESE' % C.fy(fy), 'published',
           {'y': F(fy)}),
         f('med', U(hd['statewide_median']), 'the median of %s districts' % C.num(sw[fy]['districts']),
           'published', {'n': N(sw[fy]['districts'])}),
         f('p25', U(hd['statewide_p25']), 'the first quartile, the same districts', 'published'),
         f('below', U(hd['statewide_below_median']), 'below the median (our arithmetic)',
           'published'),
         f('rank', RK(sw[fy]), 'districts, highest spending first, %s' % C.fy(fy), 'published',
           {'y': F(fy)}),
         f('bq', OF(len(bq_years), len(PS['statewide']), 'years'),
           'years below the first quartile, %s to %s' % (C.fy(y0), C.fy(fy)), 'published',
           {'y': F(y0), 'z': F(fy)}),
         f('pp0', U(r0['lunenburg']), 'a pupil, all funds, %s' % C.fy(y0), 'published',
           {'y': F(y0)}),
         f('rank0', RK(r0), 'rank, %s' % C.fy(y0), 'published', {'y': F(y0)}),
         f('best', RK(best), 'its highest standing, %s' % C.fy(best['fy']), 'published',
           {'y': F(best['fy'])})],
        [con('DESE counts every fund and every pupil: %s a pupil against a median of %s.'
             % (C.usd(hd['per_pupil']), C.usd(hd['statewide_median'])), ['pp', 'med', 'below'],
             {'a': U(hd['per_pupil']), 'b': U(hd['statewide_median'])}),
         con('It ranked %s in %s, below the first quartile in all %s years DESE publishes.'
             % (RK(sw[fy])['text'], C.fy(fy), C.num(len(bq_years))), ['rank', 'bq', 'p25'],
             {'r': RK(sw[fy]), 'y': F(fy), 'n': N(len(bq_years))}),
         con('In %s it spent %s a pupil and ranked %s; its highest standing was %s in %s.'
             % (C.fy(y0), C.usd(r0['lunenburg']), RK(r0)['text'], RK(best)['text'],
                C.fy(best['fy'])), ['pp0', 'rank0', 'best'],
             {'y': F(y0), 'a': U(r0['lunenburg']), 'r': RK(r0), 'b': RK(best),
              'z': F(best['fy'])},
             notes=[step('Whether spending less is a choice or a constraint is not in any of these '
                         'figures: the levy limit, the district’s request and Town Meeting’s vote '
                         'all land in one number.', 'gap',
                         closes='nothing published settles it; the nearest is the district’s '
                                'level-service request against the appropriation voted, by year')])],
        table=dict(caption='Spending a pupil, all funds, against every district', views=[dict(
            key='statewide', label='DESE, every district', total_col=-1, kinds=['ledger'] * 4,
            columns=['Lunenburg', 'State median', 'First quartile', 'Rank'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.usd(r['lunenburg']), C.usd(r['median']),
                                                   C.usd(r['p25']), RK(r)['text']])
                  for r in sorted(PS['statewide'], key=lambda r: -r['fy'])],
            note='DESE’s end-of-year finance collection: all funds, over total FTE pupils, '
                 'reported after each year closed. Not a budget and not the appropriation.')]),
        chart=pp_chart,
        said=[said(PS, 'bottom-ten'), said(PS, 'little-per-pupil')],
        sources=S('district-expenditures-by-function.xlsx', 'dese-function-statewide.csv'),
        finding_figures={'a': U(hd['per_pupil']), 'y': F(fy), 'b': U(hd['statewide_median'])})

    # ---------------------------------------------------------- spending by function
    cats = {c['code']: c for c in PS['statewide_categories']}
    nbq = sum(1 for c in cats.values() if c['in_bottom_quarter'])
    pdev, matl, tchr, tser = cats['PDEV'], cats['MATL'], cats['TCHR'], cats['TSER']
    if min(cats.values(), key=lambda c: c['share_of_median']) is not pdev:
        fail('professional development is no longer the furthest below its median')
    if max(cats.values(), key=lambda c: c['share_of_median']) is not tser:
        fail('other teaching services is no longer the nearest its median')
    # Pupil services drawn as its function codes (the count of categories in the bottom
    # quarter, above, stays a count of DESE's eleven categories).
    sw_serv, sw_none = serv_statewide(fy)
    sf_by = {FN_CHART[c['code']].capitalize(): c for c in cats.values() if c['code'] != 'SERV'}
    sf_by.update({'Pupil services: ' + SERV_NAME[c['code']]: c for c in sw_serv})
    sf_rows = [(l, 100 * c['share_of_median']) for l, c in sf_by.items()]
    out['spending-by-function'] = TP.page(
        'spending-by-function',
        'Lunenburg was in the state’s bottom quarter on %s DESE spending categories in %s.'
        % (OF(nbq, len(cats))['text'], C.fy(fy)),
        [f('bq', OF(nbq, len(cats), 'categories'), 'DESE categories in the bottom quarter, %s'
           % C.fy(fy), 'published', {'y': F(fy)}),
         f('pdev', U(pdev['lunenburg']), 'professional development, a pupil', 'published'),
         f('pdevm', U(pdev['median']), 'its state median', 'published'),
         f('matl', U(matl['lunenburg']), 'materials, equipment and technology, a pupil',
           'published'),
         f('matlm', U(matl['median']), 'its state median', 'published'),
         f('tchr', U(tchr['lunenburg']), 'teachers, a pupil', 'published'),
         f('tchrm', U(tchr['median']), 'its state median', 'published'),
         f('tser', U(tser['lunenburg']), 'other teaching services, a pupil', 'published'),
         f('tserm', U(tser['median']), 'its state median', 'published'),
         f('tserr', OF(tser['rank'], tser['districts'], 'districts'),
           'other teaching services, rank', 'published')],
        [con('Professional development was %s a pupil against a median of %s; %s districts spent '
             'less.' % (C.usd(pdev['lunenburg']), C.usd(pdev['median']), C.num(pdev['spend_less'])),
             ['pdev', 'pdevm'], {'a': U(pdev['lunenburg']), 'b': U(pdev['median']),
                                 'n': N(pdev['spend_less'])}),
         con('Materials, equipment and technology was %s against %s; %s districts spent less.'
             % (C.usd(matl['lunenburg']), C.usd(matl['median']), C.num(matl['spend_less'])),
             ['matl', 'matlm'], {'a': U(matl['lunenburg']), 'b': U(matl['median']),
                                 'n': N(matl['spend_less'])},
             notes=[step('A dollar figure is not what it bought: no document held counts the '
                         'materials, or says how much of either line grants paid.', 'gap',
                         closes='the district’s inventory and purchasing records for the '
                                'materials and technology line')]),
         con('Teachers was %s against %s. Other teaching services, %s against %s, sat nearest '
             'its median.' % (C.usd(tchr['lunenburg']), C.usd(tchr['median']),
                              C.usd(tser['lunenburg']), C.usd(tser['median'])),
             ['tchr', 'tchrm', 'tser', 'tserm', 'tserr', 'bq'],
             {'a': U(tchr['lunenburg']), 'b': U(tchr['median']), 'c': U(tser['lunenburg']),
              'd': U(tser['median'])})],
        table=dict(caption='Spending a pupil by function, %s' % C.fy(fy), views=[dict(
            key='functions', label='DESE, every district', total_col=-1, kinds=['ledger'] * 3,
            columns=['Lunenburg', 'State median', 'Rank'],
            rows=[dict(label=c['desc'], cells=[C.usd(c['lunenburg']), C.usd(c['median']),
                                               OF(c['rank'], c['districts'])['text']])
                  for c in sorted(list(cats.values()) + sw_serv,
                                  key=lambda c: c['share_of_median'])]
            + [dict(label='Pupil services: %s' % c['desc'],
                    cells=['none reported', C.usd(c['median']), None]) for c in sw_none],
            note='Each function over in-district FTE pupils, as DESE computes it; rank is highest '
                 'spending first. Pupil services rows: each of its function codes against the '
                 'districts that report it. All funds, after the year closed.')]),
        chart=TP.ranking('Each function against its state median', sf_rows, '%',
            highlight=[l for l, c in sf_by.items() if c['in_bottom_quarter']],
            note='Lunenburg’s figure a pupil as a share of each state median, our division. '
                 'Pupil services shown by its own codes. Marked: bottom quarter.'),
        said=[said(PS, 'materials'), said(PS, 'sharing-pd')],
        sources=S('district-expenditures-by-function.xlsx', 'dese-function-statewide.csv'),
        finding_figures={'n': OF(nbq, len(cats)), 'y': F(fy)})

    # ---------------------------------------------------------- grants and revolving funds
    gshare = 100 * hd['grant_share']
    if abs(hd['grants_revolving'] / hd['total'] - hd['grant_share']) > 5e-4:
        fail('the grant share no longer recomputes')
    top = max(six, key=lambda r: r['grant_share'])
    if min(six, key=lambda r: r['grant_share']) is not lun or not hd['grant_share_is_lowest']:
        fail('Lunenburg’s grant share is no longer the smallest of the six')
    bene = next(c for c in PS['statewide_categories'] if c['code'] == 'BENE')
    out['grants-in-school-spending'] = TP.page(
        'grants-in-school-spending',
        'Of %s DESE counts for %s, grants and revolving funds paid %s: %s.'
        % (C.usd(hd['total']), C.fy(fy), C.usd(hd['grants_revolving']), C.pct(gshare)),
        [f('total', U(hd['total']), 'all funds, %s, DESE' % C.fy(fy), 'published', {'y': F(fy)}),
         f('gf', U(hd['gen_fund']), 'of it the general fund', 'published'),
         f('gr', U(hd['grants_revolving']), 'of it grants and revolving funds', 'published'),
         f('share', P(gshare), 'the grants’ share (our division)', 'published'),
         f('top', P(100 * top['grant_share']), '%s, the largest share of the six' % top['district'],
           'published'),
         f('bene', U(bene['lunenburg']), 'insurance, retirement and other, a pupil', 'published')],
        [con('The general fund was %s of the %s; grants and revolving funds the other %s.'
             % (C.usd(hd['gen_fund']), C.usd(hd['total']), C.usd(hd['grants_revolving'])),
             ['total', 'gf', 'gr'], {'a': U(hd['gen_fund']), 'b': U(hd['total']),
                                     'c': U(hd['grants_revolving'])},
             notes=[step('How DESE’s general fund figure reconciles to the school appropriation '
                         'Town Meeting votes has not been worked out; they are two definitions.',
                         'gap', closes='the district’s End of Year Financial Report to DESE, '
                                       'schedule by schedule, for the same year')]),
         con('At %s the share was the smallest of the six districts this project compares; %s’s '
             'was %s.' % (C.pct(gshare), top['district'], C.pct(100 * top['grant_share'])),
             ['share', 'top'], {'a': P(gshare), 'b': P(100 * top['grant_share'])}),
         con('DESE’s total also counts insurance, retirement and other at %s a pupil.'
             % C.usd(bene['lunenburg']), ['bene'], {'a': U(bene['lunenburg'])})],
        table=dict(caption='All funds and the general fund, %s' % C.fy(fy), views=[dict(
            key='funds', label='The six districts this project compares', total_col=0,
            kinds=['ledger'] * 3, columns=['All funds', 'General fund', 'Grants’ share'],
            rows=[dict(label=r['district'], cells=[C.usd(r['total']), C.usd(r['gen_fund']),
                                                   C.pct(100 * r['grant_share'])]) for r in six],
            note='DESE’s end-of-year finance collection. The six are this project’s choice; no '
                 'document records the criterion.')]),
        chart=TP.ranking('Grants and revolving funds, share of all funds',
                         [(short(r['district']), 100 * r['grant_share']) for r in six], '%',
                         highlight='Lunenburg',
                         note='DESE’s all-funds total for %s. The six districts are this project’s '
                              'choice.' % C.fy(fy), note_figures={'y': F(fy)}),
        said=[said(PS, 'grant-pd')],
        sources=S('district-expenditures-by-function.xlsx', 'dese-function-expenditure.csv'),
        finding_figures={'a': U(hd['total']), 'y': F(fy), 'b': U(hd['grants_revolving']),
                         'p': P(gshare)})

    # ---------------------------------------------------------- reaching the state median
    pupils = hd['fte_total']
    PU = figure(pupils, '{:,.1f}'.format(pupils), 'FTE pupils')
    need = hd['statewide_median'] * pupils
    need25 = hd['statewide_p25'] * pupils
    more, more25 = need - hd['total'], need25 - hd['total']
    mpct = 100 * (need / hd['total'] - 1)
    out['cost-of-the-median'] = TP.page(
        'cost-of-the-median',
        'At the %s state median a pupil, Lunenburg would have spent %s, by our arithmetic.'
        % (C.fy(fy), C.usd(need)),
        [f('med', U(hd['statewide_median']), 'the state median a pupil, %s' % C.fy(fy),
           'published', {'y': F(fy)}),
         f('pupils', PU, 'FTE pupils DESE divides by, %s' % C.fy(fy), 'published', {'y': F(fy)}),
         f('spent', U(hd['total']), 'spent, all funds, %s' % C.fy(fy), 'published', {'y': F(fy)}),
         f('need', U(need), 'at the median, all funds (ours)', 'estimate'),
         f('more', U(more), 'more than was spent (ours)', 'estimate'),
         f('mpct', P(mpct), 'more, as a share (ours)', 'estimate'),
         f('need25', U(need25), 'at the first quartile (ours)', 'estimate'),
         f('more25', U(more25), 'more than was spent (ours)', 'estimate')],
        [con('The median’s %s for each of %s pupils comes to %s.'
             % (C.usd(hd['statewide_median']), PU['text'], C.usd(need)), ['med', 'pupils', 'need'],
             {'a': U(hd['statewide_median']), 'n': PU, 'b': U(need)}),
         con('That is %s more than the %s spent, or %s more.'
             % (C.usd(more), C.usd(hd['total']), C.pct(mpct)), ['more', 'spent', 'mpct'],
             {'a': U(more), 'b': U(hd['total']), 'p': P(mpct)},
             notes=[step('It is a figure for all funds, not for the appropriation, and how much of '
                         'the distance grants nobody in town votes on could cover is not '
                         'established.', 'gap',
                         closes='the district’s grant awards by year, set against DESE’s '
                                'all-funds total for the same years')]),
         con('The first quartile would have taken %s, or %s more.' % (C.usd(need25), C.usd(more25)),
             ['need25', 'more25'], {'a': U(need25), 'b': U(more25)}),
         con('No document sets the median as a target; it is a place in the distribution.',
             ['med'])],
        chart=TP.series('Spent against the state median',
                        ['Spent', 'At the first quartile', 'At the median'], [
            TP.track('Spent, all funds, DESE', [hd['total'], None, None], 'published', 'bar'),
            TP.track('Ours, DESE’s rate times its pupils', [None, need25, need], 'estimate',
                     'bar')], '$', stacked=True,
            note='%s, all funds. The two right-hand bars are our multiplication, not a target.'
                 % C.fy(fy), note_figures={'y': F(fy)}),
        sources=S('district-expenditures-by-function.xlsx', 'dese-function-statewide.csv',
                  'dese-function-expenditure.csv'),
        finding_figures={'y': F(fy), 'a': U(need)})

    # ---------------------------------------------------------- comparison districts
    tot = defaultdict(dict)
    for r in PS['totals']:
        tot[r['fy']][r['district']] = r
    lun_ranks = {y: d['Lunenburg']['rank'] for y, d in tot.items()}
    if min(lun_ranks.values()) != hd['best_rank'] or max(lun_ranks.values()) != hd['worst_rank']:
        fail('the best and worst ranks among the six no longer recompute')
    if len(six) != 6 or lun['rank'] != lun['of'] or lun['of'] != 6:
        fail('the prose says Lunenburg is sixth of six; the payload no longer does')
    nxt = six[-2]
    diff = nxt['per_pupil'] - lun['per_pupil']
    hi6 = six[0]
    Ord = lambda n: figure(n, {1: '1st', 2: '2nd', 3: '3rd'}.get(n, '%dth' % n), 'rank')
    out['comparison-districts'] = TP.page(
        'comparison-districts',
        'Of six districts this project chose to compare, Lunenburg spent the least a pupil in %s.'
        % C.fy(fy),
        [f('lun', U(lun['per_pupil']), 'Lunenburg, a pupil, all funds, %s' % C.fy(fy), 'published',
           {'y': F(fy)}),
         f('next', U(nxt['per_pupil']), '%s, next above' % nxt['district'], 'published'),
         f('diff', U(diff), 'between the two (our arithmetic)', 'published'),
         f('hi', U(hi6['per_pupil']), '%s, the highest of the six' % hi6['district'], 'published'),
         f('rank', OF(lun['rank'], lun['of'], 'districts'), 'Lunenburg’s place, %s' % C.fy(fy),
           'published', {'y': F(fy)}),
         f('best', Ord(hd['best_rank']), 'its best place among the six, %s to %s'
           % (C.fy(y0), C.fy(fy)), 'published', {'y': F(y0), 'z': F(fy)})],
        [con('Lunenburg spent %s a pupil, sixth of six; %s spent %s more.'
             % (C.usd(lun['per_pupil']), nxt['district'], C.usd(diff)), ['lun', 'next', 'diff',
                                                                          'rank'],
             {'a': U(lun['per_pupil']), 'b': U(diff)},
             notes=[step(**DIST.topic_step())]),
         con('In %s years its place among the six was never better than %s.'
             % (C.num(len(lun_ranks)), Ord(hd['best_rank'])['text']), ['best'],
             {'n': N(len(lun_ranks)), 'r': Ord(hd['best_rank'])}),
         con('%s spent the most, %s; the statewide rank does not depend on this set.'
             % (hi6['district'], C.usd(hi6['per_pupil'])), ['hi'], {'a': U(hi6['per_pupil'])},
             notes=[step('The six are this project’s choice and no document records the '
                         'criterion; a different six would give a different place.', 'gap',
                         closes='DESE’s DART comparison group for Lunenburg, which names the '
                                'districts DESE considers similar and its criteria')])],
        table=dict(caption='The six districts, %s' % C.fy(fy), views=[dict(
            key='six', label='Chosen by this project', total_col=-1, kinds=['ledger'] * 3,
            columns=['A pupil', 'All funds', 'FTE pupils'],
            rows=[dict(label=r['district'], cells=[C.usd(r['per_pupil']), C.usd(r['total']),
                                                   '{:,.1f}'.format(r['fte_total'])])
                  for r in six],
            note='DESE’s end-of-year finance collection and RADAR. Ayer stands in for Ayer '
                 'Shirley before the two regionalised for %s.' % C.fy(PS['first_comparable_fy']))]),
        chart=TP.ranking('Spending a pupil, six districts',
                         [(short(r['district']), r['per_pupil']) for r in six], '$',
                         highlight='Lunenburg',
                         note='All funds, %s. The six are this project’s choice; no document '
                              'records why.' % C.fy(fy), note_figures={'y': F(fy)}),
        said=[said(PS, 'outcomes')],
        sources=S('district-expenditures-by-function.xlsx', 'radar-district-comparison.xlsx',
                  'dese-function-expenditure.csv'),
        finding_figures={'y': F(fy)})

    # ---------------------------------------------------------- spending and pupils
    dec = {r['district']: r for r in PS['decomposition']}
    for r in dec.values():
        if abs((1 + r['spend_pct']) / (1 + r['pupils_pct']) - 1 - r['per_pupil_pct']) > 0.002:
            fail('%s: spending over pupils no longer gives the per-pupil change' % r['district'])
    ld, nm = dec['Lunenburg'], dec['North Middlesex']
    slo = min(dec.values(), key=lambda r: r['spend_pct'])
    shi = max(dec.values(), key=lambda r: r['spend_pct'])
    plo = min(dec.values(), key=lambda r: r['pupils_pct'])
    if plo is not nm:
        fail('North Middlesex is no longer the district that lost the most pupils')
    yA = PS['first_comparable_fy']
    SP = lambda v: P(100 * v)
    dorder = sorted(dec, key=lambda d: dec[d]['pupils_pct'])
    out['spending-and-pupils'] = TP.page(
        'spending-and-pupils',
        'From %s to %s Lunenburg’s spending rose %s and its pupils fell %s; North Middlesex lost %s.'
        % (C.fy(yA), C.fy(fy), C.pct(100 * ld['spend_pct']), C.pct(-100 * ld['pupils_pct']),
           C.pct(-100 * nm['pupils_pct'])),
        [f('lsp', SP(ld['spend_pct']), 'Lunenburg’s spending, %s to %s' % (C.fy(yA), C.fy(fy)),
           'published', {'y': F(yA), 'z': F(fy)}),
         f('lpu', SP(ld['pupils_pct']), 'its FTE pupils, the same years', 'published'),
         f('lpp', SP(ld['per_pupil_pct']), 'its figure a pupil', 'published'),
         f('slo', SP(slo['spend_pct']), 'the smallest spending rise, %s' % slo['district'],
           'published'),
         f('shi', SP(shi['spend_pct']), 'the largest, %s' % shi['district'], 'published'),
         f('nmpu', SP(nm['pupils_pct']), 'North Middlesex’s FTE pupils', 'published'),
         f('nmpp', SP(nm['per_pupil_pct']), 'North Middlesex’s figure a pupil', 'published')],
        [con('The six districts this project compares raised spending %s to %s; Lunenburg’s %s sat '
             'between.' % (C.pct(100 * slo['spend_pct']), C.pct(100 * shi['spend_pct']),
                           C.pct(100 * ld['spend_pct'])), ['slo', 'shi', 'lsp'],
             {'a': SP(slo['spend_pct']), 'b': SP(shi['spend_pct']), 'c': SP(ld['spend_pct'])}),
         con('Pupils moved further apart: North Middlesex lost %s of its pupils, Lunenburg %s.'
             % (C.pct(-100 * nm['pupils_pct']), C.pct(-100 * ld['pupils_pct'])), ['nmpu', 'lpu'],
             {'a': P(-100 * nm['pupils_pct']), 'b': P(-100 * ld['pupils_pct'])},
             notes=[step(**DIST.topic_step())]),
         con('So North Middlesex’s figure a pupil rose %s and Lunenburg’s %s; a ratio moves with '
             'both halves.' % (C.pct(100 * nm['per_pupil_pct']), C.pct(100 * ld['per_pupil_pct'])),
             ['nmpp', 'lpp'], {'a': SP(nm['per_pupil_pct']), 'b': SP(ld['per_pupil_pct'])},
             notes=[step('Whether a district with fewer pupils needs less money, or buys more for '
                         'each child with the same money, is not something these figures can '
                         'separate.', 'gap',
                         closes='nothing published settles it; DESE’s staffing and class-size '
                                'files would bound it district by district')])],
        table=dict(caption='Change from %s to %s' % (C.fy(yA), C.fy(fy)), views=[dict(
            key='change', label='The six districts this project compares', total_col=-1,
            kinds=['ledger'] * 3, columns=['Spending', 'FTE pupils', 'A pupil'],
            rows=[dict(label=r['district'], cells=[C.pct(100 * r['spend_pct']),
                                                   C.pct(100 * r['pupils_pct']),
                                                   C.pct(100 * r['per_pupil_pct'])])
                  for r in sorted(dec.values(), key=lambda r: -r['per_pupil_pct'])],
            note='Changes are our arithmetic on DESE’s totals, total FTE pupils and per-pupil '
                 'figures. %s is the first year Ayer Shirley exists as one district.' % C.fy(yA))]),
        chart=TP.series('Spending and pupils, change by district',
                        [AXIS.get(d, short(d)) for d in dorder], [
            TP.track('Spending', [100 * dec[d]['spend_pct'] for d in dorder], 'published', 'bar'),
            TP.track('FTE pupils', [100 * dec[d]['pupils_pct'] for d in dorder], 'published',
                     'bar')], '%',
            note='Each from %s to %s: our arithmetic on DESE’s totals and pupil counts.'
                 % (C.fy(yA), C.fy(fy)), note_figures={'y': F(yA), 'z': F(fy)}),
        sources=S('district-expenditures-by-function.xlsx', 'radar-district-comparison.xlsx',
                  'dese-function-expenditure.csv'),
        finding_figures={'y': F(yA), 'z': F(fy), 'a': SP(ld['spend_pct']),
                         'b': P(-100 * ld['pupils_pct']), 'c': P(-100 * nm['pupils_pct'])})

    # ---------------------------------------------------------- gap by function
    ch = PS['category_headline']
    med_d = ch['median_peer']
    others = sorted(v for k, v in ch['by_district'].items() if k != 'Lunenburg')
    if ch['by_district'][med_d] != others[len(others) // 2] or len(others) != 5:
        fail('%s is no longer the middle of the other five' % med_d)
    if abs(sum(c['gap'] for c in PS['categories']) - ch['gap']) > 0.5:
        fail('the gaps by function no longer sum to the in-district gap')
    if abs(ch['lunenburg'] - ch['peer'] - ch['gap']) > 0.5:
        fail('the in-district gap no longer recomputes')
    gc = {c['code']: c for c in PS['categories']}
    # PUPIL SERVICES BY ITS CODES. Each district's category figure a pupil is split in
    # proportion to its function totals -- our division, so the parts add exactly to the
    # figure DESE prints and the gap still sums.
    sv = gc['SERV']
    lp, lc = serv_totals(fy, 'Lunenburg')
    mp, mc = serv_totals(fy, med_d)
    gparts = []
    for code, name in SERV_CODES:
        lv, mv = sv['lunenburg'] * lp.get(code, 0) / lc, sv['median_peer'] * mp.get(code, 0) / mc
        if lv or mv:
            gparts.append(dict(code='SERV-' + code, desc='Pupil services: ' + name,
                               chart='Pupil services: ' + name, lunenburg=lv, median_peer=mv,
                               gap=lv - mv, none=not lp.get(code)))
    if abs(sum(g['gap'] for g in gparts) - sv['gap']) > 0.5:
        fail('the pupil-services parts no longer add to its gap')
    gcats = [dict(c, chart=FN_CHART[c['code']].capitalize()) for c in PS['categories']
             if c['code'] != 'SERV'] + gparts
    if abs(sum(c['gap'] for c in gcats) - ch['gap']) > 0.5:
        fail('the gaps by function, pupil services split, no longer sum to the in-district gap')
    big2 = sorted(gcats, key=lambda c: c['gap'])[:2]
    pos = max(gcats, key=lambda c: c['gap'])
    # A part Lunenburg reports nothing under, against a district that does.
    unrep = [g for g in gparts if g['none'] and g['median_peer']]
    mn = SHORT.get(med_d, med_d)
    G = lambda v: U(-v)
    gs = sorted(gparts, key=lambda g: g['gap'])
    out['gap-by-function'] = TP.page(
        'gap-by-function',
        'In-district, Lunenburg spent %s a pupil less than %s, the middle of the six this project '
        'chose.' % (C.usd(-ch['gap']), mn),
        [f('lun', U(ch['lunenburg']), 'Lunenburg, in-district, a pupil, %s' % C.fy(fy), 'published',
           {'y': F(fy)}),
         f('mid', U(ch['peer']), '%s, the middle of the other five' % mn, 'published'),
         f('gap', G(ch['gap']), 'less a pupil (our arithmetic)', 'published')]
        + [f(c['code'].lower(), U(c['gap']), '%s, against %s' % (FN[c['code']], mn),
             'published') for c in PS['categories']
           if c['code'] in ('TCHR', 'LDRS', 'OPMN', 'MATL', 'PDEV', 'TSER')]
        + [f(g['code'].lower(), U(g['gap']), '%s, against %s'
             % (g['desc'][len('Pupil services: '):], mn), 'published')
           for g in sorted(gparts, key=lambda g: g['gap'])[:3]],
        [con('Lunenburg’s in-district figure was %s against %s’s %s: %s less.'
             % (C.usd(ch['lunenburg']), mn, C.usd(ch['peer']), C.usd(-ch['gap'])),
             ['lun', 'mid', 'gap'], {'a': U(ch['lunenburg']), 'b': U(ch['peer']),
                                     'c': G(ch['gap'])},
             notes=[step('The comparison district is the middle of a set this project chose; '
                         'no document records why these six.', 'gap',
                         closes='DESE’s DART comparison group for Lunenburg, with its criteria')]),
         con('%s (%s) and %s (%s) were the two largest parts of the difference.'
             % (big2[0]['desc'], C.usd(big2[0]['gap']), big2[1]['desc'].lower(),
                C.usd(big2[1]['gap'])), [c['code'].lower() for c in big2],
             {'a': U(big2[0]['gap']), 'b': U(big2[1]['gap'])}),
         con('%s ran the other way, %s above %s.' % (FN[pos['code']].capitalize(),
                                                    C.usd(pos['gap']), mn),
             [pos['code'].lower()], {'a': U(pos['gap'])}),
         con('Within pupil services, %s (%s) and %s (%s) were the largest parts.'
             % (gs[0]['desc'][len('Pupil services: '):], C.usd(gs[0]['gap']),
                gs[1]['desc'][len('Pupil services: '):], C.usd(gs[1]['gap'])),
             [g['code'].lower() for g in gs[:3]],
             {'a': U(gs[0]['gap']), 'b': U(gs[1]['gap'])},
             notes=[step('%s spends %s a pupil on %s; Lunenburg reports nothing there. The '
                         'same work may be coded to another function here.'
                         % (mn, C.usd(unrep[0]['median_peer']),
                            unrep[0]['desc'][len('Pupil services: '):]),
                         'hypothesis', {'a': U(unrep[0]['median_peer'])})] if unrep else ())],
        table=dict(caption='In-district spending a pupil, by function, %s' % C.fy(fy), views=[dict(
            key='gap', label='Lunenburg against %s' % mn, total_col=-1, kinds=['ledger'] * 3,
            columns=['Lunenburg', mn, 'Difference'],
            rows=[dict(label=c['desc'], cells=[C.usd(c['lunenburg']), C.usd(c['median_peer']),
                                               C.usd(c['gap'])])
                  for c in sorted(gcats, key=lambda c: c['gap'])],
            note='DESE’s figures over in-district FTE pupils. Pupil services split by its function '
                 'codes, in proportion to each district’s totals (our division). Against one '
                 'district, because medians of parts do not add up.')]),
        chart=TP.ranking('Difference a pupil, by function',
                         [(c['chart'], c['gap']) for c in gcats],
                         '$', note='Lunenburg less %s, in-district, a pupil, %s. Below zero, '
                                   'Lunenburg spent less.' % (mn, C.fy(fy)),
                         note_figures={'y': F(fy)}),
        sources=S('district-expenditures-by-function.xlsx', 'dese-function-expenditure.csv'),
        finding_figures={'a': G(ch['gap'])})
    if 'TCHR' not in [c['code'] for c in big2]:
        fail('teachers is no longer among the two largest parts of the gap')

    # ---------------------------------------------------------- average teacher salary
    T = sorted(PS['teachers'], key=lambda r: -r['average_salary'])
    tl = next(r for r in T if r['is_lunenburg'])
    srank = T.index(tl) + 1
    tp = sorted(PS['teachers'], key=lambda r: -r['per_pupil'])
    prank = tp.index(tl) + 1
    if tl['per_pupil'] != gc['TCHR']['lunenburg']:
        fail('the teachers tables disagree on Lunenburg’s Teachers figure')
    worst = 100 * PS['teachers_meta']['worst_gap']
    if len(T) != 6 or abs(max(abs(1 - r['salary_share_of_spend_per_fte']) for r in T)
                          - PS['teachers_meta']['worst_gap']) > 1e-4:
        fail('the six teachers rows no longer give the stated worst gap')
    out['average-teacher-salary'] = TP.page(
        'average-teacher-salary',
        'Lunenburg’s average teacher salary was %s in %s, %s of the six districts this project '
        'compares.' % (C.usd(tl['average_salary']), C.fy(fy), Ord(srank)['text']),
        [f('sal', U(tl['average_salary']), 'average teacher salary, %s, DESE' % C.fy(fy),
           'published', {'y': F(fy)}),
         f('salr', OF(srank, len(T), 'districts'), 'its place, highest first', 'published'),
         f('hi', U(T[0]['average_salary']), '%s, the highest' % T[0]['district'], 'published'),
         f('lo', U(T[-1]['average_salary']), '%s, the lowest' % T[-1]['district'], 'published'),
         f('fte', figure(tl['teacher_fte'], '%.1f' % tl['teacher_fte'], 'FTE'),
           'teacher FTE, %s' % C.fy(fy), 'published', {'y': F(fy)}),
         f('tchr', U(tl['per_pupil']), 'Teachers function, a pupil', 'published'),
         f('tchrr', OF(prank, len(tp), 'districts'), 'its place on that, highest first',
           'published')],
        [con('The average salary, %s, was %s of six; %s’s %s was first.'
             % (C.usd(tl['average_salary']), Ord(srank)['text'], T[0]['district'],
                C.usd(T[0]['average_salary'])), ['sal', 'salr', 'hi', 'lo'],
             {'a': U(tl['average_salary']), 'r': Ord(srank), 'b': U(T[0]['average_salary'])}),
         con('Spending on the Teachers function was %s a pupil, %s of the six.'
             % (C.usd(tl['per_pupil']), Ord(prank)['text']), ['tchr', 'tchrr', 'fte'],
             {'a': U(tl['per_pupil']), 'r': Ord(prank)}),
         con('In all six, Teachers spending over teacher FTE is DESE’s average salary within %s.'
             % C.pct(worst, 2), ['sal', 'tchr', 'fte'],
             {'p': P(worst, 2)},
             notes=[step('An average is not a pay scale: it moves with the mix of steps and lanes '
                         'as well as with raises, and the figures here cannot tell which.', 'gap',
                         closes='the teachers’ contract salary schedule and the count of '
                                'teachers on each step and lane, by year')])],
        table=dict(caption='Teachers, %s' % C.fy(fy), views=[dict(
            key='teachers', label='The six districts this project compares', total_col=-1,
            kinds=['ledger'] * 3, columns=['Average salary', 'Teacher FTE', 'Teachers a pupil'],
            rows=[dict(label=r['district'], cells=[C.usd(r['average_salary']),
                                                   '%.1f' % r['teacher_fte'],
                                                   C.usd(r['per_pupil'])]) for r in T],
            note='DESE’s RADAR file and end-of-year finance collection. Teachers a pupil is the '
                 'Teachers function over in-district FTE pupils, DESE’s own figure.')]),
        chart=TP.ranking('Average teacher salary, six districts',
                         [(short(r['district']), r['average_salary']) for r in T], '$',
                         highlight='Lunenburg',
                         note='DESE’s RADAR file, %s. The six are this project’s choice.' % C.fy(fy),
                         note_figures={'y': F(fy)}),
        sources=S('radar-district-comparison.xlsx', 'district-expenditures-by-function.xlsx',
                  'dese-radar.csv'),
        finding_figures={'a': U(tl['average_salary']), 'y': F(fy), 'r': Ord(srank)})

    # ---------------------------------------------------------- destination districts
    de = PS['destinations']
    rows = sorted(de['rows'], key=lambda r: -r['students'])
    mt = de['widest']
    lfl = de['like_for_like']
    if rows[0]['district'] != mt['district']:
        fail('Monty Tech no longer takes the most Lunenburg children')
    if sum(r['students'] for r in de['rows']) != de['listed_children']:
        fail('the destination rows no longer sum to the children listed')
    if de['children_where_more'] + de['children_where_less'] != de['listed_children']:
        fail('the children spending more and less no longer sum to those listed')
    if de['listed_children'] + de['below_threshold_children'] != de['left']:
        fail('the listed and unlisted children no longer sum to those who left')
    k12 = sorted((r for r in de['rows'] if r['shape'] == 'K-12 district'),
                 key=lambda r: -r['students'])
    if len(k12) != 2 or k12[0]['district'] != lfl['district']:
        fail('the K-12 destinations are no longer two, led by the payload’s like-for-like')
    LIT = ('K-12',)
    efy, ffy = de['enr_fy'], de['fin_fy']
    out['destination-district-spending'] = TP.page(
        'destination-district-spending',
        '%s of the %s children schooled elsewhere in %s went to districts that spend more a pupil.'
        % (C.num(de['children_where_more']), C.num(de['left']), C.fy(efy)),
        [f('more', OF(de['children_where_more'], de['left'], 'children'),
           'went to districts spending more a pupil', 'published'),
         f('mtn', N(mt['students'], 'children'), 'at Monty Tech, %s' % C.fy(efy), 'published',
           {'y': F(efy)}),
         f('mt', U(mt['per_pupil']), 'Monty Tech, a pupil, %s' % C.fy(ffy), 'published',
           {'y': F(ffy)}),
         f('lun', U(de['lunenburg']), 'Lunenburg, a pupil, %s' % C.fy(ffy), 'published',
           {'y': F(ffy)}),
         f('lfl', U(lfl['per_pupil']), '%s, a K-12 district, a pupil' % lfl['district'],
           'published', allow=LIT),
         f('k2', U(k12[1]['per_pupil']), '%s, the other K-12 district' % k12[1]['district'],
           'published', allow=LIT),
         f('less', N(de['children_where_less'], 'children'), 'at %s virtual districts spending less'
           % C.num(de['less']), 'published', {'n': N(de['less'])}),
         f('few', N(de['below_threshold_children'], 'children'), 'in %s other districts, not '
           'compared' % C.num(de['below_threshold']), 'published', {'n': N(de['below_threshold'])})],
        [con('Monty Tech took %s of the %s and spent %s a pupil to Lunenburg’s %s.'
             % (C.num(mt['students']), C.num(de['left']), C.usd(mt['per_pupil']),
                C.usd(de['lunenburg'])), ['mtn', 'mt', 'lun'],
             {'a': N(mt['students']), 'n': N(de['left']), 'b': U(mt['per_pupil']),
              'c': U(de['lunenburg'])}),
         con('The two K-12 districts on the list, %s and %s, spent %s and %s.'
             % (lfl['district'], k12[1]['district'], C.usd(lfl['per_pupil']),
                C.usd(k12[1]['per_pupil'])), ['lfl', 'k2'],
             {'a': U(lfl['per_pupil']), 'b': U(k12[1]['per_pupil'])}, allow=LIT),
         con('These are where children went, not districts chosen as peers.', ['more', 'less',
                                                                               'few'],
             notes=[step('What Lunenburg pays for a child at any of them is a different quantity: '
                         'an assessment, a school choice tuition or a charter tuition.', 'gap',
                         closes='the Town’s cherry sheet charges by receiving district, beside '
                                'DESE’s End of Year Financial Report for each district')])],
        table=dict(caption='Where Lunenburg children went', views=[dict(
            key='destinations', label='Every district taking %s or more' % C.num(de['threshold']),
            total_col=-1, kinds=['ledger'] * 3,
            columns=['Kind', 'Children, %s' % C.fy(efy), 'A pupil, %s' % C.fy(ffy)],
            rows=[dict(label=r['district'], cells=[r['shape'], C.num(r['students']),
                                                   C.usd(r['per_pupil'])]) for r in rows],
            note='DESE’s residents-sending and enrolment files for the children; its end-of-year '
                 'finance collection for spending, a year earlier. Kind is our reading of each '
                 'district.')]),
        chart=TP.ranking('Where children went, spending a pupil',
                         [(short(r['district']), r['per_pupil']) for r in rows]
                         + [('Lunenburg', de['lunenburg'])], '$', highlight='Lunenburg',
                         note='All funds, %s, for every district taking at least %s Lunenburg '
                              'children.' % (C.fy(ffy), C.num(de['threshold'])),
                         note_figures={'y': F(ffy), 'n': N(de['threshold'])}),
        said=[said(PS, 'vocational')],
        sources=S('district-expenditures-by-function.xlsx', 'dese-town-enrollment.csv',
                  'dese-function-expenditure.csv'),
        finding_figures={'a': N(de['children_where_more']), 'n': N(de['left']), 'y': F(efy)})

    # ---------------------------------------------------------- regional districts
    pp_of = {r['district']: r['per_pupil'] for r in PS['last_year']}
    pp_of.update({r['district']: r['per_pupil'] for r in de['rows']})
    reg = sorted(((d, pp_of[d]) for d in REGIONAL), key=lambda t: t[1])
    if len(reg) != 5:
        fail('the prose says five regional districts')
    cfy = 2026
    rt = {}
    rt_all = []
    lun_rt = None
    for r in csv.DictReader(open(CHERRY, encoding='utf-8')):
        if r['fy'] != str(cfy) or r['line'] != 'Regional Transportation':
            continue
        if r['population'] == 'Regional Schools':
            rt_all.append(float(r['amount']))
            for d, n in CHERRY_NAME.items():
                if r['name'] == n:
                    rt[d] = float(r['amount'])
        elif r['name'] == 'Lunenburg':
            lun_rt = float(r['amount'])
    if set(rt) != set(REGIONAL) or lun_rt is None:
        fail('a regional transportation line is missing from the FY%d cherry sheet' % cfy)
    rt_tot, rt_n = sum(rt_all), sum(1 for a in rt_all if a > 0)
    big_rt = sorted(((d, a) for d, a in rt.items() if d != REGIONAL[0]), key=lambda t: -t[1])[:2]
    out['regional-district-spending'] = TP.page(
        'regional-district-spending',
        'Five nearby regional districts spent %s to %s a pupil in %s; Lunenburg spent %s.'
        % (C.usd(reg[0][1]), C.usd(reg[-1][1]), C.fy(fy), C.usd(hd['per_pupil'])),
        [f('lo', U(reg[0][1]), '%s, the lowest of the five' % reg[0][0], 'published'),
         f('hi', U(reg[-1][1]), '%s, the highest' % SHORT.get(reg[-1][0], reg[-1][0]),
           'published'),
         f('lun', U(hd['per_pupil']), 'Lunenburg, a single-town district, %s' % C.fy(fy),
           'published', {'y': F(fy)}),
         f('rtall', U(rt_tot), 'regional transportation aid, cherry sheet, %s' % C.fy(cfy),
           'published', {'y': F(cfy)}),
         f('rtn', N(rt_n, 'districts'), 'regional districts it is paid to', 'published'),
         f('rt1', U(big_rt[0][1]), '%s’s share' % big_rt[0][0], 'published'),
         f('rt2', U(big_rt[1][1]), '%s’s share' % big_rt[1][0], 'published'),
         f('lunrt', U(lun_rt), 'Lunenburg’s line, %s' % C.fy(cfy), 'published', {'y': F(cfy)})],
        [con('The five span %s to %s a pupil; being regional does not fix the figure.'
             % (C.usd(reg[0][1]), C.usd(reg[-1][1])), ['lo', 'hi', 'lun'],
             {'a': U(reg[0][1]), 'b': U(reg[-1][1])}),
         con('The %s cherry sheet carries %s of regional transportation aid, to %s districts.'
             % (C.fy(cfy), C.usd(rt_tot), C.num(rt_n)), ['rtall', 'rtn', 'lunrt'],
             {'y': F(cfy), 'a': U(rt_tot), 'n': N(rt_n)},
             notes=[step('A regional district also pays for the buses it is reimbursed for, and '
                         'no published figure nets the two, so what regionalising would be worth '
                         'is not established.', 'gap',
                         closes='the regional districts’ own budgets, which state transportation '
                                'as a line and the reimbursement against it')]),
         con('%s’s share was %s; %s’s %s.' % (big_rt[0][0], C.usd(big_rt[0][1]), big_rt[1][0],
                                             C.usd(big_rt[1][1])), ['rt1', 'rt2'],
             {'a': U(big_rt[0][1]), 'b': U(big_rt[1][1])})],
        table=dict(caption='The regional districts compared', views=[dict(
            key='regional', label='Regional districts nearby', total_col=-1, kinds=['ledger'] * 2,
            columns=['A pupil, %s' % C.fy(fy), 'Transport aid, %s' % C.fy(cfy)],
            rows=[dict(label=d, cells=[C.usd(v), C.usd(rt[d])]) for d, v in reversed(reg)]
            + [dict(label='Lunenburg', cells=[C.usd(hd['per_pupil']), C.usd(lun_rt)])],
            note='Spending is DESE’s, all funds; aid is the DLS cherry sheet at the final state '
                 'budget. Which districts are regional is our reading of each.')]),
        chart=TP.ranking('Regional districts, spending a pupil',
                         [(short(d), v) for d, v in reg] + [('Lunenburg', hd['per_pupil'])], '$',
                         highlight='Lunenburg',
                         note='All funds, %s. Which districts are regional is our reading of each.'
                              % C.fy(fy), note_figures={'y': F(fy)}),
        said=[quote('transport-bill'), quote('not-regionalize')],
        sources=S('district-expenditures-by-function.xlsx', 'dls-cherry-sheet.csv',
                  next(n for n in src if n.startswith('CherrySheet-2026-RegionalSchools'))),
        finding_figures={'a': U(reg[0][1]), 'b': U(reg[-1][1]), 'y': F(fy),
                         'c': U(hd['per_pupil'])})

    # ---------------------------------------------------------- budget against actual
    SL, tied = school_ledger()
    yrs = sorted(SL)
    of_rev = {y: (SL[y]['spent'] + SL[y]['committed']) / SL[y]['revised'] for y in yrs}
    under = [y for y in yrs if of_rev[y] < 1]
    if len(under) != len(yrs):
        fail('a year spent more than its revised budget; the page’s finding no longer holds')
    far = min(yrs, key=lambda y: of_rev[y])
    near = max(yrs, key=lambda y: of_rev[y])
    over_orig = [y for y in yrs if SL[y]['spent'] + SL[y]['committed'] > SL[y]['original']]
    L = SL[yrs[-1]]
    yl = yrs[-1]
    # SPENT IS PAID PLUS STILL OWED (journal.py, WHAT "SPENT" MEANS). SL keeps the two apart
    # because the workbook tie compares `spent` with what the workbook prints, which is paid.
    L_spent = L['spent'] + L['committed']
    out['school-budget-against-actual'] = TP.page(
        'school-budget-against-actual',
        'The school general fund spent less than its revised budget in all %s years, %s to %s.'
        % (C.num(len(yrs)), C.fy(yrs[0]), C.fy(yl)),
        [f('under', OF(len(under), len(yrs), 'years'), 'years spent under the revised budget',
           'published'),
         f('far', P(100 * (1 - of_rev[far])), 'furthest under, %s' % C.fy(far), 'published',
           {'y': F(far)}),
         f('near', P(100 * (1 - of_rev[near]), 2), 'nearest its budget, %s' % C.fy(near),
           'published',
           {'y': F(near)}),
         f('over', OF(len(over_orig), len(yrs), 'years'), 'years spending passed the original '
           'budget', 'published'),
         f('rev', U(L['revised']), 'revised budget, %s' % C.fy(yl), 'published', {'y': F(yl)}),
         f('spent', U(L_spent), 'spent or still owed, %s' % C.fy(yl), 'published', {'y': F(yl)}),
         f('com', U(L['committed']), 'of it still owed at the close, %s' % C.fy(yl), 'published',
           {'y': F(yl)}),
         f('tied', OF(len(tied), len(tied), 'years'), 'years the workbook ties to the ledger, '
           'to the dollar', 'published')],
        [con('Each year spent less than that year’s revised budget; %s was furthest under, at %s.'
             % (C.fy(far), C.pct(100 * (1 - of_rev[far]))), ['under', 'far', 'near'],
             {'y': F(far), 'p': P(100 * (1 - of_rev[far]))},
             notes=[step('Why a year came in under — a vacancy, a cut, a grant, a transfer — is '
                         'not in either source.', 'gap',
                         closes='payroll detail by position and date for the year, with the '
                                'grant award records for the same year')]),
         con('Spending passed the original voted budget in %s years; the revised budget covered '
             'it each time.' % C.num(len(over_orig)), ['over'], {'n': N(len(over_orig))}),
         con('For %s: %s revised and %s spent, %s of it still owed at the close.'
             % (C.fy(yl), C.usd(L['revised']), C.usd(L_spent), C.usd(L['committed'])),
             ['rev', 'spent', 'com'],
             {'y': F(yl), 'a': U(L['revised']), 'b': U(L_spent), 'c': U(L['committed'])}),
         con('Before %s the figures are a workbook assembled from the ledger; where both exist '
             'they agree.' % C.fy(min(y for y in yrs if SL[y]['source'] == 'ledger')), ['tied'],
             {'y': F(min(y for y in yrs if SL[y]['source'] == 'ledger'))})],
        table=dict(caption='The school general fund, budget beside spending', views=[
            dict(key=k, label=lab, total_col=-1, kinds=[kind] * 4,
                 columns=['Original budget', 'Revised budget', 'Spent or committed',
                          'Of revised'],
                 rows=[dict(label=C.fy(y), cells=[C.usd(SL[y]['original']), C.usd(SL[y]['revised']),
                                                  C.usd(SL[y]['spent'] + SL[y]['committed']),
                                                  C.pct(100 * of_rev[y])])
                       for y in reversed(yrs) if SL[y]['source'] == srcname],
                 note=nt)
            for k, lab, kind, srcname, nt in (
                ('ledger', 'MUNIS, period 13', 'ledger', 'ledger',
                 'The Town Accountant’s year-end reports. Each year against its own budget; no '
                 'figure is set against another year’s.'),
                ('workbook', 'Finance Committee workbook', 'stated', 'workbook',
                 'Assembled from MUNIS by the Finance Committee; its school account rows, summed. '
                 'It prints no encumbrance column.'))]),
        chart=TP.series('School general fund, budget beside spending', [C.fy(y) for y in yrs], [
            TP.track('Spent or committed, MUNIS', [SL[y]['spent'] + SL[y]['committed']
                                                   if SL[y]['source'] == 'ledger' else None
                                                   for y in yrs], 'published', 'bar'),
            TP.track('Spent, Finance Committee workbook', [SL[y]['spent']
                                                           if SL[y]['source'] == 'workbook'
                                                           else None for y in yrs], 'stated', 'bar'),
            TP.track('Revised budget, MUNIS', [SL[y]['revised'] if SL[y]['source'] == 'ledger'
                                               else None for y in yrs], 'published', 'line'),
            TP.track('Revised budget, workbook', [SL[y]['revised'] if SL[y]['source'] == 'workbook'
                                                  else None for y in yrs], 'stated', 'line')],
            '$', stacked=True,
            note='Each year’s spending beside that year’s own budget; nothing is subtracted.'),
        sources=S('glytdbud-expense-fy2026-p13-gf-school.xlsx',
                  'glytdbud-expense-fy2025-p13-gf-school.xlsx',
                  'glytdbud-expense-fy2024-p13-gf-school.xlsx',
                  'general-fund-budget-vs-actuals-history.xlsx', 'gl-history.csv',
                  'munis-school-ytd.csv'),
        finding_figures={'n': N(len(yrs)), 'y': F(yrs[0]), 'z': F(yl)})

    # ---------------------------------------------------------- line-level misses
    cv = BV['coverage']
    spread = {b['bin']: b['count'] for b in BV['spread']}
    within = sum(b['count'] for b in BV['spread'] if b['centred'])
    quarter = sum(b['count'] for b in BV['spread'] if b['lo'] >= 0.25 or b['hi'] <= -0.25)
    if within != BV['within_2pct'] or sum(spread.values()) != cv['line_years']:
        fail('the spread no longer sums to the line-years measured')
    cf = {c['figure']: c for c in BV['conclusions']}
    if cf['within2']['figures']['big_miss']['value'] != quarter:
        fail('the count missing by more than a quarter no longer recomputes')
    sw_ = sorted(BV['same_way'], key=lambda r: r['mean_dollars'])
    sec = {s['section']: s for s in BV['sections']}
    sal, rest = sec['Salaries'], sec['Everything else']
    ev = BV['evidence']
    fy21 = BV['fy21']
    if ev['document_types'].get('restatement', 0) + ev['document_types'].get('forward', 0) != \
            ev['documents'] or ev['measured_years_ledger_backed']:
        fail('a measured year is now ledger-backed; the page’s caveat no longer holds')
    y1, y2 = cv['first_fy'], cv['last_fy']
    lyrs = [y for y in yrs if SL[y]['source'] == 'ledger']
    out['line-level-misses'] = TP.page(
        'line-level-misses',
        'Of %s budget lines and years the district restated, %s landed within %s of the line’s '
        'budget.' % (C.num(cv['line_years']), C.num(within), C.pct(2, 0)),
        [f('ly', N(cv['line_years'], 'line-years'), 'measured, %s to %s' % (C.fy(y1), C.fy(y2)),
           'published', {'y': F(y1), 'z': F(y2)}),
         f('w2', OF(within, cv['line_years'], 'line-years'), 'within %s of their budget'
           % C.pct(2, 0), 'published', {'p': P(2, 0)}),
         f('q', N(quarter, 'line-years'), 'missed by more than a quarter, either way',
           'published'),
         f('same', OF(len(sw_), BV['lines_with_four_years'], 'lines'),
           'missed the same way in every year', 'published'),
         f('big', U(-sw_[0]['mean_dollars']), 'the largest of those, under, a year', 'published'),
         f('sal', P(-100 * sal['pct']), 'salaries under budget, measured years', 'published'),
         f('rest', P(100 * rest['pct']), 'everything else over budget', 'published'),
         f('fy21', OF(fy21['identical'], fy21['lines'], 'lines'), '%s lines whose spent figure is '
           'the budget' % C.fy(2021), 'published', {'y': F(2021)})],
        [con('Only %s line-years landed within %s; %s missed by more than a quarter.'
             % (OF(within, cv['line_years'])['text'], C.pct(2, 0), C.num(quarter)),
             ['ly', 'w2', 'q'], {'a': OF(within, cv['line_years']), 'p': P(2, 0),
                                 'b': N(quarter)}),
         con('Just %s lines missed the same way every year; the largest averaged %s a year under.'
             % (OF(len(sw_), BV['lines_with_four_years'])['text'],
                C.usd(-sw_[0]['mean_dollars'])), ['same', 'big'],
             {'a': OF(len(sw_), BV['lines_with_four_years']), 'b': U(-sw_[0]['mean_dollars'])}),
         con('Salaries came in %s under across %s line-years; everything else %s over.'
             % (C.pct(-100 * sal['pct']), C.num(sal['line_years']), C.pct(100 * rest['pct'])),
             ['sal', 'rest'], {'a': P(-100 * sal['pct']), 'n': N(sal['line_years']),
                               'b': P(100 * rest['pct'])}),
         con('The spent column is the district restating its own books; in %s it repeats the '
             'budget.' % C.fy(2021), ['fy21'], {'y': F(2021)},
             notes=[step('None of the %s budget books behind it is a ledger, so money moved '
                         'between lines during a year cannot be seen here.' % C.num(ev['documents']),
                         'gap', {'n': N(ev['documents'])}, allow=(C.fy(lyrs[0]), C.fy(lyrs[-1])),
                         closes='the MUNIS year-end expense report for the school department '
                                'for each year wanted, as held for %s to %s'
                                % (C.fy(lyrs[0]), C.fy(lyrs[-1])))])],
        table=dict(caption='Lines that missed the same way every year', views=[dict(
            key='same', label='Four or more measured years', total_col=-1, kinds=['stated'] * 3,
            columns=['Direction', 'Years', 'Average a year'],
            rows=[dict(label=r['line'], cells=[r['direction'], C.num(r['years']),
                                               C.usd(r['mean_dollars'])]) for r in sw_],
            note='Each year’s budget against the same year’s restated figure, out of the '
                 'district’s own budget books. A line counts only if it was more than %s off '
                 'in every year.' % C.pct(100 * cv['same_way_threshold'], 0))]),
        chart=TP.series('How far each line landed from its budget',
                        [binlabel(b) for b in BV['spread']], [
            TP.track('Line-years, the district’s restated figures',
                     [b['count'] for b in BV['spread']], 'stated', 'bar')], 'line-years',
            note='Each bar is a range of percent over or under the same year’s budget. The '
                 'district’s own budget books, %s to %s.' % (C.fy(y1), C.fy(y2)),
            note_figures={'y': F(y1), 'z': F(y2)}),
        sources=S('line-history.csv'),
        finding_figures={'a': N(cv['line_years']), 'b': N(within), 'p': P(2, 0)})

    # ---------------------------------------------------------- the hub
    h = {}
    h['h-pp'] = f('h-pp', U(hd['per_pupil']), 'a pupil, all funds, %s' % C.fy(fy), 'published',
                  {'y': F(fy)})
    h['h-med'] = f('h-med', U(hd['statewide_median']), 'the state median', 'published')
    h['h-rank'] = f('h-rank', RK(sw[fy]), 'districts, highest spending first', 'published')
    h['h-bq'] = f('h-bq', OF(len(bq_years), len(PS['statewide']), 'years'),
                  'years in the state’s bottom quarter', 'published')
    h['h-fn'] = f('h-fn', OF(nbq, len(cats), 'functions'), 'spending functions in the bottom '
                  'quarter', 'published')
    h['h-six'] = f('h-six', OF(lun['rank'], lun['of'], 'districts'), 'place among six this '
                   'project chose', 'published')
    h['h-sal'] = f('h-sal', Ord(srank), 'average teacher salary among the six', 'published')
    h['h-more'] = f('h-more', OF(de['children_where_more'], de['left'], 'children'),
                    'schooled elsewhere, at districts spending more', 'published')
    h['h-mt'] = f('h-mt', U(mt['per_pupil']), 'Monty Tech a pupil, %s' % C.fy(ffy), 'published',
                  {'y': F(ffy)})
    h['h-under'] = f('h-under', OF(len(under), len(yrs), 'years'), 'school fund under its '
                     'revised budget', 'published')
    h['h-far'] = f('h-far', P(100 * (1 - of_rev[far])), 'furthest under, %s' % C.fy(far),
                   'published', {'y': F(far)})
    h['h-lines'] = f('h-lines', OF(within, cv['line_years'], 'line-years'), 'lines within %s of '
                     'budget' % C.pct(2, 0), 'published', {'p': P(2, 0)})
    tiers = [
        LD.tier('Against the state', [h['h-pp'], h['h-med'], h['h-rank'], h['h-bq'], h['h-fn']]),
        LD.tier('Against other districts', [h['h-six'], h['h-sal'], h['h-more'], h['h-mt']]),
        LD.tier('Budget against actual', [h['h-under'], h['h-far'], h['h-lines']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('%s a pupil ranked %s in %s, in the bottom quarter in all %s years.'
                      % (C.usd(hd['per_pupil']), RK(sw[fy])['text'], C.fy(fy),
                         C.num(len(bq_years))), ['h-pp', 'h-med', 'h-rank', 'h-bq'],
                      {'a': U(hd['per_pupil']), 'r': RK(sw[fy]), 'y': F(fy),
                       'n': N(len(bq_years))}),
        LD.conclusion('It was in the state’s bottom quarter on %s spending functions.'
                      % OF(nbq, len(cats))['text'], ['h-fn'], {'n': OF(nbq, len(cats))}),
        LD.conclusion('Of six districts this project chose, it spent least a pupil; its average '
                      'teacher salary was %s.' % Ord(srank)['text'], ['h-six', 'h-sal'], {'r': Ord(srank)}),
        LD.conclusion('%s children schooled elsewhere went to districts spending more a pupil.'
                      % OF(de['children_where_more'], de['left'])['text'], ['h-more', 'h-mt'],
                      {'n': OF(de['children_where_more'], de['left'])}),
        LD.conclusion('The school fund came in under its revised budget in all %s years; single '
                      'lines missed far more.' % C.num(len(yrs)), ['h-under', 'h-far', 'h-lines'],
                      {'n': N(len(yrs))}),
    ])
    out['what-per-pupil-counts'] = what_counts()
    out['per-pupil-line-by-line'] = line_by_line()
    out['school-spending'] = TP.hub(
        'school-spending',
        'Lunenburg spent %s a pupil in %s, all funds, against a state median of %s, and has sat in '
        'the state’s bottom quarter for %s years. Its school general fund spent under its revised '
        'budget every year from %s to %s.'
        % (C.usd(hd['per_pupil']), C.fy(fy), C.usd(hd['statewide_median']), C.num(len(bq_years)),
           C.fy(yrs[0]), C.fy(yl)),
        hub_ladder, chart=pp_chart,
        answer_figures={'a': U(hd['per_pupil']), 'y': F(fy), 'b': U(hd['statewide_median']),
                        'n': N(len(bq_years)), 'c': F(yrs[0]), 'd': F(yl)})

    out.update(school_committee_fund_pages())

    if sorted(k for k in out if k != 'school-spending') != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out

# --------------------------------------------------------------------- the School Committee's funds
# Absorbs the School Committee's finance page (/boards/school-committee/finance, `schoolfinance`),
# 14 October 2026, off the /reports shelves; the page stays the board's finance tab. Every figure
# is read off its payload, fy28/public/data/finance.json (build_finance.py, from the registry
# sources/data/fund-owners.csv), and every total the payload's own conclusions state is
# recomputed here from the per-fund rows, or nothing is written.
#
# THREE GRADES, KEPT APART (rule 13a, as finance.json keeps them). `evidence` is the Town
# Accountant's FY2026 special-revenue report at 31 March 2026, a MUNIS printout. `read` is the
# annual reports' special-revenue schedule, FY2011-FY2023, read off the page and tied to its
# printed totals. `transcribed` is OCR of the FY2024-FY2025 balance tables, which these pages
# do NOT draw: where it can be checked -- a FY2025 close against the FY2026 opening the ledger
# prints -- it fails for some funds, and that count is stated instead.

SC = 'school-committee'
HIST_YEARS = range(2011, 2024)       # the `read` grade: tied to the printed totals


def _fund_label(name):
    """A fund's MUNIS name as a chart row: its own words, without the fund-type suffix."""
    n = re.sub(r'\s+(REVOLVING FUND|REVOLVING|REVOLV|FUND)$', '', ' '.join(name.split()))
    return n[:1] + n[1:].lower() if not n[:1].isdigit() else n


def school_committee_fund_pages():
    FIN = load('finance.json')
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    src = {'payload': dict(label='Lunenburg Budget Project — finance.json (every school fund, '
                                 'read off the reports below)', href='/data/finance.json')}
    for name, what in (('school-special-revenue-fy26-q3.csv',
                        'the school funds in the Town Accountant’s FY2026 special-revenue report, '
                        '31 March 2026'),
                       ('fund-owners.csv', 'which board or department owns each fund'),
                       ('special-revenue-read.csv', 'the annual reports’ special-revenue '
                                                    'schedule, read and tied, FY2011–FY2023')):
        if not os.path.exists(os.path.join(DOCS_DATA, name)):
            fail('/docs/data/%s is not published' % name)
        src[name] = dict(label='Lunenburg Budget Project — %s (%s)' % (name, what),
                         href='/docs/data/' + name)
    for fy, key in ((2011, 'town-annual-reports/docs/4117-fy-2011-annual-town-report.pdf'),
                    (2023, 'town-annual-reports/docs/4131-fy-2023-annual-town-report.pdf')):
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        src['atr%d' % fy] = dict(label='Town of Lunenburg — annual town report, %s — %s'
                                       % (C.fy(fy), key.split('/')[-1]), href='/docs/' + key)
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    OF_ = lambda a, b, unit=None: figure(a, '%s of %s' % (C.num(a), C.num(b)), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    owner = FIN['owners'][SC]
    ms = [FIN['measures'][m] for m in owner['owns']]
    sr = [m for m in ms if m['kind'] == 'special-revenue']
    if any(m['current']['grade'] != 'evidence' or m['current'].get('as_of') != '2026-03-31'
           for m in sr):
        fail('a school special-revenue fund is no longer read off the 31 March 2026 report')
    cf = {c['id']: c['figures'] for c in FIN['conclusions_by_owner'][SC]}
    # The appropriation. ONE line, department 300, as the payload's own conclusion takes it.
    gf = FIN['measures']['gf-300']['current']
    approp = gf['revised']
    held = sum(m['current']['closing'] for m in sr)
    by = {}
    for m in sr:
        by.setdefault(m['subkind'], []).append(m)
    tot = {k: sum(m['current']['closing'] for m in v) for k, v in by.items()}
    for k, want in (('held', held), ('appropriation', approp), ('n', len(sr)),
                    ('share', 100 * held / approp)):
        if abs(cf['outside-the-appropriation'][k]['value'] - want) > 0.01:
            fail('finance.json’s %s no longer recomputes from its own fund rows' % k)
    if set(by) != {'revolving', 'grant', 'gift', 'other'} or any(v <= 0 for v in tot.values()):
        fail('the school funds are no longer four kinds, each holding a positive balance')
    tr = [m for m in ms if m['kind'] == 'trust']
    trust = sum(m['current']['closing'] for m in tr)
    if abs(trust - owner['totals']['trust_held']) > 0.01:
        fail('the school trusts no longer sum to the owner total')
    share = 100 * held / approp
    # "OTHER" IS A NAME-MATCH REMAINDER, NOT A KIND OF FUND (build_fund_owners.py files a fund
    # there when its name says neither revolving, grant, gift nor receipts). It was drawn as
    # "Other receipts funds", which reads as a fund type, while one fund, After School
    # Activities, held most of it. That fund is drawn by its own name; the rest is "other funds".
    asa = [m for m in by['other'] if m['name'].startswith('AFTER SCHOOL ACTIVITIES')]
    if len(asa) != 1:
        fail('the After School Activities Fund is no longer one of the school’s "other" funds')
    asa = asa[0]
    tot['asa'] = asa['current']['closing']
    rest_other = [m for m in by['other'] if m is not asa]
    tot['other'] = sum(m['current']['closing'] for m in rest_other)
    if not tot['asa'] > tot['other']:
        fail('After School Activities no longer holds most of the "other" funds; the page says so')
    KIND = (('revolving', 'Revolving funds'), ('grant', 'Grant funds, net of overdrafts'),
            ('asa', 'After School Activities Fund'), ('gift', 'Gift funds'),
            ('other', 'Other funds'))
    out['school-committee-funds'] = TP.page(
        'school-committee-funds',
        'The schools held %s in %s funds outside the appropriation at 31 March 2026.'
        % (C.usd(held), C.num(len(sr))),
        [f('held', U(held), 'held in school funds, 31 March 2026', 'published', allow=('31',
                                                                                    '2026')),
         f('n', N(len(sr), 'funds'), 'special-revenue funds with the schools’ code', 'published'),
         f('approp', U(approp), 'school appropriation, %s, revised' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('share', P(share), 'held, against the appropriation (our division)', 'published'),
         f('rev', U(tot['revolving']), 'in %s revolving funds' % C.num(len(by['revolving'])),
           'published', {'n': N(len(by['revolving']))}),
         f('grant', U(tot['grant']), 'in %s grant funds, net of overdrafts'
           % C.num(len(by['grant'])), 'published', {'n': N(len(by['grant']))}),
         f('gift', U(tot['gift']), 'in %s gift funds' % C.num(len(by['gift'])), 'published',
           {'n': N(len(by['gift']))}),
         f('asa', U(tot['asa']), 'in the After School Activities Fund', 'published'),
         f('other', U(tot['other']), 'in %s other funds' % C.num(len(rest_other)),
           'published', {'n': N(len(rest_other))}),
         f('trust', U(trust), 'in %s school trusts' % C.num(len(tr)), 'published',
           {'n': N(len(tr))}),
         f('close', None, 'what these funds held at the close of %s' % C.fy(2026), 'gap',
           {'y': F(2026)},
           closes='the Town Accountant’s special-revenue report for %s at period 13'
                  % C.fy(2026))],
        [con('%s sat in %s school funds at 31 March 2026: %s of the %s appropriation.'
             % (C.usd(held), C.num(len(sr)), C.pct(share), C.fy(2026)),
             ['held', 'n', 'approp', 'share'],
             {'a': U(held), 'n': N(len(sr)), 'p': P(share), 'y': F(2026)}, allow=('31', '2026'),
             notes=[step('What any balance is committed to is not printed: the report gives '
                         'balances, not obligations.', 'gap',
                         closes='the district’s fund-by-fund spending plan for %s' % C.fy(2026),
                         allow=(C.fy(2026),))]),
         con('Revolving funds held %s of it; the grant funds %s, net of the ones overdrawn.'
             % (C.usd(tot['revolving']), C.usd(tot['grant'])), ['rev', 'grant'],
             {'a': U(tot['revolving']), 'b': U(tot['grant'])}),
         con('After School Activities held %s; gift funds %s, other funds %s, trusts %s.'
             % (C.usd(tot['asa']), C.usd(tot['gift']), C.usd(tot['other']), C.usd(trust)),
             ['asa', 'gift', 'other', 'trust'],
             {'d': U(tot['asa']), 'a': U(tot['gift']), 'b': U(tot['other']), 'c': U(trust)}),
         con('The balances are nine months into %s; the year-end balances are not held.'
             % C.fy(2026), ['close'], {'y': F(2026)})],
        chart=TP.parts('School fund balances, by kind of fund',
                       [(lab, tot[k]) for k, lab in KIND], '$',
                       note='The Town Accountant’s special-revenue report, every fund carrying '
                            'the schools’ department code, at 31 March 2026.',
                       note_allow=('31', '2026')),
        sources=[src['school-special-revenue-fy26-q3.csv'], src['fund-owners.csv'],
                 src['payload']],
        finding_figures={'a': U(held), 'n': N(len(sr))}, finding_allow=('31', '2026'))

    # ---- the revolving funds, nine months of FY2026
    rv = sorted(by['revolving'], key=lambda m: m['code'])
    cur = {m['code']: m['current'] for m in rv}
    rin = sum(c['revenue'] for c in cur.values())
    rout = sum(c['spent'] for c in cur.values())
    rf = cf['the-revolving-funds']
    for k, want in (('in', rin), ('out', rout), ('held', tot['revolving']), ('n', len(rv))):
        if abs(rf[k]['value'] - want) > 0.01:
            fail('the revolving funds’ %s no longer recomputes' % k)
    for m in rv:
        c = m['current']
        if not c.get('foots') or abs(c['opening'] + c['revenue'] - c['spent'] - c['closing']) > 0.01:
            fail('revolving fund %s no longer foots: opening, in, out, closing' % m['code'])
    big_in = max(rv, key=lambda m: m['current']['revenue'])
    big_held = max(rv, key=lambda m: m['current']['closing'])
    paid = sorted([m for m in rv if m['current']['salaries'] > 0],
                  key=lambda m: -m['current']['salaries'])
    if (big_in['code'], big_held['code']) != ('2200', '1308') or \
            [m['code'] for m in paid] != ['1312', '2200', '1301']:
        fail('the largest revolving flow, the largest balance or the funds paying salaries moved; '
             'the prose names them')
    lab = {m['code']: _fund_label(m['name']) for m in rv}
    lab['1301'] = 'Chapter 658: athletics and activities'
    out['school-revolving-funds'] = TP.page(
        'school-revolving-funds',
        'The %s school revolving funds took in %s and paid out %s in nine months of %s.'
        % (C.num(len(rv)), C.usd(rin), C.usd(rout), C.fy(2026)),
        [f('in', U(rin), 'in, 1 July 2025 to 31 March 2026', 'published',
           allow=('1 July 2025', '31 March 2026')),
         f('out', U(rout), 'out, the same nine months', 'published'),
         f('held', U(tot['revolving']), 'held at 31 March 2026', 'published',
           allow=('31 March 2026',)),
         f('lunch', U(big_in['current']['revenue']), 'into school lunch', 'published'),
         f('choice', U(big_held['current']['closing']), 'held by school choice', 'published'),
         f('cin', U(big_held['current']['revenue']), 'into school choice', 'published'),
         f('paid', OF_(len(paid), len(rv), 'funds'), 'funds paying salaries directly', 'published'),
         f('s1312', U(paid[0]['current']['salaries']), 'salaries from extended day', 'published'),
         f('s2200', U(paid[1]['current']['salaries']), 'salaries from school lunch', 'published'),
         f('s1301', U(paid[2]['current']['salaries']), 'salaries from athletics and activities',
           'published')],
        [con('From July to March they took in %s and paid out %s; they held %s at the end.'
             % (C.usd(rin), C.usd(rout), C.usd(tot['revolving'])), ['in', 'out', 'held'],
             {'a': U(rin), 'b': U(rout), 'c': U(tot['revolving'])},
             notes=[step('What each fund bought is not in the report, which prints totals in '
                         'and out.', 'gap',
                         closes='the Town Accountant’s year-to-date expense report run for the '
                                'school revolving funds, %s' % C.fy(2026),
                         allow=(C.fy(2026),))]),
         con('School lunch was the largest flow, %s in; school choice held the most, %s.'
             % (C.usd(big_in['current']['revenue']), C.usd(big_held['current']['closing'])),
             ['lunch', 'choice', 'cin'],
             {'a': U(big_in['current']['revenue']), 'b': U(big_held['current']['closing'])}),
         con('%s paid salaries from the fund: extended day %s, lunch %s, athletics and '
             'activities %s.'
             % (OF_(len(paid), len(rv))['text'], C.usd(paid[0]['current']['salaries']),
                C.usd(paid[1]['current']['salaries']), C.usd(paid[2]['current']['salaries'])),
             ['paid', 's1312', 's2200', 's1301'],
             {'n': OF_(len(paid), len(rv)), 'a': U(paid[0]['current']['salaries']),
              'b': U(paid[1]['current']['salaries']), 'c': U(paid[2]['current']['salaries'])})],
        chart=TP.ranking('Money into each school revolving fund',
                         [(lab[c], cur[c]['revenue']) for c in cur], '$',
                         highlight=lab[big_in['code']],
                         note='1 July 2025 to 31 March 2026, as the Town Accountant’s '
                              'special-revenue report prints it.',
                         note_allow=('1 July 2025', '31 March 2026')),
        sources=[src['school-special-revenue-fy26-q3.csv'], src['fund-owners.csv'],
                 src['payload']],
        finding_figures={'n': N(len(rv)), 'a': U(rin), 'b': U(rout), 'y': F(2026)})

    # ---- the grant funds at 31 March 2026
    gr = by['grant']
    over = sorted([m for m in gr if m['current']['closing'] < 0],
                  key=lambda m: m['current']['closing'])
    deficit = -sum(m['current']['closing'] for m in over)
    gfz = cf['grants-in-deficit']
    for k, want in (('deficit', deficit), ('deficit_n', len(over)), ('grants_n', len(gr))):
        if abs(gfz[k]['value'] - want) > 0.01:
            fail('the grant funds’ %s no longer recomputes' % k)
    cb = next(m for m in gr if m['code'] == '2640')
    if abs(gfz['cb_held']['value'] - cb['current']['closing']) > 0.01 or \
            cb['current']['closing'] != max(m['current']['closing'] for m in gr):
        fail('the circuit breaker fund is no longer the largest grant balance')
    top = over[0]
    tiny = [m for m in over if -m['current']['closing'] < 1]
    glab = lambda m: ' '.join(m['name'].split())
    out['school-grant-balances'] = TP.page(
        'school-grant-balances',
        '%s of the %s school grant funds were overdrawn at 31 March 2026, by %s together.'
        % (C.num(len(over)), C.num(len(gr)), C.usd(deficit)),
        [f('over', OF_(len(over), len(gr), 'funds'), 'grant funds overdrawn, 31 March 2026',
           'published', allow=('31 March 2026',)),
         f('deficit', U(deficit), 'overdrawn, together', 'published'),
         f('top', U(-top['current']['closing']), 'the largest, %s' % glab(top), 'published',
           allow=(glab(top),)),
         f('net', U(tot['grant']), 'all grant funds, net', 'published'),
         f('cb', U(cb['current']['closing']), 'held by the circuit breaker fund', 'published'),
         f('cbin', U(cb['current']['revenue']), 'into it, July to March', 'published'),
         f('closed', None, 'whether each overdrawn grant was repaid', 'gap',
           closes='the Town Accountant’s special-revenue report for %s at period 13'
                  % C.fy(2026))],
        [con('%s grant funds were overdrawn by %s; the largest, %s, by %s.'
             % (OF_(len(over), len(gr))['text'], C.usd(deficit), glab(top),
                C.usd(-top['current']['closing'])), ['over', 'deficit', 'top'],
             {'n': OF_(len(over), len(gr)), 'a': U(deficit), 'b': U(-top['current']['closing'])},
             allow=(glab(top),),
             notes=[step('Many school grants pay out as reimbursements after the spending, so '
                         'an overdrawn fund may be waiting on one. Nothing here tests that.',
                         'hypothesis'),
                    step('Whether each was repaid, or any grant closed short, is not in a March '
                         'report.', 'gap',
                         closes='the Town Accountant’s special-revenue report for %s at period 13'
                                % C.fy(2026), allow=(C.fy(2026), 'period 13'))]),
         con('The circuit breaker fund held %s, after %s came in from July to March.'
             % (C.usd(cb['current']['closing']), C.usd(cb['current']['revenue'])),
             ['cb', 'cbin'], {'a': U(cb['current']['closing']), 'b': U(cb['current']['revenue'])}),
         con('Netted together, the %s grant funds held %s.' % (C.num(len(gr)), C.usd(tot['grant'])),
             ['net', 'cb', 'deficit'], {'n': N(len(gr)), 'a': U(tot['grant'])})],
        chart=TP.ranking('Overdrawn school grant funds',
                         [(glab(m), -m['current']['closing']) for m in over
                          if -m['current']['closing'] >= 1], '$', highlight=glab(top),
                         note='How far below zero each stood at 31 March 2026. %s more was '
                              'overdrawn by under a dollar.' % C.num(len(tiny)),
                         note_figures={'n': N(len(tiny))}, note_allow=('31', '2026')),
        sources=[src['school-special-revenue-fy26-q3.csv'], src['fund-owners.csv'],
                 src['payload']],
        finding_figures={'n': N(len(over)), 'm': N(len(gr)), 'a': U(deficit)},
        finding_allow=('31', '2026'))

    # ---- the revolving funds since FY2011
    hist = {}
    for m in rv:
        h = {x['fy']: x for x in m['history']}
        for y in HIST_YEARS:
            if y not in h or h[y]['grade'] != 'read':
                fail('revolving fund %s has no read, tied close for FY%d' % (m['code'], y))
            hist.setdefault(y, 0.0)
            hist[y] += h[y]['closing']
    open26 = sum(c['opening'] for c in cur.values())
    unchained = [m for m in rv if any(x['fy'] == 2025 and x['grade'] == 'transcribed'
                                      and x.get('chains') is False for x in m['history'])]
    ys = list(HIST_YEARS)
    y0, yl = ys[0], ys[-1]
    hi = max(ys, key=lambda y: hist[y])
    lo = min(ys, key=lambda y: hist[y])
    lunch = next(m for m in rv if m['code'] == '2200')
    lh = {x['fy']: x['closing'] for x in lunch['history'] if x['grade'] == 'read'}
    llo = min(ys, key=lambda y: lh[y])
    # The low is $730.50: whole dollars would round it to $730 (round half to even), a figure no
    # report prints. Cents where there are cents.
    U2 = lambda v: figure(v, C.usd(v) if round(v, 2) == int(v) else '$' + format(v, ',.2f'))
    x = [C.fy(y) for y in ys] + [C.fy(2024), C.fy(2025)]
    out['revolving-fund-history'] = TP.page(
        'revolving-fund-history',
        'The %s school revolving funds closed %s holding %s, against %s at the close of %s.'
        % (C.num(len(rv)), C.fy(yl), C.usd(hist[yl]), C.usd(hist[y0]), C.fy(y0)),
        [f('first', U(hist[y0]), 'held at the close of %s' % C.fy(y0), 'published',
           {'y': F(y0)}),
         f('last', U(hist[yl]), 'held at the close of %s' % C.fy(yl), 'published', {'y': F(yl)}),
         f('hi', U(hist[hi]), 'the highest close, %s' % C.fy(hi), 'published', {'y': F(hi)}),
         f('lo', U(hist[lo]), 'the lowest close, %s' % C.fy(lo), 'published', {'y': F(lo)}),
         f('open', U(open26), 'opening %s, the Town Accountant’s report' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('llo', U2(lh[llo]), 'school lunch at the close of %s' % C.fy(llo), 'published',
           {'y': F(llo)}),
         f('lopen', U(lunch['current']['opening']), 'school lunch, opening %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('chain', OF_(len(unchained), len(rv), 'funds'), '%s closes, by OCR, that miss the '
           'ledger' % C.fy(2025), 'published', {'y': F(2025)}),
         f('fy24', None, 'each fund’s close of %s, read and tied' % C.fy(2024), 'gap',
           {'y': F(2024)},
           closes='the Town Accountant’s special-revenue reports for %s and %s'
                  % (C.fy(2024), C.fy(2025)))],
        [con('They held %s at the close of %s and %s at the close of %s.'
             % (C.usd(hist[y0]), C.fy(y0), C.usd(hist[yl]), C.fy(yl)), ['first', 'last'],
             {'a': U(hist[y0]), 'y': F(y0), 'b': U(hist[yl]), 'z': F(yl)}),
         con('The highest close was %s, %s; the lowest %s, %s.'
             % (C.fy(hi), C.usd(hist[hi]), C.fy(lo), C.usd(hist[lo])), ['hi', 'lo'],
             {'y': F(hi), 'a': U(hist[hi]), 'z': F(lo), 'b': U(hist[lo])}),
         con('School lunch closed %s at %s and opened %s at %s.'
             % (C.fy(llo), U2(lh[llo])['text'], C.fy(2026), C.usd(lunch['current']['opening'])),
             ['llo', 'lopen'],
             {'y': F(llo), 'a': U2(lh[llo]), 'z': F(2026), 'b': U(lunch['current']['opening'])},
             notes=[step('Why the lunch balance moved is not in the schedule, which prints '
                         'receipts and payments, not meals or prices.', 'gap',
                         closes='the school food service’s annual financial report for each '
                                'year')]),
         con('%s and %s are read only by OCR, and %s %s closes miss the ledger’s opening.'
             % (C.fy(2024), C.fy(2025), OF_(len(unchained), len(rv))['text'], C.fy(2025)),
             ['fy24', 'chain', 'open'],
             {'y': F(2024), 'z': F(2025), 'n': OF_(len(unchained), len(rv))})],
        chart=TP.series('School revolving fund balances at each year end', x, [
            TP.track('Annual reports, read and tied', [hist[y] for y in ys] + [None, None],
                     'published', 'bar'),
            TP.track('Opening of %s, the ledger' % C.fy(2026), [None] * (len(ys) + 1) + [open26],
                     'published', 'bar')], '$', stacked=True,
            note='The %s revolving funds together. %s is left open: only an OCR reading of it is '
                 'held.' % (C.num(len(rv)), C.fy(2024)),
            note_figures={'n': N(len(rv)), 'y': F(2024)}),
        sources=[src['special-revenue-read.csv'], src['atr2011'], src['atr2023'],
                 src['school-special-revenue-fy26-q3.csv'], src['payload']],
        finding_figures={'n': N(len(rv)), 'y': F(yl), 'a': U(hist[yl]), 'b': U(hist[y0]),
                         'z': F(y0)})
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = []
        for p, text in outs.items():
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                stale.append(os.path.relpath(p, ROOT))
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('school spending topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
