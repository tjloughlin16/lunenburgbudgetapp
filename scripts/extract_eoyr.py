#!/usr/bin/env python3
"""
Extract DESE End of Year Financial Report (EOYR) data for Lunenburg, district
code 162, FY2023 and FY2024, from the working copies obtained via the Finance
Committee / Amanda Moore FOIA request (sources/data/finance-committee-delivery.csv,
keys matching "24eoy162" and "23eoy162"). See CLAUDE.md rule 13a: these are
WORKING COPIES passed on by the district, not necessarily the report as filed
with DESE -- the FY24 file is dated 9-20-24 and an earlier review found its
grant columns differ from DESE's published FY24 data.

Produces three CSVs under sources/data/:

  eoyr-schedule1.csv  -- Schedule 1, revenue and expenditure summary, by
                         function code and printed column (fund), line by line.
  eoyr-schedule3.csv  -- Schedule 3 District Total, by function and fund,
                         with the raw header cells each stitched column name
                         came from (rule 13: a column name we assembled is
                         derived, cite its cells).
  eoyr-nss.csv        -- the Net School Spending computation (the actual-year
                         block only -- see NSS_SCOPE note below; rule 1 forbids
                         mixing the adjacent "budgeted NSS" block in with it).

Both source workbooks use the identical standard DESE EOYR template -- the
"SCHEDULE 1"/"SCHEDULE 3"/etc. markers land on the SAME row numbers in both
files -- so this script locates every section by scanning for its own
printed markers rather than by hardcoding row numbers for one year.

Run with --check to verify every tie-out below BEFORE writing anything. The
script refuses to write if a tie-out fails (DONE WHEN 1) or an NSS arithmetic
relationship fails (DONE WHEN 2).
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

REPO = Path(__file__).resolve().parent.parent
BASE = (
    REPO
    / "sources/budget-workbooks/finance-committee/fy26-budget/department-presentations"
    / "lunenburg-public-schools/school-budget-files-amanda-moore-foia-request-to-school-dept"
)

FILES = {
    "FY2024": BASE / "24eoy162-9-20-24.xlsx",
    "FY2023": BASE / "updated-th-23eoy162.xlsm",
}
EOY_SHEET = {"FY2024": "eoy24", "FY2023": "eoy23"}

OUT_S1 = REPO / "sources/data/eoyr-schedule1.csv"
OUT_S3 = REPO / "sources/data/eoyr-schedule3.csv"
OUT_NSS = REPO / "sources/data/eoyr-nss.csv"

DESE_FUNCTION_FILE = REPO / "sources/state-dese/district-expenditures-by-function.xlsx"
DESE_NSS_FILE = REPO / "sources/state-dese/dese-ch70-foundation-nss.xlsx"
DIST_CODE = "01620000"

TOL = 2.0  # dollars; the workbook's own formulas chain several ROUND()s

# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def load_grid(path, sheet):
    """Return a list of row-tuples (1-indexed: grid[r-1] is row r), values only."""
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True, keep_vba=False)
    ws = wb[sheet]
    grid = list(ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True))
    wb.close()
    return grid


def cell_at(grid, r, c):
    row = grid[r - 1]
    return row[c] if c < len(row) else None


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


FUNC_CODE_RE = re.compile(r"\(([\d][\d,\s]*)\)")


def trailing_code(desc):
    """Last purely-numeric parenthetical group anywhere in desc, or None."""
    if not isinstance(desc, str):
        return None
    codes = FUNC_CODE_RE.findall(desc)
    return codes[-1].strip() if codes else None


def is_object_code(code):
    """A two-digit DESE expenditure-object code (01-07), not a function code."""
    if code is None:
        return False
    if "," in code:
        return False
    digits = re.sub(r"\D", "", code)
    if not digits:
        return False
    try:
        return len(digits) <= 2 and int(digits) < 100
    except ValueError:
        return False


SCHEDULE_MARKER_RE = re.compile(r"^\s*SCHEDULE\s+(\d+)", re.I)


def schedule_marker(row):
    """If this row is a 'SCHEDULE N' marker (in col C or D), return N, else None."""
    for ci in (2, 3):
        v = row[ci] if ci < len(row) else None
        if isinstance(v, str):
            m = SCHEDULE_MARKER_RE.match(v.strip())
            if m:
                return int(m.group(1))
    return None


def stitch_header(grid, header_rownums, col_start, col_end):
    """
    Build {col_idx: heading_text} and {col_idx: [(coord, value), ...]} by
    concatenating, top to bottom, every non-empty text cell in col_start..col_end
    across header_rownums -- skipping any row that is purely a column-number
    index row (e.g. 1,2,3,4,5,6), which is not a heading.
    """
    heading_parts = {c: [] for c in range(col_start, col_end + 1)}
    cites = {c: [] for c in range(col_start, col_end + 1)}
    for r in header_rownums:
        row = grid[r - 1]
        vals = {c: (row[c] if c < len(row) else None) for c in range(col_start, col_end + 1)}
        nonnull = [v for v in vals.values() if v is not None]
        if nonnull:
            as_int = []
            ok = True
            for v in nonnull:
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    as_int.append(int(v))
                elif isinstance(v, str) and v.strip().lstrip("-").isdigit():
                    as_int.append(int(v.strip()))
                else:
                    ok = False
                    break
            if ok and as_int == list(range(as_int[0], as_int[0] + len(as_int))):
                continue  # this is a "1,2,3,4..." column-index row, not a heading
        for c, v in vals.items():
            if v is None:
                continue
            if isinstance(v, str):
                v = v.strip()
                if not v:
                    continue
            coord = f"{get_column_letter(c + 1)}{r}"
            heading_parts[c].append(str(v))
            cites[c].append((coord, v))
    headings = {c: " ".join(parts) for c, parts in heading_parts.items() if parts}
    return headings, cites


TIE_ERRORS = []  # list of human-readable strings; non-empty => refuse to write
TIE_WARNINGS = []  # tie mismatches fully explained by a column the marker leaves blank


def record_tie(fy, sheet, section, line, col, expected, printed, coord, headings=None, amounts=None, accum=None):
    """
    Verify printed == expected (the running sum of the raw lines since the
    previous marker). If it does not tie, check for ONE specific, real
    defect pattern seen in these workbooks: the marker row's own formula is
    a ROW-WISE sum across its own cells (e.g. =SUM(E585:P585)), and if the
    workbook's preparer left one fund column blank on that marker row (while
    every contributing line below it DID post a figure to that column), the
    marker understates itself by exactly that column's accumulated total.
    That is a genuine gap in the SOURCE workbook, not a parsing error, so it
    is downgraded to a cited warning instead of a blocking error -- but only
    when the shortfall is fully and exactly accounted for by such a blank
    column (rule 13: cite the coordinate and the raw value).
    """
    diff = (expected or 0) - (printed or 0)
    if abs(diff) <= TOL:
        return
    if headings and amounts is not None and accum is not None:
        blanks = [c2 for c2 in headings if amounts.get(c2) is None]
        blank_total = sum(accum.get(c2, 0.0) for c2 in blanks)
        if blanks and abs(blank_total - diff) <= TOL:
            row_num = "".join(ch for ch in coord if ch.isdigit())
            blank_desc = ", ".join(f"{headings[c2]!r} ({get_column_letter(c2 + 1)}{row_num})" for c2 in blanks)
            TIE_WARNINGS.append(
                f"{fy} {sheet} [{section}] line {line} col '{col}' ({coord}): printed {printed!r}, "
                f"sum of its lines is {expected!r} (short by {diff:.2f}) -- fully explained by the "
                f"marker row leaving {blank_desc} blank although the lines above it post figures there "
                f"(a gap in the source workbook, not in this extraction)."
            )
            return
    TIE_ERRORS.append(
        f"{fy} {sheet} [{section}] line {line} col '{col}' ({coord}): "
        f"printed {printed!r} but sum of its lines is {expected!r} "
        f"(diff {abs(diff):.2f})"
    )


# ---------------------------------------------------------------------------
# Schedule 1
# ---------------------------------------------------------------------------


def extract_schedule1(fy, grid):
    out = []
    n = len(grid)
    i = 0  # 0-based index; grid[i] is row i+1
    while i < n:
        row = grid[i]
        sched = schedule_marker(row)
        if sched != 1:
            i += 1
            continue

        # --- gather the header block: rows after the marker until the first
        # data row (col A / Row is numeric) or another schedule marker.
        header_rownums = []
        j = i + 1
        while j < n:
            r2 = grid[j]
            a = r2[0] if len(r2) > 0 else None
            desc3 = r2[3] if len(r2) > 3 else None
            no_fund_content = all(v is None for v in r2[4:30])
            if is_num(a):
                break
            if schedule_marker(r2) is not None:
                break
            if a is None and no_fund_content and isinstance(desc3, str) and desc3.strip():
                # a function-group banner (e.g. "School Committee (1110)") with
                # no column content of its own -- this is the first DATA row,
                # not part of the column-heading stitch.
                break
            header_rownums.append(j + 1)
            j += 1

        # section label: descriptive text in col C/D of the header rows,
        # excluding the schedule marker and the repeated "REVENUE AND
        # EXPENDITURE SUMMARY" banner.
        label_parts = []
        for hr in header_rownums:
            r2 = grid[hr - 1]
            for ci in (2, 3):
                v = r2[ci] if ci < len(r2) else None
                if (
                    isinstance(v, str)
                    and v.strip()
                    and not SCHEDULE_MARKER_RE.match(v.strip())
                    and "REVENUE AND EXPENDITURE SUMMARY" not in v.upper()
                    and v.strip().lower() not in ("line", "row")
                ):
                    label_parts.append(v.strip())
        section_label = " / ".join(dict.fromkeys(label_parts))

        # column range: scan header rows + a few data rows for the widest
        # non-empty column.
        max_col = 4
        probe_rows = header_rownums + list(range(j + 1, min(j + 6, n) + 1))
        for hr in probe_rows:
            if 0 < hr <= n:
                r2 = grid[hr - 1]
                for ci, v in enumerate(r2):
                    if v is not None and ci > max_col:
                        max_col = ci
        headings, _cites = stitch_header(grid, header_rownums, 4, max_col)

        # --- parse data rows until the next schedule marker of any number
        inner = {c: 0.0 for c in headings}
        outer = {c: 0.0 for c in headings}
        current_function = ""
        k = j
        while k < n:
            r2 = grid[k]
            if schedule_marker(r2) is not None:
                break
            a = r2[0] if len(r2) > 0 else None
            line = r2[2] if len(r2) > 2 else None
            desc = r2[3] if len(r2) > 3 else None

            if a is None:
                # header / banner row: may update current_function, resets inner
                if isinstance(desc, str):
                    code = trailing_code(desc)
                    if code and not is_object_code(code):
                        current_function = code
                inner = {c: 0.0 for c in inner}
                k += 1
                continue

            desc_s = str(desc).strip() if desc is not None else ""
            amounts = {c: (r2[c] if c < len(r2) else None) for c in headings}
            numeric = {c: v for c, v in amounts.items() if is_num(v)}

            # A bare "Total"/"Totals" (no further text) is this template's
            # occasional alternate spelling of "Sub-total" for a single
            # function group -- e.g. "Food Services (3400)" / line 1489 in
            # the FY23/FY24 files. Only "TOTAL <more text>" is a real
            # section-level grand total.
            is_bare_total = desc_s.lower() in ("total", "totals")
            is_sub = desc_s.lower() == "sub-total" or is_bare_total
            is_tot = (not is_bare_total) and bool(re.match(r"^TOTALS?\s+\S", desc_s.upper()))

            if is_sub or is_tot:
                nested = False
                func_for_row = ""
                if is_tot:
                    m = trailing_code(desc_s)
                    if m and not is_object_code(m):
                        nested = True
                        func_for_row = m
                check_against = inner if is_sub else outer
                for c, printed in numeric.items():
                    coord = f"{get_column_letter(c + 1)}{k + 1}"
                    record_tie(
                        fy, "schedule1", section_label, line, headings[c], check_against[c], printed, coord,
                        headings=headings, amounts=amounts, accum=check_against,
                    )
                    out.append(
                        {
                            "fiscal_year": fy,
                            "line": line,
                            "function_code": func_for_row,
                            "description": desc_s,
                            "column": headings[c],
                            "amount": printed,
                            "section": section_label,
                            "cell": coord,
                        }
                    )
                inner = {c: 0.0 for c in inner}
                if is_tot and not nested:
                    outer = {c: 0.0 for c in outer}
                k += 1
                continue

            # plain raw leaf row
            code = trailing_code(desc_s)
            if code and not is_object_code(code):
                current_function = code
                func_for_row = code
            else:
                func_for_row = current_function

            for c, v in numeric.items():
                inner[c] += v
                outer[c] += v

            if line is not None:
                for c, v in numeric.items():
                    coord = f"{get_column_letter(c + 1)}{k + 1}"
                    out.append(
                        {
                            "fiscal_year": fy,
                            "line": line,
                            "function_code": func_for_row,
                            "description": desc_s,
                            "column": headings[c],
                            "amount": v,
                            "section": section_label,
                            "cell": coord,
                        }
                    )
            k += 1
        i = k
    return out


# ---------------------------------------------------------------------------
# Schedule 3 (district total)
# ---------------------------------------------------------------------------


def extract_schedule3(fy, grid):
    out = []
    n = len(grid)

    # find the header-stitch rows (the "Line" marker row + the ones above it
    # that aren't the 1,2,3... index row) and the data start.
    line_row = None
    for i, row in enumerate(grid):
        v = row[0] if len(row) > 0 else None
        if isinstance(v, str) and v.strip().lower() == "line":
            line_row = i + 1
            break
    if line_row is None:
        raise RuntimeError(f"{fy}: could not find the 'Line' header row in schedule3_total")

    # header rows: scan upward from line_row to the first fully-blank row,
    # capped at 6 rows up (covers the observed 5-row stitch + index row).
    header_rownums = []
    r = line_row - 1
    while r >= 1 and (line_row - r) <= 6:
        row = grid[r - 1]
        if all(v is None for v in row):
            break
        header_rownums.append(r)
        r -= 1
    header_rownums.reverse()

    max_col = 1
    for hr in header_rownums + [line_row, line_row + 1, line_row + 2]:
        if 0 < hr <= n:
            row = grid[hr - 1]
            for ci, v in enumerate(row):
                if v is not None and ci > max_col:
                    max_col = ci
    headings, cites = stitch_header(grid, header_rownums, 2, max_col)
    header_cells = {
        c: "; ".join(f"{coord}={val!r}" for coord, val in cites[c]) for c in headings
    }

    inner = {c: 0.0 for c in headings}
    outer = {c: 0.0 for c in headings}
    current_function = ""
    k = line_row  # first function-group header is ON the "Line" row itself (col B)
    # process the 'Line' row's own col-B text as a header first
    first_desc = grid[line_row - 1][1] if len(grid[line_row - 1]) > 1 else None
    if isinstance(first_desc, str):
        code = trailing_code(first_desc)
        if code and not is_object_code(code):
            current_function = code
    k = line_row  # 0-based data start is line_row (i.e. grid index line_row, 1-based row line_row+1)
    idx = line_row  # grid[idx] is the row right after the 'Line' row
    while idx < n:
        row = grid[idx]
        a = row[0] if len(row) > 0 else None
        desc = row[1] if len(row) > 1 else None

        if a is None:
            if isinstance(desc, str):
                code = trailing_code(desc)
                if code and not is_object_code(code):
                    current_function = code
                elif desc.strip() == "":
                    pass
            inner = {c: 0.0 for c in inner}
            # a fully blank row (no description either) ends the schedule
            if desc is None and all(v is None for v in row):
                break
            idx += 1
            continue

        if not is_num(a):
            idx += 1
            continue

        line = a
        desc_s = str(desc).strip() if desc is not None else ""
        amounts = {c: (row[c] if c < len(row) else None) for c in headings}
        numeric = {c: v for c, v in amounts.items() if is_num(v)}

        is_bare_total = desc_s.lower() in ("total", "totals")
        is_sub = desc_s.lower() == "sub-total" or is_bare_total
        is_tot = (not is_bare_total) and bool(re.match(r"^TOTALS?\s+\S", desc_s.upper()))

        if is_sub or is_tot:
            nested = False
            func_for_row = ""
            if is_tot:
                m = trailing_code(desc_s)
                if m and not is_object_code(m):
                    nested = True
                    func_for_row = m
            check_against = inner if is_sub else outer
            for c, printed in numeric.items():
                coord = f"{get_column_letter(c + 1)}{idx + 1}"
                record_tie(
                    fy, "schedule3", "district total", line, headings[c], check_against[c], printed, coord,
                    headings=headings, amounts=amounts, accum=check_against,
                )
                out.append(
                    {
                        "fiscal_year": fy,
                        "line": line,
                        "function_code": func_for_row,
                        "description": desc_s,
                        "column": headings[c],
                        "amount": printed,
                        "header_cells": header_cells[c],
                        "cell": coord,
                    }
                )
            inner = {c: 0.0 for c in inner}
            if is_tot and not nested:
                outer = {c: 0.0 for c in outer}
            if is_tot and desc_s.upper().startswith("TOTAL INSTRUCTIONAL SERVICES"):
                # this is the schedule's own grand total; stop here.
                idx += 1
                break
            idx += 1
            continue

        code = trailing_code(desc_s)
        if code and not is_object_code(code):
            current_function = code
            func_for_row = code
        else:
            func_for_row = current_function

        for c, v in numeric.items():
            inner[c] += v
            outer[c] += v
        for c, v in numeric.items():
            coord = f"{get_column_letter(c + 1)}{idx + 1}"
            out.append(
                {
                    "fiscal_year": fy,
                    "line": line,
                    "function_code": func_for_row,
                    "description": desc_s,
                    "column": headings[c],
                    "amount": v,
                    "header_cells": header_cells[c],
                    "cell": coord,
                }
            )
        idx += 1

    return out


# ---------------------------------------------------------------------------
# Net School Spending (reports sheet, actual-year block only)
# ---------------------------------------------------------------------------

NSS_LINE_RE = re.compile(r"^\s*(\d+[a-z]?)[\.\)]\s*(.*)$")


def extract_nss(fy, grid):
    """
    The 'reports' sheet carries TWO NSS blocks back to back: the current
    year's ACTUAL Net School Spending (numbered lines 1-22), then the NEXT
    fiscal year's BUDGETED Net School Spending (numbered lines 23+, restarting
    the same column layout). Only the first (actual) block is extracted here
    -- CLAUDE.md rule 1 forbids mixing a budget figure into an actuals
    calculation, and the two blocks are otherwise indistinguishable once
    stripped of their banner row.
    """
    n = len(grid)
    short = "FY" + fy[-2:]
    start = None
    for i, row in enumerate(grid):
        v = row[1] if len(row) > 1 else None
        if isinstance(v, str) and re.match(r"^\s*" + re.escape(short) + r"\s+Net School Spending", v, re.I):
            start = i + 2  # banner spans 2 rows (title, then "162 Lunenburg")
            break
    if start is None:
        raise RuntimeError(f"{fy}: could not find the 'Net School Spending' banner in reports sheet")

    out = []
    acc = {}  # line_no (without letter) -> {'sc':.., 'ct':.., 'total':..}
    idx = start
    while idx < n:
        row = grid[idx]
        label = row[1] if len(row) > 1 else None
        if not isinstance(label, str) or not label.strip():
            idx += 1
            if idx < n:
                nxt = grid[idx][1] if len(grid[idx]) > 1 else None
                if isinstance(nxt, str) and "Budgeted Net School Spending" in nxt:
                    break
            continue
        m = NSS_LINE_RE.match(label)
        if not m:
            if "Budgeted Net School Spending" in label:
                break
            idx += 1
            continue
        line_no, line_label = m.group(1), m.group(2).strip()
        sc = row[2] if len(row) > 2 else None
        ct = row[3] if len(row) > 3 else None
        note = row[4] if len(row) > 4 else None
        total = row[5] if len(row) > 5 else None
        note_s = note.strip() if isinstance(note, str) and note.strip() else ""
        out.append(
            {
                "fiscal_year": fy,
                "line": line_no,
                "label": line_label,
                "school_committee": sc if is_num(sc) else "",
                "city_town": ct if is_num(ct) else "",
                "total": total if is_num(total) else "",
                "note": note_s,
                "cell_total": f"F{idx + 1}",
            }
        )
        base = re.match(r"^(\d+)", line_no).group(1)
        acc.setdefault(base, {"sc": None, "ct": None, "total": None, "label": line_label})
        if "a" not in line_no and "b" not in line_no and "c" not in line_no:
            acc[base]["sc"] = sc if is_num(sc) else acc[base]["sc"]
            acc[base]["ct"] = ct if is_num(ct) else acc[base]["ct"]
            acc[base]["total"] = total if is_num(total) else acc[base]["total"]
        idx += 1
        if idx < n:
            nxt = grid[idx][1] if len(grid[idx]) > 1 else None
            if isinstance(nxt, str) and "Budgeted Net School Spending" in nxt:
                break

    # --- arithmetic checks (DONE WHEN 2), using the literal relationships
    # the printed labels state, and -- for lines 19-22, which involve a
    # conditional/rounding -- the exact formulas read directly from the
    # workbook (cited in the final report).
    def g(line, col):
        for r in out:
            if r["line"] == line:
                v = r[col]
                return v if is_num(v) else None
        return None

    def check(label, expected, printed, tol=TOL):
        if printed is None:
            return
        if expected is None:
            return
        if abs(expected - printed) > tol:
            TIE_ERRORS.append(
                f"{fy} nss: {label}: printed {printed!r} but derived {expected!r} "
                f"(diff {abs(expected - printed):.2f})"
            )

    for col in ("school_committee", "city_town", "total"):
        ones_through_twelve = [g(str(ln), col) for ln in range(1, 13)]
        if all(v is not None for v in ones_through_twelve if v is not None) and any(
            v is not None for v in ones_through_twelve
        ):
            s = sum(v for v in ones_through_twelve if v is not None)
            check(f"13 ({col}) = sum(1..12)", s, g("13", col))
        a14, b14 = g("14a", col), g("14b", col)
        if a14 is not None or b14 is not None:
            check(f"14c ({col}) = 14a+14b", (a14 or 0) + (b14 or 0), g("14c", col))
        l13, l14c = g("13", col), g("14c", col)
        if l13 is not None and l14c is not None:
            check(f"15 ({col}) = max(13-14c,0)", max(l13 - l14c, 0), g("15", col))

    l16, l17 = g("16", "total"), g("17", "total")
    if l16 is not None and l17 is not None:
        check("18 (total) = 16+17", l16 + l17, g("18", "total"))
    l15, l18 = g("15", "total"), g("18", "total")
    if l15 is not None and l18 is not None:
        check("19 (total) = max(18-15,0)", max(l18 - l15, 0), g("19", "total"))
    l19 = g("19", "total")
    if l19 is not None and l16:
        pct = round(l19 / l16, 4)
        check("20 (total) = round(19/16,4)", pct, g("20", "total"), tol=0.0005)
        l20 = g("20", "total")
        expected21 = l19 if (l20 or pct) <= 0.05 else round(0.05 * l16, 0)
        check("21 (total) = 19 if 20<=5% else round(5%*16)", expected21, g("21", "total"))
    l21 = g("21", "total")
    if l19 is not None and l21 is not None:
        check("22 (total) = max(19-21,0)", max(l19 - l21, 0), g("22", "total"))

    return out


# ---------------------------------------------------------------------------
# DESE published-figure comparison (DONE WHEN 4)
# ---------------------------------------------------------------------------


def compare_to_dese(s1_rows, nss_rows):
    """
    Returns a list of human-readable comparison lines. Does not affect
    whether the script writes -- DONE WHEN 4 only asks that this be reported,
    not that it block the build.
    """
    report = []

    # --- function-code expenditures: sources/state-dese/district-expenditures-by-function.xlsx
    if DESE_FUNCTION_FILE.exists():
        wb = openpyxl.load_workbook(DESE_FUNCTION_FILE, data_only=True, read_only=True)
        ws = wb["Data"]
        hdr = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        idx = {name: i for i, name in enumerate(hdr)}
        dese = {}  # (sy, func_code) -> (gen_fund, grnts_revolv, tot_exp)
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[idx["DIST_CODE"]] != DIST_CODE:
                continue
            fc = row[idx["FUNC_CODE"]]
            sy = row[idx["SY"]]
            dese[(sy, str(fc))] = (
                row[idx["GEN_FUND"]],
                row[idx["GRNTS_REVOLV"]],
                row[idx["TOT_EXP"]],
            )
        wb.close()

        report.append(f"DESE 'District Expenditures by Function Code' is held ({DESE_FUNCTION_FILE}).")
        for fy_label, sy in (("FY2024", "2024"), ("FY2023", "2023")):
            ours = {}
            for r in s1_rows:
                if r["fiscal_year"] != fy_label:
                    continue
                if r["column"] != "TOTAL" and r["column"].strip().upper() != "TOTAL":
                    continue
                fc = r["function_code"]
                if not fc or "," in fc:
                    continue
                if r["description"].lower() == "sub-total" or r["description"].upper().startswith("TOTAL"):
                    continue
                try:
                    amt = float(r["amount"] or 0)
                except (TypeError, ValueError):
                    continue
                ours[fc] = ours.get(fc, 0.0) + amt
            matched = mismatched = missing = 0
            diffs = []
            dese_codes = {fc for (sy2, fc) in dese if sy2 == sy}
            for fc in sorted(dese_codes, key=lambda x: (len(x), x)):
                gen, grnts, tot = dese[(sy, fc)]
                ours_amt = ours.get(fc)
                if ours_amt is None:
                    missing += 1
                    continue
                if tot is not None and abs((tot or 0) - ours_amt) <= 1.0:
                    matched += 1
                else:
                    mismatched += 1
                    diffs.append(f"    function {fc}: DESE TOT_EXP={tot!r} vs ours={ours_amt!r}")
            report.append(
                f"  {fy_label} (SY{sy}) vs DESE, by function code (our 'TOTAL' column, "
                f"summed across Schedule 1's by-school-committee + by-city/town + grants "
                f"sub-blocks): {matched} match (within $1), {mismatched} differ, "
                f"{missing} functions DESE prints that we didn't extract a 'TOTAL' amount for."
            )
            report.extend(diffs[:15])
            if len(diffs) > 15:
                report.append(f"    ...and {len(diffs) - 15} more differences.")
    else:
        report.append("DESE function-code expenditures file not held; no comparison made.")

    # --- Required / Actual Net School Spending: dese-ch70-foundation-nss.xlsx
    if DESE_NSS_FILE.exists():
        wb = openpyxl.load_workbook(DESE_NSS_FILE, data_only=True, read_only=True)
        ws = wb["Data"]
        years = set()
        lun = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[1] != DIST_CODE:
                continue
            years.add(row[0])
            lun[row[0]] = (row[3], row[4])  # REQ_NSS_AMT, ACTL_NSS_AMT
        wb.close()
        report.append(
            f"DESE 'Chapter 70 Foundation Budget and Net School Spending' is held "
            f"({DESE_NSS_FILE}); years SY{min(years)}-SY{max(years)}."
        )
        for fy_label, sy in (("FY2024", "2024"), ("FY2023", "2023")):
            if sy in lun:
                req, act = lun[sy]
                report.append(f"  {fy_label} (SY{sy}): DESE publishes REQ_NSS_AMT={req!r}, ACTL_NSS_AMT={act!r}.")
            else:
                report.append(
                    f"  {fy_label} (SY{sy}): NOT in this DESE dataset (it stops at SY{max(years)}); "
                    f"no comparison possible."
                )
        # the prior-year reference figures printed in the 'reports' sheet side panel
        # (not part of the numbered-line NSS block, so not in eoyr-nss.csv) corroborate
        # SY2022 exactly where it is checkable -- see final report.
    else:
        report.append("DESE Chapter 70 / NSS file not held; no comparison made.")

    return report


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only; do not write")
    args = ap.parse_args()

    all_s1, all_s3, all_nss = [], [], []
    for fy, path in FILES.items():
        if not path.exists():
            print(f"ERROR: {fy} source not found: {path}", file=sys.stderr)
            sys.exit(1)
        eoy_grid = load_grid(path, EOY_SHEET[fy])
        all_s1.extend(extract_schedule1(fy, eoy_grid))

        s3_grid = load_grid(path, "schedule3_total")
        all_s3.extend(extract_schedule3(fy, s3_grid))

        rep_grid = load_grid(path, "reports")
        all_nss.extend(extract_nss(fy, rep_grid))

    if TIE_ERRORS:
        print(f"REFUSING TO WRITE: {len(TIE_ERRORS)} tie-out / arithmetic check(s) failed:", file=sys.stderr)
        for e in TIE_ERRORS:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    print(f"All tie-outs and NSS arithmetic checks passed ({len(all_s1)} schedule-1 rows, "
          f"{len(all_s3)} schedule-3 rows, {len(all_nss)} NSS lines).")
    if TIE_WARNINGS:
        print(f"\n{len(TIE_WARNINGS)} tie-out(s) did not match but are fully explained by a blank "
              f"cell in the source workbook (not blocking; cited below):")
        for w in TIE_WARNINGS:
            print(f"  ! {w}")

    dese_report = compare_to_dese(all_s1, all_nss)
    print("\n--- DESE published-figure comparison ---")
    for line in dese_report:
        print(line)

    if args.check:
        print("\n--check: not writing (verification only).")
        return

    write_csv(
        OUT_S1,
        all_s1,
        ["fiscal_year", "line", "function_code", "description", "column", "amount", "section", "cell"],
    )
    write_csv(
        OUT_S3,
        all_s3,
        ["fiscal_year", "line", "function_code", "description", "column", "amount", "header_cells", "cell"],
    )
    write_csv(
        OUT_NSS,
        all_nss,
        ["fiscal_year", "line", "label", "school_committee", "city_town", "total", "note", "cell_total"],
    )
    print(f"\nWrote {OUT_S1}")
    print(f"Wrote {OUT_S3}")
    print(f"Wrote {OUT_NSS}")


if __name__ == "__main__":
    main()
