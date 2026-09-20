#!/bin/bash
# The daily run, as launchd calls it -- see ops/README.md. Everything the refresh needs on
# PATH, a log per day, the state files committed afterwards and pushed to main, and the
# site deployed. Nothing here posts to Facebook; the paste-ready texts land in
# build/notices-to-post.md.
#
#   bash scripts/daily_refresh.sh          # by hand
#
# IT RUNS IN ITS OWN CHECKOUT. The refresh tree (scripts/setup_refresh_tree.sh) is a git
# worktree on a branch called `refresh`, reset to origin/main before every run and pushed
# back to main after. That is what makes "deploy as soon as it is done, safely" true:
# whatever branch a person or an agent has checked out in the interactive tree, the
# refresh builds main and deploys main. On 15 September 2026 it built a feature branch
# instead, and Cloudflare Pages put that deploy on a preview alias with production none
# the wiser -- see setup_refresh_tree.sh for the whole story.
#
# THE INTERACTIVE TREE IS NOT TOUCHED. This script, when launched from there (launchd
# points at this path), only hands off to the copy of itself inside the refresh tree,
# after bringing that tree up to origin/main -- so the refresh always runs the code that
# is on main, not whatever is half-edited here.
set -u
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:/usr/local/bin:/usr/bin:/bin"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TREE="${REFRESH_TREE:-$(cd "$HERE/.." && pwd)/lunenburgbudgets-refresh}"
LOGDIR="$HERE/build/refresh-logs"
mkdir -p "$LOGDIR"
# One log per day, in the interactive tree where a person looks for it, whichever tree
# is running -- the hand-off passes the path down.
LOG="${REFRESH_LOG:-$LOGDIR/$(date +%Y-%m-%d).log}"
export REFRESH_LOG="$LOG"

# ---------------------------------------------------------------- hand-off
if [ "$HERE" != "$(cd "$TREE" 2>/dev/null && pwd)" ]; then
  if [ ! -e "$TREE/.git" ]; then
    echo "$(date): no refresh tree at $TREE -- run: bash scripts/setup_refresh_tree.sh" >> "$LOG"
    exit 1
  fi
  # ONCE A DAY, WHENEVER THE MACHINE IS ON. launchd fires this at 7:00 and again at every
  # login/boot (RunAtLoad); the guard makes the second firing a no-op on a day that ran.
  if grep -q "=== finished" "$LOG" 2>/dev/null; then
    echo "already ran today ($(date)); nothing to do" >> "$LOG"
    exit 0
  fi
  {
    echo "=== bringing the refresh tree to origin/main $(date) ==="
    cd "$TREE" || exit 1
    git fetch -q origin
    # Anything left in the tree from a run that died is discarded: the tree's whole
    # contract is that it starts every run at main. Gitignored state (the archive's
    # binaries, the database, node_modules) is untouched by a reset.
    git reset -q --hard origin/main
    git clean -q -fd   # untracked files only; ignored state (binaries, .db, node_modules) stays
  } >> "$LOG" 2>&1
  exec bash "$TREE/scripts/daily_refresh.sh"
fi

# ---------------------------------------------------------------- the run, inside the tree
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
    rm -f "$ALERT"
  fi
  # Commit the observation logs, previews, minutes and payloads. A refresh that is not
  # committed is a refresh the next machine cannot see.
  git add sources/data/meeting-watch-*.csv sources/data/youtube-watch-events.csv \
          sources/data/youtube-videos.csv sources/data/youtube-video-boards.csv \
          sources/data/youtube-video-classification.csv sources/data/youtube-transcript-index.csv \
          sources/data/youtube-no-captions.csv sources/data/minutes-searchable.csv \
          sources/data/refresh-runs.csv sources/data/recording-minutes sources/data/agenda-previews \
          sources/data/search-affinity.csv sources/data/budget-state \
          sources/meetings/index.csv sources/meetings/text fy28/public/data fy28/public/docs/data \
          fy28/public/sitemap.xml fy28/public/version.json fy28/src/data/sources.json \
          notes/generated/APP-METRICS.md 2>/dev/null
  if ! git diff --cached --quiet; then
    git commit -q -m "Daily refresh, $(date +%Y-%m-%d)

$(tail -1 sources/data/refresh-runs.csv)

Automated by scripts/daily_refresh.sh."
    # Push to main. If main moved while this ran (somebody merged), rebase the one
    # refresh commit onto it and try once more; the refresh only touches data paths,
    # so a real conflict means a person changed the same data file today.
    if git push -q origin HEAD:main; then
      echo "committed and pushed to main"
    elif git pull -q --rebase origin main && git push -q origin HEAD:main; then
      echo "committed, rebased onto a moved main, and pushed"
    else
      echo "PUSH FAILED: main moved and the rebase did not resolve; the refresh commit is on branch 'refresh' in $HERE"
    fi
  else
    echo "nothing to commit"
  fi
  # ------------------------------------------------------------- triage on failure
  # THE LOOP. TJ, 20 September 2026: "when the refresh kicks off, it should spawn an agent
  # to review when it fails, and attempt to fix it. Until we get this thing fixed."
  #
  # The refresh had failed 8 of its last 10 runs, in four unrelated ways, and none of them
  # was hard to see in the log -- nobody was reading it. So on a failure, and only on a
  # failure, hand the log to an agent that can read the repository and try.
  #
  # It works on THIS branch in the refresh tree and is forbidden from pushing to main or
  # deploying: the site is public, and 07:00 is a bad time to break it unattended. The
  # report lands in build/refresh-triage/<date>.md and is the once-a-day lock.
  #
  # `|| true` deliberately: a triage that itself fails must not change the refresh's own
  # exit code, which is what the dashboard and the run registry read.
  if grep -q "^refresh exit [1-9]" "$LOG" 2>/dev/null; then
    echo "--- refresh failed; spawning triage agent ---"
    python3 "$HERE/scripts/triage_refresh.py" --log "$LOG" || true
  fi
  echo "=== finished $(date) ==="
} >> "$LOG" 2>&1
