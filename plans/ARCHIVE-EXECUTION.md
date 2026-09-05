# The archive move — what happens, in order, and where every file ends up

**Status: not started.** Written 5 September 2026, consolidating `plans/ARCHIVE-REORG.md`
(why the layout is what it is), `plans/ARCHIVE-STORAGE.md` (why the bytes leave git) and
`plans/REORG-HANDOFF.md` (what the annual-report crawl changed underneath both).

Read `plans/REORG-HANDOFF.md` first. It carries the dependency map, and that decides what
can move at all.

---

## Where things are now

    sources/                            1.5 GB on disk, 448 MB tracked in git, 2,012 files

    town-budget/          771 MB   ← 194 docs incl. 16 annual reports, + ocr/ pages/ text/
    meetings/             418 MB   ← PDFs gitignored; text and index tracked
    contracts/             91 MB
    district-budget/       79 MB
    town-supplementary/    73 MB
    data/                  37 MB   ← includes inventory/ and rosters/, NOT regenerable
    town-annual-reports/   30 MB   ← one PDF, empty index. Half-populated
    peers/                  9 MB
    munis-ledgers/          8 MB
    dese/                 3.4 MB
    analyses/             1.4 MB
    budget-workbooks/     444 KB
    dls/                   80 KB
    correspondence/         8 KB

**Tree state: 1,115 uncommitted files on branch `read-the-archive`.** That is the
annual-report work, not damage. **Ask whether to branch off it or get it committed first —
do not assume.**

---

## Step 1 — Finish the town split. Two operations that must land together

`check_archive_layout.py` currently fails on exactly this and nothing else.

**27 files exist in both `town-budget/docs/` and `town-supplementary/docs/`**, byte-identical
(sha256-verified, not assumed). **And all 27 rows in `sources/town-budget/index.csv` point at
the `town-budget/` copy.**

So deleting alone leaves 27 index rows aimed at nothing. In one commit:

| | |
|---|---|
| delete | `sources/town-budget/docs/<27 files>` and their `text/` companions |
| repoint | those 27 rows' `local` and `text` columns to `town-supplementary/…` |
| keep | the `sha256` column unchanged — same bytes, different path |
| then | `build_dataset_provenance.py`, which joins dataset rows to source documents through this index |

**Also: `sources/town-annual-reports/` is half-populated.** One PDF (FY2011), byte-identical
to the copy still in `town-budget/docs/`, and an `index.csv` with a header and no rows — so
it is a 17th duplicate that the guard does not report, because the guard compares
`town-budget/` against `town-supplementary/` only.

**Decision needed:** finish the move (all 16 annual reports out of `town-budget/docs/` into
`town-annual-reports/docs/`, index rows with them) or delete the folder. One file in it is
the state most likely to be mistaken for done. **Recommend finishing it** — the folder was
created deliberately and three files already reference it.

## Step 2 — Fix the cause, or step 1 undoes itself

`fetch_town_docs.py` tests *"have I got this already?"* against `town-budget/docs/` only. A
document that has moved to `town-supplementary/` or `town-annual-reports/` looks missing, is
re-downloaded, and lands back in `town-budget/`. It has happened at least four times, and it
rewrites `town-budget/index.csv` with every row as well.

Three changes:

1. the have-check looks in **all three** docs folders
2. a new document is routed by a classifier — annual report → `town-annual-reports/`,
   budget/plan/warrant/financial-statement → `town-budget/`, else `town-supplementary/`
3. each folder's `index.csv` is written with **only its own rows**

The classifier lives in **one** place, imported by the fetcher and by any repair, so the two
cannot disagree. The rule is in commit `b55a72e`.

## Step 3 — The four renames

Decided in `plans/ARCHIVE-STORAGE.md`. Cheap now, a redirect-per-object after the first
upload.

| from | to | scripts referencing it |
|---|---|---:|
| `sources/munis-ledgers/` | `sources/town-ledgers/` | 12 |
| `sources/dese/` | `sources/state-dese/` | 7 |
| `sources/dls/` | `sources/state-dls/` | 4 |
| `sources/peers/` | `sources/peer-districts/` | 3 |

**None of these appears in the annual-report pipeline's hardcoded paths.** Those are
`town-budget/{docs,ocr,pages,text}` and `sources/data/{inventory,rosters}` — and none of
them is being renamed. That is why these four are safe and those are not.

Each rename also touches: `sources.json`, `fy28/functions/docs/_moved.js` (one new prefix
rule each, so every old `/docs/<path>` keeps working), `views/`,
`check_archive_layout.py`'s folder table, and `.gitignore` **if any rule names the folder** —
the trap that committed 1,383 meeting PDFs last time.

## Step 4 — The bucket

Confirm against current Cloudflare docs before creating anything, because deletion safety is
the point and asserting it from memory is the wrong way to earn it:

- object **versioning** — enabled **before the first object**; a later enable does not
  protect what is already there
- **no lifecycle rule at all** — an expiry policy on an archive is a deletion scheduled in
  advance
- anonymous access is **GET and HEAD only**
- one write credential, held outside the repository

## Step 5 — Where every file ends up

**Bucket keys mirror the archive path exactly**, so an object's address describes itself and
the reorg pays off twice:

    <bucket>/town-annual-reports/docs/4117-fy-2011-annual-town-report.pdf
    <bucket>/town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx
    <bucket>/meetings/school-committee/2026-06-24-minutes-7869.pdf
    <bucket>/state-dls/free-cash-proof-lunenburg.xlsx

### What goes where

| | stays in git | goes to the bucket | stays on local disk |
|---|:--:|:--:|:--:|
| PDFs, xlsx, pptx, docx | **no** — untracked | **yes** | yes |
| extracted text (`text/`, `pages/`) | yes | yes | yes |
| `ocr/` TSVs (14 MB, ~2h to rebuild) | yes | yes | yes |
| `data/inventory/`, `data/rosters/` — **not regenerable** | yes | yes | yes |
| every `index.csv`, every `PROVENANCE*.md` | yes | yes | yes |
| derived CSVs in `sources/data/` | yes | yes | yes |
| scripts, model, analyses, notes, plans | yes | no | yes |
| `sources/data/verify/` — scratch | no | no | delete |
| `meetings/**/*.pdf` — already gitignored | already no | **yes** | yes |

**Nothing leaves the local disk.** "Goes to the bucket" is a copy. "Untracked from git" is
`git rm --cached`, which removes it from tracking and leaves the file where it is.

The whole archive goes to the bucket, not just the large half — it is a public download
area, and a partial one has gaps a visitor cannot distinguish from documents that were never
mirrored.

### Roughly what moves

    binaries untracked from git      ~440 MB of the 448 MB currently tracked
    uploaded to the bucket          ~1.5 GB (everything, including the 418 MB of
                                     gitignored meeting PDFs — their first real backup)
    git pack afterwards             ~290 MB → well under 100 MB

## Step 6 — Copy, verify, then untrack. In that order, per file

1. upload
2. **read back and compare sha256** against the `index.csv` row
3. only on a match, `git rm --cached`
4. leave the local file alone

A failure at any step leaves the file tracked in git — the state we started in. At the moment
of untracking the bytes exist in three places: bucket, local disk, and the 3.1 GB backup.

## Step 7 — The site must not notice

`llms.txt` publishes 302 documents at `/docs/<path>` and tells agents to cite those URLs.
`fy28/functions/docs/[[path]].js` already intercepts every request — it is how the reorg's
301 aliases work — and gains one branch:

1. asset in the build → serve it *(unchanged)*
2. path moved → 301 *(unchanged)*
3. **in the bucket → stream it under the same URL**
4. otherwise → the 404 that explains itself

**The gate, before any `git rm --cached`:** deploy to a **preview** URL, fetch every
`/docs/<path>` in `sources.json`, assert 200 and matching sha256. It does not ship until
that passes.

## Step 8 — Make a clone work again

- `sync_archive.py --pull` fetches missing binaries and verifies each sha256
- documented in `CLAUDE.md` and `fy28/README.md` as a step before `npm run build:site`
- `check_archive_storage.py` reconciles **both ways** — every manifest row has an object with
  a matching hash, every object appears in a manifest — and joins the standing checks

## Step 9 — The bucket has to explain itself

A folder of PDFs with no explanation is a pile, not an archive:

- `README.txt` at the root — what this is, that it mirrors public records and is not an
  official source, one line per folder
- `MANIFEST.csv` — path, size, sha256, and the publisher's original URL for every object
- a short README per folder
- a link back to lunenburgbudgetproject.org

---

## What could go wrong, and what catches it

| | |
|---|---|
| index rows point at deleted files | `build_source_index.py` — *catalogued but not on disk* |
| a rename breaks a `.gitignore` rule and commits 400 MB | check `.gitignore` after every rename; `git ls-files \| grep '\.pdf$'` |
| a moved folder leaves a script reading a stale cache | **the quiet one.** `extract_tables.py` reads the page cache, so it would keep emitting rows off stale text. `verify_report_tables.py` — 121 stated reconciliations |
| an old `/docs/` URL 404s | `check_moved_docs.py`, then the preview-deploy fetch |
| an object in the bucket differs from the manifest | `check_archive_storage.py` |
| a dataset CSV renamed and silently dropped | `build_db.py` names 25 datasets; the 19 reconciliations do not cover the annual-report data, so **the DB would build clean and be short a table** |

## Run before every commit

    python3 scripts/check_archive_layout.py
    python3 scripts/build_source_index.py
    python3 scripts/check_moved_docs.py
    python3 scripts/build_views.py --check
    python3 scripts/build_db.py --check
    python3 scripts/verify_report_tables.py
    python3 scripts/build_archive_guide.py --check
    python3 scripts/build_dataset_provenance.py     # AFTER moving anything
    python3 scripts/verify_source_copies.py         # slow; proves a moved file is still the file

## Decisions still needed

1. **Branch off `read-the-archive`, or commit its 1,115 files first?**
2. **`town-annual-reports/` — finish the move or delete the folder?** Recommend finish.
3. `peers/` → `peer-districts/` — in or out?
4. Public `r2.dev` URL, or a custom domain on the bucket?
