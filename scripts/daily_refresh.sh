#!/bin/bash
# The daily run, as launchd calls it -- see ops/README.md. Everything the refresh needs on
# PATH, a log per day, and the state files committed afterwards so the next run -- on
# this machine or another -- starts from what this one saw. Nothing here posts to
# Facebook; the paste-ready texts land in build/notices-to-post.md.
#
#   bash scripts/daily_refresh.sh          # by hand
set -u
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/tj/lunenburgbudgets || exit 1
mkdir -p build/refresh-logs
LOG="build/refresh-logs/$(date +%Y-%m-%d).log"
{
  echo "=== daily refresh started $(date) ==="
  python3 scripts/refresh.py --deploy
  echo "refresh exit $?"
  # Commit the observation logs, previews, minutes and payloads. A refresh that is not
  # committed is a refresh the next machine cannot see.
  git add sources/data/meeting-watch-*.csv sources/data/youtube-watch-events.csv \
          sources/data/youtube-videos.csv sources/data/youtube-video-boards.csv \
          sources/data/youtube-video-classification.csv sources/data/youtube-transcript-index.csv \
          sources/data/youtube-no-captions.csv sources/data/minutes-searchable.csv \
          sources/data/refresh-runs.csv sources/data/recording-minutes sources/data/agenda-previews \
          sources/meetings/index.csv sources/meetings/text fy28/public/data fy28/public/sitemap.xml \
          notes/generated/APP-METRICS.md 2>/dev/null
  if ! git diff --cached --quiet; then
    git commit -q -m "Daily refresh, $(date +%Y-%m-%d)

$(tail -1 sources/data/refresh-runs.csv)

Automated by scripts/daily_refresh.sh." && git push -q origin main && echo "committed and pushed"
  else
    echo "nothing to commit"
  fi
  echo "=== finished $(date) ==="
} >> "$LOG" 2>&1
