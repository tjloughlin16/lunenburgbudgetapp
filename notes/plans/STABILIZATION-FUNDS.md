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

---

# Added 20 September 2026: the wider page this belongs inside

TJ: *"we probably need a general 'full town accounting' page, which shows the operational
budget, plus all money held in savings, accounts, etc. we can link to the stabilization
report, but I think a broader lens, with historical trends, can be useful."*

Right, and the good news is that the backbone for it is the one annual-report dataset that
was built properly.

## `balance_sheet` is trustworthy, and almost nothing else from those reports is

774 rows, FY2011–FY2022, five fund types, and **it reconciles 72 of 72** against the
`TOTAL ASSETS` row each page prints — `balance_sheet_printed_totals` carries the printed
figure and a quote naming the page. That is the standard the trust-fund family fails.

What it already shows, excluding capital projects because borrowings make that line lumpy:

| | total held |
|---|---:|
| FY2011 | $6,034,847 |
| FY2016 | $8,175,798 |
| FY2019 | $11,107,150 |
| FY2022 | $20,935,227 |

**What the town holds roughly tripled in eleven years**, across general, enterprise,
trust/agency and special revenue alike. That is a measurement. Why it happened is not, and
rule 7 governs the difference — a page that states the trend and then explains it has
stopped reporting and started arguing.

## What the page joins

| layer | source | state |
|---|---|---|
| **Held**, FY2011–FY2022 | `balance_sheet` | reconciled, 72/72 |
| **Held, now** | `fund_activity`, FY2026 opening/closing per fund | MUNIS, system-printed |
| **Operating** | the omnibus budget | already modelled |
| **Reserves in detail** | the stabilization report | unreconciled, linked not inlined |

## Two holes to state rather than paper over

- **The balance sheet stops at FY2022.** Three years missing and the reason is not yet
  established. Find it before building the page, because a trend that ends four years ago
  invites the reader to assume it continued.
- **`special_revenue_funds` is 2,387 rows on the same broken `v1` structure** as the trust
  funds. The fund-by-fund detail beneath the totals is not reconciled, so the page can
  carry the totals and must not carry the breakdown as though it were checked.

## Order

The balance sheet is already good, so this does **not** wait on the trust-fund extractor.
Build the town page on `balance_sheet` first, link the stabilization report as the reserve
detail, and let the extraction work improve that link later rather than block the page.

---

# Attempted 20 September 2026: what actually blocks this

An extractor was built and it works. It is `scripts/extract_stabilization.py`, and it
proves every row against two identities the table itself states:

    beginning + contributions + earnings - disbursements - transfers  =  ENDING CASH
    ending cash + unrealised gain/loss                                =  ENDING MARKET

A row that does not close is not written. **It yielded two rows, both FY2014, both
proven.** That is not the series, and here is precisely why — which is worth more than the
survey's "ten of seventeen need geometry", because that description was not right.

## Three different blockers, not one

**1. Most of the pages are photographs.** The trust-fund pages carry 0 to 6 characters in
FY2011, FY2012, FY2013, FY2017, FY2019, FY2020 and FY2023. There is no text layer to read
in any reading order. This is an OCR job, not a geometry job, and `ocr_pdf.swift` already
in this repo is the tool — but OCR of a financial table then reconciled to its own totals
is a bigger and riskier piece of work than transcription, because a misread digit still
foots if two errors compensate.

**2. FY2014 is a quarter turn AND right-to-left.** `extract_text()` returns `TROPER
YRAMMUS`. The fix works and is in the script: cluster characters into bands of near-equal
x0, order each band by `top`, reverse each word and the word order. This is the part the
survey meant, and it is solved.

**3. FY2025 has clean text and prints too few columns to check.** Its rows read
`8124 Stabilization Fund 3,147,178.96 39,732.22 -` — two figures where the identity needs
six. The balances are almost certainly right; nothing in the document lets this script
prove it, so it refuses them. That refusal is correct and it is why those rows still carry
`no check`.

## What that means for the plan

The order above stands, with one correction: **step 1 is an OCR step for about half the
years**, not an extraction step. Budget accordingly, and expect the reconciliation to
carry more weight there than anywhere else in this archive — a printed grand total is the
only thing that can tell a good OCR pass from a plausible one.

`scripts/locate_stabilization_pages.py` finds the pages by reading them rather than by
arithmetic on printed page numbers, and caches the result. Its first version searched the
raw character order and missed the one page already proven to parse, which is a small
demonstration of the rule that the locator and the reader must use the same eyes.

---

# Corrected again, later on 20 September: OCR was never the blocker

TJ: *"OCR isn't a showstopper."* He was right, and more so than either of us knew: **it is
already done.**

`scripts/report_pages.py` has read all sixteen reports and cached every page as lines in
`sources/town-budget/pages/FY####.txt`, recording which instrument read each one. The raw
Vision geometry is cached too, with per-line confidence, in
`sources/town-budget/ocr/*.tsv`. The stabilization rows are legible in both. FY2020:

    8136  VEHICLE/EQUIPMENT STABILIZATION (MAIN STREET)  $643,788.80  ($300.00)  $2,122.47

So the plan's "step 1 is an OCR step" was wrong twice over. What remains is one specific
problem.

## The real blocker: skewed scans make rows overlap in y

These pages are photographs of a printed table and they are very slightly rotated, so a
row's own observations do not share a y and two adjacent rows do. There is no tolerance
that separates them:

    0.004  ->  two funds merge into one line, six values between them
    0.003  ->  one fund's row splits, the code on one line and the name on the next

The fixed-width cache shows the same thing from the other side: a row's ending values
appear on the NEXT output line, beside a different fund's name.

## What would fix it

**Anchor on the names, then assign.** A fund name (or its 81xx code) is a row anchor;
every numeric observation belongs to the anchor nearest it in y, not to a band. That
converts a clustering problem, which has no right threshold here, into an assignment
problem, which does.

**And the identities are what make it safe.** OCR digits are readings rather than figures
-- `S2,041,061.72`, `$1,968,108,91` and `$9,587,16` are all visible in the FY2020 cache --
but a misread digit almost never leaves both of these true at once:

    beginning + activity = ENDING CASH        ending cash + unrealised = ENDING MARKET

So the extractor keeps refusing what it cannot prove, and a row that survives both checks
has been verified by the document against itself rather than by anybody's eye. That is a
better guarantee than the transcription years get.

## Status

Not done. `scripts/extract_stabilization.py` reads text-layer years and proves rows;
FY2014 yields two. The OCR years need the anchor assignment above, which is a contained
piece of work now that the reading, the caching and the verification all exist.

## The technique, proven on FY2020, so nobody has to find it again

The skew is not a nuisance to be tolerated — it is **measurable from the boxes
themselves**, and once measured it is removable.

**1. Measure it.** For every numeric observation, take its nearest neighbour to the right
within a plausible column gap, and record the slope between them. The median of those is
the page rotation. FY2020 page 41: **−0.01033**, from 158 pairs. No constant is needed and
no page needs to be special-cased.

**2. Remove it.** `Y(box) = box.y − slope × box.x`. In that coordinate a table row shares a
value, which it does not in raw `y`. This is what turns the problem from "no tolerance
works" into ordinary clustering — at 0.004 in de-skewed Y, the `STABILIZATION` row goes
from one value to seven.

**3. Anchor, do not cluster.** A row is a fund: an `81xx` code box, or a name containing
STABILIZATION, excluding the section headings (`SUBTOTALS`, `GRAND TOTALS`,
`STABILIZATION FUNDS`, `... HELD BY OTHER BANKS`). A code and its name arrive as two
observations on the same row and are merged before assignment.

**4. Verify, never trust.** The identities stay the gate. OCR digits are readings.

## What is left, and it is per-year rather than technical

The columns differ between years. FY2014 prints nine in a known order; FY2020's seven
recovered values do not satisfy the nine-column identity, because the table is not the
same table. So each image-only year needs its column header read and mapped before its
rows can be checked — that is the work, and it is seven years of it.

**Do not shortcut it by matching column counts.** Two of this project's worst near-misses
came from assuming a column meant what its position suggested, and the whole reason
`column_meaning` exists is that a positional name is not a column name.
