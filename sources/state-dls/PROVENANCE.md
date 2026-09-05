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
