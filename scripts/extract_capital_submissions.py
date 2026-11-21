#!/usr/bin/env python3
"""The school department's FY28-FY37 capital request forms, and the Superintendent's
narrative that schedules them -- both from the School Committee packet of 21 October 2026.

    python3.11 scripts/extract_capital_submissions.py          # write both CSVs
    python3.11 scripts/extract_capital_submissions.py --check  # rebuild, compare, prove

Two datasets, because they are two documents that disagree:

  sources/data/capital-submissions-fy28.csv   one row per FORM, as the form prints it
  sources/data/capital-narrative-fy28.csv     one row per line of the NARRATIVE's schedule

A form is a department's request on the Town's template. The narrative
(`Lunenburg_Capital_Plan Narrative V.2`) is the Superintendent's recommendation, and it moves
years and fixes amounts. Each form row carries the narrative line it became, so every place
the two differ is a column comparison, not a sentence.

WHAT THE FORMS PRINT, AND WHERE. Facilities forms fill `Funding Requested` and `Total
Funding`; their cost table is the WHOLE facilities programme pasted into every form (its
Gross Total, 6,582,902, is the same on eleven forms -- the narrative says so too), so it is
not read as the project's cost. Technology forms leave `Funding Requested` as the template's
placeholder and put the project's cost in the cost table, in the column for its year; there
the year and amount come from that table. Every value is kept as printed in `*_printed`.

THE CHECK. The narrative prints a total for each year (`The priced FY28 requests total
$4,228,877.27.`); the schedule rows extracted here must sum to every one of them, and the
FY28-FY33 schedule must hold 19 projects (FY28 7, FY29 3, FY30 4, FY31 1, FY32 2, FY33 2).
Every form must map to a narrative line or be named in NOT_IN_NARRATIVE, and every priced
narrative line in FY28-FY36 or the smaller schedule must have a form.
"""
import argparse
import csv
import io
import os
import re
import sys
import zipfile
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
FOLDER = 'budget-workbooks/school-committee-2026-10-21/'
NARRATIVE = FOLDER + 'lunenburg-capital-plan-narrative-v.2.docx'
TECH_LIST = FOLDER + 'capital-projects-tech.docx'
OUT_FORMS = os.path.join(SRC, 'data', 'capital-submissions-fy28.csv')
OUT_NARR = os.path.join(SRC, 'data', 'capital-narrative-fy28.csv')

# The narrative's FY28-FY33 schedule, counted by table row. 19 projects.
EXPECT_COUNTS = {'FY28': 7, 'FY29': 3, 'FY30': 4, 'FY31': 1, 'FY32': 2, 'FY33': 2}

# FORM -> the narrative line it became: (section, project as the narrative prints it).
# Matched by reading both; neither document carries an id that joins them.
MAP = {
    'capital-submission-form-fy28-37-turf-field.docx': ('FY28', 'Turf and track replacement allocation'),
    'capital-submission-form-fy-28-37-3-play-ground-replacement.docx': ('FY28', 'Playground replacement construction'),
    'capital-submission-form-fy28-37-6-drive-way-construction.docx': ('FY28', 'Driveway replacement and expansion construction'),
    'capital-submission-form-fy28-37-1-truck-1.docx': ('FY28', 'Facilities truck replacement'),
    'fy28-auditorium.docx': ('FY28', 'Auditorium audio and video upgrade'),
    'fy28-thes-bells.docx': ('FY28', 'Clocks and bells replacement'),
    'fy28-core-switches-capital-submission-form-fy28-37-1.docx': ('FY28', 'Core switches'),
    'capital-submission-form-fy28-37-2-turkey-hill-exterior-doors-1.docx': ('FY29', 'Exterior door replacement'),
    'fy29-districtwide-physical-cameras.docx': ('FY29', 'Physical security camera replacement'),
    'fy29-distribution-and-access-switches-capital-submission-form-fy28-37-1.docx': ('FY29', 'Distribution and access switch renewal'),
    'fy30-lmhs-projectors.docx': ('FY30', 'Classroom TouchView displays'),
    'fy30-voip-and-paging-capital-submission-form-fy28-37-1.docx': ('FY30', 'Phone system and paging upgrade'),
    'capital-submission-form-fy28-37-5-thes-design.docx': ('FY32', 'School planning and schematic design'),
    'fy32-thes-touchviews.docx': ('FY32', 'Classroom TouchView displays'),
    'capital-submission-form-fy28-37-10-thes-elevator.docx': ('FY33', 'Accessibility lift replacement'),
    'capital-submission-form-fy28-37-9-roof-replacement.docx': ('FY33', 'Roof replacement'),
    'fy36-camera-servers.docx': ('FY36', 'Camera servers'),
    'fy36-primary-touchviews.docx': ('FY36', 'Classroom TouchView displays'),
    'capital-submission-form-fy28-37-7-hot-water-tank.docx': ('smaller', 'Hot water holding tank replacement'),
    'capital-submission-form-fy28-37-11-man-lift.docx': ('smaller', 'Personnel lift purchase'),
    'capital-submission-form-fy28-37-6-gas-boiler-design.docx': ('smaller', 'Boiler design'),
}
# A form in the packet that the narrative does not schedule anywhere.
NOT_IN_NARRATIVE = {
    'capital-submission-form-fy28-37-13-primary-roof.docx':
        'Primary School roof, $700,000 in FY29 on the form; no Primary roof line in the '
        'narrative, which schedules one roof ($1.5M, FY33, "need to confirm the roof location")',
}
# Narrative lines with no form in the packet, and why that is not an extraction miss.
NO_FORM = {
    ('FY30', 'Bells replacement'): 'TBD in the narrative; on the technology list, no form',
    ('FY31', 'Wireless access point renewal'): 'TBD in the narrative; on the technology list, no form',
}

FORM_FIELDS = ['form', 'project', 'department', 'location', 'category', 'priority_tier',
               'rank', 'rank_of', 'fy_requested', 'fy_requested_printed', 'amount',
               'amount_printed', 'amount_from', 'target_completion', 'request_status',
               'narrative_section', 'narrative_project', 'narrative_amount', 'differs', 'note']
NARR_FIELDS = ['section', 'facility', 'project', 'amount', 'amount_printed', 'status']
LABELS = ['Department', 'Project Title', 'Location / Asset', 'Request Status', 'Priority Tier',
          'Funding Requested', 'Target Completion', 'Total Funding', 'Category']
COST_ROWS = ['Study / Design', 'Land Acquisition', 'Construction', 'Equipment / Purchase',
             'Installation / Training', 'Contingency']
COST_COLS = ['Total', 'FY28', 'FY29', 'FY30', 'FY31', 'FY32', 'FY33–37']


def _xml(path):
    return zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')


def _text(fragment):
    paras = re.findall(r'<w:p[ >].*?</w:p>', fragment, re.S)
    return ' '.join(''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p)) for p in paras).strip()


def cells(path):
    return [_text(tc) for tc in re.findall(r'<w:tc[ >].*?</w:tc>', _xml(path), re.S)]


def money(s):
    """A printed amount, as dollars. `3m` and `1.5m` are how two forms print millions."""
    s = (s or '').strip().replace(',', '').replace('$', '')
    m = re.fullmatch(r'([\d.]+)\s*(m|mil)?', s, re.I)
    if not m:
        return None
    v = Decimal(m.group(1))
    return v * 1000000 if m.group(2) else v


def fy(s):
    m = re.search(r'FY\s*(?:20)?(\d{2})', s or '')
    return f'FY{m.group(1)}' if m else ''


def read_form(path):
    c = cells(path)
    d = {}
    for i, v in enumerate(c):
        for L in LABELS:
            if v.startswith(L) and L not in d:
                d[L] = (v[len(L):].strip() or (c[i + 1] if i + 1 < len(c) else '')).strip()
    tier, rank, of = d.get('Priority Tier', ''), '', ''
    m = re.search(r'Rank\s+(\d+)\s+of\s+(\d+)', tier)
    if m:
        rank, of = m.groups()
    tier = re.sub(r'\s*Rank .*$', '', tier).strip()
    row = {'project': d.get('Project Title', ''), 'department': d.get('Department', ''),
           'location': d.get('Location / Asset', ''), 'category': d.get('Category', ''),
           'priority_tier': '' if tier == 'Select' else tier, 'rank': rank, 'rank_of': of,
           'fy_requested_printed': d.get('Funding Requested', ''),
           'amount_printed': d.get('Total Funding', ''),
           'target_completion': d.get('Target Completion', ''),
           'request_status': re.sub(r'\s+', ' ', d.get('Request Status', ''))}
    total = money(row['amount_printed'])
    if total is not None:
        row.update(amount=f'{total:.2f}', amount_from='Total Funding',
                   fy_requested=fy(row['fy_requested_printed']))
        return row
    # A technology form: the cost table, in the column for its year.
    years, amount = set(), Decimal(0)
    for i, v in enumerate(c):
        if v in COST_ROWS:
            for col, cell in zip(COST_COLS, c[i + 1:i + 1 + len(COST_COLS)]):
                val = money(cell)
                if val is not None and col != 'Total':
                    years.add(col)
                    amount += val
    if len(years) != 1:
        sys.exit(f'{os.path.basename(path)}: cost table has amounts in {sorted(years)}')
    row.update(amount=f'{amount:.2f}', amount_from='cost table, ' + ' + '.join(
        f'{r}' for r in COST_ROWS if r in c), fy_requested=years.pop())
    return row


def read_narrative(path):
    """Every schedule table, under the heading (`FY28`, `FY29` ...) that precedes it."""
    xml = _xml(path)
    body = xml[xml.index('<w:body>'):]
    rows, section, printed = [], None, {}
    for m in re.finditer(r'<w:tbl>.*?</w:tbl>|<w:p[ >].*?</w:p>', body, re.S):
        frag = m.group(0)
        if frag.startswith('<w:p'):
            t = _text(frag)
            h = re.fullmatch(r'(FY\d\d)(?: provisional placement| outlook)?', t)
            if h:
                section = h.group(1)
            elif t.startswith('Smaller maintenance and equipment requests'):
                section = 'smaller'
            elif t.startswith(('Costs and funding', 'Reporting on smaller')):
                section = None
            for y, amt in re.findall(r'The priced (FY\d\d)(?: capital)? requests total \$([\d,]+(?:\.\d\d)?)', t):
                printed[y] = money(amt)
            s = re.search(r'The following requests total \$([\d,]+)', t)
            if s:
                printed['smaller'] = money(s.group(1))
            s = re.search(r'The priced FY28–FY33 capital requests total \$([\d,]+(?:\.\d\d)?)', t)
            if s:
                printed['FY28-FY33'] = money(s.group(1))
            continue
        if not section:
            continue
        trs = [[_text(tc) for tc in re.findall(r'<w:tc[ >].*?</w:tc>', tr, re.S)]
               for tr in re.findall(r'<w:tr[ >].*?</w:tr>', frag, re.S)]
        for tr in trs[1:]:
            if section == 'smaller':
                if 'Total' in tr:
                    continue
                status, facility, project, amt = tr
            elif section == 'FY27':
                facility, project, amt = tr
                status = amt.split('.', 1)[1].strip() if '.' in amt[-30:] else ''
                amt = amt.split(' ')[0].rstrip('.')
            else:
                facility, project, amt = tr
                status = ''
            v = money(amt.split(' ')[0])
            rows.append({'section': section, 'facility': facility, 'project': project,
                         'amount': '' if v is None else f'{v:.2f}', 'amount_printed': amt,
                         'status': status})
    return rows, printed


def build():
    folder = os.path.join(SRC, FOLDER)
    forms = sorted(f for f in os.listdir(folder)
                   if f.endswith('.docx') and f not in (os.path.basename(NARRATIVE),
                                                        os.path.basename(TECH_LIST))
                   and 'homecoming' not in f)
    narr, printed = read_narrative(os.path.join(SRC, NARRATIVE))
    by_line = {(r['section'], r['project']): r for r in narr}
    out = []
    for f in forms:
        row = {'form': FOLDER + f, **read_form(os.path.join(folder, f))}
        if f in MAP:
            line = by_line.get(MAP[f])
            if not line:
                sys.exit(f'{f}: the narrative has no line {MAP[f]}')
            row.update(narrative_section=line['section'], narrative_project=line['project'],
                       narrative_amount=line['amount'])
            diffs = []
            span = row['fy_requested'] == 'FY33–37' and line['section'] in (
                'FY33', 'FY34', 'FY35', 'FY36', 'FY37')
            if span:
                row['note'] = ('the template\'s last cost column is FY33–37; the file is named '
                               + f.split('-')[0].upper())
            if line['section'] not in ('smaller',) and row['fy_requested'] and not span \
                    and row['fy_requested'] != line['section']:
                diffs.append(f"year: form {row['fy_requested']}, narrative {line['section']}")
            if line['amount'] and Decimal(row['amount']) != Decimal(line['amount']):
                diffs.append(f"amount: form {row['amount']}, narrative {line['amount']}")
            row['differs'] = '; '.join(diffs)
        elif f in NOT_IN_NARRATIVE:
            row['note'] = NOT_IN_NARRATIVE[f]
            row['differs'] = 'not in the narrative'
        else:
            sys.exit(f'{f}: a form neither mapped nor named in NOT_IN_NARRATIVE')
        out.append(row)
    return out, narr, printed


def prove(forms, narr, printed):
    problems = []
    counts = {}
    for r in narr:
        counts[r['section']] = counts.get(r['section'], 0) + 1
    for y, n in EXPECT_COUNTS.items():
        if counts.get(y) != n:
            problems.append(f'{y}: {counts.get(y)} schedule rows, expected {n}')
    total19 = sum(counts.get(y, 0) for y in EXPECT_COUNTS)
    if total19 != 19:
        problems.append(f'FY28-FY33 holds {total19} projects, not 19')
    sums = {}
    for r in narr:
        if r['amount']:
            sums[r['section']] = sums.get(r['section'], Decimal(0)) + Decimal(r['amount'])
    for y, v in printed.items():
        if y == 'FY28-FY33':
            got = sum(sums.get(k, Decimal(0)) for k in EXPECT_COUNTS)
        else:
            got = sums.get(y, Decimal(0))
        if got != v:
            problems.append(f'{y}: the rows sum to {got}, the narrative prints {v}')
    for y in ('FY28', 'FY29', 'FY30', 'FY32', 'FY33', 'FY36', 'smaller', 'FY28-FY33'):
        if y not in printed:
            problems.append(f'the narrative\'s printed total for {y} was not found')
    mapped = {(r.get('narrative_section'), r.get('narrative_project')) for r in forms}
    for r in narr:
        k = (r['section'], r['project'])
        if r['section'] in ('FY27',) or k in mapped or k in NO_FORM:
            continue
        problems.append(f'narrative line with no form and no reason: {k}')
    return problems, counts, total19


def render(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n', extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    forms, narr, printed = build()
    problems, counts, n19 = prove(forms, narr, printed)
    if problems:
        sys.exit('\n'.join(problems))
    outs = {OUT_FORMS: render(forms, FORM_FIELDS), OUT_NARR: render(narr, NARR_FIELDS)}
    if a.check:
        stale = [p for p, s in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != s]
        if stale:
            sys.exit('STALE: ' + ', '.join(os.path.relpath(p, ROOT) for p in stale))
    else:
        for p, s in outs.items():
            with open(p + '.tmp', 'w', encoding='utf-8', newline='') as fh:
                fh.write(s)
            os.replace(p + '.tmp', p)
    differs = sum(1 for r in forms if r['differs'])
    print(f'ok: {len(forms)} forms, {len(narr)} narrative lines; FY28-FY33 {n19} projects '
          f'({", ".join(f"{y} {counts[y]}" for y in EXPECT_COUNTS)}); every printed total '
          f'ties ({len(printed)}); {differs} forms differ from the narrative')


if __name__ == '__main__':
    main()
