# The analysis database

`sources/data/lunenburg.db`, built by `scripts/build_db.py`. Read this before writing a
query, because two of the tables look joinable and are not.

    python3 scripts/extract_munis_report.py --check   # MUNIS reports -> munis-ledger.csv
    python3 scripts/extract_munis_school_ytd.py --check  # school YTD + trial balance (public xlsx only) -> 3 CSVs
    python3 scripts/extract_munis_school_journal.py --check  # school journal detail FY2023-26, our redacted reading -> 2 CSVs
    python3 scripts/build_db.py --check               # CSVs -> lunenburg.db, or fail

---

## The one rule

**The CSVs in `sources/data/` are the source of truth. This database is a derived read
model.** It is dropped and rebuilt from scratch on every run. Delete it and lose nothing.

That is not tidiness, it is rules 12 and 13. A row in a database has no address, no
publisher filename and no sha256. The moment a figure is *edited* here rather than
*extracted* into here, it becomes uncheckable and there is no way to tell which figures
that happened to. So: nothing writes to this file except the loader.

Every fact row carries `doc_id`. A figure that cannot name the document it came from does
not get loaded, and `v_provenance` will show you which document any total rests on.

---

## Grain — the part that decides everything

Three facts, three different grains. Getting these confused is how a budget gets compared
to an actual that is not its own.

| table | one row per | what it answers |
|---|---|---|
| `ledger_snapshot` | account × fiscal year × **period** × document | what the books say, at a moment in the year |
| `budget_figure` | line × fiscal year × **stage** × **variant** × document | what a budget document said this line would be, or was |
| `workbook_figure` | worksheet row × fiscal year × **column** × document | the FY27 workbook, unpivoted, cell-quotable |

**A period is not a stage.** A period is a point in time inside a fiscal year — period 3
is Q1, period 13 is the year-end close after the lapse period. A stage is what a figure
*is* — proposed, settled, actual. There is no join between them and nothing should invent
one.

### `budget_figure.variant`, and the filter every query needs

**And a variant is not a stage either.** A budget document may print several columns for
the same year at the same stage, each a different proposal, each named by the document:

    FY26  FY27         FY27          FY27
          Restoration  Core Budget   Balanced
          Proposed     Proposed      Proposed

`variant` carries that name verbatim, and is `''` for the documents — most of them — that
print one column per stage. **A scenario is not a disagreement**: four FY27 columns are
four proposals, not four opinions about one figure, and folding them onto one key would
keep whichever the reader happened to read last while marking the other three as documents
contradicting each other.

So `budget_figure` is grained on it, and **every query that wants "the" budget for a year
must say `variant = ''`** or it counts a line five times. That is the same trap as
`workbook_figure.row_kind = 'line'`, one table along. `v_line_budget_vs_actual` applies the
filter; `v_budget_scenario` is the other side of it, and shows the named columns only.

Which scenario became the budget is a fact about a vote. It is not in any of these
documents, and nothing here infers it.

### `ledger_snapshot` is a periodic snapshot

The same account reappears at period 3, 6, 9 and 13, each time from a different report.
That repetition is the point: it is what makes intra-year transfer tracking and burn-rate
analysis possible at all. A table holding only the year-end figure could answer "did we
spend what we budgeted" and nothing about how the year got there.

Measures: `original` (as appropriated), `transfers` (cumulative adjustments since),
`revised` (= original + transfers), `expended`, `encumbered`, `available`.

**The surplus at period 13 is `available`.** That is the same arithmetic the district used
to state FY25's surplus as $603,885.97.

**`transfers` is cumulative, not incremental.** Movement between two periods is the
difference of the column, never the later value. `v_transfer_history` does that
subtraction; do not re-do it by hand.

### `munis_school_ytd`, `munis_trial_balance_account`, `munis_trial_balance_journal`

A SEPARATE delivery from `munis-ledger.csv` / `ledger_snapshot` above, and these three
tables do not join to it. They are the school department's MUNIS `glytdbud` YTD budget
reports at period 13 (year-end close), FY2023-FY2026, plus a fund 1300 (Lost Books / Tech
Revenue) trial balance for FY2026 -- the Town's answer to the 4 September 2026 records
request. Extracted by `scripts/extract_munis_school_ytd.py` from the 9 PUBLISHED
spreadsheets only, under `sources/town-ledgers/expenses/` and
`sources/town-ledgers/account-details/`
(`sources/town-ledgers/expenses/PROVENANCE-fy2023-fy2026-p13-school.md`). **The PDFs of
these same reports are PRIVATE** (CLAUDE.md 13e) and never reach this database; a
separate, gitignored script cross-checks the published spreadsheets against those PDFs
without writing anything here.

| table | one row per | grain |
|---|---|---|
| `munis_school_ytd` | account × report (`gf-school` / `special-school`) × fiscal year | account-level, period 13 only |
| `munis_trial_balance_account` | account (GL or budget/object) | fund 1300, FY2026, periods 1-13 |
| `munis_trial_balance_journal` | journal line | fund 1300, FY2026 |

**Trap 1: the expended column changes its printed header between reports, and both
headers land in one column.** `munis_school_ytd.ytd_expended` is printed `YTD EXPENDED`
on the general-fund (`gf-school`) reports and `  YTD ACTUAL` on the special-funds
(`special-school`) reports — the same field, because MUNIS prints `YTD ACTUAL` wherever
a report can show revenue rows (`type='R'`) and `YTD EXPENDED` where every row is
type-E. The raw header text is not carried into this table.

**Trap 2: `net_change`/`running_balance` mean two different things at two grains of the
trial balance, and treating them alike is exactly the derived-quoted-as-observed mistake
rule 13 warns about.** On `munis_trial_balance_account`, `net_change` is that account's
Debits minus Credits for the WHOLE PERIOD — a total, equal to `ending - beginning`. On
`munis_trial_balance_journal`, the sheet's equivalent column is a RUNNING BALANCE
(beginning balance plus every debit, minus every credit, posted so far for that
account), stored here as `running_balance` so nobody sums it expecting a total — it is
not that line's own debit minus credit, and summing it answers nothing the report
states.

**And one journal line per account restates the account's own opening balance.** Source
code `SOY` ("OPENING BALANCE") is a journal line whose debit minus credit equals that
account's `beginning` exactly — the account row's own `debits`/`credits` already
EXCLUDE it. `is_soy_opening_balance` flags it rather than dropping it; exclude it when
summing journal lines to an account's own Debits/Credits, the way
`extract_munis_school_ytd.py`'s own tie check does.

Every row in these three tables ties, at extraction time, to a total the source
spreadsheet prints itself (every org's accounts to its `Total` row, every fund to its
total, the file to its Grand Total; the trial balance's `beginning + debits - credits =
ending` per account, journal lines excluding SOY to each account's own Debits/Credits,
and accounts to the sheet's own totals) — `extract_munis_school_ytd.py --check` refuses
to write if any of that fails. `build_db.py`'s loader additionally asserts that every
`munis_trial_balance_journal` row's `key` resolves in `munis_trial_balance_account`
(CLAUDE.md: a join that matches nothing looks exactly like absent data).

### `munis_school_journal`, `munis_school_journal_account`

Every journal line behind every school account -- fund 0100 school orgs and every school
special fund -- from FY2023 period 0 to FY2026 period 13: the Town's 1,744-page `glytdbud`
run with journal detail, generated 7 October 2026
(`sources/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md`).
Extracted by `scripts/extract_munis_school_journal.py`. **The raw PDF is private** -- the
Town's own redaction missed a child's name -- **and these tables are OUR REDACTED
READING**, under TJ's rule (19 October 2026): *"remove ANYBODY who is directly named as a
parent or child getting services from the school. anybody contributing to those services
as vendors should be ID'd... It's associating a name to a disability that we are trying to
avoid."* So:
- **Providers and vendors are named**, including special education providers, officials,
  contractors, staff in role and scholarship recipients. `name_basis` says why each person
  is shown.
- **Recipients are masked**: children read `[redacted]`. A family paid or refunded reads
  `individual (redacted)`, with no vendor, invoice, check or receipt number.
- **A blank `vendor` means the Town printed no payee.**

Three pages the Town flattened to pictures were read by eye
(`read = 'by eye (picture page)'`). The full rule is declared in the extractor's header.

| table | one row per | grain |
|---|---|---|
| `munis_school_journal` | journal line | FY2023-FY2026, every school account |
| `munis_school_journal_account` | account | the FY2026 figures the run prints |

**Trap 1: `amount` alone is not spending.** `posts_to` says which printed column a line
lands in: `actual` (API, APM, PRJ, PRH, GEN, GRV, CRP), `encumbrance` (POE, POL, POM, SOY,
YEC, GEL), `original_budget` (BUC) or `transfer` (BUA). A purchase order is opened (POE)
and liquidated (POL) as two lines that cancel; summing across `posts_to` counts it twice
and then not at all. The assignment was not assumed: it is the only one under which every
account's printed FY2026 figures close.

**Trap 2: the per-year tie exists only where a second document prints the year.** This run
prints account figures for FY2026 alone. FY2023-FY2025 tie to `munis_school_ytd` for the
939 accounts both hold; the other 2,417 accounts here (mostly dormant grant funds) have no
printed per-year figure to tie to, and `munis_school_ytd` holds 7 revenue accounts per year
this run did not select.

**Trap 3: payroll is one line per warrant per account (`PRJ`), not per person.** An
account with one employee is still that employee's pay; read it as a line, never as a
headcount.

---

## The conformed dimension, and the join that does not exist yet

`account` is used identically by every ledger fact — general fund and enterprise, revenue
and expense. That is what makes cross-fund questions a join rather than a guess.

`account.level` says what we actually hold:

- `department` — the report was run with `Print totals only: Y`, so the whole school
  district is one row, `0100-300`.
- `account` — run with `Print totals only: N`, so `0100-01001-450600` is Chapter 70 aid.

**As of 2 September 2026 the general fund *revenue* report is at account level and the
*expenditure* report is not.** So every dollar coming in is visible per account, and the
school's spending is one row. That asymmetry is the single biggest limit on this database
and it is closed by one report option.

### `crosswalk` is empty, and that is the honest state

District budget lines are **named** — `B8 = 'Staff Orientation Expenses'`. MUNIS rows are
**coded**. The group header above a line does carry a four-digit code (`A7 = '1110 -
School Committee '`, 349 of 351 lines sit under one), but those codes appear **nowhere** in
the MUNIS general fund report, which knows the district as `300 SCHOOL DEPARTMENT`. Three
code spaces, none shared.

So `crosswalk` maps `budget_line` to `account` and **starts empty**. Every row it ever
gets must carry `method` (how it was established), `confidence`, and `evidence` quoting a
coordinate and a raw value. **Nothing goes in on the strength of a similar name.** A
crosswalk full of plausible guesses is rule 13's exact failure mode, and it would silently
poison every budget-to-actual comparison built on it.

---

## `fy` is INTEGER everywhere, and the day it was not

`WHERE fy = 2023` is the most common filter anybody writes against this database. For a
long time it answered against 18 tables and returned **zero rows, raising nothing**,
against the other 44 — because the generic CSV loaders declared every column `TEXT`, and
SQLite does not compare TEXT `'2023'` equal to INTEGER `2023`.

That is the worst failure this database can have, and CLAUDE.md already names it: *a result
that matches nothing looks exactly like data that is absent.* There was no error to read
and no way to tell a real empty year from a type mismatch.

`fy` is now INTEGER in every table where every value is a bare four-digit year, which
changes no fact — `'2014'` and `2014` are the same year. Three tables keep `TEXT`, and
each has a reason that is not a year:

| table | value | why |
|---|---|---|
| `grant_award`, `grants_history` | `FY21-24` | one ESSER award genuinely spans four years |
| `rate_register` | `''` | one rate carries no fiscal year at all |

`check_fy_types()` in `build_db.py` **refuses to write the database** if a new table
arrives with a TEXT `fy` holding only years and no recorded reason. The next one fails the
build instead of the query.

> The general form, and it is the reason this section exists rather than a comment in the
> loader: **a type mismatch on a filter column is silent, and silence is indistinguishable
> from an honest empty answer.** It is the same shape as the four silent zeros of
> 5 September — a join that matched nothing, reported as data that was not there.

---

## Sign conventions and rounding, both of which have already bitten

**Revenue is stored negative, exactly as MUNIS prints it** (`Print revenue as credit: Y`).
Chapter 70 aid of $9,229,410 is stored as `-9229410`. `account.account_type` says which
convention a row follows. The `v_revenue` view negates, in one visible place, once —
flipping the sign on the way in would have hidden that the convention exists at all.

**`original`, `transfers` and `revised` are printed rounded to whole dollars** while
`expended`, `encumbered` and `available` carry cents. `ledger_snapshot.rounded_columns`
records which. Consequences:

- A department row does not reconcile to itself: `26,323,868 − 15,736,640.86 −
  1,668,043.22 = 8,919,183.92` against a printed `8,919,184.21`. The un-rounded revised
  budget is `26,323,868.29`.
- A sum of N rows cannot equal the report's own GRAND TOTAL to the cent. The tolerance is
  **one dollar per row** for the rounded columns and **exact** for the rest.

---

## Funds

`fund` carries `kind` (general / enterprise / revolving / grant / gift) and `restriction`
where a document states one. Rule 11 is entirely about the non-general funds: **a general
fund line is NET of whatever a grant, fee or revolving fund already paid for the thing.**

`fund_activity` is a different shape from `ledger_snapshot` and must not be unioned with
it. **A fund balance rolls forward; a department appropriation lapses.** Opening balance,
revenue, expenditure, closing balance is a fund's shape. Appropriation, expended,
encumbered, available is a department's.

`grant_award` is what a budget document says was awarded. It is **not** a mapping onto the
operating lines a grant paid for. That mapping is what nobody publishes, and the Town's
statement of 1 September 2026 — that about $287,000 of out-of-district tuition was charged
to the FY26 IDEA grant rather than the operating budget — is the first instance of it
being named at all.

---

## Views

| view | question |
|---|---|
| `v_appropriation_vs_spend` | did we spend what we appropriated? period 13 only |
| `v_transfer_history` | how did a line move during the year? |
| `v_burn` | committed share against elapsed year — **a screen, not a prediction** |
| `v_revenue` | where the money comes from, sign-corrected |
| `v_interfund` | free cash and inter-fund transfers reaching the operating budget |
| `v_state_aid` | Chapter 70 and the rest of the cherry sheet |
| `v_fund_year` | what each fund took in, spent and carried |
| `v_line_budget_vs_actual` | one line, both halves, from the same document |
| `v_workbook_budget_vs_actual` | the same off the FY27 workbook, which is a restatement |
| `v_provenance` | every fact table, by document, with row counts |

**`v_burn` is a screen and not a prediction, and the difference matters.** At period 9 —
75% of the year gone — the school department was 8.9 points behind a straight-line pace.
The town later reported $470,000–600,000 unexpended for FY26. But 8.9% of $26.3M is $2.3M,
four times what actually came back. School spending is back-loaded, so "behind pace" and
"normal for March" are indistinguishable **without that account's own history at the same
period in prior years.** Building that baseline is why FY24 and FY25 at multiple periods
were requested from the Town Manager.

---

## `teacher_salary_schedules` is a scale, not a payroll

One row per printed cell of every teacher salary schedule in Lunenburg's contract and those
of the neighbouring districts (`scripts/extract_teacher_salary_schedules.py`, which `--check`
rebuilds byte for byte). `teacher_salary_schedule_docs` says which contract each came from,
its period, and what could not be read.

- **Grain is (document, schedule, step, lane).** `fy` alone is not a key: Harvard prints two
  FY2020 schedules (first half, mid-year) and Leominster an extra `6/30/2018` one. Split on
  `schedule`.
- **Lanes and steps are as printed**, so `BA`, `Bach`, `B` and `I: BS / Licensure` are the
  same idea under four names, and the number of steps differs by district. Compare by name, never by
  position.
- **`read`** is how a cell was read: the PDF's text layer; Vision OCR confirmed by a second,
  independent OCR pass; or by eye off the rendered page, with what OCR returned. **`flag`**
  is any check that failed -- salary must rise along steps and across lanes, and equal the
  prior year times the increase the contract states -- and a flagged cell is printed so,
  not corrected.
- **Base schedule only.** Longevity, stipends and degree add-ons paid outside the grid are
  not here, and they differ by district (Lunenburg adds longevity to step 13).
- **Several DESE filings are expired contracts.** DESE publishes the latest one a district
  submitted. `contract_period` is the test of whether a figure is current.

## `comparison_sets` says who chose the comparison; `dese_teacher_salaries` is every district

`comparison_sets` (sources/data/comparison-sets.csv, written by hand from the documents;
`scripts/check_comparison_sets.py --check`) names which districts are compared with
Lunenburg and who chose them. `official` is every district the DISTRICT named, in three
documents -- the Budget Task Force's nine (FY2026 proposed budget, p57), the three it entered
in RADAR and the three DART columns (both FY2020 budget). `project-six` is ours, with no
recorded criterion.

- **Grain is (set, district, document).** Uxbridge and Ayer Shirley are named by all three
  documents and have three `official` rows each. Count districts with
  `COUNT(DISTINCT dese_org_code)`, never `COUNT(*)`.
- **`dese_org_code` joins** to `dese_teacher_salaries.org_code`, `teacher_salary_schedules.org_code`
  and `dese_measure.lea`. The checker refuses a printed name that resolves to anything but
  exactly one DESE district.

`dese_teacher_salaries` (`scripts/extract_dese_teacher_salaries.py --check`) is DESE's
average teacher salary, teacher FTE and teachers per 100 students for every district,
SY2009-SY2025, from the statewide spending table already held
(`state-dese/district-expenditures-by-spending-category.xlsx`). The average exists from
SY2018 only. Every figure `dese_measure` also holds ties to it, or nothing is written.
An AVERAGE is the scale times the seniority and credentials of whoever is employed; set it
beside `teacher_salary_schedules`, never in place of it.

## Adding a source

1. Extract it to a CSV in `sources/data/` with a named `extract_*.py` that **reconciles to
   the source's own printed total before it will write**.
2. Give every row a `doc_id` that resolves in `document`.
3. Add a loader to `build_db.py` and a reconciliation to `reconcile()` that asserts against
   a figure established **outside** the script — a printed total, a published figure — never
   against the loader's own output.
4. Run `python3 scripts/build_db.py --check`.

MUNIS `glytdbud` reports need no new code: drop the file in `sources/munis-ledgers/` (or wherever
it belongs) and re-run `extract_munis_report.py`. It reads the report's own options page
for the period, the account type and the grain, so the FY24, FY25 and FY26 reports
requested from the Town Manager will load as they arrive.
