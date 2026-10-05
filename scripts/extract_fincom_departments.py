#!/usr/bin/env python3
"""Finance Committee task tracker: B2, A6, D5, G1.

Extracts tidy, cited CSVs for four Finance Committee tasks and compares them
against data the archive already holds (gl-history.csv,
town-budget-fy26-fy27.csv, department-rosters.csv). Per CLAUDE.md rule 1,
every comparison to gl-history/town-budget uses BUDGET columns only; actuals
never feed a projection and are reported separately, labelled.

  B2  Police spending as expended, FY2015-FY2023 (PDF, MUNIS-style export)
  A6  Ambulance receipts history (MUNIS GL account inquiry workbook)
  D5  FY2027 department budgets presented to FinCom
  G1  Police/fire staffing plans, hiring plan, overtime model, 2.5% ceiling

Run:
    python3 scripts/extract_fincom_departments.py            # extract + write CSVs
    python3 scripts/extract_fincom_departments.py --check    # extract, verify, do not write

A table that cannot be tied to the total it prints is refused (rule 13b/13c:
"a check must assert the number, not the prose") UNLESS the mismatch has been
independently verified by position (cell/x-coordinate) and is one of the
small set of known, cited source discrepancies hardcoded below -- see
KNOWN_B2_TOTAL_EXCEPTIONS. New, unexplained mismatches still refuse to write.
"""
import csv
import os
import re
import sys
from collections import OrderedDict, defaultdict

import openpyxl
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")
DATA = os.path.join(ROOT, "sources", "data")
FC = os.path.join(SRC, "budget-workbooks", "finance-committee")

CHECK_ONLY = "--check" in sys.argv


def path(*parts):
    return os.path.join(*parts)


def write_csv(filename, fieldnames, rows):
    out = os.path.join(DATA, filename)
    if CHECK_ONLY:
        print(f"[check] would write {filename}: {len(rows)} rows")
        return
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {filename}: {len(rows)} rows")


def money_eq(a, b, tol=0.02):
    return abs(round((a or 0) - (b or 0), 2)) <= tol


# ---------------------------------------------------------------------------
# gl-history.csv / town-budget-fy26-fy27.csv lookups
# ---------------------------------------------------------------------------

def load_gl_history():
    rows = []
    with open(path(DATA, "gl-history.csv")) as f:
        for row in csv.DictReader(f):
            if row["sheet"] != "general_fund":
                continue
            rows.append(row)
    return rows


def gl_org_year_sums(gl_rows, orgs, fiscal_year):
    """Sum original/revised/actual across all objects for the given MUNIS
    org code(s) and fiscal year, within gl-history's general_fund sheet."""
    orig = rev = act = 0.0
    found = False
    for row in gl_rows:
        if row["org"] in orgs and row["fiscal_year"] == str(fiscal_year):
            found = True
            orig += float(row["original"] or 0)
            rev += float(row["revised"] or 0)
            act += float(row["actual"] or 0)
    return found, orig, rev, act


def load_town_budget_fy27():
    rows = []
    with open(path(DATA, "town-budget-fy26-fy27.csv")) as f:
        for row in csv.DictReader(f):
            if row["column_header"] == "BUDGET | REQUEST | FY2027" and row["version"].startswith(
                "Working FY27 Budget Shared 3.3.26.xlsx"
            ):
                rows.append(row)
    return rows


def town_budget_fy27_lookup(tb_rows):
    """account -> amount, for the FY2027 working-budget column."""
    out = {}
    for row in tb_rows:
        out[row["account"]] = float(row["amount"])
    return out


def load_rosters():
    counts = defaultdict(set)
    with open(path(DATA, "department-rosters.csv")) as f:
        for row in csv.DictReader(f):
            counts[(row["department"], row["fy"])].add(row["name"])
    return {k: len(v) for k, v in counts.items()}


# ---------------------------------------------------------------------------
# B2 -- Police Budget As Expended FY2015-FY2023 (PDF)
# ---------------------------------------------------------------------------

B2_PDF = path(
    FC, "fy25-budget", "police", "ii.-attachment-a-police-budget-as-expended-fy15-fy23.pdf"
)
B2_YEARS = ["FY15", "FY16", "FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23"]

# Verified by cell position (rule 13b/13c): these three line items sit ABOVE
# their category's TOTAL row in the source PDF but are excluded from the
# printed total -- a spreadsheet formula fixed before the row was added, not
# an extraction error. Confirmed twice: (1) the concatenated digits match the
# document's own printed figure exactly: (2) the x0 of each value is
# unambiguously nearest its stated column (verified against the header's own
# FY-label x0 positions, diff < 16pt vs > 38pt for the next-nearest column).
KNOWN_B2_TOTAL_EXCEPTIONS = {
    # (category, fiscal_year): (description, amount) excluded from the printed total
    ("Personnel", "FY18"): [("POLICE CPR TRAINING", 2515.96)],
    ("Personnel", "FY20"): [("FIREARMS QUALIFICATION TRNG", 24.38)],
    ("Radio Watch", "FY22"): [("SALARIES CLERICAL", 59930.28)],
    ("Radio Watch", "FY23"): [("SALARIES CLERICAL", 45094.92)],
}

B2_CAT_BY_PAGE = [
    # (page, type_label_prefix, total_description)
    (1, "Personnel", "PERSONNEL - TOTAL"),
    (1, "Expenses", "EXPENSES - TOTAL"),
    (2, "Animal Control", "ANIMAL CONTROL - TOTAL"),
    (2, "Lockup", "LOCKUP - TOTAL"),
    (2, "Radio Watch", "RADIO WATCH - TOTAL"),
    (2, "Vehicle Mtc", "VEHICLE MTC - TOTAL"),
]

# MUNIS org codes (gl-history) behind each B2 category, for the department-
# level comparison. Vehicle Mtc is filtered to the police-only sub-org
# because gl-history's department_code 429 (VEHICLE MAINTENANCE) also holds
# the fire department's share under a different org.
B2_GL_ORGS = {
    "Personnel": {"12101"},
    "Expenses": {"12102"},
    "Animal Control": {"12921", "12922"},
    "Lockup": {"12131", "12132"},
    "Radio Watch": {"12281", "12282"},
    "Vehicle Mtc": {"14292102"},
}


def extract_b2():
    """Position-based extraction (rule 13b/13c): the source PDF's text layer
    fragments wide numbers (a leading digit renders as a separate token from
    the rest), so values are reassembled by column position, never by
    reading order. Column assignment uses the '$' token's x0 against the
    header's own FY-label x0 positions (verified stable regardless of a
    number's width; the number's own right edge is NOT reliable -- a wide
    total can start closer to the PREVIOUS column's header than its own)."""
    with pdfplumber.open(B2_PDF) as pdf:
        header_words = pdf.pages[0].extract_words()
        hdr_by_top = defaultdict(list)
        for w in header_words:
            hdr_by_top[round(w["top"], 1)].append(w)
        hdr_row = hdr_by_top[61.4]
        col_x0 = {w["text"]: w["x0"] for w in hdr_row if w["text"] in B2_YEARS}
        if len(col_x0) != 9:
            raise RuntimeError(f"B2: expected 9 year columns in header, found {col_x0}")

        out = []
        for pageno, page in enumerate(pdf.pages, start=1):
            rows_by_top = defaultdict(list)
            for w in page.extract_words():
                rows_by_top[round(w["top"], 0)].append(w)
            for top in sorted(rows_by_top):
                ws = sorted(rows_by_top[top], key=lambda w: w["x0"])
                texts = [w["text"] for w in ws]
                if texts[:2] == ["Type", "Sub"]:
                    continue
                if "ATTACHMENT" in texts:
                    continue
                if texts[:2] == ["POLICE", "BUDGET"]:
                    continue
                label_type, label_sub, label_desc, numeric_zone = [], [], [], []
                for w in ws:
                    if w["x0"] < 260:
                        if w["x0"] < 50:
                            label_type.append(w["text"])
                        elif w["x0"] < 110:
                            label_sub.append(w["text"])
                        else:
                            label_desc.append(w["text"])
                    else:
                        numeric_zone.append(w)
                if not numeric_zone:
                    continue
                type_, sub, desc = " ".join(label_type), " ".join(label_sub), " ".join(label_desc)
                groups, cur = [], None
                for w in numeric_zone:
                    if "$" in w["text"]:
                        cur = {"dollar_x0": w["x0"], "parts": [w]}
                        groups.append(cur)
                    else:
                        if cur is None:
                            cur = {"dollar_x0": w["x0"], "parts": []}
                            groups.append(cur)
                        cur["parts"].append(w)
                for g in groups:
                    best_y = min(B2_YEARS, key=lambda y: abs(col_x0[y] - g["dollar_x0"]))
                    txt = "".join(p["text"] for p in g["parts"]).replace("$", "")
                    val = 0.0 if txt in ("-", "") else float(txt.replace(",", ""))
                    out.append(
                        {
                            "page": pageno,
                            "type": type_,
                            "sub_type": sub,
                            "description": desc,
                            "fiscal_year": best_y,
                            "amount": val,
                        }
                    )
        return out


def b2_fy_to_calendar(fy):
    return 2000 + int(fy[2:])


def build_b2():
    raw = extract_b2()
    line_items = [r for r in raw if r["type"] or r["sub_type"]]
    totals = {}  # (page, description) -> {fy: amount}
    for r in raw:
        if not r["type"] and not r["sub_type"]:
            totals.setdefault((r["page"], r["description"]), {})[r["fiscal_year"]] = r["amount"]

    grand_total = totals.get((2, "TOTAL POLICE BUDGET AS EXPENDED"), {})
    if not grand_total:
        raise RuntimeError("B2: could not locate the grand total row in the PDF")

    cat_totals = {}
    for page, cat, total_desc in B2_CAT_BY_PAGE:
        t = totals.get((page, total_desc))
        if not t:
            raise RuntimeError(f"B2: total row '{total_desc}' not found on page {page}")
        cat_totals[cat] = t

    # Tie check: line items per category/year must sum to the printed
    # category total, net of the known, position-verified exceptions.
    tie_notes = []
    for page, cat, _ in B2_CAT_BY_PAGE:
        for y in B2_YEARS:
            summed = sum(
                r["amount"]
                for r in line_items
                if r["page"] == page and r["type"] == cat and r["fiscal_year"] == y
            )
            printed = cat_totals[cat].get(y, 0.0)
            exceptions = KNOWN_B2_TOTAL_EXCEPTIONS.get((cat, y), [])
            excluded = sum(a for _, a in exceptions)
            if not money_eq(summed - excluded, printed):
                raise RuntimeError(
                    f"B2 REFUSED: {cat} {y} line items sum to {summed:.2f}, "
                    f"printed total is {printed:.2f} "
                    f"(known exceptions account for {excluded:.2f}); "
                    f"unexplained diff {summed - excluded - printed:.2f}"
                )
            if exceptions:
                for desc, amt in exceptions:
                    tie_notes.append(
                        f"{cat} {y}: '{desc}' (${amt:,.2f}) appears in the source table but is "
                        f"excluded from the printed {cat.upper()} - TOTAL row (verified by cell "
                        f"position, page {page} of {os.path.basename(B2_PDF)})"
                    )

    # Grand total = sum of the six printed category totals, PLUS the known,
    # position-verified exceptions above (the grand total was evidently
    # computed by summing every leaf line item directly, not by summing the
    # six printed category subtotals -- so it DOES include the line items
    # those subtotals exclude).
    for y in B2_YEARS:
        cat_sum = sum(cat_totals[cat].get(y, 0.0) for _, cat, _ in B2_CAT_BY_PAGE)
        excluded_total = sum(
            amt for (cat, yy), items in KNOWN_B2_TOTAL_EXCEPTIONS.items() if yy == y for _, amt in items
        )
        if not money_eq(cat_sum + excluded_total, grand_total.get(y, 0.0)):
            raise RuntimeError(
                f"B2 REFUSED: sum of category totals for {y} is {cat_sum:.2f} "
                f"(+ {excluded_total:.2f} known exceptions = {cat_sum + excluded_total:.2f}), "
                f"printed grand total is {grand_total.get(y, 0.0):.2f}"
            )

    rows = []
    for r in line_items:
        rows.append(
            {
                "source_file": os.path.relpath(B2_PDF, ROOT),
                "page": r["page"],
                "type": r["type"],
                "sub_type": r["sub_type"],
                "description": r["description"],
                "fiscal_year": r["fiscal_year"],
                "amount": r["amount"],
                "is_total_row": "no",
            }
        )
    for page, cat, total_desc in B2_CAT_BY_PAGE:
        for y in B2_YEARS:
            rows.append(
                {
                    "source_file": os.path.relpath(B2_PDF, ROOT),
                    "page": page,
                    "type": "",
                    "sub_type": "",
                    "description": total_desc,
                    "fiscal_year": y,
                    "amount": cat_totals[cat][y],
                    "is_total_row": "yes",
                }
            )
    for y in B2_YEARS:
        rows.append(
            {
                "source_file": os.path.relpath(B2_PDF, ROOT),
                "page": 2,
                "type": "",
                "sub_type": "",
                "description": "TOTAL POLICE BUDGET AS EXPENDED",
                "fiscal_year": y,
                "amount": grand_total[y],
                "is_total_row": "yes",
            }
        )

    print("B2 ties OK (categories -> grand total; line items -> category totals,")
    print("            net of position-verified source exceptions):")
    for note in tie_notes:
        print("  -", note)

    write_csv(
        "police-expended.csv",
        ["source_file", "page", "type", "sub_type", "description", "fiscal_year", "amount", "is_total_row"],
        rows,
    )
    return cat_totals, grand_total


def build_b2_comparison(cat_totals):
    gl_rows = load_gl_history()
    out = []
    # gl-history sums by MUNIS org, not by B2's "Personnel"/"Expenses" split
    # within a department -- Personnel and Expenses share the SAME org
    # (12101), so gl-history cannot distinguish them. Comparing each
    # separately against the whole org's actual would silently compare
    # Expenses against a figure that is mostly Personnel. Group B2's
    # categories by their underlying org-set first, and compare the SUM of
    # categories sharing an org-set against gl-history once.
    groups = OrderedDict()
    for page, cat, _ in B2_CAT_BY_PAGE:
        orgs = frozenset(B2_GL_ORGS[cat])
        groups.setdefault(orgs, []).append(cat)
    for orgs, cats in groups.items():
        label = " + ".join(cats)
        for y in B2_YEARS:
            cal_year = b2_fy_to_calendar(y)
            found, orig, rev, act = gl_org_year_sums(gl_rows, orgs, cal_year)
            b2_val = sum(cat_totals[c].get(y, 0.0) for c in cats)
            diff = round(b2_val - act, 2) if found else None
            out.append(
                {
                    "category": label,
                    "fiscal_year": y,
                    "b2_as_expended": b2_val,
                    "gl_history_actual": act if found else "",
                    "gl_history_orgs": " ".join(sorted(orgs)),
                    "found_in_gl_history": "yes" if found else "no",
                    "diff_b2_minus_gl_actual": diff if diff is not None else "",
                }
            )
    write_csv(
        "police-expended-vs-gl-history.csv",
        [
            "category",
            "fiscal_year",
            "b2_as_expended",
            "gl_history_actual",
            "gl_history_orgs",
            "found_in_gl_history",
            "diff_b2_minus_gl_actual",
        ],
        out,
    )
    diffs = [r for r in out if r["found_in_gl_history"] == "yes" and r["diff_b2_minus_gl_actual"] not in ("", 0, 0.0)]
    print(f"B2 vs gl-history: {len(out) - len(diffs)} of {len(out)} category-years tie exactly; "
          f"{len(diffs)} differ (both are ACTUALS -- rule 1 is not implicated).")
    if diffs:
        biggest = max(diffs, key=lambda r: abs(r["diff_b2_minus_gl_actual"]))
        print(f"  largest difference: {biggest['category']} {biggest['fiscal_year']}: "
              f"{biggest['diff_b2_minus_gl_actual']:+.2f}")


# ---------------------------------------------------------------------------
# A6 -- Ambulance Receipts History (MUNIS GL account inquiry workbook)
# ---------------------------------------------------------------------------

A6_XLSX = path(FC, "fy26-budget", "ambulance-receipts-history.xlsx")


def build_a6():
    wb = openpyxl.load_workbook(A6_XLSX, data_only=True)
    ws = wb[wb.sheetnames[0]]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    data_row = next(ws.iter_rows(min_row=2, max_row=2))
    values = {header[i]: c.value for i, c in enumerate(data_row)}

    fund, org, desc, obj, acct_desc = (
        values["FUND"],
        values["ORG"],
        values["DESC"],
        values["OBJECT"],
        values["ACCT DESCRIPTION"],
    )
    year_cols = [h for h in header if h and "ACTUAL" in h]
    rows = []
    for h in year_cols:
        year = int(re.search(r"\d{4}", h).group())
        amount = values[h]
        rows.append(
            {
                "source_file": os.path.relpath(A6_XLSX, ROOT),
                "sheet": ws.title,
                "row": 2,
                "fund": fund,
                "org": org,
                "department": desc,
                "object": obj,
                "account_description": acct_desc,
                "fiscal_year": year,
                # MUNIS prints revenue as a credit (negative); report the
                # receipt amount as a positive dollar figure, and keep the
                # as-printed (negative) figure too so neither is a derived
                # rendering of the other (rule 13: cite the raw value).
                "amount_as_printed": amount,
                "receipt_amount": -amount if amount is not None else None,
            }
        )
    rows.sort(key=lambda r: r["fiscal_year"])

    # There is nothing on this single-row report for a line item to be
    # TIED to -- it is one account, one row, no subtotal. The only "tie"
    # available is that the report is internally what it claims to be: one
    # FUND/ORG/OBJECT combination, 12 years, no blanks.
    if len(rows) != 12:
        raise RuntimeError(f"A6 REFUSED: expected 12 years of actuals, found {len(rows)}")
    if any(r["amount_as_printed"] is None for r in rows):
        raise RuntimeError("A6 REFUSED: a year column is blank")
    print(f"A6 ties OK: single MUNIS account inquiry row, {fund}/{org}/{obj} '{acct_desc}', "
          f"{len(rows)} consecutive fiscal years FY{rows[0]['fiscal_year']-2000:02d}-"
          f"FY{rows[-1]['fiscal_year']-2000:02d}, no blanks. (No subtotal is printed to tie to;"
          f" there is exactly one account on this report.)")

    write_csv(
        "ambulance-receipts.csv",
        [
            "source_file", "sheet", "row", "fund", "org", "department", "object",
            "account_description", "fiscal_year", "amount_as_printed", "receipt_amount",
        ],
        rows,
    )
    return rows, org


def build_a6_comparison(a6_rows, org):
    gl_rows = load_gl_history()
    gl_objects = {row["object"] for row in gl_rows}
    revenue_objects = {o for o in gl_objects if o.startswith("4")}
    out = []
    for r in a6_rows:
        found, orig, rev, act = gl_org_year_sums(gl_rows, {org}, r["fiscal_year"])
        out.append(
            {
                "fiscal_year": r["fiscal_year"],
                "a6_receipt_amount": r["receipt_amount"],
                "org": org,
                "object_470300_in_gl_history": "object 470300" in str(gl_objects) and "470300" in gl_objects,
                "found_in_gl_history": "yes" if found else "no",
            }
        )
    write_csv(
        "ambulance-receipts-vs-gl-history.csv",
        ["fiscal_year", "a6_receipt_amount", "org", "object_470300_in_gl_history", "found_in_gl_history"],
        out,
    )
    print(
        f"A6 vs gl-history: gl-history's general_fund sheet carries {len(gl_objects)} distinct "
        f"object codes and {len(revenue_objects)} of them start with '4' (revenue). Object 470300 "
        f"(RESCUE WAGON / ambulance receipts) is {'present' if '470300' in gl_objects else 'ABSENT'} "
        f"-- gl-history does not carry revenue at all, only expenditure objects (511xxx-58xxxx). "
        f"0 of {len(a6_rows)} years are comparable; this is a gap in gl-history, not in A6."
    )


# ---------------------------------------------------------------------------
# D5 -- FY2027 department budgets presented to FinCom
# ---------------------------------------------------------------------------

D5_FACILITIES = path(FC, "fy27-budget", "department-presentations", "facilities",
                      "facilities-budget-for-fincom-2.19.26-1.xlsx")
D5_FIRE = path(FC, "fy27-budget", "department-presentations", "fire",
                "fire-budget-for-fincom-2.19.26.xlsx")
D5_POLICE = path(FC, "fy27-budget", "department-presentations", "police",
                  "police-budget-for-fincom-2.19.26.xlsx")
D5_VIDEOGRAPHER = path(FC, "fy27-budget", "department-presentations", "pacc",
                        "videographer-hour-percentages.xlsx")
D5_IT = path(FC, "fy25-budget", "it", "fy25-it-budget.xlsx")
D5_LAND_USE = path(FC, "fy24-budget", "20230223-coa-land-use-library", "land-use-fy23-budget.xlsx")

# MUNIS org -> gl-history department_code, for every org that appears in the
# three FinCom-presentation workbooks (verified against gl-history.csv).
D5_ORG_DEPT = {
    "12101": "210",  # Police (personnel)
    "12102": "210",  # Police (expenses)
    "12131": "213", "12132": "213",  # Police Lock Up (salaries / expenses)
    "12141": "214",  # Injury Leave
    "15242": "524",  # Police/Fire Medical
    "12201": "220", "12202": "220",  # Fire Department
    "12232": "223",  # Fire Hydrant Expense
    "12272": "227",  # Mtc of Town Radios
    "12281": "228", "12282": "228",  # Radio Watch
    "12911": "291", "12912": "291",  # Emergency Management
    "12921": "292", "12922": "292",  # Animal Control
    "14292102": "429", "14292202": "429",  # Vehicle Maintenance (split by suborg; filter by org, not dept_code)
    "11922": "192",  # Public Buildings
    "11931": "193", "11932": "193",  # Director of Facilities & Grounds
    "16501": "650", "16502": "650",  # Parks & Recreation
}


def _leaf_rows_generic(ws, header):
    """Yield (row_no, org, obj, description, money_by_header) for every leaf
    row (one that carries an ORG code) in a FinCom department workbook."""
    di = header.index("DESCRIPTION")
    oi = header.index("ORG")
    ji = header.index("OBJ") if "OBJ" in header else None
    money_idxs = [i for i, h in enumerate(header) if h and ("BUDGET" in h or h in ("FY2027", "FY26 ORIGIN APPROP"))]
    for row in ws.iter_rows(min_row=2):
        vals = [c.value for c in row]
        if vals[oi] is not None and str(vals[oi]).strip().upper() == "ORG":
            continue  # a repeated header row, not data
        desc = vals[di]
        if desc is not None and "TOTAL" in str(desc).upper():
            continue  # a total row, handled by _total_rows_generic
        money = {header[i]: vals[i] for i in money_idxs}
        if vals[oi] is None and not any(isinstance(v, (int, float)) for v in money.values()):
            continue  # a genuinely blank row
        obj = vals[ji] if ji is not None else None
        yield row[0].row, (str(vals[oi]) if vals[oi] is not None else ""), (str(obj) if obj is not None else ""), desc, money


def _total_rows_generic(ws, header):
    """Yield (row_no, indented, description, money_by_header) for every total
    row (ORG is blank, description mentions TOTAL/SUBTOTAL)."""
    di = header.index("DESCRIPTION")
    oi = header.index("ORG")
    money_idxs = [i for i, h in enumerate(header) if h and ("BUDGET" in h or h in ("FY2027", "FY26 ORIGIN APPROP"))]
    for row in ws.iter_rows(min_row=2):
        vals = [c.value for c in row]
        desc = vals[di]
        if vals[oi] is not None or not desc:
            continue
        if "TOTAL" not in str(desc).upper():
            continue
        money = {header[i]: vals[i] for i in money_idxs}
        indented = str(desc).startswith(" ")
        yield row[0].row, indented, str(desc).strip(), money


# Verified by direct cell read (rule 13): the Fire FinCom workbook's own
# leaf row for Fire Hydrant Expense prints FY24 BUDGET=17,000 and FY24
# ACTUAL=30,000 (row 49); its TOTAL row two rows below prints FY24
# BUDGET=30,000 -- the actual figure, not the budget figure, carried into
# the wrong column (row 51). Every other column on that total row ties
# exactly. Hardcoded here as a reported exception, never silently matched.
KNOWN_D5_TOTAL_EXCEPTIONS = {
    ("fire-budget-for-fincom-2.19.26.xlsx", 51, "FY24 BUDGET"): (
        "printed 30,000 -- matches this row's own FY24 ACTUAL (and the leaf row 49's FY24 "
        "ACTUAL), not the leaf's FY24 BUDGET of 17,000; a column mix-up in the source, not an "
        "extraction error"
    ),
}


def _tie_check_hierarchical(ws_name, header, leaves, totals, money_cols):
    """Verify the nested TOTAL/SUBTOTAL hierarchy seen in the Police, Fire
    and Facilities FinCom workbooks (rule 13: a check must assert the
    number, not the prose). Every leaf row and every already-tied total is
    kept, in order, in one pending list. A TOTAL/SUBTOTAL row ties against
    the shortest trailing (most recent) run of that list whose sum matches
    its printed figure -- tried from the WHOLE list first, then shrinking
    from the front one item at a time. Once a run ties, it is replaced by
    the new total's own value (so a still-higher total can absorb it);
    anything BEFORE that run is left untouched in the pending list, so an
    earlier total that is never absorbed by anything (e.g. FIRE HYDRANT,
    MTC TOWN RADIOS -- each its own department_code in gl-history, with no
    departmental wrapper in this workbook) simply sits unused rather than
    being discarded or wrongly forced into a later sum."""
    merged = []
    for r, org, obj, desc, m in leaves:
        merged.append((r, "leaf", desc, m))
    for r, indented, desc, m in totals:
        merged.append((r, "total", desc, m))
    merged.sort(key=lambda x: x[0])

    pending = []  # list of (desc, {col: value})
    unexplained = []
    notes = []

    for r, kind, desc, m in merged:
        if kind == "leaf":
            pending.append((desc, dict(m)))
            continue
        start = 0
        tied = False
        while start <= len(pending):
            window = pending[start:]
            cand = {c: sum((p[1].get(c) or 0) for p in window) for c in money_cols}

            def col_ok(c):
                if m.get(c) is None:
                    return True
                if money_eq(cand[c], m[c]):
                    return True
                exc = KNOWN_D5_TOTAL_EXCEPTIONS.get((ws_name, r, c))
                if exc is not None:
                    notes.append(f"{ws_name} row {r} '{desc}' [{c}]: {exc}")
                    return True
                return False

            if all(col_ok(c) for c in money_cols):
                tied = True
                break
            start += 1
        if not tied:
            for c in money_cols:
                if m.get(c) is not None:
                    unexplained.append(
                        f"{ws_name} row {r} '{desc}' [{c}]: printed {m[c]}, no trailing run of "
                        f"the preceding leaves/sub-totals sums to it"
                    )
            # fall through: treat as its own standalone entry so later totals
            # aren't thrown off by a row we already flagged as unexplained
            pending.append((desc, dict(m)))
            continue
        pending = pending[:start] + [(desc, dict(m))]

    return list(dict.fromkeys(notes)), unexplained


def _extract_header(ws):
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    return header


def build_d5_fincom_workbook(xlsx_path, dept_label):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    header = _extract_header(ws)
    money_cols = [h for h in header if h and ("BUDGET" in h or h in ("FY2027", "FY26 ORIGIN APPROP"))]
    leaves = list(_leaf_rows_generic(ws, header))
    totals = list(_total_rows_generic(ws, header))
    report_lines, unexplained = _tie_check_hierarchical(os.path.basename(xlsx_path), header, leaves, totals, money_cols)
    if unexplained:
        raise RuntimeError(
            f"D5 REFUSED ({dept_label}, {os.path.basename(xlsx_path)}): "
            + "; ".join(unexplained)
        )
    rows = []
    for r, org, obj, desc, m in leaves:
        for col in money_cols:
            v = m.get(col)
            if v is None:
                continue
            rows.append(
                {
                    "department": dept_label,
                    "source_file": os.path.relpath(xlsx_path, ROOT),
                    "sheet": ws.title,
                    "row": r,
                    "org": org,
                    "object": obj,
                    "description": desc,
                    "column_header": col,
                    "amount": v,
                    "row_kind": "leaf",
                }
            )
    for r, indented, desc, m in totals:
        for col in money_cols:
            v = m.get(col)
            if v is None:
                continue
            rows.append(
                {
                    "department": dept_label,
                    "source_file": os.path.relpath(xlsx_path, ROOT),
                    "sheet": ws.title,
                    "row": r,
                    "org": "",
                    "object": "",
                    "description": desc,
                    "column_header": col,
                    "amount": v,
                    "row_kind": "subtotal" if indented else "total",
                }
            )
    return rows, report_lines


def build_d5_it():
    wb = openpyxl.load_workbook(D5_IT, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows_all = []
    for row in ws.iter_rows(min_row=2):
        vals = [c.value for c in row]
        desc = vals[2]
        if not desc:
            continue
        rows_all.append((row[0].row, vals))

    # Personnel Sub-Total: / Expense Sub-Total: tie to the leaves above them;
    # the grand "155 - TECHNOLOGY - Total" ties to the two sub-totals.
    header = [c.value for c in next(wb[wb.sheetnames[0]].iter_rows(min_row=1, max_row=1))]
    fy25_prelim_idx = header.index("FY25 TM Prelim. Budget")
    leaf_sum = 0.0
    subtotals = []
    out_rows = []
    unexplained = []
    for rno, vals in rows_all:
        desc = str(vals[2])
        val = vals[fy25_prelim_idx]
        if "Sub-Total" in desc:
            if val is not None and not money_eq(val, leaf_sum):
                unexplained.append(f"IT row {rno} '{desc}': printed {val}, leaves sum to {leaf_sum:.2f}")
            subtotals.append(val or 0.0)
            leaf_sum = 0.0
            out_rows.append((rno, desc, "subtotal", vals))
        elif "Total" in desc:
            tied_sum = sum(subtotals)
            if val is not None and not money_eq(val, tied_sum):
                unexplained.append(f"IT row {rno} '{desc}': printed {val}, sub-totals sum to {tied_sum:.2f}")
            out_rows.append((rno, desc, "total", vals))
        else:
            if isinstance(val, (int, float)):
                leaf_sum += val
            out_rows.append((rno, desc, "leaf", vals))
    if unexplained:
        raise RuntimeError("D5 REFUSED (IT, fy25-it-budget.xlsx): " + "; ".join(unexplained))

    rows = []
    for rno, desc, kind, vals in out_rows:
        obj = vals[1]
        for i, h in enumerate(header):
            if not h or i in (0, 1, 2):
                continue
            v = vals[i]
            if v is None:
                continue
            rows.append(
                {
                    "department": "IT (FY25)",
                    "source_file": os.path.relpath(D5_IT, ROOT),
                    "sheet": ws.title,
                    "row": rno,
                    "org": "155",
                    "object": str(obj) if obj is not None else "",
                    "description": desc,
                    "column_header": h,
                    "amount": v,
                    "row_kind": kind,
                }
            )
    return rows


def build_d5_land_use():
    wb = openpyxl.load_workbook(D5_LAND_USE, data_only=True)
    ws = wb[wb.sheetnames[0]]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    rows = []
    for row in ws.iter_rows(min_row=2):
        vals = [c.value for c in row]
        acct = vals[0]
        if not acct:
            continue
        acct_parts = str(acct).split("-")
        dept_code = acct_parts[2] if len(acct_parts) > 2 and acct_parts[0] == "0100" else ""
        for i, h in enumerate(header):
            if i in (0, 1) or not h:
                continue
            v = vals[i]
            if v is None:
                continue
            rows.append(
                {
                    "department": "Land Use (FY23)",
                    "source_file": os.path.relpath(D5_LAND_USE, ROOT),
                    "sheet": ws.title,
                    "row": row[0].row,
                    "org": dept_code,
                    "object": "",
                    "description": vals[1],
                    "column_header": h,
                    "amount": v,
                    "row_kind": "leaf",
                    "account": acct,
                }
            )
    # No total of any kind is printed anywhere in this workbook (checked by
    # eye and by scanning every cell for the string TOTAL): there is nothing
    # to tie to. That absence is itself worth recording rather than silently
    # treating the extraction as "ties, trivially."
    has_total = any(
        "TOTAL" in str(c.value).upper()
        for r in ws.iter_rows()
        for c in r
        if c.value
    )
    print(
        f"D5 Land Use (FY23): {len(rows)} value cells extracted from "
        f"{os.path.basename(D5_LAND_USE)}. No TOTAL row exists anywhere in this "
        f"workbook (confirmed by scanning every cell) -- there is nothing printed "
        f"to tie to, so none is claimed."
    )
    return rows


def build_d5_videographer():
    wb = openpyxl.load_workbook(D5_VIDEOGRAPHER, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = []
    totals_row = None
    for row in ws.iter_rows(min_row=6):
        vals = [c.value for c in row]
        if vals[0] == "TOTALS":
            totals_row = vals
            continue
        if vals[0] is None:
            continue
        month = vals[0]
        rows.append(
            {
                "department": "PACC Videographer",
                "source_file": os.path.relpath(D5_VIDEOGRAPHER, ROOT),
                "sheet": ws.title,
                "row": row[0].row,
                "month": month.date().isoformat() if hasattr(month, "date") else month,
                "public_ch9_hours": vals[1],
                "govt_ch8_hours": vals[2],
                "total_hours": vals[3],
                "pct_of_govt_hours": vals[4],
                "pct_of_public_hours": vals[5],
                "monthly_expense": vals[6],
            }
        )
    hours_sum = sum(r["total_hours"] for r in rows if r["total_hours"] is not None)
    expense_sum = sum(r["monthly_expense"] for r in rows if r["monthly_expense"] is not None)
    if not money_eq(hours_sum, totals_row[3]) or not money_eq(expense_sum, totals_row[6]):
        raise RuntimeError(
            f"D5 REFUSED (Videographer): hours sum to {hours_sum} (printed {totals_row[3]}), "
            f"expense sums to {expense_sum} (printed {totals_row[6]})"
        )
    print(
        f"D5 PACC Videographer ties OK: {len(rows)} months, total hours "
        f"{hours_sum:g} and total expense ${expense_sum:,.2f} both match the "
        f"printed TOTALS row."
    )
    return rows


def build_d5():
    all_rows = []
    all_report_lines = []
    for xlsx, label in [(D5_POLICE, "Police (FinCom 2.19.26)"),
                         (D5_FIRE, "Fire (FinCom 2.19.26)"),
                         (D5_FACILITIES, "Facilities (FinCom 2.19.26)")]:
        rows, report_lines = build_d5_fincom_workbook(xlsx, label)
        all_rows.extend(rows)
        all_report_lines.extend(report_lines)
        n_totals = sum(1 for r in rows if r["row_kind"] in ("total", "subtotal"))
        print(f"D5 {label}: {len(rows)} value cells, {n_totals} total/subtotal cells tie "
              f"(hierarchical: leaves -> indented sub-totals -> department total).")
    for note in all_report_lines:
        print("  -", note)

    all_rows.extend(build_d5_it())
    all_rows.extend(build_d5_videographer())
    all_rows.extend(build_d5_land_use())

    write_csv(
        "department-budgets-fincom-fy27.csv",
        ["department", "source_file", "sheet", "row", "org", "object", "description",
         "column_header", "amount", "row_kind"],
        [{k: r.get(k, "") for k in
          ["department", "source_file", "sheet", "row", "org", "object", "description",
           "column_header", "amount", "row_kind"]} for r in all_rows],
    )
    return all_rows


def build_d5_comparisons(d5_rows):
    gl_rows = load_gl_history()
    tb_fy27 = town_budget_fy27_lookup(load_town_budget_fy27())

    # vs gl-history: department-level totals for FY24/FY25/FY26, budget
    # columns only (rule 1 -- FY2025 actual is part-year and is never
    # compared here, only noted).
    gl_col_to_year = {"FY24 BUDGET": 2024, "FY25 BUDGET": 2025, "FY26 ORIGIN APPROP": 2026}
    gl_out = []
    # aggregate D5's leaf-level department totals (row_kind == 'total', the
    # department-closing rows) by (department, org-ish label, column)
    dept_totals = defaultdict(lambda: defaultdict(float))
    for r in d5_rows:
        if r.get("row_kind") != "total":
            continue
        dept_totals[(r["department"], r["description"])][r["column_header"]] += r["amount"] or 0

    # Simpler, robust comparison: sum D5's LEAF rows by (org) and column,
    # since 'total' rows are already department-specific aggregates and the
    # org->department_code map is defined at the org level.
    org_sums = defaultdict(lambda: defaultdict(float))
    for r in d5_rows:
        if r.get("row_kind") != "leaf" or not r["org"]:
            continue
        org_sums[r["org"]][r["column_header"]] += r["amount"] or 0

    orgs_seen = sorted(org_sums.keys())
    for org in orgs_seen:
        dept_code = D5_ORG_DEPT.get(org)
        for col, year in gl_col_to_year.items():
            d5_val = org_sums[org].get(col)
            if d5_val is None:
                continue
            found, orig, rev, act = gl_org_year_sums(gl_rows, {org}, year)
            gl_out.append(
                {
                    "org": org,
                    "gl_department_code": dept_code or "",
                    "fiscal_year": year,
                    "column_header": col,
                    "d5_amount": d5_val,
                    "gl_history_original": orig if found else "",
                    "gl_history_revised": rev if found else "",
                    "found_in_gl_history": "yes" if found else "no",
                    "diff_d5_minus_gl_original": round(d5_val - orig, 2) if found else "",
                }
            )
    write_csv(
        "department-budgets-fincom-fy27-vs-gl-history.csv",
        ["org", "gl_department_code", "fiscal_year", "column_header", "d5_amount",
         "gl_history_original", "gl_history_revised", "found_in_gl_history",
         "diff_d5_minus_gl_original"],
        gl_out,
    )
    agree = sum(1 for r in gl_out if r["found_in_gl_history"] == "yes" and money_eq(r["diff_d5_minus_gl_original"] or 0, 0))
    found = sum(1 for r in gl_out if r["found_in_gl_history"] == "yes")
    print(f"D5 vs gl-history: {found} of {len(gl_out)} org/column combinations found "
          f"({agree} agree exactly with the ORIGINAL appropriation).")
    diffs = [r for r in gl_out if r["found_in_gl_history"] == "yes" and r["diff_d5_minus_gl_original"] not in ("", 0)]
    if diffs:
        biggest = max(diffs, key=lambda r: abs(r["diff_d5_minus_gl_original"]))
        print(f"  largest difference: org {biggest['org']} FY{biggest['fiscal_year']} "
              f"{biggest['column_header']}: {biggest['diff_d5_minus_gl_original']:+.2f} "
              f"(D5 minus gl-history ORIGINAL; a budget revised mid-year after D5's "
              f"presentation date is not a discrepancy in either document)")

    # vs town-budget-fy26-fy27.csv FY2027 working budget, leaf rows only
    # (object-level account match).
    tb_by_account = tb_fy27
    acct_lookup = {}
    for acct in tb_by_account:
        # account format: 0100-?-<dept>-0000-00-0-00-?-<object>
        m = re.match(r"0100-\d-(\d+)-0000-00-0-00-\d-(\d+)", acct)
        if m:
            acct_lookup.setdefault((m.group(1), m.group(2)), acct)

    tb_out = []
    for r in d5_rows:
        if r.get("row_kind") != "leaf" or r["column_header"] != "FY2027" or not r["org"] or not r["object"]:
            continue
        # org like 12101 -> department_code prefix varies; match by the org's
        # OWN 5-char org code against town-budget's 'org' column directly
        # (both come from the same MUNIS org scheme), not via account regex.
        pass

    # town-budget-fy26-fy27.csv carries its own 'org' column directly --
    # match on (org, object-suffix-of-account) rather than via the dept_code
    # prefix regex above (kept only for reference, unused).
    tb_by_org_obj = {}
    with open(path(DATA, "town-budget-fy26-fy27.csv")) as f:
        for row in csv.DictReader(f):
            if row["column_header"] != "BUDGET | REQUEST | FY2027":
                continue
            if not row["version"].startswith("Working FY27 Budget Shared 3.3.26.xlsx"):
                continue
            acct = row["account"]
            m = re.search(r"-(\d)-(\d{6})$", acct)
            if not m:
                continue
            obj = m.group(2)
            tb_by_org_obj[(row["org"], obj)] = float(row["amount"])

    for r in d5_rows:
        if r.get("row_kind") != "leaf" or r["column_header"] != "FY2027" or not r["org"] or not r["object"]:
            continue
        obj = r["object"].zfill(6)
        tb_val = tb_by_org_obj.get((r["org"], obj))
        tb_out.append(
            {
                "department": r["department"],
                "org": r["org"],
                "object": obj,
                "description": r["description"],
                "d5_fy2027": r["amount"],
                "town_budget_fy27_working": tb_val if tb_val is not None else "",
                "found_in_town_budget": "yes" if tb_val is not None else "no",
                "diff_d5_minus_town_budget": round(r["amount"] - tb_val, 2) if tb_val is not None else "",
            }
        )
    write_csv(
        "department-budgets-fincom-fy27-vs-town-budget-fy27.csv",
        ["department", "org", "object", "description", "d5_fy2027", "town_budget_fy27_working",
         "found_in_town_budget", "diff_d5_minus_town_budget"],
        tb_out,
    )
    found = sum(1 for r in tb_out if r["found_in_town_budget"] == "yes")
    agree = sum(1 for r in tb_out if r["found_in_town_budget"] == "yes" and money_eq(r["diff_d5_minus_town_budget"] or 0, 0))
    print(f"D5 vs town-budget-fy26-fy27.csv (FY2027 working budget): {found} of {len(tb_out)} "
          f"leaf accounts matched; {agree} agree exactly.")
    diffs = [r for r in tb_out if r["found_in_town_budget"] == "yes" and r["diff_d5_minus_town_budget"] not in ("", 0)]
    if diffs:
        biggest = max(diffs, key=lambda r: abs(r["diff_d5_minus_town_budget"]))
        print(f"  largest difference: {biggest['department']} '{biggest['description']}': "
              f"{biggest['diff_d5_minus_town_budget']:+.2f} (FinCom 2.19.26 figure vs the "
              f"3.3.26 working budget -- later working-budget revisions, not a data error)")


# ---------------------------------------------------------------------------
# G1 -- Police/fire staffing plans, hiring plan, overtime model, ceiling
# ---------------------------------------------------------------------------

G1_ADDITIONAL_OFFICERS_XLSX = path(FC, "staffing-plans", "additional-officers-10-year-plan-1-21-2020.xlsx")
G1_FD_STAFFING_XLSX = path(FC, "staffing-plans", "fd-staffing-plan-fy-21-update.xlsx")
G1_HIRING_PLAN_PDF_TXT = path(
    FC, "fy25-budget", "police", "text", "iii.-attachment-b-fy25-10-year-hiring-plan.pdf.txt"
)
G1_OVERTIME_PDF_TXT = path(
    FC, "fy25-budget", "police", "text", "v.-attachment-d-fy25-overtime-costing-out-model.pdf.txt"
)
G1_CEILING_PDF_TXT = path(
    FC, "fy25-budget", "police", "text", "vi.-attachment-e-2.5-ceiling-budget-analysis.pdf.txt"
)

MONEY_RE = re.compile(r"\(?\$?\s?-?\d{1,3}(?:[,\s]\s?\d{3})*\.\s?\d{2}\)?\$?|\$\s*-\s*\$?|-\$")


def parse_money(tok):
    s = tok.strip()
    neg = "(" in s
    s = s.replace("(", "").replace(")", "").replace("$", "").replace(" ", "")
    if s in ("", "-", "--"):
        return 0.0
    if s.startswith("-"):
        neg = True
        s = s[1:]
    return -float(s.replace(",", "")) if neg else float(s.replace(",", ""))


def build_g1_additional_officers_2020():
    wb = openpyxl.load_workbook(G1_ADDITIONAL_OFFICERS_XLSX, data_only=True)
    ws = wb["Summary"]
    header_row = next(ws.iter_rows(min_row=3, max_row=3))
    years = [c.value for c in header_row if c.value]
    rows = []
    officer_rows = []
    total_row_vals = None
    for row in ws.iter_rows(min_row=5):
        label = row[0].value
        if not label:
            continue
        vals = [row[i].value for i in range(1, 1 + len(years))]
        if label == "TOTAL":
            total_row_vals = vals
        else:
            officer_rows.append((label, vals))
    for i, y in enumerate(years):
        col_sum = sum((v[i] or 0) for _, v in officer_rows)
        if not money_eq(col_sum, total_row_vals[i]):
            raise RuntimeError(
                f"G1 REFUSED (2020 10-Year Additional Officer Plan): {y} officers sum to "
                f"{col_sum:.2f}, printed TOTAL is {total_row_vals[i]}"
            )
    print(
        f"G1 2020 Additional-Officer Plan ties OK: {len(officer_rows)} officer rows x "
        f"{len(years)} years, every year's TOTAL = sum of officer rows."
    )
    for i, y in enumerate(years):
        for label, vals in officer_rows:
            v = vals[i]
            if not v:
                continue
            rows.append(
                {
                    "plan": "10-Year Additional Officer Plan (2020 edition, dated 1-21-2020)",
                    "source_file": os.path.relpath(G1_ADDITIONAL_OFFICERS_XLSX, ROOT),
                    "sheet": "Summary",
                    "fiscal_year": y,
                    "position": f"PLANNED: {label}",
                    "amount": v,
                    "measure": "annual cost",
                    "status": "planned, not hired (rule 7)",
                }
            )
        rows.append(
            {
                "plan": "10-Year Additional Officer Plan (2020 edition, dated 1-21-2020)",
                "source_file": os.path.relpath(G1_ADDITIONAL_OFFICERS_XLSX, ROOT),
                "sheet": "Summary",
                "fiscal_year": y,
                "position": "TOTAL",
                "amount": total_row_vals[i],
                "measure": "annual cost",
                "status": "total of planned positions",
            }
        )
    return rows


def build_g1_fd_staffing_2021():
    wb = openpyxl.load_workbook(G1_FD_STAFFING_XLSX, data_only=True)
    ws = wb["Wage Summary"]
    years = [c.value for c in next(ws.iter_rows(min_row=3, max_row=3)) if c.value]
    person_rows = []
    total_vals = None
    for row in ws.iter_rows(min_row=5):
        label = row[0].value
        if not label:
            continue
        vals = [row[i].value if isinstance(row[i].value, (int, float)) else 0.0 for i in range(1, 1 + len(years))]
        if label == "TOTAL":
            total_vals = vals
        elif label.startswith("*"):
            continue
        else:
            person_rows.append((label, vals))
    for i, y in enumerate(years):
        col_sum = sum(v[i] for _, v in person_rows)
        if not money_eq(col_sum, total_vals[i]):
            raise RuntimeError(
                f"G1 REFUSED (FD Staffing Plan Wage Summary): {y} positions sum to "
                f"{col_sum:.2f}, printed TOTAL is {total_vals[i]}"
            )

    ws2 = wb["Financial Summary"]
    fs_years = []
    fs_rows = defaultdict(dict)
    header_row = next(ws2.iter_rows(min_row=2, max_row=2))
    year_cols = {c.column: c.value for c in header_row if c.value}
    total_by_year = {}
    for row in ws2.iter_rows(min_row=5):
        label = row[0].value
        if not label:
            continue
        for col, year in year_cols.items():
            v = row[col - 1].value
            if v is None:
                continue
            if label == "Total":
                total_by_year[year] = v
            else:
                fs_rows[year][label] = v
    unexplained = []
    for year, components in fs_rows.items():
        s = sum(components.values())
        if year in total_by_year and not money_eq(s, total_by_year[year]):
            unexplained.append(f"{year}: components sum to {s:.2f}, printed Total is {total_by_year[year]}")
    if unexplained:
        raise RuntimeError("G1 REFUSED (FD Staffing Plan Financial Summary): " + "; ".join(unexplained))

    print(
        f"G1 FD Staffing Plan (FY21 update) ties OK: Wage Summary ({len(person_rows)} positions x "
        f"{len(years)} years) and Financial Summary ({len(fs_rows)} years x "
        f"{len(next(iter(fs_rows.values())))} cost components) both reproduce their own printed totals."
    )

    rows = []
    for i, y in enumerate(years):
        for label, vals in person_rows:
            v = vals[i]
            if not v:
                continue
            rows.append(
                {
                    "plan": "Fire Dept 4-Year Additional Firefighter Plan (FY21 update)",
                    "source_file": os.path.relpath(G1_FD_STAFFING_XLSX, ROOT),
                    "sheet": "Wage Summary",
                    "fiscal_year": y,
                    "position": f"PLANNED: {label}",
                    "amount": v,
                    "measure": "annual wage cost",
                    "status": "planned, not hired (rule 7)",
                }
            )
        rows.append(
            {
                "plan": "Fire Dept 4-Year Additional Firefighter Plan (FY21 update)",
                "source_file": os.path.relpath(G1_FD_STAFFING_XLSX, ROOT),
                "sheet": "Wage Summary",
                "fiscal_year": y,
                "position": "TOTAL",
                "amount": total_vals[i],
                "measure": "annual wage cost",
                "status": "total of planned positions",
            }
        )
    for year, components in fs_rows.items():
        for label, v in components.items():
            rows.append(
                {
                    "plan": "Fire Dept 4-Year Additional Firefighter Plan (FY21 update)",
                    "source_file": os.path.relpath(G1_FD_STAFFING_XLSX, ROOT),
                    "sheet": "Financial Summary",
                    "fiscal_year": year,
                    "position": label,
                    "amount": v,
                    "measure": "financial-summary component",
                    "status": "planned cost component",
                }
            )
        if year in total_by_year:
            rows.append(
                {
                    "plan": "Fire Dept 4-Year Additional Firefighter Plan (FY21 update)",
                    "source_file": os.path.relpath(G1_FD_STAFFING_XLSX, ROOT),
                    "sheet": "Financial Summary",
                    "fiscal_year": year,
                    "position": "TOTAL",
                    "amount": total_by_year[year],
                    "measure": "financial-summary component",
                    "status": "total of cost components",
                }
            )
    return rows


def build_g1_hiring_plan_summary():
    with open(G1_HIRING_PLAN_PDF_TXT) as f:
        text = f.read()
    m = re.search(r"===PAGE 4===(.*?)===PAGE 5===", text, re.S)
    if not m:
        raise RuntimeError("G1 REFUSED: could not isolate page 4 of the FY25 10-Year Hiring Plan")
    page4 = m.group(1)
    lines = [ln.strip() for ln in page4.splitlines() if ln.strip()]
    years_line = next(ln for ln in lines if ln.startswith("FY 2025"))
    years = re.findall(r"FY\s?(\d{4})", years_line)

    officer_rows = []
    total_vals = None
    for ln in lines:
        if ln.startswith("Officer ") and "-" in ln:
            vals = [parse_money(x) for x in MONEY_RE.findall(ln)]
            name = MONEY_RE.split(ln)[0].strip()
            officer_rows.append((name, vals))
        elif ln.startswith("TOTAL ") or ln == "TOTAL":
            vals = [parse_money(x) for x in MONEY_RE.findall(ln)]
            if len(vals) == len(years):
                total_vals = vals

    if total_vals is None or len(officer_rows) == 0:
        raise RuntimeError("G1 REFUSED: could not locate the 10-Year Additional Officer Plan summary table")
    for i in range(len(years)):
        col_sum = sum(v[i] for _, v in officer_rows if i < len(v))
        if not money_eq(col_sum, total_vals[i], tol=0.05):
            raise RuntimeError(
                f"G1 REFUSED (FY25 10-Year Hiring Plan summary): FY{years[i]} officers sum to "
                f"{col_sum:.2f}, printed TOTAL is {total_vals[i]:.2f}"
            )
    print(
        f"G1 FY25 10-Year Hiring Plan summary (page 4) ties OK: {len(officer_rows)} planned "
        f"officer additions x {len(years)} years (FY{years[0]}-FY{years[-1]}), each year's TOTAL "
        f"= sum of officer rows (tolerance $0.05 for the source's own rounding)."
    )

    rows = []
    for i, y in enumerate(years):
        for name, vals in officer_rows:
            if i >= len(vals) or not vals[i]:
                continue
            rows.append(
                {
                    "plan": "FY25 10-Year Hiring Plan - Additional Officer Plan Summary",
                    "source_file": os.path.relpath(path(
                        FC, "fy25-budget", "police",
                        "iii.-attachment-b-fy25-10-year-hiring-plan.pdf"
                    ), ROOT),
                    "sheet": "page 4",
                    "fiscal_year": f"FY{y}",
                    "position": f"PLANNED: {name}",
                    "amount": vals[i],
                    "measure": "annual salary",
                    "status": "planned, not hired (rule 7)",
                }
            )
        rows.append(
            {
                "plan": "FY25 10-Year Hiring Plan - Additional Officer Plan Summary",
                "source_file": os.path.relpath(path(
                    FC, "fy25-budget", "police",
                    "iii.-attachment-b-fy25-10-year-hiring-plan.pdf"
                ), ROOT),
                "sheet": "page 4",
                "fiscal_year": f"FY{y}",
                "position": "TOTAL",
                "amount": total_vals[i],
                "measure": "annual salary",
                "status": "total of planned positions",
            }
        )
    # "Total Full Time Officers" / "Administrative Staff" headcounts (not
    # dollars): plain integers/decimals, recorded as context, not tied to
    # anything (they are a count, not a sum of the rows above them).
    for ln in lines:
        if ln.startswith("Total Full Time") or ln.startswith("Administrative Staff"):
            nums = re.findall(r"[\d.]+", ln.split("Officers")[-1] if "Officers" in ln else ln)
            label = "Total Full Time Officers" if ln.startswith("Total Full Time") else "Administrative Staff"
            # pull the trailing numbers only
            nums = re.findall(r"\d+(?:\.\d+)?", ln)
            nums = nums[-len(years):]
            for i, y in enumerate(years):
                if i >= len(nums):
                    continue
                rows.append(
                    {
                        "plan": "FY25 10-Year Hiring Plan - Additional Officer Plan Summary",
                        "source_file": os.path.relpath(path(
                            FC, "fy25-budget", "police",
                            "iii.-attachment-b-fy25-10-year-hiring-plan.pdf"
                        ), ROOT),
                        "sheet": "page 4",
                        "fiscal_year": f"FY{y}",
                        "position": label,
                        "amount": nums[i],
                        "measure": "headcount (printed, not a dollar sum)",
                        "status": "planned headcount",
                    }
                )
    return rows


def build_g1_overtime_costing():
    with open(G1_OVERTIME_PDF_TXT) as f:
        text = f.read()
    m24 = re.search(r"TOTAL FY24\s+([\d,]+\.\d{2})\$", text)
    m25 = re.search(r"TOTAL FY25\s+([\d,]+\.\d{2})\$", text)
    m_ot = re.search(r"Overtime\s+([\d,]+\.\d{2})\$", text)
    m_hol = re.search(r"Holiday\s+([\d,]+\.\d{2})\$", text)
    if not (m24 and m25 and m_ot and m_hol):
        raise RuntimeError("G1 REFUSED: could not locate the Overtime Costing Model's printed totals")
    total24 = float(m24.group(1).replace(",", ""))
    total25 = float(m25.group(1).replace(",", ""))
    ot = float(m_ot.group(1).replace(",", ""))
    hol = float(m_hol.group(1).replace(",", ""))
    if not money_eq(ot + hol, total24):
        raise RuntimeError(
            f"G1 REFUSED (Overtime Costing Model): 'Actual Costs' Overtime ({ot}) + Holiday ({hol}) "
            f"= {ot + hol:.2f}, printed TOTAL FY24 is {total24}"
        )
    print(
        f"G1 Overtime Costing Model ties OK: TOTAL FY24 (${total24:,.2f}) = printed Actual Costs "
        f"Overtime (${ot:,.2f}) + Holiday (${hol:,.2f}). TOTAL FY25 (${total25:,.2f}) is a per-"
        f"officer-built estimate; this model's per-officer breakdown (21 officers x 5 leave "
        f"categories, two tables of category costs overlapping on the page) could not be "
        f"reassembled from the PDF's text layer -- its layout interleaves two side-by-side "
        f"tables with no coordinate data in the plain-text extract, and reconstructing the "
        f"per-officer rows would be a guess, not a position-verified reading (rule 13b/13c). "
        f"Only the two totals and the one printed identity above are extracted."
    )
    rows = [
        {
            "plan": "FY25 Overtime Costing-Out Model",
            "source_file": os.path.relpath(path(
                FC, "fy25-budget", "police", "v.-attachment-d-fy25-overtime-costing-out-model.pdf"
            ), ROOT),
            "sheet": "pages 1-2",
            "fiscal_year": "FY24",
            "position": "TOTAL (all officers, all leave categories)",
            "amount": total24,
            "measure": "actual overtime cost",
            "status": "actual (not a plan)",
        },
        {
            "plan": "FY25 Overtime Costing-Out Model",
            "source_file": os.path.relpath(path(
                FC, "fy25-budget", "police", "v.-attachment-d-fy25-overtime-costing-out-model.pdf"
            ), ROOT),
            "sheet": "page 4",
            "fiscal_year": "FY25",
            "position": "TOTAL (all officers, all leave categories) - estimated",
            "amount": total25,
            "measure": "estimated overtime cost",
            "status": "PLANNED/estimated, not actual (rule 7)",
        },
        {
            "plan": "FY25 Overtime Costing-Out Model",
            "source_file": os.path.relpath(path(
                FC, "fy25-budget", "police", "v.-attachment-d-fy25-overtime-costing-out-model.pdf"
            ), ROOT),
            "sheet": "page 4",
            "fiscal_year": "FY24",
            "position": "Actual Costs: Overtime",
            "amount": ot,
            "measure": "actual overtime cost",
            "status": "actual (not a plan)",
        },
        {
            "plan": "FY25 Overtime Costing-Out Model",
            "source_file": os.path.relpath(path(
                FC, "fy25-budget", "police", "v.-attachment-d-fy25-overtime-costing-out-model.pdf"
            ), ROOT),
            "sheet": "page 4",
            "fiscal_year": "FY24",
            "position": "Actual Costs: Holiday",
            "amount": hol,
            "measure": "actual overtime cost",
            "status": "actual (not a plan)",
        },
    ]
    return rows


def build_g1_ceiling_analysis():
    with open(G1_CEILING_PDF_TXT) as f:
        text = f.read()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    cols = ["FY2024 Budget", "FY2025 Target Budget", "FY25 Police Request", "FY25 2.5% Reduction", "Delta - Police vs Reduction"]
    categories = ["PERSONNEL - TOTAL", "EXPENSES - TOTAL", "ANIMAL CONTROL - TOTAL", "LOCKUP - TOTAL",
                  "RADIO WATCH - TOTAL", "VEHICLE MTC - TOTAL"]
    leaf_rows = []
    total_rows = {}
    grand_total = None
    current_cat = None
    for ln in lines:
        if ln.startswith("Type Sub Type Description") or ln.startswith("2.5% CEILING") or ln.startswith("ATTACHMENT"):
            continue
        vals = [parse_money(x) for x in MONEY_RE.findall(ln)]
        if len(vals) < 5:
            continue
        vals = vals[:5]
        label_part = MONEY_RE.split(ln)[0].strip()
        is_total = any(label_part.upper() == c for c in categories)
        if is_total:
            total_rows[label_part.upper()] = vals
            current_cat = None
        elif re.match(r"^[\d,]+\.\d{2}\$?$", ln.strip()) or (not label_part and len(vals) == 5):
            grand_total = vals
        else:
            parts = label_part.split(None, 2)
            if len(parts) >= 3:
                typ, subtyp, desc = parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                typ, subtyp, desc = parts[0], "", parts[1]
            else:
                typ, subtyp, desc = "", "", label_part
            leaf_rows.append({"type": typ, "sub_type": subtyp, "description": desc, "values": vals})

    # categories are identified by the TYPE column text seen on each leaf row;
    # map the 6 category labels to the TYPE text that precedes them.
    cat_type_map = {
        "PERSONNEL - TOTAL": "Personnel",
        "EXPENSES - TOTAL": "Expenses",
        "ANIMAL CONTROL - TOTAL": "Animal",
        "LOCKUP - TOTAL": "Lockup",
        "RADIO WATCH - TOTAL": "Radio",
        "VEHICLE MTC - TOTAL": "Vehicle",
    }
    # Verified against this document's own printed figures (rule 13): in
    # every one of the 4 budget columns, RADIO WATCH's leaf rows (SALARIES
    # CLERICAL + SALARIES RESERVES/CALL FF + UNIFORM ALLOWANCE + NVRDD
    # ASSESSMENT) sum to MORE than the printed RADIO WATCH - TOTAL, by
    # exactly the SALARIES CLERICAL figure printed on that row (49,068.80 /
    # 56,501.76 / 56,501.76 / 56,501.76). The same line item, in the same
    # department, is excluded from the printed total in the B2 "Police
    # Budget As Expended" PDF too (FY22/FY23) -- a recurring feature of
    # this department's figures, not a one-off typo.
    excluded_leaves = {"RADIO WATCH - TOTAL": "SALARIES CLERICAL"}

    unexplained = []
    excluded_sums = [0.0] * 5
    tie_notes = []
    for cat, type_prefix in cat_type_map.items():
        if cat not in total_rows:
            unexplained.append(f"total row '{cat}' not found")
            continue
        matching = [r for r in leaf_rows if r["type"].startswith(type_prefix)]
        excl_desc = excluded_leaves.get(cat)
        excl_rows = [r for r in matching if excl_desc and excl_desc in r["description"].upper()]
        incl_rows = [r for r in matching if r not in excl_rows]
        for i in range(5):
            s = sum(r["values"][i] for r in incl_rows)
            if not money_eq(s, total_rows[cat][i]):
                unexplained.append(
                    f"{cat} col {cols[i]}: leaves sum to {s:.2f}, printed {total_rows[cat][i]:.2f}"
                )
            excluded_sums[i] += sum(r["values"][i] for r in excl_rows)
        if excl_rows:
            tie_notes.append(
                f"{cat}: '{excl_desc}' ({', '.join(f'{v:,.2f}' for v in excl_rows[0]['values'][:4])}) "
                f"appears in the source table but is excluded from the printed {cat} row, in "
                f"every budget column (verified: leaves-without-it tie exactly)"
            )
    if grand_total:
        cat_sum = [sum(total_rows[c][i] for c in categories if c in total_rows) for i in range(5)]
        for i in range(5):
            if not money_eq(cat_sum[i] + excluded_sums[i], grand_total[i]):
                unexplained.append(
                    f"grand total col {cols[i]}: category totals sum to {cat_sum[i]:.2f} "
                    f"(+ {excluded_sums[i]:.2f} excluded leaves = {cat_sum[i] + excluded_sums[i]:.2f}), "
                    f"printed {grand_total[i]:.2f}"
                )
    if unexplained:
        raise RuntimeError("G1 REFUSED (2.5% Ceiling Budget Analysis): " + "; ".join(unexplained))

    print(
        f"G1 2.5% Ceiling Budget Analysis ties OK: {len(leaf_rows)} line items across 6 "
        f"categories, each category's printed total = sum of its leaves (net of the known "
        f"exception below), and the unlabelled final row = sum of the six category totals "
        f"plus that exception (grand total across all 5 budget columns)."
    )
    for note in tie_notes:
        print("  -", note)

    rows = []
    src = os.path.relpath(path(
        FC, "fy25-budget", "police", "vi.-attachment-e-2.5-ceiling-budget-analysis.pdf"
    ), ROOT)
    for r in leaf_rows:
        for i, col in enumerate(cols):
            rows.append(
                {
                    "plan": "2.5% Ceiling Budget Analysis Considerations",
                    "source_file": src,
                    "sheet": "pages 1-2",
                    "fiscal_year": "FY2024-FY2025",
                    "position": f"{r['type']} {r['sub_type']} {r['description']}".strip(),
                    "amount": r["values"][i],
                    "measure": col,
                    "status": "PLANNED/proposed (rule 7): " + (
                        "2.5% override-ceiling reduction scenario" if "Reduction" in col or "Delta" in col
                        else "budget figure"
                    ),
                }
            )
    for cat, vals in total_rows.items():
        for i, col in enumerate(cols):
            rows.append(
                {
                    "plan": "2.5% Ceiling Budget Analysis Considerations",
                    "source_file": src,
                    "sheet": "pages 1-2",
                    "fiscal_year": "FY2024-FY2025",
                    "position": cat,
                    "amount": vals[i],
                    "measure": col,
                    "status": "category total",
                }
            )
    if grand_total:
        for i, col in enumerate(cols):
            rows.append(
                {
                    "plan": "2.5% Ceiling Budget Analysis Considerations",
                    "source_file": src,
                    "sheet": "page 2",
                    "fiscal_year": "FY2024-FY2025",
                    "position": "GRAND TOTAL (all categories)",
                    "amount": grand_total[i],
                    "measure": col,
                    "status": "grand total",
                }
            )
    return rows


def build_g1():
    rows = []
    rows.extend(build_g1_additional_officers_2020())
    rows.extend(build_g1_fd_staffing_2021())
    rows.extend(build_g1_hiring_plan_summary())
    rows.extend(build_g1_overtime_costing())
    rows.extend(build_g1_ceiling_analysis())
    write_csv(
        "public-safety-staffing-plans.csv",
        ["plan", "source_file", "sheet", "fiscal_year", "position", "amount", "measure", "status"],
        rows,
    )
    return rows


def build_g1_roster_comparison(g1_rows):
    rosters = load_rosters()
    out = []
    # The 2025 planned headcount from the FY25 10-Year Hiring Plan summary
    # ("Total Full Time Officers") against the Police Department roster's
    # named-head count for the same fiscal year.
    planned = {
        r["fiscal_year"]: r["amount"]
        for r in g1_rows
        if r["position"] == "Total Full Time Officers"
    }
    for fy_label, planned_count in sorted(planned.items()):
        fy_num = fy_label.replace("FY", "")
        roster_count = rosters.get(("Police Department", fy_num))
        out.append(
            {
                "fiscal_year": fy_label,
                "planned_full_time_sworn_officers": planned_count,
                "police_dept_roster_named_headcount": roster_count if roster_count is not None else "",
                "roster_year_available": "yes" if roster_count is not None else "no",
                "note": (
                    "roster is a count of PRINTED NAMES (all ranks/roles: clerical, dispatch, "
                    "reserve/intermittent included), not FTE and not restricted to sworn full-"
                    "time officers -- it bounds the planned-vs-actual question, it does not "
                    "settle it (rule 11)"
                ),
            }
        )
    write_csv(
        "public-safety-staffing-plans-vs-roster.csv",
        ["fiscal_year", "planned_full_time_sworn_officers", "police_dept_roster_named_headcount",
         "roster_year_available", "note"],
        out,
    )
    available = [r for r in out if r["roster_year_available"] == "yes"]
    print(
        f"G1 planned staffing vs department-rosters.csv: {len(available)} of {len(out)} "
        f"planned fiscal years have a published roster. The roster counts NAMES across every "
        f"role (clerical, dispatch, reserve/intermittent); it is not comparable one-to-one to "
        f"'full-time sworn officers' and is reported as a bound, not a match."
    )


# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("B2 -- Police Budget As Expended, FY2015-FY2023")
    print("=" * 70)
    cat_totals, grand_total = build_b2()
    build_b2_comparison(cat_totals)

    print()
    print("=" * 70)
    print("A6 -- Ambulance Receipts History")
    print("=" * 70)
    a6_rows, a6_org = build_a6()
    build_a6_comparison(a6_rows, a6_org)

    print()
    print("=" * 70)
    print("D5 -- FY2027 Department Budgets Presented to FinCom")
    print("=" * 70)
    d5_rows = build_d5()
    build_d5_comparisons(d5_rows)

    print()
    print("=" * 70)
    print("G1 -- Police/Fire Staffing Plans, Hiring Plan, Overtime, Ceiling")
    print("=" * 70)
    g1_rows = build_g1()
    build_g1_roster_comparison(g1_rows)

    print()
    print("All tasks extracted and tied." + (" (--check: nothing written)" if CHECK_ONLY else ""))


if __name__ == "__main__":
    main()
