# Analysis passes


> **Working state:** `notes/HANDOFF.md` carries the current branch, the open
> decisions and what is established versus assumed. `CLAUDE.md` carries the rules.

Internal working log. **Not published** — `sources/` is served to the public through
`/sources`, this is not. One entry per substantive pass over the material: what changed,
what it broke, and what we now know we did not know.

Written for the next person to open this repo, including us in three months.

---

# Pass 2 — Special education, and the funds outside the budget

**27 August 2026.** Branch `sped`, off `main` at the source-index work.

## 2.1 What happened

The pass began as a tangent. The question was "special education isn't in this app — does
it matter?" It matters more than anything else we have looked at.

Four things came out of it, in the order they were found:

1. **Special education is ~24% of the budget and was 51% of all growth FY23→FY26**, while
   enrollment fell. It had no line in the model and no page in the app.
2. **The model could not see it.** Costs were bucketed by DESE function-code prefix, and
   two prefixes carry both kinds of cost — `2330` is paraprofessionals general *and*
   special education, `3300` is transportation of both. So ~$5.7M of caseload-driven
   spending sat inside `salaries`, inflating at the teachers' contract rate.
3. **A quarterly financial packet the town published in August** turned out to contain a
   special education account holding **$615,301** that appears in no budget document.
4. **Every growth assumption in the model was borrowed and never checked** against four
   years of actuals sitting in the same CSV. That is the failure underneath the other
   three, and it is fixed by `scripts/backtest_rates.py`, added this pass.

## 2.2 Why special education was missed

Worth being precise, because the answer is a process gap rather than an oversight, and
process gaps recur.

**The data was never missing.** `scripts/extract_lps_budget.py` has carried `fy23_actual`,
`fy24_actual` and `fy25_actual` since the first extract. Every special education line was
in the CSV from day one.

**Nothing ever compared an assumption to history.** Checked with
`git grep 'fy23_actual' main -- model/ scripts/`: only two hits, one of them the extractor
itself and the other `derivations.py`, which reads the columns to *display* line items. No
code anywhere computed a growth rate from actuals. Every rate in `DEFAULT_ASSUMPTIONS` was
the district's own forward assumption — the comments say so: `# district assumed 9% for
FY27`, `# district assumed 10%`. We inherited the district's view of its own future and
never audited it against its own past.

**The bucketing had the blind spot built in.** Function-code prefixes are a defensible
choice — they are the state's chart of accounts — but they are the wrong grain for this
question, and no amount of care *inside* the model would have surfaced it.

**It was noticed, written down, and dropped.** `sources/analyses/fy27-and-the-override.md` §6, weeks ago:

> Out-of-district SpEd placement count/cost trend (FY26 $988,630 → FY27 $536,400 is a
> large drop that needs explaining)

The strangest number in the budget was filed as an open question and never followed up.
Meanwhile `sped_tuition` carried the highest growth rate of any bucket at 8%, so the line
was understood to be the fastest-moving thing in the budget, and still nobody asked what
sat underneath it.

**The underlying bias: analysis followed actionability rather than magnitude.** Athletics
is 1.7% of spending and had three sections, because a fee can move it and people argue
about it. Special education is 24% and had none, because "the district must place a child
where the plan requires" reads like *nothing to model here*. That reasoning is wrong. A
line nobody can control still determines the size of the problem — and people argue about
special education too, which we had simply assumed they did not.

## 2.3 What the discovery does

**To the model.** Special education became its own escalator at 7.4% — the only default on
the site that is not the district's published figure, because there is no published
figure. The base splits:

| bucket | FY27 base | observed FY23→FY26 |
|---|---:|---:|
| salaries (non-SPED) | $12,688,312 | **1.5%/yr** |
| sped | $5,745,543 | **7.4%/yr** |
| health | $4,019,071 | 6.8% |
| transport (gen-ed only) | $1,053,360 | 4.8% |
| sped_tuition | $700,142 | volatile |

Ties to the published $26,572,288 within $2. Non-SPED salaries grew 1.5% a year against a
4% contract, because positions were being cut. That is the whole problem in two numbers,
and the old bucketing averaged it into nothing.

**To the gap.** FY28 $601,014 → **$796,362**. Three-year average $552,621 → **$739,886**.
Both engines (Python and TypeScript) verified to agree to the dollar.

**To the conclusions.** Two carried the old figure in prose and are now interpolated.
Conclusion 5 (athletics self-funding) is likely to flip once the fee model is re-based —
see 2.4. Conclusion 3 needs a scope footnote: the peer comparison uses DESE *in-district*
expenditure, which excludes out-of-district tuition by definition, i.e. the fastest-growing
line it is comparing on.

**To three pages nobody edited.** The scan for literal figures in prose found:

| where | said | should have said |
|---|---:|---:|
| Walkthrough, Ch.70 first-year ask | $833,340 | **$1,146,174** |
| Walkthrough, same over ten years | $64.2M | **$93.0M** |
| Bend the curve subtitle | "$613k next year" | **$796,362** |

All three now derived. The Walkthrough pair is the worse failure — a plate of four figures
where two were computed and two typed, side by side, nothing signalling which was which.

**The general lesson.** 7 files were edited; **11 pages had numbers move without being
opened.** The type checker catches the first set and cannot see the second. Prose carrying
a figure is the only thing on this site that can be silently wrong.

## 2.4 What the uploaded documents changed

Two files arrived mid-pass: the FY26 year-end school funds workbook, and the town's Q3
FY26 financial packet. Both are now in `sources/` and catalogued. Full analysis in
`sources/analyses/sped-and-funds.md`; what matters here is what they *changed*.

**The circuit breaker turns the gap into a range.** Fund 2640 held **$615,301** at
31 March 2026 — 81% of the entire $761,000 FY27 budget reduction — with **$4,005** drawn
in nine months. But the report stops in March and districts commonly book the whole
offset as a single June entry, so a small draw through Q3 is not proof of a small draw for
the year.

That single unknown is worth more than everything else in this pass:

| circuit breaker drawn | FY28 gap |
|---|---:|
| $0 (as modeled) | $796,362 |
| $325,970 (FY26 receipts) | $470,392 |
| ~$600,000 (FY27 projected) | ~$196,362 |

Modelled at zero — conservative, matches the published appropriation — with a lever on the
special education page so the range is visible rather than asserted.

**Substantially resolved, later the same day, from data already in hand.** Two unlabelled
columns in the same row are prior-period balances. Read across, fund 2640 runs:

    $182,969  ->  $600,818  ->  $293,335 (FY26 open)  ->  $615,301 (31 Mar 2026)

The fund is **drawn down and rebuilt**. It reached $600,818, fell to $293,335 — roughly
$307,000 spent — and is climbing again. That is the signature of a district booking the
offset as a year-end entry, not of money sitting untouched. So the $4,005 through nine
months is very likely a timing artefact, and the pessimistic branch is the right one: the
gap is nearer $796,362 than $196,362.

Caveat on the inference: columns 8, 10, 13 and 15 are verified by arithmetic and against
the year-end workbook for three other funds. Columns 4 and 5 are unlabelled, and that they
are FY23 and FY24 closes is inferred from how they behave across the 17 funds that populate
both. The *pattern* — spent down, rebuilt — holds whichever years they are, and it is the
pattern that matters. Still worth one confirming question, but it is no longer the thing
the project is blocked on.

The lesson for this log: the answer was in a file we already had, in a column we had
dismissed as noise because the header row did not line up with the data rows. "Not in the
data" should have been "not in the columns I bothered to identify".

**The athletics fee model is calibrated on a base that is 45% too low.** FY26 actual fee
revenue was **$188,944** against `estimatedFy26Revenue: 130129`. Effective collection was
$279.85 per high-school participation against a modeled $214. Scaling through, the
self-funding fee falls $960 → ~$734 and peak revenue rises to ~$468,652 against a full
program cost of $451,830 — which would flip conclusion 5 from "out of reach at any fee" to
"reachable but self-defeating". **Not yet done.** It is the next self-contained piece and
does not depend on the circuit breaker answer.

**$1.73M of school money sits outside the operating budget.** Circuit breaker, school
choice, lunch, athletics, gift, after-school and the rest. Most is genuinely restricted and
must never be presented as available. But it is the mirror image of conclusion 13: that one
says one-time money funds recurring costs; this says recurring restricted money is not
being spent at all, and the largest pot is restricted to the exact driver eating the budget.

**Why none of it surfaced during the budget debate.** The Finance Director's memo is dated
11 August 2026 and reports the quarter ending 31 March 2026 — a four-and-a-half month lag,
explicitly the first of a resumed series, after the Town Accountant of 38 years retired,
their successor left, the payroll person retired and the assistant was lost. The FY27
budget was built and the override voted without current quarterly reporting. Sourced, and
must be written as record rather than accusation.

## 2.5 What else the sweep found

Having been wrong once, we ran the check properly. `scripts/backtest_rates.py` compares
every assumption to history and separately ranks every function group by size and growth.

**Real, and unbucketed:**

- **Social workers, $197,364 → $369,029, 23.2%/yr.** Two positions added in FY25. Sitting
  in `salaries` at the contract rate — *structurally the identical error to special
  education*, one order of magnitude smaller. Student mental health is the second
  demand-led line hiding in a cash-limited bucket. FY27 already trims it to $334,965.
- **`other` assumed 3%, observed 6.8%.** Under-modeled.
- **Utilities assumed 5%, observed 13.8%,** and the year-by-year is a steady climb rather
  than a spike: 372,516 → 442,328 → 491,581 → 548,450 → 605,511. Under-modeled.
- **New growth revenue is assumed at $400,000 a year for ever** while the actual series
  runs 481,496 · 472,536 · 366,231 · 308,732 · 430,254 · **234,383**. The app concludes the
  commercial base is *shrinking* and simultaneously projects $400k of new growth annually;
  those cannot both be right. At the most recent actual the gap widens $89,240 in FY28 and
  $469,075 by FY32.

**False alarms a naive scan would have reported** — the reason the script prints the
year-by-year and refuses to conclude:

- Maintenance of buildings, 27.3% — a one-time move to a contracted service, flat since.
- Business office, 39.8% — a vacancy year in the base plus a reclassification.
- Utility *services* alone, 17% — that one is an FY23 electricity spike; it is the whole
  utilities bucket, not this line, that is genuinely climbing.

**Data quality:** lines that go to zero and reappear under a new name produce −100% growth
rates that look like findings. Human Resources Director → Human Resource Specialist is one.
The script lists them so they can be ignored on sight.

**Offsetting risks, worth knowing before quoting the gap:** salaries assumed 4% vs 1.5%
observed and health 9% vs 6.8% observed. Both defensible forward (the contract is real; the
district assumed 9% and FY26→FY27 was 7.9%), but they mean the model is not uniformly
conservative. It over-states two lines and under-states three.

## 2.6 Open

1. **FY26 year-end circuit breaker balance and draw.** Highest value item in the project.
2. Is the FY27 tuition line gross, or net of expected circuit breaker? If net, the
   make-or-buy story in FINDINGS-SPED-AND-FUNDS §1.4 is wrong.
3. Re-base the athletics fee model on FY26 actuals. Independent of 1 and 2.
4. Decide on the social worker line — own bucket, or fold into a wider student-services
   escalator with special education.
5. Revisit `new_growth`, `utilities` and `other` in light of 2.5.
6. Conclusion 3 scope footnote; re-read conclusion 5 after 3.
7. Out-of-district placement *counts*, not just dollars.

## 2.7 Standing checks added this pass

- `scripts/backtest_rates.py` — assumptions against history, plus an unbucketed sweep.
  Run after any change to buckets or rates.
- `scripts/build_source_index.py` fails the build if a source file is catalogued but
  missing, or present but undescribed.
- `fy28/src/components/SpedReview.tsx` — `?sped-review` overlay listing every impacted
  area. Delete on merge.

**The habit worth keeping:** a figure typed into prose is the only thing here that can be
silently wrong. Interpolate every number that comes from the model, and when a pass moves
the model, grep the prose.
