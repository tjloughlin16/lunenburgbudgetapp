---
status: reference
updated: 2026-11-04
genlock: G-D2Q4K -- next steps, prohibitions and open questions live there (genlock goal show G-D2Q4K)
---

# School warrant batches, 18-30 June 2026: do they add up to the agenda's warrant?

TJ, 4 November 2026: *"we reported that theres a discrepancy between the warrant data we got and
the posted agenda. can you tell me how that was calculated."*

## What was found

**Nothing in the repository calculated a discrepancy.** No script, dataset, page or
`money-gaps.csv` row compares the batches with the agenda. The only statement is a status note,
`notes/reference/records-requests.csv` line 23: *"whether these nine batches are the whole warrant
has not been reconciled to its $362,767.40"*. And the delivery's own note,
`sources/correspondence/2026-11-03-school-warrants-2026-06-18-to-30.md`, says nothing is
extracted yet. Any figure quoted for the gap came from a conversation, not a check -- until 4 November 2026, when it
was measured and written into `money-gaps.csv` and the records-request row.

**The sum, 4 November 2026. Every batch total ties to the batch's own proof list:**

- Agenda: `sources/meetings/text/school-committee/2026-07-15-agenda-7901.txt` lines 43-44,
  *"Review & Approve Line Item Transfers, Warrants & Donations 6/18 to 6/30 $362,767.40"*; the
  minutes (`2026-07-15-minutes-7901.txt` line 48) give warrants $362,767.40, transfers and
  donations "None".
- The nine batches' cover-sheet `GRAND TOTAL AMOUNT`, read off the Textract lines in
  `build/textract/out/*warrant-batch*.lines.tsv`: 5765 15,918.53; 5780 8,836.74; 5806 34,955.33;
  5808 38,489.81; 5809 11,671.67; 5810 60,743.83; 5811 11,194.74; 5818 119,258.87; 5823 4,540.99.
  **Sum 305,610.51. Agenda minus batches: 57,156.89.**
- **The totals are checked.** First read by a subagent (two of nine tied); then all nine cover-sheet
  totals found again on each batch's own proof-list page (`REPORT POST TOTAL`), 4 November 2026.

## What it does not establish

- **Whether nine batches is the whole warrant.** A missing batch gives exactly this shape, and
  nothing we hold lists the warrant's batches.
- **The $189,276.75 FLLAC payment** (check 218995, 30 June) is in none of the batches. FLLAC
  appears only in 5810, as $4,450.00 and $87.50. It is larger than the gap, so it is not simply the
  missing piece, and whether it belongs to this warrant is not established.
- **The agenda's heading bundles transfers, warrants and donations.** That they were nil is the
  minutes' statement, not a breakdown.
- The dates fit the window (5765 on 18 June, 5780 on 23 June, the rest on 30 June).

Every reason for the gap is a hypothesis. **Closes:** the district's list of batches in the
warrant, or the check register for 18-30 June 2026.
