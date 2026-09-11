# The blog: what to put up, and roughly when

**This is a recommendation, not a schedule. Nothing reads this file.** No script parses it,
no build consults it, and no date in it does anything. What is actually live is the
`PUBLISHED` list at the top of `scripts/build_blog.py` — a person adds a line to it, runs
the generator, commits and deploys. TJ: *"the dates are just a PLAN you and I have. I will
tell you when we push the next post up. We'll discuss and post. Nothing automated."*

So read this the way you would read a note from a colleague who has thought about it: argue
with the order, ignore the weeks, and use it to decide what goes up next.

---

## The order, in one line

**Start with the two posts that defuse the argument, not with the ones that win it.** Then
the mechanisms nobody has been shown. Then the specifics, timed to whatever the town is
about to vote on. The posts about what the record cannot tell us go last, because they land
hardest once a reader already trusts the record.

## What goes up first, and the argument for each

These are the ones to start with — the case for the first five is that **each of them tells
a reader they were right and incomplete rather than wrong**, which is the shape 43 of the
48 items are built on and the only shape that survives a Facebook comment thread.

| item | why it goes first |
|---|---|
| **1.2** The same teacher counts give three different answers | It is the FY27 argument, it takes no side, and the thing it hands a reader — *ask which year the chart starts* — is usable at the next meeting they attend. Nobody has to be wrong. |
| **2.1** Losing a student does not cost the town its share of the school budget | The single most widely believed wrong mechanism in town, and correcting it costs nobody anything. Everything else about aid rests on it. |
| **1.1** Why a school with fewer children is not a cheaper school | The central factual dispute, with both halves true. It is the strongest item in the archive and it is deliberately not first: it reads better once 1.2 has established that two true charts can disagree. |
| **3.1** $1.5 million of school insurance is not in the school budget | A structural fact nobody disputes once they see it, and it changes what "the school budget" means for every post after it. |
| **6.4** The bottom line is dependable and no single line in it is | Gives the district credit where the record shows them getting it right (rule 8) and sets up every later post about a single line. |

**Nothing is in the `PUBLISHED` list yet, deliberately.** These five are a suggestion, and
the choice of what the town hears first is TJ's.

## Then, in rough order

1. **The aid mechanisms** — 2.2, 2.3, then 2.4. 2.4 is us correcting our own published
   error, and it should go up before anything else that leans on state-aid figures rather
   than after somebody finds it.
2. **What the town raises against what the schools cost** — 3.6, 3.3, 3.4, 3.2, 3.5.
3. **Special education**, which is about 22% of the budget and the least covered subject in
   town — 4.1 first, because the line residents argue about is the town's share, then 4.6,
   4.2, 4.3, 4.7, then the two class-size items 4.4 and 4.5.
4. **Where children go** — 5.1 and 5.2 early (both correct a widely held mechanism), then
   5.6, 5.3, 5.5, 5.7, and 5.4 last of that group, because it is the one that says the
   record runs out.
5. **What a budget document can be trusted to tell you** — 6.1, 6.3, 6.2, 6.6, 6.5, 6.7.
6. **Staffing and courses** — 1.3, 1.4, 1.6, 1.5, then 7.1, 7.3, 7.2, 7.4.
7. **What a family pays** — 8.1 and 8.2, best placed beside whatever fee decision is live.
8. **What the record cannot tell you** — 9.2, 9.3, 9.1, 9.4, 9.5. These are records
   requests in the form of posts, and they read as constructive rather than accusatory only
   once a reader has seen the archive be careful several times.

## The town's calendar, and the four places to aim something

**Check every date below before relying on it.** These are the anchors worth planning
around, not dates this project has verified:

- **Free cash certification**, in the autumn. The week the Division of Local Services
  certifies is the week to put up something about one-time money — and the point of that
  post is that free cash cannot bend the curve, which is the argument residents most often
  meet in the wrong direction.
- **A December capital vote**, if one is called. Aim 6.4 and 6.5 at it: what a bottom line
  can and cannot be trusted to say.
- **The Governor's budget, late January.** This is the single most valuable slot in the
  year for 2.2 and 2.3, because the Chapter 70 number arrives and the town reads it wrong
  within a day. Hold at least two aid posts back for it.
- **Budget season proper, from January.** Everything about special education and staffing
  is worth more in the weeks the School Committee is actually voting than in November.

## Pace

Forty-eight items and roughly seventeen weeks to the start of January is **about three a
week** to spend them all by the time budget season opens. One a day empties the whole set
by late October and leaves January — the month they are worth the most — with nothing.

The honest version: **three a week is a ceiling, not a target.** A post that goes up because
it is Tuesday is worse than no post, and the set is not a queue that has to be drained.
Hold the aid posts for the Governor's budget even if it means a quiet fortnight.

## How to publish one

1. Read it as a page. `python3 scripts/build_blog.py --all`, then `npm run dev` in `fy28/`,
   then open **`http://localhost:5173/blog-drafts`** — every post, rendered exactly as a
   reader would get it, with the Facebook post that would carry it above each one. That
   page does not exist on the deployed site and neither does the file it reads.

   `/blog` is the reader's surface and it shows only what is up. Nothing on it is
   addressed to us: no counts of what is written, no drafts, no item numbers, no formats.
2. Send it to somebody if it needs another reader. `python3 scripts/build_blog.py --pdf`
   writes one PDF per post plus a combined document into `build/pdf/`. Each is the
   READER'S post — the same content in the same order — with one italic line at the top
   saying it is an unpublished draft. Cover that line with your thumb and what is left is
   what a resident would get. `build/` is gitignored.
3. Edit the copy in `notes/process/CONTENT-CANDIDATES.md`. That file is the content and
   there is no other copy of it.
4. Add one line to `PUBLISHED` at the top of `scripts/build_blog.py`:

       PUBLISHED = {
           '2.1': '2026-09-15',
       }

   The date is recorded, not read: it prints on the archive row and nothing computes from
   it. The order of the lines is publication order, and the archive shows it reversed.
5. `python3 scripts/build_blog.py` — it writes the payload and the share card, and refuses
   if anything unpublished has reached the published side.
6. `python3 scripts/build_sitemap.py`, then build and deploy. Commit.

## One thing for whoever builds the search next

The search covers published posts only, and that is correct: a post that is prepared and
unpublished is not on the site at any address, so there is nothing for a reader to find. It
follows that **the coverage count has to be of published posts, not of prepared ones** — a
denominator that included the other forty-odd would report a gap that is not a gap.

The list to read is `fy28/public/data/blog.json`: every published post, with its slug, its
title, its headline, its full text and the report it links to. It is rebuilt from scratch on
every run, so there is no incremental path to get wrong and **nothing to do when a post is
published** beyond re-running whatever builds the index. If `scripts/build_minutes_fts.py`
is the natural home for it, that payload is shaped to be read directly rather than parsed
out of HTML.
