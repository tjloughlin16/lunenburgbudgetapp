# Handoff — archive reorganisation and storage

**Scope.** One workstream: reorganising `sources/`, and moving the binaries out of git into
a public R2 bucket. Written 5 September 2026 to survive a context reset.

**READ `plans/REORG-HANDOFF.md` FIRST.** It was written 5 September at the end of the
annual-report work and it supersedes several assumptions in this file and in
`plans/ARCHIVE-STORAGE.md`. In particular it carries the dependency map — which scripts
hold hardcoded paths into `sources/` — and that is the thing that decides whether a folder
can be moved at all.

**Do not confuse this with the other handoffs.** `notes/HANDOFF.md` is the project's
standing state; `notes/HANDOFF-ANNUAL-REPORTS.md` and `plans/ANNUAL-REPORTS.md` belong to
another agent's crawl work; `plans/PLAN.md` is the whole arc. This file covers only the
archive layout and where the bytes live.

**Nothing in this file is a source.** It is a claim about the repo. Check anything
load-bearing against the repo before acting on it.

---

## Where it stands — 5 September, end of session

**Steps 1–4 of `plans/ARCHIVE-EXECUTION.md` are DONE.** On branch `archive-storage`, clean
tree, all thirteen checks passing, site builds 18/18.

| | |
|---|---|
| 1. Town split finished | 27 duplicates + their index rows; 16 annual reports rehomed |
| 2. Fetcher routing fixed | `scripts/town_document_home.py` is the one classifier; a full run re-downloads nothing and files nothing wrongly |
| 3. Four folders renamed | `town-ledgers`, `state-dese`, `state-dls`, `peer-districts`; old URLs aliased |
| 4. Bucket | **already existed and is already locked** |

### The bucket — nothing to create

    name        lunenburg-budget-project        (ENAM, created 2026-08-28)
    public URL  https://pub-5baef0f2604545c398a39a176e400e34.r2.dev
    lock rule   immutable-sources · enabled · ALL prefixes · after 3650 days
    contents    1 object, 53.4 MB — contracts/pdf/dese-teacher-contract.pdf

The lock is a ten-year retention across every prefix, blocking **delete and overwrite**,
applying to existing objects as well as new. That is the deletion safety the plan asked
for, already in place. **Do not remove that rule to "fix" a bad upload** — upload a
corrected object under a new key and repoint the manifest.

### What is left: steps 5–9

5. `sync_archive.py --push` — upload, **read back, compare sha256**, one file first
6. `check_archive_storage.py` — reconcile manifest ↔ bucket, both directions
7. R2 branch in `fy28/functions/docs/[[path]].js`, deployed to a **preview** URL
8. Fetch every `/docs/<path>` against that preview, assert 200 + sha256. **This is the gate**
9. Only then `git rm --cached` the 912 MB of binaries, and document the pull step

## Original notes below

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
  **Cost re-measured 5 September against the new dependency map: 12 scripts reference
  `munis-ledgers`, 7 `dese`, 4 `dls`, 3 `peers`.** All mechanical string replacements, and
  none of these folders appears in the annual-report pipeline's hardcoded paths — the
  expensive folders there are `town-budget/{docs,ocr,pages,text}` and
  `sources/data/{inventory,rosters}`, which are **not** being renamed.
  Named by publisher, never by contents — `state-free-cash/` was rejected because the name
  would become a lie the moment DLS publishes something else.
- **Not renamed, deliberately:** `data/`, `docs/`+`text/` inside mirrors,
  `town-supplementary/`, `meetings/`, `contracts/`.

## Next actions, in order

**Step 0 is a review, not a move** — and most of it has now been done for you.
`plans/REORG-HANDOFF.md` §2 and §3 list what is new and what depends on it, and §5 records
that every check passes except `check_archive_layout.py`, which fails only on the 27
duplicated mirror files. Read it rather than rediscovering it.

What is left of step 0: confirm those checks still pass at the moment you start, because
**the storage move takes a snapshot and anything wrong then is copied into the bucket and
versioned there.**

**The silent failure to watch for**, in their words: `extract_tables.py` reads the *page
cache*, so moving `town-budget/docs/` would leave it producing the same rows off stale text
— "silently correct-looking and no longer traceable to a document". A loud break is safe; a
quiet one is not.

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

**Use the other agent's. It is better than mine and it is current:**

    /Users/tj/lunenburgbudgets-backup-2026-09-05/lunenburgbudgets-2026-09-05.zip

3.1 GB, 19,765 entries, the whole repository including `.git`. CRC-verified with
`unzip -t`, checked back against the live tree with `shasum -c`, with a sha256 manifest of
all 16,503 working-tree files beside it. **A remote copy also exists.**

My earlier `~/lunenburg-archive-backup/` (rsync of `sources/` only, 1.2 GB, taken
4 September) is **stale and narrower** — `sources/` has since grown past 1.5 GB. Keep it or
delete it, but do not rely on it.

**Two things in `sources/data/` cannot practically be regenerated** and are the reason a
backup matters more than the byte count suggests:

| | | |
|---|---|---|
| `sources/data/inventory/` | 1.1 MB | 16 per-report table catalogues, read page by page by an agent — many hours |
| `sources/data/rosters/` | 1.4 MB | 200 roster page dumps and parsed JSON — same |

`sources/town-budget/ocr/` (14 MB) is regenerable but costs **~2 hours** of OCR.

**Re-fetching is not a recovery path either.** 57 source links died in one day in August
2026.

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
