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

## Where it stands — 5 September, second session

**Steps 1–9 of `plans/ARCHIVE-EXECUTION.md` are DONE.** The archive's binaries are in R2,
served under their own `/docs/` URLs, and out of git.

| | |
|---|---|
| 1. Town split finished | 27 duplicates + their index rows; 16 annual reports rehomed |
| 2. Fetcher routing fixed | `scripts/town_document_home.py` is the one classifier |
| 3. Four folders renamed | `town-ledgers`, `state-dese`, `state-dls`, `peer-districts` |
| 4. Bucket | already existed, already locked |
| 5. `sync_archive.py` | manifest, push with read-back, pull, lock probe |
| 6. `check_archive_storage.py` | reconciles manifest ↔ bucket both ways |
| 7. R2 branch in the Function | `fy28/functions/docs/_bucket.js`, bound in `wrangler.jsonc` |
| 8. The gate | `check_archive_urls.py`, every address hashed against a preview deploy |
| 9. Untracked | the binaries left git, and left the site build with them |

### What was learned, and is not in the plans

**The lock blocks overwriting, and that was confirmed rather than assumed.** Re-uploading
a file's own bytes over itself returns `HTTP 409 — the object is locked by the bucket
policy`. `sync_archive.py --verify-lock <key>` is that probe, and it re-uploads the
object's OWN bytes so that a lock which turned out not to hold would replace an object
with an identical one rather than damage it.

**So every write is a one-way door**, and that decided the shape of everything else. A
push reads the object back and compares sha256 before recording it; a key already holding
different bytes is an error the script refuses to touch, because it cannot be corrected in
place — only superseded under a new key.

**TJ chose to push the whole archive, ours included** (asked and answered 5 September).
The consequence, stated so nobody rediscovers it as a bug: the bucket holds a **frozen
snapshot of our derived files** — extracted text, derived CSVs, the analyses — taken this
day. When an extractor changes, git has the new version and the bucket cannot take it.
Nobody reads the stale one, because the site checks build assets before the bucket.
`check_archive_storage.py` reports those separately, as *an older rendering*, never as a
failure.

**The binaries were in git TWICE.** 912 MB under `sources/` and the identical bytes again
under `fy28/public/docs/` — 415 files, 722 MB — because `build_source_index.py` copied
every document into the build. Untracking one copy and not the other would have saved
nothing. `build_source_index.py` now publishes only what is ours; `_bucket.js` serves the
rest.

**`git rm --cached` does not shrink the pack.** The blobs stay in history, so a fresh
clone still downloads them. What it does is stop the growth. See *The history problem*
below: it is recorded, not fixed, on purpose.

**The API is rate-limited to about four requests a second** (1,200 per five minutes), and a
push makes two per file. `archive_storage.RATE` throttles globally; the first attempt at
eight workers with no limiter died on 429s a third of the way in.

### The bucket

    name        lunenburg-budget-project        (ENAM, created 2026-08-28)
    public URL  https://pub-5baef0f2604545c398a39a176e400e34.r2.dev
    lock rule   immutable-sources · enabled · ALL prefixes · after 3650 days
    contents    3,877 objects, ~1.47 GB

**Do not remove that rule to "fix" a bad upload** — upload a corrected object under a new
key and repoint the manifest.

### Two things the plan asked for and did not get, deliberately

**No `MANIFEST.csv` in the bucket.** An object there cannot be updated once written, so a
manifest stored beside the objects would be permanently out of date about them — and being
wrong about what exists is worse than not saying. The manifest is in git and published at
`/data/archive-manifest.csv`, and `sources/README.txt` (bucket key `README.txt`) points
there.

**No per-folder READMEs.** A public `r2.dev` bucket does not allow LIST, so nobody browses
it: a reader arrives at one object's URL, or at the manifest. A README they cannot find is
not documentation. The root `README.txt` carries one line per folder instead, and the
browsable index is the site's `/sources` page.

### The history problem — KNOWN, DEFERRED, decided 5 September 2026

**The binaries are out of the working tree and still in the history.** Untracking a file
removes it from the index, not from the commits that already contain it. So:

    size-pack   291.61 MiB   before this work
    size-pack   291.61 MiB   after it

That number does not move until somebody rewrites history, and **the decision taken is not
to.** It is recorded here so that nobody rediscovers it as a surprise and nobody "fixes" it
casually.

**What this move did fix, which is the thing that mattered:** no new binary enters the pack
from here. The growth stops. `sources/` was heading past a gigabyte tracked, with a 79 MB
file inside GitHub's 100 MB hard limit; that trajectory is what made this urgent, and it is
gone.

**What would make it a real problem**, in the order it would show up:

- a clone that takes long enough that somebody stops doing it
- CI, or any automated checkout, paying 291 MB per run
- GitHub warning on repository size

**What to do first, and it is not a rewrite.** A caller who does not need the history's
blobs can decline to download them:

    git clone --filter=blob:none <url>     # blobless: history, no old file contents
    git clone --depth 1 <url>              # shallow: one commit, no history at all

That is a **partial clone**, and it solves the symptom — clone size — without touching a
single hash. Try it before anything destructive.

**The rewrite, if it ever comes to that.** `git filter-repo --path-glob '*.pdf' --invert-paths`
and the same for the other binary extensions, then a force-push. The cost is not the effort:

- **every commit hash changes.** Anything that cites one — a note, an analysis, a message
  to the Town — points at a commit that no longer exists
- **every existing clone must be re-cloned.** A pull cannot reconcile a rewritten history
- **the old objects survive on GitHub** until their garbage collection runs, so the saving
  is not immediate even after the force-push

Do it only when one of the three symptoms above is actually being felt, and take a fresh
backup first — `notes/reference/BACKUP.md` says where the current one is.

### OPEN: 21 pre-reorg addresses are answered from a stale edge cache

**Expected to clear itself around 9 September 2026.** Decided 5 September to wait rather
than chase it. Written down so the next person to run the gate does not treat it as new.

`check_archive_urls.py` against production reports **117 of 138** old addresses
redirecting. The other 21 answer `200` with the document itself instead of the `301`.

**The deploy is not the problem, and that was established rather than assumed:**

    lunenburg-fy28.pages.dev/docs/txt/fy27-final-budget-doc.txt        301  correct
    www.lunenburgbudgetproject.org/…                                  301  correct
    lunenburgbudgetproject.org/…                                      200  age: 258215
    lunenburgbudgetproject.org/…?cachebust=1                          301  correct

Same edge, same IPs, same deployment. A query string changes the cache key and the answer
comes back right, so it is one cache entry per URL, made about three days before the move
under `cache-control: public, s-maxage=604800`. Two dashboard purges — Purge Everything
and a Custom Purge of the exact 21 — did not clear them; `age` kept climbing from the same
origin timestamp. Why is not established. No zone-scoped credential was available to read
Cloudflare's own answer to the purge.

**What a reader actually gets, measured rather than assumed:**

| | |
|---|---|
| 13 of 21 | the **byte-identical current document**. A 200 where a 301 belongs, nothing else |
| 6 of 21 | a `.txt` extraction 5–10 bytes older |
| **2 of 21** | genuinely stale: `txt/fy27-balanced-slides-3-23-26.txt` serves **520 bytes** against a current **7,415** — the pre-OCR extraction of an image-only slide deck. `txt/fy27-sc-slidedeck-3-23-26.txt` likewise |

None of the 21 is linked from the site; they are addresses that existed before
4 September. The list is in `purge-these-21-urls.txt` at the repository root, which can be
deleted once this clears.

**Re-check with:**

    python3 scripts/check_archive_urls.py --base https://lunenburgbudgetproject.org --limit 1

`--limit 1` fetches one document and then runs the whole alias sweep, which is the part
this is about. Expect `138 of 138` once the entries expire.

**The durable half is already fixed.** Redirects now carry `cache-control: public,
max-age=3600`, so the longest this file can be wrong about where a document lives is an
hour. Something on the zone still caches `/docs/` documents for a week — worth finding in
Caching → Cache Rules, because it is why a three-day-old asset outlived the deployment
that created it.

### The trap in untracking: a branch switch DELETES the files

**This happened, was caught, and was recovered from — 5 September 2026.** Nine contract
PDFs, 91 MB, vanished from the working tree.

`git rm --cached` keeps a file on disk. What it does not survive is **moving between a
commit that tracks the file and one that does not**: merging `archive-storage` into `main`
applied the deletion to the working tree, and the bytes went.

- **What caught it:** `build_source_index.py`, with *catalogued but not on disk*. It had
  not been run between the merge and the next time somebody asked a question. Nothing else
  in the check suite looks at whether a document is on this disk.
- **What fixed it:** `python3 scripts/sync_archive.py --pull` — nine files, each hash
  checked against the manifest after download. This was the first real use of the bucket
  as a backup and it did exactly what it was built for.
- **It failed the first time**, with `403 Forbidden` on all nine, against a bucket whose
  public access was enabled and working. `r2.dev` refuses urllib's default
  `Python-urllib/3.11` User-Agent. Fixed, and worth remembering: a recovery path is not a
  recovery path until it has recovered something.

**So after any branch switch or merge that crosses the untracking commit, run:**

    python3 scripts/sync_archive.py --pull
    python3 scripts/build_source_index.py

### What is NOT established

- **That the r2.dev public URL is the right long-term address.** It works and it costs
  nothing. A custom domain was deferred, not rejected. Nothing published points at it: the
  app links `/docs/<path>` and the Function proxies, so changing it later costs one file.
- **That every object will still be there in ten years.** The lock stops deletion by
  mistake, not by an administrator who means it, and not the account lapsing.
- **That the 3.1 GB backup is current.** It was taken 5 September before any of this.

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
