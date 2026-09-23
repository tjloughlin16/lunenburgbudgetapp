#!/bin/bash
# THE OVERNIGHT SWEEP. Launched by launchd at 02:00 on THURSDAYS
# (ops/org.lunenburgbudgetproject.sweep.plist); spends whatever the week has left on the
# backlog and stops at 10:55, five minutes before the plan's weekly reset. Runs in the
# refresh worktree so it never touches a session's working tree, and commits what it read.
#
# THE RESET IS THURSDAY AT 11:00, AND THIS FILE SAID 22:59 ON WEDNESDAY. It was scheduled
# Wednesday 18:00 and quit at 22:55 to land five minutes before a reset that happens
# twelve hours later -- so every week it handed back most of its own window, which is the
# opposite of what a sweep is for. TJ, 23 September 2026: *"reset is TOMORROW at 11, the
# 24th."*
#
# The precision was the tell. `22:55`, `five minutes before`, a named timezone: exact
# about a time nobody had checked. A figure typed into a comment is the same defect as a
# figure typed into prose -- rule 2 -- and a schedule is prose that runs.
#
# Overnight rather than Wednesday evening for a second reason: it puts four concurrent
# model processes on the machine, and at 02:00 nothing else is competing for it.
set -u
TREE=/Users/tj/lunenburgbudgets-refresh
cd "$TREE" || exit 1
git fetch -q origin && git reset -q --hard origin/main
echo "=== weekly sweep started $(date) at $(git rev-parse --short HEAD) ==="
python3 scripts/sweep_backlog.py --until 10:55 --parallel 4
python3 scripts/build_agentic_backlog.py >/dev/null
git add -A sources/data/official-votes sources/data/recording-minutes sources/data/budget-state sources/data/agentic-spend.csv notes/generated/AGENTIC-BACKLOG.md 2>/dev/null
git commit -q -m "Weekly sweep, $(date +%Y-%m-%d): the backlog worked until the reset" && git push -q origin main
echo "=== weekly sweep finished $(date) ==="
