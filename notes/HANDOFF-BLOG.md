# Handoff: the blog, the brand, and what is waiting

Written 11 September 2026, before a laptop restart. Read `CLAUDE.md` first.

**Nothing in this file is a source.** After a context reset it reads exactly like something
already verified. It is a claim about the repo and it has been wrong before. Check anything
load-bearing against the repo itself.

---

## Where everything is

**UPDATED 11 September, evening.** Everything below the line was done in one session and
is DEPLOYED (`2fb983f3`, `origin/main` = `e3fdd527`+):

- **/search** — five... six corpora, one D1 database `lunenburg-search`. The first load is
  **two-thirds pushed**: `python3 scripts/sync_search_d1.py` tomorrow sends the remaining
  ~33,000 rows (709 minutes files, 260 transcripts, the 22 `recorded` rows) and writes the
  build date; then `--check`. Do NOT run `sync_d1.py` the same day. Search-page
  denominators read 0 for corpora not yet pushed; that is the push, not a bug.
- **/what-was-said** — 22 meetings' minutes from the recordings, approved scope only. To
  widen: `write_recording_minutes.py --board <slug> --limit N` (~$0.50, 2 min each), then
  `build_recording_minutes.py`, rebuild the index, push, deploy.
- **Affinity** — `sources/data/search-affinity.csv`, 77 pages tagged. Edit the CSV; the
  index rebuild and push replace the table whole.
- **App metrics** — `notes/generated/APP-METRICS.md`, generated; regenerate after any
  ingest before sharing.
- **The family-fees inset bug** TJ found is fixed and live.
- **The transcript backfill** is still running (`/tmp/transcripts.log`); 748 held at the
  last index build. It is safe to leave running; `sync_archive.py --push --only
  data/youtube-transcripts` backs up what is new.

Remaining from the original list: the post order (after Tiffany), the refresh mechanisms
and digests (12, 12a), items 13–17, the paused pages 7–9.

---


**`HEAD == origin == 38b7e540`, zero uncommitted.** All work is on GitHub.

| | |
|---|---|
| 590 meeting transcripts, 154MB | **on disk only** — gitignored by design, and `sync_archive.py --push` has NOT run. No second copy exists anywhere. |
| `.census-key` | on disk, gitignored, not recoverable from git |
| `build/`, `fy28/dist/` | regenerable, safe to lose |

**Nothing is deployed.** The live site is still yesterday's build. Thirteen commits of
today's work — the census page, the whole blog system, the brand, the content inventory —
are pushed but not live.

---

## THE BLOG, and the one thing to understand before touching it

**This is not a CMS.** That was said out loud after three messages of me building one, and
the mechanism is now four lines:

```python
PUBLISHED = {}          # scripts/build_blog.py, line ~112
```

To publish: add `'2.1': '2026-09-15',`, run the generator, commit, deploy. **The date is
recorded and nothing reads it.** No scheduling, no draft states, no publish workflow — git
is the workflow, and a person decides in a conversation. TJ: *"the dates are just a PLAN
you and I have. I will tell you when we push the next post up. Nothing automated."*

### The three tiers, and why the middle one exists

| tier | what | how long | where |
|---|---|---|---|
| the hook | a card — label, headline, one line, link | ~8 seconds | a Facebook post, the home page |
| **the post** | why it matters, the numbers, what it means for you | ~2 minutes | **`/blog/<slug>`** |
| the working | the full analysis, charts, caveats, sources | ~20 minutes | the existing analysis pages |

The middle tier is the one that persuades. **A card is too short to convince anybody and an
analysis page is too long to read from Facebook.** I built tiers 1 and 3 first and assumed
people would jump between them; they will not.

### Two surfaces, and they must not merge again

- **`/blog`** is the READER'S. Published posts only. **Nothing addressed to us anywhere on
  it** — no counts of what is unpublished, no format filter (filtering by "Myth vs fact"
  would tell a reader we have four formats), no item numbers.
- **`/blog-drafts`** is TJ'S. Local only, never built, never deployed. Per item: the
  Facebook post beside the blog post it links to, because that pairing is what he is
  judging — does the hook earn the click, does the post deliver on it. Collapsed by
  default; 48 expanded items is a page nobody can hold a judgement in.

They share ONE `PostPage` component. **Cover the drafts page's frame with your thumb and
what remains is byte-for-byte the reader's post.** A preview that carries extra material is
not a preview.

### The absence is proved, not argued

`build_blog.py --check` and `verify_blog.py` walk every byte of `fy28/public/` and
`fy28/dist/` looking for each unpublished item — 145 probes. **It has caught real leaks**
(drafts left in a stale `dist`). Run it after any change to the blog.

`fy28/public/` IS the site: anything in it is served whether or not a page renders it. That
is why the drafts payload lives in gitignored `build/` behind a `apply: 'serve'` vite
plugin with no build hook.

### Looking at it

```
python3 scripts/build_blog.py --all     # writes the review copy into build/
cd fy28 && npm run dev                  # Node 20 is fine for dev; 22 for a build
```
`localhost:5173/blog-drafts` · `localhost:5173/blog` · `localhost:5173/`

`python3 scripts/build_blog.py --pdf` → 48 PDFs plus one combined, in `build/pdf/`, for
sending to the collaborator. **The PDF is the reader's post** — cover the draft notice and
it is byte-for-byte what a resident gets.

---

## WHAT IS OWED — the editorial pass TJ asked for and I have not done

1. **Pick the post order** — AFTER Tiffany has reviewed the package. TJ: *"pick the ones that you think the community cares about
   most."* `notes/process/BLOG-PLAN.md` suggests 1.2, 2.1, 1.1, 3.1, 6.4 with an argument
   for each; the ordering reasoning there is good and worth keeping — 1.1 is deliberately
   third because it reads better once 1.2 has established that two true charts can disagree.
2. ~~**Fix the 14 flagged headlines.**~~ **DONE, 11 September** (`da32bb53`, `65a0f0f6`): every
   headline is one sentence inside both budgets. All 14 were the same problem: the headline runs past
   ~125 characters and Facebook cuts it mid-sentence at "See more". `python3
   scripts/check_content_cards.py` lists them. Fixing a headline fixes the card and the
   post together — it is the same 126-character budget, measured off the rendered card.
3. ~~**Item 1.4 does not open with its headline.**~~ **DONE.** It did open with it — but the
   headline was three clauses and the composer takes the first sentence only, so the post
   opened *"All programmes: 57.0 posts to 67.0."* It is one sentence now.
4. ~~**Zip the PDFs with their Facebook posts**~~ **DONE.** `build/lunenburg-budget-project-drafts.zip`
   — README with each post's text, `posts/` PDFs, `images/` share cards. Sent to TJ 11 September.

Then TJ's stated sequence: **deploy `/lunenburg-by-the-numbers` and the favicon, then the
blog scaffolding — which is a no-op for viewers because nothing is published.**

---

## THE BRAND — chosen, not deployed

**"The Margin."** Ruled paper, a gutter, one ochre highlighter stroke, a pale treeline. The
favicon is the same idea as an **L** — a vertical stroke and a foot drawn as a page margin.
TJ: *"it seems more formal than the others"*, and formal is right, because **formal is not
official**.

- `sources/data/brand/facebook-group-cover.png` — 1640x856, for the group. Carries BOTH
  addresses: `lunenburgbudgetproject.org · or just lburg.org`.
- `fy28/public/favicon.svg` — live in source, not yet deployed.

**It refuses three things, and each was a decision.** No seal or crest — a private project
that reads public documents has no business looking municipal. **No brand blue** —
`--brand: #12428f` is the Blue Knights' royal, the DISTRICT's colour, and alone on a
banner it reads as the district talking. And no figure, because a banner cannot be
corrected.

**The favicon was not where anybody would look for it.** `fy28/index.html` carried an
INLINE data URI of the school-building emoji while `fy28/public/favicon.svg` sat
unreferenced with a purple template mark in it. Swapping the file alone changes nothing and
looks like it has.

---

## THE ORDER, reset by TJ on 11 September

1. **NOW** — finish the blog (above), the Facebook header, the favicon. The transcript
   backfill runs underneath and costs no attention.
2. ~~**NEXT — search across EVERYTHING.**~~ **BUILT 11 September** (`1cab0247`); see
   QUEUE item 18. What remains is operational: the first D1 load is two runs on two days
   (`python3 scripts/sync_search_d1.py`, then `--check`), and after any deploy that
   changes pages, `build_search_index.py` then the sync. Original note follows. Every page, every blog post, every source document,
   every minute. TJ's reason is a deadline in disguise: *"People need to be able to find
   things once we start pushing people here."* The blog exists to bring strangers from
   Facebook, and a stranger who searches for the one thing they care about and finds
   nothing concludes the site does not have it. **The index must be built to TAKE blog
   posts that do not exist yet.** `notes/QUEUE.md` item 18 has the five constraints; its
   scope is written for minutes only and is now much wider.
3. **THEN — minutes from the transcripts.** **BUILT 11 September** (`96887e4f`).
   `write_recording_minutes.py` writes one JSON per recording via `claude -p --tools ""
   --json-schema` (no API key needed; runs on TJ's subscription, ~$0.50 and two minutes a
   meeting); `build_recording_minutes.py` makes the payload; `/what-was-said` renders the
   index and one page per meeting, every item linked to the video at its second.
   **Approved scope so far: School Committee, Finance Committee, Select Board since
   11 June 2026 — 22 meetings.** TJ: *"we will do all others later."* Running the rest
   (~640 transcripts, ~$300, ~20 hours serial) is a decision, not a default. The minutes
   are also a search corpus (`recorded`). Original note follows.

   Inserted by TJ on 11 September, ahead of the refresh work. 590 machine transcripts are held and most School Committee
   meetings have no other surviving record. The job: **write our own minutes for every
   transcript**, in a fixed format, stored beside the meeting's agenda and its official
   minutes where those exist. What TJ wants first in each: **votes taken** (not the
   procedural ones — adjournment, approving prior minutes), **budget items discussed**,
   **transfers**, **decisions made**, and **topics with their resolutions**.

   The order is the point: (a) process one or two School Committee transcripts by hand
   to find the format; (b) build the generator that produces minutes for any transcript,
   stores them, and links them to the agenda and official minutes; (c) render a page or
   two in that format for TJ to review; (d) only once approved, run it across all 590.
   Rule 7 and rule 13 apply with full force — a caption is a derived rendering of what
   was said, every figure in it is `stated`, and a vote read off a caption is a claim
   about the recording, cited to the video at its timestamp, never to a document.

4. **THEN** the refresh mechanisms and the meeting digests (12, 12a). 12a is still *"the
   actual point"*.
5. **AT THE END, for now** — items 13-17, deferred as a block.
6. **Paused, not dropped**: pages 7, 8 and 9 of the nine-page order — enrollment, circuit
   breaker, AP coursework. Data for all three is loaded.

---

## The transcripts

**590 held**, paused mid-Select-Board. Resume with:

```
nohup bash scripts/run_transcript_backfill.sh > /tmp/transcripts.log 2>&1 &
```

It re-fetches nothing — the index is written after every fetch. **Phase 1 is complete**:
every meeting with no other surviving record and with captions now has one, 199 of 226. The
27 that carry no captions at all are flagged in `sources/data/youtube-no-captions.csv` for
TJ to look at.

**Two bugs fixed today that are worth not reintroducing.** `TranscriptsDisabled` is a
permanent fact about one recording and was being counted as throttling — three captionless
2017 meetings in a row read as an IP block and cost fifteen hours of escalating cooldowns
while nothing was wrong with our access. And phase 1 could never complete, because it asked
how many remained rather than how many were fetchable, and cooled down forever over 27 it
could never get.

---

## Still owed, none of it blocking

- `sync_d1.py` — `dese_class_size`, `dese_ap`, `dese_attrition`, `census_acs` are not
  queryable through `/api/query`
- `sync_archive.py --push` — the attrition workbook, ten census JSONs, **and the 590
  transcripts** have no second copy
- `build_master_report.py` needs a re-run now the blog's tabs are registered
- `notes/QUEUE.md` cleanup — nine of nineteen items are done and nothing is struck off, so
  the queue reads far longer than the real backlog

## TJ's own

D7 records request · D3 tax rate · nine unpriced family fees · **which five posts go first**
