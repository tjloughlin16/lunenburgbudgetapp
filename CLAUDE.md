# How to work in this repo

This is a public budget tool for one town. Residents and town officials read it and quote
it. The rules below exist because each one was learned by getting it wrong here.

---

## 1. Never mix budgets with actuals in one calculation

A **budget** is what somebody voted or proposed. An **actual** is what got spent. For some
lines they differ by 7%, and for out-of-district tuition by 59%.

A growth rate measured from an actual to a budget is partly growth and partly the step
between the two. That error put a special education escalator 1.5 points too high and was
invisible until somebody asked how the number was derived.

- The projection uses **budget columns only**. `finance.py` reads `fy27_balanced`.
- Actual spending answers a different question and lives in
  `sources/analyses/budget-vs-actual.md`.
- An actual may **explain** something in an analysis. It may never feed a projection.
- `scripts/audit_provenance.py` fails the build if a projection module reads an actuals
  column. Run it.

## 2. Interpolate every figure. Never type one into prose

A number typed into a sentence is the only thing here that can be silently wrong. The type
checker cannot see it, and it keeps rendering confidently long after the model has moved.

Three figures were found stating amounts the model no longer produced — one off by
$313,000. All were in prose beside figures that were computed.

- Derive it from the model, always, even when it feels stable.
- After any change to a rate or a bucket, grep the prose for literal figures.
- The same rule applies to `conclusions.py` and `headlines.py`, which are prose that ships.

## 3. Say which numbers are ours

Every figure is one of: published by somebody, set by contract, fixed by statute, or our
estimate. A reader cannot judge the argument without knowing which.

- `model/citations.py` carries the document and the basis for each headline figure.
- Anything we estimated says so, in the app, in the citation, in that color.
- The source archive is split: published by others above the line, written by us below it,
  in those words.

## 4. Weight times excess rate, not rate alone

A line matters to the gap in proportion to its **share of the budget times how far its
growth exceeds the levy cap**. Neither number means anything alone.

Utilities grow at 15% and are 2.3% of spending: 0.28 points. Teaching salaries are 35.7%
of spending and grew at 2.50%: 0.01 points. The biggest line in the budget is not a driver.

Rank by pull. Never by size, and never by rate.

## 5. Follow magnitude, not actionability

Athletics is 1.7% of spending and had three sections in this app. Special education is
about 22% and had none — because "the district must place a child where the plan requires"
reads like *nothing to model here*.

That reasoning is wrong. A line nobody controls still sets the size of the problem. Measure
everything; decide what is actionable afterwards.

## 6. Check assumptions against history, and check like for like

Every rate in the model was inherited from the district's forward budget narrative and
never once tested against its own later budgets. Four years of data sat in the same file.

- `scripts/backtest_rates.py` compares each assumption to what the line actually did,
  budget to budget. Run it after any change to rates or buckets.
- A three-year rate off a small base is not a trend. Read the year-by-year before
  concluding — three of six flagged lines turned out to be one-time step changes.
- Lines that go to zero and reappear renamed produce −100% rates that look like findings.

## 7. Only facts are stated as facts. A proxy is never a fact

**A number computed from the data is a fact. An explanation for why that number moved is
not.** The second is a hypothesis, however obvious it feels, and it must be labeled as one
every single time.

This rule has been broken here repeatedly and always the same way: a real measurement gets
one plausible cause attached, and a sentence later the cause is being restated as though it
were the measurement.

Three that shipped before being caught:

| written as fact | actually established |
|---|---|
| "The district brought children back in district" | Two budget lines moved in opposite directions by similar amounts |
| "The difference is not a pay rise — it is more staff" | The increase exceeds what the contract percentages alone produce |
| "The mix shifted toward intensity" | Two sources report different student counts and cannot be reconciled |

Each of those has other explanations that fit the same data equally well: the tuition line
may simply have been over-budgeted for years; the staffing residual could be
classifications, steps, hours, or recoding; the counts differ because they count different
things.

**How to write it instead.** Separate the two, explicitly, in the text:

- *What the data shows* — the measurement, and only the measurement.
- *What it does not show* — the alternatives that fit equally well.
- *A possible explanation, offered as a hypothesis* — if it is worth recording, say plainly
  that nothing here tests it, and name what would.

**Do not use a proxy as if it were the thing.** Dollars are not students. A budget line is
not a filled position. A count of documents is not a count of decisions. If the actual
quantity is not published, the honest sentence is that we cannot say — not a number
inferred from something adjacent to it.

Specifics that follow from this:

- If the data cannot distinguish two explanations, give both, and say it cannot.
- `MANDATE_FLOOR` is an assumption we invented because a cascade needs somewhere to stop.
  The town has cut a school psychologist to zero. There is no established floor.
- A document stating intent is evidence of intent, not of outcome. The district writing
  that in-district staff are cheaper than placements shows what it meant to do. It does
  not show what happened.
- Name what would settle it. Usually one number nobody publishes.

## 8. This app explains how to fix the problem. It is not an audit

The job is helping a resident understand what would work, and what each option costs
somebody. It is not cataloguing what the town got wrong.

- A discrepancy goes in an analysis document. It reaches the app only when it changes an
  assumption.
- Findings arrive as *what this means for planning*, never as *what they got wrong*.
- Give the district credit where the budget shows them doing the right thing.

## 9. Verify against the source after writing, not before

Every figure in a finished document gets re-checked against the data by script. Not
re-read — recomputed. Prose drifts during editing, and the version that ships is the one
nobody checked.

## 10. Nothing deploys without being asked

Tag what is live. `v1` is the build before the source archive; `v2` is the current public
build. Branch for anything substantial and never reuse a branch whose history got tangled.
Verify a deploy by hashing a document from production against the archive.

---

## 11. A budget line is NET, and it is dollars — it is not what the thing costs

**A budget line is what the town has to raise, after everything else that pays for the
thing has been subtracted.** If paras cost $1.5M and the state gives $500,000, the line
says $1M. Nothing in the document says $1.5M anywhere, and nothing marks the line as net.

The district does this deliberately and says so in its own workbook. Beside general
education transportation, in the comments column: *"Does this reflect a reduction of $50K
to accound for the money planned to come from the busing fees?"* That is a budget line
being netted down by expected fee revenue, asked about by the people writing it.

So a line can rise because the thing got more expensive, or because a grant stopped
covering part of it, or because a fee stopped being collected — and all three look
identical. **A rate measured off a net line is a rate of change in the town's share, not
in the cost.** Say which one you mean, every time.

The same trap runs the other way for anything fee-funded: modelling "what fee would make
this self-funding" against a line that is already net of fees counts the fees twice.

**And above all of it sits state aid.** Chapter 70 is roughly $11.4M of a $26.6M school
budget, and it is set in the Governor's budget rather than by anything Lunenburg does. So
even the appropriation is not the town's bill: the town's bill is what is left after
Chapter 70, and that can move without a single cost changing. A year where aid rises and
the appropriation rises with it is not the same year as one where aid is flat and the town
covers the difference, and the expense side of the budget cannot tell them apart.

The model handles this on the revenue side -- Chapter 70 is projected separately at 2% --
which is right. What must not happen is an expense line being described as "what the town
pays" when three layers sit between the two.

And you cannot see all the inputs or all the outputs, which is the general form of it.

**On the way in**, the district's budget documents show the general fund appropriation and
nothing else. Grants, circuit breaker reimbursement, school choice, revolving funds and
gifts pay for real staff and real programs and appear nowhere in them. So a line that rises
may mean the district employs more people, or may mean a grant that was paying for those
people ended and the cost landed on the town. Those are different facts about the world and
identical facts on the page.

**On the way out**, a budget shows dollars against a line and never people, children or
services. That is rule 7's territory and it is the same problem pointed the other way.

Both are why this project measures **appropriations** and says so. That is a real quantity,
it is what residents vote on, and it is what the model projects. It is not a measure of
staffing, of caseload, or of what the schools cost all in.

- Never let "the line went up" become "the district hired people". Write the first.
- Never call a budget line a cost. It is a net appropriation. If you need the cost, you
  need the grants, the fees and the revolving funds too, and they are in different
  documents.
- When a rate rests on a line, ask what else could be paying for that line, and say so
  next to the rate if you cannot rule it out.
- Name what would settle it. For funding sources that is usually DESE's End of Year
  Financial Report, which separates spending by fund; for people it is a headcount nobody
  publishes.
- The archive holding 245 documents does not fix this. Lunenburg publishes a great deal
  and still does not publish the mapping between the two.

---

## 12. Every source carries its address, its filename, and our copy

A figure is only checkable if somebody can get back to the document it came from. Three
things make that possible, and the first two are never optional.

**1. Where it came from, as deeply as it goes.** The direct link to the file itself, not
the page that lists it. `.../school-budget-information` is an index; it will be
reorganised, and the document a figure rests on will not be findable from it in two years.
Link the file.

Where there is no link because the document did not come off a website, say what did
produce it: a records request and its date, an email and who sent it, a meeting packet.
"Obtained from the Town by records request" is an address. "Public" is not.

**2. The publisher's own filename.** Links die — 57 of ours did in a single day, and every
one was a Google Drive link the district still holds. When that happens the only way a
resident gets the document is to ask the town for it by name, so record the name the
publisher used, not just the one we saved it under.

**3. Our processed copy, downloadable.** Whatever we actually read: the PDF, and the
extracted CSV or text if a figure was computed from one. If a number came out of a
spreadsheet we built, that spreadsheet is a source too and it gets published like any
other.

And a sha256 on all of it, because a Drive file can be replaced in place without its URL
changing.

**When adding a source, add all of this at the same time.** Retrofitting provenance is how
43 of our primary documents ended up with no address at all: they were gathered before the
mirror existed and nobody wrote down where they came from. The count is on the sources
page and it is meant to be uncomfortable.

**Cite the sources.** In the analyses, beside the figure, not in a footer.

---

## 13. Quote the source, never your rendering of it

Every serious error in this project's analysis has the same shape: **something derived got
quoted as though it were observed.** Not invented — derived. There was always a real thing
underneath, which is exactly why it survives review.

Four that happened in a single day:

| quoted as | actually was |
|---|---|
| "the sheet's columns are headed `FY23 ACTUALS`" | `C4='FY23'` and `C5='ACTUALS'` — two cells, stitched together by our own script |
| "the actuals sheet" | a forward budget workbook with a column headed ACTUALS |
| "`main` is 15 commits ahead" | a number read off a summary, never off the repo |
| a verifier passing on "four of eight usable years" | the string was present; there are nine |

**The rules.**

- **Cite a coordinate and the raw value.** `A20 = 'Purchase of Service (officials,
  uniforms, transportation, ice time, dues)'`. A rendered table is for reading, never for
  quoting. If you cannot give the cell or the line number, you have not checked it.
- **Check what a reader sees, not only what the file holds.** `fy27-proposals.xlsx` hides
  nine columns including FY23 actuals; our second copy of the same data hides a different
  set. Both statements "the workbook contains FY23 actuals" and "there is no FY23 column"
  were true at once. `data/document-basis.csv` records the hidden set for every workbook.
- **A check must assert the number, not the prose around it.** `verify_athletics.py` first
  checked that a sentence existed and passed while the sentence was wrong. Derive the value
  from the data and compare.
- **A summary in this conversation is not a source.** After a context reset the handoff
  reads exactly like something already verified. It is a claim about the repo, not the
  repo.
- **When an extract has a total the source itself prints, reconcile to it.**
  `extract_town_ledger.py` silently dropped 16 of 67 departments — MUNIS prints zero as
  `.00` and the regex wanted a digit before the point. Nothing noticed for weeks because
  nothing compared the extract to the report's own GRAND TOTAL. It does now, and refuses
  to write if it does not tie.

The general form: **an instrument that reformats before you see it is part of the finding,
and it has to be checked like one.**

---

## Picking up mid-stream

`notes/HANDOFF.md` is written to survive a context reset: which branch is live, what is on
the working branch and not yet deployed, the open decision, and — most importantly — the
list of claims that are NOT established, so they do not get restated as fact by somebody
arriving fresh.

---

## Running the checks

    python3 scripts/audit_provenance.py     # no projection reads actuals; model.json is fresh
    python3 scripts/backtest_rates.py       # assumptions against the district's own later budgets
    python3 scripts/build_source_index.py   # every source catalogued, every catalogued file present
    python3 model/export.py                 # regenerate model.json after any model/ change
    python3 scripts/classify_document_basis.py   # what produced each document's figures
    python3 scripts/extract_athletics_history.py # athletics, both sides, checked against its source
    python3 scripts/verify_athletics.py          # every figure in the athletics analysis
    python3 scripts/verify_free_cash_capital.py  # the capital section of the free cash analysis

## The standing questions

Some numbers would settle more than any further analysis. They are not published:

- Out-of-district **placement counts** by year. Dollars cannot distinguish fewer children
  from a more honest estimate.
- The FY26 **year-end** figures. Everything we hold for FY26 stops at 31 March.
- Whether budgeted positions were **filled**. A budget line is an intention.
- **How grants and state funding map onto the budget lines.** The budget shows the general
  fund and nothing else, so a line rising because a grant ended looks exactly like a line
  rising because the district grew. This one is load-bearing: the in-district special
  education escalator is built on a paraprofessional line, and it cannot currently be
  distinguished from grant money unwinding.
