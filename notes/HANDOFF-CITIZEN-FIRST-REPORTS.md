# Handoff: citizen-first reports (transportation prototype) and the FY26 surplus audit

> **Superseded in part, 10 October 2026 (night).** The transportation brief was extended the
> same day (commit 971c05b5, deployed) and much else shipped after this was written -- see
> `notes/HANDOFF-2026-10-10-JOBS-TRANSFERS-THREADS.md`, which is the current state. The open
> decisions below still stand.

As of Saturday 10 October 2026. Written by the session that did both. The pacing, search and
D1 work is a different workstream: `notes/HANDOFF-NEXT.md`. Do not edit that file from here.

## What this workstream is

TJ, 10 October 2026, said that report summaries read as "nothing-burgers". Several trusted
residents also said the big-metric-plus-paragraph cards are unusable: *"i dont come away with
the words to repeat to fellow citizens."* Two answers came out of it.

1. **How findings are FOUND.** `notes/process/AUDIT-PASS.md` sets out eight comparisons and
   the argument test. A card leads only if someone who decides the line would dispute it or
   have to answer for it. CLAUDE.md 7b now points to it ("A conclusion is a COMPARISON, or it
   is inventory"). So does step 2a of `WRITING-AN-ANALYSIS.md`.
2. **How findings are SHOWN.** The new `brief` format, prototyped on
   `/analysis/transportation`:
   - a one-line answer;
   - 3–6 verdicts, each graded sound / concern / problem / unknown;
   - for each verdict, a sentence a reader can repeat, then a "how we know" chain that goes
     one layer deeper each step, down to the ledger;
   - every layer labelled by kind: measured, on the record, from the recording, our
     estimate, a possible explanation, or not published.

   The design rules:
   - **Progressive depth:** the top ~15% must be complete on its own, for the ~90% of
     readers who stop there.
   - **The five-whys idea is the structure, but the page never uses the word "why".**
   - **Inform, never script advocacy.** TJ rejected "What to ask the School Committee" as
     *"too much on the nose"*. `scripts/brief.py` refuses prescriptive wording.

## Committed, pushed, deployed

| commit | what | live |
|---|---|---|
| `571139ae` (daily refresh) | swept up `AUDIT-PASS.md`, `notes/findings/TRANSPORTATION-AUDIT.md`, the CLAUDE.md 7b subsection, `WRITING-AN-ANALYSIS.md` §2a | n/a (notes) |
| `7a6bc77a` | the FY26 school surplus audit: `fy26_audit()` in `build_school_surplus.py`, `verify_audit_2026()`, `notes/findings/FY26-SURPLUS-AUDIT.md`, the paraprofessional fix (5 lines, not 4), money-gaps rows | yes, **still UNLISTED** (`sources/analyses/UNLISTED`) |
| `6c437ce0` | transportation rebuilt as a brief: `scripts/brief.py` (validator), `fy28/src/components/brief.tsx`, a `brief` branch in `Analysis.tsx` (inert for payloads without `brief`), `build_transportation.py` (`build_brief`, `render_brief_md`, `render_track`), `verify_transportation.py` (every brief figure recomputed by a second route) | yes, **listed** |

Deployed 10 Oct: `npx wrangler pages deploy` from `fy28/`, after `npm run build:site`
prerendered 1,398 of 1,398 routes. Checked on production:
`/data/transportation.json` serves the new answer line, and `/analysis/transportation`
returns 200. The deploy builds from the working tree, so it also shipped other sessions'
uncommitted generated files. That work stays theirs; none of it was committed here.

**Nothing of this workstream is uncommitted.** Every modified file in `git status` right now
(`fy28/public/api/*`, `d1-pushed*.txt`, search-affinity, meeting-register, app-metrics,
DATA-PROBLEMS) is a side effect of the D1/search session. Do not commit or discard them from
here.

## Open decisions (TJ's)

1. **`notes/process/REPORT-FORMAT.md` is NOT written.** A subagent drafted the standard, but
   the harness refused its write. I did not write it on its behalf. TJ was asked: save it now,
   or after he reviews the page. Once approved, the standard goes into CLAUDE.md (rule 7b
   and 7d currently describe the OLD Stat/Conclusions cards), and other reports convert one
   at a time. Memory `report-format-redesign` records the principles in the meantime.
2. **Transport rate in the model.** `model/finance.py` grows `transport` at 6%. The signed
   contract goes +7.4% into FY2028. Rule 8 says this one reaches the app because it changes
   an assumption. Not changed: it moves the projection, so it is TJ's call.
3. **`model/derivations.py`** still states the athletic bus cost against the town line using
   the HIGHER of the district's two sheets, with no spread. Rule 13a says to publish the
   spread instead.
4. **FY27 gap:** `fy27.csv` carries one dollar more than the district document prints. Not
   reconciled.
5. **`fy26-closeout.md` §8** predates the period-13 ledger and is outdated by it.
6. **Unlist or list the FY26 surplus page.** It is still in `UNLISTED`; removing the line
   publishes it.

## NOT established (do not restate these as fact)

- **Why special education busing keeps missing its budget.** The page shows the budget lagging
  spending in both directions. Placements changing between budget and year is a hypothesis.
  Closes: the van contract and a count of routes per year.
- **That the 1308 `SCH. CHOICE BUS FEE` receipts ARE the bus fees.** It is a candidate
  account. What is measured is that the general fund paid the full regular-routes contract.
- **What fund 1301's purchase-of-service bought in FY2026** (the account where buses used to
  be charged). Gap registered.
- **The athletic fee fund's balance after 30 June 2020.** Whether it ran below zero in FY2024
  is unknown. Gap registered.
- **Per-sport bus costs are allocations, not measurements.** Paired rows carry identical
  figures, so one bus is split in two. Track ranks most expensive only once its split rows
  are recombined. The FY2025 spring section prints a $0.00 total. That it was unfinished is
  a hypothesis, and the gap is registered. No trip-level data exists in the archive, so the
  verdict is "unknown".
- **Why FY2024 regular routes cost more than FY2025 under an escalating contract.** Closes:
  the FY2021–25 Dee Bus contract (requested 9 October 2026).
- **The caption summaries on the track verdict** (waiting time, Reggie Lewis Center, no
  indoor facility) come from machine captions, a finding aid. They have NOT been checked
  against the videos.
- **The FY26 surplus page has not had its persona review** (`notes/process/PERSONAS.md`).

## Loose ends, small

- `/api/money_gaps.json` and `notes/generated/DATA-PROBLEMS.md` do not yet carry the FY2025
  spring-section gap (row 260 of `money-gaps.csv`). They regenerate on the next
  `build_api.py` / `build_data_problems.py`, which the daily refresh runs.
- The sitemap warning about `/meeting-minutes/sewer-commission/2023-06-27-TbLdFYlFDtQ`
  comes from another process, not this one.
- A vite dev server may still be running on port 5191 (Node 22). It is safe to kill.
- Filing to NextLevel was offered (`#appdev #lunenburgbudgetapp`) and not answered.

## The exact next step

**TJ is reading `/analysis/transportation` on the road. Wait for his review.** Then:

1. Apply his review to the transportation brief, and to `brief.py`'s budgets if lengths are
   the complaint.
2. On approval, write `notes/process/REPORT-FORMAT.md`, and update CLAUDE.md 7b/7d to the
   new standard.
3. Convert the next report. `fy26-school-surplus` is the obvious one, since its audit
   findings already exist in `FY26-SURPLUS-AUDIT.md`. Run `AUDIT-PASS.md` first, then
   `build_brief`-style generation, a verifier, then `check_generated.py` once at the end.
