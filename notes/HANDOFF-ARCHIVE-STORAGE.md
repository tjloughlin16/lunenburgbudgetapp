# Handoff — archive reorganisation and storage

**Scope.** One workstream: reorganising `sources/`, and moving the binaries out of git into
a public R2 bucket. Written 5 September 2026 to survive a context reset.

**Do not confuse this with the other handoffs.** `notes/HANDOFF.md` is the project's
standing state; `notes/HANDOFF-ANNUAL-REPORTS.md` and `plans/ANNUAL-REPORTS.md` belong to
another agent's crawl work; `plans/PLAN.md` is the whole arc. This file covers only the
archive layout and where the bytes live.

**Nothing in this file is a source.** It is a claim about the repo. Check anything
load-bearing against the repo before acting on it.

---

## Where it stands

| | |
|---|---|
| `sources/` reorganised by provenance | **done**, commit `faf00fe` |
| `notes/` split by kind, `plans/` created | **done**, `80e533f` |
| Town mirror split three ways | **done**, `b55a72e` + `70e9147` — but the fetcher keeps undoing it |
| Old `/docs/<path>` URLs kept working | **done**, `faf00fe` — alias Function + `check_moved_docs.py` |
| Layout guard | **done**, `9dec5de` + `09901ce` |
| Storage plan | **written**, `plans/ARCHIVE-STORAGE.md` |
| Folder renames | **decided, not done** |
| Moving bytes to R2 | **not started** |

## Read these first

1. `plans/ARCHIVE-STORAGE.md` — the storage plan, including the order of work, the safety
   properties, and the decisions already taken. **Start at "Order of work", step 0.**
2. `plans/ARCHIVE-REORG.md` — why the layout is what it is, and what the folders mean.
3. `CLAUDE.md`, section "Ingesting new documents" — the four rules a new document must
   satisfy, and the checks that enforce them.

## Decisions taken. Do not relitigate these

- **The tree is keyed on provenance** — how a document reached us. It is the only attribute
  that is single-valued and never changes. Fiscal year is not: 18 of 20 budget documents
  supply more than one year, and `fy27-proposals.xlsx` alone carries FY23–FY27.
- **Year and subject are views, not folders.** `views/` holds browsable symlink trees;
  `python3 scripts/build_views.py` rebuilds them.
- **No acquisition-dated folder names.** `records-request-2026-06/` could have held
  anything. The request date is provenance and goes in a `PROVENANCE` file.
- **No format folders.** `pdf/` and `txt/` are gone.
- **Everything goes in the bucket** — no size threshold. It is a public download area and a
  partial one is incoherent.
- **Public, read-only bucket.** Meeting PDFs go too: 418 MB, gitignored, existing on exactly
  one disk, and the bucket is their first real backup.
- **The published minutes URL never moved.** `sources/minutes/` → `sources/meetings/`, but
  `/docs/minutes/text/...` and `/minutes/<board>.txt` stayed. A folder name is internal; a
  URL is a contract `llms.txt` publishes and `documents.json` embeds 1,422 times.
- **Renames agreed, not yet done:** `munis-ledgers/` → `town-ledgers/`, `dls/` →
  `state-dls/`, `dese/` → `state-dese/`, and optionally `peers/` → `peer-districts/`.
  Named by publisher, never by contents — `state-free-cash/` was rejected because the name
  would become a lie the moment DLS publishes something else.
- **Not renamed, deliberately:** `data/`, `docs/`+`text/` inside mirrors,
  `town-supplementary/`, `meetings/`, `contracts/`.

## Next actions, in order

**Step 0 is a review, not a move.** `plans/ARCHIVE-STORAGE.md` lists seven things to check
and why. The short version: the crawl was extended to a second document store and produces
derived CSVs as well as files, and **the storage move takes a snapshot — anything wrong at
that moment is copied into the bucket and versioned there.**

Then: refresh the backup → do the four renames → re-apply the town split → confirm R2
versioning and retention against current Cloudflare docs → create the bucket → push one
file and verify → the rest → add the R2 branch to the `/docs/` Function → test every
`/docs/<path>` against a **preview** deploy → only then `git rm --cached`.

## Live hazards

**The tree is shared with another agent.** It has been on branch `read-the-archive`
throughout, and it runs `git add -A`, which has swept my untracked files into its commits
more than once. Check before touching anything:

    git status -sb
    find sources scripts fy28/src notes plans -newermt '-5 minutes' -type f ! -path '*__pycache__*'

**`fetch_town_docs.py` undoes the town split on every run.** It writes every town document
to `town-budget/` and rewrites that folder's `index.csv` with all rows. Files *and*
manifest. It has happened at least three times. `python3 scripts/check_archive_layout.py`
names the damage; a repair script exists but was scratch-only — rewrite it from the
classifier in commit `b55a72e` if it is gone.

**`.gitignore` rules follow folder names.** Renaming `sources/minutes/` to
`sources/meetings/` silently stopped `sources/minutes/**/*.pdf` from matching, and 1,383
meeting PDFs — about 400 MB — were committed. Caught before any push; the commits were
reset and `git gc` reclaimed it. **Check `.gitignore` after every folder rename.**

## Backups

Taken 4 September, before anything destructive, and must be refreshed before the next
destructive step:

    ~/lunenburg-archive-backup/
        sources/              3,432 files, 1.2 GB
        MANIFEST-sha256.txt   3,428 hashes, verified
        README.md             refresh, verify, restore

`sources/` has since grown to 1.5 GB, so **the backup is already stale.** Refresh it:

    rsync -a --delete-after ~/lunenburgbudgets/sources/ ~/lunenburg-archive-backup/sources/

**Re-fetching is not a recovery path.** 57 source links died in one day in August 2026.

## What has been sent to the Town

Two documents went to the **Town Manager on 4 September 2026** and are recorded with
checksums in `notes/outbound/sent-2026-09/`:
`RECORDS-REQUEST-TOWN-ACCOUNTANT.pdf` and `REVIEW-DISCREPANCIES.pdf`.

**Never edit a file in that folder.** Both are generated, so an extractor change rewrites
their sources without anybody touching a sentence — and that folder is the only record of
what the recipient holds. `python3 scripts/check_sent_documents.py` reports drift; the
answer is a correction naming the version it corrects, never a rebuild in place.

Still unsent: `RECORDS-REQUEST-SUPERINTENDENT.pdf`, send-ready in
`notes/outbound/drafts/`. `REQUEST-CODING.pdf` is marked **not to be sent** — too detailed,
and the review document covers the same ground.

## Checks this workstream added

    python3 scripts/check_archive_layout.py   # right folder, right name, has provenance
    python3 scripts/check_moved_docs.py       # every pre-reorg /docs/ address still resolves
    python3 scripts/build_views.py --check    # every browsable symlink resolves
    python3 scripts/check_sent_documents.py   # has our copy drifted from what was sent

## Known-failing, and not ours

`verify_athletics.py` fails on a source-type table absent from `athletics.md`. Confirmed
failing before any of this work. Do not "fix" it by editing figures to match.
