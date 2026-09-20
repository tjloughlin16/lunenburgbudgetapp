#!/usr/bin/env python3
"""When the nightly refresh fails, read the log, work out why, and try to fix it.

    python3 scripts/triage_refresh.py                 # today's log, if it failed
    python3 scripts/triage_refresh.py --log <path>    # a particular day
    python3 scripts/triage_refresh.py --dry-run       # print the prompt, spawn nothing

TJ, 20 September 2026, after the refresh had failed 8 of its last 10 runs in four
unrelated ways and nobody had noticed: "I want an agentic loop engaged. when the refresh
kicks off, it should spawn an agent to review when it fails, and attempt to fix it. Until
we get this thing fixed."

WHY A LOOP RATHER THAN MORE CHECKS. The four causes found on 20 September were a disk
filling from a Chrome profile leak, a fixed port colliding between worktrees, an
undeclared npm dependency, and a search-affinity row naming an alias. They have nothing
in common and no single check would have caught the next one. What they DO have in common
is that each was obvious from the log within a minute of somebody reading it -- and for
eight runs, nobody did.

--------------------------------------------------------------------------------------
WHAT IT MAY AND MAY NOT DO
--------------------------------------------------------------------------------------

The site went public on 19 September 2026. An agent that can push to main is an agent
that can break a live public budget tool at 07:00 while nobody is awake, so:

  - It works in the REFRESH TREE, on a branch of its own, never on main.
  - It may read anything, run the checks, and edit files.
  - It MUST NOT push to main, deploy, or touch the interactive tree.
  - It commits to `refresh-fix/<date>` and pushes THAT branch, so the work is visible
    and reviewable from anywhere, and merging stays a person's decision.

ONE ATTEMPT PER DAY. The report file is the lock: if it exists, the day is already
triaged. A loop that retries a failing fix every hour is how a plan's weekly allowance
disappears overnight.

--------------------------------------------------------------------------------------
WHAT IT COSTS
--------------------------------------------------------------------------------------

`claude -p` with tools, on a 60KB log, is a real run rather than a classifier: budget
roughly 0.2-0.5% of the week per triage, against ~0.09% for a minutes run. At one a day
that is under 4% of a week, and it only fires on a FAILURE -- so as the refresh gets
healthier it costs less, which is the right direction for an incentive to point.

Every run appends to sources/data/agentic-spend.csv under the stream `triage`, so the
dashboard counts it beside the reading jobs.
"""
import argparse
import csv
import datetime as dt
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGDIR = os.path.join(ROOT, 'build', 'refresh-logs')
OUTDIR = os.path.join(ROOT, 'build', 'refresh-triage')
SPEND = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')
MODEL = os.environ.get('TRIAGE_MODEL', 'sonnet')

# How much of the log the agent is handed directly. The whole file is often 60-120KB and
# most of it is routine progress; the failure and what led to it are what matter. The
# agent can open the file itself for the rest -- it has tools.
TAIL_LINES = 160


def read(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def failure(text):
    """The failing step and the exit code, or None if the run was clean.

    Read off the two lines daily_refresh.sh actually prints -- `step failed: <cmd>` and
    `refresh exit N` -- rather than by sniffing for the word 'error', which appears in
    plenty of healthy runs (a caption model mangling the word, a document titled with it).
    """
    step = re.findall(r'^step failed: (.+)$', text, re.M)
    code = re.findall(r'^refresh exit (\d+)$', text, re.M)
    if not step and not code:
        return None
    if code and code[-1] == '0':
        return None
    return dict(step=step[-1] if step else '(not named in the log)',
                exit=int(code[-1]) if code else None)


PROMPT = """The nightly refresh for the Lunenburg Budget Project failed this morning.

FAILING STEP: {step}
EXIT CODE: {code}
LOG: {log}

The last {n} lines of that log are below. The whole file is at the path above and you can
open it, along with anything else in the repository.

YOUR JOB, in order:

1. Work out the ROOT cause, not the first error message. These failures have repeatedly
   been one thing presenting as another -- a disk filling up presented as a sqlite error,
   then as a missing table the next day.
2. Fix it if the fix is clear and small. Run whatever check proves it.
3. If the fix is not clear or not small, do not guess: write down what you established,
   what you ruled out, and the one thing somebody would need to check next.

RULES, and the first is not negotiable:

- NEVER push to main, never deploy, never run `npm run build:site` unless you need it to
  reproduce the failure. This site is live to the public.
- Commit anything you change to the current branch only.
- CLAUDE.md is the contract for this repository. Rule 2 (never type a figure into prose),
  rule 13 (quote the source, not your rendering of it) and the note about generated files
  all apply to you.
- If the cause is environmental rather than a defect -- a full disk, a dead network, a
  port held by something else -- say so plainly and fix the environment if you safely can.
  Do not invent a code change to explain an environmental failure.

Finish with a short report: what failed, why, what you changed, and what you did not.

--- last {n} lines of the log ---
{tail}
"""


def build_prompt(logpath, fail):
    lines = read(logpath).splitlines()
    return PROMPT.format(step=fail['step'], code=fail['exit'], log=logpath,
                         n=TAIL_LINES, tail='\n'.join(lines[-TAIL_LINES:]))


def record(cost, result):
    new = not os.path.exists(SPEND)
    with open(SPEND, 'a', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['at', 'stream', 'board', 'date', 'cost_usd', 'result'])
        w.writerow([dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'triage', '', dt.date.today().isoformat(),
                    '%.4f' % cost if cost else '', result])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true',
                    help='triage again even if today already has a report')
    a = ap.parse_args()

    today = dt.date.today().isoformat()
    logpath = a.log or os.path.join(LOGDIR, today + '.log')
    if not os.path.exists(logpath):
        print('no log at %s -- nothing to triage' % logpath)
        return 0

    fail = failure(read(logpath))
    if not fail:
        print('refresh %s did not fail; nothing to triage' % os.path.basename(logpath))
        return 0

    os.makedirs(OUTDIR, exist_ok=True)
    report = os.path.join(OUTDIR, os.path.basename(logpath).replace('.log', '.md'))
    if os.path.exists(report) and not a.force:
        print('already triaged today: %s' % report)
        return 0

    prompt = build_prompt(logpath, fail)
    if a.dry_run:
        print(prompt)
        return 0

    print('triaging: %s (exit %s)' % (fail['step'], fail['exit']))
    cmd = ['claude', '-p', '--model', MODEL, '--permission-mode', 'acceptEdits', prompt]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout or '') + (('\n--- stderr ---\n' + r.stderr) if r.stderr else '')

    with open(report, 'w', encoding='utf-8') as fh:
        fh.write('# Refresh triage, %s\n\n' % today)
        fh.write('**Failing step:** `%s`  \n**Exit:** %s  \n**Log:** `%s`\n\n' %
                 (fail['step'], fail['exit'], logpath))
        fh.write('Written by `scripts/triage_refresh.py` with `claude -p` (%s). '
                 'It may edit and commit on this branch; it may not push to main or '
                 'deploy.\n\n---\n\n' % MODEL)
        fh.write(out)
    cost = 0.0
    m = re.search(r'\$([\d.]+)', out)
    if m:
        try: cost = float(m.group(1))
        except ValueError: pass
    record(cost, 'ok' if r.returncode == 0 else 'failed')
    print('wrote %s' % report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
