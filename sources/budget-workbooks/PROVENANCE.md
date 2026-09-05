# The three FY27 workbooks — where they came from, and what is still not known

Nearly every budget-line figure on this site comes out of `fy27-proposals.xlsx`. For most of
this project's life none of these three files had a recorded address at all. This is what is
now established, what is corroborated, and what remains unknown — kept separate on purpose.

`scripts/verify_workbook_twins.py` re-derives every claim below from the files themselves and
fails if any of them stops being true.

---

## What the files say about themselves

Every `.xlsx` is a zip, and two of its members record authorship: `docProps/core.xml` and
`docProps/app.xml`. Quoting the tags rather than a rendering of them:

| | `fy27-proposals.xlsx` | `fy27-budget-projection-3-25-26.xlsx` | `fy27-budget-projection-2-24-26.xlsx` |
|---|---|---|---|
| `dc:creator` | Christopher McNamara | Christopher McNamara | Christopher McNamara |
| `dcterms:created` | 2025-11-04T18:07:42Z | 2025-11-04T18:07:42Z | 2025-11-04T18:07:42Z |
| `cp:lastModifiedBy` | *absent* | **Ana Lockwood** | *absent* |
| `dcterms:modified` | *absent* | 2026-03-27T01:44:48Z | *absent* |
| `Application` | *no `app.xml`* | Microsoft Excel Online | *no `app.xml`* |
| zip member stamps | 2026-04-02 05:35 | 1980-01-01 00:00 | 2026-02-26 11:34 |

**Christopher McNamara is the school district's Business Administrator.** Not inferred from
the name: the School Committee's own minutes of 1 October 2025 list him under `Guests:` as
"Christopher McNamara – Business Administrator"
(`sources/meetings/text/school-committee/2025-10-01-minutes-7432.txt`, line 21).

---

## What this establishes

**All three are saves of one workbook.** Same creator, same creation timestamp to the
second. They are not three documents; they are one document at three moments.

**The 25 March copy came from Ana Lockwood, and the file agrees.** TJ received it from her
by email, and independently of that, the file's own `cp:lastModifiedBy` reads `Ana Lockwood`,
saved 27 March 2026 through Microsoft Excel Online. Her membership of the Finance Committee
is checkable against the Committee's own agenda letterhead, most recently
[27 August 2026](https://www.lunenburgma.gov/AgendaCenter/ViewFile/Agenda/_08272026-7970).
The zeroed zip stamps are what a server-side export writes, which is consistent with the
`Excel Online` application tag.

**A date for `fy27-proposals.xlsx`, which previously had nothing.** Its zip members are
stamped **2 April 2026, 05:35** — a week after the 25 March workbook it contains. That is
when those bytes were written.

---

## What this does NOT establish

**Metadata says who authored a file. It does not say who gave it to us.** `dc:creator`
naming the Business Administrator is a fact about the workbook, not a route: it would read
the same whether the file was emailed, downloaded, or handed over on a memory stick. **We
did not obtain any of these from Christopher McNamara so far as anything here records.**

**Where `fy27-proposals.xlsx` came from is unknown.** The recollection is that it was found
online. Nothing establishes that. What is ruled out:

- **The district's budget page** publishes exactly one spreadsheet across all 87 documents —
  the FY26 Town Manager's budget sheets of 5 February 2025, two sheets, covering FY25–FY26.
  Not this workbook.
- **The town's FY27 Budget Hub** links thirteen documents and every one of them is a PDF,
  confirmed by content type, not by file extension.
- **The rest of the town site**: no `.xlsx` appears anywhere in the 74-document mirror, and
  searches of the town's own document centre for the obvious phrasings return only PDFs.

**The absence of a last modifier is suggestive and it is not proof.** `fy27-proposals.xlsx`
and the 24 February copy both lack `cp:lastModifiedBy` and `app.xml`, while the Lockwood copy
has both — consistent with those two having been downloaded rather than opened and re-saved
by a person. Save paths differ, metadata can be stripped, and this distinguishes *how a file
was last written*, never *how it reached us*.

**It is not a renamed copy of the Lockwood file.** Asked directly, and the answer is no in
three independent ways: the two are **97,035 and 122,265 bytes** with different sha256s;
of the twelve zip members they share, **exactly one is byte-identical** and nine differ,
including `xl/worksheets/sheet1.xml` itself; and each holds members the other does not —
`fy27-proposals.xlsx` carries an embedded drawing (`xl/drawings/drawing1.xml`) that the
Lockwood copy has no trace of, while the Lockwood copy has `docProps/app.xml` and
`xl/calcChain.xml`. Two different saves of one underlying workbook, arriving by two routes.

**The Internet Archive cannot settle it either.** It holds no snapshot of the district's
budget page at all, so the version of that page as it stood on 2 April 2026 — the day
`fy27-proposals.xlsx` was written — cannot be inspected. The recollection that it came from
the school budget page is therefore neither confirmed nor refuted by anything outside the
file; what can be said is that the page **as mirrored on 17 August 2026** does not carry it.

**What would settle it.** One sentence from whoever obtained it: the link, the email and its
sender, or the packet. Nothing published closes this from the outside.

---

## The mitigation, and its exact limit

Every figure this site publishes from the untraced workbook is reproduced **cell for cell,
formula for formula** in the Lockwood copy, which does have an address. Across columns E
through M — FY25 budget, FY26 final, FY26 actuals-to-date and encumbrances, and all four FY27
scenarios — **zero cells differ**. Everything that does differ sits outside the budget: an
unheaded scratch column `Y` holding `=Jn-Kn` in 389 rows that the Lockwood copy does not
carry, a five-cell year-over-year ratio row under TOTAL EXPENSES that only the Lockwood copy
has, and fourteen cells where one file writes `=sum(` and the other `=SUM(`.

So a reader can check any published figure against a document traceable to a named town
official.

**That is not the same as the load-bearing file having its own address**, and it is not
offered as if it were. The file the pipeline actually reads still has no provenance.

*(An earlier version of `MANIFEST.md` described these two as differing in "51 cells, all in
an unused scratch column (col X, full of `#VALUE!`)". None of that reproduces — the column is
Y, it holds `=Jn-Kn`, and the count is 410 at formula level. The substance survived and every
specific in it was wrong, which is why the comparison is now a script.)*
