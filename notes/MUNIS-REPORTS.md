# The Town's reports, what each one answers, and how to ask for it

A working reference, for us. `DATA-REQUEST.md` is generated and says what is *outstanding*;
`DATA-WANTED.md` says what we cannot get at all. This says **what exists, what it is called,
what parameters produce it, and which question it can answer** — so a request can be written
in the Town's own terms instead of described.

Everything below is either verified against a document we hold, or marked as inference.

---

## 1. The account code, and why it decides everything

The Town's system codes every account. Two forms of that code reach us, and the difference
is the single most consequential thing on this page.

**What the printed report gives** — what our database holds today:

    0100-S2055101-511001
    fund  org        object

**What a spreadsheet export gives** — from the Town Manager's own example:

    0100-3-300-2710-04-4-65-1-511024

Reading positionally, the fourth segment (`2710`) is the **function code** — the same code
the school budget uses for its categories (2710 Guidance, 2325 SpEd Substitutes). *This
reading is inference from a single example and should be confirmed with the Town.* If it
holds, it matters enormously:

> **The function code is the join between the ledger and the school budget, and the printed
> report does not contain it.** `extract_munis_report.py` records the same thing at line
> 147: *"The PRINTED report shows ORG and OBJ and not the account string."*

That is why the `crosswalk` table in the database is **empty on purpose**. It is not an
oversight and not a modelling gap — the key that would populate it is suppressed by the
format we have been receiving. Getting spreadsheet exports is not a convenience; it is the
difference between budget-to-actual being answerable and not.

**Always ask for the spreadsheet export.** For any report, in every request.

### Account names are truncated to ten characters

Verified in the database: `MS TEACHER`, `ES TEACHER`, `KIND TEACH`, `SPED PRIVA`,
`MS GUIDANC`, `HS GUIDANC`.

So an account name cannot be matched to a budget row by name — the name is cut off before
it is distinctive. Mapping `MS GUIDANC` to a specific school's guidance line is **inference,
not tracking**, and must be labelled that way wherever it is used. School accounts carry an
`S` prefix on the org segment (`S2055101`); fund `0100` is the general fund and departments
`300`/`301` are the school departments.

---

## 2. The tiers, and which report serves each

| tier | what it is | the report | what it answers | what we hold |
|---|---|---|---|---|
| **1** | Totals | School budget workbook; YTD report with **Print Totals Only `TRUE`** | How much was planned; how much is left | Published; several years |
| **2** | Categories, by function code | YTD report, **Print Totals Only `FALSE`** | Whether a category is over or under | FY26 |
| **3** | Individual accounts, and revenue by fund | **Account Detail**; Revenue report | Where money came from and went | Athletics revolving fund only |

The tiers are already in the data. `/api/coverage` carries a `level` field of `account` or
`department`, and says a department rollup *"cannot be traced to a budget line"* — Tier 3
against Tier 1, in the schema. Currently:

    fy2026 p12  expense  account     635 rows
    fy2026 p9   revenue  account     220 rows
    fy2026 p9   expense  account      57 rows
    fy2026 p9   expense  department   67 rows
    fy2026 p9   revenue  department    4 rows

---

## 3. The reports

### YEAR-TO-DATE BUDGET REPORT — `glytdbud`

The workhorse. 93 of these are catalogued. `scripts/extract_munis_report.py` parses any of
them and **refuses to write unless the extract ties to the report's own printed GRAND
TOTAL**.

*Parameters to name in a request:*

| | |
|---|---|
| Account type | `EXPENSE` or `REVENUE` — one report each, they do not come together |
| Print totals only | `FALSE` for Tier 2 (by category), `TRUE` for Tier 1 (totals) |
| Fund | `0100` general; school departments are `300` and `301`. **Grant, revolving and school choice funds are separate funds and must be asked for by name** |
| Period | 1–13. Period 12 is June; 13 is the closing period |
| Format | **spreadsheet, not PDF** — see §1 |

*Six money columns, in this order:* `original`, `transfers`, `revised`, `expended`,
`encumbered`, `available`, then a percent-used.

*Three conventions that have each caused an error here:*

1. **Revenue prints as a credit — negative.** The report's own options page says `Print
   revenue as credit: Y`. Chapter 70 of −9,229,410 is $9.2M arriving, not a shortfall.
   Nothing in our pipeline flips the sign; `account_type` records which convention applies.
2. **Appropriation columns are rounded to whole dollars**; `expended` and `encumbered`
   carry cents. A reconciliation demanding an exact tie fails on arithmetic rather than on a
   missing row. Tolerance is one dollar per row on the rounded columns, exact on the rest.
3. **PDF-to-text joins rows.** In `ef-sewer-revenue-fy26-q3.txt`, sixteen accounts share
   line 35. The parser scans for the account pattern anywhere rather than trusting one line
   to be one row.

### ACCOUNT DETAIL / Journal Detail Export

Every transaction against an account, with dates. **This is Tier 3 and it is the tier we do
not have**, except for the athletics revolving fund (three files, FY24–FY26).

*25 columns, verified against `fund-1301-journal-detail-fy24.xlsx`:*

    A ORG            H JOURNAL       O PO/REF2      V VOUCHER
    B OBJECT         I EFF DATE      P REF3         W CARRY FORWARD
    C PROJECT        J POST DATE     Q REFERENCE    X VDR NAME/ITEM DESC   ← confidential
    D ACCOUNT        K SRC           R AMOUNT       Y COMMENTS             ← confidential
    E DESCRIPTION    L T             S P
    F YEAR           M REF1          T CHECK NO
    G PER            N PROJECT STRING U WARRANT

**Columns X and Y can name a person.** On a special education line the vendor is often a
parent being reimbursed, not a company. Ask for them omitted at export — see
`notes/INTAKE-FOR-THE-TOWN.md`, and `scripts/check_intake_headers.py`, which decides from
the header row alone whether an arriving file is safe to ingest.

*Note what the athletics files did **not** contain*, so the same gap is anticipated next
time: every row was one account (`CASH`), with no object code and **no vendor name on any
payment row**. The request for vendor-level detail was not filled. Ask explicitly for the
object code.

### Revenue report

Same `glytdbud` format, `Account type: REVENUE`. This is the route to state and grant money
— Chapter 70, Title grants, circuit breaker. **An earlier draft of a request asked for this
with `Account type: EXPENSE`**, copied from the line above it; run as written it returns
expenditures again and costs a round trip. Check this parameter every time.

### Special revenue, trust and agency

Held for FY26 Q3 as spreadsheets: `town-special-revenue-fy26-q3.xlsx`,
`town-trust-agency-fy26-q3.xlsx`.

---

## 4. What no report answers

Recorded here so it is asked as a question rather than assumed:

- **How revenue and special revenue funds map onto school budget categories.** The funds pay
  for real staff and programmes and appear nowhere in the budget document. Whether any
  accounting relationship exists is *a question for the Town Accountant*, not something to
  infer. Load-bearing: the in-district special education escalator rests on a
  paraprofessional line that cannot currently be distinguished from grant money unwinding.
- **An exact expenditure-to-budget-line route.** §1 — the function code gets a category;
  ten-character names cannot get a school.
- **Whether a budgeted position was filled.** A budget line is an intention.
- **Placement counts.** Dollars cannot distinguish fewer children from a more honest
  estimate.

DESE's **End of Year Financial Report** separates spending by fund and is the document most
likely to settle the first of these. Ask whether the Town's submission can be shared.

---

## 5. Asking

1. Check `DATA-REQUEST.md` first — it is generated from the coverage matrix, and asking
   twice for something already sent spends goodwill the next request needs.
2. Name the report, and every parameter from the table in §3. A request that can be run
   without a decision is easier to fill than one that needs interpretation.
3. Say **spreadsheet, not PDF**, and say why — the code, not the label.
4. If the report can carry a person's name, ask for the omission **in the same message**.
5. Ask for **one month or one period first** when the format is new. A wrong field list then
   costs one period instead of several years.
