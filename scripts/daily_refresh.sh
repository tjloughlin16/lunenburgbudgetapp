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
# The sticky banner for a run that refused to start, written before the hand-off because
# the gate that can refuse runs before the tree is touched at all.
ALERT_EARLY="$HERE/build/refresh-ALERT.txt"

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
    # ------------------------------------------------------------------ THE GATE
    # NOTHING BELOW THIS LINE RUNS WHILE A DOCUMENT IS HELD IN ONE PLACE.
    #
    # TJ, 25 September 2026: *"i want to make sure any file we downoad is ALWAYS saved
    # before we can even think of deleting it or cleaning a repo..."*
    #
    # `git reset --hard` and `git clean` are below, and a previous run may have died after
    # fetching and before pushing -- which is not hypothetical: six agendas were sitting in
    # exactly that state when this was written. So the tree is asked, offline and in under a
    # second, whether every publisher document it holds is in the bucket and was read back.
    # If it is not, this run backs them up and asks again; if it still is not, the run STOPS
    # having changed nothing, and says so where a person will see it.
    if ! python3 scripts/check_archive_backed_up.py --push --quiet; then
      {
        echo "$(date '+%Y-%m-%d %H:%M')  refresh BLOCKED before it touched anything"
        echo "a document is held in only one place and could not be backed up."
        echo "run: python3 scripts/check_archive_backed_up.py"
        echo "log: $LOG"
      } > "$ALERT_EARLY"
      osascript -e 'display notification "a document is held in one place -- nothing was cleaned" with title "Lunenburg refresh BLOCKED" sound name "Basso"' >/dev/null 2>&1 || true
      echo "BLOCKED: unbacked document(s); refusing to reset or clean this tree"
      exit 1
    fi
    git fetch -q origin
    # Anything left in the tree from a run that died is discarded: the tree's whole
    # contract is that it starts every run at main. Gitignored state (the archive's
    # binaries, the database, node_modules) is untouched by a reset.
    git reset -q --hard origin/main
    # `git clean` NEVER REACHES sources/. TJ, 25 September 2026: *"if you have ANY thought
    # that refresh destroys things, we need to make that a guarantee to never even be
    # possible."*
    #
    # THIS LINE COULD DELETE FRESHLY FETCHED DOCUMENTS, and the comment it replaces said it
    # could not. The reasoning was that documents are gitignored and `-fd` skips ignored
    # files -- true for every extension .gitignore names (*.pdf, *.xlsx, *.docx, *.html).
    # It is NOT true for `.csv`, which is tracked-by-default under sources/ so the data
    # files can be versioned. A fetched CSV is therefore untracked AND not ignored, which
    # is precisely what `git clean -fd` removes. Asked directly -- `git clean -nd sources/`
    # -- git offered to delete six of the seven staff-directory sheets ingested that day.
    #
    # It only bites a run that dies between fetching and committing, which is not rare:
    # runs died on 16, 17 and 18 September, and one was killed on the 25th.
    #
    # An exclusion, not a narrower path list: a path list has to be kept in step with what
    # the build writes, and the whole point here is a guarantee that cannot rot.
    git clean -q -fd -e '/sources/'   # untracked build state only -- NEVER the archive
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
  # COMMIT WHAT THE RUN PRODUCED, NOT A HAND-LISTED SUBSET OF IT.
  #
  # This was a whitelist of data paths, and it had drifted behind what the refresh
  # actually regenerates -- the defect shape CLAUDE.md names first: a list was written
  # down, the thing it listed moved, and nothing connected the two. Eight paths were
  # being regenerated every run and committed by none of them, including
  # `sources/data/official-votes/`, which is the OUTPUT OF THE MOST EXPENSIVE THING THIS
  # PROJECT DOES. Forty extracted votes were sitting untracked on 21 September -- about
  # 1.2% of a week of plan allowance -- with `git clean -fd` at the top of the next run
  # waiting to delete them. Work was being bought and thrown away on a daily cycle.
  #
  # It also broke the push, which is what made it visible. Files left dirty by the run
  # meant `git pull --rebase` refused with "cannot pull with rebase: You have unstaged
  # changes" the moment main had moved, and the failure message blamed main moving. Three
  # triage sessions chased that.
  #
  # `-A` IS SAFE HERE FOR A REASON THAT IS LOAD-BEARING AND NOT OBVIOUS: this tree is
  # `git reset --hard origin/main` at the top of every run, so everything dirty at this
  # point was produced by this run. And this block runs BEFORE the triage agent is
  # spawned, so nothing an agent wrote can be swept into a push to main. If either of
  # those ever stops being true, this line stops being safe -- say so before moving it.
  git add -A
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
    # KEEP WHAT IT WROTE. The top of every run is `git reset --hard origin/main`, so a fix
    # the agent leaves in the working tree is destroyed the next morning -- and it then
    # rewrites the same patch, having no memory of the last one. That happened three times
    # running on 20-21 September: three sessions, three identical diagnoses of the same
    # Chrome failure, three copies of the same retry fix, none surviving to be reviewed.
    #
    # So its changes are committed onto a dated branch of their own. Not `refresh` (reset
    # moves that pointer) and never main: these are unreviewed edits written unattended at
    # 07:00, and the site is public. A branch is durable, reviewable, and costs nothing.
    if ! git diff --quiet || [ -n "$(git status --porcelain)" ]; then
      b="triage/$(date +%Y-%m-%d-%H%M)"
      git add -A
      git commit -q -m "Refresh triage, $(date +%Y-%m-%d): what the agent changed

Written unattended by scripts/triage_refresh.py. NOT reviewed and NOT on main.
Review with: git diff origin/main..$b" && git branch -f "$b" HEAD \
        && git reset -q --hard HEAD~1 \
        && echo "triage changes kept on branch $b — review with: git diff origin/main..$b"
    fi
  fi
  echo "=== finished $(date) ==="
} >> "$LOG" 2>&1
