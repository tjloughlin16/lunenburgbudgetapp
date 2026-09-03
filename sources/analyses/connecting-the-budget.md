# Connecting the school budget to the Town's books

Analysis, 3 September 2026. Every figure recomputed from `sources/data/lunenburg.db` by
`scripts/build_db.py`; the coverage counts come from `fy28/public/data/ledger.json`.

Written for the Town Manager, and published because a resident asking the same question
deserves the same answer. It sets out what can be followed from what was budgeted to what
was spent, where that stops, and which documents would move the line.

---

## In plain terms

Following a dollar from the school budget to the Town's books works at two levels and
stops at the third.

**It works for the department as a whole.** Budget against spend, both sides, every year
held. The two documents reconcile to **$1.93** across both school departments.

**It works by category** — 2710 Guidance, 2305 Teachers. The district prints the code over
each group and the Town's ledger carries the same code inside the account number, so the
two can be compared category by category. **41 of 45 codes match**, for FY2026 period 12
and no other period.

**It stops below that.** MUNIS shortens account names to ten characters, so `MS GUIDANC`
and `HS GUIDANC` are both coded 2710 where the budget has a separate row for each school.
Nothing in either document tells them apart, so a single budget line cannot be followed
into the ledger by anyone, inside the Town or outside it.

## Why the format of a report decides what can be answered

The spreadsheet export carries the whole coded account:

    0100-3-300-2710-04-4-65-1-511024

The printed PDF carries a label with the code removed. **That fourth segment is the only
thing joining the district's budget to the Town's books.** It is why the category
comparison holds for FY2026 period 12 alone: that is the one report that arrived as a
spreadsheet.

The printed copy is still worth having alongside it. The PDF carries its own options page —
account type, print totals only, the fund and period selected, whether revenue prints as a
credit — and the spreadsheet does not. That header is how anyone knows *how* a report was
run. **Spreadsheet for the data, PDF for the criteria.**

## What is missing, and from whom

Of the 70 report-years this project tracks for FY2023 to FY2026, **56 are not held**.

| from | documents | what they open |
|---|---|---|
| Town Accountant | 33 | transactions, the school's own funds, revenue, and every year before FY2026 |
| Lunenburg Public Schools | 10 | the budget documents themselves, plus a crosswalk that no report contains |
| Massachusetts DESE | 1 | published; this project will fetch it |

The two that open more than the rest combined:

1. **Year-end close, period 13**, for each year. Period 12 is the position before the books
   close; period 13 is the year as it finally stood. Without it no year's surplus can be
   computed from outside at all.
2. **Account Details for all school-related accounts, with the object code.** MUNIS already
   runs this report — it produced the athletics files sent in June. Those arrived as a
   single `CASH` account with no object code on any row, so the object code is worth naming
   explicitly rather than assuming.

## A question this project cannot answer from outside

**Is there any way to see what state aid actually paid for?**

What the data shows: no revenue account in anything held here carries a category code —
**0 of 222** — and the state aid accounts share no organisation code with any expense
account.

What that is taken to mean, which is an inference and not a measurement: Chapter 70 arrives
unrestricted into the general fund and is thereafter indistinguishable from any other
revenue, so nothing records which dollar paid which bill.

If that reading is right, the honest thing to publish is not an attribution but three
figures side by side: how much aid came in, what the department spent, and what the town
had to raise after aid. If it is wrong — if some fund structure, grant schedule or
reporting requirement ties aid to spending — that would be worth more than any document on
the list above.

The same question applies to the grants: is there anything recording which accounts a Title
grant or circuit breaker reimbursement paid into?

---

## The evidence

| claim | how it was checked |
|---|---|
| 41 of 45 category codes match | `SELECT DISTINCT function FROM account` intersected with `substr(function_group,1,4)` from `budget_line` |
| the category join is FY2026 period 12 only | `account.function` is populated for 270 rows, all FY2026 period 12; every earlier report is PDF-derived and carries no account string |
| account names truncate at ten characters | `MS TEACHER`, `ES TEACHER`, `KIND TEACH`, `SPED PRIVA` in `account.name` |
| 0 of 222 revenue accounts carry a category | `SELECT COUNT(*) FROM account WHERE account_type='revenue' AND function IS NOT NULL` |
| state aid shares no org with expenditure | intersection of `org` where `object LIKE '45%'` against expense accounts: 0 |
| the athletics detail carries no object code | 19 columns in `fund_1301_cash_journal`; none is an object, org or account code |
| 56 of 70 report-years not held | the coverage matrix in `fy28/public/data/ledger.json`, FY2023 to FY2026 |

**What this does not establish.** That the Town cannot produce any of the missing reports —
the configurations above are this project's reading of MUNIS, assembled from reports already
sent, and a correction is more useful than the data. And that state aid is untraceable
inside the Town's own system; that is the question above, not a finding.
