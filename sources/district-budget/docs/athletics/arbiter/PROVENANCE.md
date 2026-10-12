# The district's athletic schedules, from ArbiterLive

**Where it came from.** ArbiterLive, the scheduling platform the district's athletics page
links to: `https://www.arbiterlive.com/Teams?entityId=13354`. Entity 13354 is *Lunenburg
Middle High School*, which ArbiterLive prints at 1079 Massachusetts Ave, Lunenburg -- the
address the high school prints in its own footer at `https://lhs.lunenburgschools.net/`.

**What a snapshot holds**, one folder per fetch date:

| file | request | what it is |
|---|---|---|
| `teams.html` | POST `/Teams` `isAllTeam=true&isRedirect=true`, after GET `/Teams?entityId=13354` | every team, by sport and level (53 on 11 Oct 2026) |
| `schedule-<team>-<year>.html` | POST `/Teams/ScheduleForSchoolYear` `uniqueTeamId=<team>&schoolYearId=<year>` | one team's games for one school year. An XHR fragment: the POST and its form ARE its address; there is no GET |
| `game-<id>.html` | GET `/Teams/Game/<id>/13354/<team>/<year>` | one game's page: the venue's street address and the Transportation box. Held for every `@` game |
| `fetch-log.csv` | -- | every file's method, address, form, fetch time, bytes and sha256 |

School-year ids are ArbiterLive's own: 89 = 2021-22, 51 = 2022-23, 90 = 2023-24,
91 = 2024-25, 92 = 2025-26, 93 = 2026-27.

**The publisher's own name for it.** *Teams* / *Schedule*, on ArbiterLive (Arbiter Sports).

**STATUS: THE FACTS ARE PUBLISHED; THE PAGES ARE NOT.** The snapshot of 11 October 2026
(1,729 files, 43 MB) is held in the gitignored area `build/arbiter/2026-10-11/` and is not
archived or served. What this project publishes is what was read out of it (below), each
row carrying the ArbiterLive address it came from.

- **robots.txt.** `https://www.arbiterlive.com/robots.txt` reads `User-agent: *` /
  `Disallow: /` (Last-Modified 24 September 2026). `scripts/fetch_arbiter_schedules.py`
  reads and logs it, and fetches at most one page every two seconds with a User-Agent
  naming this site.
- **No names.** Ten 2021-22 schedule pages carried a team roster. Each was counted and its
  rows removed before anything was kept (`redact_rosters()` in the fetcher, applied to the
  held copy and to anything fetched); the counts are `sources/data/athletics-roster-counts.csv`.
  `fetch-log.csv` records which files were changed, with their new sha256, so the held copy
  is no longer byte-identical to what ArbiterLive served for those ten.

**What we read out of it.** `sources/data/athletics-schedules.csv` (one row per schedule
row) and `sources/data/athletics-schedules-coverage.csv` (sport x level x year), by
`scripts/extract_arbiter_schedules.py`; and the road distance to every away venue,
`sources/data/athletics-venue-distances.csv`, by `scripts/build_athletics_venue_distances.py`.

**What it is and is not.** A schedule the athletic office maintains, not a record of what
was played or what a bus cost. `missing` in the coverage file means ArbiterLive prints no
row, never that a team played nothing. ArbiterLive marks `vs` and `@` only; it has no
neutral-site flag.
