# Sent to the Town — September 2026

**These are the copies that actually went out.** Two documents, to the Town Manager, on
4 September 2026.

| file | what it asks |
|---|---|
| `RECORDS-REQUEST-TOWN-ACCOUNTANT.pdf` | Five MUNIS report configurations, FY2023–FY2026 — 23 runs. Year-end expenditures at period 13, Account Details, a line-item transfer report, revenue, and purchase orders closed after close. |
| `REVIEW-DISCREPANCIES.pdf` | Five categories where the Town's year-to-date report and the district's school budget state different things about the same account, what each mismatch prevents, and what the School Committee voted on each. |

## Do not edit anything in this folder

It is the only record of what the recipient holds. `MANIFEST.json` carries the sha256 of
each PDF and of the Markdown it was built from.

**If a figure changes afterwards, that is not a reason to rebuild the PDF in here** — that
would destroy the record and leave us unable to say what they were sent. Send a correction
that names the version it corrects.

    python3 scripts/check_sent_documents.py

reports when our copy has moved away from what went out. Drift is information, not an
error: both documents are generated, so an extractor change rewrites them without anybody
touching a sentence.

## What was NOT sent

`notes/outbound/drafts/` still holds the Superintendent request, the cover emails, the
checklist and `CONNECTING-THE-BUDGET.pdf`. Nothing there has gone to anybody.
