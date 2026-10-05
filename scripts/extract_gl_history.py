#!/usr/bin/env python3
"""extract_gl_history.py — the Finance Committee's General Fund ledger, one row
per account per fiscal year.

SOURCE (rule 13a — a workbook somebody ASSEMBLED, not a MUNIS printout):
    sources/budget-workbooks/finance-committee/fy26-budget/
        general-fund-budget-vs-actuals-history.xlsx

The Finance Committee built this workbook by pasting per-year MUNIS exports
side by side. It is `stated` evidence until it is tied to a MUNIS ledger
export directly (rule 13a: "A sheet the accounting system printed is proof.
A sheet somebody assembled is not.") It is the strongest multi-year GL view
this project currently holds, and its own printed Grand Total row ties to
the cent against the sum of its own account rows for every one of the
sixteen years (FY2010-FY2025) — see CHECK 1 below. That is NOT the same as
having been reconciled to a MUNIS report; nobody has done that yet.

THREE SHEETS, read by their own header cells (rule 13 — "a position is not a
name"), never by column position:
    - "General Fund  FY10 - FY25"        1,062 account rows, the whole fund
    - "School Only"                        412 account rows, a filtered VIEW
                                            of the same accounts (rows a
                                            subset of the sheet above, same
                                            FULL ACCT strings, same figures
                                            — CHECK 4)
    - "School Facilities Expenses Only"     29 account rows, a further
                                            filtered VIEW of School Only

COLUMN SEMANTICS — established from the header cells themselves, not
inferred from position. Every year block prints up to five columns, named
in the header exactly this way:
    "<YYYY> ORIGINAL BUDGET"  -> original
    "<YYYY> TRANSFERS IN"     -> transfers_1   (the header's own name)
    "<YYYY> TRANSFERS OUT"    -> transfers_2   (the header's own name;
                                                 values are already signed
                                                 negative)
    "<YYYY> REVISED BUDGET"   -> revised
    "<YYYY> ACTUAL"           -> actual
Some years, on some sheets, print only three of the five (ORIGINAL,
REVISED, ACTUAL — no TRANSFERS). That is detected per sheet, per year, from
the header actually present, never assumed. Where a metric's column does
not exist for a given sheet/year, this script writes an EMPTY cell — not a
zero. A zero means the workbook printed 0,00; an empty cell means the
workbook printed nothing for that metric that year.

ARITHMETIC (CHECK 3) — revised is NOT reliably original + transfers_1 +
transfers_2. On the main sheet, 1,318 of 23,931 checkable account-year rows
(5.5%) fail that identity, spread evenly across all sixteen years (29-86
rows per year — not concentrated in one era, so not a one-time step
change). And the FACT, not a guess: even the workbook's own Grand Total row
fails the same identity, by a positive residual every year ($109,000 in
FY2013 to $830,000 in FY2021). Since every metric independently foots to
the Grand Total (CHECK 1 passes cleanly on all five columns separately),
this residual is mechanical, not a bug in this script: TRANSFERS IN plus
TRANSFERS OUT do not account for the whole gap between ORIGINAL and
REVISED. A plausible, UNCONFIRMED hypothesis: "transfers" here means
Finance-Committee Reserve-Fund transfers between line items (which net
close to zero across the whole fund — see the per-year TRANSFERS IN/OUT
figures), while REVISED also carries supplemental appropriations (free
cash, overlay surplus, special Town Meeting votes) that this workbook does
not break out in their own column. Nothing in this workbook tests that;
the Town Meeting warrants for supplemental appropriations would.

DEPARTMENT SUBTOTALS (CHECK 2) are printed inconsistently, discovered only
by reading what each sheet actually fills in — not assumed to be uniform:
    - Main sheet: every department Total row prints ORIGINAL and ACTUAL
      (always), but TRANSFERS IN/OUT (never) and REVISED (once, for one
      dept-year: "SCHOOL DEPARTMENT Total" FY2025). ORIGINAL/ACTUAL tie
      to the cent for every one of 1,328 dept-year pairs but ONE:
      "LIABILITY INSURANCE Total" FY2025 ORIGINAL prints 0 where its two
      account rows sum to $249,188.81. That is a defect IN THE SOURCE
      WORKBOOK, reported, not silently corrected.
    - "School Only" sheet's single "SCHOOL DEPARTMENT Total" row prints
      all five metrics for every year, but DOES NOT TIE to the sum of this
      sheet's own 412 account rows for FY2010-FY2023 — the printed total
      is roughly 1-2% of the real sum every one of those fourteen years,
      consistent with a SUM formula that was never extended as rows were
      added to the sheet. FY2024 ties. FY2025 ties on four of five metrics
      (not ACTUAL, which the printed total undercounts by $12.35M against
      the sheet's own account rows). This sheet's Total row is UNRELIABLE
      for FY2010-FY2023 and should not be read as this sheet's whole-fund
      figure for those years; the account rows themselves (and the main
      sheet's figures, since they are identical per CHECK 4) are the real
      numbers.
    - "School Facilities Expenses Only" sheet's one subtotal row (labelled
      "SCHOOL DEPARTMENT" / "Facilities Expenses Only", not "...Total") does
      not tie to the sum of this sheet's own 29 account rows in ANY of the
      sixteen years. The sheet's own footnote ("4110 Facilities Salaries
      except supplies of $70,675") suggests the total deliberately excludes
      most SALARY account rows that are nonetheless printed on the page for
      context — but excluding exactly those rows does not reproduce the
      printed total either, so the composition of this total is NOT
      ESTABLISHED. Treat it as a label, not a number to sum against.

CHECK 4 — "School Only" and "School Facilities Expenses Only" ACCOUNT ROWS
(not their Total rows) are confirmed subsets of the main sheet: the same
FULL ACCT strings, the same figures, for every year, with exactly ONE
exception: "School Only" row for account 0100-3-300-7400-99-1-52-2-525013
("COMPUTERS-PURCHASE & LEASE"), FY2025 REVISED BUDGET. The main sheet
prints 336,963.65 there; the School Only sheet prints a single space
character (' ') instead of a number. That is a defect in the source cell,
quoted here rather than silently repaired (rule 13: "quote the source,
never your rendering of it") — this script writes that one cell EMPTY in
the CSV and reports it by coordinate every run.

FY2025 IS PART-YEAR in this workbook (rule 1 — do not treat it as a full
year's actual). The Finance Committee's own figures make this visible
without any outside source: Select Board (account
0100-1-122-0000-00-0-00-1-511000) prints FY2025 REVISED BUDGET 97,427.44
against FY2025 ACTUAL 57,803.84 — months of the fiscal year had not yet
happened when this workbook was built. Every FY2025 row in the output
carries actual_is_partial=true; no other year does.

OUTPUT: sources/data/gl-history.csv, one row per account per fiscal year:
    sheet, department_code, department, org, org_desc, object, account,
    fiscal_year, original, transfers_1, transfers_2, revised, actual,
    actual_is_partial

CHECK 1 is the only one that gates the write. It is scoped to the main
sheet's own "Grand Total" row (the only sheet that prints one) and compares
it, metric by metric, year by year, against the sum of that sheet's own
account rows. All five metrics tie to the cent for all sixteen years. If a
future version of the workbook breaks that tie, this script refuses to
write a CSV rather than publish figures that do not foot to the workbook's
own stated total.

Usage:
    python3 scripts/extract_gl_history.py          # extract, validate, write
    python3 scripts/extract_gl_history.py --check  # validate only, no write
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources/budget-workbooks/finance-committee/fy26-budget/general-fund-budget-vs-actuals-history.xlsx"
OUT = ROOT / "sources/data/gl-history.csv"

TOLERANCE = 0.01  # one cent — absorbs binary floating-point summation noise
                   # over up to ~1,062 terms. Every tie this script actually
                   # found was exact to the printed cent; this is headroom,
                   # not an admission that anything is close.

EXPECTED_META = ["DEPARTMENT", "Segment Code", "Dept Description", "ORG", "DESC", "OBJECT", "FULL ACCT"]

METRIC_MAP = {
    "ORIGINAL BUDGET": "original",
    "TRANSFERS IN": "transfers_1",
    "TRANSFERS OUT": "transfers_2",
    "REVISED BUDGET": "revised",
    "ACTUAL": "actual",
}
METRICS_IN_ORDER = ["original", "transfers_1", "transfers_2", "revised", "actual"]
PARTIAL_YEAR = 2025

YEAR_RE = re.compile(r"^(\d{4})\s+(.+)$")


def to_num(v):
    """A cell's value as a float, or None if it is blank/non-numeric.

    Rule 13: quote the source, never your rendering of it. A cell holding a
    single space (found: School Only, FY2025 REVISED, account
    0100-3-300-7400-99-1-52-2-525013) is not a zero and is not repaired
    here — it comes back None and is written as an empty CSV cell.
    """
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_header(header_row, sheet_name):
    """Read the header cells. Returns {year: {metric_key: col_index}}.

    Asserts the seven metadata columns are named exactly as the task
    describes — never inferred from position (rule 13).
    """
    meta = [(header_row[i] or "").strip() for i in range(7)]
    if meta != EXPECTED_META:
        raise ValueError(f"{sheet_name}: metadata header mismatch: {meta!r}")

    year_cols: dict[int, dict[str, int]] = {}
    for idx in range(7, len(header_row)):
        raw = header_row[idx]
        if raw is None:
            continue
        txt = re.sub(r"\s+", " ", raw.strip())
        if not txt:
            continue
        m = YEAR_RE.match(txt)
        if not m:
            raise ValueError(f"{sheet_name}: unrecognized header at col {idx + 1}: {raw!r}")
        year = int(m.group(1))
        metric_txt = m.group(2).strip()
        if metric_txt not in METRIC_MAP:
            raise ValueError(f"{sheet_name}: unrecognized metric {metric_txt!r} at col {idx + 1}: {raw!r}")
        year_cols.setdefault(year, {})[METRIC_MAP[metric_txt]] = idx
    return year_cols


def is_blank_meta(meta):
    return all(v is None for v in meta)


def walk_sheet(ws, sheet_label):
    """Parse one sheet into account rows + subtotal/grand-total rows.

    Returns:
      account_rows: list of dicts (one per account row), each holding the
                    raw metadata and {year: {metric: raw_value}}
      year_cols:    {year: {metric: col_index}}
      dept_checks:  list of dicts — every (department, year, metric) where
                    a subtotal row PRINTED a value, with the summed
                    account-row total and the pass/fail verdict
      grand_check:  list of dicts for the literal "Grand Total" row, if the
                    sheet has one (only the main sheet does)
    """
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    year_cols = parse_header(header, sheet_label)

    account_rows = []
    dept_checks = []
    grand_check = []

    dept_acc: dict[int, dict[str, float]] = {}   # resets after every dept Total row
    sheet_acc: dict[int, dict[str, float]] = {}   # never resets — the whole sheet, for the Grand Total check
    current_dept_label = None

    for r in rows[1:]:
        meta = r[:7]
        if is_blank_meta(meta):
            break  # end of data; everything after is footer notes/stray text

        department, segment, dept_desc, org, desc, obj, acct = meta
        is_account = org is not None

        if is_account:
            if current_dept_label is None:
                current_dept_label = dept_desc
            figures = {}
            for year, cols in year_cols.items():
                figures[year] = {metric: r[idx] for metric, idx in cols.items()}
                for metric, idx in cols.items():
                    v = to_num(r[idx])
                    if v is None:
                        continue
                    dept_acc.setdefault(year, {}).setdefault(metric, 0.0)
                    dept_acc[year][metric] += v
                    sheet_acc.setdefault(year, {}).setdefault(metric, 0.0)
                    sheet_acc[year][metric] += v
            account_rows.append(
                {
                    "department_code": department,
                    "department": dept_desc,
                    "org": org,
                    "org_desc": desc,
                    "object": obj,
                    "account": acct,
                    "figures": figures,
                }
            )
        else:
            # subtotal row (department Total) or the sheet's Grand Total
            is_grand = bool(dept_desc) and dept_desc.strip() == "Grand Total"
            label = dept_desc if dept_desc else current_dept_label
            running = sheet_acc if is_grand else dept_acc
            for year, cols in year_cols.items():
                for metric, idx in cols.items():
                    printed_raw = r[idx]
                    printed = to_num(printed_raw)
                    if printed is None:
                        continue  # not printed for this metric/year — nothing to check
                    summed = running.get(year, {}).get(metric, 0.0)
                    rec = {
                        "sheet": sheet_label,
                        "label": label,
                        "year": year,
                        "metric": metric,
                        "printed": printed,
                        "summed": summed,
                        "diff": printed - summed,
                        "ok": abs(printed - summed) <= TOLERANCE,
                    }
                    (grand_check if is_grand else dept_checks).append(rec)
            dept_acc = {}
            current_dept_label = None

    return account_rows, year_cols, dept_checks, grand_check


def check_arithmetic(account_rows, year_cols, sheet_label):
    """CHECK 3: revised == original + transfers_1 + transfers_2, per
    account row, per year — only where all four columns exist AND are
    numeric. Returns (checked_count, bad_count, examples, by_year)."""
    checked = 0
    bad = 0
    examples = []
    by_year: dict[int, dict[str, int]] = {}
    for row in account_rows:
        for year, cols in year_cols.items():
            if not all(k in cols for k in ("original", "transfers_1", "transfers_2", "revised")):
                continue
            vals = row["figures"][year]
            orig = to_num(vals.get("original"))
            t1 = to_num(vals.get("transfers_1"))
            t2 = to_num(vals.get("transfers_2"))
            rev = to_num(vals.get("revised"))
            by_year.setdefault(year, {"checked": 0, "bad": 0})
            if None in (orig, t1, t2, rev):
                continue  # a missing/non-numeric cell is its own anomaly (CHECK 4), not an arithmetic failure
            checked += 1
            by_year[year]["checked"] += 1
            diff = rev - (orig + t1 + t2)
            if abs(diff) > TOLERANCE:
                bad += 1
                by_year[year]["bad"] += 1
                if len(examples) < 15:
                    examples.append((sheet_label, row["account"], year, orig, t1, t2, rev, diff))
    return checked, bad, examples, by_year


def check_subset(school_rows, main_index, sheet_label):
    """CHECK 4: every account row on a filtered sheet must match the main
    sheet's row for the same FULL ACCT, figure for figure, year for year."""
    mismatches = []
    checked = 0
    for row in school_rows:
        acct = row["account"]
        main_row = main_index.get(acct)
        if main_row is None:
            mismatches.append((sheet_label, acct, None, "MISSING_FROM_MAIN", None, None))
            continue
        for year, vals in row["figures"].items():
            main_vals = main_row["figures"].get(year, {})
            for metric, raw in vals.items():
                checked += 1
                v = to_num(raw)
                mv = to_num(main_vals.get(metric))
                if v is None and mv is None:
                    continue
                if v is None or mv is None or abs(v - mv) > TOLERANCE:
                    mismatches.append((sheet_label, acct, year, metric, raw, main_vals.get(metric)))
    return checked, mismatches


def build_csv_rows(account_rows, year_cols, sheet_label):
    out = []
    for row in account_rows:
        for year in sorted(year_cols):
            vals = row["figures"][year]
            out.append(
                {
                    "sheet": sheet_label,
                    "department_code": row["department_code"],
                    "department": row["department"],
                    "org": row["org"],
                    "org_desc": row["org_desc"],
                    "object": row["object"],
                    "account": row["account"],
                    "fiscal_year": year,
                    "original": to_num(vals.get("original")),
                    "transfers_1": to_num(vals.get("transfers_1")),
                    "transfers_2": to_num(vals.get("transfers_2")),
                    "revised": to_num(vals.get("revised")),
                    "actual": to_num(vals.get("actual")),
                    "actual_is_partial": "true" if year == PARTIAL_YEAR else "false",
                }
            )
    return out


def fmt(v):
    return "" if v is None else f"{v:.2f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate only; do not write the CSV")
    args = parser.parse_args()

    if not SRC.exists():
        print(f"REFUSED: source workbook not found: {SRC}", file=sys.stderr)
        return 1

    wb = openpyxl.load_workbook(SRC, data_only=True, read_only=True)

    sheets = {
        "General Fund  FY10 - FY25": "general_fund",
        "School Only": "school_only",
        "School Facilities Expenses Only": "school_facilities",
    }
    missing = [s for s in sheets if s not in wb.sheetnames]
    if missing:
        print(f"REFUSED: expected sheet(s) not found: {missing}", file=sys.stderr)
        return 1

    all_account_rows = {}
    all_year_cols = {}
    all_dept_checks = []
    grand_checks = []
    csv_rows = []

    for sheet_name, label in sheets.items():
        ws = wb[sheet_name]
        account_rows, year_cols, dept_checks, grand_check = walk_sheet(ws, label)
        all_account_rows[label] = account_rows
        all_year_cols[label] = year_cols
        all_dept_checks.extend(dept_checks)
        grand_checks.extend(grand_check)
        csv_rows.extend(build_csv_rows(account_rows, year_cols, label))

    # ---- CHECK 1: the main sheet's Grand Total row (the gate) ----
    print("=" * 72)
    print("CHECK 1 — main sheet account rows vs. the workbook's own Grand Total row")
    print("(this is the ONLY check that gates the write)")
    print("=" * 72)
    check1_ok = True
    if not grand_checks:
        print("  No literal 'Grand Total' row was found on any sheet.")
        check1_ok = False
    for rec in sorted(grand_checks, key=lambda r: (r["year"], r["metric"])):
        status = "OK" if rec["ok"] else "FAIL"
        if not rec["ok"]:
            check1_ok = False
        print(
            f"  FY{rec['year']} {rec['metric']:<12} printed={rec['printed']:>15,.2f} "
            f"summed={rec['summed']:>15,.2f} diff={rec['diff']:>10,.2f}  {status}"
        )
    print(f"  -> {'ALL TIE TO THE CENT' if check1_ok else 'TIE FAILED — see above'}")

    # ---- CHECK 2: department subtotals, where printed ----
    print()
    print("=" * 72)
    print("CHECK 2 — department/sheet subtotal rows vs. summed account rows (where printed)")
    print("=" * 72)
    bad_dept = [r for r in all_dept_checks if not r["ok"]]
    print(f"  {len(all_dept_checks)} printed subtotal figures checked across all sheets; {len(bad_dept)} do not tie.")
    for rec in bad_dept:
        print(
            f"  [{rec['sheet']}] {rec['label']!r} FY{rec['year']} {rec['metric']}: "
            f"printed={rec['printed']:,.2f} summed={rec['summed']:,.2f} diff={rec['diff']:,.2f}"
        )

    # ---- CHECK 3: revised == original + transfers_1 + transfers_2 ----
    print()
    print("=" * 72)
    print("CHECK 3 — revised == original + transfers_1 + transfers_2 (per account row, per year)")
    print("=" * 72)
    for label in all_account_rows:
        checked, bad, examples, by_year = check_arithmetic(all_account_rows[label], all_year_cols[label], label)
        if checked == 0:
            continue
        pct = 100.0 * bad / checked if checked else 0.0
        print(f"  [{label}] {bad} of {checked} checkable account-year rows ({pct:.1f}%) do not satisfy the identity.")
        for year in sorted(by_year):
            c = by_year[year]
            if c["checked"]:
                print(f"      FY{year}: {c['bad']}/{c['checked']}")
        for ex in examples[:5]:
            print(f"      example: {ex}")

    # ---- CHECK 4: School Only / Facilities are subsets of the main sheet ----
    print()
    print("=" * 72)
    print("CHECK 4 — School Only / School Facilities account rows are a subset of the main sheet")
    print("=" * 72)
    main_index = {row["account"]: row for row in all_account_rows["general_fund"]}
    for label in ("school_only", "school_facilities"):
        checked, mismatches = check_subset(all_account_rows[label], main_index, label)
        print(f"  [{label}] {checked} figures compared against the main sheet; {len(mismatches)} mismatch(es).")
        for m in mismatches:
            print(f"      {m}")

    # ---- CHECK 5: FY2025 is part-year ----
    print()
    print("=" * 72)
    print(f"CHECK 5 — FY{PARTIAL_YEAR} is a PART-YEAR in this workbook (actual_is_partial=true)")
    print("=" * 72)
    sb = next(
        (r for r in all_account_rows["general_fund"] if r["account"] == "0100-1-122-0000-00-0-00-1-511000"), None
    )
    if sb:
        v = sb["figures"][PARTIAL_YEAR]
        print(
            f"  Select Board, SALARIES DIVISION/DEPT HEADS, FY{PARTIAL_YEAR}: "
            f"revised={to_num(v.get('revised')):,.2f} actual={to_num(v.get('actual')):,.2f}"
        )
    else:
        print("  (reference account not found this run)")

    # ---- Per-fiscal-year series, printed, not written to prose (rule 2) ----
    print()
    print("=" * 72)
    print("SERIES — per fiscal year: departments, accounts, and totals (printed only)")
    print("=" * 72)
    for label in all_account_rows:
        print(f"\n  [{label}]")
        year_cols = all_year_cols[label]
        for year in sorted(year_cols):
            depts = set()
            n_accounts = 0
            tot = {"original": 0.0, "revised": 0.0, "actual": 0.0}
            for row in all_account_rows[label]:
                vals = row["figures"][year]
                any_nonzero = any((to_num(vals.get(m)) or 0.0) != 0.0 for m in vals)
                if not any_nonzero:
                    continue
                n_accounts += 1
                depts.add(row["department_code"])
                for m in tot:
                    if m in vals:
                        tot[m] += to_num(vals[m]) or 0.0
            print(
                f"    FY{year}: {len(depts):>3} depts, {n_accounts:>4} accounts  "
                f"original={tot['original']:>14,.2f}  revised={tot['revised']:>14,.2f}  actual={tot['actual']:>14,.2f}"
            )

    print()
    print("=" * 72)
    if not check1_ok:
        print("REFUSED TO WRITE: CHECK 1 failed — the main sheet's account rows no longer")
        print("tie to its own Grand Total row. Fix the discrepancy above before writing.")
        print("=" * 72)
        return 1

    if args.check:
        print("CHECK 1 passed. --check given: not writing the CSV.")
        print("=" * 72)
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sheet",
        "department_code",
        "department",
        "org",
        "org_desc",
        "object",
        "account",
        "fiscal_year",
        "original",
        "transfers_1",
        "transfers_2",
        "revised",
        "actual",
        "actual_is_partial",
    ]
    with OUT.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in csv_rows:
            writer.writerow(
                [
                    row["sheet"],
                    row["department_code"],
                    row["department"],
                    row["org"],
                    row["org_desc"],
                    row["object"],
                    row["account"],
                    row["fiscal_year"],
                    fmt(row["original"]),
                    fmt(row["transfers_1"]),
                    fmt(row["transfers_2"]),
                    fmt(row["revised"]),
                    fmt(row["actual"]),
                    row["actual_is_partial"],
                ]
            )
    print(f"Wrote {len(csv_rows)} rows to {OUT.relative_to(ROOT)}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
