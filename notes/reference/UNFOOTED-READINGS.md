# Figures taken from a page that does not foot

`stabilization-unfooted.csv` in `sources/data/`. **These are the weakest readings this
project publishes and they are kept apart from everything else so they cannot be mistaken
for the rest.**

## Why the file exists rather than the figures being dropped or quietly mixed in

Everywhere else, a row is published only when the document's own arithmetic closes on it
— `verify()` in `read_trust_table.py`, the printed `Total Treasurer Cash` in
`extract_treasurers_cash.py`. That rule is right and it is not being relaxed here.

But it has a failure mode, and FY2021 is it. The town listed Vehicle/Equipment
Stabilization and Zoning Incentive Stabilization **only** on the Treasurer's Cash page
that year — its trust table omits both — and our scan of that page lost nine rows, so the
column cannot foot. Two figures that are perfectly legible, on a page the town published,
were therefore unpublishable, and the charts showed a gap where the town had printed a
number.

Refusing them says something false: that the town did not publish the figure. Publishing
them with the others says something else false: that they are as well established as a
row whose own table proves it. So they go here, with the reconciliation written out, and
the page that renders them says which they are.

## What every row must carry

- **`basis`** — why this page could not prove itself, in one line.
- **`reconciliation`** — the arithmetic that was possible, in full. Not "it looks about
  right": the residual, what accounts for it, what does not, and the proven neighbours
  the figure sits between. A reader must be able to disagree with it.

## The standing question

Every row here is a records request waiting to be written. The remedy for FY2021 is the
Treasurer's own cash report for 30 June 2021, which would state all 43 accounts — and
that is one line in the next letter to the Town, not a modelling problem.
