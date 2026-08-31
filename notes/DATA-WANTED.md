# Data wanted


> **Working state:** `notes/HANDOFF.md` carries the current branch, the open
> decisions and what is established versus assumed. `CLAUDE.md` carries the rules.

Things I cannot get, ranked by how much they would change. Internal working list.

Three reasons something is on here: it is behind a login or bot protection, it is a
question rather than a document, or nobody publishes it.

Each entry says **what it would settle** — if the answer would not change anything, it is
not on the list.

---

## What the archive answered on 28 August, and what it did not

The mirrored budget documents turned three of these from "not obtainable" into "measured".
Out-of-district tuition now has 11 budgets behind it, the paras 10, the teachers
8 — all budget columns, one stage held constant, in
`/data/*-history.csv`.

**What that did not answer is the same thing it never could.** Every one of those series is
dollars. None of them is children, and none is staff. The questions below are still the
questions, and item 4 has become the most important of them.

## Tier 1 — these change conclusions

### 1. Out-of-district placement counts, by year, FY23 to FY27

**The single most valuable number in the project.**

The FY27 budget cut out-of-district tuition 46%, from $1,291,293 to $700,142. Two
explanations fit the dollars equally well and point opposite ways:

- fewer children are placed outside the district, or
- the district had been over-budgeting this line and FY27 is the first honest figure
  (FY25 was budgeted $1,164,824 and spent $732,298 — 59% over)

**Dollars cannot tell these apart. A count can.** If placements fell, the saving is real
but cannot repeat. If they did not, there was never a saving and the old budgets were
padded.

- **Ask:** Business Manager, or Director of Student Services
- **Wording:** *"How many students were placed out of district in each of FY23, FY24, FY25,
  FY26 and FY27 — and how many are projected for FY28?"*
- **Format:** a number per year is enough. Split by private / collaborative if easy.

### 2. Is the FY27 out-of-district tuition line gross, or net of circuit breaker?

One question, and it decides whether a whole section of the analysis is right.

The circuit breaker reimburses part of out-of-district cost. If the $700,142 is already
net of expected reimbursement, then the "46% cut" is an accounting change, not a service
change, and the make-or-buy story is wrong.

- **Ask:** Business Manager
- **Wording:** *"Is the FY27 out-of-district tuition appropriation stated gross, or net of
  anticipated circuit breaker reimbursement?"*

### 3. FY26 year-end figures

Everything we hold for FY26 stops at **31 March 2026**. Four specific numbers:

| | why |
|---|---|
| Circuit breaker fund 2640: year-end balance, receipts and draw | The fund held $615,301 at Q3 with only $4,005 drawn. If the draw is booked in June, that is a timing artefact rather than idle money. |
| Out-of-district tuition, accounts 9300 and 9400, year-end actual | Committed spend was already $1,530,182 at Q3 against a $1,291,293 budget. Did it hold? |
| Athletics revolving fund, year-end | We have this one already, from the school funds workbook. Included for completeness if a fuller version exists. |
| General fund year-end, by department | Q3 showed the schools at 66.1% expended. |

- **Ask:** Finance Director / Town Accountant
- **Note:** she said in the 11 August memo that she hopes to report quarterly. The Q4 or
  year-end packet may simply exist by now.

### 3c. FY25 for the athletics revolving fund, and the vendor warrant

> **Partly answered, 17 June 2026.** A records request produced the fund's **cashbook** for
> FY2024, FY2025 and FY2026 — every receipt and payment with a date. It did not produce the
> object detail, the FY25 balance sheet, or any vendor name: column `VDR NAME/ITEM DESC` is
> populated on receipts and empty on every payment row. What it did produce is a new and
> sharper question, **3d** below. Read `sources/analyses/athletics-ledger.md` first.
>
> One correction it forces here: the fund closed FY25 with **$131,239.09 of cash** and a
> **fund balance of $110,247.89**. The row below quotes the second and calls it the closing
> figure. Both numbers are right and they are not the same quantity — the $20,991.20 between
> them is invoices recorded and not yet paid.

Two requests, both cheap, both from the same office, and between them they close the
athletics analysis — see `sources/analyses/athletics.md` §4a and §5.

| | why |
|---|---|
| **FY25 special revenue report / balance sheet for fund 1301** | The athletics fund was reported in public comment (School Committee, 3 September 2025) to have run "over $100,000" in deficit, and the Finance Committee raised negative balances going unnoticed on 8 July 2025. The fund closed FY25 at **+$110,248**, so the year-end figure does not show it. We hold the endpoint and not the path: there is no FY25 fund report in the archive. This is the single most likely explanation for athletics costs shifting onto the town, and it is currently a hypothesis. |
| **Vendor warrants covering FY23–FY26**, or account detail history for object `535016` | No document in the archive names a carrier beside a dollar figure for athletics. The only actual payment to Dee Bus recorded anywhere is **$731.50**, for one field trip. The warrant is the list of bills the Select Board approves for payment, itemised by vendor — it is produced roughly weekly and it is the only thing that would show what athletic transportation actually cost, as opposed to what was budgeted or encumbered. |

- **Ask:** Finance Director / Town Accountant, same channel as item 3
- **Wording:** *"The FY2025 special revenue report or fund balance sheet for fund 1301
  (Chapter 658 / athletics revolving), in the same format as the FY2026 one already
  provided; and the vendor warrants approved by the Select Board for fiscal years 2023
  through 2026, or in the alternative the account detail history for object code 535016."*

### 3d. The five memos behind the `ADJ EXP` journal entries

**The highest-value single ask in the project.** Five general journal entries move
**$304,046.18** into the athletics revolving fund across FY2024 and FY2025 — $254,121.18 of it
in FY2025 alone, 65% of that year's receipts. Every one is referenced `ADJ EXP` and commented
only *"per memo"*, with a date:

| effective | posted | journal | amount | comment |
|---|---|---:|---:|---|
| 2024-06-30 | 2024-09-18 | 1576 | 49,925.00 | `ADJ PER MEMO 08/12/24` |
| 2025-02-12 | 2025-02-12 | 157 | 1,282.57 | `PER MEMO 01/30/25` |
| 2025-05-02 | 2025-05-06 | 54 | 113,559.00 | `PER MEMO 05/02/25` |
| 2025-06-30 | 2025-07-02 | 709 | 19,271.08 | `PER MEMO 7/02/25` |
| 2025-06-30 | 2025-08-27 | 1339 | 120,008.53 | `PER MEMO 08/20/2025` |

An entry raising cash in a fund and labelled as an expense adjustment fits at least three
different things: expenses charged here and later moved to another fund, a transfer in, or a
correction of mis-posted charges. **Those are different facts about the world and identical
facts on the page.** Which one it is decides whether the athletics story is "the town took on a
cost" or "the accounting moved" — and, more generally, whether a budget line's prior-year
"actual" can be adjusted by memo months after the year it describes and after the next budget
was voted. Journal 1339 was posted on 27 August 2025.

- **Ask:** Town Accountant
- **Wording:** *"Copies of the memoranda referenced in the following general journal entries
  to fund 1301: journal 1576 dated 08/12/24; journals 157, 54, 709 and 1339 dated 01/30/25,
  05/02/25, 07/02/25 and 08/20/2025 respectively. If a memorandum does not exist as a separate
  document, the journal entry's full detail showing the offsetting account."*
- **What settles it:** the offsetting side. These exports show one leg — cash in fund 1301.
  The other leg names the fund the money came from.

### 3e. What the Capital Planning Committee does when the funding is cut

The FY27 capital plan publishes a CPC rank, a cost and a running total, and the funding line
falls between rank 12 and rank 13. That much is published. **What is not published is whether
that ranking survives a change in the money.**

It matters because the site now models redirecting free cash to the schools, and free cash is
the capital programme's largest single source — $991,627 of the $1,830,203 FY27 programme, and
an average of $591,286 a year across the plan's own ten-year table. Redirect $300,000 and the
programme is funded by $300,000 less. That part is arithmetic. Which projects stop is not:

- **Held to the published ranking**, items come off the bottom until the money is found. Rank
  7 is a $494,500 roof with only $199,449 of items below it, so any draw past that reaches the
  roof: $300,000 and $500,000 both remove $693,949.
- **Re-sequenced**, the committee drops whatever combination comes closest and there is
  $1,437,005 of ranked, costed, unfunded work below the line to substitute into. At $300,000
  the closest combination is $301,703.

The gap between the two is 131% of a $300,000 draw, and it is a **modelling artifact rather
than a cost** — it exists because one reading assumes indivisible items in a fixed order. The
site reports both ends and says nothing establishes which. It is the difference between
"cutting $300,000 costs capital $694,000" and "cutting $300,000 costs capital $300,000", and
only the second is arithmetic.

**A related gap, and it is the one that would change a number rather than a range.** The plan
publishes three funding sources for FY27 — free cash $991,627, raise and appropriate $244,576,
and $594,000 from the Vehicle Use Special Purpose Stabilization Fund — but **no
project-by-project funding table.** Two projects are footnoted as stabilization-funded (Engine
2, $335,000; Front End Loader, $259,000) and they happen to sum to exactly $594,000, which is
how the assignment is currently known. That is a reconciliation, not a statement: the plan
never says those two are the whole of it. If a third project were partly stabilization-funded
and one of those two partly free-cash-funded, the totals would still tie and the assignment
would be wrong.

- **Ask:** Capital Planning Committee, or the Town Administrator
- **Wording:** *"For any fiscal year in which the capital programme was funded below the
  committee's recommendation, the minutes or memoranda showing how the funded list was
  revised — specifically whether projects were removed in rank order or the ranking was
  re-worked against the available amount. Also the FY27 capital programme showing the funding
  source for each project, and the committee's FY26 and FY25 recommended lists showing rank,
  cost and which items were ultimately funded."*
- **What settles it:** one prior year's recommended list beside its funded list. If the funded
  set is a strict prefix of the ranking, the rigid reading is the right one; if it is not, the
  committee re-sequences and the overshoot is ours, not the town's. For the funding split, any
  document assigning a source to each project.
- **Second-best:** the FY26 and FY25 capital plans at project level. We hold only the funding
  totals for those years, from the FY27 plan's own history table — no project lists, so there
  is nothing to test the question against.

### 3b. How grants and state funding map onto the budget lines

**Now tied with item 4 as the highest-value question here, and it is the same question
from the other side.**

The district's budget documents show general-fund appropriations and nothing else. They do
not show which positions are wholly or partly paid by state or federal grants. So a line
can rise because the district employs more people, or because a grant that was paying for
those people ended and the cost landed on the town — and the two are indistinguishable in
everything published.

This bears directly on a number now on the site: the in-district special education
escalator is built on a paraprofessional line measured at 12.78% a year across ten
budgets. If part of that is grant money unwinding rather than staffing growing, the rate
is too high.

- **Ask:** Business Manager, or DESE directly
- **Wording:** *"For FY18 to FY27, what share of special education paraprofessional costs
  was funded by grants rather than the general fund appropriation?"*
- **Checked and NOT available online, 29 August 2026.** DESE's End of Year Financial
  Report does separate spending by fund, but it is a filing, not a publication. The page
  at `doe.mass.edu/finance/accounting/eoy/` is a shell — districts submit through the
  Security Portal at `gateway.edu.state.ma.us` and nothing district-level comes back out.
  The public extract is the per-pupil report at
  `profiles.doe.mass.edu/statereport/ppx.aspx`, which is explicitly titled **All Funds**
  and offers no fund selector. The state open-data portal carries only the two
  spending-category datasets, neither of which splits by fund.
- **So it has to be asked for**, and there are three people who could answer:
  the district's Business Manager, who files it; DESE's School Finance unit, who receive
  it; or the Town Accountant, whose records carry the school department's grant funds.
  **The district is the shortest route** — they file it, so they hold it.
- **Wording:** *"Could you share the district's End of Year Financial Report schedules for
  FY18 through FY25 — specifically the expenditure detail by fund, so general fund and
  grant-funded spending can be told apart?"*
- **Settles:** whether the paraprofessional trend is staffing or accounting.
- **Does not settle:** how many paras there are. That is item 4, and the two together are
  what this line actually needs.

---

### 4. Were the budgeted paraprofessional positions filled?

**Now the highest-value question in this file.** Since 28 August the whole in-district
special education escalator rests on this line: it is 34% of the component and it is
modelled at **12.78% a year**, measured across 10 budgets — $634,513 in FY18 to
$1,872,411 in FY27, up in 8 of 9 years, R² 0.89.

That is a headcount trend inferred entirely from dollars, because **a budget shows dollars
per line and never shows people.** Everything the model does with this line assumes the
budgeted money bought the budgeted staff. If a meaningful share of those positions went
unfilled, the line is not measuring headcount at all and the rate needs revisiting.

- **Ask:** Business Manager or HR (Penney Borneman, pborneman@lunenburgschools.net)
- **Wording:** *"How many special education paraprofessional FTEs were budgeted and how
  many were actually filled, for FY26 and FY27?"*
- **Checked and not useful:** the district posts openings on SchoolSpring with no
  district-specific URL, and a job board is a snapshot of what is open now rather than a
  record of what was filled two years ago. A standing list of vacancies would hint at
  difficulty hiring, but it cannot answer this. It has to be asked.

---

## Tier 2 — behind bot protection, which is the only reason I do not have them

**mass.gov returns 403 to anything automated**, including a normal browser user-agent. All
of these are freely available to a person with a browser. Downloading and dropping them in
`sources/` is all that is needed.

### 5. DLS free cash, Lunenburg, by fiscal year

> **ANSWERED, 30 August 2026.** The Free Cash Proof for Lunenburg and eight comparable towns,
> 2021-2025, is in `sources/dls-free-cash/` and read in `sources/analyses/free-cash.md`.
> Three things it raised, all still open:
>
> 1. **Lunenburg's Financial Policies Manual (April 2024)** — item 9 below. It almost
>    certainly states the town's own free cash target, which is the standard being invoked
>    when somebody says the balance is "not up to standard". One document settles a live
>    disagreement.
> 2. **Operating budget or general fund revenue for the eight peer towns.** Free cash means
>    nothing across towns of different size without a denominator, and the DLS proof carries
>    none. Schedule A (item 6) would supply it.
> 3. **Which departments turned back the $2,457,761** that makes up two thirds of
>    Lunenburg's 2025 free cash. The proof gives a town-wide total and no breakdown, so a
>    structural pattern and a run of one-offs look identical.
>
> **A fourth, added 31 August 2026: which export produced these files.** The report itself
> turns out to be reachable without a browser — the DLS Gateway's City & Town Free Cash
> Report answered a plain request, and all nine towns are on its jurisdiction list
> (Lunenburg is 162). But it is built from two dropdowns held in session, and driving it
> from outside one returns "Free Cash/Excess & Deficiency is not available for years prior
> to FY 2014", which is the report declining rather than answering. So the address is now
> the gateway page rather than "the databank", and **our copies still have not been
> re-derived from it.** The filename `FCPCompare<Town>.xlsx` and the five-year layout say
> the export was a multi-year comparison; which control produced it is not established.
> `sources/dls-free-cash/PROVENANCE.md` carries this.


#### The original ask

Free cash came up because people have asked about it. I only have single figures scraped
out of town presentations ($991,627 in one, $3.354M certified in another) and no series.

- **Where:** Division of Local Services Municipal Databank →
  https://www.mass.gov/info-details/division-of-local-services-municipal-databank
- **Want:** free cash certified by year, as far back as it goes. Excel or CSV.
- **Settles:** whether the town's reserve position is improving or deteriorating, and
  whether the $3.354M certified free cash is unusual for Lunenburg or normal.

### 6. DLS Schedule A — actual revenues and expenditures by category

The annual financial report every municipality files. It is the authoritative record of
what was *actually* spent, by function, and would let the budget-versus-actual document
stand on something firmer than two columns of a budget workbook.

- **Where:** same Databank, "Schedule A" reports
- **Want:** Lunenburg, as many years as offered

### 7. DLS levy limit history

Proposition 2½ levy limit, levy ceiling, actual levy, and excess capacity by year.

- **Settles:** the app asserts the town levies to its limit every year, on the strength of
  one Assessors' hearing document from FY23. A DLS series would confirm or break it.

### 8. Municipal Finance Trend Dashboard — Lunenburg **and the eight peer towns**

Five-year indicators including free cash as a percentage of budget, which is exactly the
comparison the reserve argument needs.

**Widened on 30 August 2026, and it is now the most-requested missing figure on the free
cash page.** The DLS proof we hold for nine towns carries **no denominator** — no
population, budget, revenue or levy for any of them, ours included. So the one question
everybody asks of that table, *how does each town sit against the same 5-7% band*, cannot
be answered from it, and `show-your-work.md` §7 says so in place of a column it would
otherwise have invented.

What the proof does support is composition, because a share compares and an absolute
dollar figure does not: unspent appropriations are 66.1% of Lunenburg's identified free
cash against 11.7% to 64.2% across the other eight. That is published. It is a different
measure and it must not be presented as the percentage-of-budget one.

- **Where:** the same Databank, per town
- **Want:** operating budget or total revenue for Ayer, Groton, Littleton, Lunenburg,
  Shirley, Townsend, Upton, Uxbridge and Westford, 2021 to 2025 — enough to turn nine
  absolute balances into nine ratios
- **Settles:** whether Lunenburg is holding more or less than comparable towns relative to
  what it spends, which is the actual question behind "is the town too conservative"

### 9. Lunenburg Financial Policies Manual, April 2024

- **Where:** https://www.mass.gov/doc/lunenburg-financial-policy-manual-april-2024/download
- **Settles:** whether the town has a stated free cash or reserve policy. If it has a
  target and is above it, that is a very different conversation from having no policy.

---

## Tier 3 — would sharpen things

### 10. DESE per-pupil expenditure *including* out-of-district

We hold in-district only, which by DESE's definition excludes out-of-district tuition —
the fastest-growing special education cost. The peer comparison is therefore narrower than
it looks, and the app now says so, but the fuller series would remove the caveat entirely.

### 11. Special education enrollment by disability type and program

The FY27 FinCom deck has this as a chart image: full inclusion 156→174, sub-separate
30→43, FY23 to FY26. **The underlying numbers, not the picture**, and ideally back further.

This matters because the DESE total count *fell* 6.9% over seven years while the district's
own chart shows intensive placements up 43%. The two count different things and their
totals do not match, so we cannot reconcile them at all from what is published — let alone
explain the difference.

- **Ask:** Director of Student Services, or DESE's special education data pages

### 12. Chapter 70 foundation budget detail — the special education increment

The state's foundation formula assumes a special education enrollment rate and funds it. If
Lunenburg's actual rate exceeds the assumption, the town pays 100% of the difference and,
as a hold-harmless district, never catches up.

- **Settles:** whether special education is structurally underfunded by the state formula
  here, which would be a genuine finding rather than a local budgeting question.

### 13. Tax classification hearings after FY23

`MANIFEST.md` records that we could not retrieve these — the town does not index them. The
FY23 hearing is the single most valuable town document we hold, carrying new growth by year,
value by class, and average bills. FY24 through FY26 would extend every series in the tax
base argument.

- **Ask:** Board of Assessors, or the Town Clerk

### 14. Contracts that are not public

- Secretaries (2025–2028) and cafeteria (2023–2026) — terms not published
- A **current** superintendent or administrator agreement. We only hold expired DESE
  templates, which the citation says plainly, but it is a real gap in the salary picture.

---

## Provenance gaps — nothing to obtain, only to write down

These are not documents we are missing. We hold every one of them. What is missing is the
address, and the person who can supply it is us.

### 15. Where the FY27 workbooks came from

> **PARTLY ANSWERED, 31 August 2026 — and note which file.**
> `xlsx/fy27-budget-projection-3-25-26.xlsx` was **sent directly to this project by Ana
> Lockwood, a member of the Lunenburg Finance Committee**, under her own filename *"FY27
> School Department Budget Projection as of 3.25.26"*. That is its address: rule 12 counts
> an email and who sent it as one. Recorded in `PROVIDED_BY` in `build_source_index.py` and
> shown on its row. Her membership is checkable against the Committee's own agenda
> letterhead, most recently 27 August 2026.
>
> **This was first recorded against the wrong file** — `fy27-proposals.xlsx` — and corrected
> the same day. Worth leaving on the record because the two are near-twins and getting them
> the wrong way round attributes the site's most load-bearing document to somebody who did
> not send it.

**Still open, and this is the one that matters: `xlsx/fy27-proposals.xlsx`.** Nearly every
budget-line figure on the site comes out of it and no route to it is recorded.

Two guesses were tested and neither closes it. It is **not** a renamed copy of the Lockwood
file — different sizes, different hashes, one of twelve shared zip members identical. And the
school budget page **as mirrored on 17 August 2026** publishes exactly one spreadsheet, the
FY26 Town Manager's budget sheets of 5 February 2025, which is not this; whether that page
carried it on 2 April 2026, the day this file's bytes were written, **cannot be checked** —
the Internet Archive holds no snapshot of the page. The town's FY27 Budget Hub links thirteen
documents and all thirteen are PDFs by content type.

`sources/xlsx/PROVENANCE.md` records what the file says about itself, and what that does not
establish.

**Also open:** `xlsx/fy27-budget-projection-2-24-26.xlsx` has no recorded route. We do have
the publisher's filename for it, from a byte-identical copy sitting in the repository root:
*"FY27 Budget Projection as of 2.24.26 with restorations.xlsx"*.

**What reduces the damage.** Every figure the site publishes from `fy27-proposals.xlsx` is
reproduced cell for cell in the Lockwood copy, which does have an address —
`scripts/verify_workbook_twins.py` finds **0 differences across columns E through M**, the
FY25 budget, FY26 final, FY26 actuals-to-date and encumbrances, and all four FY27 scenarios.
So a published figure can be checked against a document traceable to a named town official.
That is a mitigation, not a substitute: the file the pipeline actually reads still has no
provenance.

### 16. How the business certificate records were obtained

`business/merged_dataset.csv` and `business/categorized.csv` were copied from a separate
project (`~/lunenburgbusiness`) that cleaned and categorised the Town Clerk's records.
Nothing records how the underlying certificates were got — request, counter visit, or
download — so there is no address, and both files carry a `source` column reading `master`,
meaning they are our merge rather than the Clerk's records as the Clerk holds them. They
are also catalogued above the line, among documents published by the town, which on rule 3
is the wrong side.

---

## Not wanted

- **Video.** The FY20 page links a TelVue recording. Too large for what it would add.
- **The full CivicPlus document store.** Thousands of files, almost all irrelevant. The
  crawler walks the finance pages deliberately rather than enumerating ids.

---

## When something arrives

Drop it in `sources/` and tell me where it came from. Two rules from `CLAUDE.md` apply:

1. **Never mix a budget figure with an actual figure in one calculation.** Anything from
   Schedule A or a year-end report is actuals and belongs in
   `sources/analyses/budget-vs-actual.md`, not in the projection.
2. Anything that changes an assumption gets a citation in `model/citations.py` naming the
   document and the basis.
