# Ingesting a table family, without it taking a day

Stabilization took one. Nine of the ten defects found were generic table-reading faults
that had nothing to do with stabilization funds, and the tenth was a name. This is the
loop that should stop that happening twice, and the self-checks that say whether it is
working while it runs.

TJ, at the end of that day: *"we need a better more predictable and faster process to get
the rest of the data"*, and *"you seem to try something and then stop until i push. that's
not going to lead to data the fastest possible way."*

Both notes are about the same failure, and it is not a knowledge problem.

---

## The rule that matters most: what counts as DONE

**Having something worth reporting is not a stopping condition.** That was the actual
defect in the stabilization day. The pattern ran: extractor refuses → report the amount →
wait → get pushed → find the cause in four minutes. Every one of those pauses was a place
where the next step was available and known.

Stop for exactly three reasons, and no others:

1. **The objective is met** — measured, not felt. See the scoreboard below.
2. **The next step needs a person or a document we do not hold.** A records request, a
   decision about what to publish, a judgement about whether two names are one fund.
   Say which, and what would settle it.
3. **The same approach has failed twice.** Then stop repeating it and change approach —
   that is a different action, not a pause.

"I found something interesting" is not on the list. Report it while continuing.

---

## The loop

### 0. Score it before starting

Write the number down. For stabilization it was *funds with a balance for every year they
existed*: 1 of 9. Without a number, "progress" is a feeling, and a day can pass without
one.

The scoreboard has to be a script, not a query typed each time —
`scripts/check_stabilization_coverage.py` is the worked example, and `--check` fails when
it stops being true.

### 1. Map what exists before reading anything

Which pages, which years, which are already read. `map_annual_report_pages.py` does this
for the annual reports. **A page nobody has classified is not absent, it is unclassified**,
and the two need opposite work.

### 2. Run the extractor and read the REFUSALS, not the output

A good extractor refuses more than it publishes at first, and each refusal names an
amount. That list is the work queue. `sources/data/extraction-blocked.csv` holds them so
they outlive the run.

### 3. For each refusal, run the ladder — all of it, before concluding

This is the part that was improvised for a day. In order, cheapest first:

| # | check | what it tells you |
|---|---|---|
| 1 | **Diff against the nearest published year.** Which rows does that year have that this one does not? | the town lists roughly the same accounts every year, so the missing names are usually the answer |
| 2 | **Does the residual equal exactly one row on the page?** | a duplicate, or a row the reading dropped |
| 3 | **Are there labels with no amount, or amounts with no label?** | a pairing-band or filter problem, not missing data |
| 4 | **RENDER THE PAGE AND LOOK AT IT.** | settles in one glance what inference cannot. It found the rotated-page clip, the `4` read as a `1`, and three years of a fund I had just called missing |
| 5 | **Is the page landscape?** | `/Rotate` handling has cost 20% of the content of every landscape document in this archive |
| 6 | **Check the codepoints of the labels.** | `ОРЕВ` is Cyrillic and renders exactly like `OPEB` |

`scripts/diagnose_table.py` runs 1, 2, 3, 5 and 6 and prints 4's command.

**Step 4 is not last because it is a last resort.** It is fourth because it costs a minute
and is decisive; the three above it are cheaper still. What must not happen is reaching a
conclusion without having done it.

### 4. Fix it in `pdf_tables.py`, not in your extractor

**This is the whole difference between a day and an hour.** Every fix from the
stabilization day was generic and every one of them landed in one extractor, where the
next family cannot reach it. If a fix is about how tables are READ — bands, labels,
alignment, separators, rotation, wrapping, homoglyphs — it belongs in the shared module.
If it is about what a fund is CALLED, it belongs in `fund_names.py`.

Ask: *would another table family hit this?* If yes, it does not go in your file.

### 5. Re-run EVERY generator downstream, then re-score

Not the one you were thinking about. `build_pipeline_state.py` prints a STALE list by
comparing modification times; `check_generated.py` is the full version.

This is not bookkeeping. Stale output reads as **evidence of absence** — it is how three
years of a fund got reported missing and registered as a gap while sitting in the archive.

### 6. Self-check: did the number move?

Compare the score to step 0.

- **It moved** — loop back to step 2 with the next refusal.
- **It did not move, and the same approach was tried twice** — stop repeating it. Go to
  step 3.4 and LOOK at the page, or change families and come back.
- **It cannot move without a document we do not hold** — write the records request, register
  the gap with `— closes:` naming that document, and move to the next family. That is
  finishing, not stopping.

---

## What the stabilization day actually cost, itemised

Kept because the next estimate should be built on it rather than on optimism.

| defect | generic? | where the fix went |
|---|---|---|
| rotated-page clipping, ~20% of every landscape doc | yes | `ocr_pdf.swift` |
| comma scanned as a full stop | yes | one extractor |
| row band hardcoded at 0.006 | yes | one extractor |
| label filter wanted more than 5 characters | yes | one extractor |
| misaligned row discarded | yes | one extractor |
| page identified by heading and not its own total | yes | one extractor |
| OCR noise duplicating a row | yes | one extractor |
| Cyrillic homoglyphs | yes | `fund_names.py` |
| hyphenated label wrapping | yes | one extractor |
| the town swapping words in a fund's name | no | `fund_names.py` |

**Nine of ten generic, and seven of them landed somewhere the next family cannot use.**
That is the estimate for next time unless step 4 is followed.
