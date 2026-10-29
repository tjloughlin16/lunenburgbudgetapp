# The per-report worker brief (calendar editions 1959-2010)

The exact prompt each of the nine parallel workers ran on 28 October 2026, for 2001-2009. All
nine finished, none errored, ~234k tokens each, ~13 minutes wall time in parallel. Reuse it
verbatim for the remaining reports, substituting `<ED>` (the year) and `<STEM>` (the file stem,
e.g. `4512-1969-annual-town-report`; list them with
`python3 scripts/read_annual_reports.py --status`).

Run them as a Workflow (one `agent()` per report, `parallel()`), and ONLY after:
1. the report has its Tables read (`read_annual_reports.py --feature tables`, see the handoff);
2. the previous integration pass has finished (workers read the shared scripts it edits).

What a worker may NOT do is the point of the brief: it writes only inside its own edition
folder, and lists every shared-script change it needs in `NEEDS.md` for ONE integration agent
to apply afterwards. Nine agents editing shared scripts at once is how this repo has lost work
before (CLAUDE.md, "Several agents in one working tree").

**Known defect of this brief, fixed in the integration pass of 28 October:** workers named the
same new dataset differently (`report-special-services` / `report-special-education`; three
names for the Treasurer's reconciliation). Before a new batch, give the workers the list of
new-dataset names already settled in `sources/data/report-tables/README.md`, and tell them to
reuse one of those names when it is the same quantity.

---

```
You are ONE of N parallel workers. Your report: the Lunenburg MA annual town report, calendar
edition <ED>. Repo /Users/tj/lunenburgbudgets.

READ FIRST: CLAUDE.md (rules 1, 2, 7, 7c, 11, 13, 13c bind you; and "Several agents in one
working tree"), notes/PLAN-ANNUAL-REPORT-PIPELINE.md section 4a, and
sources/data/report-tables/README.md (INCLUDING the settled new-dataset names: reuse one when
it is the same quantity). Then study the finished example, sources/data/report-tables/2010/
(edition.json, map.csv, gaps.csv are written by eye; the rest is generated), and
scripts/read_report_tables.py.

INPUTS (already paid for; NEVER call Textract or any AWS API): PDF
sources/town-annual-reports/docs/<STEM>.pdf; Textract tables build/textract/out/<STEM>.cells.tsv
and lines build/textract/out/<STEM>.lines.tsv; text sources/town-annual-reports/text/<STEM>.txt.

DO, in order:
1. Create sources/data/report-tables/<ED>/edition.json, starting from 2010's and editing stem,
   PDF and periods. Every financial period is QUOTED from the page with its page number (e.g.
   "FOR THE YEAR ENDED JUNE 30, <ED>") -- never inferred from the label.
2. python3 scripts/read_report_tables.py <ED> --inventory
3. By eye, write map.csv: every (page, table) -- dataset, family, layout groups:N, header_from,
   stated_total, period, financial -- following 2010's conventions. Map to an existing dataset
   ONLY when it is the same quantity, stage (budget vs actual, rule 1) and grain; voted budgets
   never go in an actuals family; calendar wages never with fiscal. A table that prints
   something no dataset holds gets a NEW dataset named for what the page prints (TJ: these
   reports may hold tables and finances that no longer exist; capture them). School rosters:
   mark NOT LANDED (queued) exactly as 2010 does -- the integration pass handles them.
4. gaps.csv: a dataset 2010 had that <ED> does not print is a gap ONLY after you search the
   whole text for it (rule 13c: grep the thing, not the heading; say which pages you looked
   at). Gap format as 2010's.
5. python3 scripts/read_report_tables.py <ED>, then --check. Read notes.csv and the row
   statuses. Fix map.csv and rerun until it reproduces and the statuses are honest.

HARD LIMITS: write ONLY inside sources/data/report-tables/<ED>/. Do not edit any shared script,
CSV, the database, or anything else -- if your layout needs a new IDENTITY, emitter, parser
mark or dataset registration, write it down in sources/data/report-tables/<ED>/NEEDS.md (exact
change, why, which pages) for the integration pass. Do not run merge_report_tables.py,
build_db.py, report_review.py (except --dry-run), check_generated.py, any site build, git
commit/checkout/stash. Do not touch other workers' folders.

RETURN (short): tables count by subject; mapped to existing datasets (name: rows,
checked/failed/no-check); NEW datasets (name: rows, what it is); gaps; financial pages and how
many have a printed identity that ties; anything in NEEDS.md; what this report prints that
2010 did not.
```

The integration agent's brief (one agent, after every worker): see
`notes/HANDOFF-ANNUAL-REPORTS-1959-2010.md`, "Step 6".
