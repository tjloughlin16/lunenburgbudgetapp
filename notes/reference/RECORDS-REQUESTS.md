# What we have asked the Town and the District for

`records-requests.csv` beside this file. **Backend tracking. Not a report page and not
published** — TJ, 21 September 2026: *"these official requests can include committee or
superintendent names for sure… just dont need to go on report pages… this is all backend
tracking."*

So the register names officials in their official capacity, with titles verified against
the town's own minutes rather than read off a salutation, and nothing here is lifted onto
a published page. What reaches a report is the DOCUMENT if it arrives, cited under rule 12
like any other source.

People who were bcc'd are deliberately not recorded. A blind copy is one the sender chose
not to disclose, and a register is not the place to disclose it.

## Why it exists

Two reasons, and the first is already written into the code.

`build_request_doc.py` says it: *"a hand-written request list goes stale the moment
something arrives, and the failure mode is asking a public official twice for a document
they already sent. That is a real cost — it spends goodwill that the next request needs."*
That script computes what is still MISSING from the coverage matrix. Nothing recorded what
had actually been SENT, so the two halves of the question — what do we still need, and
what have we already asked for — lived in one person's email.

And rule 12: a records request IS an address. When a document arrives, the request that
produced it is its provenance, and that only works if the request was written down at the
time. `sources/town-ledgers/expenses/PROVENANCE-fy2026-p09.md` is the worked example.

## The columns

| column | what it holds |
|---|---|
| `id` | `<date>-<subject>`, stable |
| `sent` | the date it went, not the date it was drafted |
| `to` | role and name, verified from the town's own documents |
| `asks_for` | the document, as specifically as the request put it |
| `why` | what it would settle **here**, tied to what this archive already measures |
| `status` | `sent`, `answered`, `refused`, `partial` |
| `landed_as` | the path in `sources/` once it arrives — this is what closes the loop |
| `quote` | the request in the sender's own words |

**`why` is the column that earns this file.** A request with no stated purpose is
indistinguishable from curiosity six months later, and it is also the sentence that goes
into the follow-up. Where a gap in `money-gaps.csv` names the closing document, that gap
and this row are two halves of one thing.
