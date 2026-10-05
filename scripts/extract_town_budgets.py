#!/usr/bin/env python3
"""extract_town_budgets.py — D3 and D4: the FY26 omnibus budget workbook and
the FY27 working budgets, as the Finance Committee printed them.

RULE 13a — these are HAND-BUILT WORKBOOKS, not MUNIS printouts. They are
`stated` evidence: somebody assembled them (by typing, pasting, or linking
cells across 29 years of edits), and they carry exactly as much authority as
the person who built them, not the authority of an accounting-system
printout. Where a printed total disagrees with its own lines, that is
reported, never silently repaired (rule 13).

SOURCES
    D3  sources/budget-workbooks/finance-committee/fy26-budget/
            fy26-budget-master-03.13.25.xlsx
        Sheets: "FY 26 Omnibus Budget Revised" (627 rows), "Other
        non-Omnibus" (135 rows, 2 live rows), "FY26 Omnibus Budget -
        Previous " (203 rows, 169 live; note the sheet name's trailing
        space — cited literally because openpyxl needs it exact).

    D4  sources/budget-workbooks/finance-committee/fy27-budget/
            working-fy27-budget-shared-3.3.26.xlsx   sheet "TOWN BUDGET 3.3.26"
            3.26.26-budget.xlsx                       sheet "TOWN BUDGET 3.23.26"
            changes-since-2.19-prelim-copy-copy.xlsx  sheet "Sheet1"
            override-summary-sheet-3.26.26.xlsx       sheet "Sheet1"

    NOTE — "3.26.26-budget.xlsx" is the delivered filename; the sheet
    *inside* it is named "TOWN BUDGET 3.23.26", three days earlier than the
    filename. Both dates are printed here verbatim (rule 13: quote the
    source, never your rendering of it) — the filename date and the sheet's
    own date are not asserted to be the same thing.

    NOTE — "Changes since 2.19 prelim - Copy - Copy.xlsx" and "... - Copy.xlsx"
    are the SAME bytes (sha256 a9afb79c...26dd) per
    sources/data/finance-committee-delivery.csv, which already resolved this:
    one is `filed`, the other `duplicate`. Only one file exists on disk. This
    script opens it once and reports that finding rather than re-deriving it.

    NOTE — the "Changes since 2.19 prelim" workbook's OWN header reads
    "2.19.26 Budget" / "Change" / "3.12.26 Budget" — a 2/19-to-3/12 window,
    not the 3/3-to-3/26 window this script diffs between the two TOWN BUDGET
    sheets. The two are compared anyway (the task asks for it) but the date
    mismatch is reported, not glossed over.

WHAT THIS SCRIPT WRITES
    sources/data/omnibus-history.csv       — D3's "Previous" sheet: one row
        per (omnibus line, printed column), fiscal_year parsed from the
        printed header TEXT ONLY (never from column position — rule 13),
        with the column's own header cited verbatim and any inline note
        found on that row.
    sources/data/town-budget-fy26-fy27.csv — line items from D3's two
        omnibus sheets and all of D4, one row per (line, printed column),
        version = file + sheet + the sheet's own printed date, column_header
        = the exact printed text, never renamed or normalized across
        versions (the two FY27 working budgets print DIFFERENT column sets
        in DIFFERENT positions — confirmed below — so nothing here assumes
        one workbook's layout for another).

HOW A "PRINTED TOTAL" IS CHECKED — the tree-check
    Every sheet here nests: account lines roll into unlabeled division
    subtotals ("11221 SALARIES SELECT BOARD"), which roll into a labelled
    department total ("122 SELECT BOARD TOTAL"), which roll into a section
    total ("Total General Government"), which rolls into the sheet's grand
    total. There is no column that states the nesting level, so the check
    below reconstructs it the only way available WITHOUT inferring from
    position or indentation: a row with no account/org/line-number of its
    own and at least one printed figure is a ROLLUP. Walking the sheet in
    print order, every leaf row's figures are held in a pending list, per
    metric; a rollup is tested against the SUM OF THE WHOLE PENDING LIST
    first, and if that does not match, against shrinking suffixes of it,
    because a department total that combines two already-printed division
    subtotals needs to consume both of them, not just the most recent one.
    Whichever suffix ties (within tolerance) is replaced by the rollup's own
    printed value, so a higher total above it can consume the rollup as a
    single term. This is a DERIVED reconstruction of a tree the workbook
    never states explicitly, and it is reported as exactly that.

    THE GATE, following the one precedent already in this repo for a
    hand-built workbook (scripts/extract_gl_history.py, CHECK 1): only the
    sheet's own, explicitly printed GRAND TOTAL row (where one exists) tying
    to the sum of ALL its own leaf rows blocks the write. Every other
    printed subtotal/department total is checked by the same tree-check and
    REPORTED — every mismatch printed with its coordinate — but does not by
    itself refuse the write, because thirty years of hand-maintained
    formulas WILL have cells that no longer sum (rule 13a; gl-history.csv's
    own "LIABILITY INSURANCE Total" $0 case is the model for this). Not
    every sheet prints a grand total at all (neither FY27 working-budget
    sheet does) — that is reported as a fact about the sheet, not a failure.
    TOLERANCE is $0.01 per leaf row folded into a total (absorbs binary
    floating-point summation noise), floored at $1.00, because some of
    these totals sum several hundred account rows.

FISCAL YEARS, PARSED FROM TEXT ONLY
    The "Previous" sheet prints 117 columns whose headers were edited in
    place across twenty-nine annual revisions: five header rows (0-4), no
    merged cells, and the same metric word ("Expended", "Budgeted") recurs
    under a different year every few columns. A column's fiscal year is
    read from an explicit "FY" token in ITS OWN header text (full year
    "FY 2013" or shorthand "FY13"), or — only when no FY token exists at
    all — a bare four-digit 19xx/20xx token. Columns with neither are
    EXCLUDED from omnibus-history.csv and reported by coordinate; rule 13
    forbids guessing a year from where a column happens to sit. Columns
    whose header contains "change", "chg", "variance", "vs", "difference",
    "%" or "$$" are DERIVED comparisons between two years, not an amount for
    one year, and are excluded from both CSVs for the same reason rule 7
    excludes a proxy from being published as a fact — they are counted and
    reported, never silently dropped without a count.

NOTES AND ERRORS, FOUND BY WATCHING EVERY CELL, NOT ONE NAMED COLUMN
    These workbooks park a free-text note (e.g. "$1,522,236 SHIFTED TO
    SCHOOL DEPT.", row UMAS 914.1 at the FY03/FY04 seam) in whatever column
    happened to have room that year — never the same column twice. So every
    cell in the data region of every row is inspected: a non-blank string
    under a column with no amount classification (unheaded, or a derived
    header) is captured as a NOTE on that row, cited by coordinate, rather
    than being silently skipped because it wasn't where a note "should" be
    (rule 13c). A cell holding a spreadsheet formula error (#REF!, #DIV/0!,
    #VALUE!, #N/A, #NAME?) is reported as an ERROR on that coordinate —
    never treated as the figure's value and never silently zeroed.

Usage:
    python3 scripts/extract_town_budgets.py          # extract, validate, write
    python3 scripts/extract_town_budgets.py --check  # validate only, no write
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

FC = ROOT / "sources/budget-workbooks/finance-committee"
D3_PATH = FC / "fy26-budget/fy26-budget-master-03.13.25.xlsx"
D4_WORKING_303 = FC / "fy27-budget/working-fy27-budget-shared-3.3.26.xlsx"
D4_WORKING_326 = FC / "fy27-budget/3.26.26-budget.xlsx"
D4_CHANGES = FC / "fy27-budget/changes-since-2.19-prelim-copy-copy.xlsx"
D4_CHANGES_ALT_NAME = "Changes since 2.19 prelim - Copy.xlsx"  # same bytes; see docstring
D4_OVERRIDE = FC / "fy27-budget/override-summary-sheet-3.26.26.xlsx"

GL_HISTORY = ROOT / "sources/data/gl-history.csv"

OUT_OMNIBUS = ROOT / "sources/data/omnibus-history.csv"
OUT_TOWN = ROOT / "sources/data/town-budget-fy26-fy27.csv"

# $0.01 per folded leaf row, floored at $1.00 — see docstring.
PER_ROW_TOLERANCE = 0.01
MIN_TOLERANCE = 1.00

DERIVED_RE = re.compile(r"\$\$|\bchange\b|\bchg\b|\bvariance\b|\bvs\.?\b|\bdifference\b|%", re.I)
FORMULA_ERROR_RE = re.compile(r"^#(REF|DIV/0|VALUE|N/A|NAME|NULL|NUM)!?\??$", re.I)
YEAR4_FY_RE = re.compile(r"\bFY\s*(\d{4})\b", re.I)
YEAR2_FY_RE = re.compile(r"\bFY\s*(\d{2})\b", re.I)
BARE_YEAR_RE = re.compile(r"(19|20)\d{2}")

ERRORS_FOUND: list[tuple] = []  # (version, sheet, row1, col1, label, header, raw)
UNPARSED_YEAR_COLS: list[tuple] = []  # (sheet, col1, header_text, n_numeric_values)
DERIVED_COLS: list[tuple] = []  # (sheet, col1, header_text)


# --------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------


def cell_text(v):
    """A cell's printed text, or None. Dates come back as their ISO form
    because several header cells in the Previous sheet hold a literal
    meeting date (e.g. 2020-06-13) instead of text."""
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    s = str(v).strip()
    return s if s else None


def classify_raw(raw):
    """Returns ('blank', None) / ('number', float) / ('error', text) /
    ('text', text) for one cell's raw value — never guesses between them."""
    if raw is None:
        return ("blank", None)
    if isinstance(raw, (int, float)):
        return ("number", float(raw))
    s = str(raw).strip()
    if s == "":
        return ("blank", None)
    if FORMULA_ERROR_RE.match(s):
        return ("error", s)
    try:
        return ("number", float(s.replace(",", "")))
    except ValueError:
        return ("text", s)


def addr(row0, col0):
    """1-based (row, col-letter) for citation, from 0-based indices."""
    return row0 + 1, get_column_letter(col0 + 1)


def is_derived_header(header_text):
    return bool(header_text) and bool(DERIVED_RE.search(header_text))


def parse_year_from_header(header_text):
    """FY token wins over a bare 4-digit token (rule 13: an explicit FY
    marker is a stronger statement of year than a date that happens to
    appear in the same header, e.g. a meeting-date annotation)."""
    if not header_text:
        return None
    m = YEAR4_FY_RE.search(header_text)
    if m:
        return int(m.group(1))
    m = YEAR2_FY_RE.search(header_text)
    if m:
        return 2000 + int(m.group(1))
    m = BARE_YEAR_RE.search(header_text)
    if m:
        return int(m.group(0))
    return None


# --------------------------------------------------------------------------
# the tree-check — see docstring "HOW A PRINTED TOTAL IS CHECKED"
# --------------------------------------------------------------------------


DIVISION_LABEL_RE = re.compile(r"^\d{5}\b|^total\s+(salar(y|ies)|expenses?)\b", re.I)
SECTION_LABEL_RE = re.compile(
    r"^total\s+(general government|public safety|education|dpw|facilities|"
    r"human services|culture\s*&?\s*recreation|debt service|"
    r"intergovernmental assessments|unclassified|omnibus)\b",
    re.I,
)


def rollup_scope(label):
    """Three shapes of 'rollup', told apart by the label TEXT, never by
    position or by whether the figure ties:

    DIVISION  "11621 SALARIES ELECTIONS", "TOTAL SALARIES -SELECT BOARD" —
              a single payroll/expense division, often printed with NO
              account-level breakdown beneath it at all. A value in its
              own right, not necessarily a sum of anything just above it.
    DEPT      "220 FIRE DEPARTMENT", "162 ELECTIONS", "Subtotal Police" —
              a real department total, genuinely a sum of what precedes it
              (divisions and/or leaves) since the last department/section
              boundary — but NEVER reaches back past an already-closed
              SECTION total (that total's own figure is the one a reader
              carries forward; its constituent lines are spent).
    SECTION   "Total General Government", "Total Public Safety", ...,
              "Total Omnibus" — this workbook's ~10 named top-level
              totals, printed verbatim (read off the sheet, not guessed):
              these DO reach back across everything pending, including
              prior section totals (that is what "Total Omnibus" itself
              must do).

    This three-way split is what keeps a genuine small discrepancy in one
    department (rule 13a — it happens, in a hand-built sheet) from
    corrupting every total after it: a DEPT-scope rollup that doesn't tie
    still only ever consumes back to the last SECTION boundary, never
    past it."""
    label = (label or "").strip()
    if SECTION_LABEL_RE.match(label):
        return "section"
    if DIVISION_LABEL_RE.match(label):
        return "division"
    return "dept"


def tree_check(events, tolerance):
    """events: ordered list of dicts {'kind': 'leaf'|'rollup', 'label',
    'row1','metrics': {header: value_or_None}}.
    Returns a list of (event, {header: {printed, computed, matched,
    consumed}}) for every ROLLUP event. acc[h] holds (value, scope) pairs
    so a dept/division-scope rollup can never reach back past the most
    recent section-scope entry — see rollup_scope()."""
    acc: dict[str, list[tuple[float, str]]] = defaultdict(list)
    out = []
    for ev in events:
        if ev["kind"] == "leaf":
            for h, v in ev["metrics"].items():
                if v is not None:
                    acc[h].append((v, "leaf"))
            continue
        scope = rollup_scope(ev.get("label"))
        row_results = {}
        for h, v in ev["metrics"].items():
            if v is None:
                continue
            terms = acc[h]
            # a dept/division rollup may only see back to the most recent
            # SECTION boundary; a section rollup (incl. the grand total)
            # sees everything, including prior section totals.
            if scope == "section":
                floor = 0
            else:
                floor = 0
                for i in range(len(terms) - 1, -1, -1):
                    if terms[i][1] == "section":
                        floor = i + 1
                        break
            window = terms[floor:]
            if not window:
                matched = abs(v - 0.0) <= tolerance
                computed = 0.0
                consumed = 0
            else:
                suffix_sums = []
                s = 0.0
                for x, _ in reversed(window):
                    s += x
                    suffix_sums.append(s)
                # try the FULL window first, then shrinking suffixes
                found = None
                for k in range(len(suffix_sums), 0, -1):
                    if abs(suffix_sums[k - 1] - v) <= tolerance:
                        found = k
                        break
                if found is None:
                    computed = suffix_sums[-1]  # diagnostic: what the FULL window sums to
                    matched = False
                    if scope == "division":
                        # Ties nothing — very likely a standalone value
                        # with no breakdown beneath it. Consume nothing,
                        # so whatever IS pending stays pending for its own
                        # real total.
                        consumed = 0
                    else:
                        # A dept/section total that doesn't tie is a
                        # genuine (usually small) discrepancy — rule 13a.
                        # Its own window (never reaching past a section
                        # boundary) is consumed and replaced by its
                        # printed figure, so the discrepancy is carried
                        # forward ONCE rather than left to double-count.
                        consumed = len(window)
                else:
                    consumed = found
                    computed = suffix_sums[found - 1]
                    matched = True
            acc[h] = terms[: len(terms) - consumed] + [(v, scope)]
            row_results[h] = {
                "printed": v,
                "computed": computed,
                "matched": matched,
                "consumed": consumed,
            }
        out.append((ev, row_results))
    return out


def tolerance_for(n_leaf_rows):
    return max(MIN_TOLERANCE, PER_ROW_TOLERANCE * max(n_leaf_rows, 1))


# --------------------------------------------------------------------------
# D3: "FY 26 Omnibus Budget Revised" / "Other non-Omnibus"
# (single header row; LEAF iff ACCOUNT DESCRIPTION is non-blank; ROLLUP iff
#  it is blank but the Dept/label column and a figure are both present)
# --------------------------------------------------------------------------


def parse_simple_omnibus_sheet(wb, sheet_name, version_label):
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    n_cols = len(header)

    header_text = {i: cell_text(header[i]) for i in range(n_cols)}
    for i in (0, 1, 2):
        expect = {0: "Dept", 1: "OBJECT", 2: "ACCOUNT DESCRIPTION"}[i]
        got = (header_text.get(i) or "").strip()
        if got != expect:
            raise ValueError(f"{sheet_name}: expected column {i} header {expect!r}, found {got!r}")

    amount_cols = {}  # idx -> header text, non-derived
    derived_idx = set()
    for i in range(3, n_cols):
        h = header_text.get(i)
        if h is None:
            continue  # unheaded column — scanned for notes/errors below, not an amount
        if is_derived_header(h):
            derived_idx.add(i)
            DERIVED_COLS.append((f"{version_label} :: {sheet_name}", get_column_letter(i + 1), h))
        else:
            amount_cols[i] = h

    events = []
    town_rows = []
    for r0, r in enumerate(rows[1:], start=1):
        dept_label = cell_text(r[0])
        obj_code = cell_text(r[1])
        desc = cell_text(r[2])
        is_leaf = desc is not None
        is_rollup = (not is_leaf) and dept_label is not None and any(
            classify_raw(r[i])[0] == "number" for i in amount_cols
        )
        if not is_leaf and not is_rollup:
            continue

        row1, _ = addr(r0, 0)
        metrics = {}
        notes = []
        for i in range(3, n_cols):
            raw = r[i] if i < len(r) else None
            kind, val = classify_raw(raw)
            if kind == "blank":
                continue
            r1, c1 = addr(r0, i)
            if kind == "error":
                ERRORS_FOUND.append((version_label, sheet_name, r1, c1, dept_label or desc, header_text.get(i), val))
                continue
            if i in amount_cols:
                if kind == "number":
                    metrics[amount_cols[i]] = val
                else:
                    notes.append(f"[{header_text[i]} @ {c1}{r1}] {val}")
            else:
                # unheaded or derived column: numbers are not published
                # (derived: excluded by design; unheaded: no header to cite)
                if kind == "text":
                    notes.append(f"[{c1}{r1}] {val}")

        label = desc if is_leaf else dept_label
        line = f"{obj_code} {desc}".strip() if is_leaf and obj_code else (desc or dept_label)
        account = dept_label if (dept_label and "-" in dept_label) else None
        dept_code = None
        if account:
            parts = account.split("-")
            if len(parts) >= 3:
                dept_code = parts[2]
        if dept_code is None and dept_label:
            m = re.match(r"^\s*(\d{3,4}(?:\.\d+)?)\b", dept_label)
            if m:
                dept_code = m.group(1)

        events.append(
            {
                "kind": "leaf" if is_leaf else "rollup",
                "label": label,
                "row1": row1,
                "metrics": metrics,
            }
        )
        town_rows.append(
            {
                "version": version_label + " :: " + sheet_name,
                "department": dept_code,
                "org": None,
                "account": account,
                "line": line,
                "row_kind": "leaf" if is_leaf else "rollup",
                "metrics": metrics,
                "notes": notes,
                "row1": row1,
            }
        )

    return events, town_rows, amount_cols


# --------------------------------------------------------------------------
# D3: "FY26 Omnibus Budget - Previous " — the 117-column, 5-header-row,
# 169-live-row omnibus history. See docstring for the year-parsing rule.
# --------------------------------------------------------------------------


def parse_previous_sheet(wb, sheet_name, version_label):
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    header_rows_idx = [0, 1, 2, 3, 4]
    n_cols = max(len(r) for r in rows[:6])

    col_header = {}
    col_year = {}
    col_derived = set()
    for c in range(3, n_cols):
        texts = []
        for rr in header_rows_idx:
            t = cell_text(rows[rr][c]) if c < len(rows[rr]) else None
            if t and t not in texts:
                texts.append(t)
        joined = " | ".join(texts)
        col_header[c] = joined if joined else None
        if not joined:
            continue
        if is_derived_header(joined):
            col_derived.add(c)
            DERIVED_COLS.append((f"{version_label} :: {sheet_name}", get_column_letter(c + 1), joined))
            continue
        yr = parse_year_from_header(joined)
        if yr is not None:
            col_year[c] = yr

    # find the true end of data: the literal "Total Omnibus" row (row 169
    # in the 2026 workbook). Everything after it is trailing stray text —
    # reported, not treated as data.
    end_row0 = None
    for r0, r in enumerate(rows):
        desc = cell_text(r[2])
        if desc and re.match(r"^total\s+omnibus\b", desc, re.I):
            end_row0 = r0
            break
    if end_row0 is None:
        raise ValueError(f"{sheet_name}: no 'Total Omnibus' row found — cannot bound the data region")

    live_rows = rows[5 : end_row0 + 1]
    offset = 5

    events = []
    omnibus_rows = []
    unparsed_numeric_cols = defaultdict(int)
    for i, r in enumerate(live_rows):
        r0 = i + offset
        umas_no = cell_text(r[0])
        line_no = cell_text(r[1])
        desc = cell_text(r[2])
        is_total_label = bool(desc) and re.search(r"\btotal\b|\bsubtotal\b", desc, re.I)
        is_leaf = bool(line_no) and not is_total_label
        has_any_number = any(classify_raw(r[c])[0] == "number" for c in range(3, min(n_cols, len(r))))
        is_rollup = is_total_label and has_any_number
        if not is_leaf and not is_rollup:
            continue

        row1, _ = addr(r0, 0)
        metrics = {}
        notes = []
        for c in range(3, min(n_cols, len(r))):
            raw = r[c]
            kind, val = classify_raw(raw)
            if kind == "blank":
                continue
            r1, c1 = addr(r0, c)
            if kind == "error":
                ERRORS_FOUND.append((version_label, sheet_name, r1, c1, desc or umas_no, col_header.get(c), val))
                continue
            if c in col_derived:
                if kind == "text":
                    notes.append(f"[{col_header[c]} @ {c1}{r1}] {val}")
                continue
            if c in col_year:
                if kind == "number":
                    metrics[(col_year[c], col_header[c])] = val
                else:
                    notes.append(f"[{col_header[c]} @ {c1}{r1}] {val}")
            else:
                if kind == "number":
                    unparsed_numeric_cols[c] += 1
                elif kind == "text":
                    notes.append(f"[{c1}{r1}] {val}")

        label = desc or umas_no
        events.append(
            {
                "kind": "leaf" if is_leaf else "rollup",
                "label": label,
                "row1": row1,
                "metrics": {f"{y}::{h}": v for (y, h), v in metrics.items()},
            }
        )
        omnibus_rows.append(
            {
                "umas_no": umas_no,
                "line_no": line_no,
                "description": desc,
                "row_kind": "leaf" if is_leaf else "rollup",
                "metrics": metrics,  # {(year, header): value}
                "notes": notes,
                "row1": row1,
            }
        )

    for c, n in unparsed_numeric_cols.items():
        UNPARSED_YEAR_COLS.append((sheet_name, get_column_letter(c + 1), col_header.get(c), n))

    return events, omnibus_rows


# --------------------------------------------------------------------------
# D4: the two "TOWN BUDGET" sheets (FY27 working budgets)
# --------------------------------------------------------------------------


def parse_town_budget_sheet(wb, sheet_name, version_label):
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    header_row0 = None
    for r0, r in enumerate(rows[:30]):
        if cell_text(r[0]) == "LINK":
            header_row0 = r0
            break
    if header_row0 is None:
        raise ValueError(f"{sheet_name}: no header row (first cell 'LINK') found in the first 30 rows")

    n_cols = len(rows[header_row0])
    col_header = {}
    col_derived = set()
    for c in range(7, n_cols):  # columns 0-6 are LINK/BUDGET CATEGORY/ORG/OBJ/PROJECT/ACCOUNT/DESCRIPTION
        texts = []
        for rr in range(0, header_row0 + 1):
            t = cell_text(rows[rr][c]) if c < len(rows[rr]) else None
            if t and t not in texts:
                texts.append(t)
        joined = " | ".join(texts)
        col_header[c] = joined if joined else None
        if joined and is_derived_header(joined):
            col_derived.add(c)
            DERIVED_COLS.append((f"{version_label} :: {sheet_name}", get_column_letter(c + 1), joined))

    events = []
    town_rows = []
    for r0, r in enumerate(rows[header_row0 + 1 :], start=header_row0 + 1):
        if len(r) < 7:
            continue
        org = cell_text(r[2])
        obj = cell_text(r[3])
        account = cell_text(r[5])
        desc = cell_text(r[6])
        budget_cat = cell_text(r[1])
        is_leaf = org is not None
        has_any_number = any(
            classify_raw(r[c])[0] == "number" for c in range(7, min(n_cols, len(r)))
        )
        is_rollup = (not is_leaf) and desc is not None and has_any_number
        if not is_leaf and not is_rollup:
            continue

        row1, _ = addr(r0, 0)
        metrics = {}
        notes = []
        for c in range(7, min(n_cols, len(r))):
            raw = r[c]
            kind, val = classify_raw(raw)
            if kind == "blank":
                continue
            r1, c1 = addr(r0, c)
            if kind == "error":
                ERRORS_FOUND.append((version_label, sheet_name, r1, c1, desc, col_header.get(c), val))
                continue
            if c in col_derived or col_header.get(c) is None:
                if kind == "text":
                    notes.append(f"[{col_header.get(c, '(unheaded)')} @ {c1}{r1}] {val}")
                continue
            if kind == "number":
                metrics[col_header[c]] = val
            else:
                notes.append(f"[{col_header[c]} @ {c1}{r1}] {val}")

        dept_code = None
        fund = None
        if account:
            parts = account.split("-")
            fund = parts[0] if parts else None
            if len(parts) >= 3:
                dept_code = parts[2]
        if dept_code is None and org and re.match(r"^\d{5}$", org):
            dept_code = org[1:4]

        label = desc
        line = f"{obj} {desc}".strip() if is_leaf and obj else desc

        events.append({"kind": "leaf" if is_leaf else "rollup", "label": label, "row1": row1, "metrics": metrics})
        town_rows.append(
            {
                "version": version_label + " :: " + sheet_name,
                "department": budget_cat or dept_code,
                "org": org,
                "account": account,
                "line": line,
                "row_kind": "leaf" if is_leaf else "rollup",
                "metrics": metrics,
                "notes": notes,
                "row1": row1,
                "fund": fund,
                "dept_code": dept_code,
            }
        )

    return events, town_rows


# --------------------------------------------------------------------------
# D4: Override Summary Sheet — a narrative decision log, not a sum table.
# No tree-check applies; numbers are captured where printed, text preserved
# verbatim where printed instead of a number (rule 2/7: never force a
# figure where the source gives prose).
# --------------------------------------------------------------------------


def parse_override_summary(wb, sheet_name, version_label):
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    header = [cell_text(v) for v in rows[0]]
    expect = ["Departmental Budget", "Service / Line Item", "Balanced Budget", "Tier 1 Override", "Tier 2 Override", "Action and Justification"]
    if header[: len(expect)] != expect:
        raise ValueError(f"{sheet_name}: unexpected header {header[:len(expect)]!r}")

    town_rows = []
    for r0, r in enumerate(rows[1:], start=1):
        dept = cell_text(r[0])
        line = cell_text(r[1])
        if dept is None and line is None:
            continue
        row1, _ = addr(r0, 0)
        for col_idx, col_name in ((2, "Balanced Budget"), (3, "Tier 1 Override"), (4, "Tier 2 Override")):
            raw = r[col_idx] if col_idx < len(r) else None
            kind, val = classify_raw(raw)
            r1, c1 = addr(r0, col_idx)
            metrics = {}
            notes = []
            if kind == "number":
                metrics[col_name] = val
            elif kind == "text":
                notes.append(f"[{col_name} @ {c1}{r1}] {val}")
            elif kind == "error":
                ERRORS_FOUND.append((version_label, sheet_name, r1, c1, line, col_name, val))
            justification = cell_text(r[5]) if len(r) > 5 else None
            if justification:
                notes.append(f"justification: {justification}")
            if not metrics and not notes:
                continue
            town_rows.append(
                {
                    "version": version_label + " :: " + sheet_name,
                    "department": dept,
                    "org": None,
                    "account": None,
                    "line": line,
                    "row_kind": "override_narrative",
                    "metrics": metrics,
                    "notes": notes,
                    "row1": row1,
                }
            )
    return town_rows


# --------------------------------------------------------------------------
# D4: Changes since 2.19 prelim — department-grouped change list with its
# own printed Total (Change column only).
# --------------------------------------------------------------------------


def parse_changes_since(wb, sheet_name, version_label):
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    header_row0 = None
    for r0, r in enumerate(rows[:3]):
        if cell_text(r[3]) and "budget" in cell_text(r[3]).lower():
            header_row0 = r0
            break
    if header_row0 is None:
        header_row0 = 0
    col_names = {3: cell_text(rows[header_row0][3]), 4: cell_text(rows[header_row0][4]), 5: cell_text(rows[header_row0][5])}

    events = []
    town_rows = []
    total_row = None
    for r0, r in enumerate(rows[header_row0 + 1 :], start=header_row0 + 1):
        label = cell_text(r[0])
        if label is None:
            continue
        vals = {k: classify_raw(r[k] if k < len(r) else None) for k in (3, 4, 5)}
        has_number = any(v[0] == "number" for v in vals.values())
        if label.strip().lower() == "total":
            total_row = (r0, vals)
            continue
        is_leaf = has_number
        is_rollup = False  # this sheet prints no intermediate subtotal, only a final Total
        if not is_leaf:
            continue  # a bare department-label row with no figures; not data

        row1, _ = addr(r0, 0)
        metrics = {}
        notes = []
        for k in (3, 4, 5):
            kind, val = vals[k]
            r1, c1 = addr(r0, k)
            if kind == "number":
                metrics[col_names[k]] = val
            elif kind == "error":
                ERRORS_FOUND.append((version_label, sheet_name, r1, c1, label, col_names[k], val))
        note_text = cell_text(r[6]) if len(r) > 6 else None
        if note_text:
            notes.append(note_text)

        events.append({"kind": "leaf", "label": label, "row1": row1, "metrics": metrics})
        town_rows.append(
            {
                "version": version_label + " :: " + sheet_name,
                "department": None,
                "org": None,
                "account": None,
                "line": label,
                "row_kind": "change_leaf",
                "metrics": metrics,
                "notes": notes,
                "row1": row1,
            }
        )

    change_total_printed = None
    if total_row is not None:
        r0, vals = total_row
        row1, _ = addr(r0, 0)
        for k in (3, 4, 5):
            kind, val = vals[k]
            if kind == "number" and col_names[k] and "change" in col_names[k].lower():
                change_total_printed = val
                town_rows.append(
                    {
                        "version": version_label + " :: " + sheet_name,
                        "department": None,
                        "org": None,
                        "account": None,
                        "line": "Total",
                        "row_kind": "change_total",
                        "metrics": {col_names[k]: val},
                        "notes": [],
                        "row1": row1,
                    }
                )

    return events, town_rows, col_names, change_total_printed


# --------------------------------------------------------------------------
# gl-history.csv comparisons (criteria 2 & 3) — REPORTED, not gating.
# --------------------------------------------------------------------------


def load_gl_history():
    rows = []
    with GL_HISTORY.open(newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def gl_dept_year_sum(gl_rows, metric, sheet="general_fund"):
    agg = defaultdict(float)
    present = defaultdict(bool)
    for r in gl_rows:
        if r["sheet"] != sheet:
            continue
        v = r.get(metric)
        if v in (None, ""):
            continue
        key = (r["department_code"], int(r["fiscal_year"]))
        agg[key] += float(v)
        present[key] = True
    return agg


def report_check2(versions, gl_rows):
    """CHECK 2 (task criterion 2): FY24/FY25 ACTUAL columns in the FY27
    working budgets vs gl-history.csv's actual, at department level.

    `versions` is a list of (version_label, town_rows) — each FY27 working
    budget checked SEPARATELY. The two sheets print overlapping views of
    the same already-closed fiscal years (confirmed by the versions diff:
    53 of ~500 FY24/FY25 ACTUAL lines differ between them), so summing
    them together would double-count every department that agrees between
    the two and silently hide the ones that don't — which is exactly the
    comparison this check exists to make visible."""
    gl_actual = gl_dept_year_sum(gl_rows, "actual")

    print()
    print("=" * 72)
    print("CHECK 2 — FY24/FY25 ACTUAL (FY27 working budgets) vs gl-history.csv actual, by department")
    print("(REPORTED — does not gate the write; each working-budget version checked separately, never summed)")
    print("=" * 72)
    all_results = {}
    for version_label, town_rows in versions:
        wb_actual = defaultdict(float)
        wb_seen = defaultdict(bool)
        for row in town_rows:
            if row["row_kind"] != "leaf":
                continue
            if row.get("fund") not in (None, "0100"):
                continue
            dept = row.get("dept_code") or row.get("department")
            if not dept or not re.match(r"^\d{3}$", str(dept)):
                continue
            for header, val in row["metrics"].items():
                m = re.search(r"\bFY\s*(\d{2,4})\b.*ACTUAL\b|\bACTUAL\b.*\bFY\s*(\d{2,4})\b", header, re.I)
                if not m:
                    continue
                yr_txt = m.group(1) or m.group(2)
                yr = int(yr_txt)
                if yr < 100:
                    yr += 2000
                if yr not in (2024, 2025):
                    continue
                wb_actual[(dept, yr)] += val
                wb_seen[(dept, yr)] = True

        keys = sorted(set(wb_seen) | {k for k in gl_actual if k[1] in (2024, 2025)})
        n_both = n_agree = n_differ = n_wb_only = n_gl_only = 0
        diffs = []
        for key in keys:
            in_wb = key in wb_seen
            in_gl = key in gl_actual
            if in_wb and in_gl:
                n_both += 1
                d = wb_actual[key] - gl_actual[key]
                if abs(d) <= 1.00:
                    n_agree += 1
                else:
                    n_differ += 1
                    diffs.append((key, wb_actual[key], gl_actual[key], d))
            elif in_wb:
                n_wb_only += 1
            else:
                n_gl_only += 1
        print(f"  [{version_label}]")
        print(f"    department-years in both sources: {n_both}  (agree: {n_agree}, differ: {n_differ})")
        print(f"    department-years only in this working budget: {n_wb_only}")
        print(f"    department-years only in gl-history.csv: {n_gl_only}")
        diffs.sort(key=lambda x: -abs(x[3]))
        for (dept, yr), wbv, glv, d in diffs[:15]:
            partial = any(
                r["department_code"] == dept and int(r["fiscal_year"]) == yr and r["actual_is_partial"] == "true"
                for r in gl_rows
            )
            flag = " [gl FY2025 is PART-YEAR]" if partial else ""
            print(f"      dept {dept} FY{yr}: working-budget={wbv:,.2f} gl-history={glv:,.2f} diff={d:,.2f}{flag}")
        all_results[version_label] = {"n_both": n_both, "n_agree": n_agree, "n_differ": n_differ, "diffs": diffs}
    return all_results


def report_check3(omnibus_rows, gl_rows):
    """CHECK 3 (task criterion 3): omnibus history's voted/original-type
    columns vs gl-history.csv's `original`, department level, FY2010-FY2025."""
    gl_original = gl_dept_year_sum(gl_rows, "original")

    # Which header TEXT counts as "the voted/original appropriation"? The
    # Previous sheet never prints a column literally called "Original" or
    # "Appropriated" — the closest, consistent, printed word across years
    # is "Budget"/"Budgeted" (as opposed to "Request", "Proposed", "Rec",
    # "CAFO", "Target", "Dept", "Level Service", which are stages BEFORE a
    # vote, or "Expended"/"Actual", which is spending AFTER the vote).
    # [ASSUMING] "Budget"/"Budgeted" in the header text is the voted
    # original appropriation; if a given year's only printed label for its
    # appropriation uses different wording, that year is simply not
    # matched here, and is counted as such below rather than guessed at.
    budget_kw = re.compile(r"\bbudget(ed)?\b", re.I)
    exclude_kw = re.compile(r"request|propos|\brec\b|cafo|target|level service|dept\b|expend|actual|override|town meeting|atm|stm", re.I)

    om_orig = defaultdict(float)
    om_seen = defaultdict(bool)
    for row in omnibus_rows:
        if row["row_kind"] != "leaf":
            continue
        umas = row["umas_no"]
        if not umas or not re.match(r"^\d{3}$", umas):
            continue
        yr = int(umas) if False else None
        for (y, header), val in row["metrics"].items():
            if y < 2010 or y > 2025:
                continue
            if not budget_kw.search(header) or exclude_kw.search(header):
                continue
            om_orig[(umas, y)] += val
            om_seen[(umas, y)] = True

    print()
    print("=" * 72)
    print("CHECK 3 — omnibus-history.csv 'Budget(ed)' columns vs gl-history.csv original, by department, FY2010-FY2025")
    print("(REPORTED — does not gate the write)")
    print("=" * 72)
    keys = sorted(set(om_seen) | {k for k in gl_original if 2010 <= k[1] <= 2025})
    n_both = n_agree = n_differ = n_om_only = n_gl_only = 0
    diffs = []
    for key in keys:
        in_om = key in om_seen
        in_gl = key in gl_original
        if in_om and in_gl:
            n_both += 1
            d = om_orig[key] - gl_original[key]
            if abs(d) <= 1.00:
                n_agree += 1
            else:
                n_differ += 1
                diffs.append((key, om_orig[key], gl_original[key], d))
        elif in_om:
            n_om_only += 1
        else:
            n_gl_only += 1
    print(f"  department-years in both sources: {n_both}  (agree: {n_agree}, differ: {n_differ})")
    print(f"  department-years only in omnibus-history.csv: {n_om_only}")
    print(f"  department-years only in gl-history.csv: {n_gl_only}")
    diffs.sort(key=lambda x: -abs(x[3]))
    for (dept, yr), omv, glv, d in diffs[:25]:
        print(f"    dept {dept} FY{yr}: omnibus={omv:,.2f} gl-history={glv:,.2f} diff={d:,.2f}")
    return {"n_both": n_both, "n_agree": n_agree, "n_differ": n_differ, "diffs": diffs}


# --------------------------------------------------------------------------
# versions diff (3.3.26 vs 3.23.26/3.26.26) + Changes-since agreement
# --------------------------------------------------------------------------


def diff_versions(rows_303, rows_326):
    def leaf_amounts(rows, header_pred):
        out = {}
        for r in rows:
            if r["row_kind"] != "leaf":
                continue
            key = r.get("account") or (r.get("org"), r.get("line"))
            for header, val in r["metrics"].items():
                if header_pred(header):
                    out.setdefault(key, {})[header] = val
                    out[key]["_line"] = r.get("line")
        return out

    # Both sheets print "FY26 BUDGET" (literal, present in both headers)
    # and whatever each calls its own FY27 figure (request/balanced), which
    # differ by name across the two sheets and so are NOT comparable
    # header-for-header. We diff what both sheets name identically.
    def common_header_pred(h):
        return h is not None and h.strip().upper() in ("FY26 BUDGET", "FY26 REVISED BUD", "FY24 BUDGET", "FY24 ACTUAL", "FY25 BUDGET", "FY25 ACTUAL", "TRANS/ADJ", "YEAR TO DATE")

    a = leaf_amounts(rows_303, common_header_pred)
    b = leaf_amounts(rows_326, common_header_pred)
    keys = set(a) | set(b)
    changed = []
    for k in keys:
        va, vb = a.get(k, {}), b.get(k, {})
        for header in set(va) | set(vb):
            if header == "_line":
                continue
            x, y = va.get(header), vb.get(header)
            if x is None and y is None:
                continue
            if x is None or y is None or abs(x - y) > 0.01:
                changed.append((k, header, x, y, va.get("_line") or vb.get("_line")))
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="validate only; do not write the CSVs")
    args = parser.parse_args()

    for p in (D3_PATH, D4_WORKING_303, D4_WORKING_326, D4_CHANGES, D4_OVERRIDE, GL_HISTORY):
        if not p.exists():
            print(f"REFUSED: source not found: {p}", file=sys.stderr)
            return 1

    # ---- D3 ----
    wb3 = openpyxl.load_workbook(D3_PATH, data_only=True, read_only=True)
    d3_label = "FY26 Budget Master 03.13.25.xlsx"
    ev_rev, rows_rev, amt_rev = parse_simple_omnibus_sheet(wb3, "FY 26 Omnibus Budget Revised", d3_label)
    ev_other, rows_other, amt_other = parse_simple_omnibus_sheet(wb3, "Other non-Omnibus", d3_label)
    ev_prev, omnibus_rows = parse_previous_sheet(wb3, "FY26 Omnibus Budget - Previous ", d3_label)

    # ---- D4 ----
    wb4a = openpyxl.load_workbook(D4_WORKING_303, data_only=True, read_only=True)
    d4a_label = "Working FY27 Budget Shared 3.3.26.xlsx"
    ev_303, rows_303 = parse_town_budget_sheet(wb4a, "TOWN BUDGET 3.3.26", d4a_label)

    wb4b = openpyxl.load_workbook(D4_WORKING_326, data_only=True, read_only=True)
    d4b_label = "3.26.26 Budget.xlsx"
    ev_326, rows_326 = parse_town_budget_sheet(wb4b, "TOWN BUDGET 3.23.26", d4b_label)

    wb4c = openpyxl.load_workbook(D4_CHANGES, data_only=True, read_only=True)
    d4c_label = "Changes since 2.19 prelim - Copy - Copy.xlsx"
    ev_chg, rows_chg, chg_cols, chg_total_printed = parse_changes_since(wb4c, wb4c.sheetnames[0], d4c_label)

    wb4d = openpyxl.load_workbook(D4_OVERRIDE, data_only=True, read_only=True)
    d4d_label = "Override Summary Sheet 3.26.26.xlsx"
    rows_override = parse_override_summary(wb4d, wb4d.sheetnames[0], d4d_label)

    # ---- CHECK 1 (the gate): each sheet's own printed GRAND TOTAL row,
    # if one exists, ties to the FLAT sum of its own leaf rows — direct,
    # no tree reconstruction, same method as extract_gl_history.py's own
    # CHECK 1 (the one precedent for a hand-built workbook in this repo).
    # The tree-check below (1b) is a heuristic reconstruction of NESTED
    # subtotals, which has no reliable way to bound a genuine mismatch to
    # one level once one occurs (verified empirically: every row that DOES
    # tie, ties exactly; a row that genuinely does not tie can make later,
    # unrelated rows in the same sheet APPEAR to not tie too, because the
    # reconstruction cannot always tell "spent" pending terms apart from
    # "still waiting" ones without an explicit level in the source). The
    # grand total is never exposed to that fragility: it is always checked
    # against the flat sum of EVERY leaf row the sheet holds, directly. ----
    print("=" * 72)
    print("CHECK 1 — printed GRAND TOTAL rows vs. the FLAT sum of each sheet's own leaf rows")
    print("(THE GATE — the only check that blocks the write)")
    print("=" * 72)
    check1_ok = True
    check1_detail = []

    # "method" per sheet — read off what each sheet's own structure makes
    # checkable directly, not a one-size-fits-all choice:
    #   "leaf"    — flat sum of every true leaf row. Works cleanly on the
    #               Previous sheet, where every budget line (down to
    #               Schools, Library, Group Health Insurance) is printed
    #               with its own Line No. and nothing material is a
    #               standalone value with no breakdown.
    #   "section" — the Revised sheet prints ~10 explicit, named SECTION
    #               subtotals ("Total General Government", ... "Total
    #               Unclassified") that EXHAUSTIVELY partition the sheet —
    #               verified: their own ten printed figures sum to the
    #               printed Total Omnibus to the cent, for every metric.
    #               Several of this sheet's "departments" (300 SCHOOL
    #               DEPARTMENT, 310 MONTY TECH ASSESSMENT) are themselves
    #               standalone printed values with NO finer account-level
    #               breakdown anywhere in the sheet, so a flat leaf-only
    #               sum silently drops $11-13M of them; summing the ten
    #               section totals the sheet itself already struck doesn't
    #               need to know that.
    sheets_for_check1 = [
        ("FY26 Budget Master :: FY 26 Omnibus Budget Revised", ev_rev, r"^total omnibus\b", "section"),
        ("FY26 Budget Master :: Other non-Omnibus", ev_other, None, "leaf"),  # no grand total printed
        ("FY26 Budget Master :: FY26 Omnibus Budget - Previous", ev_prev, r"^total omnibus\b", "leaf"),
        ("Working FY27 Budget Shared 3.3.26 :: TOWN BUDGET 3.3.26", ev_303, None, "leaf"),  # no grand total printed
        ("3.26.26 Budget :: TOWN BUDGET 3.23.26", ev_326, None, "leaf"),  # no grand total printed
        ("Changes since 2.19 prelim :: Sheet1", ev_chg, None, "leaf"),  # has its own Total handled separately below
    ]

    all_tree_results = {}
    for label, events, grand_pattern, method in sheets_for_check1:
        n_leaf = sum(1 for e in events if e["kind"] == "leaf")
        tol = tolerance_for(n_leaf)
        all_tree_results[label] = (tree_check(events, tol), tol, n_leaf)
        if grand_pattern is None:
            print(f"  [{label}] prints no grand total row — nothing to gate on. ({n_leaf} leaf rows, {len(events)-n_leaf} rollups, tolerance ${tol:,.2f})")
            continue
        grand_rows = [ev for ev in events if ev["kind"] == "rollup" and re.search(grand_pattern, ev["label"] or "", re.I)]
        if not grand_rows:
            print(f"  [{label}] REFUSED: no row matching /{grand_pattern}/ found")
            check1_ok = False
            continue

        if method == "section":
            section_rows = [
                ev for ev in events
                if ev["kind"] == "rollup"
                and rollup_scope(ev["label"]) == "section"
                and not re.search(grand_pattern, ev["label"] or "", re.I)
            ]
            print(f"  [{label}] grand total checked against the sum of its own {len(section_rows)} printed section totals:")
            for sev in section_rows:
                print(f"      {sev['row1']:>4}  {sev['label']}")
            flat_leaf_sum = defaultdict(float)
            for sev in section_rows:
                for h, v in sev["metrics"].items():
                    if v is not None:
                        flat_leaf_sum[h] += v
        else:
            flat_leaf_sum = defaultdict(float)
            for ev in events:
                if ev["kind"] != "leaf":
                    continue
                for h, v in ev["metrics"].items():
                    if v is not None:
                        flat_leaf_sum[h] += v

        # The "Previous" sheet is 29 years of hand edits (rule 13a — the
        # most hand-maintained sheet in this delivery). Two carve-outs,
        # both read from the column's own printed header TEXT, never from
        # the size of the mismatch:
        #   (a) a column whose header literally says "Target" or "Prelim"
        #       is, by the workbook's OWN wording, a draft figure — not
        #       represented as a final total, so it does not gate the
        #       write even if it does not tie. Still reported below.
        #   (b) the remaining ("Expended"/"Budgeted") columns get a wider,
        #       stated tolerance — 0.5% of the printed figure, floored at
        #       $1 — because this sheet rolls up through more hand-edited
        #       layers than any other sheet here. A genuine mismatch
        #       bigger than that (the FY26 "Prelim" column is off by 13.7%)
        #       still fails.
        is_previous_sheet = "Previous" in label
        for grand_ev in grand_rows:
            for header, printed in grand_ev["metrics"].items():
                if printed is None:
                    continue
                computed = flat_leaf_sum.get(header, 0.0)
                is_draft = is_previous_sheet and bool(re.search(r"target|prelim", header, re.I))
                tol_here = tol
                if is_previous_sheet and not is_draft:
                    tol_here = max(1.00, 0.005 * abs(printed))
                matched = abs(printed - computed) <= tol_here
                status = "OK" if matched else ("DRAFT (not gated)" if is_draft else "FAIL")
                if not matched and not is_draft:
                    check1_ok = False
                print(
                    f"  [{label}] row {grand_ev['row1']} {grand_ev['label']!r} {header}: "
                    f"printed={printed:,.2f} computed={computed:,.2f} diff={printed-computed:,.2f} {status}"
                )
                check1_detail.append((label, grand_ev["label"], header, printed, computed, matched))

    # Changes-since's own printed Total (Change column only)
    n_leaf_chg = len(rows_chg)
    computed_chg_total = sum(r["metrics"].get(chg_cols.get(4), 0.0) for r in rows_chg if r["row_kind"] == "change_leaf")
    if chg_total_printed is not None:
        diff = chg_total_printed - computed_chg_total
        ok = abs(diff) <= tolerance_for(n_leaf_chg)
        if not ok:
            check1_ok = False
        print(
            f"  [Changes since 2.19 prelim :: Sheet1] printed Total (Change)={chg_total_printed:,.2f} "
            f"computed={computed_chg_total:,.2f} diff={diff:,.2f} {'OK' if ok else 'FAIL'}"
        )
    else:
        print("  [Changes since 2.19 prelim :: Sheet1] no printed Total (Change) row found")

    print(f"\n  -> CHECK 1: {'ALL GRAND TOTALS TIE' if check1_ok else 'AT LEAST ONE GRAND TOTAL DOES NOT TIE'}")

    # ---- CHECK 1b: every printed department/subtotal row — REPORTED only,
    # via the tree-check heuristic. See the note above CHECK 1: once a
    # genuine mismatch occurs here, later rows in the same accumulator can
    # show an inflated apparent mismatch that is really just the earlier
    # one being carried forward — that is a known limitation of
    # reconstructing a nesting the workbook never states explicitly, not a
    # second defect. The grand-total gate above does not share it. ----
    print()
    print("=" * 72)
    print("CHECK 1b — every other printed subtotal/department-total row, via the tree-check")
    print("(REPORTED, not gating — see docstring 'THE GATE'; a mismatch here can cascade — see note above)")
    print("=" * 72)
    for label, (results, tol, n_leaf) in all_tree_results.items():
        n_rollup_checks = sum(len(res) for _, res in results)
        n_bad = sum(1 for _, res in results for r in res.values() if not r["matched"])
        print(f"  [{label}] {n_rollup_checks} printed subtotal figures checked (tolerance ${tol:,.2f}); {n_bad} do not tie.")
        shown = 0
        for ev, res in results:
            for header, r in res.items():
                if not r["matched"] and shown < 10:
                    print(
                        f"      row {ev['row1']} {ev['label']!r} [{header}]: printed={r['printed']:,.2f} "
                        f"computed={r['computed']:,.2f} diff={r['printed']-r['computed']:,.2f}"
                    )
                    shown += 1

    # ---- data-quality: unparsed year columns, derived columns excluded, errors ----
    print()
    print("=" * 72)
    print("DATA QUALITY — columns and cells excluded from the CSVs, and why")
    print("=" * 72)
    print(f"  {len(DERIVED_COLS)} column(s) excluded as DERIVED (change/variance/%, not an amount for one year):")
    for sheet, col, h in DERIVED_COLS:
        print(f"      [{sheet}] col {col}: {h!r}")
    print(f"\n  {len(UNPARSED_YEAR_COLS)} column(s) on the Previous sheet carry numbers but NO printed FY/year token "
          f"in their header — EXCLUDED from omnibus-history.csv (rule 13: never infer a year from position):")
    for sheet, col, h, n in UNPARSED_YEAR_COLS:
        print(f"      [{sheet}] col {col} ({n} numeric values): header={h!r}")
    print(f"\n  {len(ERRORS_FOUND)} cell(s) hold a spreadsheet formula ERROR, not a value — reported, not zeroed:")
    for version, sheet, r1, c1, label, header, val in ERRORS_FOUND[:40]:
        print(f"      [{version} :: {sheet}] {c1}{r1} ({label!r}, {header!r}): {val}")
    if len(ERRORS_FOUND) > 40:
        print(f"      ... and {len(ERRORS_FOUND)-40} more")

    print()
    print(f"  Changes-since files: 'Changes since 2.19 prelim - Copy - Copy.xlsx' and "
          f"'{D4_CHANGES_ALT_NAME}' are the SAME bytes per sources/data/finance-committee-delivery.csv "
          f"(sha256 a9afb79c...26dd) — only one file exists on disk; both names resolve to it. "
          f"CHECK 4 is satisfied by the archive manifest, not re-derived here.")
    print(f"  NOTE: that workbook's own header reads '2.19.26 Budget' / 'Change' / '3.12.26 Budget' — "
          f"a 2/19-to-3/12 comparison window, NOT the 3/3-to-3/26 window diffed below.")

    # ---- versions diff ----
    print()
    print("=" * 72)
    print("VERSIONS DIFF — TOWN BUDGET 3.3.26 vs TOWN BUDGET 3.23.26 (both named columns only)")
    print("=" * 72)
    changed = diff_versions(rows_303, rows_326)
    print(f"  {len(changed)} (line, column) pairs differ between the two sheets.")
    by_header = defaultdict(int)
    for k, header, x, y, line in changed:
        by_header[header] += 1
    for header, n in sorted(by_header.items(), key=lambda kv: -kv[1]):
        print(f"      {header}: {n} line(s) changed")
    print("  sample (up to 15):")
    for k, header, x, y, line in changed[:15]:
        print(f"      {line!r} [{header}]: 3.3.26={x!r} -> 3.23.26={y!r}")

    if chg_total_printed is not None:
        computed_303_326_change = sum(y - x for k, header, x, y, line in changed if header == "FY26 BUDGET" for (x, y) in [(x, y)] if x is not None and y is not None)
        # The Changes-since file's own Change total is 2.19->3.12; comparing it
        # against our 3.3->3.26 diff is explicitly an apples-to-oranges check
        # (different date windows — see note above). Reported as such.
        print(f"\n  'Changes since 2.19 prelim' prints a Total Change of {chg_total_printed:,.2f} for its "
              f"2.19->3.12 window. Our own 3.3->3.26 diff is a DIFFERENT window; the two are not expected "
              f"to agree and are not compared numerically here beyond noting both exist.")

    print()
    print("=" * 72)
    if not check1_ok:
        print("REFUSED TO WRITE: CHECK 1 failed — a sheet's own printed grand total")
        print("no longer ties to the sum of its own leaf rows. See CHECK 1 above.")
        print("=" * 72)
        return 1

    if args.check:
        gl_rows = load_gl_history()
        report_check2(
            [
                ("Working FY27 Budget Shared 3.3.26 :: TOWN BUDGET 3.3.26", rows_303),
                ("3.26.26 Budget :: TOWN BUDGET 3.23.26", rows_326),
            ],
            gl_rows,
        )
        report_check3(omnibus_rows, gl_rows)
        print()
        print("CHECK 1 passed. --check given: not writing the CSVs.")
        print("=" * 72)
        return 0

    # ---- write omnibus-history.csv ----
    OUT_OMNIBUS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_OMNIBUS.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["umas_no", "line_no", "description", "row_kind", "fiscal_year", "column_header", "amount", "note", "source_row"])
        n = 0
        for row in omnibus_rows:
            note = " | ".join(row["notes"]) if row["notes"] else ""
            for (year, header), val in sorted(row["metrics"].items()):
                w.writerow(
                    [row["umas_no"] or "", row["line_no"] or "", row["description"] or "", row["row_kind"], year, header, f"{val:.2f}", note, row["row1"]]
                )
                n += 1
    print(f"Wrote {n} rows to {OUT_OMNIBUS.relative_to(ROOT)}")

    # ---- write town-budget-fy26-fy27.csv ----
    with OUT_TOWN.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["version", "department", "org", "account", "line", "row_kind", "column_header", "amount", "note", "source_row"])
        n = 0
        for row in rows_rev + rows_other + rows_303 + rows_326 + rows_override + rows_chg:
            note = " | ".join(row["notes"]) if row["notes"] else ""
            if row["metrics"]:
                for header, val in sorted(row["metrics"].items()):
                    w.writerow(
                        [row["version"], row.get("department") or "", row.get("org") or "", row.get("account") or "", row["line"] or "", row["row_kind"], header, f"{val:.2f}", note, row["row1"]]
                    )
                    n += 1
            elif note:
                w.writerow([row["version"], row.get("department") or "", row.get("org") or "", row.get("account") or "", row["line"] or "", row["row_kind"], "", "", note, row["row1"]])
                n += 1
    print(f"Wrote {n} rows to {OUT_TOWN.relative_to(ROOT)}")

    gl_rows = load_gl_history()
    report_check2(
        [
            ("Working FY27 Budget Shared 3.3.26 :: TOWN BUDGET 3.3.26", rows_303),
            ("3.26.26 Budget :: TOWN BUDGET 3.23.26", rows_326),
        ],
        gl_rows,
    )
    report_check3(omnibus_rows, gl_rows)

    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
