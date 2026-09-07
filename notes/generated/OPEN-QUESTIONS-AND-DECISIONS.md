# What is waiting on a decision, and what is waiting on a document

The Lunenburg Budget Project — for review, 7 September 2026

**9 decisions** and **13 open questions**. The gap registry behind the questions holds **32 rows** across 5 kinds: `document_wanted`, `held`, `money_in`, `money_out`, `people`.

The two lists are kept apart because they behave differently, and section 3 below is the part worth reading first if you read nothing else.

---

## 1. Decisions waiting on TJ

Not questions about the data — questions about what this project should do. Nothing
below is blocked on more analysis; each is blocked on somebody choosing.

| # | the decision | why it is yours and not mine | cost of leaving it |
|---|---|---|---|
| D1 | **Push the database to D1.** Held deliberately. A full replace is ~51,000 writes against a free-tier ceiling of 100,000 a day, and four re-imports took the endpoint dark on 5 September. | It spends a shared daily budget that residents' queries also draw on. | `/api/query` serves the older database. `sync_d1.py --check` fails, and it is the ONLY failing check — so a real failure has nowhere to hide. That is the actual cost. |
| ~~D2~~ | ~~**Deploy.**~~ **DONE 7 Sep 2026** — v11 is live, verified against the archive manifest. | | |
| D3 | **Resume the tax-rate and town-meeting extraction, or drop it.** Held after repeated `ECONNRESET`. Your instruction was to hold if the agents keep failing and continue if some make progress. | The balance-sheet and special-revenue extractions since then both succeeded, so the evidence has changed. | Two datasets stay uncaptured. Nothing else depends on them. |
| ~~D4~~ | ~~**What to do about `athletics.md` being stale.**~~ **DONE 7 Sep 2026** — both analyses corrected, the page no longer disagrees, and the verifier now reads both documents and recomputes the series it had never checked. | | |
| D5 | **IN PROGRESS 7 Sep 2026.** **Extract the FY2024/FY2025 enterprise-only combining balance sheets as a new dataset.** They cannot extend the combined series — different table — so this is a decision to start something, not to finish something. | It is scope, and enterprise funds are ratepayer money rather than tax money. | Two years of enterprise fund positions stay unread. |
| D6 | **The PEG revenue-vs-expenses statements**, ~11 editions with a real cross-check. Same shape of decision as D5, and the cross-check makes it the better bet of the two. | Scope. | Same. |
| D7 | **Send a records request.** The gaps registry now names specific documents rather than describing absences — the FY2023 trial balance, the five athletics memos, the `Account_Detail` export for orgs S3066672/S3066671, DESE's End of Year Financial Report. That is a letter, not a list. | It is outbound, to the Town, in your name. | The gaps stay gaps. Several are load-bearing. |
| D8 | **Audit the other extracts for the parenthesised-negative defect.** `sped_para_history` was wrong by $315,772 in FY2024 — twice the line, because a sign error doubles rather than zeroes. Fixed there; not looked for elsewhere. | It is unbounded work with an unknown yield, which is exactly the kind of thing to decide rather than drift into. | Unknown. That is the argument for doing it. |
| D10 | **Whether to re-derive the model's 2% state-aid rate.** It is recorded as `BARE` — no stated source, no derivation — and measured Chapter 70 receipts grew 4.47%/yr FY2014–FY2022. The two are not comparable (different quantity, different span, actual-to-actual vs forward), so this is not a bug report; it is a question about whether to go and build the comparable series. | Changing a projection rate moves every published figure downstream of it, and rule 14 says a correction that size makes *other* errors findable. That is a decision with a workload attached. | The rate stays unsupported, and the site keeps saying so honestly. Not urgent. |
| D11 | **Fix `source_ref` in `extract_free_cash.py`.** Every one of the 630 rows in `free_cash_proof` cites `Sheet1!A<row>` — the **label** cell in column A. The amounts are in another column (`Sheet1!F17` for Lunenburg 2025). So every provenance coordinate in that table points at the wrong cell: right row, wrong column. Confirmed directly — `Sheet1!A5` is recorded for a figure of `3,354,370`. | The CSV and the database feed other things, so re-extracting is a change with a blast radius, and the free-cash page already works around it by deriving the value coordinate itself and re-opening the workbook to assert all 70 cited cells. | Rule 12 says a figure is only checkable if somebody can get back to it. A citation that resolves to a label is a citation that fails exactly when somebody tries to use it — which is to say, never in testing. |
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
