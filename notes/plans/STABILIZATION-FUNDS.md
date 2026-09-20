# Stabilization funds: the extraction, then the report

**Status:** planned, not started. Written 20 September 2026, while the refresh ran.

TJ asked six questions about the town's reserves and the archive could answer one and a
half of them. This is what it takes to answer all six, in the order the answers depend on
each other.

---

## The six questions, and what each one needs

| | question | what answers it | do we hold it |
|---|---|---|---|
| 1 | What are these funds **for**? | M.G.L. c.40 §5B, plus the Town Meeting article that created each one | statute: no, not yet written down · articles: in `report_appropriations`, unreconciled |
| 2 | **How much** is in them? | the stabilization section of the annual report's trust-fund table | **FY2025 only**, and `no check` |
| 3 | **How** are they spent? | the disbursement columns of that same table, plus the articles authorising each transfer out | not extracted |
| 4 | **When** are they spent? | the same series, read as a pattern | not extracted |
| 5 | Can they pay for a deficit like the school's? | the statute, and which funds are general vs special purpose | **answerable now** |
| 6 | If the town put **less in each year**, could that money go to the gap instead? | the annual transfer-IN series, then a lever like the free-cash one | partial — four years observed, `check failed` |

Four of six are series questions. That is why the extraction comes first.

---

## Step 0 — get the words right

**Stabilization funds are not trust funds, and this project has been calling them that.**

The town prints them inside a table headed `TOWN OF LUNENBURG / TRUST FUNDS`, and our
dataset took its name from the page — which is correct provenance and the wrong noun for
the question. Of 114 rows across FY2023–25, thirteen are stabilization; the rest are
scholarship, library, cemetery, conservation and OPEB.

The distinction is the whole of question 5:

- **A trust fund** is money somebody gave the town under conditions. The donor's
  restriction binds. A scholarship bequest cannot be voted onto the school budget.
- **A stabilization fund** is the town's own reserve, created by Town Meeting under
  c.40 §5B and funded by appropriation. Town Meeting puts money in and takes it out.

The annual report groups by **where the money sits**, which is what a treasurer needs.
Every question here is about **who may vote to spend it**, which is a different axis.

Fix in this step, and nowhere else afterwards:

- the `extraction` gap rows, which currently say "the stabilization and trust fund
  balances" as though it were one category (`scripts/build_extraction_gaps.py`)
- the dataset's description wherever it is published, to say that stabilization is a
  SECTION of the trust-fund table and a different instrument

Keep `report_trust_funds` as the table name. It is named for the page it came off, which
is right, and renaming it would break the provenance chain for the sake of a label.

---

## Step 1 — the extractor

**Scope it to the stabilization section, not the whole table.** ~13 rows a year against
642 total. The other sections can follow if they are ever wanted; nothing here needs them.

What the per-year survey in `sources/data/extraction-plan.csv` already says, so nobody
rediscovers it:

- 17 years, of which **10 need real PDF geometry** rather than text, 5 are messy, 2 clean
- mirrored layouts; rows offset from their own names by a line; a missing fund-name column
  in FY2013; column counts that change between FY2011 and FY2012
- **16 of 17 print a grand total**, so every year can be reconciled rather than trusted

Two rules this family breaks if read naively, both already written down in CLAUDE.md:

- **`v1` is an ordinal, not a column.** On pages where `ACCOUNT NUMBER` is the first
  column of figures, the code lands in `v1` and every value shifts right — which is why
  FY2020 records the Vehicle/Equipment fund's balance as `8136.00`.
- **Never transcribe by row position.** FY2011's note says a fund name on line N
  frequently belongs to the numbers on line N-1 or N+1.

Done when: a balance per stabilization fund per year, FY2011–FY2025, each year footing to
the total its own page prints, and `status = checked` rather than `no check`.

---

## Step 2 — the second series, which is the interesting one

Question 6 needs what goes **in** each year, and that lives in `report_appropriations`
(4,665 rows, **0 checked**) as `Transfer to Stabilization Funds/OPEB`:

    FY2020  $538,222      FY2022  $899,752
    FY2021  $782,252      FY2023  $816,696

**Against a school gap of $930,273, that is the same order of magnitude** — which is what
makes question 6 a real lever rather than a rhetorical one.

But the line is `Stabilization Funds/OPEB`, two obligations in one figure, and OPEB is a
liability the town is funding down rather than a reserve it may redirect. **Splitting that
is the load-bearing work of this step.** A lever built on the combined number would
propose spending money that is already promised.

---

## Step 3 — the report

`sources/analyses/stabilization-funds.md`, following `notes/process/WRITING-AN-ANALYSIS.md`
in order, and rule 7b's shape: conclusions, then the categorical breakdown, then the raw.

Two things it must keep separate, because they are separate:

- **The general Stabilization Fund** ($3,147,178.96 at FY2025) — spendable on any lawful
  purpose by a two-thirds vote of Town Meeting. This is the one question 5 is about.
- **The special-purpose funds** — vehicles and equipment ($2,598,621.38), sewer capital,
  sewer I/I, zoning incentive, opioid settlement, health insurance. Restricted to their
  stated purpose. Naming them as available reserve would be wrong.

Rule 7 governs the conclusions: a balance is a fact, a reason it moved is a hypothesis,
and "the town is saving instead of spending on schools" is a hypothesis wearing a
measurement's clothes.

A verifier — `scripts/verify_stabilization.py` — written **before** publishing, asserting
the figures and not the prose.

---

## Step 4 — where it appears

- **Its own report**, as above. It is about the town's whole reserve position and does not
  belong inside a school analysis.
- **Linked from the Select Board's finance tab**, with the two or three conclusions pushed
  up to the board page rather than only the link — that was TJ's ask, and `build_finance.py`
  already renders per-board finance pages.
- **A lever, only if step 2 separates OPEB cleanly.** Modelled on the free-cash lever: a
  standing annual amount, applied after every rate has run, touching no bucket and no
  escalator. If OPEB cannot be split out, publish the series and no lever, and say why.

---

## What would make this wrong

- **Treating the whole $6.4M as available.** Roughly half is restricted by its own
  purpose.
- **Treating a reserve as income.** Spending stabilization on an operating deficit is a
  one-time fix that buys a year, exactly as free cash does — and the site already argues
  that about free cash. The lever must say so or it contradicts the page next to it.
- **Assuming the transfer-in is discretionary.** Some of it is OPEB, and some may be
  required by a funding schedule the town has adopted. Check before proposing.
