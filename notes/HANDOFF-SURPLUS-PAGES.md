# Handoff: the surplus pages, consolidated and made to mean something

Written 26 October 2026, at the end of a long session, for a FRESH one. TJ's ask, verbatim:

> *"I think we spawn a new session and review the surplus pages to see how we can consolidate,
> and better inform with insights and better page structure/format now that we're unlocked."*

and his frame for the whole day: *"we have a LOT of data spread out now and we need to
consolidate and organize better so people can more quickly find it."*

"Unlocked" is CLAUDE.md rule 7h: a page is not limited to finding, chart, facts, conclusions.
Read rule 7h and `notes/process/AUDIT-PASS.md` before touching anything.

---

## What to review: the FY2026 closeout shelf, /fy2026-closeout

16 topic pages in four groups, plus the hub. Registry: `scripts/topic_registry/fy2026_closeout.py`.
Regenerate this table rather than trusting it: the snippet at the bottom does.

| group | page | built by | opens on |
|---|---|---|---|
| (lead) | **fy2026-surplus-by-category** (START HERE, TJ: "the main school based surplus page") | build_fy2026_closeout_topics.py | $1,683,552 left on accounts under budget, $1,201,434 used by accounts over; net $482,118 |
| | fy2026-lines-over-budget (TJ: *"similarly seems useless"*) | same | 57 school accounts closed past budget; 4 in FY2025 |
| | fy2026-school-transfers | same | $394,929 in, $309,839 out, net $85,090 |
| | fy2025-school-surplus | same | FY2025 left $627,117, $23,231 more than the Committee was given |
| Surplus from the journal | surplus-bridge | build_journal_surplus_topics.py | $482,118 to $718,885 depending on $236,767 of open orders |
| | surplus-repeat-lines | same | 6 areas under every year FY2023-FY2026 |
| | budget-burndown | same | 40.2% of the budget left at end of March |
| | sped-burndown | same | circuit breaker paid $4,005 July-May, then $333,495 in June |
| | surplus-suggestions | same | many small leftovers, year after year |
| School lines | fy2026-tuition-lines | build_fy2026_closeout_topics.py | FY2027 budgets $700,142 where FY2026 spent $1,202,771 |
| | fy2026-paraprofessional-overrun | same | $208,082 over; $99,064 against no budget |
| | fy2026-psychologist-line | same | one psychologist account paid nothing |
| | special-education-transportation (home: Transportation) | build_transportation.py | |
| | fy2026-athletics-underspend (home: Athletics) | build_athletics_topics.py | |
| Town side | fy2026-town-unspent, fy2026-snow-and-reserve-fund, fy2026-school-retiree-insurance | build_fy2026_closeout_topics.py | |

Also UNLISTED long reports on the same money: `sources/analyses/fy26-school-surplus.md` and
`fy25-school-surplus.md` (built by `build_school_surplus.py --all`, verified by
`verify_school_surplus.py --all`). Decide whether they stay unlisted, become the hub's full
report, or are retired; do not leave three readings of one surplus.

**Already done today, do not redo:** `fy2026-school-surplus` and `fy2026-surplus-and-fy2027`
were folded into the hub (commit `7c348a12c`): the two-runs table (period 12 against period 13)
is the hub's table, the FY2027 comparison is a hub conclusion, and both addresses open the hub.

## The obvious overlaps, as a starting hypothesis (test them, do not assume them)

- **The $482,118 is the opening figure of at least four pages**: the hub, surplus-by-category,
  surplus-bridge, and (before today) the two folded pages. One page should own "how much was
  left and why"; the rest should link to it.
- **surplus-by-category and surplus-bridge** both decompose the same net figure, one by
  category from the period-13 report, one step by step from the journal. Two instruments, one
  question: probably one page with two views, or a bridge block on the category page.
- **lines-over-budget** (57 accounts) is the other half of surplus-by-category's
  $1,201,434. TJ called it useless; it is probably a section of the category page.
- **surplus-repeat-lines and fy2025-school-surplus** answer "does this happen every year". Could
  be one page, or a block on the lead page.
- **sped-burndown** is also on the Special education hub. Keep it where it explains something.

## THE "IMPLICATIONS" RULE: what exists, and what does not (TJ asked to confirm)

TJ, 24-25 October 2026: *"what does the fact mean or suggest? ... how does it impact decision
making or citizens or boards"* and *"put the conclusions as insights, following the 'what it
means' pattern so we dont put important metrics without an insight to understand them."*

**What is ENFORCED:** panels, chart and custom blocks refuse to build without `so=`
(`scripts/topic_blocks.py`, `_so`). Every block gets a "What it means".

**What EXISTS but is NOT enforced:** a conclusion's own meaning. `TP.conclusion(..., so=...)`
and `LD.conclusion(..., so=...)` take one, and `build_serf_topics.py` attaches them in bulk with
its `meanings()` helper. Nothing refuses a conclusion without one.

**Measured 26 October 2026: 30 of 941 conclusions on the site carry a meaning.** SERF 25 of 25,
the rest are the Circuit breaker page (SERF-built) and the FY2026 closeout hub's FY2027 line.
**Every surplus page above: 0.** It is not written in CLAUDE.md either, only in memory
(`convey-it-best-way`).

So for this review: give every conclusion on every page you touch a meaning, the SERF way, and
consider the ratchet that would make it stick: `TP.page` failing a conclusion with no `so` on a
list of shelves that have been converted, the list growing shelf by shelf (the reading-time
ratchet is the precedent). Propose it to TJ; do not turn it on site-wide in one go -- 911
conclusions would fail.

A meaning follows rule 8 (no "should", no charge, give credit) and rule 7 (a meaning is not a
cause; if it is our reading, say so).

## Tools added today that this work will want

- **Retiring a page**: remove it from its registry, delete its payload, and add
  `'old-id': 'new-id-or-hub-id'` to `TOPIC_MERGED` in `fy28/src/routes.ts`. The old address then
  opens the new page and the address bar moves. Then `build_topics_index.py`,
  `build_reports_index.py`, `build_agent_manifest.py`.
- **A page written by another shelf's builder**: `TOPIC_GENERATORS` in the registry; a builder's
  `MINE` should be "pages registered to me" (`gen == ...`), not "pages homed on my shelf".
- **A hub inside a shelf group**: a group may now list another hub's id (`topics.py`,
  `TopicLink.shelfEntry`). The SERF hub sits on Special education that way.
- **Grant names**: `journal.grant_program()` is the one naming for every page.

## Checks

    python3 scripts/build_fy2026_closeout_topics.py --check
    python3 scripts/build_journal_surplus_topics.py --check
    python3 scripts/verify_fy26_closeout.py
    python3 scripts/verify_fy26_closeout_town.py
    python3 scripts/verify_fy26_school_surplus.py
    python3 scripts/verify_journal_surplus_topics.py
    python3 scripts/verify_school_surplus.py --all
    bash scripts/check_phone_width.sh /fy2026-closeout <every page you change>

All of them passed at `7c348a12c`.

## Standing constraints (do not relearn these)

- **No `git push`** until the history rewrite (memory, open items 19 Oct).
- **Deploy only when TJ asks.** The auto-mode classifier also blocks `deploy_site.sh` from this
  agent; TJ runs `! bash scripts/deploy_site.sh` himself. Commits from 26 October are NOT live.
- **Other agents' uncommitted files are in this tree** (the 2021 minutes backlog: boards,
  recording-minutes, threads, feeds, official-votes, sources.json). Never `git checkout`, stash
  or commit them. `check_generated.py` fails ~20 checks on them; that is not yours.
- **The sitemap trap**: `build_sitemap.py` run in this tree drops ~106 /meeting-minutes URLs
  that the backlog state does not hold. Do not commit a regenerated sitemap whole; apply only
  your own page changes to the committed one (done that way in this session).
- Titles are 2-4 word nouns (`topics.py` checks). Findings are 110 characters. Every digit in
  prose is a registered figure.

## Regenerate the inventory

    python3 - <<'EOF'
    import json,sys; sys.path.insert(0,'scripts'); import topics as R
    for g,ids in R.category('fy2026-closeout')['groups']:
        print('##', g)
        for t in ids:
            d=json.load(open('fy28/public/data/topics/%s.json'%t)); cs=d.get('conclusions',[])
            print(' ', t, '|', R.TOPICS[t][2], '|', len(cs), 'concl,', sum(1 for x in cs if x.get('so')),
                  'with meaning |', d['finding']['text'][:100])
    EOF
