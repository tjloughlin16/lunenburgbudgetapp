# Handoff

Written to survive a context reset. Read `CLAUDE.md` first — fifteen rules, every one of
them written because it was broken here.

**Nothing in this file is a source.** After a reset it reads exactly like something already
verified. It is a claim about the repo, and it has been wrong before: it once said `v3` was
live when `v5` was, and it once said an athletics sentence was "fixed on this branch" when
it had never been fixed anywhere. Check anything load-bearing against the repo.

---

## 0. STATE, as of 2 September 2026

| | |
|---|---|
| **Live site** | `lunenburgbudgetproject.org` — tag **`v9.2`** |
| **`main`** | one commit ahead of `v9.2`: the stale-analysis guard and this file |
| **Branch `data-room-and-api`** | merged into `main` at `68adc15`. Do not reuse it |
| **Dev server** | `cd fy28 && npm run dev` → localhost:5173 |

**Two agents worked on this repo today.** One (this session) did the database, the ledger
ingest and the analyses; another did the agent-facing interface and shipped `v9.1` and
`v9.2`. If something in `fy28/public/minutes/find/` or `llms.txt` is unfamiliar, that is
why — see §6.

**Deploy needs Node 22 via nvm.** Build with `npm run build:site`, never `npm run build`.
Then `npm run check:agents`. Tag at deploy time, never in advance. Push before deploying.
**Nothing deploys without being asked, every single time.**

---

## 1. What this session built

### The analysis database — `sources/data/lunenburg.db`

Read `notes/SCHEMA.md` before writing a query; two tables look joinable and are not.

Built by `scripts/build_db.py` from the CSVs, which stay the source of truth. Dropped and
rebuilt every run, never hand-edited — a row in a database has no address, no publisher
filename and no sha256. **19 reconciliations, all tying**, each asserted against a figure
established outside the script.

Three facts at three grains: `ledger_snapshot` (account × year × **period**),
`budget_figure` (line × year × **stage**), `workbook_figure` (worksheet row × year ×
column). **A period is not a stage and they do not join.**

`crosswalk` is **empty and that is correct**. District lines are named, MUNIS rows are
coded, the workbook's function-group codes appear nowhere in the MUNIS report. No budget
line can be traced into an actual. Filling it with plausible name matches would be the
error this whole project is organised against.

### The FY26 ledger — the thing that made everything else possible

`sources/records-request-2026-09/`, sent by the Town Manager on 2 September, produced by
the Town Accountant the night before. **The first account-level general fund expenditure
report this project has ever held** — every previous one was a department rollup that
renders the whole school district as one row. Here it is 258 school accounts and 376 town
accounts.

Two files. The spreadsheet carries the appropriation columns un-rounded; **only the
printout states the period**, so `extract_munis_report.py` requires the twin and proves
they are one report by reconciling to its GRAND TOTAL. Expended and encumbrances agree to
the cent.

**It is period 12, not 13.** Nothing in it is a surplus.

### Two analyses, and the process for writing more

`sources/analyses/fy26-closeout.md` and `-town.md`, both verified, both with charts and
PDFs. `notes/WRITING-AN-ANALYSIS.md` is the eight-step process; `notes/PERSONAS.md` is the
six-reader review it points at.

### Published surfaces

- `/reports` — the twelve analyses, each with PDF, source text and checksum, under a
  caveat saying none of it is official
- `/data-room` — **unlisted**: no nav, no sitemap, no alias, not prerendered. Coverage
  matrix, line explorer, gross budget, funds. Anyone with the URL can read it
- `/api/index` and `/data/lunenburg.db` — the whole database, no key, no rate limit
- `sources/data/gross-school-budget-fy2026.xlsx` — the district's budget in its own shape
  with amber cells wherever the other money is not held

---

## 2. The findings, and what they rest on

**FY26 school department, period 12:** $26,247,474 appropriated, $85,090 transferred in,
$25,613,679 spent, $236,784 encumbered, **$482,101 unspent — 1.8%.**

That figure is a residue: $1,683,534 under across 160 accounts against $1,201,434 over
across 56. Grouped by what the money buys, every large category landed within 3% and the
small discretionary one missed by 15%. The median salary account spent 100% of its budget;
the median supply account spent 88%.

**Town side, same period:** $858,462 unspent across 376 accounts, 220 under and 18 over.
Snow removal cost $1,038,092 against a $355,571 appropriation — 292% — while the $185,000
Reserve Fund went untouched. $1,262,376 of school retiree health insurance sits in a town
department and appears nowhere in the school budget.

---

## 3. Do NOT restate these as established

| tempting | actually |
|---|---|
| The schools handed back half a million | They spent 97.3% of budget. The leftover is mostly large lines landing within 3% |
| The FY26 figures are final | Period 12, books open. Bounded by encumbrances: school $482,101–$718,885, town $858,462–$1,141,003 |
| Kindergarten paras were paid without authority | The line was cut and published at −100%, $99,064 was spent, no transfer covers it **at period 12**. Three readings fit. The transfer schedule would settle it |
| Support posts were cut to pay for paraprofessionals | Support is +$194,718 and paras −$210,082, $15,363 apart — but paras are **7 of 7 accounts** and support is **3 of 8**. A group-wide movement and three individual lines are not two halves of one trade |
| Out-of-district placements shifted from private to collaborative | Two lines moved in opposite directions by similar amounts. Placement counts are not published |
| A salary line spending nothing means a vacant post | Consistent with a vacancy, a post paid from another account, a grant-funded post, or a recoding |
| The town is better run than the schools | 18 of 376 accounts over against 57 of 259 is real, and four explanations fit it |
| $1,736,376 of other funds is hidden money | It is real spending nobody can attribute to a line, and it is period 9, not 12 |
| The account names mean what they say | 124 readings in `sources/data/account-names.csv` are OURS, each with its basis. `REG TRANS` is school busing in dept 300 and a regional transit assessment in dept 825 |
| The helmets could have been bought | A booster said there were more heads than helmets; equipment lines spent 56%. Adjacency, not allegation |

---

## 4. Outstanding from the Town — `notes/DATA-REQUEST.md`

Generated from the coverage matrix. **Re-run it before sending anything.** 23 of 27
report-years outstanding for FY24–FY26. In priority order:

1. **The same report for a Fund other than 0100** — the twelve school grant, revolving and
   choice funds. Turns the net budget into a gross one
2. **Period 13, the year-end close**, plus the purchase orders closed after it
3. **The year-end transfer schedule**, by account, with authority — settles the
   kindergarten question and the $85,090
4. **Account Detail export for `S2032121` and `S2032131`** — the Town has already produced
   exactly this report once, for fund 1301 in June
5. **Finance Committee minutes from 14 July 2026 onward** — four meetings have an agenda
   and no minutes, and the first took up transfers

Also, from the district rather than the Town: **the End of Year Financial Report as
submitted to DESE**, Schedule 1, which separates spending by source of funds.

---

## 5. Corrections made this session, and why they are listed

Six, and the pattern is worth knowing because it will repeat.

1. **"A quiet rename hid the kindergarten cut."** It did not. The approved budget published
   it at −100%. I characterised a document before reading it.
2. **"Nothing in the minutes mentions kindergarten paras."** Two mentions, both FY27
   requests. A shallow grep read as an absence.
3. **A psychologist section quoting one account as though it described four.** Caught by
   the verifier failing on a derived figure.
4. **"Not one of eight support accounts went over."** Three of four psychologist accounts
   are over. Read off the group net without checking rows.
5. **A variance printed without the encumbrance it was computed from**, so the arithmetic
   could not be followed. Found by TJ reading the PDF.
6. **The period-12 hedge stretched past the evidence**, implying the figures might be
   nothing. They are bounded. Found by TJ.

**Every one is still in the documents.** A correction that gets edited out teaches nobody.

---

## 6. The other agent's work — v9.1 and v9.2

Not this session's. From the commits:

- **v9.1** — every published address rendered as a link rather than described
- **v9.2** — `fy28/public/minutes/find/`, a two-character-prefix term index over the
  meeting archive, so a caller can find which documents contain a word without fetching a
  1MB bundle. `README.txt` in that directory explains the shape

Both are deployed. If you touch `llms.txt` or the minutes surface, check with them first.

---

## 7. Known gaps in our own machinery

- **The published `.md` can drift from the source `.md`.** It did: `fy26-closeout.md` was
  rewritten and shipped stale, because the PDF and the `/reports` index are regenerated
  from source while the Markdown a reader fetches is a *copy* made by
  `build_source_index.py`. `check:agents` now fails on it. Fixed, but the class of error —
  derived things fresh, the copy stale — is worth watching for elsewhere.
- **Five of twelve analyses have no verifier.** `/reports` says so on each row rather than
  letting them look the same as the checked ones.
- **`v9` numbering has not been collapsed.** v9, v9.1, v9.2 all point at real deployed
  builds. Do not retire them without recording what they pointed at — a deleted tag is a
  deleted answer to "which build is that".

---

## 8. Next, in order

1. **Nothing is deployed since `v9.2` except a guard and this file.** The persona rewrite
   of `fy26-closeout.md` IS live; it went out inside v9.2.
2. **When FY24/FY25 arrive**, they load with no new code — drop them in
   `sources/records-request-2026-09/` and re-run `extract_munis_report.py`. That is when
   §8 of both analyses stops being one observation and becomes a pattern.
3. **The town-side root-cause decomposition** has not been done the way the school side's
   §1a was. Snow will distort it, so the fixed-versus-discretionary split needs care.
4. **The gross budget workbook fills in** the moment a non-0100 fund report arrives. Every
   amber cell in the last column becomes a number.

## Running the checks

    python3 scripts/build_db.py --check           # 19 reconciliations
    python3 scripts/verify_fy26_closeout.py       # figures, codes, and the persona review
    python3 scripts/verify_fy26_closeout_town.py
    python3 scripts/build_source_index.py         # publishes sources/ — do not skip it
    python3 scripts/build_reports_index.py
    cd fy28 && npm run build:site && npm run check:agents

`CLAUDE.md` carries the full list.
