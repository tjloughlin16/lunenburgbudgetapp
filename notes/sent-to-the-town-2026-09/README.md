# Drafts for the Town — NOTHING HERE HAS BEEN SENT

**This folder is misnamed and will be renamed `notes/outbound/drafts/`.** Every document in
it is a draft. An earlier version of this README said these were "the copies that were
sent"; that was never true, and the manifest recorded `sent: null` throughout while the
folder name said otherwise.

The rename is deferred only because `scripts/export_ledger.py` references this path and is
being edited by another agent. See `plans/ARCHIVE-REORG.md` step 3.

**When something is actually sent:** copy it to `notes/outbound/sent-<YYYY-MM>/`, record the
date and the sha256 in a manifest there, and never edit the copy afterwards — it is the
only record of what the recipient holds. `scripts/check_sent_documents.py` reports when our
copy has moved away from it.

---

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
