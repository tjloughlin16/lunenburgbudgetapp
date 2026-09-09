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


# ------------------------------------------------------------------------------- build

def build():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    state, dese_docs, dese_recon = state_series(db)
    peers = peer_series(db)
    ros = roster(db)

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
                so_what='Special education teacher lines rose a fifth as fast. Inside this budget, the money went to assistants.',
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
