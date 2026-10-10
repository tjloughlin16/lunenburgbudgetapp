#!/bin/bash
# The daily run, as launchd calls it -- see ops/README.md. Everything the refresh needs on
# PATH, a log per day, and refresh.py --deploy, which commits ONLY what it wrote, replays
# it onto main and deploys main. Nothing here posts to Facebook; the paste-ready texts land
# in build/notices-to-post.md.
#
#   bash scripts/daily_refresh.sh          # by hand
#
# IT RUNS IN THE TREE IT LIVES IN, ON WHATEVER BRANCH IS CHECKED OUT. TJ, 8 October 2026:
# *"refresh should work in whatever branch we're currently on. needing to check out a new
# branch is silly. we did that for good reason before, but its only hurt us"* -- and
# *"this shouldnt have ANY chance of a destructive path"*.
#
# THIS USED TO HAND OFF TO A SECOND CHECKOUT, ~/lunenburgbudgets-refresh, which it reset to
# origin/main every morning, refusing to start unless that checkout was pristine; then it
# committed with `add -A` and, when main had moved, pushed to a side branch. Each part had
# a reason (15 September 2026: a refresh built a feature branch and Cloudflare put it on a
# preview alias), and together they meant the refresh almost never finished: blocked 5, 6
# and 7 October because that checkout sat on a 22 September commit, split across a side
# branch on the 8th. notes/HANDOFF-REFRESH-ADDITIVE.md has the whole account.
#
# WHAT REPLACED EACH PART, so none of the old protections was simply dropped:
#   * a feature branch reaching production -> refresh.py deploys only when the branch is
#     main AND its commit is origin/main's, and names `--branch main` to wrangler;
#   * `add -A` sweeping in other work      -> refresh_git.py commits only the paths the run
#     changed, and puts back anything of somebody else's it overwrote;
#   * a moved main                          -> replayed onto with merge-tree, bounded
#     retries, never a side branch, never a force;
#   * the reset that made `add -A` safe     -> nothing is reset, cleaned or deleted at all,
#     and scripts/check_refresh_safe.py fails the build if this file or refresh.py ever
#     contains a command that could.
set -u
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:/usr/local/bin:/usr/bin:/bin"
# ONCE STARTED, STAY AWAKE UNTIL DONE. On 10 October 2026 a job launched at 02:36 during a
# dark wake went back to sleep 18 seconds later and then ran ~45 seconds an hour, so a
# 14-minute search build read as "5.5 hours, too slow". This holds an idle-sleep assertion
# for exactly as long as this shell lives. It cannot WAKE the machine at 07:00 -- launchd
# runs a missed time on the next wake -- and a closed lid on battery still sleeps.
/usr/bin/caffeinate -i -w $$ &
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE" || exit 1
LOGDIR="$HERE/build/refresh-logs"
mkdir -p "$LOGDIR"
LOG="${REFRESH_LOG:-$LOGDIR/$(date +%Y-%m-%d).log}"
export REFRESH_LOG="$LOG"

# ONCE A DAY, WHENEVER THE MACHINE IS ON. launchd fires this at 7:00 and again at every
# login/boot (RunAtLoad); the guard makes the second firing a no-op on a day that ran.
#
# A FAILED RUN HAS NOT RUN. A run that dies still prints `=== finished`, so this guard used
# to treat the 9 October failure (exit 1 at 07:00:03, nothing fetched) as the day's run,
# and every later firing -- at login, or by hand once the cause was fixed -- did nothing.
# The day is done only when the LAST `refresh exit` it logged is 0.
if grep -q "=== finished" "$LOG" 2>/dev/null \
   && [ "$(grep '^refresh exit ' "$LOG" | tail -1)" = "refresh exit 0" ]; then
  echo "already ran today ($(date)); nothing to do" >> "$LOG"
  exit 0
fi

# ---------------------------------------------------------------- telling somebody
# A FAILURE THAT NOBODY IS TOLD ABOUT IS AN OUTAGE. This ran and failed on 16, 17 and 18
# September 2026 -- build_search_index.py, `database or disk is full` -- and nothing said
# so. Three things hid it at once, and each is fixed here or in the status page:
#
#   * refresh.py writes its row in refresh-runs.csv at the END, so a run that dies leaves
#     no row, and no row reads as a quiet day rather than a failure;
#   * launchd swallows the exit code -- no mail, no badge, nothing;
#   * the refresh is ADDITIVE, so failing looks exactly like a week the town posted
#     nothing. No page breaks. No figure goes wrong.
#
# TJ, 19 September 2026: "i need to be notified somehow when the refresh fails."
#
# So: a macOS notification with a sound, and a sticky file the status page reads, because
# a notification is gone the moment it is dismissed and the machine may be asleep at 7am.
# The file is the durable half and the banner stays until the next run succeeds.
ALERT="$HERE/build/refresh-ALERT.txt"
notify() {   # notify <title> <message>
  osascript -e "display notification \"$2\" with title \"$1\" sound name \"Basso\"" \
    >/dev/null 2>&1 || true
}

{
  echo "=== daily refresh started $(date) in $HERE on $(git rev-parse --abbrev-ref HEAD) at $(git rev-parse --short HEAD) ==="
  # BACK UP ANYTHING HELD IN ONE PLACE, AND SAY SO IF IT CANNOT BE. This was THE GATE --
  # nothing ran while a document existed on one disk, because a `reset --hard` followed.
  # Nothing destructive follows any more, so it no longer stops the run; it still pushes
  # what is unbacked, because a disk can fail whether or not we delete anything, and a
  # failure still reaches the banner.
  if ! python3 scripts/check_archive_backed_up.py --push --quiet; then
    echo "WARNING: a document is held in only one place and could not be backed up;"
    echo "  run: python3 scripts/check_archive_backed_up.py"
    notify "Lunenburg refresh" "a document is held in one place and could not be backed up"
  fi
  python3 scripts/refresh.py --deploy
  rc=$?
  echo "refresh exit $rc"
  if [ "$rc" -ne 0 ]; then
    # The step that broke, named, so the notification is actionable rather than a shrug.
    broke=$(grep -o 'step failed:.*' "$LOG" | tail -1 | grep -oE '[a-z_]+\.py' | tail -1)
    why=$(grep -E 'Error|error:|full|refused|denied' "$LOG" | tail -1 | cut -c1-160)
    {
      echo "$(date '+%Y-%m-%d %H:%M')  the daily refresh FAILED (exit $rc)"
      echo "broke on: ${broke:-unknown step}"
      echo "$why"
      echo "log: $LOG"
    } > "$ALERT"
    notify "Lunenburg refresh FAILED" "${broke:-a step} — nothing new was ingested today"
  else
    # A success clears the banner: an alert that outlives its cause trains you to ignore it.
    # (Under build/, which is ours -- the one place check_refresh_safe.py allows a delete.)
    rm -f "$ALERT"
  fi
  # ------------------------------------------------------------- triage on failure
  # THE LOOP. TJ, 20 September 2026: "when the refresh kicks off, it should spawn an agent
  # to review when it fails, and attempt to fix it. Until we get this thing fixed."
  #
  # The refresh had failed 8 of its last 10 runs, in four unrelated ways, and none of them
  # was hard to see in the log -- nobody was reading it. So on a failure, and only on a
  # failure, hand the log to an agent that can read the repository and try.
  #
  # IT WORKS IN A TREE OF ITS OWN, NOT THIS ONE. This tree is a person's now, and an agent
  # editing it unattended at 07:00 would leave its patch mixed into their uncommitted work.
  # triage_refresh.py adds a DETACHED worktree under build/refresh-triage/ at this commit
  # and the agent edits there: no branch is created, nothing is committed or pushed, and
  # the edits stay where they were made for a person to review -- the old version committed
  # them to a `triage/` branch only because its tree was reset every morning, which is
  # gone. The report lands in build/refresh-triage/<date>.md and is the once-a-day lock.
  #
  # `|| true` deliberately: a triage that itself fails must not change the refresh's own
  # exit code, which is what the dashboard and the run registry read.
  if grep -q "^refresh exit [1-9]" "$LOG" 2>/dev/null; then
    echo "--- refresh failed; spawning triage agent ---"
    python3 "$HERE/scripts/triage_refresh.py" --log "$LOG" --own-tree || true
  fi
  echo "=== finished $(date) ==="
} >> "$LOG" 2>&1
