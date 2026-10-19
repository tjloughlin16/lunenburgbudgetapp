# Removing a document from the public archive

**Built 19 October 2026.** The mechanism as it exists, not as it was designed; the design is
`notes/HANDOFF-TAKEDOWN.md`. TJ, 6 October 2026:

> *"we HAVE to have a way to delete things. it can't truly be permanent. thats silly."*

and the condition he set on it:

> *"we need a full backup made to make sure we don't lose data. You can make an OOPSY and
> BOOM, We're screwed."*

    python3 scripts/takedown.py --status       # every taken-down key: bucket, private copy, snapshot, site, r2.dev
    python3 scripts/takedown.py --dry-run      # exactly what --delete would do, and every reason it would refuse
    python3 scripts/takedown.py --delete       # TJ's call, and only after the steps below

## When to use it

**A document already public holds private information about a person who is not acting in a
public role**: a child, a family, a private resident. The first case was three raw MUNIS
journal exports of the athletics revolving fund (`account-details-fy2024/2025/2026-fund1301.xlsx`),
which name a family on a returned (NSF) fee check. Their figures were already published,
with the family removed, in `sources/data/fund-1301-cash-journal.csv`.

**Not for MUNIS logins.** Sixteen MUNIS documents print a staff login in their headers. TJ,
7 October 2026, told they are staff email names: *"ok if its emails then fine, not an
issue."* They stay.

**Not for a document that was never public.** A records-request delivery that has not
reached the public bucket goes through the gate (`redact.gate()`, CLAUDE.md 13e) and is
held privately from the start. Taking down is for the case the gate missed.

**Not for a correction.** A wrong copy of a publisher's document is superseded under a new
key and registered in `document-defects.csv` or `archive-orphans.csv`. Deletion is for
harm to a person, not for tidiness.

## The order, and why it cannot move

| # | step | what does it | why here |
|---|---|---|---|
| 1 | **Private copy** | the raw put in `lunenburg-budget-private` at `raw/<key>`, read back, sha256 matched | before anything else, so no step that follows can lose the bytes |
| 2 | **Withhold row** | `sources/data/redactions.csv`: `withhold`, the reason, the public copy, who decided | the gate's register is what every other check reads |
| 3 | **Out of the tree** | the local file moved out of `sources/` into gitignored `build/private/` (MUNIS: `build/private/munis/raw/<key>`); its extractor reads from there or from the private bucket, sha-checked | `redact.py --check` fails a withheld document present in `sources/`, and a document in `sources/` is a document the catalogue publishes |
| 4 | **Takedown row** | `sources/data/takedowns.csv`, state `stopped serving` | the 410, the pull, the backup gate and `--delete` all read it |
| 5 | **The 410 module** | `python3 scripts/takedown.py --write-module` writes `fy28/functions/docs/_takedowns.js` | the site never reads the CSV at runtime |
| 6 | **Catalogue** | the entry removed from `GROUPS` in `scripts/build_source_index.py`, then that script run | otherwise `sources.json` keeps linking to the withdrawn address |
| 7 | **Deploy** | `bash scripts/deploy_site.sh` (rule 10: only when TJ asks). It refuses if the module is stale | stopping serving is the urgent half and needs no bucket change |
| 8 | **Purge the edge cache** | the Cloudflare dashboard: Caching > Purge by URL, each `/docs/<key>` | the zone caches `/docs/` answers for a week; without a purge the old 200 keeps being served |
| 9 | **Fresh verified snapshot** | `python3 scripts/backup_snapshot.py` (takes hours; both buckets, git, working tree) | `--delete` refuses a snapshot older than the decision: the 6 October one is a floor, not a licence |
| 10 | **Dry run** | `python3 scripts/takedown.py --dry-run` | prints the plan and every refusal; nothing changes |
| 11 | **Delete** | `python3 scripts/takedown.py --delete` | the only step that cannot be undone, so it is last |
| 12 | **Confirm** | `python3 scripts/takedown.py --status` | the public bucket must say `NOT listed` |

## What `--delete` refuses on

For every key, each read from the thing itself:

- the register says `stopped serving`, and **the live site already answers 410** for it;
- the private copy exists and hashes to the registered sha256;
- `backup_snapshot.py --covers <key>` finds it in a VERIFIED snapshot, the snapshot's file
  hashes to the registered sha256, **and the snapshot is dated on or after the decision**;
- the public bucket lists the key, with the etag the manifest records;
- `check_archive_backed_up.py` is green.

Then it saves the lock configuration, lifts it, deletes, lists, and restores the lock in a
`finally` -- on every path, including a failure halfway. Only keys confirmed gone are
recorded: `takedowns.csv` to `deleted`, the row removed from `archive-manifest.csv`, a row
added to `archive-orphans.csv` so `check_manifest_history.py` knows it left on purpose.

## The lock

    npx wrangler r2 bucket lock list lunenburg-budget-project      # from fy28/, Node 22

One rule, `immutable-sources`, all prefixes, Age 315,360,000 seconds (3,650 days). The
account owner can lift it; "ten years" is a setting. `takedown.py` lifts and restores it
through the REST API (`GET`/`PUT .../r2/buckets/<bucket>/lock`, the body
`wrangler r2 bucket lock set --file` takes), compares the restored rules to the saved ones
field by field, and prints `wrangler r2 bucket lock list` as a second reading. If the two
disagree it prints both and says to restore it by hand. Cloudflare's docs do not say how
quickly a lock change propagates, so a DELETE straight after lifting may still be refused;
the listing will show it, and `--delete` can be run again.

## "Gone" is answered by LISTING

**R2 answers a DELETE on a locked object with success and keeps the object** (found 5
October 2026). So the DELETE response is never read. A key is gone when a listing of that
exact key comes back without it, and `--status` re-asks the bucket every time.

## What this does not reach

- **Git history.** Any text copy ever committed stays in history. Removing it means a
  rewrite and a force-push that breaks every clone -- a separate decision, TJ's.
- **Copies outside our control.** Search engines, the Wayback Machine, anybody who
  downloaded it. Deleting our object does not reach them.
- **Cloudflare's edge cache**, until it is purged (step 8).
- **The r2.dev URL** until the object is deleted. The 410 is the site's answer; the bucket's
  own public URL serves the object directly until step 11.
- **Generated pages that cite the raw.** A page built before the takedown may still link to
  the address; it now answers 410 with the reason. Regenerate the page from its script and
  repoint the citation to the public replacement.

## Where each piece lives

| piece | file |
|---|---|
| the register | `sources/data/takedowns.csv` |
| the tool | `scripts/takedown.py` |
| the 410 | `fy28/functions/docs/_takedowns.js` (generated) and `goneFor()` in `_bucket.js`, called first in `[[path]].js` |
| never pulled back | `archive_storage.taken_down()`, read by `sync_archive.py --pull` and `incomplete()` |
| the checks | `takedown.py --check`, run by `check_generated.py` and `deploy_site.sh` |
| the backup | `scripts/backup_snapshot.py`, `~/lunenburg-backups/<timestamp>/` |
