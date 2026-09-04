# The analysis database

`sources/data/lunenburg.db`, built by `scripts/build_db.py`. Read this before writing a
query, because two of the tables look joinable and are not.

    python3 scripts/extract_munis_report.py --check   # MUNIS reports -> munis-ledger.csv
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

## Adding a source

1. Extract it to a CSV in `sources/data/` with a named `extract_*.py` that **reconciles to
   the source's own printed total before it will write**.
2. Give every row a `doc_id` that resolves in `document`.
3. Add a loader to `build_db.py` and a reconciliation to `reconcile()` that asserts against
   a figure established **outside** the script — a printed total, a published figure — never
   against the loader's own output.
4. Run `python3 scripts/build_db.py --check`.

MUNIS `glytdbud` reports need no new code: drop the file in `sources/q3-fy26/` (or wherever
it belongs) and re-run `extract_munis_report.py`. It reads the report's own options page
for the period, the account type and the grain, so the FY24, FY25 and FY26 reports
requested from the Town Manager will load as they arrive.
