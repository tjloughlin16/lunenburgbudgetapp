# Plan: free cash, and the schools' part in it (a future report). ON HOLD

TJ, 30 October 2026: *"I'm inclined definitely to show that"*. He also said: *"write that up as a
design and future report. But let's hold off. There are others I want to do first."*

**Status: designed, not started. Do not build it until TJ picks it up.**

## The question it answers

How much free cash does the Town have each year, where does it come from, how much of it is
money the school budget did not spend, and what was it voted for?

The point for a resident: money the school budget leaves unspent does not stay with the schools.
At the close of the year it becomes part of free cash, and Town Meeting can vote free cash for
anything.

## Where it lives

The Town general fund page could take it as a section, or it could be its own topic page linked
from that page and from `/school-all-funds/budget-against-actual`. Decide when it is built, using
the `building-a-page` skill's "consolidate before adding" rule.

## The four parts, with the shape each takes

| # | part | shape | data held |
|---|---|---|---|
| 1 | Certified free cash, by year | line (a trend) | `sources/data/free-cash-proof.csv`, role `certified` |
| 2 | Where it came from | stacked bars (composition) | the same file: CL#6, CL#8, CL#11, CL#12 rows |
| 3 | The schools' part | panels, or a highlighted segment of part 2 | school turnback: `fy_breakdown.model()` / the "What the school fund left unspent" series; preschool above its estimate: `build_preschool.py` |
| 4 | What it was voted for | a table or timeline | `sources/data/town-meeting-votes.csv` (FY2026: Article 12, $500,000, on a condition) |

What the proof's lines mean, in plain words:
- **CL#6, receipts over estimate.** Local revenue that came in above the Town's estimate.
  Preschool tuition is one line inside it.
- **CL#11, unexpended appropriations.** Money voted but not spent. The school turnback is one
  part of it.
- **CL#8, cherry sheet over or under estimate.** State aid against its estimate; it can be
  negative.
- **CL#12, prior free cash not appropriated.** Last year's free cash that was never voted away.

The figures read off the proof on 30 October 2026, for orientation only (the page must compute
them, rule 2): certified $2.67M (2021), $2.92M, $1.87M, $2.27M and $3.35M (2025). CL#11 for 2025
is $2.46M; the FY2025 school turnback is about $555k of it.

**Peers:** the same DLS proof is held for Ayer, Groton, Littleton, Shirley, Townsend, Upton,
Uxbridge and Westford (`sources/state-dls/free-cash-proof-*.xlsx`). That allows a comparison as
a share of the budget, or per resident.

## Settle these BEFORE writing a sentence

1. **Which fiscal year is "proof year 2025"?** It is either the FY2025 close or the year the
   state certified it. If it is the certification year, every school comparison shifts by one
   year. The proof file's own header or DLS's definition settles it. Nothing has checked this.
2. **The school share is our arithmetic, not a printed figure.** DLS prints one Town-wide
   CL#11. Saying the turnback is "part of" it is how free cash is defined; the share is a
   quotient of ours and gets labelled as such (rules 3 and 7).
3. **No closing entry has been seen.** The school journal has no fund-balance accounts, and its
   year-end entries only cancel open orders. The Town GF period-13 report in the unsent records
   request (`notes/outbound/drafts/RECORDS-REQUEST-FY2026-CLOSE.md`, item B) would show the
   Town's side.

## Context worth stating, and how

The rule of thumb is **one-time revenue for one-time expenses**: DLS and the rating agencies
advise against funding recurring costs with free cash. FY2026 used $500,000 of free cash to start
the operating budget. Under rule 8, the page states the measurement (free cash used for the
operating budget, and the amount) and names the rule as the standard guidance. It does not
grade the Town.

## Done means

A generator emits a payload (rule 7d), with a verifier that recomputes every figure from
`free-cash-proof.csv` and the journal (rule 15). The year question above is answered in the
source, not assumed. The persona pass runs: the Finance Committee member is the reader most
likely to dispute part 3.
