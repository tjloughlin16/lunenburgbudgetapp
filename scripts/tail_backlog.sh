#!/bin/bash
# FOLLOW THE BACKLOG RUN, filtered, from any directory, and never quit on its own.
#
#     bash scripts/tail_backlog.sh
#
# `tail -F` (capital) follows the file by NAME and waits for it to appear. The path is
# absolute, so a relative glob that matches nothing from the wrong directory cannot end it.
# Shows meeting lines, writes, failures, stops, and the [gov] / [watch] lines.
#
# AND IT CROSSES MIDNIGHT. The log is named by date, and a run that goes past midnight writes
# to the NEW day's file; the first version picked the file once at start and sat on
# yesterday's (8 October 2026: "i dont see any meeting logs"). So it re-checks the date every
# minute and moves to the new file, showing its last lines.
# Run it in its OWN Terminal window: inside Claude Code's `!` it is killed at the timeout.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILTER="^\[|wrote|reconciled|FAILED|STOPPED|done|completed"
while true; do
  day=$(date +%Y-%m-%d)
  echo "--- following build/process-meeting-$day.log ---"
  tail -n 40 -F "$ROOT/build/process-meeting-$day.log" 2>/dev/null | grep --line-buffered -E "$FILTER" &
  pid=$!
  while [ "$(date +%Y-%m-%d)" = "$day" ]; do sleep 60; done
  pkill -P $pid 2>/dev/null; kill $pid 2>/dev/null
done
