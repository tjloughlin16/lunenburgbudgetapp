#!/bin/bash
# ONE-TIME: give the daily refresh a checkout of its own.
#
#   bash scripts/setup_refresh_tree.sh
#
# WHY. On 15 September 2026 the refresh ran in the interactive working tree while a
# feature branch was checked out, committed a day's minutes onto that branch, and
# "deployed" -- to a Cloudflare Pages preview alias, because the branch was not `main`.
# Production missed a day and nobody could tell from the run log, which said deployed=yes.
# The next morning it stopped at a stale key a branch had left behind. TJ: "Refresh
# mechanism has to be able to deploy as soon as its done refreshing, safely ... all of our
# other work has to be safely done outside that so it doesnt interfere with the refresh."
#
# So the refresh gets its own git worktree, always on a branch called `refresh` that is
# reset to origin/main before every run and pushed back to main after. Nobody edits in
# it. The interactive tree (this one) is where people and agents work, on branches, and
# main is the only thing the two share.
#
# WHAT A FRESH CHECKOUT LACKS, and this script supplies:
#   - fy28/node_modules            symlinked to this tree's (one install, two trees)
#   - the archive's binaries       git holds the manifests; the PDFs are in R2. Without
#                                  them `fetch_agendas.py --backfill` would try to fetch
#                                  twelve thousand documents from the town's site.
#   - sources/data/lunenburg.db    derived, gitignored; build_app_metrics reads it
set -eu
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TREE="${REFRESH_TREE:-$HERE/../lunenburgbudgets-refresh}"
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:/usr/local/bin:/usr/bin:/bin"

if [ -e "$TREE/.git" ]; then
  echo "refresh tree already exists at $TREE"; exit 0
fi
cd "$HERE"
git fetch -q origin
# A branch of its own, because git will not check `main` out in two worktrees at once.
git branch -f refresh origin/main
git worktree add "$TREE" refresh
cd "$TREE"
git branch --set-upstream-to=origin/main refresh >/dev/null

ln -s "$HERE/fy28/node_modules" fy28/node_modules
echo "node_modules linked"

echo "pulling the archive's binaries from R2 (about 1.4 GB, once) ..."
python3 scripts/sync_archive.py --pull

echo "building the derived database ..."
python3 scripts/build_db.py > /dev/null

echo
echo "refresh tree ready at $TREE, on branch 'refresh' tracking origin/main."
echo "The launchd job runs scripts/daily_refresh.sh here from now on; see ops/README.md."
