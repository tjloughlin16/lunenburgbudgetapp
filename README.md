# The Lunenburg Budget Project

An independent, checkable archive of the Lunenburg, Massachusetts town and school budget:
3,877 documents, 62 datasets, and 1,422 agendas and sets
of minutes across 40 town boards. Not affiliated with the Town of Lunenburg, the
School Committee or the school district.

The site is **[https://lunenburgbudgetproject.org](https://lunenburgbudgetproject.org)**. This repository is everything behind it.

Start there: [the data API](https://lunenburgbudgetproject.org/api/index) · [an MCP server](https://lunenburgbudgetproject.org/mcp) ·
[every published address](https://lunenburgbudgetproject.org/agents) · [the guide for agents](https://lunenburgbudgetproject.org/llms.txt).

---

## If you are an agent, start here

**Read [`fy28/public/llms.txt`](https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/fy28/public/llms.txt) first.** It is written for you:
what this archive holds, what it does not, and the specific ways to get a confident wrong
answer out of the data.

If you can reach the site, use it — every address below has a live equivalent and the site
serves smaller, indexed forms. If you can only reach GitHub, fetch raw files directly; no
clone is needed:

    https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/<path>

| you want | fetch |
|---|---|
| what this holds, and its limits | [`fy28/public/llms.txt`](https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/fy28/public/llms.txt) |
| every dataset, with row counts and sizes | [`fy28/public/api/tables.json`](https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/fy28/public/api/tables.json) — 53 of them |
| the grain of every table, and the traps | [`fy28/public/api/schema.json`](https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/fy28/public/api/schema.json) |
| every figure the site computes | [`fy28/public/data/model/index.json`](https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/fy28/public/data/model/index.json) — 38 sections, one file each |
| every source document, with its sha256 | [`sources/data/archive-manifest.csv`](https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/sources/data/archive-manifest.csv) |
| which meeting documents mention a word | [`fy28/public/minutes/find/README.txt`](https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/fy28/public/minutes/find/README.txt) |

**Nothing in `fy28/public/api/` is larger than one fetch.** Anything that would be is split
— `staff_roster_entries.json` is an index and `staff_roster_entries/2022.json` is that year.

**The documents themselves are not in this repository.** 3,877 files, 1.47 GB, live
in a public object store; `sources/data/archive-manifest.csv` lists every one with its
sha256 and `python3 scripts/sync_archive.py --pull` fetches them. The extracted text IS
here, under `sources/*/text/`, and that is what the analysis reads.

## Where things are

| | |
|---|---|
| `sources/` | the archive, keyed by **how a document reached us** — see `sources/README.txt` |
| `sources/data/` | 62 datasets extracted from those documents, CSV |
| `sources/analyses/` | the written analyses, each with a verifier script |
| `model/` | the projection — `python3 model/export.py` writes `fy28/src/data/model.json` |
| `scripts/` | extraction, verification and publishing |
| `fy28/` | the site: React app, Cloudflare Pages Functions, and everything published |
| `notes/` | working notes; `notes/reference/` is generated |
| `plans/` | what is being built and why |

## The rules this project works under

`CLAUDE.md` carries them in full and each one exists because it was learned by getting it
wrong here. The four that matter most to anybody reading the data:

1. **Never mix budgets with actuals in one calculation.** They differ by up to 59% on some
   lines, and a growth rate measured from one to the other is partly growth and partly the
   step between them.
2. **A budget line is NET, and it is dollars.** It is what the town must raise after
   grants, fees and state aid — not what the thing costs, and never a count of people.
3. **Only facts are stated as facts.** A number computed from the data is a fact; an
   explanation for why it moved is a hypothesis, and it is labelled as one.
4. **Every figure is interpolated from the model, never typed into prose.** Including the
   counts in this file.

## Running it

    npm install --prefix fy28
    python3 scripts/sync_archive.py --pull      # the documents; the manifest says what
    python3 model/export.py                     # -> fy28/src/data/model.json
    npm run --prefix fy28 build:site            # -> fy28/dist

`CLAUDE.md` lists every check. The ones that guard what this file describes:

    python3 scripts/build_readme.py --check       # this file, against the repository
    python3 scripts/build_api.py                  # every dataset, fetchable
    node fy28/scripts/check-agents.mjs            # every advertised URL answers, and can be read
    python3 scripts/check_archive_storage.py      # the archive against its manifest

---

*Generated by `scripts/build_readme.py`. Edit that, not this.*
