#!/bin/bash
# DEPLOY THE SITE, SAFELY, FROM ANYWHERE. No arguments, nothing to time.
#
#     bash scripts/deploy_site.sh
#
# TJ, 14 October 2026: three deploys in one morning went out while `npm run build:site`
# was still rewriting fy28/dist -- 130, 100 and 829 of ~1,900 pages built. Wrangler uploads
# whatever the folder holds at that moment (a TORN READ), and a deploy cannot see a build.
# So this one waits for any build in progress to finish, then refuses unless every sitemap
# page is in dist (check_dist_complete.py) and rendered (check_prerender.py), then deploys.
#
# The patterns are written so they cannot match this script's own command line
# (CLAUDE.md: `pgrep -f` matches itself).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:$PATH"
building() { pgrep -f "[p]rerender.mjs|[v]ite build|[n]pm run build:site" >/dev/null; }
if building; then
  echo "A site build is running. Waiting for it to finish (checking every 15s)..."
  while building; do sleep 15; done
  echo "Build finished."
fi
cd "$ROOT" || exit 1
if ! python3 scripts/check_dist_complete.py || ! python3 scripts/check_prerender.py; then
  echo
  echo "NOT DEPLOYING: fy28/dist is not fully prerendered (above). Run: cd fy28 && npm run build:site"
  exit 1
fi
# A TAKEDOWN THAT IS NOT IN THE MODULE IS NOT TAKEN DOWN. The 410s are compiled from
# sources/data/takedowns.csv; a stale module would deploy a withdrawn document as served.
if ! python3 scripts/takedown.py --check; then
  echo
  echo "NOT DEPLOYING: the takedown module is stale (above). Run: python3 scripts/takedown.py --write-module"
  exit 1
fi
cd "$ROOT/fy28" && npx wrangler pages deploy --commit-dirty=true
