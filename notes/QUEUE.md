# What is queued, in order

Written 8 September 2026. Ordered deliberately: **finishing beats starting**, and each
item below is either half-built or blocked on the one above it.

---

## 1. Finish the three partial pages — ONE AGENT AT A TIME

Four agents were launched at once and the machine saturated: load average 15, and each
agent runs `npm run build:site`, which spawns Chrome and prerenders every route. **That
build is not parallel-safe** — they contend for `dist/` and prerender port 8794, which
produces phantom "rendered 0 chars" failures that look like real defects. Three were
stopped mid-work.

All three are routed and rendering. Resume them rather than restarting — their context is
preserved and each was close.

| page | where it stopped |
|---|---|
| `/what-families-pay` | building the charts component; had the most new findings queued |
| `/if-students-leave` | wiring the route and App |
| `/stopped-being-funded` | making the search counts derived rather than typed |

**One at a time.** This is the lesson, not an aside: four agents was right for the work and
wrong for the machine.

## 2. Harvest the meetings, 2023-2024

**~1,734 documents we do not hold.** Confirmed against the town's own AgendaCenter,
one year at a time to be sure the range flags behave:

    2023: 841      2024: 893      2025: 904 (we hold 901 — essentially complete)

`fetch_agendas.py --from 2025` was a CHOICE somebody made, and it was then read — by me —
as a fact about what the town publishes. It is not.

## 3. Fix the denominator that made step 2 invisible

`search_minutes.py` prints on every run:

    Searched 1,422 of 1,422 documents the town has published.

**That denominator is ours.** It compares what we hold against what we hold, and calls the
result what the town published. The line exists precisely so that a grep finding nothing
cannot read as *nobody said it* — and it has been doing the opposite, reassuring us with
our own number.

Fix it to compare against what the AgendaCenter reports exists, and to say plainly when the
two differ. **Do this AFTER the harvest**, or it just prints a more precise wrong number.

## 4. Re-run every rule 15a search that came back empty

Athletics, PEG, free cash and the rest were searched against a corpus missing more than
half the record. In particular: **why $1,500?** The School Committee minutes of 26 February
2025 record the vote and no derivation. A slideshow was presented and is not in the
archive. The reasoning may sit in a 2023 or 2024 meeting nobody has read.

## 5. YouTube transcripts — a finding aid, never a source

The minutes carry a standing notice that each meeting is recorded and uploaded, and the
archive already holds the address: `youtube.com/user/LunenburgAccess/videos`. That is the
PEG access channel whose finances this project extracted the same week.

Needs one install (`yt-dlp` or `youtube-transcript-api`); neither is on the machine.

**Design it with the caveat built in from the start.** Auto-generated captions are a
machine's rendering of audio, not a record. They mangle names and — fatally here — numbers:
*fifteen hundred*, *$1,500* and *$50* are the same sound to a caption model. So a
transcript locates the moment; the citation is the video at that timestamp, or the document
it tells you to ask for. **A figure quoted from a caption as though it were the record is
rule 13 with a microphone.**

---

## Blocked, not queued

- **D1 is not synced.** Today's write budget is spent — the free tier stopping, not
  billing. ~70,000 rows per full push against 100,000 a day, and several went today.
  Resets tomorrow; `sync_d1 --check` is the only red until then.
- **D7, the records request.** Still the highest-value thing on the whole list and still
  TJ's to send. It has grown teeth this week: the MUNIS year-end expense report for prior
  years (we already hold FY2026's, so it is a small ask against a named document), the
  athletics accounts-payable detail, the district's fee schedule as published to families,
  and the 26 February 2025 athletic user fee presentation.
- **D3**, the tax-rate and town-meeting extraction, still parked.
