# The Finance Committee's files — received 4 October 2026

Covers everything under `budget-workbooks/finance-committee/`. The per-file record —
what each delivered file became — is `sources/data/finance-committee-delivery.csv`,
written by `scripts/ingest_finance_committee.py`, and `--check` re-proves it.

## How it reached us

**A public records request made by TJ Loughlin, answered by the chair of the Lunenburg
Finance Committee with the committee's own working files.** They arrived as a OneDrive
share, downloaded as one archive:

| | |
|---|---|
| file | `OneDrive_1_10-4-2026.zip` |
| bytes | 1,384,006,403 |
| sha256 | `169bfbd7baf55fe1228d13bdcab090069e759ee12aaeea9b6e5e50909bf323cf` |
| members | 299 files |

There is no URL. The request is the address. The name of the file a resident would ask
for is in `delivered_as`: the committee's own folder and filename, exactly as delivered.
The keys here are slugged from those names because a bucket key may only hold
`[A-Za-z0-9._/-]`.

**Not recorded here, because it is not known from the delivery:** the date the request
was made, the date the committee answered, and the wording of the request. Neither the
archive nor its members carry them. The correspondence would settle all three.

## What the folders are

The committee's tree, kept: one folder per budget year (`FY20 Budget` to `FY27 Budget`),
and inside those, folders named for the meeting a set of files was presented at — for
example `20230322 - Admin, Unclassified, & Debt Service, Monty Tech, & LPS`. That folder
name is the only record of which meeting a file belongs to, which is why the tree is kept
rather than flattened.

One subfolder is a records request inside this one:
`School Budget Files - Amanda Moore FOIA request to School Dept`. Amanda Moore made it to
the School Department as a member of the Select Board, where the minutes of 16 March 2026
list her as Vice-Chair. The committee held what that request returned, and passed it on.
So those files are two removes from the district.

## What happened to each file

Every one of the 299 members has a disposition in `sources/data/finance-committee-delivery.csv`.
The counts are not repeated here because a count typed into prose is the one thing that goes
stale silently (CLAUDE.md, rule 2). `python3 scripts/ingest_finance_committee.py --check` prints
them, recomputed.

| disposition | meaning |
|---|---|
| filed | new to the archive, published as delivered |
| redacted | about identifiable people. The raw is in the PRIVATE bucket; what is published is OUR copy, under a `.redacted` key, opening with *UNOFFICIAL DOCUMENT, REDACTION DONE BY LUNENBURGBUDGETPROJECT.ORG* |
| withheld | about identifiable people and no copy could be made anonymous. Raw in the private bucket only |
| already held | byte-identical to a document we already mirrored from the town or district site |
| duplicate | a second copy of another file in this delivery |

Why each file was redacted, withheld or cleared is in `sources/data/redactions.csv`: the
decision, the rule, what was removed and how much, and who decided -- the screen, the screen
after OCR, or a person looking. That register never holds a redacted value.

## Published before review

The first push of this delivery ran before the redaction gate existed and was stopped part way,
and more files were secured under an earlier, weaker screen before the present one. The public
bucket cannot delete any of them for ten years. Every such file that the present screen flags
carries a row in `redactions.csv` whose note begins `PUBLISHED BEFORE REVIEW`.

One of them, `PACCDraft 1 (version 3).xlsx`, holds a per-person salary row. The catalogue lists
our redacted copy of it instead; the raw remains at its original key. The rest were read again
after OCR, or looked at page by page, and none held anything about a person.

## Deleted from the public bucket

Two redacted copies of the withheld email were published and then deleted on 5 October 2026,
on TJ's instruction: the first copy's cover described what had been redacted. The bucket's lock
rule was lifted for seven seconds to do it and restored identical; both objects were confirmed
absent afterwards. They are recorded here by sha256 only, because their keys were derived from
a filename that names a person:

- `bdb16b7118db95f5a58e60fe35f28cdb412e5d49aee6253964ca4ecf24b64421`
- `e7b57637fa73ff0ccb1d3fa8ed06fecaa4c7226e894708738320c05085697cae`

## What kind of evidence this is (rule 13a)

**Most of this delivery is people's working files, not accounting-system printouts.**
Presentations, memos, and workbooks somebody built to answer a question. A figure from one
of them is `stated`, however official the folder looks. The exceptions show the system's
marks and must be checked one by one before being treated as ledger evidence. For example,
`Ambulance Receipts - History.xlsx` carries a sheet named `MUNIS GL Account Inquiry`. The
two `eoy162` workbooks are DESE End of Year Financial Report working files: a state filing,
and still a workbook somebody completed.
