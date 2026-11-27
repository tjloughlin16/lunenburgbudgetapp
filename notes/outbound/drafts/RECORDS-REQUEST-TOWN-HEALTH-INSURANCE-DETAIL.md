# Records request — Town health insurance journal detail, FY2023 to FY2026

Drafted 27 November 2026. **Not sent.** Register row: `notes/reference/records-requests.csv`,
id `DRAFT-2026-11-27-town-health-insurance-detail`.

**To:** Jennifer Warren-Dyment, Town Manager
**Subject:** Public records request — journal detail for the Town's health insurance accounts

---

Dear Ms. Warren-Dyment,

Under M.G.L. c. 66, § 10, I request the following record. It is the same report the Town ran
for the school department on 7 October 2026 (Report 1), pointed at two Town accounts.

**The report:** the MUNIS Year-to-Date Budget Report (`glytdbud`) with journal detail switched
on, for:

- `0100-19142-570001` TOWN ACTIVE HEALTH INSURANCE
- `0100-19142-570009` TOWN RETIREES HEALTH INSURANCE

**Period:** fiscal 2023 period 0 to fiscal 2026 period 13, to match Report 1. If only one year
is practical, fiscal 2026 periods 1 to 13 is the one that matters.

**Why these two accounts.** In the school journal, the school's health insurance account
(`0100-3-300-5200-99-1-99-2-570001`) receives four journal entries dated 12 June 2026 whose
other side is not in the school's accounts:

| journal | amount | description |
|---|---:|---|
| 2026/12/000235 | 314,100.80 | crt wrt 57 26 deductions crt |
| 2026/12/000236 | 335,040.55 | february health ins |
| 2026/12/000239 | 7,664.16 | crt wrt 45 26 to acct |
| 2026/12/000240 | 323,233.79 | reclass to school |

I would like to see where each came from. If their other side is on an account other than the
two above, the journal detail for that account would answer the same question, and I would
gladly take it instead.

Health insurance premiums post as monthly totals, so I do not expect the report to carry any
individual's name. If a line does, it may be masked.

An Excel export would be ideal; I understand from October that the export was producing one
row, so a PDF is completely fine.

Thank you,
TJ Loughlin

---

## Notes for us (not part of the letter)

- **What it closes:** the money-gaps row *"Where did the school's April–June 2026 health
  insurance come from, and which month did each entry pay?"*
- **Join 1** is exact: the other side of each entry carries the same journal number.
- **Join 2** — the June entries back to the MIIA invoices they replaced — has no shared key.
  The Town's own MIIA invoices will appear on these accounts with check numbers, which is the
  likeliest route; otherwise it is a match on amount and month. If `crt wrt 57 26` means
  warrant 57 of FY26 (a reading of the abbreviation, not established), warrant 57's vendor
  invoice list would be the fallback.
- Figures in the table are read from `sources/data/munis-school-journal.csv`, Report 1 pdf
  page 652, lines 40–43.
