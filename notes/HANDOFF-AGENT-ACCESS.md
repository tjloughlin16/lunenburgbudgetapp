# Handoff — making this archive usable by an agent

**Scope.** One workstream: an assistant asked a question about Lunenburg should be able to
answer it from this archive, correctly, without help. Written 5 September 2026 to survive a
context reset.

**Nothing in this file is a source.** It is a claim about the repository. Check anything
load-bearing against the repository before acting on it — that instruction is not
boilerplate here, it is the exact failure this workstream spent a day fixing.

**Related:** `notes/HANDOFF-ARCHIVE-STORAGE.md` (where the bytes live), `CLAUDE.md`
sections *"Reachability"*, *"What /api/query can cost"*, and *"The shape almost every
defect here has taken"*.

## References

Kept here rather than in a commit message, because a commit message is not somewhere
anybody looks twice.

| | |
|---|---|
| Vercel, *Make your site readable by AI agents* | <https://vercel.com/kb/guide/make-your-site-readable-by-ai-agents> — the checklist this site was audited against on 5 September; the table of what it recommends and where this site stands is below |
| Is Agentic, an external readiness scan | <https://is-agentic.com/scan/lunenburgbudgetproject.org> — scan is triggered from that page; the result then reads at <https://is-agentic.com/api/v1/report?url=lunenburgbudgetproject.org>. **Not yet run to completion** |
| IndexNow | <https://www.indexnow.org/documentation> — how the sitemap is pushed to Bing, Yandex, Seznam and Naver. Google does not participate |
| Cloudflare D1 pricing and limits | <https://developers.cloudflare.com/d1/platform/pricing/> — 5M rows read and 100k written a day on the free plan, and it stops rather than bills |
| Cloudflare rate limiting rules | <https://developers.cloudflare.com/waf/rate-limiting-rules/> — free plan is one rule and a ten-second period only |
| Google Search Console | <https://search.google.com/search-console> — the only honest answer to *"is this indexed"*. **Domain not yet verified** |
| Bing Webmaster Tools | <https://www.bing.com/webmasters> — same, and the one several agent search tools are built on |

---

## Why this exists

Four separate assistants were asked, over one day, what this archive holds about
paraprofessionals. All four failed, in four different ways, and **none of the four
failures was the assistant's fault.** Each read what the site told it and answered
correctly from that.

| what it did | what was actually wrong |
|---|---|
| "the district doesn't publish staff counts" | `llms.txt`, under a heading called *What this site does not know*, said exactly that. The rosters had been extracted weeks earlier and the published disclaimer was never updated |
| went to GitHub and grepped the tree | it cannot reach the domain at all — sandbox egress allowlist. It landed on the Vite starter template, because that was still `README.md` |
| fetched a 435KB CSV, got 40% of it, reported ten years unreachable | the citation it followed pointed at the CSV. `/api/staff_roster_entries/2022` is 73KB and was exactly what it wanted |
| quoted our own caveat back at us, including two wrong numbers | the caveat was typed from a field that the same commit had already corrected |

The pattern underneath all four is in `CLAUDE.md`: **something derived was written down, the
thing it derived from moved, and nothing connected the two.**

## What exists now

Every figure below is read from the repository, not remembered.

**Ask a question**

- `/api/query` — one read-only SQL statement, over D1. **Answers a plain GET**, because
  most agent fetchers cannot POST. Returns the documents its rows came from, or says
  plainly that this query cannot be traced and how to write one that can.
- `/api/questions` — 107 worked examples, each executed on every build; the build fails if
  one stops answering. `sources/analyses/questions.md` is the same list for a person,
  `what-you-can-ask.md` the same again without SQL.

**Find out what exists before answering**

- `/api/tables` — 49 datasets, 45 of them stating **the years they cover**, with row counts
  and byte sizes. This is the file that answers *"is there data for what I am being
  asked?"* in 5KB.
- `/api/schema` — the grain of every table and the four ways to get a confident wrong
  answer.

**Read it without choking**

- Nothing published exceeds ~150KB, the figure an agent reported as its own cutoff. 817
  API files; anything larger is split by fiscal year and then chunked further.
- 37 long documents have a `.parts/` folder with an index, split on **page** boundaries,
  each part naming the pages it covers and the publisher's own file with its sha256 — so
  an assistant that cannot hold 16.8MB can still hand a person the link.

**Reach it at all**

- 1,366 files mirrored on GitHub and checked by `check_github_mirror.py`, for agents whose
  sandbox blocks this domain. The database is committed too.
- `sitemap.xml` is generated and lists 67 URLs — 24 pages and 43 addresses a program
  needs — because one agent's allowlist is built from **search results**, not from links in
  a page it fetched. Submitted to IndexNow.
- `README.md` is generated, and is the same map at the address a GitHub-only agent arrives
  at.

**Not be lied to**

- Every figure in published prose is derived, not typed. The caveats and the worked
  examples included.
- `check_generated.py` runs the `--check` of all 15 generators and fails if any output no
  longer reproduces.
- `check-agents.mjs` fetches every URL `llms.txt` advertises and fails if one does not
  answer, cannot be **finished** (over 150KB without a smaller form beside it), or is
  linked relatively rather than absolutely.

**Not cost anything or fall over**

- A query estimated to read over 250,000 rows is refused before it reads anything, from
  table sizes baked in at build time.
- Identical queries are served from the edge for ten minutes.
- `rowsRead` is on every answer: `COUNT(*) FROM v_staff_roster` returns one row and reads
  11,444.
- About 10 requests per ten seconds per IP, measured by `check_rate_limit.py` and checked
  as a **band** rather than a number, because two probes minutes apart gave 8 and 12.
- **Every failure says it is a limit, not an absence**, names the unlimited static routes,
  and instructs the agent to tell its reader the query service was unavailable rather than
  that the archive lacks the data.

**The database**

69 tables and views, 51,067 rows, mirrored into D1 by `sync_d1.py` — which refuses to
re-import a database D1 already holds, because a full replace is ~95,000 writes against a
free-tier limit of 100,000 a day, and four of them in one day is what exhausted it.

`dataset_document` (from `build_dataset_provenance.py`) joins an annual-report row to the
document it came from. `role_classification` (1,030 rows) maps every printed job title to a
category and, where the page says one, a grade — because the town has called the same job
Tutor, Aide, Paraprofessional, Para, (para) and Sped Para across fifteen years, and a
filter on the printed title measures the house style rather than the staffing.

## What is NOT solved

- **Sandbox egress allowlists.** The site answers any user agent in under 300ms with no bot
  protection — tested, including `GPTBot` and a bare one. Some agents still cannot reach
  it. The GitHub mirror and a URL pasted into the prompt are the only routes, and both
  work today. Nothing published here changes this.
- **Google indexing.** IndexNow reaches Bing, Yandex, Seznam and Naver. Google does not
  participate. Search Console is the only honest answer to *"has this been indexed"* and it
  needs the domain verified — **not done**.
- **No agent has completed the query path unassisted.** Every fix here was verified by a
  person. The last run reached `/api/index`, found no roster endpoint (true at the time,
  fixed since), and fell back to prose. **Whether an agent now FINDS the query endpoint is
  the open question**, and it is the only one that matters.
- **The 429 body is Cloudflare's**, seventeen bytes reading `error code: 1015`. The free
  plan allows one rule and a ten-second period only, and the block page cannot be
  customised. Mitigated by saying what it means in `llms.txt` and in `/api/query`'s own
  help, before a caller ever hits it. Untested whether a rate limiting rule accepts
  `action_parameters.response` on this plan — worth one attempt.
- **The 107 questions are all schema-shaped.** Not one is phrased the way a resident would
  ask. *"Is the school budget growing faster than the town can pay for?"* is the register
  that is missing, and it is the register the site is for.

## What to do next, in order

1. **Run one agent against a citizen-phrased question** with `/api/tables` pasted into the
   prompt, and ask it afterwards *how* it got there. If it names `/api/tables` →
   `/api/query`, the path works. If it goes to GitHub or quotes prose, the problem is
   discovery and no further navigation fix will help.
2. **Verify the domain in Google Search Console and Bing Webmaster Tools.** Ten minutes,
   and it is the only route to knowing what is indexed.
3. **Add citizen-phrased questions to the bank**, mapped to the queries that answer them.
4. Consider whether a rate limiting rule can carry a custom JSON body on this plan.
5. **Markdown mirrors of the app's own pages.** Vercel's agent-readability guide
   (`vercel.com/kb/guide/make-your-site-readable-by-ai-agents`) recommends serving a
   `.md` twin of every page and advertising it with
   `<link rel="alternate" type="text/markdown">` plus `Vary: Accept`. This site has
   markdown for the ANALYSES but not for the eighteen app routes, which are where the
   argument actually lives. It is the largest remaining gap on that guide's list.

### Checked against that guide, 5 September

| its recommendation | here |
|---|---|
| pages return 200, not 403, to an agent UA | yes — `curl -A Claude-User/1.0` returns 200 |
| robots.txt permissive, sitemap lists everything | yes, 67 URLs including the endpoints |
| server-rendered, not JS-only | yes, 18 prerendered routes |
| real 404s, not soft ones | yes — that is what `functions/_notfound.js` is |
| 429 with `Retry-After` | **added** — the daily counter resets at UTC midnight and that is the number given |
| llms.txt, linked rather than guessed | yes: robots.txt, the page head, and the sitemap |
| `openapi.json` | yes, generated from the endpoint list |
| `/.well-known/` metadata | yes, `ai-plugin.json` |
| JSON-LD on the homepage | already present |
| fenced, language-tagged code blocks | yes, in `questions.md` |
| **markdown mirrors with `Vary: Accept`** | **no — see item 5 above** |
| an MCP server at a stable `/mcp` | no. Worth considering: this archive is a better fit for MCP than most sites, because the useful surface is already a small set of typed queries |

## How to check it still works

    python3 scripts/check_generated.py          # 15 generators still reproduce
    python3 scripts/check_github_mirror.py       # the fallback is complete
    python3 scripts/check_sitemap.py             # every URL in the sitemap answers
    python3 scripts/check_rate_limit.py          # the published limit is roughly true
    node fy28/scripts/check-agents.mjs           # every advertised URL answers, reads, is absolute

## The rule this workstream is really about

A failure that looks like an absence is worse than a failure. Every defect here took that
shape: a join that matched nothing, a disclaimer nobody revisited, a truncated fetch with
no marker, a soft 404, a stale caveat, a limit that read as missing data. **An agent cannot
tell the difference between "there is none" and "you could not reach it" unless something
tells it** — so everything here that can fail now says which one it was.
