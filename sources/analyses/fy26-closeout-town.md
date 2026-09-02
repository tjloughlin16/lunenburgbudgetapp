# FY26 on the town side, as the books stood in June

> **Working state:** `notes/HANDOFF.md` carries the current branch and what is established
> versus assumed. `CLAUDE.md` carries the rules.

Analysis, 2 September 2026. Companion to `analyses/fy26-closeout.md`, which reads the same
report for the school department. Every figure recomputed by
`scripts/verify_fy26_closeout_town.py` from `sources/data/lunenburg.db`.

Each section is written twice: **In plain terms** for anyone, and **The evidence** for
anyone who wants to check it.

---

## What this rests on, and what it is not

The FY26 year-to-date budget report sent by the Town Manager on 2 September 2026, at
account level: 376 accounts across 67 departments, everything except the school department
(300) and school non-recurring (301).

**The same three limits apply as on the school side.** It is **period 12, not 13** — June,
with the books open, before purchase orders are cleared. **Zero-balance accounts are
suppressed**, so nothing here reasons from what is absent. And it is **expenditures only,
Fund 0100** — no enterprise funds, no grants, no revolving funds.

**Nothing in this document is a surplus.** It is a position.

---

## 1. The town underspends differently from the schools

### In plain terms

Both sides came in under budget. They got there in completely different ways.

On the town side, **220 accounts were under and only 18 were over.** On the school side,
160 were under and **57** were over. About one school account in five overspent; on the
town side it is fewer than one in twenty.

### The evidence

| | accounts | under | accounts | over | net |
|---|---:|---:|---:|---:|---:|
| Town, 67 departments, 376 accounts | 220 | $1,279,769 | 18 | $421,307 | **$858,462** |
| Schools, 259 accounts | 160 | $1,683,534 | 57 | $1,219,295 | **$464,239** |

Both rows are departments 300 **and** 301 excluded or included consistently. The
companion school analysis covers department 300 alone — 258 accounts, 56 over,
$1,201,434 — because 301 is a single separate appropriation. Adding it moves the school
row by one account and $17,862, and that account is `CURR ADOPT`, curriculum adoption,
which spent $43,639 against a revised $35,777.

Town totals at period 12: **$24,902,491** appropriated, **$2,745,179** transferred in,
**$27,647,670** revised, **$26,506,667** spent, **$282,542** encumbered, **$858,462**
unspent, across **376** accounts in **67** departments.

### What this does not show

**Why.** Four readings fit and nothing here separates them: school budgets may be set
tighter against known costs; the town may transfer more readily during the year so an
account never shows as over; the two may code differently, with the schools carrying more
small accounts that can each tip negative; or school costs may simply be less
controllable. The ratio is a fact. The explanation is not.

---

## 2. Snow removal cost $1,038,092 against a budget of $355,571

### In plain terms

Snow was budgeted at **$355,571**. It was given **$520,319** more during the year. It
still finished **$162,521 over** — total spending of **$1,038,092**, which is **292% of
what the town appropriated.**

It is the single largest budget miss in the FY26 town books, and it is bigger than the
school department's entire net underspend.

### The evidence

| account | | original | transferred in | revised | spent | left |
|---|---|---:|---:|---:|---:|---:|
| `531003` | CONTR SERV | $114,500 | +$381,730 | $496,230 | $496,230.00 | $0 |
| `531029` | SUPP SNOW | $205,151 | +$138,589 | $343,740 | $402,039.54 | −$58,300 |
| `513000` | SNOW REMOV (wages) | $23,420 | $0 | $23,420 | $126,286.35 | **−$102,866** |
| `531030` | HIRED SNOW | $7,500 | $0 | $7,500 | $9,174.15 | −$1,674 |
| `531006` | PURCH SERV | $5,000 | −$319 | $4,681 | $4,362.42 | +$319 |
| | **department 423** | **$355,571** | **+$520,000** | **$875,571** | **$1,038,092.46** | **−$162,521** |

**Two things in that table are worth reading closely.**

`CONTR SERV` was given $381,730 and then spent **exactly** $496,230.00, to the penny of
its revised budget. A transfer sized precisely to what was spent is what a year-end
transfer looks like: the budget is moved to cover the actual, not the other way round.

`SNOW REMOV` — the wages line — got **no transfer at all** and spent **539%** of its
$23,420 budget. It is the account most over its appropriation anywhere in the town books.

### What this does not show

Snow and ice is the one thing a Massachusetts town may lawfully overspend, which is why
this department can end a year negative where others cannot. **We hold no document
stating that authority**, and it is named here as the ordinary explanation rather than as
something this project has verified.

Nor does this say the winter was severe. It says what was spent.

---

## 3. The Reserve Fund was never touched

### In plain terms

The town budgeted **$185,000** as a Reserve Fund — the contingency it holds for
unforeseen costs. At the end of June it had spent **nothing**. Not one dollar.

In the same year snow removal ran $682,521 past its original appropriation.

### The evidence

| department | account | budgeted | transferred out | spent |
|---|---|---:|---:|---:|
| `132` RESERVE FUND | `RES FUND` | $185,000 | $0 | **$0.00** |
| `133` SALARY RESERVE | `RES FUND` | $180,000 | −$128,953.67 | $51,046.33 |
| `133` SALARY RESERVE | `RETIRE/BUY` | $30,000 | $0 | **$0.00** |

The salary reserve did its job: it gave away $128,954 of its $180,000 and spent the rest.
The Reserve Fund proper did nothing, and the retirement buy-back reserve did nothing.

**$215,000 of contingency went unused**, which is 25% of the town's entire net underspend.

### What this does not show

**That this is a finding rather than a procedure.** A Reserve Fund transfer requires
Finance Committee approval, and snow deficit spending does not — so a town facing a snow
overrun would not necessarily reach for it. Whether $185,000 sitting idle reflects a
deliberate policy, an unspent contingency in a mild year, or a reserve nobody asked to
use, is not established here.

---

## 4. $3.3 million left the operating budget for capital and reserves

### In plain terms

Two accounts exist to move money out of the operating budget: one into capital projects,
one into stabilization and trust funds. Between them they were budgeted $1,285,000 and
moved **$3,321,257** — more than two and a half times as much.

This is the largest single movement in the FY26 town books, and it is money the operating
budget raised and then sent somewhere else.

### The evidence

| department | | original | transferred in | spent |
|---|---|---:|---:|---:|
| `993` | Transfer to capital project fund | $1,052,500 | +$1,240,820.32 | $2,293,320.32 |
| `996` | Transfer to trust and stabilization | $232,500 | +$795,437.00 | $1,027,937.00 |
| | **together** | **$1,285,000** | **+$2,036,257.32** | **$3,321,257.32** |

Both spent their revised budget to the dollar, which is what a transfer account does: the
money arrives and immediately leaves.

### What this does not show

**Where the incoming $2,036,257 was voted from.** These accounts received more than
they were appropriated, so something outside the original appropriation funded them —
free cash, a stabilization draw, a Town Meeting article. The ledger records that the
budget changed and never records the counterparty. That is the same gap the school
department's transfers run into, and the same document would close it.

---

## 5. The schools cost the town money the school budget never shows

### In plain terms

The town's insurance department spent **$3,598,785** in FY26. Of that, **$1,262,376 is
explicitly school retiree health insurance** — a real cost of running the schools, sitting
in a town department, appearing nowhere in the school budget the School Committee votes on.

An unknown share of the remaining $2,336,409 is health insurance for **serving** school
employees. The account names do not separate town from school, so it cannot be measured.

### The evidence

| account | | revised | spent | left |
|---|---|---:|---:|---:|
| `570018` | **SCHRETHLTH** — school retiree health | $1,521,536 | **$1,262,376.00** | +$259,160 |
| `570001` | HEALTH INS | $1,315,270 | $1,376,557.17 | −$61,287 |
| `570009` | TNRETHLTHI — town retiree health | $453,215 | $593,088.85 | −$139,874 |
| `570003` | MEDI | $400,000 | $345,848.60 | +$54,151 |
| `570002` | LIFE INS | $15,000 | $12,864.84 | +$2,135 |
| | four smaller accounts | | $8,049.98 | |
| | **department 914** | | **$3,598,785.44** | |

Elsewhere, department 210 carries `SCHRESSTIP` at **$6,800** — a school resource stipend
in the police budget.

**False friends, checked and discarded.** Nine town accounts match a search for `SCH`.
Two are the ones above. The other **seven** are named `MTGS/SCHOO`, `MTG/SCH FF`,
`MEET/SCHOO` — meetings and schooling, meaning staff training, not schools. They total
$9,944.81 and are excluded. A name match is a candidate, not a finding.

### Why this matters beyond the money

This is the mechanism behind a number this project has had to be careful with. DESE
reports Lunenburg's FY24 in-district spending at **$26,914,321.89** against a general fund
school appropriation of about $22.8M, and the difference is not hidden money — it is
costs like these, which DESE attributes to the schools and the school budget does not
carry.

**$1,269,176 of it can now be named.** The rest cannot, and this is the first document in
this project able to point at any of it in the ledger.

### What this does not show

**How much active school employee insurance is in the $1,315,270 `HEALTH INS` line.** The
account does not split town from school. It could be most of it or little of it.

---

## 6. Spending against a zero budget — and why the school case is still different

### In plain terms

`analyses/fy26-closeout.md` §3 reports two kindergarten paraprofessional accounts that
spent $99,064 with no appropriation and no transfer. The obvious question is whether that
is unusual, so it was checked against the town side.

**Thirteen non-school accounts spent money with no original appropriation. Eleven of them
received a transfer that covered it.** The remaining two are one event, not two — and it
is not the same event as the kindergarten accounts at all.

### The evidence

Eleven were covered by a transfer, and that is the ordinary mechanism working:

| department | account | transferred in | spent |
|---|---|---:|---:|
| `164` Town Clerk | TN CLK SAL | +$80,629 | $78,466.44 |
| `992` | TR SPE REV | +$15,000 | $15,000.00 |
| `136` | AUDIT COST | +$8,500 | $8,500.00 |
| `170` | CONSULTANT | +$8,971 | $8,187.54 |
| `141` | TEMP SALAR | +$13,347 | $4,276.20 |
| `136` | GASB45VALU | +$4,100 | $4,100.00 |
| … | five smaller | | |

**The two without a transfer are both in the Planning Board, and they cancel:**

| account | | original | transfers | spent |
|---|---|---:|---:|---:|
| `511000` | PLANN DIR | $0 | $0 | **+$12,796.80** |
| `511001` | PLAN CLERI | $0 | $0 | **−$12,796.80** |

Those are the department's only two accounts in this report, and the second is the exact
negative of the first. That is a **reclassification** — a salary posted to one account and
journalled out of another — and it nets to nothing. No money was spent without a budget;
money was moved between two accounts that both happen to carry no budget.

### What this changes about the school finding

**It makes the kindergarten case more unusual, not less.** The one town-side example that
looked like the same thing turns out to be a paired journal entry that cancels.

**There is no offsetting negative anywhere in the school department.** Every account in
department 300 has zero or positive spending; not one carries a credit that would net the
kindergarten accounts off against something else. Checked directly, because it is the
first thing that would have explained them.

So on the town side, spending against a zeroed line is either covered by a transfer or is
half of a recode. In the school department, $99,064 is neither.

---

## What would change these findings

1. **The FY26 period 13 report.** Every figure here is a position, not a result.
2. **The year-end transfer schedule.** Settles §2, §4 and §6 — every "transferred in"
   figure above has an unknown counterparty.
3. **A split of health insurance between town and school employees.** Settles the open
   half of §5, and is the largest single unmeasured school cost in the town books.
4. **Finance Committee minutes from 14 July 2026.**

## How to reproduce

    python3 scripts/build_db.py
    python3 scripts/verify_fy26_closeout_town.py
