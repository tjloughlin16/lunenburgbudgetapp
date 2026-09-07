#!/usr/bin/env python3
"""Budgeted state aid, budget to budget, FY2005-FY2027 -- one stage, one definition.

    python3 scripts/build_state_aid_series.py           # write it
    python3 scripts/build_state_aid_series.py --check   # fail if it is stale

WHAT THIS IS FOR. `model/finance.py` grows total state aid at 2.0% a year and
`sources/analyses/show-your-work.md` grades that rate `BARE` -- no stated source and no
derivation. `scripts/build_state_aid.py` (the /state-aid page) publishes a measured
Chapter 70 RECEIPT rate of about 4.47% a year and is careful to say it is NOT a
correction to the assumption, because it is a different quantity (Chapter 70, not all
aid) measured at a different stage (actual, not budget) over a different span.

This generator closes that. It builds the series the comparison actually needs: the
TOWN'S OWN BUDGETED total cherry sheet aid, budget stage throughout, twenty-three
consecutive fiscal years, out of the town's own revenue/expenditure worksheets.

RULE 1 IS THE WHOLE POINT. Not one figure here is an actual. Every row is what the town
estimated it would receive when it built that year's budget. A rate computed across these
rows is a rate between two budgets, which is the only thing that may be compared with a
forward budget assumption.

RULE 13 -- WHAT IS QUOTED. Every figure is read from a named column of a named document:

  * FY2005-FY2019 come from ONE workbook, `a53-fy19-budget-handout-for-annual-town-
    meeting-xlsx.xlsx`, sheet `FY19 Rev Exp 4.25.18 Bond`, row 19 `Subtotal State Aid`.
    The column headings are asserted cell by cell before any figure is read out of them,
    because that sheet's headings sit on TWO rows (B2..F2 and E3..U3) and three of its
    twenty columns are not budgets at all: F = `FY07 PROJECTED`, G = `FY06 ACTUAL`, and
    O = a second `FY13 BUDGETED` marked `W/ OVERRIDE` in O4. Summing or stepping across
    those columns blind would mix an actual into a budget series -- rule 1's exact shape,
    hiding inside a spreadsheet's layout.
  * FY2019-FY2025 come from the `Subtotal State Aid` line of five later worksheets, each
    of which RESTATES the prior years. Those restatements are asserted to agree to the
    cent; a disagreement stops the build rather than being averaged away.
  * FY2025-FY2027 come from the FY2027 Town Meeting booklet's own cherry sheet block,
    which prints the components. They are asserted to sum to the `Total Receipts` line
    the booklet prints -- the source's own identity, recomputed.

RULE 13 -- THE DEFINITION MOVED, AND THE SOURCE PROVES IT. The FY2027 booklet's
`Total Receipts` includes `School Choice Receiving` tuition; every earlier worksheet's
`Subtotal State Aid` does not. The booklet prints both, so the bridge is not an
assumption: 10,776,998.00 - 94,912.00 = 10,682,086.00, and 10,682,086.00 is exactly what
the 2024 Annual Town Meeting booklet prints for the same year. That equality is asserted
here. The published series uses the OLDER, school-choice-excluding definition throughout
and states the school-choice column separately.

RULE 11. This is aid. It is what the town does NOT have to raise. A rate measured on it
is not a rate on any cost, and nothing here says what any of it paid for.

RULE 7. A growth rate is a measurement. Why aid grew -- and whether it will keep growing
-- is not. Chapter 70 is roughly four fifths of these totals and it is the output of a
statutory formula whose inputs (foundation enrolment, required local contribution, the
minimum-aid increment) move independently of anything measured here. See
`notes/findings/STATE-AID-RATE.md` for what this series does and does not license.

WHAT IT REFUSES TO WRITE ON:
  1. a workbook heading that is not the heading it expects, in the cell it expects;
  2. two documents restating the same fiscal year's budget with different figures;
  3. the booklet's cherry sheet components not summing to its own printed total;
  4. the school-choice bridge not tying to the cent;
  5. a hole in the fiscal year sequence;
  6. `model/finance.py`'s FY27 state aid base no longer being the Governor's figure this
     series ends on, plus the enacted increment `model/export.py` publishes.
"""
import argparse
import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))

OUT = os.path.join(ROOT, 'notes/findings/state-aid-budget-series.csv')
TEXT = 'sources/town-budget/text'
DOCS = 'sources/town-budget/docs'

XLSX = 'a53-fy19-budget-handout-for-annual-town-meeting-xlsx.xlsx'
SHEET = 'FY19 Rev Exp 4.25.18 Bond'
SUBTOTAL_ROW = 19          # A19 = 'Subtotal State Aid'
CHERRY_ROW = 16            # A16 = 'Cherry Sheet/State Aid'

# The workbook's headings, cell by cell, and the fiscal year each one carries. Three
# columns are deliberately absent from this map and MUST stay absent: F ('FY07
# PROJECTED'), G ('FY06 ACTUAL') and O (a duplicate 'FY13 BUDGETED' marked 'W/ OVERRIDE').
XLSX_COLUMNS = [
    ('D', 'D2', 'FY05 BUDGETED', 2005),
    ('E', 'E3', 'FY06 BUDGETED', 2006),
    ('H', 'H3', 'FY07 BUDGETED', 2007),
    ('I', 'I3', 'FY08 BUDGETED', 2008),
    ('J', 'J3', 'FY09 BUDGETED', 2009),
    ('K', 'K3', 'FY10 BUDGETED', 2010),
    ('L', 'L3', 'FY11 BUDGETED', 2011),
    ('M', 'M3', 'FY12 BUDGETED', 2012),
    ('N', 'N3', 'FY13 BUDGETED', 2013),
    ('P', 'P3', 'FY14 BUDGETED', 2014),
    ('Q', 'Q3', 'FY15 BUDGETED', 2015),
    ('R', 'R3', 'FY16 BUDGETED', 2016),
    ('S', 'S3', 'FY17 BUDGETED', 2017),
    ('T', 'T3', 'FY18 BUDGETED', 2018),
    ('U', 'U3', 'FY19 BUDGETED', 2019),
]
# The columns that must NOT be read, and why. Asserted so that a reader of this file
# cannot mistake their absence for an oversight, and so that a re-extraction that
# renamed them stops the build.
XLSX_EXCLUDED = [('F2', 'FY07 PROJECTED', 'a projection, not an adopted budget'),
                 ('G3', 'FY06 ACTUAL', 'an ACTUAL -- rule 1'),
                 ('O3', 'FY13 BUDGETED', 'a second FY13 column, marked W/ OVERRIDE in O4')]

# THE LATER WORKSHEETS. For each: the text extract, the printed column headings in order
# on the REVENUE panel, and the fiscal year + stage each column carries. `None` means the
# column is a within-year stage (target/preliminary/COVID) that this series does not use.
#
# Every one of these documents restates prior years. Those restatements are the check:
# five documents, eleven overlapping (year, stage) pairs, all asserted equal to the cent.
SHEETS = [
    ('a91-fy20-preliminary-budget-revenue-expense-sheet-pdf.txt',
     'REVENUES/EXPENDITURES FY2020 BUDGET WORKSHEET',
     [('FY18 RECAP ADJ.', 2018, 'recap'),
      ('FY19 FINAL BUDGET', 2019, 'final'),
      ('FY20 TM TARGET BUDGET', None, None),
      ('FY20 TM PRELIM. BUDGET', None, None)]),
    ('a79-fiscal-year-2021-revenue-expense-worksheet-may-7-2020-pdf.txt',
     'REVENUES/EXPENDITURES FY2021 BUDGET WORKSHEET',
     [('FY20 FINAL BUDGET', 2020, 'final'),
      ('FY21 TM REC. BUDGET', None, None),
      ('FY21 COVID-19 BUDGET', None, None)]),
    ('a72-fy23-preliminary-budget-revenue-expense-sheet-pdf.txt',
     'PROJECTED REVENUES/EXPENDITURES FY2023',
     [('FY21 FINAL BUDGET', 2021, 'final'),
      ('FY22 FINAL BUDGET', 2022, 'final'),
      ('FY23 TARGET BUDGET', None, None),
      ('FY23 TM PRELIM. BUDGET', None, None)]),
    ('a189-fy24-revenue-expense-worksheet-february-16-2023-pdf.txt',
     'PROJECTED REVENUES/EXPENDITURES FY2024',
     [('FY22 FINAL BUDGET', 2022, 'final'),
      ('FY23 FINAL BUDGET', 2023, 'final'),
      ('FY24 TM PRELIM. BUDGET', None, None)]),
    ('a138-fy25-town-manager-s-preliminary-budget-recommendation-pdf.txt',
     'PROJECTED REVENUES/EXPENDITURES FY2025',
     [('FY23 FINAL BUDGET', 2023, 'final'),
      ('FY24 FINAL BUDGET', 2024, 'final'),
      ('FY25 TARGET BUDGET', None, None),
      ('FY25 PRELIM. BUDGET', None, None)]),
    ('a157-2024-may-annual-town-meeting-booklet-pdf.txt',
     'PROJECTED REVENUES/EXPENDITURES FY2025',
     [('FY23 FINAL BUDGET', 2023, 'final'),
      ('FY24 FINAL BUDGET', 2024, 'final'),
      ('FY25 TM REC. BUDGET', 2025, 'town meeting')]),
]

# THE FY2027 TOWN MEETING BOOKLET. Its cherry sheet block prints the components, and the
# components are what make the definitional bridge checkable rather than assumed.
BOOKLET = '3765-town-meeting-booklet-including-warrant.txt'
BOOKLET_HEADER = ('Tax Levy FY25 BUDGETED FY26 BUDGETED FY27 PROJECTED TIER 1 TIER 2 '
                  'Omnibus Budget FY25 BUDGETED FY26 BUDGETED FY27 BALANCED FY27 TIER 1 '
                  'FY27 TIER 2')
BOOKLET_YEARS = [2025, 2026, 2027]          # the first three printed columns
# line anchor -> printed label. The PDF's text layer breaks the leading capital of some
# rows onto its own line, which is why several anchors start mid-word. That is the
# instrument, and rule 13 says the instrument is part of the finding.
BOOKLET_ROWS = [('Education ', 'Education'),
                ('Unrestricted General Government Aid ', 'Unrestricted General Government Aid'),
                ('eterans Benefits ', 'Veterans Benefits'),
                ('Exemp: VBS and Elderly ', 'Exemp: VBS and Elderly'),
                ('tate Owned Land ', 'State Owned Land'),
                ('ibrary ', 'Library'),
                ('chool Choice Receiving ', 'School Choice Receiving')]
BOOKLET_TOTAL = 'otal Receipts '
# The one component the older `Subtotal State Aid` line does not contain.
NEW_IN_BOOKLET = 'School Choice Receiving'

FY27_ENACTED_INCREMENT = 471_121     # model/export.py: enactedStateAid

# EVERY RATE `notes/findings/STATE-AID-RATE.md` STATES, recomputed here and asserted to
# four decimal places. Rule 2 says never type a figure into prose, and a findings note is
# prose that ships to whoever reads this repository. The note quotes these and nothing
# else, so a figure that drifts stops `check_generated.py` rather than going on being
# published. Entries are (first fy, last fy, percent a year) for a compound rate, and
# ('median', n, percent) for the median of the last n annual steps ('median', 0, ...) for
# all of them.
RATE_CLAIMS = [
    (2005, 2027, 3.5724),
    (2005, 2019, 4.0100),
    (2013, 2023, 4.5660),
    (2017, 2027, 3.5405),
    (2019, 2027, 2.8112),
    (2019, 2026, 2.8330),
    (2022, 2026, 3.9773),
    (2023, 2026, 1.6677),
    (2023, 2027, 1.9144),
    (2025, 2027, 2.9771),
    ('median', 0, 2.7277),
    ('median', 10, 2.6218),
    ('median', 5, 2.7972),
]
RATE_TOLERANCE = 0.0002              # percentage points
CENT = 0.005

HEADER = ['fy', 'amount', 'stage', 'definition', 'document', 'reference', 'restated_by']


def fail(msg):
    sys.exit(f'build_state_aid_series: {msg}')


def money(s):
    """Every currency figure on a fragment of a line, in printed order."""
    return [float(x.replace(',', ''))
            for x in re.findall(r'-?\d[\d,]*\.\d{2}|-?\d[\d,]{2,}', s)]


# ------------------------------------------------------------------ the workbook
def read_workbook():
    try:
        import openpyxl
    except ImportError:
        fail('openpyxl is needed to read the FY19 budget handout workbook')
    path = os.path.join(ROOT, DOCS, XLSX)
    if not os.path.exists(path):
        fail(f'{DOCS}/{XLSX} is not on disk. Run scripts/sync_archive.py --pull')
    wb = openpyxl.load_workbook(path, data_only=True)
    if SHEET not in wb.sheetnames:
        fail(f'{XLSX} has no sheet {SHEET!r} -- it has {wb.sheetnames}')
    ws = wb[SHEET]

    for row, want in ((SUBTOTAL_ROW, 'Subtotal State Aid'),
                      (CHERRY_ROW, 'Cherry Sheet/State Aid')):
        got = (ws.cell(row, 1).value or '').strip()
        if got != want:
            fail(f'{XLSX}!A{row} reads {got!r}, expected {want!r}')

    for cell, want, why in XLSX_EXCLUDED:
        got = ws[cell].value
        if (got or '').strip() != want:
            fail(f'{XLSX}!{cell} reads {got!r}, expected {want!r} ({why})')

    out = []
    for col, cell, want, fy in XLSX_COLUMNS:
        got = ws[cell].value
        if (got or '').strip() != want:
            fail(f'{XLSX}!{cell} reads {got!r}, expected {want!r}')
        v = ws[f'{col}{SUBTOTAL_ROW}'].value
        if not isinstance(v, (int, float)):
            fail(f'{XLSX}!{col}{SUBTOTAL_ROW} holds {v!r}, not a figure')
        out.append(dict(fy=fy, amount=float(v), stage='town manager recommended',
                        definition='Subtotal State Aid',
                        document=f'{DOCS}/{XLSX}',
                        reference=f'{SHEET}!{col}{SUBTOTAL_ROW} (heading {cell} = '
                                  f'{want!r}; A{SUBTOTAL_ROW} = "Subtotal State Aid")'))
    return out


# ------------------------------------------------------------------ the worksheets
def read_sheets():
    """Every (fy, stage) a later worksheet states, with the document that stated it."""
    seen = {}
    for name, title, columns in SHEETS:
        path = os.path.join(ROOT, TEXT, name)
        if not os.path.exists(path):
            fail(f'{TEXT}/{name} is missing')
        txt = open(path, encoding='utf-8').read()
        if title not in ' '.join(txt.split()):
            fail(f'{name} no longer carries the title {title!r}')
        line = next((l for l in txt.split('\n')
                     if l.startswith('Subtotal State Aid')), None)
        if line is None:
            fail(f'{name} has no "Subtotal State Aid" line')
        # The revenue panel is everything left of the expenditure panel's own row label.
        left = line.split('Omnibus Total')[0]
        figures = money(left)
        if len(figures) != len(columns):
            fail(f'{name}: "Subtotal State Aid" prints {len(figures)} figures, '
                 f'{len(columns)} columns are described')
        for (heading, fy, stage), amount in zip(columns, figures):
            if fy is None:
                continue
            key = (fy, stage)
            seen.setdefault(key, []).append(
                dict(amount=amount, document=f'{TEXT}/{name}',
                     reference=f'line "Subtotal State Aid", column {heading!r}'))
    rows = []
    for (fy, stage), hits in sorted(seen.items()):
        amounts = {round(h['amount'], 2) for h in hits}
        if len(amounts) > 1:
            fail(f'FY{fy} {stage}: documents disagree -- '
                 + '; '.join(f'{h["document"]} says {h["amount"]:,.2f}' for h in hits))
        rows.append(dict(fy=fy, amount=hits[0]['amount'], stage=stage,
                         definition='Subtotal State Aid',
                         document=hits[0]['document'],
                         reference=hits[0]['reference'],
                         restated_by='; '.join(
                             os.path.basename(h['document']) for h in hits[1:])))
    return rows


# ------------------------------------------------------------------ the booklet
def read_booklet():
    path = os.path.join(ROOT, TEXT, BOOKLET)
    if not os.path.exists(path):
        fail(f'{TEXT}/{BOOKLET} is missing')
    # split('\n'), NOT splitlines(): these extracts carry form feeds, and
    # splitlines() breaks on those too, so its line numbers do not match what
    # grep or an editor shows a reader. A citation nobody can follow is not one.
    lines = open(path, encoding='utf-8').read().split('\n')
    if not any(l.strip() == BOOKLET_HEADER for l in lines):
        fail(f'{BOOKLET} no longer carries the cherry sheet column heading row')

    comps = {}
    for anchor, label in BOOKLET_ROWS:
        hit = [(i, l) for i, l in enumerate(lines, 1) if l.startswith(anchor)]
        if len(hit) != 1:
            fail(f'{BOOKLET}: {label!r} matches {len(hit)} lines, expected 1')
        n, line = hit[0]
        figures = money(line)[:len(BOOKLET_YEARS)]
        if len(figures) != len(BOOKLET_YEARS):
            fail(f'{BOOKLET} line {n}: {label!r} prints {len(figures)} figures')
        comps[label] = dict(zip(BOOKLET_YEARS, figures), line=n)

    hit = [(i, l) for i, l in enumerate(lines, 1) if l.startswith(BOOKLET_TOTAL)]
    if len(hit) != 1:
        fail(f'{BOOKLET}: the cherry sheet "Total Receipts" line matches {len(hit)} lines')
    total_line, line = hit[0]
    totals = dict(zip(BOOKLET_YEARS, money(line)[:len(BOOKLET_YEARS)]))

    rows = []
    for fy in BOOKLET_YEARS:
        parts = sum(comps[label][fy] for _, label in BOOKLET_ROWS)
        if abs(parts - totals[fy]) > CENT:
            fail(f'{BOOKLET}: FY{fy} components sum to {parts:,.2f}, the booklet prints '
                 f'{totals[fy]:,.2f} on line {total_line}')
        older = totals[fy] - comps[NEW_IN_BOOKLET][fy]
        rows.append(dict(fy=fy, amount=older, stage='town meeting',
                         definition='Subtotal State Aid',
                         document=f'{TEXT}/{BOOKLET}',
                         reference=f'line {total_line} "Total Receipts", column '
                                   f'"FY{fy % 100:02d} BUDGETED/PROJECTED", less line '
                                   f'{comps[NEW_IN_BOOKLET]["line"]} '
                                   f'"{NEW_IN_BOOKLET}"'))
    return rows, comps, totals


# ------------------------------------------------------------------ assembly
def build():
    workbook = read_workbook()
    sheets = read_sheets()
    booklet, comps, totals = read_booklet()

    # THE BRIDGE. The booklet's FY2025 total less its school choice line must equal what
    # the 2024 Annual Town Meeting booklet printed as FY2025 on the OLD definition. That
    # equality is what licenses one series across a definitional change.
    bridge_fy = 2025
    old = next((r['amount'] for r in sheets if r['fy'] == bridge_fy), None)
    new = next(r['amount'] for r in booklet if r['fy'] == bridge_fy)
    if old is None:
        fail(f'no worksheet states FY{bridge_fy} on the old definition -- the bridge '
             'cannot be checked, so the series cannot be published')
    if abs(old - new) > CENT:
        fail(f'the definitional bridge does not tie: the FY{bridge_fy} worksheets print '
             f'{old:,.2f}; the booklet prints {totals[bridge_fy]:,.2f} less '
             f'{comps[NEW_IN_BOOKLET][bridge_fy]:,.2f} of school choice = {new:,.2f}')

    # One row per fiscal year. Where two stages exist for a year, the LATER stage wins,
    # because that is the budget the town actually ran the year on -- and the stage is
    # named in the row, so nothing is hidden by the choice.
    order = {'town manager recommended': 0, 'recap': 1, 'final': 2, 'town meeting': 3}
    best = {}
    for r in workbook + sheets + booklet:
        r.setdefault('restated_by', '')
        cur = best.get(r['fy'])
        if cur is None or order[r['stage']] >= order[cur['stage']]:
            best[r['fy']] = r
    rows = [best[fy] for fy in sorted(best)]

    years = [r['fy'] for r in rows]
    if years != list(range(years[0], years[-1] + 1)):
        missing = sorted(set(range(years[0], years[-1] + 1)) - set(years))
        fail(f'the series has holes: FY{missing}')
    if len(years) < 20:
        fail(f'only {len(years)} years -- this series is meant to be the long one')

    # The model's base must be the figure this series ends on.
    import finance
    gov = totals[2027]
    if abs(finance.FY27['state_aid'] - (gov + FY27_ENACTED_INCREMENT)) > CENT:
        fail(f"model/finance.py FY27['state_aid'] is "
             f"{finance.FY27['state_aid']:,.2f}; the FY2027 Town Meeting booklet's "
             f"cherry sheet Total Receipts is {gov:,.2f} and the enacted increment is "
             f"{FY27_ENACTED_INCREMENT:,.2f}")
    check_rate_claims(rows)
    return rows


def check_rate_claims(rows):
    """Every rate the findings note states, recomputed from the series it cites."""
    s = {r['fy']: r['amount'] for r in rows}
    ys = sorted(s)
    steps = [(s[ys[i + 1]] / s[ys[i]] - 1) * 100 for i in range(len(ys) - 1)]
    for a, b, want in RATE_CLAIMS:
        if a == 'median':
            xs = steps if not b else steps[-b:]
            got = median(xs)
            what = f'median annual step, {"all " + str(len(xs)) if not b else "last " + str(b)}'
        else:
            if a not in s or b not in s:
                fail(f'the note quotes FY{a}->FY{b}, which this series does not cover')
            got = ((s[b] / s[a]) ** (1 / (b - a)) - 1) * 100
            what = f'FY{a}->FY{b}'
        if abs(got - want) > RATE_TOLERANCE:
            fail(f'notes/findings/STATE-AID-RATE.md states {what} = {want:.4f}%; the '
                 f'series now gives {got:.4f}%. Update the note and RATE_CLAIMS together.')


def render(rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(HEADER)
    for r in rows:
        w.writerow([r['fy'], f'{r["amount"]:.2f}', r['stage'], r['definition'],
                    r['document'], r['reference'], r.get('restated_by', '')])
    return buf.getvalue()


def rates(rows):
    s = {r['fy']: r['amount'] for r in rows}
    ys = sorted(s)
    out = []
    for a, b in [(ys[0], ys[-1]), (2013, 2023), (2017, 2027), (2019, 2027),
                 (2023, 2027)]:
        if a in s and b in s:
            out.append((a, b, (s[b] / s[a]) ** (1 / (b - a)) - 1))
    annual = [s[y] / s[y - 1] - 1 for y in ys[1:]]
    annual10 = [s[y] / s[y - 1] - 1 for y in ys[-10:]]
    return out, annual, annual10


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    rows = build()
    text = render(rows)

    if args.check:
        if not os.path.exists(OUT):
            fail(f'{os.path.relpath(OUT, ROOT)} does not exist. Run this without --check')
        if open(OUT, encoding='utf-8').read() != text:
            fail(f'{os.path.relpath(OUT, ROOT)} is stale. Run '
                 'python3 scripts/build_state_aid_series.py')
        print(f'ok — {os.path.relpath(OUT, ROOT)} reproduces from the town\'s own '
              f'worksheets: {len(rows)} consecutive budget years, '
              f'FY{rows[0]["fy"]}–FY{rows[-1]["fy"]}')
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(text)
    spans, annual, annual10 = rates(rows)
    med = median(annual)
    med10 = median(annual10)
    print(f'wrote {os.path.relpath(OUT, ROOT)} — {len(rows)} budget years, '
          f'FY{rows[0]["fy"]}–FY{rows[-1]["fy"]}')
    for a, b, r in spans:
        print(f'  FY{a}→FY{b} ({b - a}y): {r * 100:6.2f}% a year')
    print(f'  median annual, all {len(annual)} steps: {med * 100:.2f}%')
    print(f'  median annual, last 10 steps:          {med10 * 100:.2f}%')


if __name__ == '__main__':
    main()
