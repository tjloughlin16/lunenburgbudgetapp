# The budget feed: how a season page is read before it ships

**Scope: the budget feed and its season pages only** (`/budget-feed`, `/budget-feed/fyNN`,
the files in `sources/data/budget-seasons/`). Not a rule for the rest of the site.
The model these pages are built to is `BUDGET-SEASON-MODEL.md`; this is the checklist
they are read against, learned from three passes over FY27 on 14 September 2026.

TJ: *"don't generalise too much. This is JUST for the budget feeds."* These apply to every season file --
FY26 by hand, FY28 as the refresh proposes rows -- and a proposed row that breaks one is
wrong before anyone confirms it.

Read as the parent whose child's programme is on the list (PERSONAS.md, reader 7).

**Pass 1 -- the page's own errors**
- The first number is one people said. $761,001 (level service minus balanced) was never
  uttered; $2.4 million and $1.98 million were. A derived figure is context under the
  stated one, never the headline.
- Our notes stay ours. "The mistake TJ remembers" rendered to the town. A note about our
  process is `internal:` in the CSV and never shown.
- A fact that changes carries its dates, and every block agrees. "Middle school sports
  gone" sat three lines above "restored"; it now reads "until the September restoration
  below".

**Pass 2 -- what the page withholds**
- A proposal says what it buys in the cuts' own words -- "brings back a kindergarten para,
  an interventionist at Turkey Hill..." -- never its total alone.
- A track ends where it ended: the override track ends at the polls on 16 May, not at the
  last board recommendation.
- One structure per fact. The agenda-window calendar under the board, the department name
  under the department heading, the 864-line log under the finished story: removed or
  folded, not stacked.

**Pass 3 -- what this reader cannot find**
- Every item on the publisher's reduction list has a row a reader finds by its own word.
  Girls' lacrosse, boys' golf and the ski team were only implied inside "middle school
  sports -- all". Mechanical test when the list is parseable: every name, one row.
- A status is about the world, not our data: "proposed 26 Feb; gone from the 23 Mar list
  -- the record gives no reason", not "not on the 3/23 balanced list".
- A fee is a fee. "$75 per player" leads; the stipend accounting follows.

**Two checks to write into `build_budget_season.py --check` when the inputs allow:** no
rendered note begins `internal:`; every name on the publisher's reduction list (the
district's page, the town's at-a-glance) has a row.
