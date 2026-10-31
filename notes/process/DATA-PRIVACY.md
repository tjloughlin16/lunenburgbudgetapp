# Data privacy: what is shown, what is masked, and what is already settled

**Read this before raising any privacy question, and before redacting anything.** Every
decision below has been made, most of them more than once. Do not ask again, and do not
report something this page says is shown as a defect.

## The one test

> Does this let a reader attach a **disability, a service received, or a family's
> circumstances** to an identifiable person? If yes, mask that person. If no, show it.

Names in a public record are not the harm. A named child or parent tied to special
education, a placement, a refund for their own child's service -- that is the harm.
Over-masking hides exactly the spending this project exists to show.

## Shown, and never flagged

| what | why it is shown |
|---|---|
| **Staff, by name**, in payroll, journal, reclass and roster rows | Staff acting in their role. Settled repeatedly; not a finding, and an inconsistency in how a staff name was masked is not worth reporting either |
| **Vendors and providers of every kind**, including special education and disability service providers, contractors, game officials | Who the town pays, and how much, is the point of the archive |
| **Officials and board members**, by name and role | Public office |
| **MUNIS report logins** printed on report pages (the report user's ID and first name) | Agreed public; never a reason to hold, redact or take down a report |
| **Everything in the annual town reports**, 1959 to date: pension allowances, pupils' prizes, private payees, births, burials, rosters | The town printed and distributed them; republishing a public document is not a disclosure. No `withheld_rows` for privacy |
| **Scholarship and prize recipients** | Public honours |
| **Roster COUNTS** per team or school | Counts identify nobody |

## Masked

| what | including |
|---|---|
| **Recipients of school services**: a child, or a parent or family acting for their child | refunds, mileage for their own child, fees, NSF checks, tuition reimbursements |
| **Anything that points back to them** | initials, name fragments, check or invoice numbers the Town's warrant would resolve to a payee, a purchase-order sibling row |
| **Quasi-identifiers that single someone out** | a job title plus hire date in a department of four names that person; if the rows cannot be made anonymous, the document is withheld |
| **Student names from scraped athletics schedules** | stripped at fetch time, so they never land on disk; publish the extracted schedule facts, never the pages |
| **Who shared a document informally** | e.g. a board member who passed on slides after they were public record: say how it arrived, not who sent it |

## By source

| source | rule |
|---|---|
| Annual town reports | All public. Land every table, names included |
| Town and district websites, meeting packets, minutes | Public as published |
| **MUNIS deliveries** (`town-ledgers/`) | Held `pending` at `redact.gate()` whatever the screen says. Process, then WE review every distinct text field for a person, then `publish` in `sources/data/redactions.csv`, then publish, then build. Nothing is analysed or built while it is private. The Town does not need to confirm; we are responsible. The fact of a delivery (register row, filenames) is public from the start |
| **Records-request and emailed documents** | Through `redact.gate()`. Raw to the private bucket; our redacted copy public, marked UNOFFICIAL with *Official document available upon request* |
| Minutes a board emails to us | Filed as that meeting's minutes, held but not "posted" (see `delivered-minutes-are-posted` in the project memory) |

## The mechanisms, so nobody builds another

- `scripts/pii_screen.py` -- flags per-person tables and identifier patterns. A screen, not a
  clearance: it cannot see a name in running prose. `decided_by` in `redactions.csv` says who looked.
- `scripts/redact.py` -- builds the redacted copy from the raw and a declared rule, deterministic,
  `--check` rebuilds it byte for byte. A redacted PDF is rebuilt as images, never black boxes
  over live text.
- `scripts/takedown.py` -- the ONE way to remove a published document
  (`notes/process/REMOVING-FROM-THE-ARCHIVE.md`). Never delete by hand.
- CLAUDE.md rule 13e -- the gate, in full.

## When something here does not cover it

Apply the test. If it still is not clear, ask once, with the row in front of TJ, and then
**add the answer to this page** so it is not asked again.
