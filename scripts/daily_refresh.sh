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
  # ONCE A DAY, WHENEVER THE MACHINE IS ON. launchd fires this at 9:00 and again at every
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
{
  echo "=== daily refresh started $(date) in $HERE on $(git rev-parse --abbrev-ref HEAD) at $(git rev-parse --short HEAD) ==="
  python3 scripts/refresh.py --deploy
  echo "refresh exit $?"
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
  echo "=== finished $(date) ==="
} >> "$LOG" 2>&1
