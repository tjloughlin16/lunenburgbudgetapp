# The archive move — what happens, in order, and where every file ends up

**Status: DONE, 5 September 2026.** All nine steps. What actually happened, and the four
things this plan got wrong, are in `notes/HANDOFF-ARCHIVE-STORAGE.md` — read that first if
you are picking this up. The short version: the lock blocks overwriting (confirmed, not
assumed), so every write is one-way; the binaries turned out to be in git *twice*; and
`git rm --cached` stops the growth without shrinking the pack, because the blobs stay in
history.

Written 5 September 2026, consolidating `plans/ARCHIVE-REORG.md`
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

### Why R2 and not S3 — decided 5 September

S3 has object versioning and Object Lock; R2 has neither versioning nor true immutability.
That looks like it should settle it for S3, and it does not, for two reasons.

**We do not want our copies versioned. We want them frozen.**

A town PDF does not change. If our copy of one ever differs from what we uploaded, that is
not a revision to roll back to — **it is a defect**, and `verify_source_copies.py` exists to
catch precisely that. Rule 12 is explicit that *a Drive file can be replaced in place
without its URL changing*, which is why every source carries a sha256. If the town publishes
a revised document, that is a **new document with a new sha256 and its own object**, not a
second version of the old one.

So for the binaries, a bucket lock — which *prevents* the change — fits better than
versioning, which *records* it. And the things we genuinely do edit (extracted text, derived
CSVs, the analyses) are the 74 MB staying in git, which versions them properly: atomic
across files, with a message, reviewable before it merges. S3 versioning would not have
given any of that.

**And egress.** Checked 5 September: R2 storage is $0.015/GB-month with a 10 GB-month free
tier — so a 1.5 GB archive is free — and *"egressing directly from R2, including via the
Workers API, S3 API, and r2.dev domains does not incur data transfer (egress) charges"*. S3
charges roughly $0.09/GB out. For a **public** archive whose entire purpose is people and
agents downloading documents, that cost is unbounded and grows with success.

The one honest cost: an R2 bucket lock rule can be removed by an administrator, so this is
protection against a mistake rather than immutability against intent. A mistake is the risk
that has actually materialised in this project.

### Configuration



Confirm against current Cloudflare docs before creating anything, because deletion safety is
the point and asserting it from memory is the wrong way to earn it:

**R2 has no object versioning.** Checked against the docs on 5 September 2026, not assumed:
the bucket features are public buckets, CORS, lifecycles, **bucket locks**, event
notifications and storage classes. There is no S3-style version history, so **an overwrite
destroys the previous bytes** and there is nothing to roll back to.

What R2 gives instead is stronger for an archive, and it is what to use:

- **Bucket locks.** They prevent *both deletion and overwriting*, per prefix or across the
  whole bucket, with an Age, a date, or **Indefinite** retention — and they apply to
  existing objects as well as new ones. Set an indefinite lock over the whole bucket before
  the first upload. Note *"a bucket cannot be emptied while any bucket lock rules are
  configured"*, which is exactly the property wanted here.
- **A lock rule can be removed**, by dashboard, Wrangler or API. This is not immutability
  against a determined administrator; it is protection against a mistake, which is the
  actual risk.
- **No lifecycle rule at all.** An expiry policy on an archive is a deletion scheduled in
  advance.
- anonymous access is **GET and HEAD only**
- one write credential, held outside the repository

**And this is why the 74 MB stays in git.** With no object versioning, R2 cannot answer
"what did this file look like before?" — bucket locks stop it changing rather than
remembering what it was. Git is the archive's version history, and the extracted text is
the part of it that changes when a re-extraction changes what a figure rests on.

## Step 5 — Where every file ends up

**Bucket keys mirror the archive path exactly**, so an object's address describes itself and
the reorg pays off twice:

    <bucket>/town-annual-reports/docs/4117-fy-2011-annual-town-report.pdf
    <bucket>/town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx
    <bucket>/meetings/school-committee/2026-06-24-minutes-7869.pdf
    <bucket>/state-dls/free-cash-proof-lunenburg.xlsx

### What goes where

**Every file in `sources/` is copied to the bucket** — binaries, text, manifests, the lot.
The bucket is the complete archive and the app points all file access at it, large file or
small. It is browsable, self-describing, and nothing in it has a gap a visitor could mistake
for a document that was never mirrored.

**What git keeps a copy of is a separate question**, and the answer is decided by weight:

| tracked under `sources/` | size | files | stays in git? |
|---|---:|---:|:--|
| **binaries** — pdf, xlsx, docx, pptx | **912 MB** | 371 | **no — untracked** |
| extracted text `.txt` | 39 MB | 1,764 | yes |
| other | 17 MB | 56 | yes |
| derived data — `sources/data/*.csv`, `.db` | 16 MB | 67 | yes |
| `data/inventory/` + `data/rosters/` | 2 MB | 216 | yes |
| manifests — `index.csv`, `PROVENANCE*` | 0.4 MB | 18 | yes |
| | **986 MB** | **2,492** | **74 MB stays** |

**The binaries are 92% of the weight and 15% of the files.** Untracking those alone takes
`sources/` in git from 986 MB to 74 MB and the pack from about 1 GB to well under 100 MB.
That is the whole problem.

Three reasons the remaining 74 MB earns its place, none of which is sentiment:

- **The manifests are the index into the bucket.** 0.4 MB. Held only in R2, learning what
  exists needs a network round-trip, and a fresh clone has a chicken-and-egg.
- **The text is what everything reads** — `build_db`, the analyses, every verifier, and
  agents through `/docs/`. Tracked, an extraction change shows up in a diff; in the bucket
  alone it changes silently.
- **`inventory/` and `rosters/` cannot be regenerated.** Hours of agent reading for 2 MB.
  Version control, not just backup.

Git's copy is for building and reviewing. It is never what gets served.

### Roughly what moves

    untracked from git     912 MB of binaries, 371 files
    uploaded to R2         ~1.5 GB — the whole of sources/, including the
                           418 MB of gitignored meeting PDFs, which have
                           never had a backup anywhere
    git pack afterwards    UNCHANGED at 291.61 MiB — this line was wrong. Untracking
                           removes a file from the index, not from the commits that
                           already hold it. The growth stops; the pack does not shrink
                           without a history rewrite. Recorded as a known, deferred
                           problem in notes/HANDOFF-ARCHIVE-STORAGE.md

### The eight files that make this urgent

Seven documents are catalogued and **served nowhere**: `build_source_index.py` refuses
anything over Cloudflare Pages' 25 MiB per-file limit, prints OVERSIZE, and skips it. Six
are annual reports; the largest is 79 MB, within sight of GitHub's 100 MB hard push limit.

    79 MB  town-annual-reports/docs/4128-fy-2021-annual-town-report.pdf   NOT SERVED
    54 MB  town-annual-reports/docs/4118-fy-2012-annual-town-report.pdf   NOT SERVED
    50 MB  town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf   NOT SERVED
    38 MB  town-supplementary/docs/3463-bridge-assessment-and-ranking…    NOT SERVED
    36 MB  town-annual-reports/docs/4119-fy-2013-annual-town-report.pdf   NOT SERVED
    35 MB  town-annual-reports/docs/4124-fy-2017-annual-town-report.pdf   NOT SERVED
    30 MB  town-annual-reports/docs/4117-fy-2011-annual-town-report.pdf   NOT SERVED
    51 MB  contracts/pdf/dese-teacher-contract.pdf                        already on R2

The last line is the point: that file proves the mechanism works. The other seven are the
argument for finishing it.

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

## Decisions — settled 5 September

1. **Commit the annual-report work first, then branch.** Its 1,115 files are finished work,
   not damage; `plans/REORG-HANDOFF.md` was written at the end of it. Committing it on
   `read-the-archive` with a message that says what it is, then branching `archive-storage`
   off that, means the reorg starts from a clean tree and the two are never tangled in one
   diff. Uncommitted files follow you across branches, so leaving them was never an option.
2. **Finish `town-annual-reports/`.** All 16 annual reports move out of `town-budget/docs/`
   with their index rows. One file in a folder is the state most likely to be mistaken for
   done, and three files already reference it.
3. **Yes to `peers/` → `peer-districts/`.** Three scripts, twelve files.
4. **Public `r2.dev` URL.** No custom domain for now — one less thing to configure, and the
   path already carries the meaning.

**The hard constraint, stated plainly:** large binaries must stop going into git. Everything
below serves that; where a step is optional it is marked, and where it is not, it is because
skipping it leaves bytes in the pack.
