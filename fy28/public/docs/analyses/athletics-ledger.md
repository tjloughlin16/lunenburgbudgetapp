# The athletics ledger: what a fund's cashbook shows that a budget line cannot

On 17 June 2026 the Town of Lunenburg answered a resident's public records request with
five files. Three are MUNIS journal exports for the athletics revolving fund.
One is the district's own sport-by-sport athletics workbook, covering three school years.
One is a page of participation counts by fee category.

Provenance, filenames and hashes: `sources/munis-ledgers/account-details/PROVENANCE-fund1301.md`.

This is the first time this project has held **a dated record of money moving** for anything
that touches the school budget. The archive holds 3,230 documents and, before these arrived,
exactly one of them reached school budget lines on a ledger basis — a single quarter of FY23.
Everything else is a prior year re-presented by the party that spent it, inside the argument
for next year's budget.

What follows is what the files show. Where something is our arithmetic rather than the town's
figure, it says so, because the distinction is the whole point of holding a ledger.

---

## 1. The fund's cash, three years, tied end to end

Each export carries its own opening balance as a row the town wrote — `SRC='SOY'`,
`REFERENCE='SOY BAL'`. That gives the extract a total the source itself prints, so the closing
balance we compute for one year can be checked against the opening balance the town prints
for the next. It ties to the cent, all three years. `extract_fund1301_ledger.py` refuses to
write if it ever stops tying.

| | opening | receipts | payments | net | closing |
|---|---:|---:|---:|---:|---:|
| **FY2024** | 137,845.84 | 213,151.11 | −317,003.64 | **−103,852.53** | 33,993.31 |
| **FY2025** | 33,993.31 | 390,299.87 | −293,054.09 | **+97,245.78** | 131,239.09 |
| **FY2026** | 131,239.09 | 171,247.62 | −171,153.77 | **+93.85** | 131,332.94 |

FY26 is not a full year. Its effective dates stop at **12 June 2026**, eighteen days short,
and it carries no year-end journal entries. Every FY26 figure in this document is to that
date and should not be compared with a closed year without saying so.

**The fund lost $103,852.53 of cash in FY2024** and ended the year at $33,993.31 — on a fund
whose payments that year were $317,003.64. That is about five weeks of spending in hand.

Three people described the fund as running a deficit in 2025, and `athletics.md` §4a records
that we held the endpoint and not the path. We now hold the path. What it shows is below.

---

## 2. Four journal entries carry the fund, and we do not know what they are

Of the $390,299.87 that came into the fund in FY2025, **$254,121.18 — 65% of it — is four
general-journal entries**, each described only as an expense adjustment made per a memo:

| effective | posted | journal | `REF1` | `REFERENCE` | amount | `COMMENTS` |
|---|---|---:|---|---|---:|---|
| 2025-02-12 | 2025-02-12 | 157 | `JE FEB` | `ADJ EXP` | 1,282.57 | `PER MEMO 01/30/25` |
| 2025-05-02 | 2025-05-06 | 54 | `JE MAY` | `ADJ EXP` | 113,559.00 | `PER MEMO 05/02/25` |
| 2025-06-30 | 2025-07-02 | 709 | `JE JUN` | `ADJ EXP` | 19,271.08 | `PER MEMO 7/02/25` |
| 2025-06-30 | 2025-08-27 | 1339 | `JE JUN` | `ADJ EXP` | 120,008.53 | `PER MEMO 08/20/2025` |

FY2024 has one of the same shape: journal 1576, effective 2024-06-30, posted 2024-09-18,
**49,925.00**, `ADJ PER MEMO 08/12/24`. FY2026, to 12 June, has none.

**Take the four away and FY2025 closes at −$122,882.09.** That is arithmetic on the town's
own rows: 131,239.09 − 254,121.18.

That figure sits beside something recorded in `athletics.md` §4a — a resident telling School
Committee on 3 September 2025 that the fund "was running in a deficit, I was told over
$100,000". It is the right order of magnitude and the right year.

**What this does not establish.** It does not establish that the fund ran a deficit, and it
does not establish what these entries were for. An entry raising cash in a fund and labelled
as an expense adjustment is consistent with at least three different things: expenses
originally charged here and later moved to another fund; a transfer in from another fund; a
correction of charges posted to the wrong account. Those are different facts about the world
and identical facts on the page. The memos would settle it, and we do not hold them.

It also does not establish that the fund was *overdrawn* on any date. We can order the rows
by effective date and carry a balance, and doing so puts the fund below zero from mid-November
2024 to early May 2025 — but that ordering is ours, not the town's. MUNIS backdates: journal
1339 is effective 30 June 2025 and was posted 27 August 2025. Rows sharing an effective date
have no defined order. The CSV column is named `running_balance_derived` for that reason, and
no figure from it is quoted as a finding here.

**The single most valuable thing the town could hand over next is five memos**, dated
08/12/24, 01/30/25, 05/02/25, 07/02/25 and 08/20/2025.

---

## 3. Where the money actually goes

Splitting every row by its MUNIS source code:

| | receipts `CRP` | warrants `APP` | payroll `PRJ` | reversals `GRV` | journals `GEN` |
|---|---:|---:|---:|---:|---:|
| FY2024 | 135,965.36 | −190,978.99 | −121,346.72 | +22,582.82 | +49,925.00 |
| FY2025 | 131,481.37 | −140,878.92 | −124,895.03 | −22,582.82 | +254,121.18 |
| FY2026 | 166,421.63 | −136,753.30 | −30,513.84 | +939.36 | 0.00 |

**The fund ran a payroll.** $121,346.72 in FY2024 and $124,895.03 in FY2025 — and then
$30,513.84 in FY2026, a quarter of the earlier figure. The FY2026 number is not merely close
to the fund's own year-end report; it is that report's salary line to the cent:
`school-funds-fy26.xlsx!Athletics Revolving!B19 = 30513.84`, described there as
*"Salaries (4 revolving-fund staff)"*. Two documents produced by different processes agree
exactly, which is the strongest corroboration anything in this analysis has.

What we cannot say is **whose** payroll the FY2024 and FY2025 figures were. The export carries
no name, no position and no object code on a payroll row. The district's own athletics
workbook attributes $127,088.40 of coaching cost to FY2024, which is the right neighbourhood
— but the general fund also carried $65,073.00 of coaches that year, and the two together far
exceed the workbook's figure. Something does not add up and the ledger cannot say what.

**Receipts are net of a payment processor.** Every month carries a deposit referenced
`MMMYY/REVTRA`, `/REVTPM` or `/REVTSC` and a smaller negative row referenced `MMMYY/REVFEE`.
Reading the second as the processor's charge against the first is an inference, but it is what
the sign and the timing look like: −$1,557.13 in FY2024, −$4,037.18 in FY2025, −$3,133.51 in
FY2026. The rest arrives as counter receipts, `MISC RCPTS`, most of them carrying a staff
member's name in the vendor field.

This matters for rule 11 in the direction rule 11 warns about. **The fee revenue reaching this
fund is already net of the processor's cut.** A fee model calibrated on what the fund banked
is not a model of what families paid.

---

## 4. The fund's own FY26 report and this ledger reconcile — and disagree about a year

`school-funds-fy26.xlsx` is the fund's year-end reconciliation, already in the archive. Set it
beside the journal:

- The report's **beginning undesignated fund balance at 1 July 2025** (`C5`) is **110,247.89**.
- The journal's **opening cash at 1 July 2025** (`SOY BAL`) is **131,239.09**.
- The difference is **20,991.20**.

The report names that exact figure twice — at `Summary!A16` and at `Athletics Revolving!A26` —
as the accounts payable balance, invoices recorded as expenditures but not yet paid in cash.
And the journal's **first FY2026 disbursement**, effective 8 July 2025, is a warrant payment of
**−20,991.20** against reference `1 W/P 25`, an FY25-numbered warrant. (It is the second
movement of the year; the first is a $250 receipt the day before.)

So the two documents tie exactly, and each explains the other: cash exceeded fund balance by
the invoices still unpaid, and those invoices were paid in the first week of the next year.

**But the report dates that balance to 6/30/26, and the journal shows it paid on 8 July 2025.**
`Summary!A16` reads *"~$20,991.20 of FY26 spending was recorded as Accounts Payable at 6/30/26"*.
For
the report's own reconciliation to work, the figure has to be the payable at **6/30/25**. The
alternative — that the payable was $20,991.20 to the cent in two consecutive years — is not
impossible, but it is not what the journal shows being paid.

The report's ending balance — `Athletics Revolving!C8`, **152,280.91** — is unaffected either
way. What is affected is the sentence at `Athletics Revolving!A26` explaining why cash rose
only $21,041.82.

This is worth recording for a reason beyond athletics: **it is the second document in this
archive found to attach the wrong year to a real figure**, and both were caught only by
setting two sources beside each other. The FY25 balance sheet for fund 1301 would settle it,
and remains item 3 of `notes/REQUEST-3c.md`, unfilled.

**And note what the report's own label does.** `C8` reads *"Ending Fund Balance / Cash
(6/30/26)"*, one cell holding two quantities that differ by $20,991.20 whenever anything is
unpaid. `athletics.md` and `notes/HANDOFF.md` both record the fund as closing FY25 at
**+$110,248**. That is right as a fund balance. Its **cash** was $131,239.09. Both numbers are
correct and they are not the same number.

---

## 5. Athletics costs what nobody has published

The district's sport-by-sport workbook is the only document we hold that puts a cost against
a sport. Each season sheet prints its own total, and prints it twice — once for the season's
own lines and once including that season's third of the costs shared across all three.

| | Fall | Winter | Spring | all-in |
|---|---:|---:|---:|---:|
| **FY2024**, season only | 118,417.55 | 130,758.64 | 102,466.70 | 351,642.89 |
| **FY2024**, as the sheet prints it | 129,248.47 | 141,589.56 | 113,297.62 | **384,135.65** |
| **FY2025**, season only | 129,805.45 | 118,643.26 | 35,272.44 † | 283,721.15 |
| **FY2025**, all-in | 142,063.50 | 130,901.31 | 47,530.49 † | **320,495.30** |

† **The Spring FY2025 column does not tie.** The sheet prints 17,224.94 at `BO25` while its
own sport rows sum to 35,272.44 — the transportation column for that season and year is blank
at the total and populated in the rows beneath it. Every figure marked † uses the rows. All 342
of these total checks are published in `sources/data/athletics-by-sport-reconciliation.csv`;
271 tie and 71 do not, and which is which is a property of the document rather than of our
reading of it.

Now put that beside the general fund, category by category, taking only the categories the
workbook and the budget both name:

| FY2024 | workbook | general fund | outside the general fund |
|---|---:|---:|---:|
| Officials | 51,570.04 | 0.00 | 51,570.04 |
| Coaches | 127,088.40 | 65,073.00 | 62,015.40 |
| Transportation | 117,555.00 | 40,000.00 | 77,555.00 |
| Uniforms | 16,293.54 | 10,698.00 | 5,595.54 |
| everything else matched | 39,135.91 | 37,568.00 | 1,567.91 |
| **total** | **351,642.89** | **153,339.00** | **198,303.89** |

A further **$160,980.00** sat on general fund athletics lines with no counterpart in the
workbook at all — the athletic director, the trainer and insurance, none of which the workbook
tracks.

**In FY2024 the town's athletics appropriation covered 44% of what the district's own workbook
says the sports cost.** That is rule 11 stated as a measurement rather than as a warning, and
it is the first time this project has been able to make it one for any program.

Two things this does not say. It does not say the district hid anything: the fund is a
Chapter 658 revolving fund, its purpose is to hold fee revenue and spend it, and the district
described the arrangement in its own FY26 budget overview. And it does not generalise to other
programs by arithmetic — 44% is athletics' number, and nothing here measures anybody else's.

---

## 6. The citizen workbook is no longer unproven

`athletics.md` §6 records `Athletics_v10.xlsx` — a resident's analysis — as UNPROVEN, held
without the ledger under it, and acted on nowhere. Its central figures were that athletic
transportation cost **$117,555 in FY24** against a general fund line of $40,000, and
**$91,066 in FY25** against $87,822.

Summed from the sport rows of the town's own workbook:

```
FY2024   Fall 44,627.50   Winter 39,092.00   Spring 33,835.50   total  117,555.00
FY2025   Fall 43,446.06   Winter 29,377.50   Spring 18,242.50   total   91,066.06
```

Both reproduce to the cent. The residuals against the general fund line — $77,555.00 for FY24
and $3,244.06 for FY25 — reproduce too, and they are the figures `athletics-history.csv`
currently carries with `basis=unproven`.

**What changed is the provenance, not the arithmetic.** The numbers were never wrong; they
rested on a copy whose origin we could not show. They now rest on a workbook the Town supplied
in response to a records request. The subtraction that turns a total into a revolving-fund
share is still ours, and still an inference: it assumes the workbook's total and the budget's
line measure the same universe of trips.

The direction question in `HANDOFF.md` §4 resolves. The app does not double-count athletics
fees; it **understates the transportation line**, because the line was never the cost.

`athletics-history.csv` still says `unproven`, and `model/export.py` still keys the app's
"partial fund data" marking off that exact string. Changing it changes published figures, so
it is not changed here — `REQUEST-3c.md` ends by saying that decision comes last, and it still
does.

---

## 7. Transportation moved in FY2025, and now it has a date

The migration `athletics.md` §6 could only date approximately is visible in the ledger.

- In **FY2024** the fund's cash paid out $317,003.64 while taking in $135,965.36, and the
  general fund's transportation line was $40,000 against a $117,555.00 cost.
- In **FY2025** the general fund's transportation line rose to $87,822 and the workbook's cost
  fell to $91,066.06 — a residual of $3,244.06, effectively nothing.
- In **FY2026** the fund's payroll drops to $30,513.84 and its own year-end report describes
  its purchases of service as *"officials, uniforms, transportation, ice time, dues"*.

The sequence is: the fund carried a large share, the fund ran its cash down to five weeks,
the town's line rose, the fund's obligations shrank.

**The causal story is not established and three orderings fit.** The town may have taken the
cost on because the fund could not carry it; the fund may have been relieved of it as a matter
of policy and the cash consequence followed; or both may follow from a third decision recorded
in the memos. Nothing in these files distinguishes them. `athletics.md` §4a already records
that the fund never had slack in any year we can see, which weakens "the fund was drained"
as a special explanation for FY25 — it was never full.

---

## 8. The fee schedule changed, and the model does not know

`model/athletics.py` carries an open question, recorded in its own comments: the measured FY26
fee revenue implies **$287.82 per high school participation** against a published first-child
fee of **$250**, and a blended rate cannot exceed its top tier. Either participations were
undercounted or there were surcharges in no schedule we held. The whole fee model is carried as
a two-sided range because of it.

The workbook answers it. `Spring!E1 = 'Full Pay'`, and the three columns of that block are
labelled `E2='23/24'`, `F2='24/25'`, `G2='25/26'`:

```
Spring!E3 = 250      Spring!F3 = 250      Spring!G3 = 325
```

**The high school fee was $325 in 2025-26, not $250.** The same strip gives the reduced fees:
`Q3=32.5`, `R3=32.5`, `S3=50` for high school, and `T3=26`, `U3=26`, `V3=40` for middle school.

At $325, a blended $287.82 is unremarkable. The anomaly was an artefact of pricing FY26 at the
FY25 rate.

Measured directly against participation counts from the same workbook: FY26 gross high school
fees of $167,511.49 over 533 high school participations is **$314.28** — below $325, as it must
be once waivers and sibling discounts are in the pool. The model's `PRIOR_ATHLETIC_FEES`
prices FY26 at $250/$140/$85, and `MODELLED_FY26_FEE_REVENUE` is built on it. That is a 30%
error on the first-child rate and it is the main thing `FEE_CALIBRATION` has been absorbing.

**The middle school half does not resolve.** $27,097.96 gross over 116 middle school
participations is **$233.60**, against a middle school fee the workbook states as $200 for the
two earlier years — `Fall!A21` and `Winter!A18` both read `'MS- $200.'`. For 2025-26 the
corresponding banner, `Spring!A20`, reads `'MS-'` with no amount, and no document we hold gives
the 2025-26 middle school fee. So the blended rate still exceeds the only stated rate, on the
smaller and cleaner base, and the honest answer is that the middle school fee for that year is
unknown rather than that the anomaly persists.

The sibling rates for 2025-26 are also absent: `Spring!J3` and `Spring!M3` are empty where the
two earlier years carry 140 and 85.

**Separately, `athletic-fee-counts-2025-2026.docx` — one page, headed `ATHLETIC FEES 2025-2026`
— gives fee-category counts for that year** —
the only source that does, since those columns are empty in the workbook. Fall: 176 full pay,
8 reduced, 14 first-sibling discount, 2 second-sibling, 33 full waiver. Winter: 149, 4, 8, 1,
26. Spring: 130 full pay, 6 reduced, 15 second-sibling, 1 third-sibling, 20 full waiver, and a
row reading `Met family cap fee 1500`.

Those sum to 593 participations against the workbook's 649 for the same year, and the labels do
not match between them — Spring counts a second sibling where Fall and Winter count a first,
and the docx does not separate high school from middle school. **The two documents do not
reconcile and should not be added together.** The waiver counts are the striking figure on
their own terms: 79 full waivers across the year, against 455 full-pay.

---

## 9. What this says about special education, and about everything else

Nothing in these five files measures special education. They are athletics: one fund, one
department, 1.7% of school spending. Rule 5 says magnitude decides what matters, and by
magnitude this is a small corner of the budget.

What travels is the **mechanism**, and it travels to the one question this project has
repeatedly called load-bearing.

`notes/DATA-WANTED.md` §3b asks how grants and state funding map onto the budget lines,
because the in-district special education escalator is built on a paraprofessional line that
cannot currently be distinguished from grant money unwinding. That has always been an argument
from possibility: a line *could* rise because a grant ended.

These files change its standing from possible to demonstrated, in the only program where both
sides are visible:

- **A program's cost can be more than twice its appropriation.** Athletics' FY2024 comparable
  general fund lines were $153,339.00 against $351,642.89 of cost.
- **Costs move between funds by memo, and the memo does not appear in either budget document.**
  $254,121.18 moved in FY2025 on four journal entries. Neither the general fund budget nor the
  fund's own summary shows a trace of it. The FY2024 budget-to-budget change in the athletics
  transportation line would look identical whether the cost changed or the funding source did.
- **The change happens after the year ends.** Journal 1339 is effective 30 June 2025 and posted
  27 August 2025 — after the fiscal year closed, and after the FY26 budget was voted.

So when a district budget document prints an "actual" for a prior year, that figure may have
been adjusted by a memo months after the year it describes, and the document will not say so.
That is a general property of the source material this project rests on, established here for
the first time from a ledger rather than argued from principle.

**It raises the prior on the paraprofessional question. It does not answer it.** Athletics has
a revolving fund with a visible cashbook; special education's funding sources are circuit
breaker reimbursement, IDEA grants and Chapter 70, and none of them has produced a document
like this one. The number that would settle it is still DESE's End of Year Financial Report,
which separates spending by fund.

There is a second, narrower consequence. `sources/data/document-basis.csv` classifies every
financial document in the archive by what produced its figures, and before these arrived it
found fifteen on a ledger basis, of which exactly one reached school budget lines. Rerun, it
now scans **349** documents and finds **10** on a ledger basis: **these three journal exports
are the second, third and fourth to reach school money**, and they are the first to cover
complete fiscal years.

They needed a new signal to be seen at all. The classifier's existing ledger patterns look for
MUNIS report titles and account-code columns, and a journal export has neither. What it has is
a header row carrying a journal number beside both an effective and a posting date — which is
the tightest ledger signature in the archive, because a restatement has no posting date. It has
a paragraph. The classifier now matches on that, and quotes the raw header row it rests on, as
every other row in that file does.

**The sport workbook is classified `narrative`, and that is wrong.** `narrative` means money
discussed with no figure table, and this document is nothing but figure tables. The taxonomy
has four values — ledger, restatement, forward, narrative — and none of them fits a
departmental operating record: it is not the accounting system, it is not a prior year
re-presented inside a budget argument, and it is not a proposal. Rather than invent a signal to
push it into the nearest wrong box, it is left where the classifier puts it and named here.
`athletic-fee-counts-2025-2026.docx` is not classified at all; the classifier reads `.txt` and
`.xlsx` only.

They are a revolving fund rather than the general fund, so none of this lifts the general
finding. **School general fund spending still rests on one quarter of FY23.**

---

## 10. Claims that are NOT established

| tempting | actually established |
|---|---|
| The fund ran a $123,000 deficit in FY2025 | Without four journal entries its cash would have closed at −$122,882.09. The entries exist and are the town's |
| The fund was overdrawn from November to May | That is our ordering of backdated rows, not the town's balance |
| The four `ADJ EXP` entries moved costs to the general fund | An expense adjustment raising cash. Three readings fit and we hold no memo |
| The fund's payroll was coaches | The export carries no name, position or object code on a payroll row |
| The town's line rose because the fund ran out | The sequence is visible; the causation is not, and the fund never had slack in any year |
| The FY26 report is wrong | Its arithmetic is right. One label attaches 6/30/26 to a payable the journal shows paid on 8 July 2025 |
| Athletics costs $384,135.65 | That is what the district's operating workbook totals for FY2024. It is not a ledger and it does not reconcile to one |
| The general fund pays 44% of athletics generally | One year, one program, comparable categories only |
| Middle school fees exceed the middle school rate | The 2025-26 middle school rate is not stated in any document we hold |
| 593 students played sports in 2025-26 | Two town documents give 593 and 649 for the same year and count different things |
| The archive now has ledger coverage of school spending | Three years of one revolving fund. The general fund still has one quarter of FY23 |

---

## 11. What to ask for next

In order of what each would settle:

1. **The five memos** behind the `ADJ EXP` journal entries: 08/12/24, 01/30/25, 05/02/25,
   07/02/25, 08/20/2025. These decide whether $304,046.18 across two years was a
   reclassification, a transfer, or a correction — and that is the difference between "the
   town's share rose" and "the cost rose".
2. **The same `Account_Detail` export for the general fund athletics orgs**, `S3066672` and
   `S3066671`, all object codes. The request asked for this and did not get it; what arrived
   was fund 1301's cash account only. Item 1 of `REQUEST-3c.md`, still open.
3. **The FY2025 balance sheet for fund 1301.** Item 3 of `REQUEST-3c.md`. It would settle the
   year attached to the $20,991.20 payable, and give the FY25 fund balance against the FY25
   cash we now hold.
4. **The 2025-26 fee schedule**, all tiers, both levels — the workbook gives the high school
   full-pay rate and the reduced rates and nothing else.
5. **Vendor detail on payments.** Column `X` (`VDR NAME/ITEM DESC`) is populated on receipts
   and empty on every one of the disbursement rows. Warrant numbers are there — `19 25`,
   `47 25`, `66 25` — so the warrants themselves would name the carriers. Item 4 of
   `REQUEST-3c.md`.

---

## How to reproduce every figure in this document

```
python3 scripts/extract_fund1301_ledger.py       # the cashbook, and the SOY chain check
python3 scripts/extract_athletics_by_sport.py    # the sport workbook, and its 342 total checks
python3 scripts/verify_records_request_2026_06.py  # every figure above, recomputed
```

The sources are in `sources/munis-ledgers/account-details/`, with `PROVENANCE.md` beside them
carrying the town's own filenames and a sha256 for each. The derived tables are
`sources/data/fund-1301-cash-journal.csv`, `sources/data/athletics-by-sport.csv` and
`sources/data/athletics-by-sport-reconciliation.csv`.

General fund comparisons are taken from `sources/data/athletics-history.csv`, whose figures
for FY2024 and FY2025 come from `fy27-budget-projections-as-of-2-24-26-with-restorations.txt`
— a forward budget document restating prior years, not a ledger. Setting a restatement beside
a ledger is the whole exercise here, and neither is a substitute for the other.
