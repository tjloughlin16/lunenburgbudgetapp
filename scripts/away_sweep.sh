#!/bin/bash
# THE AWAY SWEEP. Launched by launchd at 02:00 on SUNDAY and MONDAY
# (ops/org.lunenburgbudgetproject.sweep-away.plist).
#
# WHY IT EXISTS SEPARATELY FROM weekly_sweep.sh. That one runs at 02:00 on Thursday and
# spends whatever the week has left, because the reset is five hours later and anything
# unused is gone. This one runs in the MIDDLE of the week, when there is a person coming
# back to the account, so it stops at a ceiling instead of at a refusal.
#
# TJ, 26 September 2026, going away: *"i want to burn a bunch of credits. i wont be around
# for the week, so we can use all the credits as fast as possible, leaving around 80%
# before tues morning"* -- asked which way he meant, he chose SPENDING about 80%. So the
# ceiling is the whole WEEK's scripted spend, counted from the Thursday 11:00 reset across
# every night, not a fresh 80% each time it runs.
#
# The Thursday sweep still runs after this and still has no ceiling, which is right: by
# then the allowance expires in hours and the only waste is not spending it.
set -u
TREE=/Users/tj/lunenburgbudgets-refresh
cd "$TREE" || exit 1
# THE SAME GATE AND THE SAME VERIFICATION as the weekly sweep, for the same reasons: a
# document held in one place is not backed up, and `reset --hard` below discards tracked
# work this tree may be holding from a run that died.
if ! python3 scripts/check_archive_backed_up.py --push --quiet; then
  echo "=== away sweep BLOCKED $(date): a document is held in only one place; nothing was reset ==="
  exit 1
fi
dirty="$(git status --porcelain --untracked-files=normal)"
if [ -n "$dirty" ]; then
  echo "=== away sweep STOPPED $(date): the tree is not pristine; nothing was reset ==="
  echo "$dirty"
  exit 1
fi
git fetch -q origin && git reset -q --hard origin/main
echo "=== away sweep started $(date) at $(git rev-parse --short HEAD) ==="
# --now because nobody is at the keyboard: the active-session check looks at whether a
# transcript under ~/.claude/projects changed recently, and an agent session that started
# this work would otherwise stop it.
python3 scripts/sweep_backlog.py --until 10:45 --parallel 4 --now --budget-pct 80
python3 scripts/build_agentic_backlog.py >/dev/null
git add -A sources/data/official-votes sources/data/recording-minutes sources/data/budget-state sources/data/agentic-spend.csv notes/generated/AGENTIC-BACKLOG.md 2>/dev/null
git commit -q -m "Away sweep, $(date +%Y-%m-%d): the backlog worked to the week's ceiling" && git push -q origin main
echo "=== away sweep finished $(date) ==="
