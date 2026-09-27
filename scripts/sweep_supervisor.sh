#!/bin/bash
# KEEP THE BACKLOG STREAMS PRODUCING, unattended. Runs every 30 minutes from launchd
# (ops/org.lunenburgbudgetproject.sweep-supervisor.plist).
#
# WHAT IT IS FOR, and the night that caused it. 26 September 2026: the sweep hit the
# rolling five-hour session limit at about 23:00 and went into exponential backoff, the
# votes backfill died, and BOTH PROCESSES STAYED ALIVE AND IDLE FOR EIGHT HOURS. The next
# scheduled run was 02:00, it inherited the same limit, and by morning the night had cost
# nothing and produced nothing. Nobody was there, and nothing was watching OUTPUT.
#
# So: liveness is not health. `pgrep` says a stalled sweep is running, because it is.
# sweep_health.py measures the only thing that matters -- whether anything has been
# WRITTEN -- and this acts on it:
#
#   producing            -> leave it alone
#   stalled but alive    -> kill it; an interrupted job is safe, both streams skip work
#                           that is already done, so a restart repeats nothing
#   not running at all   -> start it
#
# THE RESTART IS THE POINT. The five-hour window reopens on its own; what was missing was
# anything to notice and pick the work back up. Half an hour of idleness is the cost of
# being wrong about a slow job; eight hours was the cost of having no supervisor.
set -u
cd /Users/tj/lunenburgbudgets || exit 1
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:$PATH"
STALE=45
log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*"; }

alive() { pgrep -f "[s]weep_backlog.py" >/dev/null; }
votes_alive() { pgrep -f "[r]un_official_votes_backfill" >/dev/null; }

if python3 scripts/sweep_health.py --stale-minutes "$STALE" >/dev/null 2>&1; then
  log "producing; nothing to do"
  python3 scripts/sweep_health.py --stale-minutes "$STALE"
  exit 0
fi

log "NOTHING WRITTEN IN ${STALE} MINUTES — restarting the streams"
python3 scripts/sweep_health.py --stale-minutes "$STALE"
if alive; then log "killing a stalled sweep"; pkill -f "[s]weep_backlog.py"; fi
if votes_alive; then log "killing a stalled votes backfill"; pkill -f "[r]un_official_votes_backfill"; pkill -f "[e]xtract_official_votes.py"; fi
sleep 5

# THE WORK RUNS IN THE FOREGROUND, AND THAT IS THE WHOLE FIX.
#
# The first version launched `nohup ... &` and exited. launchd REAPS THE JOB'S ENTIRE
# PROCESS GROUP when the script returns, so both children died instantly every time --
# the supervisor logged `restarted` on the half hour for hours while both logs stayed
# zero bytes and the counters did not move. A restart that cannot outlive its own
# supervisor is worse than no supervisor: it reports success.
#
# So the sweep runs here, in front, for a window SHORTER than the launchd interval that
# starts this script. launchd will not run a second copy while this one is alive, and
# when the window closes this exits and the next firing starts a fresh one. That makes
# self-healing structural rather than something to remember: every half hour is a new
# sweep whatever happened to the last.
WINDOW_MIN=25
UNTIL="$(date -v+${WINDOW_MIN}M '+%H:%M' 2>/dev/null || date -d "+${WINDOW_MIN} minutes" '+%H:%M')"
log "running a ${WINDOW_MIN}-minute sweep, until $UNTIL"

# The votes backfill is a long loop of its own; it runs as a child of THIS script so it
# lives exactly as long as the window and dies with it. Both streams skip work already
# done, so being cut mid-window repeats nothing.
bash scripts/run_official_votes_backfill.sh >> /tmp/official-votes-supervised.log 2>&1 &
VOTES=$!
python3 scripts/sweep_backlog.py --until "$UNTIL" --now --parallel 3 \
  >> /tmp/sweep-supervised.log 2>&1
log "sweep window closed"
kill "$VOTES" 2>/dev/null
pkill -P "$VOTES" 2>/dev/null
wait "$VOTES" 2>/dev/null
python3 scripts/sweep_health.py --stale-minutes "$STALE" || true
