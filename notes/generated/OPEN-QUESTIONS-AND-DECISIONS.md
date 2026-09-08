# What is waiting on a decision, and what is waiting on a document

The Lunenburg Budget Project — for review, 8 September 2026

**4 decisions** and **13 open questions**. The gap registry behind the questions holds **81 rows** across 6 kinds: `document_wanted`, `held`, `money_in`, `money_out`, `people`, `record`.

The two lists are kept apart because they behave differently, and section 3 below is the part worth reading first if you read nothing else.

---

## 1. Decisions waiting on TJ

Not questions about the data — questions about what this project should do. Nothing
below is blocked on more analysis; each is blocked on somebody choosing.

| # | the decision | why it is yours and not mine | cost of leaving it |
|---|---|---|---|
| ~~D1~~ | ~~**Push the database to D1.**~~ **DONE 7 Sep 2026** — 70,013 rows in one pass; D1 verified to match the local copy, 78 tables. The plan's "~140,026 writes" warning proved pessimistic: the ceiling is not rows x 2, and what exhausted the budget on 5 September was four re-imports in one day rather than the size of one. | | |
| ~~D2~~ | ~~**Deploy.**~~ **DONE 7 Sep 2026** — v11 is live, verified against the archive manifest. | | |
| D3 | **Resume the tax-rate and town-meeting extraction, or drop it.** Held after repeated `ECONNRESET`. Your instruction was to hold if the agents keep failing and continue if some make progress. | The balance-sheet and special-revenue extractions since then both succeeded, so the evidence has changed. | Two datasets stay uncaptured. Nothing else depends on them. |
| ~~D4~~ | ~~**What to do about `athletics.md` being stale.**~~ **DONE 7 Sep 2026** — both analyses corrected, the page no longer disagrees, and the verifier now reads both documents and recomputes the series it had never checked. | | |
| ~~D5~~ | ~~**Extract the FY2024/FY2025 enterprise-only combining balance sheets.**~~ **DONE 7 Sep 2026** — both years tie to their own printed PROOF; FY2024's two printings agree figure for figure. Found a $102,000 pair of compensating errors and a published query that had never been run. | | |
| ~~D6~~ | ~~**The PEG revenue-vs-expenses statements.**~~ **DONE 7 Sep 2026** — eleven editions, not ten: FY2023's statement and both FY2024 tables were catalogued as absent and are not. All tie. The FY2019 town meeting article settles the rename as a reorganisation, which makes `Starting Balance` mean different things either side of it. Four published figures for the fund on 30 June 2025 and nothing joins any pair. | | |
| D7 | **Send a records request.** The gaps registry now names specific documents rather than describing absences — the FY2023 trial balance, the five athletics memos, the `Account_Detail` export for orgs S3066672/S3066671, DESE's End of Year Financial Report. That is a letter, not a list. | It is outbound, to the Town, in your name. | The gaps stay gaps. Several are load-bearing. |
| ~~D8~~ | ~~**Audit the other extracts for the parenthesised-negative defect.**~~ **DONE 7 Sep 2026** — reduced from eighteen investigations to four, because an extractor that ties to a printed control total cannot hide a sign error. One latent defect found and guarded (`extract_grants.py` would silently DROP a negative rather than flip it); `check_money_parsers.py` registered. | | |
| D10 | **Whether to re-derive the model's 2% state-aid rate.** It is recorded as `BARE` — no stated source, no derivation — and measured Chapter 70 receipts grew 4.47%/yr FY2014–FY2022. The two are not comparable (different quantity, different span, actual-to-actual vs forward), so this is not a bug report; it is a question about whether to go and build the comparable series. **The series now exists** — 23 consecutive BUDGET years of the town's own cherry sheet aid, FY2005–FY2027, in `notes/findings/state-aid-budget-series.csv`, with the investigation and a recommended rate in `notes/findings/STATE-AID-RATE.md`. The decision left is whether to move the rate. | Changing a projection rate moves every published figure downstream of it, and rule 14 says a correction that size makes *other* errors findable. That is a decision with a workload attached, and §7 of the findings note names what it expects to surface. | The rate stays unsupported, and the site keeps saying so honestly. Not urgent. |
| ~~D11~~ | ~~**Fix `source_ref` in `extract_free_cash.py`.**~~ **DONE 7 Sep 2026** — `source_ref` now names the amount's own cell and a new `label_ref` names the label. The extractor re-opens the workbook and asserts every one of the 630 citations resolves to its own figure before it writes; proved it refuses by breaking the column arithmetic by one. The free-cash page's workaround is deleted. | | |
| D9 | **Whether `held` is the right fourth side** in the gaps registry, alongside `money_in`, `money_out`, `people` and `document_wanted`. Added for the balance-sheet gap: money the town is holding is genuinely neither in nor out. | A taxonomy is an editorial choice and it renders on a public page. | Nothing breaks. Sides are read off the data, so changing it is a CSV edit. |

---

## 2. Open questions — the data ones

These do not resolve by choosing. Each needs a document, and each names the one that
would close it. All are registered in `sources/data/money-gaps.csv` unless marked.

**Load-bearing, in the sense that other conclusions rest on them:**

1. **Which fund pays which post.** The in-district special education escalator is built
   on a paraprofessional line, and that line cannot be distinguished from grant money
   unwinding. This is the single most consequential unknown in the project.
   *Closes:* DESE's End of Year Financial Report, which separates spending by fund.
2. **Whether a general fund athletics line is net of the revolving fund.** Rule 11's
   problem at its sharpest, on the one programme where both sides are visible.
   *Closes:* the MUNIS `Account_Detail` export for orgs S3066672 and S3066671.

**Specific and probably closeable:**

3. **What the $87,293.86 is.** Two tables in the FY2023 annual report state the same
   quantity and differ. Not a misreading — the page ties to itself in all six columns.
   The `Sale of Cemetery Lots` explanation is tested and dead (§4 above).
   *Closes:* the Town's FY2023 trial balance as of 30 June 2023.
4. **The residual $14.23** inside that. No FY2023 fund carries it, positive or negative.
   Probably not independently meaningful, but it is unexplained and unexplained is the
   honest word.
5. **Whether the $87,293.86 is connected to the $17,861.24** the town restated in grant
   funds between the FY2022 and FY2023 reports. Two different amounts in the same year.
   *Nothing joins them* — that is a statement about the evidence, not a denial.
6. **What the four `GEN` journal entries moved.** $254,121.18 into fund 1301 in FY2025,
   two thirds of the year's inflow, described in the ledger only as *per memo*.
   *Closes:* the five memos.
7. **FY26 year-end.** Everything held for FY26 stops at 31 March.
8. **What any Cherry Sheet actually says.** We hold none, for any year — every aid
   figure in this project is read off a ledger, a proof workbook or a DESE file rather
   than off the document that states the aid.
   *Closes:* DLS forms CS 1-ER and CS 1-EB for Lunenburg, FY2021–FY2027.
9. **Whether an aid shortfall lands on the schools or on the town.** FY2024 came in
   $390,814 under estimate. Who absorbed it is in nothing we hold.
   *Closes:* the fiscal-year-end recap (Form A-1), beside the Cherry Sheet.
10. **How many children Chapter 70 is paid for.** Foundation enrolment is 1,599; DESE's
    own measures give 1,563, 1,568.9 and 1,665.9. Four counts of four different things.
    *Closes:* DESE's FY27 foundation enrolment worksheet.

**Bounded rather than answerable:**

11. **How many children play sports.** Two town documents give 593 and 649 for the same
   year and count different things. No unduplicated count is published.
12. **Whether the fee rises moved participation.** Fees +30%, participations −3.9%, over
   exactly the same years. This is not a data gap that a document closes — it is a
   causal question the data cannot carry, and I do not expect it ever to. Listed so that
   nobody re-opens it thinking a records request would settle it.
13. **Whether a large CL#11 is prudence, a hiring freeze, a slipped project or an
    over-budgeted line.** Relevant to the free cash page in progress; the components do
    not distinguish them.

---

## 3. How to use the two lists

The distinction is the whole point of keeping them apart. **§6 items go stale** — a
decision not taken is a decision taken by default, and D1/D2 in particular decay into
"the site is out of date and nobody chose that". **§7 items do not go stale.** They are
correctly parked, they are published on `/what-we-cannot-answer`, and the honest state
of a §7 item is open.

The failure mode to avoid is treating a §7 item as if it were a §6 one — deciding what
the $87,293.86 probably is, rather than asking for the trial balance. Rule 7 exists
because that conversion happens quietly and reads like progress.

---

*Extracted from `notes/findings/DRILL-IN-PAGES.md` sections 6-8 by `scripts/build_decisions_doc.py`. The counts above are computed at build time, and the gap count is read from `sources/data/money-gaps.csv` — so if a question here is not registered there, these two numbers stop agreeing.*
