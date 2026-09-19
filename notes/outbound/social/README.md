# Posts written for somewhere other than the site

Facebook, Nextdoor, a mailing list. They live with the records requests rather than in
`build/` because they are **outbound communication**: once posted they are public, quoted,
and screenshotted, and a claim made here is as durable as one made on the site.

One file per post, named `<date>-<platform>-<what>.txt`. Plain text, because that is what
gets pasted — no Markdown, since Facebook renders `**` literally.

## The rule that matters

**Every figure in a post is derived, never typed.** The counts in the launch post come
from `scripts/build_app_metrics.py`, which computes them from the archive:

    python3 scripts/build_app_metrics.py      # rewrites notes/generated/APP-METRICS.md

Rule 2 is not only about the model. A number pasted into a post is the one thing here
nobody can check and nothing can correct: the site's figures are recomputed on every
build, and a screenshot of a Facebook post is forever. **Re-derive before reusing any of
these numbers** — the archive grows daily and every count in the launch post was already
stale the next morning.

## What the launch post deliberately leaves out

The five-year shortfall. It is a PROJECTION, ours, from the district's own budgets, and
putting it in a first public post invites an argument about the model instead of getting
people to the archive. TJ, 19 September 2026: *"i dont want to put projection data into
the FB post, as people on boards will focus on that."*

Everything in the post is instead a MEASUREMENT — a count of what is held — so the only
argument available is whether the documents say what we say they say, which is the
argument worth having. The projections are on the site, labelled, for anybody who goes
looking.

## Links

Written as `lburg.org/<page>` rather than a bare `/<page>`: a leading slash does not
auto-link on Facebook and reads as a typo. `lburg.org` 301s to the canonical domain.
