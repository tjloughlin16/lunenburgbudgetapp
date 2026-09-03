# Sent to the Town for review — September 2026

The PDFs in this folder are the copies that were sent. They are kept because a printed
copy is what gets quoted from later, and because the Markdown they came from is still
being edited: the version somebody replies to is the version in here, not the one in
`notes/`.

| file | to | what it asks |
|---|---|---|
| `REVIEW-DISCREPANCIES.pdf` | Town Manager and Town Accountant | Five categories where the Town's year-to-date report and the district's school budget state different things about the same account, what each mismatch prevents, and what the School Committee voted on each |

**Only what was actually sent is in this folder.** `notes/REQUEST-CODING.pdf` — the
account-level version of the same comparison, addressed to the Superintendent — was
**not sent**: it is too detailed, and the review document covers the same ground at the
level a reader needs. It stays in `notes/` as a draft.

**Sent:** _(fill in the date each was actually sent, and to whom)_

**Not published.** Nothing here is on the website.

## Changing a document after it has been sent

Once it is sent it is a fixed object held by somebody else. **Ours can move without
anybody touching a sentence** — both documents are generated, so a change to an
extractor, a rate or a bucket rewrites them.

`MANIFEST.json` records the sha256 of each PDF that went out and of the Markdown it was
built from, so which version a recipient holds is always answerable.

    python3 scripts/check_sent_documents.py

**Drift is not a failure and the fix is not to rebuild the PDF in here.** That would
destroy the only record of what the recipient actually has. Send a correction that names
the version it corrects.

## Regenerating

Both are generated. Re-running writes a NEW PDF into `notes/`, not into this folder —
deliberately, so a copy that has been sent cannot be overwritten by a later edit.

    python3 scripts/build_discrepancy_review.py
    python3 scripts/build_analysis_pdf.py --file notes/REVIEW-DISCREPANCIES.md

`scripts/minutes_decisions.py` re-checks every quotation in the review document against
the meeting minutes it came from, and fails if one has drifted.
