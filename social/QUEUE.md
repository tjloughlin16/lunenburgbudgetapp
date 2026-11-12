# Post queue

What is waiting to go out, and the candidates for the next post. Written 12 November 2026.
Edit this file as posts go out or the options change; the live to-do is also on the
`social-posts` goal in genlock.

## Queued

### Special Town Meeting, 17 November: on the big questions, the room decides

`posts/2026-11-12-stm-where-boards-stand/` -- built, **not posted**. Waiting on the Finance
Committee, which takes up the articles tonight (12 November, 7:00 PM, Zoom).

The hook: on the four articles that cost money or change what people pay, the Select Board
has backed none. Article 4, the special education reserve, is recommended against. Articles 7
and 8 (TC Passios, stormwater) have no position. Article 9, the track, is deferred. And the
School Committee, which sponsored the reserve article, voted on 4 November to pass it over.

Before it goes out (due 13 November):

- [ ] Add the Finance Committee's recommendations from tonight's recording.
- [ ] Drop the "Finance Committee positions not yet posted" caveat on the image and the
      "tonight" line in the text.
- [ ] Re-check the Select Board's deferred articles. It votes on them at 6:30 PM on the 17th,
      in a session that will not be recorded.
- [ ] Rebuild with `python3 scripts/build_social_post.py social/posts/2026-11-12-stm-where-boards-stand`,
      post it, then set `"posted"` in `post.json`.

Sources: board positions are printed in the signed warrant
(`town-budget/docs/4559-november-17-2026-special-town-meeting-warrant.pdf`, signed 27 October).
The School Committee's pass-over (4 November), the Select Board's deferral (10 November) and
Capital Planning's "no recommendation" (10 November) come from the recordings, read in the
captions at the cited seconds.

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
