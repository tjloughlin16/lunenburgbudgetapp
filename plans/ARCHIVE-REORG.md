# Reorganising the archive and the notes — the plan

**What this is.** A multi-step project agreed in conversation on 3–4 September 2026 and
**not yet started**. Written so it can be picked up cold. `notes/PLAN.md` is the arc of the
whole project; this is one track of it in detail, and PLAN.md does not yet mention it.

**Nothing in this file is a source.** It is a claim about the repo. Check anything
load-bearing against the repo itself before acting on it.

Status: **agreed, not started.** Blocked on a shared working tree — see *Before starting*.

---

## Why

`sources/` mixes five organising principles at one level — file format (`pdf/`, `txt/`),
publisher (`town-site/`, `dese/`), acquisition event (`records-request-2026-06/`), subject
(`minutes/`, `contracts/`) and ours (`analyses/`, `data/`). Most documents belong under
three of them, so **there is no rule that says where a new file goes.** It is ambiguous by
construction rather than untidy.

Two things brought it to a head:

- Two MUNIS reports with the same printed title, `YEAR-TO-DATE BUDGET REPORT`, sitting in
  `q3-fy26/` and `records-request-2026-09/`. They are genuinely different — FY26 period 9
  at department level, FY26 period 12 at account level — and the filenames say so. The
  folders, named for when we filed a request, do not.
- **15 documents stored twice**, once under a curated name in `pdf/` and once under the
  publisher's own name in a mirror folder.

And **23 more MUNIS runs are coming** (see `sent-to-the-town-2026-09/REQUEST-EMAIL-DRAFT.md`),
across four fiscal years and five report types. Without a rule they land wherever.

## The decision, and the reasoning behind it

**The tree carries provenance and grouping. Everything else is a view or an index.**

A directory can hold one key, and it must be *single-valued* and *immutable*. Fiscal year
is neither: **18 of 20 budget documents supply more than one year**, and `fy27-proposals.xlsx`
alone carries FY23 through FY27. Filing it under `FY27/` would hide the FY23–FY25 actuals
that only it provides.

Rejected, with reasons:

| model | why not |
|---|---|
| by fiscal year | a document carries up to six years; multi-valued keys cannot be folders |
| by subject | a town meeting warrant covers twenty subjects |
| by acquisition date | names our workflow, not the document — `records-request-2026-06` could hold anything |
| by file format | splits one document across two folders; this is the current `pdf/` + `txt/` |

## Target structure

```
sources/
├── town-budget/            ← town-site/ (74 docs, all catalogued as town budget & finance)
│                             plus department budgets and plans when requested
├── district-budget/        ← district-budget-page/  (+ the budget↔ledger crosswalk if it arrives)
├── meetings/               ← minutes/               (SEE COST WARNING BELOW)
├── dese/                   ← dese/                  (+ End of Year Financial Reports)
├── dls/                    ← dls-free-cash/
├── munis-ledgers/
│   ├── expenses/           glytdbud EXPENSE       ← q3-fy26/ + records-request-2026-09/
│   ├── revenue/            glytdbud REVENUE       ← the q3 revenue report
│   ├── account-details/    transaction detail     ← records-request-2026-06/ (fund 1301)
│   ├── transfers/          line-item transfers    ← empty; request item 3
│   └── purchase-orders/    POs closed after close ← empty; request item 5
├── budget-workbooks/       ← xlsx/
├── contracts/              unchanged
├── peers/                  unchanged
├── correspondence/         ← email/, plus request threads and replies
├── analyses/               unchanged
└── data/                   ← data/ + business/
```

**Gone:** `pdf/` and `txt/` (format folders), and every acquisition-dated folder name.

## Filename standard

The folders stop being ambiguous; the filenames have to as well, because 23 near-identical
reports are arriving.

    <report>-fy<YYYY>-p<PP>-<scope>.<ext>

    munis-ledgers/expenses/glytdbud-expense-fy2023-p13-gf-school.xlsx
    munis-ledgers/expenses/glytdbud-expense-fy2023-p13-school-funds.xlsx
    munis-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx     ← held
    munis-ledgers/expenses/glytdbud-expense-fy2026-p09-gf-all.pdf      ← held
    munis-ledgers/account-details/account-details-fy2024-fund1301.xlsx ← held

Sorts chronologically, greps by year, and the period is visible without opening anything.
`p13` is the year-end close, `p12` June, `p09` Q3 — the distinction that started all this.

**Mirrors keep the publisher's own filename.** Rule 12: when a link dies the only way a
resident gets the document is to ask the town for it by name, so `4082-fy-2027-detailed-budget.pdf`
survives as-is. The standard above applies to what we are *given*, not to what we mirror.

## Where the incoming 23 runs land

| request item | runs | folder |
|---|---:|---|
| 1a, 1b — glytdbud expenditures, period 13 | 8 | `munis-ledgers/expenses/` |
| 2 — Account Details | 4 | `munis-ledgers/account-details/` |
| 3 — line-item transfers | 4 | `munis-ledgers/transfers/` |
| 4 — glytdbud revenue | 3 | `munis-ledgers/revenue/` |
| 5 — POs closed after close | 4 | `munis-ledgers/purchase-orders/` |

From the Superintendent: End of Year Financial Reports → `dese/`; the budget↔ledger
crosswalk → `district-budget/`; answers to the three questions → `correspondence/`.

---

## Step 1 — `views/` — **DONE**, committed `e4a3a66`, on `main`

Browsable symlink views over the canonical store, so a document can be found by year or
subject without the tree having to carry those keys.

- `views/by-fiscal-year/` · `by-group/` · `by-importance/`
- 1,232 links over 302 documents; 186 placed by year, 116 unplaced
- **69 documents reach years their own filename never mentions** — years come from what
  the extracts record a document as *supplying* (`line-history.csv`, `munis-ledger.csv`,
  and the column headings in `document-basis.csv`), not from its name
- Relative symlinks, committed, 78 KB total. `--check` fails on a dangling link
- Rebuild: `python3 scripts/build_views.py`

Nothing moved, so no URL changed.

## Step 2 — move `sources/` — **NOT STARTED**

### Two blockers, both real

**1. `_redirects` does not work.** It contains **zero active rules**; its own header records
that Cloudflare Pages ignored every rule it ever held — invalid status codes and an infinite
loop. `llms.txt` publishes **302 documents at `/docs/<path>`**, so a move breaks URLs an
agent may have cited. The alias layer has to be built in `fy28/functions/docs/[[path]].js`,
which is what the repo already prefers ("*why this is a Function and not a `_redirects`
rule*"). **This is work inside step 2, not a config line.**

**2. `meetings/` is the expensive one.** Renaming `minutes/` → `meetings/` is cosmetic and
costs the most of anything here:

- 2,846 files
- **1,422 paths hard-coded in `/minutes/find/documents.json`**
- 3 documented path patterns in `llms.txt`
- every citation `search_minutes.py` has ever emitted

**Recommendation: decide `meetings/` separately, and probably leave `minutes/` alone.**
Everything else is ~500 files and no hard-coded paths.

### Order

1. Delete the 15 exact duplicates in `pdf/` (each is byte-identical to a mirror copy;
   `scripts/build_views.py` style sha256 comparison identifies them)
2. Move the 5 unique `pdf/` files to `town-budget/`, and the 20 `txt/` beside their originals
3. Create `munis-ledgers/` with its five subfolders; move `q3-fy26/`,
   `records-request-2026-09/`, `records-request-2026-06/` in, renaming to the standard
4. Rename `xlsx/` → `budget-workbooks/`, `email/` → `correspondence/`,
   `town-site/` → `town-budget/`, `district-budget-page/` → `district-budget/`,
   `dls-free-cash/` → `dls/`; move `business/` → `data/`
5. Regenerate `sources.json` (`build_source_index.py`) and rebuild `views/`
6. Build the alias Function so every old `/docs/<path>` still resolves
7. Verify, commit, deploy

### Verification — the change is only safe if these hold

Capture before and diff after. All eight passed byte-identical when `views/` landed:

    python3 scripts/audit_provenance.py
    python3 scripts/build_db.py --check
    python3 scripts/build_source_index.py
    python3 scripts/extract_munis_report.py --check
    python3 scripts/build_show_your_work.py --check
    python3 scripts/check_function_crosswalk.py
    python3 scripts/minutes_decisions.py
    python3 scripts/check_sent_documents.py
    python3 scripts/build_views.py --check
    cd fy28 && npm run build:site && npm run check:agents

Plus, specific to this step: **every old `/docs/<path>` URL must still resolve** — test a
sample against the deployed site, not just the build.

## Step 3 — reorganise `notes/` — **NOT STARTED**

`notes/` holds five kinds of file flat with nothing marking which is which, and the
hazards are concrete.

**The one that matters: three files are generated and look hand-written.** Editing one by
hand loses the edit on the next run.

| generated file | by |
|---|---|
| `DATA-REQUEST.md` | `build_request_doc.py` |
| `REQUEST-CODING.md` | `build_coding_questions.py` |
| `REVIEW-DISCREPANCIES.md` | `build_discrepancy_review.py` |
| `data-model/lineage.json`, `data-model/schema.mmd` | `build_lineage_graph.py`, `build_schema_uml.py` |

**And a folder that makes a false claim.** `sent-to-the-town-2026-09/` says in its README
"the copies that were sent". It contains: one manifest entry with `sent: null`, three files
titled "draft, not sent", and two files the manifest does not know about
(`CONNECTING-THE-BUDGET.pdf`, `REQUEST-CHECKLIST.csv`). **Nothing in it is confirmed sent.**

```
notes/
├── PLAN.md · HANDOFF.md · ARCHIVE-REORG.md      state and plans, at the top
├── process/     how to do a thing
│     WRITING-AN-ANALYSIS.md · PERSONAS.md · INTAKE.md
│     INTAKE-FOR-THE-TOWN.md · SANITISER-DESIGN.md
├── reference/   what a thing is
│     SCHEMA.md · DATA-ARCHITECTURE.md · MUNIS-REPORTS.md · data-model/
├── findings/    working analysis, superseded by published analyses
│     BUDGET-VS-ACTUAL.md · PASSES.md · DATA-WANTED.md
├── generated/   NEVER hand-edit; a header in each says which script owns it
│     DATA-REQUEST.md · REQUEST-CODING.md · REVIEW-DISCREPANCIES.md
├── outbound/
│   ├── drafts/            written, not sent
│   └── sent-2026-09/      actually sent — MANIFEST.json, sha256, and a real date
└── history/     HANDOFF-2026-09-03.md and successors
```

Ranked by value: **`generated/` first** (silent data loss), **splitting `outbound/drafts`
from `outbound/sent`** second (the folder currently lies), the rest is tidying.

Also: `REQUEST-CODING.pdf` sits loose in `notes/` — a build artifact, belongs with its
document. `REQUEST-3c.md` (30 August) may be superseded by `REQUEST-EMAIL-DRAFT.md`; check
before moving it to `history/`.

---

## Before starting

**The working tree is shared with another agent.** On 4 September it was on branch
`read-the-archive` writing `sources.json`, `DataRoom.tsx`, `export_ledger.py` and
`notes/DATA-ARCHITECTURE.md`. `sources.json` is the file step 2 must rewrite.

Check before touching anything:

    git status -sb
    find sources scripts fy28/src notes -newermt '-5 minutes' -type f ! -path '*__pycache__*'

If that returns anything, stop and ask. Do the reorg on its own branch off `main`.

## Decisions already made — do not relitigate

- Tree by provenance and grouping; year and subject are views, not folders
- No acquisition-dated folder names
- No format folders; 15 true duplicates get deleted
- `contracts/` and `peers/` stay as they are
- `business/` moves to `data/` — `sources/MANIFEST.md` already records it as misfiled
- `views/` is committed, not gitignored: a view that must be generated before it exists
  does not help somebody opening Finder on a fresh clone

## Open questions

1. **`minutes/` → `meetings/`?** Cosmetic, and the most expensive item here. Recommend no.
2. Does `notes/PLAN.md` absorb this file as a track, or link to it? It has no reorg track
   today.
3. `REQUEST-3c.md` — superseded, or still live?
