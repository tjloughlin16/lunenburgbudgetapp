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
    <name>.txt  extracted text             versioned, delete-protected
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

| | |
|---|---|
| **Moves to R2** | binaries over 5 MB — the 17+ annual reports and the 10 largest others, ~600 MB |
| **Stays in git** | all extracted text, every manifest, all CSVs, analyses, code |
| **Stays in git for now** | binaries under 5 MB. They are the long tail, they cost little, and a smaller change is a safer one |

The threshold is a starting point, not a principle. If the repository is still
uncomfortable afterwards it can come down; moving more later is cheap once the machinery
exists.

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

- object **versioning** — available, and how a delete is recorded
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

1. **Wait for the annual-report fetch to finish.** Moving bytes while a crawl is writing
   is how a half-copied file gets its sha256 taken.
2. Refresh the backup and verify the manifest.
3. Re-apply the town split the fetcher flattened — `plans/ARCHIVE-REORG.md`.
4. Confirm R2 versioning and retention against the docs; create and configure the bucket.
5. `sync_archive.py --push` for one file. Verify. Then the rest.
6. `check_archive_storage.py` green both ways.
7. Add the R2 branch to the `/docs/` Function. Deploy to a **preview** URL.
8. Fetch every `/docs/<path>` against the preview and assert 200 + sha256. **This is the
   gate.**
9. Only then `git rm --cached`, and only for files verified in the bucket.
10. Document the pull step in `CLAUDE.md` and `fy28/README.md`.

Steps 1–3 are reversible. Step 9 is the first that changes what git holds, and by then the
bytes exist in three places: the bucket, the local disk, and the backup.

## Open questions

1. **Threshold.** 5 MB moves ~600 MB and leaves the repo near 200 MB. Lower it?
2. **Public or private bucket.** Public is assumed above.
3. **Do the meeting PDFs move too?** They are 418 MB, already gitignored and already
   absent from git — so they cost nothing today, but they exist on exactly one disk and
   `fetch_agendas.py` is the only copy. Putting them in the bucket would be the first real
   backup they have ever had.
