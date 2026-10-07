#!/bin/bash
# FOLLOW THE BACKLOG RUN, filtered, from any directory, and never quit on its own.
#
#     bash scripts/tail_backlog.sh
#
# `tail -F` (capital) follows the file by NAME and waits for it to appear, so a run that has
# not started yet, or tomorrow's log, does not end it. The path is absolute, so a relative
# glob that matches nothing from the wrong directory -- zsh: "no matches found" -- cannot
# end it either. Shows meeting lines, writes, failures, stops, and the [watch] pace lines.
# Run it in its OWN Terminal window: inside Claude Code's `!` it is killed at the command
# timeout.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec tail -n 40 -F "$ROOT/build/process-meeting-$(date +%Y-%m-%d).log" \
  | grep --line-buffered -E "^\[|wrote|FAILED|STOPPED|done|completed"
