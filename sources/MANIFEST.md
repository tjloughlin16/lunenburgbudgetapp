# Source data manifest

The first documents here were pulled 2026-08-17 from:
- School: https://www.lunenburgschools.net/department-directory/superintendent-of-schools/school-budget-information
- Town:   https://www.lunenburgma.gov/835/2026-Annual-Town-Meeting-FY27-Budget-Hub

**The archive was reorganised on 4 September 2026 and every path in this file was updated
with it.** The tree is keyed on *how a document reached us* — the one thing about a
document that is single-valued and never changes. Fiscal year and subject are not: one
workbook here carries FY23 to FY27. Those are views, in `views/`, not folders.

    town-budget/         the Town's budget documents, warrants, financial statements
    town-supplementary/  everything else the Town publishes
    town-annual-reports/ the annual town reports, FY2011–FY2025
    town-ledgers/        MUNIS accounting reports, obtained by records request
    district-budget/     the school district's budget page, mirrored in full
    budget-workbooks/    the spreadsheets behind the district's budget documents
    contracts/           collective bargaining agreements
    meetings/            agendas and minutes for every Town board, 2025 onward
    state-dese/          Mass. Dept. of Elementary and Secondary Education
    state-dls/           Mass. Dept. of Revenue, Division of Local Services
    peer-districts/      budget documents from neighbouring districts
    correspondence/      letters and emails with officials
    analyses/            OURS — written here
    data/                OURS — extracted from the documents above

Inside each mirror, `docs/` holds the publisher's own file and `text/` our extracted text;
`town-budget/` also has `ocr/` and `pages/` for the scans that had no text layer.

**Where the bytes are, since 5 September 2026.** The published documents are no longer in
the git repository. They are in a public, locked object store, and are served at
`https://lunenburgbudgetproject.org/docs/<path>` — the same addresses as before. What
stays in git is everything that changes: the extracted text, the derived CSVs, the
analyses. `data/archive-manifest.csv` lists every file with its sha256, is published at
`/data/archive-manifest.csv`, and `python3 scripts/sync_archive.py --pull` is how a fresh
clone gets the documents themselves.

**Access, and what it cost to find out.** On 29 August 2026, 60% of the district's own
links returned a Google sign-in wall — 57 of 187, including the FY27 proposed budget
document the site's central appropriation figure comes from. The district was asked to
reopen them and did. On **31 August** the same 187 came back **186 open**; the one still
walled is a notice of a budget hearing from April 2020. Twenty-one addresses were then
added (below), two of which are walled, so the archive as it now stands is **205 of 208
open**.

That made a check possible that had not been possible before, and it was run: every
document in the mirror was re-downloaded from the district's own address and compared to
our copy by sha256. **82 of 87 were byte-identical to the copies taken on 17 August.** Of
the five that were not, three are Google Docs whose every zip member matched (Google
re-packages a Doc on each export, so the hash moves and the document does not), one is the
same 26-page presentation the page publishes twice under two Drive ids — identical text,
one line-break in a heading falling in a different place — and one is the 2020 notice
nobody can fetch. **Nothing the district publishes had changed underneath us.**

`scripts/verify_source_copies.py` re-runs that comparison and writes
`data/copy-status.csv`.

## School department (Google Drive)

| File | What it is | Value for FY28 |
|---|---|---|
| `district-budget/docs/final-budget-document.pdf` | FY27 proposed budget, 3/25/26. Line items: FY26 Final, FY27 Restoration/Core/Balanced | ★★★ |
| `district-budget/docs/fy27-budget-projections-as-of-3-23-26.pdf` | Same, 3/23/26, **includes Level Service column** (5 scenarios) | ★★★ |
| `district-budget/docs/fy27-budget-projections-as-of-3-16-26-with-restorations.pdf` | Earlier line-item version w/ restorations | ★★ |
| `district-budget/docs/budget-addendum-multi-scenario-financial-analysis.pdf` | Narrative defining all 4 scenarios, cut/restore lists, headcount, comparative summary | ★★★ |
| `district-budget/docs/additional-town-revenue-spending-plan.pdf` | The $453,722 Sept-2026 add-back plan + rationales | ★★★ |
| `district-budget/docs/lhs-athletics-faq.pdf` | The **superseded** athletic fee schedule — $250/$140/$85 HS with a $475 family cap, $200/$150 MS. Still the only fee schedule posted publicly, though the fee rose to $400/$300/$225 with a $1,500 cap for 2026-27. Address: [rschooltoday, the schedule vendor's file store](https://tts-livesite.rschooltoday.com/sites/lunenburghs.rschoolteams.com/files/files/Private_User/jbunnell/Frequently%20Asked%20Questions.pdf), publisher's name `Frequently Asked Questions.pdf`, verified byte-identical 31 Aug 2026. **Not hosted by the school** — it is on a third-party sports-scheduling platform, under a staff member's private-user folder, which is about as durable as an address gets here. | ★★ |
| `district-budget/docs/athletic-program-costs-by-sport.pdf` | **Per-sport cost and participation**, 25 sports, FY24. The basis for every fee calculation. | ★★★ |
| `district-budget/docs/balanced-budget-slides-3-23-26.pdf` | Slide deck — **image-only, no extractable text** | ★ |
| `district-budget/docs/slide-deck-from-the-sc-meeting-3-23-26.pdf` | SC deck 3/23/26 — **image-only, no extractable text** | ★ |

Dead link on the school site: "FAQ – November Town Meeting"
(drive id `1ntDb3MeOIRRLosIF1GqdDMJz6wB5sB68`) returns 404.

## Town of Lunenburg

| File | What it is | Value for FY28 |
|---|---|---|
| `town-budget/docs/4090-click-here-for-a-release-on-quot-understanding-lunenburg-apos-s-fy27-budget-how-.pdf` | Town Manager 4/17/26 — **the revenue formula**, all three budgets by category, cut lists, tax impact, free cash | ★★★ |
| `town-budget/docs/3769-fy-2027-operating-budgets-balanced-tier-1-tier2.pdf` | Omnibus by department, 3 scenarios | ★★★ |
| `town-budget/docs/4082-fy-2027-detailed-budget.pdf` | Line-item town budget by ORG/OBJ, 3 scenarios (incl. Monty Tech assessment) | ★★ |
| `town-supplementary/docs/town-2026-election-unofficial-results.pdf` | **Override Q1/Q2 both failed** — precinct tallies. [DocumentCenter/View/4193](https://www.lunenburgma.gov/DocumentCenter/View/4193), the town's own name **"5/16/2026 Annual Town Election Unofficial Results (PDF)"**, verified byte-identical 31 Aug 2026. The town also posts **official** results at [View/4247](https://www.lunenburgma.gov/DocumentCenter/View/4247); we hold the unofficial one, and the word is in its title for a reason | ★★★ |
| `town-budget/docs/3765-town-meeting-booklet-including-warrant.pdf` | 2026 ATM booklet + warrant, 52pp | ★★ |
| `town-budget/docs/4161-2026-annual-town-election-warrant.pdf` | Ballot question language | ★ |
| `town-budget/docs/4111-article-13-fy-2027-capital-plan.pdf` | FY27 capital plan | ★ |

## Spreadsheets

**`budget-workbooks/fy27-budget-projection-3-25-26.xlsx` was sent directly to this project by Ana Lockwood, a
member of the Lunenburg Finance Committee,** under her own filename *"FY27 School Department
Budget Projection as of 3.25.26"*. That is its address. Rule 12 counts an email and who sent
it as an address, and this is one — it was never on a public page, which is why no amount of
crawling was going to find it.

*Why a name here when the records request names nobody.* `town-ledgers/account-details/` withholds
the resident who filed it on purpose. The difference is the capacity: a private resident
asking the town a question is not part of any address a reader needs, while a Finance
Committee member circulating a budget workbook is acting as a town official, and which
official is exactly what tells a reader what the document is. The role is checkable — the
Committee's own agenda letterhead lists `Ana Lockwood` among its members, most recently on
[27 August 2026](https://www.lunenburgma.gov/AgendaCenter/ViewFile/Agenda/_08272026-7970).

**`budget-workbooks/fy27-proposals.xlsx` — the one nearly every budget-line figure on this site comes out of —
still has no address**, and it is not a renamed copy of the Lockwood file: different sizes
(97,035 against 122,265 bytes), different hashes, and of their twelve shared zip members
exactly one is byte-identical.

What the files say about themselves is now recorded in `budget-workbooks/PROVENANCE.md`, and it is
worth reading before guessing: all three were created by **Christopher McNamara, the
district's Business Administrator**, at the same timestamp to the second, so they are one
workbook saved three times. The 25 March copy's `cp:lastModifiedBy` reads **Ana Lockwood** —
the file corroborating the account of how it reached us. `budget-workbooks/fy27-proposals.xlsx` has no last
modifier at all and its zip members are stamped **2 April 2026, 05:35**.

**Metadata says who authored a file, never who gave it to us**, so none of that is a route.
The district's budget page *as mirrored on 17 August 2026* publishes exactly one
spreadsheet — the FY26 Town Manager's budget sheets of 5 February 2025, two sheets,
FY25–FY26 — and it is not this workbook. Whether the page carried it back in April cannot be
checked: the Internet Archive holds no snapshot of it.

**What takes the sting out of it, and what does not.** Every figure the site publishes from
that workbook is reproduced *cell for cell, formula for formula* in the Lockwood copy, which
does have an address. `scripts/verify_workbook_twins.py` measures this rather than asserting
it: across columns E through M — FY25 budget, FY26 final, FY26 actuals-to-date and
encumbrances, and all four FY27 scenarios — **zero cells differ**. So a reader can check any
published figure against a document traceable to a named town official. That is not the same
as the load-bearing file having its own address, and it is not offered as if it were.

`budget-workbooks/fy27-budget-projection-2-24-26.xlsx` has no recorded route either, but we do hold the
publisher's own filename: an untouched copy sits in the repository root as *"FY27 Budget
Projection as of 2.24.26 with restorations (2).xlsx"* and is byte-identical to it. The `(2)`
is the suffix a browser adds to a second download of the same name, so the published name is
almost certainly without it — *almost certainly*, not certainly.

`notes/findings/DATA-WANTED.md §15`.

| File | Notes |
|---|---|
| `budget-workbooks/fy27-proposals.xlsx` | **Richest single artifact.** The 3/25/26 workbook. 1,197 rows. Columns C/D/E are headed `FY23`/`FY24`/`FY25` over `ACTUALS` — the district's **restatement** of those years inside a forward budget, not a ledger extract; the only ledger-basis document for school lines is `district-budget/text/fy23-quarterly-budget-update.txt`. Also FY25 budget, FY26 final + actuals-to-date + encumbrances, all four FY27 scenarios, an out-year forecast column (sheet labels it "FY29"), and a 2/24/26 restoration snapshot. **Columns C, H, I, N, O, P, T, U, V are hidden**, so FY23 actuals and the FY26 actuals-to-date and encumbrances do not appear on screen when the file is opened. Source of `data/lps-budget-lines.csv`. |
| `budget-workbooks/fy27-budget-projection-3-25-26.xlsx` | The same 3/25/26 workbook as circulated to the Finance Committee, **sent to us by a member of it on 27 August 2026** under the name *"FY27 School Department Budget Projection as of 3.25.26"* — the only one of these three with a recorded address. **Identical to `budget-workbooks/fy27-proposals.xlsx` in every budget column**, checked cell by cell at formula level by `scripts/verify_workbook_twins.py`: 0 differences across columns E–M. Everything that does differ is outside the budget: 391 cells of an unheaded scratch column `Y` holding `=Jn-Kn`, which this copy does not carry, and a five-cell year-over-year ratio row (230) under TOTAL EXPENSES, which only this copy has. A further 14 differences are `=sum(` against `=SUM(` — the same sum over the same range. **Not presentation-identical**: this copy hides F and shows C, the other hides C and shows F, so the two files put different columns in front of a reader. |
| `budget-workbooks/fy27-budget-projection-2-24-26.xlsx` | Earlier, thinner version. Publisher's own filename *"FY27 Budget Projection as of 2.24.26 with restorations.xlsx"*, from a byte-identical copy left in the repository root |
| `budget-workbooks/dese-all-districts.xlsx` | DESE per-pupil + total expenditures by category, FY2017-18 → FY2023-24, Lunenburg vs 11 peer districts, w/ enrollment |
| `supplemental.csv` | Town Manager FY27 target: $26,476,533.21 (+$689,059.28) — a pre-Balanced figure |

## Local peer districts (`peer-districts/`)

Primary-source FY27 budget documents from neighboring districts. All downloaded
2026-08-17; `.txt` alongside each `.pdf`.

Every one of these was traced back to its publisher on **31 August 2026** and re-downloaded
from that address; all six matched our copy byte for byte. **Four of the six are not hosted
by the district that wrote them** — two sit on content networks a school website happens to
use, and two are in a *member town's* document centre rather than the region's. That is why
none of them could be found by looking at a district budget page, and it is a reminder that
"the district publishes it" and "the district hosts it" are different claims.

| File | District | Address | What it gives |
|---|---|---|---|
| `peer-districts/groton-dunstable-fy27-budget-book.pdf` | Groton-Dunstable | [thrillshare CDN](https://files-backend.assets.thrillshare.com/documents/asset/uploaded_file/2198/Gdrsd/a9c839f0-1ed0-4e9a-b125-32a1c58ca85d/Budget-Book-FY27-01.28.26.pdf) — publisher's name `Budget-Book-FY27-01.28.26.pdf` | 132pp full budget book — three straight years of cuts, below level service, override needed |
| `peer-districts/ashburnham-westminster-fy27-presentation.pdf` | Ashburnham-Westminster | [ParentSquare CDN](https://files.smartsites.parentsquare.com/6739/ashburnham_westminster_budget27_presentation_1.pdf), linked from [awrsd.org/budget-information](https://www.awrsd.org/budget-information) | Superintendent's FY27 budget — explicitly preserves athletics/arts/music, cuts 2 elementary FTE |
| `peer-districts/ashburnham-westminster-fy27-detail.pdf` | Ashburnham-Westminster | [ParentSquare CDN](https://files.smartsites.parentsquare.com/6739/fy27_budget_detail.pdf) — publisher's name `fy27_budget_detail.pdf` | Line-item detail |
| `peer-districts/ayer-shirley-fy27-expenses.pdf` | Ayer-Shirley | [Town of **Ayer** document centre](https://www.ayer.ma.us/DocumentCenter/View/13478), not the district's | Level-service budget by function, health insurance +14.4% |
| `peer-districts/north-middlesex-finance-subcommittee.pdf` | North Middlesex | [nmrsd.org via finalsite](https://resources.finalsite.net/images/v1764774508/nmrsdorg/bregkjqfing6b9eyfqzz/2025-12-01-FinancePacket.pdf) — publisher's name `2025-12-01-FinancePacket.pdf`. **It is the Finance Subcommittee packet for 1 December 2025**, not undated summit notes | FY27 Budget Summit notes — $64k vs $1.5M deficit at 3% vs 5% growth |
| `peer-districts/wachusett-fy27-budget-presentation.pdf` | Wachusett | [Town of **Rutland** document centre](https://www.rutlandma.gov/DocumentCenter/View/3583), a member town | Assessments, enrollment by town, discretionary contribution +9.21% |

See `analyses/peer-districts.md` Part 2 for the extracted comparison.

## Derived

`data/document-basis.csv` classifies every document here by what produced its figures —
`ledger` (the accounting system: a figure exists because a transaction did), `restatement`
(a prior year re-presented inside a document written by the party that spent it), `forward`
(proposed, requested, level service, balanced), `narrative`. Each row quotes the raw header
text the classification rests on, with its line number or cell reference. Regenerate with
`python3 scripts/classify_document_basis.py`. Do not hand-edit it.

Of 216 documents, 15 are ledger-basis, and exactly one of those reaches school budget lines.

| File | Notes |
|---|---|
| `data/lps-budget-lines.csv` | 356 rows (351 line items + 5 subtotal rows). Tidy: section, function_group, line_item, and one column per fiscal-year/scenario. Line sums tie to printed totals within ~$2 for FY25–FY27 (FY23 off $10k, FY24 off $5k — two group rows carry figures the printed totals treat differently). |

Regenerate: `python3 scripts/extract_lps_budget.py`

## Tax base and Chapter 70

**`town-budget/docs/tax-classification-fy23.pdf` is the single most valuable town document found.**
The FY2023 Tax Classification Hearing (Board of Assessors) carries year-over-year series
nothing else does. Its address is
<https://www.lunenburgma.gov/DocumentCenter/View/138>, the town's own file, under the
town's own name **"Fiscal Year 2023 Tax Classification (PDF)"** — verified byte-identical
to our copy on 31 August 2026.

- **New growth by year**: FY18 $481,496 · FY19 $472,536 · FY20 $366,231 · FY21 $308,732 ·
  FY22 $430,254 · **FY23 $234,383** — a 51% decline. The FY27 budget assumes $400,000.
- **Assessed value by class, FY22 → FY23**: residential +23.33% (+$370,289,172) while
  commercial −0.25%, industrial −3.18%, personal property −1.00%. The entire CIP base
  shrank $1,523,062 in absolute dollars.
- **Average single family**: FY19 rate $18.68 / value $308,900 / bill $5,770 →
  FY23 rate $14.62 / value $470,164 / bill $6,874. Values +52%, rate −22%, bills +19%.
  This is the Proposition 2½ paradox in the town's own table.
- **Excess levy capacity**: single-digit thousands most years — the town levies to the max.
- FY23 class detail: commercial $74,992,410 · industrial $23,827,600 ·
  personal property $55,152,710 · total CIP $153,972,120 (7.29%).
- The Assessors' own note on a maximum split-rate shift: residential bills would fall
  about 3.9% while CIP bills rose 50%.

Census Business Patterns 2024: **234 establishments**, 2,172 employees, $126.7M payroll —
about $658,001 of assessed value per establishment.

**Gap:** we could not retrieve classification hearings after FY23 (the town does not index
them). FY24–FY26 new growth and class values would extend every series above.


| File | What it gives |
|---|---|
| `town-budget/docs/1591-town-revenue-amp-proposition-2-5-presentation.pdf` | Finance Committee deck on Prop 2½ mechanics — levy ceiling vs limit vs levy, and the DOR analysis showing assessed value outpacing the levy since 2017 ("less available revenue during more growth") |
| `budget-workbooks/ch70-fy27-summary.xlsx` | DESE FY27 **preliminary** Chapter 70 — [`p-summary-district.xlsx`](https://www.doe.mass.edu/finance/chapter70/fy2027/p-summary-district.xlsx), verified byte-identical 31 Aug 2026. Preliminary means the *Governor's* budget figures, which is the point of rule 11: this number is set in Boston and can move without a single Lunenburg cost changing. Lunenburg: foundation enrollment 1,599; foundation budget $23,089,580; required contribution $14,135,611; **Chapter 70 aid $9,349,335**; required NSS $23,484,946 |

Tax structure, FY26: single rate **$14.39/$1,000**; levy **$35,819,996**; total taxable
value **$2.489B** (levy ÷ rate); **residential ~91%**, commercial + industrial + personal
under 10%. A split rate was considered and declined — it would have set residential at
$13.70 and commercial at $21.58, adding ~$2,300 to the average commercial bill.

Derived: each $1M of new taxable value is worth **$14,390 a year, permanently**. Local
cost per pupil after Chapter 70 is **$10,894**; the school share of an average tax bill is
**$3,959** — so it takes the school taxes of **2.75 average homes to educate one child**.

## Business registrations (`data/business/`)

Copied from a separate project on this machine (`~/lunenburgbusiness`), which cleaned and
categorised the Town Clerk's business certificate records.

**These are the weakest provenance in the archive and they are catalogued on the wrong side
of the line.** They sit under "published by the town" while both files carry a `source`
column reading `master` — they are our merge and our categorisation, not the Clerk's
records as the Clerk holds them. Nothing here records how the underlying certificates were
obtained: a records request, a counter visit, or a download. Until that is written down
there is no address to give, and "Town Clerk business certificate records" is a description
of a document rather than a route to one.

| File | Contents |
|---|---|
| `data/business/merged_dataset.csv` | 711 certificate records — cert number, issue/expiry, name, owner, address, status, renewal chain |
| `data/business/categorized.csv` | 554 records tagged by industry category |

**What it shows.** 363 active certificates today. New registrations peaked at 114 in 2022
and fell to 61 in 2025 (−46.5%), still well above the 2018–19 baseline of ~33. But:

- **64% are at addresses on residential streets**, only 35.5% on a commercial corridor
- **only 25%** are in trades that normally need commercial premises
- **only 39 addresses** in the whole town host more than one business

So business *formation* is healthy while commercial *square footage* is not — which is
exactly why registrations hold up while the Assessors report the commercial tax base
shrinking. A consultant working from a spare room pays residential tax.

**Caveats.** A business certificate is a d/b/a filing under M.G.L. c.110 §5, required only
of sole proprietors and partnerships — corporations and LLCs register with the Secretary of
the Commonwealth, so they are not all here. These are registrations, not employment or
floor space, and a different universe from the 234 Census establishments. Certificates run
four years, so coverage before 2018 is incomplete (every 2016–2021 record is now lapsed,
renewed or discontinued, exactly as a four-year term predicts). 2026 is partial.

## Fee schedules (athletics updated 2026-08-18)

Lunenburg **does** charge fees. An earlier version of this research wrongly stated it did not.

**The athletic fee was raised for 2026-27.** Source of record: the Superintendent's email
to families, August 2026 — "$400 for your first child, $300 for the second, and $225 for
the third. There is still a family cap of $1,500."

As of 2026-08-18 the new schedule is **not posted anywhere we can find**. The LHS athletics
FAQ (`district-budget/text/lhs-athletics-faq.txt`, re-checked 2026-08-18) still shows the old figures, and
neither lunenburgschools.net, the LHS athletics page nor the RevTrak portal publishes a fee
table. Searched: district site, LHS site, LHS athletics page, rschoolteams FAQ PDF, RevTrak
store, School Committee agendas for 2026, local press (LocalLens, The Tracker). LocalLens
reported a **$325** first-child proposal with a $1,500 cap earlier in 2026; the adopted
figure is higher.

| Fee | Amount (2026-27) | Was |
|---|---|---|
| Athletics, 1st child, per season | **$400** | $250 |
| Athletics, 2nd child, per season | **$300** | $140 |
| Athletics, 3rd child, per season | **$225** | $85 |
| Athletics, family cap | **$1,500** | $475 (per season) |
| Unified Track | $100 (old schedule; not restated in the email) | $100 |
| Bus, per year | $180 one student · **$270 family cap**; reduced $50/$75; free if qualifying | unchanged |

Not stated in the email, and so unresolved: whether middle school keeps a separate lower
schedule ($200/$150 under the old one), whether the $1,500 cap is per season or per year,
and when the School Committee voted the increase.

Bus rules: grades 7–12 all pay; K–6 pay only under two miles (state law requires free
transport beyond that). Bus cheques are payable to the *Town of Lunenburg*, not the school.

**Where the money goes — what we could and could not establish.** The LPS FY27 budget
document is expenditures only, so fee income is invisible in it. The Town's §53E½
revolving funds (ATM Article 6) list twelve funds — ambulance, library, parks, technology,
and a $13,000 school custodial special-details fund — but **neither athletics nor student
transportation**. Athletic and activity fees in Massachusetts are normally held under
M.G.L. c.71 §47, outside the §53E½ regime, which fits their absence. The district does use
revolving money to offset appropriated costs (the FY27 addendum moves "$50,000 from school
choice revolving/transportation to offset transportation costs").

**Unresolved:** whether the $451,830 athletics figure is gross or already net of roughly
$128,000 in fee income; what is actually collected and how many waivers are granted;
whether band or club fees exist at all. Three good questions for the Business Manager.

## Web sources without a downloadable file
- Enacted FY27 state budget aid: https://www.lunenburgma.gov/m/newsflash/Home/Detail/261 (+$471,121)
- Sept 3, 2026 Special Town Meeting call: https://www.lunenburgma.gov/CivicAlerts.aspx?AID=262
- Budget sandbox site: https://sites.google.com/lunenburgschools.net/budget-sandbox (near-empty shell)

---

# Added 2026-08-20

## Union contracts (`contracts/`)

Full write-up, including the verification method and what is still missing:
**`contracts/CONTRACTS.md`**. Ten PDFs in `contracts/pdf/`, text in `contracts/txt/`.

The headline: the **Lunenburg Education Association agreement runs 1 July 2024 to 30 June
2027** and raised the salary scale **2.5% (FY25), 4.0% (FY26), 3.5% (FY27)** — 10.33%
compounded — with **step increases worth about 3.32% a year on top**, plus lane changes.
That is where the model's 4% salary growth assumption comes from, and it is the reason a
"5% pay cut" is best understood next to the raises it would take back. **It expires at the
end of FY27**, so FY28 is the first year of an agreement nobody has negotiated yet.

| Unit | Term | Raises | Expires |
|---|---|---|---|
| Teachers (LEA) | FY25–FY27 | 2.5 · 4.0 · 3.5% | 2027-06-30 |
| Paraprofessionals (AFSCME 503) | FY26–FY28 | 3.0 · 2.0 · 2.0% | 2028-06-30 |
| Custodians (AFSCME 93) | FY27–FY29 | 3.5 · 2.5 · 2.5% | 2029-06-30 |
| Secretaries | 2025–2028 | not public | 2028-06-30 |
| Cafeteria | 2023–2026 | not public | 2026-06-30 |

`contracts/data/lea-teacher-salary-schedule.csv` — 13 steps × 10 lanes × FY25/26/27, built
from the printed FY25 grid and the contract's own multipliers (OCR of the FY26/FY27 grids
interleaves columns and was not trusted). FY25 Bachelor step 1 $50,790 → FY27 $54,671;
Doctorate step 13 $102,459 → $110,287.

Administrators are a gap: DESE publishes only expired templates (superintendent 2018–21,
principal 2019–22 at 2%/yr). No current agreement for the superintendent, business manager,
principals or directors is public.

Most of these are page scans. `scripts/ocr_pdf.swift` reads them with the macOS Vision
framework — no third-party install, no network:

    swift scripts/ocr_pdf.swift in.pdf out.txt [scale]

## Meeting archive, 2025– (`meetings/`)

Every agenda and set of minutes the Town publishes, across all boards. The folder is
`meetings/`; the **published address stays `/docs/minutes/...`**, because a folder name is
internal and a URL is a promise this project has already made 1,422 times.

    python3 scripts/fetch_agendas.py --from 2025 [--to YYYY] [--inventory]
    python3 scripts/extract_minutes.py

**40 boards · 1,422 documents listed · 1,422 fetched · 2025-01-06 → 2026-11-17 · 426MB.**
948 agendas, 474 sets of minutes.

**This paragraph used to say 1,383 of 1,422, with 39 that "return an error page".** They
did not. They were Word files, and two halves of one assumption hid each other: the fetcher
tested `blob.startswith(b'%PDF')` and recorded anything else as missing, while the
extractor walked `*.pdf` only. One of the 39 was School Committee minutes from the middle
of FY26. The fetcher now identifies a file from its magic bytes and the extractor reads
Word and Excel too. **`scripts/search_minutes.py` prints the denominator on every run** —
how many documents were searched out of how many the town has published — because a grep
that finds nothing prints nothing, and nothing reads as *nobody said it*.

- `meetings/index.csv` — board, date, kind, file id, local path, source URL
- `meetings/<board-slug>/YYYY-MM-DD-{agenda,minutes}-<id>.pdf`
- `meetings/text/<board-slug>/….txt` — extracted text, mirroring the PDF tree
- `meetings/text/_needs-ocr.txt` — files with no text layer, for `ocr_pdf.swift`

Heaviest boards: Select Board 141 · School Committee 119 · Conservation Commission 95 ·
Finance Committee 84 · Sewer Commission 80 · Planning Board 79.

**Why a scraper rather than the site search.** CivicEngage renders one board-year at a
time; the year tabs are an AJAX `POST /AgendaCenter/UpdateCategoryList {year, catID}`. Its
own search endpoint under-returns older years badly — 20 hits for 2025 where the School
Committee's own tab has 80 — so the script walks board × year directly. It is resumable
and skips files already on disk.

### Already found in here

- **2026-03-18 School Committee** — approved an enhanced health insurance opt-out
  negotiated with the Public Employee Committee: eligible after **1 year** instead of 2,
  incentive up from **$2,000/$4,000** to **$3,000/$6,000** (individual/family). A decided
  cost-containment measure on the health line.
- **2026-04-15** — negotiating reps assigned for cafeteria and custodial. None for the
  teacher unit, consistent with LEA talks not opening until after 1 November 2026.
- **2026-07-29** — executive session noticed for collective bargaining.
