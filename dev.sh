#!/bin/bash
# START EVERYTHING LOCAL, IN ONE COMMAND:   ./dev.sh
#
#   the site, live-reloading   http://localhost:5173        (vite, from fy28/)
#   the ingestion dashboard    http://127.0.0.1:8795        (scripts/status.sh)
#   ...its Backlog tab         http://127.0.0.1:8795/backlog.html
#
# Ctrl-C stops both. Neither needs a build: `npm run build:site` is the DEPLOY build -- it
# prerenders every page into fy28/dist and waits on the refresh's build lock -- and is not
# how to look at the site.
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:$PATH"

stop() {
  echo; echo "Stopping..."
  [ -n "${SITE:-}" ] && kill "$SITE" 2>/dev/null
  pkill -f '[b]uild_ingest_status.py --watch' 2>/dev/null
  pkill -f '[d]ashboard_server.py' 2>/dev/null
  exit 0
}
trap stop INT TERM

(cd "$ROOT/fy28" && npx vite --port 5173) &
SITE=$!
bash "$ROOT/scripts/status.sh" >/dev/null 2>&1 &

sleep 4
open "http://localhost:5173/"
echo
echo "  site       http://localhost:5173/"
echo "  dashboard  http://127.0.0.1:8795/   (backlog: /backlog.html)"
echo "  Ctrl-C to stop both."
wait "$SITE"
