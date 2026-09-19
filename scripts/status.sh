#!/bin/bash
# The ingestion dashboard: open it, and keep it fresh while it is open.
#
#   bash scripts/status.sh          # open it and keep it updating
#   bash scripts/status.sh --once   # just rewrite it
#
# Local and gitignored. It reads this machine's process list and today's refresh log,
# neither of which is true for anybody else, so it is not on the site.
cd "$(dirname "$0")/.." || exit 1
if [ "${1:-}" = "--once" ]; then
  exec python3 scripts/build_ingest_status.py
fi
# Never two watchers: the second would fight the first for the same file.
pkill -f "[b]uild_ingest_status.py --watch" 2>/dev/null
nohup python3 scripts/build_ingest_status.py --watch > /tmp/ingest-status.log 2>&1 &
sleep 2
open build/status/index.html
echo "dashboard open; refreshing every 20s (stop with: pkill -f '[b]uild_ingest_status.py --watch')"
