# Running the refresh every day

**It runs in its own checkout.** `scripts/setup_refresh_tree.sh` (once) creates a git
worktree at `../lunenburgbudgets-refresh` on a branch called `refresh`; every run resets
it to `origin/main`, refreshes, commits, pushes to `main`, builds and deploys. People and
agents never work in that tree -- they work here, on branches, and merge to `main`. After
each refresh this tree is behind `main` by one commit: `git pull` before starting work.
Why: on 15 September 2026 the refresh ran here while a feature branch was checked out and
its deploy went to a Pages preview alias; production missed a day.

    bash scripts/setup_refresh_tree.sh    # once; pulls the archive's binaries from R2 (~1.4 GB)

`scripts/daily_refresh.sh` runs `refresh.py --deploy`, commits the observation logs,
previews, minutes and payloads, and pushes. It logs to `build/refresh-logs/<date>.log`.
Nothing in it posts to Facebook; the paste-ready texts land in `build/notices-to-post.md`.

Install it as a launchd job. It fires at 7:00 every morning AND at every login/boot; the
script itself refuses to run twice in one day, so a Mac that was off at 7:00 catches up
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

## The Wednesday sweep

`org.lunenburgbudgetproject.sweep.plist` runs `scripts/weekly_sweep.sh` at 18:00 every
Wednesday: `sweep_backlog.py` works the agentic backlog four jobs at a time until 22:55,
five minutes before the plan's weekly reset, and stops the moment the plan refuses. The
daily caps in `refresh.py` stay small so the week's allowance is there for interactive
work; the sweep spends what is left rather than letting it lapse.

    cp ops/org.lunenburgbudgetproject.sweep.plist ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/org.lunenburgbudgetproject.sweep.plist


# The ingestion dashboard, without a watcher

`bash scripts/status.sh` opens the dashboard AND starts a watcher that rewrites it every
20 seconds -- and that watcher dies with its terminal. TJ, 22 September 2026: *"i need
this dash to not need YOU to run a watcher"*, after the page had sat frozen since the
previous afternoon while looking exactly like a dashboard of a busy machine.

**That is the failure worth naming: a stale dashboard and a live one are identical unless
you check the file's timestamp.** It read as a refresh still running; the refresh had
stopped nineteen hours earlier.

    cp ops/org.lunenburgbudgetproject.status.plist ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/org.lunenburgbudgetproject.status.plist

It rewrites `build/status/index.html` every 60 seconds, at login and after a reboot, with
nobody at the keyboard. Stop it the same way as the others:

    launchctl unload ~/Library/LaunchAgents/org.lunenburgbudgetproject.status.plist

Check it is actually updating -- which is the whole point, so check it properly, by
watching the mtime MOVE rather than by seeing that it is recent:

    B=$(stat -f %m build/status/index.html); sleep 70; stat -f %m build/status/index.html
