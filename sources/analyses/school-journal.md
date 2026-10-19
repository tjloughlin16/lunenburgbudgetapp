# The school journal

Every posting to every school account, FY2023 to FY2026, in every fund, with its payee and date.

## The files

| file | what it holds | size | sha256 |
|---|---|---:|---|
| [`munis-school-journal.csv`](/docs/data/munis-school-journal.csv) | every journal line | 12.6 MB | `b8303a62d2e45fd5…` |
| [`munis-school-journal-accounts.csv`](/docs/data/munis-school-journal-accounts.csv) | every account, with the FY2026 figures the report prints | 545 KB | `b5974c6932cf4b85…` |
| [`munis-school-journal-image-pages.csv`](/docs/data/munis-school-journal-image-pages.csv) | the lines of the three picture-only pages, read by eye and redacted by the same rule | 16 KB | `7c6481e8243770f3…` |

Our redacted reading of the Town’s MUNIS report `glytdbud`, run with journal detail from FY2023 period 0 to FY2026 period 13 and delivered under a records request. The Town’s own PDF is held privately and not published; why, and what it is, is in the [provenance note](/docs/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md).

## What a line is

One row per journal line: a single posting to one school account, in any fund, with its date, source code, payee and description. A payroll line is one account’s share of one pay run, not a person.

| column | holds |
|---|---|
| `fiscal_year, period` | the MUNIS fiscal year and period; period 0 is the opening entry, 13 the closing |
| `source` | the MUNIS source code; see the table below |
| `posts_to` | which column of the printed report the line adds to |
| `amount` | dollars; a credit is negative |
| `fund, org, account, object` | where it posts; `object` begins 5 for spending and 4 for revenue |
| `vendor, vendor_no` | the payee, or `individual (redacted)` or empty where masked |
| `description, comment` | the Town’s text, after our redaction |
| `masked` | which fields on the line we masked, and why |
| `name_basis` | the public record that shows a named person is an employee, or `paid as vendor` |
| `page, line` | where the line is on the Town’s printed report |

### Source codes

Which code adds to which column of the printed report is not assumed: it is the only assignment under which every account closes.

| source | posts to | what produced it | lines |
|---|---|---|---:|
| `API` | actual | invoice | 13,592 |
| `APM` | actual | invoice | 24 |
| `CRP` | actual | receipt | 3,567 |
| `GEN` | actual | journal entry | 905 |
| `GRV` | actual | journal entry | 167 |
| `PRH` | actual | payroll | 52 |
| `PRJ` | actual | payroll | 9,512 |
| `GEL` | encumbrance | — | 1 |
| `POE` | encumbrance | — | 4,843 |
| `POL` | encumbrance | — | 12,203 |
| `POM` | encumbrance | — | 1,713 |
| `SOY` | encumbrance | — | 193 |
| `YEC` | encumbrance | — | 149 |
| `BUC` | original budget | — | 1,078 |
| `BUA` | transfer | — | 1,044 |

**Payroll lines are not people.** Every `PRJ` and `PRH` line is one line per account per payroll warrant; no person is recorded. 35 pay runs posted in FY2023, 33 in FY2024, 31 in FY2025 and 36 in FY2026; 0 of 9,564 payroll lines name anyone.

### By year

| fiscal year | lines | spending, every fund | of which general fund |
|---|---:|---:|---:|
| FY2023 | 12,585 | $26,824,771 | $22,436,810 |
| FY2024 | 12,450 | $27,193,179 | $22,755,089 |
| FY2025 | 12,133 | $28,390,116 | $24,560,511 |
| FY2026 (not closed) | 11,875 | $29,661,795 | $25,657,318 |

Spending is actuals on expense accounts, net of every reversal and reclassification. It is the school ledger’s spending, not what the schools cost: see what it cannot show, below.

## The redaction

The rule is about one thing: never attaching a name to a disability or a service a child receives. So a child, or a parent acting for their child, is hidden wherever a line could tie them to one, and the people PAID to provide services are not.

- **Providers and vendors are named**: name, service, amount, invoice and check number.
- **Recipients are masked**: a child, or a parent or family acting for their child. Their name, vendor number, invoice and check number go, and so does every trace of them the extractor finds in a description; it refuses to write if any survives.
- **Staff named in their role are kept** where a public record shows they are an employee: 2,442 lines.
- **A special education family is never named**, even on a transportation line, where other families are.

1,606 lines carry at least one masked field. By field:

| field masked | lines |
|---|---:|
| `description` | 1,202 |
| `doc_no` | 516 |
| `vendor_no` | 355 |
| `check_no` | 157 |
| `vendor` | 41 |
| `comment` | 2 |

The three pages the Town delivered as pictures are read by eye into `munis-school-journal-image-pages.csv` (141 lines), through the same redaction.

**No report built on this journal may isolate a masked recipient.** A masked amount appears only inside an aggregate that also holds other payees.

## How it differs from the period-13 spreadsheets

This run holds one general fund department the Town’s period-13 school spreadsheets do not: department 301, 13012 SCHOOL NON-RECURRING EXPENSES. It carried $40,000 of the FY2026 original budget, and $10,000 of the $246,767 still on order at the run; the spreadsheets’ department 300 holds the other $236,767. Its available balance at the run was -$17,862.

## What it cannot show

- The FY2026 close: encumbrances were still open when the report was run, so every FY2026 figure can still move.
- What anything costs in full. A line is a posting to a school account; benefits and costs charged to other accounts are not in it.
- Who was paid on a pay run. Payroll lines carry no person.
- Who received a service. Families and children are masked and cannot be counted.
- Earlier years account by account against the report itself: it prints figures for FY2026 only.

Limits that a better reading cannot close are registered in `sources/data/money-gaps.csv` and published at `/what-we-cannot-answer`.

## Where it comes from

| what | where |
|---|---|
| How the journal reached us, and what the Town redacted | /docs/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md |
| The decision to publish our redacted reading, not the raw | /docs/data/redactions.csv |
| The reading and the redaction rule, in full | scripts/extract_munis_school_journal.py (its header) |
| The definitions every journal report shares | scripts/journal.py |

