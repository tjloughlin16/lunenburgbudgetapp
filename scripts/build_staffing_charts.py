#!/usr/bin/env python3
"""The school-staffing page's series, pre-rendered from the database.

    python3 scripts/build_staffing_charts.py            # write it
    python3 scripts/build_staffing_charts.py --check    # fail if it is stale

WHAT THIS PAGE IS ABOUT, AND WHY IT IS BUILT THE WAY IT IS.

Three separate things in this archive touch school staffing, and they are three different
quantities that a reader will assume are one:

  1. **The town's printed rosters** (`staff_roster_entries`) -- a list of NAMES, by school,
     in every annual town report FY2011-FY2025. No FTE, no funding source, no date within
     the year. A count of these is a count of names the town printed. It is a real
     quantity and it is not a staffing level.
  2. **DESE's published FTE** (`dese_measure`) -- the state DOES publish full-time
     equivalents, for teachers and paraprofessionals, for Lunenburg and for six comparison
     districts, FY2009-FY2025. This is the only FTE series in the archive.
  3. **Budget lines** (`budget_figure`, `sped_para_history`, `sped_teacher_history`) --
     dollars. Rule 11: a line is NET of grants, fees and reimbursement, and a line rising
     is not a position filled.

The page keeps them apart, names which one every figure comes from, and never divides one
by another. Dividing a net budget line by a DESE FTE count produces something that looks
like a cost per employee and is not one, twice over: the numerator excludes every fund but
the general fund, and the denominator counts staff those other funds pay for.

RULE 1. Nothing here measures growth from an actual in one year to a budget in another.
Every dollar series on this page is ONE stage across its whole run, and the stage is
carried in the payload so the page can say which. Nothing here feeds the projection.

RULE 6, LIKE FOR LIKE. A dollar series is built from a panel of lines present in EVERY
year of its run, not from "all lines matching para", which ran from 5 lines to 9 and would
have produced growth that was really coverage. The panel and its size are in the payload.

WHAT THE ROSTER SERIES CANNOT BE READ AS, computed rather than asserted:

  * Which schools got a roster printed changes year to year. Central office is printed in
    some years and not others; Passios closed; the middle school appears as its own roster
    from FY2016. So the year-over-year move in a raw total is partly print practice.
  * FY2024 prints TWO complete Turkey Hill rosters with different principals, and nothing
    on either page says which year each describes. That year is reported as a RANGE.
  * `monty-tech` is six administrators of the regional vocational school Lunenburg sends
    students to. Not Lunenburg staff; excluded, and the exclusion is asserted.
  * The rosters are OCR'd off scanned pages and some department headings came back
    corrupted. Those are DETECTED here by rule, not listed by hand, so the count cannot
    drift as the extraction improves.

WHY A FILE AND NOT A QUERY. D1's free tier stops at 5 million rows read a day. Everything
here is the same for every reader until the database is rebuilt.
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import sys

# The conclusions this report states, as DATA rather than as sentences in a page. See
# scripts/conclusions.py.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/school-staffing.json')
MANIFEST = os.path.join(ROOT, 'sources/data/archive-manifest.csv')
MINUTES = 'sources/meetings/text'

LEA = '01620000'                      # Lunenburg, in DESE's own org code
DISTRICT = 'Lunenburg'

# NOT Lunenburg staff. Six administrators of the regional vocational school the town SENDS
# students to, printed in the FY2019 report beside the district's own rosters.
NOT_OURS = 'monty-tech'
# Printed in 8 of the 15 years. Including it makes the total jump in the years it appears
# and fall in the years it does not, and neither move is a staffing change.
INTERMITTENT = 'central-office'

# The special-education paraprofessional lines. Five, one per school/programme, present in
# every year FY2014-FY2027 -- which is what makes a sum across years comparable at all.
SPED_PARA_LINES = ('ps special ed para', 'es special ed para', 'ms special ed para',
                   'hs special ed para', 'ace special ed para')
# The special-education TEACHER series is read from `sped_teacher_history`, not from a
# list of line keys, because one of its lines was RENAMED mid-run: the elementary line is
# `es special ed resource rm teacher` to FY2024 and `es special ed teacher` from FY2023.
# A key panel spanning both reports a year where one goes to zero and another appears --
# rule 6's "lines that go to zero and reappear renamed produce rates that look like
# findings". The history table is the district's own five-school aggregation and carries
# a documents_disagree flag; the paraprofessional panel below is RECONCILED against its
# twin so the two routes to the same figure cannot silently part company.
NURSE_LINES = ('ps nurses', 'es nurses', 'ms nurses', 'hs nurses', 'nurse coordinator')
SUB_LINES = ('ps regular sub', 'es regular sub', 'ms regular sub', 'hs regular sub',
             'kind regular sub')

# The stage every dollar series on this page is read at. ONE stage, whole run (rule 1).
# `restated` is what the district's own budget books re-present as spent for a closed year
# -- not a ledger figure, and the page says so. The stage was called `actual` until
# 7 September 2026; it was renamed because the name was being read as the accounting
# system. See the comment on ACTUAL_KINDS in scripts/extract_budget_history.py.
DOLLAR_STAGE = 'restated'

# A department heading that names a grade. These pages are SCANNED and read by OCR, so
# some headings came back mangled. They are found by RULE rather than listed by hand, so
# the count cannot go stale as the extraction improves (rule 2 applies to a fixture as
# much as to a sentence).
#
# The rule: a heading containing the word "grade" must have a recognisable ordinal on one
# side of it. `First Grade Teachers`, `Grade 3`, `Grades 6 & 7` and `Grade level
# Paraprofessionals` all pass. `Ith Grade:`, `Gth Grade:`, `8t Grade Teachers`,
# `8*" Grade Teachers`, `econd Grade Teacher` and `secona Grade` do not, and each one is a
# real grade level this project cannot read off the page.
ORDINALS = {'pre-k', 'prek', 'pre', 'kindergarten', 'k',
            'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth',
            '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th',
            'level', 'levels', '1', '2', '3', '4', '5', '6', '7', '8'}
TOKEN = re.compile(r'[a-z0-9-]+', re.I)


def grade_heading_is_readable(text):
    """None if the heading does not name a grade; True/False if it does."""
    tok = [t.lower() for t in TOKEN.findall(text or '')]
    at = [i for i, t in enumerate(tok) if t in ('grade', 'grades')]
    if not at:
        return None
    for i in at:
        near = ([tok[i - 1]] if i else []) + (tok[i + 1:i + 2])
        if any(n in ORDINALS for n in near):
            return True
    return False


def rows(db, sql, *a):
    return [dict(r) for r in db.execute(sql, a)]


# ------------------------------------------------------------------ DESE, the FTE series

def state_series(db):
    """DESE's own figures for Lunenburg. The only FTE in this archive."""
    want = {
        'Teacher FTE': 'teacher_fte',
        'Paraprofessional FTE': 'para_fte',
        'Instructional Support FTE': 'instructional_support_fte',
        'Special Education Instructional Support FTE': 'sped_support_fte',
        'In-District FTE Pupils': 'pupils_in_district',
        'Out-of-District FTE Pupils': 'pupils_out_of_district',
        'Student Headcount': 'student_headcount',
        'Students with disabilities % Headcount': 'pct_disabilities',
        'Low-Income % Headcount': 'pct_low_income',
        'Average Teacher Salary': 'average_teacher_salary',
    }
    got = collections.defaultdict(dict)
    docs, recon = set(), collections.Counter()
    for r in rows(db, 'SELECT fy, measure, value, reconciles, doc_id FROM dese_measure '
                      'WHERE lea = ? AND measure IN (%s)'
                      % ','.join('?' * len(want)), LEA, *want):
        got[r['fy']][want[r['measure']]] = r['value']
        docs.add(r['doc_id'])
        recon[r['reconciles'] or ''] += 1
    if not got:
        sys.exit('dese_measure returned nothing for Lunenburg. A join that matches nothing '
                 'looks exactly like data that is absent -- refusing to write.')
    out = []
    for fy in sorted(got):
        r = dict(fy=fy, **got[fy])
        pu = r.get('pupils_in_district')
        r['paras_per_100'] = 100 * r['para_fte'] / pu if pu and r.get('para_fte') is not None else None
        r['teachers_per_100'] = 100 * r['teacher_fte'] / pu if pu and r.get('teacher_fte') is not None else None
        out.append(r)
    return out, sorted(docs), dict(recon)


def peer_series(db):
    """The same two ratios for every district in DESE's comparison sheet.

    The PANEL IS NOT CONSTANT and that is the source, not a defect: Ayer appears to
    FY2011 and Ayer Shirley from FY2012, which is a regionalisation. Each district
    carries its own first and last year so the page can say so rather than draw a line
    across a gap.
    """
    got = collections.defaultdict(dict)
    for r in rows(db, "SELECT district, fy, measure, value FROM dese_measure "
                      "WHERE measure IN ('Paraprofessional FTE', 'Teacher FTE', "
                      "'In-District FTE Pupils')"):
        got[r['district']].setdefault(r['fy'], {})[r['measure']] = r['value']
    if DISTRICT not in got:
        sys.exit('the peer sheet no longer names Lunenburg -- refusing to write.')
    out = []
    for name in sorted(got):
        pts = []
        for fy in sorted(got[name]):
            v = got[name][fy]
            pu = v.get('In-District FTE Pupils')
            if not pu:
                continue
            pts.append(dict(
                fy=fy,
                paras_per_100=100 * v['Paraprofessional FTE'] / pu
                if v.get('Paraprofessional FTE') is not None else None,
                teachers_per_100=100 * v['Teacher FTE'] / pu
                if v.get('Teacher FTE') is not None else None))
        if pts:
            out.append(dict(district=name, is_lunenburg=name == DISTRICT,
                            first_fy=pts[0]['fy'], last_fy=pts[-1]['fy'], points=pts))
    return out


def rank_in_year(peers, fy, field):
    """Where Lunenburg sits among the districts REPORTING THAT YEAR, and how many that is.

    A rank without its denominator is the shape of error this project keeps finding: the
    comparison set has six members in some years and five in others.
    """
    vals = [(p['district'], q[field]) for p in peers for q in p['points']
            if q['fy'] == fy and q[field] is not None]
    if not any(d == DISTRICT for d, _ in vals):
        return None
    vals.sort(key=lambda t: -t[1])
    return dict(fy=fy, of=len(vals),
                rank=[d for d, _ in vals].index(DISTRICT) + 1,
                value=dict(vals)[DISTRICT],
                highest=vals[0][0], highest_value=vals[0][1],
                lowest=vals[-1][0], lowest_value=vals[-1][1])


# --------------------------------------------------------------- the town's own rosters

def roster(db):
    ent = rows(db, 'SELECT e.fy, e.school, e.page, e.name, e.role_raw, e.grade_or_dept, '
                   '       c.role_category '
                   'FROM staff_roster_entries e '
                   'LEFT JOIN role_classification c '
                   '  ON c.role_raw = e.role_raw AND c.grade_or_dept = e.grade_or_dept')
    if not ent:
        sys.exit('staff_roster_entries is empty -- refusing to write.')
    unjoined = sum(1 for r in ent if r['role_category'] is None)
    if unjoined:
        sys.exit(f'{unjoined} roster entries did not join to role_classification. A row '
                 f'with no category is not a row with no role -- refusing to write.')

    # ---- the FY2024 Turkey Hill problem, DETECTED rather than remembered.
    # A school with two pages whose name lists overlap heavily is the same roster printed
    # twice, not a bigger school. The overlap is measured; the year is reported as a range.
    doubled = []
    by_sy = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in ent:
        if r['name']:
            by_sy[(r['fy'], r['school'])][r['page']].add(r['name'])
    for (fy, school), pages in sorted(by_sy.items()):
        ps = sorted(pages)
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                a, b = pages[ps[i]], pages[ps[j]]
                shared = a & b
                if len(shared) >= 0.4 * min(len(a), len(b)):
                    doubled.append(dict(fy=fy, school=school, pages=[ps[i], ps[j]],
                                        names=[len(a), len(b)], shared=len(shared)))
    doubled_years = {d['fy'] for d in doubled}

    # ---- OCR defects in the printed department headings, found by rule.
    ocr = collections.Counter()
    ocr_where = collections.defaultdict(set)
    graded = 0
    for r in ent:
        g = (r['grade_or_dept'] or '').strip()
        ok = grade_heading_is_readable(g)
        if ok is None:
            continue
        graded += 1
        if not ok:
            ocr[g] += 1
            ocr_where[g].add((r['fy'], r['school']))
    ocr_rows = [dict(printed=g, rows=n,
                     years=sorted({fy for fy, _ in ocr_where[g]}),
                     schools=sorted({s for _, s in ocr_where[g]}))
                for g, n in ocr.most_common()]

    # ---- people appearing on two schools' rosters in one year. The source, not a bug.
    shared_staff = collections.Counter()
    seen = collections.defaultdict(set)
    for r in ent:
        if r['name']:
            seen[(r['fy'], r['name'])].add(r['school'])
    for (fy, _), sch in seen.items():
        if len(sch) > 1:
            shared_staff[fy] += 1

    # ---- the comparable panel: every school building, every year it was printed.
    school_years = collections.defaultdict(set)
    for r in ent:
        school_years[r['school']].add(r['fy'])
    all_years = sorted({r['fy'] for r in ent})
    buildings = sorted(s for s in school_years if s not in (NOT_OURS, INTERMITTENT))

    panel = [r for r in ent if r['school'] in buildings]
    by_year = collections.Counter(r['fy'] for r in panel)
    # For a doubled year, the honest figure is a band: the year with each printed roster
    # taken alone. Neither page says which year it describes.
    bands = {}
    for d in doubled:
        if d['school'] not in buildings:
            continue
        drop = set(d['pages'])
        alt = []
        for keep in d['pages']:
            alt.append(sum(1 for r in panel if r['fy'] == d['fy'] and not (
                r['school'] == d['school'] and r['page'] in drop - {keep})))
        bands[d['fy']] = dict(low=min(alt), high=max(alt), summed=by_year[d['fy']])

    year_rows = []
    for fy in all_years:
        b = bands.get(fy)
        year_rows.append(dict(
            fy=fy,
            names=b['low'] if b else by_year[fy],
            names_high=b['high'] if b else None,
            names_if_summed=b['summed'] if b else None,
            schools=sorted(s for s in buildings if fy in school_years[s]),
            pages=len({(r['school'], r['page']) for r in panel if r['fy'] == fy}),
            central_office_printed=fy in school_years.get(INTERMITTENT, set()),
            doubled=fy in doubled_years,
            shared_names=shared_staff.get(fy, 0)))

    # ---- by role category, on the same panel. A doubled year is marked, not silently
    # halved: there is no way to split a category between two printed rosters.
    cats = collections.Counter(r['role_category'] for r in panel)
    role_rows = []
    for cat in sorted(cats, key=lambda c: (-cats[c], c)):
        pts = collections.Counter(r['fy'] for r in panel if r['role_category'] == cat)
        role_rows.append(dict(
            role=cat, total=cats[cat],
            first_fy=min(pts), last_fy=max(pts),
            points=[dict(fy=fy, names=pts.get(fy, 0), doubled=fy in doubled_years)
                    for fy in all_years]))

    # ---- by school, latest year with no doubling in it.
    clean = [fy for fy in all_years if fy not in doubled_years]
    latest = clean[-1]
    by_school = [dict(school=s, names=sum(1 for r in panel
                                          if r['fy'] == latest and r['school'] == s))
                 for s in buildings if latest in school_years[s]]

    unclassified = cats.get('unknown', 0)
    return dict(
        years=year_rows, roles=role_rows,
        buildings=buildings,
        by_school=dict(fy=latest, rows=sorted(by_school, key=lambda r: -r['names'])),
        entries_total=len(ent), entries_in_panel=len(panel),
        excluded=[dict(school=NOT_OURS,
                       entries=sum(1 for r in ent if r['school'] == NOT_OURS),
                       years=sorted(school_years.get(NOT_OURS, ())),
                       why='administrators of the regional vocational school Lunenburg '
                           'sends students to — not Lunenburg staff'),
                  dict(school=INTERMITTENT,
                       entries=sum(1 for r in ent if r['school'] == INTERMITTENT),
                       years=sorted(school_years.get(INTERMITTENT, ())),
                       why='printed in some annual reports and not others, so including '
                           'it moves the total in years when nothing changed')],
        unclassified=unclassified,
        unclassified_share=unclassified / len(panel),
        doubled=doubled,
        ocr_defects=ocr_rows,
        ocr_rows=sum(r['rows'] for r in ocr_rows),
        grade_headed_rows=graded,
        shared_staff=[dict(fy=fy, names=n) for fy, n in sorted(shared_staff.items())],
        first_fy=all_years[0], last_fy=all_years[-1])


# ------------------------------------------------------------------------- the dollars

def dollar_panel(db, key, label, lines, stage=DOLLAR_STAGE):
    """One panel of budget lines, one stage, only the years where EVERY line reports.

    Rule 6: a sum over a line set that grows from five to nine measures coverage and calls
    it growth. Years where the panel is incomplete are dropped and counted.
    """
    got = collections.defaultdict(dict)
    for r in rows(db, 'SELECT fy, line_key, label, value FROM budget_figure '
                      "WHERE variant = '' AND stage = ? AND line_key IN (%s)"
                      % ','.join('?' * len(lines)), stage, *lines):
        got[r['fy']][r['line_key']] = r['value']
    if not got:
        sys.exit(f'the {key} panel matched no rows in budget_figure -- refusing to write.')
    full = sorted(fy for fy in got if len(got[fy]) == len(lines))
    partial = sorted(fy for fy in got if len(got[fy]) != len(lines))
    if not full:
        sys.exit(f'the {key} panel is complete in no year -- refusing to write.')
    names = {}
    for r in rows(db, 'SELECT line_key, label FROM budget_figure WHERE line_key IN (%s)'
                  % ','.join('?' * len(lines)), *lines):
        names[r['line_key']] = r['label']
    return dict(
        key=key, label=label, stage=stage, source='budget_figure', lines=len(lines),
        line_labels=[names.get(k, k) for k in lines],
        first_fy=full[0], last_fy=full[-1],
        years_dropped=partial,
        points=[dict(fy=fy, dollars=round(sum(got[fy].values()), 2)) for fy in full])


def history_panel(db, table, key, label, stage=DOLLAR_STAGE):
    """A series the extraction already aggregated per school, with its own total column.

    Used where a line was RENAMED mid-run, which a fixed list of line keys cannot follow.
    The table's own `total` is checked against its five school columns before it is used:
    an extract with a total the source itself prints must reconcile to it (rule 13).
    """
    out, disagree = [], 0
    for r in rows(db, f'SELECT * FROM {table} WHERE stage = ? ORDER BY fy', stage):
        parts = [float(r[c] or 0) for c in ('ps', 'es', 'ms', 'hs', 'ace')]
        total = float(r['total'] or 0)
        if abs(sum(parts) - total) > 1:
            sys.exit(f'{table} FY{r["fy"]} {stage}: the five school columns sum to '
                     f'{sum(parts):,.0f} against a printed total of {total:,.0f}. '
                     f'Refusing to write a series off a table that does not tie.')
        disagree += int(r['documents_disagree'] or 0)
        out.append(dict(fy=r['fy'], dollars=total,
                        by_school=dict(zip(('ps', 'es', 'ms', 'hs', 'ace'), parts))))
    if not out:
        sys.exit(f'{table} holds no {stage} rows -- refusing to write.')
    return dict(key=key, label=label, stage=stage, source=table, lines=5,
                line_labels=['Primary', 'Elementary', 'Middle', 'High', 'ACE'],
                first_fy=out[0]['fy'], last_fy=out[-1]['fy'], years_dropped=[],
                documents_disagree=disagree,
                points=[dict(fy=r['fy'], dollars=r['dollars']) for r in out],
                by_school=[dict(fy=r['fy'], **r['by_school']) for r in out])


def reconcile(a, b):
    """Two independent routes to the same figure, compared, with the result PUBLISHED.

    The special education paraprofessional dollars can be reached by summing five line
    keys out of `budget_figure`, or by reading `sped_para_history`'s own total column.
    Both are in this database and nothing else compares them.

    A disagreement is DATA here rather than a crash, because one has been found and it is
    worth showing: FY2024's ACE line. What is refused is a comparison that compares
    nothing, which passes trivially and looks identical to a comparison that passed.
    """
    x = {q['fy']: q['dollars'] for q in a['points']}
    y = {q['fy']: q['dollars'] for q in b['points']}
    shared = sorted(set(x) & set(y))
    if not shared:
        sys.exit(f'{a["key"]} and {b["key"]} share no year. A comparison that compares '
                 f'nothing passes trivially -- refusing to write.')
    off = [dict(fy=fy, a=round(x[fy], 2), b=round(y[fy], 2),
                difference=round(x[fy] - y[fy], 2))
           for fy in shared if abs(x[fy] - y[fy]) > 1]
    return dict(a=a['source'], b=b['source'], years=len(shared), agree=len(shared) - len(off),
                first_fy=shared[0], last_fy=shared[-1], disagree=off)


# Two renderings conclusions.py has no formatter for, because no other report needs them:
# a ratio per hundred pupils, and a full-time equivalent. Both are the state's own
# precision -- DESE publishes FTE to a tenth -- and they are here rather than inline so
# every conclusion on this page renders them the same way.
def per100(v):
    return '%.2f' % float(v)


def fte(v):
    return '%.1f' % float(v)


def change(points, key='dollars'):
    """First to last of a series, as a fact about two published figures and nothing more."""
    if len(points) < 2:
        return None
    a, b = points[0], points[-1]
    return dict(first_fy=a['fy'], last_fy=b['fy'], first=a[key], last=b[key],
                change=b[key] - a[key],
                pct=(b[key] - a[key]) / a[key] if a[key] else None)


# ================================================================= rule 12 and rule 15a
#
# ADDED with the composition sections below. This page had no provenance block and no
# meeting search, because it predates both being part of what a report is. It now
# publishes the documents behind every figure and the coverage denominator behind every
# search, like every other report on this site.

def manifest():
    with open(MANIFEST, encoding='utf-8') as fh:
        return {r['key']: r for r in csv.DictReader(fh)}


def doc(mf, key, table, publisher, note):
    r = mf.get(key)
    if not r:
        sys.exit('%s is not in archive-manifest.csv. A figure without its document is '
                 'not publishable -- refusing to write.' % key)
    return {'path': 'sources/' + key, 'sha256': r['sha256'], 'bytes': int(r['bytes']),
            'url': r['upstream'], 'docs_url': '/docs/' + key, 'table': table,
            'publisher': publisher, 'note': note}


DESE_PUB = 'Massachusetts Department of Elementary and Secondary Education'

# WHAT THE TOWN SAID, and every one of these is re-read out of the archive on every build
# and refused if it is no longer verbatim there. Rule 15a: for every category this report
# says rose or fell, search the meeting archive for what people said about that thing in
# the same year. That step is what found the ELL count and the Turkey Hill class sizes
# below -- two figures spoken in public meetings that match DESE's file for the same year
# to within one child, from sources that never consulted each other.
QUOTES = [
    dict(key='chair-staffing-up', board='finance-committee', date='2026-01-27',
         kind='minutes', doc='7619',
         quote="really irritates me when we say things like we're cutting staff when the "
               "data shows that staffing has gone up almost every year in the last 10 "
               "years",
         why='The Finance Committee chair, at the Tri-Board meeting, showing a chart of '
             'school staffing FY16 to FY25. His chart is HEADCOUNT and this page is FTE, '
             'so the two are not the same measurement — but the direction he describes is '
             'in the state’s FTE series too.'),
    dict(key='composition-not-headcount', board='finance-committee', date='2026-01-27',
         kind='minutes', doc='7619',
         quote='the more relevant data point is the composition of staff, not total '
               'headcount',
         why='The School Committee chair, in the same exchange. This page is the '
             'composition, and it is here because he asked for it in the room.'),
    dict(key='need-has-risen', board='finance-committee', date='2026-01-27',
         kind='minutes', doc='7619',
         quote="the student population's needs have increased substantially, with more "
               "students on IEPs, more English language learners, and more students "
               "entering below benchmark, meaning that even flat staffing represents a "
               "reduction in effective capacity",
         why='The School Committee vice-chair, in the same paragraph. Every quantity she '
             'names except “below benchmark” is published by DESE and is plotted here.'),
    dict(key='cuts-by-subject', board='finance-committee', date='2026-01-27',
         kind='minutes', doc='7619',
         quote='the loss of the Bridge Program, the TLC and Transition programs, and cuts '
               'across special education, music, physical education, world language, '
               'math, and science',
         why='A seventeen-year district employee, in public comment at the same meeting, '
             'naming the subjects. Four of the six she names move in the state’s file '
             'over FY2024–FY2026; mathematics moves the other way.'),
    dict(key='turkey-hill-split', board='finance-committee', date='2026-01-27',
         kind='minutes', doc='7619',
         quote='her position had been changed from full-time fourth grade special '
               'education teacher to split between special education and an MTSS '
               'interventionist',
         why='A teacher at the school this page finds carrying the district’s whole '
             'net fall in teacher FTE, describing one post becoming two part-posts. '
             'DESE counts FTE per ASSIGNMENT, which is exactly what that produces.'),
    dict(key='ell-count', board='school-committee', date='2025-12-17',
         kind='minutes', doc='7572',
         quote='we currently have 71 ELL students',
         why='Said in a School Committee meeting in December 2025. DESE’s file records '
             '70 English learners for the same school year — two counts, taken '
             'independently, one child apart.'),
    dict(key='turkey-hill-class-sizes', board='school-committee', date='2025-09-03',
         kind='minutes', doc='7385',
         quote='We have started this year with 357 students and an average class size of '
               '23/24 for third grade with 113 students, 135 students in the fourth grade '
               'with an average class size of 27, and 109 students in the fifth grade '
               'with an average class size of 22/23',
         why='The principal of the grades 3–5 school, on the first day of the year DESE '
             'records 356 pupils there — 113, 135 and 108 by grade. Three of the four '
             'figures match exactly.'),
    dict(key='esser-hired-13', board='finance-committee', date='2023-04-20',
         kind='minutes', doc='96',
         quote='ESSER funds allowed the School Department to hire 13 new positions across '
               'the district. Social workers, guidance counselors, subject specialists, '
               'tutors, and technicians were all brought into the school',
         why='The single largest confound in any staffing series covering these years. '
             'DESE counts federally funded staff exactly like appropriated staff, so a '
             'grant arriving and a grant ending are both invisible in the FTE line.'),
    dict(key='esser-unwound', board='finance-committee', date='2024-02-21',
         kind='minutes', doc='6417',
         quote='kept 2 social worker positions while cutting 2 budget funded guidance',
         why='The other end of the same grant. Positions were kept, cut and moved onto a '
             'different grant in one year — three different things that look identical '
             'in a headcount and in an FTE count alike.'),
    dict(key='one-music-teacher', board='school-committee', date='2024-01-24',
         kind='minutes', doc='6375',
         quote='there is one high school music teacher and there are two art teachers',
         why='Why this page cannot answer “what happened to music”. DESE publishes one '
             'Arts bucket; the town distinguishes music from art and this is the archive '
             'saying so.'),
    dict(key='fy27-cut-list', board='school-advisory-councils-committees',
         date='2026-03-26', kind='minutes', doc='7726',
         quote='cuts: 2 primary teachers; 2 elementary; CODA; .2 music; interventionist '
               'at primary; custodian; part time AD; band and atheltic transportation',
         why='The district publishes a line-by-line cut list every year. This one is '
             'FY2027 and is not yet in any DESE file — the state’s teacher data stops at '
             'FY2026, so the most recent cuts are visible only in the minutes.'),
]

SEARCHED_TERMS = ['staffing', 'class size', 'paraprofessional', 'world language',
                  'interventionist', 'ELL', 'ESSER', 'guidance counselor']


def said_in_meetings():
    """Every quote, re-read out of the archive and refused if it is not verbatim there."""
    out = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            sys.exit('%s is not here -- a quote on this page is attributed to a document '
                     'that is not in the archive. Refusing to write.' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            sys.exit('the quote attributed to %s %s is no longer in %s -- quote the '
                     'source, never your rendering of it. Refusing to write.'
                     % (spec['board'], spec['date'], rel))
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            kind=spec['kind'], date=spec['date'], quote=spec['quote'], why=spec['why'],
            cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_%s%s%s-%s'
                 % (spec['date'][5:7], spec['date'][8:10], spec['date'][:4], spec['doc'])))
    return out


_ARCHIVE = {}


def archive():
    """The meeting archive, read once: the bodies, and the measured coverage denominator.

    THE DENOMINATOR IS NOT `len(*.txt)`. An image scan extracts to an empty file, so
    counting text files overstates coverage by about a third. `minutes-searchable.csv` is
    the generated authority and it is read rather than recomputed.
    """
    if _ARCHIVE:
        return _ARCHIVE
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        sys.exit('sources/meetings/index.csv is not here -- a search of nothing is not a '
                 'search. Refusing to write.')
    rows_ = list(csv.DictReader(open(idx, encoding='utf-8')))
    bodies, dates = [], []
    for r in rows_:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            bodies.append(open(txt, encoding='utf-8', errors='replace').read())
            if r.get('date'):
                dates.append(r['date'])
    if not bodies or not dates:
        sys.exit('no meeting document is readable -- refusing to publish a count of what '
                 'nobody said.')
    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        sys.exit('sources/data/minutes-searchable.csv is not here -- the searchable share '
                 'cannot be typed. Refusing to write.')
    t = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            t[k] += int(r[k] or 0)
    if not t['searchable'] or t['held'] != t['searchable'] + t['unsearchable']:
        sys.exit('minutes-searchable.csv does not reconcile -- refusing to publish a '
                 'coverage figure that does not add up.')
    _ARCHIVE.update(bodies=bodies, published=len(rows_), text_files_present=len(bodies),
                    held=t['held'], searchable=t['searchable'],
                    unsearchable=t['unsearchable'], image_scan=t['image_scan'],
                    searchable_share=round(t['searchable'] / t['held'], 4),
                    first_date=min(dates), last_date=max(dates))
    return _ARCHIVE


def searched():
    a = archive()
    return [dict(term=t, documents=sum(1 for b in a['bodies']
                                       if re.search(re.escape(t), b, re.I)))
            for t in SEARCHED_TERMS]


def coverage():
    a = archive()
    return {k: a[k] for k in ('published', 'held', 'searchable', 'unsearchable',
                              'image_scan', 'searchable_share', 'text_files_present',
                              'first_date', 'last_date')}


# =====================================================================================
# WHO TEACHES, AND WHOM  --  the composition half of this page
# =====================================================================================
#
# ADDED 9 September 2026, for one reason: two town bodies are publicly disagreeing about
# a fact and this archive can settle what each of them is true of.
#
#   Finance Committee Chair, Tri-Board, 27 January 2026, showing a staffing chart:
#     "it really irritates me when we say things like we're cutting staff when the data
#      shows that staffing has gone up almost every year in the last 10 years"
#   School Committee Vice-Chair, same meeting, same paragraph:
#     "FY25 saw a downward turn, and FY26 included significant layoffs, which was not
#      reflected in the chart ... even flat staffing represents a reduction in effective
#      capacity"
#
# THE PAGE DOES NOT ADJUDICATE THAT, and the temptation to is the whole risk here. Rule 7:
# "teacher FTE rose between these two years" is a measurement and so is "teacher FTE fell
# between those two"; WHO IS RIGHT is not a third measurement, it is a choice of window.
# So every window is drawn, the two named ones are DERIVED by argmin/argmax rather than
# chosen, and the count of rising year-steps is published beside the net change because
# those two facts are what the two claims are respectively about.
#
# FOUR TRAPS, each of which this code asserts against rather than remembering.
#
#  1. DISTRICT ROWS SIT BESIDE SCHOOL ROWS in every one of these DESE tables. A query
#     that forgets `org_level` doubles the district. Every read here names the level and
#     `school_reconciliation` proves the schools sum to the district in every year.
#
#  2. `dese_educator_workforce` PRINTS ITS OWN TOTAL AS A ROW. `All Educators` and the
#     seven race rows are the same people twice, and summing them once produced
#     "administrators doubled" here when the published figures are 14 and 19. Only
#     `race_level = 'all'` is read, and the double is computed and published so the trap
#     is visible rather than merely avoided.
#
#  3. THE SUBJECT CLASSIFICATION IS NOT COMPARABLE BEFORE FY2013. `Core-All Subjects` --
#     one teacher counted against every core subject she teaches -- is 56.5 FTE in FY2008
#     and 11.0 by FY2013, which is 47 FTE moving between categories with no staffing
#     event behind it. Subject series are therefore published for the whole run and
#     DIFFERENCED only from `SUBJECT_ERA`, and the reason is in the payload.
#
#  4. `low_income_pct` AND `econ_disadvantaged_pct` ARE TWO DIFFERENT MEASURES. DESE
#     replaced the first with the second for FY2015-FY2021 and then went back to a
#     redefined `low income`. Joining them into one series produces a rise that is partly
#     a definition. The three segments are published separately and the break years are
#     named. `high_needs_pct` runs unbroken FY2013-FY2026 and is the measure the ratios
#     use -- but it carries low income inside it, so its own FY2022 step is flagged too.
#
# AND THE STANDING CAUTION FROM THE REST OF THIS PAGE APPLIES UNCHANGED. DESE's FTE
# counts staff paid from grants, circuit breaker reimbursement and revolving funds
# alongside those the town appropriates (rule 11), and DESE's FTE is per ASSIGNMENT
# rather than per person -- the EPIMS handbook defines it as "the percent of workday
# staff are involved in an assignment". A subject losing 1.0 FTE may be one person gone,
# or five people each teaching one less section of it.

# The FY2017 reconfiguration. Passios closed after FY2012; Turkey Hill Middle became
# Turkey Hill Elementary (grades 3-5) and Lunenburg Middle School (grades 6-8) opened as
# its own org code in FY2017. A per-school series drawn across that is drawing the
# buildings changing grades, so the per-school panel starts here and says so.
SCHOOL_ERA = 2017
# Subject differences start here. See trap 3 above.
SUBJECT_ERA = 2013
# The total-FTE era. FY2011 reports 102.3 between FY2010's 120.4 and FY2012's 114.4 --
# an 18 FTE fall and a 12 FTE recovery in consecutive years, which no staffing decision
# produces. The whole run is PUBLISHED; the derived peak and trough are taken from here.
TOTAL_ERA = 2013

ALL_TEACHERS = 'All Teachers'
# `Core-All Subjects` is a GROUP, not a subject: an elementary teacher's FTE apportioned
# across the core subjects she teaches. It is kept in the series because dropping it
# would make the subjects appear to sum to less than they do, and it is excluded from the
# "which programme moved" ranking because it is not a programme.
NOT_A_SUBJECT = ('All', ALL_TEACHERS, 'Core-All Subjects')

# What each school teaches, read off the enrolment file's own grade columns rather than
# asserted, so a reconfiguration cannot leave this sentence behind.
GRADE_COLS = [('pk_cnt', 'PK'), ('k_cnt', 'K')] + \
             [('grade_%d_cnt' % i, str(i)) for i in range(1, 13)]


def grade_span(db, org_code, fy):
    """The grades a school actually enrolled in a year, from the state's own columns."""
    r = db.execute('SELECT %s FROM dese_enrollment WHERE lea = ? AND org_code = ? '
                   'AND fy = ?' % ', '.join(c for c, _ in GRADE_COLS),
                   (LEA, org_code, fy)).fetchone()
    if not r:
        return ''
    got = [lab for (col, lab), v in zip(GRADE_COLS, r) if v]
    if not got:
        return ''
    return got[0] if len(got) == 1 else '%s–%s' % (got[0], got[-1])


def upsteps(points, key='fte'):
    """How many of a series' year-steps rose, and how many steps there are.

    The Finance Committee's claim is about DIRECTION IN MOST YEARS and the School
    Committee's is about the LAST STEP, so a net change alone answers neither. Both
    numbers are published for every window this page draws.
    """
    up = sum(1 for a, b in zip(points, points[1:]) if b[key] > a[key])
    return dict(up=up, steps=len(points) - 1)


def window(points, lo, hi, key='fte'):
    """One window of a series, with everything both sides of the argument need."""
    pts = [p for p in points if lo <= p['fy'] <= hi]
    if len(pts) < 2:
        sys.exit('the %s-%s window holds %d points -- a change measured over one year is '
                 'not a window. Refusing to write.' % (lo, hi, len(pts)))
    a, b = pts[0][key], pts[-1][key]
    return dict(first_fy=pts[0]['fy'], last_fy=pts[-1]['fy'], first=a, last=b,
                change=round(b - a, 4), pct=(b - a) / a * 100 if a else None,
                **upsteps(pts, key))


def teacher_totals(db):
    """DESE's `All Teachers` line for the district, every published year.

    Read from `dese_teacher_subject` at `org_level = 'district'`. The same figure is
    printed in three of DESE's files and the agreement is checked below rather than
    assumed.
    """
    out = [dict(fy=r['fy'], fte=r['teacher_fte'],
                students_per_teacher=r['students_per_teacher'],
                licensed_pct=r['licensed_pct'], in_field_pct=r['in_field_pct'])
           for r in rows(db, "SELECT fy, teacher_fte, students_per_teacher, licensed_pct, "
                             "in_field_pct FROM dese_teacher_subject WHERE lea = ? AND "
                             "org_level = 'district' AND subject = ? ORDER BY fy",
                         LEA, ALL_TEACHERS)]
    if len(out) < 15:
        sys.exit('dese_teacher_subject returned %d district years for Lunenburg. A join '
                 'that matches almost nothing looks exactly like a district with almost '
                 'no history -- refusing to write.' % len(out))
    return out


def enrolment(db):
    """Enrolment and every need measure DESE publishes for the district.

    RULE 13 ON THE NEED MEASURES. `low_income_pct` and `econ_disadvantaged_pct` are two
    different questions asked of two different definitions and they are kept in separate
    fields, never coalesced. `high_needs_pct` is the one measure that runs unbroken over
    the modern years, and it is published with its own break flag because low income sits
    inside it.
    """
    out = []
    for r in rows(db, "SELECT fy, total_cnt, swd_cnt, swd_pct, el_cnt, el_pct, "
                      "high_needs_cnt, high_needs_pct, low_income_pct, "
                      "econ_disadvantaged_pct, first_lang_not_english_cnt "
                      "FROM dese_enrollment WHERE lea = ? AND org_level = 'district' "
                      "AND total_cnt IS NOT NULL ORDER BY fy", LEA):
        out.append(dict(r))
    if len(out) < 25:
        sys.exit('dese_enrollment returned %d district years -- refusing to write.'
                 % len(out))
    # A duplicate year would double a denominator silently. DESE prints the district
    # under two spellings in the early 1990s and both reach this table.
    fys = [r['fy'] for r in out]
    if len(set(fys)) != len(fys):
        dup = sorted({f for f in fys if fys.count(f) > 1})
        sys.exit('dese_enrollment holds more than one district row for %s. Two rows for '
                 'one year is a denominator counted twice -- refusing to write.'
                 % ', '.join(str(f) for f in dup))
    return out


def need_breaks(rows_):
    """Where a need series stops being one series, computed rather than remembered."""
    out = []
    for field, what in (('low_income_pct', 'low income'),
                        ('econ_disadvantaged_pct', 'economically disadvantaged')):
        have = sorted(r['fy'] for r in rows_ if r[field] is not None)
        runs, start = [], None
        for i, f in enumerate(have):
            if start is None:
                start = f
            if i + 1 == len(have) or have[i + 1] != f + 1:
                runs.append((start, f))
                start = None
        out.append(dict(measure=field, what=what,
                        runs=[dict(first_fy=a, last_fy=b) for a, b in runs]))
    return out


def composition(db):
    """Teacher FTE decomposed four ways, against enrolment and against need.

    Every one of the four is a different question and none of them is the others:
      * BY YEAR      -- did the number of teachers move, and in which direction, when
      * BY SCHOOL    -- was it one building or all of them
      * BY SUBJECT   -- did a stable total conceal a recomposition
      * BY PROGRAMME -- general education against special education, which is a
                        REGISTERED GAP rather than a finding and is published as one
    """
    totals = teacher_totals(db)
    enr = enrolment(db)
    by_fy_enr = {r['fy']: r for r in enr}

    # ---- the district series, with the three defensible denominators beside it.
    # A ratio has two halves and this page is not allowed to publish one without saying
    # which half moved, so the numerator and both denominators travel together.
    district = []
    for t in totals:
        e = by_fy_enr.get(t['fy'])
        row = dict(t)
        row['students'] = e['total_cnt'] if e else None
        row['high_needs'] = e['high_needs_cnt'] if e else None
        row['swd'] = e['swd_cnt'] if e else None
        row['el'] = e['el_cnt'] if e else None
        row['per_100_students'] = (100 * t['fte'] / e['total_cnt']
                                   if e and e['total_cnt'] else None)
        row['per_100_high_needs'] = (100 * t['fte'] / e['high_needs_cnt']
                                     if e and e['high_needs_cnt'] else None)
        district.append(row)

    era = [p for p in district if p['fy'] >= TOTAL_ERA]
    first_fy, last_fy = district[0]['fy'], district[-1]['fy']

    # ---- THE WINDOWS, AND WHY THERE ARE THREE OF THEM RATHER THAN ONE.
    #
    # The first draft of this took the argmin and the argmax of the modern era and called
    # them "the rise" and "the fall". They are FY2014 and FY2018, and naming them would
    # have been a headline dressed as a derivation: the series ALSO falls to 107.4 in
    # FY2020, climbs to 114.0 in FY2024 and falls again. It has two peaks, no trend, and
    # the sign of "did staffing go up" is a property of the window and not of the town.
    #
    # So the page draws the whole series, publishes EVERY window's sign in one matrix, and
    # names three windows -- each of which has a reason outside anybody's argument:
    #
    #   whole    every year DESE has published. Not a choice.
    #   charted  FY2016-FY2025, because that is the span of the chart shown at the
    #            Tri-Board on 27 January 2026, per the minutes. A document, not a pick.
    #   recent   from the LATEST LOCAL MAXIMUM to the latest published year, which is a
    #            rule applied to the series rather than a year somebody liked.
    peaks = [p for k, p in enumerate(district)
             if 0 < k < len(district) - 1
             and p['fte'] > district[k - 1]['fte'] and p['fte'] > district[k + 1]['fte']]
    if not peaks:
        sys.exit('the teacher series has no local maximum, which cannot be true of a '
                 'series that both rises and falls -- refusing to write.')
    peak = peaks[-1]
    trough = min([p for p in era if p['fy'] <= peak['fy']], key=lambda p: p['fte'])

    # The span of the chart shown at the Tri-Board, read off the minutes rather than
    # chosen. The minutes say "a chart of school staffing from FY16 through FY25"; that
    # chart is HEADCOUNT and this series is FTE, which the page says every time it draws
    # this window. What is borrowed is the span, not the measurement.
    charted_lo, charted_hi = 2016, 2025

    windows = dict(
        whole=dict(why='every year DESE has published',
                   **window(district, first_fy, last_fy)),
        charted=dict(why='the span of the staffing chart shown at the Tri-Board meeting '
                         'of 27 January 2026, per the minutes',
                     **window(district, charted_lo, charted_hi)),
        recent=dict(why='from the latest local maximum in the series to the latest year '
                        'published',
                    **window(district, peak['fy'], last_fy)),
    )
    # The same two endpoints for the denominators, so "staffing fell" and "enrolment fell"
    # are never quoted over different spans (rule 6, like for like).
    for key, w in list(windows.items()):
        lo, hi = w['first_fy'], w['last_fy']
        for field, name in (('students', 'students'), ('per_100_students', 'per_100'),
                            ('high_needs', 'high_needs'),
                            ('per_100_high_needs', 'per_100_high_needs')):
            pts = [p for p in district if lo <= p['fy'] <= hi and p[field] is not None]
            w[name] = (dict(first_fy=pts[0]['fy'], last_fy=pts[-1]['fy'],
                            first=pts[0][field], last=pts[-1][field],
                            change=pts[-1][field] - pts[0][field],
                            pct=((pts[-1][field] - pts[0][field]) / pts[0][field] * 100
                                 if pts[0][field] else None))
                       if len(pts) >= 2 else None)

    # EVERY WINDOW, not three. The matrix is the answer to "did staffing go up": it went
    # up over some spans and down over others, and this counts them instead of choosing.
    # A reader who wants a different pair of years can read the sign off the grid.
    matrix, rose, fell, flat = [], 0, 0, 0
    for a in district:
        row = []
        for b in district:
            if b['fy'] <= a['fy']:
                row.append(None)
                continue
            d = round(b['fte'] - a['fte'], 1)
            row.append(d)
            if d > 0:
                rose += 1
            elif d < 0:
                fell += 1
            else:
                flat += 1
        matrix.append(dict(fy=a['fy'], to=row))
    if rose + fell + flat != len(district) * (len(district) - 1) // 2:
        sys.exit('the window matrix does not hold every pair of years -- refusing to write.')
    every_window = dict(pairs=rose + fell + flat, rose=rose, fell=fell, flat=flat,
                        rows=matrix, years=[p['fy'] for p in district])

    # ---- by school. THE SUM IS ASSERTED AGAINST THE DISTRICT IN EVERY YEAR: district
    # rows and school rows are in one table and a level filter that silently stopped
    # working would look exactly like a district that shed a school.
    recon = []
    for t in totals:
        s = db.execute("SELECT SUM(teacher_fte) FROM dese_teacher_subject WHERE lea = ? "
                       "AND org_level = 'school' AND subject = ? AND fy = ?",
                       (LEA, ALL_TEACHERS, t['fy'])).fetchone()[0]
        if s is None:
            sys.exit('no school rows at all in FY%d, against a district total of %s. A '
                     'join that matches nothing looks exactly like data that is absent '
                     '-- refusing to write.' % (t['fy'], t['fte']))
        recon.append(dict(fy=t['fy'], district=t['fte'], schools=round(s, 4),
                          difference=round(s - t['fte'], 4)))
    worst = max(recon, key=lambda r: abs(r['difference']))
    if abs(worst['difference']) > 0.5:
        sys.exit('the schools sum to %s against a district total of %s in FY%d. The '
                 'per-school panel is only publishable while it reconciles -- refusing '
                 'to write.' % (worst['schools'], worst['district'], worst['fy']))

    schools = []
    for r in rows(db, "SELECT DISTINCT org_code, org_name FROM dese_teacher_subject "
                      "WHERE lea = ? AND org_level = 'school' ORDER BY org_code", LEA):
        pts = []
        for s in rows(db, "SELECT fy, teacher_fte FROM dese_teacher_subject WHERE lea = ? "
                          "AND org_code = ? AND subject = ? ORDER BY fy",
                      LEA, r['org_code'], ALL_TEACHERS):
            e = db.execute('SELECT total_cnt FROM dese_enrollment WHERE lea = ? AND '
                           'org_code = ? AND fy = ?',
                           (LEA, r['org_code'], s['fy'])).fetchone()
            students = e[0] if e else None
            pts.append(dict(fy=s['fy'], fte=s['teacher_fte'], students=students,
                            per_100=(100 * s['teacher_fte'] / students
                                     if students else None)))
        if not pts:
            continue
        era_pts = [p for p in pts if p['fy'] >= SCHOOL_ERA]
        schools.append(dict(
            org_code=r['org_code'], name=r['org_name'],
            grades=grade_span(db, r['org_code'], pts[-1]['fy']),
            first_fy=pts[0]['fy'], last_fy=pts[-1]['fy'],
            open_now=pts[-1]['fy'] == last_fy,
            points=pts,
            since_era=(window(era_pts, SCHOOL_ERA, last_fy)
                       if len(era_pts) >= 2 else None),
            since_peak=(window(era_pts, peak['fy'], last_fy)
                        if len([p for p in era_pts if p['fy'] >= peak['fy']]) >= 2
                        else None)))
    open_now = [s for s in schools if s['open_now'] and s['since_era']]
    if not open_now:
        sys.exit('no school has a full post-reconfiguration series -- refusing to write.')
    moved = sorted(open_now, key=lambda s: s['since_era']['change'])
    steady = [s for s in open_now if abs(s['since_era']['change']) <= 1.0]

    # ---- by subject. `dese_teacher_grade_subject` is the SUPERSET -- it carries
    # Physical/Health, Computer Science, Engineering and twenty more that
    # `dese_teacher_subject` (core academic only) never prints -- so it is the source, and
    # the two files' shared cells are compared rather than trusted.
    agree = disagree = 0
    disagreements = []
    for r in rows(db, "SELECT a.fy, a.org_name, a.subject, a.total_fte, b.teacher_fte "
                      "FROM dese_teacher_grade_subject a JOIN dese_teacher_subject b "
                      "ON a.fy = b.fy AND a.org_code = b.org_code "
                      "AND a.subject = b.subject WHERE a.lea = ?", LEA):
        if r['total_fte'] is None or r['teacher_fte'] is None:
            continue
        if abs(r['total_fte'] - r['teacher_fte']) > 0.05:
            disagree += 1
            disagreements.append(dict(fy=r['fy'], org=r['org_name'], subject=r['subject'],
                                      grade_subject=r['total_fte'],
                                      teacher_subject=r['teacher_fte'],
                                      difference=round(r['total_fte'] - r['teacher_fte'], 2)))
        else:
            agree += 1
    if not agree:
        sys.exit('the two DESE teacher files share no matching cell -- a comparison that '
                 'compares nothing passes trivially. Refusing to write.')

    subject_rows = []
    for r in rows(db, "SELECT DISTINCT subject, subject_level FROM "
                      "dese_teacher_grade_subject WHERE lea = ? AND org_level = 'district' "
                      "ORDER BY subject", LEA):
        pts = [dict(fy=s['fy'], fte=s['total_fte'])
               for s in rows(db, "SELECT fy, total_fte FROM dese_teacher_grade_subject "
                                 "WHERE lea = ? AND org_level = 'district' AND subject = ? "
                                 "ORDER BY fy", LEA, r['subject'])
               if s['total_fte'] is not None]
        if not pts:
            continue
        subject_rows.append(dict(subject=r['subject'], level=r['subject_level'],
                                 is_programme=r['subject'] not in NOT_A_SUBJECT,
                                 first_fy=pts[0]['fy'], last_fy=pts[-1]['fy'],
                                 latest=pts[-1]['fte'], points=pts))

    def subject_window(lo, hi, label, why):
        got = []
        for s in subject_rows:
            if not s['is_programme']:
                continue
            d = {p['fy']: p['fte'] for p in s['points']}
            a, b = d.get(lo, 0.0), d.get(hi, 0.0)
            got.append(dict(subject=s['subject'], first=a, last=b,
                            change=round(b - a, 4),
                            pct=(b - a) / a * 100 if a else None))
        got.sort(key=lambda r: -r['change'])
        up = round(sum(r['change'] for r in got if r['change'] > 0), 4)
        down = round(sum(r['change'] for r in got if r['change'] < 0), 4)
        return dict(key=label.lower().replace(' ', '-'), label=label, why=why,
                    first_fy=lo, last_fy=hi, rows=got,
                    # THE GROSS MOVEMENT, NOT ONLY THE NET. A net of +2 FTE that is +9
                    # against -7 is a completely different decade from a quiet one, and
                    # only the gross figures show it. This is the whole finding of the
                    # subject section.
                    up=up, down=down, gross=round(up - down, 4), net=round(up + down, 4),
                    subjects=len(got))

    subject_windows = [
        subject_window(SUBJECT_ERA, last_fy, 'The comparable run',
                       'every year the subject classification is comparable across'),
        subject_window(charted_lo, charted_hi, 'The charted years',
                       'the span of the staffing chart shown at the Tri-Board'),
        subject_window(peak['fy'], last_fy, 'Since the latest peak',
                       'the same window as the recent fall in the district total'),
    ]

    # ---- by programme area. THIS IS A REGISTERED GAP AND IS PUBLISHED AS ONE.
    # `money_gaps` already carries "Why DESE special education teacher FTE falls from 18.5
    # to 2.0 while total teacher FTE holds flat". A district that had lost nine tenths of
    # its special education teachers would show it everywhere else in these files and does
    # not. The series is drawn because refusing to draw it is how it stayed unexamined;
    # the page states that it cannot be read as a staffing change.
    programme = [dict(r) for r in rows(
        db, "SELECT fy, gen_ed_fte, sped_fte, career_tech_fte, el_fte, total_fte, "
            "reconciles FROM dese_teacher_program_area WHERE lea = ? AND "
            "org_level = 'district' ORDER BY fy", LEA)]
    if not programme:
        sys.exit('dese_teacher_program_area returned nothing for Lunenburg -- refusing '
                 'to write.')
    off = [p for p in programme
           if abs((p['gen_ed_fte'] or 0) + (p['sped_fte'] or 0) + (p['career_tech_fte'] or 0)
                  + (p['el_fte'] or 0) - (p['total_fte'] or 0)) > 0.15]
    if off:
        sys.exit('the programme areas do not sum to their own printed total in FY%s -- '
                 'refusing to write.' % ', FY'.join(str(p['fy']) for p in off))
    prog_total = {p['fy']: p['total_fte'] for p in programme}
    mismatch = [t['fy'] for t in totals
                if t['fy'] in prog_total and abs(prog_total[t['fy']] - t['fte']) > 0.15]
    if mismatch:
        sys.exit('the programme-area total disagrees with the All Teachers line in FY%s. '
                 'Two DESE files that no longer describe the same district cannot both '
                 'be drawn -- refusing to write.'
                 % ', FY'.join(str(f) for f in mismatch))

    # ---- by grade band. Published, and NOT differenced: `multi_grade` absorbs between
    # 11 and 26 FTE depending on the year and FY2018 puts 13.3 in grades 9-12 against
    # 23-27 in every neighbouring year. A band series is a coding series here.
    bands = [dict(r) for r in rows(
        db, "SELECT fy, pk_2_fte, grade_3_5_fte, grade_6_8_fte, grade_9_12_fte, "
            "multi_grade_fte, all_grade_fte, total_fte FROM dese_teacher_grade_subject "
            "WHERE lea = ? AND org_level = 'district' AND subject = 'All' ORDER BY fy", LEA)]
    band_off = [b for b in bands
                if abs(sum(b[c] or 0 for c in ('pk_2_fte', 'grade_3_5_fte', 'grade_6_8_fte',
                                               'grade_9_12_fte', 'multi_grade_fte',
                                               'all_grade_fte')) - (b['total_fte'] or 0)) > 0.15]
    if band_off:
        sys.exit('the grade bands do not sum to their own total in FY%s -- refusing to '
                 'write.' % ', FY'.join(str(b['fy']) for b in band_off))

    # ---- WHO DESE'S TEACHER FILES DO NOT COUNT AT ALL.
    # TJ asked whether the town has staffed up in social workers, guidance or
    # extracurricular. None of them is a teacher on these returns. The only state file
    # that reaches them is the educator workforce file, which is THREE YEARS long, is
    # headcount rather than FTE, and puts every one of them in two residual buckets.
    # THE ROLLUP TRAP IS HERE. `All Educators` is the file's own total printed as a row
    # beside seven race rows that sum to it. Reading both doubles every figure, and doing
    # so once produced "administrators doubled" on this project when the published numbers
    # are 14 and 19. Only race_level = 'all' is read, and the double is computed so the
    # trap is visible in the payload rather than only avoided in the code.
    wf, wf_double = [], []
    for r in rows(db, "SELECT fy, job_class, educators_headcount, hires_headcount, "
                      "retained_pct FROM dese_educator_workforce WHERE lea = ? AND "
                      "race_level = 'all' ORDER BY fy, job_class", LEA):
        wf.append(dict(r))
    for r in rows(db, "SELECT fy, job_class, SUM(educators_headcount) both_levels "
                      "FROM dese_educator_workforce WHERE lea = ? GROUP BY fy, job_class",
                  LEA):
        wf_double.append(dict(r))
    if not wf:
        sys.exit('dese_educator_workforce returned nothing at race_level = all for '
                 'Lunenburg -- refusing to write.')
    by_key = {(r['fy'], r['job_class']): r['educators_headcount'] for r in wf}
    doubled_by = [d for d in wf_double
                  if by_key.get((d['fy'], d['job_class'])) is not None
                  and abs(d['both_levels'] - 2 * by_key[(d['fy'], d['job_class'])]) > 0.5]
    if doubled_by:
        sys.exit('the race detail rows no longer sum to the All Educators row in '
                 'dese_educator_workforce. The rollup shape this code guards against has '
                 'changed and the guard has to be re-derived -- refusing to write.')
    wf_years = sorted({r['fy'] for r in wf})

    # The town's own rosters ARE the only source that names these people, and they carry
    # no FTE -- which is exactly the limit `money_gaps` already registers. The counts are
    # published so a reader can see the shape of what is and is not knowable, with the
    # print-practice caveat the roster section of this page already makes.
    support = []
    for r in rows(db, "SELECT role_category, fy, COUNT(*) n FROM v_staff_roster "
                      "WHERE school NOT IN (?, ?) GROUP BY role_category, fy",
                  NOT_OURS, INTERMITTENT):
        support.append(dict(r))
    support_roles = ('counselor', 'psychologist', 'social_worker', 'nurse',
                     'speech_therapist', 'therapist', 'librarian')
    got_roles = {r['role_category'] for r in support}
    missing = [c for c in support_roles if c not in got_roles]
    if missing:
        sys.exit('the roster classification no longer produces %s. A category that '
                 'matches nothing looks exactly like a role nobody holds -- refusing to '
                 'write.' % ', '.join(missing))
    support_years = sorted({r['fy'] for r in support})
    support_rows = [
        dict(role=c, points=[dict(fy=f, names=next((r['n'] for r in support
                                                    if r['role_category'] == c
                                                    and r['fy'] == f), 0))
                             for f in support_years])
        for c in support_roles]

    return dict(
        first_fy=first_fy, last_fy=last_fy,
        eras=dict(total=TOTAL_ERA, school=SCHOOL_ERA, subject=SUBJECT_ERA,
                  why_total='FY2011 reports 18 FTE below FY2010 and FY2012 reports 12 '
                            'above FY2011, which no staffing decision produces. The whole '
                            'run is drawn; the derived peak and trough are taken from the '
                            'comparable era.',
                  why_school='Passios Elementary closed after FY2012 and the FY2017 '
                             'reconfiguration split Turkey Hill Middle into Turkey Hill '
                             'Elementary and Lunenburg Middle School. A per-school series '
                             'drawn across that is drawing the buildings changing grades.',
                  why_subject='Core-All Subjects -- one teacher counted against every core '
                              'subject she teaches -- falls from 56.5 FTE in FY2008 to '
                              '11.0 in FY2013. That is 47 FTE moving between categories '
                              'with no staffing event behind it.'),
        district=district,
        peak=peak, trough=trough, windows=windows, every_window=every_window,
        enrolment=enr, need_breaks=need_breaks(enr),
        schools=dict(era=SCHOOL_ERA, rows=schools, open_now=[s['org_code'] for s in open_now],
                     reconciliation=recon, worst=worst,
                     biggest_fall=moved[0], steady=[s['name'] for s in steady]),
        subjects=dict(era=SUBJECT_ERA, rows=subject_rows, windows=subject_windows,
                      agreement=dict(compared=agree + disagree, agree=agree,
                                     disagree=disagree, rows=disagreements,
                                     largest=(max((abs(d['difference'])
                                                   for d in disagreements), default=0.0))),
                      source='dese_teacher_grade_subject',
                      checked_against='dese_teacher_subject'),
        programme=dict(rows=programme, registered_gap=(
            'Why DESE special education teacher FTE falls from 18.5 to 2.0 while total '
            'teacher FTE holds flat')),
        bands=bands,
        not_counted=dict(
            workforce=wf, first_fy=wf_years[0], last_fy=wf_years[-1],
            years=len(wf_years),
            job_classes=sorted({r['job_class'] for r in wf}),
            rollup_trap=('`All Educators` is this file’s own total printed as a row '
                         'beside seven race rows that sum to it. Reading both doubles '
                         'every figure.'),
            roster=dict(roles=support_rows, first_fy=support_years[0],
                        last_fy=support_years[-1])),
    )


# ------------------------------------------------------------------------------- build

def build():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    state, dese_docs, dese_recon = state_series(db)
    peers = peer_series(db)
    ros = roster(db)
    mf = manifest()
    comp = composition(db)

    # The paraprofessional dollars, reached twice: by summing the five line keys out of
    # `budget_figure`, and by reading the district's own five-school aggregation in
    # `sped_para_history`. The line panel is the one the page draws, because it is the one
    # that matches the workbook cell (`sheet1!D340 = -157886.32`, checked by hand against
    # `FY27 Budget Projection as of 2.24.26 with restorations.xlsx`). The comparison is
    # published rather than swallowed.
    para = dollar_panel(db, 'sped_para', 'Special education paraprofessionals',
                        SPED_PARA_LINES)
    checked = [reconcile(para, history_panel(db, 'sped_para_history', 'sped_para_history',
                                             'Special education paraprofessionals'))]
    panels = [
        para,
        history_panel(db, 'sped_teacher_history', 'sped_teacher',
                      'Special education teachers'),
        dollar_panel(db, 'nurses', 'Nurses', NURSE_LINES),
        dollar_panel(db, 'subs', 'Regular substitutes', SUB_LINES),
    ]
    for p in panels:
        p['change'] = change(p['points'])

    # The two special-education panels over the window BOTH of them cover. Comparing a
    # 12-year run against an 8-year run and reporting the two percentages side by side is
    # the like-for-like error wearing a different coat.
    para = next(p for p in panels if p['key'] == 'sped_para')
    teach = next(p for p in panels if p['key'] == 'sped_teacher')
    lo = max(para['first_fy'], teach['first_fy'])
    hi = min(para['last_fy'], teach['last_fy'])
    common = dict(first_fy=lo, last_fy=hi, panels=[])
    for p in (para, teach):
        pts = [q for q in p['points'] if lo <= q['fy'] <= hi]
        common['panels'].append(dict(key=p['key'], label=p['label'],
                                     lines=p['lines'], change=change(pts), points=pts))

    by_fy = {r['fy']: r for r in state}
    # The state series' own endpoints, and the roster's, so the page never implies the two
    # cover the same years.
    s_lo, s_hi = state[0]['fy'], state[-1]['fy']
    # The paraprofessional trough: the lowest reported ratio and the years either side.
    ratio = [r for r in state if r['paras_per_100'] is not None]
    trough = min(ratio, key=lambda r: r['paras_per_100'])

    MEASURES = ('teacher_fte', 'para_fte', 'pupils_in_district', 'student_headcount',
                'teachers_per_100', 'paras_per_100')
    fte_change = {}
    for f in MEASURES:
        pts = [dict(fy=r['fy'], v=r[f]) for r in state if r.get(f) is not None]
        fte_change[f] = change(pts, 'v')

    # The same measures over the ROSTER's window, so the page can put the state's FTE
    # beside the town's printed names without either one implying the other's years.
    r_lo, r_hi = ros['first_fy'], ros['last_fy']
    roster_window = {}
    for f in MEASURES:
        pts = [dict(fy=r['fy'], v=r[f]) for r in state
               if r.get(f) is not None and r_lo <= r['fy'] <= r_hi]
        roster_window[f] = change(pts, 'v')

    # Gross wages: present in the archive, and NOT usable as a headcount. Counted here so
    # the page can say why with a figure rather than an adjective.
    wages = rows(db, "SELECT fy, COUNT(*) n, "
                     "SUM(CASE WHEN \"group\" LIKE 'SCHOOL%' THEN 1 ELSE 0 END) school, "
                     "COUNT(DISTINCT status) statuses, MAX(status) status "
                     "FROM report_gross_wages GROUP BY fy ORDER BY fy")

    # EVERY year, not two chosen ones. A rank quoted at a start and an end is a rank the
    # writer picked; the page draws all of them and reads the extremes off the series,
    # which is the same discipline as showing the whole chart.
    para_ranks = [r for r in (rank_in_year(peers, fy, 'paras_per_100')
                              for fy in range(s_lo, s_hi + 1)) if r]
    teacher_ranks = [r for r in (rank_in_year(peers, fy, 'teachers_per_100')
                                 for fy in range(s_lo, s_hi + 1)) if r]
    if not para_ranks or not teacher_ranks:
        sys.exit('the comparison sheet produced no ranks -- refusing to write.')

    # ---- the figures the conclusions rest on, each one derived here and nowhere else.
    lowest_para = min(para_ranks, key=lambda r: r['value'])   # the trough, WITH its rank
    latest_para = para_ranks[-1]
    latest_teach = teacher_ranks[-1]
    # How long Lunenburg has been last of its group without a break, counted back from
    # the most recent year rather than asserted.
    teach_streak = 0
    for r in reversed(teacher_ranks):
        if r['rank'] != r['of']:
            break
        teach_streak += 1
    # How many of the published years Lunenburg was last, and the year the unbroken run
    # began. Both are read off the series rather than described, because the comparison
    # set changes size year to year and a rank without its denominator is the shape of
    # error this project keeps finding.
    # The paraprofessional rise and the enrolment move over the SAME years -- from the
    # trough to the latest published year. A rise measured over one span set beside an
    # enrolment change measured over another is the like-for-like error in one sentence.
    para_rise = 100.0 * (by_fy[s_hi]['para_fte'] / trough['para_fte'] - 1)
    pupils_same_years = 100.0 * (by_fy[s_hi]['pupils_in_district']
                                 / by_fy[trough['fy']]['pupils_in_district'] - 1)
    teach_last_years = sum(1 for r in teacher_ranks if r['rank'] == r['of'])
    streak_from = teacher_ranks[-teach_streak]['fy'] if teach_streak else None
    # THE CLAIM BELOW USED TO ASSERT LUNENBURG IS LAST IN THIS GROUP, and the group is not
    # ours: DESE decides who is on its comparison sheet, and it changed underneath this
    # file mid-build -- charter districts entered the set and the unbroken run went to
    # zero, which crashed the formatter on a `None` year. A conclusion may not assume a
    # ranking it does not control. So the standing is READ, and the sentence is assembled
    # from what the standing turned out to be, with the streak clause present only in the
    # years there is a streak to state.
    is_last = latest_teach['rank'] == latest_teach['of']
    streak_clause = ('and last without a break since %s' % C.fy(streak_from)) if teach_streak \
        else 'though not the lowest in the most recent year the state published'
    cw_para = next(p for p in common['panels'] if p['key'] == 'sped_para')['change']
    cw_teach = next(p for p in common['panels'] if p['key'] == 'sped_teacher')['change']

    # ---- the composition figures the new conclusions rest on, derived here and nowhere
    # else. Every endpoint below is an argmin, an argmax or the end of a published series;
    # none of them is a year somebody chose because it made a point.
    # THE WINDOWS WERE RENAMED AND THIS CONSUMER WAS NOT, which is how the generator came
    # to fail with KeyError: 'rise'. The old names were `rise` and `fall` -- the argmin and
    # argmax of the modern era, FY2014 and FY2018 -- and the comment above their definition
    # explains why naming them that way was a headline dressed as a derivation: the series
    # has TWO peaks, falls to 107.4 in FY2020, climbs to 114.0 in FY2024 and falls again.
    # The sign of "did staffing go up" is a property of the window, not of the town.
    #
    # `whole`, `charted` and `recent` each have a reason outside anybody's argument: every
    # published year; the span of the chart the Tri-Board was actually shown; and the
    # latest local maximum to the latest year, which is a rule applied to the series.
    whole, charted, recent = (comp['windows'][k]
                              for k in ('whole', 'charted', 'recent'))
    ratio_whole = whole['per_100']
    hn = whole['per_100_high_needs']
    if not hn:
        sys.exit('no high-needs ratio window -- refusing to write.')
    worst_school = comp['schools']['biggest_fall']
    steady = comp['schools']['steady']
    sub_run = comp['subjects']['windows'][0]
    sub_fall = comp['subjects']['windows'][2]
    top_up = sub_run['rows'][0]
    top_down = sub_run['rows'][-1]
    cut_down = sub_fall['rows'][-1]

    return dict(
        generated_by='scripts/build_staffing_charts.py',
        source='sources/data/lunenburg.db — staff_roster_entries, role_classification, '
               'dese_measure, budget_figure, report_gross_wages',
        state=dict(
            lea=LEA, docs=dese_docs, reconciles=dese_recon,
            first_fy=s_lo, last_fy=s_hi, points=state,
            change=fte_change, change_over_roster_years=roster_window, trough=trough,
            ranks=dict(paras=para_ranks, teachers=teacher_ranks),
            latest=by_fy[s_hi]),
        peers=peers,
        composition=comp,
        about='Who Lunenburg’s schools employ, in the two instruments that exist: the '
              'names the town prints in its own annual reports, and the full-time '
              'equivalents the state publishes by school, by subject and by programme.',
        grain='Teacher FTE as the state counts it — per ASSIGNMENT, not per person — set '
              'against pupil headcount and the state’s need measures. Not dollars, not '
              'posts, not people, and not a count of who the town appropriates for.',
        sources=[
            doc(mf, 'state-dese/dese-teacher-data.xlsx', 'dese_teacher_subject', DESE_PUB,
                'Teacher FTE by district, by school and by core academic subject, with '
                'the state’s own students-per-teacher figure. FY2008–FY2026.'),
            doc(mf, 'state-dese/dese-teachers-by-grade-subject.xlsx',
                'dese_teacher_grade_subject', DESE_PUB,
                'The same FTE split by grade band and across a much wider subject list — '
                'physical and health education, computer science, engineering and twenty '
                'more the core-academic file never prints. The subject series on this '
                'page is read from here and checked against the file above.'),
            doc(mf, 'state-dese/dese-teachers-by-program-area.xlsx',
                'dese_teacher_program_area', DESE_PUB,
                'Teacher FTE split into general education, special education, career and '
                'technical, and English learner. Published on this page as a registered '
                'gap rather than as a finding — see the section that draws it.'),
            doc(mf, 'state-dese/dese-enrollment-by-grade.xlsx', 'dese_enrollment',
                DESE_PUB,
                'Enrolment by grade and by school, with students with disabilities, '
                'English learners, high needs and low income. FY1992–FY2026; the need '
                'measures start later and one of them changes definition twice.'),
            doc(mf, 'state-dese/dese-educators-retention.xlsx', 'dese_educator_workforce',
                DESE_PUB,
                'Educator headcount and retention by job classification, FY2021–FY2023. '
                'The only state file that reaches counsellors, administrators and '
                'paraprofessionals as a group — three years, headcount not FTE.'),
        ],
        said=said_in_meetings(),
        searched=searched(),
        minutes=coverage(),
        not_established=[
            'Whether any position was filled. DESE reports FTE per ASSIGNMENT — the '
            'state’s own handbook defines it as the percent of a workday a member of '
            'staff is involved in an assignment — so one person split across two roles '
            'and two people each half-time are the same figure. A teacher at Turkey Hill '
            'described exactly that split in a public meeting in January 2026.',
            'Who pays for any of it. DESE counts staff paid from grants, circuit breaker '
            'reimbursement and revolving funds alongside those the town appropriates, so '
            'the arrival and the ending of the federal ESSER money — thirteen positions '
            'by the Finance Committee’s own account — are both invisible in this series.',
            'What happened to music. DESE publishes one Arts bucket and the town '
            'distinguishes music from art in its own minutes. Arts FTE rose over the '
            'years the district’s cut lists name a music position each time.',
            'Whether a subject losing FTE lost a course. A fall of one FTE can be a '
            'section, a course, or one teacher’s timetable reallocated across subjects, '
            'and nothing published distinguishes them.',
            'What Lunenburg’s counsellors, social workers, psychologists and nurses do as '
            'a series. None of them is a teacher on these returns; the state’s workforce '
            'file reaches them for three years only and puts them in two residual '
            'buckets; the town’s rosters name them and carry no FTE.',
            'How the low-income share moved between FY2014 and FY2022. DESE replaced '
            '“low income” with “economically disadvantaged” and then went back to a '
            'redefined “low income”, so the three segments published here are three '
            'measures and not one series.',
        ],
        closes='DESE’s End of Year Financial Report, Schedule 1, as Lunenburg files it, '
               'which separates spending by fund and is the document that would say which '
               'fund pays which post; the district’s own EPIMS work assignment detail by '
               'school, subject and job classification, which would turn an assignment '
               'count into a position count; and the district’s master schedule by year, '
               'which would say whether a subject losing FTE lost a course.',
        roster=ros,
        dollars=dict(stage=DOLLAR_STAGE, panels=panels, sped_common_window=common,
                     reconciled=checked),
        wages=dict(
            rows=sum(r['n'] for r in wages), years=len(wages),
            school_tagged=sum(r['school'] for r in wages),
            statuses=sorted({r['status'] for r in wages}),
            by_year=[dict(fy=r['fy'], rows=r['n'], school_tagged=r['school'])
                     for r in wages]),
        conclusions=emit('school-staffing', [
            conclusion(
                id='the-change-is-paraprofessionals',
                claim='Rise in paraprofessionals for each hundred pupils, the biggest change in staffing',
                so_what='Lunenburg went from the lowest on the state’s comparison sheet to the highest.',
                lede='Paraprofessionals are the biggest change in who Lunenburg’s '
                      'schools employ: the state’s count went from %s per hundred '
                      'pupils in %s, the lowest of the %s districts on the state’s own '
                      'sheet, to %s in '
                      '%s, the highest.'
                      % (per100(lowest_para['value']), C.fy(lowest_para['fy']),
                         C.num(latest_para['of']), per100(latest_para['value']),
                         C.fy(latest_para['fy'])),
                detail='%s full-time equivalents in %s and %s in %s — a rise of %s '
                       'over years in which in-district enrolment %s %s. Nothing else '
                       'in this archive could have told a resident that: the town prints '
                       'staff rosters every year and they carry names without hours, so '
                       'the state’s file is the only place the size of the shift is '
                       'visible.'
                       % (fte(trough['para_fte']), C.fy(trough['fy']),
                          fte(by_fy[s_hi]['para_fte']), C.fy(s_hi),
                          C.pct(para_rise),
                          'fell' if pupils_same_years < 0 else 'rose',
                          C.pct(abs(pupils_same_years))),
                figure='fte_rise',
                figures={
                    'low_ratio': figure(lowest_para['value'], per100(lowest_para['value'])),
                    'low_fy': figure(lowest_para['fy'], C.fy(lowest_para['fy'])),
                    'last_ratio': figure(latest_para['value'], per100(latest_para['value'])),
                    'last_fy': figure(latest_para['fy'], C.fy(latest_para['fy'])),
                    'districts': figure(latest_para['of'], C.num(latest_para['of'])),
                    'low_fte': figure(trough['para_fte'], fte(trough['para_fte'])),
                    'last_fte': figure(by_fy[s_hi]['para_fte'],
                                       fte(by_fy[s_hi]['para_fte'])),
                    'trough_fy': figure(trough['fy'], C.fy(trough['fy'])),
                    'last_year': figure(s_hi, C.fy(s_hi)),
                    'fte_rise': figure(para_rise, C.pct(para_rise)),
                    'enrolment_move': figure(abs(pupils_same_years),
                                             C.pct(abs(pupils_same_years))),
                },
                kind='measured',
                basis='DESE’s own staffing and enrolment files for Lunenburg and for '
                      'the districts on its published comparison sheet, %s–%s. State '
                      'figures, printed by the state — not the town’s rosters, '
                      'which carry no hours, and not a budget line.'
                      % (C.fy(s_lo), C.fy(s_hi)),
                not_shown='Whether any of this is about children. An FTE count is staff: '
                          'not a count of students with disabilities, not one-to-one '
                          'assignments, not hours delivered. And DESE counts staff paid '
                          'from grants, circuit breaker reimbursement and revolving funds '
                          'alongside those the town appropriates, so this series cannot '
                          'say who pays for the rise — DESE’s End of Year '
                          'Financial Report, which separates spending by fund, is what '
                          'would.',
                see=[('/what-special-education-costs', 'what special education costs'),
                     ('/what-other-districts-spend', 'what other districts spend')],
            ),
            conclusion(
                id='fewest-teachers-per-pupil-in-the-group',
                claim='Teaching staff for each hundred pupils, near the bottom of the state’s comparison group',
                so_what='Teaching fell faster than enrollment did, so falling rolls do not explain it.',
                lede='Lunenburg ranks %s of the %s districts on the state’s '
                      'comparison sheet for teachers per pupil — and falling '
                      'enrolment is not the explanation: teacher FTE fell %s since %s '
                      'while in-district enrolment fell %s.'
                      % (C.num(latest_teach['rank']), C.num(latest_teach['of']),
                         C.pct(abs(fte_change['teacher_fte']['pct']) * 100), C.fy(s_lo),
                         C.pct(abs(fte_change['pupils_in_district']['pct']) * 100)),
                detail='%s teacher FTE per hundred in-district pupils in %s, down from '
                       '%s in %s: teaching fell faster than the roll did. It has been '
                       'last in the group in %s of the %s years the state has published, '
                       '%s. The two things a reader hears '
                       'as contradictory are both true here — measured from %s '
                       'instead, the ratio has RISEN, from %s, because over those years '
                       'the denominator fell faster. Which window a comparison is drawn '
                       'over decides its sign, so the window belongs beside the figure.'
                       % (per100(latest_teach['value']), C.fy(latest_teach['fy']),
                          per100(fte_change['teachers_per_100']['first']), C.fy(s_lo),
                          C.num(teach_last_years), C.num(len(teacher_ranks)),
                          streak_clause,
                          C.fy(roster_window['teachers_per_100']['first_fy']),
                          per100(roster_window['teachers_per_100']['first'])),
                figure='ratio',
                figures={
                    'rank': figure(latest_teach['rank'], C.num(latest_teach['rank'])),
                    'districts': figure(latest_teach['of'], C.num(latest_teach['of'])),
                    'teacher_fall': figure(
                        abs(fte_change['teacher_fte']['pct']) * 100,
                        C.pct(abs(fte_change['teacher_fte']['pct']) * 100)),
                    'first_fy': figure(s_lo, C.fy(s_lo)),
                    'enrolment_fall': figure(
                        abs(fte_change['pupils_in_district']['pct']) * 100,
                        C.pct(abs(fte_change['pupils_in_district']['pct']) * 100)),
                    'ratio': figure(latest_teach['value'], per100(latest_teach['value']),
                                    'for every 100 pupils'),
                    'last_fy': figure(latest_teach['fy'], C.fy(latest_teach['fy'])),
                    'first_ratio': figure(fte_change['teachers_per_100']['first'],
                                          per100(fte_change['teachers_per_100']['first'])),
                    'years_last': figure(teach_last_years, C.num(teach_last_years)),
                    'years_published': figure(len(teacher_ranks),
                                              C.num(len(teacher_ranks))),
                    **({'streak_from': figure(streak_from, C.fy(streak_from))}
                       if teach_streak else {}),
                    'roster_first': figure(
                        roster_window['teachers_per_100']['first'],
                        per100(roster_window['teachers_per_100']['first'])),
                    'roster_first_fy': figure(
                        roster_window['teachers_per_100']['first_fy'],
                        C.fy(roster_window['teachers_per_100']['first_fy'])),
                },
                kind='measured',
                basis='DESE’s published teacher FTE and in-district FTE pupils, for '
                      'Lunenburg and for every district on the state’s comparison '
                      'sheet, every year it has been published. The rank is taken among '
                      'the districts REPORTING IN THAT YEAR, and the count of them is '
                      'carried beside it.',
                not_shown='That a staffing level was chosen. A district cannot shed a '
                          'teacher for each departing child — sections, grade spans '
                          'and required subjects set a floor that has nothing to do with '
                          'the enrolment total, so a ratio moving is the arithmetic of a '
                          'falling denominator at least as much as it is a decision. And '
                          'a teacher here is DESE’s definition applied by DESE, not '
                          'the district’s payroll and not the contract’s '
                          'bargaining unit.',
                see=[('/what-other-districts-spend', 'what other districts spend'),
                     ('/if-students-leave', 'what happens as students leave')],
            ),
            conclusion(
                id='inside-sped-the-money-went-to-paraprofessionals',
                claim='Rise in what the schools budget for special education paraprofessionals',
                so_what='Special education teacher lines rose a fifth as fast. Inside this budget, the money went to paraprofessionals.',
                lede='Inside special education the money went to paraprofessionals: '
                      'those %s budget lines rose %s over %s, while the %s special '
                      'education teacher lines rose %s.'
                      % (C.num(5), C.pct(cw_para['pct'] * 100),
                         C.fyspan(common['first_fy'], common['last_fy']), C.num(5),
                         C.pct(cw_teach['pct'] * 100)),
                detail='%s to %s against %s to %s, both panels read at the %s stage over '
                       'the %s years both of them cover. These are NET general fund '
                       'lines — what the town has to raise after grants, circuit '
                       'breaker reimbursement and revolving funds have paid their share '
                       '— so the same rise appears whether the district added '
                       'paraprofessionals or a grant that had been paying for them ended '
                       'and the cost landed on the town. Which of the two it is matters: '
                       'this is the line this project’s own in-district special '
                       'education escalator is built on.'
                       % (C.usd(cw_para['first']), C.usd(cw_para['last']),
                          C.usd(cw_teach['first']), C.usd(cw_teach['last']),
                          DOLLAR_STAGE,
                          C.num(common['last_fy'] - common['first_fy'] + 1)),
                figures={
                    'lines': figure(5, C.num(5)),
                    'para_pct': figure(cw_para['pct'] * 100, C.pct(cw_para['pct'] * 100)),
                    'span': figure(common['first_fy'],
                                   C.fyspan(common['first_fy'], common['last_fy'])),
                    'teacher_pct': figure(cw_teach['pct'] * 100,
                                          C.pct(cw_teach['pct'] * 100)),
                    'para_first': figure(cw_para['first'], C.usd(cw_para['first'])),
                    'para_last': figure(cw_para['last'], C.usd(cw_para['last'])),
                    'teacher_first': figure(cw_teach['first'], C.usd(cw_teach['first'])),
                    'teacher_last': figure(cw_teach['last'], C.usd(cw_teach['last'])),
                    'years': figure(common['last_fy'] - common['first_fy'] + 1,
                                    C.num(common['last_fy'] - common['first_fy'] + 1)),
                },
                figure='para_pct',
                kind='measured',
                basis='Two panels of five budget lines each, out of the district’s '
                      'own budget books at one stage across their whole run, compared '
                      'only over the years both panels report. The paraprofessional '
                      'panel is reconciled against the district’s own five-school '
                      'aggregation of the same figures, and the comparison is published '
                      'in this payload rather than swallowed. A budget book restating '
                      'itself is a document the district assembled, not an accounting '
                      'printout.',
                not_shown='That anybody was hired. A budget line is dollars: not a post, '
                          'not a person, not an hour — a line rising and a line '
                          'paying more for the same people are the same number on the '
                          'page. Nor does it show what special education cost, because '
                          'these lines are net of every fund but the general fund.',
                see=[('/what-special-education-costs', 'what special education costs'),
                     ('/when-grants-end', 'what happens when a grant stops')],
            ),
        ]),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {os.path.relpath(OUT, ROOT)} is not what the database now '
                  f'produces. Run scripts/build_staffing_charts.py.')
            return 1
        print(f'ok — {os.path.relpath(OUT, ROOT)} reproduces from the database')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    print(f"wrote {os.path.relpath(OUT, ROOT)} — "
          f"{d['roster']['entries_in_panel']} roster names in the comparable panel "
          f"FY{d['roster']['first_fy'] % 100}–FY{d['roster']['last_fy'] % 100}, "
          f"{len(d['state']['points'])} years of DESE FTE, "
          f"{len(d['peers'])} districts, {len(d['dollars']['panels'])} dollar panels, "
          f"{len(d['roster']['ocr_defects'])} OCR-corrupted headings "
          f"({d['roster']['ocr_rows']} rows)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
