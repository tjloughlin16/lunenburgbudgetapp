---
status: reference
---
# Reclasses and one-sided journal entries in the school journal

Established 27 November 2026 while reading `/school-all-funds/fy2026-closeout/why-it-was-left`.
Every figure here was computed from `sources/data/munis-school-journal.csv` through
`scripts/journal.py`; rerun before quoting. The source is Report 1 (private PDF; provenance
`sources/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md`).

## The case that started it: MIIA health insurance, FY2026

- On the vendor table the school general fund paid MIIA HEALTH BENEFITS $836,416 less in FY2026.
- The account itself, `0100-3-300-5200-99-1-99-2-570001` HEALTH INSURANCE, spent $3,248,744.44 in
  FY2025 and $3,622,881.65 in FY2026 (+$374,137, +11.5%), against a $3,701,195 budget.
- MIIA invoices (source `API`, vendor 002866, check numbers) post monthly July–March; the last is
  "SCHOOLS - HI - MAR", $307,483.91, 2 April 2026.
- Then four general-journal entries (source `GEN`, no payee, no invoice, no check) on 12 June 2026,
  **$980,039.30** in all, whose other side is in no school account (Report 1 p652 l40–43):
  2026/12/000235 $314,100.80 "crt wrt 57 26 deductions crt" (doc_no `health`);
  000236 $335,040.55 "february health ins" (`feb`); 000239 $7,664.16 "crt wrt 45 26 to acct"
  (`March`); 000240 $323,233.79 "reclass to school" (`april`).
- 2026/12/000237 $303,499.32 (`may`) was posted to `…570008` UNEMPLOYMENT COMPENSATION, then
  moved to health insurance by 2026/12/001640 on 30 June.
- 2026/12/001641 "MOVE HEALTH INS FY26" moves $99,017.36 off the general fund to fund 1312
  (extended day) and five fund-2200 accounts; its +$42,398.05 line is reversed by 001642.
- Twelve premium-sized amounts ($294k–$335k) appear across invoices and journals: consistent with a
  full year charged. A COUNT, not a match; no entry is tagged January.

## Across years: net of GEN journals whose legs do not balance inside the school journal

| FY | school GF spent | GEN lines | journals one-sided | net |
|---|---:|---:|---:|---:|
| 2023 | 22,436,810 | 207 | 18 | 1,588,125 |
| 2024 | 22,755,089 | 85 | 17 | 1,503,759 |
| 2025 | 24,560,511 | 172 | 15 | 1,570,411 |
| 2026 | 25,657,318 | 215 | 22 | 3,148,868 |

Most of every year is the summer-pay accrual (FY2025 2025/12/000677 $1,361,740; FY2026
001471/001474/001475/001476, about $1.5M), whose other side is a liability, not an expense.
FY2026's doubling is mostly the health insurance above.

**The measure's own defect:** a correction booked under a different journal number counts as two
one-sided journals (000237 and 001640; 001641 and 001642). Pairing them is part of the join tool.

## Why joins fail here (known so far)

1. **Scope.** Report 1 is school accounts only. The other side of a town↔school move is in the
   Town's ledger, which is held only as account totals (`sources/data/munis-ledger.csv`).
   Request drafted: `notes/outbound/drafts/RECORDS-REQUEST-TOWN-HEALTH-INSURANCE-DETAIL.md`.
2. **Corrections under new journal numbers**, so journal number alone does not pair them.
3. **No payee on GEN lines**, so vendor views lose reclassed cost.
4. **Free-text month tags** in `doc_no` (`feb`, `March`, `april`, `may`) are the only link from a
   reclass to the invoice month it replaces.
5. **Accruals** put several months' cost into June (period 12).

## What is safe and what is not

Account and category totals tie to the period-13 reports to the cent and already include every
reclass. At risk: views by VENDOR, by MONTH, and comparisons across the school/town line.
