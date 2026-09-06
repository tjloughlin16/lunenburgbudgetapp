# Working doc — modelling how money reaches the schools

**Running notes for the money-in workstream.** Started 6 September 2026. Updated as we go;
this is the file to read first when picking this up again.

**Nothing here is a source.** It is a claim about the repository and about the data. Check
anything load-bearing before acting on it — most of what follows was found by checking
something that had been believed for a while.

---

## The goal

One page that shows every route money takes into the Lunenburg school budget and out into
the line items — state aid, property tax, fees, grants, revolving funds — with the level at
which each trail goes cold stated rather than glossed.

It exists in draft: `notes/reference/data-model/money-in.html`, *"Follow the money."*
Local-only, not published. **Every figure on it is hand-typed** — 140 of them, 107 distinct
— and nothing generates any of them. Making it generated is the current task.

---

## Where we are

**Done:** `scripts/money_in_figures.py` — every quantity computed from
`sources/data/lunenburg.db`, each as a `Fig` carrying its value, its words, and **the SQL
that defines it**. The SQL is the point: an aggregate with no stated definition cannot be
checked, only believed, and two of the page's aggregates could not be adjudicated at all
for exactly that reason.

**Next:** generate the page itself from those figures, then add the annual-report history.

---

## What has been established

### The $26m is the town's bill, and the revolving funds sit on top of it

The question was whether the district's published budget is a GROSS figure (everything the
schools spend, from every source) or the town's general-fund appropriation. It is the
second, and the test is direct:

    district workbook FY26, settled       26,142,192
    town appropriation, dept 300 voted    26,247,474
    gap                                      105,282   (0.40%)

    school-side own funds, revenue in      1,011,599   (9 months, ACTUAL)
      as a share of the appropriation             3.9%

A gross budget would exceed the appropriation by roughly the fees and grants. This does not
— it lands within 0.4% — so the workbook total **is** the appropriation.

**But rule 11 still holds at the LINE level, and the two are not in conflict.** The
district's own workbook says so in its comments column, beside general education
transportation: *"Does this reflect a reduction of $50K to accound for the money planned to
come from the busing fees?"* That is one line being netted down by expected fee revenue.

So, precisely:

- **The TOTAL** is what the town raises. Not net of anything material.
- **A LINE** may be net of fees expected against it, and nothing on the page marks which.
- **The SCHOOLS' RESOURCES** exceed the appropriation by at least the revolving funds.

*Not yet established:* whether the $105,282 gap is netting, or simply that `settled` holds
252 lines where `proposed` holds 321. Check that before quoting the gap as anything.

### The page's "Town Meeting appropriation" is not what Town Meeting voted

    dept 300   original 26,247,474  + transfers  76,394  = revised 26,323,868
    dept 301   original     40,000  + transfers  -4,223  = revised     35,777

The page states the **revised** figures under the words *"Town Meeting appropriation"*. Its
arithmetic is right and internally consistent — its 51.2% is revised over revised — but the
label names a different quantity from the number. Both bases are computed now and neither
is called the other.

### Education is more than dept 300

    school only  (300 + 301)        26,287,474   51.4% of the omnibus
    plus Monty Tech (310)           27,621,995   54.0%

`310 MONTY TECH ASSESSMENT — $1,334,521` is the regional vocational school. It is education
spending, paid by the town, outside dept 300. A resident asking *"what does the town spend
on education?"* means the second number.

### The chart shows 1 of 67 departments

Ten departments are **82.9%** of the omnibus budget; the remaining 57 share 17%, and 26 of
them are under $50,000. The right-hand side of the flow diagram currently shows only the
school. It should show the shape.

### WRRS = Worcester Regional Retirement System

The town's pension assessment, `dept 820`, **$2,392,572** — the fourth-largest line.
Established three ways rather than guessed: the ledger has `COUNT[Y] RET` under dept 820;
the FY2019 annual report's budget narrative prints *"Worcester Regional Retirement
($1,354,353)"*; and the archive pairs it seven times with *"or Massachusetts State Teachers
Retirement"*.

$1,354,353 (FY2019) → $2,392,572 (FY2026) is **+77% in seven years**, but the FY2019 figure
is prose in a narrative, not a checked table row. One observation, not a trend.

**The pairing is the interesting half.** Teachers' pensions are paid by the *state*, not by
Lunenburg — so a large part of the cost of employing the district's teachers appears in
neither the school budget line nor this assessment. It points the opposite way from the
rest of the page: not money flowing in that we cannot trace, but a cost carried elsewhere
that never appears at all. **TJ wants to come back to this — not yet digested.**

### A bug worth remembering, because it is the same shape a third time

Summing `account_id LIKE '0100-%'` returned **minus $997,871** for the town budget.
`ledger_snapshot` holds 67 department-level rows and 192 detail-level revenue accounts in
one table, revenue carried negative. Every figure now joins `account` and splits on `level`
and `account_type`.

That is the `status` rule and the `v1` rule wearing a third costume: **a column that says
what a row IS cannot be skipped because the rows look alike.**

The $997,871 turned out worth naming rather than discarding — it is revenue budgeted beyond
the omnibus, which funds the other warrant articles and the reserves. It is a stated figure
now so nobody reads it as a surplus.

---

## What the annual reports add, and what they do not

**A correction first.** They do not name school revenue the FY26 ledger lacks. The ledger
has every one of those lines already — `CH 70 AID`, `SCHCOSTREI`, `PS TUITION`,
`MSBA REIMB`, `SCHOOL TRA`. What the annual reports add is **history**: five checked years
against a ledger we hold for FY2026 alone.

    CH 70 SCHOOL AID     FY14 5,516,107  FY15 5,605,872  FY17 6,351,257
                         FY18 7,272,505  FY22 7,823,618
    MSBA REIMB-SCHOOL    474,239 in every checked year   →   FY26  0
    SCHOOL MEDICAID      FY14 154,376 … FY22 156,547
    SMART GROWTH         FY15 183,618, FY17 115,148
    TRANSPORT FEES       FY14 12,090 … FY22 41,288

**MSBA is the finding.** ~$474,239 a year of school building reimbursement in every checked
year, and **zero** in FY2026 — not moved to another fund; checked. A bond reaching term is
the obvious explanation and it is a guess. When it stopped, between FY2022 and FY2026, is
not knowable from checked data.

**Usable years are FY2014, FY2015, FY2017, FY2018, FY2022** — five years where every row is
checked against the report's own printed GRAND TOTAL. The other eight have **none** checked.
Any series must show the eight as absent rather than omit them.

**Two datasets are NOT usable at all yet:**

    special_revenue_funds    0 checked   (2,058 check failed, 329 no check)
    report_appropriations    0 checked   (4,530 check failed, 135 no check)

`CLAUDE.md` forbids aggregating without splitting on `status`.
`notes/HANDOFF-ANNUAL-REPORTS.md` has the seven-step list that would make them usable.

**A phrase to keep honest:** a receipt whose *name* says school tells you what arrived **on
account of** schools. It does not say the schools received or spent it. Chapter 70 is the
proof — $9.2M arrives as *unrestricted* revenue into fund `0100` and is thereafter
indistinguishable from property tax. That is the money-in page's own grey edge, and no
document closes it.

---

## Next steps, in order

1. **Generate the page** from `money_in_figures.py` — `scripts/build_money_in.py`, with
   `--check`, registered in `check_generated.py`. Design decision still open: regenerate
   whole, or splice marked blocks the way `build_data_model_grids.py` does.
2. **Settle the two aggregates the draft could not justify** — property tax was $195,000
   above `RE TAXES + PP TAXES`, and the revenue total $27,500 above the sum of its lines.
   Neither had a recorded definition, which is why neither could be argued with.
3. **Show all 67 departments**, tail collapsed, rather than the school alone.
4. **Add the receipts history**, with the eight unusable years visible as absent.
5. **Check the $105,282 gap** between the workbook and the appropriation — netting, or
   `settled` holding 252 lines where `proposed` holds 321?
6. **OCR fixes**, especially grade-level bugs in the roster data, and the spaced-letter
   artefacts (`PRE-SCHOOL T UIT ION`) that drop a year out of its own category on any
   GROUP BY of a source name.
7. **WRRS** — TJ to digest, then decide whether it belongs on this page at all.
8. **Then** decide about publishing. Not before 1, because publishing a page of typed
   figures is how three figures once shipped stating amounts the model no longer produced,
   one of them off by $313,000.

---

## Claims NOT established — do not restate these as fact

- That the $105,282 gap is fee netting. It may be missing lines.
- That MSBA stopped because a bond reached term. That is a guess with nothing testing it.
- That WRRS grew 77%. Two observations, one of them prose from a narrative.
- That Chapter 70 funds any particular school line. It cannot be traced past the general
  fund and no document closes that.
- That the district's line-level figures are gross. At least one is documented as net, by
  the district's own comment, and nothing marks which others are.
