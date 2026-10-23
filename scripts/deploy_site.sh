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
# A COMPLETE dist IS NOT A FRESH ONE. On 23 October 2026 a build failed at its type check and
# left the morning's dist in place, whole and prerendered, so both checks below passed and the
# preview shipped stale. Refuse if any source or public file is newer than the built page.
NEWER="$(find fy28/src fy28/public -type f -newer fy28/dist/index.html 2>/dev/null | head -3)"
if [ -n "$NEWER" ]; then
  echo "NOT DEPLOYING: fy28/dist is older than the code and data it is built from, e.g.:"
  echo "$NEWER" | sed 's/^/  /'
  echo "Run: cd fy28 && npm run build:site   (and check it exits 0)"
  exit 1
fi
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
# OUR MEETING TEXT IS SERVED FROM ITS OWN BUCKET, NOT THE DEPLOYMENT. Pages refuses past
# 20,000 files and /docs/minutes/text/ alone is ~12,000 (21 October 2026). Push what changed,
# confirm the bucket holds every file by listing it, then deploy a hard-linked copy of dist
# without them. dist stays whole: the sitemap, search and checks read it.
STAGE="$ROOT/build/deploy-stage"
if ! python3 scripts/sync_derived.py --push || ! python3 scripts/sync_derived.py --check; then
  echo
  echo "NOT DEPLOYING: the derived bucket does not hold every meeting text file (above)."
  exit 1
fi
python3 scripts/sync_derived.py --stage "$STAGE" || exit 1
cd "$ROOT/fy28" && npx wrangler pages deploy "$STAGE" "$@" --commit-dirty=true
