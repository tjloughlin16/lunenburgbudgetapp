#!/usr/bin/env python3
"""Special revenue funds, every year the annual town report prints them.

The archive holds the town's special revenue funds for **FY2026 only** -- one snapshot of
`fund_activity`. The annual reports carry the same schedule back to FY2011, which is the
difference between knowing a fund's balance and knowing whether that balance is normal.

This is the load-bearing one for the school work. Every school fund outside the general
appropriation is here by name -- Title I, PL 94-142, Chapter 658 athletics, After School,
School Facilities Use, Non-Resident Tuition, Adult Education, School Lunch -- and rule 11's
whole problem is that a budget line rising because a grant ended looks identical to one
rising because the district grew. A fifteen-year series of the grants themselves is the
closest published thing to telling those apart.

## Each year prints its own columns, and they are kept as printed

FY2012 gives forward balance, receipts, disbursements, closing balance. FY2020 gives
forward and total receipts. FY2025 gives fund balance, receipts through a date, and
remaining deficits. These are not the same table with the same columns, and forcing them
into one shape would invent figures for the years that do not print them.

So the column headings are captured **as that year prints them** and stored alongside the
values, in `columns_as_printed`. A consumer wanting a series across years has to decide
which columns correspond, and that decision is visible rather than baked in.

## Checks

Each page carries group subtotals and the schedule ends in a grand total. Where a total is
printed, the rows above it must sum to it; where none is printed the year is marked
`partial` and must never be aggregated with a reconciled one.

    python3 scripts/extract_special_revenue.py [--boxes <dir>]
"""

import argparse
import collections
import csv
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import pdf_tables as T
import report_pages as RP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The sixteen annual town reports moved out of town-budget/ on 5 September 2026.
# Every script here globs '*annual-town-report*.pdf' under this path, and a glob
# that matches nothing raises nothing -- so pointing at the folder they left made
# each of these a silent no-op rather than an error.
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
CATALOGUE = os.path.join(ROOT, 'sources', 'data', 'annual-report-catalogue.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'special-revenue-funds.csv')
PROV = os.path.join(ROOT, 'sources', 'data', 'PROVENANCE-special-revenue-funds.md')

# The department headings the schedule groups funds under. A row matching one of these is a
# heading, not a fund, and the figure beside it (where there is one) is a subtotal.
GROUPS = re.compile(
    r'^(GENERAL GOVERNMENT|SCHOOL DEPARTMENT|PUBLIC SAFETY|HIGHWAY|PARKS|LIBRARY|'
    r'HEALTH|COUNCIL ON AGING|CULTURE|RECREATION|CEMETERY|SEWER|WATER|VETERANS|'
    r'CONSERVATION|PLANNING|TOWN CLERK|FIRE|POLICE|DPW)\b', re.I)
# The grand total row, identified on the SQUASHED label so that a text layer splitting
# words apart (`GRAND T OT AL`) does not defeat it.
#
# Deliberately NOT a general /TOTAL/ match: the column header of this very schedule reads
# `FORWARD  TOTAL  TOTAL  BALANCE FWD`, so a loose match takes the headings as a totals row
# and reconciles the table against its own column names.
def is_grand_total(label):
    return squash(label).startswith('GRANDTOTAL')


def is_subtotal(label):
    """A department subtotal row.

    Matched on the squashed label so `T OT AL` counts, and anchored at the start so a fund
    actually named `... TOTAL ...` is not swallowed. These rows must be kept out of the
    column sums -- they are the sums.
    """
    sq = squash(label)
    return sq.startswith('TOTAL') and not sq.startswith('TOTALRECEIPTS')


def squash(s):
    """For comparison only -- never stored. The text layer splits words apart
    (`SUMMARY OF RECEIPT S`, `GRAND T OT AL`), so every comparison has to survive that."""
    return re.sub(r'[^A-Z0-9]', '', (s or '').upper())


def is_label(cell):
    """Is this cell the row's label?

    NOT `[A-Za-z]{3}` -- three consecutive letters. `PL 94-142 #240` has none, so that test
    dropped the federal special education grant out of every year of the special revenue
    schedule, silently and without shifting anything. Fund names in these tables are often
    mostly code: `Title I #305`, `PL 94-142 #240`, `FY22 Covid 19`, `25#305`.

    The real test is: it contains a letter, it is not itself a figure, and it is long
    enough not to be a stray mark.
    """
    t = (cell or '').strip()
    if len(t) < 2 or not re.search(r'[A-Za-z]', t):
        return False
    return T.amount(t) is None or bool(re.search(r'[A-Za-z]{2}', t))


def repair_dollar_as_five(vals, cells, idx):
    """`$` read as `5`, caught by comparing a row against itself.

    Vision reads the dollar sign as a `5` on some scans, and the result is a perfectly
    valid number ten times too large — `$1,770,967.83` becomes `51,770,967.83`. Nothing in
    the cell says it is wrong, and one such row put FY2020's appropriations $73.5M over its
    own printed total.

    What gives it away is the row: these schedules print the same figure in more than one
    column, so the correct reading is usually sitting beside the corrupt one.

        Transfer to Capital Project Fund   51.770,967.83   $1,770,967.83   51,770,967.8
        GRAND TOTAL                        S43,104,912.84  543,104,912.84  541,024,362.4

    So a value is repaired only when dropping its leading `5` makes it match another value
    in the same row. That is evidence from the document rather than a guess about the
    digit, and a row with no corroborating column is left alone.
    """
    out, repaired = list(vals), 0
    for i, v in enumerate(out):
        # No magnitude gate. An earlier version only looked at values over $1M and so
        # missed `$7,535.55` read as `57535.55` sitting beside two correct readings of the
        # same figure. The evidence is the sibling match, not the size.
        if v is None or v <= 0:
            continue
        raw = str(int(v)) if float(v).is_integer() else f'{v:.2f}'
        if not raw.startswith('5'):
            continue
        try:
            alt = float(f'{v:.2f}'.lstrip('5')) if f'{v:.2f}'.startswith('5') else None
        except ValueError:
            alt = None
        if alt is None:
            continue
        for j, w in enumerate(out):
            if j != i and w is not None and abs(w - alt) < 0.02:
                out[i] = alt
                repaired += 1
                break
    return out, repaired


def mark_arithmetic_subtotals(rows_in, tol=0.02):
    """Find subtotal rows by ARITHMETIC, not by their label.

    These schedules print a department's lines and then its total, and the total's label
    frequently does not survive extraction — it comes through blank, or as the department
    name alone. Counted as detail it is added to the very lines it summarises, so the table
    sums to far more than its own printed grand total: FY2011's appropriations came to
    $46,269,199.78 against a printed $27,948,061.40, with exactly one subtotal recognised
    among 173 rows.

    The reliable test is what the number IS. A row whose value equals the sum of the
    consecutive rows immediately above it is their total, whatever it is called:

        Payroll             10,241,099.90
        Other Expenses       4,111,404.61
        (no label)          14,352,504.51   <- the sum of the two above

    Only runs of two or more are considered, so a line that merely happens to repeat the
    value above it is not swallowed.
    """
    vals = []
    for r in rows_in:
        v = r.get('v1')
        vals.append(float(v) if v not in (None, '') else None)

    # Two passes, because the schedules nest. A department total sums its own lines; a
    # section total then sums the department totals. Once the inner ones are marked they
    # are no longer `row`, so the outer level has to be looked for among `subtotal` rows —
    # otherwise a section total stays classed as detail and is added to everything beneath
    # it a second time.
    # Looked for in BOTH directions.
    #
    # These schedules print a department total after its lines in some sections and before
    # them in others -- FY2019's `20,190,110.47` sits above the `13,947,152.00` and
    # `6,242,958.47` that make it up. Searching only upward left that one classed as detail
    # and put the year $24M over its own printed total.
    for level, want in enumerate(('row', 'subtotal')):
        for i, v in enumerate(vals):
            if v is None or rows_in[i]['kind'] != 'row':
                continue
            found = None
            for step, label in ((-1, 'above'), (1, 'below')):
                run, n, seen = 0.0, 0, 0
                j = i + step
                while 0 <= j < len(vals) and seen < 14:
                    if rows_in[j]['kind'] != want:
                        break
                    if vals[j] is None:
                        # A row with no figure does not end the group. FY2019 prints
                        # `Payo Department` with its value lost to OCR, sitting between
                        # the two lines whose sum is the total below them -- breaking
                        # there left a $20,190,110.47 subtotal classed as detail and the
                        # year $24M over its own printed total.
                        j += step
                        seen += 1
                        continue
                    run += vals[j]
                    n += 1
                    seen += 1
                    # A single line repeated with no label of its own is that line's
                    # total: these schedules print a one-line department as the line and
                    # then the department total, identical. Counting both doubles it.
                    enough = n >= 2 or (n == 1 and not rows_in[i]['label'].strip())
                    if enough and abs(run - v) <= tol:
                        found = (n, label)
                        break
                    j += step
                if found:
                    break
            if found:
                n, label = found
                rows_in[i]['kind'] = 'subtotal'
                rows_in[i]['row_check'] = (
                    f'subtotal: equals the {n} '
                    f'{"rows" if level == 0 else "subtotals"} {label} it')



def catalogue_pages(edition):
    """Where this year's schedule is, per the catalogue -- not by matching a heading.

    Two exclusions earn their place. The table of contents *lists* the schedule and would
    otherwise be taken as it (FY2015 p4-5). And the exclusion is matched against the
    table's name and printed heading only, never its description -- a description mentions
    half the book, and matching against it once disqualified FY2018's receipts page because
    the sentence describing it contained the word `assessments`.
    """
    pages = set()
    for r in csv.DictReader(open(CATALOGUE)):
        if r['edition'] != edition:
            continue
        ident = f"{r['name']} {r['printed_heading']}"
        if not re.search(r'special revenue', ident, re.I):
            continue
        if re.search(r'table of contents|balance sheet|montachusett|monty tech',
                     ident, re.I):
            continue
        for a, b in re.findall(r'(\d+)\s*[-–]\s*(\d+)', r['pages'] or ''):
            if int(b) >= int(a) and int(b) - int(a) < 20:
                pages.update(range(int(a), int(b) + 1))
        for n in re.findall(r'(?<![\d-])(\d{1,3})(?![\d-])', r['pages'] or ''):
            pages.add(int(n))
    return sorted(pages)


def header_of(lines):
    """The column headings this year prints, joined from the rows above the first fund.

    They are stored verbatim rather than mapped to a canonical set. FY2012 prints forward /
    receipts / disbursements / balance; FY2020 prints forward / total receipts; FY2025
    prints fund balance / receipts thru / remaining deficits. Mapping them onto one shape
    would invent a disbursements figure for the years that never printed one.
    """
    head = []
    for line in lines[:12]:
        if T.MONEY_TOKEN.search(line):
            break
        t = line.strip()
        if t and not re.match(r'^TOWN OF LUNENBURG$|^SPECIAL REVENUE', t, re.I):
            head.append(re.sub(r'\s{2,}', ' | ', t))
    return ' ; '.join(head[-4:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boxes', default=os.path.join(ROOT, 'sources', 'town-budget', 'ocr'))
    args = ap.parse_args()

    rows, ledger = [], []
    for edition in RP.editions():
        fy = int(re.search(r'(\d{4})', edition).group(1))
        want = catalogue_pages(edition)
        if not want:
            continue
        pages = RP.load(edition, ocr=True) or RP.load(edition)
        got = [p for p in want if p in pages]

        header, group, n_before = '', '', len(rows)
        grand_values = []
        for page in got:
            lines = [l for l in pages[page] if l.strip()]
            if not header:
                header = header_of(lines)
            ruler = T.column_ruler(T.figure_rows(lines))

            # Which cell indices are money columns on THIS page. A cell index counts if it
            # holds a figure in at least a fifth of the rows that carry any figure at all
            # -- high enough to exclude a label cell that happens to be numeric, low enough
            # to keep a column most funds leave blank (deficits, for instance).
            figure_lines = T.figure_rows(lines)
            hits = collections.Counter()
            for fl in figure_lines:
                for i, c in enumerate(T.cells(fl, ruler)):
                    if T.amount(c) is not None:
                        hits[i] += 1
            need = max(1, len(figure_lines) // 5)
            money_cols = sorted(i for i, n in hits.items() if n >= need)

            for line in lines:
                cells = T.cells(line, ruler)
                # A row the ruler could not cut cleanly is FLAGGED, not discarded.
                #
                # Skipping them threw away real data: `Teacher Quality #140` on FY2020
                # page 32 had the closing bracket of `($0.24)` fall across a gutter, so the
                # row was marked spanned and dropped -- with all four of its values parsed
                # correctly. The dataset's own reconciliation then came up short by exactly
                # that row's disbursements figure, $31,793.00.
                #
                # A dropped row shifts nothing and is invisible. A flagged row can be
                # looked at.
                spanned = '!' in cells
                cells = [c for c in cells if c != '!']
                label = next((c for c in cells if is_label(c)), '')
                # POSITION IS THE DATA, and it comes from the ruler.
                #
                # Two earlier versions got this wrong in the same way twice. The first
                # compacted the value list, dropping the Nones. The second "fixed" that by
                # trimming the LEADING Nones -- which does exactly the same damage to any
                # fund whose forward-balance cell is blank: its receipts figure slides into
                # the forward slot. Both produced sums 40-60% short of the printed totals,
                # consistently, in every year.
                #
                # A money column is a cell index that holds a figure in a good share of the
                # page's rows. That is computed once per page from the ruler and applied to
                # every row, so a blank stays a blank in its own column instead of pulling
                # the row left.
                values = [cols_[i] if i < len(cols_) else None
                          for i in money_cols] if (cols_ := [T.amount(c) for c in cells]) \
                    else []
                # `$` misread as `5`, caught where the row corroborates itself.
                values, _dollar = repair_dollar_as_five(values, cells, money_cols)
                if is_grand_total(label) and any(v is not None for v in values):
                    grand_values = values
                    continue
                if is_subtotal(label) and any(v is not None for v in values):
                    # A department subtotal. Recorded as a row so it is not silently
                    # dropped, but marked so it is never summed with the funds above it.
                    rows.append({'fy': fy, 'edition': edition, 'group': group,
                                 'fund': label.strip(), 'page': page, 'is_subtotal': 'yes',
                                 'columns_as_printed': header,
                                 **{f'v{i + 1}': ('' if v is None else f'{v:.2f}')
                                    for i, v in enumerate(values[:6])},
                                 'n_values': sum(1 for v in values if v is not None),
                                 'status': ''})
                    continue
                if not any(v is not None for v in values):
                    # A label with no figures beside it is a department heading, and it
                    # governs every fund below it until the next one. This assignment was
                    # lost in a rewrite and the `group` column came out empty for all
                    # 2,246 rows -- invisible in the CSV, because an empty column looks
                    # like a column that was never populated rather than one that stopped
                    # being populated.
                    if GROUPS.match(label.strip()):
                        group = label.strip()
                    continue
                rows.append({'fy': fy, 'edition': edition, 'group': group,
                             'fund': label.strip(), 'page': page,
                             'columns_as_printed': header, 'is_subtotal': '',
                             'ruler_spanned': 'yes' if spanned else '',
                             **{f'v{i + 1}': ('' if v is None else f'{v:.2f}')
                                for i, v in enumerate(values[:6])},
                             'n_values': sum(1 for v in values if v is not None),
                             'status': ''})
        # Subtotals whose label did not survive, found by arithmetic. A department total
        # counted as detail is added to the very lines it summarises.
        seg = rows[n_before:]
        for r in seg:
            r['kind'] = 'subtotal' if r.get('is_subtotal') == 'yes' else 'row'
        mark_arithmetic_subtotals(seg)
        for r in seg:
            if r['kind'] == 'subtotal':
                r['is_subtotal'] = 'yes'
        mine = [r for r in seg if r.get('is_subtotal') != 'yes']
        ledger.append({'fy': fy, 'edition': edition, 'pages': got, 'funds': len(mine),
                       'grand_values': grand_values, 'header': header})

    # EVERY ROW PROVES ITSELF, where the schedule prints four columns.
    #
    # The identity is the fund's own accounting: forward balance + receipts -
    # disbursements = balance carried forward. It holds on 52 of 53 complete FY2017 rows,
    # so it is the schedule's own arithmetic and not a pattern we imposed.
    #
    # That matters because it is a check the column totals cannot give: a grand total
    # proves the column adds up, while this proves each FUND adds up. A row can be wrong in
    # a way that leaves the column total intact -- two rows compensating -- and only the
    # row identity sees it.
    #
    # It also recovers a cell the OCR lost. Three FY2017 funds came through with no forward
    # balance, `PL 94-142 #240` among them; the other three columns fix it exactly. That is
    # DERIVED and is written to its own column, never into v1, so nothing downstream can
    # mistake an inference for a reading.
    for r in rows:
        vs = [r.get(f'v{i}') for i in (1, 2, 3, 4)]
        have = [i for i, v in enumerate(vs) if v not in (None, '')]
        if len(have) == 4:
            v = [float(x) for x in vs]
            r['row_check'] = ('fund balances: forward + receipts - disbursements = '
                              'carried forward'
                              if abs(v[0] + v[1] - v[2] - v[3]) < 0.02
                              else f'does NOT balance by {v[0] + v[1] - v[2] - v[3]:+,.2f}')
        elif len(have) == 3 and r.get('is_subtotal') != 'yes':
            v = {i: float(vs[i]) for i in have}
            missing = ({0, 1, 2, 3} - set(have)).pop()
            got = (v.get(3, 0) - v.get(1, 0) + v.get(2, 0) if missing == 0 else
                   v.get(3, 0) - v.get(0, 0) + v.get(2, 0) if missing == 1 else
                   v.get(0, 0) + v.get(1, 0) - v.get(3, 0) if missing == 2 else
                   v.get(0, 0) + v.get(1, 0) - v.get(2, 0))
            r['derived_cell'] = (f'v{missing + 1} = {got:,.2f}, from this fund\'s own '
                                 f'other three columns')
            r['row_check'] = 'one cell missing; derivable from the row itself'

    # Reconcile COLUMN BY COLUMN against the totals row.
    #
    # The schedule prints four money columns -- forward balance, receipts, disbursements,
    # closing balance -- and the GRAND TOTAL row gives a total for each of them. An earlier
    # version took the last value on that row as "the" total and compared it against the
    # sum of the FIRST column, which cannot tie and did not for a single year. A table with
    # per-column totals has to be checked per column.
    #
    # A year is reconciled when every column it prints a total for ties. Partial otherwise,
    # and the per-column result is recorded so a consumer can see WHICH column is
    # trustworthy rather than discarding the year whole.
    for led in ledger:
        mine = [r for r in rows if r['edition'] == led['edition']]
        led['checks'], led['ok'] = [], False
        if not led['grand_values'] or not mine:
            for r in mine:
                r['status'] = 'no check'
            continue
        ties = []
        for i, printed in enumerate(led['grand_values'], start=1):
            if printed is None:
                continue
            col = f'v{i}'
            got = round(sum(float(r[col]) for r in mine if r.get(col)), 2)
            ok = abs(got - printed) <= 0.02
            ties.append(ok)
            led['checks'].append(f'{col}: {got:,.2f} vs printed {printed:,.2f}'
                                 f'{"" if ok else f" ({got - printed:+,.2f})"}')
        led['ok'] = all(ties) and any(ties)
        for r in mine:
            # See extract_tables.py: `checked` / `check failed` / `no check`. A schedule
            # that prints no grand total is not doubtful data, it is data we must verify by
            # reading the page rather than by adding it up.
            r['status'] = ('checked' if led['ok']
                           else 'check failed' if led['grand_values'] else 'no check')
            r['columns_tying'] = sum(1 for t in ties if t)
            # The gap between what we summed and what the report prints, per column, on
            # every row. A reader can then see exactly how far off the year is rather than
            # being told only that it failed -- FY2015's forward balance is out by 0.5% and
            # its receipts column by 5.7%, and those are very different facts.
            r['reconciliation'] = ' ; '.join(led['checks'])

    fields = (['fy', 'edition', 'group', 'fund', 'page', 'is_subtotal',
               'columns_as_printed'] + [f'v{i}' for i in range(1, 7)]
              + ['n_values', 'ruler_spanned', 'row_check', 'derived_cell',
                 'columns_tying', 'status', 'reconciliation'])
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, '') for f in fields})

    print(f'{"FY":<9}{"pages":>6}{"funds":>7}{"cols":>6}  status / per-column check')
    for led in sorted(ledger, key=lambda l: l['fy']):
        print(f'FY{led["fy"]:<7}{len(led["pages"]):>6}{led["funds"]:>7}'
              f'{len(led["grand_values"]):>6}  '
              f'{"RECONCILED" if led["ok"] else "partial"}')
        for c in led['checks']:
            print(f'{"":>28}{c}')
        if not led['grand_values'] and led['funds']:
            print(f'{"":>28}no GRAND TOTAL row found on these pages')
    print(f'\n{len(rows)} fund-years, '
          f'{sum(1 for r in rows if r["status"] == "reconciled")} reconciled')
    print(f'wrote {os.path.relpath(OUT, ROOT)}')
    write_provenance(ledger, rows)
    print(f'wrote {os.path.relpath(PROV, ROOT)}')


def write_provenance(ledger, rows):
    L = ['# Special revenue funds — what was read, and why it does not yet reconcile', '',
         '**Generated by `scripts/extract_special_revenue.py`. Do not edit.**', '',
         '## Status: PARTIAL. Do not publish these figures as fact.', '',
         'Every fund-year below is real — read off the page, at its own position, with the',
         'column it was printed in. **None of it reconciles to the totals the reports',
         'print.** Residuals run from 0.2% to about 10% depending on the year and the',
         'column, and until that is closed these rows are a transcription, not a verified',
         'figure.', '',
         'They are kept because the alternative is worse: the archive holds special revenue',
         'for FY2026 only, and this is fifteen years of it. But rule 13 governs what may be',
         'quoted, and an unreconciled extract may not be.', '',
         '## Why it matters that this one gets finished', '',
         'Every school fund outside the general appropriation is here by name — Title I,',
         'PL 94-142, Chapter 658 athletics, After School, School Facilities Use,',
         'Non-Resident Tuition, Adult Education, School Lunch. Rule 11\'s central problem is',
         'that a budget line rising because a grant ended looks identical to one rising',
         'because the district grew, and a series of the grants themselves is the closest',
         'published thing to telling those apart.', '',
         '## Per year', '',
         '| FY | pages | funds | columns | reconciliation |', '|---|---|---:|---:|---|']
    for led in sorted(ledger, key=lambda l: (l['fy'], l['edition'])):
        checks = '<br>'.join(led['checks']) or 'no GRAND TOTAL row found'
        L.append(f"| {led['edition']} | {len(led['pages'])} | {led['funds']} | "
                 f"{len(led['grand_values'])} | {checks} |")
    L += ['', '## Where the residual comes from — what has been ruled out', '',
          'FY2020 is the closest year and the best worked example: 150 detail rows summing',
          'to $4,600,794.87 against a printed $4,576,323.49, over by $24,471.38 (0.5%).',
          '',
          'Ruled out by inspection:',
          '',
          '- **Duplicated rows.** No label appears twice on the five pages.',
          '- **Sign errors.** Six rows carry negative first-column values; all six are',
          '  parenthesised deficits on the page, so the sign is right. `MONEY_TOKEN` does',
          '  not capture the bracket, which makes them *look* wrong in a naive check.',
          '- **A single row equal to the overage.** None exists, so it is not one bad',
          '  figure.',
          '',
          '**The open lead: no subtotal rows are being detected at all.** `is_subtotal()`',
          'matches a label starting with `TOTAL`, and this schedule appears to print its',
          'department subtotals some other way — or to include, above the grand total, funds',
          'the grand total excludes. Either would produce exactly this signature: a small',
          'positive overage that grows with the number of departments on the page.',
          '',
          'Columns 2 and 3 are further out than 1 and 4 in almost every year, which points',
          'at the same place — the middle of the table rather than its ends.',
          '',
          '## What is known to be wrong', '',
          '- **FY2011 prints no GRAND TOTAL row** on these pages, so it cannot be checked',
          '  at all.',
          '- **FY2016 appears twice** — the main report and the addendum — with different',
          '  printed totals for the same year. The addendum is the uncut copy; the main',
          '  report\'s is clipped. They have not been reconciled against each other.',
          '- Columns 2 and 3 (receipts and disbursements) are further out than columns 1',
          '  and 4 (opening and closing balances) in almost every year, which points at row',
          '  loss or column splitting in the middle of the table rather than at the ends.',
          '',
          '## Each year prints its own columns', '',
          'FY2012 gives forward / receipts / disbursements / closing. FY2020 gives forward',
          'and total receipts. FY2025 gives fund balance / receipts through a date /',
          'remaining deficits. `columns_as_printed` records what that year actually printed;',
          'mapping them onto one canonical set would invent figures for the years that do',
          'not publish them.', '']
    with open(PROV, 'w') as fh:
        fh.write('\n'.join(L) + '\n')


def glob_pdfs():
    import glob
    return glob.glob(os.path.join(DOCS, '*annual-town-report*.pdf'))


if __name__ == '__main__':
    main()
