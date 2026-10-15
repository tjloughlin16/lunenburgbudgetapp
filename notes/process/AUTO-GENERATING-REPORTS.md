# Auto-generating suggested reports: the trial, and what would let it run alone

TJ, 15 October 2026: *"the goal is that suggested reports may be auto-generated in 3 months
from now. so we need this process crisp, and it means we need to identify only reports that
make sense to auto-generate all the time."*

So every generation today is a **trial**, and the point of a trial is its record.

## The pipeline

1. **A meeting suggests a report.** Our minutes of each recording carry `suggested_reports`;
   `build_suggested_reports.py` merges them across meetings, ties each to the threads it would
   serve, and keeps every meeting it came up in, dated (`suggested-reports-meetings.csv`).
2. **It is scored and checked for fit**, before anything is spent
   (`build_suggested_reports.score()` and `autogen_fit()`). Fit is three mechanical tests:
   figures came up; a dataset is named for it; it comes back (several meetings, or a thread).
3. **A person presses Generate** on the dashboard's Suggested reports tab
   (`bash scripts/status.sh`, then http://127.0.0.1:8795/suggested.html).
4. **An agent builds it, in its own copy of the repository** (`scripts/generate_report.py`).
   Each generation gets a git worktree, `~/lunenburgbudgets-gen/<slug>`, on its own branch
   `gen/<slug>`. Inside it the agent can do anything a session could -- TJ: *"it should be able
   to do anything YOU could do ... such as creating a hub in case its a big report"*: register
   a hub and topics, write generators and extractors, change components, run checks. Sonnet,
   capped per run; Continue resumes with a fresh cap.
5. **A fence it cannot talk its way through.** The whole agent process runs under a macOS
   sandbox: it WRITES only inside its worktree, and cannot READ the Cloudflare credential, ssh
   keys or the GitHub token -- so no bucket push, no deploy, no D1, no git push, whatever it
   tries. The runner commits its tree after every run, so its work is in git within seconds.
6. **We check it by machine.** The agent declares the pages it built and the commands that
   prove them; the runner runs those itself, in the sandbox, plus the registry check.
7. **It reports back** in `notes/report-generations/<slug>/generation.json`: status, the
   verdict and its reasons, pages, checks, datasets, figures, open questions, gaps, the branch
   and its files. Questions are answered on the dashboard and the same session resumes.
8. **Review.** Start preview runs the site's dev server from the worktree; every page the
   agent built is a link. Your verdict is recorded beside the agent's.
9. **Publish** (`scripts/publish_generation.py`) -- the button is the request to deploy:
   replay the branch onto main (`git merge-tree`, nothing touched on a conflict), move the
   tree onto it or REFUSE if that would overwrite anybody's uncommitted work, rebuild the
   shared index files on main (never carried on the branch), run the checks on main, push
   without force, then build and deploy -- refused while `fy28/` holds somebody else's
   uncommitted change. Each page is then fetched from production.

**The refresh's failures, and why they cannot recur here.** It reset its tree each morning
(nothing here resets, cleans, stashes, checks out, rebases or removes a worktree --
`check_refresh_safe.py` scans these scripts too); it committed another session's mid-edit
file (a generation's worktree belongs to one agent, and on main only the paths the publish
step wrote are committed, under refresh_git's baseline and settle); it pushed to side
branches when main moved (publish replays onto main or stops and says why).

## The verdict, and what it means

| verdict | means |
|---|---|
| `yes` | a script could regenerate this report whenever its data updates: no judgement call, no document only a person can get, no question for anybody |
| `with-a-person` | it works, but somebody must decide or check something -- the reasons say what |
| `no` | the data does not exist, or the subject is not numbers |

The agent is told a wrong `yes` is worse than a cautious `with-a-person`.

## What would let a KIND of report run with nobody (the three-month question)

Not decided yet. These are the measurements to decide it from, all already recorded:

- **Machine pass rate**: share of trials whose `build.py` passes the page checks.
- **Verdict rate**: share of trials the agent called `yes`, and whether a person reading the
  draft agreed. The second half is not recorded yet and needs a field: a person's own verdict.
- **Questions per trial**: a kind that always needs an answer is not unattended.
- **Datasets used**: the same few datasets recurring is the sign of a kind that can be scripted.
- **Cost per trial**, against the per-run cap.
- **Whether `autogen_fit()` predicted the verdict.** If `candidate` and `yes` do not line up,
  the fit tests are wrong and get changed before anything runs unattended.

## Not built yet, on purpose

- Nothing publishes on its own. Publish is a person pressing the button.
- Nothing starts a generation on its own. Unattended runs wait for the evidence above.
