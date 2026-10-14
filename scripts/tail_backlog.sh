#!/bin/bash
# FOLLOW THE MINUTES RUN -- whichever one is running -- from any directory, with no
# arguments, and never quit on its own.
#
#     bash scripts/tail_backlog.sh
#
# TJ, 14 October 2026: "i dont want to have to know which log to tail.. i want to run a
# script that always finds the relevant one automatically with no configuration."
#
# So it does not guess a name. A run started by hand writes process-meeting-<day>.log, the
# launchd run (minutes_pacing.sh) writes process-meeting-week-<day>.log, and a one-off may be
# named anything that starts process-meeting. This follows whichever build/process-meeting*.log
# was WRITTEN TO MOST RECENTLY, and re-checks every 20 seconds -- so it moves on its own when
# a new run starts, when a run crosses midnight into a new day's file, or when the name changes.
# (The first version picked a file once and sat on yesterday's; the second followed one name
# while the real run wrote the other.)
#
# Shows meeting lines, writes, failures, stops, and the [gov] / [watch] pacing lines.
# Run it in its OWN Terminal window: inside Claude Code's `!` it is killed at the timeout.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILTER="^\[|wrote|reconciled|FAILED|STOPPED|done|completed|^==="
newest() { ls -t "$ROOT"/build/process-meeting*.log 2>/dev/null | head -1; }
cur=""; pid=""
while true; do
  f=$(newest)
  if [ -n "$f" ] && [ "$f" != "$cur" ]; then
    [ -n "$pid" ] && { pkill -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null; }
    cur="$f"
    echo "--- following ${cur#$ROOT/} (the most recently written minutes-run log) ---"
    tail -n 40 -F "$cur" 2>/dev/null | grep --line-buffered -E "$FILTER" &
    pid=$!
  elif [ -z "$f" ] && [ -z "$cur" ]; then
    echo "--- no minutes-run log in build/ yet; waiting ---"; cur="(none)"
  fi
  sleep 20
done
