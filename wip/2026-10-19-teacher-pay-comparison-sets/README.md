# UNFINISHED — the district's official comparison set, its DESE salaries, and the new contracts

Saved 19 October 2026. The agent doing this work stopped when it hit a usage limit, before
checking or committing anything. This is its work as it stood. **Nothing here is verified.** Read
`notes/HANDOFF-TEACHER-PAY.md` first; it explains the goal and what is already finished and live.

## What it was for

Compare Lunenburg's teacher pay against **the district's own comparison districts**: the 11 the
district itself named (Budget Task Force, FY2026 budget p57: Nashoba, Groton-Dunstable,
Ashburnham-Westminster, Shrewsbury, Uxbridge, Maynard, Wachusett, Ayer-Shirley, Hudson; plus the
FY2020 budget's Tyngsborough and Harvard). They are shown beside the project's own six, with both
sets kept and labelled by who chose them.

## What is here

| Path | What | State |
|---|---|---|
| `files/sources/data/comparison-sets.csv` | Every comparison set, one row per (district, source document), with page and quote | Looks complete for `official`; check that the `project-six` rows exist |
| `files/scripts/check_comparison_sets.py` | Validates the sets file (every name resolves to one DESE org code) | Untested |
| `files/scripts/extract_dese_teacher_salaries.py` | DESE average teacher salary for every district | Untested. Must reproduce Lunenburg FY2018–FY2025: 74,236 / 77,908 / 83,054 / 85,067 / 85,426 / 88,019 / 98,894 / 97,233. Whether its source file was ingested is unknown |
| `files/fy28/public/docs/data/dese-teacher-salaries.csv` | That script's output | Unverified |
| `files/sources/contracts/txt/*.txt`, `words/*.tsv` | Text and OCR word boxes for 14 new contracts (Shrewsbury, Groton-Dunstable, Ayer Shirley ×2, Hudson ×2, Maynard, Uxbridge, Tyngsborough ×2, Wachusett ×2, Ashburnham-Westminster) | **Some may be partial.** Three whole-document OCR jobs (Ayer Shirley 2025–28 + Wachusett DESE; Uxbridge + Tyngsborough DESE; Shrewsbury 2025–28) were paused and then killed mid-run. Check each against its PDF's page count before trusting it |
| `patches/scripts_extract_teacher_salary_schedules.py.patch` | The schedule extractor extended to the new districts | Untested |
| `patches/sources_data_teacher-salary-schedules*.csv.patch` | New schedule cells | **Known defect:** a step value `'11/13'` (Tyngsborough) that `build_spending_staff_students_topics.py`'s `schedules()` cannot parse. Normalise it (integer `step` plus `step_as_printed`) |
| `patches/sources_contracts_index.csv.patch` | Catalogue rows for the new contracts | Check against the archive manifest |
| `patches/scripts_build_spending_staff_students_topics.py.patch` | A small change to the page generator | **Review before applying.** Possibly the agent's compatibility fix; not confirmed |
| `patches/notes_reference_records-requests.csv.patch` | Drafted request rows | May include other agents' hunks; apply by hand |

The contract PDFs themselves are in the R2 bucket and in `sources/contracts/pdf/`
(`check_archive_backed_up.py` passes). The agent's last line was "Now ingest all fifteen documents
through ingest.land"; whether all fifteen are secured is unconfirmed.

## How to resume

1. Copy `files/` back into place, or confirm the originals are still in the working tree.
   Apply the patches: `git apply --3way patches/<name>.patch`.
2. Fix the `'11/13'` step. Make the schedule extractor's `--check` pass. For the scanned
   contracts, **OCR only the salary-schedule pages, one document at a time**: whole-document
   parallel OCR held the laptop at full load for over 30 minutes.
3. Run `check_comparison_sets.py` and `extract_dese_teacher_salaries.py --check`, then
   `extract_peer_teacher_pay.py` and `build_spending_staff_students_topics.py` and its `--check`.
4. Update `teacher-pay-compared` and `teachers-on-the-scale` to show both sets.
5. Commit the finished work where it belongs, and delete this folder in the same commit.
