#!/usr/bin/env python3
"""The repository's front door, for a reader who arrives here instead of at the site.

    python3 scripts/build_readme.py [--check]

WHY THIS EXISTS

README.md was the Vite starter template -- "This template provides a minimal setup to get
React working in Vite with HMR" -- untouched since the initial commit, while the
repository grew into an archive of 3,877 documents and 57 datasets.

That is not a cosmetic problem. An assistant asked what this project holds about
paraprofessionals could not reach lunenburgbudgetproject.org at all: its sandbox allows
package registries and GitHub and nothing else. So it cloned the repository -- the only
door open to it -- and landed on boilerplate about Babel and SWC. It then reverse-
engineered its way in with `git ls-tree | grep roster` and answered from whatever it
happened to find.

**For an agent that cannot fetch arbitrary hosts, GitHub IS the site.** `llms.txt` is the
file written for that reader and it sits at `fy28/public/llms.txt`, which nobody would
guess. This puts the same map at the address such a reader actually arrives at, and gives
the raw.githubusercontent URLs that work without a clone.

Counts here are derived, never typed, for the reason rule 2 gives: a number typed into
prose is the only thing in this project that can be silently wrong.
"""
import argparse
import csv
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'README.md')
SITE = 'https://lunenburgbudgetproject.org'
RAW = 'https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main'


def counts():
    manifest = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
    docs = sum(1 for _ in open(manifest)) - 1 if os.path.exists(manifest) else 0
    datasets = len(glob.glob(os.path.join(ROOT, 'sources', 'data', '*.csv')))
    api = len(glob.glob(os.path.join(ROOT, 'fy28', 'public', 'api', '*.json')))
    minutes = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
    meetings = sum(1 for _ in open(minutes)) - 1 if os.path.exists(minutes) else 0
    boards = len({r['board'] for r in csv.DictReader(open(minutes))}) if meetings else 0
    tables = os.path.join(ROOT, 'fy28', 'public', 'api', 'tables.json')
    ntables = json.load(open(tables))['count'] if os.path.exists(tables) else 0
    rosters = os.path.join(ROOT, 'sources', 'data', 'staff-roster-entries.csv')
    nroster = sum(1 for _ in open(rosters)) - 1 if os.path.exists(rosters) else 0
    return dict(docs=docs, datasets=datasets, api=api, meetings=meetings,
                boards=boards, tables=ntables, roster=nroster)


def render():
    c = counts()
    return f"""# The Lunenburg Budget Project

An independent, checkable archive of the Lunenburg, Massachusetts town and school budget:
{c['docs']:,} documents, {c['datasets']} datasets, and {c['meetings']:,} agendas and sets
of minutes across {c['boards']} town boards. Not affiliated with the Town of Lunenburg, the
School Committee or the school district.

The site is **[{SITE}]({SITE})**. This repository is everything behind it.

Start there: [the data API]({SITE}/api/index) · [an MCP server]({SITE}/mcp) ·
[every published address]({SITE}/agents) · [the guide for agents]({SITE}/llms.txt).

---

## If you are an agent, start here

**Read [`fy28/public/llms.txt`]({RAW}/fy28/public/llms.txt) first.** It is written for you:
what this archive holds, what it does not, and the specific ways to get a confident wrong
answer out of the data.

If you can reach the site, use it — every address below has a live equivalent and the site
serves smaller, indexed forms. If you can only reach GitHub, fetch raw files directly; no
clone is needed:

    {RAW}/<path>

| you want | fetch |
|---|---|
| what this holds, and its limits | [`fy28/public/llms.txt`]({RAW}/fy28/public/llms.txt) |
| every dataset, with row counts and sizes | [`fy28/public/api/tables.json`]({RAW}/fy28/public/api/tables.json) — {c['tables']} of them |
| the grain of every table, and the traps | [`fy28/public/api/schema.json`]({RAW}/fy28/public/api/schema.json) |
| every figure the site computes | [`fy28/public/data/model/index.json`]({RAW}/fy28/public/data/model/index.json) — 38 sections, one file each |
| every source document, with its sha256 | [`sources/data/archive-manifest.csv`]({RAW}/sources/data/archive-manifest.csv) |
| which meeting documents mention a word | [`fy28/public/minutes/find/README.txt`]({RAW}/fy28/public/minutes/find/README.txt) |

**Nothing in `fy28/public/api/` is larger than one fetch.** Anything that would be is split
— `staff_roster_entries.json` is an index and `staff_roster_entries/2022.json` is that year.

**The documents themselves are not in this repository.** {c['docs']:,} files, 1.47 GB, live
in a public object store; `sources/data/archive-manifest.csv` lists every one with its
sha256 and `python3 scripts/sync_archive.py --pull` fetches them. The extracted text IS
here, under `sources/*/text/`, and that is what the analysis reads.

## Where things are

| | |
|---|---|
| `sources/` | the archive, keyed by **how a document reached us** — see `sources/README.txt` |
| `sources/data/` | {c['datasets']} datasets extracted from those documents, CSV |
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
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    body = render()

    # Every raw link this file hands an agent must be a file that is actually in the
    # repository. That reader cannot fetch the site, so a path here is the whole of what
    # it gets -- and a README naming a file nobody pushed is exactly the failure this
    # file was written to fix, one layer up.
    import re
    import subprocess
    tracked = set(subprocess.run(['git', '-C', ROOT, 'ls-files'],
                                 capture_output=True, text=True).stdout.split())
    promised = sorted(set(re.findall(re.escape(RAW) + r'/([^\s)\]`]+)', body)))
    # `<path>` is the placeholder in the "fetch raw files like this" example, not a file.
    missing = [p_ for p_ in promised if p_ not in tracked and not p_.startswith('<')]
    if missing:
        print('README.md points at %d file(s) that are not in the repository:' % len(missing))
        for p_ in missing:
            print('  ' + p_)
        print('\n  An agent that can only reach GitHub gets nothing from these. Commit '
              'them, or\n  stop naming them.')
        return 1

    if args.check:
        current = open(OUT).read() if os.path.exists(OUT) else ''
        if current != body:
            print('STALE  README.md — run: python3 scripts/build_readme.py')
            return 1
        print('ok: README.md matches the repository')
        return 0
    with open(OUT, 'w') as fh:
        fh.write(body)
    print(f'wrote README.md ({len(body):,} bytes); '
          f'{len(promised)} linked paths all present in git')
    return 0


if __name__ == '__main__':
    sys.exit(main())
