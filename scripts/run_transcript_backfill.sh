#!/bin/bash
# Fetch every meeting transcript, slowly, for as long as it takes.
#
# THE CONSTRAINT IS YOUTUBE'S PATIENCE, NOT OURS. The caption endpoint throttles by IP --
# ten fetches in 35 seconds earned a 429 from two different libraries -- and a throttle
# that is being hammered may last longer than one that is being waited out. So this does
# the opposite of retrying hard: it fetches slowly, stops the moment it is refused three
# times, sleeps for a long while, and tries again.
#
# It costs no money and no model tokens. Nothing depends on it finishing today.
#
#   nohup bash scripts/run_transcript_backfill.sh > /tmp/transcripts.log 2>&1 &
set -u
cd "$(dirname "$0")/.."

BOARDS="school-committee select-board finance-committee"
BATCH=25          # per attempt, then a long pause regardless
SLEEP=45          # between individual fetches
COOLDOWN=1800     # 30 min after a throttled batch
BETWEEN=300       # 5 min after a clean batch

while true; do
  progressed=0
  for b in $BOARDS; do
    left=$(python3 scripts/fetch_youtube_transcripts.py --board "$b" --status 2>/dev/null \
           | awk '/video\(s\) in scope/ {print $(NF-1)}')
    [ -z "${left:-}" ] && left=0
    if [ "$left" -eq 0 ]; then
      echo "$(date -u +%H:%M:%S)  $b complete"
      continue
    fi
    echo "$(date -u +%H:%M:%S)  $b — $left remaining, taking $BATCH"
    if python3 scripts/fetch_youtube_transcripts.py --board "$b" \
         --limit "$BATCH" --sleep "$SLEEP" 2>&1 | tail -20 | grep -q "fetched"; then
      progressed=1
    fi
    # Did that batch actually land anything? A batch that fetched nothing means the
    # throttle is on, and the right response is to go away for a while.
    if python3 scripts/fetch_youtube_transcripts.py --board "$b" --status 2>/dev/null \
         | grep -q "0 fetched"; then
      echo "$(date -u +%H:%M:%S)  throttled — sleeping ${COOLDOWN}s"
      sleep "$COOLDOWN"
    else
      sleep "$BETWEEN"
    fi
  done
  remaining=$(python3 scripts/fetch_youtube_transcripts.py --status 2>/dev/null \
              | awk '/video\(s\) in scope/ {print $(NF-1)}')
  if [ "${remaining:-1}" = "0" ]; then
    echo "$(date -u +%H:%M:%S)  ALL BOARDS COMPLETE"; break
  fi
  [ "$progressed" -eq 0 ] && { echo "no progress this cycle; long sleep"; sleep "$COOLDOWN"; }
done
