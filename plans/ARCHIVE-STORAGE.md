# Getting the binaries out of git without breaking anything

**Status: planned, nothing done.** A backup exists (see below). No file has been moved,
deleted or untracked.

`plans/ARCHIVE-REORG.md` is where documents live. This is what they are *stored on*.

---

## The problem, in one table

    git pack today                    291 MB
    sources/ on disk                1,200 MB

    annual town reports (17, arriving)  411 MB
    ten largest other documents         187 MB
    everything else                     600 MB

**And more is coming than this shows.** The town runs two document stores and only one was
ever crawled: `/DocumentCenter/` holds what is current, `/ArchiveCenter/` holds what has
been retired — twelve categories including town meeting and budget documents for FY12
through FY25. `fetch_town_docs.py` was extended to walk both on 4 September. The archive is
about to grow by an amount nobody has measured yet, which is the argument for changing the
storage model now rather than after.

**One series is the whole problem.** The annual reports average 24 MB each and are still
landing. Twenty years of them is ~500 MB, taking the repository to roughly 800–900 MB —
GitHub's recommended ceiling is 1 GB, and every clone and CI run pays it.

GitHub's hard limits: **100 MB per file** (push rejected), 50 MB warning. The largest file
here is 51 MB, so the wall is closer than the totals suggest.

## Why this is safe to do at all

**293 of the 307 catalogued documents have an extracted-text companion, and agents read
the text.** `llms.txt` tells them to: look a word up in a shard, resolve it in
`documents.json`, then fetch the `.txt` — *"Cite this, never the index and never a
bundle."* Every one of the ten largest documents has text beside it.

So moving a PDF out of git does not move anything an agent reads.

## The design

**Object store holds the binaries. Git holds the index, the text, and the code.**

    git                                    R2 bucket
    ─────────────────────────────          ─────────────────────────
    index.csv  (upstream url, sha256)  →   sources/<path>   the bytes
    <name>.txt  extracted text             bucket-locked, no versioning
    analyses, scripts, model, CSVs

The integrity contract already exists: **every mirrored document already carries a sha256
in its `index.csv`.** That is what makes the bucket verifiable rather than merely
convenient, and it is why this is a smaller change than it sounds.

### Agentic discovery and fetching must not change — how that is guaranteed

This is the constraint the whole design bends around. `llms.txt` publishes
`/docs/<path>` and tells agents to cite those URLs. **They keep working, unchanged.**

`fy28/functions/docs/[[path]].js` already intercepts every `/docs/` request — it is how
the reorg's 301 aliases work. It gains one more branch:

1. asset present in the build → serve it (today's behaviour, unchanged)
2. not present, but the path moved → 301, as now
3. not present, and it is in the bucket → **stream it from R2 under the same URL**
4. otherwise → the 404 that explains itself

An agent sees a document at exactly the address `llms.txt` gave it, whatever the storage
underneath. **No URL changes, no `llms.txt` change, no `documents.json` change, no change
to the search index or the bundles.** The one visible difference is a first-byte latency
on a large PDF, which is a document nothing was reading anyway.

**Verification is a test, not an assertion.** Before the bytes leave git, a script fetches
every `/docs/<path>` in `sources.json` against a preview deploy and asserts a 200 with the
right sha256. That is the gate; it does not ship until it passes.

### What moves, and what does not

**Everything goes, not a size threshold.** An earlier draft of this plan moved only files
over 5 MB. That is wrong, and the reason is the requirement below: **the bucket is the
public download area**, and a download area holding only the large half of the archive is
incoherent — somebody browsing it sees gaps with no rule behind them, and no way to tell a
missing document from one that was never mirrored.

| | |
|---|---|
| **In the bucket** | every file in `sources/` — the whole archive, browsable |
| **In git** | extracted text, every manifest, all CSVs, analyses, scripts, model |
| **Untracked from git** | the binaries, once verified in the bucket. They stay on disk |

Git keeps what is small, diffable, and read by everything. The bucket keeps the bytes and
becomes the thing a person or an agent downloads from.

### The bucket layout IS the public structure

This is why the folder reorganisation had to come first. Keyed on the archive path, an
object's address describes itself:

    <bucket>/town-annual-reports/docs/4117-fy-2011-annual-town-report.pdf
    <bucket>/munis-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx
    <bucket>/meetings/school-committee/2026-06-24-minutes-7869.pdf

A person landing on that URL can tell what they have and where it came from without
consulting anything. Under the old layout the same object would have been
`q3-fy26/town-general-fund-expenditures-fy26-q3.pdf` — a folder named for when we filed a
request, which tells a stranger nothing.

**So the layout is now load-bearing in a second way.** It was internal organisation; it
becomes a published interface, and renaming a folder afterwards costs a redirect for every
object under it. `plans/ARCHIVE-REORG.md` should be settled before the first upload.

## Safety — the part that matters

**Nothing is deleted. Ever, in this plan.**

Two operations get mistaken for deletion and neither is:

- `git rm --cached` removes a file from git *tracking*. The file stays on disk.
- Removing a byte-identical duplicate copy is not losing a document, and every such
  removal re-checks the sha256 first.

**Copy, verify, then untrack — in that order, per file:**

1. upload to the bucket
2. read it back and compare sha256 against `index.csv`
3. only on a match, `git rm --cached`
4. the local file is left exactly where it is

A failure at any step leaves the file tracked in git, which is the state we started in.

### Backups

**Taken before any of this, on 4 September 2026**, and this must stay true:

    ~/lunenburg-archive-backup/
        sources/              3,432 files, 1.2 GB, rsync -a
        MANIFEST-sha256.txt   3,428 hashes
        README.md             refresh, verify, restore

Refresh it immediately before anything destructive:

    rsync -a --delete-after ~/lunenburgbudgets/sources/ ~/lunenburg-archive-backup/sources/

**Re-fetching is not a recovery path.** 57 source links died in a single day in August
2026, and several documents here are no longer at their original addresses. The crawl took
hours and some of it cannot be repeated.

A copy on the same disk protects against a mistake in the repository, which is what it was
taken for. It does not protect against disk failure. **The bucket is the off-machine copy**,
and that is a second reason to do this rather than only a cost argument.

### Bucket configuration — to confirm against current Cloudflare docs before building

R2 is S3-compatible and already in use: the 51 MB teacher contract is served from
`pub-5baef0f2604545c398a39a176e400e34.r2.dev` through the `ELSEWHERE` map in
`build_source_index.py`. That is a working proof and nothing more — there is no bucket in
`wrangler.jsonc`, no upload script, and no record of how that file got there.

To settle from the docs rather than memory, because the whole point is deletion safety:

- **CONFIRMED 5 Sep: R2 has NO object versioning.** Use **bucket locks**, which prevent deletion *and* overwriting, per prefix or bucket-wide, Age / date / Indefinite, and apply to existing objects too
- **lifecycle rules** — and whether one could ever expire an object we depend on
- **retention / object-lock** semantics, if any
- whether public `r2.dev` access is appropriate for the archive, or a custom domain is
  better

Public read is the default assumption: it costs nothing extra (R2 has no egress fees), it
needs no credentials for anyone cloning, and it matches rule 12 — *our processed copy,
downloadable*. It arguably improves on today, since each document gains a stable direct
URL rather than being reachable only through the site.

## New failure modes this creates, and the check for each

Naming them because a second system that can disagree with the first is the real cost.

| failure | caught by |
|---|---|
| in the manifest, not in the bucket | `check_archive_storage.py` — reconcile both ways |
| in the bucket, bytes differ from the manifest sha256 | same check |
| in the bucket, in no manifest | same check |
| a `/docs/<path>` that used to serve and now 404s | the pre-move URL test, run against a preview deploy |
| a fresh clone cannot build the site | `sync_archive.py --pull` in the documented build sequence |

## Order of work

0. **Review what the other agent built. This is more than a download.**

   The crawl was extended to a second document store and it produces derived data as well
   as files, so the archive has grown in ways a file count does not show. Nothing below
   should start until this is understood, because **the storage move takes a snapshot and
   anything wrong at that moment gets copied into the bucket and locked there, with no previous version to fall back to.**

   What to check, and why each one:

   - **What is new on disk, and how much.** `sources/` was 1.2 GB before the ArchiveCenter
     crawl. Re-measure by folder. The threshold decision was "everything", so the number
     only affects how long the push takes — but a surprise here means something landed
     that nobody meant to fetch.
   - **What new scripts exist, and what they write.** A new extractor that produces a CSV
     is a new thing to keep correct, and it needs the same treatment as the others: does
     it reconcile to a printed total, does it refuse to write when it does not.
   - **Every derived CSV it produced.** These are the ones that carry document paths, and
     the reorg has already shown that stale paths hide in data files long after the code is
     fixed. Check each against the current layout.
   - **`check_archive_layout.py`** — did anything land in a folder that does not exist, or
     under a name that does not carry its year? The town split will certainly have come
     undone again; that is expected and the repair script handles it.
   - **`build_source_index.py`** — is every new file catalogued, with an address? A
     document with no provenance is the thing rule 12 exists to prevent, and a crawl of a
     retired-documents store is exactly where one appears.
   - **The full standing suite**, against the baseline. Sixteen checks; anything that moved
     is either the crawl's doing or ours, and it matters which.
   - **`notes/findings/TOWN-ARCHIVE.md`** and whatever else they wrote — read it. It is
     likely to say what the ArchiveCenter contains and what it changes.

   Only when that is understood and green does anything move.

1. **Wait for the crawl to finish.** Moving bytes while it is writing
   is how a half-copied file gets its sha256 taken.
2. Refresh the backup and verify the manifest.
3. Re-apply the town split the fetcher flattened — `plans/ARCHIVE-REORG.md`.
4. Configure the bucket: indefinite bucket lock over all prefixes, no lifecycle rule, public read. (R2 versioning was checked and does not exist.)
5. `sync_archive.py --push` for one file. Verify. Then the rest.
6. `check_archive_storage.py` green both ways.
7. Add the R2 branch to the `/docs/` Function. Deploy to a **preview** URL.
8. Fetch every `/docs/<path>` against the preview and assert 200 + sha256. **This is the
   gate.**
9. Only then `git rm --cached`, and only for files verified in the bucket.
10. Document the pull step in `CLAUDE.md` and `fy28/README.md`.

Steps 1–3 are reversible. Step 9 is the first that changes what git holds, and by then the
bytes exist in three places: the bucket, the local disk, and the backup.

## Decisions taken — 4 September 2026

| question | answer |
|---|---|
| size threshold | **None. Everything in `sources/` goes.** |
| public or private | **Public**, read-only |
| meeting PDFs, 418 MB | **Yes.** They are gitignored so they cost git nothing today, but they exist on exactly one disk and `fetch_agendas.py` is their only copy — the bucket is the first real backup they have ever had |
| `minutes/` → `meetings/` | **Settled, leave it.** The folder is `meetings/`, the published URL stays `/docs/minutes/`, and the bucket follows the folder |

## "Safe, non-edit" — what that has to mean concretely

The bucket is public and it is an archive of public records. The risk is not disclosure;
it is **something changing without anyone noticing**, which is the failure this whole
project is built against — a Drive file can be replaced in place without its URL changing,
which is why every source already carries a sha256.

Five properties, each to be verified against current Cloudflare docs before the bucket is
created rather than assumed:

1. **Read-only to the public.** Anonymous access is GET and HEAD. No anonymous PUT, DELETE
   or LIST-then-write under any circumstance.
2. **Versioning on before the first object.** A later enable does not protect what is
   already there.
3. **No lifecycle rule that expires anything.** The default should be no rule at all. An
   expiry policy on an archive is a deletion scheduled in advance.
4. **Writes from one credential, held in one place**, used by `sync_archive.py --push` and
   nothing else. Not in the repository.
5. **`check_archive_storage.py` reconciles both ways** — every manifest row has an object
   with a matching sha256, and every object appears in a manifest. Drift in either
   direction is a finding, and it runs as part of the standing checks.

A sixth, which is really the point: **the local disk, the backup and the bucket are three
copies.** Nothing is untracked from git until the sha256 has been read back out of the
bucket and matched.

## Folder renames — DECIDED, to be done before the first upload

The bucket is a public download area, so every folder name is user-facing and renaming
after the first upload costs a redirect for every object beneath it. This is the last
cheap moment.

**A folder name does not have to be self-explaining if the archive teaches its own
vocabulary** — a reader who explores learns what `town-supplementary/` holds from the
company it keeps. So this renames only the names that are *opaque* rather than merely
unfamiliar, and lets the root README carry the rest.

| now | becomes | why |
|---|---|---|
| `munis-ledgers/` | **`town-ledgers/`** | MUNIS is the vendor's name for the town's accounting software. Nothing in the folder explains it, and "ledgers" is what they are. The subfolders — `expenses/`, `revenue/`, `account-details/`, `transfers/`, `purchase-orders/`, `fund-balances/` — already carry the detail |
| `dls/` | **`state-dls/`** | Two letters that mean nothing alone. `state-` tells a stranger it is a state agency, which is the fact they need |
| `dese/` | **`state-dese/`** | So the two state publishers read as a pair. DESE itself stays: every school finance document uses the acronym, so a reader holding one has seen it |
| `peers/` | **`peer-districts/`** | *optional* — "peers" alone is ambiguous, and it is twelve files |

**Named by publisher, not by contents.** `state-free-cash/` was considered for `dls/` and
rejected: it names what is in the folder today, and the moment DLS publishes something else
the name is a lie. Provenance is the one attribute that does not change, which is the whole
reason the tree is keyed on it.

### Deliberately not renamed

| | why |
|---|---|
| `data/` | Considered `derived-data/`. Beside `analyses/` it already reads as ours, the root README can say so in a line, and it is referenced as `sources/data/` throughout the code — the most expensive rename for the least gain |
| `docs/` + `text/` inside mirrors | `original/` + `text/` is genuinely clearer and genuinely not worth it: every mirror, and every published `/docs/<path>` URL |
| `town-supplementary/` | Vague alone, obvious beside `town-budget/`. The case for letting the archive teach its own vocabulary |
| `meetings/` `contracts/` | Plain English already, and `meetings/` is 2,846 files |

### What it leaves

Almost every folder then names its publisher, and the prefix is the organising principle
visible at a glance:

    town-budget/  town-supplementary/  town-annual-reports/  town-ledgers/
    district-budget/
    state-dese/  state-dls/
    peer-districts/
    meetings/  contracts/  correspondence/
    analyses/  data/

`meetings/` and `contracts/` break the pattern — both are town or district material filed
by genre rather than by publisher — and both are left alone because they are already clear.

### Cost

Four renames touch `sources.json`, `fy28/functions/docs/_moved.js`, `views/`,
`check_archive_layout.py`, and this plan. All mechanical, all covered by the standing
checks, and every old `/docs/<path>` keeps working because the alias map gains four more
prefix rules.

## What a stranger needs in the bucket itself

A folder of PDFs with no explanation is not an archive, it is a pile. Alongside the
objects:

- **`README.txt` at the root** — what this is, who made it, that it is a mirror of public
  records rather than an official source, and the one-line rule for what each folder holds
- **`MANIFEST.csv`** — every object with its path, size, sha256 and the publisher's
  original URL. This is what makes a download checkable, and it already exists per-folder
  as `index.csv`
- **a README in each folder** — one paragraph on what is in it and where it came from
- **the link back** to lunenburgbudgetproject.org, so somebody who lands on a PDF from a
  search engine can find the analysis it belongs to
