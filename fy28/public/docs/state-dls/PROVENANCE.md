# DLS free cash proof — Lunenburg and eight comparable towns, 2021–2025

## Where it came from

**Massachusetts Department of Revenue, Division of Local Services.** Downloaded 30 August
2026 by this project. The DLS Municipal Databank publishes a "Free Cash Proof" per
community; these are that report, exported one town at a time.

**The exact download URL is not recorded, and that is a gap on our side.** Rule 12 asks for
the address as deeply as it goes, and "the DLS databank" is a hub, not an address. It needs
filling in from the browser history of whoever pulled them. `notes/DATA-WANTED.md` §5 records
that DLS pages sit behind bot protection, which is why these could not be fetched by script.

**Two things about that gap were narrowed on 31 August 2026, and one was not.**

*Narrowed: the right department, and the deepest page there is.* These were catalogued under
DESE, which is the wrong agency — DESE sets Chapter 70, the Department of Revenue certifies
free cash — and they now sit under DOR's Division of Local Services. The public report is
the DLS Gateway's **City & Town Free Cash Report**:

<https://dls-gw.dor.state.ma.us/gateway/dlspublic/certificationfreecashpublicreport/certificationfreecashpublic>

It answered a plain request, and all nine towns are on its jurisdiction list — Lunenburg is
**162**, and Ayer 019, Groton 115, Littleton 158, Shirley 270, Townsend 299, Upton 303,
Uxbridge 304, Westford 330. The report is built on submission from two dropdowns held in
session, so **there is no file URL to give**: the page plus the jurisdiction is the whole
address, the same shape as DESE's selected-populations report. That is recorded in
`build_source_index.py`'s `FORM_ONLY`, with the reason beside it.

*Not narrowed: which export produced these files.* Driving the report from outside a browser
session returns "Free Cash/Excess & Deficiency is not available for years prior to FY 2014",
which is the report declining the request rather than answering it, so **our copies have not
been re-derived and are not claimed to have been.** The filename `FCPCompare<Town>.xlsx` and
the five-year layout say the export was a multi-year comparison; nothing here establishes
which control produced it. Naming the gateway is a better address than naming the databank.
It is not a check, and it should not be read as one.

## The files

| our copy | town | sha256 |
|---|---|---|
| `free-cash-proof-ayer.xlsx` | Ayer | `efcbe33762f2376a8a689329cb963aab0a250f2e8a39e1251a0c2e0a4a771878` |
| `free-cash-proof-groton.xlsx` | Groton | `3688b80cb2226bf8a3b48dfdbd05231c088ad51960e2f9e321a28ac04d866957` |
| `free-cash-proof-littleton.xlsx` | Littleton | `1ae100302ed7db7db944f1894bb7b45ad1e408c464b6fd62691973f17b065835` |
| `free-cash-proof-lunenburg.xlsx` | Lunenburg | `d9a0fac630d1e59ef406dc84ba209e81a87ab8cd43d5aa3215d1b7c672a2809c` |
| `free-cash-proof-shirley.xlsx` | Shirley | `7982bae65c45b7a32b1c31ea37f1e21ffe7e187a142e00b5e03492d1d73980c2` |
| `free-cash-proof-townsend.xlsx` | Townsend | `fd63a62d57f74b712a17b2cdb36f3ea8b92b26930cd012c1983d7327811346b9` |
| `free-cash-proof-upton.xlsx` | Upton | `06d3ae687527d0a270105926bc677fb083d72f6813d581c0aeb7e1a593a57fb1` |
| `free-cash-proof-uxbridge.xlsx` | Uxbridge | `3a29f35d8a22ba93996c743139f0ea9ecf752e0dea6b19041c22a2fbe1871fd8` |
| `free-cash-proof-westford.xlsx` | Westford | `712834d84b7d61bf1e1dc3f5287acb0f50e7c2bb3525035c6b94183e1b1284ba` |

The publisher's own filenames were `FCPCompare<Town>.xlsx`.

## A tenth file, excluded

`FCPCompareAbington.xlsx` was supplied and is **not** here. It contains Lunenburg's data:
`A1` reads `Lunenburg`, and all 102 cells are identical to `FCPCompareLunenburg.xlsx`. It is
a mis-export. Including it would have put Lunenburg in the peer group twice under another
town's name and dragged every comparison toward Lunenburg's own figures.

The only thing that said Abington was the filename, which is rule 13 in its plainest form.
`extract_free_cash.py` asserts `A1` against the filename for every town and refuses to write
if they disagree, so this cannot pass silently again.

**Abington is not wanted and is not a gap.** It was downloaded by mistake, and the peer set
is nine towns by choice. Nothing here is waiting on it.

## What the file is

One sheet, `Sheet1`. `A1` is the town. `B3:F3` are the years 2021–2025. Rows 4–17 are the
proof: an opening figure, the components, and a total.

Two totals the source prints itself, both reconciled before anything is written:

- rows 6–16 sum to row 17, `Identified Free Cash July 1,`
- row 5 `Current Year Calculation` in year *N* equals row 4 `Free Cash Certified Prior Year`
  in year *N+1*

**81 reconciliations across nine towns and five years, all tie to the dollar.**

Note that `Identified Free Cash July 1,` and `Current Year Calculation` are different
numbers — Lunenburg 2025 identifies $3,716,282 and certifies $3,354,370. The certified
figure is the one that carries into the next year, and it is the one to quote as "free
cash". We do not hold DLS's reason for the difference and do not guess at it.

## What these files cannot do

**They carry no denominator.** Every figure is an absolute dollar amount, and there is no
population, budget, revenue or levy anywhere in the workbook. A standard for free cash is a
ratio — the Division of Local Services frames it against the operating budget, and a town's
own financial policy usually sets a target the same way. So a comparison of Littleton's
$11.3M against Shirley's $272K says nothing about which town is closer to its target.

What the proof does support is each town's own trend over five years, and the composition
of the number — which is a share, and therefore does compare.

## Our processed copy

`sources/data/free-cash-proof.csv`, produced by `scripts/extract_free_cash.py`. 630 rows:
town, year, line, amount, the role of that line in the proof, and the cell it came from.

---

# DLS free cash calculations — Lunenburg, free cash as of 1 July 2014 to 1 July 2025

## Where they came from

**The DLS Gateway's City & Town Free Cash Report**, the same report named above:

<https://dls-gw.dor.state.ma.us/gateway/dlspublic/certificationfreecashpublicreport/certificationfreecashpublic>

Jurisdiction **162** (Lunenburg), one fiscal year per request, chosen from two dropdowns held in
session. **There is no file URL**: the page plus the jurisdiction plus the fiscal year is the
whole address (`build_source_index.py`, `FORM_ONLY`). Downloaded by TJ in a browser on
**2 November 2026**, and landed through `ingest.py` (pushed to the bucket, read back, compared)
the same day.

**The report refused some requests, and those refusals are recorded here rather than archived.**
Fifteen further downloads were one-page refusals, not documents, and are not kept:

- thirteen read *"Free Cash/Excess & Deficiency is not available for years prior to FY 2014"*;
- two read *"Free Cash has not been certified for the selected jurisdiction and fiscal year"*.
  **Neither page names the year it refused**, so which fiscal years those were is not
  established from the pages. Every 1 July from 2014 to 2025 is held below, so the refusals were
  of years outside that run; the likeliest is the year not yet certified when they were
  downloaded, and that is a guess, not a reading.

## The files

| our copy | free cash as of | publisher's / downloaded filename | pages | sha256 |
|---|---|---|---:|---|
| `free-cash-worksheet-lunenburg-2014-07-01.pdf` | 1 July 2014 | `Lunenburg.pdf` | 4 | `1037cffa49a7dd469a3abe2632c9d7f5b3c1a6dd0c049c4fac1e771aaade7fd0` |
| `free-cash-worksheet-lunenburg-2015-07-01.pdf` | 1 July 2015 | `Lunenburg FY15.pdf` | 4 | `d732faf626b35284323a9755b4419470c7d901d53293154af854380e45170789` |
| `free-cash-worksheet-lunenburg-2016-07-01.pdf` | 1 July 2016 | `Lunenburg FY16.pdf` | 4 | `28ca1e9a4da82eb78e9f2889a1f8e2f1af7c385d35ef38b07b0dbce94b32019f` |
| `free-cash-worksheet-lunenburg-2017-07-01.pdf` | 1 July 2017 | `Lunenburg FY17.pdf` | 4 | `d87c743d9f693510348c36e3a8e7342c40295164de2ea246b1465551ca253822` |
| `free-cash-worksheet-lunenburg-2018-07-01.pdf` | 1 July 2018 | `Lunenburg FY18.pdf` | 4 | `9e03f2141161628f17c22c85db8d8f5ad2a4ab93af6ac9f60dc474f9153182b5` |
| `free-cash-worksheet-lunenburg-2019-07-01.pdf` | 1 July 2019 | `Lunenburg FY19.pdf` | 4 | `a8a0fc8e058d138dda02409f37926005c71337837d85c4a5dcb3505e6f32fd17` |
| `free-cash-worksheet-lunenburg-2020-07-01.pdf` | 1 July 2020 | `Lunenburg FY20.pdf` | 5 | `9e4c500d6f0a35a20a71a00c4b6a8584d5d737c3056fad7801590e01aa3c7831` |
| `free-cash-certification-lunenburg-fy2022-as-of-2021-07-01.pdf` | 1 July 2021 | `FreeCashCertification (4).PDF` | 5 | `a4752bd1e20d261f688150176ded8d80f5d0770820581f52682e9124b1f183dc` |
| `free-cash-certification-lunenburg-fy2023-as-of-2022-07-01.pdf` | 1 July 2022 | `FreeCashCertification (3).PDF` | 10 | `33a5ec64fda5fbde325e941f0e0b16516fa62992c708153d55541f7f7d160b85` |
| `free-cash-certification-lunenburg-fy2024-as-of-2023-07-01.pdf` | 1 July 2023 | `FreeCashCertification (2).PDF` | 10 | `03ce7c49a25bbae93fc8c3d4f1dae1846d8825cec86fda4d24bc67e3b56dd62f` |
| `free-cash-certification-lunenburg-fy2025-as-of-2024-07-01.pdf` | 1 July 2024 | `FreeCashCertification (1).PDF` | 10 | `519d269a129af05275bdbbcaea9f0101753f7f2dc44e17c62c6d17420f850a14` |
| `free-cash-certification-lunenburg-fy2026-as-of-2025-07-01.pdf` | 1 July 2025 | `FreeCashCertification.PDF` | 10 | `dd166b84f48d3d632770b0b29cd1fa2b790361549fd125cadf06c8164ff201f9` |

The Gateway names every certification `FreeCashCertification.PDF`; the bracketed numbers are the
browser's, added because five files arrived under one name. A resident asking DLS for one should
ask for the **Free Cash Certification for Lunenburg, fiscal year N**.

`pdf_kind.py` reads every page of all twelve as `digital: text`. Nothing was OCR'd.

## How each one's date was established

- **2014-2020, the older worksheet.** The page prints its own result as `FREE CASH, JULY 1,
  <year>`. `Lunenburg FY15.pdf` prints `FREE CASH, JULY 1, 2015`, so its `FY15` matches the
  fiscal year that ENDED on that date, not the year the money is spent in.
- **2021-2025, the Gateway form.** The heading reads `Free Cash Calculation - Fiscal Year <N>`
  and the result line reads `Free Cash Calculation for <N-1>`, so "Fiscal Year 2026" is the year
  the free cash can be spent in and the balance is the one at the close of FY2025, 1 July 2025.
  Two documents corroborate it: the state's own Free Cash Proof above carries the FY2026
  document's figure under year 2025, and the Town's fact sheet carries it under fiscal year 2026.
  `extract_free_cash_certifications.py` asserts the `for <N-1>` reading on every document.

**The two series name their years the opposite way round.** `Lunenburg FY15` and
`Fiscal Year 2016` are the same balance. Every row of the extracted data carries the as-of date
instead of either label for that reason.

**The older ones are WORKSHEETS, not the certification.** Each says *"PLEASE SEE CERTIFICATION
LETTER FOR DIRECTOR OF ACCOUNTS APPROVAL"*. The letter is not held. The worksheet's review date
and the Town fact sheet's certification date differ by days to weeks, which fits a letter issued
after review, and nothing here tests that.

**Names printed on them are shown, not masked** (CLAUDE.md 13e, `notes/process/DATA-PRIVACY.md`):
the town's submitting officer and the DLS field representatives and reviewer.

## Our processed copy

`sources/data/free-cash-certifications.csv`, written by
`scripts/extract_free_cash_certifications.py` (`--check` reproduces it byte for byte). One row per
printed line: the page and vertical position, the text as printed, the amount, and for every total
the identity it closed on. The script's docstring states the identities, the sign rule, how a
printed dash is recorded, and which closings used the $1 allowance in
`notes/process/TOLERANCES.md`. It also prints a cross-check of each year's result against the
Town's fact sheet and the Free Cash Proof, and **one year disagrees with both**: the certification
for fiscal year 2023 (as of 1 July 2022) closes on its own arithmetic at a figure different from
the one the fact sheet and the proof carry, under the same certification date. Which is the later
or corrected figure is not established by anything held.

`Additional Sheet` is printed on the receivables block of the 2016-2020 worksheets with a dash
beside it. It is recorded as a line with no amount; in every year the itemised lines on the page
sum to the printed total (2019 within the $1 allowance), so nothing on an additional sheet
carried an amount.
