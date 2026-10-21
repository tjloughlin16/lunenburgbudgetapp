# Social posts: where they stand, and what is next

Started 21 October 2026. The generator is `scripts/build_social_post.py`; one folder per post
under `social/posts/`. The format that works is in memory (`facebook-post-format`): something
residents don't know, a conflict, the caveat on the image. What leads is what residents care
about (`what-citizens-care-about`): their wallet, big binding decisions, long-term total
commitments, changes to their way of life. Heat sets WHEN, never WHAT.

## Layouts that exist (21 October 2026)

All four "item" layouts read the same `tiles` list (eyebrow = the subject, value, label,
text, path), so any post can be drawn any of them. Subject titles are large in all four
(TJ: the subject "needs to be a bit bigger. So it screams").

| layout | shape | best for |
|---|---|---|
| `tiles` | cards side by side | two to three comparable items |
| `bands` | full-width scoreboard bars, subject left, figure right | two to four items, a list with stakes (the Nov 17 post) |
| `poster` | one item takes the page, the rest in a strip | one item is the story |
| `split` | two solid colour panels | exactly two things set against each other |
| `spotlight`, `hero` | a card drawn like the page; one enormous figure | site features; a single figure |

`"layout": "auto"` picks an item layout neither of the last two posts used, so the town does
not see the same shape twice running. `drawn_as` on a post records what it was drawn in.

## TO DO -- not started (TJ, 21 October 2026: "put this on the to-do, not to do now")

**Templates by shape of content**, so a post starts from the right one:

- **one important metric** (hero / poster)
- **two metrics** (split / tiles)
- **four metrics** (bands / tiles, four)
- **two topics, each with its own metrics** (split or tiles with a sub-figure line)
- **four topics** (bands)

Each template: a starter `post.json` with the data block and slots, the layout(s) that fit,
and an example. Riff off the four drafts of the Nov 17 post, kept at
`social/posts/2026-10-21-town-meeting-nov-17/` (bands, the one posted) -- the other three
renderings were scratch; regenerate them by setting `layout`.

## TO DO -- automate posts without TJ's review (designed 21 October, not built)

1. **One public-importance score** for every thread (wallet, big, long-term, way of life),
   separate from heat; read by threads, suggested reports and posts. Point-in-time: computed
   for any date from only what the record held then, so a thread made today about a 2024
   topic gets its history; a daily file only records what the site showed.
2. **Figures without a person listening**: re-transcribe the 30 seconds around each figure
   with an independent local speech model; two hearings that agree count as checked. Until
   then, a recording figure reaches a post only through `sources/data/heard-figures.csv`.
3. **The post generator in shadow mode**: a daily draft to TJ's phone, compared with what he
   would have picked, until it agrees often enough.
4. **Then**: posting through Facebook's Page API with a veto window (goes out after a few
   hours unless TJ stops it). Needs a standing permission to deploy when a post is queued.

## BLOCKER FOR THE NEXT DEPLOY: Cloudflare Pages' 20,000-file limit (21 October 2026)

The 21 October build was 20,345 files and the deploy was refused. It went out at 19,984 by
HOLDING BACK 358 files that had never been live: the school journal's per-period API pages
(fy28/dist/api/munis_school_journal/, 241), the per-year pages of api/dese_teacher_salaries/
and api/teacher_salary_schedules/ (38), and 79 generated town-meeting thread feeds (all but
stm-2026-11-17). They are NOT on the live site. The next deploy will exceed the limit again.
The fix: serve paged /api/<table>/<n>.json (and similar) through a Pages Function reading R2,
as /docs already does (fy28/functions/docs/_bucket.js), so those files leave the deployment.
Pages Pro lifts the limit; Workers Paid does not.
