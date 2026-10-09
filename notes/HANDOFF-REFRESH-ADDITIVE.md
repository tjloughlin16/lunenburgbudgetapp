# Design: a refresh that is only ever additive, and never blocks on the whole repo

Written 8 October 2026 for TJ's approval. **Built 9 October 2026** on a worktree branch, not
yet merged -- see *What was built* below. Merging it into the branch checked out at
`~/lunenburgbudgets` is what switches it on.

TJ, 8 October 2026: *"refresh should be always additive. so i dont know why it requires no
change anywhere or it gets blocked"* -- *"refresh should work in whatever branch we're
currently on. needing to check out a new branch is silly. we did that for good reason
before, but its only hurt us"* -- *"this shouldnt have ANY chance of a destructive path"* --
*"if we have a page with edits, and the refresh would impact THAT page, just count that page
as not yet refreshable, but dont fail everything. just mark that page as a block and move on."*

## Why the old one almost never finished

Three all-or-nothing gates, none of them about the new data:

| gate | what it demanded | what happened |
|---|---|---|
| a clean, current worktree | it RESET `~/lunenburgbudgets-refresh` to main each morning, so it first refused unless that tree was pristine and its gate script existed | blocked 5, 6, 7 October: the tree was on a 22 September commit with no gate script |
| a fast-forward push | if main moved during the run, the push was rejected | 8 October: pushed to a side branch, `refresh-2026-10-08`, merged by hand |
| every generated file fresh | `check_generated` over every check; ANY stale output blocked the deploy | 8 October: 14 unrelated outputs (state aid, money flow, README...) held back new meetings |

## What was built, 9 October 2026

| file | what it does now |
|---|---|
| `scripts/daily_refresh.sh` | Runs `refresh.py --deploy` in the tree it lives in, on the current branch. No hand-off, no reset, no clean, no pristine check, no `add -A`, no side branch. Keeps the once-a-day guard (a day is done only when its last `refresh exit` is 0), the per-day log, the alert file and notification. `check_archive_backed_up.py --push` still runs first, as a warning rather than a gate, because nothing destructive follows it any more. |
| `scripts/refresh_git.py` (new) | Everything the refresh does with git. A **baseline** at the start copies every already-dirty file into `build/refresh-baseline/<stamp>/`. At the end **settle** finds the run's own files, PUTS BACK any already-dirty file the run overwrote (the run's version kept in `.../conflicts/`) and reports it as *not yet refreshable*. **commit** stages only those paths, from a pathspec file, with `--only`, so another session's staged entries stay out. **publish** fetches, and if origin/main moved, replays the refresh's commits onto it with `git merge-tree` and moves the tree with a two-tree `read-tree -m -u` that REFUSES rather than overwrites; push retried up to `PUSH_TRIES` times; never a side branch, never a force. |
| `scripts/refresh.py` | Takes the baseline first (`--commit`, implied by `--deploy`); commits the run's files BEFORE judging a deploy; deploys only when the branch is `main`, the commit reached origin/main and HEAD equals it, no file under `fy28/` holds somebody else's uncommitted change, and **every generator this run executed** reproduces. A run that dies still commits what it fetched. New weekly step: the AG's Open Meeting Law determinations. |
| `scripts/check_refresh_safe.py` (new) | Fails if `daily_refresh.sh`, `refresh.py`, `refresh_git.py` or `triage_refresh.py` contains `git reset/clean/stash/checkout/restore/switch/rebase/rm`, a force push, `branch -D/-f`, `update-ref -d`, `worktree remove`, or a delete outside `build/`. `--selftest` proves it still catches each banned form. Registered first in `check_generated.py`. |
| `scripts/test_refresh_git.py` (new) | Makes each situation happen in throwaway repositories under `build/` and asserts on what is on disk: uncommitted work put back and never staged, a mid-run commit by the owner left alone, an append-only log keeping everybody's rows, a moved main replayed onto (and the union line proven load-bearing by a case without it), a move that would touch uncommitted work refused, a real conflict kept local, a push race retried, a side branch never pushed, nothing committed into a half-finished merge. Registered in `check_generated.py`. |
| `scripts/triage_refresh.py` | `--own-tree`: the agent works in a DETACHED worktree under `build/refresh-triage/tree-<date>/`, never in the person's tree. No branch, no commit; its edits stay there for review. |
| `.gitattributes` (new) | `merge=union` for the append-only logs: `agentic-spend.csv`, `ocr-minutes.csv`, their published copies, and the `checked.csv` look-logs. Deliberately NOT `archive-manifest.csv`, `archive-push-state.csv`, `refresh-runs.csv` or `meetings/index.csv`, which are keyed or rewritten -- union on those would keep both versions of a changed row. |
| `ops/README.md` | Says the refresh runs here now. |

### Decisions taken while building, that differ from or add to the design

- **Generator inputs are NOT declared** (design §3, first bullet). The gate is scoped by what
  the run EXECUTED -- recorded where each subprocess starts (`RAN` in `refresh.py`) -- not by
  a per-generator input list. Consequence: a generator the run did not execute, whose input
  the run changed, is REPORTED as stale and does not block. Declaring inputs is still the
  way to make the run re-run exactly those.
- **"Not yet refreshable" is per FILE, not per page.** A file the run overwrote that held
  somebody's uncommitted change is put back and named. The generator that wrote it may then
  fail its check and block the deploy -- which is honest: what is on main was not built
  from what is on main.
- **An append-only log that already held uncommitted rows is left as it is**, unstaged, when
  the run only appended (checked: union-declared, and the pre-run bytes are an exact prefix).
  `agentic-spend.csv` is that file most mornings because the paced minutes run appends all
  day; putting the old copy back would only discard the refresh's rows.
- **A person's unpushed local commits are never pushed for them.** If `main` holds local
  commits that are not the refresh's (each refresh commit carries a `Refresh-Run:` trailer),
  the refresh commits locally and reports `NOT PUSHED (local-only)`.
- **No deploy while `fy28/` holds somebody else's uncommitted change.** The build reads the
  working tree, so it would ship that change to production uncommitted. Refused and named.
- **The run row is a second, small commit.** The row cannot say whether the run deployed
  until after the deploy, which now follows the first commit.
- **Weekly OML step**: gated on `build/oml-determinations-last-fetch.txt`, written only on
  exit 0, so a failed week is retried the next morning; January also walks the previous
  year. New letters are counted as `state documents` found (`state-law` joins the folders
  the refresh writes into).

## Not done

- `scripts/setup_refresh_tree.sh` and `~/lunenburgbudgets-refresh` are retired in the docs
  but left on disk. Nothing runs either any more; removing them is a person's call.
- What a commit made by ANOTHER process during the run looks like to `settle`: a file that
  was clean at the start and written mid-run by, say, the paced minutes run is committed
  with the refresh's files. It is the same additive output and would be committed anyway;
  the case that matters -- an edit in progress -- is the pre-dirty one, which is protected.
- Not run for real: no `claude -p`, no push, no deploy. Tested by `--dry-run` and by
  `test_refresh_git.py`.

## Not decided -- TJ's call

- **The morning report**: a notification, a file, or both. Unchanged for now: the run log
  (`build/refresh-logs/<date>.log`), `sources/data/refresh-runs.csv`, and
  `build/refresh-found/<date>.json`, which the dashboard reads. The macOS notification still
  fires on a failure only.
- **Whether a dirty `fy28/` should block the deploy**, or whether the deploy should build
  from a clean checkout of main instead. Blocking is the safe default; building elsewhere
  needs `node_modules`, the database and the prerender inputs in that checkout.

## To switch it on

1. Merge the branch into the branch checked out at `~/lunenburgbudgets` (normally `main`).
   The launchd job already runs `~/lunenburgbudgets/scripts/daily_refresh.sh`, so the next
   07:00 or login firing uses the new code. **No plist change is needed.**
2. Run `python3 scripts/refresh_git.py --status` in that tree first: it lists what a run
   starting now would treat as somebody else's uncommitted work.
3. Optionally `python3 scripts/refresh.py --dry-run` there, then watch the first real log.
