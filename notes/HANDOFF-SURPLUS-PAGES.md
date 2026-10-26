# Handoff: the surplus pages, consolidated and made to mean something

## DONE, 26 October 2026 (second session). Read this block first

**Committed locally, NOT deployed** (rule 10: TJ asks). Build, then `bash scripts/deploy_site.sh`.

1. **The footing defect, fixed on the hub and given a page.** A closed year's close (`YEC`) zeroes
   the orders it still owes and re-opens them next July as carried-forward budget, so FY2025's
   period-13 report prints what was left BEFORE its $72,172 of open orders. FY2026's report was
   run before its close and counts its $236,767 as spent. The hub, and the July 2026 minutes'
   comparison with "the approximately $600,000", set the two side by side as printed. On one
   footing: FY2025 $554,945 vs FY2026 $482,118 (owed counted, TJ's "spent" rule); or $627,117 vs
   up to $718,885 (the closed reports' footing). FY2023 and FY2024 left ~$32,000 each on the
   owed footing. Verified by a second route: `verify_journal_surplus_topics.py` recomputes the
   owed footing from next July's `SOY` lines, not the `YEC` lines the generator reads.
2. **Nine school-surplus pages to seven.** `fy2026-lines-over-budget` -> Surplus by category (the
   "over" half of its own net; two-panel block + accounts-over-by-year chart). `fy2025-school-surplus`
   -> `surplus-bridge`, retitled **Surplus by year** (signature: four years, both footings; the
   bridge is a body chart block; opens on the July quote it tests). Both in `TOPIC_MERGED`.
   `surplus-repeat-lines` retitled **Repeat underspending**. Groups now by reader question:
   lead (category, year, repeat, suggestions) / Through the year (burndown, SpEd burndown,
   transfers) / School lines / Town side.
3. **Every conclusion on the 14 pages these two builders write, and the hub, has a meaning.**
   `topic.MEANINGS_REQUIRED = ('fy2026-closeout',)` is the ratchet: a page homed on a listed
   shelf, or its hub, fails without `so=`. Add a shelf when converted; never remove one.
4. The two long UNLISTED reports stay unlisted (documents of record behind the hub's charts;
   TJ: no full reports promoted). Their prose already gives FY2026 as a $482,118-$718,885 range.

**Still open:** `special-education-transportation` and `fy2026-athletics-underspend` (homed on
other shelves, other builders) have no meanings yet -- do them with Athletics / Transportation.
`sources/data/threads.csv` row `fy25-school-surplus` still links the old address (redirects
fine); `threads.json` is dirty from the minutes backlog, so it was not regenerated.
`fy28/public/data/reports.json` regenerates with the backlog's byte counts; not committed.

---

**START HERE (fresh session, 26 October 2026 evening):** load the `building-a-page` skill, then
read this file top to bottom. Everything else from the long 26 October session is committed,
pushed and live; nothing of it is pending except what is listed under "Open, elsewhere" below.

Written 26 October 2026, at the end of a long session, for a FRESH one. TJ's ask, verbatim:

> *"I think we spawn a new session and review the surplus pages to see how we can consolidate,
> and better inform with insights and better page structure/format now that we're unlocked."*

and his frame for the whole day: *"we have a LOT of data spread out now and we need to
consolidate and organize better so people can more quickly find it."*

"Unlocked" is CLAUDE.md rule 7h: a page is not limited to finding, chart, facts, conclusions.
Read rule 7h and `notes/process/AUDIT-PASS.md` before touching anything.

---

## NEXT: "Why it was left" (TJ, 26 October 2026, evening) -- build in a FRESH session

TJ: the candidate causes are "really huge potential conclusions" and belong on the hub, in a
"Why it was left" section. Order by evidence; each candidate: what the ledger MEASURES, what it
cannot tell apart, the document that settles the rest (a money-gaps row). Rule 7: no cause stated.

1. **Tuition routing -- measured, lead with it.** Placement payees across EVERY fund (journal,
   tuition accounts, payees sorted by name -- ours): collaborative (FLLAC, CAPS) $197,445 /
   $290,003 / $487,249 / $1,011,557 FY2023-FY2026; private $602,270 / $764,801 / $718,700 /
   $747,059 ($459,951 GF + $287,108 from fund 2814 "FY'26 #240", May Institute, Oct-Jun).
   - The #240 grant paid NO placement in FY2023-FY2025 (funds 2758, 2813 exist, pay none); the
     circuit breaker (2640) was the other payer. FY2025: $445,631 to FLLAC posted to 2640's
     PRIVATE tuition account. FY2023/FY2024: GF collaborative line paid exactly its budget.
   - Plan (FY2026 budget book, final-fy26-sc-approved-budget...txt lines 297-301): private
     $988,630; collaborative $782,867 less circuit breaker $480,204 = $302,663 net. No grant
     offset planned on private tuition IN THE BOOK (grant application not read -- a gap).
   - Private: $988,630 set; all-fund private cost $747,059 -> $241,571 above cost even had the GF
     paid all of it; the grant took $287,108 more; line closed $522,629 under, NO transfer out.
   - Collaborative: cost $228,690 above the $782,867 gross plan; circuit breaker paid $333,495,
     $146,709 below the $480,204 planned; plus $58,708 still owed = $434,108 over, NO transfer in.
   - So the private leftover sat unused and, inside one appropriation, covered the collaborative
     overrun; tuition nets to $88,522 left. FY2027 budgets $700,142 for both lines (side by side
     with FY2026's $1,202,771 GF; never differenced -- rule 1).
   - Build: a tuition page on this shelf (by line AND by placement type, by fund), replacing the
     "Tuition at year end" framing; a verifier reading the journal raw.
2. **Building jobs -- measured** (/buildings-and-grounds/upkeep-skipped, upkeep-surplus-every-dollar):
   10 usual payees paid under half, 5 nothing; $67,393 of orders released unpaid.
3. **Spending slowed from February -- measured** (budget-burndown). Whether anyone DECIDED to hold
   spending is the gap: fix the "thrift" money-gaps row, whose remedy (the journal by month) is held.
4. **Vacancies -- gap.** Cannot look back; the open-positions list tracks forward from FY2027.
   Fix the gap row: remedy = FY2026 position-control roster (back) + the tracker (forward).
5. **Lines budgeted above cost -- measured pattern** (Repeat underspending), cause not.

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

- **Push: no hold** (the history rewrite was done 26 October; check `## Push holds` in CLAUDE.md
  before any push). Push `main` only, never `--mirror`: two local branches are on the old history.
- **Deploy only when TJ asks.** The agent CAN run it: `bash scripts/deploy_site.sh` on its own
  (a combined build-and-deploy command was once refused by the auto-mode classifier). Build first
  (`cd fy28 && npm run build:site`, ~15 min, in the background).
- **After a deploy, check the page RENDERS, not only that files match.** On 26 October three
  trend charts sat in a payload, hashed MATCH live, and were never drawn (blocks placed at
  `also2` with one `also` chart -- topic.py now refuses that). Dump the live DOM
  (`chrome --headless=new --dump-dom <url>`) and grep for each chart title, or screenshot it.
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

## Open, elsewhere (not this review's job; do not lose them)

- **GitHub Support ticket 4909191** (purge the pre-rewrite commits): `notes/HANDOFF-HISTORY-REWRITE.md`.
  Done when the old commit URL there stops answering 200.
- **Work-off page** (`/homes-and-taxes/senior-tax-work-off`): TJ to decide the opening line,
  "16 completed 2010" vs "6 took part 2025" (close but different measures).
- **School grants and aid** (`/school-all-funds/school-money-in`): fees, lunch and gifts sit
  awkwardly there now; candidate to move to a revolving-funds page (the all-funds review, queue #3).
- **Two retired addresses** still served stale by the week-long edge cache until ~1-2 November:
  `/special-education-reserve/surprises-and-state-aid`, `/fy2026-closeout/fy2026-school-surplus`.
- **Gaps registered 26 October**: the FY2026 circuit breaker $253,172 not booked in fund 2640; the
  worksheet behind the budget's 75% circuit breaker line; work-off hours per department.
- **Cleanup**: `read_allocations` (build_school_all_funds) and `read_idea` (build_serf_topics) read
  the same DESE file twice; make one shared reader.
- **Uncommitted files in the tree belong to the minutes backlog run** (2021 minutes, boards,
  threads, feeds, official-votes, sources.json). Never commit, checkout or stash them.
