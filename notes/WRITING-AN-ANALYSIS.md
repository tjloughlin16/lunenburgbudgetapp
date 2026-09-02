# How to write one of these

The process for producing an analysis in `sources/analyses/`. Follow it in order; the
order is the point, because three of these steps only work before the writing sets.

`CLAUDE.md` carries the rules about what may be said. This carries the sequence for
saying it. `notes/PERSONAS.md` carries the six readers step 6 runs against.

---

## Before you start: is this an analysis?

An analysis answers a question somebody would ask out loud, from data this project holds,
and reaches a conclusion that can be wrong. If it has no conclusion it is a data page; if
the conclusion cannot be wrong it is a description.

**It goes in `sources/analyses/` and nowhere else.** It is published at
`/docs/analyses/<name>.md`, rendered to PDF, and listed on `/reports` under a caveat
saying it is not official. All three happen automatically once the file exists and the
index is rebuilt.

---

## 1. Get the data in before writing a sentence

Every figure has to come out of `sources/data/lunenburg.db`. If the source is not in
there yet:

    python3 scripts/extract_<thing>.py     # to a CSV in sources/data/, reconciling first
    python3 scripts/build_db.py --check    # load it, and fail if a reconciliation drifts

**An extractor that does not reconcile to its source's own printed total is not finished.**
`extract_town_ledger.py` silently dropped 16 of 67 departments for weeks because nothing
compared its output to the report's GRAND TOTAL.

Add the document to `scripts/build_source_index.py` at the same time. The build refuses
to run with an undescribed file in `sources/`, which is the guard that keeps the public
catalogue honest.

## 2. Find the shape before you find the story

Decompose before you look for a headline. The first decomposition is almost never the
useful one.

- **By line** tells you which rows moved. It is where everybody starts and it produces
  "some went up, some went down", which is true and useless.
- **By what the money buys** — object code family: people, insurance, supplies, contracted
  services — tells you *why*. This is the one that found that every large category in FY26
  landed within 3% while the small discretionary one missed by 15%.
- **By role, one layer deeper**, when a group is large. The FY26 people line looked like
  1.1% rounding and was two role groups moving hard in opposite directions.

**Always compute the gross movement, not just the net.** A net of $482,101 that is
$1,683,534 against $1,201,434 is a completely different year from a quiet one, and only
the gross figures show it.

## 3. Write both halves of every section

Each section is written twice, under these headings:

    ### In plain terms          for anyone
    ### The evidence            for anyone who wants to check it
    ### What this does not show

The plain version never states anything the evidence does not support. **It is the same
finding in fewer syllables, not a softer one.**

`### What this does not show` is not optional and is not a disclaimer. It is where the
readings that fit the same numbers equally well are listed. If you cannot name a second
reading, you have probably not looked for one.

## 4. Say what would settle it

Every open question ends with the specific document that would close it, its holder, and
whether it is a public download or a records request. "More data would help" is not that.
"The `glytdbud` report at Year/Period 2025/13, from the Town Accountant" is.

These roll up into `notes/DATA-REQUEST.md`, which is generated — so a gap named properly
here becomes an ask automatically.

## 5. Write the verifier before you publish

`scripts/verify_<name>.py`. It derives every figure from the database and asserts the
derived string appears in the document.

**Assert the number, never the prose around it.** `verify_athletics.py` once passed
because a sentence existed, while the sentence was wrong.

Things learned the hard way, all of which have shipped as bugs here:

- **Key on what is unique.** An `org` holds several accounts — `S3991742` carries six —
  so a lookup on org alone silently checks the wrong line.
- **Match on a word boundary.** A bare substring check on the count `61` passed on the
  digits inside `$25,613,679.23`.
- **Assert magnitude, not sign.** The documents write a negative as `−$90,769.62`, a
  typographic minus before a currency symbol.
- **Collapse whitespace for phrases.** Prose wraps; a check that fails on a line break
  teaches you to avoid wrapping, which is the wrong lesson.
- **Assert the structure a paragraph rests on**, not only its figures. If a section says
  "every account in this group went over", check that, because the day it stops being
  true the paragraph is wrong while every number in it is still right.

## 6. Run the persona review — `notes/PERSONAS.md`

Six readers, one test each. This is the step that catches what a verifier cannot: a
document that is entirely correct and answers nobody's question.

Do not over-build it. The six tests are one line each and take a couple of minutes.
**But step 3 of that process is not optional and is not simulation:**

> For every category the report says underspent or overspent, search the meeting archive
> for what residents said about that thing in the same year.

That is evidence, not imagination, and it is the step that found a booster president
saying *"we currently have more heads than we have helmets"* in the same year the report
described an athletics equipment line spending 44% of its budget.

**Facebook and local groups are input to this step, never a source.** A post has no stable
address, can be edited or deleted, and cannot be checksummed — it fails rule 12 on every
count. Use it to decide what a report must answer; never to support a figure.

## 7. Charts, if the finding is visual

`scripts/build_closeout_charts.py` is the pattern. Load the `dataviz` guidance first.

Two things that will not be obvious:

- **Pie charts are almost never right here.** Variance is signed and a pie cannot draw a
  negative. Over-and-under belongs in one diverging bar, which also shows the thing two
  pies would hide: that the net is small because the arms are large and cancel.
- **Run the palette validator, then render it and look.** The validator checks colour and
  cannot see layout. Looking at the first render caught three label collisions and a
  subtitle claiming seven bars where four were drawn.

## 8. Publish

    python3 scripts/verify_<name>.py           # must pass
    python3 scripts/build_analysis_pdf.py <name>
    python3 scripts/build_source_index.py      # catalogue the document
    python3 scripts/build_reports_index.py     # add it to /reports

Add a one-line description to `ABOUT` in `build_reports_index.py`. Without one the page
falls back to the document's own opening paragraph and says so at build time.

**Nothing deploys without being asked.** Rule 10, every time.

---

## When a correction happens

It will. Four shipped in the FY26 analyses before publication and two were found by TJ
reading the PDF.

**The correction stays in the text.** Not edited out, not moved to a changelog. The
document says what it said before and why that was wrong, because a reader who spots a
change should find it acknowledged rather than buried — and because the failure modes
repeat, so a document that records its own is teaching the next one.

Then add an assertion so the same class of error fails the build rather than needing to be
noticed again.

---

## The order matters

| step | why it cannot move |
|---|---|
| Data before prose | A sentence written before the query gets defended instead of tested |
| Decompose before headline | The first decomposition is the wrong one and the headline sticks |
| "Does not show" while writing | Alternative readings are invisible once you believe the first |
| Verifier before publishing | Written after, it asserts what you wrote rather than what is true |
| Personas before publishing | Omissions are what you cannot see in your own work |
