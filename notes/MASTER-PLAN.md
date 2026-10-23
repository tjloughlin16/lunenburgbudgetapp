# Master plan — 22 October 2026

ONE list. It compiles TJ's 22 October brief, `QUEUE.md`, `FEEDBACK-QUEUE.md`, `DATA-TO-INGEST.md`,
every `HANDOFF-*.md` and the open-items memories. Where this disagrees with an older file on
ORDER, this wins; the older files keep their detail and their reasoning. Items carry the file
they came from so the detail is one click away.

**The first goal:** answer a board member's open question on the special education overruns.

---

## What changed what is possible (checked 22 Oct, not assumed)

- **The school journal is PUBLISHED**, not held (`2ee126b2f`; `redactions.csv:75` withholds only
  the raw PDF). `sources/data/munis-school-journal.csv`: 49,043 lines, every school account,
  FY2023 p0 to FY2026 p13, 93 funds -- general fund, revolving 1300-1315, lunch 2200, circuit
  breaker 2640, ~60 grant funds. So "what is spent from outside the general fund, on what" is
  answerable for four years, from the books. `HANDOFF-MUNIS-JOURNAL.md:44-56` saying "not
  committed" is stale.
- **Function codes on grant spending: partly.** FY2022-FY2024 IDEA funds (2785, 2791, 2758) post to
  real functions (2300, 2400). **FY2025 and FY2026 IDEA (2813, 2814) post to 0000 and 2000** --
  placeholders, so from FY2025 on the books do not say which line a grant paid for. Circuit breaker
  (2640) posts to 9300/9400/2110. That is a finding in itself and a `money-gaps` row (rule 7c).
- **Each year's IDEA grant is its own town fund** (2785 "FY22 #240" ... 2814 "FY'26 #240"); the DESE
  code is in the NAME. `journal.grant_code()` already parses it (`scripts/journal.py:206`).
- **DESE serves every district at once:** `entitlement-allocation.aspx?view=code&fy=<YYYY>&code=<4-digit
  fund>` -- 20 fund codes x FY2017-FY2027. No printed total on that view, so the check must be a
  different one (sum by district vs the per-district view for Lunenburg and a sample).
- **DESE's open-grants list is a plain table** (`/grants/grants.aspx`): fund code, name, posted, due,
  type (competitive 29, continuation 22, targeted 16, entitlement 12...), unit, contact.
  Eligibility is on each `/grants/2027/<code>/` page. **It is current-only, no history** -- so the
  only history of it will be our snapshots, which is the reason to start fetching it now.
- **Deploy is blocked**: Cloudflare Pages' 20,000-file limit (`HANDOFF-SOCIAL-POSTS.md:55`, 358
  files held back). **Push is blocked**: the history rewrite (`HANDOFF-HISTORY-REWRITE.md`). Neither
  stops local work; both stop anything reaching the public site.

---

## Phase 0 — the board member's answer (this week)

1. **Finish the overruns page** (built 22 Oct, uncommitted): add the "general fund only" footnote --
   grants, circuit breaker and revolving funds paid before this figure is measured; review on the
   dev site; commit.
2. **Put the all-funds view beside it.** `/special-education/sped-all-funds` already exists from the
   journal and is **waiting on TJ's review** (`open-items-2026-10-19`). Review it; it is the
   "does outside money change the overrun" half of the question for FY2023-FY2026.
3. **Get it to the board member without the site.** Because deploy is blocked, send the figures
   directly: a short brief (the levels table, the method line, what it does not cover) as a PDF or
   email text. Decide: wait for the deploy, or send now.

## Phase 1 — unblock the public site (needed before anything ships)

4. **Pages 20,000-file limit**: a Pages Function reading the long tail from R2, or Pages Pro. TJ's
   call on which. (`HANDOFF-SOCIAL-POSTS.md:55-64`, `HANDOFF-NEXT.md:43`)
5. **History rewrite** so pushing resumes (`HANDOFF-HISTORY-REWRITE.md:20-49`). Deferred by TJ.
6. Pre-deploy hygiene, once: `sync_archive.py --manifest` (stale journal sha), `build_source_index`,
   `build_api`, `check_generated`, phone width. Then one batched deploy, which also lets the fund-1301
   takedown proceed (`open-items-2026-10-19`).

## Phase 2 — grants data (fetchers; cheap, and they feed everything after)

7. **Wire `fetch_dese_entitlements.py`** to every district: `view=code`, 20 codes x 11 years,
   `--if-changed` snapshots through `ingest.land`, catalogue rows, weekly in `refresh.py`. Reconcile
   Lunenburg against the per-district view. Explain or register the disagreement with
   `grants-history.csv` (FY2020/FY2024 240, all 262 years, ARP IDEA).
8. **Fetch the open-grants list** (`grants.aspx` + each detail page's eligibility) weekly, snapshot on
   change. Build `/grants-open-to-lunenburg`: what is open now, due date, eligibility, type --
   for the schools to see what to apply for.
9. **A DESE fund-code -> grant-name table** from those two, so every fund on `/accounts` shows its
   name: `FY25 #240` reads "IDEA special education (DESE 240), FY2025" (`fund-owners.csv:406,423-427`;
   rendered by `Finance.tsx:60`). Also makes them searchable.
10. **Grant comparison report**: Lunenburg's allocations per pupil, by fund code, against its peer
    and border sets (`build_town_comparison.py`), FY2017-FY2027. Allocations only; what was drawn
    and spent is Phase 3.

## Phase 3 — the complete school budget (the big one)

The deliverable: the schools' budget is the general fund, and grants are layered in without being
budgeted where anybody can see it. This page shows every one of the district's own lines with ALL
the money behind it. Built from the journal, FY2023-FY2026, from the books (rule 13a).

11. **Money in, by source**: general fund appropriation, Chapter 70 (beside it, not added -- rule 11),
    each grant fund, circuit breaker, school choice, revolving funds, lunch. Receipts from the
    journal; allocations from Phase 2 beside them, never summed with them.
12. **Every budget line by function code**: voted (general fund) | spent from the general fund |
    spent from other funds, by fund | the two together. That last column is the "true" line. Where
    a grant posts to 0000/2000 (FY2025+ IDEA), the money is shown as UNATTRIBUTED, not spread across
    lines by us.
13. **Unspent**: per fund, receipts vs spending vs balance carried, each year. "Left on the table" is
    a balance that carries; say which funds carry by design (revolving) and which lapse (grants have
    a period of availability).
14. **What is paid from outside the general fund, and from where**: the report TJ named. By fund x
    function x vendor class, the journal's own descriptions.
15. **The special education version** is the same report, filtered to special education. It absorbs
    the queued "start here" table (`QUEUE.md`, budget / IDEA / circuit breaker / actual by year) and
    the overruns page links into it.

**TJ's hypotheses -- tested, not assumed (rule 7):**
- *H1: special education costs more than its budget because outside funds pay for more than is
  budgeted.* Test: per year, general-fund spending on special education functions vs all-funds
  spending on the same functions. Measures how much MORE is spent; it cannot show intent.
- *H2: do they code grant spending to budget lines?* Test: share of each grant fund's spending on a
  real function code, by year. Already partly answered: yes to FY2024, placeholders from FY2025.
  Why it changed is NOT established -- a records question for the business office.

How the district decides what to budget when a grant spans lines is not in any document we hold; the
honest page shows what was done and registers the question.

## Phase 4 — menus and reports index

16. School menu: the complete school budget (Phase 3) as a category at the TOP. Monty Tech and
    Bromfield move to an "Other schools" section at the BOTTOM.
17. Town menu: FY2026 closeout moves to a second category ("special reports") at the bottom.
18. The same moves on `/reports`. Check: `check:crumbs` still passes.

## Phase 5 — format work already queued (22 Oct)

19. Board/department finance pages: every fund clickable to its history (`QUEUE.md:3`). Pairs with 9.
20. Site-wide metrics redesign: replace the tile grid in `report.tsx`; mock 2-3 options first
    (`QUEUE.md:18`). The overruns page is the test case.

## Quick, any time

21. **A launcher at the repo root**: `./dev.sh` -- the site dev server (`fy28`, vite, :5173) and the
    ingestion dashboard (`scripts/status.sh`, :8795, its Backlog tab at `/backlog.html`), both up,
    both opened, Ctrl-C stops both. A dev server needs no build and no build lock; `build:site` is
    the deploy build (prerenders every page into `dist/`), not a way to view the site.
22. Ingest the four files from 22 Oct (`DATA-TO-INGEST.md`), provenance first; then the turf-history
    comparison against our thread.

---

## Dated

- **26 Oct** -- OML complaint response due; **4 Nov-30 Dec** AG window (`HANDOFF-FILINGS.md`).
- **17 Nov** -- Special Town Meeting; the posts that go with it.
- **Mid-February** -- budget-cycle deadline (`HANDOFF-TODO.md:94`).

## Everything else open, by workstream (not reordered; detail in the cited file)

- **Waiting on TJ**: activity-fee lever $0 vs $70 voted (`open-items-2026-10-14`); transport 6% vs
  7.4% contract, FY27 $1 gap (`HANDOFF-CITIZEN-FIRST-REPORTS.md:63-70`); para rates (~4%,
  `HANDOFF-NEXT.md:48`); FY26 surplus list/unlist; transportation-brief review (blocks
  `REPORT-FORMAT.md`, which interacts with item 20); teacher-pay decisions (`HANDOFF-TEACHER-PAY.md:125-135`);
  athletics renames and FY2024 rank test (`HANDOFF-ATHLETICS-SCHEDULES.md:68-97`); minutes pacing
  stop; social posts (Bromfield, property tax); p643 notice to the Town.
- **School money, older**: reports 1-5, 8, 10, 11, 13-15 (`REPORTS-TO-GENERATE.md`) -- many are
  absorbed by Phase 3, re-check each against it before building; surplus bridge deep dive;
  fy26-closeout section 8 stale; `follow-the-money.html` false and `money-flow.html` v1 breaks rule 1
  (`FEEDBACK-QUEUE.md:14`); the $26m+$2m bridge (`FEEDBACK-QUEUE.md:66`).
- **Teacher pay**: paused; OCR jobs to kill, extractor to commit (`HANDOFF-TEACHER-PAY.md:88-93`).
- **Ingestion**: annual-report seams A2-A5, A9; FY2011 special revenue; refused receivables and
  debt pages (`HANDOFF-INGESTION-TRUST.md`); PreK/K and non-public enrolment; FY27 department
  presentations (overdue); staff directory gaps; 3,099 image-only meeting documents (deferred).
- **Monty Tech**: Gosnold's $0 in the median; two FY26 total-value figures disagree; DESE exclusion
  page unread (`HANDOFF-MONTY-TECH-HUB.md`).
- **Records requests out**: MUNIS appeal outcome; PEC attachments; journal redaction log; Capital
  Planning request; Dee Bus FY23-25; step/lane and peer contracts drafted, not sent.
- **Site / search**: sources on every page (TJ's main to-do; do not start unprompted); thread-page
  tabs; search-built threads miss mentions; menu loads a 46 KB file; dark-mode steps; 13 pages
  without a short version.
- **Infrastructure**: refresh commit sweeps other sessions' files (same root cause as the history
  rewrite); `pmset` wake; off-machine backup; retire the refresh tree; ingestion-server decision.
- **Social**: templates by shape; automation design; six "connect the dots" fixes
  (`HANDOFF-SOCIAL-POSTS.md`).

Known duplicates across the older files (same item, two places): Pages limit; push hold; activity
fee; Gosnold; sources-on-every-page; off-machine backup; rule 15a re-runs. The YouTube-caption block
in `QUEUE.md:633` and `HANDOFF-TODO.md:33` is stale -- captions are done.
