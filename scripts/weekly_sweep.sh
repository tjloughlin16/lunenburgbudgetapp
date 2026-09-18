#!/bin/bash
# THE WEDNESDAY SWEEP. Launched by launchd at 18:00 on Wednesdays (ops/org.lunenburgbudgetproject.sweep.plist);
# spends whatever the week has left on the backlog and stops at 22:55, five minutes
# before the plan's weekly reset at 22:59 America/New_York. Runs in the refresh worktree
# so it never touches a session's working tree, and commits what it read.
set -u
TREE=/Users/tj/lunenburgbudgets-refresh
cd "$TREE" || exit 1
git fetch -q origin && git reset -q --hard origin/main
echo "=== weekly sweep started $(date) at $(git rev-parse --short HEAD) ==="
python3 scripts/sweep_backlog.py --until 22:55 --parallel 4
python3 scripts/build_agentic_backlog.py >/dev/null
git add -A sources/data/official-votes sources/data/recording-minutes sources/data/budget-state sources/data/agentic-spend.csv notes/generated/AGENTIC-BACKLOG.md 2>/dev/null
git commit -q -m "Weekly sweep, $(date +%Y-%m-%d): the backlog worked until the reset" && git push -q origin main
echo "=== weekly sweep finished $(date) ==="
