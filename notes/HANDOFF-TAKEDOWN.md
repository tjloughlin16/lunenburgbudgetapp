# Handoff: a way to DELETE from the archive -- and the 16 documents that need it first

Written 6 October 2026 for a fresh session. Nothing here is built yet.

## DECIDED 7 October 2026: the logins are NOT a reason to delete anything

TJ, told the logins look like staff email names: *"ok if its emails then fine, not an
issue."* So the "first case" below is closed and nothing is to be taken down for it.

What was established before that decision, so it is not re-derived:

- The `User: +[a-z]` grep found ONE of three MUNIS header layouts. The others put the login
  on its own line after the run timestamp, or just before `Program ID`. Across `sources/`
  that is **25 documents and six logins** (OCR variants folded: `korochu` = `kbrochu`;
  `mcnamara`, `cmchalara`, `cmcnamard` = `cmcnamara`): 17 first published by us (records
  requests: `town-ledgers/`, the Finance Committee delivery) and 8 published by the town or
  district themselves (district quarterly reports, select-board minutes 2011 and 2013).
- Checked against the staff listings (`sources/data/staff-directory.csv`,
  `school-staff-directory.csv`) and the archive: `kbarrett@lunenburgma.gov` and
  `cmcnamara@lunenburgschools.net` are printed in the directories; `kbrochu@lunenburgonline.com`
  in a 2015 budget; `eayala@lunenburgma.gov` (Ezequiel Ayala) in the change metadata of the
  Finance Committee's `fy26-budget/preliminary-budget-presentation.pptx`. `adriggers` and
  `pstewart` are in neither listing nor the rosters -- former staff, it appears -- and are
  covered only by the district's own stated rule, *"All Emails are first initial, last name
  @lunenburgschools.net"*, which is consistent with all six. That a MUNIS login is DEFINED as
  the email name, rather than matching it for these six, is not established.

The delete mechanism itself is still wanted (TJ, 6 October: *"we HAVE to have a way to delete
things"*); it simply has no current case. The design below stands for when one arrives.

## Why

TJ, 6 October 2026: *"we HAVE to have a way to delete things. it can't truly be permanent.
thats silly."* And, on the precondition: *"we need a full backup made to make sure we don't
lose data. You can make an OOPSY and BOOM, We're screwed."*

**The first case.** Sixteen MUNIS documents already public print staff MUNIS LOGINS on
their pages -- four accounts, found 6 October 2026 by grepping `User: +[a-z]` across
`sources/town-ledgers` and `sources/budget-workbooks`. The PII screen did not flag them; a
login is not a pattern it knows. They are in the public bucket and their `.txt` copies are
in git. (Run that grep to get the list; do not copy it from here -- rule 2.)

## What is true about the lock (observed 6 October 2026)

    npx wrangler r2 bucket lock list lunenburg-budget-project      # from fy28/, Node 22
    name: immutable-sources   enabled: Yes   prefix: (all prefixes)   condition: after 3650 days

One rule, the whole bucket. Wrangler has `lock remove` and `lock set`, so the account owner
CAN lift it. "Ten years" is a setting, not a property of R2. Re-read the Cloudflare docs on
R2 bucket locks before relying on any of this; and remember CLAUDE.md: **R2 answers a DELETE
on a locked object with success and keeps the object** -- whether an object is gone is
answered by LISTING it afterwards, never by the response.

## The design TJ approved (the "supersede + stop serving" option, plus real deletion)

1. **A register**, `sources/data/takedowns.csv`: key, sha256, reason, decided_by, decided_on,
   state (`stopped serving` -> `deleted` -> `superseded_by <key>`). Every removal is written
   down, exactly as redactions.csv records every publish decision.
2. **Stop serving at once**: `fy28/functions/docs/_bucket.js` answers **410 Gone, with the
   reason**, for any key in the register. No bucket change needed. (Deploying is rule 10:
   only when TJ asks.)
3. **Real deletion**, `scripts/takedown.py --delete`:
   - REFUSES unless `python3 scripts/backup_snapshot.py --covers <key>` finds the key in a
     VERIFIED snapshot (the backup exists before anything is deleted -- TJ's condition);
   - lifts the lock rule, deletes the listed objects, confirms each is gone BY LISTING,
     re-adds the lock and confirms it is back -- in a `finally`, so the bucket is never left
     unlocked on any failure path;
   - updates the register and `archive-manifest.csv` / `archive-orphans.csv` so nothing
     reports a deleted document as held.
4. **The 16 documents**: build login-masked copies with `redact.py` (a PDF is rebuilt as
   images -- see its docstring on overlay redaction), publish them under new keys, repoint
   the catalogue and links, mask the logins in the `.txt` copies in git, then take the
   originals down through 2 and 3.

## Two things this does not do -- say so to TJ, do not decide them

- **Git history keeps the old `.txt` copies.** Removing them means rewriting history and a
  force-push, which breaks every clone. A separate decision.
- **Copies outside our control** -- search engines, the Wayback Machine -- are not reached by
  deleting our object.

## The backup

`scripts/backup_snapshot.py` (6 October 2026) writes a full snapshot OUTSIDE the repository,
`~/lunenburg-backups/<timestamp>/`: every object in both buckets (each re-read and checked
against the bucket's etag), a `git bundle --all`, and an archive of every uncommitted file in
the working tree. A snapshot without `VERIFIED.txt` does not count.

**The first verified snapshot:** `~/lunenburg-backups/2026-10-06-214608/`, verified
2026-10-07 00:59 -- every object in both buckets re-read and matched, the git bundle
verified, the uncommitted working tree archived; `--verify` re-hashed it independently and
passed. Its first attempt died on one HTTP 524 and was resumed, which is why failures are now
retried rather than fatal. Take a FRESH snapshot immediately before the first real deletion:
this one is a floor, not a licence.

It is on the SAME DISK as the working tree, so it protects against a deletion bug, not
against losing this machine. An off-machine copy (an external drive, or a second bucket
under its own lock that the takedown tool is never given) is still worth having.

## Also open from that day

- The 9 PDFs of the 6 October MUNIS delivery are `pending` in redactions.csv because every
  page prints the report user's login. Once redaction-by-mask exists for them they can be
  published as masked copies; the spreadsheets already carry every figure.
