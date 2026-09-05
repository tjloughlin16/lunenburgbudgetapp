# Reorganising the archive and the notes — the plan

**What this is.** A multi-step project agreed in conversation on 3–4 September 2026 and
**not yet started**. Written so it can be picked up cold.

`notes/PLAN.md` is the arc of the whole project and does not yet mention this work.
`CLAUDE.md` is the rules. This file is one track, in enough detail to execute from.

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

## Step 2 — move `sources/` — **DONE**, 4 September

Executed. `sources/` is now: `town-budget/` · `district-budget/` · `meetings/` · `dese/` ·
`dls/` · `munis-ledgers/{expenses,revenue,account-details,transfers,purchase-orders,fund-balances}` ·
`budget-workbooks/` · `contracts/` · `peers/` · `correspondence/` · `analyses/` · `data/`.
`pdf/`, `txt/` and every acquisition-dated folder are gone.

**15 duplicate PDFs deleted** after checking sha256 against the mirror copies. Their 15
`.txt` companions were checked separately and were NOT byte-identical — the assumption
that they were would have destroyed 15 unique extractions. Compared with whitespace
normalised, 13 were the same text and 2 were *worse*: our copy of the balanced-budget
slides held 472 characters where the mirror holds 7,394. Deleting them fixed a defect
rather than losing anything.

**A pre-existing publishing bug, found by this work.** `build_source_index.publish()`
decided whether to re-copy a document by comparing `getsize()` alone, so an edit that
preserved a file's length was never republished. `analyses/budget-vs-actual.md` was live on
the site at 34,380 bytes against a source of 34,380 bytes and different sha256, publishing
"24,573 readings across 31 documents" where the repository said 24,337 across 32. It now
compares size as a cheap reject and the hash as the answer. All 307 documents verified
identical afterwards.

### Two failures that are NOT this change

- `verify_athletics.py` — the source-type table it asserts is absent from `athletics.md`
  at HEAD too. Pre-existing.
- `npm run build:site` — a TypeScript error in `fy28/src/pages/DataRoom.tsx` (`view` used
  before declaration, line 302). Another agent's in-progress edit.

### The alias layer — **DONE**

`fy28/functions/docs/_moved.js` maps every old address, and `[[path]].js` answers a miss
with a **301** rather than a silent rewrite — an agent told to cite `/docs/<path>` should
learn the new URL, not keep quoting one that works only because of this file. Five prefix
rules and 131 exact entries, derived from git's own rename detection rather than typed.

**The published minutes URL never moved.** `sources/minutes/` became `sources/meetings/`,
but `/docs/minutes/text/...` and `/minutes/<board>.txt` stayed exactly where they were.
A folder name is internal; a URL is a contract that `llms.txt` publishes, 1,422 paths in
`documents.json` embed, and `functions/minutes/[[path]].js` serves. Renaming the folder
cost nobody a link, and a blanket rename had briefly changed those constants before this
was caught.

`scripts/check_moved_docs.py` asserts the only thing that matters: every alias target is a
file the site actually serves. **A 301 to a 404 is worse than a 404** — it tells a caller
the document moved, sends them somewhere, and leaves them with nothing.

### Still to do

- Deploy. The build passes and `check:agents` reports only the tag guard.

### What it looked like before — **superseded**

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

## Step 3 — reorganise `notes/` — **MOSTLY DONE**, 4 September

Done: `plans/` created and `PLAN.md` moved into it. `notes/` split into `process/`,
`reference/`, `findings/`, `generated/`, `history/`, `outbound/drafts/`. All 15 referring
files rewritten (`CLAUDE.md` and 14 scripts). The three generators now write into
`notes/generated/` and each output carries a banner:

    <!-- GENERATED by scripts/X.py — DO NOT EDIT.
         Hand edits are overwritten on the next run. Change the script instead. -->

**`check_sent_documents.py` now distinguishes a stale draft from real drift.** Nothing has
been sent to anybody, so a changed source means the PDF is out of date — not that a
recipient holds different figures. The old wording said "drifted from what was sent" about
documents nobody had received.

**Still to do, all blocked on the shared tree:**

- `sent-to-the-town-2026-09/` → `notes/outbound/drafts/`. **Nothing in it was ever sent** —
  its README and MANIFEST now say so plainly — but `scripts/export_ledger.py` references
  the path and another agent is editing that file.
- `DATA-ARCHITECTURE.md` → `reference/`, and `data-model/` → `reference/data-model/`.
  Both are referenced by files being edited right now (`export_ledger.py`,
  `DataRoom.tsx`, `build_data_model_grids.py`).
- `REQUEST-3c.md` — still at top level pending a decision on whether it is superseded.

### What it looked like before — **NOT STARTED**

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

---

**Before starting, read `plans/REORG-HANDOFF.md`** — what changed underneath this plan
during the annual-report work, and which scripts hardcode which paths.

## Open on 5 September 2026 — the 27 duplicated mirror files

`check_archive_layout.py` fails on this and it is the only layout check still failing.
**Read this before acting on what the check tells you to do, because the check and the
index disagree.**

27 documents exist in both `sources/town-budget/docs/` and
`sources/town-supplementary/docs/`. All 27 are **byte-identical** — verified by sha256 on
5 September, not assumed:

```
python3 - <<'PY'
import os, hashlib
a, b = 'sources/town-budget/docs', 'sources/town-supplementary/docs'
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()
both = sorted(set(os.listdir(a)) & set(os.listdir(b)))
print(len(both), 'in both;',
      sum(1 for n in both if sha(os.path.join(a, n)) == sha(os.path.join(b, n))), 'identical')
PY
```

**The contradiction.** `check_archive_layout.py` prints *"Check they are identical, then
delete the `town-budget/` copy."* But `sources/town-budget/index.csv` records all 27 with
`local = sources/town-budget/docs/...`. Delete the town-budget copy alone and 27 index rows
point at nothing, which `build_source_index.py` will catch as *catalogued but not on disk*.

**By subject the supplementary folder is right.** They are a W-4 form, the senior tax
work-off programme, sex offender audits, an assessors' code of conduct, a bridge assessment,
financial wellness material. A folder called budget should hold budgets — which is the same
reasoning that created the split.

**So the fix is two operations, not one**, and they must land together:

1. delete the 27 from `sources/town-budget/docs/`
2. repoint those 27 rows in `sources/town-budget/index.csv` to
   `sources/town-supplementary/docs/...`

Then `check_archive_layout.py`, `build_source_index.py` and `verify_source_copies.py` all
have to pass. The sha256 in each index row does not change — the bytes are the same file.

**Cause, so it does not recur:** `fetch_town_docs.py` asks *"have I got this?"* against one
folder only, so a re-fetch of a document already filed as supplementary lands a second copy
under town-budget. Fixing the fetcher's existence test is part of this, not a follow-up.

## State of the tree when this was written

**1,113 uncommitted files**, from the annual-report work. Nothing is committed. That work
touched `scripts/extract_tables.py`, `scripts/build_source_index.py` (a new `annual-reports`
group of 30 items), `sources/data/*.csv`, `notes/reference/ANNUAL-REPORTS.md` and
`notes/reference/BACKUP.md`. `sources/BACKUP.md` was moved to `notes/reference/BACKUP.md`
and is now generated by `scripts/build_archive_guide.py`.

The instruction at the top of this file — *run `git status -sb`, and if it returns anything,
stop and ask* — will fire. That is expected, and it is not a reason to stop; it is a reason
to branch off the current work rather than off `main`, or to commit first.

## `town-annual-reports/` — the reorg was already started and left half done

`sources/town-annual-reports/` exists. It holds **one** PDF —
`4117-fy-2011-annual-town-report.pdf` — a byte-identical copy of the one still in
`sources/town-budget/docs/`, and an `index.csv` with a header row and no rows.

So FY2011 is a 17th duplicate that `check_archive_layout.py` does not report, because that
check compares `town-budget/` against `town-supplementary/` only. `build_source_index.py`,
`check_archive_layout.py` and `plans/ARCHIVE-STORAGE.md` all already name the folder.

Either finish the move — all sixteen reports plus their index rows — or delete the folder.
Leaving one file in it is the state most likely to be mistaken for done: a later reader sees
the folder, sees a report in it, and assumes the rest are there too.

Whichever is chosen, `sources/town-budget/index.csv` is the file that has to agree, the same
as for the 27 duplicates above.

**A full backup was taken before any of this:**
`/Users/tj/lunenburgbudgets-backup-2026-09-05/lunenburgbudgets-2026-09-05.zip` — 3.1 GB,
19,765 entries, CRC-verified, with a sha256 manifest and a README beside it.
