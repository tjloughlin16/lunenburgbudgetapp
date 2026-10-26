# A monthly refresh for the slow sources

TJ, 26 October 2026: *"we need to build a similar process for the daily refresh, but ... a
monthly refresh to start, which goes through sort of the longer term things like DESE and tries
to see if any information on all of those sources have changed as well. And any other sources
that we don't refresh ever probably needs to go into that slower refresh rate."*

## Why: it found something on its first, manual, run

Rechecking DESE's circuit breaker dataset (Socrata `ab34-d3ma`) against our copy the same day:
the dataset's rows were updated **7 October 2026**, after our copy was taken. Lunenburg's
FY2024-FY2026 rows are unchanged ($579,142 for FY2026 still stands), but **FY2023 changed**: our
copy says 6 eligible students claimed; DESE now leaves it blank, "Number of eligible students
claimed is less than 6" -- its small-count suppression. Our pages publish a count DESE now
withholds (build_circuit_breaker.py, build_serf_topics.py, build_special_education.py,
build_sped_costs.py and their verifiers read it). A source that changes in place is invisible
to a process that never looks again.

## The shape (proposed, not built)

- **One register of every source and how often it is re-checked**: daily (the town's
  AgendaCenter, the YouTube feed -- refresh.py already does these), weekly (the two staff
  directories, already), monthly (everything else that can be fetched: DESE datasets, DLS, the
  district's and the town's document pages), never (records-request deliveries -- they change
  only when we ask again).
- **The check is a hash, then a diff.** Fetch, sha256, compare with the manifest. Unchanged:
  record the date checked. Changed: never overwrite in place (the bucket refuses it anyway) --
  land the new copy under a new key through `ingest.stage()`/`secure()`, then report WHAT
  changed in the rows we use (the FY2023 suppression above is the model: one row, one field,
  old value, new value).
- **A change is a finding, not a silent update.** It lands in a generated report for a person
  to read, and every generator reading that source is re-run (`rerun-everything-downstream`).
  Privacy changes (a suppression) are applied at once; a revised figure is shown beside the old.
- **Cost:** fetching and hashing is free -- no `claude -p` in the loop. Only reading a changed
  document would cost anything, and that waits for a person.

## First tasks

1. Inventory every source with a fetchable address and no scheduled re-check (the
   `sources/*/index.csv` files and `dese-source-registry.csv` name them).
2. Apply DESE's FY2023 suppression: refresh the circuit breaker copy, carry "fewer than 6"
   through the five builders, re-run their verifiers.
