# Handoff: the school MUNIS journal (Report 1)

Written 19 October 2026, for an agent picking this up fresh. Read CLAUDE.md rules 1, 7, 11,
13, 13a and **13e** first; this delivery is the case 13e was written for.

## What it is

- **The document.** `Report 1 with Redactions Final.pdf`, 1,744 pages,
  sha256 `6d5d56ee70578b54de2066a2a75969dc62069caeba20cd92902fdfe2cf50da7a`.
- **What the report is.** A MUNIS `glytdbud` journal-detail run covering every journal line
  behind every school account, FY2023 p0 to FY2026 p13:
  - pages 1–679: the school General Fund;
  - pages 680–1742: every school special fund (grants, revolving funds, circuit breaker,
    lunch, school choice);
  - p1743: the GRAND TOTAL.
- **Where it came from.** Jennifer Warren emailed TJ at 9:37 PM on 18 October 2026, with two
  others copied. Their names are deliberately not recorded.
- **What she said:**
  - the redactions are "mostly student-related";
  - a **redaction log** will follow;
  - the **Excel export** keeps producing one row, so she may need to contact Tyler
    Technologies, the MUNIS vendor.
- **Which request it answers.** Part 2 (items 3b and 4) of `2026-09-04-town-accountant-package`
  in `notes/reference/records-requests.csv`, already updated.

## The decision TJ made (18 October 2026)

> "we already agreed that munis logins are public. we can make it private, build our own
> safe redacted csv and database entry, and analyze from there"

So:
- the **raw PDF goes to the PRIVATE bucket** and is never published;
- **our redacted CSV** and a database table are the public copy;
- analysis is built from those.

The MUNIS login printed on every page is **not** a reason to hold or redact anything.

**Why the raw stays private.** The Town's redaction missed three things. The black boxes
really do remove the text underneath; these three were simply never boxed:
- **p643:** a child's name in a tuition line;
- **p34/p35:** a two-letter code in an otherwise boxed column;
- **p1080:** an address fragment.

## Where it stands

**Done, verified, NOT committed:**

| file | what |
|---|---|
| `scripts/extract_munis_school_journal.py` | the extractor; the redaction rule is declared in its header |
| `sources/data/munis-school-journal.csv` | 49,043 journal lines, redacted |
| `sources/data/munis-school-journal-accounts.csv` | 3,356 accounts with their printed totals |
| `sources/data/munis-school-journal-image-pages.csv` | 141 lines read by eye from the 3 picture-only pages (34, 643, 1080), already masked |
| `sources/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md` | the delivery record |
| `scripts/build_db.py`, `notes/reference/SCHEMA.md` | tables `munis_school_journal` and `munis_school_journal_account` |
| `scripts/build_source_index.py` | catalogues the 3 CSVs and the PROVENANCE note |

The raw is read from a gitignored copy at
`build/private/munis/raw/town-ledgers/account-details/account-details-fy2023-fy2026-p13-school-journal.pdf`.
The extractor checks its sha256 before reading.

**What ties (`--check` refuses to write unless all of it does):**
- **Every one of the 3,356 accounts, FY2026:**
  - BUC equals the original appropriation;
  - BUA equals transfers;
  - the actual sources equal YTD actual;
  - the encumbrance sources equal encumbrances;
  - available = revised − actual − encumbrances.

  Every check holds to the cent. Which source code belongs to which column was PROVEN by the
  tie: `GEL` first went with actuals and failed by $258.72, and it is an encumbrance entry.
- **All 2,155 printed TOTAL lines, and the p1743 GRAND TOTAL.**
- **Each picture page** closes its account only with the by-eye lines.
- **FY2023–FY2026 against the published period-13 spreadsheets** (`munis_school_ytd`): actual
  and revised budget match for all 939 accounts both hold, in every year.
- **Limit:** the other ~2,417 accounts, mostly dormant grants, rest on the FY2026 tie and the
  totals only for FY2023–FY2025.

**The masking rule, in the script header:**
1. **A vendor is a person** unless its name carries a business or public-body marker, or is on
   a declared list of 178 businesses. A person becomes `individual (redacted)`, with the vendor
   number and invoice number dropped. 620 names, 4,703 lines.
2. **Every masked name**, in either name order, is masked everywhere it appears in free text.
3. **Placement and tuition lines:** every word not on a declared vocabulary is masked, because
   that is where children are.
4. **Declared name tokens**, plus initial and fragment patterns, are masked in the description,
   comment and invoice fields.
5. **The script refuses to write** if any masked name or token survives anywhere in the output.

`pii_screen.py` on the CSV flags exactly one line: p636, a vehicle "check engine" diagnosis.
It is not a person.

## Blocked — needs TJ, do not route around it

The permission guard refused both of these to the previous agent. **Do not retry them under
another name or ask another agent to do them.** TJ allows them or runs them himself.

1. **Stage the raw PDF privately:**
   ```
   python3 -c "import sys; sys.path.insert(0,'scripts'); import ingest; ingest.stage('town-ledgers/account-details/account-details-fy2023-fy2026-p13-school-journal.pdf', open('/Users/tj/Downloads/Report 1 with Redactions Final.pdf','rb').read(), delivered_as='Report 1 with Redactions Final.pdf')"
   ```
2. **Append the `sources/data/redactions.csv` row:**
   - `decision` = `withhold` for the raw;
   - the reason names the three spots the Town missed;
   - it says the public copy is our CSV;
   - `decided_by` records that every distinct vendor name (1,309), every distinct description
     word (5,765) and every masked field was read.

   The full draft is in the agent's report, quoted in the session transcript of 18–19 October.
   Rebuild it from this doc if needed. Do not invent counts: re-derive them from the script.

**Until both are done:** don't commit the `build_db.py` table loader, don't run `build_api.py`
or `build_schema_page.py` (both would publish the tables), and don't deploy. `fy28/public/docs/`
already holds copies of the three CSVs, and a deploy would serve them.

## Decisions waiting on TJ

1. **Should employees paid as vendors stay masked?** The document doesn't say who is staff, so
   all of them are masked now.
2. **Should staff names in "CLOSE PER [name]" entries stay masked?** These record who closed a
   purchase order. They are masked now.
3. **Suppression or pseudonyms?** Each person is now `individual (redacted)` (suppression).
   With `individual 17` (pseudonymisation) we could count distinct people, for example how many
   game officials the athletics fund paid, without naming anyone. It is less safe, because one
   pseudonym's pattern can identify someone in a small department.
4. **Uncertain fields:**
   - leftover staff initials (JT, JGT, MC/MO beside police details, "L C");
   - masked first names on lunch deposits;
   - single-word vendor stubs the Town left (A, G, MAY, MPY, DINNOCENZO, ELDRIDGE, KILCOMMINS,
     SUZOR), all treated as people.
5. **Should we tell the Town about p643 now, or wait for their redaction log** and check
   whether it lists the page?

## Measured so far

Every figure below comes from `lunenburg.db`. Each is a measurement; any "why" is a hypothesis
(rule 7). These are net appropriations, not costs (rule 11).

- **School General Fund, revised budget vs spent** (spent = paid plus still owed, TJ's
  definition of 23 October 2026, `journal.SPENT`; closed years owe nothing at the close, so
  only FY2026 differs from the actual column -- $25,657,318 paid, $246,767 still owed):

  | FY | revised budget | spent |
  |---|---|---|
  | 2023 | $22,546,062 | $22,436,810 |
  | 2024 | $22,977,154 | $22,755,089 |
  | 2025 | $25,187,628 | $24,560,511 |
  | 2026 | $26,368,342 | $25,904,085 |

  Salaries (object 51x) came in under budget every year.
- **FY2026 vs the period-13 spreadsheet.** This run's FY2026 General Fund actual is $43,639.08
  above the spreadsheet. That is exactly org 13012, "School Non-Recurring" (Curriculum
  Adoption), which the spreadsheet lacks.
- **The kindergarten paraprofessional payroll moved accounts in FY26 with no budget transfer
  recorded:**
  - **S2032131** paid $74,765, $77,700 and $83,766 in FY23–25; in FY26 it paid only $5,373 of
    June summer pay.
  - **S2032121** had no lines at all before FY26. In FY26 it paid $93,691 against a $0 budget.
  - This is the line under the in-district special education escalator (CLAUDE.md, the
    standing questions), so it bears on whether that rate is right.
- **Health insurance (MIIA), FY26:** $3.62M against a $3.70M budget, up about 11% on FY25's
  $3.25M. Only 8 invoices; the rest was posted by June reclassification entries.
  - The model assumes 9% a year. This actual may TEST that rate but must never feed it (rule 1).
- **Transfers (BUA):**
  - mostly the encumbrance carry-forward;
  - FY25 adds a one-line "ADJ FY25 BUDGET" of −$452,580;
  - and a reserve-fund transfer of $65,574.65, posted twice and reversed once.
- **Purchase orders:**
  - each year-end liquidation equals the next year's carry-in;
  - FY26 has no year-end close yet, so $246,767 of encumbrances is still open in this run.
- **Largest vendors, four years combined:**
  - General Fund: MIIA $12.15M, Dee Bus $3.81M, FLLAC $1.66M, Van Pool $1.64M;
  - circuit breaker fund: May Institute 42%, FLLAC 38%;
  - school lunch: Thurston Foods 42%;
  - Extended Day revolving fund: 95% of its vendor payments are MIIA premiums.
- **Payments to individuals:** 18% of the athletics revolving fund's vendor payments ($128k),
  which is consistent with game officials, and 11% of school choice's ($61k).

## Not done yet

- **`describe_data.py`:** the two tables have no semantics entry, so `check_generated.py`
  fails on it.
- **No pages built.** Follow the hub-and-spoke model (`scripts/topics.py`): every page has a
  chart, conclusions are comparisons (`notes/process/AUDIT-PASS.md`), and every limit hit is
  registered in `sources/data/money-gaps.csv` (rule 7c).
- **D1:** the next daily refresh after these tables are committed pushes ~52k rows. Don't run
  `sync_d1.py` by hand.
- **Still due from the Town:** the redaction log and the Excel export. When the Excel arrives,
  tie it to this CSV line by line. It would also let the extractor's by-eye lines be checked.
