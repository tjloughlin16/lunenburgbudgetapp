# Running the refresh every day

`scripts/daily_refresh.sh` runs `refresh.py --deploy`, commits the observation logs,
previews, minutes and payloads, and pushes. It logs to `build/refresh-logs/<date>.log`.
Nothing in it posts to Facebook; the paste-ready texts land in `build/notices-to-post.md`.

Install it as a launchd job. It fires at 9:00 every morning AND at every login/boot; the
script itself refuses to run twice in one day, so a Mac that was off at 9:00 catches up
the next time it starts, and one that was asleep runs on wake.

    cp ops/org.lunenburgbudgetproject.refresh.plist ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/org.lunenburgbudgetproject.refresh.plist

Run it by hand:          bash scripts/daily_refresh.sh
Stop it:                 launchctl unload ~/Library/LaunchAgents/org.lunenburgbudgetproject.refresh.plist
Did it run today?        tail -20 build/refresh-logs/$(date +%Y-%m-%d).log

Costs per run: agenda previews ~$0.20 each and minutes ~$0.50 each, only for the boards
and dates in `sources/data/recording-minutes-policy.csv`; everything else is free. The
search-index push uses up to 20,000 of the day's 100,000 D1 writes, so a full
`sync_d1.py` should not run on the same day as a large refresh.
