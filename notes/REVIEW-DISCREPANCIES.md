# FY2026 school budget — points for review

**To:** Town Manager and Town Accountant, Town of Lunenburg  
**Generated:** 2026-09-03 by `scripts/build_discrepancy_review.py`

Comparing two documents for the school department, FY2026:

- **the YTD report** — the Town Accountant’s `FY26 BUDGET YEAR TO DATE REPORT (9-1-2026).xlsx`, sheet `ACCOUNT DETAIL`, column E
- **the school budget** — the district’s FY27 budget projection workbook, FY26 FINAL BUDGET column, sheet `FY27 Budget Projection`, column B

Both state amounts against the same function codes. **37 of 45 codes agree.**

Every item below gives the account number and the school budget row, so each one
can be opened in both documents without searching. Nothing here is an accusation, and in
most cases the archive cannot say which document is right — only that they cannot
both be. Where I have a guess it is marked as one.

**Ordered by what needs an answer, not by size.** The largest amount is a
classification question where both documents hold the money; the smallest is
$1,896 of instructional materials.

| | category | items | sum involved | what it needs |
|---|---|---:|---:|---|
| **A** | **Spent without budget** | 6 accounts | $103,674 | **How these were authorised** |
| **B** | **Budgeted with no account to spend from** | 1 line | $40,000 | **Where this was budgeted** |
| **C** | Nothing appropriated, funded by transfer | 4 accounts | $44,121 | What each transfer paid for |
| **D** | Accounts not aligned | 4 pairs of codes | $550,708 | Which code is authoritative |
| **E** | Two figures on different bases | 2 accounts | $20,000 | Which basis the school budget column uses |
| **F** | Same total, different lines | 1 code | $1,896 | Which line the money sits against |

**The sums are the amounts involved, not money missing, and they do not add up.**
In D and F both documents hold the same total and disagree only about where it
sits.

---

# A. Spent without budget

*Nothing appropriated, no transfer in, and money paid out. 6 accounts, $103,674.*

| YTD report account | name | spent | in the school budget |
|---|---|---:|---|
| `0100-3-300-2330-03-2-12-1-511103` | KINDAIDREG | $93,691 | code `2330` — 5 lines under it, none with an amount |
| `0100-3-300-2330-03-2-13-1-511203` | KINDPARREG | $5,373 | code `2330` — 5 lines under it, none with an amount |
| `0100-3-300-2325-51-6-71-1-511003` | HS SPED LT | $1,500 | code `2325` — 5 lines under it, none with an amount |
| `0100-3-300-2415-51-4-05-2-555055` | SPEDINSTRM | $1,311 | code `2415` — 10 lines under it, none with an amount |
| `0100-3-300-2210-06-6-08-1-511019` | SAL SCH ST | $1,249 | code `2210` — 7 lines under it, none with an amount |
| `0100-3-300-2210-01-4-08-1-511102` | ES CLERK/T | $549 | code `2210` — 7 lines under it, none with an amount |

The two kindergarten accounts are $99,064 of it. The FY26 approved budget published the
kindergarten line as a cut, so the question is where these charges were provided
for. The school budget does carry a **Kindergarten Aides/Regular** line, row 333,
printed at $0, and a **Kindergarten Paraprofessionals** line, row 332, left blank.

# B. Budgeted with no account to spend from

*In the school budget, with no corresponding account anywhere in the YTD report.*

| school budget | code | amount | YTD report |
|---|---|---:|---|
| **Curriculum Adoption** — row 38 | `2110` | $40,000 | no account of any amount |

Taking every line on both sides, the school budget totals $26,287,476 and the YTD report $26,247,474. This
single line is all but $2 of that difference.

# C. Nothing appropriated, funded entirely by transfer

*The school budget appropriates **nothing** to these 4 accounts. Each was given
money by transfer during the year. One is nearly all of it.*

| YTD report account | name | appropriated | moved | spent |
|---|---|---:|---:|---:|
| `0100-3-300-2710-06-6-65-1-511002` | HS GUID SE | $0 | $42,967 | $43,980 |
| `0100-3-300-2325-51-4-71-1-511003` | ES LONG TE | $0 | $600 | $0 |
| `0100-3-300-2420-04-4-62-2-555005` | PHYS ED SU | $0 | $550 | $527 |
| `0100-3-300-2420-06-6-63-2-555028` | MUSIC BAND | $0 | $4 | $0 |

# D. Accounts not aligned

*The same money under a different function code in each document. Both documents
hold it; they disagree only about where it sits. The guess is mine, from the
amounts, and is not established.*

| codes | in the YTD report | in the school budget | amount | my guess |
|---|---|---|---:|---|
| `2710` vs `2900` | `0100-3-300-2710-04-4-65-1-511024`; `0100-3-300-2710-05-5-65-1-511024`; `0100-3-300-2710-06-6-65-1-511024`; `0100-3-300-2710-07-2-65-1-511024` | P.S. Social Worker row 364; E.S. Social Worker row 365; M.S Social Worker row 366; H.S. Social Worker row 367 | $369,029 | Same money, filed two ways. Nothing missing |
| `2310` ↔ `2320` | `0100-3-300-2310-51-0-06-1-511001` DWSPECIALI and `0100-3-300-2320-51-1-06-1-511025` ACERESROOM | District Wide Specials (ELL) row 302 and ACE Special Ed Resource Rm Teacher row 298 | $90,219 | One document has the two the wrong way round |
| `0300` vs none | `0100-3-300-0300-99-0-99-4-517006` SCHSALRESE | Salary Reserve, row 401 — under a section heading with no code | $90,770 | The same line |
| `4230` vs `4220` | `0100-3-300-4230-07-2-32-2-525003` REP OFF MA | P.S. Repair Office Machines, row 196 | $690 | The same line, coded two ways |

**The full code comparison**, for anyone checking:

| code | school budget group | YTD report | school budget | difference |
|---|---|---:|---:|---:|
| `2900` | Social Worker Salaries | $0 | $369,029 | **$369,029** |
| `2710` | Guidance Exp. / Guidance Salaries | $753,939 | $384,910 | **$369,028** |
| `0300` | *no group under this code* | $90,770 | $0 | **$90,770** |
| `2320` | Therapeutic Services | $663,335 | $753,555 | **$90,220** |
| `2310` | Tutoring Cont. Ser. / Teachers Specialists - Special Education | $2,187,067 | $2,096,848 | **$90,219** |
| `2110` | Special Education / System Curriculum Adop / Curriculum/Spec Ed Directors / Special Education Clerical | $423,481 | $463,481 | **$40,000** |
| `4220` | Maint. of Buildings | $367,000 | $367,690 | **$690** |
| `4230` | M.S. Repairs / H.S. Repairs / Maintenance Repairs | $57,145 | $56,455 | **$690** |

# E. Two figures on different bases

*Only accounts with a transfer can show which basis the school budget uses,
because only there do the appropriation and the revised budget differ.
There are 82 such accounts: the school budget matches the appropriation on 74,
the revised budget on 1, and 7 cannot be told apart.*

| YTD report account | appropriated | moved | revised | school budget says | school budget line |
|---|---:|---:|---:|---:|---|
| `0100-3-300-3510-06-6-67-2-535018` ATH INS | $29,000 | -$20,000 | $9,000 | **$9,000** | Athletic Insurance, row 171 |
| `0100-3-300-3510-06-6-67-2-535020` DUES/FEES | $0 | $29,965 | $29,965 | **$20,000** | Athletic Dues & Fees, row 172 |

Insurance matches the revised figure rather than the appropriation; dues and fees
matches neither. Which basis does the school budget column use, and for which lines?

# F. Same total, different lines

*The code total agrees, so nothing is missing and no dollar is unaccounted for.
The money sits against different lines inside the code — which is what happens
when one account covers what the school budget splits across schools.*

| code | YTD report | school budget |
|---|---|---|
| `2415` | `0100-3-300-2415-51-5-05-2-555055` SPEDINSTRM $1,896 | E.S. Special Education Instr. Materials $1,492, row 84; M.S. Special Education Instr. Materials $404, row 97 |

## What would close most of this in one step

**The account master** — the mapping from each MUNIS account number to its
function code and description. **D and F answer themselves from it.**

**A, B, C and E need a word from somebody.** A mapping cannot say how a charge was
authorised against an account with no budget, show a budget line that has no
account, say what a transfer paid for, or explain which basis a column is on.

## Method, in four lines

The join is the function code in the fourth segment of the MUNIS account string
(`0100-3-300-2330-51-2-13-1-511203`), which is the same code the school budget
prints over each group. Within a code, lines are paired **by amount**, which is not a
key: it shows a figure of that size exists on both sides, never that the two are
the same line. Full working in `sources/data/fy26-code-reconciliation.xlsx`.

