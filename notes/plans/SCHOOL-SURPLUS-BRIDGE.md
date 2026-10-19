# Plan: what the school did not spend, and where it went — a variance bridge from the journal

Written 19 October 2026. **Blocked until the school MUNIS journal is clean and published.**
TJ's rule (CLAUDE.md 13e): process, verify it is safe, publish, *then* build against it. As
of writing, the redacted CSVs failed a privacy read and are held in
`build/private/munis/held-2026-10-19/`; `scripts/extract_munis_school_journal.py` is being
fixed. Start this only when `sources/data/munis-school-journal.csv` is back, re-read, and
`redactions.csv` names it as the public copy.

## The question

TJ: *"can we figure out what they did not spend that year compared to previous years
(knowing FY25 ALSO had a surplus...) in the categories with the biggest surpluses. IOW, we
have the categories from the other reports, but now we should be able to answer what went
in and out and why."*

The surplus reports (`sources/analyses/fy25-school-surplus.md`, `fy26-school-surplus.md`,
built by `scripts/build_school_surplus.py` from the period-13 spreadsheets) already say HOW
MUCH each category came in under. The journal holds every posting behind those totals, so it
can say WHERE the money did or did not go, year against year. The journal ties to the
period-13 spreadsheets to the cent on actual and revised budget, so it does not change the
headline figures; it explains them.

## The method: a variance bridge per category

For each category, step from one year to the next in labelled pieces, each a measurement:

1. **Budget side.** Original vote (`BUC`) and every transfer in/out (`BUA`), dated. A transfer
   that cut a budget is not underspending.
2. **Spending side, by how money left.**
   - payroll (`PRJ`);
   - invoices, vendor by vendor (`API`): which vendors stopped, started or shrank;
   - June reclassifications (`GEN`): spending moved between lines at year end, which makes
     one line look under and another over with nothing bought;
   - open purchase orders carried over (`POE`/`POL`/`POM`/`SOY`/`YEC`).
3. **Across funds — the most important part.** The journal covers every school special fund
   (grants, circuit breaker, school choice, revolving), not only the general fund. For every
   line that dropped, look for the matching amount appearing in a special fund. That is
   rule 11's blind spot made visible: a line falling because a grant took it over looks
   identical, in the budget, to a line falling because nothing was bought.
4. **Timing.** The month payroll stopped, the date a contract ended, the share of the year
   settled in June.

Output per category, in this shape (figures generated, never typed — rule 2):
*FY26 spent $X less than FY25 on this line: $A is one vendor not billed after <month>; $B
moved to <fund> from <month>; $C was reclassified out in June; $D is a transfer that reduced
the budget.*

## Steps

1. **Rank** categories by surplus in FY25 AND FY26, using the categories the surplus reports
   already use (`build_school_surplus.py`), so the new work lines up with what is published.
   Under budget two years running is a different finding from a one-year surplus.
2. **Bridge** the top five or so, FY23 → FY26.
3. **Follow the money across funds** for every line that dropped.
4. **Minutes check** for each finding (rule 15a: `scripts/search_minutes.py`, same line,
   same year).
5. **Register what stays unknowable** in `sources/data/money-gaps.csv` (rule 7c).
6. **Write it as the next layer of the existing surplus reports**, via the generator — not a
   new report, and not prose with typed figures. Verifier recomputes every figure by a second
   route (rule 9).

## Settle first, before any bridge

- **Payroll grain.** Are `PRJ` lines per pay run or per person? Either way, dollars
  stopping is a proxy for a vacancy, never proof of one (rule 7). If per person, the masking
  rule decides what can be shown.
- **Open purchase orders at FY26 year end.** The handoff (`notes/HANDOFF-MUNIS-JOURNAL.md`)
  says $246,767; `fy26-school-surplus.md` says $236,767. Exactly $10,000 apart: a typo, or
  two counts of different accounts. Settle from the data.
- **Org 13012, "School Non-Recurring".** The journal's FY26 general-fund actual is above the
  period-13 spreadsheet by exactly that org, which the spreadsheet lacks. Decide whether it
  belongs in the general-fund surplus. This is the one place the headline could move.
- **FY26 year-end close** is not posted in this run (encumbrances still open). Say so on
  every FY26 figure that depends on it.

## Leads already visible (to TEST, not to state)

From the handoff and the surplus report. Each is a measurement plus a hypothesis; the
bridge is what tests them.

- A psychologist salary line paid nobody in FY26 while a contracted psychologist was billed
  from a contracted-services line. Consistent with a vacancy covered by a contractor; the
  ledger cannot show that was the reason.
- Kindergarten aide payroll moved accounts in FY26 with no budget transfer recorded. Bears on
  the in-district special education escalator (CLAUDE.md, the standing questions).
- The circuit breaker's year-end tuition reclassification: one June `GEN` entry.
- Health insurance was posted mostly by June reclassification entries, not invoices.

## What it cannot do

- Say WHY anything happened. Postings are facts; reasons are hypotheses (rule 7).
- Count people. Payroll dollars are not staff (rule 7, rule 11).
- See intent behind June purchase orders. It can sort them by how firm they look (vendor,
  date opened, what they say they're for, whether anything has been paid against them),
  not know which will be paid.
