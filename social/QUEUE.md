# Post queue

What is waiting to go out, and the candidates for the next post. Written 12 November 2026;
Town Meeting posts updated 13 November.
Edit this file as posts go out or the options change; the live to-do is also on the
`social-posts` goal in genlock.

## Queued

### Special Town Meeting, 17 November: three posts, in order

All three link to `lburg.org/threads/stm-2026-11-17`, the one page covering every article.
Built 13 November, **none posted**. They replace `posts/2026-11-12-stm-where-boards-stand/`,
which is superseded: its "Finance Committee meets Thursday" line is past, and it does not know
about the School Committee's 16 November vote on the track. Do not post it.

1. `posts/2026-11-14-stm-school-articles/` -- **this weekend.** The hook: both articles the
   School Committee put on the warrant may not reach a vote. It voted 4 November to pass over
   the special education reserve, and meets Monday 16 November to consider passing over the
   track engineering article. TC Passios and stormwater stay as the advisory questions.
2. `posts/2026-11-16-stm-stormwater-choice/` -- **Monday or the day before.** The wallet hook:
   fee or property taxes, per single-family home, as the Stormwater Task Force presented it.
3. `posts/2026-11-17-stm-tonight/` -- **morning of the 17th.** When, where, how many articles,
   the link.

Before any of them goes out:

- [ ] **Finance Committee positions.** It took up the articles 12 November (Zoom); its column
      is blank on the warrant and the recording is not in the data yet. Once read, add them to
      post 1 and drop "Finance Committee positions not yet posted" from its image.
- [ ] **Re-check post 1's track line after Monday's School Committee vote (16 November).** If it
      passes over Article 9, rewrite the headline from "may never reach a vote" to what
      happened; if it does not, the hook changes and post 1 needs a new one.
- [ ] Re-check the Select Board's deferred Articles 2, 3 and 9. It votes on them at 6:30 PM on
      the 17th, in a session that will not be recorded.
- [ ] Confirm the live page shows the 16 November School Committee meeting before posting 1.
- [ ] Rebuild with `python3 scripts/build_social_post.py social/posts/<folder>`, post, then set
      `"posted"` in that folder's `post.json`.

Sources: board positions are printed in the signed warrant
(`town-budget/docs/4559-november-17-2026-special-town-meeting-warrant.pdf`, signed 27 October).
The School Committee's pass-over (4 November), the Select Board's deferral (10 November) and
Capital Planning's "no recommendation" (10 November) come from the recordings, read in the
captions at the cited seconds. The 16 November item is on the School Committee's agenda
(`meetings/school-committee/2026-11-16-agenda-8136.pdf`). Stormwater figures are the task
force's, as presented, quoted on the warrant.

## Next post: pick one

Ranked by what residents care about (their wallet, big decisions, long-term commitments,
the places they use). How much boards are discussing a topic only decides timing. Ranking
read from `fy28/public/data/threads.json` on 12 November.

1. **Town offices: the municipal building plan** -- *recommended.* The question is where
   the town's offices go and what voters will be asked to pay for it. It is the
   highest-ranked topic on the site by a wide margin, and it does not overlap the Town
   Meeting post. On 9 November a cable committee member said Town Hall's second floor
   "sways and creaks" in wind, and another asked whether it has mold. The Select Board
   discussed municipal buildings on 10 November.
   *Check the quote by ear before it goes on an image: it comes from captions, and it is one
   member's observation, not an engineering finding.*

2. **Tax classification hearing, 24 November** -- the Select Board decides how the tax
   levy splits between homes and businesses, and that split sets every tax bill. The
   Assessors present the options at 7:25 PM. No topic page tracks it yet.
   *Close in subject to the 3 November tax-bill post. Best posted a few days before the
   hearing.*

3. **The stormwater fee** -- will every property pay a new charge, how much, and billed
   how? The most active topic right now: 10 meetings across 5 boards in 30 days. The task
   force is working through the per-property fee spreadsheet and held a public session at
   the library.
   *Featured heavily in the queued post. Better after the 17 November advisory vote, as a
   follow-up on what the room chose.*

4. **The veterans property tax exemption** -- does it increase, and what does it shift onto
   other taxpayers? The Assessors went into executive session on 4 November to review
   senior and veterans exemptions.
   *Thin on public record so far. Needs a figure before it can carry a post.*

5. **School FY26 budget reconciliation** -- a request for Finance Committee reserve funding,
   tied to reconciling the FY26 school budget. It is back on tonight's Finance Committee
   agenda. On 22 October the chair said "nothing is formalized yet" and called it "not an
   audit".
   *Wait for tonight's recording. Frame it as what it means for planning (rule 8), never as
   what went wrong.*
