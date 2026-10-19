#!/usr/bin/env python3
"""Spending, staff, students: five topic pages and the hub that sets the three side by side.

    python3 scripts/build_spending_staff_students_topics.py           # write the payloads
    python3 scripts/build_spending_staff_students_topics.py --check   # fail if any would change

WHY THIS EXISTS. Older residents, relayed by TJ on 18 October 2026: "They want to see as far
back as we have data to relate the budget and the spending to the FTE counts and the
enrollment count." Each of the three is already on the site on its own shelf; nothing set
them on one scale. This shelf does that and nothing else. It MEASURES. It does not confirm
or rebut anybody's reading of the measures (CLAUDE.md rules 7 and 8), and every page that
could be read as a cause carries the alternatives as hypotheses.

THE THREE SERIES, AND WHERE EACH STARTS -- each is drawn from the first year it is published:

  spending   DESE's NET SCHOOL SPENDING, FY1994-FY2026, from the Chapter 70 district
             profile (sources/data/dese-ch70-formula.csv). ACTUAL through FY2024 and
             BUDGETED for FY2025 and FY2026: the two stages are separate tracks and never
             one rate (rule 1). It is the state's measure, not the town's school line and
             not what the town pays: Chapter 70 aid is part of it (rule 11).
  pupils     DESE's 1 October headcount, FY1994-FY2026 (sources/data/dese-enrollment.csv).
  teachers   DESE's teacher FTE, FY2008-FY2026, read from the staffing payload that every
             teacher page reads (fy28/public/data/school-staffing.json).
  other staff  DESE's comparison sheet, FY2009-FY2025: paraprofessional and instructional
             support FTE beside teachers (sources/data/dese-radar.csv). No DESE file counts
             administrators, nurses, counsellors, clerical staff or custodians as FTE.

DOLLARS, TWO WAYS, ALWAYS SIDE BY SIDE. As printed, and in dollars of the latest ACTUAL year
(FY2024 when written; derived, never typed). The price index is the BLS CPI-U for
Boston-Cambridge-Newton, series CUURS11ASA0, landed 18 October 2026 in sources/federal-bls/
(see its PROVENANCE.md). THE CONVENTION: a FISCAL-YEAR average -- the six bimonthly values
July to May that BLS publishes for a Massachusetts fiscal year (FY2024 = July 2023 to May
2024) -- because the spending is by fiscal year. BLS publishes calendar averages only, so the
fiscal-year average and every real-dollar figure are OUR arithmetic, and every chart note
with dollars says which index, which average and which base year. A fiscal year without all
six values is refused, never averaged short.

JUDGEMENT CALLS, each named where it is used:
  * The index chart rebases each series to FY2008 = 100%, the first year all three exist.
    The base year is OURS; a page says what a different start reads.
  * Spending per child divides net school spending by the 1 October headcount -- OUR
    division, of two DESE figures that do not count exactly the same children. The
    foundation-enrolment division is given beside it so the choice is visible.
  * The town's own School Department line (sources/data/omnibus-history.csv, the Finance
    Committee's FY26 Budget Master) is NOT used: it is a workbook somebody assembled (rule
    13a), its expended column jumps between FY2006 and FY2007 by far more than net school
    spending does with no note saying why, and its other columns change kind year to year.
  * Whether the FY2011 teacher count is a real reduction or a reporting artefact is NOT
    settled; scripts/build_school_staffing_topics.py treats FY2011 the same way.

PAY OR HEADCOUNT, AND TEACHER PAY COMPARED (TJ, 19 October 2026: "did the increase cost from
more teachers, or higher pay per teacher?", and how Lunenburg's pay compares nearby):
  * The split of DESE's Teachers function into a teacher-count part and a per-teacher part
    uses MIDPOINT weights, OURS; it is run from every start year, because the start year
    sets the sign of the count part (the state's comparable count begins FY2013).
  * Spending per teacher FTE is our division; it is asserted against DESE's own Average
    Teacher Salary in every year DESE prints one, and the widest gap is printed.
  * The comparison uses the project's six districts, read from peer-spending.json, so this
    shelf and /school-spending/average-teacher-salary cannot disagree. An AVERAGE salary is
    not a salary SCHEDULE; the other districts' schedules are a registered gap.
  * What DESE counts as an "experienced" teacher is not defined in any document held.

The statewide teacher file takes about two minutes to read, so its extract is cached in the
gitignored build/cache/, keyed by the workbook's sha256 -- nothing is read from a cache that
does not match the bytes on disk.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
DOCS_DATA = os.path.join(ROOT, 'fy28', 'public', 'docs', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(DATA, 'archive-manifest.csv')
TEACHER_XLSX = os.path.join(ROOT, 'sources', 'state-dese', 'dese-teacher-data.xlsx')
CACHE = os.path.join(ROOT, 'build', 'cache')
CACHE_VERSION = 1
CPI_DIR = os.path.join(ROOT, 'sources', 'federal-bls')
CPI_SERIES = 'CUURS11ASA0'
CPI_MONTHS = (7, 9, 11, 1, 3, 5)   # the bimonthly releases inside one fiscal year, July to May
CID = 'school-spending-history'
LEA = '01620000'          # Lunenburg's DESE district code
STATE = '00000000'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == CID and gen == 'build_spending_staff_students_topics.py']

# The documents a gap would be closed by. Prose, no figures; said once.
EPIMS = ('Lunenburg’s EPIMS teacher assignments by school for the year in question, or the '
         'district’s own staffing list for it')
POSITIONS = ('the district’s position control report: each post with its FTE, funding source '
             'and whether it was filled')
NON_TEACHING = 'an FTE count by job class for every school employee, from EPIMS or the district'

FTE_UNIT = 'full-time equivalents'


def fail(msg):
    raise SystemExit('build_spending_staff_students_topics: ' + msg)


# ---------------------------------------------------------------------------- inputs

def nss_series():
    """{fy: row} for Lunenburg out of the Chapter 70 district profile extract."""
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-ch70-formula.csv'), encoding='utf-8')):
        if r['lea'] != LEA:
            continue
        if r['reconciles'] != 'yes':
            fail('Chapter 70 row FY%s no longer reconciles' % r['fy'])
        out[int(r['fy'])] = dict(
            nss=float(r['net_school_spending']) if r['net_school_spending'] else None,
            stage=r['nss_stage'] or None, aid=float(r['ch70_aid']),
            fe=int(r['foundation_enrollment']))
    return out


def enrolment():
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-enrollment.csv'), encoding='utf-8')):
        if r['lea'] == LEA and r['org_level'] == 'district' and r['total_cnt']:
            out[int(r['fy'])] = int(r['total_cnt'])
    return out


def cpi():
    """{fy: the fiscal-year average of the Boston-area CPI-U}, from the BLS responses as
    landed. A fiscal year is July to June; this area is published in odd months only, so a
    fiscal year is exactly six values or it is not computed."""
    m = {}
    keys = sorted(r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))
                  if r['key'].startswith('federal-bls/cpi-u-%s-' % CPI_SERIES))
    if not keys:
        fail('no %s responses in archive-manifest.csv' % CPI_SERIES)
    for k in keys:
        d = json.load(open(os.path.join(ROOT, 'sources', k), encoding='utf-8'))
        if d.get('status') != 'REQUEST_SUCCEEDED':
            fail('%s is not a successful BLS response' % k)
        s, = d['Results']['series']
        if s['seriesID'] != CPI_SERIES:
            fail('%s holds %s, not %s' % (k, s['seriesID'], CPI_SERIES))
        for x in s['data']:
            if not x['period'].startswith('M') or x['period'] == 'M13':
                continue
            km = (int(x['year']), int(x['period'][1:]))
            if km in m and m[km] != float(x['value']):
                fail('two responses disagree about %s' % (km,))
            m[km] = float(x['value'])
    out = {}
    for y in range(min(m)[0] + 1, max(m)[0] + 2):
        obs = [m.get((y - 1 if mo >= 7 else y, mo)) for mo in CPI_MONTHS]
        if all(v is not None for v in obs):
            out[y] = sum(obs) / len(obs)
    return out


def radar():
    out = collections.defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-radar.csv'), encoding='utf-8')):
        if r['lea'] == LEA:
            out[r['measure']][int(r['fy'])] = float(r['value'])
    return out


# DESE's function categories, in plain words. The codes are DESE's (the End of Year Financial
# Report's Schedule 3 groups); the names are ours, and the table beside the chart prints both.
FUNC_NAMES = {
    'TCHR': 'Teachers', 'BENE': 'Insurance, retirement, other',
    'TSER': 'Paras, therapists, substitutes', 'SERV': 'Pupil services',
    'TUIT': 'Out-of-district tuition', 'GUID': 'Guidance and testing',
    'OPMN': 'Buildings and upkeep', 'LDRS': 'Principals and curriculum leads',
    'ADMN': 'Central administration', 'MATL': 'Books, supplies, technology',
    'ODTR': 'Out-of-district transport', 'PDEV': 'Professional development',
}


# DESE's PUPIL SERVICES category holds buses, food, nurses and sports -- four unrelated things
# a reader will not accept as one (TJ, 19 October 2026: "are these really grouped together?!").
# Every chart and table here shows them apart, by DESE's own function codes, which must add
# back to the category every year.
SERV_SPLIT = [('SERV-3300', 'Buses', ['3300']), ('SERV-3400', 'Food service', ['3400']),
              ('SERV-3200', 'Nurses and health', ['3200']),
              ('SERV-3500', 'Sports and student activities', ['3510', '3520'])]


def types(y):
    """{key: (name, code label, $)} for one year of functions(): every DESE category, with
    pupil services split into its four parts."""
    out = {k: (FUNC_NAMES[k], k, v) for k, v in y['cat'].items() if k != 'SERV'}
    parts = 0.0
    for key, name, codes in SERV_SPLIT:
        v = sum(y['code'].get(c, 0.0) for c in codes)
        out[key] = (name, '/'.join(codes), v)
        parts += v
    if abs(parts - y['cat']['SERV']) > 12:
        fail('pupil services no longer equals buses, food, nurses and sports; a code is missing')
    return out


def functions():
    """{fy: {'total': $, 'cat': {code: $}, 'code': {func_code: $}}} for Lunenburg, from DESE's
    spending by function (all funds: general fund plus grants and revolving funds). The twelve
    categories (tuition derived, see below) must add to the `total` row DESE prints, every
    year, or nothing is built."""
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-function-expenditure.csv'), encoding='utf-8')):
        if r['lea'] != LEA:
            continue
        y = out.setdefault(int(r['fy']), {'total': None, 'cat': {}, 'code': {}})
        v = float(r['total'])
        if r['level'] == 'total':
            y['total'] = v
        elif r['level'] == 'category':
            y['cat'][r['func_cat_code']] = v
        elif r['level'] == 'detail':
            y['code'][r['func_code']] = v
        elif r['level'] == 'rollup':
            y.setdefault('roll', {})[r['func_cat_code']] = v
    if not out:
        fail('dese-function-expenditure.csv holds no rows for %s' % LEA)
    for fy, y in out.items():
        # DESE prints no category row for tuition. Its rollups do it instead: in-district
        # (IIII) is the ten in-district categories, and out-of-district (OODD) is tuition plus
        # out-of-district transport (ODTR). So tuition is OODD less ODTR, and IIII is checked.
        roll = y.get('roll', {})
        if set(roll) != {'IIII', 'OODD'} or 'ODTR' not in y['cat']:
            fail('FY%d: the in- and out-of-district rollups are not as expected' % fy)
        if abs(sum(v for k, v in y['cat'].items() if k != 'ODTR') - roll['IIII']) > 12:
            fail('FY%d: the in-district categories do not add to DESE\'s IIII rollup' % fy)
        y['cat']['TUIT'] = roll['OODD'] - y['cat']['ODTR']
        if set(y['cat']) - set(FUNC_NAMES):
            fail('FY%d has a function category with no plain name: %s'
                 % (fy, sorted(set(y['cat']) - set(FUNC_NAMES))))
        if y['total'] is None or abs(sum(y['cat'].values()) - y['total']) > 12:
            fail('FY%d: the function categories do not add to DESE\'s printed total' % fy)
    return out


def schools():
    """Teacher FTE by school and year, Lunenburg, from DESE's programme-area file."""
    out = collections.defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-teacher-program-area.csv'),
                                 encoding='utf-8')):
        if r['lea'] == LEA and r['total_fte']:
            out[r['org_name'] if r['org_level'] == 'school' else '_district'][int(r['fy'])] = \
                float(r['total_fte'])
    return out


def statewide_teachers():
    """{lea: {fy: All Teachers FTE}} for every district and the state, cached by sha256."""
    sha = hashlib.sha256(open(TEACHER_XLSX, 'rb').read()).hexdigest()
    cp = os.path.join(CACHE, 'dese-teacher-totals-%s.json' % sha[:16])
    if os.path.exists(cp):
        got = json.load(open(cp, encoding='utf-8'))
        if got.get('sha256') == sha and got.get('version') == CACHE_VERSION:
            return {k: {int(y): v for y, v in s.items()} for k, s in got['series'].items()}
    import openpyxl
    ws = openpyxl.load_workbook(TEACHER_XLSX, read_only=True)['Data']
    rows = ws.iter_rows(values_only=True)
    head = list(next(rows))
    ix = {k: head.index(k) for k in ('SY', 'DIST_CODE', 'ORG_CODE', 'SUBJECT', 'TCHR_CNT')}
    series = collections.defaultdict(dict)
    for r in rows:
        if len(r) <= ix['TCHR_CNT'] or r[ix['SUBJECT']] != 'All Teachers':
            continue
        if r[ix['ORG_CODE']] != r[ix['DIST_CODE']] or r[ix['TCHR_CNT']] is None:
            continue           # school rows; the district's own row is the one whose codes match
        series[r[ix['DIST_CODE']]][int(r[ix['SY']])] = float(r[ix['TCHR_CNT']])
    os.makedirs(CACHE, exist_ok=True)
    json.dump(dict(sha256=sha, version=CACHE_VERSION, series=series), open(cp, 'w', encoding='utf-8'))
    return dict(series)


def radar_all():
    """({lea: {measure: {fy: value}}}, {lea: name}) for every district on DESE's comparison
    sheet -- the comparison pages need the others, not only Lunenburg."""
    out, names = collections.defaultdict(lambda: collections.defaultdict(dict)), {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-radar.csv'), encoding='utf-8')):
        if r['reconciles'] != 'yes':
            # A row that fails the sheet's own check is LEFT OUT, never used; a page that
            # needs it then fails on the missing value rather than quoting it.
            continue
        out[r['lea']][r['measure']][int(r['fy'])] = float(r['value'])
        names[r['lea']] = r['district']
    return out, names


def experienced():
    """{lea: {fy: share}}: DESE's EXP_TCHR_PCT at the district's own all-teachers row, as
    extracted by scripts/extract_dese_staffing.py. WHAT DESE COUNTS AS "EXPERIENCED" IS NOT
    DEFINED in any document this archive holds -- the workbook has one sheet, Data, and no
    dictionary -- so every page that uses it says so and registers the gap."""
    out = collections.defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-teacher-subject.csv'), encoding='utf-8')):
        if (r['org_level'] == 'district' and r['subject_level'] == 'all'
                and r['experienced_pct']):
            out[r['lea']][int(r['fy'])] = float(r['experienced_pct'])
    return out


CONTRACT_TXT = os.path.join(ROOT, 'sources', 'contracts', 'txt', 'lea-teachers-2024-2027.txt')
SCHEDULE_CSV = os.path.join(ROOT, 'sources', 'contracts', 'data', 'lea-teacher-salary-schedule.csv')


def contract():
    """The teachers' agreement now in force: the first year's schedule adjustment, read off
    Appendix B's own heading, and that year's salary schedule from our table of it -- each
    cell of which must be printed in the contract text, or nothing is built (rule 13)."""
    import re
    text = open(CONTRACT_TXT, encoding='utf-8').read()
    m = re.search(r'FY ?(\d\d) Salary ([\d.]+)% COLA', text)
    if not m:
        fail('the contract text no longer prints a first-year schedule adjustment')
    fy0, cola = 2000 + int(m.group(1)), float(m.group(2))
    rows = list(csv.DictReader(open(SCHEDULE_CSV, encoding='utf-8')))
    col = 'fy%02d' % (fy0 - 2000)
    cells = [(int(r[col]), r['step'], r['lane']) for r in rows]
    flat = text.replace('\n', ' ')
    missing = [v for v, _, _ in cells if format(v, ',d') not in flat]
    if missing:
        fail('salary schedule cells not printed in the contract: %s' % missing[:5])
    return dict(fy=fy0, cola=cola, lo=min(cells), hi=max(cells))


# ---------------------------------------------------------------------------- pay scales
# TEACHER PAY COMPARED, BY SCHEDULE. sources/data/teacher-salary-schedules.csv is every cell of
# every comparison district's teachers' salary schedule, read off the contract by
# scripts/extract_teacher_salary_schedules.py. Lanes are named differently in every contract,
# so comparing them needs an ALIGNMENT, and this one is OURS -- each district's printed lane
# set against "bachelor's", "master's" and its highest lane:
#   * Montachusett's lane IV is printed "Masters or BS+45 / Licensure+45": a master's OR a
#     bachelor's plus 45 credits, so its master's lane is not master's alone.
#   * Fitchburg's highest lane is MA+60; it prints no doctorate lane.
#   * North Middlesex's BA+15 lane is closed since 1 July 2019 (its contract, Article 6,
#     pdf page 23); its BA lane is the one used, and its two BA lanes stop at step 10.
#   * "Highest lane" is the lane with the largest top step in that contract; asserted below.
# "Top" is the highest step printed in that lane. A district printing two schedules for one
# fiscal year (Harvard did, mid-year, in FY2020) would need a rule; none of the current ones
# does, and build() refuses rather than choose silently if one starts to.
SCHEDULES = os.path.join(DATA, 'teacher-salary-schedules.csv')
SCHED_DOCS = os.path.join(DATA, 'teacher-salary-schedule-docs.csv')
SHORT = {'Montachusett Regional Vocational Technical': 'Monty Tech'}
LANES = {   # district: (bachelor's, master's, highest), each as the contract prints it
    'Lunenburg': ('Bach', 'Masters', 'Doctorate'),
    'Harvard': ('B', 'M', 'PhD'),
    'North Middlesex': ('BA', 'MA', 'MA+75/Ph.D.'),
    'Fitchburg': ('BA', 'MA', 'MA+60'),
    'Montachusett Regional Vocational Technical': (
        'I: BS / Licensure', 'IV: Masters or BS+45 / Licensure+45', 'VIII: CAGS / Masters'),
}

# LONGEVITY IS PAID OUTSIDE EVERY GRID. Each rule as the contract prints it: the extracted
# text, the pdf page, and the amount by years of service completed. Every amount must be
# printed on that page of the text or nothing is built. `at(years)` is the yearly longevity a
# teacher with that many years would get -- OUR reading of each rule; the contracts count
# service differently (Lunenburg teaching service in the district, Fitchburg continuous
# service, Montachusett creditable service in the retirement system).
LONGEVITY_YEARS = 25
LONGEVITY = {
    'Lunenburg': dict(
        txt='contracts/txt/dese-teacher-contract.txt', page=28,
        printed=[1900, 3800, 5700], words=['4%'],
        tiers=[(15, 1900), (20, 3800), (25, 5700)],
        text='%s, %s, %s added to step 13 at 15, 20, 25 years; 4%% of base at 30',
        extra=None),
    'Harvard': dict(
        txt='contracts/txt/harvard-teachers-2023-2026.txt', page=None, printed=[], words=[],
        tiers=[], text='none found in the agreement', extra=None),
    'North Middlesex': dict(
        txt='contracts/txt/north-middlesex-teachers-2024-2027.txt', page=56,
        printed=[1350, 1600, 1850, 2150], words=[],
        tiers=[(15, 1350), (20, 1600), (25, 1850), (30, 2150)],
        text='%s, %s, %s, %s a year at 15, 20, 25, 30 years', extra=None),
    'Fitchburg': dict(
        txt='contracts/txt/fitchburg-teachers-2024-2027.txt', page=66,
        printed=[1000, 500, 100, 2000], words=['seven (7)'],
        # $1,000 from 7 years; from 15, $500 more, rising $100 a year to $2,000 at 30
        tiers=[(7, 1000)] + [(y, 1000 + min(500 + 100 * (y - 15), 2000)) for y in range(15, 31)],
        text='%s a year from 7 years; from 15, %s more, rising %s a year to %s', extra=None),
    'Montachusett Regional Vocational Technical': dict(
        txt='contracts/txt/dese-teacher-contract-montachusett.txt', page=10,
        printed=[750, 1000, 1250, 1500, 15000], words=['$5000'],
        tiers=[(15, 750), (20, 1000), (25, 1250), (30, 1500)],
        text='%s, %s, %s, %s a year at 15, 20, 25, 30 years; optional %s over three years',
        extra=15000),
}


def page_text(txt, page):
    """One pdf page of an extracted contract text, by its ===PAGE n=== marker."""
    import re
    t = open(os.path.join(ROOT, 'sources', txt), encoding='utf-8').read()
    parts = re.split(r'===PAGE (\d+)===', t)
    pages = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
    return pages if page is None else pages.get(page, '')


def longevity():
    """{district: {'at': {years: $}, 'text': as printed, 'page': n}}, each amount checked
    against the page of the contract it is said to be printed on."""
    out = {}
    for d, r in LONGEVITY.items():
        if r['page'] is None:
            # NONE FOUND is a statement about our search, so the search is the whole text,
            # every page, and the word is searched for, not a heading (rule 13c).
            pages = page_text(r['txt'], None)
            if any('longev' in p.lower() for p in pages.values()):
                fail('%s now prints a longevity rule; LONGEVITY says none' % d)
            r = dict(r, pages=len(pages))
        else:
            flat = ' '.join(page_text(r['txt'], r['page']).split())
            for a in r['printed']:
                if format(a, ',d') not in flat and str(a) not in flat:
                    fail('%s longevity: %s is not printed on pdf page %d of %s'
                         % (d, format(a, ',d'), r['page'], r['txt']))
            for w in r['words']:
                if w not in flat:
                    fail('%s longevity: %r is not on pdf page %d' % (d, w, r['page']))
        at = lambda y, t=r['tiers']: max([a for yy, a in t if yy <= y] or [0])
        out[d] = dict(at=at, page=r['page'], pages=r.get('pages'),
                      text=r['text'] % tuple(C.usd(a) for a in r['printed'][:r['text'].count('%s')])
                      if r['printed'] else r['text'])
    return out


def schedules():
    """({district: {fy: {lane: {step: $}}}}, {district: (schedule, doc)} for every fy), from
    our table of the contracts. Refuses a district/year printed under two schedules."""
    grid = collections.defaultdict(lambda: collections.defaultdict(
        lambda: collections.defaultdict(dict)))
    which = collections.defaultdict(set)
    for r in csv.DictReader(open(SCHEDULES, encoding='utf-8')):
        y = int(r['fy'])
        which[(r['district'], y)].add((r['schedule'], r['doc']))
        grid[r['district']][y][r['lane']][int(r['step'])] = float(r['salary'])
    return grid, which


def pay_distribution():
    """(PD, PB, TOPS) from teacher-pay-distribution.csv: per-year measures, histogram bands,
    and per-lane top-step counts. Counts and distributions only; no names (rule 13e)."""
    PD = collections.defaultdict(dict)
    PB = collections.defaultdict(list)
    TOPS = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'teacher-pay-distribution.csv'),
                                 encoding='utf-8')):
        y, m, v = int(r['fy']), r['measure'], r['value']
        if m == 'band':
            lo, hi = r['note'].split('-')
            PB[y].append((int(lo) if lo else None, int(hi) if hi else None, int(v)))
        elif m in ('top_step_calendar', 'at_or_above_top', 'above_top_plus_longevity'):
            TOPS.setdefault(r['note'], {})[m] = int(v)
        elif m not in ('matched_by_rule', 'list_heading'):
            PD[y][m] = float(v)
    return PD, PB, TOPS


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = {}
    dese = 'Massachusetts DESE'
    for k, (key, pub) in {
            'ch70': ('state-dese/dese-ch70-district-profile.xlsx', dese + ', Chapter 70 district profiles'),
            'enrol': ('state-dese/dese-enrollment-by-grade.xlsx', dese),
            'teachers': ('state-dese/dese-teacher-data.xlsx', dese),
            'program': ('state-dese/dese-teachers-by-program-area.xlsx', dese),
            'radar': ('state-dese/radar-district-comparison.xlsx', dese + ', district comparison'),
            'func': ('state-dese/district-expenditures-by-function.xlsx',
                     dese + ', district expenditures by function code'),
            'contract': ('contracts/pdf/dese-teacher-contract.pdf',
                         'Lunenburg Education Association agreement, 1 July 2024 to 30 June '
                         '2027, as filed with DESE'),
            'contract-txt': ('contracts/txt/lea-teachers-2024-2027.txt',
                             'the same agreement, the district’s copy, extracted text'),
    }.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key)
    for i, key in enumerate(sorted(k for k in man if k.startswith('federal-bls/cpi-u-'))):
        out['cpi%d' % i] = dict(label='US Bureau of Labor Statistics, CPI-U Boston-Cambridge-'
                                      'Newton — %s' % key.split('/')[-1], href='/docs/' + key)
    out['cpi-prov'] = dict(label='Lunenburg Budget Project — PROVENANCE.md (where the price '
                                 'index came from, and the fiscal-year average)',
                           href='/docs/federal-bls/PROVENANCE.md')
    if not os.path.exists(os.path.join(CPI_DIR, 'PROVENANCE.md')):
        fail('sources/federal-bls/PROVENANCE.md is missing')
    for k, (f, what) in {
            'ch70-csv': ('dese-ch70-formula.csv', 'net school spending and Chapter 70, by year'),
            'enrol-csv': ('dese-enrollment.csv', 'DESE’s 1 October headcount, by year'),
            'radar-csv': ('dese-radar.csv', 'DESE’s comparison sheet, by measure and year'),
            'program-csv': ('dese-teacher-program-area.csv', 'teacher FTE by school, by year'),
            'func-csv': ('dese-function-expenditure.csv', 'spending by function code, by year'),
    }.items():
        if not os.path.exists(os.path.join(DOCS_DATA, f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what), href='/docs/data/' + f)
    # Teacher experience by district, and our table of the salary schedule.
    for k, (f, what) in {
            'subject-csv': ('dese-teacher-subject.csv', 'teacher FTE and the share DESE counts '
                                                       'experienced, by district and year'),
    }.items():
        if not os.path.exists(os.path.join(DOCS_DATA, f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what), href='/docs/data/' + f)
    # The town's wage list, per report (TEACHERS ON THE SCALE). The pages are pdf pages,
    # every one opened; the list is the calendar year the report is named for.
    import extract_teacher_pay as XP
    for fy, (doc, pages) in XP.PAGES.items():
        key = 'town-annual-reports/docs/' + doc
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out['wages%d' % fy] = dict(
            label='Town of Lunenburg, annual town report %s — %s, “Gross Wages”, calendar %d, '
                  'pdf pages %d–%d' % (C.fy(fy), doc, fy, min(pages), max(pages)),
            href='/docs/' + key)
    for k, (f, what) in {
            'paydist-csv': ('teacher-pay-distribution.csv', 'teacher gross pay as counts and '
                            'distributions, by year; no names'),
            'roster-csv': ('staff-roster-entries.csv', 'the school rosters the reports print'),
    }.items():
        if not os.path.exists(os.path.join(DOCS_DATA, f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what), href='/docs/data/' + f)
    key = 'contracts/data/lea-teacher-salary-schedule.csv'
    if key not in man:
        fail('%s is not in archive-manifest.csv' % key)
    out['schedule-csv'] = dict(label='Lunenburg Budget Project — lea-teacher-salary-schedule.csv '
                                     '(the agreement’s salary schedules, step by lane)',
                               href='/docs/' + key)
    # Every comparison contract whose schedule was read, labelled as the contracts catalogue
    # labels it, keyed 'k:<doc>'; the pages pick the ones they use.
    labels = {r['local']: r['label'] for r in
              csv.DictReader(open(os.path.join(ROOT, 'sources', 'contracts', 'index.csv'),
                                  encoding='utf-8'))}
    for doc in sorted({r['doc'] for r in csv.DictReader(open(SCHEDULES, encoding='utf-8'))}):
        if doc not in man or 'sources/' + doc not in labels:
            fail('%s is not in archive-manifest.csv and the contracts catalogue' % doc)
        out['k:' + doc] = dict(label='%s — %s' % (labels['sources/' + doc], doc.split('/')[-1]),
                               href='/docs/' + doc)
    for k, (f, what) in {
            'schedules-csv': ('teacher-salary-schedules.csv', 'every cell of the comparison '
                              'districts’ salary schedules, with its page'),
            'schedule-docs-csv': ('teacher-salary-schedule-docs.csv', 'which contract each '
                                  'schedule came from, and what it covers'),
    }.items():
        if not os.path.exists(os.path.join(DOCS_DATA, f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what), href='/docs/data/' + f)
    return out


# ---------------------------------------------------------------------------- the pages

def build():
    src = sources()
    S = lambda *names: [src[n] for n in names]
    CPI_SRC = [src[k] for k in sorted(src) if k.startswith('cpi')]
    ch = nss_series()
    E = enrolment()
    R = radar()
    SC = schools()
    SS = json.load(open(os.path.join(PUB, 'school-staffing.json'), encoding='utf-8'))
    T = {r['fy']: r['fte'] for r in SS['composition']['district']}

    # The staffing payload and the files this script reads must describe the same counts.
    for y, v in T.items():
        if abs(SC['_district'].get(y, -1) - v) > 0.05:
            fail('teacher FTE for FY%d differs between the staffing payload and the programme '
                 'file (%s against %s)' % (y, v, SC['_district'].get(y)))
    for r in SS['composition']['district']:
        if E.get(r['fy']) != r['students']:
            fail('the 1 October headcount for FY%d differs between the staffing payload and '
                 'dese-enrollment.csv' % r['fy'])

    N_ = {y: r['nss'] for y, r in ch.items() if r['nss'] is not None}
    actual = sorted(y for y in N_ if ch[y]['stage'] == 'actual')
    budgeted = sorted(y for y in N_ if ch[y]['stage'] == 'budgeted')
    if not actual or not budgeted or actual[-1] >= budgeted[0]:
        fail('the actual and budgeted years of net school spending no longer split cleanly')
    if set(N_) != set(actual) | set(budgeted):
        fail('a net school spending year is neither actual nor budgeted')
    a0, a1 = actual[0], actual[-1]
    b1 = budgeted[-1]
    e0, e1 = min(E), max(E)
    t0, t1 = min(T), max(T)
    base = max(min(N_), e0, t0)               # the first year all three are published (ours)
    P = cpi()
    missing = [y for y in N_ if y not in P]
    if missing:
        fail('no full fiscal-year price average for FY%s' % missing)
    ref = a1                                  # dollars of the latest ACTUAL year
    RL = {y: N_[y] * P[ref] / P[y] for y in N_}
    DOLLARS = '%s dollars' % C.fy(ref)
    CPI_NOTE = ('%s: Boston-area CPI-U, July-June averages, our arithmetic.' % DOLLARS)
    cpi_fig = {'r': figure(ref, C.fy(ref), 'fiscal year')}

    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    U = lambda v: figure(v, C.usd(v))
    PC = lambda v, dp=1: figure(v, C.pct(v, dp))
    SP = lambda v: figure(v, '%+.1f%%' % v)
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    FTE = lambda v: figure(v, '%.1f' % v, FTE_UNIT)
    DF = lambda v: figure(v, '%.1f' % abs(v), FTE_UNIT)
    X = lambda v: figure(v, '%.2f' % v, 'times')
    f, con = LD.fact, TP.conclusion
    ORD = lambda n: '%d%s' % (n, 'th' if 10 <= n % 100 <= 20 else
                              {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))
    chg = lambda a, b: 100.0 * (b / a - 1)
    out = {}

    price_x = lambda a, b: P[b] / P[a]

    # ================================================================ growth side by side
    n_chg = chg(N_[base], N_[a1])
    r_chg = chg(RL[base], RL[a1])
    p_chg = chg(P[base], P[a1])
    e_chg = chg(E[base], E[a1])
    t_chg = chg(T[base], T[a1])
    nb_idx = 100.0 * N_[b1] / N_[base]
    e_last = chg(E[base], E[e1])
    t_last = chg(T[base], T[t1])
    # From the first year of the state's comparable teacher era, as the staffing pages use it.
    era = SS['composition']['eras']['total']
    t_era = chg(T[era], T[a1])
    e_era = chg(E[era], E[a1])
    years = list(range(base, max(b1, e1, t1) + 1))
    idx = lambda m, ys: [100.0 * m[y] / m[base] if y in m and y in ys else None for y in years]
    growth_chart = TP.series(
        'Spending, pupils and teachers, rebased', [C.fy(y) for y in years], [
            TP.track('Spending as printed, actual', idx(N_, actual), 'published', 'line'),
            TP.track('Spending, %s, actual' % DOLLARS, idx(RL, actual), 'published', 'line'),
            TP.track('Spending as printed, budgeted', idx(N_, budgeted), 'published', 'line'),
            TP.track('Pupils, 1 October', idx(E, E), 'published', 'line'),
            TP.track('Teacher FTE', idx(T, T), 'published', 'line')], '%',
        decimals=1, reference=(100, 'The %s level' % C.fy(base)),
        note='Each series over its own %s value. %s' % (C.fy(base), CPI_NOTE),
        note_figures=dict(cpi_fig, y=F(base)))
    out['growth-side-by-side'] = TP.page(
        'growth-side-by-side',
        '%s to %s: spending up %s after prices (%s as printed); pupils down %s, teacher FTE %s.'
        % (C.fy(base), C.fy(a1), C.pct(r_chg), C.pct(n_chg), C.pct(-e_chg), C.pct(-t_chg)),
        [f('r-chg', SP(r_chg), 'net school spending in %s, %s to %s' % (DOLLARS, C.fy(base), C.fy(a1)),
           'published', {'r': F(ref), 'a': F(base), 'b': F(a1)}),
         f('n-chg', SP(n_chg), 'net school spending as printed, the same years', 'published'),
         f('p-chg', SP(p_chg), 'Boston-area prices, the same years, July-June', 'published'),
         f('e-chg', SP(e_chg), 'pupils enrolled 1 October, the same years', 'published',
           allow=('1',)),
         f('t-chg', SP(t_chg), 'teacher FTE, the same years', 'published'),
         f('nb-idx', PC(nb_idx), 'budgeted %s spending, as a share of %s' % (C.fy(b1), C.fy(base)),
           'published', {'a': F(b1), 'b': F(base)}),
         f('e-last', SP(e_last), 'pupils, %s to %s' % (C.fy(base), C.fy(e1)), 'published',
           {'a': F(base), 'b': F(e1)}),
         f('t-last', SP(t_last), 'teacher FTE, %s to %s' % (C.fy(base), C.fy(t1)), 'published',
           {'a': F(base), 'b': F(t1)}),
         f('t-era', SP(t_era), 'teacher FTE, %s to %s' % (C.fy(era), C.fy(a1)), 'published',
           {'a': F(era), 'b': F(a1)}),
         f('e-era', SP(e_era), 'pupils, %s to %s' % (C.fy(era), C.fy(a1)), 'published',
           {'a': F(era), 'b': F(a1)})],
        [con('After prices spending rose %s over %s to %s, and pupils fell %s.'
             % (C.pct(r_chg), C.fy(base), C.fy(a1), C.pct(-e_chg)), ['r-chg', 'e-chg'],
             {'a': PC(r_chg), 'y': F(base), 'z': F(a1), 'b': PC(-e_chg)},
             notes=[step('As printed the rise is %s; Boston-area prices rose %s over the same '
                         'fiscal years.' % (C.pct(n_chg), C.pct(p_chg)), 'measured',
                         {'a': PC(n_chg), 'b': PC(p_chg)})]),
         con('Teacher FTE reads %s from %s and %s from %s; the start year sets the sign.'
             % ('%+.1f%%' % t_chg, C.fy(base), '%+.1f%%' % t_era, C.fy(era)), ['t-chg', 't-era', 'e-era'],
             {'a': SP(t_chg), 'y': F(base), 'b': SP(t_era), 'z': F(era)},
             notes=[step('%s is the first year of the state’s comparable teacher series; the '
                         'counts before it move by more than any staffing decision explains.'
                         % C.fy(era), 'gap', {'y': F(era)}, closes=EPIMS)]),
         con('Budgeted %s spending is %s of the %s level as printed, drawn as its own line.'
             % (C.fy(b1), C.pct(nb_idx), C.fy(base)), ['nb-idx'],
             {'y': F(b1), 'a': PC(nb_idx), 'b': F(base)}),
         con('The three moving apart does not show why they did.', ['r-chg', 't-chg', 'e-chg'],
             notes=[step('Salaries rising faster than prices, out-of-district placements, '
                         'mandates and staff who are not teachers all fit the same lines. '
                         'Nothing here separates them.', 'hypothesis')])],
        chart=growth_chart,
        table=dict(caption='Each series as a share of its %s value' % C.fy(base), views=[dict(
            key='index', label='Share of %s' % C.fy(base), total_col=-1, kinds=['ledger'] * 4,
            columns=['Spending as printed', 'Spending, %s' % DOLLARS, 'Pupils', 'Teacher FTE'],
            rows=[dict(label=C.fy(y) + (' (budgeted)' if y in budgeted else ''), cells=[
                C.pct(100.0 * N_[y] / N_[base]) if y in N_ else None,
                C.pct(100.0 * RL[y] / RL[base]) if y in RL else None,
                C.pct(100.0 * E[y] / E[base]) if y in E else None,
                C.pct(100.0 * T[y] / T[base]) if y in T else None]) for y in reversed(years)],
            note='Our arithmetic on DESE’s figures and the BLS price index, July-June averages. '
                 'A budgeted year is never set against an actual one.')]),
        sources=S('ch70', 'enrol', 'teachers', 'ch70-csv', 'enrol-csv') + CPI_SRC,
        finding_figures={'y': F(base), 'z': F(a1), 'r': PC(r_chg), 'a': PC(n_chg),
                         'b': PC(-e_chg), 'c': PC(-t_chg)})

    # ================================================================ long-run school spending
    mult = N_[a1] / N_[a0]
    rmult = RL[a1] / RL[a0]
    pmult = price_x(a0, a1)
    rsteps_up = sum(1 for y in actual[1:] if RL[y] > RL[y - 1])
    steps_up = sum(1 for y in actual[1:] if N_[y] > N_[y - 1])
    steps_n = len(actual) - 1
    if any(y - 1 not in N_ for y in actual[1:]):
        fail('the actual years of net school spending are no longer consecutive')
    aid0, aid1 = 100.0 * ch[a0]['aid'] / N_[a0], 100.0 * ch[a1]['aid'] / N_[a1]
    xs = list(range(a0, b1 + 1))
    out['long-run-school-spending'] = TP.page(
        'long-run-school-spending',
        'In %s net school spending went from %s in %s to %s in %s, %s times.'
        % (DOLLARS, C.usd(RL[a0]), C.fy(a0), C.usd(N_[a1]), C.fy(a1), '%.2f' % rmult),
        [f('r0', U(RL[a0]), 'net school spending, %s, in %s' % (C.fy(a0), DOLLARS), 'published',
           {'y': F(a0), 'r': F(ref)}),
         f('rmult', X(rmult), 'times the %s figure, %s, after prices' % (C.fy(a0), C.fy(a1)),
           'published', {'a': F(a0), 'b': F(a1)}),
         f('pmult', X(pmult), 'times the %s price level, %s, July-June' % (C.fy(a0), C.fy(a1)),
           'published', {'a': F(a0), 'b': F(a1)}),
         f('n0', U(N_[a0]), 'net school spending, %s, as printed' % C.fy(a0), 'published', {'y': F(a0)}),
         f('n1', U(N_[a1]), 'net school spending, %s, actual' % C.fy(a1), 'published', {'y': F(a1)}),
         f('mult', X(mult), 'times the %s figure, %s, as printed' % (C.fy(a0), C.fy(a1)),
           'published', {'a': F(a0), 'b': F(a1)}),
         f('nb', U(N_[b1]), 'net school spending, %s, budgeted' % C.fy(b1), 'published', {'y': F(b1)}),
         f('up', N(rsteps_up, 'years'), 'of %s year-to-year steps rose after prices'
           % C.num(steps_n), 'published', {'n': N(steps_n)}),
         f('aid0', PC(aid0), 'Chapter 70 aid as a share of it, %s' % C.fy(a0), 'published',
           {'y': F(a0)}, allow=('70',)),
         f('aid1', PC(aid1), 'Chapter 70 aid as a share of it, %s' % C.fy(a1), 'published',
           {'y': F(a1)}, allow=('70',))],
        [con('After prices, net school spending rose in %s of %s steps from %s to %s.'
             % (C.num(rsteps_up), C.num(steps_n), C.fy(a0), C.fy(a1)), ['up', 'r0', 'n1'],
             {'a': N(rsteps_up), 'n': N(steps_n), 'y': F(a0), 'z': F(a1)},
             notes=[step('As printed it rose in %s of them.' % C.num(steps_up), 'measured',
                         {'a': N(steps_up)})]),
         con('Chapter 70 aid was %s of it in %s and %s in %s; the rest came through the town.'
             % (C.pct(aid0), C.fy(a0), C.pct(aid1), C.fy(a1)), ['aid0', 'aid1'],
             {'a': PC(aid0), 'y': F(a0), 'b': PC(aid1), 'z': F(a1)}, allow=('70',),
             notes=[step('Net school spending is the state’s measure: it counts some costs the '
                         'town carries for the schools and leaves out transport and capital. It '
                         'is not the town’s school budget line.', 'measured')]),
         con('As printed spending is %s times %s; prices are %s times, so after prices %s.'
             % ('%.2f' % mult, C.fy(a0), '%.2f' % pmult, '%.2f' % rmult),
             ['mult', 'pmult', 'rmult'],
             {'a': X(mult), 'y': F(a0), 'b': X(pmult), 'c': X(rmult)}),
         con('%s and %s are budgets and are never set against the actual years.'
             % (C.fy(budgeted[0]), C.fy(b1)), ['nb'], {'a': F(budgeted[0]), 'b': F(b1)})],
        chart=TP.series('Net school spending by year', [C.fy(y) for y in xs], [
            TP.track('Actual, as printed', [N_[y] if y in actual else None for y in xs],
                     'published', 'bar'),
            TP.track('Budgeted, as printed', [N_[y] if y in budgeted else None for y in xs],
                     'published', 'bar'),
            TP.track('Actual, %s' % DOLLARS, [RL[y] if y in actual else None for y in xs],
                     'published', 'line'),
            TP.track('Budgeted, %s' % DOLLARS, [RL[y] if y in budgeted else None for y in xs],
                     'published', 'line')],
            '$', kind='bar', stacked=True,
            note='Bars as printed by DESE; lines in %s' % CPI_NOTE, note_figures=cpi_fig),
        table=dict(caption='Net school spending and Chapter 70 aid by year', views=[dict(
            key=key, label=label, total_col=-1, kinds=['ledger'] * 4,
            columns=['As printed', 'In %s' % DOLLARS, 'Chapter 70 aid', 'Aid share'],
            rows=[dict(label=C.fy(y) + (' (budgeted)' if y in budgeted else ''), cells=[
                C.usd(N_[y]), C.usd(RL[y]), C.usd(ch[y]['aid']),
                C.pct(100.0 * ch[y]['aid'] / N_[y])])
                for y in reversed(ys)],
            note='DESE’s figures; the share and the real dollars are ours (BLS Boston-area CPI-U, '
                 'July-June averages). The last two years are budgets.')
            for key, label, ys in (
                ('recent', '%s to %s' % (C.fy(a0 + 16), C.fy(b1)), xs[16:]),
                ('earlier', '%s to %s' % (C.fy(a0), C.fy(a0 + 15)), xs[:16]))]),
        sources=S('ch70', 'ch70-csv') + CPI_SRC,
        finding_figures={'r': F(ref), 'a': U(RL[a0]), 'y': F(a0), 'b': U(N_[a1]), 'z': F(a1),
                         'm': X(rmult)})

    # ================================================================ spending per child enrolled
    pp = {y: N_[y] / E[y] for y in N_ if y in E}
    pf1 = N_[a1] / ch[a1]['fe']
    pp_mult = pp[a1] / pp[a0]
    rpp = {y: RL[y] / E[y] for y in pp}
    rpp_mult = rpp[a1] / rpp[a0]
    e_long = chg(E[a0], E[a1])
    peak = max((y for y in E if y <= a1), key=lambda y: E[y])
    out['spending-per-child-enrolled'] = TP.page(
        'spending-per-child-enrolled',
        'In %s, spending per child went from %s in %s to %s in %s; pupils fell %s.'
        % (DOLLARS, C.usd(rpp[a0]), C.fy(a0), C.usd(pp[a1]), C.fy(a1), C.pct(-e_long)),
        [f('rpp0', U(rpp[a0]), 'per child, %s, in %s' % (C.fy(a0), DOLLARS), 'published',
           {'y': F(a0), 'r': F(ref)}),
         f('rppx', X(rpp_mult), 'times the %s figure, per child, after prices' % C.fy(a0),
           'published', {'y': F(a0)}),
         f('pp0', U(pp[a0]), 'per child enrolled, %s, as printed' % C.fy(a0), 'published',
           {'y': F(a0)}),
         f('pp1', U(pp[a1]), 'per child enrolled, %s (our division)' % C.fy(a1), 'published',
           {'y': F(a1)}),
         f('ppx', X(pp_mult), 'times the %s figure, per child, as printed' % C.fy(a0), 'published',
           {'y': F(a0)}),
         f('e0', N(E[a0], 'children'), 'enrolled 1 October, %s' % C.fy(a0), 'published',
           {'y': F(a0)}, allow=('1',)),
         f('e1', N(E[a1], 'children'), 'enrolled 1 October, %s' % C.fy(a1), 'published',
           {'y': F(a1)}, allow=('1',)),
         f('peak', N(E[peak], 'children'), 'enrolled, %s, the most in these years' % C.fy(peak),
           'published', {'y': F(peak)}),
         f('pf1', U(pf1), 'per foundation pupil, %s (our division)' % C.fy(a1), 'published',
           {'y': F(a1)}),
         f('fe1', N(ch[a1]['fe'], 'pupils'), 'the state’s foundation enrolment, %s' % C.fy(a1),
           'published', {'y': F(a1)})],
        [con('Per child, %s spending was %s times %s after prices; %s times as printed.'
             % (C.fy(a1), '%.2f' % rpp_mult, C.fy(a0), '%.2f' % pp_mult), ['rppx', 'ppx', 'e0', 'e1'],
             {'y': F(a1), 'a': X(rpp_mult), 'z': F(a0), 'b': X(pp_mult)}),
         con('Divided by the state’s foundation enrolment instead, %s reads %s a pupil.'
             % (C.fy(a1), C.usd(pf1)), ['pf1', 'fe1', 'pp1'], {'y': F(a1), 'a': U(pf1)}),
         con('Neither count is exactly the children the dollars pay for.', ['e1', 'fe1'],
             notes=[step('Tuition for children placed outside the district is in the spending '
                         'and not in the 1 October headcount; the foundation count adds '
                         'children schooled elsewhere whose costs are paid another way.',
                         'measured', allow=('1',))]),
         con('Enrolment peaked at %s children in %s; per child, %s was %s times that year after prices.'
             % (C.num(E[peak]), C.fy(peak), C.fy(a1), '%.2f' % (rpp[a1] / rpp[peak])),
             ['peak', 'pp1'], {'a': N(E[peak]), 'y': F(peak), 'z': F(a1),
                               'b': X(rpp[a1] / rpp[peak])})],
        chart=TP.series('Spending per child enrolled', [C.fy(y) for y in xs], [
            TP.track('Actual, as printed', [pp[y] if y in actual else None for y in xs],
                     'published', 'line'),
            TP.track('Budgeted, as printed', [pp[y] if y in budgeted else None for y in xs],
                     'published', 'line'),
            TP.track('Actual, %s' % DOLLARS, [rpp[y] if y in actual else None for y in xs],
                     'published', 'line'),
            TP.track('Budgeted, %s' % DOLLARS, [rpp[y] if y in budgeted else None for y in xs],
                     'published', 'line')], '$',
            note='Spending over the 1 October headcount, our division. %s' % CPI_NOTE,
            note_figures=cpi_fig, note_allow=('1',)),
        table=dict(caption='Spending, children and spending per child', views=[dict(
            key=key, label=label, total_col=-1, kinds=['ledger'] * 4,
            columns=['Net school spending', 'Enrolled', 'Per child, as printed',
                     'Per child, %s' % DOLLARS],
            rows=[dict(label=C.fy(y) + (' (budgeted)' if y in budgeted else ''), cells=[
                C.usd(N_[y]), C.num(E[y]), C.usd(pp[y]), C.usd(rpp[y])]) for y in reversed(ys)],
            note='DESE’s figures; per child and the real dollars are ours (BLS Boston-area CPI-U, '
                 'July-June averages). The last two years are budgets.')
            for key, label, ys in (
                ('recent', '%s to %s' % (C.fy(a0 + 16), C.fy(b1)), xs[16:]),
                ('earlier', '%s to %s' % (C.fy(a0), C.fy(a0 + 15)), xs[:16]))]),
        sources=S('ch70', 'enrol', 'ch70-csv', 'enrol-csv') + CPI_SRC,
        finding_figures={'r': F(ref), 'a': U(rpp[a0]), 'y': F(a0), 'b': U(pp[a1]), 'z': F(a1),
                         'c': PC(-e_long)})

    # ================================================================ teachers and other staff
    tr, pr, sr = R['Teacher FTE'], R['Paraprofessional FTE'], R['Instructional Support FTE']
    pup = R['In-District FTE Pupils']
    ry = sorted(set(tr) & set(pr) & set(sr) & set(pup))
    if ry != list(range(ry[0], ry[-1] + 1)):
        fail('the comparison sheet years are no longer consecutive')
    r0, r1 = ry[0], ry[-1]
    for y in ry:
        if y in T and abs(tr[y] - T[y]) > 0.15:
            fail('the comparison sheet and the teacher file now differ by more than they did '
                 'in FY%d' % y)
    oth = {y: pr[y] + sr[y] for y in ry}
    per = lambda m, y: 100.0 * m[y] / pup[y]
    R2 = lambda v: figure(v, '%.2f' % v, 'per hundred pupils')
    p_low = min(ry, key=lambda y: pr[y])
    out['teachers-and-other-staff'] = TP.page(
        'teachers-and-other-staff',
        'The state counted %s teacher FTE and %s paraprofessional and support FTE in %s.'
        % ('%.1f' % tr[r1], '%.1f' % oth[r1], C.fy(r1)),
        [f('t1', FTE(tr[r1]), 'teacher FTE, %s' % C.fy(r1), 'published', {'y': F(r1)}),
         f('t0', FTE(tr[r0]), 'teacher FTE, %s' % C.fy(r0), 'published', {'y': F(r0)}),
         f('o1', FTE(oth[r1]), 'paraprofessional and support FTE, %s' % C.fy(r1), 'published',
           {'y': F(r1)}),
         f('o0', FTE(oth[r0]), 'paraprofessional and support FTE, %s' % C.fy(r0), 'published',
           {'y': F(r0)}),
         f('tp1', R2(per(tr, r1)), 'teachers per hundred pupils, %s' % C.fy(r1), 'published',
           {'y': F(r1)}),
         f('tp0', R2(per(tr, r0)), 'teachers per hundred pupils, %s' % C.fy(r0), 'published',
           {'y': F(r0)}),
         f('op1', R2(per(oth, r1)), 'paraprofessional and support FTE per hundred pupils, %s' % C.fy(r1), 'published',
           {'y': F(r1)}),
         f('op0', R2(per(oth, r0)), 'paraprofessional and support FTE per hundred pupils, %s' % C.fy(r0), 'published',
           {'y': F(r0)}),
         f('pup', SP(chg(pup[r0], pup[r1])), 'in-district pupils, %s to %s' % (C.fy(r0), C.fy(r1)),
           'published', {'a': F(r0), 'b': F(r1)}),
         f('p-low', FTE(pr[p_low]), 'paraprofessional FTE, %s, the fewest' % C.fy(p_low),
           'published', {'y': F(p_low)}),
         f('non-teaching', None, 'administrators, nurses, counsellors, clerks, custodians',
           'gap', closes=NON_TEACHING),
         f('posts', None, 'which posts were filled, and which fund paid', 'gap', closes=POSITIONS)],
        [con('Teacher FTE went from %s in %s to %s in %s; paraprofessional and support from %s to %s.'
             % ('%.1f' % tr[r0], C.fy(r0), '%.1f' % tr[r1], C.fy(r1), '%.1f' % oth[r0],
                '%.1f' % oth[r1]), ['t0', 't1', 'o0', 'o1'],
             {'a': FTE(tr[r0]), 'y': F(r0), 'b': FTE(tr[r1]), 'z': F(r1), 'c': FTE(oth[r0]),
              'd': FTE(oth[r1])}),
         con('Per hundred pupils: teachers %s to %s; paraprofessionals and support %s to %s.'
             % ('%.2f' % per(tr, r0), '%.2f' % per(tr, r1), '%.2f' % per(oth, r0),
                '%.2f' % per(oth, r1)), ['tp0', 'tp1', 'op0', 'op1', 'pup'],
             {'a': R2(per(tr, r0)), 'b': R2(per(tr, r1)), 'c': R2(per(oth, r0)),
              'd': R2(per(oth, r1))}),
         con('The paraprofessional row fell to %s in %s before rising; why is not published.'
             % ('%.1f' % pr[p_low], C.fy(p_low)), ['p-low'], {'a': FTE(pr[p_low]), 'y': F(p_low)},
             notes=[step('A staffing change and a change in how posts were coded fit the same '
                         'series; the state’s two paraprofessional files also disagree in recent '
                         'years.', 'hypothesis')]),
         con('No state file counts the school’s other employees as FTE.', ['non-teaching', 'posts'])],
        chart=TP.series('Teachers and other staff by year', [C.fy(y) for y in ry], [
            TP.track('Teachers', [tr[y] for y in ry], 'published', 'bar'),
            TP.track('Paraprofessionals', [pr[y] for y in ry], 'published', 'bar'),
            TP.track('Instructional support', [sr[y] for y in ry], 'published', 'bar')], 'FTE',
            kind='bar', stacked=True, decimals=1,
            note='Three rows of DESE’s comparison sheet. An FTE counts assignments, not people '
                 'or filled posts.'),
        table=dict(caption='Staff FTE and pupils by year', views=[dict(
            key='years', label='FTE and pupils', total_col=-1, kinds=['ledger'] * 4,
            columns=['Teachers', 'Paraprofessionals', 'Instructional support', 'In-district pupils'],
            rows=[dict(label=C.fy(y), cells=['%.1f' % tr[y], '%.1f' % pr[y], '%.1f' % sr[y],
                                             '%.1f' % pup[y]]) for y in reversed(ry)],
            note='DESE’s comparison sheet, as printed. Pupils are DESE’s in-district FTE pupils.')]),
        sources=S('radar', 'radar-csv', 'teachers'),
        finding_figures={'a': FTE(tr[r1]), 'b': FTE(oth[r1]), 'y': F(r1)})

    # ================================================================ the FY2011 teacher reading
    Y = 2011       # the year under examination; named by the request, not derived
    if not (T[Y] < T[Y - 1] and T[Y] < T[Y + 1]):
        fail('FY2011 is no longer below both neighbours; this page no longer describes the file')
    st = statewide_teachers()
    if abs(st[LEA][Y] - T[Y]) > 0.05:
        fail('the statewide extract and the staffing payload disagree about FY2011')
    s_chg = chg(st[STATE][Y - 1], st[STATE][Y])
    s_other = [chg(st[STATE][y - 1], st[STATE][y]) for y in sorted(st[STATE])
               if y - 1 in st[STATE] and y != Y]
    if not s_chg < min(s_other):
        fail('the state total no longer falls more in FY2011 than in any other year')
    dch = {k: chg(s[Y - 1], s[Y]) for k, s in st.items()
           if k != STATE and s.get(Y - 1) and s.get(Y)}
    rank = sorted(dch, key=lambda k: dch[k]).index(LEA) + 1
    med = statistics.median(dch.values())
    sch = {k: v for k, v in SC.items() if k != '_district' and Y - 1 in v and Y in v}
    lower = [k for k, v in sch.items() if v[Y] < v[Y - 1]]
    back = [k for k in lower if SC[k].get(Y + 1, 0) > SC[k][Y]]
    biggest = max(sch, key=lambda k: sch[k][Y - 1] - sch[k][Y])
    sy = list(range(Y - 3, Y + 4))
    names = sorted(sch, key=lambda k: -sch[k][Y - 1])
    if len(names) > TP.TRACKS_MAX:
        fail('more schools than a chart holds')
    short = lambda k: k.replace('Thomas C ', '').replace(' Elementary', '').replace(' School', '')
    out['fy2011-teacher-reading'] = TP.page(
        'fy2011-teacher-reading',
        'The state’s file reads %s teacher FTE for %s: %s below %s and %s below %s.'
        % ('%.1f' % T[Y], C.fy(Y), '%.1f' % (T[Y - 1] - T[Y]), C.fy(Y - 1),
           '%.1f' % (T[Y + 1] - T[Y]), C.fy(Y + 1)),
        [f('y0', FTE(T[Y - 1]), 'teacher FTE, %s' % C.fy(Y - 1), 'published', {'y': F(Y - 1)}),
         f('y1', FTE(T[Y]), 'teacher FTE, %s' % C.fy(Y), 'published', {'y': F(Y)}),
         f('y2', FTE(T[Y + 1]), 'teacher FTE, %s' % C.fy(Y + 1), 'published', {'y': F(Y + 1)}),
         f('lower', N(len(lower), 'schools'), 'of %s schools read lower in %s than %s'
           % (C.num(len(sch)), C.fy(Y), C.fy(Y - 1)), 'published',
           {'n': N(len(sch)), 'y': F(Y), 'z': F(Y - 1)}),
         f('back', N(len(back), 'schools'), 'of those schools read higher again in %s' % C.fy(Y + 1),
           'published', {'y': F(Y + 1)}),
         f('big', DF(sch[biggest][Y - 1] - sch[biggest][Y]), 'FTE fewer at %s, the largest fall'
           % short(biggest), 'published'),
         f('state', SP(s_chg), 'the state’s teacher total, %s to %s' % (C.fy(Y - 1), C.fy(Y)),
           'published', {'a': F(Y - 1), 'b': F(Y)}),
         f('state-lo', SP(min(s_other)), 'the state’s total, its largest fall in other years',
           'published'),
         f('rank', figure(rank, ORD(rank), 'place'), 'of %s districts, by the size of the fall'
           % C.num(len(dch)), 'published', {'n': N(len(dch))}),
         f('median', SP(med), 'the median district’s change, %s to %s' % (C.fy(Y - 1), C.fy(Y)),
           'published', {'a': F(Y - 1), 'b': F(Y)}),
         f('cause', None, 'whether the %s figure is a cut or a reporting error' % C.fy(Y), 'gap',
           closes=EPIMS, label_figures={'y': F(Y)})],
        [con('%s of %s schools read lower in %s; %s of them read higher again in %s.'
             % (C.num(len(lower)), C.num(len(sch)), C.fy(Y), C.num(len(back)), C.fy(Y + 1)),
             ['lower', 'back', 'big'],
             {'a': N(len(lower)), 'n': N(len(sch)), 'y': F(Y), 'b': N(len(back)), 'z': F(Y + 1)}),
         con('The state’s total fell %s, more than in any other year; Lunenburg’s fell %s.'
             % (C.pct(-s_chg), C.pct(-dch[LEA])), ['state', 'state-lo', 'y0', 'y1'],
             {'a': PC(-s_chg), 'b': PC(-dch[LEA])},
             notes=[step('Cuts across the state that year fit the direction. Nothing published '
                         'here explains a fall many times the state’s, or the rise a year later.',
                         'hypothesis')]),
         con('Lunenburg’s fall was the %s largest of %s districts; the median moved %s.'
             % (ORD(rank), C.num(len(dch)), '%+.1f%%' % med), ['rank', 'median'],
             {'a': figure(rank, ORD(rank), 'place'), 'n': N(len(dch)), 'b': SP(med)}),
         con('The file cannot tell a cut restored a year later from a reporting error.',
             ['cause', 'y1'],
             notes=[step('Comparisons on this shelf start at %s, before it; one starting at %s '
                         'would read the rebound as growth.' % (C.fy(base), C.fy(Y)), 'measured',
                         {'a': F(base), 'b': F(Y)})])],
        chart=TP.series('Teacher FTE by school', [C.fy(y) for y in sy], [
            TP.track(short(k), [SC[k].get(y) for y in sy], 'published', 'line') for k in names],
            FTE_UNIT, decimals=1,
            note='DESE’s teacher FTE by programme area, school totals. A school that closed is a '
                 'gap, not a zero.'),
        table=dict(caption='Teacher FTE by school', views=[dict(
            key='schools', label='By school', total_col=len(names), kinds=['ledger'] * (len(names) + 1),
            columns=[short(k) for k in names] + ['District'],
            rows=[dict(label=C.fy(y), cells=[('%.1f' % SC[k][y]) if y in SC[k] else None
                                             for k in names] + ['%.1f' % SC['_district'][y]])
                  for y in reversed(sy)],
            note='DESE’s figures as printed. A blank is a year the school did not exist.')]),
        sources=S('teachers', 'program', 'program-csv'),
        finding_figures={'a': FTE(T[Y]), 'y': F(Y), 'b': FTE(T[Y - 1] - T[Y]), 'p': F(Y - 1),
                         'c': FTE(T[Y + 1] - T[Y]), 'q': F(Y + 1)})

    # ================================================================ growth by spending type
    # TJ, 19 October 2026: the side-by-side pages "should start with the reports that most
    # directly answer the question or show the data for this spending increase per type."
    # Ranked by CHANGE IN SHARE, not by dollars added: share x how far a line outgrew the
    # total is how this repo ranks lines (CLAUDE.md rule 4), and a share needs no deflator.
    FX = functions()
    g0, g1 = min(FX), max(FX)
    if g1 not in P:
        fail('no price average for FY%d, the last spending-by-function year' % g1)
    T0, T1 = types(FX[g0]), types(FX[g1])
    TN = {k: v[0] for k, v in T1.items()}
    TC = {k: v[1] for k, v in T1.items()}
    c0 = {k: v[2] for k, v in T0.items()}
    c1 = {k: v[2] for k, v in T1.items()}
    tt0, tt1 = FX[g0]['total'], FX[g1]['total']
    if set(c0) != set(c1):
        fail('the function categories differ between FY%d and FY%d' % (g0, g1))
    fg = {k: chg(c0[k], c1[k]) for k in c1}
    sh0 = {k: 100.0 * c0[k] / tt0 for k in c0}
    sh1 = {k: 100.0 * c1[k] / tt1 for k in c1}
    dsh = {k: sh1[k] - sh0[k] for k in c1}
    tg = chg(tt0, tt1)
    tgr = chg(tt0 * P[g1] / P[g0], tt1)
    ins0, ins1 = FX[g0]['code']['5200'], FX[g1]['code']['5200']
    # TJ, 19 October 2026: "is 'insurance and retirement grew 83%' ... of the entire budget,
    # or of itself?" So a GROWTH rate always travels with the dollars it ran between, and a
    # SHARE always names its whole -- "of all school spending". TJ asked for % rather than
    # points for the share change; the term for that quantity is percentage points, and the
    # note says what the bar measures.
    SPT = lambda v: figure(v, '%+.1f%%' % v, 'percent of all school spending')
    SH = lambda v: figure(v, C.pct(v, 1))
    fy01 = {'a': F(g0), 'b': F(g1)}
    big = max(c1, key=lambda k: c1[k] - c0[k])
    if big != 'TCHR':
        fail('teachers are no longer the largest dollar increase; the first conclusion says so')
    span = lambda k, name: f(k.lower(), SP(fg[k]), '%s: %s to %s' % (name, C.usd(c0[k]), C.usd(c1[k])),
                              'published', {'a': U(c0[k]), 'b': U(c1[k])})
    out['growth-by-spending-type'] = TP.page(
        'growth-by-spending-type',
        'Each against its own %s cost: insurance and retirement grew %s, paras %s, teachers %s,'
        ' all %s.' % (C.fy(g0), C.pct(fg['BENE'], 0), C.pct(fg['TSER'], 0),
                             C.pct(fg['TCHR'], 0), C.pct(tg, 0)),
        [f('tot', SP(tg), 'all school spending: %s to %s' % (C.usd(tt0), C.usd(tt1)), 'published',
           {'a': U(tt0), 'b': U(tt1)}),
         f('totr', SP(tgr), 'all school spending after prices, %s to %s' % (C.fy(g0), C.fy(g1)),
           'published', fy01),
         span('TCHR', 'teachers'),
         span('BENE', 'insurance and retirement'),
         f('ins', SP(chg(ins0, ins1)), 'active staff insurance: %s to %s' % (C.usd(ins0), C.usd(ins1)),
           'published', {'a': U(ins0), 'b': U(ins1)}),
         span('TSER', 'paras, therapists, substitutes'),
         span('GUID', 'guidance and testing'),
         span('PDEV', 'professional development'),
         f('tchr-sh', SPT(dsh['TCHR']), 'change in teachers’ share of all spending', 'published'),
         f('bene-sh', SPT(dsh['BENE']), 'change in insurance’s share of all spending', 'published'),
         f('posts', None, 'which posts were filled, and which fund paid', 'gap', closes=POSITIONS)],
        [con('Teachers added %s, the most of any type, yet grew %s; all spending grew %s.'
             % (C.usd(c1['TCHR'] - c0['TCHR']), C.pct(fg['TCHR'], 0), C.pct(tg, 0)),
             ['tchr', 'tot'],
             {'a': U(c1['TCHR'] - c0['TCHR']), 'b': PC(fg['TCHR'], 0), 'c': PC(tg, 0)}),
         con('Insurance and retirement grew %s, from %s a year to %s.'
             % (C.pct(fg['BENE'], 0), C.usd(c0['BENE']), C.usd(c1['BENE'])), ['bene', 'ins'],
             {'a': PC(fg['BENE'], 0), 'b': U(c0['BENE']), 'c': U(c1['BENE'])}),
         con('Paras, therapists and substitutes grew %s and guidance %s; training fell %s.'
             % (C.pct(fg['TSER'], 0), C.pct(fg['GUID'], 0), C.pct(-fg['PDEV'], 0)),
             ['tser', 'guid', 'pdev'],
             {'a': PC(fg['TSER'], 0), 'b': PC(fg['GUID'], 0), 'c': PC(-fg['PDEV'], 0)},
             notes=[step('More paraprofessional and support FTE in the state’s staffing counts '
                         'fits the direction; nothing here ties a dollar to a post.',
                         'hypothesis')]),
         con('Teachers fell from %s of all school spending to %s; insurance rose from %s to %s.'
             % (C.pct(sh0['TCHR'], 1), C.pct(sh1['TCHR'], 1), C.pct(sh0['BENE'], 1),
                C.pct(sh1['BENE'], 1)), ['tchr-sh', 'bene-sh', 'posts'],
             {'a': SH(sh0['TCHR']), 'b': SH(sh1['TCHR']), 'c': SH(sh0['BENE']),
              'd': SH(sh1['BENE'])},
             notes=[step('All funds: a line can rise because a grant moved onto it, not only '
                         'because the town spent more. DESE renumbered some codes over these '
                         'years, so compare categories, not single codes.', 'measured')])],
        chart=TP.ranking('Change in share of all school spending',
                         [(TN[k], dsh[k]) for k in c1], '%', decimals=1,
                         note='%s to %s, DESE, all funds. Insurance went from %s of all school '
                              'spending to %s: a bar of %s.'
                              % (C.fy(g0), C.fy(g1), C.pct(sh0['BENE'], 1), C.pct(sh1['BENE'], 1),
                                 C.pct(dsh['BENE'], 1)),
                         note_figures=dict(fy01, c=SH(sh0['BENE']), d=SH(sh1['BENE']),
                                           e=SH(dsh['BENE']))),
        table=dict(caption='School spending by type', views=[dict(
            key='types', label='By type', total_col=None, kinds=['ledger'] * 5,
            columns=[C.fy(g0), C.fy(g1), 'Growth on itself', 'Share %s' % C.fy(g0),
                     'Share %s' % C.fy(g1)],
            rows=[dict(label='%s (%s)' % (TN[k], TC[k]), cells=[
                C.usd(c0[k]), C.usd(c1[k]), '%+.0f%%' % fg[k], C.pct(sh0[k], 1), C.pct(sh1[k], 1)])
                  for k in sorted(c1, key=lambda k: -dsh[k])] + [dict(label='Total', cells=[
                C.usd(tt0), C.usd(tt1), '%+.0f%%' % tg, '100.0%', '100.0%'])],
            note='DESE’s figures as printed, general fund plus grants and revolving funds. '
                 'A share is of all school spending that year.')]),
        sources=S('func', 'func-csv', *[k for k in src if k.startswith('cpi')]),
        finding_figures={'y': F(g0), 'a': PC(fg['BENE'], 0), 'b': PC(fg['TSER'], 0),
                         'c': PC(fg['TCHR'], 0), 'd': PC(tg, 0)})

    # ================================================================ spending by type over time
    # TJ, 19 October 2026: "a stacked bar chart that shows the actual dollar amounts ... how
    # the spending line on the main page is composed over time." Five stacks, not twelve: the
    # palette has five colours, and twelve bands on one bar are a smear (rule 7f). The groups
    # are named for what is in them -- the fourth is every child schooled elsewhere, the fifth
    # says plainly it is the rest -- and the small multiples under the stack open them up.
    STACK = [('Teachers', ['TCHR']), ('Paras, therapists, substitutes', ['TSER']),
             ('Insurance and retirement', ['BENE']),
             ('Out-of-district tuition and transport', ['TUIT', 'ODTR']),
             ('All other in-district spending', ['SERV', 'OPMN', 'LDRS', 'ADMN', 'GUID', 'MATL', 'PDEV'])]
    if sorted(k for _, ks in STACK for k in ks) != sorted(FUNC_NAMES):
        fail('the five stacks do not hold every function category exactly once')
    gy = sorted(FX)
    band = {n: {y: sum(FX[y]['cat'][k] for k in ks) for y in gy} for n, ks in STACK}
    for y in gy:
        if abs(sum(band[n][y] for n, _ in STACK) - FX[y]['total']) > 12:
            fail('FY%d: the stacks do not add to DESE\'s total' % y)
    n0, n1 = STACK[2][0], STACK[0][0]
    # THE ODD YEAR. The stack shows one year where insurance falls by millions and teachers
    # rise by about as much, both reversing the next year. Found by drawing it (19 October
    # 2026); stated as a measurement, with its cause left open.
    odd = min(gy[1:-1], key=lambda y: FX[y]['cat']['BENE'] - FX[y - 1]['cat']['BENE'])
    dB = FX[odd]['cat']['BENE'] - FX[odd - 1]['cat']['BENE']
    dT = FX[odd]['cat']['TCHR'] - FX[odd - 1]['cat']['TCHR']
    if not (dB < -1e6 and dT > 1e6 and FX[odd + 1]['cat']['BENE'] > FX[odd]['cat']['BENE']
            and FX[odd + 1]['cat']['TCHR'] < FX[odd]['cat']['TCHR']):
        fail('the one-year swing between insurance and teachers is no longer in the data; '
             'the third conclusion says it is')
    add = {n: band[n][g1] - band[n][g0] for n, _ in STACK}
    out['spending-by-type-over-time'] = TP.page(
        'spending-by-type-over-time',
        'School spending, all funds, went from %s in %s to %s in %s.'
        % (C.usd(tt0), C.fy(g0), C.usd(tt1), C.fy(g1)),
        [f('t0', U(tt0), 'all school spending, %s' % C.fy(g0), 'published', {'y': F(g0)}),
         f('t1', U(tt1), 'all school spending, %s' % C.fy(g1), 'published', {'y': F(g1)}),
         f('a-t', U(add[n1]), 'more for teachers a year, %s to %s' % (C.fy(g0), C.fy(g1)),
           'published', fy01),
         f('a-b', U(add[n0]), 'more for insurance and retirement a year', 'published'),
         f('a-p', U(add[STACK[1][0]]), 'more for paras, therapists, substitutes a year', 'published'),
         f('a-s', U(add[STACK[3][0]]), 'more for out-of-district tuition and transport', 'published'),
         f('a-o', U(add[STACK[4][0]]), 'more for all other in-district spending', 'published'),
         f('odd-b', U(dB), 'insurance and retirement, %s against %s' % (C.fy(odd), C.fy(odd - 1)),
           'published', {'y': F(odd), 'p': F(odd - 1)}),
         f('odd-t', U(dT), 'teachers, %s against %s' % (C.fy(odd), C.fy(odd - 1)), 'published',
           {'y': F(odd), 'p': F(odd - 1)})],
        [con('Of the %s added a year, teachers took %s and insurance and retirement %s.'
             % (C.usd(tt1 - tt0), C.usd(add[n1]), C.usd(add[n0])), ['t0', 't1', 'a-t', 'a-b'],
             {'a': U(tt1 - tt0), 'b': U(add[n1]), 'c': U(add[n0])}),
         con('Paras, therapists and substitutes added %s a year; all other in-district %s.'
             % (C.usd(add[STACK[1][0]]), C.usd(add[STACK[4][0]])), ['a-p', 'a-o'],
             {'a': U(add[STACK[1][0]]), 'b': U(add[STACK[4][0]])},
             notes=[step('These are all funds, so the stack is not the net school spending line on '
                         'the hub: that is DESE’s narrower measure, and it adds town costs.',
                         'measured')]),
         con('In %s insurance and retirement fell %s and teachers rose %s; both reversed in %s.'
             % (C.fy(odd), C.usd(-dB), C.usd(dT), C.fy(odd + 1)), ['odd-b', 'odd-t'],
             {'y': F(odd), 'a': U(-dB), 'b': U(dT), 'z': F(odd + 1)},
             notes=[step('Money reported under a different code for one year fits this; so does '
                         'a real one-year change. Nothing here tells them apart; the district’s '
                         'End of Year report for that year would.', 'hypothesis')])],
        chart=TP.series('School spending by type, all funds', [C.fy(y) for y in gy], [
            TP.track(n, [band[n][y] for y in gy], 'published', 'bar') for n, _ in STACK], '$',
            kind='bar', stacked=True,
            note='DESE’s spending by function, as printed, general fund plus grants and revolving '
                 'funds. Each bar is one year’s total.'),
        # EVERY TYPE, one panel each on one scale -- how each ITSELF changed, which a stack
        # hides above its bottom band; largest dollar increase first (TJ, 19 October 2026).
        # Each panel takes the colour of the stack band it sits in, so the two charts read
        # together; pupil services is split into buses, food, nurses and sports.
        also=[TP.series('Each type on its own', [C.fy(y) for y in gy], [
            TP.track(TN[k], [types(FX[y])[k][2] for y in gy], 'published', 'line',
                     colour=next(j for j, (_, ks) in enumerate(STACK)
                                 if (k.split('-')[0]) in ks))
            for k in sorted(c1, key=lambda k: -(c1[k] - c0[k]))], '$',
            multiples=True,
            note='Every type, on one dollar scale: a steeper line is a bigger rise. A panel '
                 'takes the colour of its band in the stack above.')],
        table=dict(caption='School spending by type, by year', views=[dict(
            key='years', label='By year', total_col=len(STACK), kinds=['ledger'] * (len(STACK) + 1),
            columns=[n for n, _ in STACK] + ['Total'],
            rows=[dict(label=C.fy(y), cells=[C.usd(band[n][y]) for n, _ in STACK]
                       + [C.usd(FX[y]['total'])]) for y in reversed(gy)],
            note='DESE’s figures as printed. The groups are ours; the twelve categories are on '
                 'Growth by spending type.')]),
        sources=S('func', 'func-csv'),
        finding_figures={'a': U(tt0), 'y': F(g0), 'b': U(tt1), 'z': F(g1)})

    # ================================================================ pay or headcount
    # TJ, 19 October 2026: teacher spending rose while teacher FTE fell -- "did the increase
    # cost from more teachers, or higher pay per teacher?" A RATE-VOLUME SPLIT of DESE's
    # Teachers function (all funds) over DESE's teacher FTE, with MIDPOINT weights: the count
    # change priced at the average of the two years' spending per FTE, and the per-FTE change
    # weighted by the average of the two counts. The two parts add to the whole exactly; the
    # method is OURS and every page says so. Spending per FTE is our division, and it is
    # checked against DESE's own Average Teacher Salary in every year DESE prints one.
    TS = {y: FX[y]['cat']['TCHR'] for y in gy}
    if any(y not in T for y in gy):
        fail('a spending-by-function year has no teacher FTE')
    W = {y: TS[y] / T[y] for y in gy}
    WR = {y: W[y] * P[g1] / P[y] for y in gy}

    def split(a, b):
        v = (T[b] - T[a]) * (W[a] + W[b]) / 2
        r = (W[b] - W[a]) * (T[a] + T[b]) / 2
        if abs(v + r - (TS[b] - TS[a])) > 1:
            fail('the split FY%d-FY%d does not add back to the change' % (a, b))
        return v, r
    # The swing year (FY2024 when written) is not a start year: its teachers line is the one
    # that moved with insurance and back. Every other start year is used.
    if odd != g1 - 1:
        fail('the swing year is no longer the year before the last; the start years assume it')
    starts = [y for y in gy if y < odd]
    SPL = {y: split(y, g1) for y in starts}
    if not all(r > abs(v) for v, r in SPL.values()):
        fail('in some start year the teacher count now outweighs spending per teacher; the '
             'finding says it never does')
    v0, r0_ = SPL[g0]
    ve, re_ = SPL[era]
    if not (v0 < 0 < ve):
        fail('the count effect is no longer negative from FY%d and positive from FY%d; the '
             'first conclusion words it that way' % (g0, era))
    sal = radar()['Average Teacher Salary']
    ov = sorted(set(sal) & set(gy))
    gapd = max(abs(W[y] / sal[y] - 1) for y in ov)
    if gapd > 0.015:
        fail('spending per teacher FTE no longer matches DESE’s average salary within 1.5%%; '
             'worst %.2f%%' % (100 * gapd))
    EX = experienced()
    ex = EX[LEA]
    ey = sorted(y for y in ex if y in gy)
    KC = contract()
    if KC['fy'] != g1:
        fail('the contract’s first year is no longer the last spending year')
    SU = lambda v: figure(v, ('+' if v >= 0 else '-') + C.usd(abs(v)))
    w_chg, wr_chg = chg(W[g0], W[g1]), chg(WR[g0], WR[g1])
    dTS = chg(TS[g0], TS[g1])
    STEPS = ('the district’s count of teachers on each step and lane of the salary schedule, '
             'for each year')
    RAISES = ('the teachers’ agreements before the current one, from the district or as filed '
              'with DESE')
    EXP_DEF = 'DESE’s own definition of the experienced-teacher share in its teacher data file'
    out['pay-or-headcount'] = TP.page(
        'pay-or-headcount',
        'To %s from any start year %s–%s, more spent per teacher outweighed any change in the count.'
        % (C.fy(g1), C.fy(starts[0]), C.fy(starts[-1])),
        [f('per', SU(r0_), 'more per teacher FTE, %s to %s (our split)' % (C.fy(g0), C.fy(g1)),
           'published', fy01),
         f('cnt', SU(v0), 'from the change in teacher FTE, the same years', 'published'),
         f('per-e', SU(re_), 'more per teacher FTE, %s to %s' % (C.fy(era), C.fy(g1)),
           'published', {'a': F(era), 'b': F(g1)}),
         f('cnt-e', SU(ve), 'from the change in teacher FTE, the same years', 'published'),
         f('tchr', SP(dTS), 'Teachers spending: %s to %s' % (C.usd(TS[g0]), C.usd(TS[g1])),
           'published', {'a': U(TS[g0]), 'b': U(TS[g1])}),
         f('fte', FTE(T[g1]), 'teacher FTE, %s; %s in %s, %s in %s'
           % (C.fy(g1), '%.1f' % T[g0], C.fy(g0), '%.1f' % T[era], C.fy(era)), 'published',
           {'y': F(g1), 'a': FTE(T[g0]), 'p': F(g0), 'b': FTE(T[era]), 'q': F(era)}),
         f('w', SP(w_chg), 'per teacher FTE: %s to %s, %s to %s'
           % (C.usd(W[g0]), C.usd(W[g1]), C.fy(g0), C.fy(g1)), 'published',
           {'a': U(W[g0]), 'b': U(W[g1]), 'p': F(g0), 'q': F(g1)}),
         f('wr', SP(wr_chg), 'the same, after Boston-area prices', 'published'),
         f('dese', PC(100 * gapd, 1), 'widest gap to DESE’s average salary, %s to %s'
           % (C.fy(ov[0]), C.fy(ov[-1])), 'published', {'a': F(ov[0]), 'b': F(ov[-1])}),
         f('exp', PC(100 * ex[ey[-1]]), 'teachers DESE counts experienced, %s; %s in %s'
           % (C.fy(ey[-1]), C.pct(100 * ex[ey[0]]), C.fy(ey[0])), 'published',
           {'y': F(ey[-1]), 'a': PC(100 * ex[ey[0]]), 'p': F(ey[0])}),
         f('raise', PC(KC['cola']), 'salary schedule adjustment, %s, teachers’ agreement'
           % C.fy(KC['fy']), 'contract', {'y': F(KC['fy'])}),
         f('steps', None, 'teachers on each step and lane, each year', 'gap', closes=STEPS)],
        [con('From %s the teacher count took %s off; more spent per teacher added %s.'
             % (C.fy(g0), C.usd(-v0), C.usd(r0_)), ['cnt', 'per', 'tchr'],
             {'y': F(g0), 'a': U(-v0), 'b': U(r0_)},
             notes=[step('From %s, the first year of the state’s comparable count, the count '
                         'added %s and per teacher %s.' % (C.fy(era), C.usd(ve), C.usd(re_)),
                         'measured', {'y': F(era), 'a': U(ve), 'b': U(re_)}),
                    step('The split is ours, by midpoint weights; its two parts add to the '
                         'whole with nothing left over.', 'measured')]),
         con('Per teacher FTE went from %s to %s; after Boston-area prices that is %s.'
             % (C.usd(W[g0]), C.usd(W[g1]), '%+.1f%%' % wr_chg), ['w', 'wr', 'dese'],
             {'a': U(W[g0]), 'b': U(W[g1]), 'c': SP(wr_chg)},
             notes=[step('That division matches DESE’s own average teacher salary within %s in '
                         'every year DESE prints one, %s to %s.'
                         % (C.pct(100 * gapd), C.fy(ov[0]), C.fy(ov[-1])), 'measured',
                         {'g': PC(100 * gapd), 'a': F(ov[0]), 'b': F(ov[-1])}),
                    step('In %s the teachers line rose %s while insurance fell %s; both '
                         'reversed in %s, and DESE’s average carries the same swing.'
                         % (C.fy(odd), C.usd(dT), C.usd(-dB), C.fy(odd + 1)), 'measured',
                         {'y': F(odd), 'a': U(dT), 'b': U(-dB), 'z': F(odd + 1)})]),
         con('Neither shows whether raises, step increases or a change in who is on staff '
             'drove it.', ['steps', 'raise', 'fte'],
             notes=[step('A mix effect fits too: when the teachers who remain sit higher on the '
                         'schedule, the average rises though nobody’s pay changes.',
                         'hypothesis'),
                    step('The agreement set %s at %s; no earlier agreement is held, so earlier '
                         'raises are not known.' % (C.fy(KC['fy']), C.pct(KC['cola'])), 'gap',
                         {'y': F(KC['fy']), 'a': PC(KC['cola'])}, closes=RAISES)]),
         con('DESE counted %s of teachers experienced in %s, against %s in %s.'
             % (C.pct(100 * ex[ey[-1]]), C.fy(ey[-1]), C.pct(100 * ex[ey[0]]), C.fy(ey[0])),
             ['exp'], {'a': PC(100 * ex[ey[-1]]), 'y': F(ey[-1]), 'b': PC(100 * ex[ey[0]]),
                       'z': F(ey[0])},
             notes=[step('No document we hold defines experienced, and a share past a threshold '
                         'cannot see veterans moving up steps.', 'gap', closes=EXP_DEF)])],
        # THE SIGNATURE IS THE ONE SPLIT a reader came for, FY2009 to the latest year. It was
        # the every-start-year chart, whose x axis read as years though each bar is a SPAN to
        # the latest year -- so FY2009 looked like the year "more per teacher" was highest
        # (TJ, 19 October 2026: "what does 'more spent per teacher' mean when FY09 has the
        # highest number"). That chart is now the check underneath, labelled as start years.
        chart=TP.ranking('Where the rise in teachers spending came from',
                         [('From higher pay per teacher', r0_),
                          ('From the change in teacher count', v0)], '$',
                         note='%s to %s, our midpoint split of DESE’s figures; the two add to the '
                              'whole rise of %s.' % (C.fy(g0), C.fy(g1), C.usd(r0_ + v0)),
                         note_figures={'a': F(g0), 'b': F(g1), 'c': U(r0_ + v0)}),
        also=[TP.series('The same split from each starting year', [C.fy(y) for y in starts], [
                  # Pay first, so it takes the same colour as in the split above it.
                  TP.track('From higher pay per teacher', [SPL[y][1] for y in starts],
                           'published', 'bar'),
                  TP.track('From the change in teacher count', [SPL[y][0] for y in starts],
                           'published', 'bar')], '$', kind='bar',
                  note='Each pair runs from that starting year to %s, so longer spans add more. '
                       'Pay per teacher is larger in every one. %s is left out.'
                       % (C.fy(g1), C.fy(odd)),
                  note_figures={'a': F(g1), 'b': F(odd)}),
              TP.series('Spending per teacher FTE by year', [C.fy(y) for y in gy], [
                  TP.track('As printed, our division', [W[y] for y in gy], 'published', 'line'),
                  TP.track('In %s dollars' % C.fy(g1), [WR[y] for y in gy], 'published', 'line'),
                  TP.track('DESE’s average teacher salary', [sal.get(y) for y in gy],
                           'published', 'line')], '$',
                  note='Teachers spending over teacher FTE. %s dollars: Boston-area CPI-U, '
                       'July-June averages, our arithmetic.' % C.fy(g1),
                  note_figures={'a': F(g1)})],
        table=dict(caption='Teachers spending, teacher FTE and spending per FTE', views=[dict(
            key='years', label='By year', total_col=-1, kinds=['ledger'] * 4,
            columns=['Teachers spending', 'Teacher FTE', 'Per FTE, ours', 'DESE average salary'],
            rows=[dict(label=C.fy(y), cells=[C.usd(TS[y]), '%.1f' % T[y], C.usd(W[y]),
                                             C.usd(sal[y]) if y in sal else None])
                  for y in reversed(gy)],
            note='DESE’s figures as printed, all funds; the division is ours. DESE prints an '
                 'average salary only from %s.' % C.fy(min(sal)))]),
        sources=S('func', 'func-csv', 'teachers', 'radar', 'radar-csv', 'subject-csv',
                  'contract', 'contract-txt', 'schedule-csv') + CPI_SRC,
        finding_figures={'a': F(g1), 'b': F(starts[0]), 'c': F(starts[-1])})

    # ================================================================ teacher pay compared
    # The six districts are the project's own set, read from the payload the School spending
    # shelf builds from (peer-spending.json), so this page and /school-spending/average-
    # teacher-salary cannot name different districts or different ranks.
    RA, RN = radar_all()
    PS = json.load(open(os.path.join(PUB, 'peer-spending.json'), encoding='utf-8'))
    by_name = {v: k for k, v in RN.items()}
    six = [by_name[r['district']] for r in PS['teachers']]
    if len(six) != 6 or LEA not in six:
        fail('the six-district teacher rows no longer hold six districts and Lunenburg')
    SAL = {l: RA[l]['Average Teacher Salary'] for l in six}
    ly = PS['teachers_meta']['fy']
    if ly != max(SAL[LEA]):
        fail('the six-district payload’s year is not the latest DESE average salary')
    for r in PS['teachers']:
        if SAL[by_name[r['district']]][ly] != r['average_salary']:
            fail('peer-spending.json and dese-radar.csv disagree on %s' % r['district'])
    sy = sorted(set.intersection(*[set(SAL[l]) for l in six]))
    if sy != list(range(sy[0], sy[-1] + 1)):
        fail('the six districts’ salary years are no longer consecutive')
    place = lambda y: sorted(six, key=lambda l: -SAL[l][y]).index(LEA) + 1
    order = sorted(six, key=lambda l: -SAL[l][ly])
    nm = lambda l: {'Ayer Shirley School District': 'Ayer Shirley'}.get(RN[l], RN[l])
    # DESE's comparison sheet also lists a vocational school, charter schools and virtual
    # schools. Leaving them out of "districts" is OUR call, said on the page.
    allsal = [l for l in RA if ly in RA[l].get('Average Teacher Salary', {})]
    other = [l for l in allsal if any(w in RN[l] for w in ('Charter', 'Virtual', 'Vocational'))]
    trad = [l for l in allsal if l not in other]
    wplace = sorted(trad, key=lambda l: -RA[l]['Average Teacher Salary'][ly]).index(LEA) + 1
    EXS = {l: EX[l][ly] for l in six if ly in EX.get(l, {})}
    if set(EXS) != set(six):
        fail('the experienced share is missing for one of the six in FY%d' % ly)
    eplace = sorted(six, key=lambda l: -EXS[l]).index(LEA) + 1
    if odd not in sy:
        fail('the swing year is outside the salary years')
    Ord = lambda n: figure(n, ORD(n), 'place')
    OF = lambda a, b, unit=None: figure(a, '%s of %s' % (C.num(a), C.num(b)), unit)
    lyf = {'y': F(ly)}

    # ---- the salary SCHEDULES. The year compared is the latest one the most districts' held
    # contracts cover (ours): later years have fewer districts, and every year is in the table.
    LEA_NAME = RN[LEA]
    G, WHICH = schedules()
    cover = collections.defaultdict(set)
    for d, ys in G.items():
        for y in ys:
            cover[y].add(d)
    sfy = max(cover, key=lambda y: (len(cover[y]), y))
    held = sorted(cover[sfy])
    if LEA_NAME not in held:
        fail('Lunenburg has no schedule for FY%d' % sfy)
    if set(held) != set(LANES):
        fail('the districts with an FY%d schedule (%s) are not the ones LANES aligns'
             % (sfy, ', '.join(held)))
    stale = {d: max(G[d]) for d in G if max(G[d]) < sfy}      # read, but expired
    for y in (sfy - 1, sfy):
        for d in held:
            if len(WHICH[(d, y)]) != 1:
                fail('%s prints %d schedules for FY%d; choose one and say which on the page'
                     % (d, len(WHICH[(d, y)]), y))
    snm = lambda d: SHORT.get(d, d)

    def cells(y):
        out_ = {}
        for d in held:
            g = G[d][y]
            b, m, h = (g[l] for l in LANES[d])
            if any(not g[l] for l in LANES[d]):
                fail('%s FY%d: an aligned lane is not in the schedule' % (d, y))
            if max(g, key=lambda l: g[l][max(g[l])]) != LANES[d][2]:
                fail('%s FY%d: %s is not its highest-paid lane' % (d, y, LANES[d][2]))
            out_[d] = dict(ba1=b[1], batop=b[max(b)], ma1=m[1], matop=m[max(m)],
                           hitop=h[max(h)], bast=max(b), mast=max(m))
        return out_
    SC6, SC5 = cells(sfy), cells(sfy - 1)
    srank = lambda cs, k, d=LEA_NAME: sorted(held, key=lambda x: -cs[x][k]).index(d) + 1
    ns = len(held)
    RK = {k: srank(SC6, k) for k in ('ba1', 'batop', 'ma1', 'matop', 'hitop')}
    if not (RK['matop'] == RK['batop'] == RK['ba1'] == ns):
        fail('Lunenburg is no longer lowest on the bachelor’s start and both top steps; the '
             'finding and first conclusion say it is')
    if srank(SC5, 'ba1') != ns:
        fail('Lunenburg’s FY%d bachelor’s step 1 is no longer the lowest' % (sfy - 1))
    LG = longevity()
    LY = LONGEVITY_YEARS
    withl = {d: SC6[d]['matop'] + LG[d]['at'](LY) for d in held}
    lrank = sorted(held, key=lambda d: -withl[d]).index(LEA_NAME) + 1
    if max(held, key=lambda d: LG[d]['at'](LY)) != LEA_NAME:
        fail('Lunenburg’s longevity is no longer the largest at %d years' % LY)
    six_miss = [nm(l) for l in six if nm(l) not in held]
    if not six_miss or any(m not in stale for m in six_miss):
        fail('the six districts missing a current schedule are not all among those read')
    mx = max(held, key=lambda d: SC6[d]['matop'])
    stp = [SC6[d][k] for d in held for k in ('bast', 'mast')]
    monty = 'Montachusett Regional Vocational Technical'
    PD, _, TOPS = pay_distribution()

    def sched_view(cs, y, key):
        cols = ['Bachelor’s, step 1', 'Bachelor’s, top', 'Master’s, step 1', 'Master’s, top',
                'Highest lane, top', 'Steps, BA / MA']
        ks = ('ba1', 'batop', 'ma1', 'matop', 'hitop')
        rows = [dict(label=snm(d), cells=[C.usd(cs[d][k]) for k in ks]
                     + ['%d / %d' % (cs[d]['bast'], cs[d]['mast'])])
                for d in sorted(held, key=lambda d: -cs[d]['matop'])]
        rows.append(dict(label='Lunenburg’s place, highest first',
                         cells=['%s of %d' % (ORD(srank(cs, k)), ns) for k in ks] + [None]))
        return dict(key=key, label='Schedules, %s' % C.fy(y), total_col=-1,
                    kinds=['ledger'] * len(cols), columns=cols, rows=rows,
                    note='Each contract’s base salary schedule, lanes aligned by us (see Lanes '
                         'compared). Longevity and stipends are paid outside it.')
    pl = max(PD)
    nfull, mtop = int(PD[pl]['full_year']), TOPS['Masters']['at_or_above_top']
    CURRENT = ('each district’s current teachers’ agreement with its salary schedules, by '
               'records request')
    sy_ = {'y': F(sfy)}
    YRS = figure(LY, str(LY), 'years')
    out['teacher-pay-compared'] = TP.page(
        'teacher-pay-compared',
        'On the %s %s salary schedules held, Lunenburg’s top step was lowest in the bachelor’s '
        'and master’s lanes.' % (C.num(ns), C.fy(sfy)),
        [f('matop', U(SC6[LEA_NAME]['matop']), 'Lunenburg’s master’s top step, %s' % C.fy(sfy),
           'contract', sy_),
         f('marank', OF(RK['matop'], ns, 'districts'), 'its place on that step, highest first',
           'contract'),
         f('mahi', U(SC6[mx]['matop']), '%s’s, the highest of them' % snm(mx), 'contract'),
         f('batop', U(SC6[LEA_NAME]['batop']), 'Lunenburg’s bachelor’s top step, %s of %s'
           % (ORD(RK['batop']), C.num(ns)), 'contract',
           {'r': Ord(RK['batop']), 'n': N(ns, 'districts')}),
         f('ba1', U(SC6[LEA_NAME]['ba1']), 'its bachelor’s starting pay, %s of %s'
           % (ORD(RK['ba1']), C.num(ns)), 'contract',
           {'r': Ord(RK['ba1']), 'n': N(ns, 'districts')}),
         f('lng', U(withl[LEA_NAME]), 'its master’s top plus longevity at %d years, ours' % LY,
           'estimate', {'a': YRS}),
         f('lngr', OF(lrank, ns, 'districts'), 'its place, each contract’s longevity added',
           'estimate'),
         f('current', None, 'no current schedule held, %s districts read'
           % C.num(len(stale)), 'gap', {'n': N(len(stale), 'districts')}, closes=CURRENT),
         f('sal', U(SAL[LEA][ly]), 'Lunenburg’s average teacher salary, %s' % C.fy(ly),
           'published', lyf),
         f('rank', OF(place(ly), len(six), 'districts'), 'its place among the project’s six',
           'published'),
         f('wide', OF(wplace, len(trad), 'districts'), 'its place on all of DESE’s sheet, our cut',
           'published'),
         f('exp', PC(100 * EXS[LEA]), 'teachers DESE counts experienced, %s' % C.fy(ly),
           'published', lyf)],
        [con('Lunenburg’s master’s top was %s, against %s’s %s; its bachelor’s start was '
             'lowest too.' % (C.usd(SC6[LEA_NAME]['matop']), snm(mx), C.usd(SC6[mx]['matop'])),
             ['matop', 'marank', 'mahi', 'batop', 'ba1', 'current'],
             {'a': U(SC6[LEA_NAME]['matop']), 'b': U(SC6[mx]['matop'])},
             notes=[step('Its master’s start was %s and its highest lane’s top %s. Lanes are '
                         'aligned by us.' % (ORD(RK['ma1']), ORD(RK['hitop'])),
                         'measured', {'a': Ord(RK['ma1']), 'b': Ord(RK['hitop'])}),
                    step('The top step is step %s to step %s by contract, so it is not the same '
                         'years of service everywhere.' % (min(stp), max(stp)), 'measured',
                         {'a': N(min(stp), 'step'), 'b': N(max(stp), 'step')}),
                    step('%s districts read have no current contract held, %s of them in the '
                         'project’s six, which cannot be compared on scale.'
                         % (C.num(len(stale)), C.num(len(six_miss))), 'gap',
                         {'a': N(len(stale), 'districts'), 'b': N(len(six_miss), 'districts')},
                         closes=CURRENT)]),
         con('With each contract’s longevity at %d years, our arithmetic, its master’s top is '
             '%s, %s of %s.' % (LY, C.usd(withl[LEA_NAME]), ORD(lrank), C.num(ns)),
             ['lng', 'lngr'],
             {'y': YRS, 'a': U(withl[LEA_NAME]), 'r': Ord(lrank), 'n': N(ns, 'districts')},
             notes=[step('Longevity is paid outside every grid; at %d years Lunenburg’s, %s, is '
                         'the largest, and Harvard’s agreement prints none.'
                         % (LY, C.usd(LG[LEA_NAME]['at'](LY))), 'measured',
                         {'y': YRS, 'a': U(LG[LEA_NAME]['at'](LY))}),
                    step('Each contract counts service its own way; %s’s optional %s is left out. '
                         'Rules and pages are in the table.'
                         % (snm(monty), C.usd(LONGEVITY[monty]['extra'])), 'estimate',
                         {'a': U(LONGEVITY[monty]['extra'])})]),
         con('On DESE’s average teacher salary Lunenburg was %s of the project’s six in %s.'
             % (ORD(place(ly)), C.fy(ly)), ['sal', 'rank', 'wide'],
             {'r': Ord(place(ly)), 'y': F(ly)},
             notes=[step('A low scale fits a high average if the staff sits high on it: in calendar %d, '
                         '%s matched teachers were paid at least the master’s top, gross.'
                         % (pl, '%s of %s' % (C.num(mtop), C.num(nfull))), 'hypothesis',
                         {'y': figure(pl, str(pl), 'calendar year'),
                          'a': OF(mtop, nfull, 'teachers')},
                         cite=(REG.path('teachers-on-the-scale'), 'Teachers on the scale')),
                    step('The six are this project’s choice. Among the %s town districts on '
                         'DESE’s sheet it was %s.' % (C.num(len(trad)), ORD(wplace)), 'measured',
                         {'n': N(len(trad)), 'r': Ord(wplace)})]),
         con('DESE counted %s of Lunenburg’s teachers experienced in %s, %s of the six.'
             % (C.pct(100 * EXS[LEA]), C.fy(ly), ORD(eplace)), ['exp'],
             {'a': PC(100 * EXS[LEA]), 'y': F(ly), 'r': Ord(eplace)},
             notes=[step('No document we hold defines experienced, and a share past a threshold '
                         'cannot see veterans moving up steps.', 'gap', closes=EXP_DEF)])],
        chart=TP.ranking('Master’s lane top step by district',
                         [(snm(d), SC6[d]['matop']) for d in held], '$', highlight='Lunenburg',
                         basis='published',
                         note='Each contract’s %s salary schedule, master’s lane, highest step '
                              'printed. %s’s lane also takes a bachelor’s plus credits.'
                              % (C.fy(sfy), snm(monty)), note_figures=sy_),
        also=[TP.series('Starting and top pay by district', [snm(d) for d in
                        [LEA_NAME] + [d for d in held if d != LEA_NAME]], [
                  TP.track(name, [SC6[d][k] for d in [LEA_NAME] + [d for d in held
                                                                    if d != LEA_NAME]],
                           'published', 'bar')
                  for name, k in (('Bachelor’s, step 1', 'ba1'), ('Bachelor’s, top', 'batop'),
                                  ('Master’s, step 1', 'ma1'), ('Master’s, top', 'matop'))],
                  '$', kind='bar',
                  note='%s salary schedules, lanes aligned by us. Longevity, paid outside the '
                       'grid, is not in these.' % C.fy(sfy), note_figures=sy_,
                  note_allow=('1',)),
              TP.ranking('Average teacher salary, six districts',
                         [(nm(l), SAL[l][ly]) for l in six], '$', highlight='Lunenburg',
                         note='DESE’s comparison sheet, %s. The six are this project’s choice; '
                              'an average reflects who is employed, not only the scale.'
                              % C.fy(ly), note_figures=lyf)],
        table=dict(caption='Teacher pay: salary schedules and DESE’s average', views=[
            sched_view(SC6, sfy, 'schedule'), sched_view(SC5, sfy - 1, 'schedule-prev'),
            dict(key='lanes', label='Lanes compared', total_col=-1, kinds=['ledger'] * 3,
                 columns=['Bachelor’s', 'Master’s', 'Highest lane'],
                 rows=[dict(label=snm(d), cells=list(LANES[d])) for d in held],
                 note='Each lane as its contract prints it; the alignment is ours. North '
                      'Middlesex’s BA+15 lane is closed to new entrants.'),
            dict(key='longevity', label='Longevity', total_col=-1, kinds=['ledger'] * 4,
                 columns=['As the contract prints it', 'At %d years, ours' % LY,
                          'Master’s top plus that, ours', 'Contract page'],
                 rows=[dict(label=snm(d), cells=[
                     LG[d]['text'], C.usd(LG[d]['at'](LY)), C.usd(withl[d]),
                     ('pdf page %d' % LG[d]['page']) if LG[d]['page']
                     else 'all %d pages searched' % LG[d]['pages']])
                     for d in sorted(held, key=lambda d: -withl[d])],
                 note='Paid outside the salary grid. Each contract counts years of service its '
                      'own way; the reading at %d years is ours.' % LY),
            dict(key='missing', label='Not current', total_col=-1, kinds=['ledger'],
                 columns=['Latest schedule held'],
                 rows=[dict(label=d, cells=[C.fy(stale[d])]) for d in sorted(stale)],
                 note='Read from the latest contract each district filed with DESE; none covers '
                      '%s.' % C.fy(sfy)),
            dict(key='latest', label='Average, %s' % C.fy(ly), total_col=-1, kinds=['ledger'] * 3,
                 columns=['Average salary', 'Experienced', 'Teacher FTE'],
                 rows=[dict(label=nm(l), cells=[C.usd(SAL[l][ly]), C.pct(100 * EXS[l]),
                                                '%.1f' % RA[l]['Teacher FTE'][ly]])
                       for l in order],
                 note='DESE’s comparison sheet and teacher data, as printed.'),
            dict(key='years', label='Average by year', total_col=-1, kinds=['ledger'] * 4,
                 columns=['Lunenburg', 'Its place of six', 'Highest', 'Lowest'],
                 rows=[dict(label=C.fy(y), cells=[
                     C.usd(SAL[LEA][y]), ORD(place(y)), C.usd(max(SAL[l][y] for l in six)),
                     C.usd(min(SAL[l][y] for l in six))]) for y in reversed(sy)],
                 note='DESE’s comparison sheet. In %s DESE’s teachers line swung; that year the '
                      'average equals that line over teacher FTE.' % C.fy(odd)),
            dict(key='wide', label='All of DESE’s sheet', total_col=-1, kinds=['ledger'],
                 columns=['Average salary, %s' % C.fy(ly)],
                 rows=[dict(label=RN[l] + (' (left out)' if l in other else ''),
                            cells=[C.usd(RA[l]['Average Teacher Salary'][ly])])
                       for l in sorted(allsal, key=lambda l: -RA[l]['Average Teacher Salary'][ly])],
                 note='Every district DESE’s comparison sheet prints. Leaving out the vocational, '
                      'charter and virtual schools is ours.')]),
        sources=[src['k:' + doc] for doc in sorted({dc for d in held
                                                    for _, dc in WHICH[(d, sfy)]})]
        + S('schedules-csv', 'schedule-docs-csv', 'radar', 'radar-csv', 'teachers',
            'subject-csv', 'paydist-csv'),
        finding_figures={'n': N(ns, 'districts'), 'y': F(sfy)})


    # ================================================================ teachers on the scale
    # TJ, 19 October 2026: DESE's average puts Lunenburg second of six, residents say its
    # pay SCALE is the lowest; both are true if its teachers sit higher on the scale. Nobody
    # publishes the step-and-lane count. The town's own annual reports print every town and
    # school employee's calendar-year gross pay by name, and the school rosters by name and
    # post; scripts/extract_teacher_pay.py joins the two PRIVATELY (rule 13e) and publishes
    # only counts and distributions, which is all this page reads.
    import extract_teacher_pay as XP
    PD, PB, TOPS = pay_distribution()
    py = sorted(PD)
    pl = py[-1]
    if 'top_step_calendar' not in TOPS.get('Masters', {}) or 'Bach' not in TOPS:
        fail('the teacher pay distribution carries no calendar top steps for the bachelor’s '
             'and master’s lanes')
    L = PD[pl]
    nfull, nmatch, nrost = int(L['full_year']), int(L['matched']), int(L['roster_teachers'])
    ma, ba = TOPS['Masters'], TOPS['Bach']
    hi_lane = max(TOPS, key=lambda l: TOPS[l]['top_step_calendar'])
    rates = {y: PD[y]['match_rate'] for y in py}
    rlo, rhi = min(rates.values()), max(rates.values())
    if sum(c for _, _, c in PB[pl]) != nfull:
        fail('the %d histogram bands do not add to the full-year count' % pl)
    if not (L['p25'] >= ba['top_step_calendar']) == (ba['at_or_above_top'] >= 0.75 * nfull):
        fail('the quartile and the bachelor’s-top count no longer tell the same story')
    CY = lambda y: figure(y, str(y), 'calendar year')
    OFN = lambda a, b, unit='teachers': figure(a, '%s of %s' % (C.num(a), C.num(b)), unit)
    k = lambda v: '$%dk' % (v // 1000)
    kk = lambda v: '%d' % (v // 1000)
    xs, vals = [], []
    s1 = int(L['step1_bach_calendar'])
    for lo, hi, c in PB[pl]:
        lab = ('Under %s' % k(hi)) if lo is None else ('%s and over' % k(lo)) if hi is None \
            else '$%s–%sk' % (kk(lo), kk(hi))
        marks = []
        if (lo is None or s1 >= lo) and (hi is None or s1 < hi):
            marks.append('step 1')
        tops = [nm_ for nm_, t in (('BA top', ba), ('MA top', ma))
                if (lo is None or t['top_step_calendar'] >= lo) and
                (hi is None or t['top_step_calendar'] < hi)]
        marks += tops
        xs.append(lab + (' (%s)' % ', '.join(marks) if marks else ''))
        vals.append(c)
    WAGES_GAP = STEPS
    OTHER_TOWNS = ('the same gross wage lists from the towns of the five other districts, '
                   'read and matched the same way')
    plf = {'y': CY(pl)}
    out['teachers-on-the-scale'] = TP.page(
        'teachers-on-the-scale',
        'In calendar %d, %s teachers we matched were paid at least the master’s top step.'
        % (pl, '%s of %s' % (C.num(ma['at_or_above_top']), C.num(nfull))),
        [f('med', U(L['median']), 'median gross pay, matched teachers, calendar %d' % pl,
           'published', plf),
         f('ba', OFN(ba['at_or_above_top'], nfull), 'paid at least the bachelor’s top step',
           'estimate'),
         f('ma', OFN(ma['at_or_above_top'], nfull), 'paid at least the master’s top step',
           'estimate'),
         f('far', OFN(ma['above_top_plus_longevity'], nfull),
           'past the master’s top plus the largest longevity', 'estimate'),
         f('matop', U(ma['top_step_calendar']), 'master’s top step, calendar %d, our blend' % pl,
           'estimate', plf),
         f('batop', U(ba['top_step_calendar']), 'bachelor’s top step, the same blend', 'estimate'),
         f('s1', U(s1), 'step 1, bachelor’s lane, the same blend', 'estimate', allow=('1',)),
         f('match', OFN(nmatch, nrost), 'roster teachers matched to the wage list, %d' % pl,
           'published', plf),
         f('part', N(int(L['part_year']), 'teachers'), 'left out as part-year, our rule',
           'published'),
         f('m0', U(PD[py[0]]['median']), 'median gross pay, calendar %d' % py[0], 'published',
           {'y': CY(py[0])}),
         f('steps', None, 'teachers on each step and lane, each year', 'gap', closes=WAGES_GAP),
         f('others', None, 'the same distribution in the other five districts', 'gap',
           closes=OTHER_TOWNS)],
        [con('%s of %s matched teachers were paid at least the bachelor’s top step; %s the '
             'master’s.' % (C.num(ba['at_or_above_top']), C.num(nfull),
                            C.num(ma['at_or_above_top'])), ['ba', 'ma', 'matop', 'batop'],
             {'a': N(ba['at_or_above_top'], 'teachers'), 'b': N(nfull, 'teachers'),
              'c': N(ma['at_or_above_top'], 'teachers')},
             notes=[step('Gross pay counts stipends, coaching, summer work and longevity; it is '
                         'not the cell anybody sits on.', 'measured'),
                    step('The list is a calendar year, so each top step is our blend: half the '
                         '%s cell, half the %s.' % (C.fy(pl), C.fy(pl + 1)), 'estimate',
                         {'a': F(pl), 'b': F(pl + 1)})]),
         con('The median of matched teachers went from %s in %d to %s in %d, gross.'
             % (C.usd(PD[py[0]]['median']), py[0], C.usd(L['median']), pl),
             ['m0', 'med', 'match'],
             {'a': U(PD[py[0]]['median']), 'y': CY(py[0]), 'b': U(L['median']), 'z': CY(pl)},
             notes=[step('Matched means one wage row for a roster name: %s to %s of roster '
                         'teachers each year, never all.' % (C.pct(rlo, 0), C.pct(rhi, 0)),
                         'measured', {'a': PC(rlo, 0), 'b': PC(rhi, 0)}),
                    step('Teachers paid under half the year’s median are left out as part-year; '
                         'that line is ours.', 'measured')]),
         con('It does not show how many teachers sit on each step or lane.', ['steps', 'far'],
             notes=[step('A staff high on the scale fits: on the schedule alone, pay past the '
                         'master’s top needs a higher lane.', 'hypothesis'),
                    step('Stipends and extra duties fit too; %s were paid past that top plus '
                         'the largest longevity.' % C.num(ma['above_top_plus_longevity']),
                         'hypothesis', {'a': N(ma['above_top_plus_longevity'], 'teachers')}),
                    step('The district’s own count would settle it.', 'gap',
                         closes=WAGES_GAP)]),
         con('Whether the other districts’ teachers sit as high is not measured here.',
             ['others'],
             notes=[step('Their towns’ wage lists have not been read; a survey of which publish '
                         'one is in the project notes.', 'gap', closes=OTHER_TOWNS)])],
        chart=TP.series('Teacher gross pay, calendar year', xs, [
            TP.track('Matched teachers', vals, 'published', 'bar')], 'teachers', kind='bar',
            note='Full-year matched teachers. Step 1 %s, BA top %s, MA top %s, bachelor’s and '
                 'master’s lanes: our calendar blend.' % (C.usd(s1), C.usd(ba['top_step_calendar']),
                                          C.usd(ma['top_step_calendar'])),
            note_figures={'a': U(s1), 'b': U(ba['top_step_calendar']),
                          'c': U(ma['top_step_calendar'])}, note_allow=('1',)),
        also=[TP.series('Teacher gross pay by year', [str(y) for y in py], [
                  TP.track('Upper quartile', [PD[y]['p75'] for y in py], 'published', 'line'),
                  TP.track('Median', [PD[y]['median'] for y in py], 'published', 'line'),
                  TP.track('Lower quartile', [PD[y]['p25'] for y in py], 'published', 'line')],
                  '$', note='Full-year matched teachers, gross, each calendar year. The match '
                            'rate differs by year; see the table.')],
        table=dict(caption='Teachers matched, and their gross pay', views=[
            dict(key='years', label='By year', total_col=-1, kinds=['ledger'] * 6,
                 columns=['Roster teachers', 'Matched', 'Part-year', 'Lower quartile', 'Median',
                          'Upper quartile'],
                 rows=[dict(label=str(y), cells=[
                     C.num(int(PD[y]['roster_teachers'])), C.num(int(PD[y]['matched'])),
                     C.num(int(PD[y]['part_year'])), C.usd(PD[y]['p25']),
                     C.usd(PD[y]['median']), C.usd(PD[y]['p75'])]) for y in reversed(py)],
                 note='Calendar years, as the town prints the list. Gross pay, not salary; '
                      'counts and quartiles only.'),
            dict(key='lanes', label='Top step by lane, %d' % pl, total_col=-1,
                 kinds=['ledger'] * 3,
                 columns=['Top step, our blend', 'At or above', 'Past it plus longevity'],
                 rows=[dict(label=l, cells=[C.usd(TOPS[l]['top_step_calendar']),
                                            C.num(TOPS[l]['at_or_above_top']),
                                            C.num(TOPS[l]['above_top_plus_longevity'])])
                       for l in sorted(TOPS, key=lambda l: TOPS[l]['top_step_calendar'])],
                 note='Of %d full-year matched teachers. Longevity: up to %s on the top step, '
                      'Article XVI.' % (nfull, C.usd(XP.LONGEVITY_MAX)))]),
        sources=[src['wages%d' % y] for y in sorted(py, reverse=True)][:15]
        + S('paydist-csv', 'roster-csv', 'contract', 'schedule-csv'),
        finding_figures={'y': CY(pl), 'a': OFN(ma['at_or_above_top'], nfull)})

    # ================================================================ the hub
    tiers = [
        LD.tier('%s to %s' % (C.fy(base), C.fy(a1)), [
            f('h-r', SP(r_chg), 'net school spending, in %s' % DOLLARS, 'published',
              {'r': F(ref)}),
            f('h-n', SP(n_chg), 'net school spending, as printed', 'published'),
            f('h-e', SP(e_chg), 'pupils enrolled 1 October', 'published', allow=('1',)),
            f('h-t', SP(t_chg), 'teacher FTE', 'published')]),
        LD.tier('As far back as each goes', [
            f('h-mult', X(rmult), 'times the %s net school spending, %s, after prices'
              % (C.fy(a0), C.fy(a1)), 'published', {'a': F(a0), 'b': F(a1)}),
            f('h-pp', U(pp[a1]), 'per child enrolled, %s (ours)' % C.fy(a1), 'published',
              {'y': F(a1)}),
            f('h-rpp', U(rpp[a0]), 'per child, %s, in %s (ours)' % (C.fy(a0), DOLLARS),
              'published', {'y': F(a0), 'r': F(ref)}),
            f('h-el', SP(e_long), 'pupils, %s to %s' % (C.fy(a0), C.fy(a1)), 'published',
              {'a': F(a0), 'b': F(a1)}),
            f('h-o', FTE(oth[r1] - oth[r0]), 'more paraprofessional and support FTE, %s to %s'
              % (C.fy(r0), C.fy(r1)), 'published', {'a': F(r0), 'b': F(r1)}),
            # The gaps sit with the long run: a ladder holds three tiers, and type of spending
            # is the third (TJ, 19 October 2026: "these are really important").
            f('h-2011', None, 'what the %s teacher count measured' % C.fy(Y), 'gap', closes=EPIMS,
              label_figures={'y': F(Y)}),
            f('h-posts', None, 'which posts were filled, and which fund paid', 'gap',
              closes=POSITIONS)]),
        LD.tier('By type of spending, %s to %s' % (C.fy(g0), C.fy(g1)), [
            f('h-bene', SP(fg['BENE']), 'insurance and retirement: %s to %s'
              % (C.usd(c0['BENE']), C.usd(c1['BENE'])), 'published',
              {'a': U(c0['BENE']), 'b': U(c1['BENE'])}),
            f('h-tser', SP(fg['TSER']), 'paras, therapists, substitutes: %s to %s'
              % (C.usd(c0['TSER']), C.usd(c1['TSER'])), 'published',
              {'a': U(c0['TSER']), 'b': U(c1['TSER'])}),
            f('h-tchr', SP(fg['TCHR']), 'teachers: %s to %s' % (C.usd(c0['TCHR']), C.usd(c1['TCHR'])),
              'published', {'a': U(c0['TCHR']), 'b': U(c1['TCHR'])}),
            f('h-tot', SP(tg), 'all school spending: %s to %s' % (C.usd(tt0), C.usd(tt1)),
              'published', {'a': U(tt0), 'b': U(tt1)})]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('From %s to %s spending rose %s after prices while pupils fell %s.'
                      % (C.fy(base), C.fy(a1), C.pct(r_chg), C.pct(-e_chg)), ['h-r', 'h-n', 'h-e'],
                      {'y': F(base), 'z': F(a1), 'a': PC(r_chg), 'b': PC(-e_chg)}),
        LD.conclusion('Teacher FTE read %s lower over those years; from %s it reads %s higher.'
                      % (C.pct(-t_chg), C.fy(era), C.pct(t_era)), ['h-t', 'h-2011'],
                      {'a': PC(-t_chg), 'y': F(era), 'b': PC(t_era)}),
        LD.conclusion('Paraprofessional and support FTE rose by %s from %s to %s.'
                      % ('%.1f' % (oth[r1] - oth[r0]), C.fy(r0), C.fy(r1)), ['h-o'],
                      {'a': FTE(oth[r1] - oth[r0]), 'y': F(r0), 'z': F(r1)}),
        LD.conclusion('Over %s to %s spending is %s times larger after prices; pupils %s fewer.'
                      % (C.fy(a0), C.fy(a1), '%.2f' % rmult, C.pct(-e_long)), ['h-mult', 'h-el'],
                      {'y': F(a0), 'z': F(a1), 'a': X(rmult), 'b': PC(-e_long)}),
        LD.conclusion('Since %s, each on its own cost: insurance grew %s, paras %s, '
                      'teachers %s.' % (C.fy(g0), C.pct(fg['BENE'], 0), C.pct(fg['TSER'], 0),
                                        C.pct(fg['TCHR'], 0)),
                      ['h-bene', 'h-tser', 'h-tchr', 'h-tot'],
                      {'y': F(g0), 'a': PC(fg['BENE'], 0), 'b': PC(fg['TSER'], 0),
                       'c': PC(fg['TCHR'], 0)}),
        LD.conclusion('Per child enrolled it went from %s to %s, both in %s.'
                      % (C.usd(rpp[a0]), C.usd(pp[a1]), DOLLARS), ['h-rpp', 'h-pp'],
                      {'a': U(rpp[a0]), 'b': U(pp[a1]), 'r': F(ref)}),
    ])
    out[CID] = TP.hub(
        CID,
        'From %s to %s net school spending rose %s after prices (%s as printed), while pupils '
        'fell %s and teacher FTE %s. None of it says why.'
        % (C.fy(base), C.fy(a1), C.pct(r_chg), C.pct(n_chg), C.pct(-e_chg), C.pct(-t_chg)),
        hub_ladder, chart=growth_chart,
        answer_figures={'y': F(base), 'z': F(a1), 'r': PC(r_chg), 'a': PC(n_chg),
                        'b': PC(-e_chg), 'c': PC(-t_chg)})

    if sorted(k for k in out if k != CID) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
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
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else None) != text]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('spending, staff, students topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
