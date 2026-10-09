#!/bin/bash
# THE PACED MINUTES RUN, KEPT ALIVE. Started by launchd at login and every 30 minutes
# (~/Library/LaunchAgents/org.lunenburgbudgetproject.minutes-pacing.plist); launchd also
# runs a missed interval once when the machine wakes from sleep.
#
# TJ, 9 October 2026: "make it resilient to a reboot ... and sleeps". So this starts
# `process_meeting.py --until-usage --week-line 90` whenever it is not running -- after a
# reboot, a crash, or a long sleep -- and is a no-op otherwise. It does NOT restart a run
# that STOPPED on purpose: the run writes build/minutes-pacing.STOPPED with the reason (the
# ceiling, the output guard, the emergency brake, three failures), and that file, like the
# global kill switch build/STOP-METERED, keeps this out until a person removes it.
#
#   bash scripts/minutes_pacing.sh          # what launchd runs
#   touch build/STOP-METERED                # stop everything metered, now and on restart
cd "$(dirname "$0")/.." || exit 1
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:/usr/local/bin:/usr/bin:/bin"
PY=/usr/local/opt/python@3.11/bin/python3.11
LOG="build/process-meeting-week-$(date +%Y-%m-%d).log"
mkdir -p build
say() { echo "$(date '+%Y-%m-%d %H:%M:%S') minutes_pacing: $*" >> build/minutes-pacing.log; }

[ -e build/STOP-METERED ] && { say "kill switch present; not starting"; exit 0; }
if [ -e build/minutes-pacing.STOPPED ]; then
  say "last run stopped on purpose ($(head -1 build/minutes-pacing.STOPPED)); not starting"
  exit 0
fi
if pgrep -f "[p]rocess_meeting.py --until-usage" >/dev/null; then
  exit 0                                   # already running: the normal case, said nothing
fi
say "not running -- starting the paced run (log: $LOG)"
echo "=== WEEKLY PACED RUN, started by minutes_pacing.sh $(date)" >> "$LOG"
nohup "$PY" scripts/process_meeting.py --until-usage --week-line 90 --session-cap 80 --max-jobs 1 \
  >> "$LOG" 2>&1 < /dev/null &
