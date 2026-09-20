# The stabilization funds, and who may spend them

> **Working state:** `notes/HANDOFF.md` carries the current branch and what is
> established versus assumed. `CLAUDE.md` carries the rules.

**What the town holds in reserve, which of it could lawfully be spent on an operating deficit, and the four questions about it this archive cannot yet answer.**

Analysis, September 2026. Balances are FY2025 and are **not reconciled** — see the caveat before quoting one.

---

## The short version

The town holds **$6,444,504** across 7 stabilization funds. **$3,147,179 of it is the general Stabilization Fund, which Town Meeting may appropriate for any lawful purpose by a two-thirds vote. The remaining $3,297,325 is restricted to the purpose each fund was created for.**

So the answer to *can this pay for a school deficit* is **yes for $3,147,179 and no for the rest** — and a reserve spent on an operating cost buys one year, exactly as free cash does, which is the argument `free-cash.md` already makes.

---

## What is in them, FY2025

| account | fund | balance | may be spent on |
|---|---|---:|---|
| `8124` | Stabilization Fund | $3,147,178.96 | **anything lawful**, by a 2/3 Town Meeting vote |
| `8136` | Vehicles/Equipment Stabilization | $2,598,621.38 | its own stated purpose only |
| `8129` | Zoning Stabilization Fund | $249,060.25 | its own stated purpose only |
| `8141` | Opioid Settlement Stabilization | $241,421.18 | its own stated purpose only |
| `8138` | Sewer Capital Reserve Stabilization | $191,679.20 | its own stated purpose only |
| `8140` | Health Insurance Stabilization | $11,026.88 | its own stated purpose only |
| `8133` | Sewer I/l Stabilization Fund | $5,516.23 | its own stated purpose only |
| | **Total** | **$6,444,504.08** | |

**The general/restricted split is ours**, read off each fund’s name. The annual report prints a balance and never says what may be spent on what.

---

## What this cannot answer yet, and why

Four of the six questions this report was asked are about MOVEMENT, and the series does not exist in a form anything may aggregate:

| question | blocked on |
|---|---|
| How has each balance moved? | the series |
| How are they spent? | the disbursement columns, and the articles authorising each transfer out |
| When are they spent? | the same series, read as a pattern |
| If the town put less in each year, could that go to the gap? | the transfer-IN series, and separating OPEB from it |

`report_trust_funds` holds 642 rows for FY2011–FY2025. **Twelve are reconciled to a total the document itself prints.** The balances above are `no check`: extracted, never tied to the page’s own total. Every page was surveyed before anyone tried — ten of seventeen years need real PDF geometry rather than text, because of mirrored layouts, rows offset from their own names, and column counts that change between years.

That is registered as a gap rather than left here: see the `extraction` rows in `sources/data/money-gaps.csv`, published at `/what-we-cannot-answer`. The work to close it is `notes/plans/STABILIZATION-FUNDS.md`.

---

## What this does not show

- **That the balances are right.** They are unreconciled. A figure here is a place to look in the annual report, not a figure to quote at a meeting.

- **That the restricted funds are unavailable for ever.** Town Meeting created each one and can, in principle, act on them again. What it cannot do is spend a special purpose fund on something else while it stands.

- **That spending a reserve solves anything.** It is one-time money against a recurring cost — the same shape as the September Town Meeting appropriation that left $392,264 of salary in the following year with nothing behind it.

- **Why any balance is the size it is.** A balance is a fact; a reason is a hypothesis.

---

## Sources

| | |
|---|---|
| Balances | `report_trust_funds`, from the annual town reports — status `no check` |
| The general/restricted split | ours, from each fund’s name |
| What the archive cannot yet say | `sources/data/money-gaps.csv`, side `extraction` |
