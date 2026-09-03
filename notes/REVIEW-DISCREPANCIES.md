# FY2026 school budget — points for review

**To:** Town Manager and Town Accountant, Town of Lunenburg  
**Generated:** 2026-09-03 by `scripts/build_discrepancy_review.py`

Comparing two documents for the school department, FY2026: the Town Accountant’s
MUNIS year-to-date budget report for period 12, and the district’s FY27 budget
projection workbook, which carries the FY26 final budget. Both state amounts against
the same function codes.

**37 of 45 function codes agree. The rest are below.** Nothing here is an accusation,
and in most cases the archive cannot say which document is right — only that they
cannot both be. Where I have a guess it is marked as one.

| | category | items | amount involved | what it needs |
|---|---|---:|---:|---|
| **A** | Accounts not aligned | 4 pairs of codes | $550,708 | Which code is authoritative |
| **B** | Same total, different lines | 2 codes | $21,896 | Which line the money sits against |
| **C** | **Spent without budget** | 6 accounts | $103,674 | **How these were authorised** |
| **D** | **Budgeted with no account** | 1 line | $40,000 | **Where this was budgeted** |
| **E** | Two figures on different bases | 2 accounts | $20,000 | Which basis the workbook column uses |
| **F** | Money moved, no budget line | 7 accounts | $164,961 | What each transfer was for |

**The amounts are the sums involved, not money missing, and they do not add up.** In
most rows both documents hold the same total and disagree about where it sits. Taking
every line on both sides the workbook totals $26,287,476 and the ledger $26,247,474, a difference of
**$40,002** — item 4 and rounding.

---

# A. Accounts not aligned

*The same money under a different function code in each document. In every case
both documents hold it; they disagree only about where it sits. The guess is
mine, from the amounts, and is not established.*

| codes | what | amount | my guess |
|---|---|---:|---|
| `2710` vs `2900` | Social worker salaries — 4 accounts in the ledger under Guidance; the workbook gives them their own heading | $369,029 | Same money, filed two ways. Nothing missing |
| `2310` ↔ `2320` | District Wide Specials (ELL) $185,878 and ACE Special Ed Resource Rm Teacher $95,659 are each under the other's code | $90,219 | One document has the two the wrong way round |
| `0300` vs none | Salary reserve — coded in the ledger, carried under a section heading with no code in the workbook | $90,770 | The same line |
| `4230` vs `4220` | P.S. Repair Office Machines | $690 | The same line, coded two ways |

**The full code-level comparison**, for anyone who wants to check it:

| code | workbook group | ledger | workbook | difference |
|---|---|---:|---:|---:|
| `2900` | Social Worker Salaries | $0 | $369,029 | **$369,029** |
| `2710` | Guidance Exp. / Guidance Salaries | $753,939 | $384,910 | **$369,028** |
| `0300` | *no group under this code* | $90,770 | $0 | **$90,770** |
| `2320` | Therapeutic Services | $663,335 | $753,555 | **$90,220** |
| `2310` | Tutoring Cont. Ser. / Teachers Specialists - Special Education | $2,187,067 | $2,096,848 | **$90,219** |
| `2110` | Special Education / System Curriculum Adop / Curriculum/Spec Ed Directors / Special Education Clerical | $423,481 | $463,481 | **$40,000** |
| `4220` | Maint. of Buildings | $367,000 | $367,690 | **$690** |
| `4230` | M.S. Repairs / H.S. Repairs / Maintenance Repairs | $57,145 | $56,455 | **$690** |

# B. Same total, different lines

*The code totals agree, so nothing is missing. The money sits against different
lines inside it.*

| code | ledger | workbook |
|---|---|---|
| `2415` | SPEDINSTRM $1,896 | E.S. Special Education Instr. Materials $1,492; M.S. Special Education Instr. Materials $404 |
| `3510` | DUES/FEES appropriated $0, revised $29,965 | Athletic Dues & Fees $20,000 |

# C. Spent without budget

*Nothing appropriated, no transfer in, and money paid out. 6 accounts, $103,674.*

| account | name | spent |
|---|---|---:|
| `0100-3-300-2330-03-2-12-1-511103` | KINDAIDREG | $93,691 |
| `0100-3-300-2330-03-2-13-1-511203` | KINDPARREG | $5,373 |
| `0100-3-300-2325-51-6-71-1-511003` | HS SPED LT | $1,500 |
| `0100-3-300-2415-51-4-05-2-555055` | SPEDINSTRM | $1,311 |
| `0100-3-300-2210-06-6-08-1-511019` | SAL SCH ST | $1,249 |
| `0100-3-300-2210-01-4-08-1-511102` | ES CLERK/T | $549 |

The two kindergarten accounts are $99,064 of it. The FY26 approved budget published the
kindergarten line as a cut, so the question is where these charges were provided for.

# D. Budgeted with no account to spend it from

*In the workbook, with no corresponding account anywhere in the ledger.*

| workbook line | code | amount |
|---|---|---:|
| Curriculum Adoption | `2110` | $40,000 |

Taking every line on both sides, the workbook totals $26,287,476 and the ledger $26,247,474. This single
line is all but $2 of that difference.

# E. Two figures on different bases

*Only accounts with a transfer can show which basis the workbook uses, because only
there do the appropriation and the revised budget differ. There are 82 such accounts:
the workbook matches the appropriation on 74 of them, the revised budget on 1, and
7 cannot be told apart because they pair with nothing.*

| account | appropriated | moved | revised | workbook says |
|---|---:|---:|---:|---:|
| `ATH INS` athletic insurance | $29,000 | -$20,000 | $9,000 | **$9,000** |
| `DUES/FEES` athletic dues and fees | $0 | $29,965 | $29,965 | **$20,000** |

Insurance matches the revised figure rather than the appropriation; dues and fees
matches neither. Which basis does the workbook column use, and for which lines?

# F. Money moved, with no budget line to match

*7 accounts had money transferred in or out and pair with nothing in the workbook.*

| account | name | appropriated | moved | spent |
|---|---|---:|---:|---:|
| `0100-3-300-0300-99-0-99-4-517006` | SCHSALRESE | $90,770 | -$90,770 | $0 |
| `0100-3-300-2710-06-6-65-1-511002` | HS GUID SE | $0 | $42,967 | $43,980 |
| `0100-3-300-3510-06-6-67-2-535020` | DUES/FEES | $0 | $29,965 | $21,481 |
| `0100-3-300-2325-51-4-71-1-511003` | ES LONG TE | $0 | $600 | $0 |
| `0100-3-300-2420-04-4-62-2-555005` | PHYS ED SU | $0 | $550 | $527 |
| `0100-3-300-4230-07-2-32-2-525003` | REP OFF MA | $690 | -$105 | $585 |
| `0100-3-300-2420-06-6-63-2-555028` | MUSIC BAND | $0 | $4 | $0 |

## What would close most of this in one step

**The account master** — the mapping from each MUNIS account number to its function
code and description. **A and B answer themselves from it**, which is most of the
codes and most of the dollars.

**C, D, E and F need a word from somebody.** A mapping cannot show a line that has no
account, say how a charge was authorised against an account with no budget, explain
which basis a column is on, or say what a transfer was for.

## Method, in three lines

The join is the function code in the fourth segment of the MUNIS account string
(`0100-3-300-2330-51-2-13-1-511203`), which is the same code the workbook prints over
each group. Within a code, lines are paired **by amount**, which is not a key: it shows
a figure of that size exists on both sides, never that the two are the same line. The
full working is in `sources/data/fy26-code-reconciliation.xlsx`.

