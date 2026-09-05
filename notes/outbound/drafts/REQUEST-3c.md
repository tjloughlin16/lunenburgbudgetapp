# Records request 3c — athletics ledger and vendor warrants

Ready to send. Covers `notes/DATA-WANTED.md` §3c. Between them these close the two
questions `sources/analyses/athletics.md` cannot answer: whether the fund ran a deficit in
FY25, and what athletic transportation actually cost.

**To:** Finance Director / Town Accountant, Town of Lunenburg
**Basis:** M.G.L. c. 66 § 10

---

## Suggested wording

> Under the Massachusetts Public Records Law, M.G.L. c. 66 § 10, I request the following
> records. Where a record exists as a spreadsheet or a report that can be exported, I would
> be grateful to receive it in its native format (.xlsx or .csv) rather than as a PDF, as
> the column structure is what makes it usable.
>
> **1. General ledger detail for school athletics, fiscal years 2023 through 2026:**
> account org `S3066672` (athletics expenses) and org `S3066671` (athletics salaries),
> all object codes, including object `535016` (transportation). Transaction-level detail
> — date, vendor, amount, object code — rather than a summary.
>
> **2. General ledger detail for fund 1301** (recorded in the town's special revenue
> report as CHAPTER 658 REVOLVING FUND / Athletics Revolving), fiscal years 2023 through
> 2026, same level of detail.
>
> **3. The special revenue report or fund balance sheet for fund 1301 for fiscal year
> 2025**, in the same format as the FY2026 report already provided.
>
> **4. Vendor warrants approved by the Select Board** for fiscal years 2023 through 2026,
> or, if that is burdensome, the warrant detail limited to payments charged to the accounts
> in items 1 and 2.
>
> **5. Athletic fee receipts** as recorded in the revolving fund for fiscal years 2024
> through 2026, including any sport-specific surcharges, and the fee schedule in force in
> each of those years.
>
> If any part of this is unduly burdensome, please tell me which part and I will narrow it
> — items 2 and 3 are the ones I would keep if only one could be filled.

---

## Why each item, and what it settles

| item | question it closes | where that question is recorded |
|---|---|---|
| 1. GF athletics GL | Does a bus company appear beside a dollar figure? Nothing in the 3,230-file archive does. Also shows whether the line is one annual purchase order or a stream of invoices — which decides whether every reported "actual" on it is a payment or a commitment. | `athletics.md` §4 |
| 2. Fund 1301 GL | When transportation stopped being paid from the fund, and whether the fund was redirected or ran out. A fund that ran out looks different in a ledger from one that was told to stop. | `athletics.md` §4a, §6 |
| 3. FY25 fund report | Whether the fund ran the deficit three people described in 2025. It closed FY25 at **+$110,248**, so the year-end does not show it. We hold the endpoint and not the path. | `athletics.md` §4a |
| 4. Vendor warrants | The only record that names a carrier and an amount. | `athletics.md` conclusion 6 |
| 5. Fee receipts + schedules | Why the fund collected **$194,609 gross** in FY26 when the published schedule and reasonable sibling and waiver assumptions produce **$130,129**. That gap is currently carried as a two-sided range in the app because we cannot say which explanation is right. | `athletics.md` §6, `model/athletics.py → FEE_CALIBRATION` |

## Note on format

Item 1 was reportedly supplied to another requester as "monthly debits" and set aside as
not useful. It is the most valuable item on this list. Transaction detail with vendor names
is the only thing in the town's records that can distinguish what athletics **cost** from
what the town **appropriated** — which is the distinction this entire analysis turns on.

## On arrival

1. Hash it, catalogue it in `scripts/build_source_index.py` with its address and the date
   of the request and response — rule 12, all at once, not retrofitted.
2. Write an extractor to `sources/data/`, so the figures are re-derivable.
3. Tie the transportation totals against the general fund line, year by year.
4. Update `athletics.md` §4, §4a and §6 — moving each claim from *reported* to *established
   or refuted*, whichever it turns out to be.
5. **Then** decide whether any of it changes a published figure. Not before.
