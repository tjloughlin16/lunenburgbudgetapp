# Cover email — draft, not sent

Accompanies `REVIEW-DISCREPANCIES.pdf`. Drafted 2026-09-03.

Three things this draft does deliberately, each because the earlier version did the
opposite:

1. **It leads with $1.93.** The attachment already says no money is missing and that the
   two documents reconcile to $1.93 across both school departments. An earlier draft opened
   with "these will create audit issues", which tells a Town Accountant their books have
   audit exposure — and contradicts the document it is covering. Rule 8: findings arrive as
   what this means for planning, never as what they got wrong. These are people this
   project needs for years.
2. **It asks for the redaction at the same time as the data.** "Account Details for all
   school accounts" is the report that carries `VDR NAME/ITEM DESC`, which on a special
   education line is often a parent rather than a company. Asking for the data without
   asking for the omission is asking for the confidential version.
3. **It corrects the report parameters.** The earlier draft asked for the revenue report as
   `Account Type EXPENSE`, copied from the line above. Run as written it returns expenses
   again and costs a round trip.
4. **It is short.** A first version ran to 550 words. The recipient is a Town Manager with
   a full inbox, and length is the most common reason a request sits. Every hedge, every
   restated point and every explanation written for my benefit rather than his is gone.
   Where a section and a question said the same thing — the fund-mapping gap — one of them
   went. The table carries what a paragraph used to. A first attempt at this cut claimed to
   be concise and removed 5%; the real cut was 35%, and almost all of it was subordinate
   clauses explaining my reasoning to a reader who did not ask for it.
5. **The confidentiality ask is deliberately a placeholder.** It names the two columns and
   the reason in three lines and then says a separate message will follow. TJ is handling
   that thread on its own, and the full version — the export-layout change, CSV rather than
   .xlsx, vendor number instead of name — is in `notes/INTAKE-FOR-THE-TOWN.md`, ready to
   send. **It must go before any Account Detail is produced, not after.** The concern is not
   that the ask is long; it is that a request for Account Detail without it is a request for
   the confidential version, and the Town would fill it in good faith.
6. **It keeps the tier model, and makes the ask fall out of it.** A first revision cut the
   tiers to make the email quick for whoever runs the report. That was the wrong trade: half
   the point of writing to the Town Manager is to offer a shared way of talking about this
   data, so that "which tier is that?" becomes a question both sides can ask. The ask reads
   as arbitrary without it and as obvious with it — it is simply the tier that is missing.
   The tiers are also already in the project's own data: `/api/coverage` distinguishes
   `level: account` from `level: department`, and says a department rollup cannot be traced
   to a budget line. That is the same distinction.

---

Subject: FY26 school budget — points for review, and how I'm thinking about the data

Hello again,

Attached: five kinds of place where the year-to-date report and the school budget say
different things about the same account. Each one gives the account number and the budget
row.

**The two reconcile to $1.93 across both school departments** — no money is missing, and
this is not an audit finding. 38 of 45 function codes agree. The seven that do not make a
whole category impossible to compare from outside, and that is what I am trying to fix.

**How I think about the data now** — three levels of resolution, possibly useful shorthand
between us.

| | what it is | the document or report | what it answers | where I am |
|---|---|---|---|---|
| **Tier 1** | Totals | The district's budget workbook — `FY27 Budget Projection`, sheet `FY27 Budget Projection`. And the year-to-date report run with **Print Totals Only `TRUE`** | How much was planned, how much is left | **Have it.** Published, and back several years |
| **Tier 2** | Categories, by function code — 2710 Guidance, 2325 SpEd Substitutes | The year-to-date report run with **Print Totals Only `FALSE`** — e.g. `FY26 BUDGET YEAR TO DATE REPORT (9-1-2026).xlsx`, sheet `ACCOUNT DETAIL`, which is the one this review is built on | Whether a category is over or under, and by how much | **Have it**, for FY26 |
| **Tier 3** | Individual accounts, and revenue by fund | **Account Detail** — e.g. `FY24 Account_Detail_.xlsx`, the athletics revolving fund detail you sent in June. Plus the **Revenue report** for state and grant money | Where money actually came from and went | **Only for athletics.** This is the gap |

The attached review is a Tier 2 finding and none of it can be settled at Tier 2. Even Tier 3
will not give a clean line-by-line map: MUNIS gives `MS GUIDANC` and `HS GUIDANC`, both
coded 2710, where the budget has a row per school. That is inference, not tracking.

**Tier 3 is what would help** — it looks like the only route to mapping Chapter 70 and Title
money onto the budget's own categories.

- **Account Detail** — school-related accounts, including the grant and revenue funds, not
  only 300 and 301
- **Expenditure detail** — Account Type `EXPENSE`, Print Totals Only `FALSE`
- **Revenue report** — Account Type `REVENUE`, Print Totals Only `FALSE`

**Spreadsheet rather than PDF where there is a choice.** The sheet gives
`0100-3-300-2710-04-4-65-1-511024`; the PDF gives only a label. That code is what makes any
of this joinable.

**One caveat on Account Detail: two of its 25 columns can name a person** — `VDR NAME/ITEM
DESC` and `COMMENTS`. On a special education line the vendor is sometimes a parent rather
than a company, and I do not need to know who anyone is. I will follow up separately on the
cleanest way to leave those out; nothing needs deciding now.

**Two questions:**

1. Is there an accounting relationship between the revenue and special revenue funds and the
   school budget's lines, or are they separate? I have assumed separate.
2. Can you share the Town's End of Year Financial Report submission to DESE? It separates
   spending by fund, which I cannot reconstruct from anything I hold.

Whatever form is least work is fine — and do tell me if something is more trouble than it is
worth.

Thank you again,

Tj
