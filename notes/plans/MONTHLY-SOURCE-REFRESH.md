# The slow sources: one register, inside the daily refresh

TJ, 26 October 2026: *"we need to build a similar process for the daily refresh, but ... a
monthly refresh to start, which goes through sort of the longer term things like DESE and tries
to see if any information on all of those sources have changed as well. And any other sources
that we don't refresh ever probably needs to go into that slower refresh rate."*

TJ, 28 October 2026, on the shape: *"we dont make a separate script, and that we just put it all
in the daily refresh script. but the 'cadence' of each source is known, checked against daily,
and if the either next scheduled run is hit or past, it fetches those sources too. a separate
script feels like too much duplicate work."*

**BUILT 28 October 2026.** The table of every source is `notes/generated/SOURCE-CADENCE.md`.

## Why: it found something on its first, manual, run

Rechecking DESE's circuit breaker dataset (Socrata `ab34-d3ma`) against our copy the same day:
the dataset's rows were updated **7 October 2026**, after our copy was taken. Lunenburg's
FY2024-FY2026 rows are unchanged ($579,142 for FY2026 still stands), but **FY2023 changed**: our
copy says 6 eligible students claimed; DESE now leaves it blank, "Number of eligible students
claimed is less than 6" -- its small-count suppression. Our pages publish a count DESE now
withholds (build_circuit_breaker.py, build_serf_topics.py, build_special_education.py,
build_sped_costs.py and their verifiers read it). A source that changes in place is invisible
to a process that never looks again.

## What was built

- **`sources/data/source-cadence.csv`** -- the register, hand-kept. One row per source: its
  cadence in days, whether the refresh fetches it, checks it, leaves it to a person, or never
  sees it (records requests), and how the refresh runs it (`step`, `gated`, `job`, `slice`).
  `source_cadence.py --check` fails if any `scripts/fetch_*.py` has no row, so a new fetcher
  cannot be written and then never re-run -- the staff-directory gap.
- **`sources/data/source-checks.csv`** -- every look the refresh took, appended. `ok=1` only
  when the job exited 0, so a failure is retried the next morning rather than skipped.
- **`scripts/source_cadence.py`** -- `due(id, as_of)`: due when the cadence has elapsed since
  the last successful look, on the day or any day after (catch-up scheduling, as anacron does
  it). The refresh's three hand-written copies of that test -- the OML stamp file and two
  `checked.csv` reads -- now call it, and their history was seeded into the log.
- **refresh.py step 3j, `slow_sources()`** -- runs every `job` and `slice` row that is due,
  records the look, names in the run's notes what the checks found that day, and rewrites the
  README. About 3.5 minutes on its first run; no model calls.
- **`scripts/check_socrata_sources.py`** -- DESE's portal datasets. Asks the portal for
  `rowsUpdatedAt` and compares it with the commit that first recorded our copy's sha256. A
  Socrata export is generated per download, so hashing a fresh one says nothing.
- **`verify_source_copies.py --prefix --due-days --max`** -- the per-document check, which
  had last run on 5 September, as a daily SLICE: each morning checks the documents whose own
  last check is oldest, a few dozen per set, so 4,000 documents on a 30-to-90-day cycle never
  land on one morning (staggering, by construction).

## A change is a finding, not a silent update

The checks never land a new copy. They record what moved; the refresh names it; the README
lists it in two tables kept apart on purpose:

- **Changed at the publisher** -- a document whose content differs, a dataset whose rows moved.
  A person lands the new copy through that source's fetcher (via `ingest`) and re-runs every
  generator reading it (`rerun-everything-downstream`).
- **Defects in our archive the checks exposed** -- the same check finding OUR filing error.
  The first run's eight district `differs` were all this: the district publishes some action
  plans twice under near-identical titles ("CC & C.1", "CC & C 1"), the crawler slugged both to
  one filename, and the archive holds one of two different documents. And two DESE workbooks
  whose recorded address is the page listing them, not the file.

**The first scheduled run's instrument errors, now states of their own** -- each would have
been reported as a change:

| looked like | was | now |
|---|---|---|
| 20 town board pages and DESE regulation pages `differs` | web pages re-render on every request | `rerendered` |
| a workbook `differs` from DESE's chapter70 page | HTML compared with an xlsx; the address is an index page | `page, not file` |
| 8 district PDFs `differs` | two documents filed under one name | reported as ours |

## Not yet done

1. **Wire the `manual` rows one at a time.** DLS (cherry sheet, property, tax bills, tax
   rates), BLS, Census, board pages and the Open Meeting Law each have a target cadence and no
   schedule. Each fetcher has to be read for whether it lands through `ingest` or writes in
   place before it runs unattended; DLS's and BLS's files carry no publisher address, so no
   copy check sees them meanwhile.
2. **Apply DESE's FY2023 suppression**: refresh the circuit breaker copy, carry "fewer than 6"
   through the five builders, re-run their verifiers. A privacy change, so it goes first.
3. **Take in the enrollment dataset** (`dese-enrollment-by-grade.xlsx`): rows updated
   23 October 2026, after our copy of 8 September. Found by the first run; not yet read.
4. **The slug collision**: 35 district paths carry more than one address. Some are one
   document linked twice (legitimate); the action plans are two documents. The crawler needs
   to give a different document a different name, and the missing versions need fetching.
5. **The two `page, not file` addresses** need the file's own link (rule 12).
