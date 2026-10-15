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
4. **An agent drafts it** (`scripts/generate_report.py`): sonnet, capped per run, fenced to
   `notes/report-generations/<slug>/`, its generator run only inside a sandbox with no network
   and no writes elsewhere. It must produce `DRAFT.md`, and `build.py`, a generator that
   writes a topic payload through `scripts/topic.py` (`TP.page(..., draft=...)`).
5. **We check it by machine.** The runner runs `build.py` itself. Pass means the page met the
   same rule-2, length, chart and source checks as every published page.
6. **It reports back** in `generation.json`: status, summary, the auto-generation verdict and
   its reasons, datasets used, figures with their sources, open questions, gaps, next steps.
   Open questions are answered on the dashboard; the same session resumes with the answer.

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

- Nothing publishes a draft. A passing `payload.json` is a page in shape, not a page on the
  site: registering it in `scripts/topic_registry/` stays a person's decision.
- Nothing starts a generation on its own. Unattended runs wait for the evidence above.
