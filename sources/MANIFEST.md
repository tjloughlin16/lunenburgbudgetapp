# Source data manifest

All files pulled 2026-08-17 from:
- School: https://www.lunenburgschools.net/department-directory/superintendent-of-schools/school-budget-information
- Town:   https://www.lunenburgma.gov/835/2026-Annual-Town-Meeting-FY27-Budget-Hub

`pdf/` originals · `txt/` extracted text (pypdf) · `xlsx/` spreadsheets ·
`data/` machine-readable CSV built by `scripts/extract_lps_budget.py`

## School department (Google Drive)

| File | What it is | Value for FY28 |
|---|---|---|
| `fy27-final-budget-doc` | FY27 proposed budget, 3/25/26. Line items: FY26 Final, FY27 Restoration/Core/Balanced | ★★★ |
| `fy27-projections-3-23-26` | Same, 3/23/26, **includes Level Service column** (5 scenarios) | ★★★ |
| `fy27-projections-3-16-26` | Earlier line-item version w/ restorations | ★★ |
| `fy27-multi-scenario-addendum` | Narrative defining all 4 scenarios, cut/restore lists, headcount, comparative summary | ★★★ |
| `town-additional-revenue-plan` | The $453,722 Sept-2026 add-back plan + rationales | ★★★ |
| `lhs-athletics-faq` | The **superseded** athletic fee schedule — $250/$140/$85 HS with a $475 family cap, $200/$150 MS. Still the only fee schedule posted publicly, though the fee rose to $400/$300/$225 with a $1,500 cap for 2026-27. Source: Lunenburg High School athletics site. | ★★ |
| `athletic-program-costs-by-sport` | **Per-sport cost and participation**, 25 sports, FY24. The basis for every fee calculation. | ★★★ |
| `fy27-balanced-slides-3-23-26` | Slide deck — **image-only, no extractable text** | ★ |
| `fy27-sc-slidedeck-3-23-26` | SC deck 3/23/26 — **image-only, no extractable text** | ★ |

Dead link on the school site: "FAQ – November Town Meeting"
(drive id `1ntDb3MeOIRRLosIF1GqdDMJz6wB5sB68`) returns 404.

## Town of Lunenburg

| File | What it is | Value for FY28 |
|---|---|---|
| `town-fy27-budget-press-release` | Town Manager 4/17/26 — **the revenue formula**, all three budgets by category, cut lists, tax impact, free cash | ★★★ |
| `town-fy27-operating-budgets-balanced-tier1-tier2` | Omnibus by department, 3 scenarios | ★★★ |
| `town-fy27-detailed-budget` | Line-item town budget by ORG/OBJ, 3 scenarios (incl. Monty Tech assessment) | ★★ |
| `town-2026-election-unofficial-results` | **Override Q1/Q2 both failed** — precinct tallies | ★★★ |
| `town-atm-2026-booklet-warrant` | 2026 ATM booklet + warrant, 52pp | ★★ |
| `town-2026-election-warrant` | Ballot question language | ★ |
| `town-article13-fy27-capital-plan` | FY27 capital plan | ★ |

## Spreadsheets

| File | Notes |
|---|---|
| `xlsx/fy27-proposals.xlsx` | **Richest single artifact.** 1,197 rows. FY23/24/25 actuals, FY25 budget, FY26 final + actuals-to-date + encumbrances, all four FY27 scenarios, an out-year forecast column (sheet labels it "FY29"), and a 2/24/26 restoration snapshot. Same file as `public/data/proposals.xlsx`. |
| `xlsx/fy27-budget-projection-2-24-26.xlsx` | Earlier, thinner version (`public/data/budget.xlsx`) |
| `xlsx/dese-all-districts.xlsx` | DESE per-pupil + total expenditures by category, FY2017-18 → FY2023-24, Lunenburg vs 11 peer districts, w/ enrollment |
| `supplemental.csv` | Town Manager FY27 target: $26,476,533.21 (+$689,059.28) — a pre-Balanced figure |

## Local peer districts (`peers/`)

Primary-source FY27 budget documents from neighbouring districts. All downloaded
2026-08-17; `.txt` alongside each `.pdf`.

| File | District | What it gives |
|---|---|---|
| `groton-dunstable-fy27-budget-book` | Groton-Dunstable | 132pp full budget book — three straight years of cuts, below level service, override needed |
| `ashburnham-westminster-fy27-presentation` | Ashburnham-Westminster | Superintendent's FY27 budget — explicitly preserves athletics/arts/music, cuts 2 elementary FTE |
| `ashburnham-westminster-fy27-detail` | Ashburnham-Westminster | Line-item detail |
| `ayer-shirley-fy27-expenses` | Ayer-Shirley | Level-service budget by function, health insurance +14.4% |
| `north-middlesex-finance-subcommittee` | North Middlesex | FY27 Budget Summit notes — $64k vs $1.5M deficit at 3% vs 5% growth |
| `wachusett-fy27-budget-presentation` | Wachusett | Assessments, enrollment by town, discretionary contribution +9.21% |

See `PEER-PRECEDENT.md` Part 2 for the extracted comparison.

## Derived

| File | Notes |
|---|---|
| `data/lps-budget-lines.csv` | 356 rows (351 line items + 5 subtotal rows). Tidy: section, function_group, line_item, and one column per fiscal-year/scenario. Line sums tie to printed totals within ~$2 for FY25–FY27 (FY23 off $10k, FY24 off $5k — two group rows carry figures the printed totals treat differently). |

Regenerate: `python3 scripts/extract_lps_budget.py`

## Tax base and Chapter 70

**`pdf/tax-classification-fy23` is the single most valuable town document found.**
The FY2023 Tax Classification Hearing (Board of Assessors) carries year-over-year series
nothing else does:

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
| `pdf/town-revenue-prop25-presentation` | Finance Committee deck on Prop 2½ mechanics — levy ceiling vs limit vs levy, and the DOR analysis showing assessed value outpacing the levy since 2017 ("less available revenue during more growth") |
| `xlsx/ch70-fy27-summary` | DESE FY27 preliminary Chapter 70. Lunenburg: foundation enrolment 1,599; foundation budget $23,089,580; required contribution $14,135,611; **Chapter 70 aid $9,349,335**; required NSS $23,484,946 |

Tax structure, FY26: single rate **$14.39/$1,000**; levy **$35,819,996**; total taxable
value **$2.489B** (levy ÷ rate); **residential ~91%**, commercial + industrial + personal
under 10%. A split rate was considered and declined — it would have set residential at
$13.70 and commercial at $21.58, adding ~$2,300 to the average commercial bill.

Derived: each $1M of new taxable value is worth **$14,390 a year, permanently**. Local
cost per pupil after Chapter 70 is **$10,894**; the school share of an average tax bill is
**$3,959** — so it takes the school taxes of **2.75 average homes to educate one child**.

## Business registrations (`business/`)

Copied from a separate project on this machine (`~/lunenburgbusiness`), which cleaned and
categorised the Town Clerk's business certificate records.

| File | Contents |
|---|---|
| `merged_dataset.csv` | 711 certificate records — cert number, issue/expiry, name, owner, address, status, renewal chain |
| `categorized.csv` | 554 records tagged by industry category |

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
FAQ (`txt/lhs-athletics-faq`, re-checked 2026-08-18) still shows the old figures, and
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

## Meeting archive, 2025– (`minutes/`)

Every agenda and set of minutes the Town publishes, across all boards.

    python3 scripts/fetch_agendas.py --from 2025 [--to YYYY] [--inventory]
    python3 scripts/extract_minutes.py

**51 boards · 1,422 documents listed · 1,383 fetched · 2025-01-06 → 2026-11-17 · 408MB.**
928 agendas, 455 sets of minutes. 39 are listed by the town but return an error page
instead of a file (11 of them Sewer Commission); they are in the index with an empty
`path`.

- `minutes/index.csv` — board, date, kind, file id, local path, source URL
- `minutes/<board-slug>/YYYY-MM-DD-{agenda,minutes}-<id>.pdf`
- `minutes/text/<board-slug>/….txt` — extracted text, mirroring the PDF tree
- `minutes/text/_needs-ocr.txt` — files with no text layer, for `ocr_pdf.swift`

Heaviest boards: Select Board 141 · School Committee 119 · Finance Committee 84 · Sewer
Commission 80 · Planning Board 79 (+42 public hearings) · Board of Assessors 63.

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
