# Handoff: the surplus pages, consolidated and made to mean something

## DONE, 26 October 2026 (second session). Read this block first

**DEPLOYED 26 October 2026** (TJ asked), https://6c49d7a7.lunenburg-fy28.pages.dev, pushed at
c5e9b7266. Live pages checked by DOM dump: the hub, Surplus by category, Surplus by year, Year-end
tuition payment (every block), and both retired addresses forwarding. **The deploy skipped ONE
check, with TJ's approval:** `check_dist_complete.py` refused on 107 sitemap pages (2021
meeting-minutes and board "time" pages) that the prerender does not build -- the minutes
backlog's work in progress (`process_meeting.py --until-usage`, PID 34340, running). None was
prerendered live before the deploy either (the live site served them as the app shell), so
nothing was removed. Every other step of deploy_site.sh ran: freshness, check_prerender,
takedown --check, sync_derived push/check/stage. Fixing that gap is the backlog's, not this shelf's.

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

## LEAD OF "WHY IT WAS LEFT": the prepayment moves the comparison (TJ, 26 Oct 2026: "right?")

Take the $189,276.75 out of FY2026's spending and FY2026 left MORE than FY2025 on every single
footing. Only the as-printed pair, which mixes footings AND counts an FY2027 bill, shows less.

| | FY2025 | FY2026 |
|---|---:|---:|
| counting orders still owed | $554,945 | $671,395 |
| closed-report footing (orders not counted) | $627,117 | up to $908,162 |
| as each report prints it (the July comparison) | $627,117 | $482,118 |

- The July 2026 minutes: FY2026 would close "well below" the ~$600,000 returned from FY2025.
- Sequence (journal 2026/12/000692 and 2026/12/001152): 29 June, $333,494.89 of collaborative
  tuition reclassed from the general fund to the circuit breaker (2640); 30 June, the general
  fund pays nine `27L2KEY11-19` invoices, $189,276.75. A link between the two is a HYPOTHESIS.
- WORDING (rule 7): "carries FY2027 invoice numbers and FY2027's rate" is measured; "pays for
  FY2027's first quarter" is OUR READING -- four clues (prefix pattern, a fifth round in a
  four-quarter year, the new $19,885.50 rate, 30 June timing), no service dates. Settles it:
  FLLAC's invoice 27L2KEY11; the FY2027 journal (no Q1 FLLAC payment in its autumn); a s.71D vote.
- SAID ON THE RECORD (machine captions -- a finding aid; check the video before quoting; captions
  name no speakers):
  - School Committee, 4 Feb 2026, https://www.youtube.com/watch?v=HsjpFotE9hc&t=3700s (1:01:40-
    1:04:40). A speaker addressed as "Chris" (McNamara, Business Administrator, is listed as a
    guest in the minutes): "had I been here back in 2025 ... what would you have done with the
    $556,000? ... one of the things you can do towards the end is prepay special ed tuitions." The
    speaker he answers: "if it's spent by the school district before it gets there [free cash],
    that there is an open transparent conversation around it." The posted minutes (7634) do not
    record the exchange. So the practice was named in public five months before it was used.
    TJ confirmed (26 Oct 2026, from knowing the meeting) that the speaker is Chris McNamara. Still
    verify against the video before quoting; the page names him by role, as the minutes do.
  - Finance Committee, 22 Oct 2026, https://www.youtube.com/watch?v=wQWhIwYOc9o&t=6440s (1:47:20-
    1:51:20), the district's circuit breaker slides: "We are allowed to prepay the 1st quarter of
    out of district tuition from circuit Breaker accounts"; eligible students 9 (FY2025) -> 13
    (FY2026). The FY2026 GENERAL FUND prepayment is not mentioned anywhere in the captions.
- NOT ANNOUNCED IN JUNE OR JULY (checked 26 Oct 2026). Every June 2026 meeting of the School
  Committee (3, 24 June), Finance Committee (11 June) and Select Board (2, 15, 16, 30 June), minutes
  AND captions, plus School Committee 29 July: no mention of prepaying tuition, FY2027 tuition,
  FLLAC, or moving tuition onto the circuit breaker. What WAS presented:
  - SC 24 June (captions 35:00-42:00): four line-item transfers (salary reserve $90,769.62 to 13
    deficit salary lines; athletic transportation to dues $9,670.45; equipment $1,316.94; a salary
    to extended day $35,400/$34,500, a transposition). Carry-forward encumbrances voted from a sheet
    "not in your packet"; the largest named is June transportation. The prepayment is not an
    encumbrance (paid 30 June, API) and was not on either list as described.
  - SC 29 July (captions 22:10-29:20): year-end transfers "just to cover overages"; includes
    $81,075.96 from the HS special education resource room teacher -- "Was that an unfilled
    position?" "a leave of absence" (USE for the vacancy gap). No tuition item.
  - FinCom 11 June: year-end transfer documents "were not provided". SB 16 June: town year-end
    transfers deferred to July.
  - No s.71D advance-tuition vote in any of them. Not held: the 24 June encumbrance sheet, the
    meeting packets, and the 2 and 9 September 2026 School Committee "FY26 Year End Budget review".
- Rule 8: lawful (c.71 s.71D; DLS). The finding is the EFFECT on the figure the Committee heard
  and on what lapses to free cash, never intent.
- Still to cite in the build: the circuit breaker carry-forward rule; c.71 s.34 (bottom-line
  appropriation), which frames the whole section: transfers moved ~$277k of $1,201,434 overruns
  ($394,929 in, $117,626 of it to accounts that ended under); ~$924k was absorbed unvoted.

## "Why it was left" -- BUILT on the hub, 26 October 2026 (late evening). Not deployed

A `TB.checks` block on /fy2026-closeout (place `body`), built by `why_it_was_left()` in
`build_fy2026_closeout_topics.py` from build_school_surplus's category table, so it cannot
disagree with Surplus by category. Six rows, columns Left money / Used money / Same every year.
FY2026, counting orders still owed, net $482,118:

| row | measured |
|---|---|
| A federal grant paid a private placement | private tuition left $522,629 of $988,630; May Institute, $318,255 from the GF in FY2025, $287,108 from the IDEA grant (fund 2814) in FY2026 |
| Collaborative tuition ran past budget | $434,108, no transfer in; $189,277 of it the FY2027-numbered invoices |
| Salary lines, taken together | $192,211 left net, after aides (function 2330) ran $210,082 past |
| Building upkeep and supplies | $267,795 left |
| Health insurance and benefits | $107,003 left; ran $197,227 / $123,307 OVER in FY2023 / FY2024 |
| Therapy, buses and electricity | $189,610 used, net |

- **New evidence on the record:** School Committee, 16 Sep 2026 (captions, ~12:09-13:00,
  https://www.youtube.com/watch?v=XY8Ru12S9Xg&t=729s): "it looks like that large unexpended funds is
  in our private school tuitions" and "we're taking certain tuitions out of the grants". Speaker
  not identified from the captions. Consistent with the measured switch; says nothing about
  whether the FY2026 BUDGET expected it.
- **New money-gaps row** (last row): why the grant paid May Institute, and whether the budget
  expected it -- closes: the FY2026 IDEA (240) grant application and DESE-approved budget.
  The thrift (218) and vacancy (219) rows already carried the remedies item 3 and 4 below asked for.
- **Verified by a different route:** `verify_journal_surplus_topics.py` `why_left()` recomputes
  every dollar in the block from the period-13 spreadsheet and the raw journal CSV, set-equal
  both ways. Power-tested: one digit changed in the payload fails it.
- **NOT done:** the hub ladder is still at its 6-conclusion limit and carries no root-cause
  conclusion; the obvious swap is the FY2027-level-service one, TJ's call. Not built or rendered
  (no `npm run build:site`); not deployed. Candidate 1's tuition-by-placement-type page is still
  to build.

### The candidates as originally scoped (TJ, 26 October 2026, evening)

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
   - **CORRECTED (TJ challenged the "doubling").** Group by the school year an invoice BILLS,
     read off FLLAC's invoice numbers (`25L2KEY..` = FY2025, `26..`, `27..`; our reading of the
     numbering, corroborated by a new quarterly rate in each prefix: $18,482.40, $19,255.50,
     $19,885.50). Collaborative tuition by year billed: ~$457,677 FY2025 -> ~$851,852 FY2026
     (+86%). Invoices per quarter 5,5,6,6 -> 8,8,10,9 (an invoice is not a child -- rule 7);
     rate +4.2%. **$189,276.75 paid 30 June 2026 from FY2026 GF money bills FY2027** (nine
     `27L2KEY1x` invoices, quarter one). So of the $434,108 collaborative overrun, $189,277 is
     next year's tuition paid early, and FY2027's $700,142 starts with its first quarter paid.
     No other payee spelling in any fund; FY2025's $445,631 (on 2640's private account) is
     already counted. The cost rise is real but ~$394k, not $524k.
   - **The prepayment is LAWFUL** -- G.L. c. 71 s. 71D (a school committee may approve tuition up
     to three months in advance) and c. 40 s. 4E; DLS "Prepayment from Prior Fiscal Year Funds"
     uses this exact case (a July-September bill due 30 June). Rule 8: a tool that moves money
     between years, not a defect. Measured: FY2026 prepaid $189,276.75 -- the ONLY prepayment
     visible FY2023-FY2026. Every late-June tuition payment in every year and fund was read: the
     rest are current monthly bills ("MAY 2024", "JUNE 2024"). CORRECTION: the FY2025 "26L2KEY46"
     ($29,571.84, paid 29 April 2025, 2640) is almost certainly FY2025 quarter 4 with a mistyped
     prefix -- KEY46 is the one number missing from FY2025's KEY41-47 run. Treat it as FY2025.
     Private-school invoice numbers carry no year, so a private prepayment cannot be excluded by
     numbering; the amounts are one month's size. Open: the s. 71D approval -- no vote found in School Committee
     minutes April-July 2026; 24 June 2026 minutes say carryover POs were "already discussed ...
     with the encumbrances". Finance Committee 22 Oct 2026 (captions, 1:49:50): "We are allowed
     to prepay the 1st quarter of out of district tuition from circuit Breaker accounts" -- this
     one was paid from the GENERAL FUND. Without it, FY2026 leaves $189,277 more.
   - Build: PARTLY DONE. The prepayment has its page, `fy2026-tuition-paid-early` ("Year-end
     tuition payment", commit fa1c0e808, build_journal_surplus_topics.py). Still to do: tuition by
     placement type and by fund, replacing the "Tuition at year end" framing.
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

| group | page | built by | concl. with meaning | opens on |
|---|---|---|---|---|
| (lead) | **fy2026-surplus-by-category** (START HERE, TJ: "the main school based surplus page") | build_fy2026_closeout_topics.py | 4/4 | $1,683,552 left on accounts under budget, $1,201,434 used by accounts over; net $482,118 |
| | surplus-bridge ("Surplus by year") | build_journal_surplus_topics.py | 4/4 | printed, FY2026 left $144,999 less than FY2025; $72,827 less on one footing |
| | fy2026-tuition-paid-early ("Year-end tuition payment") | same | 4/4 | $189,277 paid 30 June 2026 on FLLAC invoices numbered for FY2027 |
| | surplus-repeat-lines ("Repeat underspending") | same | 4/4 | 6 areas under every year FY2023-FY2026 |
| | surplus-suggestions | same | 4/4 | many small leftovers, year after year |
| Through the year | budget-burndown | same | 4/4 | 40.2% of the budget left at end of March |
| | sped-burndown | same | 4/4 | circuit breaker paid $4,005 July-May, then $333,495 in June |
| | fy2026-school-transfers | build_fy2026_closeout_topics.py | 4/4 | $394,929 in, $309,839 out, net $85,090 |
| School lines | fy2026-tuition-lines | same | 3/3 | FY2027 budgets $700,142 where FY2026 spent $1,202,771 |
| | fy2026-paraprofessional-overrun | same | 4/4 | $208,082 over; $99,064 against no budget |
| | fy2026-psychologist-line | same | 4/4 | one psychologist account paid nothing |
| | special-education-transportation (home: Transportation) | build_transportation.py | **0/2** | |
| | fy2026-athletics-underspend (home: Athletics) | build_athletics_topics.py | **0/3** | |
| Town side | fy2026-town-unspent, fy2026-snow-and-reserve-fund, fy2026-school-retiree-insurance | build_fy2026_closeout_topics.py | all | |

Regenerated 26 October 2026 (evening). Retired: `fy2026-lines-over-budget` (into Surplus by
category) and `fy2025-school-surplus` (into Surplus by year).

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

## TJ's request for /school-all-funds (26 Oct 2026): "timing of money in"

*"timing of money in. So when we get money from all the various ... the tax money from the
town, all the grants, the governor's budget, when that money gets injected ... And if there's
caveats of when it needs to be spent."* For the whole-school-budget review (queue #3), not this
shelf. A timeline per source: when it arrives, and the rule on when it must be spent.
- Circuit breaker, measured (fund 2640 CRP lines): quarterly installments -- FY2023 Nov, Jan,
  Apr, Jun; FY2024 Oct, Jan, Apr (4th arrived Jul 2024); FY2025 Jul, Oct, Dec, Apr, Jun; FY2026
  Jul, Sep, Dec, then none posted. DESE FAQ q10: spend in the year received or the next.
  OPEN: DESE prints $579,142 for FY2026; fund 2640 booked $285,004 of it (Sep, Dec); $294,138 (spring and June installments) unlocated.
- Federal grants (IDEA #240 etc.): a new fund each year (2758, 2813, 2814); their own periods.
- The town appropriation, Chapter 70 / cherry sheet, revolving funds: to be read.

## Open, elsewhere (not this review's job; do not lose them)

- **GitHub Support ticket 4909191** (purge the pre-rewrite commits): `notes/HANDOFF-HISTORY-REWRITE.md`.
  Done when the old commit URL there stops answering 200.
- **Work-off page** (`/homes-and-taxes/senior-tax-work-off`): TJ to decide the opening line,
  "16 completed 2010" vs "6 took part 2025" (close but different measures).
- **School grants and aid** (`/school-all-funds/school-money-in`): fees, lunch and gifts sit
  awkwardly there now; candidate to move to a revolving-funds page (the all-funds review, queue #3).
- **Two retired addresses** still served stale by the week-long edge cache until ~1-2 November:
  `/special-education-reserve/surprises-and-state-aid`, `/fy2026-closeout/fy2026-school-surplus`.
- **Gaps registered 26 October**: the FY2026 circuit breaker: $294,138 (two installments) not booked in fund 2640 -- corrected from $253,172, which netted FY2025's $40,966 supplemental; the
  worksheet behind the budget's 75% circuit breaker line; work-off hours per department.
- **Cleanup**: `read_allocations` (build_school_all_funds) and `read_idea` (build_serf_topics) read
  the same DESE file twice; make one shared reader.
- **Uncommitted files in the tree belong to the minutes backlog run** (2021 minutes, boards,
  threads, feeds, official-votes, sources.json). Never commit, checkout or stash them.
