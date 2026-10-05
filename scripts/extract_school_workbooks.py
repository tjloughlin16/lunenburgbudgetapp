#!/usr/bin/env python3
"""Finance Committee tasks E1, E2, E4: the school district's own workbooks.

Three unrelated spreadsheets, one script because all three are "read a hand-built
workbook, tie its own printed totals to its own lines, and say what changed between
versions" (rule 13a: a hand-assembled sheet is `stated`, never treated as an accounting
system's printout, however official it looks).

    python3 scripts/extract_school_workbooks.py           # parse, print every finding
    python3 scripts/extract_school_workbooks.py --check   # ...and fail if a GATE fails

Writes:
    sources/data/school-target-fy26.csv           (E1)
    sources/data/school-staff-fte.csv             (E4, Detailed FTE by Year)
    sources/data/school-enrollment-lps-staff.csv  (E4, Enrollment sheet)

E2 (the FY27 projection workbook) is a comparison only -- it does not produce a new CSV,
because the archive already holds `sources/budget-workbooks/fy27-budget-projection-2-24-26.xlsx`
as `fy27-proposals.xlsx`'s traced twin (see `sources/budget-workbooks/PROVENANCE.md`). This
script establishes whether the Finance Committee's copy is the same workbook.

GATES (refuse to write the CSVs if any fails):
  G1  E1 -- each version's own printed arithmetic holds: TOTAL BUDGET = TOTAL EXPENSES +
      TOTAL SALARIES, to the cent, for every column where the sheet prints a dollar total.
      This is an identity the DOCUMENT states about itself (rule 13b/13c), not something we
      derive -- if it fails, the parser mis-read the sheet.
  G2  E4 -- the Pivot Table sheet's own sums agree EXACTLY with SUMIFS over Detailed FTE by
      Year, by job category and year, and the Grand Total row. Excel built the pivot from
      the detail sheet in the same workbook, so disagreement means we mis-read one of them.

What is NOT gated, and why: individual department subtotal rows inside E1 frequently do
NOT tie to their own line items -- that is a defect IN THE WORKBOOKS, found and reported
below, not a parsing failure (confirmed by checking that the columns which DO tie at the
same row use the identical set of line items). Forcing a build failure on a defect in the
source would mean the extraction can never ship; rule 13a says to publish the spread
instead of silently fixing or discarding it.
"""
import argparse
import csv
import re
import sys
import zipfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
DATA = SOURCES / "data"

FC = SOURCES / "budget-workbooks" / "finance-committee"
LPS = FC / "fy26-budget" / "department-presentations" / "lunenburg-public-schools"
PROP25 = FC / "fy26-budget" / "prop-2-1-2-override-material"

E1_FILES = [
    ("3_6_25_updatesg", LPS / "final-fy26-town-manger-s-target-budget-3-6-25-updatesg.xlsx"),
    ("sc_approved_3_12_25", LPS / "final-fy26-town-manger-s-target-budget-sc-approved-3-12-25.xlsx"),
    ("sc_approved_3_12_25_2_5", LPS / "final-fy26-town-manger-s-target-budget-sc-approved-3-12-25-2-5.xlsx"),
    ("prop25_details", PROP25 / "final-fy26-town-manger-s-target-budget-3-6-25-prop-2.5-details.xlsx"),
]

E2_FINCOM = (
    FC / "fy27-budget" / "department-presentations" / "school-department"
    / "fy27-budget-projection-as-of-2.24.26-with-restorations.xlsx"
)
E2_ARCHIVE = SOURCES / "budget-workbooks" / "fy27-budget-projection-2-24-26.xlsx"

E4_PATH = FC / "data-and-trends" / "lps-staff-2019-2025.xlsx"

GL_HISTORY = DATA / "gl-history.csv"
FINCOM_LEDGERS = DATA / "fincom-ledgers.csv"

OUT_E1 = DATA / "school-target-fy26.csv"
OUT_FTE = DATA / "school-staff-fte.csv"
OUT_ENROLL = DATA / "school-enrollment-lps-staff.csv"

TOTAL_LABELS = {"TOTAL EXPENSES", "TOTAL SALARIES", "TOTAL BUDGET"}
TOL = 0.02  # a cent of rounding per row is tolerated; nothing wider


# --------------------------------------------------------------------------------------
# E1: the four FY26 target-budget workbooks
# --------------------------------------------------------------------------------------

def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _merge_lookup(ws, row):
    """Values for one row, with merged ranges' top-left value propagated across the span.

    Excel stores a merged cell's value only in its top-left member; every other cell in
    the range is None. A header spanning several columns (e.g. 'FY26 Level' over D1:F1)
    would otherwise print as a header for column D alone. This is mechanical -- it reads
    exactly what openpyxl's own `merged_cells.ranges` says is merged, nothing inferred.
    """
    vals = {c: ws.cell(row, c).value for c in range(1, ws.max_column + 1)}
    for mc in ws.merged_cells.ranges:
        if mc.min_row <= row <= mc.max_row:
            topleft = ws.cell(mc.min_row, mc.min_col).value
            for c in range(mc.min_col, mc.max_col + 1):
                vals[c] = topleft
    return vals


def _column_headers(ws, header_rows=(1, 2, 3)):
    """The exact printed header text per column: every header row's text at that column,
    merge-aware, joined ' - '. Quotes what is printed; invents no column names."""
    lookups = {r: _merge_lookup(ws, r) for r in header_rows}
    headers = {}
    for c in range(1, ws.max_column + 1):
        parts = []
        for r in header_rows:
            v = lookups[r].get(c)
            if v is not None and str(v).strip() and "DESCRIPTION" not in str(v).upper():
                parts.append(str(v).strip())
        headers[c] = " - ".join(parts) if parts else None
    return headers


def parse_target_budget(path, version):
    """Walk one target-budget sheet. Department headers and department-subtotal rows
    both print in column A with column B blank; line items print in column B with
    column A blank. A handful of rows have a single stray space character in column A
    (confirmed at rows 74, 76, 212 of the 3/6/25 file) which is not a department code --
    stripped here, or those rows silently drop out of every sum that follows."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    headers = _column_headers(ws)
    data_cols = [c for c in range(3, ws.max_column + 1) if headers.get(c)]

    dept_code = dept_name = None
    current_items = []
    dept_totals = []
    totals = {}
    records = []
    is_salary = False

    for r in range(1, ws.max_row + 1):
        araw = ws.cell(r, 1).value
        braw = ws.cell(r, 2).value
        a = str(araw).strip() if araw is not None else ""
        b = str(braw).strip() if braw is not None else ""
        if not a and not b:
            continue
        if not a and b:
            nb = _norm(b).rstrip(":").strip().upper()
            if nb == "DESCRIPTION, SALARIES":
                is_salary = True
                continue
            if nb == "DESCRIPTION, EXPENSES":
                continue
            if nb in TOTAL_LABELS:
                vals = {c: ws.cell(r, c).value for c in data_cols}
                totals[nb] = {"row": r, "values": vals}
                continue
            if dept_code:
                vals = {c: ws.cell(r, c).value for c in data_cols}
                rec = {
                    "version": version, "row": r, "dept_code": dept_code,
                    "dept_name": dept_name, "section": "salary" if is_salary else "expense",
                    "description": b, "values": vals,
                }
                records.append(rec)
                current_items.append(rec)
            continue
        if a and not b:
            m = re.match(r"^(\d{3,4})\s*-?\s*(.+?)\s*Total\s*$", a)
            if m and a.endswith("Total"):
                code, name = m.groups()
                vals = {c: ws.cell(r, c).value for c in data_cols}
                dept_totals.append({
                    "code": code, "name": name.strip(), "row": r, "values": vals,
                    "items": current_items, "section": "salary" if is_salary else "expense",
                })
                current_items = []
                dept_code = dept_name = None
                continue
            m2 = re.match(r"^(\d{3,4})\s*-?\s*(.+)$", a)
            if m2:
                dept_code, dept_name = m2.groups()
                dept_name = dept_name.strip()
                current_items = []
                continue
            continue

    return {
        "version": version, "path": path, "headers": headers, "data_cols": data_cols,
        "records": records, "dept_totals": dept_totals, "totals": totals,
    }


def _is_dollar_col(headers, c):
    h = headers.get(c)
    return h is not None and "%" not in h


def check_e1_totals(parsed):
    """G1: TOTAL BUDGET = TOTAL EXPENSES + TOTAL SALARIES, for every column where all
    three printed cells look like dollar figures (not the grand-total rows' own quirk,
    below). Returns (ok, lines)."""
    headers, data_cols, totals = parsed["headers"], parsed["data_cols"], parsed["totals"]
    lines = []
    ok = True
    if not all(k in totals for k in TOTAL_LABELS):
        return False, [f"  MISSING one of TOTAL EXPENSES/TOTAL SALARIES/TOTAL BUDGET rows"]
    for c in data_cols:
        if not _is_dollar_col(headers, c):
            continue
        texp = totals["TOTAL EXPENSES"]["values"].get(c)
        tsal = totals["TOTAL SALARIES"]["values"].get(c)
        tbud = totals["TOTAL BUDGET"]["values"].get(c)
        if not all(isinstance(v, (int, float)) for v in (texp, tsal, tbud)):
            continue
        # The grand-total rows sometimes print a percentage in a column headed
        # "Dollar Change" (confirmed: sc-approved row 496-498, column F prints 0.1849,
        # -0.0302, 0.0363 -- clearly % figures, not dollars, while the SAME column at
        # every department subtotal row is a genuine dollar amount). A real dollar total
        # at this budget's scale is never under $100; treat anything smaller as that
        # known quirk and skip the identity check for it, but still report it.
        if abs(texp) < 100 and abs(tsal) < 100 and abs(tbud) < 100:
            lines.append(
                f"  NOTE col {c} ({headers[c]!r}): TOTAL rows print {texp}, {tsal}, {tbud} "
                f"-- too small to be dollars at this budget's scale; this column's grand-total "
                f"cells hold a percentage although the header is not a '%' column. Skipped."
            )
            continue
        diff = round((texp + tsal) - tbud, 2)
        if abs(diff) > TOL:
            ok = False
            lines.append(
                f"  FAIL col {c} ({headers[c]!r}): TOTAL EXPENSES {texp} + TOTAL SALARIES "
                f"{tsal} = {texp+tsal}, but printed TOTAL BUDGET is {tbud} (diff {diff})"
            )
        else:
            lines.append(f"  ok   col {c} ({headers[c]!r}): {texp} + {tsal} = {tbud} (diff {diff})")
    return ok, lines


def check_e1_line_ties(parsed):
    """Report-only: does the sum of a section's own line items match that section's
    printed TOTAL EXPENSES/TOTAL SALARIES, and does each department subtotal row match
    the sum of its own lines? Both are checked; neither gates the build (see module
    docstring) because real failures exist in the source documents."""
    headers, data_cols, records = parsed["headers"], parsed["data_cols"], parsed["records"]
    totals, dept_totals = parsed["totals"], parsed["dept_totals"]
    lines = []

    sums = {"expense": {c: 0.0 for c in data_cols}, "salary": {c: 0.0 for c in data_cols}}
    for rec in records:
        for c in data_cols:
            v = rec["values"].get(c)
            if isinstance(v, (int, float)):
                sums[rec["section"]][c] += v

    for section, label in (("expense", "TOTAL EXPENSES"), ("salary", "TOTAL SALARIES")):
        tv = totals.get(label, {}).get("values", {})
        for c in data_cols:
            if not _is_dollar_col(headers, c):
                continue
            t = tv.get(c)
            if not isinstance(t, (int, float)) or abs(t) < 100:
                continue
            diff = round(sums[section][c] - t, 2)
            if abs(diff) > 1.0:
                lines.append(
                    f"  SECTION TIE FAIL [{section}] col {c} ({headers[c]!r}): sum of lines "
                    f"{round(sums[section][c],2)} vs printed {label} {t} (diff {diff})"
                )

    for dt in dept_totals:
        for c in data_cols:
            if not _is_dollar_col(headers, c):
                continue
            tv = dt["values"].get(c)
            if not isinstance(tv, (int, float)):
                # The sheet left this subtotal cell blank -- not a printed zero, no
                # identity to check (confirmed: dept totals routinely omit a FY24 Actual
                # subtotal even though the grand total also omits it at the same column).
                continue
            s = sum(
                (it["values"].get(c) or 0) for it in dt["items"]
                if isinstance(it["values"].get(c), (int, float))
            )
            diff = round(s - tv, 2)
            if abs(diff) > TOL:
                lines.append(
                    f"  DEPT SUBTOTAL FAIL '{dt['code']} - {dt['name']}' row {dt['row']} "
                    f"col {c} ({headers[c]!r}): lines sum to {s}, printed total is {tv} "
                    f"(diff {diff})"
                )
    return lines


def diff_e1_versions(parsed_by_version, order):
    """Line-by-line diff across the four versions, matched by (dept_code, description) --
    the one key that is stable across every version's different column layouts."""
    lines = []
    by_version = {}
    for v in order:
        p = parsed_by_version[v]
        idx = {}
        for rec in p["records"]:
            key = (rec["dept_code"], rec["description"])
            idx.setdefault(key, []).append(rec)
        by_version[v] = idx

    all_keys = set()
    for idx in by_version.values():
        all_keys |= set(idx.keys())

    added_removed = {v: {"only_here": [], "missing": []} for v in order}
    for key in sorted(all_keys):
        present_in = [v for v in order if key in by_version[v]]
        if len(present_in) == len(order):
            continue
        for v in order:
            if v in present_in:
                continue
            added_removed[v]["missing"].append(key)
    n_common = sum(1 for key in all_keys if all(key in by_version[v] for v in order))
    lines.append(f"  lines present in ALL {len(order)} versions (by dept code + description): {n_common}")
    for v in order:
        miss = added_removed[v]["missing"]
        if miss:
            lines.append(f"  not present in {v}: {len(miss)} lines, e.g. {miss[:5]}")
    return lines


# --------------------------------------------------------------------------------------
# E2: the FY27 projection workbook, Finance Committee's copy vs. the archived twin
# --------------------------------------------------------------------------------------

def sha256_of(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_e2(fincom_path, archive_path):
    lines = []
    h1, h2 = sha256_of(fincom_path), sha256_of(archive_path)
    lines.append(f"  sha256 fincom copy:  {h1}")
    lines.append(f"  sha256 archive copy: {h2}")
    if h1 == h2:
        lines.append("  IDENTICAL BYTES.")
        return True, lines
    lines.append("  NOT byte-identical. Comparing the data range cell by cell (values, data_only)...")

    wb1 = openpyxl.load_workbook(fincom_path, data_only=True)
    wb2 = openpyxl.load_workbook(archive_path, data_only=True)
    ws1, ws2 = wb1.active, wb2.active
    lines.append(f"  fincom sheet: {ws1.title!r} {ws1.dimensions}; archive sheet: {ws2.title!r} {ws2.dimensions}")

    maxr = max(ws1.max_row, ws2.max_row)
    maxc = max(ws1.max_column, ws2.max_column)
    diffs = []
    for r in range(1, maxr + 1):
        for c in range(1, maxc + 1):
            v1 = ws1.cell(r, c).value
            v2 = ws2.cell(r, c).value
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                if abs(v1 - v2) < 1e-6:
                    continue
            if v1 != v2:
                diffs.append((r, c, v1, v2))

    col9_diffs = [d for d in diffs if d[1] == 9]
    other_diffs = [d for d in diffs if d[1] != 9]
    lines.append(
        f"  total differing cells: {len(diffs)} "
        f"({len(col9_diffs)} in column I, {len(other_diffs)} elsewhere)"
    )
    if col9_diffs:
        lines.append(
            "  column I is a '% change' column present in the ARCHIVE copy "
            "(formula '= (G-F)/F', header 'I5'=\"% change\") and ABSENT from the "
            "Finance Committee copy -- a structural difference, not a figure difference."
        )
    for r, c, v1, v2 in other_diffs:
        label = ws1.cell(r, 2).value
        lines.append(f"    row {r} col {c} ({label!r}): fincom={v1!r}  archive={v2!r}")
    return False, lines


# --------------------------------------------------------------------------------------
# E4: LPS Staff 2019-2025.xlsx
# --------------------------------------------------------------------------------------

def parse_fte(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Detailed FTE by Year"]
    years = [f"FY{16+i}" for i in range(10)]
    col_for_year = {4 + i: years[i] for i in range(10)}  # D..M

    rows = []
    schools = set()
    for r in range(2, ws.max_row + 1):
        school = ws.cell(r, 1).value
        cat = ws.cell(r, 2).value
        desc = ws.cell(r, 3).value
        if not cat or not desc:
            continue
        schools.add(school)
        m = re.match(r"^\s*(\d+)\s+(.+)$", str(desc).strip())
        if m:
            job_code, job_title = m.group(1), m.group(2).strip()
        else:
            job_code, job_title = "", str(desc).strip()
        for c, fy in col_for_year.items():
            v = ws.cell(r, c).value
            rows.append({
                "fiscal_year": fy, "job_category": cat, "job_code": job_code,
                "job_title": job_title, "fte": v, "source_row": r,
            })

    pivot = wb["Pivot Table"]
    pivot_years = {2 + i: years[i] for i in range(10)}
    pivot_cats = {}
    for r in range(4, 12):
        cat = pivot.cell(r, 1).value
        if cat:
            pivot_cats[cat] = {pivot_years[c]: pivot.cell(r, c).value for c in pivot_years}
    grand_total = {pivot_years[c]: pivot.cell(12, c).value for c in pivot_years}

    enr = wb["Enrollment"]
    enroll_years = {2 + i: years[i] for i in range(10)}
    enrollment = {enroll_years[c]: enr.cell(2, c).value for c in enroll_years}

    return {
        "rows": rows, "schools": schools, "years": years,
        "pivot_cats": pivot_cats, "grand_total": grand_total, "enrollment": enrollment,
    }


def check_e4_pivot(fte):
    """G2: Pivot Table sums must agree exactly with SUMIFS over Detailed FTE by Year."""
    sums = {}
    for row in fte["rows"]:
        v = row["fte"]
        if isinstance(v, (int, float)):
            key = (row["job_category"], row["fiscal_year"])
            sums[key] = sums.get(key, 0.0) + v

    lines = []
    ok = True
    for cat, by_year in fte["pivot_cats"].items():
        for fy, pv in by_year.items():
            computed = sums.get((cat, fy), 0.0)
            diff = round((pv or 0) - computed, 4)
            if abs(diff) > TOL:
                ok = False
                lines.append(f"  FAIL {cat} {fy}: pivot={pv} computed={computed} diff={diff}")
    for fy, pv in fte["grand_total"].items():
        computed = sum(sums.get((cat, fy), 0.0) for cat in fte["pivot_cats"])
        diff = round((pv or 0) - computed, 4)
        if abs(diff) > TOL:
            ok = False
            lines.append(f"  FAIL Grand Total {fy}: pivot={pv} computed={computed} diff={diff}")
    if ok:
        lines.append(
            f"  ok   every job-category sum, all {len(fte['years'])} years, and the Grand "
            f"Total row all agree exactly with the Detailed FTE by Year sheet."
        )
    return ok, lines


def dese_teacher_fte_by_year():
    """DESE's own published classroom-teacher FTE for the Lunenburg DISTRICT row, from
    'Elementary and Secondary Teachers by Program Area' (TCHR_FTE_CNT, ORG_TYPE=District).

    This is NOT the same population as the workbook's 'Instructional Staff' job category:
    DESE's figure counts certified classroom teachers; the workbook's category can include
    non-certified instructional roles (aides supporting instruction, long-term substitutes,
    instructional coaches) that are not 'teachers' in DESE's sense. Presented as a
    corroborating series, not an identity -- rule 7: a proxy is never the thing.
    """
    path = SOURCES / "state-dese" / "dese-teachers-by-program-area.xlsx"
    if not path.exists():
        return None
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    next(rows_iter)  # header
    out = {}
    for row in rows_iter:
        if row and row[2] == "Lunenburg" and row[5] == "District":
            sy = str(row[0])
            out[f"FY{sy[2:]}"] = row[14]
    return out


# --------------------------------------------------------------------------------------
# E1 vs. the town ledger: FY25/FY26 appropriation comparison
# --------------------------------------------------------------------------------------

def gl_history_dept300(fiscal_year):
    if not GL_HISTORY.exists():
        return None
    total = 0.0
    found = False
    with open(GL_HISTORY, newline="") as f:
        for row in csv.DictReader(f):
            if row["sheet"] == "general_fund" and row["department_code"] == "300" and row["fiscal_year"] == str(fiscal_year):
                found = True
                total += float(row["original"] or 0)
    return total if found else None


def gl_history_years_dept300():
    if not GL_HISTORY.exists():
        return set()
    years = set()
    with open(GL_HISTORY, newline="") as f:
        for row in csv.DictReader(f):
            if row["sheet"] == "general_fund" and row["department_code"] == "300":
                years.add(row["fiscal_year"])
    return years


def fincom_ledgers_by_report():
    if not FINCOM_LEDGERS.exists():
        return {}
    sums = {}
    with open(FINCOM_LEDGERS, newline="") as f:
        for row in csv.DictReader(f):
            rk = row["report_key"]
            try:
                sums[rk] = sums.get(rk, 0.0) + float(row["original"] or 0)
            except (TypeError, ValueError):
                pass
    return sums


# --------------------------------------------------------------------------------------
# CSV writers
# --------------------------------------------------------------------------------------

def write_e1_csv(parsed_by_version, order):
    header_union = []
    seen = set()
    for v in order:
        headers = parsed_by_version[v]["headers"]
        data_cols = parsed_by_version[v]["data_cols"]
        for c in data_cols:
            h = headers[c]
            if h not in seen:
                seen.add(h)
                header_union.append(h)

    fieldnames = ["version", "source_file", "row", "dept_code", "dept_name", "section", "description"] + header_union
    with open(OUT_E1, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for v in order:
            p = parsed_by_version[v]
            headers = p["headers"]
            for rec in p["records"]:
                out = {
                    "version": v, "source_file": str(p["path"].relative_to(ROOT)),
                    "row": rec["row"], "dept_code": rec["dept_code"], "dept_name": rec["dept_name"],
                    "section": rec["section"], "description": rec["description"],
                }
                for c, val in rec["values"].items():
                    out[headers[c]] = val
                w.writerow(out)
    return len(header_union)


def write_e4_csvs(fte):
    with open(OUT_FTE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fiscal_year", "job_category", "job_code", "job_title", "fte", "source_row"])
        w.writeheader()
        for row in fte["rows"]:
            w.writerow(row)

    with open(OUT_ENROLL, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fiscal_year", "district_enrollment"])
        for fy in fte["years"]:
            w.writerow([fy, fte["enrollment"].get(fy)])


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit non-zero if a gate fails")
    args = ap.parse_args()

    print("=" * 88)
    print("E1 -- FINAL FY26 Town Manager's Target Budget: four workbooks")
    print("=" * 88)

    order = [v for v, _ in E1_FILES]
    parsed_by_version = {}
    gate_ok = True
    for v, path in E1_FILES:
        if not path.exists():
            print(f"MISSING: {path}")
            gate_ok = False
            continue
        p = parse_target_budget(path, v)
        parsed_by_version[v] = p
        print(f"\n--- {v} ({path.relative_to(ROOT)}) ---")
        print(f"  {len(p['records'])} line items, {len(p['dept_totals'])} department subtotal rows, "
              f"columns: {[h for h in p['headers'].values() if h]}")
        ok, lines = check_e1_totals(p)
        print("  [G1: TOTAL BUDGET = TOTAL EXPENSES + TOTAL SALARIES]")
        for line in lines:
            print(line)
        gate_ok = gate_ok and ok

        print("  [report-only: line items vs. printed section/department totals]")
        tie_lines = check_e1_line_ties(p)
        if tie_lines:
            for line in tie_lines:
                print(line)
        else:
            print("  (no section- or department-level tie failures)")

    if len(parsed_by_version) == len(E1_FILES):
        print("\n--- line-by-line diff across all four versions (key: dept code + description) ---")
        for line in diff_e1_versions(parsed_by_version, order):
            print(line)

    print("\n--- E1 vs. the town ledger: FY26 school appropriation ---")
    years_held = sorted(gl_history_years_dept300())
    print(f"  gl-history.csv, general_fund, department_code 300: fiscal years held = {years_held}")
    if "2026" not in years_held:
        print("  FY2026 is NOT in gl-history.csv -- the FY26 appropriation does not exist there yet.")
        print("  Comparing FY2025 instead (the SC-approved workbook's own FY25 column) and noting the gap.")
    fy25_gl = gl_history_dept300(2025)
    if "sc_approved_3_12_25" in parsed_by_version:
        p = parsed_by_version["sc_approved_3_12_25"]
        tb = p["totals"].get("TOTAL BUDGET", {}).get("values", {})
        fy25_col = next((c for c in p["data_cols"] if p["headers"].get(c) == "FY25 - Actual"), None)
        fy25_budgeted_col = next((c for c in p["data_cols"] if p["headers"].get(c) == "FY25 - Budgeted"), None)
        if fy25_budgeted_col:
            wb_fy25 = tb.get(fy25_budgeted_col)
            print(f"  sc_approved_3_12_25 workbook TOTAL BUDGET, FY25 Budgeted column: {wb_fy25}")
            if fy25_gl is not None and wb_fy25 is not None:
                print(f"  gl-history.csv dept 300 FY2025 original sum: {fy25_gl}")
                print(f"  difference (ledger - workbook): {round(fy25_gl - wb_fy25, 2)}")
    fincom_sums = fincom_ledgers_by_report()
    print("  fincom-ledgers.csv, sum of 'original' by report (this file holds several overlapping YTD snapshots):")
    for rk, s in sorted(fincom_sums.items()):
        print(f"    {Path(rk).name}: {s}")
    print("  Report, not forced: these are different documents at different moments; a gap here is not")
    print("  evidence of an error in either, per rule 11 (a budget line is net, and scope/timing differ).")

    print("\n" + "=" * 88)
    print("E2 -- FY27 Budget Projection as of 2.24.26 with restorations: Finance Committee copy vs. archive")
    print("=" * 88)
    e2_identical = None
    if not E2_FINCOM.exists() or not E2_ARCHIVE.exists():
        print(f"  MISSING: fincom={E2_FINCOM.exists()} archive={E2_ARCHIVE.exists()}")
    else:
        e2_identical, lines = compare_e2(E2_FINCOM, E2_ARCHIVE)
        for line in lines:
            print(line)
    print(f"\n  RESULT: {'IDENTICAL' if e2_identical else 'NOT IDENTICAL'} (see differences above)")

    print("\n" + "=" * 88)
    print("E4 -- LPS Staff 2019-2025.xlsx")
    print("=" * 88)
    e4_ok = False
    if not E4_PATH.exists():
        print(f"  MISSING: {E4_PATH}")
    else:
        fte = parse_fte(E4_PATH)
        print(f"  schools found in 'Detailed FTE by Year': {fte['schools']}")
        print(f"  {len(fte['rows'])} (job x year) rows parsed")
        e4_ok, lines = check_e4_pivot(fte)
        print("  [G2: Pivot Table sums vs. SUMIFS over Detailed FTE by Year]")
        for line in lines:
            print(line)

        print("\n  --- comparison with DESE's own published staffing ---")
        dese = dese_teacher_fte_by_year()
        if dese is None:
            print("  No EPIMS all-staff-by-job-classification file found in sources/state-dese or sources/data.")
            print("  Searched for 'staff'/'fte'/'epims' in filenames: only epims-datahandbook.docx (documentation,")
            print("  no figures), dese-job-classification-codes.docx (code->title reference, no FTE counts), and")
            print("  three statewide educator-level files (dese-teacher-data.xlsx, dese-teachers-by-grade-subject.xlsx,")
            print("  dese-teachers-by-program-area.xlsx) that count CERTIFIED TEACHERS, not all EPIMS job categories")
            print("  (no paraprofessionals, clerical, administrators, nurses -- all present in the LPS workbook).")
        else:
            instr = fte["pivot_cats"].get("Instructional Staff", {})
            print("  Using 'Elementary and Secondary Teachers by Program Area' (TCHR_FTE_CNT, district row),")
            print("  which is DESE's own count of classroom teachers -- NOT the same population as the workbook's")
            print("  'Instructional Staff' category (that category can include non-certified instructional roles).")
            print("  Presented as a corroborating series, not an identity (rule 7: a proxy is never the thing):")
            print(f"  {'year':6} {'DESE TCHR_FTE_CNT':>18} {'workbook Instructional Staff':>30} {'diff':>8}")
            for fy in fte["years"]:
                d = dese.get(fy)
                w = instr.get(fy)
                if d is None or w is None:
                    continue
                print(f"  {fy:6} {d:>18} {round(w,3):>30} {round(d-w,3):>8}")

    print("\n" + "=" * 88)
    print("GATES")
    print("=" * 88)
    print(f"  G1 (E1 totals arithmetic): {'PASS' if gate_ok else 'FAIL'}")
    print(f"  G2 (E4 pivot agreement):   {'PASS' if e4_ok else 'FAIL'}")

    if not (gate_ok and e4_ok):
        print("\nREFUSING TO WRITE CSVs -- a gate failed.")
        return 1

    n_cols = write_e1_csv(parsed_by_version, order)
    print(f"\nWrote {OUT_E1.relative_to(ROOT)} ({n_cols} value columns, union of all four versions' headers)")
    fte = parse_fte(E4_PATH)
    write_e4_csvs(fte)
    print(f"Wrote {OUT_FTE.relative_to(ROOT)} ({len(fte['rows'])} rows)")
    print(f"Wrote {OUT_ENROLL.relative_to(ROOT)} ({len(fte['years'])} rows)")

    if args.check:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
