#!/usr/bin/env python3
"""The 4 September 2026 MUNIS records request, laid out fund by fund, as a spreadsheet.

The request itself (notes/outbound/drafts/RECORDS-REQUEST-TOWN-ACCOUNTANT.md) asks for five
report configurations across 61 school funds, the general fund school departments and ten
revenue accounts. This puts every one of those on its own row, with a cell for every report
and year, so the Town and we can tick off the same grid and write the date each one arrived.

Inputs, both read rather than typed:
  - the fund list and revenue accounts: the tables in the request as sent
  - each fund's balance and the Town's own section heading: its FY26 special revenue report,
    period 9 (31 March 2026), sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx

    python3 scripts/build_munis_request_xlsx.py
"""
import datetime as dt
import re
import sys
from pathlib import Path

import openpyxl
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
REQUEST = ROOT / "notes/outbound/drafts/RECORDS-REQUEST-TOWN-ACCOUNTANT.md"
SPECREV = ROOT / "sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx"
OUT = ROOT / "notes/outbound/drafts/MUNIS-REQUEST-FUNDS.xlsx"

REQUESTED = "2026-09-04"
YEARS = [2023, 2024, 2025, 2026]
# (item number in the request, short heading, what it is)
REPORTS = [
    ("1", "Year-end budget report", "glytdbud, EXPENSE, period 13"),
    ("2", "Account Detail", "every transaction, all columns"),
    ("3", "Transfers", "from, to, amount, date, authority"),
    ("5", "POs closed after year-end", "amounts and dates"),
]
# What we already hold, by (fund, item, year). Everything else is needed.
HELD = {
    ("1301", "2", 2024): "HAVE — Jun 2026 request",
    ("1301", "2", 2025): "HAVE — Jun 2026 request",
    ("1301", "2", 2026): "HAVE — Jun 2026 request",
}

# WHAT ARRIVED, READ FROM THE DATA RATHER THAN TYPED. The Town's 6 October 2026 answer is
# extracted to sources/data/munis-school-ytd.csv; a fund-year counts as received for item 1
# exactly when that file holds the fund for that year. Department 301 is never in it -- the
# report was run for orgs beginning S, department 300 -- so its row stays NEED.
DELIVERED_ON = "2026-10-06"
YTD = ROOT / "sources/data/munis-school-ytd.csv"
TB = ROOT / "sources/data/munis-trial-balance-journal.csv"
PARTIAL = PatternFill("solid", fgColor="FFD9A8")


def delivered():
    """{(fund-or-dept-row key, fiscal year)} the 6 October delivery holds for item 1."""
    import csv
    got = set()
    if not YTD.exists():
        return got
    for r in csv.DictReader(YTD.open(encoding="utf-8")):
        fy = int(str(r["fiscal_year"])[-4:])
        if r["report"] == "gf-school":
            seg = r["account"].split("-")
            got.add(("0100/" + (seg[2] if len(seg) > 2 else "?"), fy))
        else:
            got.add((r["fund"], fy))
    return got


YELLOW = PatternFill("solid", fgColor="FFF4C2")
GREEN = PatternFill("solid", fgColor="CDEFD3")
GREY = PatternFill("solid", fgColor="E7E7E7")
HEAD = PatternFill("solid", fgColor="1F3A5F")
SUB = PatternFill("solid", fgColor="D9E2EF")
WHITE_B = Font(bold=True, color="FFFFFF")
BOLD = Font(bold=True)
THIN = Side(style="thin", color="B0B0B0")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTRE = Alignment(horizontal="center", vertical="center", wrap_text=True)


def request_funds():
    text = REQUEST.read_text()
    funds = {}
    for num, name in re.findall(r"\*\*(\d{4})\*\* \| ([^|]+?) \|", text):
        funds[num] = name.strip()
    accounts = re.findall(r"\| `(0100-01001-\d{6})` \| ([^|]+?) \| ([\d,]+) \|", text)
    if len(funds) != 61 or len(accounts) != 10:
        sys.exit(f"request parse: {len(funds)} funds, {len(accounts)} revenue accounts; expected 61 and 10")
    return funds, accounts


def town_sections():
    """fund -> (Town's section heading verbatim, balance as printed, sheet row)."""
    ws = openpyxl.load_workbook(SPECREV, data_only=True).active
    out, pending = {}, []
    for i, r in enumerate(ws.iter_rows(values_only=True), 1):
        if i <= 8:
            continue
        if r[0] is None and r[1] and str(r[1]).strip():
            for f, bal, row in pending:
                out.setdefault(f, (str(r[1]).strip(), bal, row))
            pending = []
        elif r[0] is not None and r[2] in (300, 301):
            f = str(r[0]).strip().strip("'")
            bal = r[15] if isinstance(r[15], (int, float)) else None
            pending.append((f, bal, i))
    return out


def kind(num, name):
    n = name.upper()
    if num == "2640":
        return "Circuit breaker (state)"
    if num == "2200":
        return "School lunch"
    if "GIFT" in n:
        return "Gift"
    if "REVOLV" in n or num.startswith("13"):
        return "Revolving"
    if num.startswith("29"):
        return "Private grant"
    if num.startswith("27") or num.startswith("28") or num == "2690":
        return "Federal grant"
    return "State / other grant"


def grant_year(name):
    m = re.match(r"\s*'?FY(\d{2})\b", name)
    return 2000 + int(m.group(1)) if m else None


def header(ws, row, values, fill=HEAD, font=WHITE_B):
    for c, v in enumerate(values, 1):
        cell = ws.cell(row=row, column=c, value=v)
        cell.fill, cell.font, cell.alignment, cell.border = fill, font, CENTRE, BOX


def status_rule(ws, rng, first):
    # a date typed over NEED turns the cell green
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f"ISNUMBER({first})"], fill=GREEN))


def build():
    funds, accounts = request_funds()
    sections = town_sections()
    missing = [f for f in funds if f not in sections]
    if missing:
        sys.exit(f"funds in the request not found in the FY26 special revenue report: {missing}")

    wb = openpyxl.Workbook()

    # ---------------------------------------------------------------- Funds
    ws = wb.active
    ws.title = "Funds"
    ws["A1"] = "School funds — which reports we are asking for, by fund and fiscal year"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = ("Records request of 4 September 2026. Yellow = still needed. Grey = probably no "
                "activity that year. Type the DATE a report arrives over the cell and it turns green.")
    ws["A2"].alignment = Alignment(wrap_text=False)

    fixed = ["Fund", "Fund name (as the Town prints it)", "Kind\n(our reading)",
             "Section in the Town's FY26\nspecial revenue report", "Balance 31 Mar 2026\n(as printed; minus = available)"]
    nfix = len(fixed)
    # row 4: report group headings, row 5: years
    header(ws, 4, [""] * (nfix + len(REPORTS) * len(YEARS) + 1))
    header(ws, 5, fixed + [""] * (len(REPORTS) * len(YEARS)) + ["Notes"])
    for k, (item, title, what) in enumerate(REPORTS):
        c0 = nfix + 1 + k * len(YEARS)
        ws.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + len(YEARS) - 1)
        ws.cell(row=4, column=c0, value=f"Item {item} · {title}\n{what}")
        for j, fy in enumerate(YEARS):
            cell = ws.cell(row=5, column=c0 + j, value=f"FY{fy % 100}")
            cell.fill, cell.font, cell.alignment, cell.border = SUB, BOLD, CENTRE, BOX
    ws.row_dimensions[4].height = 44
    ws.row_dimensions[5].height = 44

    rows = [("0100", "GENERAL FUND — school department 300", "General fund", "fund 0100, dept 300", None, ""),
            ("0100", "GENERAL FUND — school department 301", "General fund", "fund 0100, dept 301", None, "")]
    for num in sorted(funds):
        sec, bal, srow = sections[num]
        rows.append((num, funds[num], kind(num, funds[num]), sec, bal, f"row {srow}"))

    got = delivered()
    r = 6
    for num, name, knd, sec, bal, srow in rows:
        gy = grant_year(name)
        notes = []
        ws.cell(row=r, column=1, value=num)
        ws.cell(row=r, column=2, value=name)
        ws.cell(row=r, column=3, value=knd)
        ws.cell(row=r, column=4, value=sec)
        c = ws.cell(row=r, column=5, value=bal)
        c.number_format = '#,##0.00;[Red]-#,##0.00'
        for k, (item, _, _) in enumerate(REPORTS):
            for j, fy in enumerate(YEARS):
                cell = ws.cell(row=r, column=nfix + 1 + k * len(YEARS) + j)
                held = HELD.get((num, item, fy))
                key = ("0100/" + ("301" if "301" in name else "300")) if num == "0100" else num
                if item == "1" and (key, fy) in got:
                    cell.value, cell.fill = "HAVE — 6 Oct 2026", GREEN
                elif item == "2" and num == "1300" and fy == 2026 and TB.exists():
                    cell.value, cell.fill = "PART — trial balance + journal, 6 Oct", PARTIAL
                elif held:
                    cell.value, cell.fill = held, GREEN
                elif gy and fy < gy:
                    cell.value, cell.fill = "n/a?", GREY
                else:
                    cell.value, cell.fill = "NEED", YELLOW
                cell.alignment, cell.border = CENTRE, BOX
                cell.number_format = "d mmm yyyy"
        if num == "0100" and "300" in name:
            notes.append("Period 13 for FY23–FY26 received 6 Oct 2026 (orgs beginning S).")
        if num == "0100" and "301" in name:
            notes.append("Not in the 6 Oct 2026 delivery: the report was run for department 300 only.")
        if num == "1300":
            notes.append("FY26 trial balance with every journal line received 6 Oct 2026 -- a trial balance, not the full Account Detail export.")
        if num == "1301":
            notes.append("Athletics. Account Detail FY24–26 already received; not needed again.")
        if num == "2903":
            notes.append("Printed twice in the Town's FY26 report (rows 150 and 241).")
        if num == "2640":
            notes.append("Offsets the placement lines that moved most in FY26.")
        if num in ("2813", "2814"):
            notes.append("Likely federal special-education grant (our reading of the name).")
        if gy and gy > YEARS[0]:
            notes.append(f"Grey cells: grant named FY{gy % 100}, so probably nothing before. If there was, please include it.")
        nc = ws.cell(row=r, column=nfix + len(REPORTS) * len(YEARS) + 1, value=" ".join(notes))
        nc.alignment = WRAP
        for col in range(1, nfix + 1):
            ws.cell(row=r, column=col).border = BOX
            ws.cell(row=r, column=col).alignment = WRAP
        r += 1
    last = r - 1
    first_cell = f"{get_column_letter(nfix + 1)}6"
    status_rule(ws, f"{get_column_letter(nfix + 1)}6:{get_column_letter(nfix + len(REPORTS) * len(YEARS))}{last}", first_cell)

    widths = [7, 34, 16, 22, 16] + [9] * (len(REPORTS) * len(YEARS)) + [60]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=6, column=3)
    ws.auto_filter.ref = f"A5:{get_column_letter(len(widths))}{last}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = "4:5"

    # ---------------------------------------------------------------- Revenue accounts
    wr = wb.create_sheet("Revenue accounts")
    wr["A1"] = "Revenue accounts — items 2 and 4"
    wr["A1"].font = Font(bold=True, size=14)
    wr["A2"] = ("These ten, and any other revenue account bearing on the schools. None of these sits "
                "in a school department, so if school revenue is recorded somewhere else, please say.")
    rev_reports = [("2", "Account Detail\nevery receipt"), ("4", "Year-end budget report\nglytdbud, REVENUE, period 13")]
    fixed_r = ["Account", "Name (as printed)", "FY26 received\n(from the FY26 p9 report)"]
    header(wr, 4, [""] * (len(fixed_r) + len(rev_reports) * len(YEARS)))
    header(wr, 5, fixed_r + [""] * (len(rev_reports) * len(YEARS)))
    for k, (item, title) in enumerate(rev_reports):
        c0 = len(fixed_r) + 1 + k * len(YEARS)
        wr.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + len(YEARS) - 1)
        wr.cell(row=4, column=c0, value=f"Item {item} · {title}")
        for j, fy in enumerate(YEARS):
            cell = wr.cell(row=5, column=c0 + j, value=f"FY{fy % 100}")
            cell.fill, cell.font, cell.alignment, cell.border = SUB, BOLD, CENTRE, BOX
    wr.row_dimensions[4].height = 44
    wr.row_dimensions[5].height = 44
    for i, (acct, name, amt) in enumerate(accounts):
        rr = 6 + i
        wr.cell(row=rr, column=1, value=acct)
        wr.cell(row=rr, column=2, value=name.strip())
        c = wr.cell(row=rr, column=3, value=int(amt.replace(",", "")))
        c.number_format = "#,##0"
        for k, (item, _) in enumerate(rev_reports):
            for j, fy in enumerate(YEARS):
                cell = wr.cell(row=rr, column=len(fixed_r) + 1 + k * len(YEARS) + j)
                if item == "4" and fy == 2026:
                    cell.value, cell.fill = "optional", GREY
                else:
                    cell.value, cell.fill = "NEED", YELLOW
                cell.alignment, cell.border, cell.number_format = CENTRE, BOX, "d mmm yyyy"
        for col in range(1, len(fixed_r) + 1):
            wr.cell(row=rr, column=col).border = BOX
    rlast = 6 + len(accounts) - 1
    status_rule(wr, f"D6:{get_column_letter(len(fixed_r) + len(rev_reports) * len(YEARS))}{rlast}", "D6")
    for i, w in enumerate([22, 14, 16] + [9] * (len(rev_reports) * len(YEARS)), 1):
        wr.column_dimensions[get_column_letter(i)].width = w
    wr.freeze_panes = "C6"

    # ---------------------------------------------------------------- Report runs
    wn = wb.create_sheet("Report runs")
    wn["A1"] = "Every report run, with its dates"
    wn["A1"].font = Font(bold=True, size=14)
    wn["A2"] = ("One row per report and fiscal year — 23 runs. If several come out of one export, "
                "that is better; write the same date on each row it covers.")
    cols = ["Ref", "Report", "How it is run (our reading of MUNIS)", "Fiscal year",
            "Covers", "Funds / accounts", "Date requested", "Date the Town expects to send",
            "Date received", "File name(s) received", "Notes"]
    header(wn, 4, cols)
    wn.row_dimensions[4].height = 32
    how = {
        "1a": "glytdbud · Account type EXPENSE · Print totals only N · Suppress zero N · Year/Period YYYY/13",
        "1b": "glytdbud · Account type EXPENSE · Print totals only N · Suppress zero N · Year/Period YYYY/13",
        "2": "Account Detail export, all columns (must include object code)",
        "3": "Line-item transfer report — name unknown to us",
        "4": "glytdbud · Account type REVENUE · Print totals only N · Year/Period YYYY/13",
        "5": "Purchase orders closed after the year closed — name unknown to us",
    }
    scope = {
        "1a": "Fund 0100, departments 300 and 301",
        "1b": "The 61 school funds (Funds tab)",
        "2": "Fund 0100 depts 300 and 301, the 61 school funds, and the 10 revenue accounts",
        "3": "Fund 0100 depts 300 and 301, and the 61 school funds",
        "4": "The 10 revenue accounts (Revenue accounts tab)",
        "5": "Fund 0100 depts 300 and 301, and the 61 school funds",
    }
    name = {"1a": "Year-end budget report — expenditures, general fund",
            "1b": "Year-end budget report — expenditures, school funds",
            "2": "Account Detail — every transaction",
            "3": "Line-item transfers",
            "4": "Year-end budget report — revenue",
            "5": "Purchase orders closed after year-end"}
    runs = []
    for g in ("1a", "1b", "2", "3"):
        runs += [(g, fy) for fy in YEARS]
    runs += [("4", fy) for fy in (2023, 2024, 2025)]
    runs += [("5", fy) for fy in YEARS]
    assert len(runs) == 23
    for i, (g, fy) in enumerate(runs):
        rr = 5 + i
        period = "year-end close (period 13)" if g in ("1a", "1b", "4") else "the whole year"
        note = ""
        if g == "2" and fy >= 2024:
            note = "Fund 1301 (athletics) already received for this year — everything else needed."
        received, files = None, None
        if g == "1a" and ("0100/300", fy) in got:
            received = dt.date.fromisoformat(DELIVERED_ON)
            files = f"glytdbud-expense-fy{fy}-p13-gf-school.xlsx"
            note = "Department 300 only -- department 301 was not included."
        if g == "1b" and all((f, fy) in got for f in funds):
            received = dt.date.fromisoformat(DELIVERED_ON)
            files = f"glytdbud-expense-fy{fy}-p13-special-school.xlsx"
            note = f"All {len(funds)} funds."
        if g == "2" and fy == 2026 and TB.exists():
            note = ("Fund 1300 only, as a trial balance with journal lines (6 Oct 2026); "
                    "everything else still needed. Fund 1301 received earlier.")
        vals = [f"{g}.{fy % 100}", name[g], how[g], f"FY{fy}",
                f"1 Jul {fy - 1} – 30 Jun {fy}, {period}", scope[g], REQUESTED, None, received, files, note]
        for c, v in enumerate(vals, 1):
            cell = wn.cell(row=rr, column=c, value=v)
            cell.border, cell.alignment = BOX, WRAP
        wn.cell(row=rr, column=7).number_format = "yyyy-mm-dd"
        for c in (8, 9):
            wn.cell(row=rr, column=c).fill = YELLOW
            wn.cell(row=rr, column=c).number_format = "d mmm yyyy"
    nlast = 5 + len(runs) - 1
    status_rule(wn, f"H5:I{nlast}", "H5")
    for i, w in enumerate([7, 30, 38, 10, 26, 32, 12, 14, 12, 28, 40], 1):
        wn.column_dimensions[get_column_letter(i)].width = w
    wn.freeze_panes = "C5"

    # ---------------------------------------------------------------- How to read
    wk = wb.create_sheet("How to read this")
    lines = [
        ("What this is", "The records request of 4 September 2026, laid out one fund per row so nothing is ambiguous."),
        ("Format", "The spreadsheet export, please — it carries the full account code. The printed copy alongside if that is no trouble."),
        ("NEED (yellow)", "Not yet received. Type the date it arrives over the word and the cell turns green."),
        ("HAVE (green)", "Already received; no need to send again. Cells reading 'HAVE — 6 Oct 2026' are filled from the delivered data itself (sources/data/munis-school-ytd.csv), not typed."),
        ("PART (orange)", "Some of what was asked for arrived, not all of it -- the note says what is still needed."),
        ("n/a? (grey)", "Our guess, from the fund's name, that it had no activity that year. If it did, please include it."),
        ("Kind", "Our reading of the fund name. The Town's own section heading is in the next column, verbatim."),
        ("Balance", "As printed in the Town's FY26 special revenue report, period 9 (31 March 2026). Minus is the available balance, per the report's own note."),
        ("Shape", "A row is not a file. If one export covers many funds or years, that is better — write its date on every cell it covers."),
        ("Source", "Funds and revenue accounts: the request as sent. Balances and sections: special-revenue-fy2026-p09.xlsx. Built by scripts/build_munis_request_xlsx.py."),
    ]
    wk.column_dimensions["A"].width = 18
    wk.column_dimensions["B"].width = 110
    for i, (a, b) in enumerate(lines, 1):
        wk.cell(row=i, column=1, value=a).font = BOLD
        wk.cell(row=i, column=2, value=b).alignment = WRAP
    wk["A3"].fill, wk["A4"].fill, wk["A5"].fill = YELLOW, GREEN, GREY

    wb.save(OUT)
    need = sum(1 for row in ws.iter_rows(min_row=6, max_row=last) for c in row if c.value == "NEED")
    print(f"{OUT.relative_to(ROOT)}: {len(rows)} fund rows, {len(accounts)} revenue accounts, "
          f"{len(runs)} runs; {need} fund-year cells NEED")


if __name__ == "__main__":
    build()
