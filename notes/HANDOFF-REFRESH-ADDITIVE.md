# Design: a refresh that is only ever additive, and never blocks on the whole repo

Written 8 October 2026 for TJ's approval. Nothing here is built yet.

TJ, 8 October 2026: *"refresh should be always additive. so i dont know why it requires no
change anywhere or it gets blocked"* -- *"refresh should work in whatever branch we're
currently on. needing to check out a new branch is silly. we did that for good reason
before, but its only hurt us"* -- *"this shouldnt have ANY chance of a destructive path"* --
*"if we have a page with edits, and the refresh would impact THAT page, just count that page
as not yet refreshable, but dont fail everything. just mark that page as a block and move on."*

## Why the current one almost never finishes

Three all-or-nothing gates, none of them about the new data:

| gate | what it demands | what happened |
|---|---|---|
| a clean, current worktree | it RESETS `~/lunenburgbudgets-refresh` to main each morning, so it first refuses unless that tree is pristine and its gate script exists | blocked 5, 6, 7 October: the tree was on a 22 September commit with no gate script |
| a fast-forward push | if main moved during the run, the push is rejected | 8 October: pushed to a side branch, `refresh-2026-10-08`, merged by hand |
| every generated file fresh | `check_generated` over all 159 checks; ANY stale output blocks the deploy | 8 October: 14 unrelated outputs (state aid, money flow, README...) held back new meetings |

## The design

### 1. It runs in the working tree, on the current branch

No second worktree, no reset, no checkout. Three rules, each from a real incident:

- **It stages only the files it wrote** -- never `git add -A`. The shared tree holds other
  sessions' uncommitted work and the governor's in-flight output.
- **It deploys only from `main`.** On another branch it ingests, processes, commits and
  reports `not deployed: on branch X` (15 September: a refresh built a feature branch and
  Cloudflare put the deploy on a preview alias).
- **One site build at a time** -- it waits for the build lock; `dist/` is shared.

### 2. Ingest is additive and cannot block

Fetch -> land in the bucket (read back) -> manifest row -> text and index rows. Before it
commits: `git pull --rebase`; if main moves during the run, rebase and retry, never a side
branch. Append-only files (`agentic-spend.csv`, run logs) get git's built-in **union merge**
in `.gitattributes`, so they cannot conflict -- the resolution done by hand on 8 October,
which must keep both sides' rows EXACTLY, duplicates included.

### 3. Publishing is scoped to what changed, page by page

- Each generator declares the inputs it reads (seeded from what its `--check` already names).
- From the files ingest touched, the refresh derives the set of generators to re-run --
  new meetings mean the register, the board pages, the feeds, search, the backlog charts.
- **A page with uncommitted changes the refresh did not make is NOT YET REFRESHABLE**: it is
  skipped, listed in the morning report with its reason, and caught up the first morning after
  those changes are committed. Nothing else waits for it.
- Only the re-run generators' checks gate the deploy. A stale output elsewhere is REPORTED,
  never blocking.

### 4. No destructive path, enforced by a check rather than promised

- No `reset`, `clean`, `checkout -- <file>`, `stash`, `push --force`, and no deletion of a
  document or data file. The bucket's lock refuses overwrites.
- **`scripts/check_refresh_safe.py`** fails the build if the refresh's code ever contains one of
  those, or `rm` / `os.remove` outside `build/`. It runs with every other check, so a later edit
  cannot quietly reintroduce one.
- The worst a refresh can do is not update something, and say so.

## Retired by this

- `~/lunenburgbudgets-refresh` and `scripts/setup_refresh_tree.sh` (the old commit
  `578b53d9` is kept on the branch `stranded-refresh-2026-09-22` in that tree).
- The "pristine tree" stop and the "everything fresh" deploy gate.

## Not decided -- TJ's call

- Whether the morning report should be a notification, a file, or both.
