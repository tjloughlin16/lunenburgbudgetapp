# Social media posts

One folder per post, under `posts/<date>-<slug>/`. **The folder is the post.**

| file | who writes it | what it is |
|---|---|---|
| `post.json` | you | the spec: words, where each figure comes from, layout, flare |
| `post.txt` | the generator | **open it, select all, paste into Facebook** |
| `image.png` | the generator | **attach it** — every post has one, or nothing is written |
| `image.html` | the generator | what the image was drawn from |

    python3 scripts/build_social_post.py --new <slug>          # start one from the template
    python3 scripts/build_social_post.py social/posts/<folder> # build it
    python3 scripts/build_social_post.py --check               # does every unposted post still reproduce?

## Rules the generator enforces, so they do not depend on remembering them

- **No figure is typed.** A template says `{sb.counts.agendas|n}`; the `data` block names
  which payload in `fy28/public/data/` it comes from. A digit typed into the words is
  refused (rule 2). URLs are exempt; anything else that is not a figure goes in `literal`.
- **Plain text only in `post.txt`.** Facebook shows Markdown as punctuation, so `**`,
  `[link](url)` and `#` headings are refused. Emoji, line breaks and bare URLs paste fine.
- **No image, no post.** `post.txt` is written last, after the image renders and is
  measured to fit its canvas.
- **One capability per post.** The spec's `about` line names it. If it needs two, it is
  two posts.

## Same frame, own flare

Every image shares the frame — kicker, headline, footer with the address and the as-of
date. Each post picks a **layout** (`spotlight`: the thing drawn as the page shows it;
`tiles`; `hero`: one big figure) and a **flare**: an accent (`royal`, `pine`, `plum`,
`ember`, `violet`, `harbor`) and a background motif (`contours`, `dots`, `arcs`,
`stripes`, `blocks`). Leave `flare` empty and both are picked from the slug, so no two
posts look alike by accident.

## After it goes out

Set `"posted": "<date>"` in `post.json`. A posted post is frozen: the figures it quoted
were true on that day, and `--check` stops rebuilding it against data that has moved.

## The format that works

TJ, 14 October 2026, after `2026-10-14-what-we-spend` drew a lot of discussion: *"this is the
proper format ... in the future lets replicate what we did for FB posts."* Start from that
post's `post.json`:

- **The hook is something residents do not know**, with an emotional hit -- a measured fact
  that contradicts what people assume. Not a metric for its own sake, not a site feature.
- **The image carries a conflict**: a headline stating the gap with the figure in the accent
  colour, two equal `tiles` side by side, and a `conclusion` line under them saying who it
  affects. The caveat that keeps it fair goes on the image, because images travel alone.
- **News about the site goes in its own follow-up post**, with its own hook.
- Never a projection, never a count multiplied into a total, never "your" for an average.
