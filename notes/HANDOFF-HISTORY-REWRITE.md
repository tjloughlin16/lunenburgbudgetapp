# Handoff: unmasked journal names were in the PUBLIC GitHub history -- REWRITTEN 26 October 2026

**STATUS, 26 October 2026: steps 1-4 DONE; step 5 (GitHub's purge) is TJ's to file.**
TJ: "do whatever you think is the best idea. i dont want to lose anything". Done as:
- Backup first: `~/lunenburg-backups/2026-10-26-history-rewrite/` -- `repo-all-refs.bundle`
  (every ref, verified "okay"), `uncommitted-work.tar.gz` (the 333 uncommitted files of other
  agents) and `uncommitted-tracked.patch`, `show-ref-before.txt`.
- Rewritten in a SCRATCH CLONE, never the working tree (filter tools reset the working tree, and
  other agents' uncommitted work was in it): `git filter-branch --index-filter` removing
  `fy28/public/api/munis_school_journal*` from exactly the 17 commits `1f6be08d4`..`06576fbea^`;
  tags v15-v19 carried onto the new history.
- Proven before anything moved: the final tree is IDENTICAL; 1,890 commits before and after; of
  the 235 journal file versions in the bad commits, the only one still reachable is
  `munis_school_journal_account.json`, byte-identical to the reviewed publication `2ee126b2f`.
- Then `update-ref` main (old value asserted), working tree untouched (338 uncommitted entries
  before and after), and `git push --force-with-lease=main:23647187f` -> origin main `912264f5a`.
- Not rewritten, local only, never pushed: branches `wip-snapshot-2026-10-19` and
  `gen/town-office-space` still sit on the OLD history. Do not push either.
- **Step 5 TICKET FILED 26 October 2026** by TJ; waiting on GitHub Support. (Its assistant
  confirmed the request is in the right shape; NEVER run the `git push --force --mirror` it
  suggests here -- it would push the two old-history local branches and delete eleven remote
  branches). The ticket names the first changed
  commit `1f6be08d4901a0859a4f7d322db9f838aea2b40d`, range to `06576fbea`, 0 PRs, 0 forks).
  Done when https://github.com/tjloughlin16/lunenburgbudgetapp/commit/1f6be08d4901a0859a4f7d322db9f838aea2b40d
  stops answering 200 (it did on 26 October, before the purge).

---

Written 20 October 2026. **Deferred by TJ** ("put this into a handoff we'll do later"). Until it is
done: **do not push** anything else to `origin`, and do not clear this from the to-do list.

## What happened

- `1f6be08d4`, "Daily refresh, 2026-10-19" (08:34, 19 Oct), swept **235 files** under
  `fy28/public/api/munis_school_journal*` into a commit while they still carried **names that had
  not yet been masked** (the school MUNIS journal, before the redaction was finished).
- `06576fbea` removed them. The current tree is clean, but **both commits are in history.**
- The journal session set a hold: *no `git push` until the unpushed range is rewritten*, which TJ
  agreed to. It was recorded in Claude's project memory (`open-items-2026-10-19.md`), **not** in
  `CLAUDE.md`.
- On 19 Oct, the teacher-pay session pushed `main` to GitHub
  (`7b1343fd3..ceeaedeec`, then more up to `23647187f`) without seeing that hold. **Both commits are
  now on the public `origin/main`**, so the unmasked version can be opened from GitHub's history.
  About 58 commits sit between `1f6be08d4` and the last push.

## The fix

1. **Pause everything that commits or pushes:** the daily refresh (`daily_refresh.sh`, launchd),
   `process_meeting.py` runs, and every other Claude session working in this repo. Confirm the tree
   is quiet (`git status`, `pgrep -fl "refresh|process_meeting|claude"`).
2. **Back up first:** `python3 scripts/backup_snapshot.py`, plus a `git bundle create` of all refs,
   kept outside the repo.
3. **Rewrite history from `1f6be08d4^` onward** so that no commit contains any
   `fy28/public/api/munis_school_journal*` path with the unmasked content. `git filter-repo`
   (preferred) with a path filter on that range, or an interactive-free rebase that rewrites
   `1f6be08d4` without those files. Every later commit keeps its content and gets a new ID.
   - Before rewriting, check whether any LATER commit (after `06576fbea`) legitimately re-added
     `munis_school_journal*` API files with the MASKED content (the journal was published on
     19 Oct, `2ee126b2f`). Those must survive. Filter by content, or limit the path removal to
     `1f6be08d4` and `06576fbea` only.
   - Verify afterwards: for every commit in the new range, grep the journal API files for a few
     of the names the masking removes (take them from the private match files under
     `build/private/munis/`; **never print them into a log or a commit**). Zero hits.
4. **Force-push** the rewritten `main`: `git push --force-with-lease origin main`.
   - Other clones (the refresh tree, any other checkout) must then be reset to the new `main`, or
     they will push the old history back. The refresh tree STOPS on a dirty tree; make sure it is
     re-cloned or hard-reset to `origin/main` deliberately.
   - The local branch `wip-snapshot-2026-10-19` (never pushed) is based on the old history. Leave
     it local, or rebase it.
5. **Purge GitHub's copies.** After a force-push, old commits stay reachable by SHA and in forks,
   caches and PR refs. Check the fork count on the repo page. File a GitHub Support request
   ("remove sensitive data", their sensitive-data removal process) naming `1f6be08d4` and
   `06576fbea` and the paths. GitHub's own guide: "Removing sensitive data from a repository".
6. **Raw mirror:** `raw.githubusercontent.com/.../<old-sha>/...` URLs serve from those commits
   until GitHub purges them. That is part of step 5.

## Also pending: lessons for `CLAUDE.md` (TJ: put them in the project's CLAUDE.md, not memory)

Add these when the rewrite is done:

1. **Push holds live in `CLAUDE.md`, and every push checks them.** A hold recorded only in one
   session's memory is invisible to every other session. That is exactly how this happened. A
   short `## Push holds` section, empty when there are none, read before any `git push`.
2. **The `wip/` convention** for unfinished work (see `wip/README.md`).
3. **OCR only the pages you need, one document at a time.** Four parallel whole-contract OCR jobs
   held the laptop at full load for over 30 minutes and drained the battery while plugged in. For a
   salary schedule, find the appendix pages first.
4. **Comparison districts:** the district's own official set (FY2026 budget p57, Budget Task
   Force, plus the FY2020 picks; 11 districts in `sources/data/comparison-sets.csv`, still in
   `wip/`) is shown BESIDE the project's six, both labelled by who chose them.

## Related

- `notes/HANDOFF-TEACHER-PAY.md`: the teacher-pay work, also paused.
- `notes/HANDOFF-MUNIS-JOURNAL.md` and memory `open-items-2026-10-19`: the journal session's state,
  including the takedown sequence for three fund-1301 workbooks and a batched deploy.
