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

### 8. Municipal Finance Trend Dashboard, Lunenburg

Five-year indicators including free cash as a percentage of budget, which is exactly the
comparison the reserve argument needs.

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
