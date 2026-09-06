# Handoff — making this archive usable by an agent

**Scope.** One workstream: an assistant asked a question about Lunenburg should be able to
answer it from this archive, correctly, without help. Written 5 September 2026 to survive a
context reset; extended 6 September with the MCP server, its registry publication, and the
front-page link.

**This file records the attempt, not only the parts that worked.** What was tried and did
not pay off is here on purpose — an approach that failed is worth more written down than
rediscovered, and the register in which this workstream fails is *quietly*, so the dead
ends are the evidence.

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
| MCP Registry, source | <https://github.com/modelcontextprotocol/registry> — the authority on DNS auth. `internal/api/handlers/v0/auth/dns.go` and `common.go` answered every question the docs did not |
| MCP Registry, our entry | <https://registry.modelcontextprotocol.io/v0/servers?search=lunenburg> — read the entry back rather than trusting a success line |
| `mcp-publisher` releases | <https://github.com/modelcontextprotocol/registry/releases> — the official binary. **Not** the npm package of the same name |
| server.json schema changelog | <https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/CHANGELOG.md> — what each dated schema changed, and whether migration is required |

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

## The MCP server

`lunenburgbudgetproject.org/mcp` — Streamable HTTP, no authentication, eight tools. A
separate Worker (`mcp/`), because Cloudflare documents remote MCP on Workers only; it binds
the same D1 database as the site's `/api/query`, so the two cannot disagree. A Workers route
on the zone diverts only that path; the Pages site is untouched.

**It is not a wrapper over the HTTP API, and that is the point.** A caveat in a document is
read once, if ever. A tool description is read every time the tool is called. So the tools
are shaped to make the documented mistakes unreachable:

| tool | the mistake it prevents |
|---|---|
| `budget_history(label, stage)` | takes ONE stage. A growth rate cannot be measured from an actual to a budget — the error that put a special education escalator 1.5 points too high |
| `staff(fy, category)` | reads `role_category`, never the printed title, which has changed five times in fifteen years |
| `search_meetings(word)` | says explicitly that an empty result means *not in the indexed documents*, and that the archive starts January 2025 |
| `document(name)` | returns the URL and the sha256, so citing is a call rather than a discipline |
| `list_datasets` / `read_first` / `worked_examples` | the discovery three agents never made |
| `query(sql)` | the escape hatch, with the same guards as the HTTP endpoint |

Every tool returns the documents its rows came from, or says plainly that this result has
none. A plain GET to `/mcp` returns a description of the server rather than a JSON-RPC
*Method not allowed*, because somebody fetching that address is trying to find out what it
is.

Deploy with `cd mcp && npx wrangler deploy`. Indexed in the sitemap, `llms.txt`,
`/api/index` and `.well-known/ai-plugin.json`.

**Untested by a real client.** It answers `tools/list` and `tools/call` correctly over the
wire, which is not the same as an assistant choosing to use it.

### Finding out whether anything uses it, without asking

There is no unbiased way to ask an assistant whether it used the tools: asking beforehand
tells it the answer, asking afterwards invites a reconstruction. Watching the server biases
nothing.

    cd mcp && npx wrangler tail lunenburg-mcp --format json

Every tool logs its name and duration — not its arguments, because a question somebody puts
to an assistant is theirs. Ask an assistant an ordinary question and see whether anything
arrives.

### How an agent could DISCOVER it

**MCP has no website-level discovery convention.** `server/discover` is a client asking a
server it already knows; there is no `/.well-known/mcp.json` in the specification. So there
is no single answer, and three partial ones were built instead. All three are live.

| route | reaches | verified |
|---|---|---|
| **The front page** | anything that reads the HTML | `href="https://lunenburgbudgetproject.org/mcp"` at byte 12,944 of 261,685 — **4.9% in** |
| **The registry** | clients that browse it | `org.lunenburgbudgetproject/archive`, status `active` |
| **`llms.txt`, the sitemap, `/api/index`, `.well-known/ai-plugin.json`** | agents that read those | one occurrence each, checked on production |

#### 1. The front page, which is the one that needed no permission from anybody

The address is in the top line of every route — the utility bar that
`src/components/DataTopLine.tsx` exists for. Its docstring carries the measurement that put
it there: the footer's addresses sat at **95.2%** of the homepage, and a reader that
converts a page and caps the result never reached them. `/mcp` now lands at **4.9%**.

That line is also read by people, so it was cut from 330 characters to 176 by printing the
host once instead of five times. The hrefs stay absolute, which is the half a fetcher uses;
the labels are paths, which is the half a person uses. `check-agents.mjs` enforces the
first and nothing enforces the second, so it is written down here instead.

#### 2. The registry — published 6 September 2026

`org.lunenburgbudgetproject/archive` 1.0.0, status `active`, listing
`https://lunenburgbudgetproject.org/mcp` as a `streamable-http` remote. Read it back rather
than trusting the success line:

    curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=lunenburg"

The namespace is the domain reversed. `BuildPermissions` grants
`org.lunenburgbudgetproject/*`, which is why `server.json` is named the way it is, and it
requires **domain-based authentication** — a DNS TXT record — which is also the honest
requirement for an archive claiming to be about one specific town.

**The key is at `mcp/mcp-registry-key.pem`, gitignored, and must stay that way.** It is the
proof of the domain. The public half is derived, never copied:

    openssl pkey -in mcp/mcp-registry-key.pem -pubout -outform DER | tail -c 32 | base64

**The record goes on the APEX, not under a selector.** MCP DNS auth works like SPF, not
like DKIM. The DKIM intuition is common enough that the registry probes for it and returns
a specific error — from `internal/api/handlers/v0/auth/dns.go`:

    var commonWrongSelectors = []string{"_mcp-auth", "_mcp-registry"}
    // MCP DNS auth uses the apex, like SPF -- see #385, #1103, #1126

So in Cloudflare: **type** `TXT`, **name** `@`, **content**
`v=MCPv1; k=ed25519; p=<public key>`, TTL auto, no proxy toggle on TXT. A record at
`_mcp.<domain>` would resolve, would be well-formed, and would never be looked at.

Two more read off the same source rather than assumed:

- The value must match `v=MCPv1;\s*k=([^;]+);\s*p=([A-Za-z0-9+/=]+)` (`common.go`), so the
  semicolons and the base64 are load-bearing and a trailing `=` is fine.
- The signed timestamp is checked to **±15 seconds**, so a drifting clock fails `login` with
  a message about the timestamp rather than about the record.

**How this was told wrong first.** The record location was given to TJ as `_mcp.` from
memory and was wrong. It was caught by reading the registry's source instead of the
assistant's recollection — which is `CLAUDE.md` rule 13 exactly: *something derived was
quoted as though it were observed.* There was a real thing underneath (selectors are how
DKIM works), which is why it survived one telling. **The check that a record is right is
never that it resolves.** Before publishing, all three of these were asserted:

    dig +short TXT <domain> @1.1.1.1  @8.8.8.8  @9.9.9.9     # all three agree
    # the record matches the registry's OWN regex, not one written from the prose
    # the p= in it equals the key derived from the private key on disk

#### What publishing cost, none of it findable from the error

- **The publisher is the GitHub release, not the npm package.** `npm view mcp-publisher`
  returns 0.4.2; the registry's own release is 1.8.1 and is the binary whose source is
  quoted above. Using the artifact from the repo you read is the whole point.
- **`--private-key` takes hex, not a PEM path.** Passing the path fails with
  `invalid hex private key format: encoding/hex: invalid byte: U+006D 'm'` — it is reading
  the filename as the key. The Ed25519 seed is the tail of the PKCS#8 DER, and belongs in a
  shell variable that is never echoed:

      openssl pkey -in mcp-registry-key.pem -outform DER | tail -c 32 | xxd -p -c 64

- **`description` is capped at 100 characters** and ours was 465 — a 422 quoting the whole
  paragraph back, with the cap named nowhere beforehand. The long form was not deleted but
  **moved** to the server's own `GET /mcp` body, which is where somebody asking what this is
  will look. The registry field is a label in a list.
- **The schema in a template goes stale.** `2025-09-29` published fine with a deprecation
  warning; `2025-12-11` is current and its changelog says *no changes required* — the only
  difference is URL template variables for multi-tenant remotes, which this does not use.

#### What being in the registry does NOT prove

- **The registry is a preview.** Its own README: *"this is still a preview release and
  breaking changes or data resets may occur."* A data reset would remove this entry and
  nothing here would notice. Nothing checks the registry entry on a schedule; if that
  matters later, it is a `check_` script that does not exist yet.
- **Being listed is not being read.** No client is known to consult the registry when
  answering an ordinary question. This buys eligibility, not traffic.
- **Still untested by a real client.** The server answers `tools/list` and `tools/call`
  correctly over the wire, which is not the same as an assistant choosing to use it. The
  unbiased way to find out is above: `wrangler tail`, and ask somebody an ordinary question.

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
- **Nothing watches the registry entry.** It was read back once, by hand, on the day it was
  published. The registry is a preview that says data resets may occur, so the entry can
  vanish silently — which is this workstream's own failure shape, pointed at itself.
- **The 429 body is Cloudflare's**, seventeen bytes reading `error code: 1015`. The free
  plan allows one rule and a ten-second period only, and the block page cannot be
  customised. Mitigated by saying what it means in `llms.txt` and in `/api/query`'s own
  help, before a caller ever hits it. Untested whether a rate limiting rule accepts
  `action_parameters.response` on this plan — worth one attempt.
- **The 107 questions are all schema-shaped.** Not one is phrased the way a resident would
  ask. *"Is the school budget growing faster than the town can pay for?"* is the register
  that is missing, and it is the register the site is for.

## What to do next, in order

1. **Run the two tests below.** Everything they need is live.
2. **Verify the domain in Google Search Console and Bing Webmaster Tools.** Ten minutes,
   and it is the only route to knowing what is indexed. Both are **apex TXT records too**,
   so add them as SEPARATE records — the apex now holds the MCP proof and editing it in
   place would revoke the domain claim.
3. **Add citizen-phrased questions to the bank**, mapped to the queries that answer them.
4. Consider whether a rate limiting rule can carry a custom JSON body on this plan.
5. **Markdown mirrors of the app's own pages.** Vercel's agent-readability guide
   (`vercel.com/kb/guide/make-your-site-readable-by-ai-agents`) recommends serving a
   `.md` twin of every page and advertising it with
   `<link rel="alternate" type="text/markdown">` plus `Vary: Accept`. This site has
   markdown for the ANALYSES but not for the eighteen app routes, which are where the
   argument actually lives. It is the largest remaining gap on that guide's list.

### The two tests, and why they are two

They ask different questions and mixing them answers neither.

**Test A — does an agent FIND it?** The unbiased one, and the one that matters.

- Start `cd mcp && npx wrangler tail lunenburg-mcp --format json` FIRST. Watching biases
  nothing; asking does.
- Give the agent an ordinary question in a resident's register — *"is the school budget
  growing faster than the town can pay for it?"* — and **do not name the site, the MCP
  server, the API or the archive.** Naming any of them makes the result worthless: the
  prompt then contains the answer.
- Afterwards ask only *how did you get that?* Not *did you use the MCP server*, which
  invites a reconstruction rather than a report.
- Read the outcome honestly: `tool <name> ok <ms>` lines arriving is the only positive
  evidence. An agent that quotes the site's prose did **not** use the tools, however right
  its answer is.

**Test B — does it WORK when connected?** Add
`https://lunenburgbudgetproject.org/mcp` as a remote MCP server in a client that supports
one, and ask the same question. This tests the eight tools, not discovery.

Most clients today do **not** consult the registry on their own — the entry buys
eligibility, and a person or a client pasting the URL is still the normal route. So a
failure of Test A with a success in Test B means the server is good and discovery is not
solved, which is the outcome to expect first and is worth stating plainly rather than
reading as the server being broken.

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
| an MCP server at a stable `/mcp` | **built, deployed, linked from the front page and published to the registry** |

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
