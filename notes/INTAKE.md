# Taking documents from the Town without publishing somebody's child

The Town has offered to send more. Some of what it holds names families — most concretely,
special education transfers where the **VENDOR** field is a parent being reimbursed rather
than a company being paid. This is the plan for receiving that safely.

The short version: **an agent never touches the upload.** A deterministic pass runs first,
it fails closed, and only what it emits is ever shown to a model, committed, or published.

---

## 1. What is actually at risk, in order of how hard it is to undo

Naming these separately matters, because a control that stops one does nothing about the
others, and "we were careful" has been the plan every time this has gone wrong anywhere.

| exposure | reversible? |
|---|---|
| **Transmitted** to a model API | No. Sending the bytes is the disclosure. |
| **Committed** to git | No. `git rm` removes it from the tip, not from history. |
| **Published** to the site and mirrored | No. Assume it was fetched. |
| **Derived** into an extract, a total, an index | Sometimes — if you know it happened. |

The fourth one is not theoretical here and it got worse today. This project now publishes an
**inverted word index over the whole archive** at `/minutes/find/`. Every word in every
ingested document becomes a searchable term pointing at the document containing it. A family
name entering the corpus does not merely get published — it gets *indexed*, which is the
difference between a name being in a 900KB file and a name being the answer to a query.

`build_minutes_search.py` is downstream of ingest and cannot protect anything. The gate has
to be upstream of it.

---

## 2. The rule: deterministic before probabilistic

**Redaction is done by code that cannot be persuaded, not by a model that can.**

A language model is the obvious tool for "find the names in this document" and it is the
wrong tool for the *gate*, for two reasons that are both fatal on their own:

- To decide whether a document contains a name, the model must be **given the document**.
  The check is itself the disclosure. There is no way to ask "is this safe to send you"
  without sending it.
- It is probabilistic. It will be right most of the time, which is the worst possible
  property for a control whose failures are permanent and unobservable.

So the gate is a script. The agent works **after** the gate, on what the gate emitted, and
never sees the input to it. This is not a limitation on the agentic pass — everything
interesting (classify the purpose of a transfer, reconcile a total, draft the analysis) is
downstream of the gate and unaffected.

---

## 3. Allowlist the institutions. Do not blocklist the names

This is the whole design, and it is the one idea worth keeping if the rest is rewritten.

**You cannot enumerate names.** A blocklist of names, patterns or heuristics fails *open*:
an unusual spelling, an OCR error, a hyphenated surname, a name that is also a word, a name
in a memo line rather than the vendor line. Every miss is silent and permanent.

**You can enumerate institutions.** The set of legitimate vendors on a special education
line is small, stable and knowable: the collaborative, the out-of-district schools, the
transport companies, the therapy providers, the state. Forty or so entries, not four
thousand.

So invert the question. Not *"is this value a person?"* — unbounded, fails open. Instead:

> **Is this value one of the institutions we recognise? If not, suppress it.**

Bounded, and it fails *closed*. A family name will never appear on a list of bus companies.
Neither will a vendor we have not seen before — which is correct: a new vendor should stop
the pipeline and get a human decision, not sail through because it did not look like a name.

`data/vendor-allowlist.csv`: the value as it appears in the source, a canonical name, and
the document that established it as an institution. It grows by human decision, one row at
a time, and every row records who decided and when.

---

## 4. Suppress the field, do not scan the contents

For anything with a schema — a MUNIS export, a warrant, a transfer schedule — you already
know which column holds the vendor. Drop the column. Do not read it, do not classify it, do
not pass it to anything.

And ask what the analysis actually needs from a transfer record: **date, amount, account,
fund, and what it was for.** Not who. The identity of the payee is not load-bearing for a
single published figure, which follows from rule 11 — a budget line is dollars, and this
project has already committed to not inferring people from dollars. Dropping the vendor
column costs nothing it publishes.

Where the vendor *is* needed — to distinguish a placement from a transport contract — the
allowlist supplies a category, not a name.

---

## 5. Two zones, and the separation is physical

**RAW.** `~/lunenburg-intake/` — **outside the repository working tree entirely.**

Not a gitignored subdirectory. `.gitignore` is a convention that `git add -f` overrides,
that a rewritten ignore file silently changes, and that half the tools in a modern editor do
not consult at all. This repo's own `.gitignore` already carries force-include rules
(`!public/data/`) that punch holes through a global ignore — which is exactly the kind of
interaction that makes "it's gitignored" an unsafe thing to rely on. If the bytes are not
inside the tree, no `git add -A` can reach them, however it is configured.

Rules for the raw zone: never opened in an editor with an AI assistant attached; never the
working directory of an agent session; never `cd`'d into during one.

**CLEAN.** `sources/<request>/` — the derived, field-suppressed artifact, and the only thing
that enters the repo, the model, or the site.

The clean artifact records its own provenance the way rule 12 requires — where the raw came
from, the date, the request — and adds two things: **which fields were suppressed** and
**which rule suppressed them.** A reader must be able to see that a column was removed, or
they will read its absence as the Town not holding it.

---

## 6. Free text has no schema, and needs a different answer

A scanned PDF, an email, a memo line. No columns to drop.

- **Preferred: do not ingest it as text.** Take the figures a human transcribes from it and
  cite the document by its address, without republishing the body.
- **If it must be processed: local inference only.** A local NER pass — spaCy, or Presidio —
  runs on this machine and transmits nothing. Use it to *flag for human review*. Never to
  clear: it fails on exactly the hard cases (OCR garble, unusual names) and a clean result
  from it means nothing.
- **Never a hosted model, at any stage, for any part of this.** Including "just to check."

A document that cannot be handled by either route is a document that gets read by a person
and summarised, not ingested. That is an acceptable answer and it should be used more often
than it will feel comfortable to use it.

---

## 7. The cheapest control is upstream — tell the Town what to send

Every byte that never arrives is a byte that cannot leak, and this costs one paragraph in
the request:

- Vendor names replaced with a **stable vendor ID**, or removed entirely. A stable ID still
  lets us count distinct payees and follow one across years, which is all the analysis needs.
- Or the same data **aggregated by object code**, which is the form the figures are quoted in
  anyway.
- Student names, addresses, dates of birth and identifiers removed at source.

Asking for this is not asking for a favour and should not be framed as one. **The Town has
its own obligation to redact before release**, and specifying the format helps it discharge
that rather than adding work. A request that arrives pre-scoped is easier to fill than one
that requires the clerk to decide what to withhold.

---

## 8. Which law — and it is probably not the one everybody says

Not legal advice; the Town's counsel decides what it may release. But asking with the right
statute named gets a better answer, and the reflex here is usually wrong.

- **FERPA** (20 U.S.C. §1232g; 34 CFR Part 99) is most likely the operative law. Special
  education records held by a school district are **education records**, and FERPA governs
  them.
- **IDEA** adds its own confidentiality provisions at 34 CFR §300.610–300.627.
- **HIPAA is usually *not* the right citation** for school records. Records that are FERPA
  education records are expressly carved out of HIPAA's definition of protected health
  information. It can still reach a contracted provider or certain health-service records,
  so it is not irrelevant — but leading with HIPAA to a school district invites a confused
  answer to a question nobody asked.
- **Massachusetts**: 603 CMR 23.00 (Student Records Regulations), which is stricter than
  FERPA in places; MGL c.71 §34D–34E; and the public records exemptions at MGL c.4 §7(26)(a)
  (statutorily exempt) and (c) (personal privacy).

Nothing here changes the engineering. The gate assumes the worst regardless of which statute
applies, because the pipeline should not depend on a legal question being answered correctly.

---

## 9. Verify by script, and put it where the irreversible step happens

Rule 9 says a finished document is re-checked against the data by script rather than
re-read. The same applies here, and the check belongs at the **commit**, because that is the
step that cannot be undone.

`scripts/verify_no_pii.py`, run by a **pre-commit hook** and in the checks list, refusing the
commit if:

- any staged file under `sources/` carries a column matching the suppressed-field schema;
- any vendor value appears that is not on `vendor-allowlist.csv`;
- any path under the raw zone appears in any tracked file;
- an ingest script wrote to `sources/` without emitting a suppression manifest beside it.

Per rule 13, each check asserts **the value**, not prose about it. `verify_athletics.py`
once passed while the sentence it was checking was wrong; a check that confirms a redaction
notice *exists* while a name sits three columns over would be the same failure with a much
worse consequence.

---

## 10. Decide the breach response now, while nothing has happened

Write it down before it is needed, because the moment it is needed is the worst moment to be
designing it.

1. Stop. Do not push, do not deploy, do not "clean it up quickly."
2. Establish the blast radius: committed only, or pushed, or published, or indexed.
3. If pushed: rewrite history, force push, and **assume a clone exists**. Rotate the
   published copy and the hash.
4. If indexed: rebuild `/minutes/find/` and confirm the term is gone from the shard, by
   fetching the shard — not by assuming the rebuild worked.
5. Tell the Town, in writing, the same day. It is their disclosure as much as ours, and they
   have obligations that run on a clock.

---

## 11. What the agentic pass actually looks like, end to end

```
Town sends  →  ~/lunenburg-intake/           RAW. Outside the tree. No agent, ever.
                      │
                      ▼
              scripts/ingest_<source>.py     Deterministic. Schema-driven. Fails closed.
                      │                      Drops suppressed fields. Checks every vendor
                      │                      value against the allowlist. Emits a manifest
                      │                      of what it removed and why.
                      ▼
              unrecognised values?  ─────▶   STOP. Human adjudicates, one value at a time,
                      │                      locally. Allowlist grows by a row.
                      ▼
              sources/<request>/             CLEAN. Provenance + suppression manifest.
                      │
                      ▼
              scripts/verify_no_pii.py       Pre-commit. Refuses the commit, not a warning.
                      │
                      ▼
              THE AGENTIC PASS               Classify, reconcile, extract, analyse, write.
                                             Everything interesting happens here, on data
                                             that never contained a name.
```

The agentic pass is not reduced by any of this. It is moved to the far side of a gate that
does not depend on the agent behaving well — which is the only kind of gate worth having,
because the agent behaving well is not something this project can verify after the fact.
