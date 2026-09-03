# The join map

What can be joined across this project's data, what cannot, and which questions each gap
makes unanswerable. `join-map.html` is the source; it is published as an Artifact and the
file here is the copy of record — **an Artifact is a rendering, not a source, and rule 12
applies to our own work as much as to the Town's.**

    open notes/data-model/join-map.html          # or re-publish it from this file

## The finding in one line

The four edge kinds are not "joined" and "not joined". They are:

| edge | meaning | who can close it |
|---|---|---|
| solid | joins; counts verified by query | — |
| dashed red | no key here; a document elsewhere could supply one | the Town, or DESE |
| dotted grey | no key anywhere; the relationship does not exist | nobody |

The page states the model, not its history: an edge that joins is drawn as a join, whatever
it took to get there. What it took is in the git log.

The grey one is the point of the model. *"Where does the school spend the Chapter 70
money?"* is grey: aid arrives as unrestricted revenue into fund `0100` and is thereafter
indistinguishable from property tax. 222 revenue accounts and 759 expense accounts share
three orgs out of 981. No document closes that, and asking the Town for one spends goodwill
on a question their own system cannot answer.

## What changed on 3 September 2026

`account` gained `account_string` and `function`, carried from `munis-ledger.csv`, which the
loader had been discarding since the database was first built. 270 accounts carry a code;
41 of the budget's 45 function codes are shared. `v_function_budget_vs_ledger` does the
join. `check_join_key()` fails the build if either number collapses.

`crosswalk` stays empty on purpose: the code joins a **category**, never a line. MUNIS
truncates account names to ten characters, so `MS GUIDANC` and `HS GUIDANC` are both 2710
where the budget has a row per school.

## Regenerating the numbers

Every figure on the page came from queries against `sources/data/lunenburg.db` and the CSVs
under `sources/data/`. Re-run them before quoting:

    python3 scripts/build_db.py --check

**Two claims on an earlier version of this page were wrong**, and the corrections are on the
page rather than quietly removed: no special-revenue row is lost to an Excel apostrophe (the
loader strips it; fund 2903 is duplicated in the Town's own export), and `balance` and
`source_url` were never dropped — they load as `closing_balance` and `url`. Both errors came
from comparing column *names* between CSV and table, which cannot tell a rename from a
deletion.
